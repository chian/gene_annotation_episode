"""Execute one explicitly selected native database command and seal its bytes.

The existing resource episode/PBS lifecycle owns selection and allocation. This
module performs mechanical verification, one subprocess invocation and capture.
It never discovers software, installs, downloads, retries, grades or chooses a
resource. An owned unsealed attempt is uncertain and cannot be invoked again.
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
import time

from . import native_blast_database_contracts as contracts

BUNDLE_NAME = "bundle.json"
OWNER_NAME = ".native-blast-database-owner.json"
_BLOCK = 1024 * 1024


def _now():
    return datetime.now(timezone.utc).isoformat()


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                contracts._fail("duplicate_json_key")
            result[key] = value
        return result
    return contracts._copy(json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: contracts._fail("finite_json_required")))


def _atomic_new(path, value):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2).encode() + b"\n"
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


def _canonical(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError("path_escape")
    return path


def _regular(path):
    path = _canonical(path)
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("regular_file_required")
    return path


def _stamp(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


class _Changed(ValueError):
    pass


def _measure(path):
    path = _regular(path)
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("regular_file_required")
        for block in iter(lambda: stream.read(_BLOCK), b""):
            digest.update(block)
            size += len(block)
        after = os.fstat(stream.fileno())
    if _stamp(before) != _stamp(after) or _stamp(after) != _stamp(path.stat()) or size != after.st_size:
        raise _Changed("file_changed")
    return {"sha256": digest.hexdigest(), "size_bytes": size}


def _copy_file(source, destination):
    source, destination = _regular(source), _canonical(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest, size = hashlib.sha256(), 0
    with source.open("rb") as reader, destination.open("xb") as writer:
        if not stat.S_ISREG(os.fstat(reader.fileno()).st_mode):
            raise ValueError("regular_file_required")
        for block in iter(lambda: reader.read(_BLOCK), b""):
            writer.write(block)
            digest.update(block)
            size += len(block)
        writer.flush()
        os.fsync(writer.fileno())
    measured = _measure(destination)
    if measured != {"sha256": digest.hexdigest(), "size_bytes": size}:
        raise _Changed("copy_changed")
    return measured


def _failure(bundle, code, *, input_key=None, database_key=None, output_key=None, artifact_key=None):
    row = {"code": code, "input_key": input_key, "database_key": database_key, "output_key": output_key,
        "artifact_key": artifact_key, "native_returncode": bundle["process"]["returncode"]
        if output_key is not None or code == "native_nonzero_exit" else None}
    if row not in bundle["failures"]:
        bundle["failures"].append(row)


def _artifact(bundle, path, measured, *, role, format, input_key=None, database_key=None, output_key=None,
              fields=None, delimiter=None):
    relative = str(Path(path).relative_to(bundle["plan"]["attempt_directory"]))
    key = "artifact-" + contracts._digest(relative)
    row = {"artifact_key": key, "input_key": input_key, "database_key": database_key, "output_key": output_key,
        "role": role, "relative_path": relative, "format": format, "fields": [] if fields is None else fields,
        "delimiter": delimiter, **measured, "content_assessment": "not_parsed"}
    if any(r["artifact_key"] == key for r in bundle["artifacts"]):
        contracts._fail("duplicate_capture_path")
    bundle["artifacts"].append(row)
    return key


def _check_file(expected, *, kind=None):
    row = {"path": expected["path"], "observed_sha256": None, "size_bytes": None,
        "checked_at": _now(), "status": "not_checked"}
    if kind is not None:
        row["kind"] = kind
    else:
        row["expected_sha256"] = expected["sha256"]
    try:
        measured = _measure(expected["path"])
    except FileNotFoundError:
        row["status"] = "missing"
    except (OSError, ValueError):
        row["status"] = "unreadable"
    else:
        row.update(observed_sha256=measured["sha256"], size_bytes=measured["size_bytes"],
            status="verified" if all(measured[k] == expected[k] for k in measured) else "mismatch")
    row["checked_at"] = _now()
    return row


def _inventory(directory):
    """Enumerate regular files and reject symlinks/special entries at any depth."""
    root = _canonical(directory)
    if not root.is_dir():
        raise ValueError("directory_required")
    result, invalid = [], False
    def visit(path):
        nonlocal invalid
        with os.scandir(path) as entries:
            for entry in sorted(entries, key=lambda e: e.name):
                if entry.is_symlink():
                    invalid = True
                elif entry.is_dir(follow_symlinks=False):
                    visit(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    result.append(Path(entry.path))
                else:
                    invalid = True
    visit(root)
    return result, invalid


def _verify_producer(bundle):
    plan, proof = bundle["plan"], bundle["producer_verification"]
    selected = plan["producer_manifest"]
    destination = Path(plan["attempt_directory"]) / "custody" / "producer-manifest"
    artifact_key = None
    try:
        measured = _copy_file(selected["path"], destination)
        proof["manifest_observed_sha256"] = measured["sha256"]
        artifact_key = _artifact(bundle, destination, measured, role="producer_manifest", format="opaque")
        if any(measured[k] != selected[k] for k in measured):
            raise ValueError("producer_manifest_identity")
        manifest = _json(destination.read_bytes())
        contracts._schema(manifest, contracts.PRODUCER_MANIFEST_SCHEMA)
        manifest = contracts.validate_native_blast_database_producer_manifest(manifest,
            module_root=manifest["module_root"], python_executable=manifest["python"]["path"])
        if contracts._inside(selected["path"], manifest["module_root"], equal=True):
            raise ValueError("producer_manifest_inside_inventory")
    except (OSError, ValueError, TypeError, UnicodeError):
        _failure(bundle, "producer_manifest_invalid", artifact_key=artifact_key)
        return
    proof["manifest"] = manifest
    next(r for r in bundle["artifacts"] if r["artifact_key"] == artifact_key)["format"] = "json"
    try:
        observed, invalid = _inventory(manifest["module_root"])
        paths = {str(p.relative_to(manifest["module_root"])) for p in observed}
        proof["package_inventory_exact"] = not invalid and paths == {r["relative_path"] for r in manifest["package_files"]}
    except (OSError, ValueError):
        proof["package_inventory_exact"] = False
    if not proof["package_inventory_exact"]:
        _failure(bundle, "producer_package_inventory_mismatch")
    for expected in contracts._producer_files(manifest):
        row = _check_file(expected, kind=expected["kind"])
        proof["checks"].append(row)
        code = {"missing": "producer_file_missing", "mismatch": "producer_file_identity_mismatch",
                "unreadable": "producer_file_unreadable"}.get(row["status"])
        if code:
            _failure(bundle, code)
    root = Path(manifest["module_root"])
    proof["running_module_paths_match"] = (
        Path(__file__).resolve() == root / "gene_annotation_episode/native_blast_database_driver.py"
        and Path(contracts.__file__).resolve() == root / "gene_annotation_episode/native_blast_database_contracts.py"
        and Path(sys.executable).resolve() == Path(manifest["python"]["path"]))
    if not proof["running_module_paths_match"]:
        _failure(bundle, "producer_runtime_path_mismatch")
    if (proof["package_inventory_exact"] and proof["running_module_paths_match"]
            and all(r["status"] == "verified" for r in proof["checks"])):
        proof["status"] = "verified"


def _fasta(path, job):
    lengths, title, length = [], None, 0
    protein = job["program"] not in {"rpstblastn", "blastn_vdb"}
    alphabet = set("ABCDEFGHIKLMNPQRSTVWXYZJUO*") if protein else set("ACGTURYSWKMBDHVN")
    with Path(path).open("r", encoding="ascii") as stream:
        for raw in stream:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if title is not None:
                    if not length:
                        raise ValueError("empty_fasta_sequence")
                    lengths.append(length)
                title, length = line[1:].strip(), 0
                if not title:
                    raise ValueError("fasta_title_required")
            elif title is None or not set(line.upper()) <= alphabet:
                raise ValueError("fasta_symbols_or_framing_invalid")
            else:
                length += len(line)
    if title is None or not length:
        raise ValueError("nonempty_fasta_required")
    lengths.append(length)
    interval = contracts._options(job).get("-query_loc")
    if interval and any(int(interval.split("-")[1]) > n for n in lengths):
        raise ValueError("query_interval_out_of_bounds")


def _msa(path, job):
    """Validate selected CLUSTAL rows without selecting any default master."""
    lines = Path(path).read_text(encoding="ascii").splitlines()
    if not lines or re.match(r"^CLUSTAL(?:\s|$)", lines[0]) is None:
        raise ValueError("clustal_header_required")
    blocks, block = [], []
    for line in lines[1:]:
        if not line.strip():
            if block:
                blocks.append(block)
                block = []
            continue
        if line[0].isspace() and set(line.strip()) <= set("*:. \t"):
            continue
        parts = line.split()
        if (len(parts) not in {2, 3} or len(parts) == 3 and not parts[2].isdigit()
                or not re.fullmatch(r"[A-Za-z-]+", parts[1])):
            raise ValueError("clustal_record_invalid")
        block.append((parts[0], parts[1]))
    if block:
        blocks.append(block)
    if not blocks:
        raise ValueError("clustal_records_missing")
    members = [r[0] for r in blocks[0]]
    if len(set(members)) != len(members):
        raise ValueError("clustal_duplicate_identifier")
    for block in blocks:
        if [r[0] for r in block] != members or len({len(r[1]) for r in block}) != 1:
            raise ValueError("clustal_block_geometry_invalid")
    selected = job["query"]["msa_master_record_ordinal"]
    if selected is not None and (selected >= len(members) or not any(b[selected][1].replace("-", "") for b in blocks)):
        raise ValueError("selected_msa_master_unavailable")


def _pssm(path, job):
    # Reuse 306's supplied-byte syntax reader, not its numerical calculator or
    # biological master mapper. The producer retains the original input bytes.
    from .blast_pssm_inputs import read_blast_pssm
    sheet = read_blast_pssm(Path(path).read_bytes(), format="scoremat_asn_text",
        artifact_key=job["query"]["input_key"], source_ref="producer-input-syntax-check")
    if sheet["status"] != "complete" or len(sheet["pssms"]) != 1:
        raise ValueError("single_complete_scoremat_required")
    record = sheet["pssms"][0]
    if record["native_type"] != "PssmWithParameters":
        raise ValueError("native_pssm_with_parameters_required")
    pssm = record["native_pssm"]
    if (pssm.get("isProtein") is False or type(pssm.get("numRows")) is not int or pssm["numRows"] <= 0
            or type(pssm.get("numColumns")) is not int or pssm["numColumns"] <= 0):
        raise ValueError("protein_pssm_dimensions_required")
    if job["program"] == "tblastn_vdb":
        # The native source uses the actual query Seq-entry; never make one from
        # matrix dimensions, a title or a guessed master sequence.
        query = pssm.get("query")
        if not isinstance(query, dict) or set(query) not in ({"seq"}, {"set"}) or not query[next(iter(query))]:
            raise ValueError("vdb_pssm_query_seq_entry_required")


def _inputs(bundle):
    plan, job = bundle["plan"], bundle["requested_job"]["native_blast_database"]
    for row in job["inputs"]:
        key, destination = row["input_key"], plan["input_paths"][row["input_key"]]
        try:
            measured = _measure(destination) if row["path"] == destination else _copy_file(row["path"], destination)
        except (OSError, ValueError):
            _failure(bundle, "input_missing", input_key=key)
            continue
        artifact_key = _artifact(bundle, destination, measured, role=row["role"], format=row["format"], input_key=key)
        bundle["input_manifest"].append({"input_key": key, "original_path": row["path"], "realized_path": destination,
            "artifact_key": artifact_key, "expected_sha256": row["sha256"], "observed_sha256": measured["sha256"],
            "size_bytes": measured["size_bytes"]})
        if any(measured[k] != row[k] for k in measured):
            _failure(bundle, "input_identity_mismatch", input_key=key, artifact_key=artifact_key)
            continue
        if row["role"] == "metadata":
            continue  # Even a declared JSON payload is opaque to this producer.
        try:
            {"sequence": _fasta, "msa": _msa, "pssm": _pssm}[job["query"]["kind"]](destination, job)
        except (ValueError, UnicodeError, OSError, ImportError):
            _failure(bundle, "input_native_incompatible", input_key=key, artifact_key=artifact_key)


def _databases(bundle):
    root = Path(bundle["plan"]["attempt_directory"])
    for db in bundle["requested_job"]["native_blast_database"]["databases"]:
        key, manifest = db["database_key"], db["manifest"]
        row = {"database_key": key, "native_paths": db["native_paths"], "manifest_artifact_key": None,
            "preparation_receipt_artifact_key": None, "metadata_manifest_artifact_keys": [],
            "sidecar_artifacts": [], "checks": []}
        bundle["database_manifest"].append(row)
        cache = {}

        def capture(identity, role):
            cache_key = contracts._digest(identity), role
            if cache_key in cache:
                return cache[cache_key]
            destination = root / "custody" / ("database-" + contracts._digest(key)) / (role + "-" + contracts._digest(identity))
            artifact_key = None
            try:
                measured = _copy_file(identity["path"], destination)
            except FileNotFoundError:
                _failure(bundle, "database_file_missing", database_key=key)
            except (OSError, ValueError):
                _failure(bundle, "database_file_unreadable", database_key=key)
            else:
                artifact_key = _artifact(bundle, destination, measured, role=role,
                    format="opaque", database_key=key)
                if any(measured[k] != identity[k] for k in measured):
                    _failure(bundle, "database_identity_mismatch", database_key=key, artifact_key=artifact_key)
                if role == "database_manifest":
                    try:
                        decoded = _json(destination.read_bytes())
                        if decoded != manifest:
                            raise ValueError("inline_manifest_mismatch")
                    except (ValueError, UnicodeError, OSError):
                        _failure(bundle, "database_manifest_invalid", database_key=key, artifact_key=artifact_key)
                    else:
                        next(r for r in bundle["artifacts"] if r["artifact_key"] == artifact_key)["format"] = "json"
            cache[cache_key] = artifact_key
            return artifact_key

        row["manifest_artifact_key"] = capture(db["manifest_file"], "database_manifest")
        row["preparation_receipt_artifact_key"] = capture(manifest["preparation"]["receipt"], "preparation_receipt")
        for identity in manifest["metadata_manifests"]:
            artifact_key = capture(identity, "metadata")
            if artifact_key is not None:
                row["metadata_manifest_artifact_keys"].append(artifact_key)
        for role, identity in contracts._database_sidecars(db):
            if identity is not None:
                row["sidecar_artifacts"].append({"role": role, "identity": identity, "artifact_key": capture(identity, "metadata")})
        for expected in manifest["files"]:
            check = _check_file(expected)
            row["checks"].append(check)
            code = {"missing": "database_file_missing", "mismatch": "database_identity_mismatch",
                    "unreadable": "database_file_unreadable"}.get(check["status"])
            if code:
                _failure(bundle, code, database_key=key)
        if db["kind"] == "vdb":
            # Directories require a complete recursive inventory. No accessor,
            # accession resolver or downloader is invoked to establish it.
            for path in db["native_paths"]:
                try:
                    actual = _canonical(path)
                    if actual.is_dir():
                        files, invalid = _inventory(actual)
                        expected = {r["path"] for r in manifest["files"] if contracts._inside(r["path"], path)}
                        if invalid or {str(p) for p in files} != expected:
                            raise ValueError("vdb_inventory_not_exact")
                    elif not actual.is_file():
                        raise ValueError("vdb_prepared_path_missing")
                except (ValueError, OSError):
                    _failure(bundle, "database_manifest_invalid", database_key=key)


def _prepare_outputs(bundle, compiled):
    root = Path(bundle["plan"]["attempt_directory"])
    for name in ("tmp", "cache"):
        _canonical(root / name).mkdir(exist_ok=False)
    for row in compiled["outputs"]:
        key, path = row["output_key"], Path(row["path"])
        try:
            _canonical(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            if row["path_kind"] == "prefix":
                if any(path.parent.iterdir()):
                    _failure(bundle, "output_inventory_incomplete", output_key=key)
            elif path.exists():
                _failure(bundle, "output_inventory_incomplete", output_key=key)
        except (OSError, ValueError):
            _failure(bundle, "output_path_escape", output_key=key)


def _outputs(bundle, compiled):
    for selected in compiled["outputs"]:
        key, path = selected["output_key"], Path(selected["path"])
        row = {"output_key": key, "presence": "unknown", "artifact_keys": [], "inventory_complete": True}
        bundle["output_manifest"].append(row)
        try:
            _canonical(path)
            if selected["path_kind"] == "prefix":
                paths, invalid = _inventory(path.parent)
                if invalid:
                    row["inventory_complete"] = False
                    _failure(bundle, "output_path_escape", output_key=key)
            else:
                paths = [] if not path.exists() else [path]
        except FileNotFoundError:
            paths = []
        except ValueError:
            paths, row["inventory_complete"] = [], False
            _failure(bundle, "output_path_escape", output_key=key)
        except OSError:
            paths, row["inventory_complete"] = [], False
            _failure(bundle, "output_inventory_incomplete", output_key=key)
        for file in paths:
            try:
                measured = _measure(file)
            except _Changed:
                row["inventory_complete"] = False
                _failure(bundle, "output_changed_during_seal", output_key=key)
            except ValueError:
                row["inventory_complete"] = False
                _failure(bundle, "output_path_escape", output_key=key)
            except OSError:
                row["inventory_complete"] = False
                _failure(bundle, "output_unreadable", output_key=key)
            else:
                row["artifact_keys"].append(_artifact(bundle, file, measured, role=selected["role"], format=selected["format"],
                    output_key=key, fields=selected["fields"], delimiter=selected["delimiter"]))
        row["presence"] = "present" if row["artifact_keys"] else ("unknown" if not row["inventory_complete"] else
            "not_emitted" if selected["path_kind"] == "prefix" else "missing")
        if selected["required"] and bundle["process"]["returncode"] == 0 and not row["artifact_keys"]:
            _failure(bundle, "required_output_missing", output_key=key)


def _seal_output_checks(bundle):
    """One final byte check; changed files are excluded, never recaptured/retried."""
    root = Path(bundle["plan"]["attempt_directory"])
    for artifact in list(bundle["artifacts"]):
        if artifact["output_key"] is None:
            continue
        try:
            measured = _measure(root / artifact["relative_path"])
            if any(measured[k] != artifact[k] for k in measured):
                raise _Changed("output_changed")
        except (OSError, ValueError):
            key = artifact["output_key"]
            bundle["artifacts"].remove(artifact)
            row = next(r for r in bundle["output_manifest"] if r["output_key"] == key)
            row["artifact_keys"].remove(artifact["artifact_key"])
            row["inventory_complete"] = False
            row["presence"] = "present" if row["artifact_keys"] else "unknown"
            _failure(bundle, "output_changed_during_seal", output_key=key)
            selected = next(r for r in bundle["requested_job"]["native_blast_database"]["outputs"] if r["output_key"] == key)
            if selected["required"] and bundle["process"]["returncode"] == 0 and not row["artifact_keys"]:
                _failure(bundle, "required_output_missing", output_key=key)


def _envelope(plan, execution_id):
    return {"identity": {**plan["identity"], "execution_id": execution_id},
        "attempt_directory": plan["attempt_directory"], "plan_sha256": contracts._digest(plan)}


def run_native_blast_database_plan(plan_path):
    """Read and validate the complete plan before any native invocation."""
    selected_path = _regular(plan_path)
    plan = contracts._validate_plan(_json(selected_path.read_bytes()))
    root = _canonical(plan["attempt_directory"])
    if not root.is_dir():
        contracts._fail("existing_attempt_directory_required")
    # The selected plan is a control file even when its caller chooses its name.
    job = plan["requested_job"]["native_blast_database"]
    compiled = contracts.compile_native_blast_database_job(job, input_paths=plan["input_paths"],
        database_paths=plan["database_paths"], output_directory=plan["output_directory"])
    boundaries = [*plan["input_paths"].values(),
        *[str(Path(r["path"]).parent) if r["path_kind"] == "prefix" else r["path"] for r in compiled["outputs"]]]
    if any(contracts._overlap(str(selected_path), p) for p in boundaries):
        contracts._fail("selected_path_plan_overlap")
    execution_id = os.environ.get("PBS_JOBID")
    if not isinstance(execution_id, str) or not execution_id or "\0" in execution_id:
        contracts._fail("actual_pbs_execution_id_required")
    envelope = _envelope(plan, execution_id)
    owner, sealed = _canonical(root / OWNER_NAME), _canonical(root / BUNDLE_NAME)
    if owner.exists():
        if _json(_regular(owner).read_bytes()) != plan:
            contracts._fail("attempt_owner_conflict")
        if not sealed.exists():
            contracts._fail("unsealed_attempt_execution_uncertain")
        saved = contracts.validate_native_blast_database_bundle(_json(_regular(sealed).read_bytes()),
            original_job=job, attempt_identity=envelope)
        for row in saved["artifacts"]:
            measured = _measure(root / row["relative_path"])
            if any(measured[k] != row[k] for k in measured):
                contracts._fail("sealed_artifact_identity_mismatch")
        return saved
    if sealed.exists():
        contracts._fail("unowned_sealed_attempt")
    # Atomic ownership wins before staging or invocation; a concurrent invocation
    # cannot replace this record or interpret an unsealed owner as permission.
    _atomic_new(owner, plan)
    q = job["query"]
    bundle = {"version": "native_blast_database_bundle_v1", "identity": envelope["identity"], "plan": plan,
        "requested_job": plan["requested_job"], "program": job["program"], "mode": "database",
        "software": {"selected": job["software"], "observed_sha256": None, "version_source": None},
        "producer_verification": {"manifest": None, "manifest_observed_sha256": None,
            "package_inventory_exact": None, "running_module_paths_match": None, "checks": [], "status": "failed"},
        "realized_argv": compiled["argv"], "environment": contracts._effective_environment(plan),
        "input_manifest": [], "database_manifest": [], "output_manifest": [], "artifacts": [],
        "associations": {"query_input_key": q["input_key"], "master_record_ordinal": q["msa_master_record_ordinal"],
            "ignore_msa_master": q["ignore_msa_master"], "selected_options": job["options"], "external_manifest_keys": []},
        "process": {"started": False, "returncode": None, "started_at": None, "finished_at": None, "native_elapsed_seconds": None},
        "failures": [], "sealed_at": None}
    _verify_producer(bundle)
    try:
        measured = _measure(job["software"]["executable"])
    except (OSError, ValueError):
        _failure(bundle, "software_missing")
    else:
        bundle["software"]["observed_sha256"] = measured["sha256"]
        if measured["sha256"] != job["software"]["sha256"]:
            _failure(bundle, "software_identity_mismatch")
    _inputs(bundle)
    _databases(bundle)
    bundle["associations"]["external_manifest_keys"] = [r["manifest_artifact_key"] for r in
        bundle["database_manifest"] if r["manifest_artifact_key"] is not None]
    _prepare_outputs(bundle, compiled)
    if not bundle["failures"]:
        outputs = {r["role"]: Path(r["path"]) for r in compiled["outputs"]}
        try:
            with outputs["stdout"].open("xb") as stdout, outputs["stderr"].open("xb") as stderr:
                started_at, start = _now(), time.monotonic()
                # No shell, timeout, fallback, formatter, indexer or retry.
                result = subprocess.run(compiled["argv"], cwd=root, env=bundle["environment"],
                    stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, check=False)
                elapsed, finished_at = time.monotonic() - start, _now()
            bundle["process"] = {"started": True, "returncode": result.returncode, "started_at": started_at,
                "finished_at": finished_at, "native_elapsed_seconds": elapsed}
            if result.returncode != 0:
                _failure(bundle, "native_nonzero_exit")
        except OSError:
            _failure(bundle, "native_start_failed")
    _outputs(bundle, compiled)
    _seal_output_checks(bundle)
    bundle["sealed_at"] = _now()
    contracts.validate_native_blast_database_bundle(bundle, original_job=job, attempt_identity=envelope)
    _atomic_new(sealed, bundle)
    return bundle


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        contracts._fail("exact_plan_file_argument_required")
    bundle = run_native_blast_database_plan(arguments[0])
    print(json.dumps({"version": bundle["version"], "bundle_path": str(Path(bundle["plan"]["attempt_directory"]) / BUNDLE_NAME),
        "native_returncode": bundle["process"]["returncode"], "failure_count": len(bundle["failures"])}))
    return 0 if not bundle["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["run_native_blast_database_plan"]
