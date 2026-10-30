# CodonTree provider workload C

The actual provider extraction, saved-sheet validation and deterministic grader
are implemented. All three exported APIs have the accepted signatures:

```python
extract_codon_tree_sheet(*, documents: dict, inputs: tuple[dict, ...],
    observed_run: dict, joins: dict, assembly: dict, parameters: dict) -> dict
validate_codon_tree_sheet(sheet: dict) -> dict
calculate_codon_tree(sheet: dict, parameters: dict) -> dict
```

Owned staged files and final SHA256:

| File | SHA256 |
| --- | --- |
| gene_annotation_episode/bvbrc_codon_tree_inputs.py | 00f915ded5a9d8c259d338c59c7829761a397a781e72b5be72de7f631cab6aa5 |
| gene_annotation_episode/bvbrc_codon_tree_grader.py | 5393d24a52e255fb1d1027082218dadc9165e1f4a0a7f279bc14cb2db82f83be |
| tests/test_bvbrc_codon_tree_provider.py | 1e000e20b0a3765c9127ee6827b6150928f3aba9498dc194f28b7a2869b48f70 |

Paths above are relative to the adjacent `staging/` directory. All other changes
from this workload are evidence in this directory.

## Behavior and source review

Extraction uses the actual common provider and creates Genome, Family and
PartitionModel tables from exact caller populations, retained native reader
values and declared joins. Main, optional, each group, explicit main unions,
actually forwarded optional inputs, recorded positive native family counts and
final alignment/tree populations remain separately identified. Known empty and
unknown populations remain different. A prepared optional file is insufficient:
forwarding requires its actual observed `--optionalGenomeIdsFile` operand and
matching retained input/member evidence.

Complete family matrices retain every declared family×genome cell, including
explicit empty feature lists. Completeness applies to the declared genome scope.
Native members from optional/outside genomes survive without enlarging it;
known inside-scope features cannot be absent from a claimed complete matrix.
No selected-feature union creates requested population or absence information.

Native membership lists retain included, deleted-paralog and missing-CDS lists.
Raw duplicate occurrences and diagnostics survive; biological membership uses
the explicitly qualified stable unique projection accepted by root.
Contradictory included/deleted or included/missing records remain raw with an
error and precise requirement, and only the contradictory typed membership is
omitted. Protein and CDS records from the same features have an explicit
dependence group. Pretrim native statistics, selection states and final FamilyBlock
coordinates remain distinct. Four global partitions do not create family blocks.

Models use exact ModelAssociation reader/model/partition indices during
extraction. The retained native LGF partition matches the log's LG substitution
matrix under the documented empirical-frequency F suffix; fitted values and
source locations remain actual log values. Conflicting fitted records are kept
separately with an error. Sampling maps require the complete sample width,
explicit evidence and unique in-range primary-final-alignment columns, following
PROVIDER_CLARIFICATIONS_002.md. Unknown correspondence remains null.

All original ReaderInput statuses, diagnostics and invalid-with-value records
survive the shared boundary. Null/invalid alignment inputs coexist with useful
independent tree and family-table information. Unknown support method, branch
unit, original residue coverage and family namespace remain qualified/missing.
The source report's CDS-count defect remains an explicit diagnostic.

The exact-original identity correction is recorded in
[IDENTITY_CLARIFICATION_001.md](IDENTITY_CLARIFICATION_001.md). It requires matching
original content and member/source pointers for the source-record fallback.
Shared aggregate evidence and bare labels supply no identity; unsupported links
remain unknown with `member_genome_association_required`. Direct inline IDs,
validated groups and forwarded-input routes remain distinct. The concrete false
conflict is retained in [aggregate-member-before.json](aggregate-member-before.json),
with the corrected outcome in [aggregate-member-after.json](aggregate-member-after.json)
and its [complete sheet](aggregate-member-after.sheet.json).

Read in full: immutable goal and all 16 design principles; accepted provider
workloads, additive contract/acceptance, original boundaries/shapes/findings;
app specification, App-CodonTree.pl, p3x-build-codon-tree.py and phylocode.py;
applicable native/calculator contracts/addenda and actual staged implementations;
native 159-test and calculator 91-test handoffs. Relevant patric_api acquisition
functions and retained RAxML manual passages were also inspected. This workload
did not invoke the native scientific pipeline or fetch new scientific data.

## Actual verification

- **89 provider tests passed** in [pytest-identity-correction.xml](pytest-identity-correction.xml).
- **590 tests and 9 subtests passed; 1 source-location test deselected** in
  [pytest-final-location-selection.xml](pytest-final-location-selection.xml).
  That uniquely named historical test requires the old calculator's staged
  location. The final run intentionally uses the actual corrected production
  calculator; [run_tests.py](run_tests.py) independently verifies 11 exact import
  paths and hashes. All prior failures, including unsuccessful relative node-ID
  deselection, remain in the original receipts and
  [VERIFICATION_RECEIPT.json](VERIFICATION_RECEIPT.json).
- **20 populated examples and 20 exact guarded JSON replays** are recorded in
  [examples-manifest.json](examples-manifest.json) and
  [offline-replays.json](offline-replays.json). Each contains complete supplied
  operands, sheet, calculation parameters, calculated components and original
  extraction outcome, with byte counts and SHA256. Recalculation blocks file
  access, sockets, process execution and every native reader; saved operands
  remain unchanged. Extraction itself also passes the supplied-data-only guard.

The corrected real dependency is production
`gene_annotation_episode/bvbrc_codon_tree_calculators.py`, SHA256
`e8eeab6a379af3cf80b0c92089df13a8c06630abf8baabe04593d94aaab87d54`, delivered by
the separate matrix-population correction. The original staged calculator and
historical receipts are unchanged. The filesystem overlay links real files;
it contains no mocked implementation or module replacement.

Commands use `/home/chia/repos/gene_annotation_episode/.venv/bin/python`, staging
cwd and staging PYTHONPATH. The final combined command is:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/chia/repos/gene_annotation_episode/verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24/staging /home/chia/repos/gene_annotation_episode/.venv/bin/python ../codon-provider-verification/run_tests.py -q -p no:cacheprovider tests -k 'not test_import_origins_and_closed_exports' --junitxml=../codon-provider-verification/pytest-final-location-selection.xml
```

## Numerical examples and limits

The retained official example includes **20 historical membership rows for 10
families**, each membership retaining 8 feature IDs, and the complete **9×15,300
final alignment**. Its literal gap count is 17,308 of 137,700 characters; the
native literal nongap summed squared frequency is 10056.41975308642. The tree
has 9 tips. Four actual partition/model associations and native log likelihood
−56958.397755 are retained. Its original preselection family matrix and final
family boundaries remain unknown. The seven original native input files are
hashed in the example manifest.

The separate synthetic current-source-syntax example establishes hand values:
2 gaps, nongap squared-frequency sum 2.875, mean 0.71875 and native ranking
component 1.4375; F1 presence 3/4, missing 1, extra copies 1 and initial rank 2.
Explicit pretrim historical inputs give genome means −1 and −2 and denominators
−1.00001 and−2.00001. The complete-empty historical case has no fabricated rows
or requirements; unknown/partial/truncated empty history keeps its unmet
requirements. Complete main and empty-main matrix examples retain outside
optional memberships while using exactly their declared denominators.

The grader dispatches the actual seven common request fields and all three
existing Codon calculators. It adds no numerical formula, native selection
threshold, confidence score or annotation-credit aggregation.

Saved validation checks retained model artifact/partition/source relationships;
the flattened saved shape cannot reconstruct the original input-only RAxML
model array or authenticate its full index range. Exact extraction-time index
checking and the saved limitation are both tested, following root clarification.
The identity fallback does not establish links through different source objects
without a declared exact relationship. Fixtures do not establish original-task
custody, a live job, C4 publication or full episode integration. Those remain
separate root integration responsibilities.
