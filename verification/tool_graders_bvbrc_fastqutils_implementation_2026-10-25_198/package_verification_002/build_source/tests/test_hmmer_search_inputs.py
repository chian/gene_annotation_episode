"""Native-output parser and metadata extractor checks; no scientific execution."""
from copy import deepcopy
import io
import json
from pathlib import Path

import pytest

from gene_annotation_episode.hmmer_search_inputs import (
    parse_hmmer_api_result, parse_hmmer_search_artifacts, build_hmmer_search_sheet,
    iter_hmmer_table_rows, iter_hmmer_stdout_queries, iter_hmmer_stdout_events,
)

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'verification/tool_graders_hmmer_search_2026-10-24/native'
CAPTURES = ROOT / 'verification/hmmer_reported_timing_actual_service_2026-10-22_001/workspace/public-search-http-captures'
PAGE1 = CAPTURES / '26bc8bd463741aea924eabd181e41bfc91237dc04a04c7a3f5d03f6f64bd1e39/response.entity'
PAGE2 = CAPTURES / '4e88be472b0304cdea6ed5c38126eef0d7865b5345ad21863e9c9e318afc1c67/response.entity'


def native(program):
    artifacts = {role: (NATIVE / f'{program}.{role}').read_text() for role in ('stdout', 'tblout', 'domtblout')}
    return parse_hmmer_search_artifacts(program=program, artifacts=artifacts,
        artifact_refs={r: program + '.' + r for r in artifacts}, engine_version='3.4')


def synthetic_api(algorithm='phmmer'):
    display = {'model': 'AC.DE', 'aseq': 'ACG-E', 'mline': 'AC  E', 'ppline': '0*9.*',
               'hmmfrom': 1, 'hmmto': 4, 'sqfrom': 2, 'sqto': 5, 'm': 10, 'l': 12,
               'n': 5, 'hmmname': 'q' if algorithm == 'phmmer' else 'model',
               'sqname': 'target' if algorithm == 'phmmer' else 'q', 'identity': [3/4, 3]}
    return {'status': 'SUCCESS', 'page_count': 1, 'result': {'stats': {'algo': algorithm, 'nreported': 1}, 'hits': [
        {'name': 'target' if algorithm == 'phmmer' else 'model', 'score': 8.0, 'bias': .2,
         'evalue': 0.0, 'is_reported': True, 'is_included': False, 'ndom': 2, 'nreported': 1, 'nincluded': 0,
         'domains': [{'ienv': 1, 'jenv': 7, 'bitscore': -2.5, 'dombias': .6931471805599453,
                      'cevalue': 0., 'ievalue': 3., 'is_reported': True, 'is_included': False,
                      'alignment_display': display}]}]}}


def test_retained_native_phmmer_complete_population_and_locators():
    p = ROOT / 'cases/gene_001/jobs/homology_001'
    arts = {r:(p / f).read_text() for r, f in [('stdout','homology_search.stdout'),('tblout','hits.tbl'),('domtblout','domains.tbl')]}
    parsed = parse_hmmer_search_artifacts(program='phmmer', artifacts=arts, artifact_refs={r:r for r in arts}, engine_version='3.4')
    assert len(parsed['hits']) == 17
    assert len(parsed['domains']) == 20
    assert parsed['completion']['output_complete'] is True
    assert all(d.get('alignment') for d in parsed['domains'])
    d = parsed['domains'][0]
    assert d['native']['reported_domain_ordinal'] == 1
    start, end = d['locator']['byte_span']
    assert arts['domtblout'].encode()[start:end].decode() == d['raw_line']
    assert sum(h['is_included'] is True for h in parsed['hits']) == 4
    assert any(d['native']['domain_score_bits'] < 0 for d in parsed['domains'])


@pytest.mark.parametrize('program,queries,domains', [('hmmsearch',1,4),('hmmscan',4,4),('jackhmmer',1,8)])
def test_actual_bounded_native_fixtures(program, queries, domains):
    parsed = native(program)
    assert len(parsed['queries']) == queries
    assert len(parsed['domains']) == domains
    assert not parsed['issues']
    assert all(not d['issues'] for d in parsed['domains'])
    sheet = build_hmmer_search_sheet(parsed, inputs={})
    assert all(d['quantities']['valid'] for d in sheet['domains'])


def test_jackhmmer_dependent_rounds_and_checkpoint_roles():
    parsed = native('jackhmmer')
    assert [r['iteration'] for r in parsed['iterations']] == [1, 2]
    assert [r['native_new_targets'] for r in parsed['iterations']] == [4, 0]
    assert [r['native_converged'] for r in parsed['iterations']] == [False, True]
    assert {r['iteration'] for r in parsed['domains'] if r['locator']['artifact_role'] == 'domtblout'} == {2}
    cp = [dict(role=role, text=(NATIVE / filename).read_text(), artifact_ref=filename, iteration=iteration)
          for role, filename, iteration in [('chkhmm','round-model-1.hmm',1),('chkali','round-included-1.sto',1)]]
    # Native checkpoint file append mode permits more than one query record.
    cp[0]['text'] *= 2
    out = parse_hmmer_search_artifacts(program='jackhmmer',artifacts={},artifact_refs={},engine_version='3.4',checkpoints=cp)
    assert [x['locator']['record_occurrence'] for x in out['checkpoints']] == [0,1,0]
    assert [x['checkpoint_role'] for x in out['checkpoints']] == ['model_at_round_start','model_at_round_start','included_alignment_at_round_end']
    assert out['checkpoints'][0]['model_length'] == 20
    assert out['checkpoints'][2]['native_sequence_rows']


def test_original_api_indices_metadata_and_page_population():
    payload = json.loads(PAGE1.read_text())
    payload['result']['hits'][0]['domains'].insert(1, 'damaged row')
    out = parse_hmmer_api_result(payload,algorithm='phmmer',artifact_ref='page1')
    d = out['domains'][1]
    assert d['locator']['domain_array_index'] == 2
    assert d['locator']['json_pointer'] == '/result/hits/0/domains/2'
    assert out['hits'][0]['identifiers']['metadata']['accession'] == '6lpm_A'
    assert out['hits'][0]['identifiers']['metadata']['uniprot_accession'] == 'Q9RXF9'
    assert out['completion']['page_count'] == 2
    assert out['completion']['hit_population_complete'] is None
    sheet = build_hmmer_search_sheet(out,inputs={'acquisition':{'output_complete':True,'hit_population_complete':True}})
    assert 'hmmer_hit_population_incomplete' in {i['code'] for i in sheet['issues']}
    second = parse_hmmer_api_result(json.loads(PAGE2.read_text()), algorithm='phmmer', artifact_ref='page2')
    assert second['hits'][0]['locator']['hit_array_index'] == 0
    assert second['hits'][0]['native_record']['index'] == 2


def test_empty_api_success_differs_from_missing_result():
    complete = parse_hmmer_api_result({'status':'SUCCESS','result':{'stats':{'algo':'hmmscan','nreported':0},'hits':[]}},algorithm='hmmscan',artifact_ref='synthetic-empty')
    missing = parse_hmmer_api_result({'status':'SUCCESS'},algorithm='hmmscan',artifact_ref='synthetic-missing')
    assert complete['hits'] == [] and complete['issues'] == []
    assert missing['issues'][0]['code'] == 'hmmer_api_result_hits_missing_or_invalid'
    assert complete['completion']['hit_population_complete'] is None


def test_table_partial_component_invalid_row_and_utf8_locators():
    text = '# description α\n' + (NATIVE / 'hmmsearch.domtblout').read_text()
    first = next(line for line in text.splitlines() if line and not line.startswith('#'))
    fields = first.split()
    fields[13] = 'bogus-score'
    damaged = ' '.join(fields) + '\n'
    events = list(iter_hmmer_table_rows(io.BytesIO((text + damaged + 'truncated\n').encode()),program='hmmsearch',role='domtblout',artifact_ref='d'))
    domains = [e['data'] for e in events if e['kind'] == 'domain']
    assert len(domains) == 5
    assert domains[-1]['native']['domain_score_bits'] is None
    assert domains[-1]['native']['hmm_from'] == 1
    assert any(e['kind']=='issue' and e['data']['code']=='hmmer_truncated_table_row' for e in events)
    assert domains[0]['locator']['byte_span'][0] > domains[0]['locator']['line_number']


def test_ambiguous_duplicate_native_query_names_are_not_arbitrarily_joined():
    text = (NATIVE / 'hmmsearch.stdout').read_text()
    arts = {'stdout':text + text, 'domtblout':(NATIVE/'hmmsearch.domtblout').read_text()}
    parsed = parse_hmmer_search_artifacts(program='hmmsearch',artifacts=arts,artifact_refs={k:k for k in arts},engine_version='3.4')
    assert [q['occurrence'] for q in parsed['queries']] == [0,1]
    table = [d for d in parsed['domains'] if d['locator']['artifact_role']=='domtblout']
    assert all('alignment' not in d for d in table)
    assert all(any(i['code']=='hmmer_table_stdout_association_ambiguous' for i in d['issues']) for d in table)


def test_metadata_length_wrong_reference_and_ambiguous_target():
    parsed = parse_hmmer_api_result(synthetic_api(),algorithm='phmmer',artifact_ref='s')
    target = {'name':'target','kind':'protein_sequence','sequence':'AACGEAAAAAAA','length':12}
    inputs = {'query':{'name':'q','kind':'protein_sequence','sequence':'ACDEAAAAAA','length':10},'targets':[target,target]}
    sheet = build_hmmer_search_sheet(parsed,inputs=inputs)
    assert sheet['domains'][0]['joins']['target'] is None
    assert any(i['code']=='hmmer_metadata_join_ambiguous' for i in sheet['domains'][0]['issues'])
    inputs['targets']=[dict(target,length=11)]
    sheet = build_hmmer_search_sheet(parsed,inputs=inputs)
    assert any(i['code']=='hmmer_metadata_sequence_length_mismatch' for i in sheet['domains'][0]['issues'])
    inputs['targets']=[dict(target,name='other')]
    assert build_hmmer_search_sheet(parsed,inputs=inputs)['domains'][0]['joins']['target'] is None


def test_truncation_coordinate_and_label_issues_preserve_native_measurements():
    payload = synthetic_api()
    ad = payload['result']['hits'][0]['domains'][0]['alignment_display']
    ad['hmmto'] = 15
    ad['sqname'] = 'wrong-target'
    sheet = build_hmmer_search_sheet(parse_hmmer_api_result(payload,algorithm='phmmer',artifact_ref='s'),inputs={})
    d = sheet['domains'][0]
    assert d['intervals']['model'] is None
    assert not d['quantities']['valid']
    assert d['native']['domain_score_bits'] == -2.5
    text = (NATIVE/'hmmsearch.stdout').read_text().split('\n//')[0]
    parsed = parse_hmmer_search_artifacts(program='hmmsearch',artifacts={'stdout':text},artifact_refs={'stdout':'s'},engine_version='3.4')
    assert parsed['completion']['output_complete'] is False
    assert len(parsed['domains']) == 4


@pytest.mark.parametrize('bad',[None,[],7,'{}'])
def test_invalid_api_top_level(bad):
    with pytest.raises(ValueError,match='hmmer_api_payload_must_be_object'):
        parse_hmmer_api_result(bad,algorithm='phmmer',artifact_ref='x')


def test_nonfinite_rejected_and_inputs_unmutated():
    p = synthetic_api(); original = deepcopy(p)
    n = parse_hmmer_api_result(p,algorithm='phmmer',artifact_ref='x')
    saved = deepcopy(n); inputs = {'database':{'name':'explicit','population':100}}
    build_hmmer_search_sheet(n,inputs=inputs)
    assert n == saved and p == original
    p['unknown_native_metadata'] = float('nan')
    with pytest.raises(ValueError,match='hmmer_nonfinite'):
        parse_hmmer_api_result(p,algorithm='phmmer',artifact_ref='x')


@pytest.mark.parametrize('program',['phmmer','hmmsearch','hmmscan','jackhmmer'])
def test_stream_events_preserve_domain_locators_and_bounded_consumption(program):
    if program=='phmmer':
        text = (ROOT/'cases/gene_001/jobs/homology_001/homology_search.stdout').read_text()
    else: text = (NATIVE/f'{program}.stdout').read_text()
    source = io.StringIO(text)
    events = iter_hmmer_stdout_events(source,program=program,artifact_ref='stream')
    first = next(e for e in events if e['kind']=='hit')
    assert first['data']['locator']['line_number'] > 0
    assert source.tell() < len(text) / 2
    rest = list(events)
    domains = [e['data'] for e in rest if e['kind']=='domain']
    bundles = list(iter_hmmer_stdout_queries(io.StringIO(text),program=program,artifact_ref='stream'))
    assert [(d['record_key'],d['native'],d.get('alignment')) for d in domains] == [
        (d['record_key'],{k:v for k,v in d['native'].items() if not k.startswith('sequence_') or k=='sequence_length'},d.get('alignment'))
        for b in bundles for d in b['domains']]
    assert all('hit_record_key' not in d for d in domains)
    assert any(e['kind']=='annotation' and e['data'].get('native_output_terminated') for e in rest)


def test_native_search_population_is_extracted_from_statistics_not_returned_hits():
    parsed = native('hmmsearch')
    facts = {k:v for s in parsed['statistics'] for k,v in s['native'].items()}
    assert facts['target_sequence_count'] == 4
    assert facts['target_residues_searched'] == 99
    assert facts['Z'] == 4 and facts['domZ'] == 4


def test_inconsistent_domain_ordinal_is_explicit_and_saved_measurements_remain():
    first = next(x for x in (NATIVE/'hmmsearch.domtblout').read_text().splitlines() if x and not x.startswith('#'))
    parts = first.split(); parts[9] = '2'; parts[10] = '1'
    row = next(iter_hmmer_table_rows(io.StringIO(' '.join(parts)),program='hmmsearch',role='domtblout',artifact_ref='d'))['data']
    assert row['native']['domain_score_bits'] == 72.1
    assert any(i['code']=='hmmer_reported_domain_ordinal_count_inconsistent' for i in row['issues'])


def test_invalid_api_identity_and_checkpoint_role_are_scoped_issues():
    p=synthetic_api();p['result']['hits'][0]['name']=['bad identity']
    n=parse_hmmer_api_result(p,algorithm='phmmer',artifact_ref='s')
    s=build_hmmer_search_sheet(n,inputs={})
    assert s['hits'][0]['target_name'] is None
    assert any(i['code']=='hmmer_identity_must_be_string_or_null' for i in s['hits'][0]['issues'])
    n=parse_hmmer_search_artifacts(program='jackhmmer',artifacts={},artifact_refs={},engine_version='3.4',checkpoints=[{'role':[],'text':'x'}])
    assert n['issues'][0]['code']=='hmmer_unknown_checkpoint_role'


def test_invalid_native_rows_keep_valid_siblings_and_numeric_fields():
    n=native('hmmsearch');n['domains'].insert(1,'bad row')
    n['domains'][0]['native']['accuracy']=['bad number']
    s=build_hmmer_search_sheet(n,inputs={})
    assert len(s['domains'])==4
    assert s['domains'][0]['native']['accuracy'] is None
    assert s['domains'][0]['native']['domain_score_bits']==72.1
    assert any(i['code']=='hmmer_native_row_identity_invalid' for i in s['issues'])
