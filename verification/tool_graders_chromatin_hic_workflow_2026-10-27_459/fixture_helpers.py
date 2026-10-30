"""015 HIC Workflow fixture: synthetic caller inputs, actual selected work.

Only JSON/typed-form/archive utilities are shared with451. HIC inputs,
populations, normalization, source identities and native outcomes belong here.
Scripted model choices are test fixtures, never production decision policy.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator
from method_loop.archive import iter_json
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.chromatin_interaction_return_views import PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE
from gene_annotation_episode.native_chromatin_interaction_contracts import POLICY, requested_job_from_chromatin, _dependency_roots
from gene_annotation_episode.native_chromatin_interaction_local import local_chromatin_interaction_plan
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

_generic = import_module('verification.tool_graders_chromatin_workflow_2026-10-27_451.fixture_helpers')
write, action, commission, provider_value = (_generic.write, _generic.action, _generic.commission, _generic.provider_value)
walk, history, result_form = _generic.walk, _generic.history, _generic.result_form
identity, artifact_path, rows, worker_runs = _generic.identity, _generic.artifact_path, _generic.rows, _generic.worker_runs
TABLES, HANDOFF_FORM, FIELDS = _generic.TABLES, deepcopy(_generic.HANDOFF_FORM), list(_generic.FIELDS)

ROOT = Path(__file__).resolve().parents[2]
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
WORKED = {r['example_key']: r['record'] for r in json.loads((ROOT /
    'verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/WORKED_RECORDS.json').read_text())['records']}
RUN_ID = 'chromatin-hic-workflow459'
TASK = 'Measure the supplied synthetic HIC contacts for E-P and E-Q in the declared populations and retain numerical qualifications.'
FIXTURES = ROOT / 'verification/tool_graders_chromatin_hic_native_2026-10-27_454'
HIC = {
    'weighted': {'path': 'native009/valid/output.hic', 'sha256': 'e77c601db18650754ab3c854db947a6031e53cb04002996d41ff86e5a281e765',
        'size_bytes': 429, 'genome_id': 'synthetic_four_bin'},
    'empty': {'path': 'native010/present_zero_block/output.hic', 'sha256': '5bc282e9dbb3aacbd77c4f815ee67a24e72c526f56f33e68095e635e59ad0be6',
        'size_bytes': 220, 'genome_id': 'synthetic_format_fixture'},
}
BED = b'chrA\t0\t2\tE\nchrA\t20\t23\tP\nchrA\t30\t33\tQ\n'


def source(store, raw, label):
    artifact = store.artifact(raw)
    return store.put('source', {'provider': 'fixture.hic459.' + label, 'accession': None, 'uri': None,
        'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'version': None,
        'retrieved_at': None}, origin='caller')


def selector(normalization, *, saved=None, partial=False):
    value = deepcopy(WORKED['raw.selector'])
    value['parameters']['normalization'] = deepcopy(normalization)
    value['population_keys'] = ['p0', 'p1'] if partial else ['p1']
    value['projection']['selection']['page']['limit'] = 4
    if saved is not None:
        value.update(mode='saved_sheet_recalculation', saved_sheet_bundle=deepcopy(saved))
        value['parameters']['contact']['fold_threshold'] = 1
    return value


def controller_factory(*, partial, recalculate):
    def controller(path, initial):
        def estimate(raw, parameters, contexts):
            horizon = 1 if path[-1][0] == 'annotation' else 3 if recalculate else 2
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
        controller_factory=controller_factory(partial=configuration['partial'], recalculate=configuration['recalculate']),
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


def workflow_case(directory, software, *, partial=False, empty=False, before_saved=None):
    assert not (partial and empty)
    recalculate = not (partial or empty)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    store = Store(directory / 'state')
    store.create_problem(raw_sequence='ACGTACGT', molecule='dna')
    scope = store.validate_scope()
    fixture = HIC['empty' if empty else 'weighted']
    contact_bytes = (FIXTURES / fixture['path']).read_bytes()
    assert hashlib.sha256(contact_bytes).hexdigest() == fixture['sha256'] and len(contact_bytes) == fixture['size_bytes']
    write(directory / 'HIC_INPUT.json', {**fixture, 'path': str(FIXTURES / fixture['path']),
        'origin': 'synthetic retained454 native fixture', 'biological_observation': False})
    request = deepcopy(WORKED['raw.request'])
    request['contact'].update(format='hic_binary_v9', group_path=None)
    request['populations'] = [dict(request['populations'][0], population_key=key) for key in ('p0', 'p1')]
    if partial:
        request['populations'][1]['chromosome'] = 'chrNotPresent'
    if not empty:
        request['normalization'] = {'kind': 'precomputed_weighted', 'weight_column': 'SYNTHETIC_DIVISIVE', 'convention': 'divisive'}
    for reference in (request['elements']['reference'], request['supplied_metadata']['reference']):
        reference['assembly_label'] = fixture['genome_id']
    reference = source(store, canonical(request['supplied_metadata']['reference']).encode(), 'reference')
    metadata = source(store, canonical({'samples': request['supplied_metadata']['samples'],
        'contact_sample_links': request['supplied_metadata']['contact_sample_links']}).encode(), 'metadata')
    request['elements']['reference']['source_ref'] = reference['id']
    request['supplied_metadata']['reference']['source_ref'] = reference['id']
    for name in ('samples', 'contact_sample_links'):
        for row in request['supplied_metadata'][name]:
            row['source_ref'] = metadata['id']
    initial_refs = [reference['id'], reference['artifact_ref'], metadata['id'], metadata['artifact_ref']]
    bindings = []
    for key, raw, format in [('contact', contact_bytes, 'hic_binary_v9'), ('elements', BED, 'bed_outer_span_v1')]:
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
    practical = {'version': 'practical_assignment_v1', 'assignment_id': 'selected-hic459',
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
            'analysis_modes': request['analysis_modes'], 'supported_formats': ['hic_binary_v9'], 'software': deepcopy(software)}]}}
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
    configuration = {'factory': factory.as_record(), 'scientific_binding': binding, 'goal': TASK,
        'scope': scope, 'initial_refs': initial_refs, 'partial': partial, 'empty': empty, 'recalculate': recalculate}
    write(directory / 'fixture-configuration.json', configuration)
    full_form = result_form('chromatin', 'saved', 'failures', completed=True)
    parent_form = result_form('chromatin')

    class Choices:
        def __init__(self):
            self.calls, self.turns, self.native_bytes = [], {}, {}
            self.initial_refs = tuple(initial_refs)
            self.plan = self.target = self.handoff = self.original_return = self.native_outcome = None

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
                    objective='Execute the exact supplied HIC request on the configured local resource.')
            elif current.get('execution_assignment', {}).get('version') == RESULTS_VERSION:
                assert turn == 1 or partial and turn == 2
                answer = action('execution.results.collect' if turn == 1 else 'execution.results.status')
            elif 'scientific_process' not in current:
                assert turn == 1
                answer = commission('scientific_process', scientific_assignment, scope, parent_form, objective=TASK)
            elif turn == 1:
                answer = commission('launch', launch, scope, HANDOFF_FORM,
                    objective='Execute the supplied HIC request for both declared populations with the original resource allocation.')
            elif turn == 2:
                reader = PracticalReceiptInformation(store, RUN_ID)
                self.handoff, = [ref for ref in current['child_reports'][-1]['references']
                    if reader.read(ref, scope)['receipt']['tool_name'] == 'practical.job.start']
                self.target = owner.job_progress_provider.targets.read_target(self.handoff, scope)
                outcome = await asyncio.to_thread(native_lifecycle.wait_job,
                    native_lifecycle.NativeJobHandle(Path(self.target['execution_id'])))
                self.native_outcome = {'returncode': outcome.returncode, 'metadata': outcome.metadata}
                write(directory / 'native-lifecycle.json', self.native_outcome)
                assert outcome.returncode == (1 if partial else 0), self.native_outcome
                self.plan = local_chromatin_interaction_plan(self.target['assignment'], self.target['execution_id'])
                for spec in self.plan['outputs']:
                    path = Path(self.plan['attempt_directory']) / spec['relative_path']
                    if path.is_file():
                        self.native_bytes[spec['file_key']] = path.read_bytes()
                write(directory / 'original-native-plan.json', self.plan)
                answer = commission('results', {'version': RESULTS_VERSION, 'handoff_ref': self.handoff,
                    'selector': selector(request['normalization'], partial=partial)}, scope, full_form,
                    objective='Return the selected contact measurements, complete received sheet and table identities, and located failures.')
            else:
                assert recalculate and turn == 3
                self.original_return = deepcopy(current['child_reports'][-1])
                assert self.original_return['completed'], self.original_return
                bundle, = self.original_return['saved']
                if before_saved:
                    before_saved(SimpleNamespace(store=store, owner=owner, flow=flow, directory=directory,
                        workspace=workspace, bundle=bundle, original_return=self.original_return,
                        provider=self, science_context=owner.native_chromatin_interaction_returns.context(episode_id)))
                answer = commission('results', {'version': RESULTS_VERSION, 'handoff_ref': self.handoff,
                    'selector': selector(request['normalization'], saved=bundle)}, scope, full_form,
                    objective='Recalculate the received saved sheet and tables at fold threshold1; preserve all original contact measurements.')
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
            full_form=full_form, scope=scope, workspace=workspace, job=job, partial=partial, empty=empty)
        write(directory / 'CASE.json', {'scope': 'scripted choices, retained synthetic HICv9 bytes, actual Workflow and local execution',
            'partial': partial, 'empty': empty, 'native_returncode': provider.native_outcome['returncode'],
            'returned': returned, 'forwarded': forwarded,
            'histories': {role: [r['controller_state'] for r in group] for role, group in by_role.items()}, 'archive': archive})
        return case
    except BaseException:
        store.close()
        raise
