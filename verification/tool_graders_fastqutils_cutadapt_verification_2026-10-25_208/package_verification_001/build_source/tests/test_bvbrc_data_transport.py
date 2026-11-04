"""One compiled public BV-BRC GET; synthetic transport, actual native decoder."""
from copy import deepcopy
from email.message import Message
import http.client
import io
import json
from urllib.error import HTTPError

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.api_bvbrc import BVBRCDataClient, DEFAULT_BASE_URL
from gene_annotation_episode.bvbrc_data_query import encode_native_query


def prepared():
    return encode_native_query({'version': 'bvbrc_data_request_v2',
        'collection': 'genome_feature', 'mode': 'count', 'filters': []},
        base_url=DEFAULT_BASE_URL)


class Response:
    status = 200
    def __init__(self, url, *, error=None):
        self.url, self.error = url, error
        self.headers = Message()
        self.headers['Content-Type'] = 'application/solr+json; charset=utf-8'
        self.headers['Set-Cookie'] = 'fixture-secret'
        self.content = b'{"responseHeader":{"status":0},"response":{"numFound":2,"numFoundExact":true,"start":0,"docs":[]}}'
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def geturl(self): return self.url
    def read(self):
        if self.error:
            raise self.error
        return self.content


def test_v2_sends_exact_prepared_get_and_records_complete_native_response(monkeypatch):
    from gene_annotation_episode.bvbrc_data_readers import parse_data_snapshot
    from gene_annotation_episode.bvbrc_data_calculators import calculate_page_counts
    original = prepared()
    before = deepcopy(original)
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append((request, timeout))
            return Response(request.full_url)
    monkeypatch.setattr('gene_annotation_episode.api_bvbrc.urllib.request.build_opener', lambda handler: Opener())
    # Sending and decoding a persisted preparation must not compile it again.
    monkeypatch.setattr('gene_annotation_episode.bvbrc_data_query.encode_native_query',
        lambda *args, **kwargs: pytest.fail('persisted query was recompiled'))
    snapshot = BVBRCDataClient(timeout=4).query_prepared(original)
    assert original == before and len(calls) == 1
    request, timeout = calls[0]
    assert request.full_url == original['native_request']['url'] and timeout == 4
    assert request.get_method() == 'GET' and request.data is None
    assert request.get_header('Accept') == 'application/solr+json'
    assert request.get_header('Content-type') == 'application/solrquery+x-www-form-urlencoded'
    assert snapshot.request == original['effective_request']
    assert snapshot.transport['body_complete'] is True
    assert snapshot.transport['automatic_redirects'] is False
    assert snapshot.transport['request'] == {
        'method': 'GET', 'url': original['native_request']['url'], 'body': None,
        'headers': {item['name']: item['value'] for item in original['native_request']['headers']}}
    assert 'fixture-secret' not in json.dumps(snapshot.transport)
    # Leave the compiler unavailable through decoding and saved-sheet calculation.
    parsed = parse_data_snapshot(snapshot, prepared=original)
    assert parsed['status'] == 'complete'
    assert parsed['sheet']['count']['reported_value'] == 2
    assert parsed['sheet']['page']['returned_row_count'] == 0
    assert parsed['sheet']['rows'] == []
    counts = calculate_page_counts(parsed['sheet'])
    assert counts['reported_population_count'] == 2
    assert counts['population_exactness'] == 'exact'


@pytest.mark.parametrize('status,code', [(429, 'provider_http_429'), (302, 'provider_redirect_not_followed')])
def test_v2_retains_error_body_without_retry_or_redirect(monkeypatch, status, code):
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append(request)
            headers = Message()
            headers['Content-Type'] = 'text/html'
            raise HTTPError(request.full_url, status, 'failure', headers, io.BytesIO(b'native failure'))
    monkeypatch.setattr('gene_annotation_episode.api_bvbrc.urllib.request.build_opener', lambda handler: Opener())
    with pytest.raises(AcquisitionError) as failure:
        BVBRCDataClient().query_prepared(prepared())
    assert failure.value.code == code and len(calls) == 1
    assert failure.value.snapshot.content == b'native failure'
    assert failure.value.snapshot.transport['body_complete'] is True


def test_v2_retains_partial_bytes_as_incomplete(monkeypatch):
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append(request)
            return Response(request.full_url, error=http.client.IncompleteRead(b'{"response":', 20))
    monkeypatch.setattr('gene_annotation_episode.api_bvbrc.urllib.request.build_opener', lambda handler: Opener())
    with pytest.raises(AcquisitionError) as failure:
        BVBRCDataClient().query_prepared(prepared())
    assert failure.value.code == 'provider_response_body_incomplete'
    assert len(calls) == 1 and failure.value.snapshot.content == b'{"response":'
    assert failure.value.snapshot.transport['body_complete'] is False


@pytest.mark.parametrize('change', ['endpoint', 'collection_path', 'fragment'])
def test_v2_prepared_query_cannot_change_the_configured_endpoint(monkeypatch, change):
    original = prepared()
    if change == 'endpoint':
        original['query_population']['base_url'] = 'https://elsewhere.invalid/api'
    elif change == 'collection_path':
        original['native_request']['url'] = original['native_request']['url'].replace('/genome_feature/', '/taxonomy/')
    else:
        original['native_request']['url'] += '#fragment'
    monkeypatch.setattr('gene_annotation_episode.api_bvbrc.urllib.request.build_opener',
        lambda *args: pytest.fail('invalid prepared endpoint attempted transport'))
    with pytest.raises(ValueError, match='bvbrc_prepared_endpoint_conflict'):
        BVBRCDataClient().query_prepared(original)
