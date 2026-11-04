"""Connected resource adapter checks using actual Store/ports and fixture bytes."""
import asyncio
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.api_resource_credit import ApiSearchOperationalCredit, ResourceCreditDispatch
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.hmmer_resource_adapter import HmmerServiceResourceAdapter
from gene_annotation_episode.hmmer_progress import HmmerProgressProvider
from gene_annotation_episode.public_search_operations import PublicSearchPorts
from gene_annotation_episode.public_search_publication import PublicSearchResultPublisher
from gene_annotation_episode.tools import ToolRegistry
from test_hmmer_api_operations import FixtureClient, result_body, setup, snapshot


RUN = 'api-resource-run'


def configured(path, client=None):
    store, client, ops, original_order = setup(path, client)
    journal = Journal(store, RUN)
    tools = ToolRegistry(store, clients=client)
    ports = PublicSearchPorts(ops.registry, ops, PublicSearchResultPublisher(store, tools, operations=ops))
    adapter = HmmerServiceResourceAdapter(SimpleNamespace(), store, journal, ports=ports)
    scope = {'subject_refs': store.problem()['subject_refs']}
    subject = scope['subject_refs'][0]
    assignment = {'version': 'resource_launch_assignment_v1',
        'job_request': {'provider': 'hmmer', 'subject_ref': subject, 'algorithm': 'phmmer',
            'database': 'swissprot', 'parameters': {}, 'page_size': 2},
        'immutable_input_versions': [{'reference': subject, 'version': None,
            'content_sha256': hashlib.sha256(b'MACDEFGH').hexdigest()}],
        'constraints': {'allowed_kinds': ['api'], 'cpu': None},
        'resource_selection': None, 'software_knowledge_refs': [], 'resource_knowledge_refs': []}
    return SimpleNamespace(store=store, client=client, ops=ops, adapter=adapter,
        journal=journal, scope=scope, assignment=assignment, original_order=original_order)


def context(env, role='launch', assignment=None, episode='episode_launch', save=True):
    assignment = deepcopy(env.assignment if assignment is None else assignment)
    request = {'message': {'scope': env.scope, 'episode_assignment': assignment}}
    value = BindingContext(RUN, episode, role, ((role, 'fixture'),), env.scope, assignment, request)
    if save:
        with env.store.transaction():
            env.journal.save('runtime_episodes', {'episode_id': episode, 'path': json.dumps(plain(value.path)),
                'request': json.dumps(request), 'initial_credit': 0, 'state': 'active'})
    return value


def assigned(env):
    value = deepcopy(env.assignment)
    value['resource_selection'] = env.adapter.information.selection()
    value = env.adapter.prepare_assignment(context(env, episode='episode_parent_prepare'), 'launch_api', value, env.scope, RUN + ':order_child:0')
    return context(env, 'launch_api', value)


async def selected(env, bound, index, tool, arguments=None):
    arguments = {} if arguments is None else arguments
    action = {'kind': 'tool', 'tool': tool, 'arguments': arguments}
    with env.store.transaction():
        env.journal.save('runtime_actions', {'episode_id': bound.episode_id,
            'decision_index': index, 'action': json.dumps(action)})
    result = await env.adapter.execute(bound, tool, arguments, f'{RUN}:{bound.episode_id}:{index}')
    with env.store.transaction():
        env.journal.save('runtime_actions', {'episode_id': bound.episode_id,
            'decision_index': index, 'action': json.dumps(action), 'result': json.dumps(result)})
    return result


def receiver(bound, known=(), initial=()):
    return {'run_id': RUN, 'episode_id': bound.episode_id,
        'known_record_refs': list(known), 'initial_known_record_refs': list(initial)}


async def checked(env):
    bound = assigned(env)
    await selected(env, bound, 0, 'api_search.submit', {'retry_of': None})
    result = await selected(env, bound, 1, 'api_search.check_handoff')
    return bound, result


def results_context(env, handoff, *, first=1, last=2, episode='episode_results'):
    value = {'version': 'resource_results_assignment_v1', 'handoff': handoff,
        'requested_data_selector': {'version': 'public_search_result_selector_v1', 'provider': 'hmmer',
            'first_page': first, 'last_page': last, 'page_size': 2}}
    value = env.adapter.prepare_assignment(context(env, episode='episode_parent_prepare'), 'results', value, env.scope, RUN + ':results_order:0')
    return context(env, 'results', value, episode)


def test_explicit_order_preparation_initial_zero_proof_and_constraints(tmp_path):
    env = configured(tmp_path)
    with env.store:
        parent = context(env)
        credit = ApiSearchOperationalCredit(env.adapter.information, handoff_unit=3, acquired_record_unit=.5)
        assert credit(parent, receiver(parent))['credit'] == 0
        bound = assigned(env)
        order = plain(bound.assignment)['adapter_assignment']
        assert env.ops.inspect(order['job_ref'])['state'] == 'not_submitted'
        assert env.ops.open_order(order['job_ref']) == order and env.client.calls == []
        for constraints in ({'cpu': 2}, {'wall_seconds': 30}, {'invented': 1}, {'allowed_kinds': ['local']}):
            value = plain(parent.assignment); value['constraints'] = constraints
            with pytest.raises(ValueError):
                credit(context(env, assignment=value), receiver(parent))
        assert env.client.calls == []


def test_pending_job_has_original_receivers_saved_proof_and_replay_without_http(tmp_path):
    async def run():
        env = configured(tmp_path)
        with env.store:
            bound, result = await checked(env)
            job = bound.assignment['adapter_assignment']['job_ref']
            handoff = result['execution_handoff']
            assert result['status'] == 'completed' and handoff['execution_handle'] == job
            assert handoff['state'] == 'usable' and result['result']['state'] == 'PENDING'
            assert handoff['monitoring']['target_handle'] == handoff['results']['target_handle'] == job
            assert handoff['monitoring']['contract_ref'] == 'public_search.status.v1'
            assert [item[0] for item in env.client.calls] == ['submit', 'status']
            assert len(result['resource_information_refs']) == 1
            saved = env.adapter.information.read_handoff_source(result['resource_information_refs'][0], scope=env.scope)
            assert saved['status_receipt_ref'] == result['result']['receipt_ref']
            assert await env.adapter.execute(bound, 'api_search.check_handoff', {}, f'{RUN}:{bound.episode_id}:1') == result
            assert env.adapter.execution_handoffs(bound) == [handoff]
            assert env.adapter.resolve(bound, handoff['check_record_refs'][0], 'handoff_receipt')
            assert env.adapter.resolve(bound, job, 'resource_execution')
            assert [item[0] for item in env.client.calls] == ['submit', 'status']
            credit = ApiSearchOperationalCredit(env.adapter.information, handoff_unit=3, acquired_record_unit=.5)
            assert credit(bound, receiver(bound, result['record_refs']))['credit'] == 3
            assert credit(bound, receiver(bound, result['record_refs'], result['record_refs']))['credit'] == 0
    asyncio.run(run())


def test_original_job_repair_keeps_same_order_without_submission(tmp_path):
    env = configured(tmp_path)
    with env.store:
        original = env.original_order
        value = deepcopy(env.assignment)
        value['job_request'] = {'provider': 'hmmer', 'existing_job_ref': original['job_ref']}
        value['resource_selection'] = env.adapter.information.selection()
        actual = env.adapter.prepare_assignment(context(env), 'launch_api', value, env.scope, 'repair_order')
        assert actual['adapter_assignment'] == original
        assert env.client.calls == []


def test_assigned_result_pages_credit_coverage_and_repeat_deduplication(tmp_path):
    async def run():
        env = configured(tmp_path)
        with env.store:
            launch, checked_result = await checked(env)
            bound = results_context(env, checked_result['execution_handoff'])
            assert bound.assignment['adapter_assignment'] == launch.assignment['adapter_assignment']
            assert env.adapter.coverage(bound) is None
            pending = await selected(env, bound, 0, 'api_search.acquire', {'page': 1})
            assert pending['feedback']['code'] == 'result_not_ready'
            assert env.adapter.coverage(bound) is None
            env.client.state = 'SUCCESS'
            await selected(env, launch, 2, 'api_search.check_handoff')
            first = await selected(env, bound, 1, 'api_search.acquire', {'page': 1})
            assert first['status'] == 'completed'
            rows = env.adapter.information.own_result_rows(bound)
            assert [row['record_type'] for row in rows] == ['reference', 'observation']
            credit = ApiSearchOperationalCredit(env.adapter.information, handoff_unit=3, acquired_record_unit=.5)
            assert credit(bound, receiver(bound, first['record_refs']))['credit'] == 1
            assert env.adapter.coverage(bound)['all_requested_pages_acquired'] is False
            repeated = await selected(env, bound, 2, 'api_search.acquire', {'page': 1})
            assert credit(bound, receiver(bound, first['record_refs'] + repeated['record_refs']))['credit'] == 1
            second = await selected(env, bound, 3, 'api_search.acquire', {'page': 2})
            coverage = env.adapter.coverage(bound)
            assert coverage['acquired_pages'] == [1, 2] and coverage['all_requested_pages_acquired'] is True
            assert credit(bound, receiver(bound, first['record_refs'] + second['record_refs']))['credit'] == 2
            assert credit(bound, receiver(bound, first['record_refs'] + second['record_refs'], first['record_refs']))['credit'] == 1
            failed = await selected(env, bound, 4, 'api_search.acquire', {'page': 3})
            assert failed['status'] == 'failed' and failed['feedback']['code'] == 'requested_data_selector_conflict'
            assert env.adapter.coverage(bound) == coverage
            assert [item[0] for item in env.client.calls].count('result') == 2
            assert not env.store.current_annotations()
    asyncio.run(run())


def test_foreign_adapter_is_noop_and_api_absence_does_not_invoke_native_changes(tmp_path):
    env = configured(tmp_path)
    with env.store:
        value = deepcopy(env.assignment)
        value['job_request'] = {'query_ref': value['job_request']['subject_ref'], 'cpu': 2}
        value['resource_selection'] = {'resource_id': 'native', 'kind': 'local',
            'allocation': {'cpu': 2, 'memory_bytes': None, 'scratch_bytes': None, 'wall_seconds': None},
            'capability_binding_ref': 'native_registry'}
        bound = context(env, 'launch_local', value)
        assert env.adapter.catalog(bound) == [] and env.adapter.execution_handoffs(bound) == []
        assert not env.adapter.resolve(bound, 'anything', 'resource_execution')
        assert env.adapter.validate_report(bound, {}, {}) is None
        assert env.adapter.initial_references(bound) == []
        assert env.client.calls == []


def test_no_store_snapshot_can_span_awaited_provider_operation(tmp_path):
    async def run():
        env = configured(tmp_path)
        with env.store:
            bound = assigned(env)
            with env.store.transaction():
                with pytest.raises(ValueError, match='api_operation_requires_committed_store'):
                    await env.adapter.execute(bound, 'api_search.submit', {'retry_of': None}, f'{RUN}:episode_launch:0')
            assert env.client.calls == []
    asyncio.run(run())


class PartialClient(FixtureClient):
    def hmmer_result(self, job_id, **kwargs):
        self.calls.append(('result', job_id, kwargs))
        body = result_body(kwargs['page'])
        body['result']['hits'].append({'index': 19, 'acc': 'INVALID', 'domains': [
            {'alignment_display': {'hmmfrom': 1, 'hmmto': 99, 'm': 8, 'sqfrom': 1, 'sqto': 8, 'l': 8}}]})
        return snapshot(body)


def test_partial_projection_keeps_actual_rows_and_reports_acquisition_coverage(tmp_path):
    async def run():
        env = configured(tmp_path, PartialClient())
        with env.store:
            launch, check = await checked(env)
            env.client.state = 'SUCCESS'; await selected(env, launch, 2, 'api_search.check_handoff')
            bound = results_context(env, check['execution_handoff'])
            outcome = await selected(env, bound, 0, 'api_search.acquire', {'page': 1})
            assert outcome['status'] == 'partial'
            assert outcome['feedback']['code'] == 'partial_projection'
            assert outcome['result']['projection_failures'] == [
                {'hit_ordinal': 1, 'domain_ordinal': None, 'code': 'invalid_native_hit'}]
            rows = env.adapter.information.own_result_rows(bound)
            assert len(rows) == 2 and all(row['hit_ordinal'] == 0 for row in rows)
            assert all(row['record_ref'] in outcome['changed_record_refs'] for row in rows)
            credit = ApiSearchOperationalCredit(env.adapter.information, handoff_unit=3, acquired_record_unit=.5)
            assert credit(bound, receiver(bound, outcome['record_refs']))['credit'] == 1
            coverage = env.adapter.coverage(bound)
            assert coverage['acquired_pages'] == [1] and coverage['projection_failure_count'] == 1
            assert coverage['all_requested_pages_acquired'] is False
    asyncio.run(run())


def test_busy_same_key_submission_returns_failed_delivery_without_new_receipt(tmp_path):
    async def run():
        env = configured(tmp_path)
        with env.store:
            bound = assigned(env); env.client.release.clear()
            task = asyncio.create_task(selected(env, bound, 0, 'api_search.submit', {'retry_of': None}))
            try:
                assert await asyncio.to_thread(env.client.entered.wait, 3)
                busy = await env.adapter.execute(bound, 'api_search.submit', {'retry_of': None}, f'{RUN}:{bound.episode_id}:0')
                assert busy['status'] == 'failed' and busy['feedback']['code'] == 'submission_in_progress'
                assert 'provider_operation_refs' not in busy and busy['record_refs'] == []
                assert env.ops.inspect(bound.assignment['adapter_assignment']['job_ref'])['latest_operation_refs'] == []
            finally:
                env.client.release.set()
                original = await task
            assert original['status'] == 'completed'
            assert [item[0] for item in env.client.calls] == ['submit']
    asyncio.run(run())


def test_busy_status_check_preserves_original_pending_operation_and_recovery(tmp_path):
    async def run():
        env = configured(tmp_path)
        with env.store:
            bound = assigned(env)
            await selected(env, bound, 0, 'api_search.submit', {'retry_of': None})
            env.client.status_release.clear()
            task = asyncio.create_task(selected(env, bound, 1, 'api_search.check_handoff'))
            try:
                assert await asyncio.to_thread(env.client.status_entered.wait, 3)
                busy = await env.adapter.execute(bound, 'api_search.check_handoff', {}, f'{RUN}:{bound.episode_id}:1')
                assert busy['status'] == 'failed' and busy['feedback']['code'] == 'submission_in_progress'
                assert busy['result'] == {'job_ref': bound.assignment['adapter_assignment']['job_ref'],
                    'operation_key': f'{RUN}:{bound.episode_id}:1'}
                assert busy['record_refs'] == [] and 'execution_handoff' not in busy
            finally:
                env.client.status_release.set()
                original = await task
            assert original['status'] == 'completed' and original['execution_handoff']['state'] == 'usable'
            assert env.adapter.execution_handoffs(bound) == [original['execution_handoff']]
            assert [item[0] for item in env.client.calls] == ['submit', 'status']
    asyncio.run(run())


@pytest.mark.parametrize('operand_kind', ['rooted_feature', 'rootless_reference'])
def test_material_operand_receivers_share_original_scope_and_sequence_port(tmp_path, operand_kind):
    async def run():
        env = configured(tmp_path)
        with env.store:
            target = env.scope['subject_refs'][0]
            with env.store.transaction():
                if operand_kind == 'rooted_feature':
                    operand = env.store.put('feature', {'subject_ref': target, 'kind': 'sequence_region',
                        'segments': [{'start': 0, 'end': 8}], 'strand': '+', 'context_refs': []},
                        origin='reasoning', scope=env.scope)
                    assert 'sequence_ref' not in operand
                else:
                    artifact = env.store.artifact('Synthetic external sequence: MACDEFGH', 'text/plain')
                    source = env.store.put('source', {'provider': 'synthetic_fixture', 'accession': 'fixture_external',
                        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
                        'version': None, 'retrieved_at': None}, origin='external')
                    operand = env.store.put('reference', {'reference_type': 'protein', 'source_ref': source['id'],
                        'accession': 'fixture_external_sequence', 'label': 'Synthetic external sequence',
                        'sequence_ref': env.store.artifact('MACDEFGH', 'text/plain'), 'molecule': 'protein',
                        'length': 8, 'term_refs': [], 'context_refs': []}, origin='external')
                    assert env.store.roots(operand['id']) == []
            env.assignment['job_request']['subject_ref'] = operand['id']
            env.assignment['immutable_input_versions'] = [{'reference': operand['id'], 'version': None,
                'content_sha256': hashlib.sha256(b'MACDEFGH').hexdigest() if operand_kind == 'rootless_reference' else None}]
            launch, checked_result = await checked(env)
            order = plain(launch.assignment)['adapter_assignment']; job = order['job_ref']
            original_scope = env.store.validate_scope(env.scope)
            assert env.ops.open_scope(job)['scope'] == original_scope
            assert env.adapter.ports.sequence_symbols(operand['id'], scope=env.scope) == 'MACDEFGH'
            assert env.store.get_artifact(order['query_fasta_ref']) == f'>{operand["id"]}\nMACDEFGH'.encode()
            progress = HmmerProgressProvider(env.store, run_id=RUN, ports=env.adapter.ports)
            assert progress.scope(job) == original_scope
            observed = await progress.observe(job, ['execution_status', 'result_available'], env.scope,
                operation_key=f'{RUN}:episode_{operand_kind}_monitor:0')
            assert observed['execution_status']['handle'] == job and observed['result_available'] is False
            env.client.state = 'SUCCESS'
            await selected(env, launch, 2, 'api_search.check_handoff')
            results = results_context(env, checked_result['execution_handoff'])
            acquired = await selected(env, results, 0, 'api_search.acquire', {'page': 1})
            assert acquired['status'] == 'completed'
            rows = env.adapter.information.own_result_rows(results)
            assert len(rows) == 2 and all(row['subject_ref'] == operand['id'] for row in rows)
            assert env.store.problem()['subject_refs'] == [target]
            assert [item[0] for item in env.client.calls] == ['submit', 'status', 'status', 'status', 'result']
    asyncio.run(run())
