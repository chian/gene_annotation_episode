# Conflicting assignment keys retain independent valid results

This adds to VERIFICATION_001; it does not replace the earlier defect, repair,
source identities or97-pass receipt.345 found the new case during actual wire
population. Root reproduced both a nonexistent destination feature and a
different real feature before changing production code: probe_run_002 reports
two failures at the global assignment-key uniqueness check, with unchanged
production source during that run.

Population already retained both conflicting declarations and marked their
shared link incompatible. Saved validation rejected the entire populated sheet
because it required the key to identify one declaration globally. It now checks
the key together with the observation's exact entity address and requires one
declaration at that address. Every conflicting declaration remains in the
shared link. Multiple conflicting declarations at the same address still cannot
produce an input-order winner. Required-observation validation uses the same
address relation, so an incompatible observation cannot simply disappear.

run_002 passed103 checks in1.68s: the original81 input checks and22 saved-relation
checks, including six new cases. Source hashes before/after are identical.
The existing local_jobs wrapper enforced20GiB RAM and4GiB scratch with no wall
cap. Tests preserve the independent B feature's exact original observation,
reject removal or false available status, and forbid native parsing, population
and base calculation while validating a saved sheet. The three frozen complete
fixtures remain unchanged.

Installed input source SHA256:
78e0491b2d52cfed4bc013b04f2f3487fb86a65691dd3b10a4c97541f6d71b84.
New test source SHA256:
8384f69c692a1e3922f9cf564fb9e2f3f6c3522b679c9717b534180a00cf6835.
The original input-test SHA256 remains
8c09ffb44e62e6e5d6293c73ca4c48403739e999436a125a2df6bf7129eaf463.

344,345 and347 were informed of the exact changed dependency.345 separately
reported that its formerly failing wire case passes against this repair; that
wire verification remains in345's own receipts. No formula, schema, v1 numerical
result, resource choice, annotation credit or completed history was changed.
This component repair does not add either VDB tool to the grader count.
