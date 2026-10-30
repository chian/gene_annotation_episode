"""Pure G2 record tests. Every native-looking record here is synthetic."""
from copy import deepcopy
from importlib import import_module
import builtins
import io
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import native_genomic_overlap_contracts as contracts
from gene_annotation_episode.genomic_overlap_contracts import genomic_overlap_schema

f = import_module("verification.tool_graders_genomic_overlap_execution_contracts_2026-10-27_426.fixtures")


def test_exact_frozen_three_set_plan_batch_and_pair_records():
    plan, batch = f.fixture()
    job = plan["requested_job"]["native_genomic_overlap"]
    assert contracts.validate_genomic_overlap_job(job) == job
    assert contracts.validate_genomic_overlap_run_plan(plan) == plan
    assert contracts.validate_genomic_overlap_batch(batch, plan=plan) == batch
    assert contracts.genomic_overlap_output_files(job["request"]) == job["outputs"]
    assert contracts.genomic_overlap_driver_argv(plan) == batch["driver_argv"]
    assert contracts.genomic_overlap_environment(job, attempt_directory=plan["attempt_directory"]) == batch["realized_environment"]
    for pair in batch["pairs"]:
        assert contracts.validate_genomic_overlap_pair_manifest(pair["manifest"], plan=plan,
            comparison=pair["comparison"], set_outputs=batch["sets"]) == pair["manifest"]
    assert len(job["outputs"]) == 26
    assert len(batch["files"]) == 25
    assert all("artifact_ref" not in json.dumps(row["manifest"]) for row in batch["pairs"])


def test_exact_two_set_outputs_and_nominal_compilation():
    job = f.two_set_job()
    assert len(job["outputs"]) == 16
    assert contracts.genomic_overlap_output_files(job["request"]) == job["outputs"]
    compiled = contracts.compile_genomic_overlap_job(job)
    assert set(compiled) == {"argv", "environment", "outputs"}
    assert compiled["argv"] == [job["software"]["python_executable"], "-B", "-m",
        "gene_annotation_episode.native_genomic_overlap_driver", "genomic-overlap-plan.json"]
    requested = contracts.requested_job_from_genomic_overlap(job)
    assert contracts.validate_genomic_overlap_requested_job(requested) == requested
    assert set(requested) == {"argv", "environment", "native_genomic_overlap"}


def test_all_seventeen_frozen_schema_definitions_and_unchanged_g1_records():
    frozen = json.loads((f.PACKET / "DATA_CONTRACT.json").read_text())
    science = genomic_overlap_schema("Request")["$defs"]
    assert len(frozen["$defs"]) == 17
    for name, expected in frozen["$defs"].items():
        document = contracts.genomic_overlap_execution_schema(name)
        Draft202012Validator.check_schema(document)
        definitions = document["allOf"][0]["$defs"]
        normalized = json.loads(json.dumps(expected).replace(
            "urn:gene-annotation:planning:genomic-overlap-contract-418:v1#/", "#/"))
        assert definitions[name] == normalized
        for key in definitions.keys() - frozen["$defs"].keys():
            assert definitions[key] == science[key]
    with pytest.raises(ValueError, match="unknown_execution_record"):
        contracts.genomic_overlap_execution_schema("__import__")
    with pytest.raises(ValueError, match="binding_mismatch"):
        contracts.genomic_overlap_execution_schema("RunPlan", bindings=[])


@pytest.mark.parametrize("mutation", [
    lambda j: j.update(extra=1),
    lambda j: j["request"]["region_sets"][0]["source"]["file"].update(size_bytes=True),
    lambda j: j["request"]["region_sets"][0]["source"]["file"].update(size_bytes=46.0),
    lambda j: j["request"]["region_sets"][0]["source"]["file"].update(size_bytes=float("nan")),
    lambda j: j["request"]["comparisons"][0].update(ordinal=False),
    lambda j: j["request"]["comparisons"].reverse(),
    lambda j: j["request"]["comparisons"].pop(),
    lambda j: j["request"]["comparisons"][0].update(b_set_key="A"),
    lambda j: j["request"]["comparisons"][1].update(comparison_key="comparison_0"),
    lambda j: j["request"]["region_sets"][1].update(set_key="A"),
    lambda j: j["request"]["region_sets"][0]["source"].update(kind="coordinate_rows_artifact"),
    lambda j: j["request"]["region_sets"][0]["source"]["file"].update(format="coordinate_rows_v1"),
    lambda j: j["inputs"].reverse(),
    lambda j: j["inputs"][1].update(path=j["inputs"][0]["path"]),
    lambda j: j["inputs"][0].update(path="/tmp/../foreign"),
    lambda j: j["inputs"][0].update(path="//foreign/source"),
    lambda j: j["outputs"].reverse(),
    lambda j: j["outputs"][0].update(relative_path="arbitrary.log"),
    lambda j: j["software"]["implementation_files"].pop(),
    lambda j: j["software"]["implementation_files"].append(deepcopy(j["software"]["implementation_files"][0])),
    lambda j: j["software"].update(bedtools_executable="bedtools"),
])
def test_job_rejects_shapes_formats_paths_and_reordered_joins(mutation):
    job = f.job()
    mutation(job)
    with pytest.raises(ValueError):
        contracts.validate_genomic_overlap_job(job)


@pytest.mark.parametrize("environment", [{}, {"LC_ALL": "POSIX"}, {"LC_ALL": "C", "HOME": "/tmp"},
    {"LC_ALL": "C", "PYTHONPATH": "/elsewhere"}, {"LC_ALL": "C", "PIP_CACHE_DIR": "/elsewhere"},
    {"LC_ALL": "C", "TMPDIR": "/elsewhere"}, {"LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "0"},
    {"LC_ALL": "C", "EXTRA": "\0"}, {"LC_ALL": "C", "EXTRA": 1}])
def test_selected_environment_cannot_redirect_fixed_worker_paths(environment):
    job = f.job()
    job["environment"] = environment
    with pytest.raises(ValueError):
        contracts.validate_genomic_overlap_job(job)


@pytest.mark.parametrize("prefix", ["bundle.json", "stdout.log", "tmp", "cache", "../escape", "a/b", "native.json"])
def test_output_prefix_cannot_alias_controls_or_other_outputs(prefix):
    request = f.job()["request"]
    request["output_prefix"] = prefix
    with pytest.raises(ValueError):
        contracts.genomic_overlap_output_files(request)


def test_same_original_identity_may_have_separate_set_occurrences():
    job = f.job()
    job["inputs"][1]["path"] = job["inputs"][0]["path"]
    job["request"]["region_sets"][1]["source"]["file"] = deepcopy(job["request"]["region_sets"][0]["source"]["file"])
    assert contracts.validate_genomic_overlap_job(job) == job
    job["request"]["region_sets"][1]["source"]["file"]["artifact_ref"] = "different:artifact"
    with pytest.raises(ValueError, match="input_identity_mismatch"):
        contracts.validate_genomic_overlap_job(job)


@pytest.mark.parametrize("mutation", [
    lambda p: p["identity"].update(run_id="foreign"),
    lambda p: p["identity"].update(episode_id="foreign"),
    lambda p: p["identity"].update(operation_key="foreign"),
    lambda p: p["identity"].update(requested_job_sha256="0" * 64),
    lambda p: p.update(attempt_directory=p["attempt_directory"] + "-foreign"),
    lambda p: p["policy"].update(memory_bytes=21474836480.0),
    lambda p: p["policy"].update(wall_seconds=60),
    lambda p: p["requested_job"]["argv"].append("--extra"),
    lambda p: p["requested_job"]["argv"].__setitem__(-1, "/tmp/genomic-overlap-plan.json"),
    lambda p: p["requested_job"]["environment"].update(EXTRA="changed"),
])
def test_original_plan_identity_nominal_request_and_allocation(mutation):
    plan, _ = f.fixture()
    mutation(plan)
    with pytest.raises(ValueError):
        contracts.validate_genomic_overlap_run_plan(plan)


def test_input_cannot_be_inside_the_attempt_even_after_rehashing_request():
    plan, batch = f.fixture()
    plan["requested_job"]["native_genomic_overlap"]["inputs"][0]["path"] = plan["attempt_directory"] + "/original"
    f.rehash(plan, batch)
    with pytest.raises(ValueError, match="invalid_path"):
        contracts.validate_genomic_overlap_run_plan(plan)


@pytest.mark.parametrize("kind", ["empty", "invalid", "missing", "mismatch"])
def test_uninvoked_c_cases_preserve_exact_ab_without_fabricated_native_facts(kind):
    plan, batch = f.c_case(kind)
    assert contracts.validate_genomic_overlap_batch(batch, plan=plan) == batch
    assert batch["pairs"][0] == f.fixture()[1]["pairs"][0]
    for row in batch["pairs"][1:]:
        manifest = row["manifest"]
        if manifest is not None:
            assert manifest["outcome"] == "not_executed"
            assert manifest["software"] is manifest["returncode"] is manifest["started_at"] is manifest["finished_at"] is None
            assert manifest["files"] == manifest["realized_argv"] == []
        else:
            assert row["manifest_file_key"] is None
    assert batch["batch_status"] == ("complete" if kind == "empty" else "partial")


@pytest.mark.parametrize("implementation", [False, True])
def test_unavailable_software_and_code_mismatch_keep_declared_origins_without_invocation(implementation):
    plan, batch = f.no_software(implementation=implementation)
    assert contracts.validate_genomic_overlap_batch(batch, plan=plan) == batch
    assert all(row["manifest"] is None for row in batch["pairs"])
    assert all(row["input_state"] == "verified" for row in batch["sets"])
    assert batch["software_verification"]["version_probe"] is None


def test_unverified_interpreter_cannot_claim_complete_g1_parsing():
    plan, batch = f.no_software()
    batch["software_verification"]["python_observed"]["sha256"] = "f" * 64
    batch["failures"][0].update(code="software_identity_mismatch", field_path="/software/python_sha256")
    with pytest.raises(ValueError, match="software_binding"):
        contracts.validate_genomic_overlap_batch(batch, plan=plan)


def test_canonical_seal_failure_preserves_original_and_parsed_set():
    plan, batch = f.fixture()
    index = f.files(batch)
    f.absent(index["s2:canonical"])
    batch["failures"] = [f.failure("seal_failed", stage="seal", set_key="C", file_key="s2:canonical")]
    batch["sets"][2]["failure_indices"] = [0]
    for row in batch["pairs"][1:]:
        ordinal = row["comparison"]["ordinal"]
        for suffix in ("manifest", "stdout", "stderr"):
            f.absent(index[f"p{ordinal}:" + suffix])
        row.update(disposition="native_unavailable", manifest=None, manifest_file_key=None, failure_indices=[0])
    batch["batch_status"] = "partial"
    assert contracts.validate_genomic_overlap_batch(batch, plan=plan) == batch
    assert batch["pairs"][0] == f.fixture()[1]["pairs"][0]


def test_invoked_zero_byte_output_is_present_and_distinct_from_analytic_empty():
    plan, batch = f.fixture()
    index = f.files(batch)
    f.supplied(index["p0:stdout"], b"")
    batch["pairs"][0]["manifest"]["files"][2]["declaration"] = deepcopy(index["p0:stdout"])
    f.reseal(batch)
    assert contracts.validate_genomic_overlap_batch(batch, plan=plan) == batch
    assert batch["pairs"][0]["disposition"] == "native_succeeded"
    f.absent(index["p0:stdout"])
    batch["pairs"][0]["manifest"]["files"][2]["declaration"] = deepcopy(index["p0:stdout"])
    f.reseal(batch)
    with pytest.raises(ValueError, match="pair_files"):
        contracts.validate_genomic_overlap_batch(batch, plan=plan)


def test_all_analytic_pairs_retain_no_version_probe_or_native_output():
    from gene_annotation_episode.genomic_overlap_inputs import parse_region_set
    plan, batch = f.c_case("empty")
    index = f.files(batch)
    spec = plan["requested_job"]["native_genomic_overlap"]["request"]["region_sets"][0]
    f.supplied(index["s0:original"], b"")
    spec["source"]["file"].update(sha256=index["s0:original"]["sha256"], size_bytes=0)
    parsed = parse_region_set(b"", specification=spec, set_position=0)
    f.supplied(index["s0:parsed"], f.canonical(parsed) + b"\n")
    f.supplied(index["s0:canonical"], b"")
    batch["sets"][0]["measured_fingerprint"].update(sha256=index["s0:original"]["sha256"], size_bytes=0)
    for row in batch["pairs"]:
        ordinal = row["comparison"]["ordinal"]
        if row["comparison"]["a_set_key"] == "A":
            row["manifest"]["input_fingerprints"][0] = deepcopy(batch["sets"][0]["measured_fingerprint"])
        row["manifest"].update(derivation="validated_empty_input", outcome="not_executed", software=None,
            returncode=None, started_at=None, finished_at=None, realized_argv=[], environment={}, files=[])
        row["disposition"] = "analytic_empty"
        for suffix in ("stdout", "stderr"):
            f.absent(index[f"p{ordinal}:" + suffix])
    for name in ("version_stdout", "version_stderr"):
        f.absent(index[name])
    batch["software_verification"].update(state="not_needed", version_probe=None, bedtools_observed=None)
    f.rehash(plan, batch)
    assert contracts.validate_genomic_overlap_batch(batch, plan=plan) == batch
    assert all(row["manifest"]["realized_argv"] == [] for row in batch["pairs"])


@pytest.mark.parametrize("mutation", [
    lambda b: b["pairs"].reverse(),
    lambda b: b["pairs"].pop(),
    lambda b: b["sets"].reverse(),
    lambda b: b["files"].reverse(),
    lambda b: b["files"][0]["declaration"].update(sha256=None),
    lambda b: b["files"][0]["declaration"].update(size_bytes=True),
    lambda b: b["files"][0]["declaration"].update(relative_path="unexpected.log"),
    lambda b: b.update(batch_status="partial"),
    lambda b: b.update(plan_sha256="0" * 64),
    lambda b: b["identity"].update(origin_episode_id="foreign"),
    lambda b: b["sets"][0]["measured_fingerprint"].update(sha256="0" * 64),
    lambda b: b["pairs"][0]["manifest"]["input_fingerprints"].reverse(),
    lambda b: b["pairs"][0]["manifest"]["files"].reverse(),
    lambda b: b["pairs"][0]["manifest"]["realized_argv"].append("-s"),
    lambda b: b["pairs"][0]["manifest"].update(returncode=1),
    lambda b: b["pairs"][0]["manifest"].update(returncode=True),
    lambda b: b["pairs"][0]["manifest"].update(writer_closed=False),
    lambda b: b["pairs"][0]["manifest"]["software"].update(observed_version="wrong"),
    lambda b: b["pairs"][0]["manifest"].update(finished_at="1999-01-01T00:00:00Z"),
    lambda b: b["software_verification"]["version_probe"]["environment"].update(TMP="/unselected"),
    lambda b: b["software_verification"].update(state="not_needed"),
])
def test_batch_rejects_original_identity_outcome_population_and_file_join_conflicts(mutation):
    plan, batch = f.fixture()
    mutation(batch)
    with pytest.raises(ValueError):
        contracts.validate_genomic_overlap_batch(batch, plan=plan)


def test_incorrect_empty_claim_is_rejected_by_canonical_size_and_invalid_input_by_extent():
    plan, batch = f.c_case("empty")
    f.supplied(f.files(batch)["s2:canonical"], b"chr1\t10\t20\ts2_r0\n")
    with pytest.raises(ValueError, match="empty_input_binding"):
        contracts.validate_genomic_overlap_batch(batch, plan=plan)
    plan, batch = f.c_case("invalid")
    batch["pairs"][1]["manifest"]["derivation"] = "validated_empty_input"
    with pytest.raises(ValueError, match="empty_input_binding"):
        contracts.validate_genomic_overlap_pair_manifest(batch["pairs"][1]["manifest"], plan=plan,
            comparison=batch["pairs"][1]["comparison"], set_outputs=batch["sets"])


@pytest.mark.parametrize("mutation", [
    lambda b: b["pairs"][1].update(failure_indices=[99]),
    lambda b: b["pairs"][1].update(failure_indices=[0, 0]),
    lambda b: b["failures"][0].update(set_key="foreign"),
    lambda b: b["failures"][0].update(comparison_key="comparison_2"),
    lambda b: b["failures"][0].update(file_key="p0:stdout"),
    lambda b: b["sets"][2].update(failure_indices=[]),
])
def test_located_failure_indices_do_not_leak_between_unrelated_pairs(mutation):
    plan, batch = f.c_case("missing")
    mutation(batch)
    with pytest.raises(ValueError):
        contracts.validate_genomic_overlap_batch(batch, plan=plan)


def test_nonzero_pair_keeps_partial_files_and_later_independent_pairs():
    plan, batch = f.fixture()
    pair = batch["pairs"][0]
    pair.update(disposition="native_failed", failure_indices=[0])
    pair["manifest"].update(outcome="failed", returncode=9)
    batch["failures"] = [f.failure("native_nonzero_exit", stage="native", comparison_key="comparison_0")]
    batch["batch_status"] = "partial"
    f.reseal(batch)
    assert contracts.validate_genomic_overlap_batch(batch, plan=plan) == batch
    assert [p["disposition"] for p in batch["pairs"][1:]] == ["native_succeeded", "native_succeeded"]


def test_all_returned_records_are_detached():
    plan, batch = f.fixture()
    returned = contracts.validate_genomic_overlap_batch(batch, plan=plan)
    returned["sets"][0]["set_key"] = "mutated"
    assert batch["sets"][0]["set_key"] == "A"
    schema = contracts.genomic_overlap_execution_schema("RequestedJob")
    schema["allOf"][0]["$defs"]["NativeJob"]["properties"].clear()
    assert contracts.genomic_overlap_execution_schema("RequestedJob")["allOf"][0]["$defs"]["NativeJob"]["properties"]
    binds = [f.binding()]
    contracts.validate_genomic_overlap_bindings(binds)[0]["software"]["implementation_files"].clear()
    assert len(binds[0]["software"]["implementation_files"]) == 4


def test_pure_ports_do_not_open_files_probe_launch_or_connect(monkeypatch):
    plan, batch = f.fixture()
    job = plan["requested_job"]["native_genomic_overlap"]
    binding = f.binding()
    def forbidden(*args, **kwargs):
        raise AssertionError("pure validation must not acquire, launch or inspect files")
    with monkeypatch.context() as guard:
        for target, name in ((builtins, "open"), (io, "open"), (os, "open"), (Path, "stat"),
            (Path, "read_bytes"), (subprocess, "run"), (subprocess, "Popen"), (socket, "socket")):
            guard.setattr(target, name, forbidden)
        assert contracts.validate_genomic_overlap_batch(batch, plan=plan) == batch
        assert contracts.validate_genomic_overlap_bindings([binding]) == [binding]
        assert contracts.compile_genomic_overlap_job(job)["outputs"] == job["outputs"]
        assert contracts.genomic_overlap_execution_schema("RequestedJob", bindings=[binding])


def test_exact_three_pair_numerical_meanings_from_supplied_tables_without_execution():
    result = f.numerical_example()
    pairs = result["components"]["pairs"]
    assert [row["unfiltered"]["native_pair_count"] for row in pairs] == [2, 1, 1]
    assert [row["unfiltered"]["pairwise_overlap_bp_sum"] for row in pairs] == [8, 5, 2]
    assert [row["unfiltered"]["intersection_union_bp"] for row in pairs] == [5, 5, 2]
    assert [row["unfiltered"]["combined_union_bp"] for row in pairs] == [15, 20, 13]
    assert [row["unfiltered"]["jaccard_bp"]["value"] for row in pairs] == [1 / 3, 1 / 4, 2 / 13]
    assert [row["set_key"] for row in result["sheet"]["sets"]] == ["A", "B", "C"]
    assert result["native_execution_claim"] is False
