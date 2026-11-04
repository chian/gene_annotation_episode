"""Store-free single-attempt Mutect2/FilterMutectCalls/SnpEff native leaf.

The host supplies authenticated inputs and selected physical software. This leaf
never downloads a database, guesses a sample from a filename, parses VCF values,
calculates a score or publishes a Source. A native exit is a process observation.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess

from . import native_flux_balance_storage as storage
from . import somatic_variant_contracts as contracts
from .local_jobs import LocalJobPolicy, check_scratch_budget
from .native_atac_differential_reference import extract_atac_bam_header


def _time():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _verify_software(software):
    pins = [software[k] for k in ("java", "gatk_jar", "snpeff_jar", "snpeff_config")]
    pins.extend(software["runtime_files"])
    database = software["database"]
    for row in database["files"]:
        path = storage.confined_file(database["root"], row["relative_path"])
        pins.append({"path": str(path), "sha256": row["sha256"], "size_bytes": row["size_bytes"]})
    seen = {}
    for pin in pins:
        contracts.require(pin["path"] not in seen or seen[pin["path"]] == pin, "software_pin_alias_conflict")
        seen[pin["path"]] = pin
        contracts.require(storage.file_pin(pin["path"]) == pin, "software_identity_conflict")
    contracts.require(os.access(software["java"]["path"], os.X_OK), "java_not_executable")


def _reserve(parent):
    parent = storage.directory(contracts.absolute_path(str(parent)))
    with storage._directory_fd(parent) as fd:
        try:
            os.mkdir(contracts.NATIVE_DIRECTORY, 0o700, dir_fd=fd)
        except FileExistsError as error:
            raise ValueError("somatic_variant_native_attempt_exists") from error
        os.fsync(fd)
    return storage.directory(parent / contracts.NATIVE_DIRECTORY)


@contextmanager
def _log(path):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        try:
            yield stream
        finally:
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), 0o444)


def _files(directory, request):
    rows, issues = [], []
    specs = contracts.INPUTS[:len(request["inputs"])] + contracts.OUTPUTS
    for role, name, format in specs:
        try:
            path = storage.confined_file(directory, name)
            pin = storage.file_pin(path)
            with storage.regular(path) as stream:
                os.fchmod(stream.fileno(), 0o444)
        except FileNotFoundError:
            continue
        except (OSError, ValueError):
            issues.append("output_unavailable")
            continue
        rows.append({"role": role, "relative_path": contracts.NATIVE_DIRECTORY + "/" + name,
            "format": format, "sha256": pin["sha256"], "size_bytes": pin["size_bytes"]})
        if role in contracts.STAGES and pin["size_bytes"] == 0:
            issues.append("output_empty")
    return rows, issues


def _headers(directory, request):
    rows, issues = [], []
    for ordinal, role in enumerate(("tumor", "normal")):
        selected = request["inputs"][ordinal * 2]
        name = role + ".header.sam"
        inspected = extract_atac_bam_header(input_path=directory / (role + ".bam"),
            input_file=selected["file"], input_key=selected["role"], callpeak_run_key="somatic_header_inspection",
            input_ordinal=ordinal, output_path=directory / name,
            output_relative_path=contracts.NATIVE_DIRECTORY + "/" + name,
            policy=LocalJobPolicy(**contracts.POLICY))
        samples = []
        try:
            raw = storage.read_bytes(directory / name)
            for line in raw.decode("utf-8").splitlines():
                if line.startswith("@RG\t"):
                    observed = [cell[3:] for cell in line.split("\t")[1:] if cell.startswith("SM:")]
                    contracts.require(len(observed) == 1 and observed[0], "sample_identity_conflict")
                    if observed[0] not in samples:
                        samples.append(observed[0])
        except (OSError, ValueError, UnicodeError):
            issues.append("header_unavailable")
        if inspected["producer_outcome"] != "succeeded":
            issues.append("header_unavailable")
        if samples != [request["sample_ids"][role]]:
            issues.append("sample_identity_conflict")
        rows.append({"role": role, "inspection": inspected, "sample_ids": samples})
    return rows, issues


def _prerequisites(directory, stage):
    names = {"raw": (), "filtered": (("raw", "raw.vcf"), ("raw_stats", "raw.vcf.stats")),
        "annotated": (("filtered", "filtered.vcf"),)}[stage]
    rows = []
    for role, name in names:
        try:
            pin = storage.file_pin(storage.confined_file(directory, name))
            if pin["size_bytes"] == 0:
                return None
        except (OSError, ValueError):
            return None
        rows.append({"role": role, "sha256": pin["sha256"], "size_bytes": pin["size_bytes"]})
    return rows


def run_somatic_variant_native(request, *, output_directory):
    request = contracts.validate_somatic_native_request(request)
    directory = _reserve(output_directory)
    storage.immutable_json(directory / "request.json", request)
    stages = [{"stage": stage, "argv": contracts.somatic_native_argv(request, stage, directory=str(directory)),
        "prerequisites": [], "state": "not_attempted", "returncode": None,
        "started_at_utc": None, "ended_at_utc": None}
        for stage in contracts.STAGES]
    issues, headers = [], []
    staging = [{"role": selected["role"], "state": "not_attempted", "observed": None}
        for selected in request["inputs"]]
    try:
        _verify_software(request["software"])
    except (OSError, ValueError):
        issues.append("software_identity_conflict")
    if not issues:
        for selected, (_role, name, _format), staged in zip(request["inputs"], contracts.INPUTS, staging):
            try:
                staged["state"] = "failed"
                check_scratch_budget(directory, LocalJobPolicy(**contracts.POLICY),
                    additional_bytes=selected["file"]["size_bytes"])
                actual = storage.retain_input(selected["path"], directory / name,
                    max_bytes=selected["file"]["size_bytes"])
                staged["observed"] = actual
                contracts.require(actual == {k: selected["file"][k] for k in ("sha256", "size_bytes")},
                    "input_identity_conflict")
                staged["state"] = "verified"
            except (OSError, ValueError):
                issues.append("input_identity_conflict")
                break
    if not issues:
        headers, header_issues = _headers(directory, request)
        issues.extend(header_issues)
    if not issues:
        for name in ("tmp", "cache", "home"):
            storage.directory(directory / name, create=True)
        environment = {"TMPDIR": str(directory / "tmp"), "TMP": str(directory / "tmp"),
            "TEMP": str(directory / "tmp"), "XDG_CACHE_HOME": str(directory / "cache"),
            "HOME": str(directory / "home"), "LC_ALL": "C", "LANG": "C"}
        storage.immutable_json(directory / "environment.json", environment)
        for stage in stages:
            name = stage["stage"]
            prerequisites = _prerequisites(directory, name)
            if prerequisites is None:
                issues.append("required_output_missing")
                break
            stage["prerequisites"] = prerequisites
            stdout_name = "annotated.vcf" if name == "annotated" else name + ".stdout"
            with _log(directory / stdout_name) as stdout, _log(directory / (name + ".stderr")) as stderr:
                stage["started_at_utc"] = _time()
                storage.immutable_json(directory / (name + ".started.json"), {
                    "stage": name, "argv": stage["argv"], "prerequisites": prerequisites,
                    "attempted_at_utc": stage["started_at_utc"]})
                try:
                    process = subprocess.Popen(stage["argv"], cwd=directory, env=environment,
                        stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, shell=False)
                except OSError:
                    stage["state"] = "spawn_failed"
                    issues.append("native_spawn_failed")
                else:
                    stage["returncode"] = process.wait()
                    stage["state"] = "exited"
                    if stage["returncode"] != 0:
                        issues.append("native_nonzero_exit")
                stage["ended_at_utc"] = _time()
            storage.immutable_json(directory / (name + ".ended.json"), stage)
            if stage["state"] != "exited" or stage["returncode"] != 0:
                break
        try:
            _verify_software(request["software"])
        except (OSError, ValueError):
            issues.append("software_changed_after_execution")
    files, file_issues = _files(directory, request)
    issues.extend(file_issues)
    for selected in request["inputs"]:
        actual = next((row for row in files if row["role"] == selected["role"]), None)
        if actual is not None and any(actual[key] != selected["file"][key] for key in ("sha256", "size_bytes")):
            issues.append("staged_input_changed")
    manifest = {"version": contracts.NATIVE_MANIFEST_VERSION, "request": request,
        "directory": str(directory), "input_staging": staging,
        "stages": stages, "headers": headers, "files": files,
        "issues": list(dict.fromkeys(issues))}
    return contracts.validate_somatic_native_manifest(manifest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    parser.add_argument("result")
    args = parser.parse_args(argv)
    request_path = Path(contracts.absolute_path(args.request))
    result_path = Path(contracts.absolute_path(args.result))
    contracts.require(result_path.parent == request_path.parent and result_path != request_path
        and result_path.name != contracts.NATIVE_DIRECTORY, "worker_result_path_invalid")
    contracts.require(not result_path.exists() and not result_path.is_symlink(), "worker_result_exists")
    envelope = storage.read_json(request_path)
    contracts.closed(envelope, "operation arguments", "worker_envelope_invalid")
    contracts.require(envelope["operation"] == contracts.NATIVE_OPERATION, "worker_operation_invalid")
    contracts.closed(envelope["arguments"], "request", "worker_arguments_invalid")
    result = run_somatic_variant_native(envelope["arguments"]["request"], output_directory=result_path.parent)
    storage.immutable_bytes(result_path, json.dumps(result, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False).encode("utf-8") + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
