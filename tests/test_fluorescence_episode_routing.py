"""Episode routing with real contracts, numerical readers and return custody.

Declared software pins and controlled closed-result/native-backend ports make
these boundary tests. They do not claim an installed producer or full Workflow.
The coordinator runs this module only in its selected bounded lifecycle.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shutil

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import (
    form_with_facts, plain, validate_closed_schema, validate_form,
)
from gene_annotation_episode.domain import obj
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, NATIVE_RESULT_ORIGIN
from gene_annotation_episode.execution_progress import ExecutionTargetReader, describe_execution_target
from gene_annotation_episode.fluorescence_context_views import project_fluorescence_context
from gene_annotation_episode.fluorescence_event_calculations import calculate_fluorescence_sheet
from gene_annotation_episode.fluorescence_event_contracts import canonical as numerical_canonical
from gene_annotation_episode.fluorescence_event_readers import parse_fluorescence_csv
from gene_annotation_episode.fluorescence_event_sheet import populate_fluorescence_sheet
from gene_annotation_episode.fluorescence_execution_common import identity
from gene_annotation_episode.fluorescence_execution_information import describe_fluorescence_result
from gene_annotation_episode.fluorescence_result_views import project_fluorescence_result
from gene_annotation_episode.fluorescence_return_views import (
    CONTEXT_SOURCE, FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE,
    fluorescence_fact_sources,
)
from gene_annotation_episode.native_fluorescence_contracts import (
    OPERATIONS, POLICY, fluorescence_environment, requested_job_from_fluorescence,
)
from gene_annotation_episode.native_fluorescence_results import ORIGIN, operation_catalog
from gene_annotation_episode.practical_receipt_information import PROVIDER
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_fluorescence_local_routing import (
    assignment_and_configuration, backend, start, target_identity,
)
from test_fluorescence_result_receipts import receipt_fixture
from test_fluorescence_returns import Fixture, form_schema
from test_native_fluorescence_contracts import event_input, job


def _owner(f, resources=None):
    return ExecutionEpisodes(None, store=f.store, directory=f.directory / 'run', run_id=f.run_id,
        resources=f.resources if resources is None else resources, initial_information={},
        tool_registry=f.tools, handoff_unit=3, acquired_record_unit=2,
        log_window_bytes=128, log_roles=('stdout', 'stderr'))


def _request(f, selected):
    return requested_job_from_fluorescence(selected, environment=fluorescence_environment(
        selected['software'], attempt_directory=str(Path(f.assignment['workspace']) / 'caller-temporaries')))


def _cell(kind='population', *, gate='gate-0', metric='selected_event_count'):
    return dict(kind=kind, gate_key=gate, domain_key='domain-0' if kind == 'intensity' else None,
        channel_key='channel-0' if kind == 'intensity' else None, control_key=None,
        native_report_key=None, denominator='none', metric=metric)


def _selector(f, *, saved=False, contexts=False):
    return dict(version='fluorescence_result_selector_v1',
        mode='saved_sheet_recalculation' if saved else 'native_result',
        selection=deepcopy(f.projection['selection']), context_fields=['sources', 'samples'] if contexts else [],
        saved_sheet_file=deepcopy(f.sheet) if saved else None,
        parameters=deepcopy(f.selected['parameters']) if saved else None)


def _results(f, *, saved=False, sources=(PROJECTION_SOURCE,), index=0, parent=None):
    child = f.child(f.root if parent is None else parent, form_schema(*sources), index=index,
        saved=f.sheet if saved else None)
    assignment = plain(child.assignment)
    assignment['selector'] = _selector(f, saved=saved, contexts=CONTEXT_SOURCE in sources)
    request = plain(child.request)
    request['message']['episode_assignment'] = assignment
    child = replace(child, assignment=assignment, request=request)
    f.persist(child)
    parent = f.root if parent is None else parent
    row = f.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
        (f.run_id, parent.episode_id, index)).fetchone()
    action = json.loads(row['action'])
    action['assignment'] = assignment
    f.journal.save('runtime_actions', dict(episode_id=parent.episode_id, decision_index=index,
        action=canonical(action), result=None, credit=None))
    return child


@pytest.fixture
def selected(tmp_path, monkeypatch):
    with Store(tmp_path / 'state') as store:
        f = Fixture(store)
        f.directory = tmp_path
        f.assignment, configuration = assignment_and_configuration(tmp_path)
        inputs = [event_input(tmp_path / 'events', index=0),
            event_input(tmp_path / 'events', b'signal\n100\n200\n', index=1)]
        f.selected = job(tmp_path / 'events', inputs=inputs)
        support = identity(b'supplied association', format='json')
        support_ref = store.artifact(b'supplied association', 'application/json')
        assert support_ref == support['artifact_ref']
        inputs[0]['sample']['associations'] = [dict(namespace='gene', identifier='supplied target label',
            file=support, source_key=None, location={key: None for key in
                ('record_ordinal', 'line_start', 'line_end', 'byte_start', 'byte_end')})]
        support_path = store.path / 'artifacts' / support['sha256'][:2] / support['sha256']
        f.selected['support_inputs'] = [dict(file=support, path=str(support_path))]
        f.selected['parameters']['intensity_requests'] = [dict(gate_key='gate-0', domain_key='domain-0', channel_key='channel-0')]
        f.input_refs, f.input_paths = [], []
        parsed = []
        for binding in f.selected['inputs']:
            raw = Path(binding['path']).read_bytes()
            reference = store.artifact(raw, 'text/csv')
            assert reference == binding['source']['file']['artifact_ref']
            path = store.path / 'artifacts' / reference[9:11] / reference[9:]
            binding['path'] = str(path)
            f.input_refs.append(reference)
            f.input_paths.append(path)
            parsed.append(parse_fluorescence_csv(raw, **{key: binding[key] for key in
                ('source', 'sample', 'channels', 'domain', 'format_spec')}))
        f.input_refs.append(support_ref)
        f.input_paths.append(support_path)
        f.ledger.receive(f.root.episode_id, f.input_refs, kind='initial')
        f.assignment['requested_job'] = _request(f, f.selected)
        f.resources = {f.assignment['resource_id']: configuration}
        configuration['native_fluorescence'].append({**deepcopy(configuration['native_fluorescence'][0]), 'operation': OPERATIONS[1]})
        f.tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
        f.owner = _owner(f)
        f.target = dict(version='execution_target_v1', handle='fixture-handoff', run_id=f.run_id,
            resource_id=f.assignment['resource_id'], resource_kind='local', execution_id='/fixture/native.json',
            request_sha256=digest(f.assignment['requested_job']), origin_episode_id='fixture-original',
            assignment=deepcopy(f.assignment), scope=f.scope)
        f.numerical_sheet = populate_fluorescence_sheet(parsed, **f.selected['definitions'])
        f.components = calculate_fluorescence_sheet(f.numerical_sheet, parameters=f.selected['parameters'])
        selection = dict(requests=[_cell('intensity', metric='selected_intensity_mean'), _cell(gate='gate-1')], offset=0, limit=1)
        f.projection = project_fluorescence_result(f.numerical_sheet, f.components, selection=selection)
        f.context_view = project_fluorescence_context(f.numerical_sheet, f.components,
            selection=selection, context_fields=['sources', 'samples'])
        raw = numerical_canonical(f.numerical_sheet) + b'\n'
        reference = store.artifact(raw, 'application/json')
        f.sheet = dict(artifact_ref=reference, sha256=reference[9:], size_bytes=len(raw), format='fluorescence_event_population_sheet_v1')
        f.versions = [dict(reference=ref, version=None, content_sha256=ref[9:]) for ref in f.input_refs]
        # No fixture in this module may accidentally run a native process.
        def forbidden(*args, **kwargs):
            pytest.fail('episode boundary test attempted a native process or resource call')
        monkeypatch.setattr('subprocess.Popen', forbidden)
        monkeypatch.setattr('socket.create_connection', forbidden)
        yield f


def _controlled_returns(f, monkeypatch):
    """Keep actual custody/commission checks; provide the closed-result port."""
    native = f.owner.native_fluorescence_results
    monkeypatch.setattr(native, 'own_fact_groups', f.host.own_fact_groups)
    monkeypatch.setattr(native.receipts, 'contribution_origins', f.host.contribution_origins)
    monkeypatch.setattr(native, 'owns_reference', lambda reference: reference == f.sheet['artifact_ref'])
    f.boundary = f.owner.native_fluorescence_returns


@pytest.mark.parametrize('operation', OPERATIONS)
def test_configured_library_and_request_schema_expose_only_bound_operation(selected, operation):
    # Requires the coordinator's actual tool-information module, never a stub.
    f = selected
    rows = [row for row in f.owner.resource_tool_contracts() if row['name'] == operation]
    entry, = rows
    requested = deepcopy(f.selected)
    requested['operation'] = operation
    request = _request(f, requested)
    assert Draft202012Validator(entry['input_schema']).is_valid(request)
    assignment = {**f.assignment, 'requested_job': request}
    assert Draft202012Validator(f.owner.assignment_schema('launch_local')).is_valid(assignment)
    assert entry['invocation_route'] == {'kind': 'commission', 'routes': [dict(entry_role='launch',
        resource_id=f.assignment['resource_id'], resource_role='launch_local')]}
    assert operation not in f.tools.catalog()
    changed = deepcopy(assignment)
    changed['requested_job']['native_fluorescence']['mode'] = 'laboratory_cell_sorting'
    assert not Draft202012Validator(f.owner.assignment_schema('launch_local')).is_valid(changed)


@pytest.mark.parametrize('change', ['resource', 'kind', 'software', 'parser', 'allocation'])
def test_new_execution_rejects_wrong_bound_resource_software_parser_or_allocation(selected, change):
    f = selected
    bad = deepcopy(f.assignment)
    if change == 'resource': bad['resource_id'] = 'unbound-local'
    if change == 'kind': bad['resource_kind'] = 'hpc'
    if change == 'software':
        altered = deepcopy(f.selected)
        altered['software']['python_version'] = 'different declared interpreter'
        bad['requested_job'] = _request(f, altered)
    if change == 'parser':
        altered = deepcopy(f.selected)
        altered['inputs'][0].update(parser='table_snapshot', format_spec=None)
        bad['requested_job'] = _request(f, altered)
    if change == 'allocation': bad['constraints']['allocation']['memory_bytes'] -= 1
    with pytest.raises(ValueError): f.owner._validate_request(bad)
    assert f.owner._validate_request(f.assignment) == f.assignment


def test_fluorescence_cannot_be_configured_as_remote_or_api(selected):
    f = selected
    for kind in ('pbs_ssh', 'api'):
        resources = deepcopy(f.resources)
        next(iter(resources.values()))['kind'] = kind
        with pytest.raises(ValueError, match='native_fluorescence_resource_execution_binding_unfinished'):
            _owner(f, resources)


def test_original_inputs_are_received_metadata_not_reopened_scientific_bytes(selected, monkeypatch):
    f = selected
    before = list(f.store.db.iterdump())
    assert f.owner._fluorescence_inputs(f.root, f.assignment) == f.input_refs
    for path in f.input_paths: path.unlink()
    monkeypatch.setattr(f.store, 'get_artifact', lambda *_: pytest.fail('commission reread scientific bytes'))
    f.owner._versions(f.versions, f.scope, context=f.root, fluorescence_assignments=[f.assignment])
    assert list(f.store.db.iterdump()) == before
    changed = deepcopy(f.versions)
    changed[0]['content_sha256'] = 'f' * 64
    with pytest.raises(ValueError, match='version_conflict'):
        f.owner._versions(changed, f.scope, context=f.root, fluorescence_assignments=[f.assignment])
    with pytest.raises(ValueError, match='outside_assigned_scope'):
        f.owner._versions(f.versions, f.scope, context=f.root)


def test_input_authority_preserves_frozen_inheritance_and_protected_denial(selected, monkeypatch):
    f = selected
    child = f.child(f.root, obj({'observed': {'type': 'boolean'}}), role='scientific_process')
    assert f.owner._fluorescence_inputs(child, f.assignment) == f.input_refs
    raw = b'signal\n30\n40\n'
    reference = f.store.artifact(raw, 'text/csv')
    f.ledger.receive(f.root.episode_id, [reference], kind='own_action')
    changed = deepcopy(f.selected)
    changed['inputs'][0]['source']['file'] = identity(raw, format='csv')
    changed['inputs'][0]['path'] = str(f.store.path / 'artifacts' / reference[9:11] / reference[9:])
    assignment = {**f.assignment, 'requested_job': _request(f, changed)}
    with pytest.raises(ValueError, match='not_received'):
        f.owner._fluorescence_inputs(child, assignment)
    monkeypatch.setattr(f.owner, 'resolve_received_reference', lambda *_: False)
    with pytest.raises(ValueError, match='protected_reference_denied'):
        f.owner._fluorescence_inputs(f.root, f.assignment)


@pytest.mark.parametrize('change', ['path', 'support_size'])
def test_input_authority_rejects_a_valid_file_at_an_unselected_path_or_identity(selected, change):
    f = selected
    changed = deepcopy(f.selected)
    if change == 'path': changed['inputs'][0]['path'] = str(f.directory / 'different.csv')
    else:
        changed['support_inputs'][0]['file']['size_bytes'] += 1
        changed['inputs'][0]['sample']['associations'][0]['file']['size_bytes'] += 1
    with pytest.raises(ValueError, match='selected_path_mismatch|artifact_metadata_mismatch'):
        f.owner._fluorescence_inputs(f.root, {**f.assignment, 'requested_job': _request(f, changed)})


def test_native_and_saved_selector_contracts_remain_exact(selected):
    f = selected
    for saved in (False, True):
        selector = _selector(f, saved=saved)
        assignment = dict(version='execution_results_assignment_v1', handoff_ref='fixture-handoff', selector=selector)
        assert f.owner._selector(assignment, f.target) == selector
        assert Draft202012Validator(f.owner.assignment_schema('results')).is_valid(assignment)
        with pytest.raises(ValueError, match='target_conflict'):
            f.owner._selector(assignment, {**f.target, 'resource_kind': 'api'})
    for selector in ({'paths': ['/unselected/output']}, {**_selector(f), 'parameters': f.selected['parameters']},
            {**_selector(f, saved=True), 'saved_sheet_file': None}):
        with pytest.raises(ValueError): f.owner._selector({'selector': selector}, f.target)


@pytest.mark.parametrize('saved', [False, True])
@pytest.mark.parametrize('with_context', [False, True])
def test_context_request_and_selector_must_correlate_before_recovery(selected, monkeypatch, saved, with_context):
    f = selected
    sources = (PROJECTION_SOURCE, CONTEXT_SOURCE) if with_context else (PROJECTION_SOURCE,)
    child = _results(f, saved=saved, sources=sources)
    assignment = plain(child.assignment)
    assignment['selector']['context_fields'] = [] if with_context else ['samples']
    request = plain(child.request)
    request['message']['episode_assignment'] = assignment
    inconsistent = replace(child, assignment=assignment, request=request)
    monkeypatch.setattr(f.owner.native_fluorescence_results, 'retained_target',
        lambda *_: pytest.fail('invalid context selection reached acquisition authority'))
    with pytest.raises(ValueError, match='fluorescence_context_selection_mismatch'):
        f.owner.initialize(inconsistent)


def test_requested_context_follows_only_selected_numerical_page(selected, monkeypatch):
    f = selected
    _controlled_returns(f, monkeypatch)
    child = _results(f, sources=(PROJECTION_SOURCE, CONTEXT_SOURCE))
    assert f.projection['returned_row_count'] == 1 and f.projection['has_more']
    assert f.projection['rows'][0]['value'] == 15
    assert [row['key'] for row in f.context_view['samples']] == ['sample-0']
    assert [row['key'] for row in f.context_view['sources']] == ['source-0']
    assert 'metadata' not in f.context_view['sources'][0]
    assert f.context_view['channels'] == f.context_view['domains'] == []
    f.own(child)
    form = f.returned(f.root, child)
    assert f.owner.received_form_references(f.root, form, form_schema(PROJECTION_SOURCE, CONTEXT_SOURCE),
        f'{f.run_id}:{f.root.episode_id}:0:typed_form') == []
    assert not f.owner.resolve_received_reference(f.root, f.sheet['artifact_ref'], 'artifact')
    # A copied label is still a recorded fact; a return cannot rename it.
    mutated = deepcopy(form)
    mutated['field_1'][0]['samples'][0]['label'] = 'guessed sample'
    with pytest.raises(ValueError, match='^fluorescence_return_frozen_facts_conflict$'):
        f.owner.validate_received_report(child, mutated, form_schema(PROJECTION_SOURCE, CONTEXT_SOURCE))


def test_saved_artifact_grant_and_forwarded_closure_keep_original_received_prefix(selected, monkeypatch):
    f = selected
    _controlled_returns(f, monkeypatch)
    schema = form_schema(PROJECTION_SOURCE, SAVED_SOURCE)
    science = f.child(f.root, schema, role='scientific_process')
    first = _results(f, sources=(PROJECTION_SOURCE, SAVED_SOURCE), parent=science)
    f.own(first)
    before = _results(f, saved=True, index=1, parent=science)
    first_form = f.returned(science, first)
    assert f.owner.received_form_references(science, first_form, schema,
        f'{f.run_id}:{science.episode_id}:0:typed_form') == [f.sheet['artifact_ref']]
    with pytest.raises(ValueError, match='not_received'):
        f.owner.native_fluorescence_returns.authenticate_received_saved_sheet(before, f.sheet)
    after = _results(f, saved=True, index=2, parent=science)
    assert f.owner.native_fluorescence_returns.authenticate_received_saved_sheet(after, f.sheet) == (first.episode_id,)
    assert f.owner.resolve_received_reference(science, f.sheet['artifact_ref'], 'artifact')
    assert not f.owner.resolve_received_reference(science, f.sheet['artifact_ref'], 'execution_result')
    closure = f.owner.received_report_facts(science)
    assert closure[PROJECTION_SOURCE] == [f.projection]
    private = set(closure) - set(FACT_SOURCES)
    assert len(private) == 1 and not private & set(f.owner.received_report_sources('scientific_process'))
    form = f.returned(f.root, science)
    # A later independently recorded page cannot expand the closed form.
    f.projection = project_fluorescence_result(f.numerical_sheet, f.components,
        selection={**f.projection['selection'], 'offset': 1})
    later = _results(f, sources=(PROJECTION_SOURCE, SAVED_SOURCE), index=3, parent=science)
    f.own(later)
    f.returned(science, later)
    assert f.owner.received_report_facts(science) == closure
    f.owner.validate_received_report(science, form, schema)


def test_fluorescence_source_schemas_and_origin_union_preserve_generic_contracts(selected):
    f = selected
    for source, declaration in fluorescence_fact_sources().items():
        assert f.owner.fact_sources('results')[source] == declaration
        assert f.owner.received_report_sources('scientific_process')[source] == declaration
        schema = form_schema(source)
        validate_closed_schema(schema)
        assert validate_form({'field_0': []}, schema) == {'field_0': []}
        bad = deepcopy(schema)
        bad['properties']['field_0']['items'] = {'type': 'string'}
        with pytest.raises(ValueError): validate_closed_schema(bad)
    origin = f.owner.fact_sources('results')['execution_result_origin']['report_schema']
    assert Draft202012Validator(origin).is_valid(ORIGIN)
    assert Draft202012Validator(origin).is_valid(NATIVE_RESULT_ORIGIN)
    assert not Draft202012Validator(origin).is_valid({**ORIGIN, 'content_location': 'complete_native_bundle'})
    generic = {**f.target, 'assignment': {'requested_job': {'argv': ['echo']}}}
    assert f.owner._selector({'selector': {'paths': [f.assignment['workspace'] + '/out.txt']}},
        {**generic, 'assignment': {'workspace': f.assignment['workspace'], 'requested_job': {'argv': ['echo']}}})


def test_capability_metadata_distinguishes_native_and_saved_calculations(selected):
    f = selected
    native = describe_fluorescence_result(f.target, called_operation='practical.job.start', selector=_selector(f))
    assert describe_execution_target(f.target)['operation'] == OPERATIONS[0]
    assert native['called_operation'] == 'practical.job.start' and native['selected_outputs']
    assert native['calculation_parameters'] == f.selected['parameters']
    assert native['input_selection'][0]['parser'] == 'csv'
    assert native['input_selection'][0]['channel_bindings'][0]['measurement_origin'] == 'supplied_predicted'
    collect = next(row for row in native['extractors'] if row['operation'] == 'execution.results.collect')
    assert collect['calculators'] == ['gene_annotation_episode.fluorescence_event_calculations.calculate_fluorescence_sheet']
    assert collect['projection_implementation'] == 'gene_annotation_episode.fluorescence_result_views.project_fluorescence_result'
    assert collect['retention_scope'] == 'verified_available_artifacts_with_explicit_partial_or_missing_roles'
    assert not collect['laboratory_operation']
    selected = _selector(f, saved=True)
    selected['parameters']['fraction_requests'] = [{'gate_key': 'gate-0', 'denominator': 'evaluable'}]
    saved = describe_fluorescence_result(f.target, selector=selected)
    assert saved['calculation_parameters'] == selected['parameters']
    assert saved['selected_outputs'] == saved['input_selection'] == []
    assert saved['status_operations'] == ['execution.results.status']
    assert not saved['status_meanings']['fresh_native_observation']
    assert all('capture' not in row and 'original_input_parsers' not in row for row in saved['extractors'])
    assert saved['acquisition_operations'] == ['execution.results.collect']


@pytest.mark.parametrize('saved', [False, True])
def test_retained_target_precedes_missing_current_binding_and_native_bytes(selected, monkeypatch, saved):
    f = selected
    bare = deepcopy(f.resources)
    next(iter(bare.values())).pop('native_fluorescence')
    f.owner = _owner(f, bare)
    child = _results(f, saved=saved)
    host = f.owner.native_fluorescence_results
    monkeypatch.setattr(host, 'retained_target', lambda *_: deepcopy(f.target))
    monkeypatch.setattr(host.receipts, 'completed_receipts', lambda *_: [])
    monkeypatch.setattr(f.owner.native_fluorescence_returns, 'authenticate_received_saved_sheet', lambda *_: ('original',))
    monkeypatch.setattr(f.owner.job_progress_provider.targets, 'read_target',
        lambda *_: pytest.fail('historical result attempted live producer lookup'))
    assert f.owner._target(child) == f.target
    assert f.owner.prepare_assignment(f.root, 'results', child.assignment, f.scope, 'selected-results') == plain(child.assignment)
    assert f.owner.initial_references(child) == ['fixture-handoff', *([f.sheet['artifact_ref']] if saved else [])]
    f.owner.initialize(child)
    described = f.owner.decision_context(child, {})['execution_target_description']
    assert described['result_selection']['mode'] == ('saved_sheet_recalculation' if saved else 'native_result')
    assert {row['name'] for row in f.owner.catalog(child)} == {row['name'] for row in operation_catalog()}
    assert not any(row['name'] in OPERATIONS for row in f.owner.resource_tool_contracts())


@pytest.mark.parametrize('mode,partial,complete,acquired', [
    ('native_result', False, True, 1), ('native_result', True, False, 1),
    ('saved_sheet_recalculation', True, True, 0)])
def test_selected_completion_and_credit_do_not_use_launch_setup_keys(selected, monkeypatch, mode, partial, complete, acquired):
    f = selected
    saved = mode == 'saved_sheet_recalculation'
    child = _results(f, saved=saved, sources=(PROJECTION_SOURCE, CONTEXT_SOURCE, SAVED_SOURCE, FAILURE_SOURCE))
    host = f.owner.native_fluorescence_results
    receipt = receipt_fixture(f.store, mode=mode, native_outcome='partial' if partial else 'complete')
    receipt['intent'].update(episode_id=child.episode_id, operation_key=f'{f.run_id}:{child.episode_id}:0', assignment=plain(child.assignment))
    receipt['facts'], receipt['delivery_complete'] = host.receipts.publication(receipt,
        originals=[{'delivery_complete': False}] if saved else None)
    receipt['acquired_population'] = host.receipts.acquisition_population(receipt)
    original = deepcopy(receipt)
    # Only the durable completed-receipt port is controlled here. The shared
    # routing, publication, deduplication and completion-proof comparison run.
    monkeypatch.setattr(host.receipts, 'completed_receipts', lambda *_: [deepcopy(receipt), deepcopy(receipt)])
    monkeypatch.setattr(host.receipts, 'baseline_populations', lambda *_: set())
    assert 'completion_keys' not in child.assignment
    assert f.owner.facts(child, {})['execution_completed'] is complete
    credit = f.owner.project_credit(child, None)
    assert credit['credit'] == acquired * 2 and credit['new_acquired_record_count'] == acquired
    proof = f.owner.completion_for_action(child, receipt['intent']['operation_key'])
    assert (proof is not None) is complete
    if complete:
        assert f.owner.verify_completion(child, proof)
        assert not f.owner.verify_completion(child, {**proof, 'receipt_sha256': 'f' * 64})
        assert f.owner.completion_for_action(child, 'different-operation') is None
    monkeypatch.setattr(host.receipts, 'baseline_populations', lambda *_: {receipt['acquired_population']})
    assert f.owner.project_credit(child, None)['credit'] == 0
    assert receipt == original


def test_selected_operation_dispatch_reuses_c_catalog_and_execution_port(selected, monkeypatch):
    f = selected
    child = _results(f)
    host = f.owner.native_fluorescence_results
    monkeypatch.setattr(host, 'retained_target', lambda *_: deepcopy(f.target))
    seen = []
    async def execute(context, target, tool_name, arguments, operation_key):
        seen.append((context, target, tool_name, arguments, operation_key))
        return {'status': 'controlled_dispatch'}
    monkeypatch.setattr(host, 'execute', execute)
    assert asyncio.run(f.owner.execute(child, 'execution.results.collect', {}, 'selected-action')) == {'status': 'controlled_dispatch'}
    assert seen == [(child, f.target, 'execution.results.collect', {}, 'selected-action')]
    rejected = asyncio.run(f.owner.execute(child, 'execution.results.read', {}, 'unselected-action'))
    assert rejected['feedback']['code'] == 'execution_operation_not_available'
    assert len(seen) == 1


def test_configured_library_launch_and_resource_admission_use_actual_selected_files(selected):
    # Requires the actual tool-information module to build the request schema.
    f = selected
    launch = dict(version='execution_launch_assignment_v1',
        requests={f.assignment['resource_id']: f.assignment}, immutable_input_versions=f.versions, constraints={})
    prepared = f.owner.prepare_assignment(f.root, 'launch', launch, f.scope, 'commission-launch')
    parent = f.child(f.root, obj({'observed': {'type': 'boolean'}}), role='launch')
    request = plain(parent.request)
    request['message']['episode_assignment'] = prepared
    parent = replace(parent, assignment=prepared, request=request)
    f.persist(parent)
    row = f.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0',
        (f.run_id, f.root.episode_id)).fetchone()
    action = json.loads(row['action'])
    action['assignment'] = prepared
    f.journal.save('runtime_actions', dict(episode_id=f.root.episode_id, decision_index=0,
        action=canonical(action), result=None, credit=None))
    f.owner.initialize(parent)
    assert f.owner.initial_references(parent) == f.input_refs
    child_assignment = f.owner.prepare_assignment(parent, 'launch_local', f.assignment, f.scope, 'commission-local')
    child = f.child(parent, obj({'observed': {'type': 'boolean'}}), role='launch_local')
    request = plain(child.request)
    request['message']['episode_assignment'] = child_assignment
    child = replace(child, assignment=child_assignment, request=request)
    f.persist(child)
    row = f.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0',
        (f.run_id, parent.episode_id)).fetchone()
    action = json.loads(row['action'])
    action['assignment'] = child_assignment
    f.journal.save('runtime_actions', dict(episode_id=parent.episode_id, decision_index=0,
        action=canonical(action), result=None, credit=None))
    f.owner._check_parent_inputs(child)
    assert f.owner.initial_references(child) == f.input_refs
    # Commissioning inputs are authenticated metadata even after disappearance.
    for path in f.input_paths: path.unlink()
    f.owner._check_parent_inputs(child)
    changed = deepcopy(child_assignment)
    changed['requested_job']['native_fluorescence']['inputs'][0]['sample']['label'] = 'substituted'
    with pytest.raises(ValueError):
        f.owner._check_parent_inputs(replace(child, assignment=changed))


@pytest.fixture
def progress(tmp_path, backend, monkeypatch):
    operations, state, execution, outcome = start(tmp_path, backend)
    with Store(tmp_path / 'state') as store:
        scope = {'subject_refs': store.create_problem(raw_sequence='ACGT', molecule='dna')['subject_refs']}
        resource_id = state.assignment['resource_id']
        reader = ExecutionTargetReader(store, run_id=state.run_id, directory=tmp_path,
            resources={resource_id: operations.configuration}, api_execution=None)
        body = dict(episode_id=state.episode_id, scope=scope,
            receipt=dict(tool_name='practical.job.start', operation_key='selected-start', outcome=outcome))
        request_ref = store.artifact(canonical({'assignment': state.assignment}).encode(), 'application/json')
        body_ref = store.artifact(canonical(body).encode(), 'application/json')
        source = dict(provider=PROVIDER, request_ref=request_ref, artifact_ref=body_ref)
        original_get = store.get
        monkeypatch.setattr(store, 'get', lambda ref: source if ref == 'controlled-original-handoff' else original_get(ref))
        # The practical receipt reader is the controlled lower authority port;
        # saved resource/attempt identity and live observe/read adapters run.
        monkeypatch.setattr(reader.receipts, 'read', lambda *_: deepcopy(body))
        yield reader, state, execution, body, source, scope, store


def test_progress_describes_original_operation_and_uses_actual_local_observe_read_ports(progress):
    reader, state, execution, body, source, scope, store = progress
    handle = 'controlled-original-handoff'
    target = reader.read_target(handle, scope)
    plan = reader.operations[target['resource_id']]._fluorescence_plan(state.assignment, execution)
    assert reader._native_identity(target) == target_identity(state, plan)
    assert reader.describe_target(handle, scope)['called_operation'] == 'practical.job.start'
    assert reader.describe_target(handle, scope)['operation'] == OPERATIONS[0]
    log = Path(execution).parent / 'stdout.log'
    log.write_bytes(b'original supplied events loaded\n')
    observed = reader.observe_target(target, operation_key='selected-observation')
    assert observed['state'] == 'running' and observed['returncode'] is None
    assert observed['native']['execution_id'] == execution
    window = reader.read_file(target, path=str(log), offset=9, limit=8)
    assert window['text_utf8'] == 'supplied' and window['returned_bytes'] == 8
    assert observed['measurements'] == []
    with pytest.raises(ValueError, match='original_output_path'):
        reader.read_file(target, path=str(log.parent / 'not-selected.txt'), offset=0, limit=8)


@pytest.mark.parametrize('change', ['resource', 'operation_key', 'request'])
def test_progress_rejects_changed_original_attempt_identity(progress, monkeypatch, change):
    reader, state, execution, body, source, scope, store = progress
    if change in {'resource', 'request'}:
        selected = deepcopy(state.assignment)
        if change == 'resource': selected['resource_id'] = 'other-resource'
        else: selected['requested_job']['environment']['UNSELECTED'] = 'changed'
        source['request_ref'] = store.artifact(canonical({'assignment': selected}).encode(), 'application/json')
    elif change == 'operation_key':
        body['receipt']['outcome']['native_outcome']['attempt_operation_key'] = 'different-start'
    with pytest.raises(ValueError): reader._native('controlled-original-handoff', scope)


@pytest.mark.parametrize('change', ['resource_id', 'operation_key'])
@pytest.mark.parametrize('action', ['observe', 'read'])
def test_selected_live_operation_rejects_changed_fluorescence_plan(progress, monkeypatch, change, action):
    reader, state, execution, body, source, scope, store = progress
    target = reader.read_target('controlled-original-handoff', scope)
    operations = reader.operations[state.assignment['resource_id']]
    original = operations._fluorescence_plan

    def altered(*args, **kwargs):
        value = original(*args, **kwargs)
        value['identity'][change] = 'substituted'
        return value

    monkeypatch.setattr(operations, '_fluorescence_plan', altered)
    # The old selected outcome does not become false when today's plan changes.
    assert reader.read_target('controlled-original-handoff', scope) == target
    assert reader.usable_handoff(target) and reader.returnable_handoff(target)
    with pytest.raises(ValueError) as caught:
        if action == 'observe':
            reader.observe_target(target, operation_key='selected-observation')
        else:
            reader.read_file(target, path=str(Path(execution).parent / 'stdout.log'), offset=0, limit=8)
    if action == 'observe':
        assert str(caught.value) == 'execution_target_observation_failed'
        assert caught.value.detail['reason'] == 'native_fluorescence_original_attempt_mismatch'
    else:
        assert str(caught.value) == 'native_fluorescence_original_attempt_mismatch'


def test_recorded_fluorescence_handoff_survives_deleted_producer_files(progress):
    reader, state, execution, body, source, scope, store = progress
    handle = 'controlled-original-handoff'
    target, original_body = reader._native(handle, scope)
    original_identity = reader._native_identity(target)
    log = str(Path(execution).parent / 'stdout.log')
    shutil.rmtree(Path(execution).parent)

    assert reader._native(handle, scope) == (target, original_body)
    assert reader.read_target(handle, scope) == target
    assert reader._native_identity(target) == original_identity
    assert reader.usable_handoff(target) and reader.returnable_handoff(target)
    assert body == original_body
    # New work still needs its original physical inputs and cannot use the
    # retained receipt as a replacement for a missing live plan.
    with pytest.raises(ValueError, match='execution_target_observation_failed'):
        reader.observe_target(target, operation_key='selected-observation')
    with pytest.raises((ValueError, OSError)):
        reader.read_file(target, path=log, offset=0, limit=8)
