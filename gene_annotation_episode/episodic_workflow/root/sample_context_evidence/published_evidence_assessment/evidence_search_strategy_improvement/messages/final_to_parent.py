"""The return of the A108 evidence search strategy improvement. Always returned: the Episode's credit (the system hands it in
``completion``; it is the productivity signal and nothing restates it) and the finding: the controlled features code
reads from each available subscoring sheet and main-sheet cell this episode's descendants saved
(``INVESTIGATION_FINDING_FEATURES_a108.md`` lines A1 to A28 and B1 to B18, each with its sheet's reference, side by
side and never combined) and the references of the current retained assessments committed with their grading. No
model-written text is returned. Selectable: the relevant source leads (count and sources) and the cell rows of the
requested A108 components (references only)."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.literature_numerical_contracts import (
    RETURN_MEANINGS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    LEAD_FORM, finding_form)

LEADS = 'literature_source_lead_dispositions'
GRADING_CELLS = 'literature_a108_grading_cells'
AGGREGATION_CELLS = 'literature_a108_aggregation_cells'

FINDING_FORM = finding_form('The current retained assessments committed with their grading sheet (returned)')
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled features of the saved A108 sheets', form=FINDING_FORM),
    LEADS: Field('record', 'The relevant validated source leads as a count and their sources', form=LEAD_FORM,
                 required=False),
    GRADING_CELLS: Field('record_refs', 'The saved cell rows: ' + RETURN_MEANINGS[GRADING_CELLS], required=False),
    AGGREGATION_CELLS: Field('record_refs', 'The saved cell rows: ' + RETURN_MEANINGS[AGGREGATION_CELLS],
                             required=False),
})


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'], 'finding': summary['finding']}
    if LEADS in selection:
        result[LEADS] = summary['lead_return']
    if GRADING_CELLS in selection:
        result[GRADING_CELLS] = summary['grading_cell_refs']
    if AGGREGATION_CELLS in selection:
        result[AGGREGATION_CELLS] = summary['aggregation_cell_refs']
    return result
