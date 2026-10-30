# Retained experimental partner-input reader

This binds PARTNER_COMPONENT_INTERFACES_015.md to source custody. Fresh reader
owner exclusively owns gene_annotation_episode/literature_partner_inputs.py and
tests/test_literature_partner_inputs.py. Calculator owner exclusively owns its
two files. Coordinator owns all records and examples. No existing production
file changes, new episodes, source acquisition, model calls, SQL or state writes.

The reader implements a retained-measurements boundary, not automatic extraction
of arbitrary publisher prose/figures. The Pdx conversion is explicitly coordinator
transcription from publisher web rendering. Do not claim a native PDF parser or
actual model interpretation. Primary-table/trace readers can later supply the
same numerical inputs. No computational A101 or A107 grading is added.

Export read_partner_inputs(arguments,*,read_source), partner_population_schema(),
LITERAL_FIELDS, COMPONENTS, SOURCE_KINDS and DATA_VERSION.
Closed selected args exactly {source_ref,data_source_ref,source_kind,literals,
interpretation_witnesses}. Both refs required nonnull; source_kind uses existing
literature_assay_inputs.SOURCE_KINDS. No numerical scientific values in args.
Witness schema is existing _Sources exact byte/UTF8/source witness schema.
LITERAL_FIELDS in fixed order: subject,partner,experiment,endpoint,normalization,
reference_condition,omitted_condition,addback_condition,function. Each is nullable
witness. Interpretation witnesses are an array of ordinary witnesses.

Read root source original bytes, even if no literal is selected; arbitrary
binary root source need not decode. Read data_source_ref original bytes as
strict UTF8 JSON with closed exactly {version:literature_partner_selection_v1,
inputs:<the exact calculator input object>}. Reject duplicate keys at every
level, NaN/infinity/overflowing float tokens and decimal underflow; reuse _numeric
for floating tokens. Specific malformed-source errors preserve callback and
ExperimentalContractError failures. All numeric operands/conditions come from
these retained bytes, not selected-operation model arguments. Source callback
signature and result match existing _Sources (artifact_ref,content bytes).

Validate all supplied literal/interpretation witnesses against original source
bytes, retaining enriched artifact/span custody. If any arm declares complete
condition coverage, require at least one interpretation witness; its presence
verifies custody, not scientific correctness/completeness. With source_kind
synthetic_fixture require synthetic measurement origin for every nonnull arm.
Use populate_partner_components(recipe.inputs) once; propagate its specific
contract failures and valid partial cells. Do not convert spread semantics,
match unlike units, infer zero, fix unknown normalization or choose a partner
requirement threshold. Inputs, arguments and source bytes stay unchanged.

Return exactly {version:literature_partner_inputs_extraction_v1,arguments,
sources,literals,interpretations,recipe,calculation,cells}. sources is the list
of directly read source refs in _Sources insertion order. Each literal is null
or {value:<exact quote>,witness:<enriched witness>}. interpretations is enriched
witness list. recipe preserves parsed source input; calculation is the complete
calculator return; cells is a deep copy of its eight numerical cells. No raw
source bytes in output. COMPONENTS reexports calculator order.

The source_kind does not turn retained numeric JSON into directly parsed paper
measurements. Original source and transcription lineage must be retained by
future storage/consumers. These are source checks and a calculator, not a source
truth or annotation-acceptance gate. Selected persistence, actual catalog/TASK,
typed parent boundary and saved-only reconstruction remain unfinished.

Meaningful tests: actual callback byte reads/dedup including binary root; UTF8
quote and artifact custody; correct matched point and censored-domain propagation;
known differing nitrogen factors/unreported mass normalization preserving native
cells; strict JSON/schema/no numeric args; bad source result and callback errors;
bad witness offsets/quotes; complete-condition witness requirement; source-kind
synthetic consistency; no caller mutation. Synthetic fixtures stay labeled.
