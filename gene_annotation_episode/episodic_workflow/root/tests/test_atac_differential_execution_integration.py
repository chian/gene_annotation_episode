"""Shared ATAC selection/receipt boundaries with explicit control fixtures.

The input/software identities here are authored fixtures. These checks do not
claim a native run; full production execution has its separate episode test.
Run only through the bounded packet477 runner.
"""
from copy import deepcopy
import base64
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import ReportBoundaryError, validate_closed_schema, validate_form
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.native_atac_differential_contracts import POLICY, OPERATION, MODE
from gene_annotation_episode.native_atac_differential_tool_info import atac_tool_information
from gene_annotation_episode.atac_differential_return_views import (
    FACT_SOURCES, SAVED_SOURCE, atac_fact_sources,
)
from gene_annotation_episode.atac_differential_result_contracts import SHEET_FORMAT, TABLE_FORMAT
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.tools import ToolRegistry
from test_atac_differential_operands import f, make_assignment


@pytest.fixture
def selected(f, tmp_path):
    assignment = make_assignment(f)
    job = assignment['requested_job']['native_atac_differential']
    workspace = tmp_path / 'work'
    workspace.mkdir()
    binding = {'operation': OPERATION, 'mode': MODE, 'software': job['software']}
    resources = {'here': {'kind': 'local', 'workspace': str(workspace),
        'policy': deepcopy(POLICY), 'native_atac_differential': [binding]}}
    tools = ToolRegistry(f.store, job_limits=deepcopy(POLICY))
    owner = ExecutionEpisodes(None, store=f.store, directory=tmp_path / 'run', run_id=f.run_id,
        resources=resources, initial_information={}, tool_registry=tools,
        handoff_unit=3, acquired_record_unit=2, log_window_bytes=128, log_roles=('stdout', 'stderr'))
    return SimpleNamespace(owner=owner, tools=tools, resources=resources, binding=binding,
        assignment=assignment, job=job, workspace=workspace)


def selector():
    return {'version': 'atac_differential_result_selector_v1', 'mode': 'native_result',
        'comparison_key': 'comparison', 'intervals': [{'chromosome': 'chrToy', 'start': 0, 'end': 12000}],
        'parameters': {'pseudocount': .01, 'cutoff_log10_lr': 3, 'minimum_length_bp': 50, 'maximum_gap_bp': 0},
        'projection': {'kind': 'summary', 'row_window': None, 'run_keys': [], 'categories': []},
        'saved_sheet_bundle': None}


def test_selected_library_entry_reaches_only_bound_local_commission(f, selected, tmp_path):
    owner = selected.owner
    entry, = [row for row in owner.resource_tool_contracts() if row['name'] == OPERATION]
    assert entry['invocation_route'] == {'kind': 'commission', 'routes': [
        {'entry_role': 'launch', 'resource_id': 'here', 'resource_role': 'launch_local'}]}
    assert Draft202012Validator(entry['input_schema']).is_valid(selected.assignment['requested_job'])
    info, = atac_tool_information([selected.binding], resource_kind='local', resource_id='here')
    assert set(info) == {'name', 'description', 'resources', 'instructions'}
    assert all(info[field] == entry[field] for field in info)
    assert OPERATION not in selected.tools.catalog()

    factory = ExecutionServiceFactory(selected.resources, {}, 3, 2, 1, log_window_bytes=128)
    application = factory(f.store, run_id=f.run_id, directory=tmp_path / 'factory', tool_registry=selected.tools)
    library = ScientificToolLibrary.freeze(tmp_path / 'tools', catalog=selected.tools.catalog(),
        tool_info=True, resource_catalogs=application.resource_tool_catalogs)
    parent, = [row for row in library.parent_tool_info() if row['name'] == OPERATION]
    assert set(parent) == {'name', 'description', 'resources'}
    selection = [{'name': OPERATION, 'resources': 'local'}]
    assert library.resolve_tool_info(selection) == [info]
    assert library.resolve_invocations(selection) == [entry]
    with pytest.raises(ValueError, match='scientific_tool_unknown'):
        library.resolve_invocations([{'name': OPERATION, 'resources': 'hpc'}])
    replacement = deepcopy(info)
    replacement['instructions'] = 'Replace the original supplied instructions.'
    with pytest.raises(ValueError, match='scientific_tool_info_changed'):
        library.resolve_tool_info([replacement])


def test_only_exact_resource_mode_and_software_are_advertised(selected):
    owner = selected.owner
    requested = owner._request_schema('here', selected=True)['properties']['requested_job']
    assert Draft202012Validator(requested).is_valid(selected.assignment['requested_job'])
    changed = deepcopy(selected.assignment['requested_job'])
    changed['native_atac_differential']['software']['driver_runtime']['python_sha256'] = 'f' * 64
    assert not Draft202012Validator(requested).is_valid(changed)
    with pytest.raises(ValueError):
        atac_tool_information([selected.binding], resource_kind='hpc', resource_id='elsewhere')


def test_atac_target_cannot_use_generic_file_window_results(selected):
    target = {'resource_kind': 'local', 'assignment': selected.assignment}
    assignment = {'selector': selector()}
    assert selected.owner._selector(assignment, target) == selector()
    with pytest.raises(ValueError):
        selected.owner._selector({'selector': {'paths': ['/unrelated/output']}}, target)
    wrong = deepcopy(assignment)
    wrong['selector']['comparison_key'] = 'different'
    with pytest.raises(ValueError, match='atac_result_comparison_conflict'):
        selected.owner._selector(wrong, target)
    with pytest.raises(ValueError, match='atac_result_target_conflict'):
        selected.owner._selector(assignment, {'resource_kind': 'local', 'assignment': {'requested_job': {}}})
    schema = selected.owner.assignment_schema('results')
    assert Draft202012Validator(schema).is_valid({'version': 'execution_results_assignment_v1',
        'handoff_ref': 'authored-handoff-control', 'selector': selector()})


def test_version_checks_accept_only_original_received_selected_bams(f, selected):
    versions = [{'reference': row['file']['artifact_ref'], 'version': None,
        'content_sha256': row['file']['sha256']} for row in f.request['inputs']]
    assert f.store.reference_subset(f.refs, f.scope) == []
    before = list(f.store.db.iterdump())
    selected.owner._versions(versions, f.scope, context=f.root, atac_assignments=[selected.assignment])
    assert list(f.store.db.iterdump()) == before
    with pytest.raises(ValueError, match='execution_input_outside_assigned_scope'):
        selected.owner._versions(versions, f.scope, context=f.root)
    unrelated = f.store.artifact(b'unreceived input')
    with pytest.raises(ValueError, match='execution_input_outside_assigned_scope'):
        selected.owner._versions([{'reference': unrelated, 'version': None, 'content_sha256': None}],
            f.scope, context=f.root, atac_assignments=[selected.assignment])
    wrong = deepcopy(versions)
    wrong[0]['content_sha256'] = 'f' * 64
    with pytest.raises(ValueError, match='execution_input_version_conflict'):
        selected.owner._versions(wrong, f.scope, context=f.root, atac_assignments=[selected.assignment])


def test_private_atac_artifact_denial_precedes_store_fallback(f, selected, monkeypatch):
    reference = f.refs[0]
    monkeypatch.setattr(selected.owner.atac_results, 'owns_reference', lambda ref: ref == reference)
    monkeypatch.setattr(selected.owner.atac_returns, 'resolve_received', lambda *_: False)
    assert selected.owner.resolve_received_reference(f.root, reference, None) is False
    assert selected.owner.resolve(f.root, reference, 'artifact') is False
    with pytest.raises(ValueError, match='protected_reference_denied'):
        selected.owner._versions([{'reference': reference, 'version': None, 'content_sha256': None}],
            f.scope, context=f.root, atac_assignments=[selected.assignment])


@pytest.mark.parametrize('source', FACT_SOURCES)
def test_registered_facts_remain_exact_top_level_fields(source):
    node = atac_fact_sources()[source]['report_schema']
    schema = {'type': 'object', 'properties': {'measurements': deepcopy(node)},
        'required': ['measurements'], 'additionalProperties': False}
    validate_closed_schema(schema)
    assert validate_form({'measurements': []}, schema) == {'measurements': []}
    changed = deepcopy(schema)
    changed['properties']['measurements']['description'] = 'Changed scientific contract'
    with pytest.raises(ReportBoundaryError, match='registered source'):
        validate_closed_schema(changed)
    nested = {'type': 'object', 'properties': {'nested': schema}, 'required': ['nested'], 'additionalProperties': False}
    with pytest.raises(ReportBoundaryError, match='whole top-level'):
        validate_closed_schema(nested)


def test_saved_bundle_semantics_visit_sheet_and_every_track_reference(f):
    sheet = {'artifact_ref': 'artifact_' + '1' * 64, 'sha256': '1' * 64, 'size_bytes': 17, 'format': SHEET_FORMAT}
    table = {'artifact_ref': 'artifact_' + '2' * 64, 'sha256': '2' * 64, 'size_bytes': 27, 'format': TABLE_FORMAT}
    bundle = {'sheet': sheet, 'tables': [{'track_key': key, 'file': deepcopy(table)} for key in ('one', 'two')]}
    schema = {'type': 'object', 'properties': {'saved': atac_fact_sources()[SAVED_SOURCE]['report_schema']},
        'required': ['saved'], 'additionalProperties': False}
    visited = []
    assert validate_form({'saved': [bundle]}, schema,
        lambda ref, ns: visited.append((ref, ns)) or True) == {'saved': [bundle]}
    assert visited == [(sheet['artifact_ref'], 'artifact'), (table['artifact_ref'], 'artifact'),
        (table['artifact_ref'], 'artifact')]
    with pytest.raises(ReportBoundaryError, match='reference is unavailable'):
        validate_form({'saved': [bundle]}, schema, lambda ref, ns: ref == sheet['artifact_ref'])
    invalid = deepcopy(bundle)
    invalid['tables'][1]['track_key'] = 'one'
    with pytest.raises(ReportBoundaryError, match='Invalid recorded ATAC fact'):
        validate_form({'saved': [invalid]}, schema, lambda *_: True)


def test_native_and_saved_origins_are_distinct_registered_facts(selected):
    from gene_annotation_episode.native_atac_differential_results import ORIGIN, SAVED_ORIGIN
    schema = selected.owner.fact_sources('results')['execution_result_origin']['report_schema']
    assert ORIGIN != SAVED_ORIGIN
    for origin in (ORIGIN, SAVED_ORIGIN, None):
        assert Draft202012Validator(schema).is_valid(origin)
    wrong = dict(ORIGIN, content_location='invented_acquisition')
    assert not Draft202012Validator(schema).is_valid(wrong)


def test_completion_uses_original_atac_receipt_only(selected, monkeypatch):
    context = SimpleNamespace(role='results', assignment={'selector': selector()})
    proof = {'version': 'practical_completion_v1', 'run_id': 'fixture', 'episode_id': 'fixture',
        'assignment_sha256': 'a' * 64, 'endpoint': 'usable_handoff', 'operation_key': 'original-action',
        'receipt_sha256': 'b' * 64, 'validation_keys': ['qualified_requested_atac_delivery']}
    monkeypatch.setattr(selected.owner.atac_results, 'completion', lambda _: proof)
    assert selected.owner._native_results_complete(context, []) is False
    assert selected.owner.completion_for_action(context, 'original-action') == proof
    assert selected.owner.completion_for_action(context, 'another-action') is None
    assert selected.owner.verify_completion(context, proof)
    assert not selected.owner.verify_completion(context, dict(proof, receipt_sha256='c' * 64))


@pytest.mark.parametrize('channels', [('stdout', 'stderr'), ('stderr',), ()])
def test_all_native_command_logs_have_distinct_shared_progress_identities(tmp_path, channels):
    from gene_annotation_episode.native_atac_differential_observations import atac_observed_files
    from gene_annotation_episode.progress_records import validate_resource_observation
    from test_native_atac_differential_contracts import plan_fixture

    plan = plan_fixture(tmp_path)
    expected = {}
    for specification in plan['outputs']:
        channel = specification['role']
        if channel not in {'stdout', 'stderr'}:
            continue
        path = Path(plan['attempt_directory']) / specification['relative_path']
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = ('authored control log for ' + specification['file_key'] + '\n').encode()
        path.write_bytes(raw)
        role = channel if specification['step_key'] is None else specification['step_key'] + ':' + channel
        if channel in channels:
            expected[role] = (str(path), raw)

    outputs, logs, available = atac_observed_files(plan, {'terminal': True, 'quiescent': True},
        log_window_bytes=19, log_roles=channels)
    observation = validate_resource_observation({'observed_at': '2026-10-27T00:00:00+00:00',
        'state': 'completed', 'returncode': 0, 'failure_code': None, 'result_available': available,
        'measurements': [], 'outputs': outputs, 'logs': logs, 'provenance_refs': [], 'native': {}})
    assert len({row['role'] for row in observation['outputs']}) == len(plan['outputs'])
    assert set(row['role'] for row in logs) == set(expected)
    assert len(logs) == len(expected) == 4 * len(channels)
    for row in logs:
        path, raw = expected[row['role']]
        assert row['path'] == path and row['observed_size'] == len(raw)
        assert row['offset'] == len(raw) - 19
        assert base64.b64decode(row['bytes_base64']) == raw[-19:]
        output, = [item for item in outputs if item['role'] == row['role']]
        assert output['bytes'] == len(raw) and output['writer_closed']
    assert not available


def test_actual_worker_snapshot_preserves_single_file_dependency_directory(tmp_path):
    import os
    import typing_extensions
    from gene_annotation_episode.local_jobs import LocalJobPolicy
    from gene_annotation_episode.native_atac_differential_preparation import _snapshot

    directory = tmp_path / 'worker'
    intent = _snapshot({'directory': str(directory)}, LocalJobPolicy(**POLICY))
    single_file, = [row for row in intent['dependencies'] if row['distribution'] == 'typing-extensions']
    package_directory = Path(typing_extensions.__file__).resolve().parent
    assert single_file['package_root'] == str(package_directory)
    paths = intent['environment']['PYTHONPATH'].split(os.pathsep)
    assert paths[0] == str(directory / 'source_snapshot')
    assert str(package_directory) in paths
    assert str(package_directory.parent) not in paths
    assert len(paths) == len(set(paths))
