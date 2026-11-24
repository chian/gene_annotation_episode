"""What this episode takes from a resource child's admitted return (carried from the three
``from_child_<role>.py``, the same text with a different name). The old receivers recorded admission references,
progress-provider receipts, timing receipts and tool attributions: old-runner machinery (the system receipts the
records a child returns). What is kept is what the parent's credit and report read: the child's handoff references,
whether it verified completion and its own finding.

A handoff is usable here when the child returned handoff references; the API child's own finding must also say it
established one (``handoff_established``). The old test of usability read the handoff record through the job
progress provider (``targets.usable_handoff``); no handoff record kind exists yet (BLOCKED-ON-JOB-SERVICE, see the
carry-over record), so the record itself is not read."""


def read_from_child(slot, result, summary, records):
    refs = list(result['execution_handoff_refs'])
    finding = result['finding']
    if slot == 'launch_api':
        usable = bool(refs) and finding['handoff_established']
    elif slot in ('launch_hpc', 'launch_local'):
        usable = bool(refs)
    else:
        raise ValueError('execution_job_submission_slot_unknown:' + slot)
    return {'slot': slot, 'handoff_refs': refs, 'usable_handoff': usable,
            'completed': bool(result['execution_completed']), 'child_credit': result['credit'], 'finding': finding}
