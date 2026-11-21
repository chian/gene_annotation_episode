"""The commission of each child (carried from ``to_child_execution_job_submission.py``,
``to_child_execution_progress_assessment.py``, ``to_child_execution_result_acquisition.py``,
``to_child_hpc_work_planning.py``, ``to_child_biochemical_feasibility_evidence.py`` and ``child_commissioning.py``).
Written against the finished ``goal.py``, ``messages/read_from_parent.py`` and ``messages/final_to_parent.py`` of the
four child folders, read as data, and the recursive commission against this episode's own form.

The old ``assemble_request`` envelopes (the child goal, the result contract written by the parent, the report
contract declaration, ``inprocess_completion_order``, ``knowledge_inheritance``, the receipts and the invocation
reference) are old-runner machinery. What each sent of its own is kept: the objective and the purpose (the old
``goal_text`` and ``purpose``), the assignment the model chose, the scope and the launch instructions. The parent
now selects return fields (``selection``): the facts the model lists in the commission. The monitor is commissioned
on one job this episode holds as outstanding (``summary['outstanding_jobs']``), named by its held handoff reference:
its assignment (``monitor_assignment_v2``) passes the job's handoff row and the check rows held of it in custody;
its credit, finding and check rows (``check_refs``) are always returned (the old forced ``monitoring_progress_refs``
is that). Every record the child's code reads is named in a ``record_refs`` field, because a pass carries only the
records named.

A wrong commission fails (rule 1): a slot that is not declared, an assignment key that is missing, a record that
this episode does not hold and a fact the child does not declare as selectable each raise where the child is built.
The old checks of the commission (``prepare_child_request`` validating the monitor assignment against the child's
``_ASSIGNMENT``, the proposed annotation inherited and equal, ``authenticate_launch``) are not carried.

New fields (listed in the carry-over record): the launch child's ``record_refs``, ``handoff_unit``,
``acquired_record_unit`` and ``scientific_task``; the results child's ``resource_kind`` and ``acquired_record_unit``;
the monitor child's ``information_unit``; the hpc child's ``scope`` and ``input_refs``; this episode's own ``scope``
and ``received_record_refs``."""
from episode_runtime import ChildMessage

LAUNCH_VERSION = 'execution_launch_assignment_v1'
RESULTS_VERSION = 'execution_results_assignment_v1'
MONITOR_VERSION = 'monitor_assignment_v2'


def _selection(arguments, *forced):
    return tuple(dict.fromkeys([*forced, *arguments.get('facts', ())]))


def _message(arguments):
    return {'purpose': arguments['purpose']}


def msg_to_child(slot, arguments, summary):
    if slot == 'launch':
        given = arguments['assignment']
        assignment = {'version': LAUNCH_VERSION, 'requests': given['requests'],
                      'immutable_input_versions': given['immutable_input_versions'],
                      'constraints': given['constraints'], 'handoff_unit': arguments['handoff_unit'],
                      'acquired_record_unit': arguments['acquired_record_unit'],
                      'record_refs': list(arguments.get('input_refs', [])),
                      'scientific_task': {'scientific_question': summary['goal']['objective'],
                                          'selected_tool_info': summary['selection']['child_tool_info']}}
        for key in ('launch_instructions', 'received_handoff_resources'):
            if key in given:
                assignment[key] = given[key]
        return ChildMessage(objective=arguments['objective'], message=_message(arguments), assignment=assignment,
                            selection=_selection(arguments))
    if slot == 'monitor':
        # The job is passed as records in custody, never by name: the handoff row of the job ledger this episode
        # holds and the check rows of that job it holds (earlier monitors returned them in ``check_refs``), as the
        # baseline of the new check. A handoff this episode does not hold as an outstanding job fails here with its
        # ``KeyError``. Nothing the model wrote passes: the objective names the job by its handle.
        job = {item['handoff_ref']: item for item in summary['outstanding_jobs']}[arguments['handoff_ref']]
        assignment = {'version': MONITOR_VERSION, 'handoff_refs': [job['handoff_ref']],
                      'known_progress_refs': job['record_refs'][1:], 'dependency_handoff_refs': [],
                      'requested_fields': list(arguments['requested_fields']),
                      'information_unit': arguments['information_unit']}
        return ChildMessage(objective='Assess the progress of job ' + job['job'] + '.', message={},
                            assignment=assignment, selection=_selection(arguments))
    if slot == 'results':
        assignment = {'version': RESULTS_VERSION, 'handoff_ref': [arguments['handoff_ref']],
                      'selector': arguments['selector'], 'resource_kind': arguments['resource_kind'],
                      'acquired_record_unit': arguments['acquired_record_unit']}
        return ChildMessage(objective=arguments['objective'], message=_message(arguments), assignment=assignment,
                            selection=_selection(arguments))
    if slot == 'hpc':
        assignment = {'scope': summary['scope'], 'input_refs': list(arguments['input_refs'])}
        if 'commission_id' in arguments:
            assignment['commission_id'] = arguments['commission_id']
        if 'commission_source_ref' in arguments:
            assignment['commission_source_ref'] = [arguments['commission_source_ref']]
        if 'tool_request' in arguments:
            assignment['tool_request'] = arguments['tool_request']
        return ChildMessage(objective=arguments['objective'], message=_message(arguments), assignment=assignment,
                            selection=_selection(arguments))
    if slot == 'biochemical_feasibility_evidence':
        given = arguments['assignment']
        # The proposed annotation is inherited from this episode (the old ``prepare_assignment``), with the context
        # of the original task; every record this episode names for the child is passed.
        assignment = {'selection': given['selection'], 'proposed_annotation_ref': [summary['proposed_annotation_ref']],
                      'evidence_refs': list(given['evidence_refs']), 'constraints': given['constraints'],
                      'context': given.get('context', summary['context']), 'scope': summary['scope'],
                      'received_record_refs': list(dict.fromkeys([*summary['received_record_refs'],
                                                                  *arguments.get('received_record_refs', [])]))}
        if 'revision_origin' in given:
            assignment['revision_origin'] = given['revision_origin']
        return ChildMessage(objective=arguments['objective'], message=_message(arguments), assignment=assignment,
                            selection=_selection(arguments))
    raise LookupError('biochemical_feasibility_evidence_has_no_slot:' + slot)
