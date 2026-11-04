"""Real Store/tools integration with synthetic sequences and remote protocol.

These checks establish source fidelity, mappings and action representation.
They make no network/model calls and establish no biological classification,
functional annotation accuracy or production-controller stopping behavior.
"""
from __future__ import annotations

import json

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


class LocalOnly:
    ncbi_email = None

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


def assert_extraction_provenance(store, product, parent_ref):
    assert product["derivation"] == "extraction"
    # A tool can retain an explicit located extraction feature between the
    # product and requested operand. Inspect actual ancestry, not a summary ID.
    pending, ancestors = list(product["parent_refs"]), set()
    while pending:
        ref = pending.pop()
        if ref in ancestors:
            continue
        ancestors.add(ref)
        row = store.get(ref)
        if row["record_type"] == "feature":
            pending.append(row["subject_ref"])
        elif row["record_type"] == "product":
            pending.extend(row["parent_refs"])
    assert parent_ref in ancestors
    source = store.get(product["mapping_source_ref"])
    assert source["provider"] == "sequence.view" and source["origin"] == "tool"
    assert product["context_refs"]
    contexts = [store.get(ref) for ref in product["context_refs"]]
    processing = [context for context in contexts if context["record_type"] == "context"
                  and context["context_type"] == "processing" and context["source_ref"] == source["id"]]
    assert processing
    assert any(attribute == {"name": "molecule_model", "value": {"type": "enum", "value": product["molecule"]}}
               for context in processing for attribute in context["attributes"])
    return source


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


@pytest.mark.parametrize("segments,expected,start,end", [
    (None, "MKWVTFISLLFLFSSAYSRGVFRR", 0, 24),
    ([{"start": 2, "end": 6}], "WVTF", 2, 6),
])
def test_unknown_protein_views_preserve_caller_material_symbol_scope_and_replay(
        tmp_path, segments, expected, start, end):
    original_sequence = "MKWVTFISLLFLFSSAYSRGVFRR"
    with Store(tmp_path) as store:
        problem = store.create_problem(raw_sequence=original_sequence)
        target = problem["subject_refs"][0]
        original_input = store.get_input(target)
        original_raw = store.get_artifact(store.get(original_input["source_ref"])["artifact_ref"])
        tools = ToolRegistry(store, clients=LocalOnly())
        args = {"subject_ref": target, "molecule": "protein"}
        if segments is not None:
            args["segments"] = segments
        response = tools.execute("sequence.view", args, operation_key="same-view")
        product = product_from_response(store, response)
        assert product_sequence(store, product) == expected
        assert product["molecule"] == "protein"
        source = assert_extraction_provenance(store, product, target)
        native = json.loads(store.get_artifact(source["artifact_ref"]))
        assert native["molecule_model"] == "protein"
        assert native["molecule_assignment"] == "not_performed"
        mapping = store.sequence_mapping(product["id"])
        assert mapping["units_per_symbol"] == 1
        assert mapping["symbol_length"] == len(expected)
        assert mapping["path"] == [{"subject_ref": target, "start": start, "end": end,
                                    "unit": "symbol", "strand": "+"}]
        assert store.coverage(product["id"]) == [{"target_ref": target, "start": start,
                                                 "end": end, "unit": "symbol"}]
        counts = store.count("product"), store.count("source"), store.count("context")
        assert tools.execute("sequence.view", args, operation_key="same-view") == response
        assert counts == (store.count("product"), store.count("source"), store.count("context"))
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 1
        assert store.problem() == problem and store.get_input(target) == original_input
        assert original_input["molecule"] == "unspecified" and original_input["unit"] == "symbol"
        assert store.get_artifact(store.get(original_input["source_ref"])["artifact_ref"]) == original_raw
        assert store.get_artifact(original_input["sequence_ref"]).decode() == original_sequence
        assert not store.list("hypothesis") and not store.current_annotations()
        assert project_credit(store).credit == 0


def test_view_of_a_native_translation_retains_parent_scale_and_exact_original_bases(tmp_path):
    with Store(tmp_path) as store:
        problem = store.create_problem(raw_sequence="ATGGCTGGTCCCTAA", molecule="dna")
        target = problem["subject_refs"][0]
        tools = ToolRegistry(store, clients=LocalOnly())
        translated = product_from_response(store, tools.execute("sequence.translate",
            {"subject_ref": target, "code": 11}, operation_key="native-translation"))
        assert product_sequence(store, translated) == "MAGP*"
        response = tools.execute("sequence.view", {"subject_ref": translated["id"],
            "molecule": "protein", "segments": [{"start": 1, "end": 3}]},
            operation_key="two-residue-view")
        cropped = product_from_response(store, response)
        assert product_sequence(store, cropped) == "AG"
        assert_extraction_provenance(store, cropped, translated["id"])
        mapping = store.sequence_mapping(cropped["id"])
        assert mapping["units_per_symbol"] == 3 and mapping["symbol_length"] == 2
        assert mapping["path"] == [{"subject_ref": target, "start": 3, "end": 9,
                                    "unit": "nt", "strand": "+"}]
        assert store.coverage(cropped["id"]) == [{"target_ref": target, "start": 3,
                                                 "end": 9, "unit": "nt"}]
        assert product_sequence(store, translated) == "MAGP*"
        assert store.targets()[0]["id"] == target and store.targets()[0]["length"] == 15
        assert not store.current_annotations() and project_credit(store).credit == 0


def test_external_rna_reverse_view_retains_source_ancestry_without_a_credit_target(tmp_path):
    with Store(tmp_path) as store:
        problem = store.create_problem(raw_sequence="MACT", molecule="protein")
        targets = store.targets()
        reference = pinned_rna_reference(store)
        tools = ToolRegistry(store, clients=LocalOnly())
        viewed = product_from_response(store, tools.execute("sequence.view", {
            "subject_ref": reference["id"], "molecule": "rna", "orientation": "reverse_complement"},
            operation_key="external-rna-view"))
        assert product_sequence(store, viewed) == "GCAU"
        assert viewed["molecule"] == "rna"
        assert_extraction_provenance(store, viewed, reference["id"])
        assert store.sequence_mapping(viewed["id"])["path"] == [{
            "subject_ref": reference["id"], "start": 0, "end": 4, "unit": "nt", "strand": "-"}]
        assert store.roots(viewed["id"]) == []
        assert viewed["footprint"] == [] and store.coverage(viewed["id"]) == []
        assert store.get(reference["id"]) == reference
        assert store.get_artifact(reference["sequence_ref"]) == b"AUGC"
        assert store.targets() == targets and store.problem() == problem
        assert not store.list("hypothesis") and project_credit(store).credit == 0


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


def test_negative_protein_feature_returns_feedback_instead_of_dna_complemented_residues(tmp_path):
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence="MACT", molecule="protein")["subject_refs"][0]
        feature = store.put("feature", {"subject_ref": target, "kind": "protein_domain",
            "segments": [{"start": 0, "end": 4}], "strand": "-", "context_refs": []}, origin="reasoning")
        tools = ToolRegistry(store, clients=LocalOnly())
        response = tools.execute("sequence.view", {"subject_ref": feature["id"], "molecule": "protein"},
            operation_key="incompatible-complement")
        assert response["status"] == "invalid", response
        assert response["feedback"]["code"] == "protein_reverse_complement_undefined"
        assert response["record_refs"] == [] and not store.list("product")
        assert store.get_artifact(store.get_input(target)["sequence_ref"]) == b"MACT"
        assert not store.current_annotations() and project_credit(store).credit == 0


def test_unknown_negative_feature_needs_an_explicit_processing_model(tmp_path):
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence="AUGC")["subject_refs"][0]
        original = store.get_input(target)
        feature = store.put("feature", {"subject_ref": target, "kind": "sequence_region",
            "segments": [{"start": 0, "end": 4}], "strand": "-", "context_refs": []}, origin="reasoning")
        tools = ToolRegistry(store, clients=LocalOnly())
        unknown = tools.execute("sequence.inspect", {"subject_ref": feature["id"]}, operation_key="unknown-orientation")
        assert unknown["status"] == "invalid", unknown
        assert unknown["feedback"]["code"] == "explicit_sequence_model_required"
        assert unknown["record_refs"] == []
        viewed = product_from_response(store, tools.execute("sequence.view", {
            "subject_ref": feature["id"], "molecule": "rna"}, operation_key="explicit-rna-orientation"))
        assert product_sequence(store, viewed) == "GCAU"
        assert store.get_input(target) == original and original["molecule"] == "unspecified"
        assert store.coverage(viewed["id"]) == [{"target_ref": target, "start": 0,
                                                "end": 4, "unit": "symbol"}]
        assert not store.list("hypothesis") and project_credit(store).credit == 0


class SyntheticHMMERProtocol:
    """Entirely local protocol responses; no acquired biological evidence."""
    ncbi_email = None
    job_id = "81bddc6e-f6ef-4f16-a8c1-32d262016ccb"

    def __init__(self):
        self.submissions = self.status_calls = self.result_calls = 0
        self.query_fasta = None

    def snapshot(self, body):
        return SourceSnapshot("ebi_hmmer", "https://fixture.invalid/hmmer/" + self.job_id,
            {}, "2026-10-20T01:00:00+00:00", json.dumps(body).encode(), "application/json",
            {"representation": "synthetic_native_protocol_fixture"})

    def hmmer_submit(self, query_fasta, **kwargs):
        self.submissions += 1
        self.query_fasta = query_fasta
        return self.snapshot({"id": self.job_id})

    def hmmer_status(self, job_id):
        assert job_id == self.job_id
        self.status_calls += 1
        return self.snapshot({"task": {"status": "SUCCESS"}, "algo": "phmmer",
            "database": {"id": "swissprot", "version": "synthetic_fixture"}, "input": self.query_fasta})

    def hmmer_result(self, job_id, **kwargs):
        assert job_id == self.job_id
        self.result_calls += 1
        length = len(self.query_fasta.splitlines()[1])
        return self.snapshot({"status": "SUCCESS", "page_count": 1, "result": {
            "stats": {"algo": "phmmer", "database": "swissprot", "nhits": 1},
            "hits": [{"index": 0, "name": "synthetic_native_hit", "acc": None,
                "score": 24., "evalue": .001,
                "metadata": {"accession": "SYNTHETIC_SEQUENCE_VIEW_001",
                    "uniprot_accession": "SYNTHETIC_SEQUENCE_VIEW_001", "description": "Synthetic protocol reference"},
                "domains": [{"bitscore": 23., "ievalue": .002, "alignment_display": {
                    "hmmfrom": 1, "hmmto": length, "m": length,
                    "sqfrom": 1, "sqto": length, "l": length, "identity": [1., length]}}]}]}})


def test_direct_unknown_protein_hmmer_is_one_ordinary_operation_without_an_identity_view(tmp_path):
    with Store(tmp_path) as store:
        sequence = "MACDEFGH"
        problem = store.create_problem(raw_sequence=sequence)
        target = problem["subject_refs"][0]
        original = store.get_input(target)
        client = SyntheticHMMERProtocol()
        tools = ToolRegistry(store, clients=client, provider_poll_interval_seconds=0)
        args = {"subject_ref": target, "algorithm": "phmmer", "database": "swissprot"}
        response = tools.execute("public.hmmer.search", args, operation_key="one-direct-search")
        assert response["status"] == "completed", response
        assert client.query_fasta.splitlines() == [">" + target, sequence]
        assert client.submissions == client.status_calls == client.result_calls == 1
        comparisons = [row for row in store.list("observation") if row["kind"] == "comparison"]
        assert len(comparisons) == 1 and comparisons[0]["subject_refs"] == [target]
        query_intervals = [row for row in comparisons[0]["operand_intervals"] if row["role"] == "query"]
        assert query_intervals == [{"role": "query", "subject_ref": target, "start": 0,
                                    "end": len(sequence), "unit": "symbol", "model_unit": "aa"}]
        source = store.get(comparisons[0]["source_ref"])
        request = json.loads(store.get_artifact(source["request_ref"]))["request"]
        assert request["molecule_model"] == "protein"
        assert request["molecule_assignment"] == "not_performed"
        assert not store.list("product") and not store.list("feature")
        assert not store.list("hypothesis") and not store.current_annotations()
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 1
        assert tools.execute("public.hmmer.search", args, operation_key="one-direct-search") == response
        assert client.submissions == client.status_calls == client.result_calls == 1
        assert store.get_input(target) == original and original["molecule"] == "unspecified"
        assert store.problem() == problem and project_credit(store).credit == 0
