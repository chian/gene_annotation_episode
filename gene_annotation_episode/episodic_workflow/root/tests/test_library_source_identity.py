"""Supplied-record and saved-command compatibility; no native execution.

Software rows below are labelled controls. Real file checks use small inert
temporary source files, not a claim of scientific runtime completeness.
"""
from copy import deepcopy
import hashlib
from importlib import import_module
from pathlib import Path
import sys

import pytest

BASE = "gene_annotation_episode.episodic_workflow.root.library."
ORIGINAL = import_module("gene_annotation_episode.episodic_workflow.root.tests.fixtures.library_source_identity.original_records")


def outcome(call, value):
    try:
        return ("returned", call(deepcopy(value)))
    except Exception as error:
        return ("raised", type(error).__name__, str(error))


def private_name(name):
    return name.replace("gene_annotation_episode.", BASE, 1)


@pytest.mark.parametrize("case", ["ordinary", "extra_current", "missing", "duplicate"])
def test_atac_legacy_admission_matches_original(case):
    old = import_module("gene_annotation_episode.native_atac_differential_contracts")
    current = import_module(BASE + "native_atac_differential_contracts")
    value = ORIGINAL.fake_software()
    rows = value["driver_runtime"]["implementation_files"]
    if case == "extra_current":
        rows.extend({"module": private_name(row["module"]), "sha256": row["sha256"]} for row in list(rows))
    elif case == "missing":
        rows.pop()
    elif case == "duplicate":
        rows.append(deepcopy(rows[0]))
    expected = outcome(old.validate_atac_software, value)
    assert expected[0] == ("returned" if case in ("ordinary", "extra_current") else "raised")
    assert outcome(current.validate_atac_software, value) == expected


@pytest.mark.parametrize("case", ["current", "changed_command"])
def test_atac_current_request_uses_its_selected_driver(tmp_path, case):
    current = import_module(BASE + "native_atac_differential_contracts")
    job = ORIGINAL.job_fixture(tmp_path)
    environment = ORIGINAL.requested(job, tmp_path)["environment"]
    for row in job["software"]["driver_runtime"]["implementation_files"]:
        row["module"] = private_name(row["module"])
    selected = current.requested_job_from_atac(job, environment=environment)
    assert selected["argv"][3:5] == ["-m", BASE + "native_atac_differential_driver"]
    if case == "changed_command":
        selected["argv"][4] = "gene_annotation_episode.native_atac_differential_driver"
        with pytest.raises(ValueError):
            current.validate_atac_requested_job(selected)
    else:
        assert current.validate_atac_requested_job(selected) == selected


@pytest.mark.parametrize("case", ["missing_driver", "incomplete_split"])
def test_atac_incomplete_current_source_group_rejected(case):
    current = import_module(BASE + "native_atac_differential_contracts")
    software = ORIGINAL.fake_software()
    rows = software["driver_runtime"]["implementation_files"]
    for row in rows:
        row["module"] = private_name(row["module"])
    if case == "missing_driver":
        rows[:] = [row for row in rows if row["module"] != BASE + "native_atac_differential_driver"]
    else:
        rows[0]["module"] = rows[0]["module"].replace(BASE, "gene_annotation_episode.", 1)
    with pytest.raises(ValueError, match="native_dependency_unavailable"):
        current.validate_atac_software(software)


def chromatin_software():
    old = import_module("gene_annotation_episode.native_chromatin_interaction_contracts")
    value = deepcopy(ORIGINAL.fake_software()["driver_runtime"])
    value["driver_module"] = old.DRIVER_MODULE
    value["implementation_files"] = [{"module": name, "sha256": "0" * 64} for name in sorted(old.REQUIRED_MODULES)]
    value["dependencies"] = [{"distribution": name, "version": "supplied-control", "package_root": "/fixture/" + name,
        "files": [{"path": "/fixture/" + name + "/__init__.py", "sha256": "0" * 64, "size_bytes": 1}]}
        for name in sorted(old.REQUIRED_DEPENDENCIES)]
    return value


@pytest.mark.parametrize("case", ["ordinary", "extra_current", "missing"])
def test_chromatin_legacy_admission_matches_original(case):
    old = import_module("gene_annotation_episode.native_chromatin_interaction_contracts")
    current = import_module(BASE + "native_chromatin_interaction_contracts")
    value = chromatin_software()
    rows = value["implementation_files"]
    if case == "extra_current":
        rows.extend({"module": private_name(row["module"]), "sha256": row["sha256"]} for row in list(rows))
    elif case == "missing":
        rows.pop()
    expected = outcome(old.validate_chromatin_software, value)
    assert expected[0] == ("raised" if case == "missing" else "returned")
    assert outcome(current.validate_chromatin_software, value) == expected


@pytest.mark.parametrize("case", ["current", "wrong_driver"])
def test_chromatin_driver_requires_its_corresponding_sources(case):
    current = import_module(BASE + "native_chromatin_interaction_contracts")
    value = chromatin_software()
    for row in value["implementation_files"]:
        row["module"] = private_name(row["module"])
    if case == "current":
        value["driver_module"] = private_name(value["driver_module"])
        assert current.validate_chromatin_software(value) == value
    else:
        with pytest.raises(ValueError, match="native_dependency_unavailable"):
            current.validate_chromatin_software(value)


@pytest.mark.parametrize("case", ["absent", "empty", "malformed", "legacy", "current"])
def test_restriction_command_preserves_original_nonvalidating_boundary(case):
    current = import_module(BASE + "restriction_mapping_jobs")
    reservation = {"software": {"python": {"path": "/fixture/python"}},
        "request_file": {"path": "/fixture/request.json"}, "output_directory": "/fixture/output"}
    if case == "empty":
        reservation["software"]["implementation_files"] = []
    elif case == "malformed":
        reservation["software"]["implementation_files"] = [None, {}]
    elif case in ("legacy", "current"):
        package = "gene_annotation_episode" + ("/episodic_workflow/root/library" if case == "current" else "")
        reservation["software"]["implementation_files"] = [{"path": "/fixture/" + package + "/restriction_mapping_worker.py"}]
    expected = ORIGINAL._command(reservation)
    if case == "current":
        expected[3] = BASE + "restriction_mapping_worker"
    assert current._command(reservation) == expected


@pytest.mark.parametrize("worker", ["global", "earlier_root"])
def test_hmmer_saved_program_bytes_match_original(worker):
    current = import_module(BASE + "native_hmmer_preparation_result_publication")
    name = ORIGINAL._HISTORICAL_WORKER_MODULE if worker == "global" else ORIGINAL._WORKER_MODULE
    driver = {"implementation_files": [{"module": name}, {"module": ORIGINAL._VERIFY_MODULE}]}
    assert current._worker_program(driver) == ORIGINAL._worker_program(driver)


def test_hmmer_fresh_program_changes_only_actual_import_owners():
    current = import_module(BASE + "native_hmmer_preparation_result_publication")
    driver = {"implementation_files": [{"module": ORIGINAL._WORKER_MODULE},
        {"module": BASE + "native_atac_differential_driver"}]}
    expected = ORIGINAL._WORKER_PROGRAM.replace(
        "from gene_annotation_episode.native_atac_differential_driver import verify_driver_runtime\n",
        "from " + BASE + "native_atac_differential_driver import verify_driver_runtime\n").replace(
        "from gene_annotation_episode.native_infernal_contracts import native_infernal_digest\n",
        "from " + BASE + "native_infernal_contracts import native_infernal_digest\n")
    assert current._worker_program(driver) == expected


def test_hmmer_ambiguous_worker_keeps_original_error():
    current = import_module(BASE + "native_hmmer_preparation_result_publication")
    value = {"implementation_files": [{"module": ORIGINAL._HISTORICAL_WORKER_MODULE},
        {"module": ORIGINAL._WORKER_MODULE}, {"module": ORIGINAL._VERIFY_MODULE}]}
    expected = outcome(ORIGINAL._worker_program, value)
    assert expected[0] == "raised"
    assert outcome(current._worker_program, value) == expected


def runtime_files(tmp_path, variant):
    worker = ORIGINAL._HISTORICAL_WORKER_MODULE if variant == "global" else ORIGINAL._WORKER_MODULE
    verifier = ORIGINAL._VERIFY_MODULE if variant != "current" else BASE + "native_atac_differential_driver"
    source_root = tmp_path / "source"
    records = []
    for name in (worker, verifier):
        path = source_root / (name.replace(".", "/") + ".py")
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = b"# Inert source-pin control; never executed.\n"
        path.write_bytes(raw)
        records.append({"module": name, "sha256": hashlib.sha256(raw).hexdigest()})
    executable = Path(sys.executable).resolve()
    dependency = tmp_path / "dependency" / "__init__.py"
    dependency.parent.mkdir()
    dependency.write_bytes(b"# Inert dependency-pin control.\n")
    return {"python_executable": str(executable), "python_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "python_version": sys.version.split()[0], "module_root": str(source_root),
        "implementation_files": records, "dependencies": [{"distribution": "source-identity-control",
            "version": "supplied-control", "package_root": str(dependency.parent),
            "files": [{"path": str(dependency), "sha256": hashlib.sha256(dependency.read_bytes()).hexdigest(),
                "size_bytes": dependency.stat().st_size}]}]}


@pytest.mark.parametrize("variant", ["global", "earlier_root", "current"])
def test_hmmer_actual_pin_checks_keep_original_inventory(tmp_path, variant):
    current = import_module(BASE + "native_hmmer_preparation_result_publication")
    driver = runtime_files(tmp_path, variant)
    if variant != "current":
        assert ORIGINAL._runtime_files(driver) == driver
    assert current._runtime_files(driver) == driver
    changed = deepcopy(driver)
    changed["implementation_files"][0]["sha256"] = "f" * 64
    failed = outcome(current._runtime_files, changed)
    assert failed[0] == "raised" and "original_software_changed" in failed[2]
    if variant != "current":
        assert failed == outcome(ORIGINAL._runtime_files, changed)
