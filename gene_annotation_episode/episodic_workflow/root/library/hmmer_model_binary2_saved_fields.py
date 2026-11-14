"""Original saved HMMER2 header and native slot validation."""
from __future__ import annotations

import math
import struct

MAGIC = 0xE8EDEDB5


_KNOWN_FLAGS = (1 << 14) - 1


def binary2_probability_start(record, field, position_ordinal, cell_index):
    """Join a saved cell to its exact native slot without raw-file access."""
    header = binary2_header(record)
    if header is None:
        return None
    length, width, fields, base = header["length"], header["width"], header["fields"], header["body_start"]
    name = field.rsplit(".", 1)[-1] if field.startswith("positions.") else field
    if name in {"match", "insert", "transitions"}:
        if type(position_ordinal) is not int or not 0 <= position_ordinal < length:
            return None
        if name == "match" and 0 <= cell_index < width:
            return base + 4 * (position_ordinal * width + cell_index)
        if position_ordinal >= length - 1:
            return None
        if name == "insert" and 0 <= cell_index < width:
            return base + 4 * (length * width + position_ordinal * width + cell_index)
        if name == "transitions" and 0 <= cell_index < 7:
            return base + 4 * (length * width + (length - 1) * width + position_ordinal * 7 + cell_index)
    native = None
    if name == "legacy.null_emissions" and 0 <= cell_index < width:
        native = "NULE[" + str(cell_index) + "]"
    elif name == "legacy.special_transitions" and 0 <= cell_index < 8:
        native = "XT[" + str(cell_index) + "]"
    elif name == "legacy.null_transitions" and cell_index == 0:
        native = "NULT.p1"
    elif name == "legacy.begin_transitions" and cell_index == 0:
        native = "TBD1"
    elif name == "legacy.entry_exit" and type(position_ordinal) is int and 0 <= position_ordinal < length and cell_index in (0, 1):
        native = ("begin" if cell_index == 0 else "end") + "[" + str(position_ordinal + 1) + "]"
    return fields[native]["byte_start"] if native in fields else None


def binary2_header(record):
    """Validate saved variable-length header framing and return its slot map.

    No source acquisition, parser call, probability calculation or normalization
    occurs. Fully observed header bytes are required before a native body cell
    can be reinterpreted by the common calculator.
    """
    try:
        rep, locator = record["representation"], record["locator"]
        prefix = "<" if rep["byte_order"] == "little" else ">"
        rows, index, offset, found = rep["native_fields"], 0, locator["byte_start"], {}
        def take(field, size, kind=None, *, unused=False, probability=False, minimum=None, positive=False):
            nonlocal index, offset
            row = rows[index]; index += 1
            if (row["field"] != field or row["byte_start"] != offset or row["byte_end"] != offset + size
                    or len(row["raw_hex"]) != size * 2): raise ValueError
            raw = bytes.fromhex(row["raw_hex"])
            if len(raw) != size: raise ValueError
            offset += size; found[field] = row
            if kind is None:
                value = raw.decode("utf-8", "surrogateescape")
                if row["value"] != value or row["state"] != "present": raise ValueError
                return raw
            value = struct.unpack(prefix + kind, raw)[0]
            finite = not isinstance(value, float) or math.isfinite(value)
            if (finite and (type(row["value"]) is not type(value) or row["value"] != value)
                    or not finite and row["value"] is not None): raise ValueError
            state = "unused" if unused else "invalid" if (not finite
                or probability and not 0 <= value <= 1
                or minimum is not None and value < minimum or positive and value <= 0) else "present"
            if row["state"] != state: raise ValueError
            return value
        def scalar(field, *, kind="i", unused=False, probability=False, minimum=None, positive=False):
            return take(field, 4, kind, unused=unused, probability=probability, minimum=minimum, positive=positive)
        if scalar("magic", kind="I") != MAGIC: return None
        flags = scalar("flags")
        if flags < 0 or flags & ~_KNOWN_FLAGS: return None
        # String native_fields values exclude their serialized NUL, unlike raw
        # annotation buffers. Validate that exact stored projection separately.
        def text_string(field):
            nonlocal index, offset
            size = scalar(field + ".length")
            if size < 0: raise ValueError
            row = rows[index]; index += 1
            if row["field"] != field or row["byte_start"] != offset or row["byte_end"] != offset + size or len(row["raw_hex"]) != size * 2: raise ValueError
            raw = bytes.fromhex(row["raw_hex"]); found[field] = row; offset += size
            if not size:
                if raw or row["value"] is not None or row["state"] != "native_missing_sentinel": raise ValueError
            elif (not raw.endswith(b"\0") or b"\0" in raw[:-1] or row["state"] != "present"
                    or row["value"] != raw[:-1].decode("utf-8", "surrogateescape")): raise ValueError
        text_string("NAME")
        for field, bit in (("ACC", 9), ("DESC", 1)):
            if flags & (1 << bit): text_string(field)
        length, alphabet = scalar("M"), scalar("alphabet_type")
        if length <= 0 or alphabet not in (2, 3): return None
        width = 4 if alphabet == 2 else 20
        for field, bit in (("RF", 2), ("CS", 3)):
            if flags & (1 << bit): take(field, length + 1)
        if flags & (1 << 8):
            for position in range(length + 1): scalar("MAP[" + str(position) + "]", unused=position == 0, minimum=0)
        text_string("COM"); scalar("NSEQ", minimum=0); text_string("DATE"); scalar("CKSUM")
        for field, bit in (("GA", 10), ("TC", 11), ("NC", 12)):
            if flags & (1 << bit):
                for number in (1, 2): scalar(field + str(number), kind="f")
        for number in range(8): scalar("XT[" + str(number) + "]", kind="f", probability=True)
        scalar("NULT.p1", kind="f", probability=True)
        for number in range(width): scalar("NULE[" + str(number) + "]", kind="f", probability=True)
        if flags & (1 << 7): scalar("EVD.mu", kind="f"); scalar("EVD.lambda", kind="f", positive=True)
        scalar("TBD1", kind="f", probability=True)
        for field in ("begin", "end"):
            for position in range(length + 1): scalar(field + "[" + str(position) + "]", kind="f", unused=position == 0, probability=True)
        if index != len(rows) or offset > locator["byte_end"]: return None
        expected_end = offset + 4 * (length * width + (length - 1) * width + (length - 1) * 7)
        if record["terminated"] and expected_end != locator["byte_end"]: return None
        return {"length": length, "width": width, "fields": found, "body_start": offset}
    except (KeyError, IndexError, TypeError, ValueError, OverflowError, struct.error):
        return None


