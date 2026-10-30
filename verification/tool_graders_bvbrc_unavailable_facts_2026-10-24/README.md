This records only additive BV-BRC unavailable-return correction 003. The original
planning artifacts and the previous D2/native-data verification remain unchanged.
Their 502 tests and 26 offline checks are historical evidence, not rerun counts.

Page fact row counts now allow null and require the existing nullable closed
unavailable reason. Facet bucket references allow null with the same namespace.
The identical corrections appear in ReceiverMaterialization's fact union. No
other exported interface, scoring sheet or closed-schema rule changed.

The focused schema suite passed 135 tests. The combined schema, D1–D5 and
existing communication suite passed 651 tests in 14.63 seconds. D5 owner079
confirmed the 85-test D5 suite was stable before the combined run. The complete
combined output is in PYTEST_MODULES.txt; exact commands and source hashes are
in REPORT.json and SOURCE_SHA256.json.

Run the offline fixture and historical-artifact checks with:

```sh
.venv/bin/python verification/tool_graders_bvbrc_unavailable_facts_2026-10-24/verify.py
```

Eight explicitly synthetic examples preserve populated/zero/partial/no-sheet
pages, an acquired null-term bucket, a query-level unavailable facet, a successful
empty facet array and an acquired invalid bucket. Each is checked as both an
ordinary closed form and an embedded receiver materialization. The no-sheet
page has null counts; the genuine missing-term bucket keeps count 0 and its
actual fixture bucket reference. The unavailable facet has no bucket reference.

These checks establish shapes and closed-boundary compatibility. The generic
schema does not establish source custody, parse-failure provenance or cross-field
scientific relationships; D5 and root-owned consumers retain those duties. No
network, live execution, jobs, model calls, prompt changes or endpoint-completion
claim occurred in this task. No unavailable row establishes endpoint completion.
