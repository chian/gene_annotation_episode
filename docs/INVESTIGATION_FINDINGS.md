# Typed scientific findings

Annotation support and investigation progress have different meanings. This
representation records useful scientific information before selecting its
numerical progress policy. It adds no episode, model call, reviewer, approval
process or scientific stopping condition.

An assessment can optionally include `investigation_finding` in its existing
ordinary reasoning commit. The target issue remains `hypothesis_ref`; the
finding separately records the actual source proposition and a typed
qualification. For example, the source proposition can describe growth of an
actual experimental construct while the target hypothesis concerns the submitted
gene. A `different_source_subject` qualification preserves that distinction.
`measurement_does_not_establish_claim` can distinguish measured fractionation
association from an inference of integral membrane localization. These are
representation examples, not new biological conclusions about the fixed case.

The exact fields are:

| Field | Meaning |
| --- | --- |
| `source_claim.subject_refs` | Actual subjects already named by this observation. |
| `source_claim.predicate` / `value` | Existing closed biological predicate and typed scientific value. |
| `source_claim.context_refs` | Actual conditions/context of that proposition. |
| `qualification.kind` | Closed limitation code, or `none`. |
| `qualification.context_refs` / `assumption_refs` | Declared context and examined assumptions for that limitation. |
| `status` | `retained` or `withdrawn`; nontransferability is not withdrawal. |
| `withdrawal_reason` | `not_withdrawn` for retained information; otherwise a concrete closed reason. |
| `same_source_claim_as_ref` | Optional earlier typed assessment asserting the same underlying source claim when representations differ. |
| `replaces_refs` | Exact earlier typed findings corrected; the standalone progress projection follows their owned dependency closure. |

All strings use the existing biological atom types, references or enumerations.
There is no findings paragraph or unrestricted rationale field. The existing
assessment revision/CAS lineage, partial commit feedback, changed-assessment
facts and parent-defined form continue to carry this information. No compulsory
new parent field is introduced.

`scientific_findings.FindingIdentity` normalizes declared meaning using the
target question, source claim and explicit qualification. It excludes relation,
applicability, disposition, revision, account, episode and quotation-window
identity. Source-local accessions are not semantic IDs: their extracted labels
and types remain scoped to actual source identity. Primary publication identity
comes from retained metadata. Missing or conflicting identity retains content
identity; a requested routing accession is not promoted to an observed
publication ID. Original target/member identity, derived sequence identity,
construct and mapping order remain distinct. Source bytes stay on disk.

This does not prove scientific truth or discover arbitrary aliases. The episode
owns an equivalence declaration. Syntax checks verify existing typed references,
actual observation subjects and status/reason relationships. The scientific
claim and qualification still need the episode's reasoning and audit.

Explicit withdrawal already excludes that assessment from annotation operands,
with a structured inactive-dependency reason. Valid `incomparable` and negative
findings remain retained information. Old scientific records are not
automatically converted or credited by inventing typed interpretations.

## Standalone progress projection

`investigation_progress.FindingProgressPolicy` requires an explicit positive
`finding_unit`; it has no default. `project_finding_progress` additionally
requires `known_assessment_refs`. It projects the intersection of declared known
canonical findings and current valid canonical findings. A relation-only revision
can witness the same known meaning without a new positive receipt; receiving
its replacement reference later adds zero. Requotation and reimport likewise
cannot add units for identical declared meaning. Valid negative/incomparable
findings remain eligible without numerical opinion/applicability weights.

Current corrections can retire previously known information before their new
meaning is received. The replacement earns no positive inclusion merely by
being shared state. Detailed loss records identify a current correction witness
or the current same-lineage withdrawal and its concrete reason. Historical
action observations and closed reports are not modified by this component.
Correction declarations name exact assessment references and their declared
replacement ancestry. They do not automatically invalidate every other current
representation with an equal canonical key. A surviving unretired representation
can still witness that known meaning. Broader invalidation semantics have not
been approved or silently inferred.

Read relevance uses actual attributed overlap with the fixed scope, including
broader inherited information. Narrowing attribution alone cannot create new
knowledge. Replacing a prior finding is a write: the existing scope boundary
now checks full prior attribution and every affected historical ancestor.
An immutable context-account domain neither grants blanket write permission
nor blocks a valid smaller actual allocation. Cleared allocations can preserve
legitimate correction declarations without earning positive allocation credit.

Temporary SQLite nodes, edges and unique ancestry closure replace an all-pairs
in-memory correction map. Only requested detail rows and one current correction
witness per requested loss are materialized. Source detail rows distinguish a
known representation from its current validity witness; credit counts distinct
finding keys, not those rows. Metadata normalization caches still grow with
encountered semantic entities; no constant-memory guarantee is claimed.

`finding_validity.FindingValidity` now provides one correction index for both
annotation support and investigation progress. Explicit replacements cannot stay
live in one projection after retirement in the other. The shared-validity test
checks the concrete annotation-still-names-retired-assessment case.

## Runtime receipt binding (engineering verification)

`ScientificFindingProgress` is an explicit runtime adapter. Its numerical unit,
initial known-record references and loss-preview size are caller-owned settings;
the `received_findings` case-policy mode records them, alongside the separate
annotation-support binding. It does not change historical policies or scores.

`episode_receipts.EpisodeReceipts` records first semantic delivery with its actual
origin: initial input, own result/read, admitted child form or report redelivery.
A child inherits a frozen prefix of its parent's receipt index, recursively
through the original commission. Its request contains a compact durable token,
not a copied parent ledger. Replays reuse the original token. Forward declared
record references carry semantic dependencies; this does not traverse backwards
from a source to all observations or read source bytes.

For this binding, the child form is admitted once before the parent's action
projection. The generic report callback reuses that saved attempt. A failed
form grants no new positive parent receipt and preserves the child's work.
Explicit state.query reads also deliver existing records; credit-detail witness
IDs are diagnostics, not automatic delivery of replacement scientific content.

Automatic scientific context pages are selected from received records before
pagination. Known immutable versions remain visible after an unseen revision;
separate revision-membership metadata avoids labeling an old version current.
Ordinary explicit discovery reads remain available. Current loss provenance is
supplied through the bounded progress preview and paged episode.credit read.

Redelivery changes received information without an extra completed-action
observation. The next ordinary observation still uses the actual cumulative
score difference from the preceding observation. No historical observation,
raw yield mark or controller stopping rule is rewritten or smoothed. Durable
receipt provenance distinguishes when information actually arrived.

The final receipt/policy/case group passed 25 tests in 79.53 seconds. It covers
selective forms, inheritance, reopen, visibility, explicit reads, mixed bindings,
initial-form baselines, immutable-assignment rejection and interruption around
publication/receipt/projection and failed-form redelivery. Independent source
review confirmed its specific remaining immutable-assignment ordering defect
closed after correction. A separate broader runtime/findings/scientific/context
group passed 71 checks; these are focused engineering groups, not a full-suite
or configured-model scientific completion claim.
A fresh configured-model verification run now uses this binding in
`cases/gene_001/runs/investigation_004` with provisional explicit finding unit 1.
Its first reasoning commit recorded two findings and progress 2; the following
decision received progress 2 separately from annotation support 0. Scientific
correctness, actual child receipt and the full native lifecycle still require
verification in this run. The numerical unit is not user-approved.

The separate historical investigation_003 retains its saved hypervolume-based
yield signal. Its scores, histories and live bindings have not been rewritten.
