"""One selected retained comparison action inside the existing results role.

Original inputs and actions establish authority. The separate worker owns only
deterministic calculation/publication. No native observation or acquisition runs.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .communication import plain, validate_form
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest, obj
from .local_jobs import LocalJobPolicy
from .native_rna_structure_result_publication import authenticate_rna_results_commission
from .practical_execution_state import _immutable, _read
from .rna_structure_comparison_contracts import (
    CALCULATOR_VERSION, SELECTOR_VERSION, validate_rna_comparison_issue,
    validate_rna_comparison_selector,
)
from .rna_structure_comparison_operands import (
    RNAComparisonInputError, SAVED_REFERENCE_FIELDS, _require,
    resolve_rna_comparison_operands, validate_rna_comparison_selected_inputs,
)
from .rna_structure_comparison_views import PROJECTION_SOURCE

VERSION = "rna_structure_comparison_result_receipt_v1"
IDENTIFIER_NAMESPACES = ("rna_comparison_receipt", "rna_comparison_calculation")
FIELDS = {"version", "run_id", "episode_id", "scope_key", "assignment_digest", "operation_key",
    "tool_name", "arguments", "selected_action_digest", "anchor_handoff_ref", "selector",
    "original_receipt_keys", "selected_input_digests", "comparison_sheet_artifact_ref",
    "comparison_sheet_sha256", "components_artifact_ref", "components_sha256", "calculator_version",
    "projection_rows", "issues", "preparation_failure", "delivery_complete"}
PREPARED_COPY_FIELDS = ("original_receipt_keys", "selected_input_digests",
    "comparison_sheet_artifact_ref", "comparison_sheet_sha256", "components_artifact_ref",
    "components_sha256", "calculator_version", "projection_rows", "issues", "preparation_failure", "delivery_complete")
VALIDATION_KEYS = ["selected_original_operand_authority", "retained_operand_custody",
    "requested_comparison_projection_or_explicit_unavailability"]
POLICY = {"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}


def result_receipt_key(body):
    return "rna_comparison_receipt:" + digest({key: body[key] for key in ("run_id", "episode_id", "operation_key")})


def operation_catalog():
    return [{"name": "execution.results.status", "description":
        "Check only the explicitly selected retained RNA inputs and recorded comparison receipts.", "input_schema": obj({})},
        {"name": "execution.results.collect", "description":
        "Calculate the assigned comparison from independently received retained sheets and return exactly its selected projections.",
        "input_schema": obj({})}]


def _original_keys(selector):
    return [member["saved_input" if member["kind"] == "saved_sheet" else "failure"]["result_receipt_key"]
        for member in selector["question"]["membership"] if member["kind"] in {"saved_sheet", "received_failure"}]


class NativeRNAStructureComparisonResults:
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store
        self.directory = owner.directory / "rna-structure-comparison-result-index"
        self.records = EpisodeReturnRecords(owner.store, owner.run_id, failure_prefix="rna_comparison_")

    @property
    def returns(self):
        return self.owner.native_rna_structure_returns

    def applies(self, context):
        return context.role == "results" and plain(context.assignment).get("selector", {}).get("version") == SELECTOR_VERSION

    def _directory(self, context):
        return self.owner._result_directory(context) / "rna-structure-comparison-actions"

    def _saved_directory(self, episode_id, operation_key):
        return (self.owner.directory / "execution-results" / digest([self.owner.run_id, episode_id]) /
            "rna-structure-comparison-actions" / digest(operation_key))

    def _assignment(self, context, *, allow_unsaved=False):
        authenticate_rna_results_commission(self.store, context, allow_unsaved=allow_unsaved)
        _require(self.applies(context), "original_results_owner_required")
        assignment = plain(context.assignment)
        _require(set(assignment) == {"version", "handoff_ref", "selector"}
            and assignment["version"] == "execution_results_assignment_v1", "selected_assignment_conflict")
        selector = validate_rna_comparison_selector(assignment["selector"])
        validate_rna_comparison_selected_inputs(self.store, context, selector,
            anchor_handoff_ref=assignment["handoff_ref"], returns=self.returns)
        return assignment

    def _resolve_operands(self, context, assignment):
        return resolve_rna_comparison_operands(self.store, context, assignment["selector"],
            anchor_handoff_ref=assignment["handoff_ref"], returns=self.returns)

    def _policy(self, target):
        config = self.owner.resources[target["resource_id"]]
        _require(config["kind"] == "local" and config["policy"] == POLICY, "policy_mismatch")
        return LocalJobPolicy(**config["policy"])

    def _intent(self, context, assignment, target, operation_key, tool_name, arguments, selected):
        return {"run_id": context.run_id, "episode_id": context.episode_id,
            "scope": plain(context.scope), "assignment": assignment, "anchor_target": target,
            "operation_key": operation_key, "tool_name": tool_name, "arguments": arguments,
            "selected_action_digest": digest(json.loads(selected["action"]))}

    @staticmethod
    def _outcome(body):
        return {"status": "completed", "record_refs": [], "changed_record_refs": [],
            "result": deepcopy(body), "feedback": None}

    def _validate_body(self, body, scope):
        _require(type(body) is dict and set(body) == FIELDS and body["version"] == VERSION
            and body["run_id"] == self.owner.run_id, "receipt_mismatch")
        context = self.records.context(body["episode_id"])
        assignment = self._assignment(context)
        self.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
        _require(body["scope_key"] == digest(plain(context.scope))
            and body["assignment_digest"] == digest(assignment)
            and body["anchor_handoff_ref"] == assignment["handoff_ref"]
            and self.records._equal(body["selector"], assignment["selector"]), "receipt_mismatch")
        _require(body["tool_name"] in {item["name"] for item in operation_catalog()}
            and type(body["arguments"]) is dict and not body["arguments"], "selected_action_mismatch")
        selected = self.owner._selected_result_action(body["episode_id"], body["operation_key"],
            body["tool_name"], body["arguments"])
        _require(body["selected_action_digest"] == digest(json.loads(selected["action"])), "selected_action_mismatch")
        directory = self._saved_directory(body["episode_id"], body["operation_key"])
        target = self.owner.job_progress_provider.targets.read_target(assignment["handoff_ref"], context.scope)
        expected_intent = self._intent(context, assignment, target, body["operation_key"],
            body["tool_name"], body["arguments"], selected)
        _require(self.records._equal(_read(directory / "intent.json"), expected_intent)
            and self.records._equal(_read(directory / "receipt.json"), body), "immutable_receipt_mismatch")
        if selected["result"] is not None:
            outcome, expected = json.loads(selected["result"]), self._outcome(body)
            _require(set(outcome) in (set(expected), {*expected, "pending_work_after_action"})
                and self.records._equal({key: outcome[key] for key in expected}, expected), "recorded_outcome_mismatch")
            if "pending_work_after_action" in outcome:
                from .waiting import validate_pending
                validate_pending(outcome["pending_work_after_action"])
        _require(body["original_receipt_keys"] == _original_keys(assignment["selector"])
            and body["calculator_version"] == CALCULATOR_VERSION and type(body["delivery_complete"]) is bool,
            "receipt_mismatch")
        for issue in body["issues"]:
            validate_rna_comparison_issue(issue)
        if body["tool_name"] == "execution.results.status" or (directory / "input-failure.json").exists():
            status = body["tool_name"] == "execution.results.status"
            failure = _read(directory / ("status.json" if status else "input-failure.json"))
            _require(type(failure) is dict and set(failure) == {"issues", "cause"}
                and self.records._equal(failure["issues"], body["issues"]), "custody_record_mismatch")
            if failure["issues"]:
                _require(len(failure["issues"]) == 1 and type(failure["cause"]) is dict
                    and set(failure["cause"]) == {"exception_type", "detail"}, "custody_record_mismatch")
                problem = failure["issues"][0]
                expected = {"stage": "input", "code": problem["code"], "member_id": problem["member_id"],
                    "comparison_id": None, "selection_id": None, "field": None, "index": None}
                _require(problem == expected and problem["code"] in {"retained_sheet_missing", "retained_sheet_digest_mismatch"}
                    and any(m["member_id"] == problem["member_id"] and m["kind"] == "saved_sheet"
                        for m in assignment["selector"]["question"]["membership"]), "custody_record_mismatch")
            else:
                _require(status and failure["cause"] is None, "custody_record_mismatch")
            _require(not body["delivery_complete"] and body["projection_rows"] == []
                and body["selected_input_digests"] == [] and body["preparation_failure"] is None
                and all(body[key] is None for key in ("comparison_sheet_artifact_ref", "comparison_sheet_sha256",
                    "components_artifact_ref", "components_sha256")), "receipt_mismatch")
        else:
            from .rna_structure_comparison_publication import validate_prepared_rna_comparison
            operands = self._resolve_operands(context, assignment)
            prepared = _read(directory / "grading" / "prepared.json")
            validate_prepared_rna_comparison(self.store, prepared, selector=assignment["selector"],
                operands=operands, result_receipt_key=result_receipt_key(body))
            _require(all(self.records._equal(body[key], prepared[key]) for key in PREPARED_COPY_FIELDS), "prepared_receipt_mismatch")
        return deepcopy(body)

    async def execute(self, context, target, tool_name, arguments, operation_key):
        assignment = self._assignment(context)
        _require(target == self.owner._target(context) and target["handle"] == assignment["handoff_ref"], "anchor_mismatch")
        _require(tool_name in {item["name"] for item in operation_catalog()}
            and type(arguments) is dict and not arguments, "invalid_operation")
        selected = self.owner._selected_result_action(context.episode_id, operation_key, tool_name, arguments)
        policy = self._policy(target)
        directory = self._directory(context) / digest(operation_key)
        directory.mkdir(parents=True, exist_ok=True)
        _immutable(directory / "intent.json", self._intent(context, assignment, target,
            operation_key, tool_name, arguments, selected))
        if (directory / "receipt.json").exists():
            body = self._validate_body(_read(directory / "receipt.json"), context.scope)
        else:
            body = {"version": VERSION, "run_id": context.run_id, "episode_id": context.episode_id,
                "scope_key": digest(plain(context.scope)), "assignment_digest": digest(assignment),
                "operation_key": operation_key, "tool_name": tool_name, "arguments": {},
                "selected_action_digest": digest(json.loads(selected["action"])),
                "anchor_handoff_ref": assignment["handoff_ref"], "selector": assignment["selector"],
                "original_receipt_keys": _original_keys(assignment["selector"]), "selected_input_digests": [],
                "comparison_sheet_artifact_ref": None, "comparison_sheet_sha256": None,
                "components_artifact_ref": None, "components_sha256": None,
                "calculator_version": CALCULATOR_VERSION, "projection_rows": [], "issues": [],
                "preparation_failure": None, "delivery_complete": False}
            failure_path = directory / "input-failure.json"
            saved_failure = _read(failure_path) if failure_path.exists() else None
            if saved_failure is not None:
                body["issues"] = saved_failure["issues"]
            else:
                failure = {"issues": [], "cause": None}
                try:
                    operands = self._resolve_operands(context, assignment)
                except RNAComparisonInputError as error:
                    failure = {"issues": [error.issue], "cause": {
                        "exception_type": type(error.__cause__).__name__, "detail": str(error.__cause__)}}
                    body["issues"] = failure["issues"]
                    if tool_name == "execution.results.collect":
                        _immutable(directory / "input-failure.json", failure)
                if tool_name == "execution.results.status":
                    _immutable(directory / "status.json", failure)
                elif not body["issues"]:
                    from .rna_structure_comparison_publication import (
                        prepare_rna_comparison_grading, publish_selected_rna_comparison_rows,
                    )
                    prepared = prepare_rna_comparison_grading(self.store, selector=assignment["selector"],
                        operands=operands, result_receipt_key=result_receipt_key(body), directory=directory / "grading", policy=policy)
                    rows = publish_selected_rna_comparison_rows(self.store, selector=assignment["selector"],
                        prepared=prepared, operands=operands, result_receipt_key=result_receipt_key(body))
                    _require(self.records._equal(rows, prepared["projection_rows"]), "projection_mismatch")
                    body.update({key: deepcopy(prepared[key]) for key in PREPARED_COPY_FIELDS})
            _immutable(directory / "receipt.json", body)
            body = self._validate_body(body, context.scope)
        pointer = {key: body[key] for key in ("run_id", "episode_id", "operation_key")}
        index = self.directory / digest(result_receipt_key(body))
        index.mkdir(parents=True, exist_ok=True)
        _immutable(index / (digest(operation_key) + ".json"), pointer)
        return self._outcome(body)

    def read_result(self, context, result):
        self.records.authenticate(context, allow_unsaved=True)
        _require(type(result) is dict and result.get("episode_id") == context.episode_id
            and result.get("assignment_digest") == digest(plain(context.assignment)), "original_context_conflict")
        return self._validate_body(result, context.scope)

    def read_receipt_key(self, key, scope, *, assignment=None):
        directory = self.directory / digest(key)
        for path in sorted(directory.glob("*.json")) if directory.exists() else []:
            pointer = _read(path)
            _require(type(pointer) is dict and set(pointer) == {"run_id", "episode_id", "operation_key"}
                and pointer["run_id"] == self.owner.run_id, "receipt_pointer_mismatch")
            body = self._validate_body(_read(self._saved_directory(pointer["episode_id"], pointer["operation_key"]) / "receipt.json"), scope)
            _require(key == result_receipt_key(body), "receipt_pointer_mismatch")
            if assignment is None or body["assignment_digest"] == digest(plain(assignment)):
                return body
        raise ValueError("rna_comparison_original_receipt_mismatch")

    def _own_bodies(self, context):
        self.records.authenticate(context, allow_unsaved=True)
        _require(self.applies(context), "original_results_owner_required")
        directory = self._saved_directory(context.episode_id, "unused").parent
        bodies = [_read(path) for path in directory.glob("*/receipt.json")] if directory.exists() else []
        for body in sorted(bodies, key=lambda item: int(item["operation_key"].rsplit(":", 1)[1])):
            _require(body["episode_id"] == context.episode_id and body["assignment_digest"] == digest(plain(context.assignment)), "receipt_mismatch")
            yield self._validate_body(body, context.scope)

    def facts(self, context, *, verify_artifacts=True):
        # Authority and actual calculation are always checked. The argument
        # preserves the host port; it is not a validation bypass.
        requested = {node.get("x-source") for node in (plain(context.request).get("report_contract") or {})
            .get("measurements", {}).get("schema", {}).get("properties", {}).values()}
        bodies = list(self._own_bodies(context))
        rows, seen, completed = [], set(), False
        for body in bodies:
            action = self.owner._selected_result_action(context.episode_id, body["operation_key"], body["tool_name"], body["arguments"])
            if action["result"] is None:
                continue
            completed = completed or body["delivery_complete"]
            if PROJECTION_SOURCE in requested:
                for row in body["projection_rows"]:
                    identity = canonical({key: value for key, value in row.items() if key != "result_receipt_key"})
                    if identity not in seen:
                        rows.append(row)
                        seen.add(identity)
        return {PROJECTION_SOURCE: rows, "execution_handoff_refs": [], "execution_blast_hsps": [],
            "execution_result_refs": [], "execution_completed": completed, "execution_result_origin": None}

    def resolve(self, context, reference, namespace):
        if not self.applies(context) or namespace not in IDENTIFIER_NAMESPACES:
            return False
        field = "result_receipt_key" if namespace == IDENTIFIER_NAMESPACES[0] else "calculation_key"
        return any(row[field] == reference for row in self.facts(context)[PROJECTION_SOURCE])

    def retained_reference_access(self, context, reference, namespace):
        # Symbolic receipt identities confer no Store custody, even when a
        # caller supplies an artifact/source namespace for the same string.
        if any(reference.startswith(prefix + ":") for prefix in IDENTIFIER_NAMESPACES):
            return self.resolve(context, reference, namespace)
        if namespace not in {None, "artifact", "source", "execution_result", "execution_handoff"}:
            return None
        if self.applies(context):
            assignment = plain(context.assignment)
            selected = [assignment["handoff_ref"]]
            selected_handoffs = {assignment["handoff_ref"]}
            for member in assignment["selector"]["question"]["membership"]:
                if member["kind"] == "saved_sheet":
                    selected.extend(member["saved_input"][key] for key in SAVED_REFERENCE_FIELDS)
                    selected_handoffs.add(member["saved_input"]["handoff_ref"])
                elif member["kind"] == "received_failure" and member["failure"]["source_ref"] is not None:
                    selected.append(member["failure"]["source_ref"])
            if namespace == "execution_handoff" and reference not in selected_handoffs:
                return False
            if reference in selected:
                allowed = validate_rna_comparison_selected_inputs(self.store, context, assignment["selector"],
                    anchor_handoff_ref=assignment["handoff_ref"], returns=self.returns)
                record = self.store.get(reference)
                return reference in allowed and namespace in {None, "execution_result", record["record_type"],
                    *({"execution_handoff"} if reference in selected_handoffs else set())}
        # Comparison artifacts are internal, and are absent from admitted refs.
        # Recognize exact recorded custody without opening their scientific data.
        for action in self.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND "
                "json_extract(result,'$.result.version')=?", (self.owner.run_id, VERSION)):
            body = json.loads(action["result"])["result"]
            grading = self._saved_directory(body["episode_id"], body["operation_key"]) / "grading"
            prepared_path = grading / "prepared.json"
            prepared = _read(prepared_path) if prepared_path.exists() else None
            refs = {body[key] for key in ("comparison_sheet_artifact_ref", "components_artifact_ref")}
            if prepared is not None:
                refs.update(value for key, value in prepared.items() if key.endswith("artifact_ref"))
            # Fixed host custody metadata names every internal worker artifact.
            # Do not open scientific inputs, projections, logs or source trees.
            worker_path = grading / "worker-receipt.json"
            if worker_path.exists():
                worker = _read(worker_path)
                refs.update(value for key, value in worker.items() if key.endswith("artifact_ref"))
                refs.update(row["artifact_ref"] for row in worker["output_artifacts"])
                refs.add(worker["input_observation"]["artifact_ref"])
            execution_path = grading / "execution-receipt.json"
            if execution_path.exists():
                execution = _read(execution_path)
                refs.update(execution[key] for key in ("stdout_artifact_ref", "stderr_artifact_ref"))
            if reference in refs:
                return self._independent_artifact_access(context, reference, namespace)
        return None

    def _independent_artifact_access(self, context, reference, namespace):
        """Preserve actual explicit custody of identical content-addressed bytes."""
        self.records.authenticate(context, allow_unsaved=True)
        if namespace not in {None, "artifact", "execution_result"}:
            return False
        old = self.owner.native_rna_structure_results.retained_reference_access(context, reference, namespace)
        if old is not None:
            return old
        assignment = plain(context.assignment)
        explicit = {row.get("artifact_ref") for row in
            assignment.get("requested_job", {}).get("native_rna_structure", {}).get("operands", [])}
        if reference in explicit:
            from .native_rna_structure_result_publication import validate_rna_structure_job_inputs
            return reference in validate_rna_structure_job_inputs(self.store, context, assignment)
        if reference in self.store._refs(assignment) and reference in set(
                EpisodeReceipts(self.store, context.run_id).known(context.episode_id, baseline=True)):
            return True
        scope = self.store.validate_scope(plain(context.scope))
        if any(self.store.get(subject).get("sequence_ref") == reference for subject in scope.get("subject_refs", [])):
            return namespace in {None, "artifact"}
        for action in self.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL",
                (context.run_id, context.episode_id)):
            outcome = json.loads(action["result"])
            if outcome.get("status") in {"completed", "partial"} and reference in outcome.get("record_refs", []):
                body = outcome.get("result")
                if isinstance(body, dict) and body.get("version") == VERSION:
                    self._validate_body(body, context.scope)
                return True
        old = self.returns.resolve_received(context, reference, namespace)
        if old is not None:
            return old
        from .native_rna_structure_returns import requested_sources
        for attempt in self.returns._attempts(context):
            schema = json.loads(attempt["contract"]).get("measurements", {}).get("schema", {})
            if requested_sources(schema) or any(node.get("x-source") == PROJECTION_SOURCE
                    for node in schema.get("properties", {}).values()):
                continue
            _, form, schema = self.returns._attempt(context, attempt["decision_index"])
            explicit_refs = []
            def collect(value, declared_namespace):
                if declared_namespace in {None, "artifact"}:
                    explicit_refs.append(value)
                return True
            validate_form(form, schema, collect)
            if reference in explicit_refs:
                return True
        return False

    def credit_view(self, context, receiver_selection):
        self._assignment(context, allow_unsaved=True)
        selection = plain(receiver_selection)
        _require(type(selection) is dict and all(type(selection.get(key)) is list
            and all(type(ref) is str for ref in selection[key]) for key in ("known_record_refs", "initial_known_record_refs"))
            and set(selection["initial_known_record_refs"]) <= set(selection["known_record_refs"]), "invalid_receiver_selection")
        return {"credit": 0, "operational_credit": 0, "new_handoff_count": 0, "new_acquired_record_count": 0,
            "operational_credit_binding": {"version": VERSION, "handoff_unit": self.owner.handoff_unit,
                "acquired_record_unit": self.owner.acquired_record_unit, "scientific_credit": False, "monitoring_credit": False}}

    def completion(self, context):
        for body in self._own_bodies(context):
            selected = self.owner._selected_result_action(context.episode_id, body["operation_key"], body["tool_name"], body["arguments"])
            if body["tool_name"] == "execution.results.collect" and body["delivery_complete"] and selected["result"] is not None:
                return {"version": "practical_completion_v1", "run_id": context.run_id, "episode_id": context.episode_id,
                    "assignment_sha256": digest(plain(context.assignment)), "endpoint": "usable_handoff",
                    "operation_key": body["operation_key"], "receipt_sha256": digest(body), "validation_keys": list(VALIDATION_KEYS)}
        return None


__all__ = ["NativeRNAStructureComparisonResults", "operation_catalog", "result_receipt_key", "VERSION", "IDENTIFIER_NAMESPACES"]
