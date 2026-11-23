"""The commission of each child (carried from ``to_child_execution_job_submission.py``,
``to_child_execution_progress_assessment.py``, ``to_child_execution_result_acquisition.py`` and ``episode.py``
``prepare_child_request``).

``launch``: the launch assignment the frozen plan carries (the old ``hpc.plan`` returned it, and the old launch was
admitted only if it equalled it: the commission is built from the plan, so it does): ``version``, ``requests`` (the
mapping by resource id, as the plan has it), ``immutable_input_versions`` (the list, as the plan has it) and
``constraints``, with the fields the launch child's form needs and the old code did not send (each a "new field" in the
carry-over record of the launch child): ``handoff_unit`` and ``acquired_record_unit`` (from the settings, via the
``ChildCall`` arguments), ``record_refs`` (every record the job inputs name, held by this episode: a pass carries only
the records named) and ``received_handoff_resources`` (the resource of a plan whose handoff this episode already
holds). ``hpc_execution_job`` is what the old ``LaunchPreparation.initial_decision_context`` gave the launch side at
its first decision: plan id, objective, the frozen scientific manifest, the acceptance predicates, the local input
file holding the plan (``hpc_plan`` wrote it), the coordinator workspace and the instruction that reference files are
inputs and not a required procedure. The launch child's form has no field for it: it rides in the free
``ChildMessage.message``, which the launch child's parent input keeps.

``monitor``: the monitor assignment passed unchanged (the old ``prepare_request``; the child's form admits it) with the
information unit. ``results``: the results assignment as selected, with the one handoff record in custody, the kind of
the resource (``hpc``: the resource of this episode is a ``pbs_ssh`` resource) and the acquired-record unit. The old
report-contract declaration, the receipt inheritance (``assemble_request``) and the comparison of the launch with the
plan's ledger rows (``authenticate_launch``: one reservation per plan, none after the plan is closed) are old-runner
machinery or moved: ``task.py`` ``action`` rejects a second launch of a plan and a launch of a closed plan, and the
system's unit journal is the one record of a launch. A plan this episode does not hold raises ``StopIteration``: a
wrong commission fails."""
from episode_runtime import ChildMessage

from ..task import (LAUNCH_JOB_INSTRUCTIONS, LAUNCH_SELECTION, MONITOR_SELECTION, RESULTS_RESOURCE_KIND,
                    RESULTS_SELECTION)

INITIAL_REPORT = 'nothing yet'
RESULTS_VERSION = 'execution_results_assignment'


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
               'supplied_input_artifact_ref': plan['supplied_input_artifact_ref'],
               'coordinator_workspace': view['coordinator_workspace'], 'instructions': LAUNCH_JOB_INSTRUCTIONS}
        return ChildMessage(
            objective='Launch the frozen plan ' + plan['plan_id'] + ' on resource ' + resource_id
                      + ' and return its usable handoff',
            message={'initial_report': INITIAL_REPORT, 'plan_ref': plan['plan_ref'], 'hpc_execution_job': job},
            assignment={'version': launch['version'], 'requests': launch['requests'],
                        'immutable_input_versions': launch['immutable_input_versions'],
                        'constraints': launch['constraints'], 'record_refs': list(dict.fromkeys([*summary['input_refs'], plan['supplied_input_artifact_ref']])),
                        'handoff_unit': arguments['handoff_unit'],
                        'acquired_record_unit': arguments['acquired_record_unit'],
                        'received_handoff_resources': handed_off},
            selection=LAUNCH_SELECTION)
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
    raise LookupError('hpc_allocation_execution_has_no_slot:' + slot)
