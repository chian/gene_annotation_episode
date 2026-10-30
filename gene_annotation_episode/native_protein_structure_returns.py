"""Original protein results and actual, frozen typed-delivery authority.

This adapter reads existing actions, forms and semantic receipts. It neither
executes science nor derives permissions by walking source auxiliaries. The
result host authenticates original publications; the separate operand adapter
validates the retained scientific bytes. No successful verdict is cached.
"""
from __future__ import annotations

from copy import deepcopy
from functools import wraps
import json
import re
from typing import Literal

from .alignment_site_native import immutable_record
from .communication import ReportBoundaryError, plain, validate_form
from .domain import identity
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .episode_contract_information import expand_fact_form, validate_saved_fact_form
from .execution_contracts import canonical, digest
from .protein_structure_authority import (
    ProteinFactGroups, ProteinResultAuthorityRecord, ProteinStructureOperandError,
)
from .protein_structure_contracts import (
    issue, validate_alignment_descriptor, validate_declared_transform_record,
    validate_saved_sheet_descriptor, validate_structure_sequence_descriptor,
)
from .protein_structure_result_views import (
    protein_structure_fact_sources, validate_protein_structure_failure_return,
    validate_protein_structure_projection_result,
)
from .scientific_process_records import (
    scientific_digest, scientific_invocation_ref, selector_selection, validate_filled_process,
)

PROJECTION_SOURCE = "execution_protein_structure_projections"
SAVED_SOURCE = "execution_protein_structure_saved_sheets"
SEQUENCE_SOURCE = "execution_protein_structure_sequences"
FAILURE_SOURCE = "execution_protein_structure_failures"
FACT_SOURCES = (PROJECTION_SOURCE, SAVED_SOURCE, SEQUENCE_SOURCE, FAILURE_SOURCE)
GENERIC_SOURCE = "execution_result_refs"
SequenceUse = Literal["sequence_align", "structure_correspondence"]
SavedSheetUse = Literal["recalculate", "select_projection", "use_transform"]
_ASSIGNED_ROLES = {"launch", "launch_api", "launch_local", "launch_hpc", "results",
                   "job_launch", "job_results"}
_VALIDATORS = {
    PROJECTION_SOURCE: validate_protein_structure_projection_result,
    SAVED_SOURCE: validate_saved_sheet_descriptor,
    SEQUENCE_SOURCE: validate_structure_sequence_descriptor,
    FAILURE_SOURCE: validate_protein_structure_failure_return,
}


def _error(code="original_commission_mismatch", *, field="receipt", stage="authority"):
    return ProteinStructureOperandError(issue(code, stage=stage, field=field))


def _boundary(function):
    """Do not expose unrelated implementation error strings as science codes."""
    @wraps(function)
    def call(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except ProteinStructureOperandError:
            raise
        except (ValueError, KeyError, TypeError, IndexError, OverflowError) as error:
            raise _error() from error
    return call


def _validate(function, value):
    try:
        return function(plain(value))
    except (ValueError, KeyError, TypeError, OverflowError) as error:
        raise _error("invalid_schema", field="descriptor") from error


def requested_sources(schema: dict) -> tuple[str, ...]:
    selected = {node.get("x-source") for node in plain(schema).get("properties", {}).values()
                if isinstance(node, dict)}
    return tuple(source for source in FACT_SOURCES if source in selected)


def _custody_refs(custody):
    return [custody[key] for key in ("handoff_ref", "source_ref", "bundle_artifact_ref")]


def _sequence_refs(descriptor):
    return [descriptor["reference_ref"],
            *(descriptor[key]["artifact_ref"] for key in
              ("sequence_file", "residue_map_file", "structure_file")),
            *_custody_refs(descriptor["custody"])]


def _saved_refs(descriptor):
    return [*_custody_refs(descriptor["custody"]), descriptor["sheet_file"]["artifact_ref"],
            descriptor["original_components_file"]["artifact_ref"]]


def _sequences(values):
    """Only explicit values cells contain delivered embedded descriptors."""
    for source in FACT_SOURCES:
        for value in values.get(source, []):
            if source == SEQUENCE_SOURCE:
                yield value
            elif source == PROJECTION_SOURCE and value["family"] == "extracted_sequence" \
                    and value["delivery"]["kind"] == "values":
                for row in value["delivery"]["rows"]:
                    for selected in row["values"]:
                        if selected["field"] == "descriptor" and selected["value"] is not None:
                            yield selected["value"]


def _references(values):
    references = [ref for descriptor in _sequences(values) for ref in _sequence_refs(descriptor)]
    references.extend(ref for value in values.get(SAVED_SOURCE, []) for ref in _saved_refs(value))
    references.extend(value["delivery"]["table_file"]["artifact_ref"]
                      for value in values.get(PROJECTION_SOURCE, [])
                      if value["delivery"]["kind"] == "artifact")
    return list(dict.fromkeys(references))


class NativeProteinStructureReturns(EpisodeReturnRecords):
    def __init__(self, owner):
        super().__init__(owner.store, owner.run_id, failure_prefix="protein_return_")
        self.owner = owner
        self.results = owner.native_protein_structure_results

    def _require(self, condition, code=None):
        if not condition:
            raise _error()

    def _manifest(self, context):
        manifest = EpisodeReceipts.read_manifest(self.db, self.run_id, context.episode_id)
        self._require(self._equal(plain(context.request)["message"].get("knowledge_inheritance"), manifest))
        return manifest

    def _commission(self, child, parent, *, unsaved=False):
        self._require(tuple(map(tuple, child.path[:-1])) == tuple(map(tuple, parent.path)))
        self.store.validate_scope(plain(child.scope), parent_scope=plain(parent.scope))
        slot = child.path[-1][1]
        self._require(isinstance(slot, str) and re.fullmatch(r"child_(0|[1-9][0-9]*)", slot))
        index = int(slot[6:])
        row = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND decision_index=?", (self.run_id, parent.episode_id, index)).fetchone()
        if row is None and unsaved:
            return index  # Construction only; authenticate checked no work/form.
        self._require(row is not None)
        action, request = json.loads(row["action"]), plain(child.request)
        contract = request.get("report_contract")
        self._require(isinstance(contract, dict) and action.get("kind") in {"child", "episode_child", "job_child"})
        self._require(self._equal(action.get("scope"), child.scope)
            and action.get("purpose") == contract["decision"]
            and action.get("goal") == request["goal"]["objective"]
            and self._equal(json.loads(action["initial_report_json"]), request["message"]["initial_report"]))
        declaration = request["message"].get("report_contract_declaration")
        if declaration is None:
            self._require(self._equal(json.loads(action["schema_json"]), contract["measurements"]["schema"]))
        else:
            validate_saved_fact_form(child_role=child.role, submitted_schema_json=action["schema_json"],
                expanded_schema=contract["measurements"]["schema"], declaration=declaration)
        if action["kind"] in {"episode_child", "job_child"}:
            self._require(action.get("role") == child.role)
            assignment = plain(child.assignment)
            if child.role == "scientific_process" and "selection" in assignment:
                # Only the existing instruction selectors are materialized.
                # Every other selected assignment field stays exact.
                selected = {**assignment, "selection": selector_selection(assignment["selection"])}
                self._require(self._equal(action.get("assignment", {}), assignment)
                    or self._equal(action.get("assignment", {}), selected))
                filled = validate_filled_process(request["message"]["scientific_process"])
                invocation = {"objective": request["goal"]["objective"], "scope": plain(child.scope),
                    "purpose": contract["decision"], "report_schema": contract["measurements"]["schema"],
                    "initial_report": request["message"]["initial_report"]}
                self._require(self._equal(filled["selection"], assignment["selection"])
                    and filled["assignment_sha256"] == scientific_digest(assignment)
                    and filled["invocation_sha256"] == scientific_digest(invocation)
                    and request["message"].get("scientific_invocation_ref") == scientific_invocation_ref(self.run_id, child.path))
            else:
                self._require(self._equal(action.get("assignment", {}), assignment))
        return index

    @_boundary
    def authenticate(self, context, *, allow_unsaved=False):
        super().authenticate(context, allow_unsaved=allow_unsaved)
        self._require(context.role == context.path[-1][0])
        saved = self.db.execute("SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone()
        manifest = self._manifest(context)
        parent_id = manifest["parent_episode_id"]
        if saved is None:
            self._require(allow_unsaved and parent_id is not None)
            work = self.db.execute("SELECT 1 FROM runtime_actions WHERE run_id=? AND episode_id=? "
                "UNION ALL SELECT 1 FROM runtime_forms WHERE run_id=? AND episode_id=? LIMIT 1",
                (self.run_id, context.episode_id, self.run_id, context.episode_id)).fetchone()
            self._require(work is None)
        # Check ancestry iteratively, including each original commission. Calling
        # self.context here would recursively authenticate the same ancestors.
        current, seen = context, {context.episode_id}
        while parent_id is not None:
            self._require(parent_id not in seen)
            seen.add(parent_id)
            parent = self._saved_context(parent_id)
            self._commission(current, parent, unsaved=saved is None and current is context)
            current = parent
            parent_id = self._manifest(current)["parent_episode_id"]
        self._require(len(current.path) == 1)
        return context

    def _saved_context(self, episode_id):
        from .episode_bindings import BindingContext
        row = self.db.execute("SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (self.run_id, episode_id)).fetchone()
        self._require(row is not None)
        path, request = json.loads(row["path"]), json.loads(row["request"])
        message = request["message"]
        context = BindingContext(self.run_id, episode_id, path[-1][0], tuple(map(tuple, path)),
            message["scope"], message.get("episode_assignment", {}), request)
        super().authenticate(context)
        return context

    def _levels(self, context):
        """Yield each exact received prefix, never an inferred old NULL prefix."""
        self.authenticate(context, allow_unsaved=True)
        current, allowed, before = context, None, None
        while True:
            yield current, allowed, before, current is not context or context.role not in _ASSIGNED_ROLES
            manifest = self._manifest(current)
            if manifest["parent_episode_id"] is None:
                return
            self._require("received_report_prefix" in manifest)
            allowed = manifest["received_report_prefix"]["attempts"]
            before = int(current.path[-1][1][6:])
            current = self._saved_context(manifest["parent_episode_id"])

    def _known(self, context):
        receipts = EpisodeReceipts(self.store, self.run_id)
        return set(receipts.known(context.episode_id, baseline=context.role in _ASSIGNED_ROLES))

    def _attempts_at(self, context, allowed, before, enabled):
        if not enabled:
            return
        rows = self.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? "
            "AND form IS NOT NULL AND failure IS NULL ORDER BY decision_index",
            (self.run_id, context.episode_id))
        for row in rows:
            if before is not None and row["decision_index"] >= before:
                continue
            if allowed is not None:
                witness = {key: row[key] for key in ("decision_index", "delivery_ref", "child_episode_id")}
                witness.update(contract_sha256=digest(json.loads(row["contract"])),
                               form_sha256=digest(json.loads(row["form"])))
                if not any(self._equal(witness, old) for old in allowed):
                    continue
            yield row

    def _attempt(self, context, index):
        self.authenticate(context)
        row = self.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? "
            "AND decision_index=?", (self.run_id, context.episode_id, index)).fetchone()
        self._require(row is not None and row["form"] is not None and row["failure"] is None)
        child = self.context(row["child_episode_id"])
        self._require(child.path[:-1] == context.path)
        self._commission(child, context)
        contract, form = json.loads(row["contract"]), json.loads(row["form"])
        schema = contract["measurements"]["schema"]
        action = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
            (self.run_id, context.episode_id, index)).fetchone()
        decision = self.db.execute("SELECT purpose,request,response FROM runtime_model_calls WHERE run_id=? "
            "AND episode_id=? AND call_index=?", (self.run_id, context.episode_id, index)).fetchone()
        selected = json.loads(action["action"]) if action is not None else \
            json.loads(decision["response"]).get("selection", {}) if decision is not None and decision["response"] is not None else {}
        original_contract = plain(child.request)["report_contract"]
        compact_redelivery = selected.get("kind") == "redeliver_report" \
            and not self._equal(json.loads(selected["schema_json"]), schema)
        if not compact_redelivery:
            # Preserve the shared recorded-return proof. Its older raw-schema
            # comparison cannot represent compact redelivery; only that path
            # is reproduced below using its frozen contract-information record.
            super()._attempt(context, index)
        if selected.get("kind") == "redeliver_report":
            self._require(selected.get("delivery_ref") == row["delivery_ref"]
                and selected.get("purpose") == contract["decision"])
            if compact_redelivery:
                self._redelivery_schema(child, selected, schema, decision)
            earlier = self.db.execute("SELECT child_episode_id,contract FROM runtime_report_attempts WHERE run_id=? "
                "AND parent_episode_id=? AND delivery_ref=? AND decision_index<? ORDER BY decision_index LIMIT 1",
                (self.run_id, context.episode_id, row["delivery_ref"], index)).fetchone()
            self._require(earlier is not None and earlier["child_episode_id"] == child.episode_id
                and self._equal(json.loads(earlier["contract"]), original_contract))
        else:
            self._require(child.path[-1][1] == "child_" + str(index)
                and selected.get("kind") in {"child", "episode_child", "job_child"}
                and self._equal(contract, original_contract))
        frozen = self.db.execute("SELECT form,facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, child.episode_id)).fetchone()
        self._require(frozen is not None)
        facts = json.loads(frozen["facts"])
        for name, node in schema.get("properties", {}).items():
            source = node.get("x-source")
            if source is not None:
                self._require(source in facts and name in form and self._equal(form[name], facts[source]))
            elif selected.get("kind") == "redeliver_report":
                # Runtime redelivery can select only already frozen original
                # interpretations under their unchanged field contracts.
                self._require(name in facts.get("interpretations", {}) and name in form
                    and self._equal(node, original_contract["measurements"]["schema"].get("properties", {}).get(name))
                    and self._equal(form[name], facts["interpretations"][name]))
        if self._equal(schema, original_contract["measurements"]["schema"]):
            self._require(frozen is not None and frozen["form"] is not None
                          and self._equal(json.loads(frozen["form"]), form))
        return child, form, schema

    def _redelivery_schema(self, child, selected, schema, decision):
        """Reproduce this recorded decision's expansion, never today's catalog."""
        from .composition_information import CONTRACT_INFORMATION_PROFILE
        self._require(decision is not None and decision["purpose"] == "decision")
        saved = json.loads(decision["request"])
        info, context = saved["contract_information"], saved["context"]
        keys = {"version", "permitted_child_roles", "fact_sources_by_role", "fact_sources_sha256",
                "catalog_sha256", "action_schema_sha256", "exchange_schema", "instructions"}
        self._require(type(info) is dict and set(info) == keys
            and info["version"] == context.get("contract_information_profile") == CONTRACT_INFORMATION_PROFILE
            and info["fact_sources_sha256"] == digest(info["fact_sources_by_role"])
            and info["catalog_sha256"] == digest(context.get("tools", []))
            and info["action_schema_sha256"] == digest(saved["schema"])
            and type(info["instructions"]) is str
            and type(info["permitted_child_roles"]) is list
            and type(info["fact_sources_by_role"]) is dict
            and set(info["permitted_child_roles"]) == set(info["fact_sources_by_role"]))
        expanded = expand_fact_form(selected["schema_json"], child_role=child.role,
            facts_by_role=info["fact_sources_by_role"], permitted_child_roles=info["permitted_child_roles"])
        validate_saved_fact_form(child_role=child.role, submitted_schema_json=selected["schema_json"],
            expanded_schema=schema, declaration=expanded["declaration"])

    def _values(self, form, schema):
        """Validate the actual enclosing parent form and exact registered facts."""
        form, schema = plain(form), plain(schema)
        definitions = protein_structure_fact_sources()
        values = {}
        if type(form) is not dict or type(schema) is not dict:
            raise _error("invalid_schema", field="descriptor")
        for name, node in schema.get("properties", {}).items():
            if type(node) is not dict:
                raise _error("invalid_schema", field="descriptor")
            source = node.get("x-source")
            if source not in FACT_SOURCES:
                if isinstance(source, str) and source.startswith("execution_protein_structure_"):
                    raise _error("invalid_schema", field="descriptor")
                continue
            expected = {**definitions[source]["report_schema"], "x-source": source}
            if not self._equal(node, expected):
                raise _error("invalid_schema", field="descriptor")
            rows = form.get(name)
            if type(rows) is not list:
                raise _error("invalid_schema", field="descriptor")
            rows = [_validate(_VALIDATORS[source], row) for row in rows]
            self._require(source not in values or self._equal(values[source], rows))
            values[source] = rows
        try:
            validate_form(form, schema, lambda *_: True)
        except ReportBoundaryError as error:
            raise _error("invalid_schema", field="descriptor") from error
        return {source: values[source] for source in FACT_SOURCES if source in values}

    def _frozen(self, context, values):
        row = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone()
        if row is not None:
            facts = json.loads(row["facts"])
            self._require(all(source in facts and self._equal(facts[source], value)
                              for source, value in values.items()))

    def _own(self, context, *, verify_artifacts=False):
        self.authenticate(context, allow_unsaved=True)
        self._require(context.role == "results")
        groups = self.results.own_fact_groups(context, verify_artifacts=verify_artifacts)
        self._require(type(groups) is dict and set(groups) == set(FACT_SOURCES))
        return {source: [_validate(_VALIDATORS[source], row) for row in groups[source]] for source in FACT_SOURCES}

    def _historical(self, context, form, schema, *, verify_artifacts=False, active=()):
        self.authenticate(context)
        marker = (context.episode_id, digest(schema), digest(form))
        self._require(marker not in active)
        values = self._values(form, schema)
        self._frozen(context, values)
        if context.role == "results":
            own = self._own(context, verify_artifacts=verify_artifacts)
            self._require(all(self._equal(rows, own[source]) for source, rows in values.items()))
        else:
            received = self._received(context, verify_artifacts=verify_artifacts, active=(*active, marker))
            self._require(all(all(any(self._equal(row, original) for original in received[source])
                                  for row in rows) for source, rows in values.items()))
        return values

    def _deliveries(self, context, *, verify_artifacts=False, active=()):
        known, seen = self._known(context), {}
        # Inherited reports were already known before this episode's own later
        # deliveries. Preserve that order across different source keys too.
        for current, allowed, before, enabled in reversed(list(self._levels(context))):
            for attempt in self._attempts_at(current, allowed, before, enabled):
                schema = json.loads(attempt["contract"])["measurements"]["schema"]
                if not requested_sources(schema):
                    continue
                child, form, schema = self._attempt(current, attempt["decision_index"])
                values = self._historical(child, form, schema, verify_artifacts=verify_artifacts, active=active)
                for source, rows in values.items():
                    for row in rows:
                        # Exact typed delivery and frozen semantic operands are
                        # independent conditions. Old recursive receipts alone
                        # never create a row or descriptor.
                        if not set(_references({source: [row]})) <= known:
                            continue
                        key = canonical(row)
                        if key not in seen.setdefault(source, set()):
                            seen[source].add(key)
                            yield source, deepcopy(row)

    def _received(self, context, *, verify_artifacts=False, active=()):
        groups = {source: [] for source in FACT_SOURCES}
        for source, row in self._deliveries(context, verify_artifacts=verify_artifacts, active=active):
            groups[source].append(row)
        return groups

    @_boundary
    def received_context(self, context) -> list[dict]:
        return [{"fact_source": source, "facts": rows} for source, rows in self._received(context).items() if rows]

    @_boundary
    def received_facts(self, context, schema) -> ProteinFactGroups:
        sources = requested_sources(schema)
        if not sources:
            return {}
        values = self._received(context)
        return {source: deepcopy(values[source]) for source in sources}

    @_boundary
    def validate_received_report(self, context, form, schema) -> None:
        if not requested_sources(schema):
            return
        self.authenticate(context, allow_unsaved=True)
        values = self._values(form, schema)
        actual = self._own(context, verify_artifacts=True) if context.role == "results" else self._received(context)
        self._require(all(self._equal(rows, actual[source]) for source, rows in values.items()))
        self._frozen(context, values)

    @_boundary
    def record_admission(self, context, form, schema, operation_key) -> list[str]:
        if not requested_sources(schema):
            return []
        child, saved, original = self._attempt(context, self._admission_index(context, operation_key))
        self._require(self._equal(saved, form) and self._equal(original, schema))
        return _references(self._historical(child, saved, original))

    def _original(self, context, descriptor, source):
        record = self.results.read_result_authority(descriptor["custody"], scope=plain(context.scope))
        self._require(self._equal(record["custody"], descriptor["custody"]))
        candidates = list(_sequences(record["facts"])) if source == SEQUENCE_SOURCE else record["facts"][source]
        self._require(any(self._equal(descriptor, original) for original in candidates))
        return deepcopy(record)

    @_boundary
    def received_sequence_descriptors(self, context, reference_ref):
        result, seen = [], set()
        for source, row in self._deliveries(context):
            for descriptor in _sequences({source: [row]}):
                if descriptor["reference_ref"] == reference_ref and canonical(descriptor) not in seen:
                    self._original(context, descriptor, SEQUENCE_SOURCE)
                    result.append(deepcopy(descriptor))
                    seen.add(canonical(descriptor))
        return result

    @_boundary
    def authenticate_received_sequence(self, context, descriptor, *, required_use: SequenceUse
                                       ) -> ProteinResultAuthorityRecord:
        descriptor = _validate(validate_structure_sequence_descriptor, descriptor)
        if required_use not in {"sequence_align", "structure_correspondence"}:
            raise _error("invalid_schema", field="descriptor")
        self.authenticate(context, allow_unsaved=True)
        if required_use not in descriptor["allowed_uses"] or not any(self._equal(descriptor, candidate)
                for candidate in self.received_sequence_descriptors(context, descriptor["reference_ref"])):
            raise _error("sequence_not_received", field="descriptor")
        return self._original(context, descriptor, SEQUENCE_SOURCE)

    @_boundary
    def authenticate_received_saved_sheet(self, context, descriptor, *, required_use: SavedSheetUse
                                         ) -> ProteinResultAuthorityRecord:
        descriptor = _validate(validate_saved_sheet_descriptor, descriptor)
        if required_use not in {"recalculate", "select_projection", "use_transform"}:
            raise _error("invalid_schema", field="descriptor")
        self.authenticate(context, allow_unsaved=True)
        if required_use not in descriptor["allowed_uses"] or not any(self._equal(descriptor, candidate)
                for candidate in self._received(context)[SAVED_SOURCE]):
            raise _error("saved_sheet_not_received", field="descriptor")
        record = self._original(context, descriptor, SAVED_SOURCE)
        self._require(record["selector"]["return_saved_sheet"] is True
            and descriptor["allowed_uses"] == ["recalculate", "select_projection", "use_transform"]
            and self._equal(record["sheet_file"], descriptor["sheet_file"])
            and self._equal(record["original_components_file"], descriptor["original_components_file"]))
        return record

    @staticmethod
    def _explicit_refs(form, schema):
        """Only schema-declared reference cells; never arbitrary *_ref keys."""
        references, pending = [], [(form, schema)]
        while pending:
            value, node = pending.pop()
            if node.get("x-source") in FACT_SOURCES:
                continue
            if isinstance(value, dict):
                pending.extend((value[key], child) for key, child in reversed(list(node.get("properties", {}).items()))
                               if key in value)
            elif isinstance(value, list):
                pending.extend((item, node.get("items", {})) for item in reversed(value))
            elif node.get("format") == "reference" and isinstance(value, str):
                references.append(value)
        return references

    def _completed_alignment(self, context, alignment, before):
        prefix = f"{self.run_id}:{context.episode_id}:"
        key = alignment["original_operation_key"]
        if not key.startswith(prefix) or re.fullmatch(r"0|[1-9][0-9]*", key[len(prefix):]) is None:
            return False
        index = int(key[len(prefix):])
        if before is not None and index >= before:
            return False
        row = self.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND decision_index=?", (self.run_id, context.episode_id, index)).fetchone()
        if row is None or row["result"] is None:
            return False
        arguments = {"query_ref": alignment["query_reference_ref"], "reference_ref": alignment["reference_reference_ref"],
                     "molecule": "protein", "mode": alignment["mode"]}
        self._require(self._equal(json.loads(row["action"]), {"kind": "tool", "tool": "sequence.align", "arguments": arguments}))
        original = self.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (key,)).fetchone()
        self._require(original is not None and original["name"] == "sequence.align"
            and self._equal(json.loads(original["arguments"]), arguments)
            and self._equal(json.loads(original["scope"]), context.scope))
        outcome, saved = json.loads(row["result"]), json.loads(original["result"])
        if "pending_work_after_action" in outcome:
            from .waiting import validate_pending
            validate_pending(outcome.pop("pending_work_after_action"))
        operation_ref = identity("operation", {"key": key, "name": "sequence.align", "arguments": arguments})
        self._require(self._equal(outcome, saved) and saved.get("status") == "completed"
            and original["id"] == operation_ref == saved.get("operation_ref")
            and {alignment["observation_ref"], alignment["source_ref"]} <= set(saved.get("record_refs", [])))
        return True

    def _alignment_received(self, context, alignment, active=()):
        self._require(context.episode_id not in active)
        if not {alignment["observation_ref"], alignment["source_ref"]} <= self._known(context):
            return False
        for current, allowed, before, enabled in self._levels(context):
            if enabled and self._completed_alignment(current, alignment, before):
                return True
            for attempt in self._attempts_at(current, allowed, before, enabled):
                child, form, schema = self._attempt(current, attempt["decision_index"])
                self._values(form, schema)
                if alignment["observation_ref"] in self._explicit_refs(form, schema) \
                        and self._alignment_received(child, alignment, (*active, context.episode_id)):
                    return True
        return False

    @_boundary
    def authenticate_received_alignment(self, context, alignment) -> None:
        alignment = _validate(validate_alignment_descriptor, alignment)
        self.authenticate(context, allow_unsaved=True)
        records = {}
        for key, kind in (("observation_ref", "observation"), ("source_ref", "source")):
            record = self.store.get(alignment[key])
            if record["record_type"] != kind:
                raise _error("conflicting_identity", field="alignment")
            try:
                immutable_record(record)
            except ValueError as error:
                raise _error("conflicting_identity", field="alignment") from error
            records[kind] = record
        if (records["observation"].get("source_ref") != alignment["source_ref"]
                or records["observation"].get("kind") != "alignment"
                or records["source"].get("provider") != "biopython.alignment"):
            raise _error("alignment_operand_mismatch", field="alignment", stage="correspondence")
        if not self._alignment_received(context, alignment):
            raise _error("alignment_not_received", field="alignment")

    @_boundary
    def received_transform_projections(self, context, transform):
        transform = _validate(validate_declared_transform_record, transform)
        if transform["origin"] != "received_fitted" or transform["received_from"] is None:
            raise _error("invalid_transform", field="rotation")
        received = transform["received_from"]
        self.authenticate_received_saved_sheet(context, received["saved_sheet"], required_use="use_transform")
        record = self.results.read_result_authority(received["calculation_custody"], scope=plain(context.scope))
        self._require(self._equal(record["custody"], received["calculation_custody"]))
        candidates = []
        for value in self._received(context)[PROJECTION_SOURCE]:
            calculation = value["calculation"]
            if (value["family"] == "transform" and calculation is not None
                    and self._equal(value["custody"], received["calculation_custody"])
                    and calculation["calculation_id"] == received["calculation_id"]
                    and self._equal(calculation["components_file"], received["components_file"])
                    and {"rotation", "translation"} <= set(value["selection"]["fields"])):
                self._require(any(self._equal(value, original) for original in record["facts"][PROJECTION_SOURCE]))
                candidates.append(deepcopy(value))
        return candidates

    def _independent_reference(self, context, reference, active=()):
        self._require(context.episode_id not in active)
        if reference not in self._known(context):
            return False
        for current, allowed, before, enabled in self._levels(context):
            if enabled:
                rows = self.db.execute("SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? "
                    "AND episode_id=? AND result IS NOT NULL ORDER BY decision_index", (self.run_id, current.episode_id))
                for row in rows:
                    if before is not None and row["decision_index"] >= before:
                        continue
                    action, outcome = json.loads(row["action"]), json.loads(row["result"])
                    if (action.get("kind") == "tool" and action.get("tool") != "execution.results.collect"
                            and outcome.get("status") in {"completed", "partial"}
                            and reference in outcome.get("record_refs", [])):
                        return True
            for attempt in self._attempts_at(current, allowed, before, enabled):
                child, form, schema = self._attempt(current, attempt["decision_index"])
                self._values(form, schema)
                if reference not in self._explicit_refs(form, schema):
                    continue
                if child.role == "results" and self.store.get(reference)["record_type"] == "source":
                    # Host verifies the actual original actions even when the
                    # parent's form requested only the generic source handle.
                    self._own(child)
                    rows = self.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? "
                        "AND result IS NOT NULL", (self.run_id, child.episode_id))
                    for row in rows:
                        action, outcome = json.loads(row["action"]), json.loads(row["result"])
                        if (action == {"kind": "tool", "tool": "execution.results.collect", "arguments": {}}
                                and outcome.get("status") == "completed" and reference in outcome.get("record_refs", [])):
                            return True
                if self._independent_reference(child, reference, (*active, context.episode_id)):
                    return True
        return False

    def _own_result_source(self, context, reference, schema):
        if not any(node.get("x-source") == GENERIC_SOURCE for node in schema.get("properties", {}).values()):
            return False
        if self.store.get(reference)["record_type"] != "source":
            return False
        # _own already authenticated each original collect through the host.
        rows = self.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND result IS NOT NULL", (self.run_id, context.episode_id))
        for row in rows:
            action, outcome = json.loads(row["action"]), json.loads(row["result"])
            if (action == {"kind": "tool", "tool": "execution.results.collect", "arguments": {}}
                    and outcome.get("status") == "completed" and reference in outcome.get("record_refs", [])):
                return True
        return False

    @_boundary
    def retained_reference_access(self, context, reference, namespace):
        self.authenticate(context, allow_unsaved=True)
        if not self.results.owns_reference(reference):
            return None
        if namespace not in {None, "artifact", "source", "reference", "observation", "execution_result",
                              "subject", "execution_handoff", "record"}:
            return False
        groups, own_source = self._received(context), False
        if context.role == "results":
            # A result episode can expose its selected own output. This does
            # not admit its own output as a frozen operand of its assignment.
            schema = plain(context.request)["report_contract"]["measurements"]["schema"]
            requested = requested_sources(schema)
            own = {source: rows if source in requested else [] for source, rows in self._own(context).items()}
            groups = {source: [*groups[source], *own[source]] for source in FACT_SOURCES}
            own_source = self._own_result_source(context, reference, schema)
        allowed = reference in _references(groups) or own_source or self._independent_reference(context, reference)
        if not allowed:
            return False
        record = self.store.get(reference)
        if namespace in {"artifact", "source", "reference", "observation"}:
            return record["record_type"] == namespace
        if namespace == "subject":
            return record["record_type"] in {"input", "reference", "feature", "product"}
        if namespace == "execution_result":
            return record["record_type"] == "source" and record.get("version") == "native_protein_structure_bundle_v1"
        if namespace == "execution_handoff":
            descriptors = [*list(_sequences(groups)), *groups[SAVED_SOURCE]]
            return any(value["custody"]["handoff_ref"] == reference for value in descriptors)
        return True

    @_boundary
    def resolve_received(self, context, reference, namespace):
        # Semantic locators remain locators. D1 exposes no generic read namespace
        # for calculation ids, projection ids or receipt keys.
        if (isinstance(reference, str) and reference.startswith("protein_structure_result_receipt:")) \
                or isinstance(namespace, str) and namespace.startswith("protein_structure_"):
            return False
        return self.retained_reference_access(context, reference, namespace)


__all__ = ["NativeProteinStructureReturns", "requested_sources", "SequenceUse", "SavedSheetUse",
           "FACT_SOURCES", "PROJECTION_SOURCE", "SAVED_SOURCE", "SEQUENCE_SOURCE", "FAILURE_SOURCE"]
