"""What this episode is for: the A106 reading of one source in document order, carried from the old ``goal.py``
(``LiteratureGoal.instructions``) of ``literature_ordered`` at 97308b94c. The old text joined the role instruction,
the perturbation task text and the A106 sub-score task text; the last two are the library's ``PERTURBATION_TASK``
and ``TASK`` (their old shared-library sources are in ``episode_support/literature``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_perturbation_prompt import (
    PERTURBATION_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_subscore import (
    TASK as A106_SUBSCORE_TASK)

BINDING_PATH = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement'
ROLE_INSTRUCTION = ('Investigate the source in document order as useful for the assigned question. Use returned '
                    'UTF-8 byte continuations and retain representation identity. Decide whether to continue, '
                    'change the examined window or interpret obtained evidence from actual outcomes.')
GOAL = '\n\n'.join((ROLE_INSTRUCTION, PERTURBATION_TASK, A106_SUBSCORE_TASK))
UNIT = ('one model-selected tool call on the assigned source (a catalog lookup, an access tool, a sheet population, '
        'the automatic A106 score judgment or a reasoning commit)')
RESULT = ('the controlled features of the current A106 grading sheets saved from the source (intervention grading '
          "sheets and final subscores), with the commissioned task's typed answers as counts and references")
