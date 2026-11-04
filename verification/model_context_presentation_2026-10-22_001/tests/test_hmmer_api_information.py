"""Original-action proof qualification and separate operational information."""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.api_resource_credit import ApiSearchOperationalCredit, ResourceCreditDispatch
from gene_annotation_episode.communication import plain, validate_closed_schema, validate_form
from gene_annotation_episode.hmmer_resource_information import ApiSearchInformationReader, proof_receipt_ref
from test_hmmer_api_adapter import (RUN, assigned, checked, configured, context,
    receiver, results_context, selected)


def test_reader_explicit_identity_and_unselected_dispatch_before_any_proof(tmp_path):
    env = configured(tmp_path)
    with env.store:
        reader = ApiSearchInformationReader(env.store, run_id=RUN, ports=env.adapter.ports)
        api = ApiSearchOperationalCredit(reader, handoff_unit=7.25, acquired_record_unit=2)
        class Native:
            def __init__(self): self.calls = []
            def as_record(self): return {'version': 'fixture_native_projection'}
            def __call__(self, bound, selection):
                self.calls.append((bound, selection)); return {'native': 'unchanged'}
        native = Native()
        dispatch = ResourceCreditDispatch(native_projector=native, api_projector=api,
            native_resource_id='native', api_resource_id=env.adapter.resource_id)
        parent = context(env)
        assert dispatch(parent, receiver(parent))['credit'] == 0
        assert native.calls == [] and 'registry_ref' not in dispatch.as_record()
        value = plain(parent.assignment); value['job_request'] = {'query_ref': env.scope['subject_refs'][0], 'cpu': 2}
        assert dispatch(context(env, assignment=value), receiver(parent)) == {'native': 'unchanged'}
        assert len(native.calls) == 1 and env.client.calls == []
        with pytest.raises(ValueError, match='resource_credit_receiver_identity_mismatch'):
            api(parent, {**receiver(parent), 'run_id': 'other_run'})
        value = plain(parent.assignment); value['job_request']['provider'] = 'blast'
        with pytest.raises(ValueError, match='unsupported_resource_credit_job_request'):
            dispatch(context(env, assignment=value), receiver(parent))


def test_checked_receipt_is_separate_deterministic_identity_and_source_is_custodied(tmp_path):
    async def run():
        env = configured(tmp_path)
        with env.store:
            bound, outcome = await checked(env)
            reference = outcome['resource_information_refs'][0]
            source = env.store.get(reference)
            body = json.loads(env.store.get_artifact(source['artifact_ref']))
            assert reference not in body['outcome']['record_refs']
            expected = proof_receipt_ref(RUN, bound.episode_id, f'{RUN}:{bound.episode_id}:1', body['status_receipt_ref'])
            assert body['execution_handoff']['check_record_refs'] == [expected]
            assert reference != expected and body['job_ref'].startswith('provider_job_')
            assert env.adapter.information.references_for_handoff(body['execution_handoff'], scope=env.scope) == [reference]
            changed = deepcopy(body['execution_handoff']); changed['results']['target_handle'] = 'foreign_job'
            with pytest.raises(ValueError, match='invalid_resource_handoff'):
                env.adapter.information.validate_handoff(changed, scope=env.scope)
            with env.store.transaction():
                corrupt = deepcopy(outcome); corrupt['result']['state'] = 'SUCCESS'
                env.journal.save('runtime_actions', {'episode_id': bound.episode_id,
                    'decision_index': 1, 'action': json.dumps({'kind': 'tool', 'tool': 'api_search.check_handoff', 'arguments': {}}),
                    'result': json.dumps(corrupt)})
            with pytest.raises(ValueError, match='api_information_saved_outcome_conflict'):
                env.adapter.information.read_handoff_source(reference, scope=env.scope)
    asyncio.run(run())


def test_same_physical_handoff_rechecks_and_inherited_proof_do_not_add_credit(tmp_path):
    async def run():
        env = configured(tmp_path)
        with env.store:
            bound, first = await checked(env)
            second = await selected(env, bound, 2, 'api_search.check_handoff')
            credit = ApiSearchOperationalCredit(env.adapter.information, handoff_unit=4, acquired_record_unit=.25)
            refs = first['record_refs'] + second['record_refs']
            assert credit(bound, receiver(bound, refs))['new_handoff_count'] == 1
            assert credit(bound, receiver(bound, refs, first['record_refs']))['credit'] == 0
            parent = context(env, episode='episode_parent')
            assert credit(parent, receiver(parent, second['record_refs']))['credit'] == 4
            changed = plain(parent.assignment); changed['job_request']['database'] = 'different_database'
            with pytest.raises(ValueError, match='api_information_assignment_conflict'):
                credit(context(env, assignment=changed, episode='episode_other'), receiver(
                    context(env, assignment=changed, episode='episode_other'), second['record_refs']))
    asyncio.run(run())


@pytest.mark.parametrize('mutation', ['input_digest', 'version', 'cpu', 'unknown_parameter', 'page_size', 'algorithm'])
def test_initial_qualification_enforces_actual_inputs_without_order_or_http(tmp_path, mutation):
    env = configured(tmp_path)
    with env.store:
        value = deepcopy(env.assignment)
        if mutation == 'input_digest': value['immutable_input_versions'][0]['content_sha256'] = '0' * 64
        elif mutation == 'version': value['immutable_input_versions'][0]['version'] = 'invented_revision'
        elif mutation == 'cpu': value['constraints']['cpu'] = 1
        elif mutation == 'unknown_parameter': value['job_request']['parameters'] = {'private_option': 1}
        elif mutation == 'page_size': value['job_request']['page_size'] = True
        else: value['job_request']['algorithm'] = 'jackhmmer'
        with pytest.raises(ValueError): env.adapter.information.qualify_launch(context(env, assignment=value))
        assert env.client.calls == []


def test_acquisition_rows_require_own_selected_action_and_immutable_publication(tmp_path):
    async def run():
        env = configured(tmp_path)
        with env.store:
            launch, handoff = await checked(env)
            bound = results_context(env, handoff['execution_handoff'])
            env.client.state = 'SUCCESS'; await selected(env, launch, 2, 'api_search.check_handoff')
            acquired = await selected(env, bound, 0, 'api_search.acquire', {'page': 1})
            other = results_context(env, handoff['execution_handoff'], episode='episode_other_results')
            credit = ApiSearchOperationalCredit(env.adapter.information, handoff_unit=3, acquired_record_unit=.5)
            assert credit(other, receiver(other, acquired['record_refs']))['credit'] == 0
            assert len(env.adapter.information.own_result_rows(bound)) == 2
            with env.store.transaction():
                forged = deepcopy(acquired); forged['result']['publication_rows'][0]['hit_ordinal'] = 8
                env.journal.save('runtime_actions', {'episode_id': bound.episode_id,
                    'decision_index': 0, 'action': json.dumps({'kind': 'tool', 'tool': 'api_search.acquire', 'arguments': {'page': 1}}),
                    'result': json.dumps(forged)})
            with pytest.raises(ValueError, match='api_information_publication_conflict'):
                env.adapter.information.own_result_rows(bound)
    asyncio.run(run())


def test_saved_failure_fact_clears_after_actual_successful_check(tmp_path):
    async def run():
        env = configured(tmp_path)
        with env.store:
            launch, handoff = await checked(env)
            bound = results_context(env, handoff['execution_handoff'])
            await selected(env, bound, 0, 'api_search.acquire', {'page': 1})
            assert env.adapter.facts(bound, {})['api_failure']['code'] == 'result_not_ready'
            env.client.state = 'SUCCESS'; await selected(env, launch, 2, 'api_search.check_handoff')
            await selected(env, bound, 1, 'api_search.acquire', {'page': 1})
            facts = env.adapter.facts(bound, {})
            assert facts['api_failure'] is None and facts['api_result_coverage']['acquired_pages'] == [1]
    asyncio.run(run())


def test_api_fact_fields_are_closed_parent_types_and_reject_changed_recorded_facts(tmp_path):
    env = configured(tmp_path)
    with env.store:
        bound = assigned(env)
        fields = {name: item['report_schema'] for name, item in env.adapter.fact_sources('launch_api').items()}
        schema = {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}
        validate_closed_schema(schema)
        form = {name: None for name in fields}
        assert validate_form(form, schema) == form
        env.adapter.validate_report(bound, form, schema)
        changed = deepcopy(form)
        changed['api_failure'] = {'code': 'invented'}
        with pytest.raises(ValueError, match='API recorded facts differ'):
            env.adapter.validate_report(bound, changed, schema)


def test_assigned_and_repair_scope_is_original_while_receiving_parent_may_contain_it(tmp_path):
    async def run():
        env = configured(tmp_path)
        with env.store:
            broad = deepcopy(env.scope); target = broad['subject_refs'][0]
            env.scope = {'subject_refs': [target], 'segments': [
                {'target_ref': target, 'start': 0, 'end': 4, 'unit': 'aa'}]}
            with env.store.transaction():
                feature = env.store.put('feature', {'subject_ref': target, 'kind': 'sequence_region',
                    'segments': [{'start': 0, 'end': 4}], 'strand': '+', 'context_refs': []},
                    origin='reasoning', scope=env.scope)
            env.assignment['job_request']['subject_ref'] = feature['id']
            env.assignment['immutable_input_versions'] = [{'reference': feature['id'], 'version': None, 'content_sha256': None}]
            launch, proof = await checked(env)
            job = launch.assignment['adapter_assignment']['job_ref']
            original_scope = env.ops.open_scope(job)
            before = list(env.client.calls)
            # A parent receives a narrower original proof without relabelling
            # the job's assigning scope or changing the submitted material.
            broad_env = SimpleNamespace(**{**vars(env), 'scope': broad})
            parent = context(broad_env, episode='episode_parent')
            credit = ApiSearchOperationalCredit(env.adapter.information, handoff_unit=3, acquired_record_unit=.5)
            assert credit(parent, receiver(parent, proof['record_refs']))['credit'] == 3
            broadened = type(launch)(launch.run_id, launch.episode_id, launch.role, launch.path,
                broad, launch.assignment, launch.request)
            with pytest.raises(ValueError, match='api_information_order_scope_conflict'):
                env.adapter.information.qualify_launch(broadened)
            repair = plain(launch.assignment)
            repair['job_request'] = {'provider': 'hmmer', 'existing_job_ref': job}
            repair.pop('adapter_assignment')
            repair_context = type(parent)(parent.run_id, 'episode_repair', 'launch', (('launch', 'fixture'),),
                broad, {**repair, 'resource_selection': None}, {})
            with pytest.raises(ValueError, match='api_information_order_scope_conflict'):
                env.adapter.information.qualify_launch(repair_context)
            results = results_context(env, proof['execution_handoff'])
            broadened_results = type(results)(results.run_id, results.episode_id, results.role, results.path,
                broad, results.assignment, results.request)
            with pytest.raises(ValueError, match='api_information_order_scope_conflict'):
                env.adapter.information.qualify_results(broadened_results)
            assert env.ops.open_scope(job) == original_scope and env.client.calls == before
            action = {'kind': 'tool', 'tool': 'resource.check_handoff',
                'arguments': {'handoff': proof['execution_handoff']}}
            key = f'{RUN}:{parent.episode_id}:0'
            with env.store.transaction():
                env.journal.save('runtime_actions', {'episode_id': parent.episode_id,
                    'decision_index': 0, 'action': json.dumps(action)})
            rechecked = await env.adapter.check_handoff(parent, proof['execution_handoff'], key)
            with env.store.transaction():
                env.journal.save('runtime_actions', {'episode_id': parent.episode_id,
                    'decision_index': 0, 'action': json.dumps(action), 'result': json.dumps(rechecked)})
            after_parent_check = results_context(env, rechecked['execution_handoff'], episode='episode_results_after_parent')
            assert env.adapter.information.qualify_results(after_parent_check)[0]['order']['job_ref'] == job
            assert env.ops.open_scope(job) == original_scope
    asyncio.run(run())
