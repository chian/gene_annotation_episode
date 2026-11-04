"""Independent numerical expectations for retained native FM diagnostics."""
from copy import deepcopy
import builtins
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.hmmer_fm_calculations import calculate_hmmer_fm_components
from gene_annotation_episode.hmmer_fm_data import populate_hmmer_fm_sheet
from test_hmmer_fm_data import ABI, artifact, build_sheet, exact_sheet, exact_payloads, encode_synthetic


def summary(result,kind="database_summary"):
    return next(r for r in result["rows"] if r["kind"]==kind)


def values(result,kind="database_summary"):
    return {key:value["value"] for key,value in summary(result,kind)["components"].items()}


def states(result,name):
    return [c["state"] for c in result["checks"] if c["name"]==name]


def test_build_numerical_components_and_all_native_arrays():
    result = calculate_hmmer_fm_components(build_sheet())
    c = values(result)
    assert (c["source_occurrence_count"],c["stored_segment_count"],c["distinct_target_count"]) == (2,2,2)
    assert (c["source_symbol_total"],c["indexed_symbols"],c["indexed_unique_symbols"],c["sentinel_count"]) == (28,28,28,1)
    assert c["actual_database_bytes"] == 314
    assert c["ambiguity_union_symbols"] == 0 and c["ambiguity_fraction"] == 0
    assert all(c["state"]=="pass" for c in result["checks"] if c["state"]!="not_applicable")
    fwd = calculate_hmmer_fm_components(build_sheet("fwd"))
    assert values(fwd)["actual_database_bytes"] == 226
    assert values(fwd)["source_symbol_total"] == 28
    assert states(fwd,"bwt_text_consistency") == ["pass"]


def test_ambiguity_fraction_is_source_union_and_native_replacements_stay_separate():
    result = calculate_hmmer_fm_components(build_sheet("ambiguous"))
    c = values(result)
    assert c["ambiguity_range_count"] == 2
    assert c["ambiguity_union_symbols"] == 6
    assert c["source_symbol_total"] == 18
    assert c["ambiguity_fraction"] == pytest.approx(1/3)
    assert states(result,"source_symbols_outside_ambiguities") == ["pass","pass"]
    assert states(result,"source_ambiguity_membership") == ["pass","pass"]


def test_rna_normalization_is_explicit_and_amino_writer_is_decoded():
    sheet = build_sheet("rna")
    none = calculate_hmmer_fm_components(sheet)
    normalized = calculate_hmmer_fm_components(sheet,parameters={"alphabet_normalization":"rna_to_dna"})
    assert states(none,"source_symbols_outside_ambiguities") == ["fail","fail"]
    assert states(normalized,"source_symbols_outside_ambiguities") == ["pass","pass"]
    amino = calculate_hmmer_fm_components(build_sheet("protein"))
    assert values(amino)["source_symbol_total"] == 40
    assert states(amino,"dna_reader_compatibility") == ["fail"]
    assert states(amino,"bwt_text_consistency") == ["pass"]
    assert states(amino,"source_symbols_outside_ambiguities") == ["pass","pass"]


@pytest.mark.parametrize("case,q,h,r,valid,invalid,expected,missing,extra",[
    ("forward",5,15,2,15,0,15,0,0),
    ("locations",5,17,2,16,1,17,1,1),
    ("reverse",2,7,1,7,0,9,2,0),
    ("forward_index",5,15,2,15,0,15,0,0),
    ("ambiguous",1,3,0,3,0,3,0,0),
    ("zero",0,0,2,0,0,0,0,0),
])
def test_exact_native_and_independent_populations(case,q,h,r,valid,invalid,expected,missing,extra):
    result = calculate_hmmer_fm_components(exact_sheet(case),parameters={"exhaustive_literal_check":True})
    c = values(result,"exactmatch_summary")
    assert (c["native_Q"],c["native_H"],c["native_R"]) == (q,h,r)
    assert c["emitted_location_count"] == h
    assert (c["valid_location_count"],c["invalid_location_count"],c["unresolved_location_count"]) == (valid,invalid,0)
    assert c["expected_literal_location_count"] == expected
    assert c["missing_literal_location_count"] == missing
    assert c["extra_literal_location_count"] == extra
    assert states(result,"native_query_population") == ["pass"]
    if case=="ambiguous":
        assert c["native_unclassified_queries"] == 3


def test_native_reverse_bug_is_retained_with_actual_missing_extra_tuples():
    result = calculate_hmmer_fm_components(exact_sheet(),parameters={"exhaustive_literal_check":True})
    rows = [r for r in result["rows"] if r["kind"]=="location_validation"]
    invalid = [r for r in rows if r["details"]["state"]=="invalid"]
    assert len(invalid)==1
    assert invalid[0]["components"]["native_anchor"]["value"] == 3
    assert invalid[0]["components"]["interval_start"]["value"] == 0
    assert invalid[0]["components"]["interval_end"]["value"] == 3
    exhaustive = summary(result,"exactmatch_summary")["details"]["exhaustive"]
    missing,extra = exhaustive["missing_tuples"][0],exhaustive["extra_tuples"][0]
    assert missing["query_record_key"].endswith("#query/4") and missing["anchor"]["value"] == 12 and missing["direction"]=="r"
    assert extra["query_record_key"].endswith("#query/1") and extra["anchor"]["value"] == 3 and extra["direction"]=="r"
    reverse = calculate_hmmer_fm_components(exact_sheet("reverse"))
    hit = next(r for r in reverse["rows"] if r["kind"]=="location_validation")
    assert hit["details"]["candidates"][0]["source_interval_text"] == "ACGT"
    assert hit["details"]["candidates"][0]["compared_text"] == "TGCA"


@pytest.mark.parametrize("case,q,h,r",[("counts_forward",5,16,2),("counts",5,19,2),("ambiguous_counts",4,6,0)])
def test_count_only_raw_intervals_never_become_validated_locations(case,q,h,r):
    result = calculate_hmmer_fm_components(exact_sheet(case),parameters={"exhaustive_literal_check":True})
    c = summary(result,"exactmatch_summary")["components"]
    assert (c["native_Q"]["value"],c["native_H"]["value"],c["native_R"]["value"]) == (q,h,r)
    assert c["native_H"]["unit"] == "raw_fm_interval_occurrences"
    for field in ("emitted_location_count","valid_location_count","invalid_location_count","unresolved_location_count"):
        assert c[field]["value"] is None and c[field]["state"]=="missing"
    assert summary(result,"exactmatch_summary")["details"]["exhaustive"]["state"] == "expected_only"


def test_missing_source_and_hits_are_unknown_not_zero():
    op,inputs,outputs = exact_payloads()
    inputs.pop("source_sequences")
    result = calculate_hmmer_fm_components(exact_sheet(inputs=inputs))
    assert values(result)["source_occurrence_count"] is None
    c = values(result,"exactmatch_summary")
    assert c["emitted_location_count"] == 17 and c["unresolved_location_count"] == 17
    outputs.pop("hits")
    result = calculate_hmmer_fm_components(exact_sheet(inputs=inputs,outputs=outputs))
    assert values(result,"exactmatch_summary")["emitted_location_count"] is None


def test_source_mismatch_detected_and_custody_stays_unknown():
    sheet = build_sheet(binding=False)
    sheet["input_records"][0]["payload"]["sequence"] = "CCGTACGTACGTACGT"
    result = calculate_hmmer_fm_components(sheet)
    assert states(result,"source_symbols_outside_ambiguities") == ["fail","pass"]
    assert states(result,"source_custody") == ["unknown"]


def test_synthetic_array_corruption_is_separately_detected():
    sheet = build_sheet()
    sheet["database"]["blocks"][0]["arrays"]["counters_b"]["values"][1][0] += 1
    sheet["database"]["blocks"][0]["arrays"]["SA"]["values"][1] += 1
    result = calculate_hmmer_fm_components(sheet)
    assert states(result,"counter_rows") == ["fail","pass"]
    assert states(result,"suffix_samples") == ["fail","not_applicable"]
    assert states(result,"source_symbols_outside_ambiguities") == ["pass","pass"]


def test_duplicate_native_tuple_is_detected_and_multiset_comparison_keeps_extra():
    op,inputs,outputs = exact_payloads("forward")
    data = outputs["hits"][0]["content"].replace(b"ACGT\n",b"ACGT\n           1 f       seq0\n",1)
    outputs["hits"] = [artifact(data,"hits","output")]
    result = calculate_hmmer_fm_components(exact_sheet("forward",outputs=outputs),parameters={"exhaustive_literal_check":True})
    assert "fail" in states(result,"hit_duplicate_tuple")
    assert values(result,"exactmatch_summary")["extra_literal_location_count"] == 1
    assert states(result,"native_location_count") == ["fail"]


def test_partial_output_reports_partial_denominators():
    op,inputs,outputs = exact_payloads("forward")
    outputs["hits"][0]["occurrence"]["completeness"] = "partial"
    result = calculate_hmmer_fm_components(exact_sheet("forward",outputs=outputs),parameters={"exhaustive_literal_check":True})
    c = summary(result,"exactmatch_summary")["components"]
    assert c["emitted_location_count"]["value"] == 15 and c["emitted_location_count"]["state"]=="incomplete"
    assert c["valid_location_fraction"]["value"] is None
    assert states(result,"exhaustive_literal_agreement") == ["unknown"]


def test_saved_sheet_recalculation_and_pure_ports_forbid_io(monkeypatch):
    sheet = json.loads(json.dumps(exact_sheet()))
    before = deepcopy(sheet)
    op,inputs,outputs = exact_payloads("forward")
    def forbidden(*args,**kwargs):
        raise AssertionError("pure component attempted I/O or native invocation")
    monkeypatch.setattr(builtins,"open",forbidden)
    monkeypatch.setattr(Path,"open",forbidden)
    monkeypatch.setattr(socket,"socket",forbidden)
    monkeypatch.setattr(subprocess,"Popen",forbidden)
    monkeypatch.setattr(subprocess,"run",forbidden)
    first = calculate_hmmer_fm_components(sheet)
    changed = calculate_hmmer_fm_components(sheet,parameters={"exhaustive_literal_check":True})
    recreated = populate_hmmer_fm_sheet(operation=op,inputs=inputs,outputs=outputs,producer_contract=ABI)
    assert values(first,"exactmatch_summary")["expected_literal_location_count"] is None
    assert values(changed,"exactmatch_summary")["expected_literal_location_count"] == 17
    assert sheet == before
    assert recreated["database"]["population"]["complete"] is True


@pytest.mark.parametrize("parameters",[{"alphabet_normalization":"auto"},{"coordinate_policy":"zero_based"},{"exhaustive_literal_check":1},{"confidence":0.9}])
def test_invalid_parameters_are_explicit(parameters):
    result = calculate_hmmer_fm_components(build_sheet(),parameters=parameters)
    assert result["issues"][0]["code"] == "invalid_parameters"
    assert result["rows"] == []


def test_repeated_block_overlap_preserves_source_union_and_all_sections():
    original = build_sheet("ambiguous")
    extracted = deepcopy(original["database"])
    extracted["metadata"]["block_count"] = 2
    extracted["metadata"]["seq_count"] = 4
    extracted["metadata"]["ambiguity_range_count"] = 4
    extracted["segments"] += deepcopy(extracted["segments"])
    extracted["ambiguity_ranges"] += deepcopy(extracted["ambiguity_ranges"])
    copies = deepcopy(extracted["blocks"])
    for block in copies:
        block["header"]["seq_offset"] = 2
        block["header"]["ambig_offset"] = 2
        block["header"]["overlap"] = 18 if block["section"]=="forward" else 0
    extracted["blocks"] += copies
    content = encode_synthetic(extracted)
    source = b">ambig0\nACGTNNACGT\n>ambig1\nNNRYACGT\n"
    sheet = populate_hmmer_fm_sheet(operation=original["operation"],inputs={"sequences":[artifact(source,"sequences")]},
        outputs={"fm_database":[artifact(content,"fm_database","output")]},producer_contract=ABI)
    result = calculate_hmmer_fm_components(sheet)
    c = values(result)
    assert c["stored_segment_count"] == 4 and c["distinct_target_count"] == 2
    assert c["indexed_symbols"] == 36 and c["indexed_unique_symbols"] == 18
    assert c["ambiguity_range_count"] == 4 and c["ambiguity_union_symbols"] == 6
    assert c["sentinel_count"] == 2 and c["stored_bwt_sentinel_count"] == 4
    assert states(result,"block_overlap") == ["pass","pass"]
    assert states(result,"total_char_count") == ["pass"]


def test_uint16_counter_boundary_and_all_sample_rows_synthetic():
    import struct
    n = 65536  # all A plus the separate terminal sentinel
    name = b"all_a"
    header = struct.pack("<BBBBIIIHIIQ",1,0,4,2,8,65536,256,1,1,0,n-1)
    segment = struct.pack("<IQIIHHHH",0,1,0,n-1,len(name),0,0,0)+name+b"\0\0\0\0"
    block = struct.pack("<QIIIIII",n,n-1,0,0,0,1,0)
    packed = b"\0"*(n//4)
    samples = [0]+[n-1-row for row in range(8,n,8)]+[0]
    b_rows = [(i*256,0,0,0) for i in range(256)]+[(0,0,0,0)]
    data = header+segment+block+packed+packed+struct.pack("<"+"I"*len(samples),*samples)
    data += b"".join(struct.pack("<HHHH",*row) for row in b_rows)
    data += struct.pack("<IIIIIIII",0,0,0,0,n,0,0,0)
    operation = build_sheet()["operation"]
    operation["settings"]["--fwd_only"] = True
    sheet = populate_hmmer_fm_sheet(operation=operation,
        inputs={"sequences":[artifact(b">all_a\n"+b"A"*(n-1)+b"\n","sequences")]},
        outputs={"fm_database":[artifact(data,"fm_database","output")]},producer_contract=ABI)
    result = calculate_hmmer_fm_components(sheet)
    assert sheet["database"]["population"]["complete"] is True
    assert states(result,"counter_rows") == ["pass"]
    assert states(result,"suffix_samples") == ["pass"]
    assert states(result,"bwt_text_consistency") == ["pass"]


def test_packed_bwt_corruption_not_hidden_by_cached_decoded_string():
    sheet = build_sheet()
    sheet["database"]["blocks"][0]["arrays"]["BWT"]["values"][0] ^= 1
    result = calculate_hmmer_fm_components(sheet)
    assert states(result,"decoded_array_symbols") == ["fail","pass"]
    assert "fail" in states(result,"bwt_text_consistency")


def test_unknown_decoder_and_unsupported_fasta_population_remain_unknown():
    sheet = build_sheet()
    sheet["operation"]["settings"]["--informat"] = "genbank"
    op,inputs,outputs = exact_payloads()
    missing = calculate_hmmer_fm_components(exact_sheet(producer_contract={}))
    assert values(missing)["stored_segment_count"] is None
    assert summary(missing)["components"]["stored_segment_count"]["state"] == "incompatible"
    # Unsupported source syntax is explicitly selected at the reader boundary.
    built = populate_hmmer_fm_sheet(operation=sheet["operation"],inputs={"sequences":[artifact(b"LOCUS x","sequences")]},
                                   outputs={},producer_contract=ABI)
    result = calculate_hmmer_fm_components(built)
    assert values(result)["source_occurrence_count"] is None
    assert summary(result)["components"]["source_occurrence_count"]["state"] == "incompatible"


def test_contradictory_native_counts_keep_numbers_and_fail_population():
    op,inputs,outputs = exact_payloads()
    outputs["stderr"] = [artifact(b"hit: 6 (4)\nmiss: 3\n","stderr","output")]
    result = calculate_hmmer_fm_components(exact_sheet(outputs=outputs))
    c = summary(result,"exactmatch_summary")["components"]
    assert c["native_Q"]["value"] == 6 and c["native_H"]["value"] == 4
    assert states(result,"native_query_population") == ["fail"]
    assert c["native_unclassified_queries"]["value"] == -2
    assert c["native_unclassified_queries"]["state"] == "failed"


def test_partial_native_count_artifact_and_absent_count_only_hit_file():
    op,inputs,outputs = exact_payloads("counts")
    outputs["stderr"][0]["occurrence"]["completeness"] = "partial"
    outputs.pop("hits")
    result = calculate_hmmer_fm_components(exact_sheet("counts",outputs=outputs))
    c = summary(result,"exactmatch_summary")["components"]
    assert c["native_H"]["value"] == 19 and c["native_H"]["state"] == "incomplete"
    assert states(result,"native_query_population") == ["unknown"]
    assert states(result,"count_only_has_no_locations") == ["unknown"]


def test_unmapped_native_groups_do_not_manufacture_per_query_zero():
    op,inputs,outputs = exact_payloads()
    inputs["queries"] = [artifact(b"GG\n","queries")]
    result = calculate_hmmer_fm_components(exact_sheet(inputs=inputs))
    query = next(r for r in result["rows"] if r["kind"]=="query_validation")
    assert query["components"]["valid_location_count"]["value"] is None
    assert query["components"]["valid_location_count"]["state"] == "incomplete"
    assert values(result,"exactmatch_summary")["unresolved_location_count"] == 17
