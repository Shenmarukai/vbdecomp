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

Several original helper boundaries are absent as standalone source functions even
though their operations occur in consumers. Examples include inventory heading
initialization (`43B1B0`), optional-model forwarding (`549FC0`), speech forwarding
(`587A60`), path-search heap helpers (`560AA0`, `560E40`, `562550`) and RGBA
read/write helpers (`4C87B0`, `4C8870`, `4C8AD0`). These are candidates for restoring
original source boundaries when accuracy work resumes. Presence in a caller does
not establish the original helper's ABI or emitted code.

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
