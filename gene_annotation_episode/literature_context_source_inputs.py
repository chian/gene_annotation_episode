"""Episode-selected A108 operands anchored in ordinary acquired sources.

The model interprets requirements and biological relations. This reader verifies
the selected source spans and parses native numbers; it does not judge that an
interpretation is true. The existing compatibility calculator owns arithmetic.
"""
from copy import deepcopy

from .domain import REF, identity, obj
from .literature_assay_inputs import _fail, _witness_schema, _nullable
from .literature_context_native_inputs import _quantity
from .literature_partner_source_fields import read_source_number


VERSION = "a108_context_source_selection_v1"


def source_selection_schema():
    from .literature_context_inputs import (
        NATIVE_UNITS, QUESTION_KINDS, PAIRINGS, WEIGHT_BASES, SAMPLING_DESIGNS,
        SCOPE_MATCHES, RELATIONS, REPLICATE_KINDS,
    )
    from .literature_context_meanings import REQUIREMENT_FIELDS, ROUTE_FIELDS
    witness = _witness_schema()
    witnesses = {"type": "array", "items": deepcopy(witness)}
    nullable_witness = _nullable(deepcopy(witness))
    number = obj({"witness": deepcopy(witness),
        "number_start": {"type": "integer", "minimum": 0},
        "number_end": {"type": "integer", "minimum": 1}})
    quantity = obj({"number": number, "unit_witness": deepcopy(witness)})
    interval = obj({"lower": _nullable(deepcopy(quantity)),
        "upper": _nullable(deepcopy(quantity)), "lower_closed": {"type": "boolean"},
        "upper_closed": {"type": "boolean"}, "basis": deepcopy(witnesses)})
    domains = {"type": "array", "items": interval}
    definition = obj({"key": {"type": "string", "minLength": 1},
        "unit": {"enum": list(NATIVE_UNITS)}, "supported": deepcopy(domains),
        "incompatible": deepcopy(domains)})
    route = obj({"key": {"type": "string", "minLength": 1},
        "requirements": {"type": "array", "items": {"type": "string"}, "uniqueItems": True,
            "description": "Keys of the requirements that must hold together for this route within the declared claim and biological scope."},
        "requirements_complete": {"type": "boolean",
            "description": "Whether the source-supported requirement set is complete for this scoped route. False retains an unresolved lower bound even if all listed requirements are met."},
        "joint_support": {"enum": ["established", "unresolved", "conflicting"],
            "description": "Evidence that the listed requirements describe one jointly applicable biological route; separate favorable experiments do not establish their conjunction."}})
    observation = obj({"requirement_key": {"type": "string", "minLength": 1},
        "measurement_identity": deepcopy(nullable_witness),
        "unit": {"enum": list(NATIVE_UNITS)}, "interval": _nullable(deepcopy(interval)),
        "relation": {"enum": list(RELATIONS)},
        "interpretation": {"type": "string", "minLength": 1}, "basis": deepcopy(witnesses),
        **{name: _nullable(deepcopy(quantity)) for name in
           ("reported_sd", "reported_sem", "reported_plusminus")},
        "reported_count": _nullable(deepcopy(number)),
        "replicate_kind": {"enum": list(REPLICATE_KINDS)}})
    # A declared state relation is an interpretation of cited evidence. Unknown
    # states may have no witness; positive or negative claims must identify one.
    # This authenticates the evidence basis, not the truth of the interpretation.
    observation["allOf"] = [{
        "if": {"properties": {"relation": {"enum": ["supported", "incompatible"]}}},
        "then": {"properties": {"basis": {"minItems": 1}}},
    }]
    context = obj({"key": {"type": "string", "minLength": 1},
        "identity": deepcopy(nullable_witness), "cluster": deepcopy(nullable_witness),
        "scope_match": {"enum": list(SCOPE_MATCHES)}, "scope_basis": deepcopy(witnesses),
        "weight": {"anyOf": [{"const": "equal_unit"}, number, {"type": "null"}]},
        "observations": {"type": "array", "items": observation}})
    meanings = obj({plural: {"type": ["array", "null"] if plural == "routes" else "array",
        "items": obj({"key": {"type": "string", "minLength": 1},
            **{name: deepcopy(nullable_witness) for name in fields}})}
        for plural, fields in (("requirements", REQUIREMENT_FIELDS), ("routes", ROUTE_FIELDS))})
    marginal = obj({"requirement_key": {"type": "string", "minLength": 1},
        "lower": deepcopy(number), "upper": deepcopy(number),
        "basis": deepcopy(witnesses)})
    return obj({"version": {"const": VERSION},
        "question": obj({"subject_ref": deepcopy(REF),
            "assertion_ref": {**REF, "x-reference-namespace": "hypothesis"},
            "scope": {"type": "string", "minLength": 1},
            "rationale": {"type": "string", "minLength": 1},
            "basis": deepcopy(witnesses)}),
        "settings": obj({"question_kind": {"enum": list(QUESTION_KINDS)},
            "scope_status": {"enum": ["defined", "unreported"]},
            "frame_status": {"enum": ["defined", "unreported"]},
            "pairing": {"enum": list(PAIRINGS)}, "weight_basis": {"enum": list(WEIGHT_BASES)},
            "sampling_design": {"enum": list(SAMPLING_DESIGNS)},
            "alpha": {"type": ["number", "null"], "exclusiveMinimum": 0, "exclusiveMaximum": 1},
            "permitted_remainder": {"type": ["boolean", "null"]},
            "interpretation": {"type": "string", "minLength": 1}, "basis": deepcopy(witnesses)}),
        "requirements": {"type": "array", "items": definition},
        "routes": {"type": ["array", "null"], "minItems": 1, "items": route,
            "description": "Explicit combinations of requirements, including a single route when there are no known alternatives. Null means the route structure is unreported and leaves compatibility unresolved; it does not mean that the listed requirements automatically form one complete route. Preserve source support in meanings.routes and settings.basis."},
        "contexts": {"type": "array", "items": context},
        "marginals": {"type": "array", "items": marginal}, "meanings": meanings})


def selected_source_refs(value):
    """Declared span sources only; this traversal interprets no source content."""
    result = []
    def visit(item):
        if isinstance(item, dict):
            if "source_ref" in item and "representation" in item:
                result.append(item["source_ref"])
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)
    visit(value)
    return list(dict.fromkeys(result))


def read_source_selection(value, *, sources, source_ref):
    from .domain import validate_schema
    from .literature_context_inputs import _validate_inputs
    from .literature_context_meanings import DATA_VERSION
    validate_schema(value, source_selection_schema())
    evidence = {"version": VERSION, "question": deepcopy(value["question"]),
        "settings": deepcopy(value["settings"]), "requirements": [], "contexts": [], "marginals": []}

    def spans(items, path):
        return [sources.witness(item, f"{path}[{i}]") for i, item in enumerate(items)]

    def reading(item, unit, path, *, spread=False):
        return _quantity(item, unit, sources, path, spread=spread)

    def domain(item, unit, path):
        if item is None:
            return None, None
        lower = reading(item["lower"], unit, path + ".lower")
        upper = reading(item["upper"], unit, path + ".upper")
        core = {"lower": None if lower is None else lower["value"],
            "upper": None if upper is None else upper["value"],
            "lower_closed": item["lower_closed"], "upper_closed": item["upper_closed"]}
        trace = {**deepcopy(core), "lower_reading": lower, "upper_reading": upper,
            "basis": spans(item["basis"], path + ".basis")}
        return core, trace

    def number(item, path):
        if item is None:
            return None, None
        trace = read_source_number(item, sources=sources, role="condition")
        if trace["relation"] != "point":
            _fail("context_source_point_required", path)
        return float(trace["raw_number"].replace("−", "-")), trace

    def witnessed(item, path):
        return None if item is None else sources.witness(item, path)

    evidence["question"]["basis"] = spans(value["question"]["basis"], "question.basis")
    evidence["settings"]["basis"] = spans(value["settings"]["basis"], "settings.basis")
    inputs = {key: deepcopy(item) for key, item in value["settings"].items()
        if key not in ("basis", "interpretation")}
    inputs.update(origin="graph_derived", requirements=[], routes=deepcopy(value["routes"]),
        contexts=[], marginals=[])
    for i, requirement in enumerate(value["requirements"]):
        path = f"requirements[{i}]"
        core = {key: requirement[key] for key in ("key", "unit")}
        trace = deepcopy(core)
        for side in ("supported", "incompatible"):
            pairs = [domain(item, requirement["unit"], f"{path}.{side}[{j}]")
                for j, item in enumerate(requirement[side])]
            core[side] = [pair[0] for pair in pairs]
            trace[side] = [pair[1] for pair in pairs]
        inputs["requirements"].append(core)
        evidence["requirements"].append(trace)
    for i, context in enumerate(value["contexts"]):
        path = f"contexts[{i}]"
        context_identity = witnessed(context["identity"], path + ".identity")
        cluster = witnessed(context["cluster"], path + ".cluster")
        scope_basis = spans(context["scope_basis"], path + ".scope_basis")
        if context["weight"] == "equal_unit":
            if inputs["weight_basis"] != "equal_units":
                _fail("context_source_weight_basis_mismatch", path + ".weight")
            weight, weight_trace = 1, {"method": "equal_unit"}
        else:
            weight, weight_trace = number(context["weight"], path + ".weight")
        key = identity("context_physical", context_identity or
            {"source_ref": source_ref, "question": value["question"], "key": context["key"]})
        core = {"key": key, "weight": weight,
            "cluster_key": None if cluster is None else identity("context_cluster", cluster),
            "scope_match": context["scope_match"], "observations": []}
        trace = {"key": key, "identity": context_identity, "cluster": cluster,
            "scope_basis": scope_basis, "weight": weight_trace, "observations": []}
        for j, observation in enumerate(context["observations"]):
            opath = f"{path}.observations[{j}]"
            physical = witnessed(observation["measurement_identity"], opath + ".measurement_identity")
            basis = spans(observation["basis"], opath + ".basis")
            interval, interval_trace = domain(observation["interval"], observation["unit"], opath + ".interval")
            spreads = {name: reading(observation[name], observation["unit"], opath + "." + name, spread=True)
                for name in ("reported_sd", "reported_sem", "reported_plusminus")}
            count, count_trace = number(observation["reported_count"], opath + ".reported_count")
            if count is not None and (not count.is_integer() or count < 0):
                _fail("context_source_integer_count_required", opath + ".reported_count")
            measurement_key = identity("context_measurement", physical or
                {"context": key, "requirement": observation["requirement_key"],
                 "interval": interval_trace, "basis": basis})
            core["observations"].append({"requirement_key": observation["requirement_key"],
                "measurement_key": measurement_key, "unit": observation["unit"],
                "interval": interval, "relation": observation["relation"],
                **{name: None if item is None else item["value"] for name, item in spreads.items()},
                "reported_count": None if count is None else int(count),
                "count_relation": "unknown" if count is None else "exact",
                "replicate_kind": observation["replicate_kind"]})
            trace["observations"].append({"measurement_key": measurement_key,
                "measurement_identity": physical, "basis": basis,
                "interpretation": observation["interpretation"], "interval": interval_trace,
                "spreads": spreads, "reported_count": count_trace})
        inputs["contexts"].append(core)
        evidence["contexts"].append(trace)
    for i, marginal in enumerate(value["marginals"]):
        lower, lower_trace = number(marginal["lower"], f"marginals[{i}].lower")
        upper, upper_trace = number(marginal["upper"], f"marginals[{i}].upper")
        inputs["marginals"].append({"requirement_key": marginal["requirement_key"], "lower": lower, "upper": upper})
        evidence["marginals"].append({"lower": lower_trace, "upper": upper_trace,
            "basis": spans(marginal["basis"], f"marginals[{i}].basis")})
    inputs["contexts"] = _validate_inputs(inputs)
    data = {"version": DATA_VERSION, "inputs": inputs, "meanings": deepcopy(value["meanings"])}
    return data, inputs, evidence
