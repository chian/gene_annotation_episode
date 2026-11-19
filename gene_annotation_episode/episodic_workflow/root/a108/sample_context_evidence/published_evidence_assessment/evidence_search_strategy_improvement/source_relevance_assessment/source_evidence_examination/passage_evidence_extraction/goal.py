"""What this episode is for: the A108 reading of the passages of one source its parent selected, carried from the
old ``goal.py`` (``LiteratureGoal.instructions``) of ``literature_targeted`` at 97308b94c. The old text joined the
role instruction, ``A108_CONTEXT_TASK`` and ``A108_READING_TASK`` (the library's
``literature/prompts/literature_prompt.py``; their old shared-library source was ``literature_a108_prompt``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_prompt import (
    A108_CONTEXT_TASK, A108_READING_TASK)

BINDING_PATH = 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction'
ROLE_INSTRUCTION = ('Investigate the supplied source-bound passages for the assigned question. Read neighboring '
                    'context, qualifications or alternative passages as needed and revise the interpretation from '
                    'actual outcomes. Separate spans remain separate; never concatenate them into a fabricated '
                    'quotation.')
GOAL = '\n\n'.join((ROLE_INSTRUCTION, A108_CONTEXT_TASK, A108_READING_TASK))
UNIT = ('one model-selected tool call on the assigned source (a catalog lookup, an access tool, a graded reasoning '
        'commit, a subscoring or aggregation population, or the report of the interpretation)')
RESULT = ('the controlled features code reads from the A108 subscoring and main evidence sheets saved, with the '
          "sheet and graded assessment references, and the commissioned task's answers as counts and references")
