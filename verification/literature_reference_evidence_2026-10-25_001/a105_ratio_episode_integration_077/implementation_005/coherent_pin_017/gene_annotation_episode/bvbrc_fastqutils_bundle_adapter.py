"""FastqUtils provider: supplied bytes → retained sheet → selected typed facts."""
from __future__ import annotations

import hashlib
from pathlib import Path

from .bvbrc_fastqutils_contracts import canonical_json, validate_contract, validate_parameters, validate_requested_form
from .bvbrc_fastqutils_metadata import extract_fastqutils_metadata, _check, _unique
from .bvbrc_fastqutils_resolution import resolve_documents, resolve_calculation_inputs
from .bvbrc_fastqutils_sheet import populate_fastqutils_sheet
from .bvbrc_fastqutils_native import parse_fastqutils_artifact
from .bvbrc_fastqutils_calculators import calculate_fastqutils
from .bvbrc_fastqutils_projection import project_fastqutils_facts
from .bvbrc_fastqutils_saved_codec import encode_failures, encode_saved_components

ADAPTER_ID = "bvbrc_fastqutils"
ADAPTER_VERSION = "2"

# Exact scientific source/asset closure. This is read only at configuration;
# parsing and saved-sheet calculation perform no filesystem access.
_DEPENDENCIES = (
    "bvbrc_fastqutils_contracts.py", "bvbrc_fastqutils_identity.py", "bvbrc_fastqutils_metric_specs.py",
    "bvbrc_fastqutils_cutadapt_specs.py", "bvbrc_fastqutils_cutadapt_reader.py",
    "bvbrc_fastqutils_legacy_v2_schemas.json",
    "bvbrc_fastqutils_legacy_cutadapt_schemas.json",
    "bvbrc_fastqutils_samstat_specs.py", "bvbrc_fastqutils_samstat_native.py",
    "bvbrc_fastqutils_samstat_svg.py", "bvbrc_fastqutils_samstat_legacy.py",
    "bvbrc_fastqutils_samstat_mapping.py",
    "bvbrc_fastqutils_sra_native.py", "bvbrc_fastqutils_sra_specs.py", "bvbrc_fastqutils_json_tokens.py",
    "bvbrc_fastqutils_schemas.json", "bvbrc_fastqutils_fastq_reader.py", "bvbrc_fastqutils_sam_reader.py",
    "bvbrc_fastqutils_bam_reader.py", "bvbrc_fastqutils_fastqc_reader.py", "bvbrc_fastqutils_trim_reader.py",
    "bvbrc_fastqutils_pair_report_reader.py", "bvbrc_fastqutils_hostile_reader.py", "bvbrc_fastqutils_composition.py",
    "bvbrc_fastqutils_quality.py", "bvbrc_fastqutils_mapping.py", "bvbrc_fastqutils_retention.py",
    "bvbrc_fastqutils_consistency.py", "bvbrc_fastqutils_native.py", "bvbrc_fastqutils_metadata.py",
    "bvbrc_fastqutils_resolution.py", "bvbrc_fastqutils_sheet.py", "bvbrc_fastqutils_calculators.py",
    "bvbrc_fastqutils_projection.py", "bvbrc_fastqutils_saved_codec.py", "bvbrc_fastqutils_bundle_adapter.py",
)


def implementation_sha256() -> str:
    digest = hashlib.sha256()
    for name in sorted(_DEPENDENCIES):
        raw = Path(__file__).with_name(name).read_bytes()
        digest.update(name.encode("utf-8") + b"\0" + str(len(raw)).encode("ascii") + b"\0" + raw)
    return digest.hexdigest()


class FastqUtilsBundleAdapter:
    adapter_id = ADAPTER_ID
    adapter_version = ADAPTER_VERSION

    def consume_bundle(self, bundle: dict, *, artifact_bytes: dict[str, bytes],
        supplied_values: list[dict], requested_form: dict, parameters: dict) -> dict:
        bundle = validate_contract("Host_ArtifactBundle", bundle)
        parameters = validate_parameters(parameters)
        validate_requested_form(requested_form)
        _check(type(supplied_values) is list, "shape_invalid", "/supplied_values")
        supplied_values = [validate_contract("SuppliedValue", r) for r in supplied_values]
        evidence = {canonical_json(row) for row in bundle["supplied_scientific_metadata"]}
        _check(all(canonical_json(row["evidence"]) in evidence for row in supplied_values), "binding_conflict", "/supplied_values")
        contexts, resolutions, resolution_requirements = resolve_documents(bundle,
            artifact_bytes=artifact_bytes, parameters=parameters)
        documents = [parse_fastqutils_artifact(artifact_bytes[c["content"]["artifact_ref"]], context=c) for c in contexts]
        metadata = extract_fastqutils_metadata(bundle["original_task"], analysis_id=parameters["analysis_id"],
            metadata_bindings=parameters["metadata_bindings"], supplied_values=supplied_values, documents=documents)
        sheet = populate_fastqutils_sheet(documents, metadata=metadata, document_resolutions=resolutions)
        calculation_parameters = resolve_calculation_inputs(sheet, requests=parameters["calculation_requests"])
        calculations = calculate_fastqutils(sheet, parameters=calculation_parameters)
        failure_context = dict(requirements=_unique(resolution_requirements + sheet["requirements"] + calculations["requirements"]),
            diagnostics=_unique(sheet["diagnostics"] + calculations["diagnostics"]))
        projection = project_fastqutils_facts(sheet, calculations, requested_form=requested_form,
            parameters=parameters, failure_context=failure_context)
        encoded = encode_failures(projection["requirements"], projection["diagnostics"])
        saved = encode_saved_components(calculations, projection_failure_context=failure_context,
            native_requirements=projection["requirements"], native_diagnostics=projection["diagnostics"])
        return validate_contract("ProviderResult", dict(adapter_id=ADAPTER_ID, adapter_version=ADAPTER_VERSION,
            status=projection["status"], facts=projection["facts"], missing_requirements=encoded["missing_requirements"],
            diagnostics=encoded["diagnostics"], sheet=sheet, components=saved))


def consume_bundle(bundle: dict, *, artifact_bytes: dict[str, bytes], supplied_values: list[dict],
                   requested_form: dict, parameters: dict) -> dict:
    return FastqUtilsBundleAdapter().consume_bundle(bundle, artifact_bytes=artifact_bytes,
        supplied_values=supplied_values, requested_form=requested_form, parameters=parameters)


__all__ = ["ADAPTER_ID", "ADAPTER_VERSION", "FastqUtilsBundleAdapter", "consume_bundle", "implementation_sha256"]
