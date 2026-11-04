"""Original selected Addgene metadata at the existing typed-return boundary.

Live ownership uses the actual API acquisition and saved publication. Closed
ownership uses small bindings frozen beside the original form in runtime_forms;
it does not reopen native bytes or private publication artifacts. Only
facts_for_closure supplies those private bindings. Ordinary facts and contexts
contain the public DTO alone. This host creates no history, observations,
credit, acquisition, model calls or receipt grants.

Source delivery keeps EpisodeReceipts' existing dependency expansion: Addgene
Sources also convey their raw HTML/request Files. Selected sequence Files are
returned explicitly; this module introduces no new File privacy policy.
"""
from copy import deepcopy
import json
import re

from .addgene_sequence_facts import (FACT_SOURCE, ADDGENE_SEQUENCE_FACTS_SCHEMA,
    build_addgene_sequence_fact, validate_addgene_sequence_fact)
from .api_sequence_support import COLLECT
from .communication import ReportBoundaryError, plain
from .episode_receipts import (EpisodeReceipts, RECEIVED_REPORT_PREFIX_VERSION,
    _validate_report_prefix)
from .episode_return_records import EpisodeReturnRecords, _same
from .execution_contracts import digest
from .form_reference_validation import form_validation_value, _binding_key
from .sequence_support_publication import read_sequence_support_publication


OWN_BINDINGS = "_addgene_sequence_acquisition_bindings_v1"
CLOSURE_PREFIX = "_addgene_sequence_return_prefix_v1"
_RECEIVERS = frozenset(("annotation", "scientific_process"))
_BINDING_FIELDS = frozenset(("decision_index", "outcome_sha256", "source_sha256", "fact_sha256"))


def _boundary(code, field=None):
    return ReportBoundaryError("addgene_sequence_return_" + code,
        code="addgene_sequence_return_" + code, field=field)


def addgene_sequence_fact_sources():
    return {FACT_SOURCE: {"type": "array", "meaning":
        "Literal selected Addgene native metadata and sequence availability from the assigned original response; "
        "full/partial and verification categories are source labels, not target identity or scientific confidence. "
        "Authentication-required and unavailable records supply no sequence bases or inferred symbol counts.",
        "report_schema": deepcopy(ADDGENE_SEQUENCE_FACTS_SCHEMA)}}


def requested_addgene_fields(schema):
    schema = plain(schema)
    if not isinstance(schema, dict) or not isinstance(schema.get("properties", {}), dict):
        raise _boundary("original_schema_conflict")
    fields = {}
    for name, node in schema.get("properties", {}).items():
        if not isinstance(node, dict):
            continue
        source = node.get("x-source")
        if source == FACT_SOURCE:
            if not _same(node, ADDGENE_SEQUENCE_FACTS_SCHEMA):
                raise _boundary("original_schema_conflict", name)
            fields[name] = source
        elif isinstance(source, str) and source.startswith("execution_addgene_"):
            raise _boundary("original_schema_conflict", name)
    return fields


def _values(form, schema):
    result = None
    for name in requested_addgene_fields(schema):
        if not isinstance(form, dict) or type(form.get(name)) is not list:
            raise _boundary("selected_value_conflict", name)
        try:
            rows = [validate_addgene_sequence_fact(row) for row in form[name]]
        except (ValueError, TypeError, RecursionError) as error:
            raise _boundary("selected_value_conflict", name) from error
        if result is not None and not _same(result, rows):
            raise _boundary("selected_value_conflict", name)
        result = rows
    return [] if result is None else result


def _merge(groups):
    rows, seen = [], {}
    for group in groups:
        for row in group:
            key = (row["source_ref"], tuple(item["record_ordinal"] for item in row["selected_rows"]))
            if key in seen:
                if not _same(seen[key], row):
                    raise _boundary("selected_value_conflict")
            else:
                seen[key] = row
                rows.append(deepcopy(row))
    return rows


def _references(rows):
    return list(dict.fromkeys(reference for row in rows
        for reference in [row["source_ref"],
            *[item["sequence_file_ref"] for item in row["selected_rows"]]] if reference is not None))


class _ReceiptView(EpisodeReceipts):
    """Use the existing receipt reader without constructing or migrating tables."""
    def __init__(self, store, run_id):
        self.store, self.db, self.run_id = store, store.db, run_id


class AddgeneSequenceReturns(EpisodeReturnRecords):
    def __init__(self, api):
        super().__init__(api.store, api.run_id, failure_prefix="addgene_sequence_return_")
        self.api = api

    def _require(self, condition, code):
        if not condition:
            raise _boundary(code)

    def authenticate(self, context, *, allow_unsaved=False):
        super().authenticate(context, allow_unsaved=allow_unsaved)
        self._require(context.role == context.path[-1][0], "original_context_conflict")
        return context

    def validate_fields(self, context, schema):
        original = (plain(context.request).get("report_contract") or {}).get("measurements", {}).get("schema", {})
        selected, declared = requested_addgene_fields(schema), requested_addgene_fields(original)
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
        action, contract = json.loads(row["action"]), plain(child.request).get("report_contract")
        self._require(isinstance(contract, dict), "original_schema_conflict")
        if action.get("kind") == "tool":
            self._require(action.get("tool") == "process.revise" and child.role == "scientific_process",
                "original_context_conflict")
            return
        self._require(action.get("kind") in {"child", "episode_child", "job_child"}
            and _same(action.get("scope"), child.scope)
            and action.get("purpose") == contract["decision"], "original_schema_conflict")
        selected_schema = json.loads(action["schema_json"])
        declaration = plain(child.request)["message"].get("report_contract_declaration")
        if declaration is not None:
            from .episode_contract_information import validate_saved_fact_form
            selected_schema = validate_saved_fact_form(child_role=child.role,
                submitted_schema_json=action["schema_json"],
                expanded_schema=contract["measurements"]["schema"], declaration=declaration)
        self._require(_same(selected_schema, contract["measurements"]["schema"]), "original_schema_conflict")
        if action["kind"] in {"episode_child", "job_child"}:
            self._require(action.get("role") == child.role, "original_context_conflict")
        if child.role == "results":
            self._require(_same(action.get("assignment"), child.assignment), "original_context_conflict")

    def _attempt(self, context, index):
        child, form, schema = super()._attempt(context, index)
        self._commission(context, child)
        closed = self._closed(child)
        self._require(closed is not None and _same(closed["form"], form), "frozen_return_conflict")
        return child, form, schema

    def _actions(self, context):
        for row in self.db.execute("SELECT decision_index,action,result FROM runtime_actions "
                "WHERE run_id=? AND episode_id=? AND result IS NOT NULL ORDER BY decision_index",
                (self.run_id, context.episode_id)):
            action, outcome = json.loads(row["action"]), json.loads(row["result"])
            if action.get("kind") != "tool" or action.get("tool") != COLLECT:
                continue
            if outcome.get("status") not in {"completed", "partial"}:
                continue
            source_ref = (outcome.get("result") or {}).get("source_ref")
            self._require(isinstance(source_ref, str), "original_receipt_conflict")
            source = self.store.get(source_ref)
            if source.get("provider") == "addgene":
                yield row["decision_index"], action, outcome, source

    def _binding(self, context, index, action, outcome, source, fact):
        result = outcome.get("result") or {}
        receipt = result.get("acquisition_receipt") or {}
        key = f"{self.run_id}:{context.episode_id}:{index}"
        self._require(type(index) is int and index >= 0
            and _same(action, {"kind": "tool", "tool": COLLECT, "arguments": {}})
            and receipt.get("version") == "api_service_acquisition_v1"
            and receipt.get("run_id") == self.run_id and receipt.get("episode_id") == context.episode_id
            and receipt.get("operation_key") == key and receipt.get("name") == COLLECT
            and _same(receipt.get("arguments"), {})
            and receipt.get("assignment_sha256") == digest(context.assignment)
            and _same(receipt.get("selector"), context.assignment.get("selector"))
            and receipt.get("handoff_ref") == context.assignment.get("handoff_ref")
            and result.get("handoff_ref") == receipt.get("handoff_ref")
            and _same(receipt.get("record_refs"), outcome.get("record_refs"))
            and source.get("id") == receipt.get("source_ref") == fact["source_ref"]
            and fact["source_ref"] in outcome.get("record_refs", [])
            and source.get("record_type") == "source" and source.get("provider") == "addgene"
            and source.get("origin") == "external"
            and source.get("uri") == "https://www.addgene.org/" + fact["requested_id"] + "/sequences/"
            and source.get("artifact_ref") == "artifact_" + str(receipt.get("snapshot_sha256"))
            and _same([row["record_ordinal"] for row in fact["selected_rows"]],
                context.assignment.get("selector", {}).get("record_ordinals"))
            and isinstance(result.get("sequence_support_ref"), str)
            and re.fullmatch(r"artifact_[0-9a-f]{64}", result["sequence_support_ref"]) is not None,
            "original_receipt_conflict")
        return dict(decision_index=index,
            outcome_sha256=digest(outcome), source_sha256=digest(source), fact_sha256=digest(fact))

    def _own_live(self, context):
        rows, bindings = [], []
        for index, action, outcome, source in self._actions(context):
            key = f"{self.run_id}:{context.episode_id}:{index}"
            acquired = self.api.read_result(source["id"], context.scope,
                episode_id=context.episode_id, operation_key=key)
            request = acquired["service_request"]
            self._require(request.get("operation") == "get_plasmid_sequence"
                and request.get("provider") == "addgene"
                and acquired["source_ref"] == source["id"]
                and _same(acquired["publication_result"], outcome["result"]), "original_receipt_conflict")
            publication = read_sequence_support_publication(self.store, outcome["result"]["sequence_support_ref"])
            self._require(_same(publication["request"], request)
                and _same(publication["selector"], context.assignment["selector"]), "original_receipt_conflict")
            fact = build_addgene_sequence_fact(publication)
            bindings.append(self._binding(context, index, action, outcome, source, fact))
            rows.append(fact)
        return _merge([rows]), {"version": OWN_BINDINGS, "acquisitions": bindings}

    def _own_closed(self, context, closed, rows):
        witness = closed["facts"].get(OWN_BINDINGS)
        self._require(type(witness) is dict and set(witness) == {"version", "acquisitions"}
            and witness["version"] == OWN_BINDINGS and type(witness["acquisitions"]) is list,
            "frozen_acquisition_conflict")
        actions = {index: (action, outcome, source) for index, action, outcome, source in self._actions(context)}
        by_hash = {digest(row): row for row in rows}
        expected, indices = [], []
        for binding in witness["acquisitions"]:
            self._require(type(binding) is dict and set(binding) == _BINDING_FIELDS
                and type(binding["decision_index"]) is int and binding["decision_index"] in actions
                and binding["fact_sha256"] in by_hash, "frozen_acquisition_conflict")
            index = binding["decision_index"]
            fact = by_hash[binding["fact_sha256"]]
            self._require(_same(binding, self._binding(context, index, *actions[index], fact)),
                "frozen_acquisition_conflict")
            indices.append(index)
            expected.append(fact)
        self._require(indices == list(actions) and _same(_merge([expected]), rows), "frozen_acquisition_conflict")
        return deepcopy(witness)

    def _own(self, context, schema):
        self.authenticate(context, allow_unsaved=True)
        closed = self._closed(context)
        if closed is None:
            return self._own_live(context)
        rows = _values(closed["form"], schema)
        self._require(_same(rows, closed["facts"].get(FACT_SOURCE)), "frozen_return_conflict")
        return rows, self._own_closed(context, closed, rows)

    @staticmethod
    def _attempt_witness(row):
        return {**{key: row[key] for key in ("decision_index", "delivery_ref", "child_episode_id")},
            "contract_sha256": digest(json.loads(row["contract"])), "form_sha256": digest(json.loads(row["form"]))}

    def _received(self, context, *, allowed=None, seen=None):
        self.authenticate(context, allow_unsaved=True)
        self._require(context.role in _RECEIVERS, "original_context_conflict")
        seen = set() if seen is None else set(seen)
        self._require(context.episode_id not in seen, "frozen_return_conflict")
        seen.add(context.episode_id)
        groups, direct, current, prefix = [], [], context, allowed
        lineage = set()
        while True:
            self._require(current.episode_id not in lineage, "frozen_prefix_conflict")
            lineage.add(current.episode_id)
            attempts = list(self.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? "
                "AND failure IS NULL AND form IS NOT NULL ORDER BY decision_index", (self.run_id, current.episode_id)))
            if prefix is not None:
                actual = {row["decision_index"]: self._attempt_witness(row) for row in attempts}
                self._require(all(_same(saved, actual.get(saved["decision_index"])) for saved in prefix),
                    "frozen_prefix_conflict")
            for attempt in attempts:
                witness = self._attempt_witness(attempt)
                if prefix is not None and not any(_same(witness, item) for item in prefix):
                    continue
                schema = json.loads(attempt["contract"])["measurements"]["schema"]
                if not requested_addgene_fields(schema):
                    continue
                child, form, schema = self._attempt(current, attempt["decision_index"])
                rows = self._verified(child, schema, seen=seen)
                self._require(_same(rows, _values(form, schema)), "frozen_return_conflict")
                groups.append(rows)
                if current.episode_id == context.episode_id:
                    direct.append(witness)
            manifest = EpisodeReceipts.read_manifest(self.db, self.run_id, current.episode_id)
            self._require(_same(plain(current.request)["message"].get("knowledge_inheritance"), manifest),
                "frozen_prefix_conflict")
            if manifest["parent_episode_id"] is None:
                self._require(len(current.path) == 1, "frozen_prefix_conflict")
                break
            self._require("received_report_prefix" in manifest, "frozen_prefix_conflict")
            parent = self.context(manifest["parent_episode_id"])
            self._commission(parent, current)
            current, prefix = parent, manifest["received_report_prefix"]["attempts"]
        rows = _merge(groups)
        known = set(_ReceiptView(self.store, self.run_id).known(context.episode_id))
        self._require(set(_references(rows)) <= known, "received_reference_ungranted")
        return rows, {"version": RECEIVED_REPORT_PREFIX_VERSION, "attempts": direct}

    def _verified(self, context, schema, *, seen=None):
        self.validate_fields(context, schema)
        if context.role == "results":
            return self._own(context, schema)[0]
        closed = self._closed(context)
        allowed = None
        if closed is not None:
            self._require(CLOSURE_PREFIX in closed["facts"], "frozen_prefix_conflict")
            allowed = _validate_report_prefix(closed["facts"][CLOSURE_PREFIX])["attempts"]
        rows, _ = self._received(context, allowed=allowed, seen=seen)
        if closed is not None:
            self._require(_same(rows, _values(closed["form"], schema))
                and _same(rows, closed["facts"].get(FACT_SOURCE)), "frozen_return_conflict")
        return rows

    def facts(self, context, schema):
        if not self.validate_fields(context, schema):
            return {}
        return {FACT_SOURCE: self._verified(context, schema)}

    def facts_for_closure(self, context, schema):
        """Closure-only facts for runtime_forms; never a model-facing context."""
        if not self.validate_fields(context, schema):
            return {}
        if context.role == "results":
            rows, bindings = self._own(context, schema)
            return {FACT_SOURCE: rows, OWN_BINDINGS: bindings}
        rows = self._verified(context, schema)
        closed = self._closed(context)
        if closed is None:
            _, prefix = self._received(context)
        else:
            prefix = _validate_report_prefix(closed["facts"][CLOSURE_PREFIX])
        return {FACT_SOURCE: rows, CLOSURE_PREFIX: deepcopy(prefix)}

    def received_facts(self, context, schema):
        return self.facts(context, schema)

    def received_context(self, context):
        closed = self._closed(context)
        if closed is not None and CLOSURE_PREFIX in closed["facts"]:
            schema = (plain(context.request).get("report_contract") or {}).get("measurements", {}).get("schema", {})
            return {FACT_SOURCE: self._verified(context, schema)}
        return {FACT_SOURCE: self._received(context)[0]}

    def validate_report(self, context, form, schema):
        if not self.validate_fields(context, schema):
            return
        rows = _values(form, schema)
        expected = form_validation_value(("addgene_sequence_return", _binding_key(context), digest(schema)),
            lambda: self.facts(context, schema))
        self._require(_same(rows, expected[FACT_SOURCE]), "selected_value_conflict")

    validate_received_report = validate_report

    def record_admission(self, context, form, schema, operation_key):
        if not requested_addgene_fields(schema):
            return []
        self._require(context.role in _RECEIVERS, "original_context_conflict")
        child, saved, declared = self._attempt(context, self._admission_index(context, operation_key))
        self._require(_same(form, saved) and _same(schema, declared), "original_schema_conflict")
        rows = self._verified(child, declared)
        self._require(_same(rows, _values(saved, declared)), "selected_value_conflict")
        return _references(rows)

    def _grant_kind(self, context, reference):
        """Classify the original forward grant; this does not authenticate it.

        Ordinary/legacy references need no Addgene state. A matching rich grant
        still takes the complete commission, prefix and custody path below.
        """
        tables = {row[0] for row in self.db.execute("SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('runtime_receipt_inheritance','runtime_record_receipts','runtime_report_attempts')")}
        if not {"runtime_receipt_inheritance", "runtime_record_receipts"} <= tables:
            return None
        current, through, seen = context.episode_id, None, set()
        while current is not None and current not in seen:
            seen.add(current)
            manifest = self.db.execute("SELECT parent_episode_id,through_receipt_index FROM runtime_receipt_inheritance "
                "WHERE run_id=? AND episode_id=?", (self.run_id, current)).fetchone()
            if manifest is None:
                return None
            receipt = self.db.execute("SELECT receipt_index,receipt_kind,source_index FROM runtime_record_receipts "
                "WHERE run_id=? AND episode_id=? AND record_ref=?", (self.run_id, current, reference)).fetchone()
            if receipt is not None and (through is None or receipt["receipt_index"] <= through):
                if receipt["receipt_kind"] not in {"child_form", "report_redelivery"} or type(receipt["source_index"]) is not int:
                    return "ordinary"
                if "runtime_report_attempts" not in tables:
                    return "ordinary"
                attempt = self.db.execute("SELECT contract,form FROM runtime_report_attempts WHERE run_id=? "
                    "AND parent_episode_id=? AND decision_index=? AND failure IS NULL AND form IS NOT NULL",
                    (self.run_id, current, receipt["source_index"])).fetchone()
                if attempt is None:
                    return "ordinary"
                contract, form = json.loads(attempt["contract"]), json.loads(attempt["form"])
                for name, node in contract.get("measurements", {}).get("schema", {}).get("properties", {}).items():
                    if not isinstance(node, dict) or node.get("x-source") != FACT_SOURCE:
                        continue
                    rows = form.get(name)
                    if type(rows) is not list:
                        continue
                    for row in rows:
                        if type(row) is not dict:
                            continue
                        if row.get("source_ref") == reference:
                            return "rich"
                        selected = row.get("selected_rows")
                        if type(selected) is list and any(type(item) is dict and item.get("sequence_file_ref") == reference
                                for item in selected):
                            return "rich"
                return "ordinary"
            current, through = manifest["parent_episode_id"], manifest["through_receipt_index"]
        return None

    def _resolve(self, context, reference, namespace, *, received):
        if not isinstance(reference, str) or not reference.startswith(("source_", "artifact_")):
            return None
        if namespace not in {None, "source", "execution_result", "artifact"}:
            return None
        if context.role not in _RECEIVERS | {"results"}:
            return None
        source = reference.startswith("source_")
        if source:
            try:
                record = self.store.get(reference)
            except (ValueError, KeyError):
                return None
            if record.get("provider") != "addgene":
                return None
        schema = (plain(context.request).get("report_contract") or {}).get("measurements", {}).get("schema", {})
        own = context.role == "results" and not received
        if own:
            if not requested_addgene_fields(schema):
                return None
        else:
            grant = self._grant_kind(context, reference)
            if grant != "rich":
                if source and grant is None and requested_addgene_fields(schema):
                    self.authenticate(context, allow_unsaved=True)
                    return False
                return None
        self.authenticate(context, allow_unsaved=True)
        if received:
            rows = form_validation_value(("addgene_sequence_received", _binding_key(context)),
                lambda: self.received_context(context))[FACT_SOURCE]
        else:
            rows = form_validation_value(("addgene_sequence_return", _binding_key(context), digest(schema)),
                lambda: self.facts(context, schema))[FACT_SOURCE]
        if reference in {row["source_ref"] for row in rows}:
            return namespace in {None, "source", "execution_result"}
        if reference in set(_references(rows)):
            return namespace in {None, "artifact"}
        return False if source else None

    def resolve_own(self, context, reference, namespace):
        return self._resolve(context, reference, namespace, received=context.role != "results")

    def resolve_received(self, context, reference, namespace):
        return self._resolve(context, reference, namespace, received=context.role != "results")


__all__ = ["AddgeneSequenceReturns", "addgene_sequence_fact_sources", "requested_addgene_fields",
    "OWN_BINDINGS", "CLOSURE_PREFIX"]
