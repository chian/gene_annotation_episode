"""Selected chromatin result work inside the existing results episode.

The episode selects status or collection. This binding records that original
action, retains closed output, invokes one finite calculator and returns only
the requested fields. It makes no scientific decision or resource selection.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy

from .communication import plain
from .domain import obj
from .execution_contracts import digest
from .chromatin_interaction_contracts import validate_chromatin_record
from .chromatin_interaction_result_receipts import (
    VERSION, ChromatinInteractionResultReceipts, closure_value, decode,
    empty_facts, empty_files, immutable, outcome, qualified_files,
    read_control, require, same, unique,
)
from .chromatin_interaction_return_views import (
    FACT_SOURCES, PROJECTION_SOURCE, SAVED_SOURCE,
    requested_chromatin_sources, validate_chromatin_fact_values,
)
from .local_jobs import LocalJobPolicy
from .native_file_capture import NativeFileCaptureError, retained_native_file
from .native_chromatin_interaction_capture import capture_chromatin_native_files
from .native_chromatin_interaction_contracts import POLICY, failure
from .native_chromatin_interaction_preparation import (
    build_native_chromatin_worker_plan, build_saved_chromatin_worker_plan,
    prepare_chromatin_result_worker, validate_prepared_chromatin_worker,
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
         "Record the selected original chromatin job or explicitly received saved-sheet status.",
         "input_schema": obj({})},
        {"name": "execution.results.collect", "description":
         "Retain the selected closed chromatin output or recalculate the explicitly received sheet and tables, returning the requested measurements.",
         "input_schema": obj({})},
    ]


def _input_failure(error, *, field, file=None):
    # Only actual retained-data failures become scientific input availability.
    # Invalid identities/paths and programming errors remain failures to repair.
    if error.code not in {"retained_artifact_unavailable", "retained_artifact_mismatch"}:
        raise error
    return failure("artifact_digest_mismatch" if error.code == "retained_artifact_mismatch"
        else "input_unavailable", "input", field_path=field,
        artifact_ref=None if file is None else file["artifact_ref"],
        requirement="matching_file_identity")


def _bundle_files(bundle):
    yield bundle["sheet"]
    yield from bundle["tables"]


class NativeChromatinInteractionResults:
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store
        self.receipts = ChromatinInteractionResultReceipts(owner)

    def applies(self, context):
        return (context.role == "results" and plain(context.assignment).get("selector", {}).get("version")
            == "chromatin_interaction_result_selector_v1")

    def retained_target(self, context, assignment, scope):
        assignment, scope = plain(assignment), plain(scope)
        validate_chromatin_record("ResultSelector", assignment["selector"])
        self.store.validate_scope(scope, parent_scope=plain(context.scope))
        if assignment["selector"]["mode"] == "saved_sheet_recalculation":
            origins = self.receipts.origins(context, assignment)
            require(bool(origins))
            target = deepcopy(origins[0]["intent"]["target"])
            require(all(same(row["intent"]["target"], target) for row in origins))
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
                with Store(store_path) as store:
                    return prepare_chromatin_result_worker(store, plan=plan,
                        policy=LocalJobPolicy(**POLICY))

            task = asyncio.create_task(asyncio.to_thread(run))
            try:
                prepared = await asyncio.shield(task)
            except asyncio.CancelledError:
                # The original reserved worker owns its finite execution. Keep
                # the action lock until it has stopped; never dispatch a second
                # worker because the caller's observation was interrupted.
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
            except NativeFileCaptureError as error:
                receipt["host_failures"].append(_input_failure(error, field="/worker/retained_inputs"))
                return
            prepared = validate_prepared_chromatin_worker(self.store, prepared, plan=plan)
            immutable(action.directory / "worker-capture.json", prepared)
        else:
            prepared = validate_prepared_chromatin_worker(self.store, prepared, plan=plan)
        execution = decode(retained_native_file(self.store, prepared["execution_receipt_file"]).read_bytes())
        immutable(action.directory / "worker-execution.json", execution)
        receipt.update(worker_capture=prepared, worker_execution=execution,
            qualified_files=qualified_files(prepared, execution))
        projection = receipt["qualified_files"]["projection"]
        if projection is not None:
            receipt["projection"] = validate_chromatin_record("RequestedProjection",
                decode(retained_native_file(self.store, projection).read_bytes()))

    async def _original(self, action, receipt, *, collecting):
        receipt["handoff_proof"] = self.receipts.read_handoff(action)
        observation = self.receipts.observation(action)
        receipt["observation"] = observation
        if not collecting:
            return
        native = observation["native"]
        if not native["terminal"] or not native["quiescent"]:
            receipt["host_failures"].append(failure("input_unavailable", "capture",
                field_path="/native/writer_closure", requirement="original_native_outcome"))
            return
        receipt["native"] = self.receipts.native_snapshot(action, observation)
        receipt["source_action_file"] = self.receipts.capture_control(action, "source-action.json",
            receipt["handoff_proof"]["start_receipt"], "practical_action_receipt_v1")
        receipt["writer_closure_file"] = self.receipts.capture_control(action, "writer-closure.json",
            closure_value(receipt), "chromatin_interaction_writer_closure_v1")
        captured = read_control(action.directory / "capture.json")
        if captured is None:
            captured = capture_chromatin_native_files(self.store,
                original_plan=receipt["native"]["original_plan"],
                source_action_receipt_ref=receipt["source_action_file"]["artifact_ref"],
                writer_closure_receipt_ref=receipt["writer_closure_file"]["artifact_ref"],
                driver_started=receipt["native"]["driver_started"])
            immutable(action.directory / "capture.json", captured)
        receipt["capture"] = captured
        plan = build_native_chromatin_worker_plan(directory=str(action.directory / "worker"),
            original_plan=receipt["native"]["original_plan"], selector=action.intent["assignment"]["selector"],
            **{key: captured[key] for key in ("bundle", "files", "source_action_receipt_ref",
                "writer_closure_receipt_ref", "driver_state", "failures")})
        await self._worker(action, receipt, plan)

    async def _saved(self, action, context, receipt, *, collecting):
        origins = self.receipts.origins(context, action.intent["assignment"])
        require(bool(origins) and all(same(row["intent"]["target"], action.intent["target"]) for row in origins))
        receipt["original_origins"] = [{"episode_id": row["intent"]["episode_id"],
            "operation_key": row["intent"]["operation_key"]} for row in origins]
        receipt["handoff_proof"] = deepcopy(origins[0]["handoff_proof"])
        immutable(action.directory / "handoff.json", receipt["handoff_proof"])
        if not collecting:
            return
        selector = action.intent["assignment"]["selector"]
        bundle = selector["saved_sheet_bundle"]
        retained = []
        for index, file in enumerate(_bundle_files(bundle)):
            field = "/selector/saved_sheet_bundle/" + ("sheet" if index == 0 else f"tables/{index - 1}")
            try:
                path = retained_native_file(self.store, file)
            except NativeFileCaptureError as error:
                receipt["host_failures"].append(_input_failure(error, field=field, file=file))
            else:
                retained.append({"file": deepcopy(file), "path": str(path)})
        if receipt["host_failures"]:
            return
        plan = build_saved_chromatin_worker_plan(directory=str(action.directory / "worker"),
            sheet_bundle={"sheet": retained[0], "tables": retained[1:]}, selector=selector)
        await self._worker(action, receipt, plan)

    async def execute(self, context, target, tool_name, arguments, operation_key):
        require(self.applies(context))
        async with self.receipts.locked_action(context, target=target, tool_name=tool_name,
                arguments=arguments, operation_key=operation_key) as action:
            staged = self.receipts.read_staged(action)
            if staged is not None:
                return outcome(staged)
            require(self.completion(context) is None, "chromatin_result_already_complete")
            receipt = {"version": VERSION, "intent": deepcopy(action.intent), "handoff_proof": None,
                "original_origins": [], "observation": None, "native": None,
                "source_action_file": None, "writer_closure_file": None, "capture": None,
                "worker_plan": None, "worker_capture": None, "worker_execution": None,
                "qualified_files": empty_files(), "sheet_evidence": None, "projection": None,
                "host_failures": [], "facts": empty_facts(), "acquired_population": None,
                "delivery_complete": False}
            collecting = tool_name == "execution.results.collect"
            if action.intent["assignment"]["selector"]["mode"] == "saved_sheet_recalculation":
                await self._saved(action, context, receipt, collecting=collecting)
            else:
                await self._original(action, receipt, collecting=collecting)
            if receipt["qualified_files"]["sheet"] is not None:
                receipt["sheet_evidence"] = self.receipts.sheet_evidence(action, receipt)
            receipt["acquired_population"] = self.receipts.acquisition_population(receipt)
            receipt["facts"], receipt["delivery_complete"] = self.receipts.publication(receipt)
            return outcome(self.receipts.publish(action, receipt))

    def _verify_artifacts(self, receipt):
        files = receipt["qualified_files"]
        if receipt["facts"][PROJECTION_SOURCE]:
            for role in ("sheet", "components", "projection"):
                retained_native_file(self.store, files[role])
            for row in files["tables"]:
                if row["file"] is not None:
                    retained_native_file(self.store, row["file"])
            require(same(decode(retained_native_file(self.store, files["projection"]).read_bytes()),
                receipt["projection"]))
        for bundle in receipt["facts"][SAVED_SOURCE]:
            for file in _bundle_files(bundle):
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

    def completed_saved_bundle_origins(self, context, bundle):
        validate_chromatin_fact_values(SAVED_SOURCE, [bundle])
        return tuple({"episode_id": receipt["intent"]["episode_id"],
            "operation_key": receipt["intent"]["operation_key"]}
            for receipt in self.receipts.completed_receipts(context)
            if any(same(bundle, row) for row in receipt["facts"][SAVED_SOURCE]))

    def facts(self, context):
        receipts = self.receipts.completed_receipts(context)
        schema = plain(context.request).get("report_contract", {}).get("measurements", {}).get("schema", {"properties": {}})
        requested = requested_chromatin_sources(schema)
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
        return any(file["artifact_ref"] == reference
            for bundle in self.own_fact_groups(context, verify_artifacts=False)[SAVED_SOURCE]
            for file in _bundle_files(bundle))

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
                    "receipt_sha256": digest(receipt), "validation_keys": ["original_chromatin_result_commission",
                        "explicitly_received_saved_sheet_bundle" if saved else "closed_original_native_capture",
                        "qualified_requested_chromatin_delivery"]}
        return None


__all__ = ["NativeChromatinInteractionResults", "operation_catalog", "VERSION"]
