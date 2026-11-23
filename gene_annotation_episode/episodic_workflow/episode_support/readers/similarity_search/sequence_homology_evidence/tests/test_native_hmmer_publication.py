"""Captured native outputs plus explicitly synthetic Store bindings/faults.

These tests execute the bounded deterministic grading worker, not HMMER or an
episode. Real native search receipts belong to the existing producer fixtures.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.hmmer_native_result_views import NATIVE_HMMER_METRICS, family_for_program
from gene_annotation_episode.state import Store


# The grading worker is a new local job of this test, so it uses the current worker bound.


def selector(program, *, offset=0, limit=100, keys=None, metrics=None):
    family = family_for_program(program)
    return {"version": "native_hmmer_result_selector", "acquisition": "complete_bound_bundle",
        "projection": {"family": family, "rows": {"record_keys": keys} if keys is not None else
            {"offset": offset, "limit": limit}, "metrics": list(metrics or NATIVE_HMMER_METRICS[family])}}


def source(store, prepared):
    return store.put("source", {"provider": "episode.execution_result", "accession": None,
        "uri": None, "artifact_ref": prepared["bundle_artifact_ref"], "text_ref": None,
        "request_ref": None, "version": "native_hmmer_result", "retrieved_at": None,
        "auxiliary_artifact_refs": [prepared["source_grading_artifact_ref"]]}, origin="tool")


