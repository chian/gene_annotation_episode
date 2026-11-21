"""Where the extraction stands, from the loop's view: the library's ``extraction_state`` (the one table region shown as
segments with their byte offsets, read through custody from the artifact of the page's representation; the input list,
which is the region until it has been extracted once and is empty after that; the held records; the extractions'
outcomes), with this episode's own credit definition, the controlled features code reads from the saved sheets, the cell
rows of the requested grading components and the source leads."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.sample_context_evidence.literature_leaf_extraction import (
    extraction_state)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    assessment_basis, lead_return, own_cell_refs, own_findings)

from ..credit import credit_binding, lead_dispositions
from .read_from_parent import REQUESTED_GRADING

GRADING_NAMESPACE = 'literature_a108_grading_cells'


def internal_summary(view):
    parent = view.parent_input
    summary = extraction_state(view, parent['spans'])
    summary['literature_assignment'] = {**summary['literature_assignment'], REQUESTED_GRADING: parent[REQUESTED_GRADING]}
    summary['credit_binding'] = credit_binding(parent['task_key'], parent['task'])
    summary['finding'] = {**own_findings(view.records), 'assessment_refs': summary['graded_assessments']}
    summary['finding']['observation_refs'] = assessment_basis(view.records, summary['finding']['assessment_refs'])
    summary['grading_cell_refs'] = own_cell_refs(view.records, GRADING_NAMESPACE)
    summary['source_lead_dispositions'] = lead_dispositions(summary, view.records)
    summary['lead_return'] = lead_return(summary['source_lead_dispositions'])
    return summary
