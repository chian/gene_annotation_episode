"""Compile one explicitly selected Infernal preparation command, without I/O.

Mutable calibration and adjacent index files get owned working copies. This
module describes those copies; it executes neither them nor the selected native
program. The existing scientific Infernal v1 contract is deliberately separate.
"""
from __future__ import annotations

from copy import deepcopy
import math
from pathlib import PurePosixPath
import re

from .infernal_preparation_schema import PROGRAM_MODES, require_finite_json
from .native_infernal_contracts import finite_json_copy, native_infernal_digest


JOB_VERSION = "native_infernal_preparation_job_v1"
_MODEL_FORMATS = {"infernal_cm_ascii", "infernal_cm_legacy_ascii", "infernal_cm_binary"}
_ALIGNMENT_FORMATS = {"stockholm", "pfam", "afa", "a2m", "clustal", "phylip"}
_FORMAT_ARG = {"stockholm": "Stockholm", "pfam": "Pfam", "afa": "AFA",
               "a2m": "A2M", "clustal": "Clustal", "phylip": "PHYLIP"}
_MODE_OPTIONS = {
    "cmcalibrate": {"calibrate": [], "forecast": ["--forecast"],
                    "memory_estimate": ["--memreq"], "split_commands": ["--split"],
                    "partition_scores": [], "merge_scores": ["--merge"]},
    "cmconvert": {"ascii": ["-a"], "binary": ["-b"], "legacy_ascii": ["-1"],
                  "maximum_likelihood_hmm": ["--mlhmm"], "filter_hmm": ["--fhmm"]},
    "cmemit": {"sample_unaligned": ["-u"], "sample_aligned": ["-a"], "consensus": ["-c"]},
    "cmfetch": {"single_key": [], "key_file": ["-f"], "index": ["--index"]},
    "cmstat": {"summary": [], "scores_at_evalue": [], "scores_at_pvalue": [],
               "evalues_at_score": [], "evalues_at_ga": ["--cut_ga"],
               "evalues_at_nc": ["--cut_nc"], "evalues_at_tc": ["--cut_tc"]},
}
_FLAGS = {
    "cmbuild": {"-F", "--fast", "--hand", "--fraggiven", "--noss", "--consrf",
                "--wpb", "--wgsc", "--wnone", "--wgiven", "--wblosum", "--eent",
                "--enone", "--p7ml", "-l", "--gibbs", "--cyk", "--notrunc", "--miss"},
    "cmcalibrate": {"--noforecast", "--cbash", "--nonbanded", "--nonull3", "--random"},
    "cmconvert": set(),
    "cmemit": {"-l", "--u5p", "--u3p", "--iid", "--rna", "--dna", "--hmmonly", "--nohmmonly"},
    "cmfetch": set(), "cmpress": {"-F"}, "cmstat": {"--hmmonly", "--nohmmonly"},
}
_NUMBERS = {
    "cmbuild": {"--symfrac": "fraction", "--fragthresh": "nonnegative", "--fragnrfpos": "integer",
                "--wid": "fraction", "--ere": "positive", "--eset": "positive",
                "--eminseq": "positive", "--emaxseq": "positive", "--ehmmre": "positive",
                "--esigma": "positive", "--p7ere": "positive", "--EmN": "positive_integer",
                "--EvN": "positive_integer", "--ElfN": "positive_integer",
                "--EgfN": "positive_integer", "--seed": "integer"},
    "cmcalibrate": {"-L": "calibration_length", "--nforecast": "positive_integer",
                    "--gtailn": "positive_integer", "--ltailn": "positive_integer",
                    "--tailp": "positive_fraction", "--part": "positive_integer",
                    "--ptot": "positive_integer", "--seed": "integer", "--beta": "positive_fraction",
                    "--cpu": "integer"},
    "cmconvert": {},
    "cmemit": {"-N": "positive_integer", "-e": "positive_integer", "--a5p": "integer",
               "--a3p": "integer", "--seed": "integer", "--idx": "integer", "--exp": "positive"},
    "cmfetch": {}, "cmpress": {},
    "cmstat": {"-E": "positive", "-P": "positive_fraction", "-T": "real", "-Z": "positive"},
}
_TEXT_OPTIONS = {"cmbuild": {"-n"}, "cmstat": {"--key"}}
_RESERVED_ENV = {"TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME"}
_COMMON_JOB_FIELDS = {"version", "program", "mode", "software", "environment", "operands",
                      "options", "outputs", "key", "grading_parameters"}


def _error(reason):
    raise ValueError("native_infernal_preparation_" + reason)


def _object(obj, keys, name):
    if type(obj) is not dict or set(obj) != set(keys):
        _error(name + "_fields")


def _text(item, name, *, nullable=False):
    if item is None and nullable:
        return
    if type(item) is not str or not item or any(c in item for c in "\x00\r\n"):
        _error(name + "_invalid")


def _path(item, *, absolute):
    _text(item, "path")
    path = PurePosixPath(item)
    if (path.is_absolute() != absolute or str(path) != item or item.startswith("//")
            or "\\" in item or ".." in item.split("/") or item in {".", "..", "/"}):
        _error("normalized_path_required")
    return path


def _sha(item):
    if type(item) is not str or re.fullmatch(r"[a-f0-9]{64}", item) is None:
        _error("sha256_invalid")


def operand_contract(program, mode):
    if program not in PROGRAM_MODES or mode not in PROGRAM_MODES[program]:
        _error("unsupported_program_mode")
    if program == "cmbuild":
        return {"alignment": _ALIGNMENT_FORMATS}, {"prior": {"text"}, "null": {"text"}, "rsearch": {"text"}}
    required, optional = {"models": _MODEL_FORMATS}, {}
    if program == "cmcalibrate":
        optional["gc"] = {"text"}
        if mode == "merge_scores":
            required["partition_scores"] = {"infernal_partition_scores"}
    if program in {"cmfetch", "cmstat"} and mode != "index":
        optional["ssi"] = {"infernal_ssi"}
    if program == "cmfetch" and mode == "key_file":
        required["keys"] = {"key_file"}
    return required, optional


def output_contract(program, mode):
    if program not in PROGRAM_MODES or mode not in PROGRAM_MODES[program]:
        _error("unsupported_program_mode")
    required = {"stdout": {"infernal_stdout"}, "stderr": {"infernal_stderr"}}
    optional = {}
    if program == "cmbuild":
        required["built_models"] = {"infernal_cm_ascii"}
        optional["processed_alignment"] = {"stockholm"}
        if mode == "refine":
            required["refined_alignment"] = {"stockholm"}
    elif program == "cmcalibrate":
        if mode in {"calibrate", "merge_scores"}:
            required["calibrated_models"] = {"infernal_cm_ascii", "infernal_cm_binary"}
            optional.update({name: {"infernal_calibration_" + name}
                             for name in ("hfile", "sfile", "qqfile", "ffile", "xfile")})
        elif mode == "split_commands":
            required["commands"] = {"infernal_commands"}
        elif mode == "partition_scores":
            required["partition_scores"] = {"infernal_partition_scores"}
    elif program == "cmconvert":
        role = "converted_hmms" if mode in {"maximum_likelihood_hmm", "filter_hmm"} else "converted_models"
        fmt = {"ascii": "infernal_cm_ascii", "binary": "infernal_cm_binary",
               "legacy_ascii": "infernal_cm_legacy_ascii"}.get(mode, "hmmer_hmm_ascii")
        required[role] = {fmt}
    elif program == "cmemit":
        if mode == "sample_aligned":
            required["generated_alignment"] = _ALIGNMENT_FORMATS
        else:
            required["generated_sequences"] = {"fasta"}
        optional["trace"] = {"infernal_trace"}
    elif program == "cmfetch":
        required["ssi" if mode == "index" else "fetched_models"] = {
            "infernal_ssi" if mode == "index" else "infernal_cm_ascii"}
    elif program == "cmpress":
        required.update({"i1m": {"infernal_cm_binary"}, "i1i": {"infernal_ssi"},
                         "i1f": {"infernal_i1f"}, "i1p": {"infernal_i1p"}})
    return required, optional


def native_options(job):
    """Parse selected options; compiler-owned paths/mode selectors are excluded."""
    program, tokens, result, index = job["program"], job["options"], {}, 0
    if type(tokens) is not list:
        _error("options_list_required")
    while index < len(tokens):
        flag = tokens[index]
        _text(flag, "option")
        index += 1
        if flag in result:
            _error("duplicate_option:" + flag)
        if flag in _FLAGS[program]:
            result[flag] = True
            continue
        kind = _NUMBERS[program].get(flag)
        is_text = flag in _TEXT_OPTIONS.get(program, set())
        if kind is None and not is_text:
            _error("unsupported_or_compiler_owned_option:" + flag)
        if index >= len(tokens):
            _error("option_operand_required:" + flag)
        raw = tokens[index]
        _text(raw, "option_operand")
        index += 1
        if is_text:
            result[flag] = raw
            continue
        try:
            number = float(raw)
            valid = math.isfinite(number)
            if kind in {"integer", "positive_integer"}:
                valid &= re.fullmatch(r"[+]?\d+", raw) is not None
                valid &= number >= (1 if kind == "positive_integer" else 0)
            if kind in {"positive", "positive_fraction"}:
                valid &= number > 0
            if kind in {"nonnegative", "fraction"}:
                valid &= number >= 0
            if kind in {"fraction", "positive_fraction"}:
                valid &= number <= 1
            if kind == "calibration_length":
                valid &= .01 <= number <= 160
        except (ValueError, OverflowError):
            valid = False
        if not valid:
            _error("invalid_option_operand:" + flag)
        result[flag] = int(raw) if kind in {"integer", "positive_integer"} else number
    if program == "cmstat":
        required_flag = {"scores_at_evalue": "-E", "scores_at_pvalue": "-P", "evalues_at_score": "-T"}.get(job["mode"])
        chosen = {flag for flag in ("-E", "-P", "-T") if flag in result}
        if chosen != ({required_flag} if required_flag else set()):
            _error("statistic_mode_threshold_conflict")
    if program == "cmcalibrate":
        mode = job["mode"]
        if ("--part" in result) != (mode == "partition_scores"):
            _error("partition_mode_conflict")
        if mode in {"partition_scores", "split_commands", "merge_scores"}:
            if "--ptot" not in result:
                _error("partition_count_required")
            if mode == "partition_scores" and result["--part"] > result["--ptot"]:
                _error("partition_index_outside_population")
        if mode in {"forecast", "memory_estimate"} and ("--cpu" in result or "INFERNAL_NCPU" in job["environment"]):
            _error("forecast_memory_cpu_environment_conflict")
    return result


def validate_native_infernal_preparation_job(value):
    job = finite_json_copy(value)
    _object(job, _COMMON_JOB_FIELDS, "job")
    if job["version"] != JOB_VERSION:
        _error("job_version")
    program, mode = job["program"], job["mode"]
    if type(program) is not str or program not in PROGRAM_MODES or type(mode) is not str or mode not in PROGRAM_MODES[program]:
        _error("unsupported_program_mode")
    software = job["software"]
    _object(software, {"executable", "sha256", "engine_version"}, "software")
    _path(software["executable"], absolute=True)
    _sha(software["sha256"])
    _text(software["engine_version"], "engine_version", nullable=True)
    if type(job["environment"]) is not dict:
        _error("environment_object_required")
    for name, setting in job["environment"].items():
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None or type(setting) is not str or "\x00" in setting or name in _RESERVED_ENV:
            _error("invalid_or_compiler_owned_environment")
    required, optional = operand_contract(program, mode)
    operands = job["operands"]
    if type(operands) is not list:
        _error("operands_list_required")
    grouped = {}
    for operand in operands:
        _object(operand, {"role", "ordinal", "path", "format", "sha256", "size_bytes", "artifact_ref"}, "operand")
        role = operand["role"]
        if type(role) is not str or operand["format"] not in {**required, **optional}.get(role, set()):
            _error("operand_role_format_conflict")
        _path(operand["path"], absolute=True)
        _sha(operand["sha256"])
        _text(operand["artifact_ref"], "artifact_ref", nullable=True)
        if type(operand["size_bytes"]) is not int or operand["size_bytes"] < 0:
            _error("operand_size_invalid")
        values = grouped.setdefault(role, [])
        if type(operand["ordinal"]) is not int or operand["ordinal"] != len(values):
            _error("operand_ordinals_must_preserve_role_order")
        values.append(operand)
    if required.keys() - grouped.keys() or any(len(rows) != 1 for role, rows in grouped.items() if role != "partition_scores"):
        _error("missing_or_repeated_operand")
    if "ssi" in grouped and grouped["ssi"][0]["path"] != grouped["models"][0]["path"] + ".ssi":
        _error("selected_index_model_stem_conflict")
    _text(job["key"], "key", nullable=True)
    if (job["key"] is not None) != (program == "cmfetch" and mode == "single_key"):
        _error("positional_key_mode_conflict")
    required, optional = output_contract(program, mode)
    if type(job["outputs"]) is not list:
        _error("outputs_list_required")
    outputs, paths = {}, []
    for output in job["outputs"]:
        _object(output, {"role", "format", "relative_path"}, "output")
        role = output["role"]
        if type(role) is not str or role in outputs or output["format"] not in {**required, **optional}.get(role, set()):
            _error("output_role_format_conflict")
        path = _path(output["relative_path"], absolute=False)
        if path.parts[0] in {"inputs", "tmp", "cache", "bundle.json", "request.json"} or path.parts[0].startswith("."):
            _error("reserved_output_path")
        if any(path == old or path in old.parents or old in path.parents for old in paths):
            _error("output_paths_overlap")
        paths.append(path)
        outputs[role] = output
    if required.keys() - outputs.keys():
        _error("required_output_missing")
    if program == "cmpress":
        stem = outputs["i1m"]["relative_path"]
        if not stem.endswith(".i1m"):
            _error("pressed_output_suffix")
        stem = stem[:-4]
        if any(outputs[role]["relative_path"] != stem + "." + role for role in ("i1m", "i1i", "i1f", "i1p")):
            _error("pressed_output_stems_differ")
    if program == "cmfetch" and mode == "index" and not outputs["ssi"]["relative_path"].endswith(".ssi"):
        _error("index_output_suffix")
    if program == "cmcalibrate" and mode in {"calibrate", "merge_scores"}:
        expected = "infernal_cm_binary" if grouped["models"][0]["format"] == "infernal_cm_binary" else "infernal_cm_ascii"
        if outputs["calibrated_models"]["format"] != expected:
            _error("calibration_output_format_does_not_match_native_writer")
    if type(job["grading_parameters"]) is not dict:
        _error("grading_parameters_object_required")
    allowed_parameters = ({"artifact_bindings"} if program in {"cmconvert", "cmfetch", "cmpress"}
        else set() if program == "cmemit" else {"search_space_mb", "evalue", "pvalue", "score_bits",
            "rounding_absolute_tolerance", "requested_megabases", "partition_index", "partition_count",
            "partition_requests"})
    if set(job["grading_parameters"]) - allowed_parameters:
        _error("unknown_grading_parameter")
    settings = native_options(job)
    if program == "cmcalibrate" and mode == "merge_scores" and len(grouped["partition_scores"]) != settings["--ptot"]:
        _error("merge_partition_artifacts_incomplete")
    return job


def compile_native_infernal_preparation_job(job, *, input_paths=None, output_directory="."):
    """Produce one argv plus explicit mechanical working-copy requirements."""
    job = validate_native_infernal_preparation_job(job)
    paths = {}
    for operand in job["operands"]:
        paths.setdefault(operand["role"], []).append(operand["path"])
    if input_paths is not None:
        if type(input_paths) is not dict or set(input_paths) != set(paths):
            _error("complete_staged_paths_required")
        for role, values in input_paths.items():
            if type(values) is not list or len(values) != len(paths[role]):
                _error("staged_operand_population_changed")
            for path in values:
                _path(path, absolute=True)
        paths = deepcopy(input_paths)
    if "ssi" in paths and paths["ssi"][0] != paths["models"][0] + ".ssi":
        _error("staged_index_model_stem_conflict")
    if output_directory != ".":
        _path(output_directory, absolute=True)
    out = {row["role"]: str(PurePosixPath(output_directory) / row["relative_path"]) for row in job["outputs"]}
    program, mode = job["program"], job["mode"]
    argv = [job["software"]["executable"], *job["options"], *_MODE_OPTIONS.get(program, {}).get(mode, [])]
    settings = native_options(job)
    for flag in _MODE_OPTIONS.get(program, {}).get(mode, []):
        settings[flag] = True
    copies = []

    def copy(role, ordinal, destination, *, mutable=False):
        if destination in [p for values in paths.values() for p in values]:
            _error("working_copy_overwrites_original_operand")
        copies.append({"operand_role": role, "operand_ordinal": ordinal,
                       "destination": destination, "mutable": mutable})
        return destination

    if program == "cmbuild":
        alignment_format = next(row["format"] for row in job["operands"] if row["role"] == "alignment")
        argv += ["--informat", _FORMAT_ARG[alignment_format]]
        for role, flag in (("prior", "--prior"), ("null", "--null"), ("rsearch", "--rsearch")):
            if role in paths:
                argv += [flag, paths[role][0]]
        for role, flag in (("processed_alignment", "-O"), ("refined_alignment", "--refine")):
            if role in out:
                argv += [flag, out[role]]
        argv += [out["built_models"], paths["alignment"][0]]
    elif program == "cmcalibrate":
        settings.setdefault("-L", 1.6)
        model = paths["models"][0]
        if mode in {"calibrate", "merge_scores"}:
            model = copy("models", 0, out["calibrated_models"], mutable=True)
        if "gc" in paths:
            argv += ["--gc", paths["gc"][0]]
        for role, flag in (("hfile", "--hfile"), ("sfile", "--sfile"), ("qqfile", "--qqfile"),
                           ("ffile", "--ffile"), ("xfile", "--xfile"), ("commands", "--cfile"),
                           ("partition_scores", "--pfile")):
            if role in out:
                argv += [flag, out[role]]
        if mode in {"split_commands", "merge_scores"}:
            prefix = str(PurePosixPath(output_directory) / "work" / "partition")
            argv += ["--proot", prefix]
            if mode == "merge_scores":
                for index in range(len(paths["partition_scores"])):
                    copy("partition_scores", index, prefix + "." + str(index + 1))
        argv += [model]
    elif program == "cmconvert":
        role = "converted_hmms" if "converted_hmms" in out else "converted_models"
        argv += ["-o", out[role], paths["models"][0]]
    elif program == "cmemit":
        settings = {"-N": 10, "--idx": 1, "--seed": 0, **settings}
        role = "generated_alignment" if mode == "sample_aligned" else "generated_sequences"
        if mode == "sample_aligned":
            fmt = next(row["format"] for row in job["outputs"] if row["role"] == role)
            argv += ["--outformat", _FORMAT_ARG[fmt]]
            settings["--outformat"] = _FORMAT_ARG[fmt]
        if "trace" in out:
            argv += ["--tfile", out["trace"]]
        argv += ["-o", out[role], paths["models"][0]]
    elif program == "cmfetch":
        model = paths["models"][0]
        if mode == "index":
            model = copy("models", 0, out["ssi"][:-4])
            argv += [model]
        else:
            argv += ["-o", out["fetched_models"], model]
            if mode == "single_key":
                argv += [job["key"]]
                settings["key"] = job["key"]
            else:
                argv += [paths["keys"][0]]
    elif program == "cmpress":
        model = copy("models", 0, out["i1m"][:-4])
        argv += [model]
    else:
        settings.setdefault("-Z", 10.0)
        argv += [paths["models"][0]]
    for index, item in enumerate(copies):
        destination = PurePosixPath(item["destination"])
        for role, path in out.items():
            target = PurePosixPath(path)
            intentional = item["mutable"] and role == "calibrated_models" and destination == target
            if not intentional and (destination == target or destination in target.parents or target in destination.parents):
                _error("working_copy_output_path_overlap")
        for earlier in copies[:index]:
            target = PurePosixPath(earlier["destination"])
            if destination == target or destination in target.parents or target in destination.parents:
                _error("working_copy_paths_overlap")
        if item["mutable"] and item["destination"] + ".xxx" in out.values():
            _error("native_calibration_temporary_output_overlap")
    return {"argv": argv, "environment": deepcopy(job["environment"]),
            "outputs": deepcopy(job["outputs"]), "working_copies": copies,
            "operation": {"program": program, "mode": mode,
                          "engine_version": job["software"]["engine_version"], "settings": settings}}


def requested_job_from_infernal_preparation(job):
    job = validate_native_infernal_preparation_job(job)
    compiled = compile_native_infernal_preparation_job(job)
    return {"argv": compiled["argv"], "environment": compiled["environment"],
            "native_infernal_preparation": job}


def validate_native_infernal_preparation_requested_job(value):
    request = finite_json_copy(value)
    _object(request, {"argv", "environment", "native_infernal_preparation"}, "requested_job")
    if request != requested_job_from_infernal_preparation(request["native_infernal_preparation"]):
        _error("requested_job_compiler_mismatch")
    return request


__all__ = ["JOB_VERSION", "operand_contract", "output_contract", "native_options",
           "validate_native_infernal_preparation_job", "compile_native_infernal_preparation_job",
           "requested_job_from_infernal_preparation", "validate_native_infernal_preparation_requested_job"]
