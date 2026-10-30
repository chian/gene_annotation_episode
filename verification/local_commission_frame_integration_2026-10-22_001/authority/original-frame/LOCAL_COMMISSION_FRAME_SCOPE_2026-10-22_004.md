# Local commission frame review clarification 004

This new record supplements scopes 001/002/003 without changing those files.

Exact saved JSON identity is compared through canonical JSON or content digests,
not Python equality that treats true, 1 and 1.0 as equal. This applies to original
action/selection agreement, matching pending selection/provenance, and original
report-contract agreement. No producer field is normalized or changed.

A present saved runtime_episodes child path/request must agree exactly with the
original C1 child. A present conflict raises
local_commission_frame_identity_conflict. A missing child row preserves the
known original commission and adds child_record_unavailable to that row; it does
not invent a new child or erase C1.

Validate each available C4 body's parent/index/handle/return/admission identities
against its physical row even when its C1 row is missing. An unmatched valid
admission still appears only by its original admission_id. Nonempty
unmatched_admission_refs also adds unmatched_admissions to top-level coverage
reasons. Complete enumeration of the current C1 table is not proof of complete
historical coverage in the presence of known unmatched admissions.

The return scan stops after the first page containing an outside-C1 item,
after processing all valid known items on that same page. Its status becomes
incomplete; remaining captured commissions stay unknown. It does not continue
through an outside population that may be growing independently of the bounded
captured C1 population. A page with an outside item followed by a known item
retains the latter's valid metadata. This fixes an ambiguity in 001's stopping
wording, not a scientific stopping rule or action cap.

Root passed these same decisions to both isolated coding workers. Their file
ownership is unchanged. No active source, score, controller, model assumption or
scientific state was changed by this clarification.
