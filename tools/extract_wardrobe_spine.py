from __future__ import annotations

import csv
import json
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "wardrobe-assets" / "spine"
CATALOG = ROOT / "wardrobe-assets" / "catalog.js"
APK = Path(r"C:\tmp\sxs-research\current-155937\UnityDataAssetPack.apk")
CACHE = Path(r"C:\tmp\sxs-yoo-cache\wardrobe-bundles")
CONFIG = Path(r"C:\tmp\sxs-yoo-cache\config")
MANIFEST = Path(r"C:\tmp\sxs-yoo-cache\PackageManifest_DefaultPackage_88_156110.bytes")
RESEARCH_TOOLS = Path(r"C:\tmp\sxs-research\tools")
UNITY_DEPS = Path(r"C:\tmp\sxs-research\.deps")

sys.path[:0] = [str(RESEARCH_TOOLS), str(UNITY_DEPS)]

import UnityPy  # noqa: E402
from PIL import Image  # noqa: E402

from bundle_crypto import decrypt_sxs_bundle  # noqa: E402
from extract_config import text_asset_bytes  # noqa: E402
from yoo_manifest import load_manifest  # noqa: E402


GROUPS = {
    "male": {
        "data": "Assets/AppearanceAssets/Character/Model/Male_1/character_Male_1.skel.bytes",
        "texture_prefixes": (
            "Assets/AppearanceAssets/Character/Model/Male_1/Atlas/High/",
            "Assets/AppearanceAssets/Character/Model/Common/Atlas/High/",
        ),
    },
    "female": {
        "data": "Assets/AppearanceAssets/Character/Model/Female_1/character_Female_1.skel.bytes",
        "texture_prefixes": (
            "Assets/AppearanceAssets/Character/Model/Female_1/Atlas/High/",
            "Assets/AppearanceAssets/Character/Model/Common/Atlas/High/",
        ),
    },
    "back": {
        "data": "Assets/AppearanceAssets/Character/backDecoration/backDecoration.skel.bytes",
        "texture_prefixes": ("Assets/AppearanceAssets/Character/backDecoration/Atlas/High/",),
    },
    "primary": {
        "data": "Assets/AppearanceAssets/Character/pWeapon/primaryWeapon.skel.bytes",
        "texture_prefixes": ("Assets/AppearanceAssets/Character/pWeapon/Atlas/High/",),
    },
    "secondary": {
        "data": "Assets/AppearanceAssets/Character/sWeapon/secondaryWeapon.skel.bytes",
        "texture_prefixes": ("Assets/AppearanceAssets/Character/sWeapon/Atlas/High/",),
    },
}

CATEGORY_FOR_TYPE = {
    "body": "outfit",
    "backDecoration": "backwear",
    "pWeapon": "mainHand",
    "sWeapon": "offHand",
    "hair": "hairstyle",
    "headDecoration": "headwear",
    "faceDecoration": "facewear",
    "facePaint": "makeup",
}


def object_name(value, fallback: str) -> str:
    return str(getattr(value, "m_Name", None) or getattr(value, "name", None) or fallback)


def bundle_blob(manifest, bundle_id: int, archive: zipfile.ZipFile) -> bytes:
    bundle = manifest.bundles[bundle_id]
    cached = CACHE / f"{bundle_id}-{bundle.file_hash}.bundle"
    if cached.exists():
        raw = cached.read_bytes()
    else:
        entry = next((name for name in archive.namelist() if bundle.file_hash in name), None)
        if not entry:
            raise FileNotFoundError(f"Bundle {bundle_id} ({bundle.file_hash}) is absent from cache and APK")
        raw = archive.read(entry)
    if len(raw) != bundle.file_size:
        raise ValueError(f"Bundle {bundle_id} has {len(raw)} bytes; manifest expects {bundle.file_size}")
    return decrypt_sxs_bundle(raw, bundle.encrypted)


def extract_bundle(blob: bytes, target: Path, *, texts: bool, textures: bool) -> tuple[int, int]:
    text_count = texture_count = 0
    environment = UnityPy.load(blob)
    for obj in environment.objects:
        if texts and obj.type.name == "TextAsset":
            value = obj.read()
            name = object_name(value, str(obj.path_id))
            if not name.endswith((".atlas", ".skel", "skin_list.txt")):
                continue
            path = target / name
            path.write_bytes(text_asset_bytes(value))
            text_count += 1
        elif textures and obj.type.name == "Texture2D":
            value = obj.read()
            name = object_name(value, str(obj.path_id))
            path = target / (name if name.lower().endswith(".png") else f"{name}.png")
            value.image.save(path, "PNG", compress_level=6)
            texture_count += 1
    return text_count, texture_count


def atlas_pages(path: Path) -> list[str]:
    return list(dict.fromkeys(re.findall(r"(?m)^([^\r\n:]+\.png)\s*$", path.read_text("utf-8", errors="replace"))))


def atlas_skin_pages(path: Path) -> dict[str, list[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    current_page: str | None = None
    for line in path.read_text("utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not line[:1].isspace() and stripped.endswith(".png"):
            current_page = stripped
        elif current_page and not line[:1].isspace() and ":" not in stripped:
            skin = stripped.split("/", 1)[0]
            result[skin].add(current_page)
    return {skin: sorted(pages) for skin, pages in result.items()}


def csv_rows(name: str, key: str) -> dict[str, dict[str, str]]:
    with (CONFIG / f"{name}.csv").open(encoding="utf-8-sig", newline="") as handle:
        return {row[key]: row for row in csv.DictReader(handle) if row.get(key, "").isdigit()}


def friendly_fallback(skin: str) -> str:
    value = re.sub(r"^(?:body_\d+_|pWeapon_|sWeapon_|hair_|headOrnament_\d+_|faceDecoration_\d+_|facePaint_)", "", skin)
    value = re.sub(r"[_-]+", " ", value).strip()
    return " ".join(word.upper() if word.isdigit() else word.title() for word in value.split()) or skin


def sex_for_skin(skin: str) -> tuple[str, ...]:
    if re.search(r"(?:^|_)M(?:_|$)", skin):
        return ("Male",)
    if re.search(r"(?:^|_)F(?:_|$)", skin):
        return ("Female",)
    return ("Male", "Female")


def write_catalog(page_maps: dict[str, set[str]], skin_pages: dict[str, dict[str, list[str]]]) -> None:
    appearances = csv_rows("append_appearance", "ClassId")
    skins = csv_rows("spine_skin", "Id")
    with (CONFIG / "text.g.csv").open(encoding="utf-8-sig", newline="") as handle:
        localized = {row["key"]: row["text"] for row in csv.DictReader(handle)}

    gift_sources: dict[str, str] = {}
    gift_path = CONFIG / "activity_appearance_gift.csv"
    if gift_path.exists():
        with gift_path.open(encoding="utf-8-sig", newline="") as handle:
            for gift in csv.DictReader(handle):
                gift_id = gift.get("GiftId", "")
                if not gift_id.isdigit():
                    continue
                gift_name = localized.get(f"appearance_gift_{gift_id}_name") or "Appearance Gift"
                for item_id in re.findall(r"(\d+):\d+", gift.get("AwardDict", "")):
                    gift_sources.setdefault(item_id, gift_name)

    linked: dict[tuple[str, str], tuple[str, str]] = {}
    for appearance_id, row in appearances.items():
        name = localized.get(f"item_{appearance_id}_name") or localized.get(f"append_appearance_image_{appearance_id}_name")
        for sex, skin_id in re.findall(r"(Male|Female):(\d+)", row.get("SkinDict", "")):
            skin_row = skins.get(skin_id)
            if skin_row and skin_row["SkinType"] in CATEGORY_FOR_TYPE:
                linked.setdefault((sex, skin_id), (appearance_id, name or ""))

    data: dict[str, dict[str, list[dict]]] = {
        category: {"Male": [], "Female": []} for category in CATEGORY_FOR_TYPE.values()
    }
    seen: set[tuple[str, str, str]] = set()
    for skin_id, row in skins.items():
        skin_type = row["SkinType"]
        category = CATEGORY_FOR_TYPE.get(skin_type)
        if not category:
            continue
        skin = row["SkinName"]
        if skin in {"emptySkin", "default"}:
            continue
        group = "back" if skin_type == "backDecoration" else "primary" if skin_type == "pWeapon" else "secondary" if skin_type == "sWeapon" else None
        for sex in sex_for_skin(skin):
            key = (category, sex, skin)
            if key in seen:
                continue
            seen.add(key)
            appearance_id, name = linked.get((sex, skin_id), (f"skin-{skin_id}", ""))
            if not name:
                name = localized.get(f"item_{appearance_id}_name") or row.get("DisplayName") or friendly_fallback(skin)
            if name.startswith("DNT") or re.search(r"[\u3400-\u9fff]", name):
                name = f"Future Cosmetic · {friendly_fallback(skin)}"
            bundle = row.get("BundleName", "")
            if appearance_id in gift_sources:
                acquisition = f"Appearance Gift: {gift_sources[appearance_id]}"
            elif bundle.startswith("AccumulatePay"):
                acquisition = "Stellaris cumulative-spend reward"
            elif bundle.startswith("Linkage"):
                acquisition = "Limited collaboration cosmetic"
            elif bundle.startswith("Activity"):
                acquisition = "Limited-time event cosmetic"
            elif bundle.startswith("Map_"):
                acquisition = f"World progression: {bundle.replace('_', ' ')}"
            elif bundle == "Profession":
                acquisition = "Class / profession progression"
            elif row.get("SkinUseType") == "Free":
                acquisition = "Base customization or gameplay unlock"
            elif bundle.startswith("Pay"):
                acquisition = "Paid wardrobe pack or limited shop"
            else:
                acquisition = "Source not specified in client data"
            actual_group = group or sex.lower()
            lookup = skin
            if actual_group == "back":
                lookup = skin.replace("backDecoration_", "wing_")
            elif actual_group == "primary":
                lookup = skin.replace("_G_", "_")
            elif skin.startswith("facePaint_"):
                lookup = "facePaint_G" if "_G_" in skin else "facePaint_M" if "_M_" in skin else "facePaint_F"
            pages = skin_pages.get(actual_group, {}).get(lookup, [])
            if not pages:
                continue
            data[category][sex].append({
                "id": f"{sex[0]}-{appearance_id}-{skin_id}",
                "itemId": appearance_id if appearance_id.isdigit() else None,
                "name": name,
                "skin": skin,
                "pages": pages,
                "group": actual_group,
                "acquisition": acquisition,
                "icon": f"sxs-stellaris/assets/item_{appearance_id}.webp"
                if appearance_id.isdigit() and (ROOT / "sxs-stellaris" / "assets" / f"item_{appearance_id}.webp").exists()
                else None,
            })

    for category, by_sex in data.items():
        for sex, entries in by_sex.items():
            entries.sort(key=lambda item: (item["name"].casefold(), item["skin"]))

    payload = {
        "version": 88,
        "categories": data,
        "counts": {category: {sex: len(entries) for sex, entries in by_sex.items()} for category, by_sex in data.items()},
    }
    CATALOG.write_text("window.WARDROBE_DATA=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print("catalog:", json.dumps(payload["counts"], ensure_ascii=False))


def main() -> int:
    manifest = load_manifest(MANIFEST)
    assets_by_path = {asset.asset_path: asset for asset in manifest.assets}
    page_maps: dict[str, set[str]] = {}
    skin_page_maps: dict[str, dict[str, list[str]]] = {}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(APK) as archive:
        for group, spec in GROUPS.items():
            target = OUTPUT / group
            target.mkdir(parents=True, exist_ok=True)
            for old in target.iterdir():
                if old.is_file():
                    old.unlink()
            data_asset = assets_by_path[spec["data"]]
            text_count, _ = extract_bundle(bundle_blob(manifest, data_asset.bundle_id, archive), target, texts=True, textures=False)
            texture_ids = sorted({
                asset.bundle_id
                for asset in manifest.assets
                if any(asset.asset_path.startswith(prefix) for prefix in spec["texture_prefixes"])
            })
            texture_count = 0
            for bundle_id in texture_ids:
                _, count = extract_bundle(bundle_blob(manifest, bundle_id, archive), target, texts=False, textures=True)
                texture_count += count
            Image.new("RGBA", (2, 2), (0, 0, 0, 0)).save(target / "_transparent.png", "PNG")
            atlas = next(target.glob("*.atlas"))
            pages = set(atlas_pages(atlas))
            available = {path.name for path in target.glob("*.png")}
            missing = sorted(pages - available)
            if missing:
                raise FileNotFoundError(f"{group}: {len(missing)} atlas pages missing, first: {missing[:10]}")
            for png in target.glob("*.png"):
                if png.name not in pages and png.name != "_transparent.png":
                    png.unlink()
            page_maps[group] = pages
            skin_page_maps[group] = atlas_skin_pages(atlas)
            print(f"{group}: {text_count} rig files, {texture_count} textures, {len(pages)} atlas pages")
    write_catalog(page_maps, skin_page_maps)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
