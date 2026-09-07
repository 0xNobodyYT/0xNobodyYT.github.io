from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "wardrobe-assets" / "spine"
ICON_OUTPUT = ROOT / "wardrobe-assets" / "icons"
CATALOG = ROOT / "wardrobe-assets" / "catalog.js"
APK = Path(r"C:\tmp\sxs-research\current-155937\UnityDataAssetPack.apk")
CACHE = Path(r"C:\tmp\sxs-yoo-cache\wardrobe-bundles")
CONFIG = Path(r"C:\tmp\sxs-yoo-cache\config")
MANIFEST = Path(r"C:\tmp\sxs-yoo-cache\PackageManifest_DefaultPackage_88_156110.bytes")
RESEARCH_TOOLS = Path(r"C:\tmp\sxs-research\tools")
UNITY_DEPS = Path(r"C:\tmp\sxs-research\.deps")
ADB = Path(r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe")
REMOTE_CACHE = "/sdcard/Android/data/com.zjcs.android.us/files/yoo/DefaultPackage/CacheFiles"

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


def ensure_cached_bundles(manifest, bundle_ids: set[int]) -> None:
    missing = [bundle_id for bundle_id in bundle_ids if not (CACHE / f"{bundle_id}-{manifest.bundles[bundle_id].file_hash}.bundle").exists()]
    if not missing or not ADB.exists():
        return
    listing = subprocess.run(
        [str(ADB), "shell", f"find {REMOTE_CACHE} -name __data"],
        check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    remote_by_hash = {}
    for raw_path in listing:
        path = raw_path.rstrip("\r").strip()
        parts = path.split("/")
        if len(parts) >= 2 and parts[-1] == "__data":
            remote_by_hash[parts[-2]] = path
    CACHE.mkdir(parents=True, exist_ok=True)
    pulled = 0
    for bundle_id in missing:
        bundle = manifest.bundles[bundle_id]
        remote = remote_by_hash.get(bundle.file_hash)
        if not remote:
            continue
        target = CACHE / f"{bundle_id}-{bundle.file_hash}.bundle"
        subprocess.run([str(ADB), "pull", remote, str(target)], check=True, stdout=subprocess.DEVNULL)
        pulled += 1
    print(f"icons: pulled {pulled}/{len(missing)} required bundles from the running client cache")


def extract_item_icons(manifest, archive: zipfile.ZipFile) -> None:
    items = csv_rows("item", "ClassId")
    appearance_ids = set(csv_rows("append_appearance", "ClassId"))
    wanted: dict[str, set[str]] = defaultdict(set)
    for item_id, row in items.items():
        if item_id not in appearance_ids:
            continue
        icon = row.get("Icon", "").replace("\\", "/")
        if icon:
            wanted[f"{icon.rsplit('/', 1)[-1]}.png".lower()].add(item_id)

    assets_by_name = {
        asset.asset_path.rsplit("/", 1)[-1].lower(): asset
        for asset in manifest.assets
        if "/ItemIcon/" in asset.asset_path and asset.asset_path.lower().endswith(".png")
    }
    selected = {name: assets_by_name[name] for name in wanted if name in assets_by_name}
    bundle_ids = {asset.bundle_id for asset in selected.values()}
    ensure_cached_bundles(manifest, bundle_ids)
    names_by_bundle: dict[int, set[str]] = defaultdict(set)
    for name, asset in selected.items():
        names_by_bundle[asset.bundle_id].add(name)

    ICON_OUTPUT.mkdir(parents=True, exist_ok=True)
    for old in ICON_OUTPUT.glob("*.webp"):
        old.unlink()
    written = unavailable = 0
    for bundle_id, names in names_by_bundle.items():
        try:
            environment = UnityPy.load(bundle_blob(manifest, bundle_id, archive))
        except FileNotFoundError:
            unavailable += len(names)
            continue
        for obj in environment.objects:
            if obj.type.name != "Texture2D":
                continue
            value = obj.read()
            name = object_name(value, str(obj.path_id)).lower()
            key = name if name.endswith(".png") else f"{name}.png"
            if key not in names:
                continue
            image = value.image.convert("RGBA")
            image.thumbnail((160, 160), Image.Resampling.LANCZOS)
            for item_id in wanted[key]:
                image.save(ICON_OUTPUT / f"item_{item_id}.webp", "WEBP", quality=88, method=3)
                written += 1
    print(f"icons: {written} item thumbnails written; {unavailable} asset entries were not cached")


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


def skin_thumbnail(group: str, pages: list[str], skin: str) -> str | None:
    if not pages:
        return None
    source = OUTPUT / group / pages[0]
    if not source.exists():
        return None
    image = Image.open(source).convert("RGBA")
    bounds = image.getchannel("A").getbbox()
    if bounds:
        image = image.crop(bounds)
    image.thumbnail((144, 144), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    canvas.alpha_composite(image, ((160 - image.width) // 2, (160 - image.height) // 2))
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", f"{group}_{skin}")
    path = ICON_OUTPUT / f"skin_{safe}.webp"
    canvas.save(path, "WEBP", quality=88, method=3)
    return f"wardrobe-assets/icons/{path.name}"


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
                map_number = bundle.removeprefix("Map_")
                region = {"11": "Forest Kingdom"}.get(map_number, f"world region {map_number}")
                acquisition = f"{region} progression reward (exploration, dungeon, monster, or NPC gear)"
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
            item_icon = (
                f"wardrobe-assets/icons/item_{appearance_id}.webp"
                if appearance_id.isdigit() and (ICON_OUTPUT / f"item_{appearance_id}.webp").exists()
                else f"sxs-stellaris/assets/item_{appearance_id}.webp"
                if appearance_id.isdigit() and (ROOT / "sxs-stellaris" / "assets" / f"item_{appearance_id}.webp").exists()
                else skin_thumbnail(actual_group, pages, skin)
            )
            data[category][sex].append({
                "id": f"{sex[0]}-{appearance_id}-{skin_id}",
                "itemId": appearance_id if appearance_id.isdigit() else None,
                "name": name,
                "skin": skin,
                "pages": pages,
                "group": actual_group,
                "acquisition": acquisition,
                "icon": item_icon,
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
        extract_item_icons(manifest, archive)
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
