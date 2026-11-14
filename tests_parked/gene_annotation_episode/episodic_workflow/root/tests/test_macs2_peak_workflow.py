"""Separately selected native MACS2 Workflow proof and closed retained replay.

The model supplies fixture decisions only. Native data, actions, Sources,
receipts and parent forms must come from the existing application owners.
"""
import asyncio
import base64
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket

import pytest
from jsonschema import Draft202012Validator
from method_loop.archive import iter_json

from gene_annotation_episode import native_lifecycle
from gene_annotation_episode import native_macs2_peak_execution as native
from gene_annotation_episode import macs2_peak_request_binding as compact
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.decision_context import state_frame
from gene_annotation_episode.episodic_workflow.root.execution_episodes import RESULTS_VERSION
from gene_annotation_episode.episodic_workflow.root.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.local_file_capture_results import (
    SOURCE_REFS_SCHEMA, OUTCOMES_SCHEMA, MACS2_SELECTOR_VERSION,
)
from gene_annotation_episode.macs2_peak_result_contracts import (
    TOOL, FACT_SOURCE, macs2_peak_fact_sources, validate_macs2_peak_return,
)
from gene_annotation_episode.molecular_result_facts import (
    received_molecular_facts, own_molecular_facts, frozen_molecular_facts,
)
from gene_annotation_episode.molecular_measurement_tools import read_retained_molecular_publication
from gene_annotation_episode import macs2_peak_tools as peak_host
from gene_annotation_episode.episodic_workflow.root.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.episodic_workflow.root.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.episodic_workflow.root.received_native_file_inputs import received_file_context
from gene_annotation_episode.episodic_workflow.root.runtime import Workflow
from gene_annotation_episode.episodic_workflow.root.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry

from macs2_peak_fixtures import TAG_COUNT, file_identity, engineering_runtime
from test_macs2_peak_execution import job_fixture, fake_software
from test_macs2_peak_presentation import _connection


ROOT = Path(__file__).resolve().parents[4]
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
QUESTION = ('Which narrow enrichment peaks does MACS2 identify in the supplied treatment relative '
            'to its matched control, preserving native intervals, statistics, model output and qualifications?')
OUTPUT_ROLES = ('peaks_xls', 'narrowpeak', 'summits', 'model', 'stdout', 'stderr', 'seal')
HANDOFF_FORM = dict(type='object', additionalProperties=False, properties={
    'completed': dict(type='boolean', **{'x-source': 'execution_completed'}),
    'references': dict(type='array', uniqueItems=True,
        items=dict(type='string', format='reference', **{'x-reference-namespace': 'execution_handoff'}),
        **{'x-source': 'execution_handoff_refs'})}, required=['completed', 'references'])
CAPTURE_FORM = dict(type='object', additionalProperties=False, properties={
    'sources': deepcopy(SOURCE_REFS_SCHEMA), 'outcomes': deepcopy(OUTCOMES_SCHEMA),
    'completed': dict(type='boolean', **{'x-source': 'execution_completed'})},
    required=['sources', 'outcomes', 'completed'])
MONITOR_FORM = dict(type='object', additionalProperties=False, properties={
    'progress': dict(type='array', uniqueItems=True,
        items=dict(type='string', format='reference', **{'x-reference-namespace': 'episode_progress'}),
        **{'x-source': 'monitoring_progress_refs'}),
    'available': dict(type=['boolean', 'null'], **{'x-source': 'monitoring_result_available'})},
    required=['progress', 'available'])


def _write(path, value):
    path = Path(path)
    def encoded(original):
        if isinstance(original, (bytes, bytearray, memoryview)):
            return dict(encoding='base64', bytes=base64.b64encode(bytes(original)).decode('ascii'))
        raise TypeError('unrepresentable proof value: ' + type(original).__name__)
    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=encoded) + '\n')


def _pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _action(tool, arguments=None):
    return dict(selection=dict(kind='tool', tool=tool, arguments={} if arguments is None else arguments), report_update={})


def _commission(role, assignment, scope, form, objective):
    return dict(selection=dict(kind='episode_child', role=role, goal=objective, scope=scope,
        purpose='Return the explicitly requested native measurements with their original meanings and custody.',
        assignment=assignment, schema_json=json.dumps(form), initial_report_json='{}'), report_update={})


def _provider_value(value, schema):
    if 'anyOf' in schema:
        for branch in schema['anyOf']:
            candidate = _provider_value(value, branch)
            if Draft202012Validator(branch).is_valid(candidate):
                return candidate
        return value
    if schema.get('type') == 'string' and isinstance(value, dict) and schema.get('description', '').startswith('JSON encoding'):
        return json.dumps(value)
    if schema.get('type') == 'object' and isinstance(value, dict):
        result = dict(value)
        for name, field in schema.get('properties', {}).items():
            if name in result:
                result[name] = _provider_value(result[name], field)
            elif name in schema.get('required', []) and Draft202012Validator(field).is_valid(None):
                result[name] = None
        return result
    if isinstance(value, list) and 'items' in schema:
        return [_provider_value(item, schema['items']) for item in value]
    return value


def _rows(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: [dict(row) for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')]
        for name in names if not name.startswith('sqlite_')}


def _walk(record):
    yield record
    for unit in record['units']:
        if unit.get('child') is not None:
            yield from _walk(unit['child'])


def _controller(path, initial, *, scientific_horizon=4):
    horizon = scientific_horizon if path[-1][0] == 'scientific_process' else 1
    def estimate(raw, parameters, contexts):
        return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1), parameters,
            {'fixture': 'explicit engineering decision horizon, not scientific confidence'})
    return YieldController(str(path), initial, 0, YieldParameters(100, 50), estimate_with_context=estimate)


def _assemble(store, directory, provider, configuration):
    factory = ExecutionServiceFactory.from_record(configuration['factory'])
    tools = ToolRegistry(store, job_limits=deepcopy(native.POLICY))
    application = factory(store, run_id=configuration['run_id'], directory=directory / 'run', tool_registry=tools)
    def controller(path, initial):
        return _controller(path, initial, scientific_horizon=configuration.get('scientific_horizon', 4))
    flow = Workflow(store, tools, provider, directory / 'run', configuration['run_id'],
        controller_factory=controller, project_credit=lambda *_a, **_k: 0,
        annotation_child_roles=tuple(configuration.get('root_child_roles', ('scientific_process',))), episode_record_receipts=True,
        initial_known_record_refs=configuration['initial_refs'],
        episode_binding_descriptors=(configuration['scientific_binding'], *application.episode_binding_descriptors),
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    return flow, tools


async def _run(flow, configuration):
    root = flow.build('annotation', configuration.get('root_key', 'root'), configuration['question'], configuration['scope'])
    record = await root.run_async(flow.context)
    await root.build_result(record)
    return json.loads(''.join(iter_json(record.as_record())))


def _attempt_id():
    value = os.environ.get('HMMER_NATIVE_ORACLE_MACS2_PEAK_ATTEMPT_ID')
    if not value:
        pytest.skip('requires one explicitly selected unique MACS2 native attempt')
    assert re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', value)
    return value


class _ExpectedEngineeringFeedback(Exception):
    """Stop a negative fixture at its actual, still-pending feedback call."""


def _verify_received_capabilities(store, flow, execution_owner, context, values, capture_sources,
        unreceived_inputs, monkeypatch):
    known, _ = received_file_context(store, context, failure_prefix='macs2_capability_test_', baseline=False)
    capture_artifacts = {store.get(reference)['artifact_ref'] for reference in capture_sources}
    assert not set(capture_sources) & known
    assert not capture_artifacts & known
    assert not set(unreceived_inputs) & known
    resolver = flow.resolver(plain(context.scope), context=context)
    private = set()
    for value in values:
        source = store.get(value['source_ref'])
        assert value['source_ref'] in known and resolver(value['source_ref'], 'source') is True
        private.update([source['artifact_ref'], source['request_ref'], *source['auxiliary_artifact_refs']])
    assert not private & known
    assert all(resolver(reference, 'artifact') is False for reference in private)
    def no_private_bytes(*args, **kwargs):
        raise AssertionError('unreceived operand admission reached private or File bytes')
    reader = execution_owner.services.read_received_molecular_input
    with monkeypatch.context() as patch:
        patch.setattr(store, 'get_artifact', no_private_bytes)
        patch.setattr(execution_owner.local_file_sources, 'read_source', no_private_bytes)
        patch.setattr(execution_owner.local_file_sources, 'read_wrapper', no_private_bytes)
        patch.setattr(execution_owner.job_progress_provider.targets, '_native', no_private_bytes)
        with pytest.raises(ValueError, match='macs2_peak_capture_source_not_received'):
            execution_owner.read_macs2_peak_capture_selection(context, [capture_sources[0]])
        for reference in sorted(capture_artifacts | set(unreceived_inputs)):
            result, path = reader(context, reference, 'artifact', file_format='binary')
            assert result['input'] is None and path is None
            assert result['failure']['code'] == 'reference_not_received'
    return dict(capture_sources_received=False, capture_artifacts_received=False,
        unreceived_input_refs=sorted(unreceived_inputs), private_artifact_refs=sorted(private),
        private_artifact_scope_resolution=False, capture_and_file_operands_denied_before_bytes=True)


def _verify_closed_delivery(store, flow, tools, execution_owner, proof, monkeypatch):
    archive = proof['archive']
    assert archive is not None
    run_id, scope = proof['configuration']['run_id'], proof['configuration']['scope']
    journal = _rows(store)
    episode_roles = {row['episode_id']: json.loads(row['path'])[-1][0]
        for row in journal['runtime_episodes'] if row['run_id'] == run_id}
    assert sum(episode_roles[row['episode_id']] == 'scientific_process' for row in _walk(archive)) == 1
    science_id, = {episode_id for episode_id, role in episode_roles.items() if role == 'scientific_process'}
    science_calls = [call for call in proof['calls'] if call['episode_id'] == science_id]
    assert science_calls
    for call in science_calls:
        assert call.get('provider_role', call['role']) == 'REASONING'
        assert call['wire']['text'].startswith('TASK\n') and QUESTION in call['wire']['text']
        raw = call['wire']['text'].encode('utf-8')
        assert len(raw) == call['wire']['bytes'] and hashlib.sha256(raw).hexdigest() == call['wire']['sha256']
    assert proof['native_status']['returncode'] == 0 and proof['capture_form']['completed'] is True
    plan = proof['native_plan']
    captured = {}
    for source_ref in proof['capture_form']['sources']:
        source = store.get(source_ref)
        selection = json.loads(store.get_artifact(source['request_ref']))['selection']
        assert selection['format'] not in captured
        captured[selection['format']] = source
    seal_source = captured['macs2_peak_command_seal_v1']
    seal = json.loads(store.get_artifact(seal_source['artifact_ref']))
    native.validate_macs2_peak_seal(seal, plan=plan)
    assert seal['outcome'] == 'succeeded' and not seal['failures']
    assert 'macs2_model_r' in captured
    model_specification, = [row for row in plan['outputs'] if row['role'] == 'model']
    assert model_specification['relative_path'] == 'native/chipseq_native_model.r'
    selected_actions = [json.loads(row['action']) for row in journal['runtime_actions'] if row['run_id'] == run_id]
    assert sum(action.get('kind') == 'tool' and action.get('tool') == 'practical.job.start'
        for action in selected_actions) == 1
    forms = [json.loads(row['form']) for row in journal['runtime_forms']
        if row['run_id'] == run_id and row['form'] is not None]
    returned = [value for value in forms if set(value) == {'peaks'}]
    assert returned and all(value['peaks'] == returned[0]['peaks'] for value in returned)
    peaks, = returned[0]['peaks']
    validate_macs2_peak_return(peaks)
    assert peaks['native_outcome'] == 'succeeded' and peaks['status'] == 'complete'
    assert peaks['reported_metadata']['format'] == 'AUTO' and peaks['reported_metadata']['control_presence'] == 'present'
    assert peaks['reported_numbers']['treatment_total_tags']['value'] == TAG_COUNT
    assert peaks['reported_numbers']['control_total_tags']['value'] == TAG_COUNT
    assert peaks['reported_numbers']['d_bp']['state'] == 'present' and peaks['reported_numbers']['d_bp']['value'] > 0
    assert all(row['count'] > 0 and row['extent'] == 'complete' for row in peaks['native_peak_counts'])
    assert peaks['peak_window']['total_rows'] >= 3
    assert {row['representation'] for row in peaks['peak_window']['rows']} == {'xls', 'narrowpeak', 'summit'}
    records_owner = EpisodeReturnRecords(store, run_id, failure_prefix='macs2_peak_fixture_')
    root_context = records_owner.context(archive['episode_id'])
    science_context = records_owner.context(science_id)
    assert received_molecular_facts(store, run_id, root_context, fact_source=FACT_SOURCE) == [peaks]
    root_resolver = flow.resolver(scope, context=root_context)
    science_resolver = flow.resolver(scope, context=science_context)
    assert root_resolver(peaks['source_ref'], 'source') is True
    original_packet_reader = peak_host._publication_bytes
    packet_ref = store.get(peaks['source_ref'])['artifact_ref']
    with monkeypatch.context() as patch:
        def public_packet_only(actual_store, reference):
            assert reference == packet_ref, 'generic retained reader opened private controls or component bytes'
            return original_packet_reader(actual_store, reference)
        def no_private_controls(*args, **kwargs):
            raise AssertionError('generic retained reader entered private component custody')
        patch.setattr(peak_host, '_publication_bytes', public_packet_only)
        patch.setattr(peak_host, '_control', no_private_controls)
        retained = read_retained_molecular_publication(tools, root_context,
            execution_owner.services.read_received_molecular_input, peaks['source_ref'], tool_name=TOOL)
        assert retained['public'] == peaks
    permissions = []
    root_capabilities = _verify_received_capabilities(store, flow, execution_owner, root_context, [peaks],
        proof['capture_form']['sources'], [], monkeypatch)
    root_known, _ = received_file_context(store, root_context, failure_prefix='macs2_capability_test_', baseline=False)
    science_known, _ = received_file_context(store, science_context, failure_prefix='macs2_capability_test_', baseline=False)
    original_inputs = {row['file']['artifact_ref'] for row in proof['selected_job']['request']['inputs']}
    assert original_inputs <= root_known  # The original caller supplied these independent Files.
    for reference in proof['capture_form']['sources']:
        body = store.get(reference)
        assert reference in science_known
        assert science_resolver(reference, 'source') is True
        permissions.append(dict(source_ref=reference, artifact_ref=body['artifact_ref'],
            scientific_source_received=True, root_source_received=False, root_artifact_received=False))
    assert store.count('annotation') == 0
    return dict(delivery_permissions=permissions, root_received_facts=[peaks], parent_form=returned[0],
        episode_roles=episode_roles, scientific_wire_calls=len(science_calls), captured_model_source=captured['macs2_model_r']['id'],
        root_capabilities=root_capabilities, independently_supplied_inputs_preserved=sorted(original_inputs))


def _verify_closed_local_completion(store, execution_owner, proof, original_directory, monkeypatch):
    run_id = proof['configuration']['run_id']
    records = EpisodeReturnRecords(store, run_id, failure_prefix='macs2_peak_fixture_')
    contexts = [records.context(row['episode_id']) for row in _rows(store)['runtime_episodes']
        if row['run_id'] == run_id and json.loads(row['path'])[-1][0] == 'launch_local']
    context, = contexts
    completions = [json.loads(row['observation'])['credit']['practical_completion']
        for row in _rows(store)['runtime_observations']
        if row['run_id'] == run_id and row['episode_id'] == context.episode_id
        and isinstance(json.loads(row['observation']).get('credit'), dict)
        and json.loads(row['observation'])['credit'].get('practical_completion') is not None]
    completion, = completions
    original_get_artifact, path_open = store.get_artifact, Path.open
    inputs = {row['file']['artifact_ref'] for row in proof['selected_job']['request']['inputs']}
    with monkeypatch.context() as patch:
        def no_input_bytes(reference, *args, **kwargs):
            assert reference not in inputs, 'closed completion verification reopened selected input bytes'
            return original_get_artifact(reference, *args, **kwargs)
        def no_original_bytes(path, *args, **kwargs):
            assert not Path(path).is_relative_to(original_directory), 'closed completion verification reopened original paths'
            return path_open(path, *args, **kwargs)
        patch.setattr(store, 'get_artifact', no_input_bytes)
        patch.setattr(Path, 'open', no_original_bytes)
        assert execution_owner._closed_completion_verdict(context, completion) is True
        assert execution_owner.verify_completion(context, completion) is True
        assert compact.materialized_assignment(store, context)['requested_job']['native_macs2_peak'] == proof['selected_job']
    return dict(context=context.as_record(), completion=completion, verified=True, selected_input_reads=0)


def _verify_saved_view_delivery(store, flow, tools, execution_owner, audit, capture_sources, input_refs, monkeypatch):
    run_id = audit['configuration']['run_id']
    original = audit['original_value']
    validate_macs2_peak_return(original)
    source_ref = original['source_ref']
    component_ref, = store.get(source_ref)['auxiliary_artifact_refs']
    selected = [row for row in audit['journal']['runtime_actions'] if row['run_id'] == run_id]
    actions = [row for row in selected if json.loads(row['action']).get('kind') == 'tool'
        and json.loads(row['action']).get('tool') == TOOL]
    commissions = [row for row in selected if json.loads(row['action']).get('kind') == 'episode_child']
    assert len(actions) == 3 and len(commissions) == 1 and len(selected) == 4
    assert json.loads(commissions[0]['action'])['role'] == 'scientific_process'
    outcomes = [json.loads(row['result']) for row in sorted(actions, key=lambda row: row['decision_index'])]
    assert all(value['status'] in ('completed', 'partial') for value in outcomes)
    for outcome in outcomes[:2]:
        assert outcome['result'] == original and outcome['record_refs'] == [source_ref]
        assert outcome['changed_record_refs'] == []
    projected = outcomes[2]['result']
    validate_macs2_peak_return(projected)
    assert projected['source_ref'] != source_ref
    assert outcomes[2]['record_refs'] == outcomes[2]['changed_record_refs'] == [projected['source_ref']]
    assert store.get(projected['source_ref'])['auxiliary_artifact_refs'] == [component_ref]
    assert projected['peak_window']['row_window'] == dict(offset=1, limit=1)
    assert projected['peak_window']['rows'] == original['peak_window']['rows'][1:2]
    for field in ('native_outcome', 'run_key', 'reference_id', 'native_peak_counts',
            'reported_metadata', 'reported_numbers', 'issues', 'failures'):
        assert projected[field] == original[field]
    assert len(audit['worker_requests']) == len(audit['saved_worker_handles']) == 1
    request, = audit['worker_requests']
    assert request['mode'] == 'project_saved' and request['native'] is None
    assert request['saved']['file']['artifact_ref'] == component_ref
    assert request['saved']['failures'] == original['failures']
    if 'sources_before' in audit:
        assert store.count('source') == audit['sources_before'] + 1
    records = EpisodeReturnRecords(store, run_id, failure_prefix='macs2_peak_fixture_')
    science_id, = {call['episode_id'] for call in audit['calls'] if call['role'] == 'scientific_process'}
    science_context = records.context(science_id)
    root_context = records.context(audit['archive']['episode_id'])
    expected = [original, projected]
    packet_refs = {store.get(value['source_ref'])['artifact_ref'] for value in expected}
    packet_reader = peak_host._publication_bytes
    with monkeypatch.context() as patch:
        def public_only(actual_store, reference):
            assert reference in packet_refs, 'retained view audit opened private component or control bytes'
            return packet_reader(actual_store, reference)
        def no_controls(*args, **kwargs):
            raise AssertionError('retained view audit entered private component custody')
        patch.setattr(peak_host, '_publication_bytes', public_only)
        patch.setattr(peak_host, '_control', no_controls)
        reader = execution_owner.services.read_received_molecular_input
        assert own_molecular_facts(tools, science_context, read_received=reader, fact_source=FACT_SOURCE) == expected
        assert frozen_molecular_facts(store, run_id, science_context, fact_source=FACT_SOURCE) == expected
        assert received_molecular_facts(store, run_id, root_context, fact_source=FACT_SOURCE) == expected
        for value in expected:
            assert read_retained_molecular_publication(tools, science_context, reader,
                value['source_ref'], tool_name=TOOL)['public'] == value
    capabilities = _verify_received_capabilities(store, flow, execution_owner, science_context, expected,
        capture_sources, input_refs, monkeypatch)
    return dict(completed=True, original_value=original, projected_value=projected, new_sources=1,
        redisplay_changed_record_refs=[[], []], typed_parent_sources=[source_ref, projected['source_ref']],
        capabilities=capabilities)


def _workflow_case(directory, runtime, *, attempt_id, template_pin, monkeypatch,
        engineered=False, select_seal=True, reject_input=None):
    assert reject_input in (None, 'unreceived')
    def no_http(*args, **kwargs):
        raise AssertionError('selected local MACS2 proof attempted external acquisition')
    monkeypatch.setattr(socket, 'create_connection', no_http)
    directory = Path(directory)
    directory.mkdir()  # An existing selected attempt is never overwritten or retried.
    proof_path = directory / 'MACS2_PEAK_WORKFLOW.json'
    proof = dict(version='macs2_peak_workflow_proof_v1', attempt_id=attempt_id, question=QUESTION,
        origin='synthetic_engineering_fixture', external_model_rpc_calls=0, macs2_command_budget=1,
        verification_scope=('Engineered command/protocol control; no MACS2 scientific algorithm or native MACS2 libraries.'
            if engineered else 'One genuine MACS2 command and actual custody/typed delivery through the compact public interface.'),
        template=template_pin, phase='selected', closed=False, archive=None,
        native_plan=None, native_status=None, capture_form=None, parent_form=None,
        configuration=None, calls=[], journal={}, store_files=[], native_files=[])
    _write(proof_path, proof)  # Durable prefix precedes preparation and every possible dispatch.
    store = None
    try:
        software = native.freeze_macs2_peak_software_binding(module_root=str(ROOT),
            snapshot_directory=str(directory / 'software'), native_runtime=runtime)
        store = Store(directory / 'state')
        store.create_problem(raw_sequence='ACGTACGT', molecule='dna')
        scope = store.validate_scope()
        supplied = job_fixture(directory / 'supplied', software=software)
        initial_refs = []
        for occurrence, binding in zip(supplied['request']['inputs'], supplied['input_bindings'], strict=True):
            raw = Path(binding['path']).read_bytes()
            artifact_ref = store.artifact(raw)
            assert file_identity(raw) == occurrence['file'] == binding['file']
            assert artifact_ref == binding['file']['artifact_ref']
            binding['path'] = str(store.path / 'artifacts' / binding['file']['sha256'][:2] / binding['file']['sha256'])
            initial_refs.append(artifact_ref)
        workspace = directory / 'workspace'
        workspace.mkdir()
        public_request = deepcopy(supplied['request'])
        for row in public_request['inputs']:
            row['file'] = {key: row['file'][key] for key in ('artifact_ref', 'format')}
        public_assignment = dict(version=compact.ASSIGNMENT_VERSION, resource_id='here', resource_kind='local',
            binding_ordinal_0based=0, endpoint='usable_handoff', request=public_request,
            progress_requirements=[dict(key='handoff', credit=7, predicate=dict(kind='requested_job_handoff'))],
            completion_keys=['handoff'], constraints=dict(allocation=deepcopy(native.POLICY)))
        launch = dict(version=compact.LAUNCH_VERSION, requests=dict(here=public_assignment),
            constraints=dict(allowed_resource_ids=['here'], allowed_kinds=['local'], allocation=deepcopy(native.POLICY)))
        factory = ExecutionServiceFactory(dict(here=dict(kind='local', workspace=str(workspace),
            policy=deepcopy(native.POLICY), native_macs2_peak=[dict(operation=native.OPERATION,
                mode=native.MODE, software=software)])), {}, 3, 2, 1, log_window_bytes=128)
        preliminary = ToolRegistry(store, job_limits=deepcopy(native.POLICY))
        run_id = 'macs2-native-' + attempt_id
        application = factory(store, run_id=run_id, directory=directory / 'run', tool_registry=preliminary)
        scientific_binding = prepare_scientific_binding(run_directory=directory / 'run', source_directory=PUBLICATION,
            tool_catalog=preliminary.catalog(), child_roles=('scientific_process', 'launch', 'monitor', 'results'),
            resource_catalogs=application.resource_tool_catalogs)
        library = ScientificProcessLibrary(directory / 'run/scientific-process-library')
        scientific_assignment = dict(selection=dict(version='scientific_process_selection_v3',
            evidence_axis=library.reference('A105'), thought_pattern=library.reference('P14'),
            child_tool_info=[dict(name=native.OPERATION, resources='local'), dict(name=TOOL, resources='local')]),
            evidence_refs=scope['subject_refs'], constraints=dict(no_external_acquisition=True,
                allocation=deepcopy(native.POLICY)), context=dict(question=QUESTION,
                engineered_origin='synthetic_engineering_fixture', supplied_macs2_request=deepcopy(public_request),
                candidate_annotation_required=False, biological_binding_or_function_inference=False))
        parent_schema = dict(type='object', properties={
            'peaks': deepcopy(macs2_peak_fact_sources()[FACT_SOURCE]['report_schema'])},
            required=['peaks'], additionalProperties=False)
        configuration = dict(run_id=run_id, factory=factory.as_record(), scientific_binding=scientific_binding,
            question=QUESTION, scope=scope,
            initial_refs=[] if reject_input == 'unreceived' else initial_refs,
            scientific_horizon=1 if reject_input else 4, parent_schema=parent_schema)
        proof['configuration'] = configuration
        proof['selected_job'] = supplied
        proof['selected_launch'] = launch
        proof['published_selection'] = dict(evidence_axis='A105', thought_pattern='P14')
        _write(directory / 'configuration.json', configuration)
        _write(proof_path, proof)

        class Choices:
            def __init__(self):
                self.turns, self.owner = {}, None
                self.handoff = self.plan = None
                self.connection, self.previous = _connection(), {}

            async def complete(self, episode_id, role, instructions, current, schema):
                current = plain(current)
                saved_episode = store.db.execute('SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                    (run_id, episode_id)).fetchone()
                episode_role = json.loads(saved_episode['path'])[-1][0]
                self.turns[episode_id] = self.turns.get(episode_id, 0) + 1
                turn = self.turns[episode_id]
                frame = state_frame(current, self.previous.get(episode_id))
                wire, sent_instructions = self.connection._presentation(episode_id, 'REASONING', instructions, frame)
                self.previous[episode_id] = deepcopy(current)
                proof['calls'].append(dict(episode_id=episode_id, role=episode_role, provider_role=role, turn=turn,
                    instructions=plain(instructions), current=deepcopy(current), schema=plain(schema),
                    wire=dict(text=wire, instructions=plain(sent_instructions),
                        bytes=len(wire.encode('utf-8')), sha256=hashlib.sha256(wire.encode('utf-8')).hexdigest())))
                if episode_role == 'scientific_process':
                    assert wire.startswith('TASK\n') and QUESTION in wire
                proof['journal'] = _rows(store)
                _write(proof_path, proof)
                if current.get('feedback') and engineered and (not select_seal or reject_input):
                    proof['expected_feedback'] = deepcopy(current['feedback'])
                    proof['phase'] = 'expected_feedback_pending'
                    _write(proof_path, proof)
                    raise _ExpectedEngineeringFeedback('observed the selected negative boundary')
                assert not current.get('feedback'), current.get('feedback')
                if 'practical_assignment' in current:
                    assert turn == 1
                    assert compact.is_compact_assignment(current['practical_assignment'])
                    original_context = EpisodeReturnRecords(store, run_id,
                        failure_prefix='macs2_peak_fixture_').context(episode_id)
                    materialized = compact.materialized_assignment(store, original_context)
                    assert materialized['requested_job']['native_macs2_peak'] == supplied
                    proof['phase'] = 'selected_native_start'
                    answer = _action('practical.job.start')
                elif current.get('execution_assignment', {}).get('version') == compact.LAUNCH_VERSION:
                    assert turn == 1
                    selected = current['execution_assignment']['requests']['here']
                    assert compact.is_compact_assignment(selected)
                    answer = _commission('launch_local', selected, scope, HANDOFF_FORM,
                        'Run the one selected MACS2 treatment/control command with its original native defaults.')
                elif 'monitor_assignment' in current:
                    assert turn == 1
                    answer = _action('progress.observe', dict(requested_fields=[
                        'execution_status', 'result_available', 'log_windows']))
                elif current.get('execution_assignment', {}).get('version') == RESULTS_VERSION:
                    assert turn == 1
                    answer = _action('execution.results.collect')
                elif 'scientific_process' not in current:
                    assert turn == 1
                    answer = _commission('scientific_process', scientific_assignment, scope, parent_schema, QUESTION)
                elif turn == 1:
                    answer = _commission('launch', launch, scope, HANDOFF_FORM, QUESTION)
                elif turn == 2:
                    reader = PracticalReceiptInformation(store, run_id)
                    self.handoff, = [ref for ref in current['child_reports'][-1]['references']
                        if reader.read(ref, scope)['receipt']['tool_name'] == 'practical.job.start']
                    target = self.owner.job_progress_provider.targets.read_target(self.handoff, scope)
                    status = await asyncio.to_thread(native_lifecycle.wait_job,
                        native_lifecycle.NativeJobHandle(Path(target['execution_id'])))
                    self.plan = native.read_local_macs2_peak_plan(target['assignment'], target['execution_id'])
                    proof['native_plan'] = self.plan
                    proof['native_status'] = dict(returncode=status.returncode, metadata=status.metadata)
                    proof['phase'] = 'native_terminal'
                    _write(proof_path, proof)
                    answer = _commission('monitor', dict(version='monitor_assignment_v1',
                        target_handle=self.handoff, requested_fields=['execution_status', 'result_available', 'log_windows'],
                        known_progress_refs=[], permitted_committed_record_types=[]), scope, MONITOR_FORM,
                        'Observe the actual selected job status and retained log windows; preserve unknowns.')
                elif turn == 3:
                    selector = dict(version=MACS2_SELECTOR_VERSION,
                        output_roles=[role for role in OUTPUT_ROLES if select_seal or role != 'seal'])
                    answer = _commission('results', dict(version=RESULTS_VERSION, handoff_ref=self.handoff,
                        selector=selector), scope, CAPTURE_FORM,
                        'Retain the selected original seal and native output files with their actual capture outcomes.')
                else:
                    assert turn == 4
                    capture = deepcopy(current['child_reports'][-1])
                    proof['capture_form'] = capture
                    proof['phase'] = 'captured'
                    _write(proof_path, proof)
                    answer = _action(TOOL, dict(mode='parse', capture_source_refs=capture['sources'],
                        row_window=dict(offset=0, limit=6)))
                _write(proof_path, proof)
                answer = _provider_value(plain(answer), plain(schema))
                Draft202012Validator(plain(schema)).validate(answer)
                return answer

            async def release(self, episode_id):
                pass

        provider = Choices()
        flow, tools = _assemble(store, directory, provider, configuration)
        if not select_seal or reject_input:
            async def no_worker(*args, **kwargs):
                raise AssertionError('unreceived producer seal reached the retained parser worker')
            monkeypatch.setattr(tools, '_sequence_worker_async', no_worker)
        if reject_input:
            def no_dispatch(*args, **kwargs):
                raise AssertionError('rejected compact File selection reached native preparation')
            monkeypatch.setattr(native_lifecycle, 'prepare_job', no_dispatch)
            original_artifact = store.get_artifact
            def no_input_payload(reference, *args, **kwargs):
                assert reference not in initial_refs, 'compiler opened selected File payload instead of metadata'
                return original_artifact(reference, *args, **kwargs)
            monkeypatch.setattr(store, 'get_artifact', no_input_payload)
        provider.owner = flow.episode_bindings.for_role('results')
        archive = asyncio.run(_run(flow, configuration))
        assert select_seal and reject_input is None, 'negative fixture unexpectedly completed the Workflow'
        proof['archive'] = archive
        proof['journal'] = _rows(store)
        proof['phase'] = 'workflow_closed'
        _write(proof_path, proof)  # Preserve actual closure before numerical/delivery assertions.
        proof.update(_verify_closed_delivery(store, flow, tools, provider.owner, proof, monkeypatch))
        proof['closed'] = True
        return proof_path
    except _ExpectedEngineeringFeedback:
        assert engineered and (not select_seal or reject_input)
        assert proof['closed'] is False and proof['archive'] is None and proof['parent_form'] is None
        proof['journal'] = _rows(store)
        feedback_call = proof['calls'][-1]
        pending, = [row for row in proof['journal']['runtime_model_calls']
            if row['episode_id'] == feedback_call['episode_id'] and row['response'] is None]
        assert json.loads(pending['request'])['context']['feedback'] == proof['expected_feedback']
        proof['pending_feedback_call'] = dict(episode_id=pending['episode_id'], call_index=pending['call_index'])
        selected_actions = [json.loads(row['action']) for row in proof['journal']['runtime_actions']]
        if reject_input:
            assert not any(action.get('tool') == 'practical.job.start' for action in selected_actions)
            expected = 'macs2_peak_request_input_not_received'
            assert proof['expected_feedback'] == dict(status='invalid', category='action_contract', detail=expected)
            assert proof['native_plan'] is proof['native_status'] is None
            original, = [row for row in proof['journal']['runtime_model_calls']
                if row['episode_id'] == pending['episode_id'] and row['call_index'] == pending['call_index'] - 1]
            response = json.loads(original['response'])
            assert response['selection']['kind'] == 'episode_child'
            assert response['selection']['role'] == 'launch'
            selected_assignment = response['selection']['assignment']
            if isinstance(selected_assignment, str):
                selected_assignment = json.loads(selected_assignment)
            assert selected_assignment == launch
            proof['expected_input_rejection'] = expected
        else:
            actions = [row for row in proof['journal']['runtime_actions']
                if json.loads(row['action']).get('tool') == TOOL]
            assert len(actions) == 1 and actions[0]['result'] is not None
            failure = json.loads(actions[0]['result'])
            assert failure['status'] == 'unavailable' and failure['result'] is None
            assert failure['record_refs'] == [] and actions[0]['credit'] is None
            assert failure['feedback']['code'] == 'macs2_peak_producer_seal_not_received'
            assert proof['expected_feedback'] == failure['feedback']
            assert proof['native_status']['returncode'] == 0
            assert proof['capture_form']['completed'] is True
            assert sum(action.get('tool') == 'practical.job.start' for action in selected_actions) == 1
            assert all(json.loads(row['data']).get('provider') != TOOL
                for row in store.db.execute("SELECT data FROM records WHERE record_type='source'"))
            proof['expected_unavailable'] = failure
        proof['expected_boundary_verified'] = True
        return proof_path
    except BaseException as error:
        proof['exception'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        if store is not None:
            proof['journal'] = _rows(store)
            store.close()
            proof['store_files'] = [_pin(path) for path in sorted((directory / 'state').rglob('*')) if path.is_file()]
        plan = proof.get('native_plan')
        if plan is not None:
            proof['native_files'] = [_pin(path) for path in sorted(Path(plan['attempt_directory']).rglob('*')) if path.is_file()]
        _write(proof_path, proof)


def test_genuine_single_macs2_command_reaches_typed_scientific_parent(tmp_path, monkeypatch):
    attempt_id = _attempt_id()
    template_path = Path(os.environ['HMMER_NATIVE_ORACLE_MACS2_PEAK_RUNTIME_TEMPLATE'])
    template = json.loads(template_path.read_bytes())
    runtime = template['requested_job']['native_atac_differential']['software']['macs2_runtime']
    _workflow_case(tmp_path / ('macs2-' + attempt_id), runtime, attempt_id=attempt_id,
        template_pin=_pin(template_path), monkeypatch=monkeypatch)


@pytest.mark.parametrize('select_seal', [False, True])
def test_engineered_public_compiler_actual_capture_and_typed_boundary(tmp_path, monkeypatch, select_seal):
    """Actual owners and an explicitly pinned Python stand-in, no native MACS2."""
    runtime = engineering_runtime(tmp_path / 'engineering-runtime')
    manifest = tmp_path / 'engineering-runtime.json'
    _write(manifest, dict(origin='engineered_protocol_standin_not_macs2', runtime=runtime))
    proof_path = _workflow_case(tmp_path / 'engineered-case', runtime,
        attempt_id='engineered-seal' if select_seal else 'engineered-no-seal',
        template_pin=_pin(manifest), monkeypatch=monkeypatch, engineered=True, select_seal=select_seal)
    proof = json.loads(proof_path.read_bytes())
    assert 'no MACS2 scientific algorithm' in proof['verification_scope']
    assert proof['configuration']['question'] == QUESTION
    assert proof['selected_launch']['version'] == compact.LAUNCH_VERSION
    public = proof['selected_launch']['requests']['here']['request']
    assert all(set(row['file']) == {'artifact_ref', 'format'} for row in public['inputs'])
    if select_seal:
        assert proof['closed'] is True
        assert proof['parent_form']['peaks'] == proof['root_received_facts']
        assert len(proof['delivery_permissions']) == 7
    else:
        assert proof['closed'] is False and proof['archive'] is None
        assert proof['expected_boundary_verified'] is True
        assert proof['parent_form'] is None
        assert proof['expected_unavailable']['feedback']['code'] == 'macs2_peak_producer_seal_not_received'


@pytest.mark.parametrize('rejection', ['unreceived'])
def test_engineered_public_compiler_denies_inputs_before_payload_or_dispatch(tmp_path, monkeypatch, rejection):
    runtime = engineering_runtime(tmp_path / 'engineering-runtime')
    manifest = tmp_path / 'engineering-runtime.json'
    _write(manifest, dict(origin='engineered_protocol_standin_not_macs2', runtime=runtime))
    proof_path = _workflow_case(tmp_path / 'denied-case', runtime, attempt_id='denied-' + rejection,
        template_pin=_pin(manifest), monkeypatch=monkeypatch, engineered=True, reject_input=rejection)
    proof = json.loads(proof_path.read_bytes())
    assert proof['closed'] is False and proof['archive'] is None and proof['native_plan'] is None
    assert proof['expected_boundary_verified'] is True
    assert proof['expected_input_rejection']


def test_metadata_only_compiler_preserves_independent_file_grant_despite_invalid_marker(tmp_path, monkeypatch):
    """Malformed marker data cannot revoke actual independent caller File receipts."""
    directory = tmp_path / 'metadata-only-independent-file-grant'
    directory.mkdir()
    audit_path = directory / 'MACS2_INDEPENDENT_FILE_GRANT.json'
    audit = dict(question=QUESTION, origin='engineered_metadata_only_compiler_control', calls=[],
        closed=False, preview_accepted=False, native_dispatches=0, selected_payload_reads=0)
    _write(audit_path, audit)
    def forbidden(*args, **kwargs):
        raise AssertionError('metadata-only compiler control reached native work or payload execution')
    for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
        monkeypatch.setattr(native_lifecycle, name, forbidden)
    monkeypatch.setattr(native, 'prepare_local_macs2_peak', forbidden)
    monkeypatch.setattr(native, 'run_macs2_peak', forbidden)
    monkeypatch.setattr(native, 'verify_software', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    class PreviewObserved(Exception):
        pass
    store = None
    try:
        store = Store(directory / 'state')
        store.create_problem(raw_sequence='ACGTACGT', molecule='dna')
        scope = store.validate_scope()
        software = fake_software()
        # A declared engineering metadata path, never a verified or executed
        # binary. Its parent layout gives the compiler an absolute PYTHONHOME.
        software['driver_runtime']['python_executable'] = str(directory / 'metadata-runtime/bin/python3.12')
        supplied = job_fixture(directory / 'supplied', software=software)
        initial_refs = [store.artifact(Path(row['path']).read_bytes()) for row in supplied['input_bindings']]
        assert initial_refs == [row['file']['artifact_ref'] for row in supplied['input_bindings']]
        marker = store.put('source', dict(provider='episode.execution_result',
            accession='deliberately_invalid_marker_without_native_producer', uri=None,
            artifact_ref=initial_refs[0], text_ref=None, request_ref=None,
            version='native_blast_utility_bundle_v1', retrieved_at=None), origin='tool')
        audit['invalid_marker'] = dict(source_ref=marker['id'],
            reason='Raw BED primary bytes and no native producer or custody witness; never a protected-result authority.')
        public_request = deepcopy(supplied['request'])
        for row in public_request['inputs']:
            row['file'] = {key: row['file'][key] for key in ('artifact_ref', 'format')}
        selected = dict(version=compact.ASSIGNMENT_VERSION, resource_id='here', resource_kind='local',
            binding_ordinal_0based=0, endpoint='usable_handoff', request=public_request,
            progress_requirements=[dict(key='handoff', credit=7, predicate=dict(kind='requested_job_handoff'))],
            completion_keys=['handoff'], constraints=dict(allocation=deepcopy(native.POLICY)))
        launch = dict(version=compact.LAUNCH_VERSION, requests=dict(here=selected),
            constraints=dict(allowed_resource_ids=['here'], allowed_kinds=['local'], allocation=deepcopy(native.POLICY)))
        workspace = directory / 'unused-workspace'
        workspace.mkdir()
        factory = ExecutionServiceFactory(dict(here=dict(kind='local', workspace=str(workspace),
            policy=deepcopy(native.POLICY), native_macs2_peak=[dict(operation=native.OPERATION,
                mode=native.MODE, software=supplied['software'])])), {}, 3, 2, 1)
        preliminary = ToolRegistry(store, job_limits=deepcopy(native.POLICY))
        run_id = 'macs2-independent-file-metadata-control'
        application = factory(store, run_id=run_id, directory=directory / 'run', tool_registry=preliminary)
        binding = prepare_scientific_binding(run_directory=directory / 'run', source_directory=PUBLICATION,
            tool_catalog=preliminary.catalog(), child_roles=('scientific_process', 'launch', 'monitor', 'results'),
            resource_catalogs=application.resource_tool_catalogs)
        library = ScientificProcessLibrary(directory / 'run/scientific-process-library')
        science = dict(selection=dict(version='scientific_process_selection_v3',
            evidence_axis=library.reference('A105'), thought_pattern=library.reference('P14'),
            child_tool_info=[dict(name=native.OPERATION, resources='local')]), evidence_refs=scope['subject_refs'],
            constraints=dict(no_external_acquisition=True, allocation=deepcopy(native.POLICY)),
            context=dict(question=QUESTION, supplied_macs2_request=public_request,
                origin='metadata_only_independent_file_admission_control'))
        parent_schema = dict(type='object', properties={
            'peaks': deepcopy(macs2_peak_fact_sources()[FACT_SOURCE]['report_schema'])},
            required=['peaks'], additionalProperties=False)
        configuration = dict(run_id=run_id, factory=factory.as_record(), scientific_binding=binding,
            question=QUESTION, scope=scope, initial_refs=initial_refs, scientific_horizon=1, parent_schema=parent_schema)
        class Preview:
            owner = None
            async def complete(self, episode_id, provider_role, instructions, current, schema):
                current = plain(current)
                context = EpisodeReturnRecords(store, run_id, failure_prefix='metadata_test_').context(episode_id)
                audit['calls'].append(dict(episode_id=episode_id, role=context.role,
                    provider_role=provider_role, current=deepcopy(current)))
                _write(audit_path, audit)
                assert not current.get('feedback'), current.get('feedback')
                if context.role == 'annotation':
                    result = _provider_value(_commission('scientific_process', science, scope, parent_schema, QUESTION), plain(schema))
                    Draft202012Validator(plain(schema)).validate(result)
                    return result
                assert context.role == 'scientific_process'
                before = _rows(store)
                public, rows = self.owner.macs2_peak_requests.preview(context, launch)
                assert public == launch and len(rows) == 1
                assert _rows(store) == before, 'metadata compiler preview mutated Store or receipt history'
                compiled = rows[0]['assignment']['requested_job']['native_macs2_peak']
                assert rows[0]['selection'] == selected and rows[0]['selection']['binding_ordinal_0based'] == 0
                assert compiled['request'] == supplied['request']
                assert rows[0]['binding']['software'] == supplied['software']
                assert [row['file']['artifact_ref'] for row in compiled['input_bindings']] == initial_refs
                audit.update(preview_accepted=True, independent_file_grant_preserved=True,
                    saved_science_context=context.as_record(), public_selection=public,
                    compiled_input_identities=[row['file'] for row in compiled['input_bindings']], preview_store_unchanged=True)
                _write(audit_path, audit)
                raise PreviewObserved('verified metadata preview; no launch was selected')
            async def release(self, episode_id):
                pass
        provider = Preview()
        flow, tools = _assemble(store, directory, provider, configuration)
        provider.owner = flow.episode_bindings.for_role('results')
        monkeypatch.setattr(tools, '_sequence_worker_async', forbidden)
        original_get_artifact = store.get_artifact
        def no_selected_payload(reference, *args, **kwargs):
            assert reference not in initial_refs, 'compiler preview opened selected File bytes'
            return original_get_artifact(reference, *args, **kwargs)
        monkeypatch.setattr(store, 'get_artifact', no_selected_payload)
        blocked_paths = {Path(row['path']) for row in supplied['input_bindings']}
        blocked_paths.update(store.path / 'artifacts' / row['file']['sha256'][:2] / row['file']['sha256']
            for row in supplied['input_bindings'])
        path_open = Path.open
        with monkeypatch.context() as patch:
            def no_selected_path(path, *args, **kwargs):
                assert Path(path) not in blocked_paths, 'compiler preview opened selected File path'
                return path_open(path, *args, **kwargs)
            patch.setattr(Path, 'open', no_selected_path)
            try:
                asyncio.run(_run(flow, configuration))
            except PreviewObserved:
                assert audit['preview_accepted'] is True
            else:
                raise AssertionError('metadata-only preview unexpectedly closed the Workflow')
        journal = _rows(store)
        episodes = [row for row in journal['runtime_episodes'] if row['run_id'] == run_id]
        assert len(episodes) == 2 and all(row['state'] == 'active' and row['archive'] is None for row in episodes)
        actions = [json.loads(row['action']) for row in journal['runtime_actions'] if row['run_id'] == run_id]
        assert len(actions) == 1 and actions[0]['kind'] == 'episode_child' and actions[0]['role'] == 'scientific_process'
        science_id = audit['saved_science_context']['episode_id']
        pending, = [row for row in journal['runtime_model_calls']
            if row['episode_id'] == science_id and row['response'] is None]
        assert pending['call_index'] == 0
        assert not [row for row in journal['runtime_observations'] if row['run_id'] == run_id]
        audit['pending_science_call'] = dict(episode_id=science_id, call_index=0)
    except BaseException as error:
        audit['exception'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        if store is not None:
            audit['journal'] = _rows(store)
            store.close()
        _write(audit_path, audit)














@pytest.fixture
def retained_capture_metadata_case(tmp_path, monkeypatch):
    import builtins
    import io
    import tempfile
    from gene_annotation_episode.episode_bindings import BindingContext
    from gene_annotation_episode.execution_contracts import canonical, digest

    selected = os.environ.get('HMMER_NATIVE_ORACLE_MACS2_PEAK_CAPTURE_PROFILE_PROOF')
    expected = os.environ.get('HMMER_NATIVE_ORACLE_MACS2_PEAK_CAPTURE_PROFILE_SHA256')
    if not selected or not expected:
        pytest.skip('requires an explicitly selected completed retained acquisition audit and SHA256')
    original = Path(selected).resolve()
    original_pin = _pin(original)
    assert re.fullmatch(r'[0-9a-f]{64}', expected) and original_pin['sha256'] == expected
    audit = json.loads(original.read_bytes())
    assert audit['completed'] is True and audit['archive'] is not None
    original_case = original.parent / 'owned-public-output-acquisition'
    original_files = [_pin(path) for path in sorted(original_case.rglob('*')) if path.is_file()]
    clone = tmp_path / 'owned-retained-capture-controls'
    shutil.copytree(original_case, clone)
    report = dict(original=original_pin, original_case_files=original_files, reads=[])

    def forbidden(*args, **kwargs):
        raise AssertionError('retained capture validation attempted new work, publication or a payload write')

    class NoDecisions:
        async def complete(self, *args, **kwargs):
            forbidden()

        async def release(self, episode_id):
            forbidden()

    for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
        monkeypatch.setattr(native_lifecycle, name, forbidden)
    for name in ('prepare_local_macs2_peak', 'run_macs2_peak', 'verify_software'):
        monkeypatch.setattr(native, name, forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    try:
        with Store(clone / 'state') as store:
            before = _rows(store)
            monkeypatch.setattr(store, 'put', forbidden)
            monkeypatch.setattr(store, 'artifact', forbidden)
            flow, tools = _assemble(store, clone, NoDecisions(), audit['configuration'])
            owner = flow.episode_bindings.for_role('results')
            local = owner.local_file_sources
            monkeypatch.setattr(tools, '_sequence_worker_async', forbidden)
            monkeypatch.setattr(tools, '_save', forbidden)
            monkeypatch.setattr(local, '_publish', forbidden)
            selected_file, = [row for row in audit['acquired'] if row['role'] == 'peaks_xls']
            reference = selected_file['source_ref']
            saved, = store.db.execute('SELECT receipt FROM runtime_execution_file_captures '
                'WHERE run_id=? AND source_ref=?', (audit['configuration']['run_id'], reference)).fetchall()
            control = json.loads(saved['receipt'])
            context = BindingContext(**control['context'])
            assert control['context']['assignment'] == audit['selected_assignment']
            wrapper_ref, = [reference for reference in audit['new_source_refs']
                if store.get(reference).get('provider') == 'episode.execution_result']
            wrapper_source = store.get(wrapper_ref)
            wrapper = json.loads(store.get_artifact(wrapper_source['artifact_ref']))
            assert control in wrapper['captured_files']
            directory = owner.directory / 'execution-results' / digest([context.run_id, context.episode_id])
            manifest = directory / 'assignment.json'
            expected_manifest = (canonical(dict(run_id=context.run_id, episode_id=context.episode_id,
                assignment=plain(context.assignment), scope=plain(context.scope))) + '\n').encode()
            assert manifest.read_bytes() == expected_manifest
            metadata_artifacts = {store.get(row['source_ref'])['request_ref'] for row in audit['acquired']}
            metadata_artifacts.add(wrapper_source['artifact_ref'])
            handoff = store.get(audit['received_handoff'])
            metadata_artifacts.update(handoff[key] for key in ('artifact_ref', 'request_ref'))
            for row in store.db.execute('SELECT file FROM runtime_macs2_peak_request_bindings WHERE run_id=?',
                    (context.run_id,)):
                metadata_artifacts.add(json.loads(row['file'])['artifact_ref'])
            assert not metadata_artifacts.intersection(row['artifact_ref'] for row in audit['acquired'])
            initial_files = [_pin(path) for path in sorted(clone.rglob('*'))
                if path.is_file() and not path.name.startswith('state.sqlite3')]
            target_reader = owner.job_progress_provider.targets
            read_native = target_reader._native
            get_artifact, path_open = store.get_artifact, Path.open
            builtin_open, io_open, os_open = builtins.open, io.open, os.open
            os_dup, os_close = os.dup, os.close

            def guarded_read(produce, *, data_artifacts=()):
                allowed = metadata_artifacts | set(data_artifacts)
                paths = {store.path / 'artifacts' / reference.removeprefix('artifact_')[:2]
                    / reference.removeprefix('artifact_') for reference in allowed}
                paths.update((clone / 'run').rglob('*.json'))
                paths.add(manifest)
                directories = {parent for path in paths for parent in path.parents}
                descriptors, opened, native_calls = {}, [], []

                def checked_path(path):
                    if isinstance(path, int):
                        assert path in descriptors, 'retained read used an untracked descriptor'
                        path = descriptors[path]
                    path = Path(os.fsdecode(path)).absolute()
                    assert path in paths, 'retained read reopened non-control or unselected data bytes: ' + str(path)
                    opened.append(str(path))

                def metadata_artifact(reference, *args, **kwargs):
                    assert reference in allowed, 'retained read opened unselected Artifact bytes'
                    return get_artifact(reference, *args, **kwargs)

                def metadata_path(path, *args, **kwargs):
                    checked_path(path)
                    mode = args[0] if args else kwargs.get('mode', 'r')
                    assert not any(flag in mode for flag in 'wax+'), 'retained read opened writable payload'
                    return path_open(path, *args, **kwargs)

                def metadata_builtin(path, *args, **kwargs):
                    checked_path(path)
                    mode = args[0] if args else kwargs.get('mode', 'r')
                    assert not any(flag in mode for flag in 'wax+'), 'retained read opened writable payload'
                    return builtin_open(path, *args, **kwargs)

                def metadata_io(path, *args, **kwargs):
                    checked_path(path)
                    mode = args[0] if args else kwargs.get('mode', 'r')
                    assert not any(flag in mode for flag in 'wax+'), 'retained read opened writable payload'
                    return io_open(path, *args, **kwargs)

                def metadata_fd(path, *args, **kwargs):
                    flags = args[0] if args else kwargs['flags']
                    assert flags & os.O_ACCMODE == os.O_RDONLY and not flags & (
                        os.O_CREAT | os.O_EXCL | os.O_TRUNC | os.O_APPEND), 'retained read attempted a write'
                    resolved = Path(os.fsdecode(path))
                    if not resolved.is_absolute():
                        parent = kwargs.get('dir_fd')
                        assert parent in descriptors, 'retained read used an untracked metadata directory'
                        resolved = descriptors[parent] / resolved
                    if flags & os.O_DIRECTORY:
                        assert resolved in directories, 'retained read opened a non-control directory'
                    else:
                        checked_path(resolved)
                    descriptor = os_open(path, *args, **kwargs)
                    descriptors[descriptor] = resolved
                    return descriptor

                def metadata_dup(descriptor):
                    assert descriptor in descriptors, 'retained read duplicated an untracked descriptor'
                    duplicate = os_dup(descriptor)
                    descriptors[duplicate] = descriptors[descriptor]
                    return duplicate

                def metadata_close(descriptor):
                    try:
                        return os_close(descriptor)
                    finally:
                        descriptors.pop(descriptor, None)

                def counted_native(*args, **kwargs):
                    native_calls.append(args[0])
                    return read_native(*args, **kwargs)

                store.db.execute('PRAGMA query_only=ON')
                try:
                    with monkeypatch.context() as patch:
                        patch.setattr(store, 'get_artifact', metadata_artifact)
                        patch.setattr(Path, 'open', metadata_path)
                        patch.setattr(builtins, 'open', metadata_builtin)
                        patch.setattr(io, 'open', metadata_io)
                        patch.setattr(os, 'open', metadata_fd)
                        patch.setattr(os, 'dup', metadata_dup)
                        patch.setattr(os, 'close', metadata_close)
                        patch.setattr(Path, 'mkdir', forbidden)
                        patch.setattr(tempfile, 'mkstemp', forbidden)
                        patch.setattr(target_reader, '_native', counted_native)
                        return produce()
                finally:
                    store.db.execute('PRAGMA query_only=OFF')
                    report['reads'].append(dict(native_authentications=len(native_calls),
                        opened=opened, allowed_data_artifacts=list(data_artifacts)))

            yield dict(store=store, flow=flow, owner=owner, local=local, audit=audit, report=report,
                source_ref=reference, wrapper_ref=wrapper_ref, control=control, context=context,
                wrapper=wrapper, scope=audit['configuration']['scope'], manifest=manifest,
                expected_manifest=expected_manifest, saved_receipt=saved['receipt'], read=guarded_read)
            assert _rows(store) == before
            assert [_pin(row['path']) for row in initial_files] == initial_files
            assert [str(path) for path in sorted(clone.rglob('*'))
                if path.is_file() and not path.name.startswith('state.sqlite3')] == [row['path'] for row in initial_files]
            report['clone_rows_receipts_and_files_unchanged'] = True
    except BaseException as error:
        report['exception'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        report['original_proof_unchanged'] = _pin(original) == original_pin
        report['original_case_unchanged'] = [_pin(row['path']) for row in original_files] == original_files
        _write(tmp_path / 'MACS2_RETAINED_CAPTURE_CONTROLS.json', report)
        assert report['original_proof_unchanged'] and report['original_case_unchanged']


