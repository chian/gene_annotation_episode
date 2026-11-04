"""Actual source bytes bind U to one endpoint, rather than a universal alias."""
from copy import deepcopy
from fractions import Fraction

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_partner_defined_units import (
    convert_defined_source_number, defined_rate_unit_schema,
    parsed_defined_rate_unit_schema, read_defined_rate_unit,
    validate_defined_spread_unit,
)
from gene_annotation_episode.literature_partner_source_fields import (
    read_source_number, read_source_rate_unit,
)


SOURCE = "source_" + "a" * 24
OTHER = "source_" + "b" * 24
ARTIFACT = "artifact_" + "c" * 64
OTHER_ARTIFACT = "artifact_" + "d" * 64


def fixture(*, entity="NADH", endpoint_entity=None, coefficient="1", quantity="µmol",
            time="min", bridge=None, clause=None, rate="7", spread="SD 58 U/mg",
            header="U/mg", representation="original"):
    endpoint_entity = entity if endpoint_entity is None else endpoint_entity
    endpoint_quote = endpoint_entity + " oxidation (measured photometrically)"
    clause = clause or f"{coefficient} {quantity} of {entity} oxidized per {time}"
    bridge = bridge or f"One unit was equivalent to {clause}, 1 µmol of TTC reduced per min, or 1 µmol of H2 formed per min."
    text = (f"µ source\n{endpoint_quote}\nSp act ({header})\nMeasured rate {rate}; "
            f"{spread}. Other units nmol/min/mg; umol/min/mg; pmol/min/mg.\n{bridge}")
    raw = text.encode()
    calls = []
    def read(reference, selected_representation):
        calls.append((reference, selected_representation))
        return {"artifact_ref": ARTIFACT if reference == SOURCE and selected_representation == representation else OTHER_ARTIFACT,
            "content": raw}
    sources = _Sources(read)
    def witness(quote, *, offset=0, reference=SOURCE, rep=representation):
        start = raw.index(quote.encode(), offset)
        return {"source_ref": reference, "representation": rep, "start": start,
            "end": start + len(quote.encode()), "quote": quote}
    def number(token, quote, *, offset=0):
        selected = witness(quote, offset=offset)
        start = quote.index(token)
        return {"witness": selected, "number_start": start, "number_end": start + len(token)}
    selected_clause = witness(clause)
    clause_start = selected_clause["start"]
    endpoint = witness(endpoint_quote)
    selection = {"kind": "source_defined_rate_unit", "witness": witness(header),
        "definition": {"bridge": witness(bridge), "clause": selected_clause,
            "amount": number(coefficient, clause),
            "amount_unit": witness(quantity, offset=clause_start),
            "time_unit": witness(time, offset=clause_start), "endpoint": endpoint,
            "endpoint_entity": witness(endpoint_entity, offset=endpoint["start"]),
            "definition_entity": witness(entity, offset=clause_start)}}
    main = read_source_number(number(rate.lstrip("<"), "Measured rate " + rate), sources=sources, role="rate")
    return {"selection": selection, "sources": sources, "endpoint": endpoint,
        "main": main, "witness": witness, "number": number, "text": text,
        "calls": calls}


def read(fix):
    return read_defined_rate_unit(fix["selection"], sources=fix["sources"], endpoint=fix["endpoint"])


def failure(code, function, *args, **kwargs):
    with pytest.raises(ExperimentalContractError) as caught:
        function(*args, **kwargs)
    assert caught.value.code == code


def test_source_definition_is_closed_enriched_and_has_no_mutation_aliases():
    fix = fixture()
    before = deepcopy(fix["selection"])
    validate_schema(before, defined_rate_unit_schema())
    unit = read(fix)
    validate_schema(unit, parsed_defined_rate_unit_schema())
    assert unit["raw_unit"] == "U/mg" and unit["canonical_unit"] == "pmol/min/mg"
    assert unit["multiplier"] == 1000000
    assert unit["definition"]["amount"]["raw_number"] == "1"
    assert unit["definition"]["amount_unit"]["quote"] == "µmol"
    assert all(w["artifact_ref"] == ARTIFACT for key, w in unit["definition"].items() if key != "amount")
    assert fix["selection"] == before
    unit["definition"]["bridge"]["quote"] = "altered"
    assert fix["selection"] == before
    assert set(fix["calls"]) == {(SOURCE, "original")}


@pytest.mark.parametrize("coefficient,quantity,time,scale", [
    ("1", "µmol", "min", 1000000), ("2", "μmol", "min", 2000000),
    ("0.125", "umol", "second", 7500000), ("1.25e-3", "nmol", "minute", 1.25),
    ("3", "pmol", "s", 180), ("+2", "µmol", "min", 2000000),
])
def test_source_coefficients_quantity_and_time_scales_are_exact(coefficient, quantity, time, scale):
    fix = fixture(coefficient=coefficient, quantity=quantity, time=time, rate="0.1")
    unit = read(fix)
    assert unit["multiplier"] == scale
    assert convert_defined_source_number(fix["main"], unit) == float(Fraction("0.1") * Fraction(str(scale)))


def test_same_U_symbol_keeps_a_source_backed_factor_two_and_endpoint_identity():
    clause = "2 µmol ferrocenium per min"
    fix = fixture(entity="ferrocenium", coefficient="2", clause=clause,
        bridge="One unit was defined as the reduction of " + clause + ".")
    unit = read(fix)
    assert unit["multiplier"] == 2000000
    assert convert_defined_source_number(fix["main"], unit) == 14000000


def test_unicode_entity_equivalence_does_not_create_synonyms():
    unit = read(fixture(entity="H2", endpoint_entity="H₂"))
    assert unit["definition"]["endpoint_entity"]["quote"] == "H₂"
    assert unit["definition"]["definition_entity"]["quote"] == "H2"
    failure("defined_unit_entity_mismatch", read, fixture(entity="NADH", endpoint_entity="NADPH"))


def test_second_real_coordinated_clause_is_distinct_from_other_endpoints():
    clause = "1 µmol of H2 formed per min"
    bridge = "One unit was equivalent to 1 µmol of NADH oxidized per min, 1 µmol of TTC reduced per min, or " + clause + "."
    fix = fixture(entity="H2", clause=clause, bridge=bridge, rate="<0.01")
    unit = read(fix)
    assert fix["main"]["relation"] == "lt"
    assert convert_defined_source_number(fix["main"], unit) == 10000


def test_number_quote_can_be_the_bridge_when_its_actual_token_is_in_selected_clause():
    fix = fixture()
    amount = fix["selection"]["definition"]["amount"]
    bridge = fix["selection"]["definition"]["bridge"]
    amount["witness"] = deepcopy(bridge)
    amount["number_start"] = bridge["quote"].index("1")
    amount["number_end"] = amount["number_start"] + 1
    assert read(fix)["multiplier"] == 1000000


@pytest.mark.parametrize("header", ["U/mg", "U / mg", "U  /  mg"])
def test_unit_header_allows_only_complete_whitespace_aliases(header):
    assert read(fixture(header=header))["raw_unit"] == header


@pytest.mark.parametrize("header", ["mU/mg", "U/ml", "u/mg", "U/g", "U", "U/mg/min"])
def test_other_units_do_not_acquire_a_universal_U_conversion(header):
    failure("defined_unit_rate_unit_unsupported", read, fixture(header=header))


@pytest.mark.parametrize("header,quote", [("mU/mg", "U/mg"), ("U/mg/min", "U/mg"),
    ("U/mgx", "U/mg"), ("U/mg per min", "U/mg")])
def test_clipping_a_unit_prefix_or_denominator_is_rejected(header, quote):
    fix = fixture(header=header)
    fix["selection"]["witness"] = fix["witness"](quote)
    failure("defined_unit_partial_rate_unit", read, fix)


def test_a_clipped_bridge_cannot_hide_a_newline_continuation():
    clause = "1 µmol of NADH oxidized per min"
    fix = fixture(bridge="One unit was equivalent to " + clause + "\n or 1 µmol of H2 formed per min.")
    fix["selection"]["definition"]["bridge"] = fix["witness"]("One unit was equivalent to " + clause)
    failure("defined_unit_bridge_boundary_required", read, fix)


def test_enriched_endpoint_is_revalidated_and_unknown_endpoint_cannot_define_U():
    fix = fixture()
    fix["endpoint"] = fix["sources"].witness(fix["endpoint"], "endpoint")
    assert read(fix)["multiplier"] == 1000000
    fix["endpoint"]["artifact_ref"] = OTHER_ARTIFACT
    failure("defined_unit_endpoint_mismatch", read, fix)
    fix["endpoint"] = None
    failure("defined_unit_endpoint_required", read, fix)


def test_same_endpoint_text_from_a_different_source_is_not_same_binding():
    fix = fixture()
    fix["endpoint"] = {**fix["endpoint"], "source_ref": OTHER}
    failure("defined_unit_endpoint_mismatch", read, fix)


@pytest.mark.parametrize("name", ["bridge", "clause", "amount_unit", "time_unit", "definition_entity"])
def test_nested_definition_parts_cannot_change_source_or_representation(name):
    fix = fixture()
    fix["selection"]["definition"][name]["representation"] = "text"
    failure("defined_unit_source_mismatch", read, fix)


def test_selected_amount_cannot_come_from_another_endpoint_clause():
    fix = fixture()
    quote = "1 µmol of TTC reduced per min"
    fix["selection"]["definition"]["amount"] = fix["number"]("1", quote)
    failure("defined_unit_containment_required", read, fix)


@pytest.mark.parametrize("field,quote", [("amount_unit", "µmol"), ("time_unit", "min"), ("definition_entity", "TTC")])
def test_selected_clause_parts_cannot_be_borrowed_from_the_next_clause(field, quote):
    fix = fixture()
    offset = fix["text"].encode().index(b"1 \xc2\xb5mol of TTC")
    fix["selection"]["definition"][field] = fix["witness"](quote, offset=offset)
    failure("defined_unit_containment_required", read, fix)


@pytest.mark.parametrize("field,quote", [("endpoint_entity", "NAD"), ("definition_entity", "NAD")])
def test_entity_substrings_are_not_endpoint_correspondence(field, quote):
    fix = fixture()
    offset = fix["selection"]["definition"]["clause"]["start"] if field == "definition_entity" else 0
    fix["selection"]["definition"][field] = fix["witness"](quote, offset=offset)
    failure("defined_unit_partial_entity", read, fix)


@pytest.mark.parametrize("bridge", ["Two units were equivalent to 1 µmol of NADH oxidized per min.",
    "One unit was not equivalent to 1 µmol of NADH oxidized per min.",
    "One unit is equivalent to 1 µmol of NADH oxidized per min."])
def test_unsupported_definition_relationships_are_explicit(bridge):
    failure("defined_unit_bridge_unsupported", read, fixture(bridge=bridge))


def test_a_short_bridge_cannot_drop_other_definition_clauses():
    fix = fixture()
    fix["selection"]["definition"]["bridge"] = fix["witness"]("One unit was equivalent to 1 µmol of NADH oxidized per min")
    failure("defined_unit_bridge_boundary_required", read, fix)


def test_a_bridge_cannot_capture_a_later_unrelated_definition():
    clause = "1 µmol of NADH oxidized per min"
    bridge = "One unit was equivalent to 1 µmol of TTC reduced per min. A later condition used " + clause + "."
    failure("defined_unit_bridge_association_required", read, fixture(bridge=bridge))


@pytest.mark.parametrize("coefficient", ["0", "-1"])
def test_unit_definition_requires_positive_source_quantity(coefficient):
    failure("defined_unit_positive_amount_required", read, fixture(coefficient=coefficient))


@pytest.mark.parametrize("quantity,time", [("mmol", "min"), ("mol", "min"), ("µM", "min"), ("µmol", "hour")])
def test_unknown_quantity_or_time_basis_is_not_rescaled(quantity, time):
    failure("defined_unit_quantity_time_unsupported", read, fixture(quantity=quantity, time=time))


@pytest.mark.parametrize("coefficient,code", [("1e308", "numerical_model_range"),
    ("1e-4000", "numerical_model_range"), ("<1", "plain_source_point_required"),
    ("about 1", "literal_source_number_required")])
def test_unrepresentable_or_qualified_coefficients_cannot_be_exact_scales(coefficient, code):
    fix = fixture(coefficient=coefficient)
    if coefficient == "<1":
        fix["selection"]["definition"]["amount"] = fix["number"]("1", fix["selection"]["definition"]["clause"]["quote"])
    failure(code, read, fix)


@pytest.mark.parametrize("field,value", [("multiplier", True), ("multiplier", 1),
    ("canonical_unit", "uM/min"), ("raw_unit", "nmol/min/mg")])
def test_conversion_rejects_changed_scale_or_repeated_unit_metadata(field, value):
    fix = fixture()
    unit = read(fix)
    unit[field] = value
    code = "defined_unit_conversion_mismatch" if field == "multiplier" and value == 1 and type(value) is int else "defined_unit_record_mismatch"
    failure(code, convert_defined_source_number, fix["main"], unit)


def test_conversion_rejects_altered_native_or_coefficient_value():
    fix = fixture()
    unit = read(fix)
    changed = deepcopy(fix["main"])
    changed["value"] = 700
    failure("defined_unit_number_record_mismatch", convert_defined_source_number, changed, unit)
    unit["definition"]["amount"]["value"] = 2
    failure("defined_unit_number_record_mismatch", convert_defined_source_number, fix["main"], unit)


def test_conversion_preserves_point_or_limit_metadata_and_input_immutability():
    fix = fixture(rate="<0.01")
    unit = read(fix)
    before = deepcopy((fix["main"], unit))
    assert convert_defined_source_number(fix["main"], unit) == 10000
    assert (fix["main"], unit) == before
    assert fix["main"]["relation"] == "lt"


@pytest.mark.parametrize("rate", ["1e308", "5e-324"])
def test_canonical_conversion_range_failure_is_explicit(rate):
    fix = fixture(rate=rate, coefficient="1e-320" if rate == "5e-324" else "1")
    unit = read(fix)
    failure("numerical_model_range", convert_defined_source_number, fix["main"], unit)


@pytest.mark.parametrize("suffix", ["U/mg", "µmol/min/mg", "µmol min-1 mg-1", "(SD)", ""])
def test_absolute_spread_checks_definition_or_matching_native_scale(suffix):
    fix = fixture(spread="SD 58 " + suffix)
    unit = read(fix)
    number = read_source_number(fix["number"]("58", "SD 58 " + suffix), sources=fix["sources"], role="spread")
    assert validate_defined_spread_unit(number, unit, sources=fix["sources"]) is None
    assert convert_defined_source_number(number, unit) == 58000000


@pytest.mark.parametrize("suffix,code", [("nmol/min/mg", "source_spread_unit_mismatch"),
    ("uM/min", "source_spread_unit_mismatch"), ("mmol/min/mg", "unsupported_explicit_spread_unit"),
    ("mU/mg", "defined_unit_spread_unit_unsupported"), ("U/ml", "defined_unit_spread_unit_unsupported"),
    ("U/mg/min", "defined_unit_partial_rate_unit"), ("U/mg per min", "defined_unit_partial_rate_unit")])
def test_spread_cannot_drop_a_changed_scale_dimension_or_U_definition(suffix, code):
    fix = fixture(spread="SD 58 " + suffix)
    unit = read(fix)
    number = read_source_number(fix["number"]("58", "SD 58 " + suffix), sources=fix["sources"], role="spread")
    failure(code, validate_defined_spread_unit, number, unit, sources=fix["sources"])


def test_plain_spread_unit_cannot_silently_ignore_explicit_Umg():
    fix = fixture()
    unit = read_source_rate_unit(fix["witness"]("nmol/min/mg"), sources=fix["sources"])
    number = read_source_number(fix["number"]("58", "SD 58 U/mg"), sources=fix["sources"], role="spread")
    failure("defined_unit_spread_definition_required", validate_defined_spread_unit, number, unit, sources=fix["sources"])


def test_independently_plain_spread_scale_remains_supported():
    fix = fixture(spread="SD 58 pmol/min/mg")
    unit = read_source_rate_unit(fix["witness"]("pmol/min/mg"), sources=fix["sources"])
    number = read_source_number(fix["number"]("58", "SD 58 pmol/min/mg"), sources=fix["sources"], role="spread")
    assert validate_defined_spread_unit(number, unit, sources=fix["sources"]) is None


@pytest.mark.parametrize("suffix", ["%", "percent", "per cent", "(CV)"])
def test_relative_spread_never_becomes_an_absolute_U_spread(suffix):
    fix = fixture(spread="SD 58 " + suffix)
    read(fix)
    failure("relative_spread_unit_unsupported", read_source_number,
        fix["number"]("58", "SD 58 " + suffix), sources=fix["sources"], role="spread")


def test_spread_revalidates_source_record_without_mutation():
    fix = fixture()
    unit = read(fix)
    number = read_source_number(fix["number"]("58", "SD 58 U/mg"), sources=fix["sources"], role="spread")
    before = deepcopy((number, unit))
    validate_defined_spread_unit(number, unit, sources=fix["sources"])
    assert (number, unit) == before
    number["value"] = 59
    failure("source_number_record_mismatch", validate_defined_spread_unit, number, unit, sources=fix["sources"])


def test_schema_objects_are_independent_and_do_not_accept_supplied_numbers():
    fix = fixture()
    schema = defined_rate_unit_schema()
    schema["properties"]["definition"] = {}
    assert defined_rate_unit_schema()["properties"]["definition"]["additionalProperties"] is False
    changed = deepcopy(fix["selection"])
    changed["definition"]["amount"] = 1
    with pytest.raises(ContractError):
        validate_schema(changed, defined_rate_unit_schema())
    schema = parsed_defined_rate_unit_schema()
    schema["properties"]["definition"] = {}
    assert parsed_defined_rate_unit_schema()["properties"]["definition"]["additionalProperties"] is False


@pytest.mark.parametrize("change", [lambda unit: unit.update(definition=None),
    lambda unit: unit.update(definition={}), lambda unit: unit.update(extra=1)])
def test_malformed_defined_spread_records_fail_as_contract_errors(change):
    fix = fixture()
    unit = read(fix)
    change(unit)
    number = read_source_number(fix["number"]("58", "SD 58 U/mg"), sources=fix["sources"], role="spread")
    failure("closed_fields_required", validate_defined_spread_unit, number, unit, sources=fix["sources"])
