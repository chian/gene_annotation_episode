"""Structural MUSCLE leaf controls; no test launches an alignment.

Metadata fixtures are explicitly engineered. Temporary physical files establish
only byte-copy/declaration behavior, not Store receipts or native production.
"""
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode import muscle_alignment_driver as driver


def _forbidden(*args, **kwargs):
    raise AssertionError("native alignment is forbidden in structural driver tests")


@pytest.fixture(autouse=True)
def no_native_process(monkeypatch):
    monkeypatch.setattr(driver.subprocess, "Popen", _forbidden)


def _request():
    return dict(version=driver.REQUEST_VERSION,
        input=dict(path="/engineered/input FASTA.fasta", source_ref=None,
            file=dict(artifact_ref="artifact_" + "a" * 64, sha256="a" * 64, size_bytes=19, format="fasta")),
        software=dict(path="/engineered/selected MUSCLE", sha256="b" * 64, size_bytes=3587040),
        parameters=dict(threads=1, randseed=1, perturb=0, perm="none", consiters=2, refineiters=100))


def _physical_input(tmp_path, raw):
    path = tmp_path / "original.fasta"
    path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    return dict(path=str(path), source_ref=None,
        file=dict(artifact_ref="artifact_" + digest, sha256=digest, size_bytes=len(raw), format="fasta"))


def _manifest(request=None):
    request = _request() if request is None else deepcopy(request)
    files = [dict(role=role, relative_path=driver.NATIVE_DIRECTORY_NAME + "/" + name,
        format=format, sha256=request["input"]["file"]["sha256"] if role == "input" else "c" * 64,
        size_bytes=request["input"]["file"]["size_bytes"] if role == "input" else 13)
        for role, name, format in (("input", "input.fasta", "fasta"),
            ("alignment", "aligned.fasta", "fasta"), ("stdout", "stdout", "muscle_log"),
            ("stderr", "stderr", "muscle_log"))]
    return dict(version=driver.MANIFEST_VERSION, request=request,
        argv=driver.muscle_alignment_native_argv(request), returncode=0, files=files, issues=[])


def test_pure_request_software_and_parameters_do_no_io_and_return_detached_values(monkeypatch):
    monkeypatch.setattr(driver.storage, "file_pin", _forbidden)
    request = _request()
    result = driver.validate_muscle_alignment_native_request(request)
    assert result == request and result is not request and result["input"] is not request["input"]
    assert driver.validate_muscle_alignment_parameters(request["parameters"]) == request["parameters"]
    assert driver.validate_muscle_alignment_software(request["software"]) == request["software"]
    result["parameters"]["threads"] = 9
    assert request["parameters"]["threads"] == 1
    request["input"]["source_ref"] = "source_" + "d" * 24
    assert driver.validate_muscle_alignment_native_request(request)["input"]["source_ref"] == request["input"]["source_ref"]


@pytest.mark.parametrize("key,value", [
    ("threads", 0), ("threads", True), ("randseed", 0), ("randseed", 1.0),
    ("perturb", -1), ("perturb", False), ("perturb", 0.25),
    ("consiters", -1), ("consiters", True), ("refineiters", -1),
    ("refineiters", float("inf")), ("perm", "all"), ("perm", "ABC"), ("perm", None),
    ("threads", 2**32), ("randseed", 2**32), ("perturb", 2**32),
    ("consiters", 2**32), ("refineiters", 2**32),
])
def test_parameters_reject_values_that_change_native_grammar(key, value):
    parameters = _request()["parameters"]
    parameters[key] = value
    with pytest.raises(ValueError, match="muscle_alignment_parameter_invalid_"):
        driver.validate_muscle_alignment_parameters(parameters)


def test_unsigned_native_maximum_is_preserved_without_wrap_or_clamp():
    parameters = _request()["parameters"]
    for key in ("threads", "randseed", "perturb", "consiters", "refineiters"):
        parameters[key] = 4294967295
    assert driver.validate_muscle_alignment_parameters(parameters) == parameters
    request = _request()
    request["parameters"] = parameters
    argv = driver.muscle_alignment_native_argv(request)
    for option in ("-threads", "-randseed", "-perturb", "-consiters", "-refineiters"):
        assert argv[argv.index(option) + 1] == "4294967295"


@pytest.mark.parametrize("permutation", ["none", "abc", "acb", "bca"])
def test_explicit_legal_zero_iterations_and_single_alignment_argv(permutation):
    request = _request()
    request["parameters"].update(perturb=0, perm=permutation, consiters=0, refineiters=0)
    assert driver.muscle_alignment_native_argv(request) == [request["software"]["path"],
        "-align", "input.fasta", "-output", "aligned.fasta", "-threads", "1", "-randseed", "1",
        "-perturb", "0", "-perm", permutation, "-consiters", "0", "-refineiters", "0"]


@pytest.mark.parametrize("change", [
    lambda value: value.update(extra=True),
    lambda value: value["input"].update(path="relative.fasta"),
    lambda value: value["input"].update(path="/engineered/../escape"),
    lambda value: value["input"].update(source_ref="artifact_" + "d" * 64),
    lambda value: value["input"]["file"].update(artifact_ref="artifact_" + "f" * 64),
    lambda value: value["input"]["file"].update(size_bytes=True),
    lambda value: value["input"]["file"].update(format="auto"),
    lambda value: value["software"].update(path="/engineered//binary"),
    lambda value: value["software"].update(sha256="F" * 64),
    lambda value: value["parameters"].update(output="elsewhere"),
])
def test_request_rejects_identity_path_and_extra_control_changes_before_io(monkeypatch, tmp_path, change):
    request = _request()
    change(request)
    monkeypatch.setattr(driver.storage, "file_pin", _forbidden)
    monkeypatch.setattr(driver, "_reserve_native_directory", _forbidden)
    with pytest.raises(ValueError, match="muscle_alignment_"):
        driver.run_muscle_alignment_native(request, output_directory=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_staging_preserves_every_supplied_case_label_gap_and_line_ending_byte(tmp_path):
    raw = b">same full label\r\nAcG.-t \r\n>same full label\r\nACGT\r\n"
    operand = _physical_input(tmp_path, raw)
    original = driver.storage.file_pin(operand["path"])
    directory = tmp_path / "owned-native"
    directory.mkdir()
    copied = driver._stage_input(operand, directory)
    assert copied == directory / "input.fasta" and copied.read_bytes() == raw
    assert driver.storage.file_pin(operand["path"]) == original
    assert driver.storage.file_pin(copied)["sha256"] == operand["file"]["sha256"]
    assert not (directory / "aligned.fasta").exists()


def test_changed_staging_identity_preserves_actual_bytes_without_native_dispatch(tmp_path):
    raw = b">engineered\nAcgT\n"
    operand = _physical_input(tmp_path, raw)
    operand["file"].update(sha256="f" * 64, artifact_ref="artifact_" + "f" * 64)
    directory = tmp_path / "owned-native"
    directory.mkdir()
    with pytest.raises(ValueError, match="muscle_alignment_input_identity_conflict"):
        driver._stage_input(operand, directory)
    assert (directory / "input.fasta").read_bytes() == raw
    assert not (directory / "aligned.fasta").exists()


def test_existing_attempt_is_not_reused_or_changed(tmp_path):
    directory = driver._reserve_native_directory(tmp_path)
    marker = directory / "original-prefix"
    marker.write_bytes(b"actual retained test prefix")
    with pytest.raises(ValueError, match="muscle_alignment_native_attempt_exists"):
        driver._reserve_native_directory(tmp_path)
    assert marker.read_bytes() == b"actual retained test prefix"
    assert directory == tmp_path / "muscle-alignment-native"


def test_physical_software_pin_checks_bytes_without_execution_or_alias_following(tmp_path):
    path = tmp_path / "engineered-byte-pin-only"
    path.write_bytes(b"engineered bytes, not a MUSCLE executable")
    path.chmod(0o555)
    selected = driver.storage.file_pin(path)
    driver._check_software(selected)
    path.chmod(0o755)
    path.write_bytes(b"changed engineered bytes")
    path.chmod(0o555)
    with pytest.raises(ValueError, match="muscle_alignment_software_identity_conflict"):
        driver._check_software(selected)
    alias = tmp_path / "unselected-alias"
    alias.symlink_to(path)
    with pytest.raises(ValueError, match="muscle_alignment_software_identity_conflict"):
        driver._check_software(dict(driver.storage.file_pin(path), path=str(alias)))


def test_manifest_is_detached_and_preserves_negative_native_returncode():
    manifest = _manifest()
    manifest.update(returncode=-9, issues=["muscle_alignment_native_nonzero_exit"])
    result = driver.validate_muscle_alignment_native_manifest(manifest)
    assert result == manifest and result is not manifest
    result["files"][0]["size_bytes"] = 0
    assert manifest["files"][0]["size_bytes"] == 19


def test_observed_engineering_files_distinguish_empty_alignment_from_missing(tmp_path):
    raw = b">supplied\nAa.-\n"
    request = _request()
    request["input"] = _physical_input(tmp_path, raw)
    directory = driver._reserve_native_directory(tmp_path)
    driver._stage_input(request["input"], directory)
    (directory / "aligned.fasta").write_bytes(b"")
    (directory / "stdout").write_bytes(b"")
    (directory / "stderr").write_bytes(b"engineered log, not native evidence\n")
    files, issues = driver._observed_files(directory, request)
    assert issues == ["muscle_alignment_alignment_empty"]
    manifest = dict(version=driver.MANIFEST_VERSION, request=request,
        argv=driver.muscle_alignment_native_argv(request), returncode=1,
        files=files, issues=["muscle_alignment_native_nonzero_exit", *issues])
    assert driver.validate_muscle_alignment_native_manifest(manifest) == manifest
    assert next(row for row in files if row["role"] == "alignment")["size_bytes"] == 0
    (directory / "aligned.fasta").unlink()
    files, issues = driver._observed_files(directory, request)
    assert "alignment" not in [row["role"] for row in files]
    assert issues == ["muscle_alignment_alignment_missing"]
    manifest.update(files=files, issues=["muscle_alignment_native_nonzero_exit", *issues])
    assert driver.validate_muscle_alignment_native_manifest(manifest) == manifest


def test_output_alias_is_unavailable_without_reading_or_changing_its_target(tmp_path):
    raw = b">supplied\nAa.-\n"
    request = _request()
    request["input"] = _physical_input(tmp_path, raw)
    directory = driver._reserve_native_directory(tmp_path)
    driver._stage_input(request["input"], directory)
    for name in ("stdout", "stderr"):
        (directory / name).write_bytes(b"")
    target = tmp_path / "private-engineering-control"
    target.write_bytes(b"not an aligned FASTA output")
    before = (target.read_bytes(), target.stat().st_mode)
    (directory / "aligned.fasta").symlink_to(target)
    files, issues = driver._observed_files(directory, request)
    assert "alignment" not in [row["role"] for row in files]
    assert issues == ["muscle_alignment_alignment_file_unavailable"]
    assert (target.read_bytes(), target.stat().st_mode) == before


@pytest.mark.parametrize("change", [
    lambda value: value.update(returncode=True),
    lambda value: value.update(returncode=1),
    lambda value: value["argv"].append("-stratified"),
    lambda value: value["files"][1].update(relative_path="../aligned.fasta"),
    lambda value: value["files"][1].update(format="newick"),
    lambda value: value["files"][1].update(size_bytes=False),
    lambda value: value["files"].append(deepcopy(value["files"][1])),
    lambda value: value["files"].reverse(),
    lambda value: value["files"].pop(1),
    lambda value: value["files"][0].update(sha256="e" * 64),
    lambda value: value["issues"].append("complete_scientific_success"),
    lambda value: value.update(environment={"PATH": "/unselected"}),
])
def test_manifest_rejects_control_changes_and_inconsistent_byte_qualifications(change):
    manifest = _manifest()
    change(manifest)
    with pytest.raises(ValueError, match="muscle_alignment_"):
        driver.validate_muscle_alignment_native_manifest(manifest)


@pytest.mark.parametrize("envelope", [
    {"operation": "another_native_operation", "arguments": {"request": {}}},
    {"operation": "protein_conservation_native", "arguments": {"request": {}, "output": "elsewhere"}},
    {"operation": "protein_conservation_native", "arguments": {"request": {}}, "extra": True},
])
def test_main_rejects_changed_worker_envelopes_before_native_leaf(monkeypatch, tmp_path, envelope):
    selected = tmp_path / "worker-request.json"
    selected.write_text(json.dumps(envelope))
    monkeypatch.setattr(driver, "run_muscle_alignment_native", _forbidden)
    with pytest.raises(ValueError, match="muscle_alignment_"):
        driver.main([str(selected), str(tmp_path / "worker-result.json")])
    assert not (tmp_path / "worker-result.json").exists()


@pytest.mark.parametrize("kind", ["file", "directory", "dangling_symlink"])
def test_main_rejects_existing_result_before_native_leaf(monkeypatch, tmp_path, kind):
    selected = tmp_path / "worker-request.json"
    selected.write_text(json.dumps(dict(operation=driver.OPERATION, arguments=dict(request=_request()))))
    result = tmp_path / "worker-result.json"
    if kind == "file":
        result.write_bytes(b"original immutable result")
    elif kind == "directory":
        result.mkdir()
    else:
        result.symlink_to(tmp_path / "missing-original-target")
    monkeypatch.setattr(driver, "run_muscle_alignment_native", _forbidden)
    with pytest.raises(ValueError, match="muscle_alignment_worker_result_exists"):
        driver.main([str(selected), str(result)])
    assert not (tmp_path / driver.NATIVE_DIRECTORY_NAME).exists()
    if kind == "file":
        assert result.read_bytes() == b"original immutable result"
    elif kind == "directory":
        assert result.is_dir() and list(result.iterdir()) == []
    else:
        assert result.is_symlink() and not result.exists()


@pytest.mark.parametrize("relative", ["muscle-alignment-native", "muscle-alignment-native/input.fasta",
    "muscle-alignment-native/aligned.fasta", "muscle-alignment-native/stdout", "muscle-alignment-native/stderr"])
def test_main_rejects_native_directory_and_fixed_file_result_collisions(monkeypatch, tmp_path, relative):
    selected = tmp_path / "worker-request.json"
    selected.write_text(json.dumps(dict(operation=driver.OPERATION, arguments=dict(request=_request()))))
    monkeypatch.setattr(driver, "run_muscle_alignment_native", _forbidden)
    with pytest.raises(ValueError, match="muscle_alignment_worker_result_path_invalid"):
        driver.main([str(selected), str(tmp_path / relative)])
    assert list(tmp_path.iterdir()) == [selected]
