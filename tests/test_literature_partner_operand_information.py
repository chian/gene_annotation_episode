"""Synthetic contract-information checks against the actual partner reader."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.composition_information import (
    CONTRACT_ARGUMENT_TRANSPORT, CONTRACT_INFORMATION_PROFILE,
)
from gene_annotation_episode.domain import validate_schema
from gene_annotation_episode.episode_contract_information import operation_contract_information
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_experimental_prompt import (
    EXPERIMENTAL_TASK, render_literature_experimental_prompt,
)
from gene_annotation_episode.literature_native_rate_operand_information import (
    rate_source_population_schema_with_information,
)
from gene_annotation_episode import literature_partner_operand_information as information
from gene_annotation_episode.literature_partner_native_inputs import (
    COMPONENTS, partner_source_population_schema, read_partner_native_inputs,
)
from gene_annotation_episode.literature_partner_prompt import PARTNER_TASK
from gene_annotation_episode.schema_information_text import parse_schema_information


SOURCE = "source_" + "1" * 24


def strip_descriptions(value):
    if isinstance(value, dict):
        return {name: strip_descriptions(child) for name, child in value.items()
                if name != "description"}
    if isinstance(value, list):
        return [strip_descriptions(child) for child in value]
    return value


def assert_only_description_additions(before, after):
    """Keep every existing value, including inherited REF descriptions, exact."""
    if isinstance(before, dict):
        assert set(after) - set(before) <= {"description"}
        assert set(before) <= set(after)
        for name, value in before.items():
            assert_only_description_additions(value, after[name])
    elif isinstance(before, list):
        assert isinstance(after, list) and len(before) == len(after)
        for left, right in zip(before, after):
            assert_only_description_additions(left, right)
    else:
        assert type(before) is type(after) and before == after


def fixture(*, introduction="One unit was defined as"):
    """Constructed bytes and supplied synthetic meanings; no paper/Store access."""
    clause = "2 nmol CompoundQ oxidized per min"
    bridge = introduction + " " + clause + ", 3 nmol CompoundR formed per second."
    lines = {role: f"µ {role} rate {token} U/mg +/- 1 U/mg SD."
             for role, token in (("reference", "8"), ("omitted", "2"), ("addback", "6"))}
    text = ("µ SubjectS; PartnerP; CompoundQ oxidation. CompoundQ oxidation. "
            "normalized per mg. complete conditions; nitrogen glutamine; temperature 37 degC.\n"
            + "\n".join(lines.values()) + "\n" + bridge)
    raw = text.encode()

    def read_source(ref, representation):
        assert ref == SOURCE and representation == "original"
        return {"artifact_ref": "synthetic:partner:artifact", "content": raw}

    def witness(quote, after=0):
        start = text.index(quote, after)
        return {"source_ref": SOURCE, "representation": "original",
                "start": len(text[:start].encode()),
                "end": len(text[:start + len(quote)].encode()), "quote": quote}

    def number(quote, token, after=0):
        start = quote.index(token)
        return {"witness": witness(quote, after), "number_start": start,
                "number_end": start + len(token)}

    endpoint = witness("CompoundQ oxidation")

    def unit(after):
        return {"kind": "source_defined_rate_unit", "witness": witness("U/mg", after),
                "definition": {"bridge": witness(bridge), "clause": witness(clause),
                    "amount": number(bridge, "2"), "amount_unit": witness("nmol", text.index(bridge)),
                    "time_unit": witness("min", text.index(bridge)),
                    "endpoint": deepcopy(endpoint), "endpoint_entity": witness("CompoundQ"),
                    "definition_entity": witness("CompoundQ", text.index(bridge))}}

    arms = {}
    for role, token in (("reference", "8"), ("omitted", "2"), ("addback", "6")):
        after = text.index(lines[role])
        arms[role] = {"subject": witness("SubjectS"), "partner": witness("PartnerP"),
            "endpoint": deepcopy(endpoint), "normalization": witness("normalized per mg"),
            "partner_state": "absent" if role == "omitted" else "present",
            "conditions": {"coverage": "complete", "factors": [
                {"factor": "nitrogen", "level": {"kind": "literal", "witness": witness("glutamine")}},
                {"factor": "temperature", "level": {"kind": "number",
                    "selector": number("temperature 37 degC", "37"), "unit_witness": witness("degC")}}]},
            "measurement_identity": witness("µ " + role + " rate"), "origin": "synthetic",
            "rate": {"value": number(lines[role], token), "unit": unit(after),
                "spread": {"kind": "SD", "magnitude": number(lines[role], "1"),
                    "unit": unit(text.index("+/-", after)), "witnesses": [witness("SD", after)]}}}
    args = {"source_ref": SOURCE, "data_source_ref": SOURCE, "source_kind": "synthetic_fixture",
        "input_mode": "native_source_spans", "literals": dict.fromkeys(("subject", "partner",
            "experiment", "endpoint", "normalization", "reference_condition", "omitted_condition",
            "addback_condition", "function")),
        "interpretation_witnesses": [witness("complete conditions")], "arms": arms}
    return args, read_source, witness, text


def checked_read(args, read_source, schema):
    validate_schema(args, schema)
    return read_partner_native_inputs(args, read_source=read_source)


def test_description_only_exact_equality_detachment_no_defaults_and_export():
    bare = partner_source_population_schema()
    before = deepcopy(bare)
    annotated = information.partner_source_population_schema_with_information()
    assert strip_descriptions(annotated) == strip_descriptions(bare)
    assert_only_description_additions(bare, annotated)
    assert bare == before
    assert "default" not in json.dumps(annotated)
    assert information.__all__ == ["partner_source_population_schema_with_information"]
    other = information.partner_source_population_schema_with_information()
    saved = deepcopy(other)
    annotated["properties"]["arms"]["properties"]["reference"]["anyOf"][0]["properties"]["rate"]["anyOf"][0]["properties"]["value"]["properties"]["number_start"]["minimum"] = 99
    assert other == saved
    assert strip_descriptions(other) == strip_descriptions(partner_source_population_schema())


def test_all_103_witnesses_15_number_selectors_and_six_definitions_have_information():
    counts = dict(witness=0, number=0, definition=0)
    def walk(node):
        if isinstance(node, dict):
            fields = node.get("properties", {})
            if set(fields) == {"source_ref", "representation", "start", "end", "quote"}:
                counts["witness"] += 1
                assert "half-open UTF-8 byte positions" in node["description"]
            if set(fields) == {"witness", "number_start", "number_end"}:
                counts["number"] += 1
                assert "Unicode characters" in node["description"]
                for name in ("number_start", "number_end"):
                    assert "Unicode character position inside witness.quote" in fields[name]["description"]
            if fields.get("kind", {}).get("const") == "source_defined_rate_unit":
                counts["definition"] += 1
                assert "no universal U conversion" in node["description"]
                assert "retains raw inputs" not in node["description"]
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    schema = information.partner_source_population_schema_with_information()
    walk(schema)
    assert counts == {"witness": 103, "number": 15, "definition": 6}
    assert json.dumps(schema).count("one unit was defined as") == 1


@pytest.mark.parametrize("role", ("reference", "omitted", "addback"))
def test_rate_and_spread_definition_instructions_bind_to_exact_role_endpoint(role):
    schema = information.partner_source_population_schema_with_information()
    rate = schema["properties"]["arms"]["properties"][role]["anyOf"][0]["properties"]["rate"]["anyOf"][0]["properties"]
    for unit in (rate["unit"], rate["spread"]["properties"]["unit"]["anyOf"][0]):
        plain, defined = unit["anyOf"]
        assert "bare U/mg witness is rejected" in plain["description"]
        fields = defined["properties"]["definition"]["properties"]
        assert "arguments.arms." + role + ".endpoint" in fields["endpoint"]["description"]
        assert "exact same witness" in fields["endpoint"]["description"]
        assert "different source occurrence" in fields["endpoint"]["description"]
        assert "all alternative endpoint branches" in fields["bridge"]["description"]
        assert "contained in the bridge" in fields["clause"]["description"]
        assert "actual source order" in fields["clause"]["description"]
        assert "physical numeric token must be contained in the clause" in fields["amount"]["description"]
        assert "endpoint occurrence" in fields["endpoint_entity"]["description"]
        assert "does not infer chemical aliases" in fields["definition_entity"]["description"]


def test_actual_reader_calculator_success_is_identical_with_either_schema():
    args, read_source, _witness, _text = fixture()
    before = deepcopy(args)
    bare = checked_read(args, read_source, partner_source_population_schema())
    informed = checked_read(args, read_source, information.partner_source_population_schema_with_information())
    assert bare == informed
    assert args == before
    assert [informed["cells"][name]["value"] for name in COMPONENTS] == [
        16000, 4000, 12000, 12000, .75, 8000, 2/3, .5]
    assert all(arm["rate"]["canonical_spread"] == 2000 for arm in informed["native_evidence"].values())


FAILURES = (
    ("endpoint_narrower", "defined_unit_endpoint_mismatch"),
    ("endpoint_equal_other_occurrence", "defined_unit_endpoint_mismatch"),
    ("bridge", "defined_unit_bridge_boundary_required"),
    ("endpoint_entity_elsewhere", "defined_unit_containment_required"),
    ("definition_entity_elsewhere", "defined_unit_containment_required"),
    ("time_other_branch", "defined_unit_containment_required"),
    ("inner_byte_index", "literal_source_number_required"),
    ("outer_character_index", "source_quote_mismatch"),
    ("bare_U", "unsupported_source_rate_unit"),
    ("unsupported_grammar", "defined_unit_bridge_unsupported"),
)


def failure_fixture(case, role="reference", spread=False):
    args, read_source, witness, text = fixture(introduction=(
        "One unit corresponds to" if case == "unsupported_grammar" else "One unit was defined as"))
    arm = args["arms"][role]
    rate = arm["rate"]
    selected = rate["spread"] if spread else rate
    definition = selected["unit"]["definition"]
    if case == "endpoint_narrower":
        definition["endpoint"] = witness("CompoundQ")
    elif case == "endpoint_equal_other_occurrence":
        definition["endpoint"] = witness("CompoundQ oxidation", text.index("CompoundQ oxidation") + 1)
    elif case == "bridge":
        definition["bridge"] = witness("One unit was defined as 2 nmol CompoundQ")
    elif case == "endpoint_entity_elsewhere":
        definition["endpoint_entity"] = deepcopy(definition["definition_entity"])
    elif case == "definition_entity_elsewhere":
        definition["definition_entity"] = deepcopy(definition["endpoint_entity"])
    elif case == "time_other_branch":
        definition["time_unit"] = witness("second")
    elif case == "inner_byte_index":
        number = rate["value"]
        number["number_start"] = len(number["witness"]["quote"][:number["number_start"]].encode())
        number["number_end"] = number["number_start"] + 1
    elif case == "outer_character_index":
        number = rate["value"]["witness"]
        number["start"] = text.index(number["quote"])
        number["end"] = number["start"] + len(number["quote"])
    elif case == "bare_U":
        selected["unit"] = selected["unit"]["witness"]
    return args, read_source


@pytest.mark.parametrize("case,code", FAILURES)
def test_actual_partner_failures_keep_exact_same_error_with_either_schema(case, code):
    args, read_source = failure_fixture(case)
    before = deepcopy(args)
    failures = []
    for schema in (partner_source_population_schema(), information.partner_source_population_schema_with_information()):
        with pytest.raises(ExperimentalContractError) as caught:
            checked_read(args, read_source, schema)
        failures.append((caught.value.code, caught.value.field))
    assert failures[0] == failures[1]
    assert failures[0][0] == code
    assert args == before


@pytest.mark.parametrize("role", ("reference", "omitted", "addback"))
@pytest.mark.parametrize("spread", (False, True))
def test_exact_endpoint_equality_and_containment_apply_to_every_arm_rate_and_spread(role, spread):
    for case, code in (("endpoint_equal_other_occurrence", "defined_unit_endpoint_mismatch"),
                       ("endpoint_entity_elsewhere", "defined_unit_containment_required")):
        args, read_source = failure_fixture(case, role=role, spread=spread)
        with pytest.raises(ExperimentalContractError) as caught:
            checked_read(args, read_source, information.partner_source_population_schema_with_information())
        assert caught.value.code == code


@pytest.mark.parametrize("with_failure", (False, True))
@pytest.mark.parametrize("profile", (False, True))
def test_actual_catalog_contract_information_and_ordinary_prompt_keep_task_and_steering_separate(profile, with_failure):
    catalog = _population_catalog()
    # Check the partner operations under test; unrelated reader additions do
    # not change this contract or the number of biological evidence axes.
    assert {row['name'] for row in catalog if row['name'].startswith('literature.partner.')} == {
        'literature.partner.populate', 'literature.partner.source.populate'}
    assert next(row for row in catalog if row["name"] == "literature.rate.source.populate")["input_schema"] == rate_source_population_schema_with_information()
    entry = next(row for row in catalog if row["name"] == "literature.partner.source.populate")
    assert entry["input_schema"] == information.partner_source_population_schema_with_information()
    assert strip_descriptions(entry["input_schema"]) == strip_descriptions(partner_source_population_schema())
    assert_only_description_additions(partner_source_population_schema(), entry["input_schema"])
    outcome = operation_contract_information(catalog=catalog, operation=entry["name"])
    assert parse_schema_information(outcome["result"]["text"]) == entry["input_schema"]
    state = {"literature_experimental_work": {"version": "literature_experimental_task_v1"},
        "goal": {"objective": "Evaluate a synthetic partner experiment."}, "scope": {},
        "literature_assignment": {"requested_partner_components": ["partner_loss"]}, "tools": [entry]}
    if profile:
        state["contract_information_profile"] = CONTRACT_INFORMATION_PROFILE
        state["tools"] = [{**entry, "argument_transport": CONTRACT_ARGUMENT_TRANSPORT}]
    if with_failure:
        state["last_local_outcome"] = {"status": "invalid", "feedback": {
            "category": "arguments_or_reference", "code": "defined_unit_endpoint_mismatch",
            "field": "defined_unit.definition.endpoint"}}
    rendered = render_literature_experimental_prompt(state, "Synthetic recurring assignment.",
        lookup_results=[outcome] if profile else ())
    task, steering = rendered.split("\n\nSTEERING", 1)
    assert PARTNER_TASK in task
    assert "Synthetic recurring assignment." in task
    assert "UTF-8 byte positions" in task
    assert "Unicode character position inside witness.quote" in task
    for role in ("reference", "omitted", "addback"):
        assert "arguments.arms." + role + ".endpoint" in task
    assert "one unit was defined as" in task
    assert "one unit was defined as" not in steering
    assert ("defined_unit_endpoint_mismatch" in steering) == with_failure
    assert "defined_unit_endpoint_mismatch" not in task


def test_metadata_module_bytes_participate_in_actual_binding_identity(monkeypatch):
    binding = LiteratureEpisodes(None, rate_population=True)
    original = binding.as_record()
    original_fact_sources = binding.fact_sources("literature")
    read_bytes = Path.read_bytes
    def altered(path):
        value = read_bytes(path)
        return value + b"\n# synthetic identity probe\n" if path.name == "literature_partner_operand_information.py" else value
    monkeypatch.setattr(Path, "read_bytes", altered)
    assert original["implementation_sha256"] != binding.as_record()["implementation_sha256"]
    assert binding.fact_sources("literature") == original_fact_sources


def test_dispatch_probe_proves_only_one_selected_repository_route(monkeypatch):
    args, _read_source, _witness, _text = fixture()
    calls = []
    outcome = {"status": "completed", "result": {"synthetic_dispatch_probe": True}}
    class Repository:
        def populate(self, context, selected, key):
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
    # This unit test isolates dispatch after argument admission. Actual source
    # authorization is exercised by the storage and ordinary-episode tests.
    monkeypatch.setattr(binding, '_tool_arguments', lambda context, name, args: args)
    result = asyncio.run(binding.execute(
        context, "literature.partner.source.populate", args, "synthetic:partner:operation"))
    assert result is outcome
    assert calls == [(context, args, "synthetic:partner:operation")]
