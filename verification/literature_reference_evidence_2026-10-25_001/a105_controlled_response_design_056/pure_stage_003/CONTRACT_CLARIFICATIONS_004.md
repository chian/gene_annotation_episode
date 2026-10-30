# Accepted finite clarifications and root review correction

Root accepted four additive closed reasons before use: conflicting_endpoint,
conflicting_normalization, conflicting_subject_correspondence (existing
conflicting status) and uninformative_bounds (existing unavailable status).
No input shape or quality coefficient was added.

Unknown reuse alone supplies neither physical identity nor alias cancellation.
Separately explicit known equal physical owner IDs, exact consistent values and
role/context, and actually applicable matched/shared controls establish an alias.
They can support cancellation while retaining the unknown_control_reuse
qualification. Unknown owners or merely equal values cannot. This makes explicit
the distinction requested in root's review; it does not infer sameness from the
unknown flag. Tests distinguish identical censored control owners from unknown
or distinct owners with equal thresholds.

Root independently found a missing global dimension check in the initial pure
implementation: two locally valid pairs could have different physical dimensions
while their declared endpoint/normalization IDs matched. The root's original
module hash was 5a3a493722e72f47b67b76a25bf56d8bbe02418e8b40ad97da003b17e93dfd92.
The same module was snapshotted here in review_baseline_004. The new dedicated
regression failed against it with e=6 and no unit, then the correction added the
required common-dimension check for e and all dependent variance/model cells.
Both valid local pair values/units remain. This is a correction to the reviewed
contract, not a new scientific applicability requirement.
