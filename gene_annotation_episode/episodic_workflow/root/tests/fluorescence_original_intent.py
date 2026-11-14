"""Exact original intent-validator functions; no native lifecycle execution."""
from copy import deepcopy
from pathlib import Path
import os
import re
from gene_annotation_episode.episodic_workflow.root.library.fluorescence_execution_common import closed, require, same
from gene_annotation_episode.episodic_workflow.root.library.fluorescence_result_contracts import validate_file, validate_path
from gene_annotation_episode.episodic_workflow.root.library.native_fluorescence_contracts import validate_fluorescence_policy

WORKER_MODULE = "gene_annotation_episode.fluorescence_result_worker"
INTENT_VERSION = "fluorescence_worker_intent_v1"


def _environment(root, home, dependencies):
    roots = []
    for row in dependencies:
        path = str(Path(row["package_root"]).parent)
        if path not in roots:
            roots.append(path)
    return dict(PYTHONPATH=os.pathsep.join([str(root / "source_snapshot"), *roots]), PYTHONHOME=home,
        PYTHONNOUSERSITE="1", PYTHONSAFEPATH="1", PYTHONDONTWRITEBYTECODE="1",
        TMPDIR=str(root), TMP=str(root), TEMP=str(root), XDG_CACHE_HOME=str(root / "cache"),
        PIP_CACHE_DIR=str(root / "cache/pip"))


def _pin(value):
    closed(value, ("path", "sha256", "size_bytes"))
    validate_path(value["path"])
    validate_file(dict(artifact_ref="artifact_" + str(value["sha256"]), sha256=value["sha256"],
        size_bytes=value["size_bytes"], format="runtime_file"))


def _validate_intent(intent, plan):
    closed(intent, ("version", "plan", "policy", "command", "environment", "source_pins", "interpreter",
        "dependencies", "python_version", "python_home", "runtime_files"))
    require(intent["version"] == INTENT_VERSION and same(intent["plan"], plan) and validate_fluorescence_policy(intent["policy"]),
            "worker_execution_mismatch")
    root = Path(plan["directory"])
    require(intent["command"] == [str(root / "runtime/python"), "-B", "-S", "-m", WORKER_MODULE, str(root / "plan.json")],
            "worker_execution_mismatch")
    require(type(intent["source_pins"]) is list and intent["source_pins"] and type(intent["runtime_files"]) is list
        and intent["runtime_files"] and type(intent["dependencies"]) is list, "worker_execution_mismatch")
    validate_path(intent["python_home"])
    require(type(intent["python_version"]) is str and bool(intent["python_version"]), "worker_execution_mismatch")
    distributions = set()
    for row in intent["dependencies"]:
        closed(row, ("distribution", "version", "package_root", "files"))
        require(type(row["distribution"]) is str and row["distribution"] and type(row["version"]) is str and row["version"]
            and type(row["files"]) is list and row["files"], "worker_execution_mismatch")
        name = re.sub(r"[-_.]+", "-", row["distribution"]).lower()
        require(name not in distributions, "worker_execution_mismatch")
        distributions.add(name)
        validate_path(row["package_root"])
        require(any(Path(pin["path"]).is_relative_to(row["package_root"]) for pin in row["files"]), "worker_execution_mismatch")
    pins = [*intent["source_pins"], intent["interpreter"], *intent["runtime_files"],
        *(pin for row in intent["dependencies"] for pin in row["files"])]
    for pin in pins:
        _pin(pin)
    require(len({pin["path"] for pin in pins}) == len(pins), "worker_execution_mismatch")
    require(intent["interpreter"]["path"] == str(root / "runtime/python"), "worker_execution_mismatch")
    source_root = root / "source_snapshot"
    require(all(Path(pin["path"]).is_relative_to(source_root) and Path(pin["path"]).suffix == ".py" for pin in intent["source_pins"])
        and str(source_root / "gene_annotation_episode/fluorescence_result_worker.py") in {pin["path"] for pin in intent["source_pins"]},
        "worker_execution_mismatch")
    require(all(Path(pin["path"]).is_relative_to(Path(intent["python_home"]) / "lib") for pin in intent["runtime_files"])
        and same(intent["environment"], _environment(root, intent["python_home"], intent["dependencies"])), "worker_execution_mismatch")
    return deepcopy(intent)


