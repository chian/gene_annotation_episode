"""Scripted choices through the actual barcode Workflow and typed return path.

Only the caller's original reads, original request and explicit mapping are supplied. Native results, action
receipts, return forms and observations are produced by their production
owners. The test harness waits for the original native handle before choosing
results; this does not prescribe a production monitoring schedule.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator
from method_loop.archive import iter_json
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.communication import plain, validate_closed_schema
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.native_barcode_contracts import OPERATION
from test_barcode_input_authority import selected_job
from gene_annotation_episode.barcode_return_views import (
    PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE, barcode_fact_sources,
)
from gene_annotation_episode.native_barcode_contracts import (
    POLICY,
)
from gene_annotation_episode.native_barcode_local import local_barcode_plan
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[2]
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
RUN_ID = 'barcode-workflow496'
TASK = ('Quantify the supplied barcode read observations and their explicit target mappings. '
    'Return the requested read-count fractions and literal sequence-distance measurements, then compare '
    'the selected cut of the retained cluster tree. Preserve sample identity and duplicate read occurrences; '
    'read counts do not establish independent molecules, partner requirements, coexpression or gene function.')
SOURCES = {'barcode': PROJECTION_SOURCE, 'saved': SAVED_SOURCE, 'failures': FAILURE_SOURCE}
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
        'purpose': 'Return the requested typed measurements with their original numerical meanings and custody.',
        'assignment': assignment, 'schema_json': json.dumps(form), 'initial_report_json': '{}'}, 'report_update': {}}


def provider_value(value, schema):
    """Encode scripted selections using the provider's existing strict schema."""
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


def rows(store, table):
    return sorted((dict(row) for row in store.db.execute('SELECT * FROM ' + table)), key=canonical)


def controller_factory(path, initial):
    def estimate(raw, parameters, contexts):
        horizon = 1 if path[-1][0] == 'annotation' else 3
        return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1), parameters,
            {'fixture': 'caller_selected_scientific_test_estimator_only'})
    scientific = path[-1][0] in {'annotation', 'scientific_process'}
    return YieldController(str(path), initial, 0, YieldParameters(100, 50),
        estimate_with_context=estimate if scientific else None)


def assemble(store, directory, provider, configuration):
    factory = ExecutionServiceFactory.from_record(configuration['factory'])
    tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
    application = factory(store, run_id=RUN_ID, directory=directory / 'run', tool_registry=tools)
    flow = Workflow(store, tools, provider, directory / 'run', RUN_ID,
        controller_factory=controller_factory, project_credit=lambda *_args, **_kwargs: 0,
        annotation_child_roles=('scientific_process',), episode_record_receipts=True,
        initial_known_record_refs=configuration['initial_refs'],
        episode_binding_descriptors=(configuration['scientific_binding'], *application.episode_binding_descriptors),
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    return flow, tools


async def run_root(flow, configuration):
    root = flow.build('annotation', 'root', configuration['goal'], configuration['scope'])
    record = await root.run_async(flow.context)
    await root.build_result(record)
    return root, record, json.loads(''.join(iter_json(record.as_record())))


def result_form(*fields, completed=False):
    definitions = barcode_fact_sources()
    properties = {field: deepcopy(definitions[SOURCES[field]]['report_schema']) for field in fields}
    if completed:
        properties['completed'] = {'type': 'boolean', 'x-source': 'execution_completed'}
    return validate_closed_schema({'type': 'object', 'properties': properties,
        'required': list(properties), 'additionalProperties': False})


def selector(*, saved=None):
    projection = {'version': 'barcode_projection_request_v1',
        'view': 'summary' if saved is None else 'clusters',
        'fields': ['total_records', 'extracted_records', 'retained_read_count', 'extraction_fraction',
            'retained_fraction_extracted', 'retained_fraction_all_reads', 'pair_count', 'mean_pair_distance',
            'cluster_count', 'uniquely_assigned_target_read_count', 'ambiguous_target_read_count',
            'unmapped_target_read_count'] if saved is None else ['cluster_barcode_count', 'cluster_read_count',
                'cluster_fraction_all_reads', 'cluster_fraction_retained_reads'],
        'barcode_keys': None, 'cluster_ids': None if saved is None else [1],
        'target_keys': None, 'top_k': None, 'include_sample': True}
    return {'version': 'barcode_result_selector_v1',
        'mode': 'native_result' if saved is None else 'saved_sheet_recalculation',
        'parameters': {'version': 'barcode_calculation_parameters_v1', 'min_count': 2,
            'cluster_population': ['AAAA', 'AAAT', 'TTTT'], 'cut_threshold': 3 if saved is None else 3.5,
            'target_aggregation': 'unique_mapping_only'},
        'projection': projection, 'saved_sheet_file': deepcopy(saved)}

def worker_runs(directory):
    runs = []
    for path in sorted((directory / 'run').rglob('worker-capture.json')):
        capture = json.loads(path.read_bytes())
        if capture.get('version') == 'barcode_worker_capture_v1':
            runs.append({'directory': str(path.parent / 'worker'), 'capture': capture,
                'plan': json.loads((path.parent / 'worker-plan.json').read_bytes())})
    return runs


def workflow_case(directory, software, *, before_saved=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    store = Store(directory / 'state')
    store.create_problem(raw_sequence='ACGTACGT', molecule='dna')
    caller_sources = [json.loads(row['data']) for row in store.db.execute(
        "SELECT data FROM records WHERE record_type='source'")]
    assert len(caller_sources) == 1
    assert caller_sources[0]['provider'] == caller_sources[0]['origin'] == 'caller'
    scope = store.validate_scope()
    workspace = directory / 'workspace'
    workspace.mkdir()
    requested = selected_job(store, workspace, deepcopy(software))
    job = requested['native_barcode']
    raw_refs = [row['file']['artifact_ref'] for row in job['inputs'].values()]
    assert [json.loads(row['data']) for row in store.db.execute(
        "SELECT data FROM records WHERE record_type='source'")] == caller_sources
    practical = {'version': 'practical_assignment_v1', 'assignment_id': 'selected-barcode496',
        'resource_id': 'here', 'resource_kind': 'local', 'workspace': str(workspace), 'endpoint': 'usable_handoff',
        'requested_job': requested,
        'progress_requirements': [{'key': 'handoff', 'credit': 7, 'predicate': {'kind': 'requested_job_handoff'}}],
        'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {'allocation': deepcopy(POLICY)}}
    launch = {'version': 'execution_launch_assignment_v1', 'requests': {'here': practical},
        'immutable_input_versions': [{'reference': row['file']['artifact_ref'], 'version': None,
            'content_sha256': row['file']['sha256']} for row in job['inputs'].values()],
        'constraints': {'allowed_resource_ids': ['here'], 'allowed_kinds': ['local'], 'allocation': deepcopy(POLICY)}}
    resources = {'here': {'kind': 'local', 'workspace': str(workspace), 'policy': deepcopy(POLICY),
        'native_barcode': [{'operation': OPERATION, 'software': deepcopy(software)}]}}
    factory = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)
    preliminary_tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
    application = factory(store, run_id=RUN_ID, directory=directory / 'run', tool_registry=preliminary_tools)
    binding = prepare_scientific_binding(run_directory=directory / 'run', source_directory=PUBLICATION,
        tool_catalog=preliminary_tools.catalog(), child_roles=('scientific_process', 'launch', 'results'),
        resource_catalogs=application.resource_tool_catalogs)
    library = ScientificProcessLibrary(directory / 'run/scientific-process-library')
    scientific_assignment = {'selection': {'version': 'scientific_process_selection_v3',
        'evidence_axis': library.reference('A107'), 'thought_pattern': library.reference('P13'),
        'child_tool_info': [{'name': OPERATION, 'resources': 'local'}]},
        'evidence_refs': scope['subject_refs'], 'constraints': {'no_external_acquisition': True, 'allocation': deepcopy(POLICY)},
        'context': {'supplied_sequence': 'ACGTACGT', 'molecule': 'dna',
            'supplied_barcode_inputs': deepcopy(job['inputs']), 'candidate_annotation_required': False}}
    configuration = {'factory': factory.as_record(), 'scientific_binding': binding, 'goal': TASK,
        'scope': scope, 'initial_refs': raw_refs}
    write(directory / 'fixture-configuration.json', configuration)
    full_form, parent_form = result_form('barcode', 'saved', 'failures', completed=True), result_form('barcode')

    class Choices:
        def __init__(self):
            self.calls, self.turns, self.native_bytes = [], {}, {}
            self.plan = self.target = self.handoff = self.original_return = None

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
                answer = commission('launch_local', current['execution_assignment']['requests']['here'], scope,
                    HANDOFF_FORM, objective='Execute the exact supplied barcode request on the configured local resource.')
            elif current.get('execution_assignment', {}).get('version') == RESULTS_VERSION:
                assert turn == 1
                answer = action('execution.results.collect')
            elif 'scientific_process' not in current:
                assert turn == 1
                answer = commission('scientific_process', scientific_assignment, scope, parent_form, objective=TASK)
            elif turn == 1:
                answer = commission('launch', launch, scope, HANDOFF_FORM,
                    objective='Extract the supplied barcode reads with their original request, parameters and allocation.')
            elif turn == 2:
                reader = PracticalReceiptInformation(store, RUN_ID)
                self.handoff, = [ref for ref in current['child_reports'][-1]['references']
                    if reader.read(ref, scope)['receipt']['tool_name'] == 'practical.job.start']
                self.target = owner.job_progress_provider.targets.read_target(self.handoff, scope)
                outcome = await asyncio.to_thread(native_lifecycle.wait_job,
                    native_lifecycle.NativeJobHandle(Path(self.target['execution_id'])))
                assert outcome.returncode == 0, outcome
                self.plan = local_barcode_plan(self.target['assignment'], self.target['execution_id'])
                for spec in self.plan['outputs']:
                    path = Path(self.plan['attempt_directory']) / spec['relative_path']
                    if path.is_file():
                        self.native_bytes[spec['role']] = path.read_bytes()
                write(directory / 'original-native-plan.json', self.plan)
                write(directory / 'native-lifecycle.json', {'returncode': outcome.returncode, 'metadata': outcome.metadata})
                answer = commission('results', {'version': RESULTS_VERSION, 'handoff_ref': self.handoff,
                    'selector': selector()}, scope, full_form,
                    objective='Return the selected read-count and sequence-distance quantities, retained numerical sheet identity and located qualifications.')
            elif turn == 3:
                self.original_return = deepcopy(current['child_reports'][-1])
                assert self.original_return['completed'], self.original_return
                sheet_file, = self.original_return['saved']
                if before_saved:
                    before_saved(SimpleNamespace(store=store, owner=owner, flow=flow, directory=directory,
                        workspace=workspace, sheet_file=sheet_file, original_return=self.original_return, provider=self,
                        science_context=owner.native_barcode_returns.context(episode_id)))
                prior = store.db.execute('SELECT delivery_ref FROM runtime_report_attempts '
                    'WHERE parent_episode_id=? AND decision_index=1', (episode_id,)).fetchone()
                assert prior is not None
                answer = {'selection': {'kind': 'redeliver_report', 'delivery_ref': prior['delivery_ref'],
                    'purpose': 'Redeliver the exact original requested numerical facts without another calculation.',
                    'schema_json': json.dumps(full_form)}, 'report_update': {}}
            else:
                assert turn == 4
                assert current['child_reports'][-1] == self.original_return
                sheet_file, = self.original_return['saved']
                answer = commission('results', {'version': RESULTS_VERSION, 'handoff_ref': self.handoff,
                    'selector': selector(saved=sheet_file)}, scope, full_form,
                    objective='Recut the retained average-linkage tree at distance 3.5 and return only the selected cluster quantities.')
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
        contexts = {row['episode_id']: owner.native_barcode_returns.context(row['episode_id']) for row in records}
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
            full_form=full_form, scope=scope, workspace=workspace, job=job)
        write(directory / 'CASE.json', {'scope': 'scripted choices, synthetic supplied reads and mappings, actual Workflow and local barcode analysis',
            'returned': returned, 'forwarded': forwarded,
            'histories': {role: [r['controller_state'] for r in group] for role, group in by_role.items()}, 'archive': archive})
        return case
    except BaseException:
        store.close()
        raise
