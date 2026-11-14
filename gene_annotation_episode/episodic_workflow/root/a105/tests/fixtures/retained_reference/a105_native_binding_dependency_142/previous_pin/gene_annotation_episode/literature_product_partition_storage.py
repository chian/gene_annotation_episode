"""Selected A105 partition custody and exact typed subsets, with no credit policy."""
from copy import deepcopy
import hashlib
import json
import re

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_rate_storage import LiteratureRateRepository
from .literature_product_partition_inputs import (MEANINGS, ROLES, BASES, STAGES, RELATIONS,
    RELATIONSHIPS, QUALIFICATIONS, EVIDENCE_ROLES, product_partition_arguments_schema,
    read_product_partition_inputs, validate_product_partition_extraction)
from .literature_product_partition_calculations import (COMPONENTS, REASONS, CONDITIONS,
    component_roles, populate_product_partition_components)

PROVIDER = "literature.a105.product_partition_population"
VERSION = "literature_product_partition_population_record_v1"
NAMESPACE = "literature_product_partition_cells"


def _number_spans(extraction):
    result = {}
    for role, quantity in extraction["selection"]["quantities"].items():
        if quantity and quantity["measurement"]:
            number = quantity["measurement"]["number"]
            selector, witness = number["selector"], number["selector"]["witness"]
            result[role] = (witness["source_ref"], witness["artifact_ref"], witness["representation"],
                witness["start"] + len(witness["quote"][:selector["number_start"]].encode()),
                witness["start"] + len(witness["quote"][:selector["number_end"]].encode()))
    return result


def _bindings(extraction, component, publish):
    """Withhold exact witnesses overlapping unrequested numerical operands.

    Never rewrite a source quote. Derived-only requests carry no native numbers.
    The child can select a smaller meaningful literal in a later own action.
    """
    allowed = component_roles(component) if component in ("partition_a_fraction", "partition_b_fraction") else ()
    forbidden = [span for role, span in _number_spans(extraction).items() if role not in allowed]
    def reference(witness, name, *, global_evidence=False):
        if witness is None:
            return None
        if any((witness["source_ref"], witness["artifact_ref"], witness["representation"]) == span[:3]
               and witness["start"] < span[4] and span[3] < witness["end"] for span in forbidden):
            return None
        anchor = {key: witness[key] for key in ("source_ref", "artifact_ref", "start", "end", "quote")}
        return publish("reference", {"reference_type": "literature_result", "source_ref": witness["source_ref"],
            "accession": identity("partition_" + name, witness), "label": witness["quote"],
            "sequence_ref": None, "molecule": None, "length": None, "term_refs": [], "context_refs": [], "anchor": anchor})
    quantities = []
    for role in component_roles(component):
        quantity = extraction["selection"]["quantities"][role]
        refs = {name + "_ref": reference(quantity["meanings"][name], name) if quantity else None for name in MEANINGS}
        quantities.append({"role": role, **refs,
            "meaning_status": {name: "not_selected" if quantity is None or quantity["meanings"][name] is None else
                "selected" if refs[name + "_ref"] is not None else "withheld_unrequested_numbers" for name in MEANINGS},
            "basis": quantity["basis"]["value"] if quantity else "unknown",
            "stage": quantity["stage"]["value"] if quantity else "unknown",
            "qualification": quantity["qualification"]["value"] if quantity else "unknown"})
    evidence = []
    for row in extraction["selection"]["evidence"]:
        ref = reference(row["witness"], row["role"], global_evidence=True)
        evidence.append({"role": row["role"], "witness_ref": ref,
                         "availability": "recorded" if ref else "withheld_unrequested_numbers"})
    experiment = reference(extraction["selection"]["experiment"], "experiment")
    return {"experiment_ref": experiment,
        "experiment_status": "not_selected" if extraction["selection"]["experiment"] is None else "selected" if experiment else "withheld_unrequested_numbers",
        "quantities": quantities, "evidence": evidence}


class LiteratureProductPartitionRepository(LiteratureRateRepository):
    provider = PROVIDER
    record_version = VERSION
    components = COMPONENTS
    operations_table = "literature_product_partition_operations"
    received_table = "literature_product_partition_received"
    binding_fields = ()

    def __init__(self, store, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("explicit_literature_run_required")
        self.store, self.run_id = store, run_id

    def _installed(self):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (self.operations_table,)).fetchone() is not None

    def _install(self):
        LiteratureRateRepository.__init__(self, self.store, self.run_id)

    def receive_cells(self, context, cells, operation_key):
        with self.store.transaction():
            self._install()
            return super().receive_cells(context, cells, operation_key)

    def received_cells(self, context):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        return super().received_cells(context) if self._installed() else []

    def validate_empty_return_family(self, context):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")

    @staticmethod
    def cell_record_refs(cells):
        """Only scientific dependencies in these exact selected rows."""
        return binding_references(cells)

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        validate_schema(args, product_partition_arguments_schema())
        requested = list(context.assignment.get("requested_product_partition_components", ()))
        self.project_cells([], permitted_record_refs=(), components=requested)
        signature = canonical({"arguments": args, "scope": plain(context.scope), "requested_components": requested})
        old = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, context.episode_id, operation_key)).fetchone() if self._installed() else None
        if old is not None:
            if signature != old["signature"]:
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
        extraction = read_product_partition_inputs(args, read_source=read_source)
        sheet = populate_product_partition_components(extraction)
        parents = list(extraction["source_refs"])
        for ref in parents:
            for ancestor in self._native_provenance(context.scope, ref).get("parent_source_refs", ()):
                self._native_provenance(context.scope, ancestor)
                if ancestor not in parents:
                    parents.append(ancestor)
        root = self._native_source(context, args["source_ref"])
        with self.store.transaction():
            self._install()
            created = []
            def publish(kind, record):
                candidate = identity(kind, {"origin": "tool", "record": record})
                existed = self.store.db.execute("SELECT 1 FROM records WHERE id=?", (candidate,)).fetchone()
                result = self.store.put(kind, record, origin="tool", scope=plain(context.scope))
                if existed is None: created.append(result["id"])
                return result["id"]
            bindings = {name: _bindings(extraction, name, publish) for name in COMPONENTS}
            payload = {"version": VERSION, "selection": args, "extraction": extraction, "sheet": sheet,
                "input_source_ref": args["source_ref"], "input_artifact_ref": root["artifact_ref"],
                "direct_input_source_refs": extraction["source_refs"], "input_source_refs": parents, "bindings": bindings}
            artifact = self.store.artifact(canonical(payload), "application/json")
            request = self.store.artifact(canonical({"run_id": self.run_id, "episode_id": context.episode_id,
                "operation_key": operation_key, "arguments": args, "scope": plain(context.scope),
                "requested_components": requested}), "application/json")
            ref = publish("source", {"provider": PROVIDER, "accession": None, "uri": None,
                "artifact_ref": artifact, "text_ref": artifact, "request_ref": request, "version": VERSION,
                "retrieved_at": None, "parent_source_refs": parents})
            rows = self._project_saved(payload, ref, requested)
            references = list(dict.fromkeys([ref, *self.cell_record_refs(rows)]))
            outcome = {"status": "completed", "operation_ref": identity("operation", {"run_id": self.run_id,
                "episode_id": context.episode_id, "key": operation_key}), "record_refs": references,
                "changed_record_refs": [r for r in created if r in references],
                "result": {"view": "reported_product_partition_components", "sheet_ref": ref, "cells": rows}, "feedback": None}
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def read(self, sheet_ref):
        if not self._installed():
            raise ContractError("literature_sheet_not_selected_output")
        saved = super().read(sheet_ref)
        source = self.store.get(sheet_ref)
        request = json.loads(self.store.get_artifact(source["request_ref"]))
        operation = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request["episode_id"], request["operation_key"])).fetchone()
        raw = self.store.get_artifact(source["artifact_ref"])
        if ("artifact_" + hashlib.sha256(raw).hexdigest() != source["artifact_ref"] or source["version"] != VERSION
                or "artifact_" + hashlib.sha256(self.store.get_artifact(source["request_ref"])).hexdigest() != source["request_ref"]
                or saved["selection"] != request["arguments"]
                or operation["signature"] != canonical({"arguments": request["arguments"], "scope": request["scope"], "requested_components": request["requested_components"]})
                or saved["direct_input_source_refs"] != saved["extraction"]["source_refs"]
                or saved["input_artifact_ref"] != self.store.get(saved["input_source_ref"])["artifact_ref"]):
            raise ContractError("literature_product_partition_saved_mismatch")
        validate_product_partition_extraction(saved["extraction"], saved["selection"])
        def custody(value):
            if isinstance(value, dict):
                if set(value) == {"source_ref", "artifact_ref", "representation", "start", "end", "quote"}:
                    row = self.store.get(value["source_ref"])
                    artifact = row["artifact_ref"] if value["representation"] == "original" else row.get("text_ref")
                    if artifact != value["artifact_ref"] or value["source_ref"] not in saved["direct_input_source_refs"]:
                        raise ContractError("literature_product_partition_source_mismatch")
                else:
                    for child in value.values(): custody(child)
            elif isinstance(value, list):
                for child in value: custody(child)
        custody(saved["extraction"])
        # This validates original arithmetic only. No source bytes are read and
        # no scientific meaning, lexical qualification or observation is changed.
        if saved["sheet"] != populate_product_partition_components(saved["extraction"]):
            raise ContractError("literature_product_partition_saved_arithmetic_mismatch")
        def expected(kind, record):
            ref = identity(kind, {"origin": "tool", "record": record})
            actual = self.store.get(ref)
            if actual.get("origin") != "tool" or actual.get("record_type") != kind or any(actual.get(k) != v for k, v in record.items()):
                raise ContractError("literature_product_partition_binding_mismatch")
            return ref
        if saved["bindings"] != {name: _bindings(saved["extraction"], name, expected) for name in COMPONENTS}:
            raise ContractError("literature_product_partition_binding_mismatch")
        if json.loads(operation["outcome"])["result"]["cells"] != self._project_saved(saved, sheet_ref, request["requested_components"]):
            raise ContractError("literature_product_partition_saved_return_mismatch")
        return saved

    @staticmethod
    def _project_saved(saved, ref, selected):
        result = []
        for name in selected:
            cell = {k: deepcopy(v) for k, v in saved["sheet"]["cells"][name].items() if k != "formula"}
            result.append({"sheet_ref": ref, "evidence_source_ref": saved["input_source_ref"],
                "component": name, **cell, **deepcopy(saved["bindings"][name]),
                "relationships": {field: saved["extraction"]["selection"]["relationships"][field]["value"] for field in RELATIONS},
                "evaluation_scope": "reported_selected_product_partition", "uncertainty_calculation": "not_implemented"})
        validate_schema(result, product_partition_cells_schema())
        return result

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        # Parent-owned selections default to empty. A caller can explicitly
        # request every component using COMPONENTS.
        selected = () if components is None else components
        if (not isinstance(selected, (tuple, list)) or any(name not in COMPONENTS for name in selected)
                or len(selected) != len(set(selected))):
            raise ContractError("literature_product_partition_component_selection_invalid")
        result = []
        for ref in dict.fromkeys(sheet_refs):
            if ref not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            saved = self.read(ref)
            result.extend(self._project_saved(saved, ref, selected))
        validate_schema(result, product_partition_cells_schema())
        return result

    def validate_returned_values(self, cells, *, permitted_record_refs):
        validate_schema(cells, product_partition_cells_schema())
        return super().validate_returned_values(cells, permitted_record_refs=permitted_record_refs)


def binding_references(value):
    result = []
    def visit(node):
        if isinstance(node, dict):
            for key, child in node.items():
                if key.endswith("_ref") and child is not None: result.append(child)
                else: visit(child)
        elif isinstance(node, list):
            for child in node: visit(child)
    visit(value)
    return list(dict.fromkeys(result))


def product_partition_cells_schema():
    def reference(namespace, nullable=True):
        return {"type": ["string", "null"] if nullable else "string", "format": "reference", "x-reference-namespace": namespace}
    def enum(values): return {"type": "string", "enum": list(values)}
    quantity = obj({"role": enum(ROLES), **{name + "_ref": reference("reference") for name in MEANINGS},
                    "meaning_status": obj({name: enum(("selected", "not_selected", "withheld_unrequested_numbers")) for name in MEANINGS}),
                    "basis": enum(BASES), "stage": enum(STAGES), "qualification": enum(QUALIFICATIONS)})
    return {"type": "array", "x-source": NAMESPACE, "items": obj({
        "sheet_ref": reference("source", False), "evidence_source_ref": reference("source", False),
        "experiment_ref": reference("reference"), "component": enum(COMPONENTS),
        "experiment_status": enum(("selected", "not_selected", "withheld_unrequested_numbers")),
        "value": {"type": ["number", "null"]}, "unit": enum(("fraction", "dimensionless")),
        "status": enum(("populated", "unavailable")), "origin": enum(("reported", "synthetic", "derived")),
        "unavailable_reason": {"type": ["string", "null"], "enum": [*REASONS, None]},
        "conditional_on": {"type": "array", "uniqueItems": True, "items": enum(CONDITIONS)},
        "approximate": {"type": "boolean"}, "threshold": {"type": ["number", "null"]},
        "bound": enum(("none", "lt", "le", "gt", "ge")), "outside_reported_fraction_range": {"type": "boolean"},
        "quantities": {"type": "array", "maxItems": 2, "items": quantity},
        "relationships": obj({name: enum(RELATIONSHIPS) for name in RELATIONS}),
        "evidence": {"type": "array", "items": obj({"role": enum(EVIDENCE_ROLES),
            "witness_ref": reference("reference"), "availability": enum(("recorded", "withheld_unrequested_numbers"))})},
        "evaluation_scope": {"type": "string", "const": "reported_selected_product_partition"},
        "uncertainty_calculation": {"type": "string", "const": "not_implemented"}})}
