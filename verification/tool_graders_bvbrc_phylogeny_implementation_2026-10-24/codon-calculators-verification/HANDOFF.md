# CodonTree numerical handoff

Implemented only the two assigned new staged files:

- `staging/gene_annotation_episode/bvbrc_codon_tree_calculators.py`
- `staging/tests/test_bvbrc_codon_tree_calculators.py`

The module exports the three fixed pure calculations and
`codon_calculation_requirements`. No production files, shared numerical or
format modules, table parsers, provider extractors, C4 registry, original
contracts, checklist, prompts, credit, method_loop or resource behavior changed.

The immutable goal remains SHA256
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
The original Codon contract remains
`040946fc00c98df6ffd0263ea83d5c4dc5b833eabc4c860374a6cd2592c48b06`.
Root accepted the historical-population interface correction in
`CODON_CALCULATIONS_ADDENDUM_001.md`, SHA256
`125085ee5eb70d7eab949687052bef172eec0847edb9636356b872cad2c80762`.
It adds required `missing_requirements` to historical ratio output so an unknown
empty population cannot masquerade as a complete empty population. No formula
changed; no dummy numerical row carries the missing information. Root also
accepted the provider sheet's required `assembly` and `read_outcomes` keys via
`../../tool_graders_bvbrc_phylogeny_provider_handoffs_2026-10-24/ACCEPTANCE_001.md`,
SHA256 `fcfaaf361318a6d0d86bf1f5c8b9d1ba3b9d8dd2024407b2072bf3e743a8c58e`,
accepting `ADDITIVE_CONTRACT.md` at SHA256
`8535b1be2802406ca70d0ba402f1400f5d7b6b079e4c4c655a62e54ea78e5d7b`.
The numerical module's only subsequent change was those two required keys.

Final module SHA256:
`e23d8aa26b90d9089819b1e8faac5a8b6c9f8b4da39fbfcb5a89934158ba4904`.
Final test SHA256:
`9ff70ea1f10eccced4cb3a0ac597e16a597542e6eae40344b7b003e991d5cd0f`.
`SAVED_RECALCULATION_004.json` records these and all actual dependency, source,
contract, input and filled-result hashes and sizes.

## Exact numerical behavior

`native_codon_literal_statistics` consumes an already parsed AlignmentDocument
and the exact supplied AlignmentPopulation. It validates both, preserves case,
and treats only `-` as a gap. Literal X, dots, stops and other nongap symbols
participate as literal states. Counts use rows/columns/characters; per-site
squared frequencies use mean_squared_fraction, the column sum uses
column_summed_squared_fraction, its mean uses mean_squared_fraction, ranking
uses square_root_columns, and row mean log frequencies use bits_per_column.
All derived quantities reference the supplied alignment population. Empty
populations retain actual count zeros and null statistical ratios/log means;
incomplete populations cannot supply complete denominators. No canonical-state
entropy is substituted, and no rows are padded or filtered.

`codon_family_population_components` resolves exactly the requested family and
genome populations by identity. Their counts use separate denominators. It
validates every matrix row of every selected family, including unselected
genomes, before computing present genomes, missing genomes, extra feature
copies, presence fraction and signed native initial rank. Protein/CDS membership
records supply no additional copy votes. An absent genome matrix row is unknown,
not absence. A known complete empty genome set needs no unused membership data
for its zero sums. Missing other families do not erase arithmetic for a known
family with a complete genome denominator. Whole family population count remains
unavailable when its membership is incomplete.

`native_codon_worst_sequence_ratios` requires the explicit evaluated_pretrim
family stage and exact expected feature memberships. It rejects duplicates,
wrong known family/feature membership, wrong units, nonfinite numbers, invalid
states and conflicting structures. It computes same-genome means over that
entire expected sequence population, then preserves each numerator, adjusted
denominator and ratio, plus the native maximum per complete family. The literal
adjustment is 0.00001. Missing feature→genome identity makes all potentially
affected genome means unavailable; a supplied identity with a missing value
affects that genome only. Positive mean-log values, and supplied incompatible
null measurements, produce incompatible derived cells without clamping or a
manufactured acquisition need. The >8 native category is not applied as a gate.

Historical output population references identify the supplied evaluated-family
population; genome/family/feature rows constrain each subset. Original input
Quantity population_ref values remain unchanged and may identify the family's
native pre-trim alignment. These pure functions do not authenticate that supplied
stage against an execution record. The provider must establish that relationship.

`codon_calculation_requirements` only resolves the seven frozen reasons. It
preserves explicit source refs, deduplicates equal meanings, rejects unknown or
conflicting definitions, and performs no arithmetic or acquisition. IDs escape
`%` as `%25` and `/` as `%2F` in each separate scope segment, followed by the
exact reason. The shared requirement registry was not edited. Providers should
invoke the Codon helper on Codon components, the shared helper on shared
components, and merge the resulting requirements with identity validation.

## Inspection and numerical evidence

Read the complete native `phylocode.calcAlignmentStats` producer, complete
`selectSingleCopyHomologs` population/ranking function, and the full relevant
launch-script population construction, pre-trim evaluation, same-genome mean,
ratio, family selection and later trimming/output consumers. Their retained
paths are under
`verification/tool_graders_bvbrc_application_artifacts_2026-10-24/sources/codon_trees/`.
The immutable objective and all sixteen design principles were reread verbatim
after substantial native inspection, before implementing, before the additive
correction, and at handoff, followed by the exact current Codon contracts.

The fixed four-row example returns 16 cells, 2 gaps, per-site squared frequencies
1, 0.5625, 0.3125 and 1; sum 2.875; mean 0.71875; ranking 1.4375; row log means
-0.75, -0.35375937481971094, -0.603759374819711 and -0.603759374819711.
The shared canonical entropy remains separately 0.9182958340544896 at the
variable canonical site; X-only has literal squared frequency 1 and undefined
canonical entropy.

The explicit four-genome family example returns present 3, missing 1, extra
copies 1, fraction 0.75 and rank 2; the separate four-single-copy family ranks 4.
Signed negative initial ranks remain available. Complete historical synthetic
rows give same-genome means -1 and -2, with adjusted denominators -1.00001 and
-2.00001. Missing historical identity, missing measurement, incompatible values,
unknown empty populations and zero values have separately saved examples.

The actual retained official final PHYLIP alignment yields 9 rows × 15,300 sites
= 137,700 cells; gaps 17,308; literal squared-frequency sum
10056.41975308642; mean 0.657282336803034; ranking 81.30133501475134. Every
site and all nine row means are retained in the filled components. An exact
rational oracle checks the nongap count squares. The isolated inspected native
`calcAlignmentStats` function was also executed on those unchanged saved rows,
without importing or running the upstream program. Gap counts/fractions match
exactly; sum differs by -7.912603905424476e-10 and mean by
-5.162537064506978e-14 because this implementation uses math.fsum while the
native function uses successive floating-point additions. This is final-matrix
arithmetic verification; it does not reconstruct any missing pre-trim tables.

## Actual checks and saved recalculation

The final staged check passed **91 Codon tests + 81 shared calculator tests +
43 format tests = 215 tests, plus 9 format subtests**, with zero failures,
errors or skips in 3.99 seconds. `CODON_SHARED_TESTS_004.xml` is the direct pytest
JUnit receipt. The prior 211-test/9-subtest run remains in
`CODON_SHARED_TESTS_003.xml`. The earlier 83-test additive run is retained in
`CODON_TESTS_002.xml`. The initial 70-test run and prior fixture-only error
(missing PHYLIP continuation_ids argument, corrected to absent) are recorded in
`PRE_ADDENDUM_TEST_RECEIPT.json` as transcript-derived evidence. No numerical
formula changed to satisfy a mistaken test expectation.

`SAVED_OPERANDS_004.json` and `FILLED_COMPONENTS_004.json.gz` contain all 31 full
cases, including the actual final matrix and every resulting numerical cell.
All cases reproduce exactly with file, socket/network, process, parser entry
points and imports/model-client loading disabled inside the calls. There is no
model dependency or hidden parser call. Static dependency checks accompany
the guards. Zero forbidden-access attempts occurred and every input object was
unchanged. Earlier unnumbered, `_002` and `_003` operand/component/replay receipts remain
retained separately; the new output field does not rewrite them.

Reproduce the current saved outputs from the staging directory:

```sh
PYTHONPATH=/home/chia/repos/gene_annotation_episode/verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24/staging /home/chia/repos/gene_annotation_episode/.venv/bin/python ../codon-calculators-verification/recalculate_saved_examples.py
```

## Provider handoff and limits

This module accepts the frozen CodonTreeSheet shape with the existing shared
addendum's Populations.taxonomy and the now-accepted required ProviderAssembly
and read_outcomes fields. Tests use a correctly shaped ProviderAssembly and
both empty and actual synthetic reader-outcome arrays. Missing either key or
supplying an unrelated extra top-level key fails specifically. The calculator
validates its numerical operands and their relationships, not every unrelated
source/custody field; it does not duplicate provider validation. No extra
analysis_id was added to Family. Provider orchestration supplies the correct
analysis-scoped records and retains every originally selected analysis.

No provider extractor/calculator orchestration, actual child-owned artifact
binding, C4 custody/adapter, requested episode projection, production installation,
live BV-BRC service execution, or HPC execution was implemented or verified by
this workload. Source truth, pre-trim provenance and external metadata joins
remain the provider's responsibility. The current pure numerical contract and
its approved empty-population correction are implemented and verified.
