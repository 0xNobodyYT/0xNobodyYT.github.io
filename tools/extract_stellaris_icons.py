"""Extract the in-game icons used by Stellaris rewards from the YooAsset pack."""

from __future__ import annotations

import csv
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(r"C:\tmp\sxs-live-config-85")
APK = Path(r"C:\tmp\sxs-assets\UnityDataAssetPack.apk")
RESEARCH = Path(r"C:\tmp\sxs-research")
OUT = ROOT / "sxs-stellaris" / "assets"
LIVE_MANIFEST = Path(r"C:\tmp\PackageManifest_DefaultPackage_88_156110.bytes")
LIVE_BUNDLES = Path(r"C:\tmp\stellaris-bundles")
MANIFEST_ENTRY = "assets/yoo/DefaultPackage/PackageManifest_DefaultPackage_77_155937.bytes"

sys.path[:0] = [str(RESEARCH / ".deps"), str(RESEARCH / "tools")]
import UnityPy  # noqa: E402
from bundle_crypto import decrypt_sxs_bundle  # noqa: E402
from yoo_manifest import parse_manifest  # noqa: E402


def reward_ids() -> set[int]:
    found = set()
    with (CONFIG / "accumulated_pay_award.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            for field in ("CoreAward", "SubAwards"):
                found.update(int(value) for value in re.findall(r"(\d+)\s*:", row.get(field, "")))
    return found


def main() -> None:
    ids = reward_ids()
    item_icons = {}
    with (CONFIG / "item.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("ClassId", "").isdigit() and int(row["ClassId"]) in ids and row.get("Icon"):
                item_icons[int(row["ClassId"])] = PurePosixPath(row["Icon"]).name

    with zipfile.ZipFile(APK) as archive:
        manifest = parse_manifest(
            LIVE_MANIFEST.read_bytes() if LIVE_MANIFEST.exists() else archive.read(MANIFEST_ENTRY)
        )
        by_bundle = defaultdict(lambda: defaultdict(list))
        for asset in manifest.assets:
            stem = PurePosixPath(asset.asset_path).stem
            for item_id, icon_stem in item_icons.items():
                if stem == icon_stem:
                    by_bundle[asset.bundle_id][stem].append(item_id)

        names = archive.namelist()
        OUT.mkdir(parents=True, exist_ok=True)
        extracted = set()
        for bundle_id, wanted in by_bundle.items():
            bundle = manifest.bundles[bundle_id]
            filename = bundle.file_name(manifest.output_name_style)
            cached = LIVE_BUNDLES / filename
            entry = next((name for name in names if name.endswith("/" + filename)), None)
            if cached.exists():
                payload = cached.read_bytes()
            elif entry:
                payload = archive.read(entry)
            else:
                continue
            environment = UnityPy.load(decrypt_sxs_bundle(payload, bundle.encrypted))
            for obj in environment.objects:
                if obj.type.name != "Sprite":
                    continue
                sprite = obj.read()
                name = getattr(sprite, "name", getattr(sprite, "m_Name", ""))
                item_ids = wanted.get(name, [])
                if not item_ids:
                    continue
                image = sprite.image
                image.thumbnail((128, 128))
                for item_id in item_ids:
                    image.save(OUT / f"item_{item_id}.webp", "WEBP", quality=92, method=6)
                    extracted.add(item_id)

    print(f"Extracted {len(extracted)}/{len(ids)} Stellaris reward icons")
    missing = sorted(ids - extracted)
    if missing:
        print("Missing:", ", ".join(map(str, missing)))


if __name__ == "__main__":
    main()
