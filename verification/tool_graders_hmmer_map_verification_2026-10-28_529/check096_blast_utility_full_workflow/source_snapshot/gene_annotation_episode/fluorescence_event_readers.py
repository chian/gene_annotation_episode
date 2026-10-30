"""Pure readers of retained event bytes for the shared fluorescence sheet.

No gate, population fraction, intensity statistic, preparation, acquisition or
instrument operation occurs here. Callers provide the complete byte artifact,
its identity, exact positional channels and the declared measurement domain.
"""

from __future__ import annotations

from copy import deepcopy
import csv
import hashlib
import io
import json

from .fluorescence_event_contracts import (
    FluorescenceContractError,
    PARSE_SCHEMA,
    TABLE_SCHEMA,
    finite,
    issue,
    validate_csv_request,
    validate_event_parse_result,
    validate_snapshot_request,
)


def _result(source, sample, channels, domain):
    result = deepcopy(dict(schema=PARSE_SCHEMA, source=source, sample=sample,
                           channels=channels, domain=domain, events=[], issues=[]))
    result["source"]["extent"] = "unavailable"
    # Neither format has a native declared count. Do not adopt a caller's count
    # or substitute the length of the parsed array for a native observation.
    result["source"]["native_event_count"] = None
    for channel in result["channels"]:
        channel.pop("measurement_origin")
        channel["domain_key"] = domain["key"]
    return result


def _add_issue(result, code, *, stage="parse", channel=None, ordinal=None):
    result["issues"].append(issue(
        code, stage, source_key=result["source"]["key"],
        sample_key=result["sample"]["key"], domain_key=result["domain"]["key"],
        channel_key=channel, event_ordinal=ordinal,
    ))


def _unavailable(result, code, *, stage="parse"):
    result["source"]["extent"] = "unavailable"
    if result["domain"]["state"] == "available":
        result["domain"]["state"] = "unavailable"
    _add_issue(result, code, stage=stage)
    return validate_event_parse_result(result)


def _input_failure(raw, result):
    if type(raw) is not bytes:
        raise FluorescenceContractError("invalid_source")
    identity = result["source"]["file"]
    if (len(raw) != identity["size_bytes"]
            or hashlib.sha256(raw).hexdigest() != identity["sha256"]):
        return _unavailable(result, "retained_artifact_mismatch", stage="input")
    if result["domain"]["state"] != "available":
        return _unavailable(result, "measurement_domain_unavailable", stage="domain")
    return None


def _columns(result, names):
    """Observe positional names without guessing or narrowing the full input."""
    if len(names) > len(result["channels"]):
        raise FluorescenceContractError("invalid_channel")
    matched = True
    for channel in result["channels"]:
        position = channel["ordinal"]
        if position >= len(names):
            _add_issue(result, "channel_missing", channel=channel["key"])
        elif (channel["native_name"] is not None
              and channel["native_name"] != names[position]):
            _add_issue(result, "native_format_mismatch", channel=channel["key"])
            matched = False
        elif channel["native_name"] is None:
            channel["native_name"] = names[position]
    return matched


def _correspondence(domain):
    if domain["correspondence"] is None:
        return None
    return {item["source_ordinal"]: item["event_ordinal"]
            for item in domain["correspondence"]}


def _ordinal(mapping, source_ordinal, *, required=True):
    if mapping is None:
        return source_ordinal
    if required and source_ordinal not in mapping:
        raise FluorescenceContractError("invalid_domain")
    return mapping.get(source_ordinal)


def _event(result, bindings, row, source_ordinal, mapping, location, width,
           *, missing_tokens=None):
    ordinal = _ordinal(mapping, source_ordinal)
    if row is None or len(row) != width:
        _add_issue(result, "invalid_event_row", ordinal=ordinal)
    cells = []
    for binding in bindings:
        position = binding["ordinal"]
        measurement = dict(value=None, state="unavailable", raw=None)
        if row is not None and position >= len(row):
            _add_issue(result, "channel_missing", channel=binding["key"], ordinal=ordinal)
        elif row is not None:
            token = row[position]
            if missing_tokens is not None:
                # csv.reader's exact decoded field, including whitespace and
                # embedded newlines; quotes/escapes remain in retained bytes.
                measurement["raw"] = token
                if token in missing_tokens:
                    measurement["state"] = "missing"
                    cells.append(dict(channel_key=binding["key"], measurement=measurement))
                    continue
                try:
                    value = float(token)
                except (ValueError, OverflowError):
                    value = None
            else:
                if token is None:
                    measurement["state"] = "missing"
                    cells.append(dict(channel_key=binding["key"], measurement=measurement))
                    continue
                value = token
            if finite(value):
                measurement.update(value=value, state=binding["measurement_origin"])
            else:
                measurement["state"] = "invalid"
                _add_issue(result, "invalid_numeric_token", channel=binding["key"], ordinal=ordinal)
        cells.append(dict(channel_key=binding["key"], measurement=measurement))
    result["events"].append(dict(
        sample_key=result["sample"]["key"], domain_key=result["domain"]["key"],
        source_ordinal=source_ordinal, event_ordinal=ordinal,
        location=location, values=cells,
    ))


class _PhysicalLines:
    """Track UTF-8 byte spans while letting csv.reader consume physical lines."""

    def __init__(self, text, byte_start):
        self.stream = io.StringIO(text, newline="")
        self.byte_position = byte_start
        self.line_number = 0
        self.record_parts = []

    def __iter__(self):
        return self

    def __next__(self):
        line = self.stream.readline()
        if line == "":
            raise StopIteration
        self.line_number += 1
        self.byte_position += len(line.encode("utf-8"))
        self.record_parts.append(line)
        return line


def _known_error_boundary(parts, format_spec):
    """Recognize a closed malformed record; never decode values permissively.

    The strict CSV parser has already failed. This scan only establishes whether
    the consumed physical line ends outside a quoted/escaped field, so that an
    unavailable row can keep its original position. Ambiguous escaped line ends
    and unclosed quotes terminate the prefix; they are never guessed apart.
    """
    quote = format_spec["quotechar"]
    delimiter = format_spec["delimiter"]
    escape = format_spec["escapechar"]
    state = "start"
    escaped_from = None
    for part in parts:
        for character in part:
            if state == "escape":
                if character in "\r\n":
                    return False
                state = escaped_from
            elif state == "quoted":
                if character == escape:
                    escaped_from, state = "quoted", "escape"
                elif character == quote:
                    state = "after_quote" if format_spec["doublequote"] else "bare"
            elif state == "after_quote" and character == quote:
                state = "quoted"
            elif character in "\r\n":
                state = "start"
            elif state == "start" and character == quote:
                state = "quoted"
            elif character == escape:
                escaped_from, state = "bare", "escape"
            elif character == delimiter:
                state = "start"
            else:
                # Unexpected text after a closing quote is still malformed.
                # It cannot open a new quoted field without a delimiter.
                state = "bare"
    return state not in {"quoted", "escape"}


def _decode_csv(raw, encoding):
    """Return only whole physical lines when a later UTF-8 byte is invalid."""
    payload = raw[3:] if encoding == "utf-8-sig" and raw.startswith(b"\xef\xbb\xbf") else raw
    try:
        return payload.decode("utf-8"), False
    except UnicodeDecodeError as error:
        prefix = payload[:error.start]
        boundary = max(prefix.rfind(b"\n"), prefix.rfind(b"\r")) + 1
        return prefix[:boundary].decode("utf-8"), True


def parse_fluorescence_csv(raw: bytes, *, source: dict, format_spec: dict,
                           sample: dict, channels: list[dict], domain: dict) -> dict:
    """Parse supplied CSV bytes under the caller's exact dialect and bindings."""
    validate_csv_request(source=source, format_spec=format_spec, sample=sample,
                         channels=channels, domain=domain)
    result = _result(source, sample, channels, domain)
    failed = _input_failure(raw, result)
    if failed is not None:
        return failed
    text, invalid_encoding = _decode_csv(raw, format_spec["encoding"])
    bom_bytes = 3 if format_spec["encoding"] == "utf-8-sig" and raw.startswith(b"\xef\xbb\xbf") else 0
    lines = _PhysicalLines(text, bom_bytes)
    dialect = {key: format_spec[key]
               for key in ("delimiter", "quotechar", "escapechar", "doublequote")}
    mapping = _correspondence(domain)
    header_pending = format_spec["header"]
    header_read = False
    width = len(channels)
    source_ordinal = 0
    result["source"]["extent"] = "complete"
    while True:
        start_line, start_byte = lines.line_number + 1, lines.byte_position
        lines.record_parts = []
        try:
            row = next(csv.reader(lines, strict=True, skipinitialspace=False, **dialect))
        except StopIteration:
            break
        except csv.Error:
            if header_pending:
                if invalid_encoding:
                    _add_issue(result, "input_encoding_invalid", stage="input")
                return _unavailable(result, "native_format_mismatch")
            if not _known_error_boundary(lines.record_parts, format_spec):
                result["source"]["extent"] = "partial"
                _add_issue(result, "truncated_source",
                           ordinal=_ordinal(mapping, source_ordinal, required=False))
                break
            row = None
        if header_pending:
            header_pending = False
            header_read = True
            if not _columns(result, row):
                result["source"]["extent"] = "unavailable"
                result["domain"]["state"] = "unavailable"
                if invalid_encoding:
                    _add_issue(result, "input_encoding_invalid", stage="input")
                return validate_event_parse_result(result)
            width = len(row)
            continue
        location = dict(record_ordinal=source_ordinal, line_start=start_line,
                        line_end=lines.line_number, byte_start=start_byte,
                        byte_end=lines.byte_position)
        _event(result, channels, row, source_ordinal, mapping, location, width,
               missing_tokens=format_spec["missing_tokens"])
        source_ordinal += 1
    if invalid_encoding:
        if not result["events"] and not header_read:
            return _unavailable(result, "input_encoding_invalid", stage="input")
        result["source"]["extent"] = "partial"
        _add_issue(result, "input_encoding_invalid", stage="input",
                   ordinal=_ordinal(mapping, source_ordinal, required=False))
    return validate_event_parse_result(result)


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("nonstandard JSON numeric constant")


def parse_fluorescence_table_snapshot(raw: bytes, *, source: dict,
                                      sample: dict, channels: list[dict],
                                      domain: dict) -> dict:
    """Read an explicit immutable JSON table; never import or convert a table."""
    validate_snapshot_request(source=source, sample=sample, channels=channels, domain=domain)
    result = _result(source, sample, channels, domain)
    failed = _input_failure(raw, result)
    if failed is not None:
        return failed
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return _unavailable(result, "input_encoding_invalid", stage="input")
    try:
        document = json.loads(text, object_pairs_hook=_json_object,
                              parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        return _unavailable(result, "native_format_mismatch")
    if (type(document) is not dict or set(document) != {"schema", "columns", "rows"}
            or document["schema"] != TABLE_SCHEMA
            or type(document["columns"]) is not list
            or any(name is not None and type(name) is not str for name in document["columns"])
            or type(document["rows"]) is not list):
        return _unavailable(result, "native_format_mismatch")
    if not _columns(result, document["columns"]):
        result["domain"]["state"] = "unavailable"
        return validate_event_parse_result(result)
    mapping = _correspondence(domain)
    width = len(document["columns"])
    result["source"]["extent"] = "complete"
    for source_ordinal, row in enumerate(document["rows"]):
        location = dict(record_ordinal=source_ordinal, line_start=None,
                        line_end=None, byte_start=None, byte_end=None)
        _event(result, channels, row if type(row) is list else None,
               source_ordinal, mapping, location, width)
    return validate_event_parse_result(result)
