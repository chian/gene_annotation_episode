"""One new tiny database reused by five authentic jobs through shared episodes.

Episode decisions are scripted fixtures. Native programs, retained capture,
requested publication, parent delivery and practical termination are actual paths.
No database BLAST, biological annotation, model inference or remote work occurs.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess
from types import SimpleNamespace

from jsonschema import Draft202012Validator
from method_loop.archive import iter_json
import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.blast_utility_result_views import blast_utility_fact_sources
from gene_annotation_episode.communication import plain, validate_closed_schema
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.native_blast_utility_contracts import requested_job_from_native_blast_utility
from gene_annotation_episode.native_blast_utility_local import local_blast_utility_plan
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_blast_utility_contracts_625 import operation
from test_blast_utility_result_views_629 import selector as result_selector
from test_native_blast_utility_producer_628 import POLICY
from test_native_hmmer_preparation_nested_workflow import provider_value, walk, history

ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
BIN = ROOT / 'resources/software/ncbi-blast-2.17.0+/bin'
RUN_ID = 'utility-workflow634'
MODES = ('create_sequence_database', 'extract_sequences', 'info', 'metadata', 'integrity')
RESULT_FIELDS = ('status', 'sequences', 'database_fields', 'integrity', 'preparation',
    'prepared_database', 'checks', 'failures', 'missing', 'artifacts', 'saved_data')
SCIENCE_FIELDS = ('status', 'sequences', 'database_fields', 'integrity', 'checks', 'failures', 'missing')
FASTA = b'>KEEP_A\nACGTTGCAACGT\n>KEEP_B\nTTGCAATTGCAA\n>KEEP_C\nACGTRYNAC\n'


def form_for(fields, completed=False):
    descriptions = blast_utility_fact_sources()
    properties = {field: deepcopy(descriptions['execution.blast_utility_' + field]['report_schema'])
        for field in fields}
    if completed:
        properties['completed'] = {'type': 'boolean', 'x-source': 'execution_completed'}
    return validate_closed_schema({'type': 'object', 'properties': properties,
        'required': list(properties), 'additionalProperties': False})


def child(role, assignment, scope, form):
    return {'selection': {'kind': 'episode_child', 'role': role,
        'goal': 'Prepare the supplied sequence database, inspect selected native facts and return the requested data.',
        'scope': scope, 'purpose': 'Return only the requested sequence, database or integrity facts.',
        'assignment': assignment, 'schema_json': json.dumps(form), 'initial_report_json': '{}'},
        'report_update': {}}


def selected(tool):
    return {'selection': {'kind': 'tool', 'tool': tool, 'arguments': {}}, 'report_update': {}}


def selected_result(mode):
    common = {'include_checks': True, 'saved_data': ['result']}
    if mode == 'create_sequence_database':
        return result_selector(**{**common, 'database_fields': ['database_sequence_count', 'database_residue_count'],
            'preparation': {'fields': ['inventory_complete', 'compatibility']}, 'prepared_database': True,
            'artifacts': [{'direction': 'output', 'role': 'preparation_receipt', 'ordinal': 0},
                {'direction': 'output', 'role': 'database_metadata', 'ordinal': None}],
            'saved_data': ['result', 'prepared_database']})
    if mode == 'extract_sequences':
        return result_selector(**common, sequences={'selector_ordinals': [1],
            'sequence_fields': ['normalized_sequence']})
    if mode in {'info', 'metadata'}:
        return result_selector(**common, database_fields=['database_sequence_count', 'database_residue_count'])
    return result_selector(**common, integrity={'fields': ['observed_checked_count',
        'observed_population_count', 'observed_sampled_oids', 'diagnostics']})


def original_job(mode, software, source, store, built):
    op = operation(mode)
    if mode == 'create_sequence_database':
        op['parameters'].update(title='workflow634 original three sequences', output_prefix='database/tiny')
        inputs = [{'input_key': 'source', 'role': 'sequence_input', 'path': str(source), 'format': 'fasta',
            'sha256': hashlib.sha256(FASTA).hexdigest(), 'size_bytes': len(FASTA), 'artifact_ref': None}]
        databases = []
    else:
        assert built is not None
        manifest = built['prepared_database'][0]['manifest']
        assert built['prepared_database'][0]['status'] == 'available'
        descriptor, = [row for row in built['saved_data'] if row['kind'] == 'prepared_database']
        op['database_key'] = manifest['database_key']
        inputs = []
        databases = [{'database_key': manifest['database_key'], 'role': 'target', 'kind': manifest['kind'],
            'identity': manifest['identity'], 'native_paths': manifest['native_paths'], 'manifest': manifest,
            'manifest_file': {'path': str(store.path / 'artifacts' / descriptor['sha256'][:2] / descriptor['sha256']),
                'artifact_ref': descriptor['artifact_ref'], 'sha256': descriptor['sha256'],
                'size_bytes': descriptor['size_bytes']}}]
        if mode == 'extract_sequences':
            op['parameters'].update(selectors=[{'ordinal': 0, 'value': 'KEEP_B'}, {'ordinal': 1, 'value': 'KEEP_B'}],
                range={'start_1based': 2, 'end_1based': 7}, strand='minus')
    fmt = {'create_sequence_database': 'text', 'extract_sequences': 'blastdbcmd_tabular_v1',
        'info': 'blastdb_info_text', 'metadata': 'blastdb_metadata_json', 'integrity': 'blastdbcheck_text'}[mode]
    outputs = [{'role': 'stdout', 'path_kind': 'file', 'relative_path': 'logs/native.stdout', 'format': fmt},
        {'role': 'stderr', 'path_kind': 'file', 'relative_path': 'logs/native.stderr', 'format': 'text'}]
    if mode == 'create_sequence_database':
        outputs.append({'role': 'database_family', 'path_kind': 'prefix',
            'relative_path': 'database/tiny', 'format': 'blastdb_family'})
    return {'version': 'native_blast_utility_job_v1', 'operation': op, 'software': software[op['program']],
        'environment': {'NCBI_DONT_USE_NCBIRC': '1', 'BLAST_USAGE_REPORT': 'false'},
        'inputs': inputs, 'databases': databases, 'outputs': outputs}


def run_case(directory):
    store = Store(directory / 'state')
    store.create_problem(raw_sequence='TTGCAATTGCAA', molecule='dna')
    scope = store.validate_scope()
    source = directory / 'supplied.fa'
    source.write_bytes(FASTA)
    workspace = directory / 'workspace'
    workspace.mkdir()
    software = {name: {'executable': str(BIN / name),
        'sha256': hashlib.sha256((BIN / name).read_bytes()).hexdigest(), 'engine_version': '2.17.0+'}
        for name in ('makeblastdb', 'blastdbcmd', 'blastdbcheck')}
    bindings = [{'program': operation(mode)['program'], 'mode': mode,
        'software': software[operation(mode)['program']], 'molecules': ['dna']} for mode in MODES]
    resources = {'here': {'kind': 'local', 'workspace': str(workspace), 'policy': POLICY,
        'native_blast_utility': bindings}}
    handoff_form = {'type': 'object', 'additionalProperties': False, 'properties': {
        'completed': {'type': 'boolean', 'x-source': 'execution_completed'},
        'references': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string',
            'format': 'reference', 'x-reference-namespace': 'execution_handoff'},
            'x-source': 'execution_handoff_refs'}}, 'required': ['completed', 'references']}
    results_form, science_form = form_for(RESULT_FIELDS, True), form_for(SCIENCE_FIELDS)
    tools = ToolRegistry(store)
    application = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)(
        store, run_id=RUN_ID, directory=directory / 'run', tool_registry=tools)
    descriptor = prepare_scientific_binding(run_directory=directory / 'run', source_directory=PUBLICATION,
        tool_catalog=tools.catalog(), child_roles=('scientific_process', 'launch', 'results'),
        resource_catalogs=application.resource_tool_catalogs)
    library = ScientificProcessLibrary(directory / 'run/scientific-process-library')
    science_assignment = {'selection': {'version': 'scientific_process_selection_v3',
        'evidence_axis': library.reference('A101'), 'thought_pattern': library.reference('P01'),
        'child_tool_info': [{'name': 'native.' + row['program'] + '.' + row['mode'], 'resources': 'local'} for row in bindings]},
        'evidence_refs': scope['subject_refs'], 'constraints': {'no_external_acquisition': True, 'allocation': POLICY},
        'context': {'supplied_sequence': 'TTGCAATTGCAA', 'molecule': 'dna', 'candidate_annotation_required': False}}
    owner = ExecutionEpisodes(None, store=store, directory=directory / 'run', run_id=RUN_ID,
        resources=resources, initial_information={}, tool_registry=tools, handoff_unit=3,
        acquired_record_unit=2, log_window_bytes=128, log_roles=('stdout', 'stderr'))

    def controller(path, initial):
        def estimate(raw, parameters, contexts):
            horizon = 1 if path[-1][0] == 'annotation' else 2 * len(MODES)
            return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1), parameters,
                {'fixture': 'explicit_scientific_test_horizon_not_production_stopping'})
        return YieldController(str(path), initial, 0, YieldParameters(100, 50),
            estimate_with_context=estimate if path[-1][0] in {'annotation', 'scientific_process'} else None)

    class Choices:
        def __init__(self):
            self.calls, self.jobs, self.plans, self.handoffs, self.native_outcomes = [], [], [], [], []
            self.science_calls = 0
            self.built = None
            self.assignment = None
            self.resource_calls, self.result_calls = set(), set()

        async def complete(self, episode_id, role, instructions, current, schema):
            self.calls.append({'episode_id': episode_id, 'role': role})
            assert not current.get('feedback'), current.get('feedback')
            if 'practical_assignment' in current:
                assert episode_id not in self.resource_calls, 'unexpected additional practical decision'
                self.resource_calls.add(episode_id)
                assert current['practical_assignment'] == self.assignment
                answer = selected('practical.job.start')
            elif current.get('execution_assignment', {}).get('version') == 'execution_launch_assignment_v1':
                answer = child('launch_local', self.assignment, scope, handoff_form)
            elif current.get('execution_assignment', {}).get('version') == RESULTS_VERSION:
                assert episode_id not in self.result_calls, 'requested result did not complete on its original selected action'
                self.result_calls.add(episode_id)
                answer = selected('execution.results.collect')
            elif 'scientific_process' not in current:
                answer = child('scientific_process', science_assignment, scope, science_form)
            else:
                self.science_calls += 1
                index = (self.science_calls - 1) // 2
                mode = MODES[index]
                if self.science_calls % 2:
                    if index == 1:
                        self.built = current['child_reports'][-1]
                    job = original_job(mode, software, source, store, self.built)
                    self.jobs.append(job)
                    request = requested_job_from_native_blast_utility(job)
                    self.assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'utility634-' + mode,
                        'resource_id': 'here', 'resource_kind': 'local', 'workspace': str(workspace),
                        'endpoint': 'usable_handoff', 'requested_job': request,
                        'progress_requirements': [{'key': 'handoff', 'credit': 7,
                            'predicate': {'kind': 'requested_job_handoff'}}],
                        'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
                        'inventory_snapshot': {}, 'constraints': {'allocation': POLICY}}
                    launch = {'version': 'execution_launch_assignment_v1', 'requests': {'here': self.assignment},
                        'immutable_input_versions': [], 'constraints': {'allowed_resource_ids': ['here'],
                            'allowed_kinds': ['local'], 'allocation': POLICY}}
                    answer = child('launch', launch, scope, handoff_form)
                else:
                    handoff, = current['child_reports'][-1]['references']
                    target = flow.progress_provider.job_provider.targets.read_target(handoff, scope)
                    completed = await asyncio.to_thread(native.wait_job, native.NativeJobHandle(Path(target['execution_id'])))
                    # Integrity may expose a genuine unavailable taxonomy dependency;
                    # its actual diagnostics must still pass through requested results.
                    assert completed.returncode == 0 or mode == 'integrity', completed
                    self.native_outcomes.append(completed.returncode)
                    self.plans.append(local_blast_utility_plan(self.assignment, target['execution_id']))
                    self.handoffs.append(handoff)
                    answer = child('results', {'version': RESULTS_VERSION, 'handoff_ref': handoff,
                        'selector': selected_result(mode)}, scope, results_form)
            answer = provider_value(plain(answer), plain(schema))
            Draft202012Validator(plain(schema)).validate(answer)
            return answer

        async def release(self, episode_id):
            pass

    provider = Choices()
    flow = Workflow(store, tools, provider, directory / 'run', RUN_ID, controller_factory=controller,
        project_credit=lambda *args, **kwargs: 0, annotation_child_roles=('scientific_process',),
        episode_record_receipts=True, initial_known_record_refs=[],
        episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    root = flow.build('annotation', 'root', 'Inspect selected facts from a supplied tiny sequence database.', scope)
    async def execute():
        record = await root.run_async(flow.context)
        await root.build_result(record)
        return record
    record = asyncio.run(execute())
    records = list(walk(json.loads(''.join(iter_json(record.as_record())))))
    contexts = {row['episode_id']: owner.native_blast_utility_returns.context(row['episode_id']) for row in records}
    results = []
    for row in records:
        context = contexts[row['episode_id']]
        if context.role == 'results':
            outcome = json.loads(flow.journal.row('runtime_actions', context.episode_id, 0)['result'])
            returned = json.loads(flow.journal.row('runtime_forms', context.episode_id)['form'])
            results.append({'context': context, 'record': row, 'outcome': outcome, 'returned': returned})
    results.sort(key=lambda item: MODES.index(item['outcome']['result']['prepared']['operation']['mode']))
    science_context, = [context for context in contexts.values() if context.role == 'scientific_process']
    forwarded = json.loads(flow.journal.row('runtime_forms', science_context.episode_id)['form'])
    case = SimpleNamespace(store=store, flow=flow, owner=owner, provider=provider, root=root, record=record,
        records=records, contexts=contexts, root_context=contexts[record.episode_id], science_context=science_context,
        results=results, forwarded=forwarded, results_form=results_form, science_form=science_form,
        scope=scope, workspace=workspace, source=source, directory=directory)
    (directory / 'CASE.json').write_text(json.dumps({'scope': 'actual tiny native utilities, scripted shared episodes',
        'plans': provider.plans, 'jobs': provider.jobs, 'native_returncodes': provider.native_outcomes,
        'results': [{key: row[key] for key in ('outcome', 'returned')} for row in results], 'forwarded': forwarded,
        'histories': {row['episode_id']: row['controller_state'] for row in records}}, indent=2) + '\n')
    return case


@pytest.fixture(scope='module')
def native_case(tmp_path_factory):
    case = run_case(tmp_path_factory.mktemp('utility-workflow634'))
    yield case
    case.store.close()


def test_original_database_is_reused_by_all_four_selected_inspections(native_case):
    case = native_case
    assert len(case.provider.plans) == len(case.results) == 5
    built = case.results[0]['returned']['prepared_database'][0]['manifest']
    for job in case.provider.jobs[1:]:
        assert job['databases'][0]['manifest'] == built
    for selected in case.results:
        body, returned = selected['outcome']['result'], selected['returned']
        assert body['complete'] and returned['completed'], body
        assert returned['status'] == [body['status']]
        result = json.loads(case.store.get_artifact(body['prepared']['result_artifact_ref']))
        mode = result['operation']['mode']
        if mode in {'create_sequence_database', 'info', 'metadata'}:
            assert {row['field_name']: row['value'] for row in returned['database_fields']} == {
                'database_sequence_count': 3, 'database_residue_count': 33}
            originals = result.get('native_fields', result.get('native_metadata'))
            assert all({key: value for key, value in row.items() if key not in {'source_ref', 'database_key'}} in originals
                for row in returned['database_fields'])
        elif mode == 'extract_sequences':
            assert len(returned['sequences']) == 2
            for row in returned['sequences']:
                assert row['selector_ordinals'] == [1] and row['native_accession'] == 'KEEP_B'
                assert row['native_reported_length'] == 12 and row['returned_symbol_count'] == 6
                assert row['effective_range'] == {'start_0based': 1, 'end_exclusive': 7, 'strand': 'minus'}
                assert row['sequences'] == {'normalized_sequence': 'ATTGCA'}
        else:
            assert returned['integrity'][0]['scope'] == result['scope']
            assert returned['integrity'][0]['fields'] == {key: result[key] for key in selected_result(mode)['integrity']['fields']}
        case.owner.validate_report(selected['context'], returned, case.results_form)
    case.owner.validate_received_report(case.root_context, case.forwarded, case.science_form)
    assert case.store.count('annotation') == case.store.count('observation') == 0


def test_actual_episode_grants_and_terminal_observations_match_selected_work(native_case):
    case = native_case
    assert len(case.provider.calls) == 26
    assert case.flow.catalog(case.scope, source=case.root.source) == []
    for row in case.records:
        role = case.contexts[row['episode_id']].role
        for table in ('runtime_actions', 'runtime_observations'):
            assert case.store.db.execute('SELECT count(*) FROM ' + table + ' WHERE episode_id=?',
                (row['episode_id'],)).fetchone()[0] == row['units_consumed']
        if role in {'launch_local', 'launch', 'results'}:
            assert row['units_consumed'] == 1
            assert row['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
            assert history(row) == [{'launch_local': 7, 'launch': 3, 'results': 2}[role]]
    assert history(case.record.as_record()) == [0]
    root_known = set(case.flow.receipts.known(case.root_context.episode_id))
    science_known = set(case.flow.receipts.known(case.science_context.episode_id))
    resolver = case.flow.resolver(case.scope, context=case.root_context)
    for selected in case.results:
        body = selected['outcome']['result']
        assert body['source_ref'] in root_known
        for row in [*body['saved_data'], *body['artifacts']]:
            assert row['artifact_ref'] in science_known
            assert row['artifact_ref'] not in root_known and not resolver(row['artifact_ref'], 'artifact')
        proof = case.owner.completion_for_action(selected['context'], body['operation_key'])
        assert proof and case.owner.verify_completion(selected['context'], proof)
    for plan in case.provider.plans:
        metadata = native.NativeJobHandle(Path(plan['identity']['execution_id'])).read()['metadata']
        assert metadata['policy'] == POLICY
        assert metadata['verified_cgroup']['memory_max'] == 20 * 1024**3
        assert metadata['verified_cgroup']['memory_swap_max'] == 0
        assert 'runtime_max' not in metadata['verified_cgroup']


def test_closed_returns_replay_without_native_files_or_parsing(native_case, monkeypatch):
    case = native_case
    before_context = deepcopy(case.owner.native_blast_utility_returns.received_context(case.root_context))
    shutil.rmtree(case.workspace)
    case.source.unlink()
    def forbidden(*args, **kwargs):
        raise AssertionError('closed replay attempted acquisition, native execution or parsing')
    for module, name in (
        ('native_blast_utility_result_publication', 'run_local_job'),
        ('native_blast_utility_acquisition', '_capture_file'),
        ('native_blast_utility_acquisition', 'local_blast_utility_plan'),
        ('native_blast_utility_results', 'prepare_native_blast_utility_result'),
        ('native_blast_utility_results', 'publish_selected_utility_result'),
        ('blast_database_extraction', 'parse_blastdbcmd_sequences'),
        ('blast_database_inspection', 'parse_blast_database_inspection'),
        ('blast_database_inspection', 'parse_blastdbcheck_diagnostics'),
        ('blast_database_preparation', 'populate_database_artifact_set')):
        monkeypatch.setattr('gene_annotation_episode.' + module + '.' + name, forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(case.owner.job_progress_provider.targets, 'observe_target', forbidden)
    before = list(case.store.db.iterdump())
    for selected in case.results:
        body = selected['outcome']['result']
        replay = asyncio.run(case.owner.execute(selected['context'], 'execution.results.collect', {}, body['operation_key']))
        assert replay == {key: value for key, value in selected['outcome'].items() if key != 'pending_work_after_action'}
    case.flow.receive_form(case.root.source, case.forwarded, case.science_form, 0, redelivery=True)
    assert case.owner.native_blast_utility_returns.received_context(case.root_context) == before_context
    assert list(case.store.db.iterdump()) == before
