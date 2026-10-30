"""Authentic saved Gene XML plus labelled engineering identity/framing cases."""
from copy import deepcopy
import builtins
import hashlib
import json
import os
from pathlib import Path
import socket
import urllib.request
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import pytest

from gene_annotation_episode.ncbi_gene_native import (
    NCBI_GENE_NATIVE_SCHEMA, read_ncbi_gene_xml, validate_ncbi_gene_native,
)

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / 'verification/tool_graders_hmmer_map_verification_2026-10-28_529/check201_native739/sequence-support-native739'
NATIVE_SHA = '06caac1d71d16e5cad9278bb81ff41cd7abc067681638cbaca3e050e025d82ca'


def engineering_record(ids=('17',), *, locus=True):
    id_xml = ''.join('<Gene-track_geneid>' + escape(value) + '</Gene-track_geneid>' for value in ids)
    return ('<Entrezgene origin="engineering737">\n'
        '<Entrezgene_track-info><Gene-track>' + id_xml + '</Gene-track></Entrezgene_track-info>'
        '<Entrezgene_gene><Gene-ref><Gene-ref_locus>ENGINEERING_SYMBOL</Gene-ref_locus>'
        '<Gene-ref_db><Dbtag><Dbtag_db>taxon</Dbtag_db><Dbtag_tag><Object-id>'
        '<Object-id_id>999999</Object-id_id></Object-id></Dbtag_tag></Dbtag></Gene-ref_db>'
        '</Gene-ref></Entrezgene_gene>'
        '<Entrezgene_source><BioSource><BioSource_org><Org-ref><Org-ref_db>'
        '<Dbtag><Dbtag_db>taxon</Dbtag_db><Dbtag_tag><Object-id><Object-id_id>123</Object-id_id>'
        '<Object-id_str>source-literal</Object-id_str></Object-id></Dbtag_tag></Dbtag>'
        '<Dbtag><Dbtag_db>other</Dbtag_db><Dbtag_tag><Object-id><Object-id_id>456</Object-id_id>'
        '</Object-id></Dbtag_tag></Dbtag></Org-ref_db></Org-ref></BioSource_org></BioSource></Entrezgene_source>'
        + ('''<Entrezgene_locus><Gene-commentary native="outer">
          <Gene-commentary_type value="genomic">1</Gene-commentary_type>
          <Gene-commentary_accession>ENGINEERING_ACC</Gene-commentary_accession>
          <Gene-commentary_version>7</Gene-commentary_version>
          <Gene-commentary_label> label with spaces </Gene-commentary_label>
          <Gene-commentary_heading></Gene-commentary_heading>
          <Gene-commentary_seqs><Seq-loc><Seq-loc_int><Seq-interval>
            <Seq-interval_from>0</Seq-interval_from><Seq-interval_to>8</Seq-interval_to>
            <Seq-interval_strand><Na-strand value="minus">2</Na-strand></Seq-interval_strand>
            <Seq-interval_id><Seq-id><Seq-id_other><Textseq-id>
              <Textseq-id_accession>ENGINEERING_ACC</Textseq-id_accession><Textseq-id_version>7</Textseq-id_version>
            </Textseq-id></Seq-id_other></Seq-id></Seq-interval_id>
          </Seq-interval></Seq-loc_int></Seq-loc></Gene-commentary_seqs>
          <Gene-commentary_products><Gene-commentary native="nested">
            <Gene-commentary_type value="mRNA">3</Gene-commentary_type>
            <Gene-commentary_accession>ENGINEERING_TRANSCRIPT</Gene-commentary_accession>
            <Gene-commentary_accession></Gene-commentary_accession>
            <Gene-commentary_version>4</Gene-commentary_version>
            <Gene-commentary_genomic-coords><Seq-loc><Seq-loc_whole><Seq-id>
              <Seq-id_local><Object-id><Object-id_str>local engineering</Object-id_str></Object-id></Seq-id_local>
            </Seq-id></Seq-loc_whole></Seq-loc></Gene-commentary_genomic-coords>
          </Gene-commentary> nested tail </Gene-commentary_products>
        </Gene-commentary></Entrezgene_locus>''' if locus else '')
        + '<Entrezgene_comments><Gene-commentary><Gene-commentary_accession>UNRELATED_COMMENT</Gene-commentary_accession>'
        '</Gene-commentary></Entrezgene_comments>\n</Entrezgene>')


def engineering_set(*records):
    return ('<Entrezgene-Set>' + ''.join(records) + '</Entrezgene-Set>').encode()


def read(content=None, *, ids=None, complete=True):
    return read_ncbi_gene_xml(engineering_set(engineering_record()) if content is None else content,
        source_ref='engineering737', requested_gene_ids=ids, response_complete=complete)


def resolve(tree, path):
    for index in path:
        tree = tree['children'][index]
    return tree


def semantic_tree(element):
    return {'tag': element.tag, 'attributes': dict(element.attrib), 'text': element.text,
            'tail': element.tail, 'children': [semantic_tree(child) for child in element]}


def issue_codes(result):
    return [issue['code'] for issue in result['issues']]


def test_actual_saved_gene2_all_loci_native_paths_and_custody():
    content = (CAPTURE / 'gene2.entity').read_bytes()
    metadata = json.loads((CAPTURE / 'gene2.json').read_text())
    assert len(content) == 2074977 and hashlib.sha256(content).hexdigest() == NATIVE_SHA
    assert metadata['status'] == 200 and metadata['body_complete'] is True
    assert metadata['sha256'] == NATIVE_SHA and metadata['attempts'] == 1
    result = read_ncbi_gene_xml(content, source_ref='saved201:gene2', requested_gene_ids=['2'], response_complete=True)
    assert result['parse_status'] == 'complete' and result['issues'] == []
    assert len(result['records']) == 1
    row = result['records'][0]
    assert row['record_ordinal'] == 0 and row['gene_id_values'] == ['2'] and row['gene_id'] == '2'
    assert row['taxon_ids'] == ['9606'] and row['gene_symbols'] == ['A2M']
    loci = row['loci']
    assert [locus['locus_ordinal'] for locus in loci] == [0, 1, 2]
    assert [locus['commentaries'][0]['accession_values'] for locus in loci] == [['NC_000012'], ['NG_011717'], ['NC_060936']]
    assert [locus['commentaries'][0]['version_values'] for locus in loci] == [['12'], ['2'], ['1']]
    assert [len(locus['commentaries']) for locus in loci] == [11, 3, 11]
    assert row['native_record'] == semantic_tree(ET.fromstring(content).find('Entrezgene'))
    for locus in loci:
        assert resolve(row['native_record'], locus['path'])['tag'] == 'Gene-commentary'
        for ordinal, commentary in enumerate(locus['commentaries']):
            assert commentary['commentary_ordinal'] == ordinal
            assert resolve(row['native_record'], commentary['path'])['tag'] == 'Gene-commentary'
            if ordinal == 0: assert commentary['parent_commentary_path'] is None
            else:
                assert commentary['parent_commentary_path'] in [c['path'] for c in locus['commentaries'][:ordinal]]
                assert commentary['path'][:len(commentary['parent_commentary_path'])] == commentary['parent_commentary_path']
            for location in commentary['locations']:
                assert resolve(row['native_record'], location['path']) == location['native']
                assert location['tag'] == location['native']['tag']
    assert validate_ncbi_gene_native(json.loads(json.dumps(result))) == result
    if 'HMMER529_ATTEMPT' in os.environ:
        directory = Path(os.environ['HMMER529_ATTEMPT']) / 'native-gene737'
        directory.mkdir(exist_ok=False)
        (directory / 'parsed.json').write_text(json.dumps(result, indent=2) + '\n')
        (directory / 'facts.json').write_text(json.dumps({'source_sha256': NATIVE_SHA,
            'source_bytes': len(content), 'source_capture_audit_clean': False,
            'source_capture_qualification': 'original201 unbound NSS mapping; no retrospective authorization',
            'record_count': len(result['records']), 'locus_count': len(loci),
            'locus_commentary_counts': [len(locus['commentaries']) for locus in loci],
            'new_network_requests': 0, 'episode_binding_verified': False}, indent=2) + '\n')


def test_engineering_recursion_native_text_tail_attributes_and_no_coordinate_conversion():
    result = read(ids=['17'])
    row = result['records'][0]
    assert row['native_record'] == semantic_tree(ET.fromstring(engineering_set(engineering_record())).find('Entrezgene'))
    assert row['taxon_ids'] == ['123', 'source-literal']
    comments = row['loci'][0]['commentaries']
    assert len(comments) == 2 and comments[0]['types'] == [{'code': '1', 'label': 'genomic'}]
    assert comments[0]['labels'] == [' label with spaces '] and comments[0]['headings'] == [None]
    assert comments[1]['accession_values'] == ['ENGINEERING_TRANSCRIPT', None]
    assert comments[1]['parent_commentary_path'] == comments[0]['path']
    assert resolve(row['native_record'], comments[1]['path'])['tail'] == ' nested tail '
    location = comments[0]['locations'][0]['native']
    text_values = []
    def gather(node):
        text_values.append((node['tag'], node['text']))
        for child in node['children']: gather(child)
    gather(location)
    assert ('Seq-interval_from', '0') in text_values and ('Seq-interval_to', '8') in text_values
    assert all('coordinate_system' not in item for item in comments)
    assert all(comment['accession_values'] != ['UNRELATED_COMMENT'] for comment in comments)


def test_multiple_records_preserve_native_order_instead_of_requested_order():
    result = read(engineering_set(engineering_record(('9',), locus=False), engineering_record(('17',))), ids=['17', '9'])
    assert [row['gene_id'] for row in result['records']] == ['9', '17']
    assert [row['record_ordinal'] for row in result['records']] == [0, 1]
    assert result['records'][0]['loci'] == [] and result['parse_status'] == 'complete'


@pytest.mark.parametrize('values,expected,code', [
    ((), [], 'gene_id_missing'), (('17', '17'), ['17', '17'], 'gene_id_ambiguous'),
    (('',), [None], 'gene_id_invalid'), (('not-decimal',), ['not-decimal'], 'gene_id_invalid'),
    (('１７',), ['１７'], 'gene_id_invalid'), ((' 17 ',), [' 17 '], 'gene_id_invalid'),
])
def test_missing_ambiguous_and_invalid_gene_ids_never_choose_first(values, expected, code):
    result = read(engineering_set(engineering_record(values)))
    assert result['parse_status'] == 'partial'
    assert result['records'][0]['gene_id'] is None
    assert result['records'][0]['gene_id_values'] == expected
    assert issue_codes(result) == [code]


def test_duplicate_requested_missing_and_unexpected_records_remain_separate():
    result = read(engineering_set(engineering_record(('17',)), engineering_record(('17',)), engineering_record(('9',))), ids=['17', '22'])
    assert [row['gene_id'] for row in result['records']] == ['17', '17', '9']
    assert result['issues'] == [
        {'code': 'gene_id_duplicate', 'record_ordinal': 0, 'path': None},
        {'code': 'gene_id_duplicate', 'record_ordinal': 1, 'path': None},
        {'code': 'unexpected_gene', 'record_ordinal': 2, 'path': None},
        {'code': 'requested_gene_missing', 'record_ordinal': None, 'path': None},
    ]


@pytest.mark.parametrize('content,status,code', [
    (b'', 'invalid', 'xml_parse_failed'), (b'not XML', 'invalid', 'xml_parse_failed'),
    (b'<wrong/>', 'invalid', 'xml_root_invalid'), (b'<Entrezgene-Set><unexpected/></Entrezgene-Set>', 'partial', 'source_identity_malformed'),
    (b'<Entrezgene-Set><Entrezgene>', 'invalid', 'xml_parse_failed'),
    (b'<?xml version="1.0" encoding="NO-SUCH-ENCODING"?><Entrezgene-Set/>', 'invalid', 'xml_parse_failed'),
])
def test_invalid_native_framing_does_not_become_empty_measured_records(content, status, code):
    result = read(content)
    assert result['parse_status'] == status and result['records'] == []
    assert code in issue_codes(result)


@pytest.mark.parametrize('complete,requested,status,codes', [
    (True, None, 'complete', []), (False, None, 'partial', ['response_incomplete']),
    (True, ['17'], 'partial', ['requested_gene_missing']),
])
def test_complete_empty_set_is_distinct_from_incomplete_and_missing_requested_record(complete, requested, status, codes):
    result = read(b'<Entrezgene-Set/>', complete=complete, ids=requested)
    assert result['records'] == [] and result['parse_status'] == status and issue_codes(result) == codes


@pytest.mark.parametrize('suffix', [b'<Entrezgene>', b'</Entrezgene-Set>trailing junk'])
def test_fully_closed_prior_record_survives_later_xml_failure(suffix):
    result = read(b'<Entrezgene-Set>' + engineering_record().encode() + suffix, ids=['17'])
    assert result['parse_status'] == 'partial' and issue_codes(result) == ['xml_parse_failed']
    assert result['records'][0]['gene_id'] == '17'
    assert len(result['records'][0]['loci']) == 1


def test_standalone_entrezgene_and_namespaced_gene_set_preserve_original_tags():
    standalone = read(engineering_record().encode())
    xml = engineering_set(engineering_record()).replace(b'<Entrezgene-Set>', b'<Entrezgene-Set xmlns="urn:engineering737">')
    namespaced = read(xml)
    assert standalone['parse_status'] == namespaced['parse_status'] == 'complete'
    assert namespaced['records'][0]['native_record']['tag'] == '{urn:engineering737}Entrezgene'
    assert namespaced['records'][0]['gene_id'] == standalone['records'][0]['gene_id'] == '17'


@pytest.mark.parametrize('content', [
    b'<!DOCTYPE Entrezgene-Set SYSTEM "https://must-not-fetch.invalid/schema.dtd"><Entrezgene-Set/>',
    b'<!DOCTYPE Entrezgene-Set [<!ENTITY ext SYSTEM "file:///must-not-read737">]><Entrezgene-Set>&ext;</Entrezgene-Set>',
])
def test_xml_external_resources_are_never_acquired(content, monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('reader attempted IO')
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(builtins, 'open', forbidden)
    result = read(content)
    assert result['parse_status'] in {'complete', 'invalid'}
    assert result['records'] == []


@pytest.mark.parametrize('field,value', [
    ('content', 'text'), ('content', bytearray()), ('source_ref', ''), ('source_ref', None),
    ('requested_gene_ids', []), ('requested_gene_ids', ['17', '17']), ('requested_gene_ids', [17]),
    ('requested_gene_ids', ['１７']), ('requested_gene_ids', '17'), ('requested_gene_ids', ['17\n']),
    ('response_complete', 1), ('response_complete', None),
])
def test_invalid_caller_operands_are_not_coerced(field, value):
    kwargs = {'content': engineering_set(engineering_record()), 'source_ref': 'engineering737',
        'requested_gene_ids': None, 'response_complete': True}
    kwargs[field] = value
    with pytest.raises(ValueError, match='ncbi_gene_'):
        read_ncbi_gene_xml(**kwargs)


@pytest.mark.parametrize('mode', ['extra_field', 'record_ordinal', 'float_ordinal', 'bool_ordinal',
    'locus_path', 'commentary_parent', 'location_path', 'location_tree', 'native_tag',
    'identity', 'taxon', 'status', 'response', 'issue_path', 'request_id'])
def test_saved_schema_paths_identities_and_status_relationships_reject_tampering(mode):
    result = read(ids=['17'])
    row = result['records'][0]
    if mode == 'extra_field': result['confidence'] = 1.0
    elif mode == 'record_ordinal': row['record_ordinal'] = 1
    elif mode == 'float_ordinal': row['record_ordinal'] = 0.0
    elif mode == 'bool_ordinal': row['record_ordinal'] = False
    elif mode == 'locus_path': row['loci'][0]['path'] = [0]
    elif mode == 'commentary_parent': row['loci'][0]['commentaries'][1]['parent_commentary_path'] = None
    elif mode == 'location_path': row['loci'][0]['commentaries'][0]['locations'][0]['path'] = []
    elif mode == 'location_tree': row['loci'][0]['commentaries'][0]['locations'][0]['native']['text'] = 'forged'
    elif mode == 'native_tag': row['native_record']['tag'] = 'wrong'
    elif mode == 'identity': row['gene_id'] = '18'
    elif mode == 'taxon': row['taxon_ids'] = ['999999']
    elif mode == 'status': result['parse_status'] = 'partial'
    elif mode == 'response': result['response_complete'] = False
    elif mode == 'issue_path': result['issues'] = [{'code': 'xml_parse_failed', 'record_ordinal': 0, 'path': [0]}]
    else: result['request']['gene_ids'] = ['１７']
    with pytest.raises(ValueError, match='ncbi_gene_'):
        validate_ncbi_gene_native(result)


def test_detached_outputs_and_exported_schema_are_not_authority_or_mutable_validator_state():
    requested = ['17']
    result = read(ids=requested)
    requested[0] = 'other'
    assert result['request']['gene_ids'] == ['17']
    original = deepcopy(result)
    validated = validate_ncbi_gene_native(result)
    validated['records'][0]['loci'][0]['commentaries'][0]['locations'][0]['native']['text'] = 'changed'
    assert result == original
    exported = deepcopy(NCBI_GENE_NATIVE_SCHEMA)
    assert exported['properties']['version']['const'] == 'ncbi_gene_native_v1'
    assert 'confidence' not in exported['properties']
    assert validate_ncbi_gene_native(json.loads(json.dumps(original))) == original


@pytest.mark.parametrize('mode', ['nan', 'tuple', 'nonstring_key', 'cycle'])
def test_nonfinite_or_nonjson_saved_data_are_specific_failures(mode):
    result = read()
    if mode == 'nan': result['unknown'] = float('nan')
    elif mode == 'tuple': result['records'] = tuple(result['records'])
    elif mode == 'nonstring_key': result[2] = 'invalid'
    else: result['cycle'] = result
    with pytest.raises(ValueError, match='ncbi_gene_finite_json_required'):
        validate_ncbi_gene_native(result)
