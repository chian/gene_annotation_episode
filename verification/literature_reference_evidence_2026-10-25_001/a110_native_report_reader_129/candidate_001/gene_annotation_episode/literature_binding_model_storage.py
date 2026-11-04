"""Persist explicitly selected, conditional binding-model source components.

Custody checks establish which received artifacts supplied a calculation; they
do not establish that a paper justifies its declared observation model. Saved
projection and replay copy the original result without scientific rereading.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .communication import plain
from .domain import ContractError, NULL_REF, REF, canonical, identity, obj, validate_schema
from .literature_assay_inputs import _Sources, _witness_schema
from .literature_binding_model_inputs import read_binding_model
from .literature_binding_models import (
    COMPONENTS, CONDITIONAL_CODES, FORMULAS, REASONS,
    binding_model_operand_keys, populate_binding_model,
)
from .literature_binding_storage import (
    ARRANGEMENTS, BINDINGS, DESIGNS, PARAMETER_KINDS, LiteratureBindingRepository,
)


PROVIDER = "literature.experimental.binding_model"
FORMULA_CODES = {name: "binding_model_" + name + "_v1" for name in COMPONENTS}
FORMULA_MEANINGS = {FORMULA_CODES[name]: FORMULAS[name] for name in COMPONENTS}


def binding_model_population_schema():
    """Select retained inputs; no numerical model operands are tool arguments."""
    return obj({"source_ref": deepcopy(REF), "model_source_ref": deepcopy(NULL_REF),
        "model_witnesses": {"type": "array", "items": _witness_schema()}})


def _model_metadata(sheet):
    model = sheet["model"]
    return {
        "model_kind": "known_normal_log_parameters" if model is not None else "unreported",
        "variance_status": model["variance_status"] if model is not None else "not_supplied",
        "censoring_model": model["censoring_model"] if model is not None else "not_supplied",
        "model_origin": model["origin"] if model is not None else "not_supplied",
    }


class LiteratureBindingModelRepository(LiteratureBindingRepository):
    provider = PROVIDER
    components = COMPONENTS
    record_version = "literature_binding_model_record_v1"
    operations_table = "literature_binding_model_operations"
    received_table = "literature_binding_model_received"

    def _binding(self, reference):
        # The ordinary binding repository checks its actual operation receipt,
        # run, version and source parents. A provider label alone is insufficient.
        return LiteratureBindingRepository(self.store, self.run_id).read(reference)

    def _provenance(self, context, reference):
        # A received committed sheet supplies these original source identities.
        # Requiring raw-source receipt would turn copying its saved numerical
        # operands into hidden reacquisition of an earlier investigation.
        if not self.store.reference_subset([reference], plain(context.scope)):
            raise ContractError("literature_source_outside_scope")
        row = self.store.get(reference)
        if row["record_type"] != "source":
            raise ContractError("literature_source_required")
        return row

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        validate_schema(args, binding_model_population_schema())
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
        binding = self._binding(source["id"])
        parents = [source["id"], *binding["input_source_refs"]]
        direct = [source["id"]]
        for reference in binding["input_source_refs"]:
            self._provenance(context, reference)

        model_source = None
        if args["model_source_ref"] is not None:
            model_source = self._source(context, args["model_source_ref"])
            parents.append(model_source["id"])
            direct.append(model_source["id"])
            for reference in model_source.get("parent_source_refs", ()):
                self._source(context, reference)
                parents.append(reference)
                direct.append(reference)
            if not args["model_witnesses"]:
                raise ContractError("binding_model_witness_required")

        def read_source(reference, representation):
            row = self._source(context, reference)
            artifact = row["artifact_ref"] if representation == "original" else row.get("text_ref")
            if artifact is None:
                raise ContractError("literature_source_representation_unavailable")
            return {"artifact_ref": artifact, "content": self.store.get_artifact(artifact)}

        sources = _Sources(read_source)
        witnesses = [sources.witness(item, f"model_witnesses[{index}]")
                     for index, item in enumerate(args["model_witnesses"])]
        parents.extend(sources.references)
        direct.extend(sources.references)
        # Witness source parents are custody too, even if their bytes were not
        # used by the selected literal span.
        for reference in sources.references:
            for parent in self.store.get(reference).get("parent_source_refs", ()):
                self._provenance(context, parent)
                parents.append(parent)

        model, provenance = None, None
        if model_source is not None:
            parsed = read_binding_model({"source_ref": model_source["id"],
                "artifact_ref": model_source["artifact_ref"],
                "content": self.store.get_artifact(model_source["artifact_ref"])},
                parameter_kind=binding["sheet"]["parameter_kind"],
                measurement_keys=binding_model_operand_keys(binding["sheet"]))
            model, provenance = parsed["model"], parsed["source"]
        sheet = populate_binding_model(binding["sheet"], model)
        payload = {"version": self.record_version, "input_source_ref": source["id"],
            "input_source_refs": list(dict.fromkeys(parents)), "input_artifact_ref": source["artifact_ref"],
            "direct_input_source_refs": list(dict.fromkeys(direct)),
            "sheet": sheet, "binding_sheet": binding["sheet"],
            "experimental_bindings": binding["experimental_bindings"],
            "original_evidence_source_ref": binding["input_source_ref"],
            "model_source_ref": args["model_source_ref"], "model_source_provenance": provenance,
            "model_witnesses": witnesses, "comparison": binding["comparison"]}
        with self.store.transaction():
            artifact = self.store.artifact(canonical(payload), "application/json")
            request = self.store.artifact(canonical({"run_id": self.run_id,
                "episode_id": context.episode_id, "operation_key": operation_key,
                "arguments": args}), "application/json")
            record = {"provider": self.provider, "accession": None, "uri": None,
                "artifact_ref": artifact, "text_ref": artifact, "request_ref": request,
                "version": self.record_version, "retrieved_at": None,
                "parent_source_refs": payload["input_source_refs"]}
            candidate = identity("source", {"origin": "tool", "record": record})
            existed = self.store.db.execute("SELECT 1 FROM records WHERE id=?", (candidate,)).fetchone()
            published = self.store.put("source", record, origin="tool", scope=plain(context.scope))
            sheet_ref = published["id"]
            outcome = {"status": "completed", "operation_ref": identity("operation", {
                "run_id": self.run_id, "episode_id": context.episode_id, "key": operation_key}),
                "record_refs": list(dict.fromkeys([sheet_ref, *payload["input_source_refs"],
                    *(ref for ref in payload["experimental_bindings"].values() if ref)])),
                "changed_record_refs": [] if existed is not None else [sheet_ref],
                "result": {"sheet_ref": sheet_ref, "evidence_source_ref": source["id"],
                    "original_evidence_source_ref": payload["original_evidence_source_ref"],
                    "model_source_ref": payload["model_source_ref"], "cells": sheet["cells"],
                    "parameter_kind": sheet["parameter_kind"],
                    "contrast_meaning": sheet["contrast_meaning"], **_model_metadata(sheet),
                    **{field: sheet[field] for field in ("source_uncertainty_basis",
                        "minimum_experiment_count", "independent_preparation_count")}},
                "feedback": None}
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def read(self, sheet_ref):
        saved = super().read(sheet_ref)
        binding = self._binding(saved["input_source_ref"])
        if (saved["original_evidence_source_ref"] != binding["input_source_ref"]
                or saved["experimental_bindings"] != binding["experimental_bindings"]
                or saved["comparison"] != binding["comparison"]
                or saved["binding_sheet"] != binding["sheet"]):
            raise ContractError("literature_binding_model_source_mismatch")
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        components = self.components if components is None else components
        if (not isinstance(components, (list, tuple))
                or any(not isinstance(name, str) or name not in self.components for name in components)
                or len(set(components)) != len(components)):
            raise ContractError("literature_binding_model_component_selection_invalid")
        result = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            saved = self.read(reference)
            sheet = saved["sheet"]
            for name in components:
                cell = {key: deepcopy(value) for key, value in sheet["cells"][name].items() if key != "formula"}
                result.append({"sheet_ref": reference, "evidence_source_ref": saved["input_source_ref"],
                    "original_evidence_source_ref": saved["original_evidence_source_ref"],
                    "model_source_ref": saved["model_source_ref"], **saved["experimental_bindings"],
                    "component": name, **cell, "formula_code": FORMULA_CODES[name],
                    "parameter_kind": sheet["parameter_kind"], "contrast_meaning": sheet["contrast_meaning"],
                    "evaluated_scope": "interpreted_source_parameter_contrast", **_model_metadata(sheet),
                    **{field: sheet[field] for field in ("source_uncertainty_basis",
                        "minimum_experiment_count", "independent_preparation_count")},
                    **{field: saved["comparison"][field] for field in ("design", "protein_arrangement")}})
        return result


def binding_model_cells_schema():
    """Closed parent rows omit host-only covariance, hashes and diagnostics."""
    reference = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    properties = {**{field: dict(reference) for field in (
        "sheet_ref", "evidence_source_ref", "original_evidence_source_ref")},
        "model_source_ref": {**reference, "type": ["string", "null"]},
        **{field: {"type": ["string", "null"], "format": "reference",
                  "x-reference-namespace": "reference"} for field in BINDINGS},
        "component": {"type": "string", "enum": list(COMPONENTS)},
        "value": {"type": ["number", "null"]},
        "relation": {"type": "string", "enum": ["eq", "gt", "ge", "lt", "le", "unreported"]},
        "unit": {"type": "string", "enum": ["dimensionless", "log_parameter_squared"]},
        "status": {"type": "string", "enum": ["populated", "reported_limit", "unavailable", "conflicting"]},
        "formula_code": {"type": "string", "enum": list(FORMULA_CODES.values())},
        "origin": {"type": "string", "enum": ["derived", "proposed"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [None, *REASONS]},
        "bound_kind": {"type": ["string", "null"], "enum": [None, "reported_limit_arithmetic"]},
        "confidence_bound": {"type": "null"}, "parameter_identification_bound": {"type": "null"},
        "conditional_on": {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "enum": list(CONDITIONAL_CODES)}},
        "parameter_kind": {"type": "string", "enum": list(PARAMETER_KINDS)},
        "contrast_meaning": {"type": "string", "enum": ["test_parameter_exceeds_reference"]},
        "evaluated_scope": {"type": "string", "enum": ["interpreted_source_parameter_contrast"]},
        "model_kind": {"type": "string", "enum": ["unreported", "known_normal_log_parameters"]},
        "variance_status": {"type": "string", "enum": ["not_supplied", "known", "estimated", "unknown"]},
        "censoring_model": {"type": "string", "enum": ["not_supplied", "none", "threshold_of_log_estimate", "unknown"]},
        "model_origin": {"type": "string", "enum": ["not_supplied", "reported", "derived", "synthetic"]},
        "source_uncertainty_basis": {"type": "string", "enum": ["fit_to_averaged_curve", "between_independent_fitted_parameters", "unknown"]},
        "minimum_experiment_count": {"type": ["integer", "null"], "minimum": 1},
        "independent_preparation_count": {"type": "null"},
        "design": {"type": "string", "enum": list(DESIGNS)},
        "protein_arrangement": {"type": "string", "enum": list(ARRANGEMENTS)}}
    return {"type": "array", "items": obj(properties), "x-source": "literature_binding_model_cells"}


__all__ = ["LiteratureBindingModelRepository", "PROVIDER", "COMPONENTS", "FORMULA_CODES",
           "FORMULA_MEANINGS", "binding_model_population_schema", "binding_model_cells_schema"]
