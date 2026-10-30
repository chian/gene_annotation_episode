# Rfam API contract planning packet

Scope: fixed row **A-L068-rfam-batch**, remote API scanning only. Proposed interfaces and evidence; no implementation completion or row-status change.

- [CONTRACT.md](CONTRACT.md): selected primitives, exact request/parser/sheet/calculator/return types, missingness and failure semantics, consuming functions, exclusive coding ownership and legacy-loop boundary.
- [SOURCE_AUDIT.md](SOURCE_AUDIT.md): primary sources, actual current HTTP absence responses, complete local path/test inspection and its limits.
- [examples/EXPECTED.md](examples/EXPECTED.md): native-source, empty, partial, duplicate, contradictory, unsupported and still-needed batch/correspondence verification cases.
- [Populated proposed sheet](examples/proposed-single-sheet.json) and [calculation](examples/proposed-single-calculation.json): actual numerical values from the official source example with unknowns explicit. These are expected outputs, not executed production grader results.
- [Fixture manifest](examples/fixture-manifest.json), [source manifest](source_evidence/source-manifest.json), [old-job GET manifest](source_evidence/old-job-get-manifest.json), and [example verification](example-verification.json): provenance and bounded verification.

The original objective and all 16 original principles were read in full, then reread after substantial study and at closure. Only files in this directory were written. No production/shared test changes, historical fixture restoration, or new remote job submission occurred.

Single-query JSON native score/E/GC and query-coverage implementation can proceed independently of the required richer display and multi-query format work. The exact multi-result schema and deployed tblout/out formats remain unestablished; byte-preserving `submit_file` enables the next explicitly selected tiny batch characterization. Single-only support cannot complete the fixed row.
