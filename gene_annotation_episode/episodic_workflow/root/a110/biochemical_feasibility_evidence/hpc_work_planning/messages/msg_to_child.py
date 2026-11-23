"""The commission of each child (carried from ``to_child_hpc_resource_prediction.py``,
``to_child_hpc_allocation_execution.py``, ``to_child_execution_job_submission.py`` (``LaunchPreparation.
initial_decision_context``), ``to_child_execution_progress_assessment.py``, ``to_child_execution_result_acquisition.py``
and ``episode.py`` ``prepare_child_request``). Written against the finished ``goal.py``, ``messages/read_from_parent.py``
and ``messages/final_to_parent.py`` of the five child folders, read as data.

``hpc_prediction`` and ``hpc_execution``: the same commission identity as this episode's own (``commission_id`` or
``commission_source_ref``, both text in the children's forms), and this episode as the ledger owner (the old requests
carried ``owner_episode_id``). The old checks that the parent has the role ``hpc`` and is the named owner are not made
(a wrong commission fails). New fields the children's forms require (each is a "new field" in the carry-over record):
``hpc_prediction``: ``ledger_refs``; ``hpc_execution``: ``scope`` and ``input_refs``. The prediction child selects
``hpc_credit`` and ``hpc_accepted_obligations`` (its ``hpc_model_ref``, ``hpc_result_refs`` and ``hpc_ledger_refs`` are
required fields); the execution child selects its four facts.

``launch``: the launch assignment the frozen plan carries (the old ``hpc.plan`` returned it, and the old launch was
admitted only if it equalled it: the commission is built from the plan, so it does) with the fields the launch child's
form has beyond the old schema: ``handoff_unit`` (from the settings, via the ``ChildCall`` arguments),
``handed_off_resource_ids`` (the resource of a plan whose handoff this episode already holds), ``record_refs`` (every
record the job inputs name, held by this episode: a pass carries only the records named) and ``hpc_execution_job``,
which the child declares: what the old ``LaunchPreparation.initial_decision_context`` gave the launch side at its first
decision (plan id, objective, the frozen scientific manifest, the acceptance predicates, the local input file holding
the plan, the coordinator workspace and the instruction that reference files are inputs and not a required
procedure).

``monitor``: the monitor assignment passed unchanged (the old ``prepare_request``; the child's form admits it) with
the information unit. ``results``: the results assignment as selected, with the one handoff record in custody, the
kind of the resource (``hpc``: the resource of this episode is a ``pbs_ssh`` resource) and the acquired-record unit; the
results child declares no ``known_result_refs``, so none is sent. The old report-contract declaration, the receipt
inheritance (``assemble_request``) and the comparison of the launch with the plan's ledger rows
(``authenticate_launch``: one reservation per plan, none after the plan is closed) are old-runner machinery or moved:
``task.py`` ``action`` rejects a second launch of a plan and a launch of a closed plan, and the system's unit journal
is the one record of a launch. A plan this episode does not hold raises ``StopIteration``: a wrong commission fails."""
from episode_runtime import ChildMessage

from ..task import (EXECUTION_SELECTION, LAUNCH_JOB_INSTRUCTIONS, LAUNCH_SELECTION, MONITOR_SELECTION,
                    PREDICTION_SELECTION, RESULTS_RESOURCE_KIND, RESULTS_SELECTION)

INITIAL_REPORT = 'nothing yet'
RESULTS_VERSION = 'execution_results_assignment'


def ledger_refs(summary):
    """The rows of this episode's ledger, passed in custody (the ledger as its latest tool outcome showed it)."""
    return list(summary['ledger_view']['row_refs'])


def commission_assignment(summary):
    assignment = {'owner_episode_id': summary['owner_episode_id']}
    assignment.update(summary['commission_identity'])
    return assignment


def msg_to_child(slot, arguments, summary):
    if slot == 'hpc_prediction':
        assignment = {**commission_assignment(summary), 'ledger_refs': ledger_refs(summary)}
        return ChildMessage(objective='Improve the prediction model of the ledger owned by ' +
                            summary['owner_episode_id'], message={'initial_report': INITIAL_REPORT},
                            assignment=assignment, selection=PREDICTION_SELECTION)
    if slot == 'hpc_execution':
        assignment = {**commission_assignment(summary), 'scope': summary['scope'],
                      'input_refs': list(summary['input_refs']), 'ledger': summary['ledger_view']['ledger'],
                      'ledger_row_refs': ledger_refs(summary)}
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
               'supplied_input_artifact_ref': plan['supplied_input_artifact_ref'],
               'coordinator_workspace': view['coordinator_workspace'], 'instructions': LAUNCH_JOB_INSTRUCTIONS}
        assignment = {'version': launch['version'], 'requests': launch['requests'],
                      'immutable_input_versions': launch['immutable_input_versions'],
                      'constraints': launch['constraints'], 'handoff_unit': arguments['handoff_unit'],
                      'handed_off_resource_ids': handed_off, 'record_refs': list(dict.fromkeys([*summary['input_refs'], plan['supplied_input_artifact_ref']])),
                      'hpc_execution_job': job}
        selected = summary['message'].get('launch_instructions')
        if selected is not None:
            assignment['launch_instructions'] = selected
        return ChildMessage(
            objective='Launch the frozen plan ' + plan['plan_id'] + ' on resource ' + resource_id
                      + ' and return its usable handoff',
            message={'initial_report': INITIAL_REPORT, 'plan_ref': plan['plan_ref']},
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
        assignment = {'version': RESULTS_VERSION, 'handoff_ref': [arguments['handoff_ref']],
                      'selector': arguments['selector'], 'resource_kind': RESULTS_RESOURCE_KIND,
                      'acquired_record_unit': arguments['acquired_record_unit']}
        return ChildMessage(objective='Acquire the requested results of the handed-off execution',
                            message={'initial_report': INITIAL_REPORT}, assignment=assignment,
                            selection=RESULTS_SELECTION)
    raise LookupError('hpc_work_planning_has_no_slot:' + slot)
