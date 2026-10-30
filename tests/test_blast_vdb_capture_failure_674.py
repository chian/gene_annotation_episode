"""Missing selected inputs preserve requested original bytes, in bounded529.

Native execution is controlled engineering data. These tests exercise actual
capture custody, result receipts, requested facts and immediate-parent admission.
"""
import asyncio
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode import native_blast_utility_capture_failure as failed
from gene_annotation_episode import native_blast_utility_result_worker as worker
from gene_annotation_episode import native_blast_utility_acquisition as acquisition
from gene_annotation_episode import native_blast_utility_contracts as contracts
from gene_annotation_episode import native_blast_utility_results as results
from gene_annotation_episode import native_blast_utility_result_publication as publication
from gene_annotation_episode.communication import form_with_facts
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.execution_contracts import canonical

import test_blast_vdb_publication_returns_669 as helpers
from test_blast_vdb_native_context_668 import (
    controlled_capture, controlled_job, controlled_dependency_job,
)


def missing_capture(tmp_path, kind, *, native_returncode=0):
    if kind in {"dependency_list", "metadata_with_present_dependency_list"}:
        job = controlled_dependency_job(tmp_path, declaration="metadata")
    else:
        job = controlled_job(tmp_path, variant="entry_batch" if kind == "entry_batch" else "entry",
            database_source="dbs_file" if kind == "dbs_file" else "db")
    if kind in {"entry_batch", "dbs_file"}:
        role = "entry_batch" if kind == "entry_batch" else "database_list"
        omission = next(("input", row["role"], i) for i, row in enumerate(job["inputs"])
            if row["role"] == role)
    elif kind == "dependency_list":
        address = job["vdb_context_request"]["database_lists"][0]["selection"]
        db = next(d for d in [*job["databases"], *job["vdb_context_request"]["dependency_databases"]]
            if d["database_key"] == address["database_key"])
        path = db["manifest"]["files"][address["file_index"]]["path"]
        omission = next(("database", row["role"], i)
            for i, row in enumerate(contracts.database_file_selections(job))
            if row["original_path"] == path)
    else:
        omission = next(("database", row["role"], i)
            for i, row in enumerate(contracts.database_file_selections(job))
            if row["role"] == "metadata_manifest")
    store, capture = controlled_capture(tmp_path, job=job, omit=(omission,), returncode=native_returncode)
    with pytest.raises(ContractError, match="^" + failed.QUALIFICATION_FAILURE + "$"):
        worker.qualified_utility_context(capture)
    return store, capture


def selected_failure(store, capture, directory, *, selector=None):
    directory.mkdir(parents=True, exist_ok=True)
    selector = helpers.selector(sequences=helpers.sequence_selection(0), vdb_context=True,
        artifacts=[{"direction": "output", "role": "stdout", "ordinal": 0},
            {"direction": "output", "role": "stderr", "ordinal": 0},
            {"direction": "output", "role": "preparation_receipt", "ordinal": 0}],
        saved_data=["result"]) if selector is None else selector
    problems = [results._failure("prepare")]
    receipt = failed.publish_capture_failure(store, capture=capture, selector=selector,
        operational_failures=problems, directory=directory)
    return receipt, selector, problems


@pytest.mark.parametrize("kind", ["metadata", "entry_batch", "dbs_file", "dependency_list"])
def test_missing_input_returns_actual_selected_bytes_without_result_or_context(tmp_path, monkeypatch, kind):
    store, capture = missing_capture(tmp_path, kind)
    try:
        monkeypatch.setattr(publication, "run_local_job", helpers.forbidden)
        receipt, chosen, problems = selected_failure(store, capture, tmp_path / "failure")
        projection = receipt["projection"]
        assert projection["sequences"] == projection["vdb_context"] == projection["saved_data"] == []
        assert projection["status"]["native_state"] == "succeeded"
        assert projection["status"]["inventory_complete"] is False
        assert projection["status"]["state"] == "partial"
        assert [row["role"] for row in projection["artifacts"]] == ["stdout", "stderr", "preparation_receipt"]
        assert projection["record_refs"] == list(dict.fromkeys([capture["source_ref"],
            *[row["artifact_ref"] for row in projection["artifacts"]]]))
        for row in projection["artifacts"]:
            actual = store.get_artifact(row["artifact_ref"])
            assert len(actual) == row["size_bytes"] and hashlib.sha256(actual).hexdigest() == row["sha256"]
        assert {row["request"]["type"] for row in projection["missing"]} == {
            "sequence_selector", "vdb_context", "saved_data"}
        assert any(row["code"] in {"dependency_unavailable", "input_population_unavailable"}
            for row in projection["failures"])
        assert failed.validate_capture_failure(store, capture=capture, selector=chosen,
            operational_failures=problems, publication=receipt) == receipt
        assert json.loads((tmp_path / "failure" / failed.FILENAME).read_text()) == receipt
    finally:
        store.close()


@pytest.mark.parametrize("kind", ["dependency_list", "metadata_with_present_dependency_list"])
def test_unqualified_database_list_is_missing_without_suppressing_available_stdout(tmp_path, kind):
    store, capture = missing_capture(tmp_path, kind)
    try:
        chosen = helpers.selector(artifacts=[{"direction": "input", "role": "database_list", "ordinal": 0},
            {"direction": "output", "role": "stdout", "ordinal": 0}])
        original = deepcopy(capture)
        receipt, _, _ = selected_failure(store, capture, tmp_path / "failure", selector=chosen)
        projection = receipt["projection"]
        assert [r["role"] for r in projection["artifacts"]] == ["stdout"]
        assert projection["missing"] == [{"version": "native_blast_utility_missing_fact_v2",
            "source_ref": capture["source_ref"], "request": {"type": "artifact", "slot": chosen["artifacts"][0]},
            "reason": "artifact_unavailable"}]
        assert capture == original
    finally:
        store.close()


def test_declared_dbs_file_bytes_stay_available_when_other_selected_metadata_is_missing(tmp_path):
    job = controlled_job(tmp_path, database_source="dbs_file")
    omission = next(("database", row["role"], i) for i, row in enumerate(contracts.database_file_selections(job))
        if row["role"] == "metadata_manifest")
    store, capture = controlled_capture(tmp_path, job=job, omit=(omission,))
    try:
        chosen = helpers.selector(artifacts=[{"direction": "input", "role": "database_list", "ordinal": 0}])
        receipt, _, _ = selected_failure(store, capture, tmp_path / "failure", selector=chosen)
        assert len(receipt["projection"]["artifacts"]) == 1
        assert receipt["projection"]["artifacts"][0]["occurrence_id"] == job["operation"]["parameters"]["database_selection"]["list_occurrence_id"]
        assert receipt["projection"]["missing"] == []
    finally:
        store.close()


def test_native_failure_is_preserved_with_available_requested_bytes(tmp_path):
    store, capture = missing_capture(tmp_path, "metadata", native_returncode=7)
    try:
        receipt, _, _ = selected_failure(store, capture, tmp_path / "failure")
        projection = receipt["projection"]
        assert projection["status"]["native_state"] == "failed"
        assert projection["status"]["state"] == "partial"
        assert [r["role"] for r in projection["artifacts"]] == ["stdout", "stderr", "preparation_receipt"]
        assert any(r["code"] == "native_nonzero_exit" and r["native_returncode"] == 7
            for r in projection["failures"])
    finally:
        store.close()


@pytest.mark.parametrize("field", ["capture_sha256", "source_ref", "selector", "operational_failures",
    "qualification_failure", "projection", "extra"])
def test_frozen_failure_publication_rejects_tampering(tmp_path, field):
    store, capture = missing_capture(tmp_path, "metadata")
    try:
        receipt, chosen, problems = selected_failure(store, capture, tmp_path / "failure")
        changed = deepcopy(receipt)
        if field == "projection":
            changed[field]["artifacts"].pop()
        elif field == "selector":
            changed[field]["artifacts"] = []
        elif field == "operational_failures":
            changed[field] = []
        else:
            changed[field] = "changed"
        with pytest.raises(ContractError, match="original_projection_conflict"):
            failed.validate_capture_failure(store, capture=capture, selector=chosen,
                operational_failures=problems, publication=changed)
    finally:
        store.close()


def test_qualified_or_invalid_capture_cannot_use_missing_input_route(tmp_path):
    store, capture = controlled_capture(tmp_path)
    try:
        with pytest.raises(ContractError, match="missing_input_qualification_required"):
            selected_failure(store, capture, tmp_path / "qualified")
        invalid = deepcopy(capture)
        invalid["artifacts"][0]["artifact_ref"] = "artifact_" + "0" * 64
        with pytest.raises(ContractError):
            selected_failure(store, invalid, tmp_path / "invalid")
        full = worker.qualified_utility_context(capture)
        observed = worker.captured_utility_observations(capture)
        assert observed == {key: full[key] for key in ("operation", "native_outcome", "occurrences", "failures")}
    finally:
        store.close()


@pytest.mark.parametrize("kind", ["metadata", "entry_batch", "dbs_file", "dependency_list"])
def test_selected_failure_returns_and_replays_original_artifacts_without_extra_acquisition(tmp_path, monkeypatch, kind):
    store, capture = missing_capture(tmp_path, kind)
    monkeypatch.setattr(helpers, "vdb_capture", lambda *a, **k: (store, capture))
    h = helpers.selected_result_host(tmp_path, monkeypatch)
    try:
        first = helpers.selected_collect(h, 0)
        body = first["result"]
        assert body["prepared"] is None and not body["complete"]
        assert body["status"]["state"] == "partial"
        assert [r["role"] for r in body["artifacts"]] == ["stdout"]
        assert body["sequences"] == body["vdb_context"] == []
        assert h.worker_calls == [] and len(h.acquisitions) == len(h.observations) == 1
        directory = h.family.native_blast_utility_results._saved_directory(h.child.episode_id, body["operation_key"])
        originals = {str(p): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
        facts = h.family.native_blast_utility_results.facts(h.child)
        form = form_with_facts({}, h.schema, facts)
        reader = h.family.native_blast_utility_returns
        reader.validate_received_report(h.child, form, h.schema)
        h.journal.save("runtime_forms", {"episode_id": h.child.episode_id,
            "facts": canonical(facts), "form": canonical(form)})
        h.journal.save("runtime_actions", {"episode_id": h.parent.episode_id, "decision_index": 0,
            "action": canonical({"kind": "episode_child", "role": "results", "scope": h.scope,
                "assignment": h.assignment, "schema_json": canonical(h.schema),
                "purpose": h.child.request["report_contract"]["decision"]}), "result": None})
        h.journal.save("runtime_report_attempts", {"parent_episode_id": h.parent.episode_id,
            "decision_index": 0, "delivery_ref": "controlled-failure-return674", "child_episode_id": h.child.episode_id,
            "contract": canonical(h.child.request["report_contract"]), "form": canonical(form), "failure": None})
        admitted = reader.record_admission(h.parent, form, h.schema,
            f"{h.parent.run_id}:{h.parent.episode_id}:0:typed_form")
        assert admitted == body["record_refs"]
        h.receipts.receive(h.parent.episode_id, admitted, kind="child_form", source_index=0)
        reader.validate_received_report(h.parent, form, h.schema)
        assert h.family.native_blast_utility_results.retained_reference_access(h.parent,
            body["artifacts"][0]["artifact_ref"], "artifact") is True
        private = next(row["artifact_ref"] for row in capture["artifacts"] if row["direction"] == "database")
        assert private not in admitted
        assert h.family.native_blast_utility_results.retained_reference_access(h.parent, private, "artifact") is False
        monkeypatch.setattr(results, "prepare_native_blast_utility_result", helpers.forbidden)
        assert asyncio.run(h.family.native_blast_utility_results.execute(h.child, h.target,
            "execution.results.collect", {}, body["operation_key"])) == first
        assert originals == {str(p): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
        monkeypatch.setattr(results, "prepare_native_blast_utility_result", publication.prepare_native_blast_utility_result)
        second = helpers.selected_collect(h, 1)["result"]
        assert second["capture"] == body["capture"] and second["observation"] == body["observation"]
        assert second["artifacts"] == body["artifacts"] and second["prepared"] is None
        assert h.worker_calls == [] and len(h.acquisitions) == len(h.observations) == 1
        assert originals == {str(p): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
        known = list(h.receipts.known(h.child.episode_id))
        credit = h.family.native_blast_utility_results.credit_view(h.child,
            {"known_record_refs": known, "initial_known_record_refs": []})
        assert credit["credit"] == 2 and credit["new_acquired_record_count"] == 1
        assert h.family.native_blast_utility_results.completion(h.child) is None
        assert h.store.db.execute("SELECT count(*) FROM runtime_actions WHERE episode_id=?", (h.child.episode_id,)).fetchone()[0] == 2
        assert h.store.db.execute("SELECT count(*) FROM runtime_observations WHERE episode_id=?", (h.child.episode_id,)).fetchone()[0] == 0
    finally:
        store.close()
