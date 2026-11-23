"""The commissions of the three children (carried from ``to_child_execution_job_submission.py``
(``authenticate_launch`` and ``LaunchPreparation.initial_decision_context``),
``to_child_execution_progress_assessment.py`` (``prepare_request``) and the generic child path for ``results``).

``launch``: the frozen plan's ``launch_assignment`` exactly (the old authentication that only the exact planned
launch consumes the plan's slot is made on the model's answer, in ``action``: the plan is the one named, launched
once, not closed), and the plan's job under ``hpc_execution_job`` (the old ``initial_decision_context``: plan id,
objective, scientific manifest, scientific acceptance, the supplied input file, the coordinator workspace and the
instruction text). The Launch child's new fields: ``handoff_unit`` (the credit of the plan's ``handoff``
requirement), ``already_handed_off`` (the plan's resource when its handoff is already attached) and ``input_refs``
(the plan record, held as produced by ``hpc_plan``, which the file the job reads is made of). Return fields: the
Launch child always returns its handoff references and completion.

``monitor``: the ``monitor_assignment`` the model wrote, unchanged (the old request "preserves the selected
target, known observations, requested fields and permitted records"), with the monitor's new ``information_unit``
and the snapshots of the known observations this episode received. The parent selects the progress observations
and their snapshots (the old received progress).

``results``: the original handoff of the plan (the old ``handoff_ref``, now a record in custody), the model's
selector, and the target's kind and workspace, which the old code let the child read from the handoff target and
which this parent knows from the frozen plan."""
from episode_runtime import ChildMessage

INSTRUCTION_TEXT = (
    'The supplied local input file contains the frozen scientific manifest and reference source files. Use general '
    'terminal commands on the coordinator or assigned resource as needed; choose your scripts, environment and '
    'transfer method. Do not transcribe supplied source code into a child goal. Reference implementation files '
    'are available inputs, not a required execution procedure. Preserve original unit identities, scientific '
    'inputs, output/progress formats and acceptance predicates. Run computation in the actual allocation and '
    'retain its original identity. An uncertain submission must be investigated rather than duplicated.')


def launch_message(arguments, summary):
    hpc = summary['hpc']
    plan = hpc['plans'][arguments['plan_ref']]
    staged = hpc['launch_inputs'][plan['plan_id']]
    practical = plan['practical_assignment']
    assignment = {
        **plan['launch_assignment'],
        'handoff_unit': sum(row['credit'] for row in practical['progress_requirements'] if row['key'] == 'handoff'),
        'already_handed_off': [practical['resource_id']] if plan['plan_id'] in hpc['handoffs'] else [],
        'input_refs': [staged['input_ref']],
        'hpc_execution_job': {
            'plan_id': plan['plan_id'], 'objective': summary['commission']['objective'],
            'scientific_manifest': plan['manifest'], 'scientific_acceptance': summary['commission']['obligations'],
            'supplied_input_file': staged['supplied_input_file'],
            'coordinator_workspace': staged['coordinator_workspace'], 'instructions': INSTRUCTION_TEXT}}
    if summary['launch_instructions'] is not None:
        assignment['launch_instructions'] = summary['launch_instructions']
    return ChildMessage(
        objective='Launch the frozen HPC plan ' + plan['plan_id'] + ' on resource ' + practical['resource_id']
                  + ' and return its usable handoff',
        message={'plan_ref': arguments['plan_ref'], 'initial_report': 'nothing yet'},
        assignment=assignment, selection=())


def monitor_message(arguments, summary):
    assignment = {'version': 'monitor_assignment', **arguments['assignment'],
                  'information_unit': arguments['information_unit']}
    known = {ref: summary['received_progress_snapshots'][ref] for ref in assignment['known_progress_refs']
             if ref in summary['received_progress_snapshots']}
    if known:
        assignment['known_progress_snapshots'] = known
    return ChildMessage(
        objective='Investigate which further exposed progress information is useful for the execution target '
                  + assignment['target_handle'] + '; this parent requests information and never polls here.',
        message={'launch_instructions': summary['launch_instructions']}, assignment=assignment,
        selection=('monitoring_progress_refs', 'monitoring_progress_snapshots'))


def results_message(arguments, summary):
    hpc = summary['hpc']
    plan = hpc['plans'][arguments['plan_ref']]
    return ChildMessage(
        objective='Acquire the original results of the allocation of plan ' + plan['plan_id']
                  + ' through its original handoff',
        message={'plan_ref': arguments['plan_ref']},
        assignment={'version': 'execution_results_assignment',
                    'handoff_ref': [hpc['handoffs'][plan['plan_id']]['handoff_ref']],
                    'selector': arguments['selector'], 'resource_kind': 'hpc',
                    'workspace': plan['manifest']['workspace'],
                    'acquired_record_unit': arguments['acquired_record_unit']},
        selection=())


def msg_to_child(slot, arguments, summary):
    if slot == 'launch':
        return launch_message(arguments, summary)
    if slot == 'monitor':
        return monitor_message(arguments, summary)
    if slot == 'results':
        return results_message(arguments, summary)
    raise LookupError('hpc_allocation_execution_has_no_slot:' + slot)
