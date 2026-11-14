"""SAM 1.6 native reader; header, optional fields and record identities survive.

The summary functions are shared with BAM because their record semantics match.
They only count native observations; none calculates a scientific component.
"""
from __future__ import annotations

from collections import Counter
import math
import re

from .bvbrc_fastqutils_contracts import validate_native_document
from .bvbrc_fastqutils_identity import native_ref
from .bvbrc_fastqutils_fastq_reader import (
    _document, _locator, _issue, _raw, _population, _cell, _sections, _label,
)


_CIGAR = re.compile(r"([0-9]+)([MIDNSHP=X])")
_INT = re.compile(r"[-+]?[0-9]+\Z")
_TAG = re.compile(r"[A-Za-z][A-Za-z0-9]\Z")
_RANGE = {"c": (-128,127), "C": (0,255), "s": (-32768,32767),
          "S": (0,65535), "i": (-2147483648,2147483647), "I": (0,4294967295)}


def _int(token, low, high):
    if not _INT.fullmatch(token):
        raise ValueError("integer")
    value = int(token)
    if not low <= value <= high:
        raise ValueError("integer_range")
    return value


def _cigar(token):
    if token == "*":
        return []
    pairs = [(int(n), op) for n,op in _CIGAR.findall(token)]
    if not pairs or re.fullmatch(r"(?:[0-9]+[MIDNSHP=X])+", token) is None:
        raise ValueError("cigar")
    if any(op == "H" and i not in (0,len(pairs)-1) for i,(_,op) in enumerate(pairs)):
        raise ValueError("hard_clip")
    for i,(_,op) in enumerate(pairs):
        if op == "S" and any(o != "H" for _,o in pairs[:i]) and any(o != "H" for _,o in pairs[i+1:]):
            raise ValueError("soft_clip")
    return pairs


def _tag(token):
    bits = token.split(":",2)
    if len(bits) != 3 or not _TAG.fullmatch(bits[0]):
        raise ValueError("tag")
    name, kind, native = bits
    row = dict(tag=name, type=kind if kind in "AcCsSiIfZHB" and len(kind)==1 else "unrecognized",
               native_value_token=native, value=None, numeric_array=None, array_subtype=None)
    codes = []
    if kind == "i":
        row["value"] = _int(native, -2147483648, 4294967295)
    elif kind == "f":
        number = float(native)
        if math.isfinite(number): row["value"] = number
        else: codes.append("nonfinite_native")
    elif kind == "A":
        if len(native) != 1 or not 33 <= ord(native) <= 126: raise ValueError("tag_A")
    elif kind == "Z":
        if any(not 32 <= ord(c) <= 126 for c in native): raise ValueError("tag_Z")
    elif kind == "H":
        if re.fullmatch(r"(?:[0-9A-F]{2})*", native) is None: raise ValueError("tag_H")
    elif kind == "B":
        values = native.split(",")
        subtype = values[0]
        if subtype not in _RANGE and subtype != "f": raise ValueError("tag_B")
        row["array_subtype"] = subtype
        row["numeric_array"] = []
        for value in values[1:]:
            if subtype == "f":
                number = float(value)
                if not math.isfinite(number): number = None; codes.append("nonfinite_native")
            else:
                number = _int(value, *_RANGE[subtype])
            row["numeric_array"].append(number)
    else:
        codes.append("unsupported_format")
    return row, codes


def _headers(lines, doc, context, *, member=None, start=0):
    offset = start
    for line in lines:
        ordinal = len(doc["alignment_headers"])
        locator = _locator("bam_header", ordinal, start=offset, end=offset+len(line), member=member)
        offset += len(line)
        try:
            native = line.rstrip(b"\r\n").decode("utf8")
        except UnicodeError:
            _raw(doc, locator, "invalid_utf8_header", kind="header")
            _issue(doc, context, "malformed_native", partial=True)
            continue
        pieces = native.split("\t")
        kind = pieces[0][1:]
        record = dict(id=native_ref("header", context, ordinal), artifact_ref=doc["artifact"]["id"],
            ordinal=ordinal, record_type=kind if kind in ("HD","SQ","RG","PG","CO") else "unrecognized",
            fields=[], comment=pieces[1] if kind=="CO" and len(pieces)>1 else None, locator=locator)
        if record["record_type"] == "unrecognized":
            _raw(doc, locator, "unrecognized_alignment_header", status="unsupported", kind="header")
            _issue(doc, context, "unsupported_report_section", "supported_parser")
        if kind == "CO":
            record["comment"] = native[4:] if native.startswith("@CO\t") else native[3:]
        else:
            for field in pieces[1:]:
                if ":" not in field:
                    _issue(doc, context, "native_header_conflict", "reference_identity")
                    _raw(doc, locator, "malformed_header", kind="header")
                    continue
                key,value = field.split(":",1)
                record["fields"].append(dict(tag=key, native_value=value))
        doc["alignment_headers"].append(record)
        values = {f["tag"]:f["native_value"] for f in record["fields"]}
        if len(values) != len(record["fields"]):
            _issue(doc, context, "native_header_conflict", "reference_identity")
        if kind == "SQ":
            try:
                name = values["SN"]
                length = _int(values["LN"], 1, 2147483647)
                if not name: raise ValueError("empty_reference")
                doc["reference_dictionary"].append(dict(ordinal=len(doc["reference_dictionary"]),
                    name=name, length=length, header_ref=record["id"], md5=values.get("M5")))
            except (ValueError, KeyError):
                _issue(doc, context, "native_header_conflict", "reference_identity")
        if kind == "HD" and "VN" in values:
            _label(doc, context, "native_label", values["VN"], "bam_header", locator)
            if values["VN"] != "1.6":
                _issue(doc, context, "unsupported_version", "native_version")
        if kind == "PG":
            for tag,label in (("PN","aligner"),("VN","producer_version"),("CL","command")):
                if tag in values: _label(doc, context, label, values[tag], "bam_header", locator)


def _header_checks(doc, context):
    references = [r["name"] for r in doc["reference_dictionary"]]
    if len(set(references)) != len(references):
        _issue(doc, context, "native_header_conflict", "reference_identity")
    groups, programs = {}, {}
    for header in doc["alignment_headers"]:
        values = {f["tag"]:f["native_value"] for f in header["fields"]}
        collection = groups if header["record_type"] == "RG" else programs if header["record_type"] == "PG" else None
        if collection is not None:
            if not values.get("ID") or values["ID"] in collection:
                _issue(doc, context, "native_header_conflict", "reference_identity")
            else: collection[values["ID"]] = values
    for value in programs.values():
        if value.get("PP") and value["PP"] not in programs:
            _issue(doc, context, "native_header_conflict", "reference_identity")
    for record in doc["alignment_records"]:
        for token in (record["reference_token"], record["mate_reference_token"]):
            if token is not None and token != "=" and token not in references:
                _issue(doc, context, "unknown_reference", "reference_identity", affected=[record["id"]])
        for tag in record["tags"]:
            if tag["tag"] in ("RG", "PG") and tag["type"] == "Z":
                collection = groups if tag["tag"] == "RG" else programs
                if tag["native_value_token"] not in collection:
                    _issue(doc, context, "native_header_conflict", "reference_identity", affected=[record["id"]])
    if not any(h["record_type"] == "PG" and any(f["tag"]=="VN" for f in h["fields"]) for h in doc["alignment_headers"]):
        _issue(doc, context, "producer_version_unproven", "native_version")
    elif context["producer_version"] is not None:
        reported = [f["native_value"] for h in doc["alignment_headers"] if h["record_type"]=="PG"
                    for f in h["fields"] if f["tag"]=="VN"]
        if context["producer_version"] not in reported:
            _issue(doc, context, "unsupported_version", "native_version")


def _alignment_summary(doc, context, *, bam):
    records = doc["alignment_records"]
    all_records = _population(doc, context, "bam_records", "alignment_records", records)
    primary_rows = [r for r in records if r["flag"] & 0x900 == 0]
    primary = _population(doc, context, "bam_primary_records", "primary_alignment_reads", primary_rows)
    primary["parent_population_refs"] = [all_records["id"]]
    basis = dict(basis="native_bam_phred" if bam else "native_sam_phred",
        encoding="bam_phred" if bam else "phred33", metadata_id=None, evidence=None,
        declaration=None, native_locator=_locator("bam_records",field="QUAL",member="bgzf_decoded_stream" if bam else None))
    missing = any(r["sequence"] is None or r["phred_values"] is None or
                  any(v is None for v in r["phred_values"]) for r in records)
    quality = _population(doc, context, "bam_quality_bases", "fastq_bases", records,
        encoding=basis["encoding"], basis=basis,
        scope="partial" if missing else all_records["scope"])
    quality["parent_population_refs"] = [all_records["id"]]
    for metric,value in (("bam_record_count",len(records)),
                         ("bam_primary_record_count",len(primary_rows)),
                         ("bam_secondary_record_count",sum(bool(r["flag"]&0x100) for r in records)),
                         ("bam_supplementary_record_count",sum(bool(r["flag"]&0x800) for r in records)),
                         ("bam_mapped_primary_count",sum(not r["flag"]&4 for r in primary_rows))):
        _cell(doc, context, metric, value, all_records)
    mapqs = Counter(r["mapq"] for r in records)
    for value,count in sorted(mapqs.items()):
        if value != 255:
            _cell(doc, context, "bam_mapq_histogram_count", count, all_records,
                axis=dict(kind="mapq",label=None,lower=value,upper=value))
    _cell(doc, context, "bam_mapq_unavailable_count", mapqs[255], all_records)
    histogram = Counter(v for r in records for v in (r["phred_values"] or []) if v is not None)
    # Registry places the quality histogram before mapping summary fields.
    mapping_cells = doc["cells"][:]
    doc["cells"].clear()
    for value,count in sorted(histogram.items()):
        _cell(doc, context, "phred_histogram_count", count, quality,
            axis=dict(kind="quality_score",label=None,lower=value,upper=value))
    for cell in mapping_cells:
        cell["id"] = native_ref("cell", context, len(doc["cells"]))
        doc["cells"].append(cell)
    if missing:
        _issue(doc, context, "missing_requested_value", "requested_measurement", affected=[quality["id"]])
    keys = [(r["qname"],r["flag"]&0xC0 if r["flag"]&1 else 0) for r in primary_rows]
    if len(keys) != len(set(keys)):
        _issue(doc, context, "ambiguous_pair_key", "pair_correspondence", affected=[primary["id"]])
    _header_checks(doc, context)
    _sections(doc, ("bam_header", "bam_records", "bam_summary"))


def parse_sam(raw: bytes, *, context: dict) -> dict:
    doc, context = _document(raw, context, "sam_1_6")
    offset = 0
    ordinal = 0
    seen_records = False
    for line in raw.splitlines(keepends=True):
        locator = _locator("bam_records",ordinal,start=offset,end=offset+len(line))
        if line.startswith(b"@"):
            _headers([line],doc,context,start=offset)
            if seen_records: _issue(doc,context,"native_header_conflict","reference_identity")
            offset += len(line)
            continue
        seen_records = True
        offset += len(line)
        try:
            fields = line.rstrip(b"\r\n").decode("ascii").split("\t")
            if len(fields) < 11: raise ValueError("columns")
            qname,flag,reference,pos,mapq,cigar,mate,mpos,tlen,sequence,quality = fields[:11]
            flag = _int(flag,0,65535); pos = _int(pos,0,2147483647)
            mapq = _int(mapq,0,255); mpos = _int(mpos,0,2147483647)
            tlen = _int(tlen,-2147483647,2147483647)
            if re.fullmatch(r"[!-?A-~]{1,254}",qname) is None: raise ValueError("qname")
            pairs = _cigar(cigar)
            if sequence != "*" and re.fullmatch(r"[A-Za-z=.]+",sequence) is None: raise ValueError("sequence")
            if sequence != "*" and pairs and sum(n for n,op in pairs if op in "MIS=X") != len(sequence): raise ValueError("cigar_sequence")
            if quality != "*" and (sequence == "*" or len(quality)!=len(sequence) or any(not 33<=ord(c)<=126 for c in quality)): raise ValueError("quality")
            tags = []
            codes = []
            for token in fields[11:]:
                tag,issues = _tag(token); tags.append(tag); codes.extend(issues)
            if len({t["tag"] for t in tags})!=len(tags): codes.append("malformed_native")
            record = dict(id=native_ref("alignment",context,ordinal), artifact_ref=doc["artifact"]["id"],
                ordinal=ordinal,qname=None if qname=="*" else qname,flag=flag,
                reference_token=None if reference=="*" else reference,position_0=pos-1 if pos else None,
                mapq=mapq,native_cigar=cigar,resolved_cigar=cigar if cigar!="*" else None,
                mate_reference_token=None if mate=="*" else mate,mate_position_0=mpos-1 if mpos else None,
                template_length=tlen,sequence=None if sequence=="*" else sequence,
                phred_values=None if quality=="*" else [ord(c)-33 for c in quality],
                native_quality_symbols=quality,tags=tags,locator=locator)
            doc["alignment_records"].append(record)
            for code in sorted(set(codes)):
                _issue(doc,context,code,"supported_parser" if code=="unsupported_format" else None,
                       partial=code=="unsupported_format",affected=[record["id"]])
                if code=="unsupported_format":
                    _raw(doc,locator,"unresolved_sam_auxiliary_fields",status="unsupported")
        except (ValueError,UnicodeError):
            _raw(doc,locator,"malformed_sam_record")
            _issue(doc,context,"malformed_native",partial=True)
        ordinal += 1
    if raw and not doc["alignment_records"] and not doc["alignment_headers"]:
        doc["parse_scope"] = "malformed"
    _alignment_summary(doc,context,bam=False)
    validate_native_document(doc)
    return doc


__all__ = ["parse_sam"]
