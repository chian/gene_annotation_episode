"""The commission of each child (carried from ``to_child_execution_job_submission.py``,
``to_child_execution_progress_assessment.py`` and ``episode.py`` ``prepare_child_request``).

``launch``: the launch assignment the frozen plan carries (the old ``hpc.plan`` returned it, and the old launch was
admitted only if it equalled it: the commission is built from the plan, so it does) with the fields the launch
child's form needs and the old code did not send (each a "new field" in the carry-over record): ``scope``,
``input_refs`` (named here: a pass carries only the records named), ``handoff_unit`` (from the settings, via the
``ChildCall`` arguments) and ``already_handed_off`` (the resource of a plan whose handoff this episode already
holds). ``hpc_execution_job`` is what the old ``LaunchPreparation.initial_decision_context`` gave the launch side
at its first decision: plan id, objective, the frozen scientific manifest, the acceptance predicates, the local
input file holding the plan (``hpc_plan`` wrote it), the coordinator workspace and the instruction that reference
files are inputs and not a required procedure. The child declares ``requests`` as a list and
``immutable_input_versions`` as a record where the plan carries a mapping by resource id and a list: the mapping's
values are sent, and a non-empty list of versions fails the commission.

``monitor``: the monitor assignment passed unchanged (the old ``prepare_request``; the child's form admits it) with
the information unit. ``results``: the results assignment as selected, with the one handoff record in custody and
the acquired-record unit. The old report-contract declaration, the receipt inheritance and the comparison of the
launch with the plan's ledger rows (``authenticate_launch``: one reservation per plan, none after the plan is
closed) are old-runner machinery or moved: ``task.py`` ``action`` rejects a second launch of a plan and a launch of
a closed plan, and the system's unit journal is the one record of a launch. A plan this episode does not hold
raises ``StopIteration``: a wrong commission fails."""
from episode_runtime import ChildMessage

from ..task import LAUNCH_JOB_INSTRUCTIONS, LAUNCH_SELECTION, MONITOR_SELECTION, RESULTS_SELECTION

INITIAL_REPORT = 'nothing yet'
RESULTS_VERSION = 'execution_results_assignment_v1'


def msg_to_child(slot, arguments, summary):
    if slot == 'launch':
        view = summary['ledger_view']
        plan = next(item for item in view['plans'] if item['plan_ref'] == arguments['plan_ref'])
        launch = plan['launch_assignment']
        if launch['immutable_input_versions']:
            raise ValueError('immutable_input_versions_list_is_not_a_record_of_the_launch_child')
        resource_id = view['commission']['resource_id']
        handed_off = [resource_id] if any(item['handoff_refs'] for item in summary['launches']
                                          if item['plan_ref'] == plan['plan_ref']) else []
        job = {'plan_id': plan['plan_id'], 'objective': view['commission']['objective'],
               'scientific_manifest': plan['manifest'], 'scientific_acceptance': view['commission']['obligations'],
               'supplied_input_file': plan['supplied_input_file'],
               'coordinator_workspace': view['coordinator_workspace'], 'instructions': LAUNCH_JOB_INSTRUCTIONS}
        return ChildMessage(
            objective='Launch the frozen plan ' + plan['plan_id'] + ' on resource ' + resource_id
                      + ' and return its usable handoff',
            message={'initial_report': INITIAL_REPORT, 'plan_ref': plan['plan_ref']},
            assignment={'version': launch['version'], 'requests': list(launch['requests'].values()),
                        'immutable_input_versions': {}, 'constraints': launch['constraints'],
                        'scope': summary['scope'], 'input_refs': list(summary['input_refs']),
                        'handoff_unit': arguments['handoff_unit'], 'already_handed_off': handed_off,
                        'hpc_execution_job': job},
            selection=LAUNCH_SELECTION)
    if slot == 'monitor':
        return ChildMessage(
            objective='Report the state of execution target ' + arguments['target_handle'],
            message={'initial_report': INITIAL_REPORT},
            assignment={'version': 'monitor_assignment_v1', 'target_handle': arguments['target_handle'],
                        'requested_fields': list(arguments['requested_fields']),
                        'known_progress_refs': list(arguments.get('known_progress_refs', [])),
                        'permitted_committed_record_types': list(arguments['permitted_committed_record_types']),
                        'information_unit': arguments['information_unit']},
            selection=MONITOR_SELECTION)
    if slot == 'results':
        assignment = {'version': RESULTS_VERSION, 'handoff_ref': [arguments['handoff_ref']],
                      'selector': arguments['selector'], 'acquired_record_unit': arguments['acquired_record_unit']}
        if 'known_result_refs' in arguments:
            assignment['known_result_refs'] = list(arguments['known_result_refs'])
        return ChildMessage(objective='Acquire the requested results of the handed-off execution',
                            message={'initial_report': INITIAL_REPORT}, assignment=assignment,
                            selection=RESULTS_SELECTION)
    raise LookupError('hpc_allocation_execution_has_no_slot:' + slot)
