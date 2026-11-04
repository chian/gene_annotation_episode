"""Engineering action/publication controls, not a native HOMER execution proof."""
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import asyncio
import hashlib
import json
import threading

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import homer_motif_tools as host
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.homer_motif_result_contracts import homer_motif_return
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.molecular_measurement_tools import (MolecularOperationUnpublished,
    read_retained_molecular_publication, run_owned_molecular_worker)
from test_homer_motif_return_boundary import _engineered_capture_case, packet as engineering_packet
from test_native_homer_execution import selected_call
from test_molecular_sequence_input_bindings import actual_received_input_owner


def forbidden(*_args, **_kwargs):
    raise AssertionError('This engineering control must not run native work or calculations')


@pytest.fixture
def saved_configuration():
    value = host.normalize_homer_configuration({}, (), policy=LocalJobPolicy(**host._native().POLICY).to_dict())
    value['saved_modes'] = True
    return value


def test_saved_only_configuration_advertises_no_native_or_host_tracking(saved_configuration):
    contract = host.homer_tool_contract(saved_configuration)
    schema = contract['input_schema']
    validator = Draft202012Validator(schema)
    source = 'source_' + 'a' * 24
    validator.validate(dict(mode='read_stored', result_ref=source))
    validator.validate(dict(mode='calculate_saved', result_ref=source,
        selector=dict(series_ids=[], offset=0, limit=0)))
    assert not validator.is_valid(dict(mode='run_native', inputs=[], parameters={}, selection={}))
    assert contract['configuration']['bindings'] == []
    assert 'supplied reference FASTA and explicit background BED only' in json.dumps(contract)
    assert not {'path', 'sha256', 'python_home', 'deployment', 'software'} & set(contract['configuration'])
    disabled = deepcopy(saved_configuration)
    disabled['saved_modes'] = False
    assert host.homer_tool_contract(disabled) is None


@pytest.mark.parametrize('flag', [0, 1, None, 'true'])
def test_saved_mode_configuration_requires_a_boolean(saved_configuration, flag):
    saved_configuration['saved_modes'] = flag
    with pytest.raises(ValueError): host.homer_tool_contract(saved_configuration)


@pytest.mark.parametrize('selection', [
    dict(series=[dict(role='known_results')], offset=True, limit=1),
    dict(series=[dict(role='known_results')], offset=0, limit=-1),
    dict(series=[dict(role='denovo_pwm', motif_length=True)], offset=0, limit=1),
    dict(series=[dict(role='known_results'), dict(role='known_results')], offset=0, limit=1),
    dict(series=[dict(role='known_pwm')], offset=0, limit=1),
])
def test_initial_selection_uses_scientific_roles_and_strict_native_lengths(selection):
    with pytest.raises(ValueError): host._initial_selection(selection)


def test_initial_selection_preserves_explicit_role_order_without_future_ids():
    selection = dict(series=[dict(role='denovo_pwm', motif_length=12), dict(role='known_results'),
        dict(role='denovo_nonredundant_pwm')], offset=2, limit=4)
    assert host._initial_selection(selection) == selection
    assert host._initial_selection(dict(series=[], offset=0, limit=0)) == dict(series=[], offset=0, limit=0)


@pytest.mark.parametrize('arguments', [
    dict(mode='read_stored', result_ref='source_' + 'a' * 24, selector={}),
    dict(mode='read_stored', result_ref='artifact_' + 'a' * 64),
    dict(mode='calculate_saved', result_ref='source_' + 'a' * 24,
        selector=dict(series_ids=['same', 'same'], offset=0, limit=1)),
    dict(mode='calculate_saved', result_ref='source_' + 'a' * 24,
        selector=dict(series_ids=[], offset=0, limit=False)),
])
def test_saved_arguments_cannot_select_native_parameters_or_implicit_series(arguments):
    with pytest.raises(ValueError): host._arguments(arguments)


@pytest.fixture
def publication(tmp_path, engineering_packet):
    """Actual authority owners over first-insert engineering action records.

    Values come from the separately retained native-data fixture. The producer
    association here is engineered, with native execution explicitly unknown;
    this fixture makes no native completion, Workflow or parent-return claim.
    """
    with ExitStack() as stack:
        case = _engineered_capture_case(stack, tmp_path / 'engineering', published=False)
        store, value = case.store, case.value
        tools = ToolRegistry(store)
        arguments = json.loads(store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? '
            'AND episode_id=? AND decision_index=7', (case.producer.run_id, case.producer.episode_id)).fetchone()[0])['arguments']
        packet = deepcopy(engineering_packet)
        packet['execution'].update(wrapper_returncode=None, wrapper_outcome='unknown',
            known_outcome='unknown', denovo_outcome='unknown')
        for series in packet['selected_series']: series['native_outcome'] = 'unknown'
        for series in packet['available_series']: series['native_outcome'] = 'unknown'
        for count in packet['counts']: count['native_outcome'] = 'unknown'
        raw_value = {key: val for key, val in packet.items() if key not in ('version', 'source_ref')}
        public_ref = store.artifact(host.canonical(dict(version=host.PACKET_VERSION, value=raw_value)), 'application/json')
        private = store.artifact(b'engineering control: deliberately unread by literal readers')
        source = store.put('source', dict(provider=host.TOOL, version=host.SOURCE_VERSION, accession=None,
            uri=None, artifact_ref=public_ref, text_ref=None, request_ref=private, retrieved_at=None,
            parent_source_refs=[case.refs['source']], auxiliary_artifact_refs=[case.refs['raw']]), origin='tool')
        public = homer_motif_return(raw_value, source_ref=source['id'])
        outcome = host._outcome(arguments, case.operation_key, public)
        tools._save(case.operation_key, host.TOOL, arguments, plain(case.producer.scope), outcome)
        store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=7',
            (canonical(outcome), case.producer.run_id, case.producer.episode_id))
        value.receipts.receive(case.producer.episode_id, [source['id']], kind='own_action', source_index=7)
        # The shared negative controls already occupy parent decisions 8 and 9.
        receiver = value.child(10)
        def reader(context, reference, namespace, **options):
            assert namespace == 'source' and options == {'source_metadata_only': True}
            return value.binding.read_received_source(context, reference)
        yield SimpleNamespace(case=case, tools=tools, store=store, context=receiver, reader=reader,
            public=public, source=source, public_ref=public_ref, private=private)


def test_retained_read_is_literal_without_private_controls_inputs_or_calculation(publication, monkeypatch):
    case = publication
    original = case.store.get_artifact
    calls = []
    def public_only(reference):
        calls.append(reference)
        assert reference == case.public_ref
        return original(reference)
    monkeypatch.setattr(case.store, 'get_artifact', public_only)
    monkeypatch.setattr(host, '_control', forbidden)
    monkeypatch.setattr(host, '_observe_native', forbidden)
    monkeypatch.setattr(case.tools, '_sequence_worker_async', forbidden)
    before = list(case.store.db.iterdump())
    result = host.read_retained_homer_publication(case.tools, case.context, case.reader, case.source['id'])
    assert result == case.public and calls == [case.public_ref]
    assert list(case.store.db.iterdump()) == before


@pytest.fixture
def current_return_receipt(publication):
    """Engineering receipt timing only, without inventing a closed child/form."""
    case = publication
    context, source = case.case.producer, case.source['id']
    case.store.db.execute('DELETE FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?',
        (context.run_id, context.episode_id, source))
    case.case.value.receipts.receive(context.episode_id, [source], kind='child_form', source_index=0)
    assert not list(case.store.db.execute('SELECT 1 FROM runtime_model_calls WHERE run_id=? AND episode_id=?',
        (context.run_id, context.episode_id)))
    return SimpleNamespace(**{**vars(case), 'context': context})


@pytest.mark.parametrize('reader_path', ['direct', 'generic'])
def test_current_literal_read_needs_no_future_decision_or_private_bytes(
        current_return_receipt, monkeypatch, reader_path):
    case = current_return_receipt
    original, calls = case.store.get_artifact, []
    def public_only(reference):
        calls.append(reference)
        assert reference == case.public_ref
        return original(reference)
    monkeypatch.setattr(case.store, 'get_artifact', public_only)
    monkeypatch.setattr(host, '_decision_admission', forbidden)
    monkeypatch.setattr(host, '_control', forbidden)
    monkeypatch.setattr(host, '_observe_native', forbidden)
    monkeypatch.setattr(case.tools, '_sequence_worker_async', forbidden)
    before = list(case.store.db.iterdump())
    if reader_path == 'direct':
        result = host.read_retained_homer_publication(case.tools, case.context, case.reader, case.source['id'])
    else:
        result = read_retained_molecular_publication(case.tools, case.context, case.reader,
            case.source['id'], tool_name=host.TOOL)['public']
    assert result == case.public and calls == [case.public_ref]
    assert list(case.store.db.iterdump()) == before


def test_explicit_old_cutoff_still_requires_the_original_decision_witness_before_bytes(
        current_return_receipt, monkeypatch):
    case = current_return_receipt
    monkeypatch.setattr(case.store, 'get_artifact', forbidden)
    before = list(case.store.db.iterdump())
    with pytest.raises(ValueError, match='^homer_motif_result_not_received$'):
        host._read_homer_publication(case.tools, case.context, case.reader, case.source['id'],
            before_decision_index=host._current_cutoff(case.tools, case.context))
    assert list(case.store.db.iterdump()) == before


@pytest.mark.parametrize('mode', ['read_stored', 'calculate_saved'])
def test_real_selected_redisplay_and_same_selector_noop_do_not_become_a_producer(
        publication, saved_configuration, monkeypatch, mode):
    case = publication
    arguments = dict(mode=mode, result_ref=case.source['id'])
    if mode == 'calculate_saved': arguments['selector'] = deepcopy(case.public['selector'])
    context = case.context
    key = f'{context.run_id}:{context.episode_id}:0'
    action = dict(kind='tool', tool=host.TOOL, arguments=arguments)
    case.store.db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)',
        (context.run_id, context.episode_id, 0, canonical(action)))
    case.tools._homer_configuration = saved_configuration
    # Explicit engineering getter seam; actual composed owner binding has its
    # separate zero-work factory controls. This does not grant input authority.
    owner = SimpleNamespace(store=case.store, tool_registry=case.tools, run_id=context.run_id)
    monkeypatch.setattr(case.tools, 'execution_owner_for', lambda run: owner if run == context.run_id else forbidden())
    monkeypatch.setattr(case.tools, '_sequence_worker_async', forbidden)
    monkeypatch.setattr(host, '_control', forbidden)
    monkeypatch.setattr(host, '_observe_native', forbidden)
    original = case.store.get_artifact
    monkeypatch.setattr(case.store, 'get_artifact', lambda ref: original(ref) if ref == case.public_ref else forbidden())
    sources = case.store.db.execute("SELECT count(*) FROM records WHERE record_type='source'").fetchone()[0]
    with case.tools.current_invocation(context, read_received=case.reader, tool_name=host.TOOL,
            arguments=arguments, operation_key=key):
        result = asyncio.run(host.execute_homer_tool(case.tools, arguments, scope=context.scope,
            operation_key=key, authority=(context, case.reader)))
        # Exact pending own-action recovery is still the same saved operation.
        repeated = asyncio.run(host.execute_homer_tool(case.tools, arguments, scope=context.scope,
            operation_key=key, authority=(context, case.reader)))
    assert result == repeated and result['result'] == case.public
    assert result['record_refs'] == [case.source['id']] and result['changed_record_refs'] == []
    assert case.store.db.execute("SELECT count(*) FROM records WHERE record_type='source'").fetchone()[0] == sources
    case.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0',
        (canonical(result), context.run_id, context.episode_id))
    assert host.read_homer_action_result(case.tools, context, arguments, key, reader=case.reader) == case.public
    producer = host._recorded_molecular_producer_details(case.tools, case.source['id'], host.TOOL)
    assert producer['invocation']['operation_key'] == case.case.operation_key


def test_withdrawn_source_receipt_denies_literal_read_before_public_bytes(publication, monkeypatch):
    case = publication
    case.store.db.execute('DELETE FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?',
        (case.case.producer.run_id, case.case.producer.episode_id, case.source['id']))
    monkeypatch.setattr(case.store, 'get_artifact', forbidden)
    with pytest.raises(ValueError):
        host.read_retained_homer_publication(case.tools, case.context, case.reader, case.source['id'])


def test_late_earlier_commission_receipt_is_not_an_original_decision_witness(current_return_receipt, monkeypatch):
    case = current_return_receipt
    context = case.context
    source = case.source['id']
    args = dict(mode='read_stored', result_ref=source)
    key = f'{context.run_id}:{context.episode_id}:11'
    case.store.db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)',
        (context.run_id, context.episode_id, 11, canonical(dict(kind='tool', tool=host.TOOL, arguments=args))))
    # A negative authority fixture: a late own return names earlier commission0,
    # but there is no saved decision child_reports snapshot containing it.
    # No child completion, native execution or successful admission is invented.
    monkeypatch.setattr(case.store, 'get_artifact', forbidden)
    before = list(case.store.db.iterdump())
    with case.tools.current_invocation(context, read_received=case.reader, tool_name=host.TOOL,
            arguments=args, operation_key=key):
        with pytest.raises(ValueError, match='^homer_motif_result_not_received$'):
            host.read_retained_homer_publication(case.tools, context, case.reader, source)
    assert list(case.store.db.iterdump()) == before


@pytest.mark.parametrize('namespace', ['artifact', 'source'])
def test_fresh_file_temporal_projection_is_required_before_the_input_reader_or_bytes(publication, monkeypatch, namespace):
    case = publication
    row = case.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? '
        'AND decision_index=7', (case.case.producer.run_id, case.case.producer.episode_id)).fetchone()
    arguments = json.loads(row[0])['arguments']
    if namespace == 'source':
        arguments['inputs'][0] = dict(role='target_bed', namespace='source', reference=case.case.value.source_ref)
    calls = []
    def unavailable(owner, context, reference, selected_namespace, artifact_ref, cutoff):
        calls.append((context, reference, selected_namespace, artifact_ref, cutoff))
        raise ValueError('homer_motif_file_admission_projection_unavailable')
    monkeypatch.setattr(EpisodeReturnRecords, 'file_admission_before', unavailable)
    monkeypatch.setattr(case.store, 'get_artifact', forbidden)
    with pytest.raises(ValueError, match='file_admission_projection_unavailable'):
        host._fresh_inputs(case.tools, case.case.producer, forbidden, arguments, 7)
    assert calls == [(case.case.producer, arguments['inputs'][0]['reference'], namespace,
        case.case.inputs[0], 7)]


def test_only_opaque_file_projection_failure_becomes_controlled_unavailable_before_bytes(publication, monkeypatch):
    case = publication
    arguments = json.loads(case.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? '
        'AND episode_id=? AND decision_index=7',
        (case.case.producer.run_id, case.case.producer.episode_id)).fetchone()[0])['arguments']
    monkeypatch.setattr(case.store, 'get_artifact', forbidden)
    for code, expected_status in [('homer_motif_file_admission_projection_unavailable', 'unavailable'),
            ('homer_motif_file_not_received', 'invalid')]:
        original = ValueError(code)
        def reject(*_args, **_kwargs):
            raise original
        monkeypatch.setattr(EpisodeReturnRecords, 'file_admission_before', reject)
        with pytest.raises(ValueError) as caught:
            host._fresh_inputs(case.tools, case.case.producer, forbidden, arguments, 7)
        if expected_status == 'unavailable':
            assert isinstance(caught.value, host._KnownUnavailable)
            assert caught.value.__cause__ is original
        else:
            assert caught.value is original and not isinstance(caught.value, host._KnownUnavailable)
        result = host._failure(case.tools, arguments, case.case.operation_key, caught.value)
        assert result['status'] == expected_status and result['result'] is None and result['record_refs'] == []
        assert result['feedback']['code'] == code


@pytest.mark.parametrize('stopped,state', [(True, 'prepared'), (False, 'prepared'), (False, 'execution_unknown')])
def test_homer_observer_stop_keeps_original_handle_without_cancel_or_resubmission(tmp_path, monkeypatch, stopped, state):
    """Controlled lifecycle metadata seam; no service or calculation is run."""
    policy, event = LocalJobPolicy(**host._native().POLICY), threading.Event()
    if stopped: event.set()
    calls = dict(prepare=0, resume=0)
    class Handle:
        def __init__(self, path): self.path = Path(path)
        def read(self): return json.loads(self.path.read_text())
    def prepare(command, *, cwd, policy, handle_path, stdout_path, stderr_path, env):
        calls['prepare'] += 1
        paths = {name: str(cwd / ('.local-job-' + 'a' * 32 + '.' + name))
            for name in ('request', 'ready', 'release', 'status', 'result', 'launcher')}
        request = dict(command=command, cwd=str(cwd), file_bytes=policy.scratch_bytes,
            ready_path=paths['ready'], release_path=paths['release'], result_path=paths['result'], stdin_path=None, env=env)
        raw = host.canonical(request).encode()
        Path(paths['request']).write_bytes(raw)
        body = dict(version=native_lifecycle.VERSION, stage='prepared', command=command, cwd=str(cwd),
            stdout=str(stdout_path), stderr=str(stderr_path), paths=paths,
            request_sha256=hashlib.sha256(raw).hexdigest(), metadata=dict(policy=policy.to_dict()))
        Path(handle_path).write_text(json.dumps(body))
        return Handle(handle_path)
    def status(handle):
        return dict(terminal=False, quiescent=False, state=state,
            metadata=dict(policy=policy.to_dict()))
    def resume(handle, **_kwargs):
        calls['resume'] += 1
        Path(handle.read()['paths']['release']).touch()
        event.set()
    monkeypatch.setattr(native_lifecycle, 'NativeJobHandle', Handle)
    monkeypatch.setattr(native_lifecycle, 'prepare_job', prepare)
    monkeypatch.setattr(native_lifecycle, 'status', status)
    monkeypatch.setattr(native_lifecycle, 'resume_start', resume)
    monkeypatch.setattr(native_lifecycle, 'wait_job', forbidden)
    monkeypatch.setattr(native_lifecycle, 'cancel', forbidden)
    monkeypatch.setattr(native_lifecycle, 'collect', forbidden)
    def invoke():
        return run_owned_molecular_worker('homer_motif_result', dict(request={'engineering': True}),
            directory=tmp_path, owned_directory=tmp_path, policy=policy, cancel_event=event)
    with pytest.raises(MolecularOperationUnpublished): invoke()
    original = (tmp_path / 'native-handle.json').read_bytes()
    with pytest.raises(MolecularOperationUnpublished): invoke()
    assert (tmp_path / 'native-handle.json').read_bytes() == original
    assert calls == dict(prepare=1, resume=1 if not stopped and state == 'prepared' else 0)


def test_fresh_missing_deployment_is_a_durable_failure_before_any_reservation(
        tmp_path, monkeypatch, selected_call):
    """Real input admission/preflight/save, explicitly non-executable software."""
    call, reservations = selected_call
    with actual_received_input_owner(tmp_path / 'input-owner', deliver=False) as case:
        store, context = case.store, case.parent
        tools = ToolRegistry(store)
        tools.local_job_policy = call['policy']
        inputs = []
        for row in call['frozen_inputs']['inputs']:
            reference = store.artifact(Path(row['path']).read_bytes(), 'application/octet-stream')
            inputs.append(dict(role=row['role'], namespace='artifact', reference=reference))
        case.receipts.receive(context.episode_id, [r['reference'] for r in inputs], kind='initial')
        selected = call['selected']
        resources = {selected['resource_id']: dict(kind='local', workspace=selected['workspace'],
            policy=call['policy'].to_dict(), native_homer_motif=[selected['binding']] * 4)}
        environments = [dict(operation=host.TOOL, resource_id=selected['resource_id'],
            binding_ordinal_0based=3, environment=selected['environment'])]
        tools._homer_configuration = host.normalize_homer_configuration(resources, environments,
            policy=call['policy'].to_dict())
        # Metadata normalization is not an installation claim. Actual selected
        # bytes disappear before the fresh producer verifies/reserves anything.
        missing = Path(selected['binding']['deployment']['root']) / 'deployment/bin/findMotifsGenome.pl'
        missing.unlink()
        arguments = dict(mode='run_native', inputs=inputs, parameters=call['arguments'],
            selection=dict(series=[dict(role='denovo_pwm', motif_length=8)], offset=0, limit=1))
        key = f'{context.run_id}:{context.episode_id}:7'
        action = dict(kind='tool', tool=host.TOOL, arguments=arguments)
        store.db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)',
            (context.run_id, context.episode_id, 7, canonical(action)))
        owner = SimpleNamespace(store=store, tool_registry=tools, run_id=context.run_id, resources=resources)
        monkeypatch.setattr(tools, 'execution_owner_for', lambda run: owner if run == context.run_id else forbidden())
        monkeypatch.setattr(tools, '_sequence_worker_async', forbidden)
        monkeypatch.setattr(host, '_observe_native', forbidden)
        monkeypatch.setattr(native_lifecycle, 'resume_start', forbidden)
        def reader(current, reference, namespace, **options):
            return case.binding.read_received_file(current, reference, namespace, **options)
        with tools.current_invocation(context, read_received=reader, tool_name=host.TOOL,
                arguments=arguments, operation_key=key):
            result = asyncio.run(host.execute_homer_tool(tools, arguments, scope=context.scope,
                operation_key=key, authority=(context, reader)))
            repeated = asyncio.run(host.execute_homer_tool(tools, arguments, scope=context.scope,
                operation_key=key, authority=(context, reader)))
        assert result == repeated and result['status'] == 'unavailable'
        assert result['result'] is None and result['record_refs'] == []
        assert result['feedback']['code'] == 'ordinary_homer_preflight_rejected'
        assert store.db.execute('SELECT count(*) FROM tool_operations WHERE operation_key=?', (key,)).fetchone()[0] == 1
        assert reservations == []
        assert not list(Path(selected['workspace']).rglob('native.json'))
        assert not list(Path(selected['workspace']).rglob('.local-job-*'))


@pytest.mark.parametrize('basename', ['unsupported workspace', 'unsupported;workspace'])
def test_unquoted_native_workspace_limit_is_checked_before_catalog_or_invocation(selected_call, tmp_path, basename):
    call, reservations = selected_call
    selected = call['selected']
    workspace = str(tmp_path / basename)
    resources = {selected['resource_id']: dict(kind='local', workspace=workspace,
        policy=call['policy'].to_dict(), native_homer_motif=[selected['binding']])}
    environments = [dict(operation=host.TOOL, resource_id=selected['resource_id'],
        binding_ordinal_0based=0, environment=selected['environment'])]
    with pytest.raises(ValueError):
        host.normalize_homer_configuration(resources, environments, policy=call['policy'].to_dict())
    assert reservations == [] and not Path(workspace).exists()
