"""Real Store byte custody with explicitly engineered private publications.

The ToolOperation/Source rows establish only test metadata roles, not native
production or authenticated scientific results. No solver, calculation, worker
or complete Workflow is exercised. Capture callers own their access authority;
verifying retained bytes neither supplies that authority nor grants receipts.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import os
from pathlib import Path

import pytest

from gene_annotation_episode import enrichr_reference_privacy, materials
from gene_annotation_episode import molecular_reference_privacy
from gene_annotation_episode import native_file_capture as capture
from gene_annotation_episode.domain import ContractError, canonical
from test_molecular_sequence_input_bindings import actual_received_input_owner


PROVIDER = "perform_flux_balance_analysis"
VERSION = "ordinary_flux_balance_result_v1"
TABLES = ("records", "artifacts", "tool_operations", "runtime_actions", "runtime_episodes",
    "runtime_receipt_inheritance", "runtime_record_receipts")


@contextmanager
def private_publication(tmp_path, *, data=b"engineered private output", role="auxiliary", grant=False):
    """Actual Store/receipts, with a deliberately engineered publication row."""
    with actual_received_input_owner(tmp_path, deliver=False) as value:
        store = value.store
        store.db.execute("CREATE TABLE tool_operations(operation_key TEXT PRIMARY KEY,id TEXT,name TEXT,"
            "arguments TEXT,scope TEXT,result TEXT)")
        reference = store.artifact(data, "text/plain")
        native = store.artifact(b'{"engineered_publication":true}', "application/json")
        control = reference if role == "control" else store.artifact(b"engineered host control", "text/plain")
        source = store.put("source", {"provider": PROVIDER, "accession": None, "uri": None,
            "artifact_ref": native, "text_ref": None, "request_ref": control, "version": VERSION,
            "retrieved_at": None, "auxiliary_artifact_refs": [reference] if role == "auxiliary" else []}, origin="tool")
        key = "engineered-private-output-publication"
        outcome = {"status": "completed", "operation_ref": key, "record_refs": [source["id"]],
            "result": {"version": VERSION, "mode": "calculate_saved", "source_ref": source["id"],
                "saved_sheets": []}, "feedback": None}
        store.db.execute("INSERT INTO tool_operations VALUES(?,?,?,?,?,?)", (key, key, PROVIDER,
            canonical({"mode": "calculate_saved"}), canonical(value.scope), canonical(outcome)))
        if role == "diagnostic":
            failed = {"status": "failed", "operation_ref": "engineered-failed-capture", "record_refs": [],
                "result": None, "feedback": {"diagnostic_ref": reference}}
            store.db.execute("INSERT INTO tool_operations VALUES(?,?,?,?,?,?)", (key + ":failed",
                "engineered-failed-capture", PROVIDER, "{}", canonical(value.scope), canonical(failed)))
        value.receipts.receive(value.parent.episode_id, [source["id"]], kind="initial")
        if grant:
            value.receipts.receive(value.parent.episode_id, [reference], kind="initial")
        value.context = value.child(1)
        value.private_ref = reference
        value.private_path = store.path / "artifacts" / reference[9:11] / reference[9:]
        value.private_identity = {"artifact_ref": reference, "sha256": hashlib.sha256(data).hexdigest(),
            "size_bytes": len(data), "format": "engineered_native_output"}
        value.publication_source = source
        yield value


def rows(store):
    return {table: [tuple(row) for row in store.db.execute("SELECT * FROM " + table + " ORDER BY rowid")]
        for table in TABLES}


def public_denied(value, monkeypatch):
    original_open = Path.open
    def guarded_open(path, *args, **kwargs):
        assert path != value.private_path, "public material read opened private bytes"
        return original_open(path, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", guarded_open)
        with pytest.raises(ContractError, match="^molecular_private_artifact_not_readable$"):
            materials.artifact_path(value.store, value.private_ref)


def fails(code, function, *args):
    with pytest.raises(capture.NativeFileCaptureError) as caught:
        function(*args)
    assert caught.value.code == str(caught.value) == code


@pytest.mark.parametrize("data", [b"independently produced private bytes", b""], ids=["private-output", "empty-stdout"])
@pytest.mark.parametrize("grant", [False, True], ids=["source-only", "explicit-private-file-receipt"])
def test_independent_capture_of_identical_private_bytes_preserves_receipts_and_public_denial(tmp_path, monkeypatch, data, grant):
    with private_publication(tmp_path, data=data, grant=grant) as value:
        producer = tmp_path / "independent-producer"
        producer.mkdir()
        output = producer / "worker.stdout"
        output.write_bytes(data)
        known = set(value.receipts.known(value.context.episode_id))
        assert value.publication_source["id"] in known
        assert (value.private_ref in known) is grant
        assert molecular_reference_privacy.molecular_reference_restriction(value.store, value.context,
            value.private_ref, "artifact") is False
        before = rows(value.store)
        public_denied(value, monkeypatch)
        identity = capture.capture_native_file(value.store, directory=str(producer),
            relative_path="worker.stdout", format="worker_stdout", media_type="text/plain")
        assert identity == {**value.private_identity, "format": "worker_stdout"}
        assert capture.retained_native_file(value.store, identity) == value.private_path
        assert value.private_path.read_bytes() == output.read_bytes() == data
        assert set(value.receipts.known(value.context.episode_id)) == known
        assert rows(value.store) == before
        public_denied(value, monkeypatch)


@pytest.mark.parametrize("role", ["auxiliary", "control", "diagnostic"])
def test_private_retained_verification_streams_identity_without_consulting_access_or_granting_it(tmp_path, monkeypatch, role):
    data = b"x" * (2 * 1024 * 1024) + b"end"
    with private_publication(tmp_path, data=data, role=role) as value:
        public_denied(value, monkeypatch)
        before, changes = rows(value.store), value.store.db.total_changes
        original_open = Path.open
        lengths = []
        class Stream:
            def __init__(self, handle): self.handle = handle
            def read(self, size=-1):
                assert 0 < size <= 1024 * 1024
                result = self.handle.read(size)
                lengths.append(len(result))
                return result
        @contextmanager
        def opened(path, *args, **kwargs):
            assert path == value.private_path and args == ("rb",) and not kwargs
            with original_open(path, *args, **kwargs) as handle:
                yield Stream(handle)
        def forbidden(*args, **kwargs):
            pytest.fail("byte identity verification performed a permission check or bulk payload read")
        with monkeypatch.context() as patch:
            patch.setattr(Path, "open", opened)
            patch.setattr(Path, "read_bytes", forbidden)
            patch.setattr(value.store, "get_artifact", forbidden)
            patch.setattr(enrichr_reference_privacy, "enrichr_reference_restriction", forbidden)
            patch.setattr(molecular_reference_privacy, "molecular_reference_restriction", forbidden)
            assert capture.retained_native_file(value.store, value.private_identity) == value.private_path
        assert lengths == [1048576, 1048576, 3, 0]
        assert rows(value.store) == before and value.store.db.total_changes == changes
        public_denied(value, monkeypatch)


@pytest.mark.parametrize("fault", ["none", "extra", "boolean-size", "float-size", "empty-format",
    "uppercase-digest", "different-reference", "missing-format"])
def test_private_identity_shape_is_validated_before_payload_access(tmp_path, monkeypatch, fault):
    with private_publication(tmp_path) as value:
        identity = deepcopy(value.private_identity)
        if fault == "none": identity = None
        elif fault == "extra": identity["access_granted"] = True
        elif fault == "boolean-size": identity["size_bytes"] = True
        elif fault == "float-size": identity["size_bytes"] = float(identity["size_bytes"])
        elif fault == "empty-format": identity["format"] = ""
        elif fault == "uppercase-digest": identity["sha256"] = identity["sha256"].upper()
        elif fault == "different-reference": identity["artifact_ref"] = "artifact_" + "0" * 64
        else: del identity["format"]
        before, changes = rows(value.store), value.store.db.total_changes
        with monkeypatch.context() as patch:
            patch.setattr(Path, "open", lambda *a, **k: pytest.fail("malformed identity opened payload"))
            fails("invalid_file_identity", capture.retained_native_file, value.store, identity)
        assert rows(value.store) == before and value.store.db.total_changes == changes
        public_denied(value, monkeypatch)


@pytest.mark.parametrize("fault,code", [("same-size", "retained_artifact_mismatch"),
    ("truncated", "retained_artifact_mismatch"), ("removed", "retained_artifact_unavailable"),
    ("symlink", "retained_artifact_unavailable"), ("fifo", "retained_artifact_unavailable")])
def test_private_retained_tampering_keeps_identity_failures_and_public_denial(tmp_path, monkeypatch, fault, code):
    with private_publication(tmp_path, data=b"original private bytes") as value:
        public_denied(value, monkeypatch)
        if fault == "same-size": value.private_path.write_bytes(b"x" * value.private_identity["size_bytes"])
        elif fault == "truncated": value.private_path.write_bytes(b"x")
        else:
            value.private_path.unlink()
            if fault == "fifo": os.mkfifo(value.private_path)
            elif fault == "symlink":
                replacement = tmp_path / "replacement"
                replacement.write_bytes(b"original private bytes")
                value.private_path.symlink_to(replacement)
        before, changes = rows(value.store), value.store.db.total_changes
        with monkeypatch.context() as patch:
            if fault != "same-size":
                patch.setattr(Path, "open", lambda *a, **k: pytest.fail("invalid retained node opened payload"))
            fails(code, capture.retained_native_file, value.store, value.private_identity)
        assert rows(value.store) == before and value.store.db.total_changes == changes
        public_denied(value, monkeypatch)


@pytest.mark.parametrize("field,value", [("size", 999), ("sha256", "0" * 64), ("media_type", "")])
def test_private_catalog_identity_mismatch_is_not_bypassed_or_repaired(tmp_path, monkeypatch, field, value):
    with private_publication(tmp_path) as publication:
        publication.store.db.execute("UPDATE artifacts SET " + field + "=? WHERE id=?", (value, publication.private_ref))
        before, changes = rows(publication.store), publication.store.db.total_changes
        with monkeypatch.context() as patch:
            patch.setattr(Path, "open", lambda *a, **k: pytest.fail("invalid metadata opened payload"))
            fails("retained_artifact_mismatch", capture.retained_native_file, publication.store, publication.private_identity)
        assert rows(publication.store) == before and publication.store.db.total_changes == changes
        public_denied(publication, monkeypatch)


@pytest.mark.parametrize("data", [b"ordinary public bytes", b""])
def test_unrelated_public_artifact_and_retained_identity_remain_readable(tmp_path, data):
    with actual_received_input_owner(tmp_path, raw=data) as value:
        metadata = value.store.get(value.artifact_ref)
        identity = {"artifact_ref": value.artifact_ref, "sha256": metadata["sha256"],
            "size_bytes": metadata["size"], "format": "explicit_opaque_format"}
        before, changes = rows_without_publication(value.store), value.store.db.total_changes
        public = materials.artifact_path(value.store, value.artifact_ref)
        retained = capture.retained_native_file(value.store, identity)
        assert retained == public and retained.read_bytes() == data
        assert rows_without_publication(value.store) == before and value.store.db.total_changes == changes


def rows_without_publication(store):
    return {table: [tuple(row) for row in store.db.execute("SELECT * FROM " + table + " ORDER BY rowid")]
        for table in TABLES if table != "tool_operations"}
