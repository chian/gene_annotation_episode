"""Synthetic direct-source four-role inputs; no scientific-source truth claims."""
from copy import deepcopy
import hashlib
from io import BytesIO
import json

import jsonschema
from PIL import Image, ImageDraw
import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_binding_interaction_calculations import populate_binding_interaction
from gene_annotation_episode.literature_binding_interaction_inputs import (
    ID_FIELDS, ROLES, VERSION, binding_interaction_arguments_schema,
    read_binding_interaction_inputs,
)
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


def png(image):
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def fixture(expressions=("5", "40", "2", "4"), unit="nM", extra=""):
    text = ("Synthetic binding case. IC50 parameter; Hill Kd parameter. "
        "formA constructA protocolA; formB constructB protocolB; apo; "
        "ligand0 ligand1; tracerX; fluorescence; relative signal; bufferX. "
        "IC50definition; Hilldefinition; separately assayed; shared conditions. "
        "fitA0 fitA1 fitB0 fitB1. Unit " + unit + ". " + extra)
    raw = text.encode()
    def witness(quote, after=0):
        start = text.index(quote, after)
        return {"kind": "text", "source_ref": "methods", "representation": "original",
            "start": len(text[:start].encode()), "end": len(text[:start + len(quote)].encode()), "quote": quote}
    def enum(value, quote=None):
        return {"value": value, "witnesses": [] if quote is None else [witness(quote)]}
    def definition(label):
        return {"status": "unknown", "label": None, "witnesses": [], "canonical_witness": None} if label is None else {
            "status": "known", "label": label, "witnesses": [witness(label)], "canonical_witness": witness(label)}
    def text_literal(quote):
        return {"status": "exact", "candidates": [witness(quote)], "fragments": []}
    image = Image.new("RGB", (500, 200), "white")
    draw = ImageDraw.Draw(image)
    roles = {}
    for index, role in enumerate(ROLES):
        subject = "A" if index < 2 else "B"
        region = [200, 10 + index * 40, 400, 38 + index * 40]
        draw.text((205, 14 + index * 40), expressions[index], fill="black")
        iw = {"kind": "image", "image_id": "table", "region": region, "quote": expressions[index]}
        labels = {name: None for name in ID_FIELDS}
        labels.update(subject="form" + subject, construct="construct" + subject, state="apo",
            experiment="protocol" + subject, ligand="ligand" + str(index % 2), tracer="tracerX",
            readout="fluorescence", normalization="relative signal", conditions="bufferX",
            parameter_definition="IC50definition")
        roles[role] = {"parameter_kind": enum("ic50", "IC50 parameter"),
            "definitions": {name: definition(labels[name]) for name in ID_FIELDS},
            "physical_fit": {"canonical_witness": witness(("fitA0", "fitA1", "fitB0", "fitB1")[index]),
                "witnesses": [witness(("fitA0", "fitA1", "fitB0", "fitB1")[index])]},
            "measurement": {"image_id": "table", "cell_region": region,
                "expression": {"status": "exact", "candidates": [iw], "fragments": []}, "unit": text_literal(unit)},
            "uncertainty": {"statistic": enum("unreported", "Synthetic binding case"),
                "basis": enum("unknown"), "repetition_basis": enum("unspecified"), "interval": None,
                "confidence_level": None, "exact_count": None, "minimum_count": None}}
    arguments = {"version": VERSION, "source_ref": "methods", "source_kind": "synthetic_fixture",
        "images": [{"image_id": "table", "source_ref": "image", "original_source_ref": "image", "mapping": None}],
        "parameter_kind": enum("ic50", "IC50 parameter"), "comparison_scope": "reported_protocols", "roles": roles,
        "relationships": {name: {"status": "matched" if name == "common_conditions" else "supported",
            "witnesses": [witness("shared conditions" if name == "common_conditions" else "separately assayed")]}
            for name in ("within_reference_subject", "within_test_subject", "ligand_correspondence",
                "parameter_definition", "separate_assays", "common_conditions")}}
    sources = {"methods": raw, "image": png(image)}
    return arguments, sources, witness, enum, text_literal, image


def reader(sources, calls=None):
    def read(reference, representation):
        assert representation in ("original", "text")
        if calls is not None:
            calls.append((reference, representation))
        raw = sources[reference]
        if isinstance(raw, Exception):
            raise raw
        return {"artifact_ref": "artifact_" + hashlib.sha256(raw).hexdigest(), "content": raw}
    return read


def run(args, sources):
    return read_binding_interaction_inputs(args, read_source=reader(sources))


def calculate(result):
    return populate_binding_interaction(result["calculation_inputs"])


def test_actual_source_roles_units_mappings_and_native_contrast_are_preserved():
    args, sources, *_ = fixture()
    before = deepcopy(args)
    calls = []
    result = read_binding_interaction_inputs(args, read_source=reader(sources, calls))
    assert args == before and result == json.loads(json.dumps(result, allow_nan=False))
    assert result["calculation_input_status"] == "ready"
    assert result["source_refs"] == ["methods", "image"]
    assert calls.count(("methods", "original")) == 1 and calls.count(("image", "original")) == 1
    assert result["roles"][ROLES[0]]["measurement"]["canonical_measurement"]["value"] == 5
    assert result["roles"][ROLES[0]]["calculation_operand"]["origin"] == "synthetic"
    assert result["roles"][ROLES[0]]["definitions"]["preparation"]["canonical_id"] is None
    assert result["roles"][ROLES[0]]["measurement"]["source_cell_id"] != result["roles"][ROLES[0]]["physical_fit"]["physical_fit_id"]
    cells = calculate(result)["cells"]
    assert cells["reference_subject_ratio"]["value"] == 8
    assert cells["test_subject_ratio"]["value"] == 2
    assert cells["interaction_ratio"]["value"] == 4
    assert cells["signed_profile_log_ratio"]["value"] is None


def test_closed_schema_and_malformed_fields_reject_before_source_access():
    args, sources, *_ = fixture()
    schema = binding_interaction_arguments_schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(args, schema)
    args["covariance"] = [[1]]
    calls = []
    with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
        read_binding_interaction_inputs(args, read_source=reader(sources, calls))
    assert calls == []
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(args, schema)
    schema["properties"].clear()
    assert binding_interaction_arguments_schema()["properties"]


@pytest.mark.parametrize("status", ["unknown", "conflicting"])
def test_no_default_common_kind_but_all_raw_measurements_survive(status):
    args, sources, witness, *_ = fixture()
    args["parameter_kind"] = {"value": status, "witnesses": [] if status == "unknown" else [witness("IC50 parameter"), witness("Hill Kd parameter")]}
    result = run(args, sources)
    assert result["calculation_inputs"] is None
    assert result["calculation_input_status"] == "common_parameter_kind_" + status
    assert [result["roles"][r]["measurement"]["canonical_measurement"]["value"] for r in ROLES] == [5, 40, 2, 4]
    assert result["roles"][ROLES[0]]["parameter_kind"]["value"] == "ic50"


@pytest.mark.parametrize("name", ["construct", "state", "normalization"])
def test_unknown_context_does_not_require_fake_witness_or_discard_raw_points(name):
    args, sources, *_ = fixture()
    for role in ROLES[:2]:
        args["roles"][role]["definitions"][name] = {"status": "unknown", "label": None, "witnesses": [], "canonical_witness": None}
    result = run(args, sources)
    cells = calculate(result)["cells"]
    assert cells["parameter_rr"]["value"] == 5 and cells["parameter_rt"]["value"] == 40
    assert cells["reference_subject_ratio"]["reason"] == "canonical_" + name + "_unknown"
    assert cells["test_subject_ratio"]["value"] == 2


@pytest.mark.parametrize("unit", [None, "mg/mL", "~nM"])
def test_unknown_or_unsupported_unit_keeps_native_number_without_scale_one_canonical(unit):
    args, sources, *_ = fixture()
    selected = args["roles"][ROLES[0]]["measurement"]
    if unit is None:
        selected["unit"] = None
    else:
        selected["unit"] = {"status": "exact", "candidates": [{"kind": "image", "image_id": "table", "region": [0, 0, 40, 10], "quote": unit}], "fragments": []}
    result = run(args, sources)
    raw = result["roles"][ROLES[0]]["measurement"]
    assert raw["native_measurement"]["value"] == 5
    assert raw["canonical_measurement"] is None and result["roles"][ROLES[0]]["calculation_operand"] is None
    assert calculate(result)["cells"]["test_subject_ratio"]["value"] == 2


@pytest.mark.parametrize("unit,scale", [("nM", 1), ("uM", 1000), ("µM", 1000), ("mM", 1000000)])
def test_actual_supported_unit_converts_only_canonical_representation(unit, scale):
    args, sources, *_ = fixture(unit=unit)
    result = run(args, sources)
    measurement = result["roles"][ROLES[0]]["measurement"]
    assert measurement["native_measurement"]["value"] == 5
    assert measurement["canonical_measurement"]["value"] == 5 * scale
    assert calculate(result)["cells"]["interaction_ratio"]["value"] == 4


@pytest.mark.parametrize("state", ["ambiguous", "unreadable", "conflicting"])
def test_raw_candidate_states_remain_distinct_and_other_pair_survives(state):
    args, sources, *_ = fixture()
    expression = args["roles"][ROLES[1]]["measurement"]["expression"]
    old = deepcopy(expression["candidates"][0])
    expression.update(status=state, candidates=[] if state == "unreadable" else [old, {**old, "quote": "46"}],
        fragments=[{**old, "quote": "4?"}] if state == "unreadable" else [])
    result = run(args, sources)
    measurement = result["roles"][ROLES[1]]["measurement"]
    assert measurement["parse_status"] == state and measurement["canonical_measurement"] is None
    if state != "unreadable":
        assert [c["native"]["value"] for c in measurement["candidate_measurements"]] == [40, 46]
    assert calculate(result)["cells"]["test_subject_ratio"]["value"] == 2
    assert calculate(result)["cells"]["interaction_ratio"]["value"] is None


def test_literal_nd_keeps_its_meaning_separate_from_unreadable():
    args, sources, *_ = fixture(expressions=("5", "n.d.", "2", "4"))
    result = run(args, sources)
    role = result["roles"][ROLES[1]]
    assert role["measurement"]["parse_status"] == "reported_unavailable"
    assert role["measurement"]["expression"]["candidates"][0]["witness"]["quote"] == "n.d."
    assert role["calculation_operand"]["relation"] == "unreported"
    assert calculate(result)["cells"]["parameter_rt"]["value"] is None


def test_uncertainty_whole_unknown_and_known_sd_missing_magnitude_preserve_point_and_d():
    args, sources, _, enum, *_ = fixture(extra="reported SD")
    args["roles"][ROLES[0]]["uncertainty"] = None
    args["roles"][ROLES[1]]["uncertainty"]["statistic"] = enum("sd", "reported SD")
    result = run(args, sources)
    assert result["roles"][ROLES[0]]["calculation_operand"]["uncertainty"] is None
    assert result["roles"][ROLES[1]]["calculation_operand"]["uncertainty"]["statistic"] == "sd"
    assert result["roles"][ROLES[1]]["calculation_operand"]["reported_spread"] is None
    assert calculate(result)["cells"]["interaction_ratio"]["value"] == 4


@pytest.mark.parametrize("missing", ["level", "lower", "upper", "both", "interval"])
def test_partial_ci_keeps_statistic_actual_endpoints_and_missing_level(missing):
    args, sources, _, enum, literal, _ = fixture(extra="reported CI; lower 4.1; upper 6.2; confidence 95%")
    selected = args["roles"][ROLES[0]]["uncertainty"]
    selected["statistic"] = enum("confidence_interval", "reported CI")
    selected["interval"] = None if missing == "interval" else {
        "lower": None if missing in ("lower", "both") else literal("4.1"),
        "upper": None if missing in ("upper", "both") else literal("6.2"),
        "unit_relationship": enum("same_as_parameter", "reported CI"), "unit": None}
    selected["confidence_level"] = None if missing == "level" else literal("95%")
    result = run(args, sources)
    uncertainty = result["roles"][ROLES[0]]["calculation_operand"]["uncertainty"]
    assert uncertainty["statistic"] == "confidence_interval"
    assert uncertainty["confidence_level"] == (None if missing == "level" else .95)
    assert uncertainty["interval"] == (None if missing == "interval" else
        [None if missing in ("lower", "both") else 4.1, None if missing in ("upper", "both") else 6.2])
    assert calculate(result)["cells"]["interaction_ratio"]["value"] == 4


@pytest.mark.parametrize("purpose,token,expected", [
    ("exact_count", "3", 3), ("exact_count", ">=3", None), ("exact_count", "about 3", None),
    ("minimum_count", ">=3", 3), ("minimum_count", "<3", None), ("minimum_count", "about 3", None),
    ("minimum_count", ">3", None),
    ("exact_count", "three", None), ("exact_count", "3.0", None),
])
def test_count_qualifiers_and_unsupported_words_are_not_upgraded(purpose, token, expected):
    args, sources, _, _, literal, _ = fixture(extra="count " + token + "; repeats")
    args["roles"][ROLES[0]]["uncertainty"][purpose] = literal(token)
    result = run(args, sources)
    assert result["roles"][ROLES[0]]["calculation_operand"]["uncertainty"][purpose] == expected
    assert result["roles"][ROLES[0]]["uncertainty"][purpose]["literal"]["candidates"][0]["witness"]["quote"] == token


def test_qualification_outside_text_selector_is_preserved_for_count_and_ci_level():
    args, sources, witness, enum, _, _ = fixture(extra="count >=73; reported CI confidence about 95%")
    def exact(w):
        return {"status": "exact", "candidates": [w], "fragments": []}
    uncertainty = args["roles"][ROLES[0]]["uncertainty"]
    uncertainty["statistic"] = enum("confidence_interval", "reported CI")
    uncertainty["exact_count"] = exact(witness("73"))
    uncertainty["confidence_level"] = exact(witness("95%"))
    result = run(args, sources)
    canonical = result["roles"][ROLES[0]]["calculation_operand"]["uncertainty"]
    assert canonical["exact_count"] is None and canonical["confidence_level"] is None
    assert result["roles"][ROLES[0]]["uncertainty"]["exact_count"]["relation"] == "ge"
    assert result["roles"][ROLES[0]]["uncertainty"]["confidence_level"]["approximate"] is True


def test_actual_canonical_witness_defines_identity_while_own_alias_witness_survives():
    args, sources, witness, *_ = fixture(extra="alternative-form-A")
    role = args["roles"][ROLES[1]]
    role["definitions"]["subject"]["label"] = "alternative-form-A"
    role["definitions"]["subject"]["witnesses"] = [witness("alternative-form-A")]
    result = run(args, sources)
    a = result["roles"][ROLES[0]]["definitions"]["subject"]
    b = result["roles"][ROLES[1]]["definitions"]["subject"]
    assert a["canonical_id"] == b["canonical_id"]
    assert b["witnesses"][0]["witness"]["quote"] == "alternative-form-A"
    assert calculate(result)["cells"]["interaction_ratio"]["value"] == 4


def test_source_cell_vs_fit_reuse_and_unknown_physical_identity_are_separate():
    args, sources, *_ = fixture()
    for role in ROLES:
        args["roles"][role]["physical_fit"] = None
    result = run(args, sources)
    assert all(result["roles"][r]["physical_fit"]["physical_fit_id"] is None for r in ROLES)
    assert calculate(result)["cells"]["interaction_ratio"]["value"] == 4
    args, sources, *_ = fixture()
    args["roles"][ROLES[2]]["physical_fit"] = deepcopy(args["roles"][ROLES[0]]["physical_fit"])
    result = run(args, sources)
    assert calculate(result)["cells"]["interaction_ratio"]["reason"] == "reused_physical_fit"
    assert calculate(result)["cells"]["parameter_tr"]["value"] == 2


def test_joint_alias_conflict_across_four_roles_including_ambiguous_rereading():
    args, sources, *_ = fixture()
    args["roles"][ROLES[1]]["measurement"] = deepcopy(args["roles"][ROLES[0]]["measurement"])
    result = run(args, sources)
    assert all(result["roles"][r]["measurement"]["parse_status"] == "conflicting" for r in ROLES[:2])
    assert calculate(result)["cells"]["test_subject_ratio"]["value"] == 2
    # Copy all meanings as well; the same source cell has one exact and one
    # unresolved reading. The exact copy cannot silently resolve the ambiguity.
    args["roles"][ROLES[1]] = deepcopy(args["roles"][ROLES[0]])
    expression = args["roles"][ROLES[1]]["measurement"]["expression"]
    expression.update(status="ambiguous", candidates=[*expression["candidates"], {**expression["candidates"][0], "quote": "6"}])
    result = run(args, sources)
    assert all(result["roles"][r]["measurement"]["parse_status"] == "ambiguous" for r in ROLES[:2])
    assert result["roles"][ROLES[0]]["measurement"]["canonical_measurement"] is None


def test_actual_crop_pixel_mapping_canonicalizes_source_cell_and_rejects_bad_mapping():
    args, sources, *_, image = fixture()
    original = deepcopy(args["roles"][ROLES[0]]["measurement"])
    region = original["cell_region"]
    sources["crop"] = png(image.crop(tuple(region)))
    args["images"].append({"image_id": "crop", "source_ref": "crop", "original_source_ref": "image",
        "mapping": {"original_region": region, "colour_conversion": "preserve"}})
    selected = args["roles"][ROLES[0]]["measurement"]
    selected.update(image_id="crop", cell_region=[0, 0, 200, 28])
    selected["expression"]["candidates"][0].update(image_id="crop", region=[0, 0, 200, 28])
    result = run(args, sources)
    assert result["roles"][ROLES[0]]["measurement"]["canonical_locator"]["image_region"] == region
    assert calculate(result)["cells"]["interaction_ratio"]["value"] == 4
    sources["crop"] = png(Image.new("RGB", (200, 28), "black"))
    failed = run(args, sources)
    assert failed["roles"][ROLES[0]]["measurement"]["parse_status"] == "source_unavailable"
    assert failed["roles"][ROLES[3]]["measurement"]["canonical_measurement"]["value"] == 4


def test_authorization_error_propagates_but_authorized_read_failure_is_local():
    args, sources, *_ = fixture()
    sources["image"] = ContractError("literature_source_not_received")
    with pytest.raises(ContractError, match="source_not_received"):
        run(args, sources)
    args, sources, witness, *_ = fixture()
    sources["missing-fit"] = OSError("authorized synthetic read failed")
    item = witness("fitA0")
    item["source_ref"] = "missing-fit"
    args["roles"][ROLES[0]]["physical_fit"] = {"canonical_witness": item, "witnesses": [item]}
    result = run(args, sources)
    assert result["roles"][ROLES[0]]["physical_fit"]["status"] == "source_unavailable"
    assert result["roles"][ROLES[0]]["physical_fit"]["physical_fit_id"] is None
    assert calculate(result)["cells"]["interaction_ratio"]["value"] == 4


def test_unknown_relationship_withholds_derived_contrast_without_inventing_identity():
    args, sources, *_ = fixture()
    args["relationships"]["ligand_correspondence"] = {"status": "unknown", "witnesses": []}
    result = run(args, sources)
    cells = calculate(result)["cells"]
    assert cells["interaction_ratio"]["reason"] == "ligand_correspondence_unknown"
    assert cells["reference_subject_ratio"]["value"] == 8 and cells["parameter_rr"]["value"] == 5


def test_selected_printed_limit_is_not_a_point_or_model_input():
    args, sources, *_ = fixture(expressions=("5", ">40", "2", "4"))
    result = run(args, sources)
    cells = calculate(result)["cells"]
    assert cells["parameter_rt"]["value"] is None and cells["parameter_rt"]["threshold"] == 40
    assert cells["interaction_ratio"]["value"] is None and cells["interaction_ratio"]["threshold"] == 4
    assert cells["interaction_ratio"]["relation"] == "gt"
    assert cells["signed_profile_log_ratio"]["value"] is None


def test_changed_kind_and_finite_dependency_fingerprints_are_explicit():
    args, sources, _, enum, *_ = fixture()
    args["roles"][ROLES[3]]["parameter_kind"] = enum("reported_hill_kd", "Hill Kd parameter")
    result = run(args, sources)
    assert result["roles"][ROLES[3]]["measurement"]["canonical_measurement"]["value"] == 4
    assert result["roles"][ROLES[3]]["calculation_operand"] is None
    assert result["roles"][ROLES[3]]["unavailable_reasons"] == ["parameter_kind_mismatch"]
    assert set(result["implementation_dependencies"]["sha256"]) == {
        "literature_binding_visual_inputs.py", "literature_binding_reader.py", "literature_experimental_contracts.py",
        "literature_binding_interaction_calculations.py"}


@pytest.mark.parametrize("statistic", ["sd", "sem", "unspecified"])
def test_actual_spread_and_source_statistic_do_not_supply_covariance(statistic):
    args, sources, _, enum, *_ = fixture(expressions=("5 ± 0.3", "40", "2", "4"), extra="reported error")
    args["roles"][ROLES[0]]["uncertainty"]["statistic"] = enum(statistic, "reported error")
    result = run(args, sources)
    operand = result["roles"][ROLES[0]]["calculation_operand"]
    assert operand["reported_spread"] == .3 and operand["uncertainty"]["statistic"] == statistic
    assert calculate(result)["cells"]["interaction_ratio"]["value"] == 4
    assert calculate(result)["cells"]["signed_profile_log_ratio"]["value"] is None


def test_explicit_interval_unit_conversion_with_missing_level():
    args, sources, _, enum, literal, _ = fixture(extra="reported CI; low 0.0041 high 0.0062; interval unit uM")
    selected = args["roles"][ROLES[0]]["uncertainty"]
    selected["statistic"] = enum("confidence_interval", "reported CI")
    selected["interval"] = {"lower": literal("0.0041"), "upper": literal("0.0062"),
        "unit_relationship": enum("explicit_unit", "interval unit"), "unit": literal("uM")}
    result = run(args, sources)
    canonical = result["roles"][ROLES[0]]["calculation_operand"]["uncertainty"]
    assert canonical["interval"] == pytest.approx([4.1, 6.2]) and canonical["confidence_level"] is None
    assert calculate(result)["cells"]["interaction_ratio"]["value"] == 4


@pytest.mark.parametrize("low,high,reason", [
    ("6.1", "4.2", "conflicting_interval_order"),
    ("1.0000000000000000002", "1.0000000000000000001", "conflicting_interval_order"),
    ("1.0000000000000000001", "1.0000000000000000002", "uncertainty_interval_numeric_range"),
])
def test_exact_source_ci_order_and_nonzero_width_are_not_replaced_by_float_equality(low, high, reason):
    args, sources, _, enum, literal, _ = fixture(extra=f"reported CI; low {low}; high {high}")
    selected = args["roles"][ROLES[0]]["uncertainty"]
    selected["statistic"] = enum("confidence_interval", "reported CI")
    selected["interval"] = {"lower": literal(low), "upper": literal(high),
        "unit_relationship": enum("same_as_parameter", "reported CI"), "unit": None}
    result = run(args, sources)
    uncertainty = result["roles"][ROLES[0]]["uncertainty"]
    assert reason in uncertainty["unavailable_reasons"]
    if reason == "conflicting_interval_order":
        assert uncertainty["canonical"] is None
    else:
        assert uncertainty["canonical"]["statistic"] == "confidence_interval"
        assert uncertainty["canonical"]["interval"] == [None, None]
    assert calculate(result)["cells"]["interaction_ratio"]["value"] == 4


def test_same_literal_label_at_different_known_canonical_locations_does_not_infer_identity():
    args, sources, witness, *_ = fixture(extra="another formA occurrence")
    mapped = args["roles"][ROLES[1]]["definitions"]["subject"]
    mapped["canonical_witness"] = witness("formA", after=sources["methods"].decode().index("another"))
    result = run(args, sources)
    assert calculate(result)["cells"]["reference_subject_ratio"]["reason"] == "canonical_subject_conflicting"
    assert result["roles"][ROLES[1]]["definitions"]["subject"]["label"] == "formA"


def test_overlapping_boxes_are_neither_merged_nor_independence():
    args, sources, *_ = fixture()
    args["roles"][ROLES[0]]["measurement"]["cell_region"] = [190, 5, 410, 70]
    result = run(args, sources)
    assert result["geometry_overlaps"] == [{"left_role": ROLES[0], "right_role": ROLES[1]}]
    assert result["roles"][ROLES[0]]["measurement"]["source_cell_id"] != result["roles"][ROLES[1]]["measurement"]["source_cell_id"]
    assert calculate(result)["cells"]["interaction_ratio"]["value"] == 4


def test_missing_operand_and_authorized_source_definition_failure_preserve_other_values():
    args, sources, witness, *_ = fixture()
    args["roles"][ROLES[0]] = None
    source_witness = witness("constructB")
    source_witness["source_ref"] = "unavailable-definition"
    args["roles"][ROLES[2]]["definitions"]["construct"].update(
        witnesses=[source_witness], canonical_witness=source_witness)
    sources["unavailable-definition"] = OSError("authorized synthetic definition unavailable")
    result = run(args, sources)
    assert result["roles"][ROLES[0]]["selection_status"] == "not_selected"
    assert result["roles"][ROLES[2]]["definitions"]["construct"]["canonical_id"] is None
    assert result["roles"][ROLES[2]]["definitions"]["construct"]["status"] == "source_unavailable"
    assert calculate(result)["cells"]["parameter_tr"]["value"] == 2
    assert calculate(result)["cells"]["parameter_tt"]["value"] == 4


def test_dependency_mismatch_is_implementation_error_before_scientific_source_reads(monkeypatch):
    import gene_annotation_episode.literature_binding_interaction_inputs as module
    args, sources, *_ = fixture()
    calls = []
    monkeypatch.setattr(module, "CALCULATOR_SHA256", "0" * 64)
    with pytest.raises(ExperimentalContractError, match="frozen_dependency_mismatch"):
        read_binding_interaction_inputs(args, read_source=reader(sources, calls))
    assert calls == []


def test_nested_markup_and_encoded_qualifier_do_not_make_a_count_exact():
    args, sources, witness, *_ = fixture(extra="μ source count &gt;=<b><i>73</i></b> measurements")
    args["roles"][ROLES[0]]["uncertainty"]["exact_count"] = {
        "status": "exact", "candidates": [witness("73")], "fragments": []}
    result = run(args, sources)
    raw = result["roles"][ROLES[0]]["uncertainty"]["exact_count"]
    assert raw["value"] == 73 and raw["relation"] == "ge" and raw["status"] == "qualified"
    assert result["roles"][ROLES[0]]["calculation_operand"]["uncertainty"]["exact_count"] is None


def test_conflict_requires_distinct_actual_witnesses_and_preserves_valid_source_failure_status():
    args, sources, witness, *_ = fixture()
    selected = witness("IC50 parameter")
    args["parameter_kind"] = {"value": "conflicting", "witnesses": [selected, deepcopy(selected)]}
    with pytest.raises(ExperimentalContractError, match="distinct_conflicting_witnesses_required"):
        run(args, sources)


def test_reported_hill_kind_is_preserved_without_ic50_conversion():
    args, sources, witness, enum, *_ = fixture()
    args["parameter_kind"] = enum("reported_hill_kd", "Hill Kd parameter")
    for role in ROLES:
        args["roles"][role]["parameter_kind"] = enum("reported_hill_kd", "Hill Kd parameter")
        args["roles"][role]["definitions"]["parameter_definition"] = {
            "status": "known", "label": "Hilldefinition", "witnesses": [witness("Hilldefinition")],
            "canonical_witness": witness("Hilldefinition")}
    result = run(args, sources)
    assert result["calculation_inputs"]["parameter_kind"] == "reported_hill_kd"
    assert calculate(result)["cells"]["interaction_ratio"]["value"] == 4


def test_actual_spread_presence_survives_unknown_statistic_or_unit():
    args, sources, *_ = fixture(expressions=("5 ± 0.3", "40", "2", "4"))
    args["roles"][ROLES[0]]["uncertainty"] = None
    result = run(args, sources)
    assert result["roles"][ROLES[0]]["uncertainty"]["reported_spread_status"] == "reported"
    assert result["roles"][ROLES[0]]["measurement"]["canonical_measurement"]["reported_spread"] == .3
    assert calculate(result)["cells"]["interaction_ratio"]["value"] == 4
    args["roles"][ROLES[0]]["measurement"]["unit"] = None
    result = run(args, sources)
    assert result["roles"][ROLES[0]]["uncertainty"]["reported_spread_status"] == "native_reported_unit_unavailable"
    assert result["roles"][ROLES[0]]["measurement"]["native_measurement"]["reported_spread"] == .3


def test_nd_state_survives_an_independently_missing_unit():
    args, sources, *_ = fixture(expressions=("n.d.", "40", "2", "4"))
    args["roles"][ROLES[0]]["measurement"]["unit"] = None
    result = run(args, sources)
    measurement = result["roles"][ROLES[0]]["measurement"]
    assert measurement["parse_status"] == "reported_unavailable"
    assert measurement["native_measurement"]["relation"] == "unreported"
    assert measurement["unit"]["status"] == "not_selected" and measurement["canonical_measurement"] is None


def test_returned_partial_codes_have_declared_finite_vocabularies():
    import gene_annotation_episode.literature_binding_interaction_inputs as module
    args, sources, *_ = fixture()
    result = run(args, sources)
    assert result["calculation_input_status"] in module.CALCULATION_INPUT_STATUSES
    for row in result["roles"].values():
        assert row["measurement"]["parse_status"] in module.MEASUREMENT_STATUSES
        assert set(row["unavailable_reasons"]) <= set(module.ROLE_UNAVAILABLE_REASONS)
        assert set(row["uncertainty"]["unavailable_reasons"]) <= set(module.UNCERTAINTY_REASONS)
        for name in ("confidence_level", "exact_count", "minimum_count"):
            assert row["uncertainty"][name]["status"] in module.SCALAR_STATUSES


def test_source_probability_domain_and_numerical_rounding_have_distinct_missing_reasons():
    for token, reason in (("1.1", "confidence_level_out_of_range"),
                          ("0.9999999999999999999", "confidence_level_numeric_range")):
        args, sources, _, enum, literal, _ = fixture(extra="reported CI; confidence " + token)
        uncertainty = args["roles"][ROLES[0]]["uncertainty"]
        uncertainty["statistic"] = enum("confidence_interval", "reported CI")
        uncertainty["confidence_level"] = literal(token)
        result = run(args, sources)
        partial = result["roles"][ROLES[0]]["uncertainty"]
        assert partial["canonical"]["confidence_level"] is None
        assert reason in partial["unavailable_reasons"]
        assert calculate(result)["cells"]["interaction_ratio"]["value"] == 4
