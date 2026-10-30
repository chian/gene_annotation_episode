# Shared native-format workload handoff

Implemented in the assigned staging files only:

- `staging/gene_annotation_episode/phylogeny_formats.py`
- `staging/gene_annotation_episode/phylogeny_format_contracts.py`
- `staging/tests/test_phylogeny_formats.py`

The frozen five reader signatures and stored keys are unchanged. The contracts
module exports exactly `validate_tree_record(value: dict) -> dict` and
`validate_alignment_document(value: dict) -> dict`. It returns detached objects,
checks closed shapes and internal identities/topology/dimensions, and raises
stable `ValueError("phylogeny_<code>")` errors. It does not resolve custody or
read source artifacts. Reader diagnostics use the exact C4 shape and only
`native_decode` or `association` phases, from a finite module code registry.

The immutable goal was read in full before work. Its objective and all sixteen
design principles were reread verbatim after substantial native examination and
again at completion, followed by the frozen parser contract. Their verified
hashes are `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`
and `cedd264ad0db30176782ba35692c1889e4d4b612d34cd50fc9c3a8612ca925cb`.
The AGENTS instructions, permanent tool-grader direction, relevant progress
rows, implementation boundaries, full existing BLAST readers/pairwise grading
example and relevant native C4 reader/diagnostic paths were also inspected.
Existing behavior was treated as an example rather than authority over the goal.

## Actual verification

Run from the staging directory:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/chia/repos/gene_annotation_episode/verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24/staging /home/chia/repos/gene_annotation_episode/.venv/bin/python ../formats-verification/verify_formats.py
```

The final run passed **43 tests**, with zero failures/errors. The harness asserts
the exact `.venv/bin/python` executable and staged locations of both imported
modules. `VERIFICATION.json` records those paths, source-code hashes, eight full
native artifact hashes, numerical facts and results. `TEST_RESULTS.txt` records
the individual tests. `NATIVE_DOCUMENTS.json` retains their complete parsed
documents, which were saved as JSON, reloaded and validated. The harness's
explicit verification identities are not production C4 task custody.

All retained native files were read completely. The PHYLIP sequences were also
compared, character for character, with an independent literal block reader.
XML properties and confidence strings were compared with an independent XML
traversal, without using phylogeny-library defaults.

| Retained native result | Verified values |
| --- | --- |
| Historical CodonTree relaxed interleaved PHYLIP | 9 rows, 15,300 columns, 137,700 actual cells, 17,308 literal gap cells |
| RAxML partitions for that exact matrix | 4 partitions of 3,825 sites; no overlap or holes; three DNA model tokens and one LGF token retained |
| Best, supported and branch-label Newick | 9 tips and 16 nodes each; explicit root length retained; six native `100` labels/comments retained in their different fields |
| Bootstrap forest | All 100 trees retained in source order, 9 tips each; absent lengths remain null |
| First GeneTree phyloXML | 17 tips, 32 nodes, 31 explicit lengths, 14 generic confidence observations, 9 explicit confidence zeros, 72 properties |
| Second GeneTree phyloXML | 17 tips, 32 nodes, 31 explicit lengths, 14 generic confidence observations, 9 explicit confidence zeros, 119 properties |

The filename's `8taxa` is not used as a denominator. Each XML file has 17 product
properties. Its support method remains unknown; its native rooted marker does
not establish biological rooting.

The synthetic tests cover duplicate/empty/quoted labels, missing versus zero,
negative lengths, numeric overflow and underflow, source byte/line/XML positions,
comments and delimiters, multiple/deep trees, independent surviving records,
FASTA case/headers/encoding, all four PHYLIP layout/continuation combinations,
wrong repeated IDs, overlong/unequal/truncated matrices, explicit zero dimensions,
partitions with overlap/holes/bounds errors, invalid confidence tokens, XML
entities/CDATA/UTF-16/Latin-1 and unsupported encoding failures, DTD/external
entity rejection, and validators' nonmutation and relationship checks.
Filesystem, network and subprocess entry points are patched to fail during
pure-reader/validator calls in the test suite.

A separate seeded robustness sweep made **6,000** small mutations across the
five input formats. Every call returned JSON-compatible data and no uncaught
exception occurred. This is a robustness check, not proof of correct semantics
for every possible malformed input.

The calculator owner separately reported actual parser-to-calculator checks for
these same native formats: the same alignment and partition counts, six mapped
splits at 100/100, and best/supported unrooted RF 0. That workload owns its own
code and evidence; this handoff does not claim an episode integration test.

## Parsing behavior and explicit limitations

All five readers consume supplied bytes and the caller's ArtifactRef, check its
SHA-256 against those bytes, and copy its identity into source locations. They
make no filesystem/network/executable/model call, choose no resource and create
no artifact custody identity. All complete source bytes remain with the caller;
the parsed document is not a substitute for retaining the artifact.

Newick is decoded as UTF-8. Standard single quotes use doubled-quote escaping;
the explicit BV-BRC double-quote dialect also uses doubled-quote escaping.
Bracket comments, including nested brackets, retain their literal tokens and
positions. RAxML comment-based labels remain comments. Numeric internal labels
remain labels. An unclosed quote/comment cannot be used to guess later tree
boundaries; the unresolved tail is incomplete. Independent semicolon-delimited
valid records survive other malformed complete records when multiple trees are
explicitly allowed. Syntax does not infer a support method or biological root.

FASTA IDs use the requested first whitespace token; the whole header remains
stored. ASCII and UTF-8 are explicit choices. Horizontal sequence whitespace is
treated as formatting with a qualification, while the native bytes preserve it.
Sequence case and actual non-whitespace symbols are retained. PHYLIP is ASCII,
with full whitespace-delimited identifiers and explicit sequential/interleaved
layout and absent/repeated continuation-ID policy. No ten-character truncation
or quoted whitespace-containing PHYLIP identifiers are implemented. With absent
continuation IDs, a sequence group that happens to match a label stays sequence
data; the reader does not guess an ID. Repeated IDs must match that source row.

Neither matrix reader pads or silently truncates rows. In incomplete PHYLIP,
`observed_row_count` counts actual retained rows reaching the declared column
length, while `rows` also retains partial rows. FASTA counts actual header
records; unequal or erroneous matrices have a null observed column count and
non-complete state. Valid explicit zero-column rows and PHYLIP `0 0` are distinct
from empty bytes. The readers check supplied syntax; they cannot establish
transport completion from EOF alone. One PHYLIP artifact represents one matrix.

Partition normalized columns are sorted unique zero-based sets. Native range
order remains available. Duplicate membership, including within one partition,
is counted when diagnosing overlap. Out-of-bounds positions are retained without
clipping to the caller-supplied actual alignment denominator. The parser does
not assign alphabets from model names or reconstruct family/residue maps.

phyloXML accepts the standard namespace or absent namespace; DTDs and all
declared entities are rejected. It uses actual elements/attributes, with no
default zero lengths. XML character references and CDATA remain visible in raw
numeric tokens; decoded finite numeric values are stored separately. Invalid
numeric/scalar confidence retains its raw token and a null value. Complete
independent phylogenies can survive later malformed/truncated XML. Duplicate
branch-length representations are rejected as ambiguous instead of choosing one.

The frozen XML keys cannot represent every XML field. In particular,
phylogeny-level name/ID/confidence fields outside the root clade, unrepresented
attributes such as an ID provider, and arbitrary unrecognized content remain
in the complete caller-retained XML with explicit qualifications. They are not
claimed to be decoded into the stored sheet. Actual clade/sequence/taxonomy
names and ID elements, accessions, confidences, and every encountered phyloXML
property in the admitted scope remain separate arrays. Comma-flattened property
values remain intact; no entity list or identity join is inferred. Root confirmed
that the frozen keys should remain unchanged for this limitation. Provider
extraction must preserve it and must not infer biological rooting from XML.

Current CodonTree mixed FASTA, GeneTree relaxed sequential PHYLIP, and BV-BRC
double-quoted names have synthetic syntax tests here; this workload has not
acquired new current-service examples for them. The retained files are official
repository examples, not newly submitted jobs. No service installation,
authentication, live execution, actual task-to-artifact custody, production
result-path binding, or selected-tool/episode typed return was verified here.
No evidence-axis, W05, annotation-score, runtime, credit, prompt, controller or
episode implementation was changed. Production integration remains root-owned.
