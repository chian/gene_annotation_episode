"""Select requested, already populated Infernal preparation values and artifacts.

This boundary does no parsing, calculation, acquisition or scientific grading.
Catalogues describe scalar Value cells in the frozen producer schemas. Native
arrays (model backgrounds, HMM statistics and calibration series), trace bodies
and full provenance remain in retained grading data; no scalar summary is implied.
"""
from __future__ import annotations

from copy import deepcopy

from .domain import ContractError, validate_schema
from .infernal_preparation_schema import (
    CALCULATIONS_SCHEMA, PROGRAM_MODES, UNITS, VALUE_BASES, VALUE_STATES,
    require_finite_json, validate_common_sheet, validate_locator,
    validate_value,
)
from .infernal_preparation_models import (
    CALIBRATION_ALGORITHMS, FIELD_UNITS, HMM_UNITS, TOPOLOGY_FIELDS,
    ROW_FIELDS as MODEL_ROW_FIELDS,
)
from .infernal_preparation_artifacts import (
    ARTIFACT_VALUE_NAMES, CHECK_NAMES as ARTIFACT_CHECKS,
    COMPONENT_NAMES as ARTIFACT_COMPONENTS, ROW_FIELDS as ARTIFACT_ROW_FIELDS,
)
from .infernal_preparation_statistics import (
    VALUE_UNITS, ROW_FIELDS as STATISTIC_ROW_FIELDS,
)
from .infernal_preparation_calculations import (
    CHECK_NAMES as STATISTIC_CHECKS, COMPONENT_UNITS as STATISTIC_COMPONENT_UNITS,
)
from .infernal_preparation_emission import (
    COMPONENT_NAMES as EMISSION_COMPONENTS, ROW_FIELDS as EMISSION_ROW_FIELDS,
    SEQUENCE_VALUE_NAMES,
)
from .infernal_preparation_emission_calculations import CHECK_NAMES as EMISSION_CHECKS


_COLLECTIONS = ("input_records", "output_records", "native_rows", "calculations")
_DIRECTIONS = ("input", "working_copy", "output")
_ROLES = ("models", "alignment", "prior", "null", "rsearch", "gc", "keys", "ssi",
          "request", "stdout", "stderr", "built_models", "calibrated_models",
          "processed_alignment", "refined_alignment", "converted_models",
          "converted_hmms", "fetched_models", "generated_sequences",
          "generated_alignment", "trace", "commands", "partition_scores",
          "hfile", "sfile", "qqfile", "ffile", "xfile", "i1m", "i1i", "i1f", "i1p")
_FORMATS = ("infernal_cm_ascii", "infernal_cm_legacy_ascii", "infernal_cm_binary",
            "hmmer_hmm_ascii", "infernal_ssi", "infernal_i1f", "infernal_i1p",
            "stockholm", "fasta", "pfam", "afa", "a2m", "clustal", "phylip",
            "infernal_stdout", "infernal_stderr", "infernal_calibration_hfile",
            "infernal_calibration_sfile", "infernal_calibration_qqfile",
            "infernal_calibration_ffile", "infernal_calibration_xfile",
            "infernal_partition_scores", "infernal_commands", "infernal_trace",
            "key_file", "infernal_request_json", "text")
_ROW_FIELDS = {**MODEL_ROW_FIELDS, **ARTIFACT_ROW_FIELDS, **STATISTIC_ROW_FIELDS,
               **EMISSION_ROW_FIELDS}
_OCCURRENCE_FIELDS = {"occurrence_ref", "direction", "role", "ordinal", "format",
                      "relative_path", "artifact_ref", "sha256", "size_bytes", "completeness"}
_CALIBRATION_UNITS = dict(VALUE_UNITS["calibration"])
_EMISSION_UNITS = {
    "residue_count": "nt", "canonical_count": "nt", "gc_count": "nt",
    "ambiguity_count": "nt", "gc_fraction_canonical": "fraction",
    "gc_denominator": "nt", "gap_count": "column", "column_count": "column",
    "gap_fraction": "fraction", "row_count": "count", "expected_sequence_count": "count",
    "actual_sequence_count": "count", "score_bits": "bit", "structure_score_bits": "bit",
}
_MODEL_MEANINGS = {
    "CLEN": "Native CM consensus length.", "W": "Native CM maximum hit length.",
    "NSEQ": "Native training sequence count.", "EFFN": "Native effective training sequence count.",
    "STATES": "Native CM state count.", "NODES": "Native CM node count.",
    "CKSUM": "Native digital sequence checksum; not a confidence measurement.",
    "GA": "Native gathering bit-score cutoff.", "TC": "Native trusted bit-score cutoff.",
    "NC": "Native noise bit-score cutoff.", "LENG": "Native HMM model length.",
    "MAXL": "Native HMM maximum hit length.",
}
_MEANINGS = {
    "lambda": "Native exponential-tail inverse-bit scale.",
    "mu_orig": "Native fitted exponential-tail location before extrapolation.",
    "mu_extrap": "Native exponential-tail location extrapolated to the full population.",
    "calibration_dbsize_nt": "Native calibration population size in nucleotides.",
    "random_hit_count": "Native random-hit count in the calibration population.",
    "tail_probability_mass": "Native fitted tail probability mass.",
    "tail_hit_count": "Native number of hits in the selected fitted tail.",
    "nseq": "Native training sequence count.", "eff_nseq": "Native effective sequence count.",
    "alignment_length": "Native training alignment width.",
    "consensus_length": "Native CM consensus length.",
    "max_hit_length": "Native maximum hit length.",
    "base_pairs": "Native paired consensus-node count.", "bifurcations": "Native bifurcation count.",
    "cm_relative_entropy": "Native CM relative entropy per consensus position.",
    "hmm_relative_entropy": "Native HMM relative entropy per consensus position.",
    "bit_score_sum": "Native refinement iteration bit-score sum.",
    "fractional_difference": "Native refinement iteration fractional difference.",
    "predicted_seconds": "Native calibration duration prediction, not measured execution time.",
    "predicted_mb": "Native calibration memory prediction in decimal megabytes.",
    "predicted_bytes": "Saved conversion of native memory prediction from decimal MB to bytes.",
    "cpu_count": "CPU population associated with the native resource prediction.",
    "command_count": "Native reported or decoded retained partition-command count.",
    "score_count": "Native partition score count; full ordered scores remain retained.",
    "requested_megabases": "Requested calibration size in millions of nucleotides, not memory MB.",
    "total_chunks": "Native total calibration chunk population.",
    "partition_chunks": "Native calibration chunks assigned to this partition.",
    "threshold_bits": "Native score threshold for the selected conversion mode.",
    "evalue": "Native expected hit count for the explicitly selected search population.",
    "pvalue": "Native tail probability for the selected algorithm and threshold.",
    "search_space_nt": "Explicit native search-space denominator in nucleotides.",
    "row_count": "Number of decoded alignment member rows; capture completeness is separate.",
    "column_count": "Retained alignment width; omitted insertion columns are not reconstructed.",
    "checksum": "Digital training-alignment checksum with the supplied compatible alphabet.",
    "rf_column_count": "Count of retained non-gap RF annotation columns.",
    "residue_count": "Generated A,C,G,T,U,R,Y,K,M,S,W,B,D,H,V,N,X symbol count, case insensitive.",
    "canonical_count": "Generated A+C+G+T+U count; excludes ambiguity and missing symbols.",
    "gc_count": "Generated G+C count, case insensitive.",
    "ambiguity_count": "Generated residue count minus canonical count.",
    "gc_denominator": "Generated canonical A+C+G+T+U count used as the GC denominator.",
    "gc_fraction_canonical": "Saved generated G+C count divided by positive canonical count.",
    "gap_count": "Count of retained literal '-', '.' and '_' alignment gap symbols.",
    "gap_fraction": "Saved gap count divided by positive known alignment column count.",
    "expected_sequence_count": "Expected generated rows from explicit settings and complete model population.",
    "actual_sequence_count": "Actual generated rows with the producer's validated record association.",
    "score_bits": "Native generated-trace SCORE header, not evidence about a target gene.",
    "structure_score_bits": "Native generated CM STRUCTURE SCORE; unmeasured HMM sentinel stays unavailable.",
    "model_count": "Native reported model population count.",
    "indexed_name_count": "Native reported indexed-name population count.",
    "indexed_accession_count": "Native reported indexed-accession population count.",
    "byte_count": "Actual retained artifact byte count where measured.",
    "input_model_count": "Decoded input model count only when that population is complete.",
    "output_model_count": "Decoded output model count only when that population is complete.",
    "requested_key_count": "Distinct requested fetch-key count.",
    "satisfied_key_count": "Distinct fetch keys with validated satisfied outcome.",
    "missing_key_count": "Distinct fetch keys with missing outcome.",
    "ambiguous_key_count": "Distinct fetch keys with ambiguous outcome.",
    "output_artifact_count": "Retained output artifact occurrences, including captured stdout/stderr.",
    "output_byte_count": "Retained output bytes in the producer's explicit artifact population.",
    "paired_consensus_fraction": "Saved twice-base-pair count divided by consensus length.",
    "paired_consensus_numerator": "Saved twice-base-pair count in consensus nucleotides.",
    "consensus_length_denominator": "Consensus length used as the paired-consensus denominator.",
    "mu_extrap_calculated": "Saved mu_orig + log(tail_probability_mass)/lambda.",
    "mu_extrap_residual": "Saved calculated minus native extrapolated location; sign is retained.",
    "actual_calibration_nt": "Native calibration population size or saved selected chunk population times 10000 nt; the existing cell retains its basis.",
    "partition_chunk_count": "Saved chunk count for the explicitly selected partition.",
    "total_calibration_chunk_count": "Saved floor(requested Mnt*100+0.5), before partitioning.",
    "effective_random_hit_count": "Saved population-scaled native random-hit count or HMM search-space/MAXL.",
    "score_at_evalue": "Saved algorithm-specific inverse-tail score for the supplied expected hit count.",
    "score_at_pvalue": "Saved algorithm-specific inverse-tail score for the supplied tail probability.",
    "evalue_at_score": "Saved population-scaled exponential tail at the supplied score.",
    "native_conversion_residual": "Saved calculated minus native conversion, in the converted quantity's units.",
    "native_rounding_half_width": "Saved half-width of the native numeric formatter's rounding interval.",
}


def _error(reason):
    raise ContractError("native_infernal_preparation_projection_" + reason)


def _text(value, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or not value or "\x00" in value:
        _error("nonempty_text_required")


def _fields(value, expected):
    if type(value) is not dict or set(value) != set(expected):
        _error("fields_invalid")


def _object(properties):
    return {"type": "object", "additionalProperties": False,
            "properties": properties, "required": list(properties)}


def _descriptor(unit, basis, meaning):
    return {"unit": unit, "basis": basis, "meaning": meaning}


def _model_quantities():
    result = {"fields." + name: _descriptor(unit, "model_header", _MODEL_MEANINGS[name])
              for name, unit in FIELD_UNITS.items()}
    result.update({"filter_hmm.fields." + name: _descriptor(unit, "model_header", _MODEL_MEANINGS[name])
                   for name, unit in HMM_UNITS.items()})
    for tag, algorithm in CALIBRATION_ALGORITHMS.items():
        for name, unit in _CALIBRATION_UNITS.items():
            result[f"calibration.{tag}.{name}"] = _descriptor(unit, "model_header", algorithm + ": " + _MEANINGS[name])
    for name in TOPOLOGY_FIELDS:
        result["topology." + name] = _descriptor("count", "model_header", "Decoded native CM topology: " + name.replace("_", " ") + ".")
    for name, unit in (("location", "bit"), ("scale", "inverse_bit")):
        result["efp7gf." + name] = _descriptor(unit, "model_header", "Native EFP7GF filter fit " + name + "; separate from CM calibration.")
    return result


def _kind_quantities(kind, collection):
    if kind == "model":
        return _model_quantities()
    if kind in VALUE_UNITS:
        units = VALUE_UNITS[kind]
    elif kind == "artifact_operation":
        units = {name: "byte" if name == "byte_count" else "count" for name in ARTIFACT_VALUE_NAMES}
    elif kind == "generated_sequence":
        units = {name: _EMISSION_UNITS[name] for name in SEQUENCE_VALUE_NAMES}
    elif kind == "generated_alignment":
        units = {name: _EMISSION_UNITS[name] for name in ("row_count", "column_count")}
    elif kind == "generated_trace":
        units = {"score_bits": "bit", "structure_score_bits": "bit"}
    else:
        return {}  # key_request contains identifiers and classifications, no Value cells.
    result = {}
    for name, unit in units.items():
        basis = "native_reported"
        if kind in {"training_alignment", "generated_sequence", "generated_alignment"} or name == "search_space_nt":
            basis = "derived"
        if kind == "resource_estimate" and name != "command_count":
            basis = "native_prediction"
        if kind == "artifact_operation" and name == "byte_count" and collection == "output_records":
            basis = "derived"
        result["values." + name] = _descriptor(unit, basis, _MEANINGS[name])
    return result


def _collection_kinds(program, mode):
    if program in {"cmconvert", "cmfetch", "cmpress"}:
        decoded = not (program == "cmpress" or mode in {"binary", "index"})
        return {"input_records": ("model",),
                "output_records": ("model", "artifact_operation") if decoded else ("artifact_operation",),
                "native_rows": ("artifact_operation", "key_request") if program == "cmfetch" and mode != "index" else ("artifact_operation",)}
    if program == "cmbuild":
        return {"input_records": ("training_alignment",),
                "output_records": ("model", "training_alignment"),
                "native_rows": ("build", "build_refinement") if mode == "refine" else ("build",)}
    if program == "cmcalibrate":
        native = {"calibrate": ("calibration", "calibration_series", "resource_estimate"),
                  "merge_scores": ("calibration", "calibration_series", "partition", "resource_estimate"),
                  "partition_scores": ("partition", "resource_estimate"),
                  "forecast": ("resource_estimate",), "memory_estimate": ("resource_estimate",),
                  "split_commands": ("resource_estimate",)}[mode]
        return {"input_records": ("model",), "output_records": ("model",) if mode in {"calibrate", "merge_scores"} else (),
                "native_rows": native}
    if program == "cmstat":
        return {"input_records": ("model",), "output_records": (), "native_rows": ("model_statistic",)}
    return {"input_records": ("model",),
            "output_records": ("generated_sequence", "generated_alignment") if mode == "sample_aligned" else ("generated_sequence",),
            "native_rows": ("generated_trace",)}


def preparation_projection_catalog(program, mode):
    """Return closed scalar paths, units, missing-cell bases and meanings.

    Existing Value cells always retain their own unit/basis. Catalogue defaults
    apply only to a genuinely absent or row-inapplicable declared field. In
    particular, native-conversion residual units depend on the cmstat mode.
    """
    if type(program) is not str or program not in PROGRAM_MODES or type(mode) is not str or mode not in PROGRAM_MODES[program]:
        _error("program_mode_invalid")
    result = {}
    for collection, kinds in _collection_kinds(program, mode).items():
        quantities = {}
        for kind in kinds:
            quantities.update(_kind_quantities(kind, collection))
        result[collection] = {"quantities": dict(sorted(quantities.items())), "checks": []}
    if program in {"cmconvert", "cmfetch", "cmpress"}:
        units = {name: "byte" if name == "output_byte_count" else "count" for name in ARTIFACT_COMPONENTS}
        checks = ARTIFACT_CHECKS
    elif program == "cmemit":
        units = {name: _EMISSION_UNITS[name] for name in EMISSION_COMPONENTS}
        checks = EMISSION_CHECKS
    else:
        units, checks = dict(STATISTIC_COMPONENT_UNITS), STATISTIC_CHECKS
        if program == "cmstat" and mode.startswith("evalues_at_"):
            units.update(native_conversion_residual="expected_count", native_rounding_half_width="expected_count")
    quantities = {}
    for name, unit in units.items():
        basis = "native_prediction" if name in {"predicted_seconds", "predicted_bytes"} else (
            "native_reported" if name in {"score_bits", "structure_score_bits"} else "derived")
        quantities["components." + name] = _descriptor(unit, basis, _MEANINGS[name])
    result["calculations"] = {"quantities": dict(sorted(quantities.items())), "checks": sorted(checks)}
    return result


_ALL_QUANTITIES = sorted({path for program, modes in PROGRAM_MODES.items() for mode in modes
                         for entry in preparation_projection_catalog(program, mode).values()
                         for path in entry["quantities"]})
_ALL_CHECKS = sorted(ARTIFACT_CHECKS | STATISTIC_CHECKS | EMISSION_CHECKS)
_TEXT = {"type": "string", "minLength": 1}
_SOURCE_REF = {**_TEXT, "format": "reference", "x-reference-namespace": "execution_result"}
_ARTIFACT_REF = {**_TEXT, "format": "reference", "x-reference-namespace": "artifact"}
_ROW_KEY = {**_TEXT, "format": "identifier", "x-reference-namespace": "native_infernal_preparation_row"}
_ARTIFACT_SELECTION = _object({"direction": {"enum": list(_DIRECTIONS)},
    "role": {"enum": list(_ROLES)}, "ordinal": {"type": "integer", "minimum": 0}})
_ROWS = {"oneOf": [_object({"offset": {"type": "integer", "minimum": 0},
    "limit": {"type": "integer", "minimum": 1}}), _object({"record_keys": {
        "type": "array", "minItems": 1, "uniqueItems": True, "items": _ROW_KEY}})]}
_PROJECTION = _object({"collection": {"enum": list(_COLLECTIONS)}, "rows": _ROWS,
    "quantities": {"type": "array", "uniqueItems": True, "items": {"enum": _ALL_QUANTITIES}},
    "checks": {"type": "array", "uniqueItems": True, "items": {"enum": _ALL_CHECKS}}})
_PROJECTION["anyOf"] = [{"properties": {"quantities": {"minItems": 1}}},
                         {"properties": {"checks": {"minItems": 1}}}]
NATIVE_INFERNAL_PREPARATION_RESULT_SELECTOR_SCHEMA = _object({
    "version": {"const": "native_infernal_preparation_result_selector_v1"},
    "acquisition": {"const": "complete_bound_bundle"},
    "projection": {"oneOf": [_PROJECTION, {"type": "null"}]},
    "artifacts": {"type": "array", "uniqueItems": True, "items": _ARTIFACT_SELECTION}})
NATIVE_INFERNAL_PREPARATION_RESULT_SELECTOR_SCHEMA["anyOf"] = [
    {"properties": {"projection": {"type": "object"}}},
    {"properties": {"artifacts": {"minItems": 1}}}]
# Reports use the existing communication boundary's deliberately small grammar.
# Its semantic identifiers are authenticated by the return owner. Strict input
# digest, selector and Value-state validation remains separate below.
_REPORT_SOURCE_REF = {"type": "string", "format": "reference", "x-reference-namespace": "execution_result"}
_REPORT_ARTIFACT_REF = {"type": "string", "format": "reference", "x-reference-namespace": "artifact"}
_REPORT_ROW_KEY = {"type": "string", "format": "identifier", "x-reference-namespace": "native_infernal_preparation_row"}
_REPORT_ARTIFACT_SELECTION = _object({"direction": {"type": "string", "enum": list(_DIRECTIONS)},
    "role": {"type": "string", "enum": list(_ROLES)}, "ordinal": {"type": "integer", "minimum": 0}})
_CHECK_OCCURRENCE_SCHEMA = _object({**_REPORT_ARTIFACT_SELECTION["properties"], "artifact_ref": _REPORT_ARTIFACT_REF})
_QUANTITY_SCHEMA = _object({"path": {"type": "string", "enum": _ALL_QUANTITIES}, "value": {"type": ["number", "null"]},
    "state": {"type": "string", "enum": sorted(VALUE_STATES)},
    "basis": {"type": "string", "enum": sorted(VALUE_BASES)}, "unit": {"type": "string", "enum": sorted(UNITS)}})
ROW_SCHEMA = _object({"record_key": _REPORT_ROW_KEY, "kind": {"type": "string", "enum": sorted({*_ROW_FIELDS, "calculation"})},
    "name": {"type": ["string", "null"], "format": "identifier", "x-reference-namespace": "native_infernal_preparation_name"},
    "accession": {"type": ["string", "null"], "format": "identifier", "x-reference-namespace": "native_infernal_preparation_accession"},
    "source_ref": _REPORT_SOURCE_REF, "artifact_ref": {**_REPORT_ARTIFACT_REF, "type": ["string", "null"]},
    "quantities": {"type": "array", "items": _QUANTITY_SCHEMA},
    "checks": {"type": "array", "items": _object({"name": {"type": "string", "enum": _ALL_CHECKS},
        "outcome": {"type": "string", "enum": ["pass", "fail", "unknown", "not_applicable"]},
        "occurrences": {"type": "array", "items": _CHECK_OCCURRENCE_SCHEMA, "uniqueItems": True}})}})
_OCCURRENCE_ARTIFACT_SCHEMA = _object({**_ARTIFACT_SELECTION["properties"], "artifact_ref": _ARTIFACT_REF,
    "format": {"enum": list(_FORMATS)}, "size_bytes": {"type": "integer", "minimum": 0},
    "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
    "completeness": {"enum": ["complete", "partial", "unknown"]}})
ARTIFACT_SCHEMA = _object({"source_ref": _REPORT_SOURCE_REF, **_REPORT_ARTIFACT_SELECTION["properties"],
    "artifact_ref": _REPORT_ARTIFACT_REF, "format": {"type": "string", "enum": list(_FORMATS)},
    "size_bytes": {"type": "integer", "minimum": 0},
    "sha256": {"type": "string", "format": "identifier", "x-reference-namespace": "native_infernal_preparation_sha256"},
    "completeness": {"type": "string", "enum": ["complete", "partial", "unknown"]}})
POPULATION_SCHEMA = _object({"source_ref": _REPORT_SOURCE_REF, "collection": {"type": ["string", "null"], "enum": [*_COLLECTIONS, None]},
    **{name: {"type": "integer", "minimum": 0} for name in (
        "total_records", "returned_records", "omitted_records", "requested_artifact_count", "returned_artifact_count")},
    "missing_record_keys": {"type": "array", "items": _REPORT_ROW_KEY, "uniqueItems": True},
    "missing_artifacts": {"type": "array", "items": _REPORT_ARTIFACT_SELECTION, "uniqueItems": True}})
FAILURE_STAGES = ("software", "inputs", "staging", "execution", "outputs", "capture",
    "prerequisite", "custody", "metadata", "native", "reading", "worker", "extraction",
    "calculation", "grading", "projection", "selection", "format", "association",
    "validation", "unclassified")
FAILURE_SCHEMA = _object({
    "handoff_ref": {"type": "string", "format": "reference", "x-reference-namespace": "execution_handoff"},
    "source_ref": {**_REPORT_SOURCE_REF, "type": ["string", "null"]},
    "stage": {"type": "string", "enum": list(FAILURE_STAGES)},
    "code": {"type": "string", "format": "identifier", "x-reference-namespace": "native_infernal_preparation_failure_code"},
    "record_key": {"type": ["string", "null"], "format": "identifier",
        "x-reference-namespace": "native_infernal_preparation_failure_record"},
    "affected": {**_REPORT_ARTIFACT_SELECTION, "type": ["object", "null"]}})
IDENTIFIER_NAMESPACES = ("native_infernal_preparation_row", "native_infernal_preparation_name",
    "native_infernal_preparation_accession", "native_infernal_preparation_sha256",
    "native_infernal_preparation_failure_code", "native_infernal_preparation_failure_record")


def preparation_fact_sources():
    """Return independent typed receiver contracts, without sharing mutable data."""
    meanings = {
        "rows": "Explicitly requested existing preparation quantities and checks; generated output remains generated, with no annotation-confidence score.",
        "artifacts": "Explicitly selected retained artifact occurrences with actual digest, size and capture completeness.",
        "population": "Selection accounting for retained decoded rows and requested artifacts; zero decoded rows does not establish a biologically empty population.",
        "result_refs": "Original preparation execution-result references for the selected retained result.",
        "failures": "Requested recorded acquisition or grading failures with the original handoff and exact affected occurrence; these identifiers do not assert a successfully decoded row.",
    }
    schemas = {"rows": ROW_SCHEMA, "artifacts": ARTIFACT_SCHEMA,
               "population": POPULATION_SCHEMA, "result_refs": _REPORT_SOURCE_REF, "failures": FAILURE_SCHEMA}
    return {"execution_infernal_preparation_" + name: {"type": "array", "meaning": meanings[name],
        "report_schema": {"type": "array", "items": deepcopy(schema),
                          "x-source": "execution_infernal_preparation_" + name}}
        for name, schema in schemas.items()}


FACT_SOURCES = preparation_fact_sources()


def validate_preparation_result_selector(value, *, program, mode):
    """Validate the closed operation/collection selection and return a fresh copy."""
    require_finite_json(value)
    result = deepcopy(value)
    validate_schema(result, NATIVE_INFERNAL_PREPARATION_RESULT_SELECTOR_SCHEMA)
    catalog = preparation_projection_catalog(program, mode)
    for artifact in result["artifacts"]:
        if type(artifact["ordinal"]) is not int:
            _error("artifact_ordinal_integer_required")
    projection = result["projection"]
    if projection is not None:
        entry = catalog[projection["collection"]]
        if set(projection["quantities"]) - entry["quantities"].keys() or set(projection["checks"]) - set(entry["checks"]):
            _error("field_not_in_operation_collection")
        rows = projection["rows"]
        if "offset" in rows and any(type(rows[key]) is not int for key in ("offset", "limit")):
            _error("row_window_integer_required")
        for key in rows.get("record_keys", []):
            _text(key)
    return result


def _occurrence_maps(occurrences, sheet):
    require_finite_json(occurrences)
    if type(occurrences) is not list:
        _error("occurrences_list_required")
    by_ref, by_selection = {}, {}
    for occurrence in occurrences:
        _fields(occurrence, _OCCURRENCE_FIELDS)
        _text(occurrence["occurrence_ref"])
        _text(occurrence["relative_path"])
        validate_schema({key: occurrence[key] for key in _OCCURRENCE_ARTIFACT_SCHEMA["properties"]}, _OCCURRENCE_ARTIFACT_SCHEMA)
        if type(occurrence["ordinal"]) is not int or type(occurrence["size_bytes"]) is not int:
            _error("occurrence_integer_required")
        key = tuple(occurrence[name] for name in ("direction", "role", "ordinal"))
        if occurrence["occurrence_ref"] in by_ref or key in by_selection:
            _error("occurrence_identity_ambiguous")
        by_ref[occurrence["occurrence_ref"]] = occurrence
        by_selection[key] = occurrence
    for artifact in sheet["artifacts"]:
        occurrence = by_ref.get(artifact["artifact_ref"])
        if occurrence is None or any(artifact[key] != occurrence[key] for key in artifact if key != "artifact_ref"):
            _error("sheet_artifact_occurrence_mismatch")
    return by_ref, by_selection


def _field_inputs(inputs, occurrences):
    if type(inputs) is not list:
        _error("field_inputs_list_required")
    selected, seen = [], set()
    for source in inputs:
        _fields(source, {"locator", "field"})
        _text(source["field"])
        validate_locator(source["locator"])
        ref = source["locator"]["artifact_ref"]
        if ref not in occurrences:
            _error("field_input_occurrence_unknown")
        if ref not in seen:
            selected.append({key: occurrences[ref][key] for key in _CHECK_OCCURRENCE_SCHEMA["properties"]})
            seen.add(ref)
    return selected


def _validate_grading(grading, occurrences):
    _fields(grading, {"version", "operation", "sheet", "calculations"})
    if grading["version"] != "native_infernal_preparation_grading_v1":
        _error("grading_version_invalid")
    require_finite_json(grading)
    sheet, calculations = grading["sheet"], grading["calculations"]
    validate_common_sheet(sheet)
    _fields(calculations, {"schema", "operation", "parameters", "rows", "issues"})
    if (calculations["schema"] != CALCULATIONS_SCHEMA or grading["operation"] != sheet["operation"]
            or calculations["operation"] != sheet["operation"] or type(calculations["parameters"]) is not dict
            or type(calculations["rows"]) is not list or type(calculations["issues"]) is not list):
        _error("grading_operation_or_calculations_invalid")
    by_ref, by_selection = _occurrence_maps(occurrences, sheet)
    original_rows = {}
    for collection in _COLLECTIONS[:3]:
        for row in sheet[collection]:
            if type(row) is not dict or row.get("kind") not in _ROW_FIELDS:
                _error("row_kind_invalid")
            _fields(row, _ROW_FIELDS[row["kind"]])
            _text(row["record_key"])
            validate_locator(row["locator"])
            if row["locator"]["artifact_ref"] not in by_ref:
                _error("row_occurrence_unknown")
            if row["record_key"] in original_rows:
                _error("record_key_ambiguous")
            original_rows[row["record_key"]] = row
    catalog = preparation_projection_catalog(grading["operation"]["program"], grading["operation"]["mode"])
    keys = set()
    for row in calculations["rows"]:
        _fields(row, {"record_key", "components", "checks"})
        _text(row["record_key"])
        if row["record_key"] in keys:
            _error("calculation_record_key_ambiguous")
        keys.add(row["record_key"])
        if type(row["components"]) is not dict or type(row["checks"]) is not list:
            _error("calculation_row_invalid")
        for name, cell in row["components"].items():
            if "components." + name not in catalog["calculations"]["quantities"]:
                _error("component_undeclared")
            validate_value(cell)
            _field_inputs(cell["inputs"], by_ref)
        for check in row["checks"]:
            _fields(check, {"check", "outcome", "inputs"})
            if check["check"] not in catalog["calculations"]["checks"] or check["outcome"] not in {"pass", "fail", "unknown", "not_applicable"}:
                _error("check_undeclared")
            _field_inputs(check["inputs"], by_ref)
    return original_rows, by_ref, by_selection, catalog


def _quantity(row, path, descriptor):
    cell = row
    for key in path.split("."):
        if cell is None or type(cell) is dict and key not in cell:
            return {"path": path, "value": None, "state": "missing",
                    "basis": descriptor["basis"], "unit": descriptor["unit"]}
        if type(cell) is not dict:
            _error("declared_quantity_container_invalid")
        cell = cell[key]
    validate_value(cell)
    return {"path": path, **{key: cell[key] for key in ("value", "state", "basis", "unit")}}


def project_preparation_result(grading, *, selector, source_ref, occurrences):
    """Copy only selected scalar cells/checks and authenticated file occurrences.

    Calculation names/locators join only by unique original record_key. The A
    aggregate is identified by its declared input_model_count component, and has
    no single artifact attribution even when its key reuses a stdout record.
    """
    original_rows, by_ref, by_selection, catalog = _validate_grading(grading, occurrences)
    _text(source_ref)
    selector = validate_preparation_result_selector(selector, program=grading["operation"]["program"], mode=grading["operation"]["mode"])
    projection = selector["projection"]
    population = {"source_ref": source_ref, "collection": None, "total_records": 0, "returned_records": 0,
        "omitted_records": 0, "missing_record_keys": [], "requested_artifact_count": len(selector["artifacts"]),
        "returned_artifact_count": 0, "missing_artifacts": []}
    rows, artifacts = [], []
    if projection is not None:
        collection = projection["collection"]
        source = grading["calculations"]["rows"] if collection == "calculations" else grading["sheet"][collection]
        selection = projection["rows"]
        if "record_keys" in selection:
            by_key = {row["record_key"]: row for row in source}
            selected = [by_key[key] for key in selection["record_keys"] if key in by_key]
            population["missing_record_keys"] = [key for key in selection["record_keys"] if key not in by_key]
        else:
            selected = source[selection["offset"]:selection["offset"] + selection["limit"]]
        for row in selected:
            original = original_rows.get(row["record_key"]) if collection == "calculations" else row
            identity = {} if original is None else original.get("identity", original)
            name, accession = identity.get("name"), identity.get("accession")
            for identifier in (name, accession):
                if identifier is not None and type(identifier) is not str:
                    _error("native_identifier_invalid")
            aggregate = collection == "calculations" and grading["operation"]["program"] in {"cmconvert", "cmfetch", "cmpress"} and "input_model_count" in row["components"]
            artifact_ref = None if original is None or aggregate else by_ref[original["locator"]["artifact_ref"]]["artifact_ref"]
            checks = []
            if collection == "calculations":
                requested = set(projection["checks"])
                for check in row["checks"]:
                    if check["check"] in requested:
                        checks.append({"name": check["check"], "outcome": check["outcome"],
                                       "occurrences": _field_inputs(check["inputs"], by_ref)})
                present = {check["name"] for check in checks}
                checks.extend({"name": name, "outcome": "unknown", "occurrences": []}
                              for name in projection["checks"] if name not in present)
            rows.append({"record_key": row["record_key"], "kind": "calculation" if collection == "calculations" else row["kind"],
                "name": name, "accession": accession, "source_ref": source_ref, "artifact_ref": artifact_ref,
                "quantities": [_quantity(row, path, catalog[collection]["quantities"][path]) for path in projection["quantities"]],
                "checks": checks})
        population.update(collection=collection, total_records=len(source), returned_records=len(rows), omitted_records=len(source) - len(rows))
    for wanted in selector["artifacts"]:
        occurrence = by_selection.get(tuple(wanted[name] for name in ("direction", "role", "ordinal")))
        if occurrence is None:
            population["missing_artifacts"].append(deepcopy(wanted))
        else:
            artifacts.append({"source_ref": source_ref,
                **{key: occurrence[key] for key in _OCCURRENCE_ARTIFACT_SCHEMA["properties"]}})
    population["returned_artifact_count"] = len(artifacts)
    result = {"rows": rows, "artifacts": artifacts, "population": population}
    require_finite_json(result)
    return result


__all__ = ["NATIVE_INFERNAL_PREPARATION_RESULT_SELECTOR_SCHEMA", "validate_preparation_result_selector",
    "preparation_projection_catalog", "project_preparation_result", "preparation_fact_sources",
    "ROW_SCHEMA", "ARTIFACT_SCHEMA", "POPULATION_SCHEMA", "FAILURE_SCHEMA", "FAILURE_STAGES",
    "IDENTIFIER_NAMESPACES", "FACT_SOURCES"]
