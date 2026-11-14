"""Selected source-native numerical extraction, using ordinary source custody.

This finite route retains reported quantities, not an inferred biochemical
experiment model. Conditions and quantitative attribution remain unresolved.
"""
from __future__ import annotations

import json
import math

from .communication import plain
from .domain import ContractError, REF, canonical, identity, obj
from .literature_rate_storage import LiteratureRateRepository

PROVIDER = "literature.a105.source_quantity"
COMPONENTS = ("reported_value", "reported_spread", "relative_reported_spread",
              "corrected_activity", "effect_variance", "effect_standard_uncertainty",
              "effect_precision", "source_profile_log_ratio", "source_presence_index")
REASONS = ("quantity_not_activity_rate", "reported_spread_unavailable", "zero_reported_value", "numerical_model_range",
           "correction_inputs_unreported", "primitive_covariance_unreported",
           "distinct_residual_variance_unreported", "invalid_propagated_variance",
           "positive_effect_variance_required", "known_variance_required",
           "observation_model_unspecified")
BINDINGS = {"reported_subject_ref": "reference", "experiment_ref": "reference",
            "condition_ref": "context", "endpoint_ref": "term", "normalization_ref": "term",
            "quantity_ref": "term", "analyte_ref": "term"}


class LiteratureQuantityRepository(LiteratureRateRepository):
    provider = PROVIDER
    components = COMPONENTS
    record_version = "literature_source_quantity_record_v1"
    operations_table = "literature_quantity_operations"
    received_table = "literature_quantity_received"
    binding_fields = tuple(BINDINGS)

    def populate(self, context, arguments, operation_key):
        from .literature_activity_calculations import populate_corrected_activity
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        from .domain import validate_schema
        validate_schema(args, quantity_population_schema())
        source_ref = args["source_ref"]
        if source_ref not in context.received_record_refs:
            raise ContractError("literature_source_not_received")
        if not self.store.reference_subset([source_ref], plain(context.scope)):
            raise ContractError("literature_source_outside_scope")
        signature = canonical({"arguments": args, "scope": plain(context.scope)})
        saved = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, context.episode_id, operation_key)).fetchone()
        if saved:
            if saved["signature"] != signature:
                raise ContractError("operation_key_reused_for_different_work")
            return json.loads(saved["outcome"])
        source = self.store.get(source_ref)
        if source["record_type"] != "source":
            raise ContractError("literature_source_required")
        artifact = source["artifact_ref"]
        try:
            source_text = self.store.get_artifact(artifact).decode("utf-8")
        except UnicodeDecodeError as error:
            code = ("literature_utf8_html_required" if args["source_kind"] == "primary_html"
                    else "literature_utf8_jats_required")
            raise ContractError(code) from error
        if args["source_kind"] == "primary_html":
            from .literature_html_quantity_reader import read_html_quantity
            reader, text_field = read_html_quantity, "html"
        else:
            from .literature_prose_reader import read_jats_quantity
            reader, text_field = read_jats_quantity, "xml"
        extracted = reader({"source_ref": source_ref, "artifact_ref": artifact,
            text_field: source_text, "representation": args["source_kind"]},
            section_id=args["section_id"], paragraph_id=args["paragraph_id"],
            expected_subject=args["subject"], quantity=args["quantity"], analyte=args["analyte"])
        # A reported specific activity is already normalized. It cannot silently
        # populate unnormalized q, protein concentration E, or product identity.
        correction = populate_corrected_activity({"values": dict.fromkeys(("q", "g", "k", "E", "u", "v")),
            "covariance": None, "variance_status": "unknown", "distinct_residual_variance": None,
            "observation_model": "none"})
        if extracted["quantity"] != "specific_activity":
            for numeric_cell in correction["cells"].values():
                numeric_cell["unavailable_reason"] = "quantity_not_activity_rate"
        def cell(value, unit, formula, reason=None, origin=None):
            return {"value": value, "unit": unit, "status": "populated" if value is not None else "unavailable",
                "formula": formula, "origin": origin or extracted["origin"],
                "unavailable_reason": reason, "conditional_on": []}
        value, spread = extracted["value"], extracted["uncertainty"]["magnitude"]
        reason = "reported_spread_unavailable" if spread is None else "zero_reported_value" if value == 0 else None
        relative = spread / abs(value) if reason is None else None
        if relative is not None and not math.isfinite(relative):
            relative, reason = None, "numerical_model_range"
        cells = {"reported_value": cell(value, extracted["unit"], "literal_source_value_with_explicit_unit_conversion"),
            "reported_spread": cell(spread, extracted["unit"], "literal_source_plus_minus_spread",
                "reported_spread_unavailable" if spread is None else None),
            "relative_reported_spread": cell(relative, "dimensionless", "reported_spread/abs(reported_value)",
                reason, "derived"), **correction["cells"]}
        payload = {"version": self.record_version, "input_source_ref": source_ref,
            "input_artifact_ref": artifact, "sheet": {"axis": "A105", "scope": "reported_source_quantity",
            "extraction": extracted, "cells": cells, "correction": correction,
            "annotation_credit": None, "source_conditions": None,
            "interpretation_limits": ["subject_token_presence_is_not_experimental_attribution",
                "reported_specific_activity_does_not_establish_product_identity",
                "reported_spread_with_unspecified_meaning_is_not_SEM_or_SD",
                "apparent_km_is_not_affinity_or_an_activity_rate"]}}
        with self.store.transaction():
            newly_created = []
            def publish(kind, record):
                candidate = identity(kind, {"origin": "tool", "record": record})
                existed = self.store.db.execute("SELECT 1 FROM records WHERE id=?", (candidate,)).fetchone()
                result = self.store.put(kind, record, origin="tool", scope=plain(context.scope))
                if existed is None:
                    newly_created.append(result["id"])
                return result["id"]
            def reference(label, key):
                return publish("reference", {"reference_type": "literature_result", "source_ref": source_ref,
                    "accession": identity(key, {"source": source_ref, "label": label}), "label": label,
                    "sequence_ref": None, "molecule": None, "length": None, "term_refs": [], "context_refs": []})
            def term(label, kind):
                return publish("term", {"namespace": "literature_" + kind,
                    "accession": identity(kind, {"source": source_ref, "label": label}),
                    "label": label, "term_type": "other", "source_ref": source_ref, "anchor": None})
            bindings = {"reported_subject_ref": reference(extracted["subject"], "source_subject_token"),
                "experiment_ref": None,
                "condition_ref": None, "endpoint_ref": term("reported " + extracted["quantity"], "endpoint"),
                "normalization_ref": term(extracted["normalization"], "normalization"),
                "quantity_ref": term(extracted["quantity"], "quantity"),
                "analyte_ref": term(extracted["analyte"], "analyte") if extracted["analyte"] else None}
            payload["experimental_bindings"] = bindings
            sheet_artifact = self.store.artifact(canonical(payload), "application/json")
            request = self.store.artifact(canonical({"run_id": self.run_id, "episode_id": context.episode_id,
                "operation_key": operation_key, "arguments": args}), "application/json")
            sheet_ref = publish("source", {"provider": self.provider, "accession": None, "uri": None,
                "artifact_ref": sheet_artifact, "text_ref": sheet_artifact, "request_ref": request,
                "version": self.record_version, "retrieved_at": None, "parent_source_refs": [source_ref]})
            outcome = {"status": "completed", "operation_ref": identity("operation", {
                "run_id": self.run_id, "episode_id": context.episode_id, "key": operation_key}),
                "record_refs": [sheet_ref, *dict.fromkeys(ref for ref in bindings.values() if ref)],
                "changed_record_refs": newly_created, "result": {"sheet_ref": sheet_ref, "cells": cells,
                    "subject": extracted["subject"], "quantity": extracted["quantity"], "analyte": extracted["analyte"],
                    "source_uncertainty": extracted["uncertainty"], "text": extracted["source"]["paragraph_text"],
                    **{key: extracted["source"][key] for key in ("source_ref", "artifact_ref", "section_id",
                        "paragraph_id", "expression_start", "expression_end")},
                    "coordinate_unit": "paragraph_unicode_characters"}, "feedback": None}
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        rows = super().project_cells(sheet_refs, permitted_record_refs=permitted_record_refs, components=components)
        for row in rows:
            extracted = self.read(row["sheet_ref"])["sheet"]["extraction"]
            row["reported_uncertainty_kind"] = extracted["uncertainty"]["kind"]
        return rows


def quantity_population_schema():
    text = {"type": "string", "minLength": 1}
    return obj({"source_ref": REF, "source_kind": {"enum": ["primary_jats", "primary_html", "synthetic_fixture"]},
        **{field: dict(text) for field in ("section_id", "paragraph_id", "subject")},
        "quantity": {"enum": ["specific_activity", "apparent_km"]},
        "analyte": {"type": ["string", "null"], "minLength": 1}})


def quantity_cells_schema():
    reference = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    properties = {"sheet_ref": dict(reference),
        "evidence_source_ref": dict(reference),
        "component": {"type": "string", "enum": list(COMPONENTS)}, "value": {"type": ["number", "null"]},
        "unit": {"type": "string", "enum": ["umol/min/mg", "uM", "dimensionless", "per_min", "per_min_squared", "min_squared"]},
        "status": {"type": "string", "enum": ["populated", "unavailable"]},
        "origin": {"type": "string", "enum": ["reported", "synthetic", "derived", "proposed"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [None, *REASONS]},
        "conditional_on": {"type": "array", "uniqueItems": True, "items": {"type": "string", "enum": [
            "first_order_covariance_propagation", "known_variance", "known_normal_nonnegative_presence"]}},
        "reported_uncertainty_kind": {"type": "string", "enum": ["unspecified", "unreported"]}}
    for field, namespace in BINDINGS.items():
        properties[field] = {"type": ["string", "null"], "format": "reference", "x-reference-namespace": namespace}
    return {"type": "array", "items": obj(properties), "x-source": "literature_quantity_cells"}
