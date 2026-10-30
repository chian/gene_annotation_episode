"""Scalar source ports; synthetic exact bytes and millibit edge cases."""
from copy import deepcopy
import json
import math
import struct

import pytest

from gene_annotation_episode.hmmer_model_source_cells import (
    binary_probability_cell, hmmer2_probability_cell,
)


@pytest.mark.parametrize("order,prefix", [("little", "<"), ("big", ">")])
@pytest.mark.parametrize("value", [0.0, -0.0, 1.0, 0.5, 2**-149])
def test_binary_exact_widening_source_and_signed_zero(order, prefix, value):
    raw = struct.pack(prefix + "f", value)
    cell = binary_probability_cell(raw, byte_start=37, byte_order=order)
    assert set(cell) == {"token", "negative_log_probability", "probability", "state", "source"}
    assert cell["token"] is cell["negative_log_probability"] is None
    assert cell["probability"] == value
    assert math.copysign(1, cell["probability"]) == math.copysign(1, value)
    assert cell["state"] == ("structural_zero" if value == 0 else "finite")
    assert cell["source"] == {"encoding": "ieee754_binary32_probability",
        "raw_hex": raw.hex(), "byte_start": 37, "byte_end": 41}
    assert json.loads(json.dumps(cell, allow_nan=False)) == cell


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, -0.25, 1.25])
def test_binary_invalid_domain_keeps_source_without_nonfinite_json(value):
    raw = struct.pack("<f", value)
    cell = binary_probability_cell(raw, byte_start=0, byte_order="little")
    assert cell["state"] == "invalid" and cell["probability"] is None
    assert cell["source"]["raw_hex"] == raw.hex()
    json.dumps(cell, allow_nan=False)


@pytest.mark.parametrize("raw", [b"", b"\x00", b"\x00\x00\x80"])
def test_partial_binary_cell_has_actual_byte_bounds(raw):
    cell = binary_probability_cell(raw, byte_start=4, byte_order="little")
    assert cell["state"] == "invalid" and cell["probability"] is None
    assert cell["source"]["byte_end"] == 4 + len(raw)
    assert cell["source"]["raw_hex"] == raw.hex()


def test_h2_integer_tokens_and_reference_meanings_stay_distinct():
    unit = hmmer2_probability_cell("+000", reference={"kind": "unit"})
    assert unit["token"] == "+000" and unit["source"]["score"] == 0
    assert unit["probability"] == unit["source"]["nominal_probability"] == 1.0
    assert unit["negative_log_probability"] is None
    uniform = hmmer2_probability_cell("0", reference={"kind": "uniform_alphabet", "denominator": 4})
    assert uniform["probability"] == 0.25
    dependent = hmmer2_probability_cell("-1000", reference={"kind": "nule", "cell_index": 2}, reference_cell=uniform)
    assert dependent["probability"] == 0.125
    assert dependent["source"]["reference"] == {"kind": "nule", "cell_index": 2}
    assert uniform["source"]["reference"] == {"kind": "uniform_alphabet", "denominator": 4}


def test_h2_structural_zero_needs_no_emission_reference():
    cell = hmmer2_probability_cell("*", reference={"kind": "nule", "cell_index": 19})
    assert cell["probability"] == cell["source"]["nominal_probability"] == 0.0
    assert cell["source"]["score"] is None and cell["state"] == "structural_zero"
    missing = hmmer2_probability_cell("0", reference={"kind": "nule", "cell_index": 19})
    assert missing["state"] == "reference_missing"
    assert missing["probability"] is missing["source"]["nominal_probability"] is None


@pytest.mark.parametrize("token", ["1.0", "1e3", "nan", " 1", "1 ", "+", "", "**", "١"])
def test_h2_invalid_score_syntax_is_not_reinterpreted(token):
    cell = hmmer2_probability_cell(token, reference={"kind": "unit"})
    assert cell["state"] == "invalid" and cell["probability"] is None
    assert cell["token"] == token and cell["source"]["score"] is None


@pytest.mark.parametrize("reference", [{}, {"kind": "default"}, {"kind": "unit", "extra": 1},
    {"kind": "uniform_alphabet", "denominator": 0}, {"kind": "uniform_alphabet", "denominator": True},
    {"kind": "nule", "cell_index": -1}, {"kind": "nule", "cell_index": True}])
def test_h2_malformed_reference_is_distinct_from_absence(reference):
    assert hmmer2_probability_cell("0", reference=reference)["state"] == "invalid"
    assert hmmer2_probability_cell("*", reference=reference)["state"] == "invalid"


def test_h2_finite_out_of_range_nominal_and_underflow_are_not_clamped():
    high = hmmer2_probability_cell("1000", reference={"kind": "unit"})
    assert high["state"] == "quantized_out_of_range"
    assert high["probability"] is None and high["source"]["nominal_probability"] == 2.0
    low = hmmer2_probability_cell("-200000", reference={"kind": "unit"})
    assert low["state"] == "underflow"
    assert low["probability"] is low["source"]["nominal_probability"] is None
    assert low["source"]["score"] == -200000
    overflow = hmmer2_probability_cell("2000000", reference={"kind": "unit"})
    assert overflow["state"] == "invalid" and overflow["probability"] is None
    assert overflow["source"]["score"] == 2000000
    json.dumps([high, low, overflow], allow_nan=False)


def test_h2_exact_zero_nule_is_an_undefined_reference_not_underflow():
    zero = hmmer2_probability_cell("*", reference={"kind": "uniform_alphabet", "denominator": 20})
    cell = hmmer2_probability_cell("100", reference={"kind": "nule", "cell_index": 0}, reference_cell=zero)
    assert cell["state"] == "invalid" and cell["probability"] is None
    assert cell["source"]["nominal_probability"] == 0.0
    assert cell["source"]["score"] == 100
    positive = hmmer2_probability_cell("0", reference={"kind": "uniform_alphabet", "denominator": 20})
    underflow = hmmer2_probability_cell("-200000", reference={"kind": "nule", "cell_index": 0}, reference_cell=positive)
    assert underflow["state"] == "underflow" and underflow["source"]["nominal_probability"] is None


@pytest.mark.parametrize("mutation", ["nominal", "score", "probability", "reference"])
def test_h2_supplied_nule_must_match_its_own_source(mutation):
    null = hmmer2_probability_cell("0", reference={"kind": "uniform_alphabet", "denominator": 1})
    original = deepcopy(null)
    if mutation == "nominal":
        null["source"]["nominal_probability"] = True
    elif mutation == "score":
        null["source"]["score"] = False
    elif mutation == "probability":
        null["probability"] = True
    else:
        null["source"]["reference"] = {"kind": "unit"}
    assert hmmer2_probability_cell("0", reference={"kind": "nule", "cell_index": 0}, reference_cell=null)["state"] == "invalid"
    assert hmmer2_probability_cell("0", reference={"kind": "nule", "cell_index": 0}, reference_cell=original)["probability"] == 1
