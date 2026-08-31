import csv
import json
import re
from pathlib import Path

CONFIG = Path(r"C:\tmp\sxs-live-config-85")
LANGUAGE = Path(r"C:\tmp\sxs-loadout-extract\en_us\Language\en_US\text.g.csv")
OUTPUT = Path(__file__).resolve().parents[1] / "sxs-stellaris" / "data.js"

RELIC_EFFECTS = {
    61211: ("Wind Affinity", "EXP Gain Boost"),
    61518: ("Light Aegis", "PvE DMG RES"),
    61617: ("Dark Affinity", "PvP Bonus DMG"),
    61618: ("Dark Aegis", "PvP DMG RES"),
    61718: ("Wind Affinity", "PvE Bonus DMG"),
    61817: ("Water Affinity", "PvE Bonus DMG"),
    61818: ("Water Aegis", "PvE DMG RES"),
    61917: ("Fire Affinity", "PvP Bonus DMG"),
    61918: ("Fire Aegis", "PvP DMG RES"),
}

# Hero's Handbook is awarded before its dedicated shard milestones. Each shard
# bundle exactly matches the next star-up cost in the extracted Gold relic table.
HANDBOOK_STAR_STEPS = {
    60: (0, 1, 5, 7),
    120: (1, 2, 7, 9),
    180: (2, 3, 9, 11),
    240: (3, 4, 11, 13),
    300: (4, 5, 13, 15),
    360: (5, 6, 15, 20),
}


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

    relics = {}
    relic_piece_to_parent = {}
    with (CONFIG / "treasure.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            relic_id = row.get("ClassId", "")
            piece_id = row.get("TreasurePieceId", "")
            if not relic_id.isdigit():
                continue
            relic_id = int(relic_id)
            relics[relic_id] = row
            if piece_id.isdigit():
                relic_piece_to_parent[int(piece_id)] = relic_id

    def reward(item_id, amount):
        meta = items.get(item_id, {})
        name = language.get(f"item_{item_id}_name", f"Item {item_id}")
        description = language.get(f"item_{item_id}_func_desc", "")
        icon = meta.get("icon", "")
        if "ItemIcon/Appearance/" in icon or "Visage Wardrobe" in description:
            kind = "Appearance"
        elif "ItemIcon/Food/" in icon:
            kind = "Dish"
        elif item_id in relics:
            kind = "Relic"
            effects = RELIC_EFFECTS.get(item_id)
            if effects:
                if item_id == 61211:
                    description = (f"Gold relic — grants {effects[0]} and {effects[1]}. "
                                   "At Lv1 it starts at 2% Wind Affinity and 5% EXP Gain Boost; "
                                   "at 6★ those values become 4% and 20%.")
                else:
                    description = (f"Relic — grants {effects[0]} and {effects[1]}. "
                                   "At Lv1 its extracted base effects are 1.2% elemental Affinity/Aegis "
                                   "and 4.8% PvE/PvP damage bonus or resistance.")
        elif item_id in relic_piece_to_parent:
            kind = "Relic shard"
            parent_id = relic_piece_to_parent[item_id]
            parent_name = language.get(f"item_{parent_id}_name", f"Relic {parent_id}")
            step = HANDBOOK_STAR_STEPS.get(amount) if parent_id == 61211 else None
            if step:
                from_star, to_star, before, after = step
                description = (f"Evolution material for the {parent_name} relic. This bundle covers "
                               f"{from_star}★ → {to_star}★ and raises EXP Gain Boost from "
                               f"{before}% to {after}% at the same relic level.")
            else:
                description = f"Evolution material for the {parent_name} relic."
        elif "ItemIcon/Treasure/" in icon:
            kind = "Relic material"
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
