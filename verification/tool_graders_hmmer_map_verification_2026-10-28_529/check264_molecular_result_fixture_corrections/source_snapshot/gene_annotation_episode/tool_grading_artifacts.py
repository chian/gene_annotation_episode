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
SCHEMA_V2 = "tool_grading_artifact_v2"
MEDIA_TYPE = "application/vnd.gene-annotation.tool-grading+json"


def _required_correspondence(grading):
    schema = grading.get("sheet", {}).get("schema") if isinstance(grading.get("sheet"), dict) else None
    return schema in {"biopython_pairwise_sheet_v1", "blast_pairwise_sheet_v1",
        "blast_database_sheet_v1", "blast_database_sheet_v2", "blast_database_sheet_v3"}


def validate_tool_correspondence(grading, correspondence, *, admission=False):
    from .alignment_correspondence import validate_correspondence_artifacts
    from .biopython_pairwise_grader import validate_biopython_correspondence
    from .blast_pairwise_grader import validate_blast_correspondence_instance
    correspondence = validate_correspondence_artifacts(correspondence, admission=admission)
    schema = grading["sheet"]["schema"]
    instances = correspondence["instances"]
    if schema == "biopython_pairwise_sheet_v1":
        if len(instances) != 1:
            raise ValueError("tool_grading_correspondence_instances_conflict")
        validate_biopython_correspondence(grading, instances[0])
    else:
        expected = ([('/sheet', grading['sheet'])] if schema == 'blast_pairwise_sheet_v1' else
            [('/sheet/hits/' + str(i), hit) for i, hit in enumerate(grading['sheet']['hits'])])
        if len(instances) != len(expected):
            raise ValueError("tool_grading_correspondence_instances_conflict")
        for instance, (pointer, legacy) in zip(instances, expected):
            if instance['legacy_pointer'] != pointer or instance['axis_basis'] != 'reported':
                raise ValueError("tool_grading_correspondence_address_conflict")
            program = grading["sheet"].get("normalized_result", {}).get("search", {}).get("program")
            validate_blast_correspondence_instance(legacy, instance, program=program)


def retain_tool_grading(store, *, provider: str, native_artifact_ref: str,
                        grading: dict) -> str:
    """Retain a full numerical sheet/calculation result without another record."""
    if not isinstance(provider, str) or not provider or not isinstance(grading, Mapping):
        raise ContractError("tool_grading_provider_and_result_required")
    if store.get(native_artifact_ref).get("record_type") != "artifact":
        raise ContractError("tool_grading_native_artifact_required")
    grading = dict(grading)
    correspondence = grading.pop("correspondence", None)
    body = {"schema": SCHEMA_V2 if correspondence is not None else SCHEMA, "provider": provider,
            "native_artifact_ref": native_artifact_ref, "grading": grading}
    if _required_correspondence(grading):
        if correspondence is None:
            raise ContractError("tool_grading_correspondence_required")
        try:
            validate_tool_correspondence(grading, correspondence, admission=True)
        except (ValueError, KeyError, TypeError, IndexError) as error:
            raise ContractError("tool_grading_correspondence_conflict") from error
    elif correspondence is not None:
        raise ContractError("tool_grading_unexpected_correspondence")
    if correspondence is not None:
        body["correspondence"] = correspondence
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
            if isinstance(body, dict) and body.get("schema") == SCHEMA_V2:
                fields.add("correspondence")
            if (not isinstance(body, dict) or set(body) != fields
                    or body["schema"] not in (SCHEMA, SCHEMA_V2)
                    or body["provider"] != source["provider"]
                    or body["native_artifact_ref"] != source["artifact_ref"]
                    or not isinstance(body["grading"], dict)):
                raise ContractError("tool_grading_source_custody_mismatch")
            if body["schema"] == SCHEMA_V2:
                if not _required_correspondence(body["grading"]):
                    raise ContractError("tool_grading_unexpected_correspondence")
                validate_tool_correspondence(body["grading"], body["correspondence"])
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
