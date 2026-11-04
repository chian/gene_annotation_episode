"""Pure selected-request tests. Native producer coverage is in the driver tests."""
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from gene_annotation_episode.native_hmmer_preparation_contracts import (
    JOB_VERSION, PROGRAM_MODES, RANGE_FLAGS, compile_native_hmmer_preparation_job,
    output_contract, requested_job_from_hmmer_preparation,
    recorded_operation_matches_compiled,
    validate_native_hmmer_preparation_job, validate_native_hmmer_preparation_requested_job,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259"
NATIVE = EVIDENCE / "native"
BIN = ROOT / "resources/software/infernal-1.1.5/hmmer/src"
MODEL = NATIVE / "hmmbuild_protein/profile.hmm"
FM_CONTRACT = {"format": "hmmer_fm_3_4", "engine_version": "3.4", "byte_order": "little", "uint8_bytes": 1,
    "uint16_bytes": 2, "uint32_bytes": 4, "uint64_bytes": 8, "int32_bytes": 4}
CASES = [(p, m) for p, modes in PROGRAM_MODES.items() for m in modes]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def operand(role, path, fmt, ordinal=0):
    return {"role": role, "ordinal": ordinal, "path": str(path), "format": fmt,
        "sha256": digest(path), "size_bytes": path.stat().st_size, "artifact_ref": f"fixture267:{role}:{ordinal}"}


def job(program="hmmconvert", mode="ascii", options=None):
    inputs = [operand("models", MODEL, "hmmer3_ascii")]
    defaults = []
    metadata = {}
    if program in {"alimask", "hmmbuild"}:
        source = "protein_single.sto" if mode == "build_single_sequence_matrix" else "protein.sto"
        inputs = [operand("alignment", EVIDENCE / "inputs" / source, "stockholm")]
        defaults = ["--amino", "--hand"] if program == "alimask" else ["--amino", "--cpu", "1", "--seed", "42"]
        if program == "alimask":
            defaults += [RANGE_FLAGS[mode], "2-4"]
    elif program == "hmmemit":
        defaults = ["--seed", "42"]
        if mode.startswith("sample_"):
            defaults += ["-N", "3"]
        if mode == "sample_profile":
            defaults += ["-L", "20"]
        if mode == "consensus_thresholded":
            defaults += ["--minl", "0.8", "--minu", "0.9"]
    elif program == "hmmfetch" and mode == "key_file":
        inputs += [operand("keys", EVIDENCE / "inputs/keys_alias.txt", "key_file")]
    elif program == "hmmsim":
        inputs = [operand("models", NATIVE / "hmmbuild_dna/profile.hmm", "hmmer3_ascii")]
        defaults = ["--seed", "42", "-N", "1000", "-L", "30"]
    elif program == "makehmmerdb":
        inputs = [operand("sequences", EVIDENCE / "inputs/tiny.fa", "fasta")]
        defaults = ["--dna", "--block_size", "1"]
    elif program == "hmmerfm-exactmatch":
        inputs = [operand("queries", EVIDENCE / "inputs/queries.txt", "literal_query_lines"),
            operand("fm_database", NATIVE / "makehmmerdb_dna/index.fm", "hmmer_fm_3_4"),
            operand("source_sequences", EVIDENCE / "inputs/tiny.fa", "fasta")]
        metadata = {"producer_contract": deepcopy(FM_CONTRACT)}
    outputs = []
    suffixes = {"binary_models": ".h3m", "ssi_index": ".h3i", "msv_profiles": ".h3f", "remaining_profiles": ".h3p", "ssi": ".ssi"}
    for role, formats in output_contract(program, mode)[0].items():
        fmt = "stockholm" if role == "masked_alignment" else sorted(formats)[0]
        path = "outputs/" + role
        if role in suffixes:
            path = "work/models.hmm" + suffixes[role]
        if program == "hmmconvert" and role in {"stdout", "converted_models"}:
            path = "outputs/converted_models"
        outputs.append({"role": role, "format": fmt, "relative_path": path})
    executable = BIN / program
    return {"version": JOB_VERSION, "program": program, "mode": mode,
        "software": {"executable": str(executable), "sha256": digest(executable), "engine_version": "3.4"},
        "environment": {}, "operands": inputs, "options": defaults if options is None else list(options), "outputs": outputs,
        "key": "TINY001" if (program, mode) == ("hmmfetch", "single_key") else None,
        "input_metadata": metadata, "grading_parameters": {}}


@pytest.mark.parametrize("program,mode", CASES)
def test_exact_pure_roundtrip_and_selected_options(program, mode, monkeypatch):
    selected = job(program, mode)
    original = deepcopy(selected)
    monkeypatch.setattr(Path, "read_bytes", lambda *a: pytest.fail("pure compiler read file"))
    request = requested_job_from_hmmer_preparation(selected)
    assert validate_native_hmmer_preparation_requested_job(request) == request
    assert selected == original
    compiled = compile_native_hmmer_preparation_job(selected)
    assert compiled["argv"][1:1+len(selected["options"])] == selected["options"]
    assert compiled["environment"] == selected["environment"]
    changed = deepcopy(request)
    changed["argv"].append("--unselected")
    with pytest.raises(ValueError, match="compiler_mismatch"):
        validate_native_hmmer_preparation_requested_job(changed)


@pytest.mark.parametrize("program,mode,options", [
    ("alimask", "mask_alignment", ["--alirange", ",".join(["1-2"]*101)]),
    ("alimask", "mask_alignment", ["--alirange", "0-2"]),
    ("alimask", "mask_alignment", ["--alirange", "3-2"]),
    ("alimask", "mask_alignment", ["--modelrange", "1-2"]),
    ("alimask", "mask_alignment", ["--alirange", "1-2", "--hand", "--symfrac", ".5"]),
    ("hmmbuild", "build_alignment", ["--amino", "--dna"]),
    ("hmmbuild", "build_alignment", ["--wnone", "--wgiven"]),
    ("hmmbuild", "build_alignment", ["--cpu", "1.0"]),
    ("hmmbuild", "build_alignment", ["--cpu", "2147483648"]),
    ("hmmbuild", "build_alignment", ["--popen", ".5"]),
    ("hmmbuild", "build_alignment", ["--wid", ".5"]),
    ("hmmemit", "consensus_simple", ["-N", "2"]),
    ("hmmemit", "sample_core_unaligned", ["-L", "30"]),
    ("hmmemit", "sample_profile", ["--local", "--glocal"]),
    ("hmmemit", "sample_profile", ["--seed", "nan"]),
    ("hmmconvert", "legacy_hmmer2", ["--outfmt", "3/f"]),
    ("hmmconvert", "ascii", ["--outfmt", "3/g"]),
    ("hmmsim", "hybrid", ["--fast"]),
    ("hmmsim", "viterbi", ["--fast", "-a"]),
    ("hmmsim", "forward", ["-a"]),
    ("hmmsim", "forward", ["-N", "9"]),
    ("hmmsim", "forward", ["--tmin", ".1", "--tmax", ".1", "--tpoints", "2"]),
    ("makehmmerdb", "build", ["--sa_freq", "0"]),
    ("makehmmerdb", "build", ["--sa_freq", "3"]),
    ("makehmmerdb", "build", ["--bin_length", "31"]),
    ("makehmmerdb", "build", ["--block_size", "2148"]),
    ("hmmstat", "summary", ["--unknown"]),
    ("hmmconvert", "binary", ["-o", "/tmp/escape"]),
])
def test_invalid_native_combinations_are_not_repaired(program, mode, options):
    selected = job(program, mode, options)
    original = deepcopy(selected)
    with pytest.raises(ValueError):
        validate_native_hmmer_preparation_job(selected)
    assert selected == original


def test_explicit_ssi_original_paths_are_independent_but_staging_must_pair():
    selected = job("hmmfetch", "single_key")
    index = operand("ssi", NATIVE / "hmmfetch_index/models.hmm.ssi", "hmmer_ssi")
    index["path"] = "/explicit-store/index-artifact-with-independent-name"
    selected["operands"].append(index)
    request = requested_job_from_hmmer_preparation(selected)
    assert validate_native_hmmer_preparation_requested_job(request) == request
    assert request["native_hmmer_preparation"]["operands"][-1]["path"] == index["path"]
    with pytest.raises(ValueError, match="staged_index_model_stem_conflict"):
        compile_native_hmmer_preparation_job(selected,
            input_paths={"models": ["/attempt/inputs/models.hmm"], "ssi": ["/attempt/inputs/unpaired.ssi"]})


def test_defaults_seed_zero_and_cpu_environment_preserved():
    selected = job("hmmbuild", "build_alignment", [])
    compiled = compile_native_hmmer_preparation_job(selected)
    assert "--cpu" not in compiled["operation"]["settings"]
    selected["environment"] = {"HMMER_NCPU": "3"}
    assert compile_native_hmmer_preparation_job(selected)["operation"]["settings"]["--cpu"] == 3
    selected = job("hmmemit", "sample_core_unaligned", [])
    assert compile_native_hmmer_preparation_job(selected)["operation"]["settings"]["--seed"] == 0
    assert "--seed" not in compile_native_hmmer_preparation_job(selected)["argv"]


@pytest.mark.parametrize("mode", ["viterbi", "msv", "forward", "hybrid"])
def test_simulation_records_actual_false_flags_without_changing_command(mode):
    selected = job("hmmsim", mode)
    compiled = compile_native_hmmer_preparation_job(selected)
    assert compiled["operation"]["settings"]["--fast"] is False
    assert compiled["operation"]["settings"]["--tlinear"] is False
    assert "--fast" not in compiled["argv"] and "--tlinear" not in compiled["argv"]
    from gene_annotation_episode.hmmer_simulation_data import _settings, recorded_tail_masses
    issues = []
    _, valid = _settings(compiled["operation"], issues)
    assert valid and issues == []
    assert recorded_tail_masses(compiled["operation"]["settings"]) == ([.02], None)


def test_explicit_simulation_flags_and_original_incomplete_records():
    selected = job("hmmsim", "viterbi", ["--fast", "--tlinear"])
    chosen = compile_native_hmmer_preparation_job(selected)["operation"]
    assert chosen["settings"]["--fast"] is True and chosen["settings"]["--tlinear"] is True
    absent_selected = deepcopy(chosen)
    del absent_selected["settings"]["--fast"]
    assert not recorded_operation_matches_compiled(absent_selected, chosen)
    current = compile_native_hmmer_preparation_job(job("hmmsim", "viterbi"))["operation"]
    old = deepcopy(current)
    del old["settings"]["--fast"], old["settings"]["--tlinear"]
    original = deepcopy(old)
    assert recorded_operation_matches_compiled(old, current)
    assert old == original
    for field, value in [("--seed", 99), ("-N", 20), ("--fast", 0)]:
        changed = deepcopy(old)
        changed["settings"][field] = value
        assert not recorded_operation_matches_compiled(changed, current)


@pytest.mark.parametrize("fault", ["alias", "traversal", "parent_child", "reserved", "copy_overlap", "metadata", "environment", "unknown_field"])
def test_exact_paths_roles_and_metadata(fault):
    selected = job("hmmpress", "index")
    if fault == "alias":
        selected = job()
        selected["outputs"][0]["relative_path"] = "other"
    elif fault == "traversal":
        selected["outputs"][0]["relative_path"] = "../elsewhere"
    elif fault == "parent_child":
        selected["outputs"][0]["relative_path"] = "work"
    elif fault == "reserved":
        selected["outputs"][0]["relative_path"] = "fmtmpABC123"
    elif fault == "copy_overlap":
        selected["outputs"][0]["relative_path"] = "work/models.hmm"
    elif fault == "metadata":
        selected["input_metadata"] = {"unknown": True}
    elif fault == "environment":
        selected["environment"] = {"TMPDIR": "/elsewhere"}
    else:
        selected["extra"] = True
    with pytest.raises(ValueError):
        compile_native_hmmer_preparation_job(selected)


def test_complete_staged_paths_and_output_input_overlap():
    selected = job("hmmstat", "summary")
    with pytest.raises(ValueError, match="complete_staged_paths"):
        compile_native_hmmer_preparation_job(selected, input_paths={})
    with pytest.raises(ValueError, match="overwrites_original"):
        compile_native_hmmer_preparation_job(selected, input_paths={"models": ["/attempt/outputs/stdout"]}, output_directory="/attempt")
    selected = job("hmmpress", "index")
    with pytest.raises(ValueError, match="working_copy_overwrites"):
        compile_native_hmmer_preparation_job(selected, input_paths={"models": ["/attempt/work/models.hmm"]}, output_directory="/attempt")


def test_grading_parameters_are_finite_retained_data_not_an_execution_language():
    selected = job()
    selected["grading_parameters"] = {"uninterpreted_for_separate_calculator": {"value": 3., "array": [None, True]}}
    assert validate_native_hmmer_preparation_job(selected) == selected
    selected["grading_parameters"]["bad"] = float("inf")
    with pytest.raises(ValueError):
        validate_native_hmmer_preparation_job(selected)
