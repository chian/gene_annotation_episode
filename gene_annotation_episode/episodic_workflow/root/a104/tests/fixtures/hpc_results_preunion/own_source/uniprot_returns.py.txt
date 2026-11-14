"""Selected UniProt facts through original episode forms and existing receipts.

Native projection is owned by uniprot_return_projection. This module authenticates
its actual acquisition and copies already delivered cells across immediate-child
boundaries. It creates no acquisition, publication, action or credit record.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

from jsonschema import Draft202012Validator

from .communication import ReportBoundaryError, plain
from .domain import identity
from .episode_receipts import EpisodeReceipts, RECEIVED_REPORT_PREFIX_VERSION, _validate_report_prefix
from .episode_return_records import EpisodeReturnRecords, _same
from .execution_contracts import canonical, digest
from .practical_execution_state import _read
from .uniprot_native_contracts import PUBLICATION_SCHEMA
from .uniprot_return_contracts import (
    UniProtReturnValidationError, requested_uniprot_selection,
    validate_uniprot_return_selection, validate_uniprot_selected_values,
)
from .uniprot_return_projection import project_uniprot_page


SOURCE = "uniprot_selected_returns"
VERSION = "uniprot_selected_returns_v1"
_CLOSURE_PREFIX = "uniprot_received_report_prefix_v1"
_RECEIVERS = {"annotation", "scientific_process"}


def _failure(code, pi, ri=None, fi=None, pointer=None):
    return {"code": code, "page_selection_index": pi, "record_selection_index": ri,
            "field_selection_index": fi, "native_pointer": pointer}


def _reindex(value, pi, ri=None, fi=None):
    """Copy a saved cell, changing only the request positions of its failures."""
    result = deepcopy(value)
    def visit(node):
        if isinstance(node, dict):
            if set(node) == {"code", "page_selection_index", "record_selection_index",
                             "field_selection_index", "native_pointer"}:
                node.update(page_selection_index=pi, record_selection_index=ri,
                            field_selection_index=fi)
            else:
                for child in node.values():
                    visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)
    visit(result)
    return result


def _cell(candidates, requested, pi, ri, fi):
    matches = [cell for cell in candidates if _same(cell["request"], requested)]
    if not matches:
        return {"request_index": fi, "request": deepcopy(requested), "status": "unavailable",
                "value": None, "failures": [_failure("field_not_received", pi, ri, fi)]}
    cells = [_reindex(cell, pi, ri, fi) for cell in matches]
    for cell in cells:
        cell["request_index"] = fi
    if not all(_same(cells[0], cell) for cell in cells):
        raise ValueError("uniprot_selected_value_conflict")
    return cells[0]


def _selected_value(form, schema):
    selection = requested_uniprot_selection(schema)
    if selection is None:
        return None, None
    name = next(name for name, node in schema["properties"].items() if node.get("x-source") == SOURCE)
    value = deepcopy(form[name])
    validate_uniprot_selected_values(value, selection=selection)
    return selection, value


def select_received_uniprot_pages(received: list[dict], *, selection: dict) -> dict:
    """Copy exact selected cells from authenticated forms, never inspect sources.

    ``received`` is transient and supplied in actual successful-attempt order by
    UniProtReturns. Different collection filters or windows are intentionally not
    synthesized from old cells, even when a caller could infer a narrower value.
    """
    selection = validate_uniprot_return_selection(selection)
    if any(page["publication"]["mode"] != "received_publication" for page in selection["pages"]):
        raise ValueError("uniprot_selection_mode_conflict")
    delivered = []
    for wrapper in received:
        if type(wrapper) is not dict or set(wrapper) != {"form", "schema", "attempt"}:
            raise ValueError("uniprot_original_receipt_conflict")
        original, value = _selected_value(wrapper["form"], wrapper["schema"])
        if value is not None:
            delivered.extend((page, original["pages"][page["page_selection_index"]]) for page in value["pages"])
    result = {"version": VERSION, "pages": [], "failures": []}
    for pi, requested in enumerate(selection["pages"]):
        wanted = requested["publication"]
        candidates = [(page, declared) for page, declared in delivered
                      if page["witness"]["source_id"] == wanted["source_id"] and
                      page["witness"]["publication_sha256"] == wanted["publication_sha256"]]
        if not candidates:
            result["failures"].append(_failure("publication_not_received", pi))
            continue
        original = candidates[0][0]
        page = {"page_selection_index": pi, "witness": deepcopy(original["witness"]),
                "status": deepcopy(original["status"]), "page_fields": [], "records": [],
                "issues": deepcopy(original["issues"]), "source_grant_status": "not_requested",
                "source_grant": None, "failures": []}
        invariant = set(page["status"]) - {"requested_record_count", "returned_bound_record_count",
            "record_selection_count", "indeterminate_record_count", "unselected_issue_count"}
        for other, _ in candidates:
            if (not _same(other["witness"], page["witness"]) or
                    not _same(other["issues"], page["issues"]) or
                    any(not _same(other["status"][key], page["status"][key]) for key in invariant)):
                raise ValueError("uniprot_selected_value_conflict")
        for fi, field in enumerate(requested["page_fields"]):
            page["page_fields"].append(_cell([cell for old, _ in candidates for cell in old["page_fields"]],
                                           field, pi, None, fi))
        for ri, clause in enumerate(requested["records"]):
            matches, clause_failures, matched_clause = [], [], False
            for old, declared in candidates:
                for old_ri, old_clause in enumerate(declared["records"]):
                    exact = _same(clause["record"], old_clause["record"])
                    if exact:
                        matched_clause = True
                        clause_failures.extend(_reindex(f, pi, ri) for f in old["failures"]
                                               if f["record_selection_index"] == old_ri)
                    matches.extend(row for row in old["records"]
                                   if row["record_selection_index"] == old_ri and (exact or
                                      clause["record"]["mode"] == "ordinal" and
                                      row["requested_record_ordinal"] == clause["record"]["ordinal"]))
            if not matches and not matched_clause:
                page["failures"].append(_failure("field_not_received", pi, ri))
                continue
            for failure in clause_failures:
                if failure not in page["failures"]:
                    page["failures"].append(failure)
            for ordinal in sorted({row["requested_record_ordinal"] for row in matches}):
                rows = [row for row in matches if row["requested_record_ordinal"] == ordinal]
                row = deepcopy(rows[0])
                if any(not _same(row["witness"], other["witness"]) or row["state"] != other["state"]
                       or not _same(row["issues"], other["issues"]) for other in rows):
                    raise ValueError("uniprot_selected_owner_conflict")
                row["record_selection_index"] = ri
                # Retain row-state failures; grant failure belongs only to a requested grant.
                row["failures"] = [_reindex(f, pi, ri) for f in row["failures"]
                                   if f["code"] not in {"sequence_unavailable", "sequence_artifact_not_received"}]
                row["fields"] = [_cell([cell for old in rows for cell in old["fields"]], field, pi, ri, fi)
                                 for fi, field in enumerate(clause["fields"])]
                grants = [old["sequence_grant"] for old in rows if old["sequence_grant_status"] == "available"]
                row.update(sequence_grant_status="not_requested", sequence_grant=None)
                if clause["grant_sequence_artifact"]:
                    row["sequence_grant_status"] = "available" if grants else "unavailable"
                    if grants:
                        if not all(_same(grants[0], grant) for grant in grants):
                            raise ValueError("uniprot_binding_conflict")
                        row["sequence_grant"] = deepcopy(grants[0])
                    else:
                        row["failures"].append(_failure("sequence_artifact_not_received", pi, ri))
                page["records"].append(row)
        grants = [old["source_grant"] for old, _ in candidates if old["source_grant_status"] == "available"]
        if requested["grant_source"]:
            page["source_grant_status"] = "available" if grants else "unavailable"
            if grants:
                if not all(_same(grants[0], grant) for grant in grants):
                    raise ValueError("uniprot_binding_conflict")
                page["source_grant"] = deepcopy(grants[0])
            else:
                page["failures"].append(_failure("source_not_received", pi))
        ordinals = {row["requested_record_ordinal"] for row in page["records"]}
        def issue_keys(rows):
            return {canonical(issue) for row in rows for issue in row["issues"]}
        total_issues = original["status"]["unselected_issue_count"] + len(issue_keys(original["records"]))
        page["status"].update(record_selection_count=len(requested["records"]),
            requested_record_count=len(ordinals),
            returned_bound_record_count=len({row["requested_record_ordinal"] for row in page["records"]
                                            if row["state"] == "bound"}),
            indeterminate_record_count=len({row["requested_record_ordinal"] for row in page["records"]
                if any(f["code"] == "record_selection_indeterminate" for f in row["failures"])}),
            unselected_issue_count=total_issues - len(issue_keys(page["records"])))
        result["pages"].append(page)
    validate_uniprot_selected_values(result, selection=selection)
    return result


class UniProtReturns(EpisodeReturnRecords):
    def __init__(self, api):
        super().__init__(api.store, api.run_id, failure_prefix="uniprot_")
        self.api = api

    def _require(self, condition, code, field=None):
        if not condition:
            declared = {"original_context_conflict", "original_receipt_conflict", "source_snapshot_conflict",
                "publication_digest_conflict", "binding_conflict", "artifact_content_conflict",
                "original_schema_conflict", "selected_owner_conflict", "selected_value_conflict",
                "frozen_prefix_conflict", "selection_mode_conflict"}
            if code not in declared:
                code = ("original_schema_conflict" if "schema" in code else
                        "frozen_prefix_conflict" if "frozen" in code or "prefix" in code else
                        "original_context_conflict" if "context" in code else "original_receipt_conflict")
            raise ReportBoundaryError("uniprot_" + code, code="uniprot_" + code, field=field)

    @staticmethod
    def _boundary(error, fallback, field=None):
        if isinstance(error, ReportBoundaryError):
            return error
        code = getattr(error, "code", str(error))
        if code == "artifact_digest_mismatch":
            code = "uniprot_artifact_content_conflict"
        elif code == "api_result_original_response_conflict":
            code = "uniprot_source_snapshot_conflict"
        if not code.startswith("uniprot_"):
            code = "uniprot_" + fallback
        return ReportBoundaryError(code, code=code, field=getattr(error, "field", field))

    def authenticate(self, context, *, allow_unsaved=False):
        super().authenticate(context, allow_unsaved=allow_unsaved)
        self._require(context.role == context.path[-1][0], "original_context_conflict")
        return context

    def _selection(self, context, schema):
        try:
            selected = requested_uniprot_selection(plain(schema))
            if selected is None:
                return None
            original = (plain(context.request).get("report_contract") or {}).get("measurements", {}).get("schema", {})
            self._require(_same(selected, requested_uniprot_selection(original)), "original_schema_conflict")
            self._require(context.role in _RECEIVERS | {"results"}, "selection_mode_conflict")
            mode = "assigned_page" if context.role == "results" else "received_publication"
            field = next(name for name, node in plain(schema)["properties"].items() if node.get("x-source") == SOURCE)
            for index, page in enumerate(selected["pages"]):
                self._require(page["publication"]["mode"] == mode, "selection_mode_conflict",
                    f"properties.{field}.x-uniprot-selection.pages[{index}].publication.mode")
            return selected
        except UniProtReturnValidationError as error:
            raise self._boundary(error, "original_schema_conflict") from error

    def _commission(self, parent, child, *, construction=False):
        self._require(child.path[:-1] == parent.path, "original_context_conflict")
        self.store.validate_scope(plain(child.scope), parent_scope=plain(parent.scope))
        slot = child.path[-1][1]
        self._require(re.fullmatch(r"child_(0|[1-9][0-9]*)", slot) is not None, "original_context_conflict")
        selected = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
            (self.run_id, parent.episode_id, int(slot[6:]))).fetchone()
        if selected is None and construction:
            saved = self.db.execute("SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                (self.run_id, child.episode_id)).fetchone()
            self._require(saved is None, "original_context_conflict")
            return
        self._require(selected is not None, "original_context_conflict")
        selected = json.loads(selected["action"])
        original = plain(child.request).get("report_contract")
        self._require(isinstance(original, dict), "original_schema_conflict")
        if selected.get("kind") == "tool":
            self._require(selected.get("tool") == "process.revise" and child.role == "scientific_process",
                          "original_context_conflict")
            return
        self._require(selected.get("kind") in {"child", "episode_child", "job_child"}
            and _same(selected.get("scope"), child.scope)
            and _same(json.loads(selected["schema_json"]), original["measurements"]["schema"])
            and selected.get("purpose") == original["decision"], "original_schema_conflict")
        if selected["kind"] in {"episode_child", "job_child"}:
            self._require(selected.get("role") == child.role, "original_context_conflict")
        if child.role == "results":
            self._require(_same(selected.get("assignment"), child.assignment), "original_context_conflict")

    def _attempt(self, context, index):
        child, form, schema = super()._attempt(context, index)
        self._commission(context, child)
        original = plain(child.request)["report_contract"]["measurements"]["schema"]
        self._require(_same(schema, original), "original_schema_conflict")
        frozen = self._closed(child)
        self._require(frozen is not None and _same(frozen["form"], form), "frozen_prefix_conflict")
        return child, form, schema

    def _closed(self, context):
        row = self.db.execute("SELECT facts,form FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone()
        if row is None or row["form"] is None:
            return None
        return {"facts": json.loads(row["facts"]), "form": json.loads(row["form"])}

    def _successful_closed(self, context):
        """Prove the exact saved form has an original successful parent attempt."""
        closed = self._closed(context)
        if closed is None or SOURCE not in closed["facts"]:
            return False
        rows = self.db.execute("SELECT parent_episode_id,decision_index FROM runtime_report_attempts "
            "WHERE run_id=? AND child_episode_id=? AND form IS NOT NULL AND failure IS NULL ORDER BY decision_index",
            (self.run_id, context.episode_id)).fetchall()
        for row in rows:
            self._attempt(self.context(row["parent_episode_id"]), row["decision_index"])
        return bool(rows)

    def _source(self, reference):
        source = self.store.get(reference)
        payload = {key: value for key, value in source.items() if key not in {"id", "record_type", "origin"}}
        self._require(source.get("record_type") == "source" and source.get("provider") == "uniprot"
            and source.get("origin") == "external"
            and reference == identity("source", {"origin": "external", "record": payload}), "source_snapshot_conflict")
        return source

    def read_own(self, reference: str, *, context, operation_key: str | None = None,
                 verify_artifacts: bool = True) -> dict:
        self.authenticate(context, allow_unsaved=True)
        self._require(context.role == "results", "original_context_conflict")
        if not verify_artifacts:
            self._require(self._successful_closed(context), "frozen_prefix_conflict")
        try:
            body = self.api.read_result(reference, context.scope, episode_id=context.episode_id,
                                       operation_key=operation_key, verify_artifacts=verify_artifacts)
        except (ValueError, KeyError) as error:
            raise self._boundary(error, "original_receipt_conflict") from error
        self._require(body.get("version") == "api_service_acquired_result_v1"
            and body["target"]["assignment"].get("service") == "uniprot"
            and _same(body["scope"], context.scope) and _same(body["assignment"], context.assignment),
            "original_context_conflict")
        result = body["publication_result"]
        receipt = result["acquisition_receipt"]
        key = receipt["operation_key"]
        self._require(operation_key is None or operation_key == key, "original_receipt_conflict")
        self._require(receipt["name"] == "api.uniprot.collect" and receipt["arguments"] == {},
                      "original_receipt_conflict")
        directory = self.api._episode_directory(context.episode_id) / "actions" / digest(key)
        metadata = _read(directory / "snapshot.json")
        intent, outcome = _read(directory / "intent.json"), _read(directory / "outcome.json")
        self._require(_same(outcome.get("result"), result) and outcome.get("status") == body["status"],
                      "original_receipt_conflict")
        service = self.api.services[body["target"]["resource_id"]]
        prepared = service.prepare("api.uniprot.collect", body["service_request"], {}, scope=body["scope"],
            previous_events=[], selector=body["assignment"]["selector"])
        self._require(_same(intent["prepared"], prepared), "original_context_conflict")
        self._require(metadata["service"] == "uniprot", "source_snapshot_conflict")
        source = self._source(body["source_ref"])
        self._require(source["artifact_ref"] == metadata["content_ref"] == "artifact_" + body["snapshot_sha256"]
            and source["uri"] == metadata["url"] and source["retrieved_at"] == metadata["retrieved_at"],
            "source_snapshot_conflict")
        self._require(_same(self.api._artifact_json(source["request_ref"]),
            {"request": metadata["request"], "transport": metadata["transport"]}), "source_snapshot_conflict")
        saved = self.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (key + ":publication",)).fetchone()
        operands = {"arguments": prepared["native_arguments"], "snapshot_sha256": body["snapshot_sha256"],
                    "request": metadata["request"], "transport": metadata["transport"]}
        self._require(saved is not None and saved["name"] == "internal.api_service.public.uniprot." + prepared["native_operation"]
            and _same(json.loads(saved["arguments"]), operands) and _same(json.loads(saved["scope"]), body["scope"]),
            "original_receipt_conflict")
        original = json.loads(saved["result"])
        expected = deepcopy(original)
        expected["operation_ref"] = identity("api_operation", {"key": key})
        expected["result"].update(acquisition_receipt=receipt, handoff_ref=body["target"]["handle"])
        self._require(_same(outcome, expected), "original_receipt_conflict")
        publication = result.get("uniprot_publication")
        if publication is None:
            return body
        self._require(next(Draft202012Validator(PUBLICATION_SCHEMA).iter_errors(publication), None) is None,
                      "publication_digest_conflict")
        self._require(publication["source_ref"] == source["id"] and publication["native_artifact_ref"] == source["artifact_ref"]
            and publication["content_sha256"] == body["snapshot_sha256"]
            and _same(publication["page"]["effective_request"],
                {"operation": prepared["native_operation"], **prepared["native_arguments"]}), "source_snapshot_conflict")
        self._require(type(result.get("count")) is int and result["count"] == len(publication["records"]), "binding_conflict")
        stored_records, ordinals = [], set()
        for bound in publication["records"]:
            anchor, native = bound["anchor"], bound["record"]
            ordinal = anchor["record_ordinal"]
            pointer = "" if publication["page"]["operation"] == "record" else "/results/" + str(ordinal)
            self._require(ordinal not in ordinals and anchor["source_ref"] == source["id"]
                and anchor["record_pointer"] == native["identity"]["record_pointer"] == pointer
                and ordinal == native["identity"]["record_ordinal"]
                and anchor["primary_accession"] == native["identity"]["primary_accession"], "binding_conflict")
            ordinals.add(ordinal)
            record = self.store.get(anchor["reference_ref"])
            payload = {key: value for key, value in record.items() if key not in {"id", "record_type", "origin"}}
            sequence = native["sequence"]
            content = sequence["value"]["value"].encode("ascii") if sequence["value"]["state"] == "present" else None
            expected_ref = None if content is None else "artifact_" + hashlib.sha256(content).hexdigest()
            self._require(record["record_type"] == "reference" and record["origin"] == "external"
                and record["reference_type"] == record["molecule"] == "protein"
                and record["id"] == identity("reference", {"origin": "external", "record": payload})
                and record["source_ref"] == source["id"] and record["accession"] == anchor["primary_accession"]
                and record["sequence_ref"] == bound["sequence_ref"] == expected_ref
                and record["length"] == sequence["observed_length_aa"]
                and record["id"] in body["record_refs"], "binding_conflict")
            stored_records.append(record)
        self._require(_same(stored_records, result.get("records")), "binding_conflict")
        return body

    def _acquisitions(self, context, *, verify_artifacts):
        for directory, outcome in self.api._own_outcomes(context):
            result = outcome.get("result") or {}
            receipt = result.get("acquisition_receipt")
            if outcome.get("status") not in {"completed", "partial"} or receipt is None:
                continue
            self._require(receipt["operation_key"] == _read(directory / "intent.json")["operation_key"],
                          "original_receipt_conflict")
            body = self.read_own(result["source_ref"], context=context,
                operation_key=receipt["operation_key"], verify_artifacts=verify_artifacts)
            self._require(_same(body["publication_result"], result), "original_receipt_conflict")
            yield body

    def _own_value(self, context, selection):
        value, seen = {"version": VERSION, "pages": [], "failures": []}, set()
        acquisitions = list(self._acquisitions(context, verify_artifacts=True)) if selection["pages"] else []
        for pi, selected in enumerate(selection["pages"]):
            if not acquisitions:
                value["failures"].append(_failure("not_acquired", pi))
            for body in acquisitions:
                result = body["publication_result"]
                publication = result.get("uniprot_publication")
                if publication is None:
                    failure = _failure("publication_unavailable", pi)
                    if failure not in value["failures"]:
                        value["failures"].append(failure)
                    continue
                witness = (publication["source_ref"], digest(publication))
                if witness in seen:
                    continue
                seen.add(witness)
                # Read only requested sequence material. The native publication
                # already authenticates every sequence artifact relationship.
                sequences = {}
                for clause in selected["records"]:
                    if not clause["grant_sequence_artifact"] and not any(f["kind"] == "sequence_window" for f in clause["fields"]):
                        continue
                    selector = clause["record"]
                    for bound in publication["records"]:
                        anchor = bound["anchor"]
                        if selector["mode"] == "ordinal" and anchor["record_ordinal"] != selector["ordinal"]:
                            continue
                        if selector["mode"] == "primary_accession" and anchor["primary_accession"] != selector["accession"]:
                            continue
                        if bound["sequence_ref"] is not None:
                            try:
                                sequences[bound["sequence_ref"]] = self.store.get_artifact(bound["sequence_ref"])
                            except FileNotFoundError:
                                # A newly requested unavailable artifact is an
                                # unavailable cell; present conflicting bytes
                                # remain an integrity error, never a zero value.
                                pass
                            except ValueError as error:
                                raise self._boundary(error, "artifact_content_conflict") from error
                try:
                    page = project_uniprot_page(publication,
                        native_content=self.store.get_artifact(publication["native_artifact_ref"]),
                        outer_status=body["status"], bound_record_count=result["count"],
                        projection_errors=result.get("projection_errors", []),
                        projection_qualifications=result.get("projection_qualifications", []),
                        page_selection=selected, page_selection_index=pi, sequence_contents=sequences)
                except ValueError as error:
                    raise self._boundary(error, "selected_value_conflict") from error
                value["pages"].append(page)
        validate_uniprot_selected_values(value, selection=selection)
        return value

    def _frozen_value(self, context, schema):
        closed = self._closed(context)
        if closed is None:
            return None
        selection, value = _selected_value(closed["form"], plain(schema))
        self._require(selection is not None and _same(closed["facts"].get(SOURCE), value), "frozen_prefix_conflict")
        return value

    def _verify_saved_own(self, context, value):
        """Authenticate saved witnesses without reprojecting historical fields."""
        original = plain(context.request)["report_contract"]["measurements"]["schema"]
        selection = self._selection(context, original)
        bodies = list(self._acquisitions(context, verify_artifacts=False)) if selection["pages"] else []
        publications = {(body["source_ref"], digest(body["publication_result"]["uniprot_publication"])): body
                        for body in bodies if body["publication_result"].get("uniprot_publication") is not None}
        self._require({(page["witness"]["source_id"], page["witness"]["publication_sha256"])
                       for page in value["pages"]} == set(publications), "publication_digest_conflict")
        for failure in value["failures"]:
            if failure["code"] == "not_acquired":
                self._require(not bodies, "original_receipt_conflict")
            elif failure["code"] == "publication_unavailable":
                self._require(any(body["publication_result"].get("uniprot_publication") is None for body in bodies),
                              "original_receipt_conflict")
        for page in value["pages"]:
            witness = page["witness"]
            body = publications.get((witness["source_id"], witness["publication_sha256"]))
            self._require(body is not None, "publication_digest_conflict")
            publication = body["publication_result"]["uniprot_publication"]
            self._require(witness["native_artifact_id"] == publication["native_artifact_ref"]
                and witness["content_sha256"] == publication["content_sha256"]
                and page["status"]["outer_acquisition_status"] == body["status"]
                and page["status"]["bound_record_count"] == body["publication_result"]["count"], "binding_conflict")
            rows = {row["anchor"]["record_ordinal"]: row for row in publication["records"]}
            for record in page["records"]:
                if record["witness"] is None:
                    continue
                bound = rows.get(record["requested_record_ordinal"])
                self._require(bound is not None, "binding_conflict")
                expected = {"record_id": bound["anchor"]["reference_ref"],
                    "record_ordinal": bound["anchor"]["record_ordinal"], "record_pointer": bound["anchor"]["record_pointer"],
                    "accession_relation": bound["record"]["identity"]["accession_relation"],
                    "sequence_artifact_id": bound["sequence_ref"]}
                self._require(_same(record["witness"], expected), "binding_conflict")

    @staticmethod
    def _witness(attempt):
        return {**{key: attempt[key] for key in ("decision_index", "delivery_ref", "child_episode_id")},
            "contract_sha256": digest(json.loads(attempt["contract"])), "form_sha256": digest(json.loads(attempt["form"]))}

    def _prefix(self, context):
        closed = self._closed(context)
        self._require(closed is not None and _CLOSURE_PREFIX in closed["facts"], "frozen_prefix_conflict")
        try:
            return _validate_report_prefix(closed["facts"][_CLOSURE_PREFIX])
        except ValueError as error:
            raise self._boundary(error, "frozen_prefix_conflict") from error

    def _historical(self, context, form, schema):
        self.authenticate(context)
        selection = self._selection(context, schema)
        _, value = _selected_value(plain(form), plain(schema))
        self._require(_same(value, self._frozen_value(context, schema)), "frozen_prefix_conflict")
        if context.role == "results":
            self._verify_saved_own(context, value)
        else:
            received = self._received(context, allowed=self._prefix(context)["attempts"])
            expected = select_received_uniprot_pages(received, selection=selection)
            self._require(_same(value, expected), "selected_value_conflict")
        return value

    def _received(self, context, *, allowed=None):
        self.authenticate(context, allow_unsaved=True)
        self._require(context.role in _RECEIVERS, "original_context_conflict")
        attempts = self.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? "
            "AND form IS NOT NULL AND failure IS NULL ORDER BY decision_index", (self.run_id, context.episode_id)).fetchall()
        if allowed is not None:
            actual = {row["decision_index"]: self._witness(row) for row in attempts}
            self._require(all(_same(saved, actual.get(saved["decision_index"])) for saved in allowed),
                          "frozen_prefix_conflict")
        received = []
        for attempt in attempts:
            witness = self._witness(attempt)
            if allowed is not None and not any(_same(witness, saved) for saved in allowed):
                continue
            schema = json.loads(attempt["contract"]).get("measurements", {}).get("schema", {})
            if requested_uniprot_selection(schema) is None:
                continue
            child, form, schema = self._attempt(context, attempt["decision_index"])
            self._historical(child, form, schema)
            received.append({"form": form, "schema": schema, "attempt": witness})
        return received

    def facts(self, context, schema):
        selection = self._selection(context, schema)
        if selection is None:
            return {}
        self.authenticate(context, allow_unsaved=True)
        if context.role != "results":
            return self.received_facts(context, schema)
        frozen = self._frozen_value(context, schema)
        if frozen is not None and self._successful_closed(context):
            self._verify_saved_own(context, frozen)
            return {SOURCE: frozen}
        return {SOURCE: self._own_value(context, selection)}

    def received_facts(self, context, schema):
        return {key: value for key, value in self.facts_for_closure(context, schema).items() if key == SOURCE}

    def facts_for_closure(self, context, schema):
        selection = self._selection(context, schema)
        if selection is None:
            return {}
        if context.role == "results":
            return self.facts(context, schema)
        with self.store.read_snapshot():
            frozen = self._frozen_value(context, schema)
            prefix = self._prefix(context) if frozen is not None else None
            received = self._received(context, allowed=None if prefix is None else prefix["attempts"])
            value = select_received_uniprot_pages(received, selection=selection)
            if frozen is not None:
                self._require(_same(value, frozen), "frozen_prefix_conflict")
            else:
                prefix = {"version": RECEIVED_REPORT_PREFIX_VERSION,
                          "attempts": [row["attempt"] for row in received]}
            return {SOURCE: value, _CLOSURE_PREFIX: deepcopy(prefix)}

    def validate_received_report(self, context, form, schema):
        # Build validates the initial interpretation form before dispatch. Its
        # recorded fields are absent, but the original requested mode must still
        # fit this episode before a tool action can be selected.
        original = (plain(context.request).get("report_contract") or {}).get("measurements", {}).get("schema", {})
        self._selection(context, original)
        selection = self._selection(context, schema)
        if selection is None:
            return
        self.authenticate(context, allow_unsaved=True)
        try:
            _, value = _selected_value(plain(form), plain(schema))
            expected = self.facts(context, schema)[SOURCE]
            self._require(_same(value, expected), "selected_value_conflict")
            frozen = self._frozen_value(context, schema)
            self._require(frozen is None or _same(frozen, value), "frozen_prefix_conflict")
        except UniProtReturnValidationError as error:
            raise self._boundary(error, "selected_value_conflict") from error

    @staticmethod
    def _grants(value):
        result = []
        for page in value["pages"]:
            if page["source_grant"] is not None:
                result.append(page["source_grant"]["source_ref"])
            result.extend(row["sequence_grant"]["artifact_ref"] for row in page["records"]
                          if row["sequence_grant"] is not None)
        return list(dict.fromkeys(result))

    def record_admission(self, context, form, schema, operation_key):
        if requested_uniprot_selection(plain(schema)) is None:
            return []
        self._require(context.role in _RECEIVERS, "original_context_conflict")
        child, saved, declared = self._attempt(context, self._admission_index(context, operation_key))
        self._require(_same(form, saved) and _same(schema, declared), "original_schema_conflict")
        return self._grants(self._historical(child, saved, declared))

    def _material_closure(self, references):
        pending, known = list(references), set()
        while pending:
            ref = pending.pop()
            if ref not in known:
                known.add(ref)
                pending.extend(self.store._refs(self.store.get(ref)))
        return known

    def _independent_references(self, context, wrappers):
        references = set()
        # Preserve initial/inherited and earlier own-action receipts. Historical
        # reference-only forms remain meaningful even beside a selected field.
        try:
            receipts = EpisodeReceipts(self.store, self.run_id)
            references.update(receipts.known(context.episode_id))
        except ValueError:
            pass
        def walk(value, node):
            if isinstance(value, str) and node.get("format") == "reference":
                references.add(value)
            elif isinstance(value, dict):
                for key, field in node.get("properties", {}).items():
                    if key in value:
                        walk(value[key], field)
            elif isinstance(value, list):
                for item in value:
                    walk(item, node.get("items", {}))
        for wrapper in wrappers:
            for name, node in wrapper["schema"]["properties"].items():
                if node.get("x-source") != SOURCE:
                    walk(wrapper["form"][name], node)
        return self._material_closure(references)

    def _resolve(self, context, reference, namespace, wrappers):
        if namespace not in {None, "source", "artifact", "reference", "execution_result"}:
            return None
        material, witnessed = [], set()
        for wrapper in wrappers:
            _, value = _selected_value(wrapper["form"], wrapper["schema"])
            material.extend(self._grants(value))
            for page in value["pages"]:
                witnessed.update((page["witness"]["source_id"], page["witness"]["native_artifact_id"]))
                for row in page["records"]:
                    if row["witness"] is not None:
                        witnessed.update((row["witness"]["record_id"], row["witness"]["sequence_artifact_id"]))
        if reference not in witnessed and reference not in material:
            return None
        allowed = self._material_closure(material) | self._independent_references(context, wrappers)
        if reference not in allowed:
            return False
        kind = self.store.get(reference)["record_type"]
        return namespace in {None, kind} or namespace == "execution_result" and kind in {"source", "reference"}

    def resolve_own(self, context, reference, namespace):
        if context.role != "results" or namespace not in {None, "source", "artifact", "reference", "execution_result"}:
            return None
        schema = (plain(context.request).get("report_contract") or {}).get("measurements", {}).get("schema", {})
        if requested_uniprot_selection(schema) is None:
            return None
        self.authenticate(context, allow_unsaved=True)
        # Own acquired material has its original receipt authority regardless
        # of which fields the parent asked this owner to return.
        for body in self._acquisitions(context, verify_artifacts=not self._successful_closed(context)):
            if reference in self._material_closure(body["record_refs"]):
                kind = self.store.get(reference)["record_type"]
                return namespace in {None, kind} or namespace == "execution_result" and kind in {"source", "reference"}
        return None

    def resolve_received(self, context, reference, namespace):
        if context.role not in _RECEIVERS or namespace not in {None, "source", "artifact", "reference", "execution_result"}:
            return None
        frozen = self._closed(context)
        allowed = self._prefix(context)["attempts"] if frozen is not None and _CLOSURE_PREFIX in frozen["facts"] else None
        return self._resolve(context, reference, namespace, self._received(context, allowed=allowed))

    def _grant_origins(self, context, descriptor, *, allowed=None):
        origins = []
        for wrapper in self._received(context, allowed=allowed):
            _, value = _selected_value(wrapper["form"], wrapper["schema"])
            if not any(_same(row["sequence_grant"], descriptor) for page in value["pages"] for row in page["records"]):
                continue
            child = self.context(wrapper["attempt"]["child_episode_id"])
            if child.role == "results":
                origins.append(child.episode_id)
            else:
                # Follow that exact closed form downward; do not walk the
                # child's inherited parent grants back up into this traversal.
                origins.extend(self._grant_origins(child, descriptor, allowed=self._prefix(child)["attempts"]))
        return origins

    def authenticate_sequence_artifact(self, context, descriptor: dict) -> tuple[str, ...]:
        """Authenticate a supplied grant through frozen inheritance; do not read bytes."""
        self.authenticate(context, allow_unsaved=True)
        current, allowed, origins, visited = context, None, [], set()
        while True:
            self._require(current.episode_id not in visited, "frozen_prefix_conflict")
            visited.add(current.episode_id)
            if current.role in _RECEIVERS:
                origins.extend(self._grant_origins(current, descriptor, allowed=allowed))
            manifest = EpisodeReceipts.read_manifest(self.db, self.run_id, current.episode_id)
            self._require(_same(plain(current.request)["message"].get("knowledge_inheritance"), manifest),
                          "frozen_prefix_conflict")
            parent_id = manifest["parent_episode_id"]
            if parent_id is None:
                self._require(len(current.path) == 1, "frozen_prefix_conflict")
                break
            self._require("received_report_prefix" in manifest, "frozen_prefix_conflict")
            parent = self.context(parent_id)
            self._commission(parent, current, construction=current is context)
            current, allowed = parent, manifest["received_report_prefix"]["attempts"]
        receipts = EpisodeReceipts(self.store, self.run_id)
        self._require(bool(origins) and descriptor.get("artifact_ref") in receipts.known(context.episode_id),
                      "original_receipt_conflict")
        return tuple(dict.fromkeys(origins))


__all__ = ["UniProtReturns", "project_uniprot_page", "select_received_uniprot_pages"]
