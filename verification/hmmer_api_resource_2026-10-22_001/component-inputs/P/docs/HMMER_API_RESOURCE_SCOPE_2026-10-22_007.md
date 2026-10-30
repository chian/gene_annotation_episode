# Explicit in-progress and absent-submission failure meanings

This new clarification follows scopes001–006 without replacing them. It fixes
two concrete cases found while exercising actual ports, with no numeric or
scientific interpretation change.

`ProviderOperationInProgress` carries the existing actual `job_ref` and selected
`operation_key`. It has no terminal operation receipt. MonitorEpisodes catches
this exception before the generic ContractError branch and returns exactly:

```json
{
  "status": "failed",
  "record_refs": [],
  "changed_record_refs": [],
  "progress_refs": [],
  "feedback": {
    "category": "provider_failure",
    "code": "submission_in_progress",
    "detail": {"job_ref": "<actual job>", "operation_key": "<actual selected key>"}
  }
}
```

The code is the existing public exception's machine code even when the selected
operation is status/result. No receipt reference, progress snapshot or completed
controller observation is invented. A local delayed-status contention case must
exercise this actual exception through the monitor consumer. P's existing
one-request worker remains responsible for its original capture and lock.

`recover_submission` on a valid ordered job with no original submission claim
has no selected attempt to recover. Its failed recovery receipt therefore uses
`code=prerequisite_missing`, `native_code=submission_claim_unavailable`,
`phase=recovery`, `submission_outcome=null`, `prerequisite=null`, actual job in
affected_refs, and the remaining existing nullable failure fields. It retains
authoritative not_submitted state and performs no POST. This does not grant
retry permission. A later separately selected initial submit can create the
first claim through its unchanged port. If an actual claim exists but its
capture/response is unavailable, submission_uncertain remains required.

C owns the monitor mapping/new contention case; P owns recovery/no-claim checks.
Both preserve earlier verified inputs/logs and test these final changed paths.
All source changes remain in the isolated API checkout. The live run and its
original pin remain untouched.
