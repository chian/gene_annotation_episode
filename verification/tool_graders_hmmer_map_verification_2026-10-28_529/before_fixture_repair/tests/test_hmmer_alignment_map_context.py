"""Source-defined map examples, not substitutes for pending native conformance.

Large populations below are deliberately constructed numerical operands. The
sampler's native oracle lives with its primitive; forced samples here isolate
PB consensus, all-row denominators, and fallback semantics.
"""
import builtins
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import hmmer_alignment_preparation_calculations as calc
from gene_annotation_episode import hmmer_alignment_preparation_data as data
from gene_annotation_episode import native_hmmer_preparation_driver as driver
from gene_annotation_episode import native_hmmer_preparation_worker as worker
from gene_annotation_episode import hmmer_preparation_result_views as views
from gene_annotation_episode.domain import ContractError
from test_hmmer_alignment_preparation_data import operation, payload
from test_hmmer_preparation_result_views import prepared, project, selection


PROFILE_DIGEST = data.ALIMASK_PROFILE_EXECUTABLE_SHA256


def software(actual=PROFILE_DIGEST, expected=PROFILE_DIGEST):
    return {"executable": "/synthetic/retained/alimask", "expected_sha256": expected,
            "actual_sha256": actual, "declared_engine_version": "3.4"}


def synthetic_alignment(sequences):
    """Shape-compatible input rows, explicitly not parsed native observations."""
    key = "input:alignment:0#alignment/0"
    return {"kind": "alignment", "record_key": key, "occurrence_id": "input:alignment:0",
        "engine_version": "3.4", "header_valid": True, "complete": True,
        "column_count": len(sequences[0]), "column_annotations": {}, "issues": [],
        "rows": [{"record_key": key + "/sequence/" + str(i), "name": "s" + str(i),
            "aligned_sequence": sequence, "geometry_valid": True, "symbols_valid": True,
            "identity_unambiguous": True, "weight": {"state": "missing", "value": None}}
            for i, sequence in enumerate(sequences)]}


def context_for(settings, *, occurrence=None, actual=PROFILE_DIGEST, expected=PROFILE_DIGEST, requested_seed=None):
    occurrence = occurrence or payload("alignment", b"explicit synthetic numerical fixture")["occurrence"]
    return calc.resolve_alimask_map_context(operation=operation(mode="alignment_to_model", **settings),
        software=software(actual, expected), source_occurrence=occurrence,
        requested_options=[] if requested_seed is None else ["--seed", str(requested_seed)])


def sheet_with_context(*, settings=None, context_change=None, suffix=b""):
    settings = settings or {"--dna": True, "--wgsc": True, "--fragthresh": 0,
                            "--symfrac": .6, "--ali2model": "1-4", "--informat": "stockholm"}
    content = b"# STOCKHOLM 1.0\na AAAA\nb AAAA\nc C--C\n//\n" + suffix
    source = payload("alignment", content)
    selected = operation(mode="alignment_to_model", **settings)
    context = context_for(settings, occurrence=source["occurrence"])
    if context_change:
        context_change(context)
    stdout = payload("stdout", b"alignment coordinates model coordinates\n1..4 -> 1..2\n", "output")
    sheet = data.populate_hmmer_alignment_preparation_sheet(operation=selected,
        inputs={"alignment": [source]}, outputs={"stdout": [stdout]},
        map_reconstruction_context=context)
    return sheet, context, source, stdout


@pytest.mark.parametrize("seed", [None, 0, 42, 17])
def test_recorded_cli_seed_is_distinct_from_effective_pb_seed(seed):
    settings = {"--dna": True, "--wpb": True, "--seed": 42 if seed is None else seed}
    context = context_for(settings, requested_seed=seed)
    assert context["requested_cli_seed"] == seed
    assert context["resolved_cli_seed"] == settings["--seed"]
    assert context["effective_pb_config"]["seed"] == 42
    assert context["binding"] == "retained_executable_profile"
    assert set(context) == data.MAP_CONTEXT_FIELDS
    assert data.alimask_map_context_valid(context, settings=settings)


@pytest.mark.parametrize("actual,expected", [(None, PROFILE_DIGEST), ("1" * 64, PROFILE_DIGEST),
                                             (PROFILE_DIGEST, "1" * 64)])
def test_unobserved_or_unbound_actual_executable_stays_unavailable(actual, expected):
    context = context_for({"--dna": True}, actual=actual, expected=expected)
    assert context["producer"]["executable_sha256"] is actual or context["producer"]["executable_sha256"] == actual
    assert context["binding"] == "unavailable"
    assert context["profile"] is context["effective_pb_config"] is None
    record = synthetic_alignment(["A"] * 50001)
    result = calc.reconstruct_alimask_model_map(record, settings={"--dna": True}, map_reconstruction_context=context)
    assert result["map"] is None
    assert result["issues"][0]["code"] == "map_context_unavailable"


def test_shared_kahan_and_divide_then_scale_normalizer():
    raw = [1., 2. ** -53, 2. ** -53]
    weights, retained = calc._normalize_easel_weights(raw)
    total = 1. + 2. ** -52
    assert retained == {"method": "easel_kahan_divide_then_scale", "sum": total,
                        "sequence_count": 3, "zero_sum": False}
    assert weights == [(value / total) * 3 for value in raw]
    zeros, retained = calc._normalize_easel_weights([0.] * 49)
    assert zeros == [(1. / 49) * 49] * 49
    assert retained["sum"] == 0 and retained["zero_sum"] is True


@pytest.mark.parametrize("method,raw", [("--wgsc", [.25, .25, .5]), ("--wblosum", [.5, .5, 1.])])
def test_gsc_blosum_weighting_changes_gap_map_and_retains_raw_operands(method, raw):
    record = synthetic_alignment(["AAAA", "AAAA", "C--C"])
    settings = {"--dna": True, method: True, "--symfrac": .6, "--fragthresh": 0}
    result = calc.reconstruct_alimask_model_map(record, settings=settings)
    assert [r["weight"] for r in result["weights"]] == [.75, .75, 1.5]
    assert result["map"] == [1, 4]
    trace = result["weighting_trace"]
    assert set(trace) == {"method", "raw_weights", "normalization", "gsc_tree", "blosum_clusters", "sampling"}
    assert trace["raw_weights"] == raw
    assert trace["normalization"]["sum"] == sum(raw)
    assert trace["sampling"] is None
    assert bool(trace["gsc_tree"]) == (method == "--wgsc")
    assert bool(trace["blosum_clusters"]) == (method == "--wblosum")
    unweighted = calc.reconstruct_alimask_model_map(record,
        settings={"--dna": True, "--wnone": True, "--symfrac": .6, "--fragthresh": 0})
    assert unweighted["map"] == [1, 2, 3, 4]


def test_one_shared_digitization_reaches_raw_helpers(monkeypatch):
    observed = []
    original = calc.gsc_raw_weights
    def raw(sequences, *, residue_symbols):
        observed.append((sequences, residue_symbols))
        return original(sequences, residue_symbols=residue_symbols)
    monkeypatch.setattr(calc, "gsc_raw_weights", raw)
    record = synthetic_alignment(["uiX._", "taN--"])
    result = calc.reconstruct_alimask_model_map(record, settings={"--dna": True, "--wgsc": True})
    assert result["state"] == "present"
    assert observed == [(["TAN--", "TAN--"], "ACGTRYMKSWHBVDN")]


@pytest.mark.parametrize("size", [50000, 50001, 130001])
def test_sampling_threshold_and_sample_record_keys_are_source_ordered(size):
    settings = {"--dna": True, "--wpb": True}
    record = synthetic_alignment(["A"] * size)
    result = calc.reconstruct_alimask_model_map(record, settings=settings,
        map_reconstruction_context=context_for(settings))
    assert result["map"] == [1]
    trace = result["weighting_trace"]
    sample = trace["sampling"]
    if size == 50000:
        assert sample is None
    else:
        assert sample["basis"] == "deterministic_source_reconstruction"
        assert sample["seed"] == 42 and sample["consensus_basis"] == "sample"
        ordinals = sample["source_row_ordinals"]
        assert len(ordinals) == len(set(ordinals)) == 10000
        assert ordinals == sorted(ordinals) and 0 <= ordinals[0] <= ordinals[-1] < size
        assert sample["source_record_keys"] == [record["rows"][i]["record_key"] for i in ordinals]
    assert len(trace["raw_weights"]) == size
    assert trace["raw_weights"][0] == 1. / size


@pytest.mark.parametrize("fragment_count,rejected", [(5000, False), (5001, True)])
def test_sample_fragment_rejection_is_strictly_more_than_half(monkeypatch, fragment_count, rejected):
    monkeypatch.setattr(calc, "sample_easel_pb_rows", lambda *a, **kw: list(range(10000)))
    record = synthetic_alignment(["--A-"] * fragment_count + ["AAAA"] * (50001 - fragment_count))
    settings = {"--dna": True, "--wpb": True}
    result = calc.reconstruct_alimask_model_map(record, settings=settings,
        map_reconstruction_context=context_for(settings))
    sample = result["weighting_trace"]["sampling"]
    assert sample["fragment_count"] == fragment_count and sample["rejected"] is rejected
    assert sample["consensus_basis"] == ("all_sequences" if rejected else "sample")


@pytest.mark.parametrize("all_columns", [False, True])
def test_empty_sample_consensus_falls_back_through_all_rows(monkeypatch, all_columns):
    monkeypatch.setattr(calc, "sample_easel_pb_rows", lambda *a, **kw: list(range(10000)))
    rows = ["A--A", "-AA-"] * (25001 if all_columns else 5000)
    if not all_columns:
        rows += ["AAAA"] * 40001
    settings = {"--dna": True, "--wpb": True}
    result = calc.reconstruct_alimask_model_map(synthetic_alignment(rows), settings=settings,
        map_reconstruction_context=context_for(settings))
    sample = result["weighting_trace"]["sampling"]
    assert sample["fragment_count"] == 0 and sample["rejected"] is False
    assert sample["consensus_basis"] == ("all_columns" if all_columns else "all_sequences")
    assert result["pb_consensus_columns"] == [1, 2, 3, 4]


def test_sample_selects_columns_but_pb_denominators_use_all_rows(monkeypatch):
    monkeypatch.setattr(calc, "sample_easel_pb_rows", lambda *a, **kw: list(range(10000)))
    settings = {"--dna": True, "--wpb": True, "--fragthresh": 0, "--symfrac": .6}
    record = synthetic_alignment(["A--A"] * 10000 + ["CCCC"] * 40001)
    result = calc.reconstruct_alimask_model_map(record, settings=settings,
        map_reconstruction_context=context_for(settings))
    assert result["pb_consensus_columns"] == [1, 4]
    raw = result["weighting_trace"]["raw_weights"]
    assert raw[:10000] == [1. / (2 * 10000)] * 10000
    assert raw[10000:] == [1. / (2 * 40001)] * 40001
    assert result["map"] == [1, 4]


@pytest.mark.parametrize("change", [
    lambda c: c.update(source_sha256="0" * 64),
    lambda c: c.update(source_occurrence_id="other:alignment:0"),
    lambda c: c["effective_pb_config"].update(seed=17),
    lambda c: c["profile"]["source_sha256s"].update({"hmmer/src/alimask.c": "0" * 64}),
    lambda c: c.update(requested_cli_seed=17),
])
def test_semantic_context_conflicts_preserve_counts_and_native_endpoints(change):
    sheet, _, _, _ = sheet_with_context(context_change=change)
    result = calc.calculate_hmmer_alignment_preparation_components(sheet)
    row = result["rows"][0]
    assert row["components"]["input_sequence_count"]["value"] == 3
    assert row["components"]["input_column_count"]["value"] == 4
    assert row["components"]["native_mapping_row_count"]["value"] == 1
    assert row["intervals"][0]["returned_source_span"]["value"] == 4
    assert row["intervals"][0]["returned_target_span"]["value"] == 2
    assert row["components"]["mapped_model_position_count"]["value"] is None
    assert "map_context_invalid" in {i["code"] for i in result["issues"]}


def test_structural_context_failure_is_not_a_semantic_unknown():
    sheet, _, _, _ = sheet_with_context()
    sheet["input_records"][0]["map_reconstruction_context"]["unexpected"] = True
    result = calc.calculate_hmmer_alignment_preparation_components(sheet)
    assert not result["rows"] and result["issues"][0]["code"] == "sheet_invalid"


def test_saved_recalculation_uses_retained_context_without_io_or_acquisition(monkeypatch):
    sheet, _, _, _ = sheet_with_context()
    sheet = json.loads(json.dumps(sheet))
    expected = calc.calculate_hmmer_alignment_preparation_components(sheet)
    original = deepcopy(sheet)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved reconstruction attempted acquisition or parsing")
    for target, name in ((builtins, "open"), (Path, "open"), (Path, "read_bytes"),
                         (socket, "socket"), (subprocess, "run"), (subprocess, "Popen"),
                         (data, "populate_hmmer_alignment_preparation_sheet"),
                         (calc, "resolve_alimask_map_context")):
        monkeypatch.setattr(target, name, forbidden)
    assert calc.calculate_hmmer_alignment_preparation_components(sheet) == expected
    assert sheet == original


def projection_fixture():
    sheet, context, source, stdout = sheet_with_context()
    args = {"operation": sheet["operation"], "inputs": {"alignment": [source]},
        "outputs": {"stdout": [stdout]}, "formats": {source["occurrence"]["occurrence_id"]: "stockholm",
            stdout["occurrence"]["occurrence_id"]: "hmmer_stdout"},
        "metadata": {"map_reconstruction_context": context}, "parameters": {}}
    return prepared(args)


@pytest.mark.parametrize("location", ["metadata", "sheet", "both", "artifact_only"])
def test_saved_projection_rejects_context_disagreement(location):
    grading, occurrences = projection_fixture()
    if location in {"metadata", "both", "artifact_only"}:
        grading["metadata"]["map_reconstruction_context"]["source_sha256"] = "0" * 64
    if location in {"sheet", "both"}:
        grading["sheet"]["input_records"][0]["map_reconstruction_context"]["source_sha256"] = "0" * 64
    if location == "artifact_only":
        grading["sheet"] = grading["calculations"] = None
    with pytest.raises(ContractError, match="map_context"):
        project(grading, occurrences, selection(None))


def test_saved_projection_copies_frozen_values_without_reconstruction(monkeypatch):
    grading, occurrences = projection_fixture()
    choice = selection(quantities=["components.mapped_model_position_count", "components.input_sequence_count"])
    expected = project(grading, occurrences, choice)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved projection recomputed numerical values")
    monkeypatch.setattr(calc, "reconstruct_alimask_model_map", forbidden)
    monkeypatch.setattr(worker, "recalculate_hmmer_preparation", forbidden)
    monkeypatch.setattr(data, "populate_hmmer_alignment_preparation_sheet", forbidden)
    assert project(grading, occurrences, choice) == expected
    assert [q["value"] for q in expected["rows"][0]["quantities"]] == [2, 3]


def preflight_fixture(tmp_path, content, *, settings=None, actual=PROFILE_DIGEST):
    settings = settings or {"--dna": True, "--wgsc": True, "--ali2model": "1-4", "--symfrac": .6, "--fragthresh": 0}
    staged = tmp_path / "source.sto"
    staged.write_bytes(content)
    job = {"mode": "alignment_to_model", "options": []}
    bundle = {"identity": {"attempt_id": "synthetic-preflight"}, "operation": operation(mode=job["mode"], **settings),
        "inputs": [{"role": "alignment", "ordinal": 0, "relative_path": "source.sto", "format": "stockholm",
            "artifact_ref": None, "staged_sha256": hashlib.sha256(content).hexdigest(), "staged_size_bytes": len(content)}],
        "software": software(actual), "failures": []}
    return staged, job, bundle


@pytest.mark.parametrize("suffix", [b"", b"# STOCKHOLM 1.0\nlate AC\n", b"# STOCKHOLM 1.0\nbad\n//\n", b"\xffinvalid suffix\n"])
def test_driver_reuses_shared_first_msa_and_keeps_original_suffix(tmp_path, monkeypatch, suffix):
    original = b"# STOCKHOLM 1.0\na AAAA\nb AAAA\nc C--C\n//\n" + suffix
    staged, job, bundle = preflight_fixture(tmp_path, original)
    calls = []
    parse, reconstruct = data.populate_hmmer_alignment_preparation_sheet, calc.reconstruct_alimask_model_map
    def reader(**kwargs):
        calls.append("reader")
        assert kwargs["inputs"]["alignment"][0]["content"] == original
        return parse(**kwargs)
    def mapper(record, **kwargs):
        calls.append("map")
        assert len(record["rows"]) == 3
        return reconstruct(record, **kwargs)
    monkeypatch.setattr(data, "populate_hmmer_alignment_preparation_sheet", reader)
    monkeypatch.setattr(calc, "reconstruct_alimask_model_map", mapper)
    monkeypatch.setattr(driver.subprocess, "run", lambda *a, **k: pytest.fail("preflight executed native work"))
    driver._alimask_preflight_shared(tmp_path, job, bundle)
    assert calls == ["reader", "map"] and not bundle["failures"]
    assert staged.read_bytes() == original
    assert not hasattr(driver, "_stockholm_for_map") and not hasattr(driver, "_alimask_map")


@pytest.mark.parametrize("content,reason", [
    (b"# STOCKHOLM 1.0\na AAAA\n", "malformed_stockholm"),
    (b"# STOCKHOLM 1.0\na AAAA\n# STOCKHOLM 1.0\nb AAAA\n//\n", "multiple_alignments"),
    (b"# STOCKHOLM 1.0\na AAAA\n#=GC RF xx\n//\n", "malformed_stockholm"),
    (b"# STOCKHOLM 1.0\n#=GS a WT\na AAAA\n//\n", "invalid_weights"),
    (b"# STOCKHOLM 1.0\n#=GS absent WT 1\na AAAA\n//\n", "invalid_weights"),
    (b"# STOCKHOLM 1.0\n#=GS a WT 1\na AAAA\nb AAAA\n//\n", "invalid_weights"),
    (b"# STOCKHOLM 1.0\na AAAA\na CCCC\n//\n", "malformed_stockholm"),
    (b"# STOCKHOLM 1.0\na ----\n//\n", "empty_model_map"),
])
def test_driver_first_record_failures_remain_specific(tmp_path, content, reason):
    _, job, bundle = preflight_fixture(tmp_path, content)
    driver._alimask_preflight_shared(tmp_path, job, bundle)
    assert bundle["failures"][0]["detail"]["reason"] == reason


def test_driver_after_last_match_is_rejected_and_mm_symbols_are_not_a_new_gate(tmp_path):
    content = b"# STOCKHOLM 1.0\na AAAA\n#=GC RF xx..\n#=GC MM XXXX\n//\n"
    _, job, bundle = preflight_fixture(tmp_path, content,
        settings={"--hand": True, "--ali2model": "3-4"})
    driver._alimask_preflight_shared(tmp_path, job, bundle)
    assert bundle["failures"][0]["code"].endswith("unsafe_alimask_range")
    bundle["failures"] = []
    bundle["operation"]["settings"]["--ali2model"] = "1-2"
    driver._alimask_preflight_shared(tmp_path, job, bundle)
    assert not bundle["failures"]


def test_final_float32_occupancy_preserves_source_row_accumulation_order():
    first = synthetic_alignment(["AA", "A-", "-A"])
    for row, weight in zip(first["rows"], [16777216., 1., 1.]):
        row["weight"] = {"state": "present", "value": weight}
    second = deepcopy(first)
    second["rows"] = second["rows"][1:] + second["rows"][:1]
    for ordinal, row in enumerate(second["rows"]):
        row["record_key"] = second["record_key"] + "/sequence/" + str(ordinal)
    settings = {"--dna": True, "--wgiven": True, "--fragthresh": 0, "--symfrac": 1}
    original = calc.reconstruct_alimask_model_map(first, settings=settings)
    reordered = calc.reconstruct_alimask_model_map(second, settings=settings)
    assert original["map"] == [1, 2]
    assert reordered["map"] == []
    assert original["column_occupancy"][0]["weighted_residue_gap_count"] == 16777216.
    assert reordered["column_occupancy"][0]["weighted_residue_gap_count"] == 16777218.
    assert reordered["state"] == "present"  # An established empty map is not unavailable.


def test_driver_unknown_sampled_profile_has_closed_configuration_failure(tmp_path):
    content = ("# STOCKHOLM 1.0\n" + "".join("s" + str(i) + " A\n" for i in range(50001)) + "//\n").encode()
    _, job, bundle = preflight_fixture(tmp_path, content, actual=None,
        settings={"--dna": True, "--wpb": True, "--ali2model": "1-1"})
    driver._alimask_preflight_shared(tmp_path, job, bundle)
    problem, = bundle["failures"]
    assert problem["code"].endswith("unsupported_alimask_model_map")
    assert problem["detail"]["reason"] == "map_configuration_unavailable"
    assert "map_configuration_unavailable" in driver.PREFLIGHT_REASONS
    from gene_annotation_episode import native_hmmer_preparation_acquisition as acquisition
    acquisition._validate_preflight_failure(problem, {"program": "alimask", "mode": "alignment_to_model"}, {})


@pytest.mark.parametrize("program,collection", [("hmmbuild", "input_records"), ("alimask", "native_rows")])
def test_direct_saved_projection_rejects_illegally_placed_context(program, collection):
    if program == "hmmbuild":
        from test_native_hmmer_preparation_worker import selected
        grading, occurrences = prepared(selected("hmmbuild", "build_alignment"))
        context = context_for({"--dna": True})
    else:
        grading, occurrences = projection_fixture()
        context = grading["metadata"]["map_reconstruction_context"]
    grading["sheet"][collection][0]["map_reconstruction_context"] = deepcopy(context)
    with pytest.raises(ContractError, match="map_context_metadata_mismatch"):
        project(grading, occurrences, selection(None))
