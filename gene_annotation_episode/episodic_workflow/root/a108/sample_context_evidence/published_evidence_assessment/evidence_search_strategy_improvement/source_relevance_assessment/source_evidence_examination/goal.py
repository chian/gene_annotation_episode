"""What this episode is for: the A108 examination of one exact source for the assigned organism-context question,
carried from the old ``goal.py`` (``LiteratureGoal.instructions``) of ``literature_page`` at 97308b94c. The old text
joined the role instruction (old ``source_contracts._ROLE_INSTRUCTIONS['literature_page']``) with the A108 context
task and the A108 reading task (the library's ``literature/prompts/literature_prompt.py``; the old shared-library
source was ``literature_a108_prompt``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_prompt import (
    A108_CONTEXT_TASK, A108_READING_TASK)

BINDING_PATH = 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
ROLE_INSTRUCTION = ('Investigate where and how this exact source should be examined. Choose ordinary source '
                    'operations or selected table, ordered-reading or targeted-passage investigations as useful. '
                    'Paragraph projections omit some XML headings, tables and footnotes; retained original bytes '
                    'remain addressable.')
GOAL = '\n\n'.join((ROLE_INSTRUCTION, A108_CONTEXT_TASK, A108_READING_TASK))
UNIT = ('one model-selected tool call on the assigned source (a catalog lookup, an access tool, a reasoning commit '
        'coupled with its contextual grading sheets, a sheet population, or the report of the interpretation), or '
        'one child commission (a table, an ordered reading or targeted passages of the source)')
RESULT = ('the controlled features code reads from the A108 subscoring and main evidence sheets saved (own and the '
          "children's), with the sheet and graded assessment references, and the commissioned task's answers as "
          'counts and references')
