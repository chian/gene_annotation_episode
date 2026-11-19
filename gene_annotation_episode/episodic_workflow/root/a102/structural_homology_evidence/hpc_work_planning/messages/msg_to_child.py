"""The commission of each child (carried from ``to_child_hpc_resource_prediction.py``,
``to_child_hpc_allocation_execution.py``, ``to_child_execution_job_submission.py`` (``LaunchPreparation.
initial_decision_context``), ``to_child_execution_progress_assessment.py`` and ``episode.py``
``prepare_child_request``).

``hpc_prediction`` and ``hpc_execution``: the same commission identity as this episode's own, and this episode as the
ledger owner (the old requests carried ``owner_episode_id``). The old checks that the parent has the role ``hpc`` and
is the named owner are not made (a wrong commission fails). New fields the children's forms require (each is a "new
field" in the carry-over record): ``hpc_prediction``: ``ledger_refs`` and ``yield_binding`` (the commission's
``yield_bindings['hpc_prediction']``, which the child's controller cannot read from a ledger); ``hpc_execution``:
``scope`` and ``input_refs``.

``launch``: the launch assignment the frozen plan carries (the old ``hpc.plan`` returned it, and the old launch was
admitted only if it equalled it: the commission is built from the plan, so it does) with the fields the launch child's
form needs and the old code did not send: ``scope``, ``input_refs`` (named here: a pass carries only the records
named), ``handoff_unit`` (from the settings, via the ``ChildCall`` arguments) and ``already_handed_off_resource_ids``
(the resource of a plan whose handoff this episode already holds). ``hpc_execution_job`` is what the old
``LaunchPreparation.initial_decision_context`` gave the launch side at its first decision: plan id, objective, the
frozen scientific manifest, the acceptance predicates, the local input file holding the plan (``hpc_plan`` wrote it),
the coordinator workspace and the instruction that reference files are inputs and not a required procedure; it rides
in the message.

``monitor``: the monitor assignment passed unchanged (the old ``prepare_request``; the child's form admits it) with
the information unit. ``results``: the results assignment as selected, with the one handoff record in custody, the
kind of the resource and the acquired-record unit. The old report-contract declaration, the receipt inheritance and
the comparison of the launch with the plan's ledger rows (``authenticate_launch``: one reservation per plan, none
after the plan is closed) are old-runner machinery or moved: ``task.py`` ``action`` rejects a second launch of a plan
and a launch of a closed plan, and the system's unit journal is the one record of a launch. A plan this episode does
not hold raises ``StopIteration``: a wrong commission fails."""
from episode_runtime import ChildMessage

from ..task import (EXECUTION_SELECTION, LAUNCH_JOB_INSTRUCTIONS, LAUNCH_SELECTION, MONITOR_SELECTION,
                    PREDICTION_SELECTION, RESULTS_SELECTION)

INITIAL_REPORT = 'nothing yet'
RESULTS_VERSION = 'execution_results_assignment_v1'
BLOCKED = 'BLOCKED-ON-JOB-SERVICE: '


def ledger_refs(summary):
    """The records of this episode's ledger the prediction sister reads, passed in custody.

    BLOCKED-ON-JOB-SERVICE: HPC ledger evidence record and HPC ledger credit record (this episode's ledger is the
    library's ``HPCLedger`` SQLite file: no job record kind or work table is declared, so there is no record to name);
    wanted call: ``[row['id'] for row in records.table(HPC_LEDGER).select({'owner': owner})]`` and the same over
    ``HPC_CREDITS``, read in ``internal_summary`` and passed here."""
    raise NotImplementedError(BLOCKED + 'HPC ledger evidence record and HPC ledger credit record; wanted call: '
                              "[row['id'] for row in records.table(HPC_LEDGER).select({'owner': owner})] and "
                              "[row['id'] for row in records.table(HPC_CREDITS).select({'owner': owner})]")


def msg_to_child(slot, arguments, summary):
    if slot == 'hpc_prediction':
        commission = summary['ledger_view']['commission']
        identity = summary['commission_identity']
        assignment = {'owner_episode_id': summary['owner_episode_id'], 'ledger_refs': ledger_refs(summary),
                      'yield_binding': commission['yield_bindings']['hpc_prediction']}
        if 'commission_id' in identity:
            assignment['commission_id'] = identity['commission_id']
        else:
            assignment['commission_source_ref'] = [identity['commission_source_ref']]
        return ChildMessage(objective='Improve the prediction model of the ledger owned by ' +
                            summary['owner_episode_id'], message={'initial_report': INITIAL_REPORT},
                            assignment=assignment, selection=PREDICTION_SELECTION)
    if slot == 'hpc_execution':
        assignment = {'owner_episode_id': summary['owner_episode_id'], 'scope': summary['scope'],
                      'input_refs': list(summary['input_refs']), **summary['commission_identity']}
        return ChildMessage(objective='Turn the commission of the ledger owned by ' + summary['owner_episode_id']
                            + ' into work done on a real allocation', message={'initial_report': INITIAL_REPORT},
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
                      'constraints': launch['constraints'], 'scope': summary['scope'],
                      'input_refs': list(summary['input_refs']), 'handoff_unit': arguments['handoff_unit'],
                      'already_handed_off_resource_ids': handed_off}
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
            assignment={'version': 'monitor_assignment_v1', 'target_handle': arguments['target_handle'],
                        'requested_fields': list(arguments['requested_fields']),
                        'known_progress_refs': list(arguments.get('known_progress_refs', [])),
                        'permitted_committed_record_types': list(arguments['permitted_committed_record_types']),
                        'information_unit': arguments['information_unit']},
            selection=MONITOR_SELECTION)
    if slot == 'results':
        assignment = {'version': RESULTS_VERSION, 'handoff_ref': [arguments['handoff_ref']],
                      'selector': arguments['selector'], 'acquired_record_unit': arguments['acquired_record_unit'],
                      'resource_kind': 'hpc'}
        if 'known_result_refs' in arguments:
            assignment['known_result_refs'] = list(arguments['known_result_refs'])
        return ChildMessage(objective='Acquire the requested results of the handed-off execution',
                            message={'initial_report': INITIAL_REPORT}, assignment=assignment,
                            selection=RESULTS_SELECTION)
    raise LookupError('hpc_work_planning_has_no_slot:' + slot)
