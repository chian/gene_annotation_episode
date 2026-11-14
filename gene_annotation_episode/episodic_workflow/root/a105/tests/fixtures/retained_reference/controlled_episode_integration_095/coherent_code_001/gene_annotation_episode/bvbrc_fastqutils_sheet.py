"""Retain native measurements and separately source-bound metadata."""
from copy import deepcopy

from .bvbrc_fastqutils_contracts import validate_contract, validate_metadata, validate_native_document, validate_sheet
from .bvbrc_fastqutils_identity import document_ref
from .bvbrc_fastqutils_metadata import _check, _escape, _requirement, _unique


def populate_fastqutils_sheet(documents: list[dict], *, metadata: dict,
                             document_resolutions: list[dict]) -> dict:
    validate_metadata(metadata)
    _check(type(documents) is list and type(document_resolutions) is list, "shape_invalid")
    documents = deepcopy(documents)
    for doc in documents:
        validate_native_document(doc)
    resolutions = [validate_contract("ResolvedDocument", r) for r in document_resolutions]
    _check(len({r["document_id"] for r in resolutions}) == len(resolutions), "duplicate_identity")
    docmap = {d["document_id"]: d for d in documents}
    _check(len(docmap) == len(documents), "duplicate_identity")
    _check(set(docmap) == {r["document_id"] for r in resolutions if r["state"] == "available"})
    for resolution in resolutions:
        if resolution["state"] == "available":
            doc = docmap[resolution["document_id"]]
            _check(resolution["artifact_ref"] == doc["artifact"]["id"] and
                   resolution["matched_contents"] == [doc["artifact"]["content_binding"]])
    requirements = []
    for resolution in resolutions:
        for code in resolution["diagnostic_codes"]:
            if resolution["state"] == "available":
                continue
            required = {"selection_ambiguous": "exact_source_cardinality", "unsupported_format": "supported_parser",
                        "unsupported_version": "native_version"}.get(code, "selected_document")
            if resolution["matched_contents"] and code == "missing_artifact":
                required = "complete_native_bytes"
            requirements.append(_requirement(metadata["analysis_id"], "/documents/" + _escape(resolution["document_id"]),
                code, required, [document_ref(metadata["analysis_id"], resolution["document_id"])],
                [c["source_ref"] for c in resolution["matched_contents"]],
                "incompatible" if resolution["state"] in {"ambiguous", "incompatible"} else "unavailable"))
    result = {k: deepcopy(metadata[k]) for k in ("analysis_id", "task_ref", "original_task", "libraries", "stages",
        "associations", "populations", "supplied_metadata", "native_lineage")}
    result.update(schema_version="fastqutils_sheet_v2", documents=documents, document_resolutions=resolutions,
        measurements=[deepcopy(r) for d in documents for r in d["cells"]] + deepcopy(metadata["measurements"]),
        categories=[deepcopy(r) for d in documents for r in d["categories"]],
        requirements=_unique(requirements + metadata["requirements"] + [r for d in documents for r in d["requirements"]]),
        diagnostics=_unique(metadata["diagnostics"] + [r for d in documents for r in d["diagnostics"]]))
    validate_sheet(result)
    return result


__all__ = ["populate_fastqutils_sheet"]
