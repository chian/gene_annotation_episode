"""Selected atac action controls and historical completed-action authority.

These private records belong to the existing results episode. They contain no
calculator and grant no access merely because a file or a private receipt exists.
Historical checks use frozen controls and Store metadata, never scientific bytes.
"""
from __future__ import annotations

import asyncio
from contextlib import ExitStack, asynccontextmanager, contextmanager
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
from typing import Literal, TypedDict

from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.domain import identity
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_contracts import validate_target
from gene_annotation_episode.native_file_capture import NativeFileIdentity, _identity
from gene_annotation_episode.episodic_workflow.root.library.atac_differential_result_contracts import validate_atac_result_record
from gene_annotation_episode.episodic_workflow.root.library.atac_differential_return_views import FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE, validate_atac_fact_values
from gene_annotation_episode.episodic_workflow.root.library.atac_differential_result_worker import validate_atac_result_worker_plan, validate_atac_result_worker_result
from gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_capture import validate_atac_native_capture
from gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_contracts import retained_policy, POLICY, atac_driver_argv, validate_atac_requested_job, validate_atac_run_plan, _dependency_roots
from gene_annotation_episode.episodic_workflow.root.practical_execution_records import validate_receipt
from gene_annotation_episode.episodic_workflow.root.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.episodic_workflow.root.progress_records import validate_resource_observation


from gene_annotation_episode.episodic_workflow.root.library.atac_result_receipt_values import AtacDifferentialResultIntent, AtacDifferentialHandoffProof, AtacDifferentialNativeSnapshot, AtacDifferentialOrigin, AtacDifferentialQualifiedFiles, AtacDifferentialFactGroups, AtacDifferentialSheetEvidence, AtacDifferentialResultReceipt, AtacDifferentialResultAction, _historical, _finite_json_copy, require, closed, same, artifact_references, decode, directory, regular, read_control, immutable, empty_facts, empty_files, unique, outcome, qualified_files, closure_value, VERSION, _READING, _READ_CACHE, _OUTPUTS, _TRACK_ROLES


class AtacResultWorkerReceipts:
    def validate_worker(self, receipt, *, verify_control_bytes=False):
        """Bind the saved finite worker to the selected plan, without reexecution."""
        plan, capture, execution = (receipt[k] for k in ("worker_plan", "worker_capture", "worker_execution"))
        if plan is None:
            require(capture is None and execution is None)
            return
        plan = validate_atac_result_worker_plan(plan, historical=_historical(receipt['intent']))
        intent, selector = receipt["intent"], receipt["intent"]["assignment"]["selector"]
        root = self.action_directory(intent["episode_id"], intent["operation_key"]) / "worker"
        require(plan["directory"] == str(root) and same(plan["selector"], selector))
        if selector["mode"] == "native_result":
            native_capture = receipt["capture"]
            require(native_capture is not None and same(plan["original_plan"], receipt["native"]["original_plan"]))
            for key in ("bundle", "files", "source_action_receipt_ref", "writer_closure_receipt_ref", "driver_state", "failures"):
                require(same(plan[key], native_capture[key]))
            retained = [plan["bundle"], *(row["retained"] for row in plan["files"])]
        else:
            retained = [plan["sheet_bundle"]["sheet"], *plan["sheet_bundle"]["tables"]]
            expected = {"sheet": plan["sheet_bundle"]["sheet"]["file"], "tables": [
                {"track_key": row["track_key"], "file": row["file"]} for row in plan["sheet_bundle"]["tables"]]}
            require(same(expected, selector["saved_sheet_bundle"]))
        for item in retained:
            if item is not None:
                file = self.file_metadata(item["file"])
                require(item["path"] == str(self.store.path / "artifacts" / file["sha256"][:2] / file["sha256"]))
        if capture is None:
            require(execution is None)
            return
        validate_atac_result_record("WorkerCapture", capture)
        policy = retained_policy(execution.get('policy') if type(execution) is dict else None, historical=_historical(receipt['intent']))
        closed(execution, ("version", "plan_file", "intent", "terminal", "quiescent", "policy", "returncode",
            "metadata", "failure", "handle_file", "request_file", "stdout_file", "stderr_file"))
        require(execution["version"] == "atac_worker_execution_v1"
            and same(execution["plan_file"], capture["plan_file"]) and same(execution["policy"], policy)
            and execution["terminal"] is True and execution["quiescent"] is True)
        self.file_metadata(capture["plan_file"], value=plan)
        self.file_metadata(capture["execution_receipt_file"], value=execution)
        require(capture["plan_file"]["format"] == "atac_differential_worker_plan_v1"
            and capture["execution_receipt_file"]["format"] == "atac_worker_execution_v1")
        selected = execution["intent"]
        closed(selected, ("version", "plan", "policy", "command", "environment", "source_pins", "interpreter", "dependencies"))
        require(selected["version"] == "atac_worker_intent_v1" and same(selected["plan"], plan)
            and same(selected["policy"], policy))
        require(type(selected["source_pins"]) is list and bool(selected["source_pins"])
            and type(selected["dependencies"]) is list)

        def pin(value):
            closed(value, ("path", "sha256", "size_bytes"))
            require(type(value["path"]) is str and Path(value["path"]).is_absolute()
                and str(Path(value["path"])) == value["path"] and ".." not in Path(value["path"]).parts
                and type(value["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is not None
                and type(value["size_bytes"]) is int and value["size_bytes"] >= 0)

        for row in [*selected["source_pins"], selected["interpreter"]]:
            pin(row)
        paths = [p["path"] for p in selected["source_pins"]]
        require(len(paths) == len(set(paths)) and all(Path(p).is_relative_to(root / "source_snapshot") for p in paths))
        required = ("atac_differential_result_worker", "atac_differential_contracts", "atac_differential_inputs",
            "atac_differential_sheet", "atac_differential_calculations", "atac_differential_scores",
            "atac_differential_calculation_inputs", "atac_reference_observations", "atac_differential_result_views")
        legacy_sources = all(str(root / "source_snapshot/gene_annotation_episode" / (name + ".py")) in paths for name in required)
        current_sources = all(str(root / "source_snapshot/gene_annotation_episode/episodic_workflow/root/library" / (name + ".py")) in paths for name in required)
        require(legacy_sources or current_sources)
        names = []
        for dependency in selected["dependencies"]:
            closed(dependency, ("distribution", "version", "package_root", "files"))
            require(type(dependency["distribution"]) is str and bool(dependency["distribution"])
                and type(dependency["version"]) is str and bool(dependency["version"])
                and type(dependency["package_root"]) is str and Path(dependency["package_root"]).is_absolute()
                and type(dependency["files"]) is list and bool(dependency["files"]))
            names.append(dependency["distribution"].lower().replace("_", "-"))
            for row in dependency["files"]:
                pin(row)
            require(len({p["path"] for p in dependency["files"]}) == len(dependency["files"]))
        require(len(names) == len(set(names))
            and {"jsonschema", "attrs", "referencing", "rpds-py", "jsonschema-specifications"} <= set(names))
        require(selected["interpreter"]["path"] == str(root / "runtime/python")
            and ((legacy_sources and selected["command"] == [str(root / "runtime/python"), "-B", "-S", "-m",
                "gene_annotation_episode.atac_differential_result_worker", str(root / "plan.json")])
                or (current_sources and selected["command"] == [str(root / "runtime/python"), "-B", "-S", "-m",
                "gene_annotation_episode.episodic_workflow.root.library.atac_differential_result_worker", str(root / "plan.json")])))
        environment = selected["environment"]
        require(type(environment) is dict and all(type(k) is str and type(v) is str for k, v in environment.items()))
        expected = {"PYTHONPATH": os.pathsep.join([str(root / "source_snapshot"), *_dependency_roots(selected)]),
            "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1", "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(root / "tmp"), "TMP": str(root / "tmp"), "TEMP": str(root / "tmp"),
            "XDG_CACHE_HOME": str(root / "cache"), "PIP_CACHE_DIR": str(root / "cache/pip")}
        require(all(environment.get(k) == v for k, v in expected.items())
            and type(environment.get("PYTHONHOME")) is str and Path(environment["PYTHONHOME"]).is_absolute())
        metadata = execution["metadata"]
        require(type(metadata) is dict and same(metadata.get("policy"), policy))
        if execution["failure"] is None:
            require(type(execution["returncode"]) is int)
            require(same(metadata.get("verified_cgroup"), {"memory_max": policy["memory_bytes"], "memory_swap_max": 0,
                "kill_mode": "control-group", "oom_policy": "kill"}))
        else:
            closed(execution["failure"], ("code", "phase", "diagnostic", "operational"))
            require(execution["returncode"] is None)
        for name in ("handle_file", "request_file", "stdout_file", "stderr_file"):
            self.file_metadata(execution[name])
        if verify_control_bytes:
            from gene_annotation_episode.native_file_capture import retained_native_file
            from gene_annotation_episode.native_lifecycle import VERSION as native_version
            handle = decode(retained_native_file(self.store, execution["handle_file"]).read_bytes(), canonical_bytes=False)
            raw = retained_native_file(self.store, execution["request_file"]).read_bytes()
            request = decode(raw, canonical_bytes=False)
            require(handle["version"] == native_version and handle["command"] == selected["command"]
                and handle["cwd"] == str(root) and same(handle["metadata"]["policy"], policy)
                and handle["stage"] in {"prepared", "submitting", "released"}
                and handle["request_sha256"] == hashlib.sha256(raw).hexdigest())
            paths = handle["paths"]
            require(len(set(paths.values())) == len(paths) and all(Path(path).parent == root for path in paths.values()))
            require(same(request, {"command": selected["command"], "cwd": str(root),
                "file_bytes": policy["scratch_bytes"], "ready_path": paths["ready"],
                "release_path": paths["release"], "result_path": paths["result"], "stdin_path": None,
                "env": selected["environment"]}))
        if capture["worker_result_file"] is not None:
            self.file_metadata(capture["worker_result_file"])
            require(capture["worker_result_file"]["format"] == "atac_differential_worker_result_v1")
        result = capture["result"]
        if result is None:
            require(capture["outputs"] == [])
        else:
            result = validate_atac_result_worker_result(result)
            self.file_metadata(capture["worker_result_file"], value=result)
            require(result["mode"] == plan["mode"] and same(result["parameters"], selector["parameters"]))
            from gene_annotation_episode.episodic_workflow.root.library.atac_differential_result_worker import worker_output_specs
            specs = worker_output_specs(plan)
            require(len(specs) == len(result["outputs"]))
            for spec, row in zip(specs, result["outputs"]):
                require(row["role"] == spec["role"] and row["table_key"] == spec["table_key"]
                    and row["declaration"]["relative_path"] == spec["relative_path"]
                    and row["declaration"]["format"] == spec["format"])
            qualified_files(capture, execution)
            for row in capture["outputs"]:
                if row["capture"]["observed"] is not None:
                    self.file_metadata(row["capture"]["observed"])

