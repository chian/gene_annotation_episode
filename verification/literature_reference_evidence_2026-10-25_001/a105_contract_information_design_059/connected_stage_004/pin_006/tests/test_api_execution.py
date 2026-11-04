"""Selected native-client fixtures exercise bounded API custody, no remote jobs."""
import asyncio
from dataclasses import replace
import hashlib
import json

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.api_execution import HMMERAPIExecution
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from api_execution_fixture import APIHarness
from test_public_search import Client, JOB, result, snapshot


@pytest.mark.parametrize('name', ['public.hmmer.databases', 'public.hmmer.search', 'public.hmmer.collect', 'public.hmmer.page'])
def test_ordinary_hmmer_bypasses_are_deleted(tmp_path, name):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        tools = ToolRegistry(store, clients=Client())
        assert name not in tools.catalog()
        response = tools.execute(name, {}, operation_key='removed')
        assert response['status'] == 'invalid' and response['feedback']['code'] == 'unknown_tool'
        assert tools.clients.submissions == tools.clients.status_calls == 0
        assert 'public.search.jobs' in tools.catalog()
        with pytest.raises(Exception, match='unimplemented_public_acquisition'):
            tools._acquisition_request(name, {}, None)


def test_each_choice_has_at_most_one_http_and_endpoint_is_receipt_proved(tmp_path):
    client = Client()
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        tools = ToolRegistry(store, clients=client)
        owner = APIHarness(tools, page_size=1)
        assert client.submissions == client.status_calls == 0
        prepared = owner.act('api.hmmer.prepare')
        assert prepared['status'] == 'completed' and not prepared['record_refs']
        request = prepared['result']['request']
        assert request['sequence_sha256'] == hashlib.sha256(b'MACDEFGH').hexdigest()
        assert request['query_sha256'] == hashlib.sha256(store.get_artifact(prepared['result']['fasta_ref'])).hexdigest()
        assert request['query_sha256'] != request['sequence_sha256']
        assert owner.api.credit_view(owner.context, owner.received_selection())['credit'] == 0
        submitted = owner.act('api.hmmer.submit')
        assert submitted['status'] == 'completed' and client.submissions == 1 and client.status_calls == 0
        assert owner.api.completion_for_action(owner.context, 'api-run:api-child:1') is None
        checked = owner.act('api.hmmer.check_handoff')
        handoff = checked['result']['handoff_ref']
        assert client.submissions == 1 and client.status_calls == 1
        target = owner.api.read_target(handoff, owner.context.scope)
        assert target['request_sha256'] == digest(owner.context.assignment) and target['execution_id'] == JOB
        proof = owner.api.completion_for_action(owner.context, 'api-run:api-child:2')
        assert proof['endpoint'] == 'usable_handoff' and len(proof) == 8
        assert owner.api.verify_completion(owner.context, proof)
        assert not owner.api.verify_completion(owner.context, {**proof, 'receipt_sha256': '0'*64})
        assert owner.api.facts(owner.context, {})['execution_completed'] is True
        assert owner.api.credit_view(owner.context, owner.received_selection())['credit'] == 2
        assert owner.act('api.hmmer.check_handoff', index=2) == checked
        assert client.status_calls == 1
        assert owner.act('api.hmmer.status')['feedback']['code'] == 'api_assignment_already_completed'
        receiver = owner.results(handoff)
        page = receiver.act('api.hmmer.result')
        assert page['status'] == 'completed', page
        assert page['result']['next_page'] == 2
        assert page['result']['database']['version'] == 'fixture-release'
        observation = store.get(page['result']['records'][0]['domain_observation_refs'][0])
        assert observation['measurements'] and observation['kind'] == 'comparison'
        source = store.get(page['result']['source_ref'])
        assert store.get_artifact(source['artifact_ref']) == snapshot(result()).content
        assert receiver.api.credit_view(receiver.context, receiver.received_selection())['credit'] == .25*len(page['record_refs'])
        inherited = receiver.received_selection(initial=page['record_refs'])
        assert receiver.api.credit_view(receiver.context, inherited)['credit'] == 0
        assert receiver.act('api.hmmer.result', index=0) == page
        assert not store.current_annotations()


def test_monitor_after_closed_handoff_is_independent_and_selected_replay_does_not_get(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        tools = ToolRegistry(store, clients=Client())
        owner = APIHarness(tools)
        handle = owner.handoff()
        before = [dict(row) for row in store.db.execute('SELECT * FROM api_execution_actions')]
        job_before = dict(store.db.execute('SELECT * FROM provider_jobs').fetchone())
        target = owner.api.read_target(handle, owner.context.scope)
        tools.clients.hmmer_status = lambda job: snapshot({'task': {'status': 'STARTED'}})
        observed = owner.api.observe_target(target, operation_key='monitor:0')
        assert observed['state'] == 'running' and observed['measurements'] == []
        tools.clients.hmmer_status = lambda job: (_ for _ in ()).throw(AssertionError('replay polled'))
        assert owner.api.observe_target(target, operation_key='monitor:0') == observed
        assert [dict(row) for row in store.db.execute('SELECT * FROM api_execution_actions')] == before
        assert dict(store.db.execute('SELECT * FROM provider_jobs').fetchone()) == job_before
        assert owner.api.facts(owner.context, {})['execution_completed']
        with pytest.raises(ValueError, match='api_observation_target_identity_conflict'):
            owner.api.observe_target({**target, 'execution_id': 'other'}, operation_key='monitor:1')


@pytest.mark.parametrize('body', [b'not-json', b'{"id":"bad-uuid"}', b'{}'])
def test_bad_submission_bytes_saved_before_handle_parse_and_never_resubmitted(tmp_path, body):
    client = Client()
    def malformed(*args, **kwargs):
        client.submissions += 1
        return replace(snapshot({}), content=body)
    client.hmmer_submit = malformed
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        tools = ToolRegistry(store, clients=client)
        owner = APIHarness(tools)
        failed = owner.act('api.hmmer.submit')
        assert failed['status'] == 'failed' and failed['feedback']['code'] == 'provider_submission_response_invalid'
        assert client.submissions == 1
        job = dict(store.db.execute('SELECT * FROM provider_jobs').fetchone())
        assert job['state'] == 'submission_uncertain'
        assert owner.api._load_snapshot(job['submission']).content == body
        assert owner.act('api.hmmer.submit', index=0) == failed
        again = owner.act('api.hmmer.submit')
        assert again['status'] == 'failed' and client.submissions == 1
        assert len(tools.remote_searches.jobs(active_only=False)) == 1
    with Store(tmp_path) as reopened:
        later = ToolRegistry(reopened, clients=Client())
        owner = APIHarness(later)
        assert owner.act('api.hmmer.submit', index=0) == failed
        assert later.clients.submissions == 0


def test_unknown_post_and_crash_gap_never_repeat(tmp_path):
    client = Client()
    def timeout(*args, **kwargs):
        client.submissions += 1
        raise TimeoutError('POST may have reached provider')
    client.hmmer_submit = timeout
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        owner = APIHarness(ToolRegistry(store, clients=client))
        failed = owner.act('api.hmmer.submit')
        assert failed['feedback']['code'] == 'remote_submission_uncertain'
        assert owner.act('api.hmmer.submit', index=0) == failed
        assert client.submissions == 1
        # Simulate interruption after intent commit but before response custody.
        store.db.execute('UPDATE api_execution_actions SET result=NULL WHERE operation_key=?', ('api-run:api-child:0',))
        uncertain = owner.act('api.hmmer.submit', index=0)
        assert uncertain['status'] == 'failed' and client.submissions == 1


@pytest.mark.parametrize('field,wrong', [('id', '00000000-0000-4000-8000-000000000000'),
    ('algo', 'hmmscan'), ('database', {'id': 'pdb'}), ('input', '>q\nYYYYYYYY')])
def test_conflicting_present_native_identity_cannot_validate_handoff(tmp_path, field, wrong):
    client = Client()
    client.hmmer_status = lambda job: snapshot({'task': {'status': 'SUCCESS'}, field: wrong})
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        owner = APIHarness(ToolRegistry(store, clients=client))
        assert owner.act('api.hmmer.submit')['status'] == 'completed'
        failed = owner.act('api.hmmer.check_handoff')
        assert failed['status'] == 'failed' and failed['feedback']['code'] == 'remote_identity_conflict_'+field
        assert owner.api.facts(owner.context, {})['execution_handoff_refs'] == []
        assert not store.count('observation')


@pytest.mark.parametrize('state,code', [('PENDING', 'remote_result_not_ready'), ('FAILURE', 'remote_search_failed')])
def test_selected_unready_page_is_not_acquired_or_credited(tmp_path, state, code):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        tools = ToolRegistry(store, clients=Client())
        owner = APIHarness(tools)
        handle = owner.handoff()
        receiver = owner.results(handle, page=2)
        tools.clients.hmmer_result = lambda *args, **kwargs: snapshot({'status': state, 'result': None})
        response = receiver.act('api.hmmer.result')
        assert response['status'] == 'failed' and response['feedback']['code'] == code
        assert not response['record_refs']
        assert receiver.api.credit_view(receiver.context, receiver.received_selection())['credit'] == 0
        assert receiver.act('api.hmmer.result', index=0) == response


def test_selected_scope_and_original_request_cannot_be_replaced(tmp_path):
    with Store(tmp_path) as store:
        fasta = tmp_path/'subjects.faa'
        fasta.write_text('>a\nMACDEFGH\n>b\nYYYYYYYY\n')
        subjects = store.create_problem(fasta, molecule='protein')['subject_refs']
        tools = ToolRegistry(store, clients=Client())
        owner = APIHarness(tools, subject_ref=subjects[0], scope={'subject_refs': [subjects[0]]})
        handle = owner.handoff()
        with pytest.raises(Exception):
            owner.api.read_target(handle, {'subject_refs': [subjects[1]]})
        with pytest.raises(ValueError, match='api_original_assignment_conflict'):
            APIHarness(tools, subject_ref=subjects[0], database='pdb', scope=plain_scope(owner))
        target = owner.api.read_target(handle, owner.context.scope)
        assert target['assignment']['database'] == 'swissprot'


def plain_scope(owner):
    from gene_annotation_episode.communication import plain
    return plain(owner.context.scope)


def test_partial_rows_keep_valid_contributions_and_cross_original_parent_scope(tmp_path):
    from gene_annotation_episode.episode_bindings import BindingContext
    from gene_annotation_episode.communication import plain
    native = result()
    broken = json.loads(json.dumps(native['result']['hits'][0]))
    broken['index'] = 1
    broken['metadata']['accession'] = 'BROKEN'
    broken['domains'][0]['alignment_display']['m'] = 99
    native['result']['hits'].append(broken)
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        tools = ToolRegistry(store, clients=Client())
        owner = APIHarness(tools)
        handle = owner.handoff()
        tools.clients.hmmer_result = lambda *args, **kwargs: snapshot(native)
        receiver = owner.results(handle)
        outcome = receiver.act('api.hmmer.result')
        assert outcome['status'] == 'partial' and outcome['record_refs']
        assert len(store.list('observation')) == 1
        assert not receiver.api.facts(receiver.context, {})['execution_completed']
        parent = BindingContext(owner.context.run_id, 'scientific-parent', 'annotation', (('annotation', 'root'),),
            plain(owner.context.scope), {}, {})
        for reference in outcome['record_refs']:
            assert receiver.api.resolve(parent, reference, 'execution_result')
            assert receiver.api.read_result(reference, parent.scope)['status'] == 'partial'
        assert receiver.api.credit_view(receiver.context, receiver.received_selection())['credit'] == .25*len(outcome['record_refs'])


def test_results_original_page_completion_is_verified_and_stops_new_acquisition(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        owner = APIHarness(ToolRegistry(store, clients=Client()))
        receiver = owner.results(owner.handoff(), page=2, page_size=1)
        outcome = receiver.act('api.hmmer.result')
        assert outcome['status'] == 'completed'
        proof = receiver.api.completion_for_action(receiver.context, 'api-run:results-child:0')
        assert proof['validation_keys'] == ['requested_result_page'] and len(proof) == 8
        assert receiver.api.verify_completion(receiver.context, proof)
        assert receiver.api.facts(receiver.context, {})['execution_completed']
        assert receiver.act('api.hmmer.result')['feedback']['code'] == 'api_assignment_already_completed'


def test_missing_status_is_unknown_and_cannot_manufacture_a_handoff(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        owner = APIHarness(ToolRegistry(store, clients=Client()))
        owner.act('api.hmmer.submit')
        owner.tools.clients.hmmer_status = lambda job: snapshot({})
        failed = owner.act('api.hmmer.check_handoff')
        assert failed['status'] == 'failed' and failed['feedback']['code'] == 'unknown_remote_search_status'
        assert not owner.api.facts(owner.context, {})['execution_completed']


def test_reacquiring_identical_page_with_new_custody_time_has_no_inherited_gain(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        owner = APIHarness(ToolRegistry(store, clients=Client()))
        handle = owner.handoff()
        first = owner.results(handle)
        original = first.act('api.hmmer.result')
        owner.tools.clients.hmmer_result = lambda *args, **kwargs: replace(snapshot(result()),
            retrieved_at='2026-10-22T00:00:00+00:00')
        second = owner.results(handle, episode_id='new-custody')
        repeated = second.act('api.hmmer.result')
        assert repeated['record_refs'] != original['record_refs']
        assert second.api.credit_view(second.context,
            second.received_selection(refs=original['record_refs']+repeated['record_refs'],
                initial=original['record_refs']))['credit'] == 0


def test_api_handoff_result_and_completion_cannot_resolve_in_another_run(tmp_path):
    from gene_annotation_episode.episode_bindings import BindingContext
    from gene_annotation_episode.communication import plain
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        owner = APIHarness(ToolRegistry(store, clients=Client()))
        handle = owner.handoff()
        receiver = owner.results(handle)
        outcome = receiver.act('api.hmmer.result')
        parent = BindingContext('other-run', 'parent', 'annotation', (('annotation', 'parent'),),
            plain(owner.context.scope), {}, {})
        assert not owner.api.resolve(parent, handle, 'execution_handoff')
        assert not owner.api.resolve(parent, outcome['record_refs'][0], 'execution_result')
        foreign = BindingContext('other-run', owner.context.episode_id, 'launch_api', owner.context.path,
            plain(owner.context.scope), plain(owner.context.assignment), {})
        proof = owner.api.completion_for_action(owner.context, 'api-run:api-child:1')
        assert not owner.api.verify_completion(foreign, proof)


def test_submit_recovery_after_native_identity_commit_preserves_submitted_state(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        owner = APIHarness(ToolRegistry(store, clients=Client()))
        original = owner.act('api.hmmer.submit')
        assert original['result']['state'] == 'submitted'
        store.db.execute('UPDATE api_execution_actions SET result=NULL WHERE operation_key=?', ('api-run:api-child:0',))
        store.db.execute('UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=? AND decision_index=0',
                         ('api-run', 'api-child'))
        assert owner.act('api.hmmer.submit', index=0) == original
        assert owner.tools.clients.submissions == 1


@pytest.mark.parametrize('content,expected', [(b'{"databases":[{"id":"swissprot","version":"fixture"}]}', 'completed'),
    (b'{"databases":[NaN]}', 'failed')])
def test_database_discovery_is_one_bounded_get_with_zero_preparation_credit(tmp_path, content, expected):
    client = Client()
    calls = []
    def databases():
        calls.append('GET')
        return replace(snapshot({}), content=content)
    client.hmmer_databases = databases
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        owner = APIHarness(ToolRegistry(store, clients=client))
        outcome = owner.act('api.hmmer.databases')
        assert outcome['status'] == expected and calls == ['GET']
        assert owner.act('api.hmmer.databases', index=0) == outcome and calls == ['GET']
        assert owner.api.credit_view(owner.context, owner.received_selection())['credit'] == 0
        if expected == 'completed':
            assert store.get_artifact(outcome['result']['raw_artifact_ref']) == content
        else:
            assert outcome['feedback']['code'] == 'provider_database_response_invalid'


def test_finite_caller_units_cannot_overflow_returned_api_credit(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        owner = APIHarness(ToolRegistry(store, clients=Client()))
        receiver = owner.results(owner.handoff())
        receiver.act('api.hmmer.result')
        oversized = HMMERAPIExecution(store, run_id=owner.context.run_id, directory=store.path/'large-unit',
            configuration={'ebi': {'kind': 'hmmer_api'}}, tool_registry=owner.tools,
            handoff_unit=1., acquired_record_unit=1e308)
        with pytest.raises(ValueError, match='finite_operational_credit_required'):
            oversized.credit_view(receiver.context, receiver.received_selection())


def test_database_string_identity_remains_valid_without_inventing_a_version(tmp_path):
    client = Client()
    client.hmmer_status = lambda job: snapshot({'task': {'status': 'SUCCESS'}, 'database': 'swissprot'})
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        owner = APIHarness(ToolRegistry(store, clients=client))
        receiver = owner.results(owner.handoff())
        acquired = receiver.act('api.hmmer.result')
        assert acquired['status'] == 'completed', acquired
        assert acquired['result']['database'] == 'swissprot'
        assert store.get(acquired['result']['source_ref'])['version'] is None
