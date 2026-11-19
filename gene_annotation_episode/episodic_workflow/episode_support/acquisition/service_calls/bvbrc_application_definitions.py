"""Retained BV-BRC application contracts and pure request preparation.

``ok`` means the supplied values passed the checks described here. It does not
mean a deployed application, file, reference, permission, or algorithm was
verified. Diagnostics have ``severity`` (``error`` or ``qualification``); unknown
fields survive unchanged with an explicit unvalidated qualification. Any error
gives ``invalid`` and a null value. No defaults, paths, modes, or resources are
selected here. No service calls are made.

An optional definition is the envelope returned by ``get_application_spec``:
required_id, native_id, definition, source, parse_corrections, and
duplicate_object_keys. Source contains exact UTF-8 content, its SHA256, kind,
and URL. An actual service definition may use kind
``retained_service_definition``. Its caller must separately establish custody
against the retained service response; a self-consistent hash is not custody.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.bvbrc_analysis_protocol import validate_start_parameters


REQUIRED_APPLICATION_IDS = ("Homology",)
_SPECS = Path(__file__).parents[2] / "forms" / "application_service_specs"
# These are byte offsets in two exact retained documents, not a JSON repair rule.
_COMMA_REMOVALS = {
    "285c918c9bcc25b5b8a2cc96582b50d1059f077e0ef691d9bdf1a5d44904796f": (544, 839),
    "d6215bd39a5947899240927b38eb1882ab6711b49f335d42375b424a6cc35b6c": (565, 983, 1208),
}


class _Pairs(list):
    """Distinguish JSON object pairs from arrays until duplicates are retained."""


def _path(parent: str, key: str) -> str:
    return parent + ("." + key if key.isidentifier() else "[" + json.dumps(key) + "]")


def _issue(out: list, code: str, path: str, *, severity="error", **detail) -> None:
    out.append({"code": code, "path": path, "severity": severity, **detail})


def _parse_source(raw: bytes) -> tuple[dict, list, list, bytes]:
    digest = sha256(raw).hexdigest()
    derived = raw
    offsets = _COMMA_REMOVALS.get(digest, ())
    for offset in reversed(offsets):
        if derived[offset:offset + 1] != b"," or derived[offset + 1:].lstrip()[:1] not in (b"}", b"]"):
            raise ValueError("retained source correction does not match")
        derived = derived[:offset] + derived[offset + 1:]
    corrections = []
    if offsets:
        corrections.append({
            "code": "remove_retained_source_trailing_commas",
            "byte_offsets": list(offsets), "original_sha256": digest,
            "derived_sha256": sha256(derived).hexdigest(),
        })

    def reject_constant(value):
        raise ValueError("nonfinite JSON constant: " + value)

    parsed = json.loads(derived, object_pairs_hook=_Pairs, parse_constant=reject_constant)
    duplicates = []

    def materialize(node, path):
        if isinstance(node, _Pairs):
            result, occurrences = {}, {}
            for key, value in node:
                item = materialize(value, _path(path, key))
                occurrences.setdefault(key, []).append(item)
                result[key] = item
            for key, values in occurrences.items():
                if len(values) > 1:
                    duplicates.append({"path": _path(path, key), "key": key, "values": values})
            return result
        if isinstance(node, list):
            return [materialize(value, f"{path}[{i}]") for i, value in enumerate(node)]
        return node

    definition = materialize(parsed, "$.definition")
    if not isinstance(definition, dict):
        raise ValueError("definition must be a JSON object")
    return definition, corrections, duplicates, derived


def get_application_spec(required_id: str) -> dict:
    """Return a fresh source-backed envelope for the retained Homology identity.

    Raises ValueError for an unknown identity, and OSError/ValueError if retained
    package data is missing or inconsistent. The definition parameter list is
    never flattened, so repeated declarations remain available to consumers.
    """
    if not isinstance(required_id, str) or required_id not in REQUIRED_APPLICATION_IDS:
        raise ValueError("unknown required BV-BRC application identity")
    manifest = json.loads((_SPECS / "MANIFEST.json").read_text())
    entry = manifest[required_id]
    original_path = _SPECS / entry["original_file"]
    raw = original_path.read_bytes()
    if sha256(raw).hexdigest() != entry["source"]["sha256"]:
        raise ValueError("retained application definition hash mismatch")
    definition, corrections, duplicates, derived = _parse_source(raw)
    if (derived != (_SPECS / entry["derived_file"]).read_bytes()
            or sha256(derived).hexdigest() != entry["derived_sha256"]
            or corrections != entry["parse_corrections"]
            or definition.get("id") != entry["native_id"]):
        raise ValueError("retained application definition derivation mismatch")
    return {
        "required_id": required_id, "native_id": entry["native_id"],
        "definition": definition,
        "source": {**deepcopy(entry["source"]), "kind": "official_repository_source",
                   "retained_path": str(original_path), "content": raw.decode("utf-8")},
        "parse_corrections": corrections, "duplicate_object_keys": duplicates,
    }


def _json_issues(value: Any, path: str, out: list, ancestors=None) -> None:
    """Do not silently coerce tuples, non-string keys, NaN, or Python objects."""
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            _issue(out, "nonfinite_number", path)
        return
    if type(value) not in (dict, list):
        _issue(out, "not_json_value", path)
        return
    ancestors = set() if ancestors is None else ancestors
    if id(value) in ancestors:
        _issue(out, "cyclic_value", path)
        return
    ancestors.add(id(value))
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                _issue(out, "non_string_key", path)
            else:
                _json_issues(item, _path(path, key), out, ancestors)
    else:
        for i, item in enumerate(value):
            _json_issues(item, f"{path}[{i}]", out, ancestors)
    ancestors.remove(id(value))


def _empty(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip()) or value == [] or value == {}


def _same_json(a, b) -> bool:
    # In particular, True must not equal 1 and 5000000 must not equal "5000000".
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def _enum_equal(a, b) -> bool:
    if type(a) in (int, float) and type(b) in (int, float):
        return a == b
    return _same_json(a, b)


def _validate_envelope(required_id, spec, out):
    if not isinstance(spec, dict):
        _issue(out, "definition_envelope_required", "$.definition")
        return None
    if spec.get("required_id") != required_id:
        _issue(out, "required_identity_mismatch", "$.definition.required_id")
    native_id = spec.get("native_id")
    accepted_ids = {required_id}
    if required_id == "InfluenzaHASubtypeConversion":
        accepted_ids.add("HASubtypeNumberingConversion")
    if not isinstance(native_id, str) or native_id not in accepted_ids:
        _issue(out, "unresolved_native_identity", "$.definition.native_id")
    source = spec.get("source")
    if not isinstance(source, dict):
        _issue(out, "source_provenance_required", "$.definition.source")
        return None
    for key in ("kind", "url", "sha256", "content"):
        if not isinstance(source.get(key), str) or not source[key]:
            _issue(out, "source_provenance_required", "$.definition.source." + key)
    if source.get("kind") not in ("official_repository_source", "retained_service_definition"):
        _issue(out, "unsupported_definition_source", "$.definition.source.kind")
    content = source.get("content")
    if not isinstance(content, str):
        return None
    try:
        raw = content.encode("utf-8")
        parsed, corrections, duplicates, _ = _parse_source(raw)
    except (ValueError, UnicodeError):
        _issue(out, "invalid_definition_json", "$.definition.source.content")
        return None
    if sha256(raw).hexdigest() != source.get("sha256"):
        _issue(out, "definition_source_hash_mismatch", "$.definition.source.sha256")
    if not _same_json(parsed, spec.get("definition")):
        _issue(out, "definition_source_content_mismatch", "$.definition.definition")
    if corrections != spec.get("parse_corrections", []):
        _issue(out, "definition_parse_corrections_mismatch", "$.definition.parse_corrections")
    if duplicates != spec.get("duplicate_object_keys", []):
        _issue(out, "definition_duplicate_members_mismatch", "$.definition.duplicate_object_keys")
    if parsed.get("id") != native_id:
        _issue(out, "definition_native_identity_mismatch", "$.definition.definition.id")
    if source.get("kind") == "official_repository_source":
        expected = get_application_spec(required_id)
        for key in ("url", "sha256", "git_tree_sha", "git_blob_sha"):
            if source.get(key) != expected["source"].get(key):
                _issue(out, "official_source_provenance_mismatch", "$.definition.source." + key)
        _issue(out, "deployment_not_verified", "$.definition.source", severity="qualification")
    else:
        _issue(out, "definition_custody_requires_caller_verification", "$.definition.source", severity="qualification")
    if native_id != required_id:
        _issue(out, "source_native_identity_mapping", "$.definition.native_id", severity="qualification",
               required_id=required_id, native_id=native_id)
    for correction in corrections:
        _issue(out, correction["code"], "$.definition.source.content", severity="qualification",
               byte_offsets=correction["byte_offsets"])
    for duplicate in duplicates:
        # Exact observed source pair: the enum is retained, and the producer
        # consumes code as genetic_code (0 is its taxonomic lookup sentinel).
        compatible = (required_id == "GenomeAnnotation"
                      and source.get("sha256") == "cd1847bd017283dfdacd7b5836a62b8bb68a336113f1f77f0e7ada9e4b735b49"
                      and duplicate["path"] == "$.definition.parameters[3].type"
                      and duplicate["values"] == ["enum", "int"])
        identical = all(_same_json(duplicate["values"][0], x) for x in duplicate["values"][1:])
        _issue(out, "duplicate_definition_member", duplicate["path"],
               severity="qualification" if compatible or identical else "error",
               values=duplicate["values"])
    return parsed


def _workspace_string(value, path, out):
    # Workspace resolution, ACL, object type, and content need acquisition.
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        _issue(out, "invalid_workspace_reference", path)
    else:
        _issue(out, "workspace_reference_unverified", path, severity="qualification")


def _validate_scalar(value, declaration, path, out):
    kind = declaration.get("type")
    choices = declaration.get("enum")
    if isinstance(choices, list) and not any(_enum_equal(value, x) for x in choices):
        _issue(out, "value_not_in_native_enum", path, allowed=deepcopy(choices))
    if isinstance(kind, list):
        if not any(_same_json(value, x) for x in kind):
            _issue(out, "value_not_in_native_type_choices", path, allowed=deepcopy(kind))
    elif kind in ("int", "integer"):
        if type(value) is not int:
            _issue(out, "expected_integer", path)
    elif kind == "float":
        if type(value) not in (int, float) or not math.isfinite(value):
            _issue(out, "expected_finite_number", path)
    elif kind in ("bool", "boolean"):
        if not (type(value) is bool or (type(value) is int and value in (0, 1))):
            _issue(out, "expected_boolean_or_native_zero_one", path)
    elif kind == "string":
        if not isinstance(value, str):
            _issue(out, "expected_string", path)
    elif kind in ("wstype", "wsid", "folder"):
        _workspace_string(value, path, out)
    elif kind in ("list", "array"):
        if not isinstance(value, list):
            _issue(out, "expected_array", path)
        elif not declaration.get("wstype"):
            _issue(out, "array_item_schema_unvalidated", path, severity="qualification")
        else:
            for i, item in enumerate(value):
                _workspace_string(item, f"{path}[{i}]", out)
    elif kind == "enum" or (kind is None and isinstance(choices, list)):
        if not isinstance(choices, list):
            _issue(out, "missing_native_enum_choices", path)
    else:
        _issue(out, "native_type_unvalidated", path, severity="qualification", native_type=kind)


def _validate_parameters(values, declarations, path, out, required_id, *, known_source=True):
    if not isinstance(declarations, list):
        _issue(out, "missing_parameter_declarations", "$.definition.parameters")
        return
    declared = {}
    for i, declaration in enumerate(declarations):
        if isinstance(declaration, dict) and set(declaration) == {"comment"}:
            continue
        if not isinstance(declaration, dict) or not isinstance(declaration.get("id"), str):
            _issue(out, "malformed_parameter_declaration", f"$.definition.parameters[{i}]")
            continue
        name = declaration["id"]
        declared.setdefault(name, []).append(declaration)
        field = _path(path, name)
        for flag in ("required", "allow_multiple"):
            if flag in declaration and not (type(declaration[flag]) is bool or
                    (type(declaration[flag]) is int and declaration[flag] in (0, 1))):
                _issue(out, "invalid_native_declaration_flag", field, declaration_field=flag)
        if name not in values or _empty(values[name]):
            if declaration.get("required") in (1, True):
                _issue(out, "required_parameter_missing", field)
            if name not in values:
                continue
        value = values[name]
        if value is None and declaration.get("default", object()) is None:
            _issue(out, "explicit_null_preserved", field, severity="qualification")
            continue
        kind = declaration.get("type")
        if kind == "group":
            array = declaration.get("allow_multiple") in (1, True)
            if array:
                if not isinstance(value, list):
                    _issue(out, "expected_group_array", field)
                    continue
                entries = [(f"{field}[{i}]", item) for i, item in enumerate(value)]
            else:
                entries = [(field, value)]
            for item_path, item in entries:
                if not isinstance(item, dict):
                    _issue(out, "expected_group_object", item_path)
                elif isinstance(declaration.get("group"), list):
                    _validate_parameters(item, declaration["group"], item_path, out, required_id,
                                         known_source=known_source)
                else:
                    _issue(out, "group_members_unvalidated", item_path, severity="qualification")
        elif not known_source and isinstance(kind, list) and not isinstance(value, str):
            _issue(out, "native_type_union_shape_unvalidated", field, severity="qualification")
        elif declaration.get("allow_multiple") in (1, True) and kind not in ("list", "array"):
            if not isinstance(value, list):
                _issue(out, "expected_array", field)
            else:
                for i, item in enumerate(value):
                    _validate_scalar(item, declaration, f"{field}[{i}]", out)
        else:
            _validate_scalar(value, declaration, field, out)
    for name, copies in declared.items():
        if len(copies) > 1:
            # No declaration wins. Every supplied value is checked against all
            # declarations, and every required declaration remains effective.
            _issue(out, "duplicate_parameter_declaration", _path(path, name), severity="qualification",
                   declarations=deepcopy(copies))
    for name in values.keys() - declared.keys():
        _issue(out, "unknown_parameter_unvalidated", _path(path, name), severity="qualification")


def _check_application_inputs(required_id, p, out):
    """Concrete input relationships from definitions and retained producers."""
    def need(name):
        if name not in p or _empty(p[name]):
            _issue(out, "selected_input_missing", _path("$.parameters", name))

    def any_input(*names):
        if not any(name in p and not _empty(p[name]) for name in names):
            _issue(out, "input_required", "$.parameters", alternatives=list(names))

    def selected(selector, choices):
        key = p.get(selector)
        if isinstance(key, str) and key in choices:
            for name in choices[key]:
                need(name)

    if required_id == "Homology":
        selected("input_source", {
            "id_list": ("input_id_list",), "fasta_data": ("input_fasta_data",),
            "fasta_file": ("input_fasta_file",), "feature_group": ("input_feature_group",),
            "genome_group_features": ("input_genome_group",), "genome_group_sequences": ("input_genome_group",),
        })
        selected("db_source", {
            "id_list": ("db_id_list",), "fasta_data": ("db_fasta_data",),
            "fasta_file": ("db_fasta_file",), "genome_list": ("db_genome_list",),
            "taxon_list": ("db_taxon_list",), "feature_group": ("db_feature_group",),
            "genome_group": ("db_genome_group",), "precomputed_database": ("db_precomputed_database",),
        })


def prepare_application(required_id, parameters, start_parameters, *, definition=None) -> dict:
    """Validate an explicit assignment and preserve its exact start_app2 operands.

    This function checks structure and retained source constraints, not remote
    existence, permissions, input file contents, biological suitability, or
    deployed availability. Inspect qualifications even when status is ``ok``.
    """
    diagnostics = []
    if not isinstance(required_id, str) or required_id not in REQUIRED_APPLICATION_IDS:
        return {"status": "invalid", "value": None, "diagnostics": [
            {"code": "unknown_required_application", "path": "$.required_id", "severity": "error"}]}
    for name, value in (("parameters", parameters), ("start_parameters", start_parameters)):
        _json_issues(value, "$." + name, diagnostics)
        if not isinstance(value, dict):
            _issue(diagnostics, "expected_object", "$." + name)
    if diagnostics:
        return {"status": "invalid", "value": None, "diagnostics": diagnostics}
    try:
        spec = get_application_spec(required_id) if definition is None else definition
        _json_issues(spec, "$.definition", diagnostics)
        parsed = None if diagnostics else _validate_envelope(required_id, spec, diagnostics)
    except (OSError, ValueError, KeyError) as exc:
        _issue(diagnostics, "retained_definition_unavailable", "$.definition", reason=type(exc).__name__)
        parsed = None
    for item in validate_start_parameters(start_parameters):
        diagnostics.append({**item, "severity": "error"})
    if parsed is not None:
        known_source = spec["source"].get("sha256") == get_application_spec(required_id)["source"]["sha256"]
        _validate_parameters(parameters, parsed.get("parameters"), "$.parameters", diagnostics, required_id,
                             known_source=known_source)
        if known_source:
            _check_application_inputs(required_id, parameters, diagnostics)
        else:
            _issue(diagnostics, "producer_binding_unverified_for_definition", "$.definition.source",
                   severity="qualification")
        # The output destination belongs to the supplied assignment. Never
        # infer a parent folder or rewrite an original output basename.
        for name in ("output_path", "output_file"):
            if name in parameters and not _empty(parameters[name]):
                if not isinstance(parameters[name], str):
                    continue
                if name == "output_file" and ("/" in parameters[name] or parameters[name] in (".", "..")):
                    _issue(diagnostics, "output_basename_required", "$.parameters.output_file")
            elif required_id == "GenomeAnnotation" and parameters.get("skip_workspace_output") not in (True, 1):
                _issue(diagnostics, "output_destination_not_supplied", "$.parameters." + name,
                       severity="qualification")
        _issue(diagnostics, "input_contents_and_reference_release_unverified", "$.parameters", severity="qualification")
    invalid = parsed is None or any(item["severity"] == "error" for item in diagnostics)
    value = None if invalid else {
        "required_id": required_id,
        "native_application_id": spec["native_id"],
        "native_params": [spec["native_id"], deepcopy(parameters), deepcopy(start_parameters)],
    }
    return {"status": "invalid" if invalid else "ok", "value": value, "diagnostics": diagnostics}
