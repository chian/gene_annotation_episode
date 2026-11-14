"""Dispatch ordinary deterministic calculators over a saved numerical sheet."""
from .bvbrc_fastqutils_contracts import validate_contract, validate_components, validate_sheet, json_sha256
from .bvbrc_fastqutils_identity import decode_reference
from .bvbrc_fastqutils_metric_specs import COMPONENT_ORDER
from .bvbrc_fastqutils_metadata import _check, _unique, _diagnostic, _requirement
from .bvbrc_fastqutils_resolution import calculation_requirements


def calculate_fastqutils(sheet: dict, *, parameters: dict) -> dict:
    validate_sheet(sheet)
    parameters = validate_contract("CalculatorParameters", parameters)
    _check(parameters["analysis_id"] == sheet["analysis_id"])
    result = dict(schema_version="fastqutils_components_v2", analysis_id=sheet["analysis_id"],
        sheet_sha256=json_sha256(sheet), parameters=parameters, components=[], requirements=[], diagnostics=[])
    # Validates all actual operand references before calling any calculator.
    validate_components(result, sheet=sheet)
    parameter_hash = json_sha256(parameters)
    requirements = calculation_requirements(sheet, parameters)
    for job in parameters["calculations"]:
        method = job["method"]
        if method == "composition_v1":
            from .bvbrc_fastqutils_composition import calculate_composition
            calculator = calculate_composition
        elif method == "quality_phred_v1":
            from .bvbrc_fastqutils_quality import calculate_quality
            calculator = calculate_quality
        elif method == "mapping_v1":
            from .bvbrc_fastqutils_mapping import calculate_mapping
            calculator = calculate_mapping
        elif method == "samstat_report_mapping_v1":
            from .bvbrc_fastqutils_samstat_mapping import calculate_samstat_report_mapping
            calculator = calculate_samstat_report_mapping
        elif method == "retention_v1":
            from .bvbrc_fastqutils_retention import calculate_retention
            calculator = calculate_retention
        else:
            from .bvbrc_fastqutils_consistency import calculate_report_consistency
            calculator = calculate_report_consistency
        rows = calculator(sheet, job=job, parameters_sha256=parameter_hash)
        rows.sort(key=lambda r: (COMPONENT_ORDER.index(r["metric"]), -1 if r["threshold"] is None else r["threshold"]))
        result["components"].extend(rows)
    data_codes = {"missing_requested_value": "requested_measurement", "missing_denominator": "before_population",
        "partial_transfer": "complete_native_bytes", "unknown_quality_encoding": "quality_encoding",
        "encoding_declaration_conflict": "source_bound_metadata", "ambiguous_pair_key": "pair_correspondence",
        "association_unresolved": "stage_input_association", "incompatible_population": "requested_measurement"}
    for row in result["components"]:
        sources = _unique([d["artifact"]["source_ref"] for d in sheet["documents"] if any(
            p["id"] in row["population_refs"] and d["document_id"] in p["document_ids"] for p in sheet["populations"])])
        for code in row["diagnostic_codes"]:
            result["diagnostics"].append(_diagnostic(code, [row["id"]], sources))
            required = data_codes.get(code)
            if row["method"] == "samstat_report_mapping_v1":
                required = {"missing_denominator": "requested_measurement", "samstat_caller_failure": "native_execution_evidence",
                    "source_row_absent": "native_execution_evidence", "unsupported_version": "native_version",
                    "unsupported_format": "supported_parser", "count_inconsistent": "requested_measurement",
                    "selection_ambiguous": "exact_source_cardinality", "malformed_native": "requested_measurement",
                    "native_header_conflict": "native_execution_evidence", "document_identity_conflict": "requested_measurement"}.get(code, required)
            if row["state"] != "available" and required is not None:
                requirements.append(_requirement(sheet["analysis_id"], decode_reference(row["id"])["pointer"],
                    code, required, [row["id"]], sources,
                    "incompatible" if row["state"] == "incompatible" else "unavailable"))
    result["requirements"] = _unique(requirements)
    result["diagnostics"] = _unique(result["diagnostics"])
    validate_components(result, sheet=sheet)
    return result


__all__ = ["calculate_fastqutils"]
