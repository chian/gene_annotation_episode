"""Engineered file/worker controls, not native MUSCLE or custody evidence.

Only the existing neutral parser/calculator interprets the literal alignment.
The synthetic capture Source operand below tests supplied metadata shape; no
Store publication, native execution, source admission or grant is asserted.
"""
import builtins
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import stat
import subprocess

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import protein_conservation_result_worker as worker


_CAPTURE = "source_" + "c" * 24
_INPUT_SOURCE = "source_" + "d" * 24


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"


def _file(directory, name, raw, format):
    path = directory / name
    path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    return {"path": str(path), "file": {"artifact_ref": "artifact_" + digest,
        "sha256": digest, "size_bytes": len(raw), "format": format}}


def _request(tmp_path, *, original=b">first full header\nAa-\n>second full header\nAA-\n",
        aligned=b">second full header\nAA-\n>first full header\nAa-\n", source_ref=None):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    selected = {**_file(inputs, "original.fasta", original, "fasta"), "source_ref": source_ref}
    captured = None
    capture = {"state": "missing", "retained_size_bytes": None, "original_size_bytes": None}
    if aligned is not None:
        captured = {**_file(inputs, "alignment.fasta", aligned, "aligned_fasta"), "source_ref": _CAPTURE,
            "capture": {"state": "complete", "byte_start_0based": 0,
                "byte_end_0based_exclusive": len(aligned), "original_size_bytes": len(aligned)}}
        capture = {"state": "complete", "retained_size_bytes": len(aligned), "original_size_bytes": len(aligned)}
    return {"version": worker.REQUEST_VERSION, "mode": "parse", "input": selected,
        "alignment_file": captured, "native_execution": {"state": "completed", "returncode": 0,
            "reported_version": "engineered metadata; no native invocation",
            "alphabet": {"state": "unknown", "value": None}, "output_capture": capture,
            "parser_status": "not_parsed"}, "native_issues": [], "saved": None,
        "population_request": {"kind": "all_output_rows_and_columns", "label": "retained output",
            "completeness": "complete"},
        "selection": {"version": "protein_conservation_selection_v1",
            "native_rows": {"row_indices": None, "offset": 0, "limit": 10},
            "sites": {"columns_0based": None, "offset": 0, "limit": 10}}}


def _out(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def _document(directory, declaration):
    path = directory / declaration["relative_path"]
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == declaration["sha256"]
    assert len(raw) == declaration["size_bytes"]
    assert stat.S_IMODE(path.stat().st_mode) == 0o444
    return json.loads(raw)


def _saved_file(directory, declaration):
    return {"path": str(directory / declaration["relative_path"]), "file": {
        "artifact_ref": "artifact_" + declaration["sha256"],
        **{key: declaration[key] for key in ("sha256", "size_bytes", "format")}}}


def _saved(request, directory, output):
    return {"version": worker.REQUEST_VERSION, "mode": "calculate_saved", "input": None,
        "alignment_file": None, "native_execution": None, "native_issues": None,
        "saved": {"alignment": None if output["alignment"] is None else _saved_file(directory, output["alignment"]),
            "context": _saved_file(directory, output["context"])},
        "population_request": deepcopy(request["population_request"]), "selection": deepcopy(request["selection"])}


def _forbidden(*args, **kwargs):
    raise AssertionError("native execution, host ownership or unselected data access is forbidden")


@pytest.fixture(autouse=True)
def no_native_or_host_owner(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if (name == "Bio" or name.startswith("Bio.") or name.endswith((
                ".muscle_alignment_driver", ".store", ".native_lifecycle"))):
            return _forbidden()
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.setattr(subprocess, "Popen", _forbidden)
    monkeypatch.setattr(subprocess, "run", _forbidden)


@pytest.mark.parametrize("kind", ["request", "output"])
def test_worker_schemas_are_draft202012_contracts(kind):
    schema = (worker.protein_conservation_result_request_schema() if kind == "request"
        else worker.protein_conservation_result_output_schema())
    Draft202012Validator.check_schema(schema)


def test_parse_delegates_once_and_retains_exact_native_document_without_new_source(tmp_path, monkeypatch):
    request = _request(tmp_path)
    before = deepcopy(request)
    parser, calculator, observed = worker.parse_aligned_fasta, worker.literal_site_conservation, []
    def parse(raw, **kwargs):
        observed.append(("parse", raw, deepcopy(kwargs)))
        return parser(raw, **kwargs)
    def calculate(alignment, **kwargs):
        value = calculator(alignment, **kwargs)
        observed.append(("calculate", deepcopy(alignment), deepcopy(kwargs), deepcopy(value)))
        return value
    monkeypatch.setattr(worker, "parse_aligned_fasta", parse)
    monkeypatch.setattr(worker, "literal_site_conservation", calculate)
    directory = _out(tmp_path, "result")
    result = worker.run_protein_conservation_result(request, output_directory=directory)
    alignment = _document(directory, result["alignment"])
    components = _document(directory, result["components"])
    context = _document(directory, result["context"])
    value = _document(directory, result["value"])
    population = _document(directory, result["population"])
    assert [row[0] for row in observed] == ["parse", "calculate"]
    assert observed[0][1] == Path(request["alignment_file"]["path"]).read_bytes()
    assert observed[0][2] == {"artifact": {"raw_artifact_ref": request["alignment_file"]["file"]["artifact_ref"],
        "source_ref": _CAPTURE, "sha256": request["alignment_file"]["file"]["sha256"]},
        "id_rule": "first_whitespace_token", "encoding": "utf-8"}
    assert observed[1][1:3] == (alignment, {"population": population})
    assert components == observed[1][3]
    assert [row["raw_header"] for row in alignment["rows"]] == ["second full header", "first full header"]
    assert [row["sequence"] for row in alignment["rows"]] == ["AA-", "Aa-"]
    assert context["row_associations"]["rows"] == [
        {"output_row_index": 0, "input_record_ordinals": [1], "state": "unique_label_match"},
        {"output_row_index": 1, "input_record_ordinals": [0], "state": "unique_label_match"}]
    assert context["input"]["source_ref"] is None
    assert context["input"]["selection"] == {"namespace": "artifact",
        "reference": request["input"]["file"]["artifact_ref"], "format": "fasta"}
    assert value["context"]["input"] == context["input"]
    assert value["native_rows"] == alignment["rows"]
    assert "source_ref" not in value and str(tmp_path) not in json.dumps(value)
    assert request == before


@pytest.mark.parametrize("case", ["duplicate_input", "duplicate_output", "first_token_only"])
def test_header_associations_never_zip_deduplicate_or_match_only_first_tokens(tmp_path, case):
    if case == "duplicate_input":
        original, aligned = b">x full\nA\n>x full\nT\n", b">x full\nA\n"
        candidates, state, unmatched = [0, 1], "ambiguous_label_match", []
    elif case == "duplicate_output":
        original, aligned = b">x full\nA\n", b">x full\nA\n>x full\nA\n"
        candidates, state, unmatched = [0], "ambiguous_label_match", []
    else:
        original, aligned = b">x one\nA\n>x two\nT\n", b">x three\nA\n"
        candidates, state, unmatched = [], "unmatched_output_label", [0, 1]
    request = _request(tmp_path, original=original, aligned=aligned)
    directory = _out(tmp_path, "result")
    result = worker.run_protein_conservation_result(request, output_directory=directory)
    associations = _document(directory, result["context"])["row_associations"]
    assert all(row["input_record_ordinals"] == candidates and row["state"] == state
        for row in associations["rows"])
    assert associations["unmatched_input_record_ordinals"] == unmatched


@pytest.mark.parametrize("original,expected", [
    (b">good\nA\n>\nT\n", "partial"),
    (b">good\nA\n>\xff\nT\n", "partial"),
    (b">\xff\nA\n", "unavailable"),
    (b"unheaded\n>good\nA\n", "partial"),
])
def test_partial_input_catalog_never_promotes_a_known_label_to_complete_membership(tmp_path, original, expected):
    request = _request(tmp_path, original=original, aligned=b">good\nA\n>\nT\n")
    directory = _out(tmp_path, "result")
    result = worker.run_protein_conservation_result(request, output_directory=directory)
    context = _document(directory, result["context"])
    assert context["input"]["records_state"] == "partial"
    assert context["row_associations"]["state"] == expected
    assert context["row_associations"]["unmatched_input_record_ordinals"] is None
    first, second = context["row_associations"]["rows"]
    assert first["state"] == ("ambiguous_label_match" if expected == "partial" else "unavailable_input_records")
    assert second["state"] == "unavailable_input_records"
    assert second["input_record_ordinals"] == []


def test_explicit_source_selection_is_preserved_without_changing_file_identity(tmp_path):
    request = _request(tmp_path, source_ref=_INPUT_SOURCE)
    directory = _out(tmp_path, "result")
    result = worker.run_protein_conservation_result(request, output_directory=directory)
    selected = _document(directory, result["context"])["input"]
    assert selected["selection"] == {"namespace": "source", "reference": _INPUT_SOURCE, "format": "fasta"}
    assert selected["source_ref"] == _INPUT_SOURCE and selected["file"] == request["input"]["file"]


def test_saved_calculation_reads_only_pinned_alignment_and_context_and_reuses_original_capture(tmp_path, monkeypatch):
    request = _request(tmp_path)
    first_dir = _out(tmp_path, "parse")
    first = worker.run_protein_conservation_result(request, output_directory=first_dir)
    saved = _saved(request, first_dir, first)
    saved["population_request"] = {"kind": "explicit_output_indices", "label": "new retained scope",
        "completeness": "complete", "row_indices": [1, 0], "columns_0based": [2, 0]}
    saved["selection"]["native_rows"] = {"row_indices": [1, 0], "offset": 1, "limit": 1}
    saved["selection"]["sites"] = {"columns_0based": [0, 2], "offset": 0, "limit": 1}
    allowed = {saved["saved"][key]["path"] for key in ("alignment", "context")}
    original_read, calculator, reads, calls = worker.storage.read_bytes, worker.literal_site_conservation, [], []
    def read(path):
        assert str(path) in allowed
        reads.append(str(path))
        return original_read(path)
    def calculate(alignment, **kwargs):
        calls.append(deepcopy(kwargs["population"]))
        return calculator(alignment, **kwargs)
    monkeypatch.setattr(worker.storage, "read_bytes", read)
    monkeypatch.setattr(worker, "parse_aligned_fasta", _forbidden)
    monkeypatch.setattr(worker, "_input_record", _forbidden)
    monkeypatch.setattr(worker, "literal_site_conservation", calculate)
    directory = _out(tmp_path, "saved")
    result = worker.run_protein_conservation_result(saved, output_directory=directory)
    assert set(reads) == allowed and len(reads) == 2
    assert len(calls) == 1 and calls[0]["row_indices"] == [1, 0] and calls[0]["columns_0based"] == [2, 0]
    assert result["alignment"] is None and not (directory / "alignment.json").exists()
    assert (directory / "context.json").read_bytes() == (first_dir / "context.json").read_bytes()
    value = _document(directory, result["value"])
    original_alignment = json.loads((first_dir / "alignment.json").read_bytes())
    assert value["context"]["alignment"]["artifact"] == original_alignment["artifact"]
    assert original_alignment["artifact"]["raw_artifact_ref"] != saved["saved"]["alignment"]["file"]["artifact_ref"]
    assert [row["row_index"] for row in value["native_rows"]] == [0]
    assert [row["column_0based"] for row in value["sites"]] == [0]


@pytest.mark.parametrize("aligned,parser_state,rows,document", [
    (None, "not_parsed", 0, False), (b"\xff", "invalid", 0, False),
    (b">a\nAA\n>b\nA\n", "partial", 2, True),
    (b">a\nA!\n", "partial", 1, True), (b"", "invalid", 0, True),
])
def test_unresolved_dimensions_keep_known_native_rows_and_null_calculated_values(
        tmp_path, monkeypatch, aligned, parser_state, rows, document):
    request = _request(tmp_path, aligned=aligned)
    monkeypatch.setattr(worker, "literal_site_conservation", _forbidden)
    directory = _out(tmp_path, "result")
    result = worker.run_protein_conservation_result(request, output_directory=directory)
    value = _document(directory, result["value"])
    assert (result["alignment"] is not None) is document
    assert result["population"] is result["components"] is None
    assert value["context"]["native_execution"]["parser_status"] == parser_state
    assert len(value["native_rows"]) == rows and value["sites"] == []
    assert value["context"]["member_count"] is value["context"]["site_count"] is None
    assert value["context"]["population_resolution"]["state"] == "unresolved"


def test_zero_columns_is_distinct_from_unresolved_dimensions(tmp_path, monkeypatch):
    request = _request(tmp_path, original=b">a\n>b\n", aligned=b">a\n>b\n")
    calculator, calls = worker.literal_site_conservation, []
    def calculate(*args, **kwargs):
        result = calculator(*args, **kwargs)
        calls.append(deepcopy(result))
        return result
    monkeypatch.setattr(worker, "literal_site_conservation", calculate)
    directory = _out(tmp_path, "result")
    result = worker.run_protein_conservation_result(request, output_directory=directory)
    assert len(calls) == 1 and _document(directory, result["components"]) == calls[0]
    assert _document(directory, result["alignment"])["observed_column_count"] == 0
    assert _document(directory, result["population"])["columns_0based"] == []


def test_failed_native_status_does_not_replace_observed_parser_or_population_state(tmp_path):
    request = _request(tmp_path)
    request["native_execution"].update(state="failed", returncode=17)
    directory = _out(tmp_path, "result")
    result = worker.run_protein_conservation_result(request, output_directory=directory)
    context = _document(directory, result["value"])["context"]
    assert context["native_execution"]["state"] == "failed"
    assert context["native_execution"]["returncode"] == 17
    assert context["native_execution"]["parser_status"] == "ok"
    assert context["population_request"]["kind"] == "all_output_rows_and_columns"
    assert context["row_associations"]["state"] == "available"


def test_truncated_capture_and_selected_incomplete_population_preserve_observed_rows(tmp_path):
    request = _request(tmp_path)
    size = request["alignment_file"]["file"]["size_bytes"]
    request["alignment_file"]["capture"].update(state="truncated", original_size_bytes=size + 10)
    request["native_execution"]["output_capture"].update(state="truncated", original_size_bytes=size + 10)
    request["population_request"]["completeness"] = "truncated"
    directory = _out(tmp_path, "result")
    result = worker.run_protein_conservation_result(request, output_directory=directory)
    value = _document(directory, result["value"])
    assert len(value["native_rows"]) == 2
    assert _document(directory, result["alignment"])["completeness"] == "complete"
    assert value["context"]["native_execution"]["output_capture"]["state"] == "truncated"
    assert value["context"]["member_count"]["state"] == "truncated"
    assert value["context"]["member_count"]["value"] is None


def test_native_qualifications_remain_literal_in_public_and_saved_context(tmp_path):
    request = _request(tmp_path)
    issue = {"code": "muscle_alignment_software_changed_after_execution", "phase": "native_execution",
        "path": "/native_execution", "severity": "error",
        "evidence_refs": [request["alignment_file"]["file"]["artifact_ref"]]}
    request["native_issues"] = [issue]
    original = deepcopy(request)
    first_dir = _out(tmp_path, "parse")
    first = worker.run_protein_conservation_result(request, output_directory=first_dir)
    assert _document(first_dir, first["context"])["issues"] == [issue]
    assert _document(first_dir, first["value"])["context"]["issues"] == [issue]
    saved = _saved(request, first_dir, first)
    assert saved["native_issues"] is None
    directory = _out(tmp_path, "saved")
    result = worker.run_protein_conservation_result(saved, output_directory=directory)
    assert (directory / "context.json").read_bytes() == (first_dir / "context.json").read_bytes()
    assert _document(directory, result["value"])["context"]["issues"] == [issue]
    assert request == original


@pytest.mark.parametrize("change", ["mixed_mode", "input_pin", "capture_pin", "source_namespace", "relative_path",
    "input_format", "capture_extent", "capture_state", "returncode_bool", "selection_bool", "population_float",
    "missing_capture_conflict", "preparsed", "native_issue_shape"])
def test_invalid_request_rejects_before_any_data_parser_or_calculator(tmp_path, monkeypatch, change):
    request = _request(tmp_path)
    if change == "mixed_mode": request["saved"] = {}
    elif change == "input_pin": request["input"]["file"]["sha256"] = "x"
    elif change == "capture_pin": request["alignment_file"]["file"]["size_bytes"] = True
    elif change == "source_namespace": request["alignment_file"]["source_ref"] = request["input"]["file"]["artifact_ref"]
    elif change == "relative_path": request["input"]["path"] = "relative.fasta"
    elif change == "input_format": request["input"]["file"]["format"] = "aligned_fasta"
    elif change == "capture_extent": request["alignment_file"]["capture"]["byte_end_0based_exclusive"] += 1
    elif change == "capture_state": request["alignment_file"]["capture"]["state"] = "unknown"
    elif change == "returncode_bool": request["native_execution"]["returncode"] = False
    elif change == "selection_bool": request["selection"]["native_rows"]["offset"] = True
    elif change == "population_float":
        request["population_request"] = {"kind": "explicit_output_indices", "label": "x",
            "completeness": "complete", "row_indices": [0.0], "columns_0based": [0]}
    elif change == "missing_capture_conflict": request["alignment_file"] = None
    elif change == "preparsed": request["native_execution"]["parser_status"] = "ok"
    else: request["native_issues"] = [{"unexpected_control": True}]
    monkeypatch.setattr(worker.storage, "read_bytes", _forbidden)
    monkeypatch.setattr(worker, "parse_aligned_fasta", _forbidden)
    monkeypatch.setattr(worker, "literal_site_conservation", _forbidden)
    directory = _out(tmp_path, "result")
    with pytest.raises(ValueError):
        worker.run_protein_conservation_result(request, output_directory=directory)
    assert list(directory.iterdir()) == []


@pytest.mark.parametrize("key", ["input", "alignment_file"])
def test_changed_pinned_bytes_never_reach_parser_or_calculator(tmp_path, monkeypatch, key):
    request = _request(tmp_path)
    Path(request[key]["path"]).write_bytes(b"changed")
    monkeypatch.setattr(worker, "parse_aligned_fasta", _forbidden)
    monkeypatch.setattr(worker, "literal_site_conservation", _forbidden)
    directory = _out(tmp_path, "result")
    with pytest.raises(ValueError, match="protein_conservation_result_file_identity_conflict"):
        worker.run_protein_conservation_result(request, output_directory=directory)
    assert list(directory.iterdir()) == []


@pytest.mark.parametrize("aligned", [None, b">a\nAA\n>b\nA\n"])
def test_saved_unresolved_state_reuses_only_saved_documents_without_parsing_or_math(tmp_path, monkeypatch, aligned):
    request = _request(tmp_path, aligned=aligned)
    first_dir = _out(tmp_path, "parse")
    first = worker.run_protein_conservation_result(request, output_directory=first_dir)
    saved = _saved(request, first_dir, first)
    monkeypatch.setattr(worker, "parse_aligned_fasta", _forbidden)
    monkeypatch.setattr(worker, "literal_site_conservation", _forbidden)
    directory = _out(tmp_path, "saved")
    result = worker.run_protein_conservation_result(saved, output_directory=directory)
    assert result["alignment"] is result["components"] is result["population"] is None
    assert (directory / "context.json").read_bytes() == (first_dir / "context.json").read_bytes()
    assert _document(directory, result["value"])["context"]["member_count"] is None


@pytest.mark.parametrize("change", ["metadata", "context_version", "capture_source", "input_association", "extent"])
def test_saved_context_contradictions_deny_before_calculator(tmp_path, monkeypatch, change):
    request = _request(tmp_path)
    first_dir = _out(tmp_path, "parse")
    first = worker.run_protein_conservation_result(request, output_directory=first_dir)
    saved = _saved(request, first_dir, first)
    context = json.loads((first_dir / "context.json").read_bytes())
    if change == "metadata": context["alignment"]["observed_row_count"] += 1
    elif change == "context_version": context["version"] = "other"
    elif change == "capture_source": context["alignment"]["artifact"]["source_ref"] = "artifact_wrong_namespace"
    elif change == "input_association": context["row_associations"]["rows"][0]["input_record_ordinals"] = [0]
    else: context["native_execution"]["output_capture"]["retained_size_bytes"] = 1
    rewritten = tmp_path / "engineered-invalid-saved"
    rewritten.mkdir()
    saved["saved"]["context"] = _file(rewritten, "context.json", _json(context), worker.CONTEXT_VERSION)
    monkeypatch.setattr(worker, "parse_aligned_fasta", _forbidden)
    monkeypatch.setattr(worker, "literal_site_conservation", _forbidden)
    directory = _out(tmp_path, "saved")
    with pytest.raises(ValueError):
        worker.run_protein_conservation_result(saved, output_directory=directory)
    assert {p.name for p in directory.iterdir()} == (
        {"context.json", "population.json"} if change == "input_association" else set())


@pytest.mark.parametrize("kind", ["population", "native_row_view", "site_view"])
def test_invalid_scope_preserves_observed_alignment_and_context_without_calculation(tmp_path, monkeypatch, kind):
    request = _request(tmp_path)
    if kind == "population":
        request["population_request"] = {"kind": "explicit_output_indices", "label": "invalid scope",
            "completeness": "complete", "row_indices": [99], "columns_0based": [0]}
    elif kind == "native_row_view":
        request["selection"]["native_rows"]["row_indices"] = [99]
    else:
        request["selection"]["sites"]["columns_0based"] = [99]
    monkeypatch.setattr(worker, "literal_site_conservation", _forbidden)
    directory = _out(tmp_path, "result")
    with pytest.raises(ValueError):
        worker.run_protein_conservation_result(request, output_directory=directory)
    alignment = json.loads((directory / "alignment.json").read_bytes())
    context = json.loads((directory / "context.json").read_bytes())
    assert [row["raw_header"] for row in alignment["rows"]] == ["second full header", "first full header"]
    assert context["alignment"] == {key: value for key, value in alignment.items() if key != "rows"}
    assert context["native_execution"]["parser_status"] == "ok"
    assert not (directory / "components.json").exists() and not (directory / "value.json").exists()
    assert (directory / "population.json").exists() is (kind != "population")


def test_late_calculator_failure_preserves_immutable_observed_alignment_context_and_population(tmp_path, monkeypatch):
    request = _request(tmp_path)
    directory = _out(tmp_path, "result")
    observed = []
    def fail(alignment, *, population):
        assert json.loads((directory / "alignment.json").read_bytes()) == alignment
        assert json.loads((directory / "population.json").read_bytes()) == population
        assert json.loads((directory / "context.json").read_bytes())["alignment"] == {
            key: value for key, value in alignment.items() if key != "rows"}
        observed.append(alignment)
        raise ValueError("engineered_calculator_failure")
    monkeypatch.setattr(worker, "literal_site_conservation", fail)
    with pytest.raises(ValueError, match="engineered_calculator_failure"):
        worker.run_protein_conservation_result(request, output_directory=directory)
    assert len(observed) == 1
    assert {p.name for p in directory.iterdir()} == {"alignment.json", "context.json", "population.json"}


def test_existing_outputs_deny_reentry_without_data_reads_or_recalculation(tmp_path, monkeypatch):
    request = _request(tmp_path)
    directory = _out(tmp_path, "result")
    worker.run_protein_conservation_result(request, output_directory=directory)
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    monkeypatch.setattr(worker.storage, "read_bytes", _forbidden)
    monkeypatch.setattr(worker, "parse_aligned_fasta", _forbidden)
    monkeypatch.setattr(worker, "literal_site_conservation", _forbidden)
    with pytest.raises(ValueError, match="protein_conservation_result_output_already_exists"):
        worker.run_protein_conservation_result(request, output_directory=directory)
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == before


def test_cli_declares_only_real_immutable_files_and_rejects_reentry(tmp_path):
    request = _request(tmp_path)
    directory = _out(tmp_path, "result")
    path, result_path = directory / "request.json", directory / "worker-result.json"
    path.write_bytes(_json({"operation": "protein_conservation_result", "arguments": {"request": request}}))
    assert worker.main([str(path), str(result_path)]) == 0
    result = json.loads(result_path.read_bytes())
    assert result["version"] == worker.OUTPUT_VERSION
    for key in ("alignment", "population", "components", "context", "value"):
        assert _document(directory, result[key]) is not None
    with pytest.raises(ValueError, match="worker_result_already_exists"):
        worker.main([str(path), str(result_path)])


def test_cli_preserves_observations_on_finite_calculator_error(tmp_path, monkeypatch):
    request = _request(tmp_path)
    directory = _out(tmp_path, "result")
    path, result_path = directory / "request.json", directory / "worker-result.json"
    path.write_bytes(_json({"operation": "protein_conservation_result", "arguments": {"request": request}}))
    def fail(*args, **kwargs):
        raise ValueError("engineered_late_failure")
    monkeypatch.setattr(worker, "literal_site_conservation", fail)
    assert worker.main([str(path), str(result_path)]) == 2
    assert json.loads(result_path.read_bytes()) == {"code": "engineered_late_failure", "exception_type": "ValueError"}
    assert (directory / "alignment.json").exists() and (directory / "context.json").exists()


@pytest.mark.parametrize("kind", ["operation", "arguments", "reserved_result"])
def test_cli_rejects_invalid_envelope_or_result_collision_before_input(tmp_path, monkeypatch, kind):
    request = _request(tmp_path)
    directory = _out(tmp_path, "result")
    payload = {"operation": "protein_conservation_result", "arguments": {"request": request}}
    if kind == "operation": payload["operation"] = "native"
    elif kind == "arguments": payload["arguments"]["extra"] = True
    path = directory / "request.json"
    path.write_bytes(_json(payload))
    result = directory / ("alignment.json" if kind == "reserved_result" else "worker-result.json")
    monkeypatch.setattr(worker, "run_protein_conservation_result", _forbidden)
    with pytest.raises(ValueError):
        worker.main([str(path), str(result)])
    assert {p.name for p in directory.iterdir()} == {"request.json"}
