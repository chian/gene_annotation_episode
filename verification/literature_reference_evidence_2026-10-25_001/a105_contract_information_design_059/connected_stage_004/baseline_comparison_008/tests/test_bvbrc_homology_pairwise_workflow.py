"""Selected pairwise Homology through the actual composed Workflow.

Only decisions, science/root continuation, and NativeClient are controlled.
All input parsing, custody, manifest association, publication, numerical reading,
typed return and practical completion use production code. Native bytes are
explicit synthetic fixtures; no remote service or BLAST executable runs.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

import pytest
from Bio.Seq import Seq
from method_loop.archive import iter_json

from gene_annotation_episode import bvbrc_homology_bundle_adapter as adapter
from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.bvbrc_homology_grader import calculate_homology_scores
from gene_annotation_episode.bvbrc_homology_returns import homology_fact_sources
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_prompt import render_scientific_process_prompt
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from bvbrc_minhash_episode_fixture import PUBLICATION
from test_api_bvbrc_appservice import CONFIG, PREFIX, OBJECT_UUID, SHOCK_UUID, metadata
from test_bvbrc_appservice_inputs import NativeClient
from test_bvbrc_homology_grader import program_document
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import form
from test_practical_runtime import selected
from test_public_search import Client


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'verification/tool_graders_bvbrc_homology_pairwise_workflow_2026-10-24'
TOOL_NAME = 'bvbrc.homology.pairwise_correspondence'
QUERY = 'ATGAAAACTGGGTAA'
REFERENCE = 'MKTGG'
MEASUREMENTS = {'query_coverage': .6, 'reference_coverage': .6, 'aligned_pairs': 3, 'identity': 1}


def _write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def _source_provenance(original_files=None):
    package = Path(adapter.__file__).resolve().parent
    assert package == ROOT / 'gene_annotation_episode'
    method_package = Path(iter_json.__code__.co_filename).resolve().parent
    loaded_modules = {}
    for name, module in list(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if filename is not None and Path(filename).is_file():
            path = Path(filename).resolve()
            loaded_modules[name] = {'path': str(path),
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    if original_files is None:
        files = {Path(row['path']) for row in loaded_modules.values()}
        for directory in (package, method_package, PUBLICATION):
            files.update(path for path in directory.rglob('*')
                if path.is_file() and path.suffix in {'.py', '.json', '.md'})
        files.update(ROOT / 'tests' / name for name in (
            'test_bvbrc_homology_pairwise_workflow.py', 'test_bvbrc_homology_subject_binding.py',
            'bvbrc_minhash_episode_fixture.py', 'test_api_bvbrc_appservice.py',
            'test_bvbrc_appservice_inputs.py', 'test_bvbrc_homology_grader.py',
            'test_execution_episodes_family.py', 'test_execution_wiring.py',
            'test_practical_runtime.py', 'test_public_search.py'))
    else:
        # A concurrent, unimported module is not part of this execution. Recheck
        # the exact original files, while recording all currently loaded modules.
        files = {Path(path) for path in original_files}
    return {'python_executable': sys.executable, 'python_version': sys.version,
        'gene_annotation_episode_package': str(package), 'method_loop_package': str(method_package),
        'scientific_library_publication': str(PUBLICATION),
        'adapter_implementation_sha256': adapter.implementation_sha256(),
        'loaded_modules': loaded_modules,
        'files': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)}}


def _content(store, source_ref):
    source = store.get(source_ref)
    raw = store.get_artifact(source['artifact_ref'])
    return {'source_ref': source_ref, 'artifact_field': 'artifact_ref',
        'artifact_ref': source['artifact_ref'], 'sha256': hashlib.sha256(raw).hexdigest(),
        'byte_count': len(raw)}


def _pairwise_supplied(store, target):
    """Retain exact full operands; no placeholder digest or one-hit proof."""
    document = program_document('blastx')
    search = document['BlastOutput2'][0]['report']['results']['search']
    query_fasta = '>' + search['query_title'] + '\n' + QUERY + '\n'
    reference_fasta = '>SYNTHETIC-subject\n' + REFERENCE + '\n'
    # The actual retained material-member identity labels the reference. It is
    # evidence only, never an additional annotation target. Selected parsing
    # below establishes the scientific child's possession before commission.
    reference_material = store.register_material(data=reference_fasta.encode(),
        name='SYNTHETIC-reference.faa', format='fasta', molecule='protein', use='evidence')
    reference_parse = store.parse_material(reference_material['id'], format='fasta')
    reference_member, = store.material_members(reference_parse['collection_ref'])['members']
    query_member = store.get(target)['source_record']['member_ref']
    query_sha = hashlib.sha256(QUERY.encode()).hexdigest()
    reference_sha = hashlib.sha256(REFERENCE.encode()).hexdigest()
    db_selection = {'db_type': 'faa', 'db_source': 'fasta_data', 'db_fasta_data': reference_fasta}
    original_input = {'fixture': 'Synthetic supplied operands and native mapping; no BLAST ran',
        'query_fasta': query_fasta, 'reference_fasta': reference_fasta,
        'query_members': [{'member_id': query_member, 'supplied_id': search['query_title'],
            'sequence': QUERY, 'length': len(QUERY), 'molecule': 'dna', 'sequence_sha256': query_sha,
            'native_query': {'report_index': 0, 'query_id': search['query_id'],
                'query_title': search['query_title'], 'query_len': len(QUERY)}, 'sequence_transform': 'identity'}],
        'reference_members': [{'member_id': reference_member['id'], 'supplied_id': 'SYNTHETIC-subject',
            'sequence': REFERENCE, 'length': len(REFERENCE), 'molecule': 'protein',
            'sequence_sha256': reference_sha, 'material_ref': reference_material['id'],
            'source_ref': reference_material['source_ref'],
            'native_hit': {'report_index': 0, 'hit_index': 0, 'description_index': 0,
                'id': 'SYNTHETIC-subject', 'length': len(REFERENCE)}}],
        'database': {'requested_selection': db_selection, 'member_count': 1,
            'effective_native_database': 'SYNTHETIC_DATABASE_PATH',
            'members': [{'identifier': reference_member['id'], 'sequence_sha256': reference_sha,
                'length': len(REFERENCE), 'molecule': 'aa'}]}}
    input_material = store.register_material(data=canonical(original_input).encode(),
        name='SYNTHETIC-pairwise-original-input.json', format='text', use='evidence')
    input_source = _content(store, input_material['source_ref'])
    inputs = []
    for binding_id, key, pointer, fasta, member in (
            ('query-input', 'input_fasta_data', '/query_members/0', query_fasta, original_input['query_members'][0]),
            ('reference-input', 'db_fasta_data', '/reference_members/0', reference_fasta, original_input['reference_members'][0])):
        inputs.append({'binding_id': binding_id, 'parameter_pointer': '/' + key,
            'kind': 'supplied_link', 'content': None, 'workspace_path': None,
            'inline_value': fasta, 'link_evidence': {'content': input_source,
                'pointer': '/query_fasta' if binding_id == 'query-input' else '/reference_fasta'},
            'members': [{'member_id': member['member_id'], 'member_pointer': pointer,
                **{name: member[name] for name in ('length', 'molecule', 'sequence_sha256')},
                'evidence': {'content': input_source, 'pointer': pointer}}]})
    request = {'version': 'bvbrc_appservice_request_v1', 'effect_contract': 'selected_api_effects_v1',
        'required_application_id': 'Homology', 'parameters': {'output_path': '/synthetic/work/output',
            'output_file': 'selected', 'input_type': 'dna', 'input_source': 'fasta_data',
            'input_fasta_data': query_fasta, 'blast_program': 'blastx', 'blast_max_hits': 3, **db_selection},
        'start_parameters': {}, 'definition_inputs': [], 'input_bindings': inputs, 'workspace_targets': []}
    scientific_inputs = {'version': adapter.SCIENTIFIC_INPUTS_VERSION,
        'queries': [{'input_binding_id': 'query-input', 'input_member_id': query_member,
            'representation': 'raw', 'binding': {'input_source_ref': input_source['source_ref'],
                'member_ref': query_member, 'subject_ref': target, 'molecule': 'nt',
                'supplied_id': search['query_title'], 'supplied_length': len(QUERY),
                'supplied_sequence_sha256': query_sha, 'staged_id': search['query_title'],
                'staged_length': len(QUERY), 'staged_sequence_sha256': query_sha,
                'sequence_transform': {'kind': 'identity', 'source_ref': input_source['source_ref'],
                    'pointer': '/query_members/0', 'coordinate_map_ref': None},
                'native_query': original_input['query_members'][0]['native_query'],
                'id_mapping_evidence': [{'source_ref': input_source['source_ref'],
                    'pointer': '/query_members/0/native_query', 'relation': 'exact_submitted_member_to_native_query'}]}}],
        'database_binding': {'requested_selection': db_selection,
            'effective_native_database': 'SYNTHETIC_DATABASE_PATH', 'effective_parameters_source': None,
            'reference_release': None, 'reference_release_source': None, 'actual_taxon_filter': None,
            'actual_database_members': original_input['database']['members'],
            'input_or_database_sequence_inventory_ref': input_source['source_ref']},
        'subject_binding': {'source_ref': input_source['source_ref'], 'member_ref': reference_member['id'],
            'subject_ref': reference_member['id'], 'sequence_sha256': reference_sha,
            'length': len(REFERENCE), 'molecule': 'aa',
            'database_membership': {'source_ref': input_source['source_ref'],
                'pointer': '/reference_members', 'member_count': 1},
            'native_hit_links': [{'report_index': 0, 'hit_index': 0, 'description_index': 0}]},
        'metadata': None}
    scientific_material = store.register_material(data=canonical(scientific_inputs).encode(),
        name='SYNTHETIC-pairwise-scientific-inputs.json', format='text', use='evidence')
    scientific_evidence = {'content': _content(store, scientific_material['source_ref']), 'pointer': ''}
    parameters = {'version': adapter.PARAMETERS_VERSION, 'scientific_mode': 'pairwise_correspondence',
        'primary_representation': 'raw', 'artifact_source_refs': dict.fromkeys(adapter.FORMATS),
        'scientific_inputs': scientific_evidence, 'tabular_fields': None, 'database_model': None}
    raw_format = {'format': adapter.FORMATS['blast_json15_raw'], 'version': None,
        'mode': 'pairwise_correspondence', 'producer_source_ref': None, 'transformation_evidence': []}
    manifest_format = {'format': 'bvbrc_job_result_json', 'version': None,
        'mode': None, 'producer_source_ref': None, 'transformation_evidence': []}
    requested = adapter.requested_form_schema({
        'query_coverage': {'metric': 'pairwise_query_coverage', 'report_index': 0},
        'reference_coverage': {'metric': 'pairwise_reference_coverage', 'report_index': 0},
        'aligned_pairs': {'metric': 'pairwise_distinct_pairs', 'report_index': 0},
        'identity': {'metric': 'pairwise_identity', 'report_index': 0},
        'missing': {'metric': 'missing_requirements'}})
    selector = {'version': 'bvbrc_appservice_result_selector_v1', 'endpoint': 'requested_projection',
        'requirements': [{'requirement_id': key, 'role': role, 'required': required,
            'declared_format': declared, 'producer_rule_evidence': None, 'exact_object': None}
            for key, role, required, declared in [('manifest', 'job_result_manifest', False, manifest_format),
                ('native', 'blast_json15_raw', True, raw_format)]],
        'adapter': {'adapter_id': 'bvbrc_homology', 'adapter_version': '1', 'parameters': parameters},
        'requested_schema': requested,
        'supplied_metadata': [scientific_evidence, {'content': input_source, 'pointer': ''}],
        'supplied_capabilities': []}
    return SimpleNamespace(request=request, selector=selector, raw=canonical(document).encode(), document=document,
        original_input=original_input, scientific_inputs=scientific_inputs, input_source=input_source,
        input_material=input_material, reference_material=reference_material, reference_member=reference_member,
        scientific_material=scientific_material, scientific_evidence=scientific_evidence,
        raw_format=raw_format, manifest_format=manifest_format)


def _child(role, assignment, scope, schema):
    return {'selection': {'kind': 'episode_child', 'role': role,
        'goal': 'Measure translated residue correspondence between the supplied DNA query and single protein reference through Homology',
        'scope': scope, 'purpose': 'Return the requested aligned-pair count, identity and separate nucleotide-query and amino-acid-reference coverage; retain missing values',
        'assignment': deepcopy(assignment), 'schema_json': json.dumps(schema),
        'initial_report_json': '{}'}, 'report_update': {}}


@pytest.fixture(scope='module')
def pairwise_run():
    (EVIDENCE / 'runs').mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='pairwise-', dir=EVIDENCE / 'runs'))
    source_provenance = _source_provenance()
    _write(directory / 'SOURCE_PROVENANCE.json', source_provenance)
    provenance = {'scope': 'synthetic native responses through actual composed Workflow',
        'scientific_mode': 'pairwise_correspondence', 'live_api': False, 'configured_model': False,
        'native_blast': False, 'hpc': False, 'production_overrides': [],
        'fixture_overrides': ['scripted choices', 'root/scientific continuation', 'NativeClient transport']}
    _write(directory / 'PROVENANCE.json', {**provenance, 'status': 'started'})
    with pytest.MonkeyPatch.context() as patch, Store(directory / 'state') as store:
        target, = store.create_problem(raw_sequence=QUERY, molecule='dna')['subject_refs']
        scope = {'subject_refs': [target]}
        supplied = _pairwise_supplied(store, target)
        manifest_path = '/synthetic/work/output/selected.job_result'
        raw_path = '/synthetic/work/output/selected.raw.json'
        manifest_bytes = canonical({'id': '123', 'app': {'id': 'Homology'}, 'success': 1,
            'parameters': supplied.request['parameters'], 'output_files': [[raw_path, SHOCK_UUID]]}).encode()

        class Responses(NativeClient):
            def rpc(self, command):
                method = command['method']
                if method == 'AppService.start_app2':
                    assert command['params'][0] == 'Homology'
                    assert command['params'][1] == supplied.request['parameters']
                    self.value = {'id': '123', 'application_id': 'Homology', 'state_code': 'Q'}
                elif method == 'Workspace.get':
                    reference, = command['params'][0]['objects']
                    assert command['params'][0]['metadata_only'] == 1
                    if reference == OBJECT_UUID:
                        row = metadata(manifest_path, type='job_result', size=len(manifest_bytes))
                    else:
                        assert reference == raw_path
                        row = metadata(raw_path, uuid=SHOCK_UUID, type='json', size=len(supplied.raw))
                    row['native_row'][8] = {'task_data': {'task_id': '123', 'app_id': 'Homology'}}
                    self.value = [[row['native_row'], None]]
                elif method == 'Workspace.get_download_url':
                    reference, = command['params'][0]['objects']
                    assert reference in (manifest_path, raw_path)
                    self.value = ['https://fixture.invalid/' + ('manifest' if reference == manifest_path else 'raw')]
                else:
                    raise AssertionError(command)
                return super().rpc(command)

            def download(self, url, *, byte_range=None):
                assert byte_range is None and url in ('https://fixture.invalid/manifest', 'https://fixture.invalid/raw')
                self.body = manifest_bytes if url.endswith('/manifest') else supplied.raw
                return super().download(url, byte_range=byte_range)

        native = Responses()
        constructor = BVBRCAppServiceService.__init__

        def configured(self, *args, **kwargs):
            constructor(self, *args, **kwargs)
            self.client = native

        def forbidden(*args, **kwargs):
            raise AssertionError('Pairwise fixture attempted live transport or native execution')

        patch.setattr(BVBRCAppServiceService, '__init__', configured)
        for name in ('socket.create_connection', 'socket.socket.connect', 'socket.socket.connect_ex',
                'urllib.request.OpenerDirector.open', 'subprocess.run', 'subprocess.Popen'):
            patch.setattr(name, forbidden)

        def controllers(path, initial):
            def fixture_estimate(history, parameters, contexts):
                count = {'annotation': 1, 'scientific_process': 5}[path[-1][0]]
                return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= count else 1),
                    parameters, {'fixture': 'root_and_scientific_continuation_only'})
            return YieldController(str(path), initial, 0, YieldParameters(100, 50),
                estimate_with_context=fixture_estimate
                if path[-1][0] in {'annotation', 'scientific_process'} else None)

        assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'selected-api',
            'service': 'bvbrc_appservice', 'request': supplied.request, 'endpoint': 'usable_handoff', 'constraints': {}}
        launch = launch_assignment({'selected-api': assignment})
        handoff_form, result_form = form('execution_handoff_refs'), form('execution_result_refs')
        sources = homology_fact_sources()
        measurements = sources['bvbrc_homology_measurements']['report_schema']
        result_form['properties'].update(measurements=measurements,
            requirements=sources['bvbrc_homology_requirements']['report_schema'])
        result_form['required'].extend(['measurements', 'requirements'])
        parent_form = {'type': 'object', 'additionalProperties': False,
            'properties': {'measurements': deepcopy(measurements)}, 'required': ['measurements']}
        config = deepcopy(CONFIG)
        config['scientific_adapters'] = [{'adapter_id': 'bvbrc_homology', 'adapter_version': '1',
            'implementation_sha256': adapter.implementation_sha256()}]
        factory = ExecutionServiceFactory({'selected-api': config}, {}, 2, 3, .5)
        tools = ToolRegistry(store, clients=Client())
        run_id, run_directory = 'homology-pairwise-selected-workflow', directory / 'run'
        application = factory(store, run_id=run_id, directory=run_directory,
            tool_registry=tools, tool_catalog=tools.catalog())
        descriptor = prepare_scientific_binding(run_directory=run_directory, source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=('scientific_process', 'launch', 'results'),
            resource_catalogs=application.resource_tool_catalogs)
        library = ScientificProcessLibrary(run_directory / 'scientific-process-library')
        selected_tools = [{'name': TOOL_NAME, 'resources': 'api'}, {'name': 'material.parse', 'resources': 'local'}]
        materials = [(supplied.reference_material, 'fasta'), (supplied.input_material, 'text'),
            (supplied.scientific_material, 'text')]

        class Choices:
            def __init__(self):
                self.counts, self.scientific_calls, self.result_objects = {}, [], {}
                self.partial_ref = self.partial_snapshot = None

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
                    return _child('launch_api', assignment, scope, handoff_form)
                if version == 'api_service_assignment_v1':
                    assert execution == assignment
                    if count == 1:
                        return selected(PREFIX + 'prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'Homology'}})
                    assert count == 2
                    return selected(PREFIX + 'submit', {'preparation_receipt_ref':
                        self.last(episode_id)['support_receipt_ref'], 'input_evidence_refs': []})
                if version == 'execution_results_assignment_v1':
                    assert execution['selector'] == supplied.selector
                    if count == 1:
                        return selected(PREFIX + 'task_info', {'handoff_ref': execution['handoff_ref'], 'file': 'job_result_id'})
                    previous = self.last(episode_id)
                    if count == 2:
                        return selected(PREFIX + 'workspace_metadata', {'objects': [{'kind': 'task_info_object',
                            'receipt_ref': previous['support_receipt_ref']}], 'options': {}})
                    if count in (3, 6):
                        obj = {'kind': 'receipt_row', 'receipt_ref': previous['support_receipt_ref'], 'row_pointer': '/result/0/0'}
                        self.result_objects[count] = obj
                        return selected(PREFIX + 'download_capability', {'objects': [obj],
                            'generation': 0, 'predecessor_receipt_ref': None})
                    if count in (4, 7):
                        manifest = count == 4
                        return selected(PREFIX + 'download', {'object': self.result_objects[count - 1],
                            'capability': {'kind': 'acquired', 'receipt_ref': previous['support_receipt_ref'], 'input_index': 0},
                            'byte_range': None, 'requirement_ids': ['manifest' if manifest else 'native'],
                            'role': 'job_result_manifest' if manifest else 'blast_json15_raw',
                            'declared_format': supplied.manifest_format if manifest else supplied.raw_format})
                    assert count == 5
                    self.partial_ref = previous['source_ref']
                    self.partial_snapshot = api.read_result(self.partial_ref, scope)
                    assert self.partial_snapshot['publication']['completion_proof'] is None
                    return selected(PREFIX + 'workspace_metadata', {'objects': [{'kind': 'manifest_member',
                        'manifest_receipt_ref': previous['support_receipt_ref'], 'output_index': 0}], 'options': {}})
                if 'scientific_process' in current:
                    self.scientific_calls.append((deepcopy(current), instructions))
                    assert current['scientific_process']['selection']['child_tool_info'] == selected_tools
                    if count <= 3:
                        material, format = materials[count - 1]
                        return selected('material.parse', {'material_ref': material['id'], 'format': format})
                    if count == 4:
                        return _child('launch', launch, scope, handoff_form)
                    assert count == 5
                    received = current['child_reports'][-1]
                    assert received['completed'] and received['yield']['expected_next_gain'] == NumericBand.exact(0).as_record()
                    handoff, = received['references']
                    return _child('results', {'version': 'execution_results_assignment_v1',
                        'handoff_ref': handoff, 'selector': supplied.selector}, scope, result_form)
                assert count == 1 and episode_id == episode.source.episode_id
                available = workflow.scientific_process_binding.tool_library.parent_tool_info(
                    workflow.services.tool_information_catalog(scope))
                assert all(any((row['name'], row['resources']) == (tool['name'], tool['resources'])
                    for row in available) for tool in selected_tools)
                scientific = {'selection': {'version': 'scientific_process_selection_v3',
                    'evidence_axis': library.reference('A101'), 'thought_pattern': library.reference('P01'),
                    'child_tool_info': deepcopy(selected_tools)}, 'evidence_refs': [target],
                    'constraints': {'preserve_original_query': True}, 'context': {'supplied_sequence': QUERY,
                        'molecule': 'dna', 'complete': True, 'label_is_public_identity': False,
                        'supplied_material_refs': [material['id'] for material, _ in materials]}}
                return _child('scientific_process', scientific, scope, parent_form)

            async def release(self, episode_id):
                pass

        choices = Choices()
        workflow = Workflow(store, tools, choices, run_directory, run_id,
            controller_factory=controllers, project_credit=lambda *_: 0,
            episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
            role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider,
            annotation_child_roles=('scientific_process',), episode_record_receipts=True, initial_known_record_refs=[])
        api = workflow.episode_bindings.for_role('results').api_execution
        episode = workflow.build('annotation', 'root',
            'Measure translated correspondence between the supplied DNA and single protein reference', scope)

        async def execute():
            record = await episode.run_async(workflow.context)
            await episode.build_result(record)
            return record

        record = asyncio.run(execute())
        archive = json.loads(''.join(iter_json(record.as_record())))
        scientific = archive['units'][0]['child']
        launch_record, results = scientific['units'][3]['child'], scientific['units'][4]['child']
        api_record = launch_record['units'][0]['child']
        returned = json.loads(workflow.journal.row('runtime_forms', results['episode_id'])['form'])
        forwarded = json.loads(workflow.journal.row('runtime_forms', scientific['episode_id'])['form'])
        final_ref, = {row['source_ref'] for row in returned['measurements']}
        body = api.read_result(final_ref, scope)
        saved = body['publication']['adapter_result']
        sheet_bytes = store.get_artifact(saved['sheet_content']['artifact_ref'])
        components_bytes = store.get_artifact(saved['components_content']['artifact_ref'])
        for name, value in (('archive', archive), ('results-return', returned), ('scientific-return', forwarded),
                ('publication', body), ('native-calls', native.calls), ('original-input', supplied.original_input)):
            _write(directory / (name + '.json'), value)
        for name, content in (('native-raw.json', supplied.raw), ('native-manifest.json', manifest_bytes),
                ('sheet.json', sheet_bytes), ('components.json', components_bytes)):
            (directory / name).write_bytes(content)
        for index, (current, instructions) in enumerate(choices.scientific_calls):
            (directory / f'scientific-presentation-{index}.txt').write_text(render_scientific_process_prompt(current, instructions))
        _write(directory / 'PROVENANCE.json', {**provenance, 'status': 'workflow_closed',
            'returned_measurements': {row['field']: row['value'] for row in returned['measurements']},
            'expected_measurements': MEASUREMENTS, 'native_raw_sha256': hashlib.sha256(supplied.raw).hexdigest(),
            'native_raw_byte_count': len(supplied.raw)})
        source_after = _source_provenance(source_provenance['files'])
        _write(directory / 'SOURCE_PROVENANCE_AFTER.json', source_after)
        assert all(source_after[key] == value for key, value in source_provenance.items()
            if key != 'loaded_modules')
        yield SimpleNamespace(store=store, workflow=workflow, api=api, native=native, choices=choices,
            record=record, archive=archive, scientific=scientific, launch=launch_record, api_record=api_record,
            results=results, returned=returned, forwarded=forwarded, final_ref=final_ref, body=body,
            scope=scope, supplied=supplied, directory=directory, run_directory=run_directory,
            sheet=json.loads(sheet_bytes), components=json.loads(components_bytes), episode=episode,
            selected_tools=selected_tools, library=library, manifest_bytes=manifest_bytes, config=config)


def test_pairwise_library_selection_preserves_owners_and_actual_supplied_inputs(pairwise_run):
    run = pairwise_run
    context = run.api.appservice.custody.context(run.scientific['episode_id'])
    binding = run.workflow.scientific_process_binding
    binding.validate_context(context)
    information = binding.tool_library.resolve_tool_info(run.selected_tools,
        run.workflow.services.tool_information_catalog(run.scope))
    assert plain(context.assignment)['selection']['child_tool_info'] == information
    assert plain(context.assignment)['selection']['evidence_axis'] == run.library.reference('A101')
    assert plain(context.assignment)['selection']['thought_pattern'] == run.library.reference('P01')
    direct = {row['name'] for row in binding.catalog(context)}
    assert 'material.parse' in direct and TOOL_NAME not in direct
    assert not any(name.startswith(PREFIX) for name in direct)
    assert run.workflow.catalog(run.scope, source=run.episode.source) == []
    contracts = binding.tool_library.resolve_invocations(run.selected_tools,
        run.workflow.services.tool_information_catalog(run.scope))
    homology = next(row for row in contracts if row['name'] == TOOL_NAME)
    assert homology['invocation_route'] == {'kind': 'commission', 'routes': [
        {'entry_role': 'launch', 'resource_id': 'selected-api', 'resource_role': 'launch_api'},
        {'entry_role': 'results', 'resource_id': 'selected-api', 'resource_role': 'results'}]}
    for index, (current, _) in enumerate(run.choices.scientific_calls):
        assert current['scientific_process']['child_tool_info'] == information
        prompt = (run.directory / f'scientific-presentation-{index}.txt').read_text()
        task, steering = prompt.split('\n\nSTEERING', 1)
        assert task.startswith('TASK\n') and homology['instructions'] in task
        assert homology['instructions'] not in steering
    for material in (run.supplied.reference_material, run.supplied.input_material, run.supplied.scientific_material):
        assert run.api.appservice.custody.possession(context, material['source_ref']) == 'own_completed_action'
    owner = run.api.appservice.custody.original_job_owner(run.api.appservice.custody.context(run.api_record['episode_id']))
    assert owner['launch_episode_id'] == run.launch['episode_id']
    assert owner['parent_commission_operation_key'] == f'{run.workflow.run_id}:{context.episode_id}:3'
    assert run.scope == {'subject_refs': run.store.problem()['subject_refs']}
    assert run.supplied.reference_member['id'] not in run.scope['subject_refs']
    original = run.supplied.original_input
    query, = original['query_members']
    reference, = original['reference_members']
    assert (query['sequence'], query['length'], query['sequence_sha256']) == (QUERY, 15, hashlib.sha256(QUERY.encode()).hexdigest())
    assert (reference['sequence'], reference['length'], reference['sequence_sha256']) == (REFERENCE, 5, hashlib.sha256(REFERENCE.encode()).hexdigest())
    assert run.store.material_member(reference['member_id'])['sequence'] == REFERENCE
    assert len(original['database']['members']) == original['database']['member_count'] == 1
    assert run.body['service_request']['input_bindings'] == run.supplied.request['input_bindings']
    assert run.body['bundle']['original_task']['submitted_parameters'] == run.supplied.request['parameters']
    assert run.body['bundle']['input_bindings'][1]['parameter_pointer'] == '/db_fasta_data'
    assert run.body['bundle']['input_bindings'][1]['inline_value'] == original['reference_fasta']


def test_actual_translated_pairwise_measurements_reach_both_receivers(pairwise_run):
    run = pairwise_run
    assert {row['field']: row['value'] for row in run.returned['measurements']} == MEASUREMENTS
    assert run.returned['completed'] is True
    assert run.forwarded == {'measurements': run.returned['measurements']}
    assert run.returned['requirements'] == [{'source_ref': run.final_ref, 'field': 'missing', 'requirements': []}]
    for child, parent, expected in ((run.results, run.scientific, run.returned),
            (run.scientific, run.archive, run.forwarded)):
        admission = run.store.db.execute('SELECT parent_episode_id,form,failure FROM runtime_report_attempts '
            'WHERE run_id=? AND child_episode_id=?', (run.workflow.run_id, child['episode_id'])).fetchone()
        assert admission['parent_episode_id'] == parent['episode_id']
        assert admission['failure'] is None and json.loads(admission['form']) == expected
        context = run.api.appservice.custody.context(parent['episode_id'])
        values = {row['fact_source']: row['facts'] for row in run.api.homology_returns.received_context(context)}
        assert values['bvbrc_homology_measurements'] == expected['measurements']
        assert 'bvbrc_homology_function_weights' not in values
    saved = run.body['publication']['adapter_result']
    assert saved['facts'] == {**MEASUREMENTS, 'missing': []}
    assert run.body['publication_inputs']['selector'] == run.supplied.selector
    assert run.body['publication_inputs']['adapter_implementation_sha256'] == run.config['scientific_adapters'][0]['implementation_sha256']
    assert saved['sheet_content']['source_ref'] != saved['components_content']['source_ref']
    artifacts = {row['role']: row for row in run.body['bundle']['artifacts']}
    raw = artifacts['blast_json15_raw']
    assert run.store.get_artifact(raw['raw_artifact_ref']) == run.supplied.raw
    assert run.store.get_artifact(artifacts['job_result_manifest']['raw_artifact_ref']) == run.manifest_bytes
    assert raw['task_association']['kind'] == 'task_result_manifest'
    assert raw['task_association']['evidence_ref'] == artifacts['job_result_manifest']['source_ref']
    assert raw['task_association']['pointer'] == '/output_files/0'
    assert raw['workspace_object']['uuid'] == SHOCK_UUID and raw['workspace_object']['metadata_receipt_ref']
    assert raw['transfer']['body_complete'] and raw['transfer']['object_complete'] == 'yes'
    assert raw['task_association']['byte_version_status'] != 'producer_bytes_bound'
    assert run.sheet['binding']['c4_bundle'] == run.body['bundle']
    query, = run.sheet['queries']
    assert query['query_binding_status'] == 'validated'
    normalized = query['normalized_result']
    hit, = normalized['hits']
    native, = hit['hsps']
    assert native['qseq'] == str(Seq(QUERY[:9]).translate(table=1)) == 'MKT'
    assert native['hseq'] == REFERENCE[:3] == 'MKT'
    assert (native['query_from'], native['query_to'], native['query_frame']) == (1, 9, 1)
    assert (native['hit_from'], native['hit_to']) == (1, 3)
    assert normalized['query']['length'] == 15 and hit['length'] == 5
    assert native['source_locator']['pointer'].endswith('/hits/0/hsps/0')
    pairwise = query['blast_sheet']
    assert pairwise['schema'] == 'blast_pairwise_sheet_v1'
    hsp, = pairwise['hsps']
    assert hsp['components']['coordinate_units'] == {'query': 'nt', 'reference': 'aa', 'alignment': 'aa'}
    assert hsp['components']['counts']['paired_query_positions'] == 9
    assert hsp['components']['counts']['paired_reference_positions'] == 3
    assert pairwise['union']['denominators'] == {'query_length': 15, 'reference_length': 5, 'distinct_residue_pairs': 3}
    pairs = pairwise['union']['pairs']
    assert [[p['query_start'], p['query_end']] for p in pairs] == [[0, 3], [3, 6], [6, 9]]
    assert [[p['reference_start'], p['reference_end']] for p in pairs] == [[0, 1], [1, 2], [2, 3]]
    assert pairwise['union']['fractions'] == {'query_paired_coverage': 9 / 15,
        'reference_paired_coverage': 3 / 5, 'paired_identity': 1}
    assert run.components['queries'][0]['conditional_function_weights'] is None
    assert run.sheet['binding']['adapter_parameters']['database_model'] is None


def test_actual_action_accounting_and_immediate_practical_completion(pairwise_run):
    run = pairwise_run
    expected = [(run.archive, ['episode_child:scientific_process']),
        (run.scientific, ['material.parse'] * 3 + ['episode_child:launch', 'episode_child:results']),
        (run.launch, ['episode_child:launch_api']), (run.api_record, [PREFIX + 'prepare', PREFIX + 'submit']),
        (run.results, [PREFIX + name for name in ('task_info', 'workspace_metadata',
            'download_capability', 'download', 'workspace_metadata', 'download_capability', 'download')])]
    for closed, names in expected:
        assert closed['units_consumed'] == len(names) == run.choices.counts[closed['episode_id']]
        for table in ('runtime_actions', 'runtime_observations', 'runtime_model_calls'):
            assert run.store.db.execute('SELECT count(*) FROM ' + table + ' WHERE run_id=? AND episode_id=?',
                (run.workflow.run_id, closed['episode_id'])).fetchone()[0] == len(names)
        actions = [json.loads(row[0]) for row in run.store.db.execute(
            'SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index',
            (run.workflow.run_id, closed['episode_id']))]
        assert [a['tool'] if a['kind'] == 'tool' else a['kind'] + ':' + a['role'] for a in actions] == names
    for closed in (run.launch, run.api_record, run.results):
        assert closed['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert closed['units'][-1]['controller_step']['marginal_credit'] > 0
    for closed in (run.archive, run.scientific):
        assert [u['controller_step']['marginal_credit'] for u in closed['units']] == [0] * closed['units_consumed']
    assert run.store.count('annotation') == run.store.count('observation') == 0
    decisions = run.store.db.execute('SELECT a.action,m.response,m.purpose FROM runtime_actions a '
        'JOIN runtime_model_calls m ON m.run_id=a.run_id AND m.episode_id=a.episode_id '
        'AND m.call_index=a.decision_index WHERE a.run_id=?', (run.workflow.run_id,)).fetchall()
    assert len(decisions) == 16
    assert all(row['purpose'] == 'decision' and json.loads(row['action']) == json.loads(row['response'])['selection']
        for row in decisions)
    assert [call[0] for call in run.native.calls] == ['rpc', 'task_info', 'rpc', 'rpc', 'download', 'rpc', 'rpc', 'download']


def _assert_saved_pairwise_recalculation_and_replay(run):
    """Check the actual host outcome and its separate Workflow enrichment."""
    calls, sheet = deepcopy(run.native.calls), deepcopy(run.sheet)
    counts = {table: run.store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
        for table in ('runtime_actions', 'runtime_model_calls', 'runtime_observations', 'runtime_report_attempts')}

    assert calculate_homology_scores(sheet) == run.components
    assert sheet == run.sheet
    with pytest.raises(ValueError, match='homology_database_model_unused_for_pairwise'):
        calculate_homology_scores(sheet, database_model={'temperature_bits': 1})
    assert run.api.read_result(run.final_ref, run.scope) == run.body
    context = run.api.appservice.custody.context(run.results['episode_id'])
    key = run.body['publication']['origin']['operation_key']
    index = int(key.rsplit(':', 1)[1])
    action = dict(run.store.db.execute('SELECT * FROM runtime_actions WHERE run_id=? '
        'AND episode_id=? AND decision_index=?', (run.api.run_id, context.episode_id, index)).fetchone())
    selection = json.loads(action['action'])
    host_path = run.api._manifest(context, create=False) / 'actions' / digest(key) / 'outcome.json'
    host_outcome = json.loads(host_path.read_text())
    recorded = json.loads(action['result'])
    pending = recorded['pending_work_after_action']
    assert set(pending) == {'version', 'captured_at', 'items'}
    assert pending['version'] == 'pending_work_v1' and pending['items'] == []
    assert isinstance(pending['captured_at'], str) and pending['captured_at']
    assert recorded == {**host_outcome, 'pending_work_after_action': pending}
    assert asyncio.run(run.api.execute(context, selection['tool'], selection['arguments'], key)) == host_outcome
    assert run.native.calls == calls
    assert {table: run.store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] for table in counts} == counts
    assert dict(run.store.db.execute('SELECT * FROM runtime_actions WHERE run_id=? '
        'AND episode_id=? AND decision_index=?', (run.api.run_id, context.episode_id, index)).fetchone()) == action
    assert json.loads(run.store.db.execute('SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?',
        (run.api.run_id, context.episode_id)).fetchone()[0]) == run.returned
    _write(run.directory / 'saved-sheet-recalculation.json', run.components)
    _write(run.directory / 'saved-replay-verification.json', {'operation_key': key,
        'host_outcome_path': str(host_path), 'host_outcome': host_outcome,
        'workflow_pending_work_after_action': pending, 'durable_action_unchanged': True,
        'counts_before': counts, 'counts_after': counts, 'native_calls_added': 0,
        'saved_sheet_recalculation_equal': True})


def test_partial_missing_values_and_saved_sheet_recalculation_replay(pairwise_run, monkeypatch):
    run = pairwise_run
    early = run.api.read_result(run.choices.partial_ref, run.scope)
    assert early == run.choices.partial_snapshot
    assert early['status'] == 'partial' and early['publication']['completion_proof'] is None
    assert all(early['publication']['adapter_result']['facts'][field] is None for field in MEASUREMENTS)
    assert early['publication']['adapter_result']['missing_requirements']
    assert all(row['source_ref'] != run.choices.partial_ref for row in run.forwarded['measurements'])

    def forbidden(*args, **kwargs):
        raise AssertionError('Saved recalculation/replay attempted native acquisition')

    for name in ('rpc', 'task_info', 'download'):
        monkeypatch.setattr(run.native, name, forbidden)
    _assert_saved_pairwise_recalculation_and_replay(run)


def test_reference_digest_mismatch_is_not_a_valid_pairwise_proof(pairwise_run):
    """Retained source custody must not promote contradictory subject claims."""
    run = pairwise_run
    bundle = deepcopy(run.body['bundle'])
    inputs = deepcopy(run.supplied.scientific_inputs)
    inputs['subject_binding']['sequence_sha256'] = hashlib.sha256(b'AAAAA').hexdigest()
    material = run.store.register_material(data=canonical(inputs).encode(),
        name='SYNTHETIC-contradictory-reference-claim.json', format='text', use='evidence')
    evidence = {'content': _content(run.store, material['source_ref']), 'pointer': ''}
    bundle['supplied_scientific_metadata'][0] = evidence
    parameters = deepcopy(run.supplied.selector['adapter']['parameters'])
    parameters['scientific_inputs'] = evidence
    values = [{'evidence': evidence, 'value': inputs},
        {'evidence': bundle['supplied_scientific_metadata'][1], 'value': run.supplied.original_input}]
    result = adapter.consume_bundle(bundle,
        artifact_bytes={row['raw_artifact_ref']: run.store.get_artifact(row['raw_artifact_ref']) for row in bundle['artifacts']},
        supplied_values=values, parameters=parameters, requested_form=run.supplied.selector['requested_schema'])
    _write(run.directory / 'contradictory-reference-claim-result.json', result)
    assert result['status'] == 'partial', result['facts']
    assert all(result['facts'][field] is None for field in MEASUREMENTS)
    assert result['missing_requirements']
