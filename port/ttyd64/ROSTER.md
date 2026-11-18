# B02 roster and lifecycle contracts

Owner approved PR26 integration and B02/#10 implementation/scoped validation.
Base: PaperBoat7f661e7609589d0af8cb3895184057fdad833ed6 (PR26, tested head31eb).
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
| Watt | 6 | Yes | B02 | B02 flight/effect lifecycle | 11 |
| Sushie | 7 | Yes | B02 | B02 ground lifecycle | 0 |
| Lakilester | 8 | Yes | B02 | B02 flight/temporary-part lifecycle | 4 |
| Bow | 9 | Yes | B02 | B02 flight/concealment lifecycle | 9 |

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

The pure checks exercise eight HP records and eight implemented adapters, including
invalid/noncombat IDs. Noncombat IDs remain negative cases; Bow is now a supported identity. Shared native routes gain
a separate Parakarry cohort; ground repetitions remain reported separately.
Builds/pure checks are not gameplay acceptance. Native flight, ordinary/guarded/
contact/item/lethal damage, Life Shroom/no-item, status/swap, world recovery,
field carry and save/continue still require pinned actual results and rendered
observation before B01 can be declared complete.

B02 implements the remaining four adapters with their own status/effect/part/flight
rules; admission is implementation state, not validation or full partner completion.
HP data or a known height alone must never enable a missing adapter.
Partner-owned items, enemy-held items and PR25 rework remain later packages.

## B02 source and ownership decisions

- Active source partner patches add shared death and omit Vanilla KO drops. Four
  new native adapters preserve Vanilla drop/recovery scripts when not bound to
  saved TTYD64 mode. Ground/home timing for the four accepted adapters stays intact.
- `PartnersHP.patch` `$PartnerDies` and `PartnersItems.patch`
  `$SetPartnerAnimation_Battle` distinguish the flying fall pose from static
  collapse. New adapters use native Hurt/Injured for the fall and native Still
  for collapse; Sushie's ground initial hurt is Injured. Heights are9/11/0/4
  for Bow/Watt/Sushie/Lakilester. No source packed index or ROM address is copied.
- A small optional defeat/release callback in the native presentation descriptor
  owns actor-specific cleanup. HP unbind invokes release before actor destruction.
  Bow restores Mario/Bow alpha, Mario's ordinary idle table and hidden-team flag
  on defeat/replacement. Native living Outta Sight/phase behavior is retained;
  full source move/stylish parity stays in B05.
- Watt's native sparkle loop suppresses effects/bounce while a bound HP actor is
  dead and recreates them when alive. It records the exact owning actor; event
  put-away and HP unbind share idempotent disposal. Native source's individual
  LifeShroomProc/Revive handlers exist, but dispatches in the source shared
  revival script are commented; no newly forced event dispatch is invented.
- Lakilester's cloud belongs to his main sprite. Native/source part2 is the
  temporary Spiny projectile, not a separate cloud actor; defeat/rebind hides it.
  Cloud Nine's existing Mario effect/timer remains separate from HP death and
  Kooper flip. Sushie retains ground presentation and the existing Water Block
  implementation; broader move mechanics are not accepted from admission alone.
- The active world `PartnersHP.patch` UseItem script lowers Bow/Watt HP/FP gain
  positions by10 before common offsets. Only those active NPC recipients gain
  this adjustment; Mario/inactive recipients keep their existing position route.
- The isolated healing developer profile recruits all eight at3HP. The status
  profile retains three ground partners; normal saves gain no recruits/items.

Current source/build/runtime acceptance belongs to the feature PR and coordination
evidence, with exact revisions, methods and failed attempts. Source implementation
here is not all-eight gameplay/move/campaign readiness or native merge permission.
