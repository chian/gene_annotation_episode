from copy import deepcopy
import pytest

from test_native_rna_structure_acquisition import F
from gene_annotation_episode.rna_structure_calculations import calculate_rna_feature_components
from gene_annotation_episode.rna_structure_result_views import (project_rna_prepublication,
    prepare_rna_structure_failure_selection, project_rna_structure_failure_rows,
    validate_rna_structure_result_selector)


def project(request, selected):
    sheet = F.CORE.feature_sheet(request)
    components = calculate_rna_feature_components(sheet, parameters=F.PARAMETERS)
    return project_rna_prepublication(sheet, components, selector=selected,
        components_sha256=F.sha(F.encoded(components)))


def test_numeric_coordinate_order_and_metric_order_are_not_selector_order():
    request = F.CORE.feature_input("(.).......(.)", "GACAAAAAAAGAC")
    keys = ["synthetic-rna:pair:10:12", "synthetic-rna:pair:0:2"]
    value, errors = project(request, F.selector("pair", ["pair_span_nt"], {"record_keys": keys}))
    assert [row["indices"] for row in value["rows"]] == [[0, 2], [10, 12]]
    assert [row["ordinal"] for row in value["rows"]] == [0, 1]
    assert [cell["name"] for cell in value["rows"][0]["cells"]] == ["pair_span_nt"]
    assert not errors and value["population_count"] == 2


@pytest.mark.parametrize("family,metrics", [("pair", ["pair_span_nt"]), ("stem", ["stem_length_pairs"]), ("region", ["loop_unpaired_nt"])])
def test_invalid_topology_has_unknown_population_not_zero(family, metrics):
    value, errors = project(F.CORE.feature_input("(]", "GC"), F.selector(family, metrics))
    assert value["population_count"] is None and value["rows"] == []
    assert value["requested_cells_accounted_for"] and errors[0]["field"] == "/selector/projection/rows"


def test_known_empty_pairs_missing_keys_and_empty_page_are_distinct():
    request = F.CORE.feature_input("....", "AAAA")
    value, errors = project(request, F.selector("pair", ["pair_span_nt"]))
    assert value["population_count"] == 0 and not value["rows"] and not errors
    value, errors = project(request, F.selector("pair", ["pair_span_nt"], {"record_keys": ["synthetic-rna:pair:0:3"]}))
    assert value["population_count"] == 0 and len(errors) == 1 and errors[0]["index"] == 0


def test_region_exterior_first_then_numeric_pairs_and_exact_hairpin_intervals():
    value, errors = project(F.CORE.feature_input(), F.selector("region", ["loop_unpaired_nt"]))
    assert [row["region_kind"] for row in value["rows"]] == ["exterior", "hairpin"]
    assert value["rows"][1]["closing_pair_key"] == "pair:2:6"
    assert value["rows"][1]["unpaired_intervals"] == [[3, 6]]
    assert value["rows"][1]["cells"][0]["value"] == 3


def test_failure_selection_is_frozen_with_supplemental_missing_keys():
    selected = F.selector("failure", [], {"record_keys": ["r:failure:1", "r:failure:8", "r:failure:0"]})
    original = [F.issue("rna_native_dependency_missing", stage="native", record_key="r"), F.issue("rna_capture_unavailable", stage="capture", record_key="r")]
    final = prepare_rna_structure_failure_selection(failures=original, selector=selected, record_key="r")
    assert final["selection"] == {"version": "rna_structure_failure_selection_v1", "population_count": 2,
        "selected_ordinals": [0, 1], "supplemental_issue_ordinals": [2], "requested_rows_accounted_for": True}
    receipt = {"run_id": "run", "episode_id": "child", "operation_key": "operation", "source_ref": None,
        "assignment": {"selector": selected}, "target": {"assignment": {"requested_job": {"native_rna_structure": {
            "record_key": "r", "mode": "supplied_features", "operation": "analyze_rna_secondary_structure_features"}}}},
        "failures": final["failures"], "failure_selection": final["selection"]}
    before = deepcopy(receipt)
    rows = project_rna_structure_failure_rows(receipt, selector=selected)
    assert [row["issue_ordinal"] for row in rows] == [0, 1, 2] and all(row["source_ref"] is None for row in rows)
    assert rows[2]["issue"]["field"] == "/selector/projection/rows/record_keys/1" and receipt == before
    receipt["failure_selection"]["selected_ordinals"].reverse()
    with pytest.raises(ValueError):
        project_rna_structure_failure_rows(receipt, selector=selected)


@pytest.mark.parametrize("mutation", [lambda x: x["projection"].update(metrics=["confidence"]),
    lambda x: x["projection"].update(metrics=["pair_count", "pair_count"]),
    lambda x: x["projection"].update(rows={"offset": True, "limit": 1}),
    lambda x: x["projection"].update(rows={"record_keys": ["a", "a"]}), lambda x: x.update(extra=True)])
def test_invalid_or_duplicate_selection_rejected(mutation):
    value = F.selector()
    mutation(value)
    with pytest.raises(ValueError):
        validate_rna_structure_result_selector(value, mode="supplied_features")
