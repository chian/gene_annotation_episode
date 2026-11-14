"""Selected completion-time sheets and exact typed subsets, with saved custody."""
from copy import deepcopy
import hashlib
import json

from .communication import plain
from .domain import ContractError, canonical, identity, obj
from .literature_completion_time_inputs import (ROLES, LITERAL_FIELDS, COMPARISON_FIELDS, COMPARISON_VALUES,
    QUALIFICATIONS, read_completion_time_inputs, validate_completion_time_extraction,
    validate_completion_time_selection, measurement_location)
from .literature_completion_time_calculations import (COMPONENTS, REASONS, CONDITIONS,
    populate_completion_time_components)
from .literature_rate_storage import LiteratureRateRepository

PROVIDER = "literature.a105.completion_time_population"
VERSION = "literature_completion_time_record_v1"
NAMESPACE = "literature_completion_time_cells"


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


def _roles(component):
    return (component.removesuffix("_time"),) if component in ("numerator_time", "denominator_time") else ROLES


def _project_saved(saved, sheet_ref, components):
    extraction = saved["extraction"]
    result = []
    for component in components:
        roles = _roles(component)
        exposed = set(roles) if component in ("numerator_time", "denominator_time") else set()
        withheld = [measurement_location(row["number"]) for role, row in extraction["quantities"].items()
            if role not in exposed and row and row["number"]]
        def meaning(witness):
            if witness is None:
                return {"status": "not_selected", "witness": None}
            overlap = any(witness["artifact_ref"] == location["artifact_ref"] and
                witness["start"] < location["end"] and witness["end"] > location["start"] for location in withheld)
            return {"status": "withheld_time_operand" if overlap else "selected", "witness": None if overlap else deepcopy(witness)}
        def interpretation(value):
            return {"value": value["value"], "support": [meaning(witness) for witness in value["witnesses"]]}
        operands = []
        for role in roles:
            row = extraction["quantities"][role]
            number = row["number"] if row else None
            reading = None
            if role in exposed and number:
                # Only the literal number span crosses. A broad nomination
                # witness must not leak the other arm's unrequested time.
                location = measurement_location(number)
                witness = {**location, "representation": number["selector"]["witness"]["representation"],
                    "quote": number["raw_number"]}
                reading = {"number": witness, "raw_unit": row["unit"]["raw_unit"] if row["unit"] else None,
                    "bound": row["bound"], "canonical_minutes": row["exact_minutes"]}
            operands.append({"role": role, "meanings": {field: meaning(row["meanings"][field] if row else None)
                for field in LITERAL_FIELDS}, "qualification": interpretation(row["qualification"]) if row else {"value": "unknown", "support": []},
                "reading": reading})
        cell = saved["sheet"]["cells"][component]
        result.append({"sheet_ref": sheet_ref, "evidence_source_ref": saved["input_source_ref"], "component": component,
            **{field: deepcopy(cell[field]) for field in ("value", "unit", "status", "unavailable_reason", "approximate",
                "origin", "conditional_on", "reported_domain", "exact_domain")},
            "evaluation_scope": "source_preparation_completion_time", "experiment": meaning(extraction["experiment"]),
            "intended_change": meaning(extraction["intended_change"]),
            "other_changes": [meaning(w) for w in extraction["other_changes"]],
            "comparison": {field: interpretation(extraction["comparison"][field]) for field in COMPARISON_FIELDS},
            "operands": operands})
    return result


class LiteratureCompletionTimeRepository(LiteratureRateRepository):
    provider = PROVIDER
    components = COMPONENTS
    record_version = VERSION
    operations_table = "literature_completion_time_operations"
    received_table = "literature_completion_time_received"
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
        extraction = read_completion_time_inputs(args, read_source=read_source)
        sheet = populate_completion_time_components(extraction)
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
            raise ContractError("completion_time_saved_artifact_hash_mismatch")
        return json.loads(content)

    def read(self, sheet_ref):
        source = self.store.get(sheet_ref)
        if source.get("record_type") != "source" or source.get("provider") != PROVIDER or source.get("version") != VERSION:
            raise ContractError("literature_completion_time_sheet_required")
        record = {key: value for key, value in source.items() if key not in ("id", "record_type", "origin")}
        if source.get("origin") != "tool" or identity("source", {"origin": "tool", "record": record}) != sheet_ref:
            raise ContractError("completion_time_saved_source_identity_mismatch")
        request = self._artifact_json(source["request_ref"])
        if request.get("run_id") != self.run_id:
            raise ContractError("literature_run_mismatch")
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
            raise ContractError("completion_time_saved_selection_mismatch")
        extraction = validate_completion_time_extraction(saved["extraction"])
        validate_completion_time_selection(saved["selection"], extraction)
        if extraction["source_refs"] != saved["direct_input_source_refs"]:
            raise ContractError("completion_time_saved_source_mismatch")
        if self.store.get(saved["input_source_ref"])["artifact_ref"] != saved["input_artifact_ref"]:
            raise ContractError("completion_time_saved_source_mismatch")
        for witness in _witnesses(extraction):
            original = self.store.get(witness["source_ref"])
            actual = original["artifact_ref"] if witness["representation"] == "original" else original.get("text_ref")
            if actual != witness["artifact_ref"] or witness["source_ref"] not in saved["direct_input_source_refs"]:
                raise ContractError("completion_time_saved_source_mismatch")
        # Deterministic algebra on committed operands is permitted; original
        # scientific bytes are neither opened nor reinterpreted on this path.
        if (canonical(saved["sheet"]) != canonical(populate_completion_time_components(extraction))
                or canonical(outcome["result"]["cells"]) != canonical(_project_saved(saved, sheet_ref, COMPONENTS))):
            raise ContractError("completion_time_saved_cells_mismatch")
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = self.components if components is None else components
        if not isinstance(selected, (list, tuple)) or len(set(selected)) != len(selected) or any(name not in COMPONENTS for name in selected):
            raise ContractError("completion_time_component_selection_invalid")
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


def completion_time_cells_schema():
    def ref(namespace):
        return {"type": "string", "format": "reference", "x-reference-namespace": namespace}
    witness = obj({"source_ref": ref("source"), "artifact_ref": ref("artifact"),
        "representation": {"type": "string", "enum": ["original", "text"]},
        "start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1},
        "quote": {"type": "string", "minLength": 1}})
    meaning = obj({"status": {"type": "string", "enum": ["selected", "not_selected", "withheld_time_operand"]},
        "witness": {"anyOf": [witness, {"type": "null"}]}})
    def interpretation(values):
        return obj({"value": {"type": "string", "enum": list(values)},
            "support": {"type": "array", "items": deepcopy(meaning)}})
    nullable_number = {"type": ["number", "null"]}
    exact_number = {"anyOf": [obj({"numerator": {"type": "string", "pattern": "^-?[0-9]+$"},
        "denominator": {"type": "string", "pattern": "^[1-9][0-9]*$"}}), {"type": "null"}]}
    exact_domain = {"anyOf": [obj({"lower": deepcopy(exact_number), "upper": deepcopy(exact_number),
        "lower_inclusive": {"type": "boolean"}, "upper_inclusive": {"type": "boolean"}}), {"type": "null"}]}
    domain = obj({"kind": {"type": "string", "enum": ["point", "finite_interval", "lower_bounded", "upper_bounded", "unbounded", "unavailable"]},
        "lower": deepcopy(nullable_number), "upper": deepcopy(nullable_number),
        "lower_inclusive": {"type": "boolean"}, "upper_inclusive": {"type": "boolean"},
        "projection": {"type": "string", "enum": ["none", "exact", "outward"]},
        "basis": {"type": "string", "enum": ["reported_operand_algebra", "reported_time_operand"]},
        "conditioning": {"type": "string", "const": "strictly_positive_physical_completion_time"},
        "failure": {"type": ["string", "null"], "enum": [*REASONS, None]}})
    reading = {"anyOf": [obj({"number": deepcopy(witness), "raw_unit": {"type": ["string", "null"]},
        "bound": {"type": "string", "enum": ["none", "lt", "le", "gt", "ge"]},
        "canonical_minutes": {"type": ["string", "null"]}}), {"type": "null"}]}
    operand = obj({"role": {"type": "string", "enum": list(ROLES)},
        "meanings": obj({field: deepcopy(meaning) for field in LITERAL_FIELDS}),
        "qualification": interpretation(QUALIFICATIONS), "reading": reading})
    return {"type": "array", "items": obj({"sheet_ref": ref("source"), "evidence_source_ref": ref("source"),
        "component": {"type": "string", "enum": list(COMPONENTS)}, "value": deepcopy(nullable_number),
        "unit": {"type": ["string", "null"], "enum": ["min", "dimensionless", None]},
        "status": {"type": "string", "enum": ["point", "bounded", "unavailable"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [*REASONS, None]},
        "origin": {"type": "string", "enum": ["reported", "synthetic", "derived"]}, "approximate": {"type": "boolean"},
        "conditional_on": {"type": "array", "uniqueItems": True, "items": {"type": "string", "enum": list(CONDITIONS)}},
        "reported_domain": domain, "exact_domain": exact_domain,
        "evaluation_scope": {"type": "string", "const": "source_preparation_completion_time"},
        "experiment": deepcopy(meaning), "intended_change": deepcopy(meaning),
        "other_changes": {"type": "array", "items": deepcopy(meaning)},
        "comparison": obj({field: interpretation(values) for field, values in zip(COMPARISON_FIELDS, COMPARISON_VALUES)}),
        "operands": {"type": "array", "minItems": 1, "maxItems": 2, "items": operand}}), "x-source": NAMESPACE}
