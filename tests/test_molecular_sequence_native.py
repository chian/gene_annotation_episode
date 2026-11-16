"""Private-protocol controls; genuine selected execution requires explicit opt-in."""
from copy import deepcopy
from pathlib import Path

import pytest

from gene_annotation_episode import molecular_sequence_native as native


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


