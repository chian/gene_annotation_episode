"""Prepared fluorescence through the actual Workflow and bounded native owners.

Only the selected choices, supplied synthetic FCS/recipe/report bytes and caller
continuation fixture are scripted. Production custody, native libraries, writer
closure, result calculations, delivery and practical completion remain active.
Import this module only inside the coordinator's existing bounded529 runner.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from fluorescence_flowio_test_support import require_bounded_runtime

require_bounded_runtime()

from jsonschema import Draft202012Validator

from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_episodes import RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.native_fluorescence_contracts import (
    MODE, OPERATIONS, POLICY, fluorescence_environment, requested_job_from_fluorescence,
)
from gene_annotation_episode.native_fluorescence_local import local_fluorescence_plan
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

import fluorescence_workflow_support as F
from native_fluorescence_prepared_test_support import (
    COMPENSATE, FACS, SCALE, actual_software, prepared_job,
)


TASK = (
    'Calculate the requested pass-all population, fractions and raw, scaled and compensated '
    'fluorescence intensities from the supplied synthetic FCS events. Execute the explicitly '
    'selected FlowIO scaling followed by FlowUtils compensation, preserving the original two '
    'event identities, separate measurement domains, Time units and floating-point residues. '
    'Compare the supplied FACS-format percentage using its explicit population association; '
    'the supplied report does not establish upstream laboratory or legacy-wrapper execution. '
    'Return only the requested numerical cells and definitions, preserving partial work and '
    'missing values without substituting another measurement domain.'
)
INPUT_ROWS = ((220, 120, 10), (40, 200, 20))
TARGET_SEQUENCE = 'ACGTACGT'
INTENSITIES = (
    ('domain-0', 'raw.c0'), ('scaled', 'scaled.c0'),
    ('compensated', 'compensated.c0'), ('scaled', 'scaled.c2'),
)
CONTEXT_FIELDS = ['samples', 'channels', 'domains', 'populations', 'gates']


def parameters(*, denominator='parent'):
    return dict(fraction_requests=[dict(gate_key='gate-0', denominator=denominator)],
        intensity_requests=[dict(gate_key='gate-0', domain_key=domain, channel_key=channel)
            for domain, channel in INTENSITIES], control_requests=[],
        native_comparison_requests=['native.report.percent'])


def selector(*, saved=None):
    denominator = 'parent' if saved is None else 'evaluable'
    requests = [F.cell_request('population', metric, gate_key='gate-0')
        for metric in ('retained_event_count', 'selected_event_count')]
    requests.extend(F.cell_request('fraction', metric, gate_key='gate-0', denominator=denominator)
        for metric in ('selected_fraction', 'selected_percent'))
    requests.extend(F.cell_request('intensity', 'selected_intensity_mean', gate_key='gate-0',
        domain_key=domain, channel_key=channel) for domain, channel in INTENSITIES)
    for metric in ('native_value', 'native_minus_calculated'):
        row = F.cell_request('native_comparison', metric, gate_key=None)
        row['native_report_key'] = 'native.report.percent'
        requests.append(row)
    return dict(version='fluorescence_result_selector_v1',
        mode='native_result' if saved is None else 'saved_sheet_recalculation',
        selection=dict(requests=requests, offset=0 if saved is None else 2,
            limit=10 if saved is None else 4), context_fields=list(CONTEXT_FIELDS),
        saved_sheet_file=deepcopy(saved), parameters=None if saved is None else parameters(denominator=denominator))


def artifact_path(store, file):
    return store.path / 'artifacts' / file['sha256'][:2] / file['sha256']


def selected_inputs(job):
    return [(row['source']['file'], row['path']) for row in job['inputs']] + [
        (row['file'], row['path']) for row in (*job['support_inputs'], *job['report_inputs'])]


def assert_initial_input_custody(baseline, initial_refs, target_record_refs, supplied):
    # Derive this one artifact from the declared target bytes, never from the
    # actual receipt set or from all artifacts retained by the Workflow.
    target_artifact_ref = 'artifact_' + hashlib.sha256(TARGET_SEQUENCE.encode('utf-8')).hexdigest()
    assert set(initial_refs) <= baseline
    assert target_artifact_ref in baseline
    assert baseline <= (set(target_record_refs) | {target_artifact_ref}
        | {file['artifact_ref'] for file in supplied})
    return target_artifact_ref


def register_supplied(store, directory, software, *, operation):
    job = prepared_job(directory, operation=operation, rows=INPUT_ROWS)
    job['software'] = deepcopy(software)
    job['parameters'] = parameters()
    files, seen = [], set()
    for row in (*job['inputs'], *job['support_inputs'], *job['report_inputs']):
        file = row['source']['file'] if 'source' in row else row['file']
        raw = Path(row['path']).read_bytes()
        reference = store.artifact(raw)
        assert reference == file['artifact_ref']
        row['path'] = str(artifact_path(store, file))
        assert Path(row['path']).read_bytes() == raw
        if reference not in seen:
            files.append(deepcopy(file))
            seen.add(reference)
    return job, files


def workflow_case(directory, *, operation, before_partial, before_saved):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    software = actual_software(directory / 'original-software')
    store = Store(directory / 'state')
    store.create_problem(raw_sequence=TARGET_SEQUENCE, molecule='dna')
    scope = store.validate_scope()
    target_record_refs = [row['id'] for row in store.db.execute('SELECT id FROM inputs UNION SELECT id FROM records')]
    job, supplied = register_supplied(store, directory / 'supplied', software, operation=operation)
    workspace = directory / 'workspace'
    workspace.mkdir()
    request = requested_job_from_fluorescence(job, environment=fluorescence_environment(
        software, attempt_directory=str(workspace / 'selected-context')))
    practical = dict(version='practical_assignment_v1', assignment_id='selected-prepared-fluorescence595',
        resource_id='here', resource_kind='local', workspace=str(workspace), endpoint='usable_handoff',
        requested_job=request, progress_requirements=[dict(key='handoff', credit=7,
            predicate=dict(kind='requested_job_handoff'))], completion_keys=['handoff'],
        initial_context=dict(revision=0, cwd=str(workspace), environment={}), inventory_snapshot={},
        constraints=dict(allocation=deepcopy(POLICY)))
    launch = dict(version='execution_launch_assignment_v1', requests={'here': practical},
        immutable_input_versions=[dict(reference=file['artifact_ref'], version=None,
            content_sha256=file['sha256']) for file in supplied],
        constraints=dict(allowed_resource_ids=['here'], allowed_kinds=['local'], allocation=deepcopy(POLICY)))
    resources = {'here': dict(kind='local', workspace=str(workspace), policy=deepcopy(POLICY),
        native_fluorescence=[dict(version='native_fluorescence_binding_v2', operation=alias, mode=MODE,
            parsers=['fcs_encoded'], preparation_methods=[SCALE, COMPENSATE], report_profiles=[FACS],
            software=deepcopy(software)) for alias in OPERATIONS])}
    factory = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)
    preliminary = ToolRegistry(store, job_limits=deepcopy(POLICY))
    application = factory(store, run_id=F.RUN_ID, directory=directory / 'run', tool_registry=preliminary)
    binding = prepare_scientific_binding(run_directory=directory / 'run', source_directory=F.PUBLICATION,
        tool_catalog=preliminary.catalog(), child_roles=('scientific_process', 'launch', 'results'),
        resource_catalogs=application.resource_tool_catalogs)
    library = ScientificProcessLibrary(directory / 'run/scientific-process-library')
    assignment = dict(selection=dict(version='scientific_process_selection_v3',
        evidence_axis=library.reference('A101'), thought_pattern=library.reference('P01'),
        child_tool_info=[dict(name=operation, resources='local')]), evidence_refs=scope['subject_refs'],
        constraints=dict(no_external_acquisition=True, allocation=deepcopy(POLICY)),
        context=dict(supplied_sequence=TARGET_SEQUENCE, molecule='dna', supplied_fluorescence_files=supplied,
            candidate_annotation_required=False))
    configuration = dict(factory=factory.as_record(), scientific_binding=binding, goal=TASK, scope=scope,
        initial_refs=list(dict.fromkeys([*scope['subject_refs'], *[file['artifact_ref'] for file in supplied]])))
    F.write(directory / 'fixture-configuration.json', configuration)
    full_form = F.result_form('measurements', 'contexts', 'saved', 'failures', completed=True)
    parent_form = F.result_form('measurements', 'contexts')

    class Choices:
        def __init__(self):
            self.calls, self.turns, self.native_bytes = [], {}, {}
            self.plan = self.target = self.handoff = self.original_return = self.partial_return = None

        async def complete(self, episode_id, role, instructions, current, schema):
            self.calls.append(dict(episode_id=episode_id, role=role, context=deepcopy(current)))
            F.write(directory / f'decision-{len(self.calls) - 1}.json', self.calls[-1])
            assert not current.get('feedback'), current.get('feedback')
            self.turns[episode_id] = self.turns.get(episode_id, 0) + 1
            turn = self.turns[episode_id]
            if 'practical_assignment' in current:
                assert turn == 1 and current['practical_assignment']['constraints']['allocation'] == POLICY
                answer = F.action('practical.job.start')
            elif current.get('execution_assignment', {}).get('version') == 'execution_launch_assignment_v1':
                assert turn == 1
                answer = F.commission('launch_local', current['execution_assignment']['requests']['here'], scope,
                    F.HANDOFF_FORM, objective='Execute the selected FCS scaling, compensation and supplied-report parsing on the bound local resource.')
            elif current.get('execution_assignment', {}).get('version') == RESULTS_VERSION:
                assert turn == 1
                answer = F.action('execution.results.collect')
            elif 'scientific_process' not in current:
                assert turn == 1
                answer = F.commission('scientific_process', assignment, scope, parent_form, objective=TASK)
            elif turn == 1:
                answer = F.commission('launch', launch, scope, F.HANDOFF_FORM,
                    objective='Execute the exact supplied FCS inputs, selected preparation recipes and report association with the original allocation.')
            elif turn == 2:
                reader = PracticalReceiptInformation(store, F.RUN_ID)
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
                F.write(directory / 'original-native-plan.json', self.plan)
                F.write(directory / 'native-lifecycle.json', dict(returncode=outcome.returncode, metadata=outcome.metadata))
                answer = F.commission('results', dict(version=RESULTS_VERSION, handoff_ref=self.handoff, selector=selector()),
                    scope, full_form, objective='Return the requested population, fraction, raw/scaled/compensated intensity and native-comparison cells with the saved common sheet.')
            elif turn == 3:
                self.original_return = deepcopy(current['child_reports'][-1])
                assert self.original_return['completed'], self.original_return
                before_partial(SimpleNamespace(store=store, owner=owner, directory=directory, software=software,
                    job=job, provider=self, original_return=self.original_return,
                    science_context=owner.native_fluorescence_returns.context(episode_id)))
                answer = F.commission('results', dict(version=RESULTS_VERSION, handoff_ref=self.handoff, selector=selector()),
                    scope, full_form, objective='Recollect the same closed producer after explicit compensated-data removal; retain the independent original, scaled and supplied-report measurements.')
            else:
                assert turn == 4
                self.partial_return = deepcopy(current['child_reports'][-1])
                assert not self.partial_return['completed'] and self.partial_return['saved'], self.partial_return
                before_saved(SimpleNamespace(store=store, owner=owner, directory=directory, software=software,
                    job=job, provider=self, partial_return=self.partial_return,
                    science_context=owner.native_fluorescence_returns.context(episode_id)))
                saved, = self.partial_return['saved']
                answer = F.commission('results', dict(version=RESULTS_VERSION, handoff_ref=self.handoff,
                    selector=selector(saved=saved)), scope, full_form,
                    objective='Recalculate only the received partial sheet with the explicit evaluable denominator and requested page; acquire no inputs and execute no producer or preparation.')
            answer = F.provider_value(plain(answer), plain(schema))
            Draft202012Validator(plain(schema)).validate(answer)
            return answer

        async def release(self, episode_id):
            pass

    provider = Choices()
    # Reuse the existing caller fixture estimator and actual Workflow assembly.
    # Its RUN_ID is local to this separate Store; no v1 fixture state is shared.
    flow, tools = F.assemble(store, directory, provider, configuration)
    owner = flow.episode_bindings.for_role('results')
    try:
        root, record, archive = asyncio.run(F.run_root(flow, configuration))
        records = list(F.walk(archive))
        contexts = {row['episode_id']: owner.native_fluorescence_returns.context(row['episode_id']) for row in records}
        by_role = {}
        for row in records:
            by_role.setdefault(contexts[row['episode_id']].role, []).append(row)
        result_contexts = [contexts[row['episode_id']] for row in by_role['results']]
        returned = [json.loads(flow.journal.row('runtime_forms', context.episode_id)['form']) for context in result_contexts]
        outcomes = [json.loads(flow.journal.row('runtime_actions', context.episode_id, 0)['result']) for context in result_contexts]
        scientific_context, = [contexts[row['episode_id']] for row in by_role['scientific_process']]
        forwarded = json.loads(flow.journal.row('runtime_forms', scientific_context.episode_id)['form'])
        case = SimpleNamespace(store=store, directory=directory, flow=flow, tools=tools, owner=owner,
            provider=provider, configuration=configuration, root=root, record=record, archive=archive,
            records=records, contexts=contexts, by_role=by_role, result_contexts=result_contexts,
            returned=returned, outcomes=outcomes, scientific_context=scientific_context,
            root_context=contexts[record.episode_id], forwarded=forwarded, parent_form=parent_form,
            full_form=full_form, scope=scope, workspace=workspace, job=job, software=software,
            supplied=supplied, launch=launch, target_record_refs=target_record_refs)
        F.write(directory / 'CASE.json', dict(scope='scripted choices; synthetic FCS/recipes/source-format report; actual native libraries, lifecycle and Workflow',
            operation=operation, returned=returned, forwarded=forwarded,
            histories={role: [row['controller_state'] for row in group] for role, group in by_role.items()}, archive=archive))
        return case
    except BaseException:
        store.close()
        raise
