# Tool-facing BLAST scoring sheets

These functions populate internal tool sheets and calculate their numerical
components from retained native results. Annotation-credit aggregation is a
separate consumer.

## Callable boundary

`gene_annotation_episode.blast_graders.grade_blast_result` consumes retained
native bytes, the explicit comparison mode and actual resource provenance.
It returns `sheet` and `probabilities` (`None` for pairwise comparison).
It performs no network request, job submission or metadata lookup.

| Stage | Function | Responsibility |
| --- | --- | --- |
| Native parser | `parse_blast_json` | Direct JSON2/JSON15, JSON2 archive, database or one-pair `bl2seq` report. |
| Native parser | `parse_blast_tabular` | Declared BLAST outfmt 6/7 fields; retains independently ordered metadata sets without inventing associations. |
| Alignment calculator | `alignment_components` | Native scores, alignment counts, actual residue pairs, gap-resolved coverage and explicit denominators. |
| Pairwise sheet | `build_pairwise_sheet` | Per-HSP measurements, union coverage, repeated mappings and conflicting correspondences. |
| Database sheet | `build_database_sheet` | Every hit's linked reference/function/taxon/source data; set-wide numerical components; database representation and missing-data qualifications. |
| Database calculator | `calculate_database_probabilities` | Replaceable formula over a saved database sheet, with all parameters and assumptions returned. |

JSON format is shared by API and command-line BLAST; resource placement alone
does not select the parser. HPC tabular files may omit alignment strings,
lengths, taxon associations or database statistics. Such omissions remain
explicit; the parser does not manufacture these data. Multiple queries and
iterative PSI-BLAST results require a separate explicit selection path and are
not silently combined by these single-query examples.

For detailed HPC result generation, JSON15 preserves the native description
associations and alignments. Tabular callers supply their exact `-outfmt` column
list or retain the `# Fields` header. Existing HPC execution choices remain with
the execution episode. These graders neither configure nor run an HPC job.

## Metadata and numerical cells

`blast_reference_metadata` reads supplied UniProt records, NCBI Taxonomy XML,
and explicitly linked NCBI assembly reports. Functions come from explicit EC
assignments and retain their source evidence codes. Names and GO annotations
remain separate source statements; neither is guessed to be an EC assignment.
This EC reader is an initial source reader, not a restriction of the database
sheet to enzymes: the sheet accepts other explicitly supplied function labels.

Taxonomy attaches by exact taxid. Assembly metadata requires the actual
protein-to-assembly link; sharing an organism is insufficient. Distinct source
records for the same reference remain available to that reference's function
calculations. Data from another native-hit alias do not silently transfer.

The internal sheets preserve:

- The query, recorded request, database/search statistics and reporting limits.
- All native HSP scores, counts, alignment strings, coordinates, frames and
  accession/taxon descriptions, plus parsed source bytes in the example artifacts.
- Paired positions and coverage, identity with its denominator, duplicate HSP
  mappings, alternative residue maps and incomplete geometry.
- Reference functions and evidence, full taxonomic lineages where supplied,
  target taxonomy and whether it is independent of the search.
- Source/assembly metadata, measured completeness and contamination, contig
  counts/lengths and measurement methods. CheckM percent-to-ratio conversion is
  arithmetic, not a category-based reliability grade. A complete assembly does
  not establish cultured origin or experimentally confirmed protein function.
- Sequence duplicate groups and shared-study identities where actually known.
  Equal aligned fragments alone do not establish identical full sequences.
- Per-function/taxon/source numerical summaries; taxonomic agreement counts,
  denominators and ambiguity; independently supplied database function counts.

No observations of source quality or taxonomic spread alone diagnose horizontal
transfer, contamination or biological function. Raw measurements remain
available for later model refinement and investigation decisions.

## Initial database calculation

For a sequence group, take its largest reported HSP bit score once. Duplicate
aliases/HSPs do not add another contribution. With temperature `t` (default 1):

```
group_weight = 2 ** ((group_bit_score - largest_scored_function_group_bit_score) / t)
function_mass[f] = sum(group_weight / number_of_distinct_functions_in_group)
unadjusted[f] = normalize(prior[f] * function_mass[f])
representation_adjusted[f] = normalize(prior[f] * function_mass[f] / database_sequence_count[f])
```

Default priors are uniform over supplied scored function labels. The labels
need not describe mutually exclusive biological activities: these numbers are
conditional relative assignment weights under the stated reference-kernel
model, not calibrated probabilities of annotation correctness. A single
represented function can receive conditional weight 1 without proving that
function. Unknown-function reference mass, absent scores and result limits are
reported separately. Database representation requires actual matching database,
scope and sequence-count units; it is never inferred from the returned-hit list.

**The first probability model uses bit scores, duplicate grouping, explicit
function assignments, priors and available database representation.** Taxonomy,
source quality, annotation evidence codes, coverage, identity and shared-study
data are calculated/preserved but are explicitly listed as unused by this first
model. Their weighting has not been invented. The user can adjust the model
without re-extracting those already saved data.

## Examples and verification

The reproducible examples are in
`verification/w04_blast_graders_2026-10-24_001`. Run from the repository root:

```
PYTHONPATH=. .venv/bin/python verification/w04_blast_graders_2026-10-24_001/write_examples.py
.venv/bin/python -m gene_annotation_episode.blast_graders \
  --mode pairwise --resource local --format json2 \
  --input verification/w04_blast_graders_2026-10-24_001/native_pair/result.json \
  --output verification/w04_blast_graders_2026-10-24_001/native_pair/graded.json
```

The actual native two-sequence BLAST+ 2.17.0 test yields 243 paired residues,
238 identical pairs, 10 gap columns, query coverage 243/253 and paired identity
238/243. Its comparison sequence is explicitly synthetic; it is not a natural
homolog or a new scientific annotation.

The synthetic database case yields .8/.2 before representation adjustment and
.5/.5 using supplied whole-database counts 200/50. Recalculating the saved sheet
at temperature 2 gives approximately .4142/.5858 after adjustment. No new BLAST
run or extraction is involved. API and HPC-format fixtures exercise the same
data and calculations. Actual live API status and exact test evidence are in
that directory's `VERIFICATION.md`; fixture parsing is not an HPC deployment.

Format/field authorities: [NCBI native BLAST schema](https://www.ncbi.nlm.nih.gov/IEB/ToolBox/CPP_DOC/asn_spec/blastxml2.asn.html),
[BLAST output formats](https://www.ncbi.nlm.nih.gov/books/NBK279684/),
[NCBI assembly report fields](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/data-reports/genome-assembly/).
The probability formula above is this implementation's explicit initial model,
not a formula attributed to those format specifications.
