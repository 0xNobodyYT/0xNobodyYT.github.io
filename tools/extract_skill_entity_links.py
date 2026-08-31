"""Extract nested fight-status links used by player skills.

This is an offline maintainer tool.  It reads the current YooAsset manifest and
the IL2CPP dummy assemblies, downloads only the fight-entity bundles referenced
by the player skill catalogue, and writes a compact entity -> entity graph used
by ``generate_combat_data.py``.

The generated JSON is committed; the live GitHub Pages site never downloads
game bundles.
"""
from __future__ import annotations

import ast
import csv
import json
import re
import struct
import sys
import urllib.request
import zipfile
from collections import deque
from pathlib import Path

RESEARCH = Path(r"C:\tmp\sxs-research")
CONFIG = Path(r"C:\tmp\sxs-live-config-85")
APK = RESEARCH / "current-155937" / "UnityDataAssetPack.apk"
DUMMY_DLLS = RESEARCH / "Il2CppDumper-current" / "DummyDll"
UNITYPY = RESEARCH / ".deps"
CACHE = Path(r"C:\tmp\sxs-effect-bundles")
DATA_JS = Path(__file__).resolve().parents[1] / "sxs-loadout-builder" / "data.js"
OUT = Path(__file__).with_name("skill-entity-links.json")
CDN = "https://zhangjcsomqdl.boltraygames.com/patch/20260828203788/Android/DefaultPackage"

sys.path.insert(0, str(RESEARCH / "tools"))
sys.path.insert(0, str(UNITYPY))

import UnityPy  # noqa: E402
import UnityPy.helpers.TypeTreeHelper as TypeTreeHelper  # noqa: E402
from UnityPy.files.SerializedFile import SerializedType  # noqa: E402
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator  # noqa: E402
from UnityPy.helpers.TypeTreeNode import TypeTreeNode  # noqa: E402
from inventory_apk import manifest_entries  # noqa: E402
from yoo_manifest import parse_manifest  # noqa: E402


def load_player_skill_ids() -> set[int]:
    text = DATA_JS.read_text(encoding="utf-8")
    payload = json.loads(text.split("=", 1)[1].rstrip(";\n"))
    return {int(skill_id) for skill_id in payload["skills"]}


def list_value(value: str) -> list[int]:
    try:
        parsed = ast.literal_eval(value or "[]")
    except Exception:
        return []
    return [int(item) for item in parsed if str(item).lstrip("-").isdigit() and int(item) > 0]


def source_entities(skill_ids: set[int]) -> dict[int, set[int]]:
    result = {}
    with (CONFIG / "skill.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if not row.get("ClassId", "").isdigit() or int(row["ClassId"]) not in skill_ids:
                continue
            values = set()
            for key in ("EcEntityId", "DirectionEcEntityId", "RandomSkillEntityId"):
                if row.get(key, "").isdigit() and int(row[key]) > 0:
                    values.add(int(row[key]))
            for key in ("PassiveStatusIdList", "ViewPropEntities"):
                values.update(list_value(row.get(key, "")))
            result[int(row["ClassId"])] = values
    return result


def load_manifest_assets():
    with zipfile.ZipFile(APK) as archive:
        entry = next(name for name in manifest_entries(archive) if "/DefaultPackage/" in name)
        manifest = parse_manifest(archive.read(entry))
    assets = {}
    for asset in manifest.assets:
        path = asset.asset_path.replace("\\", "/")
        name = path.rsplit("/", 1)[-1].removesuffix(".prefab")
        if "/EcEntity/Fight/FightSkill/" in path and path.endswith(".prefab") and name.isdigit():
            assets[int(name)] = asset
    return manifest, assets


def clone_nodes(nodes, start: int) -> TypeTreeNode:
    selected = [nodes[0], *nodes[start:]]
    copies = [
        TypeTreeNode(node.m_Level, node.m_Type, node.m_Name, 0, 0, m_MetaFlag=node.m_MetaFlag)
        for node in selected
    ]
    return TypeTreeNode.from_list(copies)


def make_ref_type(generator, class_name: str, namespace: str, assembly: str):
    lookup = f"{namespace}.{class_name}" if namespace else class_name
    nodes = generator.get_nodes(f"{assembly}.dll", lookup)
    # Serializable managed-reference classes are emitted by the dummy DLLs
    # with a MonoBehaviour header.  Their registry payload starts immediately
    # after m_Name, so remove that header while retaining the root node.
    name_index = next(index for index, node in enumerate(nodes) if node.m_Name == "m_Name")
    node = clone_nodes(nodes, name_index + 1)
    ref_type = SerializedType.__new__(SerializedType)
    ref_type.__attrs_init__(114)
    ref_type.node = node
    ref_type.m_ClassName = class_name
    ref_type.m_NameSpace = namespace
    ref_type.m_AssemblyName = assembly
    ref_type.script_type_index = -1
    ref_type.is_stripped_type = False
    ref_type.old_type_hash = b"\0" * 16
    ref_type.script_id = b"\0" * 16
    ref_type.type_dependencies = ()
    return ref_type


def read_with_references(obj, generator):
    # The original bundles strip their reference-type tree table.  Unity still
    # serializes class / namespace / assembly names in each registry.  Add each
    # missing type lazily and retry the normal UnityPy reader.
    for _ in range(30):
        try:
            return obj.read_typetree(check_read=False)
        except ValueError as error:
            match = re.search(r"Referenced type not found: (\S+) (\S*) (\S+)", str(error))
            if not match:
                raise
            class_name, namespace, assembly = match.groups()
            obj.assets_file.ref_types.append(make_ref_type(generator, class_name, namespace, assembly))
    raise RuntimeError(f"Too many missing reference types in object {obj.path_id}")


def collect_ids(value, result: set[int], key: str = ""):
    if isinstance(value, dict):
        for child_key, child in value.items():
            collect_ids(child, result, child_key)
    elif isinstance(value, list):
        for child in value:
            collect_ids(child, result, key)
    elif isinstance(value, int) and value > 0 and (
        key.endswith("StatusId") or key.endswith("StatusEntityId") or key == "StatusEntityClassId"
    ):
        result.add(value)


SUMMON_CFG = re.compile(
    rb"\x18\x00\x00\x00FightHitSummonMonsterCfg"
    rb"\x06\x00\x00\x00Common\x00\x00"
    rb"\x07\x00\x00\x00Console\x00"
)

VOODOO_SUMMON_CFG = re.compile(
    rb"\x1b\x00\x00\x00FightHitSummonVoodooDollCfg\x00"
    rb"\x06\x00\x00\x00Common\x00\x00"
    rb"\x07\x00\x00\x00Console\x00"
)


def bundle_links(bundle_path: Path, generator) -> tuple[set[int], set[int]]:
    environment = UnityPy.load(str(bundle_path))
    environment.typetree_generator = generator
    found = set()
    summon_classes = set()
    for obj in environment.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        raw = obj.get_raw_data()
        for match in SUMMON_CFG.finditer(raw):
            if match.end() + 4 <= len(raw):
                summon_id = struct.unpack_from("<I", raw, match.end())[0]
                if summon_id:
                    summon_classes.add(summon_id)
        # Decoy Clone uses a separate summon component but its SummonId feeds
        # the same summon_monster_* configuration tables as ordinary summons.
        for match in VOODOO_SUMMON_CFG.finditer(raw):
            if match.end() + 4 <= len(raw):
                summon_id = struct.unpack_from("<I", raw, match.end())[0]
                if summon_id:
                    summon_classes.add(summon_id)
        try:
            tree = read_with_references(obj, generator)
        except (AssertionError, FileNotFoundError, RuntimeError, TypeError, ValueError):
            continue
        collect_ids(tree, found)
    return found, summon_classes


def main():
    TypeTreeHelper.read_typetree_boost = None
    CACHE.mkdir(parents=True, exist_ok=True)
    skill_entities = source_entities(load_player_skill_ids())
    manifest, assets = load_manifest_assets()
    generator = TypeTreeGenerator("2022.3.57f1")
    generator.load_local_dll_folder(str(DUMMY_DLLS))

    queue = deque(sorted(set().union(*skill_entities.values())))
    seen = set()
    links = {}
    summons = {}
    bundle_cache = {}
    while queue:
        entity_id = queue.popleft()
        if entity_id in seen or entity_id not in assets:
            continue
        seen.add(entity_id)
        asset = assets[entity_id]
        bundle = manifest.bundles[asset.bundle_id]
        path = CACHE / f"{bundle.file_hash}.bundle"
        if not path.exists() or path.stat().st_size != bundle.file_size:
            path.write_bytes(urllib.request.urlopen(f"{CDN}/{bundle.file_hash}.bundle", timeout=60).read())
        if bundle.file_hash not in bundle_cache:
            bundle_cache[bundle.file_hash] = bundle_links(path, generator)
        nested_ids, summon_ids = bundle_cache[bundle.file_hash]
        nested = {item for item in nested_ids if item != entity_id}
        links[str(entity_id)] = sorted(nested)
        if summon_ids:
            summons[str(entity_id)] = sorted(summon_ids)
        queue.extend(sorted(item for item in nested if item in assets and item not in seen))
        if len(seen) % 25 == 0:
            print(f"Parsed {len(seen)} entities; queue {len(queue)}")

    payload = {
        "skills": {str(skill_id): sorted(values) for skill_id, values in sorted(skill_entities.items())},
        "links": dict(sorted(links.items(), key=lambda item: int(item[0]))),
        "summons": dict(sorted(summons.items(), key=lambda item: int(item[0]))),
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUT}: {len(payload['skills'])} skills, {len(links)} entities")


if __name__ == "__main__":
    main()
