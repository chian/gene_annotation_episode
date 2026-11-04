"""Actual registered operand parity with in-memory HMMER fixture transport."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import json

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.hmmer_request_preparation import prepare_hmmer_request, qualify_api_candidate
from gene_annotation_episode.hmmer_resource_information import ApiSearchInformationReader
from gene_annotation_episode.public_search_operations import ProviderJobOperations, PublicSearchPorts
from gene_annotation_episode.public_search_publication import PublicSearchResultPublisher
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_hmmer_api_operations import FixtureClient, registry


def configured(path):
    store = Store(path)
    problem = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
    client = FixtureClient()
    client.state = 'SUCCESS'
    tools = ToolRegistry(store, clients=client, provider_poll_interval_seconds=0)
    operations = ProviderJobOperations(store, tools.remote_searches, registry=registry(client))
    ports = PublicSearchPorts(operations.registry, operations,
        PublicSearchResultPublisher(store, tools, operations=operations))
    return store, client, tools, ports, {'subject_refs': problem['subject_refs']}


def rootless_sequence(store):
    with store.transaction():
        artifact = store.artifact('fixture evidence', 'text/plain')
        source = store.put('source', {'provider': 'fixture', 'accession': None, 'uri': None,
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': 'fixture',
            'retrieved_at': '2026-10-22T00:00:00+00:00'}, origin='external')
        return store.put('reference', {'reference_type': 'protein', 'source_ref': source['id'],
            'accession': 'FIXTURE', 'label': 'fixture protein', 'sequence_ref': store.artifact('ma c\nDEfgH'),
            'molecule': 'protein', 'length': len('ma c\nDEfgH'), 'term_refs': [], 'context_refs': []}, origin='external')['id']


@pytest.mark.parametrize('explicit', [False, True])
def test_shared_preparation_matches_fresh_assignment_order_and_ordinary_search(tmp_path, explicit):
    store, client, tools, ports, scope = configured(tmp_path)
    with store:
        subject = rootless_sequence(store)
        arguments = {'subject_ref': subject, 'algorithm': 'phmmer', 'database': 'swissprot'}
        if explicit:
            arguments.update(parameters={'E': .002, 'include_taxonomy': [562]}, page_size=2)
        original = deepcopy(arguments)
        prepared = prepare_hmmer_request(arguments, sequence_symbols=ports.sequence_symbols, scope=scope)
        reader = ApiSearchInformationReader(store, run_id='preparation-run', ports=ports)
        assignment = {'job_request': {'provider': 'hmmer', **arguments}}
        context = BindingContext('preparation-run', 'episode_fixture', 'launch',
            (('launch', 'fixture'),), scope, assignment, {})
        request, fasta = reader.request_for_assignment(context)
        assert request == plain(prepared.request)
        assert fasta == prepared.query_fasta == '>' + subject + '\nma c\nDEfgH'
        assert request['query_length'] == 8
        assert request['sequence_sha256'] == hashlib.sha256(b'MACDEFGH').hexdigest()
        assert request['query_sha256'] == hashlib.sha256(fasta.encode()).hexdigest()
        assert plain(prepared.arguments) == original
        assert plain(prepared.normalized_arguments) == {**original,
            'parameters': original.get('parameters', {}), 'page_size': original.get('page_size', 50)}
        assert client.calls == []
        order = ports.operations.order(operation_key='selected-order', provider='hmmer', scope=scope,
            query_fasta=fasta, **plain(prepared.normalized_arguments))
        assert ports.operations.inspect(order['job_ref'])['request'] == request
        result = tools.execute('public.hmmer.search', arguments, scope=scope, operation_key='ordinary-search')
        assert result['status'] == 'completed', result
        ordinary = tools.remote_searches.describe(result['result']['job_ref'])['request']
        assert ordinary == request
        assert client.calls[0] == ('submit', fasta, {'algorithm': 'phmmer', 'database': 'swissprot',
            'parameters': original.get('parameters', {})})
        source = store.get(result['result']['source_ref'])
        snapshot_request = json.loads(store.get_artifact(source['request_ref']))['request']
        assert snapshot_request['molecule_model'] == 'protein'
        assert snapshot_request['molecule_assignment'] == 'not_performed'
        arguments['database'] = 'changed'
        assert plain(prepared.arguments) == original
        with pytest.raises(TypeError):
            prepared.request['database'] = 'changed'
        with pytest.raises(FrozenInstanceError):
            prepared.query_fasta = 'changed'


@pytest.mark.parametrize('value', [float('nan'), float('inf'), float('-inf'), True, '1'])
def test_parameter_failure_precedes_accessor_and_json_canonicalization(value):
    calls = []
    def symbols(reference, *, scope):
        calls.append(reference)
        raise AssertionError('invalid input reached sequence accessor')
    with pytest.raises(ValueError, match='unsupported_api_job_request'):
        prepare_hmmer_request({'subject_ref': 'input_' + 'a' * 24, 'algorithm': 'phmmer',
            'database': 'swissprot', 'parameters': {'E': value}}, sequence_symbols=symbols, scope=None)
    assert calls == []


def test_registered_operand_scope_alias_and_explicit_versions_remain_authoritative(tmp_path):
    store, client, tools, ports, scope = configured(tmp_path)
    with store:
        subject = scope['subject_refs'][0]
        arguments = {'subject_ref': subject, 'algorithm': 'hmmscan', 'database': 'pfam'}
        restricted = {'subject_refs': [subject], 'segments': [
            {'target_ref': subject, 'start': 0, 'end': 4, 'unit': 'aa'}]}
        with pytest.raises(ContractError, match='requested_measurement_outside_assigned_segments'):
            prepare_hmmer_request(arguments, sequence_symbols=ports.sequence_symbols, scope=restricted)
        with pytest.raises(ContractError, match='unknown_reference'):
            prepare_hmmer_request({**arguments, 'subject_ref': '@earlier'},
                sequence_symbols=ports.sequence_symbols, scope=scope)
        reader = ApiSearchInformationReader(store, run_id='preparation-run', ports=ports)
        pins = [{'reference': subject, 'version': None,
            'content_sha256': hashlib.sha256(b'MACDEFGH').hexdigest()}]
        qualify_api_candidate(store, scope=scope, selection=reader.selection(),
            constraints={'kind': 'api', 'allowed_kinds': ['api'], 'cpu': None}, immutable_input_versions=pins)
        for constraints in ({'cpu': 2}, {'unknown': None}, {'allowed_resource_ids': []}):
            with pytest.raises(ValueError):
                qualify_api_candidate(store, scope=scope, selection=reader.selection(),
                    constraints=constraints, immutable_input_versions=[])
        for pin in ({**pins[0], 'version': 'invented'}, {**pins[0], 'content_sha256': '0' * 64}):
            with pytest.raises(ValueError, match='resource_input_version_conflict'):
                qualify_api_candidate(store, scope=scope, selection=reader.selection(),
                    constraints={}, immutable_input_versions=[pin])
        assert client.calls == []
        assert store.db.execute('SELECT count(*) FROM provider_jobs').fetchone()[0] == 0


def test_existing_job_assignment_retains_saved_request_and_exact_fasta(tmp_path):
    store, client, tools, ports, scope = configured(tmp_path)
    with store:
        subject = scope['subject_refs'][0]
        fasta = '>historical submitted header\nMACDEFGH\n'
        order = ports.operations.order(operation_key='existing', provider='hmmer', subject_ref=subject,
            query_fasta=fasta, algorithm='phmmer', database='swissprot', scope=scope)
        reader = ApiSearchInformationReader(store, run_id='preparation-run', ports=ports)
        context = BindingContext('preparation-run', 'episode_fixture', 'launch',
            (('launch', 'fixture'),), scope,
            {'job_request': {'provider': 'hmmer', 'existing_job_ref': order['job_ref']}}, {})
        request, actual_fasta = reader.request_for_assignment(context)
        assert actual_fasta == fasta
        assert request == ports.operations.inspect(order['job_ref'])['request']
        assert client.calls == []
