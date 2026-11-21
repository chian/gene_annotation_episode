"""The return: controlled data only; no path and no text. EVERY RETURNED RECORD LIST IS CLOSED UNDER NAMING: ``internal_summary`` builds each with ``job_records.returned_with_names`` (the records the child returns together with everything they name among the records it holds), so the parent holds what the returned records name and nothing private is named (the summary is where the closing runs: ``final_to_parent`` receives no reader). Always: ``credit`` and the ``finding``: the state of the job
(``no_estimate``, ``estimated``, ``launched``, ``finished``, ``extracted`` or ``failed``), the sequences aligned, the
alignment columns, the candidates aligned and the shared wait notice, estimate and observed seconds and last failure code
(``bvbrc_job_child.COMMON_FINDING``). Selectable: ``execution_handoff_refs``, ``check_refs``, ``closure_refs`` and
``graded_refs`` (the graded records: the source, the grading artifact, the alignment's data-product row, the reference
records and the alignment observations). The alignment's data-product row is the record a later child that needs an
alignment is passed."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_job_child import (
    COMMON_FINDING, STATES, common_finding)

FINDING_FORM = RecordForm({
    'state': ChoiceField('text', 'The job: no_estimate, estimated (an estimate held, nothing launched), launched (accepted, '
                                 'not finished), finished (the service finished it; not yet extracted), extracted (graded) '
                                 'or failed', STATES),
    'sequence_count': Field('integer', 'The sequences of the graded alignment (the target and the references)',
                            required=False),
    'column_count': Field('integer', 'The columns of the graded alignment', required=False),
    'candidate_count': Field('integer', 'The candidates with a reference sequence in the graded alignment', required=False),
    'planned_sequence_count': Field('integer', 'The sequences the job was planned with (target included)', required=False),
    **COMMON_FINDING,
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The state of the job and its controlled facts', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The handoff records of the jobs launched', required=False),
    'check_refs': Field('record_refs', 'The status records of the job', required=False),
    'closure_refs': Field('record_refs', 'The closure record of the fetched alignment', required=False),
    'graded_refs': Field('record_refs', 'The graded records: the source, the grading artifact, the alignment data-product '
                                        'row, the references and the alignment observations', required=False),
})


def final_to_parent(summary, completion, selection):
    finding = {'state': summary['state'], 'planned_sequence_count': summary['planned']['sequences'],
               **common_finding(summary)}
    if summary['counts']:
        finding.update(summary['counts'][-1])
    facts = {'execution_handoff_refs': list(summary['handoff_refs']), 'check_refs': list(summary['check_refs']),
             'closure_refs': list(summary['closure_refs']), 'graded_refs': list(summary['graded_refs'])}
    return {'credit': completion['credit'], 'finding': finding, **{name: facts[name] for name in selection}}
