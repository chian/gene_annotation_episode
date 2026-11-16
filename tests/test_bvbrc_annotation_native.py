"""Engineered GTO byte controls, not BV-BRC task/deployment evidence.

The descriptor names below are syntactic metadata for this pure reader. These
tests mint no Store Source, grant, original task, native producer or observation.
"""
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode.episodic_workflow.root.library import bvbrc_annotation_native as native
def gto():
    return {"id": "900.1", "scientific_name": "engineered annotation fixture",
        "domain": "Viruses", "genetic_code": 11,
        "contigs": [{"id": "c", "original_id": "original c", "dna": "ACGTACGT"}],
        "features": [{"id": "f", "type": "mat_peptide",
            "location": [["c", "2", "+", 3], ["c", 8, "-", 2]],
            "protein_translation": "M*", "function": "native label",
            "quality": {"truncated_begin": 0, "truncated_end": 1},
            "annotations": [["native annotation", "native annotator", 0, "event"]],
            "feature_creation_event": "event"}],
        "analysis_events": [{"id": "event", "tool_name": "VIGOR4",
            "success": 0, "parameters": "native scalar parameters"}],
        "job_metadata": {"task_id": "engineered-task"}}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


