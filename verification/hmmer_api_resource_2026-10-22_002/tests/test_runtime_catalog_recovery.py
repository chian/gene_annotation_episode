"""Saved decision contracts survive added capabilities without new observations."""
import json

import pytest

from test_runtime import FixtureTools, ScriptedProvider, obj, reason, run, setup, tool


class AddedCapabilityTools(FixtureTools):
    added = False
    added_executions = 0

    def catalog(self, scope=None):
        result = super().catalog(scope)
        if self.added:
            result.append({'name': 'fixture.added', 'input_schema': obj({})})
        return result

    def execute(self, name, args, **kwargs):
        if name == 'fixture.added':
            self.added_executions += 1
            return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': {}}
        return super().execute(name, args, **kwargs)


@pytest.mark.parametrize('try_new_tool_in_pending_decision', [False, True])
def test_saved_contract_is_replayed_and_new_catalog_applies_to_new_decisions(tmp_path, try_new_tool_in_pending_decision):
    store, _ = setup(tmp_path)
    tools = AddedCapabilityTools(store)
    counts = (2, 2) if try_new_tool_in_pending_decision else (3, 3)
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, ScriptedProvider([reason(1), KeyboardInterrupt()]), tmp_path/'run', counts=counts)
    saved_request = json.loads(store.db.execute('SELECT request FROM runtime_model_calls WHERE call_index=1').fetchone()[0])
    observation = store.db.execute('SELECT observation FROM runtime_observations').fetchone()[0]
    assert 'fixture.added' not in [entry['name'] for entry in saved_request['context']['tools']]
    tools.added = True
    added = {'selection': {'kind': 'tool', 'tool': 'fixture.added', 'arguments': {}}, 'report_update': {}}

    def pending(context):
        assert context == saved_request['context']
        return added if try_new_tool_in_pending_decision else tool()

    def fresh(context):
        assert 'fixture.added' in [entry['name'] for entry in context['tools']]
        if try_new_tool_in_pending_decision:
            assert context['feedback']['category'] == 'action_contract'
        return added

    summary = run(store, tools, ScriptedProvider([pending, fresh]), None, counts=counts, resume=True)
    assert summary['credit'] == 1 and summary['completed_actions'] == counts[0]
    assert tools.added_executions == 1
    assert tools.executions == (0 if try_new_tool_in_pending_decision else 1)
    assert store.db.execute('SELECT observation FROM runtime_observations ORDER BY unit_index LIMIT 1').fetchone()[0] == observation
    request = json.loads(store.db.execute('SELECT request FROM runtime_model_calls WHERE call_index=1').fetchone()[0])
    assert request == saved_request
    assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == counts[0]


@pytest.mark.parametrize('original_provider_has_session', [False, True])
def test_added_tool_does_not_relabel_prior_invalid_proposal_on_recovery(tmp_path, original_provider_has_session):
    store, _ = setup(tmp_path)
    tools = AddedCapabilityTools(store)
    added = {'selection': {'kind': 'tool', 'tool': 'fixture.added', 'arguments': {}}, 'report_update': {}}
    provider = ScriptedProvider([added, reason(1), KeyboardInterrupt()])
    provider.has_session = lambda *_: original_provider_has_session
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, provider, tmp_path/'run', counts=(3, 3))
    saved_request = json.loads(store.db.execute(
        'SELECT request FROM runtime_model_calls WHERE call_index=2').fetchone()[0])
    tools.added = True

    def pending(context):
        if original_provider_has_session:
            assert {key: value for key, value in context.items()
                    if key != 'restored_episode_history'} == saved_request['context']
        else:
            assert context == saved_request['context']
        entries = context['restored_episode_history']['entries']
        assert entries[0]['decision_index'] == 0
        assert entries[0]['tool'] is None
        assert entries[0]['status'] == 'unexecuted'
        return tool()

    def fresh(context):
        assert 'fixture.added' in [entry['name'] for entry in context['tools']]
        assert context['restored_episode_history']['entries'][0]['tool'] is None
        return added

    summary = run(store, tools, ScriptedProvider([pending, fresh]), None,
                  counts=(3, 3), resume=True)
    assert summary['completed_actions'] == 3
    assert tools.added_executions == 1
    assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
