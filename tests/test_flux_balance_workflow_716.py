"""Bounded FBA Workflow proof, sharing one original native case.

Scripted choices and a supplied synthetic model are engineering verification,
not configured-model reasoning or observed biology. A skipped/unrun case is
never completion evidence. Preserve its original directory after any failure.
"""
import asyncio
from copy import deepcopy
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.state import Store


H = import_module('verification.tool_graders_flux_balance_workflow_2026-10-29_716.fixture_helpers')
pytestmark = pytest.mark.skipif('HMMER529_ATTEMPT' not in os.environ, reason='requires explicitly selected bounded529')


def deny(*args, **kwargs):
    raise AssertionError('saved-only or closed replay attempted unselected scientific/native work')


def artifact_path(store, file):
    return store.path / 'artifacts' / file['sha256'][:2] / file['sha256']


def remove_owned(path, case, removed, *, kind, protected=()):
    path = Path(path)
    assert path.is_relative_to(case.directory), 'never remove688,714 deployment or another case'
    if path in protected or not path.is_file():
        return
    raw = path.read_bytes()
    path.unlink()
    removed.append({'kind': kind, 'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)})


def remove_private_worker_runtime(worker, case, removed):
    execution_root = Path(worker['execution_directory'])
    pins = [worker['execution']['intent']['interpreter'], *worker['execution']['intent']['source_pins']]
    for pin in pins:
        assert Path(pin['path']).is_relative_to(execution_root)
        remove_owned(pin['path'], case, removed, kind='private_original_worker_runtime')


@pytest.fixture(scope='module')
def connected_case():
    # A stable original-attempt directory supports assertion-only repair later.
    directory = Path(os.environ['HMMER529_ATTEMPT']) / 'workflow716'
    software = H.selected_software()
    evidence, patch = {}, pytest.MonkeyPatch()

    def before_saved(case):
        original, = H.worker_runs(directory)
        assert original['plan']['mode'] == 'native_result'
        native_outcome, = H.completed_fba_outcomes(case.store)
        receipt = native_outcome['result']
        evidence.update(original_worker=deepcopy(original), original_receipt=deepcopy(receipt),
            sheet_file=deepcopy(case.sheet_file), sheet_bytes=case.store.get_artifact(case.sheet_file['artifact_ref']),
            observations=H.rows(case.store, 'runtime_observations'),
            actions=[r for r in H.rows(case.store, 'runtime_actions') if r['result'] is not None],
            origins=case.owner.native_flux_balance_returns.authenticate_received_saved_sheet(
                case.science_context, case.sheet_file),
            calculations=json.loads(case.store.get_artifact(receipt['qualified_files']['calculations']['artifact_ref'])),
            native_plan_bytes=(directory / 'original-native-plan.json').read_bytes(),
            native_controls={str(path): path.read_bytes() for path in (
                Path(case.provider.target['execution_id']),
                Path(case.provider.target['execution_id']).parent / 'flux-balance-plan.json',
                Path(case.provider.target['execution_id']).parent / 'invoke.json',
                Path(case.provider.target['execution_id']).parent / 'flux-balance-input-binding.json',
                Path(case.provider.plan['attempt_directory']) / '.native-flux-balance-owner.json',
                Path(case.provider.plan['attempt_directory']) / '.native-flux-balance-started.json',
                Path(case.provider.plan['attempt_directory']) / '.native-flux-balance-environment.json',
                Path(case.provider.plan['attempt_directory']) / '.native-flux-balance-solve-entered.json')})
        # Preserve complete original work for operator review/assertion repair.
        # These are verification evidence copies outside every selected input
        # path and outside Store. They are never registered/granted to an episode.
        archive = directory / 'retained-native-evidence'
        archive.mkdir()
        copies = {**{'native-' + role: raw for role, raw in case.provider.native_bytes.items()},
            'sheet.json': evidence['sheet_bytes'], 'calculations.json': case.store.get_artifact(
                receipt['qualified_files']['calculations']['artifact_ref'])}
        evidence['retained_scientific_evidence'] = []
        for name, raw in copies.items():
            path = archive / name
            path.write_bytes(raw)
            evidence['retained_scientific_evidence'].append({'path': str(path),
                'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw),
                'episode_input_or_grant': False})
        H.write(archive / 'FILE_PINS.json', evidence['retained_scientific_evidence'])
        protected = {artifact_path(case.store, case.sheet_file)}
        # Frozen authority/control files remain available. Scientific files are
        # deliberately unavailable, with content-addressed aliases accounted for.
        control_files = [receipt['source_action_file'], receipt['writer_closure_file'],
            receipt['handoff_proof']['input_binding']['file']]
        control_files += [receipt['native'][name] for name in
            ('plan_file', 'handle_file', 'request_file', 'invoke_file', 'started_marker_file')]
        control_files += [row['file'] for row in receipt['capture']['controls'].values() if row is not None]
        protected.update(artifact_path(case.store, file) for file in control_files if file is not None)
        removed = []
        for spec in case.provider.plan['outputs']:
            remove_owned(Path(case.provider.plan['attempt_directory']) / spec['relative_path'], case,
                removed, kind='original_native_output')
        for row in receipt['capture']['files']:
            if row['retained'] is not None:
                remove_owned(artifact_path(case.store, row['retained']['file']), case, removed,
                    kind='captured_native_scientific_bytes', protected=protected)
        remove_owned(Path(case.provider.plan['requested_job']['native_flux_balance']['model_input']['file']['path']),
            case, removed, kind='original_caller_model', protected=protected)
        for row in original['capture']['outputs']:
            declaration = row['declared']
            remove_owned(Path(original['directory']) / declaration['relative_path'], case, removed,
                kind='original_worker_scientific_copy')
            if row['observed'] is not None:
                remove_owned(artifact_path(case.store, row['observed']), case, removed,
                    kind='original_worker_retained_scientific_bytes', protected=protected)
        remove_private_worker_runtime(original, case, removed)
        assert len([row for row in removed if row['kind'] == 'original_native_output']) == 8
        assert not Path(case.provider.plan['requested_job']['native_flux_balance']['model_input']['file']['path']).exists()
        assert case.store.get_artifact(case.sheet_file['artifact_ref']) == evidence['sheet_bytes']
        evidence.update(removed=removed, dispatches=[], lifecycle_accesses=[])
        H.write(directory / 'SAVED_REMOVALS.json', removed)

        from gene_annotation_episode import native_lifecycle
        actual_prepare = native_lifecycle.prepare_job

        def saved_worker_only(command, **kwargs):
            assert command[1:5] == ['-B', '-S', '-m', 'gene_annotation_episode.flux_balance_result_worker']
            plan = json.loads(Path(command[-1]).read_bytes())
            assert plan['mode'] == 'saved_sheet_recalculation'
            assert plan['sheet']['file'] == case.sheet_file == plan['selector']['saved_sheet_file']
            assert 'original_plan' not in plan and 'capture' not in plan
            assert kwargs['policy'].to_dict() == H.POLICY
            assert kwargs['cwd'] == Path(plan['directory']).parent
            evidence['dispatches'].append({'command': list(command), 'plan': deepcopy(plan)})
            return actual_prepare(command, **kwargs)

        patch.setattr(native_lifecycle, 'prepare_job', saved_worker_only)
        for name in ('start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
            function = getattr(native_lifecycle, name)

            def saved_lifecycle_only(handle, *args, _name=name, _function=function, **kwargs):
                assert str(handle.path) != case.provider.target['execution_id']
                assert handle.path.name == 'worker.handle.json' and handle.path.parent.name == 'worker.execution'
                evidence['lifecycle_accesses'].append({'operation': _name, 'handle': str(handle.path)})
                return _function(handle, *args, **kwargs)

            patch.setattr(native_lifecycle, name, saved_lifecycle_only)
        patch.setattr('gene_annotation_episode.native_flux_balance_results.capture_flux_balance_native_files', deny)
        patch.setattr(type(case.owner.job_progress_provider.targets), 'observe_target', deny)
        patch.setattr('socket.create_connection', deny)
        patch.setattr('socket.socket.connect', deny)
        patch.setattr('socket.socket.connect_ex', deny)

    try:
        case = H.workflow_case(directory, software, before_saved=before_saved)
        case.saved_evidence = evidence
        H.write(directory / 'SAVED_CHECK.json', {key: value for key, value in evidence.items()
            if key not in {'sheet_bytes', 'native_plan_bytes', 'native_controls', 'calculations'}})
    finally:
        patch.undo()
    try:
        yield case
    finally:
        case.store.close()


def test_selected_native_model_numbers_reach_requested_scientific_receiver(connected_case):
    case = connected_case
    assert {role: len(records) for role, records in case.by_role.items()} == {
        'annotation': 1, 'scientific_process': 1, 'launch': 1, 'launch_local': 1, 'results': 2}
    catalog = case.tools.catalog()
    registered = set(catalog) if isinstance(catalog, dict) else {row['name'] for row in catalog}
    assert H.OPERATION not in registered
    info, = plain(case.scientific_context.assignment)['selection']['child_tool_info']
    assert info['name'] == H.OPERATION and info['resources'] == 'local'
    assert info['description'] and info['instructions']
    scientific = plain(case.scientific_context.assignment)
    assert scientific['selection']['evidence_axis']['option_id'] == 'A110'
    assert scientific['selection']['thought_pattern']['option_id'] == 'P10'
    assert {case.hypothesis_ref, case.reaction_ref, case.mapping_source, case.model_source} <= set(scientific['evidence_refs'])
    assert scientific['context']['hypothesis_ref'] == case.hypothesis_ref
    assert scientific['context']['reaction_correspondence']['model_reaction_id'] == 'AB'
    assert case.store.get(case.hypothesis_ref)['value'] == {'type': 'reference', 'ref': case.reaction_ref}
    for role in ('launch', 'launch_local'):
        context = case.contexts[case.by_role[role][0]['episode_id']]
        selected = plain(context.assignment)
        assert selected['version'] == ('flux_balance_scientific_launch_v1' if role == 'launch'
            else 'flux_balance_scientific_assignment_v1')
        assert plain(context.request)['message']['episode_assignment'] == selected
    assert case.provider.plan['requested_job']['native_flux_balance'] == case.job
    assert case.job['constraints'] == [{'reaction_id': 'AB',
        'lower': {'kind': 'finite', 'value': 0, 'native_token': None, 'float_hex': None, 'source': None},
        'upper': {'kind': 'finite', 'value': 0, 'native_token': None, 'float_hex': None, 'source': None}}]
    assert case.job['objective'] == {'kind': 'model_default', 'reaction_id': None}
    assert case.job['software'] == case.configuration['factory']['resources']['here']['native_flux_balance'][0]['software']
    assert case.provider.plan['policy'] == H.POLICY
    assert case.provider.plan['version'] == 'flux_balance_run_plan_v2'
    binding = case.provider.plan['environment_binding']
    assert binding['selection'] == H.EXECUTION_SELECTION
    assert binding['requested_environment'] == case.provider.plan['requested_job']['environment']
    assert [row['name'] for row in binding['relocations']] == ['TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME', 'PIP_CACHE_DIR']
    observation = json.loads(case.saved_evidence['native_controls'][
        str(Path(case.provider.plan['attempt_directory']) / '.native-flux-balance-environment.json')])
    marker = json.loads(case.saved_evidence['native_controls'][
        str(Path(case.provider.plan['attempt_directory']) / '.native-flux-balance-started.json')])
    assert observation['expected_environment'] == observation['observed_environment'] == binding['realized_environment']
    assert marker['environment_observation_sha256'] == digest(observation)
    assert observation['plan_sha256'] == marker['plan_sha256'] == digest(case.provider.plan)
    native_execution = json.loads((case.directory / 'native-lifecycle.json').read_bytes())
    assert native_execution['returncode'] == 0
    assert native_execution['metadata']['verified_cgroup'] == {'memory_max': 21474836480,
        'memory_swap_max': 0, 'runtime_max': 'infinity', 'kill_mode': 'control-group', 'oom_policy': 'kill'}
    assert len(case.provider.native_bytes) == 8
    manifest = json.loads(case.provider.native_bytes['manifest'])
    assert manifest['attempt'] == case.provider.plan['identity']
    assert manifest['attempt']['run_id'] == H.RUN_ID != 'producer688'
    assert manifest['solve_call_count'] == 1
    native_solution = json.loads(case.provider.native_bytes['solution'])
    assert native_solution['model_optimize_call_count'] == 1
    assert native_solution['native_passes']
    assert [row['position'] for row in native_solution['native_passes']] == list(range(len(native_solution['native_passes'])))
    assert all(row['routine'] == 'glp_simplex' for row in native_solution['native_passes'])
    solve_entered = json.loads(case.saved_evidence['native_controls'][
        str(Path(case.provider.plan['attempt_directory']) / '.native-flux-balance-solve-entered.json')])
    assert solve_entered['model_optimize_call_count'] == 1 and solve_entered['attempt'] == manifest['attempt']
    assert len(case.saved_evidence['original_receipt']['capture']['files']) == 8
    assert all(row['retained'] is not None for row in case.saved_evidence['original_receipt']['capture']['files'])
    assert case.saved_evidence['original_receipt']['worker_capture']['result']['native_association'] == 'verified'
    assert case.saved_evidence['original_receipt']['worker_capture']['result']['new_attempt_evidence_roles']

    sheet, calculated = json.loads(case.saved_evidence['sheet_bytes']), case.saved_evidence['calculations']
    assert sheet['operation'] == H.OPERATION and sheet['mode'] == H.MODE
    assert [row['id'] for row in sheet['models']['effective']['reactions']] == ['IN', 'AB', 'OUT']
    for phase in ('loaded_original', 'effective'):
        bounds = {row['id']: (row['lower']['value'], row['upper']['value'])
            for row in sheet['models'][phase]['reactions']}
        assert bounds == {'IN': (0, 10), 'AB': (0, 1000) if phase == 'loaded_original' else (0, 0),
            'OUT': (0, 1000)}
    assert sheet['native']['request_realization'] == 'exact'
    assert [row['gene_positions'] for row in sheet['models']['effective']['reactions']] == [[], [0, 1], []]
    assert all(row['flux_unit']['basis'] == 'unknown' and row['flux_unit']['native_text'] is None
        for row in sheet['models']['effective']['reactions'])
    assert sheet['native_solution']['native']['native_passes'] == native_solution['native_passes']
    problem = sheet['problems']['effective']
    assert problem['variable_count'] == 6 and problem['constraint_count'] == 2
    assert {row['subject_id'] for row in case.parameters['variable_bound_tolerances']} == {row['id'] for row in problem['variables']}
    assert {row['subject_id'] for row in case.parameters['constraint_tolerances']} == {row['id'] for row in problem['constraints']}
    assert calculated['sheet_sha256'] == digest(sheet) and calculated['parameters'] == case.parameters
    assert calculated['expected_reaction_count'] == calculated['valid_flux_count'] == 3
    assert calculated['expected_variable_count'] == calculated['valid_variable_count'] == 6
    assert calculated['expected_constraint_count'] == 2
    assert calculated['evaluated_variable_bound_count'] == 12 and calculated['violated_variable_bound_count'] == 0
    assert calculated['violated_reaction_bound_count'] == calculated['violated_constraint_count'] == 0
    by_position = {row['reaction_position']: row for row in calculated['reaction_checks']}
    assert set(by_position) == {row['position'] for row in sheet['models']['effective']['reactions']}
    fluxes = {reaction['id']: by_position[reaction['position']]['flux']['value']
        for reaction in sheet['models']['effective']['reactions']}
    assert fluxes == {'IN': 0, 'AB': 0, 'OUT': 0}
    assert calculated['objective']['native_basis_calculated']['value'] == 0
    assert calculated['objective']['full_calculated']['value'] == 0
    # Independent conservation arithmetic for this explicitly supplied model.
    independent_balance = {'A': fluxes['IN'] - fluxes['AB'], 'B': fluxes['AB'] - fluxes['OUT']}
    assert independent_balance == {'A': 0, 'B': 0}
    for row in calculated['constraint_checks']:
        if row['equality_residual']['value'] is not None:
            assert row['equality_residual']['value'] == 0

    original, saved = [form['measurements'][0] for form in case.returned]
    assert original == case.outcomes[0]['result']['projection']
    assert original['selector']['view'] == 'run_diagnostics' and original['selector'] == H.selector(case.parameters)['projection']
    values = {row['field']: row['value'] for row in original['rows']}
    assert values['native_run']['solve_call_count'] == sheet['native']['solve_call_count'] == 1
    for name in ('native_basis_calculated', 'full_calculated'):
        assert values['objective']['check'][name]['value'] == calculated['objective'][name]['value']
        assert values['objective']['check'][name]['state'] == calculated['objective'][name]['state']
    assert values['reaction_population']['expected_reaction_count'] == calculated['expected_reaction_count']
    assert values['variable_population']['valid_variable_count'] == calculated['valid_variable_count']
    assert values['variable_bound_counts']['evaluated_variable_bound_count'] == calculated['evaluated_variable_bound_count']
    assert values['active_population']['active_count'] == calculated['active_count']
    assert values['balance_residual']['max_abs_balance_residual']['value'] == calculated['max_abs_balance_residual']['value']
    assert values['balance_residual']['max_abs_balance_residual']['state'] == calculated['max_abs_balance_residual']['state']
    assert saved == case.outcomes[1]['result']['projection'] and saved['selector']['view'] == 'reaction_fluxes'
    assert [row['reaction_position'] for row in saved['rows']] == [2, 0]
    assert [row['reaction_id'] for row in saved['rows']] == ['OUT', 'IN']
    assert [row['values']['flux']['flux']['value'] for row in saved['rows']] == [0, 0]
    assert tuple(saved['page'][key] for key in
        ('selected_row_count', 'row_offset', 'returned_row_count', 'has_more')) == (3, 0, 2, True)
    assert case.forwarded == {'measurements': [original, saved]}
    assert case.owner.native_flux_balance_returns.received_facts(case.root_context, case.parent_form) == {
        H.SOURCES['measurements']: [original, saved]}
    assert all(form['completed'] for form in case.returned)
    H.write(case.directory / 'NUMERICAL_EXAMPLE.json', {'scope': 'new selected synthetic Cobra JSON prediction only',
        'fluxes': fluxes, 'independent_model_balance': independent_balance,
        'calculated_objective': calculated['objective'], 'native_solve_call_count': manifest['solve_call_count'],
        'actual_native_passes': native_solution['native_passes'],
        'units': 'unknown', 'actual_native_solver_status': calculated['native_solver_status'],
        'constraint_checks': calculated['constraint_checks'], 'returned': case.returned, 'forwarded': case.forwarded})


def test_received_sheet_alone_recalculates_without_new_native_acquisition(connected_case):
    case, saved = connected_case, connected_case.saved_evidence
    assert len(saved['dispatches']) == 1
    original, recalculated = [row['result'] for row in case.outcomes]
    assert original['acquired_population'] is not None and recalculated['acquired_population'] is None
    assert all(recalculated[name] is None for name in ('observation', 'native', 'capture', 'source_action_file', 'writer_closure_file'))
    assert recalculated['original_origins'] == [{'episode_id': case.result_contexts[0].episode_id,
        'operation_key': f'{H.RUN_ID}:{case.result_contexts[0].episode_id}:0'}]
    assert case.returned[0]['saved'] == case.returned[1]['saved'] == [saved['sheet_file']]
    assert case.store.get_artifact(saved['sheet_file']['artifact_ref']) == saved['sheet_bytes']
    workers = H.worker_runs(case.directory)
    assert sorted(row['plan']['mode'] for row in workers) == ['native_result', 'saved_sheet_recalculation']
    worker, = [row for row in workers if row['plan']['mode'] == 'saved_sheet_recalculation']
    assert worker['plan']['sheet']['file'] == saved['sheet_file']
    derived = {row['observed']['sha256'] for row in worker['capture']['outputs'] if row['observed'] is not None}
    recreated = [row for row in saved['removed'] if Path(row['path']).exists()]
    assert all(row['kind'] == 'original_worker_retained_scientific_bytes' and row['sha256'] in derived for row in recreated)
    assert all(Path(path).read_bytes() == raw for path, raw in saved['native_controls'].items())
    assert (case.directory / 'original-native-plan.json').read_bytes() == saved['native_plan_bytes']
    assert all(row in H.rows(case.store, 'runtime_observations') for row in saved['observations'])
    assert all(row in H.rows(case.store, 'runtime_actions') for row in saved['actions'])
    assert case.owner.resolve_received_reference(case.scientific_context, saved['sheet_file']['artifact_ref'], 'artifact') is True
    assert case.owner.resolve_received_reference(case.root_context, saved['sheet_file']['artifact_ref'], 'artifact') is False
    with pytest.raises(ValueError, match='saved_sheet_not_received'):
        case.owner.native_flux_balance_returns.authenticate_received_saved_sheet(case.root_context, saved['sheet_file'])
    for row in workers:
        execution = row['execution']
        assert execution['terminal'] and execution['quiescent'] and execution['returncode'] == 0
        assert execution['metadata']['verified_cgroup'] == {'memory_max': 21474836480,
            'memory_swap_max': 0, 'runtime_max': 'infinity', 'kill_mode': 'control-group', 'oom_policy': 'kill'}
        assert execution['intent']['source_pins'] and execution['intent']['runtime_files']
        assert execution['intent']['interpreter'] and execution['intent']['dependencies']


def test_selected_completed_output_roles_close_the_original_native_assignment(connected_case):
    case = connected_case
    record, = case.by_role['launch_local']
    context = case.contexts[record['episode_id']]
    state = case.owner.state(context)
    selected = plain(context.assignment)
    assert selected['endpoint'] == state.assignment['endpoint'] == 'completed_job_outputs'
    assert selected['completion_keys'] == state.assignment['completion_keys'] == ['selected_outputs']
    assert selected['progress_requirements'] == state.assignment['progress_requirements'] == [
        {'key': 'handoff', 'credit': 7, 'predicate': {'kind': 'requested_job_handoff'}},
        {'key': 'selected_outputs', 'credit': 0, 'predicate': {
            'kind': 'requested_job_outputs', 'output_roles': ['solution', 'flux_csv']}}]
    receipts = state.receipts()
    assert [row['tool_name'] for row in receipts] in (
        ['practical.job.start'], ['practical.job.start', 'practical.job.collect'])
    proof = state.completion_proof()
    assert proof['endpoint'] == 'completed_job_outputs' and proof['validation_keys'] == ['selected_outputs']
    assert proof['operation_key'] == receipts[-1]['operation_key']
    assert proof['receipt_sha256'] == digest(receipts[-1]) and state.verify_completion(proof)
    original_identity = (case.provider.target['execution_id'], digest(state.assignment['requested_job']))
    for receipt in receipts:
        job = receipt['outcome']['facts']['requested_job']
        assert (job['execution_id'], job['requested_job_sha256']) == original_identity
        assert job['argv'] == state.assignment['requested_job']['argv']
        assert job['environment'] == state.assignment['requested_job']['environment']
    terminal = receipts[-1]
    job = terminal['outcome']['facts']['requested_job']
    assert job['status'] == 'completed' and job['returncode'] == 0
    declarations = {row['role']: row for row in case.provider.plan['outputs']}
    requested_paths = [str(Path(case.provider.plan['attempt_directory']) / declarations[role]['relative_path'])
        for role in ('solution', 'flux_csv')]
    assert set(requested_paths) < set(job['output_paths'])
    path_facts = {row['path']: row for row in terminal['outcome']['facts']['paths']}
    assert set(path_facts) == set(requested_paths)
    assert all(row['exists'] and row['object_type'] == 'file' for row in path_facts.values())
    validation, = [row for row in terminal['validations'] if row['key'] == 'selected_outputs']
    assert validation['satisfied'] and validation['predicate'] == selected['progress_requirements'][1]['predicate']
    assert [row['path'] for row in validation['evidence']['value']['paths']] == requested_paths
    assert validation['evidence']['value']['requested_job'] == job
    if len(receipts) == 2:
        earlier, = [row for row in receipts[0]['validations'] if row['key'] == 'selected_outputs']
        assert not earlier['satisfied']
        assert case.owner.completion_for_action(context, receipts[0]['operation_key']) is None
    assert H.history(record) == [7] + [0] * (len(receipts) - 1)
    assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()


def test_one_observation_per_action_exact_redelivery_and_immediate_practical_zero(connected_case):
    case = connected_case
    for record in case.records:
        context = case.contexts[record['episode_id']]
        actions = [row for row in H.rows(case.store, 'runtime_actions') if row['episode_id'] == context.episode_id]
        observations = [row for row in H.rows(case.store, 'runtime_observations') if row['episode_id'] == context.episode_id]
        assert len(actions) == len(observations) == record['units_consumed']
        assert case.provider.turns[context.episode_id] == len(actions) + (context.role == 'scientific_process')
        if context.role in {'launch', 'launch_local', 'results'}:
            if context.role == 'launch_local':
                assert len(actions) in (1, 2)
            else:
                assert len(actions) == 1
            assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
            final_index = max(row['decision_index'] for row in actions)
            key = f'{H.RUN_ID}:{context.episode_id}:{final_index}'
            proof = case.owner.completion_for_action(context, key)
            assert proof is not None and proof['operation_key'] == key and case.owner.verify_completion(context, proof)
            completed, = [row for row in observations if row['unit_index'] == record['units_consumed'] - 1]
            assert json.loads(completed['observation'])['credit']['practical_completion'] == proof
            for earlier in actions:
                if earlier['decision_index'] < final_index:
                    assert case.owner.completion_for_action(context,
                        f'{H.RUN_ID}:{context.episode_id}:{earlier["decision_index"]}') is None
    local, = case.by_role['launch_local']
    assert H.history(local) == [7] + [0] * (local['units_consumed'] - 1)
    assert [H.history(row) for row in case.by_role['launch']] == [[case.owner.handoff_unit]]
    assert [H.history(row) for row in case.by_role['results']] == [[case.owner.acquired_record_unit], [0]]
    assert case.store.count('annotation') == 0
    attempts = [row for row in H.rows(case.store, 'runtime_report_attempts')
        if row['parent_episode_id'] == case.scientific_context.episode_id
        and row['child_episode_id'] == case.result_contexts[0].episode_id]
    assert len(attempts) == 2 and attempts[0]['form'] == attempts[1]['form']
    assert all(row['failure'] is None for row in attempts)
    H.write(case.directory / 'COMPLETION_AND_CREDIT.json', {
        'histories': {role: [H.history(row) for row in records] for role, records in case.by_role.items()},
        'practical_future_expected_gain': 'exact_zero_at_same_closure',
        'new_native_population': case.outcomes[0]['result']['acquired_population'],
        'saved_native_population': case.outcomes[1]['result']['acquired_population'],
        'redelivery_forms_equal': True, 'units_are_operational_not_annotation_confidence': True})


def test_public_results_are_exact_views_of_retained_private_receipts(connected_case):
    case = connected_case
    for context, public, private in zip(case.result_contexts, case.public_outcomes, case.outcomes):
        assert public['result']['version'] == 'flux_balance_public_result_v1'
        assert public['result']['facts'] == private['result']['facts']
        assert public['result']['delivery_complete'] == private['result']['delivery_complete']
        for key in ('intent', 'handoff_proof', 'native', 'worker_plan', 'worker_execution'):
            assert key not in public['result']
        operation_key = f'{H.RUN_ID}:{context.episode_id}:0'
        reader = case.owner.native_flux_balance_results.receipts
        assert reader.read_completed(episode_id=context.episode_id,
            operation_key=operation_key, scope=case.scope) == private['result']
        row = case.flow.journal.row('runtime_actions', context.episode_id, 0)
        changed = json.loads(row['result'])
        changed['result']['delivery_complete'] = not changed['result']['delivery_complete']
        try:
            case.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0',
                (json.dumps(changed), H.RUN_ID, context.episode_id))
            with pytest.raises(ValueError, match='completed_result_mismatch'):
                reader.read_completed(episode_id=context.episode_id,
                    operation_key=operation_key, scope=case.scope)
        finally:
            case.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0',
                (row['result'], H.RUN_ID, context.episode_id))


def assert_committed_practical_view_is_authenticated(case, owner, store):
    record, = case.by_role['launch_local']
    context = owner.native_flux_balance_returns.context(record['episode_id'])
    receipt = owner.state(context).receipts()[-1]
    key = receipt['operation_key']
    index = int(key.rsplit(':', 1)[1])
    proof = owner.completion_for_action(context, key)
    estimator = owner.practical_estimator(context)
    assert proof is not None and estimator.verify_completion(proof)
    row = store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
        (H.RUN_ID, context.episode_id, index)).fetchone()
    altered = json.loads(row['result'])
    altered['result']['job']['returncode'] = 1
    try:
        store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?',
            (json.dumps(altered), H.RUN_ID, context.episode_id, index))
        for read in (lambda: owner.credit_view(context, {}),
                lambda: owner.completion_for_action(context, key),
                lambda: owner.verify_completion(context, proof),
                lambda: estimator.verify_completion(proof),
                lambda: owner.facts(context, {})):
            with pytest.raises(ValueError, match='public_outcome_conflict'):
                read()
    finally:
        store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?',
            (row['result'], H.RUN_ID, context.episode_id, index))
    assert estimator.verify_completion(proof)
    assert owner.completion_for_action(context, key) == proof
    return context, receipt, json.loads(row['result'])


def test_direct_practical_credit_completion_and_cached_verifier_require_exact_public_view(connected_case):
    case = connected_case
    before = {table: H.rows(case.store, table) for table in H.TABLES}
    assert_committed_practical_view_is_authenticated(case, case.owner, case.store)
    assert {table: H.rows(case.store, table) for table in H.TABLES} == before


def test_scientific_receiver_gets_recurring_actual_task_and_steering_text(connected_case):
    case = connected_case
    calls = [row for row in case.provider.calls if row['episode_id'] == case.scientific_context.episode_id]
    assert len(calls) == 4
    for row in calls:
        text = row['model_text']
        assert text.startswith('TASK\n') and '\n\nSTEERING\n' in text
        assert 'Biochemical feasibility and chemical/resource accounting' in text
        assert 'Account for the coupled chemical system' in text
        assert 'Use the account to constrain the possible function without equating feasibility with demonstrated target activity or physiological use.' in text
        assert 'Keep measured balances distinct from ideal fully coupled ratios and preserve unknown potentials/recovery.' in text
        assert 'Selected tool: perform_flux_balance_analysis (local)' in text
        assert 'reaction_correspondence.model_reaction_id | AB' in text
        assert 'For an assigned reaction knockout, set both bounds' in text
        assert '| Field | Supplied value |' in text
    # Retain every actual presentation, including other roles' current JSON
    # fallback. A successful scientific TASK is not proof of their formatting.
    H.write(case.directory / 'MODEL_PRESENTATIONS.json', [{
        'episode_id': row['episode_id'], 'episode_role': case.contexts[row['episode_id']].role,
        'model_text': row['model_text'], 'model_instructions': row['model_instructions']}
        for row in case.provider.calls])


def test_closed_workflow_replays_with_scientific_bytes_and_execution_forbidden(connected_case, monkeypatch):
    case = connected_case
    removed, denied_refs = [], set()
    for worker in H.worker_runs(case.directory):
        remove_private_worker_runtime(worker, case, removed)
        for row in worker['capture']['outputs']:
            remove_owned(Path(worker['directory']) / row['declared']['relative_path'], case, removed,
                kind='closed_worker_scientific_copy')
            if row['observed'] is not None:
                denied_refs.add(row['observed']['artifact_ref'])
                remove_owned(artifact_path(case.store, row['observed']), case, removed, kind='closed_retained_scientific_bytes')
        if worker['plan']['mode'] == 'native_result':
            denied_refs.update(row['retained']['file']['artifact_ref'] for row in worker['plan']['capture']['files']
                if row['retained'] is not None)
    H.write(case.directory / 'CLOSED_REMOVALS.json', removed)
    for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
        monkeypatch.setattr('gene_annotation_episode.native_lifecycle.' + name, deny)
    for name in ('capture_flux_balance_native_files', 'prepare_flux_balance_result_worker'):
        monkeypatch.setattr('gene_annotation_episode.native_flux_balance_results.' + name, deny)
    for target in ('gene_annotation_episode.flux_balance_readers.parse_fba_capture',
            'gene_annotation_episode.flux_balance_sheet.populate_flux_balance_sheet',
            'gene_annotation_episode.flux_balance_calculations.calculate_flux_balance_sheet',
            'gene_annotation_episode.flux_balance_result_views.project_fba_result'):
        monkeypatch.setattr(target, deny)
    monkeypatch.setattr(type(case.owner.job_progress_provider.targets), 'observe_target', deny)
    monkeypatch.setattr('socket.create_connection', deny)
    monkeypatch.setattr('socket.socket.connect', deny)
    monkeypatch.setattr('socket.socket.connect_ex', deny)
    actual_get_artifact = Store.get_artifact

    def controls_only(store, reference):
        assert reference not in denied_refs, 'closed replay read scientific artifact bytes'
        return actual_get_artifact(store, reference)

    monkeypatch.setattr(Store, 'get_artifact', controls_only)

    class NoNewDecisions:
        async def complete(self, *args, **kwargs):
            raise AssertionError('closed Workflow requested a new decision')
        async def release(self, episode_id):
            pass

    with Store(case.directory / 'state') as store:
        before = {table: H.rows(store, table) for table in H.TABLES}
        flow, _ = H.assemble(store, case.directory, NoNewDecisions(), case.configuration)
        owner = flow.episode_bindings.for_role('results')
        practical, receipt, original = assert_committed_practical_view_is_authenticated(case, owner, store)
        replay = asyncio.run(owner.execute(practical, receipt['tool_name'], receipt['arguments'], receipt['operation_key']))
        assert replay == {key: value for key, value in original.items() if key != 'pending_work_after_action'}
        for context, original in zip(case.result_contexts, case.public_outcomes):
            restored = owner.native_flux_balance_returns.context(context.episode_id)
            key = f'{H.RUN_ID}:{context.episode_id}:0'
            proof = owner.completion_for_action(restored, key)
            replay = asyncio.run(owner.execute(restored, 'execution.results.collect', {}, key))
            assert replay == {key: value for key, value in original.items() if key != 'pending_work_after_action'}
            assert owner.verify_completion(restored, proof)
        _, _, archive = asyncio.run(H.run_root(flow, case.configuration))
        assert archive == case.archive
        assert {table: H.rows(store, table) for table in H.TABLES} == before
    H.write(case.directory / 'CLOSED_REPLAY_CHECK.json', {'unchanged_tables': list(H.TABLES),
        'archive_equal': True, 'new_decisions': 0, 'new_optimizations': 0, 'new_workers': 0,
        'new_observations': 0, 'closed_credit_repriced': False})


@pytest.mark.skipif(not os.environ.get('HMMER_NATIVE_ORACLE_FBA716_RETAINED_CASE'),
    reason='requires the explicitly selected quiescent original217 records')
def test_retained_original_outcomes_follow_authenticated_result_contexts(monkeypatch):
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from gene_annotation_episode.execution_episodes import ExecutionEpisodes
    from gene_annotation_episode.tools import ToolRegistry

    directory = Path(os.environ['HMMER_NATIVE_ORACLE_FBA716_RETAINED_CASE'])
    assert directory.is_absolute()
    original_attempt = directory.parent
    original_receipt_path = original_attempt / 'receipt.json'
    collected = json.loads(original_receipt_path.read_bytes())
    assert collected['terminal'] and collected['quiescent']
    assert collected['handle'] == str(original_attempt / 'handle.json')
    configuration = json.loads((directory / 'fixture-configuration.json').read_bytes())
    recorded_case = json.loads((directory / 'CASE.json').read_bytes())
    saved = json.loads((directory / 'SAVED_CHECK.json').read_bytes())
    original_reports_path = original_attempt / 'case_reports.jsonl'
    original_reports = original_reports_path.read_bytes()
    replay_path = directory / 'CLOSED_REPLAY_CHECK.json'
    replay_proof = json.loads(replay_path.read_bytes())
    assert replay_proof['archive_equal'] and not replay_proof['closed_credit_repriced']
    assert all(replay_proof[name] == 0 for name in
        ('new_decisions', 'new_optimizations', 'new_workers', 'new_observations'))

    def pin(path):
        raw = path.read_bytes()
        return {'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}

    collected_pin, reports_pin = pin(original_receipt_path), pin(original_reports_path)

    def file_pins():
        return {str(path.relative_to(directory)): pin(path) for path in directory.rglob('*')
            if path.is_file() and not path.is_symlink() and path.name not in (
                'state.sqlite3', 'state.sqlite3-wal', 'state.sqlite3-shm', 'state.sqlite3-journal')}

    def all_rows(store):
        tables = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {table: sorted((tuple(row) for row in store.db.execute('SELECT * FROM ' + table)), key=repr)
            for table in tables}

    class NoAcquisition:
        def __getattr__(self, name):
            deny(name)

    monkeypatch.setattr(H, 'workflow_case', deny)
    monkeypatch.setattr(H, 'assemble', deny)
    monkeypatch.setattr(H, 'run_root', deny)
    monkeypatch.setattr('gene_annotation_episode.runtime.DecisionSource.call', deny)
    monkeypatch.setattr(ToolRegistry, 'execute', deny)
    monkeypatch.setattr(ToolRegistry, 'execute_async', deny)
    for name in ('prepare_job', 'start_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
        monkeypatch.setattr('gene_annotation_episode.native_lifecycle.' + name, deny)
    for name in ('capture_flux_balance_native_files', 'prepare_flux_balance_result_worker'):
        monkeypatch.setattr('gene_annotation_episode.native_flux_balance_results.' + name, deny)
    for target in ('gene_annotation_episode.native_flux_balance_local.prepare_local_flux_balance',
            'gene_annotation_episode.flux_balance_readers.parse_fba_capture',
            'gene_annotation_episode.flux_balance_sheet.populate_flux_balance_sheet',
            'gene_annotation_episode.flux_balance_calculations.calculate_flux_balance_sheet',
            'gene_annotation_episode.flux_balance_result_views.project_fba_result',
            'socket.create_connection', 'socket.socket.connect', 'socket.socket.connect_ex'):
        monkeypatch.setattr(target, deny)
    scientific_refs = {row['retained']['file']['artifact_ref'] for row in saved['original_receipt']['capture']['files']
        if row['retained'] is not None}
    for worker in H.worker_runs(directory):
        scientific_refs.update(row['observed']['artifact_ref'] for row in worker['capture']['outputs']
            if row['observed'] is not None)
    get_artifact = Store.get_artifact

    def controls_only(store, reference):
        assert reference not in scientific_refs, 'retained association audit read scientific artifact bytes'
        return get_artifact(store, reference)

    monkeypatch.setattr(Store, 'get_artifact', controls_only)
    with Store(directory / 'state') as store:
        before, files_before = all_rows(store), file_pins()
        records = EpisodeReturnRecords(store, H.RUN_ID, failure_prefix='retained_fba_workflow_')
        root = records.context(recorded_case['archive']['episode_id'])
        scientific, forwarded, _ = records._attempt(root, 0)
        native_context, native_form, _ = records._attempt(scientific, 1)
        redelivered_context, redelivered_form, _ = records._attempt(scientific, 2)
        saved_context, saved_form, _ = records._attempt(scientific, 3)
        assert redelivered_context == native_context and redelivered_form == native_form
        contexts, forms = [native_context, saved_context], [native_form, saved_form]
        assert forms == recorded_case['returned']
        assert forwarded == recorded_case['forwarded'] == {
            'measurements': [form['measurements'][0] for form in forms]}
        factory = configuration['factory']
        owner = ExecutionEpisodes(None, store=store, directory=directory / 'run', run_id=H.RUN_ID,
            resources=factory['resources'], initial_information=factory['initial_information'],
            tool_registry=ToolRegistry(store, clients=NoAcquisition(), job_limits=deepcopy(H.POLICY)),
            handoff_unit=factory['handoff_unit'], acquired_record_unit=factory['acquired_record_unit'],
            log_window_bytes=factory['log_window_bytes'], log_roles=factory['log_roles'])
        monkeypatch.setattr(type(owner.job_progress_provider.targets), 'observe_target', deny)
        reader = owner.native_flux_balance_results.receipts
        unordered = H.completed_fba_outcomes(store)
        # The actual217 SQL sort places saved credit0 before native credit2.
        # That order is preserved as evidence, not used as result association.
        assert [row['result']['intent']['episode_id'] for row in unordered] == [
            saved_context.episode_id, native_context.episode_id]
        associated = H.completed_fba_outcomes(store, result_contexts=contexts, receipt_reader=reader)
        public, credits = [], []
        for context, private, form in zip(contexts, associated, forms):
            row = store.db.execute('SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? '
                'AND decision_index=0', (H.RUN_ID, context.episode_id)).fetchone()
            public.append(json.loads(row['result']))
            credits.append(row['credit'])
            assert private['result']['intent']['episode_id'] == context.episode_id
            assert private['result']['intent']['operation_key'] == f'{H.RUN_ID}:{context.episode_id}:0'
            assert private['result']['facts'] == public[-1]['result']['facts']
            assert private['result']['delivery_complete'] == public[-1]['result']['delivery_complete'] is True
            assert private['result']['projection'] == form['measurements'][0]
            for field, source in H.SOURCES.items():
                assert form[field] == private['result']['facts'][source]
        original, recalculated = [row['result'] for row in associated]
        assert original == saved['original_receipt']
        assert original['acquired_population'] is not None and recalculated['acquired_population'] is None
        assert all(recalculated[name] is None for name in
            ('observation', 'native', 'capture', 'source_action_file', 'writer_closure_file'))
        assert recalculated['original_origins'] == [{'episode_id': native_context.episode_id,
            'operation_key': f'{H.RUN_ID}:{native_context.episode_id}:0'}]
        assert original['projection']['selector']['view'] == 'run_diagnostics'
        assert recalculated['projection']['selector']['view'] == 'reaction_fluxes'
        assert credits == [factory['acquired_record_unit'], 0]
        assert native_form['saved'] == saved_form['saved'] == [saved['sheet_file']]
        with pytest.raises(AssertionError, match='result action set differs'):
            H.completed_fba_outcomes(store, result_contexts=contexts[:1], receipt_reader=reader)
        with pytest.raises(AssertionError, match='duplicate requested FBA result context'):
            H.completed_fba_outcomes(store, result_contexts=[native_context, native_context], receipt_reader=reader)
        actual_rows = H.rows
        action_rows = actual_rows(store, 'runtime_actions')
        native_action, = [row for row in action_rows if row['episode_id'] == native_context.episode_id]
        with monkeypatch.context() as duplicated:
            duplicated.setattr(H, 'rows', lambda db, table: [*action_rows, native_action]
                if table == 'runtime_actions' else actual_rows(db, table))
            with pytest.raises(AssertionError, match='duplicate retained FBA outcome action'):
                H.completed_fba_outcomes(store, result_contexts=contexts, receipt_reader=reader)
        key = f'{H.RUN_ID}:{native_context.episode_id}:0'
        receipt_path = directory / 'run/execution-results' / digest([H.RUN_ID, native_context.episode_id]) \
            / 'native-flux-balance-actions' / digest(key) / 'receipt.json'
        changed = deepcopy(original)
        changed['intent']['operation_key'] += ':conflicting'
        actual_read = Path.read_bytes
        with monkeypatch.context() as conflicting:
            conflicting.setattr(Path, 'read_bytes', lambda path: json.dumps(changed).encode()
                if path == receipt_path else actual_read(path))
            with pytest.raises(AssertionError, match='outcome action identity conflict'):
                H.completed_fba_outcomes(store, result_contexts=contexts, receipt_reader=reader)
        assert all_rows(store) == before
        assert file_pins() == files_before
        assert original_reports_path.read_bytes() == original_reports
        assert pin(original_receipt_path) == collected_pin and pin(original_reports_path) == reports_pin
        verification = {'qualification': 'retained original217 association and custody audit only; '
            'no new Workflow, decision, optimizer, worker, recalculation, observation or grant; '
            'original failed assertions/artifacts and histories preserved; presentation defects remain separate',
            'source_contexts': [context.episode_id for context in contexts],
            'private_public_form_values_equal': True, 'operational_result_credits': credits,
            'native_acquired_population': original['acquired_population'],
            'saved_acquired_population': recalculated['acquired_population'],
            'original_closed_replay_proof': replay_proof, 'all_rows_unchanged': True,
            'row_counts': {name: len(rows) for name, rows in before.items()},
            'row_sha256': {name: digest(rows) for name, rows in before.items()},
            'original_file_pins': files_before, 'original_receipt_pin': collected_pin,
            'original_case_reports_pin': reports_pin, 'verification_complete': True}
    H.write(Path(os.environ['HMMER529_ATTEMPT']) / 'retained217-result-associations.json', verification)
