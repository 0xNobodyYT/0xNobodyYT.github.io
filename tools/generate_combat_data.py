"""Generate compact browser data for the Sword x Staff build calculator.

Source files are extracted client configuration. The generated file is committed so
GitHub Pages never needs access to the local extraction directory.
"""
from __future__ import annotations

import ast
import csv
import json
import os
import re
from pathlib import Path

ROOT = Path(r"C:\tmp\sxs-live-config-85")
LANG = Path(r"C:\tmp\sxs-loadout-extract\en_us\Language\en_US\text.g.csv")
OUT = Path(os.environ.get("SXS_COMBAT_OUT") or (Path(__file__).resolve().parents[1] / "sxs-loadout-builder" / "combat-data.js"))
ENTITY_LINKS = Path(__file__).with_name("skill-entity-links.json")


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
    {"raw": "Red", "name": "Divine", "rankId": 1215, "affixes": 4, "roll": [80, 125]},
    {"raw": "Rainbow", "name": "Immortal", "rankId": 1216, "affixes": 4, "roll": [80, 125]},
]

base_stats = {}
for row in rows("level_prop_battle.csv"):
    if row.get("class_id") == "1":
        base_stats[row["level"]] = {key: number(row[key]) for key in ("BaseMaxHp", "BaseAttack", "BaseDefence", "BaseSpeed")}

# The player entity's always-on advanced combat defaults live in a separate
# class from the per-level main-stat curve.
base_innate = {}
for row in rows("level_prop_battle.csv"):
    if row.get("class_id") == "50" and row.get("level") == "1":
        base_innate = {
            key: number(row.get(key))
            for key in ("CritPowerPercent", "BlockValuePercent")
            if number(row.get(key))
        }

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

with LANG.open(encoding="utf-8-sig", newline="") as handle:
    language = {row[0]: row[1] for row in csv.reader(handle) if len(row) >= 2}

props_by_id = {row["Id"]: row.get("Props", "") for row in rows("equip_attributes_props.csv")}
equipment_sets = []
for row in rows("equip_suit.csv"):
    if not row.get("SuitId", "").isdigit():
        continue
    try:
        attrs = ast.literal_eval((row.get("SuitAttributes") or "{}").strip())
    except Exception:
        attrs = {}
    bonuses = {}
    for pieces, attr_id in attrs.items():
        parsed = {}
        for key, value in re.findall(r"([A-Za-z][A-Za-z0-9_]*)\s*:\s*(-?\d+)", props_by_id.get(str(attr_id), "")):
            parsed[key] = int(value)
        if parsed:
            bonuses[str(pieces)] = parsed
    equipment_sets.append({
        "id": int(row["SuitId"]),
        "name": language.get(f"equip_suit_{row['SuitId']}", row.get("SuitName") or f"Set {row['SuitId']}"),
        "bonuses": bonuses,
    })
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
skill_source_rows = rows("skill.csv")
passive_source_rows = [row for row in skill_source_rows if loose_dict(row.get("PassivePropFactors", ""))]
used_passive_rank_ids = {row.get("PassiveRankPropId") for row in passive_source_rows}
used_passive_scale_ids = {row.get("PassiveRankFactorId") for row in passive_source_rows}
used_passive_group_ids = {row.get("PassiveGroupLevelPropId") for row in passive_source_rows}
rank_props = {}
for row in rows("level_prop_skill.csv"):
    rank_props.setdefault(row["class_id"], {})[row["level"]] = row
status_props = {row["EntityId"]: row for row in rows("entity_prop_status.csv")}
status_rank_props = {}
for row in rows("level_prop_status.csv"):
    status_rank_props.setdefault(row["class_id"], {})[row["level"]] = row

entity_graph = json.loads(ENTITY_LINKS.read_text(encoding="utf-8")) if ENTITY_LINKS.exists() else {"skills": {}, "links": {}}
summon_add_props = {row["class_id"]: row for row in rows("summon_monster_add_prop.csv") if row.get("class_id", "").isdigit()}
summon_rank_factors = {}
for summon_rank in rows("summon_rank_additive_factor.csv"):
    if summon_rank.get("rank_group", "").isdigit() and summon_rank.get("Rank", "").isdigit():
        summon_rank_factors.setdefault(summon_rank["rank_group"], {})[summon_rank["Rank"]] = summon_rank


def linked_entities(skill_id: str, fallback: set[int]) -> set[int]:
    """Return every nested entity referenced by a player skill prefab."""
    pending = list(entity_graph.get("skills", {}).get(skill_id, fallback))
    found = set()
    while pending:
        entity_id = int(pending.pop())
        if entity_id in found:
            continue
        found.add(entity_id)
        pending.extend(entity_graph.get("links", {}).get(str(entity_id), []))
    return found


# Numeric status properties exposed by reachable player-skill entities.  The
# metadata columns and boolean flags are deliberately excluded.
status_value_fields = {
    key
    for status in status_props.values()
    for key, value in status.items()
    if key not in {
        "EntityId", "Memo", "Memo2", "PvpPropScale", "RankPropId",
        "GroupLevelPropId", "SubRankPropId", "AffectedBySkillRank",
    }
    and number(value)
}

# Passive skills use three rank tables (percentage, main, and secondary
# properties), a rank multiplier, and a level/combat-rank fixed curve.  Keep
# the pieces separate in the browser payload so comparisons can be evaluated
# for the level and combat rank selected by the user.
passive_rank_props = {}
for filename in ("level_prop_skill_passive.csv", "level_prop_skill_passive_main.csv", "level_prop_skill_passive_other.csv"):
    for row in rows(filename):
        if row.get("class_id") not in used_passive_rank_ids or not row.get("level", "").isdigit():
            continue
        target = passive_rank_props.setdefault(row["class_id"], {}).setdefault(row["level"], {})
        target.update({key: number(value) for key, value in row.items() if key not in ("class_id", "level") and number(value)})

passive_rank_scales = {}
for row in rows("level_prop_skill_scale.csv"):
    if row.get("class_id") in used_passive_scale_ids and row.get("level", "").isdigit():
        passive_rank_scales.setdefault(row["class_id"], {})[row["level"]] = {
            key: number(value) for key, value in row.items()
            if key not in ("class_id", "level") and number(value)
        }

skill_groups = {}
used_fixed_curve_ids = set()
for row in rows("entity_prop_group_level.csv"):
    group_id, sub_rank, curve_id = row.get("GroupId"), row.get("SubRank"), row.get("LevelPropId")
    if group_id and sub_rank and curve_id:
        skill_groups.setdefault(group_id, {})[sub_rank] = curve_id
        used_fixed_curve_ids.add(curve_id)

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

passive_fields_by_group = {}
for source in passive_source_rows:
    passive_fields_by_group.setdefault(source.get("PassiveGroupLevelPropId"), set()).update(
        loose_dict(source.get("PassivePropFactors", ""))
    )
for skill_id, roots in entity_graph.get("skills", {}).items():
    for entity_id in linked_entities(skill_id, set(roots)):
        status = status_props.get(str(entity_id))
        if status and status.get("GroupLevelPropId"):
            passive_fields_by_group.setdefault(status["GroupLevelPropId"], set()).update(
                key for key in status_value_fields if number(status.get(key))
            )
used_passive_group_ids.update(passive_fields_by_group)
used_passive_curve_ids = {
    curve_id for group_id in used_passive_group_ids
    for curve_id in skill_groups.get(group_id, {}).values()
}
passive_fields_by_curve = {}
for group_id, fields in passive_fields_by_group.items():
    for curve_id in skill_groups.get(group_id, {}).values():
        passive_fields_by_curve.setdefault(curve_id, set()).update(fields)
skill_passive_curves = {}
for row in rows("level_prop_skill_all_fixed_prop.csv"):
    if row.get("class_id") in used_passive_curve_ids and row.get("level", "").isdigit():
        skill_passive_curves.setdefault(row["class_id"], {})[row["level"]] = {
            key: number(row.get(key)) for key in passive_fields_by_curve[row["class_id"]] if number(row.get(key))
        }

skills = {}
for row in skill_source_rows:
    if not row.get("ClassId", "").isdigit():
        continue
    try:
        entities = ast.literal_eval(row.get("ViewPropEntities") or "[]")
    except Exception:
        entities = []
    try:
        passive_entities = ast.literal_eval(row.get("PassiveStatusIdList") or "[]")
    except Exception:
        passive_entities = []
    root_entity_ids = {
        int(entity_id) for entity_id in [row.get("EcEntityId"), *entities, *passive_entities]
        if str(entity_id).isdigit() and int(entity_id) > 0
    }
    all_entity_ids = linked_entities(row["ClassId"], root_entity_ids)
    view_entities = [entity_props[str(eid)] for eid in entities if str(eid) in entity_props]
    primary_entity = entity_props.get(row.get("EcEntityId")) or (view_entities[0] if view_entities else None)
    passive_factors = {key: number(value) for key, value in loose_dict(row.get("PassivePropFactors", "")).items() if number(value)}
    if not primary_entity and not passive_factors and not any(str(entity_id) in status_props for entity_id in all_entity_ids):
        continue
    effect_fields = ("SkillAttack1", "SkillAttack2", "SkillAttack3", "SkillAttack4", "SkillCureByHp", "SkillCureByAttack", "SkillCureByTargetHp", "SkillFixedShield", "SkillFixedCure")
    entity = next((candidate for candidate in view_entities if any(number(candidate.get(key)) for key in effect_fields)), primary_entity) or {}
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
    cd_entity = next((candidate for candidate in [primary_entity, *view_entities] if candidate and number(candidate.get("CD"))), None)
    status_effects = []
    for status in (status_props[str(eid)] for eid in all_entity_ids if str(eid) in status_props):
        active_fields = [key for key in status_value_fields if number(status.get(key))]
        if not active_fields:
            continue
        status_ranks = status_rank_props.get(status.get("RankPropId"), {})
        ranked_effects = {}
        for rank in range(1, 35):
            rr = status_ranks.get(str(rank), {})
            item = {}
            for prop in active_fields:
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
                "entityId": number(status.get("EntityId")),
            })
    summon_effects = []
    summon_class_ids = {
        str(summon_id)
        for entity_id in all_entity_ids
        for summon_id in entity_graph.get("summons", {}).get(str(entity_id), [])
    }
    for summon_id in sorted(summon_class_ids, key=int):
        summon = summon_add_props.get(summon_id)
        if not summon:
            continue
        rank_factors = summon_rank_factors.get(summon.get("rank_group"), {})
        ranked = {}
        for rank in range(1, 35):
            rank_row = rank_factors.get(str(rank), {})
            item = {}
            for prop in ("MaxHp", "Attack", "Defence", "Speed"):
                factor = number(summon.get(prop))
                if factor:
                    item[prop] = round(factor * (number(rank_row.get(prop)) or 10000) / 10000)
            if item:
                ranked[str(rank)] = item
        if ranked:
            summon_effects.append({"classId": number(summon_id), "effects": ranked})
    skills[row["ClassId"]] = {
        "effects": effects,
        "cd": number(cd_entity.get("CD")) / 10000 if cd_entity else None,
        "groupId": entity.get("GroupLevelPropId") or "",
        "statusEffects": status_effects,
        "summons": summon_effects,
        "passive": {
            "rankPropId": row.get("PassiveRankPropId") or "",
            "groupId": row.get("PassiveGroupLevelPropId") or "",
            "rankFactorId": row.get("PassiveRankFactorId") or "",
            "factors": passive_factors,
        } if passive_factors else None,
    }

# Fantomon level curves and Baby/Adult attack skill sets. Evolution rows expose
# which support skill is used in baby form and which entity attacks unlock in
# adult form; the referenced skills already use the same rank/fixed curves as
# player skills above.
pet_level_curves = {}
for row in rows("level_prop_pet.csv"):
    if row.get("class_id", "").isdigit() and row.get("level", "").isdigit():
        pet_level_curves.setdefault(row["class_id"], {})[row["level"]] = {
            key: number(row.get(key)) for key in ("MaxHp", "Attack", "Defence", "Speed")
        }

pet_evolutions = {}
pet_forms = {}
for row in rows("pet_evolution.csv"):
    if not row.get("ClassId", "").isdigit():
        continue
    def id_list(field):
        try:
            return [int(value) for value in ast.literal_eval(row.get(field) or "[]")]
        except Exception:
            return []
    stage = row.get("EvolutionPhase") or "Childhood"
    icon_match = re.search(r"pet_(\d+)", row.get("PetIcon") or "")
    quality_match = re.search(r":\s*['\"]?([A-Za-z]+)", row.get("EvolutionSkillQuality") or "")
    pet_forms.setdefault(row["ClassId"], {})[stage] = {
        "iconId": int(icon_match.group(1)) if icon_match else 0,
        "level": number(row.get("EvolutionLevel")),
        "skillQuality": quality_match.group(1) if quality_match else "",
    }
    attacks = id_list("ActiveSkills") + id_list("SupportSkills")
    if stage == "Adulthood":
        attacks += id_list("EntityActiveSkills")
    pet_evolutions.setdefault(row["ClassId"], {})[stage] = list(dict.fromkeys(attacks))

pet_piece_qualities = {
    row["ClassId"]: row.get("Quality") or ""
    for row in rows("item.csv")
    if row.get("ClassId", "").isdigit()
}

pets = {}
for row in rows("pet.csv"):
    if not row.get("ClassId", "").isdigit():
        continue
    try:
        level_ids = ast.literal_eval(row.get("LevelPropId") or "{}")
    except Exception:
        level_ids = {}
    level_prop_id = str(next(iter(level_ids.values()), ""))
    stages = pet_evolutions.get(row["ClassId"], {})
    stage_skills = {}
    for stage in ("Childhood", "Adulthood"):
        # Support/status Fantomon skills can have all of their numeric scaling in
        # linked status or passive tables rather than the direct attack table.
        # Keep every referenced skill; the renderer resolves each linked source.
        ids = [skill_id for skill_id in stages.get(stage, []) if str(skill_id) in skills]
        stage_skills[stage] = [{
            "id": skill_id,
            "name": language.get(f"item_{skill_id}_name", f"Skill {skill_id}"),
            "description": re.sub(r"<[^>]+>", "", language.get(f"item_{skill_id}_func_desc", "")),
        } for skill_id in ids]
    pets[row["ClassId"]] = {
        "type": row.get("Type") or "",
        "minQuality": pet_piece_qualities.get(row.get("PetPieceId"), "") or row.get("GeneralPetPieceQuality") or "Purple",
        "levelPropId": level_prop_id,
        "levels": pet_level_curves.get(level_prop_id, {}),
        "stages": stage_skills,
        "forms": pet_forms.get(row["ClassId"], {}),
    }

payload = {
    "version": 1,
    "qualities": qualities,
    "baseStats": base_stats,
    "baseInnate": base_innate,
    "professions": professions,
    "professionLevels": profession_levels,
    "gear": gear,
    "gems": gems,
    "equipmentSets": equipment_sets,
    "skills": skills,
    "pets": pets,
    "combatRanks": combat_ranks,
    "skillGroups": skill_groups,
    "skillFixedCurves": skill_fixed_curves,
    "skillPassiveCurves": skill_passive_curves,
    "skillPassiveRankProps": passive_rank_props,
    "skillPassiveRankScales": passive_rank_scales,
}
OUT.write_text("window.SXS_COMBAT_DATA=" + json.dumps(payload, separators=(",", ":")) + ";\n", encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")
