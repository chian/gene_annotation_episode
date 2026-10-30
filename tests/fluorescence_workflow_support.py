"""Bounded fluorescence Workflow fixture using actual native/result owners.

Run through529/run_checks.py only. Scripted choices supply input bytes and select
operations; they never supply parsed events, sheets, scientific results, receipts
or return forms. Two variants exercise the distinct aliases and actual parsers.
The deliberately partial result has an explicitly configured fixture estimator;
all completed practical endpoints retain the production completion estimator.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

from jsonschema import Draft202012Validator
from method_loop.archive import iter_json
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.communication import plain, validate_closed_schema
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.fluorescence_execution_common import identity
from gene_annotation_episode.fluorescence_return_views import (
    PROJECTION_SOURCE, CONTEXT_SOURCE, SAVED_SOURCE, FAILURE_SOURCE,
    fluorescence_fact_sources,
)
from gene_annotation_episode.native_fluorescence_contracts import (
    IMPLEMENTATION_NAMES, MODE, OPERATIONS, POLICY, fluorescence_environment,
    requested_job_from_fluorescence, validate_fluorescence_software,
)
from gene_annotation_episode.native_fluorescence_local import local_fluorescence_plan
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
RUN_ID = 'fluorescence-workflow571'
VALUES = [90, 100, 125, 150, 200, 250, 300, 350]
TASK = ('Calculate the explicitly supplied fluorescence gate population and intensity measurements '
    'from the supplied synthetic molecular measurements. Preserve sample, condition, channel, '
    'measurement-origin, units and missing-data distinctions; return only the requested cells and definitions.')
SOURCES = {'measurements': PROJECTION_SOURCE, 'contexts': CONTEXT_SOURCE,
    'saved': SAVED_SOURCE, 'failures': FAILURE_SOURCE}
TABLES = ('runtime_episodes', 'runtime_model_calls', 'runtime_actions', 'runtime_observations', 'runtime_forms',
    'runtime_report_attempts', 'runtime_estimation_contexts', 'runtime_timed_commissions',
    'runtime_record_receipts', 'runtime_receipt_inheritance')
LIMITS = dict(memory_max=21474836480, memory_swap_max=0, runtime_max='infinity',
    kill_mode='control-group', oom_policy='kill')
HANDOFF_FORM = {'type': 'object', 'additionalProperties': False, 'properties': {
    'completed': {'type': 'boolean', 'x-source': 'execution_completed'},
    'references': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference',
        'x-reference-namespace': 'execution_handoff'}, 'x-source': 'execution_handoff_refs'}},
    'required': ['completed', 'references']}


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def pin(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            h.update(block)
    return dict(path=str(path), sha256=h.hexdigest(), size_bytes=path.stat().st_size)


def software_closure(directory):
    """Pin the actual stdlib runtime inside the existing bounded test process.

    No installation, network access, application import discovery or replacement
    scientific implementation is performed. The producer verifies all these pins
    and its actual loaded module paths before/after parsing.
    """
    attempt = Path(os.environ['HMMER529_ATTEMPT']).resolve(strict=True)
    assert Path(sys.executable).resolve().is_relative_to(attempt)
    home = Path(sys.base_prefix).resolve(strict=True)
    assert home.is_relative_to(attempt)
    directory = Path(directory)
    module_root = directory / 'modules'
    package = module_root / 'gene_annotation_episode'
    package.mkdir(parents=True)
    implementation = []
    for name in IMPLEMENTATION_NAMES:
        source, target = ROOT / 'gene_annotation_episode' / name, package / name
        shutil.copyfile(source, target)
        target.chmod(0o444)
        implementation.append(pin(target))
    binary = directory / 'python'
    shutil.copyfile(Path(sys.executable).resolve(strict=True), binary)
    binary.chmod(0o555)
    stdlib = home / 'lib' / ('python%d.%d' % sys.version_info[:2])
    runtime = [pin(path) for path in sorted(stdlib.rglob('*')) if path.is_file()
        and not any(part in ('site-packages', 'dist-packages', '__pycache__')
            for part in path.relative_to(stdlib).parts) and path.suffix not in ('.pyc', '.pyo')]
    value = validate_fluorescence_software(dict(version='fluorescence_software_v1', python=pin(binary),
        python_version=sys.version, python_home=str(home), module_root=str(module_root),
        implementation_files=implementation, dependency_roots=[], distributions=[], runtime_files=runtime))
    write(directory / 'software.json', value)
    return value


def cell_request(kind, metric, *, gate_key, denominator='none', domain_key=None, channel_key=None):
    return dict(kind=kind, metric=metric, gate_key=gate_key, denominator=denominator,
        domain_key=domain_key, channel_key=channel_key, control_key=None, native_report_key=None)


def parameters(*, denominator='parent'):
    return dict(fraction_requests=[dict(gate_key=f'gate-{i}', denominator=denominator) for i in range(2)],
        intensity_requests=[dict(gate_key=f'gate-{i}', domain_key=f'domain-{i}', channel_key=f'channel-{i}')
            for i in range(2)], control_requests=[], native_comparison_requests=[])


def selector(*, saved=None):
    requests = []
    denominator = 'parent' if saved is None else 'evaluable'
    for i in range(2):
        requests.extend(cell_request('population', metric, gate_key=f'gate-{i}')
            for metric in ('retained_event_count', 'selected_event_count'))
        requests.extend(cell_request('fraction', metric, gate_key=f'gate-{i}', denominator=denominator)
            for metric in ('selected_fraction', 'selected_percent'))
        requests.extend(cell_request('intensity', metric, gate_key=f'gate-{i}',
            domain_key=f'domain-{i}', channel_key=f'channel-{i}')
            for metric in ('selected_intensity_mean', 'selected_intensity_median'))
    return dict(version='fluorescence_result_selector_v1',
        mode='native_result' if saved is None else 'saved_sheet_recalculation',
        selection=dict(requests=requests, offset=0 if saved is None else 2, limit=12 if saved is None else 4),
        context_fields=['sources', 'samples', 'channels', 'domains', 'populations', 'gates'],
        saved_sheet_file=deepcopy(saved), parameters=None if saved is None else parameters(denominator=denominator))


def result_form(*fields, completed=False):
    definitions = fluorescence_fact_sources()
    properties = {field: deepcopy(definitions[SOURCES[field]]['report_schema']) for field in fields}
    if completed:
        properties['completed'] = {'type': 'boolean', 'x-source': 'execution_completed'}
    return validate_closed_schema(dict(type='object', properties=properties, required=list(properties),
        additionalProperties=False))


def supplied_job(store, software, *, operation, parser):
    raw = ('signal α\n' + ''.join(str(value) + '\n' for value in VALUES)).encode() if parser == 'csv' else (
        json.dumps(dict(schema='fluorescence_event_table_v1', columns=['signal α'], rows=[[v] for v in VALUES]),
            ensure_ascii=False, allow_nan=False).encode())
    ref = store.artifact(raw, 'text/csv' if parser == 'csv' else 'application/json')
    file = identity(raw, format='csv' if parser == 'csv' else 'json')
    assert file['artifact_ref'] == ref
    path = store.path / 'artifacts' / file['sha256'][:2] / file['sha256']
    inputs, populations, gates = [], [], []
    for i in range(2):
        source, sample, domain, channel = (f'{name}-{i}' for name in ('source', 'sample', 'domain', 'channel'))
        preparation = dict(state='not_applied', method=None, parameters_file=None)
        inputs.append(dict(parser=parser, path=str(path),
            source=dict(key=source, file=deepcopy(file), dataset_position=0, format_profile=parser,
                extent='unavailable', native_event_count=None,
                metadata=[dict(name='fixture', value='synthetic supplied events α')]),
            sample=dict(key=sample, primary_domain_key=domain, label=f'CD4 α {i}', condition=f'supplied-condition-{i}',
                biological_replicate=None, technical_replicate=None, associations=[]),
            channels=[dict(key=channel, ordinal=0, native_name='signal α', label='supplied channel α',
                unit='arbitrary_instrument_units', analyte=None, measurement_origin='observed')],
            domain=dict(key=domain, sample_key=sample, source_key=source, parent_domain_key=None,
                state='available', scale_kind='as_supplied', compensation=deepcopy(preparation),
                transformation=deepcopy(preparation), correspondence=None, comparison_basis=None),
            format_spec=dict(encoding='utf-8', delimiter=',', quotechar='"', escapechar=None,
                doublequote=True, header=True, missing_tokens=['']) if parser == 'csv' else None))
        populations.append(dict(key=f'population-{i}', sample_key=sample, kind='all', event_ordinals=None))
        gates.append(dict(key=f'gate-{i}', sample_key=sample, parent=dict(kind='population', key=f'population-{i}'),
            kind='threshold', domain_key=domain, channel_key=channel,
            lower=dict(value=100, inclusive=True), upper=dict(value=250, inclusive=True)))
    return dict(version='native_fluorescence_job_v1', operation=operation, mode=MODE, inputs=inputs,
        support_inputs=[], definitions=dict(populations=populations, gates=gates, control_pairs=[], native_reports=[]),
        parameters=parameters(), software=deepcopy(software), output_prefix='output-α'), raw


def action(name):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': {}}, 'report_update': {}}


def commission(role, assignment, scope, form, *, objective):
    return {'selection': {'kind': 'episode_child', 'role': role, 'goal': objective, 'scope': scope,
        'purpose': 'Return exactly the requested supplied-event measurements and their declared qualifications.',
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


def rows(store, table):
    assert table in TABLES
    return sorted((dict(row) for row in store.db.execute('SELECT * FROM ' + table)), key=canonical)


def controller_factory(path, initial):
    def estimate(raw, settings, contexts):
        horizon = 1 if path[-1][0] == 'annotation' else 4
        return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1), settings,
            {'fixture': 'explicit_caller_scientific_estimator'})
    return YieldController(str(path), initial, 0, YieldParameters(100, 50),
        estimate_with_context=estimate if path[-1][0] in {'annotation', 'scientific_process'} else None)


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
    owner = flow.episode_bindings.for_role('results')
    original_estimator = owner.practical_estimator

    def fixture_estimator(context):
        estimator = original_estimator(context)
        if context.role == 'results' and context.path[-1][1] == 'child_2':
            # This one fixture commission asks for the deliberately damaged
            # original capture. Its caller chooses to yield after the result.
            # Completion is still independently false, never manufactured.
            def partial_base(history_, settings):
                return YieldEstimate(len(history_), NumericBand.exact(0 if history_ else 1), settings,
                    {'fixture': 'explicit_caller_partial_return_estimator'})
            estimator.base_estimate = partial_base
        return estimator

    owner.practical_estimator = fixture_estimator
    return flow, tools


async def run_root(flow, configuration):
    root = flow.build('annotation', 'root', configuration['goal'], configuration['scope'])
    record = await root.run_async(flow.context)
    await root.build_result(record)
    return root, record, json.loads(''.join(iter_json(record.as_record())))


def worker_runs(directory):
    runs = []
    for path in sorted((directory / 'run').rglob('worker-capture.json')):
        capture = json.loads(path.read_bytes())
        if capture.get('version') == 'fluorescence_worker_capture_v1':
            runs.append(dict(directory=str(path.parent / 'worker'), capture=capture,
                plan=json.loads((path.parent / 'worker-plan.json').read_bytes())))
    return runs


def workflow_case(directory, *, operation, parser, before_partial=None, before_saved=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    software = software_closure(directory / 'original-software')
    store = Store(directory / 'state')
    store.create_problem(raw_sequence='ACGTACGT', molecule='dna')
    scope = store.validate_scope()
    job, raw = supplied_job(store, software, operation=operation, parser=parser)
    workspace = directory / 'workspace'
    workspace.mkdir()
    request = requested_job_from_fluorescence(job, environment=fluorescence_environment(
        software, attempt_directory=str(workspace / 'selected-context')))
    practical = dict(version='practical_assignment_v1', assignment_id='selected-fluorescence571',
        resource_id='here', resource_kind='local', workspace=str(workspace), endpoint='usable_handoff',
        requested_job=request, progress_requirements=[dict(key='handoff', credit=7,
            predicate=dict(kind='requested_job_handoff'))], completion_keys=['handoff'],
        initial_context=dict(revision=0, cwd=str(workspace), environment={}), inventory_snapshot={},
        constraints=dict(allocation=deepcopy(POLICY)))
    file = job['inputs'][0]['source']['file']
    launch = dict(version='execution_launch_assignment_v1', requests={'here': practical},
        immutable_input_versions=[dict(reference=file['artifact_ref'], version=None, content_sha256=file['sha256'])],
        constraints=dict(allowed_resource_ids=['here'], allowed_kinds=['local'], allocation=deepcopy(POLICY)))
    resources = {'here': dict(kind='local', workspace=str(workspace), policy=deepcopy(POLICY),
        native_fluorescence=[dict(operation=alias, mode=MODE, parsers=['csv', 'table_snapshot'], software=deepcopy(software))
            for alias in OPERATIONS])}
    factory = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)
    preliminary = ToolRegistry(store, job_limits=deepcopy(POLICY))
    application = factory(store, run_id=RUN_ID, directory=directory / 'run', tool_registry=preliminary)
    binding = prepare_scientific_binding(run_directory=directory / 'run', source_directory=PUBLICATION,
        tool_catalog=preliminary.catalog(), child_roles=('scientific_process', 'launch', 'results'),
        resource_catalogs=application.resource_tool_catalogs)
    library = ScientificProcessLibrary(directory / 'run/scientific-process-library')
    assignment = dict(selection=dict(version='scientific_process_selection_v3',
        evidence_axis=library.reference('A101'), thought_pattern=library.reference('P01'),
        child_tool_info=[dict(name=operation, resources='local')]), evidence_refs=scope['subject_refs'],
        constraints=dict(no_external_acquisition=True, allocation=deepcopy(POLICY)),
        context=dict(supplied_sequence='ACGTACGT', molecule='dna', supplied_fluorescence_files=[file],
            candidate_annotation_required=False))
    configuration = dict(factory=factory.as_record(), scientific_binding=binding, goal=TASK, scope=scope,
        initial_refs=[file['artifact_ref']])
    write(directory / 'fixture-configuration.json', configuration)
    full_form = result_form('measurements', 'contexts', 'saved', 'failures', completed=True)
    parent_form = result_form('measurements', 'contexts')

    class Choices:
        def __init__(self):
            self.calls, self.turns, self.native_bytes = [], {}, {}
            self.plan = self.target = self.handoff = self.original_return = self.partial_return = None

        async def complete(self, episode_id, role, instructions, current, schema):
            self.calls.append(dict(episode_id=episode_id, role=role, context=deepcopy(current)))
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
                    HANDOFF_FORM, objective='Parse the exact selected supplied fluorescence events on the configured local resource.')
            elif current.get('execution_assignment', {}).get('version') == RESULTS_VERSION:
                assert turn == 1
                answer = action('execution.results.collect')
            elif 'scientific_process' not in current:
                assert turn == 1
                answer = commission('scientific_process', assignment, scope, parent_form, objective=TASK)
            elif turn == 1:
                answer = commission('launch', launch, scope, HANDOFF_FORM,
                    objective='Execute the selected fluorescence parser with original inputs, metadata, gate and allocation.')
            elif turn == 2:
                reader = PracticalReceiptInformation(store, RUN_ID)
                self.handoff, = [ref for ref in current['child_reports'][-1]['references']
                    if reader.read(ref, scope)['receipt']['tool_name'] == 'practical.job.start']
                self.target = owner.job_progress_provider.targets.read_target(self.handoff, scope)
                outcome = await asyncio.to_thread(native_lifecycle.wait_job,
                    native_lifecycle.NativeJobHandle(Path(self.target['execution_id'])))
                assert outcome.returncode == 0, outcome
                self.plan = local_fluorescence_plan(self.target['assignment'], self.target['execution_id'])
                for spec in self.plan['outputs']:
                    path = Path(self.plan['attempt_directory']) / spec['relative_path']
                    if path.is_file():
                        self.native_bytes[spec['role']] = path.read_bytes()
                write(directory / 'original-native-plan.json', self.plan)
                write(directory / 'native-lifecycle.json', dict(returncode=outcome.returncode, metadata=outcome.metadata))
                answer = commission('results', dict(version=RESULTS_VERSION, handoff_ref=self.handoff, selector=selector()),
                    scope, full_form, objective='Return the requested gate counts, fractions, intensities, definitions and saved sheet.')
            elif turn == 3:
                self.original_return = deepcopy(current['child_reports'][-1])
                assert self.original_return['completed'], self.original_return
                if before_partial:
                    before_partial(SimpleNamespace(store=store, owner=owner, flow=flow, directory=directory,
                        workspace=workspace, software=software, provider=self, original_return=self.original_return,
                        science_context=owner.native_fluorescence_returns.context(episode_id)))
                answer = commission('results', dict(version=RESULTS_VERSION, handoff_ref=self.handoff, selector=selector()),
                    scope, full_form, objective='Collect the same original handle after controlled removal of one closed-writer input copy; retain independent measurements.')
            elif turn == 4:
                self.partial_return = deepcopy(current['child_reports'][-1])
                assert not self.partial_return['completed'] and self.partial_return['saved'], self.partial_return
                if before_saved:
                    before_saved(SimpleNamespace(store=store, owner=owner, flow=flow, directory=directory,
                        workspace=workspace, software=software, provider=self, partial_return=self.partial_return,
                        science_context=owner.native_fluorescence_returns.context(episode_id)))
                prior = store.db.execute('SELECT * FROM runtime_report_attempts '
                    'WHERE run_id=? AND parent_episode_id=? AND decision_index=1', (RUN_ID, episode_id)).fetchone()
                assert prior is not None
                self.original_delivery = dict(prior)
                assert prior['failure'] is None and json.loads(prior['form']) == self.original_return
                self.reports_before_redelivery = deepcopy(current['child_reports'])
                self.state_before_redelivery = {table: rows(store, table)
                    for table in ('runtime_actions', 'runtime_observations', 'runtime_forms')}
                answer = {'selection': {'kind': 'redeliver_report', 'delivery_ref': prior['delivery_ref'],
                    'purpose': 'Read the exact original requested numerical facts from the closed return.',
                    'schema_json': json.dumps(full_form)}, 'report_update': {}}
            else:
                assert turn == 5
                # Redelivery replaces the original child's admitted report in
                # place; it neither appends a child nor creates an observation.
                assert current['child_reports'] == self.reports_before_redelivery
                assert current['child_reports'].count(self.original_return) == 1
                attempts = [dict(row) for row in store.db.execute(
                    'SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? '
                    'AND delivery_ref=? ORDER BY decision_index',
                    (RUN_ID, episode_id, self.original_delivery['delivery_ref']))]
                assert [row['decision_index'] for row in attempts] == [1, 3]
                assert attempts[0] == self.original_delivery
                assert attempts[1]['failure'] is None
                assert attempts[1]['child_episode_id'] == self.original_delivery['child_episode_id']
                assert attempts[1]['form'] == self.original_delivery['form']
                for table, before in self.state_before_redelivery.items():
                    assert rows(store, table) == before
                saved, = self.partial_return['saved']
                answer = commission('results', dict(version=RESULTS_VERSION, handoff_ref=self.handoff,
                    selector=selector(saved=saved)), scope, full_form,
                    objective='Recalculate the received partial sheet with the evaluable denominator and return the selected page; do not reacquire original events.')
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
        contexts = {row['episode_id']: owner.native_fluorescence_returns.context(row['episode_id']) for row in records}
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
            full_form=full_form, scope=scope, workspace=workspace, job=job, raw=raw, software=software)
        write(directory / 'CASE.json', dict(scope='scripted choices, supplied synthetic events, actual local native execution and Workflow',
            operation=operation, parser=parser, returned=returned, forwarded=forwarded,
            histories={role: [row['controller_state'] for row in group] for role, group in by_role.items()}, archive=archive))
        return case
    except BaseException:
        store.close()
        raise
