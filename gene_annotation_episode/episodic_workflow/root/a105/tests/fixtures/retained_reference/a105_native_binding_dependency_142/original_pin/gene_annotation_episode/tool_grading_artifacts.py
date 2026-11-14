"""Custody of complete tool grading outputs beside their original artifacts.

This module stores and resolves supplied results. It performs no scientific
calculation, acquisition, job selection, observation publication or credit
assignment. Graders remain ordinary pure functions in their own modules.
"""
from __future__ import annotations

from collections.abc import Mapping
import json

from .domain import ContractError, canonical


SCHEMA = "tool_grading_artifact_v1"
MEDIA_TYPE = "application/vnd.gene-annotation.tool-grading+json"


def retain_tool_grading(store, *, provider: str, native_artifact_ref: str,
                        grading: dict) -> str:
    """Retain a full numerical sheet/calculation result without another record."""
    if not isinstance(provider, str) or not provider or not isinstance(grading, Mapping):
        raise ContractError("tool_grading_provider_and_result_required")
    if store.get(native_artifact_ref).get("record_type") != "artifact":
        raise ContractError("tool_grading_native_artifact_required")
    body = {"schema": SCHEMA, "provider": provider,
            "native_artifact_ref": native_artifact_ref, "grading": dict(grading)}
    return store.artifact(canonical(body), MEDIA_TYPE)


def source_tool_gradings(store, source_ref: str) -> list[dict]:
    """Resolve explicitly supplied source custody; discover no other sources.

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
            if (not isinstance(body, dict) or set(body) != {
                    "schema", "provider", "native_artifact_ref", "grading"}
                    or body["schema"] != SCHEMA
                    or body["provider"] != source["provider"]
                    or body["native_artifact_ref"] != source["artifact_ref"]
                    or not isinstance(body["grading"], dict)):
                raise ContractError("tool_grading_source_custody_mismatch")
            canonical(body)
        except (ValueError, TypeError) as error:
            if isinstance(error, ContractError):
                raise
            raise ContractError("invalid_tool_grading_artifact") from error
        results.append(body["grading"])
    return results


__all__ = ["retain_tool_grading", "source_tool_gradings", "SCHEMA", "MEDIA_TYPE"]
