"""The A106 SRA file acquisition reads its advertisement File only through the caller's received records.

Real Store, real A106 ToolRegistry and the retained NCBI experiment-package XML fixture
(``fixtures/ncbi_sra``). Every case ends before the transfer: no network request is made.
"""
import asyncio
import hashlib
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.sequence_and_context_sources.perturbation_evidence.ncbi_sra_acquisition import (
    TOOL, resolve_sra_file_selection, sra_file_request_spec)
from gene_annotation_episode.episodic_workflow.episode_support.tools.perturbation_evidence.tools import ToolRegistry
from gene_annotation_episode.state import Store

ADVERTISEMENT = Path(__file__).parent / 'fixtures' / 'ncbi_sra' / 'experiment_package.xml'


def setup(path):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    raw = ADVERTISEMENT.read_bytes()
    artifact = store.artifact(raw, 'application/xml')
    source = store.put('source', {'provider': 'public.ncbi.entrez', 'accession': None, 'uri': None,
                                  'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'version': None,
                                  'retrieved_at': None}, origin='caller')
    return store, ToolRegistry(store), raw, artifact, source['id'], {'subject_refs': store.problem()['subject_refs']}


def arguments(raw, artifact, **changes):
    """The second advertised SRAFile of the fixture's only run (its native ``url`` attribute)."""
    value = {'advertisement_file': {'artifact_ref': artifact, 'sha256': hashlib.sha256(raw).hexdigest(),
                                    'size_bytes': len(raw), 'format': 'sra_experiment_package_xml'},
             'experiment_package_ordinal_0based': 0, 'run_ordinal_0based': 0, 'file_ordinal_0based': 1,
             'url_selection': {'kind': 'file_url'}, 'run_accession': 'SRR6263255', 'semantic_name': 'SRA Normalized',
             'supertype': 'Primary ETL', 'file_name': 'SRR6263255',
             'url': 'https://sra-pub-run-odp.s3.amazonaws.com/sra/SRR6263255/SRR6263255', 'max_bytes': 1024}
    value.update(changes)
    return value


def execute(registry, args, scope, key, permitted):
    return asyncio.run(registry.execute_async(TOOL, args, scope=scope, operation_key=key,
                                              permitted_record_refs=permitted))


def test_an_advertisement_the_caller_did_not_receive_is_not_read(tmp_path):
    store, registry, raw, artifact, _, scope = setup(tmp_path)
    result = execute(registry, arguments(raw, artifact), scope, 'not-received', [])
    assert result['status'] == 'invalid'
    assert result['feedback']['code'] == 'sra_file_input_not_received'
    assert result['result'] == {'acquired': False, 'source_ref': None, 'data_ref': None,
                                'failure_code': 'sra_file_input_not_received'}


def test_the_caller_must_bind_its_received_records(tmp_path):
    store, registry, raw, artifact, _, scope = setup(tmp_path)
    result = execute(registry, arguments(raw, artifact), scope, 'unbound', None)
    assert result['status'] == 'invalid'
    assert result['feedback']['code'] == 'explicit_permitted_record_refs_required'
    assert result['result']['acquired'] is False


def test_a_supplied_identity_other_than_the_retained_bytes_conflicts(tmp_path):
    store, registry, raw, artifact, source, scope = setup(tmp_path)
    args = arguments(raw, artifact)
    args['advertisement_file']['size_bytes'] = len(raw) + 1
    result = execute(registry, args, scope, 'identity', [source])
    assert result['result']['failure_code'] == 'sra_file_input_identity_conflict'


def test_an_occurrence_the_received_advertisement_lacks_is_unavailable(tmp_path):
    store, registry, raw, artifact, source, scope = setup(tmp_path)
    result = execute(registry, arguments(raw, artifact, file_ordinal_0based=5), scope, 'absent', [source])
    assert result['result']['failure_code'] == 'sra_file_selection_unavailable'


def test_a_received_advertisement_selects_exactly_its_advertised_transfer(tmp_path):
    store, registry, raw, artifact, source, scope = setup(tmp_path)
    args = arguments(raw, artifact)
    selection = resolve_sra_file_selection(raw, arguments=args)
    for received in ([source], [artifact]):
        token = registry._permitted_record_refs.set(tuple(received))
        try:
            function, request = registry._acquisition_request(TOOL, args, scope)
        finally:
            registry._permitted_record_refs.reset(token)
        assert function == registry.clients._http
        assert request == {**sra_file_request_spec(args, selection=selection),
                           'timeout_seconds': registry.clients.timeout}
        assert request['follow_redirects'] is False and request['max_bytes'] == 1024
