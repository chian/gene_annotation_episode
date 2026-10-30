"""Three selected phylogeny modes through the real composed Workflow.

Only decisions, scientific/root continuation and native service transport are
controlled. The four-member native operands are synthetic hand examples. No
remote phylogeny, configured model, local scientific program or HPC job runs.
Custody, selected effects, publication, parsers, calculations, typed admission,
credit and practical endpoint estimation are the production implementations.
"""
import asyncio
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

import pytest
from method_loop.archive import iter_json
from method_loop.identities import EpisodeRef

from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.bvbrc_gene_tree_grader import calculate_gene_tree
from gene_annotation_episode.bvbrc_codon_tree_grader import calculate_codon_tree
from gene_annotation_episode.bvbrc_phylogeny_returns import phylogeny_fact_sources
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
from test_api_bvbrc_appservice import PREFIX
from test_bvbrc_appservice_inputs import NativeClient
from test_bvbrc_phylogeny_host_integration import MODES, configured, supplied
from test_bvbrc_phylogeny_bundle_resolution import fixture, slot
from test_bvbrc_phylogeny_returns import forbid_acquisition_or_scientific_work
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import form
from test_practical_runtime import selected
from test_public_search import Client


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'verification/tool_graders_bvbrc_phylogeny_workflow_2026-10-25'
EXPECTED = {'tips': 4, 'cells': 16, 'gap_fraction': .125}
ADAPTER_PIN = 'd2cad59d6b38933bdb7e9d2a3412612b87d70c16567c128d68632fff821e4093'
RETURNS_PIN = 'eeb008272fcc5a88601a01c1e146d9cfcb8c739f41bdd1db33faeb5a7a7acb1b'
INFORMATION_PIN = '83921b25268ad0f8b9028c8695d32b4999603b45cfeafe5a8d679dcb62eda96a'


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def content(store, source_ref):
    source = store.get(source_ref)
    raw = store.get_artifact(source['artifact_ref'])
    return {'source_ref': source_ref, 'artifact_field': 'artifact_ref',
        'artifact_ref': source['artifact_ref'], 'sha256': hashlib.sha256(raw).hexdigest(),
        'byte_count': len(raw)}


def source_provenance(original=None):
    package = ROOT / 'gene_annotation_episode'
    if original is None:
        paths = {p for directory in (package, ROOT / 'method_loop', PUBLICATION)
            for p in directory.rglob('*') if p.is_file() and p.suffix in {'.py', '.json', '.md'}}
        paths.update(ROOT / 'tests' / name for name in (
            'test_bvbrc_phylogeny_composed_workflow.py', 'test_bvbrc_phylogeny_host_integration.py',
            'test_bvbrc_phylogeny_bundle_resolution.py', 'test_bvbrc_phylogeny_returns.py',
            'test_bvbrc_appservice_inputs.py', 'test_api_bvbrc_appservice.py',
            'test_execution_episodes_family.py', 'test_execution_wiring.py',
            'test_practical_runtime.py', 'test_public_search.py', 'bvbrc_minhash_episode_fixture.py'))
    else:
        paths = {Path(path) for path in original['files']}
    files = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}
    assert files[str(package / 'bvbrc_phylogeny_returns.py')] == RETURNS_PIN
    assert files[str(package / 'bvbrc_phylogeny_tool_info.py')] == INFORMATION_PIN
    return {'python_executable': sys.executable, 'python_version': sys.version,
        'method_loop_package': str(ROOT / 'method_loop'), 'source_package': str(package),
        'adapter_implementation_sha256': ADAPTER_PIN, 'files': files}


def case_inputs(store, mode):
    """Supply original operands and explicit synthetic correspondence as data.

    The transport below represents remote Workspace paths, not local execution.
    The supplied records state their synthetic identity and do not assert an
    observed deployed producer, engine, bootstrap experiment or genome family.
    """
    case = supplied(mode)
    assert case.module.implementation_sha256() == ADAPTER_PIN
    provider = 'codon_tree' if mode == MODES[2] else 'gene_tree'
    scientific = deepcopy(fixture(provider)[2][0]['value'])
    scientific['observed_run']['settings'] = []
    final_rows = ['A-CX', 'ATCX', 'ATGX', 'AT-X']
    original = {'fixture': 'synthetic supplied operands and explicit row/locus correspondence; no phylogeny ran',
        'mode': mode, 'final_rows': [{'label': label, 'sequence': seq} for label, seq in zip('ABCD', final_rows)],
        'loci': [], 'requested_genomes': case.request['parameters'].get('genome_ids', [])}
    if provider == 'gene_tree':
        loci = [('locusA', 0, 4)] if mode == 'gene_tree' else [('locusA', 0, 2), ('locusB', 2, 4)]
        for index, (locus_id, start, stop) in enumerate(loci):
            rows = [seq[start:stop] for seq in final_rows]
            original['loci'].append({'locus_id': locus_id,
                'workspace_path': case.request['parameters']['sequences'][index]['filename'],
                'final_columns_0based_half_open': [start, stop],
                'aligned_fasta': ''.join('>' + label + '\n' + seq + '\n' for label, seq in zip('ABCD', rows)),
                'members': [{'member_id': label, 'sequence': seq.replace('-', ''),
                    'length': len(seq.replace('-', '')), 'molecule': 'protein',
                    'sequence_sha256': hashlib.sha256(seq.replace('-', '').encode()).hexdigest()}
                    for label, seq in zip('ABCD', rows)]})
    original_material = store.register_material(data=canonical(original).encode(),
        name='SYNTHETIC-' + mode + '-original-operands.json', format='text', use='evidence')
    original_content = content(store, original_material['source_ref'])
    original_evidence = {'content': original_content, 'pointer': ''}
    plan = case.selector['adapter']['parameters']['analyses'][0]
    if provider == 'gene_tree':
        plan['analysis']['locus_ids'] = [row['locus_id'] for row in original['loci']]
        for index, locus in enumerate(original['loci']):
            binding = case.request['input_bindings'][index]
            binding['binding_id'] = locus['locus_id']
            binding['members'] = [{key: member[key] for key in ('member_id', 'length', 'molecule', 'sequence_sha256')}
                | {'member_pointer': f'/loci/{index}/members/{j}',
                   'evidence': {'content': original_content, 'pointer': f'/loci/{index}/members/{j}'}}
                for j, member in enumerate(locus['members'])]
            members = [{'input_binding_id': binding['binding_id'], 'member_id': row['member_id']}
                for row in binding['members']]
            ev = {'content': original_content, 'pointer': f'/loci/{index}'}
            scientific['assembly']['locus_bindings'].append({'locus_id': locus['locus_id'],
                'input_members': members, 'completeness': 'complete', 'evidence': [ev]})
            for row_index, member in enumerate(members):
                scientific['joins']['input_rows'].append({'alignment_id': slot('alignment'),
                    'row_index': row_index, **member, 'locus_id': locus['locus_id'],
                    'transformation_id': 'supplied-concatenation' if mode == MODES[1] else None, 'evidence': [ev]})
        if mode == MODES[1]:
            scientific['joins']['transformations'].append({'transformation_id': 'supplied-concatenation',
                'kind': 'concatenate', 'input_members': [member for locus in scientific['assembly']['locus_bindings']
                    for member in locus['input_members']],
                'output_rows': [{'alignment_id': slot('alignment'), 'row_index': i} for i in range(4)],
                'before_header': None, 'after_label': None, 'segment_id': None,
                'locus_order': ['locusA', 'locusB'], 'removed_alignment_columns_0based': None,
                'before_sequence_sha256': None, 'after_sequence_sha256': None, 'evidence': [original_evidence]})
        scientific['joins']['tip_rows'] = [{'tree_id': slot('tree', tree=True), 'node_index': node,
            'alignment_id': slot('alignment'), 'row_index': i, 'evidence': [original_evidence]}
            for i, node in enumerate((2, 3, 5, 6))]
    scientific_material = store.register_material(data=canonical(scientific).encode(),
        name='SYNTHETIC-' + mode + '-scientific-inputs.json', format='text', use='evidence')
    scientific_evidence = {'content': content(store, scientific_material['source_ref']), 'pointer': ''}
    plan['scientific_inputs'] = scientific_evidence
    fields = {name: node['x-phylogeny-fact'] for name, node in case.selector['requested_schema']['properties'].items()
        if name != 'edges'}
    case.selector['requested_schema'] = case.module.requested_form_schema(fields)
    case.selector['supplied_metadata'] = [scientific_evidence, original_evidence]
    case.original, case.scientific = original, scientific
    case.materials = [original_material, scientific_material]
    case.original_content, case.scientific_evidence = original_content, scientific_evidence
    return case


def child(role, assignment, scope, schema):
    return {'selection': {'kind': 'episode_child', 'role': role,
        'goal': 'Measure the tip count, alignment cell count and gap fraction for the supplied phylogeny operands using the selected BV-BRC mode',
        'scope': scope, 'purpose': 'Return only the requested recorded measurements and missing requirements; retain original member and locus associations and unknown native provenance',
        'assignment': deepcopy(assignment), 'schema_json': json.dumps(schema),
        'initial_report_json': '{}'}, 'report_update': {}}


def run_identity(mode):
    # Exercise chronology against the opposite lexical ordering of hashed
    # directories. This changes fixture identity, never production selection.
    for index in range(100):
        run_id = f'phylogeny-composed-{mode}-{index}'
        path = (('annotation', 'root'), ('scientific_process', 'child_0'), ('results', 'child_3'))
        episode_id = EpisodeRef(run_id, path).episode_id
        if digest(f'{run_id}:{episode_id}:3') < digest(f'{run_id}:{episode_id}:1'):
            return run_id
    raise AssertionError('fixture could not construct opposite hash order')


@pytest.fixture(scope='module', params=MODES, ids=MODES)
def phylogeny_run(request):
    mode = request.param
    (EVIDENCE / 'runs').mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=mode + '-', dir=EVIDENCE / 'runs'))
    provenance = {'mode': mode, 'scope': 'synthetic native operands through actual composed Workflow',
        'live_api': False, 'configured_model': False, 'native_scientific_execution': False, 'hpc': False,
        'fixture_overrides': ['decision provider', 'root/scientific continuation', 'NativeClient transport'],
        'production_overrides': []}
    write(directory / 'PROVENANCE.json', {**provenance, 'status': 'started'})
    before = source_provenance()
    write(directory / 'SOURCE_PROVENANCE.json', before)
    with pytest.MonkeyPatch.context() as patch, Store(directory / 'state') as store:
        target, = store.create_problem(raw_sequence='ACX', molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}
        case = case_inputs(store, mode)
        original_case = deepcopy({'request': case.request, 'selector': case.selector})
        write(directory / 'selected-inputs.json', {**original_case, 'original': case.original, 'scientific': case.scientific})
        for index, item in enumerate(case.files):
            (directory / f'native-{index}.txt').write_bytes(item['raw'])
        app = case.request['required_application_id']
        paths = {row['path']: row['target_id'] for row in case.request['workspace_targets']}
        native_bytes = {row['object']['target_id']: row['raw'] for row in case.files}

        class Responses(NativeClient):
            def rpc(self, command):
                if command['method'] == 'AppService.start_app2':
                    assert command['params'] == [app, case.request['parameters'], case.request['start_parameters']]
                    self.value = {'id': '123', 'application_id': app, 'state_code': 'Q'}
                else:
                    assert command['method'] == 'Workspace.get_download_url'
                    path, = command['params'][0]['objects']
                    self.value = ['https://fixture.invalid/' + paths[path]]
                return super().rpc(command)

            def download(self, url, *, byte_range=None):
                assert byte_range is None and url.startswith('https://fixture.invalid/')
                self.body = native_bytes[url.removeprefix('https://fixture.invalid/')]
                return super().download(url, byte_range=byte_range)

        native = Responses()
        constructor = BVBRCAppServiceService.__init__

        def transport(self, *args, **kwargs):
            constructor(self, *args, **kwargs)
            self.client = native

        def forbidden(*args, **kwargs):
            raise AssertionError('Synthetic phylogeny Workflow attempted live transport or subprocess execution')

        patch.setattr(BVBRCAppServiceService, '__init__', transport)
        for name in ('socket.create_connection', 'socket.socket.connect', 'socket.socket.connect_ex',
                'urllib.request.OpenerDirector.open', 'subprocess.run', 'subprocess.Popen'):
            patch.setattr(name, forbidden)

        def controllers(path, initial):
            def fixture_estimate(history, parameters, contexts):
                limit = {'annotation': 1, 'scientific_process': 4}[path[-1][0]]
                return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= limit else 1),
                    parameters, {'fixture': 'root_and_scientific_continuation_only'})
            return YieldController(str(path), initial, 0, YieldParameters(100, 50),
                estimate_with_context=fixture_estimate if path[-1][0] in {'annotation', 'scientific_process'} else None)

        assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'selected-api',
            'service': 'bvbrc_appservice', 'request': case.request, 'endpoint': 'usable_handoff', 'constraints': {}}
        launch = launch_assignment({'selected-api': assignment})
        handoff_form, result_form = form('execution_handoff_refs'), form('execution_result_refs')
        sources = phylogeny_fact_sources()
        measurements = sources['bvbrc_phylogeny_measurements']['report_schema']
        result_form['properties'].update(numbers=measurements,
            missing=sources['bvbrc_phylogeny_requirements']['report_schema'])
        result_form['required'].extend(['numbers', 'missing'])
        parent_form = {'type': 'object', 'additionalProperties': False,
            'properties': {'numbers': deepcopy(measurements)}, 'required': ['numbers']}
        config = configured(case.module)
        factory = ExecutionServiceFactory({'selected-api': config}, {}, 2, 3, .5)
        tools = ToolRegistry(store, clients=Client())
        run_id, run_directory = run_identity(mode), directory / 'run'
        application = factory(store, run_id=run_id, directory=run_directory,
            tool_registry=tools, tool_catalog=tools.catalog())
        descriptor = prepare_scientific_binding(run_directory=run_directory, source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=('scientific_process', 'launch', 'results'),
            resource_catalogs=application.resource_tool_catalogs)
        library = ScientificProcessLibrary(run_directory / 'scientific-process-library')
        tool_name = 'bvbrc.' + ('codon_tree' if mode == MODES[2] else 'gene_tree') + '.' + mode
        selected_tools = [{'name': tool_name, 'resources': 'api'}, {'name': 'material.parse', 'resources': 'local'}]

        class Choices:
            def __init__(self):
                self.counts, self.scientific_calls = {}, []
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
                    return child('launch_api', assignment, scope, handoff_form)
                if version == 'api_service_assignment_v1':
                    assert execution == assignment
                    if count == 1:
                        return selected(PREFIX + 'prepare', {'definition': {'kind': 'packaged', 'required_application_id': app}})
                    assert count == 2
                    return selected(PREFIX + 'submit', {'preparation_receipt_ref':
                        self.last(episode_id)['support_receipt_ref'], 'input_evidence_refs': []})
                if version == 'execution_results_assignment_v1':
                    assert execution['selector'] == case.selector
                    assert 1 <= count <= 4
                    if count == 3:
                        self.partial_ref = self.last(episode_id)['source_ref']
                        self.partial_snapshot = api.read_result(self.partial_ref, scope)
                        write(directory / 'partial-publication.json', self.partial_snapshot)
                        assert self.partial_snapshot['publication']['completion_proof'] is None
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
                    if count <= 2:
                        return selected('material.parse', {'material_ref': case.materials[count - 1]['id'], 'format': 'text'})
                    if count == 3:
                        return child('launch', launch, scope, handoff_form)
                    assert count == 4
                    returned = current['child_reports'][-1]
                    assert returned['completed'] and returned['yield']['expected_next_gain'] == NumericBand.exact(0).as_record()
                    handoff, = returned['references']
                    return child('results', {'version': 'execution_results_assignment_v1',
                        'handoff_ref': handoff, 'selector': case.selector}, scope, result_form)
                assert count == 1 and episode_id == episode.source.episode_id
                available = workflow.scientific_process_binding.tool_library.parent_tool_info(
                    workflow.services.tool_information_catalog(scope))
                assert all(any((row['name'], row['resources']) == (tool['name'], tool['resources'])
                    for row in available) for tool in selected_tools)
                scientific_assignment = {'selection': {'version': 'scientific_process_selection_v3',
                    'evidence_axis': library.reference('A101'), 'thought_pattern': library.reference('P01'),
                    'child_tool_info': deepcopy(selected_tools)}, 'evidence_refs': [target],
                    'constraints': {'preserve_original_members_and_loci': True},
                    'context': {'supplied_sequence': 'ACX', 'molecule': 'protein', 'complete': True,
                        'label_is_public_identity': False, 'supplied_material_refs': [m['id'] for m in case.materials]}}
                return child('scientific_process', scientific_assignment, scope, parent_form)

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
            'Measure phylogenetic membership and alignment gaps for the supplied sequence and selected members', scope)

        async def execute():
            record = await episode.run_async(workflow.context)
            await episode.build_result(record)
            return record

        record = asyncio.run(execute())
        archive = json.loads(''.join(iter_json(record.as_record())))
        science = archive['units'][0]['child']
        launch_record, results = science['units'][2]['child'], science['units'][3]['child']
        api_record = launch_record['units'][0]['child']
        returned = json.loads(workflow.journal.row('runtime_forms', results['episode_id'])['form'])
        forwarded = json.loads(workflow.journal.row('runtime_forms', science['episode_id'])['form'])
        final_ref, = {row['source_ref'] for row in returned['numbers']}
        body = api.read_result(final_ref, scope)
        saved = body['publication']['adapter_result']
        sheet = json.loads(store.get_artifact(saved['sheet_content']['artifact_ref']))
        components = json.loads(store.get_artifact(saved['components_content']['artifact_ref']))
        for name, value in (('archive', archive), ('results-return', returned), ('scientific-return', forwarded),
                ('publication', body), ('native-calls', native.calls), ('sheet', sheet), ('components', components)):
            write(directory / (name + '.json'), value)
        for index, (current, instructions) in enumerate(choices.scientific_calls):
            (directory / f'scientific-presentation-{index}.txt').write_text(render_scientific_process_prompt(current, instructions))
        write(directory / 'PROVENANCE.json', {**provenance, 'status': 'workflow_closed',
            'returned_measurements': {row['field']: row['value'] for row in returned['numbers']},
            'expected_measurements': EXPECTED, 'own_actions': {r['scope_level']: r['units_consumed']
                for r in (archive, science, launch_record, api_record, results)}})
        after = source_provenance(before)
        write(directory / 'SOURCE_PROVENANCE_AFTER.json', after)
        assert before == after
        assert {'request': case.request, 'selector': case.selector} == original_case
        yield SimpleNamespace(mode=mode, directory=directory, run_directory=run_directory, store=store,
            workflow=workflow, api=api, native=native, choices=choices, episode=episode, archive=archive,
            science=science, launch=launch_record, api_record=api_record, results=results,
            returned=returned, forwarded=forwarded, body=body, sheet=sheet, components=components,
            final_ref=final_ref, scope=scope, case=case, library=library, selected_tools=selected_tools,
            tool_name=tool_name, config=config, result_form=result_form, parent_form=parent_form)


def test_three_slot_selection_preserves_instruction_and_execution_ownership(phylogeny_run):
    r = phylogeny_run
    context = r.api.appservice.custody.context(r.science['episode_id'])
    binding = r.workflow.scientific_process_binding
    binding.validate_context(context)
    information = binding.tool_library.resolve_tool_info(r.selected_tools, r.workflow.services.tool_information_catalog(r.scope))
    assert plain(context.assignment)['selection'] == {'version': 'scientific_process_selection_v3',
        'evidence_axis': r.library.reference('A101'), 'thought_pattern': r.library.reference('P01'),
        'child_tool_info': information}
    contract = next(row for row in binding.tool_library.resolve_invocations(r.selected_tools,
        r.workflow.services.tool_information_catalog(r.scope)) if row['name'] == r.tool_name)
    assert contract['invocation_route'] == {'kind': 'commission', 'routes': [
        {'entry_role': 'launch', 'resource_id': 'selected-api', 'resource_role': 'launch_api'},
        {'entry_role': 'results', 'resource_id': 'selected-api', 'resource_role': 'results'}]}
    direct = {row['name'] for row in binding.catalog(context)}
    assert 'material.parse' in direct and r.tool_name not in direct
    assert not any(name.startswith(PREFIX) for name in direct)
    assert r.workflow.catalog(r.scope, source=r.episode.source) == []
    for index, (current, _) in enumerate(r.choices.scientific_calls):
        task, steering = (r.directory / f'scientific-presentation-{index}.txt').read_text().split('\n\nSTEERING', 1)
        assert task.startswith('TASK\n') and contract['instructions'] in task
        assert contract['instructions'] not in steering
        assert current['scientific_process']['evidence_axis']['investigation_instructions'] in task
        assert current['scientific_process']['child_tool_info'] == information
    for material in r.case.materials:
        assert r.api.appservice.custody.possession(context, material['source_ref']) == 'own_completed_action'
    owner = r.api.appservice.custody.original_job_owner(r.api.appservice.custody.context(r.api_record['episode_id']))
    assert owner['launch_episode_id'] == r.launch['episode_id']
    assert owner['parent_commission_operation_key'] == f'{r.workflow.run_id}:{context.episode_id}:2'
    assert r.body['bundle']['original_task']['submitted_parameters'] == r.case.request['parameters']
    assert r.body['bundle']['input_bindings'] == r.case.request['input_bindings']
    if r.mode == MODES[1]:
        assert r.case.request['parameters']['genome_selection']['concat_segments'] is True
        sheet = r.sheet['analyses'][0]['sheet']
        assert [row['locus_id'] for row in sheet['loci']] == ['locusA', 'locusB']
        assert [len(row['input_members']) for row in sheet['loci']] == [4, 4]
        assert len(sheet['joins']['input_rows']) == 8
        assert sheet['joins']['transformations'][0]['locus_order'] == ['locusA', 'locusB']
        assert [row['final_columns_0based_half_open'] for row in r.case.original['loci']] == [[0, 2], [2, 4]]


def test_native_numbers_and_only_requested_facts_reach_both_parents(phylogeny_run):
    r = phylogeny_run
    assert {row['field']: row['value'] for row in r.returned['numbers']} == EXPECTED
    assert r.returned['completed'] is True
    assert r.forwarded == {'numbers': r.returned['numbers']}
    assert r.returned['missing'] == [{'source_ref': r.final_ref, 'field': 'missing', 'requirements': []}]
    assert r.body['publication']['adapter_result']['facts'] == {**EXPECTED, 'missing': []}
    assert r.body['publication_inputs']['selector'] == r.case.selector
    assert r.body['assignment']['selector']['requested_schema'] == r.case.selector['requested_schema']
    assert r.body['publication_inputs']['adapter_implementation_sha256'] == ADAPTER_PIN
    for child_record, parent_record, expected in ((r.results, r.science, r.returned), (r.science, r.archive, r.forwarded)):
        attempt = r.store.db.execute('SELECT parent_episode_id,form,failure FROM runtime_report_attempts '
            'WHERE run_id=? AND child_episode_id=?', (r.workflow.run_id, child_record['episode_id'])).fetchone()
        assert attempt['parent_episode_id'] == parent_record['episode_id']
        assert attempt['failure'] is None and json.loads(attempt['form']) == expected
        context = r.api.appservice.custody.context(parent_record['episode_id'])
        facts = {row['fact_source']: row['facts'] for row in r.api.phylogeny_returns.received_context(context)}
        assert facts['bvbrc_phylogeny_measurements'] == expected['numbers']
        assert 'bvbrc_phylogeny_branches' not in facts
        if parent_record is r.archive:
            assert set(facts) == {'bvbrc_phylogeny_measurements'}
        assert r.api.appservice.custody.possession(context, r.final_ref) == 'admitted_return'
    artifacts = {row['role']: row for row in r.body['bundle']['artifacts']}
    for original in r.case.files:
        actual = artifacts[original['role']]
        assert r.store.get_artifact(actual['raw_artifact_ref']) == original['raw']
        assert actual['sha256'] == hashlib.sha256(original['raw']).hexdigest()
        assert actual['byte_count'] == len(original['raw'])
        assert actual['transfer']['body_complete'] and actual['transfer']['object_complete'] == 'yes'
        assert actual['task_association']['kind'] == 'unverified_original_path'
        assert actual['task_association']['byte_version_status'] != 'producer_bytes_bound'
    sheet = r.sheet['analyses'][0]['sheet']
    assert sheet['mode'] == r.mode
    alignment, = sheet['documents']['store']['alignments']
    assert [row['sequence'] for row in alignment['rows']] == ['A-CX', 'ATCX', 'ATGX', 'AT-X']
    tree, = sheet['documents']['store']['tree_documents'][0]['trees']
    assert tree['nodes'][2]['branch_length'] == 0 and tree['nodes'][5]['branch_length'] == -.1
    components = r.components['analyses'][0]['components']
    matrix, = components['alignments']
    assert matrix['cell_count']['value'] == matrix['cell_count']['denominator'] == 16
    assert matrix['gap_fraction']['value'] == 2 / 16
    assert matrix['gap_fraction']['numerator'] == 2 and matrix['gap_fraction']['denominator'] == 16


def test_one_observation_per_action_and_immediate_practical_endpoint(phylogeny_run):
    r = phylogeny_run
    expected = [(r.archive, ['episode_child:scientific_process']),
        (r.science, ['material.parse', 'material.parse', 'episode_child:launch', 'episode_child:results']),
        (r.launch, ['episode_child:launch_api']), (r.api_record, [PREFIX + 'prepare', PREFIX + 'submit']),
        (r.results, [PREFIX + name for name in ('download_capability', 'download', 'download_capability', 'download')])]
    for closed, names in expected:
        assert closed['units_consumed'] == len(names) == r.choices.counts[closed['episode_id']]
        for table in ('runtime_actions', 'runtime_observations', 'runtime_model_calls'):
            assert r.store.db.execute('SELECT count(*) FROM ' + table + ' WHERE run_id=? AND episode_id=?',
                (r.workflow.run_id, closed['episode_id'])).fetchone()[0] == len(names)
        actions = [json.loads(row[0]) for row in r.store.db.execute('SELECT action FROM runtime_actions '
            'WHERE run_id=? AND episode_id=? ORDER BY decision_index', (r.workflow.run_id, closed['episode_id']))]
        assert [a['tool'] if a['kind'] == 'tool' else a['kind'] + ':' + a['role'] for a in actions] == names
    for closed in (r.launch, r.api_record, r.results):
        assert closed['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert closed['units'][-1]['controller_step']['marginal_credit'] > 0
        row = r.store.db.execute('SELECT data FROM runtime_estimation_contexts WHERE run_id=? AND episode_id=? '
            'ORDER BY decision_index DESC LIMIT 1', (r.workflow.run_id, closed['episode_id'])).fetchone()
        proof = json.loads(row[0])['practical_completion']
        assert proof['action_index'] == closed['units_consumed'] - 1
        assert proof['unit_ref']['unit_index'] == closed['units_consumed'] - 1
    for closed in (r.archive, r.science):
        assert [u['controller_step']['marginal_credit'] for u in closed['units']] == [0] * closed['units_consumed']
    assert r.store.count('annotation') == r.store.count('observation') == 0
    assert r.store.db.execute('SELECT count(*) FROM runtime_observations WHERE run_id=?', (r.workflow.run_id,)).fetchone()[0] == 12
    decisions = r.store.db.execute('SELECT a.action,m.response,m.purpose FROM runtime_actions a '
        'JOIN runtime_model_calls m ON m.run_id=a.run_id AND m.episode_id=a.episode_id '
        'AND m.call_index=a.decision_index WHERE a.run_id=?', (r.workflow.run_id,)).fetchall()
    assert len(decisions) == 12
    assert all(row['purpose'] == 'decision' and json.loads(row['action']) == json.loads(row['response'])['selection'] for row in decisions)
    assert [call[0] for call in r.native.calls] == ['rpc', 'rpc', 'download', 'rpc', 'download']


def test_partial_to_complete_uses_original_order_and_saved_recalculation_replay(phylogeny_run, monkeypatch):
    r = phylogeny_run
    early = r.api.read_result(r.choices.partial_ref, r.scope)
    assert early == r.choices.partial_snapshot
    assert early['status'] == 'partial' and early['publication']['completion_proof'] is None
    assert early['publication']['adapter_result']['facts']['tips'] is None
    assert early['publication']['adapter_result']['facts']['cells'] == 16
    assert early['publication']['adapter_result']['facts']['gap_fraction'] == .125
    assert early['publication']['adapter_result']['missing_requirements']
    assert r.body['status'] == 'completed' and r.body['publication']['completion_proof'] is not None
    assert r.final_ref != r.choices.partial_ref
    final_key, partial_key = (body['publication']['origin']['operation_key'] for body in (r.body, early))
    assert int(final_key.rsplit(':', 1)[1]) > int(partial_key.rsplit(':', 1)[1])
    assert digest(final_key) < digest(partial_key)
    assert all(row['source_ref'] == r.final_ref for row in r.forwarded['numbers'])
    context = r.api.appservice.custody.context(r.results['episode_id'])
    assert r.api.phylogeny_returns.facts(context, r.result_form)['bvbrc_phylogeny_measurements'] == r.returned['numbers']
    tables = ('runtime_actions', 'runtime_model_calls', 'runtime_observations', 'runtime_report_attempts', 'runtime_record_receipts')
    counts = {table: r.store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] for table in tables}
    calls, sheet = deepcopy(r.native.calls), deepcopy(r.sheet)

    def forbidden(*args, **kwargs):
        raise AssertionError('Saved-sheet calculation attempted acquisition or parsing')

    for name in ('rpc', 'task_info', 'download'):
        monkeypatch.setattr(r.native, name, forbidden)
    for module_name, names in {
        'phylogeny_formats': ['parse_newick', 'parse_aligned_fasta', 'parse_relaxed_phylip', 'parse_phyloxml', 'parse_raxml_partitions'],
        'bvbrc_phylogeny_bundle_resolution': ['parse_reader', 'resolve_bundle'],
        'bvbrc_gene_tree_inputs': ['extract_gene_tree_sheet'], 'bvbrc_codon_tree_inputs': ['extract_codon_tree_sheet'],
    }.items():
        module = importlib.import_module('gene_annotation_episode.' + module_name)
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    calculator = calculate_codon_tree if r.mode == MODES[2] else calculate_gene_tree
    provider_sheet = sheet['analyses'][0]['sheet']
    saved_components = r.components['analyses'][0]['components']
    recalculated = calculator(provider_sheet, deepcopy(saved_components['parameters']))
    assert recalculated == saved_components and sheet == r.sheet
    changed_parameters = deepcopy(saved_components['parameters'])
    changed_parameters['tree_requests'][0]['pairs'] = [[2, 5]]
    changed = calculator(provider_sheet, changed_parameters)
    assert changed['parameters']['tree_requests'][0]['pairs'] == [[2, 5]]
    assert changed['trees'][0]['distances'] != saved_components['trees'][0]['distances']
    assert sheet == r.sheet
    write(r.directory / 'saved-sheet-recalculation.json', recalculated)
    write(r.directory / 'saved-sheet-changed-pair.json', changed)

    # This later phase also forbids calculators: reads/admissions/replay copy
    # only saved facts and authenticate the saved sheet as identity evidence.
    forbid_acquisition_or_scientific_work(monkeypatch)
    index = int(final_key.rsplit(':', 1)[1])
    action = dict(r.store.db.execute('SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
        (r.workflow.run_id, context.episode_id, index)).fetchone())
    selection = json.loads(action['action'])
    host_path = r.api._manifest(context, create=False) / 'actions' / digest(final_key) / 'outcome.json'
    host_outcome, recorded = json.loads(host_path.read_text()), json.loads(action['result'])
    pending = recorded['pending_work_after_action']
    assert set(pending) == {'version', 'captured_at', 'items'}
    assert pending['version'] == 'pending_work_v1' and pending['items'] == []
    assert recorded == {**host_outcome, 'pending_work_after_action': pending}
    assert asyncio.run(r.api.execute(context, selection['tool'], selection['arguments'], final_key)) == host_outcome
    assert r.api.read_result(r.final_ref, r.scope) == r.body
    assert r.api.read_result(r.choices.partial_ref, r.scope) == early
    family = r.workflow.episode_bindings.for_role('results')
    for parent_record, child_record, expected, schema in ((r.science, r.results, r.returned, r.result_form),
            (r.archive, r.science, r.forwarded, r.parent_form)):
        parent_context = r.api.appservice.custody.context(parent_record['episode_id'])
        child_context = r.api.appservice.custody.context(child_record['episode_id'])
        family.validate_received_report(child_context, expected, schema)
        commission_index = int(child_context.path[-1][1].removeprefix('child_'))
        refs = family.received_form_references(parent_context, expected, schema,
            f'{r.workflow.run_id}:{parent_context.episode_id}:{commission_index}:typed_form')
        assert r.final_ref in refs
        facts = r.api.phylogeny_returns.received_facts(parent_context, r.parent_form)
        assert facts == {'bvbrc_phylogeny_measurements': r.forwarded['numbers']}
    assert r.native.calls == calls
    assert {table: r.store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] for table in tables} == counts
    assert dict(r.store.db.execute('SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
        (r.workflow.run_id, context.episode_id, index)).fetchone()) == action
    write(r.directory / 'saved-replay-verification.json', {'operation_key': final_key,
        'raw_host_outcome': host_outcome, 'workflow_pending_work_after_action': pending,
        'counts_before': counts, 'counts_after': counts, 'native_calls_added': 0,
        'saved_recalculation_equal': True, 'changed_pair_recalculation_without_parsing': True,
        'typed_read_and_admission_without_calculation': True, 'durable_action_unchanged': True})
