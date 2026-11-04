"""Retained p3-sra bytes through actual host and both typed receiving guards.

Task/Workspace/transport responses and selections are controlled. The host,
parser, sheets, records, completion proof and return guards are frozen211 code.
This test deliberately does not run method_loop or any scientific producer.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import uuid

import pytest

import test_bvbrc_fastqutils_episode_flow as host_fixture
from gene_annotation_episode import bvbrc_fastqutils_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_appservice_custody import AppServiceCustodyError
from gene_annotation_episode.bvbrc_fastqutils_contracts import validate_parameters, validate_requested_form
from gene_annotation_episode.bvbrc_fastqutils_identity import decode_reference
from gene_annotation_episode.bvbrc_fastqutils_returns import decode_return_value
from gene_annotation_episode.bvbrc_fastqutils_sra_specs import SRA_FIELDS
from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.state import Store

HERE = Path(__file__).resolve().parent
NATIVE = HERE / 'native_inputs/native_selected_run.json'
PIN = '7cfda476553dda5ee3afd317969b277a2f9973a034e1f230b65706d16285b0e7'
EXPECTED = dict(total_bases=2673129532, total_spots=35172757, size=937094000,
                read_length=76.0, n_reads=1)
NAMES = ('sra',)
OUTPUTS = {'sra': ('/fixture/output/SRR6263255.json', str(uuid.uuid5(
    uuid.NAMESPACE_URL, 'controlled-sra-host215:SRR6263255')))}


def save(name, value):
    directory = Path(os.environ['SRA_HOST_EVIDENCE'])
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (name + '.json')
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    return path


def action_rows(store):
    return [dict(row) for row in store.db.execute(
        'SELECT * FROM runtime_actions ORDER BY run_id,episode_id,decision_index')]


def declarations():
    fields = []
    for name, (metric, _, _, _) in SRA_FIELDS.items():
        fields.append(dict(field=name, selection=dict(target=dict(kind='measurement', selector=dict(
            selection='semantic', document_id='sra', section_key='sra_run', section_ordinal=0,
            metric=metric, rows=dict(kind='ordinal', ordinal=0),
            axis=dict(kind='exact', axis=dict(kind='none', label=None, lower=None, upper=None)))),
            cardinality='one_target', expected_cardinality=1, availability_requirement='available_value')))
    fields.append(dict(field='requirements', selection=dict(target=dict(kind='requirements'),
        cardinality='one_target', expected_cardinality=1, availability_requirement='typed_state')))
    selected_form = dict(version='fastqutils_projection_v2', fields=fields)
    params = validate_parameters(dict(version='fastqutils_provider_v2', analysis_id='sraHost215',
        documents=[dict(document_id='sra', selection=dict(kind='output_requirement', requirement_id='selected_sra'),
                        format='sra_metadata', producer_version=None)],
        metadata_bindings=[], calculation_requests=[]))
    return dict(parameters=params, requested_form=selected_form,
        declarations=dict(declarations=[]), submitted_parameters=dict(
            paired_end_libs=[], single_end_libs=[], srr_libs=[dict(srr_accession='SRR6263255')],
            recipe=['FASTQC'], output_path='/fixture/output', output_file='selected'))


def assert_values(typed):
    values = host_fixture.native_values(typed)
    assert set(values) == {*EXPECTED, 'requirements'}
    for name, expected in EXPECTED.items():
        selected = values[name]
        assert selected['state'] == 'satisfied' and selected['satisfied']
        assert selected['selection']['target']['selector']['rows'] == dict(kind='ordinal', ordinal=0)
        assert len(selected['records']) == selected['matched_count'] == 1
        row = selected['records'][0]
        payload = row['payload']
        assert payload['value'] == expected
        assert type(payload['value']) is type(expected)
        assert payload['quantity'] == SRA_FIELDS[name][0] and payload['unit'] == SRA_FIELDS[name][1]
        assert payload['meaning'] == 'observed_native' and payload['precision'] == 'not_reported'
        assert payload['association_ref'] is None
        assert row['source_refs']
    assert 'sra_read_types_basis_unproven' in values['n_reads']['records'][0]['diagnostic_codes']
    assert 'sra_read_length_basis_unproven' in values['read_length']['records'][0]['diagnostic_codes']
    requirements = values['requirements']['records'][0]['payload']['requirements']
    assert 'producer_version_unproven' in {row['code'] for row in requirements}
    rows = [row for items in typed.values() for row in items
            if row['value']['selection']['target']['kind'] == 'measurement']
    assert [decode_reference(row['field'])['pointer'].removeprefix('/facts/') for row in rows] == list(EXPECTED)
    assert [decode_return_value('measurement', row['value'])['records'][0]['payload']['value']
            for row in rows] == list(EXPECTED.values())
    return values


def checkpoint(driver, directory, body, phase):
    values = {name: deepcopy(getattr(driver, name)) for name in (
        'config', 'schema', 'selected', 'frozen_assignment', 'material', 'declarations',
        'query', 'handoff', 'manifest', 'native_args', 'last_outcome')}
    values.update(version='sra_host215_checkpoint_v1', directory=str(directory),
        state_path=str(driver.store.path), run_id=driver.saved.run_id, phase=phase,
        episode_ids={name: getattr(driver, name).episode_id for name in ('parent', 'grandparent', 'context', 'launch')},
        body=body, sheet=driver.sheet, components=driver.components, calls=driver.client.calls,
        actions=action_rows(driver.store))
    return save('acquired_checkpoint', values)


def reconstruct(store, saved):
    """Reopen production bindings from durable records without fixture startup."""
    d = host_fixture.FastqDriver.__new__(host_fixture.FastqDriver)
    d.store, d.config = store, deepcopy(saved['config'])
    d.saved = SimpleNamespace(run_id=saved['run_id'], journal=Journal(store, saved['run_id']),
                              receipts=EpisodeReceipts(store, saved['run_id']))
    d.family = ExecutionEpisodes(None, store=store, directory=Path(saved['directory']),
        run_id=saved['run_id'], resources={'selected-api': d.config}, initial_information={},
        tool_registry=SimpleNamespace(store=store, clients={}), handoff_unit=2, acquired_record_unit=3,
        log_window_bytes=1024, log_roles=('stdout', 'stderr'))
    d.api, d.client = d.family.api_execution, host_fixture.ControlledClient()
    d.service = d.api.services['selected-api']
    d.service.client = d.client
    d.records, d.custody = d.api.appservice.records, d.api.appservice.custody
    for name, ident in saved['episode_ids'].items():
        setattr(d, name, d.custody.context(ident))
    d.saved.root = d.parent
    for name in ('schema', 'selected', 'frozen_assignment', 'material', 'declarations',
                 'query', 'handoff', 'manifest', 'native_args', 'last_outcome'):
        setattr(d, name, deepcopy(saved[name]))
    return d


def disable_reexecution(monkeypatch):
    attempts, patched = [], []
    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError('saved host verification attempted science, acquisition, network or subprocess')

    for suffix in ('bundle_adapter', 'native', 'sra_native', 'trim_reader', 'cutadapt_reader', 'fastq_reader',
                   'sam_reader', 'bam_reader', 'fastqc_reader', 'pair_report_reader', 'hostile_reader',
                   'metadata', 'sheet', 'calculators', 'retention', 'composition', 'quality', 'mapping', 'consistency'):
        module = importlib.import_module('gene_annotation_episode.bvbrc_fastqutils_' + suffix)
        for name, function in list(vars(module).items()):
            if callable(function) and (name.startswith(('parse_', 'populate_', 'extract_', 'calculate_'))
                                       or name in ('append_cutadapt_report', 'consume_bundle')):
                monkeypatch.setattr(module, name, forbidden)
                patched.append(module.__name__ + '.' + name)
    monkeypatch.setattr(adapter.FastqUtilsBundleAdapter, 'consume_bundle', forbidden)
    patched.append(adapter.__name__ + '.FastqUtilsBundleAdapter.consume_bundle')
    for target in ('gene_annotation_episode.bvbrc_appservice_publication.AppServicePublications._grade',
        'gene_annotation_episode.api_service_execution.APIServiceExecution.execute',
        'socket.create_connection', 'socket.socket.connect', 'socket.socket.connect_ex',
        'urllib.request.OpenerDirector.open', 'subprocess.Popen'):
        monkeypatch.setattr(target, forbidden)
        patched.append(target)
    for cls in (host_fixture.ControlledClient, host_fixture.NativeClient):
        for name in ('rpc', 'task_info', 'download', 'upload'):
            monkeypatch.setattr(cls, name, forbidden)
            patched.append(cls.__module__ + '.' + cls.__name__ + '.' + name)
    return attempts, patched


def test_retained_sra_actual_host_two_returns_saved_reconstruction_and_forgery(tmp_path, monkeypatch):
    def no_external(*args, **kwargs):
        raise AssertionError('controlled SRA verification attempted live transport or subprocess')
    for name in ('socket.create_connection', 'socket.socket.connect', 'urllib.request.OpenerDirector.open', 'subprocess.Popen'):
        monkeypatch.setattr(name, no_external)
    fixture_map, native = declarations(), NATIVE.read_bytes()
    assert set(SRA_FIELDS) == set(EXPECTED)
    monkeypatch.setattr(host_fixture, 'fixture', lambda name: deepcopy(fixture_map[name]))
    monkeypatch.setattr(host_fixture, 'raw', lambda name: native)
    monkeypatch.setattr(host_fixture, 'NAMES', NAMES)
    monkeypatch.setattr(host_fixture, 'OUTPUTS', OUTPUTS)
    save('fixture_declarations', dict(fixtures=fixture_map, workspace_outputs=OUTPUTS,
        native_file=str(NATIVE), native_sha256=hashlib.sha256(native).hexdigest(), native_byte_count=len(native),
        provider_envelope_injected=False, original_native_source='211 retained p3-sra output on retained NCBI metadata',
        qualification='Controlled FastqUtils task/Workspace responses; actual host and retained native JSON bytes.'))
    resume = os.environ.get('SRA_HOST_RESUME_CHECKPOINT')
    if resume:
        saved = json.loads(Path(resume).read_text())
        save('resumed_checkpoint', dict(path=resume, sha256=hashlib.sha256(Path(resume).read_bytes()).hexdigest()))
    else:
        with Store(tmp_path / 'state') as store:
            d = host_fixture.FastqDriver(store, tmp_path)
            assert list(d.saved.receipts.known(d.saved.root.episode_id)) == []
            assert store.db.execute('SELECT COUNT(*) FROM runtime_record_receipts').fetchone()[0] == 0
            assert adapter.implementation_sha256() == PIN
            d.start(documents=NAMES)
            # Persist original selection/custody before requesting native output.
            parse = dict(d.saved.journal.row('runtime_actions', d.parent.episode_id, 1))
            parsed = json.loads(parse['result'])
            save('original_selection_and_custody', dict(initial_known_record_refs=[], initial_receipt_count=0,
                material=d.material, declarations=d.declarations, parse_action=parse, parsed=parsed,
                assignment=d.frozen_assignment, submission=d.handoff, schema=d.schema,
                custody=d.custody.possession(d.parent, d.declarations['source_ref'])))
            d.acquire_manifest()
            assert d.api._completion(d.context) is None
            body = d.acquire_native('sra')
            path = checkpoint(d, tmp_path, body, 'scientific_acquisition_complete_before_assertions')
            saved = json.loads(path.read_text())

    # Reconstruct after closing the Store, with every execution path disabled.
    attempts, patched = disable_reexecution(monkeypatch)
    save('disabled_entrypoints', patched)
    with Store(saved['state_path']) as store:
        d = reconstruct(store, saved)
        assert d.client.calls == []
        assert adapter.implementation_sha256() == PIN
        body = d.api.read_result(saved['body']['source_ref'], d.context.scope)
        assert body == saved['body']
        d.sheet = d.api.appservice.publications.read_content_source(
            body['publication']['adapter_result']['sheet_content']['source_ref'], d.context.scope)
        d.components = d.api.appservice.publications.read_content_source(
            body['publication']['adapter_result']['components_content']['source_ref'], d.context.scope)
        assert d.sheet == saved['sheet'] and d.components == saved['components']
        assert action_rows(store) == saved['actions']
        assert d.selected['adapter']['parameters'] == fixture_map['parameters']
        assert validate_requested_form(d.selected['requested_schema']) == fixture_map['requested_form']
        submitted = fixture_map['submitted_parameters']
        assert d.handoff['value']['original_task']['submitted_parameters'] == submitted
        assert d.handoff['value']['original_task']['required_application_id'] == 'FastqUtils'
        assert d.service.scientific_adapters[(adapter.ADAPTER_ID, adapter.ADAPTER_VERSION)][0] is adapter
        submit_calls = [call for call in saved['calls'] if call[0] == 'rpc'
                        and call[1]['method'] == 'AppService.start_app2']
        assert len(submit_calls) == 1 and submit_calls[0][1]['params'] == ['FastqUtils', submitted, {}]
        parse = d.saved.journal.row('runtime_actions', d.parent.episode_id, 1)
        parsed = json.loads(parse['result'])
        assert json.loads(parse['action'])['tool'] == 'material.parse'
        attempt = parsed['result']['parse_attempt']
        assert (attempt['status'], attempt['code'], attempt['source_ref']) == (
            'completed', 'retained_without_sequence_projection', d.declarations['source_ref'])
        assert store.get(d.declarations['source_ref'])['origin'] == 'caller'
        assert store.get_artifact(d.declarations['artifact_ref']) == canonical({'declarations': []}).encode()
        assert d.custody.possession(d.parent, d.declarations['source_ref']) == 'own_completed_action'
        with pytest.raises(AppServiceCustodyError, match='input_not_possessed'):
            d.custody.possession(d.parent, d.declarations['source_ref'], before=1)
        assert plain(d.context.assignment) == d.frozen_assignment
        assert body['publication_inputs']['selector'] == d.selected
        assert body['publication_inputs']['adapter_implementation_sha256'] == PIN
        assert body['bundle']['original_task'] == d.handoff['value']['original_task']
        member, = body['bundle']['artifacts']
        assert member['role'] == 'sra' and member['requirement_ids'] == ['selected_sra']
        assert member['task_association']['task_id'] == '123'
        assert member['workspace_object']['path'] == member['task_association']['output_path'] == OUTPUTS['sra'][0]
        assert member['workspace_object']['uuid'] == member['task_association']['output_uuid'] == OUTPUTS['sra'][1]
        assert member['task_association']['kind'] == 'task_result_manifest'
        assert member['task_association']['pointer'] == '/output_files/0'
        assert store.get_artifact(member['raw_artifact_ref']) == native
        assert member['sha256'] == hashlib.sha256(native).hexdigest() and member['byte_count'] == len(native)
        assert d.custody.possession(d.context, member['source_ref']) == 'own_completed_action'
        assert member['source_ref'] != 'source_sra'
        doc, = d.sheet['documents']
        assert doc['artifact']['content_binding']['source_ref'] == member['source_ref']
        assert doc['artifact']['content_binding']['artifact_ref'] == member['raw_artifact_ref']
        assert doc['artifact']['producer_version'] is None and doc['artifact']['identity'] == 'unknown'
        assert doc['parse_scope'] == 'complete'
        assert all(row['association_ref'] is None for row in d.sheet['measurements'] + d.sheet['populations'])
        assert not d.sheet['associations'] and not d.sheet['native_lineage'] and not d.sheet['supplied_metadata']
        library, = d.sheet['libraries']
        assert library['input_pointer'] == '/srr_libs/0' and library['submitted_value'] == submitted['srr_libs'][0]
        assert all(library[key] is None for key in ('sample_ref', 'condition_ref', 'replicate_ref', 'platform'))
        assert not library['metadata_ids']
        assert all(row['scope'] == 'unknown' for row in d.sheet['populations'])
        assert all(row['observed_state'] == 'unknown' for row in d.sheet['stages'])
        assert [row['requested_token'] for row in d.sheet['stages']] == ['FASTQC']
        assert not d.components['calculations']['components']
        native_rows = json.loads(native)
        expected_labels = [(ordinal, key + '/' + str(i), item) if isinstance(value, list) else (ordinal, key, value)
            for ordinal, original in enumerate(native_rows) for key, value in original.items() if key not in SRA_FIELDS
            for i, item in (enumerate(value) if isinstance(value, list) else [(None, None)])]
        assert [(row['section_ordinal'], row['locator']['field'], row['value']) for row in doc['labels']] == expected_labels
        assert len(doc['populations']) == len(doc['sections']) == len(native_rows) == 1
        assert {row['code'] for row in doc['diagnostics']} >= {
            'producer_version_unproven', 'sra_metadata_basis_unproven',
            'sra_read_length_basis_unproven', 'sra_read_types_basis_unproven',
            'sra_cross_reference_association_unproven'}
        for cell in doc['cells']:
            loc = cell['locator']
            assert cell['section_ordinal'] == loc['row_ordinal'] == 0
            assert native[loc['byte_start']:loc['byte_end']].decode() == cell['native_token']
        proof = d.api._completion(d.context)
        assert body['publication']['requested_form_status'] == 'satisfied'
        assert proof is not None and d.api.verify_completion(d.context, proof)
        assert proof['assignment_sha256'] == digest(d.frozen_assignment)
        assert proof['endpoint'] == 'completed_job_outputs'
        assert proof['validation_keys'] == ['requested_service_result']
        save('final_publication', body)
        save('sheet', d.sheet)
        save('components', d.components)
        save('native_labels_and_unknown_associations', dict(labels=doc['labels'], populations=d.sheet['populations'],
            libraries=d.sheet['libraries'], associations=d.sheet['associations'], diagnostics=doc['diagnostics']))

        actions_before = action_rows(store)
        typed, key, refs = d.admit_numeric()
        forwarded, forwarded_key, forwarded_refs = d.admit_numeric(to_grandparent=True)
        assert typed == forwarded and refs == forwarded_refs
        values = assert_values(forwarded)
        assert_values(typed)
        validate_form(forwarded, d.schema, lambda ref, namespace=None: d.family.resolve(d.parent, ref, namespace))
        assert set(d.family.received_report_facts(d.grandparent)) == {
            'bvbrc_fastqutils_measurements', 'bvbrc_fastqutils_requirements'}
        for context in (d.parent, d.grandparent):
            assert d.custody.possession(context, body['source_ref']) == 'admitted_return'
        assert action_rows(store) == actions_before
        save('typed_returns', dict(schema=d.schema, result_to_parent=typed, parent_to_grandparent=forwarded,
            parent_references=refs, grandparent_references=forwarded_refs, decoded=values))
        retained = canonical([body, d.sheet, d.components, typed, forwarded])
        facts_before = deepcopy(d.family.received_report_facts(d.grandparent))
        replayed, replay_key, replay_refs = d.admit_numeric()
        reforwarded, refwd_key, refwd_refs = d.admit_numeric(to_grandparent=True)
        assert (replayed, replay_key, replay_refs) == (typed, key, refs)
        assert (reforwarded, refwd_key, refwd_refs) == (forwarded, forwarded_key, forwarded_refs)
        assert d.family.received_report_facts(d.grandparent) == facts_before
        assert canonical([body, d.sheet, d.components, typed, forwarded]) == retained
        assert not attempts and d.client.calls == [] and action_rows(store) == actions_before
        assert store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0
        assert d.api._completion(d.context) == proof
        forged = deepcopy(typed)
        forged['facts_0'][0]['value']['records'][0]['payload']['value'] = 900
        rejections = []
        for label, context in (('owning_results_provider', d.context),
            ('child_to_parent_receiver', d.parent), ('parent_to_grandparent_receiver', d.grandparent)):
            with pytest.raises(ValueError) as error:
                d.family.validate_received_report(context, forged, d.schema)
            rejections.append(dict(boundary=label, role=context.role, episode_id=context.episode_id, code=str(error.value)))
        assert not attempts and action_rows(store) == actions_before
        assert d.family.received_report_facts(d.grandparent) == facts_before
        save('saved_replay_and_forgery', dict(disabled_callables=patched, forbidden_attempts=attempts,
            reconstruction_from_closed_store=True, result_to_parent=replayed, parent_to_grandparent=reforwarded,
            source_references_before=refs, source_references_after=replay_refs,
            action_rows_sha256_before=digest(actions_before), action_rows_sha256_after=digest(action_rows(store)),
            forged_measurement=900, rejections=rejections, practical_completion_proof=proof,
            selected_actions_before=len(actions_before), selected_actions_after=len(action_rows(store)),
            runtime_observations=0, controlled_transport_calls_after_reconstruction=d.client.calls))
        save('selected_actions', actions_before)
        save('controlled_transport_calls', saved['calls'])
        modules = []
        for name, module in sorted(sys.modules.items()):
            filename = getattr(module, '__file__', None)
            if filename is None or not Path(filename).is_file():
                continue
            path = Path(filename).resolve()
            if name.split('.', 1)[0] in ('gene_annotation_episode', 'method_loop'):
                assert path.is_relative_to(HERE / 'candidate'), (name, path)
            modules.append(dict(module=name, path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        save('actual_import_origins', modules)
        categories = Counter(json.loads(row['action'])['kind'] for row in actions_before)
        completed = [row for row in actions_before if row['result'] is not None]
        summary = dict(passed=True, provider_pin=PIN, native_sha256=hashlib.sha256(native).hexdigest(),
            numerical_values=EXPECTED, requested_fields=[*EXPECTED, 'requirements'], row_labels_retained=len(doc['labels']),
            associations_invented=0, typed_boundary_count=2, forged_value_rejection_count=len(rejections),
            saved_reconstruction=True, saved_repeated_returns=2, forbidden_call_attempts=0,
            selected_action_count=len(actions_before), selected_action_categories=dict(categories),
            completed_own_tool_action_count=len(completed), runtime_observation_count=0,
            initial_known_record_refs=[], material_custody='real_selected_material.parse',
            actual_host_objects=True, actual_retained_native_bytes=True, controlled_task_and_transport=True,
            practical_output_completion_verified=True, controller_execution_verified=False,
            native_producers_executed=0, method_loop_run=False, configured_model_run=False,
            live_bvbrc_run=False, live_sra_acquisition=False, whole_tool_complete=False, production_changes=False)
        save('verified_summary', summary)
        print(json.dumps(summary, sort_keys=True))
