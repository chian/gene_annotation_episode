"""Actual bounded numerical/publication workers over retained native bytes.

The relocated original execution envelope is a labeled synthetic fixture;
capture, file retention, subprocess grading and projection are real operations.
These checks do not claim episode commissioning or controller integration.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode import native_hmmer_preparation_acquisition as acquisition
from gene_annotation_episode import native_hmmer_preparation_result_publication as publication
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.state import Store
from test_native_hmmer_preparation_result_worker import CASES, capture_native


POLICY = LocalJobPolicy(20 * 1024 ** 3, 4 * 1024 ** 3)


def prepare(store, tmp_path, monkeypatch, program="hmmemit", mode="consensus_simple"):
    root, _, bundle, target, capture = capture_native(store, tmp_path, monkeypatch, program, mode)
    shutil.rmtree(root.parent)
    monkeypatch.setattr(acquisition, "local_hmmer_preparation_plan", lambda *a: pytest.fail("reopened native reservation"))
    prepared = publication.prepare_native_hmmer_preparation_grading(store,
        target=target, capture=capture, capture_directory=tmp_path / "capture",
        directory=tmp_path / "grading", policy=POLICY)
    assert prepared["graded"], prepared
    source = acquisition.publish_original_source(store, bundle=bundle, capture=capture, prepared=prepared)
    return bundle, target, capture, prepared, source


def selector(*, artifacts=(), quantities=(), rows=None):
    return {"version": "native_hmmer_preparation_result_selector_v1",
        "acquisition": "complete_bound_bundle", "artifacts": list(artifacts),
        "projection": {"collection": "calculations", "rows": rows or {"offset": 0, "limit": 1},
            "quantities": list(quantities), "checks": []} if quantities else None}


@pytest.mark.parametrize("program,mode", CASES)
def test_all26_modes_retain_grade_and_publish_only_requested_artifact(tmp_path, monkeypatch, program, mode):
    with Store(tmp_path / "store") as store:
        bundle, target, capture, prepared, source = prepare(store, tmp_path, monkeypatch, program, mode)
        selected = next((r for r in bundle["artifacts"] if r["role"] not in {"stdout", "stderr"}), bundle["artifacts"][0])
        choice = selector(artifacts=[{"direction": "output", "role": selected["role"], "ordinal": 0}])
        full_get = store.get_artifact
        numerical = {prepared[k] for k in ("grading_artifact_ref", "sheet_artifact_ref", "calculations_artifact_ref")}
        def no_full_sheet(reference):
            assert reference not in numerical, "host hydrated full numerical data"
            return full_get(reference)
        monkeypatch.setattr(store, "get_artifact", no_full_sheet)
        result = publication.publish_selected_preparation_result(store, source_ref=source,
            prepared=prepared, selector=choice, directory=tmp_path / "projection", policy=POLICY)
        assert result["rows"] == [] and result["population"]["total_records"] == 0
        assert len(result["artifacts"]) == 1
        artifact = result["artifacts"][0]
        assert artifact["sha256"] == selected["sha256"] and artifact["size_bytes"] == selected["size_bytes"]
        assert result["record_refs"] == [source, artifact["artifact_ref"]]
        assert not numerical.intersection(result["record_refs"])
        monkeypatch.setattr(publication, "run_local_job", lambda *a, **kw: pytest.fail("replay started worker"))
        assert publication.prepare_native_hmmer_preparation_grading(store, target=target, capture=capture,
            capture_directory=tmp_path / "capture", directory=tmp_path / "grading", policy=POLICY) == prepared
        assert publication.validate_publication(store, result, source_ref=source, prepared=prepared,
            selector=choice, directory=tmp_path / "projection", policy=POLICY) == result


@pytest.mark.parametrize("program,mode,path,expected", [
    ("hmmemit", "consensus_simple", "length", 12),
    ("makehmmerdb", "build", "components.source_symbol_total", 28),
    ("makehmmerdb", "build", "components.actual_database_bytes", 314),
])
def test_requested_native_numerical_value_crosses_saved_publication(tmp_path, monkeypatch, program, mode, path, expected):
    with Store(tmp_path / "store") as store:
        _, _, _, prepared, source = prepare(store, tmp_path, monkeypatch, program, mode)
        choice = selector(quantities=[path])
        result = publication.publish_selected_preparation_result(store, source_ref=source,
            prepared=prepared, selector=choice, directory=tmp_path / "projection", policy=POLICY)
        assert len(result["rows"]) == 1
        assert result["rows"][0]["quantities"][0]["value"] == expected
        assert result["rows"][0]["quantities"][0]["state"] == "present"
        # The selected scalar carries only the original files needed to
        # substantiate it, even though no file was explicitly requested.
        expected_roles = {("output", "generated_sequences")} if program == "hmmemit" else (
            {("input", "sequences")} if path.endswith("source_symbol_total")
            else {("output", "fm_database")})
        assert {(r["direction"], r["role"]) for r in result["artifacts"]} == expected_roles
        assert result["population"]["requested_artifact_count"] == 0
        assert result["population"]["returned_artifact_count"] == len(expected_roles)
        assert len(result["rows"][0]["quantities"]) == 1


def test_projection_rejects_changed_selection_and_prepared_identity(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        bundle, _, _, prepared, source = prepare(store, tmp_path, monkeypatch)
        choice = selector(quantities=["length"])
        result = publication.publish_selected_preparation_result(store, source_ref=source,
            prepared=prepared, selector=choice, directory=tmp_path / "projection", policy=POLICY)
        changed = deepcopy(choice)
        changed["projection"]["rows"]["offset"] = 1
        with pytest.raises(ValueError, match="identity_conflict"):
            publication.validate_publication(store, result, source_ref=source, prepared=prepared,
                selector=changed, directory=tmp_path / "projection", policy=POLICY)
        changed = deepcopy(prepared)
        changed["occurrences"][0]["ordinal"] = 9
        with pytest.raises(ValueError, match="identity_conflict"):
            publication.validate_prepared_grading(store, changed, bundle=bundle)


def test_preparation_requires_existing_capture_and_does_not_acquire(tmp_path, monkeypatch):
    monkeypatch.setattr(publication, "capture_local_bundle", lambda *a, **kw: pytest.fail("first capture hidden in grading"))
    with Store(tmp_path / "store") as store:
        prepared = publication.prepare_native_hmmer_preparation_grading(store,
            target={}, capture={}, capture_directory=tmp_path / "capture",
            directory=tmp_path / "grading", policy=POLICY)
        assert not prepared["graded"] and prepared["source_grading_artifact_ref"] is None
        assert prepared["failures"][0]["code"].endswith("completed_capture_required")


def test_captured_artifact_survives_unavailable_grade_worker(tmp_path, monkeypatch, verified_control_runtime):
    """An injected admission refusal preserves the real prepared phase, not a failed grade.

    The native capture fixture's relocated custody is synthetic, as declared at
    module scope. The durable worker preparation is real; no worker is started.
    """
    from gene_annotation_episode.acquisition import AcquisitionError
    with Store(tmp_path / "store") as store:
        root, _, _, target, capture = capture_native(store, tmp_path, monkeypatch)
        shutil.rmtree(root.parent)
        _copy_control_runtime(tmp_path, verified_control_runtime)
        calls = []
        def busy(handle, **kwargs):
            calls.append(handle.read()["unit"])
            raise AcquisitionError("local_resource_busy", phase="local_admission",
                operational={"retryable": True, "retry_same_prepared_job": True})
        monkeypatch.setattr(publication.native, "resume_start", busy)
        def counts():
            return store.count("source"), store.db.execute("SELECT count(*) FROM artifacts").fetchone()[0], store.count("observation")
        baseline = counts()
        def selected_grade():
            return publication.prepare_native_hmmer_preparation_grading(store,
                target=target, capture=capture, capture_directory=tmp_path / "capture",
                directory=tmp_path / "grading", policy=POLICY)
        with pytest.raises(publication.HmmerPreparationWorkerPending) as first:
            selected_grade()
        directory = tmp_path / "grading/native-hmmer-preparation-grading"
        handle = publication.native.NativeJobHandle(first.value.handle_path)
        original = handle.read()
        assert original["stage"] == "prepared" and original["started_at"] is None
        assert first.value.failure["operational"]["retry_same_prepared_job"] is True
        assert not any((directory / name).exists() for name in (
            "prepared.json", "grading-receipt.json", "worker-result.json", "projection-failure.json"))
        assert store.get_artifact(capture["bundle_artifact_ref"])
        assert counts() == baseline
        def no_reprepare(*args, **kwargs):
            pytest.fail("pending phase prepared a replacement native handle")
        monkeypatch.setattr(publication.native, "prepare_job", no_reprepare)
        with pytest.raises(publication.HmmerPreparationWorkerPending) as second:
            selected_grade()
        assert second.value.handle_path == first.value.handle_path
        assert handle.read() == original and calls == [original["unit"], original["unit"]]
        assert not (directory / "prepared.json").exists()
        assert counts() == baseline


def test_original_saved_alimask_publication_keeps_absent_context_and_frozen_numbers(tmp_path, monkeypatch):
    """Reuse the actual 277 closed publication; never rerun its native job/grade."""
    import hashlib
    from gene_annotation_episode import native_hmmer_preparation_result_worker as worker
    from gene_annotation_episode import hmmer_alignment_preparation_calculations as calculations
    root = Path(__file__).resolve().parents[1]
    original = root / "verification/tool_graders_hmmer_preparation_workflow_2026-10-26_277/check009/temporary/test_all_native_modes_through_3"
    prepared_path, = original.rglob("prepared.json")
    projection_path, = original.rglob("native-hmmer-preparation-projection/publication.json")
    prepared_bytes, projection_bytes = prepared_path.read_bytes(), projection_path.read_bytes()
    assert hashlib.sha256(prepared_bytes).hexdigest() == "85824c53c759e26aacebed9d8ad295578f3fbf3b9b208ee985d633678441652c"
    assert hashlib.sha256(projection_bytes).hexdigest() == "43ce501621049bc2c2c3b838fb958fab91a0b1acaa835eb6ff53d9d9714d94b0"
    shutil.copytree(original / "state", tmp_path / "state")
    # Verification snapshots are immutable. Store needs a writable copied DB
    # for its normal WAL initialization; keep the historical source untouched.
    for copied in [tmp_path / "state", *(tmp_path / "state").rglob("*")]:
        copied.chmod(0o755 if copied.is_dir() else 0o644)
    shutil.copytree(projection_path.parent, tmp_path / "projection/native-hmmer-preparation-projection")
    prepared = json.loads(prepared_bytes)
    selected = json.loads(projection_bytes)
    intent = json.loads((projection_path.parent / "intent.json").read_bytes())
    def forbidden(*args, **kwargs):
        raise AssertionError("old publication replay performed native work, acquisition or numerical grading")
    for module, name in ((publication, "run_local_job"), (publication, "_prepare_worker"),
                         (publication, "_collect_worker"), (publication, "capture_local_bundle"),
                         (worker, "_grade"), (calculations, "reconstruct_alimask_model_map")):
        monkeypatch.setattr(module, name, forbidden)
    with Store(tmp_path / "state") as store:
        stable = publication._stable(store, prepared)
        assert stable["effective_metadata"] == {}
        frozen = store.get_artifact(prepared["grading_artifact_ref"])
        assert json.loads(frozen)["metadata"] == {}
        bundle = json.loads(store.get_artifact(prepared["bundle_artifact_ref"]))
        assert publication.validate_prepared_grading(store, prepared, bundle=bundle) == prepared
        assert publication.validate_publication(store, selected, source_ref=intent["source_ref"],
            prepared=prepared, selector=intent["selector"], directory=tmp_path / "projection", policy=POLICY) == selected
        assert store.get_artifact(prepared["grading_artifact_ref"]) == frozen
        assert publication._stable(store, prepared)["effective_metadata"] == {}
        assert [q["value"] for q in selected["rows"][0]["quantities"]] == [3, 14, 12, 1, 1, None]
    assert prepared_path.read_bytes() == prepared_bytes and projection_path.read_bytes() == projection_bytes


def test_new_alimask_context_is_bound_in_publication_and_checked_on_replay(tmp_path, monkeypatch):
    from gene_annotation_episode import native_hmmer_preparation_result_worker as worker
    with Store(tmp_path / "store") as store:
        bundle, _, _, prepared, source = prepare(store, tmp_path, monkeypatch, "alimask", "alignment_to_model")
        stable = publication._stable(store, prepared)
        context = stable["effective_metadata"]["map_reconstruction_context"]
        alignment = next(r for r in prepared["occurrences"] if (r["direction"], r["role"], r["ordinal"]) == ("input", "alignment", 0))
        assert context["source_occurrence_id"] == alignment["occurrence_id"]
        assert context["source_sha256"] == alignment["sha256"]
        assert context["producer"]["executable_sha256"] == bundle["software"]["actual_sha256"]
        assert context["effective_pb_config"]["seed"] == 42
        grading = json.loads(store.get_artifact(prepared["grading_artifact_ref"]))
        assert grading["metadata"]["map_reconstruction_context"] == context
        assert grading["sheet"]["input_records"][0]["map_reconstruction_context"] == context
        choice = selector(quantities=["components.mapped_model_position_count"])
        result = publication.publish_selected_preparation_result(store, source_ref=source,
            prepared=prepared, selector=choice, directory=tmp_path / "projection", policy=POLICY)
        frozen = store.get_artifact(prepared["grading_artifact_ref"])
        monkeypatch.setattr(publication, "run_local_job", lambda *a, **kw: pytest.fail("replay started worker"))
        monkeypatch.setattr(worker, "_grade", lambda *a, **kw: pytest.fail("replay recomputed grade"))
        assert publication.validate_publication(store, result, source_ref=source, prepared=prepared,
            selector=choice, directory=tmp_path / "projection", policy=POLICY) == result
        altered = deepcopy(stable)
        altered["effective_metadata"]["map_reconstruction_context"]["source_sha256"] = "0" * 64
        changed = deepcopy(prepared)
        changed["source_grading_artifact_ref"] = publication.retain_tool_grading(store,
            provider="episode.execution_result", native_artifact_ref=prepared["bundle_artifact_ref"], grading=altered)
        with pytest.raises(ValueError, match="prepared_grading_custody_conflict"):
            publication.validate_prepared_grading(store, changed, bundle=bundle)
        assert store.get_artifact(prepared["grading_artifact_ref"]) == frozen


@pytest.fixture(scope="module")
def verified_control_runtime(tmp_path_factory):
    """Provision one real immutable driver closure for metadata controls only."""
    root = tmp_path_factory.mktemp("verified-hmmer-control-runtime")
    intent = {"policy": POLICY.to_dict(), "engineering_control": "runtime_provisioning_only"}
    directory, _ = publication._begin(root / "grading", "native-hmmer-preparation-grading", intent, "prepared.json")
    retained = publication._worker_runtime(directory, POLICY)
    publication._runtime_files(retained["driver_runtime"])
    return retained


def _copy_control_runtime(tmp_path, retained):
    """Copy verified source bytes once per owned phase, without repeated provisioning.

    The interpreter, dependencies and their literal exclusions keep their actual
    selected paths. Only the copied source's truthful deployment path changes;
    this is no Source/producer/input/Store reconstruction or path override.
    """
    import hashlib
    source = Path(retained["driver_runtime"]["module_root"])
    expected = {path.relative_to(source): {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size} for path in source.rglob("*") if path.is_file()}
    publication.check_scratch_budget(tmp_path, POLICY,
        additional_bytes=sum(row["size_bytes"] for row in expected.values()))
    shared = tmp_path / "native-hmmer-preparation-worker-runtime"
    shared.mkdir()
    copied = shared / "source"
    shutil.copytree(source, copied)
    assert {path.relative_to(copied) for path in copied.rglob("*") if path.is_file()} == set(expected)
    for relative, row in expected.items():
        path = copied / relative
        assert path.stat().st_size == row["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
    selected = deepcopy(retained)
    selected["driver_runtime"]["module_root"] = str(copied)
    publication._immutable(shared / "runtime.json", selected)
    publication._runtime_files(selected["driver_runtime"])
    return selected


def _sealed_engineering_phase(tmp_path, verified_control_runtime):
    """Prepare real durable controls, deliberately without scientific input or dispatch.

    This private-plan fixture tests admission/custody controls only. Its marker
    is not a valid scientific worker request and must never be executed.
    """
    intent = {"policy": POLICY.to_dict(), "engineering_control": "not_a_scientific_result"}
    directory, saved = publication._begin(tmp_path / "grading", "native-hmmer-preparation-grading",
        intent, "prepared.json")
    assert saved is None
    _copy_control_runtime(tmp_path, verified_control_runtime)
    plan = {"task": "grade", "directory": str(directory), "engineering_control": True, "failures": []}
    publication._immutable(directory / "plan.json", plan)
    selected, handle = publication._prepare_worker(directory, plan, POLICY)
    assert handle.read()["stage"] == "prepared" and handle.read()["started_at"] is None
    return directory, intent, plan, selected, handle


def test_matching_sealed_unfinished_phase_recovers_original_handle_without_start(tmp_path, monkeypatch, verified_control_runtime):
    directory, intent, plan, selected, handle = _sealed_engineering_phase(tmp_path, verified_control_runtime)
    before = handle.read()
    def forbidden(*args, **kwargs):
        pytest.fail("metadata-only phase recovery dispatched, observed or replaced work")
    for name in ("prepare_job", "resume_start", "status", "collect"):
        monkeypatch.setattr(publication.native, name, forbidden)
    resumed, saved = publication._begin(tmp_path / "grading", "native-hmmer-preparation-grading",
        intent, "prepared.json")
    assert resumed == directory and saved is None
    restored, same = publication._worker_selection(directory, task="grade", policy=POLICY, plan=plan)
    assert restored == selected and same.path == handle.path and same.read() == before
    assert not (directory / "prepared.json").exists()


@pytest.mark.parametrize("change", ["intent", "plan", "plan_type", "policy", "task", "command", "environment",
    "python_home", "source_bytes", "source_inventory", "runtime_data", "request_bytes", "handle_command", "handle_unit", "missing_handle", "missing_runtime"])
def test_unfinished_worker_recovery_denies_changed_original_controls_before_lifecycle(tmp_path, monkeypatch, change, verified_control_runtime):
    directory, intent, plan, selected, handle = _sealed_engineering_phase(tmp_path, verified_control_runtime)
    selected = deepcopy(selected)
    selected_policy = POLICY
    def write(path, value):
        path.write_text(json.dumps(value, allow_nan=False))
    if change == "intent":
        intent["engineering_control"] = "different"
        write(directory / "intent.json", intent)
    elif change == "plan":
        plan["engineering_control"] = False
        write(directory / "plan.json", plan)
    elif change == "plan_type":
        write(directory / "plan.json", [])
    elif change == "policy":
        selected_policy = LocalJobPolicy(POLICY.memory_bytes - 1, POLICY.scratch_bytes)
    elif change == "task":
        selected["task"] = "project"
        write(directory / "execution-selection.json", selected)
    elif change in {"command", "environment", "python_home"}:
        if change == "command":
            selected["command"][-1] = str(tmp_path / "unselected-plan.json")
        elif change == "environment":
            selected["environment"]["PYTHONPATH"] = str(tmp_path)
        else:
            selected["python_home"] = str(tmp_path)
        write(directory / "execution-selection.json", selected)
    elif change == "source_bytes":
        source = Path(selected["driver_runtime"]["module_root"]) / "gene_annotation_episode/native_hmmer_preparation_result_worker.py"
        source.chmod(0o644)
        source.write_bytes(source.read_bytes() + b"\n# changed engineering copy\n")
    elif change == "source_inventory":
        (Path(selected["driver_runtime"]["module_root"]) / "unselected.py").write_text("unselected source")
    elif change == "runtime_data":
        path = Path(selected["runtime_path"])
        runtime = json.loads(path.read_bytes())
        runtime["data_files"] = [{"path": str(tmp_path / "unselected.json")}]
        write(path, runtime)
    elif change == "request_bytes":
        Path(handle.read()["paths"]["request"]).write_text("{}")
    elif change in {"handle_command", "handle_unit"}:
        body = handle.read()
        if change == "handle_command":
            body["command"] = ["unselected-command"]
        else:
            body["unit"] = "gene-local-job-unselected.service"
        write(handle.path, body)
    elif change == "missing_handle":
        handle.path.unlink()
    else:
        (directory.parent.parent / "native-hmmer-preparation-worker-runtime/runtime.json").unlink()
    def forbidden(*args, **kwargs):
        pytest.fail("changed phase reached lifecycle before original controls authenticated")
    for name in ("prepare_job", "resume_start", "status", "collect"):
        monkeypatch.setattr(publication.native, name, forbidden)
    with pytest.raises((ValueError, FileNotFoundError), match="conflict|changed|missing|invalid|No such file"):
        publication._worker_selection(directory, task="grade", policy=selected_policy)
    assert not (directory / "prepared.json").exists()


@pytest.mark.parametrize("missing", ["selection", "plan", "handle", "binding"])
def test_matching_directory_without_sealed_original_phase_is_not_recovered(tmp_path, monkeypatch, missing, verified_control_runtime):
    directory, intent, _, _, handle = _sealed_engineering_phase(tmp_path, verified_control_runtime)
    name = {"selection": "execution-selection.json", "plan": "plan.json", "handle": handle.path.name,
        "binding": "original-handle.json"}[missing]
    (directory / name).unlink()
    def forbidden(*args, **kwargs):
        pytest.fail("unsealed directory prepared or dispatched replacement work")
    monkeypatch.setattr(publication.native, "prepare_job", forbidden)
    monkeypatch.setattr(publication.native, "resume_start", forbidden)
    with pytest.raises(ValueError, match="original_work_incomplete"):
        publication._begin(tmp_path / "grading", "native-hmmer-preparation-grading", intent, "prepared.json")


def test_grade_and_projection_share_one_original_runtime_without_environment_copy(tmp_path, monkeypatch, verified_control_runtime):
    directory, _, _, selected, first = _sealed_engineering_phase(tmp_path, verified_control_runtime)
    from gene_annotation_episode import native_atac_differential_software as software
    def forbidden(*args, **kwargs):
        pytest.fail("projection cloned an already sealed worker runtime")
    monkeypatch.setattr(software, "freeze_driver_runtime", forbidden)
    intent = {"policy": POLICY.to_dict(), "engineering_control": "projection_control_only"}
    projection, _ = publication._begin(tmp_path / "projection", "native-hmmer-preparation-projection", intent, "publication.json")
    plan = {"task": "project", "directory": str(projection), "engineering_control": True, "failures": []}
    publication._immutable(projection / "plan.json", plan)
    second_selection, second = publication._prepare_worker(projection, plan, POLICY)
    assert second_selection["driver_runtime"] == selected["driver_runtime"]
    assert second_selection["python_home"] == selected["python_home"]
    assert second.path != first.path and second.read()["unit"] != first.read()["unit"]
    assert first.read()["stage"] == second.read()["stage"] == "prepared"
    runtime = directory.parent.parent / "native-hmmer-preparation-worker-runtime"
    assert set(path.name for path in runtime.iterdir()) == {"source", "runtime.json"}
    assert not any(path.name in {"site-packages", "dist-packages"} for path in runtime.rglob("*"))
    retained = json.loads((runtime / "runtime.json").read_bytes())
    assert retained["source_copy_size_bytes"] == sum(path.stat().st_size for path in (runtime / "source").rglob("*") if path.is_file())


def test_complete_runtime_copy_footprint_is_admitted_before_any_copy(tmp_path, monkeypatch):
    from gene_annotation_episode.acquisition import AcquisitionError
    from gene_annotation_episode import native_atac_differential_software as software
    intent = {"policy": POLICY.to_dict(), "engineering_control": "copy_budget_negative"}
    directory, _ = publication._begin(tmp_path / "grading", "native-hmmer-preparation-grading", intent, "prepared.json")
    allocation = []
    def over_budget(path, policy, *, additional_bytes):
        allocation.append((path, policy, additional_bytes))
        raise AcquisitionError("local_job_resource_limit", phase="local_preflight")
    monkeypatch.setattr(publication, "check_scratch_budget", over_budget)
    monkeypatch.setattr(software, "freeze_driver_runtime", lambda **kw: pytest.fail("copied source before complete footprint admission"))
    with pytest.raises(AcquisitionError, match="local_job_resource_limit"):
        publication._worker_runtime(directory, POLICY)
    assert len(allocation) == 1 and allocation[0][:2] == (tmp_path, POLICY)
    assert type(allocation[0][2]) is int and allocation[0][2] > 0
    assert not (tmp_path / "native-hmmer-preparation-worker-runtime").exists()


@pytest.mark.parametrize("code", ["local_job_resource_limit", "local_job_execution_error"])
def test_only_observed_terminal_worker_failure_reaches_existing_failure_receipt(tmp_path, monkeypatch, code, verified_control_runtime):
    """Inject a negative lifecycle observation; this is no native success proof."""
    from gene_annotation_episode.acquisition import AcquisitionError
    directory, _, plan, selected, _ = _sealed_engineering_phase(tmp_path, verified_control_runtime)
    def terminal(handle):
        return {"terminal": True, "quiescent": True, "state": "returned"}
    monkeypatch.setattr(publication.native, "status", terminal)
    def failed(handle):
        raise AcquisitionError(code, phase="local_execution", operational={"injected_negative_control": True})
    monkeypatch.setattr(publication.native, "collect", failed)
    monkeypatch.setattr(publication.native, "resume_start", lambda *a, **kw: pytest.fail("terminal phase restarted"))
    with Store(tmp_path / "store") as store:
        outputs, failures, completed, diagnostics = publication._execute_worker(store, directory, plan, POLICY)
        assert not completed and outputs == {}
        assert code in [row["code"] for row in failures]
        assert store.count("source") == store.count("observation") == 0
        receipt = json.loads(store.get_artifact(diagnostics["worker_receipt_artifact_ref"]))
        assert receipt["operational"] == {"injected_negative_control": True}
        assert selected["command"]


def test_copied_worker_runtime_imports_and_authenticates_without_science(tmp_path, verified_control_runtime):
    """An import-only Python subprocess stays inside the enclosing bounded job.

    It executes no worker main/parser/calculator and starts no independent unit.
    The fixed copied package has no application JSON/TOML fallback directory.
    """
    import subprocess
    directory, _, _, selected, handle = _sealed_engineering_phase(tmp_path, verified_control_runtime)
    program = (
        "import json,sys\n"
        "from pathlib import Path\n"
        "with open(sys.argv[1]) as stream: selected=json.load(stream)\n"
        "from gene_annotation_episode.native_atac_differential_driver import verify_driver_runtime\n"
        "verify_driver_runtime(selected['driver_runtime'])\n"
        "import gene_annotation_episode.native_hmmer_preparation_result_worker as worker\n"
        "import gene_annotation_episode.native_hmmer_preparation_worker as grading\n"
        "import gene_annotation_episode.hmmer_preparation_result_views as views\n"
        "print(json.dumps({'python':sys.executable,'prefix':sys.prefix,"
        "'worker':worker.__file__,'grading':grading.__file__,'views':views.__file__}))\n"
    )
    completed = subprocess.run([selected["driver_runtime"]["python_executable"], "-B", "-S", "-c",
        program, str(directory / "execution-selection.json")], cwd=directory,
        env=selected["environment"], text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    observed = json.loads(completed.stdout)
    assert observed["python"] == selected["driver_runtime"]["python_executable"]
    assert observed["prefix"] == selected["python_home"]
    module_root = Path(selected["driver_runtime"]["module_root"])
    assert all(Path(observed[name]).is_relative_to(module_root) for name in ("worker", "grading", "views"))
    assert not any(path.suffix in {".json", ".toml"} for path in module_root.rglob("*"))
    runtime = json.loads(Path(selected["runtime_path"]).read_bytes())
    assert runtime["data_files"] == [] and runtime["dependency_record_mode"] == "contained_distribution_files_v1"
    assert handle.read()["stage"] == "prepared" and handle.read()["started_at"] is None
    assert not (directory / "worker-result.json").exists()
    (tmp_path / "WORKER_RUNTIME_IMPORT_PREFLIGHT.json").write_text(json.dumps({
        "version": "hmmer_worker_runtime_import_preflight_v1", "observed": observed,
        "runtime_sha256": selected["runtime_sha256"], "source_copy_size_bytes": runtime["source_copy_size_bytes"],
        "required_application_data_files": runtime["data_files"],
        "dependency_exclusions": runtime["dependency_exclusions"],
        "scope": "imports_and_runtime_authentication_only", "worker_main_executed": False,
        "native_HMMER_executed": False, "Source_or_ToolOperation_published": False,
    }, indent=2, allow_nan=False) + "\n")


def test_contained_dependency_bindings_pin_real_packages_and_original_RECORDs(tmp_path):
    import importlib.metadata
    import os
    from gene_annotation_episode import native_atac_differential_software as software
    exclusions = []
    bindings = software._dependency_bindings(contained_records=True, exclusions=exclusions)
    assert bindings
    expected_exclusions = []
    for binding in bindings:
        installed = importlib.metadata.distribution(binding["distribution"])
        root = Path(installed.locate_file("")).resolve(strict=True)
        expected_paths = set()
        # The selected stdlib's Distribution.files may filter missing RECORD
        # entries first. Compare the actual supplied declarations, including a
        # legitimate empty exclusion list, rather than inventing absent inputs.
        for entry in installed.files or ():
            candidate = Path(os.path.abspath(installed.locate_file(entry)))
            reason = ("outside_distribution_root" if not candidate.is_relative_to(root)
                else "non_runtime_bytecode" if candidate.suffix in {".pyc", ".pyo"} else None)
            if reason is not None:
                expected_exclusions.append({"distribution": binding["distribution"], "record_path": str(entry),
                    "declared_path": str(candidate), "reason": reason})
            else:
                retained = candidate.resolve(strict=True)
                assert retained.is_relative_to(root)
                if retained.is_file():
                    expected_paths.add(str(retained))
        assert {row["path"] for row in binding["files"]} == expected_paths
        assert all(Path(row["path"]).is_relative_to(root) and Path(row["path"]).is_file() for row in binding["files"])
        assert any(Path(row["path"]).name == "RECORD" for row in binding["files"])
        assert not any(Path(row["path"]).suffix in {".pyc", ".pyo"} for row in binding["files"])
    assert exclusions == expected_exclusions
    assert {row["reason"] for row in exclusions} <= {"outside_distribution_root", "non_runtime_bytecode"}
    assert all(set(row) == {"distribution", "record_path", "declared_path", "reason"} for row in exclusions)


@pytest.mark.parametrize("fault", ["missing_inside", "symlink_escape_inside"])
def test_contained_dependency_mode_rejects_unavailable_selected_runtime_files(tmp_path, monkeypatch, fault):
    """Negative metadata fixture only; it never supplies a positive runtime."""
    from gene_annotation_episode import native_atac_differential_software as software
    root = tmp_path / "distribution"
    root.mkdir()
    filename = "required.py"
    if fault == "symlink_escape_inside":
        outside = tmp_path / "outside.py"
        outside.write_text("outside selected distribution")
        (root / filename).symlink_to(outside)
    class NegativeMetadata:
        files = [filename]
        version = "negative_control"
        def locate_file(self, value):
            return root / value
    monkeypatch.setattr(software.importlib.metadata, "distribution", lambda name: NegativeMetadata())
    with pytest.raises((FileNotFoundError, ValueError), match="No such file|native_dependency_unavailable"):
        software._dependency_bindings(contained_records=True, exclusions=[])
