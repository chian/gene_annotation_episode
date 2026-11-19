"""The A103 API job binding publishes its job's receipts on the shared Store and the A103 job provider and progress
provider watch that job from them.

Real binding, the run's one ``Store``, the real ``episode_runtime`` registry, journal and linker, a real
``ModelProvider`` (never called) and the real NCBI BLAST service over the binding's own ``ToolRegistry``. Its
``PublicClients`` are configured explicitly with no NCBI contact, so the original submission is refused by the
client's own local preflight and nothing is sent; no model, network or HPC is used. The units are driven through
the source's own admission and execution.
"""
import asyncio
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.gene_context_evidence.acquisition import PublicClients
from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.gene_context_evidence.job_provider import (
    API_HANDLE_PREFIX, API_RECEIPT_PROVIDER, JobProvider)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.practical_execution_records import digest
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.execution_job_submission.\
    api_job_execution.episode import ExecutionEpisode
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.home import (
    a103_progress_provider)
from gene_annotation_episode.episodic_workflow.episode_support.tools.gene_context_evidence.tools import ToolRegistry
from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store

RUN_ID = 'a103_api_job_receipts'
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
PROTEIN = ('MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQTLGQHDFSAGEG'
           'LYTHMKALRPDEDRLSPLHSVYVDQWDWERVMGDGERQFSTLKSTVEAIWAGIKATEAAVSEEFGLAPFLPDQIHFVHSQELLSRYPDLD'
           'AKGRERAIAKDLGAVFLVGIGGKLSDGHRHDVRAPDYDDWCAGLSEVLAKAS')


def linked(tmp_path, store):
    clients = PublicClients(ncbi_email=None, access_dir=None)
    binding = ExecutionEpisode(tool_registry=ToolRegistry(store, clients=clients), configuration={
        'resources': {'blast': {'kind': 'api', 'service': 'ncbi_blast'}},
        'continuation': {'cutoff': 0.001, 'uncertainty_alpha': 0.05}})
    store.create_problem(raw_sequence=PROTEIN, molecule='protein')
    subject = store.problem()['subject_refs'][0]
    scope = {'subject_refs': [subject]}
    request = {'subject_ref': subject, 'program': 'blastp', 'database': 'swissprot'}
    run = link(BindingRegistry([binding]), binding.binding_path,
               {'scope': scope, 'resource_id': 'blast', 'request': request},
               run_id=RUN_ID, journal=RunJournal(tmp_path / 'journal.sqlite'),
               collaborators={'store': store,
                              'model_provider': ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)})
    return run.episode.source


def unit(source, position, operation):
    selection, prepared = source.admit({'selection': {'operation': 'api.blast.' + operation, 'arguments': {}}},
                                       source.action_schema())
    return asyncio.run(source._execute(position, selection, prepared))


def test_each_api_operation_publishes_a_receipt_the_job_provider_builds_the_api_job_target_from(tmp_path):
    with Store(tmp_path / 'state') as store:
        source = linked(tmp_path, store)
        bound = source._bound
        jobs = JobProvider(store, run_id=RUN_ID)
        progress = a103_progress_provider(store, run_id=RUN_ID)
        assert jobs.jobs() == {}

        preparation = unit(source, 0, 'prepare')
        assert preparation['status'] == 'completed' and preparation['event']['kind'] == 'preparation'
        record = store.get(preparation['receipt_ref'])
        assert record['provider'] == API_RECEIPT_PROVIDER
        body = json.loads(store.get_artifact(record['artifact_ref']))
        assignment = json.loads(json.dumps(dict(bound.assignment)))
        assert {key: body[key] for key in ('run_id', 'episode_id', 'resource_id', 'service', 'request_sha256',
                                           'assignment_sha256', 'scope')} == {
            'run_id': RUN_ID, 'episode_id': bound.episode_id, 'resource_id': 'blast', 'service': 'ncbi_blast',
            'request_sha256': digest(source._request), 'assignment_sha256': digest(assignment),
            'scope': source._scope}
        assert body['receipt']['operation'] == 'api.blast.prepare' and body['receipt']['response_refs'] == []

        (handle,) = jobs.jobs()
        assert handle.startswith(API_HANDLE_PREFIX)
        assert jobs.scope(handle) == source._scope
        target = progress.describe_target(handle, source._scope)
        assert target == {**target, 'kind': 'api_job', 'run_id': RUN_ID, 'execution_episode_id': bound.episode_id,
                          'resource_kind': 'api', 'resource_id': 'blast', 'service': 'ncbi_blast',
                          'request': source._request, 'native_handle': None,
                          'receipt_refs': [preparation['receipt_ref']], 'response_refs': []}
        assert progress.direct_dependencies(handle, source._scope) == []

        # The original submission is refused by the client's local preflight: a failed unit with its receipt.
        submission = unit(source, 1, 'submit')
        assert submission['status'] == 'failed'
        assert submission['feedback']['code'] == 'ncbi_contact_not_configured'
        assert submission['feedback']['submission_outcome'] == 'not_sent'
        observed = progress.observe(handle, ['execution_status', 'committed_record_refs'], source._scope,
                                    permitted_committed_record_types=['source'], operation_key='watch.0')
        status = observed['execution_status']
        assert status['lifecycle_state'] is None and status['native']['state'] == 'unknown'
        assert {key: status[key] for key in ('resource_id', 'resource_kind', 'execution_id', 'request_sha256')} == {
            'resource_id': 'blast', 'resource_kind': 'api', 'execution_id': bound.episode_id,
            'request_sha256': digest(source._request)}
        assert observed['committed_record_refs'] == [preparation['receipt_ref'], submission['receipt_ref']]
        assert observed['result_available'] is False

        # A submission whose intent was recorded before an interruption is never issued again; its recorded
        # failure is still a receipt of the same job.
        selection, prepared = source.admit({'selection': {'operation': 'api.blast.submit', 'arguments': {}}},
                                           source.action_schema())
        bound.recorder.recorded('intent.2', lambda: {'operation': 'api.blast.submit', 'request': source._request,
                                                     'native_handle': None})
        unknown = asyncio.run(source._execute(2, selection, prepared))
        assert unknown['feedback']['code'] == 'issued_outcome_unknown'
        assert jobs.describe_target(handle, source._scope)['receipt_refs'] == [
            preparation['receipt_ref'], submission['receipt_ref'], unknown['receipt_ref']]
        assert list(jobs.jobs()) == [handle]

        with pytest.raises(KeyError):
            jobs.scope(API_HANDLE_PREFIX + 'unknown')
