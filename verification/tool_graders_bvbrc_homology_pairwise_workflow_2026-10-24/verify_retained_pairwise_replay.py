"""Focused recovery check against the completed, retained actual Workflow.

This does not rerun the investigation or replace its original pytest result.
Native calls and both model-provider entry points are forbidden. All custody,
publication reads, calculation and replay use production implementations.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests'))

from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_bvbrc_homology_pairwise_workflow import (
    CONFIG, EVIDENCE, NativeClient, Client, _assert_saved_pairwise_recalculation_and_replay,
    _source_provenance, _write,
)


RUN = EVIDENCE / 'runs/pairwise-ih4zrdlw'


def test_retained_workflow_pairwise_saved_replay(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Retained replay attempted a native or model call')

    for name in ('socket.create_connection', 'socket.socket.connect', 'socket.socket.connect_ex',
            'urllib.request.OpenerDirector.open', 'subprocess.run', 'subprocess.Popen',
            'gene_annotation_episode.runtime.DecisionSource.call',
            'gene_annotation_episode.runtime.DecisionSource.exchange_decision',
            'gene_annotation_episode.providers.ModelConnection.complete',
            'gene_annotation_episode.providers._SessionConnection.complete'):
        monkeypatch.setattr(name, forbidden)
    native = NativeClient()
    for name in ('rpc', 'task_info', 'download'):
        monkeypatch.setattr(native, name, forbidden)
    original = json.loads((RUN / 'SOURCE_PROVENANCE.json').read_text())
    before = _source_provenance(original['files'])
    changed = [path for path, old in original['files'].items() if before['files'][path] != old]
    assert changed == [str(ROOT / 'tests/test_bvbrc_homology_pairwise_workflow.py')]
    _write(EVIDENCE / 'focused-replay-source-provenance.json', {
        'original_full_run_source_manifest': str(RUN / 'SOURCE_PROVENANCE.json'),
        'changed_original_files': changed,
        'reason': 'Only the verification harness changed: exact host versus Workflow replay comparison and explicit original source-file set.',
        'current': before, 'verification_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})

    body = json.loads((RUN / 'publication.json').read_text())
    config = deepcopy(CONFIG)
    config['scientific_adapters'] = [{'adapter_id': 'bvbrc_homology', 'adapter_version': '1',
        'implementation_sha256': body['publication_inputs']['adapter_implementation_sha256']}]
    with Store(RUN / 'state') as store:
        api = APIServiceExecution(store, run_id=body['run_id'], directory=RUN / 'run',
            configuration={'selected-api': config}, tool_registry=ToolRegistry(store, clients=Client()),
            handoff_unit=2, acquired_record_unit=3)
        api.services['selected-api'].client = native
        source_count = store.count('source')
        run = SimpleNamespace(api=api, store=store, native=native, body=body,
            final_ref=body['source_ref'], scope=body['scope'],
            results={'episode_id': body['episode_id']}, directory=RUN,
            returned=json.loads((RUN / 'results-return.json').read_text()),
            sheet=json.loads((RUN / 'sheet.json').read_text()),
            components=json.loads((RUN / 'components.json').read_text()))
        _assert_saved_pairwise_recalculation_and_replay(run)
        assert store.count('source') == source_count
        assert native.calls == []
    after = _source_provenance(before['files'])
    assert after['files'] == before['files']
    _write(EVIDENCE / 'focused-replay-source-provenance-after.json', after)
