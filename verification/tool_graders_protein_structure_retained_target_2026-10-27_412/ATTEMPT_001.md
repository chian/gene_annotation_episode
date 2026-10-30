# Superseded bounded attempt,check001

check001 ran the first18-case test snapshot. The operator explicitly sent SIGINT
to its pytest process after the corrected full check002 had started. This was
management of a superseded verification attempt, not an episode action or a
deployed timeout/cancellation rule. Its retained pytest summary is13 passed,
2 failed,1127.87s; three cases had not completed. The native wrapper reports
returncode2 and1128.591893981s of service wall time.

Both failures were test defects: the scope case attempted a second problem in
the same Store and failed with problem_already_exists before reaching scope
validation; the workspace case expected path_outside_assigned_workspace instead
of the existing practical_write_outside_workspace. The next snapshot uses an
actual narrower interval and the existing workspace error. Production source
was not changed to make either expectation pass.

The completed cases include actual shared saved commissioning/acquisition,
metadata description, original exact replay, pending/sibling denial, changed
original-assignment denial, exact saved-descriptor/handoff failures, configured
resource/operation/mode/software checks and missing-sheet selected-use/history
preservation. This first fixture also admitted the later saved result through
397 before subsequent tests. The final fixture keeps the required original
saved-descriptor admission; it does not add that second return before every
subsequent failure case. Packet410 owns complete Workflow return verification.

All executed source pins stayed unchanged. Checkout drift was limited to the
root-owned runtime.py and412's test corrections/added assertions. The receipt
records20GiB RAM and4GiB scratch limits, zero swap, no wall-time budget, and
41,893,888 observed scratch bytes. These are distinct from measured duration.

The stdout/stderr, selected request, lifecycle controls, fixture Store, all
result controls, read-only source snapshot and before/after pins remain under
check001. Its partial result is not a full-suite pass and must not be added to
check002 as independent test coverage.
