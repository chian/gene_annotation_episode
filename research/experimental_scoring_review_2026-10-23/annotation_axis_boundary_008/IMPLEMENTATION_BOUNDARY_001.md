# A105 whole-annotation boundary: current implementation inspection

2026-10-23. New research artifact; no existing record or production file changed.
This is source inspection, not a scorer implementation or an adopted numerical
policy. No test, scientific run, paper, retained paper evidence packet, or live
scientific database was opened. Completion remains 0/10.

The missing A105 calculation is substantive: a defined molecular-statement
score is not yet one A105 coordinate for an evolving candidate annotation.
There is also an implementation mismatch: current storage represents a
revisioned subject account containing claims and alternatives; it has no
first-class persistent identity for each competing multi-claim annotation.
An unchanged hypothesis can anchor one proposition, but cannot silently stand
for every claim in a complete candidate.

## 1. Actual stored identities and associations

Source: `gene_annotation_episode/domain.py`, `state.py`, and
`scientific_findings.py`. Field names below are existing fields unless explicitly
marked as a missing/proposed concept.

| Entity | Actual fields and identity | What persists or changes |
| --- | --- | --- |
| Original/derived subject | Annotation `subject_ref`; hypotheses `subject_refs`; observation `subject_refs` and separately `source_subject_refs` | The subject is the target/assayed object, not a candidate function. Several feature/product subjects may map to the same original footprint without being the same subject record. |
| Hypothesis (target proposition) | `{subject_refs, predicate, value: ATOM, context_refs}`; `Store.put` hashes origin plus the exact record | Exact unchanged content and origin reuse the same immutable `hypothesis_ref` when new evidence arrives. Predicate/value/context changes create another hypothesis record. There is no hypothesis revision pointer, member-claim list or candidate score. Array ordering and referenced-record identity remain part of this stored representation. |
| Observation | `{subject_refs, source_subject_refs, kind, source_ref, measurements, dependencies, anchor, ...}` | Immutable source/native observation. An observation can be linked to several hypotheses without becoming several independent experiments. Source subjects and conditions must remain separate from target attribution. |
| Assessment | `{hypothesis_ref, observation_ref, relation, applicability, extent_basis, condition_refs, assumption_refs, optional target_footprint/context masks/investigation_finding}` | Revision key is the pair `(hypothesis_ref, observation_ref)`, plus the context-account domain when present. New interpretation of that pair replaces its current revision; a new hypothesis or observation yields a different pair. Labels such as `transfer` and `mixed` are stored meanings, not current numerical weights. |
| Annotation account | `{subject_ref, footprint_kind, coherent_sets, alternative_refs, resolution, optional context masks}` | The ordinary revision key is **subject_ref**, not a candidate-function identity. A context account adds the context-domain identity. One current record exists per such key. `expected_revision` is checked; changed content increments `revision` and creates a new immutable annotation record ID. Exact unchanged content is reused. Old records remain retained. |
| Coherent set | `{interpretations: [{hypothesis_ref, disposition, assessment_refs}], context_refs}`; host adds `id = identity('coherent_set', group)` | Explicit grouping of interpretations remains useful. Its ID changes when group content changes, including disposition or assessment revision references. It is not a persistent candidate key across evidence updates. |
| Alternatives | `annotation.alternative_refs: hypothesis references`; `resolution: selected | alternatives_retained | unresolved` | These can retain competing single propositions. They do not define candidate-to-member-claim grouping or separate candidate scores. `resolution` does not name a selected coherent set; there is no `selected_coherent_set_ref` field. |
| Local interpretation account | Same scientific body as annotation; host lineage additionally includes episode owner, assigned scope, subject, context domain | It is an episode-owned revisable account. It is not another candidate just because another episode recorded it. |

The relationships are explicitly checked: one coherent set cannot repeat a
hypothesis; every listed assessment must name that interpretation's hypothesis;
hypothesis and annotation subject must have the same original-input footprint
(or matching context subject for context accounts). These are representation and
scope checks, not scientific acceptance rules. Store does not infer biological
compatibility between hypotheses.

An assessment update does **not** rewrite `assessment_refs` in already stored
annotation groups. Those references identify exact immutable versions. The
current-assessment query and `current_assessment_subset(refs)` distinguish current
versions; there is no currently bound annotation scorer deciding how an older
explicit reference contributes.

`Store.current_annotations` and current `query_records` use `current_revisions`;
`reasoning_view` normally reads these current accounts. With an explicit received
record selection it instead preserves received immutable versions and marks
their current/noncurrent status. Consequently, raw historical revision lists are
not evidence of extra candidates. The export keeps these memberships and exact
reference closures, including referenced noncurrent assessments; it supplies no
new candidate grouping.

### Exact current graph

```text
fixed target / derived subject
    |
    +-- current annotation account (one subject/domain revision lineage)
          +-- coherent_sets[] (content IDs, not persistent candidate IDs)
          |     +-- interpretations[]
          |           +-- hypothesis_ref -> target proposition
          |           +-- disposition
          |           +-- assessment_refs -> exact assessment revisions
          |                                      |
          |                                      +-- observation_ref
          |                                            +-- native measurements
          |                                            +-- actual source subjects
          |                                            +-- source/dependencies
          +-- alternative_refs[] -> hypotheses

MISSING AS AN EXISTING STORED CONTRACT:
persistent candidate annotation -> its current member propositions -> A105 value
```

## 2. Actual numerical helper and consumer contracts

| Function / field | Inputs | Actual output and boundary |
| --- | --- | --- |
| `native_metric_facts(entry, store, observation_refs=..., received_record_refs=...)` | Validated axis entry; actual received observation references | `native_facts[]` and `unavailable[]`. Copies recorded native quantities with observation/index, source, source subjects, target subjects, dependencies and method provenance. Unbound extractors remain unavailable. It does not select hypotheses, construct an experiment identity or calculate an annotation coordinate. |
| `evidence_unit_schema(entry)` | One axis entry | Unit fields are `experiment_id`, `representation_id`, `origin`, `measurements[{measurement_id, fact}]`, `judgment`, `witnesses`. `fact` contains `metric_id`, observation/index, native field/value/unit/direction, source, source subjects, subjects, dependencies and method; optional `comparison_context` retains the actual method/comparison identity. There is no typed candidate-annotation key or member-proposition collection. |
| `judgment.evidence_chain` | Witness lists named `source_subject`, `source_property`, `correspondence`, `target_hypothesis`, `limitations` | `target_hypothesis` is a witness list, not an enforced one-candidate/one-proposition grouping. An optional resolver establishes supplied witness availability, not semantic membership in one complete annotation. |
| `score_axis(entry, evidence_units, resolve_witness=None)` | Caller-scoped units; experiment and measurement identities supplied by caller | Groups by `experiment_id`; within each group merges `(measurement_id, metric_id)` across representations. Returns `experiments[].routes[]` with `score`, `score_bounds`, `score_unit`, `direction`, `polarity`, `status`, `reason` and contributing measurements. **Returns `annotation_aggregate: null` and `annotation_aggregate_status: not_defined_by_per_axis_rubric`.** No summation across experiments, propositions or candidate annotations. |
| `HypervolumeParameters(axis_weights, epsilon)` | Explicit unique axis names and finite nonnegative weights, at least one positive; `0 < epsilon < 1` | Parameters for arithmetic only. No default axes, weights, softening, measurement mapper or experiment combination. |
| `softened_hypervolume(evidence, policy)` | Mapping with exactly the parameter axis names; every value finite and in `[0,1]` | One normalized product value in `[0,1]`. Unknown, interval-only, signed-negative and native-unit quantities are not valid point operands. This helper does not choose a candidate or derive any axis value. |
| Optional runtime `project_annotation_score(store, scope)` | Actual Store and fixed scope; explicit caller binding | A finite scalar, an object with `.credit` and optional `.axis_components`, or a mapping `{'credit': scalar, 'axis_components': mapping}`. There is no declared candidate-score mapping in this consumer. A raw `score_axis` result does not satisfy it. |
| `Workflow.annotation_context(scope)` | The separately bound projector | `annotation_score`, `annotation_evidence_vector`, `annotation_score_binding`; no progress observation. Current runtime validates the scalar's finiteness; it does not itself validate/derive numerical axis semantics. |
| Optional projector `.read_details(...)` | Store, scope, `details_limit`, `details_offset` | Mapping containing `credit`. `annotation_score_read` renames it to `annotation_score` and attaches its separate support meaning/binding. It neither supplies a replacement scorer nor selects an annotation. |
| Case/default assembly | `PolicyBindings.project_annotation_score` and `annotation_score_definition`; case snapshot/reconstruction forwards them unchanged | `investigation_policy.create_policy` sets both to `None`; `assembled_case_policy.create_policy` preserves that result. The default scientific binding also supplies no annotation scorer. Ordinary continuation uses separate received-finding progress. |
| `export_annotation(..., include_credit=True)` | Current state | Explicit unavailable result with `annotation_score: null`, never zero. The current export function has no explicit numerical-projector argument; non-null legacy `credit_policy` is rejected. |

Package-wide call-site searches found `score_axis` and `native_metric_facts` as
helper definitions, not calls from the current production annotation path.
Test call sites exist, but were not run or used as behavioral proof.

The retained A105 descriptor currently has raw activity and binding-constant
identity routes, and supporting/opposing `-log10` native-test routes. The native
test extractor is unbound. Its two historical ordinal routes return
`categorical_scoring_route_withdrawn` under current code. Raw rate, concentration,
Kd or a tail statistic is not an A105 coordinate merely because a field is named
`score`. The descriptor's older applicability/sequence-only wording is not a
new authority over the subsequent user corrections.

Current numeric atoms retain bounds, approximation and an optional reported
plus/minus whose statistic is explicitly `unspecified`. They do not supply the
known SE, full covariance, sample-design information or calibrated response
parameters used by the new research proposals. Those exact proposed sheet cells
still need their own declared inputs; the current fact adapter cannot infer them
from an unspecified plus/minus.

The preserved arithmetic is:

```text
H(a; w, epsilon) =
  [product_k (epsilon + (1-epsilon)*a_k)^w_k - epsilon^sum_k(w_k)]
  / [1 - epsilon^sum_k(w_k)]
```

It can consume an identified `a_A105` once supplied together with the other
explicit operands. It does not establish what `a_A105` means. No ten-axis weights
or global formula were adopted by this inspection.

## 3. Exact one-statement / whole-annotation mismatch

A one-statement calculation can combine the source experiments bearing on
“this target performs this molecular conversion/binding/transport under these
conditions.” A complete candidate can contain several such propositions,
conditions and specificity qualifications. Several alternatives may also remain
under consideration. Existing storage tells us which hypotheses an account
explicitly includes, but neither the numerical helper nor the runtime defines
how all their evidence becomes one A105 value for **each** candidate.

These are different reductions and must not be hidden in one unnamed adapter:

```text
representations of the same measurement
    -> distinct measured evidence with shared dependencies retained
    -> numerical evidence for each declared molecular proposition
    -> A105 contribution for one persistent candidate annotation
    -> that candidate's complete explicit axis vector
    -> existing hypervolume arithmetic (later bound by W05)
```

The first identity grouping has a helper contract. The statement calculations
are research proposals. The candidate-level meaning and reducer are still
essential sheet work. Code that forwards an already defined coordinate is later
integration work; choosing its meaning, members, denominator and combination is
not merely W05 wiring.

## 4. Minimum remaining semantic decisions for the sheet

1. **Candidate identity and current contents.** Declare the persistent candidate
   whose A105 value is being computed and its current proposition membership.
   Keep evidence revisions/snapshots separate from that identity. An existing
   unchanged hypothesis can anchor a genuinely single-proposition candidate;
   using it as the identity of a multi-proposition candidate requires an
   explicit membership convention. Current coherent-set hashes cannot silently
   provide that convention. Candidate identity/claim membership in a new sheet
   contract must be marked proposed, not described as current Store fields.
2. **Meaning of the candidate's molecular content.** Specify which conversion,
   transport and binding statements the candidate makes, including conditions,
   specificity and logical relationships. Compatible multiple activities,
   mutually competing explanations, and complementary measurements of the
   same activity are different things. A105 is not all claims with a convenient
   predicate name; perturbation/restoration remains A106. This selection defines
   the number being scored, not a requirement to perform every experiment.
3. **Combination across those statements.** Give the actual equation and each
   denominator/weight's meaning. State how the result responds when an existing
   claim gains evidence, a new molecular claim is added, a claim is narrowed,
   or opposition arrives. Mean, sum, conjunction or strongest-claim selection
   answer different questions; none is already selected by the current code.
4. **Shared evidence across statement boundaries.** State how one experiment,
   shared control, derived contrast or complementary readout used by multiple
   claims affects the candidate calculation. `experiment_id` and measurement
   identity prevent repeated representations; they do not prove independent
   replication or provide covariance. Source DOI and the progress finding key
   are also not independence estimates.
5. **Point, bounds and missing-component result.** Define the candidate-level
   treatment of contradictory findings, nondetection and unknown components,
   including whether an identified point exists and what an interval means.
   Unknown remains unknown. If the research score is signed, explicitly define
   and justify the intended nonnegative axis coordinate before handing it to
   the existing hypervolume; an undocumented clamp or midpoint is not wiring.

These decisions can be demonstrated with a proposed research input/output
contract now. They do not require production mutation, a new runtime reviewer,
an evidence-acceptance gate, or mandatory experiments. The complete cross-axis
binding is still W05; missing within-A105 arithmetic remains A105 sheet work.

## 5. Useful grouping to preserve; obsolete behavior not to restore

Preserve actual target and assayed-subject identities, conditions and physical
scope; observations linked through assessments to target propositions; explicit
coherent groupings and alternatives; exact revision history/current pointers;
and source/experiment/measurement provenance. Keep these host records available
without dumping their IDs, revisions or bookkeeping into prompts.

`FindingIdentity.finding` groups question, source claim and qualification for
the **separate investigation-progress** channel. Its explicit source-claim
equivalence/correction links remain useful provenance. They are not candidate
identities, replicate counts, experimental reliability values or A105 scores.

Do not restore the deleted five axes, category-to-number applicability/relation
weights, unresolved multiplier, within-axis `max(support)/(1+max(opposition))`,
or highest-volume account selection merely because historical documentation
describes them. Do not transform revisions into new annotations, pool competing
candidates into one value, count one observation repeatedly through several
claims, or substitute finding-count progress for annotation support. Preserve
saved historical observations without recomputing them under a new formula.

Current `credit.py` has `AXES=()`, retired `CreditPolicy`/`project_credit`, and
only explicit numerical hypervolume arithmetic. Current `scientific_credit.py`
adapters reject use. Statements in historical `STATE_API.md`,
`SCIENTIFIC_CREDIT_BINDING.md` and `EVIDENCE_AXIS_SCORING_PROPOSAL...md` that describe
live categorical projection are historical, not evidence of the present code.

## Inspection provenance and limits

Read the full root `AGENTS.md`, `GOAL.md`, research `AGENTS.md`, active goal
attachment, ten-sheet goal, progress004, category-score withdrawal, evidence-axis
library instructions, `EPISODE_STRUCTURE.md`, `TIME_AWARE_ESTIMATION.md`,
`TOOL_KNOWLEDGE.md`, `TASK_AND_STEERING.md` and its amendment, evidence-axis review,
both verbatim axis-direction records, `STATE_API.md`, the historical scoring
proposal, and `SCIENTIFIC_CREDIT_BINDING.md`. Initial combined terminal output
truncated; required omitted material was reread in bounded complete portions.
No post-paper authority reset was triggered because no paper evidence was
inspected. The current task/steering candidate requirement and latest task brief
govern the interpretation of older records.

Complete code files inspected: `domain.py`, `credit.py`, `scientific_credit.py`,
`evidence_axis_contracts.py`, `evidence_axis_scoring.py`, `evidence_geometry.py`,
`scientific_findings.py`, `investigation_progress.py`, `investigation_policy.py`,
`assembled_case_policy.py`, `default_scientific_binding.py`. A105 descriptor
configuration was inspected excluding its source-case `evidence` array.

Complete relevant paths inspected: Store record/reference validation common
prefix and hypothesis/assessment/annotation branches; identity/revision `put`,
`assessment_key`, current account queries, scoped record query, reasoning view
and `commit_reasoning`; export selection/current membership/reference closure,
JSON/GFF projection and `export_annotation`; `PolicyBindings`, `_load_policy`,
`prepared_case_bindings`; runtime `run_workflow`, `projection_view`,
`annotation_context`, `report_sources`, `projection_read`,
`annotation_score_read`, and the annotation-score closure/summary hooks. The
model-context projection was checked for hidden candidate regrouping; it supplies
none. Unrelated execution, resource and HPC behavior was not audited.

No tests were executed. No imports initialized a Store or run. No scientific
state, controller, production scorer, reader, publication or prompt was changed.
The only output is this new research inspection artifact.
