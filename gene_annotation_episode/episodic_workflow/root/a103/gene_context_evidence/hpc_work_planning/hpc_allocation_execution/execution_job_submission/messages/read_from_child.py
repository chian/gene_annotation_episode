"""What this launch takes from a resource child's admitted result (carried from ``from_child_api_job_execution.py``,
``from_child_hpc_job_execution.py`` and ``from_child_local_job_execution.py``, the same text with a different
docstring).

The old receivers recorded the child's admission, received child progress, received the references in the form,
recorded native timing receipts and received tool attributions: that is custody now (the child's result names its
records in ``record_refs`` fields and the system receipts them). What is episode content is the report kept of one
child: its handoff references, whether the handoff is usable and whether it is complete. A handoff is usable when
the child returned handoff references and its own finding says a handoff was made: the API child's
``handoff_established``, the HPC child's ``handed_off``; the local child's finding has no such flag, so its
returned references decide."""


def read_from_child(slot, result, summary, records):
    refs = list(result['execution_handoff_refs'])
    finding = result['finding']
    if slot == 'api_job_execution':
        usable, qualification = bool(refs) and finding['handoff_established'], finding['qualification']
    elif slot == 'hpc_job_execution':
        usable, qualification = bool(refs) and finding['handed_off'], 'a command observed the job submitted' \
            if finding['handed_off'] else 'no command observed the job submitted with a handoff'
    elif slot == 'local_job_execution':
        usable, qualification = bool(refs), 'handoff references returned' if refs else 'no handoff reference returned'
    else:
        raise LookupError('execution_job_submission_has_no_slot:' + slot)
    return {'slot': slot, 'child_credit': result['credit'], 'handoff_refs': refs, 'usable_handoff': usable,
            'completed': bool(result['execution_completed']), 'qualification': qualification}
