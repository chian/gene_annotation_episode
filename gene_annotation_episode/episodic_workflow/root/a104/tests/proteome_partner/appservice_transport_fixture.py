from copy import deepcopy
import hashlib
import json
from gene_annotation_episode.episodic_workflow.root.a104.acquisition import SourceSnapshot
PREFIX = 'api.bvbrc_appservice.'
CONFIG = {'kind': 'api', 'service': 'bvbrc_appservice', 'execution_contract': 'bvbrc_appservice_execution_v1', 'endpoints': {'AppService': 'https://app.example.invalid/rpc', 'Workspace': 'https://workspace.example.invalid/rpc'}, 'scientific_adapters': []}
OBJECT_UUID = '11111111-1111-1111-1111-111111111111'
SHOCK_UUID = '22222222-2222-2222-2222-222222222222'

def metadata(path='/synthetic/work/input.fa', *, uuid=OBJECT_UUID, type='contigs', size=0, shock_url=None):
    parent, name = path.rsplit('/', 1)
    native = [name, type, parent, '2026-10-24T12:00:00', uuid, 'synthetic', size, {}, {}, 'w', 'n', shock_url or '']
    return {'pointer': '/rows/0', 'native_row': native, 'valid': True, 'path': path, 'uuid': uuid, 'type': type, 'shock_url': shock_url, 'creation_time': native[3], 'size': size, 'error': None}

def rpc_snapshot(rpc, value, *, endpoint=None):
    endpoint = endpoint or CONFIG['endpoints'][rpc['method'].split('.', 1)[0]]
    sent = json.dumps(rpc, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    body = json.dumps({'version': '1.1', 'id': rpc['id'], 'result': [value]}).encode()
    return SourceSnapshot('bvbrc_analysis', endpoint, {'kind': 'rpc', 'rpc': deepcopy(rpc)}, '2026-10-24T12:00:00+00:00', body, 'application/json', {'status': 200, 'body_complete': True, 'received_body_bytes': len(body), 'effective_url': endpoint, 'automatic_redirects': False, 'headers': {}, 'request': {'method': 'POST', 'url': endpoint, 'body_bytes': len(sent), 'body_sha256': hashlib.sha256(sent).hexdigest(), 'headers': []}, 'duration_measure': 'client_http_request_turnaround', 'http_turnaround_seconds': 0.25})

class Client:

    def __init__(self):
        self.calls = []
        self.value = []

    def rpc(self, rpc):
        self.calls.append(('rpc', deepcopy(rpc)))
        return rpc_snapshot(rpc, self.value)

    def task_info(self, task_id, file):
        self.calls.append(('task_info', task_id, file))
        url = CONFIG['endpoints']['AppService'] + '/task_info/' + task_id + '/' + file
        body = (OBJECT_UUID + '\n').encode() if file.startswith('job_result') else b'native log\n'
        return SourceSnapshot('bvbrc_analysis', url, {'kind': 'task_info', 'task_id': task_id, 'file': file}, '2026-10-24T12:00:00+00:00', body, 'text/plain', {'status': 200, 'body_complete': True, 'received_body_bytes': len(body), 'effective_url': url, 'automatic_redirects': False, 'request': {'method': 'GET', 'url': url}, 'headers': {'content-length': str(len(body))}})
