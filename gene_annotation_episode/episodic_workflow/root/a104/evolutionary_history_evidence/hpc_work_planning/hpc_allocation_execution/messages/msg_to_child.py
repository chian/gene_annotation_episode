"""The commission of each child: the assignment the child's form requires, every record this episode names for it,
and the selectable return fields it wants. A wrong commission fails: nothing here checks it against the child.

``launch`` (``execution_job_submission``): the plan's frozen launch assignment (old ``plan['launch_assignment']``,
which the old ``authenticate_launch`` required the model's selection to equal) with the operational units; the old
``LaunchPreparation.initial_decision_context`` (the job the launch child executes: plan id, objective, scientific
manifest, scientific acceptance, the supplied input file) rides in the message under the old key
``hpc_execution_job``. The launch child returns ``execution_handoff_refs`` and ``execution_completed`` as required
fields, so nothing is selected.
``monitor`` (``execution_progress_assessment``): the target, the exposed fields and the permitted record types the
parent's model chose (old ``prepare_child_request`` = the ``monitor_assignment_v1`` the model wrote), with the
information unit; the parent selects the facts its own forecast revision reads.
``results`` (``execution_result_acquisition``): the original handoff of the plan (named in custody), the selector the
model chose, and the plan's workspace; the parent selects ``execution_completed``."""
from episode_runtime import ChildMessage

LAUNCH_VERSION = 'execution_launch_assignment_v1'
MONITOR_VERSION = 'monitor_assignment_v1'
RESULTS_VERSION = 'execution_results_assignment_v1'
JOB_INSTRUCTIONS = ('The supplied local input file contains the frozen scientific manifest and reference source '
                    'files. Use general terminal commands on the coordinator or assigned resource as needed; choose '
                    'your scripts, environment and transfer method. Do not transcribe supplied source code into a '
                    'child goal. Reference implementation files are available inputs, not a required execution '
                    'procedure. Preserve original unit identities, scientific inputs, output/progress formats and '
                    'acceptance predicates. Run computation in the actual allocation and retain its original '
                    'identity. An uncertain submission must be investigated rather than duplicated.')


def msg_to_child(slot, arguments, summary):
    if slot == 'launch':
        plan = summary['plans'][arguments['plan_ref']]
        commission = summary['state']['hpc_commission']
        assignment = {**plan['launch_assignment'], 'handoff_unit': summary['handoff_unit'],
                      'acquired_record_unit': summary['acquired_record_unit']}
        if 'launch_instructions' in arguments:
            assignment['launch_instructions'] = arguments['launch_instructions']
        job = {'plan_id': plan['plan_id'], 'objective': commission['objective'],
               'scientific_manifest': plan['manifest'], 'scientific_acceptance': commission['obligations'],
               'supplied_input_file': summary['staged_inputs'][arguments['plan_ref']],
               'instructions': JOB_INSTRUCTIONS}
        return ChildMessage(objective='Establish the requested usable handoff of the frozen HPC allocation '
                                      + plan['plan_id'],
                            message={'plan_ref': arguments['plan_ref'], 'hpc_execution_job': job},
                            assignment=assignment, selection=())
    if slot == 'monitor':
        return ChildMessage(objective='Report which further progress information of the target '
                                      + arguments['target_handle'] + ' is useful',
                            message={'target_handle': arguments['target_handle']},
                            assignment={'version': MONITOR_VERSION, 'target_handle': arguments['target_handle'],
                                        'requested_fields': list(arguments['requested_fields']),
                                        'known_progress_refs': list(arguments['known_progress_refs']),
                                        'permitted_committed_record_types':
                                            list(arguments['permitted_committed_record_types']),
                                        'information_unit': summary['information_unit']},
                            selection=('monitoring_progress_refs', 'monitoring_target_handle',
                                       'monitoring_execution_state', 'monitoring_result_available',
                                       'monitoring_observed_at_unix_seconds'))
    if slot == 'results':
        plan = summary['plans'][arguments['plan_ref']]
        assignment = {'version': RESULTS_VERSION, 'handoff_ref': [plan['handoff_ref']],
                      'selector': arguments['selector'], 'resource_kind': 'hpc',
                      'workspace': plan['manifest']['workspace'],
                      'acquired_record_unit': summary['acquired_record_unit']}
        for name in ('initial_result_refs', 'initial_result_artifact_refs'):
            if name in arguments:
                assignment[name] = list(arguments[name])
        return ChildMessage(objective='Acquire the requested original results of the frozen HPC allocation '
                                      + plan['plan_id'],
                            message={'plan_ref': arguments['plan_ref']}, assignment=assignment,
                            selection=('execution_completed',))
    raise ValueError('hpc_child_slot_unknown:' + slot)
