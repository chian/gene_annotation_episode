# A103 exact sheet fields and proposed populating interfaces

This is the input/output contract for a research sheet, not a production reader implementation. All proposed populating functions below are **unimplemented**. The standalone `check_arithmetic.py` checks manually populated fixtures only; it does not read papers, query an annotation target, populate production state or claim A103 implementation.

## Typed conventions

`Ref` is a nonempty internal reference. `Nat` is integer ≥0. `Unit` is finite real in [0,1]. `SignedUnit` is finite real in [−1,1]. `Bound<T>` has `{lower:T, upper:T}`, lower ≤upper. No NaN/Infinity JSON numbers. `Nullable<T>` is T or null, accompanied by a reason. A missing quantity is never encoded as numerical zero. `provenance_kind` is one of `reported`, `dataset_observed`, `derived`, `synthetic`, `proposed_policy`. Measured quantities retain precision as `exact_record`, `rounded`, `approximate`, `censored`, or `unreported`.

## Sheet and target fields

| Exact path | Type | Input and meaning |
| --- | --- | --- |
| `axis_id` | literal `A103` | This axis only. |
| `sheet_version` | Ref | New revisions retain old snapshots; do not rewrite saved observations. |
| `target.material_kind` | `sequence`, `selected_file_record`, `snippet` | Actual supplied starting material. |
| `target.material_ref` | Ref | Actual bytes/file selection, not an inferred public name. |
| `target.selected_interval` | null or `{start:Nat,end:Nat,coordinate_system:enum}` | Required for region/snippet selections; preserve inclusivity conventions. |
| `target.completeness` | `complete`, `partial`, `unknown` | Does not receive a default numerical confidence. |
| `target.locus_mapping` | `unique`, `ambiguous`, `unmapped` | Mapping outcome, separate from functional annotation. |
| `target.mapping_evidence_refs` | Ref[] | Native alignment/search/sequence-identity evidence. |
| `target.locus_candidates` | Ref[] | All supported loci; never arbitrarily select one from a tie. |
| `candidate` | null or `{candidate_ref:Ref,context_predicate_refs:Ref[],unsupported_specificity:enum[]}` | Null during discovery. Unsupported specificity enum: `exact_reaction`, `substrate`, `donor`, `complex_stoichiometry`, `causality`, `native_condition`, `none`. These are reporting qualifications, not numeric categories. |
| `context_questions` | Question[] | Explicit same candidate/scope question set, including unresolved questions. |
| `question_weights` | `{question_ref:Ref,weight:Unit,origin:proposed_policy}[]` | Must sum to 1 for a nonempty set. Proposed equal value 1/J; no automatic citation or genome-count weighting. |
| `projection_status` | `point`, `bounded`, `no_evidence`, `invalid_input` | Distinguishes arithmetic results from missing evidence. |

## Question fields

| Exact path within each Question | Type | Populated meaning |
| --- | --- | --- |
| `question_ref` | Ref | One contextual relation, not one paper. |
| `predicate` | `{relation:enum,subject:Ref,anchor_or_module:Ref,expected_pattern:Ref}` | `relation` is `proximity`, `gene_order`, `orientation`, `module_colocation`, `genomic_cooccurrence`, `native_neighborhood_association`. Expected pattern defines the endpoint. |
| `metric_route` | `matched_context_counts`, `native_context_score`, `unknown` | One route supplies this contribution; other measurements remain auxiliary. |
| `metric_selection_basis` | `declared_endpoint`, `specified_native_channel`, `historical_only` | Records why the metric answers the question; no “largest score” option. |
| `population.members` | PopulationMember[] | Every planned genome/locus opportunity where known, including missing or excluded members and reasons. |
| `population.selection_mode` | `enumerated_cohort`, `reported_positive_examples`, `native_program_population`, `unknown` | Prevents positive examples from being misrepresented as the full denominator. |
| `population.complete_denominator_known` | boolean | Meaningful factual metadata, not a support multiplier. |
| `population.counting_unit` | `locus`, `genome`, `dependence_block_representative`, `program_pair` | Consistent numerator/denominator and deduplication. |
| `population.dependence_rule_ref` | Nullable<Ref> | Explicit block definition; unknown cannot imply independence. |
| `population.representative_rule` | `assembly_completeness_then_id`, `source_defined`, `not_applicable`, `unknown` | Applied before looking at spatial outcomes. Source-defined filtering retained verbatim in provenance. |
| `source_event_refs` | Ref[] | Links that merge repeated representations. |
| `dependency_question_refs` | Ref[] | Overlapping windows, same operon, shared genome evidence or common native score. |
| `allowed_scenarios` | Ref[] | Conflicting locus reports/ambiguous homolog mappings produce alternative consistent tables. |

### Native score fields

| Path `native.*` | Type | Exact use |
| --- | --- | --- |
| `program`, `program_version`, `database_version` | Nullable<Ref> each | Known native identity; missing version visible. |
| `query_subject`, `query_anchor`, `taxon` | Ref each | Exact scored pair and organism, not user-supplied labels assumed equivalent. |
| `target_mapping_status` | `exact_scored_entity`, `mapped_supplied_material`, `ambiguous`, `unknown` | The last two give bounded target contribution; retained pair score itself remains measured. |
| `channel` | `neighborhood`, `fusion`, `genomic_cooccurrence`, `combined`, `other` | This example uses only neighborhood; combined is audit-only and cannot fill A103 contribution. Each additional channel requires its documented genomic interpretation. |
| `field_name` | Ref | E.g. STRING `nscore`. |
| `raw_value` | Nullable<finite real> | Original reported value. |
| `raw_scale` | `unit_interval`, `integer_thousandths`, `other` | Known transform, never guessed from magnitude. |
| `score` | Nullable<Unit> | Identity transform for API decimals; raw/1000 only for documented integer scale. |
| `direction` | `supports_context_predicate`, `opposes_context_predicate`, `undetermined` | Explicit semantic bearing. Does not turn strength words into grades. |
| `direction_evidence_ref` | Nullable<Ref> | Needed especially for alleged incompatibility. |
| `calibration_endpoint` | `functional_association`, `same_metabolic_map_benchmark`, `physical_interaction`, `exact_function`, `unreported` | What the native scale actually evaluates, not what one hopes it evaluates. |
| `calibration_population_ref`, `validation_interval` | Nullable<Ref>, Nullable<Bound<Unit>> | Missing remains missing. These are not default 1 multipliers. |
| `included_evidence` | `{direct:bool|null,transferred:bool|null,source_genome_refs:Ref[]|null}` | Compact API may leave unknown; do not assert direct-only support. |
| `retrieval` | `{timestamp:Ref,network_type:enum,cutoff:finite real|null,limit:Nat|null,returned_rows:Nat,selected_pair_rows:Nat,truncated:bool}` | Detects nondetection caused by filtering, top-k or mapping failure. |
| `auxiliary_channel_values` | `{field:Ref,value:finite real}[]` | Audit only; excluded from current A103 arithmetic. |

### Counts, strata and observations

| Path | Type | Exact input/calculation |
| --- | --- | --- |
| `observations[].assembly_ref`, `contig_ref`, `subject_gene_ref`, `anchor_gene_ref` | Nullable<Ref> | Real coordinate source/version where available. |
| `observations[].side` | `foreground`, `background` | Declared tested/context-null population. |
| `observations[].dependence_block_ref`, `stratum_ref`, `source_event_ref` | Nullable<Ref> | Distinct roles: dependence, comparability, and duplicate provenance. |
| `observations[].homolog_native_measurements` | `{gene_ref,program,score_name,value,units,query_length,aligned_length,subject_length,database_ref}[]` | Native bits/E-values/coverage; do not call them gene-context scores. Missing numeric values explicit. |
| `observations[].homolog_assignment` | `resolved`, `ambiguous`, `not_detected`, `unexamined` | Only adequately surveyed resolved relationships give observed spatial absence. |
| `observations[].coordinates` | null or `{subject_start:int,subject_end:int,subject_strand:enum,anchor_start:int,anchor_end:int,anchor_strand:enum,contig_length:Nat|null,circular:bool|null,coordinate_system:enum}` | Coordinates are 1-based closed in this draft's deterministic gap formula. Circular origin/endpoints must be handled explicitly. |
| `observations[].gap_bp`, `intervening_gene_count` | Nullable<int>, Nullable<Nat> | Measured spatial quantities. |
| `observations[].endpoint_value` | 0, 1 or null | Actual declared spatial predicate result. |
| `observations[].readability` | `observed_complete_window`, `contig_edge`, `assembly_missing`, `gene_call_uncertain`, `source_only_relation`, `unknown` | Unknown bp can coexist with a narrower source-reported relation; do not infer stronger endpoints. |
| `observations[].selected_representative` | boolean or null | Deterministic from predeclared dependence/representative rules; no outcome-based selection. |
| `observations[].duplicate_of` | Nullable<Ref> | Duplicate representations excluded before counting. |
| `strata[].stratum_ref` | Ref | Declared measured comparison conditions. |
| `strata[].foreground` and `.background` | `{planned_n:Nat|null,observed_positive_k:Nat|null,observed_negative_k:Nat|null,unresolved_u:Nat|null}` | For enumerated strata: positive + negative + unresolved = planned. Positive-only reports cannot silently set unresolved=0. |
| `strata[].p`, `.b` | `{point:Unit|null,bounds:Bound<Unit>}` | Known complete stratum: exact fraction. Unresolved: use k/n to (k+u)/n. |
| `strata[].a`, `.a0`, `.m` | `{point:Unit|null,bounds:Bound<Unit>}` | Share of planned foreground/background population; minimum common share. |
| `strata[].contrast` | `{point:SignedUnit|null,bounds:Bound<SignedUnit>}` | g(p,b) and monotone bounds. |
| `C`, `E`, `t` | NumericCell each | C is overlap; E common-stratum average; t signed contribution. C=0 gives t=0 and E null with `no_common_strata`. |

`NumericCell` is `{point: finite real|null, lower:finite real, upper:finite real, calculation_ref:Ref, origin:enum, missing_reason:enum|null, uncertainty_kind:enum}`. Missing reasons include `not_reported`, `unknown_denominator`, `positive_selection`, `unmapped_target`, `ambiguous_homolog`, `unreadable_context`, `unreported_calibration`, `unknown_metric_scale`, `no_common_strata`, `no_opportunities`. Uncertainty kind is `computational_value`, `finite_population_identification_bounds`, `reported_sampling_interval`, `unreported_sampling_uncertainty` or `synthetic_check`.

## Exact numeric output

```
{
  "axis_id": "A103",
  "candidate_ref": "...",
  "context_predicate_refs": ["..."],
  "question_results": [{
    "question_ref": "...", "weight": 0.0,
    "C": {"point": null, "lower": 0.0, "upper": 1.0},
    "E": {"point": null, "lower": -1.0, "upper": 1.0},
    "t": {"point": null, "lower": -1.0, "upper": 1.0},
    "metric_route": "...", "native_score": null
  }],
  "supporting_total": {"point": null, "lower": 0.0, "upper": 1.0},
  "opposing_total": {"point": null, "lower": 0.0, "upper": 1.0},
  "coordinate": {"point": null, "lower": 0.0, "upper": 1.0},
  "projection_status": "bounded",
  "calibration_status": "support_index_not_exact_function_probability",
  "missing_input_paths": [],
  "sampling_uncertainty": "unreported",
  "outside_A103_specificity": [],
  "duplicate_observation_refs": [],
  "dependency_question_refs": [],
  "source_component_links": []
}
```

The numeric shape above is an unknown-value illustration, not a literal valid nonempty weighted sheet: actual question weights must sum to 1. Native-only rows have C/E **not applicable**, rather than numerical 1 masquerading as measured comparability. `t` still contains the actually selected native numerical score. Use the complete typed numeric cells in an actual output, including origin and uncertainty meaning.

## Separate targeted functions that would populate these fields

| Proposed function; status | Input | Exact outputs and deterministic boundary |
| --- | --- | --- |
| `extract_context_source_cells`; unimplemented | Selected paper table/passage and source locator | Observation identities, reported k/n or approximate fraction, selection mode, endpoint definition, native score if actually printed. It cannot infer denominators from “many” or make 1/3 into exact 50/150. Human/reader semantic extraction remains auditable. |
| `map_supplied_material_to_loci`; unimplemented | Actual supplied bytes/region, defined genome/reference collection and native search outputs | Locus candidates, native identification measurements, completeness/ambiguity. It does not require a public gene name or choose a function. |
| `measure_genomic_relation`; unimplemented | Explicit selected GFF/GenBank coordinates, complete assembly context and a stated predicate | gap_bp, orientation, intervening count, endpoint_value/readability. No score of molecular function is inferred. |
| `deduplicate_and_count_context`; unimplemented | Observation rows, source-event equivalences, dependence blocks and predeclared representative rule | Unique representative positive/negative/unresolved counts in each stratum, all exclusions/reasons retained. |
| `read_native_context_channel`; unimplemented | Exact program response plus official field/scale definition and mapped pair | Native score cells and auxiliary audit channels. Rejects combined-score substitution and exposes truncated/missing responses. The skill call made here is a research data retrieval, not this production reader. |
| `calculate_context_cells`; unimplemented | Those populated exact counts, shares or selected native score, direction and weights | C/E/t/S/O/c plus interval bounds exactly as defined in NUMERICAL_SHEET.md. No model call is needed for the arithmetic. |

Literature tables and genome datasets feed the **same** observation/count/native cells. Neither becomes a different scoring axis or a mandatory workflow step. Model interpretation, when needed to map a contextual relation to a scoped candidate, supplies the declared semantic predicate/direction and source; it never substitutes a confidence adjective for native measurements.
