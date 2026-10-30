# HMMER FM pure numerical component — workload264

Implemented F1's fixed `makehmmerdb/build` and
`hmmerfm-exactmatch/locations|count_only` numerical workload. This is not
production-complete tool registration or episode integration.

Owned implementation:

- `gene_annotation_episode/hmmer_fm_data.py`: full supplied-ABI binary extraction,
  FASTA/query/location/count parsing, occurrence relationships, source-binding
  validation and explicit imported-index structural issues.
- `gene_annotation_episode/hmmer_fm_calculations.py`: separate deterministic
  numerical components, scoped checks, source/index correspondence, original
  ambiguity unions, native versus validated match populations and optional
  exhaustive literal comparison.
- `tests/test_hmmer_fm_data.py`, `tests/test_hmmer_fm_calculations.py`.
- This verification directory only. No runtime, library, accounting, other
  preparation component, or native source files were edited.

The three F1 function signatures and top-level fields are unchanged. Exact
nested fields, closed row/issue vocabularies, every numerical component's
meaning and explicit limits are in [FIELDS.md](FIELDS.md). Root owns capture,
dispatch, publication and typed episode returns. Producer267 requested specific
imported-index invariants in the existing extractor before its native call;
this additive consumer requirement is recorded in FIELDS.md.
Its concrete consumer is
`gene_annotation_episode/native_hmmer_preparation_driver.py::_preflight_exactmatch`,
which retains these typed issue codes in an `invalid_fm_database` preflight
failure. Workload264 inspected that complete consumer function; producer267
owns its execution-path verification and changes.

## Final verification

`check006/receipt.json`: 66 tests passed in 0.45 seconds; return code0.
`examples004/receipt.json`: all15 retained examples populated; return code0.
Both use the existing `local_jobs` adapter with `.venv/bin/python`,
`PYTHONDONTWRITEBYTECODE=1`, 20GiB RAM, 4GiB scratch and no wall limit.
Receipts record actual systemd/cgroup enforcement and source hashes. Older
check/example directories retain their actual earlier verification facts;
`check006` and `examples004` describe the final implementation.

Latest full saved sheets and calculations:
`examples004/examples/<case>_sheet.json` and `<case>_components.json`.
`examples004/examples/summary.json` provides all numerical summaries.
`examples004/examples/provenance.json` hashes every retained input/output,
native intent/receipt, relevant C source, current production module and F1.
No native example was regenerated in workload264.

| Retained case | Checkable numerical result |
| --- | --- |
| DNA paired index | 2source occurrences, 2segments, 28source symbols, 28indexed symbols, 1logical sentinel, 2BWT sections, 314bytes |
| DNA forward index | same28source symbols, 1BWT section, 226bytes |
| RNA index | 28source symbols, 339bytes; source U retained; explicit `rna_to_dna` gives exact symbol agreement |
| Amino writer index | 2source occurrences, 40symbols, 618bytes; full body decoded; downstream DNA-only reader incompatible |
| Ambiguous DNA index | 18source symbols, 2stored ranges, 6source ambiguity symbols, fraction6/18=1/3; generated index substitutions stay distinct |
| Forward locations | Q5/H15/R2; 15emitted, 15valid, 15expected |
| Forward count-only | Q5/H16/R2; 16raw FM interval occurrences; locations unmeasured |
| Default locations | Q5/H17/R2; 17emitted, 16valid, 1invalid; independently17expected, 1missing, 1extra |
| Default count-only | Q5/H19/R2; 19raw FM interval occurrences; locations unmeasured |
| Reversed-string queries | Q2/H7/R1; 7valid emitted versus9expected, 2missing |
| Forward-only index search | same15valid locations as forward traversal on paired index |
| Ambiguous-source locations | Q1/H3/R0; 3valid emitted; 3queries in neither Q nor R after native filtering |
| Ambiguous-source count-only | Q4/H6/R0; 6raw interval occurrences, including generated index matches |
| Zero locations | Q0/H0/R2; complete empty hit artifact, measured0locations |
| Native default output name `none` | 7valid reversed-string rows versus9expected; literal native file preserved |

The default native `TTTT r3 seq1` interval is [0,3] and is retained as invalid.
`TTTT r4 seq1` is valid. The independently expected `GGGG r12 seq1` is missing.
Equal emitted and expected totals17 therefore do not pass tuple agreement.
Both `ACGT` query occurrences remain distinct throughout. Native `r` reverses
the source string; no reverse complement is substituted.

Tests additionally cover partial headers/segments/counters, malicious counts,
wrong ABI and digest/size, missing versus empty files, duplicate names and
ambiguous query associations, CR/long/invalid queries, contradictory counts,
source mismatch, missing metadata, full-array corruption, unknown source
custody and JSON saved-sheet recalculation with file/network/subprocess calls
forbidden. Synthetic cases are explicitly identified: big-endian reserialization,
overlapping blocks, an exact65536 counter boundary, and imported-index mutation.
Native examples remain native observations of workload259, not new runs.

The structural decoder checks imported segment/range bounds and partitions,
paired sections, signed native indexing limits, every counter row against BWT,
complete LF cycle/text correspondence and all suffix-array samples. In-range
wrong counters/samples are rejected, not merely out-of-range values. Raw arrays
remain saved. Writer bin_length32 and SA spacing>10000 are explicitly separated
from native downstream reader compatibility using inspected source restrictions;
no native execution of those incompatible variants is claimed.

## Source and authority reset record

Read the entire original attached goal and all16 principles, repo AGENTS.md,
the complete F1 and M1 contracts, relevant fixed inventory rows and the tool
grader goal/principles document. Inspected full `makehmmerdb.c`,
`hmmerfm-exactmatch.c`, `fm_alphabet.c`, `fm_general.c`, the relevant complete
`fm_sse.c` counter/configuration functions and FM types in `hmmer.h`.
The retained input/output formats and native receipt identities came from
workload259; no new upstream claims replace the user's requirements.

Performed the required verbatim objective/all16 reset after substantive native
study, again after the imported-index consumer source study, and at closure,
followed by the exact F1 contract before handoff. The authoritative original
SHA256 is `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.

## Remaining limits and integration ownership

Only explicitly declared HMMER3.4 ABI and FASTA source input are supported.
Big endian, overlaps and exact counter-boundary cases have synthetic verification;
retained native verification uses small little-endian jobs. Large native
multiblock execution and actual big-endian native execution remain unverified.
The caller retains every original artifact byte; undecodable trailing byte
fragments remain there and do not become invented scalar/counter values.

Internal index invariants do not eliminate native reverse-boundary or post-free
diagnostic defects and are not a global process-safety assertion. Native
diagnostics do not become productive throughput or confidence. Literal validity,
index consistency and historical source custody remain separate.

No scientific observation, annotation confidence, timing credit, extra turn,
resource decision, acquisition, native invocation, Store or LLM exists in these
pure modules. Real selected child execution/capture/result dispatch and typed
episode communication still require root's integration work. This workload
neither claims those paths verified nor marks the fixed tool rows complete.
