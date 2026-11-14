"""Pure, record-preserving FASTQ reader. No quality encoding is inferred.

Counts describe the exact retained artifact, never a biological sample or a
recipe stage. Byte locators in compressed data explicitly name decoded data.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import zlib

from .bvbrc_fastqutils_contracts import (
    FastqUtilsContractError, checked_bytes, validate_contract,
    validate_native_document,
)
from .bvbrc_fastqutils_identity import (
    artifact_ref, native_ref, population_ref, requirement_ref, decode_reference,
)
from .bvbrc_fastqutils_metric_specs import metric_spec


def _locator(block, row=None, field="record", start=None, end=None, member=None):
    return dict(member=member, block=block, block_ordinal=0, row_ordinal=row,
                field=field, byte_start=start, byte_end=end)


def _document(raw, context, expected):
    context = validate_contract("ParseContext", context)
    checked_bytes(raw, content=context["content"])
    if context["declared_format"] != expected:
        raise FastqUtilsContractError("binding_conflict", "/declared_format")
    binding = context["content"]
    artifact = dict(id=artifact_ref(context), source_ref=binding["source_ref"],
        content_ref=binding["artifact_ref"], task_ref=context["task_ref"],
        sha256=binding["sha256"], byte_count=binding["byte_count"],
        native_name=context["native_name"], declared_format=expected,
        actual_format=expected, compression="none", transfer_scope=context["transfer_scope"],
        producer_name=None, producer_version=None, identity=context["identity"],
        document_id=context["document_id"], content_binding=deepcopy(binding))
    doc = dict(schema_version="fastqutils_native_v2", artifact=artifact,
        analysis_id=context["analysis_id"], document_id=context["document_id"],
        parse_scope="complete", cells=[], categories=[], raw_blocks=[],
        sequence_records=[], alignment_records=[], diagnostics=[], sections=[],
        labels=[], populations=[], native_lineage=[], alignment_headers=[],
        reference_dictionary=[], requirements=[])
    if context["transfer_scope"] == "partial":
        _issue(doc, context, "partial_transfer", "complete_native_bytes", partial=True)
    elif context["transfer_scope"] == "unknown":
        _issue(doc, context, "partial_transfer", "complete_native_bytes", state="unresolved")
    if context["producer_version"] is not None:
        _label(doc, context, "producer_version", context["producer_version"],
               "unsupported", _locator("caller_expectation", field="producer_version"))
        _issue(doc, context, "supplied_version_assumption", None)
    return doc, context


def _issue(doc, context, code, required="complete_native_bytes", *, partial=False,
           locator=None, affected=None, state="unavailable"):
    refs = affected or [doc["artifact"]["id"]]
    diagnostic = dict(code=code, source_refs=[doc["artifact"]["source_ref"]],
                      locator=locator, affected_refs=refs)
    if diagnostic not in doc["diagnostics"]:
        doc["diagnostics"].append(diagnostic)
    if required is not None:
        pointer = decode_reference(refs[0])["pointer"]
        requirement = dict(id=requirement_ref(context["analysis_id"], pointer, code),
            code=code, affected_refs=refs, required_data=required, state=state,
            source_refs=[doc["artifact"]["source_ref"]])
        if requirement not in doc["requirements"]:
            doc["requirements"].append(requirement)
    if partial:
        doc["parse_scope"] = "partial"


def _label(doc, context, kind, value, section, locator):
    row = dict(id=native_ref("label", context, len(doc["labels"])),
        artifact_ref=doc["artifact"]["id"], kind=kind, value=value,
        locator=locator, section_key=section, section_ordinal=0)
    doc["labels"].append(row)
    return row


def _raw(doc, locator, name, status="malformed", kind="record"):
    doc["raw_blocks"].append(dict(artifact_ref=doc["artifact"]["id"],
        locator=locator, kind=kind, native_name=name, parse_status=status, field_names=[]))


def _population(doc, context, key, kind, records, *, encoding="unknown", basis=None,
                scope=None):
    scope = scope or (context["transfer_scope"] if doc["parse_scope"] == "complete" else "partial")
    row = dict(id=population_ref(context, key, 0), association_ref=None, kind=kind,
        scope=scope, representation="emitted_bytes", member_artifact_refs=[doc["artifact"]["id"]],
        member_record_refs=[r["id"] for r in records], parent_population_refs=[],
        disjoint_from_refs=[], pair_key_rule=None, quality_encoding=encoding,
        encoding_evidence_refs=[], document_ids=[context["document_id"]], population_key=key,
        population_ordinal=0, section_key="fastq_summary" if key.startswith("fastq") else "bam_summary",
        section_ordinal=0, encoding_basis=basis or dict(basis="unknown", encoding="unknown",
            metadata_id=None, evidence=None, declaration=None, native_locator=None))
    doc["populations"].append(row)
    return row


def _cell(doc, context, metric, value, population, *, axis=None, state=None, codes=None):
    spec = metric_spec(metric)
    section = "fastq_summary" if metric.startswith(("fastq_", "quality_")) else "bam_summary"
    if metric == "phred_histogram_count" and doc["artifact"]["actual_format"] == "fastq":
        section = "fastq_summary"
    row = dict(id=native_ref("cell", context, len(doc["cells"])),
        artifact_ref=doc["artifact"]["id"], locator=_locator(section, field=metric),
        metric=metric, axis=axis or dict(kind="none", label=None, lower=None, upper=None),
        population_ref=population["id"], association_ref=None,
        state=state or ("available" if population["scope"] == "complete" else "partial"),
        value=value, native_token=None, unit=spec["units"][0], meaning=spec["meaning"],
        precision=spec["precision"], diagnostic_codes=codes or [],
        section_key=section, section_ordinal=0)
    doc["cells"].append(row)
    return row


def _sections(doc, keys):
    keys = list(keys)
    if any(row["section_key"] == "unsupported" for row in doc["labels"]) and "unsupported" not in keys:
        keys.append("unsupported")
    for key in keys:
        doc["sections"].append(dict(key=key, ordinal=0, locator=_locator(key),
            state="complete" if doc["parse_scope"] == "complete" else "partial",
            cell_refs=[r["id"] for r in doc["cells"] if r["section_key"] == key],
            category_refs=[], label_refs=[r["id"] for r in doc["labels"] if r["section_key"] == key],
            raw_block_ordinals=[i for i,r in enumerate(doc["raw_blocks"]) if r["locator"]["block"] == key]))


def _gzip(raw, doc, context):
    """Decode concatenated gzip members, retaining the validated stream prefix."""
    if not raw.startswith(b"\x1f\x8b"):
        if (context["native_name"] or "").lower().endswith(".gz"):
            _issue(doc, context, "compression_suffix_mismatch", None)
        return raw, None
    doc["artifact"]["compression"] = "gzip"
    output = bytearray()
    pos = 0
    while pos < len(raw):
        if raw[pos:pos+2] != b"\x1f\x8b":
            _issue(doc, context, "malformed_native", partial=True)
            break
        decoder = zlib.decompressobj(31)
        start = pos
        try:
            while pos < len(raw) and not decoder.eof:
                chunk = raw[pos:pos+65536]
                pos += len(chunk)
                output.extend(decoder.decompress(chunk))
            if decoder.eof:
                pos -= len(decoder.unused_data)
            else:
                _issue(doc, context, "truncated_compressed_stream", partial=True)
                break
        except zlib.error:
            _issue(doc, context, "malformed_native", partial=True)
            _raw(doc, _locator("gzip_member", start=start, end=pos), "invalid_gzip_member")
            break
    return bytes(output), "gzip_decoded_stream"


def parse_fastq(raw: bytes, *, context: dict) -> dict:
    doc, context = _document(raw, context, "fastq")
    data, member = _gzip(raw, doc, context)
    lines = data.splitlines(keepends=True)
    offset = 0
    index = 0
    ordinal = 0
    while index < len(lines):
        start = offset
        title = lines[index].rstrip(b"\r\n")
        if not title.startswith(b"@"):
            _issue(doc, context, "record_boundary_invalid", partial=True)
            _raw(doc, _locator("fastq_records", ordinal, start=start, end=len(data), member=member), "unresolved_fastq_suffix")
            break
        offset += len(lines[index]); index += 1
        seq_parts = []
        while index < len(lines) and not lines[index].startswith(b"+"):
            seq_parts.append(lines[index].rstrip(b"\r\n"))
            offset += len(lines[index]); index += 1
        if index == len(lines):
            _issue(doc, context, "malformed_native", partial=True)
            _raw(doc, _locator("fastq_records", ordinal, start=start, end=len(data), member=member), "missing_fastq_separator")
            break
        separator = lines[index].rstrip(b"\r\n")[1:]
        offset += len(lines[index]); index += 1
        sequence = b"".join(seq_parts)
        qualities = bytearray()
        # The quality boundary is determined ONLY by length, never by '@'.
        while index < len(lines) and (len(qualities) < len(sequence) or not sequence and not qualities):
            quality_line = lines[index].rstrip(b"\r\n")
            qualities.extend(quality_line)
            offset += len(lines[index]); index += 1
            if not sequence:
                break
        locator = _locator("fastq_records", ordinal, start=start, end=offset, member=member)
        if len(qualities) != len(sequence) or (not sequence and not seq_parts):
            _issue(doc, context, "record_boundary_invalid", partial=True)
            _raw(doc, _locator("fastq_records", ordinal, start=start, end=len(data), member=member), "unresolved_fastq_record_and_suffix")
            break
        if separator and separator != title[1:]:
            _issue(doc, context, "malformed_native", partial=True)
            _raw(doc, locator, "fastq_title_separator_conflict")
            ordinal += 1
            continue
        record = dict(id=native_ref("sequence", context, ordinal), artifact_ref=doc["artifact"]["id"],
            ordinal=ordinal, title=title[1:].decode("latin1"), sequence=sequence.decode("latin1"),
            quality_symbols=qualities.decode("latin1"), phred_values=None, locator=locator)
        doc["sequence_records"].append(record)
        ordinal += 1
        if any(chr(b).upper() not in "ACGTNRYSWKMBDHV" for b in sequence):
            _issue(doc, context, "invalid_sequence_symbol", None, affected=[record["id"]])
        if any(b < 33 or b > 126 for b in qualities):
            _issue(doc, context, "invalid_quality_score", "quality_encoding", affected=[record["id"]], state="incompatible")
    if not doc["sequence_records"] and data and doc["parse_scope"] == "partial":
        doc["parse_scope"] = "malformed"
    records = doc["sequence_records"]
    reads = _population(doc, context, "fastq_reads", "fastq_reads", records)
    bases = _population(doc, context, "fastq_bases", "fastq_bases", records)
    quality = _population(doc, context, "fastq_quality_characters", "fastq_bases", records)
    counts = Counter()
    lengths = Counter()
    chars = Counter()
    for record in records:
        lengths[len(record["sequence"])] += 1
        for symbol in record["sequence"].upper():
            counts[symbol if symbol in "ACGTN" else "other_iupac" if symbol in "RYSWKMBDHV" else "invalid"] += 1
        chars.update(ord(c) for c in record["quality_symbols"])
    _cell(doc, context, "fastq_read_count", len(records), reads)
    _cell(doc, context, "fastq_base_count", sum(counts.values()), bases)
    for symbol in ("A", "C", "G", "T", "N", "other_iupac", "invalid"):
        _cell(doc, context, "fastq_symbol_count", counts[symbol], bases,
              axis=dict(kind="symbol", label=symbol, lower=None, upper=None))
    for metric, value in (("fastq_min_length", min(lengths) if lengths else None),
                          ("fastq_max_length", max(lengths) if lengths else None)):
        _cell(doc, context, metric, value, reads, state="undefined" if value is None else None,
              codes=["zero_denominator"] if value is None else [])
    for length, count in sorted(lengths.items()):
        _cell(doc, context, "fastq_length_histogram_count", count, reads,
              axis=dict(kind="length_closed", label=None, lower=length, upper=length))
    for char, count in sorted(chars.items()):
        _cell(doc, context, "quality_character_count", count, quality,
              axis=dict(kind="quality_ascii", label=chr(char), lower=char, upper=char))
    _issue(doc, context, "unknown_quality_encoding", "quality_encoding", affected=[quality["id"]])
    _issue(doc, context, "producer_version_unproven", "native_version")
    _sections(doc, ("fastq_records", "fastq_summary"))
    validate_native_document(doc)
    return doc


__all__ = ["parse_fastq"]
