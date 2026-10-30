"""Synthetic detached integrity checks; no literature/scientific execution."""
from copy import deepcopy
from pathlib import Path

import pytest

from gene_annotation_episode import literature_assay_inputs as custody
from gene_annotation_episode import literature_optical_calculations as calculator
from gene_annotation_episode import literature_optical_inputs as reader035
from gene_annotation_episode import literature_rate_native_inputs as lexical
from gene_annotation_episode.domain import identity
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_optical_validation import (
    ERROR_CODES, VERSION, validate_optical_extraction, validate_optical_selection,
)
from test_literature_optical_inputs import (
    ARTIFACT, SOURCE, TEXT, add_covariance, fixture, meaning, result, rows, witness,
)


def saved(*, cov=False, **kwargs):
    args, sources, reader, calls = fixture(**kwargs)
    if cov:
        add_covariance(args, sources, reader)
    return args, result(args, reader)


def reject(extraction, code=None):
    with pytest.raises(ExperimentalContractError) as failure:
        validate_optical_extraction(extraction)
    assert failure.value.code in ERROR_CODES
    if code:
        assert failure.value.code == "optical_validation_" + code
    assert failure.value.field


def test_detached_copies_and_frozen_version():
    args, extraction = saved(cov=True)
    before = deepcopy(extraction)
    validated = validate_optical_extraction(extraction)
    selected = validate_optical_selection(args, extraction)
    assert validated == before and selected == args
    assert VERSION == "a105_optical_saved_validation_v1"
    validated["signals"]["sample"]["number"]["selector"]["witness"]["quote"] = "changed"
    selected["signals"]["sample"]["qualification"]["witnesses"].clear()
    assert extraction == before and args["signals"]["sample"]["qualification"]["witnesses"]


def test_no_population_parser_calculator_source_or_file_access(monkeypatch):
    args, extraction = saved(cov=True)
    def forbidden(*a, **kw):
        pytest.fail("detached validation touched forbidden population/source/calculator")
    for module, names in ((reader035, ("read_optical_rate_operands", "_number", "_field_contexts", "_quantity", "_groups", "_covariance")),
                          (lexical, ("_number", "_field_contexts")),
                          (custody._Sources, ("source", "witness")),
                          (calculator, ("calculate_nadh_optical_rate", "_validate"))):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    assert validate_optical_extraction(extraction) == extraction
    assert validate_optical_selection(args, extraction) == args


@pytest.mark.parametrize("path", [(), ("context",), ("signals",), ("calibration",), ("signal_kind",),
    ("signals", "sample"), ("signals", "sample", "meanings"), ("signals", "sample", "qualification"),
    ("signals", "sample", "number"), ("signals", "sample", "number", "selector"),
    ("signals", "sample", "number", "selector", "witness"), ("signals", "sample", "unit"),
    ("covariance_source",), ("covariance_source", "data"), ("calculation_inputs",), ("input_unavailable_reasons",),
    ("dependencies", 0), ("lexical_dependency",)])
@pytest.mark.parametrize("mode", ["extra", "missing"])
def test_every_record_closed_and_every_field_required(path, mode):
    _, extraction = saved(cov=True)
    item = extraction
    for key in path:
        item = item[key]
    if mode == "extra":
        item["unsupported"] = "x"
    else:
        item.pop(next(iter(item)))
    reject(extraction)


@pytest.mark.parametrize("field", ["version", "source_kind", "signal_kind", "relation", "blank_role", "same_endpoint", "matched_window", "rate_window"])
def test_finite_root_interpretations(field):
    _, extraction = saved()
    if isinstance(extraction[field], dict):
        extraction[field]["value"] = "unrestricted meaning"
    else:
        extraction[field] = "unrecognized"
    reject(extraction, "enum")


@pytest.mark.parametrize("field,value", [("raw_number", "-0.01"), ("value", 10), ("value", True),
    ("value", float("nan")), ("value", float("inf")), ("value", 10**400),
    ("relation", "unknown"), ("approximate", 1)])
def test_forged_number_fields(field, value):
    _, extraction = saved()
    extraction["signals"]["sample"]["number"][field] = value
    reject(extraction)


@pytest.mark.parametrize("field,value", [("number_start", True), ("number_end", 10000), ("number_end", 0)])
def test_numeric_selector_indices_are_char_offsets(field, value):
    _, extraction = saved()
    extraction["signals"]["sample"]["number"]["selector"][field] = value
    reject(extraction, "number")


@pytest.mark.parametrize("field,value", [("start", True), ("start", -1), ("end", 1),
    ("quote", "forged"), ("quote", "\ud800"), ("artifact_ref", ""),
    ("source_ref", "not_a_ref"), ("representation", "json")])
def test_witness_shape_width_utf8_and_source_identity(field, value):
    _, extraction = saved()
    extraction["signals"]["sample"]["number"]["selector"]["witness"][field] = value
    reject(extraction)


@pytest.mark.parametrize("field,value", [("raw_unit", "mAU/min"), ("canonical_unit", "absorbance"),
    ("multiplier", 60), ("multiplier", True), ("unavailable_reason", "unknown")])
def test_forged_unit_projection(field, value):
    _, extraction = saved()
    extraction["signals"]["sample"]["unit"][field] = value
    reject(extraction, "unit")


@pytest.mark.parametrize("field,value", [("value", 9), ("value", False), ("status", "censored"),
    ("approximate", True), ("measurement_key", "forged"), ("physical_observation_key", "forged"),
    ("owner_key", "forged"), ("source_origin", "reported"), ("origin", "reported"),
    ("unavailable_reasons", ["invented"])])
def test_forged_quantity_relationships(field, value):
    _, extraction = saved()
    extraction["signals"]["sample"][field] = value
    reject(extraction, "quantity")


@pytest.mark.parametrize("kind", ["signal", "context", "qualification", "meaning"])
def test_semantic_owner_changes_cannot_inherit_old_key(kind):
    _, extraction = saved()
    if kind == "signal":
        extraction["signal_kind"]["value"] = "static_absorbance"
    elif kind == "context":
        extraction["context"]["molecule"] = deepcopy(extraction["signal_kind"]["witnesses"][0])
    elif kind == "qualification":
        extraction["signals"]["sample"]["qualification"]["value"] = "source_qualified_approximate"
    else:
        extraction["signals"]["sample"]["meanings"]["measured_entity"] = deepcopy(extraction["signal_kind"]["witnesses"][0])
    reject(extraction, "quantity")


def test_witness_binding_and_overlapping_bytes_consistent():
    _, extraction = saved()
    extraction["relation"]["witnesses"][0]["artifact_ref"] = "other"
    reject(extraction, "witness_binding")
    _, extraction = saved()
    w = extraction["relation"]["witnesses"][0]
    w["quote"] = "X" + w["quote"][1:]
    reject(extraction, "witness_overlap")


def test_known_and_conflicting_interpretations_require_distinct_witnesses():
    _, extraction = saved()
    extraction["relation"]["witnesses"].clear()
    reject(extraction, "interpretation")
    _, extraction = saved()
    extraction["relation"]["value"] = "conflicting"
    extraction["relation"]["witnesses"] *= 2
    reject(extraction, "interpretation")


@pytest.mark.parametrize("unknown", ["missing_sample", "missing_unit", "missing_measurement", "unsupported_unit", "unknown_qualification", "conflicting", "approximate", "bound", "unknown_signal", "unknown_covariance"])
def test_unknown_partial_censored_and_approximate_are_preserved(unknown):
    args, sources, reader, _ = fixture()
    if unknown == "missing_sample":
        args["signals"]["sample"] = None
    elif unknown == "missing_unit":
        args["signals"]["sample"]["measurement"]["unit"] = None
    elif unknown == "missing_measurement":
        args["signals"]["sample"]["measurement"] = None
    elif unknown == "unsupported_unit":
        text = TEXT.replace("-0.012 AU/min", "-0.012 arbitrary")
        args, sources, reader, _ = fixture(text, sample=("-0.012 arbitrary", "-0.012", "arbitrary"))
    elif unknown in ("unknown_qualification", "conflicting", "approximate"):
        q = {"unknown_qualification": "unknown", "conflicting": "conflicting", "approximate": "source_qualified_approximate"}[unknown]
        args["signals"]["sample"]["qualification"] = meaning(q, TEXT)
        if q == "conflicting":
            args["signals"]["sample"]["qualification"]["witnesses"].append(witness(TEXT, "NADH"))
    elif unknown == "bound":
        text = TEXT.replace("-0.012 AU/min", "about >=-0.012 AU/min")
        args, sources, reader, _ = fixture(text)
    elif unknown == "unknown_signal":
        args["signal_kind"] = meaning("unknown", TEXT)
    else:
        add_covariance(args, sources, reader, status="unknown")
    extraction = result(args, reader)
    assert validate_optical_extraction(extraction) == extraction
    assert validate_optical_selection(args, extraction) == args
    if unknown != "unknown_covariance":
        assert extraction["calculation_inputs"]["sample_slope"] is None
    else:
        assert extraction["calculation_inputs"]["covariance"] is not None
        assert extraction["calculation_inputs"]["covariance_status"] == "unknown"


@pytest.mark.parametrize("raw,number,unit", [("−0.012 absorbance min⁻¹", "−0.012", "absorbance min⁻¹"),
    ("-0.2 mAU/s", "-0.2", "mAU/s"), ("-0.012 AU min<sup>−1</sup>", "-0.012", "AU min<sup>−1</sup>")])
def test_utf8_token_absolute_identity_and_supported_units(raw, number, unit):
    text = "µ preface. " + TEXT.replace("-0.012 AU/min", raw)
    args, extraction = saved(text=text, sample=(raw, number, unit))
    assert validate_optical_selection(args, extraction) == args
    n = extraction["signals"]["sample"]["number"]
    w, ns = n["selector"]["witness"], n["selector"]
    expected = identity("literature_optical_measurement", {"source_ref": SOURCE, "artifact_ref": ARTIFACT,
        "start": w["start"] + len(w["quote"][:ns["number_start"]].encode()),
        "end": w["start"] + len(w["quote"][:ns["number_end"]].encode())})
    assert extraction["signals"]["sample"]["measurement_key"] == expected
    extraction["signals"]["sample"]["measurement_key"] = identity("literature_optical_measurement", {
        "source_ref": SOURCE, "artifact_ref": ARTIFACT, "start": w["start"] + ns["number_start"], "end": w["start"] + ns["number_end"]})
    if "−" in number:
        reject(extraction, "quantity")


@pytest.mark.parametrize("field", ["primitive_order", "primitive_measurement_keys", "primitive_physical_observation_keys", "primitive_owner_keys", "primitive_units"])
def test_covariance_owner_order_and_native_unit_snapshot(field):
    _, extraction = saved(cov=True)
    extraction["covariance_source"]["data"][field][0] = "forged"
    reject(extraction, "covariance_owner")


@pytest.mark.parametrize("matrix", [[[1]], [[True, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
    [[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
    [[1, 2, 0, 0], [2, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
    [[1, 0, 0, 0], [2, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
    [[float("nan"), 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]])
def test_invalid_saved_native_covariance_is_structured(matrix):
    _, extraction = saved(cov=True)
    extraction["covariance_source"]["data"]["covariance"] = matrix
    reject(extraction)


def test_canonical_covariance_cross_term_and_status_forgery():
    _, extraction = saved(cov=True)
    extraction["calculation_inputs"]["covariance"][2][2] = 10000
    reject(extraction, "calculation_inputs")
    _, extraction = saved(cov=True)
    extraction["calculation_inputs"]["covariance_status"] = "unknown"
    reject(extraction, "calculation_inputs")


def test_alias_groups_original_text_equal_values_and_physical_reuse():
    args, _, reader, _ = fixture()
    args["signals"]["blank"] = deepcopy(args["signals"]["sample"])
    args["signals"]["blank"]["measurement"]["number"]["witness"]["representation"] = "text"
    extraction = result(args, reader)
    assert validate_optical_selection(args, extraction) == args
    assert extraction["calculation_inputs"]["primitive_observation_refs"][0] == extraction["calculation_inputs"]["primitive_observation_refs"][1]
    extraction["dependencies"][0]["primitive_roles"] = ["sample_slope"]
    reject(extraction, "dependency")
    text = TEXT.replace("blank -0.002 AU/min", "blank -12 mAU/min")
    args, sources, reader, _ = fixture(text, blank=("-12 mAU/min", "-12", "mAU/min"))
    for row in args["signals"].values():
        row["measurement_identity"] = witness(text, "A single unnamed preparation")
    matrix = [[1e-8, 1e-5, 0, 0], [1e-5, .01, 0, 0], [0, 0, 10000, 0], [0, 0, 0, .01]]
    add_covariance(args, sources, reader, matrix=matrix)
    extraction = result(args, reader)
    assert validate_optical_selection(args, extraction) == args
    assert rows(extraction)[0]["measurement_key"] != rows(extraction)[1]["measurement_key"]
    # Valid native PSD matrix whose scaled rows disagree for a saved shared identity.
    extraction["covariance_source"]["data"]["covariance"][1][1] *= 2
    reject(extraction, "reuse")


@pytest.mark.parametrize("mutation", [lambda e: e["lexical_dependency"].update(sha256_at_release="0" * 64),
    lambda e: e["source_refs"].append(SOURCE), lambda e: e["source_refs"].append("source_" + "a" * 24),
    lambda e: e["source_refs"].reverse(), lambda e: e["calculation_inputs"].update(sample_slope=0),
    lambda e: e["calculation_inputs"].update(epsilon=True),
    lambda e: e["input_unavailable_reasons"].update(covariance=["invented"]),
    lambda e: e["calculation_inputs"]["primitive_observation_refs"].__setitem__(0, None)])
def test_dependency_roster_projection_and_reasons_cannot_drift(mutation):
    _, extraction = saved(cov=True)
    mutation(extraction)
    reject(extraction)


@pytest.mark.parametrize("path", [(), ("molecule",), ("signal_kind",), ("signals", "sample"),
    ("signals", "sample", "measurement"), ("signals", "sample", "measurement", "number"),
    ("signals", "sample", "measurement", "number", "witness"), ("calibration", "wavelength")])
def test_selection_exact_closed_inverse_enrichment(path):
    args, extraction = saved()
    if path == ("molecule",):
        args["molecule"] = witness(TEXT, "NADH")
    else:
        item = args
        for key in path:
            item = item[key]
        item["extra"] = "forged"
    with pytest.raises(ExperimentalContractError, match="optical_validation_selection"):
        validate_optical_selection(args, extraction)


def test_selection_boolean_offsets_do_not_equal_integer_zero():
    args, extraction = saved()
    args["signals"]["sample"]["measurement"]["number"]["number_start"] = False
    with pytest.raises(ExperimentalContractError, match="optical_validation_selection"):
        validate_optical_selection(args, extraction)


def test_saved_classifications_not_reinterpreted_from_unseen_surroundings():
    # Number witness deliberately excludes source-side qualifier; stored parser
    # classification is retained. Validation must not pretend to reacquire it.
    text = TEXT.replace("-0.012 AU/min", "about >=-0.012 AU/min")
    args, extraction = saved(text=text)
    assert extraction["signals"]["sample"]["number"]["relation"] == "ge"
    assert extraction["signals"]["sample"]["number"]["approximate"] is True
    assert validate_optical_selection(args, extraction) == args
