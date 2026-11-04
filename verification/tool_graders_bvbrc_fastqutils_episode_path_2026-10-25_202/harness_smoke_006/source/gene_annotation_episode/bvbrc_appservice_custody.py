"""Read-only custody of explicitly supplied AppService operands.

Existing action, commission and original typed-return records are the proof.
This module creates no receipt, observation, source, transport or scientific
fact. In particular, a received source reference never expands into its sheet.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re

from jsonschema import Draft202012Validator, ValidationError
from method_loop.episode import EpisodeGoal
from method_loop.identities import EpisodeRef

from .bvbrc_appservice_contracts import ContractValidationError, validate_contract
from .communication import REFERENCE_FORMATS, plain, validate_closed_schema, validate_form
from .domain import identity
from .episode_bindings import BindingContext
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import digest
from .launch_instructions import retain_inherited_selection


_PREFIX = "bvbrc_appservice_custody_"
_SERVICE = "bvbrc_appservice"
_SELECTOR = "bvbrc_appservice_result_selector_v1"


class AppServiceCustodyError(ValueError):
    """Stable, operand-free failure information for the consuming host."""

    def __init__(self, code, *, path=""):
        self.code = _PREFIX + code
        self.diagnostics = [{"code": self.code, "path": path}]
        super().__init__(self.code)


def _references(value, schema):
    if type(value) is dict:
        for key, child in value.items():
            yield from _references(child, schema.get("properties", {}).get(key, {}))
    elif type(value) is list:
        for child in value:
            yield from _references(child, schema.get("items", {}))
    elif type(value) is str and schema.get("format") in REFERENCE_FORMATS:
        yield value, schema.get("x-reference-namespace")


class AppServiceCustody(EpisodeReturnRecords):
    def __init__(self, store, run_id, *, read_original_handoff=None):
        super().__init__(store, run_id, failure_prefix=_PREFIX)
        self._require(type(run_id) is str and bool(run_id), "run_id_required")
        self._require(read_original_handoff is None or callable(read_original_handoff),
                      "handoff_reader_invalid")
        self.read_original_handoff = read_original_handoff

    def _require(self, condition, code):
        if not condition:
            raise AppServiceCustodyError(code)

    def _validate(self, name, value):
        try:
            return validate_contract(name, plain(value))
        except ContractValidationError as error:
            raise AppServiceCustodyError(error.code,
                path=error.diagnostics[0].get("path", "")) from error

    def _json(self, raw):
        def pairs(items):
            result = {}
            for key, value in items:
                self._require(key not in result, "duplicate_json_member")
                result[key] = value
            return result

        def number(value):
            result = float(value)
            self._require(math.isfinite(result), "nonfinite_json")
            return result

        def constant(_):
            raise AppServiceCustodyError("nonfinite_json")

        try:
            return json.loads(raw, object_pairs_hook=pairs, parse_float=number,
                              parse_constant=constant)
        except AppServiceCustodyError:
            raise
        except (ValueError, TypeError, UnicodeError, RecursionError) as error:
            raise AppServiceCustodyError("invalid_json") from error

    def _table(self, name):
        return self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                               (name,)).fetchone() is not None

    def authenticate(self, context, *, allow_unsaved=False):
        self._require(isinstance(context, BindingContext), "binding_context_required")
        self._require(type(plain(context.request).get("message")) is dict, "context_conflict")
        super().authenticate(context, allow_unsaved=allow_unsaved)
        saved = self.db.execute("SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                               (self.run_id, context.episode_id)).fetchone()
        if saved is None:
            # Workflow.build initializes before saving the child/action. Only
            # its exact already saved parent model selection may authorize that
            # interval; an arbitrary context or inherited ledger cannot.
            self._commission(context, unsaved=True)
        elif len(context.path) > 1 and context.role in {"launch", "launch_api", "results"}:
            self._commission(context)
        if context.role == "launch_api" and context.assignment.get("service") == _SERVICE:
            self._launch_context(context)
        return context

    def _commission(self, context, *, unsaved=False):
        self._require(len(context.path) > 1, "parent_commission_required")
        match = re.fullmatch(r"child_(0|[1-9][0-9]*)", context.path[-1][1])
        self._require(match is not None, "parent_commission_required")
        index = int(match[1])
        parent = self.context(EpisodeRef(self.run_id, context.path[:-1]).episode_id)
        action = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? "
            "AND episode_id=? AND decision_index=?", (self.run_id, parent.episode_id, index)).fetchone()
        call = self.db.execute("SELECT request,response,purpose FROM runtime_model_calls WHERE run_id=? "
            "AND episode_id=? AND call_index=?", (self.run_id, parent.episode_id, index)).fetchone()
        model = None
        if call is not None and call["response"] is not None:
            self._require(call["purpose"] == "decision", "parent_selection_purpose_conflict")
            response, sent = self._json(call["response"]), self._json(call["request"])
            self._require(type(response) is dict and type(sent) is dict and type(sent.get("schema")) is dict,
                          "parent_selection_schema_required")
            candidate = response.get("selection")
            if type(candidate) is dict and type(candidate.get("assignment")) is str:
                self._json(candidate["assignment"])
            # Reuse the runtime's exact transport normalization and the saved
            # original schema; today's catalog never rewrites old selections.
            from .runtime import _decode_action_response
            try:
                model = _decode_action_response(response, sent["schema"]).get("selection")
                Draft202012Validator(sent["schema"]["properties"]["selection"]).validate(model)
            except (ValidationError, ValueError, TypeError, KeyError) as error:
                raise AppServiceCustodyError("parent_selection_invalid") from error
        selected = None if action is None else self._json(action["action"])
        self._require(model is not None if unsaved else selected is not None or model is not None,
                      "saved_parent_selection_required")
        if selected is not None and model is not None:
            self._require(self._equal(selected, model), "parent_selection_conflict")
        selected = model if selected is None else selected
        self._require(type(selected) is dict and selected.get("kind") == "episode_child"
            and selected.get("role") == context.role, "commission_role_conflict")
        self._require(self._equal(selected.get("assignment"), context.assignment),
                      "commission_assignment_conflict")
        self._require(self._equal(selected.get("scope"), context.scope), "commission_scope_conflict")
        try:
            scope = self.store.validate_scope(plain(context.scope), parent_scope=plain(parent.scope))
            schema = validate_closed_schema(self._json(selected["schema_json"]))
            initial = self._json(selected["initial_report_json"])
            parent_goal = EpisodeGoal.from_record(plain(parent.request)["goal"])
            goal = EpisodeGoal.child(parent_goal, objective=selected["goal"], result_contract=schema)
        except AppServiceCustodyError:
            raise
        except (ValueError, TypeError, KeyError) as error:
            raise AppServiceCustodyError("commission_contract_invalid") from error
        request = plain(context.request)
        expected_contract = {"decision": selected.get("purpose"), "measurements": {"schema": schema},
            "information": {key: node.get("description", key) for key, node in schema["properties"].items()}}
        self._require(self._equal(scope, context.scope)
            and self._equal(request.get("goal"), goal.as_record())
            and self._equal(request.get("report_contract"), expected_contract)
            and self._equal(request["message"].get("initial_report"), initial), "commission_contract_conflict")
        self._require(set(request) == {"goal", "message", "report_contract"}
            and set(request["message"]) <= {"scope", "initial_report", "episode_assignment", "knowledge_inheritance"},
            "commission_message_conflict")
        self._inheritance(context, parent)
        if self._table("runtime_commission_intents"):
            row = self.db.execute("SELECT * FROM runtime_commission_intents WHERE run_id=? "
                "AND parent_episode_id=? AND original_decision_index=?", (self.run_id, parent.episode_id, index)).fetchone()
            if row is not None:
                from method_loop.durable import validate_commission, DurableExecutionError
                try:
                    spec = validate_commission(self._json(row["spec"]))
                except (DurableExecutionError, ValueError, TypeError, KeyError) as error:
                    raise AppServiceCustodyError("durable_commission_invalid") from error
                selected_identity = digest({"run_id": self.run_id, "parent_episode_id": parent.episode_id,
                                            "original_decision_index": index})
                self._require(self._equal(self._json(row["selection"]), selected)
                    and spec.get("run_id") == self.run_id and digest(spec) == row["commission_sha256"]
                    and row["handle"] == "execution_" + selected_identity
                    and row["operation_key"] == "commission_" + selected_identity
                    and spec.get("handle") == row["handle"] and spec.get("operation_key") == row["operation_key"]
                    and self._equal(spec.get("child", {}).get("request"), request)
                    and spec.get("child", {}).get("episode_id") == context.episode_id
                    and spec.get("child", {}).get("role") == context.role
                    and self._equal(spec.get("child", {}).get("path"), context.path)
                    and self._equal(spec.get("child", {}).get("scope"), context.scope)
                    and spec.get("parent", {}).get("episode_id") == parent.episode_id
                    and spec.get("parent", {}).get("goal_id") == parent_goal.goal_id
                    and self._equal(spec.get("parent", {}).get("path"), parent.path), "durable_commission_conflict")
        return parent, index

    def _inheritance(self, context, parent):
        manifest = plain(context.request)["message"].get("knowledge_inheritance")
        row = None if not self._table("runtime_receipt_inheritance") else self.db.execute(
            "SELECT parent_episode_id,through_receipt_index FROM runtime_receipt_inheritance "
            "WHERE run_id=? AND episode_id=?", (self.run_id, context.episode_id)).fetchone()
        if manifest is None and row is None:
            return None
        expected = None if row is None else {"version": "frozen_parent_receipt_prefix_v1",
            "parent_episode_id": row[0], "through_receipt_index": row[1]}
        self._require(row is not None and row[0] == parent.episode_id
            and self._equal(manifest, expected), "commission_inheritance_conflict")
        return row[1]

    def _before(self, before):
        self._require(before is None or type(before) is int and before >= 0, "before_index_invalid")

    def _record(self, reference):
        self._require(type(reference) is str and bool(reference), "reference_required")
        try:
            value = self.store.get(reference)
        except (ValueError, KeyError, OSError) as error:
            raise AppServiceCustodyError("reference_unavailable") from error
        self._require(value.get("id") == reference, "record_identity_conflict")
        return value

    def _own(self, context, reference, *, before=None, tool=None):
        sql = ("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND decision_index>=0 AND result IS NOT NULL "
            "AND EXISTS (SELECT 1 FROM json_each(result,'$.record_refs') WHERE value=?)")
        args = [self.run_id, context.episode_id, reference]
        if before is not None:
            sql += " AND decision_index<?"
            args.append(before)
        for row in self.db.execute(sql, args):
            action, result = self._json(row["action"]), self._json(row["result"])
            if (action.get("kind") in {"tool", "reason"} and result.get("status") in {"completed", "partial"}
                    and (tool is None or action.get("tool") == tool)):
                return True
        return False

    def possession(self, context, reference, *, before=None):
        """Prove reference custody; this never projects fields from its content."""
        self._before(before)
        return self._possession(context, reference, before=before, visiting=())

    def _possession(self, context, reference, *, before, visiting):
        self.authenticate(context, allow_unsaved=True)
        record = self._record(reference)
        key = context.episode_id, reference
        self._require(key not in visiting, "cyclic_possession")
        visiting = (*visiting, key)
        if self._own(context, reference, before=before):
            return "own_completed_action"
        rows = self.db.execute("SELECT decision_index FROM runtime_report_attempts WHERE run_id=? "
            "AND parent_episode_id=? AND failure IS NULL AND form IS NOT NULL "
            "AND EXISTS (SELECT 1 FROM json_tree(form) WHERE type='text' AND value=?) "
            "ORDER BY decision_index", (self.run_id, context.episode_id, reference))
        for row in rows:
            if before is not None and row[0] >= before:
                continue
            child, form, schema = self._attempt(context, row[0])
            # _attempt authenticates the original immediate-child return and
            # frozen facts. context() additionally verifies execution-role
            # commissions; generic child/process.revise returns retain their
            # own existing construction contract, not an AppService shape.
            try:
                validate_form(form, schema, lambda *_: True)
            except (ValueError, TypeError) as error:
                raise AppServiceCustodyError("received_form_invalid") from error
            namespaces = {None, record.get("record_type")}
            if record.get("record_type") == "source":
                namespaces |= {"execution_result", "execution_handoff", "bvbrc_appservice_support"}
            if any(ref == reference and namespace in namespaces for ref, namespace in _references(form, schema)):
                self._possession(child, reference, before=None, visiting=visiting)
                return "admitted_return"
        references, _, _ = self._inputs(context)
        if reference in references:
            parent, index = self._commission(context)
            self._possession(parent, reference, before=index, visiting=visiting)
            cutoff = self._inheritance(context, parent)
            if cutoff is not None:
                # This prefix constrains time only. It supplies no possession
                # by itself, and cannot replace the action/typed-return proof.
                receipt = self.db.execute("SELECT 1 FROM runtime_record_receipts WHERE run_id=? "
                    "AND episode_id=? AND record_ref=? AND receipt_index<=?",
                    (self.run_id, parent.episode_id, reference, cutoff)).fetchone()
                self._require(receipt is not None, "input_not_received_before_commission")
            return "parent_assignment"
        raise AppServiceCustodyError("input_not_possessed")

    def _inputs(self, context):
        """Only named schema operands; never walk arbitrary JSON for strings."""
        assignment = plain(context.assignment)
        references, contents, evidence = [], [], []

        def content(binding):
            if binding is not None:
                contents.append(binding)
                references.append(binding["source_ref"])

        def source(binding):
            if binding is not None:
                evidence.append(binding)
                content(binding["content"])

        def obj(selection):
            if selection is not None:
                for field in ("receipt_ref", "manifest_receipt_ref"):
                    if field in selection:
                        references.append(selection[field])

        def request(value):
            if value.get("service") != _SERVICE:
                return
            value = self._validate("AppServiceRequest", value.get("request"))
            for item in value["definition_inputs"]:
                source(item["evidence"])
            for item in value["input_bindings"]:
                content(item["content"])
                source(item["link_evidence"])
                for member in item["members"]:
                    source(member["evidence"])

        if context.role == "launch" and assignment.get("version") == "execution_launch_assignment_v1":
            self._require(type(assignment.get("requests")) is dict, "original_launch_assignment_required")
            for value in assignment["requests"].values():
                self._require(type(value) is dict, "original_launch_assignment_required")
                request(value)
        elif context.role == "launch_api" and assignment.get("version") == "api_service_assignment_v1":
            request(assignment)
        elif (context.role == "results" and assignment.get("version") == "execution_results_assignment_v1"
                and assignment.get("selector", {}).get("version") == _SELECTOR):
            selector = self._validate("ResultSelector", assignment["selector"])
            references.append(assignment["handoff_ref"])
            for item in selector["requirements"]:
                source(item["producer_rule_evidence"])
                obj(item["exact_object"])
                declared = item["declared_format"]
                if declared["producer_source_ref"] is not None:
                    references.append(declared["producer_source_ref"])
                for binding in declared["transformation_evidence"]:
                    source(binding)
            for binding in selector["supplied_metadata"]:
                source(binding)
            for binding in selector.get("supplied_contents", []):
                content(binding)
            for item in selector["supplied_capabilities"]:
                source(item["url_evidence"])
                references.append(item["original_handoff_ref"])
                obj(item["object_selection"])
                association = item["task_association"]
                if association["evidence_ref"] is not None:
                    references.append(association["evidence_ref"])
                for binding in association["version_evidence"]:
                    source(binding)
        return list(dict.fromkeys(references)), contents, evidence

    def initial_references(self, context):
        self.authenticate(context, allow_unsaved=True)
        references, contents, evidence = self._inputs(context)
        for reference in references:
            self.possession(context, reference)
        for binding in contents:
            self.content(context, binding)
        for binding in evidence:
            self.evidence(context, binding)
        return references

    def content(self, context, binding, *, before=None):
        binding = self._validate("ContentBinding", binding)
        self.possession(context, binding["source_ref"], before=before)
        source = self._record(binding["source_ref"])
        self._require(source.get("record_type") == "source", "content_source_required")
        payload = {key: value for key, value in source.items() if key not in {"id", "record_type", "origin"}}
        self._require(source.get("origin") is not None and identity("source", {
            "origin": source["origin"], "record": payload}) == binding["source_ref"], "source_identity_conflict")
        self._require(source.get(binding["artifact_field"]) == binding["artifact_ref"], "artifact_field_conflict")
        artifact = self._record(binding["artifact_ref"])
        self._require(artifact.get("record_type") == "artifact", "artifact_required")
        try:
            raw = self.store.get_artifact(binding["artifact_ref"])
        except (ValueError, KeyError, OSError) as error:
            if isinstance(error, ValueError) and str(error) == "artifact_digest_mismatch":
                raise AppServiceCustodyError("input_bytes_mismatch") from error
            raise AppServiceCustodyError("input_bytes_unavailable") from error
        sha = hashlib.sha256(raw).hexdigest()
        self._require(binding["artifact_ref"] == "artifact_" + sha and artifact.get("sha256") == sha
            and binding["sha256"] == sha and type(artifact.get("size")) is int
            and artifact["size"] == len(raw) == binding["byte_count"], "input_bytes_mismatch")
        return raw

    def evidence(self, context, binding, *, before=None):
        binding = self._validate("SourceEvidence", binding)
        value = self._json(self.content(context, binding["content"], before=before))
        for part in binding["pointer"].split("/")[1:]:
            part = part.replace("~1", "/").replace("~0", "~")
            if type(value) is dict:
                self._require(part in value, "evidence_pointer_unavailable")
                value = value[part]
            elif type(value) is list:
                self._require(re.fullmatch(r"0|[1-9][0-9]*", part) is not None, "evidence_array_index_invalid")
                self._require(int(part) < len(value), "evidence_pointer_unavailable")
                value = value[int(part)]
            else:
                raise AppServiceCustodyError("evidence_pointer_unavailable")
        return deepcopy(value)

    def _launch_context(self, context):
        if context.role == "launch":
            self._require(context.assignment.get("version") == "execution_launch_assignment_v1",
                          "original_launch_assignment_required")
            return context
        self._require(context.role == "launch_api"
            and context.assignment.get("version") == "api_service_assignment_v1"
            and context.assignment.get("service") == _SERVICE, "original_launch_context_required")
        parent, _ = self._commission(context)
        self._require(parent.role == "launch" and parent.assignment.get("version") ==
                      "execution_launch_assignment_v1", "original_launch_context_required")
        assignment, original = plain(context.assignment), plain(parent.assignment)
        resource = assignment.get("resource_id")
        self._require(resource in original["requests"], "original_resource_conflict")
        expected = {**original["requests"][resource], "resource_id": resource}
        self._require(self._equal({k: v for k, v in assignment.items() if k != "launch_instructions"},
            {k: v for k, v in expected.items() if k != "launch_instructions"}), "original_request_conflict")
        try:
            retain_inherited_selection(original.get("launch_instructions"), assignment.get("launch_instructions"))
            retain_inherited_selection(expected.get("launch_instructions"), assignment.get("launch_instructions"))
        except (ValueError, TypeError) as error:
            raise AppServiceCustodyError("original_instructions_conflict") from error
        constraints = original["constraints"]
        self._require(("allowed_resource_ids" not in constraints or resource in constraints["allowed_resource_ids"])
            and ("allowed_kinds" not in constraints or "api" in constraints["allowed_kinds"])
            and ("resource_id" not in constraints or resource == constraints["resource_id"])
            and ("kind" not in constraints or constraints["kind"] == "api"), "original_resource_conflict")
        for key, value in constraints.items():
            if key not in {"allowed_resource_ids", "allowed_kinds", "resource_id", "kind"}:
                self._require(key in assignment["constraints"] and self._equal(assignment["constraints"][key], value),
                              "original_constraint_conflict")
        self._validate("AppServiceRequest", assignment.get("request"))
        return parent

    def original_job_owner(self, context):
        self.authenticate(context, allow_unsaved=True)
        if context.role == "results":
            self._require(context.assignment.get("version") == "execution_results_assignment_v1"
                and context.assignment.get("selector", {}).get("version") == _SELECTOR,
                "original_results_assignment_required")
            self._commission(context)
            reference = context.assignment["handoff_ref"]
            self.possession(context, reference)
            self._require(self.read_original_handoff is not None, "original_handoff_reader_unbound")
            value = self.read_original_handoff(reference)
            self._require(type(value) is dict and value.get("reference") == reference,
                          "original_handoff_reference_conflict")
            origin = value.get("origin_context")
            if type(origin) is dict:
                try:
                    origin = BindingContext(**origin)
                except (ValueError, TypeError) as error:
                    raise AppServiceCustodyError("original_handoff_context_invalid") from error
            self.authenticate(origin)
            self._require(origin.role == "launch_api" and self._own(origin, reference,
                tool="api.bvbrc_appservice.submit"), "original_submission_action_required")
            owner = self.original_job_owner(origin)
            self._require(self._equal(self._validate("OriginalJobOwner", value.get("original_job_owner")), owner),
                          "original_handoff_owner_conflict")
            return owner
        launch = self._launch_context(context)
        parent, index = self._commission(launch)
        return self._validate("OriginalJobOwner", {"run_id": self.run_id,
            "launch_episode_id": launch.episode_id,
            "parent_commission_operation_key": f"{self.run_id}:{parent.episode_id}:{index}",
            "original_launch_assignment_sha256": digest(launch.assignment)})


__all__ = ["AppServiceCustody", "AppServiceCustodyError"]
