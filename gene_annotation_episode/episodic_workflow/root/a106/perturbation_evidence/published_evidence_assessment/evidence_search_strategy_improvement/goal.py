"""What this episode is for: the A106 investigation of which search approach is productive for the assigned question
(revising terms or source choices in light of actual search and read outcomes, and the commission of a source
relevance assessment of the returned sources), carried from the old ``goal.py`` (``LiteratureGoal.instructions``) of
``literature_strategy`` at 97308b94c. The old text joined the role instruction
(``source_contracts._ROLE_INSTRUCTIONS['literature_strategy']``), the perturbation task text and the A106 sub-score
task text; the last two are the library's ``PERTURBATION_TASK`` and ``TASK`` (their old shared-library sources are in
``episode_support/literature``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_perturbation_prompt import (
    PERTURBATION_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_subscore import (
    TASK as A106_SUBSCORE_TASK)

BINDING_PATH = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
ROLE_INSTRUCTION = ('Investigate which search approach is productive. Keep the information objective and evidence '
                    'context separate from a literal provider query. Revise terms or source choices in light of '
                    'actual search/read outcomes; a search child can investigate which returned sources deserve '
                    'examination.')
GOAL = '\n\n'.join((ROLE_INSTRUCTION, PERTURBATION_TASK, A106_SUBSCORE_TASK))
UNIT = ('one model-selected unit: a tool call (a catalog lookup, a source search or acquisition, a source read, a '
        'reasoning commit, or the report of the interpretation) or the commission of the source relevance '
        'assessment of returned sources')
RESULT = ('the interpretation of which search approach is productive for the assigned question and what the '
          "examined sources say for it, with the commissioned task's typed answers (screening answers, "
          'source-lead dispositions)')
