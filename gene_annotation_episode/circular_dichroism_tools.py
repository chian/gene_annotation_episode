"""Ordinary CD File preparation, one existing calculation, and literal views.

The host authenticates input custody and publishes through the shared molecular
owner. The Store-free worker reads only its copied File and uses the existing
CD numerical authority. Neither side chooses another method or creates an
episode. Saved modes retain the original Source and historical observations.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import stat

from . import circular_dichroism_contracts as contracts
from . import circular_dichroism_measurements as core
from .molecular_sequence_input_contracts import decode_molecular_sequence_input


CD_TOOL = contracts.CD_TOOL
_HOST_REQUEST_VERSION = "ordinary_cd_request_v1"


def circular_dichroism_tool_contract():
    return dict(resources="local", description=(
        "Calculate source-defined signed spectral point counts and relative thermal-signal summaries from an "
        "explicitly received versioned CD JSON File. Retain ordered measurements, units, original point identities, "
        "partial results and the source-labelled heuristic qualifications. Thermal summaries use min-max relative "
        "signal, the first sampled point nearest one half, and the source's N-point transition width. "
        "These are descriptive source heuristics, with no calibrated structure fractions, fitted melting parameters "
        "or function-confidence probabilities. Alternatively read literal stored values or recalculate the retained "
        "sheet with the same numerical authority. Explicit selected-row views preserve original ordinals and the "
        "full original populations; neither saved mode acquires data or republishes the original Source."),
        input_schema=contracts.circular_dichroism_tool_argument_schema())


def _regular(path):
    try:
        return stat.S_ISREG(Path(path).lstat().st_mode)
    except OSError:
        return False


def run_circular_dichroism_tool_request(request, *, input_path, output_directory):
    """Verify copied bytes, decode once, then use the existing CD calculation.

    One direct population and one numerical calculation occur here. The
    calculator's existing internal sheet revalidation/population is unchanged.
    This is not execution of the original Biomni function; its provenance flag
    remains false. Only the enclosing selected worker writes the result file.
    """
    request = contracts.validate_circular_dichroism_tool_request(request)
    try:
        directory = Path(output_directory).resolve(strict=True)
        path = Path(input_path)
        if not directory.is_dir() or not _regular(path):
            raise ValueError("circular_dichroism_input_unavailable")
        if path.resolve(strict=True).parent != directory:
            raise ValueError("circular_dichroism_owned_input_conflict")
        selected = request["input_file"]
        with path.open("rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != selected["size_bytes"]:
                raise ValueError("circular_dichroism_input_identity_conflict")
            raw = stream.read()
    except OSError as error:
        raise ValueError("circular_dichroism_input_unavailable") from error
    if len(raw) != selected["size_bytes"] or hashlib.sha256(raw).hexdigest() != selected["sha256"]:
        raise ValueError("circular_dichroism_input_identity_conflict")
    decoded = decode_molecular_sequence_input(raw, tag_key="schema")
    if decoded["failure"] is not None:
        raise ValueError("circular_dichroism_input_" + decoded["failure"]["code"])
    sheet = core.populate_circular_dichroism_sheet(measurements=decoded["value"])
    components = core.calculate_circular_dichroism_components(sheet)
    return dict(version=contracts.RESULT_VERSION, request=request, sheet=sheet, components=components)


def _verify_copy(path, file):
    from .domain import ContractError
    if not _regular(path):
        raise ContractError("circular_dichroism_copied_input_conflict")
    digest, size = hashlib.sha256(), 0
    with Path(path).open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block); size += len(block)
    if digest.hexdigest() != file["sha256"] or size != file["size_bytes"]:
        raise ContractError("circular_dichroism_copied_input_conflict")


def _copy_once(source, destination, file):
    if destination.exists() or destination.is_symlink():
        _verify_copy(destination, file)
        return
    with Path(source).open("rb") as incoming, destination.open("xb") as output:
        while block := incoming.read(1024 * 1024):
            output.write(block)
        output.flush(); os.fsync(output.fileno())
    _verify_copy(destination, file)


def _projection(stored, source_ref, view):
    return (contracts.project_circular_dichroism_return(stored, source_ref=source_ref) if view is None else
        contracts.project_circular_dichroism_view(stored, source_ref=source_ref, view=view))


def _output_failure(registry, work, directory, failure, invalid):
    from .acquisition import AcquisitionError
    from .materials import artifact_file
    diagnostic = deepcopy(failure["diagnostic"]) if failure is not None else dict(execution=deepcopy(work.metadata))
    diagnostic["native_output_validation"] = dict(exception_type=type(invalid).__name__, message=str(invalid))
    diagnostic["retained_artifacts"] = {name: artifact_file(registry.store, path, "application/octet-stream")
        for name, path in (("stdout", directory / "stdout"), ("stderr", directory / "stderr"), ("worker_output", work.output_path))
        if _regular(path)}
    original = (failure["operational"] or {}) if failure is not None else work.metadata
    code = (failure["code"] if failure is not None else
        "local_job_output_invalid" if work.output_path.exists() else "local_job_output_missing")
    phase = failure["phase"] if failure is not None else "local_execution"
    raise AcquisitionError(code, phase=phase, diagnostic=diagnostic,
        operational={**{key: original[key] for key in ("resource", "limit", "evidence") if key in original},
            "known_terminal": True, "native_returncode": work.metadata.get("native_returncode"),
            "worker_operation": "circular_dichroism"}) from invalid


async def prepare_circular_dichroism_work(registry, arguments, *, scope, operation_key, authority):
    from .communication import plain
    from .domain import ContractError, canonical
    from .molecular_measurement_tools import read_retained_molecular_publication
    arguments = contracts.validate_circular_dichroism_tool_arguments(arguments)
    if not isinstance(authority, tuple) or len(authority) != 2 or not callable(authority[1]):
        raise ContractError("circular_dichroism_authority_required")
    context, reader = authority
    mode = arguments["mode"]
    if mode in {"read_stored", "calculate_saved"}:
        publication = read_retained_molecular_publication(registry, context, reader,
            arguments["result_ref"], tool_name=CD_TOOL)
        stored = publication["stored"]
        components = stored["components"]
        if mode == "calculate_saved":
            components = core.calculate_circular_dichroism_components(stored["sheet"])
            if canonical(components) != canonical(stored["components"]):
                raise ContractError("circular_dichroism_saved_components_conflict")
        reference = publication["source"]["id"]
        return dict(stored=stored, components=components,
            projection=_projection(stored, reference, arguments["view"]),
            item=publication["received_input"], source_ref=reference)
    selected = arguments["input"]
    received = reader(context, selected["reference"], selected["namespace"], tag_key="schema")
    if received["failure"] is not None:
        raise ContractError("molecular_tool_" + received["failure"]["code"])
    item = received["input"]
    from .native_file_capture import NativeFileCaptureError, retained_native_file
    try:
        input_path = retained_native_file(registry.store, item["file"])
    except NativeFileCaptureError as error:
        raise ContractError("circular_dichroism_input_" + error.code) from error
    scientific = contracts.validate_circular_dichroism_tool_request(
        dict(version=contracts.REQUEST_VERSION, input_file=deepcopy(item["file"])))
    invocation = dict(run_id=context.run_id, episode_id=context.episode_id, operation_key=operation_key,
        decision_index=int(operation_key.rsplit(":", 1)[1]),
        request_sha256=hashlib.sha256(canonical(plain(context.request)).encode()).hexdigest(), scope=plain(scope))
    request = dict(version=_HOST_REQUEST_VERSION, arguments=deepcopy(arguments), invocation=invocation,
        received_input=deepcopy(item), request=scientific)
    directory = registry.store.path / "cache" / "molecular-measurements" / hashlib.sha256(operation_key.encode()).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    if directory.is_symlink() or not directory.resolve().is_relative_to(registry.store.path.resolve()):
        raise ContractError("circular_dichroism_owned_directory_conflict")
    from ._local_job_worker import atomic_json
    binding, copied = directory / "host-binding.json", directory / "input.json"
    if binding.exists() or binding.is_symlink():
        try:
            if not _regular(binding) or canonical(json.loads(binding.read_bytes())) != canonical(request):
                raise ContractError("circular_dichroism_original_binding_conflict")
        except (OSError, ValueError) as error:
            raise ContractError("circular_dichroism_original_binding_conflict") from error
    else:
        if any((directory / name).exists() or (directory / name).is_symlink() for name in (
                "input.json", "native-handle.json", "execution-selection.json", "worker-request.json", "worker-result.json", "stdout", "stderr")):
            raise ContractError("circular_dichroism_original_binding_missing")
        atomic_json(binding, request)
    _copy_once(input_path, copied, scientific["input_file"])
    work = await registry._sequence_worker_async("circular_dichroism", dict(request=scientific, input_path=str(copied)),
        directory=directory, owned_directory=directory)
    failure = work.metadata.get("molecular_failure")
    try:
        if not _regular(work.output_path) or work.output_path.resolve().parent != directory.resolve():
            raise ContractError("circular_dichroism_worker_output_unavailable")
        stored = contracts.validate_circular_dichroism_tool_result(json.loads(work.output_path.read_bytes()))
        if canonical(stored["request"]) != canonical(scientific):
            raise ContractError("circular_dichroism_worker_request_conflict")
        expected = core.populate_circular_dichroism_sheet(measurements=item["content"]["value"])
        if canonical(stored["sheet"]) != canonical(expected):
            raise ContractError("circular_dichroism_worker_input_conflict")
    except (OSError, ValueError, TypeError, KeyError) as invalid:
        _output_failure(registry, work, directory, failure, invalid)
    return dict(work=work, stored=stored, item=item, request=request, operational_failure=failure)


def publish_circular_dichroism_work(registry, arguments, prepared):
    from .domain import ContractError
    if arguments["mode"] in {"read_stored", "calculate_saved"}:
        return prepared["projection"], [prepared["source_ref"]]
    if arguments["mode"] != "calculate":
        raise ContractError("circular_dichroism_mode_invalid")
    from .molecular_measurement_tools import retain_molecular_publication
    publication = retain_molecular_publication(registry, prepared, tool_name=CD_TOOL)
    reference = publication["source"]["id"]
    return _projection(prepared["stored"], reference, arguments["view"]), [reference]


__all__ = ["CD_TOOL", "circular_dichroism_tool_contract", "run_circular_dichroism_tool_request",
    "prepare_circular_dichroism_work", "publish_circular_dichroism_work"]
