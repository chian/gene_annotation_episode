"""A1 supplied-byte reader tests: native259 fixtures plus explicit mutations."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.hmmer_model_data import extract_hmmer_models
from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.hmmer_artifact_data import populate_hmmer_artifact_sheet


ROOT = Path(__file__).resolve().parents[6]
FIXTURES = ROOT / "gene_annotation_episode/episodic_workflow/episode_support/readers/profile_model_preparation/tests/fixtures/hmmer_preparation_contracts"
NATIVE = FIXTURES / "native"


def payload(content, role, direction="input", ordinal=0, oid=None, completeness="complete"):
    oid = oid or direction + "/" + role + "/" + str(ordinal)
    return {"occurrence": {"occurrence_id": oid, "direction": direction, "role": role, "ordinal": ordinal,
        "artifact_ref": "retained:" + oid, "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content), "completeness": completeness}, "content": content}


def model_format(content):
    if content.startswith(b"HMMER2"):
        return "hmmer2_ascii"
    return "hmmer3_ascii" if not content or content.startswith(b"HMMER3") else "hmmer_binary"


def populate(operation, inputs, outputs, bindings=None):
    extractions = [extract_hmmer_models(p["content"], occurrence=p["occurrence"], format=model_format(p["content"]))
        for mapping in (inputs, outputs) for role, values in mapping.items()
        if role in {"models", "converted_models", "fetched_models", "binary_models"} for p in values]
    return populate_hmmer_artifact_sheet(operation=operation, inputs=inputs, outputs=outputs,
        model_extractions=extractions, artifact_bindings=bindings)


def issues(sheet):
    return {issue["code"] for issue in sheet["issues"]}

