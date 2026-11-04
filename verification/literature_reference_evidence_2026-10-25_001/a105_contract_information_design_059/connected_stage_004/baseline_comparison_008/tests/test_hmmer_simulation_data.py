"""Native-byte and deliberately synthetic verification of the pure S1 reader."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import struct

import pytest

from gene_annotation_episode.hmmer_model_data import extract_hmmer_models
from gene_annotation_episode.hmmer_simulation_data import ROW_FIELDS, populate_hmmsim_sheet


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259/native"
ABI = {"byte_order": "little", "float_format": "ieee754_binary64", "bytes_per_float": 8}
CASES = [f"{mode}_{style}" for mode in ("vit", "msv", "fwd", "hyb") for style in ("fs", "sw", "ls", "s")]
CASES += [f"{mode}_fast" for mode in ("vit", "msv", "fwd")]
MODES = {"vit": "viterbi", "msv": "msv", "fwd": "forward", "hyb": "hybrid"}


def payload(content, role, *, direction="output", ordinal=0, oid=None, completeness="complete"):
    return {"occurrence": {"occurrence_id": oid or f"{direction}:{role}:{ordinal}", "direction": direction,
            "role": role, "ordinal": ordinal, "artifact_ref": "retained/"+(oid or role),
            "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content), "completeness": completeness},
            "content": content}


def native_case(case="vit_fs"):
    directory = NATIVE / ("hmmsim_" + case)
    receipt = json.loads((directory / "receipt.json").read_text())
    assert receipt["returncode"] == 0
    argv = receipt["argv"]
    short_mode, style = case.split("_")
    settings = {"-N": int(argv[argv.index("-N")+1]), "-L": int(argv[argv.index("-L")+1]),
                "--seed": int(argv[argv.index("--seed")+1]), "style": "fs" if style == "fast" else style,
                "fast": style == "fast", "--"+short_mode: True, "-a": "-a" in argv}
    roles = {"scores.bin": "scores", "lengths.txt": "alignments", "filter.txt": "filter",
             "survival.xy": "survival", "ee.xy": "expected_counts", "stdout.log": "stdout", "stderr.log": "stderr"}
    for flag in ("--xfile", "--afile", "--ffile", "--pfile", "--efile"):
        if flag in argv:
            settings[flag] = argv[argv.index(flag)+1]
    if "--pthresh" in argv:
        settings["--pthresh"] = float(argv[argv.index("--pthresh")+1])
    if short_mode == "fwd":
        # Explicit resolved defaults are supplied from the retained HMMER 3.4
        # source; the parser itself never resolves omitted defaults.
        for flag, default, convert in (("--tmin", .02, float), ("--tmax", .02, float), ("--tpoints", 1, int)):
            settings[flag] = convert(argv[argv.index(flag)+1]) if flag in argv else default
        settings["--tlinear"] = "--tlinear" in argv
    model = payload((NATIVE / "hmmbuild_dna/profile.hmm").read_bytes(), "models", direction="input")
    extraction = extract_hmmer_models(model["content"], occurrence=model["occurrence"], format="hmmer3_ascii")
    assert extraction["population"]["complete"], extraction["issues"]
    outputs = {role: [payload((directory / name).read_bytes(), role)] for name, role in roles.items() if (directory / name).exists()}
    return {"operation": {"program": "hmmsim", "mode": MODES[short_mode], "engine_version": "3.4", "settings": settings},
            "inputs": {"models": [model]}, "outputs": outputs, "model_extraction": extraction, "native_abi": ABI}


def synthetic_case(values=None, *, mode="viterbi", models=1):
    case = native_case("fwd_fs" if mode == "forward" else "hyb_fs" if mode == "hybrid" else "vit_fs")
    values = list(range(-10, 10)) if values is None else values
    case["operation"]["settings"] = {"-N": max(1, len(values)), "-L": 30, "seed": 42, "style": "fs", "fast": False,
                                       "tail_masses": [.1, .2] if mode == "forward" else [1.0]}
    model = case["inputs"]["models"][0]
    if models != 1:
        model = payload(model["content"] * models, "models", direction="input")
        case["inputs"] = {"models": [model]}
        case["model_extraction"] = extract_hmmer_models(model["content"], occurrence=model["occurrence"], format="hmmer3_ascii")
    case["outputs"] = {"scores": [payload(struct.pack("<"+"d"*len(values)*models, *(values*models)), "scores")]}
    return case


def kinds(sheet, kind):
    return [r for r in sheet["native_rows"] if r["kind"] == kind]


def codes(sheet):
    return {i["code"] for i in sheet["issues"]}


@pytest.mark.parametrize("case", CASES)
def test_all_nineteen_native_grammars_and_original_occurrences(case):
    args = native_case(case)
    original = deepcopy(args)
    sheet = populate_hmmsim_sheet(**args)
    assert args == original
    assert set(sheet) == {"schema", "operation", "artifact_occurrences", "input_records", "native_rows", "associations", "native_abi", "issues"}
    assert sheet["input_records"] == args["model_extraction"]["records"]
    assert all(r["model_keys"] == [sheet["input_records"][0]["record_key"]] for r in sheet["native_rows"])
    assert all(set(r["payload"]) == ROW_FIELDS[r["kind"]] for r in sheet["native_rows"])
    vector = kinds(sheet, "scores")[0]["payload"]
    assert vector["observed_count"] == vector["declared_population"] == 1000
    assert vector["original_bytes_hex"] == args["outputs"]["scores"][0]["content"].hex()
    assert vector["completeness"] == "complete"
    expected = {"forward_filter_unavailable"} if case.startswith("fwd_") and case != "fwd_fast" else {"hybrid_calibration_undetermined"} if case.startswith("hyb_") else set()
    assert codes(sheet) == expected
    assert len(kinds(sheet, "summary")) == (2 if case.startswith("fwd_") and case != "fwd_fast" else 1)
    if case == "vit_fs":
        assert len(kinds(sheet, "alignments")) == 1000
        series = kinds(sheet, "xy_series")
        assert len(series) == 4
        assert len(series[-1]["payload"]["points"]) == 1000
        assert all(r["payload"]["complete"] for r in series)
        assert [r["payload"]["meaning"] for r in series[:3]] == ["empirical_binned_survival", "fitted_gumbel_survival", "fixed_lambda_gumbel_survival"]


def test_duplicate_names_and_identical_bytes_remain_occurrences():
    args = synthetic_case(models=2)
    sheet = populate_hmmsim_sheet(**args)
    assert [r["model_keys"] for r in kinds(sheet, "scores")] == [["input:models:0#model/0"], ["input:models:0#model/1"]]
    second = payload(args["inputs"]["models"][0]["content"], "models", direction="input", ordinal=1)
    args["inputs"]["models"].append(second)
    args["model_extraction"] = [args["model_extraction"], extract_hmmer_models(second["content"], occurrence=second["occurrence"], format="hmmer3_ascii")]
    raw = args["outputs"]["scores"][0]["content"]*2
    args["outputs"]["scores"] = [payload(raw, "scores")]
    sheet = populate_hmmsim_sheet(**args)
    assert len(sheet["input_records"]) == len(kinds(sheet, "scores")) == 4
    assert kinds(sheet, "scores")[2]["model_keys"] == ["input:models:1#model/0"]


def test_partial_binary_preserves_complete_earlier_segments_and_trailing_bytes():
    args = synthetic_case(models=2)
    raw = args["outputs"]["scores"][0]["content"][:-13]
    args["outputs"]["scores"] = [payload(raw, "scores", completeness="partial")]
    sheet = populate_hmmsim_sheet(**args)
    first, second = kinds(sheet, "scores")
    assert first["payload"]["completeness"] == "complete"
    assert first["payload"]["observed_count"] == 20
    assert second["payload"]["completeness"] == "partial"
    assert second["payload"]["observed_count"] == 18
    assert bytes.fromhex(first["payload"]["original_bytes_hex"]+second["payload"]["original_bytes_hex"]) == raw
    assert "score_segment_incomplete" in codes(sheet)


@pytest.mark.parametrize("abi", [None, {}, {**ABI, "bytes_per_float": 4}])
def test_absent_or_invalid_abi_never_uses_host_representation(abi):
    args = synthetic_case()
    args["native_abi"] = abi
    sheet = populate_hmmsim_sheet(**args)
    assert kinds(sheet, "scores")[0]["payload"]["values"] is None
    assert kinds(sheet, "scores")[0]["payload"]["observed_count"] is None
    assert codes(sheet) & {"abi_missing", "abi_invalid"}


def test_explicit_big_endian_and_nonfinite_cells_retained():
    args = synthetic_case([1.0, float("inf"), -3.0])
    args["native_abi"] = {**ABI, "byte_order": "big"}
    args["outputs"]["scores"] = [payload(struct.pack(">ddd", 1, float("inf"), -3), "scores")]
    sheet = populate_hmmsim_sheet(**args)
    scores = kinds(sheet, "scores")[0]["payload"]
    assert scores["values"] == [1, None, -3]
    assert scores["states"] == ["present", "nonfinite", "present"]
    json.dumps(sheet, allow_nan=False)


def test_absent_empty_zero_and_forward_defect_are_distinct():
    args = native_case("fwd_fs")
    sheet = populate_hmmsim_sheet(**args)
    assert not kinds(sheet, "filter")
    assert "forward_filter_unavailable" in codes(sheet)
    assert any(o["role"] == "filter" and o["size_bytes"] == 0 for o in sheet["artifact_occurrences"])
    del args["outputs"]["filter"]
    sheet = populate_hmmsim_sheet(**args)
    assert "output_missing" in codes(sheet)
    assert not any(o["role"] == "filter" for o in sheet["artifact_occurrences"])
    args = synthetic_case()
    args["outputs"]["filter"] = [payload(b"tiny_dna 0 0.0000\n", "filter")]
    assert kinds(populate_hmmsim_sheet(**args), "filter")[0]["payload"]["count"] == 0
    args["outputs"]["scores"] = [payload(b"", "scores")]
    sheet = populate_hmmsim_sheet(**args)
    assert kinds(sheet, "scores")[0]["payload"]["observed_count"] == 0
    assert kinds(sheet, "scores")[0]["payload"]["completeness"] == "partial"


@pytest.mark.parametrize("mutation,code", [
    (lambda a: a["outputs"]["scores"][0]["occurrence"].update(sha256="0"*64), "occurrence_digest_mismatch"),
    (lambda a: a["inputs"]["models"][0]["occurrence"].update(size_bytes=1), "occurrence_size_mismatch"),
    (lambda a: a["model_extraction"]["occurrence"].update(artifact_ref="wrong"), "model_extraction_mismatch"),
    (lambda a: a["model_extraction"]["records"][0]["locator"].update(byte_end=999999), "model_record_invalid"),
    (lambda a: a["operation"]["settings"].update({"--fwd": True}), "mode_flag_conflict"),
    (lambda a: a["operation"]["settings"].update({"--sw": True}), "style_flag_conflict"),
    (lambda a: a["operation"]["settings"].update({"fast": True, "-a": True}), "fast_traceback_unverified"),
    (lambda a: a["operation"].update(engine_version="99"), "engine_version_unsupported"),
])
def test_wrong_metadata_and_incompatible_selections_fail_join(mutation, code):
    args = native_case()
    mutation(args)
    sheet = populate_hmmsim_sheet(**args)
    assert code in codes(sheet)
    assert not kinds(sheet, "scores")[0]["model_keys"]


def test_summary_wrong_name_invalidates_serial_associations_without_sorting():
    args = native_case()
    args["outputs"]["stdout"] = [payload(args["outputs"]["stdout"][0]["content"].replace(b"tiny_dna", b"different"), "stdout")]
    sheet = populate_hmmsim_sheet(**args)
    assert "model_name_mismatch" in codes(sheet)
    assert not any(r["model_keys"] for r in sheet["native_rows"])


def test_malformed_native_text_keeps_original_tokens_and_valid_prefix():
    args = native_case()
    text = args["outputs"]["stdout"][0]["content"].splitlines()[0]
    args["outputs"]["summary"] = [payload(text+b"\ntiny_dna NaN bad 0\n", "summary")]
    args["outputs"]["alignments"] = [payload(b"4 -2.000\n5 broken extra\n", "alignments")]
    args["outputs"]["filter"] = [payload(b"tiny_dna 1001 1.001\n", "filter")]
    args["outputs"]["survival"] = [payload(b"# legend\n1 0.5\n&\n2 bad\n", "survival")]
    sheet = populate_hmmsim_sheet(**args)
    assert kinds(sheet, "summary")[0]["payload"]["tokens"]["mu"] == "-6.4146"
    assert kinds(sheet, "summary")[1]["payload"]["values"]["tailp"] is None
    assert kinds(sheet, "alignments")[1]["payload"]["tokens"] == ["5", "broken", "extra"]
    assert {"summary_width_invalid", "number_nonfinite", "number_invalid", "alignment_width_invalid", "filter_count_invalid", "xy_unterminated"} <= codes(sheet)


def test_forward_and_hybrid_qualifications_and_mode_specific_fields():
    sheet = populate_hmmsim_sheet(**native_case("fwd_fs"))
    assert set(kinds(sheet, "summary")[0]["payload"]["values"]) == {"tailp", "mu", "lambda", "E10", "mufix", "E10fix", "pmu", "plambda", "E10p"}
    args = native_case("hyb_fs")
    sheet = populate_hmmsim_sheet(**args)
    s = kinds(sheet, "summary")[0]["payload"]
    assert (s["values"]["pmu"], s["tokens"]["pmu"], s["states"]["pmu"]) == (0, "0.0000", "undetermined")
    args["operation"]["settings"]["fast"] = True
    assert "fast_hybrid_unsupported" in codes(populate_hmmsim_sheet(**args))


def test_unknown_tail_schedule_does_not_join_duplicate_models_by_name():
    args = synthetic_case(mode="forward", models=2)
    del args["operation"]["settings"]["tail_masses"]
    args["outputs"]["summary"] = [payload(b"tiny_dna .1 1 2 3 1 3 0 1 4\n"*4, "summary")]
    sheet = populate_hmmsim_sheet(**args)
    assert "tail_schedule_missing" in codes(sheet)
    assert all(not r["model_keys"] for r in kinds(sheet, "summary"))


def test_multiple_models_validate_serial_summary_and_auxiliary_segmentation():
    args = synthetic_case(models=2)
    summary = native_case()["outputs"]["stdout"][0]["content"].splitlines()[0].split()
    summary = b" ".join(summary[:-2])+b"\n"  # no -a in this supplied selection
    args["outputs"]["summary"] = [payload(summary*2, "summary")]
    args["outputs"]["alignments"] = [payload(b"4 -1.000\n"*40, "alignments")]
    args["outputs"]["filter"] = [payload(b"tiny_dna 1 .0500\n"*2, "filter")]
    args["outputs"]["survival"] = [payload(b"1 .1\n&\n"*6, "survival")]
    sheet = populate_hmmsim_sheet(**args)
    keys = [m["record_key"] for m in sheet["input_records"]]
    assert [r["model_keys"] for r in kinds(sheet, "summary")] == [[keys[0]], [keys[1]]]
    assert kinds(sheet, "alignments")[20]["model_keys"] == [keys[1]]
    assert [r["model_keys"] for r in kinds(sheet, "xy_series")] == [[keys[0]]]*3+[[keys[1]]]*3
    args["outputs"]["survival"] = [payload(b"1 .1\n&\n"*5, "survival")]
    sheet = populate_hmmsim_sheet(**args)
    assert not any(r["model_keys"] for r in kinds(sheet, "xy_series"))
    assert all(r["payload"]["meaning"] == "unknown" for r in kinds(sheet, "xy_series"))


def test_mixed_alphabet_models_are_incompatible_not_independently_sorted():
    args = synthetic_case(models=2)
    raw = (NATIVE / "hmmbuild_dna/profile.hmm").read_bytes() + (NATIVE / "hmmbuild_rna/profile.hmm").read_bytes()
    model = payload(raw, "models", direction="input")
    args["inputs"] = {"models": [model]}
    args["model_extraction"] = extract_hmmer_models(raw, occurrence=model["occurrence"], format="hmmer3_ascii")
    sheet = populate_hmmsim_sheet(**args)
    assert "model_alphabet_mismatch" in codes(sheet)
    assert all(not r["model_keys"] for r in kinds(sheet, "scores"))


def test_verbose_scores_with_redirected_summary_keep_tokens_and_precision():
    args = synthetic_case([1.23456]*20)
    args["operation"]["settings"].update({"-v": True, "-o": "summary.txt"})
    raw = b"1.235\n"*20 + b"# CPU time: separate diagnostic\n"
    args["outputs"]["stdout"] = [payload(raw, "stdout")]
    sheet = populate_hmmsim_sheet(**args)
    binary, printed = kinds(sheet, "scores")
    assert binary["payload"]["values"] == [1.23456]*20
    assert printed["payload"]["tokens"] == ["1.235"]*20
    assert printed["payload"]["values"] == [1.235]*20
    assert printed["payload"]["original_bytes_hex"] == (b"1.235\n"*20).hex()
    assert printed["payload"]["representation"] == "printed_3_decimal"


@pytest.mark.parametrize("role,content,code", [
    ("summary", b"tiny_dna 1 0 -1 2 0 2 0 2 0 1 2\n", "number_invalid"),
    ("filter", b"tiny_dna -1 -.05\n", "filter_count_invalid"),
    ("expected_counts", b"# wrong_model\n1 .01\n&\n", "xy_name_mismatch"),
])
def test_native_quantity_domains_and_xy_reference(role, content, code):
    args = synthetic_case()
    args["outputs"][role] = [payload(content, role)]
    assert code in codes(populate_hmmsim_sheet(**args))


def test_unknown_mpi_order_and_duplicate_occurrence_do_not_establish_joins():
    args = native_case()
    args["operation"]["settings"]["--mpi"] = True
    sheet = populate_hmmsim_sheet(**args)
    assert "mpi_order_unverified" in codes(sheet)
    assert not kinds(sheet, "scores")[0]["model_keys"]
    del args["operation"]["settings"]["--mpi"]
    args["outputs"]["scores"].append(deepcopy(args["outputs"]["scores"][0]))
    sheet = populate_hmmsim_sheet(**args)
    assert "occurrence_duplicate" in codes(sheet)
    assert not kinds(sheet, "scores")[0]["model_keys"]


def test_forward_synthetic_xy_curves_retain_last_tail_meaning():
    args = synthetic_case(mode="forward")
    args["outputs"]["survival"] = [payload(b"1 .5\n2 .1\n&\n"*3, "survival")]
    series = kinds(populate_hmmsim_sheet(**args), "xy_series")
    assert series[1]["payload"]["meaning"] == "last_tail_exponential_survival"
    assert series[2]["payload"]["meaning"] == "last_tail_fixed_lambda_exponential_survival"


def test_explicit_resolved_tail_schedule_cannot_conflict_with_native_cli_values():
    args = native_case("fwd_fs")
    args["operation"]["settings"]["tail_masses"] = [.3]
    sheet = populate_hmmsim_sheet(**args)
    assert "setting_conflict" in codes(sheet)
    assert not kinds(sheet, "scores")[0]["model_keys"]


def test_excess_binary_population_does_not_validate_a_wrong_smaller_N():
    args = native_case()
    args["operation"]["settings"]["-N"] = 500
    sheet = populate_hmmsim_sheet(**args)
    assert "score_population_mismatch" in codes(sheet)
    assert len(kinds(sheet, "scores")) == 2
    assert not any(r["model_keys"] for r in kinds(sheet, "scores"))
    assert sum(r["payload"]["observed_count"] for r in kinds(sheet, "scores")) == 1000


def test_pure_modules_have_no_acquisition_execution_or_model_service_imports():
    import ast
    allowed = {"__future__", "copy", "hashlib", "math", "operator", "re", "struct", "hmmer_simulation_data"}
    for name in ("data", "calculations"):
        module = ast.parse((ROOT / f"gene_annotation_episode/hmmer_simulation_{name}.py").read_text())
        imported = {n.module.split(".")[0] for n in ast.walk(module) if isinstance(n, ast.ImportFrom)}
        imported |= {a.name.split(".")[0] for n in ast.walk(module) if isinstance(n, ast.Import) for a in n.names}
        assert imported <= allowed


def test_parser_forbidden_io_and_no_mutation(monkeypatch):
    import builtins
    import socket
    import subprocess
    from gene_annotation_episode.state import Store
    args = native_case()
    before = deepcopy(args)
    def forbidden(*a, **k):
        raise AssertionError("parser attempted I/O or execution")
    with monkeypatch.context() as patch:
        for obj, name in ((builtins, "open"), (Path, "open"), (socket, "socket"), (subprocess, "Popen"), (Store, "__init__")):
            patch.setattr(obj, name, forbidden)
        sheet = populate_hmmsim_sheet(**args)
    assert args == before
    assert kinds(sheet, "scores")[0]["payload"]["observed_count"] == 1000
