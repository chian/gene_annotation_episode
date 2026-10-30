"""Pure original-record addresses and complete supplied FASTA representation.

An address does not authenticate a source or prove a biological relationship.
Metadata preparation owns byte receipts, declared formats, selected-record
existence, molecule qualification and full-sequence proofs. This module never
opens a file, infers a molecule, translates symbols or interprets a title.
"""
from __future__ import annotations

import hashlib
import re

from .domain import ContractError, parse_sequences


def blast_record_identity(*, source_ref: str, pointer: str,
                          record_locator: dict | None) -> tuple[str, str, str | int]:
    """Validate a closed address without changing its supplied source identity."""
    if not isinstance(source_ref, str) or not source_ref:
        raise ValueError("blast_record_source_invalid")
    if (not isinstance(pointer, str) or not (pointer == "" or pointer.startswith("/"))
            or re.search(r"~(?![01])", pointer) is not None):
        raise ValueError("blast_record_pointer_invalid")
    if record_locator is None:
        return source_ref, "pointer", pointer
    if (not isinstance(record_locator, dict)
            or set(record_locator) != {"kind", "record_ordinal"}
            or record_locator["kind"] != "fasta_record"
            or type(record_locator["record_ordinal"]) is not int
            or record_locator["record_ordinal"] < 0):
        raise ValueError("blast_record_locator_invalid")
    if pointer != "":
        raise ValueError("record_locator_pointer_conflict")
    return source_ref, "fasta_record", record_locator["record_ordinal"]


def parse_blast_fasta_source_records(contents: bytes) -> dict:
    """Represent every original header slot, including incompatible records.

    Byte spans are zero-based, half-open intervals in the complete original
    bytes, including leading header-line whitespace and the original line
    endings. Symbol normalization uses the existing unspecified-molecule FASTA
    parser independently for each slot, so an invalid sibling cannot renumber
    a later record. File digest/size and normalized-symbol digest/length measure
    different representations. All content failures are retained as codes.
    """
    if not isinstance(contents, bytes):
        raise ValueError("blast_fasta_bytes_required")
    result = dict(schema="blast_fasta_source_records_v1",
                  file_sha256=hashlib.sha256(contents).hexdigest(),
                  size_bytes=len(contents), records=[], issues=[])
    try:
        text = contents.decode("utf-8")
    except UnicodeDecodeError:
        result["issues"].append("input_not_utf8")
        return result

    starts, offset = [], 0
    for line in text.splitlines(keepends=True):
        # splitlines follows exactly the existing parser's line convention,
        # including Unicode line separators; byte offsets still address UTF-8.
        line_text = line.splitlines()[0] if line.splitlines() else ""
        if line_text.strip().startswith(">"):
            starts.append((offset, line_text[line_text.index(">") + 1:]))
        elif not starts and line_text.strip():
            if "sequence_before_fasta_header" not in result["issues"]:
                result["issues"].append("sequence_before_fasta_header")
        offset += len(line.encode("utf-8"))
    if not starts and not result["issues"]:
        result["issues"].append("empty_input")

    for ordinal, (start, header) in enumerate(starts):
        end = starts[ordinal + 1][0] if ordinal + 1 < len(starts) else len(contents)
        record = dict(record_ordinal=ordinal, byte_start=start, byte_end=end,
                      header=header, symbols=None, sequence_sha256=None,
                      sequence_length=None, status="incompatible", issues=[])
        try:
            parsed, = parse_sequences(contents[start:end], format="fasta", molecule="unspecified")
        except ContractError as error:
            record["issues"].append(str(error))
        else:
            record.update(symbols=parsed.sequence,
                          sequence_sha256=hashlib.sha256(parsed.sequence.encode("ascii")).hexdigest(),
                          sequence_length=len(parsed.sequence), status="available")
        result["records"].append(record)
    return result


__all__ = ["blast_record_identity", "parse_blast_fasta_source_records"]
