"""Original A107 saved-target and selected-action reads, explicitly selected by their consumers."""
import json
from ..execution_contracts import checked
from .execution_result_contract import RESULTS_SCHEMA

def received_execution_target(self, context):
    assignment = checked(context.assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
    nmf = self._retained_expression_nmf_target(context, assignment, context.scope)
    if nmf is not None:
        return nmf
    masking = self._retained_masking_target(context, assignment, context.scope)
    if masking is not None:
        return masking
    utility = self._retained_utility_target(context, assignment, context.scope)
    if utility is not None:
        return utility
    return self.job_progress_provider.targets.read_target(assignment['handoff_ref'], context.scope)
def retained_expression_nmf_target(self, context, assignment, scope):
    if not self._expression_nmf_selector(assignment):
        return None
    if self.native_expression_nmf_results is None:
        raise ValueError('native_expression_nmf_results_binding_unavailable')
    return self.native_expression_nmf_results.retained_target(context, assignment, scope)
def is_expression_nmf_selector(assignment):
    return assignment.get('selector', {}).get('version') == 'expression_nmf_result_selector_v1'
def retained_masking_target(self, context, assignment, scope):
    if not self._masking_selector(assignment):
        return None
    return self.native_blast_masking_results.retained_target(context, assignment=assignment, scope=scope)
def is_masking_selector(assignment):
    return assignment.get('selector', {}).get('version') == 'native_blast_masking_result_selector_v1'
def retained_utility_target(self, context, assignment, scope):
    if not self._utility_selector(assignment):
        return None
    return self.native_blast_utility_results.retained_target(context, assignment=assignment, scope=scope)
def is_utility_selector(assignment):
    return assignment.get('selector', {}).get('version') in {'native_blast_utility_result_selector_v1', 'native_blast_utility_result_selector_v2'}
def selected_result_action(self, episode_id, key, name, arguments):
    prefix = self.run_id + ':' + episode_id + ':'
    suffix = key.removeprefix(prefix)
    if not key.startswith(prefix) or not suffix.isdecimal() or str(int(suffix)) != suffix:
        raise ValueError('execution_result_selected_action_missing')
    row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (self.run_id, episode_id, int(suffix))).fetchone()
    if row is None:
        raise ValueError('execution_result_selected_action_missing')
    action = json.loads(row['action'])
    if action.get('kind') != 'tool' or action.get('tool') != name or action.get('arguments') != arguments:
        raise ValueError('execution_result_selected_action_conflict')
    return row
