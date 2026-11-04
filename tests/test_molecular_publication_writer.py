"""Shared writer regression using authentic268 saved scientific bytes only.

Prepared worker/control objects are explicitly engineered publisher operands.
No new selected producer/action authority, fit, forward calculation or native
job is claimed by re-retaining those existing values in a fresh test Store.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode import molecular_measurement_tools as ordinary
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import source_tool_grading_entries
from gene_annotation_episode.tools import ToolRegistry


RETAINED = Path(__file__).resolve().parents[1] / (
    "verification/tool_graders_hmmer_map_verification_2026-10-28_529/"
    "check268_itc_ordinary_tool_delivery/temporary/pytest/test_registered_itc_fit_same_e0/store")
SOURCE = "source_4f6a6927cc1b155c54974cb7"
NATIVE = "aa029c30f55e2f408c3bcf85297e2e0d96232e900f31454ea17479bcbc68ccd4"
CONTROL = "d45f9bf127d816428197bb79e8a134887fecd481dd583fbd8b8228d24559eb14"
INPUT = "8127b46a65f7cfea49238e758fc1647c1487f2c2e8c60c298a87240c1d423108"


def _forbidden(*args, **kwargs):
    raise AssertionError("retained publication regression attempted scientific production")


def _original_bytes():
    database = RETAINED / "state.sqlite3"
    assert hashlib.sha256(database.read_bytes()).hexdigest() == "0afedbd29725565d1932a153bc49f7f6d76dd9c0d9719f95c4cf41b34de80e30"
    connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        row = connection.execute("SELECT data FROM records WHERE id=? AND record_type='source'", (SOURCE,)).fetchone()
    finally:
        connection.close()
    source = json.loads(row[0])
    bodies = {}
    for digest in (NATIVE, CONTROL, INPUT):
        raw = (RETAINED / "artifacts" / digest[:2] / digest).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest
        bodies[digest] = raw
    assert source["artifact_ref"] == "artifact_" + NATIVE and source["request_ref"] == "artifact_" + CONTROL
    return source, bodies


def _guards(monkeypatch):
    from gene_annotation_episode import itc_binding_fit, itc_binding_measurements, native_lifecycle
    monkeypatch.setattr(itc_binding_fit, "fit_itc_binding_measurements", _forbidden)
    monkeypatch.setattr(itc_binding_measurements, "calculate_itc_binding_components", _forbidden)
    monkeypatch.setattr(itc_binding_measurements, "predict_itc_binding_heats", _forbidden)
    monkeypatch.setattr(ordinary, "run_itc_tool_request", _forbidden)
    monkeypatch.setattr(ordinary, "run_owned_molecular_worker", _forbidden)
    monkeypatch.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
    for name in ("prepare_job", "resume_start", "collect", "wait_job"):
        monkeypatch.setattr(native_lifecycle, name, _forbidden)


@contextmanager
def _prepared(tmp_path, monkeypatch):
    original, bodies = _original_bytes()
    _guards(monkeypatch)
    control = json.loads(bodies[CONTROL]); stored = ordinary._validate_result(json.loads(bodies[NATIVE]))
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="MKWAA", molecule="protein")
        assert store.artifact(bodies[INPUT], "application/json") == "artifact_" + INPUT
        witness = control["request"]["received_input"]["witness"]["record"]
        parent = store.put("source", {key: value for key, value in witness.items()
            if key not in {"id", "record_type", "origin"}}, origin=witness["origin"])
        assert canonical(parent) == canonical(witness)
        tools = ToolRegistry(store)
        directory = tmp_path / "engineering-worker-output"; directory.mkdir()
        output = directory / "worker-result.json"; output.write_bytes(bodies[NATIVE])
        (directory / "execution-selection.json").write_text(canonical(control["execution_selection"]))
        (directory / "native-handle.json").write_text(canonical(control["native_handle"]))
        work = SimpleNamespace(output_path=output, metadata=deepcopy(control["execution"]))
        prepared = dict(work=work, stored=deepcopy(stored), item=deepcopy(control["request"]["received_input"]),
            request=deepcopy(control["request"]), operational_failure=None)
        class OriginalPublicationTime:
            @staticmethod
            def now(timezone):
                return datetime.fromisoformat(original["retrieved_at"]).astimezone(timezone)
        # Freeze only this engineering publication time to compare the old
        # Source identity; no historical producer/receipt is synthesized.
        monkeypatch.setattr(ordinary, "datetime", OriginalPublicationTime)
        token = tools._publications.set([])
        try:
            yield SimpleNamespace(store=store, tools=tools, prepared=prepared, original=original,
                bodies=bodies, control=control, stored=stored)
        finally:
            tools._publications.reset(token)


@pytest.mark.parametrize("entry", ["common_writer", "itc_wrapper"])
def test_retained_itc_publication_preserves_native_grade_controls_source_and_legacy_triple(tmp_path, monkeypatch, entry):
    with _prepared(tmp_path, monkeypatch) as case:
        before = canonical(case.prepared["stored"])
        with case.store.transaction():
            if entry == "common_writer":
                publication = ordinary.retain_molecular_publication(case.tools, case.prepared, tool_name=ordinary.ITC_TOOL)
                source = publication["source"]
                references = [source["id"], publication["native_artifact_ref"], publication["grading_ref"]]
                projection = ordinary.project_itc_tool_result(case.stored, selection=case.control["request"]["arguments"],
                    source_ref=source["id"], artifact_ref=publication["native_artifact_ref"], grading_ref=publication["grading_ref"])
            else:
                projection, references = ordinary.publish_itc_work(case.tools, case.control["request"]["arguments"], case.prepared)
                source = case.store.get(projection["source_ref"])
        assert canonical(source) == canonical(case.original)
        assert references == [SOURCE, "artifact_" + NATIVE, case.original["auxiliary_artifact_refs"][0]]
        assert case.store.get_artifact(source["artifact_ref"]) == case.bodies[NATIVE]
        assert case.store.get_artifact(source["request_ref"]) == case.bodies[CONTROL]
        assert source["parent_source_refs"] == case.original["parent_source_refs"] and "operand_refs" not in source
        grade, = source_tool_grading_entries(case.store, source["id"])
        assert grade["artifact_ref"] == references[2]
        assert canonical(grade["grading"]) == canonical(dict(sheet=case.stored["sheet"], scores=case.stored["components"]))
        assert projection["parameters"]["kd"]["value"] == case.stored["components"]["parameter_values"]["kd"]["value"] == 2.999999999999987e-6
        assert projection["fit_call_count"] == 1 and projection["fit_call_state"] == "returned"
        assert projection["source_ref"] == SOURCE and projection["native_file"]["artifact_ref"] == references[1]
        assert projection["grading_ref"] == references[2]
        assert canonical(case.prepared["stored"]) == before
        assert case.tools._written == [SOURCE]


@pytest.mark.parametrize("changed", ["captured_output", "validated_memory"])
def test_shared_writer_rejects_capture_stored_mismatch_before_grading_or_source(tmp_path, monkeypatch, changed):
    with _prepared(tmp_path, monkeypatch) as case:
        from gene_annotation_episode import tool_grading_artifacts
        if changed == "captured_output":
            altered = deepcopy(case.stored)
            altered["components"]["parameter_values"]["kd"]["value"] = 777.25
            case.prepared["work"].output_path.write_text(canonical(altered))
        else:
            case.prepared["stored"]["components"]["parameter_values"]["kd"]["value"] = 777.25
            ordinary._validate_result(case.prepared["stored"])  # Shape-admitted data is still not the captured output.
        original_sources = canonical(case.store.list("source"))
        monkeypatch.setattr(case.tools, "_put", _forbidden)
        monkeypatch.setattr(tool_grading_artifacts, "retain_tool_grading", _forbidden)
        with pytest.raises(ContractError, match="ordinary_itc_native_capture_conflict"):
            with case.store.transaction():
                ordinary.retain_molecular_publication(case.tools, case.prepared, tool_name=ordinary.ITC_TOOL)
        assert canonical(case.store.list("source")) == original_sources
        assert case.tools._written == []
