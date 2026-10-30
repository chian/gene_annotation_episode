"""Selected protein result acquisition, qualification and requested publication.

The results episode owns the selection. This host reuses the capture and bounded
result worker; it neither performs a native analysis nor chooses another job.
Receipt proof owns durable action state and historical authority. Scientific
bytes are opened only during selected work or an explicitly requested check.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import get_args

from .communication import plain
from .domain import ContractError
from .execution_contracts import canonical, digest, obj
from .local_jobs import LocalJobPolicy
from .native_protein_structure_acquisition import (
    capture_local_protein_structure_bundle, decode_protein_structure_json,
    is_native_protein_structure_target, retained_protein_structure_file,
    validate_protein_structure_capture,
)
from .native_protein_structure_contracts import (
    validate_native_protein_structure_result, validate_protein_structure_bundle,
)
from .native_protein_structure_preparation import (
    ValidatedProteinWorker, prepare_protein_structure_worker,
    validate_prepared_protein_structure_worker,
)
from .native_protein_structure_returns import (
    FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE, SEQUENCE_SOURCE,
    requested_sources,
)
from .progress_records import validate_resource_observation
from .protein_structure_authority import (
    ProteinFactGroups, ProteinResultAuthorityRecord, ProteinStructureOperandError,
)
from .protein_structure_calculations import validate_recorded_protein_structure_components
from .protein_structure_contracts import (
    IssueCode, ResultCustody, issue, same, validate_saved_sheet_descriptor,
    validate_structure_sequence_descriptor,
)
from .protein_structure_operands import validate_protein_structure_selected_inputs
from .protein_structure_projection_publication import publish_protein_structure_projection
from .protein_structure_publication import (
    publish_protein_structure_source, publish_structure_sequence_reference,
)
from .protein_structure_result_receipts import (
    ProteinQualifiedFiles, ProteinResultAction, ProteinResultBody,
    ProteinResultPublication, ProteinResultReceipt, ProteinResultReceipts,
)
from .protein_structure_result_views import (
    project_protein_structure_results, validate_protein_structure_failure_return,
    validate_protein_structure_projection_rows,
)
from .protein_structure_result_worker import ProteinResultWorkerPlan
from .protein_structure_selection import validate_protein_structure_result_selector
from .state import Store


VERSION = "native_protein_structure_acquired_result_v1"
ORIGIN = {
    "content_location": "retained_complete_producer_bundle",
    "attempt_output_version": "original_producer_manifest_and_verified_file_digests",
    "window_consistency": "complete_files_matched_to_original_manifest",
    "completion_basis": "requested_acquisition_and_observed_successful_attempt",
}
_CODES = frozenset(get_args(IssueCode))


def operation_catalog() -> list[dict]:
    return [
        {"name": "execution.results.status", "description":
         "Read the selected original protein attempt or retained-input status.",
         "input_schema": obj({})},
        {"name": "execution.results.collect", "description":
         "Acquire and qualify the selected original protein result, or recalculate the explicitly received saved sheet, and return the requested fields.",
         "input_schema": obj({})},
    ]


def _require(condition, code="original_commission_mismatch"):
    if not condition:
        raise ProteinStructureOperandError(issue(code, stage="authority", field="receipt"))


def _problem(error, *, stage="input", field="file_identity", role=None):
    if isinstance(error, ProteinStructureOperandError):
        return deepcopy(error.issue)
    code = str(error) if str(error) in _CODES else (
        "retained_artifact_missing" if isinstance(error, OSError) else "invalid_schema")
    return issue(code, stage=stage, field=field, artifact_role=role)


def _unique(rows):
    result, seen = [], set()
    for row in rows:
        key = canonical(row)
        if key not in seen:
            seen.add(key)
            result.append(deepcopy(row))
    return result


def _empty_files() -> ProteinQualifiedFiles:
    return {name: None for name in ProteinQualifiedFiles.__annotations__}


def _empty_facts() -> ProteinFactGroups:
    return {name: [] for name in FACT_SOURCES}


def _result_key(intent):
    return "protein_structure_result_receipt:" + digest({
        name: intent[name] for name in ("run_id", "episode_id", "operation_key")})


def _outcome(receipt: ProteinResultReceipt) -> dict:
    refs = receipt["publication"]["record_refs"]
    return {"status": "completed", "record_refs": deepcopy(refs),
            "changed_record_refs": deepcopy(refs), "result": deepcopy(receipt), "feedback": None}


def _prepare_worker_in_thread(store_path: Path, *, plan: ProteinResultWorkerPlan,
                              policy: LocalJobPolicy) -> ValidatedProteinWorker:
    # SQLite connections stay on their owning thread. Only a detached plan and
    # the same Store's path cross this boundary.
    with Store(store_path) as worker_store:
        prepared = prepare_protein_structure_worker(worker_store, plan=plan, policy=policy)
        return validate_prepared_protein_structure_worker(worker_store, prepared, plan=plan)


class NativeProteinStructureResults:
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store
        self.receipts = ProteinResultReceipts(owner)

    @property
    def _returns(self):
        # Construction precedes installation of the owner's returns adapter.
        return self.owner.native_protein_structure_returns

    def applies(self, context) -> bool:
        assignment = plain(context.assignment)
        return (context.role == "results" and isinstance(assignment, dict)
                and isinstance(assignment.get("selector"), dict)
                and assignment["selector"].get("version") == "protein_structure_result_selector_v1")

    async def _prepare_worker(self, *, action: ProteinResultAction,
                              plan: ProteinResultWorkerPlan,
                              policy: LocalJobPolicy) -> ValidatedProteinWorker:
        self.receipts.require_action(action)
        _require(plan["directory"] == str(action.worker_directory), "invalid_output_path")
        _require(not self.store.db.in_transaction)
        task = asyncio.create_task(asyncio.to_thread(_prepare_worker_in_thread,
            self.store.path, plan=deepcopy(plan), policy=policy))
        try:
            return deepcopy(await asyncio.shield(task))
        except asyncio.CancelledError:
            # A cancelled caller still owns the original reservation and action
            # lock until blocking preparation has returned. Never cancel/retry
            # native work or let a second caller start while it is outstanding.
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    continue
                except BaseException:
                    break
            if task.done() and not task.cancelled():
                task.exception()
            raise

    def _policy(self, target):
        resource = self.owner.resources[target["resource_id"]]
        _require(resource["kind"] == "local")
        return LocalJobPolicy(**resource["policy"])

    def _bytes(self, identity, *, role=None):
        try:
            raw = retained_protein_structure_file(self.store, identity).read_bytes()
            if len(raw) != identity["byte_length"] or hashlib.sha256(raw).hexdigest() != identity["sha256"]:
                raise ValueError("input_digest_mismatch")
            return raw
        except (ValueError, OSError) as error:
            raise ProteinStructureOperandError(_problem(error, role=role)) from error

    def _json(self, identity, *, role=None):
        try:
            return decode_protein_structure_json(self._bytes(identity, role=role), canonical_bytes=True)
        except ValueError as error:
            raise ProteinStructureOperandError(_problem(error, role=role)) from error

    @staticmethod
    def _captured(capture, role):
        rows = [row["observed"] for row in capture["files"]
                if row["declared"]["role"] == role and row["outcome"] == "verified"]
        _require(len(rows) <= 1)
        return deepcopy(rows[0]) if rows else None

    def _original_science(self, body):
        """Read the already qualified worker outputs, without parsing/refitting."""
        worker = body["worker"]
        result = None if worker is None else worker["result"]
        if result is None:
            return None
        operation = result["operation"]
        # 008: a diagnostic C-valid comparison envelope alone is insufficient.
        required = ("native_result_file", "sheet_file", "components_file") if operation == "compare" else ("native_result_file",)
        if any(result[name] is None for name in required):
            return None
        native_file = result["native_result_file"]["file_identity"]
        native = validate_native_protein_structure_result(self._json(native_file, role="native_result"))
        job = body["bundle"]["requested_job"]["native_protein_structure"]
        _require(same(native["request"], job["request"]) and same(native["producer"], job["software"]))
        qualified = _empty_files()
        qualified["native_file"] = deepcopy(native_file)
        if operation == "inspect":
            body["qualified_files"] = qualified
            return {"kind": "inspection", "inventory": native["inventory"]}
        if operation == "extract_sequence":
            body["qualified_files"] = qualified
            sequence = native["sequence"]
            files = {role: self._captured(body["capture"], role)
                     for role in ("sequence", "residue_map", "single_structure")}
            if sequence["sequence_available"] and all(files.values()):
                try:
                    _require(same(files["single_structure"], sequence["selection"]["file_identity"]), "sequence_artifact_mismatch")
                    if (self._bytes(files["sequence"], role="sequence") != sequence["alignment_sequence"].encode("ascii")
                            or self._bytes(files["residue_map"], role="residue_map") != canonical(sequence).encode("utf-8")):
                        raise ValueError("sequence_artifact_mismatch")
                    self._bytes(files["single_structure"], role="single_structure")
                except (ValueError, OSError) as error:
                    body["issues"].append(_problem(error, stage="sequence", field="sequence"))
                else:
                    qualified.update(sequence_file=files["sequence"], residue_map_file=files["residue_map"])
            return {"kind": "extraction", "sequence": sequence, "metadata": native["metadata"], "descriptor": None}
        sheet_file, components_file = [result[name]["file_identity"] for name in ("sheet_file", "components_file")]
        sheet, components = self._json(sheet_file), self._json(components_file)
        _require(same(sheet, native["sheet"]) and same(components, sheet["native_baseline"])
                 and same(components["parameters"], job["request"]["parameters"]))
        validate_recorded_protein_structure_components(sheet, components=components)
        qualified.update(sheet_file=deepcopy(sheet_file), original_components_file=deepcopy(components_file),
                         components_file=deepcopy(components_file))
        body["qualified_files"] = qualified
        body["calculation"] = {"calculation_id": components["calculation_id"],
            "input_numerical_sha256": components["input_numerical_sha256"], "components_file": deepcopy(components_file)}
        return {"kind": "comparison", "sheet": sheet, "components": components}

    def _saved_science(self, body, original, selector):
        result = None if body["worker"] is None else body["worker"]["result"]
        if result is None or result["sheet_file"] is None or result["components_file"] is None:
            return None
        descriptor = selector["saved_sheet"]
        sheet_file = result["sheet_file"]["file_identity"]
        components_file = result["components_file"]["file_identity"]
        _require(same(sheet_file, descriptor["sheet_file"]))
        sheet, components = self._json(sheet_file), self._json(components_file)
        baseline = self._json(descriptor["original_components_file"])
        _require(same(baseline, sheet["native_baseline"])
                 and same(baseline["parameters"], sheet["native_request"])
                 and same(components["parameters"], selector["parameters"]))
        validate_recorded_protein_structure_components(sheet, components=baseline)
        validate_recorded_protein_structure_components(sheet, components=components)
        qualified = _empty_files()
        qualified.update(native_file=deepcopy(original["body"]["qualified_files"]["native_file"]),
            sheet_file=deepcopy(descriptor["sheet_file"]),
            original_components_file=deepcopy(descriptor["original_components_file"]),
            components_file=deepcopy(components_file))
        body["qualified_files"] = qualified
        body["calculation"] = {"calculation_id": components["calculation_id"],
            "input_numerical_sha256": components["input_numerical_sha256"], "components_file": deepcopy(components_file)}
        return {"kind": "comparison", "sheet": sheet, "components": components}

    async def _original(self, action, context, target, body, *, collecting):
        validate_protein_structure_selected_inputs(self.store, context, body["intent"]["assignment"]["selector"],
            handoff_ref=body["intent"]["assignment"]["handoff_ref"], returns=self._returns)
        body["handoff_proof"] = self.receipts.read_handoff_proof(action, context=context, target=target)
        observation = self.receipts.read_observation(action)
        if observation is None:
            observation = self.owner.job_progress_provider.targets.observe_target(target, operation_key=body["intent"]["operation_key"])
            validate_resource_observation(observation)
            observation = self.receipts.record_observation(action, observation=observation)
        body.update(observation=observation, observation_origin="selected_native_observation")
        if not collecting:
            return None, None
        capture = capture_local_protein_structure_bundle(self.store, target=target, directory=action.capture_directory)
        capture = validate_protein_structure_capture(self.store, capture, target=target)
        body.update(capture=capture, capture_complete=capture["capture_complete"])
        body["issues"].extend(capture["failures"])
        if not capture["bundle_validated"]:
            return None, None
        bundle = validate_protein_structure_bundle(self._json(capture["bundle_file"]), plan=capture["original_plan"])
        body.update(bundle=bundle, native_success=bundle["returncode"] == 0 and bundle["native_status"] == "complete")
        body["issues"].extend(bundle["failures"])
        native_file = self._captured(capture, "native_result")
        plan = {"version": "protein_structure_result_worker_plan_v1", "mode": "original_native_result",
            "directory": str(action.worker_directory),
            "expected_request": deepcopy(bundle["requested_job"]["native_protein_structure"]["request"]),
            "expected_software": deepcopy(bundle["software"]), "native_result": None}
        if native_file is not None:
            plan["native_result"] = {"file_identity": native_file,
                "path": str(retained_protein_structure_file(self.store, native_file))}
        try:
            body["worker"] = await self._prepare_worker(action=action, plan=plan, policy=self._policy(target))
        except (ValueError, OSError) as error:
            body["issues"].append(_problem(error))
        self._worker_issues(body)
        scientific = None
        try:
            scientific = self._original_science(body)
        except (ValueError, OSError) as error:
            body["issues"].append(_problem(error, stage="native", field=None, role="native_result"))
            body["qualified_files"], body["calculation"] = _empty_files(), None
        worker_result = None if body["worker"] is None else body["worker"]["result"]
        source = publish_protein_structure_source(self.store, bundle=bundle, capture=capture, worker_result=worker_result)
        return scientific, self.store.get(source)

    @staticmethod
    def _worker_issues(body):
        if body["worker"] is not None:
            body["issues"].extend(body["worker"]["prepared"]["issues"])
            if body["worker"]["result"] is not None:
                body["issues"].extend(body["worker"]["result"]["issues"])

    async def _saved(self, action, context, target, body, *, collecting):
        selector = body["intent"]["assignment"]["selector"]
        descriptor = selector["saved_sheet"]
        self._returns.authenticate_received_saved_sheet(context, descriptor, required_use="recalculate")
        custody = descriptor["custody"]
        original = self.receipts.read_completed(episode_id=custody["result_episode_id"],
            operation_key=custody["result_operation_key"], scope=plain(context.scope))
        _require(same(custody, original["publication"]["custody"]))
        body["original_custody"] = deepcopy(custody)
        body["handoff_proof"] = self.receipts.read_handoff_proof(action, context=context, target=target)
        for name in ("bundle", "capture", "native_success", "capture_complete"):
            body[name] = deepcopy(original["body"][name])
        observation = original["body"]["observation"]
        if observation is not None:
            observation = self.receipts.record_observation(action, observation=observation)
        body.update(observation=observation,
            observation_origin="original_saved_observation" if observation is not None else "not_observed")
        source_record = deepcopy(original["publication"]["source_record"]) if collecting else None
        # Authority survives historical byte loss. Actual use of the pair is a
        # separate selected check and its failure leaves delivery incomplete.
        try:
            validate_protein_structure_selected_inputs(self.store, context, selector,
                handoff_ref=body["intent"]["assignment"]["handoff_ref"], returns=self._returns)
            if not collecting:
                return None, None
            plan = {"version": "protein_structure_result_worker_plan_v1", "mode": "saved_sheet_recalculation",
                "directory": str(action.worker_directory), "parameters": deepcopy(selector["parameters"]),
                "sheet": {"file_identity": deepcopy(descriptor["sheet_file"]),
                    "path": str(retained_protein_structure_file(self.store, descriptor["sheet_file"]))},
                "original_components": {"file_identity": deepcopy(descriptor["original_components_file"]),
                    "path": str(retained_protein_structure_file(self.store, descriptor["original_components_file"]))}}
            body["worker"] = await self._prepare_worker(action=action, plan=plan, policy=self._policy(target))
            self._worker_issues(body)
            scientific = self._saved_science(body, original, selector)
            return scientific, source_record
        except (ValueError, OSError) as error:
            body["issues"].append(_problem(error))
            body["qualified_files"], body["calculation"] = _empty_files(), None
            return None, source_record

    def _custody(self, body, source_record) -> ResultCustody | None:
        if source_record is None:
            return None
        intent = body["intent"]
        return {"run_id": intent["run_id"], "result_episode_id": intent["episode_id"],
            "result_operation_key": intent["operation_key"], "result_receipt_key": _result_key(intent),
            "handoff_ref": intent["assignment"]["handoff_ref"], "source_ref": source_record["id"],
            "bundle_artifact_ref": body["capture"]["bundle_file"]["artifact_ref"],
            "original_request_sha256": intent["original_request_sha256"]}

    def _publication(self, body, scientific, source_record, *, collecting):
        selector = body["intent"]["assignment"]["selector"]
        saved = selector["acquisition"] == "retained_sheet_only"
        facts, references = _empty_facts(), []
        custody = self._custody(body, source_record)
        accounting = {"projection_ids": [], "failed_projection_ids": [],
            "saved_sheet": "unavailable" if collecting and selector["return_saved_sheet"] else "not_requested",
            "sequence": "unavailable" if collecting and selector["sequence_allowed_uses"] else "not_requested"}
        if collecting and custody is not None and scientific is not None:
            if scientific["kind"] == "extraction" and selector["sequence_allowed_uses"]:
                files, sequence = body["qualified_files"], scientific["sequence"]
                if files["sequence_file"] is not None and files["residue_map_file"] is not None:
                    try:
                        reference = publish_structure_sequence_reference(self.store, source_ref=source_record["id"],
                            sequence=sequence, sequence_file=files["sequence_file"], residue_map_file=files["residue_map_file"])
                        descriptor = validate_structure_sequence_descriptor({"version": "structure_sequence_descriptor_v1",
                            "custody": deepcopy(custody), "reference_ref": reference,
                            "sequence_file": deepcopy(files["sequence_file"]), "residue_map_file": deepcopy(files["residue_map_file"]),
                            "structure_file": deepcopy(sequence["selection"]["file_identity"]),
                            "selection": deepcopy(sequence["selection"]), "sequence_length": sequence["sequence_length"],
                            "allowed_uses": deepcopy(selector["sequence_allowed_uses"])})
                        scientific["descriptor"] = descriptor
                        facts[SEQUENCE_SOURCE].append(descriptor)
                        references.append(self.store.get(reference))
                        accounting["sequence"] = "published"
                    except (ValueError, OSError) as error:
                        body["issues"].append(_problem(error, role="sequence"))
            if scientific["kind"] == "comparison" and selector["return_saved_sheet"]:
                descriptor = (deepcopy(selector["saved_sheet"]) if saved else validate_saved_sheet_descriptor({
                    "version": "protein_structure_saved_sheet_v1", "custody": deepcopy(custody),
                    "sheet_file": deepcopy(body["qualified_files"]["sheet_file"]),
                    "original_components_file": deepcopy(body["qualified_files"]["original_components_file"]),
                    "operation": "compare_protein_structures", "original_mode": scientific["sheet"]["scientific_mode"],
                    "allowed_uses": ["recalculate", "select_projection", "use_transform"]}))
                facts[SAVED_SOURCE].append(descriptor)
                accounting["saved_sheet"] = "published"
        if collecting:
            for name, role in (("saved_sheet", None), ("sequence", "sequence")):
                if accounting[name] == "unavailable":
                    body["issues"].append(issue("selected_field_unavailable", stage="projection", field="descriptor", artifact_role=role))
            operation_issues = _unique(body["issues"])
            # A failure in one requested population cannot discard another.
            for selection in selector["projections"]:
                try:
                    if scientific is None or custody is None:
                        raise ValueError("selected_field_unavailable")
                    rows, = project_protein_structure_results(scientific, selection=[selection])
                    value = publish_protein_structure_projection(self.store, rows=rows,
                        custody=custody, calculation=body["calculation"])
                except (ValueError, OSError) as error:
                    problem = _problem(error, stage="projection", field="projection_fields")
                    body["issues"].append(problem)
                    facts[FAILURE_SOURCE].append(validate_protein_structure_failure_return({
                        "version": "protein_structure_failure_return_v1", "custody": deepcopy(custody),
                        "projection_id": selection["projection_id"], "issue": problem}))
                    accounting["failed_projection_ids"].append(selection["projection_id"])
                else:
                    facts[PROJECTION_SOURCE].append(value)
                    accounting["projection_ids"].append(selection["projection_id"])
            body["issues"] = _unique(body["issues"])
            facts[FAILURE_SOURCE] = [validate_protein_structure_failure_return({
                "version": "protein_structure_failure_return_v1", "custody": deepcopy(custody),
                "projection_id": None, "issue": problem}) for problem in operation_issues] + facts[FAILURE_SOURCE]
        else:
            body["issues"] = _unique(body["issues"])
        worker_result = None if body["worker"] is None else body["worker"]["result"]
        complete = bool(collecting and custody is not None and body["handoff_proof"] is not None
            and worker_result is not None and (scientific is not None and scientific["kind"] == "comparison"
                if saved else body["capture_complete"]))
        return {"version": "protein_structure_result_publication_v1", "body_sha256": digest(body),
            "result_receipt_key": _result_key(body["intent"]), "custody": custody,
            "source_record": deepcopy(source_record), "reference_records": references, "facts": facts,
            "accounting": accounting, "record_refs": [] if source_record is None else [source_record["id"]],
            "family_artifact_refs": [], "delivery_complete": complete}

    def _family_artifacts(self, action, body, publication):
        references = []
        def add(value):
            if value is not None and value not in references:
                self.store._require(value, {"artifact"})
                references.append(value)
        capture = body["capture"]
        if capture is not None:
            if capture["bundle_file"] is not None:
                add(capture["bundle_file"]["artifact_ref"])
            for row in capture["files"]:
                if row["observed"] is not None:
                    add(row["observed"]["artifact_ref"])
        worker = body["worker"]
        if worker is not None:
            prepared, execution = worker["prepared"], worker["execution"]
            for name in ("plan_artifact_ref", "execution_receipt_artifact_ref", "worker_result_artifact_ref"):
                add(prepared[name])
            for row in prepared["diagnostic_files"]:
                add(row["artifact_ref"])
            for name in ("stdout_artifact_ref", "stderr_artifact_ref", "handle_artifact_ref"):
                add(execution[name])
            # 396 already retained these exact controls. Only their existing
            # identities join classification; no implicit artifact acquisition.
            paths = []
            if execution["handle_artifact_ref"] is not None:
                handle = decode_protein_structure_json(self.store.get_artifact(execution["handle_artifact_ref"]), canonical_bytes=False)
                paths.extend(Path(value) for value in handle["paths"].values())
            paths.append(action.worker_directory / "intent.json")
            for path in paths:
                _require(path.parent == action.worker_directory, "invalid_output_path")
                try:
                    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
                except FileNotFoundError:
                    continue
                try:
                    _require(stat.S_ISREG(os.fstat(fd).st_mode), "invalid_output_path")
                    with os.fdopen(os.dup(fd), "rb") as stream:
                        raw = stream.read()
                finally:
                    os.close(fd)
                ref = "artifact_" + hashlib.sha256(raw).hexdigest()
                try:
                    self.store._require(ref, {"artifact"})
                except ContractError as error:
                    if str(error) == "unknown_reference":
                        continue
                    raise
                add(ref)
        for file in body["qualified_files"].values():
            if file is not None:
                add(file["artifact_ref"])
        for projection in publication["facts"][PROJECTION_SOURCE]:
            if projection["delivery"]["kind"] == "artifact":
                add(projection["delivery"]["table_file"]["artifact_ref"])
        return references

    async def execute(self, context, target, tool_name, arguments, operation_key) -> dict:
        _require(self.applies(context) and is_native_protein_structure_target(target))
        request = target["assignment"]["requested_job"]["native_protein_structure"]["request"]
        selector = validate_protein_structure_result_selector(plain(context.assignment)["selector"], request=request)
        _require(tool_name in {row["name"] for row in operation_catalog()} and arguments == {})
        async with self.receipts.locked_action(context, target=target, tool_name=tool_name,
                arguments=arguments, operation_key=operation_key) as action:
            staged = self.receipts.read_staged(action)
            if staged is not None:
                return _outcome(staged)
            collecting = tool_name == "execution.results.collect"
            body: ProteinResultBody = {"version": "protein_structure_result_body_v1", "intent": deepcopy(action.intent),
                "handoff_proof": None, "observation": None, "observation_origin": "not_observed",
                "original_custody": None, "capture": None, "bundle": None, "worker": None,
                "qualified_files": _empty_files(), "calculation": None, "issues": [],
                "native_success": False, "capture_complete": False}
            scientific, source_record = None, None
            try:
                operation = self._saved if selector["acquisition"] == "retained_sheet_only" else self._original
                scientific, source_record = await operation(action, context, target, body, collecting=collecting)
            except (ValueError, OSError) as error:
                body["issues"].append(_problem(error))
            publication: ProteinResultPublication = self._publication(body, scientific, source_record, collecting=collecting)
            publication["family_artifact_refs"] = self._family_artifacts(action, body, publication)
            return _outcome(self.receipts.publish(action, body=body, publication=publication))

    def read_result_authority(self, custody: ResultCustody, *, scope: dict) -> ProteinResultAuthorityRecord:
        # The existing return schema validates the complete custody shape and
        # key formula without interpreting or opening its scientific operands.
        try:
            validate_protein_structure_failure_return({"version": "protein_structure_failure_return_v1",
                "custody": custody, "projection_id": None,
                "issue": issue("original_commission_mismatch", stage="authority", field="receipt")})
            _require(custody is not None and custody["run_id"] == self.owner.run_id)
            receipt = self.receipts.read_completed(episode_id=custody["result_episode_id"],
                operation_key=custody["result_operation_key"], scope=plain(scope))
            _require(same(custody, receipt["publication"]["custody"]))
        except (ValueError, TypeError, KeyError) as error:
            raise ProteinStructureOperandError(_problem(error, stage="authority", field="receipt")) from error
        body = receipt["body"]
        job = body["bundle"]["requested_job"]["native_protein_structure"]
        return deepcopy({"custody": custody, "selector": body["intent"]["assignment"]["selector"],
            "request": job["request"], "software": job["software"],
            **body["qualified_files"], "facts": receipt["publication"]["facts"]})

    def _verify_artifacts(self, receipt):
        body, publication = receipt["body"], receipt["publication"]
        files = body["qualified_files"]
        for projection in publication["facts"][PROJECTION_SOURCE]:
            names = ("sheet_file", "components_file") if projection["calculation"] is not None else ("native_file",)
            for name in names:
                _require(files[name] is not None)
                self._bytes(files[name], role="native_result" if name == "native_file" else None)
            if projection["delivery"]["kind"] == "artifact":
                table = self._json(projection["delivery"]["table_file"])
                _require(type(table) is dict and set(table) == {"version", "rows"}
                         and table["version"] == "protein_structure_projection_table_v1", "invalid_schema")
                envelope = {name: deepcopy(projection[name]) for name in ("projection_id", "family", "selection",
                    "coordinate_set", "requested_count", "matched_count", "returned_count", "omitted_count",
                    "state", "issues", "qualifications")}
                envelope.update(version="protein_structure_projection_rows_v1", rows=table["rows"],
                    calculation_id=None if projection["calculation"] is None else projection["calculation"]["calculation_id"])
                validate_protein_structure_projection_rows(envelope)
        for descriptor in publication["facts"][SAVED_SOURCE]:
            self._bytes(descriptor["sheet_file"])
            self._bytes(descriptor["original_components_file"])
        descriptors = list(publication["facts"][SEQUENCE_SOURCE])
        for projection in publication["facts"][PROJECTION_SOURCE]:
            if projection["delivery"]["kind"] == "values":
                descriptors.extend(field["value"] for row in projection["delivery"]["rows"] for field in row["values"]
                    if field["field"] == "descriptor" and field["value"] is not None)
        for descriptor in _unique(descriptors):
            _require(files["native_file"] is not None)
            self._bytes(files["native_file"], role="native_result")
            for name, role in (("sequence_file", "sequence"), ("residue_map_file", "residue_map"), ("structure_file", "single_structure")):
                self._bytes(descriptor[name], role=role)

    def own_fact_groups(self, context, *, verify_artifacts: bool) -> ProteinFactGroups:
        _require(type(verify_artifacts) is bool)
        facts = _empty_facts()
        for receipt in self.receipts.completed_receipts(context):
            if verify_artifacts:
                self._verify_artifacts(receipt)
            for source in FACT_SOURCES:
                facts[source].extend(receipt["publication"]["facts"][source])
        return {source: _unique(rows) for source, rows in facts.items()}

    def owns_reference(self, reference: str) -> bool:
        return self.receipts.owns_reference(reference)

    def facts(self, context, *, verify_artifacts: bool = True) -> dict:
        receipts = self.receipts.completed_receipts(context)
        requested = requested_sources(plain(context.request).get("report_contract", {}).get("measurements", {}).get("schema", {}))
        groups = _empty_facts()
        for receipt in receipts:
            if verify_artifacts:
                self._verify_artifacts(receipt)
            for source in requested:
                groups[source].extend(receipt["publication"]["facts"][source])
        return {**{source: _unique(rows) for source, rows in groups.items()},
            "execution_handoff_refs": [], "execution_blast_hsps": [],
            "execution_result_refs": list(dict.fromkeys(ref for receipt in receipts for ref in receipt["publication"]["record_refs"])),
            "execution_completed": any(receipt["publication"]["delivery_complete"] for receipt in receipts),
            "execution_result_origin": deepcopy(ORIGIN) if any(
                receipt["publication"]["delivery_complete"] and receipt["body"]["native_success"]
                and receipt["body"]["capture_complete"]
                and receipt["body"]["intent"]["assignment"]["selector"]["acquisition"] == "complete_bound_bundle"
                for receipt in receipts) else None}

    def credit_view(self, context, receiver_selection) -> dict:
        selection = self.owner._selection(context, receiver_selection)
        known, initial = set(selection["known_record_refs"]), set(selection["initial_known_record_refs"])
        acquired, inherited = set(), set()
        for receipt in self.receipts.completed_receipts(context):
            body, publication = receipt["body"], receipt["publication"]
            if (body["intent"]["assignment"]["selector"]["acquisition"] == "complete_bound_bundle"
                    and publication["source_record"] is not None and publication["source_record"]["id"] in known):
                acquired.add(digest(body["bundle"]["identity"]))
        # A source can have several original collections. Authenticate every
        # matching completed receipt; never choose a sorted-first source index.
        if initial:
            rows = self.store.db.execute("SELECT episode_id,decision_index,result FROM runtime_actions "
                "WHERE run_id=? AND result IS NOT NULL AND json_extract(result,'$.result.version')=? "
                "ORDER BY episode_id,decision_index", (self.owner.run_id, VERSION))
            for row in rows:
                candidate = json.loads(row["result"])["result"]
                if not set(candidate["publication"]["record_refs"]) & initial:
                    continue
                receipt = self.receipts.read_completed(episode_id=row["episode_id"],
                    operation_key=candidate["body"]["intent"]["operation_key"], scope=plain(context.scope))
                if receipt["body"]["bundle"] is not None:
                    inherited.add(digest(receipt["body"]["bundle"]["identity"]))
        count = len(acquired - inherited)
        value = self.owner.acquired_record_unit * count
        return {"credit": value, "operational_credit": value, "new_handoff_count": 0,
            "new_acquired_record_count": count, "operational_credit_binding": {"version": VERSION,
                "handoff_unit": self.owner.handoff_unit, "acquired_record_unit": self.owner.acquired_record_unit,
                "scientific_credit": False, "monitoring_credit": False}}

    def completion(self, context) -> dict | None:
        for receipt in self.receipts.completed_receipts(context):
            if receipt["publication"]["delivery_complete"]:
                intent = receipt["body"]["intent"]
                saved = intent["assignment"]["selector"]["acquisition"] == "retained_sheet_only"
                return {"version": "practical_completion_v1", "run_id": context.run_id, "episode_id": context.episode_id,
                    "assignment_sha256": digest(plain(context.assignment)), "endpoint": "usable_handoff",
                    "operation_key": intent["operation_key"], "receipt_sha256": digest(receipt),
                    "validation_keys": ["original_protein_result_commission",
                        "retained_original_sheet_custody" if saved else "complete_sealed_bundle_acquisition",
                        "requested_protein_projection_or_explicit_unavailability"]}
        return None


__all__ = ["NativeProteinStructureResults", "operation_catalog", "VERSION"]
