"""Read retained FCS encoded events into the common fluorescence sheet operands.

The selected decoder is exactly FlowIO 1.4.0 on a little-endian runtime. Its
``events`` include native integer range-bit masking, but no gain, log, time,
compensation or other preparation is requested here. Decoder-normalized metadata
is retained separately from the original artifact's identity and byte spelling.
This module performs no acquisition or scientific calculation.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib
import io
import re
import struct
import sys

from .fluorescence_event_contracts import (
    FluorescenceContractError,
    PARSE_SCHEMA,
    finite,
    issue,
    validate_event_input_request,
    validate_event_parse_result,
)


FORMAT_PROFILE = "fcs_flowio_1_4_0_encoded"
_SIGNATURES = {b"FCS2.0", b"FCS3.0", b"FCS3.1"}
_BYTE_ORDERS = {"1,2", "1,2,3,4", "2,1", "4,3,2,1"}


class _NativeFailure(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _problem(result, code, *, stage="parse", channel=None, ordinal=None):
    result["issues"].append(issue(
        code, stage, source_key=result["source"]["key"],
        sample_key=result["sample"]["key"], domain_key=result["domain"]["key"],
        channel_key=channel, event_ordinal=ordinal,
    ))


def _unavailable(result, code=None, *, stage="parse"):
    result["source"]["extent"] = "unavailable"
    if result["domain"]["state"] == "available":
        result["domain"]["state"] = "unavailable"
    if code is not None:
        _problem(result, code, stage=stage)
    return validate_event_parse_result(result)


def _load_decoder():
    try:
        module = importlib.import_module("flowio")
    except ImportError:
        return None
    return module if getattr(module, "__version__", None) == "1.4.0" else None


def _header_preflight(raw, offset):
    """Bound the header/TEXT reads before invoking the native decoder.

    The decoder remains the metadata parser. These small fixed-field checks do
    not expose an independently interpreted metadata dictionary as native facts.
    """
    if offset < 0:
        raise _NativeFailure("native_format_mismatch")
    if offset + 58 > len(raw):
        raise _NativeFailure("truncated_source")
    if raw[offset:offset + 6] not in _SIGNATURES:
        raise _NativeFailure("native_format_mismatch")
    try:
        start = int(raw[offset + 10:offset + 18])
        stop = int(raw[offset + 18:offset + 26])
        # Blank ANALYSIS header fields are the decoder's absent-field case.
        # Malformed nonblank fields must not silently become absent fields.
        for position in (26, 34, 42, 50):
            field = raw[offset + position:offset + position + 8]
            if position in (42, 50) and not field.strip():
                continue
            if int(field) < 0:
                raise ValueError("negative segment offset")
    except ValueError as error:
        raise _NativeFailure("native_format_mismatch") from error
    if start < 58 or stop < start:
        raise _NativeFailure("native_format_mismatch")
    if offset + stop >= len(raw):
        raise _NativeFailure("truncated_source")


class _SegmentGuard(io.BytesIO):
    """Check native-declared spans before reading beyond the decoded TEXT.

    FlowIO exposes HEADER and TEXT before reading ANALYSIS. Its own metadata
    decoder therefore supplies all bounds to the existing validator; this
    handle neither parses metadata nor changes any bytes or offsets.
    """

    def __init__(self, raw, native, offset):
        super().__init__(raw)
        self._native = native
        self._offset = offset
        self._size = len(raw)
        self._checked = False

    def _check_segments(self):
        if (not self._checked and hasattr(self._native, "header")
                and hasattr(self._native, "text")):
            _segments(self._native, self._offset, self._size)
            self._checked = True

    def read(self, size=-1):
        self._check_segments()
        return super().read(size)

    def read1(self, size=-1):
        return self.read(size)

    def readinto(self, buffer):
        self._check_segments()
        return super().readinto(buffer)

    def close(self):
        self._native = None
        super().close()


def _text_token_pairs(text):
    """Observe ordered FCS TEXT tokens without decoding any DATA values.

    A doubled delimiter is an escaped delimiter. This observer is used only
    for the strict preparation profile; FlowIO still parses the actual native
    metadata. Retaining pairs permits duplicate and value-normalization checks.
    """
    if not text or len(text) < 3 or text[-1] != text[0]:
        raise _NativeFailure("native_format_mismatch")
    delimiter = text[0]
    tokens, token = [], []
    index = 1
    while index < len(text) - 1:
        character = text[index]
        if character == delimiter:
            if index + 1 < len(text) - 1 and text[index + 1] == delimiter:
                token.append(delimiter)
                index += 2
                continue
            tokens.append("".join(token))
            token = []
        else:
            token.append(character)
        index += 1
    tokens.append("".join(token))
    if len(tokens) % 2 or any(not key for key in tokens[::2]):
        raise _NativeFailure("native_format_mismatch")
    return list(zip(tokens[::2], tokens[1::2]))


def _decode(raw, offset, decoder, *, only_text, observe_text=False):
    """Keep metadata established before a strict native-constructor failure.

    FlowIO's constructor can raise after exposing HEADER/TEXT. Initializing its
    actual instance explicitly retains those attributes without retrying,
    repairing the bytes, changing its offsets, or decoding an alternate format.
    Every invocation receives a fresh BytesIO; FlowIO closes that handle.
    """
    flow_type = decoder.FlowData
    if observe_text:
        original_pairs = flow_type._FlowData__parse_pairs

        class StrictTextFlowData(flow_type):
            def _FlowData__parse_pairs(self, text):
                # Constructor parses TEXT before optional ANALYSIS. Preserve
                # only the first segment here; the decoder's answer is intact.
                if not hasattr(self, "preparation_text_pairs"):
                    self.preparation_text_pairs = _text_token_pairs(text)
                return original_pairs(text)

        flow_type = StrictTextFlowData
    native = flow_type.__new__(flow_type)
    native_errors = (decoder.exceptions.FCSParsingError,
                     decoder.exceptions.MultipleDataSetsError,
                     ValueError, KeyError, TypeError, IndexError,
                     OverflowError, NotImplementedError, struct.error, re.error)
    with _SegmentGuard(raw, native, offset) as handle:
        try:
            flow_type.__init__(native, handle, only_text=only_text,
                               nextdata_offset=offset)
        except _NativeFailure as error:
            return native, error.code
        except EOFError:
            return native, "truncated_source"
        except native_errors:
            return native, "native_format_mismatch"
    # Resource/process failures deliberately propagate; they are not bad events.
    return native, None


def decode_selected_fcs(raw: bytes, *, source: dict, only_text=False) -> dict:
    """Strict shared native dataset port for explicitly selected preparation.

    The returned native object is transient, not a serialized handoff. Source
    authentication, traversal, segment bounds, profile and the actual FlowIO
    constructor are the existing encoded-reader implementation. The old reader
    does not opt into the additional TEXT observation and keeps its semantics.
    """
    from .fluorescence_event_contracts import _source

    _source(source)
    if type(raw) is not bytes or type(only_text) is not bool:
        raise FluorescenceContractError("invalid_source")
    result = dict(native=None, error=None, count=None, widths=None,
                  data_start=None, data_stop=None, offset=None)
    identity = source["file"]
    if identity is None:
        result["error"] = "source_unavailable"
        return result
    if len(raw) != identity["size_bytes"] or hashlib.sha256(raw).hexdigest() != identity["sha256"]:
        result["error"] = "retained_artifact_mismatch"
        return result
    if source["format_profile"] != FORMAT_PROFILE or sys.byteorder != "little":
        result["error"] = "native_format_mismatch"
        return result
    try:
        decoder = _load_decoder()
    except (ImportError, OSError, ValueError):
        # A missing/ABI-incompatible native dependency is unavailable here;
        # the historical encoded-reader entry point retains its own behavior.
        decoder = None
    if decoder is None:
        result["error"] = "decoder_unavailable"
        return result
    offset = 0
    for position in range(source["dataset_position"] + 1):
        try:
            _header_preflight(raw, offset)
            native, error = _decode(raw, offset, decoder, only_text=True, observe_text=True)
            selected = position == source["dataset_position"]
            if selected:
                result.update(native=native, offset=offset)
            if error is not None:
                result["error"] = error
                return result
            next_offset, first, last = _segments(native, offset, len(raw))
            if selected:
                count, widths = _profile(native)
                result.update(count=count, widths=widths, data_start=first, data_stop=last)
                if not only_text:
                    native, error = _decode(raw, offset, decoder, only_text=False, observe_text=True)
                    result.update(native=native, error=error)
                return result
            if next_offset is None:
                result["error"] = "source_unavailable"
                return result
            offset = next_offset
        except _NativeFailure as error:
            result["error"] = error.code
            return result
    return result


def _retain_metadata(result, native):
    for section in ("header", "text", "analysis"):
        values = getattr(native, section, None)
        if values is not None:
            result["source"]["metadata"].extend(
                {"name": f"flowio.{section}.{name}", "value": str(value)}
                for name, value in values.items()
            )
    text = getattr(native, "text", {})
    try:
        count = int(text["tot"])
    except (KeyError, TypeError, ValueError):
        return
    if count >= 0:
        result["source"]["native_event_count"] = count


def _number(text, name, *, minimum=0):
    try:
        value = int(text[name])
    except (KeyError, TypeError, ValueError) as error:
        raise _NativeFailure("native_format_mismatch") from error
    if value < minimum:
        raise _NativeFailure("native_format_mismatch")
    return value


def _interval(start, stop, *, offset, boundary, size, empty=False, absent=False):
    if absent and (start, stop) in {(0, 0), (-1, -1)}:
        return
    if start < 58 or stop < start - (1 if empty else 0):
        raise _NativeFailure("native_format_mismatch")
    if offset + start > size or offset + stop >= size:
        raise _NativeFailure("truncated_source")
    if offset + start > boundary or offset + stop >= boundary:
        raise _NativeFailure("native_format_mismatch")


def _segments(native, offset, size):
    header, text = native.header, native.text
    next_relative = _number(text, "nextdata")
    next_offset = offset + next_relative if next_relative else None
    boundary = size if next_offset is None else next_offset
    if next_offset is not None:
        if next_relative < 58:
            raise _NativeFailure("native_format_mismatch")
        if next_offset + 58 > size:
            raise _NativeFailure("truncated_source")
    total = _number(text, "tot")
    if header["version"] == "2.0":
        start, stop = header["data_start"], header["data_stop"]
    else:
        start, stop = _number(text, "begindata"), _number(text, "enddata")
    for first, last in ((header["text_start"], header["text_stop"]),
                        (start, stop)):
        _interval(first, last, offset=offset, boundary=boundary, size=size,
                  empty=(first, last) == (start, stop) and total == 0)
    # Check actual HEADER intervals as well as the effective TEXT offsets. A
    # zero HEADER DATA pair is the native large-file sentinel; FlowIO itself
    # performs the strict HEADER/TEXT discrepancy checks without an override.
    if (header["data_start"], header["data_stop"]) != (0, 0):
        _interval(header["data_start"], header["data_stop"], offset=offset,
                  boundary=boundary, size=size, empty=total == 0)
    _interval(header["analysis_start"], header["analysis_stop"], offset=offset,
              boundary=boundary, size=size, absent=True)
    try:
        analysis_start = int(text.get("beginanalysis", header["analysis_start"]))
        analysis_stop = int(text.get("endanalysis", header["analysis_stop"]))
    except (TypeError, ValueError) as error:
        raise _NativeFailure("native_format_mismatch") from error
    _interval(analysis_start, analysis_stop, offset=offset, boundary=boundary,
              size=size, absent=True)
    return next_offset, start, stop


def _profile(native):
    text = native.text
    count = _number(text, "par", minimum=1)
    data_type = text.get("datatype", "").upper()
    if (text.get("mode", "").upper() != "L" or data_type not in {"I", "F", "D"}
            or text.get("byteord") not in _BYTE_ORDERS):
        raise _NativeFailure("native_format_mismatch")
    # Count native declarations before iterating PAR: a corrupt huge PAR must
    # not manufacture channel declarations or force a huge validation loop.
    for suffix in ("n", "b", "r"):
        declared = [name for name in text if re.fullmatch(r"p\d+" + suffix, name)]
        if len(declared) != count or any(
                f"p{position}{suffix}" not in text for position in range(1, count + 1)):
            raise _NativeFailure("native_format_mismatch")
    widths = []
    for position in range(1, count + 1):
        bits = _number(text, f"p{position}b", minimum=1)
        if bits not in ({8, 16, 32} if data_type == "I"
                        else {32} if data_type == "F" else {64}):
            raise _NativeFailure("native_format_mismatch")
        try:
            native_range = (int(text[f"p{position}r"]) if data_type == "I"
                            else float(text[f"p{position}r"]))
        except (ValueError, OverflowError) as error:
            raise _NativeFailure("native_format_mismatch") from error
        if not finite(native_range) or native_range <= 0:
            raise _NativeFailure("native_format_mismatch")
        widths.append(bits)
    return count, widths


def _bind_channels(result, native, count):
    if count > len(result["channels"]):
        raise FluorescenceContractError("invalid_channel")
    matched = True
    for channel in result["channels"]:
        position = channel["ordinal"] + 1
        if position > count:
            _problem(result, "channel_missing", channel=channel["key"])
            continue
        name = native.text[f"p{position}n"]
        if channel["native_name"] is not None and channel["native_name"] != name:
            _problem(result, "native_format_mismatch", channel=channel["key"])
            matched = False
        elif channel["native_name"] is None:
            channel["native_name"] = name
        if channel["label"] is None and f"p{position}s" in native.text:
            channel["label"] = native.text[f"p{position}s"]
    return matched


def _events(result, bindings, native_values, count):
    for start in range(0, len(native_values), count):
        ordinal = start // count
        row = native_values[start:start + count]
        if len(row) < count:
            result["source"]["extent"] = "partial"
            _problem(result, "invalid_event_row", ordinal=ordinal)
            _problem(result, "truncated_source", ordinal=ordinal)
        cells = []
        for binding in bindings:
            position = binding["ordinal"]
            measurement = dict(value=None, state="unavailable", raw=None)
            if position < len(row):
                value = row[position]
                if finite(value):
                    measurement.update(value=value, state=binding["measurement_origin"])
                else:
                    measurement["state"] = "invalid"
                    _problem(result, "invalid_numeric_token", channel=binding["key"],
                             ordinal=ordinal)
            elif position < count:
                _problem(result, "channel_missing", channel=binding["key"], ordinal=ordinal)
            cells.append(dict(channel_key=binding["key"], measurement=measurement))
        result["events"].append(dict(
            sample_key=result["sample"]["key"], domain_key=result["domain"]["key"],
            event_ordinal=ordinal, source_ordinal=ordinal,
            location=dict(record_ordinal=ordinal, line_start=None, line_end=None,
                          byte_start=None, byte_end=None), values=cells,
        ))


def parse_fluorescence_fcs(raw: bytes, *, source: dict, sample: dict,
                           channels: list[dict], domain: dict) -> dict:
    """Parse only the explicitly selected dataset's encoded native event values."""
    validate_event_input_request(source=source, sample=sample, channels=channels, domain=domain)
    if type(raw) is not bytes or source["format_profile"] != FORMAT_PROFILE:
        raise FluorescenceContractError("invalid_source")
    if (domain["scale_kind"] != "encoded" or domain["parent_domain_key"] is not None
            or domain["correspondence"] is not None
            or domain["key"] != sample["primary_domain_key"]):
        raise FluorescenceContractError("invalid_domain")
    result = deepcopy(dict(schema=PARSE_SCHEMA, source=source, sample=sample,
                           channels=channels, domain=domain, events=[], issues=[]))
    result["source"].update(extent="unavailable", native_event_count=None)
    for channel in result["channels"]:
        channel.pop("measurement_origin")
        channel["domain_key"] = domain["key"]
    identity = source["file"]
    if len(raw) != identity["size_bytes"] or hashlib.sha256(raw).hexdigest() != identity["sha256"]:
        return _unavailable(result, "retained_artifact_mismatch", stage="input")
    if domain["state"] != "available":
        return _unavailable(result, "measurement_domain_unavailable", stage="domain")
    decoder = _load_decoder()
    if decoder is None:
        return _unavailable(result, "decoder_unavailable")
    if sys.byteorder != "little":
        return _unavailable(result, "native_format_mismatch")
    offset = 0
    for position in range(source["dataset_position"] + 1):
        try:
            _header_preflight(raw, offset)
        except _NativeFailure as error:
            return _unavailable(result, error.code)
        native, error_code = _decode(raw, offset, decoder, only_text=True)
        selected = position == source["dataset_position"]
        if selected:
            _retain_metadata(result, native)
        if error_code is not None:
            return _unavailable(result, error_code)
        if hasattr(native, "header") and hasattr(native, "text"):
            try:
                next_offset, data_start, data_stop = _segments(native, offset, len(raw))
            except _NativeFailure as error:
                return _unavailable(result, error.code)
        if selected:
            break
        if next_offset is None:
            return _unavailable(result, "source_unavailable")
        offset = next_offset
    try:
        count, widths = _profile(native)
    except _NativeFailure as error:
        return _unavailable(result, error.code)
    if not _bind_channels(result, native, count):
        return _unavailable(result)
    decoded, error_code = _decode(raw, offset, decoder, only_text=False)
    if error_code is not None:
        return _unavailable(result, error_code)
    if decoded.events is None:
        return _unavailable(result, "native_format_mismatch")
    if not len(decoded.events) and data_stop >= data_start:
        # A decoder that discarded every incomplete value did not establish a
        # complete empty population. No absent row or zero measurement is added.
        return _unavailable(result, "truncated_source")
    result["source"]["extent"] = "complete"
    _events(result, channels, decoded.events, count)
    # Some uniform-width integer bit masks truncate an incomplete final row
    # inside FlowIO. Preserve only returned values, but never call that complete.
    if len(set(widths)) == 1:
        encoded_items, trailing_bytes = divmod(data_stop - data_start + 1, widths[0] // 8)
        if trailing_bytes or len(decoded.events) != encoded_items:
            result["source"]["extent"] = "partial"
            _problem(result, "invalid_event_row", ordinal=len(result["events"]))
            _problem(result, "truncated_source", ordinal=len(result["events"]))
    if len(result["events"]) != result["source"]["native_event_count"]:
        result["source"]["extent"] = "partial"
        _problem(result, "native_count_conflict")
    return validate_event_parse_result(result)
