"""Selected Rfam requests in the existing API episode.

Each invocation performs at most one requested HTTP operation. Native output
interpretation belongs to the separate numerical sheet and calculator modules;
receiving a response alone does not establish a valid scientific result.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import base64
from email import policy as email_policy
from email.parser import BytesParser
import hashlib
import json
import re

from .acquisition import SourceSnapshot
from .api_services import event, object_schema, validate_service_configuration, validate_value
from .execution_contracts import digest
from .rfam_batch_contracts import REQUEST_SCHEMA, SELECTOR_SCHEMA, validate_rfam_result_selector
from .rfam_discovery import BASE_URL, result_url, validate_result_url


EMPTY = object_schema({})
_NUCLEOTIDES = re.compile(r"[ACGTURYSWKMBDHVNacgturyswkmbdhvn]+")


def _json_object(content):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("rfam_json_duplicate_key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("rfam_json_invalid")

    try:
        value = json.loads(content.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=invalid_constant)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("rfam_json_invalid") from error
    if not isinstance(value, dict):
        raise ValueError("rfam_result_object_required")
    return value


class RfamBatchService:
    service = "rfam_batch"
    request_schema = REQUEST_SCHEMA
    selector_schema = SELECTOR_SCHEMA

    def __init__(self, tool_registry, configuration=None, *, client=None):
        self.configuration = validate_service_configuration(self.service, configuration or {})
        self.tools = tool_registry
        if client is None:
            from .rfam_batch_transport import RfamBatchHTTP
            timeout = self.configuration.get("timeout", getattr(tool_registry.clients, "timeout", None))
            client = RfamBatchHTTP(timeout_seconds=timeout)
        self.client = client

    def validate_request(self, request, scope):
        request = validate_value(request, self.request_schema, "rfam_request_invalid")
        if scope is not None:
            self._operand(request, scope)
        return request

    def _operand(self, request, scope):
        if request["mode"] == "single_sequence":
            return self._sequence_operand(request["subject_ref"], scope)
        queries = []
        for index, reference in enumerate(request["subject_refs"]):
            operand = self._sequence_operand(reference, scope)
            operand["query_occurrence_key"] = "rfam_query_" + digest({
                "original_occurrence": operand["query_occurrence_key"],
                "selected_occurrence_ordinal": index})
            queries.append({**operand, "selected_occurrence_ordinal": index,
                            "native_query_name": f"rfam_query_{index:08d}"})
        content = self._batch_bytes(queries)
        return {"filename": "sequences.fa", "header_transform": "generated_unique_headers",
            "submitted_file_sha256": hashlib.sha256(content).hexdigest(),
            "submitted_file_bytes": len(content), "queries": queries}

    @staticmethod
    def _batch_bytes(queries):
        return "".join(f'>{row["native_query_name"]}\n{row["submitted_sequence"]}\n'
                       for row in queries).encode("ascii")

    def _sequence_operand(self, reference, scope):
        row = self.tools._check_sequence_operand(reference, scope)
        if self.tools.store.subject_molecule(row["id"]) == "protein":
            raise ValueError("rfam_sequence_invalid")
        sequence = self.tools._sequence(row["id"], molecule_model="rna")
        if not isinstance(sequence, str) or _NUCLEOTIDES.fullmatch(sequence) is None:
            raise ValueError("rfam_sequence_invalid")
        sha = hashlib.sha256(sequence.encode("ascii")).hexdigest()
        kind = row["record_type"]
        original_ref = row.get("member_ref", row["id"])
        ordinal = row.get("source_ordinal") if kind == "read_subject" else None
        transform = ("feature_segments" if kind == "feature" else
                     "registered_view" if kind == "product" and row.get("mapping") else "unchanged")
        # References to the existing derivation records preserve their exact
        # mappings without creating an artifact during input validation.
        mapping_ref = row["id"] if transform != "unchanged" else None
        return {
            "query_occurrence_key": "rfam_query_" + digest({"subject_ref": row["id"],
                "original_input_ref": original_ref, "original_record_ordinal": ordinal,
                "submitted_sequence_sha256": sha}),
            "subject_ref": row["id"], "original_input_ref": original_ref,
            "original_record_ordinal": ordinal,
            # A parser-normalized title is not necessarily the original header.
            "original_header": None,
            "submitted_sequence": sequence, "submitted_sequence_sha256": sha,
            "submitted_length_nt": len(sequence), "input_to_submitted_transform": transform,
            "input_coordinate_mapping_ref": mapping_ref,
        }

    @staticmethod
    def _handle(handle):
        if not isinstance(handle, dict) or set(handle) != {"job_id", "result_url"}:
            raise ValueError("rfam_original_handle_required")
        validate_result_url(handle["result_url"], handle["job_id"])
        return deepcopy(handle)

    def _original_handle(self, handle, previous_events, *, required):
        candidates = [] if handle is None else [self._handle(handle)]
        for previous in previous_events:
            if previous.get("name") not in {"api.rfam.submit", "api.rfam.status", "api.rfam.fetch"}:
                continue
            native = previous.get("event", {}).get("native_handle")
            if native is not None:
                candidates.append(self._handle(native))
        if candidates and any(value != candidates[0] for value in candidates[1:]):
            raise ValueError("rfam_original_handle_conflict")
        if required and not candidates:
            raise ValueError("rfam_original_handle_required")
        return candidates[0] if candidates else None

    @staticmethod
    def _entry(operation, description, instructions):
        return {"name": "api.rfam." + operation, "description": description,
                "input_schema": deepcopy(EMPTY), "instructions": instructions}

    def capabilities(self):
        return [
            self._entry("prepare", "Validate the selected nucleotide input occurrences for Rfam without submitting them.",
                "Resolve exactly the assigned sequence or ordered selected members in scope. A batch retains "
                "every selection occurrence, including repeated subjects, with unique native query names. Preserve "
                "original input identities and coordinates. No HTTP request or RNA-family evidence is produced."),
            self._entry("submit", "Submit the assigned nucleotide input to Rfam once and retain its job handle.",
                "Use the assigned single sequence or exact selected batch and the fixed Rfam service. Preserve the exact submission and native "
                "job identifier. Submission establishes a usable handoff, not family matches; status and results "
                "are separate selected operations. An uncertain submission must be reconciled, not repeated."),
            self._entry("status", "Obtain one native status response for the original Rfam job.",
                "Observe only the original job. Preserve the native token and observation time. Unknown status "
                "or an expired handle does not establish a completed search with no matches. Decide separately "
                "whether to wait or request results; this operation neither polls nor fetches scientific output."),
        ]

    def launch_catalog(self, request):
        self.validate_request(request, None)
        return self.capabilities()

    def available_launch_catalog(self, request, previous_events):
        entries = self.launch_catalog(request)
        handle = self._original_handle(None, previous_events, required=False)
        return [entry for entry in entries if handle is not None or entry["name"] != "api.rfam.status"]

    def result_capabilities(self):
        return [self.capabilities()[2], self._entry("fetch",
            "Acquire the assigned Rfam JSON, table, or report once for the original job.",
            "Retain the complete chosen representation. JSON numerical interpretation requires the original "
            "job and query identities; an empty expired-job response is not a no-hit result. Preserve native "
            "bit scores, E-values, GC and coordinates with unavailable fields distinguished from zero. Return "
            "only the requested typed projection. For a batch, JSON lacks query attribution; the native "
            "cmscan table preserves names joined to the original submitted occurrences. Choosing a table "
            "requires an explicit result assignment. A v3 batch-report selection extracts the report's "
            "native measurements and sequence correspondence, preserving its model name separately from an "
            "unreported RF accession. Older report selections remain artifact-only. Full model length is "
            "not inferred from alignment endpoints.")]

    def result_catalog(self, request, selector):
        self.validate_request(request, None)
        selected = validate_rfam_result_selector(selector)
        if selected["version"] == "rfam_batch_result_selector_v3" and request["mode"] != "sequence_batch":
            raise ValueError("rfam_report_batch_request_required")
        return self.result_capabilities()

    def prepare(self, name, request, arguments, *, scope, previous_events, handle=None, selector=None):
        request = self.validate_request(request, scope)
        validate_value(arguments, EMPTY, "rfam_request_invalid")
        operation = name.removeprefix("api.rfam.")
        if name != "api.rfam." + operation or operation not in {"prepare", "submit", "status", "fetch"}:
            raise ValueError("rfam_request_invalid")
        if selector is not None:
            selector = validate_rfam_result_selector(selector)
            self.result_catalog(request, selector)
        if operation == "fetch" and selector is None:
            raise ValueError("rfam_projection_invalid")
        original = self._original_handle(handle, previous_events, required=operation in {"status", "fetch"})
        if operation == "submit" and original is not None:
            raise ValueError("rfam_original_submission_already_exists")
        operand = self._operand(request, scope)
        return {"operation": name, "mutates_remote": operation == "submit",
            "request": request, "native_operation": operation, "input_operand": operand,
            "native_handle": original if operation in {"status", "fetch"} else None,
            "representation": selector["representation"] if operation == "fetch" else None}

    def invoke(self, prepared):
        operation = prepared["native_operation"]
        if operation == "prepare":
            return None
        if operation == "submit":
            operand = prepared["input_operand"]
            if prepared["request"]["mode"] == "sequence_batch":
                snapshot = self.client.submit_file(self._batch_bytes(operand["queries"]),
                                                   filename=operand["filename"])
            else:
                snapshot = self.client.submit(operand["submitted_sequence"])
        elif operation == "status":
            snapshot = self.client.status(self._handle(prepared["native_handle"])["job_id"])
        elif operation == "fetch":
            snapshot = self.client.result(self._handle(prepared["native_handle"])["job_id"],
                                          representation=prepared["representation"])
        else:
            raise ValueError("rfam_request_invalid")
        if not isinstance(snapshot, SourceSnapshot):
            raise ValueError("rfam_response_unknown")
        existing = snapshot.request.get("input_operand")
        if existing is not None and existing != prepared["input_operand"]:
            raise ValueError("rfam_result_sequence_identity_conflict")
        return replace(snapshot, request={**snapshot.request,
                                          "input_operand": deepcopy(prepared["input_operand"])})

    @staticmethod
    def _submitted_bytes(snapshot, expected, filename, *, require_file_record=False):
        code = "rfam_result_sequence_identity_conflict"
        for name, value in (("file_sha256", hashlib.sha256(expected).hexdigest()),
                            ("file_bytes", len(expected)), ("filename", filename)):
            if (require_file_record or name in snapshot.request) and snapshot.request.get(name) != value:
                raise ValueError(code)
        if require_file_record or "file_base64" in snapshot.request:
            try:
                if base64.b64decode(snapshot.request["file_base64"], validate=True) != expected:
                    raise ValueError(code)
            except (ValueError, TypeError, KeyError) as error:
                raise ValueError(code) from error
        actual = snapshot.transport.get("request")
        if actual is None:
            return  # Controlled or historical envelopes can lack an HTTP wire capture.
        try:
            raw = base64.b64decode(actual["body_base64"], validate=True)
            headers = {key.lower(): value for key, value in actual["headers"].items()}
            if (actual["method"] != "POST" or actual["url"] != BASE_URL + "/submit-job"
                    or actual["body_sha256"] != hashlib.sha256(raw).hexdigest()
                    or actual.get("body_bytes", len(raw)) != len(raw)):
                raise ValueError(code)
            message = BytesParser(policy=email_policy.default).parsebytes(
                ("Content-Type: " + headers["content-type"] + "\r\nMIME-Version: 1.0\r\n\r\n").encode("ascii") + raw)
            parts = list(message.iter_parts())
            if (message.get_content_type() != "multipart/form-data" or message.defects or len(parts) != 1
                    or parts[0].defects or parts[0].get_content_disposition() != "form-data"
                    or parts[0].get_param("name", header="content-disposition") != "sequence_file"
                    or parts[0].get_filename() != filename or parts[0].get_payload(decode=True) != expected):
                raise ValueError(code)
        except (ValueError, TypeError, KeyError, UnicodeError) as error:
            raise ValueError(code) from error

    @staticmethod
    def _response_request(prepared, snapshot):
        if snapshot.service != "rfam_batch" or snapshot.request.get("action") != prepared["native_operation"]:
            raise ValueError("rfam_response_unknown")
        operand = prepared["input_operand"]
        if snapshot.request.get("input_operand") != operand:
            raise ValueError("rfam_result_sequence_identity_conflict")
        operation = prepared["native_operation"]
        if operation == "submit":
            if snapshot.url != BASE_URL + "/submit-job":
                raise ValueError("rfam_result_sequence_identity_conflict")
            if prepared["request"]["mode"] == "sequence_batch":
                expected = RfamBatchService._batch_bytes(operand["queries"])
                RfamBatchService._submitted_bytes(snapshot, expected, operand["filename"], require_file_record=True)
            elif (snapshot.request.get("sequence_sha256") != operand["submitted_sequence_sha256"]
                    or snapshot.request.get("sequence_length") != operand["submitted_length_nt"]):
                raise ValueError("rfam_result_sequence_identity_conflict")
            else:
                RfamBatchService._submitted_bytes(snapshot,
                    (operand["submitted_sequence"] + "\n").encode("ascii"), "sequence.seq")
        else:
            job_id = prepared["native_handle"]["job_id"]
            expected_url = (BASE_URL + "/status/" + job_id if operation == "status" else
                            result_url(job_id) + ("" if prepared["representation"] == "json" else
                                                  "/" + prepared["representation"]))
            if snapshot.request.get("job_id") != job_id or snapshot.url != expected_url:
                raise ValueError("rfam_result_job_identity_conflict")
            if operation == "fetch" and snapshot.request.get("representation") != prepared["representation"]:
                raise ValueError("rfam_response_unknown")

    def decode(self, prepared, snapshot):
        operation = prepared["native_operation"]
        facts = {"operation": operation, "native_status": None, "http_status": None,
            "body_complete": None, "representation": prepared["representation"],
            "query_length_nt": prepared["input_operand"].get("submitted_length_nt"),
            "reported_hit_count": None, "native_status_source": "none"}
        if operation == "prepare":
            if snapshot is not None:
                raise ValueError("rfam_response_unknown")
            return event("preparation", "completed", facts=facts)
        if not isinstance(snapshot, SourceSnapshot):
            raise ValueError("rfam_response_unknown")
        self._response_request(prepared, snapshot)
        status, complete = snapshot.transport.get("status"), snapshot.transport.get("body_complete")
        if type(status) is not int or not 100 <= status <= 599 or type(complete) is not bool:
            raise ValueError("rfam_response_unknown")
        facts.update(http_status=status, body_complete=complete)
        handle = prepared["native_handle"]
        kind = "job" if operation in {"submit", "status"} else "response"
        if not complete:
            return event(kind, "unknown", native_handle=handle, facts=facts,
                         result_available=operation == "fetch" and status == 200,
                         failure_code="rfam_response_body_incomplete")
        if 300 <= status <= 399:
            return event(kind, "unknown", native_handle=handle, facts=facts,
                         failure_code="rfam_redirect_not_followed")
        token = snapshot.content.decode("ascii", errors="replace").strip()
        if re.fullmatch(r"[A-Z][A-Z_]{0,63}", token):
            facts.update(native_status=token, native_status_source="body")
        if operation == "fetch" and status == 202 and token in {"PEND", "RUN"}:
            return event("job", "submitted" if token == "PEND" else "running",
                         native_handle=handle, facts=facts)
        if status != 200:
            return event(kind, "failed", native_handle=handle, facts=facts,
                         failure_code="rfam_http_error")
        if operation == "submit":
            body = _json_object(snapshot.content)
            handle = self._handle({"job_id": body.get("jobId"), "result_url": body.get("resultURL")})
            return event("job", "submitted", native_handle=handle, handoff_ready=True, facts=facts)
        if operation == "status":
            if token == "FINISHED":
                # The current Rfam endpoint returned this exact token for the
                # two retained successful single/batch native captures. It is
                # a job-state fact, not validation of any requested result.
                return event("job", "completed", native_handle=handle, facts=facts,
                             result_available=True)
            # Only source-qualified mappings belong here. An unrelated service's
            # SUCCESS token is not proof of this endpoint's terminal semantics.
            return event("job", "unknown", native_handle=handle, facts=facts,
                         failure_code="rfam_job_not_found" if token == "NOT_FOUND" else "rfam_status_unknown")
        # Availability is acquisition of this complete representation. The
        # publisher independently validates query/job attribution and the actual
        # requested scientific projection before practical completion is allowed.
        return event("response", "completed", native_handle=handle,
                     result_available=True, facts=facts)

    def publish(self, request, selector, snapshot, scope, operation_key, *,
                submission_snapshot=None, handle=None):
        prepared = self.prepare("api.rfam.fetch", request, {}, scope=scope,
                                previous_events=[], handle=handle, selector=selector)
        if not self.decode(prepared, snapshot)["result_available"]:
            raise ValueError("rfam_response_unknown")
        if not isinstance(submission_snapshot, SourceSnapshot):
            raise ValueError("rfam_original_handle_required")
        submitted = self.prepare("api.rfam.submit", request, {}, scope=scope, previous_events=[])
        submission = self.decode(submitted, submission_snapshot)
        if submission["native_handle"] != self._handle(handle) or not submission["handoff_ready"]:
            raise ValueError("rfam_original_handle_conflict")
        from .rfam_batch_publication import publish_rfam_batch_result
        return publish_rfam_batch_result(self.tools, request=request, selector=selector,
            snapshot=snapshot, scope=scope, operation_key=operation_key,
            submission_snapshot=submission_snapshot, handle=handle)

    def prepare_observation(self, request, handle, *, scope):
        return self.prepare("api.rfam.status", request, {}, scope=scope,
                            previous_events=[], handle=handle)


__all__ = ["RfamBatchService"]
