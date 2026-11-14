"""Synthetic producer reports; actual original custody, Workflow and comparison.

The numeric values and recognized software declarations are fixtures. No RNA
library is imported and no producer driver is started. Reservations, source
receipts, selected result actions, bounded workers and typed returns are real.
"""
import asyncio
from copy import deepcopy
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

from method_loop.archive import iter_json
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import plain, validate_closed_schema
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest, validate_target
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_rna_structure_contracts import (POLICY, INPUT_NAMES,
    compile_rna_structure_job, requested_job_from_rna_structure, realized_environment,
    validate_rna_structure_bundle)
from gene_annotation_episode.native_rna_structure_local import prepare_local_rna_structure, local_rna_structure_plan
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.practical_execution_records import assess_validations
from gene_annotation_episode.practical_execution_state import _immutable
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.rna_structure_comparison_views import PROJECTION_SOURCE, rna_comparison_fact_sources
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_native_rna_structure_acquisition import F
from test_native_rna_structure_results_integration import (
    child, selected, provider_value, walk, result_form, ROOT, PUBLICATION)

b = importlib.import_module('verification.tool_graders_rna_comparison_calculations_2026-10-26_367.fixture_helpers')
RUN_ID = 'rna-comparison-shared372'


def encoded(value):
    return (canonical(value) + '\n').encode()


def comparison_form(*, completed=True):
    props = {'comparison': rna_comparison_fact_sources()[PROJECTION_SOURCE]['report_schema']}
    if completed:
        props['completed'] = {'type': 'boolean', 'x-source': 'execution_completed'}
    return validate_closed_schema({'type': 'object', 'additionalProperties': False,
        'properties': props, 'required': list(props)})


def seed_report(store, directory, scope, sheet, *, failure=False):
    """Retain synthetic original bytes with a real scoped practical handoff."""
    directory.mkdir(parents=True)
    request = deepcopy(sheet['original_input'])
    source_input = directory / 'input.json'
    source_input.write_bytes(encoded(request))
    input_ref = store.artifact(source_input.read_bytes(), 'application/json')
    software = b.software()
    job = {'version': 'native_rna_structure_job_v1', 'program': 'rna_structure_python',
        'operation': sheet['operation'], 'mode': sheet['mode'], 'record_key': sheet['record_key'],
        'software': software, 'model': deepcopy(sheet['model']['selected']),
        'operands': [{'role': 'input', 'path': str(source_input), 'format': 'rna_input_json_v1',
            'sha256': F.sha(source_input.read_bytes()), 'size_bytes': source_input.stat().st_size,
            'artifact_ref': input_ref}],
        'outputs': [{'role': role, 'format': format_, 'relative_path': name} for role, format_, name in (
            ('native_result', 'rna_native_record_json_v1', 'native-result.json'),
            ('stdout', 'text', 'stdout.txt'), ('stderr', 'text', 'stderr.txt'),
            ('model', 'vienna_model_json_v1', 'model.json'),
            ('effective_parameters', 'viennarna_parameter_file', 'synthetic.par'))],
        'environment': {'PYTHONPATH': str(ROOT)}, 'grading_parameters': deepcopy(F.PARAMETERS)}
    workspace = directory / 'workspace'
    workspace.mkdir()
    assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'synthetic-' + sheet['record_key'],
        'resource_kind': 'local', 'resource_id': 'here', 'workspace': str(workspace),
        'requested_job': requested_job_from_rna_structure(job), 'endpoint': 'usable_handoff',
        'progress_requirements': [{'key': 'handoff', 'credit': 1, 'predicate': {'kind': 'requested_job_handoff'}}],
        'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {'allocation': deepcopy(POLICY)}}
    state = SimpleNamespace(store=store, run_id=RUN_ID, scope=scope,
        journal=Journal(store, RUN_ID), receipts=EpisodeReceipts(store, RUN_ID))
    producer = F.Fixture.context(state, (('launch_local', 'synthetic_' + sheet['record_key']),), assignment, None)
    key = f'{RUN_ID}:{producer.episode_id}:0'
    root = workspace / '.episode-operations' / digest({'run': RUN_ID, 'episode': producer.episode_id}) / digest(key)
    handle = prepare_local_rna_structure(SimpleNamespace(run_id=RUN_ID, episode_id=producer.episode_id,
        assignment=assignment), key, root=root, policy=LocalJobPolicy(**POLICY))
    plan = local_rna_structure_plan(assignment, str(handle.path))
    attempt = Path(plan['attempt_directory'])
    attempt.mkdir()
    native = F.CORE.native_record(request, energy=sheet['native_evaluation']['value'])
    native.update(model=deepcopy(sheet['model']), native_evaluation=deepcopy(sheet['native_evaluation']))
    parameter_bytes = b'Explicitly synthetic never-loaded model parameters.\n'
    native['model']['parameter_artifact'].update(sha256=F.sha(parameter_bytes), size_bytes=len(parameter_bytes))
    contents = {'input': encoded(request), 'native_result': encoded(native), 'model': encoded(native['model']),
        'effective_parameters': parameter_bytes, 'stdout': b'Synthetic original producer report; no native run.\n', 'stderr': b''}
    declarations = [{'kind': 'input', 'role': 'input', 'format': 'rna_input_json_v1', 'relative_path': INPUT_NAMES['input']}]
    declarations.extend({'kind': 'output', **row} for row in job['outputs'])
    files = []
    for row in declarations:
        raw = contents[row['role']]
        (attempt / row['relative_path']).write_bytes(raw)
        files.append({**row, 'state': 'present', 'sha256': F.sha(raw), 'size_bytes': len(raw)})
    compiled = compile_rna_structure_job(job, input_paths={'input': str(attempt / 'input.json')}, output_directory=str(attempt))
    bundle = {'version': 'native_rna_structure_bundle_v1', 'identity': plan['identity'],
        'requested_job': plan['requested_job'], **{name: job[name] for name in ('program', 'operation', 'mode', 'record_key', 'software')},
        'realized_argv': compiled['argv'], 'environment': realized_environment(job, str(attempt)),
        'files': files, 'returncode': 0, 'native_status': 'complete', 'failures': [],
        'started_at': '2026-10-26T00:00:00+00:00', 'finished_at': '2026-10-26T00:00:01+00:00', 'sealed': True}
    validate_rna_structure_bundle(bundle, plan=plan)
    _immutable(attempt / 'bundle.json', bundle)
    status_key = f'{RUN_ID}:{producer.episode_id}:1'
    action = {'kind': 'tool', 'tool': 'practical.job.status', 'arguments': {}}
    state.journal.save('runtime_actions', {'episode_id': producer.episode_id, 'decision_index': 1,
        'action': canonical(action), 'result': None, 'credit': None})
    outcome = {'facts': {'requested_job': {'argv': assignment['requested_job']['argv'],
        'environment': assignment['requested_job']['environment'], 'returncode': 0,
        'execution_id': str(handle.path), 'requested_job_sha256': digest(assignment['requested_job']),
        'resource_kind': 'local', 'status': 'completed', 'output_paths': [],
        'handoff': {'execution_id': str(handle.path), 'monitor_operation': 'practical.job.status',
            'results_operation': 'practical.job.collect'}}}, 'native_outcome': {
                'fixture': 'synthetic_terminal_report', 'attempt_operation_key': key, 'attempt_id': digest(key)}}
    receipt = {'version': 'practical_action_receipt_v1', 'run_id': RUN_ID, 'episode_id': producer.episode_id,
        'assignment_sha256': digest(assignment), 'operation_key': status_key, 'tool_name': action['tool'], 'arguments': {},
        'context_before': assignment['initial_context'], 'context_after': assignment['initial_context'], 'outcome': outcome,
        'validations': assess_validations(assignment, outcome, assignment['initial_context'],
            checked_at='2026-10-26T00:00:01+00:00', tool_name=action['tool']),
        'started_at': '2026-10-26T00:00:01+00:00', 'finished_at': '2026-10-26T00:00:01+00:00'}
    handoff = PracticalReceiptInformation(store, RUN_ID).publish(producer, receipt)
    state.journal.save('runtime_actions', {'episode_id': producer.episode_id, 'decision_index': 1,
        'action': canonical(action), 'result': canonical({'status': 'completed', 'record_refs': [handoff], 'result': receipt}), 'credit': 0})
    if failure:
        (attempt / 'bundle.json').unlink()  # Real acquisition failure on synthetic retained input, no fabricated native failure.
    return SimpleNamespace(handoff=handoff, job=job, assignment=assignment, plan=plan,
        root=root, attempt=attempt, input_ref=input_ref, failure=failure)


def workflow_case(directory, monkeypatch, *, scan=False, status=False, incompatible=False,
        before_comparison=None, corrupt=False, early=False, source_only=False):
    directory.mkdir(parents=True, exist_ok=True)
    store = Store(directory / 'store')
    store.create_problem(raw_sequence='GGGAAACCC', molecule='rna')
    scope = store.validate_scope()
    specs = [('WT', 'GGGAAACCC', -4.0), ('A', 'GGGAAAUCC', -5.0)]
    if scan:
        specs += [('B', 'GGGAAACCU', -4.0), ('C', 'GGGAAUCCC', -3.0), ('D', 'GGGUAACCC', -2.0)]
    seeds = [seed_report(store, directory / name, scope,
        b.feature(name, seq, '((.....))' if name == 'A' and not scan else '(((...)))',
            energy=value, temperature=25.0 if incompatible and name == 'A' else 37.0),
        failure=name == 'D') for name, seq, value in specs]
    resources = {'here': {'kind': 'local', 'workspace': str(directory), 'policy': deepcopy(POLICY),
        'native_rna_structure': [{key: deepcopy(seeds[0].job[key]) for key in ('operation', 'mode', 'software')}]}}
    tools = ToolRegistry(store)
    app = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)(
        store, run_id=RUN_ID, directory=directory / 'run', tool_registry=tools)
    descriptor = prepare_scientific_binding(run_directory=directory / 'run', source_directory=PUBLICATION,
        tool_catalog=tools.catalog(), child_roles=('scientific_process', 'launch', 'results'),
        resource_catalogs=app.resource_tool_catalogs)
    library = ScientificProcessLibrary(directory / 'run/scientific-process-library')
    science = {'selection': {'version': 'scientific_process_selection_v3', 'evidence_axis': library.reference('A101'),
        'thought_pattern': library.reference('P01'), 'child_tool_info': [{'name': seeds[0].job['operation'], 'resources': 'local'}]},
        'evidence_refs': scope['subject_refs'], 'constraints': {'no_external_acquisition': True},
        'context': {'supplied_sequence': 'GGGAAACCC', 'molecule': 'rna'}}
    calls, original_forms, original_contexts = [], [], []
    fixture = SimpleNamespace(store=store, seeds=seeds, resources=resources, scope=scope, selection=None,
        original_forms=original_forms, calls=calls, directory=directory, original_contexts=original_contexts)
    science_form = comparison_form(completed=False)
    if early:
        science_form['properties']['saved'] = result_form(('saved',), completed=False)['properties']['saved']
        science_form['required'].append('saved')

    def controller(path, initial):
        def estimate(raw, parameters, contexts):
            horizon = (2 if early else 1) if path[-1][0] == 'annotation' else len(seeds) + 1
            if early and len(path) == 2 and path[-1][1] == 'child_0':
                horizon = 1
            return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1), parameters,
                {'fixture': 'scripted_scientific_test_horizon'})
        return YieldController(str(path), initial, 0, YieldParameters(100, 50),
            estimate_with_context=estimate if path[-1][0] in {'annotation', 'scientific_process'} else None)

    class Choices:
        async def complete(self, episode_id, role, instructions, current, schema):
            calls.append({'episode_id': episode_id, 'role': role, 'context': deepcopy(current)})
            assert not current.get('feedback'), current.get('feedback')
            assignment = current.get('execution_assignment', {})
            if assignment.get('version') == 'execution_results_assignment_v1':
                is_comparison = assignment['selector']['version'] == 'native_rna_structure_comparison_selector_v1'
                own = [row for row in calls[:-1] if row['episode_id'] == episode_id]
                answer = selected('execution.results.status' if is_comparison and status and not own else 'execution.results.collect')
            elif 'scientific_process' not in current:
                answer = child('scientific_process', science, scope, science_form)
            else:
                own = [row for row in calls if row['episode_id'] == episode_id]
                turn = len(own) - 1
                if turn < len(seeds):
                    if turn:
                        original_forms.append(deepcopy(current['child_reports'][-1]))
                    seed = seeds[turn]
                    old = F.selector('failure' if seed.failure else 'summary', [] if seed.failure else ['pair_count'])
                    form = result_form(('references',) if source_only else ('saved', 'failure'))
                    answer = child('results', {'version': 'execution_results_assignment_v1',
                        'handoff_ref': seed.handoff, 'selector': old}, scope, form)
                else:
                    original_forms.append(deepcopy(current['child_reports'][-1]))
                    members = []
                    for (name, _, _), form in zip(specs, original_forms):
                        if name == 'D':
                            members.append({'member_id': name, 'kind': 'received_failure', 'failure': form['failure'][0]})
                        else:
                            # Adversarial source-only fixture can possess a
                            # descriptor via Store, but never received its form.
                            saved = (fixture.owner.native_rna_structure_results.saved_descriptor(
                                fixture.owner.native_rna_structure_results.read_result(form['references'][0], scope))
                                if source_only else form['saved'][0])
                            members.append({'member_id': name, 'kind': 'saved_sheet', 'saved_input': saved})
                    if scan:
                        members += [b.absent('N', 'not_tested'), b.absent('M', 'not_supplied'),
                            {'member_id': 'AliasA', 'kind': 'alias', 'canonical_member_id': 'A'}]
                    energy = b.energy_request()
                    comparisons = [b.comparison(m['member_id'], energy=energy) for m in members
                        if m['member_id'] != 'WT' and m['kind'] != 'alias']
                    projections = [{'projection_id': 'energy', 'family': 'energy_comparison', 'comparison_ids': ['compare-A'],
                        'metrics': ['baseline_native_energy', 'variant_native_energy', 'energy_delta'],
                        'include_order': True, 'include_tolerance_band': False}]
                    if scan:
                        projections = [{'projection_id': 'stability', 'family': 'scan_energy', 'scan_id': 'scan',
                            'metrics': ['baseline_rank_start', 'baseline_rank_end', 'lowest_energy_tie_count',
                                'baseline_energy_above_minimum'], 'include_rank_class': True}]
                    else:
                        comparisons[0].update(correspondence={'kind': 'substitution_only', 'substitutions': [
                            {'index': 6, 'baseline_symbol': 'C', 'variant_symbol': 'U'}]},
                            site_selections=[b.site(positions=[0, 6])], calculate_pair_changes=True)
                        projections += [{'projection_id': 'two-structures', 'family': 'structures', 'member_ids': ['WT', 'A'],
                            'fields': ['dot_bracket']}, {'projection_id': 'sites', 'family': 'position_changes',
                            'comparison_id': 'compare-A', 'selection_id': 'selected',
                            'transitions': ['unchanged_partner', 'lost_pairing']}]
                    chosen = b.selector(members, comparisons, scan=b.scan_request(energy) if scan else None,
                        projections=projections)
                    fixture.selection = chosen
                    fixture.science_context = fixture.owner.native_rna_structure_returns.context(episode_id)
                    fixture.original_contexts[:] = [fixture.owner.native_rna_structure_returns.context(row['episode_id'])
                        for row in store.db.execute("SELECT episode_id FROM runtime_episodes WHERE run_id=? AND json_extract(path,'$[#-1][0]')='results'", (RUN_ID,))]
                    if before_comparison:
                        before_comparison(fixture)
                    if corrupt:
                        artifact = store.get(members[0]['saved_input']['sheet_artifact_ref'])
                        path = store.path / 'artifacts' / artifact['sha256'][:2] / artifact['sha256']
                        if corrupt == 'missing':
                            path.unlink()
                        else:
                            path.write_bytes(b'{}\n')
                    answer = child('results', {'version': 'execution_results_assignment_v1',
                        'handoff_ref': seeds[1].handoff, 'selector': fixture.selection}, scope, comparison_form())
            answer = provider_value(plain(answer), plain(schema))
            Draft202012Validator(plain(schema)).validate(answer)
            return answer

        async def release(self, episode_id):
            pass

    flow = Workflow(store, tools, Choices(), directory / 'run', RUN_ID, controller_factory=controller,
        project_credit=lambda *a, **k: 0, annotation_child_roles=('scientific_process',), episode_record_receipts=True,
        initial_known_record_refs=[ref for seed in seeds for ref in (seed.handoff, seed.input_ref)],
        episode_binding_descriptors=(descriptor, *app.episode_binding_descriptors),
        role_credit_bindings=app.role_credit_bindings, job_progress_provider=app.job_progress_provider)
    fixture.flow = flow
    fixture.owner = owner = flow.episode_bindings.for_role('results')
    original_observations = []
    def observed(target, *, operation_key, **kwargs):
        original_observations.append(operation_key)
        assert target['handle'] in [seed.handoff for seed in seeds]
        return {'observed_at': '2026-10-26T00:00:02+00:00', 'state': 'completed', 'returncode': 0,
            'failure_code': None, 'result_available': True, 'measurements': [], 'outputs': [], 'logs': [],
            'provenance_refs': [], 'native': {'fixture': 'synthetic_producer_status'}}
    monkeypatch.setattr(owner.job_progress_provider.targets, 'observe_target', observed)
    # Missing bundle is a real result-acquisition failure. Give that old
    # result fixture a one-action horizon; it is not practical completion.
    actual_estimator = owner.practical_estimator
    def estimator(context):
        assignment = plain(context.assignment)
        failed_comparison = corrupt and assignment.get('selector', {}).get('version') == 'native_rna_structure_comparison_selector_v1'
        if context.role == 'results' and (failed_comparison or any(seed.failure and assignment['handoff_ref'] == seed.handoff for seed in seeds)):
            from gene_annotation_episode.practical_yield import PracticalYieldEstimator
            def base(raw, params):
                return YieldEstimate(len(raw), NumericBand.exact(0 if raw else 1), params, {'fixture': 'failed_acquisition_horizon'})
            return PracticalYieldEstimator(lambda proof: owner.verify_completion(context, proof), base_estimate=base)
        return actual_estimator(context)
    monkeypatch.setattr(owner, 'practical_estimator', estimator)
    if early:
        actual_build = flow.build
        def build(*args, **kwargs):
            episode = actual_build(*args, **kwargs)
            if episode.source.path == (('annotation', 'root'), ('scientific_process', 'child_0')):
                async def no_decision(view):
                    return None
                episode.source.next = no_decision
            return episode
        flow.build = build
    root = flow.build('annotation', 'root', 'Compare the selected retained RNA structures and energies.', scope)
    async def run():
        record = await root.run_async(flow.context)
        await root.build_result(record)
        return record
    record = asyncio.run(run())
    records = list(walk(json.loads(''.join(iter_json(record.as_record())))))
    contexts = {row['episode_id']: owner.native_rna_structure_returns.context(row['episode_id']) for row in records}
    result_contexts = [contexts[row['episode_id']] for row in records if contexts[row['episode_id']].role == 'results']
    comparison_context = result_contexts[-1]
    forms = {ctx.episode_id: json.loads(flow.journal.row('runtime_forms', ctx.episode_id)['form'])
        for ctx in contexts.values() if ctx.role != 'annotation'}
    fixture.record, fixture.records, fixture.contexts = record, records, contexts
    fixture.root_context = contexts[record.episode_id]
    fixture.comparison_context, fixture.forms, fixture.original_observations = comparison_context, forms, original_observations
    fixture.body = json.loads(flow.journal.row('runtime_actions', comparison_context.episode_id, int(status))['result'])['result']
    fixture.returned = forms[comparison_context.episode_id]
    (directory / 'CASE.json').write_bytes(encoded({'identity': 'synthetic_native_reports_actual_Workflow_and_bounded_comparison',
        'selector': fixture.selection, 'returned': fixture.returned, 'body': fixture.body,
        'returned_forms': forms,
        'histories': {row['episode_id']: row['controller_state'] for row in records}}))
    return fixture
