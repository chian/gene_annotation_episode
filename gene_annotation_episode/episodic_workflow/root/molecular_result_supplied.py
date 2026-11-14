"""Original molecular result responsibility: molecular_result_supplied."""
from __future__ import annotations
from copy import deepcopy
import hashlib
from pathlib import Path
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.native_control_records import immutable, read_control, same
from .molecular_result_actions import unique
from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_result_contracts import FAILURE_SOURCE, FILE_ROLES, SAVED_SOURCE, empty_file_state, failure, require, select_molecular_sequence_return_facts
from gene_annotation_episode.native_file_capture import NativeFileCaptureError, capture_native_file, retained_native_file
from .library.retained_file_read import read_bytes
from gene_annotation_episode.episodic_workflow.root.library import molecular_sequence_result_contracts as supplied
from .molecular_result_values import _facts, _json, _retained

class MolecularResultSupplied:

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
        from gene_annotation_episode.molecular_sequence_input_bindings import MolecularSequenceInputBindings
        from gene_annotation_episode.molecular_sequence_input_contracts import validate_molecular_sequence_received_input
        from gene_annotation_episode.episodic_workflow.root.library.calibrated_signal_sheet import read_calibrated_signal_inputs, validate_calibrated_signal_input_read
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
        from gene_annotation_episode.episodic_workflow.root.library.calibrated_signal_contracts import validate_calibrated_signal_selection
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
        from gene_annotation_episode.episodic_workflow.root.library.calibrated_signal_contracts import (validate_calibrated_signal_sheet,
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
            from gene_annotation_episode.molecular_sequence_result_worker import _strict_json
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
            from gene_annotation_episode.episodic_workflow.root.library.calibrated_signal_contracts import validate_calibrated_signal_components_shape
            from gene_annotation_episode.molecular_sequence_result_worker import _strict_json
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
