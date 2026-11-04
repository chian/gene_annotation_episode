"""Finite somatic native contracts; no execution, admission or VCF arithmetic.

Software and reference associations are explicit supplied declarations. Physical
pins do not establish a loaded-library trace, database correctness or clinical
validity. The ordinary host must authenticate every File before dispatch.
"""
from __future__ import annotations

from copy import deepcopy
import math
from pathlib import PurePosixPath
import re


TOOL = "detect_and_annotate_somatic_mutations"
NATIVE_OPERATION = "somatic_variant_native"
RESULT_OPERATION = "somatic_variant_result"
NATIVE_REQUEST_VERSION = "somatic_variant_native_request_v1"
NATIVE_MANIFEST_VERSION = "somatic_variant_native_manifest_v1"
NATIVE_DIRECTORY = "somatic-variant-native"
STAGES = ("raw", "filtered", "annotated")
INPUTS = (
    ("tumor_bam", "tumor.bam", "bam"),
    ("tumor_bai", "tumor.bam.bai", "bai"),
    ("normal_bam", "normal.bam", "bam"),
    ("normal_bai", "normal.bam.bai", "bai"),
    ("reference_fasta", "reference.fasta", "fasta"),
    ("reference_fai", "reference.fasta.fai", "fai"),
    ("reference_dictionary", "reference.dict", "sam_sequence_dictionary"),
    ("intervals", "intervals.interval_list", "gatk_interval_list"),
)
OUTPUTS = (
    ("raw", "raw.vcf", "vcf"), ("raw_stats", "raw.vcf.stats", "gatk_mutect_stats"),
    ("filtered", "filtered.vcf", "vcf"),
    ("filtering_stats", "filtered.vcf.filteringStats.tsv", "gatk_filtering_stats"),
    ("annotated", "annotated.vcf", "vcf"),
    *((stage + "_" + stream, stage + "." + stream, "native_log")
        for stage in STAGES for stream in ("stdout", "stderr")
        if (stage, stream) != ("annotated", "stdout")),
    ("tumor_header", "tumor.header.sam", "sam_header_text"),
    ("normal_header", "normal.header.sam", "sam_header_text"),
)
POLICY = {"memory_bytes": 20 * 1024**3, "scratch_bytes": 4 * 1024**3, "wall_seconds": None}
PACKET_VERSION = "ordinary_somatic_variant_values_v1"
SOURCE_VERSION = "ordinary_somatic_variant_result_v1"
CONTEXT_VERSION = "somatic_variant_context_v1"
FACT_SOURCE = "somatic_variant_outcomes"
ISSUE_CODES = ("input_identity_conflict", "software_identity_conflict", "header_unavailable",
    "sample_identity_conflict", "software_changed_after_execution", "staged_input_changed",
    "native_nonzero_exit", "native_spawn_failed", "required_output_missing", "output_unavailable", "output_empty")


def require(value, code):
    if not value:
        raise ValueError("somatic_variant_" + code)


def closed(value, fields, code):
    require(type(value) is dict and set(value) == set(fields.split()), code)


def absolute_path(value):
    require(type(value) is str and value and not any(c in value for c in "\0\r\n\\"), "path_invalid")
    path = PurePosixPath(value)
    require(path.is_absolute() and str(path) == value and value != "/"
        and not value.startswith("//") and ".." not in path.parts, "path_invalid")
    return value


def _sha(value):
    return type(value) is str and re.fullmatch("[a-f0-9]{64}", value) is not None


def validate_physical_pin(value):
    closed(value, "path sha256 size_bytes", "physical_pin_invalid")
    absolute_path(value["path"])
    require(_sha(value["sha256"]) and type(value["size_bytes"]) is int
        and value["size_bytes"] >= 0, "physical_pin_invalid")
    return deepcopy(value)


def validate_file(value, *, format=None):
    closed(value, "artifact_ref sha256 size_bytes format", "file_invalid")
    require(_sha(value["sha256"]) and value["artifact_ref"] == "artifact_" + value["sha256"]
        and type(value["size_bytes"]) is int and value["size_bytes"] >= 0
        and type(value["format"]) is str and value["format"], "file_invalid")
    require(format is None or value["format"] == format, "file_format_conflict")
    return deepcopy(value)


def validate_source(value):
    require(value is None or type(value) is str and re.fullmatch("source_[a-f0-9]{24,64}", value),
        "source_invalid")
    return value


def _literal(value, code):
    require(type(value) is str and value and not any(c in value for c in "\0\r\n\t"), code)
    return value


def validate_somatic_parameters(value):
    closed(value, "java_heap_mb pair_hmm_implementation", "parameters_invalid")
    require(type(value["java_heap_mb"]) is int and 1 <= value["java_heap_mb"] < 20 * 1024,
        "java_heap_invalid")
    require(value["pair_hmm_implementation"] == "LOGLESS_CACHING", "pair_hmm_profile_invalid")
    return deepcopy(value)


def _database_files(identifier, files):
    require(type(identifier) is str and re.fullmatch("[A-Za-z0-9][A-Za-z0-9_.-]*", identifier),
        "database_id_invalid")
    require(type(files) is list and files, "database_files_invalid")
    names = []
    for row in files:
        closed(row, "relative_path sha256 size_bytes", "database_file_invalid")
        name = row["relative_path"]
        require(type(name) is str and name and not any(c in name for c in "\0\r\n\\"),
            "database_path_invalid")
        path = PurePosixPath(name)
        require(bool(path.parts) and not path.is_absolute() and str(path) == name and ".." not in path.parts
            and path.parts[0] == identifier, "database_path_invalid")
        require(_sha(row["sha256"]) and type(row["size_bytes"]) is int and row["size_bytes"] >= 0,
            "database_file_invalid")
        names.append(name)
    require(len(names) == len(set(names)), "database_paths_duplicate")
    require(identifier + "/snpEffectPredictor.bin" in names, "database_predictor_missing")


def validate_somatic_software(value):
    """Validate declared physical materials without discovering or opening them."""
    closed(value, "java gatk_jar snpeff_jar snpeff_config runtime_files database reported_versions",
        "software_invalid")
    for key in ("java", "gatk_jar", "snpeff_jar", "snpeff_config"):
        validate_physical_pin(value[key])
    require(type(value["runtime_files"]) is list and value["runtime_files"], "runtime_files_invalid")
    pins = [validate_physical_pin(pin) for pin in value["runtime_files"]]
    require(len({pin["path"] for pin in pins}) == len(pins), "runtime_paths_duplicate")
    require(value["java"] in pins, "java_runtime_pin_missing")
    database = value["database"]
    closed(database, "id root files", "database_invalid")
    absolute_path(database["root"])
    _database_files(database["id"], database["files"])
    closed(value["reported_versions"], "java gatk snpeff", "versions_invalid")
    for version in value["reported_versions"].values():
        require(version is None or type(version) is str and bool(version), "version_invalid")
    return deepcopy(value)


def validate_somatic_native_request(value):
    closed(value, "version inputs sample_ids reference_id software parameters", "native_request_invalid")
    require(value["version"] == NATIVE_REQUEST_VERSION, "native_request_version_invalid")
    require(type(value["inputs"]) is list and len(value["inputs"]) in (7, 8), "inputs_invalid")
    for descriptor, (role, _name, format) in zip(value["inputs"], INPUTS):
        closed(descriptor, "role path file source_ref", "input_invalid")
        require(descriptor["role"] == role, "input_order_invalid")
        absolute_path(descriptor["path"])
        validate_file(descriptor["file"], format=format)
        validate_source(descriptor["source_ref"])
    closed(value["sample_ids"], "tumor normal", "sample_ids_invalid")
    for sample in value["sample_ids"].values():
        _literal(sample, "sample_id_invalid")
    require(value["sample_ids"]["tumor"] != value["sample_ids"]["normal"], "sample_ids_identical")
    require(value["reference_id"] is None or type(value["reference_id"]) is str
        and bool(value["reference_id"]), "reference_id_invalid")
    validate_somatic_software(value["software"])
    validate_somatic_parameters(value["parameters"])
    return deepcopy(value)


def somatic_native_argv(request, stage, *, directory):
    """Exact selected Java CLI; no shell, default download or filename inference."""
    request = validate_somatic_native_request(request)
    require(stage in STAGES, "stage_invalid")
    absolute_path(str(directory))
    software, parameters = request["software"], request["parameters"]
    java = [software["java"]["path"], "-Xmx" + str(parameters["java_heap_mb"]) + "m",
        "-Djava.io.tmpdir=" + str(PurePosixPath(directory) / "tmp"),
        "-Duser.home=" + str(PurePosixPath(directory) / "home")]
    if stage == "raw":
        result = java + ["-jar", software["gatk_jar"]["path"], "Mutect2", "-R", "reference.fasta",
            "-I", "tumor.bam", "-I", "normal.bam", "-normal", request["sample_ids"]["normal"],
            "--pair-hmm-implementation", parameters["pair_hmm_implementation"], "-O", "raw.vcf"]
        if len(request["inputs"]) == 8:
            result += ["-L", "intervals.interval_list"]
        return result
    if stage == "filtered":
        return java + ["-jar", software["gatk_jar"]["path"], "FilterMutectCalls", "-R", "reference.fasta",
            "-V", "raw.vcf", "--stats", "raw.vcf.stats", "-O", "filtered.vcf"]
    return java + ["-jar", software["snpeff_jar"]["path"], "ann", "-config",
        software["snpeff_config"]["path"], "-dataDir", software["database"]["root"],
        "-nodownload", "-noLog", "-noStats", software["database"]["id"], "filtered.vcf"]


def validate_somatic_native_manifest(value):
    """Check declarations/sequence, without authenticating a producer or bytes."""
    closed(value, "version request directory input_staging stages headers files issues", "manifest_invalid")
    require(value["version"] == NATIVE_MANIFEST_VERSION, "manifest_version_invalid")
    request = validate_somatic_native_request(value["request"])
    absolute_path(value["directory"])
    require(PurePosixPath(value["directory"]).name == NATIVE_DIRECTORY, "manifest_directory_invalid")
    require(type(value["input_staging"]) is list and len(value["input_staging"]) == len(request["inputs"]),
        "input_staging_invalid")
    for staged, selected in zip(value["input_staging"], request["inputs"]):
        closed(staged, "role state observed", "input_staging_invalid")
        require(staged["role"] == selected["role"] and staged["state"] in
            ("not_attempted", "verified", "failed"), "input_staging_invalid")
        if staged["observed"] is not None:
            closed(staged["observed"], "sha256 size_bytes", "staged_identity_invalid")
            require(_sha(staged["observed"]["sha256"]) and type(staged["observed"]["size_bytes"]) is int
                and staged["observed"]["size_bytes"] >= 0, "staged_identity_invalid")
        if staged["state"] == "verified":
            require(staged["observed"] == {k: selected["file"][k] for k in ("sha256", "size_bytes")},
                "staged_identity_conflict")
        elif staged["state"] == "not_attempted":
            require(staged["observed"] is None, "unattempted_input_conflict")
    require(type(value["issues"]) is list and all(type(x) is str and x in ISSUE_CODES for x in value["issues"])
        and len(value["issues"]) == len(set(value["issues"])), "manifest_issues_invalid")
    require(type(value["stages"]) is list and len(value["stages"]) == 3, "manifest_stages_invalid")
    previous_succeeded = True
    for row, stage in zip(value["stages"], STAGES):
        closed(row, "stage argv prerequisites state returncode started_at_utc ended_at_utc", "stage_record_invalid")
        require(row["stage"] == stage and row["argv"] == somatic_native_argv(request, stage,
            directory=value["directory"]), "stage_argv_conflict")
        state = row["state"]
        require(state in ("not_attempted", "spawn_failed", "exited"), "stage_state_invalid")
        if state == "not_attempted":
            require(row["returncode"] is None and row["started_at_utc"] is None
                and row["ended_at_utc"] is None and row["prerequisites"] == [], "unattempted_stage_conflict")
        else:
            require(previous_succeeded, "stage_prerequisite_conflict")
            require(all(type(row[k]) is str and re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z", row[k])
                for k in ("started_at_utc", "ended_at_utc")), "stage_time_invalid")
            require((state == "exited" and type(row["returncode"]) is int)
                or (state == "spawn_failed" and row["returncode"] is None), "stage_exit_invalid")
            required = () if stage == "raw" else (("raw", "raw_stats") if stage == "filtered" else ("filtered",))
            require(type(row["prerequisites"]) is list
                and [item.get("role") for item in row["prerequisites"] if type(item) is dict] == list(required),
                "stage_prerequisites_invalid")
            for item in row["prerequisites"]:
                closed(item, "role sha256 size_bytes", "stage_prerequisite_invalid")
                require(_sha(item["sha256"]) and type(item["size_bytes"]) is int and item["size_bytes"] > 0,
                    "stage_prerequisite_invalid")
        previous_succeeded = state == "exited" and row["returncode"] == 0
    require(type(value["headers"]) is list and len(value["headers"]) <= 2, "headers_invalid")
    for ordinal, header in enumerate(value["headers"]):
        closed(header, "role inspection sample_ids", "header_invalid")
        require(header["role"] == ("tumor", "normal")[ordinal], "header_order_invalid")
        require(type(header["sample_ids"]) is list and all(type(x) is str and x
            for x in header["sample_ids"]) and len(header["sample_ids"]) == len(set(header["sample_ids"])),
            "header_samples_invalid")
        from .native_atac_differential_contracts import validate_atac_record
        inspection = validate_atac_record("HeaderExtraction", header["inspection"])
        selected = request["inputs"][ordinal * 2]
        require(inspection["input_file"] == selected["file"]
            and inspection["input_key"] == selected["role"] and inspection["input_ordinal"] == ordinal,
            "header_input_conflict")
        require(inspection["header"]["relative_path"] == NATIVE_DIRECTORY + "/" + header["role"] + ".header.sam",
            "header_path_conflict")
    require(type(value["files"]) is list, "manifest_files_invalid")
    allowed = {role: (name, format) for role, name, format in OUTPUTS}
    for role, name, format in INPUTS[:len(request["inputs"])]:
        allowed[role] = (name, format)
    roles = []
    for row in value["files"]:
        closed(row, "role relative_path format sha256 size_bytes", "manifest_file_invalid")
        require(type(row["role"]) is str and row["role"] in allowed, "manifest_file_role_invalid")
        name, format = allowed[row["role"]]
        require(row["relative_path"] == NATIVE_DIRECTORY + "/" + name and row["format"] == format
            and _sha(row["sha256"]) and type(row["size_bytes"]) is int and row["size_bytes"] >= 0,
            "manifest_file_invalid")
        roles.append(row["role"])
    require(len(roles) == len(set(roles)), "manifest_file_duplicate")
    declared = {row["role"]: row for row in value["files"]}
    if any(row["state"] != "not_attempted" for row in value["stages"]):
        require(len(value["headers"]) == 2 and all(header["inspection"]["producer_outcome"] == "succeeded"
            and header["sample_ids"] == [request["sample_ids"][header["role"]]] for header in value["headers"]),
            "native_sample_association_unverified")
        require(all(row["state"] == "verified" for row in value["input_staging"]),
            "native_input_identity_unverified")
    require(any(row["state"] == "spawn_failed" for row in value["stages"])
        == ("native_spawn_failed" in value["issues"]), "spawn_issue_conflict")
    require(any(row["state"] == "exited" and row["returncode"] != 0 for row in value["stages"])
        == ("native_nonzero_exit" in value["issues"]), "exit_issue_conflict")
    require(any(row["state"] == "failed" for row in value["input_staging"])
        == ("input_identity_conflict" in value["issues"]), "staging_issue_conflict")
    changed = any(row["role"] in declared and any(declared[row["role"]][key] != selected["file"][key]
        for key in ("sha256", "size_bytes")) for row, selected in zip(value["input_staging"], request["inputs"]))
    require(changed == ("staged_input_changed" in value["issues"]), "staged_change_issue_conflict")
    return deepcopy(value)


def somatic_context_from_manifest(manifest):
    """Copy process/association facts; infer no sample, assembly or annotation truth."""
    manifest = validate_somatic_native_manifest(manifest)
    request = manifest["request"]
    software = request["software"]
    observations = {row["role"]: row["sample_ids"] for row in manifest["headers"]}
    return validate_somatic_context({"version": CONTEXT_VERSION,
        "inputs": [{"role": row["role"], "file": row["file"], "source_ref": row["source_ref"]}
            for row in request["inputs"]],
        "sample_ids": {"declared": request["sample_ids"], "observed": {
            role: observations.get(role, []) for role in ("tumor", "normal")}},
        "reference_id": request["reference_id"],
        "software": {**{key: {k: software[key][k] for k in ("sha256", "size_bytes")}
            for key in ("java", "gatk_jar", "snpeff_jar", "snpeff_config")},
            "reported_versions": software["reported_versions"],
            "loaded_dependencies_verified": False},
        "annotation_database": {"id": software["database"]["id"],
            "files": software["database"]["files"], "reference_association": "caller_declared"},
        "parameters": request["parameters"],
        "stages": [{k: row[k] for k in ("stage", "state", "returncode")} for row in manifest["stages"]],
        "outputs": [{k: row[k] for k in ("role", "sha256", "size_bytes")} for row in manifest["files"]
            if row["role"] in STAGES],
        "issues": manifest["issues"],
        "definitions": {"native_exit": "process status, not VCF validity or biological correctness",
            "software": "selected byte pins and supplied version metadata, not observed loaded-library or build-source equivalence",
            "population": "retained VCF record slots and explicitly selected ALT/sample/GT observations",
            "filter": "literal native FILTER fields; no caller-independent somatic truth assignment",
            "annotation": "literal native INFO annotations; no additional effect or clinical scoring",
            "sample_reference_database": "explicit supplied associations and observed BAM SM labels; no filename or assembly inference"}})


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def somatic_result_schema(kind="Value"):
    """Detached closed schemas; the VCF owner remains the only value authority."""
    from . import vcf_result_measurements as vcf
    definitions = deepcopy(vcf.vcf_result_schema("Value")["$defs"])
    integer = {"type": "integer", "minimum": 0}
    text = {"type": "string", "minLength": 1}
    nullable_text = {"anyOf": [{"type": "null"}, text]}
    identity = _object({"sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"}, "size_bytes": integer})
    source = {"anyOf": [{"type": "null"}, {"type": "string", "pattern": "^source_[a-f0-9]{24,64}$"}]}
    sample = _object({"tumor": text, "normal": text})
    context = _object({"version": {"const": CONTEXT_VERSION},
        "inputs": {"type": "array", "minItems": 7, "maxItems": 8, "items": _object({
            "role": {"enum": [row[0] for row in INPUTS]}, "file": {"$ref": "#/$defs/File"}, "source_ref": source})},
        "sample_ids": _object({"declared": sample, "observed": _object({role: {
            "type": "array", "items": text, "uniqueItems": True} for role in ("tumor", "normal")})}),
        "reference_id": nullable_text,
        "software": _object({**{key: deepcopy(identity) for key in ("java", "gatk_jar", "snpeff_jar", "snpeff_config")},
            "reported_versions": _object({key: nullable_text for key in ("java", "gatk", "snpeff")}),
            "loaded_dependencies_verified": {"const": False}}),
        "annotation_database": _object({"id": text, "files": {"type": "array", "minItems": 1,
            "items": _object({"relative_path": text, **identity["properties"]})},
            "reference_association": {"const": "caller_declared"}}),
        "parameters": _object({"java_heap_mb": {"type": "integer", "minimum": 1, "maximum": 20479},
            "pair_hmm_implementation": {"const": "LOGLESS_CACHING"}}),
        "stages": {"type": "array", "minItems": 3, "maxItems": 3, "items": _object({
            "stage": {"enum": list(STAGES)}, "state": {"enum": ["not_attempted", "spawn_failed", "exited"]},
            "returncode": {"type": ["integer", "null"]}})},
        "outputs": {"type": "array", "maxItems": 3, "items": _object({"role": {"enum": list(STAGES)},
            **identity["properties"]})}, "issues": {"type": "array", "items": {"enum": list(ISSUE_CODES)}, "uniqueItems": True},
        "definitions": _object({key: {"const": value} for key, value in {
            "native_exit": "process status, not VCF validity or biological correctness",
            "software": "selected byte pins and supplied version metadata, not observed loaded-library or build-source equivalence",
            "population": "retained VCF record slots and explicitly selected ALT/sample/GT observations",
            "filter": "literal native FILTER fields; no caller-independent somatic truth assignment",
            "annotation": "literal native INFO annotations; no additional effect or clinical scoring",
            "sample_reference_database": "explicit supplied associations and observed BAM SM labels; no filename or assembly inference"}.items()})})
    definitions["SomaticContext"] = context
    definitions["SomaticSelection"] = _object({"stage": {"enum": list(STAGES)}, "vcf": {"$ref": "#/$defs/Selection"}})
    definitions["SomaticValue"] = _object({"version": {"const": PACKET_VERSION},
        "selection": {"$ref": "#/$defs/SomaticSelection"}, "context": {"$ref": "#/$defs/SomaticContext"},
        "value": {"$ref": "#/$defs/Value"}})
    definitions["SomaticReturn"] = _object({**definitions["SomaticValue"]["properties"],
        "source_ref": {"type": "string", "pattern": "^source_[a-f0-9]{24,64}$"}})
    selected_file = _object({"role": {"enum": [row[0] for row in INPUTS]},
        "namespace": {"enum": ["source", "artifact"]}, "reference": text,
        "max_bytes": {"type": "integer", "minimum": 1, "maximum": POLICY["scratch_bytes"]}})
    run_arguments = _object({"mode": {"const": "run_native"},
        "inputs": {"type": "array", "minItems": 7, "maxItems": 8, "items": selected_file},
        "sample_ids": sample, "reference_id": nullable_text, "annotation_database_id": text,
        "selection": {"$ref": "#/$defs/SomaticSelection"}})
    saved_arguments = _object({"mode": {"const": "calculate_saved"}, "result_ref": text,
        "selection": {"$ref": "#/$defs/SomaticSelection"}})
    read_arguments = _object({"mode": {"const": "read_stored"}, "result_ref": text})
    definitions["SomaticArguments"] = {"oneOf": [run_arguments, saved_arguments, read_arguments]}
    names = {"Arguments": "SomaticArguments", "Context": "SomaticContext", "Selection": "SomaticSelection",
        "Value": "SomaticValue", "Return": "SomaticReturn"}
    require(kind in names, "schema_kind_invalid")
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": "#/$defs/" + names[kind], "$defs": definitions}


def _wire(value, kind):
    from jsonschema import Draft202012Validator, validators
    strict = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER
        .redefine("integer", lambda _checker, x: type(x) is int)
        .redefine("number", lambda _checker, x: type(x) is int or type(x) is float and math.isfinite(x))
        .redefine("array", lambda _checker, x: type(x) is list)
        .redefine("object", lambda _checker, x: type(x) is dict))
    require(strict(somatic_result_schema(kind)).is_valid(value), kind.lower() + "_invalid")
    return deepcopy(value)


def validate_somatic_context(value):
    value = _wire(value, "Context")
    _database_files(value["annotation_database"]["id"], value["annotation_database"]["files"])
    require([row["role"] for row in value["inputs"]] == [row[0] for row in INPUTS[:len(value["inputs"])]],
        "context_input_order_invalid")
    for row, (_role, _name, format) in zip(value["inputs"], INPUTS):
        validate_file(row["file"], format=format)
        validate_source(row["source_ref"])
    require(value["sample_ids"]["declared"]["tumor"] != value["sample_ids"]["declared"]["normal"],
        "sample_ids_identical")
    require([row["stage"] for row in value["stages"]] == list(STAGES), "context_stage_order_invalid")
    previous = True
    for row in value["stages"]:
        require((row["state"] == "exited" and type(row["returncode"]) is int)
            or (row["state"] != "exited" and row["returncode"] is None), "context_exit_invalid")
        if row["state"] != "not_attempted":
            require(previous, "context_stage_prerequisite_conflict")
        previous = row["state"] == "exited" and row["returncode"] == 0
    if any(row["state"] != "not_attempted" for row in value["stages"]):
        require(all(value["sample_ids"]["observed"][role] == [value["sample_ids"]["declared"][role]]
            for role in ("tumor", "normal")), "context_sample_association_conflict")
    roles = [row["role"] for row in value["outputs"]]
    require(roles == [stage for stage in STAGES if stage in roles] and len(roles) == len(set(roles)),
        "context_output_order_invalid")
    return value


def validate_somatic_selection(value, *, sheet=None):
    from . import vcf_result_measurements as vcf
    value = _wire(value, "Selection")
    value["vcf"] = vcf.validate_vcf_selection(value["vcf"], sheet=sheet)
    return value


def validate_somatic_arguments(value):
    value = _wire(value, "Arguments")
    if value["mode"] == "run_native":
        require([row["role"] for row in value["inputs"]] == [row[0] for row in INPUTS[:len(value["inputs"])]],
            "arguments_input_order_invalid")
        for row in value["inputs"]:
            pattern = r"source_[a-f0-9]{24,64}" if row["namespace"] == "source" else r"artifact_[a-f0-9]{64}"
            require(re.fullmatch(pattern, row["reference"]) is not None, "arguments_input_reference_invalid")
        for sample in value["sample_ids"].values():
            _literal(sample, "sample_id_invalid")
        require(value["sample_ids"]["tumor"] != value["sample_ids"]["normal"], "sample_ids_identical")
        require(re.fullmatch("[A-Za-z0-9][A-Za-z0-9_.-]*", value["annotation_database_id"]) is not None,
            "arguments_database_invalid")
    else:
        require(validate_source(value["result_ref"]) is not None, "arguments_result_source_missing")
    if value["mode"] != "read_stored":
        validate_somatic_selection(value["selection"])
    return value


def build_somatic_packet(*, context, selection, components):
    from . import vcf_result_measurements as vcf
    components = vcf.validate_vcf_components(components)
    return validate_somatic_packet({"version": PACKET_VERSION, "context": context,
        "selection": selection, "value": components["value"]})


def validate_somatic_stage_input(value, *, context, stage):
    """Join an already validated VCF Input to retained native byte metadata."""
    context = validate_somatic_context(context)
    require(stage in STAGES, "stage_invalid")
    closed(value, "input_id retained_file original_file source_ref capture", "stage_input_descriptor_invalid")
    output = next((row for row in context["outputs"] if row["role"] == stage), None)
    if value["capture"]["state"] == "complete":
        require(output is not None and value["retained_file"] is not None and all(
            value["retained_file"][key] == output[key] for key in ("sha256", "size_bytes")),
            "packet_native_bytes_conflict")
    elif value["retained_file"] is not None:
        require(output is not None and value["retained_file"]["size_bytes"] <= output["size_bytes"],
            "packet_capture_size_conflict")
    if value["capture"]["original_size_bytes"] is not None:
        require(output is not None and value["capture"]["original_size_bytes"] == output["size_bytes"],
            "packet_original_size_conflict")
    return deepcopy(value)


def validate_somatic_packet(value):
    from . import vcf_result_measurements as vcf
    value = _wire(value, "Value")
    value["context"] = validate_somatic_context(value["context"])
    value["selection"] = validate_somatic_selection(value["selection"])
    value["value"] = vcf._validate_value(value["value"])
    require(value["selection"]["vcf"] == value["value"]["selection"], "packet_selection_conflict")
    validate_somatic_stage_input(value["value"]["input"], context=value["context"], stage=value["selection"]["stage"])
    return value


def project_somatic_return(packet, source_ref):
    packet = validate_somatic_packet(packet)
    require(validate_source(source_ref) is not None, "return_source_missing")
    return {**packet, "source_ref": source_ref}


def validate_somatic_return(value):
    value = _wire(value, "Return")
    source_ref = value.pop("source_ref")
    return project_somatic_return(value, source_ref)


def somatic_fact_sources():
    schema = somatic_result_schema("Return")
    schema.update({"$id": "https://gene-annotation.invalid/somatic-variant-facts-v1"})
    schema["$defs"]["SomaticReturn"]["properties"]["source_ref"]["x-reference-namespace"] = "source"
    schema["$defs"]["SomaticReturn"]["properties"]["source_ref"]["format"] = "reference"
    schema.pop("$ref")
    schema.update({"type": "array", "items": {"$ref": "#/$defs/SomaticReturn"}})
    return {FACT_SOURCE: {"type": "array", "report_schema": schema}}
