"""Persist selected reference reaction constraints and exact admitted subsets.

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
from .literature_reaction_types import EXPERIMENT_TYPES
from . import literature_experiment_assessments as assessments
from .literature_reaction_calculations import (
    COMPONENTS, CONDITIONAL_CODES, REASONS, populate_reaction_constraints,
)
from .literature_reaction_inputs import (
    LITERAL_FIELDS, reaction_population_schema, read_reaction_inputs,
)

from .literature_reaction_meanings import (
    INPUT_VERSION as MEANINGS_INPUT_VERSION, RECORD_VERSION as MEANINGS_RECORD_VERSION,
    NAMESPACE as MEANINGS_NAMESPACE, BASES, MODEL_FIELDS, RESOURCE_FIELDS, DEMAND_FIELDS,
    direct_references as meaning_direct_references, publish_meanings, semantic_metadata,
    binding_references,
)


PROVIDER = "literature.experimental.reaction"
FORMULA_CODES = {name: "reaction_" + name + "_v1" for name in COMPONENTS}
BINDINGS = {
    "assayed_subject_ref": ("molecule", "reference"),
    "construct_ref": ("construct", "reference"),
    "experiment_ref": ("experiment", "reference"),
    "numerator_ref": ("numerator", "term"),
    "denominator_ref": ("denominator", "term"),
    "endpoint_ref": ("endpoint", "term"),
    "condition_ref": ("condition", "context"),
    "resource_context_ref": ("resource_context", "context"),
}
SOURCE_KINDS = ("primary_source", "retained_extraction", "graph_extraction", "synthetic_fixture")
_FIXED_METADATA = {
    "evaluation_scope": "reported_reference_reaction_constraints",
    "bound_kind": "logical_model_domain_not_confidence_interval",
    "measurement_corrections": "not_applied",
    "target_correspondence": "not_evaluated",
    "uncertainty_interpretation": "descriptive_not_confidence_interval",
}


def _metadata(extraction, sheet):
    ratio = extraction["calculation_inputs"]["ratio"]
    budget = extraction["calculation_inputs"]["budget"]
    details = sheet["ratio_details"]
    reported_sd = details["reported_sample_sd"]
    derived_sd = details["derived_sample_sd"]["value"]
    return {**_FIXED_METADATA,
        "operand_source_kind": extraction["arguments"]["source_kind"],
        "ratio_origin": ratio["origin"] if ratio is not None else None,
        "budget_origin": budget["origin"] if budget is not None else None,
        "independent_n": details["independent_n"],
        "reported_sample_sd": reported_sd,
        "derived_sample_sd": derived_sd,
        "ratio_uncertainty": "reported_sample_sd" if reported_sd is not None else
            "descriptive_sample_sd" if derived_sd is not None else "unreported",
        "ratio_mode": ratio["mode"] if ratio is not None else None,
        "ratio_kind": ratio["ratio_kind"] if ratio is not None else None,
        "ratio_unit": ratio["unit"] if ratio is not None else None,
        "claim_prediction": ratio["claim"] if ratio is not None else None,
        "alternative_predictions": [entry["prediction"] for entry in ratio["alternatives"]]
            if ratio is not None else [],
        "budget_basis": budget["basis"] if budget is not None else None,
        "budget_unit": budget["unit"] if budget is not None else None,
        "resources_complete": budget["resources_complete"] if budget is not None else None,
        "demand": budget["demand"] if budget is not None else None}


def _direct_references(args):
    """Fixed semantic order survives canonical JSON object-key reordering."""
    return list(dict.fromkeys([args["source_ref"],
        *([args["data_source_ref"]] if args["data_source_ref"] is not None else []),
        *(args["literals"][field]["source_ref"] for field in LITERAL_FIELDS
          if args["literals"][field] is not None),
        *(entry["source_ref"] for entry in args["interpretation_witnesses"])]))


def reaction_direct_references(extraction, direct):
    refs = meaning_direct_references(extraction, direct)
    if "native_evidence" in extraction:
        from .literature_reaction_native_inputs import native_direct_references
        refs.extend(native_direct_references(extraction["native_evidence"]))
    return list(dict.fromkeys(refs))


class LiteratureReactionRepository(LiteratureRateRepository):
    experiment_types = EXPERIMENT_TYPES
    provider = PROVIDER
    components = COMPONENTS
    record_version = "literature_reaction_record_v2"
    operations_table = "literature_reaction_operations"
    received_table = "literature_reaction_received"
    binding_fields = tuple(BINDINGS)

    def semantic_projection(self):
        return LiteratureReactionSemanticProjection(self.store, self.run_id)

    def native_observations_projection(self):
        from .literature_reaction_native_storage import LiteratureReactionNativeObservations
        return LiteratureReactionNativeObservations(self.store, self.run_id)

    def cells_schema(self):
        return reaction_cells_schema()

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
                source = self.store.get(outcome["result"]["sheet_ref"])
                if source.get("provider") == self.provider:
                    versions.add(source.get("version"))
        if self.record_version not in versions and versions & {
                "literature_reaction_record_v2", MEANINGS_RECORD_VERSION}:
            raise ContractError("literature_reaction_projection_version_mismatch")

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
        validate_schema(args, reaction_population_schema(include_assessment=True))
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
            if "experiment_assessment" in args:
                assessments.authorize_assessment(self, context, args["experiment_assessment"])
            return outcome

        assessment = args.get("experiment_assessment")
        if assessment is not None:
            assessments.authorize_assessment(self, context, assessment)
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
        extraction = read_reaction_inputs(args, read_source=read_source)
        direct = reaction_direct_references(extraction, direct)
        if set(extraction["sources"]) != set(direct):
            raise ContractError("literature_reaction_direct_source_mismatch")
        sheet = populate_reaction_constraints(extraction["calculation_inputs"])
        parents, seen = list(direct), set(direct)
        if assessment is not None:
            parents.append(self.store.get(assessment["experiment_ref"])["source_ref"])
            if assessment["revises_sheet_ref"] is not None:
                parents.append(assessment["revises_sheet_ref"])
            parents = list(dict.fromkeys(parents))
            seen = set(parents)
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
            "extraction": extraction, "sheet": sheet}
        with self.store.transaction():
            if assessment is not None:
                assessments.check_revision(self, assessment)
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
                accession = identity("reaction_literal", {"field": literal, **anchor})
                if kind == "reference":
                    record = {**common, "reference_type": "assay", "accession": accession,
                        "label": entry["value"], "sequence_ref": None, "molecule": None,
                        "length": None, "term_refs": [], "context_refs": []}
                elif kind == "term":
                    record = {**common, "namespace": "literature_reaction_" + literal,
                        "accession": accession, "label": entry["value"], "term_type": "other"}
                else:
                    record = {**common, "context_type": "assay_condition", "name": entry["value"],
                        "attributes": [], "related_refs": []}
                bindings[field] = publish(kind, record)
            if assessment is not None:
                bindings["experiment_ref"] = assessment["experiment_ref"]
                payload["experiment_assessment"] = deepcopy(assessment)
            payload["experimental_bindings"] = bindings
            semantic_bindings = (publish_meanings(extraction, publish)
                if record_version == MEANINGS_RECORD_VERSION else None)
            if semantic_bindings is not None:
                payload["semantic_bindings"] = semantic_bindings
            metadata = _metadata(extraction, sheet)
            if semantic_bindings is not None:
                metadata = semantic_metadata(metadata, semantic_bindings,
                    extraction["calculation_inputs"], sheet)
            native_rows = None
            if "native_evidence" in extraction:
                from .literature_reaction_native_storage import publish_native_observations
                native_rows = publish_native_observations(extraction, bindings, semantic_bindings, publish)
                payload["native_observations"] = native_rows
                from .literature_reaction_native_storage import native_row_references
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
                    *(binding_references(semantic_bindings) if semantic_bindings is not None else []),
                    *(native_row_references(native_rows) if native_rows is not None else [])])),
                "changed_record_refs": created, "result": {"sheet_ref": sheet_ref,
                    "cells": sheet["cells"], "assay_interpretation": extraction["literals"],
                    **metadata, **({"native_observations": native_rows} if native_rows is not None else {})}, "feedback": None}
            if assessment is not None:
                outcome["result"]["experiment_assessment"] = deepcopy(assessment)
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
                or saved["direct_input_source_refs"] != reaction_direct_references(extraction, _direct_references(args))
                or set(extraction["sources"]) != set(saved["direct_input_source_refs"])
                or self.store.get(saved["input_source_ref"])["artifact_ref"] != saved["input_artifact_ref"]
                or saved["data_source_ref"] != args["data_source_ref"]
                or extraction["arguments"] != args
                or saved["sheet"]["inputs"] != extraction["calculation_inputs"]):
            raise ContractError("literature_reaction_sheet_source_mismatch")
        if "native_evidence" in extraction:
            from .literature_reaction_native_inputs import TRACE_VERSION
            if extraction["native_evidence"].get("version") != TRACE_VERSION:
                raise ContractError("literature_reaction_native_saved_mismatch")
            def witnessed(value):
                if isinstance(value, dict):
                    if set(value) == {"source_ref", "representation", "start", "end", "quote", "artifact_ref"}:
                        yield value
                    else:
                        for child in value.values():
                            yield from witnessed(child)
                elif isinstance(value, list):
                    for child in value:
                        yield from witnessed(child)
            for witness in witnessed(extraction["native_evidence"]):
                row = self.store.get(witness["source_ref"])
                artifact = row["artifact_ref"] if witness["representation"] == "original" else row.get("text_ref")
                if artifact != witness["artifact_ref"] or witness["source_ref"] not in saved["direct_input_source_refs"]:
                    raise ContractError("literature_reaction_native_source_mismatch")
        assessments.validate_saved_assessment(self, saved, request)
        return saved

    def current_assessments(self):
        return assessments.current_assessments(self)

    def assessment_history(self, sheet_ref):
        return assessments.assessment_history(self, sheet_ref)

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        components = self.components if components is None else components
        if (not isinstance(components, (list, tuple))
                or any(not isinstance(name, str) or name not in self.components for name in components)
                or len(set(components)) != len(components)):
            raise ContractError("literature_reaction_component_selection_invalid")
        rows = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            saved = self.read(reference)
            if saved["version"] != self.record_version:
                raise ContractError("literature_reaction_projection_version_mismatch")
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


def reaction_cells_schema():
    """Closed scientific return: selected cells and their numeric model panel."""
    source = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    nullable_number = {"type": ["number", "null"]}
    def nullable_enum(values):
        return {"type": ["string", "null"], "enum": [None, *values]}
    properties = {"sheet_ref": dict(source), "evidence_source_ref": dict(source),
        "data_source_ref": {**source, "type": ["string", "null"]},
        **{field: {"type": ["string", "null"], "format": "reference", "x-reference-namespace": kind}
            for field, (_, kind) in BINDINGS.items()},
        "component": {"type": "string", "enum": list(COMPONENTS)},
        "value": dict(nullable_number),
        "unit": {"type": "string", "enum": ["mol_per_mol", "signal_per_signal", "squared_ratio",
            "dimensionless", "umol", "uM", "umol_per_min", "uM_per_min", "unreported"]},
        "status": {"type": "string", "enum": ["populated", "unavailable"]},
        "formula_code": {"type": "string", "enum": list(FORMULA_CODES.values())},
        "origin": {"type": "string", "enum": ["reported", "graph_derived", "synthetic", "derived", "proposed"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [None, *REASONS]},
        "conditional_on": {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "enum": list(CONDITIONAL_CODES)}},
        "ratio_mode": nullable_enum(["independent_units", "source_summary"]),
        "ratio_kind": nullable_enum(["product_pair", "formed_per_consumed", "formed_per_supplied", "signal_ratio"]),
        "ratio_unit": nullable_enum(["mol_per_mol", "signal_per_signal"]),
        "ratio_origin": nullable_enum(["reported", "graph_derived", "synthetic"]),
        "budget_origin": nullable_enum(["reported", "graph_derived", "synthetic"]),
        "independent_n": {"type": ["integer", "null"], "minimum": 1},
        "reported_sample_sd": {**nullable_number, "minimum": 0},
        "derived_sample_sd": {**nullable_number, "minimum": 0},
        "ratio_uncertainty": {"type": "string", "enum": ["reported_sample_sd",
            "descriptive_sample_sd", "unreported"]},
        "claim_prediction": dict(nullable_number),
        "alternative_predictions": {"type": "array", "items": dict(nullable_number)},
        "budget_basis": nullable_enum(["supplied_reagent_batch", "usable_batch", "usable_rate"]),
        "budget_unit": nullable_enum(["umol", "uM", "umol_per_min", "uM_per_min"]),
        "resources_complete": {"type": ["boolean", "null"]},
        "demand": {**nullable_number, "exclusiveMinimum": 0},
        "operand_source_kind": {"type": "string", "enum": list(SOURCE_KINDS)},
        **{field: {"type": "string", "enum": [value]} for field, value in _FIXED_METADATA.items()}}
    return {"type": "array", "items": obj(properties), "x-source": "literature_reaction_cells"}


def reaction_semantic_cells_schema():
    """Closed named scientific view of the same15 existing numerical cells."""
    schema = deepcopy(reaction_cells_schema())
    schema["x-source"] = MEANINGS_NAMESPACE
    properties = schema["items"]["properties"]
    def ref(kind, nullable=True):
        return {"type": ["string", "null"] if nullable else "string", "format": "reference",
                "x-reference-namespace": kind}
    def meaning(kind, fields, bases):
        return {kind + "_ref": ref("reference", False), "definition_reported": {"type": "boolean"},
            **{field + "_ref": ref(namespace) for field, namespace in fields.items() if field != "definition"},
            **{basis: {"type": "string", "enum": list(BASES)} for basis in bases}}
    model = obj({**meaning("model", MODEL_FIELDS, ("prediction_basis",)),
        "role": {"type": "string", "enum": ["claim", "alternative"]},
        "prediction": {"type": ["number", "null"]},
        "unit": {"type": "string", "enum": ["mol_per_mol", "signal_per_signal"]}})
    resource = obj({**meaning("resource", RESOURCE_FIELDS, ("supply_basis", "coefficient_basis")),
        "coefficient": {"type": "number", "exclusiveMinimum": 0},
        "coefficient_role": {"type": "string", "enum": ["resource_unit_per_demand_unit"]},
        "coefficient_demand_ref": ref("reference", False)})
    demand = obj({**meaning("demand", DEMAND_FIELDS, ("demand_basis",)),
        "value": {"type": ["number", "null"], "exclusiveMinimum": 0},
        "unit": {"type": "string", "enum": ["umol", "uM", "umol_per_min", "uM_per_min"]}})
    fields = {"model_definitions": {"type": "array", "items": model},
        "comparison_member_refs": {"type": "array", "uniqueItems": True, "items": ref("reference", False)},
        "comparison_reduction": {"type": "string", "enum": ["minimum_over_declared_alternatives"]},
        "resource_definitions": {"type": "array", "items": resource},
        "demand_definition": {**demand, "type": ["object", "null"]},
        "nominal_limiting_resource_refs": {"type": "array", "uniqueItems": True, "items": ref("reference", False)}}
    properties.update(fields)
    schema["items"]["required"].extend(fields)
    return schema


class LiteratureReactionSemanticProjection(LiteratureReactionRepository):
    """Independent receipt of the named view, with no new operation or sheet."""
    record_version = MEANINGS_RECORD_VERSION
    received_table = "literature_reaction_semantic_received"

    def __init__(self, store, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("explicit_literature_run_required")
        self.store, self.run_id = store, run_id

    def populate(self, context, arguments, operation_key):
        raise ContractError("reaction_semantic_return_view_cannot_publish")

    def cells_schema(self):
        return reaction_semantic_cells_schema()

    def _row_metadata(self, saved):
        return semantic_metadata(_metadata(saved["extraction"], saved["sheet"]),
            saved["semantic_bindings"], saved["extraction"]["calculation_inputs"], saved["sheet"])

    def read(self, sheet_ref):
        saved = super().read(sheet_ref)
        source = self.store.get(sheet_ref)
        request = json.loads(self.store.get_artifact(source["request_ref"]))
        operation = self.store.db.execute(f"SELECT outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request["episode_id"], request["operation_key"])).fetchone()
        outcome = json.loads(operation["outcome"])
        import hashlib
        payload = self.store.get_artifact(source["artifact_ref"])
        if ("artifact_" + hashlib.sha256(payload).hexdigest() != source["artifact_ref"]
                or saved["extraction"].get("version") != MEANINGS_INPUT_VERSION
                or saved["sheet"]["cells"] != outcome["result"]["cells"]
                or any(outcome["result"].get(key) != value for key, value in self._row_metadata(saved).items())):
            raise ContractError("literature_reaction_semantic_saved_mismatch")
        def validate_published(kind, record):
            expected = identity(kind, {"origin": "tool", "record": record})
            actual = self.store.get(expected)
            if actual != {"id": expected, "record_type": kind, "origin": "tool", **record}:
                raise ContractError("literature_reaction_semantic_binding_mismatch")
            return expected
        expected_bindings = publish_meanings(saved["extraction"], validate_published)
        if expected_bindings != saved["semantic_bindings"]:
            raise ContractError("literature_reaction_semantic_binding_mismatch")
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


__all__ = ["LiteratureReactionRepository", "LiteratureReactionSemanticProjection", "COMPONENTS", "PROVIDER",
    "reaction_population_schema", "reaction_cells_schema", "reaction_semantic_cells_schema"]
