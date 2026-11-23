"""The return: controlled data only; no path and no text. EVERY RETURNED RECORD LIST IS CLOSED UNDER NAMING: ``internal_summary`` builds
each with ``job_records.returned_with_names`` (the records the child returns together with everything they name among the records it
holds), so the parent holds what the returned records name and nothing private is named. Always: ``credit`` and the ``finding``: the
state of the job (``ready``, ``estimated``, ``launched``, ``finished``, ``extracted`` or ``failed``); once graded the ligand, candidate,
sample and clashing-sample counts of the sheet and the highest and lowest ligand value (the per-ligand values stay in the graded sheet,
which the head reads); the shared wait notice, estimate and observed seconds and last failure code (``structure_search_child.
COMMON_FINDING``). Selectable: ``execution_handoff_refs``, ``execution_check_refs``, ``execution_closure_refs`` and ``graded_refs`` (the
graded records: the scores, their source and the grading sheet, with the artifacts they name)."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.partner_cofolding import (
    STATES)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    COMMON_FINDING, common_finding)

FINDING_FORM = RecordForm({
    'state': ChoiceField('text', 'The job: ready (nothing estimated), estimated (an estimate held, nothing launched), launched '
                                 '(accepted, not finished), finished (the job ended; not yet extracted), extracted (graded) or failed',
                         STATES),
    'ligand_count': Field('integer', 'The ligands of the graded sheet', required=False),
    'candidate_count': Field('integer', 'The ligand candidates with a value in the graded test (the mean over their samples)',
                             required=False),
    'sample_count': Field('integer', 'The samples scored over all ligands', required=False),
    'clashing_sample_count': Field('integer', 'The samples with an inter-chain clash (their value is 0)', required=False),
    'highest_value': Field('number', 'The highest ligand value (the mean interface score of its samples; the model\'s confidence, '
                                     'not measured binding)', required=False),
    'lowest_value': Field('number', 'The lowest ligand value', required=False),
    **COMMON_FINDING,
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The state of the job and its controlled facts', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The handoff records of the jobs launched', required=False),
    'execution_check_refs': Field('record_refs', 'The status records of the job', required=False),
    'execution_closure_refs': Field('record_refs', 'The closure record of the fetched result', required=False),
    'graded_refs': Field('record_refs', 'The graded records: the scores data product, its source, the grading sheet and the artifacts '
                                        'they name', required=False),
})


def final_to_parent(summary, completion, selection):
    finding = {'state': summary['state'], **common_finding(summary)}
    if summary['counts']:
        counts = summary['counts'][-1]
        finding.update(counts)
    facts = {'execution_handoff_refs': list(summary['handoff_refs']), 'execution_check_refs': list(summary['check_refs']),
             'execution_closure_refs': list(summary['closure_refs']), 'graded_refs': list(summary['graded_refs'])}
    return {'credit': completion['credit'], 'finding': finding, **{name: facts[name] for name in selection}}
