"""Replay actual rejected monitoring input and preserve its factual contracts."""
from copy import deepcopy
import json

from gene_annotation_episode.episodic_workflow.root.decision_context import state_frame
from gene_annotation_episode.episodic_workflow.root.monitor_prompt import is_monitor_context, render_monitor_prompt
from gene_annotation_episode.episodic_workflow.root.providers import _SessionConnection


def wire():
    result = object.__new__(_SessionConnection)
    result.scientific_prompt_states = {}
    return result


def test_monitor_frame_updates_and_explicit_lookups_preserve_native_values():
    state = {'monitor_assignment': {'version': 'monitor_assignment_v1', 'target_handle': 'original-job'},
        'requested_form': {'type': 'object', 'properties': {
            'selected': {'type': 'object', 'x-source': 'specific_requested_fact'}}},
        'available_report_facts': {
            'specific_requested_fact': {'meaning': 'Actual selected custom return'},
            'unselected_fact': {'meaning': 'Unrelated catalog entry'}},
        'last_local_outcome': {'execution_status': {'state': 'failed', 'returncode': 1,
            'result_available': False}, 'unknown_measurement': None}, 'current_credit': .01}
    provider = wire()
    rendered, _ = provider._presentation('original-monitor', 'REASONING', 'Monitor the actual job.', state_frame(state))
    assert 'Actual selected custom return' in rendered and 'Unrelated catalog entry' not in rendered
    updated = deepcopy(state)
    updated['current_credit'] = 0
    updated['last_local_outcome']['execution_status']['returncode'] = 2
    provider._presentation('original-monitor', 'REASONING', 'Monitor the actual job.', state_frame(updated, state))
    assert provider.scientific_prompt_states[('original-monitor', 'REASONING')] == updated
    explicit = {'view': 'actual_requested_view', 'native_value': -1.5, 'missing': None}
    rendered = render_monitor_prompt(updated, 'Keep original scope.', lookup_results=[explicit])
    assert json.dumps([explicit], separators=(',', ':')) in rendered
    assert '"returncode":2' in rendered and '"unknown_measurement":null' in rendered


def test_plain_context_retains_its_existing_wire_format():
    state = {'goal': {'objective': 'An unrelated plain episode.'}, 'current_credit': 0}
    assert not is_monitor_context(state)
    provider = wire()
    frame = state_frame(state)
    rendered, _ = provider._presentation('plain', 'REASONING', 'Original instructions.', frame)
    assert json.loads(rendered) == frame
    assert not provider.scientific_prompt_states
