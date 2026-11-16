"""Real Store/tools integration with synthetic sequences and remote protocol.

These checks establish source fidelity, mappings and action representation.
They make no network/model calls and establish no biological classification,
functional annotation accuracy or production-controller stopping behavior.
"""
from __future__ import annotations

import json

import pytest

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry


class LocalOnly:
    ncbi_email = None
    access_dir = None

    def __getattr__(self, name):
        raise AssertionError(f"Unexpected external client access: {name}")


def product_from_response(store, response):
    assert response["status"] == "completed", response
    products = [row for ref in response["record_refs"]
                if (row := store.get(ref))["record_type"] == "product"]
    assert len(products) == 1, response
    return products[0]


def product_sequence(store, product):
    return store.get_artifact(product["sequence_ref"]).decode("ascii")


def pinned_rna_reference(store, sequence="AUGC"):
    """Construct source material locally; no public/empirical evidence is claimed."""
    source = store.put("source", {"provider": "synthetic_sequence_view_fixture",
        "accession": None, "uri": None, "artifact_ref": store.artifact(sequence),
        "text_ref": None, "request_ref": None, "version": "synthetic_fixture",
        "retrieved_at": None}, origin="external")
    return store.put("reference", {"reference_type": "rna", "source_ref": source["id"],
        "accession": "SYNTHETIC_RNA_VIEW_001", "label": "Synthetic RNA sequence",
        "sequence_ref": store.artifact(sequence), "molecule": "rna", "length": len(sequence),
        "term_refs": [], "context_refs": []}, origin="external")


def test_negative_rna_feature_view_preserves_rna_letters_without_double_reversal(tmp_path):
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence="AUGC", molecule="rna")["subject_refs"][0]
        feature = store.put("feature", {"subject_ref": target, "kind": "sequence_region",
            "segments": [{"start": 0, "end": 4}], "strand": "-", "context_refs": []}, origin="reasoning")
        tools = ToolRegistry(store, clients=LocalOnly())
        viewed = product_from_response(store, tools.execute("sequence.view", {
            "subject_ref": feature["id"], "molecule": "rna"}, operation_key="oriented-rna-view"))
        assert product_sequence(store, viewed) == "GCAU"
        assert store.sequence_mapping(viewed["id"])["path"] == [{
            "subject_ref": target, "start": 0, "end": 4, "unit": "nt", "strand": "-"}]
        assert store.get_artifact(store.get_input(target)["sequence_ref"]) == b"AUGC"


