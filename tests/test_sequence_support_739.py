"""Shared CDS extraction and bounded transport; engineered cases are labelled.

No fixture is a new biological annotation. Native acquisition is never repeated
here; retained source inputs and actual Bio extraction remain distinguishable.
"""
from copy import deepcopy
from dataclasses import asdict
from contextlib import contextmanager
from email.message import Message
import builtins
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import socket
import threading
import urllib.error
import urllib.request

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import BeforePosition, CompoundLocation, SeqFeature, SimpleLocation
from Bio.SeqRecord import SeqRecord
import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, parse_genbank
from gene_annotation_episode.coding_sequence_support import (
    plan_coding_sequence_extractions, read_coding_sequence_results,
)
from gene_annotation_episode.coding_sequence_native import run_coding_sequence_plan
from gene_annotation_episode.sequence_extraction_grader import calculate_extraction_scores, grade_extraction
from gene_annotation_episode.sequence_mapping import VERSION

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / 'verification/tool_graders_hmmer_map_verification_2026-10-28_529/check201_native739/sequence-support-native739'


def identity_mapping(length, source_ref):
    return {'version': VERSION, 'symbol_length': length, 'units_per_symbol': 1,
            'path': [{'subject_ref': source_ref, 'start': 0, 'end': length, 'unit': 'nt', 'strand': '+'}]}


def engineered_record(location=None):
    record = SeqRecord(Seq('AaCGTnGCTTAGACCG'), id='ENGINEERED739.1', name='ENGINEERED739',
                       description='engineering geometry, no biological measurement')
    record.annotations.update(molecule_type='DNA', topology='circular')
    record.features = [SeqFeature(SimpleLocation(0, 16), type='source'),
        SeqFeature(location if location is not None else SimpleLocation(1, 8, strand=1),
                   type='CDS', qualifiers={'note': ['first', 'second'], 'codon_start': ['2']}),
        SeqFeature(SimpleLocation(8, 15, strand=1), type='CDS', qualifiers={'pseudo': ['']})]
    output = io.StringIO()
    SeqIO.write(record, output, 'genbank')
    content = output.getvalue().encode()
    return content, parse_genbank(content), SeqIO.read(io.StringIO(content.decode()), 'genbank')


def selection(record=0, feature=1, *, length=16, source='engineering739'):
    return {'record_ordinal': record, 'feature_ordinal': feature, 'subject_ref': source,
            'parent_mapping': identity_mapping(length, source)}


def plan_for(records, choices=None):
    return plan_coding_sequence_extractions(records, selection=[selection()] if choices is None else choices,
        source_ref='engineering739', molecule_model='dna')


@pytest.mark.parametrize('strand', [1, -1])
@pytest.mark.parametrize('spans', [((10, 16), (0, 4)), ((1, 4), (8, 12), (1, 4))])
def test_engineered_ordered_circular_and_repeated_parts_match_native_feature_extract(strand, spans):
    location = CompoundLocation([SimpleLocation(a, b, strand=strand) for a, b in spans], operator='join')
    _, records, native_record = engineered_record(location)
    original = deepcopy(records)
    plan = plan_for(records)
    produced = run_coding_sequence_plan(plan)
    result = read_coding_sequence_results(plan, extracted=produced)
    row = result['rows'][0]
    assert records == original
    assert row['sequence'] == str(native_record.features[1].extract(native_record.seq))
    assert row['source_feature'] == records[0]['features'][1]
    assert row['native_part_order'] == list(range(len(spans)))
    expected_spans = list(spans) if strand == 1 else list(reversed(spans))
    assert row['effective_request']['segments'] == [{'start': a, 'end': b} for a, b in expected_spans]
    assert result['status'] == 'complete'
    direct = grade_extraction(produced[0]['native_result'], input_sequence=records[0]['sequence'],
        subject_ref='engineering739', parent_mapping=selection()['parent_mapping'], request=row['effective_request'])
    assert row['grading'] == direct
    assert row['grading']['scores']['summary']['matching_symbol_count'] == len(row['sequence'])
    if spans == ((1, 4), (8, 12), (1, 4)):
        summary = row['grading']['scores']['summary']
        assert summary['selected_symbol_occurrence_count'] == 10
        assert summary['distinct_selected_input_symbol_count'] == 7
        assert summary['repeated_selected_input_symbol_count'] == 3
    assert calculate_extraction_scores(row['grading']['sheet']) == row['grading']['scores']


def test_source_ordinals_survive_filtered_array_order_and_repeated_selections():
    _, records, _ = engineered_record()
    records[0]['source_record_index'] = 7
    records[0]['features'][1]['source_feature_index'] = 42
    records[0]['features'] = list(reversed(records[0]['features']))
    plan = plan_for(records, [selection(7, 42), selection(7, 2), selection(7, 42)])
    result = read_coding_sequence_results(plan, extracted=run_coding_sequence_plan(plan))
    assert [row['feature_ordinal'] for row in result['rows']] == [42, 2, 42]
    assert [row['selection_ordinal'] for row in result['rows']] == [0, 1, 2]
    assert result['rows'][0]['sequence'] == result['rows'][2]['sequence']
    assert result['rows'][0]['source_feature']['qualifiers']['note'] == ['first', 'second']


def test_supplied_native_sequence_case_survives_without_genbank_serialization():
    _, records, _ = engineered_record()
    records[0]['sequence'] = 'AaCGTnGCTTAGACCG'
    plan = plan_for(records)
    result = read_coding_sequence_results(plan, extracted=run_coding_sequence_plan(plan))
    assert result['rows'][0]['sequence'] == 'aCGTnGC'
    assert result['rows'][0]['grading']['scores']['summary']['matching_symbol_count'] == 7


@pytest.mark.parametrize('mode,code', [
    ('record', 'selected_record_unavailable'), ('feature', 'selected_feature_unavailable'),
    ('not_cds', 'selected_feature_not_cds'), ('undefined', 'source_sequence_unavailable'),
    ('unlocated', 'source_location_unavailable'), ('remote', 'remote_sequence_operand_required'),
    ('mixed', 'mixed_orientation_requires_shared_view_extension'),
    ('bounds', 'source_bounds_unavailable_or_outside_sequence'),
    ('empty', 'source_bounds_unavailable_or_outside_sequence'),
])
def test_unavailable_operands_remain_specific_without_native_execution(mode, code, monkeypatch):
    from gene_annotation_episode import coding_sequence_native
    _, records, _ = engineered_record()
    chosen = selection()
    feature = records[0]['features'][1]
    if mode == 'record': chosen['record_ordinal'] = 3
    elif mode == 'feature': chosen['feature_ordinal'] = 30
    elif mode == 'not_cds': chosen['feature_ordinal'] = 0
    elif mode == 'undefined': records[0]['sequence'] = None
    elif mode == 'unlocated':
        records[0]['features'].remove(feature)
        records[0]['unlocated_features'] = [{'source_feature_index': 1, 'kind': 'CDS', 'qualifiers': {}}]
    elif mode == 'remote': feature['segments'][0]['ref'] = 'UNSUPPLIED.1'
    elif mode == 'mixed': feature['segments'].append({**feature['segments'][0], 'strand': '-'})
    elif mode == 'bounds': feature['segments'][0]['end'] = 17
    elif mode == 'empty': feature['segments'][0]['end'] = feature['segments'][0]['start']
    plan = plan_for(records, [chosen])
    def forbidden(*args, **kwargs): raise AssertionError('unselected native execution')
    monkeypatch.setattr(coding_sequence_native, 'view_sequence', forbidden)
    result = read_coding_sequence_results(plan, extracted=run_coding_sequence_plan(plan))
    row = result['rows'][0]
    assert row['issue_codes'] == [code]
    assert row['extraction_status'] == 'unavailable'
    assert row['sequence'] is row['grading'] is None


@pytest.mark.parametrize('mode,code', [('fuzzy', 'nominal_fuzzy_coordinates'),
    ('unknown', 'source_strand_unknown_as_is'), ('order', 'native_order_location')])
def test_source_qualifications_are_retained_even_when_nominal_extraction_matches(mode, code):
    location = (SimpleLocation(BeforePosition(1), 8, strand=1) if mode == 'fuzzy' else
        SimpleLocation(1, 8, strand=None) if mode == 'unknown' else
        CompoundLocation([SimpleLocation(1, 4, strand=1), SimpleLocation(8, 12, strand=1)], operator='order'))
    _, records, _ = engineered_record(location)
    # GenBank has no native representation for strand=None; test the parser's
    # explicit unavailable strand rather than pretending serialization retains it.
    if mode == 'unknown': records[0]['features'][1]['segments'][0]['strand'] = 'unknown'
    plan = plan_for(records)
    row = read_coding_sequence_results(plan, extracted=run_coding_sequence_plan(plan))['rows'][0]
    assert code in row['issue_codes'] and row['extraction_status'] == 'partial'
    assert row['grading']['scores']['summary']['mismatching_symbol_count'] == 0


def test_missing_failed_and_valid_results_stay_distinct_and_saved_recalculation_is_pure(monkeypatch):
    _, records, _ = engineered_record()
    plan = plan_for(records, [selection(), selection(feature=2), selection()])
    native = run_coding_sequence_plan(plan)
    result = read_coding_sequence_results(plan, extracted=[native[0],
        {'selection_ordinal': 1, 'native_result': None, 'failure_code': 'labelled_engineering_failure'}])
    assert [row['extraction_status'] for row in result['rows']] == ['completed', 'failed', 'not_started']
    sheet, expected = deepcopy(result['rows'][0]['grading']['sheet']), deepcopy(result['rows'][0]['grading']['scores'])
    original_import = builtins.__import__
    def restricted_import(name, *args, **kwargs):
        if name == 'Bio' or name.startswith('Bio.') or name.endswith('coding_sequence_native'):
            raise AssertionError('native dependency in saved recalculation')
        return original_import(name, *args, **kwargs)
    def forbidden(*args, **kwargs): raise AssertionError('IO in saved recalculation')
    monkeypatch.setattr(builtins, '__import__', restricted_import)
    monkeypatch.setattr(builtins, 'open', forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    assert calculate_extraction_scores(sheet) == expected


@pytest.mark.parametrize('mode', ['sequence', 'request', 'schema', 'missing_field'])
def test_corrupt_native_one_row_does_not_discard_valid_other_row(mode):
    _, records, _ = engineered_record()
    plan = plan_for(records, [selection(), selection(feature=2)])
    native = run_coding_sequence_plan(plan)
    if mode == 'sequence': native[0]['native_result']['sequence'] = 'X' * 7
    elif mode == 'request': native[0]['native_result']['orientation'] = 'reverse_complement'
    elif mode == 'schema': native[0]['native_result']['operation_version'] = 'alien'
    else: del native[0]['native_result']['sequence']
    result = read_coding_sequence_results(plan, extracted=native)
    assert result['status'] == 'partial'
    assert result['rows'][0]['extraction_status'] in {'partial', 'failed'}
    assert result['rows'][1]['extraction_status'] == 'completed'


@pytest.mark.parametrize('mode', ['plan_request', 'plan_feature', 'duplicate_result', 'unknown_result',
    'bool_result', 'unavailable_result', 'native_and_failure'])
def test_selected_plan_and_result_identity_conflicts_are_rejected(mode):
    _, records, _ = engineered_record()
    plan = plan_for(records)
    native = run_coding_sequence_plan(plan)
    if mode == 'plan_request': plan['rows'][0]['effective_request']['segments'][0]['start'] = 0
    elif mode == 'plan_feature': plan['rows'][0]['source_feature']['kind'] = 'gene'
    elif mode == 'duplicate_result': native.append(deepcopy(native[0]))
    elif mode == 'unknown_result': native[0]['selection_ordinal'] = 6
    elif mode == 'bool_result': native[0]['selection_ordinal'] = False
    elif mode == 'unavailable_result': plan = plan_for(records, [selection(feature=0)])
    else: native[0]['failure_code'] = 'contradiction'
    with pytest.raises(ValueError, match='coding_sequence_'):
        read_coding_sequence_results(plan, extracted=native)


@pytest.mark.parametrize('mode', ['bool_ordinal', 'extra_selection', 'duplicate_record', 'duplicate_feature',
    'tuple_records', 'nan', 'bad_parts', 'bad_features'])
def test_malformed_source_and_selection_are_not_coerced(mode):
    _, records, _ = engineered_record()
    choices = [selection()]
    if mode == 'bool_ordinal': choices[0]['feature_ordinal'] = True
    elif mode == 'extra_selection': choices[0]['guess'] = 'CDS'
    elif mode == 'duplicate_record': records.append(deepcopy(records[0]))
    elif mode == 'duplicate_feature': records[0]['features'].append(deepcopy(records[0]['features'][1]))
    elif mode == 'tuple_records': records = tuple(records)
    elif mode == 'nan': records[0]['measurement'] = float('nan')
    elif mode == 'bad_parts': records[0]['features'][1]['segments'] = [None]
    else: records[0]['features'] = [None]
    with pytest.raises(ValueError, match='coding_sequence_'):
        plan_for(records, choices)


def test_explicit_empty_selection_does_no_work_and_missing_mapping_is_not_invented():
    _, records, _ = engineered_record()
    empty = plan_for(records, [])
    assert run_coding_sequence_plan(empty) == []
    assert read_coding_sequence_results(empty, extracted=[])['rows'] == []
    chosen = selection()
    chosen['parent_mapping'] = None
    plan = plan_for(records, [chosen])
    row = read_coding_sequence_results(plan, extracted=run_coding_sequence_plan(plan))['rows'][0]
    assert row['extraction_status'] == 'partial'
    assert row['grading']['scores']['verified_output_source_path'] is None


def test_actual_native_failure_preserves_selected_operands_and_other_valid_extraction():
    _, records, _ = engineered_record(SimpleLocation(1, 8, strand=-1))
    records[0]['sequence'] = 'ACGT?NGCTTAGACCG'
    plan = plan_for(records, [selection(), selection(feature=2)])
    produced = run_coding_sequence_plan(plan)
    assert produced[0]['failure_code'] == 'native_extraction_failed'
    result = read_coding_sequence_results(plan, extracted=produced)
    assert result['rows'][0]['input_sequence'] == records[0]['sequence']
    assert result['rows'][0]['extraction_status'] == 'failed'
    assert result['rows'][1]['extraction_status'] == 'completed'


class Received(io.BytesIO):
    def __init__(self, body, *, length=None):
        super().__init__(body)
        self.status = 200
        self.headers = Message()
        self.headers['Content-Type'] = 'application/octet-stream'
        if length is not None: self.headers['Content-Length'] = str(length)
        self.requested_sizes = []

    def read(self, size=-1):
        self.requested_sizes.append(size)
        return super().read(size)

    def geturl(self): return 'https://selected.example/entity'


@contextmanager
def bounded_loopback(mode):
    """Engineering HTTP framing; these bytes are never provider science."""
    calls = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            calls.append(self.path)
            self.send_response(200)
            if mode == 'chunked_partial':
                self.send_header('Transfer-Encoding', 'chunked')
                payload = b'3\r\nabc\r\n'
            else:
                payload = b'ab' if mode == 'short' else b'abcde'
                self.send_header('Content-Length', '5')
            self.end_headers()
            self.wfile.write(payload)
            self.wfile.flush()
            self.close_connection = True
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    thread.start()
    try: yield 'http://127.0.0.1:' + str(server.server_port) + '/selected', calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize('mode,limit,expected,code', [
    ('complete', 5, b'abcde', None), ('overflow', 3, b'abc', 'provider_response_byte_limit'),
    ('short', 10, b'ab', 'provider_body_capture_failed'),
    ('chunked_partial', 10, b'abc', 'provider_body_capture_failed'),
])
def test_real_bounded_http_framing_complete_overflow_and_truncation(mode, limit, expected, code):
    with bounded_loopback(mode) as (url, calls):
        if code is None:
            snapshot = PublicClients()._http('loopback_engineering', url, {'id': '7'}, 'text/plain', max_bytes=limit)
        else:
            with pytest.raises(AcquisitionError) as failure:
                PublicClients()._http('loopback_engineering', url, {'id': '7'}, 'text/plain', max_bytes=limit)
            assert failure.value.code == code
            snapshot = failure.value.snapshot
    assert calls == ['/selected?id=7']
    assert snapshot.content == expected
    assert snapshot.transport['body_complete'] is (code is None)


@pytest.mark.parametrize('body,limit', [(b'abc', 10), (b'abc', 3), (b'', 1)])
def test_bounded_http_complete_and_exact_limit_preserve_actual_bytes(body, limit, monkeypatch):
    response = Received(body, length=len(body))
    calls = []
    def receive(request, **kwargs): calls.append(request); return response
    monkeypatch.setattr(urllib.request, 'urlopen', receive)
    snapshot = PublicClients()._http('selected', 'https://selected.example/entity', {'id': '7'}, 'text/plain', max_bytes=limit)
    assert len(calls) == 1 and snapshot.content == body
    assert snapshot.transport['body_complete'] is True
    assert snapshot.transport['retained_body_bytes'] == len(body)
    assert all(0 < size <= limit + 1 for size in response.requested_sizes)


@pytest.mark.parametrize('mode', ['overflow', 'incomplete_exception', 'short_content_length'])
def test_bounded_http_preserves_prefix_and_distinguishes_failed_capture(mode, monkeypatch):
    response = Received(b'abcdef', length=9 if mode == 'short_content_length' else 6)
    if mode == 'incomplete_exception':
        def read(size): raise http.client.IncompleteRead(b'abc', 6)
        response.read = read
    monkeypatch.setattr(urllib.request, 'urlopen', lambda *args, **kwargs: response)
    with pytest.raises(AcquisitionError) as failure:
        PublicClients()._http('selected', 'https://selected.example/entity', {}, 'text/plain',
                             max_bytes=3 if mode == 'overflow' else 10)
    snapshot = failure.value.snapshot
    assert snapshot.content == (b'abcdef' if mode == 'short_content_length' else b'abc')
    assert snapshot.transport['body_complete'] is False
    assert failure.value.code == ('provider_response_byte_limit' if mode == 'overflow' else 'provider_body_capture_failed')
    if mode == 'overflow': assert snapshot.transport['observed_body_bytes'] == 4


def test_bounded_http_error_retains_status_and_bounded_body_without_retry(monkeypatch):
    calls = []
    headers = Message()
    headers['Retry-After'] = '7'
    headers['Content-Length'] = '8'
    def fail(request, **kwargs):
        calls.append(request)
        raise urllib.error.HTTPError(request.full_url, 503, 'labelled engineering failure', headers, io.BytesIO(b'abcdefgh'))
    monkeypatch.setattr(urllib.request, 'urlopen', fail)
    with pytest.raises(AcquisitionError) as failure:
        PublicClients()._http('selected', 'https://selected.example/entity', {}, 'text/plain', max_bytes=3)
    assert len(calls) == 1 and failure.value.code == 'provider_http_503'
    assert failure.value.retry_after == 7
    assert failure.value.snapshot.content == b'abc'
    assert failure.value.snapshot.transport['body_capture_failure'] == 'provider_response_byte_limit'


def test_historical_unbounded_http_signature_and_failed_body_are_preserved(monkeypatch):
    calls = []
    response = Received(b'complete historical mode')
    def receive(request, **kwargs): calls.append(request); return response
    monkeypatch.setattr(urllib.request, 'urlopen', receive)
    snapshot = PublicClients()._http('selected', 'https://selected.example/entity', {}, 'application/json',
                                  json_body={'selected': ['a', 'b']})
    assert response.requested_sizes == [-1] and snapshot.content == b'complete historical mode'
    assert calls[0].get_method() == 'POST' and json.loads(calls[0].data) == {'selected': ['a', 'b']}
    assert 'response_byte_limit' not in snapshot.transport
    def fail(request, **kwargs):
        raise urllib.error.HTTPError(request.full_url, 503, 'labelled historical transport', Message(), io.BytesIO(b'full error'))
    monkeypatch.setattr(urllib.request, 'urlopen', fail)
    with pytest.raises(AcquisitionError) as error:
        PublicClients()._http('selected', 'https://selected.example/entity', {}, 'application/json')
    assert error.value.snapshot.content == b'full error'
    assert error.value.snapshot.transport['body_complete'] is True


@pytest.mark.parametrize('limit', [0, -1, True, 3.0, '3'])
def test_invalid_explicit_transport_limit_rejects_before_network(limit, monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('invalid request sent')
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    with pytest.raises(ValueError, match='explicit_response_byte_limit_required'):
        PublicClients()._http('selected', 'https://selected.example/entity', {}, 'text/plain', max_bytes=limit)


def test_new_molecular_requests_preserve_all_explicit_ids_and_bounds(monkeypatch):
    calls = []
    client = PublicClients()
    def record(*args, **kwargs): calls.append((args, kwargs)); return 'captured'
    monkeypatch.setattr(client, '_http', record)
    assert client.ncbi_gene(['2', '10'], max_bytes=500) == 'captured'
    assert calls[-1][0][2]['db'] == 'gene' and calls[-1][0][2]['id'] == '2,10'
    assert calls[-1][1] == {'max_bytes': 500}
    client.addgene_sequences('50005', max_bytes=200)
    assert calls[-1][0][1] == 'https://www.addgene.org/50005/sequences/'
    client.ncbi_search('gene', 'supplied selected term', max_bytes=100)
    assert calls[-1][0][2]['db'] == 'gene' and calls[-1][1] == {'max_bytes': 100}
    client.ncbi_sequence('AJ320226.1', max_bytes=200)
    assert calls[-1][0][2]['db'] == 'nuccore' and calls[-1][1] == {'max_bytes': 200}
    client.ncbi_sequence('AJ320226.1')
    assert calls[-1][1] == {}  # Historical unbounded caller signature preserved.


@pytest.mark.parametrize('ids', [[], ['2', '2'], [2], ['2,10'], ['２'], '2', [True]])
def test_gene_operand_never_chooses_or_coerces_ids(ids, monkeypatch):
    client = PublicClients()
    def forbidden(*args, **kwargs): raise AssertionError('invalid request sent')
    monkeypatch.setattr(client, '_http', forbidden)
    with pytest.raises(ValueError, match='explicit_ncbi_gene_ids_required'):
        client.ncbi_gene(ids, max_bytes=100)


@pytest.mark.parametrize('identifier', [50005, True, '', '50005/sequences', '１２'])
def test_addgene_operand_never_guesses_a_provider(identifier):
    with pytest.raises(ValueError, match='explicit_addgene_id_required'):
        PublicClients().addgene_sequences(identifier, max_bytes=100)


def test_original_native_entities_feed_detached_support_readers_without_network(monkeypatch):
    from gene_annotation_episode.ncbi_gene_native import read_ncbi_gene_xml, validate_ncbi_gene_native
    from gene_annotation_episode.addgene_sequence_native import read_addgene_sequences, validate_addgene_sequence_page
    gene = (CAPTURE / 'gene2.entity').read_bytes()
    plasmid = (CAPTURE / 'addgene50005.entity').read_bytes()
    assert hashlib.sha256(gene).hexdigest() == '06caac1d71d16e5cad9278bb81ff41cd7abc067681638cbaca3e050e025d82ca'
    assert hashlib.sha256(plasmid).hexdigest() == 'deb0393a4b1c71ae21e438a7dd2a6f410defbc83c3e939c2ce10faf0b4b30c4d'
    def forbidden(*args, **kwargs): raise AssertionError('saved parser performed acquisition')
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    gene_result = read_ncbi_gene_xml(gene, source_ref='saved201:gene2', requested_gene_ids=['2'], response_complete=True)
    plasmid_result = read_addgene_sequences(plasmid, source_ref='saved201:addgene50005', requested_id='50005', response_complete=True)
    assert len(gene_result['records']) == 1 and len(gene_result['records'][0]['loci']) == 3
    assert gene_result['records'][0]['gene_id'] == '2'
    assert len(plasmid_result['records']) == 3 and plasmid_result['authentication_required'] is True
    assert [row['source_completeness'] for row in plasmid_result['records']].count('full') == 1
    assert all(row['sequence'] is None for row in plasmid_result['records'])
    assert validate_ncbi_gene_native(json.loads(json.dumps(gene_result))) == gene_result
    assert validate_addgene_sequence_page(json.loads(json.dumps(plasmid_result))) == plasmid_result


@pytest.mark.skipif('HMMER529_ATTEMPT' not in os.environ, reason='requires bounded529')
def test_selected_current_nucleotide_capture_through_actual_bounded_client_and_shared_cds_path():
    """ONE selected GET. On later repair run this case only from saved bytes."""
    directory = Path(os.environ['HMMER529_ATTEMPT']) / 'sequence-support-cds739'
    directory.mkdir(exist_ok=False)
    snapshot = None
    failure = None
    try:
        snapshot = PublicClients(timeout=90).ncbi_sequence('AJ320226.1', max_bytes=4 * 1024 * 1024)
    except AcquisitionError as error:
        snapshot = error.snapshot
        failure = {'code': error.code, 'phase': error.phase, 'diagnostic': error.diagnostic}
    if snapshot is not None:
        (directory / 'AJ320226.1.entity').write_bytes(snapshot.content)
        metadata = asdict(snapshot)
        del metadata['content']
        metadata.update(size_bytes=len(snapshot.content), sha256=snapshot.sha256)
        (directory / 'AJ320226.1.json').write_text(json.dumps(metadata, indent=2) + '\n')
    (directory / 'capture-status.json').write_text(json.dumps({'failure': failure,
        'snapshot_retained': snapshot is not None, 'selected_requests': 1}, indent=2) + '\n')
    assert failure is None and snapshot is not None, 'selected_nucleotide_capture_unavailable'
    assert snapshot.transport['body_complete'] is True
    assert snapshot.transport['status'] == 200
    records = parse_genbank(snapshot.content)
    (directory / 'parsed.json').write_text(json.dumps(records, indent=2) + '\n')
    assert records[0]['accession'] == 'AJ320226.1'
    assert next(feature for feature in records[0]['features'] if feature['source_feature_index'] == 2)['kind'] == 'CDS'
    chosen = selection(feature=2, length=len(records[0]['sequence']), source='selected-current-AJ320226.1')
    plan = plan_coding_sequence_extractions(records, selection=[chosen], source_ref='selected-current-AJ320226.1', molecule_model='dna')
    produced = run_coding_sequence_plan(plan)
    result = read_coding_sequence_results(plan, extracted=produced)
    (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    native_records = list(SeqIO.parse(io.StringIO(snapshot.content.decode()), 'genbank'))
    expected = str(native_records[0].features[2].extract(native_records[0].seq))
    row = result['rows'][0]
    assert row['sequence'] == expected
    assert row['grading']['scores']['summary']['matching_symbol_count'] == len(expected)
    assert row['grading']['scores']['summary']['mismatching_symbol_count'] == 0
    assert calculate_extraction_scores(row['grading']['sheet']) == row['grading']['scores']
