"""Original protein typed fact identities, boundary conversion and descriptor reference selection."""
from __future__ import annotations

from functools import wraps
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_authority import ProteinStructureOperandError
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_contracts import issue, validate_saved_sheet_descriptor, validate_structure_sequence_descriptor
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_result_views import validate_protein_structure_failure_return, validate_protein_structure_projection_result
from gene_annotation_episode.episodic_workflow.root.communication import plain
from typing import Literal


PROJECTION_SOURCE = "execution_protein_structure_projections"
SAVED_SOURCE = "execution_protein_structure_saved_sheets"
SEQUENCE_SOURCE = "execution_protein_structure_sequences"
FAILURE_SOURCE = "execution_protein_structure_failures"
FACT_SOURCES = (PROJECTION_SOURCE, SAVED_SOURCE, SEQUENCE_SOURCE, FAILURE_SOURCE)
GENERIC_SOURCE = "execution_result_refs"
SequenceUse = Literal["sequence_align", "structure_correspondence"]
SavedSheetUse = Literal["recalculate", "select_projection", "use_transform"]
_ASSIGNED_ROLES = {"launch", "launch_api", "launch_local", "launch_hpc", "results",
                   "job_launch", "job_results"}
_VALIDATORS = {
    PROJECTION_SOURCE: validate_protein_structure_projection_result,
    SAVED_SOURCE: validate_saved_sheet_descriptor,
    SEQUENCE_SOURCE: validate_structure_sequence_descriptor,
    FAILURE_SOURCE: validate_protein_structure_failure_return,
}


def _error(code="original_commission_mismatch", *, field="receipt", stage="authority"):
    return ProteinStructureOperandError(issue(code, stage=stage, field=field))


def _boundary(function):
    """Do not expose unrelated implementation error strings as science codes."""
    @wraps(function)
    def call(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except ProteinStructureOperandError:
            raise
        except (ValueError, KeyError, TypeError, IndexError, OverflowError) as error:
            raise _error() from error
    return call


def _validate(function, value):
    try:
        return function(plain(value))
    except (ValueError, KeyError, TypeError, OverflowError) as error:
        raise _error("invalid_schema", field="descriptor") from error


def requested_sources(schema: dict) -> tuple[str, ...]:
    selected = {node.get("x-source") for node in plain(schema).get("properties", {}).values()
                if isinstance(node, dict)}
    return tuple(source for source in FACT_SOURCES if source in selected)


def _custody_refs(custody):
    return [custody[key] for key in ("handoff_ref", "source_ref", "bundle_artifact_ref")]


def _sequence_refs(descriptor):
    return [descriptor["reference_ref"],
            *(descriptor[key]["artifact_ref"] for key in
              ("sequence_file", "residue_map_file", "structure_file")),
            *_custody_refs(descriptor["custody"])]


def _saved_refs(descriptor):
    return [*_custody_refs(descriptor["custody"]), descriptor["sheet_file"]["artifact_ref"],
            descriptor["original_components_file"]["artifact_ref"]]


def _sequences(values):
    """Only explicit values cells contain delivered embedded descriptors."""
    for source in FACT_SOURCES:
        for value in values.get(source, []):
            if source == SEQUENCE_SOURCE:
                yield value
            elif source == PROJECTION_SOURCE and value["family"] == "extracted_sequence" \
                    and value["delivery"]["kind"] == "values":
                for row in value["delivery"]["rows"]:
                    for selected in row["values"]:
                        if selected["field"] == "descriptor" and selected["value"] is not None:
                            yield selected["value"]


def _references(values):
    references = [ref for descriptor in _sequences(values) for ref in _sequence_refs(descriptor)]
    references.extend(ref for value in values.get(SAVED_SOURCE, []) for ref in _saved_refs(value))
    references.extend(value["delivery"]["table_file"]["artifact_ref"]
                      for value in values.get(PROJECTION_SOURCE, [])
                      if value["delivery"]["kind"] == "artifact")
    return list(dict.fromkeys(references))


