"""What this launch takes from a resource child's admitted result (carried from ``from_child_api_job_execution.py``,
``from_child_local_job_execution.py`` and ``from_child_hpc_job_execution.py``, the same text with a different
docstring).

The old receivers recorded the child's admission, received child progress, received the references in the form
(handoff, result and receipt references), recorded native timing receipts and received tool attributions. All of
that is the system's custody now: the child's result names its records in ``record_refs`` fields and the system
receipts them. What is episode content is the report kept of one child: its usable handoff references, result
references, handoff artifacts and whether the handoff is complete."""


def read_from_child(slot, result, summary, records):
    return {'slot': slot, 'child_credit': result['credit'],
            'handoff_refs': list(result.get('execution_handoff_refs', [])),
            'result_refs': list(result.get('execution_result_refs', [])),
            'artifact_refs': list(result.get('practical_receipt_artifact_refs', [])),
            'completed': bool(result.get('execution_completed', False))}
