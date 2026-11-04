# Retained real A103 inputs

These are original bounded NCBI GenBank responses and UniProt sequence/metadata
responses acquired on 2026-11-03 and 2026-11-04. `manifest.json` retains hashes, source URLs and
exact one-based-inclusive EFetch parameters. The records are fetched windows,
not complete genomes; unavailable flanks and unexamined replicons remain unknown.
Original record coordinates are recovered from those retained requests.

Sequence identity was checked against actual genomic CDS translations:

- E. coli NC_000913.3: P39280 / b4146 (epmB/YjeK), P0A6N4 / b4147 (EF-P),
  P0A8N7 / b4155 (epmA/PoxA), P31806 / b4167 (nnr/YjeF).
- Salmonella NC_003197.2: Q8ZKB8 / STM4333 (epmB), with EF-P and epmA leads.
- P. gingivalis W83 AE015924.1: AAQ66184.1 / PG_1070 (kamA), resolved from the
  original genome paper's locus lead through its actual NCBI feature table.
  The bounded window also includes the annotated PG_1073/PG_1074 components.
  Those product labels remain source annotations rather than independent assays.
- R. capsulatus NC_014034.1: D5ARG8 / WP_013068946.1, current RCAP_RS16045,
  old locus RCAP_rcc03249.
- B. subtilis NC_000964.3: O07620 / NP_388918.1, current BSU_10370 (BioY).
- M. jannaschii NC_000909.1: Q60352 / WP_010869535.1, current MJ_RS00220,
  old MJ0044/MJ_0044.
- M. thermautotrophicus NC_000916.1: O26153 / WP_010875687.1 (MTH_47).
- T. acidophilum NC_002578.1: Q9HLX1 / WP_010900530.1 (Ta0103).

The yeast NNR1/NNR2 records provide separate-domain sequence leads for fusion
analysis. Search metadata and source product labels do not constitute new assays.
Source knowledge and evaluation case labels belong to the harness; no expected
function or expected numerical score is supplied as the investigation goal.
Fresh model decisions, scripted engineering choices, new native calculations
and retained-data replay must be labeled separately in execution reports.

Reusable inputs stay here. All execution databases, logs, native jobs, caches,
temporary files and source snapshots belong beneath top-level `runs/`.
