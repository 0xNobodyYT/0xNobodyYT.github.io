"""Generate compact browser data for the Sword x Staff build calculator.

Source files are extracted client configuration. The generated file is committed so
GitHub Pages never needs access to the local extraction directory.
"""
from __future__ import annotations

import ast
import csv
import json
import re
from pathlib import Path

ROOT = Path(r"C:\tmp\sxs-config-155937")
LANG = Path(r"C:\tmp\sxs-loadout-extract\en_us\Language\en_US\text.g.csv")
OUT = Path(__file__).resolve().parents[1] / "sxs-loadout-builder" / "combat-data.js"


def rows(name: str):
    with (ROOT / name).open(encoding="utf-8-sig", newline="") as handle:
        return [row for row in csv.DictReader(handle) if row and not str(next(iter(row.values()), "")).startswith("#")]


def number(value):
    if value in (None, ""):
        return 0
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return 0


def loose_dict(value: str):
    if not value:
        return {}
    text = value.strip().replace("'", '"')
    text = re.sub(r"([{,])\s*([A-Za-z][A-Za-z0-9_]*)\s*:", r'\1"\2":', text)
    text = re.sub(r",\s*}", "}", text)
    try:
        return json.loads(text)
    except Exception:
        return {}


qualities = [
    {"raw": "White", "name": "Common", "rankId": 1210, "affixes": 0, "roll": [70, 80]},
    {"raw": "Blue", "name": "Rare", "rankId": 1211, "affixes": 2, "roll": [70, 90]},
    {"raw": "Purple", "name": "Epic", "rankId": 1212, "affixes": 3, "roll": [80, 100]},
    {"raw": "Orange", "name": "Legendary", "rankId": 1213, "affixes": 4, "roll": [80, 115]},
    {"raw": "Gold", "name": "Mythic", "rankId": 1214, "affixes": 4, "roll": [80, 125]},
    {"raw": "Red", "name": "Immortal", "rankId": 1215, "affixes": 4, "roll": [80, 125]},
    {"raw": "Rainbow", "name": "Divine", "rankId": 1216, "affixes": 4, "roll": [80, 125]},
]

base_stats = {}
for row in rows("level_prop_battle.csv"):
    if row.get("class_id") == "1":
        base_stats[row["level"]] = {key: number(row[key]) for key in ("BaseMaxHp", "BaseAttack", "BaseDefence", "BaseSpeed")}

professions = {}
for row in rows("profession_base.csv"):
    if row.get("Profession") not in ("", "None"):
        professions[row["Profession"]] = {
            "rank": number(row["Rank"]),
            "levelPropId": number(row["LevelPropId"]),
            "features": loose_dict(row.get("FeatureProps", "")),
        }

profession_levels = {}
for row in rows("level_prop_profession.csv"):
    if row.get("class_id", "").isdigit():
        profession_levels.setdefault(row["class_id"], {})[row["level"]] = {
            key: number(row.get(key)) for key in ("MaxHp", "Attack", "Defence", "Speed", "BaseMaxHpPercent", "BaseAttackPercent", "BaseDefencePercent", "BaseSpeedPercent")
        }

rank_rows = {(row["class_id"], row["level"]): row for row in rows("level_prop_equip_rank.csv") if row.get("class_id", "").isdigit()}
upgrade_rows = {row["level"]: row for row in rows("level_prop_equip_upgrade.csv") if row.get("class_id") == "1200"}

curve_files = {
    "main": rows("level_prop_equip_main.csv"),
    "second": rows("level_prop_equip_second.csv"),
    "other": rows("level_prop_equip_other.csv"),
    "blessMain": rows("level_prop_equip_bless_level.csv"),
    "blessSecond": rows("level_prop_equip_second_bless_level.csv"),
    "blessOther": rows("level_prop_equip_other_bless_level.csv"),
}
curve_maps = {name: {(r["class_id"], r["level"]): r for r in values if r.get("class_id", "").isdigit()} for name, values in curve_files.items()}

templates = {
    100: {"main": 1006, "second": 1056, "other": 1102, "blessMain": 1153, "blessSecond": 1153, "blessOther": 1174},
    130: {"main": 1008, "second": 1058, "other": 1103, "blessMain": 1154, "blessSecond": 1254, "blessOther": 1175},
    160: {"main": 1010, "second": 1060, "other": 1104, "blessMain": 1155, "blessSecond": 1299, "blessOther": 1176},
    190: {"main": 1012, "second": 1062, "other": 1105, "blessMain": 1156, "blessSecond": 1256, "blessOther": 1177},
    220: {"main": 1014, "second": 1064, "other": 1106, "blessMain": 1157, "blessSecond": 1257, "blessOther": 1178},
}
stat_keys = ["MaxHp", "Attack", "Defence", "Speed", "EffectDodge", "EffectRate", "ElementMaster", "ElementResistance", "KongFuMaster", "KongFuResistance", "CritRatePercentValue", "CritAvoidPercentValue", "BlockPercentValue", "BlockAvoidPercentValue", "BaseMaxHpPercent", "BaseAttackPercent", "BaseDefencePercent", "BaseSpeedPercent", "CritRatePercent", "CritAvoidPercent", "CritPowerPercent", "BlockPercent", "BlockAvoidPercent", "DmgAddPercent", "DmgReducePercent", "CureAddPercent"]

gear = {"templates": {}, "upgrade": {}, "rank": {}}
for level, cfg in templates.items():
    record = {}
    for kind, class_id in cfg.items():
        lookup_level = str(level) if not kind.startswith("bless") else "0"
        row = curve_maps[kind].get((str(class_id), lookup_level), {})
        record[kind] = {key: number(row.get(key)) for key in stat_keys if number(row.get(key))}
        record[kind + "Id"] = class_id
    gear["templates"][str(level)] = record
for level, row in upgrade_rows.items():
    gear["upgrade"][level] = {key: number(row.get(key)) for key in stat_keys if number(row.get(key))}
for q in qualities:
    row = rank_rows.get((str(q["rankId"]), "1"), {})
    gear["rank"][q["raw"]] = {key: number(row.get(key)) for key in stat_keys if number(row.get(key))}

# Blessing curves are selected by the original item template and evaluated at the
# season/blessing level entered by the user.
gear["bless"] = {}
for level, cfg in templates.items():
    result = {}
    for kind in ("blessMain", "blessSecond", "blessOther"):
        cid = str(cfg[kind])
        result[kind] = {}
        # A few carried-forward items deliberately point their secondary stat at
        # a main-stat blessing curve (for example the Lv100 Serene Sakura Staff).
        # Search all blessing tables and keep the first table containing the ID.
        sources = [curve_maps[kind], curve_maps["blessMain"], curve_maps["blessSecond"], curve_maps["blessOther"]]
        source = next((candidate for candidate in sources if any(class_id == cid for class_id, _ in candidate)), {})
        for (class_id, bless_level), row in source.items():
            if class_id == cid:
                result[kind][bless_level] = {key: number(row.get(key)) for key in stat_keys if number(row.get(key))}
    gear["bless"][str(level)] = result

props_by_id = {row["Id"]: row.get("Props", "") for row in rows("equip_attributes_props.csv")}
gems = {}
for row in rows("gem.csv"):
    if not row.get("ClassId", "").isdigit():
        continue
    gem_id = int(row["ClassId"])
    # The first contiguous 15 IDs are the universal T1-T15 series; later IDs are regional duplicates.
    base = gem_id % 100
    if not 1 <= base <= 15:
        continue
    gem_type = row["GemType"]
    prop_text = props_by_id.get(row.get("SpecialPropId", ""), "")
    parsed = {}
    for key, value in re.findall(r"([A-Za-z][A-Za-z0-9_]*)\s*:\s*(-?\d+)", prop_text):
        parsed[key] = int(value)
    gems.setdefault(gem_type, {"positions": ast.literal_eval(row["InlayEquipPos"]), "tiers": {}})["tiers"][str(base)] = parsed

entity_props = {row["EntityId"]: row for row in rows("entity_prop_skill.csv")}
rank_props = {}
for row in rows("level_prop_skill.csv"):
    rank_props.setdefault(row["class_id"], {})[row["level"]] = row
status_props = {row["EntityId"]: row for row in rows("entity_prop_status.csv")}
status_rank_props = {}
for row in rows("level_prop_status.csv"):
    status_rank_props.setdefault(row["class_id"], {})[row["level"]] = row

skill_groups = {}
used_fixed_curve_ids = set()
for row in rows("entity_prop_group_level.csv"):
    group_id, sub_rank, curve_id = row.get("GroupId"), row.get("SubRank"), row.get("LevelPropId")
    if group_id and sub_rank and curve_id:
        skill_groups.setdefault(group_id, {})[sub_rank] = curve_id
        used_fixed_curve_ids.add(curve_id)

with LANG.open(encoding="utf-8-sig", newline="") as handle:
    language = {row[0]: row[1] for row in csv.reader(handle) if len(row) >= 2}
combat_ranks = [
    {"raw": sub_rank, "name": language.get(f"SubRank.{sub_rank}", sub_rank)}
    for sub_rank in skill_groups.get("1", {})
]

skill_fixed_curves = {}
for row in rows("level_prop_skill_fixed_prop.csv"):
    if row.get("class_id") in used_fixed_curve_ids and row.get("level", "").isdigit():
        skill_fixed_curves.setdefault(row["class_id"], {})[row["level"]] = {
            key: number(row.get(key))
            for key in ("SkillFixedAttack1", "SkillFixedAttack2", "SkillFixedAttack3", "SkillFixedAttack4", "SkillFixedCure", "SkillFixedShield")
            if number(row.get(key))
        }

skills = {}
for row in rows("skill.csv"):
    if not row.get("ClassId", "").isdigit():
        continue
    try:
        entities = ast.literal_eval(row.get("ViewPropEntities") or "[]")
    except Exception:
        entities = []
    view_entities = [entity_props[str(eid)] for eid in entities if str(eid) in entity_props]
    primary_entity = entity_props.get(row.get("EcEntityId")) or (view_entities[0] if view_entities else None)
    if not primary_entity:
        continue
    effect_fields = ("SkillAttack1", "SkillAttack2", "SkillAttack3", "SkillAttack4", "SkillCureByHp", "SkillCureByAttack", "SkillCureByTargetHp", "SkillFixedShield", "SkillFixedCure")
    entity = next((candidate for candidate in view_entities if any(number(candidate.get(key)) for key in effect_fields)), primary_entity)
    rank_id = entity.get("RankPropId")
    ranks = rank_props.get(rank_id, {})
    effects = {}
    for rank in range(1, 35):
        rr = ranks.get(str(rank))
        if not rr:
            continue
        item = {}
        for prop in ("SkillAttack1", "SkillAttack2", "SkillAttack3", "SkillAttack4", "SkillFixedAttack1", "SkillFixedAttack2", "SkillFixedAttack3", "SkillFixedAttack4", "SkillCureByHp", "SkillCureByAttack", "SkillCureByTargetHp", "SkillFixedShield", "SkillFixedCure", "BreakResilience", "SkillDmgAddPerByTargetHp", "SkillDmgAddPerByLargeTarget", "OnceHitHemophagiaPer", "DistanceAddDmgPercent"):
            rank_value = number(rr.get(prop)) or 10000
            factor = number(entity.get(prop))
            if factor:
                item[prop] = round(rank_value * factor / 10000)
        if item:
            effects[str(rank)] = item
    cd_entity = next((candidate for candidate in [primary_entity, *view_entities] if number(candidate.get("CD"))), None)
    status_effects = []
    status_fields = ("ShieldByTargetHp", "ShieldByDefence", "ShieldByConvertedCurHp", "SkillFixedShield")
    for status in (status_props[str(eid)] for eid in entities if str(eid) in status_props):
        if not any(number(status.get(key)) for key in status_fields):
            continue
        status_ranks = status_rank_props.get(status.get("RankPropId"), {})
        ranked_effects = {}
        for rank in range(1, 35):
            rr = status_ranks.get(str(rank), {})
            item = {}
            for prop in status_fields:
                factor = number(status.get(prop))
                if factor:
                    rank_value = number(rr.get(prop)) or 10000
                    item[prop] = round(rank_value * factor / 10000)
            if item:
                ranked_effects[str(rank)] = item
        if ranked_effects:
            status_effects.append({
                "effects": ranked_effects,
                "groupId": status.get("GroupLevelPropId") or entity.get("GroupLevelPropId") or "",
            })
    skills[row["ClassId"]] = {
        "effects": effects,
        "cd": number(cd_entity.get("CD")) / 10000 if cd_entity else 0,
        "groupId": entity.get("GroupLevelPropId") or "",
        "statusEffects": status_effects,
    }

payload = {
    "version": 1,
    "qualities": qualities,
    "baseStats": base_stats,
    "professions": professions,
    "professionLevels": profession_levels,
    "gear": gear,
    "gems": gems,
    "skills": skills,
    "combatRanks": combat_ranks,
    "skillGroups": skill_groups,
    "skillFixedCurves": skill_fixed_curves,
}
OUT.write_text("window.SXS_COMBAT_DATA=" + json.dumps(payload, separators=(",", ":")) + ";\n", encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")
