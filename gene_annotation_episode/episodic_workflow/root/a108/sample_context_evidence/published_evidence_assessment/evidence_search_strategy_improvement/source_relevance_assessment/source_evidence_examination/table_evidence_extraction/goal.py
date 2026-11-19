"""What this episode is for: the A108 reading of the table or sheet of one source its parent selected, carried from
the old ``goal.py`` (``LiteratureGoal.instructions``) of ``literature_table`` at 97308b94c. The old text joined the
role instruction (``source_contracts._ROLE_INSTRUCTIONS['literature_table']``) with the A108 context task and the A108
reading task (the old shared ``literature_a108_prompt``, now ``episode_support/literature/prompts/literature_prompt.py``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_prompt import (
    A108_CONTEXT_TASK, A108_READING_TASK)

BINDING_PATH = 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction'
ROLE_INSTRUCTION = ('Investigate the selected table/sheet and its scientific meaning. Select rows, headers, '
                    'conditions and footnotes deliberately; revise row selection or reread when outcomes warrant it. '
                    'XLSX cells/formulas/caches keep their native identity. Article XML tables are read through exact '
                    'original-source windows.')
GOAL = '\n\n'.join((ROLE_INSTRUCTION, A108_CONTEXT_TASK, A108_READING_TASK))
UNIT = ('one model-selected tool call on the assigned source (a catalog lookup, an access tool, a reasoning commit '
        'coupled with its contextual grading sheets, a sheet population, or the report of the interpretation)')
RESULT = ('the controlled features code reads from the A108 subscoring and main evidence sheets saved, with the '
          "sheet and graded assessment references, and the commissioned task's answers as counts and references")
