"""Actual producer commands use existing local_jobs with the user's allocation."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

import pytest

from gene_annotation_episode import native_hmmer_preparation_driver as driver
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
from gene_annotation_episode.native_infernal_contracts import native_infernal_digest
from gene_annotation_episode.native_hmmer_preparation_contracts import requested_job_from_hmmer_preparation
from test_native_hmmer_preparation_contracts import BIN, CASES, EVIDENCE, FM_CONTRACT, NATIVE, ROOT, digest, job, operand


POLICY = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)


def make_plan(tmp_path, selected=None):
    request = requested_job_from_hmmer_preparation(job() if selected is None else selected)
    key = "selected-command"
    return {"version": driver.PLAN_VERSION, "identity": {"run_id": "producer267-test", "episode_id": "selected-local-child",
        "resource_id": "local", "execution_id": str(tmp_path / "native.json"), "operation_key": key,
        "attempt_id": native_infernal_digest(key), "requested_job_sha256": native_infernal_digest(request)},
        "requested_job": request, "attempt_directory": str(tmp_path / "hmmer-preparation-attempt"), "policy": POLICY.to_dict()}


def reseal(plan):
    plan["requested_job"] = requested_job_from_hmmer_preparation(plan["requested_job"]["native_hmmer_preparation"])
    plan["identity"]["requested_job_sha256"] = native_infernal_digest(plan["requested_job"])
    return plan


def run_actual(tmp_path, selected):
    plan = make_plan(tmp_path, selected)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan, indent=2) + "\n")
    result = run_local_job([sys.executable, "-m", "gene_annotation_episode.native_hmmer_preparation_driver", str(path)],
        cwd=tmp_path, policy=POLICY, env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
    (tmp_path / "native-lifecycle-receipt.json").write_text(json.dumps({"returncode": result.returncode,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path), "metadata": result.metadata}, indent=2) + "\n")
    assert result.metadata["verified_cgroup"]["memory_max"] == POLICY.memory_bytes
    assert result.metadata["verified_cgroup"]["runtime_max"] == "infinity"
    attempt = Path(plan["attempt_directory"])
    assert (attempt / "bundle.json").is_file(), result.stderr_path.read_text()
    bundle = driver.validate_preparation_bundle_files(json.loads((attempt / "bundle.json").read_bytes()), attempt)
    return plan, bundle


def output_bytes(plan, bundle, role):
    row = next(r for r in bundle["artifacts"] if r["role"] == role)
    return (Path(plan["attempt_directory"]) / row["relative_path"]).read_bytes()


@pytest.mark.parametrize("program,mode", CASES)
def test_actual_all_selected_modes_and_replay(tmp_path, monkeypatch, program, mode):
    selected = job(program, mode)
    original = {r["path"]: digest(Path(r["path"])) for r in selected["operands"]}
    plan, bundle = run_actual(tmp_path, selected)
    assert bundle["returncode"] == 0 and bundle["failures"] == [], bundle["failures"]
    assert {path: digest(Path(path)) for path in original} == original
    assert all(r["staged_sha256"] == r["expected_sha256"] == r["final_sha256"] for r in bundle["inputs"])
    assert all(r["initial_sha256"] == r["source_sha256"] == r["final_sha256"] for r in bundle["working_copies"])
    assert len(bundle["artifacts"]) == len(selected["outputs"])
    assert bundle["native_abi"]["float_format"] == "ieee754_binary64"
    if program == "hmmconvert":
        occurrences = [r for r in bundle["artifacts"] if r["role"] in {"stdout", "converted_models"}]
        assert len(occurrences) == 2
        assert occurrences[0]["relative_path"] == occurrences[1]["relative_path"]
        assert occurrences[0]["sha256"] == occurrences[1]["sha256"]
        if mode == "binary":
            assert output_bytes(plan, bundle, "converted_models")[:4] == bytes.fromhex("baedede8")
    if program == "hmmsim":
        assert len(output_bytes(plan, bundle, "scores")) == 8000
        assert bundle["operation"]["settings"]["--fast"] is False
        assert bundle["operation"]["settings"]["--tlinear"] is False
    if (program, mode) == ("hmmemit", "consensus_simple"):
        assert output_bytes(plan, bundle, "generated_sequences").splitlines()[1] == b"ACDEFGHIKLMN"
    monkeypatch.setattr(driver.subprocess, "run", lambda *a, **k: pytest.fail("replay executed native work"))
    assert driver.run_native_hmmer_preparation(plan) == bundle
    relocated = tmp_path / "complete-retained-copy"
    shutil.copytree(plan["attempt_directory"], relocated)
    assert driver.validate_preparation_bundle_files(bundle, relocated) == bundle


@pytest.mark.parametrize("revision", list("abcdef"))
def test_actual_conversion_revision_and_binary_input(tmp_path, revision):
    selected = job("hmmconvert", "ascii", ["--outfmt", "3/" + revision])
    selected["operands"] = [operand("models", NATIVE / "hmmconvert_binary/stdout.log", "hmmer_binary")]
    plan, bundle = run_actual(tmp_path, selected)
    assert not bundle["failures"]
    assert output_bytes(plan, bundle, "converted_models").startswith(("HMMER3/" + revision).encode())
    assert bundle["operation"]["settings"]["--outfmt"] == "3/" + revision


@pytest.mark.parametrize("style,total", [("--local", 126), ("--unilocal", 137), ("--glocal", 159), ("--uniglocal", 148)])
def test_actual_profile_styles_preserve_generated_bytes(tmp_path, style, total):
    selected = job("hmmemit", "sample_profile")
    selected["options"].append(style)
    plan, bundle = run_actual(tmp_path, selected)
    raw = output_bytes(plan, bundle, "generated_sequences")
    assert sum(len(line) for line in raw.splitlines() if not line.startswith(b">")) == total
    assert bundle["operation"]["settings"][style] is True


@pytest.mark.parametrize("mode", ["viterbi", "msv", "forward", "hybrid"])
@pytest.mark.parametrize("style", ["--fs", "--sw", "--ls", "--s"])
def test_actual_simulation_styles_and_auxiliary_artifacts(tmp_path, mode, style):
    selected = job("hmmsim", mode)
    selected["options"] += [style, "--tmin", ".1", "--tmax", ".1", "--pthresh", ".1"]
    selected["outputs"] += [{"role": role, "format": fmt, "relative_path": "outputs/" + role}
        for role, fmt in (("filter", "hmmsim_filter"), ("survival", "hmmsim_xy"), ("expected_counts", "hmmsim_xy"))]
    if mode == "viterbi":
        selected["options"].append("-a")
        selected["outputs"].append({"role": "alignments", "format": "hmmsim_alignments", "relative_path": "outputs/alignments"})
    plan, bundle = run_actual(tmp_path, selected)
    assert not bundle["failures"]
    assert len(output_bytes(plan, bundle, "scores")) == 8000
    if mode == "forward":
        assert output_bytes(plan, bundle, "filter") == b""  # observed native defect, never a fabricated zero count
    if (mode, style) == ("viterbi", "--fs"):
        values = struct.unpack("=1000d", output_bytes(plan, bundle, "scores"))
        assert sum(values) / len(values) == pytest.approx(-5.619071923450204)
        assert b"368" in output_bytes(plan, bundle, "filter")
        assert len(output_bytes(plan, bundle, "alignments").splitlines()) == 1000


@pytest.mark.parametrize("mode", ["viterbi", "msv", "forward"])
def test_actual_supported_fast_simulation(tmp_path, mode):
    selected = job("hmmsim", mode)
    selected["options"].append("--fast")
    plan, bundle = run_actual(tmp_path, selected)
    assert not bundle["failures"] and len(output_bytes(plan, bundle, "scores")) == 8000


def test_actual_press_index_private_bundle_and_explicit_ssi_partial_fetch(tmp_path):
    indexed = tmp_path / "index"
    indexed.mkdir()
    plan, bundle = run_actual(indexed, job("hmmfetch", "index"))
    assert not bundle["failures"]
    attempt = Path(plan["attempt_directory"])
    model = attempt / bundle["working_copies"][0]["relative_path"]
    selected = job("hmmfetch", "key_file")
    selected["operands"] = [operand("models", model, "hmmer3_ascii"), operand("ssi", Path(str(model) + ".ssi"), "hmmer_ssi"),
        operand("keys", EVIDENCE / "inputs/keys_missing.txt", "key_file")]
    fetched = tmp_path / "fetch"
    fetched.mkdir()
    fetch_plan, fetch = run_actual(fetched, selected)
    assert fetch["returncode"] == 1
    assert output_bytes(fetch_plan, fetch, "fetched_models").count(b"HMMER3/f") == 1
    assert [r["relative_path"] for r in fetch["inputs"][:2]] == ["inputs/models.hmm", "inputs/models.hmm.ssi"]
    assert any(f["code"].endswith("nonzero_returncode") for f in fetch["failures"])


def test_actual_conversion_failure_preserves_complete_first_native_model(tmp_path):
    selected = job()
    source = tmp_path / "partly-malformed.hmm"
    first = Path(selected["operands"][0]["path"]).read_bytes()
    # A bare truncated header is treated as EOF by this native reader. A full
    # second record with an invalid alphabet actually reaches its error path.
    source.write_bytes(first + first.replace(b"ALPH  amino", b"ALPH  invalid"))
    selected["operands"] = [operand("models", source, "hmmer3_ascii")]
    plan, bundle = run_actual(tmp_path, selected)
    assert bundle["returncode"] == 1
    assert output_bytes(plan, bundle, "converted_models").count(b"HMMER3/f") == 1
    assert output_bytes(plan, bundle, "converted_models").endswith(b"//\n")
    assert driver.run_native_hmmer_preparation(plan) == bundle


@pytest.mark.parametrize("options", [["--hand"], ["--fast", "--wnone"], ["--fast", "--wgiven"], ["--fast"], ["--fast", "--wpb"]])
def test_actual_alimask_safe_established_maps(tmp_path, options):
    selected = job("alimask", "alignment_to_model", ["--amino", *options, "--ali2model", "2-4"])
    plan, bundle = run_actual(tmp_path, selected)
    assert not bundle["failures"]
    assert b"2..4" in output_bytes(plan, bundle, "stdout")


@pytest.mark.parametrize("weight", ["--wnone", "--wgiven", "--wpb"])
def test_actual_gappy_fragment_map_matches_native_forward_map(tmp_path, weight):
    source = tmp_path / "gappy.sto"
    source.write_text("# STOCKHOLM 1.0\n#=GS s1 WT 0.7\n#=GS s2 WT 2.3\n#=GS s3 WT 0.2\ns1 --ACGT-A--\ns2 --A-GTTC--\ns3 -----TTC--\n#=GC RF ..xxxxxx..\n//\n")
    selected = job("alimask", "model_to_alignment", ["--dna", "--fast", weight, "--model2ali", "1-1", "--symfrac", ".65", "--fragthresh", ".6"])
    selected["operands"] = [operand("alignment", source, "stockholm")]
    msa, problem = driver._stockholm_for_map(source.read_bytes())
    assert problem is None
    mapping, problem = driver._alimask_map(msa, {"--dna": True, "--fast": True, weight: True, "--symfrac": .65, "--fragthresh": .6})
    assert problem is None and mapping
    selected["options"][selected["options"].index("--model2ali") + 1] = ",".join(f"{i}-{i}" for i in range(1, len(mapping)+1))
    plan, bundle = run_actual(tmp_path, selected)
    assert not bundle["failures"]
    raw = output_bytes(plan, bundle, "stdout").decode("ascii")
    import re
    actual = [int(m.group(1)) for m in re.finditer(r"->\s+(\d+)\.\.", raw)]
    assert actual == mapping


def test_actual_alimask_reads_first_alignment_and_retains_all_supplied_bytes(tmp_path):
    selected = job("alimask", "alignment_to_model")
    source = tmp_path / "two-alignments.sto"
    first = Path(selected["operands"][0]["path"]).read_bytes()
    raw = first + first + b"\xffignored-after-two-alignments\n"
    source.write_bytes(raw)
    selected["operands"] = [operand("alignment", source, "stockholm")]
    plan, bundle = run_actual(tmp_path, selected)
    assert not bundle["failures"]
    assert output_bytes(plan, bundle, "stdout").count(b"2..4") == 2
    assert (Path(plan["attempt_directory"]) / "inputs/alignment/0").read_bytes() == raw


@pytest.mark.parametrize("options,reason", [
    (["--hand", "--ali2model", "13-14"], "unsafe_alimask_range"),
    (["--fast", "--wgsc", "--ali2model", "2-4"], "unsupported_alimask_model_map"),
    (["--fast", "--wblosum", "--ali2model", "2-4"], "unsupported_alimask_model_map"),
    (["--fast", "--wnone", "--ali2model", "13-14"], "unsafe_alimask_range"),
])
def test_unsafe_or_unestablished_map_never_invokes_native(tmp_path, monkeypatch, options, reason):
    plan = make_plan(tmp_path, job("alimask", "alignment_to_model", ["--amino", *options]))
    monkeypatch.setattr(driver.subprocess, "run", lambda *a, **k: pytest.fail("unsafe native invocation"))
    bundle = driver.run_native_hmmer_preparation(plan)
    assert bundle["returncode"] is None
    assert any(f["code"].endswith(reason) for f in bundle["failures"])
    assert driver.run_native_hmmer_preparation(plan) == bundle


@pytest.mark.parametrize("query", [b"", b"\n", b"ACGT\r\n", b">ACGT\n", b"ACGN\n", b"ACGU\n", b"A"*255+b"\n", b"ACGT"])
def test_invalid_query_bytes_are_not_normalized_or_executed(tmp_path, monkeypatch, query):
    selected = job("hmmerfm-exactmatch", "locations")
    path = tmp_path / "queries"
    path.write_bytes(query)
    selected["operands"][0] = operand("queries", path, "literal_query_lines")
    plan = make_plan(tmp_path, selected)
    monkeypatch.setattr(driver.subprocess, "run", lambda *a, **k: pytest.fail("unsafe native invocation"))
    bundle = driver.run_native_hmmer_preparation(plan)
    assert bundle["returncode"] is None
    assert any(f["code"].endswith("invalid_exactmatch_queries") for f in bundle["failures"])


@pytest.mark.parametrize("mutation,expected", [
    ("truncated", "truncated_array"),
    ("sa_in_range", "native_sa_invalid"),
    ("counter_in_range", "native_counter_invalid"),
    ("bwt", "native_bwt_invalid"),
    ("segment", "native_segment_bounds"),
    ("reader_spacing", "native_reader_header_incompatible"),
    ("amino", "dna_reader_incompatible"),
])
def test_supplied_fm_structure_is_checked_before_native_reader(tmp_path, monkeypatch, mutation, expected):
    from gene_annotation_episode.hmmer_fm_data import extract_hmmer_fm_database
    selected = job("hmmerfm-exactmatch", "locations")
    original = Path(selected["operands"][1]["path"])
    raw = bytearray(original.read_bytes())
    occurrence = {"occurrence_id": "fixture:fm", "direction": "input", "role": "fm_database", "ordinal": 0,
        "artifact_ref": "fixture:fm", "sha256": digest(original), "size_bytes": len(raw), "completeness": "complete"}
    decoded = extract_hmmer_fm_database(bytes(raw), occurrence=occurrence, producer_contract=FM_CONTRACT)
    arrays = decoded["blocks"][0]["arrays"]
    if mutation == "truncated":
        del raw[-5:]
    elif mutation == "sa_in_range":
        position = arrays["SA"]["locator"]["byte_start"] + 4
        struct.pack_into("<I", raw, position, (arrays["SA"]["values"][1] + 1) % 28)
    elif mutation == "counter_in_range":
        position = arrays["counters_b"]["locator"]["byte_start"] + 8
        struct.pack_into("<H", raw, position, arrays["counters_b"]["values"][1][0] + 1)
    elif mutation == "bwt":
        raw[arrays["BWT"]["locator"]["byte_start"]] ^= 1
    elif mutation == "segment":
        struct.pack_into("<Q", raw, decoded["segments"][0]["locator"]["byte_start"] + 4, 0)
    elif mutation == "reader_spacing":
        struct.pack_into("<I", raw, 12, 32)
    else:
        raw = bytearray((NATIVE / "makehmmerdb_protein/index.fm").read_bytes())
    supplied = tmp_path / "supplied.fm"
    supplied.write_bytes(raw)
    selected["operands"][1] = operand("fm_database", supplied, "hmmer_fm_3_4")
    monkeypatch.setattr(driver.subprocess, "run", lambda *a, **k: pytest.fail("unsafe imported FM native invocation"))
    plan = make_plan(tmp_path, selected)
    bundle = driver.run_native_hmmer_preparation(plan)
    assert bundle["returncode"] is None
    failures = [f for f in bundle["failures"] if f["code"].endswith("invalid_fm_database")]
    assert failures and expected in failures[0]["detail"]["issue_codes"]
    assert driver.run_native_hmmer_preparation(plan) == bundle
    assert (Path(plan["attempt_directory"]) / "inputs/fm_database/0").read_bytes() == raw


@pytest.mark.parametrize("fault", ["byte_order", "source_binding"])
def test_imported_fm_contract_and_source_association_cannot_be_guessed(tmp_path, monkeypatch, fault):
    selected = job("hmmerfm-exactmatch", "count_only")
    if fault == "byte_order":
        selected["input_metadata"]["producer_contract"]["byte_order"] = "big"
        expected = "incompatible_fm_abi"
    else:
        selected["input_metadata"]["source_binding"] = {"database_occurrence_id": "supplied:fm",
            "source_occurrence_ids": ["supplied:source"], "source_sha256s": ["0"*64], "producer_attempt_id": "supplied:prior-build"}
        expected = "source_binding_digest_mismatch"
    monkeypatch.setattr(driver.subprocess, "run", lambda *a, **k: pytest.fail("contradictory supplied metadata native invocation"))
    bundle = driver.run_native_hmmer_preparation(make_plan(tmp_path, selected))
    assert bundle["returncode"] is None
    assert any(f["code"].endswith(expected) for f in bundle["failures"])


@pytest.mark.parametrize("fault", ["role", "reason", "program_code", "source_binding_absent", "compatible_integer_widths"])
def test_preflight_failure_meaning_cannot_be_changed(tmp_path, monkeypatch, fault):
    selected = job("hmmerfm-exactmatch", "count_only")
    selected["input_metadata"]["producer_contract"]["byte_order"] = "big"
    monkeypatch.setattr(driver.subprocess, "run", lambda *a, **k: pytest.fail("incompatible import invocation"))
    plan = make_plan(tmp_path, selected)
    bundle = driver.run_native_hmmer_preparation(plan)
    changed = deepcopy(bundle)
    failure = next(f for f in changed["failures"] if f["stage"] == "preflight")
    if fault == "role":
        failure["role"] = "queries"
    elif fault == "reason":
        failure["detail"]["reason"] = "wrong_model_signature"
    elif fault == "source_binding_absent":
        failure.update(code="native_hmmer_preparation_source_binding_digest_mismatch", role="source_sequences",
            detail={"reason": "source_sha256_order_mismatch"})
    elif fault == "compatible_integer_widths":
        failure["detail"]["reason"] = "producer_integer_width_mismatch"
    else:
        failure.update(code="native_hmmer_preparation_invalid_alimask_input", role="queries", detail={"reason": "malformed_stockholm"})
    with pytest.raises(ValueError, match="bundle_preflight_failure_context"):
        driver.validate_preparation_bundle_files(changed, plan["attempt_directory"])


@pytest.mark.parametrize("source,options,total", [
    ("tiny.fa", ["--dna", "--fwd_only"], 28),
    ("rna.fa", ["--rna"], 28),
    ("protein.fa", ["--amino"], 40),
    ("ambiguous.fa", ["--dna"], 18),
])
def test_actual_fm_writer_variants_keep_selected_alphabet_and_full_bytes(tmp_path, source, options, total):
    from gene_annotation_episode.hmmer_fm_data import extract_hmmer_fm_database
    selected = job("makehmmerdb", "build", [*options, "--block_size", "1"])
    selected["operands"] = [operand("sequences", EVIDENCE / "inputs" / source, "fasta")]
    plan, bundle = run_actual(tmp_path, selected)
    assert not bundle["failures"]
    row = next(r for r in bundle["artifacts"] if r["role"] == "fm_database")
    occurrence = {"occurrence_id": "actual:fm", "direction": "output", "role": "fm_database", "ordinal": 0,
        "artifact_ref": "actual:fm", "sha256": row["sha256"], "size_bytes": row["size_bytes"], "completeness": "complete"}
    decoded = extract_hmmer_fm_database(output_bytes(plan, bundle, "fm_database"), occurrence=occurrence, producer_contract=FM_CONTRACT)
    assert decoded["population"]["complete"] is True
    assert decoded["metadata"]["total_char_count"] == total
    assert decoded["metadata"]["dna_reader_compatibility"] == ("incompatible" if source == "protein.fa" else "compatible")


@pytest.mark.parametrize("mode", ["build_alignment", "build_single_sequence_matrix"])
def test_actual_supplied_matrix_and_resaved_alignment_are_retained(tmp_path, mode):
    selected = job("hmmbuild", mode)
    if mode == "build_single_sequence_matrix":
        selected["operands"].append(operand("matrix", BIN.parents[1] / "easel/formats/BLOSUM62", "substitution_matrix"))
    selected["outputs"] += [{"role": "resaved_alignment", "format": "stockholm", "relative_path": "outputs/resaved"},
        {"role": "summary", "format": "hmmbuild_summary", "relative_path": "outputs/summary"}]
    plan, bundle = run_actual(tmp_path, selected)
    assert not bundle["failures"]
    resaved = output_bytes(plan, bundle, "resaved_alignment")
    if mode == "build_single_sequence_matrix":
        assert resaved == b""  # native SingleBuilder does not create postmsa
    else:
        assert b"# STOCKHOLM" in resaved
    assert b"LENG  12" in output_bytes(plan, bundle, "models")


def test_actual_press_native_refusal_does_not_remove_caller_sidecars(tmp_path):
    selected = job("hmmpress", "index")
    source = tmp_path / "duplicate-models.hmm"
    source.write_bytes(Path(selected["operands"][0]["path"]).read_bytes() * 2)
    sidecars = [Path(str(source) + suffix) for suffix in (".h3m", ".h3i", ".h3f", ".h3p")]
    for path in sidecars:
        path.write_bytes(b"caller-owned-original-bundle")
    selected["operands"] = [operand("models", source, "hmmer3_ascii")]
    plan, bundle = run_actual(tmp_path, selected)
    assert bundle["returncode"] != 0
    assert any(f["code"].endswith("nonzero_returncode") for f in bundle["failures"])
    assert all(path.read_bytes() == b"caller-owned-original-bundle" for path in sidecars)
    assert driver.run_native_hmmer_preparation(plan) == bundle


def test_actual_fetch_does_not_discover_ambient_caller_ssi(tmp_path):
    selected = job("hmmfetch", "single_key")
    source = tmp_path / "caller-models.hmm"
    source.write_bytes(Path(selected["operands"][0]["path"]).read_bytes())
    ambient = Path(str(source) + ".ssi")
    ambient.write_bytes(b"caller-sidecar-is-not-selected")
    selected["operands"] = [operand("models", source, "hmmer3_ascii")]
    plan, bundle = run_actual(tmp_path, selected)
    assert not bundle["failures"]
    assert output_bytes(plan, bundle, "fetched_models").count(b"HMMER3/f") == 1
    assert ambient.read_bytes() == b"caller-sidecar-is-not-selected"
    assert not (Path(plan["attempt_directory"]) / "inputs/models.hmm.ssi").exists()


@pytest.mark.parametrize("fault", ["input_missing", "input_changed", "wrong_format", "software_changed", "software_missing", "input_fifo"])
def test_missing_wrong_and_stale_inputs_prevent_execution(tmp_path, monkeypatch, fault):
    selected = job()
    source = tmp_path / "models.hmm"
    source.write_bytes(Path(selected["operands"][0]["path"]).read_bytes())
    selected["operands"] = [operand("models", source, "hmmer3_ascii")]
    if fault == "input_missing":
        source.unlink()
    elif fault == "input_changed":
        source.write_bytes(source.read_bytes().replace(b"tiny_protein", b"fake_protein"))
    elif fault == "wrong_format":
        selected["operands"][0]["format"] = "hmmer_binary"
    elif fault == "software_changed":
        selected["software"]["sha256"] = "0"*64
    elif fault == "software_missing":
        selected["software"]["executable"] = str(tmp_path / "missing")
    else:
        import os
        source.unlink()
        os.mkfifo(source)
    plan = make_plan(tmp_path, selected)
    monkeypatch.setattr(driver.subprocess, "run", lambda *a, **k: pytest.fail("invalid input native invocation"))
    bundle = driver.run_native_hmmer_preparation(plan)
    assert bundle["returncode"] is None and bundle["failures"]
    assert driver.run_native_hmmer_preparation(plan) == bundle


def test_actual_fetch_explicit_index_from_independent_original_artifact_paths(tmp_path, monkeypatch):
    selected = job("hmmfetch", "single_key")
    model, index = tmp_path / "original-model-object", tmp_path / "independent-index-object"
    model.write_bytes((NATIVE / "hmmfetch_index/models.hmm").read_bytes())
    index.write_bytes((NATIVE / "hmmfetch_index/models.hmm.ssi").read_bytes())
    Path(str(model) + ".ssi").write_bytes(b"unselected-ambient-sidecar")
    selected["operands"] = [operand("models", model, "hmmer3_ascii"), operand("ssi", index, "hmmer_ssi")]
    plan, bundle = run_actual(tmp_path, selected)
    assert not bundle["failures"]
    assert [r["original_path"] for r in bundle["inputs"]] == [str(model), str(index)]
    assert [r["relative_path"] for r in bundle["inputs"]] == ["inputs/models.hmm", "inputs/models.hmm.ssi"]
    assert output_bytes(plan, bundle, "fetched_models").count(b"HMMER3/f") == 1
    monkeypatch.setattr(driver.subprocess, "run", lambda *a, **k: pytest.fail("replay executed indexed fetch"))
    assert driver.run_native_hmmer_preparation(plan) == bundle


def test_immutable_working_copy_change_and_missing_outputs_are_retained(tmp_path, monkeypatch):
    plan = make_plan(tmp_path, job("hmmpress", "index"))
    def synthetic(argv, **kwargs):
        Path(argv[-1]).write_bytes(b"synthetic changed private source")
        return subprocess.CompletedProcess(argv, 7)
    monkeypatch.setattr(driver.subprocess, "run", synthetic)
    bundle = driver.run_native_hmmer_preparation(plan)
    assert bundle["returncode"] == 7
    assert any(f["code"].endswith("immutable_working_copy_changed") for f in bundle["failures"])
    assert any(f["code"].endswith("missing_output") for f in bundle["failures"])
    assert all(r["staged_sha256"] == r["final_sha256"] for r in bundle["inputs"])


def test_failed_exec_retains_real_empty_logs_and_uncertain_attempt_never_repeats(tmp_path, monkeypatch):
    plan = make_plan(tmp_path)
    calls = []
    def failed(*args, **kwargs):
        calls.append(1)
        raise OSError(8, "fixture exec format error")
    monkeypatch.setattr(driver.subprocess, "run", failed)
    bundle = driver.run_native_hmmer_preparation(plan)
    assert bundle["returncode"] is None and all(r["size_bytes"] == 0 for r in bundle["artifacts"])
    assert driver.run_native_hmmer_preparation(plan) == bundle
    root = Path(plan["attempt_directory"])
    (root / "bundle.json").unlink()
    with pytest.raises(ValueError, match="unsealed_attempt_execution_uncertain"):
        driver.run_native_hmmer_preparation(plan)
    (root / driver.OWNER_NAME).unlink()
    with pytest.raises(ValueError, match="not_exclusively_owned"):
        driver.run_native_hmmer_preparation(plan)
    assert calls == [1]


@pytest.mark.parametrize("fault", ["input_bytes", "output_bytes", "native_abi", "role", "software", "timestamp", "failure", "identity"])
def test_sealed_byte_and_association_tampering_rejected(tmp_path, monkeypatch, fault):
    plan = make_plan(tmp_path)
    def synthetic(argv, **kwargs):
        kwargs["stdout"].write(b"synthetic byte-custody fixture")
        return subprocess.CompletedProcess(argv, 0)
    monkeypatch.setattr(driver.subprocess, "run", synthetic)
    bundle = driver.run_native_hmmer_preparation(plan)
    root = Path(plan["attempt_directory"])
    changed = deepcopy(bundle)
    if fault == "input_bytes":
        (root / bundle["inputs"][0]["relative_path"]).write_bytes(b"tamper")
    elif fault == "output_bytes":
        (root / bundle["artifacts"][0]["relative_path"]).write_bytes(b"tamper")
    elif fault == "native_abi":
        changed["native_abi"]["bytes_per_float"] = 4
    elif fault == "role":
        changed["artifacts"][0]["role"] = "unselected"
    elif fault == "software":
        changed["software"]["actual_sha256"] = "0"*64
    elif fault == "timestamp":
        changed["finished_at"] = "1900-01-01T00:00:00+00:00"
    elif fault == "identity":
        changed["identity"]["episode_id"] = "other-child"
    else:
        changed["failures"] = [{"stage": "outputs", "code": "unknown", "role": "stdout", "detail": {}}]
    with pytest.raises(ValueError):
        driver.validate_preparation_bundle_files(changed, root)


def test_exact_cli_arity():
    with pytest.raises(ValueError, match="exact_plan_file_operand_required"):
        driver.main([])
    with pytest.raises(ValueError, match="exact_plan_file_operand_required"):
        driver.main(["one", "two"])
