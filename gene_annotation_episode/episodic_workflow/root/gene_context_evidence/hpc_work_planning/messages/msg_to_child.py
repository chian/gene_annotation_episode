"""The commission of each child (carried from ``to_child_hpc_resource_prediction.py``,
``to_child_hpc_allocation_execution.py``, ``to_child_execution_job_submission.py`` (``LaunchPreparation.
initial_decision_context``), ``to_child_execution_progress_assessment.py`` and ``episode.py``
``prepare_child_request``).

``hpc_prediction`` and ``hpc_execution``: the same commission identity as this episode's own, and this episode as the
ledger owner (the old requests carried ``owner_episode_id``). The old checks that the parent has the role ``hpc`` and
is the named owner are not made (a wrong commission fails). New fields the execution sister's form requires (each is
a "new field" in the carry-over record): ``commission`` (the commission this episode's ledger holds), ``scope`` and
``ledger_credit`` (the credit of the ledger as this episode last saw it). The prediction sister's form takes the
identity and the owner only.

``launch``: the launch assignment the frozen plan carries (the old ``hpc.plan`` returned it, and the old launch was
admitted only if it equalled it: the commission is built from the plan, so it does) with the fields the launch child's
form takes and the old code did not send: ``input_refs`` (named here: a pass carries only the records named),
``handoff_unit`` (from the settings, via the ``ChildCall`` arguments) and ``already_handed_off_resource_ids`` (the
resource of a plan whose handoff this episode already holds). ``hpc_execution_job`` is what the old
``LaunchPreparation.initial_decision_context`` gave the launch side at its first decision: plan id, objective, the
frozen scientific manifest, the acceptance predicates, the local input file holding the plan (``hpc_plan`` wrote it),
the coordinator workspace and the instruction that reference files are inputs and not a required procedure; it rides
in the message.

``monitor``: the monitor assignment passed unchanged (the old ``prepare_request``; the child's form admits it) with
the information unit. ``results``: the results assignment as selected, with the one handoff record the plan has
attached (in custody), the kind of the resource, the workspace of the handoff target (the plan's, which the handoff
had to equal) and the acquired-record unit; sources this episode published and names as known are passed with their
artifacts. The old report-contract declaration, the receipt inheritance and the comparison of the launch with the
plan's ledger rows (``authenticate_launch``: one reservation per plan, none after the plan is closed) are old-runner
machinery or moved: ``task.py`` ``action`` rejects a second launch of a plan and a launch of a closed plan, and the
system's unit journal is the one record of a launch. A plan this episode does not hold raises ``StopIteration``: a
wrong commission fails."""
from episode_runtime import ChildMessage

from ..task import (EXECUTION_SELECTION, LAUNCH_JOB_INSTRUCTIONS, LAUNCH_SELECTION, MONITOR_SELECTION,
                    PREDICTION_SELECTION, RESULTS_SELECTION)

INITIAL_REPORT = 'nothing yet'
RESULTS_VERSION = 'execution_results_assignment'


def identity_of(summary):
    identity = summary['commission_identity']
    if 'commission_id' in identity:
        return {'commission_id': identity['commission_id']}
    return {'commission_source_ref': [identity['commission_source_ref']]}


def sister_message(summary):
    message = {'initial_report': INITIAL_REPORT}
    selected = summary['message'].get('launch_instructions')
    if selected is not None:
        message['launch_instructions'] = selected
    return message


def msg_to_child(slot, arguments, summary):
    if slot == 'hpc_prediction':
        return ChildMessage(objective='Improve the prediction model of the ledger owned by ' +
                            summary['owner_episode_id'], message=sister_message(summary),
                            assignment={'owner_episode_id': summary['owner_episode_id'], **identity_of(summary),
                                        'ledger': summary['ledger_view']['ledger']},
                            selection=PREDICTION_SELECTION)
    if slot == 'hpc_execution':
        assignment = {'owner_episode_id': summary['owner_episode_id'], **identity_of(summary),
                      'ledger': summary['ledger_view']['ledger'],
                      'commission': summary['ledger_view']['commission'], 'scope': summary['scope'],
                      'ledger_credit': summary['ledger_credit']}
        return ChildMessage(objective='Turn the commission of the ledger owned by ' + summary['owner_episode_id']
                            + ' into work done on a real allocation', message=sister_message(summary),
                            assignment=assignment, selection=EXECUTION_SELECTION)
    if slot == 'launch':
        view = summary['ledger_view']
        plan = next(item for item in view['plans'] if item['plan_ref'] == arguments['plan_ref'])
        launch = plan['launch_assignment']
        resource_id = view['commission']['resource_id']
        handed_off = [resource_id] if any(item['handoff_refs'] for item in summary['launches']
                                          if item['plan_ref'] == plan['plan_ref']) else []
        job = {'plan_id': plan['plan_id'], 'objective': view['commission']['objective'],
               'scientific_manifest': plan['manifest'], 'scientific_acceptance': view['commission']['obligations'],
               'supplied_input_file': plan['supplied_input_file'],
               'coordinator_workspace': view['coordinator_workspace'], 'instructions': LAUNCH_JOB_INSTRUCTIONS}
        assignment = {'version': launch['version'], 'requests': launch['requests'],
                      'immutable_input_versions': launch['immutable_input_versions'],
                      'constraints': launch['constraints'], 'input_refs': list(summary['input_refs']),
                      'handoff_unit': arguments['handoff_unit'], 'already_handed_off_resource_ids': handed_off}
        selected = summary['message'].get('launch_instructions')
        if selected is not None:
            assignment['launch_instructions'] = selected
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
                        'known_progress_refs': list(arguments['known_progress_refs']),
                        'permitted_committed_record_types': list(arguments['permitted_committed_record_types']),
                        'information_unit': arguments['information_unit']},
            selection=MONITOR_SELECTION)
    if slot == 'results':
        plan = next(item for item in summary['ledger_view']['plans'] if item['plan_ref'] == arguments['plan_ref'])
        assignment = {'version': RESULTS_VERSION, 'handoff_ref': [plan['handoff_ref']],
                      'selector': arguments['selector'], 'resource_kind': 'hpc', 'workspace': plan['workspace'],
                      'acquired_record_unit': arguments['acquired_record_unit']}
        known = list(arguments.get('known_result_refs', []))
        if known:
            assignment['initial_result_refs'] = known
            assignment['initial_result_artifact_refs'] = [summary['result_artifacts'][ref] for ref in known]
        return ChildMessage(objective='Acquire the requested results of the handed-off execution',
                            message={'initial_report': INITIAL_REPORT}, assignment=assignment,
                            selection=RESULTS_SELECTION)
    raise LookupError('hpc_work_planning_has_no_slot:' + slot)
