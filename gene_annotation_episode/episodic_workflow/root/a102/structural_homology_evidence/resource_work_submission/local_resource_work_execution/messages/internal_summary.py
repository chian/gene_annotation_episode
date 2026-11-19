"""Where the resource work stands, as a pure function of the view: the launch assignment and the job assignment, the
receipts of the commands run so far (each command's tool outcome carries its receipt, the reference of its saved
copy and whether it is a handoff), the receiving checks and the execution handoffs they found, the reasoning
commits, the practical credit view and the completion proof over the receipts, the working context and the
controller's yield table.

Old ``internal_summary.decision_context`` (role, assignment, resource capabilities, resource tool estimates): the
role is gone (each role is its own episode); the capabilities come from the settings and are added by ``decide``. The old
``resource_tool_estimates`` came from the selected adapter's optional ``decision_context``: no adapter object
exists now, so none are shown."""
from copy import deepcopy

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.practical_execution_credit import (
    project_practical_credit)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import (
    COMPLETION_VERSION, assess_validations, digest)

# The baseline is the assignment's frozen initial state, assessed before any action. A fixed time keeps the summary a
# pure function of the view; the baseline carries no observation time of its own.
BASELINE_CHECKED_AT = '1970-01-01T00:00:00+00:00'
HANDOFF_VERSION = 'execution_handoff_v1'


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


def _identity(handoff):
    return (handoff['resource_selection']['capability_binding_ref'], handoff['execution_handle'])


def execution_handoffs(handoffs):
    """The old ``to_parent.facts`` over the selected adapter's checks: for each distinct (registry, execution
    handle) the usable check with the latest ``checked_at``, in identity order. Library candidate."""
    latest = {}
    for handoff in handoffs:
        if handoff['state'] != 'usable':
            continue
        key = _identity(handoff)
        if key not in latest or handoff['checked_at'] >= latest[key]['checked_at']:
            latest[key] = handoff
    return [latest[key] for key in sorted(latest)]


def internal_summary(view):
    parent = view.parent_input
    assignment = parent['assignment']
    initial_validations = assess_validations(assignment, {'facts': {}}, assignment['initial_context'],
                                             checked_at=BASELINE_CHECKED_AT)
    receipts, receipt_refs, handoff_refs, commands, checks, handoffs, reasonings = [], [], [], [], [], [], []
    context = deepcopy(assignment['initial_context'])
    for unit in view.outcomes:
        outcome = unit['outcome']
        if unit['tool'] == 'exec_command':
            receipts.append(outcome['receipt'])
            receipt_refs.append(outcome['receipt_ref'])
            if outcome['handoff']:
                handoff_refs.append(outcome['receipt_ref'])
            context = outcome['receipt']['context_after']
            commands.append({'operation_ref': outcome['operation_ref'], 'receipt_ref': outcome['receipt_ref'],
                             'status': outcome['status'], 'arguments': unit['arguments']['arguments'],
                             'failure': (outcome['receipt']['outcome'].get('native_outcome') or {}).get('failure')})
        elif unit['tool'] == 'resource_check_handoff':
            checks.append({'status': outcome['status'], 'handoff': unit['arguments']['arguments']['handoff'],
                           'feedback': outcome['feedback']})
            result = outcome['result']
            if outcome['status'] == 'completed' and isinstance(result, dict) and result.get('version') == HANDOFF_VERSION:
                handoffs.append(result)
        elif unit['tool'] == 'reason':
            reasonings.append({'status': outcome['status'], 'produced': list(unit['produced'])})
    progress = project_practical_credit(assignment, initial_validations, receipts)
    controller = view.controller_state
    return {'launch': parent['launch'], 'assignment': assignment, 'scope': parent['scope'],
            'completion_target': parent['completion_target'], 'initial_validations': initial_validations,
            'receipts': receipts, 'receipt_refs': receipt_refs, 'handoff_refs': handoff_refs, 'commands': commands,
            'checks': checks, 'handoffs': execution_handoffs(handoffs), 'reasonings': reasonings,
            'execution_context': context, 'execution_progress': progress,
            'execution_completion': _completion(assignment, initial_validations, receipts),
            'reasoning_schema': view.records.reasoning_schema(),
            'controller': None if controller is None else yield_table(controller, forecast_unit='practical credit'),
            'units_consumed': view.units_consumed}
