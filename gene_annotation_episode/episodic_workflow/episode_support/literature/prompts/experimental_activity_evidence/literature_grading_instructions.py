"""The owner's A105 grading instructions as one section of a grading episode's decision instructions.

Old delivery (``prompts/literature_task_selection.py`` and ``tools/literature_task_families.py`` at ``97308b94c``):
the grader-selection hierarchy and its table of the eight graders (``A105_ASSAY_SELECTION_TASK``), the reusable
assay grader's filling instruction (``ASSAY_GRADING_TASK``), and the filling instruction of each sheet family whose
population is offered (the A105 family table, including the across-experiment aggregation rules when
``literature.a105.aggregate`` is offered). Each grading episode's ``decide`` shows this section."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_assay_grading_prompt import (
    ASSAY_GRADING_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_assay_selection_prompt import (
    A105_ASSAY_SELECTION_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_task_families import (
    family_tasks)

GRADING_HEADING = ('\n\nA105 grading. The reason tool carries the grader arguments in evidence_processing.gradings '
                   '(literature.assay_grading.populate arguments, JSON-encoded).\n')
# How a quantity the examined source prints is entered in the grader arguments. The argument object reaches the model
# only as a JSON schema inside the description of the JSON-encoded ``arguments`` string, where the ``source_number``
# form (byte witnesses and in-witness character positions) has no example; a model that had read every number of a
# table answered with every quantity null (docs/axis_restructure_20261117/BRANCH_RUNS_a105.md). AGENTS.md: a missing
# measurement is graded partial or unresolved; a measurement the source states is not missing.
QUANTITY_ENTRY = (
    'Entering the quantities of a grading. The arguments string is the JSON encoding of one object with the keys '
    'source_ref, source_kind, assay_type, assertion_ref, experiment_ref, quantity_kind, quantities, interpretations '
    'and prediction_model. quantities has the nine keys effect, effect_variance, recovery, attributed_signal, '
    'total_signal, condition_test, condition_reference, assertion_prediction and alternative_prediction; each is one '
    'operand or null. null means that the examined source does not state that quantity for this experiment. It is '
    'never a shortcut for a quantity you have read: enter every one of the nine that the examined bytes state. A '
    'sheet whose quantities are null although the examined bytes print them is a wrong grading, not a partial one. '
    'The same holds for interpretations: unknown is for a criterion the examined source does not settle, supported or '
    'conflicting for one it does, each with the anchored reference that shows it.\n'
    'A quantity printed as a number directly followed by its unit is entered as a source_number. It names bytes of '
    'the source and never carries a typed value: {"kind":"source_number","number":{"witness":{"source_ref":S,'
    '"representation":R,"start":a,"end":b},"number_start":i,"number_end":j},"unit":{"source_ref":S,'
    '"representation":R,"start":c,"end":d},"origin":"reported"}. The witness [a,b) is a byte interval of the source '
    'that contains the number, for example the printed phrase with its label. number_start and number_end are '
    'character positions inside that witness (0 is its first character) that enclose exactly the number. The unit '
    '[c,d) is the byte interval of the unit printed directly after the number, with nothing but whitespace between '
    'them. Example: source_locate of the needle "activity 4.2 U/mg" returns a match whose witness has start 2310 and '
    'end 2327; the operand is then number.witness start 2310 end 2327, number_start 9, number_end 12 (the characters '
    '4.2) and unit start 2323 end 2327 (the bytes U/mg). Take byte offsets from a source_locate match, or from the '
    'start offset of a source_read window whose text is plain ASCII (byte offset = window start + character '
    'position); do not guess them. origin is reported for a value the source reports, proposed for a value the '
    'source only proposes, synthetic for a constructed fixture value. An operand the host cannot read comes back as '
    'an invalid outcome that names the field: correct that operand and commit again; do not replace it by null.\n'
    'Committing the interpretation with its grading. A reason that fails saves nothing and earns nothing; its '
    'outcome names the error: correct exactly that and commit again. Every observation, every assessment and every '
    'new source_subjects row of reference_type assay or literature_result in the commit must be covered by a '
    'grading of the same commit: the grading names the assay as experiment_ref, the observation names that assay in '
    'source_subject_refs, and the assessment names the observation and the hypothesis that is the assertion_ref. '
    'For an experiment that already has a reference record (a commissioned experiment), use that reference and do '
    'not create a second one; do not create an assay or literature_result row for something you do not grade. A '
    'label must occur literally in the bytes of its anchor: choose the anchor, then copy the label from inside '
    'it.\n')


def grading_section(population_tools=()):
    """The grading section: how a printed quantity is entered, the selection hierarchy and grader table, the assay
    grader's instruction, and the instruction of each offered population family other than the grader itself
    (library tool names)."""
    families = family_tasks(tuple(tool for tool in population_tools if tool != 'literature.assay_grading.populate'))
    text = GRADING_HEADING + QUANTITY_ENTRY + A105_ASSAY_SELECTION_TASK + '\n\n' + ASSAY_GRADING_TASK
    if families:
        text += '\n\nSheet families offered as population tools:\n' + '\n\n'.join(families)
    return text + '\n'


__all__ = ['grading_section']
