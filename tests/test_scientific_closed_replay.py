"""Closed scientific identity restoration; all work here is an engineering fixture.

The fixture saves an earlier mechanics identity through the actual episode loop,
then restores today's binding. It never rewrites its saved request or archive to
make replay pass. The separately retained live Rfam regression remains unchanged.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

from method_loop.archive import iter_json

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import WorkflowError
from gene_annotation_episode.runtime import TypedReportContract
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.state import Store
from test_runtime import ScriptedProvider
from test_scientific_process_runtime import (Scenario, action, assert_supplied_molecule_reasoning,
    prepared_child, supplied_molecule_reasoning)


ROOT_GOAL = 'Resolve the closed replay fixture uncertainty'
EARLIER_IMPLEMENTATION = hashlib.sha256(b'earlier engineering fixture implementation').hexdigest()
HISTORY_TABLES = ('runtime_episodes', 'runtime_model_calls', 'runtime_actions',
    'runtime_observations', 'runtime_forms', 'runtime_report_attempts')


def forbidden(*args, **kwargs):
    raise AssertionError('closed replay attempted new work')


class NoWorkProvider:
    complete = forbidden

    async def release(self, episode_id):
        pass


def history(store):
    return {table: [dict(row) for row in store.db.execute(
        'SELECT * FROM ' + table + ' ORDER BY rowid')] for table in HISTORY_TABLES}


def archive_hashes(directory):
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (directory / 'archive').iterdir() if path.is_file()}


def archive_value(record):
    return json.loads(''.join(iter_json(record.as_record())))


def recorded_context(workflow, row):
    request = json.loads(row['request'])
    return BindingContext(workflow.run_id, row['episode_id'], 'scientific_process',
        json.loads(row['path']), request['message']['scope'],
        request['message']['episode_assignment'], request)


@pytest.fixture
def closed_case(tmp_path, monkeypatch):
    with Store(tmp_path / 'state') as store:
        original_record = ScientificProcessEpisodes.as_record

        def earlier_record(binding):
            return {**original_record(binding), 'implementation_sha256': EARLIER_IMPLEMENTATION}

        with monkeypatch.context() as earlier:
            earlier.setattr(ScientificProcessEpisodes, 'as_record', earlier_record)
            case = Scenario(tmp_path, store)
            provider = ScriptedProvider([case.commission(),
                action('fixture.inspect', {'value': 2}, 'unresolved'),
                action('process.entry', {'option_id': 'P01'}, 'qualified'),
                action('process.entry', {'option_id': 'P77'}, 'qualified'),
                action('episode.history', {'view': 'index'}, 'qualified'),
                supplied_molecule_reasoning(store, case.scope)])
            original = case.workflow(provider)
            root = original.build('annotation', 'root', ROOT_GOAL, case.scope)
            record = asyncio.run(root.run_async(original.context))
            result = asyncio.run(root.build_result(record))
            assert_supplied_molecule_reasoning(store, case.scope)
            expected_archive = archive_value(record)
            assert len(provider.contexts) == 6
            assert len(case.tools.calls) == 1

        before = history(store)
        saved, = [row for row in before['runtime_episodes']
            if json.loads(row['path'])[-1][0] == 'scientific_process']
        assert saved['state'] == 'yielded'
        case.descriptors[0] = original.scientific_process_binding.as_record()
        assert case.descriptors[0]['implementation_sha256'] != EARLIER_IMPLEMENTATION
        workflow = case.workflow(NoWorkProvider())
        monkeypatch.setattr(case.tools, 'execute', forbidden)
        yield SimpleNamespace(case=case, store=store, workflow=workflow,
            saved=saved, context=recorded_context(workflow, saved), history=before,
            archive=expected_archive, result=plain(result.as_record()),
            archive_hashes=archive_hashes(case.directory))


def rebuild_child(fixture, selection=None):
    """Use real preparation and build ports, independently of parent action replay."""
    workflow, case = fixture.workflow, fixture.case
    selected = deepcopy(selection or case.commission()['selection'])
    root = workflow.build('annotation', 'root', ROOT_GOAL, case.scope)
    scope = selected['scope']
    schema, initial = json.loads(selected['schema_json']), json.loads(selected['initial_report_json'])
    binding = workflow.scientific_process_binding
    prepared = binding.prepare_invocation(workflow.binding_context(root.source),
        'scientific_process', selected['assignment'], scope, 'replay:prepare', invocation={
            'objective': selected['goal'], 'purpose': selected['purpose'],
            'report_schema': schema, 'initial_report': initial})
    contract = TypedReportContract(selected['purpose'], schema,
        workflow.resolver(scope, grain='scientific_process'))
    child = workflow.build('scientific_process', 'child_0', selected['goal'], scope,
        parent=root.goal, parent_path=root.source.path, contract=contract, initial=initial,
        episode_assignment=prepared['assignment'], scientific_process=prepared['scientific_process'])
    return child


def test_fresh_scientific_episode_keeps_current_full_mechanics(tmp_path):
    with Store(tmp_path / 'state') as store:
        case = Scenario(tmp_path, store)
        workflow = case.workflow(NoWorkProvider())
        _, child = prepared_child(case, workflow)
        binding = workflow.scientific_process_binding
        context = workflow.binding_context(child.source)
        saved = workflow.journal.row('runtime_episodes', context.episode_id)
        assert json.loads(saved['request'])['message']['scientific_process']['mechanics_binding'] == binding.as_record()
        assert workflow.services.scientific_closed_request(context) is None
        assert binding.restore_closed_process(context) is None
        binding.validate_execution_context(context)


def test_closed_replay_preserves_original_identity_form_credit_history_and_archive(closed_case):
    fixture = closed_case
    binding = fixture.workflow.scientific_process_binding
    assert fixture.workflow.services.scientific_closed_request(fixture.context) == plain(fixture.context.request)
    binding.validate_context(fixture.context)
    root = fixture.workflow.build('annotation', 'root', ROOT_GOAL, fixture.case.scope)
    record = asyncio.run(root.run_async(fixture.workflow.context))
    result = asyncio.run(root.build_result(record))
    assert archive_value(record) == fixture.archive
    assert plain(result.as_record()) == fixture.result
    assert history(fixture.store) == fixture.history
    assert archive_hashes(fixture.case.directory) == fixture.archive_hashes
    child = rebuild_child(fixture)
    assert plain(child.request.as_record()) == plain(fixture.context.request)
    assert child.request.message.as_record()['scientific_process']['mechanics_binding'][
        'implementation_sha256'] == EARLIER_IMPLEMENTATION
    assert fixture.saved['initial_credit'] == 0
    child_actions = [row for row in fixture.history['runtime_actions']
        if row['episode_id'] == fixture.context.episode_id]
    assert len(child_actions) == 4 and [row['credit'] for row in child_actions] == [1, 1, 1, 1]
    assert len(fixture.history['runtime_observations']) == 6
    assert len(fixture.case.tools.calls) == 1
    assert history(fixture.store) == fixture.history


@pytest.mark.parametrize('missing', ['episode', 'active', 'completion', 'archive', 'closing', 'form'])
def test_active_or_incomplete_history_cannot_restore_old_mechanics(closed_case, missing):
    fixture = closed_case
    database, episode_id = fixture.store.db, fixture.context.episode_id
    if missing == 'episode':
        database.execute('DELETE FROM runtime_episodes WHERE episode_id=?', (episode_id,))
    elif missing == 'closing':
        database.execute('DELETE FROM runtime_forms WHERE episode_id=?', (episode_id,))
    elif missing == 'form':
        database.execute('UPDATE runtime_forms SET form=NULL WHERE episode_id=?', (episode_id,))
    elif missing == 'active':
        database.execute("UPDATE runtime_episodes SET state='active' WHERE episode_id=?", (episode_id,))
    else:
        database.execute('UPDATE runtime_episodes SET ' + missing + '=NULL WHERE episode_id=?', (episode_id,))
    before = history(fixture.store)
    binding = fixture.workflow.scientific_process_binding
    assert fixture.workflow.services.scientific_closed_request(fixture.context) is None
    assert binding.restore_closed_process(fixture.context) is None
    with pytest.raises(ContractError, match='scientific_filled_identity_mismatch'):
        binding.validate_context(fixture.context)
    if missing != 'episode':
        with pytest.raises(WorkflowError, match='reconstructed immutable assignment differs'):
            rebuild_child(fixture)
    assert history(fixture.store) == before


@pytest.mark.parametrize('change', ['scope', 'goal', 'purpose', 'assignment', 'context',
    'initial_report', 'requested_form', 'selected_tool', 'selected_thought'])
def test_closed_reconstruction_rejects_changed_parent_operands(closed_case, change):
    fixture = closed_case
    selection = deepcopy(fixture.case.commission()['selection'])
    if change == 'scope':
        selection['scope'] = {'subject_refs': []}
    elif change == 'goal':
        selection['goal'] = 'Resolve a different question'
    elif change == 'purpose':
        selection['purpose'] = 'Return a different measurement meaning'
    elif change == 'assignment':
        selection['assignment']['constraints']['target_only'] = False
    elif change == 'context':
        selection['assignment']['context']['condition'] = 'different supplied condition'
    elif change == 'initial_report':
        selection['initial_report_json'] = '{"status":"qualified"}'
    elif change == 'requested_form':
        schema = json.loads(selection['schema_json'])
        schema['properties']['status']['enum'].append('unavailable')
        selection['schema_json'] = json.dumps(schema)
    elif change == 'selected_tool':
        selection['assignment']['selection']['child_tool_info'] = []
    else:
        selection['assignment']['selection']['thought_pattern'] = fixture.case.library.reference('P77')
    with pytest.raises(ContractError, match='scientific_filled_identity_mismatch'):
        rebuild_child(fixture, selection)
    assert history(fixture.store) == fixture.history


def test_closed_context_rejects_changed_current_binding_configuration(closed_case):
    fixture = closed_case
    original = fixture.workflow.scientific_process_binding
    changed = ScientificProcessEpisodes(fixture.workflow.services, library=original.library,
        tool_library=original.tool_library, child_roles=('scientific_process',))
    with pytest.raises(ContractError, match='scientific_filled_identity_mismatch'):
        changed.restore_closed_process(fixture.context)
    with pytest.raises(ContractError, match='scientific_filled_identity_mismatch'):
        changed.validate_context(fixture.context)


@pytest.mark.parametrize('change', ['run', 'episode', 'path', 'journal_path'])
def test_closed_request_requires_exact_run_episode_and_path(closed_case, change):
    fixture, context = closed_case, closed_case.context
    if change == 'run':
        context = replace(context, run_id='different-run')
    elif change == 'episode':
        context = replace(context, episode_id='episode_' + '0' * 64)
    elif change == 'path':
        context = replace(context, path=(*context.path[:-1], ('scientific_process', 'different-child')))
    else:
        fixture.store.db.execute('UPDATE runtime_episodes SET path=? WHERE episode_id=?',
            (json.dumps([['annotation', 'root'], ['scientific_process', 'different-child']]), context.episode_id))
    with pytest.raises(ValueError, match='scientific_closed_request_identity_mismatch'):
        fixture.workflow.services.scientific_closed_request(context)
    with pytest.raises(ValueError):
        fixture.workflow.scientific_process_binding.validate_context(context)


@pytest.mark.parametrize('bad_hash', [None, 23, 'x' * 64, 'a' * 63, 'A' * 64])
def test_closed_request_requires_valid_original_hash(closed_case, bad_hash):
    fixture = closed_case
    saved = plain(fixture.context.request)
    saved['message']['scientific_process']['mechanics_binding']['implementation_sha256'] = bad_hash
    fixture.store.db.execute('UPDATE runtime_episodes SET request=? WHERE episode_id=?',
        (json.dumps(saved), fixture.context.episode_id))
    with pytest.raises(ContractError, match='scientific_closed_implementation_identity_invalid'):
        rebuild_child(fixture)


def test_closed_request_does_not_accept_an_unrelated_candidate_hash(closed_case):
    fixture = closed_case
    request = plain(fixture.context.request)
    request['message']['scientific_process']['mechanics_binding']['implementation_sha256'] = 'f' * 64
    with pytest.raises(ContractError, match='scientific_filled_identity_mismatch'):
        fixture.workflow.scientific_process_binding.restore_closed_process(
            replace(fixture.context, request=request))


def test_lightweight_services_without_closed_port_keep_strict_binding(closed_case):
    fixture = closed_case

    class WithoutClosedRequest:
        def __getattr__(self, name):
            if name == 'scientific_closed_request':
                raise AttributeError(name)
            return getattr(fixture.workflow.services, name)

    original = fixture.workflow.scientific_process_binding
    binding = ScientificProcessEpisodes(WithoutClosedRequest(), library=original.library,
        tool_library=original.tool_library, child_roles=original.child_roles('scientific_process'))
    assert binding.restore_closed_process(fixture.context) is None
    with pytest.raises(ContractError, match='scientific_filled_identity_mismatch'):
        binding.validate_context(fixture.context)


@pytest.mark.parametrize('dispatch', ['model', 'action', 'child', 'workflow_tool', 'binding_tool'])
def test_historical_identity_cannot_authorize_new_dispatch(closed_case, dispatch):
    fixture = closed_case
    child = rebuild_child(fixture)
    workflow = fixture.workflow
    with pytest.raises(ContractError, match='scientific_execution_identity_mismatch'):
        if dispatch == 'model':
            child.source.calls = 99
            asyncio.run(child.source.call({}, {}))
        elif dispatch == 'action':
            asyncio.run(child.source.execute(action('fixture.inspect', {'value': 9})['selection'], 99))
        elif dispatch == 'child':
            workflow.selected(child.source, fixture.case.commission()['selection'], 99)
        elif dispatch == 'workflow_tool':
            asyncio.run(workflow.execute(child.source, 'process.entry', {'option_id': 'P01'},
                decision_index=99, operation_key='new-work'))
        else:
            asyncio.run(workflow.scientific_process_binding.execute(
                workflow.binding_context(child.source), 'fixture.inspect', {'value': 9}, 'new-work'))
    assert history(fixture.store) == fixture.history
    assert archive_hashes(fixture.case.directory) == fixture.archive_hashes
    assert len(fixture.case.tools.calls) == 1


def test_saved_model_and_action_replay_do_not_require_current_execution_identity(closed_case):
    fixture = closed_case
    child = rebuild_child(fixture)
    calls = [row for row in fixture.history['runtime_model_calls']
        if row['episode_id'] == child.source.episode_id]
    first_call = min(calls, key=lambda row: row['call_index'])
    response, index, _, _ = asyncio.run(child.source.call({}, {}))
    assert response == json.loads(first_call['response']) and index == first_call['call_index'] == 0
    saved_action = next(row for row in fixture.history['runtime_actions']
        if row['episode_id'] == child.source.episode_id and row['decision_index'] == 0)
    asyncio.run(child.source.execute(json.loads(saved_action['action']), 0))
    assert history(fixture.store) == fixture.history
    assert archive_hashes(fixture.case.directory) == fixture.archive_hashes
    assert len(fixture.case.tools.calls) == 1
