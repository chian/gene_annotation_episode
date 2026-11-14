"""Selected four-cell binding interaction, retained source custody and native returns.

One selected operation reads authenticated retained sources once and optionally
calls the frozen pure calculator. Saved reads authenticate the original request,
outcome, source metadata and bindings without reading experimental bytes or
recomputing science. Only eight native components are callable. A requested raw
parameter row alone expands that role's native/canonical candidates and partial
uncertainty; derived rows contain no unrequested operand numbers.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_rate_storage import LiteratureRateRepository
from .literature_binding_interaction_inputs import (
    read_binding_interaction_inputs, binding_interaction_arguments_schema, ROLES, ID_FIELDS,
    KINDS, STATISTICS, BASES, REPETITIONS, MEASUREMENT_STATUSES, SCALAR_STATUSES,
    UNCERTAINTY_REASONS, ROLE_UNAVAILABLE_REASONS, CALCULATION_INPUT_STATUSES,
)
from .literature_binding_interaction_calculations import populate_binding_interaction, RELATIONS
from .literature_binding_interaction_validation import (
    COMPONENTS, RAW_COMPONENTS, FORMULA_CODES, CALCULATION_REASONS, UNAVAILABLE_REASONS,
    native_cells, validate_saved_binding_interaction,
)
from .literature_experimental_contracts import ExperimentalContractError

PROVIDER = "literature.a105.binding_interaction_population"
VERSION = "literature_binding_interaction_population_record_v1"
EVALUATION_SCOPE = "source_binding_discrimination_interaction"
MODEL_INPUT_STATUS = "not_supplied_by_native_operation"
MODEL_CAPABILITY = "unimplemented"
_REQUEST = ("run_id", "episode_id", "operation_key", "selected_tool", "scope", "assignment", "requested_components", "arguments")
_PAYLOAD = ("version", "input_source_ref", "input_artifact_ref", "direct_input_source_refs", "input_source_refs",
    "source_records", "selection", "extraction", "calculation", "cells", "role_bindings", "comparison_bindings",
    "common_kind_binding", "requested_components", "implementation_dependencies")
_FROZEN = {
    "literature_binding_interaction_inputs.py": "d17ad5095cb08c2da8c51210544c2fd22871e8fddbaade689ee7809e82a95f92",
    "literature_binding_interaction_calculations.py": "ac7ea12c105e16df5085942090ec8e3f96c618b4f5866283325c46c92804b432",
    "literature_binding_visual_inputs.py": "8153f555699cd9b1dea63bd8ccc29869c70e127c205bdb10fd26c979b202b718",
    "literature_binding_reader.py": "e117105486773280edf1dba796ab2be10c61feb6a9c0ad407ba876e2332714a1",
    "literature_experimental_contracts.py": "0d7d4cb57f63c66ae36912e369fbcea557a6b9646c727ed1c60eac229ca3bccc",
    "literature_rate_storage.py": "171eb81f23bcf5b8c048807a093a066f42674f960ac59826cbcb4ae3d94490b4",
}
# The native binding overrides never call the rate-specific population/read
# methods changed by the domain extension. All inherited custody/receipt methods
# are identical in these two exact dependencies. Inspection and cold historical
# reconstruction: tests/test_a105_native_binding_dependency_142.py and
# verification/literature_reference_evidence_2026-10-25_001/
# a105_native_binding_dependency_142/.
_COMPATIBLE_RATE_STORAGE = (
    _FROZEN["literature_rate_storage.py"],
    "66f7b53adfb4fd873386fd04a3bff681c871f29a69848e94567c1792420be541",
)
# An original saved snapshot is admitted as a whole, never as a cross-product
# of individually accepted hashes. Its original metadata and cells stay intact.
_ORIGINAL_DEPENDENCIES = {"sha256": {
    **_FROZEN,
    "literature_binding_interaction_validation.py": "f8bae57a55bc7417acd83788a9082b8f0b7c9298f84cb7c0a9482f2f59673ebc",
    "literature_binding_interaction_storage.py": "0dd5b0bbee30809560a1b39715c05c493c38d94581bbd255ebcbcdee2f6b749e",
    "literature_binding_interaction_render.py": "8f721dc277d444ce051117f94c03e6e7f016f40c6f3318db49348ccf5f316b3c",
}, "validation_version": "binding_interaction_saved_validation_v1"}


def _fail(code):
    raise ContractError("literature_binding_interaction_" + code)


def _same(a, b):
    try:
        return canonical(a) == canonical(b)
    except (ValueError, TypeError, OverflowError):
        return False


def _selected(assignment):
    values = plain(assignment).get("requested_binding_interaction_components", list(COMPONENTS))
    if (not isinstance(values, (list, tuple)) or any(type(v) is not str or v not in COMPONENTS for v in values)
            or len(values) != len(set(values))):
        _fail("component_selection_invalid")
    return list(values)


def _dependencies(saved=...):
    from .literature_binding_interaction_validation import VERSION as validator
    names = [*_FROZEN, "literature_binding_interaction_validation.py", "literature_binding_interaction_storage.py",
        "literature_binding_interaction_render.py"]
    hashes = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in names}
    if any(hashes[name] not in _COMPATIBLE_RATE_STORAGE if name == "literature_rate_storage.py"
            else hashes[name] != expected for name, expected in _FROZEN.items()):
        _fail("implementation_dependency_mismatch")
    current = {"sha256": hashes, "validation_version": validator}
    if saved is not ... and not (_same(saved, current) or _same(saved, _ORIGINAL_DEPENDENCIES)):
        _fail("implementation_dependency_mismatch")
    return current


def _signature(request):
    return canonical({k: request[k] for k in _REQUEST if k != "selected_tool"})


def _preview(text):
    text = " ".join(text.split())
    return text if len(text) <= 120 else "[source witness preview] " + text[:94] + "…"


def _bindings(extraction, publish, source_records):
    """Bind full nominations; image interpretations never acquire text anchors."""
    image_specs = {i["image_id"]: i for i in extraction["selection"]["images"]}
    def witness(value, kind):
        if value is None:
            return None, None
        nominated, located = value["witness"], value["canonical_locator"]
        anchor = None
        if nominated["kind"] == "text":
            source = nominated["source_ref"]
            if value["error"] is None:
                anchor = {k: nominated[k] for k in ("source_ref", "start", "end", "quote")}
                anchor["artifact_ref"] = value["artifact_ref"]
            location = {"kind": "utf8_span" if anchor else "unresolved", "source_ref": source,
                "artifact_ref": value["artifact_ref"] or source_records[source]["artifact_ref"],
                "start": nominated["start"] if anchor else None, "end": nominated["end"] if anchor else None, "region": None}
        else:
            spec = image_specs[nominated["image_id"]]
            source = located["original_source_ref"] if located and value["error"] is None else spec["source_ref"]
            location = {"kind": "image_region" if located and value["error"] is None else "unresolved", "source_ref": source,
                "artifact_ref": located["original_artifact_ref"] if located and value["error"] is None else source_records[source]["artifact_ref"],
                "start": None, "end": None, "region": deepcopy(located["image_region"]) if located and value["error"] is None else None}
        record = {"reference_type": "literature_result", "source_ref": source,
            "accession": identity("binding_interaction_" + kind, {"selection": nominated, "result": value,
                "image": image_specs.get(nominated.get("image_id")), "source": source_records[source]}),
            "label": _preview(nominated["quote"]), "sequence_ref": None, "molecule": None,
            "length": None, "term_refs": [], "context_refs": [], "anchor": anchor}
        ref = publish("reference", record)
        return ref, {"ref": ref, **location}

    def literal(value, kind, numbers):
        result = {"status": value["status"], "declared_status": value["declared_status"], "candidate_refs": [], "fragment_refs": []}
        for part, target in (("candidates", "candidate_refs"), ("fragments", "fragment_refs")):
            for w in value[part]:
                ref, location = witness(w, kind)
                result[target].append(ref)
                if numbers is not None:
                    numbers.append(location)
        return result

    def interpreted(value, kind):
        if value is None:
            return {"value": "unknown", "status": "not_selected", "witness_refs": []}
        return {"value": value["value"], "status": value["status"],
            "witness_refs": list(dict.fromkeys(witness(w, kind)[0] for w in value["witnesses"]))}

    def scalar(value, kind, numbers):
        return {"literal": literal(value["literal"], kind, numbers), **{k: value[k] for k in (
            "status", "relation", "approximate", "percent", "qualification_origin")}}

    roles = {}
    for role in ROLES:
        row, numbers = extraction["roles"][role], []
        measure, uncertainty = row["measurement"], row["uncertainty"]
        definitions = {}
        for name in ID_FIELDS:
            definition = row["definitions"][name] if row["definitions"] else None
            canonical_ref, canonical_location = witness(definition["canonical_witness"], name) if definition else (None, None)
            refs = list(dict.fromkeys(witness(w, name)[0] for w in definition["witnesses"])) if definition else []
            definitions[name] = {"status": definition["status"] if definition else "not_selected",
                "canonical_witness_ref": canonical_ref, "witness_refs": refs,
                "canonical_witness_location": {k: v for k, v in canonical_location.items() if k != "artifact_ref"} if canonical_location else None}
        physical = row["physical_fit"]
        physical_ref, physical_location = witness(physical["canonical_witness"], "physical_fit")
        physical_binding = {"status": physical["status"], "canonical_witness_ref": physical_ref,
            "canonical_witness_location": {k: v for k, v in physical_location.items() if k != "artifact_ref"} if physical_location else None,
            "witness_refs": list(dict.fromkeys(witness(w, "physical_fit")[0] for w in physical["witnesses"]))}
        expression = literal(measure["expression"], "measurement", numbers)
        unit = literal(measure["unit"], "unit", None)
        cell_ref = None
        if row["selection_status"] == "selected" and extraction["selection"]["roles"][role]["measurement"] is not None:
            selection = extraction["selection"]["roles"][role]["measurement"]
            located = measure["canonical_locator"]
            spec = image_specs[selection["image_id"]]
            source = located["original_source_ref"] if located else spec["source_ref"]
            cell_ref = publish("reference", {"reference_type": "literature_result", "source_ref": source,
                "accession": identity("binding_interaction_cell", {"selection": selection, "locator": located,
                    "source_cell_id": measure["source_cell_id"], "image": spec, "source": source_records[source]}),
                "label": "Selected source image cell", "sequence_ref": None, "molecule": None,
                "length": None, "term_refs": [], "context_refs": [], "anchor": None})
        unc = {"selection_status": uncertainty["selection_status"], "reported_spread_status": uncertainty["reported_spread_status"],
            "meanings": {name: interpreted(uncertainty["meanings"][name] if uncertainty["meanings"] else None, "uncertainty_" + name)
                for name in ("statistic", "basis", "repetition_basis")},
            "unavailable_reasons": list(uncertainty["unavailable_reasons"]), "interval": None}
        for name in ("confidence_level", "exact_count", "minimum_count"):
            unc[name] = scalar(uncertainty[name], name, numbers)
        interval = uncertainty["interval"]
        if interval is not None:
            unc["interval"] = {"lower": scalar(interval["lower"], "ci_lower", numbers), "upper": scalar(interval["upper"], "ci_upper", numbers),
                "unit_relationship": interpreted(interval["unit_relationship"], "ci_unit_relationship"),
                "unit": literal(interval["unit"], "ci_unit", None), "canonical_status": interval["canonical_status"],
                "canonical_unit": interval["canonical_unit"]}
        numeric = {"native": deepcopy(measure["native_measurement"]), "canonical": deepcopy(measure["canonical_measurement"]),
            "candidates": [{"witness_ref": expression["candidate_refs"][i], "native": deepcopy(c["native"]),
                "canonical": deepcopy(c["canonical"]), "canonical_unit": c["canonical_unit"]} for i, c in enumerate(measure["candidate_measurements"])],
            "uncertainty": deepcopy(uncertainty["canonical"]),
            "interval_native": [interval[k]["value"] for k in ("lower", "upper")] if interval else None,
            "scalar_native": {k: uncertainty[k]["value"] for k in ("confidence_level", "exact_count", "minimum_count")}}
        roles[role] = {"selection_status": row["selection_status"], "parameter_kind": interpreted(row["parameter_kind"], "parameter_kind"),
            "definitions": definitions, "physical_fit": physical_binding, "source_cell_ref": cell_ref,
            "parse_status": measure["parse_status"], "expression": expression, "unit": unit,
            "unavailable_reasons": list(row["unavailable_reasons"]), "uncertainty": unc,
            "numeric_locations": [{k: v for k, v in t.items() if k != "artifact_ref"} for t in {canonical(v): v for v in numbers}.values()], "numeric_values": numeric}
    return roles, {name: interpreted(extraction["relationships"][name], name) for name in RELATIONS}, interpreted(extraction["parameter_kind"], "common_parameter_kind")


class LiteratureBindingInteractionRepository(LiteratureRateRepository):
    provider = PROVIDER
    record_version = VERSION
    components = COMPONENTS
    operations_table = "literature_binding_interaction_operations"
    received_table = "literature_binding_interaction_received"
    binding_fields = ()

    def _parents(self, scope, direct):
        result, seen = list(direct), set(direct)
        for reference in result:
            for parent in self._native_provenance(scope, reference).get("parent_source_refs", ()):
                self._native_provenance(scope, parent)
                if parent not in seen:
                    seen.add(parent)
                    result.append(parent)
        return result

    def _image_lineage(self, scope, arguments):
        for image in arguments["images"]:
            if image["original_source_ref"] not in self._parents(scope, [image["source_ref"]]):
                _fail("image_original_ancestry_mismatch")

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if type(operation_key) is not str or not operation_key:
            raise ContractError("operation_key_required")
        request = {"run_id": self.run_id, "episode_id": context.episode_id, "operation_key": operation_key,
            "selected_tool": "literature.binding.interaction.populate", "scope": plain(context.scope), "assignment": plain(context.assignment),
            "requested_components": _selected(context.assignment), "arguments": plain(arguments)}
        signature = _signature(request)
        old = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, context.episode_id, operation_key)).fetchone()
        if old is not None:
            if old["signature"] != signature:
                raise ContractError("operation_key_reused_for_different_work")
            outcome = json.loads(old["outcome"])
            saved = self.read(outcome["result"]["sheet_ref"])
            for reference in saved["direct_input_source_refs"]:
                self._native_source(context, reference)
            return outcome
        validate_schema(request["arguments"], binding_interaction_arguments_schema())
        def selected_sources(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in ("source_ref", "original_source_ref") and isinstance(child, str):
                        yield child
                    else:
                        yield from selected_sources(child)
            elif isinstance(value, list):
                for child in value:
                    yield from selected_sources(child)
        # Authenticate every selected reference and page lineage before any bytes.
        for reference in dict.fromkeys(selected_sources(request["arguments"])):
            self._native_source(context, reference)
        self._image_lineage(context.scope, request["arguments"])
        def read_source(reference, representation):
            source = self._native_source(context, reference)
            artifact = source["artifact_ref"] if representation == "original" else source.get("text_ref")
            if artifact is None:
                raise ExperimentalContractError("source_representation_unavailable", "source")
            raw = self.store.get_artifact(artifact)
            if artifact != "artifact_" + hashlib.sha256(raw).hexdigest():
                _fail("source_artifact_identity_mismatch")
            return {"artifact_ref": artifact, "content": raw}
        extraction = read_binding_interaction_inputs(request["arguments"], read_source=read_source)
        self._image_lineage(context.scope, request["arguments"])
        calculation = populate_binding_interaction(extraction["calculation_inputs"]) if extraction["calculation_input_status"] == "ready" else None
        cells = native_cells(extraction, calculation)
        validate_saved_binding_interaction(request["arguments"], extraction, calculation, cells)
        direct = list(extraction["source_refs"])
        root = self._native_source(context, extraction["source_ref"])
        sources = self._parents(context.scope, direct)
        saved = {"version": VERSION, "input_source_ref": extraction["source_ref"], "input_artifact_ref": root["artifact_ref"],
            "direct_input_source_refs": direct, "input_source_refs": sources,
            "source_records": {ref: self._native_provenance(context.scope, ref) for ref in sources},
            "selection": request["arguments"], "extraction": extraction, "calculation": calculation, "cells": cells,
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
            saved["role_bindings"], saved["comparison_bindings"], saved["common_kind_binding"] = _bindings(extraction, publish, saved["source_records"])
            artifact = self.store.artifact(canonical(saved), "application/json")
            request_ref = self.store.artifact(canonical(request), "application/json")
            ref = publish("source", {"provider": PROVIDER, "accession": None, "uri": None, "artifact_ref": artifact,
                "text_ref": artifact, "request_ref": request_ref, "version": VERSION, "retrieved_at": None, "parent_source_refs": sources})
            outcome = {"status": "completed", "operation_ref": identity("operation", {"run_id": self.run_id,
                "episode_id": context.episode_id, "key": operation_key}), "record_refs": list(dict.fromkeys([ref, *records])),
                "changed_record_refs": created, "result": self._result(ref, saved), "feedback": None}
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    @staticmethod
    def _result(reference, saved):
        return {"sheet_ref": reference, "cells": saved["cells"], "evaluation_scope": EVALUATION_SCOPE,
            "source_kind": saved["extraction"]["source_kind"], "model_input_status": MODEL_INPUT_STATUS, "model_reader_capability": MODEL_CAPABILITY,
            "qualifications": {"model_reader_capability": MODEL_CAPABILITY, "model_input_status": MODEL_INPUT_STATUS,
                "calculation_input_status": saved["extraction"]["calculation_input_status"]}}

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
            raise ContractError("literature_binding_interaction_saved_mismatch") from error

    def _read(self, sheet_ref):
        source = self.store.get(sheet_ref)
        if (source.get("id") != sheet_ref or source.get("record_type") != "source" or source.get("provider") != PROVIDER
                or source.get("version") != VERSION or source.get("origin") != "tool" or not source.get("request_ref")):
            _fail("sheet_required")
        value = {k: v for k, v in source.items() if k not in ("id", "record_type", "origin")}
        if identity("source", {"origin": "tool", "record": value}) != sheet_ref:
            _fail("saved_source_identity_mismatch")
        request = self._artifact_json(source["request_ref"])
        if (set(request) != set(_REQUEST) or request["run_id"] != self.run_id
                or request["selected_tool"] != "literature.binding.interaction.populate"
                or request["requested_components"] != _selected(request["assignment"])):
            _fail("request_mismatch")
        operation = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request["episode_id"], request["operation_key"])).fetchone()
        if operation is None or operation["signature"] != _signature(request):
            _fail("operation_mismatch")
        outcome = json.loads(operation["outcome"])
        if (outcome.get("status") != "completed" or outcome.get("operation_ref") != identity("operation", {
                "run_id": self.run_id, "episode_id": request["episode_id"], "key": request["operation_key"]})
                or outcome.get("result", {}).get("sheet_ref") != sheet_ref):
            _fail("operation_mismatch")
        saved = self._artifact_json(source["artifact_ref"])
        _dependencies(saved["implementation_dependencies"])
        if (set(saved) != set(_PAYLOAD) or saved["version"] != VERSION or not _same(saved["selection"], request["arguments"])
                or saved["input_source_ref"] != request["arguments"]["source_ref"]
                or saved["direct_input_source_refs"] != saved["extraction"]["source_refs"]
                or saved["requested_components"] != request["requested_components"]
                or source.get("parent_source_refs") != saved["input_source_refs"] or source.get("text_ref") != source["artifact_ref"]
                or saved["input_source_refs"] != self._parents(request["scope"], saved["direct_input_source_refs"])):
            _fail("saved_mismatch")
        self._image_lineage(request["scope"], saved["selection"])
        if set(saved["source_records"]) != set(saved["input_source_refs"]):
            _fail("source_mismatch")
        for reference, original in saved["source_records"].items():
            actual = self._native_provenance(request["scope"], reference)
            if not _same(original, actual):
                _fail("source_mismatch")
            record = {k: v for k, v in original.items() if k not in ("id", "record_type", "origin")}
            if identity("source", {"origin": original["origin"], "record": record}) != reference:
                _fail("source_identity_mismatch")
        if saved["source_records"][saved["input_source_ref"]]["artifact_ref"] != saved["input_artifact_ref"]:
            _fail("source_mismatch")
        for row in saved["extraction"]["source_representations"]:
            meta = saved["source_records"][row["source_ref"]]
            artifact = meta["artifact_ref"] if row["representation"] == "original" else meta.get("text_ref")
            if row["error"] is None and (row["artifact_ref"] != artifact or row["artifact_ref"] != "artifact_" + row["sha256"]):
                _fail("source_mismatch")
        validate_saved_binding_interaction(saved["selection"], saved["extraction"], saved["calculation"], saved["cells"])
        if not _same(outcome["result"], self._result(sheet_ref, saved)):
            _fail("outcome_mismatch")
        records = []
        def expected(kind, value):
            reference = identity(kind, {"origin": "tool", "record": value})
            actual = self.store.get(reference)
            if (actual.get("id") != reference or actual.get("record_type") != kind or actual.get("origin") != "tool"
                    or not _same({k: actual.get(k) for k in value}, value)):
                _fail("binding_mismatch")
            records.append(reference)
            return reference
        roles, comparison, common = _bindings(saved["extraction"], expected, saved["source_records"])
        if not _same((roles, comparison, common), (saved["role_bindings"], saved["comparison_bindings"], saved["common_kind_binding"])):
            _fail("binding_mismatch")
        if outcome["record_refs"] != list(dict.fromkeys([sheet_ref, *records])) or any(r not in outcome["record_refs"] for r in outcome["changed_record_refs"]):
            _fail("operation_records_mismatch")
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = _selected({"requested_binding_interaction_components": self.components if components is None else components})
        result = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            saved = self.read(reference)
            for name in selected:
                roles = deepcopy(saved["role_bindings"])
                for raw, role in zip(RAW_COMPONENTS, ROLES):
                    values = roles[role].pop("numeric_values")
                    roles[role]["values"] = {"delivery_status": "requested" if name == raw else "not_requested",
                        **{k: deepcopy(v) if name == raw else None for k, v in values.items()}}
                result.append({"sheet_ref": reference, "evidence_source_ref": saved["input_source_ref"], "component": name,
                    **deepcopy(saved["cells"][name]), "formula_code": FORMULA_CODES[name], "evaluation_scope": EVALUATION_SCOPE,
                    "comparison_scope": saved["selection"]["comparison_scope"], "common_parameter_kind": deepcopy(saved["common_kind_binding"]),
                    "calculation_input_status": saved["extraction"]["calculation_input_status"], "model_input_status": MODEL_INPUT_STATUS,
                    "model_reader_capability": MODEL_CAPABILITY, "relationships": deepcopy(saved["comparison_bindings"]), "roles": roles})
        return result


def binding_interaction_cells_schema():
    """Closed C4 parent return: finite meanings, actual refs, selected numbers."""
    def enum(values, nullable=False):
        return {"type": ["string", "null"] if nullable else "string", "enum": [*values, None] if nullable else list(values)}
    def ref(namespace="reference", nullable=True):
        return {"type": ["string", "null"] if nullable else "string", "format": "reference", "x-reference-namespace": namespace}
    def array(value, unique=False):
        return {"type": "array", "items": value, **({"uniqueItems": True} if unique else {})}
    refs = array(ref(nullable=False), True)
    number, integer = {"type": ["number", "null"]}, {"type": ["integer", "null"]}
    literal_status = ("not_selected", "exact", "ambiguous", "unreadable", "conflicting", "source_unavailable")
    literal = obj({"status": enum(literal_status), "declared_status": enum(literal_status[1:-1], True), "candidate_refs": refs, "fragment_refs": refs})
    def interpreted(values):
        return obj({"value": enum(values), "status": enum(("interpreted", "source_unavailable", "not_selected")), "witness_refs": refs})
    region = {"type": ["array", "null"], "minItems": 4, "maxItems": 4, "items": {"type": "integer", "minimum": 0}}
    location = obj({"ref": ref(nullable=False), "source_ref": ref("source", False),
        "kind": enum(("utf8_span", "image_region", "unresolved")), "start": integer, "end": integer, "region": region})
    location_nullable = deepcopy(location)
    location_nullable["type"] = ["object", "null"]
    definition = obj({"status": enum(("known", "unknown", "conflicting", "source_unavailable", "not_selected")),
        "canonical_witness_ref": ref(), "witness_refs": refs, "canonical_witness_location": location_nullable})
    scalar = obj({"literal": literal, "status": enum(SCALAR_STATUSES), "relation": enum(("eq", "lt", "le", "gt", "ge"), True),
        "approximate": {"type": "boolean"}, "percent": {"type": "boolean"},
        "qualification_origin": enum(("selected_literal", "retained_text_context"), True)})
    measurement = obj({"value": number, "relation": enum(("eq", "lt", "le", "gt", "ge", "unreported")), "reported_spread": number})
    def nullable_object(schema):
        schema = deepcopy(schema)
        schema["type"] = ["object", "null"]
        return schema
    interval_values = {"type": ["array", "null"], "minItems": 2, "maxItems": 2, "items": number}
    canonical_uncertainty = nullable_object(obj({"statistic": enum(("sd", "sem", "confidence_interval", "unspecified", "unreported")),
        "basis": enum(("fit_to_averaged_curve", "between_independent_fitted_parameters", "unknown")),
        "exact_count": integer, "minimum_count": integer, "repetition_basis": enum(("biological_preparations", "technical_measurements", "assay_occasions", "unspecified")),
        "interval": interval_values, "confidence_level": number}))
    values = obj({"delivery_status": enum(("requested", "not_requested")), "native": nullable_object(measurement), "canonical": nullable_object(measurement),
        "candidates": {"type": ["array", "null"], "items": obj({"witness_ref": ref(nullable=False), "native": nullable_object(measurement),
            "canonical": nullable_object(measurement), "canonical_unit": enum(("nM",), True)})}, "uncertainty": canonical_uncertainty,
        "interval_native": interval_values, "scalar_native": nullable_object(obj({k: number for k in ("confidence_level", "exact_count", "minimum_count")}))})
    interval = nullable_object(obj({"lower": scalar, "upper": scalar, "unit_relationship": interpreted(("same_as_parameter", "explicit_unit", "unknown", "conflicting")),
        "unit": literal, "canonical_status": enum(("parsed", "partial", "unit_unavailable", "conflicting", "numerical_range")), "canonical_unit": enum(("nM",), True)}))
    metadata = obj({"selection_status": enum(("selected", "not_selected")), "parameter_kind": interpreted(KINDS),
        "definitions": obj({k: definition for k in ID_FIELDS}), "physical_fit": definition, "source_cell_ref": ref(),
        "parse_status": enum(MEASUREMENT_STATUSES), "expression": literal, "unit": literal,
        "unavailable_reasons": array(enum(ROLE_UNAVAILABLE_REASONS), True), "numeric_locations": array(location), "values": values,
        "uncertainty": obj({"selection_status": enum(("selected", "not_selected")), "reported_spread_status": enum(("reported", "native_reported_unit_unavailable", "not_in_selected_expression", "unresolved")),
            "meanings": obj({"statistic": interpreted(STATISTICS), "basis": interpreted(BASES), "repetition_basis": interpreted(REPETITIONS)}),
            "interval": interval, "confidence_level": scalar, "exact_count": scalar, "minimum_count": scalar,
            "unavailable_reasons": array(enum(UNCERTAINTY_REASONS), True)})})
    return {"type": "array", "x-source": "literature_binding_interaction_cells", "items": obj({
        "sheet_ref": ref("source", False), "evidence_source_ref": ref("source", False), "component": enum(COMPONENTS),
        "value": number, "threshold": number, "relation": enum(("eq", "lt", "le", "gt", "ge", "unreported", "none")),
        "unit": enum(("nM", "dimensionless"), True), "status": enum(("populated", "reported_limit", "conflicting", "unavailable")),
        "origin": enum(("synthetic", "visual_transcription", "derived")), "unavailable_reason": enum(UNAVAILABLE_REASONS, True),
        "calculation_unavailable_reason": enum(CALCULATION_REASONS, True), "bound_kind": enum(("printed_limit", "reported_limit_arithmetic"), True),
        "formula_code": enum(FORMULA_CODES.values()), "evaluation_scope": enum((EVALUATION_SCOPE,)),
        "comparison_scope": enum(("reported_protocols", "common_conditions")), "common_parameter_kind": interpreted(KINDS),
        "calculation_input_status": enum(CALCULATION_INPUT_STATUSES), "model_input_status": enum((MODEL_INPUT_STATUS,)),
        "model_reader_capability": enum((MODEL_CAPABILITY,)), "relationships": obj({k: interpreted(("supported", "unknown", "conflicting") if k != "common_conditions"
            else ("matched", "not_matched", "unknown", "conflicting")) for k in RELATIONS}), "roles": obj({k: metadata for k in ROLES})})}


__all__ = ["PROVIDER", "VERSION", "COMPONENTS", "FORMULA_CODES", "LiteratureBindingInteractionRepository",
    "binding_interaction_cells_schema", "binding_interaction_arguments_schema"]
