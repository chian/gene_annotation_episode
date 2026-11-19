"""The A110 literature reaction grader as the model is told it in a decision's instructions: the owner's two
experiment types with their questions and the considerations checked before a cell is filled (R1 to R3), the
fifteen cells and their combination (R4), the named missing reasons and the conditions every cell rests on (R5),
the inputs the sheet keeps apart (R6), the grader prompt (R7), what each saved view means (R8, R9) and the lead
of the selected family (R10). Every sentence is the owner's text from the old modules; nothing here grades."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.biochemical_feasibility_evidence.literature_reaction_calculations import (
    BUDGET_BASES, CONDITIONAL_CODES, RATIO_KINDS, RATIO_MODES, RATIO_UNITS, REASONS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.biochemical_feasibility_evidence.reaction_report_contracts import (
    CELLS_MEANING, NATIVE_OBSERVATIONS_MEANING, SEMANTIC_CELLS_MEANING)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.biochemical_feasibility_evidence.literature_reaction_types import (
    EXPERIMENT_TYPES)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_reaction_prompt import (
    REACTION_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_reaction_instructions import (
    lead)

# The calculator's own statement (``literature_reaction_calculations`` module text, owner): signed comparisons are
# proposed conventions, not probabilities.
CONVENTION = 'Signed comparisons are proposed conventions, not probabilities.'


def grader_instructions(family):
    """The grader section of the instructions for a leaf whose lead is ``family`` (``reaction`` or
    ``A110_source``, from ``selected_family``)."""
    text = ('\n' + lead(family) + '\n\nLiterature reaction grading (tools literature_reaction_populate and '
            'literature_reaction_source_populate; sheet literature_reaction_cells, or literature_reaction_semantic_cells '
            'when the dataset or native selection carries source-bound meanings).')
    for name, grader in EXPERIMENT_TYPES.items():
        text += ('\nGrader ' + name + '. Question: ' + grader['question'] + ' Check before filling a cell: '
                 + '; '.join(grader['considerations']) + '. Cells: ' + ', '.join(grader['components'])
                 + '. Combination: ' + grader['combination'])
    text += ('\nAn empty cell carries one named missing reason (' + ', '.join(REASONS) + '); a filled cell names the '
             'conditions it rests on (' + ', '.join(CONDITIONAL_CODES) + '). ' + CONVENTION
             + '\nKept apart: ratio modes ' + ', '.join(RATIO_MODES) + '; ratio kinds ' + ', '.join(RATIO_KINDS)
             + '; ratio units ' + ', '.join(RATIO_UNITS) + '; budget bases ' + ', '.join(BUDGET_BASES) + '.'
             + '\nliterature_reaction_cells: ' + CELLS_MEANING
             + '\nliterature_reaction_semantic_cells: ' + SEMANTIC_CELLS_MEANING
             + '\nNative observations: ' + NATIVE_OBSERVATIONS_MEANING
             + '\n' + REACTION_TASK + '\n')
    return text
