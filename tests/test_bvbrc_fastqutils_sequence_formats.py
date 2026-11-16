"""Handcrafted FASTQ format fixtures, not service execution claims."""
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode.episodic_workflow.root.library.bvbrc_fastqutils_contracts import FastqUtilsContractError
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_fastqutils_fastq_reader import parse_fastq


def context(raw, fmt="fastq", name="reads.fastq", document="reads", scope="complete"):
    return dict(analysis_id="example",document_id=document,task_ref="receipt:submit",
        content=dict(source_ref="receipt:download",artifact_field="artifact_ref",artifact_ref="artifact:"+document,
                     sha256=hashlib.sha256(raw).hexdigest(),byte_count=len(raw)),
        native_name=name,declared_format=fmt,producer_version=None,transfer_scope=scope,
        identity="handcrafted_synthetic")


def test_binding_errors_and_stable_byte_bound_identities():
    raw=b"@a\nA\n+\n!\n"
    source=context(raw)
    before=deepcopy(source)
    first=parse_fastq(raw,context=source)
    assert source==before
    assert first==parse_fastq(raw,context=source)
    changed=b"@b\nA\n+\n!\n"
    second=parse_fastq(changed,context=context(changed))
    assert first["artifact"]["id"]!=second["artifact"]["id"]
    assert first["sequence_records"][0]["id"]!=second["sequence_records"][0]["id"]
    for mutation in (dict(sha256="0"*64),dict(byte_count=True),dict(byte_count=100)):
        bad=deepcopy(source); bad["content"].update(mutation)
        with pytest.raises(FastqUtilsContractError): parse_fastq(raw,context=bad)
    with pytest.raises(FastqUtilsContractError): parse_fastq("text",context=source)
    json.dumps(first,allow_nan=False)


