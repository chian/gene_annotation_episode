"""Durable custody for one selected finite local restriction operation.

The existing native lifecycle owns dispatch, cancellation and waiting. This
memo does not choose resources, retry work, interpret science or create credit.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat

from .acquisition import AcquisitionError
from .domain import ContractError, canonical, identity
from .local_jobs import LocalJobPolicy, run_cancellable_native
from . import native_lifecycle as native
from .native_file_capture import capture_native_file
from .restriction_mapping_contracts import restriction_canonical, restriction_digest
from .restriction_mapping_bound_contracts import (
    validate_restriction_bound_record, validate_restriction_alias_arguments,
    restriction_native_request,
)
from .restriction_mapping_worker import validate_restriction_worker_request


_ENVIRONMENT = frozenset(("PATH", "PYTHONHOME", "PYTHONPATH", "PYTHONNOUSERSITE",
    "PYTHONDONTWRITEBYTECODE", "TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME",
    "LANG", "LC_ALL", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"))
_IMPLEMENTATIONS = frozenset(("restriction_mapping_contracts.py", "restriction_mapping_readers.py",
    "restriction_mapping_worker.py", "restriction_mapping_inputs.py",
    "restriction_mapping_bound_contracts.py", "restriction_mapping_jobs.py"))
_HANDLE_FIXED = ("version", "unit", "command", "cwd", "stdout", "stderr", "paths", "request_sha256")


def _require(condition, code):
    if not condition:
        raise ContractError("restriction_" + code)


def _same(left, right):
    return restriction_canonical(left) == restriction_canonical(right)


def _bytes(value):
    return (restriction_canonical(value) + "\n").encode("utf-8")


def _pin(path):
    """Hash source bytes only; no module import or native analysis."""
    path = Path(path)
    info = path.lstat()
    _require(stat.S_ISREG(info.st_mode), "file_identity_conflict")
    digest = hashlib.sha256()
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
        after = os.fstat(stream.fileno())
    stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    _require(stamp(info) == stamp(before) == stamp(after) == stamp(path.lstat()),
        "file_identity_conflict")
    return {"path": str(path), "sha256": digest.hexdigest(), "size_bytes": info.st_size}


def _exclusive(path, raw):
    """Finish unchanged preparation; never replace an original request."""
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        _require(stat.S_ISREG(path.lstat().st_mode) and path.read_bytes() == raw,
            "request_conflict")
        return
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _command(reservation):
    return [reservation["software"]["python"]["path"], "-B", "-m",
        "gene_annotation_episode.restriction_mapping_worker", reservation["request_file"]["path"],
        reservation["output_directory"]]


def restriction_operation_directory(store, operation_key):
    """The fixed host-owned location; no preparation or filesystem mutation."""
    _require(type(operation_key) is str and bool(operation_key), "operation_key_invalid")
    return store.path / "native-restriction" / hashlib.sha256(operation_key.encode("utf-8")).hexdigest()


def _execute_original(handle, *, completed, cancel_event):
    """Only the shared finite wait; no Store access from its worker thread."""
    try:
        if not native.status(handle)["terminal"]:
            native.resume_start(handle, cancel_event=cancel_event)
        native.wait_job(handle, cancel_event=cancel_event)
    except AcquisitionError as error:
        completed["failure"] = {"code": error.code, "phase": error.phase, "operational": error.operational}
        return completed["failure"]
    completed["failure"] = None
    return None


class RestrictionMappingJobs:
    def __init__(self, store):
        self.store = store
        store.db.execute("""CREATE TABLE IF NOT EXISTS restriction_mapping_operations(
            operation_key TEXT PRIMARY KEY, reservation_artifact_ref TEXT NOT NULL,
            prepared_handle_artifact_ref TEXT, execution_proof_artifact_ref TEXT,
            published_source_ref TEXT, published_outcome TEXT,
            retired INTEGER NOT NULL DEFAULT 0, failure_artifact_ref TEXT,
            cleanup_started INTEGER NOT NULL DEFAULT 0)""")

    def _row(self, key):
        row = self.store.db.execute("SELECT * FROM restriction_mapping_operations WHERE operation_key=?",
            (key,)).fetchone()
        _require(row is not None, "operation_missing")
        return dict(row)

    def _artifact(self, reference):
        raw = self.store.get_artifact(reference)
        _require(reference == "artifact_" + hashlib.sha256(raw).hexdigest(), "artifact_identity_conflict")
        value = json.loads(raw)
        _require(raw == _bytes(value), "artifact_identity_conflict")
        return value

    def _reservation(self, row):
        reservation = validate_restriction_bound_record("Reservation",
            self._artifact(row["reservation_artifact_ref"]))
        _require(reservation["operation_key"] == row["operation_key"], "operation_conflict")
        directory = restriction_operation_directory(self.store, row["operation_key"])
        _require(reservation["directory"] == str(directory), "operation_directory_conflict")
        for field, name in (("output_directory", "output"), ("handle_path", "handle.json"),
                ("stdout_path", "stdout.txt"), ("stderr_path", "stderr.txt")):
            _require(reservation[field] == str(directory / name), "operation_directory_conflict")
        _require(reservation["request_file"]["path"] == str(directory / "request.json")
            and reservation["request_file"]["sha256"] == hashlib.sha256(
                _bytes(reservation["worker_request"])).hexdigest()
            and reservation["request_file"]["size_bytes"] == len(_bytes(reservation["worker_request"])),
            "request_conflict")
        return reservation

    def _input(self, reservation):
        # Lazy import avoids publication -> jobs -> publication initialization.
        from .restriction_mapping_publication import read_restriction_input
        retained = read_restriction_input(self.store, reservation["input_source_ref"])
        _require(_same(retained["sequence_binding"], reservation["sequence_binding"]), "input_conflict")
        request = reservation["worker_request"]
        _require(_same(request["selected_sequence"], reservation["sequence_binding"]), "input_conflict")
        if reservation["work_mode"] == "native":
            body = retained["body"]
            _require(all(_same(body[key], reservation[key]) for key in
                ("operation_key", "operation_ref", "tool_name", "arguments", "scope")), "input_conflict")
            expected = restriction_native_request(reservation["tool_name"], reservation["arguments"],
                sequence=retained["witness"]["sequence"], sequence_binding=retained["sequence_binding"])
            _require(_same(expected, request), "request_conflict")
        else:
            from .restriction_mapping_publication import read_published_restriction_result
            prior = read_published_restriction_result(self.store,
                reservation["prior_result_source_ref"], scope=reservation["scope"])
            _require(prior["body"]["tool_name"] == reservation["tool_name"]
                and prior["body"]["input_source_ref"] == reservation["input_source_ref"], "input_conflict")
            from .materials import artifact_path
            for role in ("native", "catalog"):
                file = prior["body"]["files"][role]
                pin = request[role + "_file"]
                _require((file is None) == (pin is None), "request_conflict")
                if file is not None:
                    _require(pin == {"path": str(artifact_path(self.store, file["artifact_ref"])),
                        "sha256": file["sha256"], "size_bytes": file["size_bytes"]}, "request_conflict")
        return retained

    def _software(self, reservation):
        software = reservation["software"]
        selected = list(software["implementation_files"])
        required = set(_IMPLEMENTATIONS)
        if reservation["work_mode"] == "native":
            required.add("restriction_mapping_native.py")
            selected.extend((software["native_source_file"], software["dictionary_file"]))
        supplied = {Path(row["path"]).name: row for row in software["implementation_files"]}
        _require(len(supplied) == len(software["implementation_files"])
            and required <= set(supplied), "software_conflict")
        package = Path(supplied["restriction_mapping_worker.py"]["path"]).parent
        _require(all(Path(supplied[name]["path"]).parent == package for name in required)
            and str(package.parent) in software["environment"].get("PYTHONPATH", "").split(os.pathsep),
            "software_conflict")
        selected.append(software["python"])
        try:
            _require(all(_pin(pin["path"]) == pin for pin in selected)
                and os.access(software["python"]["path"], os.X_OK), "software_conflict")
        except OSError as error:
            raise ContractError("restriction_software_conflict", detail={"reason": "selected_file_unavailable"}) from error
        environment = software["environment"]
        _require(set(environment) <= _ENVIRONMENT, "software_environment_conflict")
        directory = Path(reservation["directory"])
        for name in ("TMPDIR", "TMP", "TEMP"):
            _require(environment.get(name) == str(directory), "software_environment_conflict")
        cache = Path(environment.get("XDG_CACHE_HOME", "/"))
        _require(cache.is_absolute() and cache.is_relative_to(directory) and ".." not in cache.parts,
            "software_environment_conflict")

    def _handle(self, row, reservation, *, archived=False):
        _require(row["prepared_handle_artifact_ref"] is not None, "handle_unavailable")
        original = self._artifact(row["prepared_handle_artifact_ref"])
        _require(original["version"] == native.VERSION and original["stage"] == "prepared"
            and original["command"] == _command(reservation) and original["cwd"] == reservation["directory"]
            and original["stdout"] == reservation["stdout_path"]
            and original["stderr"] == reservation["stderr_path"]
            and _same(original["metadata"]["policy"], reservation["policy"]), "handle_conflict")
        for path in original["paths"].values():
            _require(Path(path).parent == Path(reservation["directory"]), "handle_conflict")
        if archived:
            return original
        handle = native.NativeJobHandle(Path(reservation["handle_path"]))
        current = handle.read()
        _require(all(_same(original[field], current[field]) for field in _HANDLE_FIXED)
            and _same(current["metadata"]["policy"], reservation["policy"]), "handle_conflict")
        control = Path(original["paths"]["request"])
        _require(_pin(control)["sha256"] == original["request_sha256"], "handle_conflict")
        expected = json.loads(control.read_bytes())
        _require(expected["command"] == _command(reservation)
            and expected["cwd"] == reservation["directory"]
            and expected["env"] == reservation["software"]["environment"]
            and expected["file_bytes"] == reservation["policy"]["scratch_bytes"], "handle_conflict")
        return handle

    def reserve(self, *, operation_key, tool_name, arguments, scope, input_source_ref,
            sequence_binding, worker_request, software, policy):
        _require(type(operation_key) is str and bool(operation_key), "operation_key_invalid")
        arguments = validate_restriction_alias_arguments(tool_name, arguments)
        normalized = self.store.validate_scope(scope)
        policy = policy.to_dict() if type(policy) is LocalJobPolicy else policy
        directory = restriction_operation_directory(self.store, operation_key)
        request = validate_restriction_worker_request(worker_request)
        raw = _bytes(request)
        reservation = validate_restriction_bound_record("Reservation", {
            "version": "restriction_operation_reservation_v1", "operation_key": operation_key,
            "operation_ref": identity("operation", {"key": operation_key, "name": tool_name, "arguments": arguments}),
            "tool_name": tool_name, "arguments": arguments, "scope": normalized,
            "work_mode": arguments["mode"], "input_source_ref": input_source_ref,
            "prior_result_source_ref": arguments.get("result_source_ref"),
            "sequence_binding": sequence_binding, "worker_request": request, "software": software,
            "policy": policy, "directory": str(directory), "request_file": {
                "path": str(directory / "request.json"), "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw)}, "output_directory": str(directory / "output"),
            "handle_path": str(directory / "handle.json"), "stdout_path": str(directory / "stdout.txt"),
            "stderr_path": str(directory / "stderr.txt")})
        with self.store.transaction():
            row = self.store.db.execute("SELECT * FROM restriction_mapping_operations WHERE operation_key=?",
                (operation_key,)).fetchone()
            if row is not None:
                _require(_same(self._reservation(dict(row)), reservation), "operation_conflict")
                if row["retired"] or row["execution_proof_artifact_ref"] is not None:
                    self.publication_state(operation_key)
                    return reservation
            self._input(reservation)
            self._software(reservation)
            if row is None:
                ref = self.store.artifact(_bytes(reservation), "application/json")
                self.store.db.execute("INSERT INTO restriction_mapping_operations(operation_key,reservation_artifact_ref) VALUES(?,?)",
                    (operation_key, ref))
        # Persist the original reservation before publishing any preparation.
        # A crash here leaves an unchanged reservation with no possible dispatch.
        try:
            self._prepare(operation_key, reservation, raw)
        except (AcquisitionError, ContractError, OSError) as error:
            self._remember_failure(operation_key, {"code": getattr(error, "code", str(error)),
                "phase": getattr(error, "phase", "local_preflight"),
                "operational": getattr(error, "operational", None)})
            raise
        return reservation

    def _remember_failure(self, operation_key, failure):
        with self.store.transaction():
            previous = self._row(operation_key)["failure_artifact_ref"]
            ref = self.store.artifact(_bytes({**failure, "previous_failure_artifact_ref": previous}), "application/json")
            self.store.db.execute("UPDATE restriction_mapping_operations SET failure_artifact_ref=? WHERE operation_key=?",
                (ref, operation_key))

    def _prepare(self, operation_key, reservation, raw):
        directory = Path(reservation["directory"])
        with self.store.transaction():
            directory.mkdir(parents=True, exist_ok=True)
            _require(directory.resolve() == directory, "operation_directory_conflict")
            _exclusive(Path(reservation["request_file"]["path"]), raw)
            row = self._row(operation_key)
            if row["prepared_handle_artifact_ref"] is None:
                path = Path(reservation["handle_path"])
                handle = (native.NativeJobHandle(path) if path.exists() else native.prepare_job(_command(reservation),
                    cwd=directory, policy=LocalJobPolicy(**reservation["policy"]), handle_path=path,
                    stdout_path=reservation["stdout_path"], stderr_path=reservation["stderr_path"],
                    env=reservation["software"]["environment"]))
                original = handle.read()
                _require(original["stage"] == "prepared", "handle_conflict")
                ref = self.store.artifact(_bytes(original), "application/json")
                self.store.db.execute("UPDATE restriction_mapping_operations SET prepared_handle_artifact_ref=? WHERE operation_key=?",
                    (ref, operation_key))
            self._handle(self._row(operation_key), reservation)

    def _closed_proof(self, row, reservation, failure):
        handle = self._handle(row, reservation)
        view = native.status(handle)
        _require(view["terminal"] and view["quiescent"], "writer_not_closed")
        body = handle.read()
        def capture(path, format):
            return capture_native_file(self.store, directory=reservation["directory"],
                relative_path=Path(path).name, format=format, media_type="application/json")["artifact_ref"]
        proof = validate_restriction_bound_record("ExecutionProof", {
            "version": "restriction_operation_execution_proof_v1",
            "reservation_sha256": restriction_digest(reservation),
            "handle_artifact_ref": capture(handle.path, "native_job_handle"),
            "control_request_artifact_ref": capture(body["paths"]["request"], "native_job_request"),
            "status_artifact_ref": capture(body["paths"]["status"], "native_job_status"),
            "native_receipt_artifact_ref": capture(body["paths"]["result"], "native_job_receipt")
                if view["native_receipt"] is not None else None,
            "original_view": view, "returncode": view["metadata"]["native_returncode"],
            "failure_code": failure["code"] if failure is not None else None})
        ref = self.store.artifact(_bytes(proof), "application/json")
        self.store.db.execute("UPDATE restriction_mapping_operations SET execution_proof_artifact_ref=? WHERE operation_key=?",
            (ref, row["operation_key"]))
        return proof

    async def run_async(self, operation_key):
        _require(not self.store.db.in_transaction, "native_work_requires_no_active_store_transaction")
        row = self._row(operation_key)
        if row["execution_proof_artifact_ref"] is not None:
            return self.publication_state(operation_key)["execution_proof"]
        reservation = self._reservation(row)
        self._input(reservation)
        _require(_pin(reservation["request_file"]["path"]) == reservation["request_file"], "request_conflict")
        handle = self._handle(row, reservation)
        if handle.read()["stage"] == "prepared":
            self._software(reservation)
        failure = None
        completed = {}
        try:
            failure = await run_cancellable_native(_execute_original, handle, completed=completed)
        finally:
            # A cancelled caller still retains the original closed process tree.
            # The shared async helper reaps its thread before raising cancellation;
            # preserve that adapter's actual failure rather than lose its return.
            failure = completed.get("failure", failure)
            view = native.status(handle)
            with self.store.transaction():
                if failure is not None:
                    previous = self._row(operation_key)["failure_artifact_ref"]
                    ref = self.store.artifact(_bytes({**failure, "original_view": view,
                        "previous_failure_artifact_ref": previous}), "application/json")
                    self.store.db.execute("UPDATE restriction_mapping_operations SET failure_artifact_ref=? WHERE operation_key=?",
                        (ref, operation_key))
                if view["terminal"] and view["quiescent"]:
                    self._closed_proof(row, reservation, failure)
        if failure is not None and self._row(operation_key)["execution_proof_artifact_ref"] is None:
            raise AcquisitionError(failure["code"], phase=failure["phase"], operational=failure["operational"])
        return self.publication_state(operation_key)["execution_proof"]

    def publication_state(self, operation_key):
        row = self._row(operation_key)
        reservation = self._reservation(row)
        self._input(reservation)
        proof = None
        if row["execution_proof_artifact_ref"] is not None:
            proof = validate_restriction_bound_record("ExecutionProof", self._artifact(row["execution_proof_artifact_ref"]))
            _require(proof["reservation_sha256"] == restriction_digest(reservation), "execution_proof_conflict")
            prepared = self._handle(row, reservation, archived=True)
            raw = self.store.get_artifact(proof["handle_artifact_ref"])
            closed = json.loads(raw)
            _require(all(_same(prepared[field], closed[field]) for field in _HANDLE_FIXED)
                and _same(closed["metadata"]["policy"], reservation["policy"]), "execution_proof_conflict")
            control = self.store.get_artifact(proof["control_request_artifact_ref"])
            _require(hashlib.sha256(control).hexdigest() == closed["request_sha256"], "execution_proof_conflict")
            view = proof["original_view"]
            _require(view["terminal"] and view["quiescent"]
                and _same(json.loads(self.store.get_artifact(proof["status_artifact_ref"])),
                    view["metadata"]["service_exit"])
                and _same(json.loads(self.store.get_artifact(proof["native_receipt_artifact_ref"]))
                    if proof["native_receipt_artifact_ref"] else None, view["native_receipt"])
                and proof["returncode"] == view["metadata"]["native_returncode"], "execution_proof_conflict")
            if not row["retired"] and not row["cleanup_started"] and row["published_source_ref"] is None:
                handle = self._handle(row, reservation)
                _require(handle.path.read_bytes() == raw, "execution_proof_conflict")
        elif not row["retired"] and row["prepared_handle_artifact_ref"] is not None:
            self._handle(row, reservation)
        _require((row["published_source_ref"] is None) == (row["published_outcome"] is None), "publication_conflict")
        return {"reservation": reservation, "reservation_artifact_ref": row["reservation_artifact_ref"],
            "execution_proof": proof, "execution_proof_artifact_ref": row["execution_proof_artifact_ref"],
            "published_source_ref": row["published_source_ref"],
            "published_outcome": json.loads(row["published_outcome"]) if row["published_outcome"] else None}

    def record_publication(self, operation_key, *, source_ref, outcome):
        _require(self.store.db.in_transaction, "publication_requires_active_store_transaction")
        state = self.publication_state(operation_key)
        reservation = state["reservation"]
        _require(state["execution_proof"] is not None, "writer_not_closed")
        from .alignment_site_native import immutable_record
        source = self.store._require(source_ref, {"source"})
        immutable_record(source)
        body = validate_restriction_bound_record("PublishedBody", json.loads(self.store.get_artifact(source["artifact_ref"])))
        _require(source["provider"] == "episode.restriction_result" and source["origin"] == "tool"
            and source["version"] == "restriction_published_result_v1"
            and all(_same(body[field], reservation[field]) for field in
                ("operation_key", "operation_ref", "tool_name", "arguments", "scope", "work_mode",
                 "input_source_ref", "prior_result_source_ref"))
            and body["reservation_artifact_ref"] == state["reservation_artifact_ref"]
            and body["execution_proof_artifact_ref"] == state["execution_proof_artifact_ref"]
            and outcome["operation_ref"] == reservation["operation_ref"]
            and outcome["result"]["source_ref"] == source_ref
            and outcome["result"]["input_source_ref"] == reservation["input_source_ref"]
            and outcome["status"] == body["status"]
            and outcome["record_refs"] == list(dict.fromkeys((reservation["input_source_ref"], source_ref))),
            "publication_conflict")
        encoded = canonical(outcome)
        if state["published_source_ref"] is not None:
            _require(state["published_source_ref"] == source_ref
                and _same(state["published_outcome"], outcome), "publication_conflict")
            return
        # The existing retained publication reader authenticates the complete
        # source/byte/outcome joins. Reuse its projection rather than create a
        # second numerical or result policy here. A failed check rolls back the
        # memo even if its caller catches the exception inside a transaction.
        with self.store.transaction():
            self.store.db.execute("UPDATE restriction_mapping_operations SET published_source_ref=?,published_outcome=? WHERE operation_key=?",
                (source_ref, encoded, operation_key))
            from .restriction_mapping_publication import read_published_restriction_result
            read_published_restriction_result(self.store, source_ref, scope=reservation["scope"])

    def retire(self, operation_key):
        try:
            return self._retire(operation_key)
        except (ContractError, AcquisitionError, OSError) as error:
            # Cleanup cannot rewrite committed science. Keep its own linked
            # diagnostic so the caller may return the original saved outcome.
            if not self.store.db.in_transaction and self.store.db.execute(
                    "SELECT 1 FROM restriction_mapping_operations WHERE operation_key=?", (operation_key,)).fetchone():
                self._remember_failure(operation_key, {"code": getattr(error, "code", str(error)),
                    "phase": "cleanup", "operational": getattr(error, "operational", None)})
            raise

    def _retire(self, operation_key):
        _require(not self.store.db.in_transaction, "retirement_requires_committed_publication")
        state = self.publication_state(operation_key)
        _require(state["published_source_ref"] is not None, "retirement_requires_committed_publication")
        reservation = state["reservation"]
        self._original_operation(state)
        row = self._row(operation_key)
        if row["retired"]:
            return
        self._retire_closed_files(operation_key, state, row)

    def _original_operation(self, state):
        reservation = state["reservation"]
        operation_key = reservation["operation_key"]
        exists = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='tool_operations'").fetchone()
        original = self.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (operation_key,)).fetchone() if exists else None
        _require(original is not None and original["id"] == reservation["operation_ref"]
            and original["name"] == reservation["tool_name"]
            and _same(json.loads(original["arguments"]), reservation["arguments"])
            and _same(self.store.validate_scope(json.loads(original["scope"])), reservation["scope"])
            and _same(json.loads(original["result"]), state["published_outcome"]),
            "retirement_requires_committed_original_operation")

    def _retire_closed_files(self, operation_key, state, row):
        reservation = state["reservation"]
        from .restriction_mapping_publication import read_published_restriction_result
        published = read_published_restriction_result(self.store, state["published_source_ref"], scope=reservation["scope"])
        # Require complete custody of every extant output before any deletion.
        files = published["body"]["files"]
        output = Path(reservation["output_directory"])
        if output.exists():
            _require(not output.is_symlink() and all(path.name in {
                "native.json", "catalog.json", "mapping.json", "manifest.json"}
                for path in output.iterdir()), "retirement_requires_captured_files")
        for role, path in [(name, Path(reservation["output_directory"]) / (name + ".json"))
                for name in ("native", "catalog", "mapping", "manifest")] + [
                ("stdout", Path(reservation["stdout_path"])), ("stderr", Path(reservation["stderr_path"]))]:
            if path.exists() or path.is_symlink():
                _require(files[role] is not None and _pin(path)["sha256"] == files[role]["sha256"]
                    and _pin(path)["size_bytes"] == files[role]["size_bytes"], "retirement_requires_captured_files")
        handle_path = Path(reservation["handle_path"])
        if handle_path.exists():
            handle = native.NativeJobHandle(handle_path) if row["cleanup_started"] else self._handle(row, reservation)
            if row["cleanup_started"]:
                _require(handle_path.read_bytes() == self.store.get_artifact(
                    state["execution_proof"]["handle_artifact_ref"]), "execution_proof_conflict")
            _require(native.status(handle)["quiescent"], "writer_not_closed")
        else:
            _require(row["cleanup_started"], "handle_unavailable")
            handle = None
        with self.store.transaction():
            self.store.db.execute("UPDATE restriction_mapping_operations SET cleanup_started=1 WHERE operation_key=?", (operation_key,))
        if handle is not None:
            native.release(handle)
        if Path(reservation["directory"]).exists():
            shutil.rmtree(reservation["directory"])
        with self.store.transaction():
            self.store.db.execute("UPDATE restriction_mapping_operations SET retired=1 WHERE operation_key=?", (operation_key,))


__all__ = ["RestrictionMappingJobs", "restriction_operation_directory"]
