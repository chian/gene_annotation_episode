"""Explicit finite result-worker dependencies; no native producer execution.

The one worker consumes the existing retained 432 input fixture. Dependency
faults are engineered before dispatch. The optional legacy case reads only the
authenticated metadata of the original failed 521 worker, without reopening DBs.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_genomic_overlap_preparation as preparation
from gene_annotation_episode.state import Store
from test_native_genomic_overlap_preparation import POLICY, deny, native_plan, read


LEGACY_GATE = "HMMER_NATIVE_ORACLE_G1_LEGACY_WORKER"
LEGACY_INVENTORY_SHA256 = "13a6259f3b3cbc3e2b1fc5afc1118a87a379036e35504f21ec61e063aca32323"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False).encode()


def copy_dependencies(dependencies, directory):
    """Copy every declared distribution file, including resources and extensions."""
    result = []
    for ordinal, dependency in enumerate(dependencies):
        original_root = Path(preparation._dependency_roots({"dependencies": [dependency]})[0])
        target_root = directory / ("selected_distribution_" + str(ordinal))
        files = []
        for index, pin in enumerate(dependency["files"]):
            original = Path(pin["path"])
            try:
                relative = original.relative_to(original_root)
            except ValueError:
                # Distribution metadata can also name installed command files.
                # Keep their bytes/pins without adding that directory to imports.
                relative = Path("external_distribution_files") / str(index) / original.name
            target = target_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
            target.chmod(0o444)
            assert hashlib.sha256(target.read_bytes()).hexdigest() == pin["sha256"]
            assert target.stat().st_size == pin["size_bytes"]
            files.append({**pin, "path": str(target)})
        result.append({**dependency,
            "package_root": str(target_root / Path(dependency["package_root"]).relative_to(original_root)),
            "files": sorted(files, key=lambda row: row["path"])})
    return result


@pytest.fixture(scope="module")
def selected_dependencies(tmp_path_factory):
    # The shared authority includes the five required distributions and every
    # optional format helper actually loaded by this selected environment.
    original = preparation._runtime_dependencies()
    root = tmp_path_factory.mktemp("explicit_package_runtime")
    copied = copy_dependencies(original, root)
    assert [(r["distribution"], r["version"], len(r["files"])) for r in copied] == [
        (r["distribution"], r["version"], len(r["files"])) for r in original]
    assert all(Path(path).name not in {"site-packages", "dist-packages"}
        for path in preparation._dependency_roots({"dependencies": copied}))
    return copied


@pytest.fixture(scope="module")
def produced_worker(tmp_path_factory, selected_dependencies):
    root = tmp_path_factory.mktemp("retained_g1_worker")
    with Store(root / "store") as store:
        plan = native_plan(store, root)
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(preparation, "_runtime_dependencies", lambda: deepcopy(selected_dependencies))
            prepared = preparation.prepare_genomic_overlap_worker(store, plan=plan, policy=POLICY)
        execution = read(store, prepared["execution_receipt_file"])
        body = read(store, execution["handle_file"])
        request_path = preparation.retained_native_file(store, execution["request_file"])
        request_raw = request_path.read_bytes()
        request = json.loads(request_raw)
        yield SimpleNamespace(root=root, store=store, plan=plan, prepared=prepared,
            execution=execution, body=body, request=request, request_raw=request_raw)


def test_explicit_frozen_roots_support_no_site_worker_and_completed_replay(produced_worker, monkeypatch):
    case = produced_worker
    assert case.execution["outcome"] == "returned" and case.execution["returncode"] == 0
    assert case.prepared["failures"] == [] and case.prepared["result"]["state"] == "produced"
    dependencies = case.execution["dependencies"]
    roots = preparation._dependency_roots({"dependencies": dependencies})
    assert case.request["command"] == [case.execution["interpreter"]["path"], "-B", "-S", "-m",
        "gene_annotation_episode.genomic_overlap_result_worker", case.plan["directory"] + "/plan.json"]
    assert case.request["env"]["PYTHONPATH"].split(os.pathsep) == [
        case.plan["directory"] + "/source_snapshot", *roots]
    assert all(Path(path).name.startswith("selected_distribution_") for path in roots)
    expected_digest = hashlib.sha256(preparation._canonical(dependencies)).hexdigest()
    assert case.request["env"]["GENOMIC_OVERLAP_DEPENDENCIES_SHA256"] == expected_digest
    for row in dependencies:
        for pin in row["files"]:
            assert preparation._runtime_file_pin(pin["path"]) == pin
            assert Path(pin["path"]).stat().st_mode & 0o222 == 0
    components = read(case.store, case.prepared["outputs"][1]["observed"])
    assert [r["unfiltered"]["pairwise_overlap_bp_sum"] for r in components["pairs"]] == [8, 5, 2]
    assert [r["unfiltered"]["jaccard_bp"]["value"] for r in components["pairs"]] == pytest.approx([
        1 / 3, 1 / 4, 2 / 13])
    before = (Path(case.plan["directory"]) / "prepared.json").read_bytes()
    for name in ("source_snapshot", "runtime"):
        root = Path(case.plan["directory"]) / name
        for path in [root, *(p for p in root.rglob("*") if p.is_dir())]:
            path.chmod(0o755)
        shutil.rmtree(root)
    with monkeypatch.context() as patch:
        for name in ("_runtime_dependencies", "_runtime_file_pin", "_verify_snapshot", "_snapshot", "_run"):
            patch.setattr(preparation, name, deny)
        for name in ("prepare_job", "resume_start", "status"):
            patch.setattr(preparation.native_lifecycle, name, deny)
        assert preparation.prepare_genomic_overlap_worker(case.store, plan=case.plan, policy=POLICY) == case.prepared
        assert preparation.validate_prepared_genomic_overlap_worker(
            case.store, case.prepared, plan=case.plan) == case.prepared
    assert (Path(case.plan["directory"]) / "prepared.json").read_bytes() == before
    (case.root / "EXPLICIT_DEPENDENCY_RUNTIME.json").write_bytes(canonical({
        "capture": case.prepared, "execution_receipt_file": case.prepared["execution_receipt_file"],
        "dependency_declarations_sha256": expected_digest,
        "distributions": [{"name": r["distribution"], "version": r["version"],
            "package_root": r["package_root"], "file_count": len(r["files"])} for r in dependencies],
        "worker_returncode": case.execution["returncode"], "native_producer_executed": False,
        "completed_replay_without_runtime_refresh": True}))


@pytest.mark.parametrize("fault,code", [("changed", "dependency_conflict"),
    ("missing", "dependency_conflict"), ("injected_import_root", "dependency_binding")])
def test_pending_dependency_fault_rejects_without_new_dispatch(
        tmp_path, selected_dependencies, monkeypatch, fault, code):
    dependencies = copy_dependencies(selected_dependencies, tmp_path / "selected_packages")
    with Store(tmp_path / "store") as store:
        plan = native_plan(store, tmp_path)
        directory = Path(plan["directory"])
        directory.mkdir()
        with monkeypatch.context() as patch:
            patch.setattr(preparation, "_runtime_dependencies", lambda: deepcopy(dependencies))
            intent = preparation._snapshot(store, plan, POLICY)
        if fault == "injected_import_root":
            intent["environment"]["PYTHONPATH"] += os.pathsep + str(tmp_path / "unselected_packages")
        with preparation._directory(str(directory)) as fd:
            preparation._immutable(fd, "plan.json", plan)
            preparation._immutable(fd, "intent.json", intent)
        before = (directory / "intent.json").read_bytes()
        pin = next(pin for row in dependencies if row["distribution"] == "jsonschema"
            for pin in row["files"] if Path(pin["path"]).name == "__init__.py")
        path = Path(pin["path"])
        if fault == "changed":
            path.chmod(0o644)
            path.write_bytes(path.read_bytes() + b"\n# engineered pending runtime change\n")
            path.chmod(0o444)
        elif fault == "missing":
            path.unlink()
        with monkeypatch.context() as patch:
            for name in ("_runtime_dependencies", "_snapshot", "_run"):
                patch.setattr(preparation, name, deny)
            patch.setattr(preparation.native_lifecycle, "prepare_job", deny)
            with pytest.raises(ValueError, match="^genomic_overlap_preparation_" + code + "$"):
                preparation.prepare_genomic_overlap_worker(store, plan=plan, policy=POLICY)
        assert (directory / "intent.json").read_bytes() == before
        assert not any((directory / name).exists() for name in (
            "worker.handle.json", "execution.json", "prepared.json"))


@pytest.mark.parametrize("fault", ["duplicate_distribution", "missing_distribution", "package_root",
    "file_digest", "file_omission", "extra_import_root", "import_order", "extra_environment", "removed_declarations"])
def test_dependency_declarations_and_imports_are_bound_to_original_request(produced_worker, monkeypatch, fault):
    case = produced_worker
    execution, body, request = map(deepcopy, (case.execution, case.body, case.request))
    dependencies = execution["dependencies"]
    if fault == "duplicate_distribution":
        dependencies.append(deepcopy(dependencies[0]))
    elif fault == "missing_distribution":
        dependencies[:] = [r for r in dependencies if r["distribution"] != "jsonschema"]
    elif fault == "package_root":
        dependencies[0]["package_root"] += "/other"
    elif fault == "file_digest":
        dependencies[0]["files"][0]["sha256"] = "f" * 64
    elif fault == "file_omission":
        assert len(dependencies[0]["files"]) > 1
        dependencies[0]["files"].pop()
    elif fault == "removed_declarations":
        execution.pop("dependencies")
    elif fault == "extra_import_root":
        request["env"]["PYTHONPATH"] += os.pathsep + str(case.root / "unselected_packages")
    elif fault == "import_order":
        paths = request["env"]["PYTHONPATH"].split(os.pathsep)
        assert len(paths) > 2
        request["env"]["PYTHONPATH"] = os.pathsep.join([paths[0], *paths[:0:-1]])
    else:
        request["env"]["UNDECLARED_RUNTIME_OPTION"] = "1"
    # Keep the ordinary lifecycle request hash internally consistent so the
    # dependency/environment join, rather than stale JSON bytes, must reject.
    raw = canonical(request)
    body["request_sha256"] = hashlib.sha256(raw).hexdigest()
    with monkeypatch.context() as patch:
        patch.setattr(preparation, "_runtime_dependencies", deny)
        patch.setattr(preparation, "_runtime_file_pin", deny)
        with pytest.raises(ValueError):
            preparation._pins(execution, case.plan)
            preparation._check_handle(body, request, raw, case.plan, execution)


def legacy_inventory(directory, request):
    paths = [directory / name for name in ("plan.json", "intent.json", "execution.json", "worker.handle.json")]
    assert request.parent == directory
    paths.append(request)
    rows = []
    for path in sorted(paths):
        metadata = path.lstat()
        assert stat.S_ISREG(metadata.st_mode)
        raw = path.read_bytes()
        rows.append({"path": path.name, "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw), "mode": stat.S_IMODE(metadata.st_mode)})
    return rows


def test_actual_521_legacy_failure_metadata_needs_no_dependency_discovery(monkeypatch):
    selected = os.environ.get(LEGACY_GATE)
    if selected is None:
        pytest.skip("explicit authenticated legacy worker metadata required")
    assert os.environ.get(LEGACY_GATE + "_SHA256") == LEGACY_INVENTORY_SHA256
    directory = Path(selected)
    body = json.loads((directory / "worker.handle.json").read_bytes())
    request_path = Path(body["paths"]["request"])
    before = legacy_inventory(directory, request_path)
    assert hashlib.sha256(canonical(before)).hexdigest() == LEGACY_INVENTORY_SHA256
    plan = json.loads((directory / "plan.json").read_bytes())
    intent = json.loads((directory / "intent.json").read_bytes())
    execution = json.loads((directory / "execution.json").read_bytes())
    request_raw = request_path.read_bytes()
    request = json.loads(request_raw)
    assert execution["outcome"] == "returned" and execution["returncode"] == 1
    assert "dependencies" not in intent and "dependencies" not in execution
    assert execution["source_pins"] == intent["source_pins"]
    assert request["env"] == intent["environment"]
    assert request["env"]["PYTHONPATH"] == str(directory / "source_snapshot")
    with monkeypatch.context() as patch:
        for name in ("_runtime_dependencies", "_runtime_file_pin", "_capture"):
            patch.setattr(preparation, name, deny)
        patch.setattr(Path, "open", deny)
        preparation._validate_intent(intent, plan)
        preparation._pins(execution, plan)
        preparation._check_handle(body, request, request_raw, plan, execution)
    assert legacy_inventory(directory, request_path) == before
