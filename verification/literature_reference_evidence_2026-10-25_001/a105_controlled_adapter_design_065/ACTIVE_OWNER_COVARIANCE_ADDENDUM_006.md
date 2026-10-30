# Additive006: an unknown active owner is not covered by a known-ID roster

No schema change is needed.003 as corrected by004 requires source-owned active
covariance support. Make the following dependent invariant explicit:

If ANY active group has an unknown physical owner, V/SE/precision/model remain
unavailable. A provided OwnerCovariance can cover every listed
required_covariance_owner_id and still be incomplete, because unknown IDs cannot
appear in that list. In that case covariance_state is incomplete_active_coverage,
not available. Check all active groups for known_owner in addition to set
coverage. A genuinely canceled known owner needs no row/column.

The constructed006 fixture has known active owners[A,B,C] plus a distinct
unresolved role. OwnerCovariance legitimately supplies[A,B,C], so its provided
and known-required ID sets are equal. The unresolved active role still prevents
V/model inference. With explicitly unknown reuse and otherwise valid source
science, ordinary four-term magnitude remains conditional; do not infer that
unknown role is B, cancel it, fabricate its covariances or erase its raw/local
facts. Unknown reuse is distinct from an unsupported assertion of SAME reuse.

ACTIVE_UNKNOWN_OWNER_CASE_006.json is a HAND-CONSTRUCTED input/expected-semantics
fixture. Its schema shape was validated; no owner semantic calculator or native
execution was run. build_active_unknown_owner_case_006.py retains the exact
construction/check source for independent review and reproduction.
