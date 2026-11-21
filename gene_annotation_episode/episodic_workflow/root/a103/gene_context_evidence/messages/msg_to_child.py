"""The commissions of the A103 head's eight slots, carried from the old ``to_children.py``,
``to_child_gene_context_evidence.py``, ``to_child_published_evidence_assessment.py`` and
``to_child_execution_progress_assessment.py``. The first two (the recursive head and the literature child) were
byte-identical in the old code: the typed assignment the model wrote (``selection['assignment']``) went through the
child binding's ``prepare_assignment``; the monitor's assignment was passed on unchanged. The other four children of the
old ``episode.py`` factories (execution, HPC, resource) were commissioned through the same ``episode_child`` action with
the same typed assignment.

Each slot but the monitor is commissioned with the typed assignment the model wrote for it (the child's own form is
described to the model in ``task.py``) and the child's own values the run's settings fix (``arguments['child_values']``,
put there by ``action``: the old configuration values ``handoff_unit``, ``acquired_record_unit``, ``information_unit``,
``completion_target``; each is a "new field" of the child's form). The parent states what it sends; a field the child
does not declare, a record this episode does not hold or a field the child's form does not admit fails the commission
(rule 1): nothing here checks it.

The monitor (``_monitor``) is commissioned on one outstanding job this episode holds, with controlled values only: the
model names the job by its held handoff record and chooses what the monitor may observe and which measurements return;
this file passes the job's rows in custody (``monitor_assignment_v2``), with a fixed objective and an empty message.
The monitor always returns its credit, finding and check rows.

The recursive head takes this episode's own selection when the model writes "own" for it (the "or your own" of the
assignment text: the canonical record, never a model copy of it), and inherits the proposed annotation of this episode's own task (the old ``prepare_assignment``:
``proposed_annotation_for``), whatever the model wrote. The fact sources the old ``required_return_sources`` required
of the return are selected in addition to what the model selected: for the recursive head ``committed_record_refs``.
The old condition ``annotation_task_required``
holds here always: the proposed annotation of the commission is required (``read_from_parent``)."""
from episode_runtime import ChildMessage

SLOTS = ('gene_context_evidence', 'published_evidence_assessment', 'execution_job_submission',
         'execution_progress_assessment', 'execution_result_acquisition', 'hpc_work_planning',
         'resource_work_submission', 'resource_result_acquisition')
MONITOR_VERSION = 'monitor_assignment_v2'
MONITOR_OBJECTIVE = 'Assess the progress of one outstanding job.'


def required_return_sources(slot, summary):
    """The old ``required_return_sources`` of ``to_children.py``."""
    if slot == 'gene_context_evidence':
        return ('committed_record_refs',)
    return ()


def _monitor(arguments, summary):
    """The commission of the monitor for one outstanding job. The job is passed as records in custody, never by
    name: the handoff row of the job ledger this episode holds (a launch child returned it, or the commissioner
    passed it) and the check rows of that job it holds (earlier monitors returned them in ``check_refs``), as the
    baseline of the new check. A handoff this episode does not hold as an outstanding job fails here with its
    ``KeyError``. ``child_values`` is the monitor's ``information_unit`` from the settings."""
    job = {item['handoff_ref']: item for item in summary['outstanding_jobs']}[arguments['handoff_ref']]
    return ChildMessage(
        objective=MONITOR_OBJECTIVE, message={},
        assignment={'version': MONITOR_VERSION, 'handoff_refs': [job['handoff_ref']],
                    'known_progress_refs': job['record_refs'][1:], 'dependency_handoff_refs': [],
                    'requested_fields': list(arguments['requested_fields']), **arguments['child_values']},
        selection=tuple(arguments['select']))


def msg_to_child(slot, arguments, summary):
    if slot not in SLOTS:
        raise LookupError('gene_context_evidence_child_slot_unknown:' + repr(slot))
    if slot == 'execution_progress_assessment':
        return _monitor(arguments, summary)
    assignment = {**arguments['assignment'], **arguments['child_values']}
    if slot == 'gene_context_evidence' and assignment.get('selection') == 'own':
        # "or your own" (CHILD_ASSIGNMENTS): the parent's own canonical selection, not a model copy of it.
        assignment['selection'] = summary['assignment']['selection']
    if slot == 'gene_context_evidence':
        assignment['proposed_annotation_ref'] = [summary['assignment']['proposed_annotation_ref']]
    selection = list(arguments.get('select', ()))
    selection += [name for name in required_return_sources(slot, summary) if name not in selection]
    return ChildMessage(objective=arguments['objective'], message={'purpose': arguments['purpose']},
                        assignment=assignment, selection=tuple(selection))
