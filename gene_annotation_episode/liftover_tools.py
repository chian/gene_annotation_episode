"""Ordinary point-liftover preparation and saved-value selection.

The shared invocation/input owners authenticate the selected action and File.
Only the owned sequence worker converts coordinates. Existing liftover contracts
interpret its result; the shared publisher retains the original publication.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

from .communication import plain
from .domain import ContractError, REF, canonical, obj
from . import liftover_contracts as core
from .liftover_measurements import validate_liftover_tool_result


LIFTOVER_TOOL = "liftover_coordinates"
_REQUEST_VERSION = "ordinary_liftover_request_v1"


def liftover_tool_contract():
    point = core.liftover_request_schema()["properties"]["point"]
    convert = obj(dict(mode={"const": "convert"},
        input=obj(dict(namespace={"enum": ["source", "artifact"]}, reference=deepcopy(REF))),
        chain_format={"enum": list(core.CHAIN_FORMATS)}, point=point))
    saved = obj(dict(mode={"enum": ["read_stored", "calculate_saved"]}, result_ref=deepcopy(REF),
        mapping_ordinals={"type": "array", "items": {"type": "integer", "minimum": 0}, "uniqueItems": True}))
    return dict(resources="local", description=(
        "Convert one explicitly supplied zero-based point using an explicitly received UCSC chain File and "
        "its selected plain or gzip format. Preserve literal contigs, strands, native mapping order and chain "
        "alignment scores, including absent, empty, multiple and failed results. Assembly labels remain unavailable "
        "in this contract; this operation does not infer assemblies or fetch chains. "
        "Alternatively select original stored rows, or calculate an explicitly selected row view from the saved "
        "sheet, without another coordinate conversion. Row selection preserves the full-native-population meaning."),
        input_schema={"anyOf": [convert, saved]})


def _verify_copy(path, file):
    if path.is_symlink() or not path.is_file():
        raise ContractError("ordinary_liftover_copied_input_conflict")
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
            size += len(block)
    if digest.hexdigest() != file["sha256"] or size != file["size_bytes"]:
        raise ContractError("ordinary_liftover_copied_input_conflict")


def _copy_once(source, destination, file):
    if destination.exists() or destination.is_symlink():
        _verify_copy(destination, file)
        return
    # Exclusive creation never overwrites another original or a partial copy.
    # An interrupted/changed copy stays available for diagnosis rather than
    # silently becoming a new input on the same selected operation.
    with Path(source).open("rb") as incoming, destination.open("xb") as output:
        while block := incoming.read(1024 * 1024):
            output.write(block)
        output.flush()
        os.fsync(output.fileno())
    _verify_copy(destination, file)


def _stored_view(stored, ordinals):
    if (type(ordinals) is not list or any(type(i) is not int or i < 0 for i in ordinals)
            or len(ordinals) != len(set(ordinals))):
        raise ContractError("liftover_mapping_ordinal_invalid")
    components = deepcopy(stored["components"])
    rows = {row["ordinal"]: row for row in components["rows"]}
    if any(i not in rows for i in ordinals):
        raise ContractError("ordinary_liftover_cells_not_stored")
    components["selection"] = dict(mapping_ordinals=list(ordinals))
    components["rows"] = [deepcopy(rows[i]) for i in ordinals]
    return components


def _output_failure(registry, work, directory, failure, invalid):
    from .acquisition import AcquisitionError
    from .materials import artifact_file
    diagnostic = deepcopy(failure["diagnostic"]) if failure is not None else dict(execution=deepcopy(work.metadata))
    diagnostic["native_output_validation"] = dict(exception_type=type(invalid).__name__, message=str(invalid))
    diagnostic["retained_artifacts"] = {name: artifact_file(registry.store, path, "application/octet-stream")
        for name, path in (("stdout", directory / "stdout"), ("stderr", directory / "stderr"),
            ("worker_output", work.output_path)) if path.is_file()}
    original = (failure["operational"] or {}) if failure is not None else work.metadata
    code = (failure["code"] if failure is not None else
        "local_job_output_invalid" if work.output_path.is_file() else "local_job_output_missing")
    phase = failure["phase"] if failure is not None else "local_execution"
    raise AcquisitionError(code, phase=phase, diagnostic=diagnostic,
        operational={**{key: original[key] for key in ("resource", "limit", "evidence") if key in original},
            "known_terminal": True, "native_returncode": work.metadata.get("native_returncode"),
            "conversion_call_state": "uncertain", "conversion_call_count": None}) from invalid


async def prepare_liftover_work(registry, arguments, *, scope, operation_key, authority):
    context, reader = authority
    mode = arguments["mode"]
    if mode in {"read_stored", "calculate_saved"}:
        from .molecular_measurement_tools import read_retained_molecular_publication
        publication = read_retained_molecular_publication(registry, context, reader,
            arguments["result_ref"], tool_name=LIFTOVER_TOOL)
        stored = publication["stored"]
        components = (_stored_view(stored, arguments["mapping_ordinals"]) if mode == "read_stored" else
            core.calculate_liftover_components(stored["sheet"], mapping_ordinals=arguments["mapping_ordinals"]))
        projection = core.project_liftover_return(components, source_ref=publication["source"]["id"])
        # Preserve the full original stored document separately from this view.
        return dict(stored=stored, components=components, projection=projection,
            item=publication["received_input"], source_ref=publication["source"]["id"])
    if mode != "convert":
        raise ContractError("ordinary_liftover_mode_invalid")
    selected = arguments["input"]
    received, input_path = reader(context, selected["reference"], selected["namespace"],
        file_format=arguments["chain_format"])
    if received["failure"] is not None:
        raise ContractError("molecular_tool_" + received["failure"]["code"])
    if input_path is None:
        raise ContractError("ordinary_liftover_input_path_required")
    item = received["input"]
    witness = item["witness"]
    scientific = core.validate_liftover_request(dict(version=core.REQUEST_VERSION,
        chain=dict(file=deepcopy(item["file"]), source_ref=witness["reference"] if witness["namespace"] == "source" else None),
        point=deepcopy(arguments["point"])))
    invocation = dict(run_id=context.run_id, episode_id=context.episode_id, operation_key=operation_key,
        decision_index=int(operation_key.rsplit(":", 1)[1]),
        request_sha256=hashlib.sha256(canonical(plain(context.request)).encode()).hexdigest(), scope=plain(scope))
    request = dict(version=_REQUEST_VERSION, arguments=deepcopy(arguments), invocation=invocation,
        received_input=deepcopy(item), request=scientific)
    directory = registry.store.path / "cache" / "molecular-measurements" / hashlib.sha256(operation_key.encode()).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    if directory.is_symlink():
        raise ContractError("ordinary_liftover_owned_directory_conflict")
    from ._local_job_worker import atomic_json
    binding, copied = directory / "host-binding.json", directory / "input.chain"
    if binding.exists():
        if binding.is_symlink() or canonical(json.loads(binding.read_bytes())) != canonical(request):
            raise ContractError("ordinary_liftover_original_binding_conflict")
    else:
        if binding.is_symlink() or any((directory / name).exists() for name in (
                "input.chain", "native-handle.json", "execution-selection.json", "worker-request.json", "worker-result.json")):
            raise ContractError("ordinary_liftover_original_binding_missing")
        atomic_json(binding, request)
    _copy_once(input_path, copied, scientific["chain"]["file"])
    work = await registry._sequence_worker_async("liftover_point",
        dict(request=scientific, chain_path=str(copied)), directory=directory, owned_directory=directory)
    failure = work.metadata.get("molecular_failure")
    try:
        stored = validate_liftover_tool_result(json.loads(work.output_path.read_bytes()))
        if canonical(stored["request"]) != canonical(scientific):
            raise ContractError("ordinary_liftover_worker_request_conflict")
    except (OSError, ValueError, TypeError, KeyError) as invalid:
        _output_failure(registry, work, directory, failure, invalid)
    return dict(work=work, stored=stored, item=item, request=request, operational_failure=failure)


def publish_liftover_work(registry, arguments, prepared):
    if arguments["mode"] in {"read_stored", "calculate_saved"}:
        return prepared["projection"], [prepared["source_ref"]]
    if arguments["mode"] != "convert":
        raise ContractError("ordinary_liftover_mode_invalid")
    from .molecular_measurement_tools import retain_molecular_publication
    publication = retain_molecular_publication(registry, prepared, tool_name=LIFTOVER_TOOL)
    source_ref = publication["source"]["id"]
    return core.project_liftover_return(prepared["stored"]["components"], source_ref=source_ref), [source_ref]


__all__ = ["LIFTOVER_TOOL", "liftover_tool_contract", "prepare_liftover_work", "publish_liftover_work"]
