# A101 (sequence_homology_evidence): investigation finding features

Proposal for the owner to correct line by line. No code was changed and no Python was run.

An investigation finding is a set of fields. Every field has a controlled answer set that code can validate: a
number with a range and unit, an integer count, a boolean, a value of a fixed vocabulary, a record reference, or an
annotation (a function name or ID taken as given, never looked up). One field holds one thing. Credit is never
restated by a finding field.

## 0. What was read, and what was not where the brief said

| # | Fact | Where |
|---|---|---|
| 0.1 | A101 has **no literature grading sheet**. `literature/{forms,storage,inputs,grading}/sequence_homology_evidence/` do not exist; `literature/readers/sequence_homology_evidence/` holds only source discovery and asset readers (`literature_sequence_discovery.py`, `literature_assets.py`); no shared `literature/forms/*.py` names A101. `literature/prompts/sequence_homology_evidence/` holds only the instruction text. | listed folders |
| 0.2 | A101 grades with **native tool graders**, in `grading/similarity_search/sequence_homology_evidence/` (BLAST pairwise, BLAST database, HMMER search, nhmmer, BV-BRC Homology) and `grading/sequence_alignment/sequence_homology_evidence/` (minimap2, Biopython pairwise). These folders are named `sequence_homology_evidence`, so they were read. | 7 grader files |
| 0.3 | The axis sheet is `a101_native_correspondence_015_v1` (`grading/sequence_homology_evidence/scoring.py`, `compile_native_sheet`). Its projector `NativeCorrespondenceScoring` is in `grading/sequence_alignment/native_correspondence.py` (not a `sequence_homology_evidence` folder). I read that one file because every A101 `credit.py` imports it. Nothing else outside the named folders was read. | `scoring.py`, `native_correspondence.py` |
| 0.4 | `route_native_grading` routes **only** `hmmer_search_sheet_v1` and `blast_*` sheets into the axis sheet (and BLAST only for `blastp`). nhmmer, minimap2, Biopython and BV-BRC sheets are retained as tool gradings but never reach A101 credit. | `scoring.route_native_grading`, `native_correspondence.read_details` |
| 0.5 | The literature episodes (`published_evidence_assessment` and its five descendants) use the same native-correspondence credit as the head. They have no reasoning commit, so they create no tool-origin alignment observations; their credit moves only through native records they already hold. Their findings are model-written prose (section 9). | the six `credit.py` / `task.py` |
| 0.6 | `grading/sequence_homology_evidence/progress_information_credit.py` and `practical_execution_credit.py` are operational credits (monitor information, practical requirement keys). They grade no evidence and give no investigation finding. | both files |
| 0.7 | Observation and assessment vocabularies used below are from `records/sequence_homology_evidence/domain.py` (`OBSERVATION_KINDS`, assessment `relation`, `applicability`, `extent_basis`). | `domain.py` lines 217-367 |

## 1. Proposed `evidence_type` vocabulary for A101

| value | meaning | produced from |
|---|---|---|
| `protein_pairwise_alignment` | one protein query against one supplied protein reference | `blast_pairwise_sheet_v1` with program `blastp`; `biopython_pairwise_sheet_v1` with molecule protein |
| `protein_database_homologs` | protein query against a sequence database; a population of hits / sequence groups | `blast_database_sheet_v1/v2/v3`; `bvbrc_homology_sheet_v1` in `database_identification` mode |
| `protein_profile_match` | HMMER profile/domain correspondence (phmmer, hmmsearch, hmmscan, jackhmmer) | `hmmer_search_scores_v1` |
| `nucleotide_profile_match` | nhmmer / nhmmscan nucleotide locus match | `nhmmer_scores_v1` |
| `nucleotide_alignment` | nucleotide or translated alignment (blastn, blastx, tblastn, tblastx pairwise; minimap2 placement; Biopython nucleotide) | `blast_pairwise_sheet_v1` non-blastp, `minimap2_*_scores_v1`, `biopython_pairwise_sheet_v1` nucleotide |
| `native_correspondence_aggregate` | the axis sheet over all routed comparisons of one target | `a101_native_correspondence_015_v1` |
| `published_homology_report` | a published statement about a homolog read by the literature episodes (no sheet; section 9) | literature `report` tool |

Code chooses `evidence_type` from the sheet `schema` plus the sheet's own `program` / `molecule` / `scientific_mode`
field. The model never picks it.

Common fields every A101 finding carries, besides the strength features of its family:

| field | type | values | meaning |
|---|---|---|---|
| `evidence_type` | enum | section 1 | as above |
| `sheet_ref` | record_ref | grading artifact ref (`tool_grading_artifact_v1/v2`) | the sheet stays in the episode that graded it |
| `routed_to_axis_credit` | boolean | | true only for `hmmer_search_sheet_v1` and `blastp` `blast_*` sheets (0.4) |

## 2. Axis sheet: native correspondence (`a101_native_correspondence_015_v1`) and its projector

### 2.1 What it grades
Per target, the per-position maximum of comparison weights `native_strength * reference_paired_fraction *
identity_factor`, averaged over included algorithms, geometric mean over required regions. It is the credit of the
head and the literature episodes (scope-length-weighted mean over targets).

### 2.2 Fields as the code names them

Sheet (`compile_native_sheet`), all always present:

| field | type | range / vocabulary | unit |
|---|---|---|---|
| `value` | number | [0, 1] | dimensionless_index |
| `status` | enum | `derived` | |
| `supplied_length` | integer | > 0 | residues (aa) |
| `profile` | list of enum | `blast`, `hmmer` | |
| `regions[].start`, `regions[].end`, `regions[].length` | integer | 0..supplied_length | residues |
| `regions[].algorithm_components.blast` / `.hmmer` | number | [0, 1] | dimensionless_index |
| `regions[].value` | number | [0, 1] | dimensionless_index |
| `function_specific_index.status` | enum | `not_assessed` | |
| `full_target_index.status` | enum | `not_assessed` | |
| `coefficients.blast` / `.hmmer` | number | 0.025 / 0.020 | 1/bits |

Comparison row (`comparisons[]`; required inputs marked R, `_require` raises without them):

| field | type | range | unit |
|---|---|---|---|
| `algorithm` (R) | enum | `blast`, `hmmer` | |
| `program` | enum | `blastp`; `phmmer`, `hmmsearch`, `hmmscan` | |
| `bits` (R) | number | finite | bits |
| `native_evalue` | number | >= 0 or null | expected chance hits |
| `alignment_identity` (R for blast) | number | [0, 1] | fraction |
| `native_identity` (hmmer) | number | [0, 1] or null | fraction |
| `reference_paired_count` (R) | integer | 0..reference_length | positions |
| `reference_length` (R) | integer | > 0 | positions |
| `native_strength` | number | [0, 1) | dimensionless |
| `reference_paired_fraction` | number | [0, 1] | fraction |
| `identity_factor` | number | [0.5, 1] (1 for hmmer) | dimensionless |
| `weight` | number | [0, 1) | dimensionless |
| `hit_index`, `hsp_index` (blast) | integer | >= 0 | |

Projector (`read_details`): `credit` (number), `axis_components.A101` (= credit),
`a101_sheet.targets[t].comparison_count` (integer), `unsupported_profiles` (list), `detail_pages.source_contributions_total`
(integer).

### 2.3 Proposed finding (`native_correspondence_aggregate`, one per target)

| feature | from | type | range / vocabulary | unit |
|---|---|---|---|---|
| `blast_component` | mean over `regions[].algorithm_components.blast` weighted by `regions[].length`; null when `blast` not in `profile` | number | [0, 1] | dimensionless_index |
| `hmmer_component` | same for `hmmer` | number | [0, 1] | dimensionless_index |
| `algorithm_count` | `len(profile)` | integer | 0..2 | algorithms |
| `algorithms_agree` | both components present and both > 0 (agreement across arms) | boolean | | |
| `comparison_count` | `len(comparisons)` | integer | >= 0 | comparisons |
| `distinct_reference_count` | count of distinct `hit_index` (blast) and `native_record_key` hit part / `target_name` (hmmer) | integer | >= 0 | references |
| `max_bits` | max `comparisons[].bits` | number | finite | bits |
| `min_native_evalue` | min `comparisons[].native_evalue` | number | >= 0 | expected chance hits |
| `max_reference_paired_fraction` | max `comparisons[].reference_paired_fraction` | number | [0, 1] | fraction |
| `max_alignment_identity` | max `comparisons[].alignment_identity` (blast rows) | number | [0, 1] | fraction |
| `region_count` | `len(regions)` | integer | >= 1 | regions |
| `uncovered_region_count` | count `regions[].value == 0` (any such region makes the geometric value 0) | integer | >= 0 | regions |
| `uncertainty.kind` | constant | enum | `native_evalue` | |
| `uncertainty.magnitude` | = `min_native_evalue` | number | >= 0 | expected chance hits |
| `uncertainty.sampling_basis` | constant | enum | `native_search_space` | |
| `function_specific_assessed` | `function_specific_index.status != 'not_assessed'` (always false today) | boolean | | |

Left out: `value` (with one target it equals the credit; credit is never restated); the per-residue intervals,
`target_symbols`, `residue_pairs` (data, not features; they stay in the sheet).

### 2.4 Prose and open strings left out
`interpretation`, `aggregation`, `function_specific_index.reason`, `full_target_index.reason`, projector
`interpretation` and `policy` are code constants; `version` carries them. `target_name` (hmmer) is a native name;
`distinct_reference_count` carries what it was used for.

## 3. Per-annotation contribution (`signed_root_axis_scalar_mappings_v1`, `contribution.py`)

### 3.1 What it grades
For one proposed annotation, the native correspondence of only those received observations whose assessment is
`relation = strengthens` with established transfer; otherwise unavailable with the missing reasons.

### 3.2 Fields as the code names them

| field | type | range / vocabulary |
|---|---|---|
| `value` | number or null | [0, 1] |
| `status` | enum | `available`, `unavailable` |
| `direction` | enum | `support`, `opposition`, `measured_neutral`, `unknown` |
| `missing_inputs` | list of enum | `no_received_native_measurement`, `no_received_applicable_supporting_assessment`, `assessed_observation_has_no_received_applicable_supporting_measurement`, `unresolved_native_attribution` |
| `source_contribution_count` | integer | >= 0 |
| `assessment_refs` | record_refs | |
| `proposed_annotation_ref`, `subject_ref` | record_ref | |
| `source_refs` | record_refs | |
| `scope`, `transfer`, `assessment_qualifications`, `native_inputs` | record (structures) | |

Assessment vocabularies behind it (`domain.py`): `relation` {`strengthens`, `weakens`, `mixed`,
`does_not_discriminate`}; `applicability` {`direct`, `transfer`, `contextual`, `scope_limited`, `incomparable`};
`extent_basis` {`observed_extent`, `inferred_extent`, `context_allocation`}.

### 3.3 Proposed finding (per proposed annotation; `evidence_type` = that of the strongest routed observation)

| feature | from | type | range / vocabulary |
|---|---|---|---|
| `proposed_annotation_ref` | field | record_ref | |
| `annotation_support` | `value` | number or null | [0, 1], dimensionless_index |
| `direction` | field | enum | as above |
| `missing_<code>` | one boolean per `missing_inputs` code | boolean | 4 fields |
| `supporting_assessment_count` | `len(assessment_refs)` | integer | >= 0 |
| `source_contribution_count` | field | integer | >= 0 |
| `distinct_source_count` | `len(source_refs)` | integer | >= 0 |
| `assessment_count_by_relation.<relation>` | count of linked assessments per `relation` value | integer, 4 fields | >= 0 |
| `assessment_count_by_applicability.<applicability>` | count per `applicability` value | integer, 5 fields | >= 0 |

Left out: `formula`, `interpretation` (constants); `assessment_qualifications` and `transfer` (structures built from
assessment records; the counts above carry them).

## 4. BLAST pairwise sheet (`blast_pairwise_sheet_v1`)

### 4.1 What it grades
Per-HSP and union residue correspondence of one query against one reference; native scores per HSP, never summed.

### 4.2 Fields (all keys always present; values nullable when unavailable)

Sheet: `status` enum {`complete`, `partial`, `no_reported_alignment`, `alignment_report_unavailable`}; `issues` (list).
Per HSP `components`: `native_scores.bit_score` (bits), `.score` (raw), `.evalue` (>= 0, expected chance hits);
`counts.alignment_columns`, `.paired_columns`, `.identical_pairs`, `.query_gap_columns`, `.reference_gap_columns`
(integers, columns); `fractions.query_paired_coverage`, `.reference_paired_coverage`, `.query_span_coverage`,
`.reference_span_coverage`, `.paired_identity`, `.alignment_identity` ([0, 1]); `traceback_available`,
`geometry_available` (boolean); `reported_counts.align_len|identity|positive|gaps` (integers);
`reported_percentages.*` ([0, 100]).
Union: `counts.distinct_residue_pairs`, `.paired_query_positions`, `.paired_reference_positions`,
`.identical_residue_pairs`, `.hsps_with_geometry`, `.hsps_without_geometry` (integers); `fractions.query_paired_coverage`,
`.reference_paired_coverage`, `.paired_identity` ([0, 1]); `complete_for_reported_hsps` (boolean); `conflicts` (list).

### 4.3 Proposed finding (`protein_pairwise_alignment` or `nucleotide_alignment`)

| feature | from | type | range / vocabulary | unit |
|---|---|---|---|---|
| `program` | `input.search.program` | enum | `blastn`, `blastp`, `blastx`, `tblastn`, `tblastx` | |
| `sheet_status` | `status` | enum | 4 values above | |
| `hsp_count` | `len(hsps)` | integer | >= 0 | HSPs |
| `max_bit_score` | max HSP `native_scores.bit_score` | number | finite | bits |
| `min_evalue` | min HSP `native_scores.evalue` | number | >= 0 | expected chance hits |
| `union_paired_identity` | `union.fractions.paired_identity` | number | [0, 1] | fraction |
| `union_query_paired_coverage` | `union.fractions.query_paired_coverage` | number | [0, 1] | fraction |
| `union_reference_paired_coverage` | `union.fractions.reference_paired_coverage` | number | [0, 1] | fraction |
| `hsps_without_geometry` | `union.counts.hsps_without_geometry` | integer | >= 0 | HSPs |
| `correspondence_conflict_count` | `len(union.conflicts)` | integer | >= 0 | conflicts |
| `union_complete` | `union.complete_for_reported_hsps` | boolean | | |
| `uncertainty.kind` / `.magnitude` / `.sampling_basis` | `native_evalue` / `min_evalue` / `native_search_space` | enum / number / enum | | |

Left out: `calculations` and `union.meaning` (code constants), `reference.descriptions` and `unpaired_metadata`
(native titles: prose); `input` (native result, stays in sheet).

## 5. BLAST database sheet (`blast_database_sheet_v1/v2/v3`) and probabilities (`blast_database_probabilities_v1`)

### 5.1 What it grades
A database search as a population: hits collapsed into sequence groups by demonstrated identity, per-function group
counts and score summaries, taxonomy agreement with the target, search-limit censoring, and a conditional
reference-kernel weight per explicit function (not a calibrated probability).

### 5.2 Fields as the code names them
Per hit `measurements`: `maximum_bit_score`, `minimum_evalue`, `hsp_count`, `traceback_complete` (bool),
`observed_paired_query_positions`, `observed_paired_reference_positions`, `query_paired_coverage`,
`reference_paired_coverage`, `unique_pair_count`, `identical_unique_pair_count`, `overlap_pair_representations`.
`sequence_groups[]`: `group_index`, `hit_indices`, `functions` (annotation names), `maximum_bit_score`, `taxids`.
`functions[]`: `function` (annotation), `sequence_group_count`, `native_hit_count`, `bit_score`,
`query_paired_coverage`, `reference_paired_coverage` (each `{count, minimum, maximum, mean}`), `taxonomy.ranks[]`
(`rank`, `unambiguous_group_count`, `ambiguous_group_count`, `unknown_group_count`, `same_taxon_pair_count`,
`comparable_pair_count`, `same_taxon_pair_fraction`, `target_matching_groups`, `target_conflicting_groups`,
`target_ambiguous_groups`, `target_matching_fraction`).
`dependence`: `group_count`, `duplicate_native_hit_count`, `unknown_cross_hit_sequence_identity` (bool).
`coverage`: `native_hit_count`, `sequence_group_count`, `groups_with_explicit_function`,
`groups_without_explicit_function`, `groups_with_native_bit_score`, `metadata_row_count`, `matched_metadata_row_count`.
`search_limits`: `requested_hit_limit`, `reported_hit_count`, `limit_reached` (bool or null), `hit_array_present`
(bool), `whole_database_result_complete` (always null).
Probabilities: `parameters.temperature_bits` (> 0, bits), `unadjusted_probabilities{function: [0,1]}`,
`representation_adjusted_probabilities` (same or null), `unannotated_reference_kernel_fraction` ([0, 1]),
`unscored_sequence_group_count`, `largest_group_bit_score`, `largest_scored_function_group_bit_score`,
`calibrated_annotation_probability` (always false).

### 5.3 Proposed finding (`protein_database_homologs`, one per proposed annotation = one `functions[]` row)

| feature | from | type | range / vocabulary | unit |
|---|---|---|---|---|
| `function` | `functions[].function` | annotation | function name/ID as given by the source reader | |
| `supporting_group_count` | `functions[].sequence_group_count` (independent units) | integer | >= 0 | sequence groups |
| `total_group_count` | `coverage.sequence_group_count` | integer | >= 0 | sequence groups |
| `groups_without_function` | `coverage.groups_without_explicit_function` | integer | >= 0 | sequence groups |
| `max_bit_score` | `functions[].bit_score.maximum` | number | finite | bits |
| `max_query_paired_coverage` | `functions[].query_paired_coverage.maximum` | number | [0, 1] | fraction |
| `conditional_weight` | `unadjusted_probabilities[function]` | number | [0, 1] | model weight, not probability |
| `representation_adjusted_weight` | `representation_adjusted_probabilities[function]` or null | number | [0, 1] | model weight |
| `unannotated_fraction` | `unannotated_reference_kernel_fraction` | number | [0, 1] | fraction |
| `competing_function_count` | `len(unadjusted_probabilities) - 1` | integer | >= 0 | functions |
| `target_taxon_matching_fraction` | `taxonomy.ranks[rank=R].target_matching_fraction`, R fixed by setting (e.g. `genus`) | number | [0, 1] | fraction |
| `duplicate_hit_count` | `dependence.duplicate_native_hit_count` | integer | >= 0 | hits |
| `sequence_identity_unresolved` | `dependence.unknown_cross_hit_sequence_identity` | boolean | | |
| `search_limit_reached` | `search_limits.limit_reached` | boolean or null | | |
| `uncertainty.kind` / `.magnitude` / `.sampling_basis` | `native_evalue` / min `measurements.minimum_evalue` of the function's hits / `native_search_space` | | | |

Left out: `assumptions`, `formula`, `conditioning`, `retained_measurements_not_used_by_this_model`, every `meaning`
(code constants); `function_assignments[].evidence`, `associations[].origin`, source-quality `quality_method`,
`reference_metadata` titles (source prose or open metadata; `supporting_group_count` and the taxonomy fraction carry
what they were used for).

## 6. HMMER search scores (`hmmer_search_scores_v1`)

### 6.1 What it grades
Per domain: native scores, spans, coverages, paired/insert/delete counts, identity fractions, posterior bounds and
cutoff margins; per hit: interval unions and retained domain count; per query: hit-row counts.

### 6.2 Fields (per domain; `SCALARS`, all always present and nullable)
`model_length` (positions), `sequence_length` (residues), `model_span_positions`, `sequence_span_residues`,
`sequence_envelope_residues`, `model_span_coverage`, `sequence_span_coverage`, `sequence_envelope_coverage`,
`paired_positions`, `insert_positions`, `delete_positions`, `alignment_columns`, `paired_model_coverage`,
`paired_sequence_coverage`, `sequence_identity_fraction`, `consensus_identity_fraction`, `alignment_identity_fraction`,
`api_identity_fraction`, `native_domain_score_bits`, `native_domain_bias_bits`, `native_conditional_evalue`,
`native_independent_evalue`, `native_accuracy`, `posterior_lower_mean`, `posterior_upper_mean`; `cutoff_margins.values[]`
(`cutoff` enum {GA, TC, NC}, `scope` enum {sequence, domain}, `margin_bits`); `availability` enum {`available`,
`partial`}. Per hit: `retained_domain_count`, `interval_unions.{model,sequence,envelope}.positions`. Per query:
`acquired_hit_row_count`, `acquired_reported_hit_row_count`, `acquired_included_hit_row_count`. Per iteration:
`dependent_round` (bool).

### 6.3 Proposed finding (`protein_profile_match`, per hit)

| feature | from | type | range | unit |
|---|---|---|---|---|
| `program` | `operation.program` | enum | `phmmer`, `hmmsearch`, `hmmscan`, `jackhmmer` | |
| `domain_count` | `retained_domain_count` | integer | >= 0 | domains |
| `max_domain_score_bits` | max `native_domain_score_bits` | number | finite | bits |
| `min_independent_evalue` | min `native_independent_evalue` | number | >= 0 | expected chance hits |
| `max_domain_bias_bits` | max `native_domain_bias_bits` | number | >= 0 | bits |
| `model_coverage` | `interval_unions.model.positions / model_length` | number | [0, 1] | fraction |
| `sequence_coverage` | `interval_unions.sequence.positions / sequence_length` | number | [0, 1] | fraction |
| `max_sequence_identity` | max `sequence_identity_fraction` | number | [0, 1] or null | fraction |
| `posterior_lower_mean` | min over domains | number | [0, 1] | posterior bound |
| `gathering_cutoff_passed` | `cutoff_margins` row `GA`/`sequence` `margin_bits >= 0`; null when unavailable | boolean or null | | |
| `gathering_margin_bits` | that `margin_bits` | number | finite | bits |
| `included` | `is_included` | boolean | | |
| `dependent_round` | iteration `dependent_round` | boolean | | |
| `uncertainty.kind` / `.magnitude` / `.sampling_basis` | `native_evalue` / `min_independent_evalue` / `native_search_space` | | | |

Left out: `definitions` (code constants), `target_name`, `query_name`, `identifiers`, `associations` (native
names; the model accession could be an annotation field if the owner wants the family ID passed:
`model_accession` from `cutoff_margins.model_accession`).

## 7. Sheets that never reach A101 credit (0.4)

These are graded and retained but `route_native_grading` rejects them. Proposed findings only if the owner routes
them; strength features listed briefly.

| sheet | evidence_type | proposed strength features (sheet field names) |
|---|---|---|
| `nhmmer_scores_v1` (per locus) | `nucleotide_profile_match` | `native_score_bits` (bits), `native_evalue` (>=0, expected hits), `native_bias_bits`, `model_span_coverage`, `sequence_span_coverage` ([0,1]), `paired_positions` (int), `posterior_lower_mean` ([0,1]), `cutoff_margins[].margin_bits`, `strand` (enum `+`/`-`), count of loci per query |
| `minimap2_query_scores_v1` | `nucleotide_alignment` | `reported_placement_count`, `distinct_reference_count`, `exact_duplicate_row_count`, `alternative_correspondence_positions`, `invalid_sheet_count`, `missing_sheet_count` (ints); `query_paired_union_coverage` ([0,1]); `output_complete` (bool); `result_meaning` (enum of its 3 values); per placement `mapping_quality` (0-254), `native_alignment_identity` ([0,1]) |
| `biopython_pairwise_scores_v1` | `protein_pairwise_alignment` / `nucleotide_alignment` | `paired_identity`, `alignment_identity`, `query_paired_coverage`, `reference_paired_coverage` ([0,1]); `paired_positions`, `identical_positions`, `substituted_positions`, gap columns (ints); `native_score` (number, program units); `status` |
| `bvbrc_homology_scores_v1` | by `scientific_mode`: `protein_database_homologs` (database_identification) or pairwise | reuses sections 4.3 / 5.3 on `pairwise_correspondence` or `conditional_function_weights`; plus `alignment_supplements` `query_gap_runs`, `reference_gap_runs`, `substitution_columns` (ints) |

Prose left out: `result_meaning` free strings are already a closed set of three; `definitions`, `unused_metadata`,
`meaning` are constants; `diagnostics` stay in the sheet.

## 8. Operational credits (no finding)

`ProgressInformationCredit` (`received_progress_information_v1`) and `project_practical_credit`
(`practical_requirement_credit_v1`) measure monitoring information and requirement keys. They are the credit of the
monitor and execution episodes. They give no evidence_type. Their counts (`newly_informative_received_snapshot_count`,
`satisfied_keys`) are credit inputs and are not restated in returns.

## 9. Literature episodes: no sheet

`published_evidence_assessment` and its descendants return a model-written report (`interpretation`,
`qualification`, `source_claim`, `source_subject`, `relevance`, `statement`, `approach`, `outcome`, `location`:
all `text`, all prose). No A101 code grades a published source. Proposed replacement for
`published_homology_report`, all fields set by the `report` tool's schema (fixed vocabularies chosen by the model,
validated by the form) and counts computed by code over the report entries:

| feature | type | values | meaning |
|---|---|---|---|
| `source_ref` (per entry) | record_ref | | replaces the `text` source_ref |
| `claim_kind` (per entry) | enum | `reported_sequence_identity`, `reported_domain_assignment`, `reported_family_assignment`, `reported_homolog_function`, `reported_non_transferability`, `no_applicable_claim` | replaces `source_claim` (prompt already separates domain vs family and identity vs annotation) |
| `subject_relation` (per entry) | enum | `target_itself`, `aligned_homolog`, `family_member`, `unresolved` | replaces `source_subject` and the correspondence part of `qualification` |
| `measured` (per entry) | boolean | | the source reports a measurement (vs. a prediction/annotation) |
| `function` (per entry, optional) | annotation | function name/ID as written in the source | the annotation the claim concerns |
| `offset`, `limit` (passage/window) | integer | >= 0, bytes | already controlled |
| `entry_count` | integer | >= 0 | entries in the report |
| `unresolved_correspondence_count` | integer | >= 0 | entries with `subject_relation = unresolved` |
| `claim_count_by_kind.<kind>` | integer | >= 0 | one count per `claim_kind` |

This is a proposal without a grader: the owner must say whether A101 literature gets a sheet, or keeps only these
counts and refs.

## 10. What each parent decides next, and the smallest return it needs

Credit and finding are always returned; "finding" below is the smallest controlled set.

| child -> parent | parent's next decision (its `task.py` decide/action, `msg_to_child`) | smallest finding |
|---|---|---|
| head `sequence_homology_evidence` -> root | root `decide`: which axis to commission next, with which thought pattern and tools; whether to return to A101 for an outstanding job (`job_handoff_refs`) | `evidence_type`; from 2.3: `algorithm_count`, `algorithms_agree`, `distinct_reference_count`, `max_reference_paired_fraction`, `min_native_evalue`; from 3.3: `direction`, `missing_<code>` booleans; `outstanding_handoff_count` (integer); selectable `execution_handoff_refs`, `committed_record_refs` (record_refs). Drop `held_record_refs`, `evidence_refs`, `children[]`, `qualification` (constant text) |
| recursive head -> head | head: commit a reasoning interpretation, select a tool, or commission another child | same as above plus `committed_record_refs` |
| `published_evidence_assessment` -> head | head: commit assessments on the returned sources (reason), run alignments for named homologs, or recommission literature | section 9 counts plus the chosen `source_ref`s (record_refs) of entries with `claim_kind != no_applicable_claim` |
| `evidence_search_strategy_improvement` -> `published_evidence_assessment` | read candidate sources, recommission the strategy, or write the report | `candidate_source_refs` (record_refs), `approach_count` (integer), `candidate_count` (integer); approach as enum of the search tool names in the task catalog instead of `approach` text; drop `outcome`, `relevance` text |
| `source_relevance_assessment` -> strategy (exemplar) | how many more times to launch it; which sources to keep | `merits_examination_refs` (record_refs), `assessed_source_count` (integer) |
| `source_evidence_examination` -> `source_relevance_assessment` | examine another source or report | `reading_count`, `unresolved_correspondence_count`, `claim_count_by_kind.*` (integers); `source_ref` (record_ref) |
| `passage_evidence_extraction` / `table_evidence_extraction` / `source_coverage_improvement` -> `source_evidence_examination` | another reading child, a direct read, or report | per entry `offset`, `limit` (integers) or table address as integers (`row_start`, `row_end`, `column_start`, `column_end`), `claim_kind`, `subject_relation`; counts as section 9; drop `location`, `representation`, `statement` text (`representation` -> enum of the reader's representation names) |
| `execution_job_submission` -> head | monitor, acquire results, relaunch, or other work | `execution_handoff_refs`, `execution_result_refs` (record_refs); `execution_completed` (bool); `new_handoff_count` (int). Drop `qualification`; `handoff_resources` -> record_refs or resource-id enum |
| api/hpc/local job execution -> `execution_job_submission` | another launch on another resource | `completed` / `practical_completed` (bool), `handoff_established` (bool), `commands_run`, `commands_failed` (ints), `resource_id` (enum of configured resources). Drop `interpretation`, `last_status`, `qualification` text (`last_status` -> enum of service statuses) |
| `execution_progress_assessment` -> head | wait/commission results acquisition/relaunch | `observed`, `result_available` (bool), `execution_state` (enum of `lifecycle_state`/native `state` values in `progress_information_credit.py`); `monitoring_progress_refs`. Drop `qualification` |
| `execution_result_acquisition` -> head | grade/commit the acquired results, or acquire more | `execution_completed` (bool), `acquisitions`, `invalid_acquisitions`, `windows_acquired` (ints), `target_family` (enum); `execution_result_refs`; `handoff_ref` as record_ref; `failures` -> `failure_count` (int) + failure-code enum list |
| `resource_work_submission` -> head; api/hpc/local resource work -> it | acquire results or try another resource | `usable_handoffs`, `unavailable_checks` (ints); `availability` (enum `available`, `unavailable`, `authentication_required`, `unknown`); `execution_handoff_refs`. Drop `qualification`; `adapter_facts`, `execution_handoff(s)` are open records: keep only as record_refs |
| `resource_result_acquisition` -> head | grade results or recheck | `handoff_state` (enum `usable`, `unavailable`, ...), `handoff_count` (int), `failure_codes` (enum list); drop `interpretation` record |

## 11. Points for the owner

1. Route nhmmer, minimap2, Biopython and BV-BRC sheets into the A101 axis sheet, or keep them out of findings (0.4, section 7).
2. A101 literature has no grader: accept the section 9 vocabulary, or give A101 literature a sheet.
3. Which taxonomy rank fixes `target_taxon_matching_fraction` (5.3).
4. Whether an HMMER `model_accession` (Pfam/TIGRFAM ID) is passed as an annotation field (6.3).
5. `distinct_reference_count` counts native hits, not demonstrated-independent sequences; only the database sheet's `sequence_groups` collapse identical sequences (`supporting_group_count`).
