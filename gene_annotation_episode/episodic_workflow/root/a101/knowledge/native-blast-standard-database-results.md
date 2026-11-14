# Standard native database BLAST results

Select `native.blastn.database`, `native.blastp.database`,
`native.blastx.database`, `native.tblastn.database` or
`native.tblastx.database` from an explicitly configured HPC resource. The
selected request supplies software and prepared database identities, complete
FASTA input or a supplied tblastn text ASN PSSM, options and output selection.
These database operations have their own contracts and result families. The
launch child owns resource preparation and submission; monitoring uses the
existing resource instructions and the original attempt's actual status/logs.

The results child uses `execution.results.status` to observe the selected
attempt or `execution.results.collect` to acquire its complete declared bundle.
Collection authenticates the original submission and request, transfers bounded
byte chunks, preserves every artifact slot, and retains complete JSON15 or
explicit-field tabular6/tabular7 bytes. It never starts or retries a search.
Failed native attempts can supply partial results, while remaining unsuccessful.

Use `native_blast_standard_database_selector_v1` with
`acquisition: complete_bound_bundle`. Each projection selects a family, rows by
offset/limit or received record keys, and explicit numerical `metrics` or
`booleans`. The current metric catalog describes exact sources, formulas, units,
populations and denominators. Complete inputs, parsed reports, sheets,
calculations, rows, index and diagnostics remain retained independently of the
small requested return.

| Question | Families and representative fields |
| --- | --- |
| Report population and limits | `search`: `reported_hit_count`, `reported_hsp_count`, `parsed_hit_count`, `limit_reached` |
| Original HSP measurements | `hsp`: `native_score_bits`, `native_raw_score`, `native_evalue`, `paired_columns`, `identical_pairs`, `paired_identity` |
| Full biological coordinate geometry | `hsp`: `qualified_paired_query_units`, `qualified_paired_reference_units`, `full_query_paired_coverage`, `full_reference_paired_coverage`, `qualified_geometry_available` |
| All HSP correspondence for a hit | `sequence_hit`: `query_paired_coverage`, `reference_paired_coverage`, `selected_query_coverage` |
| Explicit function assignments and selected model | `sequence_function`: `function_mass`, `function_prior`, `unadjusted_probability`, `representation_adjusted_probability` |
| Actual database representation and taxonomic relationships | `sequence_population`, `sequence_taxonomy`, `sequence_quality` |
| Native supplied PSSM values | `pssm_matrix`, `pssm_cell`, `pssm_position` |
| Original reported search statistics | `search_statistic` |

The twelve families also include `sequence_group`. Consult the actual catalog
for each family's admitted fields; unavailable families or fields are rejected.
Function weights require explicit function assignments and selected model
parameters. Representation adjustment additionally requires source-qualified
database census measurements. These weights are conditional model calculations,
not calibrated annotation probabilities. Taxonomy and source quality remain
separate numerical components. Taxonomy, source quality, coverage and identity
do not enter the function-weight formula.

Supply exact received `metadata_inputs` and `retained_sources` to establish
query identity or sequence database metadata. The admitted consumers are
`query_identity` and `sequence_database`, using their registered metadata
schemas. Preserve original search, hit, description and HSP identities when
linking functions, taxa, full sequences and source measurements. A reported
accession or similar length does not establish an exact sequence relationship.

Translated BLASTX query coordinates are original nt and reference coordinates
are aa. TBLASTN uses aa queries and original nt references; TBLASTX uses original
nt on both axes. Qualified full-axis geometry points into the saved database
calculation. Reported lengths and raw coverage remain separate. Full-query and
selected-query coverage have distinct denominators. A supplied PSSM requires
its actual master symbols and position map, not an inferred consensus.

Numeric cells retain value, units, availability, missingness reason, original
component pointer and applicable numerator/denominator/completeness. Measured
zero, unavailable metadata, malformed native output, calculation failure and
unsuccessful execution remain distinct. A failed calculation retains raw native
rows and valid siblings without substituting parameters. Selecting another view
uses frozen rows without reparsing or recalculating.

Only an exact received full query subject within the assigned scope can yield a
query HSP observation. Missing biological binding leaves numerical rows as
source facts. Database hits do not become inferred biological reference records.
The receiving parent obtains only the typed cells returned by its actual child;
saved row or artifact presence does not grant authority to unrequested cells.
These operations add no annotation score or model-composed judgment.
