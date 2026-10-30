"""Pure compiler/selection checks; these do not prove episode integration."""
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.native_hmmer_contracts import (
    NATIVE_HMMER_JOB_SCHEMA, NATIVE_HMMER_REQUESTED_JOB_SCHEMA, PROGRAMS,
    compile_native_hmmer_job, operand_contract, output_contract,
    requested_job_from_native, validate_native_hmmer_job, validate_native_hmmer_requested_job,
)
from gene_annotation_episode.native_hmmer_tool_info import (
    native_hmmer_tool_contracts, native_hmmer_tool_information, validate_native_hmmer_bindings,
)


def job_for(program="hmmsearch", mode=None):
    mode = mode or ("sequence" if program == "nhmmer" else "align" if program == "hmmalign" else "search")
    required, _ = operand_contract(program, mode)
    outputs, _ = output_contract(program, mode)
    operands = []
    for role, formats in required.items():
        path = "/selected/" + role
        if role.startswith("profile_database_h3"):
            path = "/selected/profile_database." + role.rsplit("_", 1)[1]
        operands.append({"role": role, "format": sorted(formats)[0], "path": path,
                         "sha256": "a" * 64, "size_bytes": 123, "artifact_ref": None})
    return {"version": "native_hmmer_job_v1", "program": program, "mode": mode,
        "software": {"executable": "/selected/bin/" + program, "sha256": "b" * 64, "engine_version": "3.4"},
        "environment": {"HMMER_NCPU": "1"}, "operands": operands, "operand_bindings": [],
        "options": [] if program == "hmmalign" else ["--cpu", "1"],
        "outputs": [{"role": role, "format": fmt, "relative_path": "out/" + role} for role, fmt in outputs.items()],
        "metadata": {}, "grading_parameters": {}}


@pytest.mark.parametrize("program,mode", [(p, None) for p in PROGRAMS] + [("nhmmer", "profile"), ("nhmmer", "alignment")])
def test_original_and_staged_compilers_are_pure_and_schema_valid(monkeypatch, program, mode):
    job = job_for(program, mode)
    before = deepcopy(job)
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("pure compiler opened a file"))
    monkeypatch.setattr(Path, "resolve", lambda *a, **k: pytest.fail("pure compiler resolved a file"))
    original = compile_native_hmmer_job(job)
    request = requested_job_from_native(job)
    assert request["argv"] == original["argv"]
    assert request["environment"] == original["environment"]
    assert validate_native_hmmer_requested_job(request) == request
    Draft202012Validator(NATIVE_HMMER_JOB_SCHEMA).validate(job)
    Draft202012Validator(NATIVE_HMMER_REQUESTED_JOB_SCHEMA).validate(request)
    paths = {r["role"]: r["path"].replace("/selected/", "/attempt/inputs/") for r in job["operands"]}
    staged = compile_native_hmmer_job(job, input_paths=paths, output_directory="/attempt")
    assert staged["argv"][0] == original["argv"][0]
    assert staged["outputs"] == job["outputs"]
    assert any(arg.startswith("/attempt/") for arg in staged["argv"])
    assert job == before


@pytest.mark.parametrize("flags,code", [
    (["--tblout", "escape"], "compiler_owned_option"), (["-o", "escape"], "compiler_owned_option"),
    (["--dfamtblout", "escape"], "unsupported_path_option"), (["--mxfile", "escape"], "unsupported_path_option"),
    (["--ssifile", "escape"], "unsupported_path_option"), (["--mpi"], "unsupported_option"),
    (["--cpu", "1", "--cpu", "2"], "duplicate_option"), (["-E", "1", "-T", "2"], "conflicting_options"),
    (["--max", "--F1", "0.2"], "conflicting_filter"), (["--cut_ga", "--incT", "2"], "conflicting_threshold"),
    (["--cpu"], "option_operand_required"), (["--cpu", "1.5"], "invalid_option_operand"),
    (["-Z", "nan"], "invalid_option_operand"), (["--textw", "80"], "invalid_option_operand"),
])
def test_unsupported_path_and_conflicting_options_reject(flags, code):
    job = job_for()
    job["options"] = flags
    with pytest.raises(ValueError, match=code):
        validate_native_hmmer_job(job)


@pytest.mark.parametrize("relative", ["../escape", "/absolute", "a/../b", "a//b", "inputs/x", "bundle.json", "tmp/x", "a\nb", ".bundle.json.writing"])
def test_output_confinement(relative):
    job = job_for()
    job["outputs"][0]["relative_path"] = relative
    with pytest.raises(ValueError):
        validate_native_hmmer_job(job)


def test_pressed_indexes_are_explicit_and_keep_native_stem():
    job = job_for("hmmscan")
    job["operands"][-1]["path"] = "/unrelated/index.h3p"
    with pytest.raises(ValueError, match="pressed_index_path_association"):
        validate_native_hmmer_job(job)
    job = job_for("nhmmscan")
    job["operands"].pop()
    with pytest.raises(ValueError, match="missing_operand_roles"):
        validate_native_hmmer_job(job)


def test_native_mode_flags_and_optional_checkpoint_contract():
    job = job_for("nhmmer", "sequence")
    assert "--qsingle_seqs" in compile_native_hmmer_job(job)["argv"]
    job = job_for("nhmmer", "profile")
    job["options"] += ["--qsingle_seqs"]
    with pytest.raises(ValueError, match="mode_option_conflict"):
        validate_native_hmmer_job(job)
    job = job_for("jackhmmer")
    job["options"] += ["-N", "3", "--popen", "0.1"]
    job["outputs"] += [{"role": "checkpoint_hmm", "format": "hmmer3_ascii", "relative_path": "checkpoints/model"}]
    assert compile_native_hmmer_job(job)["argv"][compile_native_hmmer_job(job)["argv"].index("--chkhmm")+1] == "checkpoints/model"
    job["outputs"][0]["relative_path"] = "checkpoints/model-1.hmm"
    with pytest.raises(ValueError, match="checkpoint_path_overlap"):
        validate_native_hmmer_job(job)


def test_wrapper_cannot_replace_job_or_environment():
    request = requested_job_from_native(job_for())
    request["argv"][-1] = "/another/database"
    with pytest.raises(ValueError, match="compiler_mismatch"):
        validate_native_hmmer_requested_job(request)
    request = requested_job_from_native(job_for())
    request["environment"]["HMMER_NCPU"] = "99"
    with pytest.raises(ValueError, match="compiler_mismatch"):
        validate_native_hmmer_requested_job(request)


@pytest.mark.parametrize("value", [float("nan"), (1, 2), {1: "coerced"}])
def test_nonfinite_or_non_json_metadata_rejects(value):
    job = job_for()
    job["metadata"] = {"unsupported": value}
    with pytest.raises(ValueError, match="finite_json"):
        validate_native_hmmer_job(job)


def test_bound_catalog_is_explicit_mode_restricted_and_has_four_field_projection():
    software = job_for()["software"]
    bindings = [{"program": "nhmmer", "mode": mode, "software": software} for mode in ("sequence", "profile")]
    contracts = native_hmmer_tool_contracts(bindings, resource_kind="hpc", resource_id="chosen-hpc")
    assert len(contracts) == 1
    assert contracts[0]["resources"] == "hpc"
    assert contracts[0]["invocation_route"] == {"kind": "commission", "routes": [{"entry_role": "launch", "resource_id": "chosen-hpc", "resource_role": "launch_hpc"}]}
    job = job_for("nhmmer", "profile")
    job["software"] = software
    validator = Draft202012Validator(contracts[0]["input_schema"])
    assert validator.is_valid(requested_job_from_native(job))
    job = job_for("nhmmer", "alignment")
    job["software"] = software
    assert not validator.is_valid(requested_job_from_native(job))
    public = native_hmmer_tool_information(bindings, resource_kind="hpc", resource_id="chosen-hpc")
    assert set(public[0]) == {"name", "description", "resources", "instructions"}
    assert public[0]["resources"] == "hpc"
    assert native_hmmer_tool_contracts([], resource_kind="local", resource_id="local") == []
    with pytest.raises(ValueError, match="duplicate_program_mode"):
        validate_native_hmmer_bindings(bindings + [bindings[0]])
    bindings[0]["software"]["engine_version"] = ""
    with pytest.raises(ValueError, match="invalid_configured_software"):
        validate_native_hmmer_bindings(bindings)
