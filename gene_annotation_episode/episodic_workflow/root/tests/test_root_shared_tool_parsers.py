"""Original parser boundaries and labelled synthetic protocol cases; no transport."""
from copy import deepcopy
import hashlib
import io
import json
import zipfile

import pytest

from gene_annotation_episode import blast_search as blast
from gene_annotation_episode.chemistry import rhea_equation
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.rfam_discovery import (
    hit_row, result_body, result_url, submission_handle, validate_result_url)


def native(subject, program='blastn', *, bad=False, missing=False):
    row={'num':1,'query_from':3,'query_to':9,'hit_from':11,'hit_to':5,
        'bit_score':0.,'score':12.,'evalue':0.,'query_strand':'Plus','hit_strand':'Minus',
        'qseq':'ACGTAGG','hseq':'ACGTAGG'}
    if program == 'blastp':
        row.update(hit_from=5, hit_to=11, qseq='LRQQQQQ', hseq='LRQQQQQ')
        row.pop('query_strand'); row.pop('hit_strand')
    elif program in ('blastx', 'tblastn', 'tblastx'):
        row.pop('query_strand'); row.pop('hit_strand')
        row.update(query_from=3 if program == 'tblastn' else 8,
            query_to=4 if program == 'tblastn' else 3,
            hit_from=3 if program == 'blastx' else 8,
            hit_to=4 if program == 'blastx' else 3, qseq='LR', hseq='LR')
        if program != 'tblastn': row['query_frame'] = -2
        if program != 'blastx': row['hit_frame'] = -2
    if bad: row['query_to']=99
    hits=[{'num':1,'description':[{'id':'synthetic_native','accession':'SYNTHETIC.1','title':'labelled synthetic hit',
        'taxid':2157,'sciname':'Archaea'}], 'len':18,'hsps':[row]}]
    search={'query_id':'Query_1','query_title':subject,'query_len':12,'hits':hits}
    if missing: search.pop('hits')
    return {'BlastOutput2':[{'report':{'program':program,'version':'synthetic_BLAST',
        'search_target':{'db':'core_nt'},'params':{'expect':10},'results':{'search':search}}}]}


@pytest.mark.parametrize('arrow,direction',[('=','undefined'),('=>','left_to_right'),('<=','right_to_left'),('<=>','bidirectional')])
def test_synthetic_equation_direction_and_symbolic_coefficient_are_not_physiology(arrow,direction):
    # Synthetic markup exercises the notation parser, not a claim that the
    # current JSON search exposes directional-quartet entries.
    html=('<span class="participant"><span class="stoichiometry">n+1</span>'
          '<a data-molid="rhea-comp:7">a carrier+</a><span class="location">(out)</span></span>'
          ' '+arrow.replace('<','&lt;').replace('>','&gt;')+' '
          '<span class="participant"><span class="stoichiometry"> </span>'
          '<a data-molid="chebi:15377">H<sub>2</sub>O</a></span>')
    actual_arrow,actual_direction,parts=rhea_equation(html)
    assert (actual_arrow,actual_direction)==(arrow,direction)
    assert parts[0]['coefficient_expression']=='n+1' and parts[0]['source_name']=='a carrier+'
    assert parts[0]['source_location']=='(out)' and parts[0]['side']=='left'
    assert parts[1]['source_name']=='H2O' and parts[1]['side']=='right'
    assert parts[1]['coefficient_basis']=='implicit_unit_rhea_notation'


@pytest.mark.parametrize('program,units', [
    ('blastn', ('nt', 'nt', 'nt')), ('blastp', ('aa', 'aa', 'aa')),
    ('blastx', ('nt', 'aa', 'aa')), ('tblastn', ('aa', 'nt', 'aa')),
    ('tblastx', ('nt', 'nt', 'aa')),
])
def test_original_blast_native_geometry_keeps_selected_program_units(program, units):
    body = native('selected-subject', program)
    parsed = blast.document(json.dumps(body).encode())
    blast.validate_identity(parsed, {'algorithm': program, 'subject_ref': 'selected-subject', 'query_length': 12})
    hit = parsed['search']['hits'][0]
    hsp = hit['hsps'][0]
    actual = blast.native_hsp_metadata(hsp, program=program, query_length=12,
        reference_length=hit['len'], hit_ordinal=0, hsp_ordinal=0)
    assert (actual['query_coordinate_unit'], actual['hit_coordinate_unit'], actual['alignment_unit']) == units
    for key in ('query_from', 'query_to', 'hit_from', 'hit_to'):
        assert actual[key] == hsp[key]
    for key in ('query_frame', 'hit_frame', 'query_strand', 'hit_strand'):
        if key in hsp:
            assert actual[key] == hsp[key]
    assert 'measurements' not in actual


@pytest.mark.parametrize('field,value,error', [
    ('algorithm', 'blastp', 'program_conflicts'),
    ('subject_ref', 'unrelated-subject', 'query_title_conflicts'),
    ('query_length', 13, 'query_length_conflicts'),
])
def test_blast_parser_rejects_conflicting_actual_selected_operand(field, value, error):
    parsed = blast.document(json.dumps(native('selected-subject')).encode())
    request = {'algorithm': 'blastn', 'subject_ref': 'selected-subject', 'query_length': 12}
    request[field] = value
    with pytest.raises(ValueError, match=error):
        blast.validate_identity(parsed, request)


def test_actual_provider_consumer_preserves_exact_zip_member_bytes():
    from gene_annotation_episode.provider_jobs import blast as provider_blast
    assert provider_blast is blast
    content = json.dumps(native('selected-subject'), indent=3).encode() + b'\n'
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as writer:
        writer.writestr('manifest.json', json.dumps({'BlastJSON': [{'File': 'actual.json'}]}))
        writer.writestr('actual.json', content)
    parsed = provider_blast.document(archive.getvalue())
    assert parsed['json_bytes'] == content
    assert parsed['member'] == {'ordinal': 1, 'name': 'actual.json'}
    assert parsed['search']['query_title'] == 'selected-subject'


def test_blast_duplicate_selected_archive_members_are_not_silently_chosen():
    content = json.dumps(native('selected-subject')).encode()
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as writer:
        writer.writestr('first.json', content)
        writer.writestr('second.json', content)
    with pytest.raises(ValueError, match='archive_payload_ambiguous_or_missing'):
        blast.document(archive.getvalue())


def rfam_fixture():
    """Explicit synthetic protocol operands, not a retained provider response."""
    sequence = 'ACGUACGU'
    job = 'infernal_cmscan-engineering-fixture'
    body = {'jobId': job, 'searchSequence': sequence, 'numHits': 1,
        'hits': {'labelled-family': [{'acc': 'RF00001', 'id': 'labelled-family',
            'start': 8, 'end': 1, 'strand': '-', 'score': 0.0, 'E': 0.0, 'GC': 0.5}]}}
    return sequence, job, body


def test_rfam_exact_job_sequence_and_native_reverse_coordinates_are_preserved():
    sequence, job, body = rfam_fixture()
    submission = json.dumps({'jobId': job, 'resultURL': result_url(job)}).encode()
    assert submission_handle(submission) == job
    parsed = result_body(json.dumps(body).encode(), job_id=job,
        sequence_sha256=hashlib.sha256(sequence.encode()).hexdigest())
    row = hit_row(parsed['hits']['labelled-family'][0], family_key='labelled-family', sequence_length=len(sequence))
    assert row['sequence_interval'] == [0, 8]
    assert (row['native_start'], row['native_end'], row['strand']) == (8, 1, '-')
    assert row['bitscore'] == row['evalue'] == 0.0
    assert row['source_family_label'] == 'labelled-family'


@pytest.mark.parametrize('url', [
    'https://example.invalid/result/infernal_cmscan-engineering-fixture',
    'https://batch.rfam.org/result/infernal_cmscan-unrelated',
])
def test_rfam_submission_handle_does_not_authorize_foreign_provider_or_job(url):
    _, job, _ = rfam_fixture()
    with pytest.raises(ValueError, match='result_url_identity_conflict'):
        validate_result_url(url, job)


@pytest.mark.parametrize('field,value,error', [
    ('jobId', 'infernal_cmscan-unrelated', 'job_identity_conflict'),
    ('searchSequence', 'UUUUUUUU', 'sequence_identity_conflict'),
])
def test_rfam_conflicting_saved_response_identity_is_rejected(field, value, error):
    sequence, job, body = rfam_fixture()
    body[field] = value
    with pytest.raises(ValueError, match=error):
        result_body(json.dumps(body).encode(), job_id=job,
            sequence_sha256=hashlib.sha256(sequence.encode()).hexdigest())


def test_chemistry_unbalanced_native_markup_is_rejected_without_interpretation():
    with pytest.raises(ContractError, match='unbalanced_rhea_equation_markup'):
        rhea_equation('<span><a data-molid="CHEBI:15377">water</span>')
