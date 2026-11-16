"""Local source-investigation regressions; synthetic protocol, no network/model.

Evidence sequences remain evidence. No fixture is an actual biological result.
"""
import json

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry


def source(store):
    raw = store.artifact("SYNTHETIC source-investigation fixture; not public experimental evidence", "text/plain")
    return store.put("source", {"provider": "synthetic_fixture", "accession": None, "uri": None,
        "artifact_ref": raw, "text_ref": raw, "request_ref": None, "version": "fixture1", "retrieved_at": None}, origin="caller")


def reference(store, accession, sequence, molecule="protein"):
    return store.put("reference", {"reference_type": molecule, "source_ref": source(store)["id"],
        "accession": accession, "label": accession, "sequence_ref": store.artifact(sequence),
        "molecule": molecule, "length": len(sequence), "term_refs": [], "context_refs": []}, origin="external")


class SyntheticProtocol:
    ncbi_email = None
    job = "81bddc6e-f6ef-4f16-a8c1-32d262016ccb"
    def __init__(self):
        self.submissions, self.queries, self.blast_calls = 0, [], []

    def snapshot(self, body, request=None):
        return SourceSnapshot("ebi_hmmer", "https://example.invalid/synthetic-protocol", request or {},
            "2026-10-19T23:57:06+00:00", json.dumps(body).encode(), "application/json",
            {"representation": "synthetic_protocol_fixture_no_network"})

    def hmmer_submit(self, query_fasta, **kwargs):
        self.submissions += 1
        self.queries.append(query_fasta)
        return self.snapshot({"id": self.job})

    def hmmer_status(self, job_id):
        assert job_id == self.job
        return self.snapshot({"task": {"status": "SUCCESS"}, "algo": "phmmer",
            "database": {"id": "swissprot", "version": "synthetic_release"}})

    def hmmer_result(self, job_id, **kwargs):
        assert job_id == self.job
        return self.snapshot({"status": "SUCCESS", "page_count": 2, "result": {
            "stats": {"algo": "phmmer", "database": "swissprot", "nhits": 1},
            "hits": [{"index": 0, "name": "synthetic_hit", "acc": "synthetic_hit", "score": 24., "evalue": .001,
                "metadata": {"accession": "synthetic_hit", "description": "synthetic source label"},
                "domains": [{"bitscore": 23., "ievalue": .002,
                    "alignment_display": {"hmmfrom": 2, "hmmto": 7, "m": 8, "sqfrom": 4,
                        "sqto": 9, "l": 12, "identity": [.5, 3]}}]}]}})

    def blast(self, action, **kwargs):
        from dataclasses import replace
        self.blast_calls.append({"action": action, **kwargs})
        if action == "submit":
            self.blast_subject = kwargs["query_fasta"].splitlines()[0][1:]
            return replace(self.snapshot({}), content=b"RID = SYNTHETIC_RID\nRTOE = 0\n")
        if action == "status":
            return replace(self.snapshot({}), content=b"Status=READY\nThereAreHits=no\n")
        return self.snapshot({"BlastOutput2": [{"report": {"program": "blastp",
            "results": {"search": {"query_title": self.blast_subject, "query_len": 8, "hits": []}}}}]})


def test_native_reference_prediction_keeps_external_ancestry_and_source_only_account_exports(tmp_path):
    with Store(tmp_path / "db") as store:
        initial = store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        dna = reference(store, "synthetic_reference_genome", "ATG" + "AAA" * 100 + "TAA", "dna")
        registry = ToolRegistry(store, clients=SyntheticProtocol())
        predicted = registry.execute("genes.predict", {"subject_ref": dna["id"], "code": 11, "mode": "meta"})
        assert predicted["status"] == "completed", predicted
        product = store.get(predicted["result"]["records"][0]["product_ref"])
        h = store.put("hypothesis", {"subject_refs": [product["id"]], "predicate": "biological_role",
            "value": {"type": "enum", "value": "unknown"}, "context_refs": []}, origin="reasoning")
        account = store.put("annotation", {"subject_ref": product["id"], "footprint_kind": "localized",
            "coherent_sets": [{"interpretations": [{"hypothesis_ref": h["id"], "disposition": "unresolved", "assessment_refs": []}],
                "context_refs": []}], "alternative_refs": [], "resolution": "unresolved", "expected_revision": 0}, origin="reasoning")
        assert account["footprint"] == product["footprint"] == []
        exported = export_annotation(store, tmp_path / "external.annotation.json", include_credit=True)
        document = json.loads((tmp_path / "external.annotation.json").read_text())
        records = {row["id"]: row for row in document["records"]}
        assert records[product["id"]]["mapping"] == product["mapping"]
        assert records[dna["id"]]["source_ref"] == dna["source_ref"]
        assert account["id"] in document["membership"]["source_only_record_refs"]
        assert document["credit_projection"]["credit"] == 0
        assert store.problem() == initial
        assert exported["status"] == "completed"


def test_missing_sequence_is_capability_feedback_and_reference_cannot_become_target(tmp_path):
    with Store(tmp_path / "db") as store:
        store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        external = store.put("reference", {"reference_type": "family", "source_ref": source(store)["id"],
            "accession": "synthetic_family", "label": "synthetic family", "sequence_ref": None,
            "molecule": None, "length": None, "term_refs": [], "context_refs": []}, origin="external")
        result = ToolRegistry(store, clients=SyntheticProtocol()).execute("sequence.inspect", {"subject_ref": external["id"]})
        assert result["status"] == "invalid"
        assert result["feedback"]["code"] == "referenced_record_has_no_sequence"
        with pytest.raises(ContractError, match="unknown_or_empty_scope"):
            store.validate_scope({"subject_refs": [external["id"]]})


