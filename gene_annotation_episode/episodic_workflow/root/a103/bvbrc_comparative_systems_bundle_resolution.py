"""Resolve explicit supplied bindings and call the real N, D and C functions.

I authenticates task/source custody and receiver possession. This pure provider
checks equality and byte identities; it never searches Store or acquires data.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_comparative_systems_handoff_contracts import canonical_sha256, validate_shape
from .bvbrc_comparative_systems_native import parse_comparative_systems_document
from .bvbrc_comparative_systems_sheet import build_comparative_systems_sheet
from .bvbrc_comparative_systems_sheet_contracts import validate_sheet
from .bvbrc_comparative_systems_data_inputs import extract_comparative_systems_data_inputs
from .bvbrc_comparative_systems_data_contracts import validate_supplied_record_sets
from .bvbrc_comparative_systems_calculators import calculate_comparative_systems_components
from .bvbrc_comparative_systems_bundle_projection import assemble_projection
from .bvbrc_comparative_systems_fact_contracts import require, validate_requested_form
from .bvbrc_comparative_systems_bundle_contracts import (
    at, checked_bytes, issue, json_value, original_request, requirement, unique,
    unique_index, validate_parameters,
)


def _content_bindings(bundle):
    return unique([*bundle.get("supplied_contents", []),
                   *(row["content"] for row in bundle["supplied_scientific_metadata"])])


def _matches(member, selection):
    return (selection["requirement_id"] in member.get("requirement_ids", []) if selection["kind"] == "requirement"
            else member["source_ref"] == selection["source_ref"] and member["raw_artifact_ref"] == selection["raw_artifact_ref"])


def _producers(bundle, raw, supplied_values, wrappers, parameters):
    require(type(wrappers) is tuple, "qualified_producer_tuple_required")
    qualified = [validate_shape("QualifiedProducerEvidenceV1", item) for item in wrappers]
    by_id = unique_index([item["evidence"] for item in qualified], "evidence_id")
    selections = parameters["producer_evidence_selections"]
    require(set(by_id) == {item["evidence_id"] for item in selections}, "producer_evidence_selection_mismatch")
    evidence, qualifications = [], {}
    for selection in selections:
        identifier = selection["evidence_id"]
        wrapper = next(item for item in qualified if item["evidence"]["evidence_id"] == identifier)
        value, qualification = wrapper["evidence"], wrapper["qualification"]
        bindings = [item for item in bundle["supplied_scientific_metadata"]
                    if item["content"]["source_ref"] == selection["source_ref"]
                    and item["content"]["artifact_ref"] == selection["raw_artifact_ref"]
                    and item["pointer"] == selection["record_path"]]
        require(len(bindings) == 1, "producer_source_binding_mismatch")
        binding = bindings[0]
        values = [item["value"] for item in supplied_values
                  if type(item) is dict and set(item) == {"evidence", "value"} and item["evidence"] == binding]
        require(len(values) == 1 and canonical_sha256(values[0]) == canonical_sha256(value),
                "producer_supplied_value_mismatch")
        content = checked_bytes(raw.get(selection["raw_artifact_ref"]), binding["content"])
        require(canonical_sha256(at(json_value(content), selection["record_path"])) == canonical_sha256(value),
                "producer_evidence_bytes_mismatch")
        require(selection["source_ref"] in qualification["evidence_source_refs"], "producer_evidence_source_mismatch")
        require(all(ref in {item["source_ref"] for item in _content_bindings(bundle)}
                    for ref in qualification["evidence_source_refs"]), "producer_evidence_source_unselected")
        identity = {"source_only": "source_examined", "source_execution": "source_executed",
                    "native_task_bound": "deployed_attested", "unknown": "unknown"}[qualification["basis"]]
        require(value["identity_kind"] == identity, "producer_evidence_basis_mismatch")
        task_ref = bundle["original_task"]["submission_receipt_ref"]
        require(qualification["original_task_ref"] in {None, task_ref}, "original_task_mismatch")
        if qualification["basis"] in {"source_execution", "native_task_bound"}:
            require(qualification["original_task_ref"] == task_ref, "producer_execution_task_unbound")
        if qualification["basis"] in {"source_only", "unknown"}:
            require(value["runtime_version"] is None and value["dependency_version"] is None
                    and value["reference_release"] is None, "producer_unexecuted_version_claim")
        evidence.append(value)
        qualifications[identifier] = qualification
    return tuple(evidence), qualifications


def _documents(bundle, raw, parameters, evidence, qualifications):
    native, requirements, diagnostics = [], [], []
    for selection in parameters["document_selection"]["documents"]:
        matches = [member for member in bundle["artifacts"] if _matches(member, selection["input"])]
        args = dict(document_id=selection["document_id"], role=selection["role"],
                    refs=[member["source_ref"] for member in matches])
        code = None
        if len(matches) != 1:
            code = "ambiguous_document_selection" if matches else "missing_document_selection"
        else:
            member = matches[0]
            association = member["task_association"]
            if (member["role"] != selection["role"] or member["declared_format"]["format"] != selection["format_profile"]):
                code = "format_incompatible"
            elif (association["task_id"] != bundle["original_task"]["task_id"]
                  or association["kind"] not in {"task_result_manifest", "task_info_object"}):
                code = "original_task_mismatch"
            elif member["raw_artifact_ref"] not in raw:
                code = "missing_document_selection"
            else:
                try:
                    checked_bytes(raw[member["raw_artifact_ref"]], member)
                except ValueError:
                    code = "byte_identity_mismatch"
        if code:
            requirements.append(requirement(code, **args))
            diagnostics.append(issue(code, phase="association", **args))
            continue
        producer = qualifications.get(selection["producer_evidence_id"])
        basis = "source_executed_synthetic" if producer and producer["basis"] == "source_execution" else "service_artifact"
        document = {key: deepcopy(selection[key]) for key in ("document_id", "role", "format_profile", "producer_evidence_id")}
        document.update({key: member[key] for key in ("source_ref", "raw_artifact_ref", "byte_count", "sha256")})
        document.update(transfer_body_complete="complete" if member["transfer"]["body_complete"] else "partial",
                        object_complete={"yes": "complete", "no": "partial", "unknown": "unknown"}[member["transfer"]["object_complete"]],
                        original_task_ref=bundle["original_task"]["submission_receipt_ref"], basis=basis)
        native.append(parse_comparative_systems_document(raw[member["raw_artifact_ref"]], document=document,
                      format_profile=selection["format_profile"], producer_evidence=evidence))
    return tuple(native), requirements, diagnostics


def _data(bundle, raw, wrappers, selection):
    require(type(wrappers) is tuple, "qualified_data_tuple_required")
    if selection is None:
        require(not wrappers, "unselected_qualified_data")
        return None, [], []
    allowed = {source for selected in selection["record_sets"] for source in selected["source_refs"]}
    qualified = [validate_shape("QualifiedDataInputV1", item) for item in wrappers]
    sources = [item["raw_binding"]["source_ref"] for item in qualified]
    require(len(sources) == len(set(sources)) and set(sources) <= allowed, "qualified_data_source_selection_mismatch")
    bindings = _content_bindings(bundle)
    valid, problems = {}, {}
    for wrapper in qualified:
        binding = wrapper["raw_binding"]
        expected = {"source_ref": binding["source_ref"], "artifact_ref": binding["raw_artifact_ref"],
                    "sha256": binding["sha256"], "byte_count": binding["byte_count"]}
        matches = [item for item in bindings if all(item[key] == value for key, value in expected.items())]
        require(len(matches) == 1, "qualified_data_bundle_binding_mismatch")
        source = binding["source_ref"]
        if binding["bytes_key"] not in raw:
            problems[source] = "data_input_unavailable"
            continue
        try:
            checked_bytes(raw[binding["bytes_key"]], binding)
        except ValueError:
            problems[source] = "byte_identity_mismatch"
            continue
        valid[source] = wrapper
    result = {"version": "bvbrc_comparative_systems_supplied_records_v1", "selection": deepcopy(selection),
              "record_sets": [], "requirements": [], "diagnostics": []}
    requirements, diagnostics = [], []
    for selected in selection["record_sets"]:
        part_selection = {"version": selection["version"], "record_sets": [selected]}
        supplied = tuple(valid[source] for source in selected["source_refs"] if source in valid)
        try:
            part = extract_comparative_systems_data_inputs(supplied, artifact_bytes=raw, selection=part_selection)
        except ValueError as error:
            if not str(error).startswith("comparative_systems_data_"):
                raise
            # A rejected supplemental population does not erase native siblings.
            # Its unavailable result is created by D's own missing-input path.
            part = extract_comparative_systems_data_inputs((), artifact_bytes=raw, selection=part_selection)
            for source in selected["source_refs"]:
                problems[source] = "data_input_binding_mismatch"
        for name in ("record_sets", "requirements", "diagnostics"):
            result[name].extend(part[name])
        for source in selected["source_refs"]:
            if source in problems:
                role = selected["roles"][0] if len(selected["roles"]) == 1 else "native_document"
                requirements.append(requirement(problems[source], role=role, refs=[source]))
                diagnostics.append(issue(problems[source], role=role, refs=[source], phase="population"))
    result["requirements"] = unique(result["requirements"])
    result["diagnostics"] = unique(result["diagnostics"])
    return validate_supplied_record_sets(result), requirements, diagnostics


class _ReferenceFailure(Exception):
    def __init__(self, code):
        self.code = code


def _reference_require(condition, code="reference_membership_missing"):
    if not condition:
        raise _ReferenceFailure(code)


def _tokens(pointer):
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer.split("/")[1:]] if pointer else []


def _covers(location, source, artifact, pointer):
    parent, child = _tokens(location["json_pointer"]), _tokens(pointer)
    return (location["source_ref"] == source and location["raw_artifact_ref"] == artifact
            and len(parent) <= len(child) and child[:len(parent)] == parent)


def _reference_cell(row, name, *, array=False):
    cells = [cell for cell in row["native_row"]["cells"] if cell["field"] == name]
    _reference_require(len(cells) == 1, "missing_required_field")
    cell = cells[0]
    _reference_require(cell["status"] == "valid" and cell["native_shape"] == ("array" if array else "scalar")
                       and (array or len(cell["atoms"]) == 1), "native_identifier_placeholder")
    values = []
    for atom in cell["atoms"]:
        _reference_require(atom["kind"] == "string" and type(atom["string_value"]) is str
                           and atom["string_value"] == atom["string_value"].strip()
                           and bool(atom["string_value"]), "native_identifier_placeholder")
        values.append(atom["string_value"])
    return values if array else values[0], cell["native_path"]


def _verified_reference(reference, supplied, qualified_inputs, raw):
    _reference_require(reference["basis"] == "supplied_data_api" and supplied is not None)
    _reference_require(reference["release"] is None, "source_version_mismatch")
    _reference_require(len(reference["members"]) == len(set(reference["members"])), "identity_conflict")
    locations = reference["source_locations"]
    pairs = {(item["source_ref"], item["raw_artifact_ref"]) for item in locations}
    _reference_require(bool(pairs) and all(item["document_id"] is None and item["table"] is None for item in locations))
    collection = "pathway_ref" if reference["component_kind"] == "ec_number" else "subsystem_ref"
    candidates = [record for record in supplied["record_sets"] if record["collection"] == collection
                  and {(page["binding"]["source_ref"], page["binding"]["native_artifact_ref"]) for page in record["pages"]} == pairs]
    _reference_require(len(candidates) == 1, "ambiguous_document_selection" if candidates else "reference_membership_missing")
    record = candidates[0]
    _reference_require(record["population"]["completeness"] == "complete_for_declared_population"
                       and record["page_coverage"] == "complete"
                       and record["snapshot_consistency"] in {"single_response", "proven_same_snapshot"},
                       "incomplete_reference_membership")
    bindings = {page["binding"]["source_ref"]: page["binding"] for page in record["pages"]}
    wrappers = {item["raw_binding"]["source_ref"]: item for item in qualified_inputs}
    payloads = {}
    for source, artifact in pairs:
        wrapper = wrappers.get(source)
        _reference_require(wrapper is not None and wrapper["raw_binding"]["raw_artifact_ref"] == artifact)
        try:
            payloads[source] = json_value(checked_bytes(raw.get(wrapper["raw_binding"]["bytes_key"]), wrapper["raw_binding"]))
        except ValueError as error:
            raise _ReferenceFailure("byte_identity_mismatch") from error
    for location in locations:
        try:
            at(payloads[location["source_ref"]], location["json_pointer"])
        except ValueError as error:
            raise _ReferenceFailure("reference_membership_missing") from error
        tokens = _tokens(location["json_pointer"])
        if location["row_ordinal"] is not None:
            _reference_require(len(tokens) >= 3 and tokens[:2] == ["response", "docs"]
                               and tokens[2] == str(location["row_ordinal"]), "data_input_binding_mismatch")
        if location["native_field"] is not None:
            _reference_require(len(tokens) == 4 and tokens[-1] == location["native_field"], "data_input_binding_mismatch")
        if location["column_ordinal"] is not None:
            _reference_require(len(tokens) == 4 and tokens[:2] == ["response", "docs"], "data_input_binding_mismatch")
            row = at(payloads[location["source_ref"]], "/response/docs/" + tokens[2])
            ordinal = location["column_ordinal"]
            _reference_require(type(row) is dict and ordinal < len(row) and list(row)[ordinal] == tokens[-1],
                               "data_input_binding_mismatch")
    map_context = None
    if collection == "pathway_ref" and reference["map_id"] is not None:
        try:
            map_context = json.loads(reference["map_id"])
        except ValueError as error:
            raise _ReferenceFailure("population_incompatible") from error
        _reference_require(type(map_context) is list and len(map_context) == 2
                           and all(type(value) is str and bool(value) for value in map_context), "population_incompatible")
        _reference_require(reference["map_id"] == json.dumps(map_context, sort_keys=True, separators=(",", ":"),
                                                             ensure_ascii=False, allow_nan=False), "population_incompatible")
    elif collection == "subsystem_ref":
        _reference_require(reference["map_id"] is None, "population_incompatible")
    members, contexts, selected_rows = set(), set(), []
    entity = reference["entity"]
    entity_field = "pathway_id" if collection == "pathway_ref" else "subsystem_id"
    for row in record["rows"]:
        # Even an unidentified row may belong to this selected entity.
        identifier, _ = _reference_cell(row, entity_field)
        if identifier != entity[entity_field]:
            continue
        _reference_require(row["duplicate_state"] != "conflicting_repeat", "duplicate_record_conflict")
        _reference_cell(row, "id")
        if collection == "pathway_ref":
            name, _ = _reference_cell(row, "map_name")
            kind, _ = _reference_cell(row, "map_type")
            context = (kind, name)
            contexts.add(context)
            value, pointer = _reference_cell(row, "ec_number")
            if map_context is not None and list(context) != map_context:
                continue
            values = [value]
        else:
            context = []
            by_field = {cell["field"]: cell for cell in row["native_row"]["cells"]}
            for key, name in (("subsystem_name", "subsystem_name"), ("superclass_native", "superclass"),
                              ("class_name", "class"), ("subclass", "subclass")):
                cell = by_field.get(name)
                value = None
                if cell is not None and cell["presence"] not in {"absent", "null"}:
                    value, _ = _reference_cell(row, name)
                if entity[key] is not None:
                    _reference_require(value == entity[key], "population_incompatible")
                if name == "superclass" and entity["superclass_aggregation"] is not None:
                    _reference_require(value is not None and value.upper() == entity["superclass_aggregation"], "population_incompatible")
                context.append(value)
            contexts.add(tuple(context))
            values, pointer = _reference_cell(row, "role_id", array=True)
        source = row["source_ref"]
        artifact = bindings[source]["native_artifact_ref"]
        _reference_require(any(_covers(location, source, artifact, pointer) for location in locations))
        selected_rows.append(row)
        members.update(values)
    if collection == "pathway_ref":
        _reference_require(map_context is not None or len(contexts) <= 1, "ambiguous_document_selection")
        _reference_require(map_context is None or not contexts or tuple(map_context) in contexts, "population_incompatible")
    else:
        _reference_require(len(contexts) <= 1, "identity_conflict")
    if not selected_rows:
        # No row pointer can prove an empty population, and a broad nonempty
        # query without this entity does not establish its reference identity.
        _reference_require(not record["rows"])
        for source, artifact in pairs:
            _reference_require(any(_covers(location, source, artifact, "/response/docs") for location in locations))
        entity_filters = []
        for source, _ in pairs:
            filters = wrappers[source]["qualified_result"]["grading"]["prepared"]["effective_request"]["filters"]
            entity_filters.extend(predicate for predicate in filters if predicate["field"] == entity_field
                                  and predicate["operator"] == "eq" and predicate["value"] == entity[entity_field])
        _reference_require(bool(entity_filters))
    _reference_require(set(reference["members"]) == members, "population_incompatible")
    codes = list(dict.fromkeys(record["population"]["qualification_codes"] + ["reference_release_unknown"]))
    _reference_require(set(reference["qualification_codes"]) <= set(codes), "data_input_binding_mismatch")
    result = deepcopy(reference)
    result["qualification_codes"] = list(dict.fromkeys(result["qualification_codes"] + codes))
    return result


def _references(parameters, supplied, qualified_inputs, raw):
    references, requirements, diagnostics = [], [], []
    for reference in parameters["reference_memberships"]:
        try:
            references.append(_verified_reference(reference, supplied, qualified_inputs, raw))
        except _ReferenceFailure as error:
            args = dict(role="reference_membership", refs=[item["source_ref"] for item in reference["source_locations"]])
            requirements.append(requirement(error.code, **args))
            diagnostics.append(issue(error.code, phase="population", **args))
    return tuple(references), requirements, diagnostics


def consume_bundle(bundle: dict, *, artifact_bytes: dict[str, bytes], supplied_values: list[dict],
        qualified_data_inputs: tuple[dict, ...], qualified_producer_evidence: tuple[dict, ...],
        requested_form: dict, parameters: dict) -> dict:
    """Consume only explicit original bindings and separately supplied bytes."""
    selected = validate_parameters(parameters)
    form = validate_requested_form(requested_form)
    bound = validate_contract("ArtifactBundle", bundle)
    original = original_request(bound["original_task"])
    require(type(artifact_bytes) is dict and all(type(key) is str and type(value) is bytes
                                               for key, value in artifact_bytes.items()), "artifact_byte_map_required")
    require(type(supplied_values) is list, "supplied_values_list_required")
    evidence, qualifications = _producers(bound, artifact_bytes, supplied_values, qualified_producer_evidence, selected)
    documents, requirements, diagnostics = _documents(bound, artifact_bytes, selected, evidence, qualifications)
    supplied, missing, issues = _data(bound, artifact_bytes, qualified_data_inputs, selected["supplied_data_selection"])
    requirements.extend(missing)
    diagnostics.extend(issues)
    references, missing, issues = _references(selected, supplied, qualified_data_inputs, artifact_bytes)
    requirements.extend(missing)
    diagnostics.extend(issues)
    sheet = build_comparative_systems_sheet(documents, analysis_id=selected["analysis_id"],
        original_request=original, producer_evidence=evidence, document_selection=selected["document_selection"],
        population_assignments=selected["population_assignments"], supplied_record_sets=supplied,
        reference_memberships=references)
    sheet["requirements"] = unique([*sheet["requirements"], *requirements])
    sheet["diagnostics"] = unique([*sheet["diagnostics"], *diagnostics])
    sheet = validate_sheet(sheet)
    components = calculate_comparative_systems_components(sheet, parameters=selected["calculation_parameters"])
    return validate_shape("ProviderResultV1", assemble_projection(sheet, components, requested_form=form,
        failure_context={"retained_requirements": [], "retained_diagnostics": [], "failure_status": None}))


__all__ = ["consume_bundle"]
