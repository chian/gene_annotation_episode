"""Pure contracts for five explicitly selected local two-sequence BLAST jobs.

The option vocabulary follows the retained BLAST+ 2.17.0 installed help in
verification/tool_graders_blast_program_boundaries_2026-10-26_290/installed_help.
Validation and compilation perform no discovery, file access or execution.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import PurePosixPath
import re

from jsonschema import Draft202012Validator

PROGRAMS = ("blastn", "blastp", "blastx", "tblastn", "tblastx")
RESERVED_ENVIRONMENT = frozenset({"TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME"})
_STR = {"type": "string", "minLength": 1, "pattern": "^[^\\u0000]+$"}
_NULL_STR = {"anyOf": [_STR, {"type": "null"}]}
_SHA = {"type": "string", "pattern": "^[0-9a-fA-F]{64}$"}
_ABS = {"type": "string", "pattern": "^/[^\\u0000\\n\\r]+$"}


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


NATIVE_BLAST_JOB_SCHEMA = _object({
    "version": {"const": "native_blast_job_v1"}, "program": {"enum": list(PROGRAMS)},
    "mode": {"const": "pairwise"},
    "software": _object({"executable": _ABS, "sha256": _SHA, "engine_version": _NULL_STR}),
    "environment": {"type": "object", "additionalProperties": {"type": "string"}},
    "operands": {"type": "array", "minItems": 2, "maxItems": 2, "items": _object({
        "role": {"enum": ["query_sequence", "subject_sequence"]}, "path": _ABS,
        "format": {"const": "fasta"}, "sha256": _SHA,
        "size_bytes": {"type": "integer", "minimum": 0}, "artifact_ref": _NULL_STR})},
    "operand_bindings": {"type": "array", "items": _object({
        "operand_role": {"enum": ["query_sequence", "subject_sequence"]},
        "record_ordinal": {"const": 0}, "native_name": _NULL_STR,
        "native_accession": _NULL_STR, "subject_ref": _NULL_STR, "reference_ref": _NULL_STR})},
    "options": {"type": "array", "items": _STR},
    "outputs": {"type": "array", "minItems": 3, "maxItems": 3, "items": _object({
        "role": {"enum": ["stdout", "stderr", "primary_report", "tabular_report"]},
        "format": {"enum": ["text", "json15", "tabular6", "tabular7"]},
        "relative_path": _STR,
        "fields": {"anyOf": [{"type": "array", "minItems": 1, "uniqueItems": True, "items": _STR}, {"type": "null"}]},
        "delimiter": {"anyOf": [{"type": "string", "minLength": 1, "maxLength": 1}, {"type": "null"}]}})},
    "metadata": {"type": "object"}, "grading_parameters": {"type": "object", "maxProperties": 0},
})
NATIVE_BLAST_REQUESTED_JOB_SCHEMA = _object({
    "argv": {"type": "array", "minItems": 1, "items": _STR},
    "environment": {"type": "object", "additionalProperties": {"type": "string"}},
    "native_blast": NATIVE_BLAST_JOB_SCHEMA,
})


def finite_json_copy(value):
    def check(item):
        if type(item) in {str, int, bool} or item is None:
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                check(child)
            return
        raise ValueError("native_blast_finite_json_required")
    check(value)
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def native_blast_digest(value):
    return hashlib.sha256(json.dumps(finite_json_copy(value), sort_keys=True,
        separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _schema(value, schema):
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    if error is not None:
        raise ValueError("native_blast_schema:" + ".".join(map(str, error.absolute_path)) + ":" + error.validator)


def _absolute(path):
    if (type(path) is not str or not path.startswith("/") or path.startswith("//")
            or any(c in path for c in ("\0", "\n", "\r"))
            or ".." in path.split("/") or str(PurePosixPath(path)) != path):
        raise ValueError("native_blast_absolute_normalized_path_required")


def _relative(path):
    if (not path or PurePosixPath(path).is_absolute() or path in {".", ".."}
            or ".." in path.split("/") or str(PurePosixPath(path)) != path
            or any(c in path for c in ("\0", "\n", "\r", "\\"))):
        raise ValueError("native_blast_confined_relative_output_required")
    if path.split("/")[0] in {"inputs", "tmp", "cache", "bundle.json", ".native-blast-owner.json",
                              ".bundle.json.writing", "..native-blast-owner.json.writing"}:
        raise ValueError("native_blast_reserved_output_path")


# Explicit columns only: 'std' is version-dependent and must not be expanded by
# assuming an older formatter's defaults (2.17.0 documents qaccver/saccver).
TABULAR_FIELDS = frozenset("qseqid qgi qacc qaccver qlen sseqid sallseqid sgi sallgi sacc saccver sallacc slen qstart qend sstart send qseq sseq evalue bitscore score length pident nident mismatch positive gapopen gaps ppos frames qframe sframe btop staxid ssciname scomname sblastname sskingdom staxids sscinames scomnames sblastnames sskingdoms stitle salltitles sstrand qcovs qcovhsp qcovus".split())
_COMPILER_FLAGS = {"-query", "-subject", "-out", "-outfmt", "-html"}
_FORBIDDEN = {"-db", "-remote", "-import_search_strategy", "-export_search_strategy",
    "-in_pssm", "-gilist", "-seqidlist", "-negative_gilist", "-negative_seqidlist",
    "-taxids", "-negative_taxids", "-taxidlist", "-negative_taxidlist", "-no_taxid_expansion",
    "-entrez_query", "-db_soft_mask", "-db_hard_mask", "-filtering_db", "-window_masker_taxid",
    "-window_masker_db", "-use_index", "-index_name", "-ipglist", "-negative_ipglist"}
_TASKS = {"blastn": {"blastn", "blastn-short", "dc-megablast", "megablast", "rmblastn"},
    "blastp": {"blastp", "blastp-fast", "blastp-short"},
    "blastx": {"blastx", "blastx-fast"}, "tblastn": {"tblastn", "tblastn-fast"}}
_GENCODES = set(range(1, 7)) | set(range(9, 17)) | set(range(21, 32)) | {33}


def _options(job):
    program = job["program"]
    flags = {"-lcase_masking", "-parse_deflines", "-show_gis", "-subject_besthit"}
    values = {"-query_loc": "range", "-subject_loc": "range", "-evalue": "real",
        "-word_size": "word_size", "-qcov_hsp_perc": "percent", "-max_hsps": "positive_integer",
        "-xdrop_ungap": "real", "-searchsp": "nonnegative_integer", "-dbsize": "integer",
        "-soft_masking": "boolean", "-culling_limit": "nonnegative_integer",
        "-best_hit_overhang": "open_half", "-best_hit_score_edge": "open_half",
        "-window_size": "nonnegative_integer", "-max_target_seqs": "positive_integer",
        "-num_threads": "positive_integer", "-num_descriptions": "nonnegative_integer",
        "-num_alignments": "nonnegative_integer", "-line_length": "positive_integer",
        "-sorthits": "sort", "-sorthsps": "sort"}
    if program != "tblastx":
        flags.add("-ungapped")
        values.update({"-task": "task", "-gapopen": "integer", "-gapextend": "integer",
            "-xdrop_gap": "real", "-xdrop_gap_final": "real", "-mt_mode": "mt_mode"})
    if program in {"blastn", "blastx", "tblastx"}:
        values["-strand"] = "strand"
    if program == "blastn":
        flags.add("-no_greedy")
        values.update({"-perc_identity": "percent", "-penalty": "nonpositive_integer",
            "-reward": "nonnegative_integer", "-min_raw_gapped_score": "integer",
            "-template_type": "template_type", "-template_length": "template_length",
            "-dust": "dust", "-off_diagonal_range": "nonnegative_integer"})
    else:
        values.update({"-matrix": "matrix", "-threshold": "nonnegative", "-seg": "seg"})
        if program != "tblastx":
            flags.add("-use_sw_tback")
            values["-comp_based_stats"] = "composition"
    if program in {"blastx", "tblastx"}:
        values["-query_gencode"] = "gencode"
    if program in {"tblastn", "tblastx"}:
        values["-db_gencode"] = "gencode"
    if program in {"blastx", "tblastn", "tblastx"}:
        values.update({"-sum_stats": "boolean", "-max_intron_length": "nonnegative_integer"})
    selected, tokens, i = {}, job["options"], 0
    while i < len(tokens):
        flag = tokens[i]
        if flag in _COMPILER_FLAGS:
            raise ValueError("native_blast_compiler_owned_option:" + flag)
        if flag in _FORBIDDEN:
            raise ValueError("native_blast_forbidden_operand_or_resource_option:" + flag)
        if flag not in flags | values.keys():
            raise ValueError("native_blast_unsupported_option:" + flag)
        if flag in selected:
            raise ValueError("native_blast_duplicate_option:" + flag)
        selected[flag] = None
        i += 1
        if flag in flags:
            continue
        if i == len(tokens):
            raise ValueError("native_blast_option_operand_required:" + flag)
        raw, kind = tokens[i], values[flag]
        selected[flag], i = raw, i + 1
        valid = False
        if kind == "task":
            valid = raw in _TASKS[program]
        elif kind == "strand":
            valid = raw in {"plus", "minus", "both"}
        elif kind == "boolean":
            valid = raw.lower() in {"true", "false", "t", "f", "yes", "no", "y", "n", "1", "0"}
        elif kind == "composition":
            valid = raw in {"D", "d", "0", "F", "f", "1", "2", "T", "t", "3"}
        elif kind == "matrix":
            valid = re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", raw) is not None
        elif kind == "template_type":
            valid = raw in {"coding", "coding_and_optimal", "optimal"}
        elif kind == "range":
            match = re.fullmatch(r"([1-9]\d*)-([1-9]\d*)", raw)
            valid = bool(match and int(match[1]) <= int(match[2]))
        elif kind in {"dust", "seg"}:
            parts = raw.split()
            valid = raw in {"yes", "no"}
            if len(parts) == 3:
                try:
                    valid = (bool(re.fullmatch(r"\d+", parts[0])) and int(parts[0]) > 0
                        and all(math.isfinite(float(x)) and float(x) >= 0 for x in parts[1:]))
                    if kind == "dust":
                        valid &= all(re.fullmatch(r"\d+", x) is not None for x in parts)
                except ValueError:
                    valid = False
        else:
            try:
                number = float(raw)
                valid = math.isfinite(number)
                if "integer" in kind or kind in {"gencode", "template_length", "sort", "mt_mode", "word_size"}:
                    valid &= re.fullmatch(r"[+-]?\d+", raw) is not None
                if kind == "positive_integer": valid &= number > 0
                if kind in {"nonnegative_integer", "nonnegative"}: valid &= number >= 0
                if kind == "nonpositive_integer": valid &= number <= 0
                if kind == "percent": valid &= 0 <= number <= 100
                if kind == "open_half": valid &= 0 < number < .5
                if kind == "gencode": valid &= number in _GENCODES
                if kind == "template_length": valid &= number in {16, 18, 21}
                if kind == "sort": valid &= 0 <= number <= 4
                if kind == "mt_mode": valid &= 0 <= number <= 2
                if kind == "word_size": valid &= number >= (4 if program == "blastn" else 2)
            except (ValueError, OverflowError):
                valid = False
        if not valid:
            raise ValueError("native_blast_invalid_option_operand:" + flag)
    for first, second in (("-culling_limit", "-best_hit_overhang"), ("-culling_limit", "-best_hit_score_edge"),
                          ("-max_target_seqs", "-num_descriptions"), ("-max_target_seqs", "-num_alignments")):
        if first in selected and second in selected:
            raise ValueError("native_blast_conflicting_options:" + first + ":" + second)
    for flag, required in (("-mt_mode", "-num_threads"), ("-template_type", "-template_length"),
                           ("-template_length", "-template_type")):
        if flag in selected and required not in selected:
            raise ValueError("native_blast_required_option:" + flag + ":" + required)
    return selected


def validate_native_blast_job(value):
    job = finite_json_copy(value)
    _schema(job, NATIVE_BLAST_JOB_SCHEMA)
    _absolute(job["software"]["executable"])
    for key, item in job["environment"].items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or "\0" in item:
            raise ValueError("native_blast_invalid_environment")
        if key in RESERVED_ENVIRONMENT:
            raise ValueError("native_blast_compiler_owned_environment:" + key)
    roles = set()
    for row in job["operands"]:
        if row["role"] in roles:
            raise ValueError("native_blast_duplicate_operand_role")
        roles.add(row["role"])
        _absolute(row["path"])
    if roles != {"query_sequence", "subject_sequence"}:
        raise ValueError("native_blast_query_and_subject_required")
    seen = set()
    for row in job["operand_bindings"]:
        if type(row["record_ordinal"]) is not int or row["record_ordinal"] != 0:
            raise ValueError("native_blast_single_record_binding_required")
        if row["operand_role"] in seen:
            raise ValueError("native_blast_duplicate_record_binding")
        seen.add(row["operand_role"])
    seen, paths, reports = set(), [], 0
    for row in job["outputs"]:
        role, fmt = row["role"], row["format"]
        if role in seen:
            raise ValueError("native_blast_duplicate_output_role")
        seen.add(role)
        _relative(row["relative_path"])
        paths.append(PurePosixPath(row["relative_path"]))
        if role in {"stdout", "stderr"}:
            if fmt != "text" or row["fields"] is not None or row["delimiter"] is not None:
                raise ValueError("native_blast_text_output_contract")
        else:
            reports += 1
            if fmt == "json15" and role == "primary_report":
                if row["fields"] is not None or row["delimiter"] is not None:
                    raise ValueError("native_blast_json_output_contract")
            elif fmt in {"tabular6", "tabular7"}:
                if not row["fields"] or not set(row["fields"]) <= TABULAR_FIELDS:
                    raise ValueError("native_blast_explicit_tabular_fields_required")
                delimiter = row["delimiter"]
                if delimiter is None or delimiter in {"\0", "\n", "\r", " "} or len(delimiter.encode()) != 1:
                    raise ValueError("native_blast_explicit_single_byte_delimiter_required")
                if "qcovus" in row["fields"] and job["program"] != "blastn":
                    raise ValueError("native_blast_program_tabular_field_conflict:qcovus")
            else:
                raise ValueError("native_blast_report_output_contract")
    if not {"stdout", "stderr"} <= seen or reports != 1:
        raise ValueError("native_blast_exactly_one_report_required")
    for index, first in enumerate(paths):
        for second in paths[index + 1:]:
            if first == second or first in second.parents or second in first.parents:
                raise ValueError("native_blast_output_path_overlap")
    _options(job)
    return job


def compile_native_blast_job(job, *, input_paths=None, output_directory="."):
    job = validate_native_blast_job(job)
    paths = {row["role"]: row["path"] for row in job["operands"]}
    if input_paths is not None:
        if type(input_paths) is not dict or input_paths.keys() != paths.keys():
            raise ValueError("native_blast_complete_staged_path_mapping_required")
        for path in input_paths.values():
            _absolute(path)
        paths = dict(input_paths)
    if output_directory != ".":
        _absolute(output_directory)
    outputs = finite_json_copy(job["outputs"])
    report = next(row for row in outputs if row["role"] not in {"stdout", "stderr"})
    fmt = {"json15": "15", "tabular6": "6", "tabular7": "7"}[report["format"]]
    if report["fields"] is not None:
        fmt += ("" if report["delimiter"] == "\t" else " delim=" + report["delimiter"])
        fmt += " " + " ".join(report["fields"])
    argv = [job["software"]["executable"], *job["options"], "-query", paths["query_sequence"],
        "-subject", paths["subject_sequence"], "-outfmt", fmt,
        "-out", str(PurePosixPath(output_directory) / report["relative_path"])]
    return {"argv": argv, "environment": dict(job["environment"]), "outputs": outputs}


def requested_job_from_native(job):
    job = validate_native_blast_job(job)
    compiled = compile_native_blast_job(job)
    return {"argv": compiled["argv"], "environment": compiled["environment"], "native_blast": job}


def validate_native_blast_requested_job(value):
    request = finite_json_copy(value)
    _schema(request, NATIVE_BLAST_REQUESTED_JOB_SCHEMA)
    if request != requested_job_from_native(request["native_blast"]):
        raise ValueError("native_blast_requested_job_compiler_mismatch")
    return request
