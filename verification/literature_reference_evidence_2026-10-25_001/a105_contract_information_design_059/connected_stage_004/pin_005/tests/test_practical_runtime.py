"""Real local execution under scripted shared-loop practical decisions.

The provider choices are fixtures. Commands, files, validation, receipts, yield
control and saved-action replay use the actual implementation. No model,
scientific investigation, remote resource or HPC job runs in these checks.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import uuid

import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.episode_reports import report_sources
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_execution_records import assess_validations, digest
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.practical_resource_episodes import PracticalResourceEpisodes
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def selected(name, arguments=None):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': arguments or {}},
            'report_update': {}}


class Choices:
    """Explicit test choices; completed-action credit never controls this fixture."""
    def __init__(self, actions=(), *, collect_after=False):
        self.actions = iter(actions)
        self.collect_after = collect_after
        self.contexts = []
        self.released = []

    async def complete(self, episode_id, role, instructions, context, schema):
        assert role == 'REASONING'
        assert 'practical execution assignment' in instructions
        self.contexts.append(deepcopy(context))
        try:
            return deepcopy(next(self.actions))
        except StopIteration:
            if not self.collect_after:
                raise AssertionError('Episode requested an unexpected further decision')
            # Fixture-controlled observation spacing lets a tiny real process
            # exit. It is not a production polling cadence or episode action cap.
            await asyncio.sleep(.03)
            return selected('practical.job.collect')

    async def release(self, episode_id):
        self.released.append(episode_id)


def make_assignment(workspace, *, reuse=False, held=False, endpoint='completed_job_outputs'):
    workspace.mkdir(parents=True, exist_ok=True)
    work = workspace / 'work'
    script = workspace / 'prepared.py'
    result = work / 'result.json'
    nonce = uuid.uuid4().hex
    body = ('import json,os,time\nfrom pathlib import Path\n'
        + ('while not Path("release").exists(): time.sleep(.01)\n' if held else '')
        + 'with Path("invocations").open("a") as f: f.write("once\\n")\n'
        + 'Path("result.json").write_text(json.dumps({"cwd":os.getcwd(),'
          '"nonce":os.environ["RUN_NONCE"],"value":os.environ["PREP_VALUE"]}))\n')
    if reuse:
        work.mkdir(exist_ok=True)
        script.write_text(body)
    requirements = [
        {'key': 'working_directory_exists', 'credit': 1,
            'predicate': {'kind': 'path_exists', 'path': str(work), 'object_type': 'directory'}},
        {'key': 'working_directory_selected', 'credit': 1,
            'predicate': {'kind': 'context_cwd', 'path': str(work)}},
        {'key': 'preparation_environment', 'credit': .5,
            'predicate': {'kind': 'context_environment', 'name': 'PREP_VALUE', 'value': 'prepared'}},
        {'key': 'prepared_program', 'credit': 2,
            'predicate': {'kind': 'file_sha256', 'path': str(script),
                          'sha256': hashlib.sha256(body.encode()).hexdigest()}},
        {'key': 'endpoint', 'credit': 4, 'predicate': (
            {'kind': 'requested_job_handoff'} if endpoint == 'usable_handoff' else
            {'kind': 'requested_job_outputs', 'output_paths': [str(result)]})}]
    assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'fixture-' + nonce,
        'resource_kind': 'local', 'workspace': str(workspace), 'endpoint': endpoint,
        'requested_job': {'argv': [sys.executable, str(script)],
            'environment': {'RUN_NONCE': nonce, 'PREP_VALUE': 'job-specific'}},
        'progress_requirements': requirements, 'completion_keys': ['endpoint'],
        'initial_context': {'revision': 0, 'cwd': str(work if reuse else workspace),
            'environment': {'PREP_VALUE': 'prepared'} if reuse else {}},
        'inventory_snapshot': {}, 'constraints': {}}
    return SimpleNamespace(assignment=assignment, workspace=workspace, work=work,
        script=script, body=body, result=result, nonce=nonce)


def host(store, directory, assignment, provider, *, run_id='practical-runtime-fixture',
         key='root', scope=None):
    configuration = {'kind': 'local', 'workspace': assignment['workspace'],
        'policy': {'memory_bytes': 128 * 1024**2, 'scratch_bytes': 8 * 1024**2,
                   'wall_seconds': None}}
    descriptor = PracticalResourceEpisodes(None, directory=directory,
        resources={'local': configuration}).as_record()
    def controller(path, initial):
        # The production estimator cannot fit this short history. Only an
        # authoritative endpoint makes its future estimate available and zero.
        return YieldController(str(path), initial, 0, YieldParameters(100, 50))
    workflow = Workflow(store, ToolRegistry(store), provider, directory, run_id,
        controller_factory=controller, project_credit=lambda *_: 0,
        episode_binding_descriptors=[descriptor],
        role_credit_bindings={'launch_local': {'definition': {'version': 'explicit-test-units'},
            'project': lambda *_: 0}}, root_role='launch_local',
        execution_binding={'factory_module': 'fixture', 'factory_name': 'unused',
            'arguments': {}, 'implementation_sha256': 'a' * 64, 'settings_sha256': 'b' * 64})
    scope = store.validate_scope(scope or {'subject_refs': store.problem()['subject_refs']})
    episode = workflow.build('launch_local', key, 'Run the exact practical assignment', scope,
        episode_assignment=assignment)
    return SimpleNamespace(workflow=workflow, episode=episode,
        binding=workflow.specialist(episode.source),
        context=workflow.binding_context(episode.source))


def observations(bound):
    return [json.loads(row[0]) for row in bound.workflow.store.db.execute(
        'SELECT observation FROM runtime_observations WHERE run_id=? AND episode_id=? '
        'ORDER BY unit_index', (bound.workflow.run_id, bound.episode.source.episode_id))]


def run(bound):
    async def perform():
        record = await bound.episode.run_async(bound.workflow.context)
        await bound.episode.build_result(record)
        return record
    return asyncio.run(perform())


def forbid(*args, **kwargs):
    raise AssertionError('Saved completion replay must not execute, inspect resources or call a provider')


def test_actual_setup_commands_endpoint_and_saved_replay(tmp_path, monkeypatch):
    spec = make_assignment(tmp_path / 'project')
    command = [sys.executable, '-c',
        'import os\nfrom pathlib import Path\n'
        'assert os.getcwd()=='+repr(str(spec.work))+'\n'
        'assert os.environ["PREP_VALUE"]=="prepared"\n'
        'with Path("failed-attempts").open("a") as f: f.write("once\\n")\n'
        'raise SystemExit(7)']
    actions = [selected('practical.directory.create', {'path': str(spec.work)}),
        selected('practical.context.set', {'cwd': str(spec.work),
            'environment': {'PREP_VALUE': 'prepared'}}),
        selected('practical.file.write', {'path': str(spec.script), 'text': spec.body}),
        selected('practical.inspect'),
        selected('practical.command.run', {'argv': command, 'environment': {}}),
        # A malformed request is never executed and creates no receipt/turn.
        selected('practical.file.write', {'path': str(spec.workspace / 'must-not-exist')}),
        selected('practical.job.start')]
    provider = Choices(actions, collect_after=True)
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        bound = host(store, tmp_path / 'run', spec.assignment, provider)
        record = run(bound)
        assert record.ended_by == 'yield_stop'
        assert spec.script.read_text() == spec.body
        assert (spec.work / 'failed-attempts').read_text() == 'once\n'
        assert (spec.work / 'invocations').read_text() == 'once\n'
        assert json.loads(spec.result.read_text()) == {'cwd': str(spec.work),
            'nonce': spec.nonce, 'value': 'job-specific'}
        assert not (spec.workspace / 'must-not-exist').exists()
        rows = observations(bound)
        state = bound.binding.state(bound.context)
        receipts = state.receipts()
        assert record.units_consumed == len(rows) == len(receipts)
        assert len(provider.contexts) == len(receipts) + 1
        assert [row['step']['marginal_credit'] for row in rows[:5]] == [1, 1.5, 2, 0, 0]
        assert receipts[4]['outcome']['facts']['command']['returncode'] == 7
        assert rows[-1]['step']['marginal_credit'] == 4
        assert record.controller_state.estimate.expected_next_gain == NumericBand.exact(0)
        assert rows[-1]['step']['stop'] is True
        assert rows[-1]['credit']['practical_completion']['receipt_sha256'] == state.completion_proof()['receipt_sha256']
        for receipt in receipts:
            # Sparse assessments preserve earlier knowledge when this action
            # did not observe that fact. Every supplied fact still has its
            # exact assessment, with the original recorded observation time.
            expected = assess_validations(spec.assignment, receipt['outcome'], receipt['context_after'],
                tool_name=receipt['tool_name'], checked_at=receipt['finished_at'])
            actual = [{**item, 'checked_at': receipt['finished_at']}
                      for item in receipt['validations']]
            assert actual == expected
        assert all(receipt['operation_key'].endswith(':' + str(row['decision_index']))
                   for row, receipt in zip(rows, receipts))
        original_rows, original_receipts = deepcopy(rows), deepcopy(receipts)
        with monkeypatch.context() as patched:
            patched.setattr(LocalPracticalOperations, 'initial_outcome', forbid)
            patched.setattr(LocalPracticalOperations, 'execute', forbid)
            patched.setattr('gene_annotation_episode.practical_execution_operations.path_facts', forbid)
            restored_provider = Choices()
            patched.setattr(restored_provider, 'complete', forbid)
            replay = host(store, tmp_path / 'run', spec.assignment, restored_provider)
            replay_record = run(replay)
        assert replay_record.as_record() == record.as_record()
        assert observations(replay) == original_rows
        assert replay.binding.state(replay.context).receipts() == original_receipts
        assert not restored_provider.contexts
        assert (spec.work / 'invocations').read_text() == 'once\n'
        assert (spec.work / 'failed-attempts').read_text() == 'once\n'


def test_prepared_components_are_inherited_without_new_setup_credit(tmp_path):
    spec = make_assignment(tmp_path / 'project', reuse=True)
    provider = Choices([selected('practical.inspect'), selected('practical.job.start')], collect_after=True)
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        bound = host(store, tmp_path / 'run', spec.assignment, provider)
        record = run(bound)
        rows = observations(bound)
        assert record.controller_state.initial_credit == 4.5
        assert rows[0]['step']['marginal_credit'] == 0
        assert provider.contexts[0]['current_credit'] == 4.5
        assert provider.contexts[0]['practical_assignment'] == spec.assignment
        assert all(receipt['tool_name'] not in {'practical.file.write', 'practical.directory.create',
            'practical.context.set'} for receipt in bound.binding.state(bound.context).receipts())
        assert record.controller_state.current_credit == 8.5
        assert rows[-1]['step']['marginal_credit'] == 4
        assert record.controller_state.estimate.expected_next_gain == NumericBand.exact(0)
        assert json.loads(spec.result.read_text())['nonce'] == spec.nonce


def test_usable_handoff_closes_while_requested_job_continues(tmp_path):
    spec = make_assignment(tmp_path / 'project', reuse=True, held=True, endpoint='usable_handoff')
    provider = Choices([selected('practical.job.start')])
    handle = None
    try:
        with Store(tmp_path / 'state') as store:
            store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
            bound = host(store, tmp_path / 'run', spec.assignment, provider)
            record = run(bound)
            state = bound.binding.state(bound.context)
            receipt, = state.receipts()
            handle = native.NativeJobHandle(Path(receipt['outcome']['facts']['requested_job']['execution_id']))
            assert record.units_consumed == len(provider.contexts) == 1
            assert record.controller_state.estimate.expected_next_gain == NumericBand.exact(0)
            assert state.completion_proof()['endpoint'] == 'usable_handoff'
            assert not spec.result.exists()
            assert not native.status(handle)['terminal']
            assert record.unit_records[0].controller_step.marginal_credit == 4
    finally:
        # Release only this test's fixture barrier. Closing the episode itself
        # never cancels the real detached requested job.
        (spec.work / 'release').touch()
        if handle is not None:
            assert native.wait_job(handle).returncode == 0
    assert json.loads(spec.result.read_text())['nonce'] == spec.nonce


def test_fresh_episode_collects_original_handoff_without_changing_closed_history(tmp_path):
    spec = make_assignment(tmp_path / 'project', reuse=True, held=True, endpoint='usable_handoff')
    handle = None
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
        directory = tmp_path / 'run'
        origin = host(store, directory, spec.assignment, Choices([selected('practical.job.start')]))
        try:
            original_record = run(origin)
            original_state = origin.binding.state(origin.context)
            original_receipts = original_state.receipts()
            original_observations = observations(origin)
            original_closed_history = deepcopy(original_record.as_record())
            original_action = origin.workflow.journal.row('runtime_actions',
                origin.episode.source.episode_id, 0)
            source_ref, = json.loads(original_action['result'])['record_refs']
            information = PracticalReceiptInformation(store, origin.workflow.run_id)
            original_source = information.read(source_ref, origin.episode.source.scope)
            execution_id = original_receipts[0]['outcome']['facts']['requested_job']['execution_id']
            handle = native.NativeJobHandle(Path(execution_id))
            assert original_record.units_consumed == 1
            assert original_record.unit_records[0].controller_step.marginal_credit == 4
            assert original_record.controller_state.estimate.expected_next_gain == NumericBand.exact(0)
            assert not spec.result.exists()
            # The launch did not need a result-file predicate to return a
            # useful execution handle. The later receiver declares its need.
            assert not any(item['predicate']['kind'] == 'requested_job_outputs'
                           for item in spec.assignment['progress_requirements'])
        finally:
            (spec.work / 'release').touch()
            if handle is not None:
                assert native.wait_job(handle).returncode == 0

        receiving = deepcopy(spec.assignment)
        receiving['assignment_id'] += '-result-receiver'
        receiving['endpoint'] = 'completed_job_outputs'
        receiving['progress_requirements'][-1]['predicate'] = {
            'kind': 'requested_job_outputs', 'output_paths': [str(spec.result)]}
        provider = Choices([selected('practical.job.collect', {'receipt_ref': source_ref})])
        receiver = host(store, directory, receiving, provider, key='result-receiver')
        received_record = run(receiver)
        state = receiver.binding.state(receiver.context)
        received_receipt, = state.receipts()
        assert received_record.units_consumed == len(provider.contexts) == 1
        assert received_record.unit_records[0].controller_step.marginal_credit == 4
        assert received_record.controller_state.estimate.expected_next_gain == NumericBand.exact(0)
        assert state.verify_completion(state.completion_proof()) is True
        assert state.completion_proof()['assignment_sha256'] == digest(receiving)
        actual_job = received_receipt['outcome']['facts']['requested_job']
        assert actual_job['execution_id'] == execution_id
        assert actual_job['requested_job_sha256'] == digest(spec.assignment['requested_job'])
        assert actual_job['status'] == 'completed' and actual_job['returncode'] == 0
        assert str(spec.result) in actual_job['output_paths']
        assert received_receipt['arguments'] == {'receipt_ref': source_ref}
        receiver_ref, = json.loads(receiver.workflow.journal.row('runtime_actions',
            receiver.episode.source.episode_id, 0)['result'])['record_refs']
        assert information.read(receiver_ref, origin.episode.source.scope)['receipt'] == received_receipt
        assert information.read(source_ref, receiver.episode.source.scope) == original_source

        class RejectedBeforeWork(Exception):
            pass
        class RejectingChoices(Choices):
            async def complete(self, episode_id, role, instructions, context, schema):
                self.contexts.append(deepcopy(context))
                if len(self.contexts) == 1:
                    return selected('practical.job.collect', {'receipt_ref': source_ref})
                raise RejectedBeforeWork(context['feedback'])
        for name, expected_code, altered, scope in (
                ('wrong-job', 'practical_received_execution_assignment_mismatch', True, None),
                ('wrong-scope', 'practical_receipt_outside_receiving_scope', False,
                 {'subject_refs': [target], 'segments': [
                     {'target_ref': target, 'start': 0, 'end': 5, 'unit': 'aa'}]})):
            invalid_assignment = deepcopy(receiving)
            invalid_assignment['assignment_id'] += '-' + name
            if altered:
                invalid_assignment['requested_job']['environment']['RUN_NONCE'] = 'different-job'
            rejected = host(store, directory, invalid_assignment, RejectingChoices(), key=name, scope=scope)
            with pytest.raises(RejectedBeforeWork) as error:
                run(rejected)
            assert error.value.args[0]['code'] == expected_code
            rejected_state = rejected.binding.state(rejected.context)
            assert rejected_state.receipts() == []
            assert list((rejected_state.directory / 'intents').glob('*.json')) == []
            assert observations(rejected) == []

        assert original_state.receipts() == original_receipts
        assert observations(origin) == original_observations
        assert original_record.as_record() == original_closed_history
        assert (spec.work / 'invocations').read_text() == 'once\n'
        assert len(list((spec.workspace / '.episode-operations').rglob('native.json'))) == 1
        assert json.loads(spec.result.read_text())['nonce'] == spec.nonce


def test_parent_receives_only_requested_verified_completion_and_receipts(tmp_path):
    spec = make_assignment(tmp_path / 'project', reuse=True)
    form = {'type': 'object', 'properties': {
        'completed': {'type': 'boolean', 'x-source': 'practical_completed'},
        'receipts': {'type': 'array', 'items': {'type': 'string', 'format': 'identifier',
            'x-reference-namespace': 'practical_receipt'}, 'x-source': 'practical_receipt_digests'},
        'receipt_sources': {'type': 'array', 'uniqueItems': True,
            'items': {'type': 'string', 'format': 'reference',
                'x-reference-namespace': 'practical_receipt'}, 'x-source': 'practical_receipt_refs'},
        'yield': report_sources()['episode_yield']['report_schema']},
        'required': ['completed', 'receipts', 'receipt_sources', 'yield'], 'additionalProperties': False}
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}
        class ParentAndChildChoices(Choices):
            def __init__(self):
                super().__init__([selected('practical.job.start')], collect_after=True)
                self.parent_contexts = []

            async def complete(self, episode_id, role, instructions, context, schema):
                if 'practical_assignment' in context:
                    return await super().complete(episode_id, role, instructions, context, schema)
                self.parent_contexts.append(deepcopy(context))
                assert len(self.parent_contexts) == 1
                return {'selection': {'kind': 'episode_child', 'role': 'launch_local',
                    'goal': 'Establish this exact requested practical execution',
                    'scope': scope, 'purpose': 'Receive verified endpoint and its original receipts',
                    'assignment': spec.assignment, 'schema_json': json.dumps(form),
                    'initial_report_json': '{}'}, 'report_update': {}}

        provider = ParentAndChildChoices()
        configuration = {'kind': 'local', 'workspace': str(spec.workspace),
            'policy': {'memory_bytes': 128 * 1024**2, 'scratch_bytes': 8 * 1024**2,
                       'wall_seconds': None}}
        directory = tmp_path / 'run'
        descriptor = PracticalResourceEpisodes(None, directory=directory,
            resources={'local': configuration}).as_record()
        def parent_estimate(history, parameters, contexts):
            # This scientific fixture examines one real received child report.
            # It needs no additional root tool call or manufactured zero action.
            return YieldEstimate(len(history), NumericBand.exact(0 if history else 1),
                parameters, {'fixture': 'explicit_parent_continuation'})
        def controller(path, initial):
            return YieldController(str(path), initial, 0, YieldParameters(100, 50),
                estimate_with_context=parent_estimate if len(path) == 1 else None)
        workflow = Workflow(store, ToolRegistry(store), provider, directory, 'typed-practical-fixture',
            controller_factory=controller, project_credit=lambda *_: 0,
            episode_binding_descriptors=[descriptor], annotation_child_roles=('launch_local',),
            role_credit_bindings={'launch_local': {'definition': {'version': 'explicit-test-units'},
                'project': lambda *_: 0}})
        episode = workflow.build('annotation', 'root', 'Obtain the requested execution result', scope)
        bound = SimpleNamespace(workflow=workflow, episode=episode)
        record = run(bound)
        assert record.units_consumed == 1
        assert record.controller_state.history == (0,)
        assert len(provider.parent_contexts) == 1
        child_record = record.unit_records[0].child
        assert child_record is not None
        child_context = workflow.binding_context(SimpleNamespace(path=child_record.path,
            episode_id=child_record.episode_id, scope=scope, request=child_record.request))
        binding = workflow.episode_bindings.for_role('launch_local')
        state = binding.state(child_context)
        child_receipts = state.receipts()
        returned = record.unit_records[0].episode_update.report.as_record()
        assert returned['completed'] is True
        assert returned['receipts']
        assert returned['receipt_sources']
        assert returned['yield']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert set(returned) == set(form['properties'])
        assert returned['receipts'] == [digest(receipt) for receipt in child_receipts]
        source_refs = [json.loads(row[0])['record_refs'][0] for row in store.db.execute(
            'SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index',
            (workflow.run_id, child_record.episode_id))]
        assert returned['receipt_sources'] == source_refs
        information = PracticalReceiptInformation(store, workflow.run_id)
        for reference, original_receipt, receipt_digest in zip(
                returned['receipt_sources'], child_receipts, returned['receipts']):
            # Read from the receiving parent's scope through saved Store
            # artifacts; no native status check or report composer is needed.
            received_body = information.read(reference, episode.source.scope)
            assert received_body['episode_id'] == child_record.episode_id
            assert received_body['receipt'] == original_receipt
            assert digest(received_body['receipt']) == receipt_digest
            assert received_body['receipt']['outcome'] == original_receipt['outcome']
            assert received_body['receipt']['validations'] == original_receipt['validations']
        assert returned['yield']['completed_actions'] == len(child_receipts)
        assert returned['yield']['stop_requested'] is True
        assert returned['yield']['continuation_cost'] == 0
        assert json.loads(spec.result.read_text())['nonce'] == spec.nonce
        own_observations = list(store.db.execute('SELECT episode_id FROM runtime_observations'))
        assert len(own_observations) == len(child_receipts) + 1
        assert len(provider.contexts) == len(child_receipts)
        # A correctly shaped forged digest is unavailable at this original
        # child's boundary; the parent cannot accept model-invented receipts.
        forged = {**returned, 'receipts': ['0' * 64]}
        with pytest.raises(ValueError):
            child_record.request.report_contract.admit(forged,
                audit_identifiers=(child_record.episode_id, child_record.goal.goal_id))
