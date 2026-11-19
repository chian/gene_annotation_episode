"""The commission of each child (carried from ``to_child_hpc_resource_prediction.py``,
``to_child_hpc_allocation_execution.py``, ``to_child_execution_job_submission.py``,
``to_child_execution_progress_assessment.py``, ``to_child_execution_result_acquisition.py`` and ``episode.py``
``prepare_child_request``).

``hpc_prediction`` and ``hpc_execution``: the old assignment was the owner episode id (this episode: the old check that
the owner is the commissioning parent holds by construction) and exactly one of ``commission_id`` or
``commission_source_ref`` copied from this episode's own assignment, so both sisters work on this episode's ledger. The
fields the children's forms need and the old code did not send (each a "new field" in the carry-over record): ``scope``
(the old binding context scope: both sisters inherit exactly this episode's scope) and, for the prediction,
``received_record_refs`` (this episode's own received records and the result sources and artifacts it holds, which the
prediction reads with ``hpc_read``: a pass carries only the records named) and, for the allocation execution,
``input_refs`` (the records the planned jobs read). The prediction takes the commission source as one record in
custody, the allocation execution as text (its form has no record field for it: it reads the commission from the ledger).

``launch``: the launch assignment the frozen plan carries (the old ``hpc.plan`` returned it, and the old
``authenticate_launch`` admitted the launch only if it equalled it: the commission is built from the plan, so it does),
under the names of the launch child's form: ``version``, ``requests`` (the mapping by resource id),
``immutable_input_versions``, ``constraints``, the optional ``launch_instructions`` the model selected, and the fields
the child's form needs and the old code did not send (each a "new field"): ``record_refs`` (the records the planned
jobs read, named here), ``handoff_unit`` and ``acquired_record_unit`` (from the settings, via the ``ChildCall``
arguments), ``scope`` and ``received_handoff_resources`` (the resource of a plan whose handoff this episode already
holds). ``hpc_execution_job`` is what the old ``LaunchPreparation.initial_decision_context`` gave the launch side at its
first decision: plan id, objective, the frozen scientific manifest, the acceptance predicates, the local input file
holding the plan (``hpc_plan`` wrote it), the coordinator workspace and the instruction that reference files are inputs
and not a required procedure. It has no field of the child's assignment form, so it rides in the message. The old
reservation of ``launch:<plan_id>`` in the ledger (one launch per plan, none after the allocation closed) is not
written here (a commission has no write); ``task.py`` ``action`` rejects a second launch of a plan and a launch of a
closed plan. A plan this episode does not hold raises ``StopIteration``: a wrong commission fails. The child selects
``execution_handoff_refs`` and ``execution_completed``.

``monitor``: the monitor assignment passed unchanged (the old ``prepare_request``: the child's form admits it), with
the information unit. ``results``: the results assignment as selected, under the names of the results child's form; the
kind and the workspace of the handed-off target are those of the plan whose launch returned that handoff (the old child
read them from the handoff target), with the one handoff record in custody, the result sources and artifacts earlier
results children of this handoff returned (the old initial known records) and the acquired-record unit."""
from episode_runtime import ChildMessage

from ..task import (EXECUTION_SELECTION, LAUNCH_JOB_INSTRUCTIONS, LAUNCH_SELECTION, MONITOR_SELECTION,
                    PREDICTION_SELECTION, RESULTS_SELECTION)

INITIAL_REPORT = 'nothing yet'


def _sister_assignment(summary, owner):
    return {'owner_episode_id': owner, 'scope': summary['scope']}


def msg_to_child(slot, arguments, summary):
    view = summary['ledger_view']
    if slot == 'hpc_prediction':
        assignment = _sister_assignment(summary, view['owner_episode_id'])
        if summary['commission_id'] is not None:
            assignment['commission_id'] = summary['commission_id']
        else:
            assignment['commission_source_ref'] = [summary['commission_source_ref']]
        assignment['received_record_refs'] = list(dict.fromkeys(
            [*summary['received_record_refs'], *summary['result_refs'], *summary['result_artifact_refs']]))
        return ChildMessage(objective='Improve the shared resource model of the HPC ledger of this commission',
                            message={'initial_report': INITIAL_REPORT, 'launch_instructions':
                                     summary['launch_instructions']},
                            assignment=assignment, selection=PREDICTION_SELECTION)
    if slot == 'hpc_execution':
        assignment = _sister_assignment(summary, view['owner_episode_id'])
        for name in ('commission_id', 'commission_source_ref'):
            if summary[name] is not None:
                assignment[name] = summary[name]
        assignment['input_refs'] = list(summary['input_refs'])
        return ChildMessage(objective='Prepare, launch, monitor and parse the selected work of the HPC ledger of '
                                      'this commission',
                            message={'initial_report': INITIAL_REPORT}, assignment=assignment,
                            selection=EXECUTION_SELECTION)
    if slot == 'launch':
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
                      'constraints': launch['constraints'], 'record_refs': list(summary['input_refs']),
                      'handoff_unit': arguments['handoff_unit'],
                      'acquired_record_unit': arguments['acquired_record_unit'],
                      'scope': summary['scope'], 'received_handoff_resources': handed_off}
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
            assignment={'version': 'monitor_assignment_v1', 'target_handle': arguments['target_handle'],
                        'requested_fields': list(arguments['requested_fields']),
                        'known_progress_refs': list(arguments.get('known_progress_refs', [])),
                        'permitted_committed_record_types': list(arguments['permitted_committed_record_types']),
                        'information_unit': arguments['information_unit']},
            selection=MONITOR_SELECTION)
    if slot == 'results':
        handoff_ref = arguments['handoff_ref']
        launched = next(item for item in summary['launches'] if handoff_ref in item['handoff_refs'])
        plan = next(item for item in view['plans'] if item['plan_ref'] == launched['plan_ref'])
        kind = next(iter(plan['launch_assignment']['requests'].values()))['resource_kind']
        earlier = [report for report in summary['acquisitions'] if report['handoff_ref'] == handoff_ref]
        assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': [handoff_ref],
                      'selector': arguments['selector'], 'resource_kind': kind,
                      'workspace': plan['manifest']['workspace'],
                      'acquired_record_unit': arguments['acquired_record_unit'],
                      'initial_result_refs': [ref for report in earlier for ref in report['result_refs']],
                      'initial_result_artifact_refs': [ref for report in earlier
                                                       for ref in report['result_artifact_refs']]}
        if 'constraints' in arguments:
            assignment['constraints'] = arguments['constraints']
        return ChildMessage(objective='Acquire the requested results of the handed-off execution',
                            message={'initial_report': INITIAL_REPORT}, assignment=assignment,
                            selection=RESULTS_SELECTION)
    raise LookupError('hpc_work_planning_has_no_slot:' + slot)
