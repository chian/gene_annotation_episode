"""What this episode is for: the A106 reading of the passages of one source its parent selected, carried from the
old ``goal.py`` (``LiteratureGoal.instructions``) of ``literature_targeted`` at 97308b94c. The old text joined the role instruction, the perturbation task text (the library's PERTURBATION_TASK) and the A106
sub-score task text (the library's subscore TASK): all three are joined, since this episode offers
literature.a106.finalize and the other population tools."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_perturbation_prompt import (
    PERTURBATION_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_subscore import (
    TASK as A106_SUBSCORE_TASK)

BINDING_PATH = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction'
ROLE_INSTRUCTION = ('Investigate the supplied source-bound passages for the assigned question. Read neighboring '
                    'context, qualifications or alternative passages as needed and revise the interpretation from '
                    'actual outcomes. Separate spans remain separate; never concatenate them into a fabricated '
                    'quotation.')
GOAL = '\n\n'.join((ROLE_INSTRUCTION, PERTURBATION_TASK, A106_SUBSCORE_TASK))
UNIT = ('one model-selected tool call on the assigned source (a catalog lookup, an access tool, a sheet population, '
        'the automatic A106 score judgment or a reasoning commit)')
RESULT = ('the controlled features of the current A106 grading sheets saved from the source (intervention grading '
          "sheets and final subscores), with the commissioned task's typed answers as counts and references")
