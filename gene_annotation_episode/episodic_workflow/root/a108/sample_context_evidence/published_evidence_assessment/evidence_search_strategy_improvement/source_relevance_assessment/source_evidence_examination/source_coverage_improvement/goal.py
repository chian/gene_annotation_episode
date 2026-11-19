"""What this episode is for: the A108 reading of one source in document order, carried from the old ``goal.py``
(``LiteratureGoal.instructions`` of ``literature_ordered`` at 97308b94c). The old text joined the role
instruction (old ``source_contracts._ROLE_INSTRUCTIONS['literature_ordered']``) with the A108 organism-context task
text and the A108 reading task text; the last two are the library's ``A108_CONTEXT_TASK`` and
``A108_READING_TASK``."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_prompt import (
    A108_CONTEXT_TASK, A108_READING_TASK)

BINDING_PATH = 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement'
ROLE_INSTRUCTION = ('Investigate the source in document order as useful for the assigned question. Use returned '
                    'UTF-8 byte continuations and retain representation identity. Decide whether to continue, '
                    'reread, change the examined window or interpret obtained evidence from actual outcomes.')
GOAL = '\n\n'.join((ROLE_INSTRUCTION, A108_CONTEXT_TASK, A108_READING_TASK))
UNIT = ('one model-selected tool call on the assigned source (an access tool, a reasoning commit coupled with its '
        'purpose-specific grading and saved subscoring sheet, or a sheet population)')
RESULT = ('the controlled features code reads from the A108 subscoring and main evidence sheets saved with the '
          'graded interpretations of the source, with the sheet and assessment references, and the commissioned '
          "task's answers as counts and references")
