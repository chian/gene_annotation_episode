"""Python-driver pin controls; the temporary native files are never executed."""
from copy import deepcopy
import hashlib
from pathlib import Path
import platform
import stat
import sys
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode import native_atac_differential_contracts as contracts
from gene_annotation_episode import native_atac_differential_driver as driver
from gene_annotation_episode import native_atac_differential_software as software

from test_native_atac_differential_contracts import fake_software


def _pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


def _metadata():
    """Nonexistent paths establish metadata validation has no file dependency."""
    return dict(python_executable="/engineering/python", python_sha256="0" * 64,
        python_version="3.12.0", module_root="/engineering/source",
        implementation_files=[dict(module="gene_annotation_episode.fixture_driver", sha256="1" * 64)],
        dependencies=[dict(distribution="runtime-fixture", version="engineering-only",
            package_root="/engineering/site/runtime_fixture", files=[dict(
                path="/engineering/site/runtime_fixture/__init__.py", sha256="2" * 64, size_bytes=1)])])


def _actual_driver(tmp_path, monkeypatch):
    """Use real file pins with an explicitly controlled import inventory."""
    source = _write(tmp_path / "source/gene_annotation_episode/fixture_driver.py", b"SEAL_VERSION = 1\n")
    package = _write(tmp_path / "site-packages/runtime_fixture/__init__.py", b"VERSION = 'fixture'\n")
    modules = {"gene_annotation_episode.fixture_driver": SimpleNamespace(__file__=str(source)),
        "runtime_fixture": SimpleNamespace(__file__=str(package))}
    monkeypatch.setattr(driver, "sys", SimpleNamespace(modules=modules))
    monkeypatch.setattr(driver, "importlib", SimpleNamespace(
        metadata=SimpleNamespace(version=lambda name: "engineering-only"),
        import_module=lambda name: modules[name]))
    record = dict(python_executable=sys.executable,
        python_sha256=_pin(Path(sys.executable).resolve(strict=True))["sha256"],
        python_version=platform.python_version(), module_root=str(tmp_path / "source"),
        implementation_files=[dict(module="gene_annotation_episode.fixture_driver", sha256=_pin(source)["sha256"])],
        dependencies=[dict(distribution="runtime-fixture", version="engineering-only",
            package_root=str(package.parent), files=[_pin(package)])])
    return record, source, package, modules


def _native_files(tmp_path):
    """MACS2-shaped pin fixtures for the old wrapper, not native software."""
    root = tmp_path / "native/site"
    script = _write(tmp_path / "native/bin/macs2", b"engineering fixture; never executable\n")
    files = [script]
    for name in ("MACS2/callpeak_cmd.py", "MACS2/bdgdiff_cmd.py", "MACS2/IO/Parser.fixture.so",
            "numpy/__init__.py", "numpy.libs/libfixture.so"):
        files.append(_write(root / name, ("engineering fixture: " + name + "\n").encode()))
    return dict(python_executable=sys.executable,
        python_sha256=_pin(Path(sys.executable).resolve(strict=True))["sha256"],
        python_version=platform.python_version(), macs2_script=str(script), macs2_sha256=_pin(script)["sha256"],
        macs2_version="2.2.9.1", import_roots=[str(root)], files=[_pin(path) for path in files])


def test_driver_contract_is_detached_and_has_no_macs2_requirement():
    record = _metadata()
    selected = contracts.validate_driver_runtime(record,
        required_modules=("gene_annotation_episode.fixture_driver",), required_dependencies=("runtime_fixture",))
    assert selected == record and selected is not record
    selected["implementation_files"][0]["sha256"] = "f" * 64
    assert record["implementation_files"][0]["sha256"] == "1" * 64
    schema = contracts.driver_runtime_schema()
    assert schema == contracts.atac_execution_schema("DriverRuntime")
    assert set(schema["properties"]) == set(record)
    schema["properties"].clear()
    assert contracts.driver_runtime_schema()["properties"]


@pytest.mark.parametrize("changed", ["module_duplicate", "module_name", "dependency_duplicate",
    "pin_duplicate", "relative_interpreter", "relative_package"])
def test_driver_contract_rejects_ambiguous_names_or_nonabsolute_paths(changed):
    record = _metadata()
    if changed == "module_duplicate":
        record["implementation_files"].append(deepcopy(record["implementation_files"][0]))
    elif changed == "module_name":
        record["implementation_files"][0]["module"] = "other_package.fixture_driver"
    elif changed == "dependency_duplicate":
        duplicate = deepcopy(record["dependencies"][0])
        duplicate["distribution"] = "RUNTIME_fixture"
        record["dependencies"].append(duplicate)
    elif changed == "pin_duplicate":
        record["dependencies"][0]["files"] *= 2
    elif changed == "relative_interpreter":
        record["python_executable"] = "bin/python"
    else:
        record["dependencies"][0]["package_root"] = "site/runtime_fixture"
    with pytest.raises(ValueError):
        contracts.validate_driver_runtime(record)


@pytest.mark.parametrize("missing", ["module", "dependency", "callpeak", "bdgdiff", "parser", "numpy"])
def test_atac_contract_keeps_original_driver_and_native_requirements(missing):
    value = fake_software()
    assert contracts.validate_atac_software(value) == value
    if missing == "module":
        value["driver_runtime"]["implementation_files"] = [r for r in value["driver_runtime"]["implementation_files"]
            if r["module"] != contracts.DRIVER_MODULE]
    elif missing == "dependency":
        value["driver_runtime"]["dependencies"] = [r for r in value["driver_runtime"]["dependencies"]
            if r["distribution"] != "jsonschema"]
    else:
        suffix = {"callpeak": "/MACS2/callpeak_cmd.py", "bdgdiff": "/MACS2/bdgdiff_cmd.py",
            "parser": "/MACS2/IO/Parser.", "numpy": "/numpy/__init__.py"}[missing]
        value["macs2_runtime"]["files"] = [r for r in value["macs2_runtime"]["files"] if suffix not in r["path"]]
    with pytest.raises(ValueError, match="native_dependency_unavailable"):
        contracts.validate_atac_software(value)


def test_verify_driver_uses_actual_pins_without_native_software(tmp_path, monkeypatch):
    record, _, _, _ = _actual_driver(tmp_path, monkeypatch)
    assert driver.verify_driver_runtime(record) is None


@pytest.mark.parametrize("changed", ["interpreter_hash", "python_version", "source_bytes", "loaded_source",
    "dependency_version", "package_root", "dependency_bytes", "unpinned_import"])
def test_verify_driver_rejects_changed_runtime_closure(tmp_path, monkeypatch, changed):
    record, source, package, modules = _actual_driver(tmp_path, monkeypatch)
    if changed == "interpreter_hash":
        record["python_sha256"] = "f" * 64
    elif changed == "python_version":
        record["python_version"] = "0.0.0"
    elif changed == "source_bytes":
        source.write_bytes(b"SEAL_VERSION = 2\n")
    elif changed == "loaded_source":
        modules["gene_annotation_episode.fixture_driver"].__file__ = str(tmp_path / "elsewhere.py")
    elif changed == "dependency_version":
        record["dependencies"][0]["version"] = "different-version"
    elif changed == "package_root":
        record["dependencies"][0]["package_root"] = str(tmp_path / "elsewhere")
    elif changed == "dependency_bytes":
        package.write_bytes(b"VERSION = 'changed'\n")
    else:
        unpinned = _write(tmp_path / "site-packages/unpinned/__init__.py", b"UNPINNED = True\n")
        modules["unpinned"] = SimpleNamespace(__file__=str(unpinned))
    with pytest.raises(ValueError, match="native_dependency_unavailable"):
        driver.verify_driver_runtime(record)


def test_atac_verifier_delegates_driver_and_retains_native_hash_checks(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(driver, "verify_driver_runtime", lambda record: calls.append(deepcopy(record)))
    value = dict(driver_runtime=_metadata(), macs2_runtime=_native_files(tmp_path))
    assert driver.verify_software(value) is None
    assert calls == [value["driver_runtime"]]
    Path(value["macs2_runtime"]["files"][-1]["path"]).write_bytes(b"changed native closure\n")
    with pytest.raises(ValueError, match="native_dependency_unavailable"):
        driver.verify_software(value)
    assert calls == [value["driver_runtime"], value["driver_runtime"]]


def test_freezer_copies_only_selected_source_closure_and_never_imports_it(tmp_path, monkeypatch):
    source = tmp_path / "original"
    originals = {
        "gene_annotation_episode/__init__.py": b"# engineering package\n",
        "gene_annotation_episode/fixture_driver.py": b"from .leaf_fixture import VALUE\nraise RuntimeError('must not import')\n",
        "gene_annotation_episode/leaf_fixture.py": b"VALUE = 'retained driver bytes'\n",
    }
    for name, raw in originals.items():
        _write(source / name, raw)
    dependency = _metadata()["dependencies"]
    monkeypatch.setattr(software, "_dependency_bindings", lambda: deepcopy(dependency))
    target = tmp_path / "snapshot"
    arguments = dict(module_root=str(source), snapshot_directory=str(target),
        driver_modules=("gene_annotation_episode.fixture_driver",), policy=LocalJobPolicy(**contracts.POLICY))
    result = software.freeze_driver_runtime(**arguments)
    assert result["module_root"] == str(target) and result["dependencies"] == dependency
    expected = sorted(name.removesuffix(".py").replace("/", ".") for name in originals)
    assert [r["module"] for r in result["implementation_files"]] == expected
    assert contracts.DRIVER_MODULE not in expected
    for name, raw in originals.items():
        assert (target / name).read_bytes() == raw
        assert stat.S_IMODE((target / name).stat().st_mode) == 0o444
    before = {name: _pin(target / name) for name in originals}
    assert software.freeze_driver_runtime(**arguments) == result
    _write(source / "gene_annotation_episode/leaf_fixture.py", b"VALUE = 'changed original'\n")
    with pytest.raises(ValueError):
        software.freeze_driver_runtime(**arguments)
    assert {name: _pin(target / name) for name in originals} == before


def test_freezer_enforces_supplied_scratch_budget_before_copy(tmp_path, monkeypatch):
    source = tmp_path / "original"
    _write(source / "gene_annotation_episode/__init__.py", b"# package\n")
    _write(source / "gene_annotation_episode/fixture_driver.py", b"VALUE = 1\n")
    monkeypatch.setattr(software, "_dependency_bindings", lambda: pytest.fail("copy budget must fail first"))
    target = tmp_path / "snapshot"
    policy = LocalJobPolicy(memory_bytes=contracts.POLICY["memory_bytes"], scratch_bytes=1, wall_seconds=None)
    with pytest.raises(AcquisitionError, match="local_job_resource_limit"):
        software.freeze_driver_runtime(module_root=str(source), snapshot_directory=str(target),
            driver_modules=("gene_annotation_episode.fixture_driver",), policy=policy)
    assert list(target.rglob("*.py")) == []


def test_atac_freezer_keeps_seed_policy_layout_and_complete_native_closure(tmp_path, monkeypatch):
    calls = []
    frozen_driver = fake_software()["driver_runtime"]
    def freeze(**kwargs):
        calls.append(kwargs)
        return deepcopy(frozen_driver)
    monkeypatch.setattr(software, "freeze_driver_runtime", freeze)
    native = _native_files(tmp_path)
    arguments = dict(module_root=str(tmp_path / "source"), snapshot_directory=str(tmp_path / "snapshot"),
        native_runtime=native, additional_driver_modules=("gene_annotation_episode.fixture_extra",))
    assert software.freeze_atac_native_software_binding(**arguments) == dict(driver_runtime=frozen_driver, macs2_runtime=native)
    assert calls == [dict(module_root=arguments["module_root"], snapshot_directory=arguments["snapshot_directory"],
        driver_modules=[contracts.DRIVER_MODULE, "gene_annotation_episode.fixture_extra"],
        policy=LocalJobPolicy(**contracts.POLICY))]
    native["files"] = [r for r in native["files"] if "/numpy.libs/" not in r["path"]]
    with pytest.raises(ValueError, match="native_dependency_unavailable"):
        software.freeze_atac_native_software_binding(**arguments)
