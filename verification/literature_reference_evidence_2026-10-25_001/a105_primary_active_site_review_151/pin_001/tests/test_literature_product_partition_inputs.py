"""Original PMC12051542 numeric spans and explicitly synthetic contrasts."""
from copy import deepcopy
from pathlib import Path
import hashlib

import pytest

from gene_annotation_episode.literature_product_partition_inputs import (MEANINGS,
    read_product_partition_inputs, validate_product_partition_extraction)
from gene_annotation_episode.literature_product_partition_calculations import populate_product_partition_components

SOURCE = "source_" + "a" * 64
PRIMARY = Path(__file__).resolve().parents[1] / "research/experimental_scoring_review_2026-10-23/a105_assay_validity_case_145/primary.xml"
PRIMARY_SHA = "da929d9013cedb766ca861164e5c67f35bdbca891b6e1f5826df24c3eda873db"
TEXT = b"<p>Synthetic HFP preparation. Equilibrium mixture: R5P 60.3% and Ru5P 39.7%. NMR composition.</p>"


def fixture(raw=TEXT, *, primary=False, a_token="60.3", a_unit="%"):
    def witness(text, occurrence=0):
        encoded = text.encode()
        start = -1
        for _ in range(occurrence + 1): start = raw.index(encoded, start + 1)
        return {"source_ref": SOURCE, "representation": "original", "start": start,
                "end": start + len(encoded), "quote": text}
    def meaning(value, text=None):
        return {"value": value, "witnesses": [witness(text)] if text else []}
    def fraction(token, compound, unit="%"):
        w = witness(token)
        unit_start = w["end"]
        while raw[unit_start:unit_start + 1] == b" ": unit_start += 1
        meanings = {name: None for name in MEANINGS}
        meanings.update(subject=witness("HFP"), compound=witness(compound),
            denominator=witness("equilibrium mixture" if primary else "Equilibrium mixture"),
            stage=witness("equilibrium" if primary else "Equilibrium"),
            measurement_basis=witness("NMR"), preparation=witness("HFP"))
        return {"meanings": meanings, "measurement": {
            "number": {"witness": w, "number_start": 0, "number_end": len(token)},
            "unit": {"source_ref": SOURCE, "representation": "original", "start": unit_start,
                     "end": unit_start + len(unit.encode()), "quote": unit}},
            "basis": meaning("amount_fraction", "mixture"),
            "stage": meaning("equilibrium", "equilibrium" if primary else "Equilibrium"),
            "qualification": meaning("reported_point", token)}
    args = {"source_ref": SOURCE, "source_kind": "primary_source" if primary else "synthetic_fixture",
        "experiment": witness("equilibrium mixture" if primary else "Equilibrium mixture"),
        "quantities": {"a": fraction(a_token, "R5P", a_unit), "b": fraction("39.7", "Ru5P")},
        "relationships": {name: meaning("supported", "equilibrium mixture" if primary else "Equilibrium mixture")
            for name in ("same_preparation", "same_endpoint", "shared_denominator")}, "evidence": []}
    artifact = "artifact_" + hashlib.sha256(raw).hexdigest()
    def read(ref, representation):
        assert ref == SOURCE and representation == "original"
        return {"artifact_ref": artifact, "content": raw}
    return args, read, witness


def test_original_primary_percentages_preserve_selected_partition_and_not_attribution():
    raw = PRIMARY.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PRIMARY_SHA
    args, read, witness = fixture(raw, primary=True)
    # Exact source roles are qualifications, not independent numerical proofs.
    args["evidence"] = [
        {"role": "competing_contribution", "witness": witness("RpiA in the HFP sample was confirmed by mass spectrometry")},
        {"role": "composition", "witness": witness("39.7% ketose (ribulose) and 60.3% aldose (ribose)")},
    ]
    extraction = read_product_partition_inputs(args, read_source=read)
    validate_product_partition_extraction(extraction, args)
    sheet = populate_product_partition_components(extraction)
    assert [sheet["cells"][name]["value"] for name in ("partition_a_fraction", "partition_b_fraction",
        "selected_fraction_sum", "selected_closure_deviation")] == [.603, .397, 1., 0.]
    assert sheet["cells"]["partition_a_over_b"]["value"] == pytest.approx(.603 / .397)
    assert sheet["uncertainty_calculation"] == "not_implemented"
    assert extraction["quantities"]["a"]["origin"] == "reported"


@pytest.mark.parametrize("relationship", ["same_preparation", "same_endpoint", "shared_denominator"])
@pytest.mark.parametrize("value", ["unknown", "conflicting"])
def test_unresolved_pair_preserves_individual_source_numbers(relationship, value):
    args, read, witness = fixture()
    args["relationships"][relationship] = {"value": value, "witnesses": [] if value == "unknown" else [witness("R5P"), witness("Ru5P")]}
    cells = populate_product_partition_components(read_product_partition_inputs(args, read_source=read))["cells"]
    assert cells["partition_a_fraction"]["value"] == .603
    assert cells["partition_b_fraction"]["value"] == .397
    assert cells["partition_a_over_b"]["unavailable_reason"] == relationship + "_" + value


@pytest.mark.parametrize("prefix,bound,approx", [("< ", "lt", False), (">= ", "ge", False), ("approximately ", "none", True), ("about > ", "gt", True)])
def test_fraction_bounds_and_approximation_are_not_exact_points(prefix, bound, approx):
    raw = TEXT.replace(b"R5P 60.3", ("R5P " + prefix + "60.3").encode())
    args, read, _ = fixture(raw)
    cells = populate_product_partition_components(read_product_partition_inputs(args, read_source=read))["cells"]
    assert cells["partition_a_fraction"]["bound"] == bound
    assert cells["partition_a_fraction"]["approximate"] is approx
    if bound != "none":
        assert cells["partition_a_fraction"]["value"] is None
        assert cells["partition_a_fraction"]["threshold"] == .603
        assert cells["partition_a_over_b"]["value"] is None


def test_remote_source_approximation_has_explicit_witness_and_literal_cannot_be_overridden():
    raw = TEXT.replace(b"Equilibrium mixture", b"Estimated Equilibrium mixture")
    args, read, witness = fixture(raw)
    args["quantities"]["a"]["qualification"] = {"value": "source_qualified_approximate", "witnesses": [witness("Estimated")]}
    extraction = read_product_partition_inputs(args, read_source=read)
    assert extraction["quantities"]["a"]["approximate"]
    raw = TEXT.replace(b"R5P 60.3", b"R5P about 60.3")
    args, read, _ = fixture(raw)
    assert args["quantities"]["a"]["qualification"]["value"] == "reported_point"
    assert read_product_partition_inputs(args, read_source=read)["quantities"]["a"]["approximate"]


def test_percent_to_fraction_conversion_and_unsupported_units_remain_partial():
    raw = TEXT.replace(b"60.3%", b"0.603 fraction")
    args, read, _ = fixture(raw, a_token="0.603", a_unit="fraction")
    assert read_product_partition_inputs(args, read_source=read)["quantities"]["a"]["value"] == .603
    args["quantities"]["a"]["measurement"]["unit"] = None
    extraction = read_product_partition_inputs(args, read_source=read)
    cells = populate_product_partition_components(extraction)["cells"]
    assert cells["partition_a_fraction"]["unavailable_reason"] == "source_fraction_unit_unreported"
    assert cells["partition_b_fraction"]["value"] == .397


@pytest.mark.parametrize("mutation", [
    lambda a: a["quantities"]["a"]["measurement"]["number"].update(number_start=1),
    lambda a: a["quantities"]["a"]["measurement"]["number"]["witness"].update(quote="60.4"),
    lambda a: a["quantities"]["a"]["measurement"].update(value=60.3),
])
def test_clipped_forged_or_model_authored_numbers_are_rejected(mutation):
    args, read, _ = fixture()
    mutation(args)
    with pytest.raises(ValueError): read_product_partition_inputs(args, read_source=read)


def test_duplicate_source_expression_cannot_manufacture_ratio_one():
    args, read, _ = fixture()
    args["quantities"]["b"] = deepcopy(args["quantities"]["a"])
    cells = populate_product_partition_components(read_product_partition_inputs(args, read_source=read))["cells"]
    assert cells["partition_a_over_b"]["unavailable_reason"] == "reused_source_observation"


def test_calculator_validates_saved_extraction_before_using_numbers():
    args, read, _ = fixture()
    extraction = read_product_partition_inputs(args, read_source=read)
    extraction["quantities"]["a"]["value"] = 99
    with pytest.raises(ValueError, match="partition_saved_quantity_mismatch"):
        populate_product_partition_components(extraction)


@pytest.mark.parametrize("unit", ["h", "hours", "days", "U/mg", "mM", "mg"])
def test_explicit_physical_units_cannot_be_relabelled_percent(unit):
    raw = TEXT.replace(b"60.3%", ("60.3 " + unit).encode())
    args, read, witness = fixture(raw, a_unit=unit)
    args["quantities"]["a"]["measurement"]["unit"] = witness("%")
    with pytest.raises(ValueError, match="source_fraction_unit_mismatch"):
        read_product_partition_inputs(args, read_source=read)


def test_unsupported_reported_fraction_unit_is_an_input_limit_not_paper_omission():
    raw = TEXT.replace(b"60.3%", b"60.3 share")
    args, read, _ = fixture(raw, a_unit="share")
    extraction = read_product_partition_inputs(args, read_source=read)
    cells = populate_product_partition_components(extraction)["cells"]
    assert cells["partition_a_fraction"]["unavailable_reason"] == "unsupported_source_fraction_unit"
    assert extraction["selection"]["quantities"]["a"]["measurement"]["unit"]["raw_unit"] == "share"
    assert cells["partition_b_fraction"]["value"] == .397


def test_out_of_range_report_is_retained_flagged_and_never_clamped():
    raw = TEXT.replace(b"60.3%", b"160.3%")
    args, read, _ = fixture(raw, a_token="160.3")
    cells = populate_product_partition_components(read_product_partition_inputs(args, read_source=read))["cells"]
    assert cells["partition_a_fraction"]["value"] == 1.603
    assert cells["partition_a_fraction"]["outside_reported_fraction_range"]
    assert cells["selected_fraction_sum"]["value"] == 2


@pytest.mark.parametrize("qualification", ["unknown", "conflicting"])
def test_unresolved_source_qualification_retains_fraction_and_blocks_pair(qualification):
    args, read, witness = fixture()
    args["quantities"]["a"]["qualification"] = {"value": qualification,
        "witnesses": [] if qualification == "unknown" else [witness("R5P"), witness("Ru5P")]}
    cells = populate_product_partition_components(read_product_partition_inputs(args, read_source=read))["cells"]
    assert cells["partition_a_fraction"]["value"] == .603
    assert cells["partition_a_over_b"]["unavailable_reason"] == "qualification_" + qualification
