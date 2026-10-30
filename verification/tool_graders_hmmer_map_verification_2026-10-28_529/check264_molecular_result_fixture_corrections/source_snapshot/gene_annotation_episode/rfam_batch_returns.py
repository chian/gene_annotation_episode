"""Authenticated copies of the original requested Rfam numerical projection.

The generic API journal proves selected work and response custody. Its original
publication fixes the native/submission sources, parse, sheet and calculation.
Immediate parents learn only the fact families admitted by the child's
original typed form. Reading performs no acquisition, parsing or calculation,
and records no action, observation or credit.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .communication import plain, validate_form
from .domain import identity
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .form_reference_validation import _binding_key, form_validation_value
from .practical_execution_state import _read
from .rfam_batch_contracts import (RFAM_METRIC_UNITS, RFAM_MISSING_REASONS,
    RfamParseResult, closed_object, is_int, is_text, rfam_digest, validate_rfam_result_selector)
from .rfam_batch_report_contracts import (REPORT_FORMAT, REPORT_PARSE_VERSION,
    RFAM_REPORT_ISSUE_CODES, RFAM_REPORT_METRIC_UNITS, RFAM_REPORT_MISSING_REASONS,
    RfamBatchReportParseResult)


FACT_SOURCES = ("rfam_result_rows", "rfam_result_populations", "rfam_report_rows")
IDENTIFIER_NAMESPACES = ("rfam_record", "rfam_query", "rfam_family", "rfam_model")
_IDENTIFIER_FIELDS = dict(zip(IDENTIFIER_NAMESPACES,
    ("record_key", "query_occurrence_key", "family_accession", "model_name")))
_RESULT_FIELDS = ("source_ref", "submission_source_ref", "artifact_ref", "format",
    "sheet_ref", "calculation_ref", "projection", "projection_errors", "grading_source_ref")
_MANIFEST_FIELDS = ("version", "request", "selector", "input_identity", "parse_ref",
    *(key for key in _RESULT_FIELDS if key != "grading_source_ref"))
_MANIFEST_V2_FIELDS = (*_MANIFEST_FIELDS, "parse_digest", "sheet_schema", "sheet_digest",
    "calculation_schema", "calculation_digest")
_PREFIX = "rfam_return_"


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
        "additionalProperties": False}


def _identifier(namespace, *, nullable=False):
    return {"type": ["string", "null"] if nullable else "string", "format": "identifier",
        "x-reference-namespace": namespace}


def rfam_fact_sources():
    """Closed numerical rows and a separate population, including empty results."""
    source = {"type": "string", "format": "reference", "x-reference-namespace": "execution_result"}
    metric = {"type": "string", "enum": list(RFAM_METRIC_UNITS)}
    row = _object({"source_ref": source, "record_key": _identifier("rfam_record"),
        "query_occurrence_key": _identifier("rfam_query", nullable=True),
        "family_accession": _identifier("rfam_family", nullable=True),
        "strand": {"type": ["string", "null"], "format": "alignment_strand"},
        "measured": {"type": "array", "items": _object({"name": metric,
            "value": {"type": "number"}, "unit": {"type": "string",
                "enum": sorted(set(RFAM_METRIC_UNITS.values()))}})},
        "unavailable": {"type": "array", "items": _object({"name": metric,
            "reason": {"type": "string", "enum": sorted(RFAM_MISSING_REASONS)}})},
        "population_complete": {"type": "boolean"}})
    population = _object({"source_ref": source,
        "family": {"type": "string", "enum": ["hit", "query_strand"]},
        "available_row_count": {"type": "integer", "minimum": 0},
        "selected_row_count": {"type": "integer", "minimum": 0},
        "more_rows": {"type": "boolean"}, "population_complete": {"type": "boolean"}})
    report_row = deepcopy(row)
    report_fields = report_row["properties"]
    report_fields["model_name"] = _identifier("rfam_model", nullable=True)
    report_row["required"].append("model_name")
    for field in ("measured", "unavailable"):
        report_fields[field]["items"]["properties"]["name"]["enum"] = list(RFAM_REPORT_METRIC_UNITS)
    report_fields["measured"]["items"]["properties"]["unit"]["enum"] = sorted(set(RFAM_REPORT_METRIC_UNITS.values()))
    report_fields["unavailable"]["items"]["properties"]["reason"]["enum"] = sorted(RFAM_REPORT_MISSING_REASONS)
    meanings = (
        "Only the original saved requested Rfam rows, with native units, explicit unavailable cells "
        "and query/family associations. Family labels and native scores are not annotation probabilities.",
        "The original requested Rfam population and selection sizes. A complete zero-row result "
        "remains distinguishable from a missing or incomplete population.",
        "Only the original saved requested native report rows, preserving model names separately "
        "from nullable family accessions, numerical units and explicit unavailable cells.")
    return deepcopy({name: {"type": "array", "meaning": meaning,
        "report_schema": {"type": "array", "items": value, "x-source": name}}
        for name, value, meaning in zip(FACT_SOURCES, (row, population, report_row), meanings)})


def requested_sources(schema):
    return tuple(dict.fromkeys(node["x-source"]
        for node in plain(schema).get("properties", {}).values()
        if node.get("x-source") in FACT_SOURCES))


def _projection_facts(projection, format):
    facts = {source: [] for source in FACT_SOURCES}
    if projection is None:
        return facts
    # Only an authenticated manifest's actual format selects the new row form.
    row_source = "rfam_report_rows" if format == REPORT_FORMAT else "rfam_result_rows"
    facts[row_source] = [dict(source_ref=projection["source_ref"],
            **deepcopy(row), population_complete=projection["population_complete"])
            for row in projection["rows"]]
    facts["rfam_result_populations"] = [{key: deepcopy(projection[key]) for key in
        ("source_ref", "family", "available_row_count", "selected_row_count", "more_rows", "population_complete")}]
    return facts


class RfamBatchReturns(EpisodeReturnRecords):
    def __init__(self, execution):
        super().__init__(execution.store, execution.run_id, failure_prefix=_PREFIX)
        self.api = execution

    def authenticate(self, context, *, allow_unsaved=False):
        super().authenticate(context, allow_unsaved=allow_unsaved)
        self._require(context.role == context.path[-1][0], "context_role_conflict")
        return context

    def _source(self, reference, *, provider, origin):
        source = self.store.get(reference)
        self._require(source.get("record_type") == "source"
            and source.get("provider") == provider and source.get("origin") == origin,
            "source_identity_conflict")
        payload = {key: value for key, value in source.items() if key not in {"id", "record_type", "origin"}}
        self._require(reference == identity("source", {"origin": origin, "record": payload}),
            "source_identity_conflict")
        return source

    def _native_source(self, reference, snapshot, parents):
        source = self._source(reference, provider="rfam_batch", origin="external")
        self._require(source["artifact_ref"] == "artifact_" + snapshot.sha256
            and self.store.get_artifact(source["artifact_ref"]) == snapshot.content
            and source["uri"] == snapshot.url and source["retrieved_at"] == snapshot.retrieved_at
            and source.get("parent_source_refs", []) == parents,
            "original_source_conflict")
        self._require(self._equal(self.api._artifact_json(source["request_ref"]),
            {"request": snapshot.request, "transport": snapshot.transport}), "original_request_conflict")
        return source

    @staticmethod
    def _snapshot_identity(snapshot):
        return {"service": snapshot.service, "url": snapshot.url, "request": snapshot.request,
            "retrieved_at": snapshot.retrieved_at, "content_sha256": snapshot.sha256,
            "media_type": snapshot.media_type, "transport": snapshot.transport}

    def read(self, reference, scope, *, episode_id=None):
        """Prove custody, then return compact saved values and artifact references.

        No provider-name scan is an authority. The original acquisition names
        the publication; its original publication names every retained artifact.
        Full data is checked internally and never added to the returned body.
        """
        body = self.api.read_result(reference, scope, episode_id=episode_id)
        self._require(body.get("version") == "api_service_acquired_result_v1"
            and body.get("run_id") == self.run_id
            and body["target"]["assignment"].get("service") == "rfam_batch", "original_result_required")
        publication = body.get("publication_result")
        closed_object(publication, (*_RESULT_FIELDS, "handoff_ref", "acquisition_receipt"),
            code=_PREFIX + "publication_required")
        original = {key: publication[key] for key in _RESULT_FIELDS}
        self._require(reference in body["record_refs"]
            and body["record_refs"] == [publication["submission_source_ref"], publication["source_ref"], publication["grading_source_ref"]]
            and body["source_ref"] == publication["source_ref"], "result_source_conflict")
        target, request = body["target"], body["service_request"]
        selector = validate_rfam_result_selector(body["assignment"]["selector"])
        receipt = publication["acquisition_receipt"]
        self._require(receipt.get("run_id") == self.run_id and receipt.get("episode_id") == body["episode_id"]
            and receipt.get("name") == "api.rfam.fetch" and receipt.get("arguments") == {}
            and publication["handoff_ref"] == target["handle"], "original_receipt_conflict")
        directory = self.api._episode_directory(body["episode_id"])/"actions"/digest(receipt["operation_key"])
        snapshot = self.api._load_snapshot(_read(directory/"snapshot.json"))
        handoff = self.api._read_handoff(target["handle"], scope)
        submission = self.api._load_snapshot(handoff["snapshot"])
        handle = handoff["event"]["native_handle"]
        service = self.api.services[target["resource_id"]]
        prepared = service.prepare("api.rfam.fetch", request, {}, scope=body["scope"],
            previous_events=[], handle=handle, selector=selector)
        received = service.decode(prepared, snapshot)
        submitted = service.prepare("api.rfam.submit", request, {}, scope=target["scope"], previous_events=[])
        accepted = service.decode(submitted, submission)
        self._require(received["result_available"] and accepted["handoff_ready"]
            and self._equal(accepted["native_handle"], handle), "original_submission_conflict")
        saved = self.db.execute("SELECT * FROM tool_operations WHERE operation_key=?",
            (receipt["operation_key"] + ":publication",)).fetchone()
        arguments = {"request": request, "selector": selector, "handle": handle,
            "submission": self._snapshot_identity(submission), "response": self._snapshot_identity(snapshot)}
        operands = {"arguments": arguments, "snapshot_sha256": snapshot.sha256,
            "request": snapshot.request, "transport": snapshot.transport}
        self._require(saved is not None and saved["name"] == "internal.api_service.rfam.fetch"
            and self._equal(json.loads(saved["arguments"]), operands)
            and self._equal(json.loads(saved["scope"]), body["scope"]), "original_publication_conflict")
        outcome = json.loads(saved["result"])
        self._require(self._equal(outcome.get("result"), original)
            and outcome.get("record_refs") == body["record_refs"] and outcome.get("status") == body["status"],
            "original_publication_conflict")
        self._native_source(publication["submission_source_ref"], submission, [])
        native = self._native_source(publication["source_ref"], snapshot, [publication["submission_source_ref"]])
        self._require(publication["artifact_ref"] == native["artifact_ref"], "native_artifact_conflict")
        grading = self._source(publication["grading_source_ref"], provider="rfam_batch.grading", origin="tool")
        parents = [publication["submission_source_ref"], publication["source_ref"]]
        metadata_unbound = False
        if selector["model_metadata_ref"] is not None:
            # A bad optional reference stays in the original selector, with a
            # diagnostic. It cannot become a trusted parent or erase unrelated
            # native quantities. Inspect source type/scope, never its bytes on
            # this invalid path, using the publisher's same existing semantics.
            try:
                from .rfam_batch_publication import validate_rfam_metadata_source_scope
                validate_rfam_metadata_source_scope(self.store, selector["model_metadata_ref"], body["scope"])
            except ValueError:
                metadata_unbound = True
            if not metadata_unbound:
                parents.append(selector["model_metadata_ref"])
        self._require(grading.get("parent_source_refs") == list(dict.fromkeys(parents)), "grading_parents_conflict")
        manifest = self.api._artifact_json(grading["artifact_ref"])
        shared = manifest.get("version") == "rfam_batch_retained_grading_v2"
        closed_object(manifest, _MANIFEST_V2_FIELDS if shared else _MANIFEST_FIELDS,
            code=_PREFIX + "manifest_invalid")
        self._require(manifest["version"] in {"rfam_batch_retained_grading_v1", "rfam_batch_retained_grading_v2"}
            and self._equal(manifest["request"], request) and self._equal(manifest["selector"], selector)
            and all(self._equal(manifest[key], original[key]) for key in _RESULT_FIELDS if key != "grading_source_ref"),
            "manifest_publication_conflict")
        batch = request["mode"] == "sequence_batch"
        report = selector["version"] == "rfam_batch_result_selector_v3"
        identity_value = {"version": "rfam_batch_file_input_v1" if batch else "rfam_batch_input_identity_v1",
            **snapshot.request["input_operand"], "expected_job_id": handle["job_id"],
            "submission_source_ref": publication["submission_source_ref"]}
        self._require(self._equal(manifest["input_identity"], identity_value), "input_identity_conflict")
        artifact_refs = [manifest[key] for key in ("parse_ref", "sheet_ref", "calculation_ref")
            if manifest[key] is not None]
        self._require(grading.get("auxiliary_artifact_refs") == artifact_refs, "grading_artifacts_conflict")
        parsed = self.api._artifact_json(manifest["parse_ref"])
        self._require(parsed.get("format") == manifest["format"]
            and parsed.get("status") in {"complete", "partial", "rejected", "unsupported"}, "parse_schema_conflict")
        if shared:
            closed_object(parsed, ("version", "representation", "status", "format", "sheet", "issues"),
                code=_PREFIX + "parse_schema_conflict")
            self._require(parsed["version"] == "rfam_batch_parse_result_v2"
                and parsed["representation"] == selector["representation"]
                and type(parsed["issues"]) is list
                and manifest["parse_digest"] == rfam_digest(parsed), "parse_schema_conflict")
        elif report:
            self._require(parsed.get("version") == REPORT_PARSE_VERSION, "parse_schema_conflict")
            closed_object(parsed, RfamBatchReportParseResult.__annotations__, code=_PREFIX + "parse_schema_conflict")
            self._require(type(parsed["issues"]) is list, "parse_schema_conflict")
            for issue in parsed["issues"]:
                closed_object(issue, ("code", "severity", "field", "native_query_name", "source_line"),
                    code=_PREFIX + "parse_schema_conflict")
                self._require(issue["code"] in RFAM_REPORT_ISSUE_CODES
                    and issue["severity"] in {"error", "warning"}
                    and all(issue[key] is None or is_text(issue[key])
                        for key in ("field", "native_query_name"))
                    and (issue["source_line"] is None or is_int(issue["source_line"], minimum=1)), "parse_schema_conflict")
        if metadata_unbound:
            self._require(any(issue.get("field") == "model_metadata_ref" and issue.get("code") in {
                "rfam_model_metadata_conflict", "rfam_subject_out_of_scope", "rfam_batch_model_metadata_invalid"}
                for issue in parsed.get("issues", [])), "metadata_diagnostic_required")
        projection = manifest["projection"]
        if manifest["sheet_ref"] is None:
            self._require(parsed.get("sheet") is None and manifest["calculation_ref"] is None
                and projection is None, "unavailable_sheet_conflict")
            if shared:
                self._require(parsed["status"] in {"rejected", "unsupported"}
                    and all(manifest[key] is None for key in (
                        "sheet_schema", "sheet_digest", "calculation_schema", "calculation_digest")),
                    "unavailable_sheet_conflict")
            elif report and parsed.get("version") == REPORT_PARSE_VERSION:
                self._require(parsed["status"] in {"rejected", "unsupported"}, "parse_schema_conflict")
            elif parsed.get("version") == "rfam_batch_parse_result_v1":
                closed_object(parsed, RfamParseResult.__annotations__, code=_PREFIX + "parse_schema_conflict")
            else:
                from .rfam_batch_table import RfamBatchTableParseResult
                closed_object(parsed, RfamBatchTableParseResult.__annotations__, code=_PREFIX + "parse_schema_conflict")
                self._require(parsed["version"] == "rfam_batch_tblout_parse_result_v1", "parse_schema_conflict")
        else:
            sheet = self.api._artifact_json(manifest["sheet_ref"])
            calculation = self.api._artifact_json(manifest["calculation_ref"])
            self._require(self._equal(parsed.get("sheet"), sheet), "parse_sheet_conflict")
            capture = {"artifact_ref": native["artifact_ref"], "source_ref": native["id"],
                "source_sha256": snapshot.sha256, "evidence_kind": snapshot.transport.get("evidence_kind", "native_response"),
                "representation": selector["representation"], "http_status": snapshot.transport["status"],
                "body_complete": snapshot.transport["body_complete"], "request_job_id": handle["job_id"]}
            bindings = {"source_ref": native["id"], "sheet_ref": manifest["sheet_ref"],
                "calculation_ref": manifest["calculation_ref"], "sheet_digest": rfam_digest(sheet),
                "calculation_digest": rfam_digest(calculation)}
            if shared:
                from .infernal_search_contracts import (SHEET_SCHEMA, SCORE_SCHEMA,
                    validate_infernal_search_sheet, validate_infernal_search_scores)
                from .rfam_batch_infernal import project_rfam_infernal_result, select_rfam_common_sheet
                validate_infernal_search_sheet(sheet)
                validate_infernal_search_scores(calculation, sheet=sheet)
                select_rfam_common_sheet(sheet, representation=selector["representation"])
                self._require(manifest["sheet_schema"] == SHEET_SCHEMA
                    and manifest["calculation_schema"] == SCORE_SCHEMA
                    and manifest["sheet_digest"] == bindings["sheet_digest"]
                    and manifest["calculation_digest"] == bindings["calculation_digest"]
                    and calculation["parameters"] == {"hit_scope": "reported"}
                    and sheet["lineage"] is None, "calculation_binding_conflict")
                if batch:
                    capture.update(request_file_sha256=identity_value["submitted_file_sha256"],
                        submission_source_ref=publication["submission_source_ref"])
                else:
                    capture["request_sequence_sha256"] = identity_value["submitted_sequence_sha256"]
                profile, format_name = {
                    "json": ("rfam_single_json", "rfam_cmscan_single_json_v1"),
                    "tblout": ("rfam_batch_tblout", "infernal_tblout_1_cmscan_1_1_5"),
                    "out": ("rfam_batch_report", REPORT_FORMAT),
                }[selector["representation"]]
                context = sheet["source_context"]
                self._require(parsed["status"] in {"complete", "partial"}
                    and parsed["format"] == format_name
                    and context is not None and context.get("profile") == profile
                    and self._equal(context.get("capture"), capture)
                    and self._equal(context.get("input_identity"), identity_value), "common_input_conflict")
                expected_descriptor = {"profile": profile, "source_ref": native["id"],
                    "artifact_ref": native["artifact_ref"], "source_sha256": snapshot.sha256,
                    "source_byte_length": len(snapshot.content), "byte_hash_verified": True}
                self._require(len(sheet["artifacts"]) == 1
                    and sheet["artifacts"][0].get("artifact_id") == native["artifact_ref"]
                    and self._equal(sheet["artifacts"][0].get("source_descriptor"), expected_descriptor),
                    "common_source_conflict")
                project = lambda: project_rfam_infernal_result(sheet, calculation,
                    projection=selector["projection"], artifact_bindings=bindings,
                    representation=selector["representation"])
            elif report:
                from .rfam_batch_report_contracts import (
                    validate_rfam_report_sheet, validate_rfam_report_calculation)
                from .rfam_batch_report_views import project_rfam_batch_report_result
                self._require(parsed["version"] == REPORT_PARSE_VERSION
                    and manifest["format"] == REPORT_FORMAT
                    and parsed["status"] in {"complete", "partial"}, "parse_schema_conflict")
                validate_rfam_report_sheet(sheet)
                validate_rfam_report_calculation(calculation, sheet=sheet)
                capture.update(request_file_sha256=identity_value["submitted_file_sha256"],
                    submission_source_ref=publication["submission_source_ref"])
                self._require(self._equal(sheet["capture"], capture)
                    and self._equal(sheet["input_identity"], identity_value), "report_input_conflict")
                project = lambda: project_rfam_batch_report_result(sheet, calculation,
                    projection=selector["projection"], artifact_bindings=bindings)
            elif batch:
                from .rfam_batch_table_grader import PARAMETERS, VERSION, validate_rfam_table_inputs
                from .rfam_batch_table_views import project_rfam_batch_table_result
                validate_rfam_table_inputs(parsed)
                capture.update(request_file_sha256=identity_value["submitted_file_sha256"],
                    submission_source_ref=publication["submission_source_ref"])
                self._require(self._equal(parsed["capture"], capture)
                    and self._equal(parsed["input_identity"], identity_value), "table_input_conflict")
                closed_object(calculation, ("version", "sheet_digest", "parse_digest", "parameters",
                    "native_calculation", "hits", "query_strands", "population_complete"),
                    code=_PREFIX + "calculation_schema_conflict")
                self._require(calculation["version"] == VERSION
                    and calculation["sheet_digest"] == rfam_digest(sheet)
                    and calculation["parse_digest"] == rfam_digest(parsed)
                    and calculation["parameters"] == PARAMETERS
                    and calculation["native_calculation"].get("schema") == "infernal_search_scores_v1"
                    and calculation["native_calculation"].get("parameters") == PARAMETERS
                    and self._equal(calculation["native_calculation"].get("operation"), sheet.get("operation")),
                    "calculation_binding_conflict")
                project = lambda: project_rfam_batch_table_result(parsed, calculation,
                    projection=selector["projection"], artifact_bindings=bindings)
            else:
                from .rfam_batch_grader import validate_rfam_sheet
                from .rfam_batch_views import _checked_calculation, project_rfam_batch_result
                closed_object(parsed, RfamParseResult.__annotations__, code=_PREFIX + "parse_schema_conflict")
                self._require(parsed["version"] == "rfam_batch_parse_result_v1"
                    and parsed["format"] == "rfam_cmscan_single_json_v1", "parse_schema_conflict")
                capture["request_sequence_sha256"] = identity_value["submitted_sequence_sha256"]
                self._require(self._equal(sheet["source"], capture)
                    and self._equal(sheet["input"], identity_value), "json_input_conflict")
                _checked_calculation(validate_rfam_sheet(sheet), calculation)
                project = lambda: project_rfam_batch_result(sheet, calculation,
                    projection=selector["projection"], artifact_bindings=bindings)
            if projection is not None:
                self._require(selector["projection"] is not None and self._equal(project(), projection),
                    "saved_projection_conflict")
            else:
                self._require(selector["projection"] is None or bool(manifest["projection_errors"]),
                    "requested_projection_missing")
        facts = _projection_facts(projection, manifest["format"])
        self._check_fact_types(facts)
        return {**deepcopy(body), "projection": deepcopy(projection), "grading_source_ref": grading["id"]}

    @staticmethod
    def _original_sources(context):
        schema = (plain(context.request).get("report_contract") or {}).get("measurements", {}).get("schema", {})
        return requested_sources(schema)

    def _own_facts(self, context):
        self.authenticate(context, allow_unsaved=True)
        self._require(context.role == "results", "original_results_owner_required")
        facts = {name: [] for name in FACT_SOURCES}
        assignment, service, _ = self.api._context(context)
        if service.service != "rfam_batch":
            return facts
        seen = {name: set() for name in FACT_SOURCES}
        for _, outcome in self.api._own_outcomes(context):
            result = outcome.get("result") or {}
            if outcome.get("status") not in {"completed", "partial"} or "grading_source_ref" not in result:
                continue
            body = self.read(result["source_ref"], context.scope, episode_id=context.episode_id)
            self._require(self._equal(body["scope"], context.scope)
                and self._equal(body["assignment"], context.assignment)
                and self._equal(body["service_request"], assignment["request"]), "publication_owner_conflict")
            for source, rows in _projection_facts(body["projection"], body["publication_result"]["format"]).items():
                for row in rows:
                    key = canonical(row)
                    if key not in seen[source]:
                        facts[source].append(row)
                        seen[source].add(key)
        return facts

    def facts(self, context, schema):
        sources = requested_sources(schema)
        if not sources:
            return {}
        values = form_validation_value((self, "own", _binding_key(context)), lambda: self._own_facts(context))
        admitted = self._original_sources(context)
        return {name: values[name] if name in admitted else [] for name in sources}

    def _check_fact_types(self, values):
        descriptors = rfam_fact_sources()
        for source, rows in values.items():
            validate_form({"rows": rows}, _object({"rows": descriptors[source]["report_schema"]}), lambda *_: True)
        for row in (*values.get("rfam_result_rows", []), *values.get("rfam_report_rows", [])):
            # Shared forms already define this symbol format. Rfam's supported
            # values are narrower than its legacy optional "unknown" value.
            self._require(row["strand"] in {"+", "-", None}, "strand_invalid")

    def _values(self, form, schema):
        validate_form(form, schema, lambda *_: True)
        values = {}
        for name, node in plain(schema).get("properties", {}).items():
            source = node.get("x-source")
            if source in FACT_SOURCES:
                rows = plain(form[name])
                self._require(source not in values or self._equal(values[source], rows), "conflicting_fields")
                values[source] = rows
        self._check_fact_types(values)
        return values

    def _validate_values(self, context, form, schema):
        self.authenticate(context, allow_unsaved=True)
        self._require(set(requested_sources(schema)) <= set(self._original_sources(context)), "original_form_source_conflict")
        values = self._values(form, schema)
        if context.role == "results":
            expected = self.facts(context, schema)
        elif context.role in {"annotation", "scientific_process"}:
            expected = self.received_facts(context, schema)
        else:
            raise ValueError(_PREFIX + "unsupported_return_owner")
        self._require(self._equal(values, expected), "returned_facts_conflict")
        frozen = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone()
        if frozen is not None:
            saved = json.loads(frozen["facts"])
            self._require(all(name in saved and self._equal(saved[name], rows) for name, rows in values.items()),
                "frozen_facts_conflict")
        return values

    def _attempt(self, context, index):
        child, form, schema = super()._attempt(context, index)
        self.store.validate_scope(plain(child.scope), parent_scope=plain(context.scope))
        original = plain(child.request)["report_contract"]
        original_index = int(child.path[-1][1].removeprefix("child_"))
        row = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
            (self.run_id, context.episode_id, original_index)).fetchone()
        self._require(row is not None, "original_commission_required")
        selected = json.loads(row["action"])
        self._require(selected.get("kind") in {"episode_child", "child", "job_child"}
            or selected.get("kind") == "tool" and selected.get("tool") == "process.revise",
            "original_commission_conflict")
        if selected.get("kind") in {"episode_child", "child", "job_child"}:
            self._require(self._equal(selected.get("scope"), child.scope)
                and self._equal(json.loads(selected["schema_json"]), original["measurements"]["schema"])
                and selected.get("purpose") == original["decision"], "original_commission_conflict")
            if selected["kind"] in {"episode_child", "job_child"}:
                self._require(selected.get("role") == child.role, "commission_role_conflict")
            if child.role == "results":
                self._require(self._equal(selected.get("assignment"), child.assignment), "commission_assignment_conflict")
        if self._equal(schema, original["measurements"]["schema"]):
            frozen = self.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
                (self.run_id, child.episode_id)).fetchone()
            self._require(frozen is not None and frozen["form"] is not None
                and self._equal(json.loads(frozen["form"]), form), "frozen_form_conflict")
        return child, form, schema

    def _received(self, context):
        self.authenticate(context, allow_unsaved=True)
        self._require(context.role in {"annotation", "scientific_process"}, "unsupported_return_owner")
        grouped, seen = {name: [] for name in FACT_SOURCES}, {name: set() for name in FACT_SOURCES}
        attempts = self.db.execute("SELECT decision_index,contract FROM runtime_report_attempts WHERE run_id=? "
            "AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL ORDER BY decision_index",
            (self.run_id, context.episode_id)).fetchall()
        for attempt in attempts:
            schema = json.loads(attempt["contract"]).get("measurements", {}).get("schema", {})
            if not requested_sources(schema):
                continue
            child, form, declared = self._attempt(context, attempt["decision_index"])
            values = self._validate_values(child, form, declared)
            for source, rows in values.items():
                for row in rows:
                    key = canonical(row)
                    if key not in seen[source]:
                        grouped[source].append(deepcopy(row))
                        seen[source].add(key)
        return grouped

    def _received_values(self, context):
        return form_validation_value((self, "received", _binding_key(context)), lambda: self._received(context))

    def received_context(self, context):
        return [{"fact_source": source, "facts": rows}
            for source, rows in self._received_values(context).items() if rows]

    def received_facts(self, context, schema):
        sources = requested_sources(schema)
        values = self._received_values(context) if sources else {}
        return {name: values[name] for name in sources}

    def validate_received_report(self, context, form, schema):
        if requested_sources(schema):
            self._validate_values(context, plain(form), plain(schema))

    def record_admission(self, context, form, schema, operation_key):
        if not requested_sources(schema):
            return []
        self._require(context.role in {"annotation", "scientific_process"}, "unsupported_return_owner")
        child, saved, declared = self._attempt(context, self._admission_index(context, operation_key))
        self._require(self._equal(form, saved) and self._equal(schema, declared), "admitted_form_conflict")
        values = self._validate_values(child, saved, declared)
        return list(dict.fromkeys(row["source_ref"] for rows in values.values() for row in rows))

    @staticmethod
    def _resolve(values, reference, namespace):
        if namespace in _IDENTIFIER_FIELDS:
            return any(row.get(_IDENTIFIER_FIELDS[namespace]) == reference and reference is not None
                for row in (*values.get("rfam_result_rows", []), *values.get("rfam_report_rows", [])))
        if any(row["source_ref"] == reference for rows in values.values() for row in rows):
            return True
        return None

    def resolve_own(self, context, reference, namespace):
        if namespace not in (*IDENTIFIER_NAMESPACES, "source", "execution_result", None):
            return None
        if context.role != "results":
            return False if namespace in IDENTIFIER_NAMESPACES else None
        values = form_validation_value((self, "own", _binding_key(context)), lambda: self._own_facts(context))
        if "rfam_report_rows" not in self._original_sources(context):
            values = {**values, "rfam_report_rows": []}
        return self._resolve(values, reference, namespace)

    def resolve_received(self, context, reference, namespace):
        if namespace not in (*IDENTIFIER_NAMESPACES, "source", "execution_result", None):
            return None
        if context.role not in {"annotation", "scientific_process"}:
            return False if namespace in IDENTIFIER_NAMESPACES else None
        return self._resolve(self._received_values(context), reference, namespace)


__all__ = ["RfamBatchReturns", "FACT_SOURCES", "IDENTIFIER_NAMESPACES",
    "rfam_fact_sources", "requested_sources"]
