from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_fastqutils_contracts import FastqUtilsContractError
from gene_annotation_episode.bvbrc_fastqutils_metadata import select_metadata, extract_fastqutils_metadata
from gene_annotation_episode.bvbrc_fastqutils_resolution import resolve_calculation_inputs
from gene_annotation_episode.bvbrc_fastqutils_calculators import calculate_fastqutils

spec = importlib.util.spec_from_file_location("fixture_support", Path(__file__).parent / "fixtures/bvbrc_fastqutils/bundle/fixture_support.py")
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


def test_original_arrays_repeats_spelling_and_scheduler_separation():
    original = f.oracle("ORIGINAL_TASK_002.json")
    original["submitted_parameters"]["paired_end_libs"] += [dict(read1="/other", platform="nanopore")]
    original["submitted_parameters"]["single_end_libs"] = [dict(read="/single")]
    original["submitted_parameters"]["srr_libs"] = [dict(srr_accession="SRRsynthetic")]
    original["submitted_parameters"]["recipe"] = ["trim", "FASTQC", "trim", "ALIGN", "SCRUB_HUMAN"]
    # Scheduler fields are independent recorded data; they cannot replace inputs.
    original["scheduler_returned_parameters"] = dict(value={"recipe": ["FASTQC"], "paired_end_libs": []},
        evidence=f.oracle("SUPPLIED_VALUES_002.json")[0]["evidence"])
    original["effective_parameters"] = deepcopy(original["scheduler_returned_parameters"])
    data = f.build({"reads": (f.fastq(["r"]), "fastq")}, original=original)
    sheet = f.sheet_for(data)
    assert [r["input_pointer"] for r in sheet["libraries"]] == ["/paired_end_libs/0", "/paired_end_libs/1", "/single_end_libs/0", "/srr_libs/0"]
    assert [s["requested_token"] for s in sheet["stages"]] == original["submitted_parameters"]["recipe"]
    assert len({s["id"] for s in sheet["stages"]}) == 5
    assert all(s["observed_state"] == "unknown" for s in sheet["stages"])
    assert any(r["code"] == "missing_mate" for r in sheet["requirements"])


def test_selected_metadata_matches_whole_binding_and_pointer():
    data = f.build({"reads": (f.fastq(["r"]), "fastq")}, [("e", "encoding_declaration", f.encoding())])
    bundle, _, values, params = data
    inputs = dict(analysis_id=params["analysis_id"], original_task=bundle["original_task"], bindings=params["metadata_bindings"], supplied_values=values)
    selected, reqs, _ = select_metadata(inputs)
    assert selected[0]["value"] == values[0]["value"] and selected[0]["evidence"] == values[0]["evidence"] and not reqs
    for change in ("pointer", "digest", "artifact_field"):
        changed = deepcopy(inputs)
        evidence = changed["supplied_values"][0]["evidence"]
        if change == "pointer": evidence["pointer"] = "/declarations/1"
        elif change == "digest": evidence["content"]["sha256"] = "0" * 64
        else: evidence["content"]["artifact_field"] = "text_ref"
        selected, reqs, _ = select_metadata(changed)
        assert not selected and reqs[0]["code"] == "metadata_binding_missing"


def test_invalid_and_conflicting_values_are_local_and_unselected_values_do_not_influence():
    data = f.build({"reads": (f.fastq(["r"]), "fastq")}, [("e", "encoding_declaration", f.encoding())])
    bundle, raw, values, params = data
    values[0]["value"]["completed"] = True
    sheet = f.sheet_for(data)
    assert not sheet["supplied_metadata"]
    assert next(r for r in sheet["measurements"] if r["metric"] == "fastq_read_count")["value"] == 1
    assert any(r["code"] == "metadata_value_conflict" for r in sheet["requirements"])
    del values[0]["value"]["completed"]
    values.append(deepcopy(values[0])); values[1]["value"]["encoding"] = "phred64"
    assert not f.sheet_for(data)["supplied_metadata"]
    values.pop(); params["metadata_bindings"] = []
    assert all(p["quality_encoding"] == "unknown" for p in f.sheet_for(data)["populations"])


def test_exact_encoding_assumption_retained_and_no_stage_completion():
    data = f.build({"reads": (f.fastq(["r"]), "fastq")}, [("e", "encoding_declaration", f.encoding())])
    sheet = f.sheet_for(data)
    basis = next(p for p in sheet["populations"] if p["population_key"] == "fastq_quality_characters")["encoding_basis"]
    assert basis["basis"] == "explicit_source_bound_declaration"
    assert basis["evidence"] == data[2][0]["evidence"] and basis["declaration"] == data[2][0]["value"]
    assert all(s["observed_state"] == "unknown" for s in sheet["stages"])
    params = resolve_calculation_inputs(sheet, requests=[dict(calculation_id="q", method="quality_phred_v1",
        population=f.population(key="fastq_quality_characters"), quality_thresholds=[20, 40])])
    components = calculate_fastqutils(sheet, parameters=params)
    assert all(c["encoding_basis"] == basis for c in components["components"])
    assert next(c for c in components["components"] if c["metric"] == "phred_implied_expected_errors")["value"] == pytest.approx(.0004)


@pytest.mark.parametrize("rule,left,right", [
    ("exact_title", ["a", "b"], ["b", "a"]),
    ("first_token", ["a left", "b left"], ["b right", "a right"]),
    ("first_token_slash_mate", ["a/1", "b/1"], ["b/2", "a/2"]),
    ("fastq_pair_0_3", ["a/1", "a_1", "b.f"], ["b.r", "a_2", "a/2"]),
])
def test_pairs_are_actual_key_joins_not_list_positions(rule, left, right):
    data = f.build({"left": (f.fastq(left), "fastq"), "right": (f.fastq(right), "fastq")},
                   [("mates", "pair_declaration", f.pair(rule=rule))])
    sheet = f.sheet_for(data)
    cell = next(r for r in sheet["measurements"] if r["metric"] == "verified_pair_count")
    pop = next(p for p in sheet["populations"] if p["population_key"] == "verified_read_pairs")
    assert cell["value"] == len(left) and cell["state"] == "available"
    assert len(pop["member_record_refs"]) == 2 * len(left) and len(pop["member_artifact_refs"]) == 2


@pytest.mark.parametrize("left,right,rule,expected", [
    (["a/1", "a/1", "b/1"], ["a/2", "b/2"], "first_token_slash_mate", 1),
    (["a/1", "b/1"], ["c/2", "d/2"], "first_token_slash_mate", 0),
    (["a/1\tdescription"], ["a/2"], "fastq_pair_0_3", 0),
])
def test_ambiguous_or_missing_pairs_preserve_only_observed_partial_matches(left, right, rule, expected):
    data = f.build({"left": (f.fastq(left), "fastq"), "right": (f.fastq(right), "fastq")},
                   [("mates", "pair_declaration", f.pair(rule=rule))])
    sheet = f.sheet_for(data)
    cell = next(r for r in sheet["measurements"] if r["metric"] == "verified_pair_count")
    assert cell["value"] == expected and cell["state"] == "partial"
    assert sum(len(d["sequence_records"]) for d in sheet["documents"]) == len(left) + len(right)


def test_failed_pair_declaration_does_not_renumber_later_success():
    data = f.build({"left": (f.fastq(["a/1"]), "fastq"), "right": (f.fastq(["a/2"]), "fastq")},
        [("absent", "pair_declaration", f.pair(right="absent")), ("present", "pair_declaration", f.pair())])
    pops = [p for p in f.sheet_for(data)["populations"] if p["population_key"] == "verified_read_pairs"]
    assert len(pops) == 1 and pops[0]["population_ordinal"] == 1


def test_source_bound_lineage_enables_arithmetic_without_execution_claim():
    example = f.oracle("ASSUMED_LINEAGE_EXAMPLE_002.json")
    data = f.build({"before_reads": ((f.ROOT / "before_reads.fastq").read_bytes(), "fastq"),
        "after_reads": ((f.ROOT / "after_reads.fastq").read_bytes(), "fastq")},
        [("retention_assumption", "lineage_declaration", example["supplied_value"]["value"])])
    sheet = f.sheet_for(data)
    params = resolve_calculation_inputs(sheet, requests=[example["calculation_request"]])
    job = params["calculations"][0]
    assert job["state"] == "ready" and job["lineage_basis"]["evidence"] == data[2][0]["evidence"]
    components = calculate_fastqutils(sheet, parameters=params)
    assert next(c for c in components["components"] if c["metric"] == "read_retention_fraction")["value"] == .75
    assert all(s["observed_state"] == "unknown" for s in sheet["stages"])
    assert not sheet["native_lineage"]


def test_native_sam_encoding_is_not_replaced_by_fastq_declaration():
    sam = b"@HD\tVN:1.6\n@SQ\tSN:r\tLN:10\na\t0\tr\t1\t60\t4M\t*\t0\t0\tACGT\tIIII\n"
    data = f.build({"alignment": (sam, "sam_1_6")}, [("declared", "encoding_declaration", f.encoding("alignment", "phred64"))])
    sheet = f.sheet_for(data)
    pop = next(p for p in sheet["populations"] if p["population_key"] == "bam_quality_bases")
    assert pop["encoding_basis"]["basis"] == "native_sam_phred" and pop["quality_encoding"] == "phred33"
    assert pop["encoding_basis"]["declaration"] is None


def test_calculation_binding_lists_all_consumed_native_operands():
    sheet = f.sheet_for(f.build({"reads": (f.fastq(["a"]), "fastq")}))
    job = resolve_calculation_inputs(sheet, requests=[dict(calculation_id="c", method="composition_v1", population=f.population())])["calculations"][0]
    rows = [r for r in sheet["measurements"] if r["id"] in job["operand_measurement_refs"]]
    assert len(rows) == 9
    assert {r["metric"] for r in rows} == {"fastq_read_count", "fastq_base_count", "fastq_symbol_count"}
    assert {p["population_key"] for p in sheet["populations"] if p["id"] in job["population_refs"]} == {"fastq_reads", "fastq_bases"}


def test_conflicting_lineage_declarations_are_not_arbitrarily_chosen():
    example = f.oracle("ASSUMED_LINEAGE_EXAMPLE_002.json")
    first = example["supplied_value"]["value"]
    second = dict(first, relation="same_population")
    data = f.build({"before_reads": (f.fastq(["a", "b"]), "fastq"), "after_reads": (f.fastq(["a"]), "fastq")},
        [("first", "lineage_declaration", first), ("second", "lineage_declaration", second)])
    sheet = f.sheet_for(data)
    job = resolve_calculation_inputs(sheet, requests=[example["calculation_request"]])["calculations"][0]
    assert job["state"] == "incompatible" and job["lineage_basis"]["basis"] == "unknown"


def test_invalid_annotation_reference_stays_source_bound_without_erasing_native_counts():
    annotation = dict(version="fastqutils_library_annotation_v1", input_pointer="/paired_end_libs/0",
        sample_ref="contains whitespace", condition_ref=None, replicate_ref=None, platform=None)
    data = f.build({"reads": (f.fastq(["a"]), "fastq")}, [("library", "library_annotation", annotation)])
    sheet = f.sheet_for(data)
    assert sheet["supplied_metadata"][0]["value"] == annotation
    assert sheet["libraries"][0]["sample_ref"] is None
    assert any(r["code"] == "metadata_value_conflict" for r in sheet["requirements"])
    assert next(r for r in sheet["measurements"] if r["metric"] == "fastq_read_count")["value"] == 1


def test_signed_report_consistency_uses_only_exact_selected_operands():
    declaration = dict(version="fastqutils_lineage_declaration_v1", before=f.population("report"),
        after=f.population("observed"), relation="same_population", basis="explicit_assumption")
    data = f.build({"report": (f.fastq(["a", "b"]), "fastq"), "observed": (f.fastq(["a", "b", "c"]), "fastq")},
                  [("same", "lineage_declaration", declaration)])
    sheet = f.sheet_for(data)
    request = dict(calculation_id="consistency", method="report_consistency_v1",
        report_measurement=f.measurement("report"), observed_measurement=f.measurement("observed"))
    params = resolve_calculation_inputs(sheet, requests=[request])
    component = calculate_fastqutils(sheet, parameters=params)["components"][0]
    assert component["value"] == -1 and len(component["operand_measurement_refs"]) == 2
    assert component["lineage_basis"]["declaration"] == declaration
    assert all(stage["observed_state"] == "unknown" for stage in sheet["stages"])


def test_missing_selected_operands_do_not_fall_back_to_hidden_sheet_lookup():
    sheet = f.sheet_for(f.build({"reads": (f.fastq(["a"]), "fastq")}))
    params = resolve_calculation_inputs(sheet, requests=[dict(calculation_id="composition", method="composition_v1", population=f.population())])
    job = params["calculations"][0]
    job["operand_measurement_refs"] = [next(r["id"] for r in sheet["measurements"] if r["metric"] == "fastq_read_count")]
    components = calculate_fastqutils(sheet, parameters=params)["components"]
    assert all(r["value"] is None for r in components)
    assert all(set(r["operand_measurement_refs"]) <= set(job["operand_measurement_refs"]) for r in components)
