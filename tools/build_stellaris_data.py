import csv
import json
import re
from pathlib import Path

CONFIG = Path(r"C:\tmp\sxs-live-config-85")
LANGUAGE = Path(r"C:\tmp\sxs-loadout-extract\en_us\Language\en_US\text.g.csv")
OUTPUT = Path(__file__).resolve().parents[1] / "sxs-stellaris" / "data.js"


def dictionary(value):
    return {key: int(amount) for key, amount in re.findall(r"([A-Za-z]+|\d+)\s*:\s*(\d+)", value or "")}


def main():
    language = {}
    with LANGUAGE.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) >= 2:
                language[row[0]] = row[1]

    items = {}
    with (CONFIG / "item.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            item_id = row.get("ClassId", "")
            if not item_id.isdigit():
                continue
            items[int(item_id)] = {
                "quality": row.get("Quality") or "",
                "icon": row.get("Icon") or "",
            }

    def reward(item_id, amount):
        meta = items.get(item_id, {})
        name = language.get(f"item_{item_id}_name", f"Item {item_id}")
        description = language.get(f"item_{item_id}_func_desc", "")
        icon = meta.get("icon", "")
        if "ItemIcon/Appearance/" in icon or "Visage Wardrobe" in description:
            kind = "Appearance"
        elif "ItemIcon/Food/" in icon:
            kind = "Dish"
        elif "ItemIcon/Treasure/" in icon:
            kind = "Charm"
        elif "Badge" in name:
            kind = "Badge"
        elif "Fantomons" in description or "Fantomon" in name:
            kind = "Fantomon"
        elif "ItemIcon/Materials/" in icon:
            kind = "Material"
        elif "Gift" in name or "Box/" in icon:
            kind = "Gift"
        else:
            kind = "Item"
        return {
            "id": item_id,
            "amount": amount,
            "name": name,
            "description": description,
            "quality": meta.get("quality", ""),
            "icon": icon,
            "kind": kind,
            "webIcon": (OUTPUT.parent / "assets" / f"item_{item_id}.webp").exists(),
        }

    tiers = []
    with (CONFIG / "accumulated_pay_award.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if not row.get("Level", "").isdigit():
                continue
            core = dictionary(row.get("CoreAward"))
            extras = dictionary(row.get("SubAwards"))
            tiers.append({
                "level": int(row["Level"]),
                "group": int(row["Group"]),
                "major": row["IsBigLevel"].upper() == "TRUE",
                "thresholds": dictionary(row["StartValueRequire"]),
                "core": [reward(int(item_id), amount) for item_id, amount in core.items()],
                "extras": [reward(int(item_id), amount) for item_id, amount in extras.items()],
            })

    payload = {
        "configVersion": 85,
        "currencies": {
            "USD": {"label": "US Dollar", "symbol": "$", "divisor": 100, "decimals": 2},
            "CNY": {"label": "Chinese Yuan", "symbol": "¥", "divisor": 1, "decimals": 0},
            "JPY": {"label": "Japanese Yen", "symbol": "¥", "divisor": 1, "decimals": 0},
            "KRW": {"label": "South Korean Won", "symbol": "₩", "divisor": 1, "decimals": 0},
        },
        "tiers": tiers,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("window.STELLARIS_DATA=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"Wrote {len(tiers)} Stellaris tiers to {OUTPUT}")


if __name__ == "__main__":
    main()
