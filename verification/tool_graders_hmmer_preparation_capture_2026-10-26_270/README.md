# HMMER preparation original-output capture — 270/C1

This component authenticates and retains the files of one original selected
HMMER preparation attempt. It neither selects work nor calculates scientific
scores. The ten programs and26 modes retain their original request, producer
ABI, input/private-copy/output roles, per-role ordinals and complete bytes.
Same-byte aliased outputs remain separate occurrences. Empty, partial, missing
and malformed files retain different meanings.

Implemented ports are is_native_hmmer_preparation_target,
validate_original_bundle, capture_local_bundle, original_source_payload and
publish_original_source in native_hmmer_preparation_acquisition.py. Pure bundle
validation does not read today's execution host. Initial capture reads only the
original reservation and declared files; replay checks retained custody and
the original receipt without reopening native work or reacquiring output.

## Verification

All verification used local_jobs with20GiB RAM,4GiB scratch and no wall cap.
check003 passed74 capture checks against final267 retained producer cases.
check005 passed149 checks: the capture suite, current request/compiler checks
and fresh executions of all four hmmsim algorithms. The final source hashes
were unchanged during check005. check004 had a relative pytest-path mistake
and exited4 before collecting tests; it remains retained, not counted as a
successful run. Earlier capture receipts remain unchanged.

Tests establish exact original operation and ABI validation, all26 mode
populations, role/byte associations, declared-path confinement, supplied-target
identity, valid partial preservation, actual nonzero native prefixes and capture
replay. A query-line ordinal is distinguished from its input-artifact ordinal.
Retained native outputs are used with explicitly synthetic relocated custody
where stated; a separate actual native reservation/capture path is also tested.

## Recorded simulation-settings correction

P1 had omitted unselected --fast and --tlinear fields from resolved hmmsim
settings. Native HMMER3.4 source declares both false. The compiler now records
those false values; native argv is unchanged. The original requested parameters
remain separate. The compatibility comparison accepts only this exact historical
omission, never a missing selected-true flag, integer false substitute, changed
native option or altered operation. Old bundles and saved sheets are not edited
and their missing-setting qualifications are retained.

The correction is recorded additively in261/SIMULATION_SETTINGS_HANDOFF_001.md.
The four new native cases are in check005/temporary. Producer267/check005's225
tests and77 native cases describe the earlier producer checkpoint, not a claim
that all225 were rerun after this correction.

## Limits

Complete capture means complete byte custody, not successful native execution,
decoded model content or biological support. C1 does not establish library
registration, numerical grading, typed returns or full shared episode execution.
Those have separate271–278 evidence. Unsupported numerical formats remain
explicit in their corresponding parsers. No API/HPC deployment is claimed.
The full308-row goal and permanent designs remain unchanged.
