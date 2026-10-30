# Exact populating inputs and outputs — all unimplemented

These functions are specifications targeted to CURRENT_PROPOSED_SHEET.md,
including its additive orientation clarification. They are not available tools
or code. The arithmetic fixture does not implement source parsing, biological
function grounding, predicate validation or native alignment interpretation.
No investigation prompt is supplied or changed.

## Common output types

Cell = {value: finite number|null, unit: allowed unit string,
origin: reported|derived|synthetic, status: one sheet status,
printed_token: string|null, lower: number|null, upper: number|null,
lower_inclusive: boolean|null, upper_inclusive: boolean|null,
bound_kind: rounding|censoring|missing_operand|joint_sensitivity|null,
source_field: source-reference|null}.

Source-reference identifies retained bytes and source location outside the
scoring prompt. Native settings and identities support validity and repeated
representation handling; they do not themselves become numerical grades.

An interval endpoint may use a typed unbounded marker for an intermediate raw
native input. Compiled fractions/index bounds are always finite in [0,1].
Point and bounds must be coherent. Input validation returns exact field paths
and failure codes, preserves other valid rows and does not cause new execution.

## R1 — supplied_material_cells

Input:

- material_bytes or a scoped retained-record reference; explicit selected
  record/region if there are multiple records.
- alphabet: protein|DNA|RNA; complete_status: complete|fragment|unknown;
  optional independently established biological_full_length and coordinate map.
- For translated comparisons: exact peptide bytes, frame, translation table,
  source nucleotide positions and unresolved codon markers.

Output:

- supplied_length: Cell in aa or nt; selected_positions: unique integer set;
  full_length: Cell; material_complete_status; original-coordinate map.
- Peptide-to-nucleotide map, if supplied and validated.
- Failure codes: selection_ambiguous, alphabet_mismatch, invalid_coordinate,
  length_conflict, translation_map_absent. No public gene-name lookup is required.

## R2 — protein_blast_hsp_cells

Input:

- Original native output plus exact schema/program/version; supplied and
  reference sequences or known lengths with selected-range maps.
- Per HSP: score, bitscore, evalue, length, nident, positive, gaps, gapopen,
  qstart/qend, sstart/send; qseq/sseq or BTOP/another exact traceback when present.
- Scoring/statistical settings, lambda, K and effective search space when
  reported, database counts/length/release, filters and reporting limits,
  run/output completion, source comparison identities.

Output per HSP:

- S_raw_points, B_bits, E_expected_null_hits as Cells.
- n_identical, alignment_columns, paired_columns, positive_columns,
  query_gap_columns, reference_gap_columns, opening_count as Cells.
- query_span_positions, reference_span_positions, paired_target_positions,
  paired_reference_positions and exact paired-coordinate/residue rows.
- identity_all_columns, identity_pairs, positive_fraction, target/reference
  span and paired fractions as Cells.
- score_scope=blast_hsp; biological/native role mapping; native settings,
  search-space value/unit/method and actual-versus-override flag.
- guaranteed/possible position sets and exact missing reasons where output
  lacks traceback. Endpoints alone populate span, not paired sets.
- Reconstructed B/E only when exact identified native statistics permit it;
  store derived reconstruction separately from original reported fields.

Validate integer-count relationships, coordinates, sequence symbols, units and
reported precision. Do not infer a raw score from identity or substitute a
network cutoff. Repeated representations point to one underlying comparison.
Failure codes include schema_unknown, traceback_absent, score_scope_conflict,
statistics_unidentified, printed_zero_no_bound, inconsistent_counts.

## R3 — protein_hmmer_cells

Input:

- Original table/header, program/version, optional native alignment with model
  and sequence symbols and PP data; actual model length and model metadata,
  sequence lengths, native Z/domZ overrides, tau/lambda_H if known, GA1/GA2
  if actually present, filters/reporting completion.
- Supplied-target orientation:
  native_sequence|query_profile_representing_supplied_sequence.
- For the latter: actual model-state-to-original-query correspondence.
  For a reference profile: function-grounded seed/reference relationships and
  reference-to-model map where a named experimental site is transferred.
- For each sequence/profile comparison: sequence-level identity, separate
  domain identities, represented output identities and model dependencies.

Output:

- Sequence rows: sequence_bits, sequence_E, sequence_bias_bits, domain_count;
  repeated sequence fields are reconciled once.
- Domain rows: domain_bits, domain_bias_bits, iE, cE; native hmm_from/to,
  ali_from/to, env_from/to; native_acc with its original precision.
- Biological target/reference maps: paired_target_positions,
  paired_reference_positions, reference_denominator and denominator_kind
  (reference_sequence_residues|reference_profile_match_states).
- Separate model-span, model-emission, sequence-alignment-span and
  sequence-envelope fractions, all with actual denominators.
- Native whole/domain scope, native target/query roles, supplied-target role;
  exact source/output relationships; optional matching GA margins.
- Any returned web identity retains that provider's own denominator and does
  not populate BLAST identity_all_columns without an actual count/map.

The domain calculation uses domain rows; whole_sequence mode uses the one
compatible full row and excludes its domain rows from the same comparison
population. Neither output is regenerated from the other. No native acc
conversion to function probability or expected identical-residue count exists.
Failure codes additionally include profile_query_map_absent,
reference_profile_function_unresolved, whole_domain_double_use,
role_denominator_mismatch. The parser never builds or searches a model.

## R4 — literature_sequence_cells

Input: inspected source locations, typed measured/reported statement kind,
actual compared subject/region, printed numeric token, units/denominator,
reported uncertainty type, and supplied alignment/sequence content if available.
The extraction identifies what was reported; it does not assign credibility
numbers. A source-grounded human/model reading can identify a statement, but
counting and calculation remain deterministic once its operands are available.

Permitted statement kinds:
native_score; exact_alignment_count; rounded_identity; across_pairs_range;
named_site_comparison; motif_occurrence; search_threshold; supplied_sequence.

Output:

- Exactly the corresponding R1/R2/R3/site cells, plus origin=reported/derived
  and extraction status.
- Rounded percent converted only to the same fractional quantity. A
  group-range is not turned into a per-pair point or confidence interval.
- Search threshold remains a settings field and cannot populate hit E.
- Identity-only observations preserve unsupported_score_profile or
  not_reported for native B. The native-index point stays null.

Exact retained examples: TriA counts populate 466/475; QueF-like source ranges
and separate panels retain their own denominators; CodA network cutoff remains
a parameter. These packets do not implement R4 or provide native output data.

## R5 — function_and_dependency_population

Input:

- Actual characterization subject and endpoint/scope, condition/construct
  identifiers, source-experiment references; distinctions needed for
  experimental comparability and attribution are retained.
- Reference/profile/query identities and mappings; source-backed membership
  in a function-defined reference group.
- Functional relationships in a declared function vocabulary:
  compatible|nested|incompatible_at_scope|unresolved.
- Evidence-identity relationships:
  same_native_result|same_sequence_pair|shared_profile_seed|shared_family|
  shared_characterization_experiment|distinct_characterizations|unknown.

Output:

- Function label membership: established_label_set and possible_label_set;
  scope, actual grounded source endpoints, and unresolved reasons.
- comparison membership in F or its recorded incompatible set G_F;
  duplicate representations and shared-dependency links.
- Distinct_native_comparison_count, distinct_reference_sequence_count,
  distinct_profile_count and distinct_characterization_experiment_count,
  each with unresolved identity status.

This is a typed source interpretation, not an overall score or new assay
reliability formula. It cannot decide numerical credit by publication/lab
reputation, turn an uncharacterized name into an activity, or infer independent
experiments from different reports. Conflicting labels stay possible
assignments and induce bounds. No extra model call composes factual records.

## R6 — feature_panel_cells

Input:

- Function/scope and panel definition with positive N; unique feature IDs,
  actual source locations, source and record coordinate systems.
- Each site: reference position/residue, explicit allowed target symbols
  and their meaning (exact_identity|source_supported_compatibility),
  target correspondence/gap or ambiguous/unmapped status.
- Each pattern predicate: exact pattern, allowed alphabet for each position,
  target search region, completeness and matching count if already computed.
- Necessity status:
  merely_relevant|necessary_supported_by_identified_experiment|unresolved.
- Predicates sharing the same measured question and scored ownership map.

Output:

- N,m,k,u=N-m; assessed, conditional compatibility, s_lower/s_upper and
  s_point only when all assessed.
- Motif occurrence count and presence Cell, with full-scope absence separated
  from unobserved sequence. No arbitrary hydrophobic alphabet.
- Relevant-panel and necessary-predicate lists with duplicate ownership;
  A_F and V_F with their bounds/statuses under the stated sheet convention.
- Mapping discrepancies and evidence links. A reported H/Q mismatch supplies
  exact identity, not a biochemical allowed-substitution rule.

Necessary status cannot be inferred from evolutionary conservation alone.
Indispensability is a constrained source claim, not a subjective 0/1 grade.

## R7 — compile_proposed_a101_cells

Input:

- R1 target scope and source-defined required regions, merged by overlap;
  calculation_profile: blast_only|hmmer_only|blast_hmmer.
- HMMER scope profile: domain|whole_sequence, and biological orientation.
- output_form: homology_only|feature_qualified, fixed in the calculation record.
- R2/R3 eligible native rows, R5 memberships/dependence, R6 panels/predicates.
- Exact convention015 coefficients: 0.025/bit, 0.020/bit, 0.5 identity mixture;
  tool weights from named profile; equal panel/required-region weights;
  no fitted calibration artifact is implied.
- Weight intervals and guaranteed/possible paired position sets; retained
  shared-operand constraints and optional joint sensitivity scenarios.

Output:

- Per comparison f_t(B), r, optional i, w and bounds.
- Per algorithm/function/position M and O and their bound maps.
- Per region L_d, H_d, X_d, C_d and conservative bounds.
- H_F, C_native,F, A_F, V_F, homology_only_index,
  feature_qualified_index; selected_output_form/value/bounds/status.
- competitor_scope=recorded_competitors_only; alternative_coverage:
  unassessed|partial|declared_set_assessed; open-alternative sensitivity range.
- calculation_provenance and explicit missing_fields, unsupported_profiles,
  scope-conflicts, dependence/multiplicity/calibration limitations.

All formulas are in CURRENT_PROPOSED_SHEET.md. No source reads, native jobs,
resource choices, continuation, prompt construction or annotation-credit
updates are side effects. An invalid/missing row returns its specific failure
while preserving computable components. The responsible investigation decides
whether further information is useful; reader validation is not an execution
gate or an instruction to run another tool.

## Additive IO clarification 002 — membership and availability

Common Cell origin additionally permits proposed for the explicit policy
coefficients; it never labels a missing native measurement as a proposal.

R5 additionally outputs, for every F/row pair, four booleans:
guaranteed_F, possible_F, guaranteed_incompatible_F and
possible_incompatible_F. Guaranteed implies possible. A same-scope unresolved
F-or-G label has possible_F=true and possible_incompatible_F=true, with both
guaranteed flags false. The source relationship record also identifies any
mutually exclusive assignments; those are retained for optional sensitivity
enumeration. Unknown labels cannot enter a lower envelope.

R2/R3 additionally retain declared analysis scope and availability:
complete_report_available|partial_report_available|included_report_unavailable.
Report completeness concerns available native output, not exhaustive biological
search or absence of heuristic filters. R7 consumes explicit unavailable-scope
sets and their known function restrictions; it emits U_t,F and U_t,G under
section 10. No unavailable-scope marker supplies an observed row, a comparison
count, or a negative result. All actual reported rows remain preserved.

R7 computes lower/upper maxima using both membership and positional eligibility,
then the availability envelopes, then the already specified region/feature
formulas. Its selected point is null when included native information remains
unavailable. It may additionally return observed_subset_value with a visibly
different scope/status; this never fills the selected point. A complete report
with no observed compatible row gives recorded-set zero and retains its
reporting limitations. An analysis never included in the calculation is not
turned into an unavailable included channel.

Additional validation failures are contradictory_guaranteed_membership,
guaranteed_without_possible_membership, unavailable_scope_outside_material and
unknown_required_scope. Return the invalid fields and preserve other usable
components. The role of these checks is numerical provenance, not execution
selection. Every function in this file remains unimplemented.
