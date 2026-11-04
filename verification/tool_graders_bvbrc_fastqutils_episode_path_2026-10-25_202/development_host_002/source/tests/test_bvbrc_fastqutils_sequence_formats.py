"""Handcrafted FASTQ format fixtures, not service execution claims."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_fastqutils_contracts import FastqUtilsContractError
from gene_annotation_episode.bvbrc_fastqutils_fastq_reader import parse_fastq


def context(raw, fmt="fastq", name="reads.fastq", document="reads", scope="complete"):
    return dict(analysis_id="example",document_id=document,task_ref="receipt:submit",
        content=dict(source_ref="receipt:download",artifact_field="artifact_ref",artifact_ref="artifact:"+document,
                     sha256=hashlib.sha256(raw).hexdigest(),byte_count=len(raw)),
        native_name=name,declared_format=fmt,producer_version=None,transfer_scope=scope,
        identity="handcrafted_synthetic")


def value(doc,metric,label=None):
    rows=[r for r in doc["cells"] if r["metric"]==metric and (label is None or r["axis"]["label"]==label)]
    assert len(rows)==1
    return rows[0]["value"]


def test_multiline_quality_at_and_numerical_counts():
    raw=b"@one description\nAC\nGTNRY\n+one description\n@@@\nIIII\n@two\nG\n+\n!\n"
    result=parse_fastq(raw,context=context(raw))
    assert result["parse_scope"]=="complete"
    assert [r["sequence"] for r in result["sequence_records"]]==["ACGTNRY","G"]
    assert result["sequence_records"][0]["quality_symbols"]=="@@@IIII"
    assert result["sequence_records"][0]["phred_values"] is None
    assert value(result,"fastq_read_count")==2
    assert value(result,"fastq_base_count")==8
    assert value(result,"fastq_symbol_count","other_iupac")==2
    assert value(result,"quality_character_count","@")==3
    assert all(p["association_ref"] is None for p in result["populations"])
    assert all(p["quality_encoding"]=="unknown" for p in result["populations"])


def test_no_quality_resynchronization_at_at_sign():
    raw=b"@good\nA\n+\n!\n@broken\nACGTACGT\n+\n!\n@looks_like_title\nACGT\n+\n!!!!\n"
    result=parse_fastq(raw,context=context(raw))
    assert len(result["sequence_records"])==1
    assert result["parse_scope"]=="partial"
    assert value(result,"fastq_read_count")==1
    assert all(p["scope"]=="partial" for p in result["populations"])
    assert result["raw_blocks"]


def test_plain_gzip_name_concatenated_gzip_and_truncated_member():
    one=b"@one\nA\n+\n!\n"
    two=b"@two\nGC\n+\nII\n"
    plain=parse_fastq(one,context=context(one,name="false.fq.gz"))
    assert plain["artifact"]["compression"]=="none"
    assert "compression_suffix_mismatch" in [d["code"] for d in plain["diagnostics"]]
    raw=gzip.compress(one,mtime=0)+gzip.compress(two,mtime=0)
    result=parse_fastq(raw,context=context(raw,name="no_suffix"))
    assert result["artifact"]["compression"]=="gzip"
    assert value(result,"fastq_read_count")==2
    truncated=raw[:-5]
    partial=parse_fastq(truncated,context=context(truncated))
    assert partial["parse_scope"]=="partial"
    assert value(partial,"fastq_read_count")>=1
    assert "truncated_compressed_stream" in [d["code"] for d in partial["diagnostics"]]
    corrupted=bytearray(raw); corrupted[-8]^=1
    bad=parse_fastq(bytes(corrupted),context=context(bytes(corrupted)))
    assert bad["parse_scope"]=="partial"
    assert bad["sequence_records"][0]["title"]=="one"


def test_empty_complete_invalid_symbols_and_invalid_quality():
    result=parse_fastq(b"",context=context(b""))
    assert value(result,"fastq_read_count")==value(result,"fastq_base_count")==0
    assert value(result,"fastq_min_length") is None
    assert result["parse_scope"]=="complete"
    raw=b"@bad\nAcgtnryZ?\n+\n!!!! !!!!\n"
    result=parse_fastq(raw,context=context(raw))
    assert value(result,"fastq_symbol_count","invalid")==2
    assert result["sequence_records"][0]["sequence"]=="AcgtnryZ?"
    assert {"invalid_sequence_symbol","invalid_quality_score"} <= {d["code"] for d in result["diagnostics"]}


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


def test_known_separator_conflict_retains_following_record():
    raw=b"@bad\nAC\n+wrong\n!!\n@good\nG\n+\nI\n"
    result=parse_fastq(raw,context=context(raw))
    assert result["parse_scope"]=="partial"
    assert [r["title"] for r in result["sequence_records"]]==["good"]
    assert result["sequence_records"][0]["ordinal"]==1


def test_null_name_and_caller_version_do_not_invent_native_producer():
    raw=b"@r\nA\n+\n!\n"
    supplied=context(raw,name=None)
    supplied["producer_version"]="assumed-version"
    result=parse_fastq(raw,context=supplied)
    assert result["artifact"]["native_name"] is None
    assert result["artifact"]["producer_version"] is None
    assert result["labels"][0]["value"]=="assumed-version"
    assert "producer_version_unproven" in {r["code"] for r in result["diagnostics"]}


def test_retained_handcrafted_sequence_fixture_bytes():
    directory=Path(__file__).parent/"fixtures/bvbrc_fastqutils/sequence"
    for name,count,scope in (("multiline.fastq",2,"complete"),("empty.fastq",0,"complete"),
                             ("concatenated.fastq.gz",2,"complete"),("truncated.fastq.gz",2,"partial")):
        raw=(directory/name).read_bytes()
        document=parse_fastq(raw,context=context(raw,name=name))
        assert value(document,"fastq_read_count")==count
        assert document["parse_scope"]==scope
