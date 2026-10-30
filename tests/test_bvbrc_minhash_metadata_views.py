"""Synthetic saved-input projections; these fixtures do not prove live custody.

Only the existing parser/calculator builds the fixture's native scientific
sheet. Projection/replay itself must work with those functions and I/O disabled.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

import gene_annotation_episode.bvbrc_minhash_grader as grader
import gene_annotation_episode.bvbrc_minhash_views as views
from gene_annotation_episode.communication import (
    ReportBoundaryError, reference_resolver, validate_closed_schema, validate_form,
)
from test_bvbrc_minhash_views import (
    COUNTS, MATCHES, SOURCE, SOURCE_TWO, form_schema, no_external_work, qualified,
)


CALCULATIONS = "bvbrc_minhash_calculations"
DIAGNOSTICS = "bvbrc_minhash_calculation_diagnostics"
FAMILIES = (MATCHES, COUNTS, CALCULATIONS, DIAGNOSTICS)
METADATA_FIELDS = ("kmer_length", "query_length", "reference_length", "alphabet_size")
QUANTITIES = ("shared_hash_fraction", "recomputed_distance", "unsaturated_distance", "recomputed_pvalue")
METADATA_SOURCE = "source_" + "c" * 24
METADATA_DIGEST = "c" * 64
METADATA_ARTIFACT = "artifact_" + METADATA_DIGEST


def pair(index=0, genome="83333.1", *, mode="genome", values=None):
    """Explicitly synthetic source/evidence references, never host custody proof."""
    values = dict(zip(METADATA_FIELDS, (1, 2, 2, 2))) if values is None else values
    return {"row_index": index, "genome_id": genome, **values,
        "provenance": {"kind": "explicit_retained_pair_inputs", "query_mode": mode,
            "query_operand": "83333.1" if mode == "genome" else "/owner/workspace/input.fa",
            "native_parameter_equivalence": "unestablished",
            "fields": [{"field": field, "source_ref": METADATA_SOURCE,
                "artifact_ref": METADATA_ARTIFACT, "record_path": f"/pairs/{index}/{field}"}
                for field in METADATA_FIELDS if values[field] is not None]}}


def supplied(metadata=None, native=None, *, mode="genome", original=None):
    metadata = [pair(mode=mode)] if metadata is None else deepcopy(metadata)
    value = qualified(native, mode=mode) if original is None else deepcopy(original)
    saved = None
    if original is not None:
        saved = {"source_ref": original["source_ref"], "native_artifact_ref": "artifact_" + "d" * 64,
            "native_sha256": "d" * 64, "grading_artifact_ref": "artifact_" + "e" * 64,
            "grading_sha256": "e" * 64, "sheet": deepcopy(original["grading"]["sheet"]),
            "original_components": deepcopy(original["grading"]["components"])}
        value["source_ref"] = SOURCE_TWO
    selector = {"version": "bvbrc_minhash_result_selector_v2",
        "mode": "native_result" if saved is None else "saved_sheet",
        "saved_result_ref": None if saved is None else saved["source_ref"],
        "pair_metadata": deepcopy(metadata)}
    bindings = [{"pair_metadata_index": index, **deepcopy(evidence),
        "artifact_sha256": METADATA_DIGEST, "value": record[evidence["field"]]}
        for index, record in enumerate(metadata) for evidence in record["provenance"]["fields"]]
    grade = value["grading"]
    grade.update(schema="bvbrc_minhash_grading_v2", selector=selector,
        publication_inputs={"version": "bvbrc_minhash_publication_inputs_v1",
            "selector": deepcopy(selector), "pair_metadata": deepcopy(metadata),
            "metadata_bindings": bindings, "saved_result": saved},
        components=grader.calculate_minhash_components(grade["sheet"], pair_metadata=metadata))
    return value


def project(value, requested=FAMILIES):
    return views.project_minhash_facts([value], requested_sources=requested)


def test_optional_v1_calculations_preserve_existing_match_and_count_values():
    value = qualified([["83333.1", "0.02", "0.001", "41/1000"],
                       ["83333.1", "0.03", "0.002", "20/1000"]])
    before = deepcopy(value)
    legacy = project(value, (MATCHES, COUNTS))
    facts = project(value)
    assert {name: facts[name] for name in (MATCHES, COUNTS)} == legacy
    assert [row["shared_hash_fraction"] for row in facts[CALCULATIONS]] == [0.041, 0.02]
    for row in facts[CALCULATIONS]:
        assert all(row[name] is None for name in (*METADATA_FIELDS, *QUANTITIES[1:]))
        assert row["parse_status"] == "ok"
        assert row["native_parameter_equivalence"] == "unestablished"
        assert row["diagnostic_codes"] == ["pair_metadata_missing"]
    assert value == before


@pytest.mark.parametrize("mode", ["genome", "fasta"])
def test_every_requested_number_is_copied_from_saved_common_components(mode):
    value = supplied(mode=mode, native=[["83333.1", "0.223144", "0.259259", "2/3"]])
    before = deepcopy(value)
    result = project(value)
    row = result[CALCULATIONS][0]
    component = value["grading"]["components"]["rows"][0]
    assert row == {"source_ref": SOURCE, "row_index": 0, "genome_id": "83333.1",
        **{name: component[name] for name in QUANTITIES},
        **{name: component["calculation_inputs"][name] for name in METADATA_FIELDS},
        "native_parameter_equivalence": "unestablished", "parse_status": "ok", "diagnostic_codes": []}
    assert row["recomputed_distance"] == pytest.approx(0.22314355131420976)
    assert row["recomputed_pvalue"] == pytest.approx(0.2592592592592592)
    assert result[MATCHES][0]["reported_distance"] == 0.223144
    assert result[MATCHES][0]["reported_pvalue"] == 0.259259
    assert value["grading"]["sheet"]["native_result"][0][1:3] == ["0.223144", "0.259259"]
    assert value == before


@pytest.mark.parametrize("values,expected_distance,expected_missing", [
    ({"kmer_length": 1, "query_length": None, "reference_length": None, "alphabet_size": None},
     0.22314355131420976, 3),
    ({"kmer_length": None, "query_length": 2, "reference_length": 2, "alphabet_size": 2}, None, 1),
    (dict.fromkeys(METADATA_FIELDS), None, 4),
])
def test_explicit_missing_metadata_preserves_fraction_and_native_parse_status(values, expected_distance, expected_missing):
    value = supplied([pair(values=values)])
    row = project(value, (CALCULATIONS,))[CALCULATIONS][0]
    assert row["shared_hash_fraction"] == 2 / 3
    assert row["recomputed_distance"] == (None if expected_distance is None else pytest.approx(expected_distance))
    assert row["recomputed_pvalue"] is None
    assert row["parse_status"] == "ok"
    assert row["diagnostic_codes"] == ["missing_calculation_input"] * expected_missing
    assert {name: row[name] for name in METADATA_FIELDS} == values


@pytest.mark.parametrize("requested", [(), (COUNTS,), (MATCHES,), (CALCULATIONS,), (DIAGNOSTICS,)])
def test_only_explicit_requested_families_are_returned(requested):
    facts = project(supplied(), requested)
    assert set(facts) == set(requested)
    if requested == (COUNTS,):
        assert "83333.1" not in json.dumps(facts)
        assert "recomputed_distance" not in json.dumps(facts)


def test_reordered_metadata_and_duplicate_native_genomes_join_by_both_keys():
    metadata = [pair(1, values=dict(zip(METADATA_FIELDS, (2, 2, 2, 2)))), pair(0)]
    value = supplied(metadata, native=[["83333.1", 0.2, 0.3, "2/3"], ["83333.1", 0.2, 0.3, "2/3"]])
    rows = project(value)[CALCULATIONS]
    assert [(row["row_index"], row["genome_id"], row["kmer_length"]) for row in rows] == [
        (0, "83333.1", 1), (1, "83333.1", 2)]
    assert [row["recomputed_distance"] for row in rows] == pytest.approx([0.22314355131420976, 0.11157177565710488])
    assert [row["recomputed_pvalue"] for row in rows] == pytest.approx([0.2592592592592592, 0.10400000000000001])
    assert value["grading"]["publication_inputs"]["pair_metadata"] == metadata


def test_duplicate_pair_candidates_remain_ambiguous_and_retained():
    metadata = [pair(), pair()]
    value = supplied(metadata)
    row = project(value)[CALCULATIONS][0]
    assert row["shared_hash_fraction"] == 2 / 3
    assert all(row[name] is None for name in (*METADATA_FIELDS, *QUANTITIES[1:]))
    assert row["parse_status"] == "ok"
    assert row["diagnostic_codes"] == ["ambiguous_pair_metadata"]
    assert value["grading"]["components"]["rows"][0]["calculation_inputs"]["pair_metadata_candidates"] == metadata


def test_unmatched_metadata_diagnostics_remain_top_level_in_original_order():
    value = supplied([pair(4), pair(0, "83333.2"), pair()])
    facts = project(value)
    assert facts[CALCULATIONS][0]["diagnostic_codes"] == []
    expected = [
        {"source_ref": SOURCE, "code": "pair_metadata_row_index_mismatch", "path": "pair_metadata[0].row_index", "severity": "error"},
        {"source_ref": SOURCE, "code": "pair_metadata_genome_id_mismatch", "path": "pair_metadata[1].genome_id", "severity": "error"},
    ]
    assert facts[DIAGNOSTICS] == expected
    assert project(value, (CALCULATIONS,)) == {CALCULATIONS: facts[CALCULATIONS]}
    no_match = project(supplied([pair(4), pair(0, "83333.2")]))
    assert no_match[CALCULATIONS][0]["diagnostic_codes"] == ["pair_metadata_missing"]
    assert no_match[DIAGNOSTICS][:2] == expected


def test_empty_native_result_retains_unmatched_metadata_without_inventing_row():
    facts = project(supplied([pair()], native=[]))
    assert facts[CALCULATIONS] == facts[MATCHES] == []
    assert facts[COUNTS][0]["returned_row_count"] == 0
    assert [row["code"] for row in facts[DIAGNOSTICS]] == [
        "empty_result_completeness_unknown", "pair_metadata_row_index_mismatch"]


def test_zero_denominator_and_partial_native_rows_keep_distinct_availability():
    native = [["83333.1", 0, 1, "0/0"], ["83333.2", None, "bad", "2/3"],
              [None, 0, 1, "2/3"], ["unsupported identifier", 0.1, 0.01, "2/3"],
              ["83333.3", 0, 1, "bad"], ["83333.4", 0, 1, "4/3"]]
    value = supplied([pair(), pair(1, "83333.2"), pair(4, "83333.3"), pair(5, "83333.4")], native=native)
    facts = project(value)
    rows = facts[CALCULATIONS]
    assert [row["row_index"] for row in rows] == list(range(6))
    assert [row["parse_status"] for row in rows] == ["ok", "partial", "partial", "partial", "partial", "partial"]
    assert all(rows[0][name] is None for name in QUANTITIES)
    assert facts[MATCHES][0]["reported_distance"] == 0
    assert facts[MATCHES][0]["reported_pvalue"] == 1
    assert rows[1]["recomputed_distance"] is not None
    assert rows[1]["recomputed_pvalue"] is not None
    assert rows[2]["genome_id"] is rows[2]["shared_hash_fraction"] is None
    assert rows[3]["genome_id"] is None and rows[3]["shared_hash_fraction"] == 2 / 3
    assert all(rows[index][name] is None for index in (4, 5) for name in QUANTITIES)
    assert "native_result[1][1]" in [item["path"] for item in facts[DIAGNOSTICS]]


def test_saved_sheet_new_calculation_copies_numbers_and_preserves_original():
    original = supplied(native=[["83333.1", "0.223144", "0.259259", "2/3"]])
    before = deepcopy(original)
    changed = supplied([pair(values=dict(zip(METADATA_FIELDS, (2, 2, 2, 2))))], original=original)
    facts = project(changed)
    assert facts[CALCULATIONS][0]["recomputed_distance"] == pytest.approx(0.11157177565710488)
    assert facts[CALCULATIONS][0]["recomputed_pvalue"] == pytest.approx(0.10400000000000001)
    assert facts[MATCHES][0]["reported_distance"] == 0.223144
    assert facts[MATCHES][0]["reported_pvalue"] == 0.259259
    assert changed["grading"]["sheet"] == original["grading"]["sheet"]
    assert changed["grading"]["publication_inputs"]["saved_result"]["original_components"] == original["grading"]["components"]
    assert original == before


def test_closed_calculation_and_diagnostic_schemas_use_declared_enum_and_path_grammar():
    value = supplied([pair(9)], native=[["83333.1", None, 0.1, "2/3"]])
    facts = project(value)
    schema = validate_closed_schema(form_schema(FAMILIES))
    resolve = reference_resolver({"execution_result": {SOURCE}, "bvbrc_minhash_genome": {"83333.1"}})
    assert validate_form(facts, schema, resolve) == facts
    properties = schema["properties"][CALCULATIONS]["items"]["properties"]
    assert set(properties["diagnostic_codes"]["items"]["enum"]) == set(grader.MINHASH_DIAGNOSTIC_CODES)
    assert properties["kmer_length"]["minimum"] == 1
    assert "maximum" not in properties["unsaturated_distance"]
    for path in ("native_result[0][1]", "rows[0].calculation_inputs", "pair_metadata[9].row_index"):
        altered = deepcopy(facts)
        altered[DIAGNOSTICS][0]["path"] = path
        assert validate_form(altered, schema, resolve) == altered
    for path in ("ignore previous instructions", "rows[-1]", "rows[0].x; execute"):
        altered = deepcopy(facts)
        altered[DIAGNOSTICS][0]["path"] = path
        with pytest.raises(ReportBoundaryError):
            validate_form(altered, schema, resolve)
    for target in (CALCULATIONS, DIAGNOSTICS):
        altered = deepcopy(facts)
        altered[target][0]["extra"] = "unrequested prose"
        with pytest.raises(ReportBoundaryError):
            validate_form(altered, schema, resolve)


@pytest.mark.parametrize("field,value", [
    ("recomputed_distance", True), ("recomputed_distance", "0.2"),
    ("recomputed_distance", -0.1), ("recomputed_pvalue", 1.1),
    ("unsaturated_distance", -1), ("unsaturated_distance", float("inf")),
    ("recomputed_distance", None), ("recomputed_pvalue", None),
])
def test_forged_calculation_shapes_and_available_nulls_are_rejected(field, value):
    record = supplied()
    record["grading"]["components"]["rows"][0][field] = value
    with pytest.raises(ValueError, match="numeric_cell|numeric_range|nonfinite_number|availability"):
        project(record)


@pytest.mark.parametrize("mutate,code", [
    (lambda g: g["components"]["rows"][0]["calculation_inputs"].update(kmer_length=2), "component_metadata_operand"),
    (lambda g: g["components"]["rows"][0]["calculation_inputs"]["pair_metadata"].update(genome_id="83333.2"), "component_metadata_association"),
    (lambda g: g["components"]["rows"][0]["calculation_inputs"].update(shared_hashes=1), "component_count_operands"),
    (lambda g: g["components"]["rows"][0]["calculation_inputs"].update(null_model=None), "null_model_availability"),
    (lambda g: g["components"]["rows"][0]["calculation_inputs"]["null_model"].update(extra=1), "closed_fields"),
    (lambda g: g["publication_inputs"]["metadata_bindings"][0].update(pair_metadata_index=1), "minhash_publication_inputs_conflict"),
    (lambda g: g["publication_inputs"]["metadata_bindings"][0].update(value=True), "minhash_publication_inputs_conflict"),
    (lambda g: g["publication_inputs"]["metadata_bindings"][0].update(value="1"), "minhash_publication_inputs_conflict"),
    (lambda g: g["publication_inputs"]["metadata_bindings"][0].update(artifact_sha256="a" * 64), "minhash_publication_inputs_conflict"),
    (lambda g: g["selector"]["pair_metadata"][0].update(kmer_length=2), "minhash_publication_inputs_conflict"),
    (lambda g: g["publication_inputs"].update(extra="field"), "minhash_publication_inputs_conflict"),
    (lambda g: g["sheet"]["rows"].__setitem__(0, {}), "closed_fields"),
])
def test_forged_saved_associations_fail_before_projection(mutate, code):
    record = supplied()
    mutate(record["grading"])
    with pytest.raises(ValueError, match=code):
        project(record)


def test_forged_duplicate_candidates_and_unmatched_diagnostics_rejected():
    record = supplied([pair(), pair()])
    record["grading"]["components"]["rows"][0]["calculation_inputs"]["pair_metadata_candidates"].pop()
    with pytest.raises(ValueError, match="component_metadata_candidates"):
        project(record)
    record = supplied([pair(4), pair()])
    record["grading"]["components"]["diagnostics"].clear()
    with pytest.raises(ValueError, match="component_diagnostics_association"):
        project(record)
    record = supplied([pair(4), pair()])
    diagnostic = record["grading"]["components"]["diagnostics"][0]
    record["grading"]["components"]["rows"][0]["diagnostics"].append(deepcopy(diagnostic))
    with pytest.raises(ValueError, match="component_diagnostic_association"):
        project(record)


@pytest.mark.parametrize("code,path", [("arbitrary_prose", "rows[0]"),
    ("pair_metadata_missing", "rows[0]; command"), ("pair_metadata_missing", "rows[0]\n")])
def test_new_diagnostic_facts_reject_unbounded_code_or_path(code, path):
    record = supplied()
    diagnostic = {"code": code, "path": path, "severity": "error"}
    record["grading"]["components"]["rows"][0]["diagnostics"].append(deepcopy(diagnostic))
    record["grading"]["components"]["diagnostics"].append(deepcopy(diagnostic))
    with pytest.raises(ValueError, match="typed_diagnostic_fields"):
        project(record)


@pytest.mark.parametrize("values,native", [
    (dict.fromkeys(METADATA_FIELDS), None),
    (dict(zip(METADATA_FIELDS, (1, 2, 2, 2))), [["83333.1", 0, 1, "0/0"]]),
])
def test_unavailable_calculations_cannot_gain_forged_values(values, native):
    record = supplied([pair(values=values)], native=native)
    record["grading"]["components"]["rows"][0]["recomputed_distance"] = 0.0
    with pytest.raises(ValueError, match="distance_availability"):
        project(record)


def test_saved_sheet_must_match_the_selected_original_sheet():
    record = supplied(original=supplied())
    record["grading"]["publication_inputs"]["saved_result"]["sheet"]["provenance"]["extra"] = "changed"
    with pytest.raises(ValueError, match="saved_sheet_association"):
        project(record)


def test_metadata_query_must_match_original_service_operand():
    with pytest.raises(ValueError, match="minhash_metadata_query_conflict"):
        project(supplied([pair(mode="fasta")]))


def test_native_overlap_boundaries_copy_zero_and_unavailable_raw_distance():
    record = supplied([pair(), pair(1, "83333.2")],
        native=[["83333.1", 1, 1, "0/3"], ["83333.2", 0, 0, "3/3"]])
    rows = project(record)[CALCULATIONS]
    assert rows[0]["shared_hash_fraction"] == 0.0
    assert rows[0]["recomputed_distance"] == 1.0
    assert rows[0]["unsaturated_distance"] is None
    assert rows[0]["recomputed_pvalue"] == 1.0
    assert rows[1]["shared_hash_fraction"] == 1.0
    assert rows[1]["recomputed_distance"] == rows[1]["unsaturated_distance"] == 0.0
    for row, saved in zip(rows, record["grading"]["components"]["rows"]):
        assert {name: row[name] for name in QUANTITIES} == {name: saved[name] for name in QUANTITIES}


def test_new_declarations_and_requested_rows_are_detached():
    declarations = views.minhash_fact_sources()
    declarations[CALCULATIONS]["report_schema"]["items"]["properties"]["diagnostic_codes"]["items"]["enum"].clear()
    assert views.minhash_fact_sources()[CALCULATIONS]["report_schema"]["items"]["properties"]["diagnostic_codes"]["items"]["enum"]
    record = supplied([pair(9)])
    before = deepcopy(record)
    facts = project(record)
    facts[CALCULATIONS][0]["diagnostic_codes"].clear()
    facts[DIAGNOSTICS][0]["path"] = "changed"
    assert record == before


def test_projection_reuses_common_fraction_helper_and_copies_saved_result(monkeypatch):
    record = supplied()
    calls = []
    original = views.calculate_minhash_shared_hash_fraction
    def checked(shared, union, *, row_identity_available):
        calls.append((shared, union, row_identity_available))
        return original(shared, union, row_identity_available=row_identity_available)
    monkeypatch.setattr(views, "calculate_minhash_shared_hash_fraction", checked)
    assert project(record)[CALCULATIONS][0]["shared_hash_fraction"] == record["grading"]["components"]["rows"][0]["shared_hash_fraction"]
    assert calls == [(2, 3, True)]


def test_saved_projection_replay_with_full_parsers_calculators_and_io_disabled(monkeypatch):
    original = supplied()
    recalculated = supplied([pair(values=dict(zip(METADATA_FIELDS, (2, 2, 2, 2))))], original=original)
    records = [qualified(), original, recalculated,
               supplied([pair(9), pair()]), supplied([pair(), pair()])]
    frozen = json.loads(json.dumps(records, allow_nan=False))
    expected = [project(record) for record in frozen]
    def forbidden(*args, **kwargs):
        raise AssertionError("saved projection must not parse, calculate, read or acquire")
    monkeypatch.setattr(grader, "parse_minhash_result", forbidden)
    monkeypatch.setattr(grader, "calculate_minhash_components", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    assert [project(record) for record in records] == expected
    assert records == frozen
    expected[1][CALCULATIONS][0]["diagnostic_codes"].append("pair_metadata_missing")
    assert records == frozen
