"""Selected atac action controls and completed-action authority.

These private records belong to the existing results episode. They contain no
calculator and grant no access merely because a file or a private receipt exists.
Completed-action checks use frozen controls and Store metadata, never scientific bytes.
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
from gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_contracts import POLICY, atac_driver_argv, validate_atac_requested_job, validate_atac_run_plan, _dependency_roots
from gene_annotation_episode.episodic_workflow.root.practical_execution_records import validate_receipt
from gene_annotation_episode.episodic_workflow.root.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.episodic_workflow.root.progress_records import validate_resource_observation


from gene_annotation_episode.episodic_workflow.root.library.atac_result_receipt_values import AtacDifferentialResultIntent, AtacDifferentialHandoffProof, AtacDifferentialNativeSnapshot, AtacDifferentialOrigin, AtacDifferentialQualifiedFiles, AtacDifferentialFactGroups, AtacDifferentialSheetEvidence, AtacDifferentialResultReceipt, AtacDifferentialResultAction, _finite_json_copy, require, closed, same, artifact_references, decode, directory, regular, read_control, immutable, empty_facts, empty_files, unique, outcome, qualified_files, closure_value, VERSION, _READING, _READ_CACHE, _OUTPUTS, _TRACK_ROLES


class AtacResultNativeReceipts:
    def file_metadata(self, file, *, value=None, newline=False):
        file = _identity(file)
        metadata = self.store.get(file["artifact_ref"])
        closed(metadata, ("id", "record_type", "sha256", "size", "media_type"))
        require(metadata["record_type"] == "artifact" and metadata["id"] == file["artifact_ref"]
            == "artifact_" + file["sha256"] and metadata["sha256"] == file["sha256"]
            and type(metadata["size"]) is int and metadata["size"] == file["size_bytes"])
        if value is not None:
            raw = canonical(value).encode("utf-8") + (b"\n" if newline else b"")
            require(hashlib.sha256(raw).hexdigest() == file["sha256"] and len(raw) == file["size_bytes"])
        return file

    def _artifact_value(self, reference, value):
        metadata = self.store.get(reference)
        self.file_metadata({"artifact_ref": reference, "sha256": metadata["sha256"],
            "size_bytes": metadata["size"], "format": "application/json"}, value=value)

    def validate_handoff(self, proof, intent):
        from gene_annotation_episode.episodic_workflow.root.terminal_scientific_evidence import is_terminal_target, validate_terminal_handoff
        if is_terminal_target(intent['target']):
            validate_terminal_handoff(proof, intent, self.store, self.owner.run_id)
            return
        closed(proof, AtacDifferentialHandoffProof.__annotations__)
        source, body, snapshot, start = (proof[name] for name in AtacDifferentialHandoffProof.__annotations__)
        practical = PracticalReceiptInformation(self.store, self.owner.run_id)
        qualified, selected = practical._qualify(body, snapshot, intent["scope"])
        require(same(qualified, body) and selected["result"] is not None)
        self._artifact_value(source["artifact_ref"], body)
        self._artifact_value(source["request_ref"], snapshot)
        payload = practical._source_payload(body, source["artifact_ref"], source["request_ref"])
        require(same(source, self.store.get(source["id"])) and source["origin"] == "tool"
            and source["record_type"] == "source" and source["id"] == identity("source", {"origin": "tool", "record": payload})
            and same({k: v for k, v in source.items() if k not in ("id", "record_type", "origin")}, payload)
            and len(practical._sources(source["accession"])) == 1)
        receipt, assignment = body["receipt"], snapshot["assignment"]
        original = self.returns.context(body["episode_id"])
        require(same(plain(original.assignment), assignment) and same(plain(original.scope), body["scope"]))
        require(original.role == "launch_local" and len(original.path) > 2)
        launch = self.returns.context(EpisodeRef(self.owner.run_id, original.path[:-1]).episode_id)
        require(launch.role == "launch")
        self.returns._commission(launch, original)
        self.returns._commission(self.returns.context(EpisodeRef(self.owner.run_id, launch.path[:-1]).episode_id), launch)
        self.validate_launch_selection(plain(launch.assignment), assignment)
        selected_outcome = json.loads(selected["result"])
        require(selected_outcome.get("status") in ("completed", "partial")
            and same(selected_outcome.get("result"), receipt) and source["id"] in selected_outcome.get("record_refs", []))
        require(receipt["tool_name"] in ("practical.job.start", "practical.job.status", "practical.job.collect"))
        requested = validate_atac_requested_job(assignment["requested_job"])
        job = receipt["outcome"].get("facts", {}).get("requested_job", {})
        detail = receipt["outcome"].get("native_outcome") or {}
        key = detail.get("attempt_operation_key")
        require(type(key) is str and detail.get("attempt_id") == digest(key))
        require(job.get("requested_job_sha256") == digest(requested) and job.get("argv") == requested["argv"]
            and same(job.get("environment"), requested["environment"]) and job.get("resource_kind") == "local"
            and type(job.get("handoff")) is dict and job["execution_id"] == job["handoff"].get("execution_id")
            and job["handoff"].get("monitor_operation") == "practical.job.status"
            and job["handoff"].get("results_operation") == "practical.job.collect")
        start = validate_receipt(start)
        start_row = practical._selected(start)
        require(start_row["result"] is not None and start["tool_name"] == "practical.job.start"
            and start["operation_key"] == key and start["run_id"] == self.owner.run_id
            and start["episode_id"] == body["episode_id"] and start["assignment_sha256"] == body["assignment_sha256"])
        start_outcome = json.loads(start_row["result"])
        require(start_outcome.get("status") in ("completed", "partial") and same(start_outcome.get("result"), start))
        start_job = start["outcome"].get("facts", {}).get("requested_job", {})
        start_detail = start["outcome"].get("native_outcome") or {}
        require(start_job.get("execution_id") == job["execution_id"] and start_job.get("requested_job_sha256") == digest(requested)
            and start_detail.get("attempt_id") == detail["attempt_id"] and start_detail.get("attempt_operation_key") == key)
        expected = {"version": "execution_target_v1", "handle": source["id"], "run_id": self.owner.run_id,
            "resource_id": assignment["resource_id"], "resource_kind": "local", "execution_id": job["execution_id"],
            "request_sha256": digest(requested), "origin_episode_id": body["episode_id"],
            "assignment": assignment, "scope": body["scope"]}
        require(same(validate_target(expected), intent["target"]))
        require(job["execution_id"] == str(Path(assignment["workspace"]) / ".episode-operations" /
            digest({"run": self.owner.run_id, "episode": body["episode_id"]}) / digest(key) / "native.json"))

    @staticmethod
    def validate_launch_selection(launch, selected):
        """Check the original permitted choice without today's resource catalog."""
        from gene_annotation_episode.launch_instructions import retain_inherited_selection
        require(launch.get("version") == "execution_launch_assignment_v1"
            and type(launch.get("requests")) is dict and type(launch.get("constraints")) is dict)
        resource = selected["resource_id"]
        require(resource in launch["requests"])
        expected = {**launch["requests"][resource], "resource_id": resource}
        retain_inherited_selection(launch.get("launch_instructions"), selected.get("launch_instructions"))
        retain_inherited_selection(expected.get("launch_instructions"), selected.get("launch_instructions"))
        require(same({k: v for k, v in expected.items() if k != "launch_instructions"},
            {k: v for k, v in selected.items() if k != "launch_instructions"}))
        constraints = launch["constraints"]
        require(("allowed_resource_ids" not in constraints or resource in constraints["allowed_resource_ids"])
            and ("allowed_kinds" not in constraints or "local" in constraints["allowed_kinds"])
            and constraints.get("resource_id", resource) == resource
            and constraints.get("kind", "local") == "local")
        for key, value in constraints.items():
            if key not in {"allowed_resource_ids", "allowed_kinds", "resource_id", "kind"}:
                require(same(selected["constraints"].get(key), value))

    def read_handoff(self, action):
        self.require_action(action)
        from gene_annotation_episode.episodic_workflow.root.terminal_scientific_evidence import is_terminal_target, read_terminal_handoff
        if is_terminal_target(action.intent['target']):
            proof = read_terminal_handoff(self.store, self.owner.run_id,
                action.intent['target'], action.intent['scope'])
            immutable(action.directory / 'handoff.json', proof)
            return deepcopy(proof)
        path = action.directory / "handoff.json"
        saved = read_control(path)
        if saved is None:
            target = action.intent["target"]
            practical = PracticalReceiptInformation(self.store, self.owner.run_id)
            body = practical.read(target["handle"], action.intent["scope"])
            source = self.store.get(target["handle"])
            snapshot = practical._artifact_json(source["request_ref"])
            key = body["receipt"]["outcome"]["native_outcome"]["attempt_operation_key"]
            prefix = f'{self.owner.run_id}:{body["episode_id"]}:'
            suffix = key.removeprefix(prefix)
            require(key.startswith(prefix) and re.fullmatch(r"0|[1-9][0-9]*", suffix) is not None)
            row = self.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
                (self.owner.run_id, body["episode_id"], int(suffix))).fetchone()
            require(row is not None and row["result"] is not None)
            saved = {"source_record": source, "body": body, "assignment_snapshot": snapshot,
                "start_receipt": json.loads(row["result"])["result"]}
            self.validate_handoff(saved, action.intent)
            immutable(path, saved)
        self.validate_handoff(saved, action.intent)
        return deepcopy(saved)

    def capture_control(self, action, name, value, format_name):
        from gene_annotation_episode.native_file_capture import capture_native_file
        self.require_action(action)
        immutable(action.directory / name, value)
        file = capture_native_file(self.store, directory=str(action.directory),
            relative_path=name, format=format_name, media_type="application/json")
        self.file_metadata(file, value=value)
        return file

    def native_snapshot(self, action, observation):
        """Freeze authenticated original controls once, after the observation."""
        self.require_action(action)
        from gene_annotation_episode.episodic_workflow.root.terminal_scientific_evidence import is_terminal_target, terminal_native_snapshot
        if is_terminal_target(action.intent['target']):
            value = terminal_native_snapshot(self, action, observation)
            immutable(action.directory / 'native-snapshot.json', value)
            return value
        path = action.directory / "native-snapshot.json"
        value = read_control(path)
        if value is None:
            from gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_local import local_atac_differential_plan, _strict_json
            from gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_driver import _read_control, confined_file
            from gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_contracts import STARTED_FILENAME
            from gene_annotation_episode.native_file_capture import capture_native_file, retained_native_file
            target = action.intent["target"]
            plan = local_atac_differential_plan(target["assignment"], target["execution_id"])
            handle = _strict_json(Path(target["execution_id"]))
            request = _strict_json(Path(handle["paths"]["request"]))
            request_file = capture_native_file(self.store, directory=str(Path(target["execution_id"]).parent),
                relative_path=Path(handle["paths"]["request"]).name, format="native_local_job_request")
            request_raw = retained_native_file(self.store, request_file).read_bytes().decode("utf-8")
            started_path = confined_file(Path(plan["attempt_directory"]), STARTED_FILENAME)
            marker = _read_control(started_path) if started_path.exists() else None
            native_receipt = observation["native"].get("native_receipt")
            # A missing marker is not evidence that a driver never ran.
            never_started = (marker is None and type(native_receipt) is dict
                and native_receipt.get("execution_failure") is not None)
            value = {"original_plan": plan, "handle": handle, "request": request, "request_raw": request_raw,
                "started_marker": marker, "driver_started": True if marker is not None else False if never_started else None,
                "plan_file": self.capture_control(action, "native-plan.json", plan, "atac_differential_run_plan_v1"),
                "handle_file": self.capture_control(action, "native-handle.json", handle, "durable_systemd_native_job_v2"),
                "request_file": request_file,
                "started_marker_file": None if marker is None else self.capture_control(action,
                    "driver-started.json", marker, "native_atac_started_v1")}
            self.validate_native(value, action.intent, observation)
            immutable(path, value)
        self.validate_native(value, action.intent, observation)
        return deepcopy(value)

    def validate_native(self, value, intent, observation):
        from gene_annotation_episode.episodic_workflow.root.terminal_scientific_evidence import is_terminal_target, validate_terminal_native
        if is_terminal_target(intent['target']):
            validate_terminal_native(value, intent, observation, self.store, self.owner.run_id)
            return
        from gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_local import _request
        from gene_annotation_episode.native_lifecycle import VERSION as native_version
        closed(value, AtacDifferentialNativeSnapshot.__annotations__)
        plan = validate_atac_run_plan(value["original_plan"])
        policy = POLICY
        target, ident = intent["target"], plan["identity"]
        require(same(plan["requested_job"], target["assignment"]["requested_job"])
            and same(plan["policy"], policy) and ident["run_id"] == intent["run_id"]
            and ident["episode_id"] == target["origin_episode_id"]
            and ident["execution_id"] == target["execution_id"] and ident["resource_id"] == target["resource_id"]
            and ident["assignment_sha256"] == digest(target["assignment"])
            and ident["requested_job_sha256"] == target["request_sha256"]
            and ident["attempt_id"] == digest(ident["operation_key"]))
        handoff = read_control(self.action_directory(intent["episode_id"], intent["operation_key"]) / "handoff.json")
        require(handoff is not None and ident["operation_key"] == handoff["start_receipt"]["operation_key"])
        handle, request = value["handle"], value["request"]
        root = Path(target["execution_id"]).parent
        require(type(handle) is dict and handle.get("version") == native_version
            and handle.get("stage") in {"prepared", "submitting", "released"}
            and handle.get("command") == atac_driver_argv(plan) and handle.get("cwd") == str(root)
            and same(handle.get("metadata", {}).get("policy"), policy))
        paths = handle.get("paths")
        require(type(paths) is dict and {"request", "ready", "release", "status", "result", "launcher"} <= paths.keys()
            and not paths.keys() - {"request", "ready", "release", "status", "result", "launcher", "statistics", "native_events"}
            and len(set(paths.values())) == len(paths) and all(type(p) is str and Path(p).parent == root
                and str(Path(p)) == p for p in paths.values()))
        require(same(request, _request(plan, paths)))
        require(type(value["request_raw"]) is str)
        raw = value["request_raw"].encode("utf-8")
        require(same(decode(raw, canonical_bytes=False), request))
        self.file_metadata(value["request_file"])
        require(value["request_file"]["format"] == "native_local_job_request"
            and value["plan_file"]["format"] == "atac_differential_run_plan_v1"
            and value["handle_file"]["format"] == native_version)
        require(hashlib.sha256(raw).hexdigest() == value["request_file"]["sha256"] == handle.get("request_sha256")
            and len(raw) == value["request_file"]["size_bytes"])
        for field, payload in (("plan_file", plan), ("handle_file", handle)):
            self.file_metadata(value[field], value=payload)
        marker = value["started_marker"]
        if marker is not None:
            closed(marker, ("plan", "started_at"))
            require(same(marker["plan"], plan) and type(marker["started_at"]) is str and bool(marker["started_at"]))
            self.file_metadata(value["started_marker_file"], value=marker)
            require(value["driver_started"] is True
                and value["started_marker_file"]["format"] == "native_atac_started_v1")
        else:
            require(value["started_marker_file"] is None)
            native = observation["native"].get("native_receipt")
            expected = False if type(native) is dict and native.get("execution_failure") is not None else None
            require(value["driver_started"] is expected)

    def validate_observation(self, value, intent):
        from gene_annotation_episode.episodic_workflow.root.terminal_scientific_evidence import is_terminal_target, validate_terminal_observation
        if is_terminal_target(intent['target']):
            validate_terminal_observation(value, intent, self.store, self.owner.run_id)
            return value
        from gene_annotation_episode.native_lifecycle import VERSION as native_version
        value = validate_resource_observation(value)
        native = value["native"]
        policy = POLICY
        require(native.get("execution_id") == intent["target"]["execution_id"]
            and native.get("version") == native_version and type(native.get("terminal")) is bool
            and type(native.get("quiescent")) is bool and same(native.get("metadata", {}).get("policy"), policy))
        require(not native["terminal"] or native["quiescent"] and native["state"] == "returned")
        if native["terminal"]:
            require(type(native["metadata"].get("service_exit")) is dict
                and value["state"] in {"completed", "failed"})
        return value

    def observation(self, action):
        self.require_action(action)
        path = action.directory / "observation.json"
        value = read_control(path)
        if value is None:
            value = self.owner.job_progress_provider.targets.observe_target(action.intent["target"],
                operation_key=action.intent["operation_key"])
            value = self.validate_observation(value, action.intent)
            immutable(path, value)
        return deepcopy(self.validate_observation(value, action.intent))

    def origins(self, context, assignment):
        """Authenticate every exact received action origin, without science I/O."""
        bundle = assignment["selector"]["saved_sheet_bundle"]
        validate_atac_fact_values(SAVED_SOURCE, [bundle])
        origins = self.returns.authenticate_received_saved_bundle(context, bundle)
        matches = []
        require(type(origins) is tuple and bool(origins), "atac_saved_handoff_conflict")
        for origin in origins:
            closed(origin, ("episode_id", "operation_key"))
            row = self.read_completed(**origin, scope=plain(context.scope))
            require(any(same(bundle, saved) for saved in row["facts"][SAVED_SOURCE])
                and row["intent"]["target"]["handle"] == assignment["handoff_ref"], "atac_saved_handoff_conflict")
            matches.append(row)
        require(len(unique(origins)) == len(origins))
        require(all(same(row["intent"]["target"], matches[0]["intent"]["target"]) for row in matches),
            "atac_saved_target_conflict")
        return matches

