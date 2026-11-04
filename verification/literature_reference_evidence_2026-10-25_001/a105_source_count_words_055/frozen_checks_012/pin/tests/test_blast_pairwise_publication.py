"""Retained real BLAST outputs through bounded grading and biological custody.

The twenty 294 native reports, coordinates and scores are never rewritten.
Store-binding fixtures explicitly replace placeholder subject handles in copied
manifests; they are publication tests, not proof of another native invocation.
298 owns actual selected Workflow execution and parent-return verification.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.blast_pairwise_result_views import NATIVE_BLAST_METRICS
from gene_annotation_episode.blast_pairwise_results import calculate_blast_pairwise_components
from gene_annotation_episode.domain import ContractError, canonical, parse_sequences
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.materials import artifact_file, artifact_path
from gene_annotation_episode.native_blast_acquisition import publish_original_source
from gene_annotation_episode.native_blast_contracts import native_blast_digest, requested_job_from_native
from gene_annotation_episode.native_blast_result_publication import (
    prepare_native_blast_grading, publish_selected_native_blast_rows, validate_native_blast_publication,
)
from gene_annotation_episode.state import Store


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "verification/tool_graders_blast_pairwise_2026-10-26_294"
EXAMPLES = sorted((NATIVE / "native_examples").glob("*/plan.json")) + sorted((NATIVE / "native_ranges").glob("*/plan.json"))
POLICY = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)


def selector(family="pairwise_hsp", metrics=None, rows=None):
    return {"version": "native_blast_result_selector_v1", "acquisition": "complete_bound_bundle",
        "projection": {"family": family, "metrics": metrics or list(NATIVE_BLAST_METRICS[family]),
                       "rows": rows or {"offset": 0, "limit": 20}}}


def native_path(label="blastp_gaps_json15"):
    return next(path for path in EXAMPLES if path.parent.name == label)


def fixture(tmp_path, label="blastp_gaps_json15", *, wrong_query=False, wrong_reference=False,
            omit_query=False, omit_reference=False, transform=None, missing_role=None):
    path = native_path(label)
    original = json.loads((path.parent / "attempt/bundle.json").read_bytes())
    bundle = deepcopy(original)
    store = Store(tmp_path / "store")
    operands = {row["role"]: row for row in bundle["inputs"]}
    molecules = {"query_sequence": "protein" if bundle["program"] in {"blastp", "tblastn"} else "dna",
                 "subject_sequence": "protein" if bundle["program"] in {"blastp", "blastx"} else "dna"}
    parsed = {role: parse_sequences((path.parent / "attempt" / row["relative_path"]).read_bytes(),
        format="fasta", molecule=molecules[role])[0] for role, row in operands.items()}
    query_sequence = parsed["query_sequence"].sequence
    if wrong_query:
        query_sequence = ("C" if query_sequence[0] != "C" else "A") + query_sequence[1:]
    subject = store.create_problem(raw_sequence=query_sequence, format="raw", molecule=molecules["query_sequence"])["subject_refs"][0]
    ref_sequence = parsed["subject_sequence"].sequence
    if wrong_reference:
        ref_sequence = ("C" if ref_sequence[0] != "C" else "A") + ref_sequence[1:]
    src = store._caller_source({"fixture": label}, "caller")
    reference = store.put("reference", {"reference_type": "protein" if molecules["subject_sequence"] == "protein" else "sequence",
        "source_ref": src["id"], "accession": parsed["subject_sequence"].name, "label": parsed["subject_sequence"].name,
        "sequence_ref": store.artifact(ref_sequence, "text/plain"), "molecule": molecules["subject_sequence"],
        "length": len(ref_sequence), "term_refs": [], "context_refs": []}, origin="caller")["id"]
    bindings = bundle["requested_job"]["native_blast"]["operand_bindings"]
    bindings[0]["subject_ref"] = None if omit_query else subject
    bindings[1]["reference_ref"] = None if omit_reference else reference
    bundle["requested_job"] = requested_job_from_native(bundle["requested_job"]["native_blast"])
    bundle["operand_bindings"] = deepcopy(bindings)
    bundle["identity"]["requested_job_sha256"] = native_blast_digest(bundle["requested_job"])
    content_overrides = {}
    if transform:
        transform(bundle, content_overrides)
    artifacts = []
    for row in bundle["inputs"] + bundle["artifacts"]:
        if row["role"] == missing_role:
            continue
        ref = (store.artifact(content_overrides[row["role"]]) if row["role"] in content_overrides else
               artifact_file(store, path.parent / "attempt" / row["relative_path"]))
        artifacts.append({key: row[key] for key in ("role", "format", "relative_path")} | {"artifact_ref": ref})
    bundle_ref = store.artifact(canonical(bundle), "application/json")
    capture = {"version": "native_blast_capture_v1", "bundle_artifact_ref": bundle_ref,
        "bundle_validated": True, "artifacts": artifacts, "invalid_artifacts": [],
        "failures": [], "complete": missing_role is None}
    return {"store": store, "bundle": bundle, "capture": capture, "scope": store.validate_scope(),
            "subject": subject, "reference": reference, "original": original}


def prepare(case, directory, selected):
    return prepare_native_blast_grading(case["store"], bundle=case["bundle"],
        bundle_artifact_ref=case["capture"]["bundle_artifact_ref"], artifacts=case["capture"]["artifacts"],
        directory=directory, policy=POLICY, selector=selected)


def publish(case, prepared, selected):
    source = publish_original_source(case["store"], bundle=case["bundle"], capture=case["capture"], prepared=prepared)
    result = publish_selected_native_blast_rows(case["store"], source_ref=source, bundle=case["bundle"],
        prepared=prepared, scope=case["scope"], selector=selected)
    return source, result


def values(row):
    return {value["name"]: value["value"] for value in row["measurements"]}


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda path: path.parent.name)
def test_twenty_native_examples_preserve_numerical_custody_and_recalculation(tmp_path, path, monkeypatch):
    case = fixture(tmp_path, path.parent.name)
    selected = selector(metrics=["paired_positions", "query_paired_coverage", "reference_paired_coverage", "native_score_bits"])
    prepared = prepare(case, tmp_path / "grading", selected)
    source, publication = publish(case, prepared, selected)
    (tmp_path / "filled-publication.json").write_text(json.dumps({"case": path.parent.name,
        "original_manifest": str(path.parent / "attempt/bundle.json"),
        "original_report_artifacts": case["original"]["artifacts"], "prepared": prepared,
        "publication": publication}, indent=2) + "\n")
    assert case["bundle"]["artifacts"] == case["original"]["artifacts"]
    sheet = json.loads(case["store"].get_artifact(prepared["sheet_artifact_ref"]))
    scores = json.loads(case["store"].get_artifact(prepared["scores_artifact_ref"]))
    for populated, calculated in zip(sheet["searches"], scores["searches"]):
        assert calculate_blast_pairwise_components(populated["sheet"]) == calculated["scores"]
    if not scores["rows"]["pairwise_hsp"]:
        assert publication["rows"] == []
        assert publication["record_refs"] == [source]
        assert prepared["numerical_complete"] is ("tabular6" not in path.parent.name)
    else:
        assert publication["rows"] and all(row["status"] == "published" for row in publication["rows"]), publication
        assert prepared["numerical_complete"], prepared["failures"]
        for row in publication["rows"]:
            observation = case["store"].get(row["observation_ref"])
            assert len(observation["measurements"]) > len(row["measurements"])
            assert observation["native_blast_pairwise"]["search_key"] == row["search_key"]
            assert "native_blast" not in observation
    def forbidden(*args, **kwargs):
        pytest.fail("frozen replay or saved calculation performed acquisition/process/calculation work")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_blast_result_worker.calculate_blast_pairwise_components", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_blast_result_worker.populate_blast_pairwise_sheet", forbidden)
    assert prepare(case, tmp_path / "grading", selected) == prepared
    monkeypatch.setattr(case["store"], "put", forbidden)
    monkeypatch.setattr(case["store"], "artifact", forbidden)
    assert validate_native_blast_publication(case["store"], source_ref=source, bundle=case["bundle"],
        prepared=prepared, scope=case["scope"], selector=selected, publication=publication) == publication
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    for populated, calculated in zip(sheet["searches"], scores["searches"]):
        assert calculate_blast_pairwise_components(populated["sheet"]) == calculated["scores"]


def test_known_gap_counts_and_original_denominators(tmp_path):
    case = fixture(tmp_path)
    selected = selector()
    prepared = prepare(case, tmp_path / "grading", selected)
    source, result = publish(case, prepared, selected)
    numbers = values(result["rows"][0])
    assert numbers == {"native_score_bits": 486.878, "native_raw_score": 1252, "native_evalue": 0,
        "alignment_columns": 253, "paired_positions": 243, "identical_positions": 238,
        "substituted_positions": 5, "query_gap_columns": 0, "reference_gap_columns": 10,
        "query_aligned_positions": 243, "reference_aligned_positions": 243,
        "query_length": 253, "reference_length": 243, "paired_identity": 238 / 243,
        "alignment_identity": 238 / 253, "query_paired_coverage": 243 / 253, "reference_paired_coverage": 1}
    assert prepared["numerical_complete"] and not result["failures"]


def test_paging_metrics_union_and_source_have_stable_original_identity(tmp_path):
    case = fixture(tmp_path, "blastp_multiple_hsps_json15", omit_reference=True)
    first = selector(metrics=["paired_positions"], rows={"offset": 0, "limit": 1})
    prepared = prepare(case, tmp_path / "first", first)
    source, publication = publish(case, prepared, first)
    second = selector(metrics=["native_score_bits", "query_length"], rows={"record_keys": [publication["rows"][0]["record_key"]]})
    other = prepare(case, tmp_path / "second", second)
    same_source, repeated = publish(case, other, second)
    assert source == same_source and prepared["source_grading_artifact_ref"] == other["source_grading_artifact_ref"]
    assert prepared["scores_artifact_ref"] == other["scores_artifact_ref"]
    assert publication["rows"][0]["observation_ref"] == repeated["rows"][0]["observation_ref"]
    reference = case["store"].get(repeated["rows"][0]["reference_refs"][0])
    assert reference["sequence_ref"] is not None and reference["length"] == 190
    union_selector = selector("pairwise_union")
    union_prepared = prepare(case, tmp_path / "union", union_selector)
    union_source, union = publish(case, union_prepared, union_selector)
    assert union_source == source and union["record_refs"] == [source]
    assert not union_prepared["numerical_complete"]  # Requested conflicting union identity remains unknown.
    row = union["rows"][0]
    assert row["observation_ref"] is None and row["hit_ordinal"] is None and row["hsp_ordinal"] is None
    assert values(row)["observed_paired_query_positions"] == 80
    assert values(row)["observed_paired_reference_positions"] == 160
    assert "paired_identity" not in values(row) and values(row)["conflicting_mapping_count"] > 0
    page = selector(metrics=["paired_positions"], rows={"offset": 1, "limit": 1})
    _, next_page = publish(case, prepare(case, tmp_path / "page", page), page)
    assert next_page["rows"][0]["hsp_ordinal"] == 1
    assert next_page["rows"][0]["observation_ref"] != publication["rows"][0]["observation_ref"]


@pytest.mark.parametrize("label", ["blastp_multiple_hsps_json15", "tblastx_frames_json15"])
def test_valid_requested_numbers_do_not_fail_for_alternative_union_mappings(tmp_path, label):
    case = fixture(tmp_path, label)
    selection = selector("pairwise_union", ["observed_paired_query_positions", "conflicting_mapping_count"])
    prepared = prepare(case, tmp_path / "grading", selection)
    _, publication = publish(case, prepared, selection)
    assert prepared["numerical_complete"] and not publication["failures"]
    assert values(publication["rows"][0])["conflicting_mapping_count"] > 0
    assert publication["rows"][0]["native_status"] == "partial"
    diagnostics = json.loads((tmp_path / "grading/native-blast-grading/diagnostics.json").read_text())
    assert any(row["code"] == "alternative_residue_mapping" and row["diagnostic_only"] for row in diagnostics)


@pytest.mark.parametrize("label,query_length,reference_length,selected_query,selected_reference,covered", [
    ("blastn_range_forward_json15", 240, 240, 180, 210, 180),
    ("blastx_range_reverse_tabular7", 244, 80, 186, 80, 186),
])
def test_union_selected_lengths_are_not_full_lengths(tmp_path, label, query_length, reference_length, selected_query, selected_reference, covered):
    case = fixture(tmp_path, label)
    selection = selector("pairwise_union")
    _, result = publish(case, prepare(case, tmp_path / "grading", selection), selection)
    row = result["rows"][0]
    assert row["status"] == "published"
    numbers = values(row)
    assert numbers["query_length"] == query_length and numbers["reference_length"] == reference_length
    assert numbers["query_selected_length"] == selected_query and numbers["reference_selected_length"] == selected_reference
    assert numbers["query_paired_coverage"] == covered / query_length
    assert numbers["query_selected_paired_coverage"] == 1


@pytest.mark.parametrize("fault", ["wrong_query", "wrong_reference", "omit_query"])
def test_same_length_wrong_sequence_and_unbound_query_never_publish_observation(tmp_path, fault):
    case = fixture(tmp_path, **{fault: True})
    selection = selector(metrics=["identical_positions"])
    prepared = prepare(case, tmp_path / "grading", selection)
    source, result = publish(case, prepared, selection)
    row = result["rows"][0]
    assert row["status"] == ("unbound" if fault == "omit_query" else "invalid")
    assert row["observation_ref"] is None and result["record_refs"] == [source]
    assert values(row)["identical_positions"] == 238
    assert result["failures"]


def replace_report(bundle, overrides, raw):
    row = next(row for row in bundle["artifacts"] if row["role"] in {"primary_report", "tabular_report"})
    overrides[row["role"]] = raw
    row.update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def test_malformed_sibling_keeps_original_valid_hsp_ordinal(tmp_path):
    def change(bundle, overrides):
        raw = json.loads((native_path().parent / "attempt/report.json").read_bytes())
        hsps = raw["BlastOutput2"][0]["report"]["results"]["bl2seq"][0]["hits"][0]["hsps"]
        hsps.insert(0, "explicit synthetic malformed sibling")
        replace_report(bundle, overrides, canonical(raw).encode())
    case = fixture(tmp_path, transform=change)
    selection = selector(metrics=["identical_positions"])
    prepared = prepare(case, tmp_path / "grading", selection)
    _, result = publish(case, prepared, selection)
    assert [row["hsp_ordinal"] for row in result["rows"]] == [0, 1]
    assert [row["status"] for row in result["rows"]] == ["invalid", "published"]
    assert values(result["rows"][1])["identical_positions"] == 238
    assert not prepared["numerical_complete"]


def test_malformed_search_keeps_later_native_search_and_exact_pointer(tmp_path):
    def change(bundle, overrides):
        raw = json.loads((native_path().parent / "attempt/report.json").read_bytes())
        searches = raw["BlastOutput2"][0]["report"]["results"]["bl2seq"]
        invalid = deepcopy(searches[0])
        invalid["hits"] = None
        searches.insert(0, invalid)
        replace_report(bundle, overrides, canonical(raw).encode())
    case = fixture(tmp_path, transform=change)
    selected = selector(metrics=["identical_positions"])
    prepared = prepare(case, tmp_path / "grading", selected)
    _, publication = publish(case, prepared, selected)
    assert len(publication["rows"]) == 1 and publication["rows"][0]["status"] == "published"
    assert publication["rows"][0]["search_key"]["search_pointer"] == "/BlastOutput2/0/report/results/bl2seq/1"
    assert values(publication["rows"][0])["identical_positions"] == 238
    scores = json.loads(case["store"].get_artifact(prepared["scores_artifact_ref"]))
    assert len(scores["searches"]) == 2
    assert scores["rows"]["pairwise_union"][0]["native_status"] == "alignment_report_unavailable"
    assert not prepared["numerical_complete"]


def test_duplicate_mapping_is_not_independent_union_coverage(tmp_path):
    def change(bundle, overrides):
        raw = json.loads((native_path().parent / "attempt/report.json").read_bytes())
        hsps = raw["BlastOutput2"][0]["report"]["results"]["bl2seq"][0]["hits"][0]["hsps"]
        hsps.append(deepcopy(hsps[0]))
        replace_report(bundle, overrides, canonical(raw).encode())
    case = fixture(tmp_path, transform=change)
    selection = selector("pairwise_union")
    _, result = publish(case, prepare(case, tmp_path / "grading", selection), selection)
    row = result["rows"][0]
    assert values(row)["identical_mapping_group_count"] == 1
    assert values(row)["observed_paired_query_positions"] == 243
    assert row["observation_ref"] is None


@pytest.mark.parametrize("fault", ["missing_report", "malformed_report", "native_nonzero"])
def test_native_failure_missing_or_unreadable_reports_are_not_complete(tmp_path, fault):
    def change(bundle, overrides):
        if fault == "malformed_report":
            replace_report(bundle, overrides, b"{unreadable native report")
        elif fault == "native_nonzero":
            bundle["returncode"] = 7
            bundle["failures"] = [{"stage": "native", "code": "native_blast_nonzero_returncode", "role": None,
                                   "detail": {"returncode": 7}}]
    case = fixture(tmp_path, transform=change, missing_role="primary_report" if fault == "missing_report" else None)
    prepared = prepare(case, tmp_path / "grading", selector())
    assert not prepared["numerical_complete"] and prepared["failures"]
    assert prepared["sheet_artifact_ref"] and prepared["scores_artifact_ref"]


def test_original_manifest_and_captured_input_swaps_are_rejected(tmp_path):
    case = fixture(tmp_path)
    selection = selector()
    altered = deepcopy(case["bundle"])
    altered["program"] = "blastn"
    with pytest.raises(ContractError, match="captured_bundle_identity"):
        prepare_native_blast_grading(case["store"], bundle=altered,
            bundle_artifact_ref=case["capture"]["bundle_artifact_ref"], artifacts=case["capture"]["artifacts"],
            directory=tmp_path / "swapped", policy=POLICY, selector=selection)
    artifacts = deepcopy(case["capture"]["artifacts"])
    artifacts[0]["artifact_ref"], artifacts[1]["artifact_ref"] = artifacts[1]["artifact_ref"], artifacts[0]["artifact_ref"]
    prepared = prepare_native_blast_grading(case["store"], bundle=case["bundle"],
        bundle_artifact_ref=case["capture"]["bundle_artifact_ref"], artifacts=artifacts,
        directory=tmp_path / "input-swap", policy=POLICY, selector=selection)
    assert not prepared["numerical_complete"]
    assert any(row["code"] == "native_blast_captured_artifact_digest_mismatch" for row in prepared["failures"])


def test_completed_preparation_rejects_lost_retained_bytes(tmp_path):
    case = fixture(tmp_path)
    selected = selector(metrics=["paired_positions"])
    prepare(case, tmp_path / "grading", selected)
    report = next(row for row in case["capture"]["artifacts"] if row["role"] == "primary_report")
    artifact_path(case["store"], report["artifact_ref"]).unlink()
    with pytest.raises(ContractError, match="retained_artifact_changed"):
        prepare(case, tmp_path / "grading", selected)


@pytest.mark.parametrize("label,available", [("blastn_no_hits_json15", True), ("blastn_no_hits_tabular6", False)])
def test_no_hit_union_distinguishes_successful_zero_from_unavailable_report(tmp_path, label, available):
    case = fixture(tmp_path, label)
    selected = selector("pairwise_union", ["observed_distinct_residue_pairs", "query_selected_paired_positions",
                                          "query_selected_length", "query_selected_paired_coverage"])
    prepared = prepare(case, tmp_path / "grading", selected)
    source, publication = publish(case, prepared, selected)
    row = publication["rows"][0]
    assert row["observation_ref"] is None and publication["record_refs"] == [source]
    if available:
        assert values(row) == {"observed_distinct_residue_pairs": 0, "query_selected_paired_positions": 0,
                               "query_selected_length": 60, "query_selected_paired_coverage": 0}
        assert prepared["numerical_complete"]
    else:
        assert "observed_distinct_residue_pairs" not in values(row)
        assert "query_selected_paired_positions" not in values(row)
        assert row["native_status"] == "alignment_report_unavailable" and not prepared["numerical_complete"]


def test_selected_query_scope_and_actual_hsp_traceback_are_qualified(tmp_path):
    def change(bundle, overrides):
        raw = json.loads((native_path().parent / "attempt/report.json").read_bytes())
        hsp = raw["BlastOutput2"][0]["report"]["results"]["bl2seq"][0]["hits"][0]["hsps"][0]
        hsp["qseq"] = ("C" if hsp["qseq"][0] != "C" else "A") + hsp["qseq"][1:]
        replace_report(bundle, overrides, canonical(raw).encode())
    case = fixture(tmp_path, transform=change)
    selected = selector(metrics=["native_score_bits"])
    prepared = prepare(case, tmp_path / "grading", selected)
    _, publication = publish(case, prepared, selected)
    assert publication["rows"][0]["status"] == "invalid"
    assert any(row["code"] == "native_blast_traceback_sequence_mismatch:query" for row in prepared["failures"])
    valid = fixture(tmp_path / "valid")
    complete = prepare(valid, tmp_path / "valid-grading", selected)
    valid["scope"]["segments"] = [{"target_ref": valid["subject"], "start": 1, "end": 253, "unit": "aa"}]
    _, narrowed = publish(valid, complete, selected)
    assert narrowed["rows"][0]["status"] == "invalid"
    assert any(row["code"] == "native_blast_subject_interval_outside_scope" for row in narrowed["failures"])


def test_interrupted_preparation_is_explicit_without_worker_reexecution(tmp_path, monkeypatch):
    case = fixture(tmp_path)
    selection = selector()
    prepared = prepare(case, tmp_path / "grading", selection)
    (tmp_path / "grading/native-blast-grading/prepared.json").unlink()
    monkeypatch.setattr("gene_annotation_episode.native_blast_result_publication.run_local_job",
                        lambda *a, **k: pytest.fail("interrupted preparation relaunched worker"))
    with pytest.raises(ContractError, match="original_preparation_incomplete"):
        prepare(case, tmp_path / "grading", selection)


def test_frozen_publication_rejects_changed_values_source_query_and_intervals(tmp_path):
    case = fixture(tmp_path)
    selection = selector(metrics=["identical_positions"])
    prepared = prepare(case, tmp_path / "grading", selection)
    source, publication = publish(case, prepared, selection)
    for mutation in ("value", "source", "query", "observation"):
        edited = deepcopy(publication)
        row = edited["rows"][0]
        if mutation == "value": row["measurements"][0]["value"] += 1
        elif mutation == "source": row["source_ref"] = case["store"].get(case["reference"])["source_ref"]
        elif mutation == "query": row["subject_ref"] = case["reference"]
        else: row["observation_ref"] = None
        with pytest.raises(ContractError, match="frozen_publication_mismatch"):
            validate_native_blast_publication(case["store"], source_ref=source, bundle=case["bundle"],
                prepared=prepared, scope=case["scope"], selector=selection, publication=edited)
    obsref = publication["rows"][0]["observation_ref"]
    observation = case["store"].get(obsref)
    observation["operand_intervals"][0]["start"] += 1
    case["store"].db.execute("UPDATE records SET data=? WHERE id=?", (canonical(observation), obsref))
    with pytest.raises(ContractError, match="frozen_publication_mismatch"):
        validate_native_blast_publication(case["store"], source_ref=source, bundle=case["bundle"],
            prepared=prepared, scope=case["scope"], selector=selection, publication=publication)


@pytest.mark.parametrize("fault,code", [
    ("origin", "requires_native_tool_source"), ("source_origin", "requires_native_tool_source"),
    ("provider", "requires_native_tool_source"), ("version", "requires_native_tool_source"),
    ("program", "bundle_program_or_mode_mismatch"), ("mode", "bundle_program_or_mode_mismatch"),
    ("request_program", "bundle_program_or_mode_mismatch"), ("request_mode", "bundle_program_or_mode_mismatch"),
    ("bundle_version", "bundle_program_or_mode_mismatch"), ("bundle_ref", "bundle_source_mismatch"),
    ("kind", "observation_kind_mismatch"), ("mixed", "mixed_native_markers"),
])
def test_store_enforces_native_pairwise_host_marker(tmp_path, fault, code):
    case = fixture(tmp_path)
    selection = selector(metrics=["identical_positions"])
    prepared = prepare(case, tmp_path / "grading", selection)
    source, publication = publish(case, prepared, selection)
    original = case["store"].get(publication["rows"][0]["observation_ref"])
    payload = {k: v for k, v in original.items() if k not in {"id", "record_type", "origin"}}
    origin = "external" if fault == "origin" else "tool"
    if fault == "kind": payload["kind"] = "alignment"
    elif fault == "bundle_ref": payload["native_blast_pairwise"]["bundle_artifact_ref"] = case["store"].artifact("{}")
    elif fault == "mixed":
        payload["native_blast"] = {"program": "blastp", "query_coordinate_unit": "aa", "hit_coordinate_unit": "aa",
            "alignment_unit": "aa", "report_ordinal": 0, "hit_ordinal": 0, "hsp_ordinal": 0,
            "query_from": 1, "query_to": 253, "hit_from": 1, "hit_to": 243}
    elif fault in {"program", "mode", "bundle_version", "request_program", "request_mode"}:
        altered = deepcopy(case["bundle"])
        if fault == "program": altered["program"] = "blastn"
        elif fault == "mode": altered["mode"] = "database"
        elif fault == "request_program": altered["requested_job"]["native_blast"]["program"] = "blastn"
        elif fault == "request_mode": altered["requested_job"]["native_blast"]["mode"] = "database"
        else: altered["version"] = "wrong_bundle_v1"
        ref = case["store"].artifact(canonical(altered))
        src = {k: v for k, v in case["store"].get(source).items() if k not in {"id", "record_type", "origin"}}
        src["artifact_ref"] = ref
        payload["source_ref"] = case["store"].put("source", src, origin="tool")["id"]
        payload["native_blast_pairwise"]["bundle_artifact_ref"] = ref
    elif fault in {"provider", "version", "source_origin"}:
        src = {k: v for k, v in case["store"].get(source).items() if k not in {"id", "record_type", "origin"}}
        if fault != "source_origin": src[fault] = "wrong"
        payload["source_ref"] = case["store"].put("source", src, origin="caller" if fault == "source_origin" else "tool")["id"]
    with pytest.raises(ContractError, match=code):
        case["store"].put("observation", payload, origin=origin, scope=case["scope"])
