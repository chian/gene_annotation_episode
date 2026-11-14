"""Selected overlap-result operations within the existing results episode.

The native writer, finite numerical worker, return authority and episode
controller retain their separate responsibilities. This host records one
selected operation and publishes its original qualified values.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from pathlib import Path

from .communication import plain
from .domain import obj
from .execution_contracts import digest
from .genomic_overlap_contracts import validate_genomic_overlap_record
from .genomic_overlap_result_receipts import (
    VERSION, GenomicOverlapResultReceipts, closure_value, decode, empty_facts,
    empty_files, immutable, outcome, qualified_files, read_control, require,
    same, unique,
)
from .genomic_overlap_return_views import (
    FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE,
    requested_genomic_overlap_sources,
)
from .local_jobs import LocalJobPolicy
from .native_file_capture import NativeFileCaptureError, retained_native_file
from .native_genomic_overlap_capture import capture_genomic_overlap_native_files
from .native_genomic_overlap_contracts import POLICY
from .native_genomic_overlap_preparation import (
    build_native_genomic_overlap_worker_plan, build_saved_genomic_overlap_worker_plan,
    prepare_genomic_overlap_worker, validate_prepared_genomic_overlap_worker,
)
from .state import Store


ORIGIN = {
    "content_location": "retained_complete_producer_bundle",
    "attempt_output_version": "original_producer_manifest_and_verified_file_digests",
    "window_consistency": "complete_files_matched_to_original_manifest",
    "completion_basis": "requested_acquisition_and_observed_successful_attempt",
}


def operation_catalog():
    return [
        {"name": "execution.results.status", "description":
         "Record the selected original overlap attempt or explicitly received saved-sheet status.",
         "input_schema": obj({})},
        {"name": "execution.results.collect", "description":
         "Collect the selected closed overlap output or calculate the explicitly received saved sheet and return the requested measurements.",
         "input_schema": obj({})},
    ]


def _failure(code, *, stage, field, file=None, expected=None, observed=None):
    return validate_genomic_overlap_record("Failure", {"code": code, "stage": stage,
        "set_key": None, "comparison_key": None,
        "artifact_ref": None if file is None else file["artifact_ref"], "locator": None,
        "field_path": field, "expected_value": expected, "observed_value": observed,
        "partial_artifact_refs": [], "requirement": "matching_file_identity" if file is not None
            else "complete_native_output"})


class NativeGenomicOverlapResults:
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store
        self.receipts = GenomicOverlapResultReceipts(owner)

    def applies(self, context):
        return context.role == "results" and plain(context.assignment).get("selector", {}).get("version") \
            == "genomic_overlap_result_selector_v1"

    def retained_target(self, context, assignment, scope):
        assignment, scope = plain(assignment), plain(scope)
        validate_genomic_overlap_record("Selector", assignment["selector"])
        self.store.validate_scope(scope, parent_scope=plain(context.scope))
        if assignment["selector"]["mode"] == "saved_sheet_recalculation":
            originals = self.receipts.origins(context, assignment)
            target = deepcopy(originals[0]["intent"]["target"])
            self.receipts._target(context, assignment, target)
            self.store.validate_scope(target["scope"], parent_scope=scope)
            return target
        if not self.applies(context):
            self.receipts.returns.authenticate(context, allow_unsaved=True)
            return None
        self.receipts._context(context, allow_unsaved=True)
        require(same(assignment, plain(context.assignment)))
        receipts = self.receipts.completed_receipts(context)
        if not receipts:
            return None
        target = receipts[0]["intent"]["target"]
        require(all(same(row["intent"]["target"], target) for row in receipts))
        return deepcopy(target)

    async def _worker(self, action, receipt, plan):
        self.receipts.require_action(action)
        immutable(action.directory / "worker-plan.json", plan)
        receipt["worker_plan"] = deepcopy(plan)
        prepared = read_control(action.directory / "worker-capture.json")
        if prepared is None:
            store_path = self.store.path

            def run():
                # SQLite connections remain owned by their creating thread.
                with Store(store_path) as store:
                    return prepare_genomic_overlap_worker(store, plan=plan,
                        policy=LocalJobPolicy(**POLICY))

            task = asyncio.create_task(asyncio.to_thread(run))
            try:
                prepared = await asyncio.shield(task)
            except asyncio.CancelledError:
                # Release the action lock only after this finite reserved work
                # has stopped. Recovery uses434's same durable worker handle.
                while not task.done():
                    try:
                        await asyncio.shield(task)
                    except asyncio.CancelledError:
                        continue
                    except BaseException:
                        break
                if not task.cancelled():
                    task.exception()
                raise
            prepared = validate_prepared_genomic_overlap_worker(self.store, prepared, plan=plan)
            immutable(action.directory / "worker-capture.json", prepared)
        else:
            prepared = validate_prepared_genomic_overlap_worker(self.store, prepared, plan=plan)
        execution = decode(retained_native_file(self.store, prepared["execution_receipt_file"]).read_bytes())
        immutable(action.directory / "worker-execution.json", execution)
        receipt.update(worker_capture=prepared, worker_execution=execution,
            qualified_files=qualified_files(prepared, execution))
        file = receipt["qualified_files"]["projection"]
        if file is not None:
            receipt["projection"] = validate_genomic_overlap_record("Projection",
                decode(retained_native_file(self.store, file).read_bytes()))

    async def _original(self, action, receipt, *, collecting):
        receipt["handoff_proof"] = self.receipts.read_handoff(action)
        observation = self.receipts.observation(action)
        receipt["observation"] = observation
        if not collecting:
            return
        native = observation["native"]
        if not native["terminal"] or not native["quiescent"]:
            receipt["host_failures"].append(_failure("native_output_unavailable", stage="capture",
                field="/native/writer_closure", expected={"terminal": True, "quiescent": True},
                observed={key: native[key] for key in ("terminal", "quiescent")}))
            return
        receipt["native"] = self.receipts.native_snapshot(action, observation)
        receipt["source_action_file"] = self.receipts.capture_control(action, "source-action.json",
            receipt["handoff_proof"]["start_receipt"], "practical_action_receipt_v1")
        receipt["writer_closure_file"] = self.receipts.capture_control(action, "writer-closure.json",
            closure_value(receipt), "genomic_overlap_writer_closure_v1")
        captured = read_control(action.directory / "capture.json")
        if captured is None:
            captured = capture_genomic_overlap_native_files(self.store,
                original_plan=receipt["native"]["original_plan"],
                source_action_receipt_ref=receipt["source_action_file"]["artifact_ref"],
                writer_closure_receipt_ref=receipt["writer_closure_file"]["artifact_ref"],
                driver_started=receipt["native"]["driver_started"])
            immutable(action.directory / "capture.json", captured)
        receipt["capture"] = captured
        plan = build_native_genomic_overlap_worker_plan(directory=str(action.directory / "worker"),
            original_plan=receipt["native"]["original_plan"], selector=action.intent["assignment"]["selector"],
            **{key: captured[key] for key in ("batch", "files", "source_action_receipt_ref",
                "writer_closure_receipt_ref", "driver_state", "failures")})
        await self._worker(action, receipt, plan)

    async def _saved(self, action, context, receipt, *, collecting):
        originals = self.receipts.origins(context, action.intent["assignment"])
        require(all(same(row["intent"]["target"], action.intent["target"]) for row in originals))
        receipt["original_origins"] = [{"episode_id": row["intent"]["episode_id"],
            "operation_key": row["intent"]["operation_key"]} for row in originals]
        receipt["handoff_proof"] = deepcopy(originals[0]["handoff_proof"])
        immutable(action.directory / "handoff.json", receipt["handoff_proof"])
        if not collecting:
            return
        selector = action.intent["assignment"]["selector"]
        file = selector["saved_sheet_file"]
        try:
            path = retained_native_file(self.store, file)
        except NativeFileCaptureError as error:
            receipt["host_failures"].append(_failure(
                "artifact_digest_mismatch" if error.code == "retained_artifact_mismatch" else "input_unavailable",
                stage="input", field="/selector/saved_sheet_file", file=file,
                expected=file, observed={"code": error.code}))
            return
        plan = build_saved_genomic_overlap_worker_plan(directory=str(action.directory / "worker"),
            sheet={"file": file, "path": str(path)}, selector=selector)
        await self._worker(action, receipt, plan)

    async def execute(self, context, target, tool_name, arguments, operation_key):
        require(self.applies(context))
        async with self.receipts.locked_action(context, target=target, tool_name=tool_name,
                arguments=arguments, operation_key=operation_key) as action:
            staged = self.receipts.read_staged(action)
            if staged is not None:
                return outcome(staged)
            require(self.completion(context) is None, "genomic_overlap_result_already_complete")
            receipt = {"version": VERSION, "intent": deepcopy(action.intent), "handoff_proof": None,
                "original_origins": [], "observation": None, "native": None,
                "source_action_file": None, "writer_closure_file": None, "capture": None,
                "worker_plan": None, "worker_capture": None, "worker_execution": None,
                "qualified_files": empty_files(), "projection": None, "host_failures": [],
                "facts": empty_facts(), "acquisition_evidence": None,
                "acquired_population": None, "delivery_complete": False}
            collecting = tool_name == "execution.results.collect"
            if action.intent["assignment"]["selector"]["mode"] == "saved_sheet_recalculation":
                await self._saved(action, context, receipt, collecting=collecting)
            else:
                await self._original(action, receipt, collecting=collecting)
                if receipt["qualified_files"]["sheet"] is not None:
                    evidence = read_control(action.directory / "acquisition-evidence.json")
                    if evidence is None:
                        sheet_file = receipt["qualified_files"]["sheet"]
                        sheet = validate_genomic_overlap_record("Sheet",
                            decode(retained_native_file(self.store, sheet_file).read_bytes()))
                        evidence = {"version": "genomic_overlap_acquisition_evidence_v1", "sheet_file": sheet_file,
                            "comparison_receipts": [deepcopy(row["receipt"]) for row in sheet["comparisons"]]}
                        immutable(action.directory / "acquisition-evidence.json", evidence)
                    receipt["acquisition_evidence"] = evidence
                    receipt["acquired_population"] = self.receipts.acquisition_population(receipt)
            receipt["facts"], receipt["delivery_complete"] = self.receipts.publication(receipt)
            return outcome(self.receipts.publish(action, receipt))

    def _verify_artifacts(self, receipt):
        files = receipt["qualified_files"]
        if receipt["facts"][PROJECTION_SOURCE]:
            for role in ("sheet", "components", "projection"):
                retained_native_file(self.store, files[role])
            require(same(decode(retained_native_file(self.store, files["projection"]).read_bytes()), receipt["projection"]))
        for file in receipt["facts"][SAVED_SOURCE]:
            retained_native_file(self.store, file)

    def own_fact_groups(self, context, *, verify_artifacts):
        require(type(verify_artifacts) is bool)
        groups = empty_facts()
        for receipt in self.receipts.completed_receipts(context):
            if verify_artifacts:
                self._verify_artifacts(receipt)
            for source in FACT_SOURCES:
                groups[source].extend(receipt["facts"][source])
        return {source: unique(rows) for source, rows in groups.items()}

    def facts(self, context):
        receipts = self.receipts.completed_receipts(context)
        schema = plain(context.request).get("report_contract", {}).get("measurements", {}).get("schema", {"properties": {}})
        requested = requested_genomic_overlap_sources(schema)
        groups = empty_facts()
        for receipt in receipts:
            for source in requested:
                groups[source].extend(receipt["facts"][source])
        return {**{source: unique(rows) for source, rows in groups.items()},
            "execution_handoff_refs": [], "execution_result_refs": [], "execution_blast_hsps": [],
            "execution_completed": any(row["delivery_complete"] for row in receipts),
            "execution_result_origin": deepcopy(ORIGIN) if any(row["delivery_complete"]
                and row["intent"]["assignment"]["selector"]["mode"] == "native_result" for row in receipts) else None}

    def resolve_own(self, context, reference, namespace):
        if namespace not in {None, "artifact"}:
            return False
        return any(file["artifact_ref"] == reference for file in self.own_fact_groups(
            context, verify_artifacts=False)[SAVED_SOURCE])

    def owns_reference(self, reference):
        return self.receipts.owns_reference(reference)

    def credit_view(self, context, receiver_selection):
        selection = self.owner._selection(context, receiver_selection)
        acquired = {row["acquired_population"] for row in self.receipts.completed_receipts(context)
            if row["acquired_population"] is not None}
        inherited = self.receipts.baseline_populations(context, selection["initial_known_record_refs"]) \
            if selection["initial_known_record_refs"] else set()
        count = len(acquired - inherited)
        value = self.owner.acquired_record_unit * count
        return {"credit": value, "operational_credit": value, "new_handoff_count": 0,
            "new_acquired_record_count": count, "operational_credit_binding": {"version": VERSION,
                "handoff_unit": self.owner.handoff_unit, "acquired_record_unit": self.owner.acquired_record_unit,
                "scientific_credit": False, "monitoring_credit": False}}

    def completion(self, context):
        for receipt in self.receipts.completed_receipts(context):
            if receipt["delivery_complete"]:
                saved = receipt["intent"]["assignment"]["selector"]["mode"] == "saved_sheet_recalculation"
                return {"version": "practical_completion_v1", "run_id": context.run_id,
                    "episode_id": context.episode_id, "assignment_sha256": digest(plain(context.assignment)),
                    "endpoint": "usable_handoff", "operation_key": receipt["intent"]["operation_key"],
                    "receipt_sha256": digest(receipt), "validation_keys": ["original_genomic_overlap_result_commission",
                        "explicitly_received_saved_sheet" if saved else "closed_original_native_capture",
                        "qualified_requested_genomic_overlap_delivery"]}
        return None


__all__ = ["NativeGenomicOverlapResults", "operation_catalog", "VERSION"]
