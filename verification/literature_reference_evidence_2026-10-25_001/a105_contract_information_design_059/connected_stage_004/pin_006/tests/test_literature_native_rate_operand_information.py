"""Synthetic usability and unchanged-contract checks for native rate operands."""
from copy import deepcopy
import asyncio
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.domain import validate_schema
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_experimental_prompt import (
    EXPERIMENTAL_TASK, render_literature_experimental_prompt,
)
from gene_annotation_episode.literature_native_rate_operand_information import (
    rate_source_population_schema_with_information,
)
from gene_annotation_episode.literature_rate_native_inputs import (
    rate_source_population_schema, read_rate_source_inputs,
)
from gene_annotation_episode.scientific_process_prompt import _schema


SOURCE_REF = "source_" + "1" * 24


def strip_descriptions(value):
    if isinstance(value, dict):
        return {name: strip_descriptions(child) for name, child in value.items()
                if name != "description"}
    if isinstance(value, list):
        return [strip_descriptions(child) for child in value]
    return value


def fixture():
    text = (
        "<p>CompoundQ oxidation; synthetic assay; protein mass normalization. "
        "\u03bc reference rate 8 U/mg; test rate 2 U/mg.</p>\n"
        "<p>One unit was defined as 2 nmol CompoundQ oxidized per min.</p>"
    )
    raw = text.encode("utf-8")
    def source(reference, representation):
        assert reference == SOURCE_REF and representation == "original"
        return {"artifact_ref": "synthetic:artifact", "content": raw}
    def witness(quote, after=0):
        start = text.index(quote, after)
        return {"source_ref": SOURCE_REF, "representation": "original",
            "start": len(text[:start].encode()),
            "end": len(text[:start + len(quote)].encode()), "quote": quote}
    def number(quote, token):
        start = quote.index(token)
        return {"witness": witness(quote), "number_start": start,
                "number_end": start + len(token)}
    endpoint = witness("CompoundQ oxidation")
    normal = witness("protein mass normalization")
    bridge = "One unit was defined as 2 nmol CompoundQ oxidized per min."
    defined = {"kind": "source_defined_rate_unit", "witness": witness("U/mg"),
        "definition": {"bridge": witness(bridge),
            "clause": witness("2 nmol CompoundQ oxidized per min"),
            "amount": number("2 nmol CompoundQ oxidized per min", "2"),
            "amount_unit": witness("nmol"), "time_unit": witness("min"),
            "endpoint": endpoint, "endpoint_entity": witness("CompoundQ"),
            "definition_entity": witness("CompoundQ", text.index(bridge))}}
    arms = {}
    for role, quote, token in (("reference", "\u03bc reference rate 8 U/mg", "8"),
                               ("test", "test rate 2 U/mg", "2")):
        arm = {name: None for name in ("subject", "construct", "preparation",
            "experiment", "label", "condition", "measurement_identity")}
        arm.update(endpoint=deepcopy(endpoint), normalization=deepcopy(normal),
            rate={"number": number(quote, token), "unit": deepcopy(defined)},
            uncertainty={"kind": "unreported", "magnitude": None, "unit": None,
                "kind_witnesses": [], "count": None,
                "sampling_basis": {"value": "unspecified", "witnesses": []}})
        arms[role] = arm
    args = {"input_mode": "native_source_spans", "source_ref": SOURCE_REF,
        "source_kind": "synthetic_fixture", "experiment": witness("synthetic assay"),
        "arms": arms, "comparison": {
            "subject_relation": {"value": "unknown", "witnesses": []},
            "endpoint_relation": {"value": "same", "witnesses": [deepcopy(endpoint)]},
            "normalization_relation": {"value": "same", "witnesses": [deepcopy(normal)]},
            "intended_change": None},
        "dependence": {"value": "unknown", "witnesses": []},
        "observation_model": {"value": "none", "witnesses": []}}
    return args, source, witness


def test_descriptions_change_no_validation_keyword_or_schema_value():
    original = rate_source_population_schema()
    before = deepcopy(original)
    annotated = rate_source_population_schema_with_information()
    assert strip_descriptions(annotated) == strip_descriptions(original)
    assert original == before
    assert annotated != original
    assert "default" not in json.dumps(annotated)


def test_schema_builds_are_detached_from_factory_and_each_other():
    first = rate_source_population_schema_with_information()
    second = rate_source_population_schema_with_information()
    saved = deepcopy(second)
    first["properties"]["arms"]["properties"]["reference"]["anyOf"][0]["properties"]["rate"]["anyOf"][0]["properties"]["number"]["properties"]["number_start"]["minimum"] = 99
    assert second == saved
    assert strip_descriptions(second) == strip_descriptions(rate_source_population_schema())


def test_every_witness_and_numeric_selector_explains_its_coordinate_space():
    found = {"witness": 0, "number": 0}
    def walk(node):
        if isinstance(node, dict):
            properties = node.get("properties", {})
            if set(properties) == {"source_ref", "representation", "start", "end", "quote"}:
                found["witness"] += 1
                assert "UTF-8 byte positions" in node["description"]
                assert "half-open" in node["description"]
            if set(properties) == {"witness", "number_start", "number_end"}:
                found["number"] += 1
                assert "Unicode characters" in node["description"]
                assert "Unicode character position" in properties["number_start"]["description"]
                assert "Unicode character position" in properties["number_end"]["description"]
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(rate_source_population_schema_with_information())
    assert found["witness"] > 20 and found["number"] > 4


def test_defined_units_reference_the_correct_arm_endpoint_and_retain_full_rules():
    schema = rate_source_population_schema_with_information()
    assert "one unit was defined as" in schema["description"]
    assert "wording is a reader limitation" in schema["description"]
    # The long finite grammar is supplied once at the parent schema.
    assert json.dumps(schema).count("one unit was defined as") == 1
    for role in ("reference", "test"):
        arm = schema["properties"]["arms"]["properties"][role]["anyOf"][0]["properties"]
        for unit in (arm["rate"]["anyOf"][0]["properties"]["unit"],
                     arm["uncertainty"]["properties"]["unit"]):
            definition = unit["anyOf"][1]["properties"]["definition"]["properties"]
            assert "arguments.arms." + role + ".endpoint" in definition["endpoint"]["description"]
            assert "exact same witness" in definition["endpoint"]["description"]
            assert "alternative endpoint branches" in definition["bridge"]["description"]
            assert "source order" in definition["clause"]["description"]
            assert "endpoint occurrence" in definition["endpoint_entity"]["description"]
            assert "does not infer chemical aliases" in definition["definition_entity"]["description"]


def test_synthetic_definition_success_and_missing_definition_partial_are_unchanged():
    args, read_source, _witness = fixture()
    validate_schema(args, rate_source_population_schema())
    validate_schema(args, rate_source_population_schema_with_information())
    before = deepcopy(args)
    extracted = read_rate_source_inputs(args, read_source=read_source)
    assert [row["value"] for row in extracted["rows"]] == [0.016, 0.004]
    assert args == before
    for arm in args["arms"].values():
        arm["rate"]["unit"] = arm["rate"]["unit"]["witness"]
    validate_schema(args, rate_source_population_schema_with_information())
    partial = read_rate_source_inputs(args, read_source=read_source)
    assert [row["value"] for row in partial["rows"]] == [None, None]
    assert [row["source"]["number"]["value"] for row in partial["rows"]] == [8, 2]
    assert all(row["source"]["unit"]["unavailable_reason"] ==
               "source_defined_unit_definition_required" for row in partial["rows"])


@pytest.mark.parametrize("case,code", (
    ("endpoint", "defined_unit_endpoint_mismatch"),
    ("bridge", "defined_unit_bridge_boundary_required"),
    ("entity_occurrence", "defined_unit_containment_required"),
    ("inner_byte_index", "literal_source_number_required"),
))
def test_synthetic_source_relationship_failures_remain_rejected(case, code):
    args, read_source, witness = fixture()
    rate = args["arms"]["reference"]["rate"]
    definition = rate["unit"]["definition"]
    if case == "endpoint":
        definition["endpoint"] = witness("CompoundQ")
    elif case == "bridge":
        definition["bridge"] = witness("One unit was defined as 2 nmol CompoundQ")
    elif case == "entity_occurrence":
        definition["endpoint_entity"] = deepcopy(definition["definition_entity"])
    else:
        selected = rate["number"]
        selected["number_start"] = len(selected["witness"]["quote"][:selected["number_start"]].encode())
        selected["number_end"] = selected["number_start"] + 1
    validate_schema(args, rate_source_population_schema())
    validate_schema(args, rate_source_population_schema_with_information())
    with pytest.raises(ExperimentalContractError) as caught:
        read_rate_source_inputs(args, read_source=read_source)
    assert caught.value.code == code


@pytest.mark.parametrize("with_failure", (False, True))
def test_actual_catalog_schema_meanings_recur_in_task_and_feedback_stays_in_steering(with_failure):
    catalog = _population_catalog()
    assert len(catalog) == 19
    entry = next(row for row in catalog if row["name"] == "literature.rate.source.populate")
    assert entry["input_schema"] == rate_source_population_schema_with_information()
    assert strip_descriptions(entry["input_schema"]) == strip_descriptions(rate_source_population_schema())
    state = {"literature_experimental_work": {"version": "literature_experimental_task_v1"},
        "goal": {"objective": "Evaluate a synthetic reference experiment."}, "scope": {},
        "literature_assignment": {"requested_rate_components": ["rate_difference"]},
        "tools": [entry]}
    if with_failure:
        state["last_local_outcome"] = {"status": "invalid", "feedback": {
            "category": "arguments_or_reference", "code": "defined_unit_endpoint_mismatch",
            "field": "defined_unit.definition.endpoint"}}
    rendered = render_literature_experimental_prompt(state, "Synthetic recurring assignment.")
    task, steering = rendered.split("\n\nSTEERING", 1)
    assert EXPERIMENTAL_TASK in task
    assert "Synthetic recurring assignment." in task
    assert "UTF-8 byte positions" in task
    assert "Unicode character position inside witness.quote" in task
    assert "arguments.arms.reference.endpoint" in task
    assert "arguments.arms.test.endpoint" in task
    assert "one unit was defined as" in task
    assert "one unit was defined as" not in steering
    assert ("defined_unit_endpoint_mismatch" in steering) == with_failure
    assert "exact same witness" in _schema(entry["input_schema"], "arguments")


def test_actual_c7_dispatch_is_still_one_selected_native_repository_call():
    args, _read_source, _witness = fixture()
    calls = []
    outcome = {"status": "completed", "result": {"synthetic_dispatch_probe": True}}
    class Repository:
        def populate_native(self, context, selected, key):
            calls.append((context, deepcopy(selected), key))
            return outcome
    class Services:
        def tool_catalog(self, scope):
            return {}
        def __getattr__(self, name):
            if name.startswith("literature_") and name.endswith("_repository"):
                return lambda: Repository()
            raise AttributeError(name)
    context = SimpleNamespace(role="literature", scope={}, assignment={
        "version": "literature_assignment_v1", "question_context_refs": [], "source_refs": []})
    binding = LiteratureEpisodes(Services(), rate_population=True)
    result = asyncio.run(binding.execute(context, "literature.rate.source.populate", args, "synthetic:operation"))
    assert result is outcome
    assert calls == [(context, args, "synthetic:operation")]
    assert binding.fact_sources("literature")["literature_rate_source_cells"]["report_schema"]["x-source"] == "literature_rate_source_cells"
