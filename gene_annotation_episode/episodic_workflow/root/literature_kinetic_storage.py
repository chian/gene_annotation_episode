"""Selected native kinetic estimates; exact saved return subsets, no credit.

Only the five native parameter/contrast meanings are exposed by this route.
The source model/covariance reader is unfinished work, not a paper finding.
"""
from copy import deepcopy
import hashlib
import json

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.domain import ContractError, canonical, identity, obj
from .literature_rate_storage import LiteratureRateRepository
from .library.literature_kinetic_inputs import (
    read_kinetic_inputs, kinetic_arguments_schema, SUBJECT_FIELDS, CONTEXT_FIELDS,
    PARAMETER_UNITS, COMPARISON_VALUES, QUALIFICATIONS,
    COUNT_STATUSES, COUNT_REASONS, COUNT_NOTATIONS, COUNT_RELATIONS,
    VERSION as EXTRACTION_VERSION,
)
from .library.literature_kinetic_calculations import (
    populate_kinetic_contrast, COMPONENTS as ALL_COMPONENTS, FORMULAS, REASONS,
    CONDITIONAL_CODES,
)
from .library.literature_kinetic_validation import validate_saved_kinetic, witnesses

VERSION = "literature_kinetic_population_record_v3"
from .library.literature_kinetic_return_contracts import (
    PROVIDER, COMPONENTS, FORMULA_CODES, UNIT_CODES, EVALUATION_SCOPE, MODEL_INPUT_STATUS, MODEL_CAPABILITY, kinetic_cells_schema,
)

_REQUEST = ("run_id", "episode_id", "operation_key", "selected_tool", "scope", "assignment", "requested_components", "arguments")
_PAYLOAD = ("version", "input_source_ref", "input_artifact_ref", "direct_input_source_refs", "input_source_refs",
    "selection", "extraction", "calculation", "cells", "role_bindings", "comparison_bindings", "requested_components")


def _fail(code):
    raise ContractError("literature_kinetic_" + code)


def _same(a, b):
    try:
        return canonical(a) == canonical(b)
    except (ValueError, TypeError, OverflowError):
        return False


def _selected(assignment):
    values = plain(assignment).get("requested_kinetic_components", list(COMPONENTS))
    if (not isinstance(values, (list, tuple)) or any(type(v) is not str or v not in COMPONENTS for v in values)
            or len(values) != len(set(values))):
        _fail("component_selection_invalid")
    return list(values)


def _signature(request):
    return canonical({k: request[k] for k in _REQUEST if k != "selected_tool"})


def _witness_label(quote):
    """Bound display text only; the exact original witness stays in its anchor."""
    if len(quote) <= 512 and "\n" not in quote and "\r" not in quote:
        return quote
    prefix = "[source witness preview] "
    preview = " ".join(quote.split())
    available = 512 - len(prefix)
    if len(preview) > available:
        preview = preview[:available - 1] + "…"
    return prefix + preview


def _bindings(extraction, publish):
    def ref(witness, kind, number=None):
        if witness is None:
            return None
        anchor = {k: witness[k] for k in ("source_ref", "artifact_ref", "start", "end", "quote")}
        if number is not None:
            ns = number["selector"]
            anchor.update(start=witness["start"] + len(witness["quote"][:ns["number_start"]].encode()),
                end=witness["start"] + len(witness["quote"][:ns["number_end"]].encode()), quote=number["raw_number"])
        return publish("reference", {"reference_type": "literature_result", "source_ref": witness["source_ref"],
            "accession": identity("kinetic_" + kind, anchor), "label": _witness_label(anchor["quote"]), "sequence_ref": None,
            "molecule": None, "length": None, "term_refs": [], "context_refs": [], "anchor": anchor})

    def token(number, kind):
        return ref(number["selector"]["witness"], kind, number) if number else None

    def interpreted(row, kind):
        return {"value": row["value"], "witness_refs": list(dict.fromkeys(ref(w, kind) for w in row["witnesses"]))}

    roles = {}
    for role in ("numerator", "denominator"):
        row = extraction["operands"][role]
        canonical_operand = row["calculation_operand"] if row else None
        number = row["number"] if row else None
        uncertainty = row["uncertainty"] if row else None
        numbers = []
        def numeric(reference, source):
            if reference:
                numbers.append({"ref": reference, "source_ref": source})
            return reference
        measurement = token(number, "measurement")
        numeric(measurement, number["selector"]["witness"]["source_ref"] if number else None)
        uncertainty_refs = {}
        for name in ("magnitude", "count", "interval", "confidence_level"):
            native = uncertainty[name] if uncertainty else None
            if native is None:
                uncertainty_refs[name + "_ref"] = None
                continue
            if name in ("magnitude", "count"):
                witness = native["selector"]["witness"]
                reference = token(native, "uncertainty_" + name)
            else:
                witness = native["witness"] if name == "confidence_level" else native["selector"]["witness"]
                reference = ref(witness, "uncertainty_" + name)
            uncertainty_refs[name + "_ref"] = numeric(reference, witness["source_ref"])
        meanings = uncertainty["canonical"] if uncertainty else {"statistic": "unreported", "magnitude": None,
            "interval": None, "confidence_level": None, "count": None, "repetition_basis": "unspecified", "estimate_basis": "unknown"}
        count = uncertainty["count"] if uncertainty else None
        roles[role] = {
            "parameter_kind": row["parameter_kind"]["value"] if row else "unknown",
            "parameter_kind_witness_refs": interpreted(row["parameter_kind"], "parameter_kind")["witness_refs"] if row else [],
            "measurement_ref": measurement,
            "measurement_source_ref": number["selector"]["witness"]["source_ref"] if number else None,
            "physical_observation_ref": ref(row["measurement_identity"], "physical_observation") if row else None,
            "source_unit_ref": ref(row["unit"]["witness"], "unit") if row and row["unit"] else None,
            "canonical_unit": UNIT_CODES.get(row["unit"]["canonical_unit"], row["unit"]["canonical_unit"]) if row and row["unit"] else None,
            "qualification": row["qualification"]["value"] if row else "unknown",
            "qualification_witness_refs": interpreted(row["qualification"], "qualification")["witness_refs"] if row else [],
            "approximate": row["approximate"] if row else None,
            "input_status": canonical_operand["status"] if canonical_operand else "unresolved",
            "observed_relation": number["relation"] if number else None,
            "source_origin": row["source_origin"] if row else None,
            "converted_origin": canonical_operand["origin"] if canonical_operand else None,
            "subject": {k: ref(row["subject"][k], k) if row else None for k in SUBJECT_FIELDS},
            "context": {k: ref(row["context"][k], k) if row else None for k in CONTEXT_FIELDS},
            "uncertainty": {**{k: meanings[k] for k in ("statistic", "repetition_basis", "estimate_basis")},
                "count_reading_status": count["status"] if count else "not_selected",
                "count_unavailable_reason": count["unavailable_reason"] if count else None,
                "count_notation": count["notation"] if count else None,
                "count_relation": count["relation"] if count else None,
                "count_approximate": count["approximate"] if count else None,
                "unit_ref": ref(uncertainty["effective_unit"]["witness"], "uncertainty_unit") if uncertainty and uncertainty["effective_unit"] else None,
                "canonical_unit": UNIT_CODES.get(uncertainty["effective_unit"]["canonical_unit"], uncertainty["effective_unit"]["canonical_unit"]) if uncertainty and uncertainty["effective_unit"] else None,
                **uncertainty_refs, "unavailable_reason": uncertainty["unavailable_reason"] if uncertainty else None},
            "uncertainty_canonical": {**deepcopy(meanings), "count_reported_value": count["value"] if count else None},
            "numeric_tokens": numbers,
            "input_unavailable_reasons": list(extraction["input_unavailable_reasons"][role]),
        }
    comparison = {k: interpreted(extraction["comparison"][k], k) for k in COMPARISON_VALUES}
    return roles, comparison


class LiteratureKineticRepository(LiteratureRateRepository):
    provider = PROVIDER
    record_version = VERSION
    components = COMPONENTS
    operations_table = "literature_kinetic_operations"
    received_table = "literature_kinetic_received"
    binding_fields = ()

    def __init__(self, store, run_id):
        if type(run_id) is not str or not run_id:
            raise ValueError("explicit_literature_run_required")
        self.store, self.run_id = store, run_id

    def _installed(self, table):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

    def _install(self):
        super().__init__(self.store, self.run_id)

    def _parents(self, scope, direct):
        result, seen = list(direct), set(direct)
        for reference in result:
            for parent in self._native_provenance(scope, reference).get("parent_source_refs", ()):
                self._native_provenance(scope, parent)
                if parent not in seen:
                    seen.add(parent)
                    result.append(parent)
        return result

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if type(operation_key) is not str or not operation_key:
            raise ContractError("operation_key_required")
        request = {"run_id": self.run_id, "episode_id": context.episode_id, "operation_key": operation_key,
            "selected_tool": "literature.kinetic.populate", "scope": plain(context.scope), "assignment": plain(context.assignment),
            "requested_components": _selected(context.assignment), "arguments": plain(arguments)}
        signature = _signature(request)
        old = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, context.episode_id, operation_key)).fetchone() if self._installed(self.operations_table) else None
        if old is not None:
            if old["signature"] != signature:
                raise ContractError("operation_key_reused_for_different_work")
            outcome = json.loads(old["outcome"])
            saved = self.read(outcome["result"]["sheet_ref"])
            for reference in saved["direct_input_source_refs"]:
                self._native_source(context, reference)
            return outcome
        def read_source(reference, representation):
            source = self._native_source(context, reference)
            artifact = source["artifact_ref"] if representation == "original" else source.get("text_ref")
            if artifact is None:
                raise ContractError("literature_source_representation_unavailable")
            return {"artifact_ref": artifact, "content": self.store.get_artifact(artifact)}
        extraction = read_kinetic_inputs(request["arguments"], read_source=read_source)
        calculation = populate_kinetic_contrast(extraction["calculation_inputs"])
        validate_saved_kinetic(request["arguments"], extraction, calculation)
        direct = list(extraction["source_refs"])
        root = self._native_source(context, extraction["source_ref"])
        saved = {"version": VERSION, "input_source_ref": extraction["source_ref"], "input_artifact_ref": root["artifact_ref"],
            "direct_input_source_refs": direct, "input_source_refs": self._parents(context.scope, direct),
            "selection": request["arguments"], "extraction": extraction, "calculation": calculation,
            "cells": {k: deepcopy(calculation["cells"][k]) for k in COMPONENTS},
            "requested_components": request["requested_components"]}
        with self.store.transaction():
            self._install()
            created, records = [], []
            def publish(kind, value):
                ref = identity(kind, {"origin": "tool", "record": value})
                exists = self.store.db.execute("SELECT 1 FROM records WHERE id=?", (ref,)).fetchone()
                actual = self.store.put(kind, value, origin="tool", scope=plain(context.scope))
                records.append(actual["id"])
                if exists is None:
                    created.append(actual["id"])
                return actual["id"]
            saved["role_bindings"], saved["comparison_bindings"] = _bindings(extraction, publish)
            artifact = self.store.artifact(canonical(saved), "application/json")
            request_ref = self.store.artifact(canonical(request), "application/json")
            ref = publish("source", {"provider": PROVIDER, "accession": None, "uri": None, "artifact_ref": artifact,
                "text_ref": artifact, "request_ref": request_ref, "version": VERSION, "retrieved_at": None,
                "parent_source_refs": saved["input_source_refs"]})
            result = {"sheet_ref": ref, "cells": saved["cells"], "evaluation_scope": EVALUATION_SCOPE,
                "source_kind": extraction["source_kind"], "model_input_status": MODEL_INPUT_STATUS, "model_reader_capability": MODEL_CAPABILITY}
            outcome = {"status": "completed", "operation_ref": identity("operation", {"run_id": self.run_id,
                "episode_id": context.episode_id, "key": operation_key}), "record_refs": list(dict.fromkeys([ref, *records])),
                "changed_record_refs": created, "result": result, "feedback": None}
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def _artifact_json(self, reference):
        raw = self.store.get_artifact(reference)
        if reference != "artifact_" + hashlib.sha256(raw).hexdigest():
            _fail("saved_artifact_mismatch")
        return json.loads(raw)

    def read(self, sheet_ref):
        try:
            return self._read(sheet_ref)
        except (KeyError, TypeError, ValueError, OverflowError, UnicodeError) as error:
            if isinstance(error, ContractError):
                raise
            raise ContractError("literature_kinetic_saved_mismatch") from error

    def _read(self, sheet_ref):
        source = self.store.get(sheet_ref)
        if (source.get("id") != sheet_ref or source.get("record_type") != "source" or source.get("provider") != PROVIDER
                or source.get("version") != VERSION or source.get("origin") != "tool" or not source.get("request_ref")):
            _fail("sheet_required")
        value = {k: v for k, v in source.items() if k not in ("id", "record_type", "origin")}
        if identity("source", {"origin": "tool", "record": value}) != sheet_ref:
            _fail("saved_source_identity_mismatch")
        request = self._artifact_json(source["request_ref"])
        if set(request) != set(_REQUEST) or request["run_id"] != self.run_id:
            _fail("request_mismatch")
        if request["selected_tool"] != "literature.kinetic.populate" or request["requested_components"] != _selected(request["assignment"]):
            _fail("request_mismatch")
        operation = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request["episode_id"], request["operation_key"])).fetchone() if self._installed(self.operations_table) else None
        if operation is None or operation["signature"] != _signature(request):
            _fail("operation_mismatch")
        outcome = json.loads(operation["outcome"])
        if (outcome.get("status") != "completed" or outcome.get("operation_ref") != identity("operation", {
                "run_id": self.run_id, "episode_id": request["episode_id"], "key": request["operation_key"]})
                or outcome.get("result", {}).get("sheet_ref") != sheet_ref):
            _fail("operation_mismatch")
        saved = self._artifact_json(source["artifact_ref"])
        if set(saved) != set(_PAYLOAD):
            _fail("saved_fields_mismatch")
        if (saved["version"] != source["version"] or not _same(saved["selection"], request["arguments"])
                or saved["input_source_ref"] != request["arguments"]["source_ref"]
                or saved["direct_input_source_refs"] != saved["extraction"]["source_refs"]
                or saved["requested_components"] != request["requested_components"]
                or source.get("parent_source_refs") != saved["input_source_refs"]
                or source.get("text_ref") != source["artifact_ref"]
                or saved["input_source_refs"] != self._parents(request["scope"], saved["direct_input_source_refs"])):
            _fail("saved_mismatch")
        expected_extraction = EXTRACTION_VERSION
        if saved["extraction"]["version"] != expected_extraction:
            _fail("saved_version_mismatch")
        validate_saved_kinetic(saved["selection"], saved["extraction"], saved["calculation"])
        if not _same(saved["cells"], {k: saved["calculation"]["cells"][k] for k in COMPONENTS}):
            _fail("cells_mismatch")
        expected_result = {"sheet_ref": sheet_ref, "cells": saved["cells"], "evaluation_scope": EVALUATION_SCOPE,
            "source_kind": saved["extraction"]["source_kind"], "model_input_status": MODEL_INPUT_STATUS, "model_reader_capability": MODEL_CAPABILITY}
        if not _same(outcome["result"], expected_result):
            _fail("outcome_mismatch")
        if self._native_provenance(request["scope"], saved["input_source_ref"])["artifact_ref"] != saved["input_artifact_ref"]:
            _fail("source_mismatch")
        for witness in witnesses(saved["extraction"]):
            meta = self._native_provenance(request["scope"], witness["source_ref"])
            artifact = meta["artifact_ref"] if witness["representation"] == "original" else meta.get("text_ref")
            if artifact != witness["artifact_ref"] or witness["source_ref"] not in saved["direct_input_source_refs"]:
                _fail("source_mismatch")
        records = []
        def expected(kind, value):
            reference = identity(kind, {"origin": "tool", "record": value})
            actual = self.store.get(reference)
            if (actual.get("id") != reference or actual.get("record_type") != kind or actual.get("origin") != "tool"
                    or not _same({k: actual.get(k) for k in value}, value)):
                _fail("binding_mismatch")
            records.append(reference)
            return reference
        roles, comparison = _bindings(saved["extraction"], expected)
        if not _same((roles, comparison), (saved["role_bindings"], saved["comparison_bindings"])):
            _fail("binding_mismatch")
        if outcome["record_refs"] != list(dict.fromkeys([sheet_ref, *records])) or any(r not in outcome["record_refs"] for r in outcome["changed_record_refs"]):
            _fail("operation_records_mismatch")
        return saved

    def received_cells(self, context):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        return super().received_cells(context) if self._installed(self.received_table) else []

    def receive_cells(self, context, cells, operation_key):
        with self.store.transaction():
            self._install()
            return super().receive_cells(context, cells, operation_key)

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = _selected({"requested_kinetic_components": self.components if components is None else components})
        result = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            saved = self.read(reference)
            for name in selected:
                cell = saved["cells"][name]
                roles = deepcopy(saved["role_bindings"])
                for role, metadata in roles.items():
                    values = metadata.pop("uncertainty_canonical")
                    requested = name == role + "_parameter"
                    metadata["uncertainty_values"] = {"delivery_status": "requested" if requested else "not_requested",
                        **{k: values[k] if requested else None for k in ("magnitude", "interval", "confidence_level", "count", "count_reported_value")}}
                result.append({"sheet_ref": reference, "evidence_source_ref": saved["input_source_ref"], "component": name,
                    **{k: deepcopy(v) for k, v in cell.items() if k != "formula"}, "formula_code": FORMULA_CODES[name],
                    "unit": UNIT_CODES.get(cell["unit"], cell["unit"]),
                    "evaluation_scope": EVALUATION_SCOPE, "contrast_meaning": "numerator_parameter_exceeds_denominator",
                    "model_input_status": MODEL_INPUT_STATUS, "model_reader_capability": MODEL_CAPABILITY,
                    "comparison": deepcopy(saved["comparison_bindings"]), **roles})
        return result


__all__ = ["PROVIDER", "VERSION", "COMPONENTS", "FORMULA_CODES", "LiteratureKineticRepository", "kinetic_cells_schema", "kinetic_arguments_schema"]
