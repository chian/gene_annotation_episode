"""Selected immutable partner sheets and exact typed receipt projection.

Custody validates retained source records; it does not establish the truth of
supplied experimental interpretations. Saved reads never reopen source bytes or
repeat calculation. Ordinary episode accounting belongs to the caller.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import unicodedata

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_assay_inputs import SOURCE_KINDS
from .literature_partner_inputs import (
    COMPONENTS, LITERAL_FIELDS, partner_population_schema, read_partner_inputs,
)
from .literature_partner_native_inputs import (
    native_evidence_schema as _native_evidence_schema,
    partner_source_population_schema as _native_population_schema,
)
from .literature_rate_storage import LiteratureRateRepository


PROVIDER = "literature.experimental.partner"
FORMULA_CODES = dict(zip(COMPONENTS, (
    "native_partner_reference_v1", "native_partner_omitted_v1", "native_partner_addback_v1",
    "partner_reference_minus_omitted_v1", "partner_loss_over_reference_v1",
    "partner_addback_minus_omitted_v1", "partner_gain_over_loss_v1", "partner_gain_over_reference_v1")))
BINDINGS = {
    "subject_ref": ("subject", "reference"),
    "partner_ref": ("partner", "reference"),
    "experiment_ref": ("experiment", "reference"),
    "endpoint_ref": ("endpoint", "term"),
    "normalization_ref": ("normalization", "term"),
    "reference_condition_ref": ("reference_condition", "context"),
    "omitted_condition_ref": ("omitted_condition", "context"),
    "addback_condition_ref": ("addback_condition", "context"),
    "function_ref": ("function", "term"),
}
NATIVE_UNITS = ("pmol/min/mg", "nmol/min/mg", "umol/min/mg", "per_min", "per_s", "uM/min", "nM/min")
CHECK_REASONS = (
    "arm_unreported", "nonpartner_conditions_differ", "subject_unreported", "subject_mismatch",
    "partner_unreported", "partner_mismatch", "endpoint_unreported", "endpoint_mismatch",
    "normalization_unreported", "normalization_mismatch", "unit_unreported", "unit_mismatch",
    "partner_presence_not_established", "condition_factor_scope_unresolved", "conditions_incomplete",
    "measurement_identity_unreported", "role_measurement_not_distinct",
)
REASONS = (*CHECK_REASONS, "measurement_unreported", "censored_point_unreported",
    "nonpositive_reference_domain", "zero_or_straddling_loss_domain", "numerical_model_range")
_ROLES = ("reference", "omitted", "addback")
_FIXED_METADATA = {
    "evaluation_scope": "reference_experimental_partner_components",
    "target_correspondence": "not_evaluated", "partner_necessity": "not_inferred",
    "statistical_uncertainty": "not_evaluated", "measurement_corrections": "not_applied",
}
# Shape construction performs no source work. Saved reads/replay retain these
# closed shapes even when every native reader/helper function is disabled.
_NATIVE_ARGUMENT_SCHEMA = _native_population_schema()
_NATIVE_EVIDENCE_SCHEMA = _native_evidence_schema()
_NATIVE_EVIDENCE_V2_SCHEMA = _native_evidence_schema(defined_units=False)


def partner_source_population_schema():
    """Closed native-selector operands; independent of source work at replay."""
    return deepcopy(_NATIVE_ARGUMENT_SCHEMA)


def _arguments_schema(args):
    return (partner_source_population_schema() if isinstance(args, dict) and "input_mode" in args
            else partner_population_schema())


def _native_version(args):
    """Select the frozen representation from declared unit branches, not values."""
    for arm in args["arms"].values():
        if arm is None or arm["rate"] is None:
            continue
        for unit in (arm["rate"]["unit"], arm["rate"]["spread"]["unit"]):
            if isinstance(unit, dict) and unit.get("kind") == "source_defined_rate_unit":
                return "literature_partner_inputs_extraction_v3"
    return "literature_partner_inputs_extraction_v2"


def _spread_schema():
    return obj({"kind": {"type": "string", "enum": ["SD", "SEM", "CI", "unspecified", "unreported"]},
        "magnitude": {"type": ["number", "null"], "minimum": 0}})


def _arm_metadata_schema():
    arm = obj({"partner_state": {"type": "string", "enum": ["present", "absent", "unreported"]},
        "condition_coverage": {"type": "string", "enum": ["complete", "partial", "unreported"]},
        "spread": _spread_schema()})
    return obj({role: {**deepcopy(arm), "type": ["object", "null"]} for role in _ROLES})


def _check_schema(*, raw=False):
    return obj({"status": {"type": "string", "enum": ["matched", "different", "unresolved"]},
        ("differing_factors" if raw else "differing_factor_refs"): {"type": "array", "items": ({"type": "string", "minLength": 1} if raw else {"type": "string", "format": "reference", "x-reference-namespace": "term"}), "uniqueItems": True},
        "unavailable_reason": {"type": ["string", "null"], "enum": [None, *CHECK_REASONS]}})


def _checks_schema(*, raw=False):
    return obj({name: _check_schema(raw=raw) for name in ("reference_omitted", "addback_omitted")})


def _cell_schema():
    return obj({**{field: {"type": ["number", "null"]} for field in ("value", "lower", "upper")},
        "unit": {"type": ["string", "null"], "enum": [*NATIVE_UNITS, "dimensionless", None]},
        "origin": {"type": ["string", "null"], "enum": ["reported", "graph_derived", "synthetic", "derived", None]},
        "bound_kind": {"type": "string", "enum": ["point_only_not_uncertainty", "conditional_input_domain_not_CI"]},
        "status": {"type": "string", "enum": ["populated", "bounded", "unavailable"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [None, *REASONS]}})


def _input_schema():
    text = {"type": "string", "minLength": 1}
    nullable = {**text, "type": ["string", "null"]}
    factor = obj({"factor": text, "level": {"type": ["number", "string", "null"]}, "unit": text})
    arm = obj({**{name: deepcopy(nullable) for name in ("subject_ref", "partner_ref", "endpoint_ref", "normalization_ref")},
        "partner_state": {"enum": ["present", "absent", "unreported"]},
        "unit": {"enum": [*NATIVE_UNITS, "unreported"]},
        "conditions": obj({"coverage": {"enum": ["complete", "partial", "unreported"]},
            "factors": {"type": "array", "items": factor}}),
        "measurement": obj({"measurement_id": nullable,
            "status": {"enum": ["observed", "upper_bound", "unreported"]},
            "value": {"type": ["number", "null"], "minimum": 0},
            "origin": {"enum": ["reported", "graph_derived", "synthetic"]}, "spread": _spread_schema()})})
    return obj({"version": {"const": "literature_partner_inputs_v1"},
        "arms": obj({role: {**deepcopy(arm), "type": ["object", "null"]} for role in _ROLES})})


def _metadata(extraction, factor_bindings):
    arms = extraction["recipe"]["inputs"]["arms"]
    return {**_FIXED_METADATA, "source_kind": extraction["arguments"]["source_kind"],
        "comparison_checks": {name: {"status": check["status"], "unavailable_reason": check["unavailable_reason"],
            "differing_factor_refs": [factor_bindings[factor] for factor in check["differing_factors"]]}
            for name, check in extraction["calculation"]["comparison_checks"].items()},
        "arm_metadata": {role: None if arm is None else {
            "partner_state": arm["partner_state"], "condition_coverage": arm["conditions"]["coverage"],
            "spread": deepcopy(arm["measurement"]["spread"])} for role, arm in arms.items()}}


def _direct_references(args):
    direct = list(dict.fromkeys([args["source_ref"], args["data_source_ref"],
        *(args["literals"][field]["source_ref"] for field in LITERAL_FIELDS if args["literals"][field] is not None),
        *(entry["source_ref"] for entry in args["interpretation_witnesses"])]))
    if args.get("input_mode") == "native_source_spans":
        def references(value):
            if isinstance(value, dict):
                if "source_ref" in value:
                    yield value["source_ref"]
                for child in value.values():
                    yield from references(child)
            elif isinstance(value, list):
                for child in value:
                    yield from references(child)
        direct.extend(sorted(set(references(args["arms"])) - set(direct)))
    return direct


def _saved_check(first, omitted):
    """Validate frozen experimental relationships without reading or arithmetic."""
    def result(status, reason, differences=()):
        return {"status": status, "differing_factors": list(differences), "unavailable_reason": reason}
    if first is None or omitted is None:
        return result("unresolved", "arm_unreported")
    left = {f["factor"]: f for f in first["conditions"]["factors"]}
    right = {f["factor"]: f for f in omitted["conditions"]["factors"]}
    differences = sorted(name for name in left.keys() & right.keys()
        if left[name]["unit"] != right[name]["unit"] or (
            left[name]["level"] is not None and right[name]["level"] is not None
            and left[name]["level"] != right[name]["level"]))
    if differences:
        return result("different", "nonpartner_conditions_differ", differences)
    for key, stem in (("subject_ref", "subject"), ("partner_ref", "partner"),
            ("endpoint_ref", "endpoint"), ("normalization_ref", "normalization")):
        if first[key] is None or omitted[key] is None:
            return result("unresolved", stem + "_unreported")
        if first[key] != omitted[key]:
            return result("different", stem + "_mismatch")
    if first["unit"] == "unreported" or omitted["unit"] == "unreported":
        return result("unresolved", "unit_unreported")
    if first["unit"] != omitted["unit"]:
        return result("different", "unit_mismatch")
    if first["partner_state"] != "present" or omitted["partner_state"] != "absent":
        return result("unresolved", "partner_presence_not_established")
    if left.keys() != right.keys():
        return result("unresolved", "condition_factor_scope_unresolved")
    if any(a["conditions"]["coverage"] != "complete" for a in (first, omitted)):
        return result("unresolved", "conditions_incomplete")
    keys = [a["measurement"]["measurement_id"] for a in (first, omitted)]
    if None in keys:
        return result("unresolved", "measurement_identity_unreported")
    if keys[0] == keys[1]:
        return result("unresolved", "role_measurement_not_distinct")
    return result("matched", None)


def _factor_record(data_source_ref, name):
    return {"namespace": "literature_partner_condition_factor",
        "accession": identity("partner_factor", {"data_source_ref": data_source_ref, "factor": name}),
        "label": name, "term_type": "other", "source_ref": data_source_ref, "anchor": None}


def _factor_names(extraction):
    return sorted({factor for check in extraction["calculation"]["comparison_checks"].values()
        for factor in check["differing_factors"]})


def _binding_record(literal, kind, entry):
    witness = entry["witness"]
    anchor = {name: witness[name] for name in ("source_ref", "artifact_ref", "start", "end", "quote")}
    common = {"source_ref": witness["source_ref"], "anchor": anchor}
    # Even two identical selected spans retain their separate scientific roles.
    accession = identity("partner_literal", {"field": literal, **anchor})
    if kind == "reference":
        return {**common, "reference_type": "assay", "accession": accession,
            "label": entry["value"], "sequence_ref": None, "molecule": None,
            "length": None, "term_refs": [], "context_refs": []}
    if kind == "term":
        return {**common, "namespace": "literature_partner_" + literal,
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


class LiteraturePartnerRepository(LiteratureRateRepository):
    provider = PROVIDER
    components = COMPONENTS
    record_version = "literature_partner_record_v1"
    operations_table = "literature_partner_operations"
    received_table = "literature_partner_received"
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
        validate_schema(args, _arguments_schema(args))
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

            extraction = read_partner_inputs(args, read_source=read_source)
            direct = _direct_references(args)
            if (len(extraction["sources"]) != len(direct)
                    or set(extraction["sources"]) != set(direct)):
                raise ContractError("literature_partner_direct_source_mismatch")
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
            factor_bindings = {name: publish("term", _factor_record(args["data_source_ref"], name))
                for name in _factor_names(extraction)}
            payload["factor_bindings"] = factor_bindings
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
                    *(reference for reference in bindings.values() if reference), *_condition_refs(extraction), *(factor_bindings[name] for name in sorted(factor_bindings))])),
                "changed_record_refs": created,
                "result": {"sheet_ref": sheet_ref, "cells": deepcopy(extraction["cells"]),
                    "assay_interpretation": deepcopy(extraction["literals"]), **_metadata(extraction, factor_bindings)},
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
            raise ContractError("literature_partner_sheet_source_mismatch") from error
        return saved

    def _validate_saved(self, sheet_ref, saved):
        def require(condition):
            if not condition:
                raise ContractError("literature_partner_sheet_source_mismatch")

        source = self.store.get(sheet_ref)
        # Payloads published by every supported partner version are canonical
        # JSON. Bind all frozen native evidence to that original artifact, even
        # when several internally repeated metadata fields are changed together.
        artifact = self.store.get(source["artifact_ref"])
        require(hashlib.sha256(canonical(saved).encode()).hexdigest() == artifact["sha256"])
        request = json.loads(self.store.get_artifact(source["request_ref"]))
        require(set(request) == {"run_id", "episode_id", "operation_key", "arguments", "scope"})
        args, extraction = request["arguments"], saved["extraction"]
        validate_schema(args, _arguments_schema(args))
        operation = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request["episode_id"], request["operation_key"])).fetchone()
        require(operation is not None and operation["signature"] == canonical({
            "arguments": args, "scope": request["scope"]}))
        require(set(saved) == {"version", "input_source_ref", "input_artifact_ref", "input_source_refs",
            "direct_input_source_refs", "data_source_ref", "extraction", "experimental_bindings", "factor_bindings", "sheet"})
        require(source["version"] == self.record_version and source["text_ref"] == source["artifact_ref"])
        native = args.get("input_mode") == "native_source_spans"
        require(extraction["version"] == (_native_version(args) if native
            else "literature_partner_inputs_extraction_v1") and extraction["arguments"] == args)
        require(set(extraction) == {"version", "arguments", "sources", "literals", "interpretations",
            "recipe", "calculation", "cells"} | ({"native_evidence"} if native else set()))
        recipe = extraction["recipe"]
        require(set(recipe) == {"version", "inputs"} and recipe["version"] == "literature_partner_selection_v1")
        validate_schema(recipe["inputs"], _input_schema())
        calculation = extraction["calculation"]
        require(set(calculation) == {"version", "inputs", "cells", "comparison_checks"})
        require(calculation["version"] == "literature_partner_components_v1" and calculation["inputs"] == recipe["inputs"])
        require(calculation["cells"] == extraction["cells"])
        if native:
            self._validate_native_saved(args, extraction["native_evidence"], recipe["inputs"],
                                        version=extraction["version"])
        validate_schema(calculation["comparison_checks"], _checks_schema(raw=True))
        self._validate_scientific_saved(recipe["inputs"], calculation, args)
        direct = _direct_references(args)
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

        factors = saved["factor_bindings"]
        require(isinstance(factors, dict) and sorted(factors) == _factor_names(extraction))
        for name in sorted(factors):
            record = _factor_record(args["data_source_ref"], name)
            reference = factors[name]
            require(reference == identity("term", {"origin": "tool", "record": record}))
            require(self.store.get(reference) == {"id": reference, "record_type": "term", "origin": "tool", **record})
        require(set(saved["sheet"]) == {"cells"} and saved["sheet"]["cells"] == extraction["cells"])
        require(set(extraction["cells"]) == set(COMPONENTS))
        outcome = json.loads(operation["outcome"])
        require(outcome["status"] == "completed" and outcome["feedback"] is None)
        require(isinstance(outcome["changed_record_refs"], list)
            and len(set(outcome["changed_record_refs"])) == len(outcome["changed_record_refs"])
            and set(outcome["changed_record_refs"]) <= set(outcome["record_refs"]))
        require(outcome["operation_ref"] == identity("operation", {"run_id": self.run_id,
            "episode_id": request["episode_id"], "key": request["operation_key"]}))
        require(outcome["record_refs"] == list(dict.fromkeys([sheet_ref, *saved["input_source_refs"],
            *(saved["experimental_bindings"][field] for field in BINDINGS
                if saved["experimental_bindings"][field]), *_condition_refs(extraction),
            *(factors[name] for name in sorted(factors))])))
        require(outcome["result"] == {"sheet_ref": sheet_ref, "cells": extraction["cells"],
            "assay_interpretation": extraction["literals"], **_metadata(extraction, factors)})

    def _validate_native_saved(self, args, evidence, inputs, *, version=None):
        """Check frozen native-selector relationships without parsing again.

        Numerical conversions were committed by the original selected reader.
        Replay verifies their ownership/representation and copies their saved
        canonical values. It neither reacquires source bytes nor evaluates a
        number, unit conversion, scientific interpretation or core formula.
        """
        def require(condition):
            if not condition:
                raise ContractError("literature_partner_sheet_source_mismatch")

        expected_version = _native_version(args)
        require(version is None or version == expected_version)
        validate_schema(evidence, _NATIVE_EVIDENCE_V2_SCHEMA if expected_version.endswith("_v2")
                        else _NATIVE_EVIDENCE_SCHEMA)

        def witness(selected, actual):
            if selected is None:
                require(actual is None)
                return
            source = self.store.get(selected["source_ref"])
            require(source["record_type"] == "source")
            artifact = source["artifact_ref"] if selected["representation"] == "original" else source["text_ref"]
            require(actual == {**selected, "artifact_ref": artifact})
            require(artifact is not None)
            metadata = self.store.get(artifact)
            require(0 <= selected["start"] < selected["end"] <= metadata["size"])

        def number(selected, actual, *, rate=False, condition=False):
            witness(selected["witness"], actual["selector"]["witness"])
            require(actual["selector"] == {**selected, "witness": actual["selector"]["witness"]})
            start, end = selected["number_start"], selected["number_end"]
            quote = selected["witness"]["quote"]
            require(0 <= start < end <= len(quote) and actual["raw_number"] == quote[start:end])
            require(condition or actual["value"] >= 0)
            if not rate:
                require(actual["relation"] == "point")

        def contained(parent, child):
            require(all(parent[field] == child[field] for field in
                ("source_ref", "artifact_ref", "representation")))
            require(parent["start"] <= child["start"] < child["end"] <= parent["end"])
            raw = parent["quote"].encode("utf-8")
            require(raw[child["start"] - parent["start"]:child["end"] - parent["start"]]
                    == child["quote"].encode("utf-8"))

        def source_text(value):
            # Match the producer's lexical normalization, not unit arithmetic.
            return " ".join(unicodedata.normalize("NFKC", value).split())

        def whole_entity(parent, child):
            contained(parent, child)
            raw = parent["quote"].encode("utf-8")
            before = raw[:child["start"] - parent["start"]].decode("utf-8")[-1:]
            after = raw[child["end"] - parent["start"]:].decode("utf-8")[:1]
            require(not before or not (before.isalnum() or before == "_"))
            require(not after or not (after.isalnum() or after == "_"))

        def rate_unit(selected, actual, endpoint):
            if selected.get("kind") != "source_defined_rate_unit":
                require("definition" not in actual)
                witness(selected, actual["witness"])
                require(actual["raw_unit"] == selected["quote"])
                allowed = {"pmol/min/mg": (1, 1000, 1000000), "per_min": (1, 60), "uM/min": (1, .001)}
                require(actual["multiplier"] in allowed[actual["canonical_unit"]])
                return
            require("definition" in actual and endpoint is not None)
            witness(selected["witness"], actual["witness"])
            require(actual["raw_unit"] == selected["witness"]["quote"])
            require("".join(actual["raw_unit"].split()) == "U/mg")
            require(actual["canonical_unit"] == "pmol/min/mg" and actual["multiplier"] > 0)
            chosen, found = selected["definition"], actual["definition"]
            for field in ("bridge", "clause", "amount_unit", "time_unit", "endpoint",
                          "endpoint_entity", "definition_entity"):
                witness(chosen[field], found[field])
            number(chosen["amount"], found["amount"])
            require(found["amount"]["value"] > 0 and found["endpoint"] == endpoint)
            contained(found["bridge"], found["clause"])
            selection = found["amount"]["selector"]
            amount_witness = selection["witness"]
            contained(found["bridge"], amount_witness)
            start, end = selection["number_start"], selection["number_end"]
            contained(found["clause"], {**amount_witness,
                "start": amount_witness["start"] + len(amount_witness["quote"][:start].encode("utf-8")),
                "end": amount_witness["start"] + len(amount_witness["quote"][:end].encode("utf-8")),
                "quote": amount_witness["quote"][start:end]})
            for field in ("amount_unit", "time_unit", "definition_entity"):
                contained(found["clause"], found[field])
            whole_entity(found["endpoint"], found["endpoint_entity"])
            whole_entity(found["clause"], found["definition_entity"])
            require(source_text(found["endpoint_entity"]["quote"])
                    == source_text(found["definition_entity"]["quote"]))
            require(source_text(found["amount_unit"]["quote"]).replace("µ", "u").replace("μ", "u")
                    in ("pmol", "nmol", "umol"))
            require(source_text(found["time_unit"]["quote"]) in ("min", "minute", "s", "second"))

        for role in _ROLES:
            selected, actual, core = args["arms"][role], evidence[role], inputs["arms"][role]
            if selected is None:
                require(actual is None and core is None)
                continue
            require(actual is not None and core is not None)
            require(actual["origin"] == selected["origin"] == core["measurement"]["origin"])
            require(actual["partner_state"] == selected["partner_state"] == core["partner_state"])
            for field in ("subject", "partner", "endpoint", "normalization", "measurement_identity"):
                witness(selected[field], actual[field])
                name = "measurement_id" if field == "measurement_identity" else field + "_ref"
                target = core["measurement"] if field == "measurement_identity" else core
                namespace = "partner_native_measurement" if field == "measurement_identity" else "partner_native_" + field
                require(target[name] == (identity(namespace, actual[field]) if actual[field] else None))
            conditions = actual["conditions"]
            require(conditions["coverage"] == selected["conditions"]["coverage"] == core["conditions"]["coverage"])
            require(len(conditions["factors"]) == len(selected["conditions"]["factors"]) == len(core["conditions"]["factors"]))
            for chosen, found, normalized in zip(selected["conditions"]["factors"], conditions["factors"], core["conditions"]["factors"]):
                require(chosen["factor"] == found["factor"] == normalized["factor"])
                level, parsed = chosen["level"], found["level"]
                if level is None:
                    require(parsed is None and normalized["level"] is None and normalized["unit"] == "unreported")
                elif level["kind"] == "literal":
                    require(parsed["kind"] == "literal")
                    witness(level["witness"], parsed["witness"])
                    require(normalized["level"] == parsed["witness"]["quote"] and normalized["unit"] == "source_literal")
                else:
                    require(parsed["kind"] == "number")
                    number(level["selector"], parsed["selector"], condition=True)
                    witness(level["unit_witness"], parsed["unit_witness"])
                    require(normalized["level"] == parsed["selector"]["value"])
                    require(normalized["unit"] == (parsed["unit_witness"]["quote"] if parsed["unit_witness"] else "dimensionless"))
            rate, parsed = selected["rate"], actual["rate"]
            if rate is None:
                require(parsed is None and core["unit"] == "unreported")
                require(core["measurement"]["status"] == "unreported" and core["measurement"]["value"] is None)
                require(core["measurement"]["spread"] == {"kind": "unreported", "magnitude": None})
                continue
            require(parsed is not None)
            number(rate["value"], parsed["value"], rate=True)
            rate_unit(rate["unit"], parsed["unit"], actual["endpoint"])
            require(core["unit"] == parsed["unit"]["canonical_unit"])
            require(core["measurement"]["value"] == parsed["canonical_value"])
            require(core["measurement"]["status"] == ("observed" if parsed["value"]["relation"] == "point" else "upper_bound"))
            spread, found = rate["spread"], parsed["spread"]
            require(spread["kind"] == found["kind"] == core["measurement"]["spread"]["kind"])
            if spread["unit"] is None:
                require(found["unit"] is None)
            else:
                rate_unit(spread["unit"], found["unit"], actual["endpoint"])
                require(found["unit"]["canonical_unit"] == parsed["unit"]["canonical_unit"])
            require(len(spread["witnesses"]) == len(found["witnesses"]))
            for chosen, actual_basis in zip(spread["witnesses"], found["witnesses"]):
                witness(chosen, actual_basis)
            require(spread["kind"] not in ("SD", "SEM", "CI") or bool(spread["witnesses"]))
            if spread["magnitude"] is None:
                require(spread["kind"] == "unreported" and spread["unit"] is None
                    and found["magnitude"] is None and parsed["canonical_spread"] is None)
            else:
                require(spread["kind"] != "unreported")
                number(spread["magnitude"], found["magnitude"])
            require(core["measurement"]["spread"]["magnitude"] == parsed["canonical_spread"])

    def _validate_scientific_saved(self, inputs, calculation, args):
        """Validate frozen structures/meanings, never rerun a numerical formula."""
        def require(condition):
            if not condition:
                raise ContractError("literature_partner_sheet_source_mismatch")

        arms = inputs["arms"]
        seen = {}
        for role, arm in arms.items():
            if arm is None:
                continue
            for field in ("subject_ref", "partner_ref", "endpoint_ref", "normalization_ref"):
                require(arm[field] is None or bool(arm[field].strip()))
            factors = arm["conditions"]["factors"]
            names = [factor["factor"] for factor in factors]
            require(len(names) == len(set(names)))
            for factor in factors:
                require(bool(factor["factor"].strip()) and bool(factor["unit"].strip()))
                require(not isinstance(factor["level"], str) or bool(factor["level"].strip()))
            coverage = arm["conditions"]["coverage"]
            require(coverage != "unreported" or not factors)
            require(coverage != "complete" or bool(factors) and all(f["level"] is not None for f in factors))
            measurement = arm["measurement"]
            require(measurement["measurement_id"] is None or bool(measurement["measurement_id"].strip()))
            require((measurement["status"] == "unreported") == (measurement["value"] is None))
            require(arm["unit"] != "unreported" or measurement["status"] == "unreported")
            spread = measurement["spread"]
            require((spread["kind"] == "unreported") == (spread["magnitude"] is None))
            if args["source_kind"] == "synthetic_fixture":
                require(measurement["origin"] == "synthetic")
            key = measurement["measurement_id"]
            if key is not None:
                signature = (measurement["value"], measurement["status"], arm["unit"])
                require(key not in seen or seen[key] == signature)
                seen[key] = signature
        require(bool(args["interpretation_witnesses"]) or not any(arm is not None
            and arm["conditions"]["coverage"] == "complete" for arm in arms.values()))
        pairs = {"reference_omitted": (arms["reference"], arms["omitted"]),
                 "addback_omitted": (arms["addback"], arms["omitted"])}
        for name, check in calculation["comparison_checks"].items():
            require(check == _saved_check(*pairs[name]))
        cells = calculation["cells"]
        require(set(cells) == set(COMPONENTS))
        for name, cell in cells.items():
            validate_schema(cell, _cell_schema())
            if cell["status"] == "unavailable":
                require(cell["unavailable_reason"] is not None
                    and all(cell[field] is None for field in ("value", "lower", "upper")))
            elif cell["status"] == "bounded":
                require(cell["value"] is None and cell["lower"] is not None and cell["upper"] is not None
                    and cell["lower"] <= cell["upper"] and cell["unavailable_reason"] == "censored_point_unreported"
                    and cell["bound_kind"] == "conditional_input_domain_not_CI")
            else:
                require(cell["unavailable_reason"] is None and all(cell[field] is not None
                    for field in ("value", "lower", "upper")) and cell["lower"] <= cell["value"] <= cell["upper"])
            if name in COMPONENTS[3:]:
                require(cell["origin"] == "derived")
                if name in ("partner_loss_fraction", "addback_fraction", "restored_reference_fraction"):
                    require(cell["unit"] == "dimensionless")
        w, o, a = (arms[role] for role in _ROLES)
        checks = calculation["comparison_checks"]
        loss_reason = checks["reference_omitted"]["unavailable_reason"]
        gain_reason = checks["addback_omitted"]["unavailable_reason"]
        if w is not None and a is not None:
            wk, ak = (arm["measurement"]["measurement_id"] for arm in (w, a))
            if wk is not None and wk == ak:
                gain_reason = "role_measurement_not_distinct"
        triple_reason = loss_reason or gain_reason
        def unit(arm):
            return None if arm is None or arm["unit"] == "unreported" else arm["unit"]
        for name, roles, prerequisite, expected_unit, allowed in (
            ("partner_loss", (w, o), loss_reason, unit(w) if unit(w) == unit(o) else None, ("numerical_model_range",)),
            ("partner_loss_fraction", (w, o), loss_reason, "dimensionless", ("numerical_model_range", "nonpositive_reference_domain")),
            ("addback_gain", (a, o), gain_reason, unit(a) if unit(a) == unit(o) else None, ("numerical_model_range",)),
            ("addback_fraction", (w, o, a), triple_reason, "dimensionless", ("numerical_model_range", "zero_or_straddling_loss_domain")),
            ("restored_reference_fraction", (w, o, a), triple_reason, "dimensionless", ("numerical_model_range", "nonpositive_reference_domain")),
        ):
            cell = cells[name]
            require(cell["unit"] == expected_unit and cell["origin"] == "derived")
            missing = prerequisite or ("measurement_unreported" if any(arm is None or
                arm["measurement"]["status"] == "unreported" for arm in roles) else None)
            if missing:
                require(cell["status"] == "unavailable" and cell["unavailable_reason"] == missing
                    and cell["bound_kind"] == "point_only_not_uncertainty")
            else:
                require(cell["status"] != "unavailable" or cell["unavailable_reason"] in allowed)
                expected_kind = ("conditional_input_domain_not_CI" if any(
                    arm["measurement"]["status"] == "upper_bound" for arm in roles)
                    and cell["unavailable_reason"] not in ("nonpositive_reference_domain", "zero_or_straddling_loss_domain")
                    else "point_only_not_uncertainty")
                require(cell["bound_kind"] == expected_kind)
        for role, name in zip(_ROLES, COMPONENTS[:3]):
            arm, cell = arms[role], cells[name]
            if arm is None:
                require(cell == {"value": None, "lower": None, "upper": None, "unit": None,
                    "origin": None, "bound_kind": "point_only_not_uncertainty", "status": "unavailable",
                    "unavailable_reason": "arm_unreported"})
                continue
            measurement = arm["measurement"]
            require(cell["origin"] == measurement["origin"]
                and cell["unit"] == (None if arm["unit"] == "unreported" else arm["unit"]))
            if measurement["status"] == "observed":
                require(cell["status"] == "populated" and cell["value"] == cell["lower"] == cell["upper"] == measurement["value"]
                    and cell["bound_kind"] == "point_only_not_uncertainty")
            elif measurement["status"] == "upper_bound":
                require(cell["status"] == "bounded" and cell["lower"] == 0 and cell["upper"] == measurement["value"])
            else:
                require(cell["status"] == "unavailable" and cell["unavailable_reason"] == "measurement_unreported"
                    and cell["bound_kind"] == "point_only_not_uncertainty")

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        components = self.components if components is None else components
        if (not isinstance(components, (list, tuple))
                or any(not isinstance(name, str) or name not in self.components for name in components)
                or len(set(components)) != len(components)):
            raise ContractError("literature_partner_component_selection_invalid")
        rows = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            saved = self.read(reference)
            for name in components:
                rows.append({"sheet_ref": reference, "evidence_source_ref": saved["input_source_ref"],
                    "data_source_ref": saved["data_source_ref"], **deepcopy(saved["experimental_bindings"]),
                    "component": name, **deepcopy(saved["sheet"]["cells"][name]),
                    "formula_code": FORMULA_CODES[name], **_metadata(saved["extraction"], saved["factor_bindings"])})
        validate_schema(rows, partner_cells_schema())
        return rows

    def validate_returned_values(self, cells, *, permitted_record_refs):
        validate_schema(cells, partner_cells_schema())
        super().validate_returned_values(cells, permitted_record_refs=permitted_record_refs)


def partner_cells_schema():
    """Closed numerical and source-meaning rows, without raw numerical recipes."""
    source = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    properties = {
        **{field: dict(source) for field in ("sheet_ref", "evidence_source_ref", "data_source_ref")},
        **{field: {"type": ["string", "null"], "format": "reference", "x-reference-namespace": kind}
            for field, (_, kind) in BINDINGS.items()},
        "component": {"type": "string", "enum": list(COMPONENTS)},
        **deepcopy(_cell_schema()["properties"]),
        "formula_code": {"type": "string", "enum": list(FORMULA_CODES.values())},
        "source_kind": {"type": "string", "enum": list(SOURCE_KINDS)},
        "comparison_checks": _checks_schema(), "arm_metadata": _arm_metadata_schema(),
        **{field: {"type": "string", "enum": [value]} for field, value in _FIXED_METADATA.items()}}
    return {"type": "array", "items": obj(properties), "x-source": "literature_partner_cells"}


__all__ = ["LiteraturePartnerRepository", "COMPONENTS", "PROVIDER", "BINDINGS", "FORMULA_CODES",
    "partner_population_schema", "partner_source_population_schema", "partner_cells_schema"]
