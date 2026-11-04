"""Synthetic SAM/BAM/BGZF byte oracles from the retained SAM 1.6 grammar."""
import json
import math
import struct
import zlib
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_fastqutils_bam_reader import parse_bam
from gene_annotation_episode.bvbrc_fastqutils_sam_reader import parse_sam
from test_bvbrc_fastqutils_sequence_formats import context, value


EOF=bytes.fromhex("1f8b08040000000000ff0600424302001b0003000000000000000000")


def block(data):
    encoder=zlib.compressobj(wbits=-15)
    payload=encoder.compress(data)+encoder.flush()
    header=b"\x1f\x8b\x08\x04"+b"\0"*4+b"\0\xff"+struct.pack("<H",6)+b"BC"+struct.pack("<H",2)
    return header+struct.pack("<H",len(payload)+25)+payload+struct.pack("<II",zlib.crc32(data)&0xffffffff,len(data))


def record(name="read",flag=0,sequence="AC",qualities=b"\x1e\x28",mapq=60,tags=b"",cigar=None):
    encoded=name.encode()+b"\0"
    if cigar is None: cigar=[len(sequence)<<4] if sequence else []
    core=struct.pack("<iiIIIiii",0,0,len(encoded)|(mapq<<8),len(cigar)|(flag<<16),len(sequence),-1,-1,0)
    alphabet="=ACMGRSVTWYHKDBN"
    numbers=[alphabet.index(c) for c in sequence]
    packed=bytes((numbers[i]<<4)|(numbers[i+1] if i+1<len(numbers) else 0) for i in range(0,len(numbers),2))
    body=core+encoded+b"".join(struct.pack("<I",x) for x in cigar)+packed+qualities+tags
    return struct.pack("<I",len(body))+body


def bam(records=(),header=b"@HD\tVN:1.6\n@SQ\tSN:ref\tLN:100\n",reference_length=100,eof=True):
    plain=b"BAM\x01"+struct.pack("<I",len(header))+header+struct.pack("<I",1)+struct.pack("<I",4)+b"ref\0"+struct.pack("<I",reference_length)+b"".join(records)
    return b"".join(block(plain[i:i+50000]) for i in range(0,len(plain),50000))+(EOF if eof else b"")


def read(raw): return parse_bam(raw,context=context(raw,"bam_1","fixture.bam"))


def test_sam_coordinates_flags_quality_and_all_text_tag_types():
    raw=(b"@HD\tVN:1.6\n@SQ\tSN:ref\tLN:100\tM5:abc\n@RG\tID:group\tSM:sample\n"
         b"@PG\tID:aligner\tPN:synthetic\tVN:1.0\tCL:synthetic --arg\n@CO\ttabs\tremain\n"
         b"read\t0\tref\t1\t255\t2M\t=\t5\t-4\tAC\t!I\tRG:Z:group\tPG:Z:aligner\tAA:A:X\tNM:i:0\tFF:f:1.5\tHX:H:00FF\tAR:B:i,-2,4\tNF:f:nan\n"
         b"read\t256\tref\t2\t30\t2M\t*\t0\t0\tAC\t*\n"
         b"read\t2048\tref\t3\t20\t2M\t*\t0\t0\tAC\tII\n")
    result=parse_sam(raw,context=context(raw,"sam_1_6","fixture.sam"))
    first=result["alignment_records"][0]
    assert first["position_0"]==0 and first["mate_position_0"]==4
    assert first["native_quality_symbols"]=="!I" and first["phred_values"]==[0,40]
    assert first["tags"][-1]["value"] is None
    assert first["tags"][-1]["native_value_token"]=="nan"
    assert result["alignment_headers"][-1]["comment"]=="tabs\tremain"
    assert result["reference_dictionary"][0]["md5"]=="abc"
    assert value(result,"bam_record_count")==3
    assert value(result,"bam_primary_record_count")==1
    assert value(result,"bam_mapq_unavailable_count")==1
    assert [p for p in result["populations"] if p["population_key"]=="bam_quality_bases"][0]["encoding_basis"]["basis"]=="native_sam_phred"
    json.dumps(result,allow_nan=False)


def test_sam_bad_record_and_header_conflicts_retain_siblings():
    raw=(b"@SQ\tSN:ref\tLN:100\n@SQ\tSN:ref\tLN:99\n"
         b"broken\t0\tref\t1\t60\t2M\t*\t0\t0\tA\t!\n"
         b"good\t4\tmissing\t1\t60\t1M\t*\t0\t0\tA\t!\n")
    result=parse_sam(raw,context=context(raw,"sam_1_6"))
    assert [r["qname"] for r in result["alignment_records"]]==["good"]
    assert result["parse_scope"]=="partial"
    assert {"native_header_conflict","unknown_reference"} <= {r["code"] for r in result["diagnostics"]}


def test_bam_all_auxiliary_types_missing_quality_and_nonfinite():
    tags=b"AAAX"+b"CCc"+struct.pack("<b",-2)+b"DDC"+struct.pack("<B",254)+b"EEs"+struct.pack("<h",-300)
    tags+=b"FFS"+struct.pack("<H",60000)+b"GGi"+struct.pack("<i",-100000)+b"HHI"+struct.pack("<I",4000000000)
    tags+=b"IIf"+struct.pack("<f",1.5)+b"JJZtext\0"+b"KKH00FF\0"
    for i,(subtype,fmt,val) in enumerate((('c','b',-1),('C','B',255),('s','h',-2),('S','H',65535),('i','i',-3),('I','I',4294967295),('f','f',float('nan')))):
        tags+=('L'+str(i)).encode()+b"B"+subtype.encode()+struct.pack("<I",1)+struct.pack('<'+fmt,val)
    tags+=b"NNf"+struct.pack("<f",float("inf"))
    result=read(bam([record(tags=tags),record("missing",qualities=b"\xff\xff",mapq=255),record("secondary",flag=256),record("supplementary",flag=2048)]))
    assert len(result["alignment_records"])==4
    first=result["alignment_records"][0]
    assert first["native_quality_symbols"] is None
    assert {r["type"] for r in first["tags"]}==set("AcCsSiIfZHB")
    assert first["tags"][-2]["numeric_array"]==[None]
    assert first["tags"][-1]["value"] is None
    assert result["alignment_records"][1]["phred_values"] is None
    assert value(result,"bam_record_count")==4
    assert value(result,"bam_mapped_primary_count")==2
    assert value(result,"bam_secondary_record_count")==1
    assert value(result,"bam_supplementary_record_count")==1
    assert value(result,"bam_mapq_unavailable_count")==1
    json.dumps(result,allow_nan=False)


def test_long_cigar_keeps_placeholder_and_native_cg_tag():
    words=[16]*65536
    raw=bam([record(sequence="A"*65536,qualities=bytes([30])*65536,
                    cigar=[65536<<4|4,65536<<4|3],
                    tags=b"CGBI"+struct.pack("<I",len(words))+struct.pack("<"+"I"*len(words),*words))],reference_length=100000,
            header=b"@HD\tVN:1.6\n@SQ\tSN:ref\tLN:100000\n")
    result=read(raw)
    row=result["alignment_records"][0]
    assert row["native_cigar"]=="65536S65536N"
    assert row["resolved_cigar"]=="1M"*65536
    assert len(row["tags"][0]["numeric_array"])==65536


@pytest.mark.parametrize("change",["crc","isize","bc","truncated","missing_eof"])
def test_bgzf_integrity_failures(change):
    raw=bam([record()])
    if change=="missing_eof": raw=raw[:-len(EOF)]
    elif change=="truncated": raw=raw[:-len(EOF)-3]
    else:
        mutable=bytearray(raw)
        first_size=struct.unpack_from("<H",raw,16)[0]+1
        index=first_size-8 if change=="crc" else first_size-4 if change=="isize" else 12
        mutable[index]^=1; raw=bytes(mutable)
    result=read(raw)
    assert result["parse_scope"]!="complete"
    assert result["requirements"]
    if change=="missing_eof": assert len(result["alignment_records"])==1


def test_bounded_bad_record_keeps_later_sibling_and_unknown_tag_raw():
    malformed=struct.pack("<I",3)+b"bad"
    result=read(bam([record("first"),malformed,record("last")]))
    assert [r["qname"] for r in result["alignment_records"]]==["first","last"]
    assert result["alignment_records"][-1]["ordinal"]==2
    assert result["parse_scope"]=="partial"
    unknown=read(bam([record(tags=b"XXd"+b"abcdefgh"),record("last")]))
    assert unknown["alignment_records"][0]["tags"][0]["type"]=="unrecognized"
    assert unknown["alignment_records"][-1]["qname"]=="last"
    assert unknown["raw_blocks"]


def test_binary_dictionary_conflict_duplicate_primaries_and_mixed_missing_mask():
    result=read(bam([record(),record(qualities=b"\xff\x1e")],reference_length=200))
    codes={d["code"] for d in result["diagnostics"]}
    assert {"native_header_conflict","ambiguous_pair_key","invalid_quality_score"} <= codes
    assert result["alignment_records"][1]["phred_values"]==[None,30]
    assert result["reference_dictionary"][0]["length"]==200


def test_internal_eof_block_and_uncompressed_bam_rejection():
    compressed=bam([record()])
    result=read(compressed+block(record("appended"))+EOF)
    assert [r["qname"] for r in result["alignment_records"]]==["read","appended"]
    assert read(b"BAM\x01")["parse_scope"]=="malformed"


def test_sam_lexical_cigar_zero_count_arrays_and_version_expectation():
    raw=(b"@HD\tVN:1.6\n@SQ\tSN:ref\tLN:100\n@PG\tID:tool\tVN:reported\n"
         b"r\t0\tref\t1\t1\t01M\t*\t0\t0\tA\t+\tBA:B:i\tZZ:Z:\tHH:H:\n")
    source=context(raw,"sam_1_6"); source["producer_version"]="caller-expectation"
    result=parse_sam(raw,context=source)
    assert result["alignment_records"][0]["native_cigar"]=="01M"
    assert result["alignment_records"][0]["tags"][0]["numeric_array"]==[]
    assert "unsupported_version" in {r["code"] for r in result["diagnostics"]}
    assert {r["value"] for r in result["labels"] if r["kind"]=="producer_version"}=={"reported","caller-expectation"}


def test_bad_bam_array_length_and_record_length_never_allocate_declared_size():
    invalid=record("bad",tags=b"ARBf"+struct.pack("<I",4294967295))
    result=read(bam([invalid,record("good")]))
    assert [r["qname"] for r in result["alignment_records"]]==["good"]
    result=read(bam([record("good"),struct.pack("<I",4294967295)]))
    assert [r["qname"] for r in result["alignment_records"]]==["good"]
    assert result["parse_scope"]=="partial"


def test_duplicate_tags_are_preserved_and_invalid_header_bytes_are_raw():
    raw=(b"@CO\t\xff\n@SQ\tSN:ref\tLN:100\n"
         b"r\t0\tref\t1\t60\t1M\t*\t0\t0\tA\t!\tNM:i:0\tNM:i:1\n")
    result=parse_sam(raw,context=context(raw,"sam_1_6"))
    assert [t["value"] for t in result["alignment_records"][0]["tags"]]==[0,1]
    assert result["raw_blocks"][0]["native_name"]=="invalid_utf8_header"
    assert "malformed_native" in {d["code"] for d in result["diagnostics"]}


def test_retained_handcrafted_alignment_fixture_bytes():
    directory=Path(__file__).parent/"fixtures/bvbrc_fastqutils/alignment"
    for name,count,scope in (("mapped_and_unmapped.bam",3,"complete"),
                             ("auxiliary_types.bam",2,"complete"),("bounded_bad_record.bam",2,"partial")):
        result=read((directory/name).read_bytes())
        assert len(result["alignment_records"])==count
        assert result["parse_scope"]==scope
    raw=(directory/"records.sam").read_bytes()
    assert len(parse_sam(raw,context=context(raw,"sam_1_6"))["alignment_records"])==3
