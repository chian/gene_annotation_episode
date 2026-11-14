"""Custody of complete tool grading outputs beside their original artifacts.

This module stores and resolves supplied results. It performs no scientific
calculation, acquisition, job selection, observation publication or credit
assignment. Graders remain ordinary pure functions in their own modules.
"""
from __future__ import annotations

from collections.abc import Mapping
import json

from .domain import canonical
from gene_annotation_episode.domain import ContractError


SCHEMA = "tool_grading_artifact_v1"
SCHEMA_V2 = "tool_grading_artifact_v2"
MEDIA_TYPE = "application/vnd.gene-annotation.tool-grading+json"


def retain_tool_grading(store, *, provider: str, native_artifact_ref: str,
                        grading: dict) -> str:
    """Retain a full numerical sheet/calculation result without another record."""
    if not isinstance(provider, str) or not provider or not isinstance(grading, Mapping):
        raise ContractError("tool_grading_provider_and_result_required")
    if store.get(native_artifact_ref).get("record_type") != "artifact":
        raise ContractError("tool_grading_native_artifact_required")
    grading = dict(grading)
    correspondence = grading.pop("correspondence", None)
    body = {"schema": SCHEMA, "provider": provider,
            "native_artifact_ref": native_artifact_ref, "grading": grading}
    if correspondence is not None:
        raise ContractError("tool_grading_unexpected_correspondence")
    return store.artifact(canonical(body), MEDIA_TYPE)


def source_tool_grading_entries(store, source_ref: str) -> list[dict]:
    """Resolve exact retained artifact addresses and their validated grading.

    The caller owns receipt/scope qualification before calling this host helper.
    Neither a source handle nor this function grants a child access to new data.
    Legacy sources without grading artifacts return an empty list.
    """
    source = store.get(source_ref)
    if source.get("record_type") != "source":
        raise ContractError("tool_grading_source_required")
    results = []
    for reference in source.get("auxiliary_artifact_refs", ()):
        artifact = store.get(reference)
        if artifact.get("media_type") != MEDIA_TYPE:
            continue
        try:
            body = json.loads(store.get_artifact(reference))
            fields = {"schema", "provider", "native_artifact_ref", "grading"}
            if (not isinstance(body, dict) or set(body) != fields
                    or body["schema"] != SCHEMA
                    or body["provider"] != source["provider"]
                    or body["native_artifact_ref"] != source["artifact_ref"]
                    or not isinstance(body["grading"], dict)):
                raise ContractError("tool_grading_source_custody_mismatch")
            canonical(body)
        except (ValueError, TypeError, KeyError, IndexError) as error:
            if isinstance(error, ContractError):
                raise
            raise ContractError("invalid_tool_grading_artifact") from error
        results.append({"artifact_ref": reference, "grading": body["grading"]})
    return results


def source_tool_gradings(store, source_ref: str) -> list[dict]:
    """Keep the grading-only view for existing consumers."""
    return [entry["grading"] for entry in source_tool_grading_entries(store, source_ref)]


__all__ = ["retain_tool_grading", "source_tool_gradings", "source_tool_grading_entries", "SCHEMA", "SCHEMA_V2", "MEDIA_TYPE"]
