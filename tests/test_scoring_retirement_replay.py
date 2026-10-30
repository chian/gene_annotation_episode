"""Scoring retirement at runtime boundaries; all work is synthetic and local."""
import asyncio
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode.independent_execution import make_runtime_binding, _saved_episode_factories
from gene_annotation_episode.case_execution import _load_policy
from gene_annotation_episode.credit import AnnotationScoringUnavailable
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from method_loop.durable import DurableExecutionError
from test_runtime import FixtureController, ScriptedProvider


def fixture_reason(store, value='unresolved'):
    payload = {section: [] for section in store.reasoning_schema()['required']}
    payload['hypotheses'] = [{'alias': 'fixture_hypothesis',
        'subject_refs': store.problem()['subject_refs'], 'predicate': 'sequence_integrity',
        'value': {'type': 'enum', 'value': value}, 'context_refs': []}]
    return {'selection': {'kind': 'reason', 'commit': payload}, 'report_update': {}}


def saved_bytes(store, directory):
    """Include exact requests, observations, actions, settings and archive files."""
    return (store.db.serialize(), {
        str(path.relative_to(directory)): path.read_bytes()
        for path in directory.rglob('*') if path.is_file()})


@pytest.mark.parametrize('entrypoint', ['root_explicit', 'root_latest', 'detached'])
def test_retired_default_rejected_without_rewriting_saved_work(tmp_path, entrypoint):
    directory = tmp_path/'run'
    with Store(tmp_path/'workspace') as store:
        store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')
        tools = ToolRegistry(store)
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(run_workflow(store, tools, run_dir=directory,
                provider=ScriptedProvider([fixture_reason(store), asyncio.CancelledError()])))
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_model_calls').fetchone()[0] == 2

        # This temporary fixture models the saved old marker. It deliberately
        # does not run, import or reinterpret the rejected historical scorer.
        manifest = json.loads((directory/'run.json').read_text())
        manifest['binding_definitions']['credit']['default_entrypoint'] = (
            'standard_received_scientific_progress_v1')
        settings = {key: value for key, value in manifest.items() if key != 'run_id'}
        store.db.execute('UPDATE runtime_runs SET settings=? WHERE run_id=?',
            (json.dumps(settings), manifest['run_id']))
        (directory/'run.json').write_text(json.dumps(manifest)+'\n')
        before = saved_bytes(store, directory)
        provider = ScriptedProvider([])
        if entrypoint == 'detached':
            with pytest.raises(DurableExecutionError) as failure:
                make_runtime_binding(store, directory)
            assert failure.value.failure['code'] == 'unavailable_binding'
        else:
            with pytest.raises(ValueError, match='requires_original_scientific_binding_and_code_snapshot'):
                asyncio.run(run_workflow(store, tools, provider=provider, resume=True,
                    run_dir=directory if entrypoint == 'root_explicit' else None))
        assert not provider.contexts
        assert saved_bytes(store, directory) == before


def test_retired_fixed_case_policy_cannot_rebind_or_rewrite_its_saved_definition(tmp_path):
    source = tmp_path/'policy-fixture.py'
    source.write_text(
        'from gene_annotation_episode.credit import CreditPolicy\n'
        'from gene_annotation_episode.scientific_credit import ScientificEvidenceCredit\n'
        'def create_policy(parameters):\n'
        '    return ScientificEvidenceCredit(CreditPolicy.from_record(parameters))\n')
    original = source.read_bytes()
    marker = tmp_path/'policy-binding.json'
    marker.write_text(json.dumps({'source_sha256': hashlib.sha256(original).hexdigest(),
        'snapshot_file': source.name, 'parameters': {},
        'definitions': {'credit': {'kind': 'saved_rejected_categorical_scorer'}}})+'\n')
    saved = marker.read_bytes()
    with pytest.raises(AnnotationScoringUnavailable, match='use_original_snapshot_for_historical_replay'):
        _load_policy(tmp_path, None, None, resume=True)
    assert source.read_bytes() == original
    assert marker.read_bytes() == saved


class NumericAnnotationFixture:
    """Caller-supplied numerical operand, not a biological score definition."""
    def __init__(self):
        self.value = .8
        self.calls = 0

    def __call__(self, store, scope):
        self.calls += 1
        return {'credit': self.value, 'axis_components': {'synthetic_component': self.value}}


def fixture_controller(path, initial):
    return FixtureController(str(path), initial, 2)


def test_explicit_numeric_annotation_channel_preserves_progress_and_closed_history(tmp_path):
    directory = tmp_path/'run'
    scorer = NumericAnnotationFixture()
    definitions = {'annotation_score': {'kind': 'explicit_synthetic_numeric_operand'}}
    with Store(tmp_path/'workspace') as store:
        store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')
        tools = ToolRegistry(store)

        def lower_annotation(context):
            assert context['current_credit'] == 0
            assert context['annotation_score'] == .8
            assert context['annotation_evidence_vector'] == {'synthetic_component': .8}
            scorer.value = .25
            return fixture_reason(store)

        def check_separation(context):
            assert context['current_credit'] == 0
            assert context['controller']['scores'] == [0]
            assert context['annotation_score'] == .25
            assert context['annotation_evidence_vector'] == {'synthetic_component': .25}
            return fixture_reason(store, 'intact')

        options = {'run_dir': directory, 'controller_factory': fixture_controller,
            'project_annotation_score': scorer, 'binding_definitions': definitions}
        summary = asyncio.run(run_workflow(store, tools,
            provider=ScriptedProvider([lower_annotation, check_separation]), **options))
        assert summary['credit'] == 0
        assert summary['annotation_score'] == .25
        assert 'annotation_score_status' not in summary
        assert summary['completed_actions'] == 2
        assert [row[0] for row in store.db.execute(
            'SELECT credit FROM runtime_actions ORDER BY decision_index')] == [0, 0]
        before = saved_bytes(store, directory)
        scorer.value = .99
        original_calls = scorer.calls
        replay = asyncio.run(run_workflow(store, tools, provider=ScriptedProvider([]),
            resume=True, **options))
        assert replay == summary
        assert scorer.calls == original_calls
        assert saved_bytes(store, directory) == before


@pytest.mark.parametrize('retrieval', [None,
    {'version': 'scientific_tool_retrieval_v1', 'mode': 'literal_test_v1'}])
def test_current_tool_information_descriptor_reopens_only_with_matching_identity(tmp_path, retrieval):
    from gene_annotation_episode.episode_composition import reopen_scientific_binding
    from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
    from test_scientific_process_library import independent_source

    source, directory = tmp_path/'source', tmp_path/'run'
    independent_source(source)
    descriptor = prepare_scientific_binding(run_directory=directory, source_directory=source,
        tool_catalog=[{'name': 'state.query', 'description': 'Read stored fixture metadata.',
            'input_schema': {'type': 'object', 'properties': {}, 'additionalProperties': False}}],
        child_roles=('scientific_process',), tool_retrieval=retrieval)
    assert descriptor['version'] == 'scientific_process_episodes_v7'
    assert ('tool_retrieval' in descriptor['configuration']) is (retrieval is not None)
    before = {str(path.relative_to(directory)): path.read_bytes()
        for path in directory.rglob('*') if path.is_file()}
    services = object()
    factory, = _saved_episode_factories({'episode_bindings': [descriptor]}, directory)
    restored = factory(services)
    assert restored.services is services
    assert restored.tool_library.supports_tool_info
    assert restored.as_record() == descriptor
    assert restored.tool_retrieval == retrieval
    changed = deepcopy(descriptor)
    changed['implementation_sha256'] = '0'*64
    with pytest.raises(DurableExecutionError) as failure:
        reopen_scientific_binding(services, descriptor=changed, directory=directory)
    assert failure.value.failure['code'] == 'identity_conflict'
    assert {str(path.relative_to(directory)): path.read_bytes()
        for path in directory.rglob('*') if path.is_file()} == before
