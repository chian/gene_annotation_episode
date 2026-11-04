"""Closed pure contracts for retained GenomeComparison provider construction.

These validators check saved shapes, copies, identities and source relationships.
They never parse input bytes, reconstruct joins/sheets, calculate scores, project
facts, or establish custody. The execution host authenticates retained artifacts.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

from .bvbrc_appservice_contracts import ContractValidationError, validate_contract
from .bvbrc_proteome_data_contracts import ProteomeDataError, _plain, _Validator, validate_proteome_data
from .bvbrc_proteome_native_contracts import NativeValidationError, validate_native_projection
from .bvbrc_proteome_sheet_contracts import validate_proteome_sheet_data


_FAILURES = (
    ("bundle_invalid application_mismatch original_task_conflict", "original_task", None, "association"),
    ("parameters_invalid requested_form_invalid source_contract_incompatible", "parser_binding", "proteome_native_projection", "publication"),
    ("document_missing primary_document_missing artifact_bytes_missing", "output_bytes", "proteome_native_projection", "association"),
    ("document_ambiguous primary_document_invalid artifact_format_incompatible nonzero_range_unsupported", "parser_binding", "proteome_native_projection", "association"),
    ("artifact_digest_mismatch artifact_binding_conflict", "byte_version_evidence", "proteome_native_projection", "association"),
    ("supplied_data_missing supplied_data_ambiguous supplied_data_invalid", "scientific_metadata", "proteome_supplied_data", "association"),
    ("input_bytes_missing input_binding_missing input_binding_ambiguous", "input_bytes", "proteome_supplied_input", "association"),
    ("parameter_source_unbound parameter_source_conflict", "original_task", "proteome_original_input_index", "association"),
    ("completeness_evidence_unverified parsed_construction_evidence_unverified", "byte_version_evidence", "proteome_supplied_input", "association"),
    ("supplied_source_conflict source_field_unbound", "scientific_metadata", "proteome_supplied_input", "association"),
    ("deployment_evidence_unverified", "byte_version_evidence", "proteome_native_projection", "association"),
    ("parsed_result_invalid parsed_result_mismatch supplied_reader_incompatible", "parser_binding", "proteome_supplied_input", "native_decode"),
    ("projection_parameters_invalid projection_requested_form_invalid", "parser_binding", "proteome_requested_projection", "publication"),
    ("saved_sheet_invalid saved_components_invalid saved_identity_conflict saved_projection_conflict", "parser_binding", "proteome_requested_projection", "return"),
    ("requested_target_missing requested_target_ambiguous requested_value_unavailable requested_population_unavailable requested_reference_unresolved", "scientific_metadata", "proteome_requested_projection", "publication"),
)
BINDING_DETAILS = {"proteome_" + name: (kind, role, phase)
                   for names, kind, role, phase in _FAILURES for name in names.split()}
BINDING_CODES = frozenset(BINDING_DETAILS)
BINDING_INPUT_KINDS = {code: details[0] for code, details in BINDING_DETAILS.items()}
PURE_REQUIRED_INPUT_KINDS = {
    "complete_artifact_bytes": "output_bytes", "exact_input_fasta": "input_bytes",
    "identifier_mapping": "scientific_metadata", "complete_input_membership": "scientific_metadata",
    "producer_manifest": "task_manifest", "directional_blast_report": "output_bytes",
    "feature_metadata": "scientific_metadata", "genome_metadata": "scientific_metadata",
    "coordinate_convention": "scientific_metadata", "native_producer_version": "byte_version_evidence",
    "requested_calculation_field": "parser_binding", "complete_bytes": "input_bytes",
    "original_parameters": "original_task", "exact_executed_fasta": "input_bytes",
    "execution_input_witness": "task_manifest", "complete_membership": "scientific_metadata",
    "occurrence_mapping": "byte_version_evidence", "feature_sequence": "scientific_metadata",
    "representation_correspondence": "scientific_metadata", "directional_report": "output_bytes",
    "producer_execution_facts": "task_manifest", "valid_parameters": "parser_binding",
    "valid_saved_sheet": "parser_binding",
}


class ProteomeBundleError(ValueError):
    """Finite public failure identity and exact JSON pointer, without source prose."""

    def __init__(self, code: str, path: str = ""):
        if code not in BINDING_CODES:
            raise ValueError("unknown_proteome_bundle_failure_code")
        self.code, self.path = code, path
        super().__init__(code)


def _require(condition, code, path=""):
    if not condition:
        raise ProteomeBundleError(code if code.startswith("proteome_") else "proteome_" + code, path)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _pointer(path, key):
    return path + "/" + str(key).replace("~", "~0").replace("/", "~1")


def _error_path(error):
    if hasattr(error, "path"):
        return error.path
    return error.diagnostics[0]["path"] if hasattr(error, "diagnostics") else ""


_DOCUMENT = json.loads(Path(__file__).with_name("bvbrc_proteome_bundle_schemas.json").read_text(encoding="utf-8"))
_PURE_CODES = frozenset(_DOCUMENT["$defs"]["SheetPReason"]["enum"]) | frozenset(
    _DOCUMENT["$defs"]["NativeDiagnostic"]["properties"]["code"]["enum"])


@lru_cache(maxsize=None)
def _schema(name):
    definitions, reachable = _DOCUMENT["$defs"], set()
    _require(type(name) is str and name in definitions, "parameters_invalid")
    def visit(node):
        if type(node) is dict:
            if "$ref" in node:
                key = node["$ref"][8:]
                if not node["$ref"].startswith("#/$defs/") or key not in definitions:
                    raise RuntimeError("invalid_packaged_proteome_bundle_reference")
                if key not in reachable:
                    reachable.add(key)
                    visit(definitions[key])
            for child in node.values():
                visit(child)
        elif type(node) is list:
            for child in node:
                visit(child)
    root = {"$schema": _DOCUMENT["$schema"], "$ref": "#/$defs/" + name}
    visit(root)
    root["$defs"] = {key: definitions[key] for key in definitions if key in reachable}
    return root


def bundle_schema(name):
    """Return a detached wrapper schema with exact namespaced dependency shapes."""
    return deepcopy(_schema(name))


def parameters_schema():
    return bundle_schema("ProviderParameters")


@lru_cache(maxsize=None)
def _validator(name):
    return _Validator(_schema(name))


def validate_shape(name, value, *, code="parameters_invalid", path=""):
    try:
        _plain(value)
        canonical(value).encode("utf-8")
        error = next(_validator(name).iter_errors(value), None)
        if error is not None:
            location = path
            for token in error.absolute_path:
                location = _pointer(location, token)
            raise ProteomeBundleError("proteome_" + code, location)
    except (ProteomeDataError, RecursionError, UnicodeError, ValueError) as error:
        if isinstance(error, ProteomeBundleError):
            raise
        raise ProteomeBundleError("proteome_" + code, path + getattr(error, "path", "")) from error
    return deepcopy(value)


def _checked(function, name, value, code, path):
    try:
        return function(name, value)
    except (ContractValidationError, ProteomeDataError, NativeValidationError) as error:
        raise ProteomeBundleError("proteome_" + code, path + _error_path(error)) from error


def validate_parameters(value: dict) -> dict:
    result = validate_shape("ProviderParameters", value)
    ids = [row["document_id"] for row in result["native_documents"]]
    _require(len(ids) == len(set(ids)), "parameters_invalid", "/native_documents")
    _checked(validate_proteome_sheet_data, "NativeCalculationParameters", result["calculation_parameters"],
             "parameters_invalid", "/calculation_parameters")
    for i, row in enumerate(result["native_documents"]):
        _checked(validate_contract, "DeclaredFormat", row["declared_format"], "parameters_invalid",
                 f"/native_documents/{i}/declared_format")
    if result["supplied_data_evidence"] is not None:
        _checked(validate_contract, "SourceEvidence", result["supplied_data_evidence"], "parameters_invalid", "/supplied_data_evidence")
    return result


def validate_supplied_data(value: dict) -> dict:
    """Validate the selected closed operand description, retaining no authority."""
    result = validate_shape("SuppliedData", value, code="supplied_data_invalid")
    inventories, snapshots = set(), set()
    for name in ("inventories", "feature_snapshots", "genome_snapshots", "sequence_snapshots"):
        key = "inventory_key" if name == "inventories" else "snapshot_key"
        seen = inventories if name == "inventories" else snapshots
        for index, row in enumerate(result[name]):
            _require(row[key] not in seen, "supplied_data_ambiguous", f"/{name}/{index}/{key}")
            seen.add(row[key])
    return result


_RESULTS = {
    "native_document": ("native_results", "NativeProjectionResult"),
    "original_input_index": ("input_index_result", "InputIndexResult"),
    "inventory": ("inventory_results", "ProteinInventoryResult"),
    "feature_snapshot": ("feature_results", "FeatureSnapshotResult"),
    "genome_snapshot": ("genome_results", "GenomeSnapshotResult"),
    "sequence_snapshot": ("sequence_results", "FeatureSequenceSnapshotResult"),
}
_SELECTIONS = {"inventory": "inventories", "feature_snapshot": "feature_snapshots",
               "genome_snapshot": "genome_snapshots", "sequence_snapshot": "sequence_snapshots"}
_SUBMITTED_PARAMETER_POINTER = "/prepared/native_operands/call/rpc_request/params/1"


def _selected_data(saved):
    evidence = saved["parameters"]["supplied_data_evidence"]
    if evidence is None:
        return None
    rows = [row for row in saved["supplied_values"] if row["evidence"] == evidence]
    if len(rows) != 1:
        return None
    try:
        return validate_supplied_data(rows[0]["value"])
    except ProteomeBundleError:
        return None


def _at(value, pointer):
    current = value
    for token in pointer.lstrip("/").split("/") if pointer else []:
        token = token.replace("~1", "/").replace("~0", "~")
        if type(current) is dict and token in current:
            current = current[token]
        elif type(current) is list and re.fullmatch(r"0|[1-9][0-9]*", token) and int(token) < len(current):
            current = current[int(token)]
        else:
            raise ProteomeBundleError("proteome_saved_identity_conflict", pointer)
    return current


def _index_task(saved):
    result = saved["input_index_result"]
    if result is None or result["value"] is None:
        return
    index, task = result["value"], saved["original_task"]
    source = index["parameter_source"]
    if source["kind"] == "effective":
        effective = task["effective_parameters"]
        _require(effective is not None, "saved_identity_conflict", "/original_task/effective_parameters")
        evidence = effective["evidence"]
        field = source["source_field"]
        _require((field["source_ref"], field["sha256"], field["pointer"]) ==
                 (evidence["content"]["source_ref"], evidence["content"]["sha256"], evidence["pointer"]),
                 "saved_identity_conflict", "/input_index_result/value/parameter_source")
        parameters = effective["value"]
    else:
        _require(source["source_field"]["source_ref"] == task["submission_source_ref"] and
                 source["source_field"]["pointer"] == _SUBMITTED_PARAMETER_POINTER,
                 "saved_identity_conflict", "/input_index_result/value/parameter_source")
        parameters = task["submitted_parameters"]
    _require(parameters.get("reference_genome_index") == index["reference_original_index"], "saved_identity_conflict", "/input_index_result/value/reference_original_index")
    for entry in index["inputs"]:
        _require(canonical(_at(parameters, entry["parameter_pointer"])) == canonical(entry["value"]), "saved_identity_conflict", "/input_index_result/value/inputs")
    for snapshot in index["run_parameter_snapshots"]:
        original = task["submitted_parameters"] if snapshot["kind"] == "submitted" else task["effective_parameters"]["value"] if task["effective_parameters"] is not None else None
        _require(original is not None, "saved_identity_conflict", "/input_index_result/value/run_parameter_snapshots")
        if snapshot["kind"] == "submitted":
            field = snapshot["source_field"]
            _require(field["source_ref"] == task["submission_source_ref"] and
                     field["pointer"] == _SUBMITTED_PARAMETER_POINTER,
                     "saved_identity_conflict", "/input_index_result/value/run_parameter_snapshots")
        for name in ("min_ident", "min_seq_cov", "min_positives", "max_e_val"):
            cell = snapshot[name]
            if cell["presence"] == "value":
                _require(name in original and canonical(original[name]) == canonical(cell["value"]), "saved_identity_conflict", "/input_index_result/value/run_parameter_snapshots")
            elif cell["presence"] == "omitted":
                _require(name not in original, "saved_identity_conflict", "/input_index_result/value/run_parameter_snapshots")
            elif cell["presence"] == "explicit_null":
                _require(name in original and original[name] is None, "saved_identity_conflict", "/input_index_result/value/run_parameter_snapshots")


def _validate_result(name, result, path):
    if name == "NativeProjectionResult":
        validate_shape("NativeNativeProjectionResult", result, code="saved_sheet_invalid", path=path)
        _require((result["status"] == "invalid") == (result["value"] is None), "saved_sheet_invalid", path)
        _require(result["status"] != "ok" or not any(d["severity"] == "error" for d in result["diagnostics"]), "saved_sheet_invalid", path)
        if result["value"] is not None:
            try:
                validate_native_projection(result["value"])
            except NativeValidationError as error:
                raise ProteomeBundleError("proteome_saved_sheet_invalid", path + "/value" + error.path) from error
    else:
        _checked(validate_proteome_data, name, result, "saved_sheet_invalid", path)


def _validate_resolution(saved, supplied):
    outcomes = saved["input_resolution"]
    seen, accounted = set(), {name: set() for name, _ in _RESULTS.values()}
    for i, row in enumerate(outcomes):
        path = f"/input_resolution/{i}"
        kind, selection_index = row["selector_kind"], row["selection_index"]
        _require((kind, selection_index) not in seen, "saved_identity_conflict", path)
        seen.add((kind, selection_index))
        _require(len(row["requirement_ids"]) == len(set(row["requirement_ids"])), "saved_identity_conflict", path)
        _require(set(row["requirement_ids"]) <= {r["requirement_id"] for r in saved["requirements"]}, "saved_sheet_invalid", path)
        if kind == "native_document":
            choices = saved["parameters"]["native_documents"]
        elif kind == "original_input_index":
            choices = [supplied["original_input_index"]] if supplied is not None and supplied["original_input_index"] is not None else []
        else:
            choices = supplied[_SELECTIONS[kind]] if supplied is not None else []
        _require(selection_index < len(choices), "saved_sheet_invalid", path)
        choice = choices[selection_index]
        name, _ = _RESULTS[kind]
        index = row["result_index"]
        if index is None:
            _require(row["state"] not in {"resolved", "partial"}, "saved_sheet_invalid", path)
            _require(bool(row["requirement_ids"]), "saved_sheet_invalid", path + "/requirement_ids")
            continue
        results = ([saved[name]] if saved[name] is not None else []) if kind == "original_input_index" else saved[name]
        _require(index < len(results) and index not in accounted[name], "saved_identity_conflict", path)
        accounted[name].add(index)
        result, value = results[index], results[index]["value"]
        _require(row["state"] == ("invalid" if value is None else "resolved" if result["status"] == "ok" else "partial"), "saved_sheet_invalid", path)
        if value is None:
            continue
        if kind == "native_document":
            binding = value["source"]["content"]
            _require(choice["declared_format"]["format"] == value["format"] and
                     choice["source_contract"] == value["source_contract"], "saved_identity_conflict", path)
            if "source_ref" in choice:
                _require(choice["source_ref"] == binding["source_ref"] and choice["raw_artifact_ref"] == binding["artifact_ref"],
                         "saved_identity_conflict", path)
            _require(choice["declared_format"]["version"] is None and choice["declared_format"]["mode"] is None and
                     value["source_contract"]["deployment_match"] == "unobserved", "saved_identity_conflict", path)
        elif kind == "original_input_index":
            _require(choice["mode"] == "construct" and value["parameter_source"] == choice["parameter_source"], "saved_identity_conflict", path)
            if value["parameter_source"]["kind"] == "submitted":
                field, content = value["parameter_source"]["source_field"], row["content"]
                _require(content is not None and content["artifact_field"] == "request_ref" and
                         content["artifact_ref"] == "artifact_" + content["sha256"] and
                         (content["source_ref"], content["sha256"]) == (field["source_ref"], field["sha256"]),
                         "saved_identity_conflict", path + "/content")
            continue
        else:
            key = "inventory_key" if kind == "inventory" else "snapshot_key"
            _require(choice["mode"] == "raw" and value[key] == choice[key] and value["format"] == choice["declared_format"], "saved_identity_conflict", path)
            binding = value["source"]["content"]
            source = choice["source"]
            if source["kind"] == "supplied_snapshot":
                _require(binding == source["content"] and value["source"]["body_complete"] is True and value["source"]["object_complete"] == "unknown", "saved_identity_conflict", path)
            elif source["kind"] == "acquired_artifact":
                _require((source["source_ref"], source["raw_artifact_ref"]) == (binding["source_ref"], binding["artifact_ref"]), "saved_identity_conflict", path)
            else:
                _require(value["source"]["body_complete"] is True and value["source"]["object_complete"] == "yes", "saved_identity_conflict", path)
        _require(row["content"] == binding, "saved_identity_conflict", path + "/content")
    for kind, (name, _) in _RESULTS.items():
        results = ([saved[name]] if saved[name] is not None else []) if kind == "original_input_index" else saved[name]
        _require(accounted[name] == set(range(len(results))), "saved_sheet_invalid", "/" + name)
    _require({index for kind, index in seen if kind == "native_document"} == set(range(len(saved["parameters"]["native_documents"]))), "saved_sheet_invalid", "/input_resolution")


def validate_provider_sheet(value: dict) -> dict:
    saved = validate_shape("ProviderSheet", value, code="saved_sheet_invalid")
    parameters = validate_parameters(saved["parameters"])
    _require(saved["analysis_id"] == parameters["analysis_id"], "saved_identity_conflict", "/analysis_id")
    task = _checked(validate_contract, "OriginalTask", saved["original_task"], "saved_sheet_invalid", "/original_task")
    _require(task["required_application_id"] == task["native_application_id"] == "GenomeComparison", "saved_identity_conflict", "/original_task")
    from .bvbrc_proteome_fact_contracts import validate_requested_form
    try:
        validate_requested_form(saved["requested_form"], binding_codes=BINDING_CODES, binding_input_kinds=BINDING_INPUT_KINDS.values())
    except ValueError as error:
        raise ProteomeBundleError("proteome_saved_sheet_invalid", "/requested_form" + getattr(error, "path", "")) from error
    for index, row in enumerate(saved["supplied_values"]):
        _checked(validate_contract, "SourceEvidence", row["evidence"], "saved_sheet_invalid", f"/supplied_values/{index}/evidence")
    for kind, (name, contract) in _RESULTS.items():
        results = ([saved[name]] if saved[name] is not None else []) if kind == "original_input_index" else saved[name]
        for i, result in enumerate(results):
            _validate_result(contract, result, "/" + name + ("" if kind == "original_input_index" else "/" + str(i)))
    for name, contract in (("joins_result", "NativeJoinsResult"), ("native_sheet_result", "NativeSheetResult")):
        if saved[name] is not None:
            _checked(validate_proteome_sheet_data, contract, saved[name], "saved_sheet_invalid", "/" + name)
    req_ids = [row["requirement_id"] for row in saved["requirements"]]
    _require(len(req_ids) == len(set(req_ids)), "saved_identity_conflict", "/requirements")
    for name, contract in (("requirements", "AcquisitionRequirement"), ("diagnostics", "Diagnostic")):
        for i, row in enumerate(saved[name]):
            _checked(validate_contract, contract, row, "saved_sheet_invalid", f"/{name}/{i}")
            code = row["reason_code" if name == "requirements" else "code"]
            _require(code in BINDING_CODES or code in _PURE_CODES, "saved_sheet_invalid", f"/{name}/{i}")
            if code in BINDING_CODES:
                kind, role, phase = BINDING_DETAILS[code]
                _require((row["kind"] == kind and row["role"] == role) if name == "requirements" else row["phase"] == phase,
                         "saved_sheet_invalid", f"/{name}/{i}")
    supplied = _selected_data(saved)
    _validate_resolution(saved, supplied)
    _index_task(saved)
    native = saved["native_sheet_result"]
    if native is not None and native["value"] is not None:
        sheet_value = native["value"]
        choices = [i for i, row in enumerate(parameters["native_documents"]) if row["document_id"] == parameters["primary_document_id"]]
        resolved = [row for row in saved["input_resolution"] if row["selector_kind"] == "native_document" and
                    row["selection_index"] in choices and row["content"] is not None and row["result_index"] is not None]
        _require(len(choices) == len(resolved) == 1 and
                 sheet_value["primary_source_ref"] == resolved[0]["content"]["source_ref"],
                 "saved_identity_conflict", "/native_sheet_result/value/primary_source_ref")
        _require(canonical(sheet_value["native_results"]) == canonical(saved["native_results"]), "saved_sheet_invalid", "/native_sheet_result/value/native_results")
        for envelope, field in (("input_index_result", "input_index"), ("joins_result", "joins")):
            expected = saved[envelope]["value"] if saved[envelope] is not None else None
            _require(canonical(sheet_value[field]) == canonical(expected), "saved_sheet_invalid", "/native_sheet_result/value/" + field)
        for envelopes, field in (("inventory_results", "inventories"), ("feature_results", "feature_snapshots"),
                                 ("genome_results", "genome_snapshots"), ("sequence_results", "sequence_snapshots")):
            expected = [result["value"] for result in saved[envelopes] if result["value"] is not None]
            _require(canonical(sheet_value[field]) == canonical(expected), "saved_sheet_invalid", "/native_sheet_result/value/" + field)
        expected_links = supplied["representation_links"] if supplied is not None else []
        _require(canonical([item["link"] for item in sheet_value["representation_comparisons"]]) == canonical(expected_links) and sheet_value["directional_attachment"] is None, "saved_sheet_invalid", "/native_sheet_result/value/representation_comparisons")
    if saved["joins_result"] is not None and saved["joins_result"]["value"] is not None:
        joined = saved["joins_result"]["value"]
        for source, target in (("execution_links", "execution_links"), ("native_links", "requested_native_links"), ("metadata_links", "requested_metadata_links")):
            expected = supplied[source] if supplied is not None else []
            _require(canonical(joined[target]) == canonical(expected), "saved_sheet_invalid", "/joins_result/value/" + target)
    return saved


def validate_bundle_binding(saved: dict, bundle: dict | None) -> None:
    """Check saved document membership against an authenticated supplied bundle.

    This checks identities and retained transfer facts only. It neither reads
    bytes nor reruns native parsing or scientific calculation.
    """
    choices = saved["parameters"]["native_documents"]
    if bundle is None:
        _require(not any("requirement_id" in choice for choice in choices), "saved_identity_conflict", "/bundle")
        return
    actual = _checked(validate_contract, "ArtifactBundle", bundle, "saved_identity_conflict", "/bundle")
    _require(digest(actual) == saved["bundle_sha256"] and
             canonical(actual["original_task"]) == canonical(saved["original_task"]), "saved_identity_conflict", "/bundle")
    for index, row in enumerate(saved["input_resolution"]):
        if row["selector_kind"] != "native_document":
            continue
        choice = choices[row["selection_index"]]
        if "requirement_id" not in choice:
            continue
        path = "/input_resolution/" + str(index)
        members = [member for member in actual["artifacts"] if choice["requirement_id"] in member.get("requirement_ids", [])]
        # A missing or ambiguous selected document supplies no parsed result.
        if len(members) != 1:
            _require(row["content"] is None and row["result_index"] is None, "saved_identity_conflict", path)
            continue
        member = members[0]
        content = dict(source_ref=member["source_ref"], artifact_field="artifact_ref",
                       artifact_ref=member["raw_artifact_ref"], sha256=member["sha256"], byte_count=member["byte_count"])
        # Duplicate actual selections and incompatible parser declarations can
        # fail before content is resolved; they cannot carry a parsed result.
        if row["content"] is None:
            _require(row["result_index"] is None and row["state"] in {"invalid", "incompatible", "unverified"},
                     "saved_identity_conflict", path)
            continue
        _require(row["content"] == content, "saved_identity_conflict", path + "/content")
        if row["result_index"] is None:
            continue
        result = saved["native_results"][row["result_index"]]["value"]
        _require(member["role"] == choice["role"] and member["declared_format"] == choice["declared_format"],
                 "saved_identity_conflict", path)
        if result is not None:
            transfer, observed = member["transfer"], member["transfer"]["observed_range"]
            _require(not (observed is not None and observed["start"] != 0 or
                observed is None and transfer["object_complete"] != "yes" and
                transfer["requested_range"] is not None and transfer["requested_range"][0] != 0),
                "saved_identity_conflict", path)
            source = result["source"]
            _require(source["content"] == content and
                     source["body_complete"] == member["transfer"]["body_complete"] and
                     source["object_complete"] == member["transfer"]["object_complete"], "saved_identity_conflict", path)


__all__ = ["ProteomeBundleError", "BINDING_CODES", "BINDING_INPUT_KINDS", "PURE_REQUIRED_INPUT_KINDS",
           "validate_parameters", "validate_provider_sheet", "validate_bundle_binding", "validate_supplied_data", "parameters_schema", "bundle_schema"]
