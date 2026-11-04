"""Opt-in retained HOMER views through actual ordinary Workflow actions.

This consumes a separately pinned genuine prefix. It creates no native HOMER
attempt and edits no historical SQL. Scripted choices select existing public
series metadata; their callbacks are not external model calls or science.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator
from method_loop.archive import ArchivedRecord, iter_json

from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode import homer_motif_tools as host
from gene_annotation_episode import homer_motif_result_contracts as contracts
from gene_annotation_episode import homer_motif_measurements as measurements
from gene_annotation_episode import native_homer_execution as native
from gene_annotation_episode import native_homer_worker
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController
from test_homer_motif_workflow import ROOT, PUBLICATION, QUESTION, _form, _credit


ENV = 'HMMER_NATIVE_ORACLE_HOMER_RETAINED'
TABLES = ('runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_model_calls',
    'runtime_forms', 'runtime_report_attempts', 'runtime_record_receipts', 'runtime_receipt_inheritance')


def _write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def _pin(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _inventory(root):
    root = Path(root)
    return {str(path.relative_to(root)): dict(**_pin(path), mode=path.stat().st_mode)
        for path in sorted(root.rglob('*')) if path.is_file()}


def _sqlite_pins(root):
    return [dict(name=name, sha256=value['sha256'], size_bytes=value['size_bytes'])
        for name in ('state.sqlite3', 'state.sqlite3-wal', 'state.sqlite3-shm')
        if (path := Path(root) / name).is_file() for value in [_pin(path)]]


def _history(store, run_id):
    result = {name: [dict(row) for row in store.db.execute('SELECT * FROM ' + name +
        ' WHERE run_id=? ORDER BY rowid', (run_id,))] for name in TABLES}
    result['tool_operations'] = [dict(row) for row in store.db.execute(
        "SELECT * FROM tool_operations WHERE substr(operation_key,1,?)=? ORDER BY rowid",
        (len(run_id) + 1, run_id + ':'))]
    return result


def _archive(row, directory):
    descriptor = json.loads(row['archive'])
    assert Path(descriptor['file']).name == descriptor['file']
    return ArchivedRecord(Path(directory) / 'archive' / descriptor['file'],
        descriptor['sha256'], descriptor['index_sha256']).load()


def _archive_value(record):
    return json.loads(''.join(iter_json(record.as_record())))


def _contains(node, value):
    if node == value:
        return True
    return (any(_contains(item, value) for item in node.values()) if type(node) is dict else
        any(_contains(item, value) for item in node) if type(node) is list else False)


def _authenticate_original(store, proof, run_directory):
    run_id = proof['run_id']
    history = _history(store, run_id)
    rows = sorted(history['runtime_episodes'], key=lambda row: len(json.loads(row['path'])))
    assert len(rows) == 2 and all(row['state'] == 'yielded' for row in rows)
    assert len(history['runtime_actions']) == len(history['runtime_observations']) == len(history['runtime_model_calls']) == 2
    operation, = history['tool_operations']
    outcome = json.loads(operation['result'])
    public = contracts.validate_homer_motif_return(outcome['result'])
    assert outcome['status'] in ('completed', 'partial') and outcome['record_refs'] == [public['source_ref']]
    arguments = json.loads(operation['arguments'])
    assert arguments['mode'] == 'run_native' and arguments == proof['arguments']
    records = EpisodeReturnRecords(store, run_id, failure_prefix='homer_saved_original_')
    parent, science = [records.context(row['episode_id']) for row in rows]
    for context in (parent, science): records.authenticate(context)
    assert plain(parent.request)['goal']['objective'] == QUESTION
    assert plain(parent.scope) == proof['scope']
    action, = [row for row in history['runtime_actions'] if row['episode_id'] == science.episode_id]
    assert json.loads(action['action']) == dict(kind='tool', tool=contracts.TOOL, arguments=arguments)
    assert operation['operation_key'] == f'{run_id}:{science.episode_id}:{action["decision_index"]}'
    assert canonical({key: val for key, val in json.loads(action['result']).items()
        if key != 'pending_work_after_action'}) == operation['result']
    source = store.get(public['source_ref'])
    capture = store.get(source['parent_source_refs'][0])
    assert source['version'] == contracts.SOURCE_VERSION and capture['version'] == contracts.CAPTURE_VERSION
    assert capture['accession'] == operation['id']
    publication = host._metadata_publication(SimpleNamespace(store=store), public['source_ref'])
    assert publication['public'] == public
    assert publication['producer']['invocation']['operation_key'] == operation['operation_key']
    control = json.loads(store.get_artifact(source['request_ref']))
    custody = json.loads(store.get_artifact(capture['request_ref']))
    execution = native.validate_homer_execution(custody['native_execution'])
    assert execution['terminal'] is execution['quiescent'] is True
    assert execution['execution']['wrapper_returncode'] == 0
    assert execution['plan']['identity']['operation_key'] == operation['operation_key']
    if 'native_execution' in proof: assert proof['native_execution'] == execution
    form, = history['runtime_forms']
    assert form['episode_id'] == science.episode_id
    expected_form = dict(motifs=[public])
    assert json.loads(form['form']) == expected_form
    attempt, = history['runtime_report_attempts']
    assert attempt['failure'] is None and json.loads(attempt['form']) == expected_form
    assert attempt['parent_episode_id'] == parent.episode_id and attempt['child_episode_id'] == science.episode_id
    if 'returned' in proof: assert proof['returned'] == expected_form
    archives = [_archive(row, run_directory) for row in rows]
    for row, archive in zip(rows, archives, strict=True):
        assert archive['episode_id'] == row['episode_id'] and archive['run_id'] == run_id
        assert canonical(archive['request']) == canonical(json.loads(row['request']))
        assert archive['ended_by'] == 'yield_stop' and archive['units_consumed'] == 1
    assert canonical(archives[0]['units'][0]['child_result']) == canonical(dict(form=expected_form))
    assert public['available_series']
    candidates = [row for row in public['available_series'] if row['role'] == 'denovo_pwm'
        and row['requested_motif_length_bp'] == 10 and row['capture_state'] == 'complete']
    candidate, = candidates
    assert candidate['series_id'] not in public['selector']['series_ids']
    return dict(public=public, source=source, capture=capture, control=control,
        execution=execution, history=history, candidate=candidate,
        native_reported_flags={key: proof.get(key) for key in (
            'native_publication_verified', 'typed_parent_delivery_verified')})


def _controller(path, initial):
    return FixtureController(str(path), initial, 4 if path[-1][0] == 'scientific_process' else 1)


def _encode(answer, schema):
    value = deepcopy(answer)
    selection = value['selection']
    fields = [branch['properties'] for branch in schema['properties']['selection']['anyOf']
        if all(selection[key] in branch['properties'].get(key, {}).get('enum', [])
            for key in ('kind', 'role', 'tool') if key in selection)]
    assert len(fields) == 1
    for key in ('assignment', 'arguments'):
        if key in selection and fields[0][key].get('type') == 'string':
            selection[key] = json.dumps(selection[key], allow_nan=False)
    if selection['kind'] == 'episode_child':
        for key in fields[0]['scope']['required']:
            if key not in selection['scope']:
                assert {'type': 'null'} in fields[0]['scope']['properties'][key]['anyOf']
                selection['scope'][key] = None
    Draft202012Validator(schema).validate(value)
    return value


def _assemble(store, directory, configuration, provider):
    factory = ExecutionServiceFactory.from_record(configuration['factory'])
    assert not factory.homer_environments and factory.homer_saved_modes is True
    assert all('native_homer_motif' not in resource for resource in plain(factory.resources).values())
    tools = ToolRegistry(store, job_limits=deepcopy(native.POLICY))
    application = factory(store, run_id=configuration['run_id'], directory=directory, tool_registry=tools)
    workflow = Workflow(store, tools, provider, directory, configuration['run_id'], _controller, _credit,
        project_child_credit=_credit, episode_record_receipts=True,
        initial_known_record_refs=[configuration['source_ref']],
        episode_binding_descriptors=[configuration['scientific_binding'], *application.episode_binding_descriptors],
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    return workflow, tools


def _original_services(store, directory, proof):
    class NoDecisions:
        async def complete(self, *args, **kwargs):
            raise AssertionError('original parent literal read requested another decision')
        async def release(self, episode_id): pass
    factory = ExecutionServiceFactory.from_record(proof['factory'])
    tools = ToolRegistry(store, job_limits=deepcopy(native.POLICY))
    application = factory(store, run_id=proof['run_id'], directory=directory, tool_registry=tools)
    workflow = Workflow(store, tools, NoDecisions(), directory, proof['run_id'], _controller, _credit,
        project_child_credit=_credit, episode_record_receipts=True,
        initial_known_record_refs=proof['initial_known_record_refs'],
        episode_binding_descriptors=[proof['scientific_binding'], *application.episode_binding_descriptors],
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    return workflow, tools


def _capabilities(store, workflow, context, values, private, raw_inputs, audit):
    known = set(workflow.receipts.known(context.episode_id))
    assert {value['source_ref'] for value in values} <= known
    assert not known.intersection(private | raw_inputs)
    resolver = workflow.resolver(plain(context.scope), context=context)
    for reference in private:
        assert resolver(reference, 'source' if reference.startswith('source_') else 'artifact') is False
    reader = workflow.services.read_received_molecular_input
    before = _history(store, workflow.run_id)
    for reference in sorted(private | raw_inputs):
        if reference.startswith('source_'):
            result = reader(context, reference, 'source', source_metadata_only=True)
            assert result['failure'] is not None and result['input'] is None
        else:
            result, path = reader(context, reference, 'artifact', file_format='binary')
            assert result['failure'] is not None and result['input'] is None and path is None
    assert _history(store, workflow.run_id) == before
    audit.setdefault('capabilities', []).append(dict(episode_id=context.episode_id,
        result_sources=sorted(value['source_ref'] for value in values),
        private_and_raw_refs_received=False, file_and_private_source_reads_denied=True))


def test_retained_homer_source_supports_actual_saved_views_and_closed_replay(tmp_path, monkeypatch):
    selected = os.environ.get(ENV + '_PROOF')
    if not selected:
        pytest.skip('requires an explicitly selected retained genuine HOMER prefix')
    output = tmp_path / 'HOMER_SAVED_WORKFLOW_PREFIX.json'
    audit = dict(version='ordinary_homer_saved_workflow_v1', selected_prefix=None,
        original_prefix_authenticated=False, owned_database_cloned=False,
        original_parent_literal_read_verified=False,
        literal_read_verified=False, public_unselected_series_selection_verified=False,
        saved_calculation_verified=False, exact_repeat_verified=False, derived_read_verified=False,
        typed_parent_delivery_verified=False, closed_replay_verified=False,
        originals_unchanged=False, passed=False, native_attempts=[], worker_requests=[],
        worker_handles=[], calls=[], phase='selected', qualification=(
            'Actual retained-data Workflow over a separately selected genuine prefix; no native rerun.'))
    _write(output, audit)
    store = None
    originals = None
    try:
        prefix = Path(selected).resolve(strict=True)
        assert _pin(prefix)['sha256'] == os.environ[ENV + '_PROOF_SHA256']
        proof = json.loads(prefix.read_bytes())
        assert proof['version'] == 'ordinary_homer_workflow_prefix_v1' and proof['question'] == QUESTION
        original_store = Path(proof['store_directory']).resolve(strict=True)
        original_run = Path(proof['workflow_directory']).resolve(strict=True)
        original_pins, original_run_pins = _inventory(original_store), _inventory(original_run)
        bundle = _sqlite_pins(original_store)
        assert digest(bundle) == os.environ[ENV + '_SQLITE_PINS_SHA256']
        assert _pin(original_store / 'state.sqlite3') == proof['database_file']
        outer, = [parent for parent in prefix.parents if (parent / 'receipt.json').is_file()
            and (parent / 'selected_request.json').is_file()]
        receipt = json.loads((outer / 'receipt.json').read_bytes())
        assert receipt['terminal'] is receipt['quiescent'] is True
        audit.update(selected_prefix=_pin(prefix), original_sqlite_bundle=bundle,
            original_sqlite_bundle_sha256=digest(bundle), original_receipt=_pin(outer / 'receipt.json'),
            original_receipt_returncode=receipt['returncode'])
        originals = (prefix, audit['selected_prefix'], original_store, original_pins, original_run, original_run_pins)
        staging = tmp_path / 'owned-sqlite-staging'
        staging.mkdir()
        for row in bundle: shutil.copyfile(original_store / row['name'], staging / row['name'])
        assert _sqlite_pins(staging) == bundle
        owned = tmp_path / 'owned-store'
        owned.mkdir()
        shutil.copytree(original_store / 'artifacts', owned / 'artifacts')
        database = owned / 'state.sqlite3'
        source_db, target_db = sqlite3.connect(staging / 'state.sqlite3'), sqlite3.connect(database)
        try:
            source_db.execute('PRAGMA query_only=ON')
            source_db.backup(target_db)
        finally:
            target_db.close(); source_db.close()
        owned_original_run = tmp_path / 'owned-original-run'
        shutil.copytree(original_run, owned_original_run)
        store = Store(owned)
        audit['owned_database_cloned'] = True
        original = _authenticate_original(store, proof, owned_original_run)
        audit.update(original_prefix_authenticated=True, original_flags=original['native_reported_flags'],
            original_native_handle=original['execution']['handle'], original_source=original['source'],
            original_value=original['public'], original_series_candidate=original['candidate'])
        native_root = Path(original['execution']['plan']['operation_directory']).resolve(strict=True)
        native_pins = _inventory(native_root)
        assert json.loads(Path(original['execution']['plan']['identity']['execution_id']).read_bytes()) == original['execution']['handle']
        for name in ('plan_file', 'binding_file', 'request_file', 'completion_file', 'output_manifest_file'):
            pin = original['execution'][name]
            if pin is not None: assert _pin(pin['path']) == pin
        handle = original['execution']['handle']
        native_request = _pin(handle['paths']['request'])
        assert native_request['sha256'] == handle['request_sha256']
        native_result = json.loads(Path(handle['paths']['result']).read_bytes())
        assert native_result['native_returncode'] == original['execution']['returncode'] == 0
        assert native_result['resource_failure'] is native_result['execution_failure'] is None
        audit['original_native_receipt'] = native_result
        audit['original_native_files'] = native_pins
        original_history = original['history']
        source_ref = original['public']['source_ref']
        selector = dict(series_ids=[original['candidate']['series_id']], offset=0, limit=1)
        audit['new_selector_from_public_catalog'] = selector
        capture = original['capture']
        private = {capture['id'], capture['artifact_ref'], capture['request_ref'], *capture['auxiliary_artifact_refs'],
            original['source']['artifact_ref'], original['source']['request_ref'], *original['source']['auxiliary_artifact_refs']}
        raw_inputs = set(original['control']['input_artifact_refs'])
        assert not raw_inputs.intersection(private)
        for reference in raw_inputs:
            (owned / 'artifacts' / reference[9:11] / reference[9:]).unlink()
        audit['owned_original_input_bodies_removed'] = sorted(raw_inputs)
        configuration = dict(run_id=proof['run_id'] + '-saved-public-views', question=QUESTION,
            scope=proof['scope'], source_ref=source_ref)
        directory = tmp_path / 'saved-run'
        workspace = tmp_path / 'unused-workspace'
        workspace.mkdir()
        factory = ExecutionServiceFactory({'saved-local': dict(kind='local', workspace=str(workspace),
            policy=deepcopy(native.POLICY))}, {}, 2, .25, .5, homer_saved_modes=True)
        tools = ToolRegistry(store, job_limits=deepcopy(native.POLICY))
        factory.configure_tool_registry(tools)
        configuration.update(factory=factory.as_record(), scientific_binding=prepare_scientific_binding(
            run_directory=directory, source_directory=ROOT / PUBLICATION, tool_catalog=tools.catalog(),
            child_roles=['scientific_process']))
        library = ScientificProcessLibrary(directory / 'scientific-process-library')
        audit['configuration'] = deepcopy(configuration)
        active = dict(turn=0, worker=False)
        class Choices:
            def __init__(self): self.turns = {}
            async def complete(self, episode_id, role, instructions, context, schema):
                current = plain(context)
                row = store.db.execute('SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                    (configuration['run_id'], episode_id)).fetchone()
                grain = json.loads(row['path'])[-1][0]
                self.turns[episode_id] = self.turns.get(episode_id, 0) + 1
                turn = self.turns[episode_id]
                assert role == 'REASONING' and not current.get('feedback'), current.get('feedback')
                assert current['goal']['objective'] == QUESTION
                audit['calls'].append(dict(episode_id=episode_id, grain=grain, turn=turn,
                    context=deepcopy(current), instructions=plain(instructions)))
                if grain == 'annotation':
                    assert turn == 1
                    selected = dict(kind='episode_child', role='scientific_process', goal=QUESTION,
                        scope=deepcopy(configuration['scope']), purpose=QUESTION, schema_json=json.dumps(_form()),
                        initial_report_json='{}', assignment=dict(selection=dict(version='scientific_process_selection_v3',
                            evidence_axis=library.reference('A103'), thought_pattern=library.reference('P01'),
                            child_tool_info=[dict(name=contracts.TOOL, resources='local')]), evidence_refs=[], constraints={},
                            context=dict(retained_result_source=source_ref)))
                else:
                    assert grain == 'scientific_process' and 1 <= turn <= 4
                    active['turn'] = turn
                    if turn == 1:
                        arguments = dict(mode='read_stored', result_ref=source_ref)
                    else:
                        previous = [json.loads(row['result']) for row in store.db.execute(
                            "SELECT * FROM tool_operations WHERE substr(operation_key,1,?)=? ORDER BY rowid",
                            (len(configuration['run_id']) + 1, configuration['run_id'] + ':'))]
                        assert previous[0]['result'] == original['public']
                        audit['literal_read_verified'] = True
                        if turn == 2:
                            available = previous[0]['result']['available_series']
                            assert original['candidate'] in available
                            assert _contains(current, original['candidate']), (
                                'the new series choice was absent from actual decision inputs')
                            audit['public_unselected_series_selection_verified'] = True
                            arguments = dict(mode='calculate_saved', result_ref=source_ref, selector=deepcopy(selector))
                        else:
                            derived = previous[1]['result']
                            assert derived['source_ref'] != source_ref and derived['selector'] == selector
                            arguments = (dict(mode='calculate_saved', result_ref=derived['source_ref'], selector=deepcopy(selector))
                                if turn == 3 else dict(mode='read_stored', result_ref=derived['source_ref']))
                    selected = dict(kind='tool', tool=contracts.TOOL, arguments=arguments)
                value = _encode(dict(selection=selected, report_update={}), schema)
                audit['calls'][-1]['response'] = deepcopy(value)
                _write(output, audit)
                return value
            async def release(self, episode_id): pass
        workflow, tools = _assemble(store, directory, configuration, Choices())
        owner = tools.execution_owner_for(configuration['run_id'])
        assert owner is workflow.episode_bindings.for_role('results')
        assert owner.resources['saved-local'].get('native_homer_motif') is None
        original_worker = tools._sequence_worker_async
        lifecycles = {name: getattr(native_lifecycle, name) for name in
            ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect', 'cancel')}
        admitted = set()
        def no_native(*args, **kwargs):
            audit['native_attempts'].append(dict(turn=active['turn'], argument_types=[type(a).__name__ for a in args]))
            raise AssertionError('retained HOMER views attempted native execution or acquisition')
        async def measured_worker(operation, arguments, **kwargs):
            assert active['turn'] == 2 and operation == 'homer_motif_result'
            request = arguments['request']
            assert request['mode'] == 'calculate_saved'
            assert request['files'] is request['invocation'] is request['execution'] is None
            assert request['saved']['file'] == original['control']['sheet_file']
            assert request['selection'] == selector and request['projection_source_ref'] == source_ref
            audit['worker_requests'].append(deepcopy(request))
            assert len(audit['worker_requests']) == 1
            active['worker'] = True
            try: return await original_worker(operation, arguments, **kwargs)
            finally: active['worker'] = False
        def prepare_worker(command, **kwargs):
            assert active['worker'] and active['turn'] == 2 and not admitted
            assert command[1:3] == ['-m', 'gene_annotation_episode.native_homer_worker'] and len(command) == 5
            assert Path(kwargs['cwd']).is_relative_to(owned / 'cache/molecular-measurements')
            handle = lifecycles['prepare_job'](command, **kwargs)
            admitted.add(handle.path)
            audit['worker_handles'].append(str(handle.path))
            return handle
        def worker_only(name):
            def guarded(handle, *args, **kwargs):
                assert active['turn'] == 2 and handle.path in admitted
                assert name in ('status', 'collect') or active['worker']
                return lifecycles[name](handle, *args, **kwargs)
            return guarded
        original_get = store.get_artifact
        original_control = host._control
        path_open, builtin_open, io_open, os_open = Path.open, __import__('builtins').open, __import__('io').open, os.open
        forbidden_paths = {owned / 'artifacts' / ref[9:11] / ref[9:] for ref in raw_inputs}
        software = original['execution']['plan']['software']
        original_roots = (original_store, original_run, native_root,
            Path(original['execution']['plan']['request']['deployment']['root']),
            Path(software['python_home']), *(Path(root) for root in software['import_roots']))
        payload_attempts = []
        def check_path(value, *, dir_fd=None):
            if isinstance(value, int): return
            path = Path(os.fsdecode(value))
            if not path.is_absolute():
                path = (Path(os.readlink('/proc/self/fd/' + str(dir_fd))) if dir_fd is not None else Path.cwd()) / path
            path = Path(os.path.normpath(path))
            if path in forbidden_paths or any(path.is_relative_to(root) for root in original_roots):
                payload_attempts.append(str(path))
                raise AssertionError('saved views opened an original input/runtime/workspace or original Store')
        def checked_builtin(file, *args, **kwargs): check_path(file); return builtin_open(file, *args, **kwargs)
        def checked_io(file, *args, **kwargs): check_path(file); return io_open(file, *args, **kwargs)
        def checked_os(file, flags, *args, **kwargs): check_path(file, dir_fd=kwargs.get('dir_fd')); return os_open(file, flags, *args, **kwargs)
        def checked_path(path, *args, **kwargs): check_path(path); return path_open(path, *args, **kwargs)
        def source_bytes(reference):
            assert reference not in raw_inputs
            assert reference not in {capture['artifact_ref'], *capture['auxiliary_artifact_refs']}
            if active['turn'] != 2:
                packet_refs = {original['source']['artifact_ref']}
                for row in store.db.execute("SELECT result FROM tool_operations WHERE name=? "
                        "AND substr(operation_key,1,?)=?", (contracts.TOOL,
                        len(configuration['run_id']) + 1, configuration['run_id'] + ':')):
                    outcome = json.loads(row['result'])
                    if outcome.get('status') in ('completed', 'partial'):
                        packet_refs.add(store.get(outcome['result']['source_ref'])['artifact_ref'])
                assert reference in packet_refs, 'literal read/noop opened private Artifact bytes'
            return original_get(reference)
        def controlled_private(*args, **kwargs):
            assert active['turn'] == 2, 'literal read/noop opened private sheet or controls'
            return original_control(*args, **kwargs)
        sources_before = store.count('source')
        with monkeypatch.context() as patch:
            patch.setattr(native, 'prepare_ordinary_homer_attempt', no_native)
            patch.setattr(native, 'run_ordinary_homer_attempt', no_native)
            patch.setattr(native_homer_worker, 'run_native_homer', no_native)
            patch.setattr('gene_annotation_episode.acquisition.PublicClients._http', no_native)
            patch.setattr(socket, 'create_connection', no_native)
            patch.setattr(tools, '_sequence_worker_async', measured_worker)
            patch.setattr(native_lifecycle, 'prepare_job', prepare_worker)
            for name in ('start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
                patch.setattr(native_lifecycle, name, worker_only(name))
            patch.setattr(native_lifecycle, 'cancel', no_native)
            patch.setattr(host, '_control', controlled_private)
            patch.setattr(store, 'get_artifact', source_bytes)
            patch.setattr(Path, 'open', checked_path)
            patch.setattr('builtins.open', checked_builtin)
            patch.setattr('io.open', checked_io)
            patch.setattr(os, 'open', checked_os)
            original_workflow, original_tools = _original_services(store, owned_original_run, proof)
            patch.setattr(original_tools, '_sequence_worker_async', no_native)
            original_records = EpisodeReturnRecords(store, proof['run_id'], failure_prefix='homer_saved_original_')
            parent_row, = [row for row in original_history['runtime_episodes'] if len(json.loads(row['path'])) == 1]
            original_parent = original_records.context(parent_row['episode_id'])
            original_records.authenticate(original_parent)
            original_known = set(original_workflow.receipts.known(original_parent.episode_id))
            assert source_ref in original_known
            assert host.read_retained_homer_publication(original_tools, original_parent,
                original_workflow.services.read_received_molecular_input, source_ref) == original['public']
            assert set(original_workflow.receipts.known(original_parent.episode_id)) == original_known
            assert _history(store, proof['run_id']) == original_history
            audit['original_parent_literal_read_verified'] = True
            root = workflow.build('annotation', 'root', QUESTION, configuration['scope'])
            record = asyncio.run(root.run_async(workflow.context))
            final = plain(asyncio.run(root.build_result(record)).as_record())
        audit.update(phase='saved_workflow_closed', archive=_archive_value(record), final_result=final)
        assert final == dict(credit=0, pending_handles=[])
        history = _history(store, configuration['run_id'])
        actions = [row for row in history['runtime_actions'] if json.loads(row['action']).get('kind') == 'tool']
        assert len(actions) == 4 and len(history['runtime_actions']) == len(history['runtime_model_calls']) == 5
        outcomes = [json.loads(row['result']) for row in sorted(actions, key=lambda row: row['decision_index'])]
        assert outcomes[0]['result'] == original['public'] and outcomes[0]['changed_record_refs'] == []
        derived = contracts.validate_homer_motif_return(outcomes[1]['result'])
        assert derived['source_ref'] != source_ref and derived['selector'] == selector
        assert outcomes[1]['record_refs'] == outcomes[1]['changed_record_refs'] == [derived['source_ref']]
        assert outcomes[2]['result'] == outcomes[3]['result'] == derived
        assert outcomes[2]['changed_record_refs'] == outcomes[3]['changed_record_refs'] == []
        assert len(audit['worker_requests']) == len(audit['worker_handles']) == 1
        assert store.count('source') == sources_before + 1
        derived_source = store.get(derived['source_ref'])
        derived_control = json.loads(store.get_artifact(derived_source['request_ref']))
        assert derived_control['sheet_file'] == original['control']['sheet_file']
        assert derived_control['native_call_state'] == 'not_requested'
        assert derived_control['capture_source'] == original['control']['capture_source']
        sheet = json.loads(store.get_artifact(original['control']['sheet_file']['artifact_ref']))
        selected_series, = [series for series in sheet['series'] if series['series_id'] == selector['series_ids'][0]]
        assert selected_series['observations']
        components = json.loads(store.get_artifact(derived_control['components_file']['artifact_ref']))
        assert components['selected_series'][0]['observations'] == selected_series['observations'][:1]
        assert measurements.project_homer_return(components, source_ref=derived['source_ref']) == derived
        for field in ('available_series', 'execution', 'population_facts', 'reported_input_weight_sums', 'issues'):
            assert derived[field] == original['public'][field]
        audit.update(literal_read_verified=True, saved_calculation_verified=True,
            exact_repeat_verified=True, derived_read_verified=True, derived_value=derived,
            same_retained_sheet=derived_control['sheet_file'], native_call_state='not_requested')
        records = EpisodeReturnRecords(store, configuration['run_id'], failure_prefix='homer_saved_')
        episodes = sorted(history['runtime_episodes'], key=lambda row: len(json.loads(row['path'])))
        parent, science = [records.context(row['episode_id']) for row in episodes]
        expected_form = dict(motifs=[original['public'], derived])
        form, = history['runtime_forms']
        assert form['episode_id'] == science.episode_id and json.loads(form['form']) == expected_form
        attempt, = history['runtime_report_attempts']
        assert attempt['failure'] is None and json.loads(attempt['form']) == expected_form
        assert workflow.services.molecular_frozen_facts(science, fact_source=contracts.FACT_SOURCE) == expected_form['motifs']
        assert workflow.services.molecular_received_facts(parent, fact_source=contracts.FACT_SOURCE) == expected_form['motifs']
        for value in (original['public'], derived):
            source = store.get(value['source_ref'])
            private.update([source['artifact_ref'], source['request_ref'], *source['auxiliary_artifact_refs']])
        for context in (parent, science):
            _capabilities(store, workflow, context, expected_form['motifs'], private, raw_inputs, audit)
        audit['typed_parent_delivery_verified'] = True
        before = _history(store, configuration['run_id'])
        all_counts = {table: store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
            for table in (*TABLES, 'tool_operations', 'records', 'artifacts')}
        replay_archive = None
        class NoDecisions:
            async def complete(self, *args, **kwargs): raise AssertionError('closed replay requested another model/choice')
            async def release(self, episode_id): pass
        with monkeypatch.context() as patch:
            for name in lifecycles: patch.setattr(native_lifecycle, name, no_native)
            patch.setattr(native, 'prepare_ordinary_homer_attempt', no_native)
            patch.setattr(native, 'run_ordinary_homer_attempt', no_native)
            patch.setattr(native_homer_worker, 'run_native_homer', no_native)
            patch.setattr(measurements, 'calculate_homer_components', no_native)
            patch.setattr(measurements, 'parse_homer_motif_sheet', no_native)
            patch.setattr(measurements, 'project_homer_return', no_native)
            patch.setattr(ToolRegistry, '_sequence_worker_async', no_native)
            patch.setattr(host, 'execute_homer_tool', no_native)
            patch.setattr(host, '_control', no_native)
            patch.setattr('gene_annotation_episode.acquisition.PublicClients._http', no_native)
            patch.setattr(socket, 'create_connection', no_native)
            replay, replay_tools = _assemble(store, directory, configuration, NoDecisions())
            closed_root = replay.build('annotation', 'root', QUESTION, configuration['scope'])
            closed = asyncio.run(closed_root.run_async(replay.context))
            replay_archive = _archive_value(closed)
            assert replay_archive == audit['archive']
            assert plain(asyncio.run(closed_root.build_result(closed)).as_record()) == final
            assert replay.services.molecular_frozen_facts(science, fact_source=contracts.FACT_SOURCE) == expected_form['motifs']
            assert replay.services.molecular_received_facts(parent, fact_source=contracts.FACT_SOURCE) == expected_form['motifs']
            assert host.read_retained_homer_publication(replay_tools, science,
                replay.services.read_received_molecular_input, derived['source_ref']) == derived
        assert _history(store, configuration['run_id']) == before
        assert {table: store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] for table in all_counts} == all_counts
        assert _history(store, proof['run_id']) == original_history
        assert audit['native_attempts'] == payload_attempts == []
        audit.update(closed_replay_verified=True, new_run_history_unchanged_on_replay=True,
            original_history_unchanged=True, payload_read_attempts=payload_attempts,
            original_database_history=original_history, saved_run_history=history,
            worker_control=derived_control['worker'], typed_form=expected_form)
        assert _inventory(original_store) == original_pins and _inventory(original_run) == original_run_pins
        assert _inventory(native_root) == native_pins and _pin(prefix) == audit['selected_prefix']
        audit.update(originals_unchanged=True, passed=True, phase='verified')
    except BaseException as error:
        audit['failure'] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        if store is not None:
            try:
                audit['actual_histories'] = {run: _history(store, run) for run in (
                    proof['run_id'], audit.get('configuration', {}).get('run_id', proof['run_id']))}
            except BaseException as error:
                audit['history_capture_failure'] = dict(exception_type=type(error).__name__, message=str(error))
            finally:
                store.close()
            if (store.path / 'state.sqlite3').is_file():
                audit['owned_database'] = _pin(store.path / 'state.sqlite3')
        _write(output, audit)


def test_retained_closed_homer_saved_workflow_replays_without_any_new_work(tmp_path, monkeypatch):
    """Consume a passed saved Workflow; never repeat its saved calculation."""
    environment = 'HMMER_NATIVE_ORACLE_HOMER_CLOSED'
    selected = os.environ.get(environment + '_PROOF')
    if not selected:
        pytest.skip('requires an explicitly pinned passed retained HOMER Workflow')

    def rows(database):
        names = [row[0] for row in database.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {name: sorted((dict(row) for row in database.execute(
            'SELECT * FROM "' + name.replace('"', '""') + '"')), key=canonical) for name in names}

    output = tmp_path / 'HOMER_CLOSED_REPLAY.json'
    audit = dict(version='ordinary_homer_retained_closed_replay_v1', phase='selected', passed=False,
        original_authenticated=False, owned_database_cloned=False, closed_replay_verified=False,
        typed_parent_delivery_verified=False, literal_read_verified=False,
        private_permissions_verified=False, histories_unchanged=False, originals_unchanged=False,
        forbidden_work_attempts=[], qualification=(
            'Replay of an independently passed saved Workflow; no new decision, tool, Source or calculation.'))
    _write(output, audit)
    store = None
    try:
        prefix = Path(selected).resolve(strict=True)
        prefix_pin = _pin(prefix)
        assert prefix_pin['sha256'] == os.environ[environment + '_PROOF_SHA256']
        proof = json.loads(prefix.read_bytes())
        assert proof['version'] == 'ordinary_homer_saved_workflow_v1'
        assert proof['phase'] == 'verified' and proof['passed'] is True
        assert all(proof[name] is True for name in ('original_prefix_authenticated',
            'original_parent_literal_read_verified', 'literal_read_verified', 'saved_calculation_verified',
            'exact_repeat_verified', 'derived_read_verified', 'typed_parent_delivery_verified',
            'closed_replay_verified', 'originals_unchanged'))
        assert len(proof['worker_requests']) == len(proof['worker_handles']) == 1
        assert proof['native_attempts'] == proof['payload_read_attempts'] == []
        original_store = Path(proof['owned_database']['path']).resolve(strict=True).parent
        assert _pin(original_store / 'state.sqlite3') == proof['owned_database']
        original_run = prefix.parent / 'saved-run'
        original_artifacts, original_run_files = _inventory(original_store / 'artifacts'), _inventory(original_run)
        bundle = _sqlite_pins(original_store)
        assert digest(bundle) == os.environ[environment + '_SQLITE_PINS_SHA256']
        configuration = deepcopy(proof['configuration'])
        assert configuration['question'] == QUESTION
        assert configuration['factory']['homer_saved_modes'] is True
        original_values = proof['typed_form']['motifs']
        assert original_values == [proof['original_value'], proof['derived_value']]
        assert len({value['source_ref'] for value in original_values}) == 2
        assert proof['final_result'] == dict(credit=0, pending_handles=[])
        audit.update(original_authenticated=True, selected_prefix=prefix_pin,
            original_sqlite_bundle=bundle, original_sqlite_bundle_sha256=digest(bundle),
            configuration=configuration, original_saved_worker_requests=len(proof['worker_requests']))

        staging = tmp_path / 'sqlite-staging'
        staging.mkdir()
        for row in bundle: shutil.copyfile(original_store / row['name'], staging / row['name'])
        assert _sqlite_pins(staging) == bundle
        owned = tmp_path / 'owned-closed-store'
        owned.mkdir()
        source_db, target_db = sqlite3.connect(staging / 'state.sqlite3'), sqlite3.connect(owned / 'state.sqlite3')
        source_db.row_factory = sqlite3.Row
        try:
            source_db.execute('PRAGMA query_only=ON')
            original_rows = rows(source_db)
            source_db.backup(target_db)
        finally:
            target_db.close(); source_db.close()
        shutil.copytree(original_store / 'artifacts', owned / 'artifacts')
        directory = tmp_path / 'closed-run'
        shutil.copytree(original_run, directory)
        store = Store(owned)
        assert rows(store.db) == original_rows
        for run_id, history in proof['actual_histories'].items():
            assert _history(store, run_id) == history
        run_id = configuration['run_id']
        history = _history(store, run_id)
        assert history == proof['saved_run_history']
        assert len(history['runtime_episodes']) == 2 and all(row['state'] == 'yielded' for row in history['runtime_episodes'])
        assert len(history['runtime_model_calls']) == len(history['runtime_actions']) == 5
        assert len(history['tool_operations']) == 4
        parent_row, = [row for row in history['runtime_episodes'] if len(json.loads(row['path'])) == 1]
        science_row, = [row for row in history['runtime_episodes'] if len(json.loads(row['path'])) == 2]
        assert _archive(parent_row, directory) == proof['archive']
        scientific_archive = proof['archive']['units'][0]['child']
        assert scientific_archive['episode_id'] == science_row['episode_id']
        assert _archive(science_row, directory) == scientific_archive
        raw_inputs = set(proof['owned_original_input_bodies_removed'])
        assert len(raw_inputs) == 3
        for reference in raw_inputs:
            assert not (owned / 'artifacts' / reference[9:11] / reference[9:]).exists()
        sources = [store.get(value['source_ref']) for value in original_values]
        assert sources[0] == proof['original_source']
        capture = store.get(sources[0]['parent_source_refs'][0])
        private = {capture['id'], capture['artifact_ref'], capture['request_ref'], *capture['auxiliary_artifact_refs']}
        for source in sources:
            private.update([source['artifact_ref'], source['request_ref'], *source['auxiliary_artifact_refs']])
        packets = {source['artifact_ref'] for source in sources}
        known_before = {row['episode_id']: None for row in history['runtime_episodes']}
        original_get = store.get_artifact
        path_open, builtin_open, io_open, os_open = Path.open, __import__('builtins').open, __import__('io').open, os.open

        def forbidden(*args, **kwargs):
            audit['forbidden_work_attempts'].append(dict(argument_types=[type(value).__name__ for value in args]))
            raise AssertionError('closed HOMER replay attempted new work')

        def check_path(value, *, dir_fd=None):
            if isinstance(value, int): return
            path = Path(os.fsdecode(value))
            if not path.is_absolute():
                path = (Path(os.readlink('/proc/self/fd/' + str(dir_fd))) if dir_fd is not None else Path.cwd()) / path
            path = Path(os.path.normpath(path))
            if (path.is_relative_to(prefix.parent) or path.is_relative_to(original_store)
                    or path.is_relative_to(Path(proof['original_native_handle']['cwd']))
                    or path in {owned / 'artifacts' / ref[9:11] / ref[9:] for ref in raw_inputs}):
                audit['forbidden_work_attempts'].append(dict(path=str(path)))
                raise AssertionError('closed HOMER replay opened original input/runtime/workspace bytes')

        def checked_path(path, *args, **kwargs): check_path(path); return path_open(path, *args, **kwargs)
        def checked_builtin(path, *args, **kwargs): check_path(path); return builtin_open(path, *args, **kwargs)
        def checked_io(path, *args, **kwargs): check_path(path); return io_open(path, *args, **kwargs)
        def checked_os(path, flags, *args, **kwargs):
            check_path(path, dir_fd=kwargs.get('dir_fd')); return os_open(path, flags, *args, **kwargs)
        def packet_only(reference):
            assert reference in packets, 'closed HOMER reader opened private controls, raw data or numerical sheet'
            return original_get(reference)

        class NoDecisions:
            async def complete(self, *args, **kwargs): return forbidden(*args, **kwargs)
            async def release(self, episode_id): pass

        audit['owned_database_cloned'] = True
        _write(output, audit)
        with monkeypatch.context() as guard:
            for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect', 'cancel'):
                guard.setattr(native_lifecycle, name, forbidden)
            for name in ('prepare_ordinary_homer_attempt', 'run_ordinary_homer_attempt'):
                guard.setattr(native, name, forbidden)
            for name in ('run_native_homer', 'run_homer_motif_job'):
                guard.setattr(native_homer_worker, name, forbidden)
            for name in ('parse_homer_motif_sheet', 'calculate_homer_components', 'project_homer_return'):
                guard.setattr(measurements, name, forbidden)
            guard.setattr(ToolRegistry, '_sequence_worker_async', forbidden)
            guard.setattr(ToolRegistry, '_source', forbidden)
            guard.setattr(Store, 'artifact', forbidden)
            guard.setattr(host, 'execute_homer_tool', forbidden)
            guard.setattr(host, '_control', forbidden)
            guard.setattr('gene_annotation_episode.acquisition.PublicClients._http', forbidden)
            guard.setattr(socket, 'create_connection', forbidden)
            guard.setattr(socket.socket, 'connect', forbidden)
            guard.setattr(socket.socket, 'connect_ex', forbidden)
            guard.setattr(store, 'get_artifact', packet_only)
            guard.setattr(Path, 'open', checked_path)
            guard.setattr('builtins.open', checked_builtin)
            guard.setattr('io.open', checked_io)
            guard.setattr(os, 'open', checked_os)
            replay, tools = _assemble(store, directory, configuration, NoDecisions())
            records = EpisodeReturnRecords(store, run_id, failure_prefix='homer_closed_replay_')
            parent, science = [records.context(row['episode_id']) for row in (parent_row, science_row)]
            for context in (parent, science):
                records.authenticate(context)
                known_before[context.episode_id] = set(replay.receipts.known(context.episode_id))
            root = replay.build('annotation', 'root', QUESTION, configuration['scope'])
            closed = asyncio.run(root.run_async(replay.context))
            archive = _archive_value(closed)
            assert archive == proof['archive']
            final = plain(asyncio.run(root.build_result(closed)).as_record())
            assert final == proof['final_result']
            audit.update(closed_replay_verified=True, archive=archive, final_result=final)
            assert replay.services.molecular_frozen_facts(science, fact_source=contracts.FACT_SOURCE) == original_values
            assert replay.services.molecular_received_facts(parent, fact_source=contracts.FACT_SOURCE) == original_values
            form, = history['runtime_forms']
            assert json.loads(form['form']) == proof['typed_form']
            attempt, = history['runtime_report_attempts']
            assert attempt['failure'] is None and json.loads(attempt['form']) == proof['typed_form']
            audit['typed_parent_delivery_verified'] = True
            for context in (parent, science):
                for value in original_values:
                    assert host.read_retained_homer_publication(tools, context,
                        replay.services.read_received_molecular_input, value['source_ref']) == value
                _capabilities(store, replay, context, original_values, private, raw_inputs, audit)
                assert set(replay.receipts.known(context.episode_id)) == known_before[context.episode_id]
            audit.update(literal_read_verified=True, private_permissions_verified=True,
                permission_qualification='Preserve legitimate baseline scope File grants; private HOMER and raw run operands remain unreceived.')
        assert rows(store.db) == original_rows
        assert all(_history(store, run_id) == value for run_id, value in proof['actual_histories'].items())
        assert audit['forbidden_work_attempts'] == []
        assert _sqlite_pins(original_store) == bundle
        assert _inventory(original_store / 'artifacts') == original_artifacts
        assert _inventory(original_run) == original_run_files and _pin(prefix) == prefix_pin
        audit.update(histories_unchanged=True, originals_unchanged=True, passed=True, phase='verified',
            table_counts={name: len(value) for name, value in original_rows.items()},
            received_result_sources=[value['source_ref'] for value in original_values])
    except BaseException as error:
        audit['failure'] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        if store is not None:
            try: audit['actual_table_counts'] = {name: len(value) for name, value in rows(store.db).items()}
            except BaseException as error:
                audit['history_capture_failure'] = dict(exception_type=type(error).__name__, message=str(error))
            finally: store.close()
            audit['owned_database'] = _pin(store.path / 'state.sqlite3')
        _write(output, audit)
