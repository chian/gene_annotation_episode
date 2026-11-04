"""Finite retained-table calculation; no native reacquisition or execution.

The host supplies original controls and captured regular files. This worker
uses C1 read-only arrays and C2 calculations in one context, then declares
closed bytes. File production does not grant result authority or completion.
"""
from __future__ import annotations

from contextlib import ExitStack
from copy import deepcopy
import hashlib
from pathlib import Path
import sys

from .chromatin_interaction_contracts import ChromatinValidationError, validate_chromatin_record
from .native_chromatin_interaction_contracts import (
    TABLE_ROLES, TABLE_NAMES, canonical, digest, failure, unique_failures, require,
    path_value, unavailable_extraction, validate_chromatin_run_plan,
    validate_chromatin_bundle, validate_chromatin_population_seal,
)
from .native_chromatin_interaction_driver import (
    _regular, _directory, _writing, _immutable, _read_control, confined_file,
    stream_identity, file_identity, decode_json, merge_extractions,
)

PLAN_VERSION = "chromatin_interaction_result_worker_plan_v1"
RESULT_VERSION = "chromatin_interaction_result_worker_result_v1"
OUTPUTS = (("sheet", "sheet.json", "chromatin_interaction_sheet_v1"),
    ("components", "components.json", "chromatin_interaction_components_v1"),
    ("projection", "projection.json", "chromatin_interaction_projection_v1"),
    ("diagnostics", "diagnostics.json", "chromatin_interaction_result_diagnostics_v1"))


def validate_chromatin_result_worker_plan(value):
    value = validate_chromatin_record("WorkerPlan", value)
    directory = path_value(value["directory"], absolute=True)
    selector = value["selector"]
    require(selector["mode"] == value["mode"])
    retained = []
    if value["mode"] == "native_result":
        original = validate_chromatin_run_plan(value["original_plan"])
        request = original["requested_job"]["native_chromatin_interactions"]["request"]
        require(set(selector["population_keys"]) <= {p["population_key"] for p in request["populations"]})
        require(selector["saved_sheet_bundle"] is None)
        require([r["specification"] for r in value["files"]] == original["outputs"][:-1])
        if value["bundle"] is not None:
            require(value["driver_state"] == "sealed_bundle" and value["bundle"]["file"]["format"] == "chromatin_interaction_native_bundle_v1")
            retained.append(value["bundle"])
        for row in value["files"]:
            spec, capture = row["specification"], row["capture"]
            if row["declaration_source"] == "none":
                require(capture is None)
            else:
                require(capture is not None and all(capture["declared"][k] == spec[k] for k in ("relative_path", "format")))
                require(row["declaration_source"] != "bundle" or value["driver_state"] == "sealed_bundle")
                require(row["declaration_source"] != "population" or spec["role"] in TABLE_ROLES)
            if row["retained"] is not None:
                require(row["retained"]["file"]["format"] == spec["format"])
                require(capture is None or row["retained"]["file"] == capture["observed"])
                retained.append(row["retained"])
            if capture is not None:
                _validate_capture(capture)
        if value["driver_state"] == "not_started":
            require(value["bundle"] is None and all(r["retained"] is None and r["capture"] is None for r in value["files"]))
    else:
        bundle = value["sheet_bundle"]
        require(bundle["sheet"]["file"]["format"] == "chromatin_interaction_sheet_v1")
        require(selector["saved_sheet_bundle"] == {"sheet": bundle["sheet"]["file"], "tables": [r["file"] for r in bundle["tables"]]})
        retained = [bundle["sheet"], *bundle["tables"]]
    paths = {}
    for row in retained:
        path = path_value(row["path"], absolute=True)
        require(path != directory and directory not in path.parents and path not in directory.parents)
        content = {k: row["file"][k] for k in ("artifact_ref", "sha256", "size_bytes")}
        require(path not in paths or paths[path] == content)
        paths[path] = content
    return value


def _validate_capture(value):
    declaration, actual = value["declared"], value["observed"]
    equal = actual is not None and all(actual[k] == declaration[k] for k in ("sha256", "size_bytes", "format"))
    require((value["outcome"] == "verified" and declaration["state"] == "present" and equal and value["failure"] is None)
        or (value["outcome"] == "declared_absent" and declaration["state"] == "absent" and actual is None and value["failure"] is None)
        or (value["outcome"] == "unavailable" and declaration["state"] == "present" and actual is None and value["failure"] == "capture_file_unavailable")
        or (value["outcome"] == "digest_mismatch" and declaration["state"] == "present" and actual is not None and not equal and value["failure"] == "capture_file_digest_mismatch"))


def validate_chromatin_result_worker_result(value):
    value = validate_chromatin_record("WorkerResult", value)
    fixed = value["outputs"][:4]
    require(len(fixed) == 4)
    for row, (role, name, format) in zip(fixed, OUTPUTS):
        require(row["role"] == role and row["table_key"] is None and row["declaration"]["relative_path"] == name and row["declaration"]["format"] == format)
    tables = value["outputs"][4:]
    require(all(r["role"] == "table" and r["table_key"] is not None for r in tables))
    require(len({r["table_key"] for r in tables}) == len(tables))
    paths = [str(path_value(r["declaration"]["relative_path"], absolute=False)) for r in value["outputs"]]
    require(len(paths) == len(set(paths)))
    present = [r["declaration"]["state"] == "present" for r in fixed]
    require(present[3] and (not present[1] or present[0]) and (not present[2] or all(present[:2])))
    require(value["source_sheet_sha256"] == (fixed[0]["declaration"]["sha256"] if present[0] else None))
    require(value["state"] == ("produced" if all(present[:3]) else "partial" if any(present[:3]) else "unavailable"))
    return value


class _Unavailable(Exception):
    def __init__(self, problem):
        self.problem = problem
        super().__init__(problem["code"])


def _open(retained, stack, *, field_path, population_key=None):
    common = {"field_path": field_path, "population_key": population_key,
        "artifact_ref": retained["file"]["artifact_ref"] if retained else None}
    if retained is None:
        raise _Unavailable(failure("input_unavailable", "capture", **common))
    try:
        stream = stack.enter_context(_regular(retained["path"]))
    except (OSError, ValueError) as error:
        raise _Unavailable(failure("input_unavailable", "capture", **common)) from error
    if stream_identity(stream) != {k: retained["file"][k] for k in ("sha256", "size_bytes")}:
        raise _Unavailable(failure("artifact_digest_mismatch", "capture", **common))
    return stream


def _read_json(retained, stack, *, kind, field_path):
    stream = _open(retained, stack, field_path=field_path)
    try:
        value = decode_json(stream.read())
        return validate_chromatin_record(kind, value)
    except ValueError as error:
        raise _Unavailable(failure("original_attempt_mismatch", "capture", artifact_ref=retained["file"]["artifact_ref"], field_path=field_path)) from error


def _lost_table(extraction, role, problem):
    """Qualify this current retained view; original native seals stay unchanged."""
    population = extraction["populations"][0]
    extraction["failures"].append(problem)
    population["failures"].append(problem)
    if role == "weights":
        population["normalization"].update(availability="missing", vector_table_key=None,
            valid_bin_count=None, masked_bin_count=None, invalid_bin_count=None)
        return  # Raw matrix observations remain usable without a weight vector.
    population["extent"] = "partial"
    evidence = population["read_evidence"]
    if role == "bins":
        evidence["axes_extent"] = "unavailable"
    if role in ("contacts", "cell_states", "dense_values"):
        evidence["selected_records_extent"] = "unavailable"
    if role in ("bins", "contacts", "cell_states"):
        evidence["implicit_zero_semantics"] = "not_established"
        population["raw_cell_population"]["implicit_zero_directed_cells"] = None
        population["raw_cell_population"]["unavailable_directed_cells"] = None
    if role == "contacts" and evidence["symmetry"] == "square_reciprocal_verified":
        evidence["symmetry"] = "not_established"
        population["raw_cell_population"]["unique_unordered_cells"] = None


def _native(plan, stack, diagnostics):
    from .chromatin_interaction_inputs import parse_chromatin_elements, extract_chromatin_metadata
    original = plan["original_plan"]
    request = original["requested_job"]["native_chromatin_interactions"]["request"]
    rows = {r["specification"]["file_key"]: r for r in plan["files"]}
    bundle = None
    if plan["bundle"] is not None:
        try:
            bundle = validate_chromatin_bundle(_read_json(plan["bundle"], stack, kind="NativeBundle", field_path="/bundle"), plan=original)
        except _Unavailable as error:
            diagnostics["failures"].append(error.problem)
        except ValueError:
            diagnostics["failures"].append(failure("original_attempt_mismatch", "capture", field_path="/bundle"))
    if bundle is not None:
        for declared in bundle["outputs"]:
            row = rows[declared["specification"]["file_key"]]
            require(row["declaration_source"] == "bundle" and row["capture"] is not None and row["capture"]["declared"] == declared["declaration"])
        diagnostics["failures"].extend(bundle["failures"])
    extractions, descriptors, streams, attachments = [], [], {}, []
    for ordinal, population in enumerate(request["populations"]):
        key = population["population_key"]
        seal_row = rows[f"p{ordinal}.population_manifest"]
        seal, origin, manifest_file = None, "none", None
        try:
            seal = validate_chromatin_population_seal(_read_json(seal_row["retained"], stack, kind="PopulationSeal",
                field_path=f"/files/p{ordinal}.population_manifest"), plan=original, population=population)
        except _Unavailable as error:
            diagnostics["failures"].append(error.problem)
        except ValueError:
            diagnostics["failures"].append(failure("original_attempt_mismatch", "capture", population_key=key))
        if seal is not None:
            origin, manifest_file = "population", seal_row["retained"]["file"]
            header = seal["native"]
            extraction = {"format": request["contact"]["format"],
                "format_version": header["metadata"]["format_version"] if header["metadata"] else None,
                "native_metadata": header["metadata"], "chromosomes": header["chromosomes"],
                "populations": [deepcopy(seal["population"])], "table_drafts": [deepcopy(r["draft"]) for r in seal["tables"]],
                "failures": deepcopy(seal["failures"])}
            if bundle is not None and bundle["extraction"] is not None:
                require(extraction["populations"][0] == bundle["extraction"]["populations"][ordinal] and
                    all(extraction[k] == bundle["extraction"][k] for k in ("format", "format_version", "native_metadata", "chromosomes")))
                origin, manifest_file = "bundle", plan["bundle"]["file"]
        elif bundle is not None and bundle["extraction"] is not None:
            extracted = bundle["extraction"]
            extraction = {**{k: deepcopy(extracted[k]) for k in ("format", "format_version", "native_metadata", "chromosomes")},
                "populations": [deepcopy(extracted["populations"][ordinal])],
                "table_drafts": [deepcopy(d) for d in extracted["table_drafts"] if d["population_key"] == key],
                "failures": [f for f in extracted["failures"] if f["population_key"] in (None, key)]}
            origin, manifest_file = "bundle", plan["bundle"]["file"]
        else:
            extraction = unavailable_extraction(request, code="population_unavailable", populations=[population])
        for draft in extraction["table_drafts"]:
            row = rows[f"p{ordinal}.{draft['role']}"]
            if seal is not None:
                declared = next(r["declaration"] for r in seal["tables"] if r["draft"]["role"] == draft["role"])
                require(row["capture"] is not None and row["capture"]["declared"] == declared)
            descriptor = {**deepcopy(draft), "file": None}
            if draft["availability"] == "present":
                try:
                    require(row["capture"] is not None and row["capture"]["outcome"] == "verified")
                    stream = _open(row["retained"], stack, field_path=f"/files/p{ordinal}.{draft['role']}", population_key=key)
                except (ValueError, _Unavailable) as error:
                    problem = error.problem if isinstance(error, _Unavailable) else failure("artifact_digest_mismatch", "capture", population_key=key)
                    diagnostics["failures"].append(problem)
                    _lost_table(extraction, draft["role"], problem)
                    descriptor.update(availability="unavailable", absence_reason=problem["code"], encoding=None, shape=None,
                        dtype_descriptor=None, row_count=None, extent="unavailable")
                    draft.update({k: v for k, v in descriptor.items() if k != "file"})
                else:
                    descriptor["file"] = row["retained"]["file"]
                    streams[draft["table_key"]] = stream
            attachments.append((descriptor, row["retained"] if descriptor["file"] is not None else None,
                f"tables/p{ordinal}/{TABLE_NAMES[TABLE_ROLES.index(draft['role'])]}"))
            descriptors.append(descriptor)
        extractions.append(extraction)
        diagnostics["populations"].append({"population_key": key, "manifest_origin": origin, "manifest_file": manifest_file,
            "result_extent": extraction["populations"][0]["extent"], "failures": extraction["failures"]})
    extraction = merge_extractions(extractions, request)
    elements = bundle["elements"] if bundle is not None else None
    if request["elements"] is not None:
        try:
            stream = _open(rows["original_elements"]["retained"], stack, field_path="/files/original_elements")
            require({k: rows["original_elements"]["retained"]["file"][k] for k in ("sha256", "size_bytes", "format")} ==
                {k: request["elements"]["file"][k] for k in ("sha256", "size_bytes", "format")})
            parsed = parse_chromatin_elements(stream.read(), spec=request["elements"])
            require(elements is None or elements == parsed)
            elements = parsed
        except _Unavailable as error:
            diagnostics["failures"].append(error.problem)
    metadata = extract_chromatin_metadata(request=request, native=extraction, supplied=request["supplied_metadata"], elements=elements)
    return request, extraction, elements, metadata, descriptors, streams, attachments


def _copy_table(retained, target):
    if target.exists():
        require(file_identity(target) == {k: retained["file"][k] for k in ("sha256", "size_bytes")})
        return
    with _regular(retained["path"]) as source, _writing(target) as output:
        hasher, size = hashlib.sha256(), 0
        for block in iter(lambda: source.read(1024 * 1024), b""):
            output.write(block)
            hasher.update(block)
            size += len(block)
        require({"sha256": hasher.hexdigest(), "size_bytes": size} ==
            {k: retained["file"][k] for k in ("sha256", "size_bytes")}, "artifact_digest_mismatch")


def run_chromatin_result_worker(plan):
    from .chromatin_interaction_inputs import build_chromatin_sheet
    from .chromatin_interaction_tables import open_chromatin_contact_tables, read_chromatin_sheet_tables
    from .chromatin_interaction_calculations import calculate_chromatin_components
    from .chromatin_interaction_result_views import project_chromatin_result
    plan = validate_chromatin_result_worker_plan(plan)
    directory = _directory(plan["directory"])
    directory.mkdir(parents=True, exist_ok=True)
    diagnostics = {"version": "chromatin_interaction_result_diagnostics_v1", "mode": plan["mode"],
        "populations": [], "failures": deepcopy(plan.get("failures", []))}
    values, sheet, attachments, source_sha = {}, None, [], None
    with ExitStack() as stack:
        try:
            if plan["mode"] == "native_result":
                request, extraction, elements, metadata, descriptors, streams, attachments = _native(plan, stack, diagnostics)
                tables = stack.enter_context(open_chromatin_contact_tables(descriptors, streams=streams))
                sheet = build_chromatin_sheet(request=request, contacts=extraction, elements=elements,
                    metadata=metadata, tables=descriptors, table_views=tables)
            else:
                saved = plan["sheet_bundle"]
                sheet = _read_json(saved["sheet"], stack, kind="ContactSheet", field_path="/sheet_bundle/sheet")
                require(digest(sheet) == saved["sheet"]["file"]["sha256"])
                identities = [d["file"] for d in sheet["data_tables"] if d["file"] is not None]
                require([r["file"] for r in saved["tables"]] == identities)
                streams = {}
                positions = {p["population_key"]: i for i, p in enumerate(sheet["request"]["populations"])}
                selected = iter(saved["tables"])
                unavailable = []
                for descriptor in sheet["data_tables"]:
                    retained = next(selected) if descriptor["file"] is not None else None
                    if retained is not None:
                        try:
                            streams[descriptor["table_key"]] = _open(retained, stack,
                                field_path="/sheet_bundle/tables", population_key=descriptor["population_key"])
                        except _Unavailable as error:
                            unavailable.append(error.problem)
                            retained = None
                    attachments.append((descriptor, retained, f"tables/p{positions[descriptor['population_key']]}/{TABLE_NAMES[TABLE_ROLES.index(descriptor['role'])]}"))
                if unavailable:
                    diagnostics["failures"].extend(unavailable)
                    raise _Unavailable(unavailable[0])
                tables = stack.enter_context(read_chromatin_sheet_tables(sheet, streams=streams))
            source_sha = digest(sheet)
            values["sheet"] = sheet
            components = calculate_chromatin_components(sheet, tables=tables, parameters=plan["selector"]["parameters"])
            require(components["source_sheet_sha256"] == source_sha and components["parameters"] == plan["selector"]["parameters"])
            values["components"] = validate_chromatin_record("ChromatinComponents", components)
            projection = project_chromatin_result(sheet, components, selector=plan["selector"])
            require(projection["source_sheet_sha256"] == source_sha and projection["parameters"] == plan["selector"]["parameters"])
            values["projection"] = validate_chromatin_record("RequestedProjection", projection)
        except _Unavailable as error:
            diagnostics["failures"].append(error.problem)
        except ValueError as error:
            if not isinstance(error, ChromatinValidationError) and not str(error).startswith(("chromatin", "original_attempt", "artifact_", "input_", "normalization_")):
                raise
            diagnostics["failures"].append(failure("requested_field_unavailable", "calculation", field_path="/components", requirement="requested_selected_field"))
        if sheet is not None and "sheet" not in values:
            # Preserve an authentic saved sheet even when an attachment is lost.
            values["sheet"], source_sha = sheet, digest(sheet)
        table_outputs = []
        for descriptor, retained, relative in attachments:
            target = confined_file(directory, relative)
            if retained is not None:
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    _copy_table(retained, target)
                except (OSError, ValueError) as error:
                    code = "input_unavailable" if isinstance(error, OSError) else "artifact_digest_mismatch"
                    diagnostics["failures"].append(failure(code, "capture",
                        population_key=descriptor["population_key"], artifact_ref=retained["file"]["artifact_ref"],
                        field_path="/outputs/" + descriptor["table_key"]))
                    retained = None
            table_outputs.append({"role": "table", "table_key": descriptor["table_key"], "declaration": {
                "relative_path": relative, "format": "chromatin_contact_tables_v1:" + descriptor["role"],
                "state": "present" if retained is not None else "absent",
                **(file_identity(target) if retained is not None else {"sha256": None, "size_bytes": None})}})
        diagnostics["failures"] = unique_failures(diagnostics["failures"], *(r["failures"] for r in diagnostics["populations"]))
        values["diagnostics"] = validate_chromatin_record("Diagnostics", diagnostics)
        outputs = []
        for role, name, format in OUTPUTS:
            if role in values:
                _immutable(confined_file(directory, name), values[role])
            path = confined_file(directory, name)
            outputs.append({"role": role, "table_key": None, "declaration": {"relative_path": name, "format": format,
                "state": "present" if role in values else "absent", **(file_identity(path) if role in values else {"sha256": None, "size_bytes": None})}})
        outputs.extend(table_outputs)
    count = sum(role in values for role in ("sheet", "components", "projection"))
    result = validate_chromatin_result_worker_result({"version": RESULT_VERSION, "mode": plan["mode"],
        "state": "produced" if count == 3 else "partial" if count else "unavailable", "source_sheet_sha256": source_sha,
        "parameters": plan["selector"]["parameters"], "outputs": outputs, "failures": diagnostics["failures"]})
    _immutable(directory / "worker-result.json", result)
    return result


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    require(len(args) == 1)
    run_chromatin_result_worker(_read_control(Path(args[0])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
