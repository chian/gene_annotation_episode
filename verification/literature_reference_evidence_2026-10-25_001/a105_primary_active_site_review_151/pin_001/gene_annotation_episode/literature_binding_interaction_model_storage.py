"""Selected conditional binding interaction precision/evidence cells over a committed sheet.

This operation preserves the native sheet, its original inputs and eight cells.
Replay validates and copies saved results without reading scientific originals,
parsing models, calculating cells, calling a model or adding observations.
"""
from copy import deepcopy
import hashlib
import json
import math

from .communication import plain
from .domain import ContractError, REF, NULL_REF, canonical, identity, obj, validate_schema
from .literature_assay_inputs import _Sources, _witness_schema
from .literature_binding_interaction_calculations import (
    ROLES, UNCERTAINTY_PARTIAL_CODES, populate_binding_interaction, _validate_model as validate_binding_interaction_model,
)
from .literature_binding_interaction_validation import COMPONENTS as NATIVE_COMPONENTS, MODEL_COMPONENTS, CALCULATION_REASONS
ALL_COMPONENTS = (*NATIVE_COMPONENTS, *MODEL_COMPONENTS)
FORMULAS = dict(zip(MODEL_COMPONENTS, ("c' C c; c=(-1,1,1,-1)", "sqrt(c' C c)", "e * abs(e) / (2 * V)", "tanh(S / 2)")))
from .literature_binding_interaction_storage import LiteratureBindingInteractionRepository, binding_interaction_cells_schema
from .literature_rate_storage import LiteratureRateRepository
from .literature_binding_interaction_model_inputs import read_binding_interaction_model

PROVIDER = "literature.a105.binding_interaction_model_population"
VERSION = "literature_binding_interaction_model_population_record_v1"
COMPONENTS = MODEL_COMPONENTS
FORMULA_CODES = {name: "binding_interaction_model_" + name + "_v1" for name in COMPONENTS}
FORMULA_MEANINGS = {FORMULA_CODES[name]: FORMULAS[name] for name in COMPONENTS}
VIEW = "binding_interaction_log_model_components"
REASONS = (*CALCULATION_REASONS, "observation_model_missing", "covariance_status_unknown",
    "variance_representation_range", "censored_joint_likelihood_unimplemented", "covariance_estimated_not_known",
    "normal_log_observation_model_unspecified", "zero_interaction_variance",
    "profile_log_ratio_representation_range", "signed_index_representation_range",
    "common_parameter_kind_unknown", "common_parameter_kind_conflicting", "common_parameter_kind_source_unavailable")
QUALIFICATIONS = (
    "dependent_representations", "reported_parameter_not_intrinsic_affinity",
    "physical_owners_do_not_establish_independence", "common_conditions_claim_conflicts_with_canonical_ids",
    "signed_index_rounded_endpoint_not_certainty", "printed_limits_are_not_parameter_or_confidence_bounds",
    "censored_joint_likelihood_unimplemented", "censor_reporting_event_unknown",
    *("common_conditions_" + status for status in ("matched", "not_matched", "unknown", "conflicting")),
    *(code + ":" + role for code in UNCERTAINTY_PARTIAL_CODES for role in ROLES),
    *("canonical_" + field + suffix for field in ("readout", "normalization", "preparation", "experiment", "conditions", "tracer")
        for suffix in ("_partly_unknown", "_differs")),
)
REQUESTED = "requested_binding_interaction_model_components"


def binding_interaction_model_population_schema():
    return obj({"source_ref": deepcopy(REF), "model_source_ref": deepcopy(NULL_REF),
        "model_witnesses": {"type": "array", "items": _witness_schema()}})


def _selected(assignment):
    values = plain(assignment).get(REQUESTED, list(COMPONENTS))
    if (not isinstance(values, (list, tuple)) or any(type(v) is not str or v not in COMPONENTS for v in values)
            or len(values) != len(set(values))):
        raise ContractError("literature_binding_interaction_model_component_selection_invalid")
    return list(values)


def _fail():
    raise ContractError("literature_binding_interaction_model_saved_mismatch")


def _metadata(calculation):
    model = calculation["model"] if calculation else None
    return {"variance_status": model["variance_status"] if model else "not_supplied",
        "distribution": model["distribution"] if model else "not_supplied",
        "log_basis": model["log_basis"] if model else "not_supplied",
        "reporting_event": model["reporting_event"] if model else "not_supplied"}


def _cells(calculation, native):
    result = {}
    for name in COMPONENTS:
        cell = calculation["cells"][name] if calculation else None
        result[name] = {"value": cell["value"] if cell else None, "threshold": None,
            "relation": cell["relation"] if cell and cell["relation"] else "none",
            "unit": "dimensionless_squared" if name == COMPONENTS[0] else "dimensionless",
            "status": "populated" if cell and cell["status"] == "computed" else "unavailable",
            "origin": "derived", "unavailable_reason": cell["reason"] if cell else native["extraction"]["calculation_input_status"],
            "calculation_unavailable_reason": cell["reason"] if cell else None, "bound_kind": None}
    return result


class LiteratureBindingInteractionModelRepository(LiteratureRateRepository):
    provider = PROVIDER
    record_version = VERSION
    components = COMPONENTS
    operations_table = "literature_binding_interaction_model_operations"
    received_table = "literature_binding_interaction_model_received"
    binding_fields = ()

    def __init__(self, store, run_id):
        # Discovery/reconstruction must work on a query-only saved store, even
        # when this optional operation has never been selected there.
        if type(run_id) is not str or not run_id:
            raise ValueError("explicit_literature_run_required")
        self.store, self.run_id = store, run_id

    def _installed(self, table):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

    def _install(self):
        super().__init__(self.store, self.run_id)

    def _native(self):
        # Native read has no writes. Avoid its legacy table-installing constructor.
        repo = LiteratureBindingInteractionRepository.__new__(LiteratureBindingInteractionRepository)
        repo.store, repo.run_id = self.store, self.run_id
        return repo

    def _native_provenance(self, scope, reference):
        source = super()._native_provenance(scope, reference)
        record = {k: v for k, v in source.items() if k not in ("id", "record_type", "origin")}
        if source.get("id") != reference or identity("source", {"origin": source["origin"], "record": record}) != reference:
            raise ContractError("literature_binding_interaction_model_source_identity_mismatch")
        return source

    def _parents(self, scope, direct):
        references = self._native()._parents(scope, direct)
        for reference in references:
            self._native_provenance(scope, reference)
        return references

    def _json(self, reference):
        raw = self.store.get_artifact(reference)
        if reference != "artifact_" + hashlib.sha256(raw).hexdigest():
            _fail()
        return json.loads(raw)

    def _result(self, saved, sheet_ref):
        native = self._native().read(saved["input_source_ref"])
        cells = _cells(saved["calculation"], native)
        return {"view": VIEW, "cells": {name: deepcopy(cells[name]) for name in saved["requested_components"]},
            **_metadata(saved["calculation"]),
            "operand_mask": {"reference_refs": [*self._semantic_refs(native), *saved["model_support_refs"]],
                "locations": [*[location for role in native["role_bindings"].values() for location in role["numeric_locations"]],
                    *self._model_locations(saved)]},
            "rows": self._project_saved(sheet_ref, saved, native, saved["requested_components"])}

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if type(operation_key) is not str or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        validate_schema(args, binding_interaction_model_population_schema())
        request = {"run_id": self.run_id, "episode_id": context.episode_id, "operation_key": operation_key,
            "selected_tool": "literature.binding.interaction.model.populate", "arguments": args,
            "scope": plain(context.scope), "assignment": plain(context.assignment),
            "requested_components": _selected(context.assignment)}
        signature = canonical(request)
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
        source = self._native_source(context, args["source_ref"])
        native = self._native().read(source["id"])
        direct = [source["id"]]
        model_source = None
        if args["model_source_ref"] is not None:
            model_source = self._native_source(context, args["model_source_ref"])
            direct.append(model_source["id"])
            if not args["model_witnesses"]:
                raise ContractError("binding_interaction_model_witness_required")
        elif args["model_witnesses"]:
            raise ContractError("binding_interaction_model_source_required_for_witnesses")
        def read_source(reference, representation):
            row = self._native_source(context, reference)
            artifact = row["artifact_ref"] if representation == "original" else row.get("text_ref")
            if artifact is None:
                raise ContractError("literature_source_representation_unavailable")
            raw = self.store.get_artifact(artifact)
            if artifact != "artifact_" + hashlib.sha256(raw).hexdigest():
                raise ContractError("literature_binding_interaction_model_support_artifact_mismatch")
            return {"artifact_ref": artifact, "content": raw}
        sources = _Sources(read_source)
        witnesses = [sources.witness(w, f"model_witnesses[{i}]") for i, w in enumerate(args["model_witnesses"])]
        direct.extend(sources.references)
        model = None
        if model_source is not None and native["calculation"] is not None:
            raw_model = self.store.get_artifact(model_source["artifact_ref"])
            if "artifact_" + hashlib.sha256(raw_model).hexdigest() != model_source["artifact_ref"]:
                raise ContractError("literature_binding_interaction_model_source_artifact_mismatch")
            parsed = read_binding_interaction_model({"source_ref": model_source["id"], "artifact_ref": model_source["artifact_ref"],
                "content": raw_model}, inputs=native["extraction"]["calculation_inputs"])
            model = parsed["model"]
            if model["reporting_event_source"] is not None and model["reporting_event_source"] not in [
                    {"kind": "utf8_span", **{k: w[k] for k in ("source_ref", "artifact_ref", "start", "end")}} for w in witnesses]:
                raise ContractError("binding_interaction_reporting_event_witness_required")
        calculation = populate_binding_interaction(native["extraction"]["calculation_inputs"], model) if native["calculation"] is not None else None
        saved = {"version": VERSION, "input_source_ref": source["id"], "input_artifact_ref": source["artifact_ref"],
            "model_source_ref": args["model_source_ref"], "model_witnesses": witnesses,
            "direct_input_source_refs": list(dict.fromkeys(direct)),
            "input_source_refs": self._parents(context.scope, list(dict.fromkeys(direct))),
            "requested_components": request["requested_components"], "calculation": calculation}
        with self.store.transaction():
            self._install()
            supports, created = [], []
            for value in self._support_records(witnesses):
                candidate = identity("reference", {"origin": "tool", "record": value})
                exists = self.store.db.execute("SELECT 1 FROM records WHERE id=?", (candidate,)).fetchone()
                support = self.store.put("reference", value, origin="tool", scope=plain(context.scope))["id"]
                supports.append(support)
                if exists is None:
                    created.append(support)
            saved["model_support_refs"] = supports
            artifact = self.store.artifact(canonical(saved), "application/json")
            request_ref = self.store.artifact(canonical(request), "application/json")
            record = {"provider": PROVIDER, "accession": None, "uri": None, "artifact_ref": artifact,
                "text_ref": artifact, "request_ref": request_ref, "version": VERSION, "retrieved_at": None,
                "parent_source_refs": saved["input_source_refs"]}
            candidate = identity("source", {"origin": "tool", "record": record})
            existed = self.store.db.execute("SELECT 1 FROM records WHERE id=?", (candidate,)).fetchone()
            row = self.store.put("source", record, origin="tool", scope=plain(context.scope))
            # Semantic refs are inherited saved bindings, not newly measured facts.
            semantic = self._semantic_refs(native)
            outcome = {"status": "completed", "operation_ref": identity("operation", {"run_id": self.run_id,
                "episode_id": context.episode_id, "key": operation_key}),
                "record_refs": list(dict.fromkeys([row["id"], *saved["direct_input_source_refs"], *semantic, *supports])),
                "changed_record_refs": [*created, *([] if existed else [row["id"]])],
                "result": {"sheet_ref": row["id"], **self._result(saved, row["id"])}, "feedback": None}
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    @staticmethod
    def _support_records(witnesses):
        for witness in witnesses:
            anchor = {k: witness[k] for k in ("source_ref", "artifact_ref", "start", "end", "quote")}
            yield {"reference_type": "literature_result", "source_ref": witness["source_ref"],
                "accession": identity("binding_interaction_model_support", witness), "label": "Binding interaction model interpretation support",
                "sequence_ref": None, "molecule": None, "length": None, "term_refs": [], "context_refs": [], "anchor": anchor}

    @staticmethod
    def _semantic_refs(native):
        def refs(value):
            if isinstance(value, dict):
                for child in value.values():
                    yield from refs(child)
            elif isinstance(value, list):
                for child in value:
                    yield from refs(child)
            elif isinstance(value, str) and value.startswith("reference_"):
                yield value
        return list(dict.fromkeys(refs([native["role_bindings"], native["comparison_bindings"], native["common_kind_binding"]])))

    def read(self, sheet_ref):
        try:
            return self._read(sheet_ref)
        except (KeyError, TypeError, ValueError, OverflowError, UnicodeError) as error:
            if isinstance(error, ContractError):
                raise
            raise ContractError("literature_binding_interaction_model_saved_mismatch") from error

    def _read(self, sheet_ref):
        source = self.store.get(sheet_ref)
        record = {k: v for k, v in source.items() if k not in ("id", "record_type", "origin")}
        if (source.get("id") != sheet_ref or source.get("record_type") != "source" or source.get("provider") != PROVIDER
                or source.get("origin") != "tool" or source.get("version") != VERSION
                or identity("source", {"origin": "tool", "record": record}) != sheet_ref):
            _fail()
        request = self._json(source["request_ref"])
        if (set(request) != {"run_id", "episode_id", "operation_key", "selected_tool", "arguments", "scope", "assignment", "requested_components"}
                or request["run_id"] != self.run_id or request["selected_tool"] != "literature.binding.interaction.model.populate"
                or request["requested_components"] != _selected(request["assignment"])):
            _fail()
        validate_schema(request["arguments"], binding_interaction_model_population_schema())
        operation = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request["episode_id"], request["operation_key"])).fetchone()
        if operation is None or operation["signature"] != canonical(request):
            _fail()
        saved = self._json(source["artifact_ref"])
        if (set(saved) != {"version", "input_source_ref", "input_artifact_ref", "model_source_ref", "model_witnesses",
                "direct_input_source_refs", "input_source_refs", "requested_components", "calculation", "model_support_refs"}
                or saved["version"] != VERSION or saved["input_source_ref"] != request["arguments"]["source_ref"]
                or saved["model_source_ref"] != request["arguments"]["model_source_ref"]
                or saved["requested_components"] != request["requested_components"]
                or source["parent_source_refs"] != saved["input_source_refs"] or source["text_ref"] != source["artifact_ref"]):
            _fail()
        native_source = self._native_provenance(request["scope"], saved["input_source_ref"])
        native = self._native().read(saved["input_source_ref"])
        if native_source["artifact_ref"] != saved["input_artifact_ref"]:
            _fail()
        direct = [saved["input_source_ref"]]
        if saved["model_source_ref"] is not None:
            direct.append(saved["model_source_ref"])
        if len(saved["model_witnesses"]) != len(request["arguments"]["model_witnesses"]):
            _fail()
        for selected, witness in zip(request["arguments"]["model_witnesses"], saved["model_witnesses"]):
            meta = self._native_provenance(request["scope"], witness["source_ref"])
            artifact = meta["artifact_ref"] if witness["representation"] == "original" else meta.get("text_ref")
            if (set(witness) != {*selected, "artifact_ref"} or {k: witness[k] for k in selected} != selected
                    or witness["artifact_ref"] != artifact or type(witness["start"]) is not int or type(witness["end"]) is not int
                    or witness["start"] < 0 or witness["end"] <= witness["start"]
                    or len(witness["quote"].encode()) != witness["end"] - witness["start"]
                    or witness["end"] > self.store.get(artifact)["size"]):
                _fail()
            direct.append(witness["source_ref"])
        if (saved["direct_input_source_refs"] != list(dict.fromkeys(direct))
                or saved["input_source_refs"] != self._parents(request["scope"], saved["direct_input_source_refs"])):
            _fail()
        supports = []
        for value in self._support_records(saved["model_witnesses"]):
            reference = identity("reference", {"origin": "tool", "record": value})
            actual = self.store.get(reference)
            if (actual.get("record_type") != "reference" or actual.get("origin") != "tool"
                    or canonical({k: actual.get(k) for k in value}) != canonical(value)):
                _fail()
            supports.append(reference)
        if saved["model_support_refs"] != supports:
            _fail()
        calculation, original = saved["calculation"], native["calculation"]
        model = calculation["model"] if calculation else None
        if original is None:
            if calculation is not None:
                _fail()
        else:
            if set(calculation) != set(original) or set(calculation["cells"]) != set(ALL_COMPONENTS):
                _fail()
            for field in original:
                if field not in ("model", "cells", "qualifications") and canonical(calculation[field]) != canonical(original[field]):
                    _fail()
            for name in NATIVE_COMPONENTS:
                if canonical(calculation["cells"][name]) != canonical(original["cells"][name]):
                    _fail()
        if saved["model_source_ref"] is None:
            if model is not None or saved["model_witnesses"] or calculation != original:
                _fail()
        else:
            # Even unavailable native inputs retain actual model-source custody;
            # they do not establish that its scientific model was parsed.
            self._native_provenance(request["scope"], saved["model_source_ref"])
            if not saved["model_witnesses"]:
                _fail()
        if saved["model_source_ref"] is not None and original is not None:
            meta = self._native_provenance(request["scope"], saved["model_source_ref"])
            expected_locator = {"source_ref": meta["id"], "artifact_ref": meta["artifact_ref"], "kind": "utf8_span",
                "start": 0, "end": self.store.get(meta["artifact_ref"])["size"]}
            if not saved["model_witnesses"] or model is None or model["source"] != expected_locator:
                _fail()
            validate_binding_interaction_model(model, original["inputs"], original["operand_keys"])
            if model["reporting_event_source"] is not None and model["reporting_event_source"] not in [
                    {"kind": "utf8_span", **{k: w[k] for k in ("source_ref", "artifact_ref", "start", "end")}} for w in saved["model_witnesses"]]:
                _fail()
        if calculation is not None:
            qualifications = list(original["qualifications"])
            if model is not None and model["reporting_event"] == "source_defined":
                qualifications = [q for q in qualifications if q != "censor_reporting_event_unknown"]
            if calculation["cells"]["signed_index"]["value"] in (-1., 1.):
                position = next((i for i, code in enumerate(qualifications)
                    if code.startswith("canonical_") or code == "printed_limits_are_not_parameter_or_confidence_bounds"), len(qualifications))
                qualifications.insert(position, "signed_index_rounded_endpoint_not_certainty")
            if calculation["qualifications"] != qualifications:
                _fail()
        outcome = json.loads(operation["outcome"])
        expected_result = {"sheet_ref": sheet_ref, **self._result(saved, sheet_ref)}
        if (outcome.get("status") != "completed" or canonical(outcome.get("result")) != canonical(expected_result)
                or outcome.get("operation_ref") != identity("operation", {"run_id": self.run_id, "episode_id": request["episode_id"], "key": request["operation_key"]})
                or outcome["record_refs"] != list(dict.fromkeys([sheet_ref, *saved["direct_input_source_refs"], *self._semantic_refs(native), *supports]))
                or any(ref not in [sheet_ref, *supports] for ref in outcome["changed_record_refs"])):
            _fail()
        # Validate types, meanings and prerequisites without numerical replay.
        if calculation is not None:
            for name in COMPONENTS:
                cell = calculation["cells"][name]
                if (set(cell) != {"operands", "formula", "unit", "value", "threshold", "relation", "status", "reason"}
                        or cell["formula"] != FORMULAS[name] or cell["operands"] != list(ROLES)
                        or cell["unit"] != ("dimensionless_squared" if name == COMPONENTS[0] else "dimensionless")
                        or cell["threshold"] is not None):
                    _fail()
                q = cell["value"]
                if q is not None and (type(q) not in (int, float) or not math.isfinite(q)):
                    _fail()
                if (cell["status"] != ("unavailable" if q is None else "computed")
                        or cell["relation"] != (None if q is None else "eq")
                        or (cell["reason"] is None) != (q is not None)
                        or cell["reason"] is not None and cell["reason"] not in REASONS):
                    _fail()
                if q is not None:
                    if model is None or model["variance_status"] == "unknown":
                        _fail()
                    if name in COMPONENTS[:2] and q < 0 or name == "signed_index" and not -1 <= q <= 1:
                        _fail()
                    if name in COMPONENTS[2:] and (model["variance_status"] != "known" or model["distribution"] != "normal"
                            or original["cells"]["log_interaction"]["status"] != "computed"):
                        _fail()
                native_reason = original["cells"]["interaction_ratio"]["reason"]
                # Arithmetic-domain failures do not become relationship gates:
                # the original calculator can still compute covariance/SE.
                if native_reason in ("opposing_reported_limits", "numerical_representation_range"):
                    native_reason = None
                required_reason = native_reason
                model_reason = ("observation_model_missing" if model is None else
                    "covariance_status_unknown" if model["variance_status"] == "unknown" else None)
                if name in COMPONENTS[:2]:
                    required_reason = required_reason or model_reason
                else:
                    log_cell = original["cells"]["log_interaction"]
                    if required_reason is None and log_cell["status"] != "computed":
                        required_reason = log_cell["reason"] if log_cell["status"] == "unavailable" else "censored_joint_likelihood_unimplemented"
                    required_reason = required_reason or model_reason
                    if required_reason is None and model["variance_status"] != "known":
                        required_reason = "covariance_estimated_not_known"
                    if required_reason is None and model["distribution"] != "normal":
                        required_reason = "normal_log_observation_model_unspecified"
                    if required_reason is None and calculation["cells"]["log_interaction_variance"]["value"] == 0:
                        required_reason = "zero_interaction_variance"
                if required_reason is not None and cell["reason"] != required_reason:
                    _fail()
        validate_schema(self._project_saved(sheet_ref, saved, native, COMPONENTS), binding_interaction_model_cells_schema())
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = _selected({REQUESTED: self.components if components is None else components})
        rows = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            saved = self.read(reference)
            native = self._native().read(saved["input_source_ref"])
            rows.extend(self._project_saved(reference, saved, native, selected))
        return rows

    def _model_locations(self, saved):
        locations = [{"kind": "utf8_span", **{k: w[k] for k in ("source_ref", "artifact_ref", "start", "end")}}
            for w in saved["model_witnesses"]]
        if saved["model_source_ref"] is not None:
            meta = self.store.get(saved["model_source_ref"])
            locations.append({"kind": "utf8_span", "source_ref": meta["id"], "artifact_ref": meta["artifact_ref"],
                "start": 0, "end": self.store.get(meta["artifact_ref"])["size"]})
        return locations

    def _project_saved(self, reference, saved, native, selected):
        rows = []
        roles = deepcopy(native["role_bindings"])
        for metadata in roles.values():
            numeric = metadata.pop("numeric_values")
            metadata["values"] = {"delivery_status": "not_requested", **{k: None for k in numeric}}
        cells = _cells(saved["calculation"], native)
        private_locations = self._model_locations(saved)
        for name in selected:
            rows.append({"sheet_ref": reference, "evidence_source_ref": native["input_source_ref"],
                "binding_interaction_sheet_ref": saved["input_source_ref"], "model_source_ref": saved["model_source_ref"],
                "model_support_refs": deepcopy(saved["model_support_refs"]), "model_support_locations": deepcopy(private_locations),
                "view": VIEW, "component": name, **deepcopy(cells[name]), "formula_code": FORMULA_CODES[name],
                **_metadata(saved["calculation"]), "evaluation_scope": "source_binding_discrimination_interaction",
                "contrast_meaning": "reference_form_log_ligand_ratio_minus_test_form_log_ligand_ratio",
                "source_kind": native["extraction"]["source_kind"],
                "qualifications": deepcopy(saved["calculation"]["qualifications"]) if saved["calculation"] else [],
                "model_input_status": ("supplied_native_inputs_unavailable" if native["calculation"] is None else "supplied")
                    if saved["model_source_ref"] else "not_supplied",
                "model_reader_capability": "implemented", "comparison_scope": native["selection"]["comparison_scope"],
                "calculation_input_status": native["extraction"]["calculation_input_status"],
                "common_parameter_kind": deepcopy(native["common_kind_binding"]),
                "relationships": deepcopy(native["comparison_bindings"]), "roles": deepcopy(roles)})
        return rows

    def received_cells(self, context):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        return super().received_cells(context) if self._installed(self.received_table) else []

    def receive_cells(self, context, cells, operation_key):
        with self.store.transaction():
            self._install()
            return super().receive_cells(context, cells, operation_key)


def binding_interaction_model_cells_schema():
    schema = binding_interaction_cells_schema()
    schema["x-source"] = "literature_binding_interaction_model_cells"
    fields = schema["items"]["properties"]
    def enum(values):
        return {"type": "string", "enum": list(values)}
    def ref(namespace, nullable=False):
        return {"type": ["string", "null"] if nullable else "string", "format": "reference", "x-reference-namespace": namespace}
    fields.update({"component": enum(COMPONENTS), "formula_code": enum(FORMULA_CODES.values()),
        "unit": enum(["dimensionless", "dimensionless_squared"]), "origin": enum(["derived"]),
        "status": enum(["populated", "unavailable"]), "relation": enum(["eq", "none"]),
        "threshold": {"type": "null"}, "bound_kind": {"type": "null"},
        "unavailable_reason": {"type": ["string", "null"], "enum": [*REASONS, None]},
        "calculation_unavailable_reason": {"type": ["string", "null"], "enum": [*REASONS, None]},
        "view": enum([VIEW]), "binding_interaction_sheet_ref": ref("source"), "model_source_ref": ref("source", True),
        "model_support_refs": {"type": "array", "items": ref("reference")},
        "model_support_locations": {"type": "array", "items": obj({"kind": enum(["utf8_span"]),
            "source_ref": ref("source"), "artifact_ref": ref("artifact"),
            "start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1}})},
        "model_input_status": enum(["supplied", "not_supplied", "supplied_native_inputs_unavailable"]),
        "model_reader_capability": enum(["implemented"]),
        "variance_status": enum(["known", "estimated", "unknown", "not_supplied"]),
        "distribution": enum(["normal", "unspecified", "not_supplied"]),
        "log_basis": enum(["natural_log_nM", "not_supplied"]),
        "reporting_event": enum(["unknown", "source_defined", "not_supplied"]),
        "source_kind": enum(["synthetic_fixture", "primary_source"]),
        "qualifications": {"type": "array", "uniqueItems": True, "items": enum(QUALIFICATIONS)},
        "contrast_meaning": enum(["reference_form_log_ligand_ratio_minus_test_form_log_ligand_ratio"])})
    schema["items"]["required"] = list(fields)
    return schema


__all__ = ["PROVIDER", "VERSION", "COMPONENTS", "VIEW", "FORMULA_CODES", "FORMULA_MEANINGS",
    "LiteratureBindingInteractionModelRepository", "binding_interaction_model_population_schema", "binding_interaction_model_cells_schema"]
