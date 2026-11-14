"""Persist selected source kinetic responses and forward exact saved cells.

This adapter authorizes source custody, not scientific curve interpretations.
It creates no controller observations or annotation credit. Replay consumes the
original committed sheets without source reacquisition or repeated arithmetic.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_quantity_storage import LiteratureQuantityRepository
from .literature_rate_storage import LiteratureRateRepository
from .literature_transport_calculations import COMPONENTS, populate_transport_response
from .literature_transport_inputs import read_transport_inputs, transport_response_population_schema


PROVIDER = "literature.experimental.transport_response"
FORMULA_CODES = {name: "transport_" + name + "_v1" for name in COMPONENTS}
BINDINGS = {"reported_subject_ref": "reference", "analyte_ref": "term",
            "test_curve_ref": "reference", "reference_curve_ref": "reference",
            "km_curve_ref": "reference"}
REASONS = ("concentration_unreported", "concentration_inputs_unreported",
           "concentration_not_supplied", "concentration_inputs_not_supplied",
           "kinetic_curve_identity_not_supplied", "primitive_covariance_not_supplied",
           "primitive_measurement_identity_not_supplied",
           "positive_concentration_required", "kinetic_curve_identity_unreported",
           "different_kinetic_curves", "observation_model_unspecified",
           "primitive_covariance_unreported", "primitive_measurement_identity_unreported",
           "primitive_variance_status_unknown", "numerical_model_range")
CONDITIONS = ("same_kinetic_curve", "michaelis_menten_response", "first_order_covariance_propagation")
SOURCE_KINDS = ("primary_source", "retained_extraction", "graph_extraction", "synthetic_fixture")
UNCERTAINTY_KINDS = ("unspecified", "unreported", "not_supplied")


def _quantity_key(extraction):
    anchor = {name: extraction["source"][name] for name in (
        "source_ref", "artifact_ref", "section_id", "paragraph_id", "expression_start", "expression_end")}
    anchor.update(quantity=extraction["quantity"], analyte=extraction["analyte"])
    encoded = json.dumps(anchor, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return "transport_quantity_" + hashlib.sha256(encoded).hexdigest()


class LiteratureTransportRepository(LiteratureRateRepository):
    provider = PROVIDER
    components = COMPONENTS
    record_version = "literature_transport_response_record_v2"
    readable_record_versions = ("literature_transport_response_record_v1", record_version)
    operations_table = "literature_transport_operations"
    received_table = "literature_transport_received"
    binding_fields = tuple(BINDINGS)

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
        row = self._provenance(context, reference)
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
        return row

    def _quantity(self, reference):
        """Validate an actual selected quantity and its saved operand bindings."""
        saved = LiteratureQuantityRepository(self.store, self.run_id).read(reference)
        extraction = saved["sheet"]["extraction"]
        if extraction["quantity"] != "apparent_km" or extraction["unit"] != "uM":
            raise ContractError("literature_transport_apparent_km_required")
        value = extraction["value"]
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ContractError("literature_transport_finite_km_required")
        if extraction["uncertainty"]["kind"] not in ("unspecified", "unreported"):
            raise ContractError("literature_transport_km_uncertainty_kind_unsupported")
        original = self.store.get(saved["input_source_ref"])
        if (original["record_type"] != "source"
                or original["artifact_ref"] != saved["input_artifact_ref"]
                or extraction["source"]["source_ref"] != original["id"]
                or extraction["source"]["artifact_ref"] != original["artifact_ref"]):
            raise ContractError("literature_transport_km_source_mismatch")
        for field, namespace, label in (
                ("reported_subject_ref", "reference", extraction["subject"]),
                ("analyte_ref", "term", extraction["analyte"])):
            bound = saved["experimental_bindings"][field]
            if label is None:
                if bound is not None:
                    raise ContractError("literature_transport_km_binding_mismatch")
            elif bound is None:
                raise ContractError("literature_transport_km_binding_mismatch")
            else:
                record = self.store.get(bound)
                if (record["record_type"] != namespace or record["source_ref"] != original["id"]
                        or record["label"] != label):
                    raise ContractError("literature_transport_km_binding_mismatch")
        return saved

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        validate_schema(args, transport_response_population_schema())
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

        source = self._source(context, args["source_ref"])
        km_payload = None

        def read_source(reference, representation):
            row = self._source(context, reference)
            artifact = row["artifact_ref"] if representation == "original" else row.get("text_ref")
            if artifact is None:
                raise ContractError("literature_source_representation_unavailable")
            return {"artifact_ref": artifact, "content": self.store.get_artifact(artifact)}

        def read_quantity(reference):
            nonlocal km_payload
            self._source(context, reference)
            km_payload = self._quantity(reference)
            extracted = km_payload["sheet"]["extraction"]
            for parent in self.store.get(reference)["parent_source_refs"]:
                self._provenance(context, parent)
            return {"sheet_ref": reference, "input_source_ref": km_payload["input_source_ref"],
                "value": extracted["value"], "unit": extracted["unit"], "origin": extracted["origin"],
                "reported_uncertainty_kind": extracted["uncertainty"]["kind"],
                "measurement_key": _quantity_key(extracted),
                **{field: km_payload["experimental_bindings"][field]
                   for field in ("reported_subject_ref", "analyte_ref")}}

        extraction = read_transport_inputs(args, read_source=read_source, read_quantity=read_quantity)
        direct = list(extraction["source_refs"])
        parents = list(direct)
        # Parent identities remain scoped provenance; their source bytes were
        # not read and therefore do not acquire fictitious direct receipts.
        for reference in direct:
            for parent in self.store.get(reference).get("parent_source_refs", ()):
                self._provenance(context, parent)
                parents.append(parent)
        parents = list(dict.fromkeys(parents))
        origin = {"synthetic_fixture": "synthetic", "graph_extraction": "graph_derived",
                  "retained_extraction": "derived", "primary_source": "reported"}[args["source_kind"]]
        sheet = populate_transport_response({**{name: extraction[name] for name in (
            "values", "curve_keys", "measurement_keys", "covariance", "variance_status", "observation_model")},
            "origin": origin})
        # The Km's saved native provenance is independent of the selected root's
        # representation; never relabel a reported quantity as a graph value.
        if extraction["km_quantity"] is not None:
            sheet["cells"]["apparent_km"]["origin"] = extraction["km_quantity"]["origin"]
        payload = {"version": self.record_version, "input_source_ref": args["source_ref"],
            "input_source_refs": parents, "direct_input_source_refs": direct,
            "input_artifact_ref": source["artifact_ref"], "extraction": extraction,
            "sheet": sheet, "km_payload": km_payload, "km_sheet_ref": args["km_sheet_ref"],
            "covariance_source_ref": args["covariance_source_ref"]}
        with self.store.transaction():
            created = []

            def publish(kind, record):
                candidate = identity(kind, {"origin": "tool", "record": record})
                existed = self.store.db.execute("SELECT 1 FROM records WHERE id=?", (candidate,)).fetchone()
                published = self.store.put(kind, record, origin="tool", scope=plain(context.scope))
                if existed is None:
                    created.append(published["id"])
                return published["id"]

            bindings = {field: extraction["km_quantity"][field] if extraction["km_quantity"] else None
                        for field in ("reported_subject_ref", "analyte_ref")}
            for role, field in (("substrate_test", "test_curve_ref"),
                                ("substrate_reference", "reference_curve_ref"), ("km", "km_curve_ref")):
                curve = extraction["curve_contexts"][role]
                bindings[field] = publish("reference", {"reference_type": "assay",
                    "source_ref": curve["curve"]["source_ref"],
                    "accession": extraction["curve_keys"][role], "label": curve["curve"]["quote"],
                    "sequence_ref": None, "molecule": None, "length": None,
                    "term_refs": [], "context_refs": []}) if curve else None
            payload["experimental_bindings"] = bindings
            artifact = self.store.artifact(canonical(payload), "application/json")
            request = self.store.artifact(canonical({"run_id": self.run_id,
                "episode_id": context.episode_id, "operation_key": operation_key,
                "arguments": args}), "application/json")
            sheet_ref = publish("source", {"provider": self.provider, "accession": None, "uri": None,
                "artifact_ref": artifact, "text_ref": artifact, "request_ref": request,
                "version": self.record_version, "retrieved_at": None, "parent_source_refs": parents})
            outcome = {"status": "completed", "operation_ref": identity("operation", {
                "run_id": self.run_id, "episode_id": context.episode_id, "key": operation_key}),
                "record_refs": list(dict.fromkeys([sheet_ref, *parents,
                    *(ref for ref in bindings.values() if ref)])), "changed_record_refs": created,
                "result": {"sheet_ref": sheet_ref, "cells": sheet["cells"],
                    "observation_model": extraction["observation_model"],
                    "variance_status": extraction["variance_status"],
                    "operand_source_kind": extraction["source_kind"],
                    "covariance_origin": extraction["covariance_origin"],
                    "reported_km_uncertainty_kind": extraction["km_quantity"]["reported_uncertainty_kind"]
                        if extraction["km_quantity"] else "not_supplied",
                    "evaluated_scope": "interpreted_source_kinetic_response"}, "feedback": None}
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def read(self, sheet_ref):
        saved = super().read(sheet_ref)
        source = self.store.get(sheet_ref)
        request = json.loads(self.store.get_artifact(source["request_ref"]))
        args = request["arguments"]
        if (source["version"] not in self.readable_record_versions or saved["km_sheet_ref"] != args["km_sheet_ref"]
                or saved["covariance_source_ref"] != args["covariance_source_ref"]
                or self.store.get(saved["input_source_ref"])["artifact_ref"] != saved["input_artifact_ref"]):
            raise ContractError("literature_transport_sheet_source_mismatch")
        km = self._quantity(saved["km_sheet_ref"]) if saved["km_sheet_ref"] is not None else None
        if saved["km_payload"] != km:
            raise ContractError("literature_transport_km_source_mismatch")
        for field in ("reported_subject_ref", "analyte_ref"):
            expected = km["experimental_bindings"][field] if km else None
            if saved["experimental_bindings"][field] != expected:
                raise ContractError("literature_transport_km_binding_mismatch")
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        components = self.components if components is None else components
        if (not isinstance(components, (list, tuple))
                or any(not isinstance(name, str) or name not in self.components for name in components)
                or len(set(components)) != len(components)):
            raise ContractError("literature_transport_component_selection_invalid")
        rows = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            saved = self.read(reference)
            extraction = saved["extraction"]
            for name in components:
                cell = {key: deepcopy(value) for key, value in saved["sheet"]["cells"][name].items()
                        if key != "formula"}
                rows.append({"sheet_ref": reference, "evidence_source_ref": saved["input_source_ref"],
                    "km_sheet_ref": saved["km_sheet_ref"], "covariance_source_ref": saved["covariance_source_ref"],
                    **saved["experimental_bindings"], "component": name, **cell,
                    "formula_code": FORMULA_CODES[name], "variance_status": extraction["variance_status"],
                    "observation_model": extraction["observation_model"],
                    "operand_source_kind": extraction["source_kind"],
                    "covariance_origin": extraction["covariance_origin"],
                    "reported_km_uncertainty_kind": extraction["km_quantity"]["reported_uncertainty_kind"]
                        if extraction["km_quantity"] else "not_supplied",
                    "evaluated_scope": "interpreted_source_kinetic_response"})
        validate_schema(rows, transport_response_cells_schema())
        return rows

    def validate_returned_values(self, cells, *, permitted_record_refs):
        validate_schema(cells, transport_response_cells_schema())
        super().validate_returned_values(cells, permitted_record_refs=permitted_record_refs)


def transport_response_cells_schema():
    """Closed typed numerical rows; scientific operands and hashes stay saved."""
    reference = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    properties = {"sheet_ref": dict(reference), "evidence_source_ref": dict(reference),
        **{field: {**reference, "type": ["string", "null"]}
           for field in ("km_sheet_ref", "covariance_source_ref")},
        **{field: {"type": ["string", "null"], "format": "reference", "x-reference-namespace": namespace}
           for field, namespace in BINDINGS.items()},
        "component": {"type": "string", "enum": list(COMPONENTS),
            "description": "condition_response is test substrate saturation divided by reference substrate "
                "saturation under the same fitted kinetic curve. It can divide an appropriate source effect "
                "once as a conditional response correction; it is not a reliability grade."},
        "value": {"type": ["number", "null"]},
        "unit": {"type": "string", "enum": ["uM", "dimensionless", "dimensionless_squared"]},
        "status": {"type": "string", "enum": ["populated", "unavailable"]},
        "formula_code": {"type": "string", "enum": list(FORMULA_CODES.values())},
        "origin": {"type": "string", "enum": ["reported", "derived", "graph_derived", "synthetic"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [None, *REASONS]},
        "conditional_on": {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "enum": list(CONDITIONS)}},
        "variance_status": {"type": "string", "enum": ["known", "estimated", "unknown"]},
        "observation_model": {"type": "string", "enum": ["michaelis_menten", "unknown"]},
        "operand_source_kind": {"type": "string", "enum": list(SOURCE_KINDS)},
        "covariance_origin": {"type": ["string", "null"], "enum": [None, "reported", "derived", "synthetic"]},
        "reported_km_uncertainty_kind": {"type": "string", "enum": list(UNCERTAINTY_KINDS)},
        "evaluated_scope": {"type": "string", "enum": ["interpreted_source_kinetic_response"]}}
    return {"type": "array", "items": obj(properties), "x-source": "literature_transport_cells"}


__all__ = ["LiteratureTransportRepository", "PROVIDER", "COMPONENTS", "FORMULA_CODES",
           "transport_response_cells_schema", "transport_response_population_schema"]
