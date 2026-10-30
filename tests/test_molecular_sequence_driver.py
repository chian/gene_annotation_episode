"""Private writer boundaries; genuine selected-source joins require explicit opt-in."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from gene_annotation_episode import molecular_sequence_driver as driver
from gene_annotation_episode.glycosylation_measurements import build_glycosylation_sheet
from gene_annotation_episode.native_file_capture import _declaration


N_OPERATION = "find_n_glycosylation_motifs"
O_OPERATION = "predict_o_glycosylation_hotspots"
N_LOG = ("# N-linked glycosylation sequon scan (N-X-[S/T], X≠P)\n"
    "Sequence length: 3\nTotal sequons found: 1\n\nPositions (1-based):\n- 1: NAT")


def file_pin(path):
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    return file_pin(path)


def selected_request(selection=None, context=None, *, mode="native"):
    if selection is None:
        selection = {"version": "molecular_sequence_request_v2", "operation": N_OPERATION,
            "arguments": {"sequence": "NAT", "allow_overlap": False}, "deployment": {}}
    if context is None and mode == "native":
        context = {"input_ref": None, "input_mapping": None}
    return {"version": driver.REQUEST_VERSION, "mode": mode,
        "attempt_identity": {"run_id": "engineering-control-run", "episode_id": "engineering-control-episode",
            "resource_id": "explicit-control-resource", "operation_key": "explicit-control-action",
            "execution_id": "explicit-control-execution"},
        "selection": deepcopy(selection), "scientific_context": deepcopy(context)}


def engineered_capture(selection, *, failure=None):
    # This is a driver protocol fixture, not observed native scientific output.
    return {"version": "molecular_sequence_execution_v2", "request": deepcopy(selection),
        "request_canonical_sha256": None, "stage": "call" if failure else "completed",
        "native_record": {"schema": "biomni_glycosylation_log_native_v1",
            "outcome": "failed" if failure else "completed", "result": None if failure else N_LOG,
            "failure": deepcopy(failure), "source_identity": {"path": "/engineering/control/not-native.py",
                "callable": N_OPERATION, "sha256": "0" * 64}},
        "native_call_state": "raised" if failure else "returned", "reference_data": None,
        "execution_receipt": {"qualification": "engineered driver protocol fixture; no native call"},
        "stdout": "", "stderr": "", "failure": deepcopy(failure)}


def forbid_helper(*args, **kwargs):
    raise AssertionError("this driver path must not invoke a native helper")


def run_request(tmp_path, request, *, label="output"):
    request_path = tmp_path / (label + "-request.json")
    pin = write_json(request_path, request)
    before = request_path.read_bytes()
    output = tmp_path / label
    result = driver.run_molecular_sequence_driver(request_file=pin, output_directory=str(output))
    assert request_path.read_bytes() == before
    return result, output, pin


def check_declarations(result, output, present):
    assert set(result["files"]) == {"capture", "sheet", "components"}
    for role, declared in result["files"].items():
        assert _declaration(declared) == declared  # Actual existing capture-consumer contract.
        path = output / declared["relative_path"]
        assert declared["relative_path"] == role + ".json" and declared["format"] == "json"
        assert (declared["state"] == "present") is (role in present)
        if role in present:
            raw = path.read_bytes()
            assert declared["sha256"] == hashlib.sha256(raw).hexdigest()
            assert declared["size_bytes"] == len(raw)
        else:
            assert not path.exists() and declared["sha256"] is declared["size_bytes"] is None
    assert json.loads((output / "declaration.json").read_bytes()) == result
    assert "not authenticated producing-attempt custody" in result["qualification"]
    assert "does not authenticate full driver/calculator" in result["qualification"]


def test_one_helper_call_retains_exact_inputs_and_separate_artifacts(tmp_path, monkeypatch):
    request = selected_request()
    capture = engineered_capture(request["selection"])
    calls = []

    def execute(value):
        calls.append(deepcopy(value))
        return deepcopy(capture)

    monkeypatch.setattr(driver, "execute_molecular_sequence_request", execute)
    result, output, pin = run_request(tmp_path, request)
    assert calls == [request["selection"]]
    assert result["request_file"] == pin and result["request_file_pin_verified"] is True
    assert result["attempt_identity"] == request["attempt_identity"]
    assert result["native_failure"] is result["driver_failure"] is None
    assert json.loads((output / "capture.json").read_bytes()) == capture
    sheet = json.loads((output / "sheet.json").read_bytes())
    assert sheet["inputs"]["sequence"] == request["selection"]["arguments"]["sequence"]
    assert sheet["inputs"]["native_log"] == N_LOG
    components = json.loads((output / "components.json").read_bytes())
    assert components["summary"]["native_reported_total_count"] == 1
    for value in (capture, sheet, components):
        assert all(identity not in json.dumps(value) for identity in request["attempt_identity"].values())
    check_declarations(result, output, {"capture", "sheet", "components"})


@pytest.mark.parametrize("change", ["digest", "size"])
def test_request_pin_conflict_stops_before_helper_and_declares_no_artifacts(tmp_path, monkeypatch, change):
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", forbid_helper)
    pin = write_json(tmp_path / "request.json", selected_request())
    before = (tmp_path / "request.json").read_bytes()
    pin["sha256" if change == "digest" else "size_bytes"] = "0" * 64 if change == "digest" else pin["size_bytes"] + 1
    output = tmp_path / "output"
    result = driver.run_molecular_sequence_driver(request_file=pin, output_directory=str(output))
    assert result["request_file_pin_verified"] is False
    assert result["driver_failure"]["stage"] == "read_request"
    assert result["native_call_state"] is result["native_failure"] is None
    assert (tmp_path / "request.json").read_bytes() == before
    check_declarations(result, output, set())


@pytest.mark.parametrize("raw", [b'{"version":1,"version":2}', b'{"invalid":NaN}', b'{"invalid":1e999}'])
def test_selected_json_rejection_keeps_verified_pin_without_execution(tmp_path, monkeypatch, raw):
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", forbid_helper)
    path = tmp_path / "request.json";path.write_bytes(raw)
    output = tmp_path / "output"
    result = driver.run_molecular_sequence_driver(request_file=file_pin(path), output_directory=str(output))
    assert result["request_file_pin_verified"] is True
    assert result["driver_failure"]["stage"] == "parse_request"
    assert result["native_call_state"] is result["native_failure"] is None
    check_declarations(result, output, set())


def test_unknown_scientific_context_is_not_silently_dropped(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", forbid_helper)
    request = selected_request();request["scientific_context"]["substitute_sequence"] = "AAA"
    result, output, _ = run_request(tmp_path, request)
    assert result["driver_failure"]["stage"] == "validate_request"
    assert result["native_call_state"] is None
    check_declarations(result, output, set())


def test_unexpected_helper_exception_is_a_driver_failure_with_native_state_unknown(tmp_path, monkeypatch):
    def broken(value):
        raise RuntimeError("engineered helper-boundary interruption")

    monkeypatch.setattr(driver, "execute_molecular_sequence_request", broken)
    result, output, _ = run_request(tmp_path, selected_request())
    assert result["native_call_state"] == "unknown" and result["native_failure"] is None
    assert result["driver_failure"] == {"stage": "invoke_helper", "exception_type": "RuntimeError",
        "message": "engineered helper-boundary interruption"}
    check_declarations(result, output, set())


def test_source_failure_and_capture_serialization_failure_remain_separate(tmp_path, monkeypatch):
    request = selected_request()
    failure = {"stage": "call", "exception_type": "EngineeringControl",
        "message": "engineered upstream failure; no scientific measurement"}
    capture = engineered_capture(request["selection"], failure=failure)
    capture["stdout"] = object()  # Explicit writer-serialization control, not native output.
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", lambda value: capture)
    result, output, _ = run_request(tmp_path, request)
    assert result["native_failure"] == failure and result["native_call_state"] == "raised"
    assert result["driver_failure"]["stage"] == "write_capture"
    assert result["driver_failure"]["exception_type"] == "TypeError"
    check_declarations(result, output, set())


def test_sheet_serialization_failure_preserves_capture_without_inventing_later_outputs(tmp_path, monkeypatch):
    request = selected_request()
    capture = engineered_capture(request["selection"])
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", lambda value: deepcopy(capture))
    monkeypatch.setattr(driver, "_sheet", lambda *args: {"engineered_nonfinite_cell": float("nan")})
    monkeypatch.setattr(driver, "_calculate", forbid_helper)
    result, output, _ = run_request(tmp_path, request)
    assert result["native_failure"] is None and result["native_call_state"] == "returned"
    assert result["driver_failure"]["stage"] == "write_sheet"
    assert json.loads((output / "capture.json").read_bytes()) == capture
    check_declarations(result, output, {"capture"})


def test_no_native_record_preserves_helper_failure_without_fabricating_a_sheet(tmp_path, monkeypatch):
    request = selected_request()
    capture = engineered_capture(request["selection"], failure={"stage": "deployment_verification",
        "exception_type": "EngineeringControl", "message": "engineered unstarted helper selection"})
    capture.update(native_call_state="not_started", native_record=None)
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", lambda value: deepcopy(capture))
    result, output, _ = run_request(tmp_path, request)
    assert result["native_failure"] == capture["failure"] and result["driver_failure"] is None
    assert result["native_call_state"] == "not_started"
    check_declarations(result, output, {"capture"})


def supplied_saved_sheet(tmp_path, *, corrupt=False):
    sheet = build_glycosylation_sheet(N_OPERATION, N_LOG, sequence="NAT", parameters={"allow_overlap": False})
    if corrupt:
        sheet["rows"][0]["cells"]["operand_symbols"] = "AAA"
    path = tmp_path / "supplied-sheet.json"
    # Deliberately distinct formatting proves the original bytes are retained.
    path.write_text(json.dumps(sheet, ensure_ascii=True, separators=(",", ":")) + "\n\n")
    return path, selected_request({"operation": N_OPERATION, "sheet_file": file_pin(path)}, mode="saved_sheet")


def test_saved_only_uses_authoritative_sheet_without_native_call_or_parameter_changes(tmp_path, monkeypatch):
    path, request = supplied_saved_sheet(tmp_path)
    before = path.read_bytes()
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", forbid_helper)
    result, output, _ = run_request(tmp_path, request)
    assert result["native_call_state"] == "not_requested"
    assert result["driver_failure"] is result["native_failure"] is None
    assert path.read_bytes() == (output / "sheet.json").read_bytes() == before
    components = json.loads((output / "components.json").read_bytes())
    assert components["parameters"]["supplied"] == {"allow_overlap": False}
    assert components["summary"]["native_reported_total_count"] == 1
    check_declarations(result, output, {"sheet", "components"})


def test_corrupt_saved_sheet_is_retained_without_repair_or_new_native_work(tmp_path, monkeypatch):
    path, request = supplied_saved_sheet(tmp_path, corrupt=True)
    before = path.read_bytes()
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", forbid_helper)
    result, output, _ = run_request(tmp_path, request)
    assert result["native_call_state"] == "not_requested" and result["native_failure"] is None
    assert result["driver_failure"]["stage"] == "calculate"
    assert result["driver_failure"]["message"].startswith("glycosylation_saved_sheet_conflict:")
    assert path.read_bytes() == (output / "sheet.json").read_bytes() == before
    check_declarations(result, output, {"sheet"})


def test_saved_operation_conflict_cannot_relabel_a_sheet(tmp_path, monkeypatch):
    path, request = supplied_saved_sheet(tmp_path)
    request["selection"]["operation"] = O_OPERATION
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", forbid_helper)
    result, output, _ = run_request(tmp_path, request)
    assert result["driver_failure"]["stage"] == "validate_saved_sheet"
    assert result["driver_failure"]["message"] == "molecular_sequence_driver_saved_sheet_operation_conflict"
    assert (output / "sheet.json").read_bytes() == path.read_bytes()
    check_declarations(result, output, {"sheet"})


def test_existing_output_directory_is_never_reexecuted_or_overwritten(tmp_path, monkeypatch):
    path, request = supplied_saved_sheet(tmp_path)
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", forbid_helper)
    result, output, pin = run_request(tmp_path, request)
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    with pytest.raises(FileExistsError):
        driver.run_molecular_sequence_driver(request_file=pin, output_directory=str(output))
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before
    assert result["driver_failure"] is None


def test_cli_processes_one_pinned_saved_sheet_with_exact_declarations(tmp_path):
    path, request = supplied_saved_sheet(tmp_path)
    pin = write_json(tmp_path / "cli-request.json", request)
    output = tmp_path / "cli-output"
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(dict.fromkeys([str(Path(__file__).resolve().parents[1]),
        *(value for value in sys.path if value and Path(value).is_absolute())]))
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run([sys.executable, "-B", "-S", "-m", "gene_annotation_episode.molecular_sequence_driver",
        "--request-file", pin["path"], "--request-sha256", pin["sha256"],
        "--request-size-bytes", str(pin["size_bytes"]), "--output-directory", str(output)],
        cwd=Path(__file__).resolve().parents[1], env=environment, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    result = json.loads(completed.stdout)
    assert result["request_file_pin_verified"] is True and result["native_call_state"] == "not_requested"
    assert (output / "sheet.json").read_bytes() == path.read_bytes()
    check_declarations(result, output, {"sheet", "components"})


@pytest.fixture(scope="module")
def native_reports():
    rows = []
    yield rows
    if os.environ.get("HMMER_NATIVE_ORACLE_MOLECULAR_DRIVER_NATIVE") == "1":
        (Path(os.environ["HMMER529_ATTEMPT"]) / "molecular-sequence-driver-native.json").write_text(
            json.dumps({"schema": "molecular_sequence_private_driver_verification_v1",
                "qualification": "Genuine selected finite-driver engineering joins; digest declarations "
                    "do not authenticate producing-attempt custody, installation or a public child return.",
                "cases": rows}, indent=2, allow_nan=False) + "\n")


@pytest.fixture
def genuine_deployments():
    if os.environ.get("HMMER_NATIVE_ORACLE_MOLECULAR_DRIVER_NATIVE") != "1":
        pytest.skip("explicit selected native finite-driver verification within bounded529 only")
    assert os.environ.get("HMMER529_ATTEMPT")
    return {"molecular": json.loads(Path(os.environ["HMMER_NATIVE_ORACLE_MOLECULAR_DEPLOYMENT_FILE"]).read_bytes()),
        "glyco": json.loads(Path(os.environ["HMMER_NATIVE_ORACLE_GLYCO_DEPLOYMENT_FILE"]).read_bytes())}


@pytest.mark.parametrize("label,operation,arguments,context,profile", [
    ("orf", "annotate_open_reading_frames", {"sequence": "ATGAAAATGTAA", "min_length": 6,
        "search_reverse": False, "filter_subsets": False}, {"subject_ref": None, "parent_mapping": None}, "molecular"),
    ("placement", "align_sequences", {"long_seq": "AAAACCCCAAAA", "short_seqs": "AAAA"},
        {"target_ref": None, "primer_refs": None, "target_mapping": None, "primer_mappings": None}, "molecular"),
    ("n", N_OPERATION, {"sequence": "NAT", "allow_overlap": False},
        {"input_ref": None, "input_mapping": None}, "glyco"),
    ("o", O_OPERATION, {"sequence": "ASA", "window": 3, "min_st_fraction": 0.3333,
        "disallow_proline_next": True}, {"input_ref": None, "input_mapping": None}, "glyco"),
    ("source_error", O_OPERATION, {"sequence": "SSSS", "window": 3.5, "min_st_fraction": 0.4,
        "disallow_proline_next": True}, {"input_ref": None, "input_mapping": None}, "glyco"),
])
def test_genuine_selected_driver_joins_existing_authorities_once(tmp_path, monkeypatch, genuine_deployments,
        native_reports, label, operation, arguments, context, profile):
    deployment = genuine_deployments[profile]
    version = "molecular_sequence_request_v1" if profile == "molecular" else "molecular_sequence_request_v2"
    selection = {"version": version, "operation": operation, "arguments": arguments, "deployment": deployment}
    request = selected_request(selection, context)
    request["attempt_identity"]["operation_key"] += ":" + label
    actual_helper, calls = driver.execute_molecular_sequence_request, []

    def once(value):
        calls.append(deepcopy(value))
        return actual_helper(value)

    monkeypatch.setattr(driver, "execute_molecular_sequence_request", once)
    result, output, pin = run_request(tmp_path, request)
    row = {"case": label, "request_file": pin, "output_directory": str(output), "declaration": result,
        "helper_call_count": len(calls)}
    native_reports.append(row)
    assert calls == [selection] and result["driver_failure"] is None, result
    check_declarations(result, output, {"capture", "sheet", "components"})
    capture = json.loads((output / "capture.json").read_bytes())
    sheet = json.loads((output / "sheet.json").read_bytes())
    components = json.loads((output / "components.json").read_bytes())
    row.update(capture=capture, sheet=sheet, components=components)
    assert capture["request"] == selection
    assert capture["execution_receipt"]["module_load"]["source_file"] == deployment["module"]
    assert capture["execution_receipt"]["observed_callable"]["name"] == operation
    assert capture["execution_receipt"]["software_files_file"] == deployment["software_files_file"]
    if label == "source_error":
        assert result["native_call_state"] == "raised"
        assert result["native_failure"] == capture["failure"]
        assert result["native_failure"]["exception_type"] == "TypeError"
        assert capture["native_record"]["result"] is None
        assert sheet["status"] == components["status"] == "failed"
        assert components["summary"]["native_reported_total_count"] is None
    else:
        assert result["native_call_state"] == "returned" and result["native_failure"] is None
        if label == "orf":
            assert sheet["inputs"]["native_record"] == capture["native_record"]
            assert sheet["inputs"]["genetic_code"] == capture["reference_data"]["genetic_code_snapshot"]
            assert components["summary"]["reported_row_count"] == 2
            assert components["summary"]["retained_length_sum_nt"] == 18
        elif label == "placement":
            assert sheet["inputs"]["native_record"] == capture["native_record"]
            assert components["summary"]["retained_native_hit_occurrence_count"] == 4
            assert components["summary"]["mismatch_count_sum"] == 2
        else:
            assert sheet["inputs"]["native_log"] == capture["native_record"]["result"]
            assert components["summary"]["native_reported_total_count"] == 1
            assert components["summary"]["scan_exhaustiveness_verified"] is False
        if label == "o":
            assert components["rows"][0]["cells"]["calculated_st_fraction"] == 1 / 3
            assert components["rows"][0]["native_values"]["st_fraction_token"] == "0.333"
            saved_request = selected_request({"operation": operation, "sheet_file": file_pin(output / "sheet.json")},
                mode="saved_sheet")
            monkeypatch.setattr(driver, "execute_molecular_sequence_request", forbid_helper)
            saved, saved_output, _ = run_request(tmp_path, saved_request, label="saved-output")
            assert saved["native_call_state"] == "not_requested" and saved["driver_failure"] is None
            assert json.loads((saved_output / "components.json").read_bytes()) == components
            assert (saved_output / "sheet.json").read_bytes() == (output / "sheet.json").read_bytes()
            check_declarations(saved, saved_output, {"sheet", "components"})
            row["saved_only"] = {"declaration": saved, "output_directory": str(saved_output),
                "native_helper_forbidden": True, "same_components": True}
