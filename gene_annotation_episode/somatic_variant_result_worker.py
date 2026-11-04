"""Store-free retained somatic-stage VCF sheets and one selected calculation.

Every parser/calculator call delegates to vcf_result_measurements. Saved mode
reads only an authenticated retained Sheet; native software, BAM/reference and
original VCF bodies are not inputs to that mode. No Source is created here.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from . import native_flux_balance_storage as storage
from . import somatic_variant_contracts as contracts
from . import vcf_result_measurements as vcf


REQUEST_VERSION = "somatic_variant_result_request_v1"
OUTPUT_VERSION = "somatic_variant_result_output_v1"
CONTEXT_FORMAT = contracts.CONTEXT_VERSION
SHEET_FORMAT = vcf.SHEET_VERSION
COMPONENTS_FORMAT = vcf.COMPONENTS_VERSION


def _descriptor(value, *, format):
    contracts.closed(value, "path file", "result_file_descriptor_invalid")
    contracts.absolute_path(value["path"])
    return contracts.validate_file(value["file"], format=format)


def _read(descriptor):
    raw = storage.read_bytes(descriptor["path"])
    identity = descriptor["file"]
    contracts.require(len(raw) == identity["size_bytes"]
        and hashlib.sha256(raw).hexdigest() == identity["sha256"], "result_file_identity_conflict")
    return raw


def validate_somatic_result_request(value):
    contracts.closed(value, "version mode stage_inputs saved context selection", "result_request_invalid")
    contracts.require(value["version"] == REQUEST_VERSION and value["mode"] in ("parse", "calculate_saved"),
        "result_request_version_invalid")
    contracts.validate_somatic_context(value["context"])
    contracts.validate_somatic_selection(value["selection"])
    if value["mode"] == "parse":
        contracts.require(value["saved"] is None and type(value["stage_inputs"]) is list
            and len(value["stage_inputs"]) == 3, "parse_inputs_invalid")
        for row, stage in zip(value["stage_inputs"], contracts.STAGES):
            contracts.closed(row, "stage input", "stage_input_invalid")
            contracts.require(row["stage"] == stage, "stage_input_order_invalid")
            item = row["input"]
            if item is None:
                continue
            contracts.closed(item, "path file source_ref capture", "stage_file_invalid")
            _descriptor({k: item[k] for k in ("path", "file")}, format="vcf")
            contracts.require(contracts.validate_source(item["source_ref"]) is not None,
                "stage_capture_source_missing")
            capture = item["capture"]
            contracts.closed(capture, "state byte_start_0based byte_end_0based_exclusive original_size_bytes",
                "stage_capture_invalid")
            contracts.require(capture["state"] in ("complete", "truncated", "unknown")
                and type(capture["byte_start_0based"]) is int and capture["byte_start_0based"] == 0
                and type(capture["byte_end_0based_exclusive"]) is int
                and capture["byte_end_0based_exclusive"] == item["file"]["size_bytes"]
                and (capture["original_size_bytes"] is None or type(capture["original_size_bytes"]) is int
                    and capture["original_size_bytes"] >= item["file"]["size_bytes"]), "stage_capture_invalid")
            if capture["state"] == "complete":
                contracts.require(capture["original_size_bytes"] in (None, item["file"]["size_bytes"]),
                    "stage_capture_size_conflict")
            expected = next((r for r in value["context"]["outputs"] if r["role"] == stage), None)
            contracts.require(expected is not None, "stage_native_output_missing")
            contracts.require(capture["original_size_bytes"] is None
                or capture["original_size_bytes"] == expected["size_bytes"], "stage_original_size_conflict")
            if capture["state"] == "complete":
                contracts.require(all(item["file"][k] == expected[k] for k in ("sha256", "size_bytes")),
                    "stage_native_output_identity_conflict")
            else:
                contracts.require(item["file"]["size_bytes"] <= expected["size_bytes"],
                    "stage_capture_size_conflict")
    else:
        contracts.require(value["stage_inputs"] is None and type(value["saved"]) is dict,
            "saved_inputs_invalid")
        contracts.closed(value["saved"], "stage sheet", "saved_input_invalid")
        contracts.require(value["saved"]["stage"] == value["selection"]["stage"], "saved_stage_conflict")
        _descriptor(value["saved"]["sheet"], format=SHEET_FORMAT)
    return deepcopy(value)


def _parse(row):
    stage, item = row["stage"], row["input"]
    if item is None:
        return vcf.parse_vcf_sheet({"input_id": "somatic_stage:" + stage,
            "retained_file": None, "original_file": None, "source_ref": None, "content": None,
            "capture": {"state": "missing", "byte_start_0based": 0,
                "byte_end_0based_exclusive": 0, "original_size_bytes": None}})
    raw = _read(item)
    return vcf.parse_vcf_sheet({"input_id": item["source_ref"], "retained_file": item["file"],
        "original_file": item["file"] if item["capture"]["state"] == "complete" else None,
        "source_ref": item["source_ref"], "content": raw, "capture": item["capture"]})


def _write(root, name, format, value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False).encode("utf-8") + b"\n"
    storage.immutable_bytes(root / name, raw)
    pin = storage.file_pin(root / name)
    return {"relative_path": name, "format": format, "sha256": pin["sha256"], "size_bytes": pin["size_bytes"]}


def validate_somatic_result_output(value):
    contracts.closed(value, "version mode stage_sheets context components value", "result_output_invalid")
    contracts.require(value["version"] == OUTPUT_VERSION and value["mode"] in ("parse", "calculate_saved"),
        "result_output_version_invalid")
    contracts.require(type(value["stage_sheets"]) is list and len(value["stage_sheets"]) == 3,
        "result_output_sheets_invalid")
    declarations = []
    for row, stage in zip(value["stage_sheets"], contracts.STAGES):
        contracts.closed(row, "stage sheet", "result_output_sheet_invalid")
        contracts.require(row["stage"] == stage, "result_output_stage_order_invalid")
        if value["mode"] == "calculate_saved":
            contracts.require(row["sheet"] is None, "saved_sheet_declaration_conflict")
        else:
            declarations.append((row["sheet"], stage + "_sheet.json", SHEET_FORMAT))
    declarations += [(value["context"], "context.json", CONTEXT_FORMAT),
        (value["components"], "components.json", COMPONENTS_FORMAT),
        (value["value"], "value.json", contracts.PACKET_VERSION)]
    for declaration, name, format in declarations:
        contracts.closed(declaration, "relative_path format sha256 size_bytes", "result_output_declaration_invalid")
        contracts.require(declaration["relative_path"] == name and declaration["format"] == format,
            "result_output_declaration_conflict")
        contracts.require(contracts._sha(declaration["sha256"]) and type(declaration["size_bytes"]) is int
            and declaration["size_bytes"] >= 0, "result_output_identity_invalid")
    return deepcopy(value)


def run_somatic_variant_result(request, *, output_directory):
    request = validate_somatic_result_request(request)
    root = storage.directory(contracts.absolute_path(str(output_directory)))
    names = [stage + "_sheet.json" for stage in contracts.STAGES] + ["context.json", "components.json", "value.json"]
    contracts.require(all(not storage.confined_file(root, name).exists() for name in names),
        "result_output_exists")
    result = {"version": OUTPUT_VERSION, "mode": request["mode"],
        "stage_sheets": [{"stage": stage, "sheet": None} for stage in contracts.STAGES],
        "context": None, "components": None, "value": None}
    result["context"] = _write(root, "context.json", CONTEXT_FORMAT, request["context"])
    if request["mode"] == "parse":
        sheets = {}
        for row, output in zip(request["stage_inputs"], result["stage_sheets"]):
            sheet = _parse(row)
            sheets[row["stage"]] = sheet
            output["sheet"] = _write(root, row["stage"] + "_sheet.json", SHEET_FORMAT, sheet)
        sheet = sheets[request["selection"]["stage"]]
    else:
        sheet = vcf.validate_vcf_sheet(storage.decode_json(_read(request["saved"]["sheet"])))
    contracts.validate_somatic_stage_input(sheet["input"], context=request["context"], stage=request["selection"]["stage"])
    selection = contracts.validate_somatic_selection(request["selection"], sheet=sheet)
    components = vcf.calculate_vcf_components(sheet, selection["vcf"])
    contracts.require(components["sheet_sha256"] == vcf._hash(sheet), "result_sheet_join_conflict")
    packet = contracts.build_somatic_packet(context=request["context"], selection=selection, components=components)
    result["components"] = _write(root, "components.json", COMPONENTS_FORMAT, components)
    result["value"] = _write(root, "value.json", contracts.PACKET_VERSION, packet)
    return validate_somatic_result_output(result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    parser.add_argument("result")
    args = parser.parse_args(argv)
    request = Path(contracts.absolute_path(args.request))
    result = Path(contracts.absolute_path(args.result))
    contracts.require(request.parent == result.parent and request != result
        and result.name not in {stage + "_sheet.json" for stage in contracts.STAGES}
        | {"context.json", "components.json", "value.json"}, "result_worker_path_invalid")
    contracts.require(not result.exists() and not result.is_symlink(), "result_worker_exists")
    payload = storage.read_json(request)
    contracts.closed(payload, "operation arguments", "result_worker_envelope_invalid")
    contracts.require(payload["operation"] == contracts.RESULT_OPERATION, "result_worker_operation_invalid")
    contracts.closed(payload["arguments"], "request", "result_worker_arguments_invalid")
    output = run_somatic_variant_result(payload["arguments"]["request"], output_directory=result.parent)
    storage.immutable_json(result, output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
