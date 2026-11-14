"""Original requested MSA/MetaCATS facts across existing episode boundaries.

Authenticated saved sheets and components prove identities and selected values.
No parser, scientific calculator, resource operation or model runs on this path.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re

from .bvbrc_alignment_bundle_contracts import (
    FACT_SCHEMAS, REFERENCE_KINDS, encode_reference, validate_parameters,
    validate_requested_form,
)
from .bvbrc_appservice_contracts import _finite_json, validate_contract
from .bvbrc_appservice_custody import _references
from .bvbrc_appservice_publication import DATA_PROVIDER, RESULT_VERSION
from .bvbrc_appservice_saved_results import read_latest_adapter_result
from .communication import plain, validate_form
from .episode_return_records import EpisodeReturnRecords, _same
from .execution_contracts import canonical, digest
from .form_reference_validation import _binding_key, form_validation_value


_SELECTION_FAMILIES = {
    "measurement": "measurements", "native_measurement": "measurements",
    "msa_sites": "msa_sites", "reference_differences": "reference_differences",
    "group_counts": "group_counts", "statistical_tests": "statistical_tests",
    "function_composition": "function_composition", "tree_branches": "tree_branches",
    "multiplicity": "multiplicity", "missing_requirements": "requirements",
    "qualifications": "qualifications", "xmfa_coordinates": "xmfa_coordinates",
    "xmfa_source_positions": "xmfa_source_positions",
    "xmfa_alignment_measurements": "xmfa_measurements",
    "xmfa_coverage": "xmfa_coverage",
}
FACT_SOURCES = tuple(dict.fromkeys("bvbrc_alignment_" + family
    for family in _SELECTION_FAMILIES.values()))
IDENTIFIER_NAMESPACES = tuple("bvbrc_alignment_" + kind for kind in REFERENCE_KINDS)
_PREFIX = "bvbrc_alignment_return_"
_ADAPTERS = {"bvbrc_msa": "msa", "bvbrc_metacats": "metacats"}
_SOURCE_ID = re.compile(r"source_[a-f0-9]{24,64}\Z")
_SYMBOL_FIELDS = frozenset({"symbol", "member_character", "reference_character",
    "strict_majority_consensus", "aligned_symbol", "forward_symbol"})
_MEANINGS = {
    "measurements": "Original requested numerical cells, with native or calculated identity, units, populations and missing meanings.",
    "msa_sites": "Original selected alignment positions, terminal-gap exclusions, entropy, native score comparison and consensus characters.",
    "reference_differences": "Original selected residue differences and proven aligned, ungapped and original-coordinate correspondence.",
    "group_counts": "Original selected group and symbol counts, retaining biological or native-reproduction basis and actual populations.",
    "statistical_tests": "Original selected chi-square tests, degrees of freedom, probabilities and log tails; native and biological conventions remain distinct.",
    "function_composition": "Original requested function-assignment counts and fractions of the declared member population; not annotation probabilities.",
    "tree_branches": "Original selected tree edges, measured lengths, units and support method/scale qualifications.",
    "multiplicity": "Original selected tested-family corrections, input probabilities, declared denominator and method; no new family expansion.",
    "requirements": "Original explicitly requested unresolved dependencies, with exact recorded source relationships and meanings.",
    "qualifications": "Original requested finite qualifications and associated roles/dependencies; no narrative diagnostic text.",
    "xmfa_coordinates": "Original selected XMFA cells with native, byte-verified source and separately evidenced original-member coordinates.",
    "xmfa_source_positions": "Original selected inverse XMFA position matches, preserving multiple placements and search completeness.",
    "xmfa_measurements": "Original selected XMFA block/site/pair measurements and their exact selected members and columns.",
    "xmfa_coverage": "Original selected interval-union coverage, repeated placements, denominators and separately qualified original-member coverage.",
}


def _require(condition, code):
    if not condition:
        raise ValueError(_PREFIX + code)


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
        "additionalProperties": False}


def _identifier(namespace, *, reference=False):
    return {"type": "string", "format": "reference" if reference else "identifier",
        "x-reference-namespace": namespace}


def _report_node(original, field=None):
    """Represent static outward records in the application's closed form grammar."""
    node = deepcopy(original)
    if "anyOf" in node:
        choices = node.pop("anyOf")
        _require(not node and len(choices) == 2
            and sum(choice == {"type": "null"} for choice in choices) == 1,
            "unsupported_fact_schema")
        value = next(choice for choice in choices if choice != {"type": "null"})
        result = _report_node(value, field)
        result["type"] = [result["type"], "null"]
        return result
    _require("oneOf" not in node and "allOf" not in node, "unsupported_fact_schema")
    if "enum" in node and "type" not in node:
        values = node["enum"]
        _require(all(value is None or type(value) is str for value in values), "unsupported_fact_schema")
        node["type"] = ["string", "null"] if None in values else "string"
    if field in {"strand", "native_strand"}:
        node.pop("enum", None)
        node["format"] = "alignment_strand"
    elif field in _SYMBOL_FIELDS:
        node["format"] = "alignment_symbol"
    pattern = node.pop("pattern", None)
    if pattern is not None:
        matches = [kind for kind in REFERENCE_KINDS
            if pattern.startswith("^bvbrc_alignment_" + kind + ":")]
        _require(len(matches) == 1, "unsupported_reference_schema")
        node.update(format="identifier", **{"x-reference-namespace": "bvbrc_alignment_" + matches[0]})
    node.pop("minLength", None)
    if "properties" in node:
        node["properties"] = {key: _report_node(value, key)
            for key, value in node["properties"].items()}
    if "items" in node:
        node["items"] = (_identifier("source", reference=True) if field == "source_refs"
            else _report_node(node["items"]))
    return node


def alignment_fact_sources() -> dict:
    """Fourteen finite families, preserving each saved source/field/value triple."""
    result = {}
    for selection, family in _SELECTION_FAMILIES.items():
        source = "bvbrc_alignment_" + family
        if source in result:
            continue
        value = _report_node(FACT_SCHEMAS[selection])
        result[source] = {"type": "array", "meaning": _MEANINGS[family], "report_schema": {
            "type": "array", "items": _object({
                "source_ref": _identifier("execution_result", reference=True),
                "field": _identifier("bvbrc_alignment_field"), "value": value}), "x-source": source}}
    return result


def requested_sources(schema: dict) -> tuple[str, ...]:
    return tuple(dict.fromkeys(node["x-source"]
        for node in plain(schema).get("properties", {}).values()
        if node.get("x-source") in FACT_SOURCES))


def _saved_content(value, binding, name):
    _finite_json(value)
    _require((value is None) == (binding is None), "saved_" + name + "_binding_conflict")
    if binding is not None:
        _require(binding["sha256"] == digest(value)
            and binding["byte_count"] == len(canonical(value).encode("utf-8")),
            "saved_" + name + "_content_conflict")


def _saved_facts(body, sheet_set, component_set):
    _require(type(body) is dict and body.get("version") == RESULT_VERSION, "publication_required")
    source = body.get("source_ref")
    _require(type(source) is str and _SOURCE_ID.fullmatch(source) is not None
        and body.get("reference") == source, "result_source_conflict")
    publication, inputs = body.get("publication"), body.get("publication_inputs")
    _require(type(publication) is dict and type(inputs) is dict, "publication_required")
    _require(publication.get("bundle_content", {}).get("source_ref") == source
        and source in publication.get("result_record_refs", []) and source in body.get("record_refs", []),
        "result_source_conflict")
    saved = validate_contract("AdapterResult", publication.get("adapter_result"))
    _require(saved["adapter_id"] in _ADAPTERS and saved["adapter_version"] == "1", "alignment_adapter_required")
    selector = validate_contract("ResultSelector", inputs.get("selector"))
    selected = selector["adapter"]
    _require(type(selected) is dict
        and all(selected.get(key) == saved[key] for key in ("adapter_id", "adapter_version"))
        and _same(inputs.get("adapter"), selected), "original_adapter_conflict")
    pin = inputs.get("adapter_implementation_sha256")
    _require(type(pin) is str and re.fullmatch(r"[0-9a-f]{64}", pin) is not None, "original_adapter_pin_required")
    _require(_same(body.get("assignment", {}).get("selector"), selector), "original_selector_conflict")
    provider = _ADAPTERS[saved["adapter_id"]]
    parameters = validate_parameters(selected["parameters"], provider=provider)
    schema = validate_requested_form(selector["requested_schema"], provider=provider)
    _saved_content(sheet_set, saved["sheet_content"], "sheet")
    _saved_content(component_set, saved["components_content"], "components")
    facts, properties = saved["facts"], schema["properties"]
    rows = {name: [] for name in FACT_SOURCES}
    if not facts and saved["status"] in {"invalid", "failed"}:
        return rows
    _require(set(facts) == set(properties), "requested_saved_facts_conflict")
    from .bvbrc_alignment_bundle_projection import validate_projected_facts
    validate_projected_facts(facts, sheet_set=sheet_set, component_set=component_set,
        missing_requirements=tuple(saved["missing_requirements"]), diagnostics=tuple(saved["diagnostics"]),
        requested_form=schema, parameters=parameters, provider=provider)
    for field, node in properties.items():
        selection = node["x-alignment-fact"]
        family = _SELECTION_FAMILIES[selection["kind"]]
        aid = selection.get("analysis_id")
        if aid is None:
            aid = "@families" if selection["kind"] == "multiplicity" else "@requirements"
        rows["bvbrc_alignment_" + family].append({"source_ref": source,
            "field": encode_reference("field", aid, field), "value": deepcopy(facts[field])})
    return rows


def project_alignment_facts(body: dict, *, requested_sources, sheet_set: dict | None,
                            component_set: dict | None) -> dict:
    """Copy only originally requested saved facts; caller authenticates custody."""
    _require(type(requested_sources) in (tuple, list, set, frozenset)
        and all(type(name) is str and name in FACT_SOURCES for name in requested_sources)
        and len(set(requested_sources)) == len(requested_sources), "requested_sources_invalid")
    try:
        rows = _saved_facts(body, sheet_set, component_set)
    except (KeyError, TypeError, IndexError, AttributeError, RecursionError) as error:
        raise ValueError(_PREFIX + "saved_identity_structure_invalid") from error
    return {name: rows[name] for name in requested_sources}


class BVBRCAlignmentReturns(EpisodeReturnRecords):
    def __init__(self, execution):
        super().__init__(execution.store, execution.run_id, failure_prefix=_PREFIX)
        self.api = execution

    def _latest(self, context):
        self.authenticate(context, allow_unsaved=True)
        latest = read_latest_adapter_result(self.api.appservice.publications, context,
                                           adapter_ids=tuple(_ADAPTERS))
        if latest is None:
            return None
        body = latest[0]
        self._require(body.get("run_id") == self.run_id and body.get("episode_id") == context.episode_id
            and self._equal(body.get("scope"), context.scope)
            and self._equal(body.get("assignment"), context.assignment)
            and self._equal(body["publication_inputs"].get("selector"), context.assignment.get("selector")),
            "publication_owner_conflict")
        return latest

    def facts(self, context, schema):
        sources = requested_sources(schema)
        latest = self._latest(context) if sources else None
        facts = ({name: [] for name in sources} if latest is None else
            project_alignment_facts(latest[0], requested_sources=sources,
                sheet_set=latest[1], component_set=latest[2]))
        for row in facts.get("bvbrc_alignment_requirements", []):
            for requirement in row["value"]:
                for reference in requirement["source_refs"]:
                    self._require(self.store.get(reference).get("record_type") == "source", "requirement_source_required")
                    self.api.appservice.custody.possession(context, reference)
        return facts

    def _attempts(self, context):
        self.authenticate(context, allow_unsaved=True)
        return self.db.execute("SELECT decision_index,contract FROM runtime_report_attempts "
            "WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL "
            "ORDER BY decision_index", (self.run_id, context.episode_id)).fetchall()

    def _attempt(self, context, index):
        # Custody authenticates full or compact forms against the original
        # decision's frozen fact catalog before returning the expanded schema.
        child, form, schema = self.api.appservice.custody._attempt(context, index)
        validate_form(form, schema, lambda *_: True)
        self.store.validate_scope(plain(child.scope), parent_scope=plain(context.scope))
        original_index = int(child.path[-1][1].removeprefix("child_"))
        row = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND decision_index=?", (self.run_id, context.episode_id, original_index)).fetchone()
        self._require(row is not None, "original_commission_required")
        selected = json.loads(row["action"])
        original = plain(child.request)["report_contract"]
        if selected.get("kind") in {"episode_child", "child", "job_child"}:
            self._require(self._equal(selected.get("scope"), child.scope)
                and selected.get("purpose") == original["decision"], "original_commission_conflict")
        if self._equal(schema, original["measurements"]["schema"]):
            frozen = self.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
                (self.run_id, child.episode_id)).fetchone()
            self._require(frozen is not None and frozen["form"] is not None
                and self._equal(json.loads(frozen["form"]), form), "frozen_form_conflict")
        return child, form, schema

    def _validate_values(self, context, form, schema):
        validate_form(form, schema, lambda *_: True)
        if context.role == "results":
            expected = self.facts(context, schema)
        elif context.role in {"annotation", "scientific_process"}:
            expected = self.received_facts(context, schema)
        else:
            raise ValueError(_PREFIX + "unsupported_return_owner")
        for name, node in schema.get("properties", {}).items():
            source = node.get("x-source")
            if source in FACT_SOURCES:
                self._require(name in form and self._equal(form[name], expected[source]), "returned_facts_conflict")
        frozen = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone()
        if frozen is not None:
            saved = json.loads(frozen["facts"])
            self._require(all(source in saved and self._equal(saved[source], expected[source])
                for source in requested_sources(schema)), "frozen_facts_conflict")

    def received_context(self, context):
        grouped, seen = {}, {}
        for attempt in self._attempts(context):
            schema = json.loads(attempt["contract"]).get("measurements", {}).get("schema", {})
            if not requested_sources(schema):
                continue
            child, form, original = self._attempt(context, attempt["decision_index"])
            self._validate_values(child, form, original)
            for name, node in original["properties"].items():
                source = node.get("x-source")
                if source not in FACT_SOURCES:
                    continue
                rows, identities = grouped.setdefault(source, []), seen.setdefault(source, set())
                for row in form[name]:
                    key = canonical(row)
                    if key not in identities:
                        rows.append(deepcopy(row))
                        identities.add(key)
        return [{"fact_source": source, "facts": rows} for source, rows in grouped.items()]

    def received_facts(self, context, schema):
        sources = requested_sources(schema)
        facts = {name: [] for name in sources}
        for value in self.received_context(context) if sources else ():
            if value["fact_source"] in facts:
                facts[value["fact_source"]] = value["facts"]
        return facts

    def validate_received_report(self, context, form, schema):
        if requested_sources(schema):
            self._validate_values(context, plain(form), plain(schema))

    def record_admission(self, context, form, schema, operation_key):
        if not requested_sources(schema):
            return []
        child, saved_form, saved_schema = self._attempt(context, self._admission_index(context, operation_key))
        self._require(self._equal(form, saved_form) and self._equal(schema, saved_schema), "admitted_form_conflict")
        self._validate_values(child, saved_form, saved_schema)
        return list(dict.fromkeys(reference for name, node in saved_schema["properties"].items()
            if node.get("x-source") in FACT_SOURCES for reference, namespace in _references(saved_form[name], node)
            if namespace in {"execution_result", "source"}))

    @staticmethod
    def _has_reference(facts, reference, namespace):
        schemas = alignment_fact_sources()
        return any(value == reference and kind == namespace for source, rows in facts.items()
            for value, kind in _references(rows, schemas[source]["report_schema"]))

    def resolve_own(self, context, reference, namespace):
        if namespace not in (*IDENTIFIER_NAMESPACES, "source", "execution_result", None):
            return None
        schema = (plain(context.request).get("report_contract") or {}).get("measurements", {}).get("schema", {})
        facts = form_validation_value((self, "own", _binding_key(context), canonical(schema)),
            lambda: self.facts(context, schema))
        found = self._has_reference(facts, reference, "source" if namespace is None else namespace)
        if namespace is None:
            found = found or self._has_reference(facts, reference, "execution_result")
        if found and namespace in {None, "source"}:
            self._require(self.store.get(reference).get("record_type") == "source", "requirement_source_required")
            self.api.appservice.custody.possession(context, reference)
        return found if namespace in IDENTIFIER_NAMESPACES or found else None

    def resolve_received(self, context, reference, namespace):
        if namespace not in (*IDENTIFIER_NAMESPACES, "source", "execution_result", None):
            return None
        facts = form_validation_value((self, "received", _binding_key(context)),
            lambda: {value["fact_source"]: value["facts"] for value in self.received_context(context)})
        found = self._has_reference(facts, reference, "source" if namespace is None else namespace)
        if namespace is None:
            found = found or self._has_reference(facts, reference, "execution_result")
        if found and namespace in {None, "source"}:
            self._require(self.store.get(reference).get("record_type") == "source", "requirement_source_required")
            self.api.appservice.custody.possession(context, reference)
        if namespace in IDENTIFIER_NAMESPACES or found:
            return found
        try:
            if self.store.get(reference).get("provider") == DATA_PROVIDER:
                return self.api.appservice.resolve(context, reference, namespace)
        except (ValueError, KeyError):
            return False
        return None


__all__ = ["BVBRCAlignmentReturns", "FACT_SOURCES", "IDENTIFIER_NAMESPACES",
    "alignment_fact_sources", "requested_sources", "project_alignment_facts"]
