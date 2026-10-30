"""Independent numerical and failure checks for A1 saved-sheet calculations."""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path

import pytest

from gene_annotation_episode.hmmer_artifact_calculations import (
    calculate_hmmer_artifact_components, ROW_FIELDS, CELL_FIELDS, OPTIONAL_FIELD_FIELDS, ISSUE_CODES,
)
from test_hmmer_artifact_data import native_sheet, native_case, populate, payload


def rows(result,kind):
    return [row for row in result["rows"] if row["kind"] == kind]


def check(result,code):
    return [row["state"] for row in result["checks"] if row["code"] == code]


@pytest.mark.parametrize("suffix", ["ascii"] + ["3"+r for r in "abcde"] + ["annotated_3"+r for r in "abcdef"])
def test_native_conversion_compares_all_body_cells(suffix):
    result = calculate_hmmer_artifact_components(native_sheet("hmmconvert_"+suffix))
    comparison = rows(result,"model_comparison")[0]
    assert comparison["source_length"]["value"] == comparison["output_length"]["value"] == 12
    assert comparison["length_difference"]["value"] == 0
    assert comparison["compared_cell_count"]["value"] == 611
    assert len(comparison["cell_differences"]) == 611
    assert comparison["max_absolute_probability_difference"]["value"] == 0
    assert comparison["mean_absolute_probability_difference"]["value"] == 0
    assert check(result,"model_probability_equivalence") == ["pass"]
    assert check(result,"conversion_population_equal") == ["pass"]
    assert all(row.keys() == ROW_FIELDS[row["kind"]] for row in result["rows"])
    assert all(row.keys() == CELL_FIELDS for row in comparison["cell_differences"])
    assert all(row.keys() == OPTIONAL_FIELD_FIELDS for row in comparison["optional_fields"])
    assert {i["code"] for i in result["issues"]} <= ISSUE_CODES


def test_native_revision_losses_and_actual_calibration_values():
    result = calculate_hmmer_artifact_components(native_sheet("hmmconvert_annotated_3a"))
    optional = {row["field"]:row for row in rows(result,"model_comparison")[0]["optional_fields"]}
    assert optional["header.CONS"]["state"] == optional["header.MM"]["state"] == "lost"
    assert optional["positions.0.annotations.CONS"]["state"] == "lost"
    assert optional["positions.0.annotations.MM"]["state"] == "lost"
    assert optional["header.GA"]["state"] == "retained"
    stats = optional["header.STATS"]
    assert stats["state"] == "changed"
    assert ["LOCAL","VMU","-5.908600"] in stats["output_value"]
    assert ["LOCAL","VITERBI","-6.1309","0.74188"] in stats["source_value"]


@pytest.mark.parametrize("name,size,equivalence", [("hmmconvert_binary",2725,"pass"),("hmmconvert_legacy2",5175,"unknown")])
def test_decoded_formats_preserve_counts_and_specific_equivalence_limits(name,size,equivalence):
    result = calculate_hmmer_artifact_components(native_sheet(name))
    output = next(r for r in rows(result,"population") if r["direction"] == "output")
    assert output["decoded_model_count"]["value"] == 1
    assert output["model_artifact_bytes"]["value"] == size
    assert check(result,"conversion_population_equal") == ["pass"]
    assert check(result,"model_probability_equivalence") == [equivalence]


def test_quantitative_cell_difference_and_saved_tolerance_recalculation():
    operation, inputs, outputs, bindings = native_case("hmmconvert_ascii")
    changed = outputs["converted_models"][0]["content"].replace(b"0.40547",b"0.50547",1)
    outputs["converted_models"] = [payload(changed,"converted_models","output")]
    outputs["stdout"] = [payload(changed,"stdout","output")]
    sheet = populate(operation,inputs,outputs,bindings)
    saved = json.loads(json.dumps(sheet))
    result = calculate_hmmer_artifact_components(saved,parameters={"probability_tolerance":.001})
    comparison = rows(result,"model_comparison")[0]
    with localcontext() as ctx:
        ctx.prec = 60
        expected = abs((-Decimal("0.50547")).exp()-(-Decimal("0.40547")).exp())
    assert comparison["max_absolute_probability_difference"]["value"] == pytest.approx(float(expected),abs=1e-15)
    assert comparison["mean_absolute_probability_difference"]["value"] == pytest.approx(float(expected/611),abs=1e-15)
    assert comparison["mean_absolute_probability_difference"]["inputs"][-1]["role"] == "denominator"
    assert check(result,"model_probability_equivalence") == ["fail"]
    relaxed = calculate_hmmer_artifact_components(saved,parameters={"probability_tolerance":.1,"expected_revision":"3/e"})
    assert check(relaxed,"model_probability_equivalence") == ["pass"]
    assert check(relaxed,"expected_revision") == ["fail"]
    assert rows(relaxed,"model_comparison")[0]["cell_differences"] == comparison["cell_differences"]
    assert saved == sheet


@pytest.mark.parametrize("mutation,state", [(b"99999.00000","nonfinite"),(b"garbage","incompatible")])
def test_native_underflow_or_malformed_probability_is_not_zero(mutation,state):
    operation,inputs,outputs,bindings = native_case("hmmconvert_ascii")
    content = outputs["converted_models"][0]["content"].replace(b"0.40547",mutation,1)
    outputs["converted_models"] = [payload(content,"converted_models","output")]
    outputs["stdout"] = [payload(content,"stdout","output")]
    result = calculate_hmmer_artifact_components(populate(operation,inputs,outputs,bindings))
    comparison = rows(result,"model_comparison")[0]
    cell = next(c for c in comparison["cell_differences"] if c["output_token"] == mutation.decode())
    assert cell["output_probability"]["value"] is None
    assert cell["absolute_difference"]["state"] == state
    assert comparison["compared_cell_count"]["value"] == 610
    assert comparison["max_absolute_probability_difference"]["state"] == state
    assert check(result,"model_probability_equivalence") == ["unknown"]


def test_insert_and_transition_values_are_actual_operands():
    operation,inputs,outputs,bindings = native_case("hmmconvert_ascii")
    content = outputs["converted_models"][0]["content"]
    # First COMPO and first initial-insert cells carry these native tokens.
    lines = content.splitlines(keepends=True)
    start = next(i for i,line in enumerate(lines) if b"COMPO" in line)
    old_insert = lines[start+1].split()[0]
    old_transition = lines[start+2].split()[0]
    lines[start+1] = lines[start+1].replace(old_insert,b"1.00000",1)
    lines[start+2] = lines[start+2].replace(old_transition,b"1.00000",1)
    changed = b"".join(lines)
    outputs["converted_models"] = [payload(changed,"converted_models","output")]
    outputs["stdout"] = [payload(changed,"stdout","output")]
    result = calculate_hmmer_artifact_components(populate(operation,inputs,outputs,bindings))
    comparison = rows(result,"model_comparison")[0]
    changed_cells = [c for c in comparison["cell_differences"] if c["absolute_difference"]["value"]]
    assert {c["field"] for c in changed_cells} == {"initial.insert","initial.transitions"}
    with localcontext() as ctx:
        ctx.prec = 60
        deltas = [abs((-Decimal("1")).exp()-(-Decimal(old.decode())).exp()) for old in (old_insert,old_transition)]
    assert comparison["max_absolute_probability_difference"]["value"] == pytest.approx(float(max(deltas)))
    assert comparison["mean_absolute_probability_difference"]["value"] == pytest.approx(float(sum(deltas)/611))


@pytest.mark.parametrize("name,requested,resolved,missing,returned,duplicates", [
    ("hmmfetch_single",1,1,0,1,0),("hmmfetch_unindexed_alias",2,2,0,1,0),
    ("hmmfetch_indexed_alias",2,2,0,2,1),("hmmfetch_unindexed_missing",2,1,1,1,0),
    ("hmmfetch_indexed_missing",2,1,1,1,0),("hmmfetch_duplicate",2,2,0,1,0)])
def test_native_fetch_numeric_populations(name,requested,resolved,missing,returned,duplicates):
    result = calculate_hmmer_artifact_components(native_sheet(name))
    row = rows(result,"key_population")[0]
    expected = {"requested_key_count":requested,"resolved_key_count":resolved,"missing_key_count":missing,
        "returned_model_occurrence_count":returned,"duplicate_representation_count":duplicates,"selected_source_occurrence_count":1}
    assert {name:row[name]["value"] for name in expected} == expected
    assert all(r["compared_cell_count"]["value"] == 611 for r in rows(result,"model_comparison"))
    if missing:
        assert check(result,"all_requested_keys_resolved") == ["fail"]
    if name == "hmmfetch_indexed_missing":
        assert check(result,"native_diagnostics") == ["fail"]
    if name == "hmmfetch_unindexed_missing":
        assert check(result,"native_diagnostics") == ["not_applicable"]
        assert row["fulfilled_key_count"]["value"] == 1


def test_native_press_bundle_sizes_counts_and_custody_limits():
    result = calculate_hmmer_artifact_components(native_sheet("hmmpress_success"))
    assert rows(result,"bundle")[0]["bundle_byte_sum"]["value"] == 2725+165+9918+3216 == 16024
    summary = rows(result,"index_summary")[0]
    assert [summary["native_"+n]["value"] for n in ("model_count","primary_name_count","accession_count")] == [1,1,1]
    assert check(result,"supplied_artifact_binding") == ["pass"]*4
    assert check(result,"authenticated_artifact_custody") == ["unknown"]*4
    assert check(result,"binary_internal_content") == ["pass", "unknown", "unknown", "unknown"]
    assert check(result,"binary_framing") == ["pass"]*4
    assert check(result,"bundle_supplied_attempt_consistency") == ["pass"]


def test_native_fetch_index_is_165_bytes_not_165_decoded_models():
    result = calculate_hmmer_artifact_components(native_sheet("hmmfetch_index"))
    ssi = next(r for r in rows(result,"artifact") if r["format"] == "ssi")
    assert ssi["size_bytes"]["value"] == 165
    assert ssi["decoded_record_count"]["value"] is None
    assert check(result,"native_model_count") == ["pass"]


def test_fetch_decoded_binary_source_resolves_original_model_occurrence():
    operation,inputs,outputs,bindings = native_case("hmmfetch_single")
    _,_,converted,_ = native_case("hmmconvert_binary")
    inputs["models"] = [payload(converted["converted_models"][0]["content"],"models")]
    result = calculate_hmmer_artifact_components(populate(operation,inputs,outputs,bindings))
    population = rows(result,"key_population")[0]
    assert population["unknown_key_count"]["value"] == 0
    assert population["selected_source_occurrence_count"]["value"] == 1
    assert population["expected_returned_model_occurrence_count"]["value"] == 1
    assert check(result,"fetch_output_population") == ["pass"]
    assert check(result,"model_probability_equivalence") == ["pass"]


@pytest.mark.parametrize("indexed", [False,True])
def test_fetch_preserves_native_source_order_or_key_order_with_two_distinct_models(indexed):
    operation,inputs,outputs,bindings = native_case("hmmfetch_indexed_alias" if indexed else "hmmfetch_unindexed_alias")
    first = inputs["models"][0]["content"]
    second = first.replace(b"tiny_protein",b"second_model").replace(b"TINY001",b"TINY002")
    inputs["models"] = [payload(first+second,"models")]
    inputs["keys"] = [payload(b"TINY002\ntiny_protein\n","keys")]
    outputs["fetched_models"] = [payload(second+first if indexed else first+second,"fetched_models","output")]
    result = calculate_hmmer_artifact_components(populate(operation,inputs,outputs,None))
    assert check(result,"model_probability_equivalence") == ["pass","pass"]
    pairs = rows(result,"model_comparison")
    assert [r["source_record_key"] for r in pairs] == ["input/models/0#model/"+str(i) for i in ([1,0] if indexed else [0,1])]
    assert rows(result,"key_population")[0]["duplicate_representation_count"]["value"] == 0


@pytest.mark.parametrize("case", ["missing", "empty", "magic", "truncated", "wrong_role", "stale_binding", "mixed_attempt", "no_binding"])
def test_press_failure_states_do_not_invent_internal_validation(case):
    operation, inputs, outputs, bindings = native_case("hmmpress_success")
    if case == "missing": outputs.pop("remaining_profiles")
    elif case in {"empty","magic","truncated"}:
        content = {"empty":b"", "magic":b"xxxx"+outputs["msv_profiles"][0]["content"][4:], "truncated":outputs["msv_profiles"][0]["content"][:15]}[case]
        outputs["msv_profiles"] = [payload(content,"msv_profiles","output")]
    elif case == "wrong_role":
        outputs["msv_profiles"] = [payload(outputs["remaining_profiles"][0]["content"],"msv_profiles","output")]
    elif case == "stale_binding": bindings[0]["source_sha256"] = "0"*64
    elif case == "mixed_attempt": bindings[0]["producer_attempt_id"] = "other-attempt"
    elif case == "no_binding": bindings = None
    result = calculate_hmmer_artifact_components(populate(operation,inputs,outputs,bindings))
    content_checks = [c for c in result["checks"] if c["code"] == "binary_internal_content"]
    assert next(c["state"] for c in content_checks if c["row_key"] == "output/binary_models/0") == "pass"
    assert all(c["state"] == "unknown" for c in content_checks if c["row_key"] != "output/binary_models/0")
    if case == "missing":
        assert "fail" in check(result,"required_member_present")
        assert rows(result,"bundle")[0]["bundle_byte_sum"]["state"] == "incomplete"
    elif case in {"empty","magic","truncated","wrong_role"}: assert "fail" in check(result,"binary_framing")
    elif case == "stale_binding": assert "fail" in check(result,"supplied_artifact_binding")
    elif case == "mixed_attempt": assert check(result,"bundle_supplied_attempt_consistency") == ["fail"]
    else: assert check(result,"supplied_artifact_binding") == ["unknown"]*4


def test_missing_accessions_compare_zero_against_actual_source_population():
    operation, inputs, outputs, bindings = native_case("hmmfetch_index")
    content = inputs["models"][0]["content"].replace(b"ACC   TINY001\n",b"")
    inputs["models"] = [payload(content,"models")]
    outputs["stdout"] = [payload(b"Indexed 1 HMMs (1 names).\n","stdout","output")]
    result = calculate_hmmer_artifact_components(populate(operation,inputs,outputs,bindings))
    assert rows(result,"index_summary")[0]["native_accession_count"]["value"] == 0
    assert check(result,"native_accession_count") == ["pass"]


def test_truncated_trailing_model_retains_completed_prefix_comparison():
    operation, inputs, outputs, _ = native_case("hmmconvert_ascii")
    content = inputs["models"][0]["content"]
    inputs["models"] = [payload(content*2,"models")]
    outputs["converted_models"] = [payload(content+content[:-250],"converted_models","output",completeness="partial")]
    outputs["stdout"] = [payload(content+content[:-250],"stdout","output",completeness="partial")]
    result = calculate_hmmer_artifact_components(populate(operation,inputs,outputs))
    assert check(result,"model_probability_equivalence")[0] == "pass"
    assert check(result,"model_probability_equivalence")[1] == "unknown"
    assert rows(result,"model_comparison")[0]["compared_cell_count"]["value"] == 611
    assert rows(result,"model_comparison")[1]["max_absolute_probability_difference"]["state"] == "incomplete"


@pytest.mark.parametrize("mutation", ["different_name", "different_length", "body_mismatch", "duplicate_source", "unindexed_duplicates"])
def test_fetch_cannot_claim_source_equivalence_from_labels_alone(mutation):
    operation, inputs, outputs, bindings = native_case("hmmfetch_indexed_alias")
    native = outputs["fetched_models"][0]["content"]
    if mutation == "different_name": native = native.replace(b"tiny_protein",b"other_protein")
    if mutation == "different_length": native = native.replace(b"LENG  12",b"LENG  13")
    if mutation == "body_mismatch": native = native.replace(b"0.40547",b"0.50547")
    if mutation == "duplicate_source": inputs["models"] = [payload(inputs["models"][0]["content"]*2,"models")]
    if mutation == "unindexed_duplicates":
        inputs.pop("ssi")
        inputs["keys"] = [payload(b"tiny_protein\ntiny_protein\n","keys")]
    outputs["fetched_models"] = [payload(native,"fetched_models","output")]
    result = calculate_hmmer_artifact_components(populate(operation,inputs,outputs,bindings))
    if mutation == "body_mismatch": assert check(result,"model_probability_equivalence") == ["fail","fail"]
    else: assert "pass" not in check(result,"model_probability_equivalence")


@pytest.mark.parametrize("field", ["association", "record_copy", "record_reference", "native_reference"])
def test_saved_sheet_reference_corruption_is_rejected(field):
    sheet = native_sheet("hmmfetch_indexed_alias")
    if field == "association": sheet["associations"][0]["output_record_keys"] = ["unrelated"]
    if field == "record_copy": sheet["output_records"][0]["length"] = 4
    if field == "record_reference":
        sheet["model_extractions"][0]["records"][0]["record_key"] = "wrong#model/0"
        sheet["input_records"][0]["record_key"] = "wrong#model/0"
    if field == "native_reference": sheet["native_rows"][0]["occurrence_id"] = "unrelated"
    result = calculate_hmmer_artifact_components(sheet)
    assert not result["rows"]
    assert result["issues"][0]["code"] in {"saved_reference_invalid","saved_association_invalid"}


@pytest.mark.parametrize("replacement", [None,[],{},"bad"])
def test_malformed_saved_distribution_returns_structured_failure(replacement):
    sheet = native_sheet("hmmconvert_ascii")
    for records in (sheet["output_records"],sheet["model_extractions"][1]["records"]):
        records[0]["positions"][0]["match"] = replacement
    result = calculate_hmmer_artifact_components(sheet)
    if replacement is None:
        assert check(result,"model_probability_equivalence") == ["unknown"]
    else:
        assert result["issues"][0]["code"] == "saved_reference_invalid"


def test_empty_output_is_zero_but_missing_output_is_unknown():
    operation,inputs,outputs,bindings = native_case("hmmconvert_ascii")
    outputs["converted_models"] = [payload(b"","converted_models","output")]
    outputs["stdout"] = [payload(b"","stdout","output")]
    empty = calculate_hmmer_artifact_components(populate(operation,inputs,outputs,bindings))
    assert next(r for r in rows(empty,"population") if r["direction"] == "output")["decoded_model_count"]["value"] == 0
    outputs.pop("converted_models")
    missing = calculate_hmmer_artifact_components(populate(operation,inputs,outputs,bindings))
    assert next(r for r in rows(missing,"population") if r["direction"] == "output")["decoded_model_count"]["value"] is None


@pytest.mark.parametrize("tolerance", [-1, float("inf"),float("nan"),".1",True])
def test_invalid_tolerance_preserves_numbers_without_pass(tolerance):
    result = calculate_hmmer_artifact_components(native_sheet("hmmconvert_ascii"),parameters={"probability_tolerance":tolerance})
    assert check(result,"parameters_valid") == ["fail"]
    assert check(result,"model_probability_equivalence") == ["unknown"]
    assert rows(result,"model_comparison")[0]["compared_cell_count"]["value"] == 611


def test_saved_recalculation_is_pure_and_does_not_mutate_sheet(monkeypatch):
    sheet = json.loads(json.dumps(native_sheet("hmmpress_success")))
    before = deepcopy(sheet)
    def forbidden(*args,**kwargs): raise AssertionError("saved-sheet calculation attempted I/O/native execution")
    import builtins,subprocess,socket,os
    monkeypatch.setattr(builtins,"open",forbidden)
    monkeypatch.setattr(Path,"open",forbidden)
    monkeypatch.setattr(subprocess,"Popen",forbidden)
    monkeypatch.setattr(socket,"socket",forbidden)
    monkeypatch.setattr(os,"system",forbidden)
    result = calculate_hmmer_artifact_components(sheet,parameters={"probability_tolerance":1e-8,"expected_revision":"3/f"})
    assert rows(result,"bundle")[0]["bundle_byte_sum"]["value"] == 16024
    assert sheet == before


@pytest.mark.parametrize("case", ["hmmconvert_ascii"] +
    ["hmmconvert_annotated_3" + revision for revision in "abcdef"] +
    ["hmmfetch_single", "hmmfetch_indexed_alias", "hmmfetch_unindexed_alias"])
def test_saved_recalculation_ignores_json_object_key_order(case, monkeypatch):
    sheet = native_sheet(case)
    parameters = {"probability_tolerance": 1e-4}
    original = calculate_hmmer_artifact_components(sheet, parameters=parameters)
    canonical = json.loads(json.dumps(sheet, sort_keys=True))
    reversed_keys = json.loads(json.dumps(sheet),
        object_pairs_hook=lambda pairs: dict(reversed(pairs)))
    saved = deepcopy([canonical, reversed_keys])

    def forbidden(*args, **kwargs):
        raise AssertionError("Recalculation must use only the saved numerical sheet")

    import builtins, subprocess, socket, os
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    for reordered in (canonical, reversed_keys):
        # Do not normalize result lists: the saved result and its exact
        # recalculation must agree despite meaningless object-key ordering.
        assert calculate_hmmer_artifact_components(reordered, parameters=parameters) == original
    assert [canonical, reversed_keys] == saved
