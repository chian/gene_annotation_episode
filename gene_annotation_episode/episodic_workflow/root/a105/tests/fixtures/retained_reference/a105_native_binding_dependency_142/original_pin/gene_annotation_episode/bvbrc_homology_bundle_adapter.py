"""Deterministic C4 artifact-bundle bridge to the existing Homology graders.

The host authenticates and retains bytes and explicitly supplied source values.
This module validates their scientific relationships, calls the existing pure
readers/calculators, and projects only declared numerical facts. No callback,
Store lookup, acquisition, execution, model, or continuation decision occurs.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from .bvbrc_appservice_contracts import (
    ContractValidationError, _finite_json, _same, _Validator, contract_schema,
    validate_contract,
)
from .bvbrc_homology_inputs import (
    FIELDS, FORMATS, _index, _pointer, _text,
    read_homology_raw_json, read_homology_processed_json, read_homology_tabular,
    reconcile_homology_artifacts,
)
from .bvbrc_homology_metadata import read_homology_metadata, bind_homology_metadata
from .bvbrc_homology_grader import build_homology_sheet, calculate_homology_scores
from .bvbrc_homology_subject_binding import validate_pairwise_subject


ADAPTER_ID = "bvbrc_homology"
ADAPTER_VERSION = "1"
PARAMETERS_VERSION = "bvbrc_homology_bundle_parameters_v1"
SCIENTIFIC_INPUTS_VERSION = "bvbrc_homology_scientific_inputs_v1"
_PRIMARY = {"raw": "blast_json15_raw", "processed": "homology_processed_json", "tabular": "blast_tabular"}
_ROLES = tuple(FORMATS)
_DEPENDENCIES = (
    "bvbrc_homology_bundle_adapter.py", "bvbrc_homology_inputs.py",
    "bvbrc_homology_metadata.py", "bvbrc_homology_grader.py", "bvbrc_homology_subject_binding.py",
    "blast_grading_inputs.py", "blast_database_grader.py", "blast_pairwise_grader.py",
    "blast_search.py", "bvbrc_appservice_contracts.py", "bvbrc_appservice_schemas.json",
)
_QUERY_FIELDS = {"input_source_ref", "member_ref", "subject_ref", "molecule", "supplied_id",
    "supplied_length", "supplied_sequence_sha256", "staged_id", "staged_length", "staged_sequence_sha256",
    "sequence_transform", "native_query", "id_mapping_evidence"}


def implementation_sha256() -> str:
    """Configuration identity only; scientific computation never calls this.

    Hash the actual adapter and repository parser/calculator/contract dependency
    bytes with unambiguous filename/length framing. No input or reference data
    are read. A later dependency edit changes the installed implementation pin.
    """
    result = hashlib.sha256()
    for name in sorted(_DEPENDENCIES):
        content = Path(__file__).with_name(name).read_bytes()
        result.update(name.encode() + b"\0" + str(len(content)).encode() + b"\0" + content)
    return result.hexdigest()


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def _nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


_STRING = {"type": "string", "minLength": 1}
_EVIDENCE_SCHEMA = contract_schema("SourceEvidence")
PARAMETERS_SCHEMA = _object({
    "version": {"const": PARAMETERS_VERSION},
    "scientific_mode": {"enum": ["database_identification", "pairwise_correspondence"]},
    "primary_representation": {"enum": list(_PRIMARY)},
    "artifact_source_refs": _object({role: _nullable(_STRING) for role in _ROLES}),
    "scientific_inputs": _nullable({"$ref": "#/$defs/SourceEvidence"}),
    "tabular_fields": _nullable({"const": FIELDS}),
    "database_model": _nullable(_object({
        "temperature_bits": {"type": "number", "exclusiveMinimum": 0},
        "function_priors": _nullable({"type": "object", "additionalProperties": {"type": "number", "minimum": 0}}),
    })),
})
PARAMETERS_SCHEMA["$defs"] = deepcopy(_EVIDENCE_SCHEMA["$defs"])


def _validate(schema, value, code):
    _finite_json(value)
    error = next(_Validator(schema).iter_errors(value), None)
    if error is not None:
        path = "".join("/" + str(k).replace("~", "~0").replace("/", "~1") for k in error.absolute_path)
        raise ContractValidationError(code, path)
    return deepcopy(value)


def validate_parameters(parameters: dict) -> dict:
    result = _validate(PARAMETERS_SCHEMA, parameters, "homology_adapter_parameters_invalid")
    if result["scientific_inputs"] is not None:
        validate_contract("SourceEvidence", result["scientific_inputs"])
    if result["scientific_mode"] == "pairwise_correspondence" and result["database_model"] is not None:
        raise ContractValidationError("homology_database_model_unused_for_pairwise", "/database_model")
    model = result["database_model"]
    if model is not None:
        numbers = [model["temperature_bits"], *(model["function_priors"] or {}).values()]
        try:
            valid = all(math.isfinite(value) for value in numbers)
        except OverflowError:
            valid = False
        if not valid:
            raise ContractValidationError("homology_adapter_parameters_invalid", "/database_model")
    return result


# This finite catalog selects existing quantities; it evaluates no user formula
# or arbitrary JSON path. The numerical meanings remain the existing sheets'.
_QUERY_METRICS = {
    "reported_hit_count": ("integer", "native"),
    "query_length": ("integer", "native"),
    "sequence_group_count": ("integer", "coverage"),
    "groups_with_explicit_function": ("integer", "coverage"),
    "groups_without_explicit_function": ("integer", "coverage"),
    "matched_metadata_row_count": ("integer", "coverage"),
    "duplicate_native_hit_count": ("integer", "dependence"),
    "unannotated_reference_kernel_fraction": ("number", "kernel"),
}
_HIT_METRICS = {
    "hsp_count": "integer", "maximum_bit_score": "number", "minimum_evalue": "number",
    "observed_paired_query_positions": "integer", "observed_paired_reference_positions": "integer",
    "query_paired_coverage": "number", "reference_paired_coverage": "number",
    "unique_pair_count": "integer", "overlap_pair_representations": "integer",
    "reference_length": "integer", "query_span_coverage": "number", "reference_span_coverage": "number",
}
_HSP_METRICS = {
    "hsp_bit_score": ("number", "native_scores", "bit_score"),
    "hsp_score": ("number", "native_scores", "score"),
    "hsp_evalue": ("number", "native_scores", "evalue"),
    "alignment_columns": ("integer", "counts", "alignment_columns"),
    "paired_columns": ("integer", "counts", "paired_columns"),
    "identical_pairs": ("integer", "counts", "identical_pairs"),
    "query_gap_columns": ("integer", "counts", "query_gap_columns"),
    "reference_gap_columns": ("integer", "counts", "reference_gap_columns"),
    "hsp_query_paired_coverage": ("number", "fractions", "query_paired_coverage"),
    "hsp_reference_paired_coverage": ("number", "fractions", "reference_paired_coverage"),
    "paired_identity": ("number", "fractions", "paired_identity"),
    "alignment_identity": ("number", "fractions", "alignment_identity"),
    "substitution_columns": ("integer", "supplement", "substitution_columns"),
    "query_gap_runs": ("integer", "supplement", "query_gap_runs"),
    "reference_gap_runs": ("integer", "supplement", "reference_gap_runs"),
}
_PAIR_METRICS = {
    "pairwise_query_coverage": ("number", "fractions", "query_paired_coverage"),
    "pairwise_reference_coverage": ("number", "fractions", "reference_paired_coverage"),
    "pairwise_identity": ("number", "fractions", "paired_identity"),
    "pairwise_distinct_pairs": ("integer", "counts", "distinct_residue_pairs"),
}
_FUNCTION_METRICS = {
    "conditional_function_weight": ("number", "unadjusted_probabilities"),
    "representation_adjusted_function_weight": ("number", "representation_adjusted_probabilities"),
    "function_kernel_mass": ("number", "function_masses"),
    "database_function_count": ("integer", "database_sequence_count"),
    "database_function_fraction": ("number", "database_fraction"),
}
_DISTRIBUTION_METRICS = {
    "conditional_function_weights": "unadjusted_probabilities",
    "representation_adjusted_function_weights": "representation_adjusted_probabilities",
}
_TAXON_METRICS = {
    "same_taxon_pair_count": "integer", "comparable_pair_count": "integer",
    "same_taxon_pair_fraction": "number", "target_matching_groups": "integer",
    "target_conflicting_groups": "integer", "target_matching_fraction": "number",
    "unknown_group_count": "integer", "ambiguous_group_count": "integer",
}
_QUALITY_FIELDS = {"completeness_fraction", "contamination_fraction", "contig_count", "contig_n50", "total_sequence_length"}


def _selector_type(selection):
    if type(selection) is not dict or not _text(selection.get("metric")):
        raise ContractValidationError("homology_fact_selector_invalid")
    metric, fields = selection["metric"], {"metric", "report_index"}
    if metric == "missing_requirements":
        fields, value_type = {"metric"}, "requirements"
    elif metric in _QUERY_METRICS:
        value_type = _QUERY_METRICS[metric][0]
    elif metric in _HIT_METRICS:
        fields.add("hit_index")
        value_type = _HIT_METRICS[metric]
    elif metric in _HSP_METRICS:
        fields.update(("hit_index", "hsp_index"))
        value_type = _HSP_METRICS[metric][0]
    elif metric in _PAIR_METRICS:
        value_type = _PAIR_METRICS[metric][0]
    elif metric in _FUNCTION_METRICS:
        fields.add("function")
        value_type = _FUNCTION_METRICS[metric][0]
    elif metric in _DISTRIBUTION_METRICS:
        value_type = "distribution"
    elif metric in _TAXON_METRICS:
        fields.add("rank")
        value_type = _TAXON_METRICS[metric]
    elif metric == "source_quality_mean":
        fields.update(("field", "method"))
        value_type = "number"
    elif metric in {"tabular_mismatch", "tabular_gapopen", "tabular_pident"}:
        fields.add("line")
        value_type = "number" if metric == "tabular_pident" else "integer"
    else:
        raise ContractValidationError("homology_fact_metric_unknown")
    if set(selection) != fields:
        raise ContractValidationError("homology_fact_selector_invalid")
    for field in fields - {"metric"}:
        value = selection[field]
        valid = (_index(value) if field in {"report_index", "hit_index", "hsp_index"}
                 else type(value) is int and value > 0 if field == "line"
                 else value in _QUALITY_FIELDS if field == "field" and type(value) is str
                 else _text(value))
        if not valid:
            raise ContractValidationError("homology_fact_selector_invalid")
    return value_type


def requested_form_schema(fields: dict) -> dict:
    """Build the closed original requested form from exact metric selections."""
    _finite_json(fields)
    if type(fields) is not dict or not fields or any(not _text(k) for k in fields):
        raise ContractValidationError("homology_requested_form_invalid")
    properties = {}
    for name, selection in fields.items():
        kind = _selector_type(selection)
        if kind == "requirements":
            node = {"type": "array", "items": contract_schema("AcquisitionRequirement")["$defs"]["AcquisitionRequirement"]}
        elif kind == "distribution":
            node = {"type": ["array", "null"], "items": _object({
                "function": _STRING, "weight": {"type": "number", "minimum": 0, "maximum": 1}})}
        else:
            node = {"type": [kind, "null"]}
        properties[name] = {**node, "x-homology-fact": deepcopy(selection)}
    return _object(properties)


def validate_requested_form(requested_form: dict) -> dict:
    _finite_json(requested_form)
    if (type(requested_form) is not dict or set(requested_form) != {"type", "properties", "required", "additionalProperties"}
            or type(requested_form.get("properties")) is not dict):
        raise ContractValidationError("homology_requested_form_invalid")
    selections = {}
    for name, node in requested_form["properties"].items():
        if type(node) is not dict or "x-homology-fact" not in node:
            raise ContractValidationError("homology_fact_selector_required")
        selections[name] = node["x-homology-fact"]
    expected = requested_form_schema(selections)
    # Property order is irrelevant; required is a set of all selected fields.
    required = requested_form.get("required")
    if (type(required) is not list or any(type(v) is not str for v in required)
            or len(required) != len(set(required)) or set(required) != set(selections)):
        raise ContractValidationError("homology_requested_form_invalid")
    expected["required"] = required
    if not _same(expected, requested_form):
        raise ContractValidationError("homology_requested_form_invalid")
    return deepcopy(requested_form)


def _diag(code, path="", *, phase="association", severity="error", refs=()):
    return {"code": code, "phase": phase, "path": path, "severity": severity,
            "evidence_refs": list(dict.fromkeys(ref for ref in refs if _text(ref)))}


def _requirement(code, *, kind="scientific_metadata", role=None, refs=(), identity=""):
    # Local stable identity, not a new source/receipt or an acquisition decision.
    token = hashlib.sha256(json.dumps([code, kind, role, identity], separators=(",", ":")).encode()).hexdigest()[:20]
    return {"requirement_id": "homology:" + token, "kind": kind, "role": role,
            "source_refs": list(dict.fromkeys(ref for ref in refs if _text(ref))), "reason_code": code}


def _unique(rows):
    result = []
    for row in rows:
        if row not in result:
            result.append(deepcopy(row))
    return result


def _empty_metadata():
    return {"schema": "bvbrc_homology_metadata_bindings_v1", "description_links": [], "records": [],
            "bindings": [], "sequence_identity_bindings": [], "target_context_by_query": [], "database_profile": None}


def _metadata_input(scientific, diagnostics):
    value = scientific["metadata"] if scientific else None
    if value is None:
        return _empty_metadata()
    expected = _empty_metadata()
    if (set(value) != set(expected) or value.get("schema") != expected["schema"]
            or any(type(value.get(key)) is not list for key in
                   ("description_links", "records", "bindings", "sequence_identity_bindings", "target_context_by_query"))
            or value.get("database_profile") is not None and type(value["database_profile"]) is not dict):
        diagnostics.append(_diag("homology_supplied_metadata_shape_invalid", "/scientific_inputs/metadata"))
        # Preserve the actual invalid supplied value in binding.supplied_values.
        # The source cannot attach metadata, but valid alignments still calculate.
        return expected
    return value


def _supplied(bundle, supplied_values, selected):
    _finite_json(supplied_values)
    if type(supplied_values) is not list:
        raise ContractValidationError("homology_supplied_values_invalid")
    seen = []
    for row in supplied_values:
        if type(row) is not dict or set(row) != {"evidence", "value"}:
            raise ContractValidationError("homology_supplied_values_invalid")
        evidence = validate_contract("SourceEvidence", row["evidence"])
        if not any(_same(evidence, item) for item in bundle["supplied_scientific_metadata"]):
            raise ContractValidationError("homology_supplied_evidence_not_in_bundle")
        if any(_same(evidence, other["evidence"]) for other in seen):
            raise ContractValidationError("homology_supplied_evidence_ambiguous")
        seen.append(row)
    if selected is None:
        return None
    matches = [row for row in seen if _same(row["evidence"], selected)]
    if len(matches) != 1:
        raise ContractValidationError("homology_scientific_inputs_not_supplied")
    value = matches[0]["value"]
    if (type(value) is not dict or set(value) != {"version", "queries", "database_binding", "subject_binding", "metadata"}
            or value["version"] != SCIENTIFIC_INPUTS_VERSION or type(value["queries"]) is not list
            or any(value[key] is not None and type(value[key]) is not dict
                   for key in ("database_binding", "subject_binding", "metadata"))):
        raise ContractValidationError("homology_scientific_inputs_invalid")
    return deepcopy(value)


def _query_bindings(bundle, scientific, primary, selected, diagnostics, requirements):
    bindings = []
    for index, row in enumerate(scientific["queries"] if scientific else []):
        path = f"/scientific_inputs/queries/{index}"
        if (type(row) is not dict or set(row) != {"input_binding_id", "input_member_id", "representation", "binding"}
                or type(row["representation"]) is not str or row["representation"] not in _PRIMARY
                or type(row["binding"]) is not dict):
            diagnostics.append(_diag("homology_query_mapping_invalid", path))
            requirements.append(_requirement("homology_query_mapping_invalid", identity=path))
            continue
        if row["representation"] != primary:
            continue
        binding = row["binding"]
        inputs = [item for item in bundle["input_bindings"] if item["binding_id"] == row["input_binding_id"]]
        members = [m for item in inputs for m in item["members"] if m["member_id"] == row["input_member_id"]]
        code = None
        if (set(binding) != _QUERY_FIELDS or type(binding["native_query"]) is not dict
                or set(binding["native_query"]) != {"report_index", "query_id", "query_title", "query_len"}
                or type(binding["sequence_transform"]) is not dict
                or set(binding["sequence_transform"]) != {"kind", "source_ref", "pointer", "coordinate_map_ref"}
                or type(binding["id_mapping_evidence"]) is not list
                or any(type(e) is not dict or set(e) != {"source_ref", "pointer", "relation"}
                       for e in binding["id_mapping_evidence"])):
            code = "homology_query_mapping_invalid"
        elif len(inputs) != 1 or len(members) != 1:
            code = "homology_query_input_member_missing"
        else:
            source = inputs[0]["content"] or (members[0]["evidence"] or {}).get("content")
            member = members[0]
            molecule = {"protein": "aa", "dna": "nt", "rna": "nt"}.get(member["molecule"])
            if (source is None or binding.get("input_source_ref") != source["source_ref"]
                    or binding.get("member_ref") != member["member_id"]
                    or type(member["length"]) is not int or member["length"] <= 0
                    or member["sequence_sha256"] is None or molecule is None
                    or not _same(binding.get("supplied_length"), member["length"])
                    or binding.get("supplied_sequence_sha256") != member["sequence_sha256"]
                    or binding.get("molecule") != molecule):
                code = "homology_query_input_member_conflict"
            native = binding.get("native_query")
            if code is None and (type(native) is not dict or not _index(native.get("report_index"))):
                code = "homology_query_mapping_invalid"
            if code is None and selected is not None:
                candidates = [q for q in bundle["query_bindings"]
                    if q["raw_source_ref"] == selected["source_ref"] and q["raw_report_ordinal"] == native["report_index"]]
                if candidates:
                    q = candidates[0]
                    expected = {"input_binding_id": row["input_binding_id"], "input_member_id": row["input_member_id"],
                        "input_member_pointer": member["member_pointer"], "input_source_ref": source["source_ref"],
                        "length": member["length"], "molecule": member["molecule"], "sequence_sha256": member["sequence_sha256"],
                        "query_id": native.get("query_id"), "query_title": native.get("query_title")}
                    if any(not _same(q[key], value) for key, value in expected.items()):
                        code = "homology_c4_query_mapping_conflict"
        if code:
            diagnostics.append(_diag(code, path))
            requirements.append(_requirement(code, kind="input_metadata", identity=path))
        else:
            bindings.append(deepcopy(binding))
    return bindings


def _database_binding(task, scientific):
    requested = {key: deepcopy(value) for key, value in task["submitted_parameters"].items() if key.startswith("db_")}
    value = scientific["database_binding"] if scientific else None
    if value is None:
        return {"requested_selection": requested, "effective_native_database": None,
            "effective_parameters_source": None, "reference_release": None, "reference_release_source": None,
            "actual_taxon_filter": None, "actual_database_members": None, "input_or_database_sequence_inventory_ref": None}
    fields = {"requested_selection", "effective_native_database", "effective_parameters_source", "reference_release",
              "reference_release_source", "actual_taxon_filter", "actual_database_members", "input_or_database_sequence_inventory_ref"}
    if set(value) != fields or not _same(value["requested_selection"], requested):
        raise ContractValidationError("homology_database_request_binding_conflict")
    if value["effective_parameters_source"] is not None:
        effective = task["effective_parameters"]
        expected = None if effective is None else {"source_ref": effective["evidence"]["content"]["source_ref"],
                                                   "pointer": effective["evidence"]["pointer"]}
        if not _same(value["effective_parameters_source"], expected):
            raise ContractValidationError("homology_effective_parameters_source_conflict")
    return deepcopy(value)


def _representation_key(artifact):
    return {"role": artifact["role"], "sha256": artifact["sha256"], "byte_count": artifact["byte_count"],
        "workspace_object": {k: artifact["workspace_object"][k] for k in ("path", "uuid", "type")},
        "task_association": artifact["task_association"],
        "transfer": {k: v for k, v in artifact["transfer"].items() if k != "receipt_ref"},
        "declared_format": artifact["declared_format"]}


def _artifacts(bundle, content, parameters, diagnostics, requirements):
    selected, mapped = {}, []
    for role in _ROLES:
        candidates = [a for a in bundle["artifacts"] if a["role"] == role]
        source = parameters["artifact_source_refs"][role]
        if source is not None:
            candidates = [a for a in candidates if a["source_ref"] == source]
        if not candidates:
            if role == _PRIMARY[parameters["primary_representation"]] or source is not None:
                requirements.append(_requirement("homology_selected_artifact_missing", kind="output_bytes", role=role, refs=[source]))
            continue
        keys = _unique([_representation_key(a) for a in candidates])
        if len(keys) != 1:
            requirements.append(_requirement("homology_artifact_role_ambiguous", kind="parser_binding", role=role,
                                             refs=[a["source_ref"] for a in candidates]))
            diagnostics.append(_diag("homology_artifact_role_ambiguous", refs=[a["source_ref"] for a in candidates]))
            continue
        # A repeat of identical bytes/object/format/association is one scientific
        # representation. Canonical provenance is stable under input reordering;
        # every original record remains in binding.c4_bundle.
        artifact = deepcopy(min(candidates, key=lambda a: json.dumps(a, sort_keys=True)))
        if len(candidates) > 1:
            diagnostics.append(_diag("duplicate_artifact_representation", severity="qualification",
                                     refs=[a["source_ref"] for a in candidates]))
        refs, code, kind = [artifact["source_ref"]], None, "output_bytes"
        native = content.get(artifact["raw_artifact_ref"])
        if native is None:
            code = "homology_artifact_bytes_not_supplied"
        elif hashlib.sha256(native).hexdigest() != artifact["sha256"] or len(native) != artifact["byte_count"]:
            code = "homology_artifact_bytes_conflict"
        elif artifact["declared_format"]["format"] != FORMATS[role] or artifact["declared_format"]["mode"] != parameters["scientific_mode"]:
            code, kind = "homology_declared_format_conflict", "parser_binding"
        elif artifact["task_association"]["kind"] != "task_result_manifest":
            code, kind = "homology_task_manifest_required", "task_manifest"
        elif any(artifact["workspace_object"][key] is None for key in ("path", "uuid", "type", "metadata_receipt_ref")):
            code, kind = "homology_workspace_metadata_required", "output_metadata"
        elif (artifact["task_association"]["output_path"] != artifact["workspace_object"]["path"]
              or artifact["task_association"]["output_uuid"] != artifact["workspace_object"]["uuid"]):
            code, kind = "homology_task_manifest_object_required", "task_manifest"
        elif (artifact["transfer"]["body_complete"] is not True or artifact["transfer"]["object_complete"] != "yes"
              or artifact["transfer"]["total_size"] != len(native)):
            code = "homology_complete_object_required"
        if code:
            requirements.append(_requirement(code, kind=kind, role=role, refs=refs))
            diagnostics.append(_diag(code, refs=refs))
            continue
        if artifact["task_association"]["byte_version_status"] != "producer_bytes_bound":
            diagnostics.append(_diag("output_version_unproven", severity="qualification", refs=refs))
        association = artifact["task_association"]
        artifact["task_association"] = {"manifest_source_ref": association["evidence_ref"],
            "manifest_record_pointer": association["pointer"],
            **{k: association[k] for k in ("task_id", "output_path", "output_uuid")}}
        artifact["declared_format"].update(transformation_version=None,
            fields=deepcopy(parameters["tabular_fields"]) if role in {"blast_tabular", "blast_tabular_header"} else None)
        selected[role] = artifact
        mapped.append(artifact)
    return selected, mapped


def _one(rows, key, value):
    matches = [row for row in rows if type(row) is dict and _same(row.get(key), value)]
    return matches[0] if len(matches) == 1 else None


def _fact(selection, sheet, components):
    """Project a single existing native/derived quantity; None is not zero."""
    metric = selection["metric"]
    query = _one(sheet["queries"], "report_index", selection["report_index"])
    if query is None or query["normalized_result"] is None:
        return None, "homology_requested_query_unavailable"
    if query["query_binding_status"] != "validated":
        return None, "homology_query_binding_unavailable"
    conflicts = {"homology_program_request_conflict", "homology_program_database_type_conflict",
                 "homology_native_database_conflict", "homology_format_version_conflict"}
    if any(row["code"] in conflicts for row in query["diagnostics"]):
        return None, "homology_native_request_conflict"
    normalized, blast = query["normalized_result"], query["blast_sheet"]
    scored = _one(components["queries"], "report_index", selection["report_index"])
    supplement = _one(components["alignment_supplements"]["queries"], "report_index", selection["report_index"])
    value = None
    if metric in _QUERY_METRICS:
        section = _QUERY_METRICS[metric][1]
        if metric == "reported_hit_count":
            value = normalized["search"]["reported_hit_count"]
        elif metric == "query_length":
            value = normalized["query"]["length"]
        elif section == "kernel":
            value = (scored["conditional_function_weights"] or {}).get(metric)
        elif blast and blast["schema"] == "blast_database_sheet_v1":
            value = blast[section].get(metric)
    elif metric in _HIT_METRICS:
        hit = _one(normalized["hits"], "hit_index", selection["hit_index"])
        if hit and metric == "reference_length":
            value = hit["length"]
        elif hit and metric == "hsp_count":
            # Native arrays missing or malformed do not become measured zero.
            issues = normalized["issues"]
            if not any(i.get("hit_index") == hit["hit_index"] and i["code"] in
                       {"blast_hsp_array_not_reported", "blast_hsp_array_invalid", "blast_hit_object_required"} for i in issues):
                value = len(hit["hsps"])
        elif metric in {"query_span_coverage", "reference_span_coverage"}:
            sh = _one(supplement["hits"], "hit_index", selection["hit_index"])
            if sh:
                value = sh["span_union"][metric.split("_", 1)[0]]["coverage"]["value"]
        elif blast and blast["schema"] == "blast_database_sheet_v1":
            bh = _one(blast["hits"], "hit_index", selection["hit_index"])
            value = bh["measurements"].get(metric) if bh else None
    elif metric in _HSP_METRICS:
        hit = _one(supplement["hits"], "hit_index", selection["hit_index"])
        hsp = _one(hit["hsps"], "hsp_index", selection["hsp_index"]) if hit else None
        if hsp:
            _, section, field = _HSP_METRICS[metric]
            value = hsp[field]["value"] if section == "supplement" else hsp["alignment_components"][section].get(field)
    elif metric in _PAIR_METRICS:
        pair = scored["pairwise_correspondence"]
        if pair:
            _, section, field = _PAIR_METRICS[metric]
            value = pair["union"][section].get(field)
    elif metric in _FUNCTION_METRICS:
        kernel = scored["conditional_function_weights"]
        if kernel and metric in {"conditional_function_weight", "representation_adjusted_function_weight", "function_kernel_mass"}:
            value = (kernel[_FUNCTION_METRICS[metric][1]] or {}).get(selection["function"])
        elif blast and blast["schema"] == "blast_database_sheet_v1":
            row = _one(blast["database_representation"]["function_representation"], "function", selection["function"])
            if row and blast["database_representation"]["available_for_adjustment"]:
                value = row[_FUNCTION_METRICS[metric][1]]
    elif metric in _DISTRIBUTION_METRICS:
        kernel = scored["conditional_function_weights"]
        weights = kernel[_DISTRIBUTION_METRICS[metric]] if kernel else None
        if weights is not None:
            # Labels are dictionary keys from the existing source-grounded
            # calculator, paired with their own weights; no sorted-list join.
            value = [{"function": function, "weight": weights[function]} for function in sorted(weights)]
        elif normalized["search"]["hit_array_present"] and normalized["search"]["reported_hit_count"] == 0:
            # This is the empty reported candidate population, never a claim
            # of zero functions in the database. Unknown/missing hits stay null.
            value = []
    elif metric in _TAXON_METRICS and blast and blast["schema"] == "blast_database_sheet_v1":
        row = _one(blast["taxonomy"]["ranks"], "rank", selection["rank"])
        value = row.get(metric) if row else None
    elif metric == "source_quality_mean" and blast and blast["schema"] == "blast_database_sheet_v1":
        rows = [row for row in blast["source_quality"]["numerical_summaries"]
                if row["field"] == selection["field"] and row["quality_method"] == selection["method"]]
        value = rows[0]["mean"] if len(rows) == 1 else None
    elif metric.startswith("tabular_"):
        row = _one(query["native_tabular_measurements"], "line", selection["line"])
        if row and row.get("association_status") not in {"conflicting", "ambiguous"}:
            value = row.get(metric[len("tabular_"):])
    if value is not None:
        return value, None
    if metric in _PAIR_METRICS and (not blast or blast["schema"] != "blast_pairwise_sheet_v1"):
        reason = "homology_pairwise_subject_membership_unproved"
    elif metric in _TAXON_METRICS:
        reason = "homology_linked_taxonomy_or_comparison_population_unavailable"
    elif metric == "source_quality_mean":
        reason = "homology_source_measurements_unavailable"
    elif metric in {"representation_adjusted_function_weight", "representation_adjusted_function_weights",
                    "database_function_count", "database_function_fraction"}:
        reason = "homology_matching_database_population_unavailable"
    elif metric in _FUNCTION_METRICS or metric in _DISTRIBUTION_METRICS or metric == "unannotated_reference_kernel_fraction":
        reason = "homology_scored_function_population_unavailable"
    elif metric in {"reported_hit_count", "hsp_count"}:
        reason = "homology_native_array_unavailable"
    elif metric in {"query_length", "reference_length"}:
        reason = "homology_operand_length_unavailable"
    else:
        reason = "homology_native_alignment_quantity_unavailable"
    return None, reason


def _validate_mode_projection(form, mode):
    common_hits = {"reference_length", "hsp_count", "query_span_coverage", "reference_span_coverage"}
    database = ((set(_QUERY_METRICS) - {"reported_hit_count", "query_length"})
                | (set(_HIT_METRICS) - common_hits) | set(_FUNCTION_METRICS) | set(_DISTRIBUTION_METRICS)
                | set(_TAXON_METRICS) | {"source_quality_mean"})
    for name, node in form["properties"].items():
        metric = node["x-homology-fact"]["metric"]
        if ((mode == "pairwise_correspondence" and metric in database)
                or mode == "database_identification" and metric in _PAIR_METRICS):
            raise ContractValidationError("homology_fact_scientific_mode_conflict",
                                          "/properties/" + name.replace("~", "~0").replace("/", "~1"))


def _native_diagnostics(parsed, sheet, components):
    rows = [*parsed["diagnostics"], *sheet["diagnostics"]]
    for collection in (sheet["queries"], components["queries"], components["alignment_supplements"]["queries"]):
        for row in collection:
            rows.extend(row.get("diagnostics", []))
    result = []
    for row in rows:
        # Legacy details remain intact in the sheet. C4 diagnostics contain only
        # a stable code, locator and evidence references, never a prose report.
        code = row["code"].split(":", 1)[0] if _text(row.get("code")) else "homology_invalid_native_diagnostic"
        path = row.get("pointer")
        if not _pointer(path):
            path = ""
        result.append(_diag(code, path, phase="native_decode", severity=row.get("severity", "error"),
                            refs=[row.get("artifact_ref")]))
    return result


def consume_bundle(bundle: dict, *, artifact_bytes: dict[str, bytes], supplied_values: list[dict],
                   requested_form: dict, parameters: dict) -> dict:
    """Consume actual supplied bytes without consulting any external state.

    Status concerns the original requested numeric projection. Valid partial
    sheets survive missing metadata or quantities; an operationally complete
    ArtifactBundle alone cannot establish this projection's completeness.
    """
    output = {"adapter_id": ADAPTER_ID, "adapter_version": ADAPTER_VERSION, "status": "invalid",
              "sheet": None, "components": None, "facts": {}, "missing_requirements": [], "diagnostics": []}
    try:
        bundle = validate_contract("ArtifactBundle", bundle)
        parameters, requested_form = validate_parameters(parameters), validate_requested_form(requested_form)
        _validate_mode_projection(requested_form, parameters["scientific_mode"])
        if (bundle["original_task"]["required_application_id"] != "Homology"
                or bundle["original_task"]["native_application_id"] != "Homology"):
            raise ContractValidationError("homology_artifact_task_mismatch")
        if (type(artifact_bytes) is not dict or any(type(k) is not str or type(v) is not bytes for k, v in artifact_bytes.items())
                or set(artifact_bytes) - {a["raw_artifact_ref"] for a in bundle["artifacts"]}):
            raise ContractValidationError("homology_artifact_bytes_map_invalid")
        scientific = _supplied(bundle, supplied_values, parameters["scientific_inputs"])
        diagnostics = output["diagnostics"] = deepcopy(bundle["diagnostics"])
        requirements = output["missing_requirements"] = deepcopy(bundle["missing_requirements"])
        selected, artifacts = _artifacts(bundle, artifact_bytes, parameters, diagnostics, requirements)
        task = deepcopy(bundle["original_task"])
        effective = task["effective_parameters"]
        task["effective_parameters"] = deepcopy(effective["value"]) if effective is not None else None
        task["effective_parameters_source"] = (None if effective is None else {
            "source_ref": effective["evidence"]["content"]["source_ref"], "pointer": effective["evidence"]["pointer"]})
        primary_role = _PRIMARY[parameters["primary_representation"]]
        binding = {"schema": "bvbrc_homology_artifact_bundle_v1", "original_task": task,
            "scientific_mode": parameters["scientific_mode"], "primary_representation": parameters["primary_representation"],
            "query_bindings": _query_bindings(bundle, scientific, parameters["primary_representation"],
                                               selected.get(primary_role), diagnostics, requirements),
            "subject_binding": deepcopy(scientific["subject_binding"]) if scientific else None,
            "database_binding": _database_binding(bundle["original_task"], scientific), "artifacts": artifacts,
            "c4_bundle": deepcopy(bundle), "scientific_inputs_evidence": deepcopy(parameters["scientific_inputs"]),
            "supplied_values": deepcopy(supplied_values), "adapter_parameters": deepcopy(parameters)}
        parsed_representations = {"raw": None, "processed": None, "tabular": None}
        for representation, reader in (("raw", read_homology_raw_json), ("processed", read_homology_processed_json)):
            artifact = selected.get(_PRIMARY[representation])
            if artifact:
                parsed_representations[representation] = reader(artifact_bytes[artifact["raw_artifact_ref"]],
                                                                artifact=artifact, binding=binding)
        table, header = selected.get("blast_tabular"), selected.get("blast_tabular_header")
        if table is not None:
            if header is None or parameters["tabular_fields"] is None:
                requirements.append(_requirement("homology_tabular_header_and_fields_required", kind="parser_binding", role="blast_tabular_header"))
            else:
                parsed_representations["tabular"] = read_homology_tabular(artifact_bytes[table["raw_artifact_ref"]],
                    header_content=artifact_bytes[header["raw_artifact_ref"]], artifact=table, header_artifact=header, binding=binding)
        parsed = reconcile_homology_artifacts(**parsed_representations, binding=binding)
        subject_failures = []
        if parameters["scientific_mode"] == "pairwise_correspondence":
            subject_failures = validate_pairwise_subject(bundle, subject=binding["subject_binding"],
                database=binding["database_binding"], supplied_values=supplied_values, queries=parsed["queries"])
            diagnostics.extend(_diag(row["code"], row["path"]) for row in subject_failures)
            if subject_failures:
                # Preserve the asserted original in supplied_values. Only a
                # subject associated with the submitted reference reaches the
                # paired sheet; unrelated valid native measurements survive.
                parsed["binding"]["subject_binding"] = None
        native_metadata = None
        sidecar = selected.get("homology_metadata_json")
        if sidecar:
            native_metadata = read_homology_metadata(artifact_bytes[sidecar["raw_artifact_ref"]], artifact=sidecar,
                description_links=[link for query in parsed["queries"] for link in query["description_links"]])
            retained = deepcopy(native_metadata["artifact"])
            retained["native_document"] = deepcopy(native_metadata.get("native_document"))
            parsed["artifacts"] = [retained if row["artifact"] == sidecar else row for row in parsed["artifacts"]]
        archive = selected.get("blast_archive")
        if archive is not None:
            for row in parsed["artifacts"]:
                if row["artifact"] == archive:
                    row.update(status="complete", qualifications=["retained_opaque_native_archive", "archive_decoder_not_provided"])
        metadata = bind_homology_metadata(parsed, native_metadata=native_metadata,
            supplied_metadata=_metadata_input(scientific, diagnostics))
        sheet = output["sheet"] = build_homology_sheet(parsed, metadata=metadata)
        components = output["components"] = calculate_homology_scores(sheet, database_model=parameters["database_model"])
        diagnostics.extend(_native_diagnostics(parsed, sheet, components))
        for name, node in requested_form["properties"].items():
            selection = node["x-homology-fact"]
            if selection["metric"] == "missing_requirements":
                continue
            value, reason = _fact(selection, sheet, components)
            output["facts"][name] = value
            if reason:
                requirements.append(_requirement(reason, identity=name))
                diagnostics.append(_diag(reason, "/facts/" + name.replace("~", "~0").replace("/", "~1"), phase="return"))
                if selection["metric"] in _PAIR_METRICS:
                    requirements.extend(_requirement(row["code"], kind="input_metadata", identity=row["path"])
                                        for row in subject_failures)
        output["missing_requirements"] = _unique(requirements)
        output["diagnostics"] = _unique(diagnostics)
        for name, node in requested_form["properties"].items():
            if node["x-homology-fact"]["metric"] == "missing_requirements":
                output["facts"][name] = deepcopy(output["missing_requirements"])
        _validate(requested_form, output["facts"], "homology_projected_fact_type_conflict")
        # A missing unrequested annotation or an unrelated invalid HSP remains
        # visible in the sheet and diagnostics; it does not invalidate an actual
        # requested native count. Every requested missing/conflicting quantity
        # above supplies its own requirement. Acquisition status alone never
        # establishes scientific completion, nor does unknown producer version
        # prevent reporting measurements of the actual retained current bytes.
        output["status"] = "partial" if output["missing_requirements"] or bundle["status"] != "ok" else "ok"
    except ContractValidationError as error:
        output["diagnostics"].extend(_diag(row["code"], row["path"], phase="publication") for row in error.diagnostics)
        output["status"] = "invalid"
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        # Retain valid data already produced; never include arbitrary exception
        # text or source values in the small returned diagnostic.
        output["diagnostics"].append(_diag("homology_scientific_input_or_calculation_failed", phase="native_decode"))
        output["status"] = "failed"
    output["diagnostics"] = _unique(output["diagnostics"])
    output["missing_requirements"] = _unique(output["missing_requirements"])
    for row in output["diagnostics"]:
        validate_contract("Diagnostic", row)
    for row in output["missing_requirements"]:
        validate_contract("AcquisitionRequirement", row)
    _finite_json(output)
    return output


__all__ = ["ADAPTER_ID", "ADAPTER_VERSION", "PARAMETERS_SCHEMA", "validate_parameters",
           "requested_form_schema", "validate_requested_form", "implementation_sha256", "consume_bundle"]
