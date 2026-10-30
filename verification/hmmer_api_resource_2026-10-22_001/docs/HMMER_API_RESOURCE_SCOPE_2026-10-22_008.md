# Status/result prerequisites before a remote handle exists

P identified the same concrete distinction in selected status/result operations:
an original order can be known not to have been sent, which is different from
an ambiguous actual submission. This new clarification extends only P's
remote-id-missing preflight branch; no public port or schema changes.

For a valid original order with state not_submitted and no submission claim,
status_once/result_once return their own failed operation receipt with
code prerequisite_missing, native_code submission_claim_unavailable,
phase status/result respectively, submission_outcome null, prerequisite null,
the actual job in affected_refs, and the other existing nullable failure fields.
No HTTP or status fabrication occurs.

For state not_submitted after the latest original selected submit has an actual
receipt explicitly recording submission_outcome not_sent, the same failed
status/result shape uses native_code submission_not_sent. It does not relabel
that known not-sent attempt as uncertain. The original submit receipt and its
own failure remain unchanged and addressable. Claim existence alone does not
prove send, rejection, active execution or uncertainty.

An actual selected claim with no usable response/handle and no explicit
not_sent receipt remains submission_uncertain. These preflight conditions
authorize no retry, replacement, timer or new submission. A separate selected
initial submit or explicit not_sent repair continues through the unchanged
claim/retry port. No completed local observation or monitoring snapshot is
created for failed status/result work.

P tests both status and result against no claim, explicit not_sent and actual
ambiguous claim boundaries, preserving earlier verified inputs/logs. Root/C
consume the unchanged failed-receipt contract. All work stays isolated.
