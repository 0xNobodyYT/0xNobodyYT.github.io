from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "wardrobe-assets" / "spine"
APK = Path(r"C:\tmp\sxs-research\current-155937\UnityDataAssetPack.apk")
RESEARCH_TOOLS = Path(r"C:\tmp\sxs-research\tools")
UNITY_DEPS = Path(r"C:\tmp\sxs-research\.deps")

sys.path.insert(0, str(RESEARCH_TOOLS))
sys.path.insert(0, str(UNITY_DEPS))

import UnityPy  # noqa: E402
from PIL import Image  # noqa: E402

from bundle_crypto import decrypt_sxs_bundle  # noqa: E402
from extract_config import text_asset_bytes  # noqa: E402
from inventory_apk import bundle_entry, manifest_entries  # noqa: E402
from yoo_manifest import parse_manifest  # noqa: E402


GROUPS = {
    "male": {"data": 4155, "textures": [4076, 4079, 4138, 4141, 4153]},
    "female": {"data": 4117, "textures": [4076, 4079, 4100, 4103]},
    "back": {"data": 4062, "textures": [4061]},
    "primary": {"data": 4198, "textures": [4175]},
    "secondary": {"data": 4218, "textures": [4200, 4203]},
}

KEEP_PAGES = {
    "male": {
        "face.png", "brow.png",
        "body_0_M_008.png", "body_0_M_013.png", "body_0_M_017.png",
        "hair_M_15.png", "hair_M_18.png", "hair_M_22.png",
        "headOrnament_2_G_002.png", "headOrnament_2_G_022.png",
    },
    "female": {
        "face.png", "brow.png",
        "body_0_F_008.png", "body_0_F_013.png", "body_0_F_017.png",
        "hair_F_15.png", "hair_F_18.png", "hair_F_22.png",
        "headOrnament_2_G_003.png", "headOrnament_2_G_023.png",
    },
    "back": {"wing_01.png", "wing_02.png", "wing_03.png", "wing_07.png", "wing_12.png"},
    "primary": {"pWeapon_100_002.png", "pWeapon_200_002.png"},
    "secondary": {"sWeapon_11_002.png", "sWeapon_12_002.png", "sWeapon_21_002.png", "sWeapon_22_002.png"},
}


def object_name(value, fallback: str) -> str:
    return str(getattr(value, "m_Name", None) or getattr(value, "name", None) or fallback)


def extract_bundle(blob: bytes, target: Path) -> tuple[list[Path], int]:
    environment = UnityPy.load(blob)
    text_files: list[Path] = []
    textures = 0
    target.mkdir(parents=True, exist_ok=True)
    for obj in environment.objects:
        if obj.type.name == "TextAsset":
            value = obj.read()
            name = object_name(value, str(obj.path_id))
            raw = text_asset_bytes(value)
            suffix = ".atlas" if name.endswith(".atlas") else ".skel" if name.endswith(".skel") else ".txt"
            if name.endswith((".atlas", ".skel")):
                output_name = name
            else:
                output_name = f"{name}{suffix}"
            path = target / output_name
            path.write_bytes(raw)
            text_files.append(path)
        elif obj.type.name == "Texture2D":
            value = obj.read()
            name = object_name(value, str(obj.path_id))
            path = target / (name if name.lower().endswith(".png") else f"{name}.png")
            value.image.save(path, "PNG", optimize=True)
            textures += 1
    return text_files, textures


def atlas_pages(atlas: Path) -> list[str]:
    text = atlas.read_text(encoding="utf-8", errors="replace")
    return list(dict.fromkeys(re.findall(r"(?m)^([^\r\n:]+\.png)\s*$", text)))


def prune_atlas(group: str, atlas: Path, target: Path) -> int:
    keep = KEEP_PAGES[group]
    text = atlas.read_text(encoding="utf-8", errors="replace")
    pages = atlas_pages(atlas)
    discarded = 0
    for page in pages:
        if page not in keep:
            text = re.sub(rf"(?m)^{re.escape(page)}\s*$", "_transparent.png", text)
            discarded += 1
    atlas.write_text(text, encoding="utf-8", newline="\n")

    for png in target.glob("*.png"):
        if png.name not in keep and png.name != "_transparent.png":
            png.unlink()
    Image.new("RGBA", (2, 2), (0, 0, 0, 0)).save(target / "_transparent.png", "PNG")
    return discarded


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(APK) as archive:
        default_entry = next(entry for entry in manifest_entries(archive) if "/DefaultPackage/" in entry)
        manifest = parse_manifest(archive.read(default_entry))
        names = set(archive.namelist())

        def payload(bundle_id: int) -> bytes:
            bundle = manifest.bundles[bundle_id]
            entry = bundle_entry(default_entry, bundle.file_name(manifest.output_name_style))
            if entry not in names:
                raise FileNotFoundError(f"Bundle {bundle_id} is not embedded: {entry}")
            return decrypt_sxs_bundle(archive.read(entry), bundle.encrypted)

        for group, bundles in GROUPS.items():
            target = OUTPUT / group
            for old in target.glob("*.png"):
                old.unlink()
            texts, texture_count = extract_bundle(payload(bundles["data"]), target)
            for bundle_id in bundles["textures"]:
                extra_texts, count = extract_bundle(payload(bundle_id), target)
                texts.extend(extra_texts)
                texture_count += count

            discarded = 0
            for atlas in target.glob("*.atlas"):
                discarded += prune_atlas(group, atlas, target)
            missing_kept = sorted(page for page in KEEP_PAGES[group] if not (target / page).exists())
            if missing_kept:
                raise FileNotFoundError(f"{group}: required embedded pages are missing: {missing_kept}")
            print(f"{group}: {len(texts)} text assets, {texture_count} textures, {discarded} pages redirected to one transparent texture")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
