"""Selected HTTP recovery and protocol/result boundaries; no external calls."""
import asyncio

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.execution_contracts import canonical
from test_api_blast_service import Client as BlastClient
from test_api_service_integration import assignment, generic_host, service_responses
from test_execution_episodes_family import context, select


def selected_intent(h, ctx, index, name):
    with h.store.transaction():
        h.journal.save('runtime_actions', {'episode_id': ctx.episode_id,
            'decision_index': index, 'action': canonical({'kind': 'tool',
                'tool': name, 'arguments': {}}), 'result': None, 'credit': None})
    return f'{ctx.run_id}:{ctx.episode_id}:{index}'


def remember(h, ctx, index, result):
    with h.store.transaction():
        h.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? '
            'AND episode_id=? AND decision_index=?',
            (canonical(result), ctx.run_id, ctx.episode_id, index))


def record_context(h, episode='api'):
    request = assignment('uniprot', 'uniprot', {'operation': 'record', 'accession': 'P12345'})
    return context(h, 'launch_api', request, episode)


def test_received_response_survives_interrupted_decoding_without_another_request(generic_host, monkeypatch):
    h = generic_host
    ctx = record_context(h)
    service = h.family.api_execution.services['uniprot']
    decode = service.decode
    first = True

    def interrupted(command, snapshot):
        nonlocal first
        if first:
            first = False
            raise asyncio.CancelledError()
        return decode(command, snapshot)

    monkeypatch.setattr(service, 'decode', interrupted)
    key = selected_intent(h, ctx, 0, 'api.uniprot.record')
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(h.family.execute(ctx, 'api.uniprot.record', {}, key))
    assert len(h.client.requests) == 1
    restored = asyncio.run(h.family.execute(ctx, 'api.uniprot.record', {}, key))
    assert restored['status'] == 'completed', restored
    assert len(h.client.requests) == 1
    remember(h, ctx, 0, restored)
    proof = h.family.completion_for_action(ctx, key)
    assert proof and h.family.verify_completion(ctx, proof)
    handoff, = restored['record_refs']
    target = h.family.job_progress_provider.targets.read_target(handoff, h.scope)
    assert target['execution_id'].startswith('request:')  # Actual recorded GET, no remote job.
    observed = h.family.api_execution.observe_target(target, operation_key='after-recovery')
    assert observed['state'] == 'completed'
    assert observed['observed_at'] == '2026-10-23T12:00:01+00:00'
    assert len(h.client.requests) == 1


def test_concurrent_original_action_replay_makes_one_request(generic_host):
    h = generic_host
    ctx = record_context(h)
    key = selected_intent(h, ctx, 0, 'api.uniprot.record')

    async def run():
        return await asyncio.gather(
            h.family.execute(ctx, 'api.uniprot.record', {}, key),
            h.family.execute(ctx, 'api.uniprot.record', {}, key))

    one, two = asyncio.run(run())
    assert one == two and one['status'] == 'completed'
    assert len(h.client.requests) == 1


def blast_context(h):
    client = BlastClient()
    h.family.api_execution.services['ncbi-blast'].client = client
    request = assignment('ncbi-blast', 'ncbi_blast', {'subject_ref': h.target,
        'program': 'blastp', 'database': 'swissprot'})
    return context(h, 'launch_api', request, 'blast'), client


def test_lost_submission_reply_cannot_create_replacement_job(generic_host, monkeypatch):
    h = generic_host
    ctx, client = blast_context(h)

    def unknown(action, **arguments):
        client.calls.append((action, arguments))
        raise AcquisitionError('submission_reply_lost', phase='submission', submission_outcome='unknown')

    monkeypatch.setattr(client, 'blast', unknown)
    failed = select(h, ctx, 0, 'api.blast.submit')
    assert failed['status'] == 'failed'
    key = f'{ctx.run_id}:{ctx.episode_id}:0'
    assert asyncio.run(h.family.execute(ctx, 'api.blast.submit', {}, key)) == failed
    replacement = select(h, ctx, 1, 'api.blast.submit')
    assert replacement['status'] == 'invalid'
    assert replacement['feedback']['code'] == 'api_original_submission_already_exists'
    assert len(client.calls) == 1


def test_explicit_not_sent_failure_allows_a_later_selected_submission(generic_host):
    h = generic_host
    ctx, client = blast_context(h)
    client.refuse = True
    failed = select(h, ctx, 0, 'api.blast.submit')
    assert failed['feedback']['submission_outcome'] == 'not_sent'
    client.refuse = False
    accepted = select(h, ctx, 1, 'api.blast.submit')
    assert accepted['status'] == 'completed', accepted
    assert [row[0] for row in client.calls] == ['submit', 'submit']
    assert len(accepted['record_refs']) == 1


def test_result_status_is_information_until_actual_native_result_is_fetched(generic_host):
    h = generic_host
    ctx, client = blast_context(h)
    launched = select(h, ctx, 0, 'api.blast.submit')
    assert launched['status'] == 'completed', launched
    handoff, = launched['record_refs']
    requested = {'version': 'execution_results_assignment_v1', 'handoff_ref': handoff, 'selector': {}}
    receiver = context(h, 'results', requested, 'blast-results')
    status = select(h, receiver, 0, 'api.blast.status')
    assert status['status'] == 'completed', status
    assert status['record_refs'] == []
    assert h.family.facts(receiver, {})['execution_completed'] is False
    assert h.store.count('observation') == 0
    fetched = select(h, receiver, 1, 'api.blast.fetch')
    assert fetched['status'] == 'completed', fetched
    assert h.family.facts(receiver, {})['execution_completed'] is True
    assert [row[0] for row in client.calls] == ['submit', 'status', 'fetch']
    assert h.store.count('annotation') == 0
    observation = next(h.store.get(ref) for ref in fetched['record_refs']
        if h.store.get(ref)['record_type'] == 'observation')
    assert observation['subject_refs'] == [h.target]
    assert observation['source_subject_refs'] != [h.target]


def test_result_publication_recovers_without_rereading_or_duplicating_sources(generic_host, monkeypatch):
    h = generic_host
    ctx = record_context(h)
    launched = select(h, ctx, 0, 'api.uniprot.record')
    handoff, = launched['record_refs']
    receiver = context(h, 'results', {'version': 'execution_results_assignment_v1',
        'handoff_ref': handoff, 'selector': {}}, 'results')
    core = h.family.api_execution
    index = core._index_result
    first = True

    def interrupted(*args):
        nonlocal first
        if first:
            first = False
            raise asyncio.CancelledError()
        return index(*args)

    monkeypatch.setattr(core, '_index_result', interrupted)
    key = selected_intent(h, receiver, 0, 'api.uniprot.collect')
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(h.family.execute(receiver, 'api.uniprot.collect', {}, key))
    sources = h.store.count('source')
    restored = asyncio.run(h.family.execute(receiver, 'api.uniprot.collect', {}, key))
    assert restored['status'] == 'completed', restored
    remember(h, receiver, 0, restored)
    assert h.store.count('source') == sources
    assert len(h.client.requests) == 1
    assert h.family.facts(receiver, {})['execution_completed'] is True
    for ref in restored['record_refs']:
        assert core.read_result(ref, h.scope)['source_ref'] == restored['result']['source_ref']
