"""Exact retained envelope and live-source pin compatibility; no native jobs."""
import hashlib

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import biopython_pairwise_grader as pairwise
from gene_annotation_episode.episodic_workflow.root.library import native_protein_structure_worker as worker
from gene_annotation_episode.episodic_workflow.root.library import protein_structure_contracts as science
from gene_annotation_episode.execution_contracts import canonical


def envelope(version):
    # Explicit engineering traceback fixture, not a claimed native execution.
    native = {"native_format": "biopython_pairwise_native_v2", "aligned": True, "mode": "global",
        "query_length": 4, "reference_length": 4, "native_score": 19., "matrix": "BLOSUM62",
        "gap_open": -10., "gap_extend": -.5, "aligned_query": "AGST", "aligned_reference": "AGST",
        "query_interval": [0, 4], "reference_interval": [0, 4], "coordinates": [[0, 4], [0, 4]]}
    grading = pairwise.grade_biopython_pairwise(native, molecule="protein", _retain_correspondence=version == 2)
    companion = grading.pop("correspondence", None)
    result = {"schema": "tool_grading_artifact_v" + str(version), "provider": "biopython.alignment",
        "native_artifact_ref": "constructed-native-artifact", "grading": grading}
    if companion is not None:
        result["correspondence"] = companion
    return result


def descriptor(value):
    def identity(raw, format_name):
        digest = hashlib.sha256(raw).hexdigest()
        return dict(artifact_ref="artifact_" + digest, sha256=digest, byte_length=len(raw), format=format_name)
    native_file = identity(canonical(value["grading"]["sheet"]["native_result"]).encode(), "biopython_pairwise_json")
    value["native_artifact_ref"] = native_file["artifact_ref"]
    grading_file = identity(canonical(value).encode(), value["schema"])
    return dict(version="structure_alignment_descriptor_v1", observation_ref="observation_" + "a"*24,
        source_ref="source_" + "b"*24, original_operation_key="constructed-alignment",
        query_reference_ref="reference_" + "c"*24, reference_reference_ref="reference_" + "d"*24,
        native_file=native_file, grading_file=grading_file, molecule="protein", mode="global",
        traceback_selection="explicit_retained", producer_traceback_selection="first_native_optimal_returned",
        optimal_alternative_count=None)


@pytest.mark.parametrize("version", [1, 2])
def test_truthful_descriptor_schema_and_validator_admit_exact_outer_version(version):
    value = envelope(version)
    claimed = descriptor(value)
    schema = {"$defs": science.protein_structure_schema_definitions(), "$ref": "#/$defs/AlignmentDescriptor"}
    Draft202012Validator(schema).validate(claimed)
    assert science.validate_alignment_descriptor(claimed) == claimed
    result = worker._alignment_grading(value, native_artifact_ref=claimed["native_file"]["artifact_ref"],
        grading_format=claimed["grading_file"]["format"])
    assert result == value["grading"]
    with pytest.raises(ValueError, match="alignment_operand_mismatch"):
        worker._alignment_grading(value, native_artifact_ref=claimed["native_file"]["artifact_ref"],
            grading_format="tool_grading_artifact_v" + str(3-version))


def test_unknown_descriptor_and_outer_version_are_rejected():
    value = envelope(2)
    claimed = descriptor(value)
    claimed["grading_file"]["format"] = "tool_grading_artifact_v3"
    schema = {"$defs": science.protein_structure_schema_definitions(), "$ref": "#/$defs/AlignmentDescriptor"}
    assert not Draft202012Validator(schema).is_valid(claimed)
    with pytest.raises(ValueError, match="invalid_schema|unsupported_format"):
        science.validate_alignment_descriptor(claimed)
    value["schema"] = "tool_grading_artifact_v3"
    with pytest.raises(ValueError, match="invalid_traceback"):
        worker._alignment_grading(value, native_artifact_ref=claimed["native_file"]["artifact_ref"],
            grading_format=claimed["grading_file"]["format"])


