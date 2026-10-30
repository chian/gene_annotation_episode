"""Store custody tests; authored controls are not native scientific measurements.

All cases run under packet446/run_bounded.py. The final parameterized case reads
separately pinned, genuinely executed C3 producer files from their original paths.
Fixture receipt labels do not establish original episode-action authority.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tracemalloc

import pytest

from gene_annotation_episode import native_file_capture
from gene_annotation_episode.state import Store
from gene_annotation_episode.native_chromatin_interaction_capture import (
    capture_chromatin_native_files, validate_chromatin_native_capture,
)
from gene_annotation_episode.native_chromatin_interaction_contracts import (
    ATTEMPT_DIRECTORY_NAME, POLICY, REQUIRED_DEPENDENCIES, REQUIRED_MODULES,
    TABLE_ROLES, canonical, digest, chromatin_output_files, requested_job_from_chromatin,
    validate_chromatin_run_plan, validate_chromatin_bundle, validate_chromatin_population_seal,
    _dependency_roots,
)
from gene_annotation_episode.native_chromatin_interaction_preparation import build_native_chromatin_worker_plan


FIXTURES = Path(os.environ["CHROMATIN_CAPTURE_FIXTURES"])
ATTEMPT = Path(os.environ["CHROMATIN_CAPTURE_ATTEMPT"])
WORKED = {r["example_key"]: r["record"] for r in json.loads((FIXTURES / "WORKED_RECORDS.json").read_text())["records"]}


def identity(raw, format_name):
    sha = hashlib.sha256(raw).hexdigest()
    return {"artifact_ref": "artifact_" + sha, "sha256": sha, "size_bytes": len(raw), "format": format_name}


def path_for(plan, key):
    return Path(plan["attempt_directory"]) / next(r["relative_path"] for r in plan["outputs"] if r["file_key"] == key)


def write_control(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))


def declared(spec, directory):
    path = directory / spec["relative_path"]
    result = {"relative_path": spec["relative_path"], "format": spec["format"],
        "state": "absent", "sha256": None, "size_bytes": None}
    if path.exists():
        actual = identity(path.read_bytes(), spec["format"])
        result.update(state="present", **{k: actual[k] for k in ("sha256", "size_bytes")})
    return result


def authored_fixture(directory, *, populations=2):
    """Authored opaque data/control bytes; never dispatched as native science."""
    source = directory / "never-open-original-bindings"
    request = deepcopy(WORKED["raw.request"])
    request["output_prefix"] = "selected/output"
    raw_inputs = {"contact": b"authored opaque contact fixture, not an HDF5 measurement\n",
        "elements": b"chrA\t0\t2\tE\nchrA\t20\t23\tP\nchrA\t30\t33\tQ\n"}
    bindings = []
    for role in ("contact", "elements"):
        request[role]["file"] = identity(raw_inputs[role], request[role]["format"])
        bindings.append({"input_key": request[role]["input_key"], "file": request[role]["file"], "path": str(source / role)})
    request["populations"] = [{**request["populations"][0], "population_key": f"p{i}"} for i in range(populations)]
    software = deepcopy(WORKED["handoff.plan"]["requested_job"]["native_chromatin_interactions"]["software"])
    software["implementation_files"] = [{"module": name, "sha256": digest({"authored_fixture": name})} for name in sorted(REQUIRED_MODULES)]
    software["dependencies"] = [{"distribution": name, "version": "authored-fixture-only", "package_root": "/fixture/packages/" + name,
        "files": [{"path": "/fixture/packages/" + name + "/__init__.py", "sha256": digest(name), "size_bytes": 1}]} for name in sorted(REQUIRED_DEPENDENCIES)]
    environment = deepcopy(WORKED["handoff.plan"]["requested_job"]["environment"])
    environment["PYTHONPATH"] = os.pathsep.join([software["module_root"], *_dependency_roots(software)])
    requested = requested_job_from_chromatin({"request": request, "software": software, "input_bindings": bindings}, environment=environment)
    run, episode, operation = "authored-capture-fixture", "original-local-child", "selected-operation"
    root = directory / ".episode-operations" / digest({"run": run, "episode": episode}) / digest(operation)
    plan = validate_chromatin_run_plan({"version": "chromatin_interaction_run_plan_v1", "identity": {
        "run_id": run, "episode_id": episode, "resource_id": "local", "execution_id": str(root / "native.json"),
        "operation_key": operation, "attempt_id": digest(operation), "requested_job_sha256": digest(requested),
        "assignment_sha256": digest({"authored_fixture": "no episode authority"})},
        "requested_job": requested, "attempt_directory": str(root / ATTEMPT_DIRECTORY_NAME), "policy": POLICY,
        "outputs": chromatin_output_files(request)})
    output = Path(plan["attempt_directory"])
    specs = {row["file_key"]: row for row in plan["outputs"]}
    extraction = deepcopy(WORKED["raw.extraction"])
    extraction["native_metadata"]["source_file"] = request["contact"]["file"]
    original_population, original_drafts = extraction["populations"][0], extraction["table_drafts"]
    extraction["populations"], extraction["table_drafts"] = [], []
    seals = []
    for ordinal, selected in enumerate(request["populations"]):
        key = selected["population_key"]
        population = deepcopy(original_population)
        population.update(population_key=key, selected_region=selected,
            data_table_keys=[f"{key}.{role}" for role in TABLE_ROLES])
        drafts = [{**deepcopy(d), "population_key": key, "table_key": f"{key}.{d['role']}"} for d in original_drafts]
        for draft in drafts:
            if draft["availability"] == "present":
                path = path_for(plan, draft["table_key"])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(("authored opaque table bytes:" + draft["table_key"] + "\n").encode())
        seal = {"version": "chromatin_interaction_population_seal_v1", "identity": plan["identity"],
            "request_sha256": digest(request), "native": {"metadata": extraction["native_metadata"], "chromosomes": extraction["chromosomes"]},
            "population": population, "tables": [{"draft": d, "declaration": declared(specs[d["table_key"]], output)} for d in drafts],
            "input_files": [r["file"] for r in bindings], "failures": []}
        seal = validate_chromatin_population_seal(seal, plan=plan, population=selected)
        write_control(path_for(plan, f"p{ordinal}.population_manifest"), seal)
        seals.append(seal)
        extraction["populations"].append(population)
        extraction["table_drafts"].extend(drafts)
    for key, raw in {"original_contact": raw_inputs["contact"], "original_elements": raw_inputs["elements"],
            "original_metadata": canonical(request["supplied_metadata"]), "stdout": b"", "stderr": b""}.items():
        path = path_for(plan, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    bundle = validate_chromatin_bundle({"version": "chromatin_interaction_native_bundle_v1", "identity": plan["identity"],
        "request": request, "software": software, "extraction": extraction, "elements": None, "metadata": None,
        "population_seals": [declared(specs[f"p{i}.population_manifest"], output) for i in range(populations)],
        "outputs": [{"specification": spec, "declaration": declared(spec, output)} for spec in plan["outputs"][:-1]],
        "failures": []}, plan=plan)
    write_control(path_for(plan, "bundle"), bundle)
    return plan, bundle, seals


def capture(store, plan, *, started=True):
    return capture_chromatin_native_files(store, original_plan=plan,
        source_action_receipt_ref="fixture:original-action", writer_closure_receipt_ref="fixture:qualified-writer-closure",
        driver_started=started)


def rows_by_key(value):
    return {r["specification"]["file_key"]: r for r in value["files"]}


def worker_plan(value, directory, selector=None):
    selected = deepcopy(selector or WORKED["raw.selector"])
    selected["population_keys"] = [p["population_key"] for p in value["original_plan"]["requested_job"]["native_chromatin_interactions"]["request"]["populations"]]
    return build_native_chromatin_worker_plan(directory=str(directory), selector=selected, **value)


def test_authored_complete_bundle_retains_all_bytes_and_actual_consumer(tmp_path):
    plan, bundle, _ = authored_fixture(tmp_path)
    original = deepcopy(plan)
    with Store(tmp_path / "store") as store:
        value = capture(store, plan)
        assert value["driver_state"] == "sealed_bundle" and value["failures"] == []
        assert json.loads(Path(value["bundle"]["path"]).read_bytes()) == bundle
        for row in value["files"]:
            assert row["declaration_source"] == "bundle"
            if row["retained"] is not None:
                actual = native_file_capture.retained_native_file(store, row["retained"]["file"])
                assert str(actual) == row["retained"]["path"]
                assert actual.read_bytes() == (Path(plan["attempt_directory"]) / row["specification"]["relative_path"]).read_bytes()
            else:
                assert row["capture"]["outcome"] == "declared_absent"
        rows = rows_by_key(value)
        assert rows["stdout"]["capture"]["outcome"] == "verified" and rows["stdout"]["retained"]["file"]["size_bytes"] == 0
        assert rows["stdout"]["retained"]["path"] == rows["stderr"]["retained"]["path"]
        assert worker_plan(value, tmp_path / "worker")["files"] == value["files"]
        path_for(plan, "stdout").write_bytes(b"later producer mutation")
        assert Path(rows["stdout"]["retained"]["path"]).read_bytes() == b""
    assert plan == original


def test_authored_declared_absent_does_not_open_later_extra_bytes(tmp_path):
    plan, _, _ = authored_fixture(tmp_path)
    path_for(plan, "p0.weights").write_bytes(b"unclaimed later file")
    with Store(tmp_path / "store") as store:
        value = capture(store, plan)
        row = rows_by_key(value)["p0.weights"]
        assert row["capture"]["outcome"] == "declared_absent" and row["retained"] is None


@pytest.mark.parametrize("change", ["same_size_wrong_digest", "wrong_size", "missing"])
def test_authored_changed_table_keeps_other_population_and_original_bundle(tmp_path, change):
    plan, bundle, _ = authored_fixture(tmp_path)
    original_bundle = path_for(plan, "bundle").read_bytes()
    table = path_for(plan, "p1.contacts")
    expected = table.read_bytes()
    if change == "missing":
        table.unlink()
    else:
        table.write_bytes(b"x" * len(expected) if change == "same_size_wrong_digest" else b"short")
    with Store(tmp_path / "store") as store:
        value = capture(store, plan)
        rows = rows_by_key(value)
        assert value["driver_state"] == "sealed_bundle"
        assert Path(value["bundle"]["path"]).read_bytes() == original_bundle
        assert rows["p0.contacts"]["capture"]["outcome"] == "verified"
        assert rows["p1.contacts"]["capture"]["outcome"] == ("unavailable" if change == "missing" else "digest_mismatch")
        if change != "missing":
            assert Path(rows["p1.contacts"]["retained"]["path"]).read_bytes() == table.read_bytes()
        assert any(p["population_key"] == "p1" and p["code"] == ("input_unavailable" if change == "missing" else "artifact_digest_mismatch") for p in value["failures"])
        assert worker_plan(value, tmp_path / "worker")["bundle"] == value["bundle"]
    assert json.loads(original_bundle) == bundle and path_for(plan, "bundle").read_bytes() == original_bundle


@pytest.mark.parametrize("invalid", [None, b"{", b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e9999}', b"{} ", b"\xff"])
def test_authored_invalid_bundle_preserves_earlier_seal_and_diagnostic_bytes(tmp_path, invalid):
    plan, _, _ = authored_fixture(tmp_path)
    bundle_path = path_for(plan, "bundle")
    bundle_path.unlink() if invalid is None else bundle_path.write_bytes(invalid)
    path_for(plan, "p1.population_manifest").unlink()
    with Store(tmp_path / "store") as store:
        value = capture(store, plan, started=None)
        rows = rows_by_key(value)
        assert value["driver_state"] == "unsealed_attempt" and value["bundle"] is None
        assert all(rows["p0." + role]["declaration_source"] == "population" for role in TABLE_ROLES)
        assert rows["p0.weights"]["capture"]["outcome"] == "declared_absent"
        assert rows["p1.contacts"]["declaration_source"] == "none" and rows["p1.contacts"]["capture"] is None
        assert Path(rows["p1.contacts"]["retained"]["path"]).read_bytes() == path_for(plan, "p1.contacts").read_bytes()
        if invalid is not None:
            located = next(p for p in value["failures"] if p["field_path"] == "/bundle")
            assert located["code"] == "malformed_native_header"
            assert store.get_artifact(located["artifact_ref"]) == invalid
        assert worker_plan(value, tmp_path / "worker")["driver_state"] == "unsealed_attempt"


def test_authored_noncanonical_valid_body_rejects_but_c3_newline_is_allowed(tmp_path):
    plan, bundle, _ = authored_fixture(tmp_path)
    path_for(plan, "bundle").write_bytes(canonical(bundle) + b"\n")
    with Store(tmp_path / "store") as store:
        assert capture(store, plan)["driver_state"] == "sealed_bundle"
        path_for(plan, "bundle").write_text(json.dumps(bundle, indent=2))
        value = capture(store, plan)
        assert value["driver_state"] == "unsealed_attempt"
        assert any(p["code"] == "malformed_native_header" and p["field_path"] == "/bundle" for p in value["failures"])


@pytest.mark.parametrize("change", ["identity", "input_file", "population", "normalization", "foreign_path"])
def test_authored_foreign_seal_cannot_authenticate_tables(tmp_path, change):
    plan, _, seals = authored_fixture(tmp_path)
    path_for(plan, "bundle").unlink()
    seal = deepcopy(seals[1])
    if change == "identity":
        seal["identity"]["operation_key"] = "foreign-action"
    elif change == "input_file":
        seal["input_files"][0] = identity(b"foreign source", "cooler_hdf5_v3")
    elif change == "population":
        seal["population"]["population_key"] = "p0"
    elif change == "normalization":
        seal["population"]["normalization"]["specification"] = {"kind": "precomputed_weighted", "weight_column": "weight", "convention": "multiplicative"}
    else:
        seal["tables"][0]["declaration"]["relative_path"] = "../foreign/bins.tsv"
    write_control(path_for(plan, "p1.population_manifest"), seal)
    with Store(tmp_path / "store") as store:
        value = capture(store, plan)
        rows = rows_by_key(value)
        assert rows["p0.contacts"]["declaration_source"] == "population"
        assert rows["p1.contacts"]["declaration_source"] == "none"
        control = rows["p1.population_manifest"]["retained"]
        assert any(p["code"] == "original_attempt_mismatch" and p["artifact_ref"] == control["file"]["artifact_ref"] for p in value["failures"])
        assert Path(control["path"]).read_bytes() == canonical(seal)


def test_authored_header_conflicts_remain_explicit_for_both_seals(tmp_path):
    plan, _, seals = authored_fixture(tmp_path)
    path_for(plan, "bundle").unlink()
    changed = deepcopy(seals[1])
    changed["native"]["metadata"]["attributes"].append({"path": "/@conflict", "dtype": "utf8", "shape": [], "value_state": "decoded", "value": "different"})
    write_control(path_for(plan, "p1.population_manifest"), changed)
    with Store(tmp_path / "store") as store:
        value = capture(store, plan)
        rows = rows_by_key(value)
        conflicts = [p for p in value["failures"] if p["field_path"].endswith("/native")]
        assert {p["population_key"] for p in conflicts} == {"p0", "p1"}
        assert all(p["code"] == "original_attempt_mismatch" and len(p["partial_artifact_refs"]) == 2 for p in conflicts)
        assert all(rows[f"p{i}.contacts"]["declaration_source"] == "population" for i in range(2))
        assert worker_plan(value, tmp_path / "worker")["failures"] == value["failures"]


def test_authored_bundle_source_mismatch_and_original_copy_mismatch(tmp_path, monkeypatch):
    plan, bundle, _ = authored_fixture(tmp_path)
    bundle["identity"]["run_id"] = "foreign-run"
    write_control(path_for(plan, "bundle"), bundle)
    path_for(plan, "original_contact").write_bytes(b"changed copy")
    allowed = {r["relative_path"] for r in plan["outputs"]}
    original_capture = native_file_capture.capture_native_file
    def only_fixed(store, **arguments):
        assert arguments["directory"] == plan["attempt_directory"] and arguments["relative_path"] in allowed
        return original_capture(store, **arguments)
    monkeypatch.setattr(native_file_capture, "capture_native_file", only_fixed)
    with Store(tmp_path / "store") as store:
        value = capture(store, plan)
        assert value["driver_state"] == "unsealed_attempt"
        assert any(p["code"] == "original_attempt_mismatch" and p["field_path"] == "/bundle" for p in value["failures"])
        problem = next(p for p in value["failures"] if p["code"] == "input_digest_mismatch")
        assert problem["input_key"] == "contact0" and store.get_artifact(problem["artifact_ref"]) == b"changed copy"
        assert not Path(plan["requested_job"]["native_chromatin_interactions"]["input_bindings"][0]["path"]).exists()


def test_false_not_started_opens_nothing_and_missing_is_still_unknown(tmp_path, monkeypatch):
    plan, _, _ = authored_fixture(tmp_path)
    with Store(tmp_path / "store") as store:
        with monkeypatch.context() as patch:
            patch.setattr(native_file_capture, "capture_native_file", lambda *a, **k: pytest.fail("producer opened"))
            patch.setattr(Path, "open", lambda *a, **k: pytest.fail("filesystem read"))
            patch.setattr(os, "open", lambda *a, **k: pytest.fail("filesystem read"))
            value = capture(store, plan, started=False)
            assert value["driver_state"] == "not_started" and len(value["failures"]) == len(plan["outputs"])
            assert all(row["capture"] is None and row["retained"] is None for row in value["files"])
            assert validate_chromatin_native_capture(value, original_plan=plan) == value
        shutil.rmtree(plan["attempt_directory"])
        unknown = capture(store, plan, started=None)
        assert unknown["driver_state"] == "unsealed_attempt" and unknown["bundle"] is None


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_producer_symlinks_never_followed(tmp_path, kind):
    plan, _, _ = authored_fixture(tmp_path)
    original = path_for(plan, "p1.contacts")
    outside = tmp_path / "outside"
    if kind == "file":
        outside.write_bytes(original.read_bytes())
        original.unlink()
        original.symlink_to(outside)
    else:
        original.parent.rename(outside)
        original.parent.symlink_to(outside, target_is_directory=True)
    with Store(tmp_path / "store") as store:
        rows = rows_by_key(capture(store, plan))
        assert rows["p1.contacts"]["capture"]["outcome"] == "unavailable"
        assert rows["p1.contacts"]["retained"] is None and rows["p0.contacts"]["capture"]["outcome"] == "verified"


def test_original_plan_path_escape_rejected_before_any_access(tmp_path, monkeypatch):
    plan, _, _ = authored_fixture(tmp_path)
    plan["outputs"][0]["relative_path"] = "../outside"
    monkeypatch.setattr(native_file_capture, "capture_native_file", lambda *a, **k: pytest.fail("capture before validation"))
    with pytest.raises(ValueError):
        capture(None, plan)


def test_actual_store_write_failure_propagates_shared_storage_error(tmp_path):
    plan, _, _ = authored_fixture(tmp_path)
    with Store(tmp_path / "store") as store:
        store.db.execute("PRAGMA query_only=ON")
        with pytest.raises(native_file_capture.NativeFileCaptureError) as problem:
            capture(store, plan)
        assert problem.value.code == "retained_artifact_unavailable"


def test_large_authored_log_captured_complete_with_bounded_memory(tmp_path):
    plan, bundle, _ = authored_fixture(tmp_path)
    path = path_for(plan, "stdout")
    block = bytes(range(256)) * 4096
    hasher = hashlib.sha256()
    with path.open("wb") as stream:
        for _ in range(64):
            stream.write(block)
            hasher.update(block)
    declaration = next(r["declaration"] for r in bundle["outputs"] if r["specification"]["file_key"] == "stdout")
    declaration.update(sha256=hasher.hexdigest(), size_bytes=64 * len(block))
    write_control(path_for(plan, "bundle"), bundle)
    with Store(tmp_path / "store") as store:
        tracemalloc.start()
        value = capture(store, plan)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        row = rows_by_key(value)["stdout"]
        assert row["capture"]["outcome"] == "verified" and row["retained"]["file"]["size_bytes"] == 67108864
        assert row["retained"]["file"]["sha256"] == hasher.hexdigest()
        assert native_file_capture.retained_native_file(store, row["retained"]["file"]).stat().st_size == 67108864
        assert peak < 16 * 1024 * 1024, peak
        (ATTEMPT / "large-file-memory.json").write_text(json.dumps({"fixture_kind": "authored_log", "retained_bytes": 67108864,
            "sha256": hasher.hexdigest(), "tracemalloc_peak_bytes": peak}) + "\n")


def test_pure_validator_detached_record_and_cross_field_rejections(tmp_path, monkeypatch):
    plan, _, _ = authored_fixture(tmp_path)
    path_for(plan, "p1.contacts").unlink()
    with Store(tmp_path / "store") as store:
        value = capture(store, plan)
    def row(v, key="p0.contacts"):
        return next(r for r in v["files"] if r["specification"]["file_key"] == key)
    changes = [lambda v: v.update(extra=True), lambda v: v["original_plan"]["identity"].update(assignment_sha256="0" * 64),
        lambda v: v["files"].reverse(), lambda v: v.update(driver_state="unsealed_attempt"),
        lambda v: row(v, "stdout").update(declaration_source="population"),
        lambda v: row(v)["capture"]["observed"].update(artifact_ref="artifact_" + "0" * 64),
        lambda v: row(v)["capture"]["observed"].update(size_bytes=True),
        lambda v: row(v)["capture"]["declared"].update(size_bytes=0),
        lambda v: row(v)["capture"].update(outcome="declared_absent"), lambda v: row(v).update(retained=None),
        lambda v: row(v)["retained"].update(path="/arbitrary/file"),
        lambda v: row(v)["retained"].update(path=v["bundle"]["path"]),
        lambda v: v["failures"][0].update(population_key="foreign"),
        lambda v: v["failures"][0].update(field_path="/files/999"),
        lambda v: v["failures"][0].update(field_path="/files/01"),
        lambda v: v["failures"][0].update(input_key="contact0"),
        lambda v: v["failures"][0].update(pair_key="invented-pair")]
    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", lambda *a, **k: pytest.fail("pure validator opened a file"))
        patch.setattr(os, "open", lambda *a, **k: pytest.fail("pure validator opened a path"))
        detached = validate_chromatin_native_capture(value, original_plan=plan)
        assert detached == value and detached is not value and detached["original_plan"] is not value["original_plan"]
        for change in changes:
            bad = deepcopy(value)
            change(bad)
            with pytest.raises(ValueError):
                validate_chromatin_native_capture(bad, original_plan=plan)


@pytest.mark.parametrize("case", ["raw", "weighted", "insulation"])
def test_genuine_executed_c3_bytes_feed_actual_worker_without_original_input_access(tmp_path, monkeypatch, case):
    """Native serialized synthetic source data, separately from authored controls."""
    import h5py
    from gene_annotation_episode.chromatin_interaction_result_worker import run_chromatin_result_worker
    evidence = json.loads((FIXTURES / "NATIVE_INPUTS.json").read_text())[case]
    plan_bytes = Path(evidence["plan"]["path"]).read_bytes()
    assert hashlib.sha256(plan_bytes).hexdigest() == evidence["plan"]["sha256"]
    plan = json.loads(plan_bytes)
    for pin in evidence["producer_pins"]:
        assert hashlib.sha256(Path(pin["path"]).read_bytes()).hexdigest() == pin["sha256"]
    assert evidence["terminal"] and evidence["quiescent"] and evidence["native_returncode"] == 0
    original_open, original_os_open = Path.open, os.open
    forbidden = {row["path"] for row in plan["requested_job"]["native_chromatin_interactions"]["input_bindings"]}
    producer = Path(plan["attempt_directory"])
    protect_producer = False
    def guarded_os_open(path, flags, mode=0o777, *, dir_fd=None):
        selected = Path(os.fsdecode(path))
        if not selected.is_absolute():
            base = Path(os.readlink(f"/proc/self/fd/{dir_fd}")) if dir_fd is not None else Path.cwd()
            selected = base / selected
        assert str(selected) not in forbidden, "original binding reopened through descriptor"
        if protect_producer:
            assert selected != producer and producer not in selected.parents, "producer reopened through descriptor"
        return original_os_open(path, flags, mode, dir_fd=dir_fd)
    def guarded_open(path, *arguments, **keywords):
        assert str(path) not in forbidden, "original binding reopened"
        return original_open(path, *arguments, **keywords)
    monkeypatch.setattr(Path, "open", guarded_open)
    monkeypatch.setattr(os, "open", guarded_os_open)
    monkeypatch.setattr(h5py, "File", lambda *a, **k: pytest.fail("original HDF5 parsed during capture or retained work"))
    with Store(tmp_path / "store") as store:
        value = capture(store, plan)
        assert value["driver_state"] == "sealed_bundle" and value["failures"] == []
        for row in value["files"]:
            if row["retained"] is not None:
                assert row["capture"]["outcome"] == "verified"
                assert native_file_capture.retained_native_file(store, row["retained"]["file"]).read_bytes() == (
                    Path(plan["attempt_directory"]) / row["specification"]["relative_path"]).read_bytes()
        worker = worker_plan(value, tmp_path / "worker", WORKED[case + ".selector"])
        # Once captured, the worker may open retained bytes only. This guard
        # covers producer outputs as well as original contact/BED bindings.
        protect_producer = True
        def retained_only(path, *arguments, **keywords):
            assert producer not in Path(path).parents and str(path) not in forbidden, "producer reopened by retained worker"
            return original_open(path, *arguments, **keywords)
        monkeypatch.setattr(Path, "open", retained_only)
        result = run_chromatin_result_worker(worker)
        assert result["state"] == "produced", result
        projection = json.loads((tmp_path / "worker/projection.json").read_text())
        expected = WORKED[case + ".projection"]
        assert len(projection["rows"]) == len(expected["rows"])
        for actual, wanted in zip(projection["rows"], expected["rows"]):
            for key, measure in actual["fields"].items():
                assert set(measure) == set(wanted["fields"][key])
                for field, expected_value in wanted["fields"][key].items():
                    assert measure[field] == (pytest.approx(expected_value) if type(expected_value) in (float, int) else expected_value)
        (ATTEMPT / (case + "-capture.json")).write_bytes(canonical(value))
        (ATTEMPT / (case + "-projection.json")).write_bytes(canonical(projection))
