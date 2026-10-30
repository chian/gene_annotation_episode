"""Retained native MSA/MetaCATS bytes through the actual composed Workflow.

Decisions and the loopback AppService/Workspace server are controlled fixtures.
No model, remote service, aligner, R program or HPC job runs. Production HTTP,
custody, parsers, sheets, calculators, report admission and controllers run.
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

from gene_annotation_episode import bvbrc_msa_bundle_adapter as msa
from gene_annotation_episode import bvbrc_metacats_bundle_adapter as metacats
from gene_annotation_episode.bvbrc_alignment_bundle_contracts import decode_reference, encode_reference
from gene_annotation_episode.bvbrc_alignment_returns import alignment_fact_sources
from gene_annotation_episode.bvbrc_msa_grader import calculate_msa
from gene_annotation_episode.bvbrc_metacats_grader import calculate_metacats
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
from test_bvbrc_alignment_bundle_resolution import (
    MSA_NATIVE, META_NATIVE, meta_fixture, msa_native_fixture, slot, xmfa_native_fixture,
)
from test_bvbrc_alignment_tool_info import launch_payload
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import form
from test_practical_runtime import selected
from test_public_search import Client


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25'
PREFIX = 'api.bvbrc_appservice.'
CASES = ('msa_dna', 'metacats_files', 'xmfa_blocks')


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def content(store, reference):
    source = store.get(reference)
    raw = store.get_artifact(source['artifact_ref'])
    return {'source_ref': reference, 'artifact_field': 'artifact_ref',
        'artifact_ref': source['artifact_ref'], 'sha256': hashlib.sha256(raw).hexdigest(),
        'byte_count': len(raw)}


def measurement(request, metric, selector=None):
    return {'kind': 'measurement', 'analysis_id': 'analysis', 'request_id': request,
        'metric': metric, 'selector': {} if selector is None else selector}


def case_inputs(store, kind):
    """Rebuild every supplied source binding from actual Store material bytes."""
    if kind == 'msa_dna':
        fixture, module, mode = msa_native_fixture('dna'), msa, 'ordinary_alignment'
        fields = {'members': measurement('alignment', 'member_count'),
            'cells': measurement('alignment', 'cell_count'),
            'gaps': measurement('alignment', 'gap_fraction'),
            'entropy': measurement('entropy', 'literal_entropy_bits', {'column_0based': 1}),
            'native_score': {'kind': 'native_measurement', 'analysis_id': 'analysis',
                'table': slot('analysis', 'frequency'), 'row_index': 1, 'field': {'kind': 'score'}},
            'sites': {'kind': 'msa_sites', 'analysis_id': 'analysis', 'request_id': 'entropy',
                'columns_0based': [1, 2]}}
        expected = {'members': 4, 'cells': 28, 'gaps': 6 / 28,
            'entropy': 0.9182958340544896, 'native_score': 92}
        originals = [MSA_NATIVE / 'dna' / name for name in ('output.afa', 'foma.table', 'cons.fasta')]
    elif kind == 'metacats_files':
        directory = META_NATIVE / 'aa_two_groups'
        fixture = meta_fixture((directory / 'original.fasta').read_bytes(), (directory / 'metadata.tsv').read_bytes())
        module, mode = metacats, 'files'
        context = fixture.values[0]['value']
        context['categories'][0]['raw_heading_token'] = 'comparison'
        groups = ['metacats_group:category/A', 'metacats_group:category/B']
        requests = fixture.plan()['calculation_parameters']['requests']
        for row in requests:
            if 'selected_pairs' in row:
                row['selected_pairs'] = [groups]
        requests[0]['alphabet'] = 'protein'
        native = directory / 'output/comparison-chisqTable.tsv'
        fixture.artifact(native.read_bytes(), 'chisq', {'reader': 'metacats_chisq',
            'layout': 'current_filtered_tsv', 'category_id': 'category', 'encoding': 'ascii'}, 'chisq_export')
        fixture.plan()['analysis']['chisq_table_ids'] = [slot('analysis', 'chisq')]
        test = {'category_id': 'category', 'column_0based': 1, 'kind': 'omnibus', 'group_ids': groups}
        fields = {'members': measurement('alignment', 'member_count'),
            'chi_square': measurement('stats', 'chi_square', {'test': test}),
            'p_value': measurement('stats', 'mathematical_p', {'test': test}),
            'native_p': {'kind': 'native_measurement', 'analysis_id': 'analysis',
                'table': slot('analysis', 'chisq'), 'row_index': 0, 'field': {'kind': 'p_value'}},
            'counts': {'kind': 'group_counts', 'analysis_id': 'analysis', 'request_id': 'counts',
                'columns_0based': [1], 'group_ids': groups, 'symbols': ['A', 'C']}}
        expected = {'members': 12, 'chi_square': 8.330556481172943,
            'p_value': 0.0038983714243371837, 'native_p': 0.00389837142433717}
        originals = [directory / 'original.fasta', directory / 'metadata.tsv', native, directory / 'RECEIPT.json']
    else:
        fixture, module, mode = xmfa_native_fixture(with_sources=False), msa, 'mauve_alignment'
        fields = {'pair': {'kind': 'xmfa_alignment_measurements', 'analysis_id': 'analysis', 'request_id': 'metrics',
            'measurements': [{'metric': metric, 'block_index': 0, 'member_a': 1, 'member_b': 3}
                for metric in ('identical_canonical', 'substitutions', 'comparable_canonical', 'identity_fraction')]}}
        expected = {'identical_canonical': 39, 'substitutions': 7,
            'comparable_canonical': 46, 'identity_fraction': 39 / 46}
        originals = [ROOT / 'verification/tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25/native_examples/combined.xmfa']

    assignment = launch_payload('metacats' if module is metacats else 'msa', mode)
    request = assignment['request']
    if kind == 'metacats_files':
        request['parameters'].update(alphabet='aa', alignment_type='aligned_protein_fasta')
        request['input_bindings'].append({'binding_id': 'metadata-input', 'parameter_pointer': '/group_file',
            'kind': 'workspace_object', 'content': None, 'workspace_path': request['parameters']['group_file'],
            'inline_value': None, 'link_evidence': None, 'members': []})
    elif kind == 'msa_dna':
        original = (MSA_NATIVE / 'dna/output.afa').read_text()
        request['parameters']['fasta_keyboard_input'] = original
        request['input_bindings'][0]['inline_value'] = original
    fields['missing'] = {'kind': 'missing_requirements'}
    materials, metadata = [], []
    # Do not reuse Fixture's synthetic source/content labels as received facts.
    for selected_input in fixture.plan()['scientific_inputs']:
        row = next(v for v in fixture.values if v['evidence'] == selected_input['evidence'])
        material = store.register_material(data=canonical(row['value']).encode(),
            name=kind + '-' + selected_input['role'] + '.json', format='text', use='evidence')
        evidence = {'content': content(store, material['source_ref']), 'pointer': ''}
        selected_input['evidence'] = evidence
        materials.append(material)
        metadata.append(evidence)
    # One supplied native-byte receipt is read through an actual selected action
    # even for the cases with no additional scientific-input JSON.
    manifest = {'kind': 'retained_native_fixture_provenance', 'new_native_execution': False,
        'sources': [{'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'byte_count': path.stat().st_size} for path in originals]}
    materials.append(store.register_material(data=canonical(manifest).encode(),
        name=kind + '-retained-source-provenance.json', format='text', use='evidence'))
    files, requirements = [], []
    for index, artifact in enumerate(fixture.bundle['artifacts']):
        target = 'native-' + str(index)
        fmt = {**artifact['declared_format'], 'mode': fixture.plan()['analysis']['mode']}
        request['workspace_targets'].append({'target_id': target, 'path': '/controlled/output/' + target,
            'type': 'file', 'purpose': 'output_parent', 'input_binding_id': None, 'metadata': {},
            'allow_overwrite': False, 'allow_create_parents': True})
        requirements.append({'requirement_id': target, 'role': artifact['role'], 'required': True,
            'declared_format': fmt, 'producer_rule_evidence': None, 'exact_object': None})
        files.append({'object': {'kind': 'original_target', 'target_id': target}, 'role': artifact['role'],
            'declared_format': fmt, 'requirement_ids': [target], 'raw': fixture.raw[artifact['raw_artifact_ref']]})
    selector = {'version': 'bvbrc_appservice_result_selector_v1', 'endpoint': 'requested_projection',
        'requirements': requirements, 'adapter': {'adapter_id': module.ADAPTER_ID,
            'adapter_version': module.ADAPTER_VERSION, 'parameters': fixture.parameters},
        'requested_schema': module.requested_form_schema(fields), 'supplied_metadata': metadata, 'supplied_capabilities': []}
    family = 'xmfa_measurements' if kind == 'xmfa_blocks' else 'measurements'
    return SimpleNamespace(kind=kind, fixture=fixture, module=module, mode=mode, assignment=assignment,
        request=request, selector=selector, files=files, fields=fields, expected=expected,
        materials=materials, manifest=manifest, family=family,
        tool_name='bvbrc.' + ('metacats.' if module is metacats else 'msa.') + mode)


@contextmanager
def protocol_server(case):
    """Actual HTTP with controlled protocol replies and retained native bodies."""
    calls, errors = [], []
    paths = {row['path']: row['target_id'] for row in case.request['workspace_targets']}
    files = {row['object']['target_id']: row['raw'] for row in case.files}

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
                if command['method'] == 'AppService.start_app2':
                    assert self.path == '/app'
                    assert command['params'] == [case.request['required_application_id'], case.request['parameters'], {}]
                    result = {'id': '123', 'application_id': case.request['required_application_id'], 'state_code': 'Q'}
                else:
                    assert self.path == '/workspace' and command['method'] == 'Workspace.get_download_url'
                    path, = command['params'][0]['objects']
                    result = [url + '/download/' + paths[path]]
                response = {'version': '1.1', 'id': command['id'], 'result': [result]}
                self.send(canonical(response).encode(), 'application/json')
            except Exception as error:
                errors.append(repr(error))
                self.send_error(500)

        def do_GET(self):
            try:
                assert self.path.startswith('/download/') and 'Range' not in self.headers
                raw = files[self.path.removeprefix('/download/')]
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
        'goal': 'Measure the selected alignment and group comparison quantities for the supplied sequences',
        'scope': scope, 'purpose': 'Return the original requested native measurements and calculated quantities with their units, populations and missing qualifications',
        'assignment': deepcopy(assignment), 'schema_json': json.dumps(schema), 'initial_report_json': '{}'}, 'report_update': {}}


def run_identity(kind, science_count, download_count):
    """Ensure later selected work sorts before the early hash directory."""
    for index in range(100):
        run_id = f'alignment-composed-{kind}-{index}'
        path = (('annotation', 'root'), ('scientific_process', 'child_0'), ('results', 'child_' + str(science_count + 1)))
        episode_id = EpisodeRef(run_id, path).episode_id
        if digest(f'{run_id}:{episode_id}:{2 * download_count - 1}') < digest(f'{run_id}:{episode_id}:1') or download_count == 1:
            return run_id
    raise AssertionError('Unable to construct reverse hash ordering')


def source_hashes():
    paths = {path for folder in ('gene_annotation_episode', 'method_loop')
        for path in (ROOT / folder).rglob('*') if path.is_file() and path.suffix in {'.py', '.json'}}
    paths.add(Path(__file__))
    paths.update(ROOT / 'tests' / name for name in ('test_bvbrc_alignment_bundle_resolution.py',
        'test_bvbrc_alignment_tool_info.py', 'test_execution_episodes_family.py', 'test_execution_wiring.py',
        'test_practical_runtime.py', 'test_public_search.py', 'bvbrc_minhash_episode_fixture.py'))
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


@pytest.fixture(scope='module', params=CASES, ids=CASES)
def alignment_run(request):
    (EVIDENCE / 'runs').mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=request.param + '-', dir=EVIDENCE / 'runs'))
    before = source_hashes()
    write(directory / 'SOURCE_HASHES_BEFORE.json', before)
    provenance = {'scope': 'controlled selected Workflow and loopback HTTP using retained native byte examples',
        'configured_model': False, 'live_bvbrc': False, 'new_native_scientific_execution': False, 'hpc': False,
        'production_overrides': [], 'controlled_fixtures': ['decision provider', 'local HTTP protocol replies', 'caller scientific credit zero'],
        'controller': {'class': 'YieldController', 'cost': .1, 'parameters': YieldParameters().as_record(),
            'scientific_estimator': 'unchanged estimate_score_yield', 'resource_endpoint': 'existing practical exact-zero'},
        'python_executable': sys.executable, 'python_version': sys.version}
    write(directory / 'PROVENANCE.json', {**provenance, 'status': 'started'})
    with pytest.MonkeyPatch.context() as patch, Store(directory / 'state') as store:
        target, = store.create_problem(raw_sequence='AACGT', molecule='dna')['subject_refs']
        scope = {'subject_refs': [target]}
        case = case_inputs(store, request.param)
        original_case = deepcopy({'request': case.request, 'selector': case.selector})
        write(directory / 'selected-inputs.json', {**original_case, 'provenance': case.manifest})
        for index, item in enumerate(case.files):
            (directory / f'native-{index}.bin').write_bytes(item['raw'])
        with protocol_server(case) as native:
            original_connect = socket.socket.connect
            def controlled_connect(sock, address):
                if sock.family in (socket.AF_INET, socket.AF_INET6):
                    assert address[0] == '127.0.0.1' and address[1] == native.port, address
                return original_connect(sock, address)
            patch.setattr(socket.socket, 'connect', controlled_connect)
            def forbidden(*_, **__):
                raise AssertionError('Workflow fixture attempted a new native process')
            patch.setattr('subprocess.run', forbidden)
            patch.setattr('subprocess.Popen', forbidden)

            config = {'kind': 'api', 'service': 'bvbrc_appservice', 'execution_contract': 'bvbrc_appservice_execution_v1',
                'endpoints': {'AppService': native.url + '/app', 'Workspace': native.url + '/workspace'},
                'scientific_adapters': [{'adapter_id': module.ADAPTER_ID, 'adapter_version': '1',
                    'implementation_sha256': module.implementation_sha256()} for module in (msa, metacats)]}
            pin = next(row['implementation_sha256'] for row in config['scientific_adapters'] if row['adapter_id'] == case.module.ADAPTER_ID)
            handoff_form, result_form = form('execution_handoff_refs'), form('execution_result_refs')
            sources = alignment_fact_sources()
            result_form['properties'].update(numbers=sources['bvbrc_alignment_' + case.family]['report_schema'],
                missing=sources['bvbrc_alignment_requirements']['report_schema'])
            result_form['required'].extend(['numbers', 'missing'])
            detail = {'msa_dna': 'msa_sites', 'metacats_files': 'group_counts'}.get(case.kind)
            if detail:
                result_form['properties']['detail'] = sources['bvbrc_alignment_' + detail]['report_schema']
                result_form['required'].append('detail')
            parent_form = {'type': 'object', 'additionalProperties': False, 'properties': {
                'numbers': deepcopy(result_form['properties']['numbers'])}, 'required': ['numbers']}
            launch = launch_assignment({'selected-api': case.assignment})
            factory = ExecutionServiceFactory({'selected-api': config}, {}, 2, 3, .5)
            tools = ToolRegistry(store, clients=Client())
            run_id = run_identity(case.kind, len(case.materials), len(case.files))
            run_directory = directory / 'run'
            application = factory(store, run_id=run_id, directory=run_directory, tool_registry=tools, tool_catalog=tools.catalog())
            descriptor = prepare_scientific_binding(run_directory=run_directory, source_directory=PUBLICATION,
                tool_catalog=tools.catalog(), child_roles=('scientific_process', 'launch', 'results'),
                resource_catalogs=application.resource_tool_catalogs)
            library = ScientificProcessLibrary(run_directory / 'scientific-process-library')
            selected_tools = [{'name': case.tool_name, 'resources': 'api'}, {'name': 'material.parse', 'resources': 'local'}]

            class Choices:
                def __init__(self):
                    self.counts, self.scientific_calls, self.partial = {}, [], []
                    self.received = None

                def last(self, episode_id):
                    row = store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? '
                        'AND result IS NOT NULL ORDER BY decision_index DESC LIMIT 1', (run_id, episode_id)).fetchone()
                    return json.loads(row['result'])['result']

                async def complete(self, episode_id, role, instructions, current, schema):
                    assert current.get('feedback') is None, current.get('feedback')
                    self.counts[episode_id] = count = self.counts.get(episode_id, 0) + 1
                    execution = current.get('execution_assignment', {})
                    version = execution.get('version')
                    if version == 'execution_launch_assignment_v1':
                        assert count == 1 and execution == launch
                        return child('launch_api', case.assignment, scope, handoff_form)
                    if version == 'api_service_assignment_v1':
                        assert execution == case.assignment
                        if count == 1:
                            return selected(PREFIX + 'prepare', {'definition': {'kind': 'packaged',
                                'required_application_id': case.request['required_application_id']}})
                        assert count == 2
                        return selected(PREFIX + 'submit', {'preparation_receipt_ref': self.last(episode_id)['support_receipt_ref'],
                            'input_evidence_refs': []})
                    if version == 'execution_results_assignment_v1':
                        assert execution['selector'] == case.selector
                        if count > 1 and count % 2:
                            body = api.read_result(self.last(episode_id)['source_ref'], scope)
                            self.partial.append(deepcopy(body))
                            write(directory / f'partial-{count - 2}.json', body)
                            assert body['publication']['completion_proof'] is None
                        if count > 2 * len(case.files):
                            raise AssertionError('Original requested numeric endpoint did not close: ' + canonical(api.read_result(self.last(episode_id)['source_ref'], scope)['publication']))
                        item = case.files[(count - 1) // 2]
                        if count % 2:
                            return selected(PREFIX + 'download_capability', {'objects': [item['object']],
                                'generation': 0, 'predecessor_receipt_ref': None})
                        arguments = {key: deepcopy(item[key]) for key in ('object', 'role', 'declared_format', 'requirement_ids')}
                        arguments.update(byte_range=None, capability={'kind': 'acquired',
                            'receipt_ref': self.last(episode_id)['support_receipt_ref'], 'input_index': 0})
                        return selected(PREFIX + 'download', arguments)
                    if 'scientific_process' in current:
                        self.scientific_calls.append((deepcopy(current), instructions))
                        assert current['scientific_process']['selection']['child_tool_info'] == selected_tools
                        if count <= len(case.materials):
                            return selected('material.parse', {'material_ref': case.materials[count - 1]['id'], 'format': 'text'})
                        if count == len(case.materials) + 1:
                            return child('launch', launch, scope, handoff_form)
                        if count == len(case.materials) + 2:
                            handoff, = current['child_reports'][-1]['references']
                            return child('results', {'version': 'execution_results_assignment_v1',
                                'handoff_ref': handoff, 'selector': case.selector}, scope, result_form)
                        self.received = deepcopy(current['child_reports'][-1])
                        if count == len(case.materials) + 3:
                            delivery = current['report_deliveries'][-1]
                            return {'selection': {'kind': 'redeliver_report',
                                'delivery_ref': delivery['delivery_ref'],
                                'purpose': 'Receive the same original measured quantities from the saved closed child form',
                                'schema_json': json.dumps(result_form)}, 'report_update': {}}
                        # Re-reading selected supplied material is an ordinary own
                        # action; it does not create another native observation.
                        return selected('material.parse', {'material_ref': case.materials[-1]['id'], 'format': 'text'})
                    if count == 1:
                        scientific = {'selection': {'version': 'scientific_process_selection_v3',
                            'evidence_axis': library.reference('A101'), 'thought_pattern': library.reference('P01'),
                            'child_tool_info': deepcopy(selected_tools)}, 'evidence_refs': [target],
                            'constraints': {'preserve_original_alignment_and_groups': True},
                            'context': {'supplied_sequence': 'AACGT', 'molecule': 'dna', 'complete': True,
                                'label_is_public_identity': False, 'supplied_material_refs': [m['id'] for m in case.materials]}}
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
            episode = workflow.build('annotation', 'root', 'Measure selected sequence-alignment quantities and group differences', scope)
            async def execute():
                record = await episode.run_async(workflow.context)
                await episode.build_result(record)
                return record
            record = asyncio.run(execute())
            archive = json.loads(''.join(iter_json(record.as_record())))
            science = archive['units'][0]['child']
            launch_record = science['units'][len(case.materials)]['child']
            results = science['units'][len(case.materials) + 1]['child']
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
            for index, (current, instructions) in enumerate(choices.scientific_calls):
                (directory / f'scientific-presentation-{index}.txt').write_text(render_scientific_process_prompt(current, instructions))
            after = source_hashes()
            write(directory / 'SOURCE_HASHES_AFTER.json', after)
            write(directory / 'PROVENANCE.json', {**provenance, 'status': 'workflow_closed',
                'adapter_pin': pin, 'expected_measurements': case.expected,
                'source_changes_during_run': [name for name in before if before[name] != after.get(name)]})
            assert before == after, 'Source changed during controlled run; retain this receipt and rerun.'
            assert not native.errors
            assert original_case == {'request': case.request, 'selector': case.selector}
            yield SimpleNamespace(directory=directory, store=store, case=case, native=native, workflow=workflow,
                api=api, choices=choices, archive=archive, science=science, launch=launch_record, api_record=api_record,
                results=results, returned=returned, forwarded=forwarded, body=body, sheet=sheet, components=components,
                final_ref=final_ref, scope=scope, result_form=result_form, parent_form=parent_form, episode=episode,
                library=library, selected_tools=selected_tools, pin=pin)


def test_selected_three_slots_and_child_owned_http_route(alignment_run):
    r = alignment_run
    binding = r.workflow.scientific_process_binding
    context = r.api.appservice.custody.context(r.science['episode_id'])
    binding.validate_context(context)
    catalog = r.workflow.services.tool_information_catalog(r.scope)
    information = binding.tool_library.resolve_tool_info(r.selected_tools, catalog)
    assert plain(context.assignment)['selection'] == {'version': 'scientific_process_selection_v3',
        'evidence_axis': r.library.reference('A101'), 'thought_pattern': r.library.reference('P01'), 'child_tool_info': information}
    contract = next(row for row in binding.tool_library.resolve_invocations(r.selected_tools, catalog) if row['name'] == r.case.tool_name)
    assert contract['invocation_route'] == {'kind': 'commission', 'routes': [
        {'entry_role': 'launch', 'resource_id': 'selected-api', 'resource_role': 'launch_api'},
        {'entry_role': 'results', 'resource_id': 'selected-api', 'resource_role': 'results'}]}
    direct = {row['name'] for row in binding.catalog(context)}
    assert 'material.parse' in direct and not any(name.startswith('bvbrc.') or name.startswith(PREFIX) for name in direct)
    assert r.workflow.catalog(r.scope, source=r.episode.source) == []
    for index, (current, _) in enumerate(r.choices.scientific_calls):
        task, steering = (r.directory / f'scientific-presentation-{index}.txt').read_text().split('\n\nSTEERING', 1)
        assert task.startswith('TASK\n') and contract['instructions'] in task
        assert contract['instructions'] not in steering
        assert current['scientific_process']['evidence_axis']['investigation_instructions'] in task
        assert all(value not in task + steering for value in (
            r.final_ref, r.pin, r.science['episode_id'], r.results['episode_id']))
    for material in r.case.materials:
        assert r.api.appservice.custody.possession(context, material['source_ref']) == 'own_completed_action'
    owner = r.api.appservice.custody.original_job_owner(r.api.appservice.custody.context(r.api_record['episode_id']))
    assert owner['launch_episode_id'] == r.launch['episode_id']
    assert owner['parent_commission_operation_key'] == f'{r.workflow.run_id}:{context.episode_id}:{len(r.case.materials)}'
    assert r.body['bundle']['original_task']['submitted_parameters'] == r.case.request['parameters']
    assert r.body['bundle']['input_bindings'] == r.case.request['input_bindings']
    assert [call['rpc']['method'] for call in r.native.calls if call['method'] == 'POST'] == [
        'AppService.start_app2', *(['Workspace.get_download_url'] * len(r.case.files))]
    assert len([call for call in r.native.calls if call['method'] == 'GET']) == len(r.case.files)


def test_retained_bytes_full_sheets_and_original_numbers_reach_both_parents(alignment_run):
    r = alignment_run
    if r.case.kind == 'xmfa_blocks':
        values = {v['selection']['metric']: v['measurement']['value'] for row in r.returned['numbers'] for v in row['value']}
    else:
        values = {decode_reference(row['field'])[2]: row['value']['value'] for row in r.returned['numbers']}
    assert values == pytest.approx(r.case.expected)
    assert r.returned['completed'] is True and r.forwarded == {'numbers': r.returned['numbers']}
    assert r.body['publication_inputs']['selector'] == r.case.selector
    assert r.body['publication_inputs']['adapter_implementation_sha256'] == r.pin
    assert r.body['publication']['adapter_result']['missing_requirements']
    assert r.body['publication']['completion_proof'] is not None
    artifacts = {row['role']: row for row in r.body['bundle']['artifacts']}
    for item in r.case.files:
        actual = artifacts[item['role']]
        assert r.store.get_artifact(actual['raw_artifact_ref']) == item['raw']
        assert actual['sha256'] == hashlib.sha256(item['raw']).hexdigest() and actual['byte_count'] == len(item['raw'])
        assert actual['transfer']['body_complete'] and actual['transfer']['object_complete'] == 'yes'
        assert actual['task_association']['kind'] == 'unverified_original_path'
        assert actual['task_association']['byte_version_status'] != 'producer_bytes_bound'
    sheet = r.sheet['analyses'][0]['sheet']
    assert len(sheet['documents']) == len(r.case.files)
    assert sheet['run']['versions'] == []
    assert sheet['analysis']['mode'] == r.case.fixture.plan()['analysis']['mode']
    if r.case.kind == 'msa_dna':
        assert len(sheet['native_observations']) > 7
        assert [x['column_0based'] for x in r.returned['detail'][0]['value']] == [1, 2]
        native = next(row['value'] for row in r.returned['numbers'] if decode_reference(row['field'])[2] == 'native_score')
        assert native['origin'] == 'native_observation' and native['method_ref'] is None
    elif r.case.kind == 'metacats_files':
        assert len(sheet['native_observations']) >= 3
        counts = r.returned['detail'][0]['value']
        assert [row['count'] for row in counts] == [6, 0, 0, 6]
        assert all(row['basis'] == 'biological' for row in counts)
        assert sheet['native_group_columns'] == []
    else:
        document, = sheet['documents']
        assert len(document['value']['blocks']) == 6
        assert len(r.components['analyses'][0]['components']['results']) == 6
    family = 'bvbrc_alignment_' + r.case.family
    for child_record, parent_record, expected in ((r.results, r.science, r.returned), (r.science, r.archive, r.forwarded)):
        attempt = r.store.db.execute('SELECT parent_episode_id,form,failure FROM runtime_report_attempts '
            'WHERE run_id=? AND child_episode_id=?', (r.workflow.run_id, child_record['episode_id'])).fetchone()
        assert attempt['parent_episode_id'] == parent_record['episode_id'] and attempt['failure'] is None
        assert json.loads(attempt['form']) == expected
        context = r.api.appservice.custody.context(parent_record['episode_id'])
        received = {row['fact_source']: row['facts'] for row in r.api.alignment_returns.received_context(context)}
        assert received[family] == expected['numbers']
        assert r.api.appservice.custody.possession(context, r.final_ref) == 'admitted_return'
        if parent_record is r.archive:
            assert set(received) == {family}
    write(r.directory / 'NUMERICAL_RETURN_CHECK.json', {'actual': values, 'expected': r.case.expected,
        'retained_optional_requirements': r.body['publication']['adapter_result']['missing_requirements']})


def test_controller_exact_zero_and_one_observation_per_selected_action(alignment_run):
    r = alignment_run
    for record in (r.archive, r.science, r.launch, r.api_record, r.results):
        internal_redelivery = int(record is r.science)
        assert record['units_consumed'] + internal_redelivery == r.choices.counts[record['episode_id']]
        for table in ('runtime_actions', 'runtime_observations', 'runtime_model_calls'):
            expected_count = record['units_consumed'] + (internal_redelivery if table == 'runtime_model_calls' else 0)
            assert r.store.db.execute('SELECT count(*) FROM ' + table + ' WHERE run_id=? AND episode_id=?',
                (r.workflow.run_id, record['episode_id'])).fetchone()[0] == expected_count
    attempts = r.store.db.execute('SELECT form FROM runtime_report_attempts WHERE run_id=? AND child_episode_id=?',
        (r.workflow.run_id, r.results['episode_id'])).fetchall()
    assert len(attempts) == 2 and all(json.loads(row['form']) == r.returned for row in attempts)
    assert r.api_record['units_consumed'] == 2 and r.launch['units_consumed'] == 1
    assert r.results['units_consumed'] == 2 * len(r.case.files)
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


def test_partial_order_saved_recalculation_and_forwarding_without_new_work(alignment_run, monkeypatch):
    r = alignment_run
    if r.choices.partial:
        early = r.choices.partial[0]
        assert r.api.read_result(early['reference'], r.scope) == early
        assert early['status'] == 'partial' and early['publication']['completion_proof'] is None
        assert early['publication']['missing_requirements']
        early_key = early['publication']['origin']['operation_key']
        final_key = r.body['publication']['origin']['operation_key']
        assert int(early_key.rsplit(':', 1)[1]) < int(final_key.rsplit(':', 1)[1])
        assert digest(final_key) < digest(early_key)
        assert all(row['source_ref'] == r.final_ref for row in r.forwarded['numbers'])
        for index, partial in enumerate(r.choices.partial):
            repair = r.case.files[index + 1]
            assert any(row['requirement_id'] in repair['requirement_ids']
                and row['role'] == repair['role'] and row['reason_code'] == 'output_bytes_missing'
                for row in partial['bundle']['missing_requirements'])
            selected_repair = json.loads(r.store.db.execute('SELECT action FROM runtime_actions '
                'WHERE run_id=? AND episode_id=? AND decision_index=?',
                (r.workflow.run_id, r.results['episode_id'], 2 * (index + 1) + 1)).fetchone()[0])
            assert selected_repair['tool'] == PREFIX + 'download'
            assert selected_repair['arguments']['requirement_ids'] == repair['requirement_ids']
            assert selected_repair['arguments']['object'] == repair['object']
        if r.case.kind == 'msa_dna':
            assert early['publication']['adapter_result']['facts']['members']['value'] == 4
            assert early['publication']['adapter_result']['facts']['native_score']['value'] is None
            middle = r.choices.partial[1]
            assert middle['publication']['adapter_result']['facts']['native_score']['value'] == 92
            assert middle['publication']['adapter_result']['status'] == 'ok'
            assert middle['publication']['completion_proof'] is None  # original required consensus bytes absent
    tables = ('runtime_actions', 'runtime_model_calls', 'runtime_observations', 'runtime_report_attempts', 'runtime_record_receipts')
    counts = {table: r.store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] for table in tables}
    calls, sheet_before = deepcopy(r.native.calls), deepcopy(r.sheet)
    def forbidden(*_, **__):
        raise AssertionError('Saved replay attempted acquisition, native parsing or scientific calculation')
    for module_name, names in {
        'bvbrc_analysis_transport': ['BVBRCAnalysisClient'],
        'bvbrc_alignment_bundle_resolution': ['_parse', 'resolve_bundle'],
        'phylogeny_formats': ['parse_aligned_fasta', 'parse_newick'],
        'bvbrc_msa_formats': ['parse_msa_frequency_table'],
        'bvbrc_metacats_formats': ['parse_metacats_metadata', 'parse_metacats_chisq_table'],
        'bvbrc_metacats_input_formats': ['parse_metacats_input_fasta'],
        'xmfa_formats': ['parse_mauve_xmfa'],
    }.items():
        module = importlib.import_module('gene_annotation_episode.' + module_name)
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    provider_sheet = r.sheet['analyses'][0]['sheet']
    saved_components = r.components['analyses'][0]['components']
    calculator = calculate_metacats if r.case.module is metacats else calculate_msa
    repeated = calculator(provider_sheet, deepcopy(saved_components['parameters']))
    assert repeated == saved_components
    changed = deepcopy(saved_components['parameters'])
    if r.case.kind == 'metacats_files':
        next(row for row in changed['requests'] if row['kind'] == 'biological_statistics')['epsilon'] = .01
    else:
        changed['requests'][0]['selected_pairs' if r.case.kind == 'xmfa_blocks' else 'pairs'] = []
    recalculated = calculator(provider_sheet, changed)
    assert recalculated['results'] != repeated['results'] and r.sheet == sheet_before
    write(r.directory / 'saved-sheet-recalculation.json', repeated)
    write(r.directory / 'saved-sheet-changed-parameters.json', recalculated)
    # Saved return validation and read/replay must now use no calculator either.
    for module_name in ('bvbrc_msa_grader', 'bvbrc_metacats_grader', 'bvbrc_alignment_bundle_resolution'):
        module = importlib.import_module('gene_annotation_episode.' + module_name)
        for name in ('calculate_msa', 'calculate_metacats', 'consume_bundle'):
            if hasattr(module, name):
                monkeypatch.setattr(module, name, forbidden)
    context = r.api.appservice.custody.context(r.results['episode_id'])
    key = r.body['publication']['origin']['operation_key']
    index = int(key.rsplit(':', 1)[1])
    action = dict(r.store.db.execute('SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
        (r.workflow.run_id, context.episode_id, index)).fetchone())
    selection = json.loads(action['action'])
    host_outcome = json.loads((r.api._manifest(context, create=False) / 'actions' / digest(key) / 'outcome.json').read_text())
    assert asyncio.run(r.api.execute(context, selection['tool'], selection['arguments'], key)) == host_outcome
    assert r.api.read_result(r.final_ref, r.scope) == r.body
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
        assert r.api.alignment_returns.received_facts(parent_context, r.parent_form) == {
            'bvbrc_alignment_' + r.case.family: r.forwarded['numbers']}
        forged = deepcopy(expected)
        if r.case.kind == 'xmfa_blocks':
            forged['numbers'][0]['value'][0]['measurement']['value'] += 1
        else:
            forged['numbers'][0]['value']['value'] += 1
        with pytest.raises(ValueError):
            family.validate_received_report(child_context, forged, schema)
        expanded = deepcopy(expected)
        extra = deepcopy(expanded['numbers'][0])
        kind, analysis, _ = decode_reference(extra['field'])
        extra['field'] = encode_reference(kind, analysis, 'unrequested_numeric_field')
        expanded['numbers'].append(extra)
        with pytest.raises(ValueError):
            family.validate_received_report(child_context, expanded, schema)
    assert r.native.calls == calls
    assert {table: r.store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] for table in tables} == counts
    assert dict(r.store.db.execute('SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
        (r.workflow.run_id, context.episode_id, index)).fetchone()) == action
    write(r.directory / 'saved-replay-verification.json', {'counts_before': counts, 'counts_after': counts,
        'new_http_calls': 0, 'saved_recalculation_equal': True, 'changed_parameter_result_differs': True,
        'typed_read_and_admission_without_calculation': True, 'original_action_unchanged': True})
