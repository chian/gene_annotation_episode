"""The return of the A108 source coverage improvement. Always returned: the Episode's credit (the system hands it in
``completion``; it is the productivity signal and nothing restates it) and the finding: the controlled features code
reads from each available subscoring sheet and main-sheet cell the Episode saved (``INVESTIGATION_FINDING_FEATURES_a108.md``
lines A1 to A28 and B1 to B18, with each sheet's reference) and the references of the current retained assessments
committed with their grading. No model-written text is returned: the assessments' ``investigation_finding`` stays
in the assessment records. Selectable: the cell rows of the requested A108 components (references only), the
screening answer (counts) and the source leads (count and source references)."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.literature_numerical_contracts import (
    RETURN_MEANINGS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    LEAD_FORM, SCREENING_FORM, finding_form)

from .internal_summary import POPULATION_ROUTES

GRADING_CELLS = POPULATION_ROUTES[0][0]
AGGREGATION_CELLS = POPULATION_ROUTES[1][0]
SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'

FINDING_FORM = finding_form('The current retained assessments committed with their grading sheet')
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled features of the saved A108 sheets', form=FINDING_FORM),
    GRADING_CELLS: Field('record_refs', 'The saved cell rows: ' + RETURN_MEANINGS[GRADING_CELLS], required=False),
    AGGREGATION_CELLS: Field('record_refs', 'The saved cell rows: ' + RETURN_MEANINGS[AGGREGATION_CELLS],
                             required=False),
    SCREENING: Field('record', 'The screening answer as counts', form=SCREENING_FORM, required=False),
    LEADS: Field('record', 'The relevant validated source leads as a count and their sources', form=LEAD_FORM,
                 required=False),
})


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'], 'finding': summary['finding']}
    if GRADING_CELLS in selection:
        result[GRADING_CELLS] = summary['grading_cell_refs']
    if AGGREGATION_CELLS in selection:
        result[AGGREGATION_CELLS] = summary['aggregation_cell_refs']
    if SCREENING in selection:
        result[SCREENING] = summary['screening_return']
    if LEADS in selection:
        result[LEADS] = summary['lead_return']
    return result
