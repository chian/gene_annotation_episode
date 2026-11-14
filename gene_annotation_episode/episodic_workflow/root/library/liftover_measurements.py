"""Store-free producer for one explicitly selected point and chain file.

This adapter performs no acquisition, custody admission or publication. The
caller owns the copied input, process limits and private native streams. Only
the existing liftover core interprets results and calculates components.
"""
from copy import deepcopy
import gzip
import hashlib
from importlib import metadata
from pathlib import Path
import sys
import traceback

from . import liftover_contracts as core


RESULT_VERSION = "ordinary_liftover_result_v1"


def _result(request, *, software_version, state, native=None, failure=None):
    observation = dict(version=core.OBSERVATION_VERSION,
        request_sha256=core.liftover_request_sha256(request),
        chain_file=deepcopy(request["chain"]["file"]),
        software=dict(name="pyliftover", version=software_version),
        conversion_call_state=state,
        conversion_call_count=0 if state == "not_started" else 1,
        result_state="captured" if failure is None else "unavailable",
        native_result=native, failure=failure)
    sheet = core.populate_liftover_sheet(request, native_observation=observation)
    return dict(version=RESULT_VERSION, request=deepcopy(request), sheet=sheet,
        components=core.calculate_liftover_components(sheet))


def _failed(request, error, *, code, software_version, state):
    # The exact diagnostic belongs to the caller's private stderr. Native
    # messages can contain the copied input path, so none is copied into the
    # Source-readable scientific record. None means omitted, not no diagnostic.
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
    failure = dict(stage=core.FAILURES[code], code=code,
        exception_type=type(error).__name__, exception_message=None)
    return _result(request, software_version=software_version, state=state,
        failure=failure)


def run_liftover_tool_request(request, *, chain_path, output_directory):
    """Return one original native observation and the existing core's sheet.

    The declared plain/gzip format selects decoding; the filename does not.
    The same opened binary file is hashed completely and rewound before native
    parsing. A zero call count is scoped only to convert_coordinate, including
    constructor failures after some chain parsing. Operational interruption or
    missing software propagates; this adapter never invents an empty result or
    an observation that an unconfirmed native call did not occur.
    """
    request = core.validate_liftover_request(request)
    software_version = None
    code = "input_unavailable"
    try:
        directory = Path(output_directory).resolve(strict=True)
        if not directory.is_dir():
            raise ValueError("liftover_owned_output_directory_unavailable")
        path = Path(chain_path).resolve(strict=True)
        code = "input_identity_conflict"
        path.relative_to(directory)
        code = "input_unavailable"
        if not path.is_file():
            raise ValueError("liftover_chain_file_unavailable")
        with path.open("rb") as raw:
            code = "chain_read_failed"
            digest, size = hashlib.sha256(), 0
            while block := raw.read(1024 * 1024):
                digest.update(block)
                size += len(block)
            selected = request["chain"]["file"]
            code = "input_identity_conflict"
            if digest.hexdigest() != selected["sha256"] or size != selected["size_bytes"]:
                raise ValueError("liftover_chain_file_identity_conflict")
            code = "chain_read_failed"
            raw.seek(0)

            # This is selected installed software, not a chain or input error.
            # The explicit stream constructor never selects assembly names,
            # searches the current directory/cache, or downloads a chain.
            code = None
            from pyliftover import LiftOver
            try:
                software_version = metadata.version("pyliftover")
            except metadata.PackageNotFoundError:
                software_version = None
            code = "chain_parse_failed"
            try:
                stream = (gzip.GzipFile(fileobj=raw, mode="rb")
                    if selected["format"] == "ucsc_chain_gzip" else raw)
                with stream:
                    converter = LiftOver(stream, search_dir=None, cache_dir=None,
                        use_web=False, write_cache=False, show_progress=False)
            except (OSError, EOFError):
                code = "chain_read_failed"
                raise
    except Exception as error:
        if code is None:
            raise
        return _failed(request, error, code=code,
            software_version=software_version, state="not_started")

    point = request["point"]
    try:
        native = converter.convert_coordinate(point["chromosome"],
            point["position_0based"], point["strand"])
    except Exception as error:
        return _failed(request, error, code="coordinate_conversion_failed",
            software_version=software_version, state="raised")
    try:
        return _result(request, software_version=software_version,
            state="returned", native=native)
    except Exception as error:
        return _failed(request, error, code="native_result_capture_failed",
            software_version=software_version, state="returned")


def validate_liftover_tool_result(value):
    """Validate saved envelope consistency; confer no producer or custody proof.

    All numerical consistency uses the existing core. Canonical comparison also
    preserves distinctions such as native JSON integer, float and boolean cells
    when independently valid copies would compare equal as Python dictionaries.
    """
    if (type(value) is not dict or set(value) != {"version", "request", "sheet", "components"}
            or type(value["version"]) is not str or value["version"] != RESULT_VERSION):
        raise ValueError("liftover_tool_result_invalid")
    request = core.validate_liftover_request(value["request"])
    sheet = core.validate_liftover_sheet(value["sheet"])
    components = core.validate_liftover_components(value["components"])
    if (not core._same(request, sheet["request"])
            or not core._same(sheet, components["sheet"])):
        raise ValueError("liftover_tool_result_identity_conflict")
    return dict(version=RESULT_VERSION, request=request, sheet=sheet, components=components)


__all__ = ["RESULT_VERSION", "run_liftover_tool_request", "validate_liftover_tool_result"]
