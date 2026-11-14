"""Original molecular result responsibility: molecular_result_saved."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from gene_annotation_episode.episodic_workflow.root.communication import plain
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.native_control_records import immutable, read_control, same
from .molecular_result_actions import unique
from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_result_contracts import FAILURE_SOURCE, FILE_ROLES, MODES, empty_file_state, failure, require, SCHEMAS
from .library.retained_file_pin import file_pin
from gene_annotation_episode.episodic_workflow.root.library import molecular_sequence_result_contracts as supplied
from .molecular_result_values import _retained

class MolecularResultSaved:

    def _ordinary_saved_admission(self, context, source_ref, received):
        from gene_annotation_episode.molecular_sequence_input_contracts import validate_molecular_sequence_received_source, input_record_digest
        received = validate_molecular_sequence_received_source(received)
        require(received["failure"] is None and received["selection"] == dict(reference=source_ref, namespace="source"),
            "molecular_sequence_ordinary_source_not_received")
        item = received["input"]
        manifest = EpisodeReceipts.read_manifest(self.db, context.run_id, context.episode_id)
        require(item["receiver"] == dict(run_id=context.run_id, episode_id=context.episode_id,
            request_sha256=input_record_digest(plain(context.request)), assignment_sha256=input_record_digest(plain(context.assignment)))
            and same(item["scope"], self.store.validate_scope(plain(context.scope)))
            and same(item["inheritance_manifest"], manifest)
            and same(plain(context.request)["message"].get("knowledge_inheritance"), manifest)
            and item["witness"]["record"] == self.store.get(source_ref),
            "molecular_sequence_ordinary_source_admission_conflict")
        return received

    def _ordinary_saved_input(self, action, *, read_received):
        self.require_action(action)
        operation = action.intent["tool_name"]
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        context = self.context(action.intent["episode_id"])
        reference = action.intent["arguments"]["result_ref"]
        self._ordinary_original_source_admission(context, reference, action.intent["operation_key"])
        path = action.directory / "ordinary-source-admission.json"
        received = read_control(path)
        if received is None:
            require(callable(read_received), "molecular_sequence_ordinary_source_admission_required")
            received = self._ordinary_saved_admission(context, reference,
                read_received(context, reference, "source", source_metadata_only=True))
            immutable(path, received)
        received = self._ordinary_saved_admission(context, reference, received)
        publication = self.read_ordinary_molecular_sequence_publication(context, reference, operation=operation,
            read_received=lambda *_args, **_kwargs: received)
        return publication, received

    def _ordinary_original_source_admission(self, context, source_ref, operation_key):
        """Use original selected-action receipt authority without opening bytes."""
        records = EpisodeReturnRecords(self.store, context.run_id,
            failure_prefix="molecular_sequence_ordinary_")
        records.authenticate(context)
        return records.source_admission_before(context, source_ref, int(operation_key.rsplit(":", 1)[1]))

    def project_ordinary_molecular_sequence_view(self, publication, *, rows):
        """Select literal retained cells without recalculating their populations."""
        operation = publication["control"]["projection"]["public"]["operation"]
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        control = publication["control"]
        selector = {**control["projection"]["selector"], "rows": deepcopy(rows)}
        projection = self._admit_projection(selector=selector, sources=control["source_files"],
            association=control["projection"]["association"], calculation=control["projection"]["calculation"])
        packet = supplied.ordinary_molecular_sequence_packet({**control, "intent": {"arguments": {"rows": rows}},
            "projection": projection, "failures": unique([*control["failures"], *projection["public"]["failures"]])}, operation=operation)
        return supplied.validate_ordinary_molecular_sequence_return(dict(source_ref=publication["source"]["id"], **packet), operation=operation)

    def prepare_ordinary_molecular_sequence_saved(self, action, *, read_received):
        """One literal read or one existing pure calculation, never a native call."""
        self.require_action(action)
        operation = action.intent["tool_name"]
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        arguments = supplied.validate_ordinary_molecular_sequence_arguments(operation, action.intent["arguments"])
        require(arguments.get("mode") in ("read_stored", "calculate_saved"))
        publication, received = self._ordinary_saved_input(action, read_received=read_received)
        if arguments["mode"] == "read_stored":
            public = self.project_ordinary_molecular_sequence_view(publication, rows=arguments["rows"])
            immutable(action.directory / "ordinary-read-receipt.json", dict(version=profile['read_receipt_version'],
                intent=action.intent, source_sha256=digest(publication["source"]), public=public))
            return dict(public=public, publication=publication, received=received, calculation=None)
        sheet_file = publication["control"]["source_files"]["sheet"]["file"]
        require(sheet_file is not None, "molecular_sequence_ordinary_saved_sheet_unavailable")
        sheet = self._ordinary_value(sheet_file)
        if operation in supplied.OPERATIONS[2:4]:
            require(type(sheet) is dict and sheet.get("schema") == SCHEMAS[operation][0]
                and type(sheet.get("inputs")) is dict and sheet["inputs"].get("operation") == operation,
                "molecular_sequence_ordinary_saved_sheet_operation_conflict")
        result_path = action.directory / "ordinary-calculation-result.json"
        calculated = read_control(result_path)
        started = action.directory / "ordinary-calculation-started.json"
        expected_started = dict(version=profile['calculation_started_version'], intent_sha256=digest(action.intent),
            source_ref=publication["source"]["id"], source_sha256=digest(publication["source"]),
            sheet_file=sheet_file, native_call_state="not_requested", calculator_id=profile['calculator_id'])
        if calculated is None:
            if started.exists() or started.is_symlink():
                from gene_annotation_episode.molecular_measurement_tools import MolecularOperationUnpublished
                raise MolecularOperationUnpublished(profile["public_version"].removesuffix("_values_v1") + "_saved_calculation_outcome_unknown")
            immutable(started, expected_started)
            if operation == supplied.ORDINARY_ORF_TOOL:
                from gene_annotation_episode.orf_measurements import calculate_orf_components as calculator
            elif operation == "align_sequences":
                from gene_annotation_episode.primer_placement_measurements import calculate_primer_placement_components as calculator
            else:
                from gene_annotation_episode.glycosylation_measurements import calculate_glycosylation_components as calculator
            diagnostic = dict(version=profile['calculation_diagnostic_version'], native_call_state="not_requested",
                calculator_id=profile['calculator_id'], state="returned", call_count=1,
                exception_type=None, exception_message=None)
            components_pin = None
            try:
                components = calculator(sheet)
            except Exception as error:
                trace, called = error.__traceback__, False
                while trace is not None:
                    called |= trace.tb_frame.f_code is calculator.__code__
                    trace = trace.tb_next
                diagnostic.update(state="raised", call_count=1 if called else None,
                    exception_type=type(error).__module__ + "." + type(error).__name__, exception_message=str(error))
            else:
                path = action.directory / "ordinary-calculated-components.json"
                immutable(path, components)
                components_pin = file_pin(path)
            diagnostic_path = action.directory / "ordinary-calculation-diagnostic.json"
            immutable(diagnostic_path, diagnostic)
            calculated = dict(version=profile['calculation_result_version'], intent_sha256=digest(action.intent),
                source_ref=publication["source"]["id"], source_sha256=digest(publication["source"]), sheet_file=sheet_file,
                native_call_state="not_requested", state=diagnostic["state"], call_count=diagnostic["call_count"],
                components_pin=components_pin, diagnostic_pin=file_pin(diagnostic_path))
            immutable(result_path, calculated)
        require(same(read_control(started), expected_started), "molecular_sequence_ordinary_calculation_intent_conflict")
        self._ordinary_saved_calculation(calculated, intent=action.intent, publication=publication)
        return dict(public=None, publication=publication, received=received, calculation=calculated)

    def _ordinary_saved_calculation(self, result, *, intent, publication):
        operation = intent["tool_name"]
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        require(type(result) is dict and set(result) == {"version", "intent_sha256", "source_ref", "source_sha256",
            "sheet_file", "native_call_state", "state", "call_count", "components_pin", "diagnostic_pin"}
            and result["version"] == profile['calculation_result_version'] and result["intent_sha256"] == digest(intent)
            and result["source_ref"] == publication["source"]["id"] and result["source_sha256"] == digest(publication["source"])
            and result["sheet_file"] == publication["control"]["source_files"]["sheet"]["file"]
            and result["native_call_state"] == "not_requested" and result["state"] in ("returned", "raised")
            and (result["call_count"] is None or type(result["call_count"]) is int and result["call_count"] == 1)
            and (result["state"] != "returned" or result["call_count"] == 1)
            and (result["components_pin"] is not None if result["state"] == "returned" else result["components_pin"] is None),
            "molecular_sequence_ordinary_calculation_conflict")
        from gene_annotation_episode.molecular_sequence_execution_contracts import file_pin as validate_pin
        validate_pin(result["diagnostic_pin"])
        if result["components_pin"] is not None: validate_pin(result["components_pin"])
        return result

    def capture_ordinary_molecular_sequence_saved(self, action, *, prepared):
        """Retain saved outputs within the caller's publication/save transaction."""
        self.require_action(action)
        operation = action.intent["tool_name"]
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        require(self.store.db.in_transaction and action.intent["arguments"]["mode"] == "calculate_saved")
        calculated = self._ordinary_saved_calculation(prepared["calculation"], intent=action.intent,
            publication=prepared["publication"])
        # Fixed owned paths, never paths supplied by a worker/carrier. Repeating
        # capture repairs catalog rows after a rolled-back publication, not math.
        result_file = self.capture_control(action, "ordinary-calculation-result.json", calculated, calculated["version"])
        started_file = self.capture_control(action, "ordinary-calculation-started.json",
            read_control(action.directory / "ordinary-calculation-started.json"), profile['calculation_started_version'])
        diagnostic_file = self._ordinary_capture_path(action.directory / "ordinary-calculation-diagnostic.json",
            profile['calculation_diagnostic_version'], pin=calculated["diagnostic_pin"])
        sources = {role: empty_file_state("not_requested") for role in FILE_ROLES}
        sources["sheet"] = deepcopy(prepared["publication"]["control"]["source_files"]["sheet"])
        if calculated["components_pin"] is not None:
            sources["components"] = _retained(self._ordinary_capture_path(action.directory / "ordinary-calculated-components.json",
                SCHEMAS[operation][1][0], pin=calculated["components_pin"]))
        else:
            sources["components"] = empty_file_state("producer_unavailable", issue=failure("calculation_failed", "calculation", role="components"))
        source = prepared["publication"]["source"]
        association = deepcopy(prepared["publication"]["control"]["projection"]["association"])
        selector = supplied.validate_molecular_sequence_result_selector(dict(version=profile["selector_version"],
            mode=MODES[1], operation=operation, saved_sheet_ref=sources["sheet"]["file"]["artifact_ref"],
            rows=action.intent["arguments"]["rows"], return_files=[]))
        projection = self._admit_projection(selector=selector, sources=sources, association=association,
            calculation=dict(kind="selected_saved_calculation", calculator_id=profile['calculator_id']))
        stamp_path = action.directory / "ordinary-publication-time.json"
        stamp = read_control(stamp_path)
        if stamp is None:
            stamp = dict(retrieved_at=datetime.now(timezone.utc).isoformat()); immutable(stamp_path, stamp)
        metadata = self.store.get(source["request_ref"])
        packet_metadata = self.store.get(source["artifact_ref"])
        custody = dict(version=profile['saved_custody_version'], intent=deepcopy(action.intent),
            request=dict(version=profile['saved_request_version'], arguments=action.intent["arguments"],
                invocation=dict(run_id=self.run_id, episode_id=action.intent["episode_id"], operation_key=action.intent["operation_key"],
                    decision_index=int(action.intent["operation_key"].rsplit(":", 1)[1]),
                    request_sha256=action.intent["original_request_sha256"], scope=action.intent["scope"]),
                source_admission_file=self.capture_control(action, "ordinary-source-admission.json", prepared["received"], prepared["received"]["version"])),
            original_source=dict(source_ref=source["id"], record_sha256=digest(source),
                custody_file=dict(artifact_ref=source["request_ref"], sha256=metadata["sha256"], size_bytes=metadata["size"], format=prepared["publication"]["control"]["version"]),
                packet_file=dict(artifact_ref=source["artifact_ref"], sha256=packet_metadata["sha256"], size_bytes=packet_metadata["size"], format=profile['packet_format'])),
            source_files=sources, projection=projection, calculation=dict(calculator_id=profile['calculator_id'],
                native_call_state="not_requested", state=calculated["state"], call_count=calculated["call_count"],
                started_file=started_file, result_file=result_file, diagnostic_file=diagnostic_file),
            failures=self._publication(selector, sources, projection, [])[FAILURE_SOURCE], public_packet_file=None,
            retrieved_at=stamp["retrieved_at"])
        if operation == "align_sequences":
            custody["context"] = self._placement_context(sources, parent_context=prepared["publication"]["control"]["context"])
        custody["public_packet_file"] = self.capture_control(action, "ordinary-public-packet.json",
            supplied.validate_ordinary_molecular_sequence_packet(supplied.ordinary_molecular_sequence_packet(custody, operation=operation), operation=operation), profile['packet_format'])
        custody = self._validate_ordinary_molecular_sequence_custody(custody, action.intent)
        immutable(action.directory / "ordinary-custody.json", custody)
        return custody

    def _validate_ordinary_molecular_sequence_saved_custody(self, custody, intent, *, _seen):
        operation = intent["tool_name"]
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        custody = supplied.validate_ordinary_molecular_sequence_saved_custody(custody, operation=operation)
        require(same(custody["intent"], intent), "molecular_sequence_ordinary_custody_intent_conflict")
        context = EpisodeReturnRecords(self.store, intent["run_id"], failure_prefix="molecular_sequence_ordinary_").context(intent["episode_id"])
        original = custody["original_source"]
        self._ordinary_original_source_admission(context, original["source_ref"], intent["operation_key"])
        received = self._ordinary_saved_admission(context, original["source_ref"],
            self._ordinary_value(custody["request"]["source_admission_file"]))
        publication = self._read_ordinary_molecular_sequence_publication(context, original["source_ref"],
            operation=operation, read_received=lambda *_args, **_kwargs: received, pending_operation_key=None, _seen=_seen)
        require(digest(publication["source"]) == original["record_sha256"]
            and original["custody_file"]["artifact_ref"] == publication["source"]["request_ref"]
            and original["custody_file"]["format"] == publication["control"]["version"]
            and original["packet_file"]["artifact_ref"] == publication["source"]["artifact_ref"]
            and original["packet_file"]["format"] == profile['packet_format']
            and same(custody["source_files"]["sheet"], publication["control"]["source_files"]["sheet"]),
            "molecular_sequence_ordinary_saved_source_conflict")
        for key in ("custody_file", "packet_file"): self.file_metadata(original[key])
        calculated = self._ordinary_saved_calculation(self._ordinary_value(custody["calculation"]["result_file"]),
            intent=intent, publication=publication)
        require(same(self._ordinary_value(custody["calculation"]["started_file"]), dict(
            version=profile['calculation_started_version'], intent_sha256=digest(intent),
            source_ref=publication["source"]["id"], source_sha256=digest(publication["source"]),
            sheet_file=calculated["sheet_file"], native_call_state="not_requested", calculator_id=profile['calculator_id'])),
            "molecular_sequence_ordinary_calculation_intent_conflict")
        diagnostic = self._ordinary_value(custody["calculation"]["diagnostic_file"])
        require(type(diagnostic) is dict and set(diagnostic) == {"version", "native_call_state", "calculator_id", "state", "call_count", "exception_type", "exception_message"}
            and diagnostic["version"] == profile['calculation_diagnostic_version']
            and (diagnostic["call_count"] is None or type(diagnostic["call_count"]) is int and diagnostic["call_count"] == 1)
            and all(diagnostic[key] is None or type(diagnostic[key]) is str for key in ("exception_type", "exception_message"))
            and (all(diagnostic[key] is None for key in ("exception_type", "exception_message")) if diagnostic["state"] == "returned"
                else all(type(diagnostic[key]) is str for key in ("exception_type", "exception_message")))
            and all(diagnostic[key] == custody["calculation"][key] == calculated[key]
                for key in ("native_call_state", "state", "call_count"))
            and diagnostic["calculator_id"] == profile['calculator_id'],
            "molecular_sequence_ordinary_calculation_conflict")
        for pin, file in ((calculated["diagnostic_pin"], custody["calculation"]["diagnostic_file"]),
                (calculated["components_pin"], custody["source_files"]["components"]["file"])):
            require((pin is None) == (file is None))
            if file is not None:
                self.file_metadata(file)
                require(all(pin[key] == file[key] for key in ("sha256", "size_bytes")), "molecular_sequence_ordinary_calculation_conflict")
        projection = self._admit_projection(selector=custody["projection"]["selector"], sources=custody["source_files"],
            association=publication["control"]["projection"]["association"],
            calculation=dict(kind="selected_saved_calculation", calculator_id=profile['calculator_id']))
        require(same(projection, custody["projection"])
            and same(self._ordinary_value(custody["public_packet_file"]), supplied.ordinary_molecular_sequence_packet(custody, operation=operation)),
            "molecular_sequence_ordinary_saved_values_conflict")
        if operation == "align_sequences":
            require(same(custody["context"], self._placement_context(custody["source_files"],
                parent_context=publication["control"]["context"])), "molecular_sequence_ordinary_placement_context_conflict")
        return custody

    def _validate_ordinary_orf_custody(self, custody, intent, *, _seen=()):
        supplied.validate_ordinary_orf_intent(intent)
        return self._validate_ordinary_molecular_sequence_custody(custody, intent, _seen=_seen)

    def capture_ordinary_orf(self, action, *, execution):
        self.require_action(action)
        supplied.validate_ordinary_orf_intent(action.intent)
        return self.capture_ordinary_molecular_sequence(action, execution=execution)

    def _ordinary_orf_source_record(self, custody, capsule):
        supplied.validate_ordinary_orf_intent(custody["intent"])
        return self._ordinary_molecular_sequence_source_record(custody, capsule)

    def publish_ordinary_orf(self, action, *, custody):
        self.require_action(action)
        supplied.validate_ordinary_orf_intent(action.intent)
        return self.publish_ordinary_molecular_sequence(action, custody=custody)

    def read_ordinary_orf_publication(self, context, source_ref, *, read_received=None, pending_operation_key=None):
        return self.read_ordinary_molecular_sequence_publication(context, source_ref,
            operation=supplied.ORDINARY_ORF_TOOL, read_received=read_received,
            pending_operation_key=pending_operation_key)

    def _read_ordinary_orf_publication(self, context, source_ref, *, read_received, pending_operation_key, _seen=()):
        return self._read_ordinary_molecular_sequence_publication(context, source_ref,
            operation=supplied.ORDINARY_ORF_TOOL, read_received=read_received,
            pending_operation_key=pending_operation_key, _seen=_seen)

    def read_ordinary_orf_action_result(self, context, arguments, operation_key, *, read_received=None):
        return self.read_ordinary_molecular_sequence_action_result(context, arguments, operation_key,
            operation=supplied.ORDINARY_ORF_TOOL, read_received=read_received)

    def project_ordinary_orf_view(self, publication, *, rows):
        require(publication["control"]["projection"]["public"]["operation"] == supplied.ORDINARY_ORF_TOOL)
        return self.project_ordinary_molecular_sequence_view(publication, rows=rows)

    def prepare_ordinary_orf_saved(self, action, *, read_received):
        self.require_action(action)
        supplied.validate_ordinary_orf_intent(action.intent)
        return self.prepare_ordinary_molecular_sequence_saved(action, read_received=read_received)

    def capture_ordinary_orf_saved(self, action, *, prepared):
        self.require_action(action)
        supplied.validate_ordinary_orf_intent(action.intent)
        return self.capture_ordinary_molecular_sequence_saved(action, prepared=prepared)

    def _validate_ordinary_orf_saved_custody(self, custody, intent, *, _seen):
        supplied.validate_ordinary_orf_intent(intent)
        return self._validate_ordinary_molecular_sequence_saved_custody(custody, intent, _seen=_seen)
