"""Declared-format dispatch and honest retention of unsupported artifacts."""
from copy import deepcopy

from .bvbrc_fastqutils_contracts import checked_bytes, validate_contract, validate_native_document
from .bvbrc_fastqutils_identity import artifact_ref
from .bvbrc_fastqutils_metadata import _check, _escape, _diagnostic, _requirement


def parse_unsupported_artifact(raw: bytes, *, context: dict) -> dict:
    context = validate_contract("ParseContext", context)
    checked_bytes(raw, content=context["content"])
    _check(context["declared_format"] in {"bai", "samstat_html", "sra_metadata", "native_text", "native_json", "unknown"})
    content = context["content"]
    ident = artifact_ref(context)
    artifact = dict(id=ident, source_ref=content["source_ref"], content_ref=content["artifact_ref"],
        task_ref=context["task_ref"], sha256=content["sha256"], byte_count=content["byte_count"],
        native_name=context["native_name"], declared_format=context["declared_format"], actual_format="unknown",
        compression="unknown", transfer_scope=context["transfer_scope"], producer_name=None,
        producer_version=context["producer_version"], identity=context["identity"],
        document_id=context["document_id"], content_binding=deepcopy(content))
    locator = dict(member=None, block="unsupported", block_ordinal=0, row_ordinal=None,
                   field="retained_artifact", byte_start=None, byte_end=None)
    requirement = _requirement(context["analysis_id"], "/documents/" + _escape(context["document_id"]),
        "unsupported_format", "supported_parser", [ident], [content["source_ref"]])
    doc = dict(schema_version="fastqutils_native_v2", analysis_id=context["analysis_id"],
        document_id=context["document_id"], artifact=artifact, parse_scope="unsupported", cells=[], categories=[],
        raw_blocks=[dict(artifact_ref=ident, locator=locator, kind="unsupported_section",
            native_name=context["declared_format"], parse_status="unsupported", field_names=[])],
        sequence_records=[], alignment_records=[], labels=[], populations=[], native_lineage=[],
        alignment_headers=[], reference_dictionary=[], requirements=[requirement],
        diagnostics=[_diagnostic("unsupported_format", [ident], [content["source_ref"]])],
        sections=[dict(key="unsupported", ordinal=0, locator=locator, state="unsupported",
                       cell_refs=[], category_refs=[], label_refs=[], raw_block_ordinals=[0])])
    validate_native_document(doc)
    return doc


def parse_fastqutils_artifact(raw: bytes, *, context: dict) -> dict:
    context = validate_contract("ParseContext", context)
    checked_bytes(raw, content=context["content"])
    format_name = context["declared_format"]
    if format_name == "fastq":
        from .bvbrc_fastqutils_fastq_reader import parse_fastq
        parser = parse_fastq
    elif format_name == "sam_1_6":
        from .bvbrc_fastqutils_sam_reader import parse_sam
        parser = parse_sam
    elif format_name == "bam_1":
        from .bvbrc_fastqutils_bam_reader import parse_bam
        parser = parse_bam
    elif format_name.startswith("fastqc_"):
        from .bvbrc_fastqutils_fastqc_reader import parse_fastqc_html, parse_fastqc_data, parse_fastqc_zip
        parser = {"fastqc_html_0_12_1": parse_fastqc_html, "fastqc_data_0_12_1": parse_fastqc_data,
                  "fastqc_zip_0_12_1": parse_fastqc_zip}[format_name]
    elif format_name == "trim_galore_report_0_6_10":
        from .bvbrc_fastqutils_trim_reader import parse_trim_galore_report
        parser = parse_trim_galore_report
    elif format_name == "fastq_pair_stderr_0_3":
        from .bvbrc_fastqutils_pair_report_reader import parse_fastq_pair_stderr
        parser = parse_fastq_pair_stderr
    elif format_name == "hostile_json_1_1_0":
        from .bvbrc_fastqutils_hostile_reader import parse_hostile_json
        parser = parse_hostile_json
    elif format_name == "sra_metadata":
        from .bvbrc_fastqutils_sra_native import parse_sra_metadata
        parser = parse_sra_metadata
    elif format_name in {"samstat_html", "samstat_html_2_2_3", "samstat_html_2_5_0", "samstat_bvbrc_error_html"}:
        from .bvbrc_fastqutils_samstat_native import parse_samstat_html
        parser = parse_samstat_html
    else:
        parser = parse_unsupported_artifact
    result = parser(raw, context=context)
    validate_native_document(result)
    return result


__all__ = ["parse_fastqutils_artifact", "parse_unsupported_artifact"]
