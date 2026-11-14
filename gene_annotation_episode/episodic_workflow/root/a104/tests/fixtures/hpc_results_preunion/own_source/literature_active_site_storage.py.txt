"""Selected active-site amount sheets, exact typed subsets and source-free replay."""
from copy import deepcopy
import hashlib
import json

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_active_site_inputs import (ROLES, LITERAL_FIELDS, INTERPRETATIONS, QUALIFICATIONS, SPREAD_KINDS, SAMPLING,
    VERSION as EXTRACTION_VERSION, DEPENDENCY, read_active_site_inputs,
    validate_active_site_selection, measurement_location)
from .literature_active_site_calculations import (COMPONENTS, COMPONENT_ROLES, REASONS, CONDITIONS,
    VERSION as SHEET_VERSION, LIMITS, populate_active_site_components)
from .literature_rate_storage import LiteratureRateRepository

PROVIDER = "literature.a105.active_site_population"
VERSION = "literature_active_site_record_v1"
NAMESPACE = "literature_active_site_cells"


def _witnesses(value):
    if isinstance(value, dict):
        if set(value) == {"source_ref", "artifact_ref", "representation", "start", "end", "quote"}:
            yield value
        else:
            for child in value.values():
                yield from _witnesses(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _witnesses(child)


def _saved_extraction_schema():
    """Describe committed values without parsing or converting them again."""
    text = {"type": "string", "minLength": 1}
    nullable = lambda schema: {"anyOf": [schema, {"type": "null"}]}
    witness = obj({"source_ref": text, "artifact_ref": text,
        "representation": {"enum": ["original", "text"]},
        "start": {"type": "integer", "minimum": 0},
        "end": {"type": "integer", "minimum": 1}, "quote": text})
    def interpretation(values):
        return obj({"value": {"enum": list(values)},
            "witnesses": {"type": "array", "items": witness}})
    number = obj({"selector": obj({"witness": witness,
        "number_start": {"type": "integer", "minimum": 0},
        "number_end": {"type": "integer", "minimum": 1}}),
        "raw_number": text, "value": {"type": "number"},
        "relation": {"enum": ["point", "lt", "le", "gt", "ge"]},
        "approximate": {"type": "boolean"}})
    quantities = {}
    units = dict(zip(ROLES, ("mg/mL", "kDa", "nM", "dimensionless")))
    for role in ROLES:
        unit = obj({"witness": nullable(witness), "raw_unit": nullable(text),
            "canonical_unit": {"enum": [units[role], None]},
            "conflicting_units": {"type": "array", "items": witness}})
        quantities[role] = nullable(obj({
            "meanings": obj({field: nullable(witness) for field in LITERAL_FIELDS}),
            "qualification": interpretation(QUALIFICATIONS), "number": nullable(number),
            "unit": nullable(unit), "reported_uncertainty": obj({
                "kind": interpretation(SPREAD_KINDS), "number": nullable(number),
                "sampling_basis": interpretation(SAMPLING),
                "statement": nullable(witness), "unit": nullable(unit)}),
            "exact_value": nullable({"type": "string", "pattern": r"^-?[0-9]+(?:/[1-9][0-9]*)?$"}),
            "unavailable_reason": {"enum": [None, *REASONS]},
            "measurement_key": nullable(text), "physical_observation_key": nullable(text),
            "bound": {"enum": ["none", "lt", "le", "gt", "ge"]},
            "approximate": {"type": "boolean"},
            "origin": {"enum": ["reported", "synthetic", "derived"]}}))
    return obj({"version": {"const": EXTRACTION_VERSION}, "source_ref": text,
        "source_kind": {"enum": ["primary_source", "retained_extraction", "synthetic_fixture"]},
        "experiment": nullable(witness), "intended_change": nullable(witness),
        "other_changes": {"type": "array", "items": witness},
        "interpretations": obj({field: interpretation(values) for field, values in INTERPRETATIONS.items()}),
        "quantities": obj(quantities),
        "source_refs": {"type": "array", "uniqueItems": True, "items": text},
        "lexical_dependency": {"const": DEPENDENCY}})


def _validate_saved_extraction(extraction, selection):
    """Validate original custody/meaning relationships, never scientific algebra.

    The authenticated payload and original selected outcome retain the numerical
    results. This check does not turn their printed tokens into numbers, look up
    unit multipliers, or reconstruct the calculator's domains and fractions.
    """
    validate_schema(extraction, _saved_extraction_schema())
    validate_active_site_selection(selection, extraction)
    witnesses = list(_witnesses(extraction))
    if set(extraction["source_refs"]) != {selection["source_ref"], *(w["source_ref"] for w in witnesses)}:
        raise ContractError("active_site_saved_source_mismatch")
    for witness in witnesses:
        if witness["end"] - witness["start"] != len(witness["quote"].encode("utf-8")):
            raise ContractError("active_site_saved_witness_mismatch")
    def interpretation(value):
        unique = {(w["source_ref"], w["artifact_ref"], w["start"], w["end"]) for w in value["witnesses"]}
        required = 2 if value["value"] == "conflicting" else 0 if value["value"] in ("unknown", "unreported") else 1
        if len(unique) < required:
            raise ContractError("active_site_saved_interpretation_mismatch")
    for value in extraction["interpretations"].values():
        interpretation(value)
    for row in extraction["quantities"].values():
        if row is None:
            continue
        for value in (row["qualification"], row["reported_uncertainty"]["kind"], row["reported_uncertainty"]["sampling_basis"]):
            interpretation(value)
        for item in (row, row["reported_uncertainty"]):
            number, unit = item["number"], item["unit"]
            if number is not None:
                selector = number["selector"]
                start, end = selector["number_start"], selector["number_end"]
                if not 0 <= start < end <= len(selector["witness"]["quote"]) or selector["witness"]["quote"][start:end] != number["raw_number"]:
                    raise ContractError("active_site_saved_number_selection_mismatch")
            if unit is not None:
                conflicts = unit["conflicting_units"]
                if conflicts:
                    if (len({(w["source_ref"], w["artifact_ref"], w["start"], w["end"]) for w in conflicts}) < 2
                            or any(unit[key] is not None for key in ("witness", "raw_unit", "canonical_unit"))):
                        raise ContractError("active_site_saved_unit_mismatch")
                elif unit["witness"] is None or unit["raw_unit"] != unit["witness"]["quote"]:
                    raise ContractError("active_site_saved_unit_mismatch")
        expected_key = identity("active_site_measurement", measurement_location(row["number"])) if row["number"] else None
        physical = row["meanings"]["measurement_identity"]
        expected_physical = identity("active_site_observation", {field: physical[field]
            for field in ("source_ref", "artifact_ref", "start", "end")}) if physical else None
        if row["measurement_key"] != expected_key or row["physical_observation_key"] != expected_physical:
            raise ContractError("active_site_saved_measurement_identity_mismatch")
        if row["bound"] != (row["number"]["relation"] if row["number"] and row["number"]["relation"] != "point" else "none"):
            raise ContractError("active_site_saved_number_selection_mismatch")
        spread = row["reported_uncertainty"]
        if spread["number"] is not None and (spread["kind"]["value"] == "unreported"
                or spread["number"]["relation"] != "point" or spread["number"]["approximate"]
                or spread["number"]["value"] < 0):
            raise ContractError("active_site_saved_spread_mismatch")


def _validate_saved_sheet(saved, sheet_ref):
    sheet = saved["sheet"]
    if (set(sheet) != {"version", "axis", "evaluation_scope", "cells", "interpretation_limits",
            "annotation_credit", "rate_factor_applied", "fraction_uncertainty", "independent_preparation_count"}
            or sheet["version"] != SHEET_VERSION or sheet["axis"] != "A105"
            or sheet["evaluation_scope"] != "active_site_titration_amount"
            or sheet["annotation_credit"] is not None or sheet["rate_factor_applied"] is not False
            or sheet["independent_preparation_count"] is not None or sheet["interpretation_limits"] != list(LIMITS)
            or set(sheet["cells"]) != set(COMPONENTS)):
        raise ContractError("active_site_saved_cells_mismatch")
    for name, cell in sheet["cells"].items():
        if (set(cell) != {"value", "unit", "status", "unavailable_reason", "approximate", "origin",
                "conditional_on", "reported_domain", "exact_domain", "formula", "input_measurement_keys"}
                or not isinstance(cell["formula"], str) or not cell["formula"]):
            raise ContractError("active_site_saved_cells_mismatch")
        expected = [saved["extraction"]["quantities"][role]["measurement_key"] for role in COMPONENT_ROLES[name]
            if saved["extraction"]["quantities"][role] and saved["extraction"]["quantities"][role]["measurement_key"]]
        if cell["input_measurement_keys"] != expected:
            raise ContractError("active_site_saved_measurement_identity_mismatch")
    rows = _project_saved(saved, sheet_ref, COMPONENTS)
    validate_schema(rows, active_site_cells_schema())
    return rows


def _project_saved(saved, sheet_ref, components):
    extraction = saved["extraction"]
    result = []
    for component in components:
        roles = COMPONENT_ROLES[component]
        exposed = {component} if component in ROLES else set()
        withheld = [measurement_location(number) for role, row in extraction["quantities"].items()
            if role not in exposed and row for number in (row["number"], row["reported_uncertainty"]["number"]) if number]
        def meaning(witness):
            if witness is None:
                return {"status": "not_selected", "witness": None}
            overlap = any(witness["artifact_ref"] == loc["artifact_ref"] and witness["start"] < loc["end"] and witness["end"] > loc["start"] for loc in withheld)
            return {"status": "withheld_amount_operand" if overlap else "selected", "witness": None if overlap else deepcopy(witness)}
        def interpretation(value):
            return {"value": value["value"], "support": [meaning(w) for w in value["witnesses"]]}
        def reading(number, unit, role):
            if role not in exposed or number is None:
                return None
            return {"number": {**measurement_location(number), "representation": number["selector"]["witness"]["representation"], "quote": number["raw_number"]},
                "raw_unit": unit["raw_unit"] if unit else None, "bound": number["relation"]}
        operands = []
        for role in roles:
            row = extraction["quantities"][role]
            unc = row["reported_uncertainty"] if row else None
            operands.append({"role": role, "meanings": {field: meaning(row["meanings"][field] if row else None) for field in LITERAL_FIELDS},
                "qualification": interpretation(row["qualification"]) if row else {"value": "unknown", "support": []},
                "reading": reading(row["number"], row["unit"], role) if row else None,
                "reported_uncertainty": {"kind": interpretation(unc["kind"]) if unc else {"value": "unknown", "support": []},
                    "sampling_basis": interpretation(unc["sampling_basis"]) if unc else {"value": "unknown", "support": []},
                    "statement": meaning(unc["statement"] if unc else None),
                    "reading": reading(unc["number"], unc["unit"], role) if unc else None},
                "measurement_key": row["measurement_key"] if row else None,
                "physical_observation_key": row["physical_observation_key"] if row else None})
        cell = saved["sheet"]["cells"][component]
        result.append({"sheet_ref": sheet_ref, "evidence_source_ref": saved["input_source_ref"], "component": component,
            **{field: deepcopy(cell[field]) for field in ("value", "unit", "status", "unavailable_reason", "approximate", "origin", "conditional_on", "reported_domain", "exact_domain")},
            "evaluation_scope": "active_site_titration_amount", "experiment": meaning(extraction["experiment"]),
            "intended_change": meaning(extraction["intended_change"]), "other_changes": [meaning(w) for w in extraction["other_changes"]],
            "interpretations": {field: interpretation(value) for field, value in extraction["interpretations"].items()},
            "operands": operands, "fraction_uncertainty": deepcopy(saved["sheet"]["fraction_uncertainty"]),
            "rate_application_status": {"active_sites": "not_applied_already_active_normalized", "total_monomer": "not_applied_requires_same_rate_context",
                "none": "not_applied_no_rate_selected", "unknown": "not_applied_normalization_unknown", "conflicting": "not_applied_normalization_conflicting"}[extraction["interpretations"]["normalization_stage"]["value"]]})
    return result


class LiteratureActiveSiteRepository(LiteratureRateRepository):
    provider = PROVIDER
    components = COMPONENTS
    record_version = VERSION
    operations_table = "literature_active_site_operations"
    received_table = "literature_active_site_received"
    binding_fields = ()

    def __init__(self, store, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("explicit_literature_run_required")
        self.store, self.run_id = store, run_id

    def _installed(self, table):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

    def _install(self):
        # Install only in an actual selected population/admission transaction.
        super().__init__(self.store, self.run_id)

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        request = {"run_id": self.run_id, "episode_id": context.episode_id, "operation_key": operation_key,
            "arguments": args, "scope": plain(context.scope)}
        signature = canonical(request)
        old = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, context.episode_id, operation_key)).fetchone() if self._installed(self.operations_table) else None
        if old:
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
        extraction = read_active_site_inputs(args, read_source=read_source)
        sheet = populate_active_site_components(extraction)
        direct = extraction["source_refs"]
        ancestors = list(direct)
        for reference in ancestors:
            source = self._native_provenance(context.scope, reference)
            for ancestor in source.get("parent_source_refs", ()):
                if ancestor not in ancestors:
                    ancestors.append(ancestor)
        root = self._native_source(context, args["source_ref"])
        payload = {"version": VERSION, "input_source_ref": args["source_ref"], "input_artifact_ref": root["artifact_ref"],
            "direct_input_source_refs": direct, "input_source_refs": ancestors, "selection": args,
            "extraction": extraction, "sheet": sheet}
        with self.store.transaction():
            self._install()
            artifact = self.store.artifact(canonical(payload), "application/json")
            request_ref = self.store.artifact(canonical(request), "application/json")
            record = {"provider": PROVIDER, "accession": None, "uri": None, "artifact_ref": artifact,
                "text_ref": artifact, "request_ref": request_ref, "version": VERSION, "retrieved_at": None,
                "parent_source_refs": ancestors}
            sheet_ref = identity("source", {"origin": "tool", "record": record})
            exists = self.store.db.execute("SELECT 1 FROM records WHERE id=?", (sheet_ref,)).fetchone()
            self.store.put("source", record, origin="tool", scope=plain(context.scope))
            outcome = {"status": "completed", "operation_ref": identity("operation", {
                "run_id": self.run_id, "episode_id": context.episode_id, "key": operation_key}),
                "record_refs": [sheet_ref], "changed_record_refs": [] if exists else [sheet_ref],
                "result": {"sheet_ref": sheet_ref, "cells": _project_saved(payload, sheet_ref, COMPONENTS)}, "feedback": None}
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def _artifact_json(self, reference):
        content = self.store.get_artifact(reference)
        if "artifact_" + hashlib.sha256(content).hexdigest() != reference:
            raise ContractError("active_site_saved_artifact_hash_mismatch")
        try:
            value = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ContractError("active_site_saved_artifact_json_required") from error
        if not isinstance(value, dict):
            raise ContractError("active_site_saved_artifact_object_required")
        return value

    def read(self, sheet_ref):
        source = self.store.get(sheet_ref)
        if source.get("record_type") != "source" or source.get("provider") != PROVIDER or source.get("version") != VERSION:
            raise ContractError("literature_active_site_sheet_required")
        record = {key: value for key, value in source.items() if key not in ("id", "record_type", "origin")}
        if source.get("origin") != "tool" or identity("source", {"origin": "tool", "record": record}) != sheet_ref:
            raise ContractError("active_site_saved_source_identity_mismatch")
        request = self._artifact_json(source["request_ref"])
        if request.get("run_id") != self.run_id:
            raise ContractError("literature_run_mismatch")
        if (set(request) != {"run_id", "episode_id", "operation_key", "arguments", "scope"}
                or any(not isinstance(request.get(field), str) or not request[field]
                       for field in ("episode_id", "operation_key"))):
            raise ContractError("active_site_saved_selection_mismatch")
        original_scope = self.store.validate_scope(request["scope"])
        self._native_provenance(original_scope, sheet_ref)
        operation = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request.get("episode_id"), request.get("operation_key"))).fetchone() if self._installed(self.operations_table) else None
        if operation is None or operation["signature"] != canonical(request):
            raise ContractError("literature_sheet_not_selected_output")
        outcome = json.loads(operation["outcome"])
        saved = self._artifact_json(source["artifact_ref"])
        expected_fields = {"version", "input_source_ref", "input_artifact_ref", "direct_input_source_refs", "input_source_refs", "selection", "extraction", "sheet"}
        if (set(saved) != expected_fields or saved["version"] != VERSION or saved["selection"] != request["arguments"]
                or saved["input_source_ref"] != request["arguments"]["source_ref"]
                or saved["input_source_refs"] != source["parent_source_refs"]
                or outcome.get("result", {}).get("sheet_ref") != sheet_ref
                or outcome.get("operation_ref") != identity("operation", {"run_id": self.run_id,
                    "episode_id": request["episode_id"], "key": request["operation_key"]})):
            raise ContractError("active_site_saved_selection_mismatch")
        extraction = saved["extraction"]
        _validate_saved_extraction(extraction, saved["selection"])
        if extraction["source_refs"] != saved["direct_input_source_refs"]:
            raise ContractError("active_site_saved_source_mismatch")
        validate_schema(saved["input_source_refs"], {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "minLength": 1}})
        ancestors = list(saved["direct_input_source_refs"])
        for reference in ancestors:
            original = self._native_provenance(original_scope, reference)
            for parent in original.get("parent_source_refs", ()):
                if parent not in ancestors:
                    ancestors.append(parent)
        if saved["input_source_refs"] != ancestors:
            raise ContractError("active_site_saved_source_mismatch")
        if self.store.get(saved["input_source_ref"])["artifact_ref"] != saved["input_artifact_ref"]:
            raise ContractError("active_site_saved_source_mismatch")
        for witness in _witnesses(extraction):
            original = self.store.get(witness["source_ref"])
            actual = original["artifact_ref"] if witness["representation"] == "original" else original.get("text_ref")
            if actual != witness["artifact_ref"] or witness["source_ref"] not in saved["direct_input_source_refs"]:
                raise ContractError("active_site_saved_source_mismatch")
        # Authenticate the original selected cells. Replaying the calculator or
        # unit parser here would reconstruct a new result instead of returning
        # the committed result. Mechanical typed projection uses no equations.
        if (outcome.get("status") != "completed" or sheet_ref not in outcome.get("record_refs", ())
                or canonical(outcome["result"]["cells"]) != canonical(_validate_saved_sheet(saved, sheet_ref))):
            raise ContractError("active_site_saved_cells_mismatch")
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = self.components if components is None else components
        if not isinstance(selected, (list, tuple)) or len(set(selected)) != len(selected) or any(name not in COMPONENTS for name in selected):
            raise ContractError("active_site_component_selection_invalid")
        result = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            result.extend(_project_saved(self.read(reference), reference, selected))
        return result

    def received_cells(self, context):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        return super().received_cells(context) if self._installed(self.received_table) else []

    def receive_cells(self, context, cells, operation_key):
        with self.store.transaction():
            self._install()
            return super().receive_cells(context, cells, operation_key)

    @staticmethod
    def cell_record_refs(cells):
        return list(dict.fromkeys(reference for row in cells for reference in
            [row["sheet_ref"], row["evidence_source_ref"], *[w[field] for w in _witnesses(row) for field in ("source_ref", "artifact_ref")]]))


def active_site_cells_schema():
    def ref(namespace):
        return {"type": "string", "format": "reference", "x-reference-namespace": namespace}
    witness = obj({"source_ref": ref("source"), "artifact_ref": ref("artifact"),
        "representation": {"type": "string", "enum": ["original", "text"]},
        "start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1},
        "quote": {"type": "string", "minLength": 1}})
    meaning = obj({"status": {"type": "string", "enum": ["selected", "not_selected", "withheld_amount_operand"]},
        "witness": {"anyOf": [deepcopy(witness), {"type": "null"}]}})
    def interpretation(values):
        return obj({"value": {"type": "string", "enum": list(values)}, "support": {"type": "array", "items": deepcopy(meaning)}})
    nullable_number = {"type": ["number", "null"]}
    exact_number = {"anyOf": [obj({"numerator": {"type": "string", "pattern": "^-?[0-9]+$"},
        "denominator": {"type": "string", "pattern": "^[1-9][0-9]*$"}}), {"type": "null"}]}
    exact_domain = {"anyOf": [obj({"lower": deepcopy(exact_number), "upper": deepcopy(exact_number),
        "lower_inclusive": {"type": "boolean"}, "upper_inclusive": {"type": "boolean"}}), {"type": "null"}]}
    domain = obj({"kind": {"type": "string", "enum": ["point", "finite_interval", "lower_bounded", "upper_bounded", "unbounded", "unavailable"]},
        "lower": deepcopy(nullable_number), "upper": deepcopy(nullable_number),
        "lower_inclusive": {"type": "boolean"}, "upper_inclusive": {"type": "boolean"},
        "projection": {"type": "string", "enum": ["none", "exact", "outward"]},
        "basis": {"type": "string", "enum": ["reported_operand", "reported_operand_algebra"]},
        "conditioning": {"type": "string", "const": "nonnegative_amounts_positive_molecular_weight"},
        "failure": {"type": ["string", "null"], "enum": [*REASONS, None]}})
    reading = {"anyOf": [obj({"number": deepcopy(witness), "raw_unit": {"type": ["string", "null"]},
        "bound": {"type": "string", "enum": ["point", "lt", "le", "gt", "ge"]}}), {"type": "null"}]}
    operand = obj({"role": {"type": "string", "enum": list(ROLES)},
        "meanings": obj({field: deepcopy(meaning) for field in LITERAL_FIELDS}),
        "qualification": interpretation(QUALIFICATIONS), "reading": deepcopy(reading),
        "reported_uncertainty": obj({"kind": interpretation(SPREAD_KINDS), "sampling_basis": interpretation(SAMPLING),
            "statement": deepcopy(meaning), "reading": deepcopy(reading)}),
        "measurement_key": {"type": ["string", "null"]}, "physical_observation_key": {"type": ["string", "null"]}})
    uncertainty = obj({"value": {"type": "null"}, "status": {"type": "string", "const": "unavailable"},
        "reason": {"type": "string", "const": "full_joint_covariance_propagation_not_implemented"},
        "input_state": {"type": "string", "const": "joint_source_error_covariance_not_selected"},
        "source_spreads_are_not_full_joint_uncertainty": {"type": "boolean", "const": True}})
    return {"type": "array", "items": obj({"sheet_ref": ref("source"), "evidence_source_ref": ref("source"),
        "component": {"type": "string", "enum": list(COMPONENTS)}, "value": deepcopy(nullable_number),
        "unit": {"type": ["string", "null"], "enum": ["mg/mL", "kDa", "nM", "dimensionless", None]},
        "status": {"type": "string", "enum": ["point", "bounded", "unavailable"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [*REASONS, None]},
        "origin": {"type": "string", "enum": ["reported", "synthetic", "derived"]}, "approximate": {"type": "boolean"},
        "conditional_on": {"type": "array", "uniqueItems": True, "items": {"type": "string", "enum": list(CONDITIONS)}},
        "reported_domain": domain, "exact_domain": exact_domain,
        "evaluation_scope": {"type": "string", "const": "active_site_titration_amount"},
        "experiment": deepcopy(meaning), "intended_change": deepcopy(meaning), "other_changes": {"type": "array", "items": deepcopy(meaning)},
        "interpretations": obj({field: interpretation(values) for field, values in INTERPRETATIONS.items()}),
        "operands": {"type": "array", "minItems": 1, "maxItems": 4, "items": operand}, "fraction_uncertainty": uncertainty,
        "rate_application_status": {"type": "string", "enum": ["not_applied_already_active_normalized", "not_applied_requires_same_rate_context",
            "not_applied_no_rate_selected", "not_applied_normalization_unknown", "not_applied_normalization_conflicting"]}}), "x-source": NAMESPACE}
