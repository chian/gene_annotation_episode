"""Finish the three074 assertions using their actual retained Workflow results.

The original complete paths already passed permissions/accounting and closed
replay checks. Their numerical assertion incorrectly expected Operation inside
Components, instead of the Sheet. No native job or Workflow is rerun here.
"""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.sequence_masking_contracts import validate_sequence_masking_record
from test_native_blast_masking_workflow import assert_selected_numbers


@pytest.mark.parametrize('program', ('dustmasker', 'segmasker', 'windowmasker'))
def test_actual_saved_workflow_measurements_equal_shared_components(program, monkeypatch):
    root = Path(os.environ['HMMER_NATIVE_ORACLE_MASKING_CASES'])
    directory = root / (program + '-mask0')
    saved = json.loads((directory / 'CASE.json').read_text())
    body = saved['result']['result']
    assert saved['program'] == program and saved['mode'] == 'mask'
    assert body['complete'] and body['status']['state'] == 'complete'
    assert saved['forwarded'] == {key: saved['returned'][key] for key in ('status','quantities','statistics')}
    assert not Path(body['target']['execution_id']).exists()
    def forbidden(*args, **kwargs):
        raise AssertionError('saved assertion reran original native work or numerical calculation')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr('gene_annotation_episode.sequence_masking_calculations.calculate_sequence_masking_components', forbidden)
    def read_artifact(reference):
        assert reference.startswith('artifact_')
        digest = reference.removeprefix('artifact_')
        raw = (directory / 'state/artifacts' / digest[:2] / digest).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest
        return raw
    prepared = body['prepared']
    validate_sequence_masking_record('SequenceMaskingSheet',json.loads(read_artifact(prepared['sheet_artifact_ref'])))
    validate_sequence_masking_record('SequenceMaskingComponents',json.loads(read_artifact(prepared['calculations_artifact_ref'])))
    assert_selected_numbers(body['target']['assignment']['requested_job']['native_blast_masking'],
        body, saved['returned'], read_artifact)
