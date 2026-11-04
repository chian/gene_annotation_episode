"""Synthetic native source selections; no paper acquisition or model inference."""
from copy import deepcopy
import hashlib

import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError, validate_rate_extraction
from gene_annotation_episode.literature_rate_calculations import populate_rate_contrast
from gene_annotation_episode.literature_rate_native_inputs import read_rate_source_inputs, _number
from gene_annotation_episode.literature_assay_inputs import _Sources


def witness(raw, source, text, occurrence=0, *, representation="original"):
    start = -1
    for _ in range(occurrence + 1):
        start = raw.index(text.encode(), start + 1)
    return {"source_ref": source, "representation": representation,
            "start": start, "end": start + len(text.encode()), "quote": text}


def number(raw, source, line, token):
    selected = witness(raw, source, line)
    start = line.index(token)
    return {"witness": selected, "number_start": start, "number_end": start + len(token)}


def synthetic_case(*, source="source_native", reference="12", test="3", reference_unit="nmol/min/mg",
                   test_unit="nmol/min/mg", uncertainty=False, independent=False):
    lines = ["Synthetic experiment A compares different constructs.",
        "The same endpoint and normalization are compared; other changes remain unisolated.",
        "Reference subject enzyme Alpha; construct WT; preparation prepR; condition buffered control.",
        "Test subject enzyme Beta; construct variant; preparation prepT; condition buffered intervention.",
        "Endpoint NADH oxidation; normalization per mg preparation.",
        f"Reference rate {reference} {reference_unit}.", f"Test rate {test} {test_unit}.",
        "Reference observation obsR; test observation obsT.",
        "Model assumption: independent normal groups."]
    if uncertainty:
        lines += [f"Reference SD 2 {reference_unit}; reference count 5.",
                  f"Test SD 1 {test_unit}; test count 5."]
    raw = ("\n".join(lines) + "\n").encode()
    w = lambda text, occurrence=0: witness(raw, source, text, occurrence)
    relation = lambda value: {"value": value, "witnesses": [] if value == "unknown" else [w(lines[1])]}
    args = {"input_mode": "native_source_spans", "source_ref": source, "source_kind": "synthetic_fixture",
        "experiment": w("experiment A"), "comparison": {"subject_relation": relation("different"),
            "endpoint_relation": relation("same"), "normalization_relation": relation("same"),
            "intended_change": w("different constructs")},
        "dependence": {"value": "independent" if independent else "unknown",
            "witnesses": [w("independent normal groups")] if independent else []},
        "observation_model": {"value": "independent_normal_groups" if independent else "none",
            "witnesses": [w("independent normal groups")] if independent else []}, "arms": {}}
    for role, subject, construct, prep, condition, value, unit in [
            ("reference", "enzyme Alpha", "WT", "prepR", "buffered control", reference, reference_unit),
            ("test", "enzyme Beta", "variant", "prepT", "buffered intervention", test, test_unit)]:
        line = f"{role.title()} rate {value} {unit}."
        magnitude = "2" if role == "reference" else "1"
        spread_line = f"{role.title()} SD {magnitude} {unit}; {role} count 5."
        args["arms"][role] = {"subject": w(subject), "construct": w(construct), "preparation": w(prep),
            "experiment": w("experiment A"), "label": w(role.title() + " subject"),
            "condition": w(condition), "endpoint": w("NADH oxidation"),
            "normalization": w("per mg preparation"), "measurement_identity": None,
            "rate": {"number": number(raw, source, line, value),
                     "unit": w(line)["quote"]},
            "uncertainty": {"kind": "sd" if uncertainty else "unreported",
                "magnitude": number(raw, source, spread_line, magnitude) if uncertainty else None,
                "unit": None, "kind_witnesses": [w(role.title() + " SD")] if uncertainty else [],
                "count": number(raw, source, f"{role} count 5", "5") if uncertainty else None,
                "sampling_basis": {"value": "unspecified", "witnesses": []}}}
        # Bind the complete printed unit at its physical occurrence in this arm.
        line_w = w(line)
        start = line_w["start"] + len(line[:line.index(unit)].encode())
        args["arms"][role]["rate"]["unit"] = {"source_ref": source, "representation": "original",
            "start": start, "end": start + len(unit.encode()), "quote": unit}
    return raw, args


def read_case(raw, args, *, text_artifact=None):
    artifact = "artifact_" + hashlib.sha256(raw).hexdigest()
    def read_source(source, representation):
        assert source == args["source_ref"]
        return {"artifact_ref": text_artifact if representation == "text" and text_artifact else artifact,
                "content": raw}
    return read_rate_source_inputs(args, read_source=read_source)


def calculate(extraction):
    rows = {row["arm"]: row for row in extraction["rows"]}
    model = extraction["native_context"]["model"]
    return populate_rate_contrast(extraction, reference_arm="reference", test_arm="test",
        reference_condition=rows.get("reference", {}).get("condition"),
        test_condition=rows.get("test", {}).get("condition"),
        dependence=model["dependence"]["value"], observation_model=model["observation_model"]["value"])


def defined_case(reference_scale="2", test_scale="1"):
    raw, args = synthetic_case(reference="7", test="0.1", reference_unit="U/mg", test_unit="U/mg")
    clauses = [f"One unit was defined as {scale} umol NADH per min." for scale in (reference_scale, test_scale)]
    raw += ("\n".join(clauses) + "\n").encode()
    for index, (role, scale, bridge) in enumerate(zip(("reference", "test"), (reference_scale, test_scale), clauses)):
        bridge_w = witness(raw, args["source_ref"], bridge, index if clauses[0] == clauses[1] else 0)
        clause = f"{scale} umol NADH per min"
        def within(text):
            left = bridge_w["quote"].index(text)
            start = bridge_w["start"] + len(bridge_w["quote"][:left].encode())
            return {"source_ref": args["source_ref"], "representation": "original",
                    "start": start, "end": start + len(text.encode()), "quote": text}
        endpoint = args["arms"][role]["endpoint"]
        entity = {**endpoint, "end": endpoint["start"] + len("NADH"), "quote": "NADH"}
        args["arms"][role]["rate"]["unit"] = {"kind": "source_defined_rate_unit",
            "witness": args["arms"][role]["rate"]["unit"], "definition": {"bridge": bridge_w,
                "clause": within(clause), "amount": {"witness": within(clause), "number_start": 0, "number_end": len(scale)},
                "amount_unit": within("umol"), "time_unit": within("min"),
                "endpoint": endpoint, "endpoint_entity": entity, "definition_entity": within("NADH")}}
    return raw, args


def test_different_constructs_have_native_provenance_and_the_same_existing_rate_cells():
    raw, args = synthetic_case()
    extracted = read_case(raw, args)
    assert validate_rate_extraction(extracted) == extracted
    assert extracted["subject"] is None
    assert all("row_number" not in row["source"] for row in extracted["rows"])
    assert [row["source"]["meanings"]["construct"]["quote"] for row in extracted["rows"]] == ["WT", "variant"]
    cells = calculate(extracted)["cells"]
    for name, value in [("reference_rate", .012), ("test_rate", .003), ("rate_difference", .009),
                        ("retained_fraction", .25), ("fractional_decrease", .75)]:
        assert cells[name]["value"] == pytest.approx(value)
    assert cells["difference_se"]["value"] is None
    assert cells["source_signed_index"]["value"] is None
    assert cells["reference_rate"]["input_rows"][0]["start"] < cells["reference_rate"]["input_rows"][0]["end"]


def test_source_supported_model_can_have_unknown_physical_ids_without_inventing_biological_replication():
    raw, args = synthetic_case(uncertainty=True, independent=True)
    extracted = read_case(raw, args)
    assert all(row["source"]["measurement_identity"] is None for row in extracted["rows"])
    assert all(row["uncertainty"]["sampling_basis"] == "unspecified" for row in extracted["rows"])
    cells = calculate(extracted)["cells"]
    assert cells["difference_se"]["value"] == pytest.approx(.001)
    assert cells["signed_profile_log_ratio"]["value"] > 0
    assert cells["source_signed_index"]["origin"] == "proposed"


@pytest.mark.parametrize("which", ["subject", "construct", "preparation", "condition", "experiment"])
def test_missing_context_is_retained_without_inventing_a_shared_subject_or_condition(which):
    raw, args = synthetic_case()
    args["arms"]["test"][which] = None
    extracted = read_case(raw, args)
    assert extracted["rows"][1]["source"]["meanings"][which] is None
    assert calculate(extracted)["cells"]["rate_difference"]["value"] == pytest.approx(.009)


@pytest.mark.parametrize("field", ["endpoint", "normalization"])
@pytest.mark.parametrize("relation", ["unknown", "different"])
def test_unestablished_common_endpoint_or_basis_keeps_individual_values(field, relation):
    raw, args = synthetic_case()
    args["comparison"][field + "_relation"]["value"] = relation
    if relation == "unknown":
        args["comparison"][field + "_relation"]["witnesses"] = []
    cells = calculate(read_case(raw, args))["cells"]
    assert cells["reference_rate"]["value"] == pytest.approx(.012)
    assert cells["test_rate"]["value"] == pytest.approx(.003)
    assert cells["rate_difference"]["value"] is None
    assert cells["rate_difference"]["unavailable_reason"] == f"source_{field}_relationship_{relation}"


@pytest.mark.parametrize("factor, expected_test, ratio", [("1", .1, 1/140), ("2", .2, 1/70)])
def test_endpoint_defined_units_have_their_own_exact_source_scales(factor, expected_test, ratio):
    raw, args = defined_case(test_scale=factor)
    extracted = read_case(raw, args)
    assert validate_rate_extraction(extracted) == extracted
    cells = calculate(extracted)["cells"]
    assert cells["reference_rate"]["value"] == 14
    assert cells["test_rate"]["value"] == expected_test
    assert cells["rate_difference"]["value"] == pytest.approx(14 - expected_test)
    assert cells["retained_fraction"]["value"] == pytest.approx(ratio)
    assert cells["reference_rate"]["unit"] == "umol/min/mg"


def test_defined_unit_endpoint_cannot_be_substituted_or_missing():
    raw, args = defined_case()
    args["arms"]["reference"]["endpoint"] = args["arms"]["reference"]["condition"]
    with pytest.raises(ExperimentalContractError, match="defined_unit_endpoint_mismatch"):
        read_case(raw, args)


@pytest.mark.parametrize("unit", ["U/mg", "mU/mg", "bananas/min"])
def test_unsupported_or_undefined_units_are_explicit_partial_inputs(unit):
    raw, args = synthetic_case(reference_unit=unit)
    extracted = read_case(raw, args)
    assert extracted["rows"][0]["source"]["number"]["value"] == 12
    assert extracted["rows"][0]["source"]["unit"]["raw_unit"] == unit
    cells = calculate(extracted)["cells"]
    assert cells["reference_rate"]["value"] is None
    assert cells["test_rate"]["value"] == pytest.approx(.003)
    assert cells["rate_difference"]["value"] is None


def test_incompatible_dimensions_keep_the_two_native_values_with_their_own_units():
    raw, args = synthetic_case(reference_unit="uM/min")
    cells = calculate(read_case(raw, args))["cells"]
    assert cells["reference_rate"]["value"] == 12
    assert cells["reference_rate"]["unit"] == "uM/min"
    assert cells["test_rate"]["unit"] == "umol/min/mg"
    assert cells["rate_difference"]["value"] is None
    assert cells["rate_difference"]["unavailable_reason"] == "incompatible_rate_dimensions"


@pytest.mark.parametrize("qualifier, relation", [("< ", "lt"), (">= ", "ge"),
    ("< approximately ", "lt"), ("greater than about ", "gt"), ("more than ", "gt"),
    ("about > ", "gt"), ("roughly < ", "lt")])
def test_qualifiers_outside_a_numeric_only_witness_remain_limits(qualifier, relation):
    raw, args = synthetic_case(reference=qualifier + "12")
    selected = args["arms"]["reference"]["rate"]["number"]
    selected.update(witness=witness(raw, args["source_ref"], "12"), number_start=0, number_end=2)
    extracted = read_case(raw, args)
    assert extracted["rows"][0]["bound"] == relation
    assert extracted["rows"][0]["source"]["number"]["value"] == 12
    assert calculate(extracted)["cells"]["reference_rate"]["unavailable_reason"] == "censored_measurement"


def test_roughly_does_not_silently_become_a_precise_point():
    raw, args = synthetic_case(reference="roughly 12")
    args["arms"]["reference"]["rate"]["number"] = {"witness": witness(raw, args["source_ref"], "12"),
        "number_start": 0, "number_end": 2}
    cells = calculate(read_case(raw, args))["cells"]
    assert cells["reference_rate"]["value"] == pytest.approx(.012)
    assert cells["reference_rate"]["approximate"] is True


@pytest.mark.parametrize("role, qualifier", [("magnitude", "roughly "), ("count", "more than ")])
def test_qualified_spread_or_count_is_not_an_exact_operand(role, qualifier):
    raw, args = synthetic_case(uncertainty=True, independent=True)
    text = "Reference SD 2" if role == "magnitude" else "reference count 5"
    token = "2" if role == "magnitude" else "5"
    replacement = text[:-1] + qualifier + token
    # Rebuild all witnesses after changing the synthetic bytes so no stale
    # offset, rather than the qualifier guard, supplies the expected failure.
    delta = len(qualifier.encode())
    insertion = raw.index(text.encode()) + len(text.encode()) - 1
    raw = raw[:insertion] + qualifier.encode() + raw[insertion:]
    def move(value):
        if isinstance(value, dict):
            if set(value) == {"source_ref", "representation", "start", "end", "quote"}:
                if value["start"] >= insertion:
                    value["start"] += delta;value["end"] += delta
                elif value["end"] > insertion:
                    value["end"] += delta
                    value["quote"] = raw[value["start"]:value["end"]].decode()
            else:
                for child in value.values():move(child)
        elif isinstance(value, list):
            for child in value:move(child)
    move(args)
    target = args["arms"]["reference"]["uncertainty"][role]
    target["witness"] = witness(raw, args["source_ref"], replacement)
    target["number_start"] = len(replacement) - 1;target["number_end"] = len(replacement)
    with pytest.raises(ExperimentalContractError, match="plain_source_point_required"):
        read_case(raw, args)


@pytest.mark.parametrize("expression, token, error", [("about 12 or less", "12", "postfix_source_bound"),
    ("12 ± about 0.2", "0.2", "uncertainty_is_not_rate_point"),
    ("about 12 to 15", "12", "interval_source_number"),
    ("not greater than about 12", "12", "negated_source_comparator")])
def test_approximation_fallback_does_not_erase_other_scientific_qualifiers(expression, token, error):
    raw, args = synthetic_case(reference=expression)
    args["arms"]["reference"]["rate"]["number"] = {"witness": witness(raw, args["source_ref"], token),
        "number_start": 0, "number_end": len(token)}
    with pytest.raises(ExperimentalContractError, match=error):
        read_case(raw, args)


def test_approximate_mean_does_not_label_its_independently_reported_sem_as_approximate():
    raw, args = synthetic_case(reference="about 12", uncertainty=True, independent=True)
    args["arms"]["reference"]["rate"]["number"] = number(raw, args["source_ref"], "Reference rate about 12 nmol/min/mg.", "12")
    cells = calculate(read_case(raw, args))["cells"]
    assert cells["reference_rate"]["value"] == pytest.approx(.012)
    assert cells["reference_rate"]["approximate"] and cells["rate_difference"]["approximate"]
    assert cells["signed_profile_log_ratio"]["approximate"]
    assert not cells["test_rate"]["approximate"]
    assert not cells["reference_mean_se"]["approximate"]
    assert not cells["difference_se"]["approximate"]


def test_signed_finite_rates_are_not_clipped():
    raw, args = synthetic_case(reference="-12")
    cells = calculate(read_case(raw, args))["cells"]
    assert cells["reference_rate"]["value"] == pytest.approx(-.012)
    assert cells["retained_fraction"]["value"] == -.25


@pytest.mark.parametrize("same_numeric_location", [False, True])
def test_same_actual_bytes_in_original_and_text_cannot_manufacture_independent_observations(same_numeric_location):
    raw, args = synthetic_case(uncertainty=True, independent=True)
    if same_numeric_location:
        args["arms"]["test"]["rate"] = deepcopy(args["arms"]["reference"]["rate"])
        args["arms"]["test"]["rate"]["number"]["witness"]["representation"] = "text"
    else:
        first = witness(raw, args["source_ref"], "obsR")
        args["arms"]["reference"]["measurement_identity"] = first
        args["arms"]["test"]["measurement_identity"] = {**first, "representation": "text"}
    cells = calculate(read_case(raw, args))["cells"]
    assert cells["reference_rate"]["value"] is not None and cells["test_rate"]["value"] is not None
    assert cells["difference_se"]["value"] is None
    assert cells["difference_se"]["unavailable_reason"] == "reused_source_observation"


def test_unrelated_source_provenance_is_not_merged_just_because_artifact_bytes_coincide():
    raw, args = synthetic_case(uncertainty=True, independent=True)
    args["arms"]["test"]["rate"]["number"] = deepcopy(args["arms"]["reference"]["rate"]["number"])
    args["arms"]["test"]["rate"]["number"]["witness"]["source_ref"] = "source_unrelated"
    artifact = "artifact_" + hashlib.sha256(raw).hexdigest()
    extracted = read_rate_source_inputs(args, read_source=lambda _source, _representation: {
        "artifact_ref": artifact, "content": raw})
    cells = calculate(extracted)["cells"]
    assert cells["rate_difference"]["value"] == 0
    assert cells["difference_se"]["value"] == pytest.approx(.001)


def test_shortening_a_unit_cannot_remove_its_actual_mass_denominator():
    raw, args = synthetic_case()
    unit = args["arms"]["reference"]["rate"]["unit"]
    unit.update(end=unit["start"] + len("nmol/min"), quote="nmol/min")
    with pytest.raises(ExperimentalContractError, match="partial_source_rate_unit"):
        read_case(raw, args)


def test_shortening_a_number_cannot_remove_a_digit():
    raw, args = synthetic_case(reference="312")
    spec = args["arms"]["reference"]["rate"]["number"]
    spec["number_start"] += 1
    with pytest.raises(ExperimentalContractError, match="partial_source_numeric_token"):
        read_case(raw, args)


def test_native_saved_contract_rejects_modified_numeric_or_location_records():
    raw, args = synthetic_case()
    extracted = read_case(raw, args)
    for field in ("value", "location"):
        changed = deepcopy(extracted)
        if field == "value":
            changed["rows"][0]["value"] = 99
        else:
            changed["rows"][0]["source"]["location"]["start"] += 1
        with pytest.raises(ExperimentalContractError):
            validate_rate_extraction(changed)


@pytest.mark.parametrize("expression,token", [("1/3", "1"), ("1/3", "3"),
    ("3 times 2", "3"), ("3 times 2", "2"), ("2 × 3", "3"),
    ("3 * 2", "3"), ("3 + 2", "3"), ("3^2", "3")])
@pytest.mark.parametrize("role", ["rate", "spread", "condition"])
def test_a_narrow_numeric_witness_cannot_clip_a_fraction_or_arithmetic_expression(expression, token, role):
    text = "Synthetic reported quantity " + expression + " nmol/min/mg."
    raw = text.encode()
    selected = witness(raw, "source_synthetic", token)
    sources = _Sources(lambda *_: {"artifact_ref": "artifact_synthetic", "content": raw})
    with pytest.raises(ExperimentalContractError, match="source_arithmetic_expression_unsupported"):
        _number({"witness": selected, "number_start": 0, "number_end": len(token)}, sources, role)


def test_unit_denominator_is_not_a_numeric_fraction():
    raw = b"Synthetic reported quantity 3/min."
    selected = witness(raw, "source_synthetic", "3")
    sources = _Sources(lambda *_: {"artifact_ref": "artifact_synthetic", "content": raw})
    result = _number({"witness": selected, "number_start": 0, "number_end": 1}, sources, "rate")
    assert result["value"] == 3 and result["relation"] == "point"


@pytest.mark.parametrize("phrase,token", [("Relative retained signal 3%.", "3"),
    ("Retained fraction 0.3.", "0.3")])
def test_a_relative_signal_cannot_borrow_an_unrelated_dimensional_rate_unit(phrase, token):
    raw, args = synthetic_case()
    start = len(raw) + phrase.index(token)
    raw += phrase.encode() + b"\n"
    args["arms"]["test"]["rate"]["number"] = {"witness": {"source_ref": args["source_ref"],
        "representation": "original", "start": start, "end": start + len(token.encode()), "quote": token},
        "number_start": 0, "number_end": len(token)}
    with pytest.raises(ExperimentalContractError, match="source_number_unit_role_mismatch"):
        read_case(raw, args)


@pytest.mark.parametrize("unit", ["nmol/min/mg", "µM", "s", "mg"])
def test_an_exact_count_cannot_be_an_explicitly_dimensioned_quantity(unit):
    raw, args = synthetic_case(uncertainty=True, independent=True)
    phrase = "Other reported quantity 12 " + unit + "."
    start = len(raw) + phrase.index("12")
    raw += phrase.encode() + b"\n"
    args["arms"]["reference"]["uncertainty"]["count"] = {"witness": {
        "source_ref": args["source_ref"], "representation": "original", "start": start,
        "end": start + 2, "quote": "12"}, "number_start": 0, "number_end": 2}
    with pytest.raises(ExperimentalContractError, match="source_number_unit_role_mismatch"):
        read_case(raw, args)


@pytest.mark.parametrize("word", ["samples", "measurements", "preparations"])
def test_ordinary_count_words_are_not_mistaken_for_physical_units(word):
    raw, args = synthetic_case(uncertainty=True, independent=True)
    phrase = "There were 5 " + word + "."
    start = len(raw) + phrase.index("5")
    raw += phrase.encode() + b"\n"
    args["arms"]["reference"]["uncertainty"]["count"] = {"witness": {
        "source_ref": args["source_ref"], "representation": "original", "start": start,
        "end": start + 1, "quote": "5"}, "number_start": 0, "number_end": 1}
    assert read_case(raw, args)["rows"][0]["uncertainty"]["count"] == 5


def test_native_table_cells_keep_unit_in_header_and_do_not_join_unrelated_neighbours():
    raw, args = synthetic_case(uncertainty=True, independent=True)
    table = ("<table><tr><th>Rate (nmol/min/mg)</th><th>Count</th><th>Other unit</th><th>Other fraction</th></tr>"
        "<tr><td>12</td><td>5</td><td>µM</td><td>3%</td></tr>"
        "<tr><td>3</td><td>5</td><td>s</td><td>4%</td></tr></table>")
    offset = len(raw)
    raw += table.encode()
    unit = witness(raw, args["source_ref"], "nmol/min/mg", raw[:offset].count(b"nmol/min/mg"))
    for role, row, token in [("reference", "<tr><td>12</td><td>5</td>", "12"),
                              ("test", "<tr><td>3</td><td>5</td>", "3")]:
        start = offset + len(table[:table.index(row) + len("<tr><td>")].encode())
        selected = {"source_ref": args["source_ref"], "representation": "original",
            "start": start, "end": start + len(token), "quote": token}
        count_start = start + len(token) + len("</td><td>")
        args["arms"][role]["rate"] = {"number": {"witness": selected, "number_start": 0, "number_end": len(token)}, "unit": unit}
        args["arms"][role]["uncertainty"]["count"] = {"witness": {**selected,
            "start": count_start, "end": count_start + 1, "quote": "5"}, "number_start": 0, "number_end": 1}
    extracted = read_case(raw, args)
    assert [row["uncertainty"]["count"] for row in extracted["rows"]] == [5, 5]
    assert calculate(extracted)["cells"]["rate_difference"]["value"] == pytest.approx(.009)


def test_inline_markup_keeps_the_real_outside_comparator_and_approximation():
    raw, args = synthetic_case()
    phrase = "<p><em>&lt; approximately </em><strong>12</strong> nmol/min/mg.</p>"
    start = len(raw) + phrase.index("12")
    raw += phrase.encode()
    args["arms"]["reference"]["rate"]["number"] = {"witness": {
        "source_ref": args["source_ref"], "representation": "original", "start": start,
        "end": start + 2, "quote": "12"}, "number_start": 0, "number_end": 2}
    extracted = read_case(raw, args)
    assert extracted["rows"][0]["bound"] == "lt" and extracted["rows"][0]["approximate"]


def test_standalone_defined_unit_in_a_table_header_preserves_its_actual_definition():
    raw, args = defined_case()
    phrase = "<table><tr><th>U/mg</th><th>Unrelated field</th></tr><tr><td>7</td><td>0.1</td></tr></table>"
    offset = len(raw)
    raw += phrase.encode()
    start = offset + phrase.index("U/mg")
    args["arms"]["reference"]["rate"]["unit"]["witness"] = {
        "source_ref": args["source_ref"], "representation": "original", "start": start,
        "end": start + len("U/mg"), "quote": "U/mg"}
    extracted = read_case(raw, args)
    assert calculate(extracted)["cells"]["reference_rate"]["value"] == 14


def test_native_defined_unit_adaptation_matches_the_existing_parsed_prose_record_exactly():
    from gene_annotation_episode.literature_partner_defined_units import read_defined_rate_unit
    raw, args = defined_case()
    extracted = read_case(raw, args)
    artifact = "artifact_" + hashlib.sha256(raw).hexdigest()
    for role, row in zip(("reference", "test"), extracted["rows"]):
        original = read_defined_rate_unit(args["arms"][role]["rate"]["unit"],
            sources=_Sources(lambda *_: {"artifact_ref": artifact, "content": raw}), endpoint=args["arms"][role]["endpoint"])
        assert row["source"]["unit"]["source_defined_unit"] == original


@pytest.mark.parametrize("phrase,token,role,error", [
    ("SD 2%", "2", "spread", "relative_spread_unit_unsupported"),
    ("CV 2", "2", "spread", "relative_spread_unit_unsupported"),
    ("Retained fraction 0.3", "0.3", "spread", "source_number_unit_role_mismatch"),
    ("Retained fraction 0.3", "0.3", "condition", "source_number_unit_role_mismatch"),
    ("not less than 3", "3", "rate", "negated_source_comparator_unsupported"),
    ("LOD: 3", "3", "rate", "untyped_limit_source_number"),
    ("range [3, 5]", "3", "rate", "interval_source_number_unsupported"),
    ("3 to 5", "3", "spread", "interval_source_number_unsupported"),
    ("SD 3", "3", "rate", "uncertainty_is_not_rate_point"),
    ("2 ± 3", "3", "rate", "uncertainty_is_not_rate_point"),
    ("3 or less", "3", "rate", "postfix_source_bound_unsupported"),
    ("3 or more", "3", "rate", "lower_bound_source_number_unsupported"),
    ("3,000", "3", "rate", "comma_source_number_unsupported"),
    ("-3", "3", "rate", "partial_source_numeric_token"),
    ("3e2", "3", "rate", "partial_source_numeric_token"),
    ("3e309", "3e309", "rate", "numerical_model_range"),
    ("3e-4000", "3e-4000", "rate", "numerical_model_range"),
    ("SD -3", "-3", "spread", "nonnegative_source_number_required"),
])
def test_field_aware_scalar_reader_preserves_the_original_semantic_and_numeric_guards(phrase, token, role, error):
    raw = ("<table><tr><td>Unrelated 7%</td><td>" + phrase + "</td><td>99 mg</td></tr></table>").encode()
    selected = witness(raw, "source_synthetic", token)
    sources = _Sources(lambda *_: {"artifact_ref": "artifact_synthetic", "content": raw})
    with pytest.raises(ExperimentalContractError, match=error):
        _number({"witness": selected, "number_start": 0, "number_end": len(token)}, sources, role)


def test_field_aware_scalar_reader_keeps_exact_plus_minus_spread_and_unicode_offsets():
    raw = "<p>Δ rate 12 ± <em>2</em> nmol/min/mg.</p><p>3%</p>".encode()
    selected = witness(raw, "source_synthetic", "2", 1)
    sources = _Sources(lambda *_: {"artifact_ref": "artifact_synthetic", "content": raw})
    value = _number({"witness": selected, "number_start": 0, "number_end": 1}, sources, "spread")
    assert value["value"] == 2 and value["relation"] == "point" and not value["approximate"]
    assert raw[selected["start"]:selected["end"]] == b"2"


@pytest.mark.parametrize("continuation", ["<em>/min</em>", "<span> per min</span>"])
def test_native_defined_unit_table_header_does_not_hide_inline_denominator(continuation):
    raw, args = defined_case()
    phrase = "<table><tr><th>U/mg" + continuation + "</th><th>Other</th></tr></table>"
    start = len(raw) + phrase.index("U/mg")
    raw += phrase.encode()
    args["arms"]["reference"]["rate"]["unit"]["witness"] = {
        "source_ref": args["source_ref"], "representation": "original", "start": start,
        "end": start + 4, "quote": "U/mg"}
    with pytest.raises(ExperimentalContractError, match="defined_unit_partial_rate_unit"):
        read_case(raw, args)


def test_native_defined_unit_field_context_keeps_bridge_word_boundary():
    raw, args = defined_case()
    bridge = args["arms"]["reference"]["rate"]["unit"]["definition"]["bridge"]
    start = len(raw) + len("<p>x")
    raw += ("<p>x" + bridge["quote"] + "</p>").encode()
    bridge.update(start=start, end=start + len(bridge["quote"].encode()))
    with pytest.raises(ExperimentalContractError, match="defined_unit_bridge_boundary_required"):
        read_case(raw, args)


@pytest.mark.parametrize("phrase", ["Retained fraction about 0.3", "Percent: approximately 0.3"])
def test_approximation_does_not_hide_an_explicit_relative_quantity_role(phrase):
    raw = ("<p>" + phrase + "</p>").encode()
    selected = witness(raw, "source_synthetic", "0.3")
    sources = _Sources(lambda *_: {"artifact_ref": "artifact_synthetic", "content": raw})
    with pytest.raises(ExperimentalContractError, match="source_number_unit_role_mismatch"):
        _number({"witness": selected, "number_start": 0, "number_end": 3}, sources, "rate")


def test_a_line_break_is_not_a_separate_field_that_can_hide_a_qualifier():
    raw = b"<p>Rate about <br/><strong>3</strong> nmol/min/mg.</p>"
    selected = witness(raw, "source_synthetic", "3")
    sources = _Sources(lambda *_: {"artifact_ref": "artifact_synthetic", "content": raw})
    value = _number({"witness": selected, "number_start": 0, "number_end": 1}, sources, "rate")
    assert value["value"] == 3 and value["approximate"] and value["relation"] == "point"


@pytest.mark.parametrize("qualifier,bound", [("< approximately ", "lt"), ("at most ", "le"),
    ("greater than ", "gt"), ("at least ", "ge")])
def test_native_individual_cells_keep_canonical_censoring_threshold_without_inventing_contrast_bounds(qualifier, bound):
    raw, args = synthetic_case(reference=qualifier + "12", test="> 3")
    for role, prefix in [("reference", qualifier), ("test", "> ")]:
        args["arms"][role]["rate"]["number"]["number_start"] += len(prefix)
    cells = calculate(read_case(raw, args))["cells"]
    assert cells["reference_rate"]["value"] is None
    assert cells["reference_rate"]["threshold"] == pytest.approx(.012)
    assert cells["reference_rate"]["bound"] == bound
    assert cells["reference_rate"]["approximate"] == ("approximately" in qualifier)
    assert cells["test_rate"]["threshold"] == pytest.approx(.003)
    assert cells["test_rate"]["bound"] == "gt"
    for name, cell in cells.items():
        if name not in ("reference_rate", "test_rate"):
            assert cell["threshold"] is None and cell["bound"] == "none"


def test_native_unknown_unit_preserves_the_censoring_relation_without_a_canonical_threshold():
    raw, args = synthetic_case(reference="< 12", reference_unit="unreported")
    args["arms"]["reference"]["rate"]["number"]["number_start"] += 2
    cells = calculate(read_case(raw, args))["cells"]
    assert cells["reference_rate"]["value"] is None
    assert cells["reference_rate"]["threshold"] is None and cells["reference_rate"]["bound"] == "lt"
    assert cells["reference_rate"]["unavailable_reason"] == "unsupported_source_rate_unit"
