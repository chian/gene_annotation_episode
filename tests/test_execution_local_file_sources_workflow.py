"""Opt-in genuine file custody and non-native FBA receiving-context admission.

The supplied model was actually edited and solved by212. This case copies its
unchanged bytes through a new generic job; it does not repeat the edit or FBA
solve, or claim an additional scientific measurement from a file transfer.
The scripted parent explicitly receives the unchanged Rhea210 mapping first.
The later compact FBA child only initializes/inspects its original input control;
it never prepares, starts or completes an FBA execution.
The explicit retained245 mode continues its saved unanswered call and completed
copy; it repeats neither the lookup nor the generic execution.
"""
import asyncio
from copy import deepcopy
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path
import sys

import pytest
from jsonschema import Draft202012Validator
from method_loop.archive import iter_json

from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.communication import plain, validate_closed_schema
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.flux_balance_request_binding import materialized_assignment, read_request_binding
from gene_annotation_episode.native_flux_balance_contracts import POLICY, validate_flux_balance_software
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


G = import_module('verification.tool_graders_expression_nmf_episode_path_2026-10-27_490.fixture_helpers')
ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
MODEL_SHA = 'd17368c1769aed2e311e7d3dd7e1cddfac454cf94aa1e756e4f49a97275a77eb'
RECEIPT_SHA = 'c2eed01e14137524a54705463318552410af5a9df920f12ebd152ea380c110da'
SOFTWARE_SHA = '9a35a5c56d9672957322865f4f105b279b432a3f22ea8a96f0ef8f0ced2e05e5'
RHEA_CAPTURE_SHA = 'a8f987d37abf10904d30b235eaf2cee8481307b8e4ea1105f0dbfabac484e641'
RHEA_BODY_SHA = 'e6e0533ec0df9f0d7b9920cdc64bb3efb30038ab4c21bd4b7b85ce835c14a0df'
GENERIC_INVOKE_SHA = 'cda813d9398fe1052159ffce67a6f21414514fbf91c986853872bc256fb2b23f'
RUN_ID = 'generic-local-model-source-workflow'


def _selected_bytes(name, sha256, size):
    path = Path(os.environ[name])
    assert path.is_absolute()
    raw = path.read_bytes()
    assert len(raw) == size and hashlib.sha256(raw).hexdigest() == sha256
    return path, raw


def _parent_form(definition):
    return validate_closed_schema({'type': 'object', 'properties': {
        'files': deepcopy(definition['report_schema'])},
        'required': ['files'], 'additionalProperties': False})


def _controller(path, initial):
    # Explicit caller-owned engineering continuation, through the ordinary
    # estimator port. No runtime action cap or practical completion is added.
    role = path[-1][0]
    horizon = (6 if role == 'scientific_process' and len(path) == 2 else
        3 if role == 'scientific_process' else 2 if role == 'results' else 1)
    def estimate(raw, parameters, contexts):
        return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1), parameters,
            {'fixture': 'selected_file_transfer_and_non_native_input_admission_only'})
    return YieldController(str(path), initial, 0, YieldParameters(100, 50), estimate_with_context=estimate)


def _capture_privacy_view(current, model_text, model_instructions, definitions, private_values):
    # These exact source-owned schema words describe field names. They are not
    # values of an original operation or a resolved host path. Do not exempt
    # other schema values, modified schemas, or the same words elsewhere.
    vocabulary = {
        'execution.blast_utility_database_fields': {'vdb_resolved_paths'},
        'execution.blast_utility_missing': {'vdb_resolved_paths'},
        **{name: {'original_operation_key', 'result_operation_key'} for name in (
            'execution_protein_structure_failures', 'execution_protein_structure_projections',
            'execution_protein_structure_saved_sheets', 'execution_protein_structure_sequences')},
    }
    private = ('requested_job', 'execution_id', 'operation_key', 'source_payload',
        'whole_file_bridge', 'resolved_path', 'implementation_files', 'runtime_files',
        'solver_runtime_files', 'PYTHONHOME', 'PYTHONPATH', 'verified_cgroup', 'source_function_sha256')

    def schema_words(value, words):
        if isinstance(value, dict):
            return {('[registered schema field]' if key in words else key): schema_words(item, words)
                for key, item in value.items()}
        if isinstance(value, list):
            return [schema_words(item, words) for item in value]
        return '[registered schema field]' if isinstance(value, str) and value in words else value

    checked = deepcopy(plain(current))
    for name, words in vocabulary.items():
        actual = checked['available_report_facts'][name]['report_schema']
        assert actual == definitions[name]['report_schema'], 'registered capture schema changed'
        checked['available_report_facts'][name]['report_schema'] = schema_words(actual, words)
    if model_text.lstrip().startswith('{'):
        # The current production fallback is JSON. Preserve the actual text in
        # evidence; this comparison is only the test's privacy classification.
        assert json.loads(model_text) == plain(current)
        checked_text = canonical(checked)
    else:
        checked_text = model_text
    shown = canonical({'context': checked, 'model_text': checked_text,
        'model_instructions': model_instructions})
    assert not any(key in shown for key in private), 'private capture controls entered actual production presentation'
    actual_shown = canonical({'context': plain(current), 'model_text': model_text,
        'model_instructions': model_instructions})
    assert not any(value in actual_shown for value in private_values), 'actual private capture value entered presentation'


def _closed_rows(store):
    predicates = {'runtime_actions': 'result IS NOT NULL AND credit IS NOT NULL',
        'runtime_model_calls': 'response IS NOT NULL', 'runtime_episodes': "state='yielded'"}
    tables = (*predicates, 'runtime_observations', 'runtime_forms', 'runtime_report_attempts',
        'tool_operations', 'records', 'artifacts', 'runtime_record_receipts', 'runtime_receipt_inheritance')
    return {table: {tuple(row) for row in store.db.execute(
        'SELECT * FROM ' + table + (' WHERE ' + predicates[table] if table in predicates else ''))}
        for table in tables}


@pytest.mark.skipif(not os.environ.get('HMMER_NATIVE_ORACLE_FILE_CAPTURE_SUPPLIED_MODEL'),
    reason='requires explicit retained212 model and selected bounded runtime')
def test_genuine_generic_job_typed_file_source_and_compact_fba_admission(tmp_path, monkeypatch):
    assert os.environ.get('HMMER529_ATTEMPT'), 'native execution requires the bounded529 runtime'
    model_path, model_raw = _selected_bytes('HMMER_NATIVE_ORACLE_FILE_CAPTURE_SUPPLIED_MODEL', MODEL_SHA, 1974)
    receipt_path, receipt_raw = _selected_bytes('HMMER_NATIVE_ORACLE_FILE_CAPTURE_ADDITION_RECEIPT', RECEIPT_SHA, 2993)
    _, software_raw = _selected_bytes('HMMER_NATIVE_ORACLE_FBA716_SOFTWARE', SOFTWARE_SHA, 3540474)
    software = validate_flux_balance_software(json.loads(software_raw))
    prior = json.loads(receipt_raw)
    assert prior['edited_model']['sha256'] == MODEL_SHA and prior['optimization_calls'] == 0
    assert prior['source_direction'] == 'undefined'
    capture_path = Path(os.environ['HMMER_NATIVE_ORACLE_RHEA_WORKFLOW_CAPTURE'])
    assert capture_path.is_absolute()
    capture_raw = capture_path.read_bytes()
    assert hashlib.sha256(capture_raw).hexdigest() == RHEA_CAPTURE_SHA
    capture = json.loads(capture_raw)
    assert capture['schema'] == 'rhea_live_reaction_acquisition_v1' and capture['replay_verified']
    assert capture['request'] == {'operation': 'public.rhea.reaction', 'arguments': {'accession': 'RHEA:11740'}}
    body = Path(capture['native_body']['path']).read_bytes()
    assert len(body) == capture['native_body']['size_bytes'] == 1010
    assert hashlib.sha256(body).hexdigest() == capture['native_body']['sha256'] == RHEA_BODY_SHA
    original_rhea_source = capture['source_record']
    metadata = capture['request_metadata']
    mapping_refs = capture['outcome']['record_refs']
    expected_mapping = {row['id']: row for row in [original_rhea_source,
        *capture['reaction_records'], *capture['reaction_references'], *capture['chemical_references']]}
    assert len(mapping_refs) == len(expected_mapping) == 8 and set(mapping_refs) == set(expected_mapping)
    reaction, = capture['reaction_records']
    assert prior['reaction_record_ref'] == reaction['id']
    assert prior['source_ref'] == reaction['source_ref'] == original_rhea_source['id']
    assert prior['source_accession'] == reaction['accession'] == 'RHEA:11740'
    model = json.loads(model_raw)
    selected_reaction, = [row for row in model['reactions'] if row['id'] == prior['reaction_id']]
    assert selected_reaction['annotation']['rhea'] == reaction['accession']
    assert selected_reaction['metabolites'] == prior['stoichiometry']

    class RetainedNativeRhea:
        def __init__(self):
            self.calls = []

        def rhea_reaction(self, accession):
            assert accession == 'RHEA:11740'
            self.calls.append(deepcopy(capture['request']))
            return SourceSnapshot('rhea', original_rhea_source['uri'], deepcopy(metadata['request']),
                original_rhea_source['retrieved_at'], body, 'application/json', deepcopy(metadata['transport']))

    client = RetainedNativeRhea()
    retained_case = os.environ.get('HMMER_NATIVE_ORACLE_FILE_CAPTURE_RETAINED_CASE')
    directory = Path(retained_case) if retained_case else tmp_path / 'genuine-local-source'
    copy_wrapper_python = sys.executable
    if retained_case:
        assert directory.is_absolute() and directory.name == 'genuine-local-source'
        assert (directory / 'state/state.sqlite3').is_file()
        original_attempt = directory.parents[3]
        original_request = json.loads((original_attempt / 'selected_request.json').read_text())
        assert Path(original_request['environment']['TMPDIR']) == directory.parents[2]
        copy_wrapper_python = original_request['argv'][0]
        evidence_path = Path(os.environ['HMMER529_ATTEMPT']) / 'retained245-continuation.json'
        old_marker = directory / 'verified-file-source-workflow.json'
        old_marker_pin = {'size_bytes': old_marker.stat().st_size,
            'sha256': hashlib.sha256(old_marker.read_bytes()).hexdigest()}
    else:
        directory.mkdir()
        evidence_path = directory / 'verified-file-source-workflow.json'
    workspace = directory / 'workspace'
    if not retained_case:
        workspace.mkdir()
    output_path = workspace / 'received-edited-model.json'
    with Store(directory / 'state') as store:
        if not retained_case:
            store.create_problem(raw_sequence='ACGTACGT', molecule='dna')
        scope = store.validate_scope()
        closed_before = _closed_rows(store) if retained_case else None
        if retained_case:
            provenance_record, = [row for row in store.list('source')
                if row['provider'] == 'supplied_actual212_addition_receipt']
            original_record, = [row for row in store.list('source')
                if row['provider'] == 'supplied_actual212_edited_control']
            provenance_source, original_source = provenance_record['id'], original_record['id']
            assert provenance_record['uri'] == receipt_path.as_uri()
            assert original_record['uri'] == model_path.as_uri()
            assert original_record['parent_source_refs'] == [provenance_source]
            assert store.get_artifact(original_record['artifact_ref']) == model_raw
            assert store.get_artifact(provenance_record['artifact_ref']) == receipt_raw
        else:
            original_artifact = store.artifact(model_raw, 'application/json')
            provenance_artifact = store.artifact(receipt_raw, 'application/json')
            provenance_source = store.put('source', {'provider': 'supplied_actual212_addition_receipt',
                'accession': None, 'uri': receipt_path.as_uri(), 'artifact_ref': provenance_artifact,
                'text_ref': provenance_artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='tool')['id']
            original_source = store.put('source', {'provider': 'supplied_actual212_edited_control',
                'accession': None, 'uri': model_path.as_uri(), 'artifact_ref': original_artifact,
                'text_ref': original_artifact, 'request_ref': None, 'version': None, 'retrieved_at': None,
                'parent_source_refs': [provenance_source]}, origin='tool')['id']
        input_path = store.path / 'artifacts' / MODEL_SHA[:2] / MODEL_SHA
        requested = {'argv': [software['python']['path'], '-B', '-S', '-c',
            'import shutil,sys; shutil.copyfile(sys.argv[1],sys.argv[2])', str(input_path), str(output_path)],
            'environment': {'PYTHONHOME': software['python_home'], 'PYTHONDONTWRITEBYTECODE': '1',
                'PYTHONNOUSERSITE': '1'}}
        practical = {'version': 'practical_assignment_v1', 'assignment_id': 'selected-generic-file-transfer',
            'resource_id': 'here', 'resource_kind': 'local', 'workspace': str(workspace),
            'endpoint': 'usable_handoff', 'requested_job': requested,
            'progress_requirements': [{'key': 'original_handoff', 'credit': 7,
                'predicate': {'kind': 'requested_job_handoff'}}], 'completion_keys': ['original_handoff'],
            'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
            'inventory_snapshot': {}, 'constraints': {'allocation': deepcopy(POLICY)}}
        # The original job has no requested_job_outputs declaration. The later
        # file selection uses the existing local workspace access policy.
        launch = {'version': 'execution_launch_assignment_v1', 'requests': {'here': practical},
            'immutable_input_versions': [{'reference': original_source, 'version': None,
                'content_sha256': MODEL_SHA}], 'constraints': {'allowed_resource_ids': ['here'],
                'allowed_kinds': ['local'], 'allocation': deepcopy(POLICY)}}
        resources = {'here': {'kind': 'local', 'workspace': str(workspace), 'policy': deepcopy(POLICY),
            'native_flux_balance': [{'version': 'flux_balance_local_binding_v1',
                'operation': 'perform_flux_balance_analysis', 'mode': 'steady_state_linear_fba',
                'software': software, 'model_formats': ['cobra_json']}]}}
        factory = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)
        tools = ToolRegistry(store, clients=client, job_limits=deepcopy(POLICY))
        application = factory(store, run_id=RUN_ID, directory=directory / 'run', tool_registry=tools)
        binding = prepare_scientific_binding(run_directory=directory / 'run', source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=('scientific_process', 'launch', 'results'),
            resource_catalogs=application.resource_tool_catalogs)
        library = ScientificProcessLibrary(directory / 'run/scientific-process-library')
        axis, pattern = library.reference('A110'), library.reference('P10')
        assert library.resolve(axis)['name'] == 'Biochemical feasibility and chemical/resource accounting'
        assert library.resolve(pattern)['name'] == 'Account for the coupled chemical system'
        scientific = {'selection': {'version': 'scientific_process_selection_v3',
            'evidence_axis': axis, 'thought_pattern': pattern,
            'child_tool_info': [{'name': name, 'resources': 'local'} for name in (
                'practical.job.start', 'execution.results.collect', 'source.read', 'state.query', 'perform_flux_balance_analysis')]},
            'evidence_refs': [*scope['subject_refs'], original_source, provenance_source],
            'constraints': {'no_fresh_http': True, 'allocation': deepcopy(POLICY)},
            'context': {'supplied_edited_model_source': original_source,
                'meaning': 'prior actual212 numerical control; transfer is not a new edit or solve',
                'hypothetical_question': 'Receive the source reaction correspondence, then inspect whether the '
                    'captured control model can be commissioned with the corresponding reaction clamped to zero; '
                    'do not infer a gene correspondence, biological growth or a new flux measurement.'}}
        lookup = {'selection': {'version': 'scientific_process_selection_v3',
            'evidence_axis': axis, 'thought_pattern': pattern,
            'child_tool_info': [{'name': name, 'resources': resource} for name, resource in (
                ('public.rhea.reaction', 'api'), ('state.query', 'local'), ('source.read', 'local'))]},
            'evidence_refs': scope['subject_refs'], 'constraints': {'no_fresh_http': True},
            'context': {'fixture_owner': 'retained_mapping_lookup',
                'meaning': 'unchanged authentic210 source records; no new HTTP or target annotation'}}
        mapping_form = validate_closed_schema({'type': 'object', 'properties': {
            'mapping_refs': {'type': 'array', 'uniqueItems': True,
                'items': {'type': 'string', 'format': 'reference'}, 'x-source': 'committed_record_refs'}},
            'required': ['mapping_refs'], 'additionalProperties': False})
        parent_form = None
        native_calls = {'prepare': [], 'start': []}
        original_prepare = native_lifecycle.prepare_job
        original_start, original_resume = native_lifecycle.start_prepared, native_lifecycle.resume_start
        original_handle = LocalPracticalOperations._handle
        copy_reservation = {}

        def only_copy_handle(operations, state, operation_key, command, **options):
            assert provider.copy_context is not None
            assert state.run_id == RUN_ID and state.episode_id == provider.copy_context.episode_id
            assert operation_key == f'{RUN_ID}:{provider.copy_context.episode_id}:0'
            assert state.assignment['requested_job'] == requested
            assert command == requested['argv'] and options['env'] == requested['environment']
            assert str(options['cwd']) == str(workspace)
            selected = {'operation_key': operation_key, 'directory': str(workspace / '.episode-operations' /
                digest({'run': state.run_id, 'episode': state.episode_id}) / digest(operation_key))}
            assert not copy_reservation or copy_reservation == selected
            copy_reservation.update(selected)
            return original_handle(operations, state, operation_key, command, **options)

        def selected_copy_invocation(command, root):
            root = Path(root)
            assert provider.copy_context is not None
            expected_parent = workspace / '.episode-operations' / digest({
                'run': RUN_ID, 'episode': provider.copy_context.episode_id})
            assert root.parent == expected_parent and str(root) == copy_reservation['directory']
            runner, invocation = root / 'invoke.py', root / 'invoke.json'
            assert list(command) == [copy_wrapper_python, str(runner), str(invocation)]
            runner_raw, invocation_raw = runner.read_bytes(), invocation.read_bytes()
            assert hashlib.sha256(runner_raw).hexdigest() == GENERIC_INVOKE_SHA
            assert json.loads(invocation_raw) == {'cwd': str(workspace),
                'argv': requested['argv'], 'environment': requested['environment']}
            return {'operation_key': copy_reservation['operation_key'],
                'command': list(command), 'directory': str(root),
                'handle': str(root / 'native.json'), 'runner_sha256': GENERIC_INVOKE_SHA,
                'invocation_sha256': hashlib.sha256(invocation_raw).hexdigest()}

        def only_copy_prepare(command, **kwargs):
            selected = selected_copy_invocation(command, kwargs['cwd'])
            assert str(kwargs['handle_path']) == selected['handle']
            assert kwargs['policy'].to_dict() == POLICY
            assert kwargs['env'] == {'TMPDIR': selected['directory'],
                'XDG_CACHE_HOME': str(Path(selected['directory']) / 'cache'), 'PYTHONDONTWRITEBYTECODE': '1'}
            assert not native_calls['prepare'], 'a second native preparation attempted'
            native_calls['prepare'].append(selected)
            return original_prepare(command, **kwargs)

        def only_copy_start(callback):
            def start(handle, *args, **kwargs):
                body = handle.read()
                selected = selected_copy_invocation(body['command'], body['cwd'])
                assert native_calls['prepare'] == [selected] and str(handle.path) == selected['handle']
                request_raw = Path(body['paths']['request']).read_bytes()
                assert hashlib.sha256(request_raw).hexdigest() == body['request_sha256']
                assert json.loads(request_raw) == {'command': selected['command'],
                    'cwd': selected['directory'], 'file_bytes': POLICY['scratch_bytes'],
                    'ready_path': body['paths']['ready'], 'release_path': body['paths']['release'],
                    'result_path': body['paths']['result'], 'stdin_path': None,
                    'env': {'TMPDIR': selected['directory'],
                        'XDG_CACHE_HOME': str(Path(selected['directory']) / 'cache'),
                        'PYTHONDONTWRITEBYTECODE': '1'}}
                assert body['metadata']['policy'] == POLICY
                if str(handle.path) not in native_calls['start']:
                    native_calls['start'].append(str(handle.path))
                return callback(handle, *args, **kwargs)
            return start

        def forbidden_fba(*args, **kwargs):
            pytest.fail('this admission-only fixture must not prepare or execute FBA')

        monkeypatch.setattr(native_lifecycle, 'prepare_job', only_copy_prepare)
        monkeypatch.setattr(LocalPracticalOperations, '_handle', only_copy_handle)
        monkeypatch.setattr(native_lifecycle, 'start_prepared', only_copy_start(original_start))
        monkeypatch.setattr(native_lifecycle, 'resume_start', only_copy_start(original_resume))
        monkeypatch.setattr('gene_annotation_episode.native_flux_balance_local.prepare_local_flux_balance', forbidden_fba)

        class Choices:
            def __init__(self):
                self.turns, self.handoff, self.source = {}, None, None
                self.native_result = self.capture_context = self.scientific_context = None
                self.copy_context = None
                self.lookup_context = self.fba_context = self.fba_launch_context = None
                self.input_control = self.fba_control = self.fba_selection = None
                self.mapping_return = None
                self.capture_catalog = None
                self.presentation = _SessionConnection.__new__(_SessionConnection)
                self.presentation.scientific_prompt_states = {}
                self.presentations = []

            async def complete(self, episode_id, role, instructions, current, schema):
                assert not current.get('feedback'), current.get('feedback')
                model_text, model_instructions = self.presentation._presentation(
                    episode_id, role, instructions, plain(current))
                private = ('requested_job', 'execution_id', 'operation_key', 'source_payload',
                    'whole_file_bridge', 'resolved_path', 'implementation_files', 'runtime_files',
                    'solver_runtime_files', 'PYTHONHOME', 'PYTHONPATH', 'verified_cgroup', 'source_function_sha256')
                shown = canonical({'context': plain(current), 'model_text': model_text,
                    'model_instructions': model_instructions})
                capture = current.get('execution_assignment', {}).get('selector', {}).get('version') == 'local_file_source_selector_v1'
                self.presentations.append({'role': role, 'capture_selector': capture,
                    'model_text': model_text, 'model_instructions': model_instructions,
                    'model_context': deepcopy(plain(current)), 'response_schema': deepcopy(plain(schema)),
                    'observed_private_key_names': [key for key in private if key in shown],
                    'model_text_starts_with_json_object': model_text.lstrip().startswith('{')})
                G.write(evidence_path, {
                    'verification_complete': False,
                    'qualification': 'retained actual in-progress presentations; no completion claim',
                    'retained245_original_failed_model_call': failed_call,
                    'retained245_original_marker_pin': old_marker_pin if retained_case else None,
                    'presentations': self.presentations})
                if capture:
                    handle_path = Path(copy_reservation['directory']) / 'native.json'
                    handle_body = native_lifecycle.NativeJobHandle(handle_path).read()
                    private_values = (str(handle_path), handle_body['unit'], handle_body['request_sha256'],
                        copy_reservation['operation_key'], SOFTWARE_SHA, software['python']['path'], canonical(software))
                    definitions = owner.fact_sources('results')
                    _capture_privacy_view(current, model_text, model_instructions, definitions, private_values)
                    # An actual private value elsewhere, or inside an altered
                    # registered schema, must still fail this test boundary.
                    for place in ('execution_target', 'available_report_facts'):
                        changed = deepcopy(plain(current))
                        if place == 'execution_target':
                            changed[place]['operation_key'] = copy_reservation['operation_key']
                        else:
                            changed[place]['execution_protein_structure_failures']['report_schema'][
                                'description'] = copy_reservation['operation_key']
                        with pytest.raises(AssertionError):
                            _capture_privacy_view(changed, canonical(changed), model_instructions,
                                definitions, private_values)
                self.turns[episode_id] = self.turns.get(episode_id, 0) + 1
                turn = self.turns[episode_id]
                compact_fba = current.get('practical_assignment', {}).get('version') == 'flux_balance_scientific_assignment_v1'
                compact_launch = current.get('execution_assignment', {}).get('version') == 'flux_balance_scientific_launch_v1'
                mapping_lookup = current.get('scientific_process', {}).get('assignment', {}).get(
                    'context', {}).get('fixture_owner') == 'retained_mapping_lookup'
                if compact_fba or compact_launch:
                    assert SOFTWARE_SHA not in shown and canonical(software) not in shown
                    assert software['python']['path'] not in shown
                if compact_fba:
                    assert turn == 1
                    self.fba_context = owner.flux_balance_inputs.records.context(episode_id)
                    self.fba_control = read_request_binding(store, RUN_ID, episode_id)
                    self.input_control = owner.flux_balance_inputs.for_start(owner.state(self.fba_context))
                    assert plain(self.fba_context.assignment) == self.fba_selection['requests']['here']
                    assert self.input_control['receipt']['binding']['model']['file']['artifact_ref'] == store.get(self.source)['artifact_ref']
                    assert {row['reference'] for row in self.input_control['receipt']['witness_records']} == {self.source}
                    assert self.input_control['receipt']['binding']['assignment_sha256'] == digest(materialized_assignment(store, self.fba_context))
                    answer = G.action('practical.inspect')
                elif compact_launch:
                    assert turn == 1
                    self.fba_launch_context = owner.local_file_sources.records.context(episode_id)
                    answer = G.commission('launch_local', current['execution_assignment']['requests']['here'],
                        scope, G.HANDOFF_FORM, objective='Inspect the actual compact FBA receiving context only; no native preparation or start.')
                elif mapping_lookup:
                    self.lookup_context = EpisodeReturnRecords(store, RUN_ID,
                        failure_prefix='file_source_fba_workflow_').context(episode_id)
                    if turn == 1:
                        assert not store.list('reaction_record')
                        answer = G.action('public.rhea.reaction', {'accession': 'RHEA:11740'})
                    elif turn == 2:
                        answer = G.action('state.query', {'refs': mapping_refs})
                    else:
                        assert turn == 3
                        answer = G.action('source.read', {'source_ref': original_rhea_source['id'],
                            'representation': 'original', 'offset': 0, 'limit': len(body)})
                elif 'practical_assignment' in current:
                    assert turn == 1
                    self.copy_context = owner.local_file_sources.records.context(episode_id)
                    answer = G.action('practical.job.start')
                elif current.get('execution_assignment', {}).get('version') == 'execution_launch_assignment_v1':
                    assert turn == 1
                    answer = G.commission('launch_local', current['execution_assignment']['requests']['here'],
                        scope, G.HANDOFF_FORM, objective='Execute the explicitly supplied generic local copy request.')
                elif current.get('execution_assignment', {}).get('version') == 'execution_results_assignment_v1':
                    assert turn in (1, 2)
                    self.capture_context = owner.local_file_sources.records.context(episode_id)
                    actual_catalog = {row['name']: row for row in owner.catalog(self.capture_context)}
                    self.capture_catalog = deepcopy(actual_catalog)
                    assert actual_catalog['execution.results.collect']['input_schema'] == {
                        'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}
                    answer = G.action('execution.results.status' if turn == 1 else 'execution.results.collect')
                elif 'scientific_process' not in current:
                    assert turn == 1
                    answer = G.commission('scientific_process', scientific, scope, parent_form,
                        objective='Transfer the supplied edited control model through a genuine local job and typed source return.')
                elif turn == 1:
                    self.scientific_context = owner.local_file_sources.records.context(episode_id)
                    assert not set(mapping_refs).intersection(flow.receipts.known(episode_id))
                    answer = G.commission('scientific_process', lookup, scope, mapping_form,
                        objective='Inspect the retained Rhea source reaction correspondence and return its actual typed records.')
                elif turn == 2:
                    self.mapping_return = deepcopy(plain(current['child_reports'][-1]))
                    assert self.mapping_return == {'mapping_refs': mapping_refs}
                    assert set(mapping_refs) <= set(flow.receipts.known(episode_id))
                    assert {reference: store.get(reference) for reference in mapping_refs} == expected_mapping
                    answer = G.action('state.query', {'refs': mapping_refs})
                elif turn == 3:
                    answer = G.commission('launch', launch, scope, G.HANDOFF_FORM,
                        objective='Obtain the real generic copy-job handoff with its selected allocation.')
                elif turn == 4:
                    reader = PracticalReceiptInformation(store, RUN_ID)
                    self.handoff, = [ref for ref in current['child_reports'][-1]['references']
                        if reader.read(ref, scope)['receipt']['tool_name'] == 'practical.job.start']
                    target = owner.job_progress_provider.targets.read_target(self.handoff, scope)
                    self.native_result = await asyncio.to_thread(native_lifecycle.wait_job,
                        native_lifecycle.NativeJobHandle(Path(target['execution_id'])))
                    assert self.native_result.returncode == 0
                    assert output_path.read_bytes() == model_raw
                    fact = owner.fact_sources('results').get('execution_file_source_refs')
                    assert fact is not None and fact['report_schema']['items']['x-reference-namespace'] == 'source', \
                        'real custody fact registration is required; the fixture must not invent it'
                    file_form = validate_closed_schema({'type': 'object', 'properties': {
                        'files': deepcopy(fact['report_schema']),
                        'completed': {'type': 'boolean', 'x-source': 'execution_completed'}},
                        'required': ['files', 'completed'], 'additionalProperties': False})
                    answer = G.commission('results', {'version': 'execution_results_assignment_v1',
                        'handoff_ref': self.handoff, 'selector': {'version': 'local_file_source_selector_v1',
                            'files': [{'path': str(output_path), 'format': 'cobra_json'}]}}, scope, file_form,
                        objective='Retain the explicitly selected current model bytes as a reusable source.')
                elif turn == 5:
                    returned = current['child_reports'][-1]
                    assert returned['completed']
                    self.source, = returned['files']
                    self.scientific_context = owner.local_file_sources.records.context(episode_id)
                    assert self.source in flow.receipts.known(episode_id)
                    fba_request = {'version': 'flux_balance_scientific_request_v1',
                        'operation': 'perform_flux_balance_analysis', 'mode': 'steady_state_linear_fba',
                        'model_input': {'file': {'witness_ref': self.source, 'version': None,
                            'artifact_field': 'artifact_ref', 'format': 'cobra_json'},
                            'original_loader_selection': 'json_file', 'repository_identifier': None,
                            'acquisition_receipt_file': None}, 'constraints': [{
                            'reaction_id': prior['reaction_id'],
                            'lower': {'kind': 'finite', 'value': 0}, 'upper': {'kind': 'finite', 'value': 0}}],
                        'objective': {'kind': 'model_default', 'reaction_id': None},
                        'solver_options': {'feasibility_tolerance': None, 'optimality_tolerance': None,
                            'integrality_tolerance': None}}
                    fba_assignment = {'version': 'flux_balance_scientific_assignment_v1',
                        'resource_id': 'here', 'resource_kind': 'local', 'endpoint': 'usable_handoff',
                        'request': fba_request, 'progress_requirements': [{'key': 'handoff', 'credit': 1,
                            'predicate': {'kind': 'requested_job_handoff'}}], 'completion_keys': ['handoff'],
                        'constraints': {'allocation': deepcopy(POLICY)}}
                    self.fba_selection = {
                        'version': 'flux_balance_scientific_launch_v1', 'requests': {'here': fba_assignment},
                        'constraints': {'allowed_resource_ids': ['here'], 'allowed_kinds': ['local'],
                            'allocation': deepcopy(POLICY)}}
                    answer = G.commission('launch', self.fba_selection, scope, G.HANDOFF_FORM,
                        objective='Inspect admission of the explicitly received model with caller-selected zero bounds on RHEA11740_ADDITION; do not run FBA.')
                else:
                    assert turn == 6
                    assert current['child_reports'][-1]['completed'] is False
                    assert current['child_reports'][-1]['references'] == []
                    answer = G.action('source.read', {'source_ref': self.source,
                        'representation': 'original', 'offset': 0, 'limit': len(model_raw)})
                answer = G.provider_value(plain(answer), plain(schema))
                Draft202012Validator(plain(schema)).validate(answer)
                return answer

            async def release(self, episode_id):
                pass

        provider = Choices()
        failed_call = retained_native = None
        if retained_case:
            records = EpisodeReturnRecords(store, RUN_ID, failure_prefix='file_source_fba_workflow_')
            episodes = {tuple(tuple(part) for part in json.loads(row['path'])): row['episode_id']
                for row in store.db.execute('SELECT path,episode_id FROM runtime_episodes WHERE run_id=?', (RUN_ID,))}
            parent_path = (('annotation', 'root'), ('scientific_process', 'child_0'))
            provider.scientific_context = records.context(episodes[parent_path])
            provider.lookup_context, provider.mapping_return, _ = records._attempt(provider.scientific_context, 0)
            assert provider.mapping_return == {'mapping_refs': mapping_refs}
            provider.copy_context = records.context(episodes[(*parent_path,
                ('launch', 'child_2'), ('launch_local', 'child_0'))])
            provider.capture_context = records.context(episodes[(*parent_path, ('results', 'child_3'))])
            provider.handoff = plain(provider.capture_context.assignment)['handoff_ref']
            _, original_handoff_form, _ = records._attempt(provider.scientific_context, 2)
            assert original_handoff_form['references'] == [provider.handoff]
            for row in store.db.execute('SELECT episode_id,response FROM runtime_model_calls '
                    "WHERE run_id=? AND purpose='decision' AND response IS NOT NULL", (RUN_ID,)):
                assert isinstance(json.loads(row['response']), dict)
                provider.turns[row['episode_id']] = provider.turns.get(row['episode_id'], 0) + 1
            failed_call, = [dict(row) for row in store.db.execute('SELECT * FROM runtime_model_calls '
                'WHERE run_id=? AND response IS NULL', (RUN_ID,))]
            assert failed_call['episode_id'] == provider.capture_context.episode_id and failed_call['call_index'] == 0
            failed_timing = json.loads(failed_call['timing'])
            assert len(failed_timing['intervals']) == 1
            assert failed_timing['intervals'][0]['state'] == 'raised'
            assert failed_timing['intervals'][0]['exception_type'] == 'AssertionError'
            copy_key = f'{RUN_ID}:{provider.copy_context.episode_id}:0'
            assert plain(provider.copy_context.assignment)['requested_job'] == requested
            copy_root = workspace / '.episode-operations' / digest({
                'run': RUN_ID, 'episode': provider.copy_context.episode_id}) / digest(copy_key)
            copy_reservation.update({'operation_key': copy_key, 'directory': str(copy_root)})
            copy_handle = native_lifecycle.NativeJobHandle(copy_root / 'native.json')
            retained_native = deepcopy(copy_handle.read())
            selected_copy_invocation(retained_native['command'], retained_native['cwd'])
            assert retained_native['stage'] == 'released' and Path(retained_native['paths']['release']).is_file()
            assert hashlib.sha256(Path(retained_native['paths']['request']).read_bytes()).hexdigest() == retained_native['request_sha256']
            assert retained_native['metadata']['policy'] == POLICY
            assert output_path.read_bytes() == model_raw
            original_status, original_collect = native_lifecycle.status, native_lifecycle.collect

            def same_original_handle(handle):
                assert handle.path == copy_handle.path and handle.read() == retained_native
                assert Path(retained_native['paths']['release']).is_file()

            def observe_only(callback):
                def observe(handle, *args, **kwargs):
                    same_original_handle(handle)
                    return callback(handle, *args, **kwargs)
                return observe

            def released_resume(handle, **kwargs):
                same_original_handle(handle)
                # Existing resume_start observes this release before any
                # dispatch or polling. No prepared/submitting handle is allowed.
                return original_resume(handle, **kwargs)

            def forbidden_retained_work(*args, **kwargs):
                pytest.fail('retained245 continuation attempted acquisition, preparation, start or a second copy')

            monkeypatch.setattr(native_lifecycle, 'prepare_job', forbidden_retained_work)
            monkeypatch.setattr(native_lifecycle, 'start_prepared', forbidden_retained_work)
            monkeypatch.setattr(native_lifecycle, 'wait_job', forbidden_retained_work)
            monkeypatch.setattr(LocalPracticalOperations, '_handle', forbidden_retained_work)
            monkeypatch.setattr(native_lifecycle, 'resume_start', released_resume)
            monkeypatch.setattr(native_lifecycle, 'status', observe_only(original_status))
            monkeypatch.setattr(native_lifecycle, 'collect', observe_only(original_collect))
            monkeypatch.setattr(client, 'rhea_reaction', forbidden_retained_work)
            native_view = native_lifecycle.status(copy_handle)
            assert native_view['terminal'] and native_view['quiescent']
            provider.native_result = native_lifecycle.collect(copy_handle)
            assert provider.native_result.returncode == 0
            G.write(evidence_path, {'verification_complete': False,
                'qualification': 'retained245 ordinary retry; original failed row and completed records preserved',
                'original_failed_model_call': failed_call, 'original_marker_pin': old_marker_pin})
        flow = Workflow(store, tools, provider, directory / 'run', RUN_ID,
            controller_factory=_controller, project_credit=lambda *_args, **_kwargs: 0,
            annotation_child_roles=('scientific_process',), episode_record_receipts=True,
            initial_known_record_refs=[original_source, provenance_source],
            episode_binding_descriptors=(binding, *application.episode_binding_descriptors),
            role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
        owner = flow.episode_bindings.for_role('results')
        if retained_case:
            original_target = owner.job_progress_provider.targets.read_target(provider.handoff, scope)
            assert original_target['execution_id'] == str(copy_handle.path)
            assert original_target['resource_kind'] == 'local'
        definition = owner.fact_sources('results').get('execution_file_source_refs')
        assert definition is not None, \
            'real custody registration is required before starting the native verification job'
        parent_form = _parent_form(definition)

        async def run():
            root = flow.build('annotation', 'root', 'Verify genuine model-byte transfer and FBA input admission', scope)
            record = await root.run_async(flow.context)
            await root.build_result(record)
            return record

        record = asyncio.run(run())
        archive = json.loads(''.join(iter_json(record.as_record())))
        source = store.get(provider.source)
        assert store.get_artifact(source['artifact_ref']) == model_raw == input_path.read_bytes()
        assert source['provider'] == 'episode.execution_file' and source['origin'] == 'tool'
        assert source['parent_source_refs'] == [provider.handoff]
        admitted, = provider.fba_control['requests']
        assert admitted['assignment']['requested_job']['native_flux_balance']['model_input']['artifact_ref'] == source['artifact_ref']
        assert admitted['input_versions'] == [{'reference': provider.source,
            'version': None, 'content_sha256': MODEL_SHA}]
        assert admitted['selection'] == plain(provider.fba_context.assignment)
        assert admitted['selection']['request']['constraints'] == [{
            'reaction_id': 'RHEA11740_ADDITION', 'lower': {'kind': 'finite', 'value': 0},
            'upper': {'kind': 'finite', 'value': 0}}]
        assert provider.fba_control['version'] == read_request_binding(
            store, RUN_ID, provider.fba_launch_context.episode_id)['version']
        assert client.calls == ([] if retained_case else [capture['request']])
        assert provider.mapping_return == {'mapping_refs': mapping_refs}
        assert {reference: store.get(reference) for reference in mapping_refs} == expected_mapping
        assert store.get(original_rhea_source['id']) == original_rhea_source
        assert store.get_artifact(original_rhea_source['artifact_ref']) == body
        assert json.loads(store.get_artifact(original_rhea_source['request_ref'])) == metadata
        assert set(mapping_refs) <= set(flow.receipts.known(provider.scientific_context.episode_id))
        assert not set(mapping_refs).intersection(flow.receipts.known(record.episode_id))
        assert len(native_calls['prepare']) == (0 if retained_case else 1)
        assert len(set(native_calls['start'])) == (0 if retained_case else 1)
        assert provider.source in flow.receipts.known(record.episode_id)
        frozen = json.loads(flow.journal.row('runtime_forms', provider.scientific_context.episode_id)['facts'])
        returned = json.loads(flow.journal.row('runtime_forms', provider.scientific_context.episode_id)['form'])
        assert frozen['execution_file_source_refs'] == returned['files'] == [provider.source]
        assert store.count('observation') == store.count('assessment') == store.count('annotation') == 0
        read_outcomes = [json.loads(row['result']) for row in store.db.execute(
            'SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL',
            (RUN_ID, provider.scientific_context.episode_id))
            if json.loads(row['action']).get('tool') == 'source.read']
        assert len(read_outcomes) == 1 and read_outcomes[0]['status'] == 'completed'
        assert read_outcomes[0]['result']['text'].encode() == model_raw
        assert read_outcomes[0]['result']['end'] == read_outcomes[0]['result']['total_bytes'] == len(model_raw)
        assert provider.native_result.metadata['policy'] == POLICY
        assert provider.native_result.metadata['verified_cgroup']['memory_swap_max'] == 0
        assert flow.services.scientific_credit(provider.scientific_context,
            flow.record_selection(provider.scientific_context.episode_id))['credit'] == 0
        capture_facts = owner.facts(provider.capture_context, {})
        assert capture_facts['execution_file_source_refs'] == [provider.source]
        assert capture_facts['execution_result_refs'] == [] and capture_facts['execution_result_origin'] is None
        assert owner.project_credit(provider.capture_context, flow.record_selection(provider.capture_context.episode_id))['new_acquired_record_count'] == 1
        assert owner.facts(provider.fba_context, {})['execution_completed'] is False
        assert owner.completion_for_action(provider.fba_context,
            f'{RUN_ID}:{provider.fba_context.episode_id}:0') is None
        fba_action = flow.journal.row('runtime_actions', provider.fba_context.episode_id, 0)
        assert json.loads(fba_action['action']) == {'kind': 'tool', 'tool': 'practical.inspect', 'arguments': {}}
        fba_receipts = owner.state(provider.fba_context).receipts()
        assert len(fba_receipts) == 1 and fba_receipts[0]['tool_name'] == 'practical.inspect'
        assert not fba_receipts[0]['outcome'].get('facts', {}).get('requested_job')
        fba_observation, = list(store.db.execute('SELECT observation FROM runtime_observations '
            'WHERE run_id=? AND episode_id=?', (RUN_ID, provider.fba_context.episode_id)))
        fba_observation = json.loads(fba_observation['observation'])
        assert 'practical_completion' not in fba_observation['credit']
        assert 'completion_proof' not in fba_observation['step']['estimate']['diagnostics']
        fba_attempt_root = workspace / '.episode-operations' / digest({
            'run': RUN_ID, 'episode': provider.fba_context.episode_id})
        assert not fba_attempt_root.exists()
        assert not (workspace / '.fba-selected-runtime').exists()
        assert not any(workspace.rglob('fluxes.csv'))
        lookup_context, lookup_form, _ = EpisodeReturnRecords(store, RUN_ID,
            failure_prefix='file_source_fba_workflow_')._attempt(provider.scientific_context, 0)
        assert lookup_context.episode_id == provider.lookup_context.episode_id
        assert lookup_form == provider.mapping_return
        retained_history = None
        if retained_case:
            closed_after = _closed_rows(store)
            assert all(rows <= closed_after[table] for table, rows in closed_before.items())
            retried = dict(store.db.execute('SELECT * FROM runtime_model_calls WHERE run_id=? '
                'AND episode_id=? AND call_index=?', (RUN_ID, failed_call['episode_id'], failed_call['call_index'])).fetchone())
            assert {key: retried[key] for key in failed_call if key not in ('response', 'timing')} == {
                key: value for key, value in failed_call.items() if key not in ('response', 'timing')}
            assert retried['response'] is not None
            retried_timing = json.loads(retried['timing'])
            assert len(retried_timing['intervals']) == 2
            assert retried_timing['intervals'][0] == failed_timing['intervals'][0]
            assert json.dumps(failed_timing['intervals'][0], separators=(',', ':')) in retried['timing']
            assert retried_timing['intervals'][1]['state'] == 'returned'
            assert copy_handle.read() == retained_native
            assert {'size_bytes': old_marker.stat().st_size,
                'sha256': hashlib.sha256(old_marker.read_bytes()).hexdigest()} == old_marker_pin
            retained_history = {'original_failed_model_call': failed_call,
                'retried_model_call': retried, 'original_marker_pin': old_marker_pin,
                'unchanged_closed_row_counts': {table: len(rows) for table, rows in closed_before.items()},
                'unchanged_closed_rows_sha256': {table: digest(sorted(rows)) for table, rows in closed_before.items()},
                'original_copy_handle': str(copy_handle.path), 'original_copy_unit': retained_native['unit'],
                'no_new_acquisition_preparation_start_or_copy': True}
        # Removal affects only this new generic job's current output path.
        # Its actually captured source and original212 operator evidence stay intact.
        output_path.unlink()
        frozen_input = deepcopy(provider.input_control)
        frozen_request = deepcopy(provider.fba_control)
        fba_episode_id = provider.fba_context.episode_id
        frozen_counts = {table: store.db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
            for table in ('runtime_actions', 'runtime_model_calls', 'runtime_observations',
                'runtime_forms', 'runtime_report_attempts', 'runtime_record_receipts',
                'runtime_flux_balance_request_bindings')}
        verification = {'qualification':
            'scripted genuine generic copy/capture and typed source custody, explicitly received unchanged Rhea210 '
            'mapping, actual compact FBA receiving initialization/inspection and saved-binding reopen; '
            'no new edit, FBA preparation/start/solver/outputs/handoff or scientific measurement',
            'supplied_model_sha256': MODEL_SHA, 'supplied_addition_receipt_sha256': RECEIPT_SHA,
            'source': source, 'admitted_model': admitted['assignment']['requested_job']['native_flux_balance']['model_input'],
            'original_rhea_capture': {'path': str(capture_path), 'sha256': RHEA_CAPTURE_SHA},
            'original_rhea_request_metadata': metadata, 'mapping_refs': mapping_refs,
            'fba_local_episode_id': fba_episode_id, 'fba_input_control': frozen_input,
            'fba_selected_request': admitted['selection'], 'native_calls': native_calls,
            'fba_execution_completed': False, 'fba_completion_proof': None,
            'native': {'returncode': provider.native_result.returncode, 'metadata': provider.native_result.metadata},
            'capture_catalog': provider.capture_catalog,
            'presentations': provider.presentations,
            'presentation_audit_scope': 'actual existing text/schema retained; capture/FBA public wording and broader '
                'renderer compliance are unfinished and no replacement wording is required by this fixture',
            'archive': archive, 'retained245_history': retained_history,
            'saved_binding_reopen_verified': False, 'verification_complete': False}

    def forbidden_reopen(*args, **kwargs):
        pytest.fail('saved binding reopen attempted acquisition, native lifecycle or rebinding')

    for name in ('prepare_job', 'start_prepared', 'resume_start', 'wait_job', 'status', 'collect'):
        monkeypatch.setattr(native_lifecycle, name, forbidden_reopen)
    monkeypatch.setattr(client, 'rhea_reaction', forbidden_reopen)
    with Store(directory / 'state') as reopened:
        restored = ExecutionEpisodes(None, store=reopened, directory=directory / 'run', run_id=RUN_ID,
            resources=resources, initial_information={}, tool_registry=ToolRegistry(reopened, clients=client),
            handoff_unit=3, acquired_record_unit=2, log_window_bytes=128, log_roles=('stdout', 'stderr'))
        context = EpisodeReturnRecords(reopened, RUN_ID,
            failure_prefix='file_source_fba_workflow_').context(fba_episode_id)
        monkeypatch.setattr(restored.flux_balance_requests, 'preview', forbidden_reopen)
        monkeypatch.setattr(restored.flux_balance_inputs, 'validate_selected', forbidden_reopen)
        monkeypatch.setattr(restored.local_file_sources, 'execute', forbidden_reopen)
        monkeypatch.setattr(restored.job_progress_provider.targets, 'observe_target', forbidden_reopen)
        restored.initialize(context)
        assert read_request_binding(reopened, RUN_ID, fba_episode_id) == frozen_request
        assert restored.flux_balance_inputs.received(context) == frozen_input
        assert restored.flux_balance_inputs.for_start(restored.state(context)) == frozen_input
        assert restored.local_file_sources.read_source(provider.source, context.scope,
            verify_artifact=True)['file']['sha256'] == MODEL_SHA
        assert reopened.get_artifact(reopened.get(provider.source)['artifact_ref']) == model_raw
        assert {reference: reopened.get(reference) for reference in mapping_refs} == expected_mapping
        assert {table: reopened.db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
            for table in frozen_counts} == frozen_counts
        assert reopened.count('observation') == reopened.count('assessment') == reopened.count('annotation') == 0
        assert not output_path.exists() and not fba_attempt_root.exists()
    verification['saved_binding_reopen_verified'] = True
    verification['verification_complete'] = True
    G.write(evidence_path, verification)


@pytest.mark.skipif(not os.environ.get('HMMER_NATIVE_ORACLE_FILE_CAPTURE_RETAINED_AUDIT'),
    reason='requires the explicit original245/246 partial Store and retained presentations')
def test_retained_file_source_compact_fba_admission_reopens_without_native_work(tmp_path, monkeypatch):
    assert os.environ.get('HMMER529_ATTEMPT'), 'requires the bounded529 runtime'
    directory = Path(os.environ['HMMER_NATIVE_ORACLE_FILE_CAPTURE_RETAINED_CASE'])
    evidence_path = Path(os.environ['HMMER_NATIVE_ORACLE_FILE_CAPTURE_RETAINED_AUDIT'])
    assert directory.is_absolute() and evidence_path.is_absolute()
    model_path, model_raw = _selected_bytes('HMMER_NATIVE_ORACLE_FILE_CAPTURE_SUPPLIED_MODEL', MODEL_SHA, 1974)
    receipt_path, _ = _selected_bytes('HMMER_NATIVE_ORACLE_FILE_CAPTURE_ADDITION_RECEIPT', RECEIPT_SHA, 2993)
    _, software_raw = _selected_bytes('HMMER_NATIVE_ORACLE_FBA716_SOFTWARE', SOFTWARE_SHA, 3540474)
    software = validate_flux_balance_software(json.loads(software_raw))
    evidence_raw = evidence_path.read_bytes()
    evidence = json.loads(evidence_raw)
    assert evidence['verification_complete'] is False
    original_failure = evidence['retained245_original_failed_model_call']
    original_marker = directory / 'verified-file-source-workflow.json'

    def pin(path):
        raw = path.read_bytes()
        return {'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}

    assert pin(original_marker) == evidence['retained245_original_marker_pin']
    workspace = directory / 'workspace'
    producer = workspace / 'received-edited-model.json'
    producer_pin = pin(producer)
    assert producer_pin == {'sha256': MODEL_SHA, 'size_bytes': len(model_raw)}

    def case_pins():
        return {str(path.relative_to(directory)): pin(path) for path in directory.rglob('*')
            if path.is_file() and not path.is_symlink() and path.name not in (
                'state.sqlite3', 'state.sqlite3-wal', 'state.sqlite3-shm', 'state.sqlite3-journal')}

    def database_rows(store):
        tables = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {table: sorted((tuple(row) for row in store.db.execute('SELECT * FROM ' + table)), key=repr)
            for table in tables}

    def forbidden(*args, **kwargs):
        pytest.fail('retained admission audit attempted model, acquisition, capture, native work or new selection')

    class NoAcquisition:
        def __getattr__(self, name):
            forbidden(name)

    for name in ('prepare_job', 'start_job', 'start_prepared', 'resume_start', 'wait_job', 'status', 'collect'):
        monkeypatch.setattr(native_lifecycle, name, forbidden)
    monkeypatch.setattr('gene_annotation_episode.runtime.DecisionSource.call', forbidden)
    monkeypatch.setattr(Workflow, 'build', forbidden)
    monkeypatch.setattr(ToolRegistry, 'execute', forbidden)
    monkeypatch.setattr(ToolRegistry, 'execute_async', forbidden)
    monkeypatch.setattr(LocalPracticalOperations, '_handle', forbidden)
    monkeypatch.setattr('gene_annotation_episode.native_flux_balance_local.prepare_local_flux_balance', forbidden)
    monkeypatch.setattr('gene_annotation_episode.native_file_capture.capture_native_file', forbidden)
    monkeypatch.setattr('gene_annotation_episode.local_file_capture_results.capture_native_file', forbidden)
    with Store(directory / 'state') as store:
        before = database_rows(store)
        files_before = case_pins()
        records = EpisodeReturnRecords(store, RUN_ID, failure_prefix='file_source_fba_workflow_')
        episodes = {tuple(tuple(part) for part in json.loads(row['path'])): row['episode_id']
            for row in store.db.execute('SELECT episode_id,path FROM runtime_episodes WHERE run_id=?', (RUN_ID,))}
        parent_path = (('annotation', 'root'), ('scientific_process', 'child_0'))
        parent = records.context(episodes[parent_path])
        lookup, mapping_form, _ = records._attempt(parent, 0)
        capture_context, capture_form, _ = records._attempt(parent, 3)
        assert capture_form['completed'] is True
        source_ref, = capture_form['files']
        source = store.get(source_ref)
        assert source['provider'] == 'episode.execution_file' and source['origin'] == 'tool'
        assert source['artifact_ref'] == 'artifact_' + MODEL_SHA
        assert store.get_artifact(source['artifact_ref']) == model_raw
        handoff = plain(capture_context.assignment)['handoff_ref']
        assert source['parent_source_refs'] == [handoff]
        _, original_handoff, _ = records._attempt(parent, 2)
        assert original_handoff['references'] == [handoff]
        launch = records.context(episodes[(*parent_path, ('launch', 'child_4'))])
        local = records.context(episodes[(*parent_path, ('launch', 'child_4'), ('launch_local', 'child_0'))])
        local_assignment = plain(local.assignment)
        assert local_assignment == plain(launch.assignment)['requests']['here']
        assert local_assignment['request']['model_input']['file']['witness_ref'] == source_ref
        assert local_assignment['request']['constraints'] == [{'reaction_id': 'RHEA11740_ADDITION',
            'lower': {'kind': 'finite', 'value': 0}, 'upper': {'kind': 'finite', 'value': 0}}]
        assert local_assignment['endpoint'] == 'usable_handoff'
        for context in (parent, launch, local):
            assert store.db.execute('SELECT state FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                (RUN_ID, context.episode_id)).fetchone()[0] == 'active'
        actions = list(store.db.execute('SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=?',
            (RUN_ID, local.episode_id)))
        action, = actions
        assert action['decision_index'] == 0 and action['result'] is not None and action['credit'] == 0
        assert json.loads(action['action']) == {'kind': 'tool', 'tool': 'practical.inspect', 'arguments': {}}
        observation, = store.db.execute('SELECT observation FROM runtime_observations WHERE run_id=? AND episode_id=?',
            (RUN_ID, local.episode_id))
        observation = json.loads(observation[0])
        assert 'practical_completion' not in observation['credit']
        assert 'completion_proof' not in observation['step']['estimate']['diagnostics']
        assert observation['step']['stop'] is False
        assert observation['step']['estimate']['diagnostics']['initialization'] == 'cold_template_prior'
        failed_local = dict(store.db.execute('SELECT * FROM runtime_model_calls WHERE run_id=? '
            'AND episode_id=? AND call_index=1', (RUN_ID, local.episode_id)).fetchone())
        assert failed_local['response'] is None
        assert json.loads(failed_local['timing'])['intervals'][0]['state'] == 'raised'
        assert json.loads(failed_local['timing'])['intervals'][0]['exception_type'] == 'AssertionError'
        retried = dict(store.db.execute('SELECT * FROM runtime_model_calls WHERE run_id=? '
            'AND episode_id=? AND call_index=?', (RUN_ID, original_failure['episode_id'], original_failure['call_index'])).fetchone())
        assert retried['request'] == original_failure['request'] and retried['response'] is not None
        assert json.loads(retried['timing'])['intervals'][0] == json.loads(original_failure['timing'])['intervals'][0]
        assert [(span['state'], span['exception_type']) for span in json.loads(retried['timing'])['intervals']] == [
            ('raised', 'AssertionError'), ('returned', None)]
        for provider_name, path in (('supplied_actual212_edited_control', model_path),
                ('supplied_actual212_addition_receipt', receipt_path)):
            original_source, = [row for row in store.list('source') if row['provider'] == provider_name]
            assert original_source['uri'] == path.as_uri()
        resources = {'here': {'kind': 'local', 'workspace': str(workspace), 'policy': deepcopy(POLICY),
            'native_flux_balance': [{'version': 'flux_balance_local_binding_v1',
                'operation': 'perform_flux_balance_analysis', 'mode': 'steady_state_linear_fba',
                'software': software, 'model_formats': ['cobra_json']}]}}
        owner = ExecutionEpisodes(None, store=store, directory=directory / 'run', run_id=RUN_ID,
            resources=resources, initial_information={}, tool_registry=ToolRegistry(store, clients=NoAcquisition()),
            handoff_unit=3, acquired_record_unit=2, log_window_bytes=128, log_roles=('stdout', 'stderr'))
        monkeypatch.setattr(owner.flux_balance_requests, 'preview', forbidden)
        monkeypatch.setattr(owner.flux_balance_inputs, 'validate_selected', forbidden)
        monkeypatch.setattr(owner.local_file_sources, 'execute', forbidden)
        monkeypatch.setattr(owner.job_progress_provider.targets, 'observe_target', forbidden)
        original_open, original_os_open = Path.open, os.open

        def producer_path(path, dir_fd=None):
            path = Path(os.fsdecode(path))
            if not path.is_absolute():
                root = Path(os.readlink('/proc/self/fd/' + str(dir_fd))) if dir_fd is not None else Path.cwd()
                path = root / path
            return Path(os.path.abspath(path)) == producer

        def no_producer_open(path, *args, **kwargs):
            assert not producer_path(path), 'producer bytes forbidden during saved reopen'
            return original_open(path, *args, **kwargs)

        def no_producer_os_open(path, *args, dir_fd=None, **kwargs):
            assert not producer_path(path, dir_fd), 'producer bytes forbidden during saved reopen'
            return original_os_open(path, *args, dir_fd=dir_fd, **kwargs)

        with monkeypatch.context() as read_guard:
            read_guard.setattr(Path, 'open', no_producer_open)
            read_guard.setattr(os, 'open', no_producer_os_open)
            with pytest.raises(AssertionError, match='producer bytes forbidden'):
                producer.open('rb')
            with pytest.raises(AssertionError, match='producer bytes forbidden'):
                os.open(producer, os.O_RDONLY)
            descriptor = original_os_open(workspace, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with pytest.raises(AssertionError, match='producer bytes forbidden'):
                    os.open(producer.name, os.O_RDONLY, dir_fd=descriptor)
            finally:
                os.close(descriptor)
            original_control = read_request_binding(store, RUN_ID, local.episode_id)
            launch_control = read_request_binding(store, RUN_ID, launch.episode_id)
            saved_input = owner.flux_balance_inputs.received(local)
            owner.initialize(launch)
            owner.initialize(local)
            assert read_request_binding(store, RUN_ID, local.episode_id) == original_control
            assert read_request_binding(store, RUN_ID, launch.episode_id) == launch_control
            assert owner.flux_balance_inputs.received(local) == saved_input
            assert owner.flux_balance_inputs.for_start(owner.state(local)) == saved_input
            assert saved_input['receipt']['binding']['model']['file']['artifact_ref'] == source['artifact_ref']
            assert {row['reference'] for row in saved_input['receipt']['witness_records']} == {source_ref}
            assert records._received_before(parent.episode_id, source_ref, 4)
            assert records._received_before(local.episode_id, source_ref, 0)
            assert owner.local_file_sources.read_source(source_ref, local.scope,
                verify_artifact=True)['file']['sha256'] == MODEL_SHA
            assert owner.facts(local, {})['execution_completed'] is False
            assert owner.completion_for_action(local, f'{RUN_ID}:{local.episode_id}:0') is None
        assert pin(producer) == producer_pin
        assert database_rows(store) == before
        assert case_pins() == files_before
        assert evidence_path.read_bytes() == evidence_raw
        assert not (workspace / '.fba-selected-runtime').exists()
        assert not (workspace / '.episode-operations' / digest({'run': RUN_ID, 'episode': local.episode_id})).exists()
        assert not any(workspace.rglob('fluxes.csv'))
        verification = {'qualification': 'retained245/246 partial input admission and saved-control reopen only; '
            'one original generic copy and typed capture, no new lookup/copy/model call/inspection/FBA execution, '
            'no practical endpoint or active parent closure; actual JSON/schema presentation remains unfinished',
            'source_ref': source_ref, 'model_sha256': MODEL_SHA, 'mapping_form': mapping_form,
            'lookup_episode_id': lookup.episode_id, 'capture_episode_id': capture_context.episode_id,
            'local_episode_id': local.episode_id, 'observed_estimate': observation['step']['estimate'],
            'original245_failed_interval_preserved': True, 'failed246_call_preserved': True,
            'all_original_rows_unchanged': True, 'all_original_files_unchanged': True,
            'row_counts': {name: len(rows) for name, rows in before.items()},
            'row_sha256': {name: digest(rows) for name, rows in before.items()},
            'file_pins': files_before, 'producer_read_forbidden': True,
            'selected_control_sha256': digest(original_control), 'saved_input_control_sha256': digest(saved_input),
            'fba_execution_completed': False, 'completion_proof': None, 'verification_complete': True}
    G.write(Path(os.environ['HMMER529_ATTEMPT']) / 'retained-file-source-input-reopen.json', verification)
