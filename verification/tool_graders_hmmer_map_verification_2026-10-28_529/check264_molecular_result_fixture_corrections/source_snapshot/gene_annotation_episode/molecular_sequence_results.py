"""One private molecular custody, selected-action and immediate-child owner.

Public/Episodes registration and the independent scientific launch binding do
not exist in this revision. Ordinary byte/episode custody cannot substitute for
that missing producer association. Stored results are never regraded here.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import fcntl
import hashlib
import json
import os
from pathlib import Path

from method_loop.identities import EpisodeRef
from .acquisition import AcquisitionError
from .communication import plain, validate_form
from .bvbrc_appservice_custody import AppServiceCustody
from .episode_receipts import EpisodeReceipts, RECEIVED_REPORT_PREFIX_VERSION, _validate_report_prefix
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest, validate_target
from .genomic_overlap_result_receipts import GenomicOverlapResultReceipts as _Actions
from .genomic_overlap_result_receipts import immutable, read_control, same, unique
from .genomic_overlap_result_receipts import directory as _control_directory, regular as _control_regular
from .molecular_sequence_result_contracts import (
    FACT_SOURCES, FAILURE_SOURCE, FILE_ROLES, MODES, PLAN_VERSION, PROJECTION_SOURCE, SAVED_SOURCE,
    empty_file_state, failure, require, select_molecular_sequence_return_facts,
    select_stored_molecular_sequence_values, validate_file_state, validate_molecular_sequence_fact_values,
    validate_molecular_sequence_projection, validate_molecular_sequence_result_selector, validate_molecular_sequence_result_worker_result,
    SCHEMAS,
)
from .native_file_capture import NativeFileCaptureError, capture_native_file, retained_native_file, _identity, _declaration
from .native_flux_balance_storage import file_pin, read_bytes
from .practical_receipt_information import PracticalReceiptInformation
from . import molecular_sequence_result_contracts as supplied


VERSION = "molecular_sequence_result_receipt_v1"
PUBLIC_VERSION = "molecular_sequence_public_result_v1"
PREFIX = "molecular_sequence_received_report_prefix"
POLICY = {"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}


def _json(raw):
    from .molecular_sequence_driver import _json as decode
    return decode(raw)


def _facts():
    return {source: [] for source in FACT_SOURCES}


def _retained(identity, declaration=None):
    return dict(state="retained" if declaration is not None else "retained_undeclared", file=identity,
        declared=deepcopy(declaration), observed_identity={k: identity[k] for k in ("sha256", "size_bytes")}, failure=None)


class MolecularSequenceResults(EpisodeReturnRecords):
    """One owner for five profiles; no per-profile receipt or episode types."""
    locked_action = _Actions.locked_action
    require_action = _Actions.require_action
    _selected = _Actions._selected
    _artifact_value = _Actions._artifact_value
    capture_control = _Actions.capture_control
    observation = _Actions.observation
    # These particular helpers validate original generic decision/return frames;
    # no AppService operand, submission or scientific ownership method is used.
    _selection = AppServiceCustody._selection
    _selected_form = AppServiceCustody._selected_form
    _child_contract = AppServiceCustody._child_contract
    _report_contract = staticmethod(AppServiceCustody._report_contract)
    _contract_information = AppServiceCustody._contract_information
    _json = AppServiceCustody._json
    _table = AppServiceCustody._table
    _attempt = AppServiceCustody._attempt

    def __init__(self, owner):
        super().__init__(owner.store, owner.run_id, failure_prefix="molecular_sequence_result_")
        self.owner, self._active = owner, {}

    @property
    def returns(self):
        return self

    def applies(self, context):
        return context.role == "results" and plain(context.assignment).get("selector", {}).get("version") in (
            "molecular_sequence_result_selector_v1", supplied.SUPPLIED_SELECTOR_VERSION)

    def action_directory(self, episode_id, operation_key):
        return Path(self.owner.directory) / "execution-results" / digest([self.run_id, episode_id]) / "molecular-sequence-actions" / digest(operation_key)

    def file_metadata(self, file, *, value=None, newline=False):
        file = _identity(file)
        metadata = self.store.get(file["artifact_ref"])
        require(metadata["record_type"] == "artifact" and metadata["id"] == file["artifact_ref"]
            and metadata["sha256"] == file["sha256"] and metadata["size"] == file["size_bytes"], "molecular_sequence_file_identity_conflict")
        if value is not None:
            raw = canonical(value).encode() + (b"\n" if newline else b"")
            require(hashlib.sha256(raw).hexdigest() == file["sha256"] and len(raw) == file["size_bytes"], "molecular_sequence_file_value_conflict")
        return file

    def _commission(self, parent, child, *, construction=False):
        self.authenticate(parent, allow_unsaved=construction); self.authenticate(child, allow_unsaved=construction)
        require(child.path[:-1] == parent.path, "molecular_sequence_commission_parent_conflict")
        self.store.validate_scope(plain(child.scope), parent_scope=plain(parent.scope))
        slot = child.path[-1][1]
        require(slot.startswith("child_") and slot[6:].isdecimal(), "molecular_sequence_commission_slot_conflict")
        index = int(slot[6:])
        require(str(index) == slot[6:])
        selected, sent = self._selection(parent, index, unsaved=construction)
        require(selected.get("kind") in ("episode_child", "job_child", "child"), "molecular_sequence_original_commission_required")
        require(selected.get("kind") == "child" or selected.get("role") == child.role, "molecular_sequence_commission_role_conflict")
        require(same(selected.get("scope"), plain(child.scope)), "molecular_sequence_commission_scope_conflict")
        if child.role in ("results", "launch", "launch_local"):
            require(same(selected.get("assignment"), plain(child.assignment)), "molecular_sequence_commission_assignment_conflict")
        self._child_contract(child, selected, sent)

    def _context(self, context):
        self.authenticate(context)
        require(self.applies(context) and len(context.path) > 1, "molecular_sequence_results_context_required")
        assignment = plain(context.assignment)
        if assignment.get("selector", {}).get("version") == supplied.SUPPLIED_SELECTOR_VERSION:
            require(set(assignment) == {"version", "selector", "constraints"}
                and assignment["version"] == supplied.SUPPLIED_ASSIGNMENT_VERSION)
            supplied.validate_molecular_sequence_supplied_selector(assignment["selector"])
            supplied.supplied_execution_constraints(assignment["constraints"])
        else:
            require(set(assignment) == {"version", "handoff_ref", "selector"} and assignment["version"] == "execution_results_assignment_v1")
            validate_molecular_sequence_result_selector(assignment["selector"])
        self.store.validate_scope(plain(context.scope))
        self._commission(self.context(EpisodeRef(self.run_id, context.path[:-1]).episode_id), context)
        return assignment

    def intent(self, context, target, tool_name, arguments, operation_key):
        assignment = self._context(context)
        require(tool_name in ("execution.results.status", "execution.results.collect") and arguments == {} and type(arguments) is dict)
        if assignment["selector"].get("version") == supplied.SUPPLIED_SELECTOR_VERSION:
            require(target is None)
        elif assignment["selector"]["mode"] == MODES[0]:
            target = validate_target(plain(target))
            require(target["run_id"] == self.run_id and target["handle"] == assignment["handoff_ref"] and target["resource_kind"] == "local")
            self.store.validate_scope(target["scope"], parent_scope=plain(context.scope))
        else:
            require(target is None)
        value = dict(version="molecular_sequence_result_intent_v1", run_id=self.run_id, episode_id=context.episode_id,
            path=plain(context.path), scope=plain(context.scope), assignment=assignment,
            original_request_sha256=digest(plain(context.request)), operation_key=operation_key, tool_name=tool_name,
            arguments={}, target=deepcopy(target))
        self._selected(value)
        return value

    def validate_observation(self, value, intent):
        from .progress_records import validate_resource_observation
        value = validate_resource_observation(value)
        native = value["native"]
        require(native.get("execution_id") == intent["target"]["execution_id"] and type(native.get("terminal")) is bool
            and type(native.get("quiescent")) is bool and same(native.get("metadata", {}).get("policy"), POLICY), "molecular_sequence_observation_conflict")
        return value

    def initialize_original_binding(self, context, **selected):
        self.authenticate(context)
        # No independently authenticated molecular scientific-request reader or
        # launch materializer is registered. An arbitrary dict/callback cannot
        # turn a private plan's agreement with itself into that missing proof.
        return {"state": "unavailable", "reason": "scientific_binding_unavailable", "proof_file": None, "original_identity": None}

    def received_original_binding(self, context, *, required=True):
        require(type(required) is bool); return self.initialize_original_binding(context)

    def validate_original_association(self, context, *, target, handoff, selection_control, native_snapshot):
        self.authenticate(context)
        state = self.initialize_original_binding(context)
        plan = selection_control
        try:
            original = self.context(target["origin_episode_id"])
            require(same(plain(original.assignment), target["assignment"]))
            require(same(handoff["assignment_snapshot"]["assignment"], target["assignment"]))
            start = handoff["start_receipt"]
            job = start["outcome"]["facts"]["requested_job"]
            ident = plan["identity"]
            require(job["execution_id"] == target["execution_id"] and job["requested_job_sha256"] == target["request_sha256"]
                and job["argv"] == target["assignment"]["requested_job"]["argv"]
                and same(job["environment"], target["assignment"]["requested_job"]["environment"]))
            require(ident["run_id"] == self.run_id and ident["episode_id"] == target["origin_episode_id"]
                and ident["resource_id"] == target["resource_id"] and ident["execution_id"] == target["execution_id"]
                and ident["requested_job_sha256"] == target["request_sha256"] and ident["assignment_sha256"] == digest(target["assignment"])
                and ident["operation_key"] == start["operation_key"] and ident["attempt_id"] == digest(start["operation_key"]))
            handle, request = native_snapshot["handle"], native_snapshot["request"]
            require(handle["request_sha256"] == native_snapshot["request_file"]["sha256"]
                and same(request["command"], handle["command"]) and request["cwd"] == handle["cwd"]
                and same(handle["metadata"]["policy"], plan["policy"]))
            from .molecular_sequence_execution_contracts import molecular_sequence_adapter_argv
            invoke = native_snapshot["invoke"]
            expected = molecular_sequence_adapter_argv(plan)
            if invoke is None:
                require(handle["command"] == expected and request["env"] == plan["selected_environment"])
            else:
                root = Path(target["execution_id"]).parent
                require(handle["command"][1:] == [str(root / "invoke.py"), str(root / "invoke.json")]
                    and invoke["argv"] == expected and invoke["cwd"] == str(root)
                    and invoke["environment"] == plan["selected_environment"])
            state["original_identity"] = deepcopy(ident)
        except (ValueError, KeyError, TypeError, IndexError):
            state.update(state="conflict", reason="original_attempt_conflict")
        return state

    def _handoff(self, action):
        target, scope = action.intent["target"], action.intent["scope"]
        practical = PracticalReceiptInformation(self.store, self.run_id)
        reader = self.owner.job_progress_provider.targets
        require(same(reader.read_target(target["handle"], scope), target), "molecular_sequence_target_history_conflict")
        body = practical.read(target["handle"], scope)
        source = self.store.get(target["handle"])
        snapshot = practical._artifact_json(source["request_ref"])
        key = body["receipt"]["outcome"]["native_outcome"]["attempt_operation_key"]
        starts = practical._sources(practical._accession(target["origin_episode_id"], key)); require(len(starts) == 1)
        start_body = practical.read(starts[0]["id"], scope)
        require(start_body["receipt"]["tool_name"] == "practical.job.start" and practical._selected(start_body["receipt"])["result"] is not None)
        result = dict(source_record=source, body=body, assignment_snapshot=snapshot, start_receipt=start_body["receipt"], start_source=starts[0])
        immutable(action.directory / "handoff.json", result)
        return result

    def _capture_files(self, *, directory, declarations, capture_directory, roles=FILE_ROLES, relative_paths=None):
        """Commit successes one role at a time; never turn storage failure into absence."""
        root = Path(capture_directory); root.mkdir(parents=True, exist_ok=True)
        result = {}
        for role in roles:
            require(role in FILE_ROLES)
            selected = declarations.get(role)
            if selected is not None:
                try:
                    selected = _declaration(selected)
                except NativeFileCaptureError:
                    # Raw producer evidence stays in a private immutable
                    # control. The typed FileState carries only its failure.
                    immutable(root / ("invalid-" + role + "-" + digest(selected) + ".json"),
                        {"version": "molecular_sequence_invalid_declaration_v1", "role": role, "declaration": selected})
                    result[role] = empty_file_state("unavailable", issue=failure("schema_invalid", "capture", role=role))
                    continue
            previous = read_control(root / (role + ".json"))
            if previous is not None:
                previous = validate_file_state(previous)
                require(previous["declared"] == selected, "molecular_sequence_original_capture_selection_conflict")
                try:
                    retained_native_file(self.store, previous["file"])
                except NativeFileCaptureError as error:
                    code = "retention_failed" if error.code == "retained_artifact_unavailable" else "artifact_identity_conflict"
                    result[role] = empty_file_state("retention_failed" if code == "retention_failed" else "identity_conflict",
                        declared=selected, issue=failure(code, "capture", role=role))
                else:
                    result[role] = previous
                continue
            if selected is not None and selected["state"] == "absent":
                result[role] = empty_file_state("producer_absent", declared=selected)
                continue
            relative = selected["relative_path"] if selected is not None else (relative_paths or {}).get(role, role + ".json" if role in ("sheet", "components", "capture") else None)
            if relative is None:
                result[role] = empty_file_state("not_requested"); continue
            try:
                with self.store.transaction():
                    identity = capture_native_file(self.store, directory=str(directory), relative_path=relative,
                        format="json" if role in ("sheet", "components", "capture") else selected["format"])
            except NativeFileCaptureError as error:
                code = "producer_unavailable" if error.code == "capture_file_unavailable" else "retention_failed" if error.code == "retained_artifact_unavailable" else "artifact_identity_conflict"
                result[role] = empty_file_state(code if code != "artifact_identity_conflict" else "identity_conflict", declared=selected,
                    issue=failure(code, "capture", role=role)); continue
            if selected is not None and any(identity[key] != selected[key] for key in ("sha256", "size_bytes")):
                result[role] = empty_file_state("identity_conflict", declared=selected,
                    issue=failure("artifact_identity_conflict", "capture", role=role, source_ref=identity["artifact_ref"]))
                result[role]["observed_identity"] = {k: identity[k] for k in ("sha256", "size_bytes")}
                continue
            result[role] = _retained(identity, selected)
            immutable(root / (role + ".json"), result[role])
        return result

    def _received_sheet(self, context):
        assignment = self._context(context); reference = assignment["selector"]["saved_sheet_ref"]
        receipts = EpisodeReceipts(self.store, self.run_id)
        require(reference in set(receipts.known(context.episode_id, baseline=True)), "molecular_sequence_received_sheet_not_known")
        metadata = self.store.get(reference)
        identity = self.file_metadata(dict(artifact_ref=reference, sha256=metadata["sha256"], size_bytes=metadata["size"], format="json"))
        retained_native_file(self.store, identity)
        return identity, {"version": "molecular_sequence_received_sheet_v1", "run_id": self.run_id, "episode_id": context.episode_id,
            "context_sha256": digest(context.as_record()), "file": identity, "receipt_manifest": receipts.manifest(context.episode_id)}

    def _original_job(self, action, proof):
        """Locate one original from authenticated generic receipts, never a plan."""
        target, start = action.intent["target"], proof["start_receipt"]
        job = start["outcome"]["facts"]["requested_job"]
        detail = start["outcome"]["native_outcome"]
        key = start["operation_key"]
        require(target["run_id"] == self.run_id == start["run_id"]
            and start["episode_id"] == target["origin_episode_id"]
            and start["assignment_sha256"] == digest(target["assignment"])
            and same(proof["assignment_snapshot"]["assignment"], target["assignment"])
            and start["tool_name"] == "practical.job.start"
            and job["execution_id"] == target["execution_id"]
            and job["requested_job_sha256"] == target["request_sha256"] == digest(target["assignment"]["requested_job"])
            and same({k: job[k] for k in ("argv", "environment")}, target["assignment"]["requested_job"])
            and detail["attempt_operation_key"] == key and detail["attempt_id"] == digest(key),
            "molecular_sequence_original_job_conflict")
        return dict(version="molecular_sequence_original_job_identity_v1", run_id=self.run_id,
            origin_episode_id=target["origin_episode_id"], resource_id=target["resource_id"], resource_kind="local",
            execution_id=target["execution_id"], assignment_sha256=digest(target["assignment"]),
            requested_job_sha256=target["request_sha256"], start_operation_key=key,
            start_source_ref=proof["start_source"]["id"], attempt_id=detail["attempt_id"])

    def _original_snapshot(self, action, proof, observation):
        previous = read_control(action.directory / "original-snapshot.json")
        if previous is not None:
            return previous
        target = action.intent["target"]; root = Path(target["execution_id"]).parent
        from .molecular_sequence_execution_contracts import validate_molecular_sequence_selected_plan
        try:
            raw = read_bytes(root / "molecular-sequence-plan.json")
        except OSError as error:
            raise NativeFileCaptureError("capture_file_unavailable") from error
        plan = _json(raw)
        requested = target["assignment"]["requested_job"]
        argv = requested["argv"]; position = argv.index("--selected-payload-sha256")
        plan = validate_molecular_sequence_selected_plan(plan, expected_payload_sha256=argv[position + 1])
        require(same(plan["requested_job"], requested))
        handle_file = capture_native_file(self.store, directory=str(root), relative_path=Path(target["execution_id"]).name, format="durable_systemd_native_job_v2")
        handle = _json(read_bytes(retained_native_file(self.store, handle_file)))
        request_path = Path(handle["paths"]["request"])
        require(request_path.parent == root)
        request_file = capture_native_file(self.store, directory=str(root), relative_path=request_path.name, format="native_local_job_request")
        request = _json(read_bytes(retained_native_file(self.store, request_file)))
        invoke = _json(read_bytes(root / "invoke.json")) if (root / "invoke.json").exists() else None
        snapshot = dict(handle=handle, handle_file=handle_file, request=request, request_file=request_file, invoke=invoke,
            selected_overlay=plan["selected_environment"], invoke_overlay=None if invoke is None else invoke["environment"],
            adapter_popen_environment=plan["selected_environment"], native_outer_request_environment=request["env"],
            full_adapter_environment_observed=False, full_private_child_environment_observed=False,
            original_plan=plan, observation=observation)
        immutable(action.directory / "original-snapshot.json", snapshot)
        return snapshot

    def _validate_original_evidence(self, value, *, action, proof, original_job):
        require(type(value) is dict and set(value) == {"version", "original_job", "snapshot_file",
            "writer_observation_file", "declaration", "association"}
            and value["version"] == "molecular_sequence_original_capture_evidence_v1"
            and same(value["original_job"], original_job), "molecular_sequence_original_evidence_conflict")
        snapshot = _json(read_bytes(retained_native_file(self.store, self.file_metadata(value["snapshot_file"]))))
        observation = _json(read_bytes(retained_native_file(self.store, self.file_metadata(value["writer_observation_file"]))))
        require(type(snapshot) is dict and set(snapshot) == {"handle", "handle_file", "request", "request_file", "invoke",
            "selected_overlay", "invoke_overlay", "adapter_popen_environment", "native_outer_request_environment",
            "full_adapter_environment_observed", "full_private_child_environment_observed", "original_plan", "observation"})
        self.validate_observation(observation, action.intent)
        require(observation["native"]["terminal"] and observation["native"]["quiescent"]
            and same(snapshot["observation"], observation), "molecular_sequence_original_writer_conflict")
        from .molecular_sequence_execution_contracts import validate_molecular_sequence_selected_plan
        target = action.intent["target"]; requested = target["assignment"]["requested_job"]
        argv = requested["argv"]; position = argv.index("--selected-payload-sha256")
        plan = validate_molecular_sequence_selected_plan(snapshot["original_plan"], expected_payload_sha256=argv[position + 1])
        require(same(plan["requested_job"], requested) and plan["policy"] == POLICY
            and plan["selection"]["operation"] == action.intent["assignment"]["selector"]["operation"])
        for role in ("handle", "request"):
            stored = _json(read_bytes(retained_native_file(self.store, self.file_metadata(snapshot[role + "_file"]))))
            require(same(stored, snapshot[role]), "molecular_sequence_original_snapshot_conflict")
        require(snapshot["full_adapter_environment_observed"] is False and snapshot["full_private_child_environment_observed"] is False
            and same(snapshot["selected_overlay"], plan["selected_environment"])
            and same(snapshot["adapter_popen_environment"], plan["selected_environment"])
            and same(snapshot["native_outer_request_environment"], snapshot["request"]["env"])
            and same(snapshot["invoke_overlay"], None if snapshot["invoke"] is None else snapshot["invoke"]["environment"]))
        association = self.validate_original_association(self.context(action.intent["episode_id"]), target=target,
            handoff=proof, selection_control=plan, native_snapshot=snapshot)
        require(association["state"] == "unavailable" and same(value["association"], association),
            "molecular_sequence_original_attempt_conflict")
        declared = value["declaration"]
        require(type(declared) is dict and set(declared) == {"state", "file", "failure"}
            and declared["state"] in ("retained", "producer_unavailable", "schema_invalid"))
        if declared["state"] == "producer_unavailable":
            require(declared["file"] is None and declared["failure"] == failure("producer_unavailable", "capture"))
            declarations = {}
        else:
            raw = read_bytes(retained_native_file(self.store, self.file_metadata(declared["file"])))
            try:
                document = _json(raw)
                require(type(document) is dict and type(document.get("files")) is dict)
            except (ValueError, UnicodeError):
                require(declared["state"] == "schema_invalid" and declared["failure"] == failure("schema_invalid", "capture"))
                declarations = {}
            else:
                require(declared["state"] == "retained" and declared["failure"] is None)
                declarations = document["files"]
        return snapshot, declarations, association

    def _original_evidence(self, action, *, proof, original_job):
        """Seal controls before outputs; every collector reuses one original key."""
        root = Path(self.owner.directory) / "molecular-sequence-captures" / digest(original_job)
        with _control_directory(root, create=True) as fd, _control_regular(fd, ".original.lock", flags=os.O_RDWR | os.O_CREAT) as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                file = read_control(root / "evidence-file.json")
                value = read_control(root / "evidence.json")
                if file is not None:
                    self.file_metadata(file, value=value)
                    require(same(_json(read_bytes(retained_native_file(self.store, file))), value))
                elif value is None:
                    observation = self.observation(action)
                    if not observation["native"]["terminal"] or not observation["native"]["quiescent"]:
                        return None, None, root, failure("writer_not_closed", "authority")
                    snapshot = self._original_snapshot(action, proof, observation)
                    plan = snapshot["original_plan"]
                    association = self.validate_original_association(self.context(action.intent["episode_id"]),
                        target=action.intent["target"], handoff=proof, selection_control=plan, native_snapshot=snapshot)
                    snapshot_file = self.capture_control(action, "original-snapshot.json", snapshot, "molecular_sequence_original_snapshot_v1")
                    observation_file = self.capture_control(action, "observation.json", observation, "molecular_sequence_writer_observation_v1")
                    declaration = dict(state="producer_unavailable", file=None, failure=failure("producer_unavailable", "capture"))
                    value = dict(version="molecular_sequence_original_capture_evidence_v1", original_job=original_job,
                        snapshot_file=snapshot_file, writer_observation_file=observation_file,
                        declaration=declaration, association=association)
                    # Qualify the independent job/plan/native relationship
                    # before opening any path supplied by that plan.
                    self._validate_original_evidence(value, action=action, proof=proof, original_job=original_job)
                    try:
                        declared_file = capture_native_file(self.store, directory=str(Path(plan["attempt_directory"]) / "driver-output"),
                            relative_path="declaration.json", format="molecular_sequence_driver_declaration")
                    except NativeFileCaptureError as error:
                        if error.code != "capture_file_unavailable": raise
                    else:
                        declaration = dict(state="retained", file=declared_file, failure=None)
                        try:
                            document = _json(read_bytes(retained_native_file(self.store, declared_file)))
                            require(type(document) is dict and type(document.get("files")) is dict)
                        except (ValueError, UnicodeError):
                            declaration.update(state="schema_invalid", failure=failure("schema_invalid", "capture"))
                    value = dict(version="molecular_sequence_original_capture_evidence_v1", original_job=original_job,
                        snapshot_file=snapshot_file, writer_observation_file=observation_file,
                        declaration=declaration, association=association)
                    self._validate_original_evidence(value, action=action, proof=proof, original_job=original_job)
                    immutable(root / "evidence.json", value)
                self._validate_original_evidence(value, action=action, proof=proof, original_job=original_job)
                if file is None:
                    file = capture_native_file(self.store, directory=str(root), relative_path="evidence.json",
                        format="molecular_sequence_original_capture_evidence_v1", media_type="application/json")
                    self.file_metadata(file, value=value)
                    immutable(root / "evidence-file.json", file)
                return value, file, root, None
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _original(self, action):
        unavailable = dict(state="unavailable", reason="scientific_binding_unavailable", proof_file=None, original_identity=None)
        try:
            proof = self._handoff(action)
            original_job = self._original_job(action, proof)
            value, file, root, issue = self._original_evidence(action, proof=proof, original_job=original_job)
            if issue is not None: return None, unavailable, issue
            snapshot, declarations, association = self._validate_original_evidence(value, action=action, proof=proof, original_job=original_job)
            link = dict(version="molecular_sequence_original_capture_link_v1", intent_sha256=digest(action.intent),
                original_job_sha256=digest(original_job), evidence_file=file)
            self.capture_control(action, "original-evidence-link.json", link, link["version"])
            association["proof_file"] = self.capture_control(action, "association.json", association, "molecular_sequence_association_v1")
        except NativeFileCaptureError as error:
            code = "producer_unavailable" if error.code == "capture_file_unavailable" else "retention_failed" if error.code == "retained_artifact_unavailable" else "artifact_identity_conflict"
            return None, unavailable, failure(code, "authority")
        except OSError:
            return None, unavailable, failure("retention_failed", "authority")
        sources = self._capture_files(directory=Path(snapshot["original_plan"]["attempt_directory"]) / "driver-output",
            declarations=declarations, capture_directory=root / "roles")
        return sources, association, value["declaration"]["failure"]

    async def _worker(self, action, plan):
        """Only an explicitly selected deployment may execute a finite worker."""
        software = getattr(self.owner, "molecular_sequence_result_software", None)
        if software is None:
            return None, failure("worker_unavailable", "worker")
        from .molecular_sequence_native import _manifest
        index, _ = _manifest(software)
        require(index.get(software["python"]["path"]) == software["python"])
        for selected in index.values(): require(file_pin(selected["path"]) == selected, "molecular_sequence_worker_selected_pin_conflict")
        from .local_jobs import LocalJobPolicy
        from .native_lifecycle import NativeJobHandle, prepare_job, resume_start, wait_job
        plan_path = action.directory / "worker-plan.json"; immutable(plan_path, plan)
        pin = file_pin(plan_path)
        command = [software["python"]["path"], "-B", "-m", "gene_annotation_episode.molecular_sequence_result_worker",
            "--plan-file", str(plan_path), "--sha256", pin["sha256"], "--size-bytes", str(pin["size_bytes"]),
            "--output-directory", plan["directory"]]
        handle = NativeJobHandle(action.directory / "worker-handle.json")
        environment = {"PYTHONHOME": software["python_home"], "PYTHONPATH": ":".join(software["import_roots"]),
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"}
        policy = POLICY
        if plan["version"] == supplied.SUPPLIED_PLAN_VERSION:
            require(plan["software"] == software)
            environment, policy = plan["selected_environment"], plan["policy"]
        if not handle.path.exists():
            prepare_job(command, cwd=action.directory, policy=LocalJobPolicy(**policy), handle_path=handle.path, env=environment)
        else:
            body = handle.read(); require(body["command"] == command and body["metadata"]["policy"] == policy)
        if plan["version"] == supplied.SUPPLIED_PLAN_VERSION:
            self._supplied_worker_request(handle, command=command, cwd=action.directory, environment=environment, policy=policy)
        def finish():
            resume_start(handle)
            return wait_job(handle)
        task = asyncio.create_task(asyncio.to_thread(finish))
        try:
            execution = await asyncio.shield(task)
            immutable(action.directory / "worker-execution.json", {"returncode": execution.returncode, "metadata": execution.metadata})
            result = validate_molecular_sequence_result_worker_result(_json(read_bytes(Path(plan["directory"]) / "result.json")))
        except asyncio.CancelledError:
            while not task.done():
                try: await asyncio.shield(task)
                except asyncio.CancelledError: continue
                except BaseException: break
            if not task.cancelled(): task.exception()
            raise
        except (AcquisitionError, OSError, ValueError):
            return None, failure("worker_failed", "worker")
        require(result["plan_sha256"] == digest(plan) and same(result["selector"], plan["selector"]))
        return result, None

    def _admit_projection(self, *, selector, sources, association, calculation):
        documents = {"sheet": None, "components": None}
        issues = []
        for role in documents:
            if sources[role]["file"] is not None:
                try:
                    document = _json(read_bytes(retained_native_file(self.store, sources[role]["file"])))
                    expected = SCHEMAS[selector["operation"]][0 if role == "sheet" else 1]
                    require(type(document) is dict and (document.get("schema") == expected if role == "sheet" else document.get("schema") in expected))
                    documents[role] = document
                except (OSError, ValueError):
                    issues.append(failure("schema_invalid", "load", role=role, source_ref=sources[role]["file"]["artifact_ref"]))
        projection = select_stored_molecular_sequence_values(operation=selector["operation"], sheet=documents["sheet"],
            components=documents["components"], selection=selector, source_files=sources, association=association, calculation=calculation)
        projection["public"]["failures"].extend(issues)
        return projection

    def _publication(self, selector, sources, projection, failures):
        groups = _facts()
        if projection is not None: groups[PROJECTION_SOURCE] = validate_molecular_sequence_fact_values(PROJECTION_SOURCE, [projection["public"]])
        components_schema = None if projection is None else projection["public"]["components_schema"]
        for role in selector["return_files"]:
            if sources[role]["file"] is not None:
                groups[SAVED_SOURCE].append(dict(operation=selector["operation"], role=role, artifact_ref=sources[role]["file"]["artifact_ref"],
                    source_kind="original_stored" if selector["mode"] == MODES[0] else "selected_saved_calculation",
                    source_sheet_ref=None if sources["sheet"]["file"] is None else sources["sheet"]["file"]["artifact_ref"], components_schema=components_schema))
        groups[FAILURE_SOURCE] = unique([*failures, *(row["failure"] for row in sources.values() if row["failure"] is not None),
            *([] if projection is None else projection["public"]["failures"])])
        return groups

    def _outcome(self, receipt):
        files = receipt["facts"][SAVED_SOURCE]
        return {"status": "completed", "record_refs": [row["artifact_ref"] for row in files],
            "changed_record_refs": [row["artifact_ref"] for row in files], "feedback": None,
            "result": {"version": "molecular_sequence_public_result_v2" if receipt["version"] == "molecular_sequence_result_receipt_v2" else PUBLIC_VERSION,
                "facts": deepcopy(receipt["facts"]), "delivery_complete": receipt["delivery_complete"]}}

    async def execute(self, context, target, tool_name, arguments, operation_key):
        async with self.locked_action(context, target=target, tool_name=tool_name, arguments=arguments, operation_key=operation_key) as action:
            if action.intent["assignment"]["selector"]["version"] == supplied.SUPPLIED_SELECTOR_VERSION:
                return await self._execute_supplied(action)
            saved = read_control(action.directory / "receipt.json")
            if saved is not None: return self._outcome(self._validate_receipt(saved, action.intent))
            selector = action.intent["assignment"]["selector"]
            sources = {role: empty_file_state() for role in FILE_ROLES}
            association = dict(state="unavailable", reason="scientific_binding_unavailable", proof_file=None, original_identity=None)
            failures, projection, worker_plan, result, received_file = [], None, None, None, None
            if tool_name == "execution.results.collect":
                if selector["mode"] == MODES[0]:
                    observed, association, issue = self._original(action)
                    if observed is not None: sources = observed
                    if issue is not None: failures.append(issue)
                else:
                    identity, received = self._received_sheet(context)
                    received_file = self.capture_control(action, "received-sheet.json", received, received["version"])
                    sources["sheet"] = _retained(identity)
                worker_plan = dict(version=PLAN_VERSION, directory=str(action.directory / "worker"), selector=selector,
                    source_files=deepcopy(sources), inputs=[dict(role=role, file=row["file"], path=str(retained_native_file(self.store, row["file"])))
                        for role, row in sources.items() if row["file"] is not None], association=association, received_sheet_receipt_file=received_file,
                    software=deepcopy(getattr(self.owner, "molecular_sequence_result_software", None)),
                    selected_environment={}, policy=deepcopy(POLICY))
                if worker_plan["software"] is not None:
                    selected_software = worker_plan["software"]
                    worker_plan["selected_environment"] = {"PYTHONHOME": selected_software["python_home"], "PYTHONPATH": ":".join(selected_software["import_roots"]),
                        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"}
                try:
                    result, issue = await self._worker(action, worker_plan)
                except (AcquisitionError, OSError, ValueError):
                    result, issue = None, failure("worker_failed", "worker")
                if issue is not None: failures.append(issue)
                calculation = {"kind": "original_stored", "calculator_id": None}
                if result is not None:
                    failures.extend(result["failures"])
                if selector["mode"] == MODES[1] and Path(worker_plan["directory"]).is_dir():
                    declaration = None if result is None else next(row["declaration"] for row in result["outputs"] if row["role"] == "calculated_components")
                    sources["components"] = self._capture_files(directory=worker_plan["directory"],
                        declarations={} if declaration is None else {"components": declaration}, capture_directory=action.directory / "calculated-capture",
                        roles=("components",), relative_paths={"components": "calculated_components.json"})["components"]
                    calculation = {"kind": "selected_saved_calculation", "calculator_id": "existing_operation_specific_pure_authority"}
                # This is literal source selection after actual Store retention,
                # not a second scientific calculation or a worker success gate.
                projection = self._admit_projection(selector=selector, sources=sources, association=association, calculation=calculation)
            facts = self._publication(selector, sources, projection, failures)
            requested = plain(context.request).get("report_contract", {}).get("measurements", {}).get("schema", {"properties": {}})
            facts = {source: rows if source in select_molecular_sequence_return_facts(facts, schema=requested) else [] for source, rows in facts.items()}
            complete = bool(tool_name == "execution.results.collect" and result is not None and projection is not None
                and all(sources[role]["file"] is not None for role in selector["return_files"]))
            receipt = dict(version=VERSION, intent=action.intent, source_files=sources, association=association,
                received_sheet_receipt_file=received_file, worker_plan=worker_plan, worker_result=result,
                projection=projection, failures=failures, facts=facts, acquired_population=None, delivery_complete=complete)
            immutable(action.directory / "receipt.json", self._validate_receipt(receipt, action.intent))
            return self._outcome(receipt)

    def _validate_receipt(self, receipt, intent):
        if receipt.get("version") == "molecular_sequence_result_receipt_v2":
            return self._validate_supplied_receipt(receipt, intent)
        require(type(receipt) is dict and set(receipt) == {"version", "intent", "source_files", "association", "received_sheet_receipt_file",
            "worker_plan", "worker_result", "projection", "failures", "facts", "acquired_population", "delivery_complete"})
        require(receipt["version"] == VERSION and same(receipt["intent"], intent) and receipt["acquired_population"] is None)
        require(receipt["association"]["state"] in ("unavailable", "conflict"), "molecular_sequence_independent_scientific_binding_unavailable")
        require(set(receipt["source_files"]) == set(FILE_ROLES) and set(receipt["facts"]) == set(FACT_SOURCES))
        for row in receipt["source_files"].values():
            validate_file_state(row)
            if row["file"] is not None: self.file_metadata(row["file"])
        for source, values in receipt["facts"].items(): validate_molecular_sequence_fact_values(source, values)
        if receipt["projection"] is not None:
            validate_molecular_sequence_projection(receipt["projection"])
            require(same(receipt["projection"]["source_files"], receipt["source_files"]))
            require(same(receipt["projection"]["association"], receipt["association"]))
            require(not receipt["facts"][PROJECTION_SOURCE] or same(receipt["facts"][PROJECTION_SOURCE], [receipt["projection"]["public"]]))
        expected = self._publication(intent["assignment"]["selector"], receipt["source_files"], receipt["projection"], receipt["failures"])
        schema = plain(self.context(intent["episode_id"]).request)["report_contract"]["measurements"]["schema"]
        wanted = select_molecular_sequence_return_facts(expected, schema=schema)
        require(same(receipt["facts"], {source: rows if source in wanted else [] for source, rows in expected.items()}), "molecular_sequence_publication_conflict")
        require(type(receipt["delivery_complete"]) is bool)
        return deepcopy(receipt)

    def _completed(self, context):
        self.authenticate(context)
        result = []
        for row in self.db.execute("SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index", (self.run_id, context.episode_id)):
            action = json.loads(row["action"])
            if action.get("tool") != "execution.results.collect" or row["result"] is None: continue
            key = f'{self.run_id}:{context.episode_id}:{row["decision_index"]}'
            receipt = read_control(self.action_directory(context.episode_id, key) / "receipt.json")
            require(receipt is not None and same(json.loads(row["result"]), self._outcome(receipt)), "molecular_sequence_completed_action_conflict")
            result.append(self._validate_receipt(receipt, self.intent(context, receipt["intent"]["target"], action["tool"], {}, key)))
        return result

    def own_fact_groups(self, context, *, verify_artifacts):
        require(type(verify_artifacts) is bool and self.applies(context)); groups = _facts()
        for receipt in self._completed(context):
            if verify_artifacts:
                for row in receipt["source_files"].values():
                    if row["file"] is not None: retained_native_file(self.store, row["file"])
            for source in FACT_SOURCES: groups[source].extend(receipt["facts"][source])
        return {source: unique(rows) for source, rows in groups.items()}

    def facts(self, context):
        groups = self.own_fact_groups(context, verify_artifacts=False)
        if plain(context.assignment).get("selector", {}).get("version") == supplied.SUPPLIED_SELECTOR_VERSION:
            return {**groups, "calculation_delivery_complete": self.calculation_completion(context) is not None}
        return {**groups, "execution_completed": self.completion(context) is not None}

    def _values(self, form, schema):
        validate_form(plain(form), plain(schema), lambda *_: True)
        groups = {}
        for name, node in plain(schema)["properties"].items():
            source = node.get("x-source")
            if source in FACT_SOURCES:
                values = validate_molecular_sequence_fact_values(source, plain(form)[name])
                require(source not in groups or same(groups[source], values)); groups[source] = values
        return groups

    def _received(self, context, sources, *, allowed=None):
        self.authenticate(context); require(context.role in ("annotation", "scientific_process"))
        groups = {source: [] for source in sources}; witnesses = []
        attempts = self.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL ORDER BY decision_index", (self.run_id, context.episode_id)).fetchall()
        actual = []
        for attempt in attempts:
            witness = {k: attempt[k] for k in ("decision_index", "delivery_ref", "child_episode_id")}
            witness.update(contract_sha256=digest(json.loads(attempt["contract"])), form_sha256=digest(json.loads(attempt["form"])))
            actual.append(witness)
        if allowed is not None: require(all(any(same(w, current) for current in actual) for w in allowed), "molecular_sequence_frozen_report_prefix_conflict")
        for attempt, witness in zip(attempts, actual):
            if allowed is not None and not any(same(witness, w) for w in allowed): continue
            schema = json.loads(attempt["contract"]).get("measurements", {}).get("schema", {})
            if not any(node.get("x-source") in sources for node in schema.get("properties", {}).values()): continue
            child, form, schema = self._attempt(context, attempt["decision_index"])
            values = self._values(form, schema)
            if not any(source in values for source in sources): continue
            frozen = json.loads(self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?", (self.run_id, child.episode_id)).fetchone()[0])
            if self.applies(child): expected = self.own_fact_groups(child, verify_artifacts=False)
            else:
                require(PREFIX in frozen, "molecular_sequence_frozen_report_prefix_required")
                expected, _ = self._received(child, sources, allowed=_validate_report_prefix(frozen[PREFIX])["attempts"])
            for source in sources:
                for value in values.get(source, []):
                    require(any(same(value, item) for item in expected.get(source, [])), "molecular_sequence_returned_value_conflict")
                    groups[source].append(value)
            witnesses.append(witness)
        return {source: unique(values) for source, values in groups.items()}, witnesses

    def received_facts(self, context, schema):
        sources = tuple(select_molecular_sequence_return_facts(_facts(), schema=plain(schema)))
        groups = self.own_fact_groups(context, verify_artifacts=False) if self.applies(context) else self._received(context, sources)[0]
        return select_molecular_sequence_return_facts(groups, schema=plain(schema))

    def facts_for_closure(self, context, schema):
        if self.applies(context): return self.received_facts(context, schema)
        sources = tuple(select_molecular_sequence_return_facts(_facts(), schema=plain(schema)))
        frozen = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?", (self.run_id, context.episode_id)).fetchone()
        allowed = None if frozen is None else _validate_report_prefix(json.loads(frozen[0])[PREFIX])["attempts"]
        groups, witnesses = self._received(context, sources, allowed=allowed)
        return {**select_molecular_sequence_return_facts(groups, schema=plain(schema)), PREFIX: _validate_report_prefix({"version": RECEIVED_REPORT_PREFIX_VERSION, "attempts": witnesses})}

    def validate_received_report(self, context, form, schema):
        values = self._values(form, schema)
        if not values: return
        frozen = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?", (self.run_id, context.episode_id)).fetchone()
        if self.applies(context): expected = self.own_fact_groups(context, verify_artifacts=frozen is None)
        else:
            allowed = None if frozen is None else _validate_report_prefix(json.loads(frozen[0])[PREFIX])["attempts"]
            expected = self._received(context, values, allowed=allowed)[0]
        for source, rows in values.items(): require(all(any(same(row, original) for original in expected.get(source, [])) for row in rows), "molecular_sequence_returned_value_conflict")

    def record_admission(self, context, form, schema, operation_key):
        child, actual, declared = self._attempt(context, self._admission_index(context, operation_key))
        require(same(form, actual) and same(schema, declared))
        self.validate_received_report(child, actual, declared)
        return list(dict.fromkeys(row["artifact_ref"] for row in self._values(actual, declared).get(SAVED_SOURCE, [])))

    def resolve_own(self, context, reference, namespace):
        return namespace in (None, "artifact") and self.applies(context) and any(row["artifact_ref"] == reference for row in self.own_fact_groups(context, verify_artifacts=False)[SAVED_SOURCE])

    def resolve_received(self, context, reference, namespace):
        return namespace in (None, "artifact") and context.role in ("annotation", "scientific_process") and any(row["artifact_ref"] == reference for row in self._received(context, (SAVED_SOURCE,))[0][SAVED_SOURCE])

    def owns_reference(self, reference):
        if type(reference) is not str or not reference.startswith("artifact_"): return False
        for row in self.db.execute("SELECT episode_id,decision_index,action,result FROM runtime_actions WHERE run_id=? AND result IS NOT NULL", (self.run_id,)):
            value = json.loads(row["result"])
            if value.get("result", {}).get("version") not in (PUBLIC_VERSION, "molecular_sequence_public_result_v2"): continue
            receipt = read_control(self.action_directory(row["episode_id"], f'{self.run_id}:{row["episode_id"]}:{row["decision_index"]}') / "receipt.json")
            require(receipt is not None)
            if value["result"]["version"] == "molecular_sequence_public_result_v2":
                context = self.context(row["episode_id"])
                action = json.loads(row["action"])
                intent = self.intent(context, None, action.get("tool"), action.get("arguments"),
                    f'{self.run_id}:{row["episode_id"]}:{row["decision_index"]}')
                receipt = self._validate_supplied_receipt(receipt, intent)
                require(same(value, self._outcome(receipt)), "molecular_sequence_completed_action_conflict")
                if self._supplied_produced_component(receipt) == reference: return True
                continue
            if any(source["file"] is not None and source["file"]["artifact_ref"] == reference for source in receipt["source_files"].values()): return True
        return False

    def credit_view(self, context, receiver_selection):
        if plain(context.assignment).get("selector", {}).get("version") == supplied.SUPPLIED_SELECTOR_VERSION:
            # This reports acquisition only. Investigation value and the
            # configured controller's credit/continuation are not estimated.
            return {"new_acquired_record_count": 0, "new_handoff_count": 0,
                "operational_credit_binding": {"version": supplied.CALCULATION_RECORD_VERSION,
                    "basis": "supplied_measurements_without_native_acquisition"}}
        # No authenticated original scientific producer hook exists here yet.
        # This says nothing about investigation value or parent scientific yield.
        return {"credit": 0, "operational_credit": 0, "new_acquired_record_count": 0, "new_handoff_count": 0,
            "operational_credit_binding": {"version": VERSION, "basis": "no_verified_original_molecular_acquisition"}}

    def completion(self, context):
        if plain(context.assignment).get("selector", {}).get("version") == supplied.SUPPLIED_SELECTOR_VERSION:
            return None  # No invented original practical/native receipt.
        for receipt in self._completed(context):
            if receipt["delivery_complete"]:
                return dict(version="practical_completion_v1", run_id=self.run_id, episode_id=context.episode_id,
                    assignment_sha256=digest(plain(context.assignment)), endpoint="usable_handoff", operation_key=receipt["intent"]["operation_key"],
                    receipt_sha256=digest(receipt), validation_keys=["selected_molecular_typed_delivery"])
        return None

    def _supplied_record(self, action):
        selector = action.intent["assignment"]["selector"]
        calculation = selector["action"] == "calculate"
        constraints = action.intent["assignment"]["constraints"]
        return dict(version=supplied.CALCULATION_RECORD_VERSION, operation=supplied.SUPPLIED_OPERATION,
            kind="selected_supplied_calculation" if calculation else "admitted_stored_read", input_evidence_files={},
            input_sheet_file=None, selection=deepcopy(selector["calculation_selection"]), software=None,
            selected_environment={}, policy=deepcopy(constraints["policy"]) if calculation else None,
            worker_plan_file=None, worker_result_file=None, worker_diagnostics_file=None,
            source_files={role: empty_file_state("not_requested") for role in FILE_ROLES},
            worker_outputs={role: empty_file_state("not_requested") for role in ("sheet", "components")},
            calculation_state="input_unavailable" if calculation else "stored_read", calculation_call_count=0,
            origin_state="selected_action_only" if calculation else "admitted_stored_unverified", linkage_state="not_assessed",
            validation_states={role: "unavailable" for role in ("sheet", "components")},
            native_invocation="not_requested", acquired_population=None, failures=[])

    def _supplied_received(self, action, role, selection, *, interpret_sheet):
        """Freeze this selected action's actual current admission, never an alias replay."""
        from .molecular_sequence_input_bindings import MolecularSequenceInputBindings
        from .molecular_sequence_input_contracts import validate_molecular_sequence_received_input
        from .calibrated_signal_sheet import read_calibrated_signal_inputs, validate_calibrated_signal_input_read
        path = action.directory / ("supplied-" + role + "-input.json")
        value = read_control(path)
        if value is None:
            context = self.context(action.intent["episode_id"])
            binding = MolecularSequenceInputBindings(self.owner)
            def read(reference, namespace):
                return binding.read_received(context, reference, namespace, tag_key="version")
            evidence = (read_calibrated_signal_inputs(selection["reference"], namespace=selection["namespace"], read_input=read)
                if interpret_sheet else read(selection["reference"], selection["namespace"]))
            value = dict(version="molecular_sequence_supplied_input_evidence_v1", intent_sha256=digest(action.intent),
                role=role, interpret_sheet=interpret_sheet, evidence=evidence)
            immutable(path, value)
        require(type(value) is dict and set(value) == {"version", "intent_sha256", "role", "interpret_sheet", "evidence"}
            and value["version"] == "molecular_sequence_supplied_input_evidence_v1"
            and value["intent_sha256"] == digest(action.intent) and value["role"] == role
            and value["interpret_sheet"] is interpret_sheet, "molecular_sequence_supplied_input_control_conflict")
        evidence = (validate_calibrated_signal_input_read(value["evidence"]) if interpret_sheet
            else validate_molecular_sequence_received_input(value["evidence"]))
        received = evidence["received_input"] if interpret_sheet else evidence
        require(received["selection"] == selection, "molecular_sequence_supplied_input_selection_conflict")
        file = self.capture_control(action, path.name, value, "molecular_sequence_supplied_input_evidence_v1")
        return evidence, received, file

    def _supplied_input(self, action, record):
        from .calibrated_signal_contracts import validate_calibrated_signal_selection
        selected = action.intent["assignment"]["selector"]
        try:
            evidence, received, file = self._supplied_received(action, "sheet", selected["input"], interpret_sheet=True)
        except (OSError, NativeFileCaptureError):
            record["failures"].append(supplied.supplied_failure("retention_failed", "capture", role="sheet")); return None
        record["input_evidence_files"]["sheet"] = file
        admitted = received["input"]
        if admitted is not None:
            identity = self.file_metadata(admitted["file"])
            record["input_sheet_file"] = identity
            if admitted["byte_verification"] == "verified":
                record["source_files"]["sheet"] = _retained(identity)
            else:
                record["source_files"]["sheet"] = empty_file_state("identity_conflict" if admitted["byte_verification"] == "identity_conflict" else "unavailable")
        if evidence["sheet"] is None:
            record["validation_states"]["sheet"] = "invalid" if admitted is not None else "unavailable"
            code = ("input_unavailable" if admitted is None or admitted["byte_verification"] == "unavailable" else
                "artifact_identity_conflict" if admitted["byte_verification"] == "identity_conflict" else "input_invalid")
            record["failures"].append(supplied.supplied_failure(code, "load", role="sheet"))
            return None
        record["validation_states"]["sheet"] = "valid"
        try:
            validate_calibrated_signal_selection(selected["calculation_selection"], evidence["sheet"])
        except ValueError:
            record["calculation_state"] = "selection_invalid"
            record["failures"].append(supplied.supplied_failure("selection_invalid", "selection", role="sheet")); return None
        return evidence

    def _stored_supplied(self, action, record):
        from .calibrated_signal_contracts import (validate_calibrated_signal_sheet,
            validate_calibrated_signal_selection, validate_calibrated_signal_components_shape)
        documents = {"sheet": None, "components": None}
        for role, selected in action.intent["assignment"]["selector"]["stored"].items():
            if selected is None: continue
            try:
                _evidence, received, file = self._supplied_received(action, role, selected, interpret_sheet=False)
            except (OSError, NativeFileCaptureError):
                record["failures"].append(supplied.supplied_failure("retention_failed", "capture", role=role)); continue
            record["input_evidence_files"][role] = file
            admitted = received["input"]
            if admitted is None:
                record["failures"].append(supplied.supplied_failure("input_unavailable", "authority", role=role)); continue
            if admitted["byte_verification"] == "verified":
                record["source_files"][role] = _retained(self.file_metadata(admitted["file"]))
            else:
                record["source_files"][role] = empty_file_state("identity_conflict" if admitted["byte_verification"] == "identity_conflict" else "unavailable")
            if role == "sheet": record["input_sheet_file"] = admitted["file"]
            try:
                require(admitted["byte_verification"] == "verified" and admitted["content"]["state"] == "decoded")
                document = admitted["content"]["value"]
                if role == "sheet": validate_calibrated_signal_sheet(document)
                else:
                    validate_calibrated_signal_components_shape(document)
                    validate_calibrated_signal_sheet(document["sheet"])
                    validate_calibrated_signal_selection(document["selection"], document["sheet"])
            except ValueError:
                record["validation_states"][role] = "invalid"
                record["failures"].append(supplied.supplied_failure("schema_invalid", "load", role=role,
                    source_ref=admitted["file"]["artifact_ref"])); continue
            record["validation_states"][role] = "valid"; documents[role] = document
        if documents["sheet"] is None: record["linkage_state"] = "sheet_unavailable"
        elif documents["components"] is None: record["linkage_state"] = "components_unavailable"
        elif same(documents["sheet"], documents["components"]["sheet"]): record["linkage_state"] = "matched"
        else:
            record["linkage_state"] = "conflict"
            record["failures"].append(supplied.supplied_failure("stored_linkage_conflict", "load", role="components",
                source_ref=record["source_files"]["components"]["file"]["artifact_ref"], source_pointer="/sheet"))
        # Shape, byte identity and cross-file equality are not a selected
        # original-calculator receipt. Full stored numerical data stay literal.
        return documents

    async def _supplied_calculation(self, action, record, admitted):
        selector, constraints = action.intent["assignment"]["selector"], action.intent["assignment"]["constraints"]
        software = deepcopy(getattr(self.owner, "molecular_sequence_result_software", None))
        environment = {} if software is None else {"PYTHONHOME": software["python_home"], "PYTHONPATH": ":".join(software["import_roots"]),
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"}
        requested = constraints["environment"]
        if any(key in environment and environment[key] != value for key, value in requested.items()) or software is None and requested:
            record["failures"].append(supplied.supplied_failure("environment_conflict", "worker")); return
        environment.update(requested)
        record.update(software=software, selected_environment=environment, calculation_state="not_started")
        identity = record["input_sheet_file"]
        plan = dict(version=supplied.SUPPLIED_PLAN_VERSION, directory=str(action.directory / "worker"), selector=selector,
            input_file=identity, input_path=str(retained_native_file(self.store, identity)),
            input_evidence_file=record["input_evidence_files"]["sheet"], software=software,
            selected_environment=environment, policy=constraints["policy"])
        supplied.validate_supplied_worker_plan(plan)
        record["worker_plan_file"] = self.capture_control(action, "supplied-worker-plan.json", plan, supplied.SUPPLIED_PLAN_VERSION)
        # Work may already have completed before its control can be retained.
        # Only explicit no-start or retained completed evidence supplies0/1.
        record.update(calculation_state="worker_uncertain", calculation_call_count=None)
        sealed = read_control(action.directory / "supplied-worker-result.json")
        issue = None
        if sealed is None:
            try:
                result, issue = await self._worker(action, plan)
            except (AcquisitionError, OSError, ValueError):
                result, issue = None, failure("worker_failed", "worker")
            if result is not None:
                supplied.validate_supplied_worker_result(result)
                require(result["plan_sha256"] == digest(plan) and same(result["selector"], selector))
                immutable(action.directory / "supplied-worker-result.json", result)
        else:
            result = supplied.validate_supplied_worker_result(sealed)
            require(result["plan_sha256"] == digest(plan) and same(result["selector"], selector))
        if result is None:
            uncertain = issue is None or issue["code"] != "worker_unavailable"
            record.update(calculation_state="worker_uncertain" if uncertain else "worker_failed",
                calculation_call_count=None if uncertain else 0)
            record["failures"].append(supplied.supplied_failure("worker_uncertain" if uncertain else
                "worker_unavailable" if issue is not None and issue["code"] == "worker_unavailable" else "worker_failed", "worker"))
            return
        record["worker_result_file"] = self.capture_control(action, "supplied-worker-result.json", result, supplied.SUPPLIED_RESULT_VERSION)
        record["failures"].extend(result["failures"])
        declarations = {row["role"]: row["declaration"] for row in result["outputs"]}
        record["calculation_call_count"] = None  # No inference from pre-call intent.
        try:
            declared = declarations["diagnostics"]
            require(declared["state"] == "present")
            file = capture_native_file(self.store, directory=plan["directory"], relative_path=declared["relative_path"], format="json")
            require(all(file[key] == declared[key] for key in ("sha256", "size_bytes")))
            from .molecular_sequence_result_worker import _strict_json
            diagnostic = _strict_json(read_bytes(retained_native_file(self.store, file)))
            require(type(diagnostic) is dict and set(diagnostic) == {"version", "operation", "calculator_id", "selection",
                "calculation_state", "calculation_call_count", "native_invocation", "software_before", "software_after", "failures"}
                and diagnostic["version"] == "molecular_sequence_supplied_worker_diagnostics_v1"
                and diagnostic["operation"] == supplied.SUPPLIED_OPERATION and diagnostic["calculator_id"] == supplied.SUPPLIED_PROFILE["calculator_id"]
                and diagnostic["native_invocation"] == "not_requested" and same(diagnostic["selection"], selector["calculation_selection"]))
            count = diagnostic["calculation_call_count"]
            require(count is None or type(count) is int and count in (0, 1))
            record.update(worker_diagnostics_file=file, calculation_call_count=count, calculation_state=diagnostic["calculation_state"])
            if count == 1: record["origin_state"] = "selected_calculation_recorded"
        except (OSError, ValueError):
            record["calculation_state"] = "worker_failed"
            record["failures"].append(supplied.supplied_failure("retention_failed", "capture"))
        captured = self._capture_files(directory=plan["directory"], declarations={"sheet": declarations["sheet"],
            "components": declarations["calculated_components"]}, capture_directory=action.directory / "supplied-output-capture",
            roles=("sheet", "components"))
        record["worker_outputs"] = captured
        # Original supplied sheet custody is independent of a failed duplicate
        # worker-sheet capture. Components are published only after retention.
        record["source_files"]["components"] = captured["components"]
        for role, state in captured.items():
            if state["failure"] is not None:
                code = "artifact_identity_conflict" if state["state"] == "identity_conflict" else "retention_failed"
                record["failures"].append(supplied.supplied_failure(code, "capture", role=role))
        if captured["components"]["file"] is not None:
            from .calibrated_signal_contracts import validate_calibrated_signal_components_shape
            from .molecular_sequence_result_worker import _strict_json
            try:
                components = validate_calibrated_signal_components_shape(_strict_json(read_bytes(retained_native_file(self.store, captured["components"]["file"]))))
                require(same(components["sheet"], admitted["sheet"]) and same(components["selection"], selector["calculation_selection"]))
            except ValueError:
                record["validation_states"]["components"] = "invalid"
                record["failures"].append(supplied.supplied_failure("schema_invalid", "load", role="components"))
            else:
                record["validation_states"]["components"] = "valid"; record["linkage_state"] = "matched"
        else: record["linkage_state"] = "components_unavailable"

    def _supplied_publication(self, selector, record):
        groups = _facts()
        has_components = record["validation_states"]["components"] == "valid"
        for role in selector["return_files"]:
            file = record["source_files"][role]["file"]
            if file is None: continue
            groups[SAVED_SOURCE].append(dict(version="molecular_sequence_retained_file_v2", operation=supplied.SUPPLIED_OPERATION,
                role=role, artifact_ref=file["artifact_ref"], source_kind="admitted_stored" if selector["action"] == "read_stored"
                else "admitted_input" if role == "sheet" else "selected_supplied_calculation",
                source_sheet_ref=None if record["source_files"]["sheet"]["file"] is None else record["source_files"]["sheet"]["file"]["artifact_ref"],
                components_tag_key="version" if has_components else None,
                components_version=supplied.SUPPLIED_PROFILE["components_version"] if has_components else None,
                validation_state=record["validation_states"][role], calculation_origin=record["origin_state"], linkage_state=record["linkage_state"]))
        groups[FAILURE_SOURCE] = unique([supplied.supplied_failure_view(issue) for issue in record["failures"]])
        return groups

    async def _execute_supplied(self, action):
        saved = read_control(action.directory / "receipt.json")
        if saved is not None: return self._outcome(self._validate_supplied_receipt(saved, action.intent))
        selector = action.intent["assignment"]["selector"]
        record = read_control(action.directory / "calculation-record.json")
        if record is not None:
            record = supplied.validate_molecular_sequence_calculation_record(record)
        else:
            record = self._supplied_record(action)
        if not (action.directory / "calculation-record.json").exists() and action.intent["tool_name"] == "execution.results.collect":
            if selector["action"] == "read_stored": self._stored_supplied(action, record)
            else:
                admitted = self._supplied_input(action, record)
                if admitted is not None:
                    try: await self._supplied_calculation(action, record, admitted)
                    except (NativeFileCaptureError, OSError):
                        record["failures"].append(supplied.supplied_failure("retention_failed", "capture"))
        elif selector["action"] == "read_stored":
            record["calculation_state"] = "stored_read"
        record = supplied.validate_molecular_sequence_calculation_record(record)
        file = self.capture_control(action, "calculation-record.json", record, supplied.CALCULATION_RECORD_VERSION)
        all_facts = self._supplied_publication(selector, record)
        schema = plain(self.context(action.intent["episode_id"]).request)["report_contract"]["measurements"]["schema"]
        selected = select_molecular_sequence_return_facts(all_facts, schema=schema)
        facts = {source: rows if source in selected else [] for source, rows in all_facts.items()}
        complete = action.intent["tool_name"] == "execution.results.collect" and all(
            any(row["role"] == role for row in facts[SAVED_SOURCE]) for role in selector["return_files"])
        receipt = dict(version="molecular_sequence_result_receipt_v2", intent=action.intent, calculation_record=record,
            calculation_record_file=file, source_files=record["source_files"], facts=facts, delivery_complete=bool(complete))
        immutable(action.directory / "receipt.json", self._validate_supplied_receipt(receipt, action.intent))
        return self._outcome(receipt)

    def _validate_supplied_receipt(self, value, intent):
        require(type(value) is dict and set(value) == {"version", "intent", "calculation_record", "calculation_record_file", "source_files", "facts", "delivery_complete"}
            and value["version"] == "molecular_sequence_result_receipt_v2" and same(value["intent"], intent))
        record = supplied.validate_molecular_sequence_calculation_record(value["calculation_record"])
        selector = intent["assignment"]["selector"]
        require(record["operation"] == selector["operation"] and same(record["selection"], selector["calculation_selection"]))
        if selector["action"] == "calculate":
            require(record["kind"] == "selected_supplied_calculation"
                and same(record["policy"], intent["assignment"]["constraints"]["policy"]))
        else: require(record["kind"] == "admitted_stored_read")
        for role, evidence_file in record["input_evidence_files"].items():
            control = _json(read_bytes(retained_native_file(self.store, self.file_metadata(evidence_file))))
            require(control["intent_sha256"] == digest(intent) and control["role"] == role)
            received = control["evidence"]["received_input"] if control["interpret_sheet"] else control["evidence"]
            selected = selector["input"] if selector["action"] == "calculate" else selector["stored"][role]
            require(received["selection"] == selected)
            source = record["source_files"][role]
            require(source["file"] is None or received["input"] is not None
                and received["input"]["byte_verification"] == "verified" and source["file"] == received["input"]["file"])
        if record["worker_plan_file"] is not None:
            plan = supplied.validate_supplied_worker_plan(_json(read_bytes(retained_native_file(self.store,
                self.file_metadata(record["worker_plan_file"])))))
            require(same(plan["selector"], selector) and same(plan["input_file"], record["input_sheet_file"])
                and same(plan["software"], record["software"]) and same(plan["selected_environment"], record["selected_environment"])
                and same(plan["policy"], record["policy"]))
            if record["worker_result_file"] is not None:
                result = supplied.validate_supplied_worker_result(_json(read_bytes(retained_native_file(self.store,
                    self.file_metadata(record["worker_result_file"])))))
                require(result["plan_sha256"] == digest(plan) and same(result["selector"], selector))
        if record["worker_diagnostics_file"] is not None:
            diagnostic = _json(read_bytes(retained_native_file(self.store, self.file_metadata(record["worker_diagnostics_file"]))))
            require(diagnostic["calculation_call_count"] == record["calculation_call_count"]
                and same(diagnostic["selection"], selector["calculation_selection"]) and diagnostic["native_invocation"] == "not_requested")
        file = self.file_metadata(value["calculation_record_file"], value=record)
        require(same(_json(read_bytes(retained_native_file(self.store, file))), record))
        require(same(value["source_files"], record["source_files"]))
        expected = self._supplied_publication(intent["assignment"]["selector"], record)
        schema = plain(self.context(intent["episode_id"]).request)["report_contract"]["measurements"]["schema"]
        wanted = select_molecular_sequence_return_facts(expected, schema=schema)
        require(same(value["facts"], {source: rows if source in wanted else [] for source, rows in expected.items()})
            and type(value["delivery_complete"]) is bool)
        require(value["delivery_complete"] == bool(intent["tool_name"] == "execution.results.collect" and all(
            any(row["role"] == role for row in value["facts"][SAVED_SOURCE]) for role in selector["return_files"])))
        return deepcopy(value)

    def calculation_completion(self, context):
        """Private delivered-file endpoint, never an original practical receipt."""
        for receipt in self._completed(context):
            if receipt["version"] == "molecular_sequence_result_receipt_v2" and receipt["delivery_complete"]:
                return {"version": "molecular_sequence_calculation_delivery_v1", "operation": supplied.SUPPLIED_OPERATION,
                    "endpoint": "requested_scientific_files_delivered"}
        return None

    def _supplied_worker_request(self, handle, *, command, cwd, environment, policy):
        """Check the actual selected launcher input, not a full process env."""
        body = handle.read(); cwd = Path(cwd)
        path = Path(body["paths"]["request"])
        require(path.parent == cwd and body["command"] == command and body["cwd"] == str(cwd)
            and body["metadata"]["policy"] == policy, "molecular_sequence_worker_request_conflict")
        raw = read_bytes(path)
        require(hashlib.sha256(raw).hexdigest() == body["request_sha256"], "molecular_sequence_worker_request_identity_conflict")
        request = _json(raw)
        require(request["command"] == command and request["cwd"] == str(cwd)
            and request["env"] == environment and request["file_bytes"] == policy["scratch_bytes"],
            "molecular_sequence_worker_environment_conflict")
        return request

    def _supplied_produced_component(self, receipt):
        """Classify produced bytes only; reading an input creates no ownership."""
        record = receipt["calculation_record"]
        if record["kind"] != "selected_supplied_calculation" or record["worker_result_file"] is None: return None
        produced = record["worker_outputs"]["components"]
        source = record["source_files"]["components"]
        if produced["state"] != "retained" or produced["file"] is None: return None
        require(produced["file"] == source["file"], "molecular_sequence_supplied_output_ownership_conflict")
        result = supplied.validate_supplied_worker_result(_json(read_bytes(retained_native_file(self.store,
            self.file_metadata(record["worker_result_file"])))))
        declaration = next(row["declaration"] for row in result["outputs"] if row["role"] == "calculated_components")
        require(declaration["state"] == "present" and produced["declared"] == declaration
            and all(produced["file"][key] == declaration[key] for key in ("sha256", "size_bytes")),
            "molecular_sequence_supplied_output_ownership_conflict")
        return produced["file"]["artifact_ref"]
