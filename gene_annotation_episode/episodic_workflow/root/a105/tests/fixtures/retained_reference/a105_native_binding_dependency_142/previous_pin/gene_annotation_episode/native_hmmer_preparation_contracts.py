"""Pure, exact requests for one selected HMMER 3.4 preparation command.

Paths and native mode selectors are compiled from typed operands. Alimask's
range selector is the documented exception: its value is selected data and is
retained verbatim in options. No file is read and no work is selected here.
"""
from __future__ import annotations

from copy import deepcopy
import math
from pathlib import PurePosixPath
import re

from .native_infernal_contracts import finite_json_copy, native_infernal_digest


JOB_VERSION = "native_hmmer_preparation_job_v1"
PROGRAM_MODES = {
    "alimask": ("mask_alignment", "mask_model", "model_to_alignment", "alignment_to_model"),
    "hmmbuild": ("build_alignment", "build_single_sequence_matrix"),
    "hmmconvert": ("ascii", "binary", "legacy_hmmer2"),
    "hmmemit": ("sample_core_unaligned", "sample_core_aligned", "consensus_simple", "consensus_thresholded", "sample_profile"),
    "hmmfetch": ("single_key", "key_file", "index"), "hmmpress": ("index",),
    "hmmsim": ("viterbi", "msv", "forward", "hybrid"), "hmmstat": ("summary",),
    "makehmmerdb": ("build",), "hmmerfm-exactmatch": ("locations", "count_only"),
}
MODEL_FORMATS = frozenset({"hmmer3_ascii", "hmmer2_ascii", "hmmer_binary"})
ALIGNMENT_FORMATS = frozenset({"stockholm", "pfam", "a2m", "psiblast", "selex", "afa", "clustal", "clustallike", "phylip", "phylips"})
SEQUENCE_FORMATS = ALIGNMENT_FORMATS | {"fasta", "embl", "genbank", "ddbj", "uniprot", "ncbi", "daemon", "hmmpgmd"}
FORMAT_ARGUMENTS = {name: name for name in SEQUENCE_FORMATS}
FORMAT_ARGUMENTS.update(stockholm="Stockholm", pfam="Pfam", afa="AFA", a2m="A2M", clustal="Clustal", phylip="PHYLIP")
RESERVED_ENVIRONMENT = frozenset({"TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME"})
RANGE_FLAGS = {"mask_alignment": "--alirange", "mask_model": "--modelrange", "model_to_alignment": "--model2ali", "alignment_to_model": "--ali2model"}
PRESS_SUFFIXES = {"binary_models": ".h3m", "ssi_index": ".h3i", "msv_profiles": ".h3f", "remaining_profiles": ".h3p"}
_MODES = {
    "hmmbuild": {"build_alignment": [], "build_single_sequence_matrix": ["--singlemx"]},
    "hmmconvert": {"ascii": ["-a"], "binary": ["-b"], "legacy_hmmer2": ["-2"]},
    "hmmemit": {"sample_core_unaligned": [], "sample_core_aligned": ["-a"], "consensus_simple": ["-c"], "consensus_thresholded": ["-C"], "sample_profile": ["-p"]},
    "hmmfetch": {"single_key": [], "key_file": ["-f"], "index": ["--index"]},
    "hmmsim": {"viterbi": ["--vit"], "msv": ["--msv"], "forward": ["--fwd"], "hybrid": ["--hyb"]},
    "hmmerfm-exactmatch": {"locations": [], "count_only": ["--count_only"]},
}
_ALPHABET = {"--amino", "--dna", "--rna"}
_WEIGHTS = {"--wpb", "--wgsc", "--wblosum", "--wnone", "--wgiven"}
_BUILD_FLAGS = _ALPHABET | _WEIGHTS | {"--fast", "--hand"}
_BUILD_NUMBERS = {"--symfrac": "fraction", "--fragthresh": "fraction", "--wid": "fraction", "--seed": "uint"}
_CALIBRATION = {key: "positive_int" for key in ("--EmL", "--EmN", "--EvL", "--EvN", "--EfL", "--EfN")}
_CALIBRATION["--Eft"] = "open_fraction"
_FLAGS = {
    "alimask": _BUILD_FLAGS | {"--appendmask"},
    "hmmbuild": _BUILD_FLAGS | {"--eent", "--eentexp", "--eclust", "--enone", "--pnone", "--plaplace"},
    "hmmconvert": set(), "hmmemit": {"--local", "--unilocal", "--glocal", "--uniglocal"},
    "hmmfetch": set(), "hmmpress": {"-f"},
    "hmmsim": {"-a", "-v", "--fs", "--sw", "--ls", "--s", "--fast", "--tlinear", "--bgflat", "--bgcomp", "--x-no-lengthmodel"},
    "hmmstat": set(), "makehmmerdb": _ALPHABET | {"--fwd_only"}, "hmmerfm-exactmatch": {"--fwd_only"},
}
_NUMBERS = {
    "alimask": _BUILD_NUMBERS,
    "hmmbuild": {**_BUILD_NUMBERS, **_CALIBRATION, "--eset": "positive", "--ere": "positive", "--esigma": "positive", "--eid": "fraction", "--popen": "half_open", "--pextend": "unit_open", "--cpu": "uint", "--w_beta": "open_fraction", "--w_length": "positive_int", "--maxinsertlen": "min_five"},
    "hmmconvert": {}, "hmmemit": {"-N": "positive_int", "-L": "positive_int", "--seed": "uint", "--minl": "fraction", "--minu": "fraction"},
    "hmmfetch": {}, "hmmpress": {},
    "hmmsim": {**_CALIBRATION, "-N": "min_ten", "-L": "positive_int", "--seed": "uint", "--tmin": "open_fraction", "--tmax": "open_fraction", "--tpoints": "positive_int", "--nu": "positive", "--pthresh": "fraction"},
    "hmmstat": {}, "makehmmerdb": {"--bin_length": "bin", "--sa_freq": "power_two", "--block_size": "block"}, "hmmerfm-exactmatch": {},
}
_TEXT_OPTIONS = {"alimask": set(RANGE_FLAGS.values()), "hmmbuild": {"-n", "--mx"}, "hmmconvert": {"--outfmt"}}
_DEFAULT_CALIBRATION = {"--EmL": 200, "--EmN": 200, "--EvL": 200, "--EvN": 200, "--EfL": 100, "--EfN": 200, "--Eft": .04}
_JOB_FIELDS = {"version", "program", "mode", "software", "environment", "operands", "options", "outputs", "key", "input_metadata", "grading_parameters"}
FM_PRODUCER_FIELDS = {"format", "engine_version", "byte_order", "uint8_bytes", "uint16_bytes", "uint32_bytes", "uint64_bytes", "int32_bytes"}


def _error(reason):
    raise ValueError("native_hmmer_preparation_" + reason)


def _object(value, keys, name):
    if type(value) is not dict or set(value) != set(keys):
        _error(name + "_fields")


def _text(value, name, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or not value or any(c in value for c in "\x00\r\n"):
        _error(name + "_invalid")


def _path(value, *, absolute):
    _text(value, "path")
    path = PurePosixPath(value)
    if (path.is_absolute() != absolute or str(path) != value or value.startswith("//") or "\\" in value
            or ".." in value.split("/") or value in {".", "..", "/"}):
        _error("normalized_path_required")
    return path


def _sha(value):
    if type(value) is not str or re.fullmatch(r"[a-f0-9]{64}", value) is None:
        _error("sha256_invalid")


def _mode(program, mode):
    if type(program) is not str or program not in PROGRAM_MODES or type(mode) is not str or mode not in PROGRAM_MODES[program]:
        _error("unsupported_program_mode")


def operand_contract(program, mode):
    _mode(program, mode)
    if program in {"alimask", "hmmbuild"}:
        return {"alignment": ALIGNMENT_FORMATS}, ({"matrix": {"substitution_matrix"}} if program == "hmmbuild" else {})
    if program == "makehmmerdb":
        return {"sequences": SEQUENCE_FORMATS}, {}
    if program == "hmmerfm-exactmatch":
        return {"queries": {"literal_query_lines"}, "fm_database": {"hmmer_fm_3_4"}, "source_sequences": {"fasta"}}, {}
    required, optional = {"models": MODEL_FORMATS}, {}
    if program == "hmmfetch":
        if mode == "key_file":
            required["keys"] = {"key_file"}
        if mode != "index":
            optional["ssi"] = {"hmmer_ssi"}
    return required, optional


def output_contract(program, mode):
    _mode(program, mode)
    required, optional = {"stdout": {"hmmer_stdout"}, "stderr": {"hmmer_stderr"}}, {}
    if program == "alimask":
        if mode.startswith("mask_"):
            required["masked_alignment"] = {"stockholm", "pfam"}
        optional["header"] = {"alimask_header"}
    elif program == "hmmbuild":
        required["models"] = {"hmmer3_ascii"}
        optional = {"resaved_alignment": {"stockholm"}, "summary": {"hmmbuild_summary"}}
    elif program == "hmmconvert":
        fmt = {"ascii": "hmmer3_ascii", "binary": "hmmer_binary", "legacy_hmmer2": "hmmer2_ascii"}[mode]
        required.update(stdout={fmt}, converted_models={fmt})
    elif program == "hmmemit":
        required["generated_alignment" if mode == "sample_core_aligned" else "generated_sequences"] = {"stockholm" if mode == "sample_core_aligned" else "fasta"}
    elif program == "hmmfetch":
        required["ssi" if mode == "index" else "fetched_models"] = {"hmmer_ssi" if mode == "index" else "hmmer3_ascii"}
    elif program == "hmmpress":
        required.update(binary_models={"hmmer_binary"}, ssi_index={"hmmer_ssi"}, msv_profiles={"hmmer_h3f"}, remaining_profiles={"hmmer_h3p"})
    elif program == "hmmsim":
        required.update(summary={"hmmsim_summary"}, scores={"native_float64_vector"})
        optional = {"alignments": {"hmmsim_alignments"}, "filter": {"hmmsim_filter"}, "survival": {"hmmsim_xy"}, "expected_counts": {"hmmsim_xy"}}
    elif program == "makehmmerdb":
        required["fm_database"] = {"hmmer_fm_3_4"}
    elif program == "hmmerfm-exactmatch":
        required["hits"] = {"hmmerfm_exactmatch_hits"}
    return required, optional


def parse_ranges(value):
    """Native coordinate request occurrences, limited to the real 100 slots."""
    ranges = value.split(",")
    if not 1 <= len(ranges) <= 100:
        _error("alimask_range_capacity")
    result = []
    for item in ranges:
        match = re.fullmatch(r"([0-9]+)(?:-|\.\.)([0-9]+)", item)
        if match is None:
            _error("alimask_range_syntax")
        start, end = map(int, match.groups())
        if not 1 <= start <= end <= 2147483647:
            _error("alimask_range_bounds")
        result.append((start, end))
    return result


def _number(raw, kind, flag):
    integer = kind in {"uint", "positive_int", "min_five", "min_ten", "bin", "power_two", "block"}
    try:
        value = int(raw) if integer and re.fullmatch(r"[+]?\d+", raw) else float(raw)
        valid = math.isfinite(value)
        if integer:
            valid &= type(value) is int and 0 <= value <= 2147483647
        if kind in {"positive_int", "positive", "power_two", "block"}:
            valid &= value > 0
        if kind == "min_five":
            valid &= value >= 5
        if kind == "min_ten":
            valid &= value >= 10  # native unconditionally reads the tenth-highest score
        if kind == "fraction":
            valid &= 0 <= value <= 1
        if kind == "open_fraction":
            valid &= 0 < value < 1
        if kind == "half_open":
            valid &= 0 <= value < .5
        if kind == "unit_open":
            valid &= 0 <= value < 1
        if kind in {"bin", "power_two"}:
            valid &= type(value) is int and value > 0 and value & (value - 1) == 0
        if kind == "bin":
            valid &= 32 <= value <= 4096
        if kind == "block":
            valid &= value <= 2147  # C int multiplication by 1000000 precedes uint32 assignment
    except (ValueError, OverflowError, TypeError):
        valid = False
    if not valid:
        _error("invalid_option_operand:" + flag)
    return value


def native_options(job):
    program, mode, tokens = job["program"], job["mode"], job["options"]
    if type(tokens) is not list:
        _error("options_list_required")
    result, index = {}, 0
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
        if kind is None and flag not in _TEXT_OPTIONS.get(program, set()):
            _error("unsupported_or_compiler_owned_option:" + flag)
        if index == len(tokens):
            _error("option_operand_required:" + flag)
        raw = tokens[index]
        _text(raw, "option_operand")
        index += 1
        result[flag] = _number(raw, kind, flag) if kind else raw
    for group in (_ALPHABET, _WEIGHTS, {"--fast", "--hand"} if program in {"alimask", "hmmbuild"} else set(),
                  {"--eent", "--eentexp", "--eclust", "--eset", "--enone"}, {"--pnone", "--plaplace"},
                  {"--local", "--unilocal", "--glocal", "--uniglocal"}, {"--fs", "--sw", "--ls", "--s"}):
        if len(group & result.keys()) > 1:
            _error("mutually_exclusive_options:" + ",".join(sorted(group & result.keys())))
    if "--symfrac" in result and "--hand" in result:
        _error("symfrac_requires_fast")
    for flag, required in (("--wid", "--wblosum"), ("--eid", "--eclust")):
        if flag in result and required not in result:
            _error("option_requires:" + flag + ":" + required)
    roles = {r["role"] for r in job["operands"]}
    outputs = {r["role"] for r in job["outputs"]}
    if program == "alimask":
        if set(RANGE_FLAGS.values()) & result.keys() != {RANGE_FLAGS[mode]}:
            _error("range_mode_conflict")
        parse_ranges(result[RANGE_FLAGS[mode]])
        if "--appendmask" in result and not mode.startswith("mask_"):
            _error("appendmask_requires_mask_mode")
    if program == "hmmbuild":
        if "matrix" in roles and (mode != "build_single_sequence_matrix" or "--mx" in result):
            _error("matrix_mode_or_option_conflict")
        if any(k in result for k in ("--mx", "--popen", "--pextend")) and mode != "build_single_sequence_matrix":
            _error("matrix_parameters_require_single_sequence_mode")
        if "--mx" in result and result["--mx"] not in {"BLOSUM45", "BLOSUM50", "BLOSUM62", "BLOSUM80", "BLOSUM90", "PAM30", "PAM70", "PAM120", "PAM240"}:
            _error("unsupported_substitution_matrix")
        if "HMMER_NCPU" in job["environment"]:
            _number(job["environment"]["HMMER_NCPU"], "uint", "HMMER_NCPU")
    if program == "hmmconvert" and "--outfmt" in result:
        if mode == "legacy_hmmer2" or result["--outfmt"] not in {"3/" + c for c in "abcdef"}:
            _error("conversion_revision_conflict")
    if program == "hmmemit":
        if mode.startswith("consensus_") and "-N" in result:
            _error("consensus_sample_count_conflict")
        if ({"--minl", "--minu"} & result.keys()) and mode != "consensus_thresholded":
            _error("thresholds_require_thresholded_consensus")
        if ({"-L", "--local", "--unilocal", "--glocal", "--uniglocal"} & result.keys()) and mode != "sample_profile":
            _error("profile_options_require_profile_mode")
    if program == "hmmsim":
        if "--fast" in result and mode == "hybrid":
            _error("undefined_native_fast_hybrid")
        if "-a" in result and (mode != "viterbi" or "--fast" in result):
            _error("undefined_native_traceback_combination")
        if "alignments" in outputs and "-a" not in result:
            _error("alignments_require_traceback")
        if "--nu" in result and (mode != "msv" or "--fast" in result):
            _error("nu_requires_generic_msv")
        if "--pthresh" in result and "filter" not in outputs:
            _error("pthresh_requires_filter")
        low, high, points = result.get("--tmin", .02), result.get("--tmax", .02), result.get("--tpoints", 1)
        if low > high or points > 1 and low == high:
            _error("invalid_or_nonadvancing_tail_schedule")
    return result


def _validate_metadata(job):
    metadata = job["input_metadata"]
    if type(metadata) is not dict or set(metadata) - {"producer_contract", "source_binding"}:
        _error("input_metadata_fields")
    if job["program"] not in {"makehmmerdb", "hmmerfm-exactmatch"} and metadata:
        _error("metadata_only_for_fm")
    if job["program"] == "hmmerfm-exactmatch" and "producer_contract" not in metadata:
        _error("fm_producer_contract_required")
    if "producer_contract" in metadata:
        contract = metadata["producer_contract"]
        _object(contract, FM_PRODUCER_FIELDS, "fm_producer_contract")
        if (contract["format"] != "hmmer_fm_3_4" or contract["engine_version"] != "3.4"
                or contract["byte_order"] not in {"little", "big"}
                or any(type(contract[k]) is not int or contract[k] != v for k, v in
                       {"uint8_bytes": 1, "uint16_bytes": 2, "uint32_bytes": 4, "uint64_bytes": 8, "int32_bytes": 4}.items())):
            _error("incompatible_fm_producer_contract")
    if "source_binding" in metadata:
        binding = metadata["source_binding"]
        _object(binding, {"database_occurrence_id", "source_occurrence_ids", "source_sha256s", "producer_attempt_id"}, "fm_source_binding")
        for key in ("database_occurrence_id", "producer_attempt_id"):
            _text(binding[key], key)
        if (type(binding["source_occurrence_ids"]) is not list or type(binding["source_sha256s"]) is not list
                or not binding["source_occurrence_ids"] or len(binding["source_occurrence_ids"]) != len(binding["source_sha256s"])):
            _error("fm_source_binding_population")
        for identifier, digest in zip(binding["source_occurrence_ids"], binding["source_sha256s"]):
            _text(identifier, "source_occurrence_id")
            _sha(digest)


def validate_native_hmmer_preparation_job(value):
    job = finite_json_copy(value)
    _object(job, _JOB_FIELDS, "job")
    if job["version"] != JOB_VERSION:
        _error("job_version")
    program, mode = job["program"], job["mode"]
    _mode(program, mode)
    _object(job["software"], {"executable", "sha256", "engine_version"}, "software")
    _path(job["software"]["executable"], absolute=True)
    _sha(job["software"]["sha256"])
    if job["software"]["engine_version"] != "3.4":
        _error("unverified_engine_version")
    if type(job["environment"]) is not dict:
        _error("environment_object_required")
    for key, setting in job["environment"].items():
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) is None or key in RESERVED_ENVIRONMENT or type(setting) is not str or "\x00" in setting:
            _error("invalid_or_compiler_owned_environment")
    required, optional = operand_contract(program, mode)
    if type(job["operands"]) is not list:
        _error("operands_list_required")
    grouped = {}
    for row in job["operands"]:
        _object(row, {"role", "ordinal", "path", "format", "sha256", "size_bytes", "artifact_ref"}, "operand")
        role = row["role"]
        if type(role) is not str or type(row["format"]) is not str or row["format"] not in {**required, **optional}.get(role, set()):
            _error("operand_role_format_conflict")
        _path(row["path"], absolute=True)
        _sha(row["sha256"])
        _text(row["artifact_ref"], "artifact_ref", nullable=True)
        if type(row["size_bytes"]) is not int or row["size_bytes"] < 0:
            _error("operand_size_invalid")
        if type(row["ordinal"]) is not int or row["ordinal"] != len(grouped.setdefault(role, [])):
            _error("operand_ordinals_must_preserve_role_order")
        grouped[role].append(row)
    if required.keys() - grouped.keys() or any(len(rows) != 1 for role, rows in grouped.items() if role != "source_sequences"):
        _error("missing_or_repeated_operand")
    _text(job["key"], "key", nullable=True)
    if (job["key"] is not None) != (program == "hmmfetch" and mode == "single_key"):
        _error("positional_key_mode_conflict")
    if job["key"] is not None and (job["key"].startswith("-") or any(c.isspace() for c in job["key"])):
        _error("unsafe_positional_key")
    required, optional = output_contract(program, mode)
    if type(job["outputs"]) is not list:
        _error("outputs_list_required")
    outputs, paths = {}, []
    for row in job["outputs"]:
        _object(row, {"role", "format", "relative_path"}, "output")
        role = row["role"]
        if type(role) is not str or role in outputs or type(row["format"]) is not str or row["format"] not in {**required, **optional}.get(role, set()):
            _error("output_role_format_conflict")
        path = _path(row["relative_path"], absolute=False)
        if path.parts[0] in {"inputs", "tmp", "cache", "bundle.json", "request.json"} or path.parts[0].startswith(".") or path.parts[0].startswith("fmtmp"):
            _error("reserved_output_path")
        for old_role, old in paths:
            alias = program == "hmmconvert" and {role, old_role} == {"stdout", "converted_models"} and path == old
            if not alias and (path == old or path in old.parents or old in path.parents):
                _error("output_paths_overlap")
        paths.append((role, path))
        outputs[role] = row
    if required.keys() - outputs.keys():
        _error("required_output_missing")
    if program == "hmmconvert" and outputs["stdout"]["relative_path"] != outputs["converted_models"]["relative_path"]:
        _error("conversion_stdout_must_alias_native_bytes")
    if program == "hmmpress":
        stem = outputs["binary_models"]["relative_path"]
        if not stem.endswith(".h3m") or any(outputs[r]["relative_path"] != stem[:-4] + suffix for r, suffix in PRESS_SUFFIXES.items()):
            _error("pressed_output_stems_differ")
    if program == "hmmfetch" and mode == "index" and not outputs["ssi"]["relative_path"].endswith(".ssi"):
        _error("index_output_suffix")
    if type(job["grading_parameters"]) is not dict:
        _error("grading_parameters_object_required")
    _validate_metadata(job)
    native_options(job)
    return job


def _settings(job):
    selected, program, mode = native_options(job), job["program"], job["mode"]
    defaults = {}
    if program in {"alimask", "hmmbuild"}:
        defaults = {"--symfrac": .5, "--fragthresh": .5, "--wid": .62, "--seed": 42}
        defaults["--hand" if "--hand" in selected else "--fast"] = True
        defaults[next((k for k in sorted(_WEIGHTS) if k in selected), "--wpb")] = True
    if program == "hmmbuild":
        defaults.update(_DEFAULT_CALIBRATION)
        defaults.update({"--esigma": 45., "--eid": .62})
        if not ({"--eent", "--eentexp", "--eclust", "--eset", "--enone"} & selected.keys()):
            defaults["--eent"] = True
        if mode == "build_single_sequence_matrix" and not any(r["role"] == "matrix" for r in job["operands"]):
            defaults["--mx"] = "BLOSUM62"
        # The native CPU default can resolve to available cores. No invented count.
        if "--cpu" not in selected and "HMMER_NCPU" in job["environment"]:
            defaults["--cpu"] = int(job["environment"]["HMMER_NCPU"])
    elif program == "hmmconvert" and mode != "legacy_hmmer2":
        defaults["--outfmt"] = "3/f"
    elif program == "hmmemit":
        defaults["--seed"] = 0
        if mode.startswith("sample_"):
            defaults["-N"] = 1
        if mode == "sample_profile":
            defaults["-L"] = 400
            if not _FLAGS["hmmemit"] & selected.keys():
                defaults["--local"] = True
        if mode == "consensus_thresholded":
            defaults.update({"--minl": 0., "--minu": 0.})
    elif program == "hmmsim":
        defaults = {**_DEFAULT_CALIBRATION, "-N": 1000, "-L": 100, "--seed": 0,
            "--tmin": .02, "--tmax": .02, "--tpoints": 1, "--nu": 2., "--pthresh": .02,
            "--fast": False, "--tlinear": False}
        if not {"--fs", "--sw", "--ls", "--s"} & selected.keys():
            defaults["--fs"] = True
    elif program == "makehmmerdb":
        defaults = {"--bin_length": 256, "--sa_freq": 8, "--block_size": 50, "--fwd_only": False}
    elif program == "hmmerfm-exactmatch":
        defaults["--fwd_only"] = False
    return {**defaults, **selected, **{flag: True for flag in _MODES.get(program, {}).get(mode, [])}}


def compile_native_hmmer_preparation_job(job, *, input_paths=None, output_directory="."):
    job = validate_native_hmmer_preparation_job(job)
    paths = {}
    for row in job["operands"]:
        paths.setdefault(row["role"], []).append(row["path"])
    if input_paths is not None:
        if type(input_paths) is not dict or input_paths.keys() != paths.keys():
            _error("complete_staged_paths_required")
        for role, values in input_paths.items():
            if type(values) is not list or len(values) != len(paths[role]):
                _error("staged_operand_population_changed")
            for path in values:
                _path(path, absolute=True)
        paths = deepcopy(input_paths)
    # Original selected artifacts may live at independent Store paths. Only
    # realized staged paths must satisfy the native implicit-sidecar spelling.
    if input_paths is not None and "ssi" in paths and paths["ssi"][0] != paths["models"][0] + ".ssi":
        _error("staged_index_model_stem_conflict")
    if output_directory != ".":
        _path(output_directory, absolute=True)
    out = {r["role"]: str(PurePosixPath(output_directory) / r["relative_path"]) for r in job["outputs"]}
    all_inputs = [PurePosixPath(p) for values in paths.values() for p in values]
    for target in out.values():
        path = PurePosixPath(target)
        if any(path == p or path in p.parents or p in path.parents for p in all_inputs):
            _error("output_overwrites_original_operand")
    program, mode = job["program"], job["mode"]
    argv = [job["software"]["executable"], *job["options"], *_MODES.get(program, {}).get(mode, [])]
    settings, copies = _settings(job), []

    def redirected(role, flag):
        if role in out:
            argv.extend((flag, out[role]))

    def copy(role, destination):
        path = PurePosixPath(destination)
        if any(path == p or path in p.parents or p in path.parents for p in all_inputs):
            _error("working_copy_overwrites_original_operand")
        for target in out.values():
            other = PurePosixPath(target)
            if path == other or path in other.parents or other in path.parents:
                _error("working_copy_output_path_overlap")
        copies.append({"operand_role": role, "operand_ordinal": 0, "destination": destination, "mutable": False})
        return destination

    if program in {"alimask", "hmmbuild", "makehmmerdb"}:
        role = "sequences" if program == "makehmmerdb" else "alignment"
        fmt = next(r["format"] for r in job["operands"] if r["role"] == role)
        argv += ["--informat", FORMAT_ARGUMENTS[fmt]]
        settings["--informat"] = FORMAT_ARGUMENTS[fmt]
    if program == "alimask":
        redirected("header", "-o")
        if "masked_alignment" in out:
            fmt = next(r["format"] for r in job["outputs"] if r["role"] == "masked_alignment")
            argv += ["--outformat", FORMAT_ARGUMENTS[fmt]]
            settings["--outformat"] = FORMAT_ARGUMENTS[fmt]
        argv += paths["alignment"]
        if "masked_alignment" in out:
            argv += [out["masked_alignment"]]
    elif program == "hmmbuild":
        if "matrix" in paths:
            argv += ["--mxfile", paths["matrix"][0]]
        redirected("summary", "-o")
        redirected("resaved_alignment", "-O")
        argv += [out["models"], paths["alignment"][0]]
    elif program == "hmmconvert":
        argv += paths["models"]
    elif program == "hmmemit":
        redirected("generated_alignment" if mode == "sample_core_aligned" else "generated_sequences", "-o")
        argv += paths["models"]
    elif program == "hmmfetch":
        if mode == "index":
            argv += [copy("models", out["ssi"][:-4])]
        else:
            redirected("fetched_models", "-o")
            argv += paths["models"] + ([job["key"]] if mode == "single_key" else paths["keys"])
            if mode == "single_key":
                settings["key"] = job["key"]
    elif program == "hmmpress":
        argv += [copy("models", out["binary_models"][:-4])]
    elif program == "hmmsim":
        for role, flag in (("summary", "-o"), ("scores", "--xfile"), ("alignments", "--afile"), ("filter", "--ffile"), ("survival", "--pfile"), ("expected_counts", "--efile")):
            redirected(role, flag)
        argv += paths["models"]
    elif program == "makehmmerdb":
        argv += paths["sequences"] + [out["fm_database"]]
    elif program == "hmmerfm-exactmatch":
        redirected("hits", "--out")
        argv += paths["queries"] + paths["fm_database"]
    else:
        argv += paths["models"]
    return {"argv": argv, "environment": deepcopy(job["environment"]), "outputs": deepcopy(job["outputs"]),
            "working_copies": copies, "operation": {"program": program, "mode": mode,
                "engine_version": job["software"]["engine_version"], "settings": settings}}


def requested_job_from_hmmer_preparation(job):
    job = validate_native_hmmer_preparation_job(job)
    compiled = compile_native_hmmer_preparation_job(job)
    return {"argv": compiled["argv"], "environment": compiled["environment"], "native_hmmer_preparation": job}


def recorded_operation_matches_compiled(recorded, compiled):
    """Validate original operations without rewriting old incomplete records.

    The initial v1 producer omitted two false hmmsim defaults. Their absence
    remains absent in saved bundles and saved grading. Only that exact omission
    is accepted; a selected true flag, changed quantity, or other missing field
    cannot pass through this historical-record check. New compilation always
    records both flags, as the numerical consumer requires.
    """
    recorded, compiled = finite_json_copy(recorded), finite_json_copy(compiled)
    if native_infernal_digest(recorded) == native_infernal_digest(compiled):
        return True
    if (type(recorded) is not dict or type(compiled) is not dict
            or set(recorded) != {"program", "mode", "engine_version", "settings"}
            or set(compiled) != set(recorded) or recorded["program"] != "hmmsim"
            or compiled["program"] != "hmmsim" or recorded["engine_version"] != "3.4"
            or type(recorded["settings"]) is not dict or type(compiled["settings"]) is not dict):
        return False
    historical = deepcopy(compiled)
    for flag in ("--fast", "--tlinear"):
        if flag not in recorded["settings"] and historical["settings"].get(flag) is False:
            del historical["settings"][flag]
    return native_infernal_digest(recorded) == native_infernal_digest(historical)


def validate_native_hmmer_preparation_requested_job(value):
    request = finite_json_copy(value)
    _object(request, {"argv", "environment", "native_hmmer_preparation"}, "requested_job")
    if request != requested_job_from_hmmer_preparation(request["native_hmmer_preparation"]):
        _error("requested_job_compiler_mismatch")
    return request


__all__ = ["JOB_VERSION", "PROGRAM_MODES", "operand_contract", "output_contract", "native_options",
           "validate_native_hmmer_preparation_job", "compile_native_hmmer_preparation_job",
           "recorded_operation_matches_compiled",
           "requested_job_from_hmmer_preparation", "validate_native_hmmer_preparation_requested_job"]
