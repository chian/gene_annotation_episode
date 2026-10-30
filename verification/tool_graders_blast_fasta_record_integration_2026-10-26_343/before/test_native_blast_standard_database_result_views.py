"""R333 closed numerical forms and frozen-row projection tests."""
from copy import deepcopy
import pytest

from gene_annotation_episode import native_blast_standard_database_result_views as v
from gene_annotation_episode import native_blast_standard_database_calculators as c
from gene_annotation_episode.domain import validate_schema
from test_native_blast_standard_database_calculators import calculate, cell, family, fixture, numerical
from test_native_blast_standard_database_metadata import assert_pure


def selector(name="hsp", *, rows=None, metrics=None, booleans=None):
    return dict(version=v.PREFIX + "selector_v1", acquisition="complete_bound_bundle", metadata_inputs=[], retained_sources=[],
        projections=[dict(family=name, rows=rows or dict(offset=0, limit=10), metrics=metrics or ["native_score_bits"], booleans=booleans or [])])


def test_R6_definitions_full_rows_and_fact_schema_are_closed():
    _, _, rows = calculate(numerical())
    definitions = v.standard_blast_database_metric_definitions()
    assert set(definitions) == set(v.FAMILIES) and len(definitions) == 12
    assert "iteration" not in str(definitions)
    for names in definitions.values():
        for definition in names.values():
            assert set(definition) == {"inputs", "formula", "units", "population", "denominator", "origin", "coordinates", "uncertainty", "missingness"}
    sources = v.standard_blast_database_fact_sources()
    for row in rows:
        v._validate_row(row, "a" * 64)
        assert [x["name"] for x in row["measurements"]] == list(definitions[row["family"]])
        source = sources["execution_blast_standard_database_" + row["family"] + "_rows"]
        published = dict(row, source_ref="source-1", observation_ref=None, subject_ref=None, reference_refs=[], publication_status="source_only")
        validate_schema([published], source["report_schema"])
        with pytest.raises(ValueError): validate_schema([dict(published, invented="yes")], source["report_schema"])
    assert sources["execution_blast_standard_database_failures"]["report_schema"]["items"] == v.FAILURE_SCHEMA


@pytest.mark.parametrize("change", ["empty", "old_tag", "model", "unknown_family", "unknown_metric", "duplicate_family", "float_offset", "mixed_rows", "empty_selection", "unregistered_metadata", "duplicate_source"])
def test_R6_selector_rejects_unbounded_or_ineligible_requests(change):
    value = selector()
    p = value["projections"][0]
    if change == "empty": value["projections"] = []
    if change == "old_tag": value["version"] = "native_blast_database_selector_v1"
    if change == "model": value["sequence_model"] = None
    if change == "unknown_family": p["family"] = "iteration_summary"
    if change == "unknown_metric": p["metrics"] = ["confidence"]
    if change == "duplicate_family": value["projections"].append(deepcopy(p))
    if change == "float_offset": p["rows"]["offset"] = 0.0
    if change == "mixed_rows": p["rows"]["record_keys"] = ["one"]
    if change == "empty_selection": p["metrics"] = []
    if change == "unregistered_metadata": value["metadata_inputs"] = [dict(input_key="m", consumer="query_identity", schema_id="native_blast_database_sequence_metadata_v1", artifact_ref="a", sha256="b" * 64, size_bytes=1)]
    if change == "duplicate_source": value["retained_sources"] = [dict(source_ref="s", artifact_ref="a", sha256="b" * 64, size_bytes=1)] * 2
    with pytest.raises(ValueError): v.validate_standard_blast_database_selector(value, program="blastp")


def test_R6_pssm_family_only_for_tblastn():
    value = selector("pssm_cell", metrics=["scores"])
    assert v.validate_standard_blast_database_selector(value, program="tblastn") == value
    for program in ("blastn", "blastp", "blastx", "tblastx"):
        with pytest.raises(ValueError): v.validate_standard_blast_database_selector(value, program=program)


def test_R9_projection_never_parses_calculates_or_reads_files(monkeypatch):
    _, _, rows = calculate(numerical()); original = deepcopy(rows)
    def forbidden(*a, **kw): raise AssertionError("projection called calculation")
    monkeypatch.setattr(c, "calculate_standard_blast_database_sheets", forbidden)
    monkeypatch.setattr(c._sequence, "calculate_blast_sequence_database_components", forbidden)
    with monkeypatch.context() as blocked:
        assert_pure(blocked)
        projected = v.project_standard_blast_database_rows(rows, selector=selector(metrics=["native_evalue", "native_score_bits"]), calculation_id="a" * 64)
    selected = projected["families"][0]["rows"]
    assert [x["name"] for x in selected[0]["measurements"]] == ["native_evalue", "native_score_bits"]
    assert cell(selected[0], "native_evalue")["value"] == 0.0
    assert rows == original
    projected["families"][0]["rows"][0]["measurements"][0]["value"] = 42
    assert rows == original


def test_R9_pagination_explicit_order_and_missing_key():
    _, _, rows = calculate(fixture()); hsps = family(rows, "hsp")
    selected = v.project_standard_blast_database_rows(rows, selector=selector(rows=dict(record_keys=[hsps[1]["record_key"], hsps[0]["record_key"]])), calculation_id="a" * 64)
    assert [cell(r, "native_score_bits")["value"] for r in selected["families"][0]["rows"]] == [18, 20]
    empty = v.project_standard_blast_database_rows(rows, selector=selector(rows=dict(offset=999, limit=1)), calculation_id="a" * 64)
    assert not empty["families"][0]["rows"] and not empty["failures"]
    missing = v.project_standard_blast_database_rows(rows, selector=selector(rows=dict(record_keys=["missing"])), calculation_id="a" * 64)
    assert missing["failures"][0]["code"] == v.PREFIX + "selector_unavailable"
    assert missing["failures"][0]["detail_code"] == "explicit_row_missing"
    for altered in ([*rows, rows[0]], [dict(rows[0], calculation_id="b" * 64), *rows[1:]]):
        with pytest.raises(ValueError): v.project_standard_blast_database_rows(altered, selector=selector(), calculation_id="a" * 64)
