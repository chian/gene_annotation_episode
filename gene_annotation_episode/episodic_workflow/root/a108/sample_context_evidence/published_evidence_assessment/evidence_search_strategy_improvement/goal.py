"""What this episode is for: which search approach is productive for the assigned organism-context question, carried
from the old ``goal.py`` (``LiteratureGoal.instructions``) of ``literature_strategy`` at 97308b94c. The old text joined
the role instruction (old ``source_contracts._ROLE_INSTRUCTIONS['literature_strategy']``) with the A108 context task
and the A108 reading task (the library's ``literature/prompts/literature_prompt.py``; the old shared-library source was
``literature_a108_prompt``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_prompt import (
    A108_CONTEXT_TASK, A108_READING_TASK)

BINDING_PATH = 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
ROLE_INSTRUCTION = ('Investigate which search approach is productive. Keep the information objective and evidence '
                    'context separate from a literal provider query. Revise terms or source choices in light of '
                    'actual search/read outcomes; a search child can investigate which returned sources deserve '
                    'examination.')
GOAL = '\n\n'.join((ROLE_INSTRUCTION, A108_CONTEXT_TASK, A108_READING_TASK))
UNIT = ('one model-selected tool call (a catalog lookup, an acquisition or access tool, a reasoning commit coupled '
        'with its contextual grading sheets, a sheet population, or the report of the interpretation), or one child '
        'commission (the relevance assessment of the returned sources a search produced)')
RESULT = ('the controlled features code reads from the A108 subscoring and main evidence sheets saved (own and the '
          "children's), with the sheet and graded assessment references, and the commissioned task's answers as "
          'counts and references')
