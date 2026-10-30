# Original-owner occurrence identity correction

Self-review after check068 found that an operation-key-derived attempt_id alone
can repeat across run/episode owners. `masking_occurrence_id` now uses the canonical
SHA256 of the **full Identity** before direction/role/ordinal:
`native_blast_masking:<identity_sha256>:<direction>:<role>:<ordinal>`.

This supersedes the helper encoding in IMPLEMENTATION_001, without changing its
public signature or any Job/Bundle/Capture shape. Native producer_attempt_id stays
the original attempt_id. The original check068 artifacts/source snapshot remain
unchanged historical evidence. Its four tiny native operations and47 passing
checks establish the tested source pin, not a silent test of this later correction.
A separate saved-data-only focused check will cover the corrected identifier,
generated reference association and unchanged custody; no native rerun is needed.
