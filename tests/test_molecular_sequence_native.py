"""Private-protocol controls; genuine selected execution requires explicit opt-in."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

import pytest

from gene_annotation_episode import molecular_sequence_native as native
from gene_annotation_episode.glycosylation_measurements import (
    build_glycosylation_sheet, calculate_glycosylation_components,
)
from gene_annotation_episode.orf_measurements import build_orf_sheet, calculate_orf_components
from gene_annotation_episode.primer_placement_measurements import (
    build_primer_placement_sheet, calculate_primer_placement_components,
)
from gene_annotation_episode.sequence_mapping import VERSION as MAPPING_VERSION


def request(arguments=None, operation="annotate_open_reading_frames", deployment=None):
    return {"version": native.REQUEST_VERSION, "operation": operation,
        "arguments": ({"sequence": "ATGAAAATGTAA", "min_length": 6,
            "search_reverse": False, "filter_subsets": False} if arguments is None else deepcopy(arguments)),
        "deployment": {} if deployment is None else deepcopy(deployment)}


@pytest.mark.parametrize("change,code,path", [
    ({"operation": "pcr_simple"}, "operation_not_supported", "/operation"),
    ({"version": "unselected"}, "request_version_required", "/version"),
    ({"arguments": {"sequence": "ATGTAA"}}, "closed_fields_required", "/arguments"),
    ({"deployment": {}}, "closed_fields_required", "/deployment"),
])
def test_invalid_private_request_fails_before_native_file_read(monkeypatch, change, code, path):
    selected = request();selected.update(change)
    before = deepcopy(selected);reads = []

    def forbidden(*args, **kwargs):
        reads.append((args, kwargs))
        raise AssertionError("invalid request attempted native file read")

    with monkeypatch.context() as guarded:
        guarded.setattr(Path, "read_bytes", forbidden)
        result = native.execute_molecular_sequence_request(selected)
    assert not reads
    assert result["failure"]["code"] == "molecular_sequence_" + code
    assert result["failure"]["path"] == path
    assert result["execution_receipt"]["observed_callable"] is None
    assert result["native_call_state"] == "not_started"
    assert result["request"] == selected == before


def test_nonfinite_request_retains_rejection_without_inventing_native_output():
    selected = request();selected["arguments"]["min_length"] = float("nan")
    result = native.execute_molecular_sequence_request(selected)
    assert result["failure"]["code"] == "molecular_sequence_finite_json_request_required"
    assert result["failure"]["path"] == "/arguments/min_length"
    assert result["failure"]["details"] == {"value_type": "float", "nonfinite_token": "nan"}
    assert result["request"] is None and result["request_canonical_sha256"] is None
    assert result["native_record"] is None
    assert result["execution_receipt"]["observed_callable"] is None


def test_manifest_artifact_identity_conflict_is_not_resolved_or_opened(monkeypatch):
    pin = {"path": "/explicit/unavailable/input", "sha256": "0" * 64, "size_bytes": 0}
    selected = request(deployment={"version": native.DEPLOYMENT_VERSION,
        "runtime": {"executable": pin, "home": "/explicit/runtime"},
        "module": {**pin, "sha256": native.SOURCE_SHA256},
        "import_roots": ["/explicit/application"], "software_files_ref": "artifact_" + "1" * 64,
        "software_files_file": pin})
    reads = []

    def forbidden(*args, **kwargs):
        reads.append((args, kwargs))
        raise AssertionError("conflicting manifest attempted a read")

    with monkeypatch.context() as guarded:
        guarded.setattr(Path, "read_bytes", forbidden)
        result = native.execute_molecular_sequence_request(selected)
    assert not reads
    assert result["failure"]["code"] == "molecular_sequence_manifest_artifact_identity_mismatch"
    assert result["native_record"]["source_identity"] is None
    assert result["native_record"]["result"] is None


@pytest.fixture
def selected_deployment():
    if os.environ.get("HMMER_NATIVE_ORACLE_MOLECULAR_NATIVE") != "1":
        pytest.skip("explicit selected genuine runtime/source/manifest execution only")
    path = Path(os.environ["HMMER_NATIVE_ORACLE_MOLECULAR_DEPLOYMENT_FILE"])
    value = json.loads(path.read_bytes())
    assert value["version"] == native.DEPLOYMENT_VERSION
    # This is a host-prepared engineering input, not proof of a production
    # Store grant, installation, registry operation or typed child return.
    assert value["module"]["sha256"] == native.SOURCE_SHA256
    return value


def write_manifest_control(tmp_path, deployment, rows, label):
    changed = deepcopy(deployment)
    path = tmp_path / (label + ".json")
    raw = json.dumps(rows, allow_nan=False, sort_keys=True, indent=2).encode()
    path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    changed["software_files_ref"] = "artifact_" + digest
    changed["software_files_file"] = {"path": str(path.resolve()), "sha256": digest,
        "size_bytes": len(raw)}
    return changed


def test_selected_manifest_bytes_must_match_host_file_pin(selected_deployment):
    changed = deepcopy(selected_deployment)
    changed["software_files_file"]["sha256"] = "0" * 64
    changed["software_files_ref"] = "artifact_" + "0" * 64
    result = native.execute_molecular_sequence_request(request(deployment=changed))
    assert result["failure"]["code"] == "molecular_sequence_selected_file_mismatch"
    assert result["failure"]["path"] == "/deployment/software_files_file"
    assert result["execution_receipt"]["module_load"]["state"] == "not_started"
    assert result["execution_receipt"]["observed_callable"] is None


def test_selected_runtime_cannot_fall_back_to_current_python(selected_deployment):
    changed = deepcopy(selected_deployment)
    changed["runtime"]["executable"] = deepcopy(changed["module"])
    result = native.execute_molecular_sequence_request(request(deployment=changed))
    assert result["failure"]["code"] == "molecular_sequence_executing_interpreter_mismatch"
    assert result["execution_receipt"]["module_load"]["state"] == "not_started"
    assert result["native_call_state"] == "not_started"


def test_selected_original_source_pin_cannot_be_replaced(selected_deployment):
    changed = deepcopy(selected_deployment);changed["module"]["sha256"] = "0" * 64
    result = native.execute_molecular_sequence_request(request(deployment=changed))
    assert result["failure"]["code"] == "molecular_sequence_original_source_pin_required"
    assert result["native_record"]["source_identity"] is None
    assert result["native_record"]["result"] is None


def test_current_helper_must_be_in_host_selected_application_pins(selected_deployment, tmp_path):
    rows = json.loads(Path(selected_deployment["software_files_file"]["path"]).read_bytes())
    helper_path = str(Path(native.__file__).resolve())
    assert any(row["path"] == helper_path for row in rows)
    changed = write_manifest_control(tmp_path, selected_deployment,
        [row for row in rows if row["path"] != helper_path], "missing-current-helper")
    result = native.execute_molecular_sequence_request(request(deployment=changed))
    assert result["failure"]["code"] == "molecular_sequence_file_not_selected"
    assert result["failure"]["path"] == "/runtime/helper_file"
    assert result["execution_receipt"]["module_load"]["state"] == "not_started"
    assert result["execution_receipt"]["observed_callable"] is None


def test_duplicate_manifest_paths_are_explicitly_rejected(selected_deployment, tmp_path):
    rows = json.loads(Path(selected_deployment["software_files_file"]["path"]).read_bytes())
    changed = write_manifest_control(tmp_path, selected_deployment, [*rows, rows[0]], "duplicate-pin")
    result = native.execute_molecular_sequence_request(request(deployment=changed))
    assert result["failure"]["code"] == "molecular_sequence_duplicate_manifest_path"
    assert result["execution_receipt"]["observed_callable"] is None


def test_real_library_pin_conflict_stops_before_scientific_call(selected_deployment, tmp_path):
    rows = json.loads(Path(selected_deployment["software_files_file"]["path"]).read_bytes())
    support = Path(selected_deployment["module"]["path"]).parents[2]
    bs4_path = str((support / "bs4/__init__.py").resolve())
    assert any(row["path"] == bs4_path for row in rows)
    changed_rows = [{**row, "sha256": "0" * 64} if row["path"] == bs4_path else row for row in rows]
    changed = write_manifest_control(tmp_path, selected_deployment, changed_rows, "wrong-genuine-bs4-pin")
    before_path, before_bytecode = list(sys.path), sys.dont_write_bytecode
    result = native.execute_molecular_sequence_request(request(deployment=changed))
    assert result["failure"]["code"] == "molecular_sequence_import_file_mismatch"
    assert result["failure"]["path"] == "/libraries/bs4"
    assert result["execution_receipt"]["module_load"]["state"] == "loaded"
    assert result["execution_receipt"]["observed_callable"] is None
    assert result["native_record"]["source_identity"] is None
    assert result["native_record"]["result"] is None and result["native_call_state"] == "not_started"
    assert sys.path == before_path and sys.dont_write_bytecode == before_bytecode


def mapping(length, subject):
    return {"version": MAPPING_VERSION, "units_per_symbol": 1, "symbol_length": length,
        "path": [{"subject_ref": subject, "start": 0, "end": length, "unit": "nt", "strand": "+"}]}


def numerical_result(capture):
    arguments = capture["request"]["arguments"]
    if capture["request"]["operation"] == "annotate_open_reading_frames":
        sheet = build_orf_sheet(capture["native_record"], input_sequence=arguments["sequence"],
            subject_ref="supplied:helper-orf", parent_mapping=mapping(len(arguments["sequence"]), "source:helper-orf"),
            request={key: arguments[key] for key in ("min_length", "search_reverse", "filter_subsets")},
            genetic_code=capture["reference_data"]["genetic_code_snapshot"])
        return {"sheet": sheet, "components": calculate_orf_components(sheet)}
    primers = arguments["short_seqs"]
    occurrences = [primers] if type(primers) is str else primers
    sheet = build_primer_placement_sheet(capture["native_record"],
        target_sequence=arguments["long_seq"], primers=primers, target_ref="supplied:helper-target",
        primer_refs=["supplied:helper-primer:" + str(i) for i in range(len(occurrences))],
        target_mapping=mapping(len(arguments["long_seq"]), "source:helper-target"),
        primer_mappings=[mapping(len(primer), "source:helper-primer:" + str(i))
            if type(primer) is str and primer else None for i, primer in enumerate(occurrences)])
    return {"sheet": sheet, "components": calculate_primer_placement_components(sheet)}


def test_genuine_selected_helper_preserves_original_outputs_errors_and_numerical_inputs(selected_deployment):
    orf_arguments = {"sequence": "ATGAAAATGTAA", "min_length": 6,
        "search_reverse": False, "filter_subsets": False}
    cases = [
        ("orf_nested", "annotate_open_reading_frames", orf_arguments),
        ("orf_filtered", "annotate_open_reading_frames", {**orf_arguments, "filter_subsets": True}),
        ("orf_reverse", "annotate_open_reading_frames", {**orf_arguments, "sequence": "TTACAT", "search_reverse": True}),
        ("orf_ambiguity", "annotate_open_reading_frames", {**orf_arguments, "sequence": "ATGTARTAA"}),
        ("orf_error", "annotate_open_reading_frames", {**orf_arguments, "sequence": "ATG?AATAA"}),
        ("primer_four", "align_sequences", {"long_seq": "AAAACCCCAAAA", "short_seqs": "AAAA"}),
        ("primer_reverse", "align_sequences", {"long_seq": "AAATGGG", "short_seqs": "CGTT"}),
        ("primer_duplicates", "align_sequences", {"long_seq": "ATATAT", "short_seqs": ["ATAT", "ATAT"]}),
        ("primer_noncanonical", "align_sequences", {"long_seq": "ARAC", "short_seqs": "AR"}),
        ("primer_empty", "align_sequences", {"long_seq": "AC", "short_seqs": ""}),
        ("primer_error", "align_sequences", {"long_seq": "AA", "short_seqs": [None]}),
    ]
    observed = {"schema": "molecular_sequence_native_helper_verification_v1",
        "qualification": "explicit genuine selected private helper controls; no production installation, registry or child-return claim",
        "cases": []}
    failure = None
    try:
        for label, operation, arguments in cases:
            selected = request(arguments, operation, selected_deployment)
            before = deepcopy(selected)
            before_path, before_bytecode = list(sys.path), sys.dont_write_bytecode
            previous = sys.modules.get("_selected_molecular_sequence_native")
            capture = native.execute_molecular_sequence_request(selected)
            row = {"case": label, "input_origin": "explicit_numerical_control", "capture": capture}
            observed["cases"].append(row)
            assert selected == before
            assert sys.path == before_path and sys.dont_write_bytecode == before_bytecode
            assert sys.modules.get("_selected_molecular_sequence_native") is previous
            assert capture["request"] == selected
            canonical = json.dumps(selected, sort_keys=True, ensure_ascii=False,
                allow_nan=False, separators=(",", ":")).encode()
            assert capture["request_canonical_sha256"] == hashlib.sha256(canonical).hexdigest()
            assert capture["execution_receipt"]["helper_file"]["path"] == str(Path(native.__file__).resolve())
            assert capture["execution_receipt"]["module_load"]["state"] == "loaded", capture
            assert capture["execution_receipt"]["observed_callable"]["name"] == operation
            assert capture["native_record"]["source_identity"]["callable"] == operation
            assert capture["native_record"]["source_identity"]["path"] == selected_deployment["module"]["path"]
            assert all(row["file"]["path"] for row in capture["execution_receipt"]["imported_files"])
            assert {row["distribution_name"] for row in capture["execution_receipt"]["libraries"]} == {
                "pandas", "requests", "biopython", "beautifulsoup4", "soupsieve", "typing_extensions"}
            assert capture["native_call_state"] == ("raised" if label.endswith("_error") else "returned")
            if label.endswith("_error"):
                assert capture["stage"] == "call" and capture["failure"] is not None
            else:
                assert capture["stage"] == "completed" and capture["failure"] is None
            row.update(numerical_result(capture))
            assert row["sheet"]["inputs"]["native_record"] == capture["native_record"]
        assert_actual_controls(observed)
    except Exception as error:
        failure = {"exception_type": type(error).__name__, "message": str(error),
            "traceback": traceback.format_exc()}
        raise
    finally:
        observed["verification_error"] = failure
        (Path(os.environ["HMMER529_ATTEMPT"]) / "molecular-sequence-native-helper.json").write_text(
            json.dumps(observed, allow_nan=False, indent=2))



def assert_actual_controls(observed):
    by = {row["case"]: row for row in observed["cases"]}
    assert by["orf_nested"]["capture"]["native_record"]["result"]["orfs"] == [
        ["ATGAAAATGTAA", "MKM", 0, 12, "+", 1], ["ATGTAA", "M", 6, 12, "+", 1]]
    assert by["orf_nested"]["components"]["summary"]["retained_length_sum_nt"] == 18
    assert by["orf_nested"]["components"]["summary"]["mean_retained_orf_length_nt"] == 9
    assert by["orf_filtered"]["capture"]["native_record"]["result"]["orfs"] == [
        ["ATGAAAATGTAA", "MKM", 0, 12, "+", 1]]
    assert by["orf_reverse"]["capture"]["native_record"]["result"]["orfs"] == [
        ["ATGTAA", "M", 0, 6, "-", -1]]
    assert by["orf_ambiguity"]["capture"]["native_record"]["result"]["orfs"] == [
        ["ATGTARTAA", "M", 0, 9, "+", 1]]
    assert by["orf_ambiguity"]["components"]["rows"][0]["translation"]["termination_codon"] == "TAR"
    assert by["orf_ambiguity"]["components"]["rows"][0]["translation"]["untranslated_suffix_nt"] == 3
    forward = by["primer_four"]["capture"]["native_record"]["result"]["sequences"][0]["alignments"]
    assert forward == [
        {"position": 0, "strand": "+", "mismatches": []},
        {"position": 1, "strand": "+", "mismatches": [[3, "A", "C"]]},
        {"position": 7, "strand": "+", "mismatches": [[0, "A", "C"]]},
        {"position": 8, "strand": "+", "mismatches": []}]
    assert by["primer_four"]["components"]["summary"]["mismatch_count_sum"] == 2
    reverse = by["primer_reverse"]["components"]["groups"][0]["hits"][0]
    assert reverse["native_hit"] == {"position": 1, "strand": "-", "mismatches": [[2, "C", "T"]]}
    assert reverse["mismatches"][0]["original_primer_position"] == 1
    assert by["primer_duplicates"]["components"]["summary"]["retained_native_hit_occurrence_count"] == 8
    noncanonical = by["primer_noncanonical"]["components"]["groups"][0]["hits"]
    assert noncanonical[2]["oriented_source_primer"] == "RT"
    assert all(hit["mismatch_count"] is None for hit in noncanonical)
    empty = by["primer_empty"]["components"]["groups"][0]["hits"]
    assert len(empty) == 6
    assert all(hit["mismatch_fraction"] == {"numerator": None, "denominator": 0, "value": None} for hit in empty)
    for label, exception, field in (
        ("orf_error", "TranslationError", "reported_row_count"),
        ("primer_error", "AttributeError", "retained_native_hit_occurrence_count")):
        actual = by[label]
        assert actual["capture"]["native_record"]["outcome"] == "failed"
        assert actual["capture"]["native_record"]["result"] is None
        assert actual["capture"]["native_record"]["failure"]["exception_type"] == exception
        assert actual["components"]["summary"][field] is None
    reference = by["orf_nested"]["capture"]["reference_data"]["genetic_code_snapshot"]
    assert reference["biopython_version"] == "1.88"
    assert reference["forward_table"]["ATG"] == "M" and reference["stop_codons"] == ["TAA", "TAG", "TGA"]
    assert by["primer_four"]["capture"]["reference_data"] is None


def request_v2(arguments, operation, deployment):
    return {"version": native.REQUEST_VERSION_V2, "operation": operation,
        "arguments": deepcopy(arguments), "deployment": deepcopy(deployment)}


@pytest.mark.parametrize("version,operation,arguments,deployment_version,module_sha,code,path", [
    ("molecular_sequence_request_v1", "find_n_glycosylation_motifs",
        {"sequence": "NNST", "allow_overlap": False}, "molecular_sequence_deployment_v1",
        native.GLYCO_SOURCE_SHA256, "operation_not_supported", "/operation"),
    ("molecular_sequence_request_v1", "predict_o_glycosylation_hotspots",
        {"sequence": "ASA", "window": 3, "min_st_fraction": 0.3333, "disallow_proline_next": True},
        "molecular_sequence_deployment_v1", native.GLYCO_SOURCE_SHA256,
        "operation_not_supported", "/operation"),
    ("molecular_sequence_request_v2", "find_n_glycosylation_motifs",
        {"sequence": "NNST", "allow_overlap": False}, "molecular_sequence_deployment_v1",
        native.GLYCO_SOURCE_SHA256, "deployment_version_required", "/deployment/version"),
    ("molecular_sequence_request_v1", "annotate_open_reading_frames",
        {"sequence": "ATGTAA", "min_length": 6, "search_reverse": False, "filter_subsets": False},
        "molecular_sequence_deployment_v2", native.SOURCE_SHA256,
        "deployment_version_required", "/deployment/version"),
    ("molecular_sequence_request_v2", "find_n_glycosylation_motifs",
        {"sequence": "NNST", "allow_overlap": False}, "molecular_sequence_deployment_v2",
        native.SOURCE_SHA256, "original_source_pin_required", "/deployment/module/sha256"),
    ("molecular_sequence_request_v2", "annotate_open_reading_frames",
        {"sequence": "ATGTAA", "min_length": 6, "search_reverse": False, "filter_subsets": False},
        "molecular_sequence_deployment_v2", native.GLYCO_SOURCE_SHA256,
        "original_source_pin_required", "/deployment/module/sha256"),
    ("molecular_sequence_request_v2", "align_sequences",
        {"long_seq": "ATAT", "short_seqs": "AT"}, "molecular_sequence_deployment_v2",
        native.GLYCO_SOURCE_SHA256, "original_source_pin_required", "/deployment/module/sha256"),
    ("molecular_sequence_request_v2", "predict_o_glycosylation_hotspots",
        {"sequence": "ASA", "window": 3, "min_st_fraction": 0.4},
        "molecular_sequence_deployment_v2", native.GLYCO_SOURCE_SHA256,
        "closed_fields_required", "/arguments"),
    ("molecular_sequence_request_v2", "find_n_glycosylation_motifs",
        {"sequence": "NNST", "allow_overlap": False, "callable": "list_glycoengineering_resources"},
        "molecular_sequence_deployment_v2", native.GLYCO_SOURCE_SHA256,
        "closed_fields_required", "/arguments"),
])
def test_fixed_private_versions_and_source_profiles_fail_before_file_reads(
        monkeypatch, version, operation, arguments, deployment_version, module_sha, code, path):
    pin = {"path": "/explicit/unavailable/input", "sha256": "0" * 64, "size_bytes": 0}
    selected = {"version": version, "operation": operation, "arguments": arguments,
        "deployment": {"version": deployment_version,
            "runtime": {"executable": pin, "home": "/explicit/runtime"},
            "module": {**pin, "sha256": module_sha}, "import_roots": ["/explicit/application"],
            "software_files_ref": "artifact_" + "0" * 64, "software_files_file": pin}}
    before, reads = deepcopy(selected), []

    def forbidden(*args, **kwargs):
        reads.append((args, kwargs))
        raise AssertionError("invalid source/version profile attempted a file read")

    with monkeypatch.context() as guarded:
        guarded.setattr(Path, "read_bytes", forbidden)
        result = native.execute_molecular_sequence_request(selected)
    assert not reads
    assert result["version"] == ("molecular_sequence_execution_v2"
        if version == "molecular_sequence_request_v2" else "molecular_sequence_execution_v1")
    assert result["failure"]["code"] == "molecular_sequence_" + code
    assert result["failure"]["path"] == path
    assert result["request"] == selected == before
    assert result["native_call_state"] == "not_started"
    assert result["execution_receipt"]["observed_callable"] is None
    assert result["execution_receipt"]["module_load"]["state"] == "not_started"
    assert result["reference_data"] is None
    if result["native_record"] is not None:
        assert result["native_record"]["source_identity"] is None
        assert result["native_record"]["result"] is None


@pytest.fixture
def selected_glyco_deployment():
    if os.environ.get("HMMER_NATIVE_ORACLE_MOLECULAR_NATIVE_V2") != "1":
        pytest.skip("explicit selected genuine glyco runtime/source/manifest execution only")
    value = json.loads(Path(os.environ["HMMER_NATIVE_ORACLE_GLYCO_DEPLOYMENT_FILE"]).read_bytes())
    assert value["version"] == "molecular_sequence_deployment_v2"
    assert value["module"]["sha256"] == "ed3726d318f239e98183a359f18bcd341f4159ef2e400322c6141f77dcd2aff2"
    # Host-prepared engineering input, not production installation or Store admission.
    return value


def test_selected_glyco_module_bytes_cannot_be_replaced(selected_glyco_deployment):
    changed = deepcopy(selected_glyco_deployment)
    changed["module"]["path"] = str(Path(native.__file__).resolve())
    selected = request_v2({"sequence": "NNST", "allow_overlap": False},
        "find_n_glycosylation_motifs", changed)
    result = native.execute_molecular_sequence_request(selected)
    assert result["failure"]["code"] == "molecular_sequence_selected_file_mismatch"
    assert result["failure"]["path"] == "/deployment/module"
    assert result["execution_receipt"]["module_load"]["state"] == "not_started"
    assert result["execution_receipt"]["observed_callable"] is None
    assert result["native_call_state"] == "not_started"
    assert result["native_record"]["source_identity"] is None
    assert result["native_record"]["result"] is None
    assert result["reference_data"] is None


def test_genuine_selected_v2_glyco_outputs_errors_and_existing_numerical_authority(selected_glyco_deployment):
    n_operation, o_operation = "find_n_glycosylation_motifs", "predict_o_glycosylation_hotspots"
    o_arguments = {"sequence": "ASA", "window": 3, "min_st_fraction": 0.3333,
        "disallow_proline_next": True}
    cases = [
        ("n_nonoverlap", n_operation, {"sequence": "NNST", "allow_overlap": False}),
        ("n_overlap", n_operation, {"sequence": "NNST", "allow_overlap": True}),
        ("n_null", n_operation, {"sequence": None, "allow_overlap": False}),
        ("o_unrounded_selected", o_operation, o_arguments),
        ("o_unrounded_excluded", o_operation, {**o_arguments, "min_st_fraction": 0.3334}),
        ("o_fallback_and_proline", o_operation,
            {**o_arguments, "sequence": "STP", "window": 2, "min_st_fraction": 0.4}),
        ("o_native_error", o_operation, {**o_arguments, "sequence": "SSSS", "window": 3.5}),
    ]
    callable_pins = {
        n_operation: "d574294b1088dfb22b6f4242cc0c94b17de4999e86330e07620a83a0b4754c61",
        o_operation: "dac5fa5bd182e0f7d4154ad72289c9adae173864e07e6392ae32d1e1102b2ca6",
    }
    observed = {"schema": "molecular_sequence_native_glyco_helper_verification_v2",
        "qualification": "genuine selected private native controls; no production installation, Store admission, public registration, occupancy or child-return claim",
        "cases": []}
    failure = None
    try:
        for label, operation, arguments in cases:
            selected = request_v2(arguments, operation, selected_glyco_deployment)
            before = deepcopy(selected)
            before_path, before_bytecode = list(sys.path), sys.dont_write_bytecode
            previous = sys.modules.get("_selected_molecular_sequence_native")
            capture = native.execute_molecular_sequence_request(selected)
            row = {"case": label, "input_origin": "explicit_numerical_control", "capture": capture}
            observed["cases"].append(row)
            assert selected == before and capture["request"] == selected
            assert sys.path == before_path and sys.dont_write_bytecode == before_bytecode
            assert sys.modules.get("_selected_molecular_sequence_native") is previous
            assert capture["version"] == "molecular_sequence_execution_v2"
            canonical = json.dumps(selected, sort_keys=True, ensure_ascii=False,
                allow_nan=False, separators=(",", ":")).encode()
            assert capture["request_canonical_sha256"] == hashlib.sha256(canonical).hexdigest()
            receipt, record = capture["execution_receipt"], capture["native_record"]
            assert receipt["software_files_file"] == selected_glyco_deployment["software_files_file"]
            assert receipt["helper_file"]["path"] == str(Path(native.__file__).resolve())
            assert receipt["module_load"]["state"] == "loaded"
            assert receipt["module_load"]["source_file"] == selected_glyco_deployment["module"]
            assert receipt["observed_callable"]["name"] == operation
            assert receipt["observed_callable"]["sha256"] == callable_pins[operation]
            assert record["schema"] == "biomni_glycosylation_log_native_v1"
            assert set(record) == {"schema", "outcome", "result", "failure", "source_identity"}
            assert record["source_identity"] == {"path": selected_glyco_deployment["module"]["path"],
                "callable": operation, "sha256": callable_pins[operation]}
            assert capture["reference_data"] is None and receipt["libraries"] == []
            assert receipt["imported_files"]
            assert all(item["file"]["path"] for item in receipt["imported_files"])
            assert capture["stdout"] == capture["stderr"] == ""
            if label == "o_native_error":
                assert capture["native_call_state"] == "raised" and capture["stage"] == "call"
                assert record["outcome"] == "failed" and record["result"] is None
                assert record["failure"]["exception_type"] == "TypeError"
                assert record["failure"]["traceback"]
            else:
                assert capture["stage"] == "completed" and capture["failure"] is None
                assert capture["native_call_state"] == "returned" and record["outcome"] == "completed"
                assert type(record["result"]) is str
            sheet = build_glycosylation_sheet(operation, record["result"],
                sequence=arguments["sequence"],
                parameters={key: value for key, value in arguments.items() if key != "sequence"},
                native_outcome=record["outcome"], input_ref="supplied:helper-glyco:" + label)
            row.update(sheet=sheet, components=calculate_glycosylation_components(sheet))
            assert sheet["inputs"]["native_log"] == record["result"]
            assert sheet["inputs"]["sequence"] == arguments["sequence"]
            assert sheet["inputs"]["parameters"] == {key: value for key, value in arguments.items() if key != "sequence"}
            assert row["components"]["summary"]["scan_exhaustiveness_verified"] is False
        by = {row["case"]: row for row in observed["cases"]}
        nonoverlap = by["n_nonoverlap"]
        assert nonoverlap["capture"]["native_record"]["result"] == (
            "# N-linked glycosylation sequon scan (N-X-[S/T], X≠P)\n"
            "Sequence length: 4\nTotal sequons found: 1\n\nPositions (1-based):\n- 1: NNS")
        assert nonoverlap["components"]["summary"]["native_reported_total_count"] == 1
        assert nonoverlap["components"]["rows"][0]["cells"]["processed_interval"] == [0, 3]
        overlap = by["n_overlap"]
        assert overlap["components"]["summary"]["native_reported_total_count"] == 2
        assert [row["native_values"]["position_1based"] for row in overlap["components"]["rows"]] == [1, 2]
        assert [row["native_values"]["motif"] for row in overlap["components"]["rows"]] == ["NNS", "NST"]
        assert overlap["components"]["summary"]["usable_checked_row_count"] == 2
        assert by["n_null"]["capture"]["request"]["arguments"]["sequence"] is None
        assert by["n_null"]["components"]["summary"]["original_symbol_count"] is None
        assert by["n_null"]["components"]["summary"]["processed_symbol_count"] == 0
        assert by["n_null"]["components"]["summary"]["native_reported_total_count"] == 0
        chosen = by["o_unrounded_selected"]["components"]
        assert chosen["summary"]["native_reported_total_count"] == 1
        assert chosen["rows"][0]["cells"]["st_count"] == 1
        assert chosen["rows"][0]["cells"]["window_denominator_symbols"] == 3
        assert chosen["rows"][0]["cells"]["calculated_st_fraction"] == 1 / 3
        assert chosen["rows"][0]["native_values"]["st_fraction_token"] == "0.333"
        assert chosen["rows"][0]["cells"]["unrounded_threshold_satisfied"] is True
        assert by["o_unrounded_excluded"]["components"]["summary"]["native_reported_total_count"] == 0
        fallback = by["o_fallback_and_proline"]["components"]
        assert fallback["parameters"]["supplied"]["window"] == 2
        assert fallback["parameters"]["effective"]["window"] == 7
        assert fallback["summary"]["native_reported_total_count"] == 1
        assert fallback["rows"][0]["native_values"]["position_1based"] == 1
        assert fallback["rows"][0]["cells"]["calculated_st_fraction"] == 2 / 3
        assert fallback["rows"][0]["native_values"]["window_start_1based"] == 1
        assert fallback["rows"][0]["native_values"]["window_end_1based"] == 3
        native_error = by["o_native_error"]
        assert native_error["capture"]["request"]["arguments"]["window"] == 3.5
        assert native_error["components"]["summary"]["native_reported_total_count"] is None
        assert native_error["components"]["status"] == "failed"
    except Exception as error:
        failure = {"exception_type": type(error).__name__, "message": str(error),
            "traceback": traceback.format_exc()}
        raise
    finally:
        observed["verification_error"] = failure
        (Path(os.environ["HMMER529_ATTEMPT"]) / "molecular-sequence-native-glyco-helper.json").write_text(
            json.dumps(observed, allow_nan=False, indent=2))
