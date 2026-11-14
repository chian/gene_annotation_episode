"""Source-preserving representation parsing, independent of biological identity."""
from __future__ import annotations

from importlib.metadata import version

from Bio.SeqIO.QualityIO import FastqGeneralIterator

from .domain import ContractError, parse_sequences

VERSION = "supplied_material_parsing_v5.biopython_" + version("biopython")
FORMATS = ["auto", "raw", "fasta", "fastq", "text", "opaque", "genbank"]


def recognize(prefix: bytes) -> str:
    """Recognize wrappers; unknown content is never silently raw sequence."""
    prefix = prefix.lstrip()
    if prefix.startswith(b">"):
        return "fasta"
    if prefix.startswith(b"@"):
        return "fastq"
    if prefix.startswith(b"LOCUS "):
        return "genbank"
    return "unknown"


def _record(header, sequence, quality, ordinal, offset, molecule, seen,
            title_representation="parser_returned_title"):
    fields = header.strip().split(maxsplit=1)
    if not fields:
        raise ContractError("empty_sequence_identifier")
    if callable(seen):
        occurrence = seen(fields[0])
    else:
        occurrence = seen.get(fields[0], 0)
        seen[fields[0]] = occurrence + 1
    parsed = parse_sequences(sequence, format="raw", molecule=molecule, name=fields[0])[0]
    issues = list(parsed.issues)
    if occurrence:
        issues.append("duplicate_source_identifier")
    if quality is not None and (not quality.isascii() or len(quality) != len(parsed.sequence)):
        raise ContractError("quality_sequence_representation_mismatch")
    return {"ordinal": ordinal, "name": parsed.name,
        "description": fields[1] if len(fields) > 1 else "", "occurrence": occurrence,
        "native_title": header, "header_representation": title_representation,
        "sequence": parsed.sequence, "quality": quality,
        "source_byte_offset": offset, "issues": issues}


def records(handle, representation, *, molecule, name, occurrences=None):
    """Yield independent records or precise parse feedback, retaining valid work.

    FASTA recovers at an explicit next header. FASTQ uses Biopython's wrapped-
    record parser; after malformed input it retains the valid prefix and reports
    the remaining scope unresolved rather than guessing that @ in quality is a
    new record boundary. No quality score encoding or molecule is inferred.
    """
    seen = occurrences if occurrences is not None else {}
    if representation == "genbank":
        from .genbank_intake import records as genbank_records
        yield from genbank_records(handle, molecule=molecule, name=name)
        return
    if representation == "raw":
        try:
            text = handle.read().decode("utf-8")
            yield {"record": _record(name, text, None, 0, 0, molecule, seen,
                                     title_representation="caller_material_name")}
        except (ContractError, UnicodeError) as error:
            yield {"error": {"ordinal": 0, "byte_offset": 0,
                "code": str(error) if isinstance(error, ContractError) else "input_not_utf8"}}
        return
    if representation == "fastq":
        import io
        text = io.TextIOWrapper(handle, encoding="utf-8", newline=None)
        ordinal = 0
        try:
            for header, sequence, quality in FastqGeneralIterator(text):
                try:
                    yield {"record": _record(header, sequence, quality, ordinal, None, molecule, seen)}
                except ContractError as error:
                    yield {"error": {"ordinal": ordinal, "byte_offset": None, "code": str(error)}}
                ordinal += 1
        except (ValueError, UnicodeError):
            yield {"error": {"ordinal": ordinal, "byte_offset": None,
                "code": "malformed_fastq_remaining_scope_unparsed"}}
        finally:
            text.detach()
        return
    if representation != "fasta":
        return
    header, sequence, offset, ordinal = None, [], None, 0

    def finish():
        try:
            return {"record": _record(header, "".join(sequence), None, ordinal, offset, molecule, seen)}
        except ContractError as error:
            return {"error": {"ordinal": ordinal, "byte_offset": offset, "code": str(error)}}

    while True:
        position = handle.tell()
        raw = handle.readline()
        if not raw:
            break
        try:
            line = raw.decode("utf-8").strip()
        except UnicodeError:
            yield {"error": {"ordinal": ordinal, "byte_offset": position, "code": "input_not_utf8"}}
            # Make this record unrepresentable, never join across a bad line.
            sequence.append("\x00")
            continue
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                yield finish()
                ordinal += 1
            header, sequence, offset = line[1:], [], position
        elif header is None:
            yield {"error": {"ordinal": ordinal, "byte_offset": position,
                "code": "sequence_before_fasta_header"}}
        else:
            sequence.append(line)
    if header is not None:
        yield finish()
