"""Legacy publication consumes common Infernal values without native execution.

These controlled publication fixtures select the first retained native hit and
replace its target name with the temporary Store subject. Numerical native
cells are unchanged; this does not claim a newly executed one-target search.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode import infernal_search_grader, rna_evidence
from gene_annotation_episode.infernal_search_contracts import sheet_digest
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


NATIVE = Path(__file__).parent / "fixtures/native_infernal_result_worker/cmsearch"


def prepared_case(store):
    first = (NATIVE / "inputs/sequences.fa").read_text().split(">")[1].splitlines()
    sequence = "".join(first[1:])
    subject = store.create_problem(raw_sequence=sequence, molecule="rna")["subject_refs"][0]
    # The native fixture searches two models. This legacy invocation accepts
    # one model, so retain its first complete CM/filter record only.
    model_bytes = (NATIVE / "inputs/models.cm").read_bytes().split(b"\nINFERNAL1/", 1)[0] + b"\n"
    header = rna_evidence.model_header(model_bytes)
    source = store.put("source", {"provider": "fixture_native_model", "accession": None,
        "uri": None, "artifact_ref": store.artifact(model_bytes), "text_ref": None,
        "request_ref": None, "version": None, "retrieved_at": None}, origin="tool")
    model = store.put("reference", {"reference_type": "family", "source_ref": source["id"],
        "accession": header["name"], "label": header["name"], "sequence_ref": None,
        "molecule": None, "length": None, "term_refs": [], "context_refs": []}, origin="tool")
    original = (NATIVE / "hits.tblout").read_text().splitlines()
    rows = [line.replace(first[0], subject, 1) for line in original
        if line.startswith("#") or line.split()[:1] == [first[0]]]
    table = ("\n".join(rows) + "\n").encode()
    metadata = {"native_version": "1.1.5", "returncode": 0,
        "model_header": header, "target_length": len(sequence),
        "target_sequence_sha256": hashlib.sha256(sequence.encode()).hexdigest(),
        "model_sha256": hashlib.sha256(model_bytes).hexdigest(), "settings": {},
        "configuration": {}, "native_limitations": ["synthetic_selected_hit_and_target_identity"],
        "native_roles": {"query": "covariance_model", "target": "submitted_sequence"},
        "no_hit_meaning": "no_reported_match_under_recorded_search_settings_not_organism_absence"}
    native = rna_evidence.NativeSearch(metadata, b"controlled publication fixture\n", b"", table,
        f">{subject}\n{sequence}\n".encode(), b"")
    return {"subject_ref": subject, "model_ref": model["id"]}, native


def saved_grading(store, source_ref):
    source = store.get(source_ref)
    envelope, = [json.loads(store.get_artifact(ref)) for ref in source["auxiliary_artifact_refs"]]
    return envelope["grading"]


def test_cmsearch_publication_has_one_common_calculation_and_saved_recalculation(tmp_path, monkeypatch):
    with Store(tmp_path / "state") as store:
        args, native = prepared_case(store)
        calculate = infernal_search_grader.calculate_infernal_search_scores
        calls = []

        def tracked(sheet, *, parameters=None):
            calls.append(sheet)
            return calculate(sheet, parameters=parameters)

        def forbidden(*args, **kwargs):
            raise AssertionError("publication attempted legacy parsing, native work or acquisition")

        monkeypatch.setattr(infernal_search_grader, "calculate_infernal_search_scores", tracked)
        monkeypatch.setattr(rna_evidence, "iter_fmt3", forbidden)
        registry = ToolRegistry(store)

        async def captured_completion(selected, scope):
            assert selected == args
            return native

        monkeypatch.setattr(registry, "_native_cmsearch_async", captured_completion)
        outcome = registry.execute("rna.cmsearch", args, operation_key="controlled-captured-result")
        assert outcome["status"] == "completed", outcome
        result, refs = outcome["result"], outcome["record_refs"]
        assert len(calls) == 1 and result["reported_hit_count"] == 1
        assert store.count("observation") == 1 and len(refs) == 2
        assert registry.execute("rna.cmsearch", args, operation_key="controlled-captured-result") == outcome
        assert len(calls) == 1
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 1
        grading = saved_grading(store, result["source_ref"])
        sheet, scores = grading["sheet"], grading["scores"]
        assert scores["sheet_digest"] == sheet_digest(sheet)
        hit = scores["hits"][0]
        observation = store.get(result["records"][0]["observation_ref"])
        measurements = {row["name"]: row["value"].get("value") for row in observation["measurements"]}
        assert measurements["bitscore"] == hit["components"]["bitscore"] == 71.4
        assert measurements["evalue"] == hit["components"]["evalue"] == 3.6e-22
        assert measurements["query_coverage"] == hit["components"]["sequence_span_fraction"] == 1
        assert [measurements["query_start"], measurements["query_end"]] == hit["sequence_interval"] == [0, 72]
        assert observation["native_cmsearch"]["model_consensus_interval"] == hit["model_interval"]
        assert store.get_artifact(result["raw_artifacts"]["table_ref"]) == native.table
        monkeypatch.setattr(Path, "open", forbidden)
        assert calculate(sheet, parameters=scores["parameters"]) == scores


def test_malformed_trailing_row_preserves_shared_sheet_and_valid_observation(tmp_path, monkeypatch):
    with Store(tmp_path / "state") as store:
        args, native = prepared_case(store)
        native = replace(native, table=native.table + b"invalid trailing synthetic parser fixture\n")
        registry = ToolRegistry(store)

        async def captured_completion(selected, scope):
            assert selected == args
            return native

        monkeypatch.setattr(registry, "_native_cmsearch_async", captured_completion)
        outcome = registry.execute("rna.cmsearch", args, operation_key="controlled-malformed-result")
        assert outcome["status"] == "partial", outcome
        assert outcome["feedback"]["code"] == "invalid_cmsearch_fmt3_row"
        observation, = store.list("observation")
        grading = saved_grading(store, observation["source_ref"])
        assert grading["sheet"]["status"] == "partial"
        assert grading["scores"]["hits"][0]["components"]["bitscore"] == 71.4
        assert any(row["status"] == "invalid" for row in grading["sheet"]["artifacts"][0]["rows"])
        assert observation["native_cmsearch"]["native_target_subject_ref"] == args["subject_ref"]
