"""Saved-sheet oracles; all input sequences here are handcrafted synthetic."""
from copy import deepcopy
import builtins
import hashlib
import json
import math
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_fastqutils_contracts import json_sha256, validate_sheet, validate_components
from gene_annotation_episode.bvbrc_fastqutils_composition import calculate_composition
from gene_annotation_episode.bvbrc_fastqutils_quality import calculate_quality
from gene_annotation_episode.bvbrc_fastqutils_mapping import calculate_mapping
from gene_annotation_episode.bvbrc_fastqutils_fastq_reader import parse_fastq
from gene_annotation_episode.bvbrc_fastqutils_bam_reader import parse_bam
from test_bvbrc_fastqutils_sequence_formats import context
from test_bvbrc_fastqutils_alignment_formats import bam,record


def sheet_for(*documents):
    task=dict(resource_id="api:configured",task_id="synthetic",required_application_id="FastqUtils",
        native_application_id="FastqUtils",submitted_parameters={"recipe":[]},submitted_start_parameters={},
        scheduler_returned_parameters=None,effective_parameters=None,submission_receipt_ref="receipt:submit",
        submission_operation_key="run:launch:1",submission_source_ref="source:submit")
    sheet=dict(schema_version="fastqutils_sheet_v2",analysis_id="example",task_ref="receipt:submit",original_task=task,
        documents=deepcopy(list(documents)),document_resolutions=[],libraries=[],stages=[],associations=[],
        populations=[deepcopy(p) for d in documents for p in d["populations"]],
        measurements=[deepcopy(r) for d in documents for r in d["cells"]],
        categories=[],requirements=[deepcopy(r) for d in documents for r in d["requirements"]],
        diagnostics=[deepcopy(r) for d in documents for r in d["diagnostics"]],supplied_metadata=[],native_lineage=[])
    validate_sheet(sheet)
    return sheet


def encoding(sheet,document,encoding="phred33"):
    declaration=dict(version="fastqutils_encoding_declaration_v1",document_id=document,encoding=encoding,basis="explicit_assumption")
    raw=json.dumps(declaration,sort_keys=True,separators=(",",":")).encode()
    evidence=dict(content=dict(source_ref="source:metadata",artifact_field="artifact_ref",artifact_ref="artifact:encoding",
        sha256=hashlib.sha256(raw).hexdigest(),byte_count=len(raw)),pointer="")
    sheet["supplied_metadata"].append(dict(metadata_id="encoding",kind="encoding_declaration",evidence=evidence,value=declaration))
    for p in sheet["populations"]:
        if p["document_ids"]==[document] and p["population_key"]=="fastq_quality_characters":
            p["quality_encoding"]=encoding
            p["encoding_evidence_refs"]=["source:metadata"]
            p["encoding_basis"]=dict(basis="explicit_source_bound_declaration",encoding=encoding,
                metadata_id="encoding",evidence=deepcopy(evidence),declaration=deepcopy(declaration),native_locator=None)
    validate_sheet(sheet)


def binding(sheet,method,population_keys,metrics,**kwargs):
    pops=[p for p in sheet["populations"] if p["population_key"] in population_keys]
    refs=[p["id"] for p in pops]
    job=dict(calculation_id="calculation",method=method,state="ready",population_refs=refs,
        operand_measurement_refs=[r["id"] for r in sheet["measurements"] if r["population_ref"] in refs and r["metric"] in metrics],
        comparison_kind=None,quality_thresholds=[],read_key_rule=None,lineage_ref=None,lineage_basis=None,
        requirement_refs=[],diagnostic_codes=[])
    job.update(kwargs)
    return job


def calculate(fn,sheet,job):
    parameters=dict(analysis_id="example",calculations=[job])
    # Check the exact current parameter schema rather than invent a provider.
    parameters["version"]="fastqutils_calculators_v2"
    sha=json_sha256(parameters)
    rows=fn(sheet,job=job,parameters_sha256=sha)
    validate_components(dict(schema_version="fastqutils_components_v2",sheet_sha256=json_sha256(sheet),
        parameters=parameters,components=rows,requirements=[],diagnostics=[],analysis_id="example"),sheet=sheet)
    return rows


def by_metric(rows): return {r["metric"]:r for r in rows}


def composition_job(sheet):
    return binding(sheet,"composition_v1",["fastq_reads","fastq_bases"],
                   ["fastq_read_count","fastq_base_count","fastq_symbol_count"])


def quality_job(sheet,**kwargs):
    return binding(sheet,"quality_phred_v1",["fastq_quality_characters","bam_quality_bases"],
                   ["quality_character_count","phred_histogram_count"],quality_thresholds=[20,30],**kwargs)


def test_composition_hand_calculated_zero_invalid_partial_and_missing():
    raw=b"@one\nACGTNRY\n+\n!!!!!!!\n@two\nGC\n+\nII\n"
    sheet=sheet_for(parse_fastq(raw,context=context(raw)))
    job=composition_job(sheet)
    components=by_metric(calculate(calculate_composition,sheet,job))
    assert components["gc_acgt_fraction"]["value"]==4/6
    assert components["n_fraction"]["value"]==1/9
    assert components["ambiguous_fraction"]["value"]==3/9
    assert components["mean_read_length"]["value"]==9/2
    assert components["gc_acgt_fraction"]["numerator"]==4
    assert components["gc_acgt_fraction"]["denominator"]==6
    missing=deepcopy(job)
    missing["operand_measurement_refs"]=[ref for ref in job["operand_measurement_refs"] if ref!=next(r["id"] for r in sheet["measurements"] if r["metric"]=="fastq_read_count")]
    assert by_metric(calculate(calculate_composition,sheet,missing))["mean_read_length"]["value"] is None
    empty=sheet_for(parse_fastq(b"",context=context(b"")))
    assert all(r["state"]=="undefined" and r["value"] is None for r in calculate(calculate_composition,empty,composition_job(empty)))
    invalid=b"@invalid\nAC?\n+\n!!!\n"
    bad=sheet_for(parse_fastq(invalid,context=context(invalid)))
    rows=by_metric(calculate(calculate_composition,bad,composition_job(bad)))
    assert rows["gc_acgt_fraction"]["state"]=="incompatible"
    assert rows["mean_read_length"]["value"]==3
    partial=sheet_for(parse_fastq(raw,context=context(raw,scope="partial")))
    assert all(r["state"]=="truncated" for r in calculate(calculate_composition,partial,composition_job(partial)))


def test_phred_models_keep_explicit_encoding_and_saved_recalculation(monkeypatch):
    raw=b"@read\nACGT\n+\n!+5?\n"
    sheet=sheet_for(parse_fastq(raw,context=context(raw)))
    unknown=calculate(calculate_quality,sheet,quality_job(sheet))
    assert all(r["value"] is None and r["encoding_basis"]["basis"]=="unknown" for r in unknown)
    encoding(sheet,"reads")
    job=quality_job(sheet)
    original=deepcopy(sheet)
    rows=calculate(calculate_quality,sheet,job)
    values=by_metric(rows)
    assert values["mean_phred"]["value"]==15
    assert values["phred_implied_expected_errors"]["value"]==pytest.approx(1.111)
    assert values["phred_implied_error_fraction"]["value"]==pytest.approx(1.111/4)
    assert [r["value"] for r in rows if r["metric"]=="q_ge_threshold_fraction"]==[0.5,0.25]
    assert all(r["encoding_basis"]==sheet["populations"][-1]["encoding_basis"] for r in rows)
    assert all("explicit_encoding_assumption" in r["diagnostic_codes"] for r in rows)
    assert values["phred_implied_expected_errors"]["meaning"]=="phred_model_prediction"
    saved=json.loads(json.dumps(sheet))
    def forbidden(*args,**kwargs): raise AssertionError("Saved recalculation attempted I/O or native parsing")
    monkeypatch.setattr(builtins,"open",forbidden)
    monkeypatch.setattr(socket,"socket",forbidden)
    monkeypatch.setattr(subprocess,"Popen",forbidden)
    monkeypatch.setattr("gene_annotation_episode.bvbrc_fastqutils_fastq_reader.parse_fastq",forbidden)
    assert calculate(calculate_quality,saved,job)==rows
    changed=deepcopy(job); changed["quality_thresholds"]=[10]
    updated=calculate(calculate_quality,saved,changed)
    assert next(r["value"] for r in updated if r["metric"]=="q_ge_threshold_fraction")==0.75
    assert updated[0]["id"]!=rows[0]["id"]
    assert sheet==original


def test_phred64_bam_numeric_missing_ff_and_empty_quality():
    raw=b"@read\nAC\n+\n@J\n"
    sheet=sheet_for(parse_fastq(raw,context=context(raw)))
    encoding(sheet,"reads","phred64")
    assert by_metric(calculate(calculate_quality,sheet,quality_job(sheet)))["mean_phred"]["value"]==5
    raw_bam=bam([record(qualities=bytes([0,10]))])
    numeric=sheet_for(parse_bam(raw_bam,context=context(raw_bam,"bam_1")))
    assert by_metric(calculate(calculate_quality,numeric,quality_job(numeric)))["mean_phred"]["value"]==5
    absent=bam([record(qualities=b"\xff\xff")])
    missing=sheet_for(parse_bam(absent,context=context(absent,"bam_1")))
    assert all(r["value"] is None and r["state"]=="not_measured" for r in calculate(calculate_quality,missing,quality_job(missing)))
    empty=sheet_for(parse_fastq(b"",context=context(b""))); encoding(empty,"reads")
    rows=by_metric(calculate(calculate_quality,empty,quality_job(empty)))
    assert rows["phred_implied_expected_errors"]["value"]==0
    assert rows["mean_phred"]["state"]=="undefined"


def test_mapping_requires_complete_unambiguous_input_segments():
    raw=b"@r1\nAC\n+\nII\n@r2\nAC\n+\nII\n@r3\nAC\n+\nII\n"
    alignment=bam([record("r1"),record("r1",flag=256),record("r2",flag=4)])
    sheet=sheet_for(parse_fastq(raw,context=context(raw)),parse_bam(alignment,context=context(alignment,"bam_1",document="alignment")))
    job=binding(sheet,"mapping_v1",["fastq_reads","bam_records"],
                ["fastq_read_count","bam_record_count","bam_primary_record_count"],read_key_rule="exact_title")
    rows=by_metric(calculate(calculate_mapping,sheet,job))
    assert rows["distinct_mapped_read_fraction"]["value"]==1/3
    assert rows["primary_record_fraction"]["value"]==2/3
    assert rows["distinct_mapped_read_fraction"]["denominator"]==3
    only=sheet_for(sheet["documents"][1])
    missing=binding(only,"mapping_v1",["bam_records"],["bam_record_count","bam_primary_record_count"],read_key_rule="exact_title")
    assert by_metric(calculate(calculate_mapping,only,missing))["distinct_mapped_read_fraction"]["state"]=="missing"
    duplicate=bam([record("r1"),record("r1")])
    broken=sheet_for(sheet["documents"][0],parse_bam(duplicate,context=context(duplicate,"bam_1",document="alignment")))
    job=binding(broken,"mapping_v1",["fastq_reads","bam_records"],
                ["fastq_read_count","bam_record_count","bam_primary_record_count"],read_key_rule="exact_title")
    assert by_metric(calculate(calculate_mapping,broken,job))["distinct_mapped_read_fraction"]["state"]=="incompatible"


def test_mapping_mates_use_actual_flags_and_declared_key_rule():
    raw=b"@r/1\nAC\n+\nII\n@r/2\nAC\n+\nII\n"
    alignment=bam([record("r",flag=65),record("r",flag=133)])
    sheet=sheet_for(parse_fastq(raw,context=context(raw)),parse_bam(alignment,context=context(alignment,"bam_1",document="align")))
    job=binding(sheet,"mapping_v1",["fastq_reads","bam_records"],
                ["fastq_read_count","bam_record_count","bam_primary_record_count"],read_key_rule="first_token_slash_mate")
    assert by_metric(calculate(calculate_mapping,sheet,job))["distinct_mapped_read_fraction"]["value"]==0.5


def test_unavailable_binding_returns_typed_null_family():
    sheet=sheet_for()
    for fn,method,count in ((calculate_composition,"composition_v1",4),(calculate_quality,"quality_phred_v1",4),(calculate_mapping,"mapping_v1",2)):
        job=binding(sheet,method,[],[],state="unavailable",quality_thresholds=[30])
        rows=calculate(fn,sheet,job)
        assert len(rows)==count
        assert all(r["value"] is None and r["state"]=="missing" and r["population_refs"]==[] for r in rows)


def test_invalid_declared_quality_and_missing_selected_histogram_are_unavailable():
    raw=b"@r\nAC\n+\n!!\n"
    sheet=sheet_for(parse_fastq(raw,context=context(raw))); encoding(sheet,"reads","phred64")
    rows=calculate(calculate_quality,sheet,quality_job(sheet))
    assert all(r["state"]=="incompatible" and "invalid_quality_score" in r["diagnostic_codes"] for r in rows)
    numeric=bam([record(qualities=b"\xff\x1e")])
    invalid=sheet_for(parse_bam(numeric,context=context(numeric,"bam_1")))
    assert all(r["state"]=="incompatible" for r in calculate(calculate_quality,invalid,quality_job(invalid)))
    raw=b"@r\nAC\n+\n!I\n"
    valid=sheet_for(parse_fastq(raw,context=context(raw))); encoding(valid,"reads")
    job=quality_job(valid); job["operand_measurement_refs"]=job["operand_measurement_refs"][:1]
    assert all(r["value"] is None for r in calculate(calculate_quality,valid,job))


def test_mapping_duplicate_inputs_wrong_names_and_partial_scope():
    def run(raw,alignment,scope="complete"):
        sheet=sheet_for(parse_fastq(raw,context=context(raw,scope=scope)),
            parse_bam(alignment,context=context(alignment,"bam_1",document="align")))
        job=binding(sheet,"mapping_v1",["fastq_reads","bam_records"],
            ["fastq_read_count","bam_record_count","bam_primary_record_count"],read_key_rule="first_token")
        return by_metric(calculate(calculate_mapping,sheet,job))
    duplicate=b"@r1 first\nAC\n+\nII\n@r1 second\nAC\n+\nII\n"
    assert run(duplicate,bam([record("r1")]))["distinct_mapped_read_fraction"]["state"]=="incompatible"
    raw=b"@r1\nAC\n+\nII\n"
    assert run(raw,bam([record("unrelated")]))["distinct_mapped_read_fraction"]["state"]=="incompatible"
    rows=run(raw,bam([record("r1")]),"partial")
    assert rows["distinct_mapped_read_fraction"]["state"]=="truncated"
    assert rows["primary_record_fraction"]["value"]==1


def test_exact_two_read_requested_numerical_example():
    raw=b"@one\nACGT\n+\n5555\n@two\nGGTT\n+\nIIII\n"
    sheet=sheet_for(parse_fastq(raw,context=context(raw))); encoding(sheet,"reads")
    comp=by_metric(calculate(calculate_composition,sheet,composition_job(sheet)))
    qual=by_metric(calculate(calculate_quality,sheet,quality_job(sheet)))
    assert comp["gc_acgt_fraction"]["value"]==0.5
    assert comp["mean_read_length"]["numerator"]==8 and comp["mean_read_length"]["denominator"]==2
    assert qual["mean_phred"]["value"]==30
    assert qual["q_ge_threshold_fraction"]["threshold"]==30
    assert qual["q_ge_threshold_fraction"]["value"]==0.5
    assert qual["phred_implied_expected_errors"]["value"]==pytest.approx(0.0404)
    assert qual["phred_implied_error_fraction"]["value"]==pytest.approx(0.00505)


def test_conflicting_source_bound_encoding_declarations_do_not_calculate():
    raw=b"@r\nAC\n+\nII\n"
    sheet=sheet_for(parse_fastq(raw,context=context(raw))); encoding(sheet,"reads")
    conflicting=deepcopy(sheet["supplied_metadata"][0])
    conflicting["metadata_id"]="conflicting_encoding"
    conflicting["value"]["encoding"]="phred64"
    native=json.dumps(conflicting["value"],sort_keys=True,separators=(",",":")).encode()
    conflicting["evidence"]["content"].update(artifact_ref="artifact:other_encoding",
        source_ref="source:other_metadata",sha256=hashlib.sha256(native).hexdigest(),byte_count=len(native))
    sheet["supplied_metadata"].append(conflicting)
    rows=calculate(calculate_quality,sheet,quality_job(sheet))
    assert all(r["state"]=="incompatible" and r["value"] is None
               and "encoding_declaration_conflict" in r["diagnostic_codes"] for r in rows)


def test_unknown_transfer_scope_does_not_claim_truncation():
    raw=b"@r\nAC\n+\nII\n"
    document=parse_fastq(raw,context=context(raw,scope="unknown"))
    assert document["parse_scope"]=="complete"
    assert document["artifact"]["transfer_scope"]=="unknown"
    assert all(p["scope"]=="unknown" for p in document["populations"])
    sheet=sheet_for(document); encoding(sheet,"reads")
    assert all(r["state"]=="missing" for r in calculate(calculate_composition,sheet,composition_job(sheet)))
    assert all(r["state"]=="missing" for r in calculate(calculate_quality,sheet,quality_job(sheet)))


def test_fastq_pair_mapping_keeps_delimiters_in_distinct_read_keys():
    raw = b"@r/1 description\nAC\n+\nII\n@r_1 description\nAC\n+\nII\n"
    alignment = bam([record("r/1"), record("r_1")])
    sheet = sheet_for(parse_fastq(raw, context=context(raw)),
        parse_bam(alignment, context=context(alignment, "bam_1", document="align")))
    job = binding(sheet, "mapping_v1", ["fastq_reads", "bam_records"],
        ["fastq_read_count", "bam_record_count", "bam_primary_record_count"],
        read_key_rule="fastq_pair_0_3")
    fraction = by_metric(calculate(calculate_mapping, sheet, job))["distinct_mapped_read_fraction"]
    assert fraction["state"] == "available"
    assert (fraction["numerator"], fraction["denominator"], fraction["value"]) == (2, 2, 1)


def test_fastq_pair_mapping_does_not_treat_a_tab_as_its_native_space_split():
    raw = b"@r/1\tdescription\nAC\n+\nII\n"
    alignment = bam([record("r/1")])
    sheet = sheet_for(parse_fastq(raw, context=context(raw)),
        parse_bam(alignment, context=context(alignment, "bam_1", document="align")))
    job = binding(sheet, "mapping_v1", ["fastq_reads", "bam_records"],
        ["fastq_read_count", "bam_record_count", "bam_primary_record_count"],
        read_key_rule="fastq_pair_0_3")
    fraction = by_metric(calculate(calculate_mapping, sheet, job))["distinct_mapped_read_fraction"]
    assert fraction["state"] == "incompatible"
    assert fraction["value"] is None
    assert "incompatible_population" in fraction["diagnostic_codes"]
