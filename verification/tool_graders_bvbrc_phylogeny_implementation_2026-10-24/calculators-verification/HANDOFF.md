# Shared phylogeny calculator handoff

This workload implemented new staged code only. It did not install production
modules, bind a provider operation, execute a BV-BRC job, change a prompt or
episode, edit W05, or change the fixed work accounting. The immutable goal
remains SHA256 `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.

## Delivered files and contracts

- `staging/gene_annotation_episode/phylogeny_calculators.py`: all eight agreed
  public calculations and the explicitly accepted `calculation_requirements`.
- `staging/gene_annotation_episode/phylogeny_calculation_contracts.py`: pure
  closed-operand checks, quantity constructors and finite requirement registry.
- `staging/tests/test_phylogeny_calculators.py`: 81 tests, including actual
  parser-to-calculator retained-native cases.

The original frozen goal/proposal/shape/calculator hashes matched their declared
values. The additive contract was read and validated at SHA256
`67e011477d56a20c84ccf8f3cbf5dd4bd18dd55cfebcae2348bfdd9ff98dd63f` before its changes.
`VERIFICATION_REPORT.json` records complete file hashes, including the actual
parser dependency revisions used in the final check. All asserted calculator
and parser module origins are inside this staging package.

The actual dependency is exactly
`phylogeny_format_contracts.validate_tree_record(dict) -> dict` and
`validate_alignment_document(dict) -> dict`. The calculators do not parse bytes
or read a hidden sheet. Invalid closed structures and contradictory operand
relationships raise stable `ValueError("phylogeny_<code>")`. Call arguments can
use JSON arrays where the signatures show tuples, supporting saved JSON replay.

## Implemented numerical behavior

`alignment_components` retains literal source-character counts, exact selected
row/site/cell populations, alphabet-dependent canonical/ambiguous/stop/other
counts, per-row matrix occupancy, canonical site entropy/majority, disjoint
pairwise categories and full-final-string duplicate groups. Only literal `-`
is a gap. Unknown alphabet leaves canonical statistics unavailable. Incomplete
matrices do not acquire whole-population denominators from surviving prefixes.

`ungapped_coordinate_map` returns only staged nongap offsets.
`original_member_coverage` separately validates supplied original members,
lengths, digests, intervals and staged offsets when present. It unions overlap,
keeps separate member denominators in concatenated rows, and checks complete
selected nongap association across all members before returning coverage. A
missing map is unavailable, not observed zero. Known partial unions stay
explicitly partial; an all-gap row can yield a genuine zero covered count.

`tree_components` uses the exact complete supplied leaf population. Root
pseudo-edge length remains in the input but is excluded from sums. Missing
lengths retain a known partial sum and missing-edge count; zero and signed
negative native lengths remain distinct. Known branch units require matching
per-edge NativeObservations; a requested unit alone cannot establish provenance.
The known partial sum retains the units of its actual contributing edges.
Support records must resolve supplied NativeObservation IDs for the same
tree/node and native support field, with consistent method/scale. Multiple
conflicting observations remain referenced and have unavailable rescaling.
Absent support is not_measured; it is not fabricated zero support.

Whole-tree split identities use actual terminal indices with numeric canonical
tie breaking. Multiple original edges mapping to one unrooted split are retained.
Bootstrap joins are explicit bijections into a single reference tree's terminal
identities. Missing/incompatible mappings are excluded with reasons, preserving
expected, supplied and usable counts; incomplete-population frequencies are
explicitly conditional. Labels are never an implicit join in a calculator.

Function composition keeps all-member and recorded-member denominators, with
each member counted once per function and multi-valued functions preserved.
Taxonomy retains known/unknown counts and pairs among known taxa at the supplied
rank. The additive TaxonPopulation permits genuine genome subjects, while
function CompositionPopulation still forbids genome-wide function votes.

Relationship comparisons require explicit injective tip correspondence and
retain omitted tips. The additive restricted split arrays save both sides and
all original contributing edges under comparison-specific IDs; every shared
split pair resolves to those arrays. Whole-tree split IDs remain unchanged.
RF compares only the explicitly mapped unrooted split sets. No horizontal
transfer conclusion, annotation score or universal confidence is computed.

## Concrete provider handoff

The future `calculate_gene_tree` and `calculate_codon_tree` consumers must:

1. Validate actual full-sheet source-record/subject relationships and evidence
   through their provider/C4 path before calling these calculators. Then select
   assignments for an exact CompositionPopulation or TaxonPopulation by full
   QualifiedSubject identity. Do not drop a conflicting identity to hide it.
2. Retain native observations and parser/provider qualifications in the sheet,
   including negative lengths, unknown methods/units and derivative XML limits.
   These calculators do not authenticate custody or recover absent run evidence.
3. Retain the separate `Populations.taxonomy` registry required by the addendum.
   A taxon request resolves there; function requests resolve in composition.
4. Merge `calculation_requirements(component)` into the provider requirement
   registry. That helper traverses already-calculated values and performs no
   numerical recalculation, parsing, I/O or acquisition. It retains explicit
   OriginalCoverage requirements and rejects unequal meanings sharing an ID.
5. Persist the restricted comparison split definitions for later reference
   resolution. A return resolver reads them; it does not rerun the comparison.

The accepted requirement registry is finite:

| Reason | Kind | Role |
| --- | --- | --- |
| alignment_population_incomplete | output_bytes | alignment |
| alphabet_required | scientific_metadata | alignment_alphabet |
| original_member_length_required | input_metadata | original_member_length |
| original_residue_map_required | scientific_metadata | original_residue_map |
| branch_lengths_required | output_bytes | native_tree |
| support_method_unresolved | scientific_metadata | support_method |
| support_scale_unresolved | scientific_metadata | support_scale |
| support_observations_conflict | scientific_metadata | branch_support_resolution |
| bootstrap_expected_count_required | scientific_metadata | bootstrap_population |
| bootstrap_replicates_not_retained | output_bytes | bootstrap_replicates |
| composition_population_required | input_metadata | composition_population |
| taxon_associations_required | scientific_metadata | taxon_associations |

IDs start `phylogeny/`; each supplied population/member/rank identifier occupies
one escaped segment (`%` becomes `%25`, `/` becomes `%2F`). Row/member and node
scopes add explicit segments. A taxon-label requirement includes the rank.
The final segment is the exact finite reason. Source refs remain empty unless
an explicit original-coverage requirement carries the supplied artifact ref.
Unknown/dangling reasons fail. Genuine zero denominators do not manufacture an
acquisition requirement, and this helper never selects work.

## Actual verification

The final staged run passed **81 calculator tests + 43 format tests = 124 tests,
plus 9 format subtests**, with zero failures/errors in 3.91 seconds. The earlier
calculator run had 65 passes and two failing new test expectations: the DNA/RNA
fixture has three other nongap symbols (dot, star, X/T), not four. Those expected
counts were corrected; no formula was changed to satisfy the mistaken values.
Earlier successful test records and saved examples remain retained separately.

Checked hand values include:

- Four rows × four sites = 16 cells; gaps 2, ambiguous X 4, canonical 10;
  gap fraction 0.125; variable-site canonical entropy 0.9182958340544896 bits.
- Original interval union 6 positions / original length 8 = 0.75; this is
  distinct from staged occupancy. Partial maps do not return full coverage.
- Signed nonroot branch sum 9.5, excluding the retained root length of 99.
- Function A: 2/4 = 0.5 among all members, 2/3 among recorded assignments.
- Four genomes: known taxa 3, unknown 1, distinct known taxa 2, same-taxon pairs
  1 out of 3 known pairs, fraction 1/3.
- Explicit incompatible four-tip topologies: RF 2, fraction 1. The five-to-four
  counterexample and three-original-edge collapse retain resolvable restricted
  definitions and do not invent full-tree split identities.

Actual parser outputs from the retained official CodonTree example yielded
9 rows × 15,300 sites = 137,700 cells; 17,308 gaps;
`17308/137700 = 0.12569353667392882`. Four partitions each contain 3,825 sites.
Six nontrivial splits each occur in 100/100 explicitly mapped bootstrap trees.
The native best and supported tree topologies have RF 0 over nine mapped tips.
These are repository example artifacts, not a new AppService execution or
verified original-task custody chain.

`SAVED_OPERANDS_002.json` contains complete saved calculation inputs and explicit
parameters for 14 cases across all eight functions. `FILLED_COMPONENTS_002.json.gz`
retains the complete resulting values, including every native alignment site.
The verification program loads those files before disabling file/network/process
and import access during all calculator calls. All 14 cases reproduce exactly,
with zero forbidden-access attempts and unchanged input objects. This is
saved-document arithmetic verification, not provider/episode integration.

Reproduce from the staging cwd with absolute Python and staging PYTHONPATH:

```sh
PYTHONPATH=/home/chia/repos/gene_annotation_episode/verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24/staging /home/chia/repos/gene_annotation_episode/.venv/bin/python ../calculators-verification/recalculate_saved_examples.py
```

Production installation, provider-specific sheet extraction/calculation,
C4 adapters, tool information/library binding, requested typed episode returns,
full integration, live BV-BRC execution and HPC deployment remain unverified
and outside this completed shared-calculator workload.
