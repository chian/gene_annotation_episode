"""Original molecular result responsibility: molecular_result_custody."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from .episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.native_control_records import immutable, read_control, same
from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_result_contracts import FAILURE_SOURCE, FILE_ROLES, empty_file_state, failure, require
from gene_annotation_episode.native_file_capture import NativeFileCaptureError, capture_native_file, retained_native_file, _declaration
from .library.retained_file_pin import file_pin
from .library.retained_file_read import read_bytes
from gene_annotation_episode.episodic_workflow.root.library import molecular_sequence_result_contracts as supplied
from .molecular_result_values import POLICY, _json

class MolecularResultCustody:

    def _ordinary_capture_path(self, path, format_name, *, pin=None):
        path = Path(path)
        with self.store.transaction():
            file = capture_native_file(self.store, directory=str(path.parent), relative_path=path.name, format=format_name)
        if pin is not None:
            require(all(file[key] == pin[key] for key in ("sha256", "size_bytes")),
                "molecular_sequence_ordinary_control_identity_conflict")
        return file

    def _ordinary_value(self, file):
        return _json(read_bytes(retained_native_file(self.store, self.file_metadata(file))))

    def _ordinary_retained_metadata(self, plan, original):
        """Use the one existing metadata parser against retained original bytes."""
        from gene_annotation_episode import molecular_sequence_ordinary as ordinary
        attempt = Path(plan["attempt_directory"])
        files = {str(attempt / "attempt-bundle.json"): original["bundle_file"],
            str(attempt / "driver-output" / "declaration.json"): original["declaration_file"]}
        def read(path):
            selected = files[str(path)]
            if selected is None:
                raise FileNotFoundError(str(path))
            return self._ordinary_value(selected)
        return ordinary._result_metadata(plan, read_json=read)

    def _ordinary_match_metadata(self, execution, metadata, *, original):
        bundle, declaration, declarations, _issues = metadata
        # Unavailable/malformed metadata remains qualified byte evidence. Only
        # independently parsed valid metadata can authenticate carrier claims.
        if bundle is not None:
            require(same(bundle, execution["bundle"]), "molecular_sequence_ordinary_original_metadata_conflict")
        if declaration is not None:
            require(same(declaration, execution["declaration"]) and same(declarations, execution["declarations"]),
                "molecular_sequence_ordinary_original_metadata_conflict")
            if bundle is not None:
                observed = next(row for row in bundle["files"] if row["role"] == "declaration")["observed"]
                require(observed is not None and original["declaration_file"] is not None and all(
                    observed[key] == original["declaration_file"][key] for key in ("sha256", "size_bytes")),
                    "molecular_sequence_ordinary_original_metadata_conflict")

    def _ordinary_bundle_role_states(self, sources, bundle):
        """Qualify actual retained bytes against independent original observations."""
        result = deepcopy(sources)
        if bundle is None:
            return result
        observed = {row["role"]: row for row in bundle["files"]}
        for role in ("capture", "sheet", "components"):
            state, observation = result[role], observed.get(role)
            file = state["file"]
            if file is None or observation is None or observation["observed_state"] == "unavailable":
                continue
            pin = observation["observed"]
            if observation["observed_state"] == "present" and all(file[key] == pin[key] for key in ("sha256", "size_bytes")):
                continue
            result[role] = empty_file_state("identity_conflict", declared=state["declared"],
                issue=failure("artifact_identity_conflict", "capture", role=role, source_ref=file["artifact_ref"]))
            result[role]["observed_identity"] = {key: file[key] for key in ("sha256", "size_bytes")}
        return result

    def _ordinary_failed_capture_refs(self, sources):
        """Index only captured failures whose typed observation matches Store metadata."""
        references = []
        for role in ("capture", "sheet", "components"):
            state = sources[role]
            issue, observed = state["failure"], state["observed_identity"]
            if (state["state"] != "identity_conflict" or state["file"] is not None or observed is None or issue is None
                    or issue["code"] != "artifact_identity_conflict" or issue["stage"] != "capture" or issue["role"] != role
                    or issue["source_ref"] != "artifact_" + observed["sha256"]):
                continue
            try:
                self.file_metadata(dict(artifact_ref=issue["source_ref"], format="json", **observed))
            except (ValueError, KeyError):
                continue
            references.append(issue["source_ref"])
        return references

    def _placement_context(self, sources, *, operand=None, parent_context=None):
        """Copy authenticated stored input/population facts, without calculation."""
        from gene_annotation_episode.episodic_workflow.root.library.primer_placement_result_contracts import context, native_arguments, operand_files, scientific_context
        documents = {}
        for role in ("sheet", "components"):
            file = sources[role]["file"]
            try:
                documents[role] = None if file is None else self._ordinary_value(file)
            except (OSError, ValueError, UnicodeError):
                documents[role] = None
        original_files = None if parent_context is None else parent_context["original_operand_files"]
        frozen_input = None if parent_context is None else parent_context["input"]
        if operand is not None:
            primers = operand["primers"]
            args = dict(target_ref=operand["target"]["subject"]["id"],
                primer_refs=[row["subject"]["id"] for row in primers] if type(primers) is list else primers["subject"]["id"])
            native = native_arguments(args, operand)
            frozen_input = dict(target_sequence=native["long_seq"], primers=native["short_seqs"], **scientific_context(args, operand))
            original_files = operand_files(operand)
        return context(sheet=documents["sheet"], components=documents["components"], source_files=sources,
            original_files=original_files, frozen_input=frozen_input)

    def _validate_ordinary_molecular_sequence_custody(self, custody, intent, *, _seen=()):
        operation = intent["tool_name"]
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        if type(custody) is dict and custody.get("version") == profile['saved_custody_version']:
            return self._validate_ordinary_molecular_sequence_saved_custody(custody, intent, _seen=_seen)
        custody = supplied.validate_ordinary_molecular_sequence_custody(custody, operation=operation)
        require(custody["intent"] == intent, "molecular_sequence_ordinary_custody_intent_conflict")
        original = custody["original"]
        binding = self._ordinary_value(custody["request"]["input_binding_file"])
        execution = supplied.validate_ordinary_molecular_sequence_execution(self._ordinary_value(original["execution_file"]), operation=operation)
        producer = EpisodeReturnRecords(self.store, intent["run_id"], failure_prefix="molecular_sequence_ordinary_").context(intent["episode_id"])
        require(binding["context"] == producer.as_record()
            and binding["arguments"] == intent["arguments"] and binding["operation_key"] == intent["operation_key"]
            and execution["plan"]["identity"] == original["identity"], "molecular_sequence_ordinary_binding_conflict")
        from gene_annotation_episode import molecular_sequence_ordinary as ordinary
        ordinary._closed(binding, ("version", "context", "operation_key", "arguments", "frozen_operand", "selected", "policy"),
            "retained_binding_fields_invalid")
        ordinary._closed(binding["selected"], ("resource_id", "workspace", "deployment", "software", "environment"),
            "retained_selection_fields_invalid")
        ordinary._deployment(operation, binding["selected"]["deployment"])
        operand = ordinary._operand(binding["frozen_operand"], intent["arguments"] if operation == "align_sequences" else intent["arguments"]["subject_ref"], operation=operation)
        plan = execution["plan"]
        require(set(binding) == {"version", "context", "operation_key", "arguments", "frozen_operand", "selected", "policy"}
            and binding["version"] == profile["binding_version"] and binding["policy"] == POLICY
            and all(plan["identity"][key] == intent[key] for key in ("run_id", "episode_id", "operation_key"))
            and plan["identity"]["assignment_sha256"] == digest(intent["assignment"])
            and binding["selected"]["software"] == plan["software"]
            and binding["selected"]["environment"] == ordinary.ENVIRONMENT_SELECTION
            and binding["selected"]["resource_id"] == plan["identity"]["resource_id"]
            and binding["selected"]["deployment"] == plan["selection"]["driver_request"]["selection"]["deployment"],
            "molecular_sequence_ordinary_plan_binding_conflict")
        for retained, selected in ((custody["request"]["input_binding_file"], execution["binding_file"]),
                (original["plan_file"], execution["plan_file"]), (original["driver_request_file"], execution["driver_request_file"])):
            require(all(retained[key] == selected[key] for key in ("sha256", "size_bytes")),
                "molecular_sequence_ordinary_retained_control_conflict")
        request = self._ordinary_value(original["driver_request_file"])
        require(self._ordinary_value(original["plan_file"]) == plan
            and request == plan["selection"]["driver_request"]
            and request["selection"]["arguments"] == ordinary._native_arguments(operation, intent["arguments"], operand)
            and request["scientific_context"] == ordinary._scientific_context(operation, intent["arguments"], operand), "molecular_sequence_ordinary_request_conflict")
        handle, native_request = self._ordinary_value(original["native_handle_file"]), self._ordinary_value(original["native_request_file"])
        from gene_annotation_episode.molecular_sequence_execution_contracts import molecular_sequence_adapter_argv
        require(handle == execution["handle"] and handle["command"] == molecular_sequence_adapter_argv(plan)
            and handle["cwd"] == str(Path(plan["identity"]["execution_id"]).parent)
            and handle["metadata"]["policy"] == POLICY and native_request == ordinary._native_request(plan, handle["paths"])
            and hashlib.sha256(read_bytes(retained_native_file(self.store, original["native_request_file"]))).hexdigest()
                == handle["request_sha256"], "molecular_sequence_ordinary_native_request_conflict")
        proof = self._ordinary_value(original["association_file"])
        require(proof == dict(version="molecular_sequence_ordinary_association_v1", intent_sha256=digest(intent),
            original_identity=original["identity"], input_binding_file=custody["request"]["input_binding_file"],
            controls={key: original[key] for key in ("plan_file", "driver_request_file", "native_handle_file", "native_request_file", "execution_file")},
            terminal=True, quiescent=True, metadata=execution["metadata"], returncode=execution["returncode"]),
            "molecular_sequence_ordinary_association_conflict")
        metadata = self._ordinary_retained_metadata(plan, original)
        self._ordinary_match_metadata(execution, metadata, original=original)
        bundle, declaration, declarations, _issues = metadata
        require(same(self._ordinary_bundle_role_states(custody["source_files"], bundle), custody["source_files"]),
            "molecular_sequence_ordinary_bundle_role_identity_conflict")
        raw_roles = {} if declaration is None else declaration["files"]
        for role in ("capture", "sheet", "components"):
            state = custody["source_files"][role]
            if role in declarations:
                require(same(state["declared"], declarations[role]), "molecular_sequence_ordinary_role_declaration_conflict")
                if state["file"] is not None:
                    require(declarations[role]["state"] == "present" and all(
                        state["file"][key] == declarations[role][key] for key in ("sha256", "size_bytes")),
                        "molecular_sequence_ordinary_role_identity_conflict")
            elif role in raw_roles:
                require(state["file"] is None and state["failure"] == failure("schema_invalid", "capture", role=role),
                    "molecular_sequence_ordinary_invalid_role_conflict")
            else:
                require(state["declared"] is None and state["state"] != "retained",
                    "molecular_sequence_ordinary_undeclared_role_conflict")
        packet = supplied.validate_ordinary_molecular_sequence_packet(self._ordinary_value(custody["public_packet_file"]), operation=operation)
        if operation == "align_sequences":
            require(same(custody["context"], self._placement_context(custody["source_files"], operand=operand)),
                "molecular_sequence_ordinary_placement_context_conflict")
        require(packet == supplied.ordinary_molecular_sequence_packet(custody, operation=operation), "molecular_sequence_ordinary_packet_conflict")
        return custody

    def capture_ordinary_molecular_sequence(self, action, *, execution):
        """Retain one actual ordinary attempt; literal selection runs no calculator."""
        self.require_action(action)
        operation = action.intent["tool_name"]
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        intent = supplied.validate_ordinary_molecular_sequence_intent(action.intent, operation=operation)
        execution = supplied.validate_ordinary_molecular_sequence_execution(execution, operation=operation)
        previous = read_control(action.directory / "ordinary-custody.json")
        if previous is not None:
            previous = self._validate_ordinary_molecular_sequence_custody(previous, intent)
            require(self._ordinary_value(previous["original"]["execution_file"]) == execution,
                "molecular_sequence_ordinary_original_execution_conflict")
            return previous
        from gene_annotation_episode import molecular_sequence_ordinary as ordinary
        from gene_annotation_episode.molecular_measurement_tools import MolecularOperationUnpublished
        plan = execution["plan"]
        root = Path(plan["identity"]["execution_id"]).parent
        try:
            require(file_pin(root / profile["binding_filename"]) == execution["binding_file"])
            binding = _json(read_bytes(root / profile["binding_filename"]))
            prepared = dict(version=profile["prepared_version"], binding=binding, binding_file=execution["binding_file"],
                plan=plan, plan_file=execution["plan_file"], driver_request_file=execution["driver_request_file"],
                handle_path=plan["identity"]["execution_id"])
            handle, body = ordinary._verify_handle(prepared)
            require(binding["context"] == self.context(intent["episode_id"]).as_record()
                and binding["operation_key"] == intent["operation_key"] and binding["arguments"] == intent["arguments"]
                and body == execution["handle"], "molecular_sequence_ordinary_original_binding_conflict")
            view = ordinary._observe(handle, POLICY)
            require(view["terminal"] and view["quiescent"] and view["metadata"] == execution["metadata"]
                and view["metadata"].get("native_returncode") == execution["returncode"],
                "molecular_sequence_ordinary_writer_not_closed")
        except Exception as error:
            raise MolecularOperationUnpublished("molecular_sequence_ordinary_original_attempt_unconfirmed") from error
        input_binding = self._ordinary_capture_path(root / profile["binding_filename"],
            profile["binding_version"], pin=execution["binding_file"])
        original = dict(identity=deepcopy(plan["identity"]),
            plan_file=self._ordinary_capture_path(root / "molecular-sequence-plan.json", plan["version"], pin=execution["plan_file"]),
            driver_request_file=self._ordinary_capture_path(root / ordinary.DRIVER_REQUEST_FILENAME,
                plan["selection"]["driver_request"]["version"], pin=execution["driver_request_file"]),
            native_handle_file=self._ordinary_capture_path(handle.path, body["version"]),
            native_request_file=self._ordinary_capture_path(body["paths"]["request"], "native_local_job_request"),
            execution_file=None,
            bundle_file=None, declaration_file=None, association_file=None)
        require(self._ordinary_value(original["native_handle_file"]) == body)
        issues = []
        attempt = Path(plan["attempt_directory"])
        for key, path, fmt in (("bundle_file", attempt / "attempt-bundle.json", "molecular_sequence_attempt_bundle_v1"),
                ("declaration_file", attempt / "driver-output" / "declaration.json", "molecular_sequence_driver_declaration_v1")):
            try:
                original[key] = self._ordinary_capture_path(path, fmt)
            except NativeFileCaptureError as error:
                issues.append(failure("producer_unavailable" if error.code == "capture_file_unavailable" else
                    "retention_failed", "capture"))
        metadata = self._ordinary_retained_metadata(plan, original)
        try:
            self._ordinary_match_metadata(execution, metadata, original=original)
        except ValueError as error:
            raise MolecularOperationUnpublished("molecular_sequence_ordinary_original_metadata_conflict") from error
        # An inconsistent carrier cannot freeze the recovery operand for the
        # original valid attempt. Seal it only after raw metadata association.
        original["execution_file"] = self.capture_control(action, "ordinary-execution.json", execution, execution["version"])
        bundle, declaration, _declarations, metadata_issues = metadata
        for item in metadata_issues:
            issues.append(failure("producer_unavailable" if item["code"].endswith("_unavailable") else "schema_invalid",
                "capture" if item["code"].endswith("_unavailable") else "load", role=item["role"]))
        if execution["failure"] is not None or execution["returncode"] not in (0, None):
            issues.append(failure("worker_failed", "worker"))
        declared = {} if declaration is None else deepcopy(declaration["files"])
        # Preserve a valid-but-wrong role path as explicit invalid evidence;
        # never open that path or downgrade it to an undeclared capture.
        for role in ("capture", "sheet", "components"):
            if role not in declared: continue
            if declared[role] is None:
                declared[role] = {"invalid_ordinary_role_declaration": None}
                continue
            try:
                row = _declaration(declared[role])
            except NativeFileCaptureError:
                continue
            if row["relative_path"] != role + ".json" or row["format"] != "json":
                declared[role] = {"invalid_ordinary_role_declaration": declared[role]}
        sources = {role: empty_file_state("not_requested") for role in FILE_ROLES}
        sources.update(self._capture_files(directory=attempt / "driver-output", declarations=declared,
            capture_directory=action.directory / "ordinary-role-capture", roles=("capture", "sheet", "components")))
        sources = self._ordinary_bundle_role_states(sources, bundle)
        if sources["capture"]["file"] is not None:
            from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_driver import _native_capture
            try:
                _native_capture(self._ordinary_value(sources["capture"]["file"]), plan["selection"]["driver_request"]["selection"])
            except (ValueError, TypeError, KeyError, UnicodeError):
                issues.append(failure("schema_invalid", "load", role="capture",
                    source_ref=sources["capture"]["file"]["artifact_ref"]))
        proof = dict(version="molecular_sequence_ordinary_association_v1", intent_sha256=digest(intent),
            original_identity=original["identity"], input_binding_file=input_binding,
            controls={key: original[key] for key in ("plan_file", "driver_request_file", "native_handle_file", "native_request_file", "execution_file")},
            terminal=True, quiescent=True, metadata=execution["metadata"], returncode=execution["returncode"])
        original["association_file"] = self.capture_control(action, "ordinary-association.json", proof, proof["version"])
        association = dict(state="verified", reason="ordinary_selected_action_and_closed_native_handle",
            proof_file=original["association_file"], original_identity=original["identity"])
        selector = supplied.ordinary_molecular_sequence_selector(operation, intent["arguments"])
        projection = self._admit_projection(selector=selector, sources=sources, association=association,
            calculation={"kind": "original_stored", "calculator_id": None})
        facts = self._publication(selector, sources, projection, issues)
        invocation = dict(run_id=self.run_id, episode_id=intent["episode_id"], operation_key=intent["operation_key"],
            decision_index=int(intent["operation_key"].rsplit(":", 1)[1]), request_sha256=intent["original_request_sha256"], scope=intent["scope"])
        # Freeze publication time before computing the Source identity. A crash
        # after this control reuses the original packet and timestamp.
        stamp = read_control(action.directory / "ordinary-publication-time.json")
        if stamp is None:
            stamp = {"retrieved_at": datetime.now(timezone.utc).isoformat()}
            immutable(action.directory / "ordinary-publication-time.json", stamp)
        custody = dict(version=profile['custody_version'], intent=deepcopy(intent),
            request=dict(version=profile['publication_request_version'], arguments=intent["arguments"],
                invocation=invocation, input_binding_file=input_binding), original=original, source_files=sources,
            projection=projection, failures=facts[FAILURE_SOURCE], public_packet_file=None, retrieved_at=stamp["retrieved_at"])
        if operation == "align_sequences":
            custody["context"] = self._placement_context(sources, operand=binding["frozen_operand"])
        packet = supplied.validate_ordinary_molecular_sequence_packet(supplied.ordinary_molecular_sequence_packet(custody, operation=operation), operation=operation)
        custody["public_packet_file"] = self.capture_control(action, "ordinary-public-packet.json", packet,
            profile['packet_format'])
        custody = self._validate_ordinary_molecular_sequence_custody(custody, intent)
        immutable(action.directory / "ordinary-custody.json", custody)
        return custody

    def _ordinary_molecular_sequence_source_record(self, custody, capsule):
        operation = custody["intent"]["tool_name"]
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        if custody["version"] == profile['saved_custody_version']:
            refs = [custody["request"]["source_admission_file"]["artifact_ref"],
                custody["calculation"]["started_file"]["artifact_ref"],
                custody["calculation"]["result_file"]["artifact_ref"], custody["calculation"]["diagnostic_file"]["artifact_ref"]]
            if custody["source_files"]["components"]["file"] is not None:
                refs.append(custody["source_files"]["components"]["file"]["artifact_ref"])
            if operation == "align_sequences" and custody["context"]["original_operand_files"] is not None:
                files = custody["context"]["original_operand_files"]
                inputs = {file["artifact_ref"] for file in [files["target"],
                    *(files["primers"] if type(files["primers"]) is list else [files["primers"]])]}
                refs = [ref for ref in refs if ref not in inputs]
            return dict(provider=operation, version=profile['source_version'],
                artifact_ref=custody["public_packet_file"]["artifact_ref"], request_ref=capsule["artifact_ref"],
                text_ref=None, accession=None, uri=None, retrieved_at=custody["retrieved_at"],
                parent_source_refs=[custody["original_source"]["source_ref"]], auxiliary_artifact_refs=list(dict.fromkeys(refs)))
        # Original operand Files are deliberately absent from this produced
        # auxiliary list; pre-existing admissions retain their original owner.
        refs = [row["file"]["artifact_ref"] for row in custody["source_files"].values() if row["file"] is not None]
        refs.extend(self._ordinary_failed_capture_refs(custody["source_files"]))
        refs.extend(file["artifact_ref"] for file in custody["original"].values()
            if type(file) is dict and "artifact_ref" in file)
        refs.append(custody["request"]["input_binding_file"]["artifact_ref"])
        operand = self._ordinary_value(custody["request"]["input_binding_file"])["frozen_operand"]
        if operation == "align_sequences":
            from gene_annotation_episode.episodic_workflow.root.library.primer_placement_result_contracts import operand_records
            inputs = {row["input_file"]["artifact_ref"] for row in operand_records(operand)}
            refs = [ref for ref in dict.fromkeys(refs) if ref not in inputs]
        else:
            refs = [ref for ref in dict.fromkeys(refs) if ref != operand["input_file"]["artifact_ref"]]
        return dict(provider=operation, version=profile['source_version'],
            artifact_ref=custody["public_packet_file"]["artifact_ref"], request_ref=capsule["artifact_ref"],
            text_ref=None, accession=None, uri=None, retrieved_at=custody["retrieved_at"],
            parent_source_refs=[], auxiliary_artifact_refs=refs)
