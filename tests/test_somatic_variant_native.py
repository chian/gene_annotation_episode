"""Engineering boundary controls; these fixtures are not a native caller proof."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode import somatic_variant_contracts as contracts
from gene_annotation_episode import somatic_variant_driver as driver


def request_fixture():
    digest = hashlib.sha256(b"engineered descriptor only").hexdigest()
    def pin(path):
        return {"path": path, "sha256": digest, "size_bytes": 26}
    inputs = [{"role": role, "path": "/selected/" + name,
        "file": {"artifact_ref": "artifact_" + digest, "sha256": digest,
            "size_bytes": 26, "format": format}, "source_ref": None}
        for role, name, format in contracts.INPUTS[:7]]
    return {"version": contracts.NATIVE_REQUEST_VERSION, "inputs": inputs,
        "sample_ids": {"tumor": "literal tumor ID", "normal": "literal normal ID"},
        "reference_id": None, "software": {"java": pin("/selected/java/bin/java"),
            "gatk_jar": pin("/selected/gatk.jar"), "snpeff_jar": pin("/selected/snpEff.jar"),
            "snpeff_config": pin("/selected/snpEff.config"),
            "runtime_files": [pin("/selected/java/bin/java"), pin("/selected/java/lib/modules")],
            "database": {"id": "explicit.1", "root": "/selected/data", "files": [
                {"relative_path": "explicit.1/snpEffectPredictor.bin", "sha256": digest, "size_bytes": 26}]},
            "reported_versions": {"java": None, "gatk": None, "snpeff": None}},
        "parameters": {"java_heap_mb": 1024, "pair_hmm_implementation": "LOGLESS_CACHING"}}


def _forbidden(*args, **kwargs):
    raise AssertionError("unexpected execution or input body read")


def test_exact_three_argv_keep_literal_normal_and_explicit_stats_database():
    request = request_fixture()
    directory = "/owned/worker/" + contracts.NATIVE_DIRECTORY
    raw = contracts.somatic_native_argv(request, "raw", directory=directory)
    filtered = contracts.somatic_native_argv(request, "filtered", directory=directory)
    annotated = contracts.somatic_native_argv(request, "annotated", directory=directory)
    assert raw[raw.index("-normal") + 1] == "literal normal ID"
    assert raw[raw.index("--pair-hmm-implementation") + 1] == "LOGLESS_CACHING"
    assert filtered[filtered.index("--stats") + 1] == "raw.vcf.stats"
    assert filtered[filtered.index("-V") + 1] == "raw.vcf"
    assert annotated[-2:] == ["explicit.1", "filtered.vcf"]
    assert all(flag in annotated for flag in ("-nodownload", "-noLog", "-noStats"))
    assert annotated[annotated.index("-dataDir") + 1] == "/selected/data"
    assert not any("shell" in cell or ">" == cell for cell in annotated)
    assert "-L" not in raw


def test_optional_interval_is_an_explicit_file_occurrence_and_fixed_staged_name():
    request = request_fixture()
    role, name, format = contracts.INPUTS[-1]
    item = deepcopy(request["inputs"][0])
    item.update(role=role, path="/received/a name;not shell.list")
    item["file"]["format"] = format
    request["inputs"].append(item)
    argv = contracts.somatic_native_argv(request, "raw", directory="/owned/" + contracts.NATIVE_DIRECTORY)
    assert argv[-2:] == ["-L", name]
    assert item["path"] not in argv


@pytest.mark.parametrize("change", [
    lambda r: r.update(extra="not allowed"),
    lambda r: r["inputs"].reverse(),
    lambda r: r["inputs"][0]["file"].update(size_bytes=True),
    lambda r: r["inputs"][0]["file"].update(artifact_ref="artifact_" + "0" * 64),
    lambda r: r["inputs"][0].update(path="/selected/../other.bam"),
    lambda r: r["inputs"][0].update(source_ref="made_up_source"),
    lambda r: r["sample_ids"].update(normal=r["sample_ids"]["tumor"]),
    lambda r: r["sample_ids"].update(normal="normal\nother"),
    lambda r: r["parameters"].update(java_heap_mb=True),
    lambda r: r["parameters"].update(pair_hmm_implementation="FASTEST_AVAILABLE"),
    lambda r: r["software"]["database"].update(id="../other"),
    lambda r: r["software"]["database"]["files"][0].update(relative_path="other/snpEffectPredictor.bin"),
    lambda r: r["software"]["runtime_files"].clear(),
    lambda r: r["software"]["runtime_files"].pop(0),
    lambda r: r["software"].update(gatk_jar={"path": "relative.jar", "sha256": "0" * 64, "size_bytes": 1}),
])
def test_changed_native_identity_grammar_rejected_without_io(change, monkeypatch):
    request = request_fixture()
    change(request)
    monkeypatch.setattr(driver.storage, "file_pin", _forbidden)
    monkeypatch.setattr(driver.subprocess, "Popen", _forbidden)
    with pytest.raises(ValueError, match="somatic_variant_"):
        contracts.validate_somatic_native_request(request)


def test_validators_detach_original_declarations():
    request = request_fixture()
    validated = contracts.validate_somatic_native_request(request)
    validated["inputs"][0]["file"]["format"] = "changed"
    validated["software"]["runtime_files"].clear()
    assert request["inputs"][0]["file"]["format"] == "bam"
    assert len(request["software"]["runtime_files"]) == 2


def test_missing_selected_software_preserves_unattempted_manifest_without_reading_bams(tmp_path, monkeypatch):
    request = request_fixture()
    monkeypatch.setattr(driver.storage, "retain_input", _forbidden)
    monkeypatch.setattr(driver, "extract_atac_bam_header", _forbidden)
    monkeypatch.setattr(driver.subprocess, "Popen", _forbidden)
    manifest = driver.run_somatic_variant_native(request, output_directory=tmp_path)
    assert manifest["issues"] == ["software_identity_conflict"]
    assert manifest["files"] == [] and manifest["headers"] == []
    assert all(row["state"] == "not_attempted" and row["returncode"] is None for row in manifest["stages"])
    assert all(row["state"] == "not_attempted" and row["observed"] is None for row in manifest["input_staging"])
    assert json.loads((tmp_path / contracts.NATIVE_DIRECTORY / "request.json").read_bytes()) == request
    with pytest.raises(ValueError, match="native_attempt_exists"):
        driver.run_somatic_variant_native(request, output_directory=tmp_path)


def test_existing_result_never_reaches_native_leaf(tmp_path, monkeypatch):
    request = tmp_path / "request.json"
    result = tmp_path / "result.json"
    request.write_text(json.dumps({"operation": contracts.NATIVE_OPERATION,
        "arguments": {"request": request_fixture()}}))
    result.write_bytes(b"original result")
    monkeypatch.setattr(driver, "run_somatic_variant_native", _forbidden)
    with pytest.raises(ValueError, match="worker_result_exists"):
        driver.main([str(request), str(result)])
    assert result.read_bytes() == b"original result"


def test_stage_sequence_cannot_claim_downstream_execution_after_unattempted_caller(tmp_path, monkeypatch):
    monkeypatch.setattr(driver.subprocess, "Popen", _forbidden)
    manifest = driver.run_somatic_variant_native(request_fixture(), output_directory=tmp_path)
    manifest["stages"][1].update(state="exited", returncode=0,
        started_at_utc="2026-11-02T00:00:00.000000Z", ended_at_utc="2026-11-02T00:00:01.000000Z")
    with pytest.raises(ValueError, match="stage_prerequisite_conflict"):
        contracts.validate_somatic_native_manifest(manifest)
