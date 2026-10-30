# Final joined snapshot after G1 updates

Additive verification record, 2026-10-27. `REPORT_001.md` and all earlier attempt
receipts remain historical facts. This record qualifies the newer executed
sources and supersedes only the final-source status of the earlier report.

After check002, G1 strengthened supplied canonical-file identity and located-row
validation, adopted root's supplied invocation clarification in packet422
`NATIVE_METADATA_CLARIFICATIONS_003.md`, and replaced repeated occurrence/edge
scans with ordered adjacency lists. Projection's exact occurrence-to-edge join
validation was also changed to ordered adjacency lookup, preserving the same
recorded associations without repeating interval calculations. Complete original
G1 paths and their full subsequent changes were inspected before the joined run.

After G1's final-ready signal, `check003` took a fresh read-only source snapshot
and ran all **41 projection tests**, including the actual G1 supplied reader,
reference extractor, sheet builder and calculator feeding the projection.
All passed in 1.03 s pytest duration. Return code was 0; executed before/after
pins were identical and checkout source drift during the run was empty.
The Jaccard-only return again matched the packet418 requested return exactly:
numerator 5, denominator 15, value 0.3333333333333333, complete extent, unknown
reference relation, with no unrequested measurement fields.

| Final executed source | SHA-256 |
| --- | --- |
| `genomic_overlap_result_views.py` | `a9422dd9acd70355d1cb4e0ae5a9f773eee7a0c030eaf7cb00515b96f68b8df8` |
| `test_genomic_overlap_result_views.py` | `600d85e0e85014ab90702e0c2aa18dcfe8c2a2e35e491ea953eaa9351f9d2088` |
| G1 `genomic_overlap_contracts.py` | `1bde770d3360feb38d2d3c77a5ab8c44f2c810cd86dbbf9cf15d0b658d4a906e` |
| G1 `genomic_overlap_inputs.py` | `f84562475133ac699a1f82d42d4693a9f50a3ce16ea4f457a5e56ce643b6ee23` |
| G1 `genomic_overlap_calculations.py` | `1c7c4f4bd08323eb1903ac94774ca7d7d6d6829cc4ab6a4744fd96a4d0de9e84` |

Check003 used the same protected `local_jobs` path: 20 GiB RAM, 4 GiB scratch,
zero swap and no wall allocation. Its receipt verifies memory max 21474836480,
swap max 0, runtime max infinity, service success, and 22056960 observed scratch
bytes. Scratch remains monitored with possible overshoot; this does not claim
a filesystem sandbox. All three attempts and source snapshots are retained.

The final immutable objective and all sixteen principles were reread verbatim,
then the accepted root contract and projection clarifications were reread before
handoff. This remains a pure projection implementation with supplied-data
verification. Production native/result binding, original-action custody, live
resource execution and complete episode communication are not established by
these tests; their owners and unfinished status remain unchanged.
