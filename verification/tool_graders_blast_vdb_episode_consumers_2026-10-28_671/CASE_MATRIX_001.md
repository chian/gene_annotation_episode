# Controlled consumer cases, 671

These tests use real configured consumers with explicitly controlled native
start/status and wrapper-output fixtures. They do not establish authentic VDB
native output, offline resource closure or a configured-model Workflow run.

| Cases | Count | Exercised boundary |
| --- | ---: | --- |
| Allowed operation/source/selection/filter bindings | 20 | Actual resource catalog, launch assignment, selected local child, common validator and exact binding schema |
| Changed software, variant, resource, kind, allocation, workspace or binding | 7 | Rejection before creating a native handle |
| Unsupported PBS/API binding | 2 | No substituted resource |
| Exact selector union | 1 | Only v1/v2 discriminators and closed branches |
| Selector against original operation | 1 | Wrong selector version, entry ordinal or resource rejected |
| Primary/supporting received input | 2 | Actual receipt required; wrong original bytes rejected |
| Status replay | 1 | Original attempt, no capture/acquisition, no completion, unchanged saved action |
| Entry/path-section result with native return 0/7 | 4 | Original practical reservation/receipt, capture, authentication worker, selected publication, typed immediate-child return, exact artifact grants, one bundle credit and immediate future zero |
| Forged attempt/owner/allocation/handoff | 4 | Original physical execution identity retained |
| Legacy base/full descriptors | 2 | Complete old key sets and extractor fields unchanged; mismatched new selector rejected |

There are 44 current 671 cases. The first bounded snapshot contained 41;
the follow-up added three cases and corrected only the catalog-selection test.
Twenty initial catalog fixtures incorrectly unpacked the entire resource catalog
as one utility row. The repair selects the exact operation name from that catalog;
its 20 cases pass in check128b. Production code did not change after check128.
All unchanged cases continue in their original check128; they are not restarted.

The full consumer tests call consumers directly and intentionally assert that
no runtime observations were synthesized by their internals. They do not assert
that a direct call creates a method_loop observation. The shared-loop Workflow
verification is separately owned by root. Existing practical receipts and same-key
result action bytes are preserved; original acquisition contributes exactly two
configured operational units once. Native failure can coexist with complete
requested qualified delivery. No scientific annotation score is introduced.

The old 630/632 regressions are selected in check128. The 651 regression file is
also selected there; its frozen descriptor cases require the two explicit 651
support files, which the initial invocation omitted. Root's independent check129
already exercised all 110 cases with those support files. Any actual failure
from the omitted support will remain in the original attempt record and be
reported without treating it as a production regression.

See the bounded attempts' final case reports and authoritative collection
receipts for actual outcomes. This matrix is not itself a passing-test claim.

Final outcome: all 44 current 671 cases passed across check128/check128b. The
five omitted-support legacy cases were rerun alone in check128c and passed.
`VERIFICATION_001.json` records all 228 distinct final passing cases and the
25 preserved original fixture failures. All three handles are terminal/quiescent.
