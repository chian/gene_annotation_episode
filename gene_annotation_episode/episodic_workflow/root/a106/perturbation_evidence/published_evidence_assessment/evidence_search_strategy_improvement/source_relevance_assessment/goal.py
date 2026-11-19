"""What this episode is for: the A106 search for which returned sources merit examination for the assigned question
(discovery, acquisition and reading of sources, and the commission of a page examination of one selected source),
carried from the old ``goal.py`` (``LiteratureGoal.instructions``) of ``literature_search`` at 97308b94c. The old
text joined the role instruction (``source_contracts._ROLE_INSTRUCTIONS['literature_search']``), the perturbation
task text and the A106 sub-score task text; the last two are the library's ``PERTURBATION_TASK`` and ``TASK`` (their
old shared-library sources are in ``episode_support/literature``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_perturbation_prompt import (
    PERTURBATION_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_subscore import (
    TASK as A106_SUBSCORE_TASK)

BINDING_PATH = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
ROLE_INSTRUCTION = ('Investigate which returned sources merit examination for the assigned question. Search results '
                    'are source-discovery information. Examine original sources and their conditions before '
                    'asserting biological evidence. A page child can investigate where and how to examine a '
                    'selected source.')
GOAL = '\n\n'.join((ROLE_INSTRUCTION, PERTURBATION_TASK, A106_SUBSCORE_TASK))
UNIT = ('one model-selected unit: a tool call (a catalog lookup, a source search or acquisition, a source read, a '
        'reasoning commit, or the report of the interpretation) or the commission of the examination of one '
        'selected source')
RESULT = ('the interpretation of which returned sources merit examination for the assigned question and what the '
          "examined sources say for it, with the commissioned task's typed answers (screening answers, "
          'source-lead dispositions)')
