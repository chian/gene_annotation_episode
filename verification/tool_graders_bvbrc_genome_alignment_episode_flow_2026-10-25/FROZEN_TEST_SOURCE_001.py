"""Retained Mauve v4 through the selected GenomeAlignment Workflow.

Choices and loopback AppService/Workspace replies are controlled fixtures.
Production HTTP, custody, native parsing, numerical calculation, typed returns
and shared method_loop controllers run. No live BV-BRC, new aligner, configured
model, local scientific executable or HPC execution is claimed.
"""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import json
from pathlib import Path
import socket
import sys
import tempfile
from threading import Thread
from types import SimpleNamespace

import pytest
from method_loop.archive import iter_json
from method_loop.identities import EpisodeRef

from gene_annotation_episode import bvbrc_genome_alignment_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_genome_alignment_bundle_contracts import decode_reference, encode_reference
from gene_annotation_episode.bvbrc_genome_alignment_calculators import recalculate_genome_alignment_sheet
from gene_annotation_episode.bvbrc_genome_alignment_returns import genome_alignment_fact_sources
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_prompt import render_scientific_process_prompt
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from bvbrc_minhash_episode_fixture import PUBLICATION
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import form
from test_bvbrc_genome_alignment_calculators import IO_AND_PARSERS
from test_genome_alignment_saved_structure import scientific_barrier
from test_practical_runtime import selected
from test_public_search import Client


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'verification/tool_graders_bvbrc_genome_alignment_episode_flow_2026-10-25'
NATIVE = ROOT / ('verification/tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/'
    'retained_sources/mauve/testdata/small.mauve')
PREFIX = 'api.bvbrc_appservice.'
MEASUREMENTS = 'bvbrc_genome_alignment_measurements'
REQUIREMENTS = 'bvbrc_genome_alignment_requirements'
QUALIFICATIONS = 'bvbrc_genome_alignment_qualifications'
MANIFEST_UUID = '11111111-1111-1111-1111-111111111111'
OUTPUT_UUID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
MANIFEST_PATH = '/controlled/genome-alignment/manifest'
OUTPUT_PATH = '/controlled/genome-alignment/native'


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def member(index=0):
    return {'namespace': 'mauve_v4_member_0based', 'index': index}


def measurement(field, *, family='v4_coverage', **location):
    return {'kind': 'measurement', 'request_id': 'anchors',
        'metric': {'family': family, 'field': field, **(location or {'member': member()})}}


def declaration(fmt):
    return {'format': fmt, 'version': '4' if fmt == 'mauve_v4' else None,
        'mode': None, 'producer_source_ref': None, 'transformation_evidence': []}


def case_inputs(store):
    """Explicit original choices; no positive scientific/custody witness is made."""
    genomes = ['123.1', '456.2']
    request = {'version': 'bvbrc_appservice_request_v1', 'effect_contract': 'selected_api_effects_v1',
        'required_application_id': 'GenomeAlignment', 'parameters': {'genome_ids': genomes,
            'recipe': 'mauveAligner', 'seedWeight': 15, 'maxGappedAlignerLength': 10000,
            'output_path': '/controlled/genome-alignment', 'output_file': 'selected'},
        'start_parameters': {}, 'definition_inputs': [], 'input_bindings': [{
            'binding_id': 'original-genomes', 'parameter_pointer': '/genome_ids', 'kind': 'inline_parameter',
            'content': None, 'workspace_path': None, 'inline_value': deepcopy(genomes),
            'link_evidence': None, 'members': []}], 'workspace_targets': []}
    assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'selected-api',
        'service': 'bvbrc_appservice', 'request': request, 'endpoint': 'usable_handoff', 'constraints': {}}
    # The eight native segment widths are explicitly selected. The native
    # document is still parsed from acquired bytes by the production provider.
    segments = [(0, 0, 13), (0, 1, 10), (0, 2, 269), (0, 3, 13),
        (1, 0, 565), (2, 0, 304), (3, 0, 85), (4, 0, 1391)]
    plan = {'schema_version': 'bvbrc_genome_alignment_calculation_plan_v1', 'requests': [{
        'request_id': 'anchors', 'kind': 'mauve_v4_segments', 'document_slot_id': 'v4',
        'use_inputs': False, 'selection': {'schema_version': 'mauve_v4_selection_v1',
            'population_id': 'retained-v4-all-observed-explicit-segments',
            'members': [member(), member(1)],
            'pairs': [{'member_a': member(), 'member_b': member(1)}],
            'segments': [{'interval_index': interval, 'segment_index': segment,
                'column_ranges_0based_half_open': [[0, width]]} for interval, segment, width in segments],
            'case_policy': 'uppercase', 'denominator': 'native_declared_length',
            'population_scope': 'all_observed_document_segments', 'evidence': []}}]}
    parameters = {'schema_version': 'bvbrc_genome_alignment_parameters_v1',
        'analysis_id': 'retained-v4-workflow', 'document_slots': [{
            'slot_id': 'v4', 'role': 'genome_alignment_primary', 'source_ref': None,
            'raw_artifact_ref': None, 'reader': {'format': 'mauve_v4', 'encoding': 'ascii'}}],
        'calculation_plan': plan}
    fields = {'coverage': measurement('coverage_fraction'),
        'zero_gaps': measurement('selected_gap_count', family='v4_member', interval_index=0,
            segment_index=0, member=member()),
        'missing': {'kind': 'missing_requirements', 'scope': 'all', 'request_id': None},
        'qualifications': {'kind': 'qualifications', 'scope': 'all', 'request_id': None}}
    selector = {'version': 'bvbrc_appservice_result_selector_v1', 'endpoint': 'requested_projection',
        'requirements': [{'requirement_id': 'manifest', 'role': 'task_manifest', 'required': False,
            'declared_format': declaration('json'), 'producer_rule_evidence': None, 'exact_object': None},
            {'requirement_id': 'native', 'role': 'genome_alignment_primary', 'required': True,
            'declared_format': declaration('mauve_v4'), 'producer_rule_evidence': None, 'exact_object': None}],
        'adapter': {'adapter_id': adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION,
            'parameters': parameters}, 'requested_schema': adapter.requested_form_schema(fields),
        'supplied_metadata': [], 'supplied_contents': [], 'supplied_capabilities': []}
    raw = NATIVE.read_bytes()
    provenance = {'kind': 'retained_native_fixture_provenance', 'new_native_execution': False,
        'sources': [{'path': str(NATIVE.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest(),
            'byte_count': len(raw)}], 'association_with_controlled_task_is_fixture': True}
    material = store.register_material(data=canonical(provenance).encode(),
        name='retained-v4-provenance.json', format='text', use='evidence')
    manifest = {'id': '123', 'app': {'id': 'GenomeAlignment'}, 'parameters': deepcopy(request['parameters']),
        'success': 1, 'output_files': [[OUTPUT_PATH, OUTPUT_UUID]]}
    return SimpleNamespace(request=request, assignment=assignment, selector=selector, fields=fields,
        raw=raw, manifest=manifest, manifest_raw=canonical(manifest).encode(), material=material,
        provenance=provenance, expected={'coverage': 690 / 693, 'zero_gaps': 0})


@contextmanager
def protocol_server(case):
    """Actual HTTP, controlled native protocol records and retained native body."""
    calls, errors = [], []
    metadata = ['manifest', 'job_result', '/controlled/genome-alignment', '2026-10-25T12:00:00',
        MANIFEST_UUID, 'controlled-fixture', len(case.manifest_raw), {}, {}, 'w', 'n', '']

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, data, content_type):
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            try:
                raw = self.rfile.read(int(self.headers['Content-Length']))
                command = json.loads(raw)
                calls.append({'method': 'POST', 'path': self.path, 'rpc': command,
                    'body_sha256': hashlib.sha256(raw).hexdigest()})
                method, params = command['method'], command['params']
                if method == 'AppService.start_app2':
                    assert self.path == '/app'
                    assert params == ['GenomeAlignment', case.request['parameters'], {}]
                    result = {'id': '123', 'application_id': 'GenomeAlignment', 'state_code': 'Q'}
                elif method == 'AppService.query_tasks':
                    assert self.path == '/app' and params == [['123']]
                    result = {'123': {'id': '123', 'application_id': 'GenomeAlignment', 'state_code': 'C'}}
                elif method == 'Workspace.get':
                    assert self.path == '/workspace' and params == [{'objects': [MANIFEST_UUID], 'metadata_only': 1}]
                    result = [[metadata]]
                else:
                    assert method == 'Workspace.get_download_url' and self.path == '/workspace'
                    obj, = params[0]['objects']
                    assert obj in (MANIFEST_PATH, OUTPUT_PATH, MANIFEST_UUID, OUTPUT_UUID)
                    result = [url + ('/download/manifest' if obj in (MANIFEST_PATH, MANIFEST_UUID) else '/download/native')]
                self.send(canonical({'version': '1.1', 'id': command['id'], 'result': [result]}).encode(),
                    'application/json')
            except Exception as error:
                errors.append(repr(error))
                self.send_error(500)

        def do_GET(self):
            try:
                assert 'Range' not in self.headers
                payloads = {'/app/task_info/123/job_result_id': (MANIFEST_UUID + '\n').encode(),
                    '/download/manifest': case.manifest_raw, '/download/native': case.raw}
                raw = payloads[self.path]
                calls.append({'method': 'GET', 'path': self.path, 'byte_count': len(raw),
                    'sha256': hashlib.sha256(raw).hexdigest()})
                self.send(raw, 'application/octet-stream')
            except Exception as error:
                errors.append(repr(error))
                self.send_error(500)

    host = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    url = f'http://127.0.0.1:{host.server_port}'
    thread = Thread(target=host.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    thread.start()
    try:
        yield SimpleNamespace(url=url, calls=calls, errors=errors, port=host.server_port)
    finally:
        host.shutdown()
        host.server_close()
        thread.join()


def child(role, assignment, scope, schema):
    return {'selection': {'kind': 'episode_child', 'role': role,
        'goal': 'Measure the selected retained genome alignment coverage and preserve its source qualifications',
        'scope': scope, 'purpose': 'Return original requested GenomeAlignment numerical facts, denominators and missing source relationships',
        'assignment': deepcopy(assignment), 'schema_json': json.dumps(schema), 'initial_report_json': '{}'}, 'report_update': {}}


def run_identity():
    # This finite search chooses an audit identity, not an episode turn limit.
    # Native is action6; the earlier manifest publication is action4.
    for ordinal in range(100):
        run_id = 'genome-alignment-composed-v4-' + str(ordinal)
        path = (('annotation', 'root'), ('scientific_process', 'child_0'), ('results', 'child_2'))
        episode_id = EpisodeRef(run_id, path).episode_id
        if digest(f'{run_id}:{episode_id}:6') < digest(f'{run_id}:{episode_id}:4'):
            return run_id
    raise AssertionError('No reverse-hash audit identity found')


def loaded_source_paths():
    paths = set()
    for module in tuple(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if not isinstance(name, str):
            continue
        path = Path(name)
        if path.suffix == '.pyc':
            path = Path(importlib.util.source_from_cache(str(path)))
        path = path.resolve()
        if path.suffix == '.py' and path.is_relative_to(ROOT) and path.relative_to(ROOT).parts[0] != '.venv':
            paths.add(path)
    return paths


def explicit_source_paths():
    from gene_annotation_episode.scientific_process_episodes import _IMPLEMENTATION_FILES
    package = ROOT / 'gene_annotation_episode'
    paths = {package / name for name in (*adapter._DEPENDENCIES, *_IMPLEMENTATION_FILES)}
    paths.update(path for path in PUBLICATION.rglob('*') if path.is_file())
    paths.update((Path(__file__).resolve(), NATIVE, package / 'execution_service_setup.py'))
    specs = package / 'bvbrc_application_specs'
    manifest = specs / 'MANIFEST.json'
    spec = json.loads(manifest.read_text())['GenomeAlignment']
    paths.update((manifest, specs / spec['original_file'], specs / spec['derived_file']))
    return paths


def source_hashes(extra=()):
    paths = {path for folder in ('gene_annotation_episode', 'method_loop', 'tests')
        for path in (ROOT / folder).rglob('*') if path.is_file() and path.suffix in {'.py', '.json'}}
    paths.update(extra)
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths) if path.is_file()}


def source_guard(before, after, used_paths):
    used = {str(path.relative_to(ROOT)) for path in used_paths}
    changed = {name for name in before if before[name] != after.get(name)}
    added = set(after) - set(before)
    return {'used_paths': sorted(used), 'used_without_before_hash': sorted(used - set(before)),
        'used_changes': sorted(changed & used), 'outside_used_changes': sorted(changed - used),
        'outside_used_additions': sorted(added - used), 'all_changes': sorted(changed), 'all_additions': sorted(added)}


def require_source_guard(guard):
    assert not guard['used_without_before_hash'], 'A used source lacks its original before hash'
    assert not guard['used_changes'], 'A used source changed or disappeared during this run'


@pytest.fixture(scope='module')
def genome_run():
    (EVIDENCE / 'runs').mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='mauve-v4-', dir=EVIDENCE / 'runs'))
    explicit, initially_loaded = explicit_source_paths(), loaded_source_paths()
    before = source_hashes(explicit | initially_loaded)
    write(directory / 'SOURCE_HASHES_BEFORE.json', before)
    write(directory / 'SOURCE_CLOSURE_INPUTS_BEFORE.json', {
        'explicit': sorted(str(path.relative_to(ROOT)) for path in explicit),
        'loaded_modules': sorted(str(path.relative_to(ROOT)) for path in initially_loaded)})
    provenance = {'scope': 'actual composed Workflow and loopback HTTP with unchanged retained Mauve v4 bytes',
        'configured_model': False, 'live_bvbrc': False, 'new_native_scientific_execution': False, 'hpc': False,
        'production_overrides': [], 'controlled_fixtures': ['decision provider', 'loopback native protocol responses',
            'caller scientific credit zero'], 'python_executable': sys.executable, 'python_version': sys.version,
        'controller': {'class': 'YieldController', 'cost': .1, 'parameters': YieldParameters().as_record(),
            'scientific_estimator': 'unchanged estimate_score_yield', 'resource_endpoint': 'existing practical exact-zero'}}
    write(directory / 'PROVENANCE.json', {**provenance, 'status': 'started'})
    with pytest.MonkeyPatch.context() as patch, Store(directory / 'state') as store:
        target, = store.create_problem(raw_sequence='AACGT', molecule='dna')['subject_refs']
        scope = {'subject_refs': [target]}
        case = case_inputs(store)
        original_case = deepcopy({'request': case.request, 'selector': case.selector})
        write(directory / 'selected-inputs.json', {**original_case, 'provenance': case.provenance})
        (directory / 'native-v4.mauve').write_bytes(case.raw)
        (directory / 'controlled-job-result.json').write_bytes(case.manifest_raw)
        with protocol_server(case) as native:
            original_connect = socket.socket.connect
            def controlled_connect(sock, address):
                if sock.family in (socket.AF_INET, socket.AF_INET6):
                    assert address[0] == '127.0.0.1' and address[1] == native.port, address
                return original_connect(sock, address)
            patch.setattr(socket.socket, 'connect', controlled_connect)
            def forbidden(*_, **__):
                raise AssertionError('Workflow fixture attempted new native execution')
            patch.setattr('subprocess.run', forbidden)
            patch.setattr('subprocess.Popen', forbidden)
            pin = adapter.implementation_sha256()
            config = {'kind': 'api', 'service': 'bvbrc_appservice', 'execution_contract': 'bvbrc_appservice_execution_v1',
                'endpoints': {'AppService': native.url + '/app', 'Workspace': native.url + '/workspace'},
                'scientific_adapters': [{'adapter_id': adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION,
                    'implementation_sha256': pin}]}
            descriptors = genome_alignment_fact_sources()
            handoff_form, result_form = form('execution_handoff_refs'), form('execution_result_refs')
            requested_families = {'numbers': MEASUREMENTS, 'missing': REQUIREMENTS, 'qualifications': QUALIFICATIONS}
            for name, family in requested_families.items():
                result_form['properties'][name] = deepcopy(descriptors[family]['report_schema'])
                result_form['required'].append(name)
            parent_form = {'type': 'object', 'additionalProperties': False,
                'properties': {name: deepcopy(result_form['properties'][name]) for name in requested_families},
                'required': list(requested_families)}
            launch = launch_assignment({'selected-api': case.assignment})
            factory = ExecutionServiceFactory({'selected-api': config}, {}, 2, 3, .5)
            tools = ToolRegistry(store, clients=Client())
            run_id, run_directory = run_identity(), directory / 'run'
            application = factory(store, run_id=run_id, directory=run_directory,
                tool_registry=tools, tool_catalog=tools.catalog())
            descriptor = prepare_scientific_binding(run_directory=run_directory, source_directory=PUBLICATION,
                tool_catalog=tools.catalog(), child_roles=('scientific_process', 'launch', 'results'),
                resource_catalogs=application.resource_tool_catalogs)
            library = ScientificProcessLibrary(run_directory / 'scientific-process-library')
            selected_tools = [{'name': 'bvbrc.genome_alignment', 'resources': 'api'},
                {'name': 'material.parse', 'resources': 'local'}]

            class Choices:
                def __init__(self):
                    self.counts, self.calls, self.partial = {}, [], []
                    self.task_info_ref = self.manifest_object = self.manifest_receipt_ref = None

                def last(self, episode_id):
                    row = store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? '
                        'AND result IS NOT NULL ORDER BY decision_index DESC LIMIT 1', (run_id, episode_id)).fetchone()
                    return json.loads(row['result'])['result']

                async def complete(self, episode_id, role, instructions, current, schema):
                    assert current.get('feedback') is None, current.get('feedback')
                    self.counts[episode_id] = count = self.counts.get(episode_id, 0) + 1
                    self.calls.append((episode_id, role, instructions, deepcopy(current)))
                    execution = current.get('execution_assignment', {})
                    version = execution.get('version')
                    if version == 'execution_launch_assignment_v1':
                        assert count == 1 and execution == launch
                        return child('launch_api', case.assignment, scope, handoff_form)
                    if version == 'api_service_assignment_v1':
                        assert execution == case.assignment
                        if count == 1:
                            return selected(PREFIX + 'prepare', {'definition': {'kind': 'packaged',
                                'required_application_id': 'GenomeAlignment'}})
                        assert count == 2, 'Validated original handoff should have closed the API assignment'
                        return selected(PREFIX + 'submit', {'preparation_receipt_ref': self.last(episode_id)['support_receipt_ref'],
                            'input_evidence_refs': []})
                    if version == 'execution_results_assignment_v1':
                        assert execution['selector'] == case.selector
                        if count == 1:
                            return selected(PREFIX + 'status', {'handoff_ref': execution['handoff_ref']})
                        if count == 2:
                            return selected(PREFIX + 'task_info', {'handoff_ref': execution['handoff_ref'], 'file': 'job_result_id'})
                        if count == 3:
                            self.task_info_ref = self.last(episode_id)['support_receipt_ref']
                            return selected(PREFIX + 'workspace_metadata', {'objects': [{
                                'kind': 'task_info_object', 'receipt_ref': self.task_info_ref}], 'options': {}})
                        if count == 4:
                            self.manifest_object = {'kind': 'receipt_row',
                                'receipt_ref': self.last(episode_id)['support_receipt_ref'], 'row_pointer': '/result/0/0'}
                            return selected(PREFIX + 'download_capability', {'objects': [self.manifest_object],
                                'generation': 0, 'predecessor_receipt_ref': None})
                        if count == 5:
                            return selected(PREFIX + 'download', {'object': self.manifest_object,
                                'capability': {'kind': 'acquired', 'receipt_ref': self.last(episode_id)['support_receipt_ref'], 'input_index': 0},
                                'byte_range': None, 'requirement_ids': ['manifest'], 'role': 'task_manifest',
                                'declared_format': declaration('json')})
                        if count == 6:
                            outcome = self.last(episode_id)
                            self.manifest_receipt_ref = outcome['support_receipt_ref']
                            body = api.read_result(outcome['source_ref'], scope)
                            self.partial.append(deepcopy(body))
                            write(directory / 'partial-manifest.json', body)
                            assert body['publication']['completion_proof'] is None
                            return selected(PREFIX + 'download_capability', {'objects': [{
                                'kind': 'manifest_member', 'manifest_receipt_ref': self.manifest_receipt_ref, 'output_index': 0}],
                                'generation': 0, 'predecessor_receipt_ref': None})
                        assert count == 7, 'Original requested numerical result should close without an extra turn'
                        return selected(PREFIX + 'download', {'object': {'kind': 'manifest_member',
                            'manifest_receipt_ref': self.manifest_receipt_ref, 'output_index': 0},
                            'capability': {'kind': 'acquired', 'receipt_ref': self.last(episode_id)['support_receipt_ref'], 'input_index': 0},
                            'byte_range': None, 'requirement_ids': ['native'], 'role': 'genome_alignment_primary',
                            'declared_format': declaration('mauve_v4')})
                    if 'scientific_process' in current:
                        assert current['scientific_process']['selection']['child_tool_info'] == selected_tools
                        if count == 1:
                            return selected('material.parse', {'material_ref': case.material['id'], 'format': 'text'})
                        if count == 2:
                            return child('launch', launch, scope, handoff_form)
                        if count == 3:
                            handoff, = current['child_reports'][-1]['references']
                            return child('results', {'version': 'execution_results_assignment_v1',
                                'handoff_ref': handoff, 'selector': case.selector}, scope, result_form)
                        if count == 4:
                            delivery = current['report_deliveries'][-1]
                            return {'selection': {'kind': 'redeliver_report', 'delivery_ref': delivery['delivery_ref'],
                                'purpose': 'Receive the same original requested facts from the saved closed results child',
                                'schema_json': json.dumps(result_form)}, 'report_update': {}}
                        return selected('material.parse', {'material_ref': case.material['id'], 'format': 'text'})
                    if count == 1:
                        scientific = {'selection': {'version': 'scientific_process_selection_v3',
                            'evidence_axis': library.reference('A101'), 'thought_pattern': library.reference('P01'),
                            'child_tool_info': deepcopy(selected_tools)}, 'evidence_refs': [target],
                            'constraints': {'preserve_original_genome_occurrences_and_native_populations': True},
                            'context': {'supplied_sequence': 'AACGT', 'molecule': 'dna', 'complete': True,
                                'label_is_public_identity': False, 'supplied_material_refs': [case.material['id']]}}
                        return child('scientific_process', scientific, scope, parent_form)
                    return {'selection': {'kind': 'wait', 'condition': {'version': 'event_condition_v1',
                        'events': [], 'reconsider_at': datetime.now(timezone.utc).isoformat()}}, 'report_update': {}}

                async def release(self, episode_id):
                    pass

            choices = Choices()
            workflow = Workflow(store, tools, choices, run_directory, run_id,
                controller_factory=lambda path, initial: YieldController(str(path), initial, .1, YieldParameters()),
                project_credit=lambda *_: 0, episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
                role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider,
                annotation_child_roles=('scientific_process',), episode_record_receipts=True, initial_known_record_refs=[])
            api = workflow.episode_bindings.for_role('results').api_execution
            binding_snapshot = {'factory': factory.as_record(), 'service_configuration': deepcopy(config),
                'configured_episode_bindings': plain((descriptor, *application.episode_binding_descriptors)),
                'actual_scientific_binding': workflow.scientific_process_binding.as_record(),
                'actual_api_configuration': deepcopy(api.configuration)}
            write(directory / 'CONFIGURED_BINDINGS.json', binding_snapshot)
            episode = workflow.build('annotation', 'root', 'Measure retained genome-alignment correspondence with qualified source coverage', scope)

            async def execute():
                record = await episode.run_async(workflow.context)
                await episode.build_result(record)
                return record

            try:
                record = asyncio.run(execute())
            except BaseException as error:
                write(directory / 'WORKFLOW_FAILURE.json', {'type': type(error).__name__, 'message': str(error),
                    'provider_call_counts': choices.counts, 'http_calls': native.calls, 'protocol_errors': native.errors})
                used = explicit | initially_loaded | loaded_source_paths()
                after = source_hashes(used)
                write(directory / 'SOURCE_HASHES_FAILED.json', after)
                write(directory / 'SOURCE_GUARD_FAILED.json', source_guard(before, after, used))
                raise
            archive = json.loads(''.join(iter_json(record.as_record())))
            science = archive['units'][0]['child']
            launch_record, results = science['units'][1]['child'], science['units'][2]['child']
            api_record = launch_record['units'][0]['child']
            returned = json.loads(workflow.journal.row('runtime_forms', results['episode_id'])['form'])
            forwarded = json.loads(workflow.journal.row('runtime_forms', science['episode_id'])['form'])
            final_ref, = {row['source_ref'] for row in returned['numbers']}
            body = api.read_result(final_ref, scope)
            saved = body['publication']['adapter_result']
            sheet = json.loads(store.get_artifact(saved['sheet_content']['artifact_ref']))
            components = json.loads(store.get_artifact(saved['components_content']['artifact_ref']))
            for name, value in (('archive', archive), ('results-return', returned), ('scientific-return', forwarded),
                    ('publication', body), ('native-http-calls', native.calls), ('sheet', sheet), ('components', components)):
                write(directory / (name + '.json'), value)
            for index, (episode_id, role, instructions, current) in enumerate(choices.calls):
                write(directory / f'decision-{index}.json', {'episode_id': episode_id, 'role': role,
                    'instructions': instructions, 'context': current})
                if 'scientific_process' in current:
                    (directory / f'scientific-presentation-{index}.txt').write_text(render_scientific_process_prompt(current, instructions))
            used = explicit | initially_loaded | loaded_source_paths()
            after = source_hashes(used)
            guard = source_guard(before, after, used)
            write(directory / 'SOURCE_HASHES_AFTER.json', after)
            write(directory / 'SOURCE_GUARD_WORKFLOW_CLOSED.json', guard)
            write(directory / 'PROVENANCE.json', {**provenance, 'status': 'workflow_closed', 'adapter_pin': pin,
                'scientific_binding_pin': workflow.scientific_process_binding.as_record()['implementation_sha256'],
                'expected_measurements': case.expected, 'source_guard': guard,
                'presentation_scope': 'Scientific process uses detailed TASK/curt STEERING; other provider contexts retain existing JSON presentation'})
            require_source_guard(guard)
            assert adapter.implementation_sha256() == pin
            assert workflow.scientific_process_binding.as_record() == binding_snapshot['actual_scientific_binding']
            assert api.configuration == binding_snapshot['actual_api_configuration']
            assert original_case == {'request': case.request, 'selector': case.selector}
            assert not native.errors
            yield SimpleNamespace(directory=directory, store=store, case=case, native=native, workflow=workflow,
                api=api, choices=choices, archive=archive, science=science, launch=launch_record, api_record=api_record,
                results=results, returned=returned, forwarded=forwarded, body=body, sheet=sheet, components=components,
                final_ref=final_ref, scope=scope, result_form=result_form, parent_form=parent_form, episode=episode,
                library=library, selected_tools=selected_tools, pin=pin, requested_families=requested_families)
            used |= loaded_source_paths()
            final_sources = source_hashes(used)
            final_guard = source_guard(before, final_sources, used)
            write(directory / 'SOURCE_HASHES_AFTER_TESTS.json', final_sources)
            write(directory / 'SOURCE_GUARD_AFTER_TESTS.json', final_guard)
            require_source_guard(final_guard)
            assert adapter.implementation_sha256() == pin
            assert workflow.scientific_process_binding.as_record() == binding_snapshot['actual_scientific_binding']
            assert api.configuration == binding_snapshot['actual_api_configuration']


def test_selected_library_three_slots_and_real_child_http_route(genome_run):
    r = genome_run
    binding = r.workflow.scientific_process_binding
    context = r.api.appservice.custody.context(r.science['episode_id'])
    binding.validate_context(context)
    catalog = r.workflow.services.tool_information_catalog(r.scope)
    information = binding.tool_library.resolve_tool_info(r.selected_tools, catalog)
    assert plain(context.assignment)['selection'] == {'version': 'scientific_process_selection_v3',
        'evidence_axis': r.library.reference('A101'), 'thought_pattern': r.library.reference('P01'),
        'child_tool_info': information}
    contract = next(row for row in binding.tool_library.resolve_invocations(r.selected_tools, catalog)
        if row['name'] == 'bvbrc.genome_alignment')
    assert contract['invocation_route'] == {'kind': 'commission', 'routes': [
        {'entry_role': 'launch', 'resource_id': 'selected-api', 'resource_role': 'launch_api'},
        {'entry_role': 'results', 'resource_id': 'selected-api', 'resource_role': 'results'}]}
    direct = {row['name'] for row in binding.catalog(context)}
    assert 'material.parse' in direct and not any(name.startswith('bvbrc.') or name.startswith(PREFIX) for name in direct)
    assert r.workflow.catalog(r.scope, source=r.episode.source) == []
    assert r.api.services['selected-api'].scientific_adapters[(adapter.ADAPTER_ID, adapter.ADAPTER_VERSION)][0] is adapter
    assert r.api.appservice.custody.possession(context, r.case.material['source_ref']) == 'own_completed_action'
    owner = r.api.appservice.custody.original_job_owner(r.api.appservice.custody.context(r.api_record['episode_id']))
    assert owner['launch_episode_id'] == r.launch['episode_id']
    assert owner['parent_commission_operation_key'] == f'{r.workflow.run_id}:{context.episode_id}:1'
    assert r.body['bundle']['original_task']['submitted_parameters'] == r.case.request['parameters']
    assert r.body['bundle']['input_bindings'] == r.case.request['input_bindings']
    assert [call['rpc']['method'] for call in r.native.calls if call['method'] == 'POST'] == [
        'AppService.start_app2', 'AppService.query_tasks', 'Workspace.get',
        'Workspace.get_download_url', 'Workspace.get_download_url']
    assert [call['path'] for call in r.native.calls if call['method'] == 'GET'] == [
        '/app/task_info/123/job_result_id', '/download/manifest', '/download/native']


def test_detailed_scientific_task_and_curt_steering_on_every_iteration(genome_run):
    r = genome_run
    binding = r.workflow.scientific_process_binding
    catalog = r.workflow.services.tool_information_catalog(r.scope)
    contract = next(row for row in binding.tool_library.resolve_invocations(r.selected_tools, catalog)
        if row['name'] == 'bvbrc.genome_alignment')
    scientific = [(index, instructions, current) for index, (_, _, instructions, current) in enumerate(r.choices.calls)
        if 'scientific_process' in current]
    assert len(scientific) == r.choices.counts[r.science['episode_id']]
    for index, instructions, current in scientific:
        task, steering = (r.directory / f'scientific-presentation-{index}.txt').read_text().split('\n\nSTEERING', 1)
        assert task.startswith('TASK\n') and contract['instructions'] in task
        assert contract['instructions'] not in steering
        assert current['scientific_process']['evidence_axis']['investigation_instructions'] in task
        thought = current['scientific_process']['thought_pattern']
        for field in ('description', 'use_when', 'boundary'):
            if thought.get(field):
                assert thought[field] in task
        for field in ('live_alternatives', 'decision_guidance'):
            assert all(value in task for value in thought.get(field, []))
        assert 'Own completed actions' in steering
        if current.get('action_yields', {}).get('rows'):
            assert 'Total signed yield' in steering and 'Expected next yield' in steering and 'Uncertainty' in steering
        for forbidden in (r.final_ref, r.pin, r.science['episode_id'], r.results['episode_id'],
                canonical(r.sheet), canonical(r.components), r.case.raw.decode('ascii'), 'SOURCE_HASHES_BEFORE'):
            assert forbidden not in task + steering
    # Resource instructions recur in the actual provider calls. The existing
    # provider's non-scientific JSON presentation is not mislabeled as a newly
    # implemented TASK/STEERING template by this test.
    for role, text in (('launch', 'Choose which permitted concrete execution request'),
            ('launch_api', 'Carry out the assigned work through bvbrc_appservice'),
            ('results', 'Acquire the original selected execution results')):
        calls = [instructions for _, actual_role, instructions, _ in r.choices.calls if actual_role == role]
        assert calls and all(text in instructions for instructions in calls)


def test_retained_native_sheet_numbers_and_exact_both_parent_returns(genome_run):
    r = genome_run
    numbers = {decode_reference(row['field'])[2]: row['value']['value'] for row in r.returned['numbers']}
    assert {name: row['value'] for name, row in numbers.items()} == pytest.approx(r.case.expected)
    fraction = numbers['coverage']
    assert (fraction['numerator'], fraction['denominator'], fraction['unit'], fraction['state']) == (690, 693, 'fraction', 'available')
    assert numbers['zero_gaps']['value'] == 0 and numbers['zero_gaps']['state'] == 'available'
    assert r.returned['completed'] is True
    assert r.forwarded == {name: r.returned[name] for name in r.requested_families}
    assert r.body['publication_inputs']['selector'] == r.case.selector
    assert r.body['publication_inputs']['adapter_implementation_sha256'] == r.pin
    assert r.body['publication']['completion_proof'] is not None
    assert r.sheet['components'] == r.components
    native, = r.sheet['data']['parsed_artifacts']
    assert native['format'] == 'mauve_v4' and len(native['document']['intervals']) == 5
    artifact = next(row for row in r.body['bundle']['artifacts'] if row['role'] == 'genome_alignment_primary')
    assert r.store.get_artifact(artifact['raw_artifact_ref']) == r.case.raw == NATIVE.read_bytes()
    assert (artifact['sha256'], artifact['byte_count']) == (hashlib.sha256(r.case.raw).hexdigest(), len(r.case.raw))
    assert artifact['transfer']['body_complete'] and artifact['transfer']['object_complete'] == 'yes'
    assert artifact['task_association']['kind'] == 'manifest_member'
    assert artifact['task_association']['byte_version_status'] == 'unknown'
    assert r.sheet['data']['associations']['artifacts'][0]['state'] == 'bound'
    inputs = r.sheet['data']['inputs']
    assert inputs['original_maps'] == [] and inputs['xmfa_source_inputs'] is None
    assert inputs['invocation']['observed_argv'] is None
    assert inputs['genome_census_state'] == 'unknown'
    assert [row['genome_id'] for row in inputs['genome_occurrences']] == ['123.1', '456.2']
    assert [row['input_binding_id'] for row in inputs['genome_occurrences']] == ['original-genomes'] * 2
    value = r.components['outcomes'][0]['measurement']['value']
    coverage = value['coverage'][0]
    assert coverage['known_union_intervals'] == [[0, 578], [581, 693]]
    assert coverage['complement_intervals'] == [[578, 581]]
    assert coverage['denominator_kind'] == 'native_declared_length'
    assert coverage['denominator_bases']['value'] == 693 and coverage['denominator_bases']['origin'] == 'native_observation'
    assert coverage['population_state'] == 'complete_selected'
    assert value['member_segments'][0]['selected_canonical_count']['state'] == 'missing'
    saved = r.body['publication']['adapter_result']
    assert saved['missing_requirements'] and saved['diagnostics'] and r.returned['missing'] and r.returned['qualifications']
    for child_record, parent_record, expected in ((r.results, r.science, r.returned), (r.science, r.archive, r.forwarded)):
        attempt = r.store.db.execute('SELECT parent_episode_id,form,failure FROM runtime_report_attempts '
            'WHERE run_id=? AND child_episode_id=? ORDER BY decision_index LIMIT 1',
            (r.workflow.run_id, child_record['episode_id'])).fetchone()
        assert attempt['parent_episode_id'] == parent_record['episode_id'] and attempt['failure'] is None
        assert json.loads(attempt['form']) == expected
        context = r.api.appservice.custody.context(parent_record['episode_id'])
        received = {row['fact_source']: row['facts'] for row in r.api.genome_alignment_returns.received_context(context)}
        assert received == {family: expected[name] for name, family in r.requested_families.items()}
        assert r.api.appservice.custody.possession(context, r.final_ref) == 'admitted_return'
    write(r.directory / 'NUMERICAL_RETURN_CHECK.json', {'numbers': numbers,
        'native_union_intervals': coverage['known_union_intervals'], 'original_source_mapping': 'missing',
        'retained_missing_requirements': saved['missing_requirements'], 'qualifications': saved['diagnostics']})


def test_exact_zero_endpoint_and_one_observation_per_completed_own_action(genome_run):
    r = genome_run
    for record in (r.archive, r.science, r.launch, r.api_record, r.results):
        redelivery = int(record is r.science)
        assert record['units_consumed'] + redelivery == r.choices.counts[record['episode_id']]
        for table in ('runtime_actions', 'runtime_observations', 'runtime_model_calls'):
            expected = record['units_consumed'] + (redelivery if table == 'runtime_model_calls' else 0)
            assert r.store.db.execute('SELECT count(*) FROM ' + table + ' WHERE run_id=? AND episode_id=?',
                (r.workflow.run_id, record['episode_id'])).fetchone()[0] == expected
    attempts = r.store.db.execute('SELECT form FROM runtime_report_attempts WHERE run_id=? AND child_episode_id=?',
        (r.workflow.run_id, r.results['episode_id'])).fetchall()
    assert len(attempts) == 2 and all(json.loads(row['form']) == r.returned for row in attempts)
    assert (r.api_record['units_consumed'], r.launch['units_consumed'], r.results['units_consumed']) == (2, 1, 7)
    for record in (r.launch, r.api_record, r.results):
        assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert record['units'][-1]['controller_step']['marginal_credit'] > 0
        saved = r.store.db.execute('SELECT data FROM runtime_estimation_contexts WHERE run_id=? AND episode_id=? '
            'ORDER BY decision_index DESC LIMIT 1', (r.workflow.run_id, record['episode_id'])).fetchone()
        proof = json.loads(saved[0])['practical_completion']
        assert proof['action_index'] == proof['unit_ref']['unit_index'] == record['units_consumed'] - 1
    for record in (r.archive, r.science):
        assert all(unit['controller_step']['marginal_credit'] == 0 for unit in record['units'])
        estimate = record['controller_state']['estimate']
        assert estimate['provenance']['estimator'] == 'completed_signed_score_preferential_yield_v1'
        assert estimate['expected_next_gain']['upper'] <= .1
    assert r.store.count('annotation') == r.store.count('observation') == 0


def test_numeric_action_order_preserves_partial_original_publication(genome_run):
    r = genome_run
    early, = r.choices.partial
    assert r.api.read_result(early['reference'], r.scope) == early
    assert early['status'] == 'partial' and early['publication']['completion_proof'] is None
    assert early['publication']['adapter_result']['facts']['coverage']['state'] == 'missing'
    assert any(row['requirement_id'] == 'native' and row['role'] == 'genome_alignment_primary'
        and row['reason_code'] == 'output_bytes_missing' for row in early['bundle']['missing_requirements'])
    first_key, final_key = early['publication']['origin']['operation_key'], r.body['publication']['origin']['operation_key']
    assert (int(first_key.rsplit(':', 1)[1]), int(final_key.rsplit(':', 1)[1])) == (4, 6)
    assert digest(final_key) < digest(first_key)
    own = r.api.genome_alignment_returns.facts(r.api.appservice.custody.context(r.results['episode_id']), r.result_form)
    assert own == {family: r.returned[name] for name, family in r.requested_families.items()}
    assert all(row['source_ref'] == r.final_ref for row in r.forwarded['numbers'])


def test_explicit_recalculation_and_saved_replay_forbid_new_science(genome_run, monkeypatch):
    r = genome_run
    tables = ('runtime_actions', 'runtime_model_calls', 'runtime_observations', 'runtime_report_attempts', 'runtime_record_receipts')
    counts = {table: r.store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] for table in tables}
    calls, original_sheet = deepcopy(r.native.calls), deepcopy(r.sheet)
    def forbidden(*_, **__):
        raise AssertionError('Saved result attempted acquisition, native parsing or a new native process')
    # Recalculation is a separate operation using saved data and changed plan.
    # Native parsing and acquisition already fail before that operation.
    for name, attributes in {'mauve_v4_formats': ('parse_mauve_v4',),
            'mauve_backbone_formats': ('parse_mauve_backbone', 'parse_mauve_bbcols'),
            'xmfa_formats': ('parse_mauve_xmfa',),
            'bvbrc_genome_alignment_bundle_resolution': ('consume_bundle', '_parse'),
            'bvbrc_analysis_transport': ('BVBRCAnalysisClient',)}.items():
        module = importlib.import_module('gene_annotation_episode.' + name)
        for attribute in attributes:
            monkeypatch.setattr(module, attribute, forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr('subprocess.run', forbidden)
    original_plan = r.components['calculation_plan']
    changed = deepcopy(original_plan)
    chosen = changed['requests'][0]['selection']
    chosen['population_scope'] = 'selected_segments'
    chosen['segments'] = chosen['segments'][1:]
    with monkeypatch.context() as recalc_patch:
        for target in IO_AND_PARSERS:
            recalc_patch.setattr(target, forbidden)
        repeated = recalculate_genome_alignment_sheet(r.sheet, calculation_plan=deepcopy(original_plan))
        recalculated = recalculate_genome_alignment_sheet(r.sheet, calculation_plan=changed)
    assert repeated == r.sheet
    changed_coverage = recalculated['components']['outcomes'][0]['measurement']['value']['coverage'][0]
    assert changed_coverage['known_union_bases']['value'] == 677
    assert changed_coverage['coverage_fraction']['value'] == 677 / 693
    assert r.sheet == original_sheet and repeated != recalculated
    write(r.directory / 'saved-sheet-recalculation.json', repeated)
    write(r.directory / 'saved-sheet-changed-parameters.json', recalculated)
    # Reconstruct the original closed child's actual source through Workflow;
    # never run it. This makes the original redelivery consumer available while
    # preserving its durable assignment, form and observations.
    root_action = json.loads(r.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? '
        'AND episode_id=? AND decision_index=0', (r.workflow.run_id, r.archive['episode_id'])).fetchone()[0])
    rebuilt = r.workflow.selected(r.episode.source, root_action, 0).child
    assert rebuilt.source.episode_id == r.science['episode_id']
    redelivery_attempt = r.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? '
        'AND parent_episode_id=? AND child_episode_id=? ORDER BY decision_index DESC LIMIT 1',
        (r.workflow.run_id, r.science['episode_id'], r.results['episode_id'])).fetchone()
    redelivery_selection = {'kind': 'redeliver_report', 'delivery_ref': redelivery_attempt['delivery_ref'],
        'purpose': json.loads(redelivery_attempt['contract'])['decision'], 'schema_json': json.dumps(r.result_form)}
    # Create the event loop before the strict barrier also blocks socket.socket;
    # replay must not even create an internal socket pair or external socket.
    loop = asyncio.new_event_loop()
    try:
        with monkeypatch.context() as replay_patch:
            blocked = scientific_barrier(replay_patch)
            context = r.api.appservice.custody.context(r.results['episode_id'])
            key = r.body['publication']['origin']['operation_key']
            index = int(key.rsplit(':', 1)[1])
            action = dict(r.store.db.execute('SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
                (r.workflow.run_id, context.episode_id, index)).fetchone())
            choice = json.loads(action['action'])
            outcome = json.loads((r.api._manifest(context, create=False) / 'actions' / digest(key) / 'outcome.json').read_text())
            assert loop.run_until_complete(r.api.execute(context, choice['tool'], choice['arguments'], key)) == outcome
            assert r.api.read_result(r.final_ref, r.scope) == r.body
            redelivery = r.workflow.redeliver(rebuilt.source, redelivery_selection, redelivery_attempt['decision_index'])
            assert redelivery.failure is None and redelivery.report.as_record() == r.returned
            family = r.workflow.episode_bindings.for_role('results')
            for parent, closed, expected, schema in ((r.science, r.results, r.returned, r.result_form),
                    (r.archive, r.science, r.forwarded, r.parent_form)):
                parent_context = r.api.appservice.custody.context(parent['episode_id'])
                child_context = r.api.appservice.custody.context(closed['episode_id'])
                family.validate_received_report(child_context, expected, schema)
                commission = int(child_context.path[-1][1].removeprefix('child_'))
                refs = family.received_form_references(parent_context, expected, schema,
                    f'{r.workflow.run_id}:{parent_context.episode_id}:{commission}:typed_form')
                assert r.final_ref in refs
                assert r.api.genome_alignment_returns.received_facts(parent_context, r.parent_form) == {
                    source: r.forwarded[name] for name, source in r.requested_families.items()}
                forged = deepcopy(expected)
                forged['numbers'][0]['value']['value']['value'] += 1
                with pytest.raises(ValueError):
                    family.validate_received_report(child_context, forged, schema)
                expanded = deepcopy(expected)
                extra = deepcopy(expanded['numbers'][0])
                kind, analysis, _ = decode_reference(extra['field'])
                extra['field'] = encode_reference(kind, analysis, 'unrequested_measurement')
                expanded['numbers'].append(extra)
                with pytest.raises(ValueError):
                    family.validate_received_report(child_context, expanded, schema)
            assert dict(r.store.db.execute('SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
                (r.workflow.run_id, context.episode_id, index)).fetchone()) == action
    finally:
        loop.close()
    assert r.native.calls == calls
    assert {table: r.store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] for table in tables} == counts
    write(r.directory / 'SAVED_REPLAY_CHECK.json', {'counts_before': counts, 'counts_after': counts,
        'new_http_calls': 0, 'same_plan_recalculation_equal': True, 'changed_plan_union_bases': 677,
        'changed_plan_fraction': 677 / 693, 'saved_reads_and_admission_without_science': True,
        'workflow_redelivery_without_science': True, 'original_action_unchanged': True,
        'blocked_recalculation_io_and_parsers': IO_AND_PARSERS,
        'blocked_scientific_implementations_and_aliases': blocked})
