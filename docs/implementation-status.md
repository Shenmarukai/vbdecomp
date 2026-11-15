# Implementation status

Source accounting reconciled 2026-11-14 UTC. The catalog has 10,110 entries:
5,242 classified game/engine, 4,115 library, 592 compiler glue and 161 with
unresolved origin. Catalog entries can share code or include compiler-generated
operations; they are not independent authored bodies.

The current source associations are summarized in the [README](../README.md).
Neither those counts nor the 98.4% origin-attribution figure measure completion.

## What was checked

Three parallel reviews covered every one of the 586 game/engine entries previously
flagged for mapping, scope, partial-body, parser or implicit-operation review.

| Finding in that group | Entries |
| --- | ---: |
| Existing body or factored operation located | 246 |
| Implicit or compiler-generated operation present | 152 |
| Original identity or coverage scope still uncertain | 181 |
| Concrete incomplete path | 6 |
| Confirmed missing body | 1 |

These are source-review dispositions, not full-function correctness judgments.
The uncertain-scope group also contains existing source, including receiver
adapters and shared tails whose complete original coverage is unproved. All 11
parser-flagged entries have source bodies; their parser flags remain explicit.
The 93 previously recognized implicit/generated entries were inspected, along
with further lifetime and copy operations found during reconciliation.

Stale paths, signatures and owner fingerprints were repaired in 250 local mapping
records. Twenty additional proposals remain evidence only because an inline factor
or containing class does not establish the original function's identity. Native
scope limitations and existing match receipts were preserved; no new origin or
exact-match credit was awarded.

The other 4,656 game/engine entries received a targeted placeholder-pattern check.
Eighteen original entries corresponding to suspicious simple bodies or markers
were inspected; none established a hidden stub. This includes original no-op
hooks and the original unimplemented `PlayMusic` diagnostic. Ordinary constructors
and destructors can have empty explicit bodies while performing member/base
lifetime work. This check does not verify every branch or lifetime operation.

## Demonstrated implementation gaps

| Missing routine or incomplete path | Dependency still unresolved |
| --- | --- |
| `430760`: missing auxiliary-screen cleanup body; also blocks paths in `45E6C0` and `46F190` | Concrete screen producer/type and resource member at `+84` |
| `458770`: declaration-only route-child cleanup; related WorldMap continuation in `461A10` is incomplete | Concrete child ownership and the WorldMap screen producer at `GameInterfaces+34` |
| `506B70`, `507580`: BufferManager release/destruction with a live child | Concrete owner and lifetime contract for member `+2C` |
| `5AEB20`: octree root-leaf ground-ray path | Original selector read at ray `+24`, outside the recovered 32-byte ray object |

`430760` belongs to the classified game/engine group; `458770` remains among the
161 entries with unresolved origin. The two missing routines and six incomplete
paths are demonstrated lower bounds. They do not establish that every other
function or transitive call is implemented correctly.

Other mapping flags describe ABI, calling-convention, code-generation or coverage
questions rather than missing bodies. In particular, unresolved GameEntity and
Action layouts affect consumers even where a source implementation exists.

## Work that can be separated from those blockers

The RGBA helpers (`4C87B0`, `4C8870`, `4C8AD0`) now have separate source bodies.
The text writer captures all four components before numeric formatting. Their
original private register conventions remain unresolved: current 90/124/45-byte
bodies differ from the original 86/121/41-byte scopes. Release compile/link and
static capture/publication checks pass; no exact-match credit is added.
Complete text RGBA read/write and binary-read comparisons remain nonmatching.
The binary RGBA writer is unclosed on overlap with its defined RGB helper.
Vertex text export also restores separate 24-byte position/normal snapshots
before their formatter calls. Its complete 287-byte caller remains nonmatching.
Vertex text input now calls the existing three-component reader in both
coordinate and normal branches. Its 52-byte reader and 12-byte scaled-number
helper match complete code; the caller remains nonmatching.

The attack-series animation helper (`4012C0`) now has a separate 21-byte body
and caller boundary. Its complete static comparison has one layout difference:
attacker current `+10` versus original `+18`. No exact-match credit is added.
The point-target setter (`401100`) now has a separate 39-byte body and packet
caller. Four field operands retain the unresolved Action-layout difference.

The following helper boundaries have complete function-code matches verified
2026-11-15 with VC7 13.00.9466, LINK 7.00.9466, PSDK 5.1.3590.2 and DirectX 8.1.
Every relocation is resolved; EH and metadata contributions are included.

| Original | Source function | Code including EH | Owned metadata |
| --- | --- | ---: | ---: |
| `549FC0` | `JE::Entity::ProcessAnimationCues` | 18 | 0 |
| `587A60` | `JE::Client::AddFloatingSpeechText` (text overload) | 10 | 0 |
| `43B1B0` | `F3::InventoryInterface::InitializeHeading` | 196 | 36 |
| `560AA0` | `JE::ReprioritizePathNode` | 99 | 0 |
| `560E40` | `JE::PopPathNode` | 103 | 0 |
| `562550` | `JE::PushPathNode` | 63 | 0 |
| `4C9330` | `G3D_WriteTextVector` | 72 | 0 |
| `5BBC00` | `CreateOctreeTriangle2D` | 197 | 36 |
| `5BB090` | `CreateOctreePie2D` | 197 | 36 |
| `584ED0` | `JE::ModelCache::GetTextureSlot` | 354 | 0 |
| `4B41D0` | `GUI::Manager::ReadClipboardText` | 298 | 36 |
| `564AA0` | `ExcludedMaterial` | 232 | 0 |

The triangle/pie factories restore separate allocation/configuration boundaries
and the original ordinary `operator new` call. The dispatcher uses all five
factory calls; its complete equality remains unverified.

Socket replacement remains nonmatching after a complete static comparison. Its
defined removal and animation helpers are included.

Material exclusion restores its pointer table and per-comparison string lifetime.
Texture stitching restores material-name snapshots, direct resource operations,
live socket reloads, a signed initial scan and coordinate-conversion order. The
unit uses native Release `/GS`. Complete caller comparison is nonmatching; owned
EH and metadata match.

The texture-slot query restores its persistent `TextureSlot` key and the original
one-argument call from texture stitching. Required lookups remain unchecked;
the texture caller remains nonmatching.

The clipboard reader restores the ordinary Manager member and Paste call.
Its native security-cookie sequence supports the unit's Release `/GS` option.
Original clipboard failure behavior remains. Paste restores the original range
comparisons; its owned EH still overlaps CopySelection.

Typed text editing restores virtual text snapshots, the Label append boundary
and scoped overwrite/selection string construction. The logical body remains
nonmatching inside catalog aggregate `4C13C0`; no catalog match is credited.

Keyboard deletion, Right Arrow and End restore virtual text snapshots and
cleanup before blink reset. End uses virtual wrapping, and modifier bits are
reread after callbacks. The handler remains nonmatching; comparison closure
is blocked by existing Paste/CopySelection support overlap.

Edit events restore virtual wrapping for drag scrolling and mouse wheels, with
original captures before callbacks. Paste/CopySelection support overlap still
blocks comparison closure.

Caret hit testing restores the virtual text snapshot, bounded row lookups and
captured clipping bounds and character indices. The body remains nonmatching; all
operands resolve and the complete unwind metadata matches.

Loading-screen visibility has a complete nonmatching static comparison with all
call operands resolved. No source change or new exact-match credit follows.

The inventory constructor emits all 29 original helper/name pairs. Path update
restores frontier-pointer reloads after callbacks. Release compile/link and
shared-consumer checks pass. Two STL heap supports were checked separately and
earn no proprietary credit. Complete caller equality, class ABI and runtime
behavior remain unverified; `PathManager::Update` remains nonmatching.

The 161 unresolved-origin entries were reviewed separately: 63 have registered
source bodies, 43 have current source-annotation candidates, 54 still lack a
resolved source identity, and one is the declaration-only `458770` boundary.
All 161 remain unclassified. Names, address adjacency and similar instruction
sequences do not establish ownership by a recovered runtime or SDK.

## Accuracy, build and behavior

The canonical VC7 Release target compiled and linked at `39abe6524`. This
reconciliation changed documentation and local mapping metadata only, so no
build or runtime check was performed.

Historical accounting on 2026-11-12 recorded at least 3,447 game/engine functions
with exact-match receipts. Those receipts were not revalidated against the current
tree. Current function-code equality, whole-class ABI coverage and runtime
correctness remain separate, incompletely measured results. No single completion
percentage is established.

Detailed per-address findings and preserved before/after mapping records remain
local under `analysis/implementation-reconciliation-20261114/`.
