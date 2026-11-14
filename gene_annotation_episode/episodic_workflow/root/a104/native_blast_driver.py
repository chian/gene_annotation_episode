"""One selected native pairwise BLAST attempt, run inside the caller's resource boundary.

The existing durable local/PBS lifecycle owns process lifetime and hard limits.
This producer stages exact operands, invokes one subprocess, retains complete
files and seals a manifest. It has no model, retry, polling or resource choice.
A killed producer can leave an unsealed attempt; that uncertainty never permits
another invocation of the selected command. The CLI accepts exactly one plan.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from ._local_job_worker import allocated_bytes
from .native_blast_contracts import (
    compile_native_blast_job, _options,
    finite_json_copy, native_blast_digest, validate_native_blast_requested_job,
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _atomic_new(path, value):
    """Atomic immutable publication: link cannot replace an existing manifest."""
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2).encode() + b"\n"
    temporary = path.with_name("." + path.name + ".writing")
    with temporary.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temporary, path)
    temporary.unlink()
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _read_json(path):
    with path.open("rb") as stream:
        return finite_json_copy(json.load(stream))


def _digest_file(path):
    hasher, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("native_blast_regular_file_required")
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            hasher.update(block)
    return size, hasher.hexdigest()


def _validate_plan(value):
    plan = finite_json_copy(value)
    if (type(plan) is not dict or set(plan) != {"version", "identity", "requested_job", "attempt_directory", "policy"}
            or plan["version"] != "native_blast_run_plan_v1"):
        raise ValueError("native_blast_run_plan_required")
    identity = plan["identity"]
    keys = {"run_id", "episode_id", "resource_id", "execution_id", "attempt_id", "operation_key", "requested_job_sha256"}
    if type(identity) is not dict or set(identity) != keys or any(type(v) is not str or not v or "\0" in v for v in identity.values()):
        raise ValueError("native_blast_complete_attempt_identity_required")
    request = validate_native_blast_requested_job(plan["requested_job"])
    if identity["requested_job_sha256"] != native_blast_digest(request):
        raise ValueError("native_blast_requested_job_digest_mismatch")
    policy = plan["policy"]
    if type(policy) is not dict or set(policy) != {'memory_bytes', 'scratch_bytes'}:
        raise ValueError("native_blast_explicit_policy_required")
    from .local_jobs import LocalJobPolicy
    LocalJobPolicy(**policy)  # Validate the supplied allocation; never replace it.
    name = plan["attempt_directory"]
    if (type(name) is not str or not Path(name).is_absolute() or str(Path(name)) != name
            or ".." in Path(name).parts or any(c in name for c in ("\0", "\n", "\r"))):
        raise ValueError("native_blast_absolute_attempt_directory_required")
    root = Path(name)
    if root.resolve() != root:
        raise ValueError("native_blast_attempt_symlink_forbidden")
    return plan


def _failure(bundle, stage, code, role=None, **detail):
    bundle["failures"].append({"stage": stage, "code": code, "role": role, "detail": detail})


def _scratch(root, policy):
    observed = allocated_bytes(root)
    if observed > policy["scratch_bytes"]:
        raise _ScratchLimit(observed, policy["scratch_bytes"])


class _ScratchLimit(Exception):
    def __init__(self, observed, limit):
        self.observed, self.limit = observed, limit
        super().__init__("native_blast_scratch_limit")


def _staged_relative(operand):
    return "inputs/" + operand["role"] + ".fa"


def _stage_input(root, operand, policy, row):
    source, destination = Path(operand["path"]), root / row["relative_path"]
    with source.open("rb") as reader:
        info = os.fstat(reader.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("native_blast_regular_input_required")
        row["size_bytes"] = info.st_size
        if info.st_size != operand["size_bytes"]:
            raise ValueError("native_blast_input_size_mismatch")
        observed = allocated_bytes(root)
        if observed + info.st_size > policy["scratch_bytes"]:
            raise _ScratchLimit(observed + info.st_size, policy["scratch_bytes"])
        hasher, copied = hashlib.sha256(), 0
        with destination.open("xb") as writer:
            for block in iter(lambda: reader.read(1024 * 1024), b""):
                copied += len(block)
                writer.write(block)
                writer.flush()
                hasher.update(block)
                _scratch(root, policy)
            os.fsync(writer.fileno())
        row["size_bytes"], row["actual_sha256"] = copied, hasher.hexdigest()
        if copied != operand["size_bytes"]:
            raise ValueError("native_blast_input_changed_size_during_capture")
        if row["actual_sha256"].lower() != operand["sha256"].lower():
            raise ValueError("native_blast_input_digest_mismatch")


def _validate_input_format(path, *, role, job):
    """Validate one actual ungapped FASTA operand and its selected bounds.

    This checks input framing and identity, not native output or science. It
    cannot repair an invalid sequence or choose another molecule or interval.
    """
    title, sequence = None, []
    with path.open("r", encoding="ascii") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if title is not None:
                    raise ValueError("native_blast_exactly_one_fasta_record_required")
                title = line[1:].strip()
                if not title:
                    raise ValueError("native_blast_fasta_header_required")
            elif title is None:
                raise ValueError("native_blast_fasta_input_required")
            else:
                if re.fullmatch(r"[A-Za-z*]+", line) is None:
                    raise ValueError("native_blast_ungapped_sequence_symbols_required")
                sequence.append(line)
    if not title or not sequence:
        raise ValueError("native_blast_nonempty_fasta_sequence_required")
    sequence = "".join(sequence).upper()
    protein = (role == "query_sequence" and job["program"] in {"blastp", "tblastn"}
        or role == "subject_sequence" and job["program"] in {"blastp", "blastx"})
    alphabet = set("ABCDEFGHIKLMNPQRSTVWXYZJUO*") if protein else set("ACGTURYSWKMBDHVN")
    if not set(sequence) <= alphabet:
        raise ValueError("native_blast_operand_molecule_symbols_conflict")
    options = _options(job)
    selection = options.get("-query_loc" if role == "query_sequence" else "-subject_loc")
    if selection and int(selection.split("-")[1]) > len(sequence):
        raise ValueError("native_blast_selected_interval_outside_operand")
    for binding in job["operand_bindings"]:
        if binding["operand_role"] == role:
            if binding["native_name"] is not None and binding["native_name"] not in {title, title.split()[0]}:
                raise ValueError("native_blast_operand_name_conflict")
            # An accession is not inferred from a title. It must occur as an
            # exact native identifier or pipe-delimited defline component.
            accession = binding["native_accession"]
            if accession is not None and accession not in {title.split()[0], *title.split()[0].split("|")}:
                raise ValueError("native_blast_operand_accession_conflict")


def _confined_file(root, relative):
    path = root / relative
    if path.resolve() != path or not path.is_relative_to(root) or path == root:
        raise ValueError("native_blast_output_path_escape")
    if path.exists() and not path.is_file():
        raise ValueError("native_blast_output_not_regular_file")
    return path


def validate_native_blast_bundle_files(bundle, directory):
    """Verify original request, staged inputs and outputs without recapture."""
    root = Path(directory)
    if not root.is_absolute() or root.resolve() != root:
        raise ValueError("native_blast_attempt_symlink_forbidden")
    bundle = finite_json_copy(bundle)
    owner_path = root / ".native-blast-owner.json"
    if owner_path.resolve() != owner_path:
        raise ValueError("native_blast_attempt_owner_path_escape")
    plan = _validate_plan(_read_json(owner_path))
    fields = {"version", "identity", "requested_job", "program", "mode", "software",
        "realized_argv", "environment", "inputs", "operand_bindings", "returncode", "artifacts",
        "failures", "started_at", "finished_at"}
    if (type(bundle) is not dict or set(bundle) != fields or bundle["version"] != "native_blast_bundle_v1"
            or bundle["identity"] != plan["identity"] or bundle["requested_job"] != plan["requested_job"]
            or plan["attempt_directory"] != str(root)):
        raise ValueError("native_blast_sealed_manifest_identity_conflict")
    job = validate_native_blast_requested_job(bundle["requested_job"])["native_blast"]
    if (bundle["program"] != job["program"] or bundle["mode"] != job["mode"]
            or bundle["operand_bindings"] != job["operand_bindings"]):
        raise ValueError("native_blast_sealed_manifest_request_conflict")
    software = bundle["software"]
    if (type(software) is not dict or set(software) != {"executable", "expected_sha256", "actual_sha256", "declared_engine_version"}
            or software["executable"] != job["software"]["executable"]
            or software["expected_sha256"] != job["software"]["sha256"]
            or software["declared_engine_version"] != job["software"]["engine_version"]
            or software["actual_sha256"] is not None and (type(software["actual_sha256"]) is not str
                or re.fullmatch(r"[0-9a-f]{64}", software["actual_sha256"]) is None)):
        raise ValueError("native_blast_sealed_software_contract_conflict")
    if (bundle["returncode"] is not None and type(bundle["returncode"]) is not int
            or any(type(bundle[key]) is not str or not bundle[key] for key in ("started_at", "finished_at"))
            or type(bundle["failures"]) is not list
            or any(type(row) is not dict or set(row) != {"stage", "code", "role", "detail"}
                or type(row["detail"]) is not dict
                or any(type(row[key]) is not str or not row[key] for key in ("stage", "code"))
                or row["role"] is not None and type(row["role"]) is not str for row in bundle["failures"])):
        raise ValueError("native_blast_sealed_outcome_contract_conflict")
    if type(bundle["inputs"]) is not list or len(bundle["inputs"]) != len(job["operands"]):
        raise ValueError("native_blast_sealed_input_contract_conflict")
    inputs = {row["role"]: row for row in job["operands"]}
    seen = set()
    for row in bundle["inputs"]:
        if (type(row) is not dict or set(row) != {"role", "format", "original_path", "relative_path",
                "artifact_ref", "expected_sha256", "actual_sha256", "expected_size_bytes", "size_bytes"}
                or row["role"] not in inputs or row["role"] in seen):
            raise ValueError("native_blast_sealed_input_contract_conflict")
        selected = inputs[row["role"]]
        seen.add(row["role"])
        if (row["relative_path"] != _staged_relative(selected)
                or any(row[a] != selected[b] for a, b in (("format", "format"), ("original_path", "path"),
                    ("artifact_ref", "artifact_ref"), ("expected_sha256", "sha256"), ("expected_size_bytes", "size_bytes")))):
            raise ValueError("native_blast_sealed_input_contract_conflict")
        path = _confined_file(root, row["relative_path"])
        if row["actual_sha256"] is None:
            if path.exists():
                raise ValueError("native_blast_unrecorded_staged_input")
        else:
            size, digest = _digest_file(path)
            if size != row["size_bytes"] or digest != row["actual_sha256"]:
                raise ValueError("native_blast_sealed_input_digest_mismatch:" + row["relative_path"])
    paths = {role: str(root / _staged_relative(row)) for role, row in inputs.items()}
    compiled = compile_native_blast_job(job, input_paths=paths, output_directory=str(root))
    environment = {**compiled["environment"], **{key: str(root / "tmp") for key in ("TMPDIR", "TMP", "TEMP")},
        "XDG_CACHE_HOME": str(root / "cache")}
    if bundle["realized_argv"] != compiled["argv"] or bundle["environment"] != environment:
        raise ValueError("native_blast_sealed_realized_command_conflict")
    expected = {row["role"]: row for row in job["outputs"]}
    seen = set()
    if type(bundle["artifacts"]) is not list:
        raise ValueError("native_blast_sealed_output_contract_conflict")
    for row in bundle["artifacts"]:
        if (type(row) is not dict or set(row) != {"role", "format", "relative_path", "size_bytes", "sha256"}
                or row["role"] not in expected or row["role"] in seen
                or any(row[key] != expected[row["role"]][key] for key in ("format", "relative_path"))):
            raise ValueError("native_blast_sealed_output_contract_conflict")
        seen.add(row["role"])
        path = _confined_file(root, row["relative_path"])
        size, digest = _digest_file(path)
        if size != row["size_bytes"] or digest != row["sha256"]:
            raise ValueError("native_blast_sealed_artifact_digest_mismatch:" + row["relative_path"])
    if bundle["returncode"] == 0 and not bundle["failures"] and seen != expected.keys():
        raise ValueError("native_blast_sealed_success_missing_output")
    return bundle


def _collect_outputs(root, job, bundle):
    for output in job["outputs"]:
        role, relative = output["role"], output["relative_path"]
        try:
            path = _confined_file(root, relative)
            size, digest = _digest_file(path)
        except FileNotFoundError:
            _failure(bundle, "outputs", "native_blast_missing_output", role, relative_path=relative)
        except (OSError, ValueError) as error:
            _failure(bundle, "outputs", "native_blast_invalid_output", role, relative_path=relative, reason=str(error))
        else:
            bundle["artifacts"].append({"role": role, "format": output["format"],
                "relative_path": relative, "size_bytes": size, "sha256": digest})


def run_native_blast(plan) -> dict:
    plan = _validate_plan(plan)
    root, request = Path(plan["attempt_directory"]), plan["requested_job"]
    job = request["native_blast"]
    owner, manifest_path = root / ".native-blast-owner.json", root / "bundle.json"
    try:
        root.mkdir(mode=0o700)
    except FileExistsError:
        if owner.resolve() != owner or manifest_path.resolve() != manifest_path:
            raise ValueError("native_blast_attempt_record_path_escape")
        if not owner.is_file():
            raise ValueError("native_blast_attempt_not_exclusively_owned")
        if _read_json(owner) != plan:
            raise ValueError("native_blast_attempt_identity_conflict")
        if not manifest_path.is_file():
            raise ValueError("native_blast_unsealed_attempt_execution_uncertain")
        saved = _read_json(manifest_path)
        if (saved.get("identity") != plan["identity"] or saved.get("requested_job") != request
                or saved.get("version") != "native_blast_bundle_v1"):
            raise ValueError("native_blast_sealed_manifest_identity_conflict")
        return validate_native_blast_bundle_files(saved, root)
    _atomic_new(owner, plan)
    bundle = {"version": "native_blast_bundle_v1", "identity": plan["identity"],
        "requested_job": request, "program": job["program"], "mode": job["mode"],
        "software": {"executable": job["software"]["executable"], "expected_sha256": job["software"]["sha256"],
                     "actual_sha256": None, "declared_engine_version": job["software"]["engine_version"]},
        "realized_argv": [], "environment": {}, "inputs": [], "operand_bindings": job["operand_bindings"],
        "returncode": None, "artifacts": [], "failures": [], "started_at": _now(), "finished_at": None}
    for name in ("inputs", "tmp", "cache"):
        (root / name).mkdir()
    paths = {row["role"]: str(root / _staged_relative(row)) for row in job["operands"]}
    compiled = compile_native_blast_job(job, input_paths=paths, output_directory=str(root))
    bundle["realized_argv"] = compiled["argv"]
    bundle["environment"] = {**compiled["environment"], "TMPDIR": str(root / "tmp"),
        "TMP": str(root / "tmp"), "TEMP": str(root / "tmp"), "XDG_CACHE_HOME": str(root / "cache")}
    try:
        _, actual_sha = _digest_file(Path(job["software"]["executable"]))
        bundle["software"]["actual_sha256"] = actual_sha
        if actual_sha.lower() != job["software"]["sha256"].lower():
            _failure(bundle, "software", "native_blast_software_digest_mismatch")
        elif not os.access(job["software"]["executable"], os.X_OK):
            _failure(bundle, "software", "native_blast_software_not_executable")
    except (OSError, ValueError) as error:
        _failure(bundle, "software", "native_blast_software_unavailable", reason=str(error))
    for operand in job["operands"]:
        row = {"role": operand["role"], "format": operand["format"], "original_path": operand["path"],
            "relative_path": _staged_relative(operand), "artifact_ref": operand["artifact_ref"],
            "expected_sha256": operand["sha256"], "actual_sha256": None,
            "expected_size_bytes": operand["size_bytes"], "size_bytes": None}
        bundle["inputs"].append(row)
        try:
            _stage_input(root, operand, plan["policy"], row)
            _validate_input_format(root / row["relative_path"], role=operand["role"], job=job)
        except _ScratchLimit as error:
            _failure(bundle, "staging", "native_blast_scratch_limit", operand["role"],
                     observed_bytes=error.observed, limit_bytes=error.limit)
        except FileNotFoundError:
            _failure(bundle, "inputs", "native_blast_input_missing", operand["role"])
        except (OSError, ValueError, UnicodeError) as error:
            _failure(bundle, "inputs", str(error) if isinstance(error, ValueError) else "native_blast_input_io_error",
                     operand["role"], **({"errno": error.errno} if isinstance(error, OSError) else {}))
        finally:
            staged = root / row["relative_path"]
            if staged.is_file():
                row["size_bytes"], row["actual_sha256"] = _digest_file(staged)
    outputs = {row["role"]: root / row["relative_path"] for row in job["outputs"]}
    for path in outputs.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    if not bundle["failures"]:
        try:
            _scratch(root, plan["policy"])
            stdout_role = "stdout"
            with outputs[stdout_role].open("xb") as stdout, outputs["stderr"].open("xb") as stderr:
                # This single wait is for this selected native command only. The
                # caller's existing lifecycle enforces its supplied allocation.
                outcome = subprocess.run(compiled["argv"], cwd=root, env=bundle["environment"],
                    stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, check=False)
            bundle["returncode"] = outcome.returncode
            if outcome.returncode:
                _failure(bundle, "execution", "native_blast_nonzero_returncode", returncode=outcome.returncode)
            _scratch(root, plan["policy"])
        except _ScratchLimit as error:
            _failure(bundle, "execution", "native_blast_scratch_limit",
                     observed_bytes=error.observed, limit_bytes=error.limit)
        except OSError as error:
            _failure(bundle, "execution", "native_blast_command_unavailable", errno=error.errno)
    _collect_outputs(root, job, bundle)
    bundle["finished_at"] = _now()
    _atomic_new(manifest_path, bundle)
    return bundle


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        raise ValueError("native_blast_exact_plan_file_operand_required")
    plan = _read_json(Path(arguments[0]))
    result = run_native_blast(plan)
    print(json.dumps({"version": result["version"], "returncode": result["returncode"],
        "failure_count": len(result["failures"]), "bundle_path": str(Path(plan["attempt_directory"]) / "bundle.json")}))
    return 0 if not result["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
