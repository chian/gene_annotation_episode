# First bounded routing run and two assertion corrections

The coordinator ran the independent routing selectors plus its two actual
native-producer cases in
`verification/tool_graders_hmmer_map_verification_2026-10-28_529/check024_fluorescence_routing_native`.
Its JUnit record contains 33 cases: 30 passed, 3 failed, 0 errors, 0 skipped.
The two native-producer cases passed; their separate runtime evidence is owned
by the coordinator. This does not establish the pending tool library or full
Workflow/receiver rendering.

The three failures were two test assertions, not production changes:

- The context tampering case runs after the original form is frozen. Actual
  FluorescenceReturns._frozen rejects it as
  `fluorescence_return_frozen_facts_conflict`, before the later non-frozen
  equality check. The test now requires that exact error.
- Both retained-target modes compared returned validated plain JSON to an
  immutable BindingContext assignment whose arrays are tuples. BindingContext
  intentionally freezes arrays and objects. The test now compares to
  `plain(child.assignment)`, retaining exact values and order.

The complete _frozen/validate_received_report and BindingContext implementation
paths were reread before correction. No production validator was weakened.
Source, binary, dependency, stdlib, native-library and original-fixture before
and after pin records in check024 were compared with stdlib JSON and are equal.

Test SHA256 after the two corrections:
`d809ead963f53e8dc210fabe2ff2298cf6838d962a0562ac9dba146a03d07e86`.
Production hashes remain those in SOURCE_AUDIT_001.json. AST parsing passed.
No host application import or test execution occurred.

Requested follow-up selectors (3 parameterized cases total):

```text
tests/test_fluorescence_episode_routing.py::test_requested_context_follows_only_selected_numerical_page
tests/test_fluorescence_episode_routing.py::test_retained_target_precedes_missing_current_binding_and_native_bytes
```

Earlier successful cases and native jobs need no repeated run for these
assertion-only corrections. Follow-up outcome is recorded separately.
