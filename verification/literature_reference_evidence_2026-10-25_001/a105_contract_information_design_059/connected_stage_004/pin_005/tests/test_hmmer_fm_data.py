"""Retained native FM formats and explicitly synthetic malformed variants."""
from copy import deepcopy
import hashlib
from pathlib import Path
import struct

import pytest

from gene_annotation_episode.hmmer_fm_data import (
    ISSUE_CODES, ROW_FIELDS, extract_hmmer_fm_database, populate_hmmer_fm_sheet,
)

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259"
ABI = {"format":"hmmer_fm_3_4","engine_version":"3.4","byte_order":"little",
       "uint8_bytes":1,"uint16_bytes":2,"uint32_bytes":4,"uint64_bytes":8,"int32_bytes":4}


def artifact(data, role, direction="input", ordinal=0, label=None, completeness="complete"):
    oid = label or f"synthetic:{direction}:{role}:{ordinal}"
    return {"content":data,"occurrence":{"occurrence_id":oid,"direction":direction,"role":role,
        "ordinal":ordinal,"artifact_ref":oid,"sha256":hashlib.sha256(data).hexdigest(),
        "size_bytes":len(data),"completeness":completeness}}


def retained(path, role, direction="input"):
    return artifact(path.read_bytes(),role,direction,label="retained:"+str(path.relative_to(ROOT)))


def extraction(data=None, abi=None, completeness="complete"):
    if data is None:
        data = (NATIVE / "native/makehmmerdb_dna/index.fm").read_bytes()
    item = artifact(data,"fm_database","output",completeness=completeness)
    return extract_hmmer_fm_database(data,occurrence=item["occurrence"],producer_contract=ABI if abi is None else abi)


def build_sheet(case="dna", *, binding=True):
    source_file = {"dna":"tiny.fa","fwd":"tiny.fa","rna":"rna.fa","protein":"protein.fa","ambiguous":"ambiguous.fa"}[case]
    path = NATIVE / "native" / ("makehmmerdb_"+case)
    inputs = {"sequences":[retained(NATIVE / "inputs" / source_file,"sequences")]}
    outputs = {"fm_database":[retained(path / "index.fm","fm_database","output")],
               **{role:[retained(path/(role+".log"),role,"output")] for role in ("stdout","stderr")}}
    operation = {"program":"makehmmerdb","mode":"build","engine_version":"3.4",
        "settings":{"--fwd_only":case=="fwd","--amino":case=="protein","--rna":case=="rna",
                    "--dna":case in ("dna","fwd","ambiguous"),"--block_size":1,"--bin_length":256,"--sa_freq":8}}
    source_binding = {"database_occurrence_id":outputs["fm_database"][0]["occurrence"]["occurrence_id"],
        "source_occurrence_ids":[inputs["sequences"][0]["occurrence"]["occurrence_id"]],
        "source_sha256s":[inputs["sequences"][0]["occurrence"]["sha256"]],"producer_attempt_id":str(path.relative_to(ROOT))}
    return populate_hmmer_fm_sheet(operation=operation,inputs=inputs,outputs=outputs,producer_contract=ABI,
                                   source_binding=source_binding if binding else None)


def exact_payloads(case="locations"):
    ambiguous = case.startswith("ambiguous")
    source = "ambiguous.fa" if ambiguous else "tiny.fa"
    query = "queries_ambiguous.txt" if ambiguous else "queries_reverse.txt" if case in ("reverse","default_output") else "queries_zero.txt" if case=="zero" else "queries.txt"
    index = "ambiguous" if ambiguous else "fwd" if case=="forward_index" else "dna"
    path = NATIVE / "native" / ("hmmerfm_exactmatch_"+case)
    inputs = {"queries":[retained(NATIVE/"inputs"/query,"queries")],
              "source_sequences":[retained(NATIVE/"inputs"/source,"source_sequences")],
              "fm_database":[retained(NATIVE/"native"/("makehmmerdb_"+index)/"index.fm","fm_database")]}
    outputs = {"hits":[retained(path/("none" if case=="default_output" else "hits.txt"),"hits","output")],
               **{role:[retained(path/(role+".log"),role,"output")] for role in ("stdout","stderr")}}
    count_only = "counts" in case
    operation = {"program":"hmmerfm-exactmatch","mode":"count_only" if count_only else "locations","engine_version":"3.4",
                 "settings":{"--fwd_only":case in ("forward","counts_forward","ambiguous","ambiguous_counts"),"--count_only":count_only,"--out":"none" if case=="default_output" else "hits.txt"}}
    return operation,inputs,outputs


def exact_sheet(case="locations", **overrides):
    operation,inputs,outputs = exact_payloads(case)
    return populate_hmmer_fm_sheet(operation=overrides.get("operation",operation),inputs=overrides.get("inputs",inputs),
                                  outputs=overrides.get("outputs",outputs),producer_contract=overrides.get("producer_contract",ABI))


def test_native_dna_complete_layout_and_arrays():
    result = extraction()
    assert result["population"] == {"state":"decoded","complete":True,"decoded_segment_count":2,
        "decoded_ambiguity_range_count":0,"decoded_block_section_count":2,"body_complete":True}
    assert result["metadata"]["total_char_count"] == 28
    assert result["metadata"]["actual_bytes"] == 314
    assert [(s["target_id"],s["target_start"],s["fm_start"],s["length"]) for s in result["segments"]] == [(0,1,0,16),(1,1,16,12)]
    first,second = result["blocks"]
    assert first["decoded"]["text"] == "ACGTACGTACGTACGTTTTTACGTGGGGA"
    assert len(first["arrays"]["T"]["values"]) == 8
    assert len(first["arrays"]["SA"]["values"]) == 4
    assert len(first["arrays"]["counters_b"]["values"]) == 2
    assert len(first["arrays"]["counters_sb"]["values"]) == 2
    assert first["header"]["N"] == 29
    assert set(second["arrays"]) == {"BWT","counters_b","counters_sb"}
    assert second["locator"]["byte_end"] == 314
    assert not result["issues"]


@pytest.mark.parametrize("case,size,sections,total",[("dna",314,2,28),("fwd",226,1,28),("rna",339,2,28),("protein",618,1,40),("ambiguous",325,2,18)])
def test_all_retained_writer_layouts(case,size,sections,total):
    sheet = build_sheet(case)
    result = sheet["database"]
    assert result["population"]["complete"] is True
    assert result["metadata"]["actual_bytes"] == size
    assert result["metadata"]["total_char_count"] == total
    assert len(result["blocks"]) == sections
    assert all(a["complete"] for b in result["blocks"] for a in b["arrays"].values())
    assert result["metadata"]["dna_reader_compatibility"] == ("incompatible" if case=="protein" else "compatible")
    if case=="ambiguous":
        assert [(r["lower"],r["upper"]) for r in result["ambiguity_ranges"]] == [(4,5),(10,13)]
        assert result["blocks"][0]["decoded"]["text"][:-1] == "ACGTGGACGTATGTACGT"
        assert [r["payload"]["sequence"] for r in sheet["input_records"]] == ["ACGTNNACGT","NNRYACGT"]


def test_unknown_wrong_and_big_endian_contracts_are_explicit():
    data = (NATIVE/"native/makehmmerdb_dna/index.fm").read_bytes()
    occ = artifact(data,"fm_database")["occurrence"]
    for abi in (None,{}, {**ABI,"uint64_bytes":4}, {**ABI,"engine_version":"3.3"}):
        result = extract_hmmer_fm_database(data,occurrence=occ,producer_contract=abi)
        assert result["population"]["decoded_segment_count"] is None
        assert result["population"]["state"] == "unsupported"
    result = extraction(data,abi={**ABI,"byte_order":"big"})
    assert result["population"]["complete"] is False
    assert result["population"]["state"] == "invalid"


def test_partial_records_and_hostile_counts_bound_allocation():
    full = (NATIVE/"native/makehmmerdb_dna/index.fm").read_bytes()
    result = extraction(full[:-5])
    assert len(result["segments"]) == 2 and len(result["blocks"]) == 2
    assert result["blocks"][0]["complete"] is True
    assert result["blocks"][1]["arrays"]["counters_sb"]["complete"] is False
    assert result["blocks"][1]["arrays"]["counters_sb"]["values"] == [[0,0,0,0]]
    assert result["population"]["state"] == "partial"
    result = extraction(full[:80])
    assert len(result["segments"]) == 1
    assert any(i["code"] == "truncated_segment" for i in result["issues"])
    mutated = bytearray(full)
    struct.pack_into("<I",mutated,18,0xFFFFFFFF)
    result = extraction(bytes(mutated))
    assert not result["population"]["complete"]
    assert len(result["segments"]) < 10
    for size in (0,1,33):
        assert extraction(full[:size])["metadata"] is None


def test_bad_offsets_size_digest_trailing_and_metadata_strings():
    full = (NATIVE/"native/makehmmerdb_dna/index.fm").read_bytes()
    first = extraction()["blocks"][0]["locator"]["byte_start"]
    mutated = bytearray(full)
    struct.pack_into("<I",mutated,first+12,99)
    assert any(i["code"]=="invalid_block" for i in extraction(bytes(mutated))["issues"])
    assert any(i["code"]=="trailing_bytes" for i in extraction(full+b"junk")["issues"])
    mutated = bytearray(full)
    mutated[66] = ord("x")  # NUL after first name
    assert any(i["code"]=="invalid_string" for i in extraction(bytes(mutated))["issues"])
    occ = artifact(full,"fm_database")["occurrence"]
    occ["sha256"],occ["size_bytes"] = "0"*64,1
    result = extract_hmmer_fm_database(full,occurrence=occ,producer_contract=ABI)
    assert {"size_mismatch","digest_mismatch"} <= {i["code"] for i in result["issues"]}
    assert result["population"]["state"] == "invalid"


def test_original_occurrences_order_and_native_row_fields():
    sheet = exact_sheet()
    queries = [r for r in sheet["input_records"] if r["kind"]=="query"]
    assert [q["payload"]["text"] for q in queries] == ["ACGT","TTTT","AAAA","CCCC","GGGG","ACGT","CGTA"]
    groups = sheet["associations"]["query_groups"]
    assert [g["query_record_keys"] for g in groups] == [[queries[i]["record_key"]] for i in (0,1,4,5,6)]
    assert all(set(r["payload"]) == ROW_FIELDS[r["kind"]] for r in sheet["native_rows"])
    assert all(i["code"] in ISSUE_CODES for i in sheet["issues"])
    assert len({r["record_key"] for r in sheet["native_rows"]}) == len(sheet["native_rows"])
    assert any(r["payload"].get("category")=="unsafe_post_free_statistic" for r in sheet["native_rows"])


@pytest.mark.parametrize("query",[b"ACGT\r\n",b"\n",b">q\n",b"ACNT\n",b"AC GT\n",b"A"*255+b"\n",b"\xff\n"])
def test_invalid_query_lines_are_retained_not_fixed(query):
    op,inputs,outputs = exact_payloads()
    inputs["queries"] = [artifact(query,"queries")]
    sheet = exact_sheet(inputs=inputs)
    records = [r for r in sheet["input_records"] if r["kind"]=="query"]
    assert records[0]["payload"]["raw_line"].encode("latin1") == query
    assert records[0]["payload"]["valid"] is False
    assert any(i["code"]=="invalid_query" for i in sheet["issues"])


def test_ambiguous_duplicate_queries_and_source_names_never_pick_first():
    op,inputs,outputs = exact_payloads()
    inputs["queries"] = [artifact(b"ACGT\nACGT\n","queries")]
    outputs["hits"] = [artifact(b"ACGT\n  1 f seq0\n\n","hits","output")]
    sheet = exact_sheet(inputs=inputs,outputs=outputs)
    assert len(sheet["associations"]["query_groups"][0]["query_record_keys"]) == 2
    assert sheet["associations"]["query_groups"][0]["state"] == "ambiguous"
    # Synthetic duplicate names in both source records and index labels.
    inputs["source_sequences"] = [artifact(b">seq0\nACGTACGTACGTACGT\n>seq0\nTTTTACGTGGGG\n","source_sequences")]
    db = inputs["fm_database"][0]["content"].replace(b"seq1",b"seq0")
    inputs["fm_database"] = [artifact(db,"fm_database")]
    sheet = exact_sheet(inputs=inputs,outputs=outputs)
    targets = sheet["associations"]["hit_targets"][0]
    assert targets["state"] == "ambiguous"
    assert len(targets["candidates"]) == 2


def test_binding_unknown_matching_and_mismatching_remain_separate():
    assert build_sheet(binding=False)["associations"]["source_binding_state"] == "unknown"
    assert build_sheet()["associations"]["source_binding_state"] == "matched"
    op,inputs,outputs = exact_payloads()
    binding = {"database_occurrence_id":inputs["fm_database"][0]["occurrence"]["occurrence_id"],
               "source_occurrence_ids":[inputs["source_sequences"][0]["occurrence"]["occurrence_id"]],
               "source_sha256s":["0"*64],"producer_attempt_id":"synthetic_wrong_attempt"}
    sheet = populate_hmmer_fm_sheet(operation=op,inputs=inputs,outputs=outputs,producer_contract=ABI,source_binding=binding)
    assert sheet["associations"]["source_binding_state"] == "mismatch"


def test_malformed_hits_preserve_valid_prefix_and_missing_empty_differ():
    op,inputs,outputs = exact_payloads()
    outputs["hits"] = [artifact(b"ACGT\n  1 f seq0\n  broken\n","hits","output",completeness="partial")]
    sheet = exact_sheet(outputs=outputs)
    assert len([r for r in sheet["native_rows"] if r["kind"]=="exactmatch_hit"]) == 1
    assert {"partial_artifact","invalid_hits"} <= {i["code"] for i in sheet["issues"]}
    assert not any(i["code"]=="missing_artifact" and i["field"]=="hits" for i in exact_sheet("zero")["issues"])
    outputs.pop("hits")
    assert any(i["code"]=="missing_artifact" and i["field"]=="hits" for i in exact_sheet(outputs=outputs)["issues"])


def test_empty_source_and_query_files_have_zero_records():
    op,inputs,outputs = exact_payloads()
    inputs["queries"] = [artifact(b"","queries")]
    inputs["source_sequences"] = [artifact(b"","source_sequences")]
    sheet = exact_sheet(inputs=inputs)
    assert sheet["input_records"] == []
    assert not any(i["code"]=="missing_artifact" for i in sheet["issues"])


def test_invalid_occurrence_and_operation_are_structured():
    op,inputs,outputs = exact_payloads()
    inputs["queries"][0]["occurrence"]["format"] = "invented"
    assert any(i["code"]=="invalid_occurrence" for i in exact_sheet(inputs=inputs)["issues"])
    assert any(i["code"]=="invalid_operation" for i in exact_sheet(operation={**op,"engine_version":"unknown"})["issues"])


def encode_synthetic(extracted, byte_order="little"):
    """Test-only reserialization; synthetic bytes, never a native execution."""
    from gene_annotation_episode.hmmer_fm_data import HEADER_FIELDS, SEGMENT_FIELDS, BLOCK_FIELDS
    endian = "<" if byte_order=="little" else ">"
    metadata = extracted["metadata"]
    pieces = [struct.pack(endian+"BBBBIIIHIIQ",*(metadata[k] for k in HEADER_FIELDS))]
    for segment in extracted["segments"]:
        pieces.append(struct.pack(endian+"IQIIHHHH",*(segment[k] for k in SEGMENT_FIELDS)))
        pieces.extend(segment[field].encode("latin1")+b"\0" for field in ("name","acc","source","desc"))
    pieces.extend(struct.pack(endian+"ii",r["lower"],r["upper"]) for r in extracted["ambiguity_ranges"])
    for block in extracted["blocks"]:
        pieces.append(struct.pack(endian+"QIIIIII",*(block["header"][k] for k in BLOCK_FIELDS)))
        for field in ("T","BWT","SA","counters_b","counters_sb"):
            if field not in block["arrays"]:
                continue
            values = block["arrays"][field]["values"]
            fmt = "B" if field in ("T","BWT") else "H" if field=="counters_b" else "I"
            flat = [v for row in values for v in row] if field.startswith("counters_") else values
            pieces.append(struct.pack(endian+fmt*len(flat),*flat))
    return b"".join(pieces)


def test_declared_big_endian_decodes_synthetic_reserialization():
    original = extraction()
    data = encode_synthetic(original,"big")
    changed = extraction(data,abi={**ABI,"byte_order":"big"})
    assert changed["population"]["complete"] is True
    assert changed["blocks"][0]["arrays"]["SA"]["values"] == original["blocks"][0]["arrays"]["SA"]["values"]
    assert changed["metadata"]["total_char_count"] == 28


def test_original_fasta_strings_case_and_two_artifact_occurrences():
    op,inputs,outputs = exact_payloads()
    inputs["source_sequences"] = [artifact(b">seq0 description\r\naCgT\r\n","source_sequences",ordinal=0),
                                 artifact(b">seq0 description\r\naCgT\r\n","source_sequences",ordinal=1)]
    sheet = exact_sheet(inputs=inputs)
    records = [r for r in sheet["input_records"] if r["kind"]=="fasta"]
    assert records[0]["payload"]["raw_header"] == ">seq0 description\r\n"
    assert records[0]["payload"]["sequence"] == "aCgT"
    assert records[0]["payload"]["sequence_lines"] == ["aCgT\r\n"]
    assert [r["source_ordinal"] for r in records] == [0,1]
    assert records[0]["record_key"] != records[1]["record_key"]


@pytest.mark.parametrize("mutation,code",[
    ("sa_out_of_bounds","native_sa_invalid"),
    ("sa_in_range_wrong","native_sa_invalid"),
    ("counter_out_of_bounds","native_counter_invalid"),
    ("counter_in_range_wrong","native_counter_invalid"),
    ("bwt","native_bwt_invalid"),
    ("pair","native_block_pair"),
    ("segment_offset","native_segment_bounds"),
    ("segment_coordinate","native_segment_bounds"),
    ("segment_target_id","native_segment_bounds"),
    ("metadata_partition","native_metadata_partition"),
])
def test_structurally_framed_imports_reject_unsafe_native_indices(mutation,code):
    decoded = extraction()
    first,second = decoded["blocks"]
    if mutation=="sa_out_of_bounds":
        first["arrays"]["SA"]["values"][1] = 0xFFFFFFFF
    elif mutation=="sa_in_range_wrong":
        first["arrays"]["SA"]["values"][1] = (first["arrays"]["SA"]["values"][1]+1)%28
    elif mutation=="counter_out_of_bounds":
        first["arrays"]["counters_sb"]["values"][1][0] = 0xFFFFFFFF
    elif mutation=="counter_in_range_wrong":
        first["arrays"]["counters_b"]["values"][1][0] += 1
    elif mutation=="bwt":
        first["arrays"]["BWT"]["values"][0] ^= 1
    elif mutation=="pair":
        second["header"]["overlap"] = 1
    elif mutation=="segment_offset":
        decoded["segments"][1]["fm_start"] = 15
    elif mutation=="segment_coordinate":
        decoded["segments"][0]["target_start"] = 0
    elif mutation=="segment_target_id":
        decoded["segments"][0]["target_id"] = 0x80000000
    elif mutation=="metadata_partition":
        first["header"]["seq_offset"] = 1
        first["header"]["seq_cnt"] = 1
    result = extraction(encode_synthetic(decoded))
    assert result["population"]["body_complete"] is True
    assert result["population"]["complete"] is False
    assert result["population"]["state"] == "invalid"
    assert code in {i["code"] for i in result["issues"]}
    assert len(result["blocks"]) == 2  # malformed arrays remain retained, not repaired


def test_ambiguity_bounds_and_writer_reader_header_distinction():
    decoded = build_sheet("ambiguous")["database"]
    decoded["ambiguity_ranges"][0]["lower"] = -1
    assert "native_ambiguity_bounds" in {i["code"] for i in extraction(encode_synthetic(decoded))["issues"]}
    for field,value in (("freq_cnt_b",32),("freq_SA",16384)):
        decoded = extraction()
        decoded["metadata"][field] = value
        if field=="freq_SA":
            decoded["blocks"][0]["arrays"]["SA"]["values"] = [0]
        result = extraction(encode_synthetic(decoded))
        assert result["population"]["complete"] is True
        assert result["metadata"]["dna_reader_compatibility"] == "incompatible"
        assert "native_reader_header_incompatible" in {i["code"] for i in result["issues"]}


def test_malformed_public_occurrence_and_operation_do_not_raise():
    data = (NATIVE/"native/makehmmerdb_dna/index.fm").read_bytes()
    result = extract_hmmer_fm_database(data,occurrence=None,producer_contract=ABI)
    assert result["population"]["state"] == "invalid"
    op,inputs,outputs = exact_payloads()
    op["program"] = []
    result = exact_sheet(operation=op)
    assert result["issues"][0]["code"] == "invalid_operation"
