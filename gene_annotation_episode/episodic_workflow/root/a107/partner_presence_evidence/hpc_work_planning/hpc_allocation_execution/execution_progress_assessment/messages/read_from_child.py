"""What the monitor takes from a child monitor's return, carried from ``from_child_execution_progress_assessment.py``
(``receive_progress``): the progress observations the child delivered. Each delivered ref must be a readable
progress observation: here, one the child's return carries a snapshot of. The old recording of the delivery under
its operation key with a signature of form, schema and scope (a different form under the same key conflicts) is
the system's, and the old scope check of each ref against the provider is not carried (README 3b R1)."""


def read_from_child(slot, result, summary, records):
    refs = result['monitoring_progress_refs']
    snapshots = result['monitoring_progress_snapshots']
    missing = [ref for ref in refs if ref not in snapshots]
    if missing:
        raise ValueError('monitor_child_progress_not_a_readable_observation:' + missing[0])
    return {'slot': slot, 'progress_refs': list(dict.fromkeys(refs)), 'progress_snapshots': dict(snapshots),
            'child_credit': result['credit'], 'child_finding': result['finding']}
