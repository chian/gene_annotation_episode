"""015 H4 Workflow verification; scripted choices and actual retained synthetic HIC v9.

Execute only through a retained bounded Workflow runner. Positive result authority is generated
by actual production commissions/actions/receipts/returns, never fixture rows.
"""
import asyncio
from copy import deepcopy
import hashlib
from importlib import import_module
from io import BytesIO
import json
import os
from pathlib import Path

import pytest
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.state import Store

F = import_module('verification.tool_graders_chromatin_hic_workflow_2026-10-27_459.fixture_helpers')


def deny(*args, **kwargs):
    raise AssertionError('received-only saved calculation or closed replay attempted native work, acquisition, or network')


def worker_output(run, role):
    captured, = [r for r in run['capture']['outputs'] if r['role'] == role]
    assert captured['capture']['outcome'] == 'verified', captured
    return captured['capture']['observed']


def contained_versions(value):
    if isinstance(value, dict):
        if isinstance(value.get('version'), str):
            yield value['version']
        for item in value.values():
            yield from contained_versions(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from contained_versions(item)


@pytest.fixture(scope='session', autouse=True)
def retained_fatal_diagnostics():
    """Retain fatal faults without a background periodic stack sampler."""
    import faulthandler
    with (Path(os.environ['WORKFLOW459_ATTEMPT']) / 'fatal-faults.txt').open('w') as stream:
        faulthandler.enable(file=stream, all_threads=True)
        try:
            yield
        finally:
            faulthandler.disable()


def assert_pairs(rows, *, threshold):
    assert [r['promoter_element_key'] for r in rows] == ['P', 'Q']
    p, q = [r.get('fields', r.get('measurements')) for r in rows]
    assert [p[k]['value'] for k in ('raw_contact', 'normalized_contact', 'expected_contact', 'fold_enrichment')] == [6, 6, 3.25, 24 / 13]
    assert p['expected_contact']['numerator'] == 6.5 and p['expected_contact']['denominator'] == 2
    assert p['fold_enrichment']['numerator'] == 6 and p['fold_enrichment']['denominator'] == 3.25
    assert p['above_fold_threshold']['value'] is threshold
    assert [q[k]['value'] for k in ('raw_contact', 'normalized_contact', 'expected_contact', 'fold_enrichment')] == [0, 0, 0, None]
    assert q['raw_contact']['state'] == 'observed'
    assert q['expected_contact']['numerator'] == 0 and q['expected_contact']['denominator'] == 1
    assert q['fold_enrichment']['reason'] == 'zero_denominator'
    assert q['above_fold_threshold']['value'] is None
    for row in rows:
        assert row['enhancer_element_key'] == 'E'
        assert row['enhancer_bin_id'] == 0
        assert row['promoter_bin_id'] == {'P': 2, 'Q': 3}[row['promoter_element_key']]
        assert row['qualifications']['data_extent'] == 'complete'


@pytest.fixture(scope='module')
def software():
    from gene_annotation_episode.native_chromatin_interaction_preparation import freeze_chromatin_software_binding
    import gene_annotation_episode.native_chromatin_interaction_driver as driver
    return freeze_chromatin_software_binding(module_root=str(Path(driver.__file__).parents[1]),
        snapshot_directory=str(Path(os.environ['WORKFLOW459_ATTEMPT']) / 'native_software'),
        python_executable=os.sys.executable, supported_formats=['hic_binary_v9'])


@pytest.fixture(scope='module')
def connected_case(tmp_path_factory, software):
    directory = tmp_path_factory.mktemp('hic459')
    evidence, patch = {}, pytest.MonkeyPatch()

    def before_saved(case):
        original, = F.worker_runs(directory)
        assert original['plan']['mode'] == 'native_result'
        evidence['original_worker'] = original
        evidence['bundle'] = deepcopy(case.bundle)
        evidence['sheet_bytes'] = case.store.get_artifact(case.bundle['sheet']['artifact_ref'])
        evidence['table_bytes'] = [case.store.get_artifact(f['artifact_ref']) for f in case.bundle['tables']]
        evidence['components_file'] = worker_output(original, 'components')
        evidence['components_bytes'] = case.store.get_artifact(evidence['components_file']['artifact_ref'])
        evidence['observations'] = F.rows(case.store, 'runtime_observations')
        evidence['completed_actions'] = [row for row in F.rows(case.store, 'runtime_actions') if row['result'] is not None]
        evidence['native_plans'] = {str(p): p.read_bytes() for p in case.workspace.rglob('chromatin-plan.json')}
        evidence['origins_before_saved'] = case.owner.native_chromatin_interaction_returns.authenticate_received_saved_bundle(
            case.science_context, case.bundle)
        preserved = {f['artifact_ref'] for f in (case.bundle['sheet'], *case.bundle['tables'])}
        removed = []

        def remove(path, kind):
            if path.is_file():
                raw = path.read_bytes()
                path.unlink()
                removed.append({'kind': kind, 'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})

        science_roles = {'original_contact', 'original_elements', 'original_metadata',
            'bins', 'contacts', 'weights', 'cell_states', 'dense_values'}
        for spec in case.provider.plan['outputs']:
            if spec['role'] not in science_roles:
                continue
            remove(Path(case.provider.plan['attempt_directory']) / spec['relative_path'], 'native_producer_scientific_copy')
            raw = case.provider.native_bytes.get(spec['file_key'])
            if raw is not None:
                sha = hashlib.sha256(raw).hexdigest()
                if 'artifact_' + sha not in preserved:
                    remove(case.store.path / 'artifacts' / sha[:2] / sha, 'retained_original_native_bytes')
        for item in case.provider.plan['requested_job']['native_chromatin_interactions']['input_bindings']:
            remove(Path(item['path']), 'original_caller_input')
        for reference in case.provider.initial_refs:
            if reference.startswith('artifact_') and reference not in preserved:
                sha = reference.removeprefix('artifact_')
                remove(case.store.path / 'artifacts' / sha[:2] / sha, 'original_caller_metadata_or_input')
        declared_absent = []
        sheet_tables = {row['table_key']: row for row in json.loads(evidence['sheet_bytes'])['data_tables']}
        for row in original['capture']['outputs']:
            if row['role'] in {'sheet', 'components', 'projection', 'table'}:
                capture = row['capture']
                path = Path(original['directory']) / capture['declared']['relative_path']
                file = capture['observed']
                if file is None:
                    # Sparse HIC has no dense-values file to remove. An absent
                    # representation is different from a failed present file.
                    assert row['role'] == 'table'
                    assert row['table_key'] in {'p0:dense_values', 'p1:dense_values'}
                    assert capture['outcome'] == 'declared_absent' and capture['failure'] is None
                    assert capture['declared']['state'] == 'absent'
                    assert capture['declared']['sha256'] is capture['declared']['size_bytes'] is None
                    descriptor = sheet_tables[row['table_key']]
                    assert descriptor['availability'] == 'not_native_representation' and descriptor['file'] is None
                    assert not path.exists()
                    declared_absent.append(row['table_key'])
                    continue
                assert capture['outcome'] == 'verified' and capture['failure'] is None
                remove(path, 'original_worker_scientific_copy')
                if file['artifact_ref'] not in preserved:
                    remove(F.artifact_path(case.store, file), 'unreceived_original_worker_artifact')
        assert declared_absent == ['p0:dense_values', 'p1:dense_values']
        assert removed and all(not Path(row['path']).exists() for row in removed)
        evidence['removed'], evidence['dispatches'] = removed, []
        evidence['declared_absent_tables'] = declared_absent
        F.write(directory / 'SAVED_PREPARATION.json', {
            'received_bundle': case.bundle, 'removed': removed,
            'declared_absent_tables': declared_absent,
            'original_worker_directory': original['directory'],
            'origins_before_saved': evidence['origins_before_saved'],
            'original_observations': evidence['observations'],
            'original_completed_actions': evidence['completed_actions']})
        from gene_annotation_episode import native_lifecycle
        actual_prepare = native_lifecycle.prepare_job

        def saved_worker_only(command, **kwargs):
            assert command[1:5] == ['-B', '-S', '-m', 'gene_annotation_episode.chromatin_interaction_result_worker']
            plan = json.loads(Path(command[-1]).read_bytes())
            assert plan['mode'] == 'saved_sheet_recalculation'
            assert set(plan) == {'version', 'mode', 'directory', 'sheet_bundle', 'selector'}
            assert plan['selector']['saved_sheet_bundle'] == case.bundle
            assert plan['sheet_bundle']['sheet']['file'] == case.bundle['sheet']
            assert [r['file'] for r in plan['sheet_bundle']['tables']] == case.bundle['tables']
            assert kwargs['policy'].to_dict() == F.POLICY
            evidence['dispatches'].append({'command': list(command), 'plan': deepcopy(plan)})
            F.write(directory / 'SAVED_DISPATCHES.json', evidence['dispatches'])
            return actual_prepare(command, **kwargs)

        patch.setattr(native_lifecycle, 'prepare_job', saved_worker_only)
        patch.setattr('gene_annotation_episode.native_chromatin_interaction_results.capture_chromatin_native_files', deny)
        patch.setattr(type(case.owner.job_progress_provider.targets), 'observe_target', deny)
        patch.setattr('gene_annotation_episode.chromatin_hic_inputs.read_hic_contacts', deny)
        patch.setattr('socket.create_connection', deny)
        patch.setattr('socket.socket.connect', deny)
        patch.setattr('socket.socket.connect_ex', deny)

    try:
        case = F.workflow_case(directory, software, before_saved=before_saved)
        case.saved_evidence = evidence
        F.write(directory / 'SAVED_CHECK.json', {key: value for key, value in evidence.items()
            if key not in {'sheet_bytes', 'table_bytes', 'components_bytes', 'native_plans'}})
    finally:
        patch.undo()
    try:
        yield case
    finally:
        case.store.close()


def test_selected_tool_actual_local_native_and_exact_typed_return(connected_case):
    import numpy as np

    case, saved = connected_case, connected_case.saved_evidence
    assert {role: len(rows) for role, rows in case.by_role.items()} == {
        'annotation': 1, 'scientific_process': 1, 'launch': 1, 'launch_local': 1, 'results': 2}
    assert 'analyze_chromatin_interactions' not in case.tools.catalog()
    information, = plain(case.scientific_context.assignment)['selection']['child_tool_info']
    assert information['name'] == 'analyze_chromatin_interactions' and information['resources'] == 'local'
    assert information['description'] and information['instructions']
    assert case.provider.plan['requested_job']['native_chromatin_interactions'] == case.job
    assert case.provider.plan['policy'] == F.POLICY
    assert case.job['request']['contact']['format'] == 'hic_binary_v9'
    assert case.job['request']['contact']['group_path'] is None
    assert case.job['request']['contact']['file']['sha256'] == F.HIC['weighted']['sha256']
    assert case.job['request']['normalization'] == {
        'kind': 'precomputed_weighted', 'weight_column': 'SYNTHETIC_DIVISIVE', 'convention': 'divisive'}
    assert case.provider.native_outcome['returncode'] == 0
    assert [(row['element_key'], row['source_data_row'], row['anchor']['position_bp'])
        for row in case.job['request']['elements']['assignments']] == [('E', 0, 1), ('P', 1, 21), ('Q', 2, 31)]
    native = json.loads(case.provider.native_bytes['bundle'])
    assert native['extraction']['format'] == 'hic_binary_v9'
    header = native['extraction']['native_metadata']['hic']
    assert header['source_version'] == 9 and header['genome_id'] == F.HIC['weighted']['genome_id']
    assert header['bin_id_space'] == 'chromosome_local'
    assert [p['population_key'] for p in native['extraction']['populations']] == ['p0', 'p1']
    assert all(p['extent'] == 'complete' for p in native['extraction']['populations'])
    assert case.provider.native_bytes['p0.contacts'] == case.provider.native_bytes['p1.contacts']
    sheet = json.loads(saved['sheet_bytes'])
    components = json.loads(saved['components_bytes'])
    assert sheet['request'] == case.job['request']
    assert sheet['request']['supplied_metadata']['reference']['assembly_label'] == F.HIC['weighted']['genome_id']
    assert len(sheet['data_tables']) == 10
    assert saved['bundle']['tables'] == [d['file'] for d in sheet['data_tables'] if d['file'] is not None]
    assert len(saved['bundle']['tables']) == 8
    assert len({canonical(file) for file in saved['bundle']['tables']}) == 4
    assert saved['bundle']['tables'][:4] == saved['bundle']['tables'][4:]
    tables = {d['role']: d['file'] for d in sheet['data_tables'] if d['population_key'] == 'p0'}
    bins = case.store.get_artifact(tables['bins']['artifact_ref']).decode().splitlines()
    assert bins == ['bin_id\tchromosome_index\tstart_bp\tend_bp',
        '0\t0\t0\t10', '1\t0\t10\t20', '2\t0\t20\t30', '3\t0\t30\t40']
    weights = np.load(BytesIO(case.store.get_artifact(tables['weights']['artifact_ref'])), allow_pickle=False)
    assert weights.tolist() == [1, 2, 1, 2]
    contacts = np.load(BytesIO(case.store.get_artifact(tables['contacts']['artifact_ref'])), allow_pickle=False)
    assert contacts.tolist() == [(0, 0, 4, 0, 0), (0, 1, 2, 0, 4), (0, 2, 6, 0, 8),
        (1, 1, 4, 0, 5), (1, 2, 2, 0, 9), (1, 3, 2, 0, 13),
        (2, 2, 4, 0, 10), (2, 3, 2, 0, 14), (3, 3, 4, 0, 15)]
    assert [p['population_key'] for p in components['contact']['populations']] == ['p0', 'p1']
    for population in components['contact']['populations']:
        assert_pairs(population['pairs'], threshold=False)
    first, second = [form['chromatin'][0] for form in case.returned]
    for projection, threshold in ((first, False), (second, True)):
        assert projection['population_keys'] == ['p1'] and projection['requested_fields'] == F.FIELDS
        assert {r['population_key'] for r in projection['rows']} == {'p1'}
        assert_pairs(projection['rows'], threshold=threshold)
        assert projection['page'] == {'offset': 0, 'returned_count': 2, 'total_row_count': 2, 'has_more': False}
    assert case.forwarded == {'chromatin': [first, second]}
    assert case.owner.native_chromatin_interaction_returns.facts(case.root_context, case.parent_form) == {
        F.PROJECTION_SOURCE: [first, second]}
    original = case.outcomes[0]['result']
    assert original['acquired_population'] == digest(case.provider.plan['identity'])
    assert [p['population_key'] for p in original['sheet_evidence']['populations']] == ['p0', 'p1']
    assert case.owner.native_chromatin_interaction_results.receipts.original_acquisition_complete(original)
    for call in case.provider.calls:
        if case.contexts[call['episode_id']].role in {'annotation', 'scientific_process'}:
            assert not {'chromatin_interaction_sheet_v1', 'chromatin_interaction_components_v1'}.intersection(
                contained_versions(call['context']))
    commissions = [json.loads(row['action']) for row in F.rows(case.store, 'runtime_actions')
        if json.loads(row['action'])['kind'] == 'episode_child']
    assert [sum(row['role'] == role for row in commissions) for role in
        ('scientific_process', 'launch', 'launch_local', 'results')] == [1, 1, 1, 2]
    for context, form in zip(case.result_contexts, case.returned):
        groups = case.owner.native_chromatin_interaction_results.own_fact_groups(context, verify_artifacts=False)
        assert form == {'chromatin': groups[F.PROJECTION_SOURCE], 'saved': groups[F.SAVED_SOURCE],
            'failures': groups[F.FAILURE_SOURCE], 'completed': True}


def test_received_bundle_recalculates_without_native_inputs_or_producer_copies(connected_case):
    case, saved = connected_case, connected_case.saved_evidence
    assert len(saved['dispatches']) == 1
    assert saved['dispatches'][0]['plan']['selector']['parameters']['contact']['fold_threshold'] == 1
    assert saved['origins_before_saved'] == ({'episode_id': case.result_contexts[0].episode_id,
        'operation_key': f'{F.RUN_ID}:{case.result_contexts[0].episode_id}:0'},)
    recalculated = case.outcomes[1]['result']
    assert recalculated['acquired_population'] is None and recalculated['observation'] is None and recalculated['capture'] is None
    assert case.returned[0]['saved'] == case.returned[1]['saved'] == [saved['bundle']]
    assert case.store.get_artifact(saved['bundle']['sheet']['artifact_ref']) == saved['sheet_bytes']
    assert [case.store.get_artifact(f['artifact_ref']) for f in saved['bundle']['tables']] == saved['table_bytes']
    assert all(not Path(row['path']).exists() for row in saved['removed'])
    assert {str(p): p.read_bytes() for p in case.workspace.rglob('chromatin-plan.json')} == saved['native_plans']
    assert sorted(r['plan']['mode'] for r in F.worker_runs(case.directory)) == ['native_result', 'saved_sheet_recalculation']
    old, new = [form['chromatin'][0]['rows'] for form in case.returned]
    for before, after in zip(old, new):
        assert {k: v for k, v in before['fields'].items() if k != 'above_fold_threshold'} == {
            k: v for k, v in after['fields'].items() if k != 'above_fold_threshold'}
    assert all(row in F.rows(case.store, 'runtime_observations') for row in saved['observations'])
    assert all(row in F.rows(case.store, 'runtime_actions') for row in saved['completed_actions'])


def test_projection_only_root_has_no_implicit_saved_bundle_authority(connected_case):
    case, bundle = connected_case, connected_case.saved_evidence['bundle']
    reader = case.owner.native_chromatin_interaction_returns
    assert reader.authenticate_received_saved_bundle(case.scientific_context, bundle) == tuple(
        {'episode_id': context.episode_id, 'operation_key': f'{F.RUN_ID}:{context.episode_id}:0'} for context in case.result_contexts)
    references = dict.fromkeys(file['artifact_ref'] for file in (bundle['sheet'], *bundle['tables']))
    for reference in references:
        assert reader.resolve_received(case.scientific_context, reference, 'artifact')
        assert not reader.resolve_received(case.root_context, reference, 'artifact')
        for namespace in ('artifact', None):
            assert case.owner.resolve_received_reference(case.scientific_context, reference, namespace) is True
            assert case.owner.resolve_received_reference(case.root_context, reference, namespace) is False
    with pytest.raises(ValueError, match='saved_bundle_not_received'):
        reader.authenticate_received_saved_bundle(case.root_context, bundle)
    facts = json.loads(case.flow.journal.row('runtime_forms', case.scientific_context.episode_id)['facts'])
    assert facts[F.PROJECTION_SOURCE] == case.forwarded['chromatin']
    assert len(facts['chromatin_received_report_prefix']['attempts']) == 2
    assert F.SAVED_SOURCE not in {r.get('x-source') for r in case.parent_form['properties'].values()}


def test_actual_action_counts_credit_and_immediate_zero_future_expectation(connected_case):
    case = connected_case
    for record in case.records:
        context = case.contexts[record['episode_id']]
        actions = [r for r in F.rows(case.store, 'runtime_actions') if r['episode_id'] == context.episode_id]
        observations = [r for r in F.rows(case.store, 'runtime_observations') if r['episode_id'] == context.episode_id]
        assert len(actions) == len(observations) == record['units_consumed'] == case.provider.turns[context.episode_id]
        if context.role in {'launch', 'launch_local', 'results'}:
            assert len(actions) == 1
            estimate = record['controller_state']['estimate']
            assert estimate['expected_next_gain'] == NumericBand.exact(0).as_record()
            assert estimate['provenance']['version'] == 'verified_practical_endpoint_yield_v1'
            proof = case.owner.completion_for_action(context, f'{F.RUN_ID}:{context.episode_id}:0')
            assert proof is not None and case.owner.verify_completion(context, proof)
    assert [F.history(row) for row in case.by_role['launch_local']] == [[7]]
    assert [F.history(row) for row in case.by_role['launch']] == [[3]]
    assert [F.history(row) for row in case.by_role['results']] == [[2], [0]]
    assert F.history(case.by_role['scientific_process'][0]) == [0, 0, 0]
    assert F.history(case.by_role['annotation'][0]) == [0]
    assert case.store.count('annotation') == 0


def test_closed_workflow_and_results_replay_without_new_decisions_or_work(connected_case, monkeypatch):
    case = connected_case
    for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
        monkeypatch.setattr('gene_annotation_episode.native_lifecycle.' + name, deny)
    for name in ('capture_chromatin_native_files', 'prepare_chromatin_result_worker'):
        monkeypatch.setattr('gene_annotation_episode.native_chromatin_interaction_results.' + name, deny)
    monkeypatch.setattr(type(case.owner.job_progress_provider.targets), 'observe_target', deny)
    monkeypatch.setattr('gene_annotation_episode.chromatin_hic_inputs.read_hic_contacts', deny)
    monkeypatch.setattr('socket.create_connection', deny)
    monkeypatch.setattr('socket.socket.connect', deny)
    monkeypatch.setattr('socket.socket.connect_ex', deny)

    class NoNewDecisions:
        async def complete(self, *args, **kwargs):
            raise AssertionError('closed Workflow replay requested a new decision')
        async def release(self, episode_id):
            pass

    with Store(case.directory / 'state') as store:
        before = {table: F.rows(store, table) for table in F.TABLES}
        retained = {str(p): p.read_bytes() for p in (case.directory / 'run').rglob('*.json')}
        flow, _ = F.assemble(store, case.directory, NoNewDecisions(), case.configuration)
        owner = flow.episode_bindings.for_role('results')
        proofs = []
        for original_context, original_outcome in zip(case.result_contexts, case.outcomes):
            context = owner.native_chromatin_interaction_returns.context(original_context.episode_id)
            key = f'{F.RUN_ID}:{context.episode_id}:0'
            proof = owner.completion_for_action(context, key)
            replay = asyncio.run(owner.execute(context, 'execution.results.collect', {}, key))
            assert replay == {k: v for k, v in original_outcome.items() if k != 'pending_work_after_action'}
            assert owner.completion_for_action(context, key) == proof and owner.verify_completion(context, proof)
            proofs.append(proof)
        _, _, archive = asyncio.run(F.run_root(flow, case.configuration))
        assert archive == case.archive
        assert {table: F.rows(store, table) for table in F.TABLES} == before
        assert {str(p): p.read_bytes() for p in (case.directory / 'run').rglob('*.json')} == retained
        assert all(not Path(row['path']).exists() for row in case.saved_evidence['removed'])
        F.write(case.directory / 'REPLAY_CHECK.json', {'reopened_store': True, 'new_decisions': 0,
            'new_native_or_calculation_workers': 0, 'unchanged_tables': list(F.TABLES),
            'unchanged_archive': True, 'original_completion_proofs': proofs})


def test_native_nonzero_wrong_population_preserves_p0_and_one_acquisition(tmp_path, software):
    case = F.workflow_case(tmp_path / 'wrong_population', software, partial=True)
    try:
        assert case.provider.native_outcome['returncode'] == 1
        assert case.job['request']['populations'] == [
            {'population_key': 'p0', 'chromosome': 'chrA', 'start_bp': 0, 'end_bp': 40},
            {'population_key': 'p1', 'chromosome': 'chrNotPresent', 'start_bp': 0, 'end_bp': 40}]
        native = json.loads(case.provider.native_bytes['bundle'])
        assert [p['extent'] for p in native['extraction']['populations']] == ['complete', 'unavailable']
        returned, = case.returned
        projection, = returned['chromatin']
        assert not returned['completed'] and returned['failures']
        assert projection['population_keys'] == ['p0', 'p1']
        assert_pairs([r for r in projection['rows'] if r['population_key'] == 'p0'], threshold=False)
        for row in (r for r in projection['rows'] if r['population_key'] == 'p1'):
            assert all(value['value'] is None for value in row['fields'].values())
            assert row['qualifications']['data_extent'] != 'complete'
        assert any(r['population_key'] == 'p1' and r['code'] == 'population_unavailable'
            and (r['field_path'] or r['locator']) for r in returned['failures'])
        receipt = case.outcomes[0]['result']
        assert receipt['observation']['state'] == 'failed'
        assert receipt['observation']['returncode'] == 1
        assert receipt['observation']['failure_code'] == 'native_nonzero_returncode'
        assert receipt['acquired_population'] == digest(case.provider.plan['identity'])
        assert [p['extent'] for p in receipt['sheet_evidence']['populations']] == ['complete', 'unavailable']
        assert not case.owner.native_chromatin_interaction_results.receipts.original_acquisition_complete(receipt)
        context, = case.result_contexts
        assert case.owner.native_chromatin_interaction_results.completion(context) is None
        assert case.owner.completion_for_action(context, f'{F.RUN_ID}:{context.episode_id}:0') is None
        actions = [json.loads(r['action']) for r in F.rows(case.store, 'runtime_actions') if r['episode_id'] == context.episode_id]
        assert [r['tool'] for r in actions] == ['execution.results.collect', 'execution.results.status']
        assert len([r for r in F.rows(case.store, 'runtime_observations') if r['episode_id'] == context.episode_id]) == 2
        assert F.history(case.by_role['results'][0]) == [2, 0]
        estimate = case.by_role['results'][0]['controller_state']['estimate']
        assert estimate['provenance'].get('version') != 'verified_practical_endpoint_yield_v1'
        assert estimate['expected_next_gain'] != NumericBand.exact(0).as_record()
        assert len(F.worker_runs(case.directory)) == len(list(case.workspace.rglob('native.json'))) == 1
    finally:
        case.store.close()


def test_true_present_zero_block_is_complete_measured_zero_with_immediate_zero_future_credit(tmp_path, software):
    import numpy as np

    case = F.workflow_case(tmp_path / 'present_zero_block', software, empty=True)
    try:
        assert case.provider.native_outcome['returncode'] == 0
        assert case.job['request']['contact']['file']['sha256'] == F.HIC['empty']['sha256']
        original, = [row['result'] for row in case.outcomes]
        returned, = case.returned
        bundle, = returned['saved']
        sheet = json.loads(case.store.get_artifact(bundle['sheet']['artifact_ref']))
        native = json.loads(case.provider.native_bytes['bundle'])
        assert native['extraction']['native_metadata']['hic']['genome_id'] == F.HIC['empty']['genome_id']
        assert [p['population_key'] for p in sheet['populations']] == ['p0', 'p1']
        for population in sheet['populations']:
            assert population['extent'] == 'complete' and population['bin_count'] == 4
            evidence = population['read_evidence']
            assert all(evidence[k] == 'complete' for k in ('axes_extent', 'index_extent', 'selected_records_extent'))
            assert evidence['implicit_zero_semantics'] == 'validated_sparse_absence'
            assert not evidence['failed_block_ids']
            assert evidence['hic']['matrix_key'] == '0_0'
            assert evidence['hic']['declared_block_count'] == 0 and evidence['hic']['blocks'] == []
            counts = population['raw_cell_population']
            assert counts['stored_rows'] == counts['validated_observed_row_count'] == counts['explicit_zero_rows'] == 0
            assert counts['implicit_zero_directed_cells'] == 16 and counts['unavailable_directed_cells'] == 0
            descriptor, = [d for d in sheet['data_tables']
                if d['population_key'] == population['population_key'] and d['role'] == 'contacts']
            assert descriptor['availability'] == 'present' and descriptor['shape'] == [0]
            assert descriptor['file'] in bundle['tables'] and descriptor['file']['size_bytes'] > 0
            raw = case.store.get_artifact(descriptor['file']['artifact_ref'])
            assert raw == case.provider.native_bytes[population['population_key'] + '.contacts']
            table = np.load(BytesIO(raw), allow_pickle=False)
            assert table.shape == (0,) and set(table.dtype.names) == {'bin1_id', 'bin2_id', 'value', 'source_block', 'source_row'}
            assert case.owner.native_chromatin_interaction_results.receipts._population_acquired(original, population)
        assert len(bundle['tables']) == 6 and bundle['tables'][:3] == bundle['tables'][3:]
        assert returned['completed']
        worker, = F.worker_runs(case.directory)
        components = json.loads(case.store.get_artifact(worker_output(worker, 'components')['artifact_ref']))
        for population in components['contact']['populations']:
            assert [row['promoter_element_key'] for row in population['pairs']] == ['P', 'Q']
            for row, denominator in zip(population['pairs'], (2, 1)):
                fields = row['measurements']
                assert fields['raw_contact']['value'] == fields['expected_contact']['value'] == 0
                assert fields['normalized_contact']['value'] is None and fields['normalized_contact']['state'] == 'not_measured'
                assert fields['raw_contact']['state'] == 'observed'
                assert fields['expected_contact']['numerator'] == 0 and fields['expected_contact']['denominator'] == denominator
                assert fields['fold_enrichment']['value'] is None and fields['fold_enrichment']['reason'] == 'zero_denominator'
                assert fields['above_fold_threshold']['value'] is None
                assert row['qualifications']['data_extent'] == 'complete'
        projection, = returned['chromatin']
        assert projection['population_keys'] == ['p1'] and projection['requested_fields'] == F.FIELDS
        assert [row['fields']['raw_contact']['value'] for row in projection['rows']] == [0, 0]
        assert original['acquired_population'] == digest(case.provider.plan['identity'])
        assert case.owner.native_chromatin_interaction_results.receipts.original_acquisition_complete(original)
        assert [F.history(record) for record in case.by_role['results']] == [[2]]
        context, = case.result_contexts
        record, = case.by_role['results']
        assert record['units_consumed'] == case.provider.turns[context.episode_id] == 1
        assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert record['controller_state']['estimate']['provenance']['version'] == 'verified_practical_endpoint_yield_v1'
        proof = case.owner.completion_for_action(context, f'{F.RUN_ID}:{context.episode_id}:0')
        assert proof is not None and case.owner.verify_completion(context, proof)
        assert len(list(case.workspace.rglob('native.json'))) == 1 and worker['plan']['mode'] == 'native_result'
    finally:
        case.store.close()


