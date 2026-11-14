"""A106 exact task-artifact and selected-member extraction."""
from copy import deepcopy

def _issue(code, path, *, severity="qualification"):
    return {"code": code, "path": path, "severity": severity}

def _diagnostic(code, path, refs=(), *, severity="qualification"):
    return {"code": code, "phase": "association", "path": path,
        "severity": severity, "evidence_refs": list(dict.fromkeys(refs))}

def _missing(specification, code, refs=()):
    return {"requirement_id": specification["requirement_id"], "kind": "parser_binding",
        "role": None, "source_refs": list(dict.fromkeys(refs)), "reason_code": code}

def _content(artifact):
    return {"source_ref": artifact["source_ref"], "artifact_field": "artifact_ref",
        "artifact_ref": artifact["raw_artifact_ref"], "sha256": artifact["sha256"],
        "byte_count": artifact["byte_count"]}

def _resolve(bundle, specification, artifact_bytes, *, parse_artifact, formats, family="intervention"):
    """Resolve one explicitly selected artifact using the shared task binding.

    Other application families supply their own reader and declared formats;
    this function owns no acquisition, Source custody or scientific calculation.
    """
    identifier = specification["document_id"]
    candidates = [artifact for artifact in bundle["artifacts"]
        if specification["requirement_id"] in artifact.get("requirement_ids", [])]
    refs = [artifact["source_ref"] for artifact in candidates]
    resolution = {"document_id": identifier, "specification": deepcopy(specification),
        "state": "missing", "candidate_contents": [_content(row) for row in candidates], "document": None}
    if len(candidates) != 1:
        code = family + ("_artifact_missing" if not candidates else "_artifact_ambiguous")
        resolution["state"] = "missing" if not candidates else "ambiguous"
        return resolution, [_missing(specification, code, refs)], [_diagnostic(code, "/documents/" + identifier, refs)]
    artifact, = candidates
    task = bundle["original_task"]
    association = artifact["task_association"]
    if (association["task_id"] != task["task_id"] or association["kind"] == "unverified_original_path"
            or artifact["declared_format"]["format"] not in formats[specification["representation"]]):
        resolution["state"] = "incompatible"
        code = family + "_artifact_task_or_format_conflict"
        return resolution, [_missing(specification, code, refs)], [_diagnostic(code, "/documents/" + identifier, refs, severity="error")]
    reference = artifact["raw_artifact_ref"]
    if reference not in artifact_bytes:
        code = family + "_artifact_bytes_missing"
        return resolution, [_missing(specification, code, refs)], [_diagnostic(code, "/documents/" + identifier, refs)]
    transfer = artifact["transfer"]
    document = parse_artifact(artifact_bytes[reference], content=_content(artifact),
        representation=specification["representation"],
        capture_complete=transfer["body_complete"] and transfer["object_complete"] == "yes",
        expected_task_id=task["task_id"])
    resolution.update(state="available", document=document)
    diagnostics = [_diagnostic(row["code"], row["path"], refs, severity=row["severity"])
        for row in document["issues"]]
    return resolution, [], diagnostics

def _record(value, ordinal, pointer, *, state=None):
    if state is None:
        state = "stored_null" if value is None or type(value) is dict and value.get("kind") == "null" else "available"
    return {"requested_ordinal": ordinal, "source_pointer": pointer,
        "state": state, "value": deepcopy(value)}

def _select_members(value, names, pointer):
    if names is None:
        return deepcopy(value), []
    if type(value) is not dict:
        return None, []
    return ({name: deepcopy(value[name]) for name in names if name in value},
        [_issue("selected_component_member_missing", pointer + "/" + name.replace("~", "~0").replace("/", "~1"))
            for name in names if name not in value])

