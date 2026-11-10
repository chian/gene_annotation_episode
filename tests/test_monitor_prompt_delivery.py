"""Replay actual rejected monitoring input and preserve its factual contracts."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.monitor_prompt import is_monitor_context, render_monitor_prompt
from gene_annotation_episode.providers import _SessionConnection


FIXTURE = Path(__file__).parent / 'fixtures/hpc/a107-genomic05-monitor-context.json.gz'


def wire():
    result = object.__new__(_SessionConnection)
    result.scientific_prompt_states = {}
    return result


def test_actual_failed_monitor_input_retains_state_and_selected_contracts():
    with gzip.open(FIXTURE, 'rt') as handle:
        original = json.load(handle)
    frame = original['context']
    before = deepcopy(frame)
    assert json.dumps(frame, allow_nan=False) == original['actual_input']
    assert len(original['actual_input']) == original['failure']['input_chars']
    assert original['failure']['input_chars'] > original['failure']['provider_max_chars']
    provider = wire()
    rendered, _ = provider._presentation(original['episode_id'], 'REASONING',
        original['instructions'], frame)
    # Existing transport capacity, not a newly configured investigation budget.
    assert len(rendered) < original['failure']['provider_max_chars']
    documents = [json.loads(line) for line in rendered.splitlines() if line.startswith('{')]
    visible = next(value for value in documents if 'monitor_assignment' in value)
    expected = {name: value for name, value in frame['fields'].items()
        if name not in ('available_report_facts', 'completed_action_reports')}
    assert visible == expected
    contracts = next(value for value in documents if 'monitoring_progress_refs' in value)
    assert contracts['monitoring_progress_refs'] == frame['fields']['available_report_facts']['monitoring_progress_refs']
    assert contracts['committed_record_refs'] == frame['fields']['available_report_facts']['committed_record_refs']
    assert 'literature_binding_interaction_model_cells' not in contracts
    assert provider.scientific_prompt_states[(original['episode_id'], 'REASONING')] == frame['fields']
    assert frame == before


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
