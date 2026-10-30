"""Selected native commands and immutable preparation operands, not an episode test."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from gene_annotation_episode.native_infernal_preparation_contracts import (
    JOB_VERSION, compile_native_infernal_preparation_job, output_contract,
    requested_job_from_infernal_preparation, validate_native_infernal_preparation_job,
    validate_native_infernal_preparation_requested_job,
)


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "verification/tool_graders_infernal_preparation_boundaries_2026-10-26_246/native"
BIN = ROOT / "resources/software/infernal-1.1.5-install/bin"
MODELS = NATIVE / "cmbuild_hand/built.cm"
CALIBRATED = NATIVE / "cmcalibrate_tiny/model.cm"


def operand(role, path, fmt, ordinal=0):
    raw = path.read_bytes()
    return {"role": role, "ordinal": ordinal, "path": str(path), "format": fmt,
            "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw),
            "artifact_ref": "fixture:" + role + ":" + str(ordinal)}


def job(program, mode, options=()):
    executable = BIN / program
    inputs = ([operand("alignment", NATIVE / "cmbuild_hand/seed.sto", "stockholm")]
              if program == "cmbuild" else [operand("models", CALIBRATED if program == "cmstat" else MODELS, "infernal_cm_ascii")])
    if program == "cmfetch" and mode == "key_file":
        inputs = [operand("models", NATIVE / "cmfetch_missing_unindexed/models.cm", "infernal_cm_ascii"),
                  operand("keys", NATIVE / "cmfetch_missing_unindexed/keys.txt", "key_file")]
    if program == "cmcalibrate" and mode == "merge_scores":
        inputs += [operand("partition_scores", NATIVE / f"cmcalibrate_partition_{i}/scores.dat",
                           "infernal_partition_scores", i - 1) for i in (1, 2)]
    required, _ = output_contract(program, mode)
    outputs = []
    for role, formats in required.items():
        fmt = "stockholm" if role == "generated_alignment" else "infernal_cm_ascii" if role == "calibrated_models" else sorted(formats)[0]
        path = "outputs/" + role
        if role in {"i1m", "i1i", "i1f", "i1p", "ssi"}:
            path = "work/models.cm." + role
        outputs.append({"role": role, "format": fmt, "relative_path": path})
    return {"version": JOB_VERSION, "program": program, "mode": mode,
            "software": {"executable": str(executable), "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                         "engine_version": "1.1.5"}, "environment": {}, "operands": inputs,
            "options": list(options), "outputs": outputs,
            "key": "fixture246" if program == "cmfetch" and mode == "single_key" else None,
            "grading_parameters": {}}


CASES = [
    ("cmbuild", "build", ["--hand"]),
    ("cmbuild", "refine", ["--hand"]),
    ("cmcalibrate", "calibrate", ["-L", "0.01", "--tailp", "0.1", "--seed", "181", "--cpu", "1", "--noforecast"]),
    ("cmcalibrate", "forecast", ["-L", "0.01", "--nforecast", "1"]),
    ("cmcalibrate", "memory_estimate", ["-L", "0.01"]),
    ("cmcalibrate", "split_commands", ["-L", "0.02", "--ptot", "2", "--cpu", "1"]),
    ("cmcalibrate", "partition_scores", ["-L", "0.02", "--part", "1", "--ptot", "2", "--cpu", "1", "--seed", "181"]),
    ("cmcalibrate", "merge_scores", ["-L", "0.02", "--ptot", "2", "--tailp", "0.1", "--cpu", "1"]),
    *[("cmconvert", mode, []) for mode in ("ascii", "binary", "legacy_ascii", "maximum_likelihood_hmm", "filter_hmm")],
    *[("cmemit", mode, ["--seed", "181", "-N", "2"]) for mode in ("sample_unaligned", "sample_aligned", "consensus")],
    *[("cmfetch", mode, []) for mode in ("single_key", "key_file", "index")],
    ("cmpress", "press", []),
    ("cmstat", "summary", []), ("cmstat", "scores_at_evalue", ["-E", "0.01"]),
    ("cmstat", "scores_at_pvalue", ["-P", "0.01"]), ("cmstat", "evalues_at_score", ["-T", "10"]),
    *[("cmstat", "evalues_at_" + cutoff, []) for cutoff in ("ga", "nc", "tc")],
]


@pytest.mark.parametrize("program,mode,options", CASES, ids=[p + "-" + m for p, m, _ in CASES])
def test_compiled_command_runs_actual_selected_mode_without_changing_inputs(tmp_path, program, mode, options):
    selected = job(program, mode, options)
    original = {row["path"]: hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest() for row in selected["operands"]}
    paths = {}
    for row in selected["operands"]:
        target = tmp_path / "inputs" / row["role"] / str(row["ordinal"])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(row["path"], target)
        paths.setdefault(row["role"], []).append(str(target))
    compiled = compile_native_infernal_preparation_job(selected, input_paths=paths, output_directory=str(tmp_path))
    for output in compiled["outputs"]:
        (tmp_path / output["relative_path"]).parent.mkdir(parents=True, exist_ok=True)
    for copy in compiled["working_copies"]:
        target = Path(copy["destination"])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(paths[copy["operand_role"]][copy["operand_ordinal"]], target)
    # Tests run under the existing bounded local_jobs runner. This subprocess is
    # the selected native executable, not an independent unbounded job wrapper.
    environment = {**os.environ, **compiled["environment"], "TMPDIR": str(tmp_path)}
    environment.pop("INFERNAL_NCPU", None)  # fixture explicitly selects its environment
    outputs = {row["role"]: tmp_path / row["relative_path"] for row in compiled["outputs"]}
    with outputs["stdout"].open("wb") as out, outputs["stderr"].open("wb") as err:
        native = subprocess.run(compiled["argv"], cwd=tmp_path, env=environment, stdout=out, stderr=err)
    (tmp_path / "selected-job.json").write_text(json.dumps(selected, indent=2) + "\n")
    (tmp_path / "compiled-command.json").write_text(json.dumps(compiled, indent=2) + "\n")
    assert native.returncode == 0, outputs["stdout"].read_text() + outputs["stderr"].read_text()
    assert all(path.is_file() for path in outputs.values())
    assert {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in original} == original
    assert all(hashlib.sha256(Path(paths[row["role"]][row["ordinal"]]).read_bytes()).hexdigest() == row["sha256"]
               for row in selected["operands"])
    if program == "cmemit" and mode == "consensus":
        assert outputs["generated_sequences"].read_text().splitlines()[1] == "GCGCaaAAGCGC"
    if program == "cmcalibrate" and mode in {"calibrate", "merge_scores"}:
        assert "ECMLC" in outputs["calibrated_models"].read_text()
        assert "ECMLC" not in MODELS.read_text()
    if program == "cmfetch" and mode == "key_file":
        assert "absent_key" in Path(selected["operands"][1]["path"]).read_text()
        assert "absent_key" not in outputs["fetched_models"].read_text()


def test_exact_requested_job_and_no_side_effects(tmp_path, monkeypatch):
    selected = job("cmcalibrate", "calibrate", ["-L", "0.01"])
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("compiler executed work"))
    request = requested_job_from_infernal_preparation(selected)
    assert validate_native_infernal_preparation_requested_job(request) == request
    assert not list(tmp_path.iterdir())
    forged = deepcopy(request)
    forged["argv"][-1] = str(MODELS)
    with pytest.raises(ValueError, match="compiler_mismatch"):
        validate_native_infernal_preparation_requested_job(forged)


@pytest.mark.parametrize("field,value", [("--cpu", "1"), ("INFERNAL_NCPU", "2")])
def test_forecast_cpu_conflicts_are_not_silently_repaired(field, value):
    selected = job("cmcalibrate", "forecast")
    if field.startswith("--"):
        selected["options"] = [field, value]
    else:
        selected["environment"][field] = value
    before = deepcopy(selected)
    with pytest.raises(ValueError, match="cpu_environment_conflict"):
        validate_native_infernal_preparation_job(selected)
    assert selected == before


@pytest.mark.parametrize("mode,options", [("summary", ["-E", "1"]), ("scores_at_evalue", ["-P", "0.1"]),
                                          ("scores_at_pvalue", ["-P", "1.1"]), ("evalues_at_score", ["-T", "nan"])])
def test_statistic_selection_and_number_validation(mode, options):
    with pytest.raises(ValueError):
        validate_native_infernal_preparation_job(job("cmstat", mode, options))


def test_alignment_format_follows_role_not_operand_list_position():
    selected = job("cmbuild", "build")
    extra = deepcopy(selected["operands"][0])
    extra.update(role="prior", format="text", artifact_ref="fixture:prior")
    selected["operands"].insert(0, extra)
    compiled = compile_native_infernal_preparation_job(selected)
    assert compiled["argv"][compiled["argv"].index("--informat") + 1] == "Stockholm"


@pytest.mark.parametrize("mutation", ["mixed_stems", "input_overwrite", "path_traversal", "copy_log_overlap"])
def test_index_and_working_copy_ownership(mutation):
    selected = job("cmpress", "press")
    if mutation == "mixed_stems":
        next(r for r in selected["outputs"] if r["role"] == "i1f")["relative_path"] = "other.cm.i1f"
    elif mutation == "path_traversal":
        selected["outputs"][0]["relative_path"] = "../outside"
    elif mutation == "copy_log_overlap":
        next(r for r in selected["outputs"] if r["role"] == "stdout")["relative_path"] = "work/models.cm"
    else:
        # Explicit staged input equals the compiler's selected owned copy destination.
        with pytest.raises(ValueError, match="overwrites_original"):
            compile_native_infernal_preparation_job(selected, input_paths={"models": ["/owned/work/models.cm"]}, output_directory="/owned")
        return
    with pytest.raises(ValueError):
        compile_native_infernal_preparation_job(selected)


def test_binary_calibration_output_is_not_mislabeled_ascii():
    selected = job("cmcalibrate", "calibrate")
    selected["operands"][0]["format"] = "infernal_cm_binary"
    with pytest.raises(ValueError, match="native_writer"):
        validate_native_infernal_preparation_job(selected)
    next(r for r in selected["outputs"] if r["role"] == "calibrated_models")["format"] = "infernal_cm_binary"
    validate_native_infernal_preparation_job(selected)


def test_mode_parser_rejects_new_hidden_path_or_mode_options():
    for options in (["-o", "/elsewhere"], ["--index"], ["--fhmm"], ["--unknown"]):
        with pytest.raises(ValueError, match="compiler_owned"):
            validate_native_infernal_preparation_job(job("cmconvert", "ascii", options))
