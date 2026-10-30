# MetaCATS native parsers and saved-document validators

This workload implements the five pure readers and five detached validators in
ACCEPTED_PURE_INTERFACES_001.md and INTERFACE_CLARIFICATIONS_002.md. It does not
claim a completed MetaCATS tool or production episode integration.

Owned implementation:

- `gene_annotation_episode/bvbrc_metacats_formats.py`
- `gene_annotation_episode/bvbrc_metacats_format_contracts.py`
- `tests/test_bvbrc_metacats_formats.py`
- `tests/test_bvbrc_metacats_format_contracts.py`

The parsers receive supplied bytes and an explicit format/encoding declaration.
They check the declared SHA256, preserve all readable native rows and tokens,
and return the exact frozen document/diagnostic shapes. They make no file or
network requests, launch no process, invoke no LLM and choose no resource.
Their validators consume saved records without calling the native readers;
they reject unknown keys and contradictory tokens, numerical states, source
ranges, ordered row indexes, headers and identities. Validation does not
authenticate original artifact custody.

The native source examined in full includes Meta-CATS.R, metadata_parser.pl,
App-MetaCATS.pl and MetaCATS.json. The existing BLAST dispatcher and pairwise
sheet/calculator were read as the separation example. No producer or existing
BLAST/phylogeny implementation was edited. No new dependency was installed.

All seven retained native Perl/R cases are exercised. These were actual native
component executions on synthetic or official supplied inputs in the earlier
native-execution directory. This workload reads those outputs; it does not
rerun the analysis, invoke an aligner or execute a live AppService request.
The official legacy source file is checked separately. `saved_examples/`
contains complete parsed documents for all 43 inputs, including every raw site,
pair, metadata row and adjusted-matrix row. VERIFICATION_001.json records input
and example digests, installed source/test digests and all row counts.

Concrete observations:

- The retained two-group AA site has native counts 6 A and 6 C, omnibus X²
  8.33055648117294, p 0.00389837142433717, df 1, and pair p
  0.000533148220906465. Surrounding conserved rows retain NA/1/NA/N/NA.
- Three-group AA pair p is 0.0173810251352965 for each explicitly emitted pair.
- Official NA has 765 raw omnibus and pair rows, including 312 variable sites;
  its filtered files each contain 143 rows. Significant-only files do not
  establish a complete test population.
- The native underflow case retains omnibus p=0 and raw pair p=1; the filtered
  pair file is empty. The parser never turns that 1 into a mathematical tail.
- The metadata-only case retains 13 metadata rows, 12 matrix rows, exported
  headings A/B/C, matrix group tokens 2/3, and the emitted pair label A,B. It
  does not relabel the result or infer a scientific identity by sorted order.
- Twelve-group raw positional entries remain 1 through 12 in native order,
  and all 198 raw pairs remain present. R's separately observed padded column
  tokens belong to root's association evidence; they cannot be recovered from
  the unpadded matrix ordinal fields. Explicitly supplied padded matrix tokens
  are retained exactly in the synthetic preservation test.
- Legacy `14*` remains token `14*`, coordinate 14 and `legacy_star` qualification.
  The trailing empty native column remains present with unknown identity.

Verification includes actual retained numerical values, exact original number
byte/line ranges, duplicate/extra/empty metadata rows, UTF-8 data, malformed
counts/p-values/df, exact large integer counts, underflow/overflow, ragged rows,
bad digests/layouts/encodings, unknown columns, raw-R quoted multiline data,
truncated wrappers and inert attempted code text. Original data row indexes
survive skipped malformed records. A missing final newline alone is accepted.
Saved JSON validation and supplied-byte parsing are checked with file, socket,
subprocess and/or native-reader calls forbidden. The focused pytest result is
recorded separately in TEST_RESULTS_001.json.

Skipped malformed fixed-width rows have their original data-row index in the
diagnostic path and exact artifact evidence reference. The full retained bytes
and original index locate that unreadable record. The frozen shape provides no
standalone SourceLocation object for an unparsed row; exact byte/line spans are
retained for every readable row and number. No diagnostic path invents a JSON
pointer containing encoded byte offsets.

Reproduce the retained-data/examples check from repository root:

```
.venv/bin/python verification/tool_graders_bvbrc_metacats_formats_2026-10-25/verify_and_save_001.py
.venv/bin/python -m pytest -q tests/test_bvbrc_metacats_formats.py tests/test_bvbrc_metacats_format_contracts.py
```

Remaining work includes original task/artifact/member/group association,
provider assembly and scientific calculators, invocation and production return
binding, complete episode communication tests, and live resource verification.
The provider must retain raw input bytes. Group labels, metadata ordinals and R
columns require separate source-backed associations. No ambiguous comma-joined
pair is split, no significance is calculated here, and no literature, W05,
evidence-axis, episode, controller or credit path is changed.
