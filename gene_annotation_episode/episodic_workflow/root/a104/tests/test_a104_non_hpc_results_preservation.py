"""Engineered original Results commissions at the actual preparation boundary.

Store, Journal, typed requests, EPR and receipt traversal are real. No service,
scientific producer or Workflow is executed by these controlled journal frames.

A104 adaptation uses two actual non-HPC Results constructors and original saved receipt boundaries."""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace
from gene_annotation_episode.episodic_workflow.root.a104.method_loop import EpisodeGoal, EpisodeRequest
from gene_annotation_episode.episodic_workflow.root.a104.method_loop.identities import EpisodeRef
import pytest
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.a104.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.a104.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a104.runtime import Record, TypedReportContract
from gene_annotation_episode.episodic_workflow.root.a104.state import Store
import importlib
from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources
HOMES = ('execution_result_acquisition', 'evolutionary_history_evidence/execution_result_acquisition')

def own_module(name):
    return importlib.import_module('gene_annotation_episode.episodic_workflow.root.a104.' + name.replace('/', '.'))

def parent_path(binding_home):
    assert binding_home in HOMES
    path = (('annotation', 'root'),)
    if binding_home.startswith('evolutionary_history_evidence/'):
        path += (('evolutionary_history_evidence', 'original-A104'),)
    return path

@pytest.fixture(params=HOMES)
def binding_home(request):
    return request.param

def forbidden(*_args, **_kwargs):
    raise AssertionError('proven Results restoration must not prepare or read native payloads')

def rows(store):
    return {row[0]: sorted((tuple(value) for value in store.db.execute('SELECT * FROM "' + row[0] + '"'))) for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}

class ResultsFrame:
    index = 1

    def __init__(self, store, *, receipts=True, binding_home):
        self.store, self.run_id = (store, 'recorded-results-engineering')
        self.journal = Journal(store, self.run_id)
        self.receipts = EpisodeReceipts(store, self.run_id) if receipts else None
        self.scope = {'subject_refs': store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']}
        handoff = self.source('original handoff metadata')
        result = self.source('original returned data')
        self.result_ref = result['id']
        self.assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': handoff['id'], 'selector': {'paths': ['original-output.txt'], 'offset': 0, 'limit': 1}}
        self.schema = {'type': 'object', 'properties': {'sources': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference'}, 'x-source': 'execution_result_refs'}, 'completed': {'type': 'boolean', 'x-source': 'execution_completed'}}, 'required': ['sources', 'completed'], 'additionalProperties': False}
        self.form = {'sources': [self.result_ref], 'completed': False}
        contract = TypedReportContract('Return the selected original data', self.schema, lambda *_: True)
        path = parent_path(binding_home)
        parent_goal = EpisodeGoal.root(objective='Preserve original Results selection', result_contract={'role': path[-1][0]})
        self.parent = self.context(path, parent_goal, {}, None)
        if self.receipts is not None:
            self.receipts.receive(self.parent.episode_id, [handoff['id']], kind='initial')
        child_goal = EpisodeGoal.child(parent_goal, objective='Read selected original rows', result_contract=contract.schema)
        self.child = self.context((*path, ('results', 'child_1')), child_goal, self.assignment, contract, parent=self.parent, state='yielded')
        self.key = f'{self.run_id}:{self.parent.episode_id}:{self.index}'
        self.journal.save('runtime_actions', {'episode_id': self.parent.episode_id, 'decision_index': self.index, 'action': canonical({'kind': 'episode_child', 'role': 'results', 'assignment': self.assignment, 'scope': self.scope, 'purpose': contract.decision, 'schema_json': canonical(self.schema)}), 'result': canonical({'status': 'completed', 'record_refs': [self.result_ref], 'changed_record_refs': []}), 'credit': 0})
        self.journal.save('runtime_forms', {'episode_id': self.child.episode_id, 'facts': canonical({'execution_result_refs': self.form['sources'], 'execution_completed': False}), 'form': canonical(self.form)})
        self.journal.save('runtime_report_attempts', {'parent_episode_id': self.parent.episode_id, 'decision_index': self.index, 'delivery_ref': 'delivery_engineering_results', 'child_episode_id': self.child.episode_id, 'contract': canonical(contract.as_record()), 'form': canonical(self.form), 'failure': None})
        if self.receipts is not None:
            self.receipts.receive(self.parent.episode_id, self.form['sources'], kind='child_form', source_index=self.index)
        owner_type = own_module(binding_home + '/episode').ExecutionEpisode
        self.owner = owner_type(SimpleNamespace(), store=store, run_id=self.run_id, directory=store.path / 'results-frame-workflow', resources=resources(), initial_information={}, tool_registry=None, handoff_unit=1, acquired_record_unit=1, log_window_bytes=1024, log_roles=('stdout', 'stderr'))
        self.owner._retained_masking_target = forbidden
        self.owner.job_progress_provider = SimpleNamespace(targets=SimpleNamespace(read_target=forbidden))

    def source(self, text):
        artifact = self.store.artifact(text)
        return self.store.put('source', {'provider': 'engineering.recorded_results', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'version': 'engineering_v1', 'retrieved_at': None}, origin='caller')

    def context(self, path, goal, assignment, contract, *, parent=None, state='active'):
        episode_id = EpisodeRef(self.run_id, path).episode_id
        message = {'scope': self.scope, 'episode_assignment': assignment, 'initial_report': {}}
        if self.receipts is not None:
            message['knowledge_inheritance'] = self.receipts.bind(episode_id, None if parent is None else parent.episode_id)
        request = EpisodeRequest(goal, Record(message), contract).as_record()
        self.journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path), 'request': canonical(request), 'initial_credit': 0, 'state': state, 'completion': canonical({'ended_by': 'yield_stop', 'actions': 1}) if state == 'yielded' else None, 'archive': None})
        return BindingContext(self.run_id, episode_id, path[-1][0], path, self.scope, assignment, request)

    def prepare(self, *, assignment=None, scope=None, key=None):
        return self.owner.prepare_assignment(self.parent, 'results', self.assignment if assignment is None else assignment, self.scope if scope is None else scope, self.key if key is None else key)

    def outcome(self, **changes):
        row = self.journal.row('runtime_actions', self.parent.episode_id, self.index)
        value = json.loads(row['result'])
        value.update(changes)
        self.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?', (canonical(value), self.run_id, self.parent.episode_id, self.index))

@pytest.fixture
def frame(tmp_path, binding_home):
    with Store(tmp_path / 'state') as store:
        yield ResultsFrame(store, binding_home=binding_home)

def test_original_results_assignment_is_restored_detached_without_preparation_bytes_or_writes(frame, monkeypatch):
    for path in (frame.store.path / 'artifacts').glob('*/*'):
        path.unlink()
    monkeypatch.setattr(frame.store, 'get_artifact', forbidden)
    before = rows(frame.store)
    result = frame.prepare()
    assert result == frame.assignment == plain(frame.child.assignment)
    assert result is not frame.assignment
    result['selector']['offset'] = 99
    assert frame.prepare()['selector']['offset'] == 0
    assert frame.form['completed'] is False and rows(frame.store) == before

@pytest.mark.parametrize('changed', ['foreign_run', 'foreign_parent', 'leading_zero', 'suffix'])
def test_recorded_results_requires_original_parent_operation_identity(frame, changed):
    key = {'foreign_run': f'other:{frame.parent.episode_id}:1', 'foreign_parent': f'{frame.run_id}:episode_other:1', 'leading_zero': frame.key[:-1] + '01', 'suffix': frame.key + ':typed_form'}[changed]
    with pytest.raises(ValueError, match='recorded_results_admission_operation_required'):
        frame.prepare(key=key)

@pytest.mark.parametrize('changed', ['current_assignment', 'current_scope', 'receiver', 'original_assignment', 'original_scope', 'child_scope', 'child_identity', 'slot', 'contract', 'facts', 'selected_kind', 'receipt'])
def test_recorded_results_rejects_conflicting_original_or_current_commission_metadata(frame, changed):
    assignment, scope = (deepcopy(frame.assignment), deepcopy(frame.scope))
    if changed == 'current_assignment':
        assignment['selector']['offset'] = 1
    elif changed == 'current_scope':
        scope['subject_refs'] = []
    elif changed == 'receiver':
        frame.parent = replace(frame.parent, scope={'subject_refs': []})
    elif changed in {'original_assignment', 'child_scope'}:
        request = plain(frame.child.request)
        if changed == 'original_assignment':
            request['message']['episode_assignment']['selector']['offset'] = 1
        else:
            request['message']['scope']['subject_refs'] = []
        frame.store.db.execute('UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?', (canonical(request), frame.run_id, frame.child.episode_id))
    elif changed in {'original_scope', 'selected_kind'}:
        action = json.loads(frame.journal.row('runtime_actions', frame.parent.episode_id, frame.index)['action'])
        if changed == 'original_scope':
            action['scope']['subject_refs'] = []
        else:
            action['kind'] = 'child'
        frame.store.db.execute('UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=?', (canonical(action), frame.run_id, frame.parent.episode_id, frame.index))
    elif changed == 'child_identity':
        frame.store.db.execute('UPDATE runtime_report_attempts SET child_episode_id=? WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (frame.parent.episode_id, frame.run_id, frame.parent.episode_id, frame.index))
    elif changed == 'slot':
        path = [*plain(frame.child.path[:-1]), ['results', 'child_9']]
        frame.store.db.execute('UPDATE runtime_episodes SET path=? WHERE run_id=? AND episode_id=?', (canonical(path), frame.run_id, frame.child.episode_id))
    elif changed == 'contract':
        request = plain(frame.child.request)
        request['report_contract']['decision'] = 'changed contract'
        frame.store.db.execute('UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?', (canonical(request), frame.run_id, frame.child.episode_id))
    elif changed == 'facts':
        frame.store.db.execute('UPDATE runtime_forms SET facts=? WHERE run_id=? AND episode_id=?', (canonical({'execution_result_refs': [], 'execution_completed': False}), frame.run_id, frame.child.episode_id))
    else:
        frame.store.db.execute('DELETE FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?', (frame.run_id, frame.parent.episode_id, frame.result_ref))
    with pytest.raises(ValueError, match='recorded_results_'):
        frame.prepare(assignment=assignment, scope=scope)

class LivePreparation(Exception):
    pass

def require_live_path(frame, monkeypatch):
    seen = []

    def live(parent, selected, scope):
        assert parent == frame.parent and selected == frame.assignment and (scope == frame.scope)
        seen.append(True)
        raise LivePreparation
    monkeypatch.setattr(frame.owner, '_retained_masking_target', live)
    with pytest.raises(LivePreparation):
        frame.prepare()
    assert seen == [True]

@pytest.mark.parametrize('state', ['first', 'pending', 'partial_status', 'legacy', 'missing_attempt', 'failed_return', 'active_child'])
def test_results_without_successful_completed_original_projection_keeps_live_preparation(frame, monkeypatch, state):
    key = (frame.run_id, frame.parent.episode_id, frame.index)
    if state == 'first':
        frame.store.db.execute('UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=? AND decision_index=?', key)
    elif state == 'pending':
        frame.outcome(status='completed', pending_handle='execution_engineering_pending', record_refs=[])
    elif state == 'partial_status':
        frame.outcome(status='partial')
    elif state == 'legacy':
        frame.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?', (canonical({'status': 'completed'}), *key))
    elif state == 'missing_attempt':
        frame.store.db.execute('DELETE FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?', key)
    elif state == 'failed_return':
        frame.store.db.execute('UPDATE runtime_report_attempts SET failure=? WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (canonical({'reason': 'not received'}), *key))
    else:
        frame.store.db.execute("UPDATE runtime_episodes SET state='active' WHERE run_id=? AND episode_id=?", (frame.run_id, frame.child.episode_id))
    require_live_path(frame, monkeypatch)

def test_results_without_receipt_binding_keeps_live_preparation(tmp_path, monkeypatch, binding_home):
    with Store(tmp_path / 'state') as store:
        require_live_path(ResultsFrame(store, receipts=False, binding_home=binding_home), monkeypatch)

def test_results_member_projection_without_ordinary_receipt_keeps_live_preparation(frame, monkeypatch):
    material = frame.store.register_material(data=b'>engineering\nACGT\n', format='fasta', molecule='dna')
    parsed = frame.store.parse_material(material['id'])
    assert parsed['status'] == 'completed'
    member, = frame.store.material_members(parsed['collection_ref'])['members']
    frame.form['sources'] = [member['id']]
    frame.outcome(record_refs=[member['id']])
    frame.store.db.execute('UPDATE runtime_forms SET facts=?,form=? WHERE run_id=? AND episode_id=?', (canonical({'execution_result_refs': frame.form['sources'], 'execution_completed': False}), canonical(frame.form), frame.run_id, frame.child.episode_id))
    frame.store.db.execute('UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (canonical(frame.form), frame.run_id, frame.parent.episode_id, frame.index))
    frame.receipts.receive(frame.parent.episode_id, [member['id']], kind='child_form', source_index=frame.index)
    assert member['id'] not in set(frame.receipts.known(frame.parent.episode_id))
    require_live_path(frame, monkeypatch)

def test_current_assignment_schema_is_checked_before_recorded_restoration(frame, monkeypatch):
    assignment = {**frame.assignment, 'selector': []}
    monkeypatch.setattr(frame.owner, '_recorded_results_assignment', forbidden)
    with pytest.raises(ValueError, match='invalid_execution_assignment'):
        frame.prepare(assignment=assignment)

def task_case(frame, tmp_path, monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.tests.hpc_planning_allocation_task_behavior import PlanningAllocationTaskBehavior
    monkeypatch.setattr(frame.owner, 'credit_view', lambda context, selection: {'credit': 0.0})
    value = SimpleNamespace(binding=frame.owner, context=frame.child, c={'objective': 'Preserve the original Results action and outcome'})
    adapter = SimpleNamespace(setup=lambda path: value, module=own_module)
    return PlanningAllocationTaskBehavior.fixture(adapter, tmp_path)

@pytest.mark.parametrize('status', ['completed', 'invalid', 'failed', 'unavailable'])
def test_results_task_retains_complete_returned_outcome_and_single_replay(frame, tmp_path, monkeypatch, status):
    import asyncio
    case = task_case(frame, tmp_path, monkeypatch)
    payload = {'status': status, 'record_refs': [frame.result_ref], 'changed_record_refs': [], 'result': {'selected_windows': [{'path': 'original-output.txt', 'offset': 0, 'size': 1}], 'failed_windows': [{'path': 'missing-output.txt', 'code': 'unavailable'}]}, 'feedback': {'category': 'controlled_original_return', 'code': 'retained-' + status}}
    calls = []

    async def returned(source, name, arguments, **kwargs):
        calls.append((name, deepcopy(arguments), kwargs['operation_key']))
        return deepcopy(payload)
    case.task.workflow.execute = returned
    selected = {'kind': 'tool', 'tool': 'execution.results.read', 'arguments': {'path': 'original-output.txt', 'offset': 0, 'limit': 1}}
    result = asyncio.run(case.task.execute(selected, 5))
    assert result == {'index': 5, 'credit': 0.0}
    assert asyncio.run(case.task.execute(selected, 5)) == result
    assert calls == [('execution.results.read', selected['arguments'], f'{frame.run_id}:{case.task.episode_id}:5')]
    assert case.receipts == [(5, status)] and len(case.projections) == 1
    assert json.loads(case.saved[5]['action']) == selected
    assert json.loads(case.saved[5]['result']) == {**payload, 'pending_work_after_action': case.task.workflow.pending_work(case.task)}
    assert case.runtime.observes_action_outcome('tool', status)

@pytest.mark.parametrize('kind,status', [('wait', 'completed'), ('wait', 'failed'), ('reason', 'completed')])
def test_results_task_preserves_historical_action_and_original_credit(frame, tmp_path, monkeypatch, kind, status):
    import asyncio
    case = task_case(frame, tmp_path, monkeypatch)
    selected = {'kind': kind, **({'condition': {'original': 'saved'}} if kind == 'wait' else {'reasoning': {'original': 'saved'}})}
    payload = {'status': status, 'record_refs': [], 'changed_record_refs': [], 'result': {'preserved': 'full original payload'}, 'feedback': {'code': 'original-code'}}
    case.saved[9] = {'episode_id': case.task.episode_id, 'decision_index': 9, 'action': case.runtime._json(selected), 'result': case.runtime._json(payload), 'credit': 7.25}
    if kind == 'wait' and status == 'failed':
        with pytest.raises(case.runtime.ActionFailure):
            asyncio.run(case.task.execute(selected, 9))
    else:
        assert asyncio.run(case.task.execute(selected, 9)) == {'index': 9, 'credit': 7.25}
    assert json.loads(case.saved[9]['action']) == selected
    assert json.loads(case.saved[9]['result']) == payload
    assert case.executions == case.receipts == case.projections == []

def test_results_task_unfinished_wait_returns_once_without_new_credit(frame, tmp_path, monkeypatch):
    import asyncio
    case = task_case(frame, tmp_path, monkeypatch)
    selected = {'kind': 'wait', 'condition': {'original': 'pending'}}
    case.saved[6] = {'episode_id': case.task.episode_id, 'decision_index': 6, 'action': case.runtime._json(selected), 'result': None, 'credit': None}
    waits = []

    async def wait(source, condition, index):
        waits.append((deepcopy(condition), index))
        return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': {'ready': True}}
    case.task.workflow.perform_selected_wait = wait
    case.task.workflow.last_observed_credit = lambda source: 4.5
    assert asyncio.run(case.task.execute(selected, 6)) == {'index': 6, 'credit': 4.5}
    assert asyncio.run(case.task.execute(selected, 6)) == {'index': 6, 'credit': 4.5}
    assert waits == [(selected['condition'], 6)]
    assert case.receipts == [(6, 'completed')] and case.executions == case.projections == []

@pytest.fixture
def runtime_results_frame(tmp_path, binding_home):
    """Controlled handoff through real receipt/state readers; no native run.

    This active Results fixture is separate from metadata-only restoration.
    No target reader, initializer, selector or receipt validator is substituted.
    """
    from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_records import assess_validations, digest
    from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import PracticalState
    from gene_annotation_episode.episodic_workflow.root.a104.practical_receipt_information import PracticalReceiptInformation
    from gene_annotation_episode.episodic_workflow.root.a104.local_jobs import LocalJobPolicy
    with Store(tmp_path / 'runtime-state') as store:
        run_id = 'controlled-results-runtime-selection'
        journal, receipts = Journal(store, run_id), EpisodeReceipts(store, run_id)
        scope = {'subject_refs': store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']}
        workspace = tmp_path / 'runtime-workspace'
        workspace.mkdir()
        report_schema = {'type': 'object', 'properties': {'sources': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference'}, 'x-source': 'execution_result_refs'}, 'completed': {'type': 'boolean', 'x-source': 'execution_completed'}}, 'required': ['sources', 'completed'], 'additionalProperties': False}
        contract = TypedReportContract('Controlled runtime-selection fixture', report_schema, lambda *_: True)

        def saved_context(path, assignment, parent=None):
            episode_id = EpisodeRef(run_id, path).episode_id
            goal = (EpisodeGoal.root(objective='Controlled Results initialization', result_contract={'role': path[-1][0]})
                if parent is None else EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)['goal']),
                    objective='Controlled Results initialization', result_contract=report_schema))
            message = {'scope': scope, 'episode_assignment': assignment, 'initial_report': {},
                'knowledge_inheritance': receipts.bind(episode_id, None if parent is None else parent.episode_id)}
            request = EpisodeRequest(goal, Record(message), None if parent is None else contract).as_record()
            context = BindingContext(run_id, episode_id, path[-1][0], path, scope, assignment, request)
            journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
                'request': canonical(request), 'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
            return context

        parent = None
        for end in range(1, len(parent_path(binding_home)) + 1):
            parent = saved_context(parent_path(binding_home)[:end], {}, parent)
        assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'controlled-results-target',
            'resource_id': 'local', 'resource_kind': 'local', 'workspace': str(workspace),
            'endpoint': 'usable_handoff', 'requested_job': {'argv': ['/not-an-executed-fixture'], 'environment': {}},
            'progress_requirements': [{'key': 'handoff', 'credit': 1., 'predicate': {'kind': 'requested_job_handoff'}}],
            'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
            'inventory_snapshot': {}, 'constraints': {}}
        launch_assignment = {'version': 'execution_launch_assignment_v1', 'requests': {'local': assignment},
            'immutable_input_versions': [], 'constraints': {}}
        launch = saved_context((*parent.path, ('launch', 'controlled')), launch_assignment, parent)
        producer = saved_context((*launch.path, ('launch_local', 'controlled')), assignment, launch)
        state = PracticalState(tmp_path / 'controlled-practical-state', run_id, producer.episode_id, assignment)
        operation_key = f'{run_id}:{producer.episode_id}:0'
        action = {'kind': 'tool', 'tool': 'practical.job.start', 'arguments': {}}
        journal.save('runtime_actions', {'episode_id': producer.episode_id, 'decision_index': 0,
            'action': canonical(action), 'result': None, 'credit': None})
        state.begin(operation_key, action['tool'], action['arguments'])
        execution_id = str(workspace / 'controlled-job-identity')
        outcome = {'facts': {'requested_job': {
            'argv': assignment['requested_job']['argv'], 'environment': {}, 'returncode': None,
            'execution_id': execution_id, 'requested_job_sha256': digest(assignment['requested_job']),
            'resource_kind': 'local', 'status': 'submitted', 'output_paths': [],
            'handoff': {'execution_id': execution_id, 'monitor_operation': 'practical.job.status',
                'results_operation': 'practical.job.collect'}}},
            'native_outcome': {'controlled_test_data': 'no_native_or_scientific_execution'}}
        receipt = state.finish(operation_key, outcome,
            assess_validations(assignment, outcome, state.context(), tool_name=action['tool']))
        information = PracticalReceiptInformation(store, run_id)
        handoff_ref = information.publish(producer, receipt)
        returned = {'status': 'completed', 'record_refs': [handoff_ref], 'changed_record_refs': [], 'result': receipt}
        journal.save('runtime_actions', {'episode_id': producer.episode_id, 'decision_index': 0,
            'action': canonical(action), 'result': canonical(returned), 'credit': state.credit_view()['credit']})
        assert information.read(handoff_ref, scope)['receipt'] == receipt
        receipts.receive(parent.episode_id, [handoff_ref], kind='initial')
        results_assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': handoff_ref,
            'selector': {'path': str(workspace / 'controlled-output.txt'), 'offset': 0, 'limit': 1}}
        child = saved_context((*parent.path, ('results', 'child_1')), results_assignment, parent)
        resources = {'local': {'kind': 'local', 'workspace': str(workspace),
            'policy': LocalJobPolicy.from_config().to_dict()}}
        owner_type = own_module(binding_home + '/episode').ExecutionEpisode
        owner = owner_type(SimpleNamespace(), store=store, run_id=run_id,
            directory=tmp_path / 'runtime-workflow', resources=resources, initial_information={},
            tool_registry=None, handoff_unit=1., acquired_record_unit=1.,
            log_window_bytes=1024, log_roles=('stdout', 'stderr'))
        target = owner.job_progress_provider.targets.read_target(handoff_ref, scope)
        assert target['handle'] == handoff_ref and target['origin_episode_id'] == producer.episode_id
        assert target['assignment'] == assignment and target['scope'] == scope
        assert target['resource_kind'] == 'local' and target['execution_id'] == execution_id
        assert owner._target(child) == target
        assert owner._selector(plain(child.assignment), target) == results_assignment['selector']
        yield SimpleNamespace(owner=owner, child=child, target=target, store=store, journal=journal,
            receipt=receipt, handoff_ref=handoff_ref, producer=producer)
        # The actual Workflow.build initializer must have written its own
        # assignment control. This check never creates it on the test's behalf.
        owner._result_directory(child, create=False)


def test_original_runtime_build_selects_results_source_type(runtime_results_frame, tmp_path, monkeypatch):
    frame = runtime_results_frame
    from gene_annotation_episode.episodic_workflow.root.tests.hpc_planning_allocation_task_behavior import PlanningAllocationTaskBehavior
    monkeypatch.setattr(frame.owner, 'credit_view', lambda context, selection: {'credit': 0.0})
    value = SimpleNamespace(binding=frame.owner, context=frame.child, c={'objective': 'Preserve the actual Results runtime build'})
    adapter = SimpleNamespace(role='results', setup=lambda path: value, module=own_module)
    PlanningAllocationTaskBehavior.test_original_runtime_build_selects_this_binding_task(adapter, tmp_path, monkeypatch)

@pytest.mark.parametrize('reason,wait', [(False, False), (False, True), (True, True)])
def test_results_task_private_instruction_composition_matches_original(frame, tmp_path, monkeypatch, reason, wait):
    case = task_case(frame, tmp_path, monkeypatch)
    prompt = own_module('runtime_prompt')
    monkeypatch.setattr(frame.owner, 'instructions', lambda context: 'Original selected A104 Results goal.')
    workflow = case.task.workflow
    workflow.specialist = lambda source: frame.owner
    workflow.binding_context = lambda source: frame.child
    workflow.is_job_source = lambda source: False
    workflow.permits_common_action = lambda source, action: reason if action == 'reason' else wait if action == 'wait' else False
    workflow.knowledge = SimpleNamespace(instructions='\nOriginal selected source instructions.')
    workflow.launch_instructions = SimpleNamespace(instructions='\nOriginal selected Launch instructions.')
    workflow.native_event_information = object()
    workflow.decision_protocol = 'decision_exchange_v1'
    workflow.services = SimpleNamespace(instructions=prompt.instructions)
    context = {'tool_knowledge': {}, 'launch_instruction_library': {}}
    assert case.task.instructions(context) == prompt.instructions(case.task, context)
