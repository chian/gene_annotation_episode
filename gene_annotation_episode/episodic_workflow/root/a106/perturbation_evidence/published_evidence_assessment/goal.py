"""What this episode is for: the A106 investigation of which published evidence bears on the assigned scientific
question, carried from the old ``goal.py`` (``LiteratureGoal.instructions``) of role ``literature`` at 97308b94c. The
old text joined the role instruction (``source_contracts._ROLE_INSTRUCTIONS['literature']``), the perturbation task
text and the A106 sub-score task text; the last two are the library's ``PERTURBATION_TASK`` and ``TASK`` (their old
shared-library sources are in ``episode_support/literature``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_perturbation_prompt import (
    PERTURBATION_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_subscore import (
    TASK as A106_SUBSCORE_TASK)

BINDING_PATH = 'perturbation_evidence/published_evidence_assessment'
ROLE_INSTRUCTION = ('Investigate which published evidence bears on the assigned scientific question. You can pursue '
                    'ordinary searches and source reads directly, or assign a strategy investigation when that '
                    'narrower question warrants iteration.')
GOAL = '\n\n'.join((ROLE_INSTRUCTION, PERTURBATION_TASK, A106_SUBSCORE_TASK))
UNIT = ('one model-selected unit: a tool call (a catalog lookup, a source search or acquisition, a source read, a '
        'reasoning commit, the construction of an intervention analysis contract, or the report of the '
        'interpretation) or the commission of a child (a search strategy investigation, the launch of a permitted '
        'execution request, or the acquisition of the results of a launched job)')
RESULT = ('the interpretation of which published evidence bears on the assigned question, with the commissioned '
          "task's typed answers (screening answers, source-lead dispositions)")
