# SAMStat2.2.3 legacy parser delivery

Implemented public function:

`parse_samstat_html_2_2_3(raw: bytes, *, context: dict) -> dict`

Owned candidate files, under
`verification/tool_graders_fastqutils_samstat_implementation_2026-10-25_212/candidate`:

- `gene_annotation_episode/bvbrc_fastqutils_samstat_legacy.py`
- `tests/test_bvbrc_fastqutils_samstat_legacy.py`
- `tests/fixtures/bvbrc_fastqutils_samstat_legacy/` —20 native HTML fixtures.

Only these candidate files and213 evidence/scripts were written. Shared enums,
current parser, calculators, production files and other workers' evidence were
not edited. No processes belonging to202 were stopped.

The pure parser checks supplied content binding and uses an inert HTML tokenizer
plus finite literal lexer. It never executes JavaScript, uses eval/exec/
literal_eval, loads Plotly, invokes a subprocess, acquires source bytes, reads
input files or calls an LLM. It returns the existing validated NativeDocument,
preserving source byte locators, actual tokens, native arrays and all associations.
Duplicate assignments/mutations, array cardinality, references, native labels,
group legends, applicable axes, counts and versions are checked. Independent
valid blocks survive malformed siblings. Unsupported versions remain unknown
actual format with typed requirements and retained version claims.

All37 legacy native metrics have populated examples: alignment bin/total counts,
FASTX sequence counts, native mapping fractions, paired/proper-pair display counts
and percentages, length density, five base counts plus five clustered means,
SAM mean/SEM and FASTX index mean/SEM, five mismatch counts plus their five
clustered means, insertion/deletion opening counts and clustered means.

Checked numerical examples:

- Mixed SAM and BAM: R1 bins5,2,2,1; R2 bins0,1,0,0; separate report total11
  and mate totals10/1. Supplementary contribution and MAPQ255 remain retained.
- Empty SAM: four observed zeros; five native `-nan` fraction cells are undefined,
  preserving tokens and zero-denominator/nonfinite qualifications.
- Paired1002: exact report total1002; paired/proper display `1K` stores1000 with
  native-rounded precision. The rounded display never becomes an exact count.
- SAM Q0/Q40: native mean20 and SEM14.142136. Default missing QUAL has no quality
  series. FASTX native index means37,41,41,41,41 retain the offset defect.
- Lengths4,8,8: native density0.090324/0.169574, inverse-bp units. Single-length
  fallback1 stays explicitly qualified.
- Native end/relative coordinates and clustered textual labels remain distinct;
  all seven clustered-error metrics and all seven unclustered error metrics have
  separately checked examples. Two-base gaps yield one opening each.
- Requested prefix10 produced native10000. Prefix populations are partial while
  complete literal observations are available. A closed first-record report from
  malformed input leaves original-input completeness unknown.

Final focused test:57 passed in16.06s, `PYTEST_ATTEMPT_007.log`. Twenty native
reports yield6547 populated cells across all37 legacy metric names. Every native
y/error-array token, axis label and row index is compared with the original
bytes. Negative checks cover duplicates, mutations, mismatched arrays/headers/
legends, unknown groups, truncation, nonfinite fractions, malicious script text,
UTF-8 offsets, wrong versions, invalid contexts and failed content binding.
Offline JSON round-trip retains the complete document, and parsing with filesystem
reads/network/subprocess disabled is tested.

`IMPLEMENTATION_HANDOFF_002.json` contains exact owned-file hashes, every native
fixture hash, per-document metric counts and the exact integration ports.
`parsed_native_002/` retains all20 complete parsed documents. Additional native
receipts and the producer-defect clarification are additive. All original failures
remain in place.

For the root calculator, mode is established by NativeLabel
`kind=native_label`, `value=Mapping statistics`, section `samstat_summary` ordinal0.
FASTX has `File statistics` and sequence populations. Alignment populations are
`samstat_report_records` ordinals1/2 with mutual `disjoint_from_refs`; conditional
report-wide ordinal0 is their parent and is never disjoint. Generic declared
format is retained; actual format/version are2.2.3 only after recognition.

This delivery proves the leaf parser and retained/local native examples.
Production installation, the full child-owned selected Workspace/provider/sheet/
calculator/requested-return path, saved-package dependency closure, and live
BV-BRC deployment/version were not verified by this workload. They remain the
integration owner's work. No calculator, new score or annotation-credit change
was introduced here.
