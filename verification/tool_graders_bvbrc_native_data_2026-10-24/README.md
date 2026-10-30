D2 provides pure BV-BRC Data shape validation, native readers and numerical
calculators. It does not establish a service binding, host admission or episode
delivery. The original authoritative goal and frozen contract remain unchanged;
the explicit correction002 supplies the source-locator, invalid-array and JSON
digest clarifications.

Reproduce the native numerical checks with:

```sh
python3 verification/tool_graders_bvbrc_native_data_2026-10-24/verify.py
python3 -m pytest -q tests/test_bvbrc_data_schema.py tests/test_bvbrc_data_readers.py tests/test_bvbrc_data_calculators.py
```

`REPORT.json` records exact exports, signatures, native-byte hashes, source/test
hashes, commands and limitations. `PYTEST.txt` records the broader D1–D4 test
output. `FILLED_RESULTS.json` retains complete parsed examples and separately
calculated values, with the origin of each fixture stated.

The retained native count response has zero documents and reports two matching
documents. The facet response has numerators 1, 1 and 0 for the native PATRIC,
RefSeq and missing buckets, with exact denominator 2. The separately calculated
fractions are 0.5, 0.5 and 0.0. The two feature IDs retain four AA/NA relations
and one distinct sequence of each kind, with four native length agreements.
Genome measurements include length 4,639,675, native GC value 50.8 with unknown
denominator, and reported plasmid count zero. Native expression values retain
log2_fc −0.132/−0.129 and z_score −0.544/−0.556, with absent measurements left
unavailable. The native PPI scalar 7.9219284 remains an observed schema exception
with unknown scale. Protein feature E-value text `1.25E-9` remains retained beside
its numerical projection 1.25e−9.

The retained array responses use the private explicitly selected native decoder
and remain unqualified for v2. The complete v2 parser comparisons around retained
Solr bytes use synthetic transport bindings, labeled as such. They are not live
v2 invocations. The older genome capture did not record body completeness; HTTP
200 alone does not fill that missing fact.

Page components count every retained native row, including invalid rows, and
report native query population separately. Facet fractions divide each bucket
document count by the same successful exact Solr response numFound. Missing,
inexact, conflicting, partial and zero denominators remain unavailable. Buckets
can overlap; the calculator never divides by their sum. Feature components count
selected feature IDs, distinct selected feature-row occurrences, every explicit
sequence-page row, joined/repeated-identical edges, distinct joined hashes per
kind, exact missing-key/missing-record statuses, conflict/type-mismatch statuses,
and true length agreements on joined edges. Other missing states remain in the
full edge sheet. No component is an annotation confidence score.

Tests preserve original numeric tokens and distinguish absent, null, unselected,
zero, incompatible, invalid and unrepresentable values. They reject duplicate
JSON keys, non-JSON numbers and boolean-as-number; malformed fields retain valid
independent rows. Invalid nested-array values remain at exact raw-byte paths,
with invalid projection and no fabricated atoms. Saved-sheet recalculation is
verified with network and subprocess entry points patched to fail.

The shared `schema` module validates finite plain JSON and closed types. D2 owns
native row/cell/population consistency; D3/D4 own sequence and molecular joins;
D5/D6 own requested projections, qualified source custody and actual episode
communication. This verification did not call a live service, submit a job,
invoke an LLM or change W05/literature work.
