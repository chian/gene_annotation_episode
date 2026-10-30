"""One supplied-data protein operation; no alignment, acquisition or retry.

The pure dispatch port consumes authorized bytes. The CLI alone reads staged
files, checks the selected software and writes the complete native result.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys
import traceback
from typing import get_args

from .execution_contracts import canonical
from . import protein_structure_contracts as science
from .native_protein_structure_contracts import (
    ScientificRequest, NativeProteinResult, Software, SuppliedBytes, NATIVE_FORMATS,
    WORKER_INPUT_FILENAME, _require, validate_protein_structure_request,
    validate_protein_structure_software, validate_native_protein_structure_result,
    validate_input_associations, validate_protein_structure_worker_input,
)
from .protein_structure_formats import parse_pdb_structure, parse_mmcif_structure
from .protein_structure_sequences import inspect_structure, extract_structure_sequence, rebind_structure_sequence
from .protein_structure_metadata import extract_native_structure_metadata
from .protein_structure_correspondence import correspondence_from_pairwise_sheet, validate_explicit_residue_map
from .alignment_correspondence import validate_correspondence_artifacts
from .biopython_pairwise_grader import validate_biopython_correspondence


def strict_json(raw):
    if type(raw) is bytes:
        raw = raw.decode("utf-8")
    def pairs(items):
        value = {}
        for key, item in items:
            _require(key not in value)
            value[key] = item
        return value
    def nonfinite(_):
        raise ValueError("invalid_schema")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def _checksum(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_selected_software(selected: Software) -> None:
    """Verify actual interpreter/dependencies/source pins, never substitute them."""
    import numpy
    import Bio
    selected = validate_protein_structure_software(selected)
    _require({"gene_annotation_episode.biopython_pairwise_grader", "gene_annotation_episode.alignment_correspondence"}
        <= {row["module"] for row in selected["implementation_files"]}, "software_identity_mismatch")
    observed = {"python_executable": sys.executable, "python_sha256": _checksum(sys.executable),
        "python_version": platform.python_version(), "numpy_version": numpy.__version__,
        "biopython_version": Bio.__version__, "implementation_files": []}
    for row in selected["implementation_files"]:
        spec = importlib.util.find_spec(row["module"])
        _require(spec is not None and spec.origin is not None, "software_identity_mismatch")
        observed["implementation_files"].append({"module": row["module"], "sha256": _checksum(spec.origin)})
    print(canonical({"version": "protein_structure_software_observation_v1", "software": observed}), flush=True)
    _require(Path(selected["python_executable"]).resolve() == Path(sys.executable).resolve(), "software_identity_mismatch")
    for name in ("python_sha256", "python_version", "numpy_version", "biopython_version", "implementation_files"):
        _require(science.same(selected[name], observed[name]), "software_identity_mismatch")


def _supplied(request, rows):
    _require(type(rows) is list)
    for row in rows:
        _require(type(row) is dict and set(row) == {"input_id", "role", "file_identity", "data"})
        _require(type(row["input_id"]) is str and type(row["role"]) is str and type(row["data"]) is bytes)
    validate_input_associations(request, rows)
    for row in rows:
        identity = row["file_identity"]
        _require(len(row["data"]) == identity["byte_length"] and
            hashlib.sha256(row["data"]).hexdigest() == identity["sha256"], "input_digest_mismatch")
    return deepcopy(rows)


def _parse(data, file, block=None):
    if file["format"] == "pdb_3x_text":
        return parse_pdb_structure(data, file_identity=file)
    return parse_mmcif_structure(data, file_identity=file, data_block=block)


def _metadata(request, rows):
    result = []
    for file in request.get("supplied_metadata_files", []):
        matches = [r for r in rows if r["role"] == "supplied_metadata" and science.same(r["file_identity"], file)]
        _require(len(matches) == 1, "metadata_join_conflict")
        result.append({"file_identity": deepcopy(file), "document": science.validate_metadata_document(strict_json(matches[0]["data"]))})
    return result


def _deduplicate(rows):
    result = []
    for row in rows:
        if not any(science.same(row, prior) for prior in result):
            result.append(deepcopy(row))
    return result


def _state(records):
    states = [r["state"] for r in records]
    if all(s == "complete" for s in states):
        return "complete"
    return "invalid" if all(s == "invalid" for s in states) else "partial"


def _alignment_correspondence(request, rows, parsed, sequences):
    corr = request["correspondence"]
    data = {row["role"]: row["data"] for row in rows if row["role"] != "supplied_metadata"}
    for side in ("fixed", "moving"):
        descriptor = corr[side + "_sequence_descriptor"]
        original_map = science.validate_structure_sequence(strict_json(data[side + "_residue_map"]))
        original = extract_structure_sequence(parsed[side], selection=descriptor["selection"])
        _require(science.same(original_map, original), "sequence_artifact_mismatch")
        _require(science.same(original["selection"], descriptor["selection"]) and original["sequence_available"]
            and original["sequence_length"] == descriptor["sequence_length"], "sequence_artifact_mismatch")
        _require(data[side + "_sequence"] == original["alignment_sequence"].encode("ascii"), "sequence_artifact_mismatch")
        _require(science.same(rebind_structure_sequence(original, structure_role=side), sequences[side]), "sequence_artifact_mismatch")
    native = strict_json(data["alignment_native"])
    grading = strict_json(data["alignment_grading"])
    legacy = _alignment_grading(grading, native_artifact_ref=corr["alignment"]["native_file"]["artifact_ref"],
        grading_format=corr["alignment"]["grading_file"]["format"])
    sheet = legacy["sheet"]
    _require(type(sheet) is dict and science.same(sheet.get("native_result"), native), "invalid_traceback")
    return correspondence_from_pairwise_sheet(sheet, native=native, alignment=corr["alignment"],
        fixed=sequences["fixed"], moving=sequences["moving"],
        fixed_descriptor=corr["fixed_sequence_descriptor"], moving_descriptor=corr["moving_sequence_descriptor"],
        orientation=corr["orientation"])


def _alignment_grading(grading, *, native_artifact_ref, grading_format):
    """Read explicit original envelopes; compare v2 saved cells without regrading."""
    _require(type(grading) is dict, "invalid_traceback")
    version = grading.get("schema")
    fields = {"schema", "provider", "native_artifact_ref", "grading"}
    if version == "tool_grading_artifact_v2":
        fields.add("correspondence")
    _require(version in {"tool_grading_artifact_v1", "tool_grading_artifact_v2"} and set(grading) == fields,
        "invalid_traceback")
    _require(version == grading_format and grading["provider"] == "biopython.alignment"
        and grading["native_artifact_ref"] == native_artifact_ref,
        "alignment_operand_mismatch")
    legacy = grading["grading"]
    _require(type(legacy) is dict and set(legacy) == {"sheet", "scores"}, "invalid_traceback")
    if version == "tool_grading_artifact_v2":
        try:
            companion = validate_correspondence_artifacts(grading["correspondence"], admission=False)
            _require(len(companion["instances"]) == 1, "invalid_traceback")
            validate_biopython_correspondence(legacy, companion["instances"][0])
        except (ValueError, KeyError, TypeError, IndexError) as error:
            raise ValueError("invalid_traceback") from error
    return legacy


def _received_transform(request, rows):
    declared = request["parameters"]["declared_transform"]
    if declared is None or declared["received_from"] is None:
        return
    # This checks retained numerical equality, not the original receipt grant;
    # D has already authenticated that grant before commissioning this worker.
    by_role = {r["role"]: r for r in rows}
    sheet = science.validate_protein_structure_sheet(strict_json(by_role["received_transform_sheet"]["data"]))
    components = science.validate_protein_structure_components(strict_json(by_role["received_transform_components"]["data"]))
    received = declared["received_from"]
    _require(sheet["native_baseline"] is not None and received["saved_sheet"]["original_mode"] == sheet["native_request"]["mode"], "original_commission_mismatch")
    transform = components["transform"]
    _require(components["calculation_id"] == received["calculation_id"] and transform["state"] == "identifiable_fit", "invalid_transform")
    _require(science.same(transform["rotation"]["value"], declared["rotation"]) and
        science.same(transform["translation"]["value"], declared["translation_A"]), "invalid_transform")
    for side in ("fixed", "moving"):
        _require(science.same(sheet["sequences"][side]["selection"], request[side + "_selection"]), "invalid_transform")
    from .protein_structure_calculations import validate_recorded_protein_structure_components
    validate_recorded_protein_structure_components(sheet, components=components)


def execute_protein_structure_request(request: ScientificRequest, *,
    input_bytes: list[SuppliedBytes], software: Software) -> NativeProteinResult:
    """Deterministic dispatch on supplied bytes; no producer reads or fitting loop."""
    request = validate_protein_structure_request(request)
    software = validate_protein_structure_software(software)
    rows = _supplied(request, input_bytes)
    data = {row["role"]: row["data"] for row in rows if row["role"] != "supplied_metadata"}
    operation = request["operation"]
    base = {"version": NATIVE_FORMATS[operation], "producer": software, "request": request}
    if operation == "inspect":
        parsed = _parse(data["single_structure"], request["structure_file"])
        inventory = inspect_structure(parsed, inventory_selection=request["inventory"])
        result = {**base, "parsed": parsed, "inventory": inventory,
            "state": _state([parsed, inventory]), "issues": _deduplicate(parsed["issues"] + inventory["issues"])}
    elif operation == "extract_sequence":
        selection = request["selection"]
        parsed = _parse(data["single_structure"], selection["file_identity"], selection["data_block"])
        sequence = extract_structure_sequence(parsed, selection=selection)
        metadata = extract_native_structure_metadata(parsed, selected_sequence=sequence, supplied_metadata=_metadata(request, rows))
        result = {**base, "parsed": parsed, "sequence": sequence, "metadata": metadata,
            "state": _state([parsed, sequence, metadata]), "issues": _deduplicate(parsed["issues"] + sequence["issues"] + metadata["issues"])}
    else:
        from .protein_structure_sheet import build_protein_structure_sheet
        from .protein_structure_calculations import calculate_protein_structure_components
        try:
            supplied_metadata = _metadata(request, rows)
            parsed, sequences, metadata = {}, {}, {}
            for side in ("fixed", "moving"):
                selection = request[side + "_selection"]
                parsed[side] = _parse(data[side + "_structure"], selection["file_identity"], selection["data_block"])
                sequences[side] = extract_structure_sequence(parsed[side], selection=selection)
                metadata[side] = extract_native_structure_metadata(parsed[side], selected_sequence=sequences[side], supplied_metadata=supplied_metadata)
            source = request["correspondence"]
            if source["kind"] == "explicit_map":
                correspondence = validate_explicit_residue_map(strict_json(data["explicit_map"]), map_file=source["map_file"],
                    fixed=sequences["fixed"], moving=sequences["moving"])
            else:
                correspondence = _alignment_correspondence(request, rows, parsed, sequences)
            _received_transform(request, rows)
            sheet = build_protein_structure_sheet(fixed=parsed["fixed"], moving=parsed["moving"],
                fixed_sequence=sequences["fixed"], moving_sequence=sequences["moving"], correspondence=correspondence,
                correspondence_input=source, fixed_metadata=metadata["fixed"], moving_metadata=metadata["moving"],
                native_request=request["parameters"], native_baseline=None)
            components = calculate_protein_structure_components(sheet, parameters=request["parameters"])
            sheet["native_baseline"] = deepcopy(components)
            result = {**base, "sheet": sheet, "state": components["state"],
                "issues": _deduplicate(sheet["parse_issues"] + sheet["correspondence_issues"] + components["issues"])}
        except (ValueError, UnicodeError) as error:
            code = str(error) if str(error) in get_args(science.IssueCode) else "invalid_schema"
            result = {**base, "sheet": None, "state": "invalid", "issues": [science.issue(code, stage="input")]}
    return validate_native_protein_structure_result(result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-json", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args(argv)
    from .native_protein_structure_driver import confined_file, _directory, _strict_json, _regular, immutable_bytes
    directory = _directory(Path.cwd())
    _require(Path(args.request_json) == directory / WORKER_INPUT_FILENAME and Path(args.output_json) == directory / "result.json", "invalid_output_path")
    original = validate_protein_structure_worker_input(_strict_json(confined_file(directory, WORKER_INPUT_FILENAME)))
    check_selected_software(original["software"])
    inputs = []
    for row in original["files"]:
        expected = confined_file(directory, "inputs/" + row["input_id"])
        _require(row["path"] == str(expected), "invalid_output_path")
        with _regular(expected) as stream:
            raw = stream.read()
        inputs.append({k: deepcopy(row[k]) for k in ("input_id", "role", "file_identity")} | {"data": raw})
    result = execute_protein_structure_request(original["request"], input_bytes=inputs, software=original["software"])
    immutable_bytes(confined_file(directory, "result.json"), canonical(result).encode("utf-8"))
    if result["version"] == NATIVE_FORMATS["extract_sequence"]:
        sequence = result["sequence"]
        immutable_bytes(confined_file(directory, "residue-map.json"), canonical(sequence).encode("utf-8"))
        if sequence["sequence_available"]:
            immutable_bytes(confined_file(directory, "sequence.txt"), sequence["alignment_sequence"].encode("ascii"))
    # A typed unavailable scientific quantity is still an executed operation.
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc(file=sys.stderr)
        raise SystemExit(1)
