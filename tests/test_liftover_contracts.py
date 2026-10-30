"""Pure engineered records of documented PyLiftover point-result shapes.

No native converter, chain file, installation, host publication, custody or
episode is exercised. Version labels/observations below are supplied fixtures,
not proof of an executed producer. The proposed fact schema is unregistered.
"""
import builtins
from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import liftover_contracts as c


def request():
    return dict(version=c.REQUEST_VERSION, chain=dict(file=dict(artifact_ref="artifact_" + "a" * 64,
        sha256="a" * 64, size_bytes=73, format="ucsc_chain"), source_ref="source_" + "b" * 24),
        point=dict(chromosome="contig.literal", position_0based=0, strand="+"))


def observed(native, *, selected=None, state="returned", count=1, captured=True, failure=None):
    selected = request() if selected is None else selected
    return dict(version=c.OBSERVATION_VERSION, request_sha256=c.liftover_request_sha256(selected),
        chain_file=deepcopy(selected["chain"]["file"]), software=dict(name="pyliftover", version="0.4.1"),
        conversion_call_state=state, conversion_call_count=count,
        result_state="captured" if captured else "unavailable", native_result=native, failure=failure)


def failure(code):
    return dict(stage=c.FAILURES[code], code=code, exception_type=None, exception_message=None)


def sheet(native, **kwargs):
    return c.populate_liftover_sheet(request(), native_observation=observed(native, **kwargs))


def returned(components):
    return c.project_liftover_return(components, source_ref="source_" + "c" * 24)


@pytest.mark.parametrize("contig,position,strand,format", [
    ("1", 0, "+", "ucsc_chain"), ("chr1", 1, "-", "ucsc_chain_gzip"),
    ("AP012306.1", 16000, "+", "ucsc_chain"), ("scaffold:alt_2", 2**40, "-", "ucsc_chain_gzip")])
def test_literal_point_and_single_chain_identity_are_preserved(contig, position, strand, format):
    value = request(); value["point"] = dict(chromosome=contig, position_0based=position, strand=strand)
    value["chain"]["file"]["format"] = format
    original = deepcopy(value)
    assert c.validate_liftover_request(value) == original
    Draft202012Validator(c.liftover_request_schema()).validate(value)
    populated = c.populate_liftover_sheet(value, native_observation=observed(None, selected=value))
    assert populated["request"] == original and value == original
    assert populated["assembly_context"] == {
        "source": {"state": "unavailable", "label": None, "reason": "not_provided"},
        "target": {"state": "unavailable", "label": None, "reason": "not_provided"}}


@pytest.mark.parametrize("path,value", [
    (("point", "position_0based"), True), (("point", "position_0based"), 1.0),
    (("point", "position_0based"), -1), (("point", "chromosome"), ""),
    (("point", "chromosome"), "chr\x001"), (("point", "strand"), "."),
    (("chain", "file", "size_bytes"), False), (("chain", "file", "size_bytes"), 73.0),
    (("chain", "file", "size_bytes"), -1), (("chain", "file", "format"), "auto"),
    (("chain", "file", "artifact_ref"), "artifact_" + "f" * 64),
    (("chain", "file", "sha256"), "A" * 64), (("chain", "source_ref"), "artifact_" + "b" * 64)])
def test_invalid_request_types_or_file_identity_are_not_coerced(path, value):
    selected = request(); parent = selected
    for key in path[:-1]: parent = parent[key]
    parent[path[-1]] = value
    with pytest.raises(ValueError): c.validate_liftover_request(selected)


def test_no_free_form_assembly_labels_or_implicit_conversion_settings():
    selected = request(); selected["input_format"] = "hg19"
    with pytest.raises(ValueError): c.validate_liftover_request(selected)
    selected = request(); selected["chain"]["source_ref"] = None
    assert c.validate_liftover_request(selected)["chain"]["source_ref"] is None
    assert c.liftover_request_sha256(selected) != c.liftover_request_sha256(request())


@pytest.mark.parametrize("native,state,rows,mappings", [
    (None, "chromosome_not_in_chain", None, None), ([], "unmapped_under_selected_chain", 0, 0),
    ([("target", 0, "-", 0)], "unique", 1, 1),
    ([("same", 7, "+", 3), ("same", 7, "+", 3)], "multiple", 2, 2),
    ({"unexpected": "object"}, "native_result_invalid", None, None)])
def test_none_empty_valid_multiplicity_and_wrong_top_level_remain_distinct(native, state, rows, mappings):
    components = c.calculate_liftover_components(sheet(native))
    population = components["population"]
    assert population["requested_point_count"] == 1 and population["point_state"] == state
    assert population["native_row_count"] == rows and population["mapping_count"] == mappings
    assert population["conversion_call_scope"] == c.CALL_SCOPE
    assert population["conversion_call_state"] == "returned" and population["conversion_call_count"] == 1
    assert [row["ordinal"] for row in components["rows"]] == list(range(rows or 0))


@pytest.mark.parametrize("score", [0, -7, 2**80 + 1, 10**400 + 3])
def test_native_integer_score_precision_order_and_zero_are_retained(score):
    native = [("target:Z", 0, "-", score), ("target:A", 12, "+", score - 1)]
    populated = sheet(native)
    assert populated["observation"]["native_result"] == [list(row) for row in native]
    result = returned(c.calculate_liftover_components(populated))
    assert [row["native_chain_score"] for row in result["rows"]] == [score, score - 1]
    assert all(type(row["native_chain_score"]) is int for row in result["rows"])
    assert result["rows"][0]["target_position_0based"] == 0


@pytest.mark.parametrize("malformed,code", [
    (False, "native_tuple_type_invalid"), ([], "native_tuple_width_invalid"),
    (["target", 3, "+"], "native_tuple_width_invalid"),
    (["target", 3, "+", 1, "extra"], "native_tuple_width_invalid"),
    ([None, 3, "+", 1], "native_target_chromosome_invalid"),
    (["target", True, "+", 1], "native_target_position_invalid"),
    (["target", 3.0, "+", 1], "native_target_position_invalid"),
    (["target", -1, "+", 1], "native_target_position_invalid"),
    (["target", 3, ".", 1], "native_target_strand_invalid"),
    (["target", 3, "+", False], "native_chain_score_invalid"),
    (["target", 3, "+", 1.0], "native_chain_score_invalid"),
    (["target", 3, "+", "1"], "native_chain_score_invalid")])
def test_malformed_rows_preserve_original_ordinals_raw_cells_and_independent_valid_rows(malformed, code):
    native = [["left", 4, "+", 9], malformed, ["right", 8, "-", 7]]
    populated = sheet(native)
    assert populated["observation"]["native_result"] == native
    assert populated["parsing_state"] == "partial"
    assert populated["issues"] == [{"code": code, "row_ordinal": 1}]
    assert [row["ordinal"] for row in populated["rows"]] == [0, 1, 2]
    assert populated["rows"][1]["state"] == "invalid"
    components = c.calculate_liftover_components(populated, mapping_ordinals=[2, 0])
    assert [row["ordinal"] for row in components["rows"]] == [2, 0]
    assert components["population"]["native_row_count"] == 3
    assert components["population"]["valid_mapping_count"] == 2
    assert components["population"]["mapping_count"] is None
    assert components["population"]["point_state"] == "native_rows_invalid"
    assert components["sheet"]["observation"]["conversion_call_state"] == "returned"


@pytest.mark.parametrize("selection", [[2, 0], [1], []])
def test_explicit_selection_never_turns_original_multiple_into_unique_or_unmapped(selection):
    populated = sheet([["C", 8, "+", 30], ["A", 2, "-", 20], ["C", 8, "+", 10]])
    components = c.calculate_liftover_components(populated, mapping_ordinals=selection)
    assert components["population"]["point_state"] == "multiple"
    assert components["population"]["mapping_count"] == 3
    assert [row["ordinal"] for row in returned(components)["rows"]] == selection


@pytest.mark.parametrize("selection", [[0, 0], [-1], [True], [0.0], [2], (0,), "0"])
def test_selection_requires_unique_exact_original_ordinals(selection):
    with pytest.raises(ValueError, match="liftover_mapping_ordinal_invalid"):
        c.calculate_liftover_components(sheet([["T", 1, "+", 1]]), mapping_ordinals=selection)


@pytest.mark.parametrize("state,count,code,point_state", [
    ("not_started", 0, "input_unavailable", "not_started"),
    ("not_started", 0, "chain_parse_failed", "not_started"),
    ("raised", 1, "coordinate_conversion_failed", "conversion_failed"),
    ("uncertain", None, "execution_unconfirmed", "execution_unconfirmed"),
    ("uncertain", None, None, "execution_unconfirmed"),
    ("returned", 1, "native_result_capture_failed", "result_unavailable")])
def test_call_scope_failure_and_unavailable_capture_never_become_zero_mappings(state, count, code, point_state):
    populated = sheet(None, state=state, count=count, captured=False, failure=None if code is None else failure(code))
    result = returned(c.calculate_liftover_components(populated))
    assert result["population"]["point_state"] == point_state
    assert result["population"]["conversion_call_count"] == count
    assert count is None or type(result["population"]["conversion_call_count"]) is int
    assert result["population"]["mapping_count"] is None and result["rows"] == []
    if code is None:
        assert result["failure"] is None
    else:
        assert result["failure"]["code"] == code


@pytest.mark.parametrize("field,value", [("conversion_call_count", True), ("conversion_call_count", 1.0),
    ("conversion_call_count", 0), ("conversion_call_count", None), ("conversion_call_state", "uncertain"),
    ("request_sha256", "0" * 64), ("result_state", "unavailable")])
def test_contradictory_native_call_or_original_request_identity_is_rejected(field, value):
    native = observed([]); native[field] = value
    with pytest.raises(ValueError): c.populate_liftover_sheet(request(), native_observation=native)


def test_original_chain_identity_and_failure_relationships_are_closed():
    native = observed([]); native["chain_file"]["size_bytes"] = 74
    with pytest.raises(ValueError, match="identity_conflict"):
        c.populate_liftover_sheet(request(), native_observation=native)
    native = observed([], failure=failure("coordinate_conversion_failed"))
    with pytest.raises(ValueError, match="captured_result_conflict"):
        c.populate_liftover_sheet(request(), native_observation=native)
    native = observed(None, captured=False, state="not_started", count=0,
        failure=failure("coordinate_conversion_failed"))
    with pytest.raises(ValueError): c.populate_liftover_sheet(request(), native_observation=native)


@pytest.mark.parametrize("which", ["row_position", "row_ordinal", "score_type", "assembly", "population", "selected_rows"])
def test_forged_saved_sheet_or_components_are_rejected_instead_of_repaired(which):
    components = c.calculate_liftover_components(sheet([["T", 0, "+", 1]]))
    if which in ("row_position", "row_ordinal", "score_type", "assembly"):
        changed = deepcopy(components["sheet"])
        if which == "assembly": changed["assembly_context"]["target"]["label"] = "hg38"
        elif which == "row_position": changed["rows"][0]["target_position_0based"] = 1
        elif which == "row_ordinal": changed["rows"][0]["ordinal"] = True
        else: changed["rows"][0]["native_chain_score"] = 1.0
        with pytest.raises(ValueError, match="saved_sheet_conflict"): c.validate_liftover_sheet(changed)
    else:
        if which == "population": components["population"]["mapping_count"] = True
        else: components["rows"][0]["target_position_0based"] = 1
        with pytest.raises(ValueError, match="saved_components_conflict"): returned(components)


@pytest.mark.parametrize("field,value", [("source_ref", "artifact_" + "c" * 64),
    ("point", {"chromosome": "normalized", "position_0based": 0, "strand": "+"}),
    ("population", {}), ("rows", []), ("native_artifact_ref", "artifact_" + "d" * 64),
    ("grading_artifact_ref", "artifact_" + "e" * 64)])
def test_return_validation_requires_exact_retained_values(field, value):
    components = c.calculate_liftover_components(sheet([["T", 0, "+", 1]]))
    result = returned(components); result[field] = value
    with pytest.raises(ValueError): c.validate_liftover_return(result, components=components)
    if field in {"native_artifact_ref", "grading_artifact_ref"}:
        schema = c.liftover_fact_sources()[c.FACT_SOURCE]["report_schema"]
        assert not Draft202012Validator(schema).is_valid([result])


def test_serialized_saved_recalculation_projection_and_schema_need_no_converter_or_io(monkeypatch):
    populated = sheet([["target_literal", 0, "-", 10**400], False, ["target_literal", 9, "+", 0]])
    original = c.calculate_liftover_components(populated, mapping_ordinals=[2, 0, 1])
    saved = json.dumps(original, sort_keys=True, separators=(",", ":"))
    schema = c.liftover_fact_sources()[c.FACT_SOURCE]["report_schema"]
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate([returned(original)])
    original_import = builtins.__import__
    def import_without_converter(name, *args, **kwargs):
        assert not name.startswith("pyliftover"), "pure saved data must not import a converter"
        return original_import(name, *args, **kwargs)
    def no_io(*args, **kwargs): raise AssertionError("saved numerical work must not read files")
    monkeypatch.setattr(builtins, "__import__", import_without_converter)
    monkeypatch.setattr(builtins, "open", no_io)
    monkeypatch.setattr(Path, "open", no_io)
    decoded = json.loads(saved)
    recalculated = c.calculate_liftover_components(decoded["sheet"], mapping_ordinals=[2, 0, 1])
    assert json.dumps(recalculated, sort_keys=True, separators=(",", ":")) == saved
    result = returned(decoded)
    assert "native_artifact_ref" not in result and "grading_artifact_ref" not in result
    assert result["chain"] == decoded["sheet"]["request"]["chain"]
    assert c.validate_liftover_return(result, components=decoded) == result
    assert decoded["sheet"]["observation"]["native_result"][1] is False


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), {1: "nonstring"}, object()])
def test_non_json_or_nonfinite_observation_cells_are_not_silently_changed(value):
    with pytest.raises(ValueError): sheet([["T", 0, "+", value]])
