"""Faithful native GenBank record projections, not biological annotations.

The native parser owns what it returned. Original bytes and explicit frame
bounds remain separate from these normalized objects and their nominal positions.
"""
from __future__ import annotations

import io
from collections.abc import Mapping
import warnings

from Bio import SeqIO
from Bio.Seq import UndefinedSequenceError
from Bio.SeqFeature import CompoundLocation, Position, Reference, SimpleLocation

from .domain import ContractError, parse_sequences

REPRESENTATION = "native_genbank_assertions_jsonl_v1"


def native_position(value):
    try:
        number = int(value)
    except TypeError:
        number = None
    return {"class": type(value).__name__, "nominal": number, "text": str(value),
            "attributes": {key: native_value(child) for key, child in vars(value).items()}}


def native_location(value):
    if value is None:
        return None
    if isinstance(value, CompoundLocation):
        return {"class": type(value).__name__, "text": str(value), "operator": value.operator,
                "strand": value.strand, "parts": [native_location(part) for part in value.parts]}
    if isinstance(value, SimpleLocation):
        return {"class": type(value).__name__, "text": str(value),
                "start": native_position(value.start), "end": native_position(value.end),
                "strand": value.strand, "ref": value.ref, "ref_db": value.ref_db}
    raise TypeError("unsupported_native_location_type")


def native_value(value):
    # Most fuzzy positions inherit int: preserve their native class/attributes
    # before considering ordinary scalar values.
    if isinstance(value, Position):
        return native_position(value)
    if isinstance(value, (SimpleLocation, CompoundLocation)):
        return native_location(value)
    if isinstance(value, Reference):
        return {"class": type(value).__name__,
                "attributes": {key: native_value(child) for key, child in vars(value).items()}}
    if value is None or type(value) in {str, bool, int, float}:
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("unsupported_native_mapping_key")
        return {key: native_value(child) for key, child in value.items()}
    if isinstance(value, list):
        return [native_value(child) for child in value]
    if isinstance(value, tuple):
        return {"class": "tuple", "items": [native_value(child) for child in value]}
    raise TypeError("unsupported_native_metadata_type")


def sequence_metadata(sequence):
    data = {"length": len(sequence), "defined": sequence.defined,
            "defined_ranges": [list(pair) for pair in sequence.defined_ranges]}
    if not sequence.defined:
        data["defined_fragments"] = [{"start": start, "end": end, "sequence": str(sequence[start:end])}
                                     for start, end in sequence.defined_ranges]
    return data


def native_record(record):
    return {"id": record.id, "name": record.name, "description": record.description,
            "dbxrefs": native_value(record.dbxrefs), "annotations": native_value(record.annotations),
            "letter_annotations": native_value(record.letter_annotations),
            "sequence": sequence_metadata(record.seq), "feature_count": len(record.features)}


def native_feature(feature, index):
    return {"native_feature_index": index, "id": feature.id, "type": feature.type,
            "location": native_location(feature.location), "qualifiers": native_value(feature.qualifiers),
            "coordinate_meaning": "native_zero_based_nominal_positions_fuzziness_and_part_order_retained"}


def _frames(handle):
    """Recover only at actual left-aligned LOCUS starts, never feature text."""
    frame, start, ordinal = [], None, 0
    while True:
        offset = handle.tell()
        line = handle.readline()
        if not line:
            break
        if line.startswith(b"LOCUS "):
            if frame:
                yield ordinal, start, offset, False, b"".join(frame)
                ordinal += 1
            frame, start = [line], offset
        elif frame:
            frame.append(line)
        elif line.strip():
            yield {"error": {"ordinal": ordinal, "byte_offset": offset,
                             "code": "genbank_content_outside_record"}}
        if frame and line.startswith(b"//"):
            yield ordinal, start, handle.tell(), True, b"".join(frame)
            ordinal += 1
            frame, start = [], None
    if frame:
        yield ordinal, start, handle.tell(), False, b"".join(frame)


def records(handle, *, molecule, name):
    """Yield source entries and independent sequence projections for each frame.

    A successful native parse can still issue warnings or have no defined
    sequence. Such metadata remains accessible, without filling bases, creating
    a target, or claiming the warning-free completeness of the source features.
    """
    seen = {}
    for frame in _frames(handle):
        if isinstance(frame, dict):
            yield frame
            continue
        ordinal, start, end, complete, raw = frame
        native_warnings, record, failure = [], None, None
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                try:
                    record = SeqIO.read(io.StringIO(raw.decode("utf-8")), "genbank")
                finally:
                    native_warnings = [{"category": item.category.__name__, "message": str(item.message)}
                                       for item in caught]
        except Exception as error:
            failure = {"class": type(error).__name__, "message": str(error)}
        entry = {"representation": REPRESENTATION, "record_ordinal": ordinal,
            "meaning": "native_supplied_source_assertions_not_current_target_annotations",
            "source_frame": {"start": start, "end": end, "terminated": complete,
                             "coordinate_system": "parsed_input_source_byte_offsets"},
            "parser_warnings": native_warnings, "parse_failure": failure,
            "native_parser_returned_record": record is not None,
            "record": None}
        if record is not None:
            try:
                entry["record"] = native_record(record)
            except Exception as error:
                entry["metadata_projection_failure"] = {"class": type(error).__name__, "message": str(error)}
                yield {"error": {"ordinal": ordinal, "byte_offset": start,
                                  "code": "genbank_metadata_projection_failed"}}
        yield {"native_entry": entry, "ordinal": ordinal, "entry_kind": "record", "entry_ordinal": 0}
        for index, warning in enumerate(native_warnings):
            yield {"error": {"ordinal": ordinal, "byte_offset": start,
                             "code": "genbank_native_parser_warning", "warning_index": index,
                             "warning_category": warning["category"]}}
        if not complete:
            yield {"error": {"ordinal": ordinal, "byte_offset": start,
                             "code": "genbank_record_terminator_missing"}}
        if record is None:
            yield {"error": {"ordinal": ordinal, "byte_offset": start,
                             "code": "genbank_record_parse_failed"}}
            continue
        for index, feature in enumerate(record.features):
            try:
                data = native_feature(feature, index)
                yield {"native_entry": {"representation": REPRESENTATION, "record_ordinal": ordinal,
                    "meaning": entry["meaning"], "feature": data},
                    "ordinal": ordinal, "entry_kind": "feature", "entry_ordinal": index}
            except Exception as error:
                # Keep exact projection diagnostics in the selected native
                # source, alongside the affected native feature identity.
                # Owner-facing feedback remains a typed ordinal and code.
                yield {"native_entry": {"representation": REPRESENTATION, "record_ordinal": ordinal,
                    "meaning": entry["meaning"], "feature": None,
                    "native_feature_index": index,
                    "projection_failure": {"class": type(error).__name__, "message": str(error)}},
                    "ordinal": ordinal, "entry_kind": "feature", "entry_ordinal": index}
                yield {"error": {"ordinal": ordinal, "byte_offset": start,
                                 "code": "genbank_feature_projection_failed", "feature_ordinal": index}}
        try:
            sequence = str(record.seq)
        except UndefinedSequenceError:
            yield {"error": {"ordinal": ordinal, "byte_offset": start,
                             "code": "genbank_record_sequence_unavailable"}}
            continue
        try:
            parsed = parse_sequences(sequence, format="raw", molecule=molecule, name="genbank")[0]
            occurrence = seen.get(record.id, 0)
            seen[record.id] = occurrence + 1
            yield {"record": {"ordinal": ordinal, "name": record.id, "description": record.description,
                "occurrence": occurrence, "native_title": record.id,
                "header_representation": "biopython_genbank_identifier", "sequence": parsed.sequence,
                "quality": None, "source_byte_offset": start,
                "issues": [*parsed.issues, *(["duplicate_source_identifier"] if occurrence else [])]}}
        except ContractError as error:
            yield {"error": {"ordinal": ordinal, "byte_offset": start, "code": str(error)}}
