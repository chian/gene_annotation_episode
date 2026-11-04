"""Retained native observations; synthetic corruptions are labelled explicitly."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_proteome_directional import parse_genome_comparison_directional_report
from gene_annotation_episode.bvbrc_proteome_directional_sheet import build_directional_sheet
from gene_annotation_episode.bvbrc_proteome_directional_numerical_contracts import (
    DirectionalNumericalContractError, validate_directional_numerical,
)

FIXTURES = Path(__file__).parent / 'fixtures' / 'bvbrc_proteome_directional'
FILES = {
    '2011': ('biopython_text_2011L_blastp_002.txt','c122ef42cd2d2da7ae5318045aa88a73c84713572a2c14d15c562117f3eec62d'),
    '2202': ('biopython_text_2202L_blastp_001.txt','c0f5e5d3541500aef1ac93957fe35fbd4481f5788314e3e12ed1ea5f9d16510a'),
    '2221': ('biopython_text_2221L_blastp_001.txt','e8bcff01bf827d936c36f00e4bbb73f2b5b1dd99b4d37af4cb9a6b0de44e25f8'),
}
PARAMETERS = {'version':'bvbrc_proteome_directional_parameters_v1',
    'formula_version':'displayed_blastp_correspondence_v1', 'amino_acid_alphabet':'standard20',
    'ratio_decimal_places':18, 'rounding':'half_even'}


def native_bytes(name):
    filename, digest = FILES[name]
    data = (FIXTURES / filename).read_bytes()
    assert hashlib.sha256(data).hexdigest() == digest
    return data


def parse_bytes(data, *, name='synthetic', body_complete=True, object_complete='yes'):
    source = {'content':{'source_ref':name,'artifact_field':'stdout_ref',
        'artifact_ref':name + '-retained', 'sha256':hashlib.sha256(data).hexdigest(), 'byte_count':len(data)},
        'body_complete':body_complete,'object_complete':object_complete}
    return parse_genome_comparison_directional_report(data, source=source,
        declared_format='ncbi_blastall_blastp_pairwise_text_v1', report_key=name)


def native_sheet(name='2221'):
    return build_directional_sheet([parse_bytes(native_bytes(name),name=name)])['sheet']


def synthetic_sheet(*, hsps=None, query_length=10, subject_length=10, suffix='', nohit=False):
    header = 'BLASTP 2.2.2\nQuery= repeated-q\n'
    if query_length is not None: header += f' ({query_length} letters)\n'
    if nohit:
        data = header + ' ***** No hits found ******\n'
    else:
        data = header + '> repeated-s\n'
        if subject_length is not None: data += f' Length = {subject_length}\n'
        for h in (hsps if hsps is not None else [dict(q='ACDE',s='ACDE',qs=1,qe=4,ss=1,se=4,i=4,d=4)]):
            data += f" Score = {h.get('bits','20')} bits ({h.get('raw','40')}), Expect = {h.get('expect','e-30')}\n"
            data += f" Identities = {h.get('i',4)}/{h.get('d',4)} (100%)"
            if 'p' in h: data += f", Positives = {h['p']}/{h.get('pd',h.get('d',4))} (100%)"
            if 'g' in h: data += f", Gaps = {h['g']}/{h.get('gd',h.get('d',4))} (0%)"
            data += '\n'
            blocks = h.get('blocks', [h])
            for b in blocks:
                if b.get('q') is not None: data += f"Query: {b.get('qs',1)} {b['q']} {b.get('qe',4)}\n"
                if b.get('s') is not None: data += f"Sbjct: {b.get('ss',1)} {b['s']} {b.get('se',4)}\n"
    data += suffix + 'S2: 40 (20 bits)\n'
    return build_directional_sheet([parse_bytes(data.encode(),name='synthetic')])['sheet']


@pytest.mark.parametrize('name,population', [('2011',(1,0,0,0)),('2202',(2,23,25,42)),('2221',(3,3,4,23))])
def test_original_native_complete_occurrences_and_numeric_cells(name,population):
    result = build_directional_sheet([parse_bytes(native_bytes(name),name=name)])
    assert result['state'] == 'available'
    sheet = result['sheet']
    raw = sheet['reader_results'][0]
    queries = sheet['reports'][0]['query_rows']
    subjects = [s for q in queries for s in q['subjects']]
    hsps = [h for s in subjects for h in s['hsps']]
    blocks = [b for h in hsps for b in h['traceback_blocks']]
    assert (len(queries),len(subjects),len(hsps),len(blocks)) == population
    assert len(blocks) == sum(line.startswith(b'Query:') for line in native_bytes(name).splitlines())
    for qi,q in enumerate(queries):
        assert q['reported_length'] == raw['queries'][qi]['length']
        assert q['descriptions'] == raw['queries'][qi]['descriptions']
        assert q['statistics'] == raw['queries'][qi]['statistics']
        for si,s in enumerate(q['subjects']):
            assert s['reported_length'] == raw['queries'][qi]['subjects'][si]['length']
            for hi,h in enumerate(s['hsps']):
                assert h['key'] == dict(report_ordinal=0,query_ordinal=qi,subject_ordinal=si,hsp_ordinal=hi)
                source = raw['queries'][qi]['subjects'][si]['hsps'][hi]
                assert all(v == source[k] for k,v in h.items() if k != 'key')


def test_original_native_missing_gap_and_lexical_scores_are_not_rewritten():
    sheet = native_sheet()
    q = sheet['reports'][0]['query_rows'][1]
    a,b = q['subjects'][0]['hsps']
    assert (a['identity_count']['value'],a['identity_denominator']['value']) == (353,414)
    assert (b['identity_count']['value'],b['identity_denominator']['value']) == (115,115)
    assert a['gap_count'] == dict(state='missing',value=None,native_text=None,locations=[])
    assert a['expect']['native_text'] == '0.0'
    assert b['expect']['native_text'] == '2e-66'
    assert sheet['reports'][0]['query_rows'][0]['descriptions'][1]['evalue']['native_text'] == 'e-179'
    assert len(sheet['reports'][0]['query_rows'][0]['subjects']) == 1
    assert len(sheet['reports'][0]['query_rows'][0]['descriptions']) == 10


def test_original_native_nohit_is_distinct_from_empty_input():
    result = build_directional_sheet([])
    assert result['state'] == 'partial'
    assert result['sheet']['reader_results'] == result['sheet']['reports'] == []
    assert [i['code'] for i in result['diagnostics']] == ['no_report_supplied']
    sheet = native_sheet('2011')
    q = sheet['reports'][0]['query_rows'][0]
    assert q['reported_length']['value'] == 102
    assert q['no_hits_marker']['state'] == 'present'
    assert q['subjects'] == []


def test_synthetic_equal_reports_remain_separate_occurrences():
    raw = parse_bytes(native_bytes('2221'),name='same-key')
    result = build_directional_sheet([raw,raw])
    assert result['state'] == 'available'
    sheet = result['sheet']
    assert len(sheet['reader_results']) == len(sheet['reports']) == 2
    assert sheet['reports'][1]['query_rows'][1]['subjects'][0]['hsps'][1]['key']['report_ordinal'] == 1
    assert sheet['reader_results'][0] == sheet['reader_results'][1]
    assert sheet['reader_results'][0] is not sheet['reader_results'][1]


@pytest.mark.parametrize('flags,code', [({'body_complete':False},'source_body_incomplete'),({'object_complete':'no'},'source_object_incomplete'),({'object_complete':'unknown'},'source_object_completeness_unknown')])
def test_native_incomplete_custody_does_not_drop_observed_rows(flags,code):
    result = build_directional_sheet([parse_bytes(native_bytes('2221'),**flags)])
    assert result['state'] == 'partial'
    assert code in {i['code'] for i in result['diagnostics']}
    assert len(result['sheet']['reports'][0]['query_rows']) == 3


def test_synthetic_later_partial_and_failure_reports_keep_valid_neighbors():
    original = native_bytes('2221')
    cut = original.index(b'Sbjct: 546') + len(b'Sbjct: 546 CSVCITEY')
    partial = parse_bytes(original[:cut],name='truncated')
    failed = parse_bytes(b'unsupported bytes',name='failed')
    result = build_directional_sheet([parse_bytes(original,name='complete'),partial,failed])
    assert result['state'] == 'partial'
    assert result['sheet']['reader_results'][2] == failed
    assert [len(r['query_rows']) for r in result['sheet']['reports']] == [3,2,0]
    assert result['sheet']['reports'][1]['query_rows'][1]['subjects'][0]['hsps'][1]['identity_count']['value'] == 115


@pytest.mark.parametrize('mutator', [
    lambda r:r['source']['content'].update(sha256='0'*64),
    lambda r:r['queries'][1]['subjects'][0]['hsps'][0]['identity_count'].update(value=354),
    lambda r:r['queries'][0].update(ordinal=True),
    lambda r:r.update(extra='not closed'),
])
def test_synthetic_reader_corruption_rejects_without_mutating_input(mutator):
    raw = parse_bytes(native_bytes('2221'))
    mutator(raw)
    original = deepcopy(raw)
    result = build_directional_sheet([raw])
    assert result['state'] == 'failure' and result['sheet'] is None
    assert result['diagnostics'][0]['argument_pointer'].startswith('/directional_results/0')
    assert result['diagnostics'][0]['fields'] == []
    assert raw == original


@pytest.mark.parametrize('argument', [None,{},'path-to-file',True])
def test_invalid_top_arguments_have_structured_failure(argument):
    result = build_directional_sheet(argument)
    assert result['diagnostics'][0]['argument_pointer'] == '/directional_results'
    assert validate_directional_numerical('DirectionalSheetResult',result) == result


def test_sheet_copy_and_validation_do_no_io(monkeypatch):
    raw = parse_bytes(native_bytes('2221'))
    original = deepcopy(raw)
    def forbidden(*args,**kwargs): raise AssertionError('unexpected I/O')
    monkeypatch.setattr('builtins.open',forbidden)
    monkeypatch.setattr(Path,'open',forbidden)
    monkeypatch.setattr('socket.socket',forbidden)
    monkeypatch.setattr('subprocess.Popen',forbidden)
    result = build_directional_sheet([raw])
    assert result['state'] == 'available'
    saved = json.loads(json.dumps(result))
    assert validate_directional_numerical('DirectionalSheetResult',saved) == result
    result['sheet']['reports'][0]['query_rows'][0]['reported_length']['value'] = 999
    assert raw == original


@pytest.mark.parametrize('mutator', [
    lambda s:s['reports'][0]['query_rows'][0].update(reported_length=deepcopy(s['reports'][0]['query_rows'][1]['reported_length'])),
    lambda s:s['reports'][0]['query_rows'][1]['subjects'][0]['hsps'].reverse(),
    lambda s:s['reports'][0]['query_rows'].pop(),
    lambda s:s['reports'][0]['query_rows'][1]['subjects'][0]['hsps'][0]['key'].update(hsp_ordinal=1),
    lambda s:s['reports'][0].update(report_key='changed'),
])
def test_synthetic_copied_observation_tampering_is_rejected(mutator):
    sheet = native_sheet()
    mutator(sheet)
    with pytest.raises(DirectionalNumericalContractError): validate_directional_numerical('DirectionalSheet',sheet)
