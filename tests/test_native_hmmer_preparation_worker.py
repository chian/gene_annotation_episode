"""D1 composition against retained native259/267/270 bytes, without native calls."""
from copy import deepcopy
import builtins
import hashlib
import io
import json
import math
import os
from pathlib import Path
import socket
import struct
import subprocess

import pytest

from gene_annotation_episode import native_hmmer_preparation_worker as worker
from gene_annotation_episode.native_hmmer_preparation_contracts import PROGRAM_MODES
from gene_annotation_episode.hmmer_statistics_calculations import native_hmmstat_parameters
from gene_annotation_episode.state import Store


ROOT = Path(__file__).resolve().parents[1]
P1 = ROOT / "verification/tool_graders_hmmer_preparation_producer_2026-10-26_267"
NATIVE = ROOT / "verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259/native"
MANIFEST = json.loads((P1 / "check005_native_cases.json").read_text())
CASES = MANIFEST["cases"]
CURRENT = ROOT / "verification/tool_graders_hmmer_preparation_capture_2026-10-26_270/check005/temporary"
ABI = {"byte_order": "little", "float_format": "ieee754_binary64", "bytes_per_float": 8,
       "uint8_bytes": 1, "uint16_bytes": 2, "uint32_bytes": 4, "uint64_bytes": 8,
       "int32_bytes": 4, "c_int_bytes": 4, "c_long_bytes": 8, "c_float_bytes": 4}


def payload(content, role, direction, ordinal=0, identity=None, completeness="complete"):
    oid = identity or direction + "/" + role + "/" + str(ordinal)
    return {"occurrence": {"occurrence_id": oid, "direction": direction, "role": role,
        "ordinal": ordinal, "artifact_ref": "retained:" + oid,
        "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content),
        "completeness": completeness}, "content": content}


def arguments(operation, inputs, outputs, role_formats, *, metadata=None, parameters=None, abi=None):
    return {"operation": operation, "inputs": inputs, "outputs": outputs,
        "formats": {p["occurrence"]["occurrence_id"]: role_formats[(direction, role)]
                    for direction, mapping in (("input", inputs), ("output", outputs))
                    for role, values in mapping.items() for p in values},
        "metadata": {} if metadata is None else metadata,
        "parameters": {} if parameters is None else parameters, "native_abi": deepcopy(abi)}


def bundle_arguments(path, expected_sha256=None):
    raw = path.read_bytes()
    if expected_sha256 is not None:
        assert hashlib.sha256(raw).hexdigest() == expected_sha256
    bundle = json.loads(raw)
    mappings, formats = [], {}
    for direction, rows in (("input", bundle["inputs"]), ("output", bundle["artifacts"])):
        mapping, ordinals = {}, {}
        for row in rows:
            role = row["role"]
            ordinal = row["ordinal"] if direction == "input" else ordinals.get(role, 0)
            ordinals[role] = ordinal + 1
            retained = path.parent / row["relative_path"]
            if not retained.exists():
                continue  # a missing occurrence is never fabricated or renumbered
            content = retained.read_bytes()
            sha_key, size_key = (("staged_sha256", "staged_size_bytes") if direction == "input"
                                 else ("sha256", "size_bytes"))
            assert hashlib.sha256(content).hexdigest() == row[sha_key]
            assert len(content) == row[size_key]
            oid = bundle["identity"]["attempt_id"] + "/" + direction + "/" + role + "/" + str(ordinal)
            item = payload(content, role, direction, ordinal, oid)
            item["occurrence"]["artifact_ref"] = str(retained)
            mapping.setdefault(role, []).append(item)
            formats[oid] = row["format"]
        mappings.append(mapping)
    metadata = {}
    if bundle["program"] == "makehmmerdb":
        metadata["producer_contract"] = {"format": "hmmer_fm_3_4", "engine_version": "3.4",
            **{key: bundle["native_abi"][key] for key in
               ("byte_order", "uint8_bytes", "uint16_bytes", "uint32_bytes", "uint64_bytes", "int32_bytes")}}
        if mappings[1].get("fm_database"):
            metadata["source_binding"] = {
                "database_occurrence_id": mappings[1]["fm_database"][0]["occurrence"]["occurrence_id"],
                "source_occurrence_ids": [p["occurrence"]["occurrence_id"] for p in mappings[0]["sequences"]],
                "source_sha256s": [p["occurrence"]["sha256"] for p in mappings[0]["sequences"]],
                "producer_attempt_id": bundle["identity"]["attempt_id"]}
    elif bundle["program"] == "hmmerfm-exactmatch":
        metadata = deepcopy(bundle["requested_job"]["native_hmmer_preparation"]["input_metadata"])
    return {"operation": bundle["operation"], "inputs": mappings[0], "outputs": mappings[1],
        "formats": formats, "metadata": metadata, "parameters": {}, "native_abi": bundle["native_abi"]}


def selected(program, mode=None, *, case=None):
    row = next(r for r in CASES if r["program"] == program and
               (mode is None or r["mode"] == mode) and (case is None or case in r["case"]))
    return bundle_arguments(P1 / row["bundle"], row["bundle_sha256"])


def legacy_artifact(name):
    # This helper only acquires supplied bytes and receipt facts; D1 receives no paths to read.
    from tests.test_hmmer_artifact_data import native_case
    operation, inputs, outputs, bindings = native_case(name)
    role_formats = {("input", "models"): "hmmer3_ascii", ("input", "keys"): "key_file",
        ("input", "ssi"): "hmmer_ssi", ("output", "stdout"): "hmmer_stdout",
        ("output", "stderr"): "hmmer_stderr", ("output", "fetched_models"): "hmmer3_ascii",
        ("output", "binary_models"): "hmmer_binary", ("output", "ssi_index"): "hmmer_ssi",
        ("output", "msv_profiles"): "hmmer_h3f", ("output", "remaining_profiles"): "hmmer_h3p"}
    return arguments(operation, inputs, outputs, role_formats, metadata={"artifact_bindings": bindings})


def legacy_simulation():
    from tests.test_hmmer_simulation_data import native_case
    case = native_case("vit_fs")
    role_formats = {("input", "models"): "hmmer3_ascii", ("output", "stdout"): "hmmer_stdout",
        ("output", "stderr"): "hmmer_stderr", ("output", "scores"): "native_float64_vector",
        ("output", "alignments"): "hmmsim_alignments", ("output", "filter"): "hmmsim_filter",
        ("output", "survival"): "hmmsim_xy", ("output", "expected_counts"): "hmmsim_xy"}
    return arguments(case["operation"], case["inputs"], case["outputs"], role_formats, abi=ABI)


def dna_statistics():
    model = payload((NATIVE / "hmmbuild_dna/profile.hmm").read_bytes(), "models", "input")
    summary = payload((NATIVE / "hmmstat_dna/stdout.log").read_bytes(), "stdout", "output")
    return arguments({"program": "hmmstat", "mode": "summary", "engine_version": "3.4", "settings": {}},
        {"models": [model]}, {"stdout": [summary]},
        {("input", "models"): "hmmer3_ascii", ("output", "stdout"): "hmmer_stdout"},
        parameters=native_hmmstat_parameters("3.4", "DNA"))


def legacy_mask():
    directory = NATIVE / "alimask_alignment"
    receipt = json.loads((directory / "receipt.json").read_text())
    assert receipt["returncode"] == 0
    argv = receipt["argv"]
    interval = argv[argv.index("--alirange") + 1]
    assert interval == "2-4,4-6" and "--amino" in argv and "--hand" not in argv
    source = payload(Path(argv[-2]).read_bytes(), "alignment", "input")
    outputs = {role: [payload((directory / filename).read_bytes(), role, "output")]
               for role, filename in (("stdout", "stdout.log"), ("stderr", "stderr.log"),
                                      ("masked_alignment", "masked.sto"))}
    # Original259 predates P1. These are explicit caller declarations of its
    # observed native Stockholm formats, plus the retained actual request.
    operation = {"program": "alimask", "mode": "mask_alignment", "engine_version": "3.4",
        "settings": {"--alirange": interval, "--amino": True, "--informat": "Stockholm",
                     "--outformat": "Stockholm", "native_argv": argv[1:]}}
    return arguments(operation, {"alignment": [source]}, outputs,
        {("input", "alignment"): "stockholm", ("output", "masked_alignment"): "stockholm",
         ("output", "stdout"): "hmmer_stdout", ("output", "stderr"): "hmmer_stderr"})


def rows(grading, kind):
    return [row for row in grading["calculations"]["rows"] if row.get("kind") == kind]


@pytest.mark.parametrize("case", CASES, ids=[r["case"].split("/")[-1] for r in CASES])
def test_all_retained_native_cases_have_exact_lossless_composition(case):
    args = bundle_arguments(P1 / case["bundle"], case["bundle_sha256"])
    before = deepcopy(args)
    result = worker.grade_hmmer_preparation(**args)
    assert set(result) == worker.GRADING_FIELDS
    assert result["version"] == "native_hmmer_preparation_grading_v1"
    assert result["operation"] == result["sheet"]["operation"] == args["operation"]
    assert result["formats"] == args["formats"]
    assert result["requested_parameters"] == {} and result["metadata"] == args["metadata"]
    expected = [p["occurrence"] for key in ("inputs", "outputs") for ps in args[key].values() for p in ps]
    assert {o["occurrence_id"]: o for o in result["sheet"]["artifact_occurrences"]} == {
        o["occurrence_id"]: o for o in expected}
    assert result["calculations"]["schema"].endswith("components_v1")
    json.dumps(result, allow_nan=False)
    assert args == before


def test_all_twenty_six_modes_are_actual_successful_native_receipts():
    assert len(CASES) == 77
    expected = {(program, mode) for program, modes in PROGRAM_MODES.items() for mode in modes}
    assert len(expected) == 26
    assert {(row["program"], row["mode"]) for row in CASES if row["returncode"] == 0} == expected
    for row in CASES:
        assert hashlib.sha256((P1 / row["receipt"]).read_bytes()).hexdigest() == row["receipt_sha256"]


@pytest.mark.parametrize("index,mode", list(enumerate(("viterbi", "msv", "forward", "hybrid"))))
def test_current_native_simulations_preserve_explicit_defaults(index, mode):
    args = bundle_arguments(CURRENT / ("test_actual_all_selected_modes" + str(index)) /
                            "hmmer-preparation-attempt/bundle.json")
    assert args["operation"]["mode"] == mode
    assert args["operation"]["settings"]["--fast"] is False
    assert args["operation"]["settings"]["--tlinear"] is False
    result = worker.grade_hmmer_preparation(**args)
    vector = next(r["payload"] for r in result["sheet"]["native_rows"] if r["kind"] == "scores")
    assert vector["observed_count"] == vector["declared_population"] == 1000
    assert rows(result, "score_statistics")[0]["components"]["mean"]["state"] == "present"
    assert result["sheet"]["native_abi"] == {key: ABI[key] for key in
                                                ("byte_order", "float_format", "bytes_per_float")}


def test_statistics_independent_kl_and_no_implicit_background():
    args = dna_statistics()
    result = worker.grade_hmmer_preparation(**args)
    component = result["calculations"]["rows"][0]["components"]["mean_match_relative_entropy"]
    assert component["value"] == pytest.approx(1.0074921672642938, abs=1e-13)
    # Direct calculation from the retained native tokens, independent of M1/H1 arithmetic.
    model = args["inputs"]["models"][0]["content"].decode().splitlines()
    costs = [list(map(float, line.split()[1:5])) for line in model
             if line.split() and line.split()[0].isdigit()]
    manual = sum(sum(math.exp(-x) * math.log2(math.exp(-x) / .25) for x in p) for p in costs) / 12
    assert component["value"] == pytest.approx(manual, abs=1e-13)
    assert {o["role"] for o in result["sheet"]["artifact_occurrences"]} == {"models", "stdout"}
    args["parameters"] = {}
    unknown = worker.grade_hmmer_preparation(**args)
    assert unknown["requested_parameters"] == {}
    assert unknown["calculations"]["parameters"]["background"] is None
    assert unknown["calculations"]["rows"][0]["components"]["mean_match_relative_entropy"]["value"] is None


def test_simulation_independent_mean_original_bytes_and_legacy_qualifications():
    args = legacy_simulation()
    result = worker.grade_hmmer_preparation(**args)
    cell = rows(result, "score_statistics")[0]["components"]["mean"]
    assert cell["value"] == pytest.approx(-5.619071923450204, abs=1e-13)
    content = args["outputs"]["scores"][0]["content"]
    values = struct.unpack("<" + "d" * (len(content) // 8), content)
    assert cell["value"] == pytest.approx(math.fsum(values) / len(values), abs=1e-13)
    vector = next(r["payload"] for r in result["sheet"]["native_rows"] if r["kind"] == "scores")
    assert vector["original_bytes_hex"] == content.hex() and vector["observed_count"] == 1000
    old = selected("hmmsim", "viterbi")
    original = deepcopy(old["operation"])
    legacy = worker.grade_hmmer_preparation(**old)
    assert legacy["operation"] == original and "--fast" not in original["settings"]
    assert legacy["sheet"]["issues"]  # recorded missing defaults are not repaired in D1


def test_simple_consensus_is_retained_generated_sequence():
    result = worker.grade_hmmer_preparation(**selected("hmmemit", "consensus_simple"))
    assert rows(result, "generated_record")[0]["sequence"] == "ACDEFGHIKLMN"
    assert rows(result, "consensus")[0]["actual_sequence"] == "ACDEFGHIKLMN"
    assert rows(result, "consensus")[0]["expected_sequence"] == "ACDEFGHIKLMN"


def test_fm_independent_symbol_and_byte_counts_without_host_abi_fallback():
    args = selected("makehmmerdb", "build")
    result = worker.grade_hmmer_preparation(**args)
    components = rows(result, "database_summary")[0]["components"]
    assert components["source_symbol_total"]["value"] == 28
    assert components["actual_database_bytes"]["value"] == 314
    assert len(args["outputs"]["fm_database"][0]["content"]) == 314
    fasta = args["inputs"]["sequences"][0]["content"].decode().splitlines()
    assert sum(len(line) for line in fasta if not line.startswith(">")) == 28
    args["metadata"] = {}
    unknown = worker.grade_hmmer_preparation(**args)
    assert unknown["sheet"]["producer_contract"] is None
    assert unknown["sheet"]["database"]["population"]["state"] == "unsupported"
    assert unknown["native_abi"] == args["native_abi"]


def test_pressed_bundle_actual_byte_sum_and_binary_m1_preserved():
    args = legacy_artifact("hmmpress_success")
    result = worker.grade_hmmer_preparation(**args)
    assert rows(result, "bundle")[0]["bundle_byte_sum"]["value"] == 2725 + 165 + 9918 + 3216 == 16024
    binary = next(e for e in result["sheet"]["model_extractions"] if e["occurrence"]["role"] == "binary_models")
    assert binary["population"] == {"decoded_count": 1, "complete": True, "state": "decoded"}
    assert binary["occurrence"]["size_bytes"] == 2725
    assert not binary["issues"]
    assert binary["records"][0]["representation"]["encoding"] == "hmmer3_binary_probability"


@pytest.mark.parametrize("indexed,count", [(False, 1), (True, 2)])
def test_alias_retrieval_keeps_occurrences_not_a_generic_failure(indexed, count):
    name = "hmmfetch_" + ("indexed" if indexed else "unindexed") + "_alias"
    result = worker.grade_hmmer_preparation(**legacy_artifact(name))
    extraction = next(e for e in result["sheet"]["model_extractions"] if e["occurrence"]["direction"] == "output")
    assert extraction["population"]["decoded_count"] == count
    assert len(extraction["records"]) == count and result["calculations"]["rows"]


def test_build_original_and_resaved_column_populations_and_empty_singlemx():
    result = worker.grade_hmmer_preparation(**selected("hmmbuild", "build_alignment"))
    c = result["calculations"]["rows"][0]["components"]
    assert [c[key]["value"] for key in ("input_sequence_count", "input_column_count", "model_length")] == [3, 14, 12]
    args = selected("hmmbuild", "build_single_sequence_matrix", case="supplied_matrix")
    assert args["outputs"]["resaved_alignment"][0]["content"] == b""
    empty = worker.grade_hmmer_preparation(**args)
    assert any(o["role"] == "resaved_alignment" and o["size_bytes"] == 0 for o in empty["sheet"]["artifact_occurrences"])
    assert "resaved_alignment_empty" in {i["code"] for i in empty["sheet"]["issues"]}


def test_mask_overlap_union_independent_five_of_fourteen():
    result = worker.grade_hmmer_preparation(**legacy_mask())
    c = result["calculations"]["rows"][0]["components"]
    assert c["requested_union_count"]["value"] == len(set(range(2, 5)) | set(range(4, 7))) == 5
    assert c["actual_masked_count"]["value"] == 5
    assert c["masked_fraction"]["value"] == 5 / 14


def test_missing_selected_summary_does_not_become_measured_zero():
    args = selected("hmmbuild", "build_alignment", case="supplied_matrix")
    summary = args["outputs"].pop("summary")
    for p in summary:
        del args["formats"][p["occurrence"]["occurrence_id"]]
    assert args["outputs"]["stdout"][0]["content"] == b""
    result = worker.grade_hmmer_preparation(**args)
    assert not any(o["role"] == "summary" for o in result["sheet"]["artifact_occurrences"])
    assert not any(r["kind"] == "build_summary" for r in result["sheet"]["native_rows"])
    components = result["calculations"]["rows"][0]["components"]
    assert components["input_sequence_count"]["value"] == 3
    assert components["model_length"]["value"] == 12
    assert components["native_relative_entropy"]["value"] is None


def test_conversion_same_bytes_different_roles_no_second_stdout_model_population():
    args = selected("hmmconvert", "ascii")
    assert args["outputs"]["stdout"][0]["content"] == args["outputs"]["converted_models"][0]["content"]
    result = worker.grade_hmmer_preparation(**args)
    assert len(result["sheet"]["artifact_occurrences"]) == 4
    assert len(result["sheet"]["model_extractions"]) == 2
    assert {e["occurrence"]["role"] for e in result["sheet"]["model_extractions"]} == {"models", "converted_models"}


@pytest.mark.parametrize("change,code", [
    ("digest", "occurrence_digest_mismatch"), ("size", "occurrence_size_mismatch"),
    ("identity", "occurrence_id_duplicate"), ("role", "occurrence_role_mismatch"),
    ("ordinal", "occurrence_invalid"), ("format", "format_role_mismatch"),
    ("extra_format", "format_occurrences_mismatch"), ("missing_format", "format_role_mismatch"),
    ("payload_extra", "object_fields"), ("content", "content_bytes_required"),
    ("unknown_parameter", "parameters_unknown"), ("nan_parameter", "finite_json_required"),
    ("inf_metadata", "finite_json_required"), ("unrelated_metadata", "metadata_unrelated"),
    ("bad_binding", "object_fields"), ("bad_operation", "object_fields"),
    ("bad_mode", "program_mode_invalid"), ("abi_subset", "object_fields"),
])
def test_malformed_handoffs_raise_specific_contract_errors(change, code):
    args = selected("hmmconvert", "ascii")
    p = args["inputs"]["models"][0]
    oid = p["occurrence"]["occurrence_id"]
    if change == "digest": p["occurrence"]["sha256"] = "0" * 64
    elif change == "size": p["occurrence"]["size_bytes"] += 1
    elif change == "identity": args["outputs"]["converted_models"][0]["occurrence"]["occurrence_id"] = oid
    elif change == "role": p["occurrence"]["direction"] = "output"
    elif change == "ordinal": p["occurrence"]["ordinal"] = -1
    elif change == "format": args["formats"][oid] = "fasta"
    elif change == "extra_format": args["formats"]["not-supplied"] = "hmmer3_ascii"
    elif change == "missing_format": del args["formats"][oid]
    elif change == "payload_extra": p["path"] = "/forbidden"
    elif change == "content": p["content"] = bytearray(p["content"])
    elif change == "unknown_parameter": args["parameters"]["confidence"] = .9
    elif change == "nan_parameter": args["parameters"]["probability_tolerance"] = float("nan")
    elif change == "inf_metadata": args["metadata"]["artifact_bindings"] = float("inf")
    elif change == "unrelated_metadata": args["metadata"]["producer_contract"] = None
    elif change == "bad_binding": args["metadata"]["artifact_bindings"] = [{"source_sha256": "0" * 64}]
    elif change == "bad_operation": args["operation"]["guess"] = True
    elif change == "bad_mode": args["operation"]["mode"] = "viterbi"
    elif change == "abi_subset": args["native_abi"] = {"byte_order": "little"}
    with pytest.raises(worker.ContractError, match=code):
        worker.grade_hmmer_preparation(**args)


@pytest.mark.parametrize("program,mode", [("hmmemit", "consensus_simple"), ("hmmstat", "summary"),
                                         ("hmmsim", "viterbi"), ("hmmconvert", "ascii")])
def test_missing_models_remain_missing_without_fabricated_extraction(program, mode):
    args = selected(program, mode)
    for p in args["inputs"].pop("models"):
        del args["formats"][p["occurrence"]["occurrence_id"]]
    result = worker.grade_hmmer_preparation(**args)
    assert not any(o["direction"] == "input" and o["role"] == "models" for o in result["sheet"]["artifact_occurrences"])
    if "model_extraction" in result["sheet"]:
        assert result["sheet"]["model_extraction"] is None
    assert result["sheet"]["issues"] or result["calculations"]["issues"]
    assert result["sheet"]["native_rows"] or result["sheet"].get("output_records")


def test_partial_vector_preserves_decoded_prefix_and_unknown_abi_preserves_bytes():
    args = legacy_simulation()
    old = args["outputs"]["scores"][0]
    args["outputs"]["scores"] = [payload(old["content"][:81], "scores", "output",
        identity=old["occurrence"]["occurrence_id"], completeness="partial")]
    partial = worker.grade_hmmer_preparation(**args)
    vector = next(r["payload"] for r in partial["sheet"]["native_rows"] if r["kind"] == "scores")
    assert len(vector["values"]) == 10 and vector["original_bytes_hex"] == old["content"][:81].hex()
    assert rows(partial, "score_statistics")[0]["components"]["mean"]["value"] is None
    args["native_abi"] = None
    unknown = worker.grade_hmmer_preparation(**args)
    vector = next(r["payload"] for r in unknown["sheet"]["native_rows"] if r["kind"] == "scores")
    assert vector["values"] is None and vector["observed_count"] is None
    assert vector["original_bytes_hex"] == old["content"][:81].hex()


def test_explicit_unsupported_abi_never_infers_host_representation():
    args = legacy_simulation()
    args["native_abi"]["float_format"] = "unsupported"
    result = worker.grade_hmmer_preparation(**args)
    vector = next(r["payload"] for r in result["sheet"]["native_rows"] if r["kind"] == "scores")
    assert vector["values"] is None
    assert vector["original_bytes_hex"] == args["outputs"]["scores"][0]["content"].hex()
    assert result["native_abi"]["float_format"] == "unsupported"


def test_nonfinite_native_score_keeps_finite_scores_and_specific_state():
    args = legacy_simulation()
    old = args["outputs"]["scores"][0]
    mutated = struct.pack("<d", float("nan")) + old["content"][8:]
    args["outputs"]["scores"] = [payload(mutated, "scores", "output", identity=old["occurrence"]["occurrence_id"])]
    result = worker.grade_hmmer_preparation(**args)
    vector = next(r["payload"] for r in result["sheet"]["native_rows"] if r["kind"] == "scores")
    assert vector["values"][0] is None and vector["states"][0] == "nonfinite"
    assert vector["observed_count"] == 1000 and len(vector["values"]) == 1000
    assert vector["values"][1] == struct.unpack("<d", old["content"][8:16])[0]
    assert vector["original_bytes_hex"] == mutated.hex()
    assert rows(result, "score_statistics")[0]["components"]["mean"]["value"] is None
    json.dumps(result, allow_nan=False)


def test_all_simulation_model_occurrences_retain_distinct_associations():
    args = legacy_simulation()
    old = args["inputs"]["models"][0]
    later = payload(old["content"], "models", "input", 1, "input/second-model")
    args["inputs"]["models"].append(later)
    args["formats"][later["occurrence"]["occurrence_id"]] = "hmmer3_ascii"
    result = worker.grade_hmmer_preparation(**args)
    model_keys = [r["record_key"] for r in result["sheet"]["input_records"]]
    assert len(model_keys) == len(set(model_keys)) == 2
    assert model_keys[1].startswith("input/second-model#")
    vectors = [r for r in result["sheet"]["native_rows"] if r["kind"] == "scores"]
    assert len(vectors) == 1  # absent second-model score segment is never fabricated
    assert vectors[0]["payload"]["declared_population"] == vectors[0]["payload"]["observed_count"] == 1000
    assert vectors[0]["model_keys"] == [model_keys[0]]
    assert "score_population_mismatch" in {i["code"] for i in result["sheet"]["issues"]}


@pytest.mark.parametrize("change", ["missing_width", "boolean_width", "unknown_field", "bad_hash", "wrong_population"])
def test_fm_metadata_malformed_shapes_are_not_silently_dropped(change):
    args = selected("makehmmerdb", "build")
    if change == "missing_width": del args["metadata"]["producer_contract"]["uint8_bytes"]
    elif change == "boolean_width": args["metadata"]["producer_contract"]["uint8_bytes"] = True
    elif change == "unknown_field": args["metadata"]["source_binding"]["trusted"] = True
    elif change == "bad_hash": args["metadata"]["source_binding"]["source_sha256s"][0] = "invalid"
    elif change == "wrong_population": args["metadata"]["source_binding"]["source_sha256s"] = []
    with pytest.raises(worker.ContractError):
        worker.grade_hmmer_preparation(**args)


def test_declared_binary_format_is_not_guessed_from_ascii_bytes():
    args = selected("hmmconvert", "ascii")
    oid = args["inputs"]["models"][0]["occurrence"]["occurrence_id"]
    args["formats"][oid] = "hmmer_binary"
    result = worker.grade_hmmer_preparation(**args)
    extraction = next(e for e in result["sheet"]["model_extractions"] if e["occurrence"]["occurrence_id"] == oid)
    assert extraction["population"]["decoded_count"] is None
    assert extraction["records"] == [] and extraction["issues"]


def test_original_ordinal_gap_and_duplicate_model_bytes_are_preserved():
    args = selected("hmmconvert", "ascii")
    original = args["inputs"]["models"][0]
    later = payload(original["content"], "models", "input", 2, "input/models/2")
    args["inputs"]["models"].append(later)
    args["formats"][later["occurrence"]["occurrence_id"]] = "hmmer3_ascii"
    result = worker.grade_hmmer_preparation(**args)
    ex = [e for e in result["sheet"]["model_extractions"] if e["occurrence"]["direction"] == "input"]
    assert [e["occurrence"]["ordinal"] for e in ex] == [0, 2]
    assert [e["population"]["decoded_count"] for e in ex] == [1, 1]
    assert ex[0]["records"][0]["record_key"] != ex[1]["records"][0]["record_key"]


def test_negative_parameters_keep_unaffected_statistics_and_original_request():
    args = dna_statistics()
    args["parameters"]["length_probability"] = -1
    result = worker.grade_hmmer_preparation(**args)
    c = result["calculations"]["rows"][0]["components"]
    assert c["position_relative_entropy"]["state"] == "incompatible"
    assert c["mean_match_relative_entropy"]["value"] == pytest.approx(1.0074921672642938)
    assert result["requested_parameters"]["length_probability"] == -1


def test_saved_recalculation_all_schemas_with_parsers_and_io_forbidden(monkeypatch):
    sources = [selected("hmmconvert", "ascii"), selected("hmmbuild", "build_alignment"),
               selected("hmmemit", "consensus_simple"), legacy_simulation(), dna_statistics(),
               selected("makehmmerdb", "build")]
    saved = [json.loads(json.dumps(worker.grade_hmmer_preparation(**args))) for args in sources]
    original = deepcopy(saved)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved recalculation attempted a parser, acquisition, or native work")
    with monkeypatch.context() as patch:
        for name, value in vars(Store).items():
            if callable(value):
                patch.setattr(Store, name, forbidden)
        for target, name in ((builtins, "open"), (io, "open"), (os, "open"), (Path, "open"),
                             (Path, "read_bytes"), (Path, "read_text"), (socket, "socket"),
                             (socket, "create_connection"), (subprocess, "run"), (subprocess, "Popen")):
            patch.setattr(target, name, forbidden)
        for module in (worker.model_data, worker.artifact_data, worker.alignment_data,
                       worker.emission_data, worker.simulation_data, worker.statistics_data, worker.fm_data):
            for name, value in vars(module).items():
                if callable(value) and name.startswith(("populate_", "parse_", "extract_", "iter_")):
                    patch.setattr(module, name, forbidden)
        actual = [worker.recalculate_hmmer_preparation(item["sheet"], parameters=item["requested_parameters"])
                  for item in saved]
        changed = worker.recalculate_hmmer_preparation(saved[4]["sheet"], parameters={})
    assert actual == [item["calculations"] for item in original]
    assert saved == original
    assert changed["rows"][0]["components"]["mean_match_relative_entropy"]["state"] == "missing"
    assert changed["rows"][0]["components"]["mean_match_entropy"]["value"] == pytest.approx(.9925134248800135)


def test_supplied_byte_grading_all_components_forbids_io_native_and_store(monkeypatch):
    args = [selected("hmmpress", "index"), selected("hmmbuild", "build_alignment"),
            selected("hmmemit", "consensus_simple"), legacy_simulation(), dna_statistics(),
            selected("makehmmerdb", "build")]
    def forbidden(*args, **kwargs):
        raise AssertionError("supplied-byte grading attempted acquisition or native work")
    with monkeypatch.context() as patch:
        for name, value in vars(Store).items():
            if callable(value):
                patch.setattr(Store, name, forbidden)
        for target, name in ((builtins, "open"), (io, "open"), (os, "open"), (Path, "open"),
                             (Path, "read_bytes"), (Path, "read_text"), (socket, "socket"),
                             (socket, "create_connection"), (subprocess, "run"), (subprocess, "Popen")):
            patch.setattr(target, name, forbidden)
        results = [worker.grade_hmmer_preparation(**source) for source in args]
    assert all(result["calculations"]["rows"] for result in results)


@pytest.mark.parametrize("change", ["schema", "program", "extra_field", "unknown_parameter", "infinite_parameter"])
def test_recalculation_rejects_wrong_saved_contract(change):
    result = worker.grade_hmmer_preparation(**dna_statistics())
    parameters = {}
    if change == "schema": result["sheet"]["schema"] = "hmmer_emission_sheet_v1"
    elif change == "program": result["sheet"]["operation"].update(program="hmmemit", mode="consensus_simple")
    elif change == "extra_field": result["sheet"]["score_rules"] = {}
    elif change == "unknown_parameter": parameters["confidence"] = .5
    elif change == "infinite_parameter": parameters["length_probability"] = float("inf")
    with pytest.raises(worker.ContractError):
        worker.recalculate_hmmer_preparation(result["sheet"], parameters=parameters)


def test_save_complete_actual_examples_and_source_provenance(tmp_path):
    examples = {"H1": dna_statistics(), "S1": legacy_simulation(),
        "E1": selected("hmmemit", "consensus_simple"), "F1": selected("makehmmerdb", "build"),
        "A1": legacy_artifact("hmmpress_success"), "B1": selected("hmmbuild", "build_alignment"),
        "B1_mask": legacy_mask(), "A1_alias_indexed": legacy_artifact("hmmfetch_indexed_alias"),
        "A1_alias_unindexed": legacy_artifact("hmmfetch_unindexed_alias")}
    report = {}
    for name, args in examples.items():
        grading = worker.grade_hmmer_preparation(**args)
        path = tmp_path / (name + ".json")
        path.write_text(json.dumps(grading, indent=2, allow_nan=False) + "\n")
        report[name] = {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "sources": grading["sheet"]["artifact_occurrences"]}
    (tmp_path / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
