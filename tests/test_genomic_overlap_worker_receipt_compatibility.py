"""Metadata-only validation of the five genuine, failed521 worker receipts.

This test reconstructs the original owned caller without advancing it.  The
failures remain failures; neither the producer nor a result worker is run.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sqlite3

import pytest

from test_genomic_overlap_file_retained import PREFIX, _records, _snapshot
from test_interval_pending_results import _fixture
from test_interval_results_presentation import _canonical, _inventory, _tables


PROOF_SHA256 = "1b2fb1116c04b506bb43714d9ca78837d40a8ac15409420c9179c05ef549ede9"
EPISODE_ID = "episode_4baa7298d980513497659eb7cb8e5d50625d95bbd4610fcec72727eee0107561"
RECEIPT_SHA256 = (
    "96c35259c071e8a19d436b8555d6c988e32e1932705e15c0a78d91b3e2f41128",
    "7c08a2a0bce195b0d57237412fecfad594556fbffc987a08ef558ac5550837dc",
    "ff32a3145306591c06bdd2cca3770d672e26932d40d70bd5a225bf0a152e6044",
    "a256b8a2be0acb23967676b47bd69f689e017b88682a750d29be74663537ca87",
    "7cccab8219d5f34148c4ef7da40bf07e100f70466ad5da9bc4569eabe8e34c6a",
)
OBSERVER_SIDECARS = {
    "state/state.sqlite3-shm": dict(kind="file", mode=0o644, size_bytes=32768,
        sha256="fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb"),
    "state/state.sqlite3-wal": dict(kind="file", mode=0o644, size_bytes=0,
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _forbidden(*args, **kwargs):
    raise AssertionError("metadata_receipt_check_must_not_execute_or_read_artifact_bodies")


class NoWork:
    complete = _forbidden
    release = _forbidden


def _gate():
    if os.environ.get("HMMER_NATIVE_ORACLE_GENOMIC_WORKER_RECEIPTS") != "1":
        pytest.skip("explicit original521 metadata validation gate required")
    path = Path(os.environ["HMMER_NATIVE_ORACLE_GENOMIC_CONTINUATION_PROOF"]).resolve(strict=True)
    expected = os.environ["HMMER_NATIVE_ORACLE_GENOMIC_CONTINUATION_PROOF_SHA256"]
    raw = path.read_bytes()
    assert expected == PROOF_SHA256 == _sha(raw)
    value = json.loads(raw)
    assert value["version"] == "genomic_overlap_retained_continuation_v1"
    assert value["passed"] is False and value["failure"] is not None
    assert value["original_prefix"] == str(PREFIX)
    assert value["original_failed_action_count"] == 5
    assert value["original_native_reexecuted"] is False
    assert value["prepared"] == []
    assert value["current_native_full_builder_verified"] is False
    assert value["current_saved_full_builder_verified"] is False
    assert PREFIX.resolve(strict=True) == PREFIX
    return path, value


def _guards(monkeypatch):
    from gene_annotation_episode import genomic_overlap_calculations as calculations
    from gene_annotation_episode import genomic_overlap_result_worker as worker
    from gene_annotation_episode import native_genomic_overlap_driver as driver
    from gene_annotation_episode import native_genomic_overlap_local as local
    from gene_annotation_episode import native_genomic_overlap_preparation as prep
    from gene_annotation_episode import native_atac_differential_preparation as shared_prep
    from gene_annotation_episode import native_lifecycle
    from gene_annotation_episode.acquisition import PublicClients
    from gene_annotation_episode.providers import _SessionConnection
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry

    for name in ("prepare_job", "start_prepared", "start_job", "resume_start", "status",
            "collect", "cancel", "release", "run_blocking", "wait_job"):
        monkeypatch.setattr(native_lifecycle, name, _forbidden)
    for name in ("_dependency_roots", "_runtime_dependencies", "_runtime_file_pin", "_snapshot", "_verify_snapshot",
            "prepare_genomic_overlap_worker", "_run"):
        monkeypatch.setattr(prep, name, _forbidden)
    monkeypatch.setattr(shared_prep, "_dependencies", _forbidden)
    monkeypatch.setattr(worker, "run_genomic_overlap_result_worker", _forbidden)
    monkeypatch.setattr(calculations, "calculate_genomic_overlap_components", _forbidden)
    monkeypatch.setattr(driver, "run_genomic_overlap_driver", _forbidden)
    monkeypatch.setattr(driver, "_native_call", _forbidden)
    monkeypatch.setattr(local, "prepare_local_genomic_overlap", _forbidden)
    monkeypatch.setattr(Store, "get_artifact", _forbidden)
    monkeypatch.setattr(Store, "put", _forbidden)
    monkeypatch.setattr(ToolRegistry, "execute", _forbidden)
    monkeypatch.setattr(ToolRegistry, "execute_async", _forbidden)
    monkeypatch.setattr(PublicClients, "_http", _forbidden)
    monkeypatch.setattr(_SessionConnection, "complete", _forbidden)
    for target in ("urllib.request.urlopen", "urllib.request.build_opener",
            "socket.create_connection", "socket.socket.connect"):
        monkeypatch.setattr(target, _forbidden)


def _query_only(connection):
    connection.execute("PRAGMA query_only=ON")
    assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
    permitted = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
        sqlite3.SQLITE_RECURSIVE}
    attempts = []

    def authorize(action, first, second, database, trigger):
        if action == sqlite3.SQLITE_PRAGMA and first == "table_info" and second is not None:
            return sqlite3.SQLITE_OK
        if action not in permitted:
            attempts.append(dict(action=action, first=first, second=second, database=database))
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    connection.set_authorizer(authorize)
    return attempts


def _observer_initialization(before, after):
    # Failed527 established these exact two readonly-observer creations:
    # removing them reproduces its original complete inventory hash exactly.
    # Original members, including the main database, may never change here.
    assert set(before) <= set(after)
    assert all(after[name] == value for name, value in before.items())
    created = {name: value for name, value in after.items() if name not in before}
    assert not created or created == OBSERVER_SIDECARS
    assert {name: after.get(name) for name in OBSERVER_SIDECARS} == OBSERVER_SIDECARS
    return created


def _original_receipts(reader, rows):
    result = []
    selected = {row["decision_index"]: row for row in rows
        if row["run_id"] == reader.owner.run_id and row["episode_id"] == EPISODE_ID
        and row["decision_index"] in range(5)}
    assert set(selected) == set(range(5))
    for index, expected in enumerate(RECEIPT_SHA256):
        row = selected[index]
        assert json.loads(row["action"]) == {
            "kind": "tool", "tool": "execution.results.collect", "arguments": {}}
        key = f"{reader.owner.run_id}:{EPISODE_ID}:{index}"
        path = reader.action_directory(EPISODE_ID, key) / "receipt.json"
        raw = path.read_bytes()
        assert len(raw) == 139417 and _sha(raw) == expected
        receipt = json.loads(raw)
        assert receipt["intent"]["operation_key"] == key
        assert receipt["intent"]["episode_id"] == EPISODE_ID
        assert receipt["intent"]["run_id"] == reader.owner.run_id
        assert receipt["version"] == "native_genomic_overlap_acquired_result_v1"
        assert receipt["delivery_complete"] is False
        execution, capture = receipt["worker_execution"], receipt["worker_capture"]
        assert "dependencies" not in execution
        assert execution["outcome"] == "returned" and execution["returncode"] == 1
        assert capture["result"] is None and capture["outputs"] == []
        assert receipt["projection"] is None
        assert receipt["facts"]["genomic_overlap_pair_metrics"] == []
        assert receipt["facts"]["genomic_overlap_saved_sheets"] == []
        reader.match_outcome(row, receipt)
        result.append((path, receipt))
    return result


def test_original_five_failed_worker_receipts_validate_without_dependency_discovery(tmp_path, monkeypatch):
    proof_path, original = _gate()
    helper = _fixture(dict(name="overlap_complete"), monkeypatch)
    _guards(monkeypatch)
    from gene_annotation_episode.episode_composition import scientific_binding_compatible
    from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
    from gene_annotation_episode.genomic_overlap_result_receipts import GenomicOverlapResultReceipts
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry

    configuration = deepcopy(original["restored_configuration"])
    assert ExecutionServiceFactory.from_record(configuration["factory"]).as_record() == configuration["factory"]
    initial_files = _inventory(PREFIX)
    database = PREFIX / "state/state.sqlite3"
    # A readonly SQLite connection can initialize WAL/SHM on this WAL-mode
    # database. Establish the strict baseline after that explicit observation.
    before_tables = _snapshot(database)
    before_files = _inventory(PREFIX)
    report = dict(version="genomic_overlap_worker_receipt_compatibility_v1", passed=False,
        continuation_proof=dict(path=str(proof_path), sha256=PROOF_SHA256),
        original_prefix=str(PREFIX), original_continuation_passed=False,
        original_worker_failures_preserved=False, validated=[], engineered_rejections=[],
        constructor_schema_additions=[], new_scientific_work=False,
        initial_files=initial_files, baseline_files=before_files,
        readonly_observer_sidecars=OBSERVER_SIDECARS)
    store = None
    validation_completed = False
    try:
        report["readonly_observer_created"] = _observer_initialization(initial_files, before_files)
        store = Store(PREFIX / "state")
        flow, registry = helper.assemble(store, PREFIX, NoWork(), configuration)
        owner = flow.episode_bindings.for_role("results")
        assert isinstance(registry, ToolRegistry) and owner.store is store
        assert owner.tool_registry is registry and owner.run_id == helper.RUN_ID
        assert owner.directory == PREFIX / "run" and store.path == PREFIX / "state"
        assert owner.resources == configuration["factory"]["resources"]
        reader = owner.native_genomic_overlap_results.receipts
        assert isinstance(reader, GenomicOverlapResultReceipts) and reader.owner is owner
        assert _tables(store.db) == before_tables, "constructor changed the original Store"
        denied_queries = _query_only(store.db)
        scientific = flow.episode_bindings.for_role("scientific_process")
        assert scientific is flow.scientific_process_binding
        recorded = deepcopy(configuration["scientific_binding"])
        actual = scientific.as_record()
        assert recorded["implementation_sha256"] == "f74c77cd6e9a080313662d5a3d11114bc03ff223ebac4f3c6c34e75a13fce4f3"
        assert actual["implementation_sha256"] == "440744897da3527ac75775c40b94d394e9e81d71b4308a23db57591ef052b42f"
        assert {key: value for key, value in actual.items() if key != "implementation_sha256"} == {
            key: value for key, value in recorded.items() if key != "implementation_sha256"}
        assert scientific_binding_compatible(actual, recorded)
        assert not scientific_binding_compatible(recorded, actual)
        rejected_descriptors = []
        for change in ("unknown_implementation", "changed_library", "changed_tool_library", "changed_child_roles"):
            damaged = deepcopy(recorded)
            if change == "unknown_implementation":
                damaged["implementation_sha256"] = "0" * 64
            elif change == "changed_library":
                damaged["configuration"]["library"]["manifest_sha256"] = "0" * 64
            elif change == "changed_tool_library":
                damaged["configuration"]["tool_library"]["catalog_sha256"] = "0" * 64
            else:
                damaged["configuration"]["child_roles"] = list(reversed(damaged["configuration"]["child_roles"]))
            assert damaged != recorded
            assert not scientific_binding_compatible(actual, damaged)
            rejected_descriptors.append(change)
        assert configuration["scientific_binding"] == recorded
        report["scientific_binding"] = dict(recorded_descriptor=recorded, reopened_descriptor=actual,
            forward_accepted=True, reverse_denied=True, engineered_denials=rejected_descriptors,
            original_descriptor_unchanged=True,
            custody_change="AlphaFold/EMDB Source forwarding excludes private request/auxiliary controls; "
                "explicit primary data File receipts remain separate. This is a directed repair, "
                "not globally identical reference semantics.")
        receipts = _original_receipts(reader, _records(before_tables, "runtime_actions"))
        original_get = store.get
        metadata_refs = []

        def metadata_only(ref):
            assert isinstance(ref, str) and ref.startswith("artifact_")
            value = original_get(ref)
            assert value["record_type"] == "artifact"
            metadata_refs.append(ref)
            return value

        monkeypatch.setattr(store, "get", metadata_only)
        actual_read_bytes = Path.read_bytes
        actual_read_text = Path.read_text

        def deny_artifact_bytes(path, *args, **kwargs):
            assert not path.is_relative_to(store.path / "artifacts"), "private artifact byte read"
            return actual_read_bytes(path, *args, **kwargs)

        def deny_artifact_text(path, *args, **kwargs):
            assert not path.is_relative_to(store.path / "artifacts"), "private artifact text read"
            return actual_read_text(path, *args, **kwargs)

        # Physical preservation hashes happen outside this application-read guard.
        with monkeypatch.context() as body_guard:
            body_guard.setattr(Path, "read_bytes", deny_artifact_bytes)
            body_guard.setattr(Path, "read_text", deny_artifact_text)
            for path, receipt in receipts:
                saved = deepcopy(receipt)
                assert reader.validate_worker(receipt) is None
                assert receipt == saved
                report["validated"].append(dict(operation_key=receipt["intent"]["operation_key"],
                    path=str(path), sha256=_sha(actual_read_bytes(path)), worker_returncode=1,
                    result=None, dependencies_recorded=False, outcome="failed_worker_preserved"))
            for change in ("unknown_execution_field", "missing_interpreter", "invalid_dependencies"):
                damaged = deepcopy(receipts[0][1])
                execution = damaged["worker_execution"]
                if change == "unknown_execution_field":
                    execution["engineered_extra"] = None
                elif change == "missing_interpreter":
                    del execution["interpreter"]
                else:
                    execution["dependencies"] = []
                with pytest.raises(ValueError):
                    reader.validate_worker(damaged)
                report["engineered_rejections"].append(change)
        assert metadata_refs and denied_queries == []
        assert _tables(store.db) == before_tables
        report["metadata_file_refs"] = sorted(set(metadata_refs))
        report["denied_sql_attempts"] = denied_queries
        report["original_failed_action_count"] = len(receipts)
        validation_completed = True
    except BaseException as exc:
        report["failure"] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        if store is not None:
            store.db.close()
        before_final_observer = _inventory(PREFIX)
        after_tables = _snapshot(database)
        after_files = _inventory(PREFIX)
        report["before_final_readonly_observer_files"] = before_final_observer
        report["after_files"] = after_files
        try:
            report["final_readonly_observer_created"] = _observer_initialization(before_final_observer, after_files)
            report["final_readonly_observer_valid"] = True
        except AssertionError:
            report["final_readonly_observer_valid"] = False
        report["all_initial_members_unchanged"] = all(
            after_files.get(name) == value for name, value in initial_files.items())
        report["all_tables_unchanged"] = after_tables == before_tables
        report["all_files_and_modes_unchanged"] = after_files == before_files
        report["before_tables_sha256"] = _sha(_canonical(before_tables).encode())
        report["after_tables_sha256"] = _sha(_canonical(after_tables).encode())
        report["before_files_sha256"] = _sha(_canonical(before_files).encode())
        report["after_files_sha256"] = _sha(_canonical(after_files).encode())
        report["table_counts"] = {name: len(value["rows"]) for name, value in before_tables.items()}
        report["continuation_proof_unchanged"] = _sha(proof_path.read_bytes()) == PROOF_SHA256
        report["original_worker_failures_preserved"] = (
            len(report["validated"]) == 5 and report["all_tables_unchanged"]
            and report["all_files_and_modes_unchanged"])
        report["passed"] = (validation_completed and report["original_worker_failures_preserved"]
            and report["continuation_proof_unchanged"] and report["all_initial_members_unchanged"]
            and report["final_readonly_observer_valid"])
        (tmp_path / "GENOMIC_OVERLAP_WORKER_RECEIPT_COMPATIBILITY.json").write_text(
            json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n")
        assert report["all_tables_unchanged"] and report["all_files_and_modes_unchanged"]
        assert report["continuation_proof_unchanged"] and report["all_initial_members_unchanged"]
        assert report["final_readonly_observer_valid"]
