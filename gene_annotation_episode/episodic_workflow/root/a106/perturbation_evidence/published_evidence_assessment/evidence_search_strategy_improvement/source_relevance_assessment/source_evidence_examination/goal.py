"""What this episode is for: the A106 examination of one source its parent selected (where and how the exact source
should be examined, and the commissions of its table, ordered-reading and targeted-passage investigations), carried
from the old ``goal.py`` (``LiteratureGoal.instructions``) of ``literature_page`` at 97308b94c. The old text joined
the role instruction (``source_contracts._ROLE_INSTRUCTIONS['literature_page']``), the perturbation task text and
the A106 sub-score task text; the last two are the library's ``PERTURBATION_TASK`` and ``TASK`` (their old
shared-library sources are in ``episode_support/literature``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_perturbation_prompt import (
    PERTURBATION_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_subscore import (
    TASK as A106_SUBSCORE_TASK)

BINDING_PATH = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
ROLE_INSTRUCTION = ('Investigate where and how this exact source should be examined. Choose ordinary source '
                    'operations or selected table, ordered-reading or targeted-passage investigations as useful. '
                    'Paragraph projections omit some XML headings, tables and footnotes; retained original bytes '
                    'remain addressable.')
GOAL = '\n\n'.join((ROLE_INSTRUCTION, PERTURBATION_TASK, A106_SUBSCORE_TASK))
UNIT = ('one model-selected unit on the assigned source: a tool call (a catalog lookup, an access tool, a reasoning '
        'commit, or the report of the interpretation) or the commission of a table, ordered-reading or '
        'targeted-passage investigation of it')
RESULT = ('the interpretation of where and how the assigned source is to be examined and what it says for the '
          "assigned question, with the commissioned task's typed answers (screening answers, source-lead "
          'dispositions)')
