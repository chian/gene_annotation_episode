"""What the launch takes from a route child's return (the old ``from_child_hpc_job_execution`` and
``from_child_local_job_execution`` ``receive_report``, whose recorded-admission, progress-provider and receipt
paths are the system's now): the handoff references, whether the endpoint was validated, and the child's own
credit and finding. The same reading for both slots; the unit's resource_id is in the unit's arguments."""


def read_from_child(slot, result, summary, records):
    if slot not in ('hpc_job_execution', 'local_job_execution'):
        raise ValueError('unknown_execution_child_slot:' + slot)
    return {'handoff_refs': list(result['execution_handoff_refs']), 'completed': result['execution_completed'],
            'child_credit': result['credit'], 'child_finding': result['finding']}
