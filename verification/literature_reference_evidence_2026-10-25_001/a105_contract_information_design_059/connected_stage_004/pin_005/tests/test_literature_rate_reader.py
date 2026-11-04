"""Synthetic table fixtures: parsing/custody checks, not biological evidence."""
from copy import deepcopy
import csv
import io
import json

import pytest

from gene_annotation_episode.literature_experimental_contracts import (
    ExperimentalContractError, HEADERS,
)
from gene_annotation_episode.literature_rate_reader import read_rate_table


def source_table(*, changes=None, headers=HEADERS, delimiter="\t", newline="\n",
                 extra_rows=()):
    row = dict(zip(HEADERS, (
        "ConstructX", "assay-1", "reference", "without inhibitor", "oxygen consumption",
        "preparation", "1.60e-1", "µmol/min", "sd", ".01", "3",
        "technical_measurements", "synthetic",
    )))
    row.update(changes or {})
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=delimiter, lineterminator=newline)
    writer.writerow(headers)
    writer.writerow([row[field] for field in headers])
    for extra in extra_rows:
        writer.writerow([extra.get(field, row[field]) for field in headers])
    return {"source_ref": "source_fixture", "artifact_ref": "artifact_fixture",
            "text": stream.getvalue(), "representation": "synthetic_fixture",
            "delimiter": delimiter}


def read(table):
    return read_rate_table(table, expected_subject="ConstructX", expected_experiment="assay-1")


@pytest.mark.parametrize("delimiter", ("\t", ","))
@pytest.mark.parametrize("newline", ("\n", "\r\n", "\r"))
def test_source_fields_numeric_values_and_physical_rows_are_retained(delimiter, newline):
    table = source_table(delimiter=delimiter, newline=newline,
                         extra_rows=({"arm": "test", "condition": "with inhibitor", "value": ".10"},))
    before = deepcopy(table)
    result = read(table)
    first, second = result["rows"]
    assert first["value"] == .16 and first["unit"] == "umol/min"
    assert first["uncertainty"] == {"kind": "sd", "magnitude": .01, "count": 3,
                                    "sampling_basis": "technical_measurements"}
    assert first["source"]["row_number"] == 2
    assert second["source"]["row_number"] == 3
    assert first["source"]["header"] == delimiter.join(HEADERS)
    assert "µmol/min" in first["source"]["raw_row"]
    assert second["condition"] == "with inhibitor"
    assert result == json.loads(json.dumps(result))
    assert table == before


def test_permuted_headers_retain_column_meanings():
    result = read(source_table(headers=tuple(reversed(HEADERS))))
    assert result["rows"][0]["value"] == .16
    assert result["rows"][0]["condition"] == "without inhibitor"


@pytest.mark.parametrize("field,token,code", (
    ("subject", "ConstructY", "source_subject_mismatch"),
    ("experiment", "assay-2", "source_experiment_mismatch"),
))
def test_wrong_subject_or_experiment_is_rejected_not_filtered(field, token, code):
    with pytest.raises(ExperimentalContractError) as error:
        read(source_table(extra_rows=({field: token},)))
    assert error.value.code == code


def test_swapped_header_without_swapped_values_is_detected():
    table = source_table()
    lines = table["text"].splitlines()
    headers = lines[0].split("\t")
    headers[0], headers[1] = headers[1], headers[0]
    table["text"] = "\t".join(headers) + "\n" + lines[1] + "\n"
    with pytest.raises(ExperimentalContractError, match="source_subject_mismatch"):
        read(table)


@pytest.mark.parametrize("token", ("True", "False", "NaN", "inf", "-Infinity", "1e9999",
                                   "1.2 ± .1", "1,000", "1/2", "<", "~"))
def test_invalid_or_nonfinite_measurement_tokens_fail(token):
    with pytest.raises(ExperimentalContractError):
        read(source_table(changes={"value": token}))


@pytest.mark.parametrize("token,bound,approx", (
    ("<.01", "lt", False), ("<=1e-2", "le", False),
    (">.01", "gt", False), (">= .01", "ge", False),
    ("~ < .01", "lt", True),
))
def test_censored_threshold_remains_a_limit(token, bound, approx):
    row = read(source_table(changes={"value": token}))["rows"][0]
    assert row["status"] == "censored"
    assert row["bound"] == bound and row["approximate"] is approx
    assert row["value"] == .01


def test_blank_mean_is_unavailable_not_zero():
    row = read(source_table(changes={"value": ""}))["rows"][0]
    assert row["value"] is None and row["status"] == "unavailable"
    assert row["bound"] == "none"
    assert row["uncertainty"]["magnitude"] == .01


def test_approximate_and_negative_observed_rates_remain_native():
    row = read(source_table(changes={"value": "~ -2.0e-3"}))["rows"][0]
    assert row["value"] == -.002 and row["approximate"]
    assert row["status"] == "observed"


@pytest.mark.parametrize("kind", ("sd", "sem", "unspecified"))
def test_error_statistic_is_preserved_without_conversion(kind):
    row = read(source_table(changes={"uncertainty_kind": kind}))["rows"][0]
    assert row["uncertainty"]["kind"] == kind
    assert row["uncertainty"]["magnitude"] == .01


def test_unknown_repetition_and_uncertainty_stay_unknown():
    row = read(source_table(changes={"count": "", "sampling_basis": "",
                                    "uncertainty_kind": "", "uncertainty_magnitude": ""}))["rows"][0]
    assert row["uncertainty"] == {"kind": "unreported", "magnitude": None,
                                    "count": None, "sampling_basis": "unspecified"}


def test_untyped_reported_error_magnitude_does_not_become_sd_or_sem():
    row = read(source_table(changes={"uncertainty_kind": ""}))["rows"][0]
    assert row["uncertainty"]["kind"] == "unspecified"
    assert row["uncertainty"]["magnitude"] == .01


@pytest.mark.parametrize("changes", (
    {"count": "0"}, {"count": "-1"}, {"count": "3.0"}, {"count": "True"},
    {"uncertainty_kind": "sd", "uncertainty_magnitude": ""},
    {"uncertainty_kind": "unreported", "uncertainty_magnitude": ".01"},
    {"uncertainty_kind": "CI"}, {"uncertainty_magnitude": "<.01"},
    {"uncertainty_magnitude": "-.01"}, {"uncertainty_magnitude": "NaN"},
    {"sampling_basis": "independent"}, {"unit": "units/min"},
))
def test_invalid_count_uncertainty_or_unit_is_not_reinterpreted(changes):
    with pytest.raises(ExperimentalContractError):
        read(source_table(changes=changes))


def test_identical_numbers_in_different_rows_are_not_deduplicated():
    rows = read(source_table(extra_rows=({},)))["rows"]
    assert len(rows) == 2
    assert rows[0]["value"] == rows[1]["value"]
    assert rows[0]["source"]["row_number"] != rows[1]["source"]["row_number"]


def test_conflicting_arm_summaries_are_retained_separately():
    rows = read(source_table(extra_rows=({"value": ".21"},)))["rows"]
    assert [row["value"] for row in rows] == [.16, .21]
    assert [row["arm"] for row in rows] == ["reference", "reference"]


@pytest.mark.parametrize("changes", ({"condition": "with\ninhibitor"}, {"endpoint": "line1\r\nline2"}))
def test_multiline_csv_cells_are_explicitly_unsupported(changes):
    with pytest.raises(ExperimentalContractError, match="multiline_csv_record_unsupported"):
        read(source_table(changes=changes))


def test_quoted_single_line_field_preserves_delimiters_and_quotes():
    row = read(source_table(delimiter=",", changes={"condition": 'buffer, "A"'}))["rows"][0]
    assert row["condition"] == 'buffer, "A"'
    assert '"buffer, ""A"""' in row["source"]["raw_row"]


@pytest.mark.parametrize("mutation", ("duplicate_header", "unknown_header", "missing_column", "extra_column"))
def test_malformed_table_shape_is_rejected(mutation):
    table = source_table()
    lines = table["text"].splitlines()
    if mutation == "duplicate_header":
        lines[0] = lines[0].replace("experiment", "subject")
    elif mutation == "unknown_header":
        lines[0] = lines[0].replace("experiment", "unrecognized")
    elif mutation == "missing_column":
        lines[1] = lines[1].rsplit("\t", 1)[0]
    else:
        lines[1] += "\textra"
    table["text"] = "\n".join(lines)
    with pytest.raises(ExperimentalContractError):
        read(table)


@pytest.mark.parametrize("changes", ({"delimiter": ";"}, {"representation": "inferred"},
                                     {"text": True}, {"artifact_ref": ""}))
def test_input_contract_rejects_invalid_table_metadata(changes):
    table = source_table()
    table.update(changes)
    with pytest.raises(ExperimentalContractError):
        read(table)


def test_synthetic_source_cannot_claim_reported_origin():
    with pytest.raises(ExperimentalContractError, match="synthetic_origin_required"):
        read(source_table(changes={"origin": "reported"}))


def test_retained_source_extraction_can_preserve_graph_derived_origin():
    table = source_table(changes={"origin": "graph_derived"})
    table["representation"] = "retained_extraction"
    row = read(table)["rows"][0]
    assert row["origin"] == "graph_derived"
    assert row["source"]["representation"] == "retained_extraction"


def test_unrepresentable_integer_token_returns_structured_failure():
    with pytest.raises(ExperimentalContractError) as error:
        read(source_table(changes={"count": "9" * 5000}))
    assert error.value.code == "integer_token_unrepresentable"


def test_header_only_table_does_not_invent_observations():
    table = source_table()
    table["text"] = table["text"].splitlines()[0] + "\n"
    result = read(table)
    assert result["rows"] == []
