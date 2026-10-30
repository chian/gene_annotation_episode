"""Actual host input/configuration ports; all model/software bytes synthetic."""
from copy import deepcopy
import asyncio
import hashlib
import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.native_flux_balance_contracts import POLICY
from gene_annotation_episode.tools import ToolRegistry
from test_flux_balance_execution_inputs_704 import selected
from test_flux_balance_result_selection_699 import selector

pytestmark = pytest.mark.skipif('HMMER529_ATTEMPT' not in os.environ, reason='requires bounded529')


def _family(f, *, kind='local', formats=None):
    configuration = {'kind': kind, 'workspace': str(f.workspace), 'policy': deepcopy(POLICY),
        'native_flux_balance': [{'version': 'flux_balance_local_binding_v1',
            'operation': 'perform_flux_balance_analysis', 'mode': 'steady_state_linear_fba',
            'software': deepcopy(f.assignment['requested_job']['native_flux_balance']['software']),
            'model_formats': ['cobra_json'] if formats is None else formats}]}
    return ExecutionEpisodes(None, store=f.store, run_id=f.records.run_id, directory=f.owner.directory,
        resources={'selected-local': configuration}, initial_information={}, tool_registry=ToolRegistry(f.store),
        handoff_unit=1, acquired_record_unit=1, log_window_bytes=64, log_roles=['stdout', 'stderr'])


def test_bound_request_schema_is_detached_and_rejects_unselected_software_format(selected):
    f = selected; family = _family(f)
    schema = family._request_schema('selected-local', selected=True, internal=True, compact=False)
    assert Draft202012Validator(schema).is_valid(f.assignment)
    for fault in ('software', 'format'):
        changed = deepcopy(f.assignment)
        job = changed['requested_job']['native_flux_balance']
        if fault == 'software': job['software']['python_version'] = 'unselected software version'
        else:
            job['model_input']['format'] = 'sbml'
            job['model_input']['original_loader_selection'] = 'sbml_file'
        assert not Draft202012Validator(schema).is_valid(changed)
    request_schema = schema['properties']['requested_job']['anyOf'][1]
    request_schema['allOf'][1]['properties']['native_flux_balance']['properties']['model_input']['properties']['format']['enum'].append('sbml')
    assert family.resources['selected-local']['native_flux_balance'][0]['model_formats'] == ['cobra_json']


def _compact(f):
    job = f.assignment['requested_job']['native_flux_balance']
    return {'version': 'flux_balance_scientific_assignment_v1', 'resource_id': 'selected-local',
        'resource_kind': 'local', 'endpoint': f.assignment['endpoint'],
        'request': {'version': 'flux_balance_scientific_request_v1',
            'operation': job['operation'], 'mode': job['mode'], 'model_input': {
                'file': {'witness_ref': f.source, 'version': None,
                    'artifact_field': 'artifact_ref', 'format': job['model_input']['format']},
                'original_loader_selection': job['model_input']['original_loader_selection'],
                'repository_identifier': None, 'acquisition_receipt_file': None},
            'constraints': None, 'objective': deepcopy(job['objective']),
            'solver_options': deepcopy(job['solver_options'])},
        'progress_requirements': deepcopy(f.assignment['progress_requirements']),
        'completion_keys': deepcopy(f.assignment['completion_keys']),
        'constraints': deepcopy(f.assignment['constraints'])}


def _compact_launch(f, assignment):
    return {'version': 'flux_balance_scientific_launch_v1',
        'requests': {'selected-local': deepcopy(assignment)},
        'constraints': deepcopy(plain(f.parent.assignment)['constraints'])}


def test_public_fba_commission_has_scientific_operands_without_software_closure(selected):
    f = selected; family = _family(f); compact = _compact(f)
    schema = family.assignment_schema('launch_local')
    assert Draft202012Validator(schema).is_valid(compact)
    assert not Draft202012Validator(schema).is_valid(f.assignment)
    information, = [row for row in family.resource_tool_contracts() if row['name'] == 'perform_flux_balance_analysis']
    assert Draft202012Validator(information['input_schema']).is_valid(compact['request'])
    assert information['description'] and information['instructions']
    assert information['invocation_route'] == {'kind': 'commission', 'routes': [{
        'entry_role': 'launch', 'resource_id': 'selected-local', 'resource_role': 'launch_local'}]}
    text = canonical(family.assignment_schema('launch')) + canonical(schema) + canonical(information)
    for private in ('implementation_files', 'runtime_files', 'solver_runtime_files',
            'source_function_sha256', 'fba_software_v1', 'PYTHONPATH'):
        assert private not in text
    assert Draft202012Validator(family.assignment_schema('launch')).is_valid(_compact_launch(f, compact))


def test_compact_source_witness_materializes_once_and_preserves_original_request(selected, monkeypatch):
    from gene_annotation_episode.execution_contracts import digest
    from gene_annotation_episode.flux_balance_request_binding import CONTROL_VERSION, read_request_binding
    f = selected; family = _family(f); compact = _compact(f)
    launch = f.records.child(f.records.root, 'launch', _compact_launch(f, compact), 1)
    monkeypatch.setattr(f.store, 'get_artifact', lambda *_: pytest.fail('host read scientific bytes'))
    family.initialize(launch)
    assignment = family.prepare_assignment(launch, 'launch_local', compact, launch.scope, 'compact-resource')
    child = f.records.child(launch, 'launch_local', assignment, 0)
    state = family.initialize(child)
    original = family.flux_balance_inputs.for_start(state)
    control = read_request_binding(f.store, f.records.run_id, child.episode_id)
    assert control['version'] == control['file']['format'] == control['parent_file']['format'] == CONTROL_VERSION
    assert plain(child.assignment) == compact == assignment
    assert plain(child.request)['message']['episode_assignment'] == compact
    assert state.assignment == control['requests'][0]['assignment']
    assert state.assignment['requested_job']['native_flux_balance']['software'] == family.resources[
        'selected-local']['native_flux_balance'][0]['software']
    assert state.assignment['endpoint'] == compact['endpoint']
    assert state.assignment['progress_requirements'] == compact['progress_requirements']
    assert state.assignment['constraints'] == compact['constraints']
    assert original['receipt']['binding']['request_sha256'] == digest(child.request)
    assert original['receipt']['binding']['assignment_sha256'] == digest(state.assignment)
    assert original['receipt']['binding']['model']['witnesses'][0]['reference'] == f.source
    assert family.initial_references(child) == [f.source]
    shown = canonical({'initial': family.initial_decision_context(child),
        'current': family.decision_context(child, {}), 'instructions': family.instructions(child),
        'catalog': family.catalog(child)})
    for private in ('implementation_files', 'runtime_files', 'solver_runtime_files',
            'source_function_sha256', 'fba_software_v1', 'PYTHONPATH'):
        assert private not in shown
    source = f.store.get(f.source); source['artifact_ref'] = f.store.artifact(b'later source alias')
    f.store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(source), f.source))
    get = f.store.get
    def without_source(reference):
        assert reference != f.source, 'reopened compact control rebound its source witness'
        return get(reference)
    monkeypatch.setattr(f.store, 'get', without_source)
    assert family.initialize(child).assignment == state.assignment
    assert family.flux_balance_inputs.for_start(state) == original
    assert family.initial_references(child) == [f.source]
    assert f.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


def test_compact_selection_rejects_ambiguous_software_and_changed_parent_request(selected):
    f = selected; family = _family(f); compact = _compact(f)
    extra = deepcopy(family.resources['selected-local']['native_flux_balance'][0])
    extra['software']['python_version'] = 'another explicitly configured software closure'
    family.resources['selected-local']['native_flux_balance'].append(extra)
    with pytest.raises(ValueError, match='binding_ambiguous'):
        family.prepare_assignment(f.records.root, 'launch', _compact_launch(f, compact),
            f.records.scope, 'ambiguous-compact')
    family.resources['selected-local']['native_flux_balance'].pop()
    launch = f.records.child(f.records.root, 'launch', _compact_launch(f, compact), 1)
    family.initialize(launch)
    changed = deepcopy(compact); changed['request']['objective'] = {'kind': 'single_reaction', 'reaction_id': 'changed'}
    with pytest.raises(ValueError, match='execution_original_request_conflict'):
        family.prepare_assignment(launch, 'launch_local', changed, launch.scope, 'changed-compact')


def test_compact_resource_initializes_before_its_runtime_episode_is_saved(selected):
    f = selected; family = _family(f); compact = _compact(f)
    launch = f.records.child(f.records.root, 'launch', _compact_launch(f, compact), 1)
    family.initialize(launch)
    child = f.records.child(launch, 'launch_local', compact, 0, save=False, action=False)
    state = family.initialize(child)
    received = family.flux_balance_inputs.received(child)
    assert state.assignment['endpoint'] == compact['endpoint']
    assert plain(child.assignment) == compact
    assert received['receipt']['binding']['episode_id'] == child.episode_id
    with pytest.raises(ValueError, match='saved_context_required'):
        family.flux_balance_inputs.for_start(state)


def _selected_compact_action(f, tool_name='practical.inspect', *, legacy=False):
    family = _family(f); compact = _compact(f)
    launch = f.records.child(f.records.root, 'launch', _compact_launch(f, compact), 1)
    if legacy:
        from gene_annotation_episode.flux_balance_request_binding import LEGACY_CONTROL_VERSION
        _, rows = family.flux_balance_requests.preview(launch, plain(launch.assignment))
        family.flux_balance_requests._write(launch, rows, version=LEGACY_CONTROL_VERSION)
    family.initialize(launch)
    child = f.records.child(launch, 'launch_local', compact, 0)
    family.initialize(child)
    action = {'kind': 'tool', 'tool': tool_name, 'arguments': {}}
    f.records.journal.save('runtime_actions', {'episode_id': child.episode_id, 'decision_index': 0,
        'action': canonical(action), 'result': None, 'credit': None})
    return family, child, f'{f.records.run_id}:{child.episode_id}:0'


def test_async_fba_start_authenticates_store_on_owning_thread_before_preparation(selected, monkeypatch):
    """Reach the real threaded preparation boundary; dispatch no native work."""
    from threading import get_ident
    f = selected; family, child, key = _selected_compact_action(f, 'practical.job.start')
    owning_thread = get_ident()
    original_reader = family.flux_balance_inputs.for_start
    controls, preparation_threads = [], []
    def read_original(state):
        assert get_ident() == owning_thread, 'authenticated Store crossed the thread boundary'
        control = original_reader(state)
        controls.append(deepcopy(control))
        return control
    family._practical['selected-local'].flux_balance_input_reader = read_original
    def preparation_boundary(state, operation_key, *, root, policy, input_binding_receipt, input_binding_file):
        preparation_threads.append(get_ident())
        assert get_ident() != owning_thread
        assert operation_key == key and state.episode_id == child.episode_id
        assert policy.to_dict() == POLICY
        assert input_binding_receipt == controls[0]['receipt'] and input_binding_file == controls[0]['file']
        assert not (root / 'native.json').exists()
        raise RuntimeError('verified original input reached threaded preparation boundary')
    monkeypatch.setattr('gene_annotation_episode.native_flux_balance_local.prepare_local_flux_balance', preparation_boundary)
    with pytest.raises(RuntimeError, match='verified original input reached threaded preparation boundary'):
        asyncio.run(family.execute(child, 'practical.job.start', {}, key))
    assert len(controls) == len(preparation_threads) == 1
    assert family.state(child).receipts() == []
    assert not list(f.workspace.rglob('native.json'))
    assert f.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


@pytest.mark.parametrize('fault', ['assignment', 'arguments', 'tool'])
def test_direct_async_invalid_fba_selection_precedes_input_reader_and_preparation(selected, monkeypatch, fault):
    from types import SimpleNamespace
    f = selected; family, child, key = _selected_compact_action(f, 'practical.job.start')
    original = family.state(child)
    state = SimpleNamespace(assignment=deepcopy(original.assignment), run_id=original.run_id,
        episode_id=original.episode_id, receipts=original.receipts, context=original.context)
    operations = family._practical['selected-local']._operations('local')
    def no_input_side_effect(*_args, **_kwargs):
        pytest.fail('invalid direct selection reached authenticated input/native preparation')
    operations.flux_balance_input_reader = no_input_side_effect
    monkeypatch.setattr('gene_annotation_episode.native_flux_balance_local.prepare_local_flux_balance', no_input_side_effect)
    tool_name, arguments = 'practical.job.start', {}
    if fault == 'assignment':
        state.assignment['requested_job']['native_flux_balance']['software']['python_version'] = 'unselected'
        expected = 'not_bound'
    elif fault == 'arguments':
        arguments = {'argv': ['invalid\0argument']}
        expected = 'invalid_practical_command_argument'
    else:
        tool_name = 'practical.not-an-operation'
        expected = 'practical_operation_not_bound'
    with pytest.raises(ValueError, match=expected):
        asyncio.run(operations.execute(state, tool_name, arguments, key))
    assert original.receipts() == []
    assert not list((original.directory / 'intents').iterdir())
    assert not list(f.workspace.rglob('native.json'))
    assert f.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


def test_compact_completed_private_action_reopens_before_public_commit_without_execution(selected, monkeypatch):
    from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
    f = selected; family, child, key = _selected_compact_action(f)
    original = asyncio.run(family.execute(child, 'practical.inspect', {}, key))
    assert original['result']['version'] == 'flux_balance_practical_outcome_v2'
    receipt, = family.state(child).receipts()
    assert f.records.journal.row('runtime_actions', child.episode_id, 0)['result'] is None
    async def no_execution(*_args, **_kwargs):
        pytest.fail('completed private action replayed its operation')
    monkeypatch.setattr(LocalPracticalOperations, 'execute', no_execution)
    descriptor = family.as_record()
    restored = ExecutionEpisodes(None, store=f.store, run_id=f.records.run_id, directory=f.owner.directory,
        tool_registry=ToolRegistry(f.store), **descriptor['configuration'])
    assert restored.initialize(child).receipts() == [receipt]
    assert asyncio.run(restored.execute(child, 'practical.inspect', {}, key)) == original
    f.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0',
        (canonical(original), f.records.run_id, child.episode_id))
    assert restored.credit_view(child, {})['credit'] == 0
    assert restored.completion_for_action(child, key) is None
    assert restored.state(child).receipts() == [receipt]
    assert f.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


def test_legacy_compact_control_recovery_and_committed_replay_keep_original_projection(selected, monkeypatch):
    from gene_annotation_episode.episode_bindings import BindingContext
    from gene_annotation_episode.flux_balance_request_binding import LEGACY_CONTROL_VERSION, read_request_binding
    from gene_annotation_episode.native_file_capture import retained_native_file
    from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
    f = selected; family, child, key = _selected_compact_action(f, legacy=True)
    original_control = read_request_binding(f.store, f.records.run_id, child.episode_id)
    parent_value = json.loads(retained_native_file(f.store, original_control['parent_file']).read_bytes())
    launch = BindingContext(**parent_value['context'])
    original_parent = read_request_binding(f.store, f.records.run_id, launch.episode_id)
    assert original_control['version'] == original_control['file']['format'] == LEGACY_CONTROL_VERSION
    assert original_parent['version'] == LEGACY_CONTROL_VERSION
    outcome = asyncio.run(family.execute(child, 'practical.inspect', {}, key))
    assert outcome['result']['version'] == 'flux_balance_practical_outcome_v1'
    f.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0',
        (canonical(outcome), f.records.run_id, child.episode_id))
    original_receipts = family.state(child).receipts()
    f.store.db.execute('DELETE FROM runtime_flux_balance_request_bindings WHERE run_id=?', (f.records.run_id,))
    descriptor = family.as_record()
    restored = ExecutionEpisodes(None, store=f.store, run_id=f.records.run_id, directory=f.owner.directory,
        tool_registry=ToolRegistry(f.store), **descriptor['configuration'])
    restored.initialize(launch)
    restored.initialize(child)
    assert read_request_binding(f.store, f.records.run_id, launch.episode_id) == original_parent
    assert read_request_binding(f.store, f.records.run_id, child.episode_id) == original_control
    async def no_execution(*_args, **_kwargs):
        pytest.fail('legacy committed receipt replayed its operation')
    monkeypatch.setattr(LocalPracticalOperations, 'execute', no_execution)
    assert asyncio.run(restored.execute(child, 'practical.inspect', {}, key)) == outcome
    assert restored.credit_view(child, {})['credit'] == 0
    assert restored.state(child).receipts() == original_receipts
    assert f.records.journal.row('runtime_actions', child.episode_id, 0)['result'] == canonical(outcome)
    assert f.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


@pytest.mark.parametrize('interrupted_at', ['reserved', 'private_receipt'])
def test_compact_reserved_or_unpublished_metadata_action_recovers_original_selection(selected, monkeypatch, interrupted_at):
    from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
    from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
    f = selected; family, child, key = _selected_compact_action(f)
    actual_execute, actual_publish = LocalPracticalOperations.execute, PracticalReceiptInformation.publish
    async def interrupted_operation(*_args, **_kwargs):
        raise RuntimeError('selected metadata action interrupted after reservation')
    def interrupted_publication(*_args, **_kwargs):
        raise RuntimeError('selected metadata action interrupted after private receipt')
    if interrupted_at == 'reserved': monkeypatch.setattr(LocalPracticalOperations, 'execute', interrupted_operation)
    else: monkeypatch.setattr(PracticalReceiptInformation, 'publish', interrupted_publication)
    with pytest.raises(RuntimeError, match='selected metadata action interrupted'):
        asyncio.run(family.execute(child, 'practical.inspect', {}, key))
    state = family.state(child)
    intents = {path.name: path.read_bytes() for path in (state.directory / 'intents').iterdir()}
    assert len(intents) == 1
    assert len(state.receipts()) == (interrupted_at == 'private_receipt')
    monkeypatch.setattr(PracticalReceiptInformation, 'publish', actual_publish)
    async def no_repeated_operation(*_args, **_kwargs):
        pytest.fail('unpublished completed metadata action was executed again')
    monkeypatch.setattr(LocalPracticalOperations, 'execute',
        actual_execute if interrupted_at == 'reserved' else no_repeated_operation)
    descriptor = family.as_record()
    restored = ExecutionEpisodes(None, store=f.store, run_id=f.records.run_id, directory=f.owner.directory,
        tool_registry=ToolRegistry(f.store), **descriptor['configuration'])
    result = asyncio.run(restored.execute(child, 'practical.inspect', {}, key))
    assert result['status'] == 'completed'
    assert {path.name: path.read_bytes() for path in (state.directory / 'intents').iterdir()} == intents
    receipt, = restored.state(child).receipts()
    assert receipt['operation_key'] == key and receipt['tool_name'] == 'practical.inspect'
    reference, = result['record_refs']
    assert PracticalReceiptInformation(f.store, f.records.run_id).read(reference, child.scope)['receipt'] == receipt
    assert f.records.journal.row('runtime_actions', child.episode_id, 0)['result'] is None
    assert f.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


@pytest.mark.parametrize('fault', ['body', 'added_reference', 'changed_references', 'status', 'pending',
    'malformed_result', 'projection_downgrade'])
def test_compact_direct_practical_readers_reject_changed_committed_view(selected, fault):
    from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
    f = selected; family, child, key = _selected_compact_action(f)
    original = asyncio.run(family.execute(child, 'practical.inspect', {}, key))
    f.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0',
        (canonical(original), f.records.run_id, child.episode_id))
    reference, = original['record_refs']
    receipt, = family.state(child).receipts()
    assert family.credit_view(child, {})['credit'] == 0
    altered = deepcopy(original)
    if fault == 'body': altered['result']['job'] = {'status': 'completed', 'returncode': 0}
    elif fault == 'added_reference': altered['record_refs'].append(f.artifact)
    elif fault == 'changed_references': altered['changed_record_refs'] = []
    elif fault == 'status': altered['status'] = 'partial'
    elif fault == 'pending': altered['pending_work_after_action'] = {'version': 'invalid-pending-packet'}
    elif fault == 'projection_downgrade': altered['result']['version'] = 'flux_balance_practical_outcome_v1'
    else: altered = []
    try:
        f.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0',
            (canonical(altered), f.records.run_id, child.episode_id))
        for read in (lambda: family.credit_view(child, {}),
                lambda: family.completion_for_action(child, key),
                lambda: family.practical_estimator(child),
                lambda: family.state(child),
                lambda: PracticalReceiptInformation(f.store, f.records.run_id).read(reference, child.scope)):
            with pytest.raises(ValueError, match='public_outcome_conflict|invalid_wait_record'):
                read()
    finally:
        f.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0',
            (canonical(original), f.records.run_id, child.episode_id))
    assert family.state(child).receipts() == [receipt]
    assert f.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


@pytest.fixture
def retained_practical217():
    """Original observations are projection inputs, never a new native attempt."""
    root = Path(__file__).resolve().parents[1] / (
        'verification/tool_graders_hmmer_map_verification_2026-10-28_529/check217_fba_rhea_workflows/workflow716')
    state = 'run/practical-execution/dd7f0a5018e620060b947c2812960f86329595c78603d31eda5f7c07006051de/'
    pins = {
        'assignment': (state + 'assignment.json', 'f9baa7f6c4db8e6f0c415d76f6d8be634da180a73f9bce97432ca191204d79f2'),
        'start': (state + 'receipts/900a61859eee23a8ec8690b5fd1bb92890297f514c7e1cc0e97caffde40ffbba.json',
            '08473a533bd9e94199578658ae63a939dfc876c802e3b65ad82b629c6ab543f1'),
        'collect': (state + 'receipts/4df4409401e5e4712d114b27f612957dbf58b063e1376a6221966bae9153c067.json',
            '5cd3c8b5d064cedd82da877874ca7b0f67f07f8d9e097440eb6a4ec46933540f'),
        'decision': ('decision-4.json', '73a4c70a896e648da65542e195038447df86fc36a7cbcdbc53b37e6271876e7d')}
    values = {}
    for name, (path, sha256) in pins.items():
        raw = (root / path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == sha256
        values[name] = json.loads(raw)
    values['assignment'] = values['assignment']['assignment']
    values['public_start'] = values.pop('decision')['context']['last_local_outcome']
    return values


@pytest.mark.parametrize('phase', ['start', 'collect'])
def test_v2_projection_names_authentic_original_output_roles_without_native_reads(retained_practical217, monkeypatch, phase):
    from gene_annotation_episode.flux_balance_request_binding import CONTROL_VERSION, practical_outcome_view
    original = retained_practical217
    receipt = original[phase]
    private = deepcopy(receipt)
    monkeypatch.setattr(Path, 'read_bytes', lambda *_args: pytest.fail('projection read native/control bytes'))
    view = practical_outcome_view(receipt, assignment=original['assignment'], control_version=CONTROL_VERSION)
    assert view['version'] == 'flux_balance_practical_outcome_v2'
    assert [row['role'] for row in view['outputs']] == ['original_model', 'selected_request',
        'effective_model', 'effective_problem', 'solution', 'flux_csv', 'native_log', 'manifest', 'stdout', 'stderr']
    assert [{key: value for key, value in row.items() if key != 'role'} for row in view['outputs']] == [
        {key: row[key] for key in ('available', 'bytes', 'writer_closed')}
        for row in receipt['outcome']['native_outcome']['observed_outputs']]
    assert view['job'] == {key: receipt['outcome']['facts']['requested_job'][key] for key in ('status', 'returncode')}
    assert '.episode-operations' not in canonical(view) and 'requested_output:' not in canonical(view)
    assert receipt == private


def test_retained_v1_projection_is_exact_and_v2_rejects_downgrade_and_unknown_roles(retained_practical217):
    from gene_annotation_episode.flux_balance_request_binding import (
        CONTROL_VERSION, LEGACY_CONTROL_VERSION, match_practical_public_outcome, practical_outcome_view)
    original = retained_practical217
    receipt, public = original['start'], original['public_start']
    reference, = public['record_refs']
    assert practical_outcome_view(receipt, control_version=LEGACY_CONTROL_VERSION) == public['result']
    match_practical_public_outcome(public, receipt, reference, control_version=LEGACY_CONTROL_VERSION)
    options = {'assignment': original['assignment'], 'control_version': CONTROL_VERSION}
    corrected = {**public, 'result': practical_outcome_view(receipt, **options)}
    match_practical_public_outcome(corrected, receipt, reference, **options)
    for fault in ('downgrade', 'availability'):
        changed = deepcopy(public if fault == 'downgrade' else corrected)
        if fault == 'availability': changed['result']['outputs'][0]['available'] = not changed['result']['outputs'][0]['available']
        with pytest.raises(ValueError, match='public_outcome_conflict'):
            match_practical_public_outcome(changed, receipt, reference, **options)
    for fault in ('unknown', 'duplicate'):
        changed = deepcopy(receipt)
        outputs = changed['outcome']['native_outcome']['observed_outputs']
        if fault == 'unknown': outputs[0]['role'] += '-unselected'
        else: outputs[1]['role'] = outputs[0]['role']
        with pytest.raises(ValueError, match='public_output_role_conflict|public_output_role_ambiguous'):
            practical_outcome_view(changed, **options)


def test_compact_bound_source_retains_its_received_witness_and_pointer(selected, monkeypatch):
    f = selected; family = _family(f); compact = _compact(f)
    artifact = f.store.artifact(canonical({'bounds': {'lower': 0, 'upper': 0}}))
    source = f.store.put('source', {'provider': 'synthetic707_bounds', 'accession': 'selected-zero-bounds',
        'artifact_ref': f.store.artifact(b'supplied synthetic bound provenance'),
        'text_ref': artifact, 'request_ref': None, 'uri': None,
        'version': None, 'retrieved_at': None}, origin='tool', scope=f.records.scope)['id']
    f.records.receipts.receive(f.records.root.episode_id, [source], kind='initial')
    compact['request']['constraints'] = [{'reaction_id': 'supplied-reaction', **{side: {
        'kind': 'finite', 'value': 0, 'source': {'file': {'witness_ref': source, 'version': None,
            'artifact_field': 'text_ref', 'format': 'application/json'}, 'pointer': '/bounds/' + side}}
        for side in ('lower', 'upper')}}]
    launch = f.records.child(f.records.root, 'launch', _compact_launch(f, compact), 1)
    monkeypatch.setattr(f.store, 'get_artifact', lambda *_: pytest.fail('host parsed scientific bound bytes'))
    family.initialize(launch)
    child = f.records.child(launch, 'launch_local', compact, 0)
    state = family.initialize(child)
    received = family.flux_balance_inputs.for_start(state)
    change, = state.assignment['requested_job']['native_flux_balance']['constraints']
    assert family.initial_references(child) == [f.source, source]
    for side in ('lower', 'upper'):
        assert change[side]['source']['file']['artifact_ref'] == artifact
        assert change[side]['source']['pointer'] == '/bounds/' + side
    original_get = f.store.get
    def without_bound_source(reference):
        assert reference != source, 'reopened control rebound a bound source'
        return original_get(reference)
    monkeypatch.setattr(f.store, 'get', without_bound_source)
    assert family.initialize(child).assignment == state.assignment
    assert family.flux_balance_inputs.for_start(state) == received


def test_compact_completed_output_endpoint_preserves_selected_roles_and_keys(selected):
    from gene_annotation_episode.practical_execution_records import flux_balance_role_paths, validate_assignment
    f = selected; family = _family(f); compact = _compact(f)
    compact['endpoint'] = 'completed_job_outputs'
    compact['progress_requirements'] = [{'key': 'selected-outputs', 'credit': 9,
        'predicate': {'kind': 'requested_job_outputs', 'output_roles': ['solution', 'flux_csv']}}]
    compact['completion_keys'] = ['selected-outputs']
    launch = f.records.child(f.records.root, 'launch', _compact_launch(f, compact), 1)
    family.initialize(launch)
    child = f.records.child(launch, 'launch_local', compact, 0)
    assignment = family.initialize(child).assignment
    assert assignment['endpoint'] == compact['endpoint']
    assert assignment['progress_requirements'] == compact['progress_requirements']
    assert assignment['completion_keys'] == compact['completion_keys']
    roles = compact['progress_requirements'][0]['predicate']['output_roles']
    with pytest.raises(ValueError, match='original_execution_required'):
        flux_balance_role_paths(assignment, {'execution_id': 'unselected-future-action'}, roles)
    generic = deepcopy(assignment)
    generic['requested_job'] = {'argv': ['/bin/true'], 'environment': {}}
    generic.pop('native_flux_balance_execution')
    with pytest.raises(ValueError, match='output_roles_require_fba'):
        validate_assignment(generic)


@pytest.mark.parametrize('changed_execution', [False, True])
def test_forwarded_fba_role_qualification_uses_actual_paths_without_claiming_completion(selected, monkeypatch, changed_execution):
    """Operational port composition only; no native or scientific result is fabricated."""
    from gene_annotation_episode.execution_contracts import digest
    from gene_annotation_episode.practical_execution_records import flux_balance_role_paths
    f = selected; family = _family(f); assignment = deepcopy(f.assignment)
    assignment['endpoint'] = 'completed_job_outputs'
    assignment['progress_requirements'] = [{'key': 'selected-outputs', 'credit': 9,
        'predicate': {'kind': 'requested_job_outputs', 'output_roles': ['solution', 'flux_csv']}}]
    assignment['completion_keys'] = ['selected-outputs']
    launch_assignment = plain(f.parent.assignment)
    launch_assignment['requests']['selected-local'] = assignment
    launch = f.records.child(f.records.root, 'launch', launch_assignment, 1)
    child = f.records.child(launch, 'launch_local', assignment, 0)
    family.initialize(child)
    delegate = family._practical['selected-local']
    operations = delegate._operations('local')
    execution_id = str(f.workspace / 'forwarded-original' / 'native.json')
    job = {'argv': assignment['requested_job']['argv'], 'environment': assignment['requested_job']['environment'],
        'returncode': None, 'execution_id': execution_id,
        'requested_job_sha256': digest(assignment['requested_job']), 'resource_kind': 'local',
        'status': 'running', 'output_paths': [], 'handoff': {'execution_id': execution_id,
            'monitor_operation': 'practical.job.status', 'results_operation': 'practical.job.collect'}}
    paths = flux_balance_role_paths(assignment, job, ['solution', 'flux_csv'])
    for path in paths:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b'operational path-presence fixture; no scientific measurement')
    job['output_paths'] = paths
    source_state = object()
    monkeypatch.setattr(delegate, '_received_target', lambda _context, _reference: (source_state, execution_id))
    async def running_observation(state, tool_name, arguments, operation_key):
        assert state is source_state and tool_name == 'practical.job.status' and arguments == {}
        observed = deepcopy(job)
        if changed_execution:
            observed['execution_id'] = str(f.workspace / 'wrong-original' / 'native.json')
            observed['handoff']['execution_id'] = observed['execution_id']
        return {'facts': {'requested_job': observed}}, None
    monkeypatch.setattr(operations, 'execute', running_observation)
    monkeypatch.setattr(delegate, '_operations', lambda _kind: operations)
    # This isolated port test does not publish its supplied operational facts
    # as a real selected native receipt or bypass the original receipt reader.
    delegate.store = None
    result = asyncio.run(delegate.execute(child, 'practical.job.status', {'receipt_ref': 'operational-port-fixture'},
        f'{f.records.run_id}:{child.episode_id}:0'))
    receipt = result['result']
    if changed_execution:
        assert receipt['validations'] == []
        assert receipt['outcome']['native_outcome']['failure']['code'] == 'practical_received_execution_target_changed'
    else:
        assert not receipt['validations'][0]['satisfied']
        assert receipt['outcome']['facts']['requested_job'] == job
        assert [row['path'] for row in receipt['validations'][0]['evidence']['value']['paths']] == paths
        assert all(row['exists'] for row in receipt['validations'][0]['evidence']['value']['paths'])
    assert delegate.state(child).completion_proof() is None


def test_nonlocal_fba_registration_rejects_before_transport(selected):
    with pytest.raises(ValueError, match='native_flux_balance_resource_execution_binding_unfinished:hpc'):
        _family(selected, kind='pbs_ssh')


def test_original_launch_and_resource_admission_use_metadata_not_scientific_bytes(selected, monkeypatch):
    f = selected; family = _family(f)
    monkeypatch.setattr(f.store, 'get_artifact', lambda *_: pytest.fail('host read FBA scientific bytes'))
    assignment = family.prepare_assignment(f.records.root, 'launch', plain(f.parent.assignment),
        f.parent.scope, 'selected-parent-admission')
    assert assignment == plain(f.parent.assignment)
    selected_job = family.prepare_assignment(f.parent, 'launch_local', f.assignment,
        f.parent.scope, 'selected-resource-admission')
    assert selected_job == f.assignment
    assert family.initial_references(f.parent) == [f.source]


@pytest.mark.parametrize('source_change', ['mutate', 'delete'])
def test_resource_initialize_and_reopen_keep_frozen_sources_and_original_reader(selected, monkeypatch, source_change):
    f = selected; family = _family(f); context = f.child()
    monkeypatch.setattr(f.store, 'get_artifact', lambda *_: pytest.fail('host read FBA scientific bytes'))
    state = family.initialize(context)
    original = family.flux_balance_inputs.for_start(state)
    operations = family._practical['selected-local']._operations('local')
    assert operations.flux_balance_input_reader.__self__ is family.flux_balance_inputs
    assert operations.flux_balance_input_reader(state) == original
    if source_change == 'mutate':
        source = f.store.get(f.source);source['artifact_ref'] = f.store.artifact(b'changed later source primary')
        f.store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(source), f.source))
    else:
        f.store.db.execute('DELETE FROM records WHERE id=?', (f.source,))
    get = f.store.get
    def without_current_source(ref):
        assert ref != f.source, 'host rebound receiving control to current source'
        return get(ref)
    monkeypatch.setattr(f.store, 'get', without_current_source)
    assert family.initialize(context).assignment == state.assignment
    assert family.flux_balance_inputs.for_start(state) == original
    assert family.initial_references(context) == [f.source]
    assert family.state(context).receipts() == []
    assert f.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


def test_descriptor_reconstruction_installs_original_receiver_without_serializing_callback(selected):
    f = selected; family = _family(f); context = f.child()
    state = family.initialize(context); original = family.flux_balance_inputs.for_start(state)
    record = family.as_record(); json.dumps(record, allow_nan=False)
    assert 'flux_balance_input_reader' not in canonical(record)
    restored = ExecutionEpisodes(None, store=f.store, run_id=f.records.run_id, directory=f.owner.directory,
        tool_registry=ToolRegistry(f.store), **record['configuration'])
    assert restored.as_record() == record
    operation = restored._practical['selected-local']._operations('local')
    assert operation.flux_balance_input_reader.__self__ is restored.flux_balance_inputs
    assert operation.flux_balance_input_reader(restored.initialize(context)) == original


def test_received_optional_mode_cannot_rebind_missing_initialized_controls(selected):
    f = selected; family = _family(f); context = f.child()
    assert family.flux_balance_inputs.received(context, required=False) is None
    family.initialize(context)
    root = family.flux_balance_inputs._directory(context)
    for path in root.iterdir(): path.unlink()
    root.rmdir()
    with pytest.raises(ValueError, match='original_control_required'):
        family.flux_balance_inputs.received(context, required=False)
    with pytest.raises(ValueError): family.initialize(context)


@pytest.mark.parametrize('kind', ['source', 'artifact'])
def test_first_admission_preserves_protected_reference_denial(selected, monkeypatch, kind):
    f = selected; family = _family(f); context = f.child()
    denied = f.source if kind == 'source' else f.artifact
    monkeypatch.setattr(family, 'resolve_received_reference',
        lambda _context, reference, namespace: False if reference == denied else None)
    with pytest.raises(ValueError, match='protected_reference_denied'):
        family.initialize(context)
    assert not family.flux_balance_inputs._directory(context).exists()


@pytest.mark.parametrize('mode', ['native_result', 'saved_sheet_recalculation'])
def test_results_schema_and_selector_use_existing_modes_and_common_job(selected, selector, mode):
    f = selected; family = _family(f)
    selector['mode'] = mode
    if mode == 'saved_sheet_recalculation':
        selector['saved_sheet_file'] = {'artifact_ref': 'artifact_' + 'a' * 64,
            'sha256': 'a' * 64, 'size_bytes': 17, 'format': 'flux_balance_sheet_v1'}
    assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': 'selected-original-handoff',
        'selector': selector}
    schema = family.assignment_schema('results')
    assert Draft202012Validator(schema).is_valid(assignment)
    target = {'resource_kind': 'local', 'assignment': f.assignment}
    assert family._selector(assignment, target) == selector
    invalid = deepcopy(assignment);invalid['selector']['calculation_parameters']['objective_absolute_tolerance'] = True
    assert not Draft202012Validator(schema).is_valid(invalid)
    with pytest.raises(ValueError): family._selector(invalid, target)
    with pytest.raises(ValueError, match='flux_balance_result_target_conflict'):
        family._selector(assignment, {'resource_kind': 'local', 'assignment': {'requested_job': {}}})


def test_installed_result_and_receiver_sources_are_exact_common_declarations(selected):
    from gene_annotation_episode.flux_balance_return_views import fba_fact_sources
    from gene_annotation_episode.flux_balance_returns import FluxBalanceReturns
    from gene_annotation_episode.native_flux_balance_results import NativeFluxBalanceResults
    family = _family(selected)
    assert isinstance(family.native_flux_balance_results, NativeFluxBalanceResults)
    assert isinstance(family.native_flux_balance_returns, FluxBalanceReturns)
    expected = fba_fact_sources()
    assert {k: family.fact_sources('results')[k] for k in expected} == expected
    assert {k: family.received_report_sources('scientific_process')[k] for k in expected} == expected
    assert {k: family.received_report_sources('annotation')[k] for k in expected} == expected
    assert not set(expected).intersection(family.received_report_sources('launch'))
