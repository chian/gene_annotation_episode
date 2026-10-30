# Explicit calculations and the accepted biological-group extension

Proposed next contracts, 2026-10-25. Existing public pure signatures and saved results remain unchanged except the explicitly accepted additive `TestFamily.p_value_basis` value below. All operands and results are finite JSON after tuple-to-list serialization. Parameters are retained verbatim with each result. No expression evaluator, arbitrary JSON path, weighted-score DSL, runtime resource choice or acquisition is introduced.

## Existing pure functions to call directly

The complete installed implementations inspected are `bvbrc_msa_calculators.py`, `bvbrc_msa_calculation_contracts.py`, `bvbrc_metacats_calculators.py`, `bvbrc_metacats_calculation_contracts.py`, `phylogeny_calculators.py`, `phylogeny_calculation_contracts.py`, and their format/value contracts. They are the exact mathematical dependencies, not proposed replacements.

```python
msa_native_entropy(alignment, *, analysis_id, population, alphabet,
    case_policy, terminal_gap, observed_table, native_rounding)
# alphabet=dna|protein; case_policy=uppercase; terminal_gap='-';
# observed_table=MSAFrequencyTable|null;
# native_rounding=binary64_fixed_2_ties_to_even|null.

msa_reference_differences(alignment, *, analysis_id, population, reference,
    member_row_indices, alphabet, case_policy, original_correspondences)
# reference=ReferenceBinding; alphabet=dna|protein;
# case_policy=preserve|uppercase; member_row_indices=tuple[index,...];
# original_correspondences=tuple[Correspondence,...].

metacats_group_counts(alignment, *, analysis_id, population, assignments,
    category_id, group_order, case_policy, terminal_mask, native_input_hash_policy)
# assignments=tuple[GroupAssignment,...]; group_order=tuple[GroupColumn,...];
# case_policy=preserve|uppercase; terminal_mask=native_terminal_dash_to_hash;
# native_input_hash_policy=exclude_hash.

metacats_statistics(counts, *, alphabet, epsilon, nucleotide_padding,
    omnibus_continuity, pair_df_policy, pair_zero_policy,
    selected_pairs, distribution_backend)
# alphabet=na|aa; epsilon>=0; nucleotide_padding=ACGT_at_variable_sites;
# omnibus_continuity=r_default_2x2_min_delta;
# pair_df_policy=native_source|standard_pair;
# pair_zero_policy=retain_math_and_native_zero_to_one;
# selected_pairs=tuple[tuple[group_id,group_id],...];
# distribution_backend={name:scipy_chi2_integer_df_logtail_v1,
#                       version:actual installed scipy version}.

metacats_effects(counts, *, selected_pairs, zero_margin_policy)
# zero_margin_policy=drop_for_raw_effect_only.

adjust_p_values(p_values, *, family, method, alpha, dependence_assumption)
# p_values=tuple[{test_id:id,value:NumericCell},...];
# method=none|bonferroni|holm|bh|by; alpha in[0,1];
# dependence_assumption=none_required_between_tests|
#                      independent_or_positive_regression_dependence_assumed.

alignment_components(alignment, *, population, alphabet, case_policy, pairs=())
# alphabet=dna|rna|protein|unknown; case_policy=uppercase|literal;
# pairs=tuple[tuple[row_index,row_index],...].
ungapped_coordinate_map(alignment, *, row_indices)
original_member_coverage(alignment, *, population, members, correspondences)
# members=tuple[{row:{alignment_id,row_index},member:MemberRef,
# original_length:index|null,original_sequence_sha256:hex|null,evidence:[Evidence]},...].
function_composition(*, population, assignments, equivalences=())
# exact CompositionPopulation, FunctionAssignment, FunctionEquivalence records.
taxon_components(*, population, rank, assignments)
# exact TaxonPopulation, rank:id, TaxonAssignment records.
tree_components(tree, *, leaf_population, support_observations,
    native_measurements, branch_unit, pairs)
# exact saved TreeRecord; whole LeafPopulation; declared branch unit;
# pairs=tuple[tuple[node_index,node_index],...].
compare_unrooted_relationships(gene_tree, *, comparison_id, organismal_tree,
    injective_tip_join)
# injective_tip_join=tuple[TipJoin,...], no inferred taxon/name pairing.
```

Shared alignment, coverage, composition, taxon and tree results retain `SharedQuantity`; native MSA/MetaCATS results retain `NumericCell`. Neither is a functional annotation probability. Requested finite projections copy their saved values with original method/population/unit identity.

MSA entropy counts every eligible literal symbol, including ambiguous letters, stops and internal `-`; terminal dash bounds come from each full row before any site subset. `H = -sum(p*log2(p))` is in bits. The selected source score is `100*float(format(H,'.2f'))`; it is separate from the unrounded entropy and from the observed `Score`. The residual is observed score minus selected recalculation only with a unique matching full-population observation. Subsets and duplicate positions remain qualified. DNA blank count cells remain missing. Protein `Del`, `Xaa` and unrecognized tokens preserve their native identities.

Reference differences retain six categories (`identical_canonical`, `substitution`, `insertion_relative_to_reference`, `deletion_relative_to_reference`, `both_gap`, `ambiguous_or_other`) with explicit population counts. Ordinary ungapped positions are staged-sequence offsets. An absent original map does not erase staged comparisons or pretend they are original genome coordinates.

Native MetaCATS counts exclude original `#` separately from terminal dashes. All missing sites, conserved placeholders and variable positive-df tests remain distinct. For an incomplete sequence, a trailing run of dashes cannot be called terminal; root's corrected current calculator leaves it unresolved. Source reproduction pads missing A/C/G/T only at variable NA sites and adds selected epsilon to every retained cell. Omnibus default continuity correction applies only at 2x2; native AA pair df can use the full R-group count. Native pair numerical underflow returning 1 remains separate from mathematical p and log-p. Native cutoff is strictly `p < cutoff`; neither its empty table nor its returned row count establishes the full testing-family size.

## Accepted new biological-group path

Root explicitly accepted the following direction during this planning task: ordinary biological counts cannot require R-column evidence; share matching arithmetic with native reproduction without fabricating `GroupColumn` values. Standard pair df is the only biological pair estimator. Native full-category df remains exclusively in `metacats_statistics(...pair_df_policy='native_source')`.

New module `bvbrc_metacats_biological_calculators.py` and corresponding contracts:

```python
biological_group_counts(alignment: dict, *, analysis_id: str, population: dict,
    category_id: str, assignments: tuple[dict,...], group_population: dict,
    case_policy: str, terminal_gap_policy: str, original_hash_policy: str) -> dict
# case_policy=preserve|uppercase;
# terminal_gap_policy='exclude_terminal_dash'; original_hash_policy='exclude_hash'.
# assignments=BiologicalAssignment; group_population=BiologicalGroupPopulation.

biological_group_statistics(counts: dict, *, alphabet: str, epsilon: float,
    nucleotide_padding: str, omnibus_continuity: str, pair_df_policy: str,
    selected_pairs: tuple[tuple[str,str],...], distribution_backend: dict) -> dict
# alphabet=na|aa; epsilon>=0;
# nucleotide_padding='ACGT_at_variable_sites';
# omnibus_continuity='r_default_2x2_min_delta'; pair_df_policy='standard_pair'.
# same explicit installed distribution_backend as chi_square_tail.

biological_group_effects(counts: dict, *, selected_pairs: tuple[tuple[str,str],...],
    zero_margin_policy: str) -> dict
# zero_margin_policy='drop_for_raw_effect_only'.
```

Resolved row membership plus its actual group identity is sufficient for biological counting; missing original `MemberKey` does not invalidate an otherwise explicit alignment-row/group join. `member_key=null` remains an original-identity qualification. One row cannot belong to two groups within the same category; overlap across categories remains represented. A group population supplies explicit group order and completeness, not R order. No group is removed because it has no observed residues.

All fields of the new results are defined here:

```text
CountSite = {table_id:id,column_0based:index,
  state:all_missing|conserved|variable|unresolved,symbols:[one-character-string],
  observed_counts:[[index]],included_rows_by_group:[[index]],
  excluded_terminal_rows_by_group:[[index]],
  excluded_original_hash_rows_by_group:[[index]],internal_gap_rows_by_group:[[index]],
  unresolved_row_indices:[index],completeness:Completeness,evidence:[Evidence]}
BiologicalCounts = {status:ok|partial|invalid,analysis_id:id,population_id:id,
  alignment_id:id,category_id:id,group_population:BiologicalGroupPopulation,
  method_parameters:{case_policy:preserve|uppercase,
    terminal_gap_policy:'exclude_terminal_dash',original_hash_policy:'exclude_hash'},
  sites:[CountSite],requirements:[Requirement],diagnostics:[Diagnostic]}
```

`observed_counts` is symbols-by-declared-groups. Symbols are sorted exact characters actually included, with no zero-only symbol row. Every counted row contributes one observation to one group. Terminal exclusions, original-hash exclusions and unresolved rows are disjoint from included rows. Internal gaps are an included subset. The output matrix contains raw integer observations, no pseudocounts. `table_id` is `biological_group_counts:` plus SHA256 of canonical JSON containing analysis ID, full AlignmentPopulation, actual alignment artifact/ID, category, complete group population, column, explicit parameters and actual assignments. It cannot alias a native count table or a different membership assignment. Missing population/membership/truncated rows retain observed counts with unresolved state; full-population inferential values are null until those requirements are met.

```text
BiologicalStatisticalCalculation = {test_id:id,kind:omnibus|pairwise,category_id:id,
  column_0based:index,group_ids:[id],raw_table_id:id,raw_symbols:[text],
  augmented_symbols:[text],group_population_count:index,epsilon:NumericCell,
  augmented_counts:[[number]],expected_counts:[[number]],augmented_total:NumericCell,
  continuity_delta:NumericCell,chi_square:NumericCell,df:NumericCell,
  mathematical_p:NumericCell,log_p:NumericCell,
  numerical_state:finite|underflow|unavailable,method_id:id,requirements:[Requirement]}
TestExclusion = {column_0based:index,test_kind:omnibus|pairwise,
  group_pair:[id,id]|null,reason:all_missing|conserved_placeholder|degenerate_df|unresolved}
BiologicalStatistics = {status:ok|partial|invalid,analysis_id:id,category_id:id,
  method_parameters:{alphabet:na|aa,epsilon:number>=0,
    nucleotide_padding:'ACGT_at_variable_sites',omnibus_continuity:'r_default_2x2_min_delta',
    pair_df_policy:'standard_pair',selected_pairs:[[id,id]],
    distribution_backend:{name:'scipy_chi2_integer_df_logtail_v1',version:id}},
  omnibus:[BiologicalStatisticalCalculation],pairs:[BiologicalStatisticalCalculation],
  exclusions:[TestExclusion],requirements:[Requirement],diagnostics:[Diagnostic]}
Adequacy = {table_id:id,minimum_expected:NumericCell,cells_below_5:NumericCell,
  cells_below_1:NumericCell,cell_denominator:NumericCell}
PairEffect = {group_ids:[id,id],frequency_deltas:[{symbol:text,value:NumericCell}],
  total_variation:NumericCell}
BiologicalEffectSite = {raw_table_id:id,column_0based:index,raw_chi_square:NumericCell,
  cramers_v:NumericCell,effective_symbol_count:index,effective_group_count:index,
  raw_expected:[[number]],raw_adequacy:Adequacy,
  positive_observed_cells_below_5:index,pairs:[PairEffect]}
BiologicalEffects = {status:ok|partial|invalid,analysis_id:id,category_id:id,
  zero_margin_policy:'drop_for_raw_effect_only',sites:[BiologicalEffectSite],
  requirements:[Requirement],diagnostics:[Diagnostic]}
```

Biological statistical rows do not contain `r_table_group_count`, `native_zero_rule_p` or native observation IDs. `group_population_count` is the declared count actually used. Omnibus df is `(R-1)*(K-1)`; pair df is `R-1` on the selected two columns, retaining source-comparable category symbol rows and the explicitly selected padding/epsilon policy. Inferential matrices and expected counts are saved separately from raw matrices. `E_ij = row_total_i * column_total_j / total`; use divide-before-multiply to avoid unnecessary overflow. Pearson is `sum((abs(O-E)-delta)^2/E)`; omnibus 2x2 delta is `min(.5, min(abs(O-E)))`, otherwise zero; pair delta is zero. Invalid expected margins produce a requirement, not a fabricated p value. Distribution backend remains pinned and test IDs include full parameters and raw-table ID. Underflow keeps mathematical p null/failed and finite natural-log p where obtainable; it never applies the native zero-to-one anomaly.

Raw effects drop zero margins only for that descriptive calculation. Pearson uses no pseudocount or continuity correction; `V = sqrt(X2 / (N*min(R-1,K-1)))`. Empty/one-dimensional denominators yield null. Frequency difference is selected group A's raw frequency minus B's; total variation is `0.5*sum(abs(delta))`. Adequacy reports minimum expected, count of expected cells `<5`, count `<1`, and total expected-cell count for that exact reduced table. `positive_observed_cells_below_5` is a different quantity; no label equates it with expected-count adequacy. Biological outputs have method IDs beginning `biological_group_`, never `metacats_native_`.

## Shared arithmetic, controlled refactor boundary

New `bvbrc_contingency_math.py` contains ordinary pure kernels:

```python
count_alignment_group_sites(alignment: dict, *, population: dict,
    row_groups: tuple[dict,...], group_count: int, groups_complete: bool,
    case_policy: str, terminal_gap_policy: str, original_hash_policy: str) -> list[dict]
# row_groups={row_index:index,group_index:index|null}; exactly one for each selected row.
# returned records are CountSite with table_id/evidence omitted. The caller supplies
# its actual table identity and population evidence. No category or R fields.

expected_contingency_counts(matrix: tuple[tuple[float,...],...]) -> dict
# {expected_counts:[[number]],total:number}; all inputs finite nonnegative, rectangular.
pearson_contingency_statistic(matrix: tuple[tuple[float,...],...], *,
    expected: tuple[tuple[float,...],...], continuity_delta: float) -> float|None
# None when empty or any expected cell <=0. No silent clamping of signed quantities.
```

Root accepted controlled refactor ownership of existing `bvbrc_metacats_calculators.py`: native count code lowers **its real GroupColumn map** to row/group indices; biological count code lowers **its real BiologicalGroupPopulation map** independently. Both call the count kernel. Existing `_expected` and `_chi_square` may become wrappers around these kernels. Keep `chi_square_tail` public signature and implementation, and call it from biological statistics. Existing native method IDs, result IDs, parameters, row order, qualification states, source anomalies and JSON results must remain byte-for-byte equivalent on saved replays. The shared kernel does not construct a fake native `counts` object. No native public validator accepts biological records.

## Additive multiplicity provenance, explicitly accepted by root

Extend the existing `validate_test_family` union with the third value `biological_mathematical_recalculation`. This is an additive accepted contract change, not an interpretation of an old source-backed record. No new FDR wrapper or duplicate family schema is needed. Existing `adjust_p_values` mathematical implementation and original saved results remain unchanged.

```text
TestFamily = {family_id:id,analysis_ids:[id],category_ids:[id],
  test_kind:omnibus|pairwise,test_ids:[id],eligibility:'variable_site_positive_df',
  population_state:complete|known_count_only|declared_upper_bound|unknown,
  total_test_count:index|null,assumption:null|{kind:independently_known_count|
    parent_declared_upper_bound,count:index,evidence:[Evidence]},
  p_value_basis:native_unadjusted|source_mathematical_recalculation|
    biological_mathematical_recalculation,evidence:[Evidence]}
```

The provider compiles exact test IDs from selected **full** statistical results or complete unfiltered native observations. It does not infer a family from exported significant rows. Complete families can include all declared categories or an explicit category/site/pair subset. Complete result enumeration includes explicit conserved/all-missing exclusions; these are not positive-df tests. `known_count_only`/`declared_upper_bound` require their supplied evidence and permit the existing Bonferroni exception only. BH requires the declared independent/positive-dependence assumption. BY retains its harmonic factor. A source or biological mathematical p underflow null cannot be silently replaced by native zero to complete a mathematical family.

## Separate expected-count adequacy helper, accepted by root

New `bvbrc_metacats_adequacy.py`:

```python
expected_count_adequacy(statistics: dict, *,
    statistics_kind: str) -> dict
# statistics_kind='native_reproduction'|'biological'; select the exact validator.
```

```text
ExpectedCountAdequacy = {status:ok|partial|invalid,analysis_id:id,category_id:id,
  statistics_kind:native_reproduction|biological,
  rows:[{test_id:id,raw_table_id:id,kind:omnibus|pairwise,column_0based:index,
    group_ids:[id],basis:'augmented_expected',
    minimum_expected:NumericCell,cells_below_5:NumericCell,cells_below_1:NumericCell,
    cell_denominator:NumericCell}],requirements:[Requirement],diagnostics:[Diagnostic]}
```

Consume the saved `expected_counts` of every valid omnibus/pair row, not observed cells, full-category counts for a two-column test, or reconstructed native p values. Each row's cell population is its actual `test_id`; method is `expected_count_adequacy_v1`. Units are `expected_observations` for minimum and `cells` for the other three. Count denominator is the exact matrix dimension product. Empty/unavailable expected matrices have null cells plus a requirement, not zero adequacy. Finite zero expected values remain observed calculated zeros (and count below thresholds), while the statistical result retains its invalid-margin requirement. Preserve input requirements. Do not mutate `metacats_effects.augmented_adequacy`, native tables or statistics. The old null field remains historical.

## Provider request tagged unions

Each provider accepts `CalculationParameters = {version:'bvbrc_msa_components_v1'|'bvbrc_metacats_components_v1', requests:[CalculationRequest]}`. Every request has unique `request_id:id`; all additional keys are exactly as listed. A reference to another request names its actual typed output. Reject cycles, duplicate IDs, undeclared references and wrong-kind references before calculating. Deterministic evaluation follows the declared dependency graph; it neither chooses work nor executes native programs. Independent requests survive another request's unavailable input.

```text
{kind:'alignment',request_id,population_id,alphabet:dna|rna|protein|unknown,
 case_policy:uppercase|literal,pairs:[[index,index]]}
{kind:'ungapped_map',request_id,alignment_id,row_indices:[index]}
{kind:'original_coverage',request_id,population_id}
{kind:'function_composition',request_id,population_id}
{kind:'taxonomy',request_id,population_id,rank:id}
{kind:'tree',request_id,population_id,branch_unit:<shared BRANCH_UNITS>,pairs:[[index,index]]}
{kind:'relationship_comparison',request_id,comparison_id,gene_tree_id,
 organismal_tree_id,injective_tip_join:[TipJoin]}
{kind:'msa_entropy',request_id,population_id,alphabet:dna|protein,
 case_policy:'uppercase',terminal_gap:'-',observed_table_id:id|null,
 native_rounding:'binary64_fixed_2_ties_to_even'|null}
{kind:'msa_reference_differences',request_id,population_id,reference:ReferenceBinding,
 member_row_indices:[index],alphabet:dna|protein,case_policy:preserve|uppercase}
{kind:'native_group_counts',request_id,population_id,category_id,
 case_policy:preserve|uppercase,terminal_mask:'native_terminal_dash_to_hash',
 native_input_hash_policy:'exclude_hash'}
{kind:'native_statistics',request_id,counts_request_id,alphabet:na|aa,epsilon:number>=0,
 nucleotide_padding:'ACGT_at_variable_sites',omnibus_continuity:'r_default_2x2_min_delta',
 pair_df_policy:native_source|standard_pair,
 pair_zero_policy:'retain_math_and_native_zero_to_one',selected_pairs:[[id,id]],
 distribution_backend:{name:'scipy_chi2_integer_df_logtail_v1',version:id}}
{kind:'native_effects',request_id,counts_request_id,selected_pairs:[[id,id]],
 zero_margin_policy:'drop_for_raw_effect_only'}
{kind:'biological_group_counts',request_id,population_id,category_id,
 group_population_id,case_policy:preserve|uppercase,
 terminal_gap_policy:'exclude_terminal_dash',original_hash_policy:'exclude_hash'}
{kind:'biological_statistics',request_id,counts_request_id,alphabet:na|aa,epsilon:number>=0,
 nucleotide_padding:'ACGT_at_variable_sites',omnibus_continuity:'r_default_2x2_min_delta',
 pair_df_policy:'standard_pair',selected_pairs:[[id,id]],
 distribution_backend:{name:'scipy_chi2_integer_df_logtail_v1',version:id}}
{kind:'biological_effects',request_id,counts_request_id,selected_pairs:[[id,id]],
 zero_margin_policy:'drop_for_raw_effect_only'}
{kind:'expected_adequacy',request_id,statistics_request_id,
 statistics_kind:native_reproduction|biological}
{kind:'multiplicity',request_id,family:FamilyPlan,p_values:PValuePlan,
 method:none|bonferroni|holm|bh|by,alpha:number-in[0,1],
 dependence_assumption:none_required_between_tests|
   independent_or_positive_regression_dependence_assumed}
```

MSA permits the seven common request tags plus its two `msa_*` tags; MetaCATS permits alignment/ungapped_map/original_coverage/function_composition/taxonomy plus its group/statistic/effect/adequacy/multiplicity tags. Tree and organismal comparison are MSA adjuncts, not an automatic MetaCATS phylogeny. Every population is explicit and every method choice mandatory. Population/table/tree IDs in the commissioning form use slot references compiled once after acquisition, as specified in `BUNDLE_AND_RETURN_001.md`.

```text
TestSelector = {category_id:id,column_0based:index,kind:omnibus|pairwise,
  group_ids:[id]}
FamilyPlan = {family_id:id,analysis_ids:[id],category_ids:[id],
  test_kind:omnibus|pairwise,eligibility:'variable_site_positive_df',
  population_state:complete|known_count_only|declared_upper_bound|unknown,
  total_test_count:index|null,assumption:<TestFamily.assumption>,
  p_value_basis:<TestFamily.p_value_basis>,evidence:[Evidence],
  selection:all_eligible|explicit_tests,tests:[TestSelector]}
PValuePlan =
 {kind:'statistical_results',statistics_request_ids:[id],field:'mathematical_p'} |
 {kind:'native_observations',observation_ids:[id],test_association_ids:[id]}
```

`selection=all_eligible` requires `tests=[]`; complete selected statistical outputs establish the eligible set, including zero eligible tests. `explicit_tests` supplies exact selectors, each resolves once to an eligible test. Native observation plans use only unadjusted p observations with validated native test associations; native pair zero-rule observations keep that identity and do not become mathematical recalculations. Across analyses, requests are scoped `{analysis_id,request_id}` in adapter parameters; provider-local parameters refer only to their analysis. Cross-analysis multiplicity is compiled by an explicit adapter-level family operation after all named per-analysis results, using the same `adjust_p_values`; it is never silently done per file/category.

```python
calculate_msa(sheet: dict, parameters: dict) -> dict
calculate_metacats(sheet: dict, parameters: dict) -> dict
```

Both return `Components = {schema_version:<matching components version>,analysis_id:id,parameters:CalculationParameters,results:[CalculationOutcome],requirements:[Requirement],diagnostics:[Diagnostic]}`. `CalculationOutcome = {request_id:id,kind:<request kind>,status:ok|partial|invalid,value:<exact corresponding function output>|null,requirements:[Requirement],diagnostics:[Diagnostic]}`. `ungapped_map` value is the exact shared function list of `{alignment_id,row_index,column_0based,ungapped_position_0based}`; all other existing output records remain whole and validate with their installed contracts. Failure in one request retains all independent result values; a failed dependency gives null for its consumers with a dependency-specific requirement. Component wrappers do not overwrite native methods or compute annotation credit.
