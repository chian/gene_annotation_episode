"""Handcrafted synthetic provider fixtures; no service or authenticated custody."""
from copy import deepcopy
import json
from pathlib import Path

from gene_annotation_episode.bvbrc_fastqutils_contracts import bytes_sha256, canonical_json, make_requested_schema
from gene_annotation_episode.bvbrc_fastqutils_bundle_adapter import consume_bundle
from gene_annotation_episode.bvbrc_fastqutils_resolution import resolve_documents
from gene_annotation_episode.bvbrc_fastqutils_native import parse_fastqutils_artifact
from gene_annotation_episode.bvbrc_fastqutils_metadata import extract_fastqutils_metadata
from gene_annotation_episode.bvbrc_fastqutils_sheet import populate_fastqutils_sheet

ROOT = Path(__file__).parent


def oracle(name):
    return json.loads((ROOT / name).read_text())


def fixture195():
    bundle = oracle("ARTIFACT_BUNDLE_AFTER_DOWNLOAD_002.json")
    parameters = oracle("PROVIDER_PARAMETERS_002.json")
    raw = {"artifact_reads195": (ROOT / "native_reads.fastq").read_bytes(),
           "artifact_hostile195": (ROOT / "native_hostile_1_1_0.json").read_bytes()}
    return bundle, raw, oracle("SUPPLIED_VALUES_002.json"), parameters


def population(document="reads", key="fastq_reads", ordinal=0):
    return dict(selection="semantic", document_id=document, population_key=key, population_ordinal=ordinal)


def measurement(document="reads", metric="fastq_read_count", section="fastq_summary", rows=None, axis=None):
    return dict(selection="semantic", document_id=document, section_key=section, section_ordinal=0, metric=metric,
        rows=rows or {"kind": "all"}, axis=axis or dict(kind="exact", axis=dict(kind="none", label=None, lower=None, upper=None)))


def selection(kind, selector=None, *, availability="typed_state", cardinality="one_target", count=1, field=None):
    target = dict(kind=kind)
    if selector is not None:
        target["selector"] = selector
    if field is not None:
        target["field"] = field
    return dict(target=target, cardinality=cardinality, expected_cardinality=count, availability_requirement=availability)


def schema(fields):
    return make_requested_schema(dict(version="fastqutils_projection_v2",
        fields=[dict(field=name, selection=value) for name, value in fields.items()]))


def build(documents, declarations=(), original=None):
    base = oracle("ARTIFACT_BUNDLE_AFTER_DOWNLOAD_002.json")
    bundle = deepcopy(base)
    bundle.update(artifacts=[], supplied_scientific_metadata=[], supplied_contents=[], diagnostics=[],
                  acquisition_receipt_refs=[], missing_requirements=[])
    if original is not None:
        bundle["original_task"] = deepcopy(original)
    params = dict(version="fastqutils_provider_v2", analysis_id="testC198", documents=[],
                  metadata_bindings=[], calculation_requests=[])
    raw = {}
    for name, (data, format_name) in documents.items():
        member = deepcopy(base["artifacts"][0])
        member.update(source_ref="source_" + name, raw_artifact_ref="artifact_" + name,
            sha256=bytes_sha256(data), byte_count=len(data), requirement_ids=["selected_" + name], role=name)
        member["workspace_object"]["path"] = "/fixture/output/" + name
        member["workspace_object"]["uuid"] = "synthetic_uuid_" + name
        member["task_association"]["task_id"] = bundle["original_task"]["task_id"]
        member["task_association"]["output_path"] = member["workspace_object"]["path"]
        member["task_association"]["output_uuid"] = member["workspace_object"]["uuid"]
        member["transfer"].update(total_size=len(data), receipt_ref="source_transfer_" + name)
        member["declared_format"].update(format=format_name, version=None)
        bundle["artifacts"].append(member)
        bundle["acquisition_receipt_refs"].append(member["transfer"]["receipt_ref"])
        raw[member["raw_artifact_ref"]] = data
        params["documents"].append(dict(document_id=name, selection=dict(kind="output_requirement", requirement_id="selected_" + name),
            format=format_name, producer_version=None))
    values = []
    metadata_raw = canonical_json({"declarations": [v for _, _, v in declarations]}).encode()
    content = dict(source_ref="source_declarations", artifact_field="artifact_ref", artifact_ref="artifact_declarations",
                   sha256=bytes_sha256(metadata_raw), byte_count=len(metadata_raw))
    for index, (ident, kind, value) in enumerate(declarations):
        evidence = dict(content=content, pointer="/declarations/" + str(index))
        params["metadata_bindings"].append(dict(metadata_id=ident, kind=kind, evidence=deepcopy(evidence)))
        values.append(dict(evidence=deepcopy(evidence), value=deepcopy(value)))
        bundle["supplied_scientific_metadata"].append(deepcopy(evidence))
    return bundle, raw, values, params


def sheet_for(data):
    bundle, raw, values, params = data
    contexts, resolutions, _ = resolve_documents(bundle, artifact_bytes=raw, parameters=params)
    docs = [parse_fastqutils_artifact(raw[c["content"]["artifact_ref"]], context=c) for c in contexts]
    metadata = extract_fastqutils_metadata(bundle["original_task"], analysis_id=params["analysis_id"],
        metadata_bindings=params["metadata_bindings"], supplied_values=values, documents=docs)
    return populate_fastqutils_sheet(docs, metadata=metadata, document_resolutions=resolutions)


def run(data, fields):
    bundle, raw, values, params = data
    return consume_bundle(bundle, artifact_bytes=raw, supplied_values=values,
                          requested_form=schema(fields), parameters=params)


def fastq(titles, sequence="ACGT", quality="IIII"):
    return "".join("@" + title + "\n" + sequence + "\n+\n" + quality + "\n" for title in titles).encode()


def encoding(document="reads", encoding="phred33"):
    return dict(version="fastqutils_encoding_declaration_v1", document_id=document, encoding=encoding, basis="explicit_assumption")


def pair(left="left", right="right", rule="first_token_slash_mate"):
    return dict(version="fastqutils_pair_declaration_v1", left_document_id=left,
                right_document_id=right, pair_key_rule=rule)


def seven_family_data():
    declaration = dict(version="fastqutils_association_assertion_v1", document_id="hostile",
        input_pointer="/paired_end_libs/0", recipe_ordinal=4, mate="combined", branch="clean", basis="explicit_assertion")
    qc = b"##FastQC\t0.12.1\n>>Basic Statistics\tpass\n#Measure\tValue\nFilename\treads.fastq\nFile type\tConventional base calls\nEncoding\tSanger / Illumina 1.9\nTotal Sequences\t2\nSequences flagged as poor quality\t0\nSequence length\t5\n%GC\t56\n>>END_MODULE\n"
    data = build({"reads": ((ROOT / "native_reads.fastq").read_bytes(), "fastq"),
        "hostile": ((ROOT / "native_hostile_1_1_0.json").read_bytes(), "hostile_json_1_1_0"),
        "qc": (qc, "fastqc_data_0_12_1")},
        [("encoding_reads", "encoding_declaration", encoding()), ("assert_hostile", "association_assertion", declaration)])
    original_requests = oracle("PROVIDER_PARAMETERS_002.json")["calculation_requests"]
    data[3]["calculation_requests"] = original_requests
    fields = dict(read_count=selection("measurement", measurement(), availability="available_value"),
        gc=selection("component", dict(selection="semantic", calculation_id="composition_reads", metric="gc_acgt_fraction", threshold=None), availability="available_value"),
        errors=selection("component", dict(selection="semantic", calculation_id="quality_reads", metric="phred_implied_expected_errors", threshold=None), availability="available_value"),
        retained=selection("component", dict(selection="semantic", calculation_id="retention_hostile", metric="native_report_retention_fraction", threshold=None), availability="available_value"),
        qc=selection("category", dict(selection="semantic", document_id="qc", section_key="fastqc_basic_statistics", section_ordinal=0), availability="available_value"),
        population=selection("population", population(), availability="available_value"),
        association=selection("association", dict(selection="semantic", document_id="hostile", input_pointer="/paired_end_libs/0", recipe_ordinal=4, mate="combined", branch="clean")),
        requirements=selection("requirements"), status=selection("request_status", field="read_count"))
    return data, fields
