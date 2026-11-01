# Latest Sword x Staff client audit

Audit date: 2026-11-01

## Client checked

| Field | Value |
| --- | --- |
| Android package | `com.zjcs.android.us` |
| APK version code | `156259` |
| Current YooAsset package | `134_156699` |
| Current resource snapshot | `202610291942134` |
| Previous YooAsset package | `131_156640` |
| Previous resource snapshot | `202610231055131` |

The manifests and changed bundles were read from the running Global client in BlueStacks. The previous live bundles were downloaded from the resource snapshot recorded by the client so that the comparison uses two adjacent production releases.

## Adjacent-release diff

| Package | Result |
| --- | --- |
| `DefaultPackage` | 20,686 bundles; no added, removed, or changed bundles |
| `Config` | 50 bundles; only `config_assets_config.bundle` and `config_assets_config_luban.bundle` changed |
| `ConfigRawFile` | Seven localized text bundles changed |
| `HybridCLR` | Runtime assemblies and metadata changed |

The two changed Config bundles were unpacked and compared asset by asset:

- `config_assets_config.bundle`: 128 assets; only `questionnaire_web` changed (1,694 to 1,846 bytes).
- `config_assets_config_luban.bundle`: 24 assets; no contained data asset changed.

This means package 134 contains no new or modified gameplay tables. The localization changes accompany the questionnaire/runtime update and do not add tool data.

## Tool impact

| Tool | Data checked | Package 134 action |
| --- | --- | --- |
| Season Planner | Season rules, scoring, EXP, upgrade costs, Realm yields | No data change |
| Server Calendar | Event schedules, server-relative milestones, rewards | No data change; provenance note updated |
| Loadout Builder | Classes, skills, equipment, Fantomons, formulas | No data change |
| Skills Conversion | Class-change pools and base grades | No data change |
| Skills Overview | Techniques, Charms, ranks, curves, descriptions | No data change |
| Fantomons | Roster, forms, skills, grades, stats | No data change |
| Stellaris | Milestones, reward bundles, pricing scale | No data change |
| Wardrobe Viewer | Cosmetics, models, Spine attachments, acquisition data | No asset or table change |
| Companions | Roster, friendship curves, bonuses, profiles | No data change |
| World Map | Regions, unlocks, loot, wheels | No asset or table change |
| Community Tier List | Class roster | No class data change |

No user-facing values were changed merely to create an update. Future client audits should compare the next live manifests against `134_156699` and regenerate only the tools whose source tables actually differ.
