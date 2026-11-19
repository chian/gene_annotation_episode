"""What the parent takes from a child's admitted result (carried from ``from_child_execution_job_submission.py``,
``from_child_execution_progress_assessment.py``, ``from_child_execution_result_acquisition.py``,
``from_child_hpc_work_planning.py``, ``from_child_published_evidence_assessment.py`` and
``from_child_biochemical_feasibility_evidence.py``).

Not carried: the old receivers' bookkeeping (``receive_report``, ``receive_progress``: the recorded-admission refs on
replay, the progress provider delivery with its content digest, the receipts, the counterpart reads and the tool
attributions are the system's custody now). What a receiver kept of the child's typed form is the child's admitted
result: its credit (information for this episode's summary: a child's credit is never added to this credit), its
finding and every field this episode asked for (the required fields of the child's form and the selected ones). The
references the old receiver read from the typed form are the ``record_refs`` fields of the result; the system writes
the ``returned`` receipts for them, and they are held from here on."""
from ..task import CHILD_SLOTS


def read_from_child(slot, result, summary, records):
    if slot not in CHILD_SLOTS:
        raise LookupError('biochemical_feasibility_evidence_has_no_slot:' + slot)
    return {'slot': slot, 'child_credit': result['credit'], 'finding': result['finding'],
            'facts': {name: value for name, value in result.items() if name not in ('credit', 'finding')}}
