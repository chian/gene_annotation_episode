"""Original molecular result responsibility: molecular_result_original_evidence."""
from __future__ import annotations
from copy import deepcopy
import fcntl
import os
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.communication import plain
from .episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.native_control_records import immutable, read_control, same
from gene_annotation_episode.native_control_records import directory as _control_directory, regular as _control_regular
from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_result_contracts import FILE_ROLES, empty_file_state, failure, require, validate_file_state
from gene_annotation_episode.native_file_capture import NativeFileCaptureError, capture_native_file, retained_native_file, _declaration
from .library.retained_file_read import read_bytes
from .practical_receipt_information import PracticalReceiptInformation
from .molecular_result_values import POLICY, _json, _retained

class MolecularResultOriginalEvidence:

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
            from gene_annotation_episode.molecular_sequence_execution_contracts import molecular_sequence_adapter_argv
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
        from gene_annotation_episode.molecular_sequence_execution_contracts import validate_molecular_sequence_selected_plan
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
        from gene_annotation_episode.molecular_sequence_execution_contracts import validate_molecular_sequence_selected_plan
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
