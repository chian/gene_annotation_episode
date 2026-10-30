"""Selected immutable figure sheets and exact typed receipt projection.

Custody validates retained source records; it does not establish the truth of
supplied experimental interpretations. Saved reads never reopen source bytes or
repeat digitization. Ordinary episode accounting belongs to the caller.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_assay_inputs import SOURCE_KINDS
from .literature_figure_inputs import (
    COMPONENTS, LITERAL_FIELDS, REASONS, figure_population_schema, read_figure_inputs,
)
from .literature_rate_storage import LiteratureRateRepository


PROVIDER = "literature.experimental.figure"
FORMULA_CODES = {
    "first_ordinate": "native_first_bar_linear_v1",
    "second_ordinate": "native_second_bar_linear_v1",
    "ordinate_difference": "native_first_minus_second_v1",
}
BINDINGS = {
    "first_subject_ref": ("first_subject", "reference"),
    "first_partner_ref": ("first_partner", "reference"),
    "second_subject_ref": ("second_subject", "reference"),
    "second_partner_ref": ("second_partner", "reference"),
    "experiment_ref": ("experiment", "reference"),
    "endpoint_ref": ("endpoint", "term"),
    "first_condition_ref": ("first_condition", "context"),
    "second_condition_ref": ("second_condition", "context"),
    "normalization_ref": ("normalization", "term"),
    "function_ref": ("function", "term"),
}
NATIVE_UNITS = ("relative_turnover_percent", "arbitrary_signal", "nanomolar")
BOUND_KIND = "conditional_digitization_not_confidence_interval"
_FIXED_METADATA = {
    "evaluation_scope": "reference_experimental_figure_ordinates",
    "statistical_uncertainty": "not_extracted",
    "measurement_corrections": "not_applied",
    "target_correspondence": "not_evaluated",
    "partner_necessity": "not_evaluated",
}


def _repeat_schema():
    return obj({"reported_n": {"type": ["integer", "null"], "minimum": 1},
        "repeat_kind": {"type": "string", "enum": ["biological", "technical", "unknown"]},
        "independent_preparation_count": {"type": ["integer", "null"], "minimum": 1},
        "spread_kind": {"type": "string", "enum": ["SD", "SEM", "CI", "unspecified", "unreported"]},
        "spread_numeric_status": {"type": "string", "enum": ["not_extracted", "unreported"]}})


def _design_schema():
    return obj({
        "arrangement": {"type": "string", "enum": ["coexisting_sequential_catalysts", "coexisting_complex",
            "single_molecule", "unresolved"]},
        "contrast_kind": {"type": "string", "enum": ["source_representation", "partner_swap", "other", "unreported"]},
        "endpoint_scope": {"type": "string", "enum": ["coupled_final_product", "direct_subject_step", "binding",
            "indirect_response", "unreported"]},
        "normalization_basis": {"type": "string", "enum": ["reported_relative_turnover", "arbitrary_signal",
            "concentration", "unreported"]},
        "measurement_relation": {"type": "string", "enum": ["same_physical_measurement",
            "distinct_physical_measurements", "unresolved"]},
        "first_repeat": _repeat_schema(),
        "second_repeat": {**_repeat_schema(), "type": ["object", "null"]}})


def _cell_schema():
    return obj({**{field: {"type": ["number", "null"]} for field in ("value", "lower", "upper")},
        "unit": {"type": ["string", "null"], "enum": [*NATIVE_UNITS, "relative_turnover_percentage_points", None]},
        "origin": {"type": "string", "enum": ["graph_derived", "derived"]},
        "bound_kind": {"type": "string", "enum": [BOUND_KIND]},
        "status": {"type": "string", "enum": ["populated", "unavailable"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [None, *REASONS]}})


def _metadata(extraction):
    recipe = extraction["recipe"]
    first, second = recipe["first"], recipe["second"]
    return {**_FIXED_METADATA, "source_kind": extraction["arguments"]["source_kind"],
        "first_image_origin": first["image_origin"],
        "second_image_origin": second["image_origin"] if second else None,
        "design": deepcopy(recipe["design"]),
        "first_axis_unit": first["selection"]["calibration"]["unit"],
        "second_axis_unit": second["selection"]["calibration"]["unit"] if second else None}


def _direct_references(args, recipe):
    images = [recipe["first"]["image_source_ref"]]
    if recipe["second"] is not None:
        images.append(recipe["second"]["image_source_ref"])
    return list(dict.fromkeys([args["source_ref"], args["data_source_ref"], *images,
        *(args["literals"][field]["source_ref"] for field in LITERAL_FIELDS
          if args["literals"][field] is not None),
        *(entry["source_ref"] for entry in args["interpretation_witnesses"])]))


def _binding_record(literal, kind, entry):
    witness = entry["witness"]
    anchor = {name: witness[name] for name in ("source_ref", "artifact_ref", "start", "end", "quote")}
    common = {"source_ref": witness["source_ref"], "anchor": anchor}
    # Even two identical selected spans retain their separate scientific roles.
    accession = identity("figure_literal", {"field": literal, **anchor})
    if kind == "reference":
        return {**common, "reference_type": "assay", "accession": accession,
            "label": entry["value"], "sequence_ref": None, "molecule": None,
            "length": None, "term_refs": [], "context_refs": []}
    if kind == "term":
        return {**common, "namespace": "literature_figure_" + literal,
            "accession": accession, "label": entry["value"], "term_type": "other"}
    # Context has no accession field; an anchored role record preserves field
    # identity without changing the source's literal name.
    role = _condition_role(literal, entry)
    return {**common, "context_type": "assay_condition", "name": entry["value"],
        "attributes": [], "related_refs": [identity("reference", {"origin": "tool", "record": role})]}


def _condition_role(literal, entry):
    return _binding_record(literal, "reference", entry)


def _condition_refs(extraction):
    return [identity("reference", {"origin": "tool", "record": _condition_role(literal, entry)})
        for literal, kind in BINDINGS.values() if kind == "context"
        and (entry := extraction["literals"][literal]) is not None]


class LiteratureFigureRepository(LiteratureRateRepository):
    provider = PROVIDER
    components = COMPONENTS
    record_version = "literature_figure_record_v1"
    operations_table = "literature_figure_operations"
    received_table = "literature_figure_received"
    binding_fields = tuple(BINDINGS)

    def _provenance(self, scope, reference):
        if not self.store.reference_subset([reference], plain(scope)):
            raise ContractError("literature_source_outside_scope")
        source = self.store.get(reference)
        if source["record_type"] != "source":
            raise ContractError("literature_source_required")
        return source

    def _source(self, context, reference):
        if reference not in context.received_record_refs:
            raise ContractError("literature_source_not_received")
        source = self._provenance(context.scope, reference)
        page = context.assignment if context.role == "literature_page" else context.assignment.get("page")
        if page:
            pending, seen = [reference], set()
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                ancestor = self._provenance(context.scope, current)
                if current == page["source_ref"]:
                    break
                pending.extend(ancestor.get("parent_source_refs", ()))
            else:
                raise ContractError("literature_reading_outside_assigned_source")
        return source

    def _parents(self, scope, direct):
        parents, seen = list(direct), set(direct)
        cursor = 0
        while cursor < len(parents):
            source = self._provenance(scope, parents[cursor])
            cursor += 1
            for reference in source.get("parent_source_refs", ()):
                self._provenance(scope, reference)
                if reference not in seen:
                    seen.add(reference)
                    parents.append(reference)
        return parents

    def _replay(self, context, old, signature):
        if old["signature"] != signature:
            raise ContractError("operation_key_reused_for_different_work")
        outcome = json.loads(old["outcome"])
        saved = self.read(outcome["result"]["sheet_ref"])
        for reference in saved["direct_input_source_refs"]:
            self._source(context, reference)
        for reference in saved["input_source_refs"]:
            self._provenance(context.scope, reference)
        return outcome

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        validate_schema(args, figure_population_schema())
        signature = canonical({"arguments": args, "scope": plain(context.scope)})
        parameters = (self.run_id, context.episode_id, operation_key)
        query = (f"SELECT signature,outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?")
        old = self.store.db.execute(query, parameters).fetchone()
        if old is not None:
            return self._replay(context, old, signature)
        with self.store.transaction():
            old = self.store.db.execute(query, parameters).fetchone()
            if old is not None:
                return self._replay(context, old, signature)

            def read_source(reference, representation):
                source = self._source(context, reference)
                if representation not in ("original", "text"):
                    raise ContractError("literature_source_representation_required")
                artifact = source["artifact_ref"] if representation == "original" else source.get("text_ref")
                if artifact is None:
                    raise ContractError("literature_source_representation_unavailable")
                return {"artifact_ref": artifact, "content": self.store.get_artifact(artifact)}

            extraction = read_figure_inputs(args, read_source=read_source)
            direct = _direct_references(args, extraction["recipe"])
            if (len(extraction["sources"]) != len(direct)
                    or set(extraction["sources"]) != set(direct)):
                raise ContractError("literature_figure_direct_source_mismatch")
            for reference in direct:
                self._source(context, reference)
            parents = self._parents(context.scope, direct)
            source = self.store.get(args["source_ref"])
            payload = {"version": self.record_version, "input_source_ref": source["id"],
                "input_artifact_ref": source["artifact_ref"], "input_source_refs": parents,
                "direct_input_source_refs": direct, "data_source_ref": args["data_source_ref"],
                "extraction": extraction, "sheet": {"cells": deepcopy(extraction["cells"])}}
            created = []

            def publish(kind, record):
                candidate = identity(kind, {"origin": "tool", "record": record})
                exists = self.store.db.execute("SELECT 1 FROM records WHERE id=?", (candidate,)).fetchone()
                row = self.store.put(kind, record, origin="tool", scope=plain(context.scope))
                if exists is None:
                    created.append(row["id"])
                return row["id"]

            bindings = {}
            for field, (literal, kind) in BINDINGS.items():
                entry = extraction["literals"][literal]
                if entry and kind == "context":
                    publish("reference", _condition_role(literal, entry))
                bindings[field] = publish(kind, _binding_record(literal, kind, entry)) if entry else None
            payload["experimental_bindings"] = bindings
            artifact = self.store.artifact(canonical(payload), "application/json")
            request = self.store.artifact(canonical({"run_id": self.run_id,
                "episode_id": context.episode_id, "operation_key": operation_key,
                "arguments": args, "scope": plain(context.scope)}), "application/json")
            sheet_ref = publish("source", {"provider": self.provider, "accession": None,
                "uri": None, "artifact_ref": artifact, "text_ref": artifact, "request_ref": request,
                "version": self.record_version, "retrieved_at": None, "parent_source_refs": parents})
            outcome = {"status": "completed", "operation_ref": identity("operation", {
                "run_id": self.run_id, "episode_id": context.episode_id, "key": operation_key}),
                "record_refs": list(dict.fromkeys([sheet_ref, *parents,
                    *(reference for reference in bindings.values() if reference), *_condition_refs(extraction)])),
                "changed_record_refs": created,
                "result": {"sheet_ref": sheet_ref, "cells": deepcopy(extraction["cells"]),
                    "assay_interpretation": deepcopy(extraction["literals"]), **_metadata(extraction)},
                "feedback": None}
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (*parameters, signature, canonical(outcome)))
        return outcome

    def read(self, sheet_ref):
        """Validate saved authority and copy cells, without source-byte reads."""
        saved = super().read(sheet_ref)
        try:
            self._validate_saved(sheet_ref, saved)
        except ContractError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise ContractError("literature_figure_sheet_source_mismatch") from error
        return saved

    def _validate_saved(self, sheet_ref, saved):
        def require(condition):
            if not condition:
                raise ContractError("literature_figure_sheet_source_mismatch")

        source = self.store.get(sheet_ref)
        request = json.loads(self.store.get_artifact(source["request_ref"]))
        require(set(request) == {"run_id", "episode_id", "operation_key", "arguments", "scope"})
        args, extraction = request["arguments"], saved["extraction"]
        validate_schema(args, figure_population_schema())
        operation = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request["episode_id"], request["operation_key"])).fetchone()
        require(operation is not None and operation["signature"] == canonical({
            "arguments": args, "scope": request["scope"]}))
        require(set(saved) == {"version", "input_source_ref", "input_artifact_ref", "input_source_refs",
            "direct_input_source_refs", "data_source_ref", "extraction", "experimental_bindings", "sheet"})
        require(source["version"] == self.record_version and source["text_ref"] == source["artifact_ref"])
        require(extraction["version"] == "a105_figure_inputs_v1" and extraction["arguments"] == args)
        require(set(extraction) == {"version", "arguments", "sources", "literals", "interpretations",
            "recipe", "measurements", "cells"})
        recipe = extraction["recipe"]
        require(set(recipe) == {"version", "first", "second", "design"})
        require(recipe["version"] == "literature_figure_selection_v1")
        validate_schema(recipe["design"], _design_schema())
        require((recipe["second"] is None) == (recipe["design"]["second_repeat"] is None))
        for repeat in (recipe["design"]["first_repeat"], recipe["design"]["second_repeat"]):
            if repeat:
                require(repeat["spread_numeric_status"] == (
                    "unreported" if repeat["spread_kind"] == "unreported" else "not_extracted"))
        direct = _direct_references(args, recipe)
        require(saved["direct_input_source_refs"] == direct)
        require(isinstance(extraction["sources"], list) and len(extraction["sources"]) == len(direct)
            and set(extraction["sources"]) == set(direct))
        require(saved["input_source_refs"] == self._parents(request["scope"], direct))
        require(saved["input_artifact_ref"] == self.store.get(args["source_ref"])["artifact_ref"]
            and saved["data_source_ref"] == args["data_source_ref"])

        def witness(value):
            row = self.store.get(value["source_ref"])
            artifact = row["artifact_ref"] if value["representation"] == "original" else row["text_ref"]
            return {**value, "artifact_ref": artifact}

        require(set(extraction["literals"]) == set(LITERAL_FIELDS))
        for literal in LITERAL_FIELDS:
            selected = args["literals"][literal]
            expected = {"value": selected["quote"], "witness": witness(selected)} if selected else None
            require(extraction["literals"][literal] == expected)
        require(extraction["interpretations"] == [witness(entry) for entry in args["interpretation_witnesses"]])
        require(set(saved["experimental_bindings"]) == set(BINDINGS))
        for field, (literal, kind) in BINDINGS.items():
            entry, reference = extraction["literals"][literal], saved["experimental_bindings"][field]
            if entry is None:
                require(reference is None)
            else:
                record = _binding_record(literal, kind, entry)
                require(reference == identity(kind, {"origin": "tool", "record": record}))
                require(self.store.get(reference) == {"id": reference, "record_type": kind,
                    "origin": "tool", **record})
                if kind == "context":
                    role = _condition_role(literal, entry)
                    role_ref = record["related_refs"][0]
                    require(self.store.get(role_ref) == {"id": role_ref, "record_type": "reference",
                        "origin": "tool", **role})

        require(set(saved["sheet"]) == {"cells"} and saved["sheet"]["cells"] == extraction["cells"])
        require(set(extraction["cells"]) == set(COMPONENTS))
        require(set(extraction["measurements"]) == {"first", "second"})
        for side in ("first", "second"):
            selected, measurement = recipe[side], extraction["measurements"][side]
            if selected is None:
                require(measurement is None)
                continue
            require(set(selected) == {"image_source_ref", "image_origin", "axis_scale", "selection"})
            require(selected["image_origin"] in ("published", "synthetic") and selected["axis_scale"] == "linear")
            require(set(measurement) == {"version", "image_sha256", "image_size", "selection",
                "qualifying_runs", "pixel_edge", "cell"})
            require(measurement["version"] == "literature_bar_ordinate_v1")
            require(measurement["selection"] == selected["selection"])
            require("artifact_" + measurement["image_sha256"] == self.store.get(selected["image_source_ref"])["artifact_ref"])
            require(measurement["cell"] == extraction["cells"][side + "_ordinate"])
            require(measurement["cell"]["unit"] == selected["selection"]["calibration"]["unit"])
        for name, cell in extraction["cells"].items():
            validate_schema(cell, _cell_schema())
            require(cell["origin"] == ("derived" if name == "ordinate_difference" else "graph_derived"))
            if name != "ordinate_difference" and not (
                    name == "second_ordinate" and recipe["second"] is None):
                require(cell["unit"] in NATIVE_UNITS and cell["unavailable_reason"] in (
                    None, "no_bar_pixels", "ambiguous_bar_runs", "truncated_mean_edge", "numerical_model_range"))
            if cell["status"] == "populated":
                require(cell["unavailable_reason"] is None and all(cell[key] is not None
                    for key in ("value", "lower", "upper")) and cell["lower"] <= cell["value"] <= cell["upper"])
            else:
                require(cell["unavailable_reason"] is not None and all(cell[key] is None
                    for key in ("value", "lower", "upper")))
        second, difference = extraction["cells"]["second_ordinate"], extraction["cells"]["ordinate_difference"]
        if recipe["second"] is None:
            require(all(cell["status"] == "unavailable" and cell["unit"] is None
                and cell["unavailable_reason"] == "second_ordinate_unreported" for cell in (second, difference)))
        elif _metadata(extraction)["first_axis_unit"] != _metadata(extraction)["second_axis_unit"]:
            require(difference["status"] == "unavailable" and difference["unit"] is None
                and difference["unavailable_reason"] == "ordinate_unit_mismatch")
        else:
            unit = _metadata(extraction)["first_axis_unit"]
            require(difference["unit"] == ("relative_turnover_percentage_points"
                if unit == "relative_turnover_percent" else unit))
            if any(extraction["cells"][side + "_ordinate"]["status"] == "unavailable"
                    for side in ("first", "second")):
                require(difference["status"] == "unavailable" and difference["unavailable_reason"] == "missing_ordinate")
            else:
                require(difference["status"] == "populated" or difference["unavailable_reason"] == "numerical_model_range")
        outcome = json.loads(operation["outcome"])
        require(outcome["status"] == "completed" and outcome["feedback"] is None)
        require(isinstance(outcome["changed_record_refs"], list)
            and len(set(outcome["changed_record_refs"])) == len(outcome["changed_record_refs"])
            and set(outcome["changed_record_refs"]) <= set(outcome["record_refs"]))
        require(outcome["operation_ref"] == identity("operation", {"run_id": self.run_id,
            "episode_id": request["episode_id"], "key": request["operation_key"]}))
        require(outcome["record_refs"] == list(dict.fromkeys([sheet_ref, *saved["input_source_refs"],
            *(saved["experimental_bindings"][field] for field in BINDINGS
                if saved["experimental_bindings"][field]), *_condition_refs(extraction)])))
        require(outcome["result"] == {"sheet_ref": sheet_ref, "cells": extraction["cells"],
            "assay_interpretation": extraction["literals"], **_metadata(extraction)})

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        components = self.components if components is None else components
        if (not isinstance(components, (list, tuple))
                or any(not isinstance(name, str) or name not in self.components for name in components)
                or len(set(components)) != len(components)):
            raise ContractError("literature_figure_component_selection_invalid")
        rows = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            saved = self.read(reference)
            recipe = saved["extraction"]["recipe"]
            for name in components:
                rows.append({"sheet_ref": reference, "evidence_source_ref": saved["input_source_ref"],
                    "data_source_ref": saved["data_source_ref"],
                    "first_image_source_ref": recipe["first"]["image_source_ref"],
                    "second_image_source_ref": recipe["second"]["image_source_ref"] if recipe["second"] else None,
                    **deepcopy(saved["experimental_bindings"]), "component": name,
                    **deepcopy(saved["sheet"]["cells"][name]), "formula_code": FORMULA_CODES[name],
                    **_metadata(saved["extraction"])})
        validate_schema(rows, figure_cells_schema())
        return rows

    def validate_returned_values(self, cells, *, permitted_record_refs):
        validate_schema(cells, figure_cells_schema())
        super().validate_returned_values(cells, permitted_record_refs=permitted_record_refs)


def figure_cells_schema():
    """Closed scientific rows; pixel selections remain in saved custody only."""
    source = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    properties = {
        **{field: dict(source) for field in ("sheet_ref", "evidence_source_ref", "data_source_ref",
            "first_image_source_ref")},
        "second_image_source_ref": {**source, "type": ["string", "null"]},
        **{field: {"type": ["string", "null"], "format": "reference", "x-reference-namespace": kind}
            for field, (_, kind) in BINDINGS.items()},
        "component": {"type": "string", "enum": list(COMPONENTS)},
        **deepcopy(_cell_schema()["properties"]),
        "formula_code": {"type": "string", "enum": list(FORMULA_CODES.values())},
        "source_kind": {"type": "string", "enum": list(SOURCE_KINDS)},
        "first_image_origin": {"type": "string", "enum": ["published", "synthetic"]},
        "second_image_origin": {"type": ["string", "null"], "enum": ["published", "synthetic", None]},
        "design": _design_schema(),
        "first_axis_unit": {"type": "string", "enum": list(NATIVE_UNITS)},
        "second_axis_unit": {"type": ["string", "null"], "enum": [*NATIVE_UNITS, None]},
        **{field: {"type": "string", "enum": [value]} for field, value in _FIXED_METADATA.items()}}
    # Explicit types are required by the parent form's closed-schema checker.
    for field, schema in properties.items():
        if "type" not in schema and "enum" in schema:
            schema["type"] = ["string", "null"] if None in schema["enum"] else "string"
    return {"type": "array", "items": obj(properties), "x-source": "literature_figure_cells"}


def figure_operation_schema():
    """Explicit endpoint branch alongside the unchanged native bar contract."""
    from .literature_endpoint_signal_storage import endpoint_signal_operation_schema
    return {"type": "object", "anyOf": [figure_population_schema(), endpoint_signal_operation_schema()]}


__all__ = ["LiteratureFigureRepository", "COMPONENTS", "PROVIDER", "BINDINGS",
    "figure_population_schema", "figure_cells_schema"]
