"""A real HTTP server that speaks the NCBI BLAST Common URL API, for the tests of the API job route.

It listens on a port of 127.0.0.1 and answers the three requests of the protocol as the service does:

- ``CMD=Put`` (POST, form fields): a page with ``RID = ...`` and ``RTOE = ...`` between ``QBlastInfoBegin`` and
  ``QBlastInfoEnd``;
- ``CMD=Get`` with ``FORMAT_OBJECT=SearchInfo``: ``Status=WAITING`` for the first ``waiting_polls`` status requests
  of a job, then ``Status=<final>`` (``READY`` with ``ThereAreHits=yes``, or ``FAILED``); ``Status=UNKNOWN`` for a
  job it does not know;
- ``CMD=Get`` with ``FORMAT_TYPE=JSON2``: the report of the submitted query (its program, its title, its length,
  one hit), as the ZIP archive the service sends (a manifest and one report member) or as plain JSON.

Nothing computes an alignment: the report is a fixed hit over the submitted query. What a test changes is how the
service behaves (``submit_status``, ``give_rid``, ``waiting_polls``, ``final``, ``archive``, ``redirect_to``), and
``requests`` is what the service received, in order, with the time of each.

``reachable_through_proxy_settings`` makes the loopback address exempt from the proxy the test environment names
(``http_proxy``), as a deployment does with ``no_proxy``: the route's HTTP client is used as it is.
"""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
import threading
import time
import urllib.parse
import zipfile


def report(fields):
    header, *lines = fields['QUERY'].strip().splitlines()
    sequence = ''.join(lines)
    span = min(5, len(sequence))
    hit = {'num': 1, 'len': len(sequence),
           'description': [{'id': 'sp|TEST1|TEST_HIT', 'accession': 'TEST1', 'title': 'Test protein',
                            'taxid': 562, 'sciname': 'Escherichia coli'}],
           'hsps': [{'num': 1, 'bit_score': 40.0, 'score': 90, 'evalue': 1e-9, 'query_from': 1, 'query_to': span,
                     'hit_from': 1, 'hit_to': span, 'identity': span, 'positive': span, 'align_len': span,
                     'gaps': 0, 'qseq': sequence[:span], 'hseq': sequence[:span]}]}
    return {'report': {'program': fields['PROGRAM'], 'version': 'BLAST test service',
                       'search_target': {'db': fields['DATABASE']}, 'params': {'expect': 10},
                       'results': {'search': {'query_id': 'Query_1', 'query_title': header[1:],
                                              'query_len': len(sequence), 'hits': [hit],
                                              'stat': {'db_num': 1000, 'db_len': 100000}}}}}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *arguments):
        pass

    def _reply(self, status, body, content_type='text/html', headers=()):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _info(self, *lines):
        return ('<html><body>\n' + ''.join('<!--QBlastInfoBegin\n' + ''.join('    ' + item + '\n' for item in block)
                                           + 'QBlastInfoEnd\n-->\n' for block in lines) + '</body></html>\n').encode()

    def _handle(self, fields):
        service = self.server.service
        with service.lock:
            service.requests.append({'method': self.command, 'fields': fields, 'at': time.time(),
                                     'user_agent': self.headers.get('User-Agent'),
                                     'authorization': self.headers.get('Authorization'),
                                     'cookie': self.headers.get('Cookie')})
            if service.redirect_to is not None:
                return self._reply(302, b'', headers=[('Location', service.redirect_to)])
            if fields.get('CMD') == 'Put':
                if service.submit_status != 200:
                    return self._reply(service.submit_status, b'the service is not available')
                rid = 'TESTRID%04d' % (len(service.jobs) + 1)
                service.jobs[rid] = {'fields': fields, 'polls': 0}
                return self._reply(200, self._info(['RID = ' + (rid if service.give_rid else ''),
                                                    'RTOE = ' + str(service.expected_seconds)]))
            job = service.jobs.get(fields.get('RID'))
            if fields.get('CMD') == 'Get' and fields.get('FORMAT_OBJECT') == 'SearchInfo':
                if job is None:
                    return self._reply(200, self._info(['Status=UNKNOWN']))
                job['polls'] += 1
                if job['polls'] <= service.waiting_polls:
                    return self._reply(200, self._info(['Status=WAITING']))
                if service.final == 'READY':
                    return self._reply(200, self._info(['Status=READY'], ['ThereAreHits=yes']))
                return self._reply(200, self._info(['Status=' + service.final]))
            if fields.get('CMD') == 'Get' and fields.get('FORMAT_TYPE') == 'JSON2' and job is not None:
                if not service.archive:
                    return self._reply(200, json.dumps({'BlastOutput2': [report(job['fields'])]}).encode(),
                                       'application/json')
                rid, packed = fields['RID'], io.BytesIO()
                with zipfile.ZipFile(packed, 'w') as archive:
                    archive.writestr(rid + '.json', json.dumps({'BlastJSON': [{'File': rid + '_1.json'}]}))
                    archive.writestr(rid + '_1.json', json.dumps({'BlastOutput2': report(job['fields'])}))
                return self._reply(200, packed.getvalue(), 'application/zip')
            return self._reply(400, b'unknown request')

    def do_GET(self):
        self._handle(dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(self.path).query)))

    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        self._handle(dict(urllib.parse.parse_qsl(body.decode())))


class BlastUrlApiService:
    """The running service: its address, how it behaves and what it received."""

    def __init__(self, *, waiting_polls=1, expected_seconds=0):
        self.waiting_polls, self.expected_seconds = waiting_polls, expected_seconds
        self.submit_status, self.give_rid, self.final, self.archive, self.redirect_to = 200, True, 'READY', True, None
        self.requests, self.jobs, self.lock = [], {}, threading.Lock()
        self._server = ThreadingHTTPServer(('127.0.0.1', 0), _Handler)
        self._server.service = self
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self):
        return 'http://127.0.0.1:%d/Blast.cgi' % self._server.server_address[1]

    def received(self, **fields):
        """The requests received whose fields include ``fields``."""
        return [item for item in self.requests if fields.items() <= item['fields'].items()]

    def close(self):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()


@contextmanager
def reachable_through_proxy_settings():
    before = os.environ.get('no_proxy')
    os.environ['no_proxy'] = '127.0.0.1'
    try:
        yield
    finally:
        if before is None:
            del os.environ['no_proxy']
        else:
            os.environ['no_proxy'] = before


@contextmanager
def blast_url_api_service(**behaviour):
    with reachable_through_proxy_settings():
        service = BlastUrlApiService(**behaviour)
        try:
            yield service
        finally:
            service.close()


def route_configuration(service, workspace, *, request_spacing=0.05, poll_spacing=0.2, contact_email=None):
    """The configuration of an ``ApiJobRoute`` on the test service, with the service's spacing rules made short."""
    return {'service': 'ncbi_blast', 'base_url': service.url, 'workspace': str(workspace),
            'client_name': 'api-job-route-test', 'contact_email': contact_email,
            'request_spacing_seconds': request_spacing, 'poll_spacing_seconds': poll_spacing,
            'transport_timeout_seconds': 10}
