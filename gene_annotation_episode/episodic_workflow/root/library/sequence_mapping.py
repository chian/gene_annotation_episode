"""Exact coordinate arithmetic over an explicitly observed derivation path.

Paths retain the supplied segment order and orientation. They do not infer a
mapping from sequence lengths or label a biological gene model as correct.
ToolRegistry binds these paths to native source-preserving sequence operations.
"""
from __future__ import annotations

from copy import deepcopy


VERSION = "oriented_source_subject_path_v2"


def path_length(path: list[dict]) -> int:
    """Validate representation and return the length in physical source units."""
    if not isinstance(path, list) or not path:
        raise ValueError("mapping_path_required")
    length = 0
    for row in path:
        if not isinstance(row, dict) or set(row) != {"subject_ref", "start", "end", "unit", "strand"}:
            raise ValueError("invalid_mapping_segment")
        if (not isinstance(row["subject_ref"], str) or not row["subject_ref"]
                or type(row["start"]) is not int or type(row["end"]) is not int
                or not 0 <= row["start"] < row["end"]
                or row["unit"] not in {"nt", "aa", "symbol"}
                or row["strand"] not in {"+", "-"}):
            raise ValueError("invalid_mapping_segment")
        length += row["end"] - row["start"]
    return length


def slice_path(path: list[dict], start: int, end: int) -> list[dict]:
    """Map one half-open interval on a concatenated, oriented sequence path."""
    length = path_length(path)
    if type(start) is not int or type(end) is not int or not 0 <= start <= end <= length:
        raise ValueError("interval_outside_mapping_path")
    result, offset = [], 0
    for row in path:
        size = row["end"] - row["start"]
        left, right = max(start, offset) - offset, min(end, offset + size) - offset
        if left < right:
            if row["strand"] == "+":
                bounds = {"start": row["start"] + left, "end": row["start"] + right}
            else:
                bounds = {"start": row["end"] - right, "end": row["end"] - left}
            result.append({**row, **bounds})
        offset += size
        if offset >= end:
            break
    return result


def reverse_path(path: list[dict]) -> list[dict]:
    path_length(path)
    return [{**row, "strand": "-" if row["strand"] == "+" else "+"}
            for row in reversed(path)]


def extract_path(path: list[dict], segments: list[dict], *, strand: str = "+") -> list[dict]:
    """Mirror concatenation/extraction, followed by optional reverse complement."""
    path_length(path)
    if strand not in {"+", "-", "."} or not isinstance(segments, list) or not segments:
        raise ValueError("invalid_path_extraction")
    result = []
    for row in segments:
        if not isinstance(row, dict) or set(row) != {"start", "end"} or row["start"] == row["end"]:
            raise ValueError("invalid_path_extraction")
        result.extend(slice_path(path, row["start"], row["end"]))
    return reverse_path(result) if strand == "-" else result


def validate_mapping(mapping: dict) -> None:
    if (not isinstance(mapping, dict)
            or set(mapping) != {"version", "units_per_symbol", "symbol_length", "path"}
            or mapping["version"] != VERSION
            or type(mapping["units_per_symbol"]) is not int
            or mapping["units_per_symbol"] not in {1, 3}
            or type(mapping["symbol_length"]) is not int or mapping["symbol_length"] <= 0):
        raise ValueError("invalid_sequence_mapping")
    if path_length(mapping["path"]) != mapping["units_per_symbol"] * mapping["symbol_length"]:
        raise ValueError("mapping_length_mismatch")


def translation_mapping(parent_path: list[dict], *, start: int, end: int,
                        strand: str, protein_length: int,
                        omitted_terminal_stop: bool = False) -> dict:
    """Bind a known translation interval, including explicit CDS stop omission.

    ``start``/``end`` already exclude the translator's frame offset and unused
    trailing bases. Stop omission must come from the executed translator's
    semantics, rather than being inferred from a convenient length difference.
    """
    if (strand not in {"+", "-"} or type(protein_length) is not int or protein_length <= 0
            or type(omitted_terminal_stop) is not bool):
        raise ValueError("invalid_translation_mapping")
    path = slice_path(parent_path, start, end)
    if not path or path_length(path) != 3 * (protein_length + int(omitted_terminal_stop)):
        raise ValueError("translation_mapping_length_mismatch")
    if any(row["unit"] not in {"nt", "symbol"} for row in path):
        raise ValueError("translation_requires_nucleotide_input_mapping")
    if strand == "-":
        path = reverse_path(path)
    path = slice_path(path, 0, 3 * protein_length)
    result = {"version": VERSION, "units_per_symbol": 3,
              "symbol_length": protein_length, "path": path}
    validate_mapping(result)
    return result


def map_interval(mapping: dict, start: int, end: int) -> list[dict]:
    """Return ordered original intervals for actual mapped output symbols."""
    validate_mapping(mapping)
    if (type(start) is not int or type(end) is not int
            or not 0 <= start <= end <= mapping["symbol_length"]):
        raise ValueError("interval_outside_mapped_sequence")
    scale = mapping["units_per_symbol"]
    return slice_path(mapping["path"], start * scale, end * scale)


def mapping_footprint(mapping: dict, *, input_refs) -> list[dict]:
    """Project a physical path onto the caller's actual immutable input IDs.

    External references retain physical source identities in the mapping. They
    never become targets simply because their sequence was examined.
    """
    validate_mapping(mapping)
    eligible = set(input_refs)
    return [{"target_ref": row["subject_ref"], "start": row["start"],
             "end": row["end"], "unit": row["unit"]}
            for row in mapping["path"] if row["subject_ref"] in eligible]
