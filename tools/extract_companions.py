from __future__ import annotations

import ast
import csv
import io
import json
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sxs-companions"
ASSETS = OUT / "assets"
CACHE = Path(r"C:\tmp\sxs-yoo-cache\companion-bundles")
MANIFEST = Path(r"C:\tmp\sxs-yoo-cache\PackageManifest_DefaultPackage_88_156110.bytes")
RESEARCH = Path(r"C:\tmp\sxs-research\tools")
DEPS = Path(r"C:\tmp\sxs-research\.deps")
CDN = "https://zhangjcsomqdl.boltraygames.com/patch/20260828203788/Android/DefaultPackage"

sys.path[:0] = [str(RESEARCH), str(DEPS)]
import UnityPy  # noqa: E402
from bundle_crypto import decrypt_sxs_bundle  # noqa: E402
from extract_config import text_asset_bytes  # noqa: E402
from yoo_manifest import load_manifest  # noqa: E402


PROFESSIONS = {"Doushi": "Duelist", "Shushi": "Sorcerer", "Huwei": "Knight", "Xianzhe": "Sage"}
GIFTS = {"Flower": "Flowers", "Commodity": "Practical Goods", "Valuables": "Valuables", "Book": "Books"}
STAT_LABELS = {
    "Attack": "ATK", "MaxHp": "HP", "Defence": "DEF", "Speed": "SPD",
    "BaseMaxHpPercent": "HP %", "BaseAttackPercent": "ATK %",
    "BaseDefencePercent": "DEF %", "BaseSpeedPercent": "SPD %",
    "CritRatePercent": "Crit Rate", "CritAvoidPercent": "Crit RES",
    "BlockAvoidPercent": "Accuracy", "BlockPercent": "Block Rate",
    "CritPowerPercent": "Crit DMG", "CureAddPercent": "Healing Boost",
    "EffectRate": "Effect Hit Rate", "EffectDodge": "Effect RES",
    "DmgAddPercent": "DMG Boost", "DmgReducePercent": "DMG RES",
    "TravelNpcBaseRewardAddCount": "Travel Base Reward +",
    "TravelNpcBaseRewardAddPercent": "Travel Reward Bonus",
    "TravelNpcExtraRewardAddProbability": "Travel Extra Reward Chance",
}
FLAT_STATS = {"Attack", "MaxHp", "Defence", "Speed", "EffectRate", "EffectDodge", "TravelNpcBaseRewardAddCount"}
PERCENT_STATS = set(STAT_LABELS) - FLAT_STATS


def download_bundle(manifest, bundle_id: int) -> bytes:
    bundle = manifest.bundles[bundle_id]
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / f"{bundle_id}-{bundle.file_hash}.bundle"
    if not cached.exists():
        print(f"downloading bundle {bundle_id} ({bundle.file_size:,} bytes)")
        with urllib.request.urlopen(f"{CDN}/{bundle.file_hash}.bundle", timeout=90) as response:
            cached.write_bytes(response.read())
    raw = cached.read_bytes()
    if len(raw) != bundle.file_size:
        raise RuntimeError(f"bundle {bundle_id}: expected {bundle.file_size}, got {len(raw)}")
    return decrypt_sxs_bundle(raw, bundle.encrypted)


def extract_csvs(manifest) -> dict[str, bytes]:
    wanted = {
        "npc.csv", "level_prop_npc_friendship.csv", "npc_friendship_level.csv",
        "npc_profile.csv", "item.csv", "item_source.csv", "text.g.csv",
    }
    chosen = [
        a for a in manifest.assets
        if PurePosixPath(a.asset_path).name in wanted
        and (PurePosixPath(a.asset_path).name != "text.g.csv" or "/Language/en_US/" in a.asset_path)
    ]
    by_bundle = defaultdict(list)
    for asset in chosen:
        by_bundle[asset.bundle_id].append(asset)
    result = {}
    for bundle_id, assets in by_bundle.items():
        expected = {PurePosixPath(a.asset_path).stem: PurePosixPath(a.asset_path).name for a in assets}
        env = UnityPy.load(download_bundle(manifest, bundle_id))
        for obj in env.objects:
            if obj.type.name != "TextAsset":
                continue
            value = obj.read()
            name = str(getattr(value, "m_Name", None) or getattr(value, "name", ""))
            if name in expected:
                result[expected[name]] = text_asset_bytes(value)
    missing = wanted - set(result)
    if missing:
        raise RuntimeError(f"missing CSV assets: {sorted(missing)}")
    return result


def rows(blob: bytes) -> list[dict[str, str]]:
    text = blob.decode("utf-8-sig", errors="replace")
    return [row for row in csv.DictReader(io.StringIO(text)) if row and not str(next(iter(row.values()), "")).startswith("#")]


def parse_loose_dict(value: str) -> dict:
    if not value:
        return {}
    normalized = re.sub(r"([{,])\s*([A-Za-z][A-Za-z0-9_]*)\s*:", r"\1'\2':", value)
    normalized = normalized.replace("true", "True").replace("false", "False")
    try:
        parsed = ast.literal_eval(normalized)
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, SyntaxError):
        return {}


def format_unlock(row: dict[str, str], item_names: dict[str, str], sources: dict[str, list[str]]) -> dict:
    kind = row.get("CanMeetConditionType", "")
    params = parse_loose_dict(row.get("CanMeetConditionParam", ""))
    if kind == "Level":
        level = params.get("Level")
        return {"label": f"Reach character level {level}" if level is not None else "Story progression", "sources": []}
    if kind == "HasItem":
        item_id = str(params.get("ClassId", ""))
        count = params.get("Count", 1)
        name = item_names.get(item_id, f"Item {item_id}")
        return {"label": f"Collect {count} × {name}", "sources": sources.get(item_id, [])}
    if row.get("IsAutoMeet", "").upper() == "TRUE":
        return {"label": "Met automatically through progression", "sources": []}
    return {"label": "Availability condition is stored in the client", "sources": []}


def recommended(stats: dict[str, float]) -> list[str]:
    if stats.get("ATK %") or stats.get("SPD %"):
        return ["Duelist", "Sorcerer"]
    if stats.get("DEF %"):
        return ["Knight"]
    if stats.get("HP %") and stats.get("Healing Boost"):
        return ["Sage"]
    if stats.get("HP %"):
        return ["Knight", "Sage"]
    return []


def save_art(manifest, companion_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    wanted = {}
    result = defaultdict(dict)
    allowed_ids = {row["Id"] for row in companion_rows}
    if ASSETS.exists():
        for old in ASSETS.glob("*.webp"):
            match = re.search(r"_(\d+)\.webp$", old.name)
            if not match or match.group(1) not in allowed_ids:
                old.unlink()
    for row in companion_rows:
        npc_id = row["Id"]
        for kind, filename in (("icon", f"npc_icon_{npc_id}.png"), ("figure", f"npc_role_{npc_id}.png")):
            target = ASSETS / f"{kind}_{npc_id}.webp"
            if target.exists():
                result[npc_id][kind] = f"assets/{target.name}"
            else:
                wanted[filename] = (npc_id, kind)
    selected = {}
    for asset in manifest.assets:
        name = PurePosixPath(asset.asset_path).name.lower()
        if name in wanted and ("/NPC/" in asset.asset_path or "/Npc_" in asset.asset_path):
            selected[name] = asset
    by_bundle = defaultdict(set)
    for name, asset in selected.items():
        by_bundle[asset.bundle_id].add(name)
    ASSETS.mkdir(parents=True, exist_ok=True)
    for bundle_id, names in by_bundle.items():
        env = UnityPy.load(download_bundle(manifest, bundle_id))
        for obj in env.objects:
            if obj.type.name not in {"Sprite", "Texture2D"}:
                continue
            value = obj.read()
            name = str(getattr(value, "m_Name", None) or getattr(value, "name", "")).lower()
            filename = name if name.endswith(".png") else f"{name}.png"
            if filename not in names:
                continue
            npc_id, kind = wanted[filename]
            target = ASSETS / f"{kind}_{npc_id}.webp"
            value.image.save(target, "WEBP", quality=92, method=6)
            result[npc_id][kind] = f"assets/{target.name}"
    return result


def main() -> int:
    manifest = load_manifest(MANIFEST)
    blobs = extract_csvs(manifest)
    localization = {r["key"]: r.get("text", "") for r in rows(blobs["text.g.csv"])}
    npc_rows = [
        r for r in rows(blobs["npc.csv"])
        if r.get("LevelPropId") and r.get("NameKey") and r.get("FriendshipItemId")
        and int(r.get("Id", "0") or 0) >= 8000
    ]
    item_names = {}
    for row in rows(blobs["item.csv"]):
        item_id = row.get("ClassId") or row.get("Id")
        if item_id:
            item_names[item_id] = localization.get(f"item_{item_id}_name", row.get("Name", f"Item {item_id}"))
    source_names = {
        "DelegateTask": "Commission tasks", "MapExplore": "Map exploration", "Shop": "Shop",
        "Activity": "Event", "Quest": "Quest", "Dungeon": "Dungeon", "Achievement": "Achievement",
    }
    sources = defaultdict(list)
    for row in rows(blobs["item_source.csv"]):
        item_id = row.get("Id") or row.get("ClassId")
        raw = row.get("ItemSourceType") or row.get("SourceType") or ""
        label = source_names.get(raw, re.sub(r"(?<!^)(?=[A-Z])", " ", raw).strip())
        if item_id and label and label not in sources[item_id]:
            sources[item_id].append(label)

    curve_rows = defaultdict(dict)
    for row in rows(blobs["level_prop_npc_friendship.csv"]):
        level = int(row["level"])
        values = {}
        for key, label in STAT_LABELS.items():
            raw = row.get(key, "0") or "0"
            value = float(raw)
            if value:
                values[label] = value / 100 if key in PERCENT_STATS else value
        curve_rows[row["class_id"]][level] = values

    exp_rows = defaultdict(dict)
    for row in rows(blobs["npc_friendship_level.csv"]):
        exp_rows[row["Id"]][int(row["Level"])] = int(float(row.get("FriendshipExp", "0") or 0))

    profile_rows = defaultdict(list)
    for row in rows(blobs["npc_profile.csv"]):
        npc_id = row["Id"]
        profile_id = row.get("ProfileId", "")
        text = localization.get(f"npc_profile_Content_{npc_id}_{profile_id}", "")
        if not text:
            text = row.get("ContentText", "").replace("\\n", "\n")
        if text:
            condition = parse_loose_dict(row.get("UnlockConditionParam", ""))
            profile_rows[npc_id].append({"id": profile_id, "level": condition.get("FriendshipLevel"), "text": text})

    art = save_art(manifest, npc_rows)
    companions = []
    for row in npc_rows:
        npc_id = row["Id"]
        name = localization.get(row["NameKey"], "").strip()
        if not name or name.startswith("DNT"):
            continue
        curve = curve_rows.get(row["LevelPropId"], {})
        if not curve:
            continue
        max_level = max(curve)
        final_stats = curve[max_level]
        companions.append({
            "id": int(npc_id), "name": name, "premium": row.get("NpcRoleType") == "Special",
            "catalog": "Crossover" if row.get("NpcCatalog") == "Linkage" else "World",
            "nativeClass": PROFESSIONS.get(row.get("TravelProfession", ""), row.get("TravelProfession", "")),
            "recommended": recommended(final_stats), "gift": GIFTS.get(row.get("PreferenceGiftType", ""), row.get("PreferenceGiftType", "")),
            "region": localization.get(f"Mainland_group_{row.get('MapGroupId', '')}", f"Map group {row.get('MapGroupId', '')}"),
            "unlock": format_unlock(row, item_names, sources), "art": art.get(npc_id, {}),
            "maxLevel": max_level, "curve": [curve.get(level, {}) for level in range(1, max_level + 1)],
            "exp": [exp_rows[npc_id].get(level, 0) for level in range(1, max_level + 1)],
            "profiles": sorted(profile_rows[npc_id], key=lambda p: int(p["id"] or 0)),
        })
    companions.sort(key=lambda c: (not c["premium"], c["nativeClass"], c["name"]))
    published_ids = {str(c["id"]) for c in companions}
    for old in ASSETS.glob("*.webp"):
        match = re.search(r"_(\d+)\.webp$", old.name)
        if not match or match.group(1) not in published_ids:
            old.unlink()
    OUT.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(companions, ensure_ascii=False, separators=(",", ":"))
    (OUT / "data.js").write_text(f"window.COMPANION_DATA={payload};\n", encoding="utf-8")
    print(f"wrote {len(companions)} localized companions and {sum(bool(c['art']) for c in companions)} art records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
