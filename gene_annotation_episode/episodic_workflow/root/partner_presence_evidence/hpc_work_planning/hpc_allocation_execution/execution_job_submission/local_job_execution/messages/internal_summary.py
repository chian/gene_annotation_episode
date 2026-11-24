"""Where the execution stands, as a pure function of the view: the assignment, the receipts of the commands run so
far (each tool outcome carries its receipt, the reference of its saved copy and any handoff), the practical credit
view and the completion proof over them, the selected execution task (when the parent supplied the scientific
task), and the controller's yield table.

Old ``OperationalSummary.decision_context`` / ``_with_selected_execution_task`` and the delegate's
``decision_context``: execution_assignment, execution_progress, execution_completion, selected_execution_task. The
resource, the coordinator workspace and the resource's launch instructions come from the settings and are added by
``decide``; everything else is here."""
from copy import deepcopy

from gene_annotation_episode.episodic_workflow.episode_support.grading.partner_presence_evidence.practical_execution_credit import (
    project_practical_credit)
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.practical_execution_records import (
    COMPLETION_VERSION, assess_validations, digest)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

# The baseline is the assignment's frozen initial state, assessed before any action. A fixed time keeps the summary a
# pure function of the view; the baseline carries no observation time of its own.
BASELINE_CHECKED_AT = '1970-01-01T00:00:00+00:00'
SUPPORTED_NATIVE_JOBS = ('native_blast', 'native_blast_masking', 'native_blast_utility', 'native_blast_database',
                         'native_blast_standard_database', 'native_hmmer', 'native_hmmer_preparation',
                         'native_expression_nmf')


def _completion(assignment, initial_validations, receipts):
    """The verified completion of the assignment's endpoint, or None (the old ``PracticalState._completion`` over
    the receipts; library candidate)."""
    if not receipts:
        return None
    satisfied = set(project_practical_credit(assignment, initial_validations, receipts)['satisfied_keys'])
    keys = set(assignment['completion_keys'])
    if not keys <= satisfied:
        return None
    endpoint_kind = 'requested_job_handoff' if assignment['endpoint'] == 'usable_handoff' else 'requested_job_outputs'
    last = receipts[-1]
    if not any(item['key'] in keys and item['satisfied'] and item['predicate']['kind'] == endpoint_kind
               for item in last['validations']):
        return None
    return {'version': COMPLETION_VERSION, 'run_id': last['run_id'], 'episode_id': last['episode_id'],
            'assignment_sha256': digest(assignment), 'endpoint': assignment['endpoint'],
            'operation_key': last['operation_key'], 'receipt_sha256': digest(last),
            'validation_keys': sorted(keys)}


def _selected_execution_task(parent_input):
    """The old ``selected_execution_task`` of the decision context: present only when the parent supplied the
    scientific task and the request names exactly one supported native job. The resource information of the
    request is added by ``decide`` (it comes from the settings)."""
    task = parent_input.get('scientific_task')
    if task is None:
        return None
    assignment = parent_input['assignment']
    jobs = assignment['requested_job']
    chosen = [name for name in SUPPORTED_NATIVE_JOBS if isinstance(jobs.get(name), dict)]
    if len(chosen) != 1:
        return None
    name = chosen[0]
    job = deepcopy(jobs[name])
    if name == 'native_expression_nmf':
        # old: expression_nmf_presentation.expression_nmf_scientific_job_view(job), in no place now
        raise NotImplementedError('unplaced:expression_nmf_scientific_job_view')
    if name in {'native_hmmer', 'native_hmmer_preparation'}:
        # old: native_profile_presentation.native_profile_scientific_job_view(job), in no place now
        raise NotImplementedError('unplaced:native_profile_scientific_job_view')
    return deepcopy({'version': 'selected_execution_task', 'scientific_question': task['scientific_question'],
                     'selected_tool_info': task['selected_tool_info'],
                     'requests': [{'resource_id': assignment['resource_id'], 'resource_kind': 'local',
                                   'endpoint': assignment['endpoint'], 'constraints': assignment['constraints'],
                                   'job': job}],
                     'constraints': assignment['constraints'], 'selector': None, 'result_description': None})


def internal_summary(view):
    parent = view.parent_input
    assignment = parent['assignment']
    initial_validations = assess_validations(assignment, {'facts': {}}, assignment['initial_context'],
                                             checked_at=BASELINE_CHECKED_AT)
    receipts, receipt_refs, handoff_refs, commands = [], [], [], []
    for unit in view.outcomes:
        outcome = unit['outcome']
        receipts.append(outcome['receipt'])
        receipt_refs.append(outcome['receipt_ref'])
        if outcome['handoff']:
            handoff_refs.append(outcome['receipt_ref'])
        commands.append({'operation_ref': outcome['operation_ref'], 'receipt_ref': outcome['receipt_ref'],
                         'arguments': unit['arguments']['arguments'],
                         'failure': (outcome['receipt']['outcome'].get('native_outcome') or {}).get('failure')})
    progress = project_practical_credit(assignment, initial_validations, receipts)
    completion = _completion(assignment, initial_validations, receipts)
    controller = view.controller_state
    return {'assignment': assignment, 'completion_target': parent['completion_target'],
            'initial_validations': initial_validations, 'receipts': receipts, 'receipt_refs': receipt_refs,
            'handoff_refs': handoff_refs, 'commands': commands, 'execution_progress': progress,
            'execution_completion': completion, 'selected_execution_task': _selected_execution_task(parent),
            'controller': None if controller is None else yield_table(controller, forecast_unit='practical credit'),
            'units_consumed': view.units_consumed}
