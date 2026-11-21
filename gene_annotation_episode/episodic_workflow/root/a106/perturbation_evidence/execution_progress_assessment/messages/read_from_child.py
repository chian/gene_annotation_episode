"""What the monitor takes from a dependency monitor's return, carried from
``from_child_execution_progress_assessment.py`` (``receive_progress``): the child's credit, its controlled finding
and the references of the check rows it returned. The system has receipted those rows as returned, so this monitor
holds them: its credit and its summary read them through ``records``."""


def read_from_child(slot, result, summary, records):
    return {'slot': slot, 'credit': result['credit'], 'finding': result['finding'],
            'check_refs': list(result['check_refs'])}
