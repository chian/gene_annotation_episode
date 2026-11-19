"""Credit: the A104 credit projector of the commissioned task over the records this episode holds.

The old ``credit.py`` (``credit_projector``, ``credit_view``) and ``task_projector.py`` (``original_task_projector``)
chose the projector from the original assignment's ``context.a104_task`` name: ``panel_identity`` is
``A104PanelIdentityCredit``, ``alignment_suitability`` is ``A104AlignmentSuitabilityCredit``, ``robustness`` is
``A104RobustnessCredit`` and no task (or any other task of the old ``TASKS``) is ``A104EvolutionaryCredit``. The
projectors are library classes (``episode_support/grading/evolutionary_history_evidence/credit.py``) called with this
episode's own pieces: the held records (``records``), the Store scope of the commission and the proposed annotation.
The old credit view was a record, not a number: ``credit`` returns its number, ``internal_summary`` shows the rest.

BLOCKED-ON-STORE-ACCESS (library not carried): the projectors read the Store through ``store.read_snapshot``,
``store.db`` (``a104_native_requests``, ``a104_native_results``) and the old ``known_record_refs`` receipts. The call
stays as written; ``records`` is what the final API offers (it has no ``read_snapshot``)."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.credit import (
    A104AlignmentSuitabilityCredit, A104EvolutionaryCredit, A104PanelIdentityCredit, A104RobustnessCredit)

TASK_PROJECTORS = {'panel_identity': A104PanelIdentityCredit, 'alignment_suitability': A104AlignmentSuitabilityCredit,
                   'robustness': A104RobustnessCredit}


def credit_projector(parent_input):
    """The old ``original_task_projector``, over the parent input (the task is read by ``read_from_parent``).

    The three named tasks select their projector; no task, or any other task name, is ``A104EvolutionaryCredit``
    (the old ``.get(name, A104EvolutionaryCredit)``). The old check of the name against ``TASKS`` and of
    ``allowed_tasks`` was a check of the commission (a wrong commission just fails) and is not carried."""
    task = parent_input['a104_task']
    if task is None:
        return A104EvolutionaryCredit()
    return TASK_PROJECTORS.get(task.get('name'), A104EvolutionaryCredit)()


def credit_view(summary, records):
    """The projector's view of the held records: ``credit``, ``target_sheets``, ``source_contributions`` ..."""
    scope = summary['scope']
    assignment = {'scope': scope, 'proposed_annotation_ref': summary['proposed_annotation_ref'],
                  'evidence_refs': summary['evidence_refs'], 'context': summary['context']}
    return credit_projector(summary)(records, scope, known_record_refs=list(records.refs()), assignment=assignment)


def credit(summary, records):
    value = credit_view(summary, records)['credit']
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('a104_credit_must_be_finite')
    return float(value)
