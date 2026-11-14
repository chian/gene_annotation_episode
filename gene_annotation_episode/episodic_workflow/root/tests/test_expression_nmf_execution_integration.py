"""Actual shared NMF catalogs, supplied-input custody and return schemas.

These use recorded software identities and authored receipt contexts. They do
not replace the separately selected native run or full Workflow verification.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator
from method_loop.episode import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.communication import plain, validate_closed_schema, validate_form
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.expression_nmf_common import MODE, OPERATION, default_nmf_parameters, identity
from gene_annotation_episode.expression_nmf_execution_information import describe_expression_nmf_result
from gene_annotation_episode.expression_nmf_return_views import SAVED_SOURCE, expression_nmf_fact_sources
from gene_annotation_episode.native_expression_nmf_contracts import POLICY, expression_nmf_environment, requested_job_from_expression_nmf
from gene_annotation_episode.runtime import Record, TypedReportContract
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


RAW = b'gene,A,B,B\ng,1,2,0\ng,0,1,3\ng3,1,3,3\n'


def context(f, *, parent=None):
    path = (('annotation', 'root'),) if parent is None else parent.path + (('launch', 'child_0'),)
    role, episode_id = path[-1][0], EpisodeRef(f.run_id, path).episode_id
    manifest = f.receipts.bind(episode_id, None if parent is None else parent.episode_id)
    schema = {'type': 'object', 'properties': {'received': {'type': 'boolean'}},
        'required': ['received'], 'additionalProperties': False}
    contract = None if parent is None else TypedReportContract('Return the selected input facts', schema, lambda *_: True)
    goal = (EpisodeGoal.root(objective='Verify supplied expression matrix access', result_contract={'role': role})
        if parent is None else EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)['goal']),
            objective='Verify supplied expression matrix access', result_contract=schema))
    request = EpisodeRequest(goal, Record({'scope': f.scope, 'episode_assignment': {},
        'initial_report': {} if parent is None else {'received': False}, 'knowledge_inheritance': manifest}), contract).as_record()
    value = BindingContext(f.run_id, episode_id, role, path, f.scope, {}, request)
    f.journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
        'request': canonical(request), 'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
    if parent is not None:
        f.journal.save('runtime_actions', {'episode_id': parent.episode_id, 'decision_index': 0,
            'action': canonical({'kind': 'episode_child', 'role': role, 'assignment': {}, 'scope': f.scope,
                'purpose': contract.decision, 'schema_json': canonical(schema)}), 'result': None, 'credit': None})
    return value


@pytest.fixture
def selected(tmp_path):
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        f = SimpleNamespace(store=store, scope=store.validate_scope(), run_id='nmf488-shared', directory=tmp_path)
        f.journal, f.receipts = Journal(store, f.run_id), EpisodeReceipts(store, f.run_id)
        f.root = context(f)
        f.reference = store.artifact(RAW, 'text/csv')
        f.receipts.receive(f.root.episode_id, [f.reference], kind='initial')
        software = json.loads(Path(os.environ['NMF488_SOFTWARE']).read_text())
        workspace = tmp_path / 'workspace'
        workspace.mkdir()
        f.input_path = store.path / 'artifacts' / identity(RAW)['sha256'][:2] / identity(RAW)['sha256']
        job = {'version': 'native_expression_nmf_job_v1', 'operation': OPERATION, 'mode': MODE,
            'input': {'path': str(f.input_path), **identity(RAW), 'artifact_ref': f.reference,
                'delimiter': ',', 'metadata': {'units': 'counts'}},
            'parameters': default_nmf_parameters(rank=2, normalization='none'),
            'software': software, 'output_prefix': 'native-output'}
        f.request = requested_job_from_expression_nmf(job,
            environment=expression_nmf_environment(software, attempt_directory=str(workspace / 'selected-context')))
        f.assignment = {'requested_job': f.request}
        f.resources = {'here': {'kind': 'local', 'workspace': str(workspace), 'policy': deepcopy(POLICY),
            'native_expression_nmf': [{'operation': OPERATION, 'mode': MODE, 'software': software}]}}
        f.tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
        f.owner = ExecutionEpisodes(None, store=store, directory=tmp_path / 'run', run_id=f.run_id,
            resources=f.resources, initial_information={}, tool_registry=f.tools, handoff_unit=3,
            acquired_record_unit=2, log_window_bytes=128, log_roles=('stdout', 'stderr'))
        yield f


def selector():
    return {'version': 'expression_nmf_result_selector_v1', 'mode': 'native_result',
        'projection': {'view': 'fit_diagnostics', 'fields': ['sse', 'cell_count'],
            'row_window': {'offset': 0, 'limit': 2}}, 'saved_sheet_file': None}


def test_actual_library_contract_and_selected_resource_route(selected):
    f = selected
    entry, = [r for r in f.owner.resource_tool_contracts() if r['name'] == OPERATION]
    assert entry['invocation_route'] == {'kind': 'commission', 'routes': [
        {'entry_role': 'launch', 'resource_id': 'here', 'resource_role': 'launch_local'}]}
    assert Draft202012Validator(entry['input_schema']).is_valid(f.request)
    assert OPERATION not in f.tools.catalog()
    factory = ExecutionServiceFactory(f.resources, {}, 3, 2, 1, log_window_bytes=128)
    application = factory(f.store, run_id=f.run_id, directory=f.directory / 'factory', tool_registry=f.tools)
    library = ScientificToolLibrary.freeze(f.directory / 'library', catalog=f.tools.catalog(),
        tool_info=True, resource_catalogs=application.resource_tool_catalogs)
    info, = [r for r in library.parent_tool_info() if r['name'] == OPERATION]
    assert set(info) == {'name', 'description', 'resources'}
    choice = [{'name': OPERATION, 'resources': 'local'}]
    assert library.resolve_invocations(choice) == [entry]
    full, = library.resolve_tool_info(choice)
    assert full == {k: entry[k] for k in ('name', 'description', 'resources', 'instructions')}
    with pytest.raises(ValueError, match='scientific_tool_unknown'):
        library.resolve_invocations([{'name': OPERATION, 'resources': 'hpc'}])


def test_exact_result_mode_and_received_fact_contract(selected):
    f = selected
    target = {'resource_kind': 'local', 'assignment': f.assignment}
    assert f.owner._selector({'selector': selector()}, target) == selector()
    with pytest.raises(ValueError):
        f.owner._selector({'selector': {'paths': ['/arbitrary']}}, target)
    with pytest.raises(ValueError, match='target_conflict'):
        f.owner._selector({'selector': selector()}, {'resource_kind': 'api', 'assignment': f.assignment})
    assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': 'fixture', 'selector': selector()}
    assert Draft202012Validator(f.owner.assignment_schema('results')).is_valid(assignment)
    declarations = expression_nmf_fact_sources()
    for source, declared in declarations.items():
        assert f.owner.fact_sources('results')[source] == declared
        assert f.owner.received_report_sources('scientific_process')[source] == declared
        form = {'type': 'object', 'properties': {'value': declared['report_schema']},
            'required': ['value'], 'additionalProperties': False}
        validate_closed_schema(form)
        assert validate_form({'value': []}, form) == {'value': []}
        changed = deepcopy(form)
        changed['properties']['value']['items'] = {'type': 'string'}
        with pytest.raises(ValueError):
            validate_closed_schema(changed)


def test_received_matrix_identity_survives_original_byte_loss(selected, monkeypatch):
    f = selected
    versions = [{'reference': f.reference, 'version': None, 'content_sha256': identity(RAW)['sha256']}]
    before = list(f.store.db.iterdump())
    assert f.owner._expression_nmf_inputs(f.root, f.assignment) == [f.reference]
    f.input_path.unlink()
    monkeypatch.setattr(f.store, 'get_artifact', lambda *_: pytest.fail('commission reread scientific bytes'))
    f.owner._versions(versions, f.scope, context=f.root, nmf_assignments=[f.assignment])
    assert list(f.store.db.iterdump()) == before
    changed = deepcopy(versions)
    changed[0]['content_sha256'] = 'f' * 64
    with pytest.raises(ValueError, match='version_conflict'):
        f.owner._versions(changed, f.scope, context=f.root, nmf_assignments=[f.assignment])
    with pytest.raises(ValueError, match='outside_assigned_scope'):
        f.owner._versions(versions, f.scope, context=f.root)


def test_frozen_input_inheritance_does_not_grant_later_parent_input(selected):
    f = selected
    child = context(f, parent=f.root)
    assert f.owner._expression_nmf_inputs(child, f.assignment) == [f.reference]
    raw = RAW.replace(b'1,2,0', b'2,2,0')
    reference = f.store.artifact(raw)
    f.receipts.receive(f.root.episode_id, [reference], kind='own_action')
    changed = deepcopy(f.assignment)
    changed['requested_job']['native_expression_nmf']['input'].update(artifact_ref=reference,
        **identity(raw), path=str(f.store.path / 'artifacts' / identity(raw)['sha256'][:2] / identity(raw)['sha256']))
    with pytest.raises(ValueError, match='not_received'):
        f.owner._expression_nmf_inputs(child, changed)


def test_result_information_preserves_selected_question_without_new_work(selected):
    f = selected
    target = {'version': 'execution_target_v1', 'handle': 'fixture-handoff', 'run_id': f.run_id,
        'resource_id': 'here', 'resource_kind': 'local', 'execution_id': '/fixture/native.json',
        'request_sha256': digest(f.request), 'origin_episode_id': 'fixture-original',
        'assignment': {**f.assignment, 'resource_kind': 'local', 'resource_id': 'here'}, 'scope': f.scope}
    native = describe_expression_nmf_result(target, called_operation='practical.job.start', selector=selector())
    assert native['operation'] == OPERATION and native['called_operation'] == 'practical.job.start'
    assert native['result_selection']['projection']['fields'] == ['sse', 'cell_count']
    assert len(native['selected_outputs']) == 5
    saved = selector()
    saved.update(mode='saved_sheet_recalculation', saved_sheet_file={'artifact_ref': 'artifact_'+'f'*64,
        'sha256': 'f'*64, 'size_bytes': 123, 'format': 'expression_nmf_sheet_v1'})
    described = describe_expression_nmf_result(target, selector=saved)
    assert described['status_operations'] == ['execution.results.status']
    assert described['status_meanings']['fresh_native_observation'] is False
    assert described['selected_outputs'] == []
