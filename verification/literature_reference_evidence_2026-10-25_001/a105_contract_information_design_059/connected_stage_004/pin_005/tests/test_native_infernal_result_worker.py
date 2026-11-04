"""Worker integration using sealed native evidence and explicit synthetic faults."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess

import pytest

from gene_annotation_episode import native_infernal_result_worker as worker
from gene_annotation_episode.cmalign_grader import calculate_cmalign_scores
from gene_annotation_episode.infernal_search_grader import calculate_infernal_search_scores
from gene_annotation_episode.infernal_native_result_views import NATIVE_INFERNAL_METRICS


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/native_infernal_result_worker"
ALIGNMENTS = ROOT / "tests/fixtures/cmalign_graders/native"
SEARCHES = ROOT / "tests/fixtures/infernal_search_graders"


def plan_for(tmp_path, case="cmsearch", family="search_hit", *, rows=None, metrics=None):
    source = FIXTURES / case
    captured = tmp_path / "captured"
    shutil.copytree(source, captured)
    bundle = json.loads((captured / "bundle.json").read_text())
    artifacts = []
    for kind, items in (("input", bundle["inputs"]), ("output", bundle["artifacts"])):
        for row in items:
            artifacts.append({k: row[k] for k in ("role", "format", "relative_path")})
            artifacts[-1].update(kind=kind, path=str(captured / row["relative_path"]),
                artifact_ref="captured_" + kind + "_" + row["role"])
    return {"version": "native_infernal_grading_plan_v1", "bundle": bundle,
        "artifacts": artifacts, "directory": str(tmp_path / "graded"), "failures": [],
        "selector": {"version": "native_infernal_result_selector_v1", "acquisition": "complete_bound_bundle",
            "projection": {"family": family, "rows": rows or {"offset": 0, "limit": 10000},
                "metrics": metrics or list(NATIVE_INFERNAL_METRICS[family])}}}


def captured(plan, role, kind="output"):
    return next(r for r in plan["artifacts"] if r["role"] == role and r["kind"] == kind)


def replace_bytes(plan, role, content, kind="output"):
    row = captured(plan, role, kind)
    raw = content.encode() if isinstance(content, str) else content
    Path(row["path"]).write_bytes(raw)
    bundle = plan["bundle"]
    native = next(r for r in bundle["inputs" if kind == "input" else "artifacts"] if r["role"] == role)
    if kind == "input":
        operand = next(r for r in bundle["requested_job"]["native_infernal"]["operands"] if r["role"] == role)
        operand.update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        native.update(actual_sha256=operand["sha256"], expected_sha256=operand["sha256"],
            size_bytes=len(raw), expected_size_bytes=len(raw))
    else:
        native.update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def execute(plan):
    manifest = worker.run(plan)
    directory = Path(plan["directory"])
    outputs = {key: json.loads((directory / (key + ".json")).read_text())
        for key in ("sheet", "scores", "diagnostics", "worker-result")}
    rows = [json.loads(line) for line in (directory / "selected-rows.ndjson").read_text().splitlines()]
    assert outputs["worker-result"] == manifest
    return manifest, outputs["sheet"], outputs["scores"], rows, outputs["diagnostics"]


def values(row, key="measurements"):
    return {r["name"]: r["value"] for r in row[key]}


def alignment_case(tmp_path, case, *, family="alignment_sequence"):
    """Compose a grading plan from 220's real outputs and original metadata.

    This is a consumer fixture, not a claim of another executed producer job.
    """
    plan = plan_for(tmp_path, "cmalign", family)
    metadata = json.loads((ALIGNMENTS / case / "metadata.json").read_text())
    job = plan["bundle"]["requested_job"]["native_infernal"]
    settings = metadata["operation"]["settings"]
    job["options"] = ["--cpu", "0" if settings["algorithm"] == "sample" else "1"]
    for key, flag in (("global", "-g"), ("notrunc", "--notrunc"), ("sub", "--sub"),
            ("matchonly", "--matchonly"), ("noprob", "--noprob"), ("miss", "--miss")):
        if settings.get(key):
            job["options"].append(flag)
    if settings["algorithm"] in {"cyk", "sample"}:
        job["options"].append("--" + settings["algorithm"])
    if settings["algorithm"] == "sample":
        job["options"] += ["--seed", "42"]
    fasta = "".join(">" + r["name"] + "\n" + r["sequence"] + "\n" for r in metadata["sequences"])
    replace_bytes(plan, "sequences", fasta, "input")
    # All used edge cases use the original tRNA5 model from the producer.
    assert metadata["model"]["name"] == "tRNA5"
    job["operand_bindings"] = [r for r in job["operand_bindings"] if r["operand_role"] == "models"] + [
        {"operand_role": "sequences", "record_ordinal": i, "native_name": r["name"],
            "native_accession": None, "subject_ref": "new_" + str(i), "reference_ref": None}
        for i, r in enumerate(metadata["sequences"])]
    selected_roles = {"stdout", "stderr", "stockholm", "scores", "inserts"}
    if not settings.get("global"):
        selected_roles.add("local_ends")
    job["outputs"] = [r for r in job["outputs"] if r["role"] in selected_roles]
    plan["artifacts"] = [r for r in plan["artifacts"] if r["kind"] == "input" or r["role"] in selected_roles]
    plan["bundle"]["artifacts"] = [r for r in plan["bundle"]["artifacts"] if r["role"] in selected_roles]
    for role, filename in (("stockholm", "alignment.sto"), ("scores", "scores.txt"),
            ("inserts", "inserts.txt"), ("local_ends", "local_ends.txt")):
        if role in selected_roles:
            replace_bytes(plan, role, (ALIGNMENTS / case / filename).read_bytes())
    if "inherited_alignment" in metadata:
        content = metadata["inherited_alignment"]["content"]
        path = Path(plan["directory"]).parent / "captured/inputs/mapali.sto"
        path.write_text(content)
        raw = path.read_bytes()
        job["operands"].append({"role": "mapali", "format": "stockholm", "path": "/absent/original/mapali.sto",
            "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw), "artifact_ref": "original_mapali"})
        plan["artifacts"].append({"role": "mapali", "format": "stockholm", "relative_path": "inputs/mapali.sto",
            "kind": "input", "artifact_ref": "captured_input_mapali", "path": str(path)})
        plan["bundle"]["inputs"].append({"role": "mapali", "format": "stockholm", "relative_path": "inputs/mapali.sto"})
        seed = worker._stockholm_inputs({**metadata["inherited_alignment"], "artifact_id": "captured_input_mapali"})
        for i, row in enumerate(seed):
            job["operand_bindings"].append({"operand_role": "mapali", "record_ordinal": i,
                "native_name": row["name"], "native_accession": row["accession"],
                "subject_ref": "inherited_" + str(i), "reference_ref": None})
    plan["bundle"]["operand_bindings"] = deepcopy(job["operand_bindings"])
    return plan


@pytest.mark.parametrize("case,family", [("cmsearch", "search_hit"), ("cmscan", "search_hit"),
    ("cmsearch", "search_sequence"), ("cmalign", "alignment_sequence"),
    ("cmalign", "alignment_column"), ("cmalign", "alignment_pair")])
def test_native_five_families_complete_numerical_projection(tmp_path, case, family):
    plan = plan_for(tmp_path, case, family)
    original = deepcopy(plan)
    manifest, sheet, scores, rows, diagnostics = execute(plan)
    assert manifest["numerical_complete"], diagnostics
    assert plan == original
    assert len(rows) == len(scores[worker.COLLECTIONS[family]])
    first = rows[0]
    assert set(first) == {"version", "family", "native_ordinal", "record_key", "locator",
        "sequence_name", "model_name", "strand", "origin", "population", "column_index", "pair_columns",
        "invalid", "measurements", "unavailable", "observation_measurements", "subject_operand",
        "subject_intervals", "related_operands"}
    assert first["native_ordinal"] == 0 and not first["invalid"]
    assert not any("time" in r["name"] or "seconds" in r["name"] for r in first["observation_measurements"])
    if family == "search_hit":
        assert values(first) == {"bitscore": 71.4, "evalue": 3.6e-22 if case == "cmsearch" else 1e-22,
            "bias_bits": 0.0, "gc_fraction": 0.5, "model_span_length": 72, "model_span_fraction": 1.0,
            "sequence_span_length": 72, "sequence_span_fraction": 1.0, "consensus_length": 72, "sequence_length": 72}
        assert first["subject_intervals"] == [[0, 72]]
    elif family == "search_sequence":
        assert values(first) == {"hit_count": 1, "union_numerator": 72, "union_denominator": 72,
            "union_span_fraction": 1.0, "unselected_hit_count": 0, "unknown_selection_count": 0, "invalid_geometry_count": 0}
        assert first["record_key"] == scores["sequence_strand_aggregates"][0]["aggregate_id"]
    elif family == "alignment_sequence":
        assert values(first)["native_bit_score"] == 60.03
        assert values(first)["native_avg_pp"] == 1.0
        assert values(first)["model_match_nucleotides"] == 72
        assert values(first)["posterior_lower_mean"] == .95
        assert values(first)["posterior_upper_mean"] == 1.0
        assert {r["name"]: r["reason"] for r in first["unavailable"]}["deleted_model_positions"] == "not_measured"
        assert values(rows[8])["retained_local_end_nucleotides"] == 40
    elif family == "alignment_column":
        assert values(first)["row_count"] == 10
        assert values(first)["occupancy"] == 1
        assert values(first)["occupancy_denominator"] == 10
        assert first["subject_operand"] is None and first["subject_intervals"] == []
    elif family == "alignment_pair":
        assert values(first)["canonical_pair_fraction"] == 1
        assert values(first)["canonical_pairs"] == 10
        assert values(first)["unambiguous_pair_denominator"] == 10
        assert first["subject_operand"] is None and len(first["pair_columns"]) == 2
    if first["subject_operand"]:
        assert first["subject_operand"]["record_ordinal"] == 0
        assert first["subject_operand"]["binding"]["subject_ref"] == "subject_tutorial_sequence_0"
    assert first["related_operands"][0]["kind"] == "covariance_model"
    assert first["related_operands"][0]["sequence_sha256"] is None
    assert sheet["publication_inputs"]["supplied_metadata"] == {}
    assert all("path" not in a for a in sheet["publication_inputs"]["captured_artifacts"])
    assert len([r for r in sheet["publication_inputs"]["parsed_records"] if r["kind"] == "covariance_model"]) == (
        1 if case == "cmalign" else 3)


def test_no_original_paths_network_store_or_native_execution(tmp_path, monkeypatch):
    plan = plan_for(tmp_path)
    original_open = Path.open
    allowed = {Path(r["path"]) for r in plan["artifacts"]}
    output = Path(plan["directory"])
    def confined_open(path, mode="r", *args, **kwargs):
        if not any(flag in mode for flag in "wax+"):
            assert path in allowed or path.is_relative_to(output), "original/unselected path was opened"
        return original_open(path, mode, *args, **kwargs)
    def forbidden(*args, **kwargs):
        pytest.fail("grading attempted acquisition, execution or Store access")
    from gene_annotation_episode.state import Store
    monkeypatch.setattr(Store, "__init__", forbidden)
    monkeypatch.setattr(Path, "open", confined_open)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert execute(plan)[0]["numerical_complete"]


def test_metric_subset_preserves_observation_and_requested_order_is_native(tmp_path):
    plan = plan_for(tmp_path, metrics=["bitscore"])
    _, _, _, first_rows, _ = execute(plan)
    keys = [first_rows[5]["record_key"], first_rows[0]["record_key"]]
    plan["selector"]["projection"].update(rows={"record_keys": keys}, metrics=["evalue"])
    manifest, _, _, rows, _ = execute(plan)
    assert manifest["numerical_complete"]
    assert [r["record_key"] for r in rows] == keys[::-1]
    assert values(rows[0]) == {"evalue": 3.6e-22}
    assert rows[0]["observation_measurements"] == first_rows[0]["observation_measurements"]
    plan["selector"]["projection"]["rows"] = {"record_keys": [keys[0], "absent_native_key"]}
    manifest, _, _, rows, _ = execute(plan)
    assert not manifest["numerical_complete"] and len(rows) == 1
    assert any(r["code"] == "native_infernal_requested_record_key_missing" and
        r["record_key"] == "absent_native_key" for r in manifest["failures"])


def test_original_record_ordinal_not_tblout_query_position(tmp_path):
    plan = plan_for(tmp_path, "cmscan")
    text = Path(captured(plan, "sequences", "input")["path"]).read_text()
    replace_bytes(plan, "sequences", ">no_hit_original_first\nAAAA\n" + text, "input")
    job = plan["bundle"]["requested_job"]["native_infernal"]
    for row in job["operand_bindings"]:
        if row["operand_role"] == "sequences":
            row["record_ordinal"] += 1
    plan["bundle"]["operand_bindings"] = deepcopy(job["operand_bindings"])
    manifest, sheet, _, rows, _ = execute(plan)
    assert manifest["numerical_complete"]
    assert rows[0]["subject_operand"]["record_ordinal"] == 1
    assert rows[0]["subject_operand"]["binding"]["record_ordinal"] == 1
    assert all("occurrence" not in r for r in sheet["sequence_metadata"])


def test_duplicate_search_names_unbound_without_ordinal_guess(tmp_path):
    plan = plan_for(tmp_path, "cmscan")
    text = Path(captured(plan, "sequences", "input")["path"]).read_text()
    replace_bytes(plan, "sequences", text + ">mrum-tRNA.1\nAAAA\n", "input")
    manifest, sheet, _, rows, _ = execute(plan)
    assert not manifest["numerical_complete"]
    assert rows[0]["subject_operand"] is None and rows[0]["subject_intervals"] == []
    assert values(rows[0])["bitscore"] == 71.4
    assert "sequence_span_fraction" not in values(rows[0])
    assert sheet["hits"][0]["sequence"]["metadata_join"]["status"] == "ambiguous"


@pytest.mark.parametrize("field,value", [("length", 999), ("sequence", "AAAA"), ("name", "wrong")])
def test_metadata_conflicts_do_not_overwrite_actual_input(tmp_path, field, value):
    plan = plan_for(tmp_path)
    metadata = {"sequence_metadata": [{"record_ordinal": 0, field: value}]}
    plan["bundle"]["requested_job"]["native_infernal"]["metadata"] = metadata
    manifest, sheet, _, rows, diagnostics = execute(plan)
    assert not manifest["numerical_complete"]
    assert sheet["publication_inputs"]["supplied_metadata"] == metadata
    assert values(rows[0])["sequence_length"] == 72
    assert any(r["code"] == "native_infernal_supplied_metadata_conflict" for r in diagnostics)


@pytest.mark.parametrize("name,accession", [("wrong", None), ("mrum-tRNA.1", "unobserved_accession"), (None, None)])
def test_binding_requires_both_ordinal_and_native_identity(tmp_path, name, accession):
    plan = plan_for(tmp_path)
    job = plan["bundle"]["requested_job"]["native_infernal"]
    binding = next(r for r in job["operand_bindings"] if r["operand_role"] == "sequences")
    binding.update(native_name=name, native_accession=accession)
    plan["bundle"]["operand_bindings"] = deepcopy(job["operand_bindings"])
    manifest, sheet, _, rows, diagnostics = execute(plan)
    assert not manifest["numerical_complete"]
    assert rows[0]["subject_operand"]["binding"] is None
    assert rows[0]["subject_intervals"] == [[0, 72]]
    assert sheet["publication_inputs"]["operand_bindings"] == job["operand_bindings"]
    assert any(r["code"].startswith("native_infernal_operand_binding_identity") for r in diagnostics)


def test_absent_optional_external_binding_is_typed_unknown(tmp_path):
    plan = plan_for(tmp_path)
    plan["bundle"]["requested_job"]["native_infernal"]["operand_bindings"] = []
    plan["bundle"]["operand_bindings"] = []
    manifest, _, _, rows, diagnostics = execute(plan)
    assert manifest["numerical_complete"] and not manifest["failures"]
    assert rows[0]["subject_operand"]["binding"] is None
    assert any(r["code"] == "native_infernal_operand_binding_unavailable" for r in diagnostics)


def test_native_failure_preserves_saved_inputs_and_specific_missingness(tmp_path):
    plan = plan_for(tmp_path, "cmalign_native_failure", "alignment_sequence")
    manifest, sheet, scores, rows, diagnostics = execute(plan)
    assert not manifest["numerical_complete"] and rows == []
    assert sheet["schema"] == "cmalign_sheet_v1" and scores["schema"] == "cmalign_scores_v1"
    assert sheet["operation"]["settings"]["algorithm"] == "sample"
    assert sheet["operation"]["settings"]["--cpu"] == "1"
    assert len(sheet["publication_inputs"]["parsed_records"]) == 11
    assert any(r["code"] == "native_infernal_nonzero_returncode" for r in diagnostics)


def test_no_hit_output_is_zero_rows_not_a_biological_absence_score(tmp_path):
    plan = plan_for(tmp_path)
    replace_bytes(plan, "tblout", (SEARCHES / "cmsearch_no_hits.hits.tbl").read_bytes())
    manifest, sheet, scores, rows, _ = execute(plan)
    assert manifest["numerical_complete"]
    assert rows == [] and scores["hits"] == [] and scores["sequence_strand_aggregates"] == []
    assert sheet["no_hit_meaning"] == "no_reported_match_under_recorded_settings; not biological absence"


def test_invalid_native_cell_preserves_other_components_and_truncated_rows(tmp_path):
    plan = plan_for(tmp_path)
    table = Path(captured(plan, "tblout")["path"]).read_text()
    replace_bytes(plan, "tblout", table.replace("71.4", "invalid", 1).replace("# [ok]", "truncated row\n# [ok]"))
    manifest, sheet, _, rows, diagnostics = execute(plan)
    assert not manifest["numerical_complete"] and len(rows) == 10
    assert "bitscore" not in values(rows[0]) and values(rows[0])["sequence_span_fraction"] == 1
    assert sheet["artifacts"][0]["rows"][-1]["text"] == "truncated row"
    assert any(r["code"] == "native_row_truncated_or_wrong_format" for r in diagnostics)


def test_selected_native_modes_preserved_without_changing_parameters(tmp_path):
    plan = plan_for(tmp_path, "cmscan", "search_sequence")
    job = plan["bundle"]["requested_job"]["native_infernal"]
    job["options"] = ["--cpu", "1", "--oskip", "--anytrunc", "-T", "22.5", "--incE", "0.01", "-Z", "0.123"]
    job["grading_parameters"] = {"hit_scope": "included"}
    table = Path(captured(plan, "tblout")["path"]).read_text()
    replace_bytes(plan, "tblout", table.replace("# Option settings:", "# Option settings: --oskip --anytrunc "))
    _, sheet, scores, rows, _ = execute(plan)
    settings = sheet["operation"]["settings"]
    assert settings["native_options"] == job["options"]
    assert settings["--oskip"] is True and settings["-T"] == "22.5" and settings["--incE"] == "0.01"
    assert scores["parameters"] == job["grading_parameters"]
    assert rows[0]["population"] == "included"
    assert "union_span_fraction" not in values(rows[0])


def test_selected_oskip_without_footer_still_qualifies_aggregate_population(tmp_path):
    plan = plan_for(tmp_path, "cmscan", "search_sequence")
    job = plan["bundle"]["requested_job"]["native_infernal"]
    job["options"] += ["--oskip"]
    table = Path(captured(plan, "tblout")["path"]).read_text()
    replace_bytes(plan, "tblout", "\n".join(line for line in table.splitlines() if not line.startswith("# Option settings:")) + "\n")
    _, sheet, scores, rows, _ = execute(plan)
    assert sheet["artifacts"][0]["effective_complete"] is True
    assert scores["sequence_strand_aggregates"][0]["union_span_fraction"] is None
    assert "union_span_fraction" not in values(rows[0])


@pytest.mark.parametrize("case", ["global", "submodel", "matchonly", "noprob", "sample_serial"])
def test_alignment_native_modes_and_unknown_cells_are_preserved(tmp_path, case):
    plan = alignment_case(tmp_path, case)
    manifest, sheet, scores, rows, diagnostics = execute(plan)
    assert manifest["numerical_complete"], diagnostics
    settings = sheet["operation"]["settings"]
    if case == "global":
        assert settings["global"] is True and settings["notrunc"] is True
        assert values(rows[0])["deleted_model_positions"] == 1
        assert values(rows[0])["total_local_end_nucleotides"] == 0
    elif case == "submodel":
        assert settings["sub"] is True and settings["notrunc"] is True
        assert "deleted_model_positions" not in values(rows[0])
    elif case == "matchonly":
        assert settings["matchonly"] is True
        assert values(rows[0])["omitted_nucleotides"] == 1
        assert sum(b-a for a,b in rows[0]["subject_intervals"]) == 71
    elif case == "noprob":
        assert values(rows[0])["posterior_available_count"] == 0
        assert "posterior_lower_mean" not in values(rows[0])
    elif case == "sample_serial":
        assert sheet["alignment_kind"] == scores["alignment_kind"] == "sampled_alignment"


def test_same_name_mapali_inherited_prefix_and_new_input_have_distinct_bindings(tmp_path):
    plan = alignment_case(tmp_path, "mapali_collision")
    manifest, sheet, scores, rows, diagnostics = execute(plan)
    assert manifest["numerical_complete"], diagnostics
    assert len(rows) == 6
    inherited, new = rows[0], rows[5]
    assert inherited["sequence_name"] == new["sequence_name"] == "tRNA1"
    assert inherited["origin"] == "inherited" and new["origin"] == "newly_aligned"
    assert inherited["subject_operand"]["operand_role"] == "mapali"
    assert inherited["subject_operand"]["binding"]["subject_ref"] == "inherited_0"
    assert new["subject_operand"]["operand_role"] == "sequences"
    assert new["subject_operand"]["binding"]["subject_ref"] == "new_0"
    assert "native_bit_score" not in values(inherited)
    assert values(new)["native_bit_score"] == 40.84 and values(new)["original_length"] == 72
    assert sheet["sequences"][0]["native_name"] == "0|tRNA1"
    assert sheet["sequences"][5]["native_name"] == "5|tRNA1"
    assert scores["sequences"][5]["native_index"] == 1
    assert any(r["code"] == "cmalign_insert_native_model_header_absent_supplied_mapali_association" for r in diagnostics)


def test_alignment_population_uses_original_calculator_parameter(tmp_path):
    plan = alignment_case(tmp_path, "mapali", family="alignment_column")
    plan["bundle"]["requested_job"]["native_infernal"]["grading_parameters"] = {"population": "inherited"}
    manifest, sheet, scores, rows, _ = execute(plan)
    assert manifest["numerical_complete"]
    assert values(rows[0])["row_count"] == 5 and rows[0]["population"] == "inherited"
    assert scores["columns"][0]["populations"]["all"]["row_count"] == 6
    assert len(sheet["sequences"]) == 6


def test_original_tu_xn_ia_identity_survives_native_normalization(tmp_path):
    plan = plan_for(tmp_path, "cmalign", "alignment_sequence")
    sequences = Path(captured(plan, "sequences", "input")["path"]).read_text()
    # T/U and I/A have different original identities despite native digitization.
    sequences = "\n".join(line if line.startswith(">") else line.replace("U", "T").replace("A", "I")
        for line in sequences.splitlines()) + "\n"
    replace_bytes(plan, "sequences", sequences, "input")
    manifest, sheet, _, rows, _ = execute(plan)
    assert manifest["numerical_complete"]
    original = sheet["publication_inputs"]["parsed_records"][1]["sequence"]
    assert "I" in original and "T" in original and "U" not in original
    assert rows[0]["subject_operand"]["sequence_sha256"] == hashlib.sha256(original.upper().encode()).hexdigest()
    assert rows[0]["subject_intervals"] == [[0, 72]]


def test_missing_matchonly_sidecar_preserves_native_score_without_invented_subject(tmp_path):
    plan = alignment_case(tmp_path, "matchonly")
    plan["artifacts"] = [r for r in plan["artifacts"] if r["role"] != "inserts"]
    manifest, _, _, rows, _ = execute(plan)
    assert not manifest["numerical_complete"]
    assert values(rows[0])["native_bit_score"] == 40.84
    assert rows[0]["subject_operand"] is None and rows[0]["subject_intervals"] == []


@pytest.mark.parametrize("case,family", [("cmsearch", "search_hit"), ("cmalign", "alignment_pair")])
def test_saved_sheet_recalculation_without_parser_or_io(tmp_path, monkeypatch, case, family):
    plan = plan_for(tmp_path, case, family)
    _, sheet, expected, _, _ = execute(plan)
    original = deepcopy(sheet)
    def forbidden(*args, **kwargs):
        pytest.fail("recalculation reparsed, reacquired or reran native work")
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(worker, "populate_cmalign_sheet", forbidden)
    monkeypatch.setattr(worker, "populate_infernal_search_sheet", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    calculate = calculate_cmalign_scores if case == "cmalign" else calculate_infernal_search_scores
    assert calculate(sheet, parameters=expected["parameters"]) == expected
    assert sheet == original


def test_cli_entrypoint_and_all_output_files(tmp_path, capsys):
    plan = plan_for(tmp_path)
    path = tmp_path / "grading-plan.json"
    path.write_text(json.dumps(plan))
    assert worker.main([str(path)]) == 0
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["numerical_complete"]
    assert {p.name for p in Path(plan["directory"]).iterdir()} == {
        "sheet.json", "scores.json", "selected-rows.ndjson", "diagnostics.json", "worker-result.json"}


def test_retained_producer_fixture_bytes_match_frozen_sources():
    hashes = json.loads((FIXTURES / "NATIVE_SHA256.json").read_text())
    for case, files in hashes.items():
        for name, expected in files.items():
            assert hashlib.sha256((FIXTURES / case / name).read_bytes()).hexdigest() == expected


@pytest.mark.parametrize("fault", ["missing_capture", "unreadable_capture", "truncated_cm_filter"])
def test_missing_or_malformed_model_keeps_native_values_and_sequence_binding(tmp_path, fault):
    plan = plan_for(tmp_path)
    if fault == "missing_capture":
        plan["artifacts"] = [r for r in plan["artifacts"] if r["role"] != "models"]
    elif fault == "unreadable_capture":
        Path(captured(plan, "models", "input")["path"]).unlink()
    else:
        original = Path(captured(plan, "models", "input")["path"]).read_text()
        replace_bytes(plan, "models", original[:original.index("HMMER3/")], "input")
    manifest, sheet, _, rows, diagnostics = execute(plan)
    assert not manifest["numerical_complete"]
    assert values(rows[0])["bitscore"] == 71.4 and rows[0]["subject_operand"] is not None
    assert rows[0]["related_operands"] == []
    assert len([r for r in sheet["publication_inputs"]["parsed_records"] if r["operand_role"] == "sequences"]) == 10
    assert diagnostics


def test_search_reverse_coordinates_are_physical_half_open_intervals(tmp_path):
    plan = plan_for(tmp_path)
    table = Path(captured(plan, "tblout")["path"]).read_text().splitlines()
    fields = table[2].split()
    fields[7:10] = ["72", "1", "-"]  # Explicit synthetic reversed-strand geometry.
    table[2] = " ".join(fields)
    replace_bytes(plan, "tblout", "\n".join(table) + "\n")
    manifest, _, _, rows, _ = execute(plan)
    assert manifest["numerical_complete"]
    assert rows[0]["strand"] == "-" and rows[0]["subject_intervals"] == [[0, 72]]
    assert values(rows[0])["sequence_span_length"] == 72


def test_out_of_range_native_interval_is_not_attached_to_physical_subject(tmp_path):
    plan = plan_for(tmp_path)
    table = Path(captured(plan, "tblout")["path"]).read_text().splitlines()
    fields = table[2].split()
    fields[8] = "73"  # Native/supplied first sequence length is 72.
    table[2] = " ".join(fields)
    replace_bytes(plan, "tblout", "\n".join(table) + "\n")
    manifest, _, _, rows, _ = execute(plan)
    assert not manifest["numerical_complete"]
    assert rows[0]["subject_intervals"] == [] and values(rows[0])["bitscore"] == 71.4
    assert "sequence_span_length" not in values(rows[0])


def test_alignment_wrong_original_sequence_does_not_bind_by_name(tmp_path):
    plan = plan_for(tmp_path, "cmalign", "alignment_sequence")
    sequence = Path(captured(plan, "sequences", "input")["path"]).read_text()
    replace_bytes(plan, "sequences", sequence.replace("GGAGCUA", "AAAGCUA", 1), "input")
    manifest, _, _, rows, diagnostics = execute(plan)
    assert not manifest["numerical_complete"]
    assert rows[0]["sequence_name"] == "mrum-tRNA.1" and rows[0]["subject_operand"] is None
    assert values(rows[0])["native_bit_score"] == 60.03
    assert any(r["code"] == "cmalign_supplied_sequence_content_mismatch" for r in diagnostics)


def test_x_to_n_output_matching_keeps_original_x_sequence_identity(tmp_path):
    plan = plan_for(tmp_path, "cmalign", "alignment_sequence")
    sequence = Path(captured(plan, "sequences", "input")["path"]).read_text()
    alignment = Path(captured(plan, "stockholm")["path"]).read_text()
    # Synthetic digitization edge only; this does not claim newly measured scores.
    replace_bytes(plan, "sequences", sequence.replace("GGAGCUA", "XGAGCUA", 1), "input")
    replace_bytes(plan, "stockholm", alignment.replace("GGAGCUA", "NGAGCUA", 1))
    manifest, sheet, _, rows, _ = execute(plan)
    assert manifest["numerical_complete"]
    original = next(r["sequence"] for r in sheet["publication_inputs"]["parsed_records"]
        if r["operand_role"] == "sequences" and r["record_ordinal"] == 0)
    assert original.startswith("X")
    assert rows[0]["subject_operand"]["sequence_sha256"] == hashlib.sha256(original.encode()).hexdigest()


def test_model_accession_disambiguates_same_name_without_guessing_ordinal(tmp_path):
    plan = plan_for(tmp_path)
    text = Path(captured(plan, "models", "input")["path"]).read_text()
    cm, filt, remainder = text.split("//\n", 2)
    first = cm + "//\n" + filt + "//\n"
    def accession(record, acc):
        return re.sub(r"^(NAME\s+tRNA5)\n", r"\1\nACC      " + acc + "\n", record, flags=re.M)
    # Synthetic duplicate-name identity edge, preserving the actual model body.
    replace_bytes(plan, "models", accession(first, "RF00005") + remainder + accession(first, "RF99999"), "input")
    table = Path(captured(plan, "tblout")["path"]).read_text().splitlines()
    for index, line in enumerate(table):
        if line and not line.startswith("#"):
            fields = line.split()
            fields[3] = "RF00005"
            table[index] = " ".join(fields)
    replace_bytes(plan, "tblout", "\n".join(table) + "\n")
    job = plan["bundle"]["requested_job"]["native_infernal"]
    job["operand_bindings"][0]["native_accession"] = "RF00005"
    plan["bundle"]["operand_bindings"] = deepcopy(job["operand_bindings"])
    manifest, sheet, _, rows, diagnostics = execute(plan)
    assert manifest["numerical_complete"], diagnostics
    assert len(sheet["model_metadata"]) == 4
    assert rows[0]["related_operands"][0]["accession"] == "RF00005"
    assert rows[0]["related_operands"][0]["record_ordinal"] == 0
    assert values(rows[0])["model_span_fraction"] == 1.0
