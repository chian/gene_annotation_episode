"""The return of the A108 passage evidence extraction. Always returned: the Episode's credit (the system hands it in
``completion``; it is the productivity signal and nothing restates it) and the finding: the controlled features code
reads from each available subscoring sheet the Episode saved (``INVESTIGATION_FINDING_FEATURES_a108.md`` lines A1 to A28
and B1 to B18, each with its sheet's reference) and the references of the current retained assessments committed with
their grading. No model-written text is returned: the assessments' typed ``investigation_finding`` stays in the
assessment records. Selectable: the relevant source leads (count and sources). This episode declares no cells (its parent
requests none)."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    LEAD_FORM, finding_form)

LEADS = 'literature_source_lead_dispositions'

FINDING_FORM = finding_form('The current retained assessments committed with their grading sheet')
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled features of the saved A108 sheets', form=FINDING_FORM),
    LEADS: Field('record', 'The relevant validated source leads as a count and their sources', form=LEAD_FORM,
                 required=False),
})


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'], 'finding': summary['finding']}
    if LEADS in selection:
        result[LEADS] = summary['lead_return']
    return result
