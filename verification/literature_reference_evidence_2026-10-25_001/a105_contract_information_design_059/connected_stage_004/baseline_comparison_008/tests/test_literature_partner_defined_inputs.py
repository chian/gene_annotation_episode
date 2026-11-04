"""Source-backed activity-unit relationships feed the existing partner cells."""
from copy import deepcopy

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode import literature_partner_native_inputs as reader


ROOT, DATA, DEFINITION = ("source_" + str(i) * 24 for i in (1, 2, 3))


def fixture(*, coefficient="1", time="min", omitted="0.1", mean_unit="defined",
            spread_unit="common", partial=False, source_kind="synthetic_fixture"):
    """Synthetic source text; never acquires or interprets a primary paper."""
    main = "U/mg" if mean_unit == "defined" else "umol/min/mg"
    uncertainty_unit = {"common": "", "plain": " umol/min/mg", "defined": " U/mg"}[spread_unit]
    raw = ("µ SubjectS; PartnerP; NADH oxidation; per mg SubjectS. "
        "Panel is complete. Nitrogen glutamine. physicalW; physicalO; physicalA.\n"
        f"W rate 7 {main} +/- 0.2{uncertainty_unit} SD.\n"
        f"O rate {omitted} {main}.\nA rate 6 {main}.\n").encode()
    clause = f"{coefficient} μmol of NADH oxidized per {time}"
    bridge = f"One unit was equivalent to {clause}, 1 μmol of H2 formed per min."
    definition_raw = bridge.encode()
    payloads = {
        ROOT: {"artifact_ref": "artifact_" + "a" * 64, "content": b"\xff\x00Synthetic source"},
        DATA: {"artifact_ref": "artifact_" + "b" * 64, "content": raw},
        DEFINITION: {"artifact_ref": "artifact_" + "c" * 64, "content": definition_raw},
    }
    calls = []

    def read_source(ref, representation):
        calls.append((ref, representation))
        assert representation == "original"
        return payloads[ref]

    def witness(quote, *, ref=DATA, offset=0):
        content = payloads[ref]["content"]
        start = content.index(quote.encode(), offset)
        return {"source_ref": ref, "representation": "original", "start": start,
                "end": start + len(quote.encode()), "quote": quote}

    def number(token, *, quote=None, ref=DATA, offset=0):
        selected = witness(token if quote is None else quote, ref=ref, offset=offset)
        start = selected["quote"].index(token)
        return {"witness": selected, "number_start": start, "number_end": start + len(token)}

    endpoint = witness("NADH oxidation")

    def defined_unit(header):
        return {"kind": "source_defined_rate_unit", "witness": header,
            "definition": {"bridge": witness(bridge, ref=DEFINITION),
                "clause": witness(clause, ref=DEFINITION),
                "amount": number(coefficient, quote=bridge, ref=DEFINITION),
                "amount_unit": witness("μmol", ref=DEFINITION),
                "time_unit": witness(time, ref=DEFINITION,
                    offset=definition_raw.index(clause.encode())),
                "endpoint": deepcopy(endpoint), "endpoint_entity": witness("NADH"),
                "definition_entity": witness("NADH", ref=DEFINITION)}}

    arms = {}
    for role, label, token in (("reference", "W", "7"),
            ("omitted", "O", omitted.lstrip("<≤=")), ("addback", "A", "6")):
        offset = raw.index((label + " rate").encode())
        unit = witness(main, offset=offset)
        spread = {"kind": "unreported", "magnitude": None, "unit": None, "witnesses": []}
        if role == "reference":
            chosen_spread = None
            if spread_unit != "common":
                header = witness("U/mg" if spread_unit == "defined" else "umol/min/mg",
                                 offset=raw.index(b"0.2", offset))
                chosen_spread = defined_unit(header) if spread_unit == "defined" else header
            spread = {"kind": "SD", "magnitude": number("0.2", offset=offset),
                      "unit": chosen_spread, "witnesses": [witness("SD")]}
        arms[role] = {"subject": witness("SubjectS"), "partner": witness("PartnerP"),
            "endpoint": deepcopy(endpoint), "normalization": witness("per mg SubjectS"),
            "partner_state": "absent" if role == "omitted" else "present",
            "conditions": {"coverage": "partial" if partial else "complete", "factors": [
                {"factor": "nitrogen", "level": {"kind": "literal", "witness": witness("glutamine")}}]},
            "measurement_identity": None if partial else witness("physical" + label),
            "origin": "synthetic" if source_kind == "synthetic_fixture" else "reported",
            "rate": {"value": number(token, offset=offset),
                "unit": defined_unit(unit) if mean_unit == "defined" else unit, "spread": spread}}
    args = {"source_ref": ROOT, "data_source_ref": DATA, "source_kind": source_kind,
        "literals": dict.fromkeys(reader.LITERAL_FIELDS),
        "interpretation_witnesses": [witness("Panel is complete.")],
        "input_mode": "native_source_spans", "arms": arms}
    args["literals"].update(subject=witness("SubjectS"), partner=witness("PartnerP"),
        endpoint=deepcopy(endpoint), normalization=witness("per mg SubjectS"))
    return args, payloads, calls, read_source, witness, number


def read(fix):
    return reader.read_partner_native_inputs(fix[0], read_source=fix[3])


def test_source_defined_unit_populates_existing_cells_and_preserves_raw_relationship():
    fix = fixture()
    before = deepcopy((fix[0], fix[1]))
    out = read(fix)
    assert out["version"] == reader.DEFINED_VERSION
    assert [out["cells"][name]["value"] for name in reader.COMPONENTS] == [
        7000000, 100000, 6000000, 6900000, 69/70, 5900000, 59/69, 59/70]
    unit = out["native_evidence"]["reference"]["rate"]["unit"]
    assert unit["raw_unit"] == "U/mg" and unit["multiplier"] == 1000000
    assert unit["definition"]["amount"]["raw_number"] == "1"
    assert unit["definition"]["endpoint"]["quote"] == "NADH oxidation"
    assert out["native_evidence"]["reference"]["rate"]["canonical_spread"] == 200000
    assert out["sources"] == [ROOT, DATA, DEFINITION]
    validate_schema(fix[0], reader.partner_source_population_schema())
    validate_schema(out["native_evidence"], reader.native_evidence_schema())
    assert (fix[0], fix[1]) == before


def test_plain_only_input_retains_exact_v2_and_has_no_definition_fields():
    out = read(fixture(mean_unit="plain"))
    assert out["version"] == reader.VERSION
    assert out["sources"] == [ROOT, DATA]
    assert set(out["native_evidence"]["reference"]["rate"]["unit"]) == {
        "witness", "raw_unit", "canonical_unit", "multiplier"}
    validate_schema(out["native_evidence"], reader.native_evidence_schema(defined_units=False))


@pytest.mark.parametrize("coefficient,time,scale", [("2", "min", 2000000), ("1", "s", 60000000)])
def test_source_coefficient_and_time_basis_control_the_conversion(coefficient, time, scale):
    out = read(fixture(coefficient=coefficient, time=time))
    assert out["cells"]["reference_rate"]["value"] == 7 * scale
    assert out["native_evidence"]["reference"]["rate"]["unit"]["multiplier"] == scale


@pytest.mark.parametrize("mean_unit,spread_unit,coefficient,spread", [
    ("defined", "plain", "1", 200000), ("plain", "defined", "2", 400000)])
def test_explicit_spread_unit_is_converted_independently(mean_unit, spread_unit, coefficient, spread):
    out = read(fixture(mean_unit=mean_unit, spread_unit=spread_unit, coefficient=coefficient))
    assert out["version"] == reader.DEFINED_VERSION
    rate = out["native_evidence"]["reference"]["rate"]
    assert rate["canonical_spread"] == spread
    assert ("definition" in rate["unit"]) == (mean_unit == "defined")
    assert ("definition" in rate["spread"]["unit"]) == (spread_unit == "defined")


def test_unselected_U_spread_is_rejected_even_for_otherwise_v2_input():
    fix = fixture(mean_unit="plain", spread_unit="defined")
    fix[0]["arms"]["reference"]["rate"]["spread"]["unit"] = None
    with pytest.raises(ExperimentalContractError, match="defined_unit_spread_definition_required"):
        read(fix)


def test_defined_upper_limit_keeps_its_raw_strict_relation_and_unknown_point():
    out = read(fixture(omitted="<0.01"))
    native = out["native_evidence"]["omitted"]["rate"]
    assert native["value"]["relation"] == "lt" and native["value"]["raw_number"] == "0.01"
    cell = out["cells"]["omitted_rate"]
    assert cell["value"] is None and (cell["lower"], cell["upper"]) == (0, 10000)
    assert cell["bound_kind"] == "conditional_input_domain_not_CI"


def test_partial_scientific_information_keeps_native_rates_without_invented_comparisons():
    fix = fixture(partial=True, source_kind="retained_extraction")
    fix[0]["arms"]["addback"] = None
    out = read(fix)
    assert [out["cells"][name]["value"] for name in reader.COMPONENTS] == [
        7000000, 100000, None, None, None, None, None, None]
    assert out["cells"]["partner_loss"]["unavailable_reason"] == "conditions_incomplete"
    assert out["recipe"]["inputs"]["arms"]["reference"]["measurement"]["measurement_id"] is None


@pytest.mark.parametrize("mode", ["endpoint", "entity", "outside_clause", "numeric_argument", "unknown_endpoint"])
def test_wrong_defined_relationship_does_not_reach_core(mode, monkeypatch):
    fix = fixture()
    arm = fix[0]["arms"]["reference"]
    definition = arm["rate"]["unit"]["definition"]
    if mode == "endpoint":
        definition["endpoint"] = fix[4]("SubjectS")
    elif mode == "entity":
        definition["definition_entity"] = fix[4]("H2", ref=DEFINITION)
    elif mode == "outside_clause":
        definition["time_unit"] = fix[4]("min", ref=DEFINITION,
            offset=definition["clause"]["end"])
    elif mode == "numeric_argument":
        definition["amount"] = 1
    else:
        arm["endpoint"] = None
    monkeypatch.setattr(reader, "populate_partner_components", lambda _: pytest.fail("bad unit reached calculator"))
    with pytest.raises(ExperimentalContractError):
        read(fix)


def test_broad_v3_schema_does_not_change_the_strict_v2_evidence_shape():
    out = read(fixture())
    with pytest.raises(ContractError):
        validate_schema(out["native_evidence"], reader.native_evidence_schema(defined_units=False))
    invalid = deepcopy(fixture()[0])
    invalid["arms"]["reference"]["rate"]["unit"]["multiplier"] = 1000000
    with pytest.raises(ContractError):
        validate_schema(invalid, reader.partner_source_population_schema())
