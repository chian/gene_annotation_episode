"""Pure resolution of explicit GenomeComparison bytes into real A/B1/B2/B3/B4.

This selected calculation performs no acquisition, retry, fallback-primary choice,
resource operation or model invocation. Native and supplied operands keep their
actual completeness. Optional failures remain scoped and their original values
remain in the provider sheet. Constructor outputs are retained unchanged.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
import re

from . import bvbrc_proteome_bundle_contracts as c
from .bvbrc_appservice_contracts import ContractValidationError, validate_contract
from .bvbrc_proteome_data_contracts import ProteomeDataError, validate_proteome_data
from .bvbrc_proteome_native import parse_genome_comparison
from .bvbrc_proteome_inputs import (
    index_original_inputs, read_protein_fasta, read_feature_metadata,
    read_genome_metadata, read_feature_sequences,
)
from .bvbrc_proteome_joins import build_native_joins
from .bvbrc_proteome_sheet import build_native_sheet
from .bvbrc_proteome_calculators import calculate_native_components
from .bvbrc_proteome_fact_contracts import validate_requested_form


_FORMATS = {"genome_comparison_json_v1", "genome_comparison_tsv_v1"}
_INPUTS = (
    ("inventories", "inventory", "inventory_results", "ProteinInventoryResult", read_protein_fasta),
    ("feature_snapshots", "feature_snapshot", "feature_results", "FeatureSnapshotResult", read_feature_metadata),
    ("genome_snapshots", "genome_snapshot", "genome_results", "GenomeSnapshotResult", read_genome_metadata),
    ("sequence_snapshots", "sequence_snapshot", "sequence_results", "FeatureSequenceSnapshotResult", read_feature_sequences),
)
_FIELD_KEYS = {"source_ref", "sha256", "pointer", "row_ordinal", "field_name"}


def _unique(rows):
    values, seen = [], set()
    for row in rows:
        key = c.canonical(row)
        if key not in seen:
            seen.add(key)
            values.append(deepcopy(row))
    return values


def _content(member):
    return {"source_ref": member["source_ref"], "artifact_field": "artifact_ref",
            "artifact_ref": member["raw_artifact_ref"], "sha256": member["sha256"],
            "byte_count": member["byte_count"]}


def _fields(value):
    if type(value) is dict:
        if set(value) == _FIELD_KEYS:
            yield value
        else:
            for child in value.values():
                yield from _fields(child)
    elif type(value) is list:
        for child in value:
            yield from _fields(child)


def _json(raw):
    def pairs(items):
        value = {}
        for key, child in items:
            if key in value:
                raise ValueError("duplicate_json_member")
            value[key] = child
        return value
    def invalid(_):
        raise ValueError("nonfinite_json")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid)


def _at(value, pointer):
    if pointer == "":
        return value
    if not pointer.startswith("/") or re.search(r"~(?![01])", pointer):
        raise ValueError("source_pointer_invalid")
    current = value
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if type(current) is dict and token in current:
            current = current[token]
        elif type(current) is list and re.fullmatch(r"0|[1-9][0-9]*", token) and int(token) < len(current):
            current = current[int(token)]
        else:
            raise ValueError("source_pointer_unbound")
    return current


def _submitted_record(raw, task):
    """Check the retained native-source wrapper, without asserting host custody.

    request_ref is canonical retained metadata, not literal HTTP request bytes.
    The returned task ID is absent from this wrapper; the host authenticates it
    against the original native response and confirmed submission receipt.
    """
    retained = _json(raw)
    if (type(retained) is not dict or set(retained) != {"version", "origin", "snapshot", "prepared"}
            or retained["version"] != "bvbrc_appservice_native_source_v1"
            or raw != c.canonical(retained).encode("utf-8")):
        raise ValueError("submission_record_invalid")
    origin = validate_contract("ReceiptOrigin", retained["origin"])
    prepared = validate_contract("PreparedOperation", retained["prepared"])
    operands, bound = prepared["native_operands"], prepared["bound_inputs"]
    if set(operands) != {"request", "arguments", "selector", "call", "local_failure"}:
        raise ValueError("submission_operands_invalid")
    request = validate_contract("AppServiceRequest", operands["request"])
    validate_contract("OperationSelection", {"name": prepared["operation"], "arguments": operands["arguments"]})
    operation = "api.bvbrc_appservice.submit"
    # The service's original request/argument hashes use its canonical encoder.
    # The retained wrapper and HTTP RPC body use UTF-8 without ASCII escaping.
    def native_digest(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    prefix = origin["run_id"] + ":" + origin["episode_id"] + ":"
    if (origin["name"] != operation or prepared["operation"] != operation
            or origin["operation_key"] != task["submission_operation_key"]
            or not origin["operation_key"].startswith(prefix)
            or re.fullmatch(r"0|[1-9][0-9]*", origin["operation_key"][len(prefix):]) is None
            or prepared["purpose"] != "handoff" or prepared["native_kind"] != "rpc"
            or not prepared["mutates_remote"] or operands["local_failure"] is not None
            or operands["selector"] is not None or bound["original_handoff_ref"] is not None
            or origin["arguments_sha256"] != prepared["arguments_sha256"]
            or prepared["arguments_sha256"] != native_digest(operands["arguments"])
            or prepared["request_sha256"] != native_digest(request)
            or bound["original_job_owner"]["run_id"] != origin["run_id"]
            or bound["resource_id"] != task["resource_id"]
            or request["required_application_id"] != task["required_application_id"]
            or c.canonical(request["parameters"]) != c.canonical(task["submitted_parameters"])
            or c.canonical(request["start_parameters"]) != c.canonical(task["submitted_start_parameters"])):
        raise ValueError("submission_identity_conflict")
    rpc_id = "bvbrc_rpc_" + native_digest({"operation": operation, "owner": bound["original_job_owner"],
        "resource_id": bound["resource_id"], "request": bound["request_sha256"],
        "arguments": bound["selected_argument_sha256"]})
    rpc = {"version": "1.1", "method": "AppService.start_app2", "id": rpc_id,
           "params": [task["native_application_id"], task["submitted_parameters"], task["submitted_start_parameters"]]}
    if c.canonical(operands["call"]) != c.canonical({"rpc_request": rpc}):
        raise ValueError("submission_rpc_conflict")
    preparation = bound["resolved"]["preparation"]
    native = preparation["c3_result"].get("value")
    if (preparation["receipt"]["receipt_ref"] != operands["arguments"]["preparation_receipt_ref"]
            or preparation["receipt"]["origin"]["name"] != "api.bvbrc_appservice.prepare"
            or preparation["receipt"]["status"] != "ok" or preparation["c3_result"].get("status") != "ok"
            or preparation["request_sha256"] != prepared["request_sha256"]
            or preparation["required_application_id"] != task["required_application_id"]
            or preparation["native_application_id"] != task["native_application_id"]
            or c.canonical(preparation["native_parameters"]) != c.canonical(task["submitted_parameters"])
            or c.canonical(preparation["start_parameters"]) != c.canonical(task["submitted_start_parameters"])
            or type(native) is not dict or native.get("required_id") != task["required_application_id"]
            or native.get("native_application_id") != task["native_application_id"]
            or c.canonical(native.get("native_params")) != c.canonical(rpc["params"])):
        raise ValueError("submission_preparation_conflict")
    effects = prepared["effects"]
    if (len(effects) != 1 or effects[0]["kind"] != "appservice_submit"
            or effects[0]["slot"] != {"kind": "appservice_submit"}
            or effects[0]["payload_sha256"] != native_digest({"method": rpc["method"], "params": rpc["params"]})):
        raise ValueError("submission_effect_conflict")
    snapshot = retained["snapshot"]
    if (type(snapshot) is not dict or set(snapshot) != {"service", "url", "request", "retrieved_at", "content_ref", "media_type", "transport"}
            or snapshot["service"] != "bvbrc_analysis"
            or any(type(snapshot[key]) is not str or not snapshot[key] for key in ("url", "retrieved_at", "media_type", "content_ref"))
            or re.fullmatch(r"artifact_[0-9a-f]{64}", snapshot["content_ref"]) is None
            or c.canonical(snapshot["request"]) != c.canonical({"kind": "rpc", "rpc": rpc})):
        raise ValueError("submission_snapshot_conflict")
    transport = snapshot["transport"]
    sent = transport.get("request") if type(transport) is dict else None
    body = c.canonical(rpc).encode("utf-8")
    if (type(sent) is not dict or transport.get("body_complete") is not True
            or type(transport.get("status")) is not int or not 200 <= transport["status"] < 300
            or type(transport.get("received_body_bytes")) is not int or transport["received_body_bytes"] < 0
            or transport.get("effective_url") != snapshot["url"] or transport.get("automatic_redirects") is not False
            or sent.get("method") != "POST" or sent.get("url") != snapshot["url"]
            or type(sent.get("body_bytes")) is not int or sent["body_bytes"] != len(body)
            or sent.get("body_sha256") != hashlib.sha256(body).hexdigest()):
        raise ValueError("submission_transport_conflict")


class _Resolution:
    def __init__(self, bundle, raw, values, parameters, form):
        self.bundle, self.raw, self.values = bundle, raw, values
        self.parameters, self.form = parameters, form
        self.requirements, self.diagnostics, self.outcomes = [], [], []
        self.sources = {}
        self.native_results, self.input_index_result = [], None
        self.inventory_results, self.feature_results, self.genome_results, self.sequence_results = [], [], [], []

    def problem(self, code, path, *, refs=(), severity="qualification", row=None):
        code = code if code.startswith("proteome_") else "proteome_" + code
        kind, role, phase = c.BINDING_DETAILS[code]
        refs = list(dict.fromkeys(refs))
        # The selection carries only the exact finite construction selector; it
        # does not introduce a rule language or reinterpret the native Scope.
        selection = None if row is None else {"selector_kind": row["selector_kind"], "selection_index": row["selection_index"]}
        payload = dict(version="bvbrc_proteome_requirement_v1", analysis_id=self.parameters["analysis_id"],
            reason_code=code, role=role, field=None, selection=selection, source_refs=refs, pure_requirement=None)
        req = dict(requirement_id="proteome_requirement_" + c.digest(payload), kind=kind, role=role,
                   source_refs=refs, reason_code=code)
        self.requirements = _unique([*self.requirements, req])
        self.diagnostics = _unique([*self.diagnostics, dict(code=code, phase=phase, path=path,
            severity=severity, evidence_refs=refs)])
        if row is not None and req["requirement_id"] not in row["requirement_ids"]:
            row["requirement_ids"].append(req["requirement_id"])
        return req

    def pure(self, result, path, *, role, row=None):
        for requirement in result["requirements"]:
            input_kind = requirement["required_input"]
            if input_kind not in c.PURE_REQUIRED_INPUT_KINDS:
                raise c.ProteomeBundleError("proteome_supplied_reader_incompatible", path + "/requirements")
            refs = list(dict.fromkeys(field["source_ref"] for field in requirement["source_fields"]))
            payload = dict(version="bvbrc_proteome_requirement_v1", analysis_id=self.parameters["analysis_id"],
                reason_code=requirement["code"], role=role, field=None, selection=None, source_refs=refs,
                pure_requirement=deepcopy(requirement))
            host = dict(requirement_id="proteome_requirement_" + c.digest(payload),
                kind=c.PURE_REQUIRED_INPUT_KINDS[input_kind], role=role, source_refs=refs, reason_code=requirement["code"])
            self.requirements = _unique([*self.requirements, host])
            if row is not None and host["requirement_id"] not in row["requirement_ids"]:
                row["requirement_ids"].append(host["requirement_id"])
        self.diagnostics = _unique([*self.diagnostics, *[
            dict(code=d["code"], phase="native_decode", path=f"{path}/diagnostics/{i}", severity=d["severity"],
                 evidence_refs=list(dict.fromkeys(f["source_ref"] for f in d["source_fields"])))
            for i, d in enumerate(result["diagnostics"])]])

    def outcome(self, kind, index):
        row = dict(selector_kind=kind, selection_index=index, state="missing", content=None,
                   construction_evidence=None, result_index=None, requirement_ids=[])
        self.outcomes.append(row)
        return row

    def register(self, content, path, row, *, code="supplied_source_conflict"):
        # One source can retain distinct request and response artifacts. Only
        # competing descriptions of the same source field are versions of the
        # same operand; SourceField joins still require their exact digest.
        key = content["source_ref"], content["artifact_field"]
        old = self.sources.get(key)
        if old is not None and (old["sha256"], old["byte_count"]) != (content["sha256"], content["byte_count"]):
            row["state"] = "invalid"
            self.problem(code, path, refs=[content["source_ref"]], severity="error", row=row)
            return False
        self.sources[key] = deepcopy(content)
        return True

    def bytes_for(self, content, path, row, *, output=False):
        raw = self.raw.get(content["artifact_ref"])
        if raw is None:
            self.problem("artifact_bytes_missing" if output else "input_bytes_missing", path,
                         refs=[content["source_ref"]], row=row)
            return None
        if type(raw) is not bytes or len(raw) != content["byte_count"] or hashlib.sha256(raw).hexdigest() != content["sha256"]:
            row["state"] = "invalid"
            self.problem("artifact_digest_mismatch", path, refs=[content["source_ref"]], severity="error", row=row)
            return None
        return raw

    def artifact(self, source_ref, artifact_ref, path, row, *, declared=None, role=None):
        matches = [a for a in self.bundle["artifacts"] if a["source_ref"] == source_ref and a["raw_artifact_ref"] == artifact_ref]
        if len(matches) != 1:
            near = [a for a in self.bundle["artifacts"] if a["source_ref"] == source_ref or a["raw_artifact_ref"] == artifact_ref]
            code = "document_ambiguous" if len(matches) > 1 else "artifact_binding_conflict" if near else "document_missing"
            row["state"] = "invalid" if matches or near else "missing"
            self.problem(code, path, refs=[source_ref], severity="error" if matches or near else "qualification", row=row)
            return None, None
        member = matches[0]
        row["content"] = _content(member)
        if role is not None and member["role"] != role:
            row["state"] = "invalid"
            self.problem("artifact_binding_conflict", path, refs=[source_ref], severity="error", row=row)
            return None, None
        if declared is not None and member["declared_format"] != declared:
            row["state"] = "incompatible"
            self.problem("artifact_format_incompatible", path, refs=[source_ref], severity="error", row=row)
            return None, None
        transfer, observed = member["transfer"], member["transfer"]["observed_range"]
        if (observed is not None and observed["start"] != 0 or observed is None and transfer["object_complete"] != "yes"
                and transfer["requested_range"] is not None and transfer["requested_range"][0] != 0):
            row["state"] = "incompatible"
            self.problem("nonzero_range_unsupported", path, refs=[source_ref], row=row)
            return None, None
        if not self.register(row["content"], path, row, code="artifact_binding_conflict"):
            return None, None
        raw = self.bytes_for(row["content"], path, row, output=True)
        if raw is None:
            return None, None
        return raw, dict(content=deepcopy(row["content"]), body_complete=transfer["body_complete"],
                         object_complete=transfer["object_complete"])

    def documents(self):
        selections = self.parameters["native_documents"]
        counts = Counter(selection["source_ref"] for selection in selections)
        for i, selected in enumerate(selections):
            path = f"/parameters/native_documents/{i}"
            row = self.outcome("native_document", i)
            if counts[selected["source_ref"]] != 1:
                row["state"] = "invalid"
                self.problem("document_ambiguous", path, refs=[selected["source_ref"]], severity="error", row=row)
                continue
            declaration, contract = selected["declared_format"], selected["source_contract"]
            if declaration["format"] not in _FORMATS or declaration["version"] is not None or declaration["mode"] is not None:
                row["state"] = "incompatible"
                self.problem("artifact_format_incompatible", path + "/declared_format", refs=[selected["source_ref"]], severity="error", row=row)
                continue
            if contract["deployment_match"] != "unobserved":
                row["state"] = "incompatible" if contract["deployment_match"] == "different" else "unverified"
                self.problem("source_contract_incompatible" if contract["deployment_match"] == "different" else "deployment_evidence_unverified",
                             path + "/source_contract", refs=[selected["source_ref"]],
                             severity="error" if contract["deployment_match"] == "different" else "qualification", row=row)
                continue
            raw, source = self.artifact(selected["source_ref"], selected["raw_artifact_ref"], path, row,
                                        declared=declaration, role=selected["role"])
            if raw is None:
                continue
            result = parse_genome_comparison(raw, source=source, declared_format=declaration["format"], source_contract=contract)
            row["result_index"] = len(self.native_results)
            self.native_results.append(result)
            self.record(result, row, f'/native_results/{row["result_index"]}', "proteome_native_projection")

    def record(self, result, row, path, role):
        row["state"] = "invalid" if result["value"] is None else "resolved" if result["status"] == "ok" else "partial"
        self.pure(result, path, role=role, row=row)

    def supplementary(self):
        evidence = self.parameters["supplied_data_evidence"]
        if evidence is None:
            return None
        rows = [(i, r) for i, r in enumerate(self.values) if r["evidence"] == evidence]
        if len(rows) != 1:
            self.problem("supplied_data_missing" if not rows else "supplied_data_ambiguous", "/parameters/supplied_data_evidence",
                         refs=[evidence["content"]["source_ref"]], severity="qualification" if not rows else "error")
            return None
        self.data_path = f"/supplied_values/{rows[0][0]}/value"
        try:
            return c.validate_supplied_data(rows[0][1]["value"])
        except c.ProteomeBundleError as error:
            self.problem(error.code, self.data_path + error.path, refs=[evidence["content"]["source_ref"]], severity="error")
            return None

    def evidence_supplied(self, evidence):
        return sum(row["evidence"] == evidence for row in self.values) == 1 and evidence != self.parameters["supplied_data_evidence"]

    def parsed(self, selected, contract, path, row):
        row["construction_evidence"] = deepcopy(selected["construction_evidence"])
        try:
            result = validate_proteome_data(contract, selected["result"])
        except ProteomeDataError as error:
            row["state"] = "invalid"
            self.problem("parsed_result_invalid", path + "/result" + error.path, severity="error", row=row)
            return
        value = result["value"]
        key = "inventory_key" if contract == "ProteinInventoryResult" else "snapshot_key" if contract != "InputIndexResult" else None
        if value is not None and key is not None and value[key] != selected[key]:
            row["state"] = "invalid"
            self.problem("parsed_result_mismatch", path + "/result/value/" + key, severity="error", row=row)
            return
        if value is not None and "source" in value:
            content = value["source"]["content"]
            row["content"] = deepcopy(content)
            contents = [*self.bundle.get("supplied_contents", []), *[_content(a) for a in self.bundle["artifacts"]]]
            candidates = [b for b in contents if b["source_ref"] == content["source_ref"] or b["artifact_ref"] == content["artifact_ref"]]
            if candidates and content not in candidates:
                row["state"] = "invalid"
                self.problem("supplied_source_conflict", path + "/result/value/source/content", refs=[content["source_ref"]], severity="error", row=row)
                return
        elif value is not None and contract == "InputIndexResult":
            field = value["parameter_source"]["source_field"]
            task = self.bundle["original_task"]
            expected = task["submission_source_ref"] if value["parameter_source"]["kind"] == "submitted" else (
                task["effective_parameters"]["evidence"]["content"]["source_ref"] if task["effective_parameters"] is not None else None)
            if field["source_ref"] != expected:
                row["state"] = "invalid"
                self.problem("parameter_source_conflict", path + "/result/value/parameter_source", refs=[field["source_ref"]], severity="error", row=row)
                return
        evidence = selected["construction_evidence"]
        row["state"] = "unverified"
        self.problem("parsed_construction_evidence_unverified", path + "/construction_evidence",
                     refs=[evidence["content"]["source_ref"]], row=row)
        # Custody of a supplied JSON value is not a typed constructor decoder.
        # Neither a self-consistent digest nor a caller flag authenticates it.
        if not self.evidence_supplied(evidence):
            self.problem("source_field_unbound", path + "/construction_evidence", refs=[evidence["content"]["source_ref"]], row=row)

    def input_source(self, selected, path, row):
        source = selected["source"]
        if source["kind"] == "acquired_artifact":
            matches = [a for a in self.bundle["artifacts"] if a["source_ref"] == source["source_ref"] and a["raw_artifact_ref"] == source["raw_artifact_ref"]]
            raw, actual = self.artifact(source["source_ref"], source["raw_artifact_ref"], path, row)
            if raw is not None:
                declared = matches[0]["declared_format"]
                if declared["format"] != selected["declared_format"] or declared["version"] is not None or declared["mode"] is not None:
                    row["state"] = "incompatible"
                    self.problem("supplied_reader_incompatible", path + "/declared_format", refs=[source["source_ref"]], severity="error", row=row)
                    return None, None
            return raw, actual
        if source["kind"] == "original_retained_input":
            matches = [b for b in self.bundle["input_bindings"] if b["binding_id"] == source["input_binding_id"]]
            if len(matches) != 1 or matches[0]["kind"] != "retained_bytes":
                self.problem("input_binding_ambiguous" if len(matches) > 1 else "input_binding_missing", path + "/source", row=row)
                return None, None
            binding = matches[0]
            try:
                operand = _at(self.bundle["original_task"]["submitted_parameters"], binding["parameter_pointer"])
            except (ValueError, RecursionError):
                operand = None
            if operand != binding["workspace_path"]:
                row["state"] = "invalid"
                self.problem("original_task_conflict", path + "/source", refs=[binding["content"]["source_ref"]], severity="error", row=row)
                return None, None
            content, complete = binding["content"], "yes"
        else:
            content, complete = source["content"], "unknown"
            evidence = source["completeness_evidence"]
            if evidence is not None:
                row["construction_evidence"] = deepcopy(evidence)
                self.problem("completeness_evidence_unverified", path + "/source/completeness_evidence", refs=[evidence["content"]["source_ref"]], row=row)
                if not self.evidence_supplied(evidence):
                    self.problem("source_field_unbound", path + "/source/completeness_evidence", refs=[evidence["content"]["source_ref"]], row=row)
        row["content"] = deepcopy(content)
        if content not in self.bundle.get("supplied_contents", []):
            self.problem("input_binding_missing", path + "/source", refs=[content["source_ref"]], row=row)
            return None, None
        if not self.register(content, path, row):
            return None, None
        raw = self.bytes_for(content, path, row)
        return (raw, dict(content=deepcopy(content), body_complete=True, object_complete=complete)) if raw is not None else (None, None)

    def source_fields(self, value, path, row):
        """Check supplied scientific metadata references against explicit bytes."""
        contents = [*self.bundle.get("supplied_contents", []), *[_content(a) for a in self.bundle["artifacts"]]]
        valid = True
        for field in _fields(value):
            matches = [b for b in contents if b["source_ref"] == field["source_ref"] and b["sha256"] == field["sha256"]]
            if not matches:
                conflict = any(b["source_ref"] == field["source_ref"] for b in contents)
                self.problem("supplied_source_conflict" if conflict else "source_field_unbound", path,
                             refs=[field["source_ref"]], severity="error" if conflict else "qualification", row=row)
                valid = False
                continue
            bindings = _unique(matches)
            if len(bindings) != 1:
                self.problem("supplied_source_conflict", path, refs=[field["source_ref"]], severity="error", row=row)
                valid = False
                continue
            if not self.register(bindings[0], path, row):
                valid = False
                continue
            raw = self.bytes_for(bindings[0], path, row)
            if raw is None:
                valid = False
                continue
            try:
                _at(_json(raw), field["pointer"])
            except (ValueError, UnicodeError, RecursionError):
                self.problem("source_field_unbound", path, refs=[field["source_ref"]], row=row)
                valid = False
        return valid

    def parameter(self, selected, path, row):
        source = selected["source_field"]
        task = self.bundle["original_task"]
        if selected["kind"] == "submitted":
            if source["source_ref"] != task["submission_source_ref"]:
                row["state"] = "invalid"
                self.problem("parameter_source_conflict", path, refs=[source["source_ref"], task["submission_source_ref"]], severity="error", row=row)
                return None
            # The response artifact or another equal-valued JSON field cannot
            # replace an explicitly supplied original request_ref binding.
            matches = _unique([item for item in self.bundle.get("supplied_contents", [])
                               if item["source_ref"] == source["source_ref"] and item["artifact_field"] == "request_ref"])
            if not matches:
                self.problem("parameter_source_unbound", path, refs=[source["source_ref"]], row=row)
                return None
            if (len(matches) != 1 or matches[0]["sha256"] != source["sha256"]
                    or source["pointer"] != c._SUBMITTED_PARAMETER_POINTER
                    or matches[0]["artifact_ref"] != "artifact_" + matches[0]["sha256"]):
                row["state"] = "invalid"
                self.problem("parameter_source_conflict", path, refs=[source["source_ref"]], severity="error", row=row)
                return None
            content = matches[0]
            raw = self.bytes_for(content, path, row)
            if raw is None:
                return None
            try:
                _submitted_record(raw, task)
            except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
                row["state"] = "invalid"
                self.problem("parameter_source_conflict", path, refs=[source["source_ref"]], severity="error", row=row)
                return None
            if not self.register(content, path, row):
                return None
            return content
        recorded = task["effective_parameters"]
        if recorded is None:
            self.problem("parameter_source_unbound", path, refs=[source["source_ref"]], row=row)
            return None
        evidence, value = recorded["evidence"], recorded["value"]
        content = evidence["content"]
        if (source["source_ref"], source["sha256"], source["pointer"]) != (content["source_ref"], content["sha256"], evidence["pointer"]):
            row["state"] = "invalid"
            self.problem("parameter_source_conflict", path, refs=[source["source_ref"], content["source_ref"]], severity="error", row=row)
            return None
        matches = [r for r in self.values if r["evidence"] == evidence]
        if len(matches) != 1 or content not in self.bundle.get("supplied_contents", []):
            self.problem("parameter_source_unbound", path, refs=[source["source_ref"]], row=row)
            return None
        if c.canonical(matches[0]["value"]) != c.canonical(value):
            row["state"] = "invalid"
            self.problem("parameter_source_conflict", path, refs=[source["source_ref"]], severity="error", row=row)
            return None
        raw = self.bytes_for(content, path, row)
        if raw is None:
            return None
        try:
            actual = _at(_json(raw), evidence["pointer"])
            if c.canonical(actual) != c.canonical(value):
                raise ValueError("parameter_conflict")
        except (ValueError, UnicodeError, RecursionError):
            row["state"] = "invalid"
            self.problem("parameter_source_conflict", path, refs=[source["source_ref"]], severity="error", row=row)
            return None
        if not self.register(content, path, row):
            return None
        return content

    def inputs(self, supplied, primary):
        selected = supplied["original_input_index"]
        if selected is not None:
            row, path = self.outcome("original_input_index", 0), self.data_path + "/original_input_index"
            if selected["mode"] == "parsed":
                self.parsed(selected, "InputIndexResult", path, row)
            elif primary is None:
                self.problem("primary_document_invalid", path, row=row)
            else:
                sources = [selected["parameter_source"], *selected["additional_parameter_sources"]]
                bindings = [self.parameter(s, path + ("/parameter_source" if i == 0 else f"/additional_parameter_sources/{i - 1}"), row)
                            for i, s in enumerate(sources)]
                if all(b is not None for b in bindings):
                    row["content"] = bindings[0]
                    self.input_index_result = index_original_inputs(self.bundle["original_task"],
                        parameter_source=selected["parameter_source"], additional_parameter_sources=selected["additional_parameter_sources"],
                        source_contract=primary["source_contract"])
                    row["result_index"] = 0
                    self.record(self.input_index_result, row, "/input_index_result", "proteome_original_input_index")
        for group, kind, result_name, contract, reader in _INPUTS:
            results = getattr(self, result_name)
            for i, selected in enumerate(supplied[group]):
                row, path = self.outcome(kind, i), self.data_path + f"/{group}/{i}"
                if selected["mode"] == "parsed":
                    self.parsed(selected, contract, path, row)
                    continue
                raw, source = self.input_source(selected, path, row)
                if raw is None:
                    continue
                kwargs = dict(source=source, declared_format=selected["declared_format"])
                if kind == "inventory":
                    kwargs["inventory_key"] = selected["inventory_key"]
                else:
                    population = deepcopy(selected["population"])
                    if not self.source_fields(population, path + "/population", row):
                        row["state"] = "invalid" if any(d["severity"] == "error" and d["path"] == path + "/population" for d in self.diagnostics) else "unverified"
                        continue
                    if population["population_complete"] == "yes" or population["origin"] == "execution_time_snapshot" or population["completeness_evidence"]:
                        self.problem("completeness_evidence_unverified", path + "/population", refs=[source["content"]["source_ref"]], row=row)
                        population["population_complete"] = "unknown"
                        if population["origin"] == "execution_time_snapshot":
                            population["origin"] = "unknown"
                    kwargs.update(snapshot_key=selected["snapshot_key"], population=population)
                    if kind == "feature_snapshot":
                        if not self.source_fields(selected["coordinate_convention"], path + "/coordinate_convention", row):
                            row["state"] = "unverified"
                            continue
                        kwargs["coordinate_convention"] = selected["coordinate_convention"]
                result = reader(raw, **kwargs)
                row["result_index"] = len(results)
                results.append(result)
                self.record(result, row, f'/{result_name}/{row["result_index"]}', "proteome_supplied_input")

    def primary(self):
        selected = [i for i, row in enumerate(self.parameters["native_documents"])
                    if row["document_id"] == self.parameters["primary_document_id"]]
        if not selected:
            self.problem("primary_document_missing", "/parameters/primary_document_id")
            return None
        row = self.outcomes[selected[0]]
        if row["result_index"] is not None:
            value = self.native_results[row["result_index"]]["value"]
            if value is not None and value["projection_completeness"] != "invalid_document":
                return value
        self.problem("primary_document_invalid", "/parameters/primary_document_id", row=row)
        return None

    def link_conflicts(self, supplied, primary):
        """Expose exact source contradictions without changing B2's raw claims."""
        if primary is None:
            return
        content = primary["source"]["content"]
        for i, link in enumerate(supplied["native_links"]):
            selected = link["native"]
            if (selected["source_ref"], selected["sha256"]) != (content["source_ref"], content["sha256"]):
                self.problem("supplied_source_conflict", self.data_path + f"/native_links/{i}/native",
                    refs=[selected["source_ref"], content["source_ref"]], severity="error")


def consume_bundle(bundle: dict, *, artifact_bytes: dict[str, bytes], supplied_values: list[dict],
                   requested_form: dict, parameters: dict) -> dict:
    """Resolve the existing host ABI, calling the actual native constructors once.

    Global malformed identities raise a finite ProteomeBundleError. Scoped
    acquisition/optional-input failures remain in the saved envelope and can
    coexist with available requested facts. This does not claim episode custody.
    """
    try:
        bundle = validate_contract("ArtifactBundle", bundle)
    except ContractValidationError as error:
        code = "proteome_original_task_conflict" if error.code == "original_task_mismatch" else "proteome_bundle_invalid"
        raise c.ProteomeBundleError(code, c._error_path(error)) from error
    try:
        c.canonical(bundle).encode("utf-8")
    except (ValueError, UnicodeError, RecursionError) as error:
        raise c.ProteomeBundleError("proteome_bundle_invalid", "/bundle") from error
    parameters = c.validate_parameters(parameters)
    try:
        form = validate_requested_form(requested_form)
    except ValueError as error:
        raise c.ProteomeBundleError("proteome_requested_form_invalid", getattr(error, "path", "")) from error
    task = bundle["original_task"]
    c._require(task["required_application_id"] == task["native_application_id"] == "GenomeComparison", "application_mismatch", "/original_task")
    c._require(type(artifact_bytes) is dict and all(type(k) is str and k and type(v) is bytes for k, v in artifact_bytes.items()), "bundle_invalid", "/artifact_bytes")
    c._require(type(supplied_values) is list, "supplied_data_invalid", "/supplied_values")
    for i, value in enumerate(supplied_values):
        c.validate_shape("SuppliedValue", value, code="supplied_data_invalid", path=f"/supplied_values/{i}")
    c._require([r["evidence"] for r in supplied_values] == bundle["supplied_scientific_metadata"], "supplied_source_conflict", "/supplied_values")
    supplied_values = deepcopy(supplied_values)
    resolution = _Resolution(bundle, artifact_bytes, supplied_values, parameters, form)
    resolution.documents()
    primary = resolution.primary()
    supplied = resolution.supplementary()
    if supplied is not None:
        resolution.inputs(supplied, primary)
        resolution.link_conflicts(supplied, primary)
    groups = {name: [result["value"] for result in getattr(resolution, result_name) if result["value"] is not None]
              for name, _, result_name, _, _ in _INPUTS}
    index = resolution.input_index_result
    data = dict(input_index=index["value"] if index is not None else None, **groups)
    joins = sheet = components = None
    if primary is not None:
        joins = build_native_joins(primary, **data,
            execution_links=supplied["execution_links"] if supplied is not None else [],
            native_links=supplied["native_links"] if supplied is not None else [],
            metadata_links=supplied["metadata_links"] if supplied is not None else [])
        resolution.pure(joins, "/joins_result", role="proteome_native_projection")
        sheet = build_native_sheet(resolution.native_results, primary_source_ref=primary["source"]["content"]["source_ref"],
            **data, joins=joins["value"], representation_links=supplied["representation_links"] if supplied is not None else [],
            directional_attachment=None)
        resolution.pure(sheet, "/native_sheet_result", role="proteome_native_projection")
        if sheet["value"] is not None:
            components = calculate_native_components(sheet["value"], parameters=parameters["calculation_parameters"])
            resolution.pure(components, "/components", role="proteome_native_projection")
    saved = dict(version="bvbrc_proteome_provider_sheet_v1", analysis_id=parameters["analysis_id"],
        original_task=task, parameters=parameters, requested_form=form, bundle_sha256=c.digest(bundle),
        supplied_values=supplied_values, input_resolution=resolution.outcomes, native_results=resolution.native_results,
        input_index_result=resolution.input_index_result, inventory_results=resolution.inventory_results,
        feature_results=resolution.feature_results, genome_results=resolution.genome_results,
        sequence_results=resolution.sequence_results, joins_result=joins, native_sheet_result=sheet,
        requirements=resolution.requirements, diagnostics=resolution.diagnostics)
    saved = c.validate_provider_sheet(saved)
    from .bvbrc_proteome_bundle_projection import project_requested_facts
    projection = project_requested_facts(saved, components, missing_requirements=tuple(saved["requirements"]),
        diagnostics=tuple(saved["diagnostics"]), requested_form=form, parameters=parameters)
    return dict(adapter_id="bvbrc_proteome", adapter_version="1", **projection, sheet=saved, components=components)


__all__ = ["consume_bundle"]
