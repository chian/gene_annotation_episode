"""The commission of each child (carried from ``to_child_execution_job_submission.py``,
``to_child_execution_progress_assessment.py``, ``to_child_execution_result_acquisition.py`` and ``episode.py``
``prepare_child_request``).

``launch``: the launch assignment the frozen plan carries (the old ``hpc.plan`` returned it, and the old launch was
admitted only if it equalled it: the commission is built from the plan, so it does), under the names of the launch
child's form: ``version``, ``requests`` (the mapping by resource id), ``immutable_input_versions``, ``constraints``,
the optional ``launch_instructions`` the model selected, and the fields the child's form needs and the old code did
not send (each a "new field" in the carry-over record): ``record_refs`` (the records the planned jobs read, named
here: a pass carries only the records named), ``handoff_unit`` and ``acquired_record_unit`` (from the settings, via
the ``ChildCall`` arguments) and ``received_handoff_resources`` (the resource of a plan whose handoff this episode
already holds). ``hpc_execution_job`` is what the old ``LaunchPreparation.initial_decision_context`` gave the launch
side at its first decision: plan id, objective, the frozen scientific manifest, the acceptance predicates, the
launch input (the artifact holding the plan, which the ledger names and ``record_refs`` passes) and the instruction that reference
files are inputs and not a required procedure. It has no field of the child's assignment form, so it rides in the
message. The old report-contract declaration, the receipt inheritance and the comparison of the launch with the
plan's ledger rows (``authenticate_launch``: one reservation per plan, none after the plan is closed) are old-runner
machinery or moved: ``task.py`` ``action`` rejects a second launch of a plan and a launch of a closed plan, and the
system's unit journal is the one record of a launch. A plan this episode does not hold raises ``StopIteration``: a
wrong commission fails.

``monitor``: the monitor assignment passed unchanged (the old ``prepare_request``: the child's form admits it) with
the information unit. ``results``: the results assignment as selected under the names of the results child's form;
the kind and the workspace of the handed-off target are those of the plan whose launch returned that handoff (the old
child read them from the handoff target), with the one handoff record in custody and the acquired-record unit."""
from episode_runtime import ChildMessage

from ..task import LAUNCH_JOB_INSTRUCTIONS, LAUNCH_SELECTION, MONITOR_SELECTION, RESULTS_SELECTION

INITIAL_REPORT = 'nothing yet'


def msg_to_child(slot, arguments, summary):
    if slot == 'launch':
        view = summary['ledger_view']
        plan = next(item for item in view['plans'] if item['plan_ref'] == arguments['plan_ref'])
        launch = plan['launch_assignment']
        resource_id = view['commission']['resource_id']
        handed_off = [resource_id] if any(item['handoff_refs'] for item in summary['launches']
                                          if item['plan_ref'] == plan['plan_ref']) else []
        job = {'plan_id': plan['plan_id'], 'objective': view['commission']['objective'],
               'scientific_manifest': plan['manifest'], 'scientific_acceptance': view['commission']['obligations'],
               'launch_input_ref': plan['launch_input_ref'], 'instructions': LAUNCH_JOB_INSTRUCTIONS}
        assignment = {'version': launch['version'], 'requests': launch['requests'],
                      'immutable_input_versions': launch['immutable_input_versions'],
                      'constraints': launch['constraints'],
                      'record_refs': [*summary['input_refs'], plan['launch_input_ref']],
                      'handoff_unit': arguments['handoff_unit'],
                      'acquired_record_unit': arguments['acquired_record_unit'],
                      'received_handoff_resources': handed_off}
        if 'launch_instructions' in arguments:
            assignment['launch_instructions'] = arguments['launch_instructions']
        return ChildMessage(
            objective='Launch the frozen plan ' + plan['plan_id'] + ' on resource ' + resource_id
                      + ' and return its usable handoff',
            message={'initial_report': INITIAL_REPORT, 'plan_ref': plan['plan_ref'], 'hpc_execution_job': job},
            assignment=assignment, selection=LAUNCH_SELECTION)
    if slot == 'monitor':
        return ChildMessage(
            objective='Report the state of execution target ' + arguments['target_handle'],
            message={'initial_report': INITIAL_REPORT},
            assignment={'version': 'monitor_assignment', 'target_handle': arguments['target_handle'],
                        'requested_fields': list(arguments['requested_fields']),
                        'known_progress_refs': list(arguments.get('known_progress_refs', [])),
                        'permitted_committed_record_types': list(arguments['permitted_committed_record_types']),
                        'information_unit': arguments['information_unit']},
            selection=MONITOR_SELECTION)
    if slot == 'results':
        handoff_ref = arguments['handoff_ref']
        view = summary['ledger_view']
        launched = next(item for item in summary['launches'] if handoff_ref in item['handoff_refs'])
        plan = next(item for item in view['plans'] if item['plan_ref'] == launched['plan_ref'])
        kind = next(iter(plan['launch_assignment']['requests'].values()))['resource_kind']
        assignment = {'handoff_ref': [handoff_ref], 'selector': arguments['selector'], 'resource_kind': kind,
                      'workspace': plan['manifest']['workspace'],
                      'acquired_record_unit': arguments['acquired_record_unit']}
        if 'constraints' in arguments:
            assignment['constraints'] = arguments['constraints']
        return ChildMessage(objective='Acquire the requested results of the handed-off execution',
                            message={'initial_report': INITIAL_REPORT}, assignment=assignment,
                            selection=RESULTS_SELECTION)
    raise LookupError('hpc_allocation_execution_has_no_slot:' + slot)
