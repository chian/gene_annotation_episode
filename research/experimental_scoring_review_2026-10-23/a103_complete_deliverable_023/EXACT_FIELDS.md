# A103 exact field crosswalk and targeted reader contracts

This describes the fields that a reader must populate in this research sheet. No reader, grader, investigation prompt or production integration is implemented here. Literature and datasets supply the same fields; arithmetic then has no model dependency. Semantic extraction may identify a spatial question or source statement, but it cannot invent numerical confidence, unknown denominators or coordinates.

## Types and numerical states

`Ref` is a nonempty reference to retained material; `Nat` is integer ≥0; `Real` is finite; `Unit` is [0,1]; `Signed` is [−1,1]. Null is never a numerical zero. Source quotations, custody and explanations reside in separately referenced records, not numerical cells or prompts.

Every calculated field uses `Cell` with these exact keys:

| Key | Type / rule |
| --- | --- |
| `state` | `point`, `bounded`, `not_applicable`, `invalid` |
| `point`, `lower`, `upper` | `Real|null`. For point: point=lower=upper. For bounded: point=null and finite ordered bounds. For not_applicable/invalid: all three null. |
| `units` | `fraction`, `signed_index`, `bp`, `genes`, `genomes`, `representatives`, `genes_per_genome`, or an exact native unit Ref |
| `origin` | `reported`, `dataset_observed`, `derived`, `synthetic`, `proposed_policy`; mixed calculations name input refs and use derived/proposed_policy as appropriate |
| `input_refs`, `calculation_ref` | Ref[], Ref; identify actual operands and the formula used |
| `missing_reason` | null or `not_reported`, `unknown_denominator`, `positive_selection`, `no_opportunities`, `empty_population`, `no_common_strata`, `unmapped_target`, `ambiguous_mapping`, `ambiguous_homolog`, `unreadable_context`, `unknown_metric_scale`, `unknown_direction`, `not_this_route`, `invalid_counts`, `invalid_weights`, `out_of_scope_channel` |
| `identification_uncertainty` | `none`, `finite_population_bounds`, `outer_bounds`, `scenario_bounds`, `not_applicable` |
| `sampling_interval` | null or `{lower:Real,upper:Real,level:Unit|null,method_ref:Ref,replication_unit_ref:Ref,source_ref:Ref}`; never synthesized from a count alone |
| `calibration_uncertainty` | `unreported`, `source_reported`, `not_applicable`; source_reported requires `calibration_ref:Ref`, otherwise calibration_ref=null |

A computational point can have unreported biological sampling/calibration uncertainty. `C`/`E` in a native row are not_applicable with null bounds. `E` for known C=0 is bounded [−1,1], point null, reason no_common_strata; t is point zero with that same explanatory reason. Entire empty populations yield C bounded [0,1], E/t bounded [−1,1], reason empty_population. Invalid input preserves valid source cells but produces invalid calculated cells with explicit affected paths.

`ReportedNumber` has `{value:Real|null, units:Ref, precision:exact_record|rounded|approximate|censored|unreported, lower:Real|null, upper:Real|null, source_ref:Ref, locator_ref:Ref}`. ReportedNumber bounds are only those actually supplied by the source. Approximate one-third with no stated error has value 1/3, precision approximate and null source bounds; it does not automatically produce a point frequency. Count-derived identification bounds use Cell separately.

## Sheet and question inputs

| Exact path | Type and exact meaning | Populator |
| --- | --- | --- |
| `axis_id`, `sheet_version`, `scope` | literal A103; Ref; literal `genomic_arrangement_and_neighborhood` | Assignment/version record |
| `target.material_kind`, `material_ref`, `selected_interval`, `completeness` | `sequence|selected_file_record|snippet`; retained bytes Ref; null or `{start:Nat,end:Nat,coordinate_system:Ref}`; `complete|partial|unknown` | `map_supplied_material_to_loci` preserves the supplied selection |
| `target.locus_mapping`, `locus_candidates`, `mapping_evidence_refs` | `unique|ambiguous|unmapped`; Ref[]; Ref[] | Same function, from native mapping outputs |
| `candidate` | null during discovery, otherwise `{candidate_ref:Ref,context_predicate_refs:Ref[],unsupported_specificity:Ref[]}` | Source-grounded functional interpretation, separate from numerical grading |
| `context_questions[]` | Question records below; unique question_ref | Declared spatial questions, not automatically generated per hit |
| `question_weights[]` | `{question_ref:Ref,weight:Unit,origin:proposed_policy,policy_ref:Ref}` | Declared weights; nonempty sets sum to exactly 1 in their stated numeric representation |
| `allowed_scenarios[]` | `{scenario_ref:Ref,input_record_refs:Ref[],reason:ambiguous_mapping|conflicting_source|specified_sensitivity}` | Explicit alternative consistent input tables; not independent evidence |
| `source_component_links[]` | `{source_ref:Ref,locator_ref:Ref,component_paths:Ref[],coverage:inherited_primary_review|inherited_program_review|own_cross_case_read|own_synthetic_check}` | Provenance only, never a strength score |

Paths in the next tables are relative to `context_questions[]` unless prefixed otherwise.

| Exact path | Type and meaning | Populator |
| --- | --- | --- |
| `question_ref`, `scope_ref` | Ref, Ref; same scoped relation across its rows | Declared question |
| `predicate.relation` | `proximity|gene_order|orientation|module_colocation|native_neighborhood_association`; spatial module_colocation requires coordinates, not just genome-wide presence | Declared question |
| `predicate.subject_ref`, `anchor_or_module_ref`, `expected_pattern_ref`, `direction_evidence_ref` | Ref each; source-grounded relation to a possible function | Interpreted question with retained evidence |
| `predicate.spatial_rule` | null for native-only; otherwise `{same_contig_required:bool,max_intervening_genes:Nat|null,strand_relation:same|opposite|specified_order|any,ordered_gene_refs:Ref[],max_gap_bp:Real|null,coordinate_system:Ref,arc_rule_ref:Ref|null}`; conjunction of specified criteria | Declared endpoint, shared by foreground/background |
| `metric_route`, `metric_selection_basis` | `matched_context_counts|native_neighborhood_score|unavailable`; `declared_endpoint|specified_native_channel|historical_only` | One selected route; alternative route kept as auxiliary |
| `population.selection_mode`, `complete_denominator_known` | `enumerated_cohort|reported_positive_examples|native_program_population|unknown`; bool | Source table or declared dataset population |
| `population.counting_unit` | `locus|genome|dependence_block_representative|program_pair`; consistent in all numerator/denominator operands | Declared counting rule |
| `population.foreground_definition_ref`, `background_definition_ref`, `eligibility_rule_ref` | Ref or null when unknown; identify actual population and matching/sensitivity rules | Source or analysis definition |
| `population.members[]` | `{member_ref:Ref,side:foreground|background,stratum_ref:Ref|null,dependence_block_ref:Ref|null,observation_ref:Ref|null,eligible:bool|null,exclusion_reason_ref:Ref|null}`; unresolved eligible members stay planned | `extract_context_source_cells` or dataset selection |
| `population.dependence_rule_ref`, `representative_rule_ref` | Ref|null each; explicit pre-outcome block and selection rule | Source or declared analysis rule |
| `population.representatives[]` | `{dependence_block_ref:Ref,selected_member_ref:Ref,selection_basis_ref:Ref}`; supplied ranking resolves completeness then immutable-ID tie, or source-defined rule | `deduplicate_and_count_context` from declared rule/ranking, never endpoint outcomes |
| `source_event_refs`, `dependency_question_refs` | Ref[], Ref[]; repeated representations and shared data retained | Source-event equivalence declaration and deterministic joins |
| `reported_summary[]` | ReportedNumber[]; e.g. 150 genes, 127 genomes, approximately one-third; never coerced to complete planned counts | `extract_context_source_cells` |

## Observation and count inputs/outputs

| Exact path | Type and meaning | Populator |
| --- | --- | --- |
| `observations[].observation_ref`, `source_event_ref`, `source_ref`, `locator_ref` | Ref each | Literature passage/table or dataset row |
| `observations[].side`, `stratum_ref`, `dependence_block_ref` | foreground/background; Ref|null; Ref|null | Explicit population membership |
| `observations[].assembly_ref`, `contig_ref`, `subject_gene_ref`, `anchor_gene_ref` | Ref|null each; versioned coordinate identities | Selected annotation dataset or source |
| `observations[].homolog_native_measurements[]` | `{gene_ref:Ref,program:Ref,version:Ref|null,score_name:Ref,value:Real|null,units:Ref,query_length:Nat|null,aligned_length:Nat|null,subject_length:Nat|null,database_ref:Ref|null}` | Preserve available search/identity/alignment outputs |
| `observations[].homolog_assignment` | `resolved|ambiguous|not_detected|unexamined`; synthetic fixture's old `resolved_in_synthetic_fixture` maps to resolved with origin synthetic | Mapping/extraction evidence |
| `observations[].coordinates` | null or `{subject_start:int,subject_end:int,subject_strand:+|-|unknown,anchor_start:int,anchor_end:int,anchor_strand:+|-|unknown,same_contig:bool|null,contig_length:Nat|null,circular:bool|null,coordinate_system:Ref,unwrapped_arc_ref:Ref|null}` | Dataset positions; no invented values for a quoted “next to” |
| `observations[].gap_bp`, `intervening_gene_count`, `endpoint_value` | int|null; Nat|null; 0|1|null | `measure_genomic_relation`; unknown predicates remain unresolved |
| `observations[].readability`, `origin` | `observed_complete_window|contig_edge|assembly_missing|gene_call_uncertain|source_only_relation|unknown`; reported/dataset_observed/synthetic | Source observation, not an inferred quality score |
| `observations[].selected_representative`, `duplicate_of` | bool|null; Ref|null | Declared block representative and source-event deduplication |
| `strata[].stratum_ref`, `definition_ref` | Ref each; matching conditions and membership rule | Declared comparison design |
| `strata[].foreground`, `background` | Each `{planned_n:Nat|null,observed_positive_k:Nat|null,observed_negative_k:Nat|null,unresolved_u:Nat|null}`; full known counts sum to planned_n | `deduplicate_and_count_context`; positive-only selection cannot populate complete n |
| `strata[].p`, `b`, `a`, `a0`, `m` | Cell, fraction | `calculate_context_cells`; formulas in NUMERICAL_SHEET.md |
| `strata[].contrast`, `weighted_contrast` | Cell, signed_index | Same; weighted_contrast=0 when m=0 even if contrast bounded/unknown |
| `C`, `E`, `t` | Cell; C fraction, E/t signed_index | Same, including empty-population and zero-common-mass branches |

For composite predicates, an observed decisive false criterion can establish event 0; all required criteria must be observed true to establish 1; otherwise event is null. This is three-valued conjunction, not conversion of missing criteria to false. For gene_order or circular cases, the supplied ordered/unwrapped positions must make the selected comparison computable; unresolved geometry returns missing operands rather than an improvised ordering.

## Native neighborhood inputs/outputs

| Exact path `native.*` | Type and calculation |
| --- | --- |
| `program`, `program_version`, `database_version`, `definition_ref` | Ref|null each; actual retained identity and score/scale documentation |
| `pair_ids`, `taxon_ref` | Exactly two distinct Ref values; Ref; preserve exact scored entities even if target mapping is unresolved |
| `target_mapping_status`, `mapping_evidence_refs` | `exact_scored_entity|mapped_supplied_material|ambiguous|unknown`; Ref[] |
| `channel` | Literal `neighborhood` for the contributing route. Fusion, cooccurrence, combined, coexpression and other channels cannot fill this t. |
| `field_name`, `raw_value`, `raw_scale` | Ref; Real|null; `unit_interval|integer_thousandths|unsupported`. For supported decimal scale s=raw; for documented integer thousandths s=raw/1000. Unknown scale gives no point s. |
| `score` | Cell, fraction; original raw value retained separately |
| `direction`, `direction_evidence_ref` | `supports_context_predicate|opposes_context_predicate|undetermined`; Ref|null. Maps only to +1, −1 or unresolved sign. |
| `calibration_endpoint`, `calibration_population_ref` | `functional_association|same_metabolic_map_benchmark|unreported`; Ref|null. A claimed physical-interaction or exact-function endpoint requires a different justified input contract; it is not silently read into neighborhood. |
| `included_evidence` | `{direct:bool|null,transferred:bool|null,source_genome_refs:Ref[]|null}`; missing source details remain unknown |
| `retrieval` | `{record_ref:Ref,timestamp:Ref|null,network_type:Ref|null,cutoff:Real|null,limit:Nat|null,returned_rows:Nat|null,selected_pair_rows:Nat,truncated:bool|null}`; missing row is not a zero score |
| `auxiliary_channel_values[]` | `{field_name:Ref,raw_value:Real,units:Ref,source_ref:Ref}`; audit-only with no formula path into t |

## Exact result record

These are output names, not optional prose. All numerical objects are full Cells as defined above.

```
axis_id: A103
sheet_version: Ref
candidate_ref: Ref|null
context_predicate_refs: Ref[]
question_results[]:
  question_ref: Ref
  weight: Unit
  metric_route: matched_context_counts|native_neighborhood_score|unavailable
  C: Cell
  E: Cell
  t: Cell
  native_score: Cell|null
  stratum_results[]: {stratum_ref, p:Cell, b:Cell, a:Cell, a0:Cell,
                     m:Cell, contrast:Cell, weighted_contrast:Cell}
supporting_total: Cell
opposing_total: Cell
coordinate: Cell
projection_status: point|bounded|no_evidence|invalid_input
calibration_status: support_index_not_exact_function_probability
missing_input_paths: Ref[]
failures[]: {code:Ref, affected_paths:Ref[], source_refs:Ref[]}
duplicate_observation_refs: Ref[]
excluded_member_refs: Ref[]
dependency_question_refs: Ref[]
source_component_links[]: {source_ref, locator_ref, component_paths, coverage}
scenario_results[]: {scenario_ref:Ref, coordinate:Cell}
```

`projection_status=point` requires a point coordinate, but it does not erase unreported biological uncertainty. No-question/no-candidate results use no_evidence and bounded coordinate [0,1]. Identical bounds may identify a result despite unresolved zero-weight inputs. Invalid weights/counts give invalid_input with preserved valid source fields, not a biological zero.

## Separate targeted functions — all intentionally unimplemented

| Function | Exact inputs | Exact populated paths / calculation boundary |
| --- | --- | --- |
| `extract_context_source_cells` | Retained selected passage/table, source and locator, endpoint definition | `reported_summary`, `population.selection_mode`, actually reported counts and observation fields; approximate summaries stay ReportedNumber, not fabricated count tables |
| `map_supplied_material_to_loci` | Actual material/selection, selected reference collection and native mapping outputs | `target.*`, `observations[].homolog_native_measurements`, homolog_assignment, native target_mapping_status; all mappings retained, no highest-score locus selection without supported resolution |
| `measure_genomic_relation` | Exact coordinates/annotation rows, supplied spatial_rule and locus/readability evidence | `gap_bp`, `intervening_gene_count`, `endpoint_value`; deterministic geometry or typed missing fields |
| `deduplicate_and_count_context` | Observations, enumerated planned members, source-event equivalences, dependence rule and pre-outcome representative ranking | Duplicate/exclusion lists; selected_representative; exact positive/negative/unresolved/planned counts per side/stratum; does not treat count as independent replication without a justified design |
| `read_native_context_channel` | Exact retained response, documented channel/scale, exact pair mapping and retrieval bounds | `native.*`; only neighborhood fills score; combined and other fields remain auxiliary; unsupported channel/scale produces typed failure |
| `calculate_context_cells` | Exact count fields or native score/direction, declared fixed question weights and consistent scenarios | `p,b,a,a0,m,contrast,weighted_contrast,C,E,t,S,O,c`, bounds and missing paths from the numerical sheet; zero mass is checked before division |

Source semantics, mapping uncertainty and the declared question remain explicit inputs. A numerical grader has no discretion to replace missing empirical operands with an overall intuitive grade. The investigation prompt remains a separate responsibility and is neither constructed nor modified by this contract.

## Crosswalk from draft 011 — additive corrections in this deliverable

| Older path / statement | Consolidated treatment | Reason |
| --- | --- | --- |
| `predicate.relation=genomic_cooccurrence`; native fusion/cooccurrence options | Not permitted in the contributing scope; only spatial relation enums and native neighborhood remain | Parent review 003 explicitly limited its review to arrangement/neighborhood |
| `metric_route=native_context_score` | `native_neighborhood_score` | Name exposes the actual reviewed channel boundary |
| Native `query_subject`, `query_anchor` | `pair_ids` plus separate target mapping and predicate subject/anchor fields | Exact pair custody does not assume labels establish mapping or an ordered biochemical role |
| NumericCell required finite bounds even for native C/E “not applicable” | Explicit Cell state; not_applicable has null point/bounds | Removes contradictory schema/example handling without inventing C=E=1 |
| Count checker divided k/n before testing common mass | Compute shares first; zero m has point weighted_contrast=0 without resolving g | Preserves parent's verified zero-common-mass correction |
| Entire empty population | Unknown shares and t; not zero | Parent 003 distinction retained |
| Approximate or selected-positive literature values | `reported_summary` with precision and selection mode, distinct from complete `strata` counts | Stops 1/3→50 or 9/9→full prevalence conversions |
| Missing direction, shared scenarios and zero weights | Exact interval propagation, consistent-scenario envelope, and skip zero-weight arithmetic | Completes numeric joins without adding a new conceptual axis |

All original files and historical measurements remain unchanged. These are prospective research-sheet clarifications, not a migration of production or saved-run state.
