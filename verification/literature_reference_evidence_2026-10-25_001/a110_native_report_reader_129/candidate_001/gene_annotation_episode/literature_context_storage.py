"""Persist selected reference organism/sample compatibility and exact admitted subsets.

This adapter owns source custody and immutable selected-operation records. It
does not choose investigations, interpret experiments, add observations or
recompute a saved numerical sheet during replay.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_rate_storage import LiteratureRateRepository
from .literature_context_calculations import (
    COMPONENTS, CONDITIONAL_CODES, REASONS, QUESTION_KINDS, ORIGINS,
    SCOPE_STATUSES, FRAME_STATUSES, PAIRINGS, WEIGHT_BASES, SAMPLING_DESIGNS,
    empty_context_inputs, populate_context_compatibility,
)
from .literature_context_inputs import (
    LITERAL_FIELDS, NATIVE_UNITS, context_population_schema, read_context_inputs,
)
from .literature_context_meanings import (
    INPUT_VERSION as MEANINGS_INPUT_VERSION, RECORD_VERSION as MEANINGS_RECORD_VERSION,
    NAMESPACE as MEANINGS_NAMESPACE, direct_references as meaning_direct_references,
    publish_meanings, semantic_metadata, binding_references,
)


PROVIDER = "literature.experimental.context"
FORMULA_CODES = {name: "context_" + name + "_v1" for name in COMPONENTS}
BINDINGS = {
    "assayed_subject_ref": ("molecule", "reference"),
    "organism_ref": ("organism", "reference"),
    "strain_ref": ("strain", "reference"),
    "experiment_ref": ("experiment", "reference"),
    "function_ref": ("function", "term"),
    "biological_context_ref": ("biological_context", "context"),
    "sample_frame_ref": ("sample_frame", "context"),
    "endpoint_ref": ("endpoint", "term"),
    "condition_ref": ("condition", "context"),
}
_FIXED_METADATA = {
    "evaluation_scope": "reference_organism_sample_compatibility",
    "bound_kind": "logical_domain_not_confidence_interval",
    "measurement_corrections": "not_applied",
    "target_correspondence": "not_evaluated",
}


def _metadata(extraction, sheet):
    inputs = sheet["inputs"]
    indices = {entry["key"]: index for index, entry in enumerate(inputs["requirements"])}
    units = [entry["unit"] for entry in inputs["requirements"]]
    units.extend(observation["unit"] for context in inputs["contexts"]
                 for observation in context["observations"])
    return {**_FIXED_METADATA,
        **{key: deepcopy(inputs[key]) for key in (
            "question_kind", "scope_status", "frame_status", "pairing", "weight_basis",
            "sampling_design", "alpha", "permitted_remainder")},
        "operand_origin": inputs["origin"],
        **deepcopy(sheet["counts"]),
        "requirement_count": len(inputs["requirements"]),
        "route_count": None if inputs["routes"] is None else len(inputs["routes"]),
        "requirement_definitions": [{key: deepcopy(entry[key])
            for key in ("unit", "supported", "incompatible")} for entry in inputs["requirements"]],
        "route_definitions": None if inputs["routes"] is None else [{
            "requirements": [indices[key] for key in route["requirements"]],
            "requirements_complete": route["requirements_complete"],
            "joint_support": route["joint_support"]} for route in inputs["routes"]],
        "native_unit_bases": list(dict.fromkeys(units)),
        "qualifications": deepcopy(sheet["qualifications"])}


def _direct_references(args):
    """Fixed semantic order survives canonical JSON object-key reordering."""
    return list(dict.fromkeys([args["source_ref"],
        *([args["data_source_ref"]] if args["data_source_ref"] is not None else []),
        *(args["literals"][field]["source_ref"] for field in LITERAL_FIELDS
          if args["literals"][field] is not None),
        *(entry["source_ref"] for entry in args["interpretation_witnesses"])]))


class LiteratureContextRepository(LiteratureRateRepository):
    provider = PROVIDER
    components = COMPONENTS
    record_version = "literature_context_record_v1"
    operations_table = "literature_context_operations"
    received_table = "literature_context_received"
    binding_fields = tuple(BINDINGS)

    def semantic_projection(self):
        return LiteratureContextSemanticProjection(self.store, self.run_id)

    def cells_schema(self):
        return context_cells_schema()

    def _row_metadata(self, saved):
        return _metadata(saved["extraction"], saved["sheet"])

    def validate_empty_return_family(self, context):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        versions = set()
        for row in self.store.db.execute(f"SELECT outcome FROM {self.operations_table} "
                "WHERE run_id=? AND episode_id=?", (self.run_id, context.episode_id)):
            outcome = json.loads(row["outcome"])
            if outcome.get("status") == "completed":
                sheet = self.store.get(outcome["result"]["sheet_ref"])
                if sheet.get("provider") == self.provider:
                    versions.add(sheet.get("version"))
        if self.record_version not in versions and versions & {
                "literature_context_record_v1", MEANINGS_RECORD_VERSION}:
            raise ContractError("literature_context_projection_version_mismatch")

    def _provenance(self, context, reference):
        if not self.store.reference_subset([reference], plain(context.scope)):
            raise ContractError("literature_source_outside_scope")
        row = self.store.get(reference)
        if row["record_type"] != "source":
            raise ContractError("literature_source_required")
        return row

    def _source(self, context, reference):
        if reference not in context.received_record_refs:
            raise ContractError("literature_source_not_received")
        source = self._provenance(context, reference)
        page = context.assignment if context.role == "literature_page" else context.assignment.get("page")
        if page:
            pending, seen = [reference], set()
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                ancestor = self._provenance(context, current)
                if current == page["source_ref"]:
                    break
                pending.extend(ancestor.get("parent_source_refs", ()))
            else:
                raise ContractError("literature_reading_outside_assigned_source")
        return source

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        validate_schema(args, context_population_schema())
        signature = canonical({"arguments": args, "scope": plain(context.scope)})
        old = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, context.episode_id, operation_key)).fetchone()
        if old is not None:
            if old["signature"] != signature:
                raise ContractError("operation_key_reused_for_different_work")
            outcome = json.loads(old["outcome"])
            saved = self.read(outcome["result"]["sheet_ref"])
            for reference in saved["direct_input_source_refs"]:
                self._source(context, reference)
            for reference in saved["input_source_refs"]:
                self._provenance(context, reference)
            return outcome

        direct = _direct_references(args)
        for reference in direct:
            self._source(context, reference)
        source = self.store.get(args["source_ref"])
        def read_source(reference, representation):
            row = self._source(context, reference)
            if representation not in ("original", "text"):
                raise ContractError("literature_source_representation_required")
            artifact = row["artifact_ref"] if representation == "original" else row.get("text_ref")
            if artifact is None:
                raise ContractError("literature_source_representation_unavailable")
            return {"artifact_ref": artifact, "content": self.store.get_artifact(artifact)}
        extraction = read_context_inputs(args, read_source=read_source)
        direct = meaning_direct_references(args, extraction, direct)
        if set(extraction["sources"]) != set(direct):
            raise ContractError("literature_context_direct_source_mismatch")
        inputs = extraction["calculation_inputs"]
        prepared_inputs = empty_context_inputs() if inputs is None else inputs
        sheet = populate_context_compatibility(prepared_inputs)
        parents, seen = list(direct), set(direct)
        cursor = 0
        while cursor < len(parents):
            reference = parents[cursor]
            cursor += 1
            for parent in self.store.get(reference).get("parent_source_refs", ()):
                self._provenance(context, parent)
                if parent not in seen:
                    seen.add(parent)
                    parents.append(parent)
        record_version = (MEANINGS_RECORD_VERSION if extraction["version"] == MEANINGS_INPUT_VERSION
                          else self.record_version)
        payload = {"version": record_version, "input_source_ref": source["id"],
            "input_artifact_ref": source["artifact_ref"], "input_source_refs": parents,
            "direct_input_source_refs": direct, "data_source_ref": args["data_source_ref"],
            "extraction": extraction, "prepared_inputs": prepared_inputs, "sheet": sheet}
        with self.store.transaction():
            created = []
            def publish(kind, record):
                candidate = identity(kind, {"origin": "tool", "record": record})
                existed = self.store.db.execute("SELECT 1 FROM records WHERE id=?", (candidate,)).fetchone()
                row = self.store.put(kind, record, origin="tool", scope=plain(context.scope))
                if existed is None:
                    created.append(row["id"])
                return row["id"]
            bindings = {}
            for field, (literal, kind) in BINDINGS.items():
                entry = extraction["literals"][literal]
                if entry is None:
                    bindings[field] = None
                    continue
                witness = entry["witness"]
                anchor = {name: witness[name] for name in (
                    "source_ref", "artifact_ref", "start", "end", "quote")}
                common = {"source_ref": witness["source_ref"], "anchor": anchor}
                accession = identity("context_literal", {"field": literal, **anchor})
                if kind == "reference":
                    record = {**common, "reference_type": "assay", "accession": accession,
                        "label": entry["value"], "sequence_ref": None, "molecule": None,
                        "length": None, "term_refs": [], "context_refs": []}
                elif kind == "term":
                    record = {**common, "namespace": "literature_context_" + literal,
                        "accession": accession, "label": entry["value"], "term_type": "other"}
                else:
                    context_type = {"biological_context": "environment", "sample_frame": "sample",
                                    "condition": "assay_condition"}[literal]
                    record = {**common, "context_type": context_type, "name": entry["value"],
                        "attributes": [], "related_refs": []}
                bindings[field] = publish(kind, record)
            payload["experimental_bindings"] = bindings
            semantic_bindings = (publish_meanings(extraction, publish)
                if record_version == MEANINGS_RECORD_VERSION else None)
            if semantic_bindings is not None:
                payload["semantic_bindings"] = semantic_bindings
            metadata = _metadata(extraction, sheet)
            if semantic_bindings is not None:
                metadata = semantic_metadata(metadata, semantic_bindings)
            artifact = self.store.artifact(canonical(payload), "application/json")
            request = self.store.artifact(canonical({"run_id": self.run_id,
                "episode_id": context.episode_id, "operation_key": operation_key,
                "arguments": args, "scope": plain(context.scope)}), "application/json")
            sheet_ref = publish("source", {"provider": self.provider, "accession": None, "uri": None,
                "artifact_ref": artifact, "text_ref": artifact, "request_ref": request,
                "version": record_version, "retrieved_at": None, "parent_source_refs": parents})
            outcome = {"status": "completed", "operation_ref": identity("operation", {
                "run_id": self.run_id, "episode_id": context.episode_id, "key": operation_key}),
                "record_refs": list(dict.fromkeys([sheet_ref, *parents,
                    *(reference for reference in bindings.values() if reference),
                    *(binding_references(semantic_bindings) if semantic_bindings is not None else [])])),
                "changed_record_refs": created, "result": {"sheet_ref": sheet_ref,
                    "cells": sheet["cells"], "assay_interpretation": extraction["literals"],
                    **metadata}, "feedback": None}
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def read(self, sheet_ref):
        if (self.record_version != MEANINGS_RECORD_VERSION
                and self.store.get(sheet_ref).get("version") == MEANINGS_RECORD_VERSION):
            return self.semantic_projection().read(sheet_ref)
        saved = super().read(sheet_ref)
        source = self.store.get(sheet_ref)
        request = json.loads(self.store.get_artifact(source["request_ref"]))
        args, extraction = request["arguments"], saved["extraction"]
        operation = self.store.db.execute(f"SELECT signature FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request["episode_id"], request["operation_key"])).fetchone()
        if (source["version"] != self.record_version
                or operation["signature"] != canonical({"arguments": args, "scope": request["scope"]})
                or saved["direct_input_source_refs"] != meaning_direct_references(
                    args, extraction, _direct_references(args))
                or set(extraction["sources"]) != set(saved["direct_input_source_refs"])
                or self.store.get(saved["input_source_ref"])["artifact_ref"] != saved["input_artifact_ref"]
                or saved["data_source_ref"] != args["data_source_ref"]
                or extraction["arguments"] != args
                or saved["sheet"]["inputs"] != saved["prepared_inputs"]
                or (extraction["calculation_inputs"] is not None
                    and saved["prepared_inputs"] != extraction["calculation_inputs"])):
            raise ContractError("literature_context_sheet_source_mismatch")
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        components = self.components if components is None else components
        if (not isinstance(components, (list, tuple))
                or any(not isinstance(name, str) or name not in self.components for name in components)
                or len(set(components)) != len(components)):
            raise ContractError("literature_context_component_selection_invalid")
        rows = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            saved = self.read(reference)
            if saved["version"] != self.record_version:
                raise ContractError("literature_context_projection_version_mismatch")
            for name in components:
                cell = {key: deepcopy(value) for key, value in saved["sheet"]["cells"][name].items()
                    if key != "formula"}
                rows.append({"sheet_ref": reference, "evidence_source_ref": saved["input_source_ref"],
                    "data_source_ref": saved["data_source_ref"], **saved["experimental_bindings"],
                    "component": name, **cell, "formula_code": FORMULA_CODES[name],
                    **self._row_metadata(saved)})
        validate_schema(rows, self.cells_schema())
        return rows

    def validate_returned_values(self, cells, *, permitted_record_refs):
        validate_schema(cells, self.cells_schema())
        super().validate_returned_values(cells, permitted_record_refs=permitted_record_refs)


def context_cells_schema():
    """Closed scientific rows retain logical bounds and sampling conditions."""
    source = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    nullable_number = {"type": ["number", "null"]}
    interval = obj({"lower": dict(nullable_number), "upper": dict(nullable_number),
        "lower_closed": {"type": "boolean"}, "upper_closed": {"type": "boolean"}})
    domains = {"type": "array", "items": interval}
    requirement = obj({"unit": {"type": "string", "enum": list(NATIVE_UNITS)},
        "supported": deepcopy(domains), "incompatible": deepcopy(domains)})
    route = obj({"requirements": {"type": "array", "uniqueItems": True,
        "items": {"type": "integer", "minimum": 0}},
        "requirements_complete": {"type": "boolean"},
        "joint_support": {"type": "string", "enum": ["established", "unresolved", "conflicting"]}})
    properties = {"sheet_ref": dict(source), "evidence_source_ref": dict(source),
        "data_source_ref": {**source, "type": ["string", "null"]},
        **{field: {"type": ["string", "null"], "format": "reference", "x-reference-namespace": kind}
            for field, (_, kind) in BINDINGS.items()},
        "component": {"type": "string", "enum": list(COMPONENTS)},
        "value": dict(nullable_number),
        "unit": {"type": "string", "enum": ["context_weight", "dimensionless"]},
        "status": {"type": "string", "enum": ["populated", "unavailable"]},
        "formula_code": {"type": "string", "enum": list(FORMULA_CODES.values())},
        "origin": {"type": "string", "enum": ["reported", "graph_derived", "synthetic", "derived", "proposed"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [None, *REASONS]},
        "conditional_on": {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "enum": list(CONDITIONAL_CODES)}},
        **{field: {"type": "string", "enum": list(allowed)} for field, allowed in (
            ("question_kind", QUESTION_KINDS), ("operand_origin", ORIGINS),
            ("scope_status", SCOPE_STATUSES), ("frame_status", FRAME_STATUSES),
            ("pairing", PAIRINGS), ("weight_basis", WEIGHT_BASES),
            ("sampling_design", SAMPLING_DESIGNS))},
        "alpha": {**nullable_number, "exclusiveMinimum": 0, "exclusiveMaximum": 1},
        "permitted_remainder": {"type": ["boolean", "null"]},
        **{field: {"type": "integer", "minimum": 0} for field in (
            "context_units", "distinct_known_clusters", "requirement_count")},
        "actual_sampling_n": {"type": ["integer", "null"], "minimum": 1},
        "route_count": {"type": ["integer", "null"], "minimum": 1},
        "requirement_definitions": {"type": "array", "items": requirement},
        "route_definitions": {"type": ["array", "null"], "minItems": 1, "items": route},
        "native_unit_bases": {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "enum": list(NATIVE_UNITS)}},
        "qualifications": {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "enum": list(REASONS)}},
        **{field: {"type": "string", "enum": [value]} for field, value in _FIXED_METADATA.items()}}
    return {"type": "array", "items": obj(properties), "x-source": "literature_context_cells"}


def context_semantic_cells_schema():
    """Closed v2 view of the same cells, with scoped operand and route meanings."""
    schema = deepcopy(context_cells_schema())
    schema["x-source"] = MEANINGS_NAMESPACE
    properties = schema["items"]["properties"]
    requirement = properties["requirement_definitions"]["items"]
    route = properties["route_definitions"]["items"]
    def ref(namespace, nullable=True):
        return {"type": ["string", "null"] if nullable else "string", "format": "reference",
                "x-reference-namespace": namespace}
    def extend(target, fields):
        target["properties"].update(fields)
        target["required"].extend(fields)
    extend(requirement, {"requirement_ref": ref("reference", False),
        "definition_reported": {"type": "boolean"}, "entity_ref": ref("term"),
        "property_ref": ref("term"), "biological_setting_ref": ref("context"),
        "function_relation_ref": ref("term")})
    extend(route, {"route_ref": ref("reference", False),
        "definition_reported": {"type": "boolean"}, "biological_setting_ref": ref("context"),
        "function_relation_ref": ref("term"), "membership_evidence_ref": ref("reference"),
        "joint_scope_evidence_ref": ref("reference"),
        "requirement_refs": {"type": "array", "uniqueItems": True, "items": ref("reference", False)}})
    return schema


class LiteratureContextSemanticProjection(LiteratureContextRepository):
    """Independently received scientific view; no additional sheet or operation."""
    record_version = MEANINGS_RECORD_VERSION
    received_table = "literature_context_semantic_received"

    def __init__(self, store, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("explicit_literature_run_required")
        self.store, self.run_id = store, run_id

    def populate(self, context, arguments, operation_key):
        raise ContractError("context_semantic_return_view_cannot_publish")

    def cells_schema(self):
        return context_semantic_cells_schema()

    def _row_metadata(self, saved):
        return semantic_metadata(_metadata(saved["extraction"], saved["sheet"]), saved["semantic_bindings"])

    def read(self, sheet_ref):
        saved = super().read(sheet_ref)
        source = self.store.get(sheet_ref)
        request = json.loads(self.store.get_artifact(source["request_ref"]))
        operation = self.store.db.execute(f"SELECT outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request["episode_id"], request["operation_key"])).fetchone()
        outcome = json.loads(operation["outcome"])
        # Read only immutable saved artifacts/records, never source bytes or a
        # new calculator/extractor pass. Exact outcome agrees with this view.
        import hashlib
        payload = self.store.get_artifact(source["artifact_ref"])
        if ("artifact_" + hashlib.sha256(payload).hexdigest() != source["artifact_ref"]
                or saved["extraction"].get("version") != MEANINGS_INPUT_VERSION
                or saved["sheet"]["cells"] != outcome["result"]["cells"]
                or any(outcome["result"].get(key) != value for key, value in self._row_metadata(saved).items())):
            raise ContractError("literature_context_semantic_saved_mismatch")
        return saved

    def _installed(self):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (self.received_table,)).fetchone() is not None

    def received_cells(self, context):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        return super().received_cells(context) if self._installed() else []

    def receive_cells(self, context, cells, operation_key):
        with self.store.transaction():
            self.store.db.execute(f"""CREATE TABLE IF NOT EXISTS {self.received_table}(
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, operation_key TEXT NOT NULL,
                cells TEXT NOT NULL, PRIMARY KEY(run_id,episode_id,operation_key))""")
            return super().receive_cells(context, cells, operation_key)


__all__ = ["LiteratureContextRepository", "COMPONENTS", "PROVIDER",
    "LiteratureContextSemanticProjection", "context_population_schema", "context_cells_schema",
    "context_semantic_cells_schema"]
