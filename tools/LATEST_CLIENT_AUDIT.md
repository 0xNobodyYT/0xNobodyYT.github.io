# Latest Sword x Staff client audit

Audit date: 2026-11-24

## Client checked

| Field | Value |
| --- | --- |
| Android package | `com.zjcs.android.us` |
| Installed APK version code | `156940` |
| Current YooAsset package | `153_156959` |
| Current resource snapshot | `202611202141153` |
| Previous YooAsset package | `150_156940` |
| Previous resource snapshot | `202611200130150` |

The manifests and cached bundles were read from the running Global client in BlueStacks. Package 153 was compared directly with the adjacent package 150 manifests and extracted data assets.

## Adjacent-release diff

| Package | Result |
| --- | --- |
| `DefaultPackage` | 21,059 to 21,068 bundles; nine Christmas localization bundles added, no removals, seven existing bundles changed |
| `Config` | 42 bundles; only `config_assets_config_luban.bundle` changed |
| `ConfigRawFile` | 16 bundles; seven language/localization files changed |
| `HybridCLR` | 23 bundles; nine runtime/metadata files changed |

Both Config bundles were unpacked and all 452 TextAssets were compared. Only `mail_send_timer.g.bin` and `questionnaire.g.bin` changed. No season, progression, class, skill, Fantomon, companion, equipment, formula, or event gameplay table changed between packages 150 and 153.

The presentation changes include the Christmas activity prefab, Slime activity prefab, Chinese Odyssey UI assets, Season 4 Russian logo, and battle-royale fight panel. Nine localized Christmas appearance bundles were added.

## Calendar impact

The November 24 client update notice confirms:

- **Sword x Staff × That Time I Got Reincarnated as a Slime** opens December 1.
- **Chic Chores** returns December 7.
- **Academy Fantasia** opens December 12.
- **Starfrost Fete** opens December 18.
- **Asuran Wraith** returns December 21.

The Slime collaboration and three Visage packs were already represented in the calendar. The Slime title was updated to the official English name and the missing Starfrost Fete date was added.

## Tool impact

| Tool | Package 153 action |
| --- | --- |
| Season Planner | No progression, scoring, upgrade, EXP, or Realm-yield table change |
| Server Calendar | Confirmed Slime event name/date and added Starfrost Fete on December 18 |
| Loadout Builder | No class, skill, equipment, formula, or Fantomon gameplay change |
| Skills Conversion | No class-change pool change |
| Skills Overview | No numeric skill/Charm curve change |
| Fantomons | No roster, form, skill, grade, or stat change |
| Stellaris | No milestone, reward-bundle, or pricing change |
| Wardrobe Viewer | Christmas appearance presentation assets added; gameplay/acquisition tables unchanged in this adjacent release |
| Companions | No roster, bonus, friendship, or profile change |
| World Map | No region, unlock, loot, or wheel configuration change |
| Community Tier List | No class roster or tier change |

This audit records only data that is present in the current client; no future gameplay values were inferred from presentation assets.
