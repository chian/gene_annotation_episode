# SAMstat native-output contract evidence

This workload completed the source/native-output contract, not the SAMstat grader implementation. All writes are under this 207 directory. No production or candidate code was changed, no embedded JavaScript was executed, and no live BV-BRC authentication or execution is claimed.

Read the consolidated [field contract](NATIVE_FIELDS_002.json), [parser/calculator ports](PARSER_CALCULATOR_PORTS_002.md), and [owned implementation workloads](WORKLOADS_002.md). The requested initial `NATIVE_FIELDS_001.json` and `PARSER_CALCULATOR_PORTS_001.md` remain intact. [Additive corrections](CONTRACT_CORRECTIONS_002.md) explain the precision and population refinements; revision002 is the coding handoff.

## Sources and actual caller

Official [SAMstat source](https://github.com/TimoLassmann/samstat) was pinned and built locally at:

| Producer | Source commit | Local executable version | Native output |
|---|---|---|---|
| 2.2.3 | `86e05e4870fe782defea40f0c854e4e110e2e6f7` | `SAMStat 2.2.3` | Literal arrays/objects in Plotly HTML |
| 2.5.0 | `e41808fb7ad34cc9b2c97c3eed60ad8e5eed50be` | `SAMStat 2.5.0` | Static SVG, textual summaries/tables/notes |

The 2.2.3 `tld` submodule is pinned at `0ebff385f781294be81b3986d053afb78256e332`. Both retained source worktrees have no tracked modifications. Source hashes, binary hashes, local dependency packages, successful and failed build attempts, commands and versions are retained in [SOURCE_RECEIPTS_001.json](SOURCE_RECEIPTS_001.json) and its manifests. The manifest covers 469 tracked source files. Local CMake/development dependencies were placed under this workload, not globally installed; legacy build-tool relocation is documented separately from the unchanged scientific source.

The complete retained FastqUtils `run_alignment` was read at caller tree `efb17b5c23448eb6e2c81b90fbefcd5a2898ac86`. It runs `samstat <prefix>.all.bam`, deletes that input, and retains an unmapped-filtered `.aligned.bam`. The latter cannot restore the original denominator. Inspected caller Makefile, requirements and README provide no SAMstat pin; external deployment make rules were not available. **BV-BRC's deployed SAMstat version remains unknown.** The upstream checkout does not identify it.

The complete relevant 204 native/metadata/sheet/calculation/projection/return/saved-codec paths and their concrete data shapes were inspected. Current 204 `samstat_html` is unsupported; its existing distinct-read mapping calculator requires actual sequence/alignment correspondence. The contract preserves that distinction. Root's later 208 compatibility status is recorded as a parent report, not independently certified here.

## Native execution and numerical findings

There are 40 tiny SAMstat input invocations, plus help/version/conversion process receipts and a separate source-executed caller-failure injection. They produced 37 native HTML reports. Inputs, reports, optional comparison JSON, stdout/stderr, run commands, timings and hashes remain in [native_examples_001](native_examples_001). All inputs are known synthetic examples, not biological measurements from BV-BRC users.

| Retained case | Native observation and implication |
|---|---|
| Same 12-record mixed SAM/BAM | Legacy contributes 11 records, excludes secondary and includes supplementary; current contributes 10 and excludes both. Both versions were run on SAM and converted BAM. |
| Mapping bins | Legacy R1 `[5,2,2,1]`, R2 `[0,1,0,0]`; current all `[4,3,2,1]`, R1 `[4,2,2,1]`, R2 `[0,1,0,0]`. Exact bins are ≥30,10–29,0–9,unmapped. MAPQ255 is merged into ≥30 by the producer and is not calibrated high-confidence evidence. |
| Candidate report-bin arithmetic | Legacy mapped10/11 and ge30 5/11; current mapped9/10 and ge30 4/10. These are fractions of contributing alignment records, not distinct reads, molecules or pairs. The future calculator is specified but not implemented or tested here. |
| Two Q0/Q40 bases | Legacy arithmetic mean20.000000, SEM14.142136; current error-probability mean3.0. Means/uncertainty are not interchangeable. |
| Mixed current quality | HTML MeanQ16.2; separately requested local JSON16.1541. The real caller does not request JSON; its extra precision must not replace the HTML value. |
| Legacy FASTQ quality | Native first-position mean37 for input Phred0/40 because pinned FASTX code leaves offset0 and caps indices41. Preserve native index values and known limitation; do not silently repair or claim valid decoded Phred. SAM/BAM's default quality path is distinct. |
| Legacy lengths4,8,8 | `y=[0.090324,0.169574]`: KDE estimates, not counts1/2. A single-length density spike1 is a native fallback. SAM/BAM legacy lengths exclude soft clips. |
| Legacy300-bp sequence | Position cluster `250-255` has A-value1, a rounded mean per clustered position; do not multiply a guessed width to recover base totals. Cluster labels are not ordinary closed intervals. |
| 1002 paired records | Legacy prints pair/proper-pair totals `1K` without exact values; overall total explicitly says exact1002 and table counts remain exact. Rounded display cardinalities are not exact operands. |
| 10001 current records | Main count `10.0 k`, exact sublabel `10,001`. Both display and exact token are retained with their distinct roles. |
| Current lengths10123/10987 | Median10.1kb, N5011.0kb, Bases21.1kb with exact21110. Do not recover exact individual lengths from rounded summaries. |
| Current clipping and identity | Five-record error example has clipped15.4% (=4/26 before rounding); three NM-tagged examples have native gap-compressed median identity80.0%. MD alone does not provide current identity. |
| Prefix limit10 | Legacy processes a full10000-record batch; current returns10. Both are prefixes, not random samples. |
| Malformed SAM after one valid record | Legacy exits0, writes a count1 report and emits an htslib parse warning; current exits1 with no report. Closed HTML/exit0 does not establish complete original-input consumption. |
| Empty input and missing fields | Legacy empty SAM has zero counts and `-nan` fractions. Legacy empty FASTQ exits0 with a native error in stdout and no HTML. Current empty input has an explicit no-reads report; absent SEQ is Bases n/a and absent QUAL omits MeanQ. These states remain distinct. |
| Caller failure | Exact exception block was executed locally with `/bin/false`; native code1 report says “segfault.” This proves caller stub shape, not an actual SAMstat segfault. |
| Current SVG | Per-position/distribution arrays are not embedded. Text retains counts and some extrema/notes. No numerical counts were reconstructed from geometry or chart ticks. |

[44 fixed-file native evidence checks passed](native_examples_001/NATIVE_EVIDENCE_CHECKS_003.json). The initial audit had a string-match failure because it expected a plain capitalized return-code label; the native HTML used `<b>return code:</b>`. That failed attempt and corrected additive audits are retained. These checks validate retained evidence facts; they do not test a production parser or calculator.

## Interface result

The field catalog defines 23 native field families with measurements, native inputs/formulas, units, populations/denominators, coordinates, precision, uncertainty and missingness. It preserves quality, mapping/mate and record/sequence distinctions, known producer limitations and absent references. It maps into the existing NativeDocument/Cell/Population/NativeSection/NativeLabel/RawBlock envelopes, with explicit finite enum additions rather than untyped metric sidecars.

The public reader signatures are `parse_samstat_html`, version-specific `parse_samstat_html_2_2_3` / `parse_samstat_html_2_5_0`, and `parse_samstat_bvbrc_error_html`, all taking supplied `raw: bytes` and keyword `context: dict` and returning a validated NativeDocument. The ordinary saved-sheet calculator `calculate_samstat_report_mapping` takes the sheet, a resolved job and parameter hash, returns two typed components, and never fetches inputs or executes tools.

The implementation workload divides leaf files for legacy parsing, current/failure parsing and arithmetic. Root owns shared schemas/enums, dispatch, selectors, original requested-form/saved compatibility, dependency manifests and actual path integration. Both the old 198 and current 208 saved generations must be preserved. No new evidence-axis or annotation-credit formula is proposed.

## Limits and unfinished implementation

Native versions/source are present and executed locally. Parsers and calculators are **not implemented or tested** by this workload. Live service version/execution and complete child-owned selected-artifact → provider → numerical sheet → original typed return integration remain unverified. Optional legacy end/relative missing-QUAL SAM behavior and a positive modern beyond-position-axis case were source-inspected but not natively exercised. No unobserved mode is claimed verified.

The source receipt recorded about 248.8 MB apparent retained scratch, below 4 GiB. Maximum reported build child RSS was 124640 KiB; native harness maximum child RSS 26744 KiB. The latter is a harness cumulative maximum, not independent per-process profiling. Native harnesses set a 20 GiB address-space limit and disabled core dumps. No wall-time cap, Aurora use or global installation was introduced.

The original authoritative goal and all 16 design principles were reread after substantial source/native study before contracts and again after the precision study. A final authority/contract reread is recorded separately in the final reset receipt. This task is a contract/evidence handoff; it does not mark the original inventory row complete.
