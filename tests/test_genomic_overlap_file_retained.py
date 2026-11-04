"""Continue the actual interrupted521 owner without another native producer.

This opt-in test changes the original active journal through normal Workflow
APIs. The five failed result-worker actions remain historical facts. Only a new
collect and the subsequently selected saved-sheet calculation may start workers.
"""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.execution_episodes import RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.genomic_overlap_return_views import FAILURE_SOURCE, PROJECTION_SOURCE
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from test_interval_pending_results import _fixture
from test_interval_results_presentation import _canonical, _inventory, _session, _sha, _tables


PREFIX = Path('/home/chia/repos/gene_annotation_episode/runs/'
    'check521_genomic_file_native_and_admission_repair/tmp/'
    'test_file_only_native_saved_an0/file-only-workflow')
STOPPED_SHA256 = '19c7277c73301dd328263d5f42ee4526ddd98cdfc9929c5dcdce285874768c07'
ORIGINAL_MAIN_SHA256 = '065e173a005a7c957bcc28a1ab3fa693bb446ed420d830510ba6a0651cd71e23'
ORIGINAL_WAL_SHA256 = '08f10403707f06a75aac890ff92b26def006ced504a8b332cfe070ed0ada45fd'
NATIVE_PINS = {
    'plan': '14cdbbc063d0592f49c0a9818a727fb63a75ab8c94c855ad1356d9cc2ce01023',
    'handle': 'fd1365b0ecd609d1c1c50a6e252cc80f97bc602765f3ec4c92655831f8ef06cf',
    'bundle': '89bbb384a1e61abcff4e6b66b4aa58dd41bb1c13819f8e8cf1d682b258e535d6',
    'stdout': '5c8778e4a3a09e32385673227f93432d9d6470d9691b874bcd343430a81566cb',
}


def _forbidden(*args, **kwargs):
    raise AssertionError('retained521 continuation attempted a new producer, freeze, acquisition or real model')


def _write(path, value):
    with path.open('w') as handle:
        handle.write(json.dumps(value, indent=2, allow_nan=False) + '\n')
        handle.flush()
        os.fsync(handle.fileno())


def _snapshot(database):
    # WAL-aware read of this explicitly selected owned active Store. Immutable
    # main-only reads would lose its actual committed521 prefix.
    connection = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        return _tables(connection)
    finally:
        connection.close()


def _records(snapshot, table):
    value = snapshot[table]
    return [dict(zip(value['columns'], row)) for row in value['rows']]


def _history(before, after, *, active_episodes, pending_actions):
    """Allow only normal completion fields of the original active prefix."""
    assert set(after) == set(before)
    summaries = {}
    for name, original in before.items():
        current = after[name]
        assert current['sql'] == original['sql'] and current['columns'] == original['columns']
        old, new = _records(before, name), _records(after, name)
        if name == 'runtime_episodes':
            by_key = {(row['run_id'], row['episode_id']): row for row in new}
            for row in old:
                actual = by_key[(row['run_id'], row['episode_id'])]
                if row['episode_id'] in active_episodes:
                    assert row['state'] == 'active' and row['completion'] is row['archive'] is None
                    assert actual['state'] == 'yielded' and actual['completion'] is not None and actual['archive'] is not None
                    assert {k: v for k, v in actual.items() if k not in {'state', 'completion', 'archive'}} == {
                        k: v for k, v in row.items() if k not in {'state', 'completion', 'archive'}}
                else:
                    assert actual == row
        elif name == 'runtime_actions':
            by_key = {(row['run_id'], row['episode_id'], row['decision_index']): row for row in new}
            for row in old:
                key = (row['run_id'], row['episode_id'], row['decision_index'])
                actual = by_key[key]
                if key in pending_actions:
                    assert row['result'] is None and actual['result'] is not None
                    assert {k: v for k, v in actual.items() if k not in {'result', 'credit', 'timing'}} == {
                        k: v for k, v in row.items() if k not in {'result', 'credit', 'timing'}}
                else:
                    assert actual == row
        else:
            retained = {_canonical(row) for row in new}
            assert all(_canonical(row) in retained for row in old), name
        summaries[name] = dict(before_rows=len(old), after_rows=len(new), added_rows=len(new) - len(old),
            before_sha256=_sha(_canonical(original['rows']).encode()),
            after_sha256=_sha(_canonical(current['rows']).encode()))
    return summaries


def _guards(monkeypatch, helper, prefix):
    from gene_annotation_episode import native_genomic_overlap_driver as driver
    from gene_annotation_episode import native_genomic_overlap_local as local
    from gene_annotation_episode import native_lifecycle
    monkeypatch.setattr(local, 'prepare_local_genomic_overlap', _forbidden)
    monkeypatch.setattr(driver, 'run_genomic_overlap_driver', _forbidden)
    monkeypatch.setattr(driver, '_native_call', _forbidden)
    monkeypatch.setattr(helper.NATIVE, 'software', _forbidden)
    monkeypatch.setattr(helper, 'prepare_scientific_binding', _forbidden)
    monkeypatch.setattr(ScientificProcessLibrary, 'freeze', _forbidden)
    monkeypatch.setattr(ScientificToolLibrary, 'freeze', _forbidden)
    monkeypatch.setattr(PublicClients, '_http', _forbidden)
    monkeypatch.setattr(_SessionConnection, 'complete', _forbidden)
    for name in ('urllib.request.urlopen', 'urllib.request.build_opener', 'socket.create_connection'):
        monkeypatch.setattr(name, _forbidden)
    actual_prepare, actual_start = native_lifecycle.prepare_job, native_lifecycle.resume_start
    actual_prepared_start = native_lifecycle.start_prepared
    prepared = []

    def prepare(command, *, cwd, **kwargs):
        directory = Path(cwd)
        assert directory.is_relative_to(prefix / 'run/execution-results') and directory.name == 'worker'
        assert list(command) == [str(directory / 'runtime/python'), '-B', '-S', '-m',
            'gene_annotation_episode.genomic_overlap_result_worker', str(directory / 'plan.json')]
        plan = json.loads((directory / 'plan.json').read_bytes())
        assert plan['mode'] == ('native_result' if not prepared else 'saved_sheet_recalculation')
        assert len(prepared) < 2, 'no retry or repeated collect is selected'
        prepared.append(dict(directory=str(directory), mode=plan['mode'], command=list(command)))
        return actual_prepare(command, cwd=cwd, **kwargs)

    def start(handle, *args, **kwargs):
        assert str(Path(handle.path).parent) in {row['directory'] for row in prepared}
        return actual_start(handle, *args, **kwargs)

    def prepared_start(handle, *args, **kwargs):
        assert str(Path(handle.path).parent) in {row['directory'] for row in prepared}
        return actual_prepared_start(handle, *args, **kwargs)

    monkeypatch.setattr(native_lifecycle, 'prepare_job', prepare)
    monkeypatch.setattr(native_lifecycle, 'resume_start', start)
    monkeypatch.setattr(native_lifecycle, 'start_prepared', prepared_start)
    return prepared


def test_continue_original521_native_result_saved_builder_and_typed_parent(tmp_path, monkeypatch):
    if os.environ.get('HMMER_NATIVE_ORACLE_OVERLAP_FILE_RETAINED') != '1':
        pytest.skip('requires explicit continuation of the stopped original521 File-only owner')
    stopped_path = PREFIX.parents[2] / 'stopped_verification_audit.json'
    stopped_raw = stopped_path.read_bytes()
    assert _sha(stopped_raw) == STOPPED_SHA256
    stopped = json.loads(stopped_raw)
    assert stopped['native_producer_attempts'] == 1 and stopped['native_returncode'] == 0
    assert stopped['failed_result_workers'] == 5 and stopped['whole_native_workflow_test_passed'] is False
    assert stopped['actual_top_unit']['ControlGroup'] == ''
    assert all(row['terminal'] and row['quiescent'] for row in stopped['child_lifecycle'])
    database = PREFIX / 'state/state.sqlite3'
    assert _sha(database.read_bytes()) == ORIGINAL_MAIN_SHA256
    assert _sha(Path(str(database) + '-wal').read_bytes()) == ORIGINAL_WAL_SHA256
    original_files = _inventory(PREFIX)
    before = _snapshot(database)
    episodes = _records(before, 'runtime_episodes')
    by_role = {json.loads(row['path'])[-1][0]: row for row in episodes}
    root_row, science_row, results_row = (by_role[name] for name in ('annotation', 'scientific_process', 'results'))
    assert len(episodes) == 5 and all(row['state'] == 'active' for row in (root_row, science_row, results_row))
    root_request, science_request, results_request = (json.loads(row['request'])
        for row in (root_row, science_row, results_row))
    run_id = root_row['run_id']
    assert {row['run_id'] for row in episodes} == {run_id}
    actions = _records(before, 'runtime_actions')
    failed = sorted((row for row in actions if row['episode_id'] == results_row['episode_id']),
        key=lambda row: row['decision_index'])
    assert [row['decision_index'] for row in failed] == list(range(5))
    receipts = [json.loads(row['result'])['result'] for row in failed]
    assert all(not value['delivery_complete'] and value['worker_execution']['returncode'] == 1 for value in receipts)
    assert all(json.loads(row['action']) == dict(kind='tool', tool='execution.results.collect', arguments={}) for row in failed)
    target = deepcopy(receipts[0]['intent']['target'])
    assert all(value['intent']['target'] == target for value in receipts)
    native_assignment = results_request['message']['episode_assignment']
    assert all(value['intent']['assignment'] == native_assignment for value in receipts)
    native_selector = deepcopy(native_assignment['selector'])
    assert native_selector['mode'] == 'native_result' and native_selector['parameters']['minimum_overlap_bp'] == 1
    handoff = native_assignment['handoff_ref']
    assert handoff == target['handle'] == 'source_6aad56cf475ede7ec070fd79'
    plan_path = Path(target['execution_id']).parent / 'genomic-overlap-plan.json'
    native_plan = json.loads(plan_path.read_bytes())
    assert native_plan['requested_job'] == target['assignment']['requested_job']
    assert native_plan['identity']['requested_job_sha256'] == digest(native_plan['requested_job'])
    attempt = Path(native_plan['attempt_directory'])
    native_files = dict(plan=plan_path, handle=Path(target['execution_id']),
        bundle=attempt / 'bundle.json', stdout=attempt / 'overlap/pairs/p0/overlap.wo.tsv')
    assert {role: _sha(path.read_bytes()) for role, path in native_files.items()} == NATIVE_PINS
    assert native_files['stdout'].read_bytes() == b'chr1\t0\t10\ts0_r0\tchr1\t5\t15\ts1_r0\t5\n'
    practical_row, = [row for row in episodes if json.loads(row['path'])[-1][0] == 'launch_local']
    assert json.loads(practical_row['request'])['message']['episode_assignment'] == target['assignment']
    job = native_plan['requested_job']['native_genomic_overlap']
    request = job['request']
    assert all('source_ref' not in spec['source'] for spec in request['region_sets'])
    scope, question = root_request['message']['scope'], root_request['goal']['objective']
    assert scope == science_request['message']['scope'] == results_request['message']['scope']
    assert 'minimum_overlap_bp=6' in question
    assert science_request['message']['episode_assignment']['context']['supplied_genomic_overlap_request'] == request
    binding = science_request['message']['scientific_process']['mechanics_binding']
    helper = _fixture(dict(name='overlap_complete'), monkeypatch)
    assert helper.RUN_ID == run_id
    prepared = _guards(monkeypatch, helper, PREFIX)
    initial = [spec['source']['file']['artifact_ref'] for spec in request['region_sets']]
    factory = ExecutionServiceFactory({target['resource_id']: dict(kind=target['resource_kind'],
        workspace=target['assignment']['workspace'], policy=deepcopy(native_plan['policy']),
        native_genomic_overlap=[dict(operation=request['operation'], mode=request['mode'],
            software=deepcopy(job['software']))])}, {}, 3, 2, 1, log_window_bytes=128)
    configuration = dict(factory=factory.as_record(), scientific_binding=deepcopy(binding),
        goal=question, scope=deepcopy(scope), initial_refs=initial, saved=True, failure=None)
    full_form = results_request['report_contract']['measurements']['schema']
    parent_form = science_request['report_contract']['measurements']['schema']
    session = _session(tmp_path / 'current-presentation')
    proof_path = tmp_path / 'GENOMIC_OVERLAP_RETAINED_CONTINUATION.json'
    proof = dict(version='genomic_overlap_retained_continuation_v1', passed=False,
        original_prefix=str(PREFIX), stopped_audit_sha256=STOPPED_SHA256, native_pins=NATIVE_PINS,
        original_failed_action_count=len(failed), original_native_reexecuted=False,
        current_native_full_builder_verified=False, current_saved_full_builder_verified=False,
        restored_configuration=configuration, before_table_counts={name: len(value['rows'])
            for name, value in before.items()}, calls=[], prepared=prepared)
    _write(proof_path, proof)
    active_episodes = {row['episode_id'] for row in (root_row, science_row, results_row)}
    pending = {(row['run_id'], row['episode_id'], row['decision_index']) for row in actions if row['result'] is None}
    assert len(pending) == 2
    selected_saved, returned_native = {}, {}

    class Choices:
        async def complete(self, episode_id, role, instructions, current, schema):
            assert len(proof['calls']) < 3, 'only the three genuinely new continuation choices are selected'
            row, = list(store.db.execute('SELECT call_index FROM runtime_model_calls WHERE run_id=? '
                'AND episode_id=? AND response IS NULL', (run_id, episode_id)))
            index = row['call_index']
            wire, actual_instructions = session._presentation(episode_id, role, instructions, current)
            assert actual_instructions == instructions and instructions in wire
            assert wire.startswith('TASK') and 'STEERING' in wire and question in wire
            call = dict(episode_id=episode_id, call_index=index, context=deepcopy(current), wire=wire)
            proof['calls'].append(call)
            if current.get('execution_assignment', {}).get('version') == RESULTS_VERSION:
                task = current['selected_execution_task']
                assert task['scientific_question'] == question
                assert task['selector'] == current['execution_assignment']['selector']
                assert task['selected_tool_info'] == science_request['message']['scientific_process']['selection']['child_tool_info']
                for info in task['selected_tool_info']:
                    assert info['name'] in wire and info['description'] in wire and info['instructions'] in wire
            if episode_id == results_row['episode_id']:
                assert index == len(failed) and len(proof['calls']) == 1
                assert current['execution_assignment'] == native_assignment
                assert current['last_local_outcome']['result']['delivery_complete'] is False
                proof['current_native_full_builder_verified'] = True
                answer = helper.action('execution.results.collect')
            elif episode_id == science_row['episode_id']:
                assert index == 2 and len(proof['calls']) == 2
                report = current['child_reports'][-1]
                assert report['completed'] is True and len(report['overlap']) == len(report['saved']) == 1
                returned_native.update(deepcopy(report))
                saved, = report['saved']
                selected_saved.update(deepcopy(native_selector))
                selected_saved.update(mode='saved_sheet_recalculation', saved_sheet_file=deepcopy(saved))
                selected_saved['parameters']['minimum_overlap_bp'] = 6
                answer = helper.commission('results', dict(version=RESULTS_VERSION,
                    handoff_ref=handoff, selector=deepcopy(selected_saved)), scope, full_form,
                    objective='Recalculate the received sheet with minimum_overlap_bp=6.')
            else:
                assert len(proof['calls']) == 3 and index == 0
                assert current['execution_assignment'] == dict(version=RESULTS_VERSION,
                    handoff_ref=handoff, selector=selected_saved)
                task = current['selected_execution_task']
                assert task['scientific_question'] == question and task['selector'] == selected_saved
                assert current['last_local_outcome'] is None and current['execution_progress']['execution_completed'] is False
                assert 'saved_sheet_recalculation' in wire and 'minimum_overlap_bp' in wire
                proof['current_saved_full_builder_verified'] = True
                answer = helper.action('execution.results.collect')
            answer = helper.provider_value(plain(answer), plain(schema))
            Draft202012Validator(plain(schema)).validate(answer)
            _write(proof_path, proof)
            return answer

        async def release(self, episode_id):
            pass

    store = None
    try:
        store = Store(PREFIX / 'state')
        current_binding = ScientificProcessEpisodes(None,
            library=ScientificProcessLibrary(PREFIX / 'run/scientific-process-library'),
            tool_library=ScientificToolLibrary(PREFIX / 'run/scientific-tool-library'),
            child_roles=binding['configuration']['child_roles']).as_record()
        assert current_binding == binding, 'no mechanics identity repair or descriptor rebase is authorized'
        flow, _ = helper.assemble(store, PREFIX, Choices(), configuration)
        owner = flow.episode_bindings.for_role('results')
        assert owner.job_progress_provider.targets.read_target(handoff, scope) == target
        root, record, archive = asyncio.run(helper.run_root(flow, configuration))
        assert root.source.episode_id == root_row['episode_id']
        result_contexts = [owner.native_genomic_overlap_returns.context(row['episode_id'])
            for row in helper.walk(archive) if json.loads(store.db.execute('SELECT path FROM runtime_episodes '
                'WHERE run_id=? AND episode_id=?', (run_id, row['episode_id'])).fetchone()[0])[-1][0] == 'results']
        forms = [json.loads(flow.journal.row('runtime_forms', context.episode_id)['form']) for context in result_contexts]
        assert len(forms) == 2 and all(form['completed'] for form in forms)
        new_native = json.loads(flow.journal.row('runtime_actions', results_row['episode_id'], len(failed))['result'])['result']
        saved_context, = [context for context in result_contexts if context.episode_id != results_row['episode_id']]
        new_saved = json.loads(flow.journal.row('runtime_actions', saved_context.episode_id, 0)['result'])['result']
        assert all(value['delivery_complete'] and value['worker_execution']['returncode'] == 0
            for value in (new_native, new_saved))
        assert new_native['native']['original_plan'] == native_plan
        assert forms[0]['failures'] == receipts[0]['facts'][FAILURE_SOURCE]
        assert forms[1]['failures'] == []
        projections = [form['overlap'][0] for form in forms]
        for projection in projections:
            row, = projection['pair_rows']
            values = row['measurements']
            assert row['reference_relation'] == 'unknown'
            assert values['unfiltered.native_pair_count'] == 1
            assert values['unfiltered.intersection_union_bp'] == 5 and values['unfiltered.combined_union_bp'] == 15
            assert values['unfiltered.jaccard_bp'] == dict(numerator=5, denominator=15, value=1/3, missing_reason=None)
        assert [value['pair_rows'][0]['measurements']['selected.selected_pair_count'] for value in projections] == [1, 0]
        assert [value['pair_rows'][0]['measurements']['selected.selected_pairwise_bp_sum'] for value in projections] == [5, 0]
        assert forms[0]['saved'] == forms[1]['saved']
        parent = owner.native_genomic_overlap_returns.context(record.episode_id)
        assert owner.native_genomic_overlap_returns.received_facts(parent, parent_form) == {PROJECTION_SOURCE: projections}
        assert not owner.native_genomic_overlap_returns.resolve_received(parent, forms[0]['saved'][0]['artifact_ref'], 'artifact')
        assert [row['mode'] for row in prepared] == ['native_result', 'saved_sheet_recalculation']
        assert proof['current_native_full_builder_verified'] and proof['current_saved_full_builder_verified']
        assert len(proof['calls']) == 3
        after = _tables(store.db)
        proof['tables'] = _history(before, after, active_episodes=active_episodes, pending_actions=pending)
        assert proof['tables']['runtime_episodes']['added_rows'] == 1
        assert proof['tables']['runtime_actions']['added_rows'] == 3
        assert proof['tables']['runtime_model_calls']['added_rows'] == 3
        proof.update(passed=True, forms=forms, typed_parent_values=projections,
            actual_native_child_report=returned_native,
            legitimate_original_pending_action_completions=[list(key) for key in sorted(pending)],
            legitimate_original_active_episode_completions=sorted(active_episodes))
    except BaseException as error:
        proof['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        if store is not None:
            proof['after_table_counts'] = {name: len(value['rows']) for name, value in _tables(store.db).items()}
            store.close()
        current_files = _inventory(PREFIX)
        database_names = {'state/state.sqlite3', 'state/state.sqlite3-wal', 'state/state.sqlite3-shm'}
        proof['old_database_family_before'] = {name: value for name, value in original_files.items() if name in database_names}
        proof['old_database_family_after'] = {name: value for name, value in current_files.items() if name in database_names}
        changed = [name for name, value in original_files.items()
            if name not in database_names and current_files.get(name) != value]
        proof['changed_original_non_database_members'] = changed
        proof['native_pins_after'] = {role: _sha(path.read_bytes()) for role, path in native_files.items()}
        proof['stopped_audit_unchanged'] = _sha(stopped_path.read_bytes()) == STOPPED_SHA256
        proof['passed'] = proof['passed'] and not changed and proof['native_pins_after'] == NATIVE_PINS
        _write(proof_path, proof)
        assert not changed and proof['native_pins_after'] == NATIVE_PINS and proof['stopped_audit_unchanged']


from gene_annotation_episode.episode_composition import scientific_binding_compatible


RESUME526_PROOF = Path('/home/chia/repos/gene_annotation_episode/runs/'
    'check526_genomic_original_file_workflow_continuation/tmp/'
    'test_continue_original521_nati0/GENOMIC_OVERLAP_RETAINED_CONTINUATION.json')
RESUME526_PROOF_SHA256 = '1b2fb1116c04b506bb43714d9ca78837d40a8ac15409420c9179c05ef549ede9'
RESUME526_DATABASE_SHA256 = 'e6c42b3b5d780cfa41dca467509fa88a26320272bb90990174cfab1652471251'
RESUME526_PENDING_REQUEST_SHA256 = 'fff232fa18bd4b07daa41cd410c412e9490cd6f24e3d37cf4eee8fada03ab523'
RESUME526_RECORDED_IMPLEMENTATION_SHA256 = 'f74c77cd6e9a080313662d5a3d11114bc03ff223ebac4f3c6c34e75a13fce4f3'
RESUME526_CURRENT_IMPLEMENTATION_SHA256 = '440744897da3527ac75775c40b94d394e9e81d71b4308a23db57591ef052b42f'
RESUME526_BEFORE_OBSERVER_INVENTORY_SHA256 = '87c109cc17725f929ada3643b7c62677794dafd21719f20330305d250780b756'
RESUME526_AFTER_OBSERVER_INVENTORY_SHA256 = 'c0a3dc751600896dc1129a04bd515bbe884e2530b641c5dc8d7d6258e98eb047'
RESUME526_OBSERVER_FILES = {
    'state/state.sqlite3-shm': dict(kind='file', mode=0o644, size_bytes=32768,
        sha256='fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb'),
    'state/state.sqlite3-wal': dict(kind='file', mode=0o644, size_bytes=0,
        sha256='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
}


def _resume526_history(before, after, *, active_episodes, pending_actions, pending_call):
    """Preserve every old cell except actual pending work's completion fields."""
    summaries = _history({key: value for key, value in before.items() if key != 'runtime_model_calls'},
        {key: value for key, value in after.items() if key != 'runtime_model_calls'},
        active_episodes=active_episodes, pending_actions=pending_actions)
    original, current = before['runtime_model_calls'], after['runtime_model_calls']
    assert original['sql'] == current['sql'] and original['columns'] == current['columns']
    old, new = _records(before, 'runtime_model_calls'), _records(after, 'runtime_model_calls')
    by_key = {(row['run_id'], row['episode_id'], row['call_index']): row for row in new}
    for row in old:
        key = (row['run_id'], row['episode_id'], row['call_index'])
        actual = by_key[key]
        if key == pending_call:
            assert row['response'] is None and actual['response'] is not None
            assert {k: v for k, v in actual.items() if k not in {'response', 'timing'}} == {
                k: v for k, v in row.items() if k not in {'response', 'timing'}}
        else:
            assert actual == row
    summaries['runtime_model_calls'] = dict(before_rows=len(old), after_rows=len(new),
        added_rows=len(new) - len(old), before_sha256=_sha(_canonical(original['rows']).encode()),
        after_sha256=_sha(_canonical(current['rows']).encode()))
    return summaries


def test_resume526_frozen_scientific_call_then_saved_results_without_native_repeat(tmp_path, monkeypatch):
    """Resume the actual failed526 prefix; redelivery is an engineering control.

    The unanswered scientific call retains its launch-only context. Its visible
    launch report is redelivered normally, without an acquisition or controller
    sample, before a fresh scientific call may use the newly returned sheet.
    """
    if os.environ.get('HMMER_NATIVE_ORACLE_OVERLAP_FILE_RESUME526') != '1':
        pytest.skip('requires explicit continuation of the authentic failed526 original owner')
    original526_raw = RESUME526_PROOF.read_bytes()
    assert _sha(original526_raw) == RESUME526_PROOF_SHA256
    original526 = json.loads(original526_raw)
    assert original526['passed'] is False and original526['prepared'] == []
    assert original526['failure']['type'] == 'AssertionError'
    assert len(original526['calls']) == 1 and original526['calls'][0]['call_index'] == 2
    assert original526['changed_original_non_database_members'] == []
    assert original526['native_pins_after'] == NATIVE_PINS
    stopped_path = PREFIX.parents[2] / 'stopped_verification_audit.json'
    assert _sha(stopped_path.read_bytes()) == STOPPED_SHA256
    database = PREFIX / 'state/state.sqlite3'
    assert _sha(database.read_bytes()) == RESUME526_DATABASE_SHA256
    original_files = _inventory(PREFIX)
    assert _sha(_canonical(original_files).encode()) == RESUME526_AFTER_OBSERVER_INVENTORY_SHA256
    assert {name: original_files[name] for name in RESUME526_OBSERVER_FILES} == RESUME526_OBSERVER_FILES
    # The527 read-only observer created exactly this empty-WAL/shared-memory
    # pair. Removing these two entries from a detached inventory, never from
    # disk, must reproduce the entire original526 no-sidecar inventory.
    without_observer = {name: value for name, value in original_files.items()
        if name not in RESUME526_OBSERVER_FILES}
    assert _sha(_canonical(without_observer).encode()) == RESUME526_BEFORE_OBSERVER_INVENTORY_SHA256
    database_names = {'state/state.sqlite3', 'state/state.sqlite3-wal', 'state/state.sqlite3-shm'}
    assert {name: value for name, value in without_observer.items() if name in database_names} == (
        original526['old_database_family_after'])
    before = _snapshot(database)
    assert {name: len(value['rows']) for name, value in before.items()} == original526['after_table_counts']
    episodes = _records(before, 'runtime_episodes')
    by_role = {json.loads(row['path'])[-1][0]: row for row in episodes}
    root_row, science_row, results_row = (by_role[name] for name in ('annotation', 'scientific_process', 'results'))
    assert len(episodes) == 5 and all(row['state'] == 'active' and row['completion'] is row['archive'] is None
        for row in (root_row, science_row, results_row))
    root_request, science_request, results_request = (json.loads(row['request'])
        for row in (root_row, science_row, results_row))
    run_id = root_row['run_id']
    assert {row['run_id'] for row in episodes} == {run_id}
    actions = _records(before, 'runtime_actions')
    failed = sorted((row for row in actions if row['episode_id'] == results_row['episode_id']),
        key=lambda row: row['decision_index'])
    assert [row['decision_index'] for row in failed] == list(range(5))
    receipts = [json.loads(row['result'])['result'] for row in failed]
    assert all(not value['delivery_complete'] and value['worker_execution']['returncode'] == 1 for value in receipts)
    assert all(json.loads(row['action']) == dict(kind='tool', tool='execution.results.collect', arguments={})
        for row in failed)
    pending_actions = {(row['run_id'], row['episode_id'], row['decision_index'])
        for row in actions if row['result'] is None}
    assert pending_actions == {(run_id, root_row['episode_id'], 0), (run_id, science_row['episode_id'], 1)}
    pending_model, = [row for row in _records(before, 'runtime_model_calls') if row['response'] is None]
    pending_call = (run_id, science_row['episode_id'], 2)
    assert (pending_model['run_id'], pending_model['episode_id'], pending_model['call_index']) == pending_call
    assert _sha(pending_model['request'].encode()) == RESUME526_PENDING_REQUEST_SHA256
    frozen_request = json.loads(pending_model['request'])
    frozen_context = frozen_request['context']
    assert frozen_context == original526['calls'][0]['context']
    assert 'decision_protocol' not in frozen_request
    assert frozen_context['feedback'] == dict(status='invalid', category='action_contract',
        detail='genomic_overlap_result_invalid_record')
    assert frozen_context['controller']['scores'] == [0.0]
    target = deepcopy(receipts[0]['intent']['target'])
    native_assignment = results_request['message']['episode_assignment']
    assert all(value['intent']['target'] == target and value['intent']['assignment'] == native_assignment
        for value in receipts)
    native_selector = deepcopy(native_assignment['selector'])
    assert native_selector['mode'] == 'native_result' and native_selector['parameters']['minimum_overlap_bp'] == 1
    handoff = native_assignment['handoff_ref']
    assert handoff == target['handle'] == 'source_6aad56cf475ede7ec070fd79'
    assert frozen_context['child_reports'] == [dict(completed=True, references=[handoff])]
    visible_delivery, = frozen_context['report_deliveries']
    assert visible_delivery == dict(delivery_ref='delivery_61d998569d63bb25f6bf98a6', status='delivered')
    launch_action, = [row for row in actions if row['episode_id'] == science_row['episode_id']
        and row['decision_index'] == 0]
    launch_selection = json.loads(launch_action['action'])
    launch_row, = [row for row in episodes if row['episode_id'] ==
        next(row['child_episode_id'] for row in _records(before, 'runtime_report_attempts')
            if row['delivery_ref'] == visible_delivery['delivery_ref'])]
    launch_request = json.loads(launch_row['request'])
    assert json.loads(launch_selection['schema_json']) == launch_request['report_contract']['measurements']['schema']
    assert launch_selection['purpose'] == launch_request['report_contract']['decision']
    assert launch_row['state'] == 'yielded'
    plan_path = Path(target['execution_id']).parent / 'genomic-overlap-plan.json'
    native_plan = json.loads(plan_path.read_bytes())
    assert native_plan['requested_job'] == target['assignment']['requested_job']
    assert native_plan['identity']['requested_job_sha256'] == digest(native_plan['requested_job'])
    attempt = Path(native_plan['attempt_directory'])
    native_files = dict(plan=plan_path, handle=Path(target['execution_id']),
        bundle=attempt / 'bundle.json', stdout=attempt / 'overlap/pairs/p0/overlap.wo.tsv')
    assert {role: _sha(path.read_bytes()) for role, path in native_files.items()} == NATIVE_PINS
    assert native_files['stdout'].read_bytes() == b'chr1\t0\t10\ts0_r0\tchr1\t5\t15\ts1_r0\t5\n'
    job = native_plan['requested_job']['native_genomic_overlap']
    request = job['request']
    practical_row = by_role['launch_local']
    assert json.loads(practical_row['request'])['message']['episode_assignment'] == target['assignment']
    assert all('source_ref' not in spec['source'] for spec in request['region_sets'])
    scope, question = root_request['message']['scope'], root_request['goal']['objective']
    assert scope == science_request['message']['scope'] == results_request['message']['scope']
    assert 'minimum_overlap_bp=6' in question
    assert science_request['message']['episode_assignment']['context']['supplied_genomic_overlap_request'] == request
    binding = science_request['message']['scientific_process']['mechanics_binding']
    helper = _fixture(dict(name='overlap_complete'), monkeypatch)
    assert helper.RUN_ID == run_id
    prepared = _guards(monkeypatch, helper, PREFIX)
    factory = ExecutionServiceFactory({target['resource_id']: dict(kind=target['resource_kind'],
        workspace=target['assignment']['workspace'], policy=deepcopy(native_plan['policy']),
        native_genomic_overlap=[dict(operation=request['operation'], mode=request['mode'],
            software=deepcopy(job['software']))])}, {}, 3, 2, 1, log_window_bytes=128)
    configuration = dict(factory=factory.as_record(), scientific_binding=deepcopy(binding),
        goal=question, scope=deepcopy(scope), initial_refs=[spec['source']['file']['artifact_ref']
            for spec in request['region_sets']], saved=True, failure=None)
    assert configuration == original526['restored_configuration']
    full_form = results_request['report_contract']['measurements']['schema']
    parent_form = science_request['report_contract']['measurements']['schema']
    session = _session(tmp_path / 'current-presentation')
    proof_path = tmp_path / 'GENOMIC_OVERLAP_RESUME526.json'
    proof = dict(version='genomic_overlap_resume526_v1', passed=False, original_prefix=str(PREFIX),
        original526_proof_sha256=RESUME526_PROOF_SHA256, original526_passed=False,
        original_failed_action_count=5, native_pins=NATIVE_PINS, original_native_reexecuted=False,
        frozen_scientific_request_sha256=RESUME526_PENDING_REQUEST_SHA256,
        measured_read_only_observer_transition=dict(
            before_inventory_sha256=RESUME526_BEFORE_OBSERVER_INVENTORY_SHA256,
            after_inventory_sha256=RESUME526_AFTER_OBSERVER_INVENTORY_SHA256,
            added_files=deepcopy(RESUME526_OBSERVER_FILES)),
        current_native_full_builder_verified=False, current_saved_full_builder_verified=False,
        current_fresh_scientific_context_verified=False, calls=[], prepared=prepared,
        before_table_counts={name: len(value['rows']) for name, value in before.items()})
    _write(proof_path, proof)
    selected_saved, returned_native, redelivery_before = {}, {}, {}

    class Choices:
        async def complete(self, episode_id, role, instructions, current, schema):
            assert len(proof['calls']) < 4, 'only four genuine scripted recovery callbacks are selected'
            row, = list(store.db.execute('SELECT call_index,request FROM runtime_model_calls WHERE run_id=? '
                'AND episode_id=? AND response IS NULL', (run_id, episode_id)))
            index = row['call_index']
            wire, actual_instructions = session._presentation(episode_id, role, instructions, current)
            assert actual_instructions == instructions and instructions in wire
            assert wire.startswith('TASK') and 'STEERING' in wire and question in wire
            proof['calls'].append(dict(episode_id=episode_id, call_index=index,
                context=deepcopy(current), wire=wire))
            if current.get('execution_assignment', {}).get('version') == RESULTS_VERSION:
                task = current['selected_execution_task']
                assert task['scientific_question'] == question
                assert task['selector'] == current['execution_assignment']['selector']
                assert task['selected_tool_info'] == science_request['message']['scientific_process']['selection']['child_tool_info']
                for info in task['selected_tool_info']:
                    assert info['name'] in wire and info['description'] in wire and info['instructions'] in wire
            if episode_id == results_row['episode_id']:
                assert index == 5 and len(proof['calls']) == 1
                assert current['execution_assignment'] == native_assignment
                assert current['last_local_outcome']['result']['delivery_complete'] is False
                proof['current_native_full_builder_verified'] = True
                answer = helper.action('execution.results.collect')
            elif episode_id == science_row['episode_id'] and index == 2:
                assert len(proof['calls']) == 2 and row['request'] == pending_model['request']
                assert current == frozen_context
                # The choice uses only the launch report/delivery visible in this
                # frozen input. No newly acquired sheet is read out of band.
                assert current['child_reports'] == [dict(completed=True, references=[handoff])]
                assert current['report_deliveries'] == [visible_delivery]
                redelivery_before.update(observation_count=store.db.execute(
                    'SELECT COUNT(*) FROM runtime_observations').fetchone()[0],
                    scientific_observation_count=store.db.execute('SELECT COUNT(*) FROM runtime_observations '
                        'WHERE run_id=? AND episode_id=?', (run_id, episode_id)).fetchone()[0])
                assert redelivery_before['scientific_observation_count'] == 2
                answer = dict(selection=dict(kind='redeliver_report',
                    delivery_ref=current['report_deliveries'][0]['delivery_ref'],
                    purpose=launch_selection['purpose'], schema_json=launch_selection['schema_json']), report_update={})
                proof['frozen_scientific_choice'] = deepcopy(answer)
            elif episode_id == science_row['episode_id']:
                assert index == 3 and len(proof['calls']) == 3
                assert current['controller']['scores'] == [0.0, 0.0]
                assert store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == (
                    redelivery_before['observation_count'])
                assert store.db.execute('SELECT COUNT(*) FROM runtime_observations WHERE run_id=? AND episode_id=?',
                    (run_id, episode_id)).fetchone()[0] == redelivery_before['scientific_observation_count']
                assert flow.journal.row('runtime_actions', episode_id, 2) is None
                attempt_row = store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? '
                    'AND parent_episode_id=? AND decision_index=?', (run_id, episode_id, 2)).fetchone()
                assert attempt_row['failure'] is None and json.loads(attempt_row['form']) == frozen_context['child_reports'][0]
                assert attempt_row['delivery_ref'] == visible_delivery['delivery_ref']
                report, = [value for value in current['child_reports'] if value.get('overlap')]
                assert report['completed'] is True and len(report['overlap']) == len(report['saved']) == 1
                returned_native.update(deepcopy(report))
                saved, = report['saved']
                selected_saved.update(deepcopy(native_selector))
                selected_saved.update(mode='saved_sheet_recalculation', saved_sheet_file=deepcopy(saved))
                selected_saved['parameters']['minimum_overlap_bp'] = 6
                proof['redelivery_no_observation_or_controller_sample_verified'] = True
                proof['current_fresh_scientific_context_verified'] = True
                answer = helper.commission('results', dict(version=RESULTS_VERSION,
                    handoff_ref=handoff, selector=deepcopy(selected_saved)), scope, full_form,
                    objective='Recalculate the received sheet with minimum_overlap_bp=6.')
            else:
                assert len(proof['calls']) == 4 and index == 0
                assert current['execution_assignment'] == dict(version=RESULTS_VERSION,
                    handoff_ref=handoff, selector=selected_saved)
                assert current['last_local_outcome'] is None and current['execution_progress']['execution_completed'] is False
                assert 'saved_sheet_recalculation' in wire and 'minimum_overlap_bp' in wire
                proof['current_saved_full_builder_verified'] = True
                answer = helper.action('execution.results.collect')
            answer = helper.provider_value(plain(answer), plain(schema))
            Draft202012Validator(plain(schema)).validate(answer)
            _write(proof_path, proof)
            return answer

        async def release(self, episode_id):
            pass

    store = None
    try:
        store = Store(PREFIX / 'state')
        current_binding = ScientificProcessEpisodes(None,
            library=ScientificProcessLibrary(PREFIX / 'run/scientific-process-library'),
            tool_library=ScientificToolLibrary(PREFIX / 'run/scientific-tool-library'),
            child_roles=binding['configuration']['child_roles']).as_record()
        assert binding['implementation_sha256'] == RESUME526_RECORDED_IMPLEMENTATION_SHA256
        assert current_binding['implementation_sha256'] == RESUME526_CURRENT_IMPLEMENTATION_SHA256
        assert {key: value for key, value in current_binding.items() if key != 'implementation_sha256'} == {
            key: value for key, value in binding.items() if key != 'implementation_sha256'}
        assert scientific_binding_compatible(current_binding, binding)
        proof['scientific_bindings'] = dict(recorded=deepcopy(binding), current=deepcopy(current_binding),
            admission='existing_exact_directed_compatibility_pair_with_all_other_fields_equal')
        _write(proof_path, proof)
        flow, _ = helper.assemble(store, PREFIX, Choices(), configuration)
        owner = flow.episode_bindings.for_role('results')
        assert owner.job_progress_provider.targets.read_target(handoff, scope) == target
        root, record, archive = asyncio.run(helper.run_root(flow, configuration))
        assert root.source.episode_id == root_row['episode_id']
        result_contexts = [owner.native_genomic_overlap_returns.context(value['episode_id'])
            for value in helper.walk(archive) if json.loads(store.db.execute('SELECT path FROM runtime_episodes '
                'WHERE run_id=? AND episode_id=?', (run_id, value['episode_id'])).fetchone()[0])[-1][0] == 'results']
        native_context, = [value for value in result_contexts if value.episode_id == results_row['episode_id']]
        saved_context, = [value for value in result_contexts if value.episode_id != results_row['episode_id']]
        forms = [json.loads(flow.journal.row('runtime_forms', value.episode_id)['form'])
            for value in (native_context, saved_context)]
        assert all(form['completed'] for form in forms)
        new_native = json.loads(flow.journal.row('runtime_actions', native_context.episode_id, 5)['result'])['result']
        new_saved = json.loads(flow.journal.row('runtime_actions', saved_context.episode_id, 0)['result'])['result']
        assert all(value['delivery_complete'] and value['worker_execution']['returncode'] == 0
            for value in (new_native, new_saved))
        assert new_native['native']['original_plan'] == native_plan
        assert forms[0]['failures'] == receipts[0]['facts'][FAILURE_SOURCE] and forms[1]['failures'] == []
        projections = [form['overlap'][0] for form in forms]
        for projection in projections:
            pair, = projection['pair_rows']
            values = pair['measurements']
            assert pair['reference_relation'] == 'unknown'
            assert values['unfiltered.native_pair_count'] == 1
            assert values['unfiltered.intersection_union_bp'] == 5 and values['unfiltered.combined_union_bp'] == 15
            assert values['unfiltered.jaccard_bp'] == dict(numerator=5, denominator=15, value=1/3, missing_reason=None)
        assert [value['pair_rows'][0]['measurements']['selected.selected_pair_count'] for value in projections] == [1, 0]
        assert [value['pair_rows'][0]['measurements']['selected.selected_pairwise_bp_sum'] for value in projections] == [5, 0]
        assert forms[0]['saved'] == forms[1]['saved']
        parent = owner.native_genomic_overlap_returns.context(record.episode_id)
        assert owner.native_genomic_overlap_returns.received_facts(parent, parent_form) == {PROJECTION_SOURCE: projections}
        assert not owner.native_genomic_overlap_returns.resolve_received(parent, forms[0]['saved'][0]['artifact_ref'], 'artifact')
        assert [value['mode'] for value in prepared] == ['native_result', 'saved_sheet_recalculation']
        assert [(value['episode_id'], value['call_index']) for value in proof['calls']] == [
            (results_row['episode_id'], 5), (science_row['episode_id'], 2),
            (science_row['episode_id'], 3), (saved_context.episode_id, 0)]
        assert flow.journal.row('runtime_model_calls', science_row['episode_id'], 2)['request'] == pending_model['request']
        after = _tables(store.db)
        active = {value['episode_id'] for value in (root_row, science_row, results_row)}
        proof['tables'] = _resume526_history(before, after, active_episodes=active,
            pending_actions=pending_actions, pending_call=pending_call)
        for name, expected in {'runtime_episodes': 1, 'runtime_actions': 3, 'runtime_model_calls': 3,
                'runtime_observations': 5, 'runtime_forms': 3, 'runtime_report_attempts': 4}.items():
            assert proof['tables'][name]['added_rows'] == expected, name
        assert proof['current_native_full_builder_verified'] and proof['current_saved_full_builder_verified']
        assert proof['current_fresh_scientific_context_verified']
        proof.update(passed=True, forms=forms, typed_parent_values=projections,
            actual_fresh_native_child_report=returned_native, frozen_request_bytes_unchanged=True,
            legitimate_original_pending_action_completions=[list(key) for key in sorted(pending_actions)],
            legitimate_original_active_episode_completions=sorted(active))
    except BaseException as error:
        proof['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        if store is not None:
            proof['after_table_counts'] = {name: len(value['rows']) for name, value in _tables(store.db).items()}
            store.close()
        current_files = _inventory(PREFIX)
        proof['database_family_before'] = {name: value for name, value in original_files.items() if name in database_names}
        proof['database_family_after'] = {name: value for name, value in current_files.items() if name in database_names}
        changed = [name for name, value in original_files.items()
            if name not in database_names and current_files.get(name) != value]
        proof['changed_original_non_database_members'] = changed
        proof['native_pins_after'] = {role: _sha(path.read_bytes()) for role, path in native_files.items()}
        proof['original526_proof_unchanged'] = _sha(RESUME526_PROOF.read_bytes()) == RESUME526_PROOF_SHA256
        proof['stopped_audit_unchanged'] = _sha(stopped_path.read_bytes()) == STOPPED_SHA256
        proof['passed'] = (proof['passed'] and not changed and proof['native_pins_after'] == NATIVE_PINS
            and proof['original526_proof_unchanged'] and proof['stopped_audit_unchanged'])
        _write(proof_path, proof)
        assert not changed and proof['native_pins_after'] == NATIVE_PINS
        assert proof['original526_proof_unchanged'] and proof['stopped_audit_unchanged']


CLOSED531_PROOF = Path('/home/chia/repos/gene_annotation_episode/runs/'
    'check531_genomic_original_native_saved_continuation/tmp/'
    'test_resume526_frozen_scientif0/GENOMIC_OVERLAP_RESUME526.json')
CLOSED531_PROOF_SHA256 = 'c0a1b989a84f73c09a3b8454da806de3d3e53423d781923d1c2110b19d7c7d10'
CLOSED531_DATABASE_SHA256 = '3977233946a41dc4fd0b82a5dfcca6ddb3ea4b84f07b6a0306f7ababfe387f6f'
CLOSED531_INVENTORY_WITHOUT_OBSERVER_SHA256 = '8a092d0e8188aecb1aeab000e1ac90f8890da0836594cba050456680c64e355e'
CLOSED531_OBSERVED_INVENTORY_SHA256 = '13f9e75358e9dd249442cffc61ce2d1b1686e06fb6e2818ea648c509adc85c43'
CLOSED534_CURRENT_IMPLEMENTATION_SHA256 = '85612b5c97264c97ba2380ec2335584a5a8261c7655e54f8f04470f750e13f87'
CURRENT_PROVIDER_PROTEASE_IMPLEMENTATION_SHA256 = '39977fe39ea61eccfba5da479cae42dd90702810ce95353e5fa981208950ccd8'


def _closed531_guards(monkeypatch, helper, registry, result_owner):
    """Closed replay may read its controls, forms and archive, not science bodies."""
    from gene_annotation_episode import genomic_overlap_calculations as calculations
    from gene_annotation_episode import genomic_overlap_result_worker as worker
    from gene_annotation_episode import native_file_capture
    from gene_annotation_episode import native_genomic_overlap_driver as driver
    from gene_annotation_episode import native_genomic_overlap_local as local
    from gene_annotation_episode import native_genomic_overlap_preparation as preparation
    from gene_annotation_episode import native_genomic_overlap_results as results
    from gene_annotation_episode import native_lifecycle
    monkeypatch.setattr(registry, '_execute_operation_async', _forbidden)
    monkeypatch.setattr(result_owner, '_worker', _forbidden)
    monkeypatch.setattr(local, 'prepare_local_genomic_overlap', _forbidden)
    monkeypatch.setattr(driver, 'run_genomic_overlap_driver', _forbidden)
    monkeypatch.setattr(driver, '_native_call', _forbidden)
    monkeypatch.setattr(preparation, 'prepare_genomic_overlap_worker', _forbidden)
    monkeypatch.setattr(results, 'prepare_genomic_overlap_worker', _forbidden)
    monkeypatch.setattr(worker, 'run_genomic_overlap_result_worker', _forbidden)
    monkeypatch.setattr(worker, 'calculate_genomic_overlap_components', _forbidden)
    monkeypatch.setattr(calculations, 'calculate_genomic_overlap_components', _forbidden)
    monkeypatch.setattr(native_file_capture, 'retained_native_file', _forbidden)
    monkeypatch.setattr(results, 'retained_native_file', _forbidden)
    monkeypatch.setattr(Store, 'get_artifact', _forbidden)
    monkeypatch.setattr(helper.NATIVE, 'software', _forbidden)
    monkeypatch.setattr(helper, 'prepare_scientific_binding', _forbidden)
    monkeypatch.setattr(ScientificProcessLibrary, 'freeze', _forbidden)
    monkeypatch.setattr(ScientificToolLibrary, 'freeze', _forbidden)
    monkeypatch.setattr(PublicClients, '_http', _forbidden)
    monkeypatch.setattr(_SessionConnection, 'complete', _forbidden)
    for name in ('prepare_job', 'resume_start', 'start_prepared', 'wait_job', 'status', 'collect'):
        monkeypatch.setattr(native_lifecycle, name, _forbidden)
    for name in ('urllib.request.urlopen', 'urllib.request.build_opener', 'socket.create_connection'):
        monkeypatch.setattr(name, _forbidden)


def test_closed531_native_saved_typed_messages_and_exact_replay_without_work(tmp_path, monkeypatch):
    """Validate the completed531 data despite its final form-count fixture failure.

    Captured531 callbacks are authenticated historical current-builder evidence.
    This selected check makes no new decision, worker, calculation or projection.
    The root received numeric projections, not a newly invented result Source.
    """
    if os.environ.get('HMMER_NATIVE_ORACLE_OVERLAP_FILE_CLOSED531') != '1':
        pytest.skip('requires the exact completed531 original owner and failed proof')
    raw531 = CLOSED531_PROOF.read_bytes()
    assert _sha(raw531) == CLOSED531_PROOF_SHA256
    original531 = json.loads(raw531)
    assert original531['passed'] is False and original531['failure'] == dict(
        type='AssertionError', message='runtime_forms\nassert 3 == 4')
    assert original531['original526_passed'] is False
    assert original531['original_failed_action_count'] == 5
    assert all(original531[key] is True for key in ('current_native_full_builder_verified',
        'current_saved_full_builder_verified', 'current_fresh_scientific_context_verified',
        'redelivery_no_observation_or_controller_sample_verified', 'original526_proof_unchanged',
        'stopped_audit_unchanged'))
    assert original531['changed_original_non_database_members'] == []
    assert original531['native_pins_after'] == NATIVE_PINS
    assert [value['mode'] for value in original531['prepared']] == ['native_result', 'saved_sheet_recalculation']
    original526_raw = RESUME526_PROOF.read_bytes()
    assert _sha(original526_raw) == RESUME526_PROOF_SHA256
    original526 = json.loads(original526_raw)
    configuration = deepcopy(original526['restored_configuration'])
    database = PREFIX / 'state/state.sqlite3'
    assert _sha(database.read_bytes()) == CLOSED531_DATABASE_SHA256
    selected_files = _inventory(PREFIX)
    for name in RESUME526_OBSERVER_FILES:
        if name in selected_files:
            assert selected_files[name] == RESUME526_OBSERVER_FILES[name]
    no_observer = {name: value for name, value in selected_files.items() if name not in RESUME526_OBSERVER_FILES}
    assert _sha(_canonical(no_observer).encode()) == CLOSED531_INVENTORY_WITHOUT_OBSERVER_SHA256
    assert {name: value for name, value in no_observer.items() if name == 'state/state.sqlite3'} == (
        original531['database_family_after'])
    # Establish the explicit read-only SQLite observer pair before the strict
    # physical baseline. Both possible initial states were byte-authenticated
    # above; no file is deleted, synthesized or restored by this test.
    before = _snapshot(database)
    before_files = _inventory(PREFIX)
    assert _sha(_canonical(before_files).encode()) == CLOSED531_OBSERVED_INVENTORY_SHA256
    assert {name: before_files[name] for name in RESUME526_OBSERVER_FILES} == RESUME526_OBSERVER_FILES
    assert set(before) == set(original531['tables'])
    for name, value in before.items():
        assert len(value['rows']) == original531['after_table_counts'][name]
        assert _sha(_canonical(value['rows']).encode()) == original531['tables'][name]['after_sha256']
    episodes = _records(before, 'runtime_episodes')
    assert len(episodes) == 6 and all(row['state'] == 'yielded' and row['archive'] is not None for row in episodes)
    root_row, = [row for row in episodes if len(json.loads(row['path'])) == 1]
    science_row, = [row for row in episodes if json.loads(row['path'])[-1][0] == 'scientific_process']
    native_row, = [row for row in episodes if json.loads(row['path'])[-1] == ['results', 'child_1']]
    saved_row, = [row for row in episodes if json.loads(row['path'])[-1] == ['results', 'child_3']]
    run_id, question = root_row['run_id'], configuration['goal']
    assert {row['run_id'] for row in episodes} == {run_id}
    assert json.loads(root_row['request'])['goal']['objective'] == question
    science_request = json.loads(science_row['request'])
    native_request, saved_request = (json.loads(row['request']) for row in (native_row, saved_row))
    binding = science_request['message']['scientific_process']['mechanics_binding']
    assert configuration['scientific_binding'] == binding == original531['scientific_bindings']['recorded']
    assert binding['implementation_sha256'] == RESUME526_RECORDED_IMPLEMENTATION_SHA256
    tool_info = science_request['message']['scientific_process']['selection']['child_tool_info']
    model_rows = {(row['episode_id'], row['call_index']): row for row in _records(before, 'runtime_model_calls')}
    expected_calls = [(native_row['episode_id'], 5), (science_row['episode_id'], 2),
        (science_row['episode_id'], 3), (saved_row['episode_id'], 0)]
    assert [(row['episode_id'], row['call_index']) for row in original531['calls']] == expected_calls
    for call in original531['calls']:
        recorded = model_rows[(call['episode_id'], call['call_index'])]
        assert recorded['response'] is not None
        assert json.loads(recorded['request'])['context'] == call['context']
        wire = call['wire']
        assert wire.startswith('TASK') and 'STEERING' in wire and question in wire
        for info in tool_info:
            assert all(info[key] in wire for key in ('name', 'description', 'instructions'))
        if call['episode_id'] in (native_row['episode_id'], saved_row['episode_id']):
            original_request = native_request if call['episode_id'] == native_row['episode_id'] else saved_request
            assert call['context']['execution_assignment'] == original_request['message']['episode_assignment']
            task = call['context']['selected_execution_task']
            assert task['scientific_question'] == question and task['selected_tool_info'] == tool_info
            assert task['selector'] == call['context']['execution_assignment']['selector']
    frozen = model_rows[(science_row['episode_id'], 2)]
    assert _sha(frozen['request'].encode()) == RESUME526_PENDING_REQUEST_SHA256
    assert original531['calls'][1]['context'] == original526['calls'][0]['context']
    actions = _records(before, 'runtime_actions')
    assert not any(row['result'] is None for row in actions)
    old_failed = sorted((row for row in actions if row['episode_id'] == native_row['episode_id']
        and row['decision_index'] < 5), key=lambda row: row['decision_index'])
    assert [row['decision_index'] for row in old_failed] == list(range(5))
    for row in old_failed:
        action, outcome = json.loads(row['action']), json.loads(row['result'])
        assert action == dict(kind='tool', tool='execution.results.collect', arguments={})
        assert outcome['status'] == 'completed' and outcome['result']['delivery_complete'] is False
        assert outcome['result']['worker_execution']['returncode'] == 1
        assert [value['code'] for value in outcome['result']['facts'][FAILURE_SOURCE]] == [
            'native_nonzero_exit', 'native_output_unavailable']
    assert not any(row['episode_id'] == science_row['episode_id'] and row['decision_index'] == 2 for row in actions)
    forms_by_id = {row['episode_id']: json.loads(row['form']) for row in _records(before, 'runtime_forms')}
    assert root_row['episode_id'] not in forms_by_id and len(forms_by_id) == 5
    assert original531['tables']['runtime_forms']['added_rows'] == 3
    forms = [forms_by_id[row['episode_id']] for row in (native_row, saved_row)]
    assert all(form['completed'] for form in forms) and forms[0]['saved'] == forms[1]['saved']
    sheet_file, = forms[0]['saved']
    projections = [form['overlap'][0] for form in forms]
    assert forms_by_id[science_row['episode_id']] == dict(overlap=projections)
    assert [value['parameters']['minimum_overlap_bp'] for value in projections] == [1, 6]
    for value in projections:
        pair, = value['pair_rows']
        measurements = pair['measurements']
        assert value['result_extent'] == pair['result_extent'] == 'complete'
        assert pair['reference_relation'] == 'unknown'
        assert measurements['unfiltered.native_pair_count'] == 1
        assert measurements['unfiltered.intersection_union_bp'] == 5
        assert measurements['unfiltered.combined_union_bp'] == 15
        assert measurements['unfiltered.jaccard_bp'] == dict(numerator=5, denominator=15, value=1/3, missing_reason=None)
        assert value['source_sheet_sha256'] == sheet_file['sha256']
    assert [value['pair_rows'][0]['measurements']['selected.selected_pair_count'] for value in projections] == [1, 0]
    assert [value['pair_rows'][0]['measurements']['selected.selected_pairwise_bp_sum'] for value in projections] == [5, 0]
    saved_selector = saved_request['message']['episode_assignment']['selector']
    assert saved_selector['mode'] == 'saved_sheet_recalculation' and saved_selector['saved_sheet_file'] == sheet_file
    assert original531['calls'][2]['context']['child_reports'][-1] == forms[0]
    native_actions = {(row['episode_id'], row['decision_index']): json.loads(row['result']) for row in actions}
    for key in ((native_row['episode_id'], 5), (saved_row['episode_id'], 0)):
        value = native_actions[key]['result']
        assert value['delivery_complete'] and value['worker_execution']['returncode'] == 0
        assert value['facts'][PROJECTION_SOURCE] == [projections[0 if key[0] == native_row['episode_id'] else 1]]
    proof_path = tmp_path / 'GENOMIC_OVERLAP_CLOSED531_REPLAY.json'
    proof = dict(version='genomic_overlap_closed531_replay_v1', passed=False,
        original531_proof_sha256=CLOSED531_PROOF_SHA256, original531_passed=False,
        actual_original_failure='runtime_forms_added3_expected4_fixture_only',
        original_prefix=str(PREFIX), actual_forms_total=5, actual_added_form_owners=[
            native_row['episode_id'], saved_row['episode_id'], science_row['episode_id']],
        authenticated_original_callbacks=expected_calls, typed_parent_values=projections,
        saved_sheet_file=sheet_file, native_reexecuted=False, calculation_repeated=False,
        new_model_calls=0, new_observations=0, new_result_workers=0, before_counts={
            name: len(value['rows']) for name, value in before.items()})
    _write(proof_path, proof)
    helper = _fixture(dict(name='overlap_complete'), monkeypatch)

    class NoChoices:
        async def complete(self, *args, **kwargs):
            return _forbidden()

        async def release(self, episode_id):
            pass

    store = None
    try:
        store = Store(PREFIX / 'state')
        current_binding = ScientificProcessEpisodes(None,
            library=ScientificProcessLibrary(PREFIX / 'run/scientific-process-library'),
            tool_library=ScientificToolLibrary(PREFIX / 'run/scientific-tool-library'),
            child_roles=binding['configuration']['child_roles']).as_record()
        prior_current = original531['scientific_bindings']['current']
        assert prior_current['implementation_sha256'] == RESUME526_CURRENT_IMPLEMENTATION_SHA256
        assert current_binding['implementation_sha256'] == CURRENT_PROVIDER_PROTEASE_IMPLEMENTATION_SHA256
        assert {key: value for key, value in current_binding.items() if key != 'implementation_sha256'} == {
            key: value for key, value in prior_current.items() if key != 'implementation_sha256'} == {
            key: value for key, value in binding.items() if key != 'implementation_sha256'}
        assert scientific_binding_compatible(current_binding, prior_current)
        assert scientific_binding_compatible(current_binding, binding)
        flow, registry = helper.assemble(store, PREFIX, NoChoices(), configuration)
        owner = flow.episode_bindings.for_role('results')
        _closed531_guards(monkeypatch, helper, registry, owner.native_genomic_overlap_results)
        returns = owner.native_genomic_overlap_returns
        for row, form in zip((native_row, saved_row), forms):
            context = returns.context(row['episode_id'])
            schema = json.loads(row['request'])['report_contract']['measurements']['schema']
            returns.validate_received_report(context, form, schema)
        science_context = returns.context(science_row['episode_id'])
        parent_schema = science_request['report_contract']['measurements']['schema']
        returns.validate_received_report(science_context, dict(overlap=projections), parent_schema)
        root_context = returns.context(root_row['episode_id'])
        assert returns.received_facts(root_context, parent_schema) == {PROJECTION_SOURCE: projections}
        assert returns.resolve_received(science_context, sheet_file['artifact_ref'], 'artifact')
        assert not returns.resolve_received(root_context, sheet_file['artifact_ref'], 'artifact')
        root, record, archive = asyncio.run(helper.run_root(flow, configuration))
        assert root.source.episode_id == record.episode_id == root_row['episode_id']
        assert {value['episode_id'] for value in helper.walk(archive)} == {value['episode_id'] for value in episodes}
        assert flow.resolver(configuration['scope'], source=root.source)(sheet_file['artifact_ref'], 'artifact') is False
        assert _tables(store.db) == before
        proof.update(closed_replay_completed=True, parent_controlled_projection_only=True,
            root_has_saved_file_grant=False, scientific_parent_has_requested_saved_file_grant=True,
            scientific_bindings=dict(recorded=binding, prior_current=prior_current, current=current_binding))
    except BaseException as error:
        proof['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        if store is not None:
            store.close()
        after = _snapshot(database)
        after_files = _inventory(PREFIX)
        proof['all_tables_exact'] = after == before
        proof['all_files_and_modes_exact'] = after_files == before_files
        proof['database_main_sha256'] = _sha(database.read_bytes())
        proof['original531_proof_unchanged'] = _sha(CLOSED531_PROOF.read_bytes()) == CLOSED531_PROOF_SHA256
        proof['original526_proof_unchanged'] = _sha(RESUME526_PROOF.read_bytes()) == RESUME526_PROOF_SHA256
        proof['passed'] = (proof.get('closed_replay_completed', False) and proof['all_tables_exact']
            and proof['all_files_and_modes_exact'] and proof['original531_proof_unchanged']
            and proof['original526_proof_unchanged'] and proof['database_main_sha256'] == CLOSED531_DATABASE_SHA256)
        _write(proof_path, proof)
        assert proof['all_tables_exact'] and proof['all_files_and_modes_exact']
        assert proof['original531_proof_unchanged'] and proof['original526_proof_unchanged']
        assert proof['database_main_sha256'] == CLOSED531_DATABASE_SHA256
