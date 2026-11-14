"""Standard-library BAM1/BGZF reader over supplied bytes only.

No BAI inference, program invocation or reference acquisition. Length fields are
bounded against actual bytes before allocation. A bad bounded record does not
erase intact later records. A broken compressed block ends the reliable prefix.
"""
from __future__ import annotations

import math
import struct
import zlib

from .bvbrc_fastqutils_contracts import validate_native_document
from .bvbrc_fastqutils_identity import native_ref
from .bvbrc_fastqutils_fastq_reader import _document, _locator, _issue, _raw
from .bvbrc_fastqutils_sam_reader import _headers, _alignment_summary, _TAG, _cigar


_NUMERIC = {"c":"b", "C":"B", "s":"h", "S":"H", "i":"i", "I":"I", "f":"f"}
_BASES = "=ACMGRSVTWYHKDBN"
_OPS = "MIDNSHP=X"


class _Cursor:
    def __init__(self, raw):
        self.raw = raw
        self.pos = 0

    def take(self, size):
        if size < 0 or size > len(self.raw)-self.pos:
            raise ValueError("bounded_length")
        start = self.pos
        self.pos += size
        return self.raw[start:self.pos]

    def unpack(self, fmt):
        return struct.unpack("<"+fmt, self.take(struct.calcsize("<"+fmt)))

    def cstring(self):
        end = self.raw.find(b"\0", self.pos)
        if end < 0: raise ValueError("unterminated_string")
        value = self.take(end-self.pos)
        self.take(1)
        return value


def _bgzf(raw, doc, context):
    stream = bytearray()
    pos = 0
    final_empty = False
    while pos < len(raw):
        start = pos
        try:
            if len(raw)-pos < 12:
                raise EOFError
            if raw[pos:pos+4] != b"\x1f\x8b\x08\x04":
                raise ValueError("bgzf_header")
            extra_size = struct.unpack_from("<H",raw,pos+10)[0]
            extra_end = pos+12+extra_size
            if extra_end > len(raw): raise EOFError
            cursor = _Cursor(raw[pos+12:extra_end])
            block_sizes = []
            while cursor.pos < len(cursor.raw):
                name = cursor.take(2)
                length, = cursor.unpack("H")
                payload = cursor.take(length)
                if name == b"BC":
                    if length != 2: raise ValueError("bc_size")
                    block_sizes.append(struct.unpack("<H",payload)[0]+1)
            if len(block_sizes) != 1: raise ValueError("bc_missing_or_duplicate")
            size = block_sizes[0]
            if size < extra_size+20 or size > 65536: raise ValueError("bsize")
            if size > len(raw)-pos: raise EOFError
            end = pos+size
            crc, expected_size = struct.unpack_from("<II",raw,end-8)
            if expected_size > 65536: raise ValueError("isize_limit")
            decoder = zlib.decompressobj(-15)
            value = decoder.decompress(raw[extra_end:end-8],65537)
            if len(value)>65536 or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                raise ValueError("deflate_boundary")
            if len(value) != expected_size or zlib.crc32(value)&0xffffffff != crc:
                raise ValueError("crc_or_isize")
            stream.extend(value)
            final_empty = not value
            pos = end
        except EOFError:
            _issue(doc,context,"truncated_compressed_stream",partial=True)
            _raw(doc,_locator("bgzf_block",start=start,end=len(raw)),"truncated_bgzf_block")
            break
        except (ValueError,struct.error,zlib.error):
            _issue(doc,context,"malformed_native",partial=True)
            _raw(doc,_locator("bgzf_block",start=start,end=len(raw)),"invalid_bgzf_block")
            break
    if not final_empty or pos != len(raw):
        _issue(doc,context,"missing_bgzf_eof",partial=True)
    return bytes(stream)


def _decode_cigar(words):
    pairs = []
    for word in words:
        op = word & 15
        length = word >> 4
        if op >= len(_OPS): raise ValueError("cigar_operation")
        pairs.append(str(length)+_OPS[op])
    return "".join(pairs) or "*"


def _tags(cursor):
    tags, issues = [], []
    while cursor.pos < len(cursor.raw):
        name = cursor.take(2).decode("ascii")
        if not _TAG.fullmatch(name): raise ValueError("tag_name")
        kind = cursor.take(1).decode("ascii")
        start = cursor.pos
        tag = dict(tag=name,type=kind if kind in "AcCsSiIfZHB" else "unrecognized",
                   native_value_token="",value=None,numeric_array=None,array_subtype=None)
        if kind in _NUMERIC:
            number, = cursor.unpack(_NUMERIC[kind])
            tag["value"] = number if math.isfinite(number) else None
            if tag["value"] is None: issues.append("nonfinite_native")
        elif kind == "A":
            value = cursor.take(1)
            if not 33 <= value[0] <= 126: raise ValueError("tag_A")
            tag["native_value_token"] = value.decode("ascii")
        elif kind in ("Z","H"):
            value = cursor.cstring()
            if any(not 32<=b<=126 for b in value): raise ValueError("tag_string")
            if kind == "H" and (len(value)%2 or any(b not in b"0123456789ABCDEF" for b in value)):
                raise ValueError("tag_hex")
            tag["native_value_token"] = value.decode("ascii")
        elif kind == "B":
            subtype = cursor.take(1).decode("ascii")
            if subtype not in _NUMERIC: raise ValueError("tag_subtype")
            count, = cursor.unpack("I")
            size = struct.calcsize("<"+_NUMERIC[subtype])
            if count > (len(cursor.raw)-cursor.pos)//size: raise ValueError("tag_array_length")
            tag["array_subtype"] = subtype
            tag["numeric_array"] = []
            for item, in struct.iter_unpack("<"+_NUMERIC[subtype],cursor.take(count*size)):
                tag["numeric_array"].append(item if math.isfinite(item) else None)
                if not math.isfinite(item): issues.append("nonfinite_native")
        else:
            cursor.take(len(cursor.raw)-cursor.pos)
            issues.append("unsupported_format")
        if kind not in ("A","Z","H"):
            tag["native_value_token"] = "hex:"+cursor.raw[start:cursor.pos].hex()
        tags.append(tag)
        if kind not in "AcCsSiIfZHB": break
    if len({r["tag"] for r in tags})!=len(tags): issues.append("malformed_native")
    return tags, issues


def _record(block, ordinal, locator, doc, context):
    cursor = _Cursor(block)
    refid,pos,bin_mq_nl,flag_nc,length,nextid,nextpos,tlen = cursor.unpack("iiIIIiii")
    name_length = bin_mq_nl & 255
    mapq = (bin_mq_nl>>8)&255
    flag = flag_nc>>16
    cigar_count = flag_nc&65535
    refs = doc["reference_dictionary"]
    if not -1<=refid<len(refs) or not -1<=nextid<len(refs) or pos < -1 or nextpos < -1:
        raise ValueError("reference_or_position")
    if not name_length: raise ValueError("read_name_length")
    name = cursor.take(name_length)
    if name[-1:]!=b"\0" or b"\0" in name[:-1]: raise ValueError("read_name_nul")
    qname = name[:-1].decode("ascii")
    if not qname or len(qname)>254 or any(not 33<=ord(c)<=126 or c=="@" for c in qname):
        raise ValueError("qname")
    cigar_words = [v for v, in struct.iter_unpack("<I",cursor.take(4*cigar_count))]
    native_cigar = _decode_cigar(cigar_words)
    packed = cursor.take((length+1)//2)
    sequence = "".join(_BASES[(packed[i//2]>>(4 if i%2==0 else 0))&15] for i in range(length))
    quals = cursor.take(length)
    if quals and all(q==255 for q in quals):
        values = None
    else:
        values = [q if q<=93 else None for q in quals] if length else None
    tags,issues = _tags(cursor)
    if any(q>93 and q!=255 for q in quals) or (quals and any(q==255 for q in quals) and values is not None):
        issues.append("invalid_quality_score")
    resolved = native_cigar if native_cigar!="*" else None
    cg = [t for t in tags if t["tag"]=="CG"]
    if len(cigar_words)==2 and (cigar_words[0]&15)==4 and (cigar_words[0]>>4)==length and (cigar_words[1]&15)==3 and cg:
        if len(cg)!=1 or cg[0]["type"]!="B" or cg[0]["array_subtype"]!="I":
            raise ValueError("long_cigar_tag")
        resolved = _decode_cigar(cg[0]["numeric_array"])
        pairs = _cigar(resolved)
        if sum(n for n,op in pairs if op in "MDN=X") != cigar_words[1]>>4:
            raise ValueError("long_cigar_span")
    pairs = _cigar(resolved) if resolved else []
    if length and pairs and sum(n for n,op in pairs if op in "MIS=X")!=length:
        raise ValueError("cigar_query_span")
    row = dict(id=native_ref("alignment",context,ordinal),artifact_ref=doc["artifact"]["id"],ordinal=ordinal,
        qname=None if qname=="*" else qname,flag=flag,
        reference_token=None if refid==-1 else refs[refid]["name"],position_0=None if pos==-1 else pos,
        mapq=mapq,native_cigar=native_cigar,resolved_cigar=resolved,
        mate_reference_token=None if nextid==-1 else refs[nextid]["name"],
        mate_position_0=None if nextpos==-1 else nextpos,template_length=tlen,
        sequence=sequence if length else None,phred_values=values,native_quality_symbols=None,
        tags=tags,locator=locator)
    return row,issues


def parse_bam(raw: bytes, *, context: dict) -> dict:
    doc,context = _document(raw,context,"bam_1")
    doc["artifact"]["compression"] = "bgzf" if raw.startswith(b"\x1f\x8b") else "none"
    if not raw.startswith(b"\x1f\x8b"):
        doc["parse_scope"] = "malformed"
        _issue(doc,context,"unsupported_format","supported_parser")
        _raw(doc,_locator("bam_header",start=0,end=len(raw)),"non_bgzf_bam")
        _alignment_summary(doc,context,bam=True)
        validate_native_document(doc)
        return doc
    stream = _bgzf(raw,doc,context)
    cursor = _Cursor(stream)
    try:
        if cursor.take(4)!=b"BAM\x01": raise ValueError("magic")
        header_length, = cursor.unpack("I")
        if header_length >= 2**31: raise ValueError("header_length")
        header_bytes = cursor.take(header_length)
        header_text = header_bytes.rstrip(b"\0")
        if b"\0" in header_text: raise ValueError("header_nul")
        _headers(header_text.splitlines(keepends=True),doc,context,member="bgzf_decoded_stream",start=8)
        text_refs = doc["reference_dictionary"][:]
        count, = cursor.unpack("I")
        if count >= 2**31 or count > (len(stream)-cursor.pos)//9: raise ValueError("reference_count")
        doc["reference_dictionary"] = []
        for ordinal in range(count):
            name_size, = cursor.unpack("I")
            if not name_size: raise ValueError("reference_name_size")
            name = cursor.take(name_size)
            if name[-1:]!=b"\0" or b"\0" in name[:-1]: raise ValueError("reference_name_nul")
            length, = cursor.unpack("I")
            if length>=2**31: raise ValueError("reference_length")
            name = name[:-1].decode("ascii")
            if not name: raise ValueError("empty_reference_name")
            matching = [r for r in text_refs if r["name"]==name and r["length"]==length]
            doc["reference_dictionary"].append(dict(ordinal=ordinal,name=name,length=length,
                header_ref=matching[0]["header_ref"] if len(matching)==1 else None,
                md5=matching[0]["md5"] if len(matching)==1 else None))
        if text_refs and [(r["name"],r["length"]) for r in text_refs] != [(r["name"],r["length"]) for r in doc["reference_dictionary"]]:
            _issue(doc,context,"native_header_conflict","reference_identity")
    except (ValueError,UnicodeError,struct.error):
        _issue(doc,context,"malformed_native",partial=True)
        doc["parse_scope"] = "malformed"
        _raw(doc,_locator("bam_header",start=0,end=len(stream),member="bgzf_decoded_stream"),"unresolved_bam_header")
        _alignment_summary(doc,context,bam=True)
        validate_native_document(doc)
        return doc
    ordinal = 0
    while cursor.pos < len(stream):
        start = cursor.pos
        try:
            size, = cursor.unpack("I")
            if size > len(stream)-cursor.pos: raise ValueError("record_length")
            block = cursor.take(size)
        except (ValueError,struct.error):
            _issue(doc,context,"record_boundary_invalid",partial=True)
            _raw(doc,_locator("bam_records",ordinal,start=start,end=len(stream),member="bgzf_decoded_stream"),"unresolved_bam_suffix")
            break
        locator = _locator("bam_records",ordinal,start=start,end=cursor.pos,member="bgzf_decoded_stream")
        try:
            row,issues = _record(block,ordinal,locator,doc,context)
            doc["alignment_records"].append(row)
            for code in sorted(set(issues)):
                _issue(doc,context,code,"supported_parser" if code=="unsupported_format" else None,
                    partial=code=="unsupported_format",affected=[row["id"]])
                if code=="unsupported_format": _raw(doc,locator,"unresolved_bam_auxiliary_fields",status="unsupported")
        except (ValueError,UnicodeError,struct.error):
            _raw(doc,locator,"malformed_bounded_bam_record")
            _issue(doc,context,"malformed_native",partial=True)
        ordinal += 1
    _alignment_summary(doc,context,bam=True)
    validate_native_document(doc)
    return doc


__all__ = ["parse_bam"]
