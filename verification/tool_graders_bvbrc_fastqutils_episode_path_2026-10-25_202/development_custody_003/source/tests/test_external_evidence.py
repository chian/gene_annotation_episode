"""Local source-investigation regressions; synthetic protocol, no network/model.

Evidence sequences remain evidence. No fixture is an actual biological result.
"""
import json

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


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


def test_external_pair_comparison_and_site_inspection_preserve_both_identities(tmp_path):
    with Store(tmp_path / "db") as store:
        initial = store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        a, b = reference(store, "synthetic_A", "MACDEFGH"), reference(store, "synthetic_B", "MACDFFGH")
        registry = ToolRegistry(store, clients=SyntheticProtocol())
        inspection = registry.execute("sequence.inspect", {"subject_ref": a["id"]})
        assert inspection["status"] == "completed", inspection
        alignment = registry.execute("sequence.align", {"query_ref": a["id"], "reference_ref": b["id"],
            "molecule": "protein", "mode": "global"})
        assert alignment["status"] == "completed", alignment
        observation = store.get(alignment["result"]["observation_ref"])
        assert observation["subject_refs"] == [a["id"]]
        assert observation["source_subject_refs"] == [b["id"]]
        assert observation["dependencies"] == [a["id"], b["id"]]
        assert {row["subject_ref"] for row in observation["operand_intervals"]} == {a["id"], b["id"]}
        sites = registry.execute("sequence.sites", {"alignment_ref": observation["id"], "positions": [1, 4]})
        assert sites["status"] == "completed", sites
        assert [row["relationship"] for row in sites["result"]["sites"]] == ["identical", "substituted"]
        measured = store.get(sites["result"]["observation_ref"])
        assert len(measured["operand_intervals"]) == 4
        assert all(row["end"] - row["start"] == 1 for row in measured["operand_intervals"])
        assert registry.execute("state.query", {"refs": [observation["id"]]})["result"]["records"] == [observation]
        assert store.problem() == initial
        assert store.roots(a["id"]) == store.coverage(a["id"]) == []
        assert project_credit(store).credit == 0


def test_external_search_resume_pages_and_jobs_share_actual_query_without_new_targets(tmp_path):
    with Store(tmp_path / "db") as store:
        initial = store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        external = reference(store, "synthetic_query", "MACDEFGH")
        client = SyntheticProtocol()
        registry = ToolRegistry(store, clients=client, provider_poll_interval_seconds=0)
        from api_execution_fixture import APIHarness
        owner = APIHarness(registry, subject_ref=external['id'], page_size=1)
        handoff = owner.handoff()
        first_receiver = owner.results(handoff)
        first = first_receiver.act('api.hmmer.result')
        assert first['status'] == 'completed', first
        page = owner.results(handoff, page=2, episode_id='page-two').act('api.hmmer.result')
        collected = first_receiver.act('api.hmmer.result', index=0)
        jobs = registry.execute('public.search.jobs', {'active_only': False})
        for result in (page, collected, jobs):
            assert result['status'] == 'completed', result
        assert client.submissions == 1
        assert client.queries == [">" + external["id"] + "\nMACDEFGH"]
        assert jobs["result"]["jobs"][0]["request"]["subject_ref"] == external["id"]
        for observation in store.list("observation"):
            assert observation["subject_refs"] == [external["id"]]
            assert all(row["subject_ref"] == external["id"] for row in observation["operand_intervals"])
        blast = registry.execute("public.blast.search", {"subject_ref": external["id"], "program": "blastp", "database": "swissprot"})
        assert blast["status"] == "completed", blast
        assert registry.execute("public.blast.collect", {"job_ref": blast["result"]["job_ref"]})["status"] == "completed"
        assert client.blast_calls[0]["query_fasta"] == ">" + external["id"] + "\nMACDEFGH"
        assert store.problem() == initial
        assert project_credit(store).credit == 0


@pytest.mark.parametrize("strand,expected", [("+", "MKG"), ("-", "LPFH")])
def test_reference_gene_model_translation_preserves_external_source_coordinates(tmp_path, strand, expected):
    with Store(tmp_path / "db") as store:
        initial = store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        external = reference(store, "synthetic_DNA", "ATGAAAGGGTAA", "dna")
        registry = ToolRegistry(store, clients=SyntheticProtocol())
        args = {"subject_ref": external["id"], "code": 11, "strand": strand}
        if strand == "+":
            args["cds"] = True
        result = registry.execute("sequence.translate", args)
        assert result["status"] == "completed", result
        product = store.get(result["result"]["records"][0]["product_ref"])
        assert store.get_artifact(product["sequence_ref"]).decode() == expected
        assert product["footprint"] == []
        assert store.roots(product["id"]) == []
        assert all(row["subject_ref"] == external["id"] for row in product["mapping"]["path"])
        assert store.map_segments(product["id"], [{"start": 0, "end": 1}]) == []
        read = registry.execute("state.query", {"refs": [product["id"]]})
        assert read["status"] == "completed", read
        assert store.problem() == initial
        assert project_credit(store).credit == 0


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


def test_original_target_ownership_is_checked_before_running_native_derivation(tmp_path, monkeypatch):
    from gene_annotation_episode import tools as tool_module
    with Store(tmp_path / "db") as store:
        store.create_problem(raw_sequence="ATG" + "AAA" * 100 + "TAA", molecule="dna")
        target = store.targets()[0]["id"]
        scope = {"subject_refs": [target], "segments": [{"target_ref": target, "start": 0, "end": 9, "unit": "nt"}]}
        def forbidden(*args, **kwargs):
            pytest.fail("out-of-scope native prediction executed")
        monkeypatch.setattr(tool_module.ToolRegistry, "_sequence_worker_async", forbidden)
        result = ToolRegistry(store, clients=SyntheticProtocol()).execute("genes.predict",
            {"subject_ref": target, "code": 11, "mode": "meta"}, scope=scope)
        assert result["status"] == "invalid"
        assert result["feedback"]["code"] == "requested_measurement_outside_assigned_segments"
        assert not result["record_refs"]
        assert not store.list("product")
