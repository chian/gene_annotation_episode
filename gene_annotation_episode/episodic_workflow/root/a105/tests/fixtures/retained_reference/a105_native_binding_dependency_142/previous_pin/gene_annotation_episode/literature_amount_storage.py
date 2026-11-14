"""Selected source-amount persistence and exact typed subsets; no credit policy."""
from __future__ import annotations

import json

from .communication import plain
from .domain import ContractError, canonical, identity, obj
from .literature_amount_inputs import (
    ROLES, LITERAL_FIELDS, COMPARISON_KINDS, AMOUNT_ROLES, AMOUNT_KINDS, QUALIFICATIONS,
    RELATIONSHIPS, STOCK_RELATIONSHIPS, UNCERTAINTY_KINDS, read_amount_inputs,
    validate_amount_extraction, validate_amount_selection,
)
from .literature_amount_calculations import COMPONENTS, REASONS, populate_amount_components
from .literature_rate_storage import LiteratureRateRepository


PROVIDER = "literature.a105.amount_population"
VERSION = "literature_amount_population_record_v1"
RETURN_UNITS = {"(mg/ml)^2": "mg2/ml2", "(uM)^2": "uM2"}
CONDITIONS = ("source_role_and_pair_interpretations", "linear_covariance_propagation",
    "first_order_covariance_propagation", "same_stock_rate_with_total_mass_denominator_required_before_application")
_QUANTITY_REF_FIELDS = ("subject_ref", "construct_ref", "preparation_ref", "stock_ref", "method_ref",
    "reported_basis_ref", "condition_ref", "measurement_ref", "physical_observation_ref", "reported_uncertainty_ref")


def _bindings(extraction, publish):
    """Publish/validate exactly the same immutable source assertion records."""
    def reference(witness, kind, *, number=None):
        if witness is None:
            return None
        anchor = {key: witness[key] for key in ("source_ref", "artifact_ref", "start", "end", "quote")}
        if number is not None:
            selection = number["selector"]
            anchor.update(start=witness["start"] + len(witness["quote"][:selection["number_start"]].encode()),
                end=witness["start"] + len(witness["quote"][:selection["number_end"]].encode()), quote=number["raw_number"])
        return publish("reference", {"reference_type": "literature_result", "source_ref": witness["source_ref"],
            "accession": identity("amount_" + kind, witness if number is None else {"witness": witness, "number": number}),
            "label": witness["quote"] if number is None else number["raw_number"],
            "sequence_ref": None, "molecule": None, "length": None, "term_refs": [], "context_refs": [], "anchor": anchor})
    quantity_bindings = {}
    for role in ROLES:
        row = extraction["quantities"][role]
        meanings = row["meanings"] if row else {}
        bindings = {name + "_ref": reference(meanings.get(name), name)
            for name in ("subject", "construct", "preparation", "stock", "method", "reported_basis")}
        condition = meanings.get("condition")
        bindings["condition_ref"] = (publish("context", {"context_type": "assay_condition",
            "name": condition["quote"], "source_ref": condition["source_ref"], "attributes": [],
            "related_refs": list(dict.fromkeys(ref for ref in bindings.values() if ref))}) if condition else None)
        number = row["number"] if row else None
        bindings["measurement_ref"] = reference(number["selector"]["witness"], "measurement", number=number) if number else None
        bindings["physical_observation_ref"] = reference(meanings.get("measurement_identity"), "physical_observation")
        bindings["reported_uncertainty_ref"] = reference(row["reported_uncertainty"]["statement"], "reported_uncertainty") if row else None
        bindings.update({field: row[field]["value"] if row else "unknown"
            for field in ("amount_role", "amount_kind", "basis_status", "qualification")},
            approximate=row["approximate"] if row else False,
            reported_uncertainty_kind=row["reported_uncertainty"]["kind"]["value"] if row else "unknown")
        quantity_bindings[role] = bindings
    experimental = {"experiment_ref": reference(extraction["experiment"], "experiment"),
        "intended_change_ref": reference(extraction["intended_change"], "intended_change"),
        "covariance_source_ref": extraction["covariance_source"]["source_ref"] if extraction["covariance_source"] else None}
    return quantity_bindings, experimental


class LiteratureAmountRepository(LiteratureRateRepository):
    provider = PROVIDER
    components = COMPONENTS
    record_version = VERSION
    operations_table = "literature_amount_operations"
    received_table = "literature_amount_received"
    binding_fields = ()

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        signature = canonical({"arguments": args, "scope": plain(context.scope),
            "run_id": self.run_id, "episode_id": context.episode_id})
        old = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?", (self.run_id, context.episode_id, operation_key)).fetchone()
        if old is not None:
            if old["signature"] != signature:
                raise ContractError("operation_key_reused_for_different_work")
            outcome = json.loads(old["outcome"])
            saved = self.read(outcome["result"]["sheet_ref"])
            for reference in saved["direct_input_source_refs"]:
                self._native_source(context, reference)
            for reference in saved["input_source_refs"]:
                self._native_provenance(context.scope, reference)
            return outcome

        def read_source(reference, representation):
            source = self._native_source(context, reference)
            artifact = source["artifact_ref"] if representation == "original" else source.get("text_ref")
            if artifact is None:
                raise ContractError("literature_source_representation_unavailable")
            return {"artifact_ref": artifact, "content": self.store.get_artifact(artifact)}

        extraction = read_amount_inputs(args, read_source=read_source)
        sheet = populate_amount_components(extraction["calculation_inputs"])
        direct = list(extraction["source_refs"])
        parents, seen = list(direct), set(direct)
        for reference in parents:
            source = self._native_provenance(context.scope, reference)
            for ancestor in source.get("parent_source_refs", ()):
                self._native_provenance(context.scope, ancestor)
                if ancestor not in seen:
                    seen.add(ancestor)
                    parents.append(ancestor)
        source = self._native_source(context, args["source_ref"])
        payload = {"version": VERSION, "input_source_ref": args["source_ref"],
            "input_artifact_ref": source["artifact_ref"], "direct_input_source_refs": direct,
            "input_source_refs": parents, "selection": args, "extraction": extraction, "sheet": sheet}
        with self.store.transaction():
            created = []
            def publish(kind, value):
                key = identity(kind, {"origin": "tool", "record": value})
                exists = self.store.db.execute("SELECT 1 FROM records WHERE id=?", (key,)).fetchone()
                row = self.store.put(kind, value, origin="tool", scope=plain(context.scope))
                if exists is None:
                    created.append(row["id"])
                return row["id"]
            quantities, experimental = _bindings(extraction, publish)
            payload.update(quantity_bindings=quantities, experimental_bindings=experimental)
            artifact = self.store.artifact(canonical(payload), "application/json")
            request = self.store.artifact(canonical({"run_id": self.run_id, "episode_id": context.episode_id,
                "operation_key": operation_key, "arguments": args}), "application/json")
            sheet_ref = publish("source", {"provider": self.provider, "accession": None, "uri": None,
                "artifact_ref": artifact, "text_ref": artifact, "request_ref": request, "version": VERSION,
                "retrieved_at": None, "parent_source_refs": parents})
            refs = [sheet_ref, *dict.fromkeys(ref for bindings in quantities.values()
                for field, ref in bindings.items() if field in _QUANTITY_REF_FIELDS and ref),
                *[ref for ref in experimental.values() if ref]]
            outcome = {"status": "completed", "operation_ref": identity("operation", {
                "run_id": self.run_id, "episode_id": context.episode_id, "key": operation_key}),
                "record_refs": list(dict.fromkeys(refs)), "changed_record_refs": created,
                "result": {"sheet_ref": sheet_ref, "cells": sheet["cells"],
                    "comparison_kind": extraction["comparison_kind"]["value"],
                    "pair_relationship": extraction["pair_relationship"]["value"],
                    "stock_relationship": extraction["stock_relationship"]["value"],
                    "quantity_metadata": quantities,
                    "variance_status": sheet["variance_status"], "covariance_origin": sheet["covariance_origin"],
                    "mass_factor_applied_to_rate": False}, "feedback": None}
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def read(self, sheet_ref):
        source = self.store.get(sheet_ref)
        if (source["record_type"] != "source" or source.get("provider") != PROVIDER
                or source.get("version") != VERSION or source.get("origin") != "tool" or source.get("request_ref") is None):
            raise ContractError("literature_amount_sheet_required")
        request = json.loads(self.store.get_artifact(source["request_ref"]))
        if request.get("run_id") != self.run_id:
            raise ContractError("literature_amount_sheet_run_mismatch")
        row = self.store.db.execute(f"SELECT outcome FROM {self.operations_table} WHERE "
            "run_id=? AND episode_id=? AND operation_key=?", (self.run_id, request.get("episode_id"), request.get("operation_key"))).fetchone()
        outcome = json.loads(row["outcome"]) if row else None
        if outcome is None or outcome.get("result", {}).get("sheet_ref") != sheet_ref:
            raise ContractError("literature_sheet_not_selected_output")
        saved = json.loads(self.store.get_artifact(source["artifact_ref"]))
        if (set(saved) != {"version", "input_source_ref", "input_artifact_ref", "direct_input_source_refs",
                "input_source_refs", "selection", "extraction", "sheet", "quantity_bindings", "experimental_bindings"}
                or saved["version"] != VERSION or saved["selection"] != request.get("arguments")
                or saved["input_source_ref"] != saved["selection"].get("source_ref")
                or source.get("parent_source_refs") != saved["input_source_refs"]
                or outcome["result"].get("cells") != saved["sheet"]["cells"]
                or saved["sheet"]["inputs"] != saved["extraction"]["calculation_inputs"]):
            raise ContractError("literature_amount_saved_mismatch")
        extraction = validate_amount_extraction(saved["extraction"])
        validate_amount_selection(saved["selection"], extraction)
        if extraction["source_refs"] != saved["direct_input_source_refs"]:
            raise ContractError("literature_amount_saved_mismatch")
        root = self.store.get(saved["input_source_ref"])
        if root["artifact_ref"] != saved["input_artifact_ref"]:
            raise ContractError("literature_amount_source_mismatch")
        def witnesses(value):
            if isinstance(value, dict):
                if set(value) == {"source_ref", "representation", "artifact_ref", "start", "end", "quote"}:
                    yield value
                else:
                    for child in value.values():
                        yield from witnesses(child)
            elif isinstance(value, list):
                for child in value:
                    yield from witnesses(child)
        for witness in witnesses(extraction):
            row = self.store.get(witness["source_ref"])
            actual = row["artifact_ref"] if witness["representation"] == "original" else row.get("text_ref")
            if actual != witness["artifact_ref"] or witness["source_ref"] not in saved["direct_input_source_refs"]:
                raise ContractError("literature_amount_source_mismatch")
        covariance = extraction["covariance_source"]
        if covariance is not None and self.store.get(covariance["source_ref"])["artifact_ref"] != covariance["artifact_ref"]:
            raise ContractError("literature_amount_source_mismatch")
        def expected(kind, value):
            reference = identity(kind, {"origin": "tool", "record": value})
            actual = self.store.get(reference)
            if actual.get("record_type") != kind or actual.get("origin") != "tool" or any(actual.get(key) != child for key, child in value.items()):
                raise ContractError("literature_amount_binding_mismatch")
            return reference
        quantities, experimental = _bindings(extraction, expected)
        if quantities != saved["quantity_bindings"] or experimental != saved["experimental_bindings"]:
            raise ContractError("literature_amount_binding_mismatch")
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = self.components if components is None else components
        if (not isinstance(selected, (tuple, list)) or len(selected) != len(set(selected))
                or any(name not in self.components for name in selected)):
            raise ContractError("literature_amount_component_selection_invalid")
        result = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            saved = self.read(reference)
            extraction = saved["extraction"]
            for component in selected:
                cell = saved["sheet"]["cells"][component]
                roles = ("numerator",) if component == "numerator_amount" else ("denominator",) if component == "denominator_amount" else ROLES
                result.append({"sheet_ref": reference, "evidence_source_ref": saved["input_source_ref"],
                    **saved["experimental_bindings"], "component": component,
                    **{field: cell[field] for field in ("value", "unit", "status", "origin", "unavailable_reason", "conditional_on", "approximate")},
                    "threshold": cell.get("threshold"), "bound": cell.get("bound", "none"),
                    "evaluation_scope": "source_amount_comparison",
                    **{field: extraction[field]["value"] for field in ("comparison_kind", "pair_relationship", "stock_relationship")},
                    "variance_status": saved["sheet"]["variance_status"], "covariance_origin": saved["sheet"]["covariance_origin"],
                    **{role: saved["quantity_bindings"][role] for role in ROLES},
                    "input_measurement_refs": list(dict.fromkeys(saved["quantity_bindings"][role]["measurement_ref"]
                        for role in roles if saved["quantity_bindings"][role]["measurement_ref"])),
                    "mass_factor_applied_to_rate": False})
                result[-1]["unit"] = RETURN_UNITS.get(cell["unit"], cell["unit"])
        return result


def amount_cells_schema():
    def reference(namespace, nullable=True):
        return {"type": ["string", "null"] if nullable else "string", "format": "reference", "x-reference-namespace": namespace}
    quantity = obj({**{name: reference("context" if name == "condition_ref" else "reference") for name in _QUANTITY_REF_FIELDS},
        "amount_role": {"enum": list(AMOUNT_ROLES)}, "amount_kind": {"enum": list(AMOUNT_KINDS)},
        "basis_status": {"enum": list(RELATIONSHIPS)}, "qualification": {"enum": list(QUALIFICATIONS)},
        "approximate": {"type": "boolean"}, "reported_uncertainty_kind": {"enum": list(UNCERTAINTY_KINDS)}})
    schema = {"type": "array", "items": obj({"sheet_ref": reference("source", False),
        "evidence_source_ref": reference("source", False), "experiment_ref": reference("reference"),
        "intended_change_ref": reference("reference"), "covariance_source_ref": reference("source"),
        "component": {"enum": list(COMPONENTS)}, "value": {"type": ["number", "null"]},
        "threshold": {"type": ["number", "null"]}, "bound": {"enum": ["none", "lt", "le", "gt", "ge"]},
        "unit": {"enum": ["mg/ml", "uM", "mg2/ml2", "uM2", "dimensionless", None]},
        "status": {"enum": ["populated", "unavailable"]}, "origin": {"enum": ["reported", "derived", "synthetic"]},
        "unavailable_reason": {"enum": [*REASONS, None]},
        "conditional_on": {"type": "array", "uniqueItems": True, "items": {"enum": list(CONDITIONS)}},
        "approximate": {"type": "boolean"}, "evaluation_scope": {"const": "source_amount_comparison"},
        "comparison_kind": {"enum": list(COMPARISON_KINDS)}, "pair_relationship": {"enum": list(RELATIONSHIPS)},
        "stock_relationship": {"enum": list(STOCK_RELATIONSHIPS)}, "variance_status": {"enum": ["known", "estimated", "unknown"]},
        "covariance_origin": {"enum": ["reported", "derived", "synthetic", None]},
        "numerator": quantity, "denominator": json.loads(json.dumps(quantity)),
        "input_measurement_refs": {"type": "array", "uniqueItems": True, "items": reference("reference", False)},
        "mass_factor_applied_to_rate": {"const": False}}), "x-source": "literature_amount_cells"}
    # The application return boundary requires explicit types even for closed
    # enums/consts. All enum codes here are strings with declared nullable cases.
    def typed(node):
        if not isinstance(node, dict):
            return
        if "enum" in node and "type" not in node:
            node["type"] = ["string", "null"] if None in node["enum"] else "string"
        if "const" in node and "type" not in node:
            node["type"] = "boolean" if type(node["const"]) is bool else "string"
        for child in node.get("properties", {}).values():
            typed(child)
        if "items" in node:
            typed(node["items"])
    typed(schema)
    return schema


__all__ = ["PROVIDER", "VERSION", "COMPONENTS", "LiteratureAmountRepository", "amount_cells_schema"]
