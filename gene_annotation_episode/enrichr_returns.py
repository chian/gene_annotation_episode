"""Original Enrichr API publications and literal, frozen typed-return custody.

This owner reads existing selected actions, publications and successful forms.
It submits no work and computes no enrichment statistic. Closed returns use
their original frozen witnesses and cells, without parsing native bytes again.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re

from jsonschema import Draft202012Validator

from .communication import ReportBoundaryError, plain
from .domain import identity
from .api_enrichr import PROTOCOL_VERSION, WIRE_PROFILE, _prepared as validate_prepared_enrichr
from .enrichr_contracts import (TABLE_SOURCE, ROW_SOURCE, enrichr_fact_sources,
    project_enrichr_return, validate_enrichr_selector, validate_enrichr_sheet)
from .enrichr_reference_privacy import (validated_enrichr_source, normalized_enrichr_outcome,
    matching_enrichr_publications, committed_enrichr_reference_kind)
from .episode_receipts import (EpisodeReceipts, RECEIVED_REPORT_PREFIX_VERSION,
    _validate_report_prefix)
from .episode_return_records import EpisodeReturnRecords, _same
from .execution_contracts import digest
from .practical_execution_state import _read
from .tool_grading_artifacts import source_tool_grading_entries


SOURCES = (TABLE_SOURCE, ROW_SOURCE)
OWN_WITNESSES = "enrichr_original_publication_witnesses_v1"
CLOSURE_PREFIX = "enrichr_received_report_prefix_v1"
_RECEIVERS = {"annotation", "scientific_process"}
_WITNESS_FIELDS = {"source_ref", "operation_key", "source_record_sha256", "native_artifact_ref",
    "snapshot_sha256", "snapshot_metadata_sha256", "request_artifact_ref", "grading_artifact_ref",
    "tool_operation_sha256", "selector_sha256", "projected_sha256",
    "native_artifact_metadata_sha256", "request_artifact_metadata_sha256", "grading_artifact_metadata_sha256",
    "protocol_artifacts"}


def _boundary(code, field=None):
    return ReportBoundaryError("enrichr_" + code, code="enrichr_" + code, field=field)


def requested_enrichr_fields(schema):
    """Recognize exact source-owned contracts; this does not authenticate values."""
    schema = plain(schema)
    if not isinstance(schema, dict) or not isinstance(schema.get("properties", {}), dict):
        raise _boundary("original_schema_conflict")
    available, result = enrichr_fact_sources(), {}
    for name, node in schema.get("properties", {}).items():
        if not isinstance(node, dict):
            continue
        source = node.get("x-source")
        if source in SOURCES:
            if not _same(node, available[source]["report_schema"]):
                raise _boundary("original_schema_conflict", name)
            result[name] = source
        elif isinstance(source, str) and source.startswith("execution_enrichr_"):
            raise _boundary("original_schema_conflict", name)
    return result


def _result_reference_fields(schema):
    """Recognize the existing standard result-reference field, not a new view."""
    expected = {"type": "array", "uniqueItems": True,
        "items": {"type": "string", "format": "reference", "x-reference-namespace": "execution_result"},
        "x-source": "execution_result_refs"}
    result = []
    for name, node in plain(schema).get("properties", {}).items():
        if isinstance(node, dict) and node.get("x-source") == "execution_result_refs":
            if not _same(node, expected):
                raise _boundary("original_schema_conflict", name)
            result.append(name)
    return result


def _values(form, schema):
    fields, result = requested_enrichr_fields(schema), {}
    for name, source in fields.items():
        if name not in form:
            raise _boundary("selected_value_conflict", name)
        value = plain(form[name])
        validator = Draft202012Validator(enrichr_fact_sources()[source]["report_schema"])
        if not validator.is_valid(value):
            raise _boundary("selected_value_conflict", name)
        if source in result and not _same(value, result[source]):
            raise _boundary("selected_value_conflict", name)
        result[source] = deepcopy(value)
    return result


def _merge(groups):
    result, seen = {source: [] for source in SOURCES}, {source: {} for source in SOURCES}
    for group in groups:
        for source, rows in group.items():
            if source not in SOURCES:
                continue
            for row in rows:
                key = ((row["source_ref"], row["window"]["offset"], row["window"]["limit"])
                    if source == TABLE_SOURCE else (row["source_ref"], row["ordinal"]))
                previous = seen[source].get(key)
                if previous is not None:
                    if not _same(previous, row):
                        raise _boundary("selected_value_conflict")
                else:
                    seen[source][key] = row
                    result[source].append(deepcopy(row))
    return result


class EnrichrReturns(EpisodeReturnRecords):
    def __init__(self, api):
        super().__init__(api.store, api.run_id, failure_prefix="enrichr_")
        self.api = api

    def _require(self, condition, code):
        if not condition:
            raise _boundary(code)

    def authenticate(self, context, *, allow_unsaved=False):
        try:
            super().authenticate(context, allow_unsaved=allow_unsaved)
        except (ValueError, KeyError, TypeError) as error:
            raise _boundary("original_context_conflict") from error
        self._require(context.role == context.path[-1][0], "original_context_conflict")
        return context

    def validate_fields(self, context, schema):
        original = (plain(context.request).get("report_contract") or {}).get("measurements", {}).get("schema", {})
        declared = requested_enrichr_fields(original)
        selected = requested_enrichr_fields(schema)
        if declared:
            self._require(context.role in _RECEIVERS | {"results"}, "original_context_conflict")
        if selected:
            self._require(_same(selected, declared), "original_schema_conflict")
        return selected

    def _closed(self, context):
        row = self.db.execute("SELECT facts,form FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone()
        return None if row is None or row["form"] is None else {
            "facts": json.loads(row["facts"]), "form": json.loads(row["form"])}

    def _commission(self, parent, child):
        self._require(child.path[:-1] == parent.path, "original_context_conflict")
        self.store.validate_scope(plain(child.scope), parent_scope=plain(parent.scope))
        slot = child.path[-1][1]
        self._require(re.fullmatch(r"child_(0|[1-9][0-9]*)", slot) is not None, "original_context_conflict")
        row = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
            (self.run_id, parent.episode_id, int(slot[6:]))).fetchone()
        self._require(row is not None, "original_context_conflict")
        action = json.loads(row["action"])
        contract = plain(child.request).get("report_contract")
        self._require(isinstance(contract, dict), "original_schema_conflict")
        if action.get("kind") == "tool":
            self._require(action.get("tool") == "process.revise" and child.role == "scientific_process",
                "original_context_conflict")
            return
        self._require(action.get("kind") in {"child", "episode_child", "job_child"}
            and _same(action.get("scope"), child.scope)
            and _same(json.loads(action["schema_json"]), contract["measurements"]["schema"])
            and action.get("purpose") == contract["decision"], "original_schema_conflict")
        if action["kind"] in {"episode_child", "job_child"}:
            self._require(action.get("role") == child.role, "original_context_conflict")
        if child.role == "results":
            self._require(_same(action.get("assignment"), child.assignment), "original_context_conflict")

    def _attempt(self, context, index):
        try:
            child, form, schema = super()._attempt(context, index)
        except (ValueError, KeyError, TypeError) as error:
            raise _boundary("original_receipt_conflict") from error
        self._commission(context, child)
        closed = self._closed(child)
        self._require(closed is not None and _same(closed["form"], form), "frozen_prefix_conflict")
        self._require(_same(schema, plain(child.request)["report_contract"]["measurements"]["schema"]),
            "original_schema_conflict")
        return child, form, schema

    def _successful_closed(self, context):
        closed = self._closed(context)
        if closed is None or OWN_WITNESSES not in closed["facts"]:
            return False
        if not self._own_witnesses(context):
            return False
        rows = list(self.db.execute("SELECT parent_episode_id,decision_index FROM runtime_report_attempts "
            "WHERE run_id=? AND child_episode_id=? AND failure IS NULL AND form IS NOT NULL ORDER BY decision_index",
            (self.run_id, context.episode_id)))
        for row in rows:
            self._attempt(self.context(row["parent_episode_id"]), row["decision_index"])
        return bool(rows)

    @staticmethod
    def _runtime_outcome(value):
        return normalized_enrichr_outcome(value)

    def _source(self, reference):
        return validated_enrichr_source(self.store, reference)

    def _artifact_metadata(self, reference, *, content=None):
        metadata = self.store.get(reference)
        self._require(type(reference) is str and re.fullmatch(r"artifact_[a-f0-9]{64}", reference)
            and set(metadata) == {"id", "sha256", "media_type", "size", "record_type"}
            and metadata["id"] == reference and metadata["sha256"] == reference.removeprefix("artifact_")
            and metadata["record_type"] == "artifact" and type(metadata["size"]) is int
            and metadata["size"] >= 0 and type(metadata["media_type"]) is str,
            "artifact_identity_conflict")
        if content is not None:
            self._require(type(content) is bytes and len(content) == metadata["size"],
                "artifact_identity_conflict")
        return metadata

    def _protocol_artifacts(self, transport, native_ref, *, verify_bytes):
        self._require(type(transport) is dict, "protocol_artifact_conflict")
        protocol = transport.get("enrichr_protocol")
        self._require(type(protocol) is dict and set(protocol) == {"version", "wire_profile", "prepared", "stages"}
            and protocol["version"] == PROTOCOL_VERSION and protocol["wire_profile"] == WIRE_PROFILE
            and type(protocol["stages"]) is list and len(protocol["stages"]) in (2, 3), "protocol_artifact_conflict")
        artifacts = []
        for ordinal, stage in enumerate(protocol["stages"]):
            self._require(type(stage) is dict and set(stage) == {"ordinal", "stage_code", "snapshot"}
                and type(stage["ordinal"]) is int and stage["ordinal"] == ordinal
                and stage["stage_code"] in {"query_upload", "background_upload", "enrichment"}
                and type(stage["snapshot"]) is dict and set(stage["snapshot"]) == {
                    "service", "url", "request", "retrieved_at", "media_type", "transport", "content_ref"}
                and stage["snapshot"]["service"] == "enrichr", "protocol_artifact_conflict")
            reference = stage["snapshot"]["content_ref"]
            content = self.store.get_artifact(reference) if verify_bytes else None
            artifacts.append({"stage_ordinal": ordinal, "artifact_ref": reference,
                "artifact_metadata_sha256": digest(self._artifact_metadata(reference, content=content))})
        self._require(artifacts[-1]["artifact_ref"] == native_ref, "protocol_artifact_conflict")
        return artifacts

    def _own_witnesses(self, context):
        closed = self._closed(context)
        self._require(closed is not None, "frozen_prefix_conflict")
        value = closed["facts"].get(OWN_WITNESSES)
        self._require(type(value) is dict and set(value) == {"version", "publications"}
            and value["version"] == OWN_WITNESSES and type(value["publications"]) is list,
            "frozen_prefix_conflict")
        keys = set()
        for witness in value["publications"]:
            self._require(type(witness) is dict and set(witness) == _WITNESS_FIELDS,
                "frozen_prefix_conflict")
            self._require(all(type(witness[name]) is str and re.fullmatch(r"artifact_[a-f0-9]{64}", witness[name])
                for name in ("native_artifact_ref", "request_artifact_ref", "grading_artifact_ref")),
                "frozen_prefix_conflict")
            prefix = f"{self.run_id}:{context.episode_id}:"
            key = witness["operation_key"]
            self._require(type(witness["source_ref"]) is str and re.fullmatch(r"source_[a-f0-9]{24,64}", witness["source_ref"])
                and type(key) is str and key.startswith(prefix)
                and re.fullmatch(r"0|[1-9][0-9]*", key[len(prefix):]), "frozen_prefix_conflict")
            key = witness["source_ref"], witness["operation_key"]
            self._require(key not in keys, "frozen_prefix_conflict")
            keys.add(key)
            self._require(all(type(witness[name]) is str and re.fullmatch(r"[a-f0-9]{64}", witness[name])
                for name in _WITNESS_FIELDS if name.endswith("sha256")), "frozen_prefix_conflict")
            self._require(type(witness["protocol_artifacts"]) is list
                and len(witness["protocol_artifacts"]) in (2, 3), "frozen_prefix_conflict")
            for ordinal, artifact in enumerate(witness["protocol_artifacts"]):
                self._require(type(artifact) is dict and set(artifact) == {"stage_ordinal", "artifact_ref", "artifact_metadata_sha256"}
                    and type(artifact["stage_ordinal"]) is int and artifact["stage_ordinal"] == ordinal
                    and type(artifact["artifact_ref"]) is str and re.fullmatch(r"artifact_[a-f0-9]{64}", artifact["artifact_ref"])
                    and type(artifact["artifact_metadata_sha256"]) is str
                    and re.fullmatch(r"[a-f0-9]{64}", artifact["artifact_metadata_sha256"]), "frozen_prefix_conflict")
        return value["publications"]

    def _publication_records(self, reference, *, context, operation_key):
        """One metadata-only authority for the original selected RESULT records."""
        try:
            prefix = f"{self.run_id}:{context.episode_id}:"
            self._require(type(operation_key) is str and operation_key.startswith(prefix)
                and re.fullmatch(r"0|[1-9][0-9]*", operation_key[len(prefix):]), "original_receipt_conflict")
            assignment = plain(context.assignment)
            self._require(set(assignment) == {"version", "handoff_ref", "selector"}
                and assignment["version"] == "execution_results_assignment_v1", "original_context_conflict")
            selector = validate_enrichr_selector(assignment["selector"])
            directory = self.api._episode_directory(context.episode_id) / "actions" / digest(operation_key)
            metadata = _read(directory / "snapshot.json")
            intent, outcome, receipt = (_read(directory / name) for name in ("intent.json", "outcome.json", "acquisition.json"))
            prepared = validate_prepared_enrichr(intent["prepared"])
            request = prepared["request"]
            self._require(prepared["operation"] == "api.enrichr.result"
                and intent["run_id"] == context.run_id and intent["episode_id"] == context.episode_id
                and intent["operation_key"] == operation_key and intent["name"] == "api.enrichr.result"
                and intent["arguments"] == {} and intent["assignment_sha256"] == digest(assignment), "original_context_conflict")
            self._require(receipt["version"] == "api_service_acquisition_v1"
                and receipt["run_id"] == context.run_id and receipt["episode_id"] == context.episode_id
                and receipt["operation_key"] == operation_key and receipt["name"] == intent["name"]
                and receipt["arguments"] == {} and receipt["assignment_sha256"] == digest(assignment)
                and receipt["handoff_ref"] == assignment["handoff_ref"] and _same(receipt["selector"], selector)
                and receipt["source_ref"] == reference, "original_receipt_conflict")
            source = self._source(reference)
            self._require(metadata["service"] == "enrichr"
                and source["artifact_ref"] == metadata["content_ref"] == "artifact_" + receipt["snapshot_sha256"]
                and source["uri"] == metadata["url"] and source["retrieved_at"] == metadata["retrieved_at"], "source_snapshot_conflict")
            saved = self.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (operation_key + ":publication",)).fetchone()
            operands = {"arguments": {"request": request, "selector": selector},
                "snapshot_sha256": receipt["snapshot_sha256"], "request": metadata["request"], "transport": metadata["transport"]}
            self._require(saved is not None and saved["name"] == "internal.api_service.enrichr.result"
                and _same(json.loads(saved["arguments"]), operands) and _same(json.loads(saved["scope"]), context.scope), "original_receipt_conflict")
            original = json.loads(saved["result"])
            self._require(original["status"] in {"completed", "partial"} and original["record_refs"] == [reference]
                and original["operation_ref"] == saved["id"] == identity("operation", {
                    "key": operation_key + ":publication", "name": saved["name"], "arguments": operands}), "original_receipt_conflict")
            mandatory = {"source_ref", TABLE_SOURCE, ROW_SOURCE}
            self._require(set(original["result"]) in (mandatory, mandatory | {"projection_errors"})
                and original["result"]["source_ref"] == reference, "original_receipt_conflict")
            expected = deepcopy(original)
            expected["operation_ref"] = identity("api_operation", {"key": operation_key})
            expected["result"].update(acquisition_receipt=receipt, handoff_ref=assignment["handoff_ref"])
            self._require(_same(outcome, expected) and receipt["record_refs"] == outcome["record_refs"], "original_receipt_conflict")
            action = self.api._selected(context, intent["name"], intent["arguments"], operation_key)
            if action["result"] is not None:
                self._require(_same(self._runtime_outcome(json.loads(action["result"])), outcome), "original_receipt_conflict")
            public = {name: deepcopy(original["result"][name]) for name in SOURCES}
            for name in SOURCES:
                self._require(Draft202012Validator(enrichr_fact_sources()[name]["report_schema"]).is_valid(public[name])
                    and all(row["source_ref"] == reference for row in public[name]), "selected_value_conflict")
            grading = source.get("auxiliary_artifact_refs")
            self._require(type(grading) is list and len(grading) == 1, "grading_custody_conflict")
            witness = {"source_ref": reference, "operation_key": operation_key,
                "source_record_sha256": digest(source), "native_artifact_ref": source["artifact_ref"],
                "snapshot_sha256": receipt["snapshot_sha256"], "snapshot_metadata_sha256": digest(metadata),
                "request_artifact_ref": source["request_ref"], "grading_artifact_ref": grading[0],
                "tool_operation_sha256": digest(dict(saved)), "selector_sha256": digest(selector),
                "projected_sha256": digest(public),
                "native_artifact_metadata_sha256": digest(self._artifact_metadata(source["artifact_ref"])),
                "request_artifact_metadata_sha256": digest(self._artifact_metadata(source["request_ref"])),
                "grading_artifact_metadata_sha256": digest(self._artifact_metadata(grading[0])),
                "protocol_artifacts": self._protocol_artifacts(metadata["transport"], source["artifact_ref"], verify_bytes=False)}
            return {"metadata": metadata, "intent": intent, "outcome": outcome, "receipt": receipt,
                "source": source, "public": public, "witness": witness, "request": request, "selector": selector,
                "action_committed": action["result"] is not None}
        except ReportBoundaryError:
            raise
        except (ValueError, TypeError, KeyError, IndexError, OSError) as error:
            raise _boundary("original_receipt_conflict") from error

    def historical_result_witness(self, reference, *, context, operation_key):
        """Prove an admitted frozen publication before the API reads its handoff.

        This port never calls API.read_result, read_own or API._context. The API
        separately verifies the original query handoff after this pre-proof.
        """
        self.authenticate(context)
        self._require(context.role == "results" and _same(self.context(context.episode_id).as_record(), context.as_record()),
            "original_context_conflict")
        schema = (plain(context.request).get("report_contract") or {}).get("measurements", {}).get("schema", {})
        self.validate_fields(context, schema)
        self._require(self._successful_closed(context), "frozen_prefix_conflict")
        matches = [item for item in self._own_witnesses(context)
            if item["source_ref"] == reference and item["operation_key"] == operation_key]
        self._require(len(matches) == 1, "frozen_prefix_conflict")
        records = self._publication_records(reference, context=context, operation_key=operation_key)
        self._require(records["action_committed"] and _same(records["witness"], matches[0]), "frozen_prefix_conflict")
        frozen = self._frozen_values(context, schema)
        for name, values in frozen.items():
            selected = [row for row in values if row["source_ref"] == reference]
            self._require(_same(selected, records["public"][name]), "frozen_prefix_conflict")
        return deepcopy(matches[0])

    def read_own(self, reference, *, context, operation_key=None, verify_artifacts=True):
        self.authenticate(context, allow_unsaved=True)
        self._require(context.role == "results" and type(verify_artifacts) is bool, "original_context_conflict")
        if not verify_artifacts:
            self._require(self._successful_closed(context), "frozen_prefix_conflict")
            if operation_key is None:
                matches = [item for item in self._own_witnesses(context) if item["source_ref"] == reference]
                self._require(len(matches) == 1, "original_receipt_conflict")
                operation_key = matches[0]["operation_key"]
            self.historical_result_witness(reference, context=context, operation_key=operation_key)
        try:
            body = self.api.read_result(reference, context.scope, episode_id=context.episode_id,
                operation_key=operation_key, verify_artifacts=verify_artifacts)
            result = body["publication_result"]
            key = result["acquisition_receipt"]["operation_key"]
            records = self._publication_records(reference, context=context, operation_key=key)
            source, metadata, public = records["source"], records["metadata"], records["public"]
            self._require(body.get("version") == "api_service_acquired_result_v1"
                and body["target"]["assignment"].get("service") == "enrichr"
                and _same(body["scope"], context.scope) and _same(body["assignment"], context.assignment)
                and body["source_ref"] == reference and body["snapshot_sha256"] == records["receipt"]["snapshot_sha256"]
                and _same(body["service_request"], records["request"])
                and _same(result, records["outcome"]["result"]) and body["status"] == records["outcome"]["status"], "original_context_conflict")
            service = self.api.services[body["target"]["resource_id"]]
            prepared = service.prepare("api.enrichr.result", records["request"], {}, scope=body["scope"],
                previous_events=[], selector=records["selector"])
            self._require(_same(prepared, records["intent"]["prepared"]), "original_context_conflict")
            witness = records["witness"]
            if verify_artifacts:
                raw = self.store.get_artifact(source["artifact_ref"])
                control_bytes = self.store.get_artifact(source["request_ref"])
                control = json.loads(control_bytes)
                self._require(_same(control, {"request": metadata["request"], "transport": metadata["transport"]}), "source_snapshot_conflict")
                self._require(_same(self._protocol_artifacts(control["transport"], source["artifact_ref"], verify_bytes=True),
                    witness["protocol_artifacts"]), "protocol_artifact_conflict")
                entries = source_tool_grading_entries(self.store, reference)
                self._require(len(entries) == 1 and entries[0]["artifact_ref"] == witness["grading_artifact_ref"], "grading_custody_conflict")
                grade = entries[0]["grading"]
                self._require(type(grade) is dict and set(grade) == {"version", "sheet", "components"}
                    and grade["version"] == "enrichr_grade_v1", "grading_custody_conflict")
                sheet = validate_enrichr_sheet(grade["sheet"])
                import base64
                self._require(base64.b64decode(sheet["response"]["raw_base64"], validate=True) == raw
                    and _same(sheet["request"], records["request"])
                    and sheet["response"]["complete"] is metadata["transport"]["body_complete"]
                    and sheet["response"]["media_type"] == metadata["transport"].get("headers", {}).get("content-type", metadata["media_type"])
                    and _same(sheet, grade["components"]["sheet"])
                    and _same(records["selector"], grade["components"]["selector"]), "grading_custody_conflict")
                self._require(_same(project_enrichr_return(grade["components"], source_ref=reference), public), "selected_value_conflict")
                for role, artifact, content in (("native", source["artifact_ref"], raw),
                        ("request", source["request_ref"], control_bytes),
                        ("grading", witness["grading_artifact_ref"], self.store.get_artifact(witness["grading_artifact_ref"]))):
                    self._require(digest(self._artifact_metadata(artifact, content=content)) == witness[role + "_artifact_metadata_sha256"],
                        "artifact_identity_conflict")
            return {**body, "enrichr_values": public, "enrichr_witness": witness}
        except ReportBoundaryError:
            raise
        except (ValueError, TypeError, KeyError, IndexError, OSError) as error:
            raise _boundary("original_receipt_conflict") from error


    def _acquisitions(self, context, *, verify_artifacts):
        for directory, outcome in self.api._own_outcomes(context):
            intent = _read(directory / "intent.json")
            if intent.get("name") != "api.enrichr.result":
                continue
            result = outcome.get("result") or {}
            receipt = result.get("acquisition_receipt")
            if outcome.get("status") not in {"completed", "partial"} or receipt is None:
                continue
            self._require(receipt["operation_key"] == intent["operation_key"],
                "original_receipt_conflict")
            yield self.read_own(result["source_ref"], context=context,
                operation_key=receipt["operation_key"], verify_artifacts=verify_artifacts)

    def _frozen_values(self, context, schema):
        closed = self._closed(context)
        if closed is None:
            return None
        values = _values(closed["form"], schema)
        self._require(all(source in closed["facts"] and _same(value, closed["facts"][source])
            for source, value in values.items()), "frozen_prefix_conflict")
        return values

    @staticmethod
    def _witness(attempt):
        return {**{key: attempt[key] for key in ("decision_index", "delivery_ref", "child_episode_id")},
            "contract_sha256": digest(json.loads(attempt["contract"])), "form_sha256": digest(json.loads(attempt["form"]))}

    def _prefix(self, context):
        closed = self._closed(context)
        self._require(closed is not None and CLOSURE_PREFIX in closed["facts"], "frozen_prefix_conflict")
        try:
            return _validate_report_prefix(closed["facts"][CLOSURE_PREFIX])
        except ValueError as error:
            raise _boundary("frozen_prefix_conflict") from error

    def _historical(self, context, form, schema):
        self.authenticate(context)
        self.validate_fields(context, schema)
        values = _values(form, schema)
        self._require(_same(values, self._frozen_values(context, schema)), "frozen_prefix_conflict")
        if context.role == "results":
            bodies = list(self._acquisitions(context, verify_artifacts=False))
            expected = _merge([body["enrichr_values"] for body in bodies])
        else:
            wrappers, _ = self._received(context, allowed=self._prefix(context)["attempts"])
            expected = _merge([_values(wrapper["form"], wrapper["schema"]) for wrapper in wrappers])
        self._require(all(_same(value, expected[source]) for source, value in values.items()), "selected_value_conflict")
        return values

    def _received(self, context, *, allowed=None):
        self.authenticate(context, allow_unsaved=True)
        self._require(context.role in _RECEIVERS, "original_context_conflict")
        wrappers, current, prefix, seen, direct = [], context, allowed, set(), []
        while True:
            self._require(current.episode_id not in seen, "frozen_prefix_conflict")
            seen.add(current.episode_id)
            attempts = list(self.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? "
                "AND failure IS NULL AND form IS NOT NULL ORDER BY decision_index", (self.run_id, current.episode_id)))
            if prefix is not None:
                actual = {row["decision_index"]: self._witness(row) for row in attempts}
                self._require(all(_same(saved, actual.get(saved["decision_index"])) for saved in prefix), "frozen_prefix_conflict")
            for attempt in attempts:
                witness = self._witness(attempt)
                if prefix is not None and not any(_same(witness, item) for item in prefix):
                    continue
                schema = json.loads(attempt["contract"])["measurements"]["schema"]
                if not requested_enrichr_fields(schema):
                    continue
                child, form, schema = self._attempt(current, attempt["decision_index"])
                self._historical(child, form, schema)
                wrappers.append({"form": form, "schema": schema, "attempt": witness})
                if current.episode_id == context.episode_id:
                    direct.append(witness)
            manifest = EpisodeReceipts.read_manifest(self.db, self.run_id, current.episode_id)
            self._require(_same(plain(current.request)["message"].get("knowledge_inheritance"), manifest),
                "frozen_prefix_conflict")
            parent_id = manifest["parent_episode_id"]
            if parent_id is None:
                self._require(len(current.path) == 1, "frozen_prefix_conflict")
                break
            self._require("received_report_prefix" in manifest, "frozen_prefix_conflict")
            parent = self.context(parent_id)
            self._commission(parent, current)
            current, prefix = parent, manifest["received_report_prefix"]["attempts"]
        return wrappers, {"version": RECEIVED_REPORT_PREFIX_VERSION, "attempts": direct}

    def facts(self, context, schema):
        fields = self.validate_fields(context, schema)
        if context.role != "results":
            return self.received_facts(context, schema) if fields else {}
        self.authenticate(context, allow_unsaved=True)
        frozen = self._frozen_values(context, schema)
        closed = frozen is not None and self._successful_closed(context)
        bodies = list(self._acquisitions(context, verify_artifacts=not closed))
        values = _merge([body["enrichr_values"] for body in bodies])
        selected = {source: values[source] for source in dict.fromkeys(fields.values())}
        if frozen is not None:
            self._require(_same(frozen, selected), "frozen_prefix_conflict")
        witnesses = [body["enrichr_witness"] for body in bodies]
        if closed:
            self._require(_same(witnesses, self._own_witnesses(context)), "frozen_prefix_conflict")
        return {**selected, **({OWN_WITNESSES: {"version": OWN_WITNESSES,
            "publications": witnesses}} if witnesses else {})}

    def facts_for_closure(self, context, schema):
        fields = self.validate_fields(context, schema)
        if context.role == "results":
            return self.facts(context, schema)
        if not fields:
            return {}
        with self.store.read_snapshot():
            frozen = self._frozen_values(context, schema)
            prefix = self._prefix(context) if frozen is not None else None
            wrappers, captured = self._received(context, allowed=None if prefix is None else prefix["attempts"])
            values = _merge([_values(wrapper["form"], wrapper["schema"]) for wrapper in wrappers])
            selected = {source: values[source] for source in dict.fromkeys(fields.values())}
            if frozen is not None:
                self._require(_same(selected, frozen), "frozen_prefix_conflict")
            return {**selected, CLOSURE_PREFIX: deepcopy(captured if prefix is None else prefix)}

    def received_facts(self, context, schema):
        return {key: value for key, value in self.facts_for_closure(context, schema).items() if key in SOURCES}

    def received_context(self, context):
        self.authenticate(context, allow_unsaved=True)
        if context.role not in _RECEIVERS:
            return {}
        closed = self._closed(context)
        allowed = self._prefix(context)["attempts"] if closed is not None and CLOSURE_PREFIX in closed["facts"] else None
        with self.store.read_snapshot():
            wrappers, _ = self._received(context, allowed=allowed)
            return _merge([_values(wrapper["form"], wrapper["schema"]) for wrapper in wrappers])

    def validate_received_report(self, context, form, schema):
        fields = self.validate_fields(context, schema)
        if not fields:
            return
        values = _values(plain(form), plain(schema))
        expected = self.facts(context, schema)
        self._require(all(_same(value, expected[source]) for source, value in values.items()), "selected_value_conflict")

    def record_admission(self, context, form, schema, operation_key):
        rich_fields = requested_enrichr_fields(schema)
        reference_fields = _result_reference_fields(schema)
        if not rich_fields and not reference_fields:
            return []
        self._require(context.role in _RECEIVERS, "original_context_conflict")
        child, saved, declared = self._attempt(context, self._admission_index(context, operation_key))
        self._require(_same(form, saved) and _same(schema, declared), "original_schema_conflict")
        references = []
        if rich_fields:
            values = self._historical(child, saved, declared)
            references.extend(row["source_ref"] for rows in values.values() for row in rows)
        for name in reference_fields if child.role == "results" else []:
            selected = saved[name]
            self._require(type(selected) is list and all(type(reference) is str for reference in selected)
                and len(selected) == len(set(selected)), "selected_value_conflict")
            for reference in selected:
                if self.store.get(reference).get("provider") != "enrichr":
                    continue
                matches = [item for item in self._own_witnesses(child) if item["source_ref"] == reference]
                self._require(len(matches) == 1, "frozen_prefix_conflict")
                self.historical_result_witness(reference, context=child, operation_key=matches[0]["operation_key"])
                references.append(reference)
        return list(dict.fromkeys(references))


    def _reference_kind(self, reference):
        if not isinstance(reference, str):
            return None
        # A provider-like Source alone cannot claim somebody else's artifact.
        # Prefilter the actual candidate before authenticating any publication.
        rows = matching_enrichr_publications(self.store, reference, current_run_id=self.run_id)
        kinds = set()
        for row in rows:
            if row["publication_run_id"] != self.run_id:
                kinds.add(committed_enrichr_reference_kind(self.store, row, reference))
                continue
            source = json.loads(row["data"])
            direct = ("source" if row["id"] == reference else "raw" if source["artifact_ref"] == reference
                else "private" if reference == source.get("request_ref") or reference in source.get("auxiliary_artifact_refs", []) else None)
            key = row["operation_key"].removesuffix(":publication")
            context = self.context(row["episode_id"])
            if direct is None:
                direct = "private"  # Exact protocol-stage candidate selected by SQL.
            self.read_own(row["id"], context=context, operation_key=key,
                verify_artifacts=not self._successful_closed(context))
            kinds.add(direct)
        return "private" if "private" in kinds else "source" if "source" in kinds else "raw" if "raw" in kinds else None

    def _known(self, context):
        receipts = EpisodeReceipts.__new__(EpisodeReceipts)
        receipts.store, receipts.db, receipts.run_id = self.store, self.db, self.run_id
        return set(receipts.known(context.episode_id))

    def resolve_own(self, context, reference, namespace):
        kind = self._reference_kind(reference)
        if kind is None:
            return None
        self.authenticate(context, allow_unsaved=True)
        if kind == "private":
            return False
        if kind == "raw":
            return namespace in {None, "artifact"} and reference in self._known(context)
        if context.role != "results":
            return self.resolve_received(context, reference, namespace)
        for body in self._acquisitions(context, verify_artifacts=not self._successful_closed(context)):
            if body["source_ref"] == reference:
                return namespace in {None, "source", "execution_result"}
        return namespace in {None, "source", "execution_result"} and reference in self._known(context)

    def resolve_received(self, context, reference, namespace):
        kind = self._reference_kind(reference)
        if kind is None:
            return None
        self.authenticate(context, allow_unsaved=True)
        if kind == "private":
            return False
        if kind == "raw":
            return namespace in {None, "artifact"} and reference in self._known(context)
        if context.role not in _RECEIVERS:
            return False
        values = self.received_context(context)
        granted = {row["source_ref"] for rows in values.values() for row in rows}
        return namespace in {None, "source", "execution_result"} and (
            reference in granted or reference in self._known(context))


__all__ = ["EnrichrReturns", "requested_enrichr_fields", "OWN_WITNESSES", "CLOSURE_PREFIX"]
