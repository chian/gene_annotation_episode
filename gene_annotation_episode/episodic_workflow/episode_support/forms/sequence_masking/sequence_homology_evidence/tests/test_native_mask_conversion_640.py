"""Converter invocation and custody through the existing masking producer.

Process outcomes are controlled test replacements using retained 636 bytes.
These tests establish command/custody behavior, not a new native execution or
scientific measurement. Actual Workflow execution is verified separately.
"""
from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_masking.sequence_homology_evidence import native_blast_masking_driver as driver
from gene_annotation_episode.episodic_workflow.episode_support.jobs.sequence_masking.sequence_homology_evidence import native_blast_masking_local as local
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.sequence_homology_evidence.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_masking.sequence_homology_evidence.native_blast_masking_contracts import ATTEMPT_NAME, BUNDLE_VERSION, MODES, NATIVE_BLAST_MASKING_JOB_SCHEMA, NATIVE_BLAST_MASKING_REQUESTED_JOB_SCHEMA, PLAN_VERSION, compile_native_blast_masking_job, native_blast_digest as digest, requested_job_from_native_blast_masking, validate_native_blast_masking_job, validate_native_blast_masking_requested_job, validate_original_bundle
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_masking.sequence_homology_evidence.native_blast_masking_tool_info import (
    native_blast_masking_tool_contracts, validate_native_blast_masking_bindings,
)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_masking.sequence_homology_evidence.sequence_masking_contracts import sequence_masking_molecule
from gene_annotation_episode.state import Store


ROOT = Path(__file__).resolve().parents[7]
RETAINED = ROOT / "gene_annotation_episode/episodic_workflow/episode_support/forms/sequence_masking/sequence_homology_evidence/tests/fixtures/blast_mask_conversion/outputs"
POLICY = {'memory_bytes': ENVIRONMENT_BOUNDS['memory_bytes'], 'scratch_bytes': 4 * 1024 ** 3}
FORMATS = ("maskinfo_xml", "maskinfo_asn1_text", "maskinfo_asn1_bin", "interval")
DNA = b">duplicate\nAAaaGG\n>duplicate\nttCCaa\n"
PROTEIN = b">protein_a\nMKWVtfISLLflFSSaysR\n"


def pin(path):
    content = path.read_bytes()
    return {"sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)}


def conversion_job(tmp_path, *, molecule="dna", fmt="maskinfo_xml", parse_seqids=True,
        engine_version=None, content=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    binary = tmp_path / "convert2blastmask-controlled"
    binary.write_bytes(b"controlled process replacement; never executed\n")
    binary.chmod(0o700)
    source = tmp_path / "supplied.fa"
    source.write_bytes(content if content is not None else PROTEIN if molecule == "protein" else DNA)
    return {"version": "native_blast_masking_job", "operation": {
        "version": "sequence_masking_operation", "program": "convert2blastmask", "mode": "convert_mask",
        "engine_version": engine_version, "input_format": "fasta", "input_mask_basis": "lowercase_input",
        "molecule": molecule, "output_format": fmt, "masking_style": "interval", "parse_seqids": parse_seqids,
        # Deliberately reversed mapping order: compilation uses the shared schema.
        "requested_parameters": {"masking_options": "", "masking_algorithm": "DuSt"}},
        "software": {"executable": str(binary), "sha256": pin(binary)["sha256"], "engine_version": engine_version},
        "environment": {"BLAST_USAGE_REPORT": "false", "NCBI_DONT_USE_NCBIRC": "1", "LC_ALL": "C"},
        "operands": [{"role": "sequences", "ordinal": 0, "path": str(source), "format": "fasta",
                      **pin(source), "artifact_ref": None}],
        "operand_bindings": [{"operand_role": "sequences", "operand_ordinal": 0, "record_ordinal": 0,
                              "source_record_ref": "sequence_supplied_first"}],
        "statistics_binding": None,
        "outputs": [{"role": "mask", "format": fmt, "relative_path": "selected.mask"},
                    {"role": "stdout", "format": "text", "relative_path": "stdout.txt"},
                    {"role": "stderr", "format": "text", "relative_path": "stderr.txt"}]}


@pytest.mark.parametrize("molecule", ["dna", "protein"])
@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("parse_seqids", [False, True])
@pytest.mark.parametrize("engine_version", [None, "2.17.0+"])
def test_exact_converter_argv_from_shared_schema(tmp_path, molecule, fmt, parse_seqids, engine_version):
    assert ("convert2blastmask", "convert_mask") in MODES
    job = conversion_job(tmp_path, molecule=molecule, fmt=fmt, parse_seqids=parse_seqids, engine_version=engine_version)
    assert Draft202012Validator(NATIVE_BLAST_MASKING_JOB_SCHEMA).is_valid(job)
    assert sequence_masking_molecule(job["operation"]) == molecule
    request = requested_job_from_native_blast_masking(job)
    expected = [job["software"]["executable"], "-in", job["operands"][0]["path"], "-outfmt", fmt]
    if parse_seqids:
        expected.append("-parse_seqids")
    expected += ["-masking_algorithm", "DuSt", "-masking_options", "", "-out", "selected.mask"]
    assert request["argv"] == expected
    assert Draft202012Validator(NATIVE_BLAST_MASKING_REQUESTED_JOB_SCHEMA).is_valid(request)
    assert validate_native_blast_masking_requested_job(request) == request
    options = 'caller supplied; "$HOME"\n-level 12\tunaltered'
    job["operation"]["requested_parameters"]["masking_options"] = options
    argv = compile_native_blast_masking_job(job, input_paths={"sequences": "/staged/exact-case.fa"}, output_directory="/out")
    assert argv == [*expected[:2], "/staged/exact-case.fa", *expected[3:-3], options, "-out", "/out/selected.mask"]
    assert not {"-infmt", "-molecule", "-hard_masking", "-dust", "-ustat"} & set(argv)


@pytest.mark.parametrize("fault", ["molecule_missing", "molecule_rna", "mask_basis_missing", "mask_basis_wrong",
    "algorithm_missing", "algorithm_null", "algorithm_empty", "algorithm_nul", "options_missing", "options_null",
    "options_nul", "extra_parameter", "wrong_mode", "fasta_output", "wrong_style", "output_format_mismatch"])
def test_converter_rejects_unselected_or_incomplete_inputs(tmp_path, fault):
    job = conversion_job(tmp_path)
    operation, parameters = job["operation"], job["operation"]["requested_parameters"]
    if fault == "molecule_missing": del operation["molecule"]
    elif fault == "molecule_rna": operation["molecule"] = "rna"
    elif fault == "mask_basis_missing": del operation["input_mask_basis"]
    elif fault == "mask_basis_wrong": operation["input_mask_basis"] = "detected"
    elif fault == "algorithm_missing": del parameters["masking_algorithm"]
    elif fault == "algorithm_null": parameters["masking_algorithm"] = None
    elif fault == "algorithm_empty": parameters["masking_algorithm"] = ""
    elif fault == "algorithm_nul": parameters["masking_algorithm"] = "dust\0"
    elif fault == "options_missing": del parameters["masking_options"]
    elif fault == "options_null": parameters["masking_options"] = None
    elif fault == "options_nul": parameters["masking_options"] = "a\0b"
    elif fault == "extra_parameter": parameters["level"] = 20
    elif fault == "wrong_mode": operation["mode"] = "mask"
    elif fault == "fasta_output": operation["output_format"] = "fasta"
    elif fault == "wrong_style": operation["masking_style"] = "soft"
    elif fault == "output_format_mismatch": job["outputs"][0]["format"] = "maskinfo_asn1_bin"
    with pytest.raises(ValueError):
        validate_native_blast_masking_job(job)


@pytest.mark.parametrize("fmt", FORMATS)
def test_converter_tool_information_is_configured_and_does_not_claim_detection(tmp_path, fmt):
    job = conversion_job(tmp_path, fmt=fmt)
    binding = {"program": "convert2blastmask", "mode": "convert_mask", "software": job["software"],
        "output_formats": [fmt], "masking_styles": ["interval"]}
    assert validate_native_blast_masking_bindings([binding]) == [binding]
    info = native_blast_masking_tool_contracts([binding], resource_kind="local", resource_id="local640")[0]
    assert info["name"] == "native.convert2blastmask.convert_mask"
    assert info["invocation_route"]["routes"] == [{"entry_role": "launch", "resource_id": "local640", "resource_role": "launch_local"}]
    assert Draft202012Validator(info["input_schema"]).is_valid(requested_job_from_native_blast_masking(job))
    instructions = info["instructions"]
    assert "lowercase_input" in instructions and "without running DUST" in instructions
    assert "both are required and non-null" in instructions and "no native default is inserted" in instructions
    assert "is not an inherited mask" not in instructions and "null omits" not in instructions
    if fmt == "maskinfo_asn1_bin":
        assert "reader is explicitly unavailable" in instructions
    else:
        assert "ASN.1 binary bytes can be acquired" not in instructions
    for wrong_format in set(FORMATS) - {fmt}:
        wrong = deepcopy(job)
        wrong["operation"]["output_format"] = wrong["outputs"][0]["format"] = wrong_format
        assert not Draft202012Validator(info["input_schema"]).is_valid(requested_job_from_native_blast_masking(wrong))
    for formats, styles in [(["fasta"], ["soft"]), ([fmt], ["hard"]), (["ascii_statistics"], ["not_applicable"])]:
        with pytest.raises(ValueError):
            validate_native_blast_masking_bindings([{**binding, "output_formats": formats, "masking_styles": styles}])


