**A102 implementation plan: approved, implemented and validated**

Build an A102-only structural-homology subtree using the shared Episode loop,
receipt handling, automatic grader routing and resource controls. An
investigation can begin with an unnamed sequence, a selected file
record or region, or supplied coordinates. Native structural correspondence
earns credit even while exact function remains unresolved.

The user approved this implementation and numerical policy with the explicit
A102-only subtree and shared-parent communication boundary. The implemented
entry points and usage are documented in [A102 implementation](A102_IMPLEMENTATION.md).
The plan below preserves its original design context; published instructions
and research drafts remain intact. Eleven fresh native execution cases passed
with scripted episode choices. Four separate fresh configured-model
investigations completed with matching owner and receiving-parent credit.
Required inputs and reusable helpers are retained with the tests; raw traces,
execution state and validation results remain under `runs/`.

The investigation definition comes from the published
[A102 instructions](../research/slotted_process_library/publications/2026-10-24-001/entries/A102.json).
The detailed numerical basis is
[A102 numerical sheet draft 002](../research/experimental_scoring_review_2026-10-23/a102_numerical_sheet_012/A102_numerical_sheet_draft_002.md).
Its [handoff](../research/experimental_scoring_review_2026-10-23/a102_numerical_sheet_012/HANDOFF_001.md)
explicitly identifies its formulas as proposed conventions requiring user
adoption. The published investigation instructions do not themselves adopt
those equations. Older axis-scoring tests also explicitly show A102 native
extractors as unbound; their arithmetic fixtures do not establish working
automatic structural credit.

The existing pieces and required additions are:

| Task | Existing tools or code | Implementation needed |
|---|---|---|
| Bind supplied material and its actual scope | Shared material/commission mechanics, material readers, original-input coverage | A102 material descriptor retaining sequence/coordinate identity, represented residues and completeness |
| Obtain external identities or sequence-homolog leads | Parent-supplied evidence or an explicitly authorized shared-state delivery | Publish an information need when leads are missing; the shared parent chooses how to obtain them, including an A101 sibling when appropriate |
| Retrieve deposited structures | `public.rcsb.entry`, `public.rcsb.file` | Join exact entry/entity/chain/construct metadata to target and comparator identities |
| Retrieve existing predicted models | `public.alphafold.prediction`, `public.alphafold.file` | Preserve selected model/version, sequence match and uncertainty; these operations retrieve models and do not fold a novel sequence |
| Obtain a model for a novel sequence | Generic launch/API/HPC Episode infrastructure | Prediction commission contract for a caller-configured backend; expose `needs_model` when no usable backend/model exists |
| Inspect coordinates | `inspect_protein_structure` | Bind the existing native software/environment profiles and original result permissions |
| Establish coordinate-to-sequence correspondence | `extract_protein_structure_sequence`, `sequence.align`, structure sequence/map descriptors | Authenticate correspondence to the supplied target, including construct changes, missing residues and insertion codes |
| Discover structural comparators | No Foldseek adapter found in the current structure tool stack | Add versioned Foldseek search/preparation/result contracts; use bounded local panels or a configured remote/HPC resource |
| Perform structural alignment | Current comparison tool requires a supplied correspondence | Add a pinned US-align adapter returning native metrics, exact residue/chain correspondence and transforms |
| Check selected geometry | `compare_protein_structures`, `protein_structure_sheet.py`, `protein_structure_calculations.py` | Reuse CA fit/evaluation and saved recalculation; add source-defined atom/centroid feature geometry where required |
| Ground comparator function and important features | Received characterization/structural-observation records; literature children for structural source interpretation | Request missing external characterization through the parent; populate A102 structural feature definitions while retaining producer and cross-axis dependencies |
| Score and transfer structural evidence | Qualified structure projections, saved sheets and custody checks | A102 graders, subscoring sheets, receipt-scoped compiler and automatic root/child projector selection |

The current `compare_protein_structures` operation performs an explicit-map
rigid fit or evaluates a supplied transform. It does not discover a structural
alignment or search a structure database. Reusing it alone would leave a
sequence-independent structural-homology gap.

I recommend [US-align](https://github.com/pylelab/USalign) for explicit pairwise
and, where selected, assembly alignment, and
[Foldseek](https://github.com/steineggerlab/foldseek) for discovery. Both require
new repository adapters and actual registered execution resources. Record
binary/version/hash, mode, database identity, selected structures and native
output schema. In particular, Foldseek's documented alignment modes change the
meaning of fields such as `evalue` and `score`; parsing must dispatch on the
recorded mode. A column name alone cannot select a grading formula.

Request the native map, transforms and paired-coordinate information needed
for grading when the selected search mode provides them. Credit an already
complete Foldseek comparison immediately. Deriving RMSD from its retained
coordinates and transform is deterministic arithmetic, not a new alignment.
Commission a pairwise follow-up only when required geometry or correspondence
is missing or a genuinely different comparison is needed.

DALI results should be accepted through a dedicated native/reported-result
reader when available. Adding a DALI deployment is optional for the first
release. Preserve Z scores as their native statistics. A Z-only excerpt does
not supply RMSD, a residue map or a geometry score.

The scoring outputs should remain explicit:

| Output | Meaning | Relationship to Episode credit |
|---|---|---|
| Native structural correspondence `B` | Measured geometry and extent on the assigned material | Supplies the A102 controller's native credit, including before a functional hypothesis exists |
| Function-qualified correspondence `E` | Native correspondence constrained by source-grounded functional features | Separate output; unavailable until its required features and correspondence are established |
| Contrast margin `A102_f` | Discrimination between explicitly defined incompatible functional alternatives | Separate output; unavailable when the alternative panel is unexamined or incompatible in scope |
| Quality/completeness diagnostics | Model origin, confidence, missing coordinates, construct and state qualifications | Inform interpretation and subsequent work; do not act as invented similarity or function probabilities |

For the first implementation, I recommend the draft's RMSD profile as the
declared common numerical profile. For one comparison:

```text
C = 2*n_pairs / (L_target + L_reference)
G = 1 / (1 + (RMSD / 2 angstrom)^2)
B = C * G

F = mean over the declared K physical features of
    1 / (1 + (feature_distance / 1 angstrom)^2)
E = B * F

S_f = max(E over supporting references in the declared contrast)
O_f = max(E over explicitly incompatible references in that contrast)
A102_f = max(0, S_f - O_f)
```

The 2 Å and 1 Å scales, equal feature weights, maximum pooling and unit
competitor subtraction are proposed policy choices, not calibrated biological
probabilities. Approval of this plan would authorize those versioned
conventions. The optimization scalar is native correspondence; a missing `F`
does not erase a measured `B`. An unknown alternative panel leaves the margin
unknown rather than assigning `O_f=0`.

For example, a synthetic row with `B=0.72` and `F=0.55` has `E=0.396`.
An explicitly evaluated incompatible row with `E=0.10` gives margin `0.296`.
Without the feature measurements, native correspondence remains `0.72` while
the function-qualified result remains unknown. These illustrate arithmetic,
not expected scores for the real cases.

Retain native TM scores and their normalization lengths. Implement the draft's
separate TM profile, `B=min(TM_target, TM_reference)`, only where the two values
are established to use the same map and transform at the declared scopes.
Verify that property for the pinned software outputs; do not assume its two
printed scores meet it. TM already includes length normalization, so this
profile receives no additional coverage multiplier. Keep TM and RMSD panels
separate; use the declared RMSD profile for the initial controller credit.

Within each commissioned scope/profile, maximum pooling over eligible distinct
comparisons prevents repeated references or reread results from adding votes.
Aggregate explicitly required scopes with a declared geometric mean, and
supplied targets by their assigned scope lengths. Preserve every required
scope, including uncovered material. Child selections cannot silently narrow
the parent denominator. Full-protein and assembly claims require their own
coverage and geometry; domain matches remain attributable to their domains.
The symmetric coverage term is applied once, without another positional
coverage multiplier. Alternative representations or model versions of the
same comparison require a declared primary result or retain a range with no
selected point; the compiler must not select the largest variant.

Implement these subscoring sheets and graders:

| Sheet / grader | Inputs and outputs |
|---|---|
| Structure identity and scope | Original target linkage; source and file hashes; sequence maps; chain/model/assembly/construct/state; declared and coordinate-observed lengths; experimental/predicted origin; uncertainty |
| Native structural alignment | US-align/Foldseek or authenticated existing comparison output; exact map/transform/atom selections; mode-specific native metrics; pair counts; scope checks; `C`, `G`, `B` and explicit missing-input reasons |
| Functional feature geometry | Source-grounded, versioned complete feature set for the limited claim; atom/centroid definitions and allowed chemical equivalences; distances under the retained scaffold transform; present/absent/unresolved counts; `F`, `E` and bounds |
| Reported structural comparisons | Source-confirmed paper/table values, units and scope; reported descriptors and missingness; preserve the distinction from a newly executed target comparison |
| Functional contrast panel | Compatible scope/profile, supporting/incompatible/shared/unresolved relationships, dependency and duplicate identities; `S_f`, `O_f`, margin and bounds |
| A102 axis compiler | Receipt-eligible graded rows; native controller credit, optional qualified outputs, provenance, exclusions and pending numerical inputs |

A missing side chain, unknown residue correspondence, low-confidence region or
unexamined interface remains unresolved. A zero feature value requires an
established deletion or incompatible feature at the specified chemical role.
Feature definitions must be fixed and source-backed before evaluation; dropping
unmatched anchors cannot reduce `K`. Sites use the scaffold transform rather
than a separately optimized site fit that conceals domain or pocket movement.
pLDDT, PAE, resolution and B factors retain their actual meanings; they are not
automatic fit weights or multipliers on function confidence. Report justified
bounds or declared state/model variants separately.

The automatic connection should be:

```text
qualified native result committed
  -> producer/schema-specific grader automatically attached
  -> structural/feature/panel subscoring sheets populated
  -> receipt-scoped A102 compiler
  -> controller credit, episode.credit details and typed child return
  -> receiving parent recomputes from its own admitted evidence
```

This route is code. The model chooses investigations, comparisons and
source-grounded interpretations; it does not choose whether a grader runs or
write a numerical score. Reading `episode.credit` reports existing credit and
does not trigger the first grading or launch an unselected comparison.
An expected missing/malformed grader produces an explicit scoring diagnostic
and the missing input list, without substituting an assertion counter.

Use the existing qualified structure projection and saved-sheet machinery,
including `execution_protein_structure_projections`,
`execution_protein_structure_saved_sheets`,
`execution_protein_structure_sequences` and
`execution_protein_structure_failures`. Add an explicitly received A102 grade
fact with a narrow scoring-use grant. A Source auxiliary file or a received
descriptor alone grants no access to unselected coordinates or values.
The producer can retain a full sheet while returning the selected grade and
its authenticated numerical operands. The default A102 return must transport
the grade evidence and scope maps the parent needs, rather than only a job ID
or a model-authored score. Metadata-only returns must earn no parent credit.

A102 is an axis boundary. Scientific children inside this subtree remain A102
structural investigations; operational and structural-literature children
support that work. Another evidence axis is commissioned by the shared parent
as a sibling. A102 does not commission A101, A105, A111 or another axis beneath
itself. Enforce that boundary in child admission, not only in prompt guidance.

Information exchange and subtree membership are separate contracts. Both
acquired information and the need for information must be visible to the
shared parent. Use the canonical shared record store and the parent's existing
commission/return mechanisms, with these proposed communication records:

| Record | Required contents |
|---|---|
| Information need | Need identifier, requesting episode and A102 task, target and scope, requested facts, why they are needed, required provenance/fields, currently available references, and whether structural work can continue without them |
| Evidence availability/delivery | Producing episode/axis, target and scope, evidence references, correspondence/provenance references, qualifications, and the needs those records may satisfy |
| Need disposition | Parent-owned assignment/resolution references and status: open, assigned, partially fulfilled, fulfilled, unavailable or superseded |

Needs describe data, such as characterized homolog identities and sequence
correspondence. They do not prescribe a sibling's tools or take over its
investigation. The parent can fulfill a need from existing shared evidence,
commission a sibling, or explicitly retain it as unresolved. For example:

```text
A102 identifies a need for sequence-homolog leads
  -> publishes the need for the shared parent
  -> parent finds existing evidence or commissions an A101 sibling
  -> parent admits the returned evidence and delivers selected references
  -> A102 uses those inputs for structural comparison
  -> A102 publishes structural results and any remaining information needs
```

An authorized shared-state read can also deliver published information. Record
that delivery and its provenance/receipt; shared storage does not automatically
make private or unselected records eligible for scoring. The parent sees the
published needs at its next decision. A102 can continue independent structural
tasks or return with an open dependency; the parent can recommission it with
fulfilled inputs while preserving original commissions and archived decisions.
Publishing or satisfying a request does not itself create structural credit.
Sequence-homology scores remain with their producing axis. A102 calculates its
own credit from eligible structural evidence.

Coordinate-to-sequence mapping remains an A102 supporting transformation.
Discovery of sequence-homolog leads is an external information need. The same
boundary applies to experimental activity and observed ligand/metal evidence:
A102 can consume qualified records and request missing characterization, while
the parent owns commissioning any separate evidence-axis investigation.

The A102 child structure uses the ordinary recursive `scientific_process` role:

| Current need | Child and decisions | Required return / subsequent choice |
|---|---|---|
| Material or construct identity unresolved | Narrow scientific child selects material inspection, structure inspection or sequence correspondence | Actual scope/map and unresolved identities; owner chooses which models/chains are usable |
| Sequence-only target needs a model | A102 model-acquisition child uses supplied identifiers/coordinates or a bound predictor; missing external identities/leads are published as parent-facing needs | Identity-verified retrieved model or newly predicted model with lineage; otherwise `needs_model` plus the outstanding information need |
| Structural comparator panel missing | Scientific child chooses discovery panel and Foldseek job through launch | Native search results, search-space completeness and comparator identities; owner chooses informative matches and contrasts |
| Native structural alignment missing | Scientific comparison child chooses structures, scopes and US-align mode; launch child chooses a permitted resource | Actual map, transform, metrics and grade; owner assesses coverage and remaining uncertainty |
| Function-relevant geometry unknown | Scientific child selects grounded residues, loops, pocket/domain/interface anchors and the appropriate calculation | Scoped feature sheet and unresolved features; owner decides which functional interpretations survive |
| Comparator function or site definition uncertain | A102 structural-literature child interprets received structural sources; missing external characterization is requested from the parent | Source-linked structural feature definitions and unresolved needs; parent selects any required sibling investigation |
| Another function could explain the fold | Scientific child chooses a discriminating incompatible reference or scope/state comparison | Actual contrast panel with both support and opposition retained |
| Job pending, busy or incompletely acquired | Existing launch, monitor and results roles inspect, wait, recover or retry the original work | Execution state, exact acquired evidence and completeness; owner chooses further work through the ordinary loop |

Use the published thought patterns as appropriate: P01 for bounded analogue
transfer, P02/P03 for counterexamples and discriminating chemistry, P13 for
domain/site versus aggregate claims, P14 for a metric's relation to its readout,
and P18 for construct/state-dependent conflicts. These are selectable child
investigations, not a prescribed itinerary or a new private decision loop.
Both an existing alignment and its attached grade should be inspected before
commissioning another calculation. Literature or an inferred identity can
motivate a native check; it cannot masquerade as that check.

All parents and children receive the shared resource context. Native work uses
the existing atomic host admission and CPU/RAM/scratch enforcement, including
the default one-job/one-CPU budget. Start with bounded local reference panels;
larger databases and novel-sequence prediction use actually configured
resources. Missing resources return an explicit limitation. Result-worker
contention preserves prepared work and must not cache a failed or empty
structural analysis. Prediction availability is a prerequisite, not a hidden
assumption that the AlphaFold database API performs prediction.

Implementation should proceed in this order:

1. Freeze the A102 material, comparison, grade, feature, panel and return
   contracts, parent-facing information-need/evidence-delivery contracts and
   the versioned numerical profile. Use the canonical shared store for the
   communication records. Add pure arithmetic and
   scope checks, including the documented draft examples.
2. Bind existing retrieval, inspection, extraction, comparison and saved-result
   tools. Define the prediction port and its unavailable branch. Add pinned
   US-align and Foldseek launch/result adapters with resource estimates,
   native parsers and reusable raw-output fixtures.
3. Implement the subscoring sheets and automatic producer/schema grader
   registry. Bridge existing qualified comparison results to the same A102
   grade contract. Verify source/receipt authority before the compiler uses a
   grade. Keep discovery-only and paper-only observations distinguishable.
4. Add `a102_investigation.py`, `a102_scoring.py` and `a102_credit.py` using the
   shared assembly and receipt primitives. Select the projector from the frozen A102 axis and
   use the same projection for controllers, inspection and receiving parents.
   Enforce A102-only scientific descendants and expose needs/results to the
   shared parent. Other axes and their parent-owned orchestration stay outside
   this subtree's implementation.
5. Exercise adversarial boundaries: self-structure copies, duplicate hits,
   short matches, missing density, unsupported metrics, incompatible TM
   transforms, domain/state scope changes, absent versus unresolved features,
   incomplete search/parse, metadata-only returns and interrupted/busy jobs.
   Verify that a cross-axis child beneath A102 is rejected, a parent-supplied
   sibling result can satisfy an A102 need, and an unresolved need produces no
   fabricated observation, completed no-hit result or structural credit.
6. Run real cases with native algorithms and fresh configured-model decisions,
   retain traces and exact fixtures, and report numerical results at owner and
   receiving parent. Keep scripted integration results separately labeled.

The real validation set should build on the existing sequence cases and the
reviewed structural examples:

| Case | What the real run must establish |
|---|---|
| TPI | Anonymous sequence/model with a distinct TPI homolog; obtain real structural correspondence before native credit. [1YPI](https://www.rcsb.org/structure/1YPI) is a verified deposited TPI example; choose the actual non-self pair after sequence/construct checks |
| LacY, P02920 | Transporter correspondence with a nonidentical homolog/model; preserve state, membrane architecture and construct changes. [1PV7](https://www.rcsb.org/structure/1PV7) is a deposited LacY example with mutations, so it cannot silently stand in for an unchanged target |
| AtpG, P0ABA6 | Complex-subunit correspondence with a nonidentical gamma-chain homolog/model; distinguish a subunit fold from a verified assembled ATP synthase or demonstrated ATP synthesis |
| MJ0226 / synthetase comparisons | Use [1B78](https://www.rcsb.org/structure/1B78) and the reviewed comparator structures to test partial-domain resemblance without transferring whole synthetase function; calculate fresh results rather than asserting reproduction of unrecovered paper maps |
| Unrelated structural control | Explicit completed comparison/search with its actual weak or non-discriminating values; preserve the evaluated search space |
| Scope and uncertainty variants | Selected fragments, missing coordinates and predicted uncertain regions; verify coverage penalties, null function fields and honest bounds |

Freeze exact available models, chains, sequences, revisions and checksums before
the runs. Retain required coordinates and reusable helpers with tests, and put
execution output, caches and snapshots under `runs/`. Existing paper-derived
arithmetic rows are numerical fixtures, not substitutes for the fresh native
runs. Final reporting should show native method/metrics, coverage, model
origin, qualified feature/panel outputs, owner/parent credit, and the actual
next decisions and limitations.

Approved scope: the A102-only implementation and parent communication
boundary above, US-align plus bounded
Foldseek discovery, the RMSD-first native credit profile, and the draft's
separate feature/contrast conventions. A new prediction service deployment or
DALI deployment would require an explicit resource binding; this plan does not
claim either is already available. Full novel-sequence model generation remains
an explicit dependency until a predictor is bound and exercised.
