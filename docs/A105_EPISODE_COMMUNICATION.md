# A105 episode communication audit and A108 adaptation requirements

Source review: 2026-11-04. This document traces the executable communication
boundaries in the working tree. It reports no workflow execution or validation
result. File links identify the inspected symbols; concurrent work may move line
numbers. The A108 section is a design requirement, not a claim that its contracts
are already implemented.

## 1. Vocabulary and the two hierarchies

The **main evidence scoring sheet** receives selected results of the
experiment-type **graders**. A grader populates its experiment-type **subscoring
sheet** using source-anchored interpretations and operands supplied by the
appropriate **readers** and measurement-specific **subscoring sheets**. A reader
does not become a grader merely because both are implemented in one module. A
Python function or file count does not identify the scientific hierarchy.

For A105, the scientific flow is:

```text
Parent's experimental question and requested A105 information
    ↓
Selection of experiment type and functional assertion
    ↓
Questions about the required measurements, controls and comparisons
    ↓
Literature/database acquisition → source-specific readers
    ↓
Measurement-specific subscoring sheets and selected components
    ↓
Experiment-type grader → experiment-type subscoring sheet
    ↓
Explicit selection of components for each actual experiment
    ↓
Main A105 evidence scoring sheet
    ↓
Requested, authenticated return to the parent
```

The episode-role hierarchy answers a different question: which investigation
may commission which narrower investigation?

```text
literature
└── literature_strategy
    └── literature_search
        └── literature_page
            ├── literature_table
            ├── literature_ordered
            └── literature_targeted
```

This is a graph of permitted child relationships, not a mandatory itinerary.
An episode may use its own permitted tools directly. There is no distinct
runtime role named “grader”; enabled population tools are available to all of
these literature roles. Therefore a source investigation may populate a
measurement subscoring sheet and invoke its experiment-type grader without
creating another episode. Conversely, a difficult measurement question may
justify a child whose return is deliberately narrower than the eventual grader
input. These facts follow from [`_CHILDREN` and `_ROLE_INSTRUCTIONS`](../gene_annotation_episode/literature_episodes.py:45),
[`catalog`](../gene_annotation_episode/literature_episodes.py:1090), and
[`_population_catalog`](../gene_annotation_episode/literature_episodes.py:71).

## 2. Exact commissions between literature episodes

Every child commission also contains `goal`, `scope`, `purpose`,
`schema_json`, and `initial_report_json`. The scientific question is in the goal;
the information needed for the parent's next decision and each field's meaning
belong in the purpose. The parent selects a **closed typed return**, not a request
for the child's entire transcript. The initial report supplies only
interpretation fields. Host-bound recorded facts are absent from it.

| Sender → receiver | Assignment and purpose | What the child may acquire/read | What returns upward |
| --- | --- | --- | --- |
| Scientific parent → `literature` | `literature_assignment_v1`; `question_context_refs`, `source_refs`; supplied material, actual experimental question, requested components | Literature/database acquisition and source access; enabled population operations | Only the declared saved component families and constrained interpretations needed by this parent |
| `literature` → `literature_strategy` | `strategy_assignment_v1`; `question_context_refs`, `prior_search_refs`; investigate a productive search approach | Searches and original-source reads; enabled population operations | Selected search/source findings and, when explicitly requested, populated scientific components; search history is not automatically evidence |
| `literature_strategy` → `literature_search` | `search_assignment_v1`; `question_context_refs`, `search_result_refs`; investigate which returned sources merit examination | Searches, original sources and enabled population operations | Requested source discoveries or assessed components with source identity; discovery does not establish experimental support |
| `literature_search` → `literature_page` | `page_assignment_v1`; exact `source_ref`, `representation`, `artifact_ref`, `question_context_refs`, `prior_delivery_refs`; determine where/how to examine this source | Source operations and enabled population operations, without acquisition grants | Requested source-specific evidence/limitations/components; prior deliveries do not prove coverage or understanding |
| `literature_page` → `literature_table` | `reading_assignment_v1`; exact page plus an XLSX selection or byte window; interpret selected rows, headers, conditions and footnotes | Source-bound table/read operations and enabled population operations | Requested table-derived components and their experimental meanings; no unrequested table dump |
| `literature_page` → `literature_ordered` | Same reading assignment; exact source representation, byte `offset` and `limit`; investigate in document order | Source reads using actual returned continuations | Requested findings/components and unresolved qualifications; navigation distance is not evidence |
| `literature_page` → `literature_targeted` | Same reading assignment; separate exact source-bound spans; investigate those passages and necessary neighboring context | Selected passages and source access | Requested passage-supported meanings/components; separate spans never become a fabricated continuous quotation |

Assignment definitions and validation are in
[`assignment_schema`](../gene_annotation_episode/literature_episodes.py:630),
[`_validate_page`](../gene_annotation_episode/literature_episodes.py:853),
[`_validate_assignment`](../gene_annotation_episode/literature_episodes.py:865), and
[`prepare_assignment`](../gene_annotation_episode/literature_episodes.py:892).
Table selectors retain `sheet_key`, `offset`, `limit`, `header_row` and an optional
column/match/value/case-sensitive filter. Reading children stay within the
commissioned source and representation. The role graph does not grant sibling
access or broader scientific scope.

The actual access catalog contains source reading, locating, sequence scanning
and exact sequence references, experimental-record reading, images, archives,
XLSX and PDF operations. Acquisition is restricted to the literature, strategy
and search roles. Population capability is separately enabled by configuration.
The literature common actions are `tool`, `reason`, `child`, and
`redeliver_report`; **there is no `wait`** in
[`permitted_common_actions`](../gene_annotation_episode/literature_episodes.py:822).

## 3. Source, reader, grader and main-sheet handoffs

| Sender → receiver | Exact carried information | Scientific result and what remains local |
| --- | --- | --- |
| Search/database acquisition → source investigation | Actual request, transport/source provenance, captured original representation and record references | A source to investigate. Neither a provider hit nor a captured assay record is automatically a molecular-function grade. |
| Source reader → measurement subscoring sheet | Authenticated source witnesses, actual studied entities, measurement/endpoint/unit/condition identities and the particular selected operands | The sheet stores the supported calculation/interpretation and unavailable reasons. Unrequested raw operands remain local. Different readers retain their own scientific schemas. |
| Measurement subscoring sheet → experiment-type grader | A selected `received_component` with exact `namespace`, `sheet_ref`, `component`; alternatively an authenticated `source_number`, an eligible database effect measurement, or explicit missing input | The grader receives the selected measurement's native meaning, uncertainty, origin and dependence. A bare sheet reference is not a grant to its other components. |
| Source interpretation → experiment-type grader | Source-anchored `experiment_ref`, functional `assertion_ref`, selected `assay_type`/quantity, criterion interpretations and their `support_refs`; supported prediction model when requested | The grader applies criteria for the actual experiment type. A free narrative cannot substitute for an authenticated numeric cell. Missing operands do not become zero. |
| Experiment-type grader → saved experiment subscoring sheet | Original immutable operation, exact input selection/bindings/artifacts and calculated cells | The complete saved sheet is retained locally. Reusing an operation key for different inputs is rejected. Reading a saved sheet validates it rather than recalculating the science. |
| Saved experiment subscoring sheet → A105 main evidence scoring sheet | For every actual `experiment_ref`, explicitly selected `{sheet_ref, component}` for each requested dimension, or `null`; common `assertion_ref`, optional `comparison_ref` | Aggregate calculation consumes only possessed/authenticated selected rows. It rejects duplicate experiment selections, wrong experiment/assertion/dimension bindings, and unreceived components. |
| Main evidence scoring sheet → parent | Requested `literature_a105_aggregation_cells`, optionally requested experiment/measurement cells, plus the parent's declared interpretation fields | The parent receives typed values, status, missing inputs, units, actual contributor identities and qualifications. It does not receive all local source processing or the child's credit scalar. |

The executable reader boundary is
[`assay_grading_population_schema` and `read_assay_grading_inputs`](../gene_annotation_episode/literature_assay_grading_inputs.py:127).
The selected component resolver is
[`_component`](../gene_annotation_episode/literature_assay_grading_inputs.py:304).
Source/operation custody and persistence are in
[`LiteratureAssayGradingRepository.populate`](../gene_annotation_episode/literature_assay_grading_storage.py:127)
and [`read`](../gene_annotation_episode/literature_assay_grading_storage.py:257).
Database acquisition's discovery/capture purpose is explicit in
[`experimental_database_acquisition.py`](../gene_annotation_episode/experimental_database_acquisition.py:1).

A105 currently distinguishes eight experiment-type graders: `activity_rate`,
`endpoint_conversion`, `product_distribution`, `reaction_coupling`,
`ligand_binding`, `transport_response`, `protein_signal`, and `protein_amount`.
Each selects its own allowable quantities and criteria through
[`QUANTITY_KINDS` and `CRITERIA_BY_TYPE`](../gene_annotation_episode/literature_assay_grading.py:18).
The common storage code does not make these one scientific grader.

### Component-specific upward filtering from experiment subscoring sheets

Every returned experiment component retains its saved `sheet_ref`,
`evidence_source_ref`, actual experiment, assertion, assay type, quantity,
evaluation scope and the cell's value/unit/status/reasons/formula/meaning,
measurement keys, source references, origins and conditions. Its criterion
interpretations are narrowed by the component being returned:

| Component | Criterion interpretations included |
| --- | --- |
| `measured_effect` | None; the measured cell's identity and meaning still accompany it |
| `effect_variance` | `variance_correspondence` |
| `effect_precision` | `variance_correspondence` |
| `recovery_deviation` | `calibration_applicability` |
| `attributed_fraction` | `measurement_identity`, `attribution_supported` |
| `condition_response` | `measurement_identity`, `condition_scope` |
| `assertion_prediction_error` | Selected experiment type's predictive criteria, excluding variance correspondence and sampling basis |
| `alternative_prediction_error` | The same predictive criterion selection, applied to the alternative prediction component |
| `source_log_evidence_ratio` | All criteria for the selected experiment type and the supported prediction model |

Only `source_log_evidence_ratio` carries the prediction-model object. This is an
actual filter in [`_rows`](../gene_annotation_episode/literature_assay_grading_storage.py:59),
not merely an instruction to summarize briefly. Supporting identities required
to interpret/validate received cells are selected by
[`cell_record_refs`](../gene_annotation_episode/literature_assay_grading_storage.py:374).
The private operands behind an unrequested component are not thereby delivered.

The main A105 evidence scoring sheet currently has `reliability`, `validity`,
`relevance`, `attribution`, and `overall`, with A105's declared sum/sum/max/max/sum
reducers. It retains `selected_components`, selected/available/missing experiment
references, `missing_inputs`, original units/meanings and measurement identities.
An incomplete aggregate has `value: null`, with separately qualified
`available_value` where possible. The code applies no independence correction or
normalization; it explicitly retains `no_weighting_or_orthogonality_adjustment`.
Duplicate experiment rejection therefore must not be misreported as general
statistical independence handling. See
[`aggregate_a105`](../gene_annotation_episode/literature_a105_aggregation.py:84).
These dimensions and reducers are **A105 science**, not requirements for A108.

## 4. How a requested subscoring component becomes received knowledge

1. The parent selects a declared return family using a top-level
   `{"$ref":"episode-fact:<namespace>"}` alias and a purpose-specific
   interpretation schema. The host expands the alias into the exact original
   schema and freezes that declaration. The requested components are independently
   selected in the child's assignment.
2. The child inherits its parent's receipt history at the frozen commission
   boundary. Future parent discoveries do not silently appear in that child.
   Source metadata dependencies and actually possessed numerical cells are
   different forms of knowledge.
3. The source owner populates an immutable sheet. The repository projects only
   the requested components. A nonowner can forward only exact rows it already
   received, identified by `(sheet_ref, component)`.
4. During ordinary episode reasoning, the model updates only its declared
   interpretation fields. `interpretation_schema` removes `x-source` fields;
   `form_with_facts` supplies these recorded facts from authenticated repositories.
5. At child closure, the runtime stores a candidate form under the original
   contract. This does not yet mean the parent has received it.
6. Admission validates the original parent/child/operation identity, closed form,
   reference scope, requested component selection, authentic saved values and
   receipt custody. Repository-specific `receive_cells` records the exact admitted
   rows, bound to the original return, before parent credit is projected.
7. The parent sees the admitted form and its own resulting outcome/feedback. It
   must reason about that information for its next decision. Global database
   presence of an artifact or sheet proves neither receipt nor use.

Sources: [`action_schema`](../gene_annotation_episode/runtime.py:4163),
[`commission_child`](../gene_annotation_episode/runtime.py:2035),
[`expanded_contract_form`](../gene_annotation_episode/runtime.py:2680),
[`EpisodeReceipts.bind`](../gene_annotation_episode/episode_receipts.py:94),
[`fact_cells`, `receive_cells`, `received_cells`](../gene_annotation_episode/literature_rate_storage.py:717),
[`interpretation_schema` / `form_with_facts`](../gene_annotation_episode/communication.py:1287),
[`finish`](../gene_annotation_episode/runtime.py:1775),
[`next_return`](../gene_annotation_episode/runtime.py:2125),
[`_receive_form`](../gene_annotation_episode/runtime.py:3173), and
[`validate_received_report`](../gene_annotation_episode/literature_episodes.py:2403).

The numerical return registry in
[`literature_numerical_contracts.py`](../gene_annotation_episode/literature_numerical_contracts.py:24)
maps each namespace to its particular schema. Adding a name there installs no
reader, grader or scientific calculation. The matching
[`_population_routes`](../gene_annotation_episode/literature_episodes.py:2003)
binds namespace, assignment component roster, source provider, defaults and
repository. All of these must agree. Separate scientific sheets can share these
receipt mechanics without sharing criteria or formulas.

The normal assignment convention is `requested_<family>_components` for the
corresponding `literature_<family>_cells`. Important explicit exceptions and
additional selections are:

| Return projection | Assignment selection and consequence |
| --- | --- |
| `literature_rate_source_cells`, `literature_rate_source_domain_cells`, `literature_rate_source_meaning_cells` | All use `requested_rate_components`; these are different projections of the same rate work, not new experiments |
| `literature_reaction_semantic_cells` | `requested_reaction_components`; preserves selected reaction meanings rather than creating independent observations |
| `literature_reaction_native_observations` | `requested_reaction_native_positions`; selected original observation positions, not an implicit full table |
| `literature_compiled_assay_v2_cells` | `requested_compiled_assay_components_v2`; retains the frozen version-specific schema |
| `literature_compiled_assay_v3_cells` | `requested_compiled_assay_components_v3`; does not rewrite a prior v1/v2 return |
| `literature_controlled_response_component_cells` | `requested_controlled_response_components`, `requested_controlled_response_views`, `requested_controlled_response_component_keys`; selected views and exact component keys matter |
| `literature_gel_component_cells` | `requested_gel_components`, `requested_gel_views`, `requested_gel_component_keys`; does not grant the full source image or all band measurements |
| `literature_assay_grading_cells` | `requested_assay_grading_components`; selected experiment subscoring components |
| `literature_a105_aggregation_cells` | `requested_a105_aggregation_components`; selected main evidence scoring sheet components |

These projections are selected in
[`_rate_facts`](../gene_annotation_episode/literature_episodes.py:2151).
For a parent outside the literature roles,
[`received_report_facts`](../gene_annotation_episode/literature_episodes.py:2240)
forwards only repository rows that parent actually received. The report-composition
worksheet in [`literature_a105_worksheet.py`](../gene_annotation_episode/literature_a105_worksheet.py:1)
selects already populated information; it is not another grader or main evidence
scoring sheet.

## 5. Failure, partial results, revisions and credit

| Event | What is retained locally | What the receiver gets and may infer |
| --- | --- | --- |
| Missing scientific operand | Available supported cells and exact unavailable reason | A typed partial/unavailable component if requested; neither zero nor a fabricated complete grade |
| Missing uncertainty or unsupported inference | Available measured effect, source qualifications, unresolved precision/model status | The effect can remain useful, with its limitation preserved; the missing inference is not silently supplied |
| Source/search/transport action fails | Actual request, operation result and diagnostic where recorded | Operation feedback for steering; failure itself does not establish absence of biological evidence |
| Valid scientific action, invalid `report_update` | Completed scientific work remains durable | Report-format feedback; valid work is not undone to force a report-shaped result |
| Child execution fails or is interrupted | Already durable child records | Structured failure with `code`, `affected_refs`, `diagnostic_ref`, `partial_record_refs`; no successful form or private child work is invented |
| Child finishes but return fails validation | Candidate form and original delivery attempt | `report_delivery_failed`, failing field/reason where available, and no admission of rejected cells |
| Report needs repair | Original work, original commission and recorded return lineage | `redeliver_report` can repair delivery under the original constraints; scientific work need not be rerun merely to restate it |
| Parent already closed | Durable child return | Admission state `receiver_closed`; no claim that the parent integrated it |
| New assessment of the same experiment | Separate immutable sheet and original measurement identities | Explicit selected revision; grouping by experiment does not pool sheets or make revisions independent |
| Correction retires an earlier finding | Original record plus validity/correction provenance | Existing known finding may lose validity; its replacement earns progress only after actual receipt |

Execution versus report failure is implemented in
[`episode_admission.py`](../gene_annotation_episode/episode_admission.py:217);
valid action versus report formatting is separated in
[`apply_response`](../gene_annotation_episode/runtime.py:1591).
Experiment/sheet grouping is in
[`experiment_sheets`](../gene_annotation_episode/literature_assay_grading_storage.py:351).

Three quantities must remain separate: the measurement or experiment subscoring
component, the main evidence scoring sheet result, and episodic progress credit.
A105 recorded numerical cells explicitly have `annotation_credit: null`.
[`ScientificFindingProgress`](../gene_annotation_episode/investigation_progress.py:18)
uses actual received, distinct, currently retained typed target findings, keeps
negative information eligible, and declares
`parent_projection: received_meanings_not_sum_of_child_scores`. Search count,
bytes read, source count and report construction are not scientific findings.

## 6. Parent context and actual cross-axis information mechanisms

The reference parent prompt keeps the parent's original question and separates
its own tool catalog from the tools available inside literature children.
Its steering renderer selects the parent's own outcomes, feedback, working
state, admitted child reports and received component displays; it does not seed
parent steering with a child's task, assignment or transcript.
See [`REFERENCE_PARENT_TASK`](../gene_annotation_episode/literature_reference_parent_prompt.py:24)
and [`render_reference_evidence_parent_prompt`](../gene_annotation_episode/literature_reference_parent_prompt.py:153).
Numerical schema presentation may be compacted, but the original closed schema
and authentic scientific values remain authoritative in
[`literature_numerical_return_presentation.py`](../gene_annotation_episode/literature_numerical_return_presentation.py:1).

Cross-axis coordination already has explicit operational records and tools in
[`shared_information.py`](../gene_annotation_episode/shared_information.py:23):

| Sender → receiver | Existing tool and exact selected fields | Information boundary |
| --- | --- | --- |
| Axis scientific process → immediate participating parent | `shared.request_information`: `target_ref`, `question`, `required_information`, `reason`, `blocking`, `available_record_refs` | Names the missing operand, its required provenance and the decision affected. Creates no evidence, sibling commission, incoming-response promise or reason to wait |
| Evidence-owning axis → immediate participating parent | `shared.publish_information`: `target_ref`, `evidence_refs` | Offers selected received records. Saved grading supplies evidence results and qualifications after receipt; no extra evidence-summary paragraph is supplied. Publication alone grants no scientific knowledge or score |
| Addressed parent → requesting child | `shared.resolve_information_need`: `need_ref`, selected `status`, `evidence_refs`; operational `reason` only for unavailable/superseded replies | Only the actual recipient can resolve it; delivered records must be possessed and inside the child's request scope. Fulfilled/partial replies use saved grading rather than an additional assessment |
| Authorized parent/requester → selected publication | `shared.read_information`: `publication_ref` | Receives only explicitly delivered records; no implicit sibling-private access |
| Parent/requester → older coordination metadata | `shared.list_information`: selected `kind`, `offset`, `limit` | Pages need/availability/disposition metadata without evidence or progress credit |

New needs are open. A response can mark them partially fulfilled, fulfilled,
unavailable, or superseded. Fulfillment requires received evidence references.
The former `assigned` disposition had no actual work identity; it is no longer
offered. Existing recorded dispositions remain readable, without implying that
a response-producing job exists.

Each new publication identifies its actual recipient. Only the sender and
recipient see it; grandchildren do not broadcast directly to every ancestor.
A parent can read a child's need, act within its available options or explicitly
relay the specific unmet need through its own parent route. The root has no
upward request or evidence-offer operation. Read and response operations require
existing eligible messages; metadata paging is offered only beyond the automatic
preview. A literature-only root with no such messages has no shared tools to poll.
Responses are available only while the requesting child is active. Once that
child has returned, its unmet need is a retained limitation for the parent's next
commission; writing a response cannot reopen or deliver to the closed child.
The participating roles remain `annotation`, `scientific_process` and
`improvement`; literature readers use their requested typed child forms.
See [shared_information.py](../gene_annotation_episode/shared_information.py)
and `Workflow.shared_information_catalog` in [runtime.py](../gene_annotation_episode/runtime.py).

The preview retains the exact missing operand, decision reason, target/scope,
latest disposition and offered record types. After the normal receipt, the
original read action retains exact selected saved grading/scoring results,
including their numerical values, conditions and limitations. The completed-work
report places these results beside that action's original earned credit.
Unreturned cells and unrelated sheets remain unavailable. Material without
delivered grading is identified as material only; no evidence score is invented.
Historical evidence-summary paragraphs remain in immutable original artifacts
but are omitted from current message presentation. Selected Source bodies,
full evidence-reference arrays and older message versions are read explicitly.
An information need never suspends an episode or changes its continuation rule.

Two implementation boundaries follow from the code:

* Receipt no longer automatically broadcasts every A102/A103/A104/A107/A110
  record batch with generic availability text. An episode selects the existing
  `shared.publish_information` operation for a useful evidence offer. Native
  attribution can still publish a concrete measurement/request reference, missing
  operands and required provenance to an actual immediate parent. This creates
  an actionable limitation, without assigning work or replacing the typed return.
* A shared information read delivers selected record references. It does not
  invoke a literature repository's `receive_cells`. Therefore delivering a
  saved A105 sheet reference through shared information is not sufficient to
  grant all its typed numerical components. A108 must receive the required
  previously assessed components through an authenticated typed projection or
  an explicitly designed component delivery route preserving original custody.
  A new reader must not bypass this boundary by hydrating all private cells.

## 7. A108 adaptation: the required communication design

A108 asks how other evidence fits the candidate function in the actual organism
and sample. It must consume relevant **already assessed evidence**, preserve
that evidence's reliability qualifications, and assess its contextual bearing.
It must not automatically repeat A105 assay grading. Its main evidence scoring
sheet dimensions, reducers, and necessary subscoring sheets must follow that
scientific question independently. A105's eight experiment types and five main
dimensions are not a rename list.

The reusable design is explicit questions, purpose-specific subscoring sheets,
selected typed returns, original-source custody, immutable grades, admitted
receipts, qualification-preserving partial results and parent steering. The
following handoffs must be designed explicitly for A108:

| Sender → receiver | Required information selected for this handoff | Purpose and filtering |
| --- | --- | --- |
| Annotation parent → A108 scientific process | Actual target, candidate function/assertion, organism identity, supplied sample identity and stated sampling conditions; specific received evidence records/components that the contextual question depends on | Establish the question and known evidence. Missing organism/sample context remains explicit; no invented habitat, condition or answer is inserted. |
| A108 → shared parent | An existing `shared.request_information` record naming the missing fact/component, actual target, why it affects the contextual interpretation, known supporting records, and whether other useful work can continue | Ask the owner for needed evidence. A108 does not commission a sibling axis or start an unrelated algorithm on its behalf. |
| Other evidence axis → parent → A108 | Selected already assessed findings/components with original axis/assertion, actual studied subject/organism/sample/conditions, original value or categorical observation, uncertainty/limitations, original subscoring references and source/measurement/dependence identities | Supply the precise existing evidence needed for contextual interpretation. Preserve original reliability judgments; do not convert them into newly independent support or grade them again. |
| A108 → literature investigation | A specific unresolved contextual relationship, relevant already received evidence identities, organism/sample scope and selected contextual return fields | Target original literature/database evidence that resolves that relationship. Search query and source choices remain the episode's work. |
| Literature investigation → contextual reader | Exact source/record selection and the required identity/condition/relationship question | A reader extracts and authenticates the requested contextual claim and its qualifications. It does not automatically run raw assay calculations. |
| Contextual reader → appropriate A108 grader | Original contextual observation, studied entity and sampling scope, candidate-function relationship being evaluated, conditions/limitations, anchored support and dependency identities; only measurements relevant to that relationship | Each scientifically justified grader evaluates its particular contextual question. A common storage interface must not replace custom scientific criteria. |
| A108 grader → A108 main evidence scoring sheet | The selected contextual subscoring components, exact originating evidence and relationship identity, original reliability qualifications, contradictions, missing context and dependence | Combine only the independently specified A108 dimensions/reducers. Preserve distinctions between new contextual findings and reused evidence. |
| A108 → annotation parent | Requested main-sheet components, decisive contextual relationships and conflicts, inherited evidence identity/qualifications, unresolved question requiring the parent's next action | Return sufficient context for the parent's next decision. Do not return all child sources, raw measurements, sibling logs or a repeated reliability assessment. |

For each proposed A108 subscoring sheet, the build plan must explicitly name:
the contextual question; its actual source or incoming-report operands; its
reader; the criteria its grader applies; each output component's meaning and
units or categorical semantics; missing/conditional/contradictory states; the
specific downstream main-sheet consumer; component-level provenance and
dependence; and the exact upward projection. A sheet without a necessary
scientific consumer is not justified by an A105 counterpart.

The incoming evidence contract must retain, when relevant to the selected
question: original assessment/component reference, candidate assertion,
actual studied subject, organism/sample/condition scope, source observation,
original qualification/uncertainty, source and measurement identities, and
revision/dependence relationships. A108 adds a separately identified contextual
relationship and its supporting contextual evidence. Repeating the incoming
observation or giving it another source reference must not create another
independent contribution.

Use the existing parent-mediated need/disposition mechanism for missing evidence.
For a request whose answer is already in another axis's admitted typed return,
deliver only the necessary fields with the original projection identity. For a
missing source qualification, commission the narrow source investigation. For
an unavailable sibling result, report the unresolved need to the parent and
continue only work with expected scientific yield. Need status is operational
coordination, not a new episode continuation rule, wait action or progress score.

The current reference-parent prompt contains A105-specific molecular assay
instructions. Its A108 branch is a limited string substitution in
[`_task`](../gene_annotation_episode/literature_reference_parent_prompt.py:63).
That substitution is **not an adequate A108 scientific prompt**: it leaves
assay/measurement/transfer concerns that may be irrelevant to the contextual
question. A108 needs purpose-specific parent and child instructions while
retaining the same communication and receipt rules.

## 8. What source review establishes, and what later validation must establish

Source review establishes the stated contract/custody mechanisms and their
current limits. It does not establish that an autonomous episode chooses
sufficient fields, uses every necessary grader, produces useful grades or
actually steers correctly after receiving them.

Later A108 validation must follow the complete chain: original parent question
and scoped input → independently selected information need/source investigation
→ justified reader and subscoring sheet → appropriate contextual grader →
main evidence scoring sheet → candidate return → admitted parent receipt →
parent's next decision. Saved sheets alone prove only the middle of this chain.
The retained evidence must show requested component scope, original reliability
qualifications, missing inputs, corrections and reused-evidence identities
surviving each handoff. It must also show that a parent-mediated response is
actually received before it is used, and that an unsuccessful delivery produces
actionable feedback rather than silently vanishing or granting private work.

No test, workflow or source edit was performed for this communication audit.
