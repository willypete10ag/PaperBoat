# B01 roster and lifecycle contracts

Owner approved architecture ADR0008 and B01 in ttyd64-port issues #8/#9.
Base: PaperBoat c133c85527b178854e35c1287726f955dc1c8ca8 (PR24).
Reference: TTYD64 b8d2058ea057b2dfc168f2d909a2a2ea0927ce17.
This branch is implementation work in progress, not native acceptance or merge
permission. PR25/524832099614aa8df6ef5aca5d35bb536ad938f6 remains paused.

## Identity, data and admission

Native partner IDs remain save indices. Source compact extra-partner battle
records put Bow in a different slot; never use their packed order as save IDs.
HP records, world presentation/recipient readiness and combat lifecycle readiness
are independent queries. Recruitment, saved mode, context/demo/Peach guards and
actor/NPC instance ownership still apply after a capability query succeeds.

| Partner | Native ID | HP data | World adapter | Combat adapter | Source battle home Y |
| --- | ---: | --- | --- | --- | ---: |
| Goombario | 1 | Yes | Existing | Existing | 0 |
| Kooper | 2 | Yes | Existing | Existing; independent flip state | 0 |
| Bombette | 3 | Yes | Existing | Existing | 0 |
| Parakarry | 4 | Yes | B01 | B01 flight lifecycle | 4 |
| Watt | 6 | Yes | Not admitted | Not admitted | 11 |
| Sushie | 7 | Yes | Not admitted | Not admitted | 0 |
| Lakilester | 8 | Yes | Not admitted | Not admitted | 4 |
| Bow | 9 | Yes | Not admitted | Not admitted | 9 |

None, Goompa (5), Goombaria (10), Twink (11) and out-of-range IDs have no HP
record or adapter. Source height data does not admit a partner. Native Vanilla
DMA heights stay unchanged. Per-file mode remains ADR0007; no process-global
prototype flag, new save schema, original struct change or item identity.

## Consumer map

- `ttyd64_rules.c`: source rank HP, HP-data compatibility, separate world/combat
  admission and source battle home Y. Invalid IDs short-circuit before indexing.
- `ttyd64_partner_hp.c`: live HP and snapshot ownership remain separate. Binding
  requires a ready combat adapter as well as the existing context/mode/instance
  guards. Damage load/store, modifiers/status, death scheduling, turns, team
  targeting and battle recovery continue to require the bound current actor.
- `world_use_item.c`, `world/partners.c`, `world/menus.c`: world-ready recruited
  identities, then item/context policy and current NPC ownership. World food
  can restore zero HP; battle ordinary food requires a living active actor.
- `pause/pause_partners.c`, `8a860_len_3f30.c`: world/pause/list readiness instead
  of treating a stored HP record as proof of a presentation adapter.
- `battle/standard_events.c`: native animation descriptors for admitted actors.
  Existing ground death/revival waits and poses remain; a flying adapter lands
  before collapse, retains its dead floor pose on rebind, and recovers its source
  home height. The explicit DEFEAT scheduler and null-handler fallback remain.
- `battle/partner/parakarry.c`: death event, dead-pose/idle protection, no Vanilla
  KO drop on HP reactions, source recovery height, and dead celebration/flee
  protection. Vanilla scripts remain selected outside bound saved-mode combat.

## Source-backed Parakarry slice

`globals/patch/Battle_FlyingPartners_SpawnPos.patch` sets Parakarry Y=4;
`PartnersHP.patch` `$PartnerDies` lands flying actors at Y=3 before the 86-degree
collapse; `$UseLifeShroom_Actor` restores ten capped and returns the turn.
`battle/partner/patch/03 Parakarry.bpat` adds death and removes Vanilla KO drops
from hit/contact/burn/explosion paths, with recovery height 4. This branch
translates lifecycle behavior using native sprite names and shared event APIs.
Existing native landing dust and recovery helper remain presentation choices;
full source choreography/stylish/move mechanics are not accepted by this slice.

No-item Mario-front movement preserves each actor's vertical plane. Explicit
team swaps already exchange X/Z only. Replacement actors must not retain stale
status/effect/script ownership. HP persists by roster identity, while battle
timers remain unsaved and follow existing active/inactive phase rules.

## Validation boundary and next adapters

The pure checks distinguish eight HP records from four ready adapters, including
invalid/noncombat IDs. Existing negative cases use unadmitted Bow instead of
incorrectly continuing to label Parakarry unsupported. Shared native routes gain
a separate Parakarry cohort; ground repetitions remain reported separately.
Builds/pure checks are not gameplay acceptance. Native flight, ordinary/guarded/
contact/item/lethal damage, Life Shroom/no-item, status/swap, world recovery,
field carry and save/continue still require pinned actual results and rendered
observation before B01 can be declared complete.

B02 adds the remaining four adapters with their own status/effect/part/flight
rules and acceptance. HP data or a known height alone must never enable them.
Partner-owned items, enemy-held items and PR25 rework remain later packages.
