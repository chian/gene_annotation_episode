"""Retained native producer bytes through controlled actual host and returns.

The task, Workspace identities and transport are explicit fixtures. The host,
native readers, numerical calculators, saved records and both return guards
are the frozen production implementations. This does not run method_loop.
"""
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import uuid

import pytest

import test_bvbrc_fastqutils_episode_flow as host_fixture
import test_bvbrc_fastqutils_cutadapt_provider as native_fixture
from gene_annotation_episode import bvbrc_fastqutils_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_fastqutils_contracts import validate_requested_form
from gene_annotation_episode.bvbrc_appservice_custody import AppServiceCustodyError
from gene_annotation_episode.bvbrc_fastqutils_identity import decode_reference
from gene_annotation_episode.bvbrc_fastqutils_returns import decode_return_value
from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.state import Store

HERE = Path(__file__).resolve().parent
NATIVE = HERE / 'native_inputs'
PIN = '20adf5d29462216bca37f8bcf23c573aacca8b4eb6f10bb9cabed25ec8f654dd'
NAMES = ('trim', 'final')
FILES = {'trim': 'synthetic.fastq_trimming_report.txt', 'final': 'synthetic_trimmed.fq'}
EXPECTED_NAMES = ('cutadapt_input_reads', 'cutadapt_output_reads', 'cutadapt_output_bases',
                  'trimgalore_input_reads', 'final_reads', 'final_bases',
                  'cutadapt_base_retention', 'requirements')
EXPECTED_MEASUREMENTS = [4, 4, 28, 4, 3, 24]


def save(name, value):
    destination = Path(os.environ['CUTADAPT_HOST_EVIDENCE'])
    destination.mkdir(parents=True, exist_ok=True)
    with (destination / (name + '.json')).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def action_rows(store):
    return [dict(row) for row in store.db.execute(
        'SELECT * FROM runtime_actions ORDER BY run_id,episode_id,decision_index')]


def sources(store):
    return [dict(row) for row in store.db.execute(
        "SELECT * FROM records WHERE record_type='source' ORDER BY id")]


def assert_values(typed):
    values = host_fixture.native_values(typed)
    assert set(values) == set(EXPECTED_NAMES)
    assert [values[name]['records'][0]['payload']['value']
            for name in EXPECTED_NAMES[:6]] == EXPECTED_MEASUREMENTS
    component = values['cutadapt_base_retention']['records'][0]['payload']
    assert component['value'] == 28 / 58
    assert (component['numerator'], component['denominator']) == (28, 58)
    assert component['lineage_basis']['basis'] == 'native_report'
    assert values['requirements']['selection']['target']['kind'] == 'requirements'
    requirements = values['requirements']['records'][0]['payload']['requirements']
    assert {'stage_execution_unknown', 'producer_version_unproven', 'unknown_quality_encoding'} <= {
        row['code'] for row in requirements}
    measurement_rows = [row for rows in typed.values() for row in rows
                        if row['value']['selection']['target']['kind'] == 'measurement']
    assert [decode_reference(row['field'])['pointer'].removeprefix('/facts/')
            for row in measurement_rows] == list(EXPECTED_NAMES[:6])
    assert [decode_return_value('measurement', row['value'])['records'][0]['payload']['value']
            for row in measurement_rows] == EXPECTED_MEASUREMENTS
    return values


def disable_reexecution(monkeypatch, driver):
    attempts, patched = [], []

    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError('Saved host return attempted acquisition, parsing, metadata extraction or calculation')

    for suffix in ('bundle_adapter', 'native', 'trim_reader', 'cutadapt_reader', 'fastq_reader',
                   'sam_reader', 'bam_reader', 'fastqc_reader', 'pair_report_reader', 'hostile_reader',
                   'metadata', 'sheet', 'calculators', 'retention', 'composition', 'quality',
                   'mapping', 'consistency'):
        module = importlib.import_module('gene_annotation_episode.bvbrc_fastqutils_' + suffix)
        for name, function in list(vars(module).items()):
            if callable(function) and (name.startswith(('parse_', 'populate_', 'extract_', 'calculate_'))
                                       or name in ('append_cutadapt_report', 'consume_bundle')):
                monkeypatch.setattr(module, name, forbidden)
                patched.append(module.__name__ + '.' + name)
    monkeypatch.setattr(adapter.FastqUtilsBundleAdapter, 'consume_bundle', forbidden)
    patched.append(adapter.__name__ + '.FastqUtilsBundleAdapter.consume_bundle')
    for name in ('rpc', 'task_info', 'download', 'upload'):
        monkeypatch.setattr(driver.client, name, forbidden)
        patched.append('controlled_transport.' + name)
    for name in ('socket.create_connection', 'socket.socket.connect', 'urllib.request.OpenerDirector.open',
                 'subprocess.Popen'):
        monkeypatch.setattr(name, forbidden)
        patched.append(name)
    return attempts, patched


def test_retained_trimgalore_cutadapt_bytes_actual_host_two_returns_and_saved_replay(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError('Controlled host verification attempted live transport')

    for name in ('socket.create_connection', 'socket.socket.connect', 'urllib.request.OpenerDirector.open'):
        monkeypatch.setattr(name, no_network)
    # Reuse precisely the original 204 parameters/form. Its handcrafted bundle
    # is used only as a fixture declaration source and is never sent to the host.
    monkeypatch.setattr(native_fixture, 'NATIVE', NATIVE)
    data, fields = native_fixture.fixture()
    assert tuple(fields) == EXPECTED_NAMES
    params = deepcopy(data[3])
    assert params['metadata_bindings'] == []
    assert [row['selection'] for row in params['documents']] == [
        {'kind': 'output_requirement', 'requirement_id': 'selected_trim'},
        {'kind': 'output_requirement', 'requirement_id': 'selected_final'}]
    selected_form = validate_requested_form(native_fixture.f.schema(fields))
    fixture_map = {'parameters': params, 'requested_form': selected_form,
                   'declarations': {'declarations': []},
                   'submitted_parameters': deepcopy(data[0]['original_task']['submitted_parameters'])}
    submitted = fixture_map['submitted_parameters']
    assert submitted['recipe'] == ['TRIM']
    assert submitted['paired_end_libs'] == submitted['srr_libs'] == []
    assert submitted['single_end_libs'] == [{'read': '/synthetic/input.fastq'}]
    output_objects = {name: ('/fixture/output/' + FILES[name], str(uuid.uuid5(
        uuid.NAMESPACE_URL, 'controlled-cutadapt-host209:' + name))) for name in NAMES}
    native_bytes = {name: (NATIVE / FILES[name]).read_bytes() for name in NAMES}
    monkeypatch.setattr(host_fixture, 'fixture', lambda name: deepcopy(fixture_map[name]))
    monkeypatch.setattr(host_fixture, 'raw', lambda name: native_bytes[name])
    monkeypatch.setattr(host_fixture, 'NAMES', NAMES)
    monkeypatch.setattr(host_fixture, 'OUTPUTS', output_objects)
    save('fixture_declarations', dict(fixtures=fixture_map, requested_fields=fields,
        workspace_outputs=output_objects,
        native_inputs={name: dict(file=FILES[name], sha256=hashlib.sha256(raw).hexdigest(), byte_count=len(raw))
                       for name, raw in native_bytes.items()},
        original_provider_bundle_injected=False,
        qualification='Actual retained local native output on synthetic reads; controlled task and Workspace transport.'))

    with Store(tmp_path / 'state') as store:
        d = host_fixture.FastqDriver(store, tmp_path)
        assert d.saved.receipts.known(d.saved.root.episode_id) == []
        initial_receipts = store.db.execute('SELECT COUNT(*) FROM runtime_record_receipts').fetchone()[0]
        assert initial_receipts == 0
        assert adapter.implementation_sha256() == PIN
        d.start(documents=('trim', 'final'))
        assert d.selected['adapter']['parameters'] == params
        assert validate_requested_form(d.selected['requested_schema']) == selected_form
        assert d.handoff['value']['original_task']['submitted_parameters'] == submitted
        assert d.service.scientific_adapters[(adapter.ADAPTER_ID, adapter.ADAPTER_VERSION)][0] is adapter
        parse = d.saved.journal.row('runtime_actions', d.parent.episode_id, 1)
        parsed = json.loads(parse['result'])
        assert json.loads(parse['action'])['tool'] == 'material.parse'
        assert parsed['status'] == 'completed' and d.declarations['source_ref'] in parsed['record_refs']
        attempt = parsed['result']['parse_attempt']
        assert (attempt['status'], attempt['code'], attempt['source_ref']) == (
            'completed', 'retained_without_sequence_projection', d.declarations['source_ref'])
        assert store.get(d.declarations['source_ref'])['origin'] == 'caller'
        assert store.get_artifact(d.declarations['artifact_ref']) == canonical({'declarations': []}).encode()
        assert d.custody.possession(d.parent, d.declarations['source_ref']) == 'own_completed_action'
        with pytest.raises(AppServiceCustodyError, match='input_not_possessed'):
            d.custody.possession(d.parent, d.declarations['source_ref'], before=1)
        save('original_selection_and_custody', dict(initial_known_record_refs=[], initial_receipt_count=initial_receipts,
            material=d.material, declarations=d.declarations, parse_action=dict(parse), parsed=parsed,
            assignment=d.frozen_assignment, submission=d.handoff,
            custody='own_completed_action', custody_before_parse='input_not_possessed'))
        d.acquire_manifest()
        assert d.api._completion(d.context) is None
        first = d.acquire_native('trim')
        assert d.api._completion(d.context) is None
        assert first['publication']['completion_proof'] is None
        assert first['publication']['requested_form_status'] == 'partial'
        assert [row['role'] for row in first['bundle']['artifacts']] == ['trim']
        assert first['publication']['adapter_result']['facts']['cutadapt_output_bases']['records'][0]['payload']['value'] == 28
        save('first_artifact_publication', first)
        body = d.acquire_native('final')
        assert body['publication']['requested_form_status'] == 'satisfied'
        proof = d.api._completion(d.context)
        assert proof is not None and d.api.verify_completion(d.context, proof)
        assert plain(d.context.assignment) == d.frozen_assignment
        assert body['publication_inputs']['selector'] == d.selected
        assert body['publication_inputs']['adapter_implementation_sha256'] == PIN
        assert body['bundle']['original_task'] == d.handoff['value']['original_task']
        assert [row['role'] for row in body['bundle']['artifacts']] == list(NAMES)
        for member in body['bundle']['artifacts']:
            name = member['role']
            assert member['requirement_ids'] == ['selected_' + name]
            assert member['task_association']['task_id'] == '123'
            assert member['workspace_object']['path'] == member['task_association']['output_path'] == output_objects[name][0]
            assert member['workspace_object']['uuid'] == member['task_association']['output_uuid'] == output_objects[name][1]
            assert store.get_artifact(member['raw_artifact_ref']) == native_bytes[name]
            assert member['sha256'] == hashlib.sha256(native_bytes[name]).hexdigest()
            assert member['byte_count'] == len(native_bytes[name])
            assert d.custody.possession(d.context, member['source_ref']) == 'own_completed_action'
            assert member['source_ref'] != 'source_' + name
            document = next(row for row in d.sheet['documents'] if row['document_id'] == name)
            assert document['artifact']['content_binding']['source_ref'] == member['source_ref']
            assert document['artifact']['content_binding']['artifact_ref'] == member['raw_artifact_ref']
        assert all(row['observed_state'] == 'unknown' for row in d.sheet['stages'])
        assert [row['requested_token'] for row in d.sheet['stages']] == ['TRIM']
        assert all(row['artifact']['identity'] == 'unknown' for row in d.sheet['documents'])
        assert all(edge['scope'] == 'artifact_local' and edge['task_stage_ref'] is None
                   for edge in d.sheet['native_lineage'])
        populations = {row['id']: row for row in d.sheet['populations']}
        for edge in d.sheet['native_lineage']:
            assert populations[edge['before_population_ref']]['document_ids'] == ['trim']
            assert populations[edge['after_population_ref']]['document_ids'] == ['trim']
        trim = next(row for row in d.sheet['documents'] if row['document_id'] == 'trim')
        assert [row['value'] for row in trim['labels'] if row['kind'] == 'producer_version'] == ['0.6.10', '4.9']
        save('final_publication', body)
        save('sheet', d.sheet)
        save('components', d.components)

        actions_before = action_rows(store)
        typed, key, refs = d.admit_numeric()
        forwarded, forwarded_key, forwarded_refs = d.admit_numeric(to_grandparent=True)
        assert typed == forwarded and refs == forwarded_refs
        values = assert_values(forwarded)
        assert_values(typed)
        validate_form(forwarded, d.schema, lambda ref, namespace=None: d.family.resolve(d.parent, ref, namespace))
        assert set(d.family.received_report_facts(d.grandparent)) == {
            'bvbrc_fastqutils_measurements', 'bvbrc_fastqutils_components', 'bvbrc_fastqutils_requirements'}
        for context in (d.parent, d.grandparent):
            assert d.custody.possession(context, body['source_ref']) == 'admitted_return'
        assert action_rows(store) == actions_before
        save('typed_returns', dict(schema=d.schema, result_to_parent=typed, parent_to_grandparent=forwarded,
            parent_references=refs, grandparent_references=forwarded_refs, decoded=values))

        retained = canonical([body, d.sheet, d.components, typed, forwarded])
        calls_before = deepcopy(d.client.calls)
        facts_before = deepcopy(d.family.received_report_facts(d.grandparent))
        attempts, patched = disable_reexecution(monkeypatch, d)
        assert d.api.read_result(body['source_ref'], d.context.scope) == body
        assert d.api.appservice.publications.read_content_source(
            body['publication']['adapter_result']['sheet_content']['source_ref'], d.context.scope) == d.sheet
        replayed, replay_key, replay_refs = d.admit_numeric()
        reforwarded, refwd_key, refwd_refs = d.admit_numeric(to_grandparent=True)
        assert (replayed, replay_key, replay_refs) == (typed, key, refs)
        assert (reforwarded, refwd_key, refwd_refs) == (forwarded, forwarded_key, forwarded_refs)
        assert_values(reforwarded)
        assert d.family.received_form_references(d.parent, typed, d.schema, key) == refs
        assert d.family.received_form_references(d.grandparent, forwarded, d.schema, forwarded_key) == forwarded_refs
        assert d.family.received_report_facts(d.grandparent) == facts_before
        assert canonical([body, d.sheet, d.components, typed, forwarded]) == retained
        assert d.client.calls == calls_before and not attempts
        assert action_rows(store) == actions_before
        assert store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0
        assert d.api._completion(d.context) == proof

        forged = deepcopy(typed)
        forged['facts_0'][0]['value']['records'][0]['payload']['value'] = 900
        rejections = []
        for context in (d.context, d.parent, d.grandparent):
            with pytest.raises(ValueError) as error:
                d.family.validate_received_report(context, forged, d.schema)
            rejections.append(dict(role=context.role, episode_id=context.episode_id, code=str(error.value)))
        assert not attempts and action_rows(store) == actions_before
        assert d.family.received_report_facts(d.grandparent) == facts_before
        save('saved_replay_and_forgery', dict(disabled_callables=patched, forbidden_attempts=attempts,
            result_to_parent=replayed, parent_to_grandparent=reforwarded,
            source_references_before=refs, source_references_after=replay_refs,
            selected_actions_before=len(actions_before), selected_actions_after=len(action_rows(store)),
            synthetic_observations=0, forged_measurement=900, rejections=rejections,
            practical_completion_proof=proof, transport_calls_unchanged=True))
        save('selected_actions', actions_before)
        save('controlled_transport_calls', calls_before)
        modules = []
        frozen = HERE / 'candidate'
        for name, module in sorted(sys.modules.items()):
            path = getattr(module, '__file__', None)
            if path is None or not Path(path).is_file():
                continue
            path = Path(path).resolve()
            if name.split('.', 1)[0] in ('gene_annotation_episode', 'method_loop'):
                assert path.is_relative_to(frozen), (name, path)
            modules.append(dict(module=name, path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        save('actual_import_origins', modules)
        summary = dict(passed=True, provider_pin=PIN, requested_fields=list(EXPECTED_NAMES),
            measurement_values=EXPECTED_MEASUREMENTS, cutadapt_retention=28 / 58,
            cutadapt_numerator=28, cutadapt_denominator=58,
            intermediate_cutadapt_population={'reads': 4, 'bases': 28},
            final_fastq_population={'reads': 3, 'bases': 24},
            first_artifact_completes=False, both_artifacts_complete=True,
            typed_boundary_count=2, saved_replay_preserves_sources_and_values=True,
            forged_value_rejection_count=len(rejections), forbidden_call_attempts=0,
            selected_action_count=len(actions_before), runtime_observation_count=0,
            initial_known_record_refs=[], material_custody='real_selected_material.parse',
            actual_host_objects=True, controlled_task_and_transport=True,
            actual_native_bytes_from_prior_local_producer=True, native_producers_executed=0,
            method_loop_run=False, configured_model_run=False, live_bvbrc_run=False,
            whole_tool_complete=False, production_changes=False)
        save('verified_summary', summary)
        print(json.dumps(summary, sort_keys=True))
