# Selected experimental figure cells and controlled return

This implementation contract binds the verified native helper013/clarification014
to existing LiteratureEpisodes. The original case conversion and reset remain
the scientific basis; no new paper interpretation is assigned here. Exactly ten
axes remain. This supplies A105 source components, not A101 or A107 computation,
partner necessity, a new episode type, or annotation credit/W05.

## Exclusive owners

- Fresh reader owner: gene_annotation_episode/literature_figure_inputs.py and
  tests/test_literature_figure_inputs.py only.
- Fresh storage owner: gene_annotation_episode/literature_figure_storage.py and
  tests/test_literature_figure_storage.py only.
- Coordinator: existing services, LiteratureEpisodes, prompt renderer, new
  literature_figure_prompt.py, integration tests and retained examples/reports.
- Existing literature_figure_measurements.py and its tests remain unchanged.

## Operation and retained selection source

Selected name literature.figure.populate. Export figure_population_schema() in
the reader (re-export storage). Closed args exactly:
`{source_ref,data_source_ref,source_kind,literals,interpretation_witnesses}`.
Both source refs required nonnull. source_kind uses existing SOURCE_KINDS.
literals has exactly ten nullable ordinary _Sources witness fields in order:
first_subject,first_partner,second_subject,second_partner,experiment,endpoint,
first_condition,second_condition,normalization,function.
Interpretation witnesses are the ordinary exact source-witness array, including
empty when genuinely no text is supplied. No numeric measurements in args.

data_source_ref original bytes are strict closed duplicate-free finite JSON:

```
version: literature_figure_selection_v1
first: ImageSelection
second: ImageSelection | null
design: {
 arrangement: coexisting_sequential_catalysts|coexisting_complex|single_molecule|unresolved
 contrast_kind: source_representation|partner_swap|other|unreported
 endpoint_scope: coupled_final_product|direct_subject_step|binding|indirect_response|unreported
 normalization_basis: reported_relative_turnover|arbitrary_signal|concentration|unreported
 measurement_relation: same_physical_measurement|distinct_physical_measurements|unresolved
 first_repeat: Repeat
 second_repeat: Repeat|null
}
ImageSelection exactly {
 image_source_ref:sourceREF,
 image_origin:published|synthetic,
 axis_scale:linear,
 selection:<complete exact native-helper selection from interface013/clarification014>
}
Repeat exactly {
 reported_n:integer>=1|null,
 repeat_kind:biological|technical|unknown,
 independent_preparation_count:integer>=1|null,
 spread_kind:SD|SEM|CI|unspecified|unreported,
 spread_numeric_status:not_extracted|unreported
}
```

second_repeat is null iff second is null. Unreported spread_kind requires
spread_numeric_status=unreported; all other kinds require not_extracted. No SD,
variance or independent preparation count is computed from pixels or n. Unknown
axis scale is an explicit unsupported contract failure in this first linear-axis
branch; do not interpret a logarithmic graph as linear. Source interpretations
remain supplied scientific meanings, not source-truth proofs from byte custody.

## Reader output and calculations

read_figure_inputs(arguments,*,read_source) uses the existing callback signature
and _Sources to read original paper/recipe/witnesses/images. No network, model,
SQL or state writes. Validate all reference/design/closed-field meanings, native
selection shape and source bytes. Read actual original image bytes only, then
call read_bar_ordinate. read_source returns artifact_ref and content(bytes).

Return exactly `{version:a105_figure_inputs_v1,arguments,sources,literals,
interpretations,recipe,measurements,cells}`. sources is the ordinary _Sources
manifest including every directly read source. literals/interpretations use
the existing source-witness meanings. recipe retains the unmodified parsed
selection document. measurements exactly `{first:<helper result>,second:<helper
result>|null}`. Helper results retain actual image hashes/size/selection/run.
No graph bytes in JSON. COMPONENTS in order:
`first_ordinate,second_ordinate,ordinate_difference`.

Cell shape exactly `{value,lower,upper,unit,origin,bound_kind,status,
unavailable_reason}` from the native helper. Raw ordinates are graph_derived;
difference is derived, explicitly in percentage points for percent input.
Missing second gives unavailable second/difference with unit=null and reason
second_ordinate_unreported. Valid unequal native units preserve both raw cells
and leave only difference unavailable, unit=null, reason=ordinate_unit_mismatch.
Native no-pixels/ambiguous/cropped/range failures remain usable partial results;
comparison of unavailable inputs gives missing_ordinate as in the helper.
Never renormalize percentages, infer SD, choose favorable representations or
turn source labels into necessity/reliability categories.

Reader exports LITERAL_FIELDS,COMPONENTS,REASONS and figure_population_schema.
REASONS includes native no_bar_pixels,ambiguous_bar_runs,truncated_mean_edge,
numerical_model_range plus missing_ordinate,second_ordinate_unreported,
ordinate_unit_mismatch. _Sources must read source_ref even when no literals
are selected; raw source bytes need not be decoded just to establish custody.

## Storage and typed boundary

LiteratureFigureRepository extends LiteratureRateRepository, provider
literature.experimental.figure, recordversion literature_figure_record_v1,
tables literature_figure_operations/literature_figure_received. Reuse existing
selected run/episode/scope authority, transactional immutable publication,
assigned-page lineage for ALL direct refs (including recipe images), transitive
scoped provenance, exact subset validation, admission and saved-only forwarding.

Direct source order: root,recipe,firstimage,secondimage if any,literal sources
in fixed LITERAL_FIELDS order,interpretation witnesses; deduplicate preserving
order. Reader manifest may have a different insertion order but exact same set.
Store all parents in that direct order followed by unique scoped ancestors.

Bind source witnesses as first_subject_ref,first_partner_ref,second_subject_ref,
second_partner_ref,experiment_ref (reference records); endpoint_ref,
normalization_ref,function_ref(term);first_condition_ref,second_condition_ref
(assay_condition context). Each anchor must contain actual source/artifact and
byte span/quote; distinct field meanings remain distinct even for equal spans.

Payload exactly enough to preserve version,input_source_ref,input_artifact_ref,
input_source_refs,direct_input_source_refs,data_source_ref,extraction,
experimental_bindings,sheet:{cells}. No calculator work in read/replay.
read verifies original saved request, scope signature, record/sheet identity,
source/header bindings, extraction arguments/recipe image refs and saved cells.
Never reopen original recipe/paper/image bytes, call _Sources or helper functions
in read/project/operation replay. Receipt creation adds no observation/credit.

Typed row exactly sheet_ref,evidence_source_ref,data_source_ref,
first_image_source_ref,second_image_source_ref(nullable),ten binding refs,
component plus complete eight-field cell,formula_code,source_kind,
first_image_origin,second_image_origin(nullable),design (full closed object),
first_axis_unit,second_axis_unit(nullable), and fixed metadata:
evaluation_scope=reference_experimental_figure_ordinates,
statistical_uncertainty=not_extracted,
measurement_corrections=not_applied,
target_correspondence=not_evaluated,
partner_necessity=not_evaluated.

Formula codes fixed mapping first_ordinate->native_first_bar_linear_v1,
second_ordinate->native_second_bar_linear_v1,
ordinate_difference->native_first_minus_second_v1.
Row unit enum: native three units,relative_turnover_percentage_points,null.
graph cell bound_kind conditional_digitization_not_confidence_interval is never
renamed a confidence interval. Typed schema closed, x-source=literature_figure_cells.
No arbitrary prose. Invalid supplied returned numbers/meanings must be rejected.

## Coordinator integration and checks

Add lazy service, descriptor hashes, optional requested_figure_components,
catalog/dispatch, page-source guard, fact-source route and typed receipt route
through existing machinery. Full recurring scientific FIGURE_TASK must reach
every iteration, including lookups/reconstruction. Parent retains own TASK;
admitted figure rows render concise component/bounds tables and one design/
binding panel per sheet, with both molecule/partner sides and repeat meanings.
Exclude raw ROI/pixel hashes from parent steering; retain them in saved sheets.

Meaningful tests: actual native image reads, missing second/mean/unsupported
units, strict recipe/witness/finite validation, scope/unreceived/page lineage,
transaction/idempotence, saved-only reconstruction with readers/helpers and
original artifacts blocked plus SQL query_only, exact requested subsets,
forged metadata rejection, ordinary Workflow selected operation/typed delivery,
one observation per completed own action, zero bookkeeping credit, full recurring
TASK and parent scientific meaning. Retain original F420 pair comparisons and
explicit contrasting pixel fixtures. Do not mutate original case Store or livepin.
