"""One ordinary caller-selected GEO study-file getter.

This retains transfer bytes and provenance. SOFT/matrix parsing and scientific
interpretation belong to later explicitly selected data handling or analysis.
"""
from copy import deepcopy
from dataclasses import replace
import gzip
import hashlib
import io
import json
import math
import re
import zlib
from urllib.parse import quote

from .acquisition import AcquisitionError, SourceSnapshot
from .domain import ContractError, canonical


TOOL = "public.ncbi.geo"
MAX_DOWNLOAD_BYTES = 1024 ** 3
ROOT = "https://ftp.ncbi.nlm.nih.gov/geo/series/"
REQUEST_VERSION = "geo_download_request_v1"
_STUDY = re.compile(r"GSE[1-9][0-9]*\Z", re.ASCII)
_STUDY_SCHEMA = {"type": "string", "pattern": "^GSE[1-9][0-9]*$"}
_LIMIT = {"type": "integer", "minimum": 1, "maximum": MAX_DOWNLOAD_BYTES}
_NAME = {"type": "string", "minLength": 1, "pattern": r"^[^/\\\x00-\x1f\x7f]+$"}


def _branch(data_type, *, named):
    fields = {"study": deepcopy(_STUDY_SCHEMA), "data_type": {"const": data_type}, "max_bytes": deepcopy(_LIMIT)}
    if named:
        fields["file_name"] = deepcopy(_NAME)
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


ARGUMENTS_SCHEMA = {"oneOf": [_branch("family_soft", named=False),
    _branch("series_matrix", named=True), _branch("supplementary_file", named=True)]}


def validate_geo_arguments(arguments):
    """Keep an explicit study, representation and filename; insert no choices."""
    def require(condition):
        if not condition:
            raise ContractError("geo_arguments_invalid")
    require(type(arguments) is dict)
    value = deepcopy(arguments)
    require(type(value.get("data_type")) is str
        and value["data_type"] in {"family_soft", "series_matrix", "supplementary_file"})
    named = value["data_type"] != "family_soft"
    require(set(value) == {"study", "data_type", "max_bytes"} | ({"file_name"} if named else set()))
    require(type(value["study"]) is str and _STUDY.fullmatch(value["study"]) is not None)
    require(type(value["max_bytes"]) is int and 1 <= value["max_bytes"] <= MAX_DOWNLOAD_BYTES)
    if named:
        name = value["file_name"]
        require(type(name) is str and bool(name) and name not in {".", ".."}
            and not any(character in "/\\" or ord(character) < 32 or ord(character) == 127 for character in name))
        try:
            name.encode("utf-8")
        except UnicodeError as error:
            raise ContractError("geo_arguments_invalid") from error
        if value["data_type"] == "series_matrix":
            require(re.fullmatch(re.escape(value["study"]) + r"(?:-GPL[1-9][0-9]*)?_series_matrix\.txt\.gz", name,
                re.ASCII) is not None)
    return value


def geo_request_spec(arguments):
    """Compile documented paths on the independently verified HTTPS file host.

    Directory/filename definitions: https://ftp.ncbi.nlm.nih.gov/geo/README.txt
    Actual HTTPS indexes independently expose soft/, matrix/ and suppl/ under
    https://ftp.ncbi.nlm.nih.gov/geo/series/GSE1nnn/GSE1000/ (matrix also GSE1001).
    """
    value = validate_geo_arguments(arguments)
    study = value["study"]
    bucket = "GSE" + study[3:][:-3] + "nnn"
    directory = {"family_soft": "soft", "series_matrix": "matrix", "supplementary_file": "suppl"}[value["data_type"]]
    filename = study + "_family.soft.gz" if value["data_type"] == "family_soft" else value["file_name"]
    return {"service": "geo", "url": ROOT + bucket + "/" + study + "/" + directory + "/" + quote(filename, safe=""),
        "params": {}, "media_type": "application/octet-stream", "max_bytes": value["max_bytes"], "follow_redirects": False}


def geo_tool_contract():
    return {"name": TOOL, "description": "Retrieve one caller-selected GEO study data file for future analysis.",
        "input_schema": deepcopy(ARGUMENTS_SCHEMA), "instructions":
            "Select the exact GSE study and data_type: family_soft, series_matrix or supplementary_file. "
            "Family SOFT selects the documented study family file. For a matrix or supplementary file, "
            "supply its exact file_name from prior study/file inventory; a different platform matrix "
            "or file requires a separate choice. Set max_bytes to the explicit download limit (up to "
            "1 GiB). Each call transfers one file. The receipt says whether that selected file was "
            "acquired and supplies its Source and original data File on success; a captured failure "
            "retains its actual Source. Data, metadata and native associations remain available for "
            "later analysis. Filename labels do not establish raw/processed scale or comparability."}


def _timeout(client):
    value = getattr(client, "timeout", None)
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        valid = False
    if not valid:
        raise ContractError("geo_timeout_invalid")
    return value


def request_geo(client, arguments):
    """Perform exactly one fixed shared HTTP request; retain actual error bodies."""
    value = validate_geo_arguments(arguments)
    spec = geo_request_spec(value)
    try:
        snapshot = client._http(**spec, timeout_seconds=_timeout(client))
    except AcquisitionError as error:
        if not isinstance(error.snapshot, SourceSnapshot) or type(error.snapshot.content) is not bytes:
            raise
        snapshot = error.snapshot
    if not isinstance(snapshot, SourceSnapshot) or type(snapshot.content) is not bytes:
        raise AcquisitionError("geo_snapshot_invalid", phase="http_response")
    # Preserve a supplied client's original native request independently of the
    # caller's arguments. Publication must prove both against the actual URL.
    return replace(snapshot, request={"version": REQUEST_VERSION, "arguments": value,
        "native_request": deepcopy(snapshot.request)})


def _association_failure(snapshot, arguments, *, timeout):
    spec = geo_request_spec(arguments)
    expected = {"version": REQUEST_VERSION, "arguments": arguments, "native_request": {}}
    if (snapshot.service != "geo" or snapshot.url != spec["url"]
            or canonical(snapshot.request) != canonical(expected)):
        return "geo_selected_request_mismatch"
    transport = snapshot.transport
    if type(transport) is not dict:
        return "geo_transport_invalid"
    try:
        json.dumps(transport, allow_nan=False)
    except (ValueError, TypeError, OverflowError, RecursionError):
        return "geo_transport_invalid"
    request = transport.get("request")
    if (type(request) is not dict or request.get("method") != "GET" or request.get("url") != spec["url"]
            or any(key in request for key in ("body_base64", "body_sha256"))
            or transport.get("effective_url", spec["url"]) != spec["url"]):
        return "geo_selected_request_mismatch"
    headers = request.get("headers")
    if (type(headers) is not dict or any(type(key) is not str for key in headers)
            or [item for key, item in headers.items() if key.lower() == "accept"] != [spec["media_type"]]):
        return "geo_selected_request_mismatch"
    policy = transport.get("request_policy")
    if (type(policy) is not dict or policy.get("automatic_redirects") is not False
            or canonical(policy.get("timeout_seconds")) != canonical(timeout)
            or type(transport.get("response_byte_limit")) is not int
            or transport["response_byte_limit"] != arguments["max_bytes"]):
        return "geo_transfer_policy_mismatch"
    pairs = transport.get("header_items")
    if (type(pairs) not in (list, tuple) or any(type(pair) not in (list, tuple) or len(pair) != 2
            or any(type(item) is not str for item in pair) for pair in pairs)):
        return "geo_transport_invalid"
    return None


class _RetainedBytes(io.RawIOBase):
    """Stream existing capture bytes without copying the complete body."""
    def __init__(self, raw):
        self.raw, self.position = memoryview(raw), 0

    def readable(self):
        return True

    def readinto(self, buffer):
        count = min(len(buffer), len(self.raw) - self.position)
        buffer[:count] = self.raw[self.position:self.position + count]
        self.position += count
        return count


class _GeoIdentity:
    """Recognize native identity headers, retaining no decoded tables or long lines."""
    def __init__(self, arguments):
        marker = b'^SERIES' if arguments['data_type'] == 'family_soft' else b'!Series_geo_accession'
        self.delimiter = 61 if arguments['data_type'] == 'family_soft' else 9
        platform = re.fullmatch(re.escape(arguments['study']) + r'-(GPL[1-9][0-9]*)_series_matrix\.txt\.gz',
            arguments.get('file_name', ''), re.ASCII)
        self.fields = {marker: ('study', arguments['study'].encode('ascii'))}
        if platform is not None:
            self.fields[b'!Sample_platform_id'] = ('platform', platform[1].encode('ascii'))
        self.study_match = self.study_other = False
        self.platform_signature = None
        self.platform_match = self.platform_ambiguous = self.platform_unknown = False
        self._reset()

    def _reset(self):
        self.name, self.name_space, self.skip, self.field = bytearray(), False, False, None
        self.active = self.quoted = self.quote_closed = False
        self.tokens = 0
        self.line_invalid = self.line_match = self.line_other = self.after_tab = False

    def _start_token(self, quoted):
        self.active, self.quoted, self.quote_closed = True, quoted, False
        self.token_size, self.token_valid, self.token_match = 0, True, True
        self.token_digest = hashlib.sha256()

    def _token_byte(self, byte):
        kind, expected = self.field
        prefix = b'GSE' if kind == 'study' else b'GPL'
        index = self.token_size
        self.token_valid &= (byte == prefix[index] if index < 3 else
            49 <= byte <= 57 if index == 3 else 48 <= byte <= 57)
        self.token_match &= index < len(expected) and byte == expected[index]
        self.token_digest.update(bytes((byte,)))
        self.token_size += 1

    def _end_token(self):
        if not self.active:
            return
        valid = self.token_valid and self.token_size > 3 and not self.quoted
        self.line_invalid |= not valid
        match = valid and self.token_match and self.token_size == len(self.field[1])
        self.line_match |= match
        self.line_other |= valid and not match
        self.tokens += 1
        if self.field[0] == 'platform' and valid:
            signature = self.token_size, self.token_digest.digest()
            if self.platform_signature is None:
                self.platform_signature = signature
            elif self.platform_signature != signature:
                self.platform_ambiguous = True
            self.platform_match |= match
        self.active = self.quote_closed = False

    def _end_line(self):
        if self.field is not None:
            self._end_token()
            if self.field[0] == 'study' and not self.line_invalid and self.tokens == 1:
                self.study_match |= self.line_match
                self.study_other |= self.line_other
            elif self.field[0] == 'platform':
                self.platform_unknown |= self.line_invalid or self.after_tab or self.tokens == 0
        self._reset()

    def feed(self, block):
        index = 0
        while index < len(block):
            if self.skip:
                endings = [p for p in (block.find(b'\r', index), block.find(b'\n', index)) if p >= 0]
                if not endings:
                    return
                index = min(endings)
            byte = block[index]
            index += 1
            if byte in (10, 13):
                self._end_line()
                continue
            if self.field is None:
                if byte == self.delimiter:
                    self.field = self.fields.get(bytes(self.name))
                    self.skip = self.field is None
                elif byte in (9, 32):
                    if not self.name:
                        self.skip = True
                    elif self.name not in (b'^', b'!'):
                        self.name_space = True
                elif self.name_space or len(self.name) >= max(map(len, self.fields)):
                    self.skip = True
                else:
                    self.name.append(byte)
                    self.skip = not any(marker.startswith(self.name) for marker in self.fields)
                continue
            if byte in (9, 32) and not self.quoted:
                was_active = self.active
                self._end_token()
                if byte == 9 and self.field[0] == 'platform':
                    self.line_invalid |= self.after_tab or not was_active and self.tokens == 0
                    self.after_tab = True
                continue
            if not self.active:
                self.line_invalid |= self.field[0] == 'platform' and self.tokens > 0 and not self.after_tab
                self._start_token(byte == 34)
                self.after_tab = False
                if byte == 34:
                    continue
            if byte == 34:
                if self.quoted:
                    self.quoted, self.quote_closed = False, True
                else:
                    self.token_valid = False
            elif self.quote_closed:
                self.token_valid = False
            else:
                self._token_byte(byte)

    def finish(self):
        self._end_line()
        if not self.study_match:
            return 'geo_selected_study_identity_conflict' if self.study_other else 'geo_selected_study_identity_unavailable'
        if (self.platform_signature is not None and not self.platform_match
                and not self.platform_ambiguous and not self.platform_unknown):
            return 'geo_selected_platform_identity_conflict'
        return None


def _content_failure(raw, arguments):
    if arguments['data_type'] == 'supplementary_file':
        return None  # No native representation or internal study identity was selected.
    identity = _GeoIdentity(arguments)
    try:
        with _RetainedBytes(raw) as retained, gzip.GzipFile(fileobj=retained, mode='rb') as stream:
            for block in iter(lambda: stream.read(65536), b''):
                identity.feed(block)
    except (OSError, EOFError, ValueError, zlib.error):
        return 'geo_gzip_integrity_failed'
    return identity.finish()


def _transfer_failure(snapshot, arguments):
    transport = snapshot.transport
    status = transport.get("status")
    if type(status) is not int:
        return "geo_http_status_unavailable"
    if status == 206:
        return "geo_partial_response"
    if status != 200:
        return "geo_http_not_successful"
    if (transport.get("body_complete") is not True or transport.get("body_capture_failure") is not None
            or transport.get("body_capture_error") is not None):
        return "geo_capture_incomplete"
    size = len(snapshot.content)
    if size > arguments["max_bytes"]:
        return "geo_capture_identity_mismatch"
    for key in ("retained_body_bytes", "observed_body_bytes"):
        if type(transport.get(key)) is not int or transport[key] != size:
            return "geo_capture_identity_mismatch"
    declared = transport.get("declared_body_bytes")
    if declared is not None and (type(declared) is not int or declared != size):
        return "geo_capture_identity_mismatch"
    pairs = transport["header_items"]
    encoding = [value.strip().lower() for name, value in pairs if name.lower() == "content-encoding"]
    if encoding not in ([], ["identity"]):
        return "geo_http_content_encoding_unsupported"
    if any(name.lower() == "content-range" for name, _ in pairs):
        return "geo_partial_response"
    if arguments["data_type"] in {"family_soft", "series_matrix"}:
        types = [value.split(";", 1)[0].strip().lower() for name, value in pairs if name.lower() == "content-type"]
        if "text/html" in types or not snapshot.content.startswith(b"\x1f\x8b\x08"):
            return "geo_wrong_file_representation"
    return _content_failure(snapshot.content, arguments)


def publish_geo_request(registry, arguments, snapshot):
    """Return only acquisition outcome and explicit original Source/File handles.

    The ordinary ToolRegistry owns selected action authentication, the existing
    operation lock, same-key recovery and saving. This internal publisher adds
    no action, permission, receipt, parser, scientific fact or database workflow.
    """
    value = validate_geo_arguments(arguments)
    if not isinstance(snapshot, SourceSnapshot) or type(snapshot.content) is not bytes:
        raise ContractError("geo_snapshot_invalid")
    association = _association_failure(snapshot, value, timeout=_timeout(registry.clients))
    source = registry._source(TOOL, None, snapshot=snapshot,
        accession=value["study"] if association is None else None)
    failure = association or _transfer_failure(snapshot, value)
    acquired = failure is None
    receipt = {"acquired": acquired, "source_ref": source["id"],
        "data_ref": source["artifact_ref"] if acquired else None, "failure_code": failure}
    return receipt, [source["id"], source["artifact_ref"]] if acquired else [source["id"]]


__all__ = ["TOOL", "MAX_DOWNLOAD_BYTES", "ARGUMENTS_SCHEMA", "validate_geo_arguments", "geo_request_spec",
    "geo_tool_contract", "request_geo", "publish_geo_request"]
