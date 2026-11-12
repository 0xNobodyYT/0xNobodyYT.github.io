# Latest Sword x Staff client audit

Audit date: 2026-11-12

## Client checked

| Field | Value |
| --- | --- |
| Android package | `com.zjcs.android.us` |
| APK version code | `156259` |
| Current YooAsset package | `137_156823` |
| Current resource snapshot | `202611111409137` |
| Previous YooAsset package | `134_156699` |
| Previous resource snapshot | `202610291942134` |

The manifests and cached bundles were read from the running Global client in BlueStacks. Package 137 was compared directly with the adjacent package 134 manifests and data assets.

## Adjacent-release diff

| Package | Result |
| --- | --- |
| `DefaultPackage` | 20,686 bundles in both releases; no additions or removals; 487 rebuilt or changed bundles |
| `Config` | 50 bundles; only `config_assets_config_luban.bundle` changed |
| `ConfigRawFile` | No changed bundles |
| `HybridCLR` | Four runtime/metadata bundles changed |

The changed Config bundle was unpacked and all 343 Unity objects were compared. Only `general_activity_shop.g` differs, and its 13,859-byte payload has exactly one changed byte in the `Halloween26` shop record. The season, progression, class, skill, Fantomon, companion, map, wardrobe-acquisition, Stellaris, and calendar configuration assets are byte-identical to package 134.

The changed presentation bundles mainly contain `linkage08` appearance atlases, Slime-themed blind-box/emoji art, NPC presentation assets, the Pet item-icon atlas, and `map_10`. These are presentation updates backed by unchanged gameplay tables; they do not add a Season 8 ruleset.

## Season availability

The live `astrological_season_config.g` table contains **seven rows**:

- Seasons 1–6 are unchanged.
- Season 7 is present as `Godtouched2`, with a Lv280 scoring baseline, 200 fixed Primostars, 3 progression points per Primostar, and scoring weights of Character 100, Gear 20, Relics 35, Skills 6, and Fantomons 12.
- There is **no Season 8 row**. No Season 8 baseline, Primostar conversion, fixed award, scoring weights, EXP curve, upgrade curve, Realm yield, event schedule, class tier, skill pool, or other Season 8-specific gameplay configuration is available in the current Global client.

Season 8 values must not be inferred from the rank enum or extrapolated from Season 7. `Godtouched3` exists as a generic rank enum/reference in some shared systems, but it is not an active Season 8 configuration.

## Tool impact

| Tool | Package 137 action |
| --- | --- |
| Season Planner | No Season 8 data to add; existing S1–6 production values remain unchanged |
| Server Calendar | No Season 8 schedule or server-relative milestones present |
| Loadout Builder | No Season 8 class, skill, equipment, formula, or Fantomon table change |
| Skills Conversion | No class-change pool change |
| Skills Overview | No technique, Charm, rank, curve, or description change |
| Fantomons | Pet icon atlas rebuilt, but roster/forms/skills/grades/stats are unchanged |
| Stellaris | No milestone, reward-bundle, or pricing change |
| Wardrobe Viewer | New presentation atlases exist, but the appearance/acquisition tables are unchanged |
| Companions | Some NPC presentation bundles changed; roster, bonuses, friendship data, and profiles are unchanged |
| World Map | `map_10` presentation bundle changed; region/unlock/loot/wheel configuration is unchanged |
| Community Tier List | No class roster or tier change |

No user-facing values were changed or guessed merely to label the tools as Season 8-ready. The next live manifests should be compared against `137_156823`; Season 8 support can be added once an eighth season row and its dependent progression tables actually ship.
