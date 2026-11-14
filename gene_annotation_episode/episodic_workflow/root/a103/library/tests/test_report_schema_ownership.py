"""Finite policy assembly/override checks; no new scientific workflow cohort."""
from types import MethodType, SimpleNamespace
import pytest
from .report_schema_checks import (action_schema, facts, host, invoke, original,
    paired, report_observation, runtime, schema_observation)


@pytest.mark.parametrize('role,scenario', [
    ('improvement', 'saved'), ('annotation', 'fresh'),
    ('scientific_process', 'fresh'), ('annotation', 'late-provider'),
    ('annotation', 'received-conflict'), ('annotation', 'provider-error'),
    ('improvement', 'private-finish'),
], ids=['saved-improvement', 'fresh-annotation', 'fresh-scientific',
        'late-report-provider', 'received-conflict', 'report-error-identity',
        'actual-private-finish'])
def test_report_projection(tmp_path, role, scenario):
    with host(tmp_path, role) as value:
        observed = paired(value, report_observation, scenario)
    if scenario == 'saved':
        assert observed['events'] == ['current_saved_view']
        assert 'interpretations' not in observed['outcome'][1]
    elif scenario == 'received-conflict':
        assert observed['outcome'] == ('raised', 'ValueError', 'received_report_fact_conflict', False)
    elif scenario == 'provider-error':
        assert observed['outcome'][-1] is True
    elif scenario == 'late-provider':
        assert observed['events'].index('native_event_callback') < observed['events'].index('annotation_projection')
        assert observed['events'].index('annotation_projection') < observed['events'].index('late_forecasts')
    elif scenario == 'private-finish':
        assert observed['outcome'][1]['answer'] == {'form': {'credit': 2.0}}
        assert observed['events'][-1] == 'release'
    elif role == 'scientific_process':
        snapshots = [entry[1] for entry in observed['events'] if isinstance(entry, tuple) and entry[0] == 'scientific_projection']
        assert snapshots[0]['parent_invocation_ref'] == 'original-parent-invocation'
        assert snapshots[0]['initial_credit'] == 1.0


@pytest.mark.parametrize('scenario', ['ordinary', 'late-binding', 'late-json-error'])
def test_action_contract_order(tmp_path, scenario):
    with host(tmp_path, 'improvement') as value:
        observed = paired(value, schema_observation, scenario)
    if scenario == 'late-json-error':
        assert observed['events'][-2:] == ['catalog', 'late_json']
        assert observed['outcome'][-1] is True
    else:
        kinds = [row['properties']['kind']['const'] for row in observed['outcome'][1]['properties']['selection']['anyOf']]
        assert ('child' in kinds) is (scenario != 'late-binding')
        assert {'reason', 'wait', 'tool', 'redeliver_report'} <= set(kinds)


@pytest.mark.parametrize('kind', ['class-method', 'instance-callable', 'nominal-selected'])
def test_private_selection_preserves_override(kind):
    events = []
    marker = RuntimeError('original override identity')
    source = object()
    def chosen(workflow, actual, **kwargs):
        assert actual is source
        events.append(('selected', kwargs))
        return marker
    def override(actual, **kwargs):
        assert actual is source
        events.append(('override', kwargs))
        return marker
    workflow = SimpleNamespace()
    if kind == 'nominal-selected':
        bound = MethodType(chosen, workflow)
    elif kind == 'class-method':
        def method(self, actual, **kwargs):
            return override(actual, **kwargs)
        bound = MethodType(method, workflow)
    else:
        bound = override
    assert invoke(bound, chosen, source, completion_record=None) is marker
    assert events == [('selected' if kind == 'nominal-selected' else 'override', {'completion_record': None})]
