"""Ordinary TF integration and retained recovery, selected explicitly by the runner.

The choices are deterministic engineering fixtures. Native scoring, journals,
Source custody and typed delivery use the actual application ports.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import struct
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_lifecycle
from gene_annotation_episode import tf_binding_measurements as core
from gene_annotation_episode import tf_binding_result_contracts as contracts
from gene_annotation_episode import tf_binding_tools as host
from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.molecular_sequence_input_bindings import MolecularSequenceInputBindings
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_homer_motif_saved_workflow import _archive, _archive_value, _encode
from test_runtime import FixtureController


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = 'research/slotted_process_library/publications/2026-10-24-001'
POLICY = dict(memory_bytes=21474836480, scratch_bytes=4294967296)
ENVIRONMENT = dict(version='tf_binding_execution_selection_v1',
    environment_realization='operation_scoped_tmp_and_cache_v1')
QUESTION = ('Which positions and strands in the supplied GATC DNA meet raw log2-odds thresholds '
    '2 and 0 for the supplied count matrix, using the declared background and zero pseudocounts? '
    'Retain both selected strand score arrays. Return candidate sites at raw log2-odds '
    'threshold 2, read that fixed result, then use the same saved scores '
    'at threshold 0 and select that exact saved view again. Preserve original coordinates, '
    'qualifications and the distinction between candidates and measured binding or regulation. '
    'The extra binary input is an explicitly unselected invalid DNA slot, not measured DNA; '
    'these fragments establish no gene or neighborhood context.')
JOURNALS = ('runtime_episodes', 'runtime_actions', 'runtime_observations',
    'runtime_model_calls', 'runtime_forms', 'runtime_report_attempts')


def _write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def _pin(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _sqlite_pins(directory):
    return [dict(name=name, **{k: v for k, v in _pin(path).items() if k != 'path'})
        for name in ('state.sqlite3', 'state.sqlite3-wal', 'state.sqlite3-shm')
        if (path := Path(directory) / name).is_file()]


def _inventory(directory):
    root = Path(directory)
    return [dict(relative_path=str(path.relative_to(root)), mode=stat.S_IMODE(path.stat().st_mode),
        sha256=value['sha256'], size_bytes=value['size_bytes'])
        for path in sorted(root.rglob('*')) if path.is_file() for value in [_pin(path)]]


def _tables(store):
    result = {}
    for row in store.db.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name"):
        name = row['name']
        quoted = '"' + name.replace('"', '""') + '"'
        columns = [r[1] for r in store.db.execute('PRAGMA table_info(' + quoted + ')')]
        rows = [list(r) for r in store.db.execute('SELECT * FROM ' + quoted)]
        result[name] = dict(sql=row['sql'], columns=columns, rows=sorted(rows, key=canonical))
    return result


def _history(store, run_id):
    result = {name: [dict(row) for row in store.db.execute(
        'SELECT * FROM ' + name + ' WHERE run_id=? ORDER BY rowid', (run_id,))] for name in JOURNALS}
    result['tool_operations'] = [dict(row) for row in store.db.execute(
        'SELECT * FROM tool_operations WHERE substr(operation_key,1,?)=? ORDER BY rowid',
        (len(run_id) + 1, run_id + ':'))]
    return result


def _form():
    return obj(dict(sites=contracts.tf_binding_fact_sources()[contracts.FACT_SOURCE]['report_schema']))


def _controller(path, initial):
    return FixtureController(str(path), initial, 4 if path[-1][0] == 'scientific_process' else 1)


def _credit(*args, **kwargs):
    return 0


def _selection(threshold):
    return dict(scope='all_retained_scans', scan_ids=None, raw_threshold=threshold, offset=0, limit=20)


def _assemble(store, directory, proof, provider):
    factory = ExecutionServiceFactory.from_record(proof['factory'])
    tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
    application = factory(store, run_id=proof['run_id'], directory=directory, tool_registry=tools)
    workflow = Workflow(store, tools, provider, directory, proof['run_id'], _controller, _credit,
        project_child_credit=_credit, episode_record_receipts=True,
        initial_known_record_refs=proof['initial_known_record_refs'],
        episode_binding_descriptors=[proof['scientific_binding'], *application.episode_binding_descriptors],
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    return workflow, tools


def _checkpoint(store, workflow, proof, path):
    proof['history'] = _history(store, workflow.run_id)
    proof['counts'] = {name: len(rows) for name, rows in proof['history'].items()}
    proof['tables'] = _tables(store)
    _write(path, proof)


def _inputs(store):
    values = [('dna', 'dna', 'raw_dna', b'GATC'),
        ('matrix', 'matrix', 'acgt_count_json', canonical(dict(A=[2, 4], C=[1, 2], G=[1, 1], T=[4, 1]))),
        ('unselected-binary', 'dna', 'raw_dna', struct.pack('<3f', 0, -1, 2))]
    rows, refs = [], []
    for input_id, role, fmt, raw in values:
        reference = store.artifact(raw, 'application/octet-stream')
        refs.append(reference)
        rows.append(dict(input_id=input_id, role=role, format=fmt, namespace='artifact', reference=reference))
    return rows, refs


def _assert_tf_display(text, packet):
    """Independent display boundary: literal scientific operands and values."""
    for heading in ('Selected scans in caller order', 'Declared input parameters before native normalization',
            'Original sequence occurrences', 'Original matrix occurrences',
            'Retained scans available for saved selection', 'Retained counts for the selected scans',
            'Returned raw-threshold rows; coordinates are zero-based forward-sequence intervals',
            'Retained relative normalization', 'Result qualifications'):
        assert heading in text
    assert '| Raw log2-odds threshold | ' + str(packet['selection']['raw_threshold']) + ' |' in text
    assert packet['source_ref'] in text
    for scan in packet['selection']['scan_ids']:
        assert scan in text
    for base in 'ACGT':
        assert '| ' + base + ' | ' + str(packet['parameters']['background'][base]) + ' | ' + str(packet['parameters']['pseudocounts'][base]) + ' |' in text
    for key in ('possible_strand_windows', 'model_eligible_candidate_sites', 'nan_scores', 'negative_infinity_scores'):
        cell = packet['totals'][key]
        value = 'null' if cell['value'] is None else str(cell['value'])
        assert '| ' + key.replace('_', ' ') + ' | ' + value + ' | ' + cell['state'] + ' | ' + cell['unit'] + ' |' in text
    assert 'forward_pssm_bounds_for_both_strands' in text
    # These keys belong to the controlled DTO, not the finite literal display.
    for field in ('raw_threshold_matches', 'relative_normalizations', 'numeric_authority', 'available_scans'):
        assert '"' + field + '":' not in text


class _Choices:
    def __init__(self, store, library, proof, output, active):
        self.store, self.library, self.proof, self.output, self.active = store, library, proof, output, active
        self.turns, self.states = {}, {}
        self.connection = object.__new__(_SessionConnection)
        self.connection.scientific_prompt_states = {}

    async def complete(self, episode_id, role, instructions, context, schema):
        current = plain(context)
        row = self.store.db.execute('SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.proof['run_id'], episode_id)).fetchone()
        grain = json.loads(row['path'])[-1][0]
        turn = self.turns.get(episode_id, 0) + 1
        self.turns[episode_id] = turn
        assert role == 'REASONING' and not current.get('feedback'), current.get('feedback')
        assert current['goal']['objective'] == QUESTION
        wire, wire_instructions = self.connection._presentation(episode_id, role, instructions,
            state_frame(current, self.states.get(episode_id)))
        self.states[episode_id] = deepcopy(current)
        call = dict(episode_id=episode_id, grain=grain, turn=turn, provider_role=role,
            context=deepcopy(current), schema=deepcopy(schema), instructions=plain(instructions),
            wire=wire, wire_instructions=plain(wire_instructions))
        self.proof['calls'].append(call)
        if grain == 'annotation':
            assert turn == 1
            selected = dict(kind='episode_child', role='scientific_process', goal=QUESTION,
                scope=deepcopy(self.proof['scope']), purpose=QUESTION, schema_json=json.dumps(_form()),
                initial_report_json='{}', assignment=dict(selection=dict(version='scientific_process_selection_v3',
                    evidence_axis=self.library.reference('A103'), thought_pattern=self.library.reference('P01'),
                    child_tool_info=[dict(name=contracts.TOOL, resources='local')]), evidence_refs=[], constraints={},
                    context=dict(tf_binding_request=deepcopy(self.proof['arguments']))))
        else:
            assert grain == 'scientific_process' and 1 <= turn <= 4
            self.active['turn'] = turn
            assert current['requested_form'] == _form()
            assert current['scientific_process']['assignment']['context']['tf_binding_request'] == self.proof['arguments']
            information, = [r for r in current['tools'] if r['name'] == contracts.TOOL]
            assert information['resources'] == 'local'
            assert wire.startswith('TASK\n') and '\n\nSTEERING\n' in wire
            task, steering = wire.split('\n\nSTEERING\n', 1)
            assert QUESTION in task
            assert self.proof['selected_tool_contract']['instructions'] in task
            assert self.proof['selected_tool_contract']['description'] in task
            assert 'Operands for ' + contracts.TOOL in task and 'Parent return form' in task
            if turn > 1:
                shown = contracts.validate_tf_binding_return(current['last_local_outcome']['result'])
                assert shown['selection']['raw_threshold'] == (0 if turn == 4 else 2)
                assert shown['parameters'] == self.proof['arguments']['parameters']
                _assert_tf_display(steering, shown)
                call['finite_tf_display_verified'] = True
            previous = [json.loads(r['result']) for r in self.store.db.execute(
                'SELECT result FROM tool_operations WHERE substr(operation_key,1,?)=? ORDER BY rowid',
                (len(self.proof['run_id']) + 1, self.proof['run_id'] + ':'))]
            if turn == 1:
                arguments = deepcopy(self.proof['arguments'])
            elif turn == 2:
                assert len(previous) == 1
                arguments = dict(mode='read_stored', result_ref=previous[0]['result']['source_ref'])
            elif turn == 3:
                assert len(previous) == 2 and previous[1]['result'] == previous[0]['result']
                assert previous[1]['changed_record_refs'] == []
                self.proof['literal_read_verified'] = True
                arguments = dict(mode='calculate_saved', result_ref=previous[0]['result']['source_ref'], selection=_selection(0))
            else:
                assert len(previous) == 3 and previous[2]['result']['source_ref'] != previous[0]['result']['source_ref']
                arguments = dict(mode='calculate_saved', result_ref=previous[2]['result']['source_ref'], selection=_selection(0))
            selected = dict(kind='tool', tool=contracts.TOOL, arguments=arguments)
        value = _encode(dict(selection=selected, report_update={}), schema)
        call['response'] = deepcopy(value)
        self.proof['phase'] = 'decision_selected'
        _write(self.output, self.proof)
        return value

    async def release(self, episode_id):
        pass


def _capabilities(store, workflow, contexts, values, initial, arguments):
    sources = [store.get(value['source_ref']) for value in values]
    capture = store.get(sources[0]['parent_source_refs'][0])
    protected_inputs = {row['reference'] for row in arguments['inputs']}
    private = {capture['id'], capture['artifact_ref'], capture['request_ref'], *capture['auxiliary_artifact_refs']}
    for source in sources:
        private.update([source['artifact_ref'], source['request_ref'], *source['auxiliary_artifact_refs']])
    assert private.isdisjoint(protected_inputs)
    services = workflow.services
    def actual_access(current, reference, namespace):
        verdict = services._molecular_reference_access(current, reference, namespace)
        return (verdict if verdict is not None else
            workflow.episode_bindings.resolve_received_reference(current, reference, namespace))
    # Exactly the existing WorkflowServices received-input owner construction.
    # Reuse its metadata admission before the public reader would stream bytes.
    binding = MolecularSequenceInputBindings(SimpleNamespace(store=store, run_id=workflow.run_id,
        resolve_received_reference=actual_access,
        commission_assignment_matches=services.molecular_commission_assignment_matches))
    input_admissions, form_verdicts = [], []
    for context in contexts:
        known = set(workflow.receipts.known(context.episode_id))
        assert set(initial) | {value['source_ref'] for value in values} <= known
        assert private.isdisjoint(known)
        resolver = workflow.resolver(plain(context.scope), context=context)
        for reference in private:
            assert resolver(reference, 'source' if reference == capture['id'] else 'artifact') is False
        for reference in sorted(protected_inputs):
            metadata_owned = bool(store.reference_subset([reference], plain(context.scope)))
            verdict = resolver(reference, 'artifact')
            if metadata_owned:
                assert verdict is True
            form_verdicts.append(dict(episode_id=context.episode_id, reference=reference,
                store_metadata_owned=metadata_owned, form_reference_resolver_verdict=verdict))
        # Exercise actual operand rejection, including a Source guess. These
        # denied operands must not open any Artifact body on their way out.
        reader = workflow.services.read_received_molecular_input
        original_open = Path.open
        def metadata_only_open(path, *args, **kwargs):
            assert not Path(path).resolve().is_relative_to(store.path / 'artifacts')
            return original_open(path, *args, **kwargs)
        with pytest.MonkeyPatch.context() as guard:
            guard.setattr(Path, 'open', metadata_only_open)
            guard.setattr(store, 'get_artifact', lambda *args, **kwargs: pytest.fail('denied operand read Artifact bytes'))
            changes = store.db.total_changes
            for row in arguments['inputs']:
                with store.read_snapshot():
                    item = binding._received_file_item(context, row['reference'],
                        row['namespace'], file_format=row['format'])
                assert row['reference'] in known
                assert item['witness']['reference'] == row['reference']
                assert item['witness']['namespace'] == row['namespace']
                assert item['receiver']['episode_id'] == context.episode_id
                assert item['file']['artifact_ref'] == row['reference']
                assert item['file']['format'] == row['format']
                assert item['byte_verification'] == 'unavailable'
                input_admissions.append(dict(episode_id=context.episode_id, reference=row['reference'],
                    file=item['file'], witness_record_sha256=item['witness']['record_sha256'],
                    metadata_admitted=True, bytes_read=False))
            assert store.db.total_changes == changes
            denied = reader(context, capture['id'], 'source', source_metadata_only=True)
            assert denied['failure'] is not None and denied['input'] is None
            for reference in (sources[0]['request_ref'], next(iter(capture['auxiliary_artifact_refs']))):
                denied, path = reader(context, reference, 'artifact', file_format='binary')
                assert denied['failure'] is not None and denied['input'] is None and path is None
        for value in values:
            assert host.read_retained_tf_binding_publication(workflow.tools, context,
                workflow.services.read_received_molecular_input, value['source_ref']) == value
        assert set(workflow.receipts.known(context.episode_id)) == known
    return dict(private_refs=sorted(private), protected_input_refs=sorted(protected_inputs),
        received_values=[value['source_ref'] for value in values], input_grants_preserved=True,
        received_input_metadata_admissions=input_admissions, generic_form_reference_verdicts=form_verdicts,
        capture_and_private_file_grants_added=False)


def _closed_delivery(store, workflow, proof):
    history = _history(store, workflow.run_id)
    rows = sorted(history['runtime_episodes'], key=lambda r: len(json.loads(r['path'])))
    assert len(rows) == 2 and all(r['state'] == 'yielded' and r['archive'] and r['completion'] for r in rows)
    assert all(len(history[name]) == 5 for name in ('runtime_actions', 'runtime_observations', 'runtime_model_calls'))
    operations = history['tool_operations']
    assert len(operations) == 4
    arguments = [json.loads(r['arguments']) for r in operations]
    outcomes = [json.loads(r['result']) for r in operations]
    assert [r['mode'] for r in arguments] == ['run_native', 'read_stored', 'calculate_saved', 'calculate_saved']
    assert arguments[0] == proof['arguments']
    assert all(r['status'] in ('completed', 'partial') for r in outcomes)
    values = [contracts.validate_tf_binding_return(r['result']) for r in outcomes]
    assert values[0] == values[1] and values[2] == values[3]
    assert values[0]['source_ref'] != values[2]['source_ref']
    for index, outcome in enumerate(outcomes):
        assert outcome['record_refs'] == [values[index]['source_ref']]
        assert outcome['changed_record_refs'] == ([] if index in (1, 3) else [values[index]['source_ref']])
    assert [values[i]['totals']['model_eligible_candidate_sites']['value'] for i in (0, 2)] == [2, 4]
    assert all(value['totals']['possible_strand_windows']['value'] == 6 for value in values)
    assert all(value['parameters'] == proof['arguments']['parameters'] for value in values)
    assert [(r['start_0based'], r['end_0based_exclusive'], r['strand']) for r in values[0]['hits']] == [(0, 2, '-'), (2, 4, '+')]
    assert [(r['start_0based'], r['end_0based_exclusive'], r['strand']) for r in values[2]['hits']] == [(0, 2, '+'), (0, 2, '-'), (2, 4, '+'), (2, 4, '-')]
    records = EpisodeReturnRecords(store, workflow.run_id, failure_prefix='tf_workflow_')
    parent, science = [records.context(r['episode_id']) for r in rows]
    for context in (parent, science): records.authenticate(context)
    expected = dict(sites=[values[0], values[2]])
    form, = history['runtime_forms']
    attempt, = history['runtime_report_attempts']
    assert form['episode_id'] == science.episode_id and json.loads(form['form']) == expected
    assert attempt['failure'] is None and json.loads(attempt['form']) == expected
    assert attempt['parent_episode_id'] == parent.episode_id and attempt['child_episode_id'] == science.episode_id
    assert workflow.services.molecular_own_facts(science, fact_source=contracts.FACT_SOURCE) == expected['sites']
    assert workflow.services.molecular_frozen_facts(science, fact_source=contracts.FACT_SOURCE) == expected['sites']
    assert workflow.services.molecular_received_facts(parent, fact_source=contracts.FACT_SOURCE) == expected['sites']
    archives = [_archive(r, workflow.directory) for r in rows]
    assert [r['units_consumed'] for r in archives] == [1, 4]
    assert archives[0]['units'][0]['child_result'] == dict(form=expected)
    assert all(r['ended_by'] == 'yield_stop' for r in archives)
    return dict(values=expected['sites'], returned=expected, episode_ids=[parent.episode_id, science.episode_id],
        archives=archives, outcomes=outcomes), (parent, science)


def _native_custody(store, proof, delivery):
    first, changed = [store.get(v['source_ref']) for v in delivery['values']]
    capture = store.get(first['parent_source_refs'][0])
    assert first['version'] == changed['version'] == contracts.SOURCE_VERSION
    assert first['provider'] == changed['provider'] == capture['provider'] == contracts.TOOL
    assert changed['parent_source_refs'] == [first['id']]
    assert capture['version'] == contracts.CAPTURE_VERSION
    operations = proof['history']['tool_operations']
    assert capture['accession'] == operations[0]['id']
    assert len(list(store.db.execute("SELECT id FROM records WHERE record_type='source' AND json_extract(data,'$.provider')=?",
        (contracts.TOOL,)))) == 3
    custody = json.loads(store.get_artifact(capture['request_ref']))
    worker = custody['native_worker']
    assert worker['observation']['terminal'] is worker['observation']['quiescent'] is True
    assert worker['observation']['metadata']['native_returncode'] == 0
    assert worker['selection']['request']['operation'] == 'tf_binding_native'
    assert custody['input_artifact_refs'] == [r['reference'] for r in proof['arguments']['inputs']]
    body = json.loads(store.get_artifact(capture['artifact_ref']))
    native = core.validate_tf_binding_native_value(body['original_manifest']['value'])
    assert native['returncode'] is None and len(native['scans']) == 2 and len(native['models']) == 1
    assert native['scan_selection'] == proof['arguments']['scan_selection']
    assert [r['input_id'] for r in native['input_identities']] == ['dna', 'matrix', 'unselected-binary']
    arrays = {}
    for scan in native['scans']:
        assert scan['state'] == 'complete' and scan['possible_positions'] == scan['declared_count'] == 3
        row, = [r for r in body['outputs'] if r['declared'] is not None and r['declared']['file_id'] == scan['score_file_id']]
        raw = store.get_artifact(row['file']['artifact_ref'])
        assert len(raw) == scan['size_bytes'] == 12 and hashlib.sha256(raw).hexdigest() == scan['sha256']
        arrays[scan['strand']] = list(struct.unpack(('<' if scan['byte_order'] == 'little' else '>') + '3f', raw))
        if scan['strand'] == '+': assert row['file']['artifact_ref'] == proof['arguments']['inputs'][2]['reference']
    assert arrays == {'+': [0, -1, 2], '-': [2, -1, 0]}
    controls = []
    for source, value in zip((first, changed), delivery['values'], strict=True):
        control = json.loads(store.get_artifact(source['request_ref']))
        assert control['capture_source']['source_ref'] == capture['id']
        assert control['worker']['observation']['terminal'] is control['worker']['observation']['quiescent'] is True
        assert control['worker']['observation']['metadata']['native_returncode'] == 0
        components = core.validate_tf_binding_components(json.loads(store.get_artifact(control['components_file']['artifact_ref'])))
        assert core.project_tf_binding_return(components, source['id']) == value
        controls.append(control)
    assert [control['invocation']['operation_key'] for control in controls] == [operations[i]['operation_key'] for i in (0, 2)]
    assert controls[0]['sheet_file'] == controls[1]['sheet_file']
    assert controls[0]['worker']['request']['mode'] == 'parse'
    assert controls[1]['worker']['request']['mode'] == 'calculate_saved'
    protected = set(custody['input_artifact_refs'])
    assert protected.isdisjoint(capture['auxiliary_artifact_refs'])
    assert all(protected.isdisjoint(source['auxiliary_artifact_refs']) for source in (first, changed))
    return dict(source_records=[first, changed], capture_source=capture, native_value=native,
        observed_arrays=arrays, controls=controls, one_native_worker_two_result_workers=True,
        unselected_binary_input_scored=False, original_input_collision_preserved=True)


def test_genuine_tf_binding_native_saved_views_and_typed_return(tmp_path, monkeypatch):
    if os.environ.get('ORDINARY_TF_BINDING_GENUINE') != '1':
        pytest.skip('requires explicit bounded genuine ordinary TF selection')
    attempt = os.environ.get('ORDINARY_TF_BINDING_ATTEMPT_ID')
    assert attempt and Path(attempt).name == attempt and attempt not in ('.', '..')
    case = tmp_path / ('tf-binding-' + attempt)
    case.mkdir()
    output = case / 'TF_BINDING_WORKFLOW_PREFIX.json'
    proof = dict(version='ordinary_tf_binding_workflow_prefix_v1', run_id='ordinary-tf-' + attempt,
        case_directory=str(case), store_directory=str(case / 'store'), workflow_directory=str(case / 'run'),
        question=QUESTION, calls=[], worker_calls=[], phase='prepared', literal_read_verified=False,
        native_custody_verified=False, typed_delivery_verified=False, closed_workflow_verified=False,
        qualification='Deterministic engineered choices and tiny supplied inputs; genuine ordinary Bio scoring and owned result workers.')
    _write(output, proof)
    active = dict(turn=0)
    try:
        workspace = case / 'native-workspace'; workspace.mkdir()
        resources = {'selected-tf': dict(kind='local', workspace=str(workspace), policy=deepcopy(POLICY))}
        factory = ExecutionServiceFactory(resources, {}, 2, .25, .5,
            tf_binding_environments=[dict(operation=contracts.TOOL, resource_id='selected-tf', environment=deepcopy(ENVIRONMENT))],
            tf_binding_saved_modes=True)
        proof['factory'] = factory.as_record()
        with Store(case / 'store') as store:
            subject, = store.create_problem(raw_sequence='GATC', molecule='dna')['subject_refs']
            inputs, refs = _inputs(store)
            proof.update(subject_ref=subject, scope=store.validate_scope(), initial_known_record_refs=[subject, *refs],
                arguments=dict(mode='run_native', inputs=inputs, parameters=dict(
                    background=dict(A=.5, C=.25, G=.125, T=.125), pseudocounts=dict(A=0, C=0, G=0, T=0)),
                    scan_selection=dict(mode='explicit', requests=[dict(sequence_input_id='dna',
                        sequence_record_ordinal_0based=0, matrix_input_id='matrix', matrix_record_ordinal_0based=0,
                        strands=['+', '-'])]), selection=_selection(2)))
            configured = ToolRegistry(store, job_limits=deepcopy(POLICY)); factory.configure_tool_registry(configured)
            entry = configured.catalog()[contracts.TOOL]
            assert entry['invocation_route'] == dict(kind='direct') and entry['resources'] == 'local'
            assert entry['configuration']['saved_modes'] is True
            proof['selected_tool_contract'] = entry
            proof['scientific_binding'] = prepare_scientific_binding(run_directory=case / 'run',
                source_directory=ROOT / PUBLICATION, tool_catalog=configured.catalog(), child_roles=['scientific_process'])
            library = ScientificProcessLibrary(case / 'run/scientific-process-library')
            provider = _Choices(store, library, proof, output, active)
            workflow, tools = _assemble(store, case / 'run', proof, provider)
            original_worker = tools._sequence_worker_async
            async def measured_worker(operation, arguments, **kwargs):
                assert active['turn'] in (1, 3), 'literal read/no-op attempted a worker'
                assert operation in ('tf_binding_native', 'tf_binding_result')
                if active['turn'] == 3:
                    assert operation == 'tf_binding_result' and arguments['request']['mode'] == 'calculate_saved'
                proof['worker_calls'].append(dict(turn=active['turn'], operation=operation,
                    mode=arguments['request'].get('mode'), directory=str(kwargs['directory'])))
                _write(output, proof)
                return await original_worker(operation, arguments, **kwargs)
            monkeypatch.setattr(tools, '_sequence_worker_async', measured_worker)
            original_control, original_calculate = host._control, core.calculate_tf_binding_components
            def guarded_control(*args, **kwargs):
                assert active['turn'] not in (2, 4), 'literal read/no-op reopened private controls'
                return original_control(*args, **kwargs)
            def guarded_calculate(*args, **kwargs):
                raise AssertionError('host attempted a scientific calculation outside the owned worker')
            monkeypatch.setattr(host, '_control', guarded_control)
            monkeypatch.setattr(core, 'calculate_tf_binding_components', guarded_calculate)
            root = workflow.build('annotation', 'root', QUESTION, proof['scope'])
            try:
                _checkpoint(store, workflow, proof, output)
                completed = asyncio.run(root.run_async(workflow.context))
                proof['phase'] = 'workflow_returned'
                proof['archive'] = _archive_value(completed)
                _checkpoint(store, workflow, proof, output)
                active['turn'] = 0
                delivery, contexts = _closed_delivery(store, workflow, proof)
                proof['typed_delivery_verified'] = True
                proof['delivery'] = delivery
                proof['native_custody'] = _native_custody(store, proof, delivery)
                proof['native_custody_verified'] = True
                proof['capabilities'] = _capabilities(store, workflow, contexts, delivery['values'], proof['initial_known_record_refs'], proof['arguments'])
                assert [(r['turn'], r['operation'], r['mode']) for r in proof['worker_calls']] == [
                    (1, 'tf_binding_native', None), (1, 'tf_binding_result', 'parse'), (3, 'tf_binding_result', 'calculate_saved')]
                assert len(proof['calls']) == 5 and [r['grain'] for r in proof['calls']] == ['annotation'] + ['scientific_process'] * 4
                for call in proof['calls'][1:]:
                    assert 'TASK' in call['wire'] and 'STEERING' in call['wire']
                    assert str(case) not in call['wire']
                    assert QUESTION in call['wire'] and proof['selected_tool_contract']['instructions'] in call['wire']
                assert all(call['finite_tf_display_verified'] for call in proof['calls'][2:])
                proof['wire_verified'] = True
                final = _archive_value(asyncio.run(root.build_result(completed)))
                assert final == dict(credit=0, pending_handles=[])
                proof.update(final_result=final, phase='workflow_closed', closed_workflow_verified=True)
            finally:
                _checkpoint(store, workflow, proof, output)
                monkeypatch.setattr(core, 'calculate_tf_binding_components', original_calculate)
    except BaseException as error:
        proof['failure'] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        if (case / 'store/state.sqlite3').is_file():
            proof['sqlite_pins'] = _sqlite_pins(case / 'store')
            proof['sqlite_pins_sha256'] = digest(proof['sqlite_pins'])
        _write(output, proof)


def _dispatch_fixture(tmp_path):
    directory = tmp_path / 'worker'; directory.mkdir()
    resource = dict(resource_id='tf', resource=dict(kind='local', workspace=str(tmp_path), policy=deepcopy(POLICY)),
        environment=deepcopy(ENVIRONMENT))
    registry = SimpleNamespace(local_job_policy=LocalJobPolicy(**POLICY))
    owner = SimpleNamespace(resources={'tf': deepcopy(resource['resource'])})
    request = dict(engineered_metadata_only=True)
    selected = dict(version='ordinary_molecular_execution_v1', command=['/selected/python', '-m',
        'gene_annotation_episode.tf_binding_driver', str(directory / 'worker-request.json'), str(directory / 'worker-result.json')],
        cwd=str(directory), environment={}, policy=deepcopy(POLICY), request=dict(operation='tf_binding_native', arguments=dict(request=deepcopy(request))),
        python=dict(path='/selected/python'), implementation_files=[])
    return directory, resource, registry, owner, request, selected


@pytest.mark.parametrize('field', ['request', 'command', 'cwd', 'policy'])
def test_tf_dispatch_rejects_changed_original_selection_before_work(tmp_path, field):
    directory, resource, registry, owner, request, selected = _dispatch_fixture(tmp_path)
    if field == 'request': selected['request']['arguments']['request']['changed'] = True
    elif field == 'command': selected['command'][2] = 'gene_annotation_episode.tf_binding_result_worker'
    elif field == 'cwd': selected['cwd'] += '-other'
    else: selected['policy']['scratch_bytes'] += 1
    _write(directory / 'execution-selection.json', selected)
    before = _inventory(tmp_path)
    with pytest.raises(ValueError, match='tf_binding_original_worker_selection_conflict'):
        host._worker_dispatch(registry, owner, request, directory, 'tf_binding_native', POLICY, resource)
    assert _inventory(tmp_path) == before


def test_tf_dispatch_preserves_original_policy_without_repricing(tmp_path):
    directory, resource, registry, owner, request, selected = _dispatch_fixture(tmp_path)
    _write(directory / 'execution-selection.json', selected)
    registry.local_job_policy = LocalJobPolicy(**dict(POLICY, scratch_bytes=POLICY['scratch_bytes'] * 2))
    owner.resources = {}
    before = _inventory(tmp_path)
    host._worker_dispatch(registry, owner, request, directory, 'tf_binding_native', POLICY, resource)
    assert _inventory(tmp_path) == before


@pytest.mark.parametrize('fault', ['current_policy', 'resource'])
def test_tf_dispatch_authenticates_first_allocation_before_work(tmp_path, fault):
    directory, resource, registry, owner, request, _ = _dispatch_fixture(tmp_path)
    if fault == 'current_policy':
        registry.local_job_policy = LocalJobPolicy(**dict(POLICY, scratch_bytes=POLICY['scratch_bytes'] * 2))
    else:
        owner.resources['tf']['workspace'] += '-other'
    before = _inventory(tmp_path)
    with pytest.raises(ValueError, match='tf_binding_run_resource_selection_conflict'):
        host._worker_dispatch(registry, owner, request, directory, 'tf_binding_native', POLICY, resource)
    assert _inventory(tmp_path) == before


def _copy_retained_case(proof, owned):
    """Recover committed SQLite only after copying every physical family member."""
    original_store = Path(proof['store_directory'])
    physical = _sqlite_pins(original_store)
    assert physical == proof['sqlite_pins']
    assert digest(physical) == os.environ['ORDINARY_TF_BINDING_RETAINED_SQLITE_PINS_SHA256']
    staging = owned / 'physical-sqlite-copy'; staging.mkdir(parents=True)
    for item in physical:
        shutil.copy2(original_store / item['name'], staging / item['name'])
    assert _sqlite_pins(staging) == physical
    store_directory = owned / 'store'; store_directory.mkdir()
    source = sqlite3.connect(staging / 'state.sqlite3')
    destination = sqlite3.connect(store_directory / 'state.sqlite3')
    try:
        source.backup(destination)
    finally:
        destination.close(); source.close()
    shutil.copytree(original_store / 'artifacts', store_directory / 'artifacts')
    directory = owned / 'run'
    shutil.copytree(proof['workflow_directory'], directory)
    return store_directory, directory


def test_retained_tf_binding_workflow_replays_without_scoring_or_calculation(tmp_path, monkeypatch):
    original_path = os.environ.get('ORDINARY_TF_BINDING_RETAINED_PROOF')
    if not original_path:
        pytest.skip('requires the exact retained original TF attempt; never reruns the genuine node')
    original_path = Path(original_path).resolve(strict=True)
    assert _pin(original_path)['sha256'] == os.environ['ORDINARY_TF_BINDING_RETAINED_PROOF_SHA256']
    proof = json.loads(original_path.read_bytes())
    assert proof['version'] == 'ordinary_tf_binding_workflow_prefix_v1'
    assert Path(proof['store_directory']).resolve(strict=True) == Path(os.environ['ORDINARY_TF_BINDING_RETAINED_STORE']).resolve(strict=True)
    # A late fixture assertion may leave flags false. Actual closed journals and
    # archives below, rather than such flags, authenticate completed work.
    assert proof['history'] and proof['tables'] and len(proof['calls']) == 5
    original_case = Path(proof['case_directory']).resolve(strict=True)
    original_before = _inventory(original_case)
    original_proof_pin = _pin(original_path)
    physical_before = _sqlite_pins(proof['store_directory'])
    owned = tmp_path / 'owned-retained-tf'
    store_directory, directory = _copy_retained_case(proof, owned)
    output = tmp_path / 'TF_BINDING_RETAINED_REPLAY.json'
    audit = dict(version='ordinary_tf_binding_retained_replay_v1', original_proof=original_proof_pin,
        original_sqlite_pins=physical_before, run_id=proof['run_id'], store_directory=str(store_directory),
        workflow_directory=str(directory), phase='copied', replay_verified=False, literal_reads_verified=False,
        zero_new_scientific_work=False, original_flags={key: proof.get(key) for key in (
            'native_custody_verified', 'typed_delivery_verified', 'closed_workflow_verified', 'wire_verified')})
    _write(output, audit)
    def forbidden(*args, **kwargs):
        raise AssertionError('retained TF replay attempted new work, private controls or original payload')
    async def forbidden_async(*args, **kwargs):
        forbidden()
    class NoDecisions:
        async def complete(self, *args, **kwargs):
            forbidden()
        async def release(self, episode_id):
            pass
    try:
        with Store(store_directory) as store:
            assert _tables(store) == proof['tables']
            assert _history(store, proof['run_id']) == proof['history']
            before_tables = _tables(store)
            before_files = dict(artifacts=_inventory(store_directory / 'artifacts'), workflow=_inventory(directory))
            monkeypatch.setattr(Store, 'artifact', forbidden)
            monkeypatch.setattr(Store, 'put', forbidden)
            monkeypatch.setattr(Store, 'commit_reasoning', forbidden)
            monkeypatch.setattr(ToolRegistry, '_source', forbidden)
            monkeypatch.setattr(ToolRegistry, '_sequence_worker_async', forbidden_async)
            monkeypatch.setattr(host, 'execute_tf_binding_tool', forbidden_async)
            monkeypatch.setattr(host, '_control', forbidden)
            monkeypatch.setattr(core, 'calculate_tf_binding_components', forbidden)
            monkeypatch.setattr(core, 'project_tf_binding_return', forbidden)
            for name in ('prepare_job', 'start', 'resume_start', 'status', 'collect', 'cancel', 'release', 'wait_job'):
                if hasattr(native_lifecycle, name): monkeypatch.setattr(native_lifecycle, name, forbidden)
            import gene_annotation_episode.tf_binding_driver as driver
            import gene_annotation_episode.tf_binding_result_worker as result_worker
            monkeypatch.setattr(driver, 'run_tf_binding_native', forbidden)
            monkeypatch.setattr(result_worker, 'run_tf_binding_result', forbidden)
            import urllib.request
            monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
            monkeypatch.setattr(urllib.request.OpenerDirector, 'open', forbidden)
            public_refs = {store.get(json.loads(row['result'])['result']['source_ref'])['artifact_ref']
                for row in proof['history']['tool_operations']}
            original_get = store.get_artifact
            def guarded_get(reference):
                assert reference in public_refs, 'retained replay opened an input, capture or private component File'
                return original_get(reference)
            monkeypatch.setattr(store, 'get_artifact', guarded_get)
            original_open, original_read = Path.open, Path.read_bytes
            def checked_path(path):
                resolved = Path(path).resolve()
                assert not resolved.is_relative_to(original_case), 'retained replay reopened the original case'
                # Owned artifact bodies are permitted only for literal public
                # packets. File metadata and Source records remain available.
                artifacts = store_directory / 'artifacts'
                if resolved.is_relative_to(artifacts):
                    assert 'artifact_' + resolved.name in public_refs
            def guarded_open(path, *args, **kwargs):
                checked_path(path)
                return original_open(path, *args, **kwargs)
            def guarded_read(path, *args, **kwargs):
                checked_path(path)
                return original_read(path, *args, **kwargs)
            with monkeypatch.context() as reads:
                reads.setattr(Path, 'open', guarded_open)
                reads.setattr(Path, 'read_bytes', guarded_read)
                workflow, tools = _assemble(store, directory, proof, NoDecisions())
                assert _tables(store) == before_tables
                root = workflow.build('annotation', 'root', QUESTION, proof['scope'])
                record = asyncio.run(root.run_async(workflow.context))
                assert _archive_value(record) == proof['archive']
                final = _archive_value(asyncio.run(root.build_result(record)))
                assert final == dict(credit=0, pending_handles=[])
                delivery, contexts = _closed_delivery(store, workflow, proof)
                audit['replay_verified'] = True
                audit['returned'] = delivery['returned']
                known_before = {context.episode_id: set(workflow.receipts.known(context.episode_id)) for context in contexts}
                audit['capabilities'] = _capabilities(store, workflow, contexts, delivery['values'],
                    proof['initial_known_record_refs'], proof['arguments'])
                assert all(set(workflow.receipts.known(context.episode_id)) == known_before[context.episode_id] for context in contexts)
                audit['literal_reads_verified'] = True
                assert _tables(store) == before_tables
                assert _history(store, proof['run_id']) == proof['history']
                audit.update(zero_new_scientific_work=True, phase='verified', final_result=final,
                    journal_table_count=len(before_tables), before_table_rows={name: len(value['rows']) for name, value in before_tables.items()},
                    after_table_rows={name: len(value['rows']) for name, value in _tables(store).items()},
                    tables_unchanged=True, history_unchanged=True)
            assert dict(artifacts=_inventory(store_directory / 'artifacts'), workflow=_inventory(directory)) == before_files
    except BaseException as error:
        audit['failure'] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        # Original files are checked only after the original-path read guard is
        # removed; no connection was ever opened against their SQLite family.
        audit['original_proof_unchanged'] = _pin(original_path) == original_proof_pin
        audit['original_sqlite_pins_unchanged'] = _sqlite_pins(proof['store_directory']) == physical_before
        audit['original_case_files_unchanged'] = _inventory(original_case) == original_before
        _write(output, audit)
        assert audit['original_proof_unchanged'] and audit['original_sqlite_pins_unchanged'] and audit['original_case_files_unchanged']


def test_tf_shared_scientific_guard_covers_actual_semantic_owners():
    from gene_annotation_episode.scientific_process_episodes import _IMPLEMENTATION_FILES
    required = {'tf_binding_result_contracts.py', 'tf_binding_measurements.py', 'tf_binding_tools.py',
        'communication.py', 'molecular_reference_privacy.py', 'episode_receipts.py'}
    assert required <= set(_IMPLEMENTATION_FILES)
    assert len(_IMPLEMENTATION_FILES) == len(set(_IMPLEMENTATION_FILES))


def _render_tf_without_work(packet, monkeypatch):
    """Engineered display control, not an actual Source or native observation."""
    from Bio.motifs.matrix import PositionSpecificScoringMatrix
    from gene_annotation_episode import scientific_process_prompt as prompt
    from gene_annotation_episode import tf_binding_driver as driver
    from gene_annotation_episode import tf_binding_result_worker as result_worker
    import builtins
    import urllib.request
    def forbidden(*args, **kwargs):
        raise AssertionError('TF display attempted I/O, scoring, calculation or publication')
    with monkeypatch.context() as guard:
        for name in ('decode_tf_binding_inputs', 'populate_tf_binding_sheet',
                'calculate_tf_binding_components', 'project_tf_binding_return'):
            guard.setattr(core, name, forbidden)
        guard.setattr(PositionSpecificScoringMatrix, 'calculate', forbidden)
        guard.setattr(driver, 'run_tf_binding_native', forbidden)
        guard.setattr(result_worker, 'run_tf_binding_result', forbidden)
        guard.setattr(Store, '__init__', forbidden)
        guard.setattr(Store, 'get_artifact', forbidden)
        guard.setattr(Store, 'artifact', forbidden)
        guard.setattr(ToolRegistry, '_source', forbidden)
        guard.setattr(Path, 'open', forbidden)
        guard.setattr(Path, 'read_bytes', forbidden)
        guard.setattr(builtins, 'open', forbidden)
        guard.setattr(urllib.request, 'urlopen', forbidden)
        for name in ('prepare_job', 'start', 'resume_start', 'status', 'collect', 'cancel', 'release', 'wait_job'):
            if hasattr(native_lifecycle, name): guard.setattr(native_lifecycle, name, forbidden)
        return prompt._values(dict(result=packet, status='completed', record_refs=[packet['source_ref']],
            changed_record_refs=[packet['source_ref']], same_fixed_result=deepcopy(packet)))


@pytest.mark.parametrize('threshold,expected_candidates', [(2., 2), (0., 4)])
def test_tf_display_uses_fixed_values_without_io_or_calculation(monkeypatch, threshold, expected_candidates):
    from test_tf_binding_measurements import engineered_sheet, selection
    sheet = engineered_sheet()
    components = core.calculate_tf_binding_components(sheet, selection(sheet, threshold))
    packet = core.project_tf_binding_return(components, 'source_' + 'c' * 24)
    before = deepcopy(packet)
    text = _render_tf_without_work(packet, monkeypatch)
    _assert_tf_display(text, packet)
    assert packet['totals']['model_eligible_candidate_sites']['value'] == expected_candidates
    assert text.count('Declared input parameters before native normalization') == 1
    assert text.count(packet['source_ref']) == 1
    assert '| - | 0 | 2 | GA | TC | 2.0 | finite |' in text
    assert '| + | 2 | 4 | TC | TC | 2.0 | finite |' in text
    assert all(row['sha256'] not in text for row in packet['inputs'])
    assert packet == before


def test_tf_display_keeps_nonfinite_counts_and_undefined_relative_meaning(monkeypatch):
    from test_tf_binding_measurements import engineered_sheet, selection
    sheet = engineered_sheet(dna=b'ANC', counts=dict(A=[1], C=[0], G=[0], T=[0]),
        pwm=[[1], [0], [0], [0]], pssm=[[2], [-float('inf')], [-float('inf')], [-float('inf')]],
        rc=[[-float('inf')], [-float('inf')], [-float('inf')], [2]],
        background=dict.fromkeys('ACGT', .25), bounds=(-float('inf'), 2),
        scores={'+': [2, float('nan'), -float('inf')]}, strands=('+',))
    packet = core.project_tf_binding_return(core.calculate_tf_binding_components(sheet, selection(sheet)),
        'source_' + 'd' * 24)
    before = deepcopy(packet)
    text = _render_tf_without_work(packet, monkeypatch)
    _assert_tf_display(text, packet)
    assert '| nan scores | 1 | available | count |' in text
    assert '| negative infinity scores | 1 | available | count |' in text
    assert '| scientific_state | undefined |' in text
    assert '| reason_code | nonfinite_relative_bounds |' in text
    assert '| minimum | null | negative_infinity | available | bits |' in text
    assert 'undefined' in text and 'nonfinite_relative_bounds' in text
    assert packet == before


@pytest.mark.parametrize('fault', ['version', 'parameters'])
def test_tf_display_requires_exact_validated_packet(monkeypatch, fault):
    from test_tf_binding_measurements import engineered_sheet, selection
    sheet = engineered_sheet()
    packet = core.project_tf_binding_return(core.calculate_tf_binding_components(sheet, selection(sheet)),
        'source_' + 'e' * 24)
    if fault == 'version': packet['version'] = 'tf_binding_return_v999'
    else: packet['parameters']['background']['A'] = -1
    before = deepcopy(packet)
    text = _render_tf_without_work(packet, monkeypatch)
    assert 'Declared input parameters before native normalization' not in text
    assert 'Raw log2-odds threshold' not in text
    assert packet['source_ref'] in text
    assert packet == before


def _engineered_tf_form():
    from test_tf_binding_measurements import engineered_sheet, selection
    sheet = engineered_sheet()
    returned = core.project_tf_binding_return(core.calculate_tf_binding_components(sheet, selection(sheet)),
        'source_' + 'c' * 24)
    # Deliberately identifier-shaped opaque metadata. It is not another grant.
    returned['inputs'][0]['upstream_source_id'] = 'source_' + 'f' * 24
    return _form(), dict(sites=[returned])


def _validate_tf_form_without_work(schema, payload, resolver, monkeypatch, *, compile_only=False):
    from Bio.motifs.matrix import PositionSpecificScoringMatrix
    from gene_annotation_episode import communication
    from gene_annotation_episode import tf_binding_driver as driver
    from gene_annotation_episode import tf_binding_result_worker as result_worker
    import builtins
    import urllib.request
    def forbidden(*args, **kwargs):
        raise AssertionError('TF form validation attempted I/O, scoring, calculation or publication')
    with monkeypatch.context() as guard:
        for name in ('decode_tf_binding_inputs', 'populate_tf_binding_sheet',
                'calculate_tf_binding_components', 'project_tf_binding_return'):
            guard.setattr(core, name, forbidden)
        guard.setattr(PositionSpecificScoringMatrix, 'calculate', forbidden)
        guard.setattr(driver, 'run_tf_binding_native', forbidden)
        guard.setattr(result_worker, 'run_tf_binding_result', forbidden)
        guard.setattr(Store, '__init__', forbidden)
        guard.setattr(Store, 'get_artifact', forbidden)
        guard.setattr(Store, 'artifact', forbidden)
        guard.setattr(ToolRegistry, '_source', forbidden)
        guard.setattr(Path, 'open', forbidden)
        guard.setattr(Path, 'read_bytes', forbidden)
        guard.setattr(builtins, 'open', forbidden)
        guard.setattr(urllib.request, 'urlopen', forbidden)
        guard.setattr(urllib.request.OpenerDirector, 'open', forbidden)
        if compile_only:
            return communication.validate_closed_schema(schema)
        return communication.validate_form(payload, schema, resolver)


def test_tf_registered_form_compiles_without_work(monkeypatch):
    schema = _form()
    before = deepcopy(schema)
    compiled = _validate_tf_form_without_work(schema, None, None, monkeypatch, compile_only=True)
    assert compiled == before and schema == before


def test_tf_form_resolves_only_top_source_and_keeps_input_ids_opaque(monkeypatch):
    schema, payload = _engineered_tf_form()
    before = deepcopy((schema, payload))
    returned = payload['sites'][0]
    seen = []
    def resolver(reference, namespace):
        seen.append((reference, namespace))
        return reference == returned['source_ref'] and namespace == 'source'
    admitted = _validate_tf_form_without_work(schema, payload, resolver, monkeypatch)
    assert admitted == payload
    assert seen == [(returned['source_ref'], 'source')]
    assert returned['inputs'][0]['artifact_id'].startswith('artifact_')
    assert returned['inputs'][0]['upstream_source_id'] == 'source_' + 'f' * 24
    assert (schema, payload) == before


@pytest.mark.parametrize('fault', ['modified', 'widened', 'nested', 'unregistered'])
def test_tf_form_rejects_changed_or_nested_registered_contract(monkeypatch, fault):
    from gene_annotation_episode.communication import ReportBoundaryError
    schema = _form()
    field = schema['properties']['sites']
    if fault == 'modified': field['description'] = field.get('description', '') + ' changed'
    elif fault == 'widened': field['$defs']['Return']['additionalProperties'] = True
    elif fault == 'nested': schema = obj(dict(wrapper=obj(dict(sites=field))))
    else: del field['x-source']
    before = deepcopy(schema)
    with pytest.raises(ReportBoundaryError) as error:
        _validate_tf_form_without_work(schema, None, None, monkeypatch, compile_only=True)
    assert error.value.diagnostic['code'] == 'invalid_schema'
    assert schema == before


@pytest.mark.parametrize('fault', ['negative_parameter', 'crossfield_count', 'score_bits', 'float_integer'])
def test_tf_form_rejects_invalid_parameters_and_crossfield_values(monkeypatch, fault):
    from gene_annotation_episode.communication import ReportBoundaryError
    schema, payload = _engineered_tf_form()
    value = payload['sites'][0]
    if fault == 'negative_parameter': value['parameters']['background']['A'] = -1
    elif fault == 'crossfield_count': value['totals']['returned_candidate_rows']['value'] = 0
    elif fault == 'score_bits': value['raw_threshold_matches'][0]['score']['bits_hex'] = '00000000'
    else: value['inputs'][0]['size_bytes'] = float(value['inputs'][0]['size_bytes'])
    before = deepcopy((schema, payload))
    seen = []
    with pytest.raises(ReportBoundaryError) as error:
        _validate_tf_form_without_work(schema, payload, lambda *args: seen.append(args) or True, monkeypatch)
    assert error.value.diagnostic['field'] == 'sites'
    assert seen == [] and (schema, payload) == before


def test_tf_form_revalidates_source_permission_after_cached_schema(monkeypatch):
    from gene_annotation_episode.communication import ReportBoundaryError
    schema, payload = _engineered_tf_form()
    source = payload['sites'][0]['source_ref']
    assert _validate_tf_form_without_work(schema, payload, lambda ref, ns: (ref, ns) == (source, 'source'), monkeypatch) == payload
    seen = []
    with pytest.raises(ReportBoundaryError) as error:
        _validate_tf_form_without_work(schema, payload, lambda *args: seen.append(args) or False, monkeypatch)
    assert seen == [(source, 'source')]
    assert error.value.diagnostic == dict(category='report_format', code='unknown_reference', field='report.sites[0].source_ref')


def test_tf_registration_does_not_widen_generic_string_forms(monkeypatch):
    from gene_annotation_episode.communication import ReportBoundaryError
    with pytest.raises(ReportBoundaryError) as error:
        _validate_tf_form_without_work(obj(dict(unrestricted=dict(type='string'))), None, None,
            monkeypatch, compile_only=True)
    assert error.value.diagnostic['code'] == 'unrestricted_string'
