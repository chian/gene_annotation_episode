"""The return of the A108 sample-context head. Always returned: the Episode's credit (the system hands it in
``completion``; it is the productivity signal and nothing restates it) and the finding: the controlled features code
reads from each available subscoring sheet and main-sheet cell this episode and its children saved
(``INVESTIGATION_FINDING_FEATURES_a108.md`` lines A1 to A28 and B1 to B18, each with its sheet's reference, side by
side and never combined) and the references of the current retained assessments committed with their grading (own and
returned), which the parent's credit counts. No model-written text is returned. Selectable: the records the reasoning
commits of this episode and its children created or changed (references)."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    finding_form)

COMMITTED = 'committed_record_refs'

FINDING_FORM = finding_form('The current retained assessments committed with their grading sheet (own and returned)')
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled features of the saved A108 sheets', form=FINDING_FORM),
    COMMITTED: Field('record_refs', 'Every record the reasoning commits of this episode and its children created or '
                     'changed', required=False),
})


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'], 'finding': summary['finding']}
    if COMMITTED in selection:
        result[COMMITTED] = summary['committed_record_refs']
    return result
