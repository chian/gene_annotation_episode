"""Synthetic contrasts and the retained primary HFP completion-time example."""
from copy import deepcopy
from fractions import Fraction
import hashlib
from pathlib import Path

import pytest

from gene_annotation_episode.literature_completion_time_inputs import (
    LITERAL_FIELDS, read_completion_time_inputs, validate_completion_time_extraction)
from gene_annotation_episode.literature_completion_time_calculations import populate_completion_time_components
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError

SOURCE = "source_" + "1" * 24
ARTIFACT = "artifact_" + "2" * 64
TEXT = "Synthetic preparation cleanup took >18 h; original took <10 min to reach equilibrium. The intended change was purification. Heat also changed."


def witness(text, quote, occurrence=0):
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(quote, start + 1)
    return {"source_ref": SOURCE, "representation": "original", "start": len(text[:start].encode()),
        "end": len(text[:start + len(quote)].encode()), "quote": quote}


def interpretation(value, text=TEXT, quote="equilibrium"):
    return {"value": value, "witnesses": [] if value == "unknown" else [witness(text, quote)]}


def fixture(text=TEXT, first="18 h", second="10 min", n="18", d="10", nunit="h", dunit="min"):
    def quantity(quote, token, unit, preparation):
        selected = {**dict.fromkeys(LITERAL_FIELDS), "preparation": witness(text, preparation if preparation in text else "equilibrium"),
            "endpoint": witness(text, "equilibrium"),
            "measurement": {"number": {"witness": witness(text, quote), "number_start": quote.index(token),
                "number_end": quote.index(token) + len(token)},
                "unit": witness(text, unit, text[:text.index(quote)].count(unit)) if unit else None},
            "qualification": interpretation("reported_point", text)}
        return selected
    args = {"source_ref": SOURCE, "source_kind": "synthetic_fixture", "experiment": witness(text, "equilibrium"),
        "intended_change": witness(text, "purification") if "purification" in text else None,
        "other_changes": [witness(text, "Heat also changed")] if "Heat also changed" in text else [],
        "comparison": {"endpoint_relation": interpretation("same", text),
            "preparation_relation": interpretation("different", text), "pair_relationship": interpretation("supported", text),
            "other_changes_status": interpretation("partial", text)},
        "quantities": {"numerator": quantity(first, n, nunit, "cleanup"),
            "denominator": quantity(second, d, dunit, "original")}}
    sources = {SOURCE: {"artifact_ref": ARTIFACT, "content": text.encode()}}
    def reader(reference, representation):
        return deepcopy(sources[reference])
    return args, sources, reader


def primary_fixture():
    path = Path(__file__).resolve().parents[1] / "research/experimental_scoring_review_2026-10-23/a105_assay_validity_case_145/primary.xml"
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == "da929d9013cedb766ca861164e5c67f35bdbca891b6e1f5826df24c3eda873db"
    text = data.decode()
    args, sources, reader = fixture(text, first="&gt;18 h", second="&lt;10 min")
    args["source_kind"] = "primary_source"
    w = lambda quote: witness(text, quote)
    args["experiment"] = w("the sample isomerizes Ru5P")
    args["intended_change"] = w("In order to obtain a sample of the highest purity possible")
    args["other_changes"] = [w("an HFP construct was generated bearing a histidine tag"),
        w("Following purification using affinity chromatography, gel filtration, heat (90 °C for 2 min) followed by centrifugation to remove precipitated proteins")]
    basis = w("equilibrium is reached much more slowly (&gt;18 h as opposed to &lt;10 min)")
    for field in args["comparison"]:
        args["comparison"][field]["witnesses"] = [basis]
    for role in args["quantities"]:
        q = args["quantities"][role]
        q["subject"] = w("HFP")
        q["endpoint"] = w("equilibrium mixture of 39.7% ketose (ribulose) and 60.3% aldose (ribose) stereoisomer 5-phosphates")
        q["preparation"] = w("Following purification using affinity chromatography, gel filtration, heat (90 °C for 2 min) followed by centrifugation to remove precipitated proteins") if role == "numerator" else w("the sample had isomerase activity interconverting ribulose 5-phosphate and ribose 5-phosphate")
        q["qualification"]["witnesses"] = [basis]
    # Distinct original time tokens appear in Results p0065's explicit comparison.
    for role, raw, unit in (("numerator", "&gt;18 h", "h"), ("denominator", "&lt;10 min", "min")):
        start = text.index(raw)
        uq = witness(text, raw)
        q = args["quantities"][role]
        q["measurement"]["unit"] = {**uq, "start": len(text[:start + raw.rindex(unit)].encode()),
            "end": len(text[:start + len(raw)].encode()), "quote": unit}
    return args, sources, reader


def populated(args, reader):
    extraction = read_completion_time_inputs(args, read_source=reader)
    validate_completion_time_extraction(extraction)
    return extraction, populate_completion_time_components(extraction)["cells"]


def test_primary_hfp_strict_time_ratio_and_inverse_are_endpoint_protocol_comparisons():
    args, _, reader = primary_fixture()
    extraction, cells = populated(args, reader)
    assert extraction["quantities"]["numerator"]["exact_minutes"] == "1080"
    ratio = cells["completion_time_ratio"]
    assert ratio["value"] is None
    assert ratio["reported_domain"]["lower"] == 108
    assert ratio["reported_domain"]["upper"] is None
    assert not ratio["reported_domain"]["lower_inclusive"]
    inverse = cells["inverse_completion_time_ratio"]["exact_domain"]
    assert inverse["upper"] == {"numerator": "1", "denominator": "108"}
    assert not inverse["upper_inclusive"] and not inverse["lower_inclusive"]
    assert len(args["other_changes"]) == 2


@pytest.mark.parametrize("first,n,unit,expected", [("7 s", "7", "s", Fraction(7, 60)),
    ("2 hours", "2", "hours", Fraction(120)), ("1 minutes", "1", "minutes", Fraction(1))])
def test_exact_unit_conversion_keeps_nearest_point_separate_from_outward_domain(first, n, unit, expected):
    text = f"Synthetic cleanup took {first}; original took 10 min to equilibrium."
    args, _, reader = fixture(text, first=first, n=n, nunit=unit)
    _, cells = populated(args, reader)
    cell = cells["numerator_time"]
    assert cell["value"] == float(expected)
    assert cell["exact_domain"]["lower"] == {"numerator": str(expected.numerator), "denominator": str(expected.denominator)}
    assert Fraction(cell["reported_domain"]["lower"]) <= expected <= Fraction(cell["reported_domain"]["upper"])


@pytest.mark.parametrize("prefix,valid", [("", False), ("<", False), ("<=", False), (">", True), (">=", True)])
def test_zero_time_is_not_an_observed_denominator_but_censored_zero_edge_is_open(prefix, valid):
    text = f"Synthetic cleanup took 18 h; original took {prefix}0 min to equilibrium."
    args, _, reader = fixture(text, d="0", second="0 min")
    _, cells = populated(args, reader)
    assert (cells["completion_time_ratio"]["status"] != "unavailable") is valid
    if valid:
        domain = cells["denominator_time"]["exact_domain"]
        assert domain["lower"] == {"numerator": "0", "denominator": "1"}
        assert not domain["lower_inclusive"]
    else:
        assert cells["completion_time_ratio"]["unavailable_reason"] == "nonpositive_physical_time"


@pytest.mark.parametrize("raw,unit", [("10 days", "min"), ("10 milliseconds", "min"), ("10 ms", "min"), ("10 h", "min")])
def test_cannot_borrow_unit_from_unrelated_time(raw, unit):
    text = f"Synthetic cleanup took {raw}; original took 10 min to equilibrium."
    args, _, reader = fixture(text, first=raw, n="10", nunit=unit)
    with pytest.raises(ExperimentalContractError, match="source_time_unit_mismatch"):
        populated(args, reader)


@pytest.mark.parametrize("raw,unit", [("10 min^-1", "min"), ("10 ms", "s"), ("10 h/min", "h"), ("10 per min", "min"), ("10 min%", "min"), ("10 seconds per minute", "seconds")])
def test_cannot_clip_rate_or_unit_token_to_time(raw, unit):
    text = f"Synthetic cleanup took {raw}; original took 10 min to equilibrium."
    args, _, reader = fixture(text, first=raw, n="10", nunit=unit)
    with pytest.raises(ExperimentalContractError, match="partial_source_time_unit"):
        populated(args, reader)


def test_unknown_unit_or_relationship_keeps_individual_other_time_and_source_censor():
    text = "Synthetic cleanup took >18 days; original took <10 min to equilibrium."
    args, _, reader = fixture(text, first="18 days", nunit="days")
    extraction, cells = populated(args, reader)
    assert extraction["quantities"]["numerator"]["bound"] == "gt"
    assert cells["numerator_time"]["unavailable_reason"] == "unsupported_source_time_unit"
    assert cells["denominator_time"]["reported_domain"]["upper"] == 10
    args, _, reader = fixture()
    args["comparison"]["endpoint_relation"] = {"value": "unknown", "witnesses": []}
    _, cells = populated(args, reader)
    assert cells["numerator_time"]["reported_domain"]["lower"] == 1080
    assert cells["completion_time_ratio"]["unavailable_reason"] == "endpoint_relation_unknown"


def test_approximation_unknown_qualification_and_duplicate_identity_remain_distinct():
    text = "Synthetic cleanup took approximately 18 h; original took 10 min to equilibrium."
    args, _, reader = fixture(text)
    _, cells = populated(args, reader)
    assert cells["completion_time_ratio"]["value"] == 108 and cells["completion_time_ratio"]["approximate"]
    args["quantities"]["numerator"]["qualification"] = {"value": "unknown", "witnesses": []}
    _, cells = populated(args, reader)
    assert cells["numerator_time"]["value"] == 1080
    assert cells["completion_time_ratio"]["unavailable_reason"] == "qualification_unknown"
    args, _, reader = fixture()
    args["quantities"]["denominator"] = deepcopy(args["quantities"]["numerator"])
    _, cells = populated(args, reader)
    assert cells["completion_time_ratio"]["unavailable_reason"] == "reused_source_observation"


def test_missing_and_conflicting_units_preserve_partial_other_time():
    args, _, reader = fixture()
    args["quantities"]["numerator"]["measurement"]["unit"] = None
    _, cells = populated(args, reader)
    assert cells["numerator_time"]["unavailable_reason"] == "source_time_unit_unreported"
    assert cells["denominator_time"]["exact_domain"] is not None
    # Deliberately synthetic competing source-unit selections, not a claim
    # that the two correctly labeled arms in TEXT scientifically conflict.
    args, _, reader = fixture()
    args["quantities"]["numerator"]["measurement"]["unit"] = {"conflicting_units": [witness(TEXT, " h"), witness(TEXT, "min")]}
    extraction, cells = populated(args, reader)
    assert cells["numerator_time"]["unavailable_reason"] == "source_time_unit_conflicting"
    assert cells["denominator_time"]["exact_domain"] is not None
    assert len(extraction["quantities"]["numerator"]["unit"]["conflicting_units"]) == 2
