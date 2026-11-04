"""Standard entry points: synthetic science, real state/forms/score projection.

No biological conclusion, model call or native job is produced by these fixtures.
"""
import asyncio
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.cli import main
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_investigation_progress import put_finding
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_findings import finding, target_question
from test_scientific_hypervolume_runtime import assessment, annotation, evidence


def tool(name, arguments):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': arguments}, 'report_update': {}}


def reason(store, rows, account=None):
    payload = {name: [] for name in store.reasoning_schema()['required']}
    payload['assessments'] = rows
    payload['annotation_updates'] = [] if account is None else [{**account, 'alias': 'account'}]
    return {'selection': {'kind': 'reason', 'commit': payload}, 'report_update': {}}


def repeat_hypothesis(store, hypothesis):
    """A real, nonempty fixture commitment with no new scored finding."""
    request = reason(store, [])
    saved = store.get(hypothesis)
    request['selection']['commit']['hypotheses'] = [{'alias': 'same_question',
        **{key: saved[key] for key in ('subject_refs', 'predicate', 'value', 'context_refs')}}]
    return request


def selected_account(target, hypothesis, refs, revision):
    value = annotation(target, hypothesis, refs, revision)
    value['coherent_sets'][0]['interpretations'][0]['disposition'] = 'supported'
    value['alternative_refs'] = []
    value['resolution'] = 'selected'
    return value


def fixture_factory(path, initial):
    return FixtureController(str(path), initial, 3)


def test_default_progress_is_preserved_without_inventing_an_annotation_score(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        positive, negative = [evidence(store, target, kind) for kind in ['alignment', 'comparison']]
        first = assessment(hypothesis, positive['id'], 'direct', alias='support')
        first['investigation_finding'] = finding(target)
        initial = reason(store, [first], selected_account(target, hypothesis, ['@support'], 0))

        def oppose(context):
            assert context['current_credit'] == 7
            assert 'annotation_score' not in context
            assert 'annotation_evidence_vector' not in context
            previous, = store.current_assessments()
            current, = store.current_annotations()
            row = assessment(hypothesis, negative['id'], 'direct', alias='opposition')
            row['relation'] = 'weakens'
            row['investigation_finding'] = finding(target, value='negative')
            return reason(store, [row], selected_account(target, hypothesis,
                [previous['id'], '@opposition'], current['revision']))

        def inspect(context):
            assert context['current_credit'] == 14
            assert 'annotation_score' not in context
            assert context['controller']['scores'] == [7, 7]
            return repeat_hypothesis(store, hypothesis)

        config = {'scientific_progress': {'finding_unit': 7}}
        options = {'run_dir': tmp_path/'run', 'controller_factory': fixture_factory,
            'initial_known_record_refs': [hypothesis, positive['id'], negative['id']]}
        summary = asyncio.run(run_workflow(store, ToolRegistry(store),
            provider=ScriptedProvider([initial, oppose, inspect]),
            provider_config=config, **options))
        assert summary['credit'] == 14 and 'annotation_score' not in summary
        assert summary['annotation_score_status'] == 'unavailable_no_scorer_bound'
        saved = json.loads((tmp_path/'run/run.json').read_text())
        assert saved['binding_definitions']['credit']['policy']['finding_unit'] == 7
        assert 'annotation_score' not in saved['binding_definitions']
        assert 'annotation_score' not in saved['bindings']
        rows = [tuple(row) for row in store.db.execute('SELECT * FROM runtime_observations ORDER BY rowid')]
        # No configuration supplied: restore the original values, not defaults.
        replay = asyncio.run(run_workflow(store, ToolRegistry(store),
            provider=ScriptedProvider([]), resume=True, **options))
        assert replay == summary
        assert [tuple(row) for row in store.db.execute('SELECT * FROM runtime_observations ORDER BY rowid')] == rows
        with pytest.raises(Exception, match='binding definitions'):
            asyncio.run(run_workflow(store, ToolRegistry(store),
                provider=ScriptedProvider([]), resume=True,
                provider_config={'scientific_progress': {'finding_unit': 9}}, **options))


def test_default_finding_credit_needs_no_annotation_and_interrupted_resume_keeps_the_prefix(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        observed = evidence(store, target, 'alignment')
        row = assessment(hypothesis, observed['id'], 'incomparable', alias='finding')
        row['investigation_finding'] = finding(target)
        options = {'run_dir': tmp_path/'run',
            'initial_known_record_refs': [hypothesis, observed['id']],
            'controller_factory': lambda path, initial: FixtureController(str(path), initial, 2)}
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(run_workflow(store, ToolRegistry(store),
                provider=ScriptedProvider([reason(store, [row]), asyncio.CancelledError()]),
                provider_config={'scientific_progress': {'finding_unit': 7}}, **options))
        prefix = [tuple(r) for r in store.db.execute('SELECT * FROM runtime_observations ORDER BY rowid')]
        assert len(prefix) == 1

        def next_choice(context):
            assert context['current_credit'] == 7 and 'annotation_score' not in context
            assert context['controller']['scores'] == [7]
            return repeat_hypothesis(store, hypothesis)
        summary = asyncio.run(run_workflow(store, ToolRegistry(store),
            provider=ScriptedProvider([next_choice]), resume=True, **options))
        assert summary['credit'] == 7 and 'annotation_score' not in summary
        assert summary['annotation_score_status'] == 'unavailable_no_scorer_bound'
        after = [tuple(r) for r in store.db.execute('SELECT * FROM runtime_observations ORDER BY rowid')]
        assert len(after) == 2 and after[:1] == prefix


def test_cli_uses_received_progress_without_the_retired_annotation_default(tmp_path, monkeypatch, capsys):
    from gene_annotation_episode import providers

    directory = tmp_path/'workspace'
    with Store(directory) as store:
        target, hypothesis = target_question(store)
        saved = put_finding(store, hypothesis, evidence(store, target, 'alignment'), target)
        account = store.put('annotation', selected_account(target, hypothesis, [saved['id']], 0), origin='reasoning')
        unchanged_reason = repeat_hypothesis(store, hypothesis)
    contexts = []

    class Connection:
        def __init__(self, *args, **kwargs):
            self.state = None
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def release(self, episode_id):
            pass
        async def complete(self, episode_id, role, instructions, context, output_schema):
            from gene_annotation_episode.decision_context import apply_state_frame
            self.state = apply_state_frame(self.state, context)
            context = self.state
            contexts.append(deepcopy(context))
            assert context['current_credit'] == 7
            assert 'annotation_score' not in context
            assert len(contexts) < 30, 'fixture did not reach a completed zero-gain action'
            return {'response': {'response_type': 'select_action', **unchanged_reason}}

    monkeypatch.setattr(providers, 'ModelConnection', Connection)
    config = tmp_path/'fixture.toml'
    config.write_text('[scientific_progress]\nfinding_unit=7\ninitial_known_record_refs='
        +json.dumps([saved['id'], account['id']])+'\n'
        '[controller]\ncost=0.1\n')
    result = main(['run', '--workspace', str(directory), '--run-dir', str(tmp_path/'run'),
                   '--config', str(config)])
    assert result == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary['credit'] == 7 and 'annotation_score' not in summary
    assert summary['annotation_score_status'] == 'unavailable_no_scorer_bound'
    assert contexts[0]['controller']['initial_credit'] == 7
    assert all(row['total_yield'] == 0 for row in contexts[-1]['action_yields']['rows'])
    assert len(contexts) == summary['completed_actions']
