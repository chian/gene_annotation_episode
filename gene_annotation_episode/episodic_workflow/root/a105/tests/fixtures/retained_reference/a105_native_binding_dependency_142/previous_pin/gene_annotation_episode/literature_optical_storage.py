"""Selected optical q/Vq input storage; no scientific interpretation or credit.

035 owns source parsing,033 owns numerical calculation, and037 owns detached
input integrity. Saved reads authenticate original associations without source
artifact IO, parsing or numerical recalculation. Local aliases imply no global
identity or independence.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_optical_inputs import (
    INTERPRETATIONS, LITERAL_FIELDS, PRIMITIVE_ORDER, QUALIFICATIONS, SOURCE_KINDS,
    read_optical_rate_operands,
)
from .literature_optical_calculations import calculate_nadh_optical_rate
from .literature_rate_storage import LiteratureRateRepository

PROVIDER = "literature.a105.optical_population"
VERSION = "literature_optical_population_record_v1"
COMPONENTS = ("net_rate", "variance_net_rate")
CELL_MAP = {"net_rate": "net_depletion_rate", "variance_net_rate": "net_depletion_variance"}
EVALUATION_SCOPE = "source_nadh_depletion_endpoint"
RETURN_UNITS = {"(uM/min)^2": "uM2/min2"}
FORMULAS = {
    "net_rate": "-1000*(sample_slope-blank_slope)/epsilon/path_length",
    "variance_net_rate": "J*covariance*J_transpose; J=(-1000/(epsilon*l),1000/(epsilon*l),-q/epsilon,-q/l)",
}
FORMULA_CODES = {"net_rate": "nadh_extinction_net_rate", "variance_net_rate": "first_order_nadh_extinction_variance"}
REASONS = ("missing_sample_slope", "missing_blank_slope", "missing_epsilon", "missing_path_length",
    "optical_relation_unknown", "optical_relation_conflicting", "optical_relation_not_applicable",
    "blank_role_unresolved", "blank_role_not_background", "endpoint_mismatch_or_unknown",
    "window_mismatch_or_unknown", "rate_interval_unestablished", "covariance_unreported",
    "covariance_status_unknown", "numerical_model_range", "invalid_propagated_variance")
INPUT_REASONS = ("source_measurement_unreported", "source_optical_unit_unreported",
    "unsupported_source_optical_unit", "censored_source_operand", "approximate_source_operand",
    "source_operand_qualification_unknown", "source_operand_qualification_conflicting",
    "optical_signal_not_slope", "optical_signal_kind_unknown", "optical_signal_unit_mismatch")
CONDITIONS = ("source_optical_relationship_assignments", "first_order_covariance_propagation")
ORIGINS = ("reported", "derived", "synthetic")
UNIT_CODES = {"mM^-1cm^-1": "mM_inverse_cm_inverse"}
_OPERAND_REFS = ("measurement_ref", "physical_observation_ref", "semantic_owner_ref", "local_reuse_ref",
    "condition_ref", "measured_entity_ref", "interval_ref")
_PAYLOAD_FIELDS = ("version", "input_source_ref", "input_artifact_ref", "direct_input_source_refs",
    "input_source_refs", "selection", "extraction", "calculation", "cells", "context_bindings",
    "operand_bindings", "interpretation_bindings", "covariance_binding_ref", "requested_components",
    "implementation_dependencies")
_REQUEST_FIELDS = ("run_id", "episode_id", "operation_key", "selected_tool", "scope", "assignment",
    "requested_components", "arguments")
_PINNED = {"literature_optical_inputs.py": "6e956a39196800d2fe2e4e841a913f40ae4f2d1c44c1fd54fc6abdc6afd6b474",
    "literature_optical_calculations.py": "1242c0e58e83a1ef4e4e8f25bbf94737b33dc706e61794c6ff98b87ce3c5740e",
    "literature_optical_validation.py": "4340cce4a7a659d167b15fcb707b646bd13f8d213e36e0957a454cc02eb54425"}


def _fail(code):
    raise ContractError("literature_optical_" + code)


def _keys(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        _fail("saved_fields_mismatch")


def _selected(assignment):
    values = plain(assignment).get("requested_optical_components", list(COMPONENTS))
    if (not isinstance(values, (list, tuple)) or any(type(v) is not str or v not in COMPONENTS for v in values)
            or len(values) != len(set(values))):
        _fail("component_selection_invalid")
    return list(values)


def _signature(request):
    return canonical({name: request[name] for name in (
        "arguments", "scope", "run_id", "episode_id", "assignment", "requested_components")})


def _dependencies():
    from . import literature_optical_validation
    names = tuple(_PINNED)
    result = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in names}
    if any(result[name] != value for name, value in _PINNED.items()):
        _fail("implementation_dependency_mismatch")
    return {"sha256": result, "validation_version": literature_optical_validation.VERSION}


def _validate_inputs(selection, extraction):
    from .literature_optical_validation import validate_optical_extraction, validate_optical_selection
    validated = validate_optical_extraction(extraction)
    validate_optical_selection(selection, validated)
    return validated


def _witnesses(value):
    if isinstance(value, dict):
        if set(value) == {"source_ref", "representation", "artifact_ref", "start", "end", "quote"}:
            yield value
        else:
            for child in value.values():
                yield from _witnesses(child)
    elif isinstance(value, list):
        for child in value:
            yield from _witnesses(child)


def _bindings(extraction, publish):
    """Define once for publication and saved immutable-record authentication."""
    def reference(witness, kind, *, number=None):
        if witness is None:
            return None
        anchor = {key: witness[key] for key in ("source_ref", "artifact_ref", "start", "end", "quote")}
        if number is not None:
            selected = number["selector"]
            anchor.update(start=witness["start"] + len(witness["quote"][:selected["number_start"]].encode()),
                end=witness["start"] + len(witness["quote"][:selected["number_end"]].encode()), quote=number["raw_number"])
        return publish("reference", {"reference_type": "literature_result", "source_ref": witness["source_ref"],
            "accession": identity("optical_" + kind, {"witness": witness, "number": number}),
            "label": anchor["quote"], "sequence_ref": None, "molecule": None, "length": None,
            "term_refs": [], "context_refs": [], "anchor": anchor})

    def metadata(accession, label, source_ref):
        return publish("reference", {"reference_type": "literature_result", "source_ref": source_ref,
            "accession": accession, "label": label, "sequence_ref": None, "molecule": None,
            "length": None, "term_refs": [], "context_refs": [], "anchor": None})

    def condition(witness):
        return publish("context", {"context_type": "assay_condition", "source_ref": witness["source_ref"],
            "name": witness["quote"], "attributes": [], "related_refs": [],
            "anchor": {key: witness[key] for key in ("source_ref", "artifact_ref", "start", "end", "quote")}}) if witness else None

    context = {name: condition(w) if name == "condition" else reference(w, name)
        for name in LITERAL_FIELDS for w in (extraction["context"][name],)}
    interpretations = {name: {"value": extraction[name]["value"],
        "witness_refs": list(dict.fromkeys(reference(w, name) for w in extraction[name]["witnesses"]))}
        for name in INTERPRETATIONS}
    originals = {"sample_slope": extraction["signals"]["sample"], "blank_slope": extraction["signals"]["blank"],
        **extraction["calibration"]}
    aliases = {role: dep["primitive_observation_ref"] for dep in extraction["dependencies"] for role in dep["primitive_roles"]}
    operands = {}
    for role, row in originals.items():
        meanings = row["meanings"] if row else {}
        number = row["number"] if row else None
        local = aliases.get(role)
        operands["wavelength_context" if role == "wavelength" else role] = {
            "measurement_ref": reference(number["selector"]["witness"], "measurement", number=number) if number else None,
            "measurement_source_ref": number["selector"]["witness"]["source_ref"] if number else None,
            "physical_observation_ref": reference(meanings.get("measurement_identity"), "physical"),
            "semantic_owner_ref": metadata(row["owner_key"], "Optical " + role + " semantic owner", extraction["source_ref"]) if row and row["owner_key"] else None,
            "local_reuse_ref": metadata(local, "Local optical operand reuse alias", extraction["source_ref"]) if local else None,
            "condition_ref": condition(meanings.get("condition")),
            "measured_entity_ref": reference(meanings.get("measured_entity"), "measured_entity"),
            "interval_ref": reference(meanings.get("interval"), "interval"),
            "qualification": row["qualification"]["value"] if row else "unknown",
            "approximate": row["approximate"] if row else None,
            "observed_relation": number["relation"] if number else None,
            "observation_status": row["status"] if row else "unreported",
            "source_origin": row["source_origin"] if row else None,
            "converted_origin": row["origin"] if row else None,
            "canonical_unit": UNIT_CODES.get(row["unit"]["canonical_unit"], row["unit"]["canonical_unit"]) if row and row["unit"] else None,
            "input_status": "context_only" if role == "wavelength" else "available" if extraction["calculation_inputs"][role] is not None else "unavailable",
            "input_unavailable_reasons": list(row["unavailable_reasons"] if row else ["source_measurement_unreported"]) if role == "wavelength" else list(extraction["input_unavailable_reasons"][role]),
        }
    covariance = extraction["covariance_source"]
    cov_ref = metadata(identity("optical_covariance", covariance), "Source-owned ordered optical covariance",
        covariance["source_ref"]) if covariance else None
    return context, operands, interpretations, cov_ref


def _saved_equal(left, right):
    """Exact JSON identity; malformed nonfinite data is a structured mismatch."""
    try:
        return canonical(left) == canonical(right)
    except (ValueError, TypeError, OverflowError):
        return False


def _finite_cell(value):
    import math
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def _admitted_digest(cells):
    try:
        return identity("optical_admitted_cells", cells)
    except (ValueError, TypeError, OverflowError):
        _fail("delivery_binding_mismatch")


def _validate_calculation(saved):
    result, inputs = saved["calculation"], saved["extraction"]["calculation_inputs"]
    _keys(result, ("version", "endpoint", *CELL_MAP.values(), "primitive_observation_refs", "input_snapshot"))
    if (result["version"] != "a105_nadh_optical_rate_cells_v1" or result["endpoint"] != "NADH_depletion"
            or not _saved_equal(result["input_snapshot"], inputs)
            or not _saved_equal(result["primitive_observation_refs"], inputs["primitive_observation_refs"])):
        _fail("saved_calculation_mismatch")
    _keys(saved["cells"], COMPONENTS)
    expected_conditions = [name + "=" + inputs[name] for name in INTERPRETATIONS if name != "signal_kind"]
    for component in COMPONENTS:
        cell = result[CELL_MAP[component]]
        _keys(cell, ("value", "unit", "status", "formula", "origin", "unavailable_reason", "conditional_on"))
        value, reason = cell["value"], cell["unavailable_reason"]
        if value is not None and not _finite_cell(value):
            _fail("saved_cell_mismatch")
        if (not _saved_equal(saved["cells"][component], cell)
                or cell["unit"] != ("uM/min" if component == "net_rate" else "(uM/min)^2")
                or cell["formula"] != FORMULAS[component] or cell["origin"] != "derived"
                or cell["status"] != ("unavailable" if value is None else "populated")
                or (reason not in REASONS if value is None else reason is not None)):
            _fail("saved_cell_mismatch")
        conditions = expected_conditions if component == "net_rate" else [*expected_conditions,
            "first_order_covariance_propagation", "covariance_status=" + inputs["covariance_status"]]
        if cell["conditional_on"] != conditions:
            _fail("saved_cell_conditions_mismatch")
    rate, variance = saved["cells"]["net_rate"], saved["cells"]["variance_net_rate"]
    if (rate["value"] is None and (variance["value"] is not None or variance["unavailable_reason"] != rate["unavailable_reason"])):
        _fail("saved_cell_relationship_mismatch")
    if variance["value"] is not None and (variance["value"] < 0 or inputs["covariance"] is None or inputs["covariance_status"] == "unknown"):
        _fail("saved_cell_relationship_mismatch")


class LiteratureOpticalRepository(LiteratureRateRepository):
    provider = PROVIDER
    record_version = VERSION
    components = COMPONENTS
    operations_table = "literature_optical_operations"
    received_table = "literature_optical_received"
    binding_fields = ()

    def __init__(self, store, run_id):
        super().__init__(store, run_id)
        store.db.execute("""CREATE TABLE IF NOT EXISTS literature_optical_delivery_bindings(
            run_id TEXT NOT NULL, episode_id TEXT NOT NULL, operation_key TEXT NOT NULL,
            cells_digest TEXT NOT NULL, PRIMARY KEY(run_id,episode_id,operation_key))""")

    def _original_delivery_cells(self, context, operation_key):
        prefix = self.run_id + ":" + context.episode_id + ":"
        if not operation_key.startswith(prefix):
            # Standalone repository consumers supply an explicit admitted call;
            # runtime calls additionally authenticate their original form attempt.
            return None
        suffix = operation_key[len(prefix):].split(":")
        if len(suffix) != 2 or not suffix[0].isdigit() or suffix[1] != "typed_form":
            _fail("delivery_binding_mismatch")
        exists = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_report_attempts'").fetchone()
        attempt = self.store.db.execute("SELECT form,contract,failure FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?",
            (self.run_id, context.episode_id, int(suffix[0]))).fetchone() if exists else None
        if attempt is None or attempt["form"] is None or attempt["failure"] is not None:
            _fail("delivery_binding_mismatch")
        form, contract = json.loads(attempt["form"]), json.loads(attempt["contract"])
        schema = contract["measurements"]["schema"]
        return [row for name, node in schema["properties"].items() if node.get("x-source") == "literature_optical_cells" for row in form[name]]

    def receive_cells(self, context, cells, operation_key):
        with self.store.transaction():
            original = self._original_delivery_cells(context, operation_key)
            if original is not None and not _saved_equal(cells, original):
                _fail("delivery_binding_mismatch")
            super().receive_cells(context, cells, operation_key)
            digest = _admitted_digest(cells)
            old = self.store.db.execute("SELECT cells_digest FROM literature_optical_delivery_bindings WHERE run_id=? AND episode_id=? AND operation_key=?",
                (self.run_id, context.episode_id, operation_key)).fetchone()
            if old is not None and old[0] != digest:
                _fail("delivery_binding_mismatch")
            self.store.db.execute("INSERT OR IGNORE INTO literature_optical_delivery_bindings VALUES(?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, digest))

    def _parents(self, scope, direct):
        parents, seen = list(direct), set(direct)
        for reference in parents:
            source = self._native_provenance(scope, reference)
            for ancestor in source.get("parent_source_refs", ()):
                self._native_provenance(scope, ancestor)
                if ancestor not in seen:
                    seen.add(ancestor)
                    parents.append(ancestor)
        return parents

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        request = {"run_id": self.run_id, "episode_id": context.episode_id, "operation_key": operation_key,
            "selected_tool": "literature.optical.populate", "scope": plain(context.scope),
            "assignment": plain(context.assignment), "requested_components": _selected(context.assignment), "arguments": args}
        signature = _signature(request)
        old = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, context.episode_id, operation_key)).fetchone()
        if old is not None:
            if old["signature"] != signature:
                raise ContractError("operation_key_reused_for_different_work")
            outcome = json.loads(old["outcome"])
            saved = self.read(outcome["result"]["sheet_ref"])
            for ref in saved["direct_input_source_refs"]:
                self._native_source(context, ref)
            if self._parents(context.scope, saved["direct_input_source_refs"]) != saved["input_source_refs"]:
                _fail("source_ancestry_mismatch")
            return outcome

        def read_source(reference, representation):
            row = self._native_source(context, reference)
            artifact = row["artifact_ref"] if representation == "original" else row.get("text_ref")
            if artifact is None:
                raise ContractError("literature_source_representation_unavailable")
            return {"artifact_ref": artifact, "content": self.store.get_artifact(artifact)}

        extraction = read_optical_rate_operands(args, read_source=read_source)
        _validate_inputs(args, extraction)
        calculation = calculate_nadh_optical_rate(extraction["calculation_inputs"])
        direct = list(extraction["source_refs"])
        source = self._native_source(context, args["source_ref"])
        payload = {"version": VERSION, "input_source_ref": args["source_ref"], "input_artifact_ref": source["artifact_ref"],
            "direct_input_source_refs": direct, "input_source_refs": self._parents(context.scope, direct),
            "selection": args, "extraction": extraction, "calculation": calculation,
            "cells": {name: deepcopy(calculation[key]) for name, key in CELL_MAP.items()},
            "requested_components": request["requested_components"], "implementation_dependencies": _dependencies()}
        with self.store.transaction():
            created, records = [], []
            def publish(kind, value):
                ref = identity(kind, {"origin": "tool", "record": value})
                exists = self.store.db.execute("SELECT 1 FROM records WHERE id=?", (ref,)).fetchone()
                actual = self.store.put(kind, value, origin="tool", scope=plain(context.scope))
                records.append(actual["id"])
                if exists is None:
                    created.append(actual["id"])
                return actual["id"]
            context_refs, operands, interpretations, covariance = _bindings(extraction, publish)
            payload.update(context_bindings=context_refs, operand_bindings=operands,
                interpretation_bindings=interpretations, covariance_binding_ref=covariance)
            artifact = self.store.artifact(canonical(payload), "application/json")
            request_ref = self.store.artifact(canonical(request), "application/json")
            sheet_ref = publish("source", {"provider": PROVIDER, "accession": None, "uri": None,
                "artifact_ref": artifact, "text_ref": artifact, "request_ref": request_ref, "version": VERSION,
                "retrieved_at": None, "parent_source_refs": payload["input_source_refs"]})
            outcome = {"status": "completed", "operation_ref": identity("operation", {
                "run_id": self.run_id, "episode_id": context.episode_id, "key": operation_key}),
                "record_refs": list(dict.fromkeys([sheet_ref, *records])), "changed_record_refs": created,
                "result": {"sheet_ref": sheet_ref, "cells": payload["cells"], "source_kind": extraction["source_kind"],
                    "evaluation_scope": EVALUATION_SCOPE, "endpoint_kind": "NADH_depletion"}, "feedback": None}
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def read(self, sheet_ref):
        """Authenticate original saved associations; never read scientific bytes."""
        source = self.store.get(sheet_ref)
        if (source.get("id") != sheet_ref or source.get("record_type") != "source" or source.get("provider") != PROVIDER
                or source.get("version") != VERSION or source.get("origin") != "tool" or not source.get("request_ref")):
            _fail("sheet_required")
        request = json.loads(self.store.get_artifact(source["request_ref"]))
        _keys(request, _REQUEST_FIELDS)
        if request["run_id"] != self.run_id:
            _fail("sheet_run_mismatch")
        if request["selected_tool"] != "literature.optical.populate" or request["requested_components"] != _selected(request["assignment"]):
            _fail("operation_binding_mismatch")
        selected = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request["episode_id"], request["operation_key"])).fetchone()
        if selected is None:
            raise ContractError("literature_sheet_not_selected_output")
        outcome = json.loads(selected["outcome"])
        if (selected["signature"] != _signature(request) or outcome.get("status") != "completed"
                or outcome.get("operation_ref") != identity("operation", {"run_id": self.run_id, "episode_id": request["episode_id"], "key": request["operation_key"]})
                or outcome.get("result", {}).get("sheet_ref") != sheet_ref):
            _fail("operation_binding_mismatch")
        saved = json.loads(self.store.get_artifact(source["artifact_ref"]))
        _keys(saved, _PAYLOAD_FIELDS)
        if (saved["version"] != VERSION or saved["selection"] != request["arguments"]
                or saved["input_source_ref"] != saved["selection"].get("source_ref")
                or saved["requested_components"] != request["requested_components"]
                or saved["direct_input_source_refs"] != saved["extraction"]["source_refs"]
                or source.get("parent_source_refs") != saved["input_source_refs"]
                or source.get("text_ref") != source["artifact_ref"]
                or self._parents(request["scope"], saved["direct_input_source_refs"]) != saved["input_source_refs"]
                or saved["implementation_dependencies"] != _dependencies()):
            _fail("saved_mismatch")
        _validate_inputs(saved["selection"], saved["extraction"])
        _validate_calculation(saved)
        if not _saved_equal(outcome["result"], {"sheet_ref": sheet_ref, "cells": saved["cells"], "source_kind": saved["extraction"]["source_kind"],
                "evaluation_scope": EVALUATION_SCOPE, "endpoint_kind": "NADH_depletion"}):
            _fail("outcome_mismatch")
        root = self.store.get(saved["input_source_ref"])
        if root.get("artifact_ref") != saved["input_artifact_ref"]:
            _fail("source_mismatch")
        for witness in _witnesses(saved["extraction"]):
            row = self._native_provenance(request["scope"], witness["source_ref"])
            actual = row["artifact_ref"] if witness["representation"] == "original" else row.get("text_ref")
            if actual != witness["artifact_ref"] or witness["source_ref"] not in saved["direct_input_source_refs"]:
                _fail("source_mismatch")
        covariance = saved["extraction"]["covariance_source"]
        if covariance and self.store.get(covariance["source_ref"])["artifact_ref"] != covariance["artifact_ref"]:
            _fail("source_mismatch")
        records = []
        def expected(kind, value):
            ref = identity(kind, {"origin": "tool", "record": value})
            actual = self.store.get(ref)
            if (actual.get("id") != ref or actual.get("record_type") != kind or actual.get("origin") != "tool"
                    or not _saved_equal({key: actual.get(key) for key in value}, value)):
                _fail("binding_mismatch")
            records.append(ref)
            return ref
        bindings = _bindings(saved["extraction"], expected)
        if not _saved_equal(bindings, (saved["context_bindings"], saved["operand_bindings"], saved["interpretation_bindings"], saved["covariance_binding_ref"])):
            _fail("binding_mismatch")
        if outcome.get("record_refs") != list(dict.fromkeys([sheet_ref, *records])):
            _fail("operation_records_mismatch")
        if any(ref not in outcome["record_refs"] for ref in outcome.get("changed_record_refs", ())):
            _fail("operation_records_mismatch")
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        components = list(self.components) if components is None else list(components)
        selected = _selected({"requested_optical_components": components})
        result = []
        for ref in dict.fromkeys(sheet_refs):
            if ref not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            saved = self.read(ref)
            extraction = saved["extraction"]
            covariance = extraction["covariance_source"]
            for name in selected:
                cell = saved["cells"][name]
                result.append({"sheet_ref": ref, "evidence_source_ref": saved["input_source_ref"], "component": name,
                    **{k: cell[k] for k in ("value", "status", "origin", "unavailable_reason")},
                    "unit": RETURN_UNITS.get(cell["unit"], cell["unit"]), "formula_code": FORMULA_CODES[name],
                    "conditional_on": list(CONDITIONS[:1] if name == "net_rate" else CONDITIONS),
                    "evaluation_scope": EVALUATION_SCOPE, "endpoint_kind": "NADH_depletion",
                    "endpoint_assignment": "conditional_on_selected_extinction_relation", "source_kind": extraction["source_kind"],
                    "source_origin": {"primary_source": "reported", "retained_extraction": "derived", "synthetic_fixture": "synthetic"}[extraction["source_kind"]],
                    "context": {key: {"ref": value, "unavailable_reason": None if value else "source_context_unreported"}
                        for key, value in saved["context_bindings"].items()},
                    "interpretations": deepcopy(saved["interpretation_bindings"]),
                    "covariance": {"source_ref": covariance["source_ref"] if covariance else None,
                        "binding_ref": saved["covariance_binding_ref"], "status": extraction["calculation_inputs"]["covariance_status"],
                        "origin": covariance["data"]["origin"] if covariance else None,
                        "unavailable_reason": "covariance_unreported" if covariance is None else "covariance_status_unknown" if extraction["calculation_inputs"]["covariance_status"] == "unknown" else None},
                    "operands": deepcopy(saved["operand_bindings"])})
        return result

    def validate_cells(self, cells, *, sheet_refs, permitted_record_refs, components=None):
        expected = self.project_cells(sheet_refs, permitted_record_refs=permitted_record_refs, components=components)
        if not _saved_equal(cells, expected):
            raise ContractError("literature_rate_return_differs_from_saved_cells")

    def validate_returned_values(self, cells, *, permitted_record_refs):
        seen = set()
        for row in cells:
            key = (row["sheet_ref"], row["component"])
            if key in seen:
                raise ContractError("duplicate_literature_rate_return_cell")
            seen.add(key)
            expected = self.project_cells([row["sheet_ref"]], permitted_record_refs=permitted_record_refs, components=[row["component"]])
            if not _saved_equal(row, expected[0]):
                raise ContractError("literature_rate_return_differs_from_saved_cells")

    def fact_cells(self, context, sheet_refs, *, components):
        """Own sheets can project; child sheets forward only actually admitted cells."""
        selected = _selected({"requested_optical_components": list(components)})
        received = {(row["sheet_ref"], row["component"]): row for row in self.received_cells(context)}
        result = []
        for ref in dict.fromkeys(sheet_refs):
            if ref not in context.received_record_refs:
                raise ContractError("literature_sheet_not_received")
            self.read(ref)
            source = self.store.get(ref)
            owner = json.loads(self.store.get_artifact(source["request_ref"]))["episode_id"]
            if owner == context.episode_id:
                result.extend(self.project_cells([ref], permitted_record_refs=context.received_record_refs, components=selected))
            else:
                result.extend(deepcopy(received[(ref, name)]) for name in selected if (ref, name) in received)
        return result

    def received_cells(self, context):
        for receipt in self.store.db.execute(f"SELECT operation_key,cells FROM {self.received_table} WHERE run_id=? AND episode_id=? ORDER BY rowid",
                (self.run_id, context.episode_id)):
            cells = json.loads(receipt["cells"])
            bound = self.store.db.execute("SELECT cells_digest FROM literature_optical_delivery_bindings WHERE run_id=? AND episode_id=? AND operation_key=?",
                (self.run_id, context.episode_id, receipt["operation_key"])).fetchone()
            original = self._original_delivery_cells(context, receipt["operation_key"])
            if (bound is None or bound[0] != _admitted_digest(cells)
                    or original is not None and not _saved_equal(original, cells)):
                _fail("delivery_binding_mismatch")
        rows = super().received_cells(context)
        self.validate_returned_values(rows, permitted_record_refs=[row["sheet_ref"] for row in rows])
        return rows


def optical_cells_schema():
    def enum(values, nullable=False):
        return {"type": ["string", "null"] if nullable else "string", "enum": [*values, None] if nullable else list(values)}
    def ref(namespace="reference", nullable=True):
        return {"type": ["string", "null"] if nullable else "string", "format": "reference", "x-reference-namespace": namespace}
    def refs():
        return {"type": "array", "uniqueItems": True, "items": ref(nullable=False)}
    context = {name: obj({"ref": ref("context" if name == "condition" else "reference"),
        "unavailable_reason": enum(["source_context_unreported"], True)}) for name in LITERAL_FIELDS}
    operand = obj({**{name: ref("context" if name == "condition_ref" else "reference") for name in _OPERAND_REFS},
        "measurement_source_ref": ref("source"),
        "qualification": enum(QUALIFICATIONS), "approximate": {"type": ["boolean", "null"]},
        "observed_relation": enum(["point", "lt", "le", "gt", "ge"], True),
        "observation_status": enum(["observed", "censored", "unavailable", "unreported"]),
        "source_origin": enum(ORIGINS, True), "converted_origin": enum(ORIGINS, True),
        "canonical_unit": enum(["absorbance/min", "absorbance", "mM_inverse_cm_inverse", "cm", "nm"], True),
        "input_status": enum(["available", "unavailable", "context_only"]),
        "input_unavailable_reasons": {"type": "array", "uniqueItems": True, "items": enum(INPUT_REASONS)}})
    return {"type": "array", "x-source": "literature_optical_cells", "items": obj({
        "sheet_ref": ref("source", False), "evidence_source_ref": ref("source", False),
        "component": enum(COMPONENTS), "value": {"type": ["number", "null"]}, "unit": enum(["uM/min", "uM2/min2"]),
        "status": enum(["populated", "unavailable"]), "origin": enum(["derived"]),
        "unavailable_reason": enum(REASONS, True), "formula_code": enum(FORMULA_CODES.values()),
        "conditional_on": {"type": "array", "uniqueItems": True, "items": enum(CONDITIONS)},
        "evaluation_scope": enum([EVALUATION_SCOPE]), "endpoint_kind": enum(["NADH_depletion"]),
        "endpoint_assignment": enum(["conditional_on_selected_extinction_relation"]),
        "source_kind": enum(SOURCE_KINDS), "source_origin": enum(ORIGINS), "context": obj(context),
        "interpretations": obj({name: obj({"value": enum(values), "witness_refs": refs()}) for name, values in INTERPRETATIONS.items()}),
        "covariance": obj({"source_ref": ref("source"), "binding_ref": ref(), "status": enum(["known", "estimated", "unknown"]),
            "origin": enum(ORIGINS, True), "unavailable_reason": enum(["covariance_unreported", "covariance_status_unknown"], True)}),
        "operands": obj({name: deepcopy(operand) for name in (*PRIMITIVE_ORDER, "wavelength_context")})})}


__all__ = ["PROVIDER", "VERSION", "COMPONENTS", "LiteratureOpticalRepository", "optical_cells_schema"]
