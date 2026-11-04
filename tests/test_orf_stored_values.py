"""ORF stored-view controls, without native execution or publication authority.

The existing labelled supplied-data helpers and ORF reader/calculator produce
the numerical rows. Other cases explicitly damage or replace stored cells to
check selection/validation; they are not claims of native scientific output.
"""
from copy import deepcopy
import hashlib
import json

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import molecular_sequence_result_contracts as contracts
from gene_annotation_episode import orf_measurements as measurements
from test_orf_measurements import ROWS, native_fixture, operands


OPERATION = "annotate_open_reading_frames"
FIELDS = ("native_row", "orf_source_path", "protein_source_path", "omitted_stop_source_path")


def _produced(*, native_rows=None, args=None):
    sheet = measurements.build_orf_sheet(native_fixture(ROWS if native_rows is None else native_rows),
        **(operands() if args is None else args))
    return sheet, measurements.calculate_orf_components(sheet)


def _retained(document):
    # An in-memory file-state contract fixture, not a Store/custody proof.
    raw = json.dumps(document, sort_keys=True, allow_nan=False).encode()
    sha = hashlib.sha256(raw).hexdigest()
    file = dict(artifact_ref="artifact_" + sha, sha256=sha, size_bytes=len(raw), format="json")
    return dict(state="retained", file=file, declared=None,
        observed_identity=dict(sha256=sha, size_bytes=len(raw)), failure=None)


def _sources(sheet, components):
    sources = {role: contracts.empty_file_state() for role in contracts.FILE_ROLES}
    sources.update(sheet=_retained(sheet), components=_retained(components))
    return sources


def _select(sheet, components, *, requests=None, sources=None, mode="original_attempt"):
    sources = _sources(sheet, components) if sources is None else sources
    selected = dict(version=contracts.SELECTOR_VERSION, mode=mode, operation=OPERATION,
        saved_sheet_ref=sources["sheet"]["file"]["artifact_ref"] if mode == "saved_sheet_calculation" else None,
        rows=[dict(row_id=dict(kind="orf", row_index=0), fields=list(FIELDS))]
            if requests is None else requests, return_files=[])
    projection = contracts.select_stored_molecular_sequence_values(operation=OPERATION,
        sheet=sheet, components=components, selection=selected, source_files=sources)
    contracts.validate_molecular_sequence_projection(projection)
    _validate(projection["public"])
    return projection


def _validate(value):
    contracts.validate_molecular_sequence_fact_values(contracts.PROJECTION_SOURCE, [value])
    schema = contracts.molecular_sequence_fact_sources()[contracts.PROJECTION_SOURCE]["report_schema"]
    Draft202012Validator(schema).validate([value])


@pytest.mark.parametrize("objects", [False, True])
def test_original_native_representation_and_all_three_calculated_paths_are_copied(objects):
    native_rows = ([dict(zip(("sequence", "aa_sequence", "start", "end", "strand", "frame"), row))
        for row in ROWS] if objects else deepcopy(ROWS))
    sheet, components = _produced(native_rows=native_rows)
    before = deepcopy((sheet, components))
    projection = _select(sheet, components)
    rows = projection["public"]["rows"]
    assert [row["value"] for row in rows] == [components["rows"][0][field] for field in FIELDS]
    assert type(rows[0]["value"]) is (dict if objects else list)
    assert [row["source_pointer"] for row in rows] == ["/rows/0/" + field for field in FIELDS]
    assert [row["unit"] for row in rows] == ["native_field_units", *["per_segment_nt_or_symbol"] * 3]
    assert all(row["value_state"] == "stored_value" for row in rows)
    assert (sheet, components) == before


def test_reverse_compound_path_order_orientation_and_unspecified_units_survive():
    args = operands("TTACATTTTCAT", search_reverse=True)
    args["parent_mapping"]["path"] = [
        dict(subject_ref="source:a", start=20, end=24, unit="nt", strand="+"),
        dict(subject_ref="source:b", start=50, end=58, unit="symbol", strand="-")]
    sheet, components = _produced(native_rows=[
        ["ATGAAAATGTAA", "MKM", 0, 12, "-", -1], ["ATGTAA", "M", 0, 6, "-", -1]], args=args)
    rows = _select(sheet, components)["public"]["rows"]
    assert rows[0]["value"] == ["ATGAAAATGTAA", "MKM", 0, 12, "-", -1]
    assert rows[2]["value"] == [
        dict(subject_ref="source:b", start=50, end=58, unit="symbol", strand="+"),
        dict(subject_ref="source:a", start=23, end=24, unit="nt", strand="-")]
    assert rows[3]["value"] == [dict(subject_ref="source:a", start=20, end=23, unit="nt", strand="-")]


def test_native_coordinate_conflicts_are_literal_not_repaired_or_used_as_validated_geometry():
    native_row = ["ATGAAAATGTAA", "MKM", -3, 99, "+", 1]
    sheet, components = _produced(native_rows=[native_row, ROWS[1]])
    rows = _select(sheet, components)["public"]["rows"]
    assert rows[0]["value_state"] == "stored_value" and rows[0]["value"] == native_row
    assert components["rows"][0]["interval"] is None
    assert all(row["value_state"] == "stored_null" for row in rows[1:])


@pytest.mark.parametrize("raw", [
    ["ATGTAA", "M", 0, 6, "+"],
    ["ATGTAA", "M", False, 6, "+", 1],
    ["ATGTAA", None, 0, 6, "+", 1],
    ["ATGTAA", "M", 0, 6, "?", 1],
    ["ATGTAA", "M", 0, 6, "+", True],
    dict(sequence="ATGTAA", aa_sequence="M", start=0, end=6, strand="+", frame=1, extra="unselected"),
])
def test_malformed_native_row_keeps_its_ordinal_and_does_not_compact_a_valid_sibling(raw):
    sheet, components = _produced(native_rows=[raw, ROWS[1]])
    requests = [dict(row_id=dict(kind="orf", row_index=i), fields=list(FIELDS)) for i in (1, 0)]
    rows = _select(sheet, components, requests=requests)["public"]["rows"]
    assert [row["row_id"]["row_index"] for row in rows] == [1] * 4 + [0] * 4
    assert rows[0]["value"] == ROWS[1]
    assert rows[4]["value_state"] == "invalid_type" and rows[4]["value"] is None
    assert rows[4]["source_pointer"] == "/rows/0/native_row"
    assert components["rows"][0]["native_row"] == raw


def test_missing_mapping_stays_null_with_native_fields_and_row_qualifications_intact():
    args = operands(); args["parent_mapping"] = None
    sheet, components = _produced(args=args)
    rows = _select(sheet, components)["public"]["rows"]
    assert rows[0]["value"] == ROWS[0]
    assert [(row["value_state"], row["value"]) for row in rows[1:]] == [("stored_null", None)] * 3
    assert rows[0]["scientific_qualifiers"]["states"]["component_status"]["value"] == "partial"
    assert rows[0]["scientific_qualifiers"]["states"]["reported_row_count"]["value"] == 2


def test_empty_path_null_missing_invalid_and_unavailable_source_remain_distinct():
    sheet, components = _produced()
    components["rows"][0].update(orf_source_path=[], protein_source_path=None)
    del components["rows"][0]["omitted_stop_source_path"]
    rows = _select(sheet, components)["public"]["rows"]
    assert [(row["value_state"], row["value"]) for row in rows[1:]] == [
        ("stored_value", []), ("stored_null", None), ("path_missing", None)]
    components["rows"][0]["orf_source_path"] = [dict(subject_ref="source:a", start=0, end=0, unit="nt", strand="+")]
    assert _select(sheet, components)["public"]["rows"][1]["value_state"] == "invalid_type"
    sources = _sources(sheet, components)
    sources["components"] = contracts.empty_file_state("retention_failed",
        issue=contracts.failure("retention_failed", "capture", role="components"))
    rows = _select(sheet, components, sources=sources)["public"]["rows"]
    assert all(row["value_state"] == "source_unavailable" and row["source_ref"] is None for row in rows)


@pytest.mark.parametrize("path", [
    {},
    [dict(subject_ref="source:a", start=0, end=3, unit="aa", strand="+")],
    [dict(subject_ref="", start=0, end=3, unit="nt", strand="+")],
    [dict(subject_ref="source:a", start=True, end=3, unit="nt", strand="+")],
    [dict(subject_ref="source:a", start=4, end=3, unit="nt", strand="+")],
    [dict(subject_ref="source:a", start=0, end=3, unit="nt", strand="+", extra=1)],
])
def test_path_selection_reuses_closed_source_traversal_validation(path):
    sheet, components = _produced()
    components["rows"][0]["protein_source_path"] = deepcopy(path)
    row = _select(sheet, components)["public"]["rows"][2]
    assert row["value_state"] == "invalid_type" and row["value"] is None
    assert components["rows"][0]["protein_source_path"] == path


@pytest.mark.parametrize("field,value", [
    ("native_row", {"arbitrary": "object"}),
    ("native_row", ["ATGTAA", "M", 0, 6, "+", 1, "extra"]),
    ("native_row", ["ATGTAA", "M", 0, 6, "+", False]),
    ("protein_source_path", [dict(subject_ref="source:a", start=0, end=3, unit="aa", strand="+")]),
    ("orf_source_path", [dict(subject_ref="source:a", start=0, end=3, unit="nt", strand="+", extra=1)]),
])
def test_semantic_fact_validator_and_json_schema_reject_unconstrained_structured_values(field, value):
    sheet, components = _produced()
    public = _select(sheet, components)["public"]
    selected = next(row for row in public["rows"] if row["field"] == field)
    selected.update(value_state="stored_value", value=value)
    with pytest.raises(ValueError):
        contracts.validate_molecular_sequence_fact_values(contracts.PROJECTION_SOURCE, [public])
    schema = contracts.molecular_sequence_fact_sources()[contracts.PROJECTION_SOURCE]["report_schema"]
    assert not Draft202012Validator(schema).is_valid([public])


@pytest.mark.parametrize("field", FIELDS)
def test_structured_field_units_cannot_relabel_original_symbol_ancestry(field):
    sheet, components = _produced()
    public = _select(sheet, components)["public"]
    selected = next(row for row in public["rows"] if row["field"] == field)
    selected["unit"] = "aa"
    with pytest.raises(ValueError):
        contracts.validate_molecular_sequence_fact_values(contracts.PROJECTION_SOURCE, [public])
    schema = contracts.molecular_sequence_fact_sources()[contracts.PROJECTION_SOURCE]["report_schema"]
    assert not Draft202012Validator(schema).is_valid([public])


def test_saved_corrupt_row_stays_at_original_index_with_paths_missing_not_reconstructed():
    sheet, _components = _produced()
    sheet["rows"][0]["protein_source_path"][0]["subject_ref"] = "unrelated:source"
    components = measurements.calculate_orf_components(sheet)
    requests = [dict(row_id=dict(kind="orf", row_index=i), fields=list(FIELDS)) for i in (0, 1)]
    rows = _select(sheet, components, requests=requests)["public"]["rows"]
    assert all(row["value_state"] == "path_missing" for row in rows[:4])
    assert rows[4]["row_id"] == dict(kind="orf", row_index=1)
    assert rows[4]["value"] == ROWS[1]
    assert components["rows"][0]["state"] == "incompatible"


@pytest.mark.parametrize("mode", ["original_attempt", "saved_sheet_calculation"])
def test_stored_selection_never_rebuilds_calculates_translates_or_changes_saved_rows(monkeypatch, mode):
    sheet, components = _produced()
    sheet, components = json.loads(json.dumps((sheet, components)))
    before = deepcopy((sheet, components))
    def forbidden(*_args, **_kwargs):
        pytest.fail("stored selection attempted scientific production")
    monkeypatch.setattr(measurements, "build_orf_sheet", forbidden)
    monkeypatch.setattr(measurements, "calculate_orf_components", forbidden)
    monkeypatch.setattr(measurements, "_translation", forbidden)
    _select(sheet, components, mode=mode)
    assert (sheet, components) == before


def test_existing_selectors_zero_values_and_other_operation_field_sets_are_preserved():
    sheet, components = _produced(native_rows=[])
    requests = [dict(row_id=dict(kind="summary"), fields=["reported_row_count",
        "retained_length_sum_nt", "retained_length_denominator_rows", "mean_retained_orf_length_nt"])]
    rows = _select(sheet, components, requests=requests)["public"]["rows"]
    assert [(row["value_state"], row["value"]) for row in rows] == [
        ("stored_value", 0), ("stored_value", 0), ("stored_value", 0), ("stored_null", None)]
    assert contracts.field_table(OPERATION, dict(kind="orf", row_index=8))["interval"] == (
        "/rows/8/interval", "interval", "zero_based_input_nt_symbol_indices", "orf_retained_row", ())
    for operation, identity in ((contracts.OPERATIONS[1], dict(kind="placement_hit", group_ordinal=0, native_hit_ordinal=0)),
            (contracts.OPERATIONS[2], dict(kind="glycosylation_site", row_ordinal=0)),
            (contracts.OPERATIONS[3], dict(kind="glycosylation_site", row_ordinal=0)),
            (contracts.OPERATIONS[4], dict(kind="protease_fit"))):
        assert not set(FIELDS).intersection(contracts.field_table(operation, identity))
