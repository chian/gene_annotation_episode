# Complete Codon family matrices retain their declared population

Additive correction, 2026-10-24. The original numerical sheet, native formulas,
source-stage receipts and contracts remain unchanged. Root accepted this exact
scope before implementation.

The production `codon_family_population_components(sheet, *,
family_population_id, genome_population_id)` consumes the saved sheet. Its
`_family_matrix` validator must not interpret `matrix_completeness=complete`
as a claim that every independent native membership feature or genome occurs
in that matrix. `ExplicitFamilyMatrix.genome_population_id` identifies the
matrix's scope. Native protein/CDS records may include other genomes, including
optional genomes, or accompany a complete empty main population.

Keep every supplied membership record unchanged. Keep matrix row/feature
uniqueness, source-record uniqueness and included/deleted feature checks. For
an included feature explicitly mapped by the matrix, compare its mapped genome
with a nonempty membership genome set. Reject that actual contradiction even
when the matrix is partial. Independent feature/genome arrays are never zipped;
an absent feature mapping and an empty genome list establish no new association.
Deleted/missing-CDS features are not constrained to the included-genome list.

Provider assembly owns the stronger checks using the saved explicit matrix
population, native table and `FeatureGenomeJoin`. The calculator does not parse
those tables or fabricate unseen relationships. Provider changes are owned by
the separate Codon provider workload.

Arithmetic is unchanged: for the explicitly requested genome population of
size N, present counts matrix rows with at least one feature; missing is
N-present; extra copies sums max(copies-1,0); presence is present/N; native rank
is present-extra. Missing selected rows stay unknown. A complete empty genome
population yields zero counts and a null fraction with denominator zero.
Independent protein/CDS records do not add votes or expand the denominator.

Owned changes are only the production calculator, a new matrix-population test
module and this new verification directory. No historical stage, provider,
prompt, episode, evidence-axis, W05 or accounting files are edited here.

Verification will retain actual before/after pytest receipts, filled saved
numerical examples and offline replay results. Existing 91 calculator tests
must remain passing. New coverage includes complete subsets, complete empty
main populations with unrelated memberships, optional populations without
matrix coverage, partial/missing data, actual contradictory mappings and
retained native membership with explicit source-table joins. Synthetic cases
remain labeled synthetic; no live service or episode return is claimed.
