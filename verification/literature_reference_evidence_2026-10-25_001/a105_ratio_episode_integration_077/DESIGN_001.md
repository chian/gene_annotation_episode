# Source-ratio LiteratureEpisode integration — design for root review

Design only. No production/test edits, workflow, provider, paper, retained packet,
source acquisition, HPC job or controller observation was run in077. All examples
below are constructed engineering examples. Accepted070+074 and071+075 establish
their documented primitives; they do not establish this integration.

## Exact API and compatibility proposal

Extend the existing constructor to:

```python
LiteratureEpisodes(services, *, outcome_page_size=8, rate_population=False,
    reference_parent_sources=None, contract_information_profile=None,
    ratio_source_population=False, ratio_source_evidence_origin='reported_source')
```

`ratio_source_population` must be an actual bool. True requires
`rate_population=True`; false retains the original19 population operations and18
fact namespaces with exactly their original schemas, descriptions, component
selectors and relationships. Neither an unavailable catalog entry nor an alias
counts as disabled. No new role, axis, relationship, router or itinerary.
`ratio_source_evidence_origin` is caller configuration, exactly `reported_source`
or `synthetic_fixture`; a nondefault origin requires the new opt-in. It is never
a model-selected operand. The tests explicitly bind synthetic_fixture.

Enable exactly one new operation `literature.ratio.source.populate`, using the
existing `ratio_source_population_schema()` unchanged. Its closed request is
`relative_signal_source_selection_v2`. Its complete standalone draft contract
is REQUEST_SCHEMA_001.json, copied from the actual installed schema API.
The existing `literature.ratio.populate` stays v1 with all old meanings.

The optional child-assignment property is
`requested_ratio_source_components`: unique array whose items are exactly
`reported_ratio`, `difference_from_reference`, `log_reported_ratio`,
`calibrated_amount_ratio`, `amount_adjusted_effect`, `source_profile_log_ratio`,
`source_signed_index`. It has the same omission semantics as existing component
selectors: omitted means all seven; [] requests none. It is not required on old
assignments. True opt-in adds it to every existing literature assignment schema;
false exposes no such property. The existing roles/versions/required fields stay.

The new fact namespace is exactly `literature_ratio_source_cells`. A parent
chooses any legal top-level field name and copies the exact native
`ratio_source_cells_schema()` (RETURN_SCHEMA_001.json), or explicitly requests
`$ref: episode-fact:literature_ratio_source_cells` under the existing contract
information profile. No schema extension or evaluation_scope is proposed.
This projection is a view of source evidence, not another evidence axis.

The provider remains `literature.experimental.relative_signal_source`; the
source record version remains `literature_relative_signal_source_record_v3`;
extraction v3, numerical sheet v2, calculation v2 and source request v2 retain
their existing meanings. All exact008 fields remain required/closed at their
current levels. Candidate/domain/flag/meaning/origin information is preserved.

Add `WorkflowServices.literature_ratio_source_repository(*,
evidence_origin='reported_source')`. It constructs the actual existing
LiteratureRatioSourceRepository(store,run_id,evidence_origin=...) and caches by
explicit origin; it does not discover/read sources or choose actions. The
binding's route factory closes over its caller-bound origin, so execute/facts/
receive/reconstruction use the same repository configuration. No fake repo and
no alternate pure/native wrapper. Existing no-argument repository ports stay.

The descriptor remains binding_id=literature and
version=literature_episode_binding_v1. With the new option enabled, configuration
adds `ratio_source_population: true` and the explicit origin, including the
reported_source default. Disabled descriptors omit both new keys. The enabled
implementation hash adds the three existing pure modules, actual native storage,
and NEW prompt/render dependencies. Changed current shared source bytes naturally
change current implementation hashes; historical descriptors/pins are immutable.

`compose_episode_bindings` and `_saved_episode_factories` already instantiate
LiteratureEpisodes with **descriptor.configuration; no edit there is needed.
`open_commission` already checks complete implementation/settings identities,
restores descriptors, reconstructs the exact request/declaration/inheritance and
builds the ordinary episode. Tests must execute those paths and reject changed
option/origin/dependency bytes before transport. No historical hotpatch/migration.

## Owned implementation paths after review

Released paths: literature_episodes.py, episode_services.py and
literature_experimental_prompt.py; NEW literature_ratio_source_prompt.py and
literature_ratio_source_render.py; NEW targeted tests; and this077 subtree.
One additional production edit is PROPOSED FOR ROOT REVIEW, not authorized or
touched: literature_reference_parent_prompt.py must pass the host-filtered
`literature_ratio_source_return_meanings` field into its existing _steering
whitelist. Its REFERENCE_PARENT_TASK and all other rendering remain exact.
This makes saved-only label selection possible without inserting extra fields
into immutable typed rows or exposing a private sheet to the parent. Root review
of the exact label projection proposal below is still needed. Native/pure modules,073 source
readers,076 owner calculator,072 metadata, shared loop/runtime/controllers,
existing tests, historical runs007/024/030 and pins remain read-only.

## Concrete shared changes

1. `_population_catalog` gains an explicit keyword flag default false and appends
   the new operation only when true. All three callers (initial parent operation
   information, actual child catalog and execution validation) pass the same
   flag. Existing19 rows retain their ordering and bodies.
2. `assignment_schema` conditionally adds the one selector. `decision_context`
   adds a host-only marker `literature_ratio_source_work` with
   version=literature_ratio_source_task_v1 on opted-in literature decisions.
   The marker does not replace the experimental marker or become prompt text.
3. `_tool_arguments` includes this operation in the existing recursive source
   ancestry check. Native repository authorization still checks every selected
   source/view, actual receiver, scope and own image.view action before bytes.
   A view_ref is not an original-source receipt and ancestry grants no knowledge.
4. `execute` dispatches to the new service repository's actual populate;
   existing structured contract/experimental errors remain the feedback path.
   There is no host-selected image.view, source-reading action or model report.
5. `_rate_fact_sources` becomes instance-aware (all actual call sites are through
   self) and appends the exact new projection only when enabled.
   `_population_routes` appends the exact namespace/assignment field/provider/
   components/factory tuple. `_rate_facts` additionally checks this provider's
   exact native record version before selecting its received sheet. Old routes,
   including rate-v1/native-rate filtering and old ratio, retain their behavior.
6. Existing validate_received_report checks the reporting child's actual saved
   possession, refreshed only from that child's durable receipts, plus requested
   component membership. Existing received_form_references writes only admitted
   rows using the actual typed_form operation key; the repository validates the
   runtime attempt/original contract and receiver digest. Existing forwarding
   methods copy the receiver's admitted subset, never all cells reachable by ID.
7. The new source TASK insert is included in full on every opted-in child
   iteration, alongside the existing full experimental task, assignment, scope,
   constraints, selected operations and requested typed meanings. The existing
   parent REFERENCE_PARENT_TASK remains exact; only its operation-information
   table gains the newly enabled capability. The shared STEERING renderer gains
   a dedicated exact008 source-ratio view in both directions.
8. The new render module exports pure `render_received(parts,rows,meanings,*,
   section,table,values)` and `hidden_records(reports,records)` plus a host-side
   `admitted_return_meanings(context,repository)` projection. The last function
   first obtains actual received_cells, then validates/reads only their original
   saved native payloads to select permitted scientific role labels and disjoint
   definition locations. It emits a closed internal object with version
   ratio_source_prompt_meanings_v1 and sheets[{sheet_ref,roles:[{role,status,
   label,display_status}]}]. role is one of native MEANINGS, status is
   known/unknown/conflicting; label is string|null; display_status is
   supplied_definition/retained_for_scoped_access/unresolved_source_meaning.
   This internal projection is host validation/presentation metadata, not a
   new evidence return schema or delivery of unrequested cells. Only supplied
   definitions are printed; known-but-withheld stays known. It supplies no
   measurement labels, raw tokens, sheet contents, witnesses or extra numbers.
   `initial_decision_context` calls it for the configured source parent;
   `decision_context` calls it for opted-in literature receivers. No model,
   source decoder, receipt, population, score or observation callback runs.

## Scientific meaning and finite reader scope

The constructed separate replacement arms use tagged WT complementation as the
reference, not endogenous unmodified WT. Their protein-band signal is used for
experimental comparability. A printed0.64/1.00 yields r=.64, r−1=−.36,
ln(r)=−.44628710262841953. These are dependent transforms of one comparison;
they are not three quality grades, independent experiments or scientific credits.
They do not establish molar/active amount, catalytic activity or recovery-lag
correction. A coexistence experiment requires a different effect-isolation
question; this operation makes no mixture correction.

Linked1/1.12 remains conflicting alternatives. A different experiment with a
different quantity is not that conflict. Unknown association, different or
unknown scales, unreadable selected regions and ambiguous alternatives retain
their distinct states; no primary selection/averaging/unknown0or1. Printed zero
has no log point. Censor domains retain strict ends/unbounded flags and are not
confidence intervals. Duplicate displays retain custody aliases without a
preparation count or bonus. Four conversion/model components remain explicitly
unimplemented. Numeric uncertainty reading is unimplemented; that is not evidence
that a paper failed to report uncertainty. Exact source custody validates the
retained selection, not scientific interpretation or visual reading correctness.

## Prompt delivery and label question for review

Full drafts are DRAFT_CHILD_TASK_001.txt and DRAFT_PARENT_TASK_001.txt. These are
rendered design artifacts, not dispatched prompts. The child draft includes all
existing recurring TASK inserts; it does not shorten existing task instructions
to introduce the new insert. The parent draft preserves its complete own TASK.

DRAFT_PARENT_STEERING_001.txt contains only requested reported_ratio and its
admitted qualifications. It does not list other numerical components or raw
numerator/reference values. IDs, view metadata, hashes, receipts, stored sheet,
witness prose, private image inputs and child history remain outside that text.
Recognize the source-ratio rows using their existing exact constants
candidate_basis=selected_received_source_representations and
uncertainty_evaluation=numeric_uncertainty_reader_unimplemented, plus valid
component/row shape; do not add an invented evaluation_scope.

Suppress automatic generic expansion of source-ratio row references and broad
same-evidence-source records. Display requested cells/candidates/domains/flags,
source origin and meaning/association/scale/identity states explicitly. Scientific
role labels can contain essential numbers; a blanket numeric-label filter is
withdrawn. DRAFT_LABEL_RENDERING_001.md gives concrete proposed handling and the
exact008 information limitation. This issue must be settled in root review
before implementation; no generic regex is claimed to prove source semantics.

## Trace from selection to continuation

Parent chooses literature child, assignment/scope and requested schema. Original
C1 freezes that request, input versions, caller descriptor and inheritance.
Child's ordinary DecisionSource repeatedly supplies its full TASK and own terse
STEERING. Child may select image.view or other available reading, then nominate
supported literal/meaning candidates in the selected new population operation.
ToolRegistry publishes actual native view/result; runtime journals that own action
and receives its refs. The native repository requires both records, runs actual
pure reader then separate calculator, and atomically publishes original request,
extraction, sheet, calculation, bindings and outcome. Host does not choose science.

Child closure freezes facts from actual received owned sheets and requested
components; form_with_facts populates the parent-selected fact field.
The original TypedReportContract/C4 compares form to original runtime_forms,
validates source values/possession/selector, records the successful form attempt,
receives the exact subset and its refs, then projects existing scientific credit.
Parent's next actual decision receives the admitted form, preserving its own TASK.
Its STEERING renders the requested source comparison and limitations.

One completed child own image.view and one completed child population each supply
one ordinary observation. Pure extraction, arithmetic, persistence, return
construction, label rendering, contract lookup and admission do not create extra
observations. A completed child return supplies one parent commission observation,
not copies of child turns. Exact raw credits/projectors/controller comparison and
costs remain unchanged. A fixture may use explicit synthetic controller seams;
those are fixture termination, not production stopping policy. Source processing
does not manufacture annotation assessments or W05 credit.

PROOF_PLAN_001.md names actual C1/C4/shared-loop paths and first fresh readonly
proof. No connected proof is claimed by this design. A later genuine primary /
configured-model source interpretation remains separately required by the full
active objective; calibration, uncertainty and wider scientific coverage remain.
