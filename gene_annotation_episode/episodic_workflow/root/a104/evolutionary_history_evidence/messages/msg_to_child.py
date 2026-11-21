"""The commission of each child: its objective, its message, the assignment its own form requires, every record this
episode names for it and the selectable return fields this commission wants.

Carried from the old ``to_child_*.py`` (``assemble_request``, ``prepare_parent_request``, ``prepare_request``,
``required_return_sources``) and the old ``from_parent.prepare_assignment`` / ``prepare_invocation``. What an old
assembler did that was a check of a commission is not carried (rule 1: a wrong commission fails): the child role is
allowed (``allowed_child_roles``), the closed-commission replay and its identity checks, the monitor assignment
against the monitor contract (``prepare_request``), the HPC-launch handoff field requirement, the initial report
against the interpretation schema, the revision preparation against the journal (``_validate_origin``), and the
refusal of a proposed annotation that differs from the inherited one (this episode copies its own). The runner's
machinery (``EpisodeGoal``, ``EpisodeRequest``, ``Episode.identity``, ``receipts.bind``, the knowledge inheritance,
the ``inprocess_completion_order``, the ``scientific_invocation_ref`` of the message) is the system's now.

The ``ChildCall`` arguments are what ``task.py`` built from the model's selection: ``objective``, ``purpose``,
``scope``, ``initial_report`` (optional), ``assignment`` and ``return_fields``. The own slot and ``hpc`` are the
children the model is offered; the slots ``launch``, ``results`` and ``literature`` carry the old assemblers with
the child's own assignment in ``assignment`` as the old ``episode_assignment`` (their old yield/handoff units ride
in it). The ``monitor`` slot is commissioned on a job this episode holds (``_monitor``): its ``ChildCall`` arguments
are ``handoff_ref`` (the held handoff row of the job), ``requested_fields``, ``information_unit`` and
``return_fields``."""
from episode_runtime import ChildMessage

OWN = 'evolutionary_history_evidence'
# What a head asks of a child of its own kind: the records its interpretations committed.
RECORD_SOURCE = 'committed_record_refs'


def _unique(refs):
    return list(dict.fromkeys(refs))


def _message(arguments):
    return {'purpose': arguments['purpose'], 'initial_report': arguments.get('initial_report', {})}


def _monitor(arguments, summary):
    """The commission of the monitor for one outstanding job. The job is passed as records in custody, never by
    name: the handoff row of the job ledger this episode holds (the launch child returned it in
    ``execution_handoff_refs``, or the commissioner passed it back) and the check rows of that job it holds
    (earlier monitors returned them in ``check_refs``), as the baseline of the new check. A handoff this episode
    does not hold as an outstanding job fails here with its ``KeyError``. The monitor's required fields (credit,
    finding, check rows) are always returned; ``return_fields`` selects its measurements."""
    job = {item['handoff_ref']: item for item in summary['outstanding_jobs']}[arguments['handoff_ref']]
    return ChildMessage(
        objective='Assess the progress of job ' + job['job'] + '.', message={},
        assignment={'version': 'monitor_assignment_v2', 'handoff_refs': [job['handoff_ref']],
                    'known_progress_refs': job['record_refs'][1:], 'dependency_handoff_refs': [],
                    'requested_fields': list(arguments['requested_fields']),
                    'information_unit': arguments['information_unit']},
        selection=tuple(_unique(arguments['return_fields'])))


def msg_to_child(slot, arguments, summary):
    if slot == 'monitor':
        return _monitor(arguments, summary)
    message = _message(arguments)
    wanted = list(arguments['return_fields'])
    if slot == OWN:
        assignment = {**arguments['assignment'], 'scope': arguments['scope']}
        # prepare_assignment: the child inherits the proposed annotation of its parent.
        proposed = summary['proposed_annotation_ref']
        if proposed is not None:
            assignment['proposed_annotation_ref'] = proposed
        # every record the child's code reads: the proposed annotation, the subjects of its scope and the records
        # the model names beside the evidence (T5: a pass carries only the records named)
        assignment['record_refs'] = _unique([*([proposed] if proposed is not None else []),
                                             *arguments['scope']['subject_refs'], *summary['record_refs']])
        required = [RECORD_SOURCE]
        selection = tuple(_unique([*required, *wanted]))
    elif slot == 'hpc':
        assignment = {**arguments['assignment'], 'scope': arguments['scope']}
        selection = tuple(_unique(wanted))
    else:
        # launch, results, literature: the old assemblers took the child's own assignment as written
        assignment = dict(arguments['assignment'])
        selection = tuple(_unique(wanted))
    return ChildMessage(objective=arguments['objective'], message=message, assignment=assignment,
                        selection=selection)
