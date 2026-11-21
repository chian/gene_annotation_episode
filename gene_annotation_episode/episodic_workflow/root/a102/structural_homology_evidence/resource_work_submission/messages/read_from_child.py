"""What this parent takes from a resource child's admitted return for its next decision: what the launch earned
(the child's credit) and the state of the launched job at the child's last check. The handoff and check rows the
child returned are held in custody from the return on (``returned`` receipts); ``internal_summary`` reads the job
from them, so the report does not repeat them."""


def read_from_child(slot, result, summary, records):
    return {'slot': slot, 'child_credit': result['credit'], 'job_state': result['finding']['job_state']}
