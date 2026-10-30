"""Synthetic caller inputs and scripted choices through actual Workflow ports.

The fixture never inserts actions, receipts, forms, observations or authority.
Transport and archive mechanics follow437; scientific operands follow011/439.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator
from method_loop.archive import iter_json
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.communication import plain, validate_closed_schema
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.chromatin_interaction_return_views import (
    PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE, chromatin_fact_sources,
)
from gene_annotation_episode.native_chromatin_interaction_contracts import (
    POLICY, requested_job_from_chromatin, _dependency_roots,
)
from gene_annotation_episode.native_chromatin_interaction_local import local_chromatin_interaction_plan
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

ROOT = Path(__file__).resolve().parents[2]
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
WORKED = {r['example_key']: r['record'] for r in json.loads((ROOT /
    'verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/WORKED_RECORDS.json').read_text())['records']}
RUN_ID = 'chromatin-workflow451'
TASK = 'Measure the supplied synthetic chromatin contacts for E-P and E-Q in both declared populations and retain numerical qualifications.'
SOURCES = {'chromatin': PROJECTION_SOURCE, 'saved': SAVED_SOURCE, 'failures': FAILURE_SOURCE}
FIELDS = ['raw_contact', 'normalized_contact', 'expected_contact', 'fold_enrichment', 'above_fold_threshold']
TABLES = ('runtime_episodes', 'runtime_model_calls', 'runtime_actions', 'runtime_observations', 'runtime_forms',
    'runtime_report_attempts', 'runtime_estimation_contexts', 'runtime_timed_commissions',
    'runtime_record_receipts', 'runtime_receipt_inheritance')
HANDOFF_FORM = {'type': 'object', 'additionalProperties': False, 'properties': {
    'completed': {'type': 'boolean', 'x-source': 'execution_completed'},
    'references': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference',
        'x-reference-namespace': 'execution_handoff'}, 'x-source': 'execution_handoff_refs'}},
    'required': ['completed', 'references']}


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def action(name, arguments=None):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': arguments or {}}, 'report_update': {}}


def commission(role, assignment, scope, form, *, objective):
    return {'selection': {'kind': 'episode_child', 'role': role, 'goal': objective, 'scope': scope,
        'purpose': 'Return the requested typed facts with their original numerical meanings and custody.',
        'assignment': assignment, 'schema_json': json.dumps(form), 'initial_report_json': '{}'}, 'report_update': {}}


def provider_value(value, schema):
    if 'anyOf' in schema:
        for branch in schema['anyOf']:
            candidate = provider_value(value, branch)
            if Draft202012Validator(branch).is_valid(candidate):
                return candidate
        return value
    if schema.get('type') == 'string' and isinstance(value, dict) and schema.get('description', '').startswith('JSON encoding'):
        return json.dumps(value)
    if schema.get('type') == 'object' and isinstance(value, dict):
        result = dict(value)
        for name, field in schema.get('properties', {}).items():
            if name in result:
                result[name] = provider_value(result[name], field)
            elif name in schema.get('required', []) and Draft202012Validator(field).is_valid(None):
                result[name] = None
        return result
    if isinstance(value, list) and 'items' in schema:
        return [provider_value(item, schema['items']) for item in value]
    return value


def walk(record):
    yield record
    for unit in record['units']:
        if unit.get('child') is not None:
            yield from walk(unit['child'])


def history(record):
    return [unit['controller_step']['marginal_credit'] for unit in record['units']]


def result_form(*fields, completed=False):
    definitions = chromatin_fact_sources()
    properties = {field: deepcopy(definitions[SOURCES[field]]['report_schema']) for field in fields}
    if completed:
        properties['completed'] = {'type': 'boolean', 'x-source': 'execution_completed'}
    return validate_closed_schema({'type': 'object', 'properties': properties,
        'required': list(properties), 'additionalProperties': False})


def selector(*, saved=None, partial=False):
    value = deepcopy(WORKED['raw.selector'])
    value['population_keys'] = ['p0', 'p1'] if partial else ['p1']
    value['projection']['selection']['page']['limit'] = 4
    if saved is not None:
        value.update(mode='saved_sheet_recalculation', saved_sheet_bundle=deepcopy(saved))
        value['parameters']['contact']['fold_threshold'] = 1
    return value


def source(store, raw, label):
    artifact = store.artifact(raw)
    return store.put('source', {'provider': 'fixture.chromatin451.' + label,
        'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': None,
        'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')


def identity(store, artifact, format):
    metadata = store.get(artifact)
    return {'artifact_ref': artifact, 'sha256': metadata['sha256'],
        'size_bytes': metadata['size'], 'format': format}


def artifact_path(store, file):
    return store.path / 'artifacts' / file['sha256'][:2] / file['sha256']


def rows(store, table):
    return sorted((dict(row) for row in store.db.execute('SELECT * FROM ' + table)), key=canonical)


def controller_factory(*, partial):
    def controller(path, initial):
        def estimate(raw, parameters, contexts):
            horizon = 1 if path[-1][0] == 'annotation' else 2 if partial else 3
            return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1), parameters,
                {'fixture': 'caller_selected_scientific_test_horizon_only'})
        scientific = path[-1][0] in {'annotation', 'scientific_process'}
        return YieldController(str(path), initial, 0 if scientific or not partial else 1e9,
            YieldParameters(100, 50) if scientific or not partial else YieldParameters(2, 1),
            estimate_with_context=estimate if scientific else None)
    return controller


def assemble(store, directory, provider, configuration):
    factory = ExecutionServiceFactory.from_record(configuration['factory'])
    tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
    application = factory(store, run_id=RUN_ID, directory=directory / 'run', tool_registry=tools)
    flow = Workflow(store, tools, provider, directory / 'run', RUN_ID,
        controller_factory=controller_factory(partial=configuration['partial']),
        project_credit=lambda *_args, **_kwargs: 0, annotation_child_roles=('scientific_process',),
        episode_record_receipts=True, initial_known_record_refs=configuration['initial_refs'],
        episode_binding_descriptors=(configuration['scientific_binding'], *application.episode_binding_descriptors),
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    return flow, tools


async def run_root(flow, configuration):
    root = flow.build('annotation', 'root', configuration['goal'], configuration['scope'])
    record = await root.run_async(flow.context)
    await root.build_result(record)
    return root, record, json.loads(''.join(iter_json(record.as_record())))


def worker_runs(directory):
    runs = []
    for path in sorted((directory / 'run').rglob('prepared.json')):
        capture = json.loads(path.read_bytes())
        if capture.get('version') == 'chromatin_interaction_worker_capture_v1':
            runs.append({'directory': str(path.parent), 'capture': capture,
                'plan': json.loads((path.parent / 'plan.json').read_bytes())})
    return runs


def workflow_case(directory, software, *, partial=False, before_saved=None, contact_bytes=None,
        request_template=None, result_selector=None, saved_selector_factory=None, objective=TASK):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    store = Store(directory / 'state')
    store.create_problem(raw_sequence='ACGTACGT', molecule='dna')
    scope = store.validate_scope()
    request = deepcopy(WORKED['raw.request'] if request_template is None else request_template)
    if request_template is None:
        request['populations'] = [dict(request['populations'][0], population_key=key) for key in ('p0', 'p1')]
    initial_refs, reference_sources = [], {}
    references = [request['supplied_metadata']['reference']]
    if request['elements'] is not None:
        references.append(request['elements']['reference'])
    for reference in references:
        if reference['source_ref'] is None:
            continue
        key = canonical(reference)
        if key not in reference_sources:
            reference_sources[key] = source(store, key.encode(), 'reference')
            initial_refs.extend((reference_sources[key]['id'], reference_sources[key]['artifact_ref']))
        reference['source_ref'] = reference_sources[key]['id']
    metadata_rows = [row for name in ('samples', 'contact_sample_links')
        for row in request['supplied_metadata'][name] if row['source_ref'] is not None]
    if metadata_rows:
        metadata = source(store, canonical({'samples': request['supplied_metadata']['samples'],
            'contact_sample_links': request['supplied_metadata']['contact_sample_links']}).encode(), 'metadata')
        for row in metadata_rows:
            row['source_ref'] = metadata['id']
        initial_refs.extend((metadata['id'], metadata['artifact_ref']))
    fixture = ROOT / 'verification/tool_graders_chromatin_native_prerequisites_2026-10-27_440/fixture_generation/fixtures/four-bin-raw-weighted.cool'
    bindings = []
    supplied_files = [('contact', fixture.read_bytes() if contact_bytes is None else contact_bytes, 'cooler_hdf5_v3')]
    if request['elements'] is not None:
        supplied_files.append(('elements', b'chrA\t0\t2\tE\nchrA\t20\t23\tP\nchrA\t30\t33\tQ\n', 'bed_outer_span_v1'))
    for key, raw, format in supplied_files:
        supplied = source(store, raw, key)
        file = identity(store, supplied['artifact_ref'], format)
        request[key].update(source_ref=supplied['id'], file=file)
        bindings.append({'input_key': request[key]['input_key'], 'file': file, 'path': str(artifact_path(store, file))})
        initial_refs.extend((supplied['id'], supplied['artifact_ref']))
    workspace = directory / 'workspace'
    workspace.mkdir()
    environment = {'PYTHONPATH': os.pathsep.join([software['module_root'], *_dependency_roots(software)]),
        'PYTHONHOME': os.sys.base_prefix, 'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1', 'PYTHONDONTWRITEBYTECODE': '1',
        'TMPDIR': str(workspace / 'tmp'), 'TMP': str(workspace / 'tmp'), 'TEMP': str(workspace / 'tmp'),
        'XDG_CACHE_HOME': str(workspace / 'cache'), 'PIP_CACHE_DIR': str(workspace / 'cache/pip'),
        'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}
    job = {'request': request, 'software': deepcopy(software), 'input_bindings': bindings}
    practical = {'version': 'practical_assignment_v1', 'assignment_id': 'selected-chromatin451',
        'resource_id': 'here', 'resource_kind': 'local', 'workspace': str(workspace), 'endpoint': 'usable_handoff',
        'requested_job': requested_job_from_chromatin(job, environment=environment),
        'progress_requirements': [{'key': 'handoff', 'credit': 7, 'predicate': {'kind': 'requested_job_handoff'}}],
        'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {'allocation': deepcopy(POLICY)}}
    launch = {'version': 'execution_launch_assignment_v1', 'requests': {'here': practical},
        'immutable_input_versions': [], 'constraints': {'allowed_resource_ids': ['here'],
            'allowed_kinds': ['local'], 'allocation': deepcopy(POLICY)}}
    resources = {'here': {'kind': 'local', 'workspace': str(workspace), 'policy': deepcopy(POLICY),
        'native_chromatin_interactions': [{'operation': request['operation'], 'resource_kind': 'local',
            'analysis_modes': request['analysis_modes'], 'supported_formats': ['cooler_hdf5_v3'], 'software': deepcopy(software)}]}}
    factory = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)
    preliminary_tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
    application = factory(store, run_id=RUN_ID, directory=directory / 'run', tool_registry=preliminary_tools)
    binding = prepare_scientific_binding(run_directory=directory / 'run', source_directory=PUBLICATION,
        tool_catalog=preliminary_tools.catalog(), child_roles=('scientific_process', 'launch', 'results'),
        resource_catalogs=application.resource_tool_catalogs)
    library = ScientificProcessLibrary(directory / 'run/scientific-process-library')
    scientific_assignment = {'selection': {'version': 'scientific_process_selection_v3',
        'evidence_axis': library.reference('A101'), 'thought_pattern': library.reference('P01'),
        'child_tool_info': [{'name': 'analyze_chromatin_interactions', 'resources': 'local'}]},
        'evidence_refs': scope['subject_refs'], 'constraints': {'no_external_acquisition': True, 'allocation': deepcopy(POLICY)},
        'context': {'supplied_sequence': 'ACGTACGT', 'molecule': 'dna',
            'supplied_chromatin_request': deepcopy(request), 'candidate_annotation_required': False}}
    configuration = {'factory': factory.as_record(), 'scientific_binding': binding, 'goal': objective,
        'scope': scope, 'initial_refs': initial_refs, 'partial': partial}
    write(directory / 'fixture-configuration.json', configuration)
    full_form = result_form('chromatin', 'saved', 'failures', completed=True)
    parent_form = result_form('chromatin')
    selected_selector = deepcopy(selector(partial=partial) if result_selector is None else result_selector)

    class Choices:
        def __init__(self):
            self.calls, self.turns, self.native_bytes = [], {}, {}
            self.plan = self.target = self.handoff = self.original_return = self.loss = None
            self.input_refs = None

        async def complete(self, episode_id, role, instructions, current, schema):
            self.calls.append({'episode_id': episode_id, 'role': role, 'context': deepcopy(current)})
            write(directory / f'decision-{len(self.calls) - 1}.json', self.calls[-1])
            assert not current.get('feedback'), current.get('feedback')
            self.turns[episode_id] = self.turns.get(episode_id, 0) + 1
            turn = self.turns[episode_id]
            if 'practical_assignment' in current:
                assert turn == 1 and current['practical_assignment']['constraints']['allocation'] == POLICY
                answer = action('practical.job.start')
            elif current.get('execution_assignment', {}).get('version') == 'execution_launch_assignment_v1':
                assert turn == 1
                answer = commission('launch_local', current['execution_assignment']['requests']['here'], scope, HANDOFF_FORM,
                    objective='Execute the exact supplied chromatin request on the configured local resource.')
            elif current.get('execution_assignment', {}).get('version') == RESULTS_VERSION:
                assert turn == 1 or partial and turn == 2
                answer = action('execution.results.collect' if turn == 1 else 'execution.results.status')
            elif 'scientific_process' not in current:
                assert turn == 1
                answer = commission('scientific_process', scientific_assignment, scope, parent_form, objective=objective)
            elif turn == 1:
                if request_template is not None:
                    from gene_annotation_episode.chromatin_interaction_operands import validate_chromatin_job_inputs
                    # Defer optional provider classification; actual received
                    # records and exact source/file/metadata relations remain required.
                    self.input_refs = validate_chromatin_job_inputs(store,
                        owner.native_chromatin_interaction_returns.context(episode_id), practical,
                        reference_access=lambda *_: None)
                answer = commission('launch', launch, scope, HANDOFF_FORM,
                    objective=('Execute the supplied Cooler request for both declared populations with the original resource allocation.'
                        if request_template is None else 'Execute the exact supplied Cooler request with the original resource allocation.'))
            elif turn == 2:
                reader = PracticalReceiptInformation(store, RUN_ID)
                self.handoff, = [ref for ref in current['child_reports'][-1]['references']
                    if reader.read(ref, scope)['receipt']['tool_name'] == 'practical.job.start']
                self.target = owner.job_progress_provider.targets.read_target(self.handoff, scope)
                outcome = await asyncio.to_thread(native_lifecycle.wait_job,
                    native_lifecycle.NativeJobHandle(Path(self.target['execution_id'])))
                assert outcome.returncode == 0, outcome
                self.plan = local_chromatin_interaction_plan(self.target['assignment'], self.target['execution_id'])
                for spec in self.plan['outputs']:
                    path = Path(self.plan['attempt_directory']) / spec['relative_path']
                    if path.is_file():
                        self.native_bytes[spec['file_key']] = path.read_bytes()
                write(directory / 'original-native-plan.json', self.plan)
                write(directory / 'native-lifecycle.json', {'returncode': outcome.returncode, 'metadata': outcome.metadata})
                if partial:
                    spec, = [row for row in self.plan['outputs'] if row['file_key'] == 'p1.contacts']
                    path = Path(self.plan['attempt_directory']) / spec['relative_path']
                    path.unlink()
                    self.loss = {'kind': 'actual_post_execution_output_loss', 'population_key': 'p1', 'path': str(path),
                        'preserved_control_evidence': 'original sealed bundle and population manifests'}
                    write(directory / 'injected-loss.json', self.loss)
                answer = commission('results', {'version': RESULTS_VERSION, 'handoff_ref': self.handoff,
                    'selector': deepcopy(selected_selector)}, scope, full_form,
                    objective='Return the requested chromatin measurements, complete saved sheet and table identities, and located failures.')
            else:
                assert not partial and turn == 3
                self.original_return = deepcopy(current['child_reports'][-1])
                assert self.original_return['completed'], self.original_return
                bundle, = self.original_return['saved']
                if before_saved:
                    before_saved(SimpleNamespace(store=store, owner=owner, flow=flow, directory=directory,
                        workspace=workspace, bundle=bundle, original_return=self.original_return,
                        provider=self, science_context=owner.native_chromatin_interaction_returns.context(episode_id)))
                answer = commission('results', {'version': RESULTS_VERSION, 'handoff_ref': self.handoff,
                    'selector': deepcopy(selector(saved=bundle) if saved_selector_factory is None
                        else saved_selector_factory(deepcopy(bundle)))}, scope, full_form,
                    objective=('Recalculate only the explicitly received saved sheet and tables with fold threshold1; preserve original contact measurements.'
                        if saved_selector_factory is None else
                        'Calculate only the explicitly selected received saved sheet and tables; return the requested numerical projection.'))
            answer = provider_value(plain(answer), plain(schema))
            Draft202012Validator(plain(schema)).validate(answer)
            return answer

        async def release(self, episode_id):
            pass

    provider = Choices()
    flow, tools = assemble(store, directory, provider, configuration)
    owner = flow.episode_bindings.for_role('results')
    try:
        root, record, archive = asyncio.run(run_root(flow, configuration))
        records = list(walk(archive))
        contexts = {row['episode_id']: owner.native_chromatin_interaction_returns.context(row['episode_id']) for row in records}
        by_role = {}
        for row in records:
            by_role.setdefault(contexts[row['episode_id']].role, []).append(row)
        result_contexts = [contexts[row['episode_id']] for row in by_role['results']]
        returned = [json.loads(flow.journal.row('runtime_forms', c.episode_id)['form']) for c in result_contexts]
        outcomes = [json.loads(flow.journal.row('runtime_actions', c.episode_id, 0)['result']) for c in result_contexts]
        scientific_context, = [contexts[row['episode_id']] for row in by_role['scientific_process']]
        forwarded = json.loads(flow.journal.row('runtime_forms', scientific_context.episode_id)['form'])
        case = SimpleNamespace(store=store, directory=directory, flow=flow, tools=tools, owner=owner,
            provider=provider, configuration=configuration, root=root, record=record, archive=archive,
            records=records, contexts=contexts, by_role=by_role, result_contexts=result_contexts,
            returned=returned, outcomes=outcomes, scientific_context=scientific_context,
            root_context=contexts[record.episode_id], forwarded=forwarded, parent_form=parent_form,
            full_form=full_form, scope=scope, workspace=workspace, job=job, partial=partial)
        write(directory / 'CASE.json', {'scope': 'scripted choices, synthetic Cooler data, actual Workflow and local execution',
            'partial': partial, 'returned': returned, 'forwarded': forwarded,
            'histories': {role: [r['controller_state'] for r in group] for role, group in by_role.items()}, 'archive': archive})
        return case
    except BaseException:
        store.close()
        raise
