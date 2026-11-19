"""What this episode is for: which published evidence bears on the commissioned A108 organism-context question,
carried from the old ``goal.py`` (``LiteratureGoal.instructions``) of ``literature`` at 97308b94c. The old text joined
the role instruction (old ``source_contracts._ROLE_INSTRUCTIONS['literature']``) with the A108 context task and the
A108 reading task (the library's ``literature/prompts/literature_prompt.py``; the old shared-library source was
``literature_a108_prompt``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_prompt import (
    A108_CONTEXT_TASK, A108_READING_TASK)

BINDING_PATH = 'sample_context_evidence/published_evidence_assessment'
ROLE_INSTRUCTION = ('Investigate which published evidence bears on the assigned scientific question. You can pursue '
                    'ordinary searches and source reads directly, or assign a strategy investigation when that '
                    'narrower question warrants iteration.')
GOAL = '\n\n'.join((ROLE_INSTRUCTION, A108_CONTEXT_TASK, A108_READING_TASK))
UNIT = ('one model-selected tool call (a catalog lookup, an acquisition or access tool, a reasoning commit coupled '
        'with its contextual grading sheets, a sheet population, or the report of the interpretation), or one child '
        'commission (the strategy investigation of which search approach is productive for the question)')
RESULT = ('the controlled features code reads from the A108 subscoring and main evidence sheets saved (own and the '
          "children's), with the sheet and graded assessment references, and the commissioned task's answers as "
          'counts and references')
