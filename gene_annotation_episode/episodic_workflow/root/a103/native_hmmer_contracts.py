"""Pure selected-job contracts for the six B004 native HMMER operations.

No function in this module resolves a path, opens an input, or starts work.
Formats are deliberately closed: FASTA, Stockholm, HMMER3 ASCII profiles and
the four explicitly supplied hmmpress companions. Optional checkpoint paths
are native prefixes; a producer manifest records their actual produced files.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import PurePosixPath
import re

from jsonschema import Draft202012Validator


PROGRAMS = ("hmmscan", "hmmsearch", "jackhmmer", "nhmmer", "nhmmscan", "hmmalign")
PRESSED_SUFFIXES = ("h3f", "h3i", "h3m", "h3p")
CHECKPOINT_ROLES = {"checkpoint_hmm": ".hmm", "checkpoint_msa": ".sto"}
RESERVED_ENVIRONMENT = frozenset({"TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME"})
_STR = {"type": "string", "minLength": 1, "pattern": "^[^\\u0000]+$"}
_NULL_STR = {"anyOf": [_STR, {"type": "null"}]}
_SHA = {"type": "string", "pattern": "^[0-9a-fA-F]{64}$"}
_ABS = {"type": "string", "pattern": "^/[^\\u0000\\n\\r]+$"}


def _object(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def _array(items):
    return {"type": "array", "items": items}


def operand_contract(program, mode):
    """Return required and optional role-to-format choices, without I/O."""
    if program in {"hmmscan", "nhmmscan"}:
        return ({"profile_database": {"hmmer3_ascii"}, "query_sequence": {"fasta"},
                 **{"profile_database_" + suffix: {"hmmer_" + suffix}
                    for suffix in PRESSED_SUFFIXES}}, {})
    if program == "hmmsearch":
        return ({"query_profile": {"hmmer3_ascii"}, "sequence_database": {"fasta"}}, {})
    if program == "jackhmmer":
        return ({"query_sequence": {"fasta"}, "sequence_database": {"fasta"}}, {})
    if program == "nhmmer":
        query = {"sequence": ("query_sequence", {"fasta", "stockholm"}),
                 "profile": ("query_profile", {"hmmer3_ascii"}),
                 "alignment": ("query_alignment", {"stockholm"})}[mode]
        return ({query[0]: query[1], "sequence_database": {"fasta"}}, {})
    return ({"profile": {"hmmer3_ascii"}, "sequences": {"fasta"}}, {"mapali": {"stockholm"}})


def output_contract(program, mode):
    """Required and optional output roles; checkpoint roles denote prefixes."""
    if program == "hmmalign":
        return ({"stockholm": "stockholm", "stderr": "text"}, {})
    required = {"stdout": "hmmer_stdout", "stderr": "text",
                "tblout": "nhmmer_tblout" if program.startswith("nhmm") else "protein_tblout"}
    if program in {"hmmscan", "hmmsearch", "jackhmmer"}:
        required["domtblout"] = "protein_domtblout"
    optional = {}
    if program in {"hmmsearch", "jackhmmer", "nhmmer"}:
        optional["included_msa"] = "stockholm"
    if program == "jackhmmer":
        optional.update(checkpoint_hmm="hmmer3_ascii", checkpoint_msa="stockholm")
    if program == "nhmmer" and mode == "alignment":
        optional["constructed_hmm"] = "hmmer3_ascii"
    return required, optional


_INPUT_ROLES = sorted({"profile_database", "query_sequence", "query_profile", "query_alignment",
                       "sequence_database", "profile", "sequences", "mapali"}
                      | {"profile_database_" + suffix for suffix in PRESSED_SUFFIXES})
_OUTPUT_ROLES = ["stdout", "stderr", "tblout", "domtblout", "stockholm", "included_msa",
                 "checkpoint_hmm", "checkpoint_msa", "constructed_hmm"]
NATIVE_HMMER_JOB_SCHEMA = _object({
    "version": {"const": "native_hmmer_job_v1"}, "program": {"enum": list(PROGRAMS)},
    "mode": {"enum": ["search", "sequence", "profile", "alignment", "align"]},
    "software": _object({"executable": _ABS, "sha256": _SHA, "engine_version": _NULL_STR}),
    "environment": {"type": "object", "additionalProperties": {"type": "string"}},
    "operands": _array(_object({"role": {"enum": _INPUT_ROLES}, "path": _ABS,
        "format": {"enum": ["fasta", "stockholm", "hmmer3_ascii"] +
                               ["hmmer_" + suffix for suffix in PRESSED_SUFFIXES]},
        "sha256": _SHA, "size_bytes": {"type": "integer", "minimum": 0}, "artifact_ref": _NULL_STR})),
    "operand_bindings": _array(_object({"operand_role": {"enum": _INPUT_ROLES},
        "record_ordinal": {"type": "integer", "minimum": 0}, "native_name": _NULL_STR,
        "native_accession": _NULL_STR, "subject_ref": _NULL_STR, "reference_ref": _NULL_STR})),
    "options": _array(_STR), "outputs": _array(_object({"role": {"enum": _OUTPUT_ROLES},
        "format": {"enum": ["hmmer_stdout", "text", "protein_tblout", "protein_domtblout",
                              "nhmmer_tblout", "stockholm", "hmmer3_ascii"]}, "relative_path": _STR})),
    "metadata": {"type": "object"}, "grading_parameters": {"type": "object", "maxProperties": 0},
})
NATIVE_HMMER_JOB_SCHEMA["allOf"] = [
    {"if": {"properties": {"program": {"const": p}}},
     "then": {"properties": {"mode": {"enum": (
         ["sequence", "profile", "alignment"] if p == "nhmmer" else
         ["align"] if p == "hmmalign" else ["search"])}}}} for p in PROGRAMS]
NATIVE_HMMER_REQUESTED_JOB_SCHEMA = _object({
    "argv": {"type": "array", "minItems": 1, "items": _STR},
    "environment": {"type": "object", "additionalProperties": {"type": "string"}},
    "native_hmmer": NATIVE_HMMER_JOB_SCHEMA,
})


def finite_json_copy(value):
    """Reject coercions (tuples, nonstring keys, NaN) as well as non-JSON types."""
    def check(item):
        if type(item) in {str, int, bool} or item is None:
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict and all(type(k) is str for k in item):
            for child in item.values():
                check(child)
            return
        raise ValueError("native_hmmer_finite_json_required")
    check(value)
    return json.loads(json.dumps(value, allow_nan=False, ensure_ascii=False))


def native_hmmer_digest(value):
    return hashlib.sha256(json.dumps(finite_json_copy(value), sort_keys=True,
        separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _schema(value, schema):
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    if error is not None:
        path = ".".join(map(str, error.absolute_path))
        raise ValueError("native_hmmer_schema:" + path + ":" + error.validator)


def _absolute(path):
    if (type(path) is not str or not path.startswith("/") or path.startswith("//")
            or any(c in path for c in ("\0", "\n", "\r"))
            or ".." in path.split("/") or str(PurePosixPath(path)) != path):
        raise ValueError("native_hmmer_absolute_normalized_path_required")


def _relative(path):
    if (not path or PurePosixPath(path).is_absolute() or path in {".", ".."}
            or ".." in path.split("/") or str(PurePosixPath(path)) != path
            or any(c in path for c in ("\0", "\n", "\r", "\\"))):
        raise ValueError("native_hmmer_confined_relative_output_required")
    if path.split("/")[0] in {"inputs", "tmp", "cache", "bundle.json", ".native-hmmer-owner.json",
                             ".bundle.json.writing", "..native-hmmer-owner.json.writing"}:
        raise ValueError("native_hmmer_reserved_output_path")


_COMMON_FLAGS = {"--acc", "--noali", "--notextw", "--max", "--nobias", "--nonull2"}
_COMMON_VALUES = {"--textw": "integer", "-E": "positive", "-T": "real", "--incE": "positive",
                  "--incT": "real", "--F1": "real", "--F2": "real", "--F3": "real",
                  "-Z": "positive", "--seed": "nonnegative_integer", "--cpu": "nonnegative_integer"}
_DOMAIN_VALUES = {"--domE": "positive", "--domT": "real", "--incdomE": "positive",
                  "--incdomT": "real", "--domZ": "positive"}
_CUTOFFS = {"--cut_ga", "--cut_nc", "--cut_tc"}
_COMPILER_FLAGS = {"-o", "-A", "--tblout", "--domtblout", "--mapali", "--chkhmm", "--chkali",
                   "--hmmout", "--qformat", "--tformat", "--informat", "--outformat"}
_UNSUPPORTED_PATH_FLAGS = {"--mxfile", "--bgfile", "--ssifile", "--pfamtblout", "--dfamtblout", "--aliscoresout"}


def _options(job):
    program, mode = job["program"], job["mode"]
    flags, values = set(_COMMON_FLAGS), dict(_COMMON_VALUES)
    if program == "hmmalign":
        flags, values = {"--trim", "--amino", "--dna", "--rna"}, {}
    elif program in {"hmmscan", "hmmsearch", "jackhmmer"}:
        values.update(_DOMAIN_VALUES)
        if program != "jackhmmer":
            flags |= _CUTOFFS
        else:
            flags |= {"--wpb", "--wgsc", "--wblosum", "--wnone", "--eent", "--eentexp", "--eclust",
                      "--enone", "--pnone", "--plaplace"}
            values.update({"-N": "positive_integer", "--mx": "string", "--popen": "gap_open",
                           "--pextend": "gap_extend", "--fragthresh": "fraction", "--wid": "fraction",
                           "--eset": "positive", "--ere": "positive", "--esigma": "positive", "--eid": "fraction",
                           **{flag: "positive_integer" for flag in ("--EmL", "--EmN", "--EvL", "--EvN", "--EfL", "--EfN")},
                           "--Eft": "open_fraction"})
    else:
        flags |= _CUTOFFS | {"--watson", "--crick"}
        values.update({"--w_beta": "real", "--w_length": "integer", "--B1": "integer", "--B2": "integer", "--B3": "integer"})
        if program == "nhmmer":
            flags |= {"--dna", "--rna", "--singlemx", "--qsingle_seqs"}
            values.update({"--popen": "gap_open", "--pextend": "gap_extend", "--block_length": "integer"})
    selected, tokens, i = {}, job["options"], 0
    while i < len(tokens):
        flag = tokens[i]
        if flag in _COMPILER_FLAGS:
            raise ValueError("native_hmmer_compiler_owned_option:" + flag)
        if flag in _UNSUPPORTED_PATH_FLAGS:
            raise ValueError("native_hmmer_unsupported_path_option:" + flag)
        if flag not in flags | values.keys():
            raise ValueError("native_hmmer_unsupported_option:" + flag)
        if flag in selected:
            raise ValueError("native_hmmer_duplicate_option:" + flag)
        selected[flag] = None
        i += 1
        if flag in flags:
            continue
        if i == len(tokens):
            raise ValueError("native_hmmer_option_operand_required:" + flag)
        raw, kind = tokens[i], values[flag]
        selected[flag] = raw
        i += 1
        if kind == "string":
            if raw.startswith("-") or "/" in raw:
                raise ValueError("native_hmmer_invalid_option_operand:" + flag)
            continue
        try:
            numeric = float(raw)
            valid = math.isfinite(numeric)
            if "integer" in kind:
                valid &= bool(re.fullmatch(r"[+-]?\d+", raw))
            if kind.startswith("positive"):
                valid &= numeric > 0
            if kind == "nonnegative_integer":
                valid &= numeric >= 0
            if kind == "fraction":
                valid &= 0 <= numeric <= 1
            if kind == "open_fraction":
                valid &= 0 < numeric < 1
            if kind == "gap_open":
                valid &= 0 <= numeric < .5
            if kind == "gap_extend":
                valid &= 0 <= numeric < 1
            if flag == "--textw":
                valid &= numeric >= 120
            if flag == "--block_length":
                valid &= numeric >= 50000
        except (ValueError, OverflowError):
            valid = False
        if not valid:
            raise ValueError("native_hmmer_invalid_option_operand:" + flag)
    groups = [set(pair) for pair in (("-E", "-T"), ("--domE", "--domT"), ("--incE", "--incT"),
              ("--incdomE", "--incdomT"), ("--watson", "--crick"), ("--notextw", "--textw"))]
    groups += [_CUTOFFS, {"--amino", "--dna", "--rna"}, {"--wpb", "--wgsc", "--wblosum", "--wnone"},
               {"--eent", "--eentexp", "--eclust", "--enone", "--eset"}, {"--pnone", "--plaplace"}]
    for group in groups:
        if len(group & selected.keys()) > 1:
            raise ValueError("native_hmmer_conflicting_options:" + ",".join(sorted(group & selected.keys())))
    if _CUTOFFS & selected.keys() and {"-E", "-T", "--domE", "--domT", "--incE", "--incT", "--incdomE", "--incdomT"} & selected.keys():
        raise ValueError("native_hmmer_conflicting_threshold_options")
    if "--max" in selected and {"--F1", "--F2", "--F3", "--nobias", "--B1", "--B2", "--B3"} & selected.keys():
        raise ValueError("native_hmmer_conflicting_filter_options")
    if "--nobias" in selected and {"--B1", "--B2", "--B3"} & selected.keys():
        raise ValueError("native_hmmer_conflicting_bias_options")
    for flag, required in (("--wid", "--wblosum"), ("--eid", "--eclust")):
        if flag in selected and required not in selected:
            raise ValueError("native_hmmer_required_option:" + flag + ":" + required)
    if program == "nhmmer":
        if "--qsingle_seqs" in selected and mode != "sequence":
            raise ValueError("native_hmmer_mode_option_conflict:--qsingle_seqs")
        if "--singlemx" in selected and mode != "alignment":
            raise ValueError("native_hmmer_mode_option_conflict:--singlemx")
    return selected


def validate_native_hmmer_job(value) -> dict:
    job = finite_json_copy(value)
    _schema(job, NATIVE_HMMER_JOB_SCHEMA)
    _absolute(job["software"]["executable"])
    for key, item in job["environment"].items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or "\0" in item:
            raise ValueError("native_hmmer_invalid_environment")
        if key in RESERVED_ENVIRONMENT:
            raise ValueError("native_hmmer_compiler_owned_environment:" + key)
    required, optional = operand_contract(job["program"], job["mode"])
    roles = {}
    for operand in job["operands"]:
        role = operand["role"]
        if role in roles:
            raise ValueError("native_hmmer_duplicate_operand_role:" + role)
        if operand["format"] not in {**required, **optional}.get(role, set()):
            raise ValueError("native_hmmer_operand_role_format:" + role)
        _absolute(operand["path"])
        roles[role] = operand
    if required.keys() - roles.keys():
        raise ValueError("native_hmmer_missing_operand_roles:" + ",".join(sorted(required.keys() - roles.keys())))
    if "profile_database" in roles:
        for suffix in PRESSED_SUFFIXES:
            if roles["profile_database_" + suffix]["path"] != roles["profile_database"]["path"] + "." + suffix:
                raise ValueError("native_hmmer_pressed_index_path_association:" + suffix)
    bindings = set()
    for binding in job["operand_bindings"]:
        role = binding["operand_role"]
        key = role, binding["record_ordinal"]
        if role not in roles or role.startswith("profile_database_h3"):
            raise ValueError("native_hmmer_binding_operand_role")
        if key in bindings:
            raise ValueError("native_hmmer_duplicate_record_binding")
        bindings.add(key)
    required_outputs, optional_outputs = output_contract(job["program"], job["mode"])
    outputs, paths = {}, []
    for row in job["outputs"]:
        role = row["role"]
        if role in outputs:
            raise ValueError("native_hmmer_duplicate_output_role:" + role)
        if row["format"] != {**required_outputs, **optional_outputs}.get(role):
            raise ValueError("native_hmmer_unsupported_output_role_format:" + role)
        _relative(row["relative_path"])
        paths.append(PurePosixPath(row["relative_path"]))
        outputs[role] = row
    if required_outputs.keys() - outputs.keys():
        raise ValueError("native_hmmer_missing_output_roles:" + ",".join(sorted(required_outputs.keys() - outputs.keys())))
    for i, first in enumerate(paths):
        for second in paths[i+1:]:
            if first == second or first in second.parents or second in first.parents:
                raise ValueError("native_hmmer_output_path_overlap")
    for role in CHECKPOINT_ROLES.keys() & outputs.keys():
        prefix = outputs[role]["relative_path"]
        for other in outputs.values():
            if other["role"] != role and (other["relative_path"].startswith(prefix + "-")
                    or prefix.startswith(other["relative_path"] + "-")):
                raise ValueError("native_hmmer_checkpoint_path_overlap")
    _options(job)
    return job


def compile_native_hmmer_job(job, *, input_paths=None, output_directory=".") -> dict:
    job = validate_native_hmmer_job(job)
    paths = {row["role"]: row["path"] for row in job["operands"]}
    if input_paths is not None:
        if type(input_paths) is not dict or input_paths.keys() != paths.keys():
            raise ValueError("native_hmmer_complete_staged_path_mapping_required")
        for path in input_paths.values():
            _absolute(path)
        paths = dict(input_paths)
    if output_directory != ".":
        _absolute(output_directory)
    if "profile_database" in paths:
        for suffix in PRESSED_SUFFIXES:
            if paths["profile_database_" + suffix] != paths["profile_database"] + "." + suffix:
                raise ValueError("native_hmmer_staged_pressed_index_association:" + suffix)
    outputs = finite_json_copy(job["outputs"])
    out = {row["role"]: str(PurePosixPath(output_directory) / row["relative_path"]) for row in outputs}
    argv = [job["software"]["executable"], *job["options"]]
    for role, flag in (("tblout", "--tblout"), ("domtblout", "--domtblout"), ("included_msa", "-A"),
                       ("checkpoint_hmm", "--chkhmm"), ("checkpoint_msa", "--chkali"), ("constructed_hmm", "--hmmout")):
        if role in out:
            argv += [flag, out[role]]
    program = job["program"]
    if program in {"hmmscan", "nhmmscan"}:
        argv += ["--qformat", "fasta", paths["profile_database"], paths["query_sequence"]]
    elif program == "hmmsearch":
        argv += ["--tformat", "fasta", paths["query_profile"], paths["sequence_database"]]
    elif program == "jackhmmer":
        argv += ["--qformat", "fasta", "--tformat", "fasta", paths["query_sequence"], paths["sequence_database"]]
    elif program == "nhmmer":
        query_role = {"sequence": "query_sequence", "profile": "query_profile", "alignment": "query_alignment"}[job["mode"]]
        if job["mode"] != "profile":
            fmt = next(row["format"] for row in job["operands"] if row["role"] == query_role)
            argv += ["--qformat", fmt]
        if job["mode"] == "sequence" and "--qsingle_seqs" not in job["options"]:
            argv += ["--qsingle_seqs"]
        argv += ["--tformat", "fasta", paths[query_role], paths["sequence_database"]]
    else:
        if "mapali" in paths:
            argv += ["--mapali", paths["mapali"]]
        argv += ["--informat", "fasta", "--outformat", "Stockholm", paths["profile"], paths["sequences"]]
    return {"argv": argv, "environment": dict(job["environment"]), "outputs": outputs}


def requested_job_from_native(job) -> dict:
    job = validate_native_hmmer_job(job)
    compiled = compile_native_hmmer_job(job)
    return {"argv": compiled["argv"], "environment": compiled["environment"], "native_hmmer": job}


def validate_native_hmmer_requested_job(value) -> dict:
    request = finite_json_copy(value)
    _schema(request, NATIVE_HMMER_REQUESTED_JOB_SCHEMA)
    if request != requested_job_from_native(request["native_hmmer"]):
        raise ValueError("native_hmmer_requested_job_compiler_mismatch")
    return request
