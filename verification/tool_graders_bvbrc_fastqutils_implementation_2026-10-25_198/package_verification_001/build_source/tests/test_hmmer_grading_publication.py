"""HMMER page publication with retained bytes and explicitly synthetic transport.

No service, native algorithm, model, or pending NCBI job is called. Retained
phmmer response bytes are historical actual service output; all manipulated
responses and the hmmscan examples below are synthetic fault/numerical fixtures.
"""
from copy import deepcopy
from dataclasses import replace
import json
import math
from pathlib import Path
import socket
import subprocess
import urllib.request

import pytest
import requests

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.hmmer_graders import api_domain_scores
from gene_annotation_episode.hmmer_search_grader import calculate_hmmer_search_scores
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import source_tool_gradings
from gene_annotation_episode.tools import ToolRegistry
from api_execution_fixture import APIHarness


ROOT = Path(__file__).resolve().parents[1]
CAPTURES = ROOT / 'verification/hmmer_reported_timing_actual_service_2026-10-22_001/workspace/public-search-http-captures'
PAGE1 = CAPTURES / '26bc8bd463741aea924eabd181e41bfc91237dc04a04c7a3f5d03f6f64bd1e39/response.entity'
PAGE2 = CAPTURES / '4e88be472b0304cdea6ed5c38126eef0d7865b5345ad21863e9c9e318afc1c67/response.entity'
STATUS = CAPTURES / '4f8a4e3724b4713cc66862aca1fd3b6849fcfd5f55ddabd46e74f3accc29dc0a/response.entity'
ACTUAL = json.loads(STATUS.read_bytes())
QUERY = ''.join(ACTUAL['input'].splitlines()[1:])


@pytest.fixture(autouse=True)
def prohibit_live_network_and_native_execution(monkeypatch):
    def prohibited(*args, **kwargs):
        raise AssertionError('this verification permits supplied bytes only')
    monkeypatch.setattr(socket, 'create_connection', prohibited)
    monkeypatch.setattr(requests.sessions.Session, 'request', prohibited)
    monkeypatch.setattr(urllib.request, 'urlopen', prohibited)
    monkeypatch.setattr(subprocess, 'Popen', prohibited)


class RetainedClient:
    """Synthetic HTTP transport returning exact retained or synthetic bodies."""
    def __init__(self, body=None, *, algorithm='phmmer', database='pdb'):
        self.body = PAGE1.read_bytes() if body is None else body
        self.algorithm, self.database = algorithm, database
        self.calls, self.submitted_fasta = [], None

    def snapshot(self, body):
        return SourceSnapshot('ebi_hmmer', 'https://fixture.invalid/retained-hmmer', {},
            '2026-10-24T00:00:00+00:00', body if isinstance(body, bytes) else json.dumps(body).encode(),
            'application/json', {'representation': 'synthetic_transport_retained_or_synthetic_body'})

    def hmmer_submit(self, query_fasta, **kwargs):
        self.calls.append(('submit', kwargs))
        self.submitted_fasta = query_fasta
        return self.snapshot({'id': ACTUAL['id']})

    def hmmer_status(self, job_id):
        assert job_id == ACTUAL['id']
        self.calls.append(('status', job_id))
        return self.snapshot({'id': job_id, 'task': {'status': 'SUCCESS'}, 'algo': self.algorithm,
            'database': {'id': self.database, 'version': 'fixture-version'}, 'input': self.submitted_fasta})

    def hmmer_result(self, job_id, **kwargs):
        assert job_id == ACTUAL['id']
        self.calls.append(('result', kwargs))
        return self.snapshot(self.body)


def synthetic_payload(algorithm='phmmer'):
    """Five columns: 3 paired, one insertion, one deletion; asymmetric axes."""
    display = {'model': 'AC.DE', 'aseq': 'ACG-E', 'mline': 'AC  E', 'ppline': '0*9.*',
        'hmmfrom': 1, 'hmmto': 4, 'sqfrom': 2, 'sqto': 5, 'm': 10, 'l': 12, 'n': 5,
        'hmmname': 'query' if algorithm == 'phmmer' else 'PF_SYNTHETIC',
        'sqname': 'target' if algorithm == 'phmmer' else 'query', 'identity': [.75, 3]}
    return {'status': 'SUCCESS', 'page_count': 1, 'result': {
        'stats': {'algo': algorithm, 'nreported': 1}, 'hits': [{
            'index': 17, 'name': 'target' if algorithm == 'phmmer' else 'PF_SYNTHETIC',
            'acc': None, 'score': 8., 'bias': .2, 'evalue': 0., 'is_reported': True,
            'is_included': False, 'ndom': 1, 'nreported': 1, 'nincluded': 0,
            'metadata': {'accession': 'SYNTHETIC_TARGET', 'description': 'Explicitly synthetic fixture'},
            'domains': [{'ienv': 1, 'jenv': 7, 'bitscore': -2.5, 'dombias': math.log(2),
                'cevalue': 0., 'ievalue': 3., 'is_reported': True, 'is_included': False,
                'alignment_display': display}]}]}}


def receiver(store, *, body=None, algorithm='phmmer', sequence=QUERY, page=1, page_size=2):
    store.create_problem(raw_sequence=sequence, molecule='protein')
    database = 'pdb' if algorithm == 'phmmer' else 'pfam'
    client = RetainedClient(body, algorithm=algorithm, database=database)
    tools = ToolRegistry(store, clients=client)
    owner = APIHarness(tools, algorithm=algorithm, database=database, page_size=page_size)
    result_owner = owner.results(owner.handoff(), page=page)
    return tools, client, owner, result_owner


def grading_for(store, outcome):
    grading, = source_tool_gradings(store, outcome['result']['source_ref'])
    return grading


def numeric(store, reference):
    return {x['name']: x['value']['value'] for x in store.get(reference)['measurements']
            if x['value']['type'] == 'number'}


def domain_refs(outcome, hit=0):
    return {x['domain_array_index']: x['observation_ref']
            for x in outcome['result']['records'][hit]['domain_publications']}


def test_retained_phmmer_full_page_custody_and_checkable_distinct_components(tmp_path):
    with Store(tmp_path) as store:
        tools, client, owner, result_owner = receiver(store)
        outcome = result_owner.act('api.hmmer.result')
        assert outcome['status'] == 'completed', outcome
        source = store.get(outcome['result']['source_ref'])
        assert store.get_artifact(source['artifact_ref']) == PAGE1.read_bytes()
        grading = grading_for(store, outcome)
        assert len(grading['sheet']['hits']) == 2 and len(grading['sheet']['domains']) == 4
        assert grading['sheet']['inputs']['acquisition']['hit_population_complete'] is False
        assert grading['sheet']['inputs']['acquisition']['output_complete'] is True
        metadata = grading['sheet']['hits'][0]['identifiers']['metadata']
        assert metadata['accession'] == '6lpm_A' and metadata['uniprot_accession'] == 'Q9RXF9'
        published = outcome['result']['records'][0]
        assert published['accession'] == published['provider_accession'] == '6lpm_A'
        assert published['linked_uniprot_accession'] == 'Q9RXF9'
        assert published['native_name'] == '000058351' and published['native_accession'] is None
        assert store.get(published['reference_ref'])['accession'] == '6lpm_A'
        assert store.get(published['reference_ref'])['length'] == 283
        values = numeric(store, domain_refs(outcome)[1])
        for key, expected in {'model_length': 253, 'sequence_length': 283,
            'paired_positions': 88, 'insert_positions': 2, 'delete_positions': 1,
            'alignment_columns': 91, 'model_span_positions': 89, 'sequence_span_residues': 90,
            'api_identity_fraction': 25/89, 'consensus_identity_fraction': 25/88,
            'alignment_identity_fraction': 25/91, 'model_span_coverage': 89/253,
            'paired_model_coverage': 88/253, 'sequence_span_coverage': 90/283,
            'paired_sequence_coverage': 88/283,
            'native_domain_bias_bits': .03572461009025574/math.log(2),
            'posterior_lower_mean': .8277777777777777,
            'posterior_upper_mean': 81.85/90}.items():
            assert values[key] == pytest.approx(expected), key
        assert 'identity_fraction' not in values and 'sequence_identity_fraction' not in values
        assert 'elapsed' not in values and 'native_accuracy' not in values
        assert numeric(store, domain_refs(outcome)[0])['native_domain_score_bits'] < 0
        score = api_domain_scores(grading, hit_array_index=0, domain_array_index=1,
                                  artifact_ref=source['artifact_ref'])
        assert score['native']['domain_bias_nats'] == .03572461009025574
        for key, den in [('api_identity_fraction', 89), ('consensus_identity_fraction', 88),
                         ('alignment_identity_fraction', 91)]:
            assert score['components'][key]['numerator'] == 25
            assert score['components'][key]['denominator'] == den
        assert [x[0] for x in client.calls] == ['submit', 'status', 'result']
        assert len(store.list('observation')) == 4
        assert store.db.execute('SELECT count(*) FROM tool_operations').fetchone()[0] == 1
        assert not store.current_annotations()


def test_original_domain_indices_survive_invalid_internal_row_and_duplicate_provider_indices(tmp_path):
    body = json.loads(PAGE1.read_bytes())
    body['result']['hits'][0]['domains'].insert(1, 'invalid internal domain')
    body['result']['hits'][1]['index'] = body['result']['hits'][0]['index']
    with Store(tmp_path) as store:
        _, _, _, result_owner = receiver(store, body=body)
        outcome = result_owner.act('api.hmmer.result')
        assert outcome['status'] == 'partial'
        assert set(domain_refs(outcome)) == {0, 2, 3}
        assert numeric(store, domain_refs(outcome)[2])['consensus_identity_fraction'] == pytest.approx(25/88)
        assert numeric(store, domain_refs(outcome, 1)[0])['consensus_identity_fraction'] == pytest.approx(38/114)
        assert [r['native_index'] for r in outcome['result']['records']] == [0, 0]
        assert [r['native_array_index'] for r in outcome['result']['records']] == [0, 1]
        assert any(e.get('domain_array_index') == 1 for e in outcome['result']['projection_errors'])
        assert len(grading_for(store, outcome)['scores']['domains']) == 4


def test_invalid_query_length_preserves_later_sibling_and_exact_raw_page(tmp_path):
    body = json.loads(PAGE1.read_bytes())
    body['result']['hits'][0]['domains'][0]['alignment_display']['m'] = 254
    with Store(tmp_path) as store:
        _, client, _, result_owner = receiver(store, body=body)
        outcome = result_owner.act('api.hmmer.result')
        assert outcome['status'] == 'partial'
        assert set(domain_refs(outcome)) == {1, 2}
        assert numeric(store, domain_refs(outcome)[1])['paired_positions'] == 88
        assert any(e['code'] == 'provider_query_length_differs_from_submitted_subject'
                   and e['domain_array_index'] == 0 for e in outcome['result']['projection_errors'])
        source = store.get(outcome['result']['source_ref'])
        assert store.get_artifact(source['artifact_ref']) == client.snapshot(body).content


def test_conflicting_reference_lengths_are_not_arbitrarily_selected(tmp_path):
    body = json.loads(PAGE1.read_bytes())
    body['result']['hits'][0]['domains'][0]['alignment_display']['l'] = 284
    with Store(tmp_path) as store:
        _, _, _, result_owner = receiver(store, body=body)
        outcome = result_owner.act('api.hmmer.result')
        assert outcome['status'] == 'partial'
        assert store.get(outcome['result']['records'][0]['reference_ref'])['length'] is None
        assert set(domain_refs(outcome)) == {0, 1, 2}
        assert any(e['code'] == 'provider_reference_length_inconsistent_between_domains'
                   for e in outcome['result']['projection_errors'])


@pytest.mark.parametrize('algorithm', ['phmmer', 'hmmscan'])
def test_synthetic_axes_native_zero_negative_and_posterior_intervals(algorithm, tmp_path):
    with Store(tmp_path) as store:
        _, _, _, result_owner = receiver(store, body=synthetic_payload(algorithm), algorithm=algorithm,
            sequence='MACDEFGHIK' if algorithm == 'phmmer' else 'MACDEFGHIKLM')
        outcome = result_owner.act('api.hmmer.result')
        assert outcome['status'] == 'completed', outcome
        reference = store.get(outcome['result']['records'][0]['reference_ref'])
        observation = store.get(domain_refs(outcome)[0])
        values = numeric(store, observation['id'])
        assert observation['kind'] == ('comparison' if algorithm == 'phmmer' else 'profile_match')
        assert reference['reference_type'] == ('protein' if algorithm == 'phmmer' else 'family')
        assert reference['length'] == (12 if algorithm == 'phmmer' else None)
        assert values['query_coverage'] == (4/10 if algorithm == 'phmmer' else 4/12)
        assert (values['query_start'], values['query_end']) == ((0, 4) if algorithm == 'phmmer' else (1, 5))
        for name, value in {'model_length': 10, 'sequence_length': 12, 'paired_positions': 3,
            'insert_positions': 1, 'delete_positions': 1, 'alignment_columns': 5,
            'model_span_coverage': .4, 'sequence_span_coverage': 4/12, 'paired_model_coverage': .3,
            'native_domain_score_bits': -2.5, 'native_conditional_evalue': 0,
            'native_domain_bias_bits': 1., 'posterior_lower_mean': (0+.95+.85+.95)/4,
            'posterior_upper_mean': (.05+1+.95+1)/4}.items():
            assert values[name] == pytest.approx(value)
        assert 'identity_fraction' not in values and 'sequence_identity_fraction' not in values


@pytest.mark.parametrize('missing', [True, False])
def test_missing_or_invalid_measurements_never_become_zero(missing, tmp_path):
    body = synthetic_payload()
    domain = body['result']['hits'][0]['domains'][0]
    for key in ('bitscore', 'ievalue', 'dombias'):
        if missing:
            domain.pop(key)
        else:
            domain[key] = 'not a measurement'
    domain['alignment_display'].pop('ppline')
    with Store(tmp_path) as store:
        _, _, _, result_owner = receiver(store, body=body, sequence='MACDEFGHIK')
        outcome = result_owner.act('api.hmmer.result')
        grading = grading_for(store, outcome)
        scored, = grading['scores']['domains']
        assert scored['native_domain_score_bits'] is None
        assert scored['native_independent_evalue'] is None
        assert scored['native_domain_bias_bits'] is None
        assert scored['posterior_lower_mean'] is None
        assert scored['native_conditional_evalue'] == 0
        # An invalid legacy native scalar may reject this domain projection;
        # it must never replace invalid/missing native measurements with zero.
        for reference in domain_refs(outcome).values():
            values = numeric(store, reference)
            assert not {'native_domain_score_bits', 'native_independent_evalue',
                        'native_domain_bias_bits', 'posterior_lower_mean'} & values.keys()
            assert 'bitscore' not in values and 'evalue' not in values
            assert values['native_conditional_evalue'] == 0


def test_exact_artifact_and_original_array_join_reject_wrong_or_ambiguous_match(tmp_path):
    with Store(tmp_path) as store:
        _, _, _, result_owner = receiver(store)
        outcome = result_owner.act('api.hmmer.result')
        grading = grading_for(store, outcome)
        with pytest.raises(ValueError, match='hmmer_grading_domain_artifact_mismatch'):
            api_domain_scores(grading, hit_array_index=0, domain_array_index=1, artifact_ref='other-page')
        assert api_domain_scores(grading, hit_array_index=0, domain_array_index=99) == {}
        assert api_domain_scores(grading, hit_array_index=0, domain_array_index=None) == {}
        damaged = deepcopy(grading)
        damaged['scores']['domains'].append(deepcopy(damaged['scores']['domains'][1]))
        with pytest.raises(ValueError, match='hmmer_grading_domain_locator_ambiguous'):
            api_domain_scores(damaged, hit_array_index=0, domain_array_index=1)


def test_publication_rejects_wrong_native_page_scores_and_preserves_valid_siblings(tmp_path, monkeypatch):
    with Store(tmp_path) as store:
        tools, _, _, result_owner = receiver(store)
        original = tools._hmmer_grading
        def wrong_page(snapshot):
            grading = original(snapshot)
            grading['scores']['domains'][1]['locator']['artifact_ref'] = 'synthetic-wrong-page'
            return grading
        monkeypatch.setattr(tools, '_hmmer_grading', wrong_page)
        outcome = result_owner.act('api.hmmer.result')
        assert outcome['status'] == 'partial'
        assert set(domain_refs(outcome)) == {0, 2}
        assert len(domain_refs(outcome, 1)) == 1
        assert any(e['code'] == 'hmmer_grading_domain_artifact_mismatch' and e['domain_array_index'] == 1
                   for e in outcome['result']['projection_errors'])


def test_missing_reference_length_preserves_native_domain_and_available_components(tmp_path):
    body = synthetic_payload()
    body['result']['hits'][0]['domains'][0]['alignment_display']['l'] = None
    with Store(tmp_path) as store:
        _, _, _, result_owner = receiver(store, body=body, sequence='MACDEFGHIK')
        outcome = result_owner.act('api.hmmer.result')
        assert set(domain_refs(outcome)) == {0}
        values = numeric(store, domain_refs(outcome)[0])
        assert values['native_domain_score_bits'] == values['bitscore'] == -2.5
        assert values['paired_positions'] == 3 and values['sequence_span_residues'] == 4
        assert not {'sequence_length', 'sequence_span_coverage', 'paired_sequence_coverage',
                    'target_coverage'} & values.keys()


def test_second_page_provider_index_is_not_array_index_or_population_completion(tmp_path):
    with Store(tmp_path) as store:
        _, _, _, result_owner = receiver(store, body=PAGE2.read_bytes(), page=2)
        outcome = result_owner.act('api.hmmer.result')
        assert outcome['status'] == 'completed' and outcome['result']['next_page'] is None
        row, = outcome['result']['records']
        assert row['native_array_index'] == 0 and row['native_index'] == 2
        assert numeric(store, domain_refs(outcome)[0])['alignment_columns'] == 73
        grading = grading_for(store, outcome)
        assert grading['sheet']['inputs']['acquisition']['hit_population_complete'] is False
        assert grading['sheet']['inputs']['acquisition']['page_start'] == 2
        assert result_owner.api.facts(result_owner.context, {})['execution_completed'] is True


def test_empty_synthetic_hmmscan_is_completed_page_with_no_observed_matches(tmp_path):
    body = {'status': 'SUCCESS', 'page_count': 1,
        'result': {'stats': {'algo': 'hmmscan', 'nreported': 0}, 'hits': []}}
    with Store(tmp_path) as store:
        _, _, _, result_owner = receiver(store, body=body, algorithm='hmmscan')
        outcome = result_owner.act('api.hmmer.result')
        assert outcome['status'] == 'completed' and not outcome['result']['records']
        assert not store.list('observation')
        grading = grading_for(store, outcome)
        assert grading['sheet']['hits'] == [] and grading['scores']['domains'] == []
        assert grading['sheet']['inputs']['acquisition']['hit_population_complete'] is True


@pytest.mark.parametrize('body', [b'not-json', b'\xff', b'{"status":"SUCCESS","result":'])
def test_malformed_native_bytes_retained_before_parse_and_replay_never_fetches(body, tmp_path):
    with Store(tmp_path) as store:
        _, client, _, result_owner = receiver(store, body=body)
        outcome = result_owner.act('api.hmmer.result')
        assert outcome['status'] == 'failed' and not outcome['record_refs']
        saved = store.db.execute("SELECT snapshot FROM api_execution_actions WHERE name='api.hmmer.result'").fetchone()[0]
        assert result_owner.api._load_snapshot(saved).content == body
        assert result_owner.act('api.hmmer.result', index=0) == outcome
        assert [x[0] for x in client.calls].count('result') == 1


def test_injected_grading_failure_preserves_native_and_valid_existing_rows(tmp_path, monkeypatch):
    with Store(tmp_path) as store:
        tools, _, _, result_owner = receiver(store)
        def rejected(snapshot):
            raise ValueError('synthetic_grading_rejection')
        monkeypatch.setattr(tools, '_hmmer_grading', rejected)
        outcome = result_owner.act('api.hmmer.result')
        source = store.get(outcome['result']['source_ref'])
        assert store.get_artifact(source['artifact_ref']) == PAGE1.read_bytes()
        assert grading_for(store, outcome) == {'sheet': None, 'scores': None,
            'failure': {'code': 'synthetic_grading_rejection', 'category': 'grading_input'}}
        assert len(store.list('observation')) == 4
        assert numeric(store, domain_refs(outcome)[1])['bitscore'] == 16.722900390625
        assert 'consensus_identity_fraction' not in numeric(store, domain_refs(outcome)[1])


def test_saved_sheet_recalculation_after_store_reopen_needs_no_network_or_analysis(tmp_path, monkeypatch):
    with Store(tmp_path) as store:
        _, _, _, result_owner = receiver(store)
        outcome = result_owner.act('api.hmmer.result')
        source_ref = outcome['result']['source_ref']
    def prohibited(*args, **kwargs):
        raise AssertionError('offline recalculation attempted network or native execution')
    monkeypatch.setattr(socket, 'socket', prohibited)
    monkeypatch.setattr(subprocess, 'Popen', prohibited)
    with Store(tmp_path) as reopened:
        saved, = source_tool_gradings(reopened, source_ref)
        sheet = json.loads(json.dumps(saved['sheet']))
        before = deepcopy(sheet)
        monkeypatch.setattr('builtins.open', prohibited)
        assert calculate_hmmer_search_scores(sheet) == saved['scores']
        assert calculate_hmmer_search_scores(sheet, parameters={}) == saved['scores']
        assert sheet == before


def test_source_grading_helper_cannot_resolve_non_source_or_substitute_native_custody(tmp_path):
    with Store(tmp_path) as store:
        _, _, _, result_owner = receiver(store)
        outcome = result_owner.act('api.hmmer.result')
        source = store.get(outcome['result']['source_ref'])
        with pytest.raises(ContractError, match='tool_grading_source_required'):
            source_tool_gradings(store, source['artifact_ref'])
        other = store.artifact(b'other native page', 'application/json')
        original = store.get
        def wrong_source(reference):
            value = original(reference)
            return {**value, 'artifact_ref': other} if reference == source['id'] else value
        # Fault-inject a wrong source record without rewriting immutable evidence.
        store.get = wrong_source
        with pytest.raises(ContractError, match='tool_grading_source_custody_mismatch'):
            source_tool_gradings(store, source['id'])
