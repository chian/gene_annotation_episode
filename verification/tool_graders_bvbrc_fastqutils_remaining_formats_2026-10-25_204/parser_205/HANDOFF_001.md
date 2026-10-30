# Embedded Cutadapt parser handoff

Owned candidate files:

| File | SHA256 | Bytes |
| --- | --- | ---: |
| `gene_annotation_episode/bvbrc_fastqutils_cutadapt_reader.py` | `1237535586dfc9f08510586901f09f01d78c6064fb0da78f8e736fea679da882` | 38393 |
| `tests/test_bvbrc_fastqutils_cutadapt_reader.py` | `bf75b0a89543006afc3fe2edb854f77ff8e777ba4caf810dc7768f0d845dbd47` | 30961 |

The parser implements `append_cutadapt_report(report, raw, *, start, end)`.
It checks the complete artifact binding and byte boundaries, appends native
rows, retains the stable `cutadapt_embedded` raw-block name, and does not call
outer `finish` or alter the outer producer/version. It makes no acquisition,
program, model or calculator call. Root owns common contracts, dispatch,
packaging, source closure and integration.

The final focused suite passed **77 tests in 7.38 seconds**. `test_result_001.json`
records the exact command and final file hashes. The retained 31 producer
cases comprise four supplied Cutadapt runs, one supplied genuine Trim Galore
run, and 26 additional actual Cutadapt runs on explicit synthetic inputs.
The three `native_examples_*/receipt.json` files retain exact argv, full native
stdout/stderr/JSON/FASTQ hashes, exit status, resource limits and timing.
All new native runs exited zero. They used the private verified Cutadapt 4.9
environment, 20 GiB address-space limit, 4 GiB scratch budget and no wall limit.

Filled native documents for every case and three saved sheets/components are
bound by `evidence_002/manifest.json`. See `PROVENANCE_CORRECTION_001.md` for the
additive correction of the earlier direct-helper fixture labels; historical
`evidence_001` was not rewritten. Bare Cutadapt bytes are direct helper tests,
truthfully labelled Cutadapt/native text, and are not a standalone dispatch claim.

Numerical examples:

| Case | Actual native quantities | Separate saved-sheet result |
| --- | --- | --- |
| Single | 4 reads, 58 bases in; 4 reads, 28 bases out; 4 quality-removed bases; 2 adapter-containing reads | Base retention 28/58; 30 removed bases |
| Filtered | 4 reads, 58 bases in; 3 reads, 24 bases out | Base retention 24/58; 34 removed bases |
| Paired | 4 pairs, 116 bases in; 4 pairs, 56 bases out; 58/28 bases per mate | Four artifact-local count/base lineage edges |
| Genuine Trim Galore | Embedded Cutadapt output 4 reads/28 bases; final FASTQ 3 reads/24 bases | No invented edge equating these populations |
| Repeated adapter | 2 reads, 5 adapter events | Events remain events |
| Indel | Removed length 9; nominal max.err 0; one observation in error bin 1 | Both native coordinates retained |
| Empty input | Text prints only `No reads processed!` | One input-count zero; no borrowed JSON counters |
| Zero bases | 2 reads, 0 bases in and out | Base fraction undefined; removed count exactly 0 |

Native oracle tests exercise all 23 added metric fields, single and paired
reports, all specified adapter types, repeated names/events, quality/poly-A,
empty endpoint tables, positive filters, adjacent-base warnings and trailing
global warnings. Mutation tests separately verify malformed/partial rows,
missing/wrong versions, conflicting modes/percentages, duplicate summaries,
original UTF-8/CRLF offsets, repeated invocations, unknown sections, full-byte
binding and retained valid siblings. Saved-sheet tests disable native parsing,
network and subprocess calls while checking exact retention and zero-denominator
behavior.

Native named `discarded as trimmed` and `discarded as untrimmed` counters remain
a qualified branch: the actual corresponding option runs omit these counters
from both text and JSON. Their source-defined printed forms are tested with
clearly handcrafted read and pair fixtures; no counters were inferred from
those actual omitted fields.

Inspected complete relevant paths: Cutadapt `report.py` and CLI header/full-report
selection; `_Report`; native contracts/schema fields; Trim Galore outer reader;
native dispatch; metadata/sheet population; calculation resolution, retention
and calculator dispatch; projection/provider; and saved episode-return consumers.
Retained Cutadapt source hashes are in the evidence manifest. The installed
`report.py` matches the retained source SHA256
`3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d`.

No production files or frozen 198 files were edited. Other Cutadapt versions,
deployed BV-BRC artifact/version verification, remote authentication, and full
episode-path completion are not claimed by this parser handoff. SAMstat and SRA
metadata are outside this workload. No known parser-port shape blocker remains.
