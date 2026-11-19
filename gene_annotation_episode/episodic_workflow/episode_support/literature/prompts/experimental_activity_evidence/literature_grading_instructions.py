"""The owner's A105 grading instructions as one section of a grading episode's decision instructions.

Old delivery (``prompts/literature_task_selection.py`` and ``tools/literature_task_families.py`` at ``97308b94c``):
the grader-selection hierarchy and its table of the eight graders (``A105_ASSAY_SELECTION_TASK``), the reusable
assay grader's filling instruction (``ASSAY_GRADING_TASK``), and the filling instruction of each sheet family whose
population is offered (the A105 family table, including the across-experiment aggregation rules when
``literature.a105.aggregate`` is offered). Each grading episode's ``decide`` shows this section."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_assay_grading_prompt import (
    ASSAY_GRADING_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_assay_selection_prompt import (
    A105_ASSAY_SELECTION_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_task_families import (
    family_tasks)

GRADING_HEADING = ('\n\nA105 grading. The reason tool carries the grader arguments in evidence_processing.gradings '
                   '(literature.assay_grading.populate arguments, JSON-encoded).\n')


def grading_section(population_tools=()):
    """The grading section: the selection hierarchy and grader table, the assay grader's instruction, and the
    instruction of each offered population family other than the grader itself (library tool names)."""
    families = family_tasks(tuple(tool for tool in population_tools if tool != 'literature.assay_grading.populate'))
    text = GRADING_HEADING + A105_ASSAY_SELECTION_TASK + '\n\n' + ASSAY_GRADING_TASK
    if families:
        text += '\n\nSheet families offered as population tools:\n' + '\n\n'.join(families)
    return text + '\n'


__all__ = ['grading_section']
