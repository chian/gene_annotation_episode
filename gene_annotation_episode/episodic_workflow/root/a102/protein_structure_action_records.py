"""Ordinary protein action views and received descriptor authority.

Scientific rows and calculations belong to the existing protein modules. This
adapter authenticates original actions and typed deliveries; public Source
custody never creates an execution episode, handoff or File permission.
"""
from copy import deepcopy
import json
import math
import re
from pathlib import Path

from jsonschema import Draft202012Validator, validators

from .communication import plain, ReportBoundaryError
from .domain import canonical, identity
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import digest
from . import protein_structure_contracts as science
from . import protein_structure_result_views as views
from .protein_structure_authority import ProteinStructureOperandError


VIEW_SOURCE = "protein_structure_action_views"
SEQUENCE_SOURCE = "protein_structure_action_sequences"
SAVED_SOURCE = "protein_structure_action_saved_sheets"
FACT_SOURCES = (VIEW_SOURCE, SEQUENCE_SOURCE, SAVED_SOURCE)
TOOLS = {"inspect_protein_structure": "inspect",
    "extract_protein_structure_sequence": "extract_sequence", "compare_protein_structures": "compare"}
RESULT_VERSION = "protein_structure_tool_result_v1"
SAVED_ACTION_SOURCE_VERSION = "protein_structure_saved_action_v1"
_PAYLOAD_FIELDS = {VIEW_SOURCE: "views", SEQUENCE_SOURCE: "sequences", SAVED_SOURCE: "saved_sheets"}


def _error(code="original_commission_mismatch", *, field="receipt"):
    return ProteinStructureOperandError(science.issue(code, stage="authority", field=field))


def _require(condition, code="original_commission_mismatch", *, field="receipt"):
    if not condition:
        raise _error(code, field=field)


def _object(**properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def _definitions():
    # Reuse shared row/cell schemas. Only this opt-in resource admits action
    # descriptors; the default legacy public resources are untouched.
    definitions = views._schema("ProjectionRows")["$defs"]
    definitions.update(science.protein_structure_schema_definitions(action_custody=True))
    ref = lambda name: {"$ref": "#/$defs/" + name}
    artifact = deepcopy(definitions["ProjectionRows"]["oneOf"])
    artifacts = []
    for row_ref in artifact:
        row_type = deepcopy(definitions[row_ref["$ref"].rsplit("/", 1)[1]])
        properties = row_type["properties"]
        properties.pop("rows")
        properties["version"] = {"const": "protein_structure_action_artifact_view_v1"}
        properties["delivery"] = ref("ArtifactDelivery")
        row_type["required"] = list(properties)
        artifacts.append(row_type)
    definitions["ProteinActionArtifactView"] = {"oneOf": artifacts}
    definitions["ProteinActionUnavailable"] = _object(
        version={"const": "protein_structure_action_unavailable_v1"},
        issues={"type": "array", "items": ref("StructuredIssue"), "minItems": 1})
    definitions["ProteinActionView"] = _object(
        version={"const": "protein_structure_action_view_v1"},
        source_ref={"type": "string", "format": "reference", "x-reference-namespace": "source",
            "pattern": "^source_[a-f0-9]{24,64}$"},
        operation={"enum": list(TOOLS.values())}, selection=ref("ProjectionSelection"),
        outcome={"oneOf": [ref("ProjectionRows"), ref("ProteinActionArtifactView"), ref("ProteinActionUnavailable")]})
    definitions["ProteinActionResult"] = _object(
        version={"const": RESULT_VERSION},
        source_ref=deepcopy(definitions["ProteinActionView"]["properties"]["source_ref"]),
        operation={"enum": list(TOOLS.values())},
        views={"type": "array", "items": ref("ProteinActionView")},
        sequences={"type": "array", "items": ref("StructureSequenceDescriptorV2")},
        saved_sheets={"type": "array", "items": ref("SavedSheetDescriptorV2")},
        issues={"type": "array", "items": ref("StructuredIssue")})
    return definitions


def _schema(name):
    return {"$defs": _definitions(), "$ref": "#/$defs/" + name}


def _shape(name, value):
    science._json_only(value)
    strict = validators.extend(Draft202012Validator, type_checker=
        Draft202012Validator.TYPE_CHECKER.redefine("integer", lambda _, item: type(item) is int)
        .redefine("number", lambda _, item: type(item) in (int, float) and math.isfinite(item)))
    if not strict(_schema(name)).is_valid(value):
        raise ValueError("invalid_schema")


def _reachable_definitions(definitions, name):
    pending, selected = [name], set()
    while pending:
        name = pending.pop()
        if name in selected:
            continue
        selected.add(name)
        nodes = [definitions[name]]
        while nodes:
            value = nodes.pop()
            if isinstance(value, dict):
                reference = value.get("$ref")
                if isinstance(reference, str) and reference.startswith("#/$defs/"):
                    pending.append(reference[len("#/$defs/"):])
                nodes.extend(value.values())
            elif isinstance(value, list):
                nodes.extend(value)
    return {name: deepcopy(value) for name, value in definitions.items() if name in selected}


def protein_structure_action_fact_sources():
    names = {VIEW_SOURCE: "ProteinActionView", SEQUENCE_SOURCE: "StructureSequenceDescriptorV2",
        SAVED_SOURCE: "SavedSheetDescriptorV2"}
    meanings = {VIEW_SOURCE: "Exactly selected retained protein values or selected-table identity from an authenticated ordinary action.",
        SEQUENCE_SOURCE: "Original structure-derived sequence descriptor and explicitly selected allowed uses from an authenticated ordinary action.",
        SAVED_SOURCE: "Original protein saved-sheet descriptor with declared uses; Source custody does not itself grant Files or authority."}
    result = {}
    for source, name in names.items():
        resource = {"$defs": _reachable_definitions(_definitions(), name), "type": "array", "items": {"$ref": "#/$defs/" + name}}
        resource["$id"] = "urn:gene-annotation:protein-action:" + digest(resource)
        document = {"$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": deepcopy(resource["$defs"]), "type": "array", "allOf": [resource], "x-source": source}
        document["$id"] = "urn:gene-annotation:protein-action:" + digest(document)
        result[source] = dict(type="array", meaning=meanings[source], report_schema=document)
    return result


def validate_protein_structure_action_view(value):
    _shape("ProteinActionView", value)
    selection, outcome = value["selection"], value["outcome"]
    views.validate_protein_structure_projection_selection(selection)
    kind, family = value["operation"], selection["family"]
    if (kind == "inspect" and family != "structure_inventory"
            or kind == "extract_sequence" and family not in {"extracted_sequence", "native_uncertainty"}
            or kind == "compare" and family in {"structure_inventory", "extracted_sequence"}
            or family == "native_uncertainty" and (kind == "extract_sequence") != (
                selection["members"]["structure_role"] == "single")):
        raise ValueError("invalid_schema")
    if outcome["version"] == "protein_structure_action_unavailable_v1":
        science._relations(outcome)
        return deepcopy(value)
    if not science.same(selection, outcome["selection"]):
        raise ValueError("conflicting_identity")
    if outcome["version"] == "protein_structure_projection_rows_v1":
        if selection["delivery_kind"] != "values":
            raise ValueError("conflicting_identity")
        views.validate_protein_structure_projection_rows(outcome)
    else:
        if selection["delivery_kind"] != "artifact":
            raise ValueError("conflicting_identity")
        views._envelope(outcome, None)
        delivery = outcome["delivery"]
        science.validate_file_identity(delivery["table_file"])
        if (delivery["table_file"]["format"] != "protein_structure_projection_table_v1"
                or delivery["row_count"] != outcome["returned_count"]
                or "artifact_descriptor_not_numerical_delivery" not in outcome["qualifications"]):
            raise ValueError("conflicting_identity")
    return deepcopy(value)


def protein_structure_action_view_identity(value):
    value = validate_protein_structure_action_view(value)
    return value["source_ref"], canonical(value["selection"])


def validate_protein_structure_tool_result(value):
    _shape("ProteinActionResult", value)
    keys = []
    for item in value["views"]:
        validate_protein_structure_action_view(item)
        if item["source_ref"] != value["source_ref"] or item["operation"] != value["operation"]:
            raise ValueError("conflicting_identity")
        keys.append(protein_structure_action_view_identity(item))
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate_selection")
    for field, version, operation, validator in (
            ("sequences", "structure_sequence_descriptor_v2", "extract_sequence", science.validate_structure_sequence_descriptor_v2),
            ("saved_sheets", "protein_structure_saved_sheet_v2", "compare", science.validate_saved_sheet_descriptor_v2)):
        if value[field] and value["operation"] != operation:
            raise ValueError("conflicting_identity")
        for item in value[field]:
            validator(item)
            if item["version"] != version or item["custody"]["source_ref"] != value["source_ref"]:
                raise ValueError("conflicting_identity")
        if len(value[field]) > 1:
            raise ValueError("duplicate_selection")
    return deepcopy(value)


def action_view_from_projection_rows(rows, *, source_ref, operation, table_file=None):
    rows = views.validate_protein_structure_projection_rows(rows)
    if rows["selection"]["delivery_kind"] == "values":
        if table_file is not None:
            raise ValueError("conflicting_identity")
        outcome = rows
    else:
        if table_file is None:
            raise ValueError("selected_field_unavailable")
        science.validate_file_identity(table_file)
        outcome = {key: deepcopy(item) for key, item in rows.items() if key != "rows"}
        outcome.update(version="protein_structure_action_artifact_view_v1", delivery=dict(kind="artifact",
            table_file=deepcopy(table_file), row_count=rows["returned_count"], allowed_use="read_exact_selected_table"))
    return validate_protein_structure_action_view(dict(version="protein_structure_action_view_v1",
        source_ref=source_ref, operation=operation, selection=deepcopy(rows["selection"]), outcome=outcome))


def project_protein_structure_action_views(scientific, *, source_ref, operation, selections,
                                         issues=(), artifact_files=None):
    if type(selections) is not list or len({item["projection_id"] for item in selections}) != len(selections):
        raise ValueError("duplicate_selection")
    output = []
    for selection in selections:
        selection = views.validate_protein_structure_projection_selection(selection)
        if scientific is None:
            selected_issues = list(deepcopy(issues)) or [science.issue("selected_field_unavailable", stage="projection", field="projection_fields")]
            item = dict(version="protein_structure_action_view_v1", source_ref=source_ref, operation=operation,
                selection=selection, outcome=dict(version="protein_structure_action_unavailable_v1", issues=selected_issues))
        else:
            try:
                rows, = views.project_protein_structure_results(scientific, selection=[selection])
            except ValueError as error:
                from typing import get_args
                code = str(error) if str(error) in get_args(science.IssueCode) else "invalid_schema"
                item = dict(version="protein_structure_action_view_v1", source_ref=source_ref, operation=operation,
                    selection=selection, outcome=dict(version="protein_structure_action_unavailable_v1",
                        issues=[science.issue(code, stage="projection", field="projection_fields")]))
            else:
                table = None if artifact_files is None else artifact_files.get(selection["projection_id"])
                item = action_view_from_projection_rows(rows, source_ref=source_ref, operation=operation, table_file=table)
        output.append(validate_protein_structure_action_view(item))
    return output


def _validate_fact(value, fact_source):
    if fact_source == VIEW_SOURCE:
        return validate_protein_structure_action_view(value)
    if fact_source == SEQUENCE_SOURCE:
        return science.validate_structure_sequence_descriptor_v2(value)
    if fact_source == SAVED_SOURCE:
        return science.validate_saved_sheet_descriptor_v2(value)
    raise ValueError("invalid_schema")


def _fact_source_ref(value, fact_source):
    return value["source_ref"] if fact_source == VIEW_SOURCE else value["custody"]["source_ref"]


def merge_protein_structure_action_facts(*groups, fact_source):
    result, seen = [], {}
    for group in groups:
        _require(type(group) is list, "invalid_schema")
        for item in group:
            item = _validate_fact(item, fact_source)
            source = _fact_source_ref(item, fact_source)
            key = (protein_structure_action_view_identity(item) if fact_source == VIEW_SOURCE else
                (source, item["reference_ref"]) if fact_source == SEQUENCE_SOURCE else source)
            encoded = canonical(item)
            _require(key not in seen or seen[key] == encoded)
            if key not in seen:
                result.append(item)
                seen[key] = encoded
    return result


def requested_protein_structure_action_fields(schema, *, fact_source):
    if fact_source not in FACT_SOURCES:
        raise ValueError("invalid_schema")
    properties = plain(schema).get("properties", {})
    if not any(isinstance(node, dict) and node.get("x-source") == fact_source for node in properties.values()):
        return []
    expected = protein_structure_action_fact_sources()[fact_source]["report_schema"]
    fields = []
    for name, node in properties.items():
        if node.get("x-source") == fact_source:
            _require(science.same(node, expected), "invalid_schema")
            fields.append(name)
    return fields


def protein_structure_action_form_references(form, schema):
    """Project typed references after the caller's frozen-value admission check.

    This projection is not producer authority and never grants File identities
    or private publication controls. Existing native/received owners perform
    the actual value and receipt checks before this specialist hook is called.
    """
    form, references = plain(form), []
    for source in FACT_SOURCES:
        for field in requested_protein_structure_action_fields(schema, fact_source=source):
            _require(type(form) is dict and field in form and type(form[field]) is list, "invalid_schema")
            for value in form[field]:
                value = _validate_fact(value, source)
                references.append(_fact_source_ref(value, source))
                if source == SEQUENCE_SOURCE:
                    references.append(value["reference_ref"])
    return list(dict.fromkeys(references))


def _artifact(store, reference, *, format="text"):
    from .native_protein_structure_acquisition import retained_protein_structure_file
    metadata = store.get(reference)
    _require(metadata.get("record_type") == "artifact", "invalid_schema")
    file = dict(artifact_ref=reference, sha256=metadata["sha256"], byte_length=metadata["size"], format=format)
    raw = retained_protein_structure_file(store, file).read_bytes()
    import hashlib
    _require(len(raw) == file["byte_length"] and hashlib.sha256(raw).hexdigest() == file["sha256"], "input_digest_mismatch")
    return raw


def _json_artifact(store, reference):
    from .native_protein_structure_acquisition import decode_protein_structure_json
    return decode_protein_structure_json(_artifact(store, reference), canonical_bytes=True)


class ProteinStructureActionRecords(EpisodeReturnRecords):
    """Ordinary action authority, with optional real legacy Results authority."""

    def __init__(self, store, run_id, *, legacy_returns=None):
        super().__init__(store, run_id, failure_prefix="protein_structure_action_")
        if legacy_returns is not None:
            _require(legacy_returns.store is store and legacy_returns.run_id == run_id)
        self.legacy_returns = legacy_returns

    @property
    def owner(self):
        _require(self.legacy_returns is not None)
        return self.legacy_returns.owner

    def _require(self, condition, code=None):
        _require(condition)

    def authenticate(self, context, *, allow_unsaved=False):
        super().authenticate(context, allow_unsaved=allow_unsaved)
        _require(context.role == context.path[-1][0])
        self.store.validate_scope(plain(context.scope))
        if self.legacy_returns is not None:
            self.legacy_returns.authenticate(context, allow_unsaved=allow_unsaved)
        return context

    def _known(self, context):
        self.authenticate(context, allow_unsaved=True)
        receipts = EpisodeReceipts.__new__(EpisodeReceipts)
        receipts.store, receipts.db, receipts.run_id = self.store, self.db, self.run_id
        return set(receipts.known(context.episode_id))

    def _rows(self, context, *, before_decision_index=None):
        self.authenticate(context)
        _require(before_decision_index is None or type(before_decision_index) is int
            and before_decision_index >= 0, "invalid_schema")
        return self.db.execute("SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? "
            "AND episode_id=? AND json_extract(action,'$.kind')='tool' "
            "AND json_extract(action,'$.tool') IN (SELECT value FROM json_each(?)) "
            "AND json_extract(result,'$.status') IN ('completed','partial') "
            "AND json_extract(result,'$.result.version')=? AND (? IS NULL OR decision_index<?) ORDER BY decision_index",
            (context.run_id, context.episode_id, canonical(list(TOOLS)), RESULT_VERSION,
                before_decision_index, before_decision_index))

    def _action(self, context, row):
        action, outcome = json.loads(row["action"]), json.loads(row["result"])
        key = f'{context.run_id}:{context.episode_id}:{row["decision_index"]}'
        operation = self.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (key,)).fetchone()
        expected = identity("operation", dict(key=key, name=action["tool"], arguments=action["arguments"]))
        _require(operation is not None and action["tool"] in TOOLS and operation["id"] == expected
            and operation["name"] == action["tool"] and outcome.get("operation_ref") == expected
            and operation["arguments"] == canonical(action["arguments"])
            and operation["scope"] == canonical(plain(context.scope))
            and operation["result"] == canonical({k: v for k, v in outcome.items() if k != "pending_work_after_action"}))
        result = validate_protein_structure_tool_result(outcome["result"])
        _require(result["operation"] == TOOLS[action["tool"]] and result["source_ref"] in outcome["record_refs"])
        mode = action["arguments"].get("mode")
        if mode == "read_stored":
            original = self.read_stored_result(context, action["arguments"]["result_ref"],
                before_decision_index=row["decision_index"])
            _require(science.same(result, original["result"]) and outcome["status"] == original["status"]
                and science.same(outcome.get("feedback"), original["feedback"])
                and outcome["record_refs"] == [result["source_ref"]]
                and outcome.get("changed_record_refs") == [])
        elif mode == "select_projection" and result["source_ref"] == action["arguments"]["result_ref"]:
            inputs = self.saved_action_inputs(context, action["arguments"]["saved_sheet"],
                required_use="select_projection", before_decision_index=row["decision_index"],
                result_ref=action["arguments"]["result_ref"])
            original = inputs["basis"]["published"]
            _require(science.same(action["arguments"]["projections"],
                [view["selection"] for view in original["result"]["views"]])
                and science.same(result, original["result"]) and outcome["status"] == original["status"]
                and science.same(outcome.get("feedback"), original["feedback"])
                and outcome["record_refs"] == [result["source_ref"]]
                and outcome.get("changed_record_refs") == [])
        return action, outcome, result

    def authenticate_saved_operation(self, context, *, operation_key, name, arguments, scope, outcome):
        """Read a committed ToolOperation even before its action result is saved."""
        self.authenticate(context)
        prefix = f"{context.run_id}:{context.episode_id}:"
        _require(type(operation_key) is str and operation_key.startswith(prefix)
            and re.fullmatch(r"0|[1-9][0-9]*", operation_key[len(prefix):]) is not None
            and name in TOOLS and science.same(plain(scope), plain(context.scope)))
        index = int(operation_key[len(prefix):])
        row = self.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
            (context.run_id, context.episode_id, index)).fetchone()
        _require(row is not None)
        action = json.loads(row["action"])
        _require(science.same(action, dict(kind="tool", tool=name, arguments=plain(arguments))))
        operation = self.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (operation_key,)).fetchone()
        normalized = {key: value for key, value in plain(outcome).items() if key != "pending_work_after_action"}
        expected = identity("operation", dict(key=operation_key, name=name, arguments=plain(arguments)))
        _require(operation is not None and operation["id"] == expected and operation["name"] == name
            and operation["arguments"] == canonical(plain(arguments))
            and operation["scope"] == canonical(plain(context.scope))
            and operation["result"] == canonical(normalized) and normalized.get("operation_ref") == expected)
        if row["result"] is not None:
            recorded = {key: value for key, value in json.loads(row["result"]).items() if key != "pending_work_after_action"}
            _require(science.same(recorded, normalized))
        result = normalized.get("result")
        if type(result) is dict and result.get("version") == RESULT_VERSION:
            from .protein_structure_publication import _ordinary_record
            result = validate_protein_structure_tool_result(result)
            _require(result["operation"] == TOOLS[name] and result["source_ref"] in normalized["record_refs"])
            source = _ordinary_record(self.store, result["source_ref"], "source")
            _require(source["provider"] == "episode.execution_result" and source["version"] in {
                "native_protein_structure_bundle_v1", SAVED_ACTION_SOURCE_VERSION})
            if arguments.get("mode") == "read_stored" or (arguments.get("mode") == "select_projection"
                    and result["source_ref"] == arguments.get("result_ref")):
                self._action(context, dict(action=canonical(action), result=canonical(normalized), decision_index=index))
            else:
                self._publication(dict(context=context, action=action, outcome=normalized, result=result,
                    source=source, decision_index=index))
        return deepcopy(plain(outcome))

    def _producer(self, source_ref, *, verify_artifacts):
        from .protein_structure_publication import _ordinary_record
        source = _ordinary_record(self.store, source_ref, "source")
        _require(source["provider"] == "episode.execution_result" and source["version"] in {
            "native_protein_structure_bundle_v1", SAVED_ACTION_SOURCE_VERSION})
        rows = list(self.db.execute("SELECT a.run_id,a.episode_id,a.decision_index,a.action,a.result "
            "FROM runtime_actions a JOIN tool_operations t ON t.operation_key=a.run_id||':'||a.episode_id||':'||a.decision_index "
            "WHERE t.name IN (SELECT value FROM json_each(?)) AND json_extract(a.result,'$.status') IN ('completed','partial') "
            "AND json_extract(a.result,'$.result.version')=? AND json_extract(a.result,'$.result.source_ref')=? "
            "AND coalesce(json_extract(a.action,'$.arguments.mode'),'native')!='read_stored' "
            "AND NOT(coalesce(json_extract(a.action,'$.arguments.mode'),'native')='select_projection' "
            "AND json_extract(a.action,'$.arguments.result_ref')=json_extract(a.result,'$.result.source_ref'))",
            (canonical(list(TOOLS)), RESULT_VERSION, source_ref)))
        _require(len(rows) == 1)
        row, = rows
        records = EpisodeReturnRecords(self.store, row["run_id"], failure_prefix="protein_structure_action_producer_")
        context = records.context(row["episode_id"])
        action, outcome, result = self._action(context, row)
        value = dict(context=context, action=action, outcome=outcome, result=result, source=source,
            decision_index=row["decision_index"])
        if verify_artifacts:
            value.update(self._publication(value))
        return value

    def _publication(self, producer):
        if producer["source"]["version"] == SAVED_ACTION_SOURCE_VERSION:
            return self._saved_publication(producer)
        from .native_protein_structure_contracts import (validate_protein_structure_bundle,
            validate_native_protein_structure_result, validate_protein_structure_run_plan)
        from .protein_structure_publication import protein_structure_source_payload, _ordinary_record
        from .protein_structure_calculations import validate_recorded_protein_structure_components
        from .native_protein_structure_acquisition import retained_protein_structure_file
        from .native_protein_structure_preparation import validate_prepared_protein_structure_worker
        source, context, action = producer["source"], producer["context"], producer["action"]
        capsule = _json_artifact(self.store, source["request_ref"])
        _require(type(capsule) is dict and set(capsule) == {"version", "invocation", "tool_name", "arguments", "scope",
            "binding", "plan", "execution", "capture", "worker", "qualified_files"}
            and capsule["version"] == "protein_structure_action_publication_v1")
        invocation = dict(run_id=context.run_id, episode_id=context.episode_id,
            operation_key=f'{context.run_id}:{context.episode_id}:{producer["decision_index"]}',
            request_sha256=digest(plain(context.request)))
        _require(science.same(capsule["invocation"], invocation) and capsule["tool_name"] == action["tool"]
            and science.same(capsule["arguments"], action["arguments"])
            and science.same(capsule["scope"], plain(context.scope)))
        plan = validate_protein_structure_run_plan(capsule["plan"])
        _require(all(plan["identity"][name] == invocation[name] for name in ("run_id", "episode_id", "operation_key")))
        bundle = validate_protein_structure_bundle(_json_artifact(self.store, source["artifact_ref"]), plan=plan)
        job, binding, args = bundle["requested_job"]["native_protein_structure"], capsule["binding"], action["arguments"]
        _require(science.same(job["request"], args["request"]) and science.same(job["software"], binding["software"])
            and binding["resource_id"] == args["resource_id"]
            and plan["identity"]["resource_id"] == binding["resource_id"]
            and type(args["binding_ordinal_0based"]) is int and binding["binding_ordinal_0based"] == args["binding_ordinal_0based"]
            and binding["operation"] == producer["result"]["operation"]
            and science.same(binding["environment"], job["environment"]) and science.same(binding["policy"], plan["policy"]))
        capture, worker = capsule["capture"], capsule["worker"]
        _require(science.same(capture["original_plan"], plan)
            and capture["bundle_file"]["artifact_ref"] == source["artifact_ref"])
        controls = capsule["execution"]["artifacts"]
        _require(capsule["execution"]["terminal"] is True and capsule["execution"]["quiescent"] is True
            and science.same(_json_artifact(self.store, controls["ordinary-execution.json"]),
                {key: value for key, value in capsule["execution"].items() if key != "artifacts"}))
        binding_control = _json_artifact(self.store, controls["ordinary-tool-binding.json"])
        expected_selector = dict(version="protein_structure_result_selector_v1", acquisition="complete_bound_bundle",
            saved_sheet=None, parameters=None, **args["selection"])
        _require(science.same(binding_control, dict(version="ordinary_protein_structure_binding_v1", invocation=invocation,
            tool_name=action["tool"], arguments=args, scope=plain(context.scope), binding_sha256=digest(binding),
            requested_job_sha256=digest(bundle["requested_job"]), selector=expected_selector)))
        worker_result = None if worker is None else worker["result"]
        if worker is not None:
            worker_store = self._original_worker_store(worker, capture)
            _require(science.same(validate_prepared_protein_structure_worker(worker_store,
                worker["prepared"], plan=worker["plan"]), worker)
                and worker["plan"]["mode"] == "original_native_result"
                and science.same(worker["plan"]["expected_request"], job["request"])
                and science.same(worker["plan"]["expected_software"], job["software"]))
        expected_source = protein_structure_source_payload(bundle=bundle, capture=capture,
            worker_result=worker_result, request_ref=source["request_ref"])
        _require(science.same({k: v for k, v in source.items() if k not in {"id", "record_type", "origin"}}, expected_source))
        _require(len(capture["files"]) == len(bundle["files"]))
        capture_failures = []
        for index, row in enumerate(capture["files"]):
            _require(row["manifest_index_0based"] == index and science.same(row["declared"], bundle["files"][index]))
            declared, observed = row["declared"], row["observed"]
            if declared["state"] == "absent":
                _require(observed is None)
                outcome, failure = "declared_absent", None
            elif observed is None:
                outcome, failure = "unavailable", science.issue("capture_incomplete", stage="capture",
                    field="manifest", artifact_role=declared["role"])
            else:
                science.validate_file_identity(row["observed"])
                _require(observed["format"] == declared["format"])
                equal = all(observed[key] == declared[key] for key in ("sha256", "byte_length"))
                outcome, failure = ("verified", None) if equal else ("digest_mismatch",
                    science.issue("input_digest_mismatch", stage="capture", field="manifest", artifact_role=declared["role"]))
            _require(row["outcome"] == outcome and science.same(row["issue"], failure))
            if failure is not None:
                capture_failures.append(failure)
        _require(science.same(capture["failures"], capture_failures)
            and capture["capture_complete"] is (not capture_failures))
        files, scientific, native_issues = capsule["qualified_files"], None, []
        for file in files.values():
            if file is not None:
                retained_protein_structure_file(self.store, file)
        if files["native_file"] is not None:
            _require(worker_result is not None and worker_result["native_result_file"] is not None
                and science.same(files["native_file"], worker_result["native_result_file"]["file_identity"]))
            native = validate_native_protein_structure_result(_json_artifact(self.store, files["native_file"]["artifact_ref"]))
            native_issues = deepcopy(native["issues"])
            _require(science.same(native["request"], job["request"]) and science.same(native["producer"], job["software"]))
            operation = job["request"]["operation"]
            if operation == "inspect":
                scientific = dict(kind="inspection", inventory=native["inventory"])
            elif operation == "extract_sequence":
                scientific = dict(kind="extraction", sequence=native["sequence"], metadata=native["metadata"], descriptor=None)
            elif files["sheet_file"] is not None and files["components_file"] is not None:
                sheet = _json_artifact(self.store, files["sheet_file"]["artifact_ref"])
                components = _json_artifact(self.store, files["components_file"]["artifact_ref"])
                _require(science.same(sheet, native["sheet"]) and science.same(components, sheet["native_baseline"])
                    and science.same(files["original_components_file"], files["components_file"])
                    and science.same(files["sheet_file"], worker_result["sheet_file"]["file_identity"])
                    and science.same(files["components_file"], worker_result["components_file"]["file_identity"]))
                validate_recorded_protein_structure_components(sheet, components=components)
                scientific = dict(kind="comparison", sheet=sheet, components=components)
        result, selection = producer["result"], args["selection"]
        expected_sequences, expected_saved = [], []
        custody = dict(version="protein_structure_action_custody_v1", source_ref=source["id"])
        if scientific is not None and scientific["kind"] == "extraction" and selection["sequence_allowed_uses"]:
            sequence = scientific["sequence"]
            if sequence["sequence_available"] and files["sequence_file"] is not None and files["residue_map_file"] is not None:
                for role, field in (("sequence", "sequence_file"), ("residue_map", "residue_map_file")):
                    selected = [row["observed"] for row in capture["files"] if row["declared"]["role"] == role
                        and row["observed"] is not None]
                    _require(len(selected) == 1 and science.same(selected[0], files[field]))
                _require(_artifact(self.store, files["sequence_file"]["artifact_ref"]) == sequence["alignment_sequence"].encode("ascii")
                    and _artifact(self.store, files["residue_map_file"]["artifact_ref"]) == canonical(sequence).encode())
                payload = dict(reference_type="protein", source_ref=source["id"], accession="structure_sequence_" + digest(sequence),
                    label="Structure-derived protein sequence", sequence_ref=files["sequence_file"]["artifact_ref"],
                    molecule="protein", length=sequence["sequence_length"], term_refs=[], context_refs=[], anchor=None)
                reference_ref = identity("reference", dict(origin="tool", record=payload))
                reference = _ordinary_record(self.store, reference_ref, "reference")
                _require(science.same({k: v for k, v in reference.items() if k not in {"id", "record_type", "origin"}}, payload))
                expected_sequences.append(science.validate_structure_sequence_descriptor_v2(dict(
                    version="structure_sequence_descriptor_v2", custody=custody, reference_ref=reference_ref,
                    sequence_file=files["sequence_file"], residue_map_file=files["residue_map_file"],
                    structure_file=sequence["selection"]["file_identity"], selection=sequence["selection"],
                    sequence_length=sequence["sequence_length"], allowed_uses=selection["sequence_allowed_uses"])))
                scientific["descriptor"] = expected_sequences[0]
        if scientific is not None and scientific["kind"] == "comparison" and selection["return_saved_sheet"]:
            expected_saved.append(science.validate_saved_sheet_descriptor_v2(dict(version="protein_structure_saved_sheet_v2",
                custody=custody, sheet_file=files["sheet_file"], original_components_file=files["original_components_file"],
                operation="compare_protein_structures", original_mode=scientific["sheet"]["scientific_mode"],
                allowed_uses=["recalculate", "select_projection", "use_transform"])))
        _require(science.same(result["sequences"], expected_sequences) and science.same(result["saved_sheets"], expected_saved))
        _require(science.same([view["selection"] for view in result["views"]], selection["projections"]))
        for view in result["views"]:
            if view["outcome"]["version"] == "protein_structure_action_artifact_view_v1":
                file = view["outcome"]["delivery"]["table_file"]
                retained_protein_structure_file(self.store, file)
                table = _json_artifact(self.store, file["artifact_ref"])
                rows, = views.project_protein_structure_results(scientific, selection=[view["selection"]])
                _require(science.same(table, dict(version="protein_structure_projection_table_v1", rows=rows["rows"])))
            else:
                file = None
            expected = project_protein_structure_action_views(scientific, source_ref=source["id"],
                operation=result["operation"], selections=[view["selection"]], issues=result["issues"],
                artifact_files=None if file is None else {view["selection"]["projection_id"]: file})
            _require(science.same(expected, [view]))
        return dict(capsule=capsule, bundle=bundle, scientific=scientific, qualified_files=files,
            native_issues=native_issues)

    def _saved_publication(self, producer):
        from .protein_structure_tools import validate_saved_protein_work
        from .protein_structure_publication import (saved_protein_action_values,
            saved_protein_action_source_payload, saved_protein_action_result)
        source, context, action = producer["source"], producer["context"], producer["action"]
        records = ProteinStructureActionRecords(self.store, context.run_id)
        capsule = _json_artifact(self.store, source["request_ref"])
        _require(type(capsule) is dict and set(capsule) == {"version", "work"}
            and capsule["version"] == "protein_structure_saved_action_publication_v1")
        work = capsule["work"]
        _require(work["mode"] in {"recalculate", "select_projection"} and work["redisplay"] is None
            and science.same(work["arguments"], action["arguments"])
            and work["invocation"]["operation_key"] == f'{context.run_id}:{context.episode_id}:{producer["decision_index"]}')
        checked = validate_saved_protein_work(self.store, work, context=context, input_authority=records)
        _require(checked["redisplay"] is None)
        values = saved_protein_action_values(checked)
        _require(science.same(_json_artifact(self.store, source["artifact_ref"]), values))
        payload = saved_protein_action_source_payload(self.store, capsule=capsule,
            public_ref=source["artifact_ref"], request_ref=source["request_ref"])
        _require(science.same({key: value for key, value in source.items()
            if key not in {"id", "record_type", "origin"}}, payload))
        result = saved_protein_action_result(values, source_ref=source["id"])
        _require(science.same(result, producer["result"]) and producer["outcome"]["record_refs"] == [source["id"]]
            and producer["outcome"].get("changed_record_refs") == [source["id"]])
        incomplete = any(view["outcome"]["version"] == "protein_structure_action_unavailable_v1"
            or view["outcome"].get("state") != "complete" for view in result["views"])
        _require(producer["outcome"]["status"] == ("partial" if result["issues"] or incomplete else "completed"))
        original = records.read_result_authority(context, action["arguments"]["saved_sheet"]["custody"])
        parameters = (action["arguments"]["parameters"] if work["mode"] == "recalculate" else
            records.read_result_authority(context, dict(version="protein_structure_action_custody_v1",
                source_ref=action["arguments"]["result_ref"]))["selector"]["parameters"])
        if parameters is None:
            parameters = original["request"]["parameters"]
        return dict(capsule=capsule, scientific=checked["scientific"], qualified_files=checked["qualified_files"],
            native_issues=original["native_issues"], operation_issues=checked["issues"],
            original_authority=original, parameters=deepcopy(parameters))

    def _original_worker_store(self, worker, capture):
        """Read original retained controls at their authenticated artifact root.

        This view owns no connection or writes. It does not relocate a plan,
        inspect raw structure inputs or revisit the producer workspace.
        """
        plan = worker["plan"]
        _require(plan["mode"] == "original_native_result" and plan["native_result"] is not None)
        native = plan["native_result"]
        matches = [row["observed"] for row in capture["files"]
            if row["declared"]["role"] == "native_result" and row["observed"] is not None]
        _require(len(matches) == 1 and science.same(matches[0], native["file_identity"]))
        path, sha = Path(native["path"]), native["file_identity"]["sha256"]
        _require(path.is_absolute() and len(path.parents) >= 3 and path.name == sha
            and path.parent.name == sha[:2] and path.parent.parent.name == "artifacts"
            and str(path) == str(path.parents[2] / "artifacts" / sha[:2] / sha))
        root = path.parents[2]
        if root == self.store.path:
            return self.store
        view = type(self.store).__new__(type(self.store))
        view.path, view.db, view._savepoint = root, self.store.db, self.store._savepoint
        return view

    def own_facts(self, context, *, fact_source, verify_artifacts=True, before_decision_index=None):
        _require(fact_source in FACT_SOURCES, "invalid_schema")
        groups = []
        for row in self._rows(context, before_decision_index=before_decision_index):
            _, _, result = self._action(context, row)
            self._producer(result["source_ref"], verify_artifacts=verify_artifacts)
            groups.append(result[_PAYLOAD_FIELDS[fact_source]])
        return merge_protein_structure_action_facts(*groups, fact_source=fact_source)

    def received_facts(self, context, *, fact_source, before_decision_index=None):
        _require(fact_source in FACT_SOURCES, "invalid_schema")
        known, groups = self._known(context), []
        for child, form, schema in self.received_attempts(context, allow_unsaved=True):
            if before_decision_index is not None and not self._form_before(context, child, form, schema, before_decision_index):
                continue
            for name in requested_protein_structure_action_fields(schema, fact_source=fact_source):
                group = form[name]
                for value in group:
                    _validate_fact(value, fact_source)
                    source_ref = _fact_source_ref(value, fact_source)
                    _require(source_ref in known)
                    if before_decision_index is not None:
                        _require(self._received_before(context.episode_id, source_ref, before_decision_index))
                    producer = self._producer(source_ref, verify_artifacts=False)
                    _require(any(science.same(value, item) for item in producer["result"][_PAYLOAD_FIELDS[fact_source]]))
                    if fact_source == SEQUENCE_SOURCE:
                        _require(value["reference_ref"] in known)
                groups.append(group)
        return merge_protein_structure_action_facts(*groups, fact_source=fact_source)

    def _form_before(self, context, child, form, schema, cutoff):
        if child.path[:-1] != context.path:
            # The canonical iterator has already authenticated the ancestor's
            # frozen received-report prefix at child construction.
            return True
        rows = self.db.execute("SELECT decision_index,form,contract FROM runtime_report_attempts "
            "WHERE run_id=? AND parent_episode_id=? AND child_episode_id=? AND decision_index<? "
            "AND failure IS NULL AND form IS NOT NULL", (self.run_id, context.episode_id, child.episode_id, cutoff))
        recorded = any(science.same(json.loads(row["form"]), form) and science.same(
            json.loads(row["contract"]).get("measurements", {}).get("schema"), schema) for row in rows)
        return recorded and bool(self._decision_witnesses(context, form, cutoff))

    def _decision_witnesses(self, context, value, cutoff):
        return self.decision_witnesses(context, value, cutoff)

    def _source_at(self, context, source_ref, cutoff):
        try:
            return super().source_admission_before(context, source_ref, cutoff)
        except ValueError as error:
            for code in ('invalid_schema', 'result_not_received'):
                if str(error) == self.failure_prefix + code:
                    raise _error(code) from error
            raise

    def read_stored_result(self, context, source_ref, *, before_decision_index):
        self.authenticate(context)
        _require(type(before_decision_index) is int and before_decision_index >= 0, "invalid_schema")
        admission = self._source_at(context, source_ref, before_decision_index)
        producer = self._producer(source_ref, verify_artifacts=True)
        _require(producer["result"]["operation"] == "compare", "invalid_schema")
        return deepcopy({**{key: producer["outcome"].get(key) for key in ("status", "result", "feedback")},
            "admission": admission})

    def saved_action_inputs(self, context, descriptor, *, required_use, before_decision_index, result_ref=None):
        self.authenticate(context)
        _require(type(before_decision_index) is int and before_decision_index >= 0, "invalid_schema")
        descriptor = science.validate_saved_sheet_descriptor_v2(descriptor)
        original = self.authenticate_received_saved_sheet(context, descriptor, required_use=required_use,
            before_decision_index=before_decision_index)
        basis_ref = descriptor["custody"]["source_ref"] if result_ref is None else result_ref
        source_admission = self._source_at(context, basis_ref, before_decision_index)
        basis = self.read_result_authority(context,
            dict(version="protein_structure_action_custody_v1", source_ref=basis_ref))
        _require(all(science.same(basis[name], original[name]) for name in
            ("sheet_file", "original_components_file", "request", "software")), "original_commission_mismatch")
        witnesses = []
        for row in self._rows(context, before_decision_index=before_decision_index):
            action, outcome, value = self._action(context, row)
            if any(science.same(descriptor, item) for item in value["saved_sheets"]):
                witnesses.append(dict(kind="own_action", episode_id=context.episode_id,
                    decision_index=row["decision_index"], action_sha256=digest(action), outcome_sha256=digest(outcome)))
        for child, form, schema in self.received_attempts(context, allow_unsaved=True):
            if not self._form_before(context, child, form, schema, before_decision_index):
                continue
            if any(any(science.same(descriptor, item) for item in form[field])
                    for field in requested_protein_structure_action_fields(schema, fact_source=SAVED_SOURCE)):
                witnesses.append(dict(kind="typed_return", child_episode_id=child.episode_id,
                    form_sha256=digest(form), schema_sha256=digest(schema),
                    decision_witnesses=(self._decision_witnesses(context, form, before_decision_index)
                        if child.path[:-1] == context.path else [])))
        _require(bool(witnesses), "saved_sheet_not_received")
        admission = dict(version="protein_structure_saved_action_admission_v1", run_id=context.run_id,
            episode_id=context.episode_id, before_decision_index=before_decision_index,
            request_sha256=digest(plain(context.request)), scope_sha256=digest(plain(context.scope)),
            receipt_manifest_sha256=digest(EpisodeReceipts.read_manifest(self.db, self.run_id, context.episode_id)),
            descriptor_sha256=digest(descriptor), original_source_sha256=digest(self.store.get(descriptor["custody"]["source_ref"])),
            result_ref=basis_ref, source_admission=source_admission,
            result_source_sha256=digest(self.store.get(basis_ref)), witnesses=witnesses)
        return deepcopy(dict(original=original, basis=basis, admission=admission))

    def _available(self, context, fact_source, *, before_decision_index=None):
        own = [] if self.db.execute("SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone() is None else self.own_facts(context,
                fact_source=fact_source, verify_artifacts=False, before_decision_index=before_decision_index)
        return merge_protein_structure_action_facts(self.received_facts(context, fact_source=fact_source,
            before_decision_index=before_decision_index), own,
            fact_source=fact_source)

    def received_sequence_descriptors(self, context, reference_ref):
        result = [row for row in self._available(context, SEQUENCE_SOURCE) if row["reference_ref"] == reference_ref]
        if self.legacy_returns is not None:
            result.extend(self.legacy_returns.received_sequence_descriptors(context, reference_ref))
        return result

    def authenticate_received_sequence(self, context, descriptor, *, required_use):
        if descriptor.get("version") == "structure_sequence_descriptor_v1":
            _require(self.legacy_returns is not None, "sequence_not_received")
            return self.legacy_returns.authenticate_received_sequence(context, descriptor, required_use=required_use)
        descriptor = science.validate_structure_sequence_descriptor_v2(descriptor)
        _require(required_use in descriptor["allowed_uses"] and any(science.same(descriptor, row)
            for row in self._available(context, SEQUENCE_SOURCE)), "sequence_not_received")
        _require({descriptor["reference_ref"], descriptor["custody"]["source_ref"]} <= self._known(context), "sequence_not_received")
        return self.read_result_authority(context, descriptor["custody"])

    def authenticate_received_saved_sheet(self, context, descriptor, *, required_use, before_decision_index=None):
        if descriptor.get("version") == "protein_structure_saved_sheet_v1":
            _require(self.legacy_returns is not None, "saved_sheet_not_received")
            value = self.legacy_returns.authenticate_received_saved_sheet(context, descriptor, required_use=required_use)
            if before_decision_index is not None:
                self._source_at(context, descriptor["custody"]["source_ref"], before_decision_index)
                _require(self._typed_value_before(context, descriptor, "execution_protein_structure_saved_sheets",
                    before_decision_index), "saved_sheet_not_received")
            return value
        descriptor = science.validate_saved_sheet_descriptor_v2(descriptor)
        _require(required_use in descriptor["allowed_uses"] and any(science.same(descriptor, row)
            for row in self._available(context, SAVED_SOURCE, before_decision_index=before_decision_index)), "saved_sheet_not_received")
        _require(descriptor["custody"]["source_ref"] in self._known(context), "saved_sheet_not_received")
        if before_decision_index is not None:
            self._source_at(context, descriptor["custody"]["source_ref"], before_decision_index)
        return self.read_result_authority(context, descriptor["custody"])

    def read_result_authority(self, context, custody, *, before_decision_index=None):
        science.validate_protein_structure_action_custody(custody)
        _require(custody["source_ref"] in self._known(context))
        if before_decision_index is not None:
            self._source_at(context, custody["source_ref"], before_decision_index)
        producer = self._producer(custody["source_ref"], verify_artifacts=True)
        capsule, files = producer["capsule"], producer["qualified_files"]
        saved = producer["source"]["version"] == SAVED_ACTION_SOURCE_VERSION
        return deepcopy(dict(custody=custody, selector=(dict(projections=producer["action"]["arguments"]["projections"],
                parameters=producer["parameters"]) if saved else {**producer["action"]["arguments"]["selection"], "parameters": None}),
            request=(producer["original_authority"]["request"] if saved else producer["bundle"]["requested_job"]["native_protein_structure"]["request"]),
            software=(producer["original_authority"]["software"] if saved else capsule["binding"]["software"]), **files,
            facts={source: producer["result"][_PAYLOAD_FIELDS[source]] for source in FACT_SOURCES},
            scientific=producer["scientific"], native_issues=producer.get("native_issues", []),
            operation_issues=producer.get("operation_issues", producer.get("native_issues", [])),
            published={key: deepcopy(producer["outcome"].get(key)) for key in ("status", "result", "feedback")}))

    def authenticate_received_alignment(self, context, alignment):
        if self.legacy_returns is not None:
            return self.legacy_returns.authenticate_received_alignment(context, alignment)
        self.authenticate(context, allow_unsaved=True)
        known = self._known(context)
        _require({alignment["source_ref"], alignment["observation_ref"]} <= known, "alignment_not_received")
        prefix = f"{context.run_id}:{context.episode_id}:"
        key = alignment["original_operation_key"]
        _require(key.startswith(prefix) and key[len(prefix):].isdecimal(), "alignment_not_received")
        index = int(key[len(prefix):])
        row = self.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
            (context.run_id, context.episode_id, index)).fetchone()
        _require(row is not None and row["result"] is not None, "alignment_not_received")
        arguments = dict(query_ref=alignment["query_reference_ref"], reference_ref=alignment["reference_reference_ref"], molecule="protein", mode=alignment["mode"])
        _require(science.same(json.loads(row["action"]), dict(kind="tool", tool="sequence.align", arguments=arguments)), "alignment_not_received")
        operation = self.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (key,)).fetchone()
        outcome = json.loads(row["result"])
        _require(operation is not None and operation["name"] == "sequence.align" and operation["arguments"] == canonical(arguments)
            and operation["scope"] == canonical(plain(context.scope))
            and operation["id"] == identity("operation", dict(key=key, name="sequence.align", arguments=arguments))
            and operation["id"] == outcome.get("operation_ref")
            and operation["result"] == canonical({k: v for k, v in outcome.items() if k != "pending_work_after_action"})
            and outcome["status"] == "completed"
            and {alignment["source_ref"], alignment["observation_ref"]} <= set(outcome["record_refs"]), "alignment_not_received")

    def _typed_value_before(self, context, value, source, cutoff):
        for child, form, schema in self.received_attempts(context, allow_unsaved=True):
            if not self._form_before(context, child, form, schema, cutoff):
                continue
            for name, field in schema.get("properties", {}).items():
                if field.get("x-source") == source and any(science.same(value, item) for item in form[name]):
                    return True
        return False

    def received_transform_projections(self, context, transform, *, before_decision_index=None):
        received = transform["received_from"]
        if received["saved_sheet"].get("version") == "protein_structure_saved_sheet_v1":
            _require(self.legacy_returns is not None, "invalid_transform")
            values = self.legacy_returns.received_transform_projections(context, transform)
            if before_decision_index is not None:
                self.authenticate_received_saved_sheet(context, received["saved_sheet"], required_use="use_transform",
                    before_decision_index=before_decision_index)
                values = [row for row in values if self._typed_value_before(context, row,
                    "execution_protein_structure_projections", before_decision_index)]
            return values
        self.authenticate_received_saved_sheet(context, received["saved_sheet"], required_use="use_transform",
            before_decision_index=before_decision_index)
        if before_decision_index is not None:
            self._source_at(context, received["calculation_custody"]["source_ref"], before_decision_index)
        return [row for row in self._available(context, VIEW_SOURCE, before_decision_index=before_decision_index)
            if row["selection"]["family"] == "transform"
            and row["source_ref"] == received["calculation_custody"]["source_ref"]]

    def retained_reference_access(self, context, reference, namespace):
        if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='tool_operations'").fetchone() is None:
            return None
        candidates = list(self.db.execute("SELECT result FROM tool_operations "
            "WHERE name IN (SELECT value FROM json_each(?)) AND json_extract(result,'$.result.version')=?",
            (canonical(list(TOOLS)), RESULT_VERSION)))
        matched = []
        for row in candidates:
            result = json.loads(row["result"])["result"]
            source = self.store.get(result["source_ref"])
            refs = [source["id"], source["artifact_ref"], source.get("request_ref"), *source.get("auxiliary_artifact_refs", [])]
            refs += [item["reference_ref"] for item in result["sequences"]]
            refs += [item["outcome"]["delivery"]["table_file"]["artifact_ref"] for item in result["views"]
                if item["outcome"]["version"] == "protein_structure_action_artifact_view_v1"]
            if reference not in refs:
                continue
            matched.append(source["id"])
        if not matched:
            return None
        self.authenticate(context, allow_unsaved=True)
        for source_ref in matched:
            producer = self._producer(source_ref, verify_artifacts=False)
            source = producer["source"]
            if reference == source.get("request_ref"):
                return False
            if reference in self._known(context):
                record = self.store.get(reference)
                return namespace in {None, "record", record["record_type"]} or namespace == "subject" and record["record_type"] == "reference"
        return False

    def resolve_received(self, context, reference, namespace):
        return self.retained_reference_access(context, reference, namespace)


def own_protein_structure_action_facts(registry, context, *, fact_source):
    return ProteinStructureActionRecords(registry.store, context.run_id).own_facts(context, fact_source=fact_source)


def frozen_protein_structure_action_facts(store, run_id, context, *, fact_source):
    records = ProteinStructureActionRecords(store, run_id)
    records.authenticate(context)
    row = store.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?", (run_id, context.episode_id)).fetchone()
    if row is None:
        return None
    facts = json.loads(row["facts"])
    if fact_source not in facts:
        return None
    values = facts[fact_source]
    _require(type(values) is list, "invalid_schema")
    for value in values:
        _validate_fact(value, fact_source)
        source = _fact_source_ref(value, fact_source)
        producer = records._producer(source, verify_artifacts=False)
        _require(any(science.same(value, item) for item in producer["result"][_PAYLOAD_FIELDS[fact_source]]))
    return deepcopy(values)


def received_protein_structure_action_facts(store, run_id, context, *, fact_source):
    return ProteinStructureActionRecords(store, run_id).received_facts(context, fact_source=fact_source)


def validate_frozen_protein_structure_action_return(form, schema, frozen, *, fact_source):
    for name in requested_protein_structure_action_fields(schema, fact_source=fact_source):
        try:
            actual = plain(form).get(name)
            _require(type(actual) is list and type(frozen) is list)
            for item in [*actual, *frozen]:
                _validate_fact(item, fact_source)
            _require(science.same(actual, frozen))
        except ValueError as error:
            raise ReportBoundaryError("Return differs from the frozen protein action facts", code="protein_structure_action_frozen_conflict", field=name) from error


__all__ = ["FACT_SOURCES", "VIEW_SOURCE", "SEQUENCE_SOURCE", "SAVED_SOURCE", "ProteinStructureActionRecords",
    "protein_structure_action_fact_sources", "validate_protein_structure_tool_result", "validate_protein_structure_action_view",
    "protein_structure_action_view_identity", "action_view_from_projection_rows", "project_protein_structure_action_views",
    "merge_protein_structure_action_facts", "requested_protein_structure_action_fields", "protein_structure_action_form_references",
    "own_protein_structure_action_facts",
    "frozen_protein_structure_action_facts", "received_protein_structure_action_facts", "validate_frozen_protein_structure_action_return"]
