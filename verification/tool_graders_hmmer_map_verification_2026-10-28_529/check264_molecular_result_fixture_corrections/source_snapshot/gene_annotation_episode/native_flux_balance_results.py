"""Selected FBA-result operations within the existing results episode.

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
from .flux_balance_result_contracts import validate_fba_projection
from .flux_balance_result_receipts import (
    VERSION, FluxBalanceResultReceipts, closure_value, empty_facts,
    empty_files, immutable, qualified_files, read_control, require,
    same, unique, issue,
    FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE,
)
from .flux_balance_return_views import requested_fba_sources
from .local_jobs import LocalJobPolicy
from .native_file_capture import NativeFileCaptureError, retained_native_file
from .native_flux_balance_capture import capture_flux_balance_native_files
from .native_flux_balance_contracts import POLICY
from .flux_balance_worker_contracts import (
    build_native_flux_balance_worker_plan, build_saved_flux_balance_worker_plan)
from .native_flux_balance_preparation import (
    prepare_flux_balance_result_worker, validate_prepared_flux_balance_worker,
)
from .state import Store
from .native_flux_balance_storage import read_json


ORIGIN = {
    "content_location": "retained_declared_native_files",
    "attempt_output_version": "independent_retained_file_digests_with_recorded_association",
    "window_consistency": "independently_captured_files_writer_closed",
    "completion_basis": "requested_typed_delivery_from_original_closed_attempt",
}


def operation_catalog():
    return [
        {"name": "execution.results.status", "description":
         "Record the selected original FBA attempt or explicitly received saved-sheet status.",
         "input_schema": obj({})},
        {"name": "execution.results.collect", "description":
         "Collect the selected closed FBA output or calculate the explicitly received saved sheet and return the requested measurements.",
         "input_schema": obj({})},
    ]


class NativeFluxBalanceResults:
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store
        self.receipts = FluxBalanceResultReceipts(owner)

    def applies(self, context):
        return context.role == "results" and plain(context.assignment).get("selector", {}).get("version") \
            == "flux_balance_result_selector_v1"

    def retained_target(self, context, assignment, scope):
        assignment, scope = plain(assignment), plain(scope)
        from .flux_balance_result_selection import validate_flux_balance_result_selector
        validate_flux_balance_result_selector(assignment["selector"])
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
                    return prepare_flux_balance_result_worker(store, plan=plan,
                        policy=LocalJobPolicy(**POLICY))

            task = asyncio.create_task(asyncio.to_thread(run))
            try:
                prepared = await asyncio.shield(task)
            except asyncio.CancelledError:
                # Release the action lock only after this finite reserved work
                # has stopped. Recovery uses the same durable worker handle.
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
            prepared = validate_prepared_flux_balance_worker(self.store, prepared, plan=plan)
            immutable(action.directory / "worker-capture.json", prepared)
        else:
            prepared = validate_prepared_flux_balance_worker(self.store, prepared, plan=plan)
        execution = read_json(retained_native_file(self.store, prepared["execution_receipt_file"]))
        immutable(action.directory / "worker-execution.json", execution)
        receipt.update(worker_capture=prepared, worker_execution=execution,
            qualified_files=qualified_files(prepared, execution))
        file = receipt["qualified_files"]["projection"]
        if file is not None:
            receipt["projection"] = validate_fba_projection(read_json(retained_native_file(self.store, file)))

    async def _original(self, action, receipt, *, collecting):
        receipt["handoff_proof"] = self.receipts.read_handoff(action)
        observation = self.receipts.observation(action)
        receipt["observation"] = observation
        if not collecting:
            return
        native = observation["native"]
        if not native["terminal"] or not native["quiescent"]:
            receipt["host_failures"].append(issue("writer_not_closed", "capture", "native"))
            return
        receipt["native"] = self.receipts.native_snapshot(action, observation)
        receipt["source_action_file"] = self.receipts.capture_control(action, "source-action.json",
            receipt["handoff_proof"]["start_receipt"], "practical_action_receipt_v1")
        receipt["writer_closure_file"] = self.receipts.capture_control(action, "writer-closure.json",
            closure_value(receipt), "flux_balance_writer_closure_v1")
        captured = read_control(action.directory / "capture.json")
        if captured is None:
            captured = capture_flux_balance_native_files(self.store,
                original_plan=receipt["native"]["original_plan"],
                source_action_receipt_ref=receipt["source_action_file"]["artifact_ref"],
                writer_closure_receipt_ref=receipt["writer_closure_file"]["artifact_ref"],
                input_binding_file=receipt["handoff_proof"]["input_binding"]["file"],
                prior_sources=self.receipts.selected_priors(receipt["handoff_proof"]),
                driver_started=receipt["native"]["driver_started"])
            immutable(action.directory / "capture.json", captured)
        receipt["capture"] = captured
        plan = build_native_flux_balance_worker_plan(directory=str(action.directory / "worker"),
            original_plan=receipt["native"]["original_plan"], selector=action.intent["assignment"]["selector"],
            capture=captured)
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
            receipt["host_failures"].append(issue("artifact_identity_conflict" if error.code == "retained_artifact_mismatch" else
                "artifact_missing", "load", "saved_sheet_file"))
            return
        plan = build_saved_flux_balance_worker_plan(directory=str(action.directory / "worker"),
            sheet={"file": file, "path": str(path)}, selector=selector)
        await self._worker(action, receipt, plan)

    async def execute(self, context, target, tool_name, arguments, operation_key):
        require(self.applies(context))
        async with self.receipts.locked_action(context, target=target, tool_name=tool_name,
                arguments=arguments, operation_key=operation_key) as action:
            staged = self.receipts.read_staged(action)
            if staged is not None:
                return self.receipts.outcome(staged)
            require(self.completion(context) is None, "flux_balance_result_already_complete")
            receipt = {"version": VERSION, "intent": deepcopy(action.intent), "handoff_proof": None,
                "original_origins": [], "observation": None, "native": None,
                "source_action_file": None, "writer_closure_file": None, "capture": None,
                "worker_plan": None, "worker_capture": None, "worker_execution": None,
                "qualified_files": empty_files(), "projection": None, "host_failures": [],
                "facts": empty_facts(),
                "acquired_population": None, "delivery_complete": False}
            collecting = tool_name == "execution.results.collect"
            if action.intent["assignment"]["selector"]["mode"] == "saved_sheet_recalculation":
                await self._saved(action, context, receipt, collecting=collecting)
            else:
                await self._original(action, receipt, collecting=collecting)
                receipt["acquired_population"] = self.receipts.acquisition_population(receipt)
            receipt["facts"], receipt["delivery_complete"] = self.receipts.publication(receipt)
            return self.receipts.outcome(self.receipts.publish(action, receipt))

    def _verify_artifacts(self, receipt):
        files = receipt["qualified_files"]
        if receipt["facts"][PROJECTION_SOURCE]:
            retained_native_file(self.store, files["projection"])
            require(same(read_json(retained_native_file(self.store, files["projection"])), receipt["projection"]))
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
        requested = requested_fba_sources(schema)
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
        inherited = self.receipts.baseline_populations(context, selection["initial_known_record_refs"])
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
                    "receipt_sha256": digest(receipt), "validation_keys": ["original_flux_balance_result_commission",
                        "explicitly_received_saved_sheet" if saved else "closed_original_native_capture",
                        "qualified_requested_flux_balance_delivery"]}
        return None


__all__ = ["NativeFluxBalanceResults", "operation_catalog", "VERSION"]
