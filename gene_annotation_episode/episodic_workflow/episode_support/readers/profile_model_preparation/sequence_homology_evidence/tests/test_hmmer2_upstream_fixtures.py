"""Opt-in one-time capture of three original HMMER2 distribution assets.

This is selected upstream-file acquisition and parser verification, not a new
HMMER execution, calibration or publication of Store Sources/Artifacts. Every
response or failure is checkpointed before native-format assertions.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import urllib.request

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients
from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.hmmer_model_data import extract_hmmer_models
from gene_annotation_episode.episodic_workflow.episode_support.tools.profile_model_preparation.hmmer_model_binary2 import MAGIC


GATE = "HMMER_NATIVE_ORACLE_HMMER2_UPSTREAM_JSON"
ASSETS = [
    ("fn3-bin", "https://sources.debian.org/data/main/h/hmmer/2.3.2-5/testsuite/fn3-bin", 16930, "hmmer_binary"),
    ("fn3-bin-swap", "https://sources.debian.org/data/main/h/hmmer/2.3.2-5/testsuite/fn3-bin-swap", 16930, "hmmer_binary"),
    ("rrm.hmm", "https://sources.debian.org/data/main/h/hmmer/2.3.2-5/tutorial/rrm.hmm", 29502, "hmmer2_ascii"),
]
MAX_BYTES = 65536
TIMEOUT = 30


def checkpoint(path, value):
    temporary = path.with_suffix(".pending.json")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=True, allow_nan=False)
        stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def semantic_model(record):
    """Copy decoded source fields, excluding physical byte order/unused slots."""
    def distribution(value):
        return None if value is None else {"symbols": value["symbols"],
            "cells": [{"probability": cell["probability"], "state": cell["state"]} for cell in value["cells"]]}
    return {"format_tag": record["format_tag"], "engine_text": record["engine_text"],
        "headers": record["headers"], "alphabet": record["alphabet"], "length": record["length"],
        "sequence_count": record["sequence_count"], "effective_sequence_count": record["effective_sequence_count"],
        "cutoffs": record["cutoffs"], "calibration": record["calibration"],
        "initial": {name: distribution(value) for name, value in record["initial"].items()},
        "positions": [{"position": row["position"], "annotations": row["annotations"],
            **{name: distribution(row[name]) for name in ("match", "insert", "transitions")}}
            for row in record["positions"]],
        "used_native_fields": [{key: field[key] for key in ("field", "value", "state")}
            for field in record["representation"]["native_fields"] if field["state"] != "unused"]}


def compare_native_pair(first, second):
    """Retain the distributed p1 conflict; upstream compared ASCII conversion."""
    left, right = semantic_model(first), semantic_model(second)
    assert {key: value for key, value in left.items() if key != "used_native_fields"} == {
        key: value for key, value in right.items() if key != "used_native_fields"}
    assert len(left["used_native_fields"]) == len(right["used_native_fields"])
    differences = [{"first": a, "second": b} for a, b in zip(
        left["used_native_fields"], right["used_native_fields"]) if a != b]
    assert differences == [{"first": {"field": "NULT.p1", "value": 0.9971505999565125, "state": "present"},
        "second": {"field": "NULT.p1", "value": 0.9971505403518677, "state": "present"}}]
    slots = [next(field for field in record["representation"]["native_fields"] if field["field"] == "NULT.p1")
        for record in (first, second)]
    assert [(field["byte_start"], field["byte_end"], field["raw_hex"]) for field in slots] == [
        (478, 482, "43457f3f"), (478, 482, "3f7f4542")]
    return differences


