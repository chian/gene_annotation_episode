"""Original HMMER result custody; these tests do not execute HMMER.

The complete native producer outputs are retained evidence. Relocated cases
explicitly build synthetic custody envelopes around copied native bytes; the
original reservation test separately opens a real producer reservation.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import socket
import subprocess

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.profile_model_preparation.sequence_homology_evidence import native_hmmer_preparation_acquisition as capture
from gene_annotation_episode.episodic_workflow.episode_support.forms.profile_model_preparation.sequence_homology_evidence.native_hmmer_preparation_contracts import PROGRAM_MODES
from gene_annotation_episode.episodic_workflow.episode_support.records.local_execution.native_record_identity import native_record_digest as digest
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.practical_execution_records import canonical
from gene_annotation_episode.state import Store


ROOT = Path(__file__).resolve().parents[7]
PREFIX = "native_hmmer_preparation_"


def forbidden(*args, **kwargs):
    raise AssertionError("capture must not run native work, grade, or reacquire on replay")


def read_native(plan_path):
    plan = json.loads(plan_path.read_bytes())
    bundle = json.loads((plan_path.parent / "hmmer-preparation-attempt/bundle.json").read_bytes())
    return plan, bundle


@pytest.mark.parametrize("value", [None, [], {}, {"resource_kind": []}, {"resource_kind": "api"},
    {"resource_kind": "local", "assignment": {"requested_job": {"native_infernal_preparation": {}}}}])
def test_recognizer_requires_exact_branch(value):
    assert capture.is_native_hmmer_preparation_target(value) is False

