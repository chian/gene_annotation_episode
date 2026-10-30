# Shared provider workload S handoff

Implemented only the four assigned new staged files. The public APIs retain
exactly the accepted keyword/positional names and closed CommonFields,
CommonCalculationParameters and CommonComponents shapes. The common extractor
uses supplied reader values; the common dispatcher calls the eight existing
shared calculators. No shared numerical formula, production file, parser,
registry, runtime prompt, episode behavior, W05 or annotation score was edited.

## Actual verification

- Final staged eight-file suite: **531 passed, 9 subtests passed in 11.18s**.
  Complete actual stdout is `TEST_RUN_001.txt`.
- The S file contains **52 collected tests**. The integrated S/G/C provider
  run immediately before final export reported **131 passed in 7.24s**.
- Absolute interpreter:
  `/home/chia/repos/gene_annotation_episode/.venv/bin/python`.
  Cwd and PYTHONPATH were the exact implementation `staging` directory.
  Tests assert that the three S imports resolve to the assigned staged files.
- Six complete exported examples replay identically from JSON with file,
  network and subprocess operations disabled during extraction, saved
  validation and calculation. `EXPORT_RUN_001.txt` is the actual exporter
  stdout. `EXAMPLES_MANIFEST.json` pins every implementation, example and
  retained raw artifact by SHA256 and byte count.
- The complete native matrix example is compressed only for storage: its
  uncompressed JSON is 89,402,103 bytes, including exact extraction inputs,
  ReadResult, full saved sheet, parameters and all requested components. No
  preview/truncation substitutes for the data. Complete original native bytes
  are copied under `raw/` and retain their original hashes.

Final command:

```text
PYTHONPATH=/home/chia/repos/gene_annotation_episode/verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24/staging /home/chia/repos/gene_annotation_episode/.venv/bin/python -m pytest tests/test_phylogeny_formats.py tests/test_phylogeny_calculators.py tests/test_phylogeny_raxml_inputs.py tests/test_bvbrc_codon_tree_native.py tests/test_bvbrc_codon_tree_calculators.py tests/test_bvbrc_phylogeny_common.py tests/test_bvbrc_gene_tree_provider.py tests/test_bvbrc_codon_tree_provider.py -q
```

## Concrete numerical and association examples

The synthetic four-row matrix has 16 cells, 2 gaps, 10 canonical symbols and
4 ambiguous X symbols. Gap fraction is 0.125; the variable canonical site's
entropy is 0.9182958340544896 bits. Signed branch sum is 13 in native_unknown
units; native support 0 remains a measured zero with unknown method. Function
A uses separate 2/4 and 2/3 fractions; taxonomy uses its independently supplied
three-member population and same-taxon pair fraction 1/3.

The retained official CodonTree matrix has 9 rows, 15,300 columns, 137,700 cells
and 17,308 gaps: 0.12569353667392882. Its raw tree has nine tips. Both retained
GeneTree XML examples have 17 tips and 14 generic support observations with
unknown method; converter inserted-zero/lost-zero-support qualifications remain.
These are retained repository outputs, not newly submitted service results.

Additional checks cover invalid-with-value readers, malformed independent
matrices with valid trees, complete trees inside a partial forest, conditional
bootstrap frequencies, exact restricted comparison splits, source-record and
input/member association failures, two bindings containing member q, unknown
original coverage, duplicate headers, negative branches, root XML zero support,
requested/observed setting conflicts and invalid native engine records.

The clarified transformation rule is exact: before digest is the single known
original MemberFact digest; after digest is the single complete output row's
UTF-8 sequence, retaining case and gaps. Unknown/multiple operands use null.
Original nucleotide correspondence requires actual molecular units, strand and
translation metadata for interpreted coverage; incomplete metadata retains the
asserted map but returns unavailable coverage.

Missing alphabet, branch unit or bootstrap method does not erase independent
measurements. Unsupported alphabet yields unknown canonical quantities while
retaining literal counts. Unknown named branch units retain native_unknown
signed quantities and an exact unmet requirement. Unsupported bootstrap method
omits only that unsupported component with its dependency; method conflicts are
explicit diagnostics. The original requested parameters remain unchanged.

Shared-original dependence uses actual source content identity, evidence
pointer and MemberFact.member_pointer. Two members within one container are
not equated merely because they share an evidence record. Conflicting known
facts at the same original locator fail validation. Identical final sequences
remain a separate dependence kind.

## Failure retention and remaining boundaries

`FAILURE_HISTORY.json` explicitly distinguishes early tool-transcript-derived
failure summaries from actual saved stdout. The initial root XML omission was
fixed. Incorrect duplicate-label, invalid-header, native-file-suffix and
alphabet-negative fixtures were corrected without changing native data or
scientific formulas. `invalid_association.json` retains exact current bad input
and its invalid ReadResult. No unsupported scientific result was replaced by
zeros, a dummy member or a placeholder tree.

This is a pure provider layer. Store authentication and external raw-byte
custody, C4 semantic slot dispatch, production installation and registries,
selected resource-child execution, typed episode returns and live service runs
remain root integration work. This handoff does not declare GeneTree or
CodonTree complete. Unknown PhyML/FastTree metadata, original maps, native task
versions and missing acquisition remain explicit.

The immutable objective and all sixteen design principles were reread verbatim
from the original attachment after source/native study and again before this
handoff, followed by the exact S workload, accepted reader/outcome and component
contracts and root's additive provider clarification. The objective SHA256
remains `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
