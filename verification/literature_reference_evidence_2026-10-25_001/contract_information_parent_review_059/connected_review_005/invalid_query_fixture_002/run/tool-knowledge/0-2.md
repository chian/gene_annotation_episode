# Numerical results from native database BLAST

This section describes results from the selected psiblast, deltablast, rpsblast,
rpstblastn, blastn_vdb or tblastn_vdb operation. Use its original HPC attempt and
parent-defined return form. `execution.results.status` observes that attempt;
`execution.results.collect` captures its declared artifacts and prepares the
requested numerical return. Neither operation starts a new search. The operation
and monitoring section describes the actual software/resource requirements.

## Choose the measurements needed for the assigned investigation

The result selector is `native_blast_database_result_selector_v1` with
`acquisition: complete_bound_bundle`. Each projection selects one result family,
rows by offset/limit or previously received record keys, and explicit `metrics`
and `booleans`. A family occurs once in a selector. At least one measurement or
boolean is selected per projection. Complete source files and calculations are
retained separately; a short return does not discard the remaining alignments.

| Needed information | Result families and example fields |
| --- | --- |
| Reported and successfully parsed search populations | `search`: `reported_hit_count`, `reported_hsp_count`, `observed_hsp_count`, `parsed_hit_count`, `parsed_hsp_count` |
| One original alignment and its native scores | `hsp`: `native_score_bits`, `native_raw_score`, `native_evalue`, `paired_columns`, `identical_pairs`, `paired_identity`, `alignment_identity` |
| Sequence correspondence over all reported HSPs for a hit | `sequence_hit`: `observed_paired_query_positions`, `overlap_pair_representations`, `query_paired_coverage`, `reference_paired_coverage`, `selected_query_coverage` |
| Explicit function assignments and selected-model weights | `sequence_function`: `function_mass`, `function_prior`, `unadjusted_probability`, `representation_adjusted_probability` |
| Actual database representation | `sequence_population`: `database_sequence_count`, `database_total_sequence_count`, `database_fraction` |
| Taxonomic agreement within results and with an independently supplied query taxon | `sequence_taxonomy` or `vdb_taxonomy`: `same_taxon_pair_fraction`, `target_matching_groups`, `target_conflicting_groups` |
| A profile match with its model's thresholds | `profile_model`: `paired_model_positions`, `model_coverage`; `profile_hsp_model`: `specific_bits_threshold`, `specific_bits_margin`, `reporting_bits_margin` |
| Retained native PSSM values | `pssm_matrix`, `pssm_cell`, `pssm_position`: native dimensions, scores, frequencies and per-position diagnostics |
| VDB subject, sample and feature relationships | `vdb_subject`, `vdb_membership`, `vdb_sample`, `vdb_feature`: the actual reported subject geometry and source-qualified member/sample/feature measurements |

Only families applicable to the selected program are accepted. A profile's
displayed representative is not an experimentally annotated biological reference.
For translated RPS, query coverage uses nucleotide positions while model coverage
uses model positions. Retain original units and the numerator/denominator supplied
with each fraction. Paired identity and alignment identity have different
denominators; full-query coverage and selected-query coverage are also distinct.

## Supply the actual metadata relationships

`metadata_inputs` identifies exact retained inputs by `input_key`, `consumer`,
`schema_id` and artifact identity. Consumers are `query_identity`,
`sequence_database`, `profile`, `iteration` or `vdb`. `retained_sources` supplies
the actual saved source documents referenced by that metadata. The same input
can serve multiple explicitly declared consumer/schema combinations; duplicate
combinations and conflicting identities are rejected. An unsupported schema is
retained and reported as unsupported, not interpreted by guessing its fields.

Function names, query taxon, sequence-equivalence groups, model release and
thresholds, database census, VDB sample membership and CDS translation need their
respective source-qualified metadata. Returned hit frequency is not a database
population census. Matching labels alone do not establish sequence equivalence
or an effective MSA/PSSM master. Missing relationships remain unavailable while
independent native measurements are preserved.

Sequence-function probabilities require the explicitly selected numerical model
and explicit assignments. Representation-adjusted values additionally require
actual matching database-population measurements. They are model calculations;
their presence does not establish an empirically calibrated annotation probability.

## Interpret result status and scope precisely

A numeric cell contains its value, unit, availability status, missingness reason,
and, where applicable, numerator, denominator and completeness. A measured zero
is available. A null value is accompanied by its reason; it is never converted
to zero. Native nonzero exit, partial capture, malformed report, unsupported
metadata and a successful zero-hit search remain distinct outcomes.

`iteration_inclusion`, `iteration_convergence` and `iteration_comparison` retain
only source-qualified facts. A checkpoint filename, array index, configured
iteration limit or absence of a message cannot establish a biological round,
membership or negative convergence. Query-scoped convergence does not establish
convergence for every search or round. Native-message extraction integration
must be verified separately before relying on that path.

The receiving episode gets the requested recorded fields from its actual child.
Complete saved sheets and calculator outputs remain available for later selected
views. Selecting another view does not rerun the native search. These operations
do not produce a new overall annotation score or an LLM assessment of the result.
