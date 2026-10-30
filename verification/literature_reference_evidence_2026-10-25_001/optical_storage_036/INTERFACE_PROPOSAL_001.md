# Optical storage036 — exact interface proposal before shared coding

This proposal records the read-only review and the three-part interface sent to
root. Root provisionally accepted the numerical/scientific boundaries and has
authorized this NEW proposal artifact only. Shared production coding is not yet
released. No paper or retained paper-specific evidence packet was read. No model
history, model/scientific run, pin, existing source/test or runtime state was
changed. No tests were run during this proposal review. No delegation was made.
Exactly ten axes remain, A105 first; the full literature goal is incomplete.
Scientific TASK feedback remains pending. No new TASK/template is incorporated.

## Authority and immutable dependencies

The active objective is the complete attachment
/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt.
The workload boundary is OPTICAL_STORAGE_INTERFACES_036.md in this directory.
Applicable root AGENTS.md, GOAL.md, docs/EPISODE_STRUCTURE.md,
docs/TIME_AWARE_ESTIMATION.md, docs/TOOL_KNOWLEDGE.md,
docs/TASK_AND_STEERING.md, the W04 evidence-axis library amendment, and
research/experimental_scoring_review_2026-10-23/AGENTS.md were inspected.
This is synthetic-only engineering; no post-paper interpretation is performed.

The existing modules remain byte-identical:

| Dependency | SHA256 inspected |
| --- | --- |
| literature_optical_inputs.py (035) | 6e956a39196800d2fe2e4e841a913f40ae4f2d1c44c1fd54fc6abdc6afd6b474 |
| literature_optical_calculations.py (033) | 1242c0e58e83a1ef4e4e8f25bbf94737b33dc706e61794c6ff98b87ce3c5740e |

035's stored lexical dependency retains native reader55244315, source-fields
20fd7866 and custody52069b7d, with the full hashes already in its output and
FINAL_RECEIPT.json. These are inspected implementation identities, not new
scientific measurements. 033/035 interfaces, implementation, tests and their
synthetic-only proposal/final receipts were read; no source-case packet was used.

Root's coordination decision keeps033 and035 frozen. The exclusive035 owner is
preparing NEW literature_optical_validation.py under workload037. Its expected
public API is agreed as:

- validate_optical_extraction(extraction) returns a detached validated extraction.
- validate_optical_selection(selection, extraction) returns a detached validated
  selection. Storage need not depend on that return value.

037's exact released hash/version will be recorded as a dependency before036
integration. Neither validator may call a source reader/callback, native numeric
parser, optical source reader, calculator, model or runtime. Section "Saved-only
validation" states the necessary responsibilities supplied to that owner.

Coordination correction received after the initial proposal text: W04 requires a
fresh owner. The NEW validator module belongs exclusively to
/root/a105_optical_validation_037, not the035 owner named above.035 remains
frozen and complete. The exact API and boundary request have been sent to037;
this correction changes engineering ownership only, not either frozen module.

## Existing numerical meaning and limits

The selected operation is literature.optical.populate within existing
LiteratureEpisodes/shared method_loop, exposed only by the existing
rate_population capability. It is a finite source-to-input publication adapter,
not another episode, loop, acquisition route, itinerary, retry mechanism,
scientific interpreter or controller.

| Existing A105 input meaning | Original033 result | Numerical meaning |
| --- | --- | --- |
| net_rate (q) | net_depletion_rate | Signed net NADH-depletion concentration rate, uM/min |
| variance_net_rate (Vq) | net_depletion_variance | Conditional first-order variance of that same endpoint rate, (uM/min)^2 |

For source-supported relationships and complete unqualified point operands,
q = -1000*(sample_slope-blank_slope)/(epsilon*path_length). This subtracts the
selected matched no-reaction background exactly once. Vq = J Sigma J-transpose,
where J = (-1000/(epsilon*l), +1000/(epsilon*l), -q/epsilon, -q/l). 033 owns the
arithmetic and its reason precedence. Its signed zero/negative estimates and
known/estimated/unknown covariance status survive unchanged.

The names net_rate and variance_net_rate explicitly project existing q/Vq
meanings; they do not create a third sheet, eleventh axis, new reliability factor
or independent observation. The scope is the source NADH-depletion endpoint
conditional on the supplied scientific relationships. The conversion does not
establish isolated protein product formation, productive coupling, recovery k,
molar E, normalization per mass, corrected activity or a source S/B score. It
does not apply a new correction to another saved rate or complete A105. Neither
component automatically earns credit because a rate has another representation.
W05/target correspondence and annotation-credit aggregation remain separate.

## Exact selected input

The operation's input schema is exactly frozen035 optical_arguments_schema().
There is no wrapper, added scientific number or model-authored arithmetic.
All properties in each selected object are required; missing information uses
the schema's explicit null/unknown forms. This notation specifies those fields:

    W = {source_ref: REF, representation: original|text,
         start: integer>=0, end: integer>=1, quote: nonempty string}
    N = {witness: W, number_start: integer>=0, number_end: integer>=1}
    M = {number: N, unit: W|null}
    I(allowed) = {value: one allowed code, witnesses: array[W]}
    Q = {measurement_identity: W|null, condition: W|null,
         measured_entity: W|null, interval: W|null,
         measurement: M|null,
         qualification: I(reported_point|source_qualified_approximate|
                          unknown|conflicting)}

    {
      source_ref: REF,
      source_kind: primary_source|retained_extraction|synthetic_fixture,
      molecule: W|null, construct: W|null, preparation: W|null,
      condition: W|null, measured_entity: W|null,
      signal_kind: I(absorbance_slope|absorbance_difference|
                     static_absorbance|unknown),
      signals: {sample: Q|null, blank: Q|null},
      calibration: {epsilon: Q|null, path_length: Q|null, wavelength: Q|null},
      relation: I(applicable_extinction_relation|not_applicable|unknown|conflicting),
      blank_role: I(matched_no_reaction_background|condition_reference|
                    component_omission|unknown|conflicting),
      same_endpoint: I(same|different|unknown),
      matched_window: I(same|different|unknown),
      rate_window: I(source_supported_rate_interval|interval_mean_only|
                     static_only|unknown),
      covariance_source_ref: REF|null
    }

W positions are original UTF8 byte offsets. N positions are Unicode character
positions inside W.quote. 035 checks exact source bytes and qualified numerical
selection. Its source callback authorizes every exact ref/representation and
returns exactly {artifact_ref: REF, content: bytes}. Known/conflicting meanings
retain actual witnesses; witness custody does not prove their scientific truth.

The child assignment gains optional requested_optical_components, a unique array
whose item enum is net_rate|variance_net_rate. Omission retains the repository's
two-component default; an explicit empty array stays empty. The parent chooses
whether its top-level typed return uses literature_optical_cells. Infrastructure
does not force that schema or enrich old selections retrospectively.

## Repository API, custody and atomic publication

NEW literature_optical_storage.py exports PROVIDER, VERSION, COMPONENTS,
LiteratureOpticalRepository and optical_cells_schema(). Proposed constants:

    PROVIDER = literature.a105.optical_population
    VERSION = literature_optical_population_record_v1
    COMPONENTS = (net_rate, variance_net_rate)

LiteratureOpticalRepository subclasses the existing LiteratureRateRepository
mechanical repository interface, with distinct literature_optical_operations
and literature_optical_received tables. It supplies populate/read/project_cells,
validate_returned_values/validate_cells, receive_cells and received_cells. It
does not inherit legacy rate scientific population behavior.

populate(context, arguments, operation_key) validates the exact run and nonempty
selected key. For a new operation, its callback uses actual _native_source
receipt, scope and assigned-page ancestry validation for EVERY read source,
including witnesses and covariance. Global Store presence is not authorization.
The requested original/text artifact must actually exist; no text-to-original
fallback is introduced. Every provenance ancestor is validated in the actual
scope; only sources whose bytes are read require direct receipt authorization.

The source035 reader executes once, then existing033 executes once. Both results
are detached. All bindings, payload/request artifacts, selected source and saved
outcome publish within one Store transaction. There is no partial authoritative
sheet if publication interrupts. Valid source partials still publish with the
available raw facts and explicit unavailable cells. Invalid attempts use the
existing LiteratureEpisodes structured failure path and create no completed
controller observation or automatic retry.

The canonical signature binds arguments, scope, run_id, episode_id, original
assignment and requested subset. Same operation key with changed signature
rejects. Same key/signature returns the original saved outcome after checking
saved associations and current receipt/scope/assigned-source metadata; it does
not reopen scientific source bytes, reparse or recalculate.

Exact saved payload fields:

    {
      version, input_source_ref, input_artifact_ref,
      direct_input_source_refs, input_source_refs,
      selection, extraction, calculation, cells,
      context_bindings, operand_bindings, interpretation_bindings,
      covariance_binding_ref, requested_components, implementation_dependencies
    }

selection is the exact035 selection. extraction is the complete unmodified035
output, including context, all six selected interpretations, sample/blank and
epsilon/path/wavelength raw observations, qualified numerical tokens, exact unit
witnesses/conversions, source and converted origins, full covariance source/data,
canonical calculation_inputs, input_unavailable_reasons, local reuse dependencies,
source_refs and lexical_dependency. Every original measurement_key,
physical_observation_key and owner_key remains saved there. calculation is the
complete unmodified033 output, including input_snapshot. cells is the exact
two-key alias projection of033 cells into existing q/Vq names; it is not a
different numerical computation. No raw record is stripped to serve transport.

Exact request artifact fields:

    {
      run_id, episode_id, operation_key,
      selected_tool: literature.optical.populate,
      scope, assignment, requested_components, arguments
    }

The operation table uses the original run/episode/key primary key and canonical
signature/outcome. The outcome has ordinary status/operation_ref/record_refs/
changed_record_refs/result/feedback fields. operation_ref is the existing
identity over run/episode/key. result contains sheet_ref, the two original named
cells and factual optical metadata only. Newly created and complete record
memberships are preserved. The selected sheet source has provider/version/origin,
request_ref, payload artifact and exact provenance parents.

Bindings are immutable ordinary Store records. Numeric measurement references
have narrow exact token anchors and raw token labels. Physical/meaning/context
references retain their exact source anchors, including original broad spans.
Semantic-owner references carry the original owner_key accession and fixed safe
role labels. Local-reuse references carry the original035 connected alias as
accession and a fixed local-alias label. Covariance binding references retain a
definition of the exact saved source/ordered owner relationship; a source label
alone cannot create covariance custody. Their immutable definitions and IDs are
checked on saved reads. Different local aliases do not establish global identity
or independence; later source/assay covariance assembly still needs the retained
original physical and semantic keys. No6x6 completion is attempted.

## Exact closed typed return

optical_cells_schema() is an array with x-source=literature_optical_cells.
Its item is a closed object; every field below is required. Every nested object
is likewise closed and fully required. All string enums have explicit string
types, numerical unknowns are nullable, and reference formats identify actual
Store records with declared namespaces. There are no unrestricted prose fields.

    {
      sheet_ref: source REF,
      evidence_source_ref: source REF,
      component: net_rate|variance_net_rate,
      value: number|null,
      unit: uM/min|uM2/min2,
      status: populated|unavailable,
      origin: derived,
      unavailable_reason: null|one finite033 reason,
      formula_code: nadh_extinction_net_rate|first_order_nadh_extinction_variance,
      conditional_on: unique array[source_optical_relationship_assignments|
                                   first_order_covariance_propagation],
      evaluation_scope: source_nadh_depletion_endpoint,
      endpoint_kind: NADH_depletion,
      endpoint_assignment: conditional_on_selected_extinction_relation,
      source_kind: primary_source|retained_extraction|synthetic_fixture,
      source_origin: reported|derived|synthetic,
      context: {
        molecule: C, construct: C, preparation: C,
        condition: C_context, measured_entity: C
      },
      interpretations: {
        signal_kind: TI(exact035 signal_kind enum),
        relation: TI(exact035 relation enum),
        blank_role: TI(exact035 blank_role enum),
        same_endpoint: TI(exact035 same_endpoint enum),
        matched_window: TI(exact035 matched_window enum),
        rate_window: TI(exact035 rate_window enum)
      },
      covariance: {
        source_ref: source REF|null,
        binding_ref: reference REF|null,
        status: known|estimated|unknown,
        origin: reported|derived|synthetic|null,
        unavailable_reason: null|covariance_unreported|covariance_status_unknown
      },
      operands: {
        sample_slope: D, blank_slope: D, epsilon: D, path_length: D,
        wavelength_context: D
      }
    }

    C = {ref: reference REF|null,
         unavailable_reason: null|source_context_unreported}
    C_context = same closed shape with context namespace for ref
    TI(enum) = {value: one enum, witness_refs: unique array[reference REF]}
    D = {
      measurement_ref: reference REF|null,
      physical_observation_ref: reference REF|null,
      semantic_owner_ref: reference REF|null,
      local_reuse_ref: reference REF|null,
      condition_ref: context REF|null,
      measured_entity_ref: reference REF|null,
      interval_ref: reference REF|null,
      qualification: reported_point|source_qualified_approximate|unknown|conflicting,
      approximate: boolean|null,
      observed_relation: point|lt|le|gt|ge|null,
      observation_status: observed|censored|unavailable|unreported,
      source_origin: reported|derived|synthetic|null,
      converted_origin: reported|derived|synthetic|null,
      canonical_unit: absorbance/min|absorbance|mM_inverse_cm_inverse|cm|nm|null,
      input_status: available|unavailable|context_only,
      input_unavailable_reasons: unique array[finite035 reason codes]
    }

Missing operand metadata uses explicit null references/numerical flags and an
unreported/unavailable status plus source_measurement_unreported. Source context
nulls carry source_context_unreported. Unknown qualification remains unknown;
reported_point means a point estimate, not zero sampling/physical uncertainty.
Wavelength metadata is context_only and never becomes a fifth formula operand.
Covariance absence is unknown/unreported, not a zero matrix. Supplied unknown
covariance stays source-bound with status_unknown; the rate may remain available.

The finite033 cell reasons are missing_sample_slope, missing_blank_slope,
missing_epsilon, missing_path_length, optical_relation_unknown,
optical_relation_conflicting, optical_relation_not_applicable,
blank_role_unresolved, blank_role_not_background, endpoint_mismatch_or_unknown,
window_mismatch_or_unknown, rate_interval_unestablished, covariance_unreported,
covariance_status_unknown, numerical_model_range and invalid_propagated_variance.
The finite035 operand reasons are source_measurement_unreported,
source_optical_unit_unreported, unsupported_source_optical_unit,
censored_source_operand, approximate_source_operand,
source_operand_qualification_unknown, source_operand_qualification_conflicting,
optical_signal_not_slope, optical_signal_kind_unknown,
optical_signal_unit_mismatch; the covariance reasons above are also retained
in their proper existing035 input reason position. Raw source qualifications
are never replaced by the first033 cell reason.

033 conditional strings containing '=' are not inserted unchanged into CODE
enums. Their complete information is transported through the typed selected
interpretation values, covariance status and propagation flag above. The
original strings remain immutable in calculation. Formula codes render symbolic
meaning; they contain no unrequested numerical operands.

| Internal scientific unit | Transport enum code | Factual rendering |
| --- | --- | --- |
| uM/min | uM/min | uM/min |
| (uM/min)^2 | uM2/min2 | (uM/min)^2 |
| mM^-1cm^-1 operand dimension | mM_inverse_cm_inverse | mM^-1 cm^-1 |

All codes must pass actual communication.validate_closed_schema and form
validation. Shared communication.CODE is unchanged; the internal variance unit
cannot pass it unchanged. A copied returned row must exactly match the saved
requested projection, including relationships, dependencies and unavailable
reasons, not merely satisfy JSON syntax.

## Saved-only validation and authoritative binding

037 validates exact035 detached record associations. Necessary checks supplied
to that exclusive owner include closed fields/enums/finiteness; enriched witness
shape and UTF8-length/internal selector relationships; original selection
recovered by dropping only enriched artifact_ref; raw numerical substring and
absolute token custody key; physical and semantic owner identities; qualification,
unit dimension/conversion and canonical input/reason consistency; local connected
alias grouping; full covariance shape/PSD/order/raw-unit/owner/source snapshot
relationships and supplied status; exact source roster and lexical dependency.
No source IO/native reparse/optical re-read/calculator call is allowed. Detached
checks cannot establish what unseen surrounding source bytes said or prove the
truth of scientific interpretation; they must not claim that capability.

Storage adds the following checks before projection/forwarding:

1. Actual Store source record provider/version/origin and request artifact,
   exact run and selected_tool, original request/selection/signature identities.
2. Original authoritative repository operation row by run/episode/key, its
   operation_ref, completed outcome, exact sheet_ref/cells and record membership.
   A copied provider label or fabricated request key has no matching selected
   authoritative outcome and is rejected.
3. Original selection against037 extraction validation; extraction inputs equal
   calculation.input_snapshot; two alias cells equal the original033 cell
   objects. Closed output shape, finiteness, value/status/reason/unit/formula/
   conditional relationships are checked without recalculating historical cells.
4. Actual source-record metadata artifacts match each enriched witness's chosen
   representation and covariance artifact; exact direct/provenance rosters and
   root artifact binding match. These are metadata reads, never scientific bytes.
5. Immutable published context/operand/meaning/covariance bindings match their
   saved definitions and identities. Requested subset and operation ownership
   remain original, rather than inferred from a provider string.
6. Typed supplied rows exactly equal their selected saved projections; duplicate,
   changed, wrong-family and unrequested components reject. Receipt storage
   freezes exactly admitted subsets and preserves forwarding order/idempotence.

Existing C4 admission separately checks original requested schema/commission,
closed form versus saved child facts, semantic validation and original action
identity before receiving references/credit. Repeated admission reuses original
admission/controller inputs. Old returns are not reinterpreted or enriched.
Source reads,033/035 population, model access and credit-history rewrite remain
forbidden during saved-only reopen/reconstruction/forwarding.

## Factual TASK/STEERING transport and its limits

No scientific TASK constants, aspect instructions or new template imports are
changed. A new factual optical branch in shared _received_returns is used by
literature children and the source-evidence parent (which imports _steering).
It renders only requested q/Vq cells, readable units, source endpoint, selected
relationships, qualifications, covariance meaning and safe received scientific
subject/construct/preparation/condition/measured-entity labels.

The typed dependency objects contain no raw or canonical operand scalars and no
covariance matrix values. Their actual refs preserve custody for permitted later
access. Dedicated rendering resolves labels from already received working
records; it does not acquire sources. Optical binding records are omitted from
generic _values expansion, and internal IDs/accession keys are not substituted
for scientific text. If a broad witness includes hidden operands, render the
specific fact that its source-bound witness remains available for scoped access.

Current renderer limitation found: _selected_records suppresses unrequested
amount measurement refs and associated broad anchored refs only. It has no
optical subset handling.036 proposes minimum optical-specific handling that
suppresses raw optical measurement/physical expansions and every reachable
anchored reference/context whose source/artifact span contains an unrequested
optical token. All optical context records retain actual anchors so a broad
condition label can be detected. Source meaning records and aliases remain on
disk/in typed refs. Existing amount behavior remains unchanged.

Tests must inspect actual receiving TASK and STEERING with distinct numeric
sentinels for raw slopes/epsilon/path and the unrequested output. Absence of a
component name alone does not establish subset protection. Requested q or Vq
must remain present with useful relationships and limitations. This is automatic
subset expansion control, not general redaction of arbitrary interpretive prose,
caller-supplied TASK text or explicitly selected later source.read content.
Generic non-optical renderer limitations are not claimed fixed.

## Consumer trace and prospective file ownership

The inspected complete affected modules were literature_episodes.py,
episode_services.py, literature_experimental_prompt.py,
literature_reference_parent_prompt.py, literature_amount_storage.py,
literature_assay_storage.py, literature_rate_storage.py,
literature_optical_inputs.py and literature_optical_calculations.py. The full
optical tests and amount storage tests were read. Relevant native/amount source
validator conventions, _Sources exact callback/witness path, communication closed
schema/form/fact filling and EpisodeBindingRegistry receipt/report hooks were
inspected. C4 episode_admission original frozen fact/ownership/receipt/credit
path and episode_completion saved slot/observation restoration were inspected.
The complete affected runtime methods inspected include DecisionSource.execute
and finish; Workflow.execute, report_sources, validate_report, facts, build and
its observation callbacks; receive_form/_receive_form's binding receipt entry.
The whole large runtime module was not read and is not an editing target.

The complete parent_population_information test path was inspected, including
its original14-entry frozen fixture preservation, native and amount additions,
capability delivery, provider turns and runtime observation assertions. Native
storage/return-fact/provider-delivery test names and relevant replay boundaries
were located for the prospective connected group; those tests are not claimed
all reread/executed yet.

Ownership, still prospective pending root release:

- NEW gene_annotation_episode/literature_optical_storage.py.
- literature_episodes.py: additive selected operation, assignment/fact route,
  source/ancestry checks and immutable fingerprint dependencies only. Preserve
  prior16 operation entries, schemas and behavior; new optical entry is17.
- episode_services.py: new lazy optical repository accessor only. Preserve all
  unrelated alignment and existing literature methods.
- literature_experimental_prompt.py: factual optical rendering and minimum
  automatic unrequested-value handling only; amount behavior stays intact.
- NEW tests/test_literature_optical_storage.py and
  NEW tests/test_literature_optical_integration.py.
- tests/test_literature_parent_population_information.py: additive optical
  catalog/schema checks only, preserving original14 fixture and existing16.
- NEW optical_storage_036 artifacts. This file is the only released write now.

No033/035, shared communication, parent TASK, runtime, scoring/credit formula,
historical code pin, saved run or other workload file ownership is requested.
037 remains separately owned and must be reviewed/released before consumption.

The complete path to verify is episode-owned selected operation → authorized
035 source reads →033 deterministic result → atomic original selected records
and outcome → C7 requested facts → original closed typed admission/receipt →
parent's actual receiving factual text → configured ordinary observation and
continuation. Parsing/calculation/rendering/reporting supply no extra observations.

## Proposed meaningful synthetic checks

1. Complete q=2 and Vq=.0024 through actual reader/calculator/storage with known
   versus estimated covariance retained; signed zero/negative q survive.
2. Epsilon-only and each missing operand; unsupported/qualified/censored source
   inputs; static/interval-only signals; unmatched/unknown/nonbackground roles.
   Preserve useful source observations and explicit partial/unavailable cells.
3. Missing source receipt, wrong scope, unrelated assigned-page ancestry,
   unavailable exact representation and forged witness fail without publication.
4. Same numeric token and same physical observation versus distinct equal values;
   original identities/local aliases survive. Covariance cross terms, status,
   owner/order/unit mismatch and contradictory reused covariance reject.
5. Idempotent same selected key, changed-key signature rejection, interrupted
   atomic publication rollback and recovered original outcome without parsing.
6. Forged provider/request/outcome/binding/selection/cell and cross-run ownership
   reject; legitimate saved metadata/source associations remain usable.
7. Real C7/shared-loop child selection → publication → original closed typed
   admission → caller-chosen subset → parent forward. Do not force schema choice.
8. Interrupted/repeated admission and redelivery preserve original subset,
   controller inputs, credit and observation count. One selected completed action
   adds one ordinary child observation; internal work adds none. Parent child
   admission completes its original commission only, not each internal cell.
9. Actual receiving provider TASK/STEERING with unique numeric operand/output
   tokens; rate-only, variance-only and empty subsets; broad source anchors;
   both literature and reference-evidence-parent receiver; requested meanings
   visible and unrequested numeric values absent. Existing amount subset checks.
10. Saved-only Store reopen and original forwarding/admission with source
    artifact IO, parser/reader/calculator/model access forbidden. Preserve exact
    original saved cells and historical observations, with no reacquisition.

Run only appropriate focused/new036 and connected affected groups:033/035,
amount/native storage, parent information, renderer/provider delivery and saved
return fact paths. No need repeat terminal3750-check main regression without a
new concern. Receipts will state actual commands, terminal results, hashes and
limits. Synthetic controlled providers/controllers are engineering fixtures;
they do not establish model-backed literature science or full A105 completion.
