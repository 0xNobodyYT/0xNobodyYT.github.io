# Sword x Staff Bot and AI System Findings

Last reviewed: September 25, 2026  
Scope: Static analysis of the extracted Global client configuration and decompiled client assemblies. No live-server manipulation, packet modification, or account automation was used.

## Executive summary

Sword x Staff does not use one universal type of bot. The client contains several separate systems that can all look like bots to a player:

1. Automatic matchmaking NPCs used to fill selected cooperative activities.
2. Borrowed real-player builds or player snapshots controlled by AI.
3. Arena guards that occupy real ladder positions.
4. Fixed guards used by systems such as Legion fights.
5. AI-managed player-shaped entities supported by the runtime.

Automatic NPC backfill is explicitly configured for Daily Dungeon, Secret Area, and Joint Strike. The normal client configuration begins this backfill after four minutes, not after one minute. At one minute, matchmaking instead widens the eligible real-player level range and continues global cross-server matching.

The cooperative matchmaking NPCs are not limited to Season 1 power. Their displayed level, rank, attributes, skills, and combat rating are calculated from runtime values supplied by the server. Their available curves extend into later-season level ranges.

Arena is the clearest confirmed use of bots in rankings: Arena positions and top-list entries can be owned by either a real player or a generated guard. These guards appear to be initial or filler ladder population rather than dynamically season-scaled endgame competitors.

## Confidence labels

- **Confirmed:** Directly represented by production configuration and client execution paths.
- **Supported:** The engine and network models support it, but the client does not prove that the live server automatically activates it.
- **Server-controlled:** The client contains the receiving/calculation path, while the live selection rule exists on the server and is unavailable in the APK.
- **Test-only:** Explicitly identified as debug, GM, or test functionality and not evidence of live production use.

## Matchmaking behavior

### Confirmed timing

The extracted `GameMatchInfo` configuration contains the following defaults:

| Setting | Value | Meaning |
|---|---:|---|
| Match check interval | 1 second | How frequently the matching state is checked |
| First NPC backfill timeout | 240 seconds | First attempt to add a resident/native NPC |
| Later NPC backfill timeout | 120 seconds | Interval for additional NPC backfill |
| Default wait time | 240 seconds | Normal maximum wait target |
| Maximum wait time | 240 seconds | Configured maximum matchmaking wait |

The default NPC preference order is:

1. Sage/Xianzhe
2. Knight/Huwei
3. Fighter/Doushi
4. Sorcerer/Shushi

The default fallback NPC IDs are `8402`, `8404`, `8406`, `8408`, `8409`, and `8411`. The same settings also reference assist buff ID `100` for strengthening matchmaking-assist NPCs.

### Real-player range expansion

`game_match_config.csv` expands the acceptable level range while the player waits. The configured checkpoints include:

| Waiting time | Approximate accepted level difference |
|---:|---:|
| 0 seconds | ±1 level |
| 10 seconds | ±3 levels |
| 20 seconds | ±5 levels |
| 40 seconds | ±10 levels |
| 60 seconds | ±20 levels |
| 90 seconds | ±30 levels |
| 120 seconds | ±40 levels |

These activities use global cross-server matching. Therefore, a powerful teammate appearing around the one-minute mark is more likely to be a real cross-server player admitted after the range widened than the normal automatic NPC fallback.

The live server may override packaged client values, so the four-minute timeout is strong evidence of the intended default behavior rather than proof that every production region always uses exactly the same timeout.

## Confirmed automatic NPC pools

Dedicated production NPC pools were found in `game_match_npc.csv` for:

| Activity | Configured target entries | Automatic NPC pool |
|---|---:|---|
| Daily Dungeon | 31 | Confirmed |
| Secret Area | 6 | Confirmed |
| Joint Strike | 51 | Confirmed |

Across those entries, 41 distinct NPC IDs are used. They correspond to named story or companion characters rather than generated fake player usernames.

No equivalent dedicated production NPC list was found for every other game mode. A mode being compatible with robot participants is not by itself proof that its live queue automatically creates them.

## Matchmaking NPC power and season scaling

Normal match-assist NPCs use runtime data including:

- NPC level
- NPC subrank
- Plane or season rank
- Profession
- Calculated combat rating

`NpcFightData` looks up the NPC's level-detail record and calculates battle attributes using the runtime level and subrank. Skill combat rating is also calculated from those runtime values. `PlayerLiteInfo` then wraps the NPC in player-like information for team and matchmaking UI while identifying it internally as a robot player.

All 41 distinct matchmaking NPC IDs have configured progression curves. The available ranges include approximately:

| Rank curve | Available level range |
|---|---:|
| Silver | Up to Lv170 |
| Gold | Up to Lv220 |
| Saint | Up to Lv400 |
| Legend | Up to Lv400 |
| Angel | Up to Lv999 |

This means their power is not permanently frozen at a Season 1 value. The server can supply a later-season level and rank, after which the client calculates the corresponding statistics and combat rating.

The exact rule the server uses to select an NPC's level relative to the party is server-side and cannot be recovered from the client alone.

## Game-mode support matrix

The game-mode configuration distinguishes between modes that require a real human and modes that do not. `NeedPlayer = false` means the engine permits the activity without a real player in every slot; it does not prove that production matchmaking always spawns bots there.

### Modes that do not require a real player in every slot

- Daily Dungeon
- Secret Area
- Void Fissure
- Demon Invasion
- Team Challenge 2v2
- Team Challenge 4v4
- Joint Strike
- Roadblock
- Explore Boss Team
- Battle Stele
- Activity Festival Boss
- Battle Royale
- Free Battle
- Activity Domain Boss
- Activity Domain Funny Boss
- Free exploration/None mode

### Modes explicitly configured to require real players

- Activity Game
- Hide and Seek
- Football Collision
- Double Kitchen

Some entries such as Roadblock, Explore Boss Team, and Activity Festival Boss are marked unused in `team_target.csv`, although assist or UI routes for related systems still exist elsewhere in the client.

## PvP findings

### Arena: confirmed guards in rankings

Arena is the strongest confirmed example of bots participating in a ranked system.

`ArenaRoleType` supports both `Guard` and `Player`. An Arena season position stores:

- Season ID
- Rank
- An owner that can be a real player or an Arena guard

Arena top-list responses and opponent records use the same owner abstraction, so generated guards can occupy real ladder positions, appear in opponent selections, and be returned in ranking lists.

`arena_guard_template.csv` contains approximately 500 numeric guard templates covering Warrior, Mage, Knight, Fighter, Sorcerer, and Sage lines. `arena_rank_template.csv` can seed ranks 1 through 5,000 with weighted guard templates.

These Arena templates are primarily early-game filler:

- Template levels run only to approximately Lv100.
- Guards seeded near the top use templates around Lv59/Bronze II.
- Lower seeded positions can use templates around Lv26.

Their battle properties and skill combat rating are calculated, but their source level and subrank come from fixed templates. The extracted client does not show these Arena guards automatically growing into Season 2 or later endgame opponents. They are expected to be displaced as real players populate the ladder.

### Other PvP modes

Team Challenge, Free Battle, and Battle Royale are robot-compatible at the engine and protocol level. Their result messages can represent robot participants. However, no dedicated production matchmaking NPC pool equivalent to Daily Dungeon, Secret Area, or Joint Strike was found for these modes.

Therefore:

- Arena guard use is confirmed.
- Automatic bot creation in other live PvP queues is supported but not proven by the client.
- Any activation rules may be controlled entirely by the server.

## Borrowed players and AI-managed player entities

The client contains a separate player-assist system represented by files and classes such as:

- `player_robot_invite.csv`
- `PlayerRobotInvite`
- `TeamInviteRobotPanel`
- `PlayerRobotAssistData`

It supports assist candidates for activities including Roadblock/Prop Gate, Secret Area, Explore Boss, Joint Strike, Activity Festival Boss, and NPC Adventure.

These candidates can include:

- Companion or story NPCs
- Stored information from real player builds
- Player-shaped entities operated by AI

Candidates can be sorted using combat rating and elemental properties. Consequently, a powerful AI-controlled teammate may be a stored copy of a real player's build rather than a fabricated bot account.

The runtime also has a distinct `IsAiManaged` state for player entities. This differs from the explicit `RobotPlayer` mode and allows a real-player-shaped entity to be treated as AI-managed. The trigger that enables this state is server-side. The client alone cannot prove whether it is used for disconnection takeover, borrowed helpers, offline snapshots, or several of those cases.

## Robot identity and rewards

The player model distinguishes:

- `RealPlayer`
- `RobotPlayer`
- Real-player-shaped entities marked `IsAiManaged`

Explicit robot players do not follow ordinary player persistence and reward paths. The client also suppresses some profile interactions, notifications, collection operations, and rewards for robot or assist actors.

Robot IDs can be generated by adding `1,000,000,000,000` to an underlying ID. IDs at or above that threshold can be recognized as robot IDs by the client.

## Fixed guard systems

### Legion/Guild fights

`legion_fight_guard_template.csv` contains 48 guard templates: 12 for each of Knight, Fighter, Sorcerer, and Sage. These are fixed around:

- Lv70
- Silver I
- Lv70 skills at rank 8

They are clear Season 1-style fixed guards and are not dynamically increased to later-season power by the template data.

### Multi-group rivalry or tournament guards

`multi_group_rivalry_guard_template.csv` contains 48 guard appearances and loadouts. Its runtime code can calculate base properties from a supplied level and subrank, allowing dynamic stat scaling. However, the configured skill loadouts remain at fixed Lv70/rank 8 values.

In the currently extracted `multi_group_rivalry_stage.csv`, the upper and lower guard IDs are blank and the stages use monsters. The client supports rivalry guards, but the current stage configuration does not prove that they are active in the live tournament.

## Test and debug systems that are not production proof

`player_template.csv` contains a small set of entries marked as robots, including Karl and "young lady" templates with levels up to approximately 150. It also contains:

- Four managed-AI/tester templates around Lv100
- Four matchmaking-function test players around Lv100

These rows are test, GM, legacy, or generic fixtures and should not be treated as proof that matching live users are present in production.

The debug client can also create fake matchmaking participants, choose a target, select template IDs and counts, and mark them as robots. That functionality is explicitly debug/GM tooling rather than evidence of normal matchmaking behavior.

## Broad protocol compatibility

Many activity result requests contain an `IsRobot` field, including Arena, Daily Dungeon, Team Challenge, Free Battle, Void Fissure, Secret Area, Joint Strike, Legion activities, exploration bosses, activity bosses, Demon Battlefield, NPC Adventure, and other modes.

This proves that the shared battle/result infrastructure can handle robot participants across many systems. It does not prove that every one of those systems automatically inserts bots during normal production play.

## Interpreting reports of powerful players joining after one minute

If a high-power teammate appears around one minute, the most likely explanations are:

1. A real cross-server player became eligible when the accepted level range widened at 60 seconds.
2. A borrowed or stored real-player build was supplied through an assist system.
3. A server-side rule differs from the packaged client defaults.

The normal automatic resident-NPC backfill is configured to begin after 240 seconds, making it a less likely explanation for a one-minute arrival.

Useful signs when observing this in-game include:

- A recognizable companion/story name and portrait suggests a matchmaking NPC.
- A normal player identity with unusually high power may be a real cross-server player or a stored player snapshot.
- Timing near exactly 60 seconds aligns with the matchmaking range expansion.
- Timing near four minutes aligns with the configured first NPC fallback.

These signs are indicators rather than absolute proof because the server controls the final participant assignment.

## What the client cannot establish

Static client analysis cannot definitively reveal:

- Current live-server timeout overrides
- The exact algorithm used to choose an NPC's level and power
- Whether a particular observed teammate was human at that moment
- The server trigger for `IsAiManaged`
- Whether bot-compatible PvP modes currently create bots in a specific region
- Current counts of real players versus guards in a live ladder

Those questions would require authorized server telemetry or controlled in-game observation. They should not be answered solely from the APK.

## Primary extracted sources reviewed

Configuration tables:

- `game_settings.csv`
- `game_match_config.csv`
- `game_match_npc.csv`
- `game_play_mode.csv`
- `team_target.csv`
- `npc_level_detail.csv`
- `arena_guard_template.csv`
- `arena_rank_template.csv`
- `legion_fight_guard_template.csv`
- `multi_group_rivalry_guard_template.csv`
- `multi_group_rivalry_stage.csv`
- `player_robot_invite.csv`
- `player_template.csv`

Relevant decompiled client models and paths included `NpcFightData`, `NpcTargetData`, `PlayerLiteInfo`, `GameMatchPlayerInfo`, `ArenaSeasonFightPosData`, Arena owner/opponent types, player robot-assist models, `EPlayerMode`, `IsAiManaged`, robot ID helpers, and game-end request models carrying `IsRobot`.

