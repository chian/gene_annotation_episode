"""New input operands use the existing B1 numerical authority.

Retained fixtures remain unchanged. Mutations below are labeled engineering
cases; run these only in the root-selected bounded verification lifecycle.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode import hmmer_alignment_preparation_calculations as calc
from gene_annotation_episode import hmmer_alignment_preparation_data as data
from gene_annotation_episode import native_hmmer_preparation_worker as worker
from test_hmmer_alignment_preparation_data import operation, payload

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "verification/tool_graders_hmmer_input_native_oracle_2026-10-28_539/fixtures"
EMISSION = ROOT / "verification/tool_graders_infernal_preparation_emission_2026-10-26_250/native"
SELEX = ROOT / "resources/software/infernal-1.1.5/easel/esl_msa_testfiles/selex/selex.good.4"


def source_record(content, fmt, alphabet=None):
    item = payload("alignment", content)
    return data.read_hmmer_alignment_input(content, declared_format=fmt,
        occurrence=item["occurrence"], explicit_alphabet=alphabet, engine_version="3.4")


def sheet_for(content, fmt, *, alphabet=None, mode="mask_alignment", output=None, **options):
    flag = {"mask_alignment": "--alirange", "mask_model": "--modelrange",
            "alignment_to_model": "--ali2model", "model_to_alignment": "--model2ali"}[mode]
    settings = {"--informat": fmt, "--outformat": "stockholm", flag: "1-2", **options}
    if alphabet is not None:
        settings[{"amino": "--amino", "DNA": "--dna", "RNA": "--rna"}[alphabet]] = True
    outputs = {} if output is None else {"masked_alignment": [payload("masked_alignment", output, "output")]}
    return data.populate_hmmer_alignment_preparation_sheet(operation=operation(mode=mode, **settings),
        inputs={"alignment": [payload("alignment", content)]}, outputs=outputs)


def checks(result, code):
    return [item for item in result["checks"] if item["code"] == code]


@pytest.mark.parametrize("fixture,fmt,alphabet", [
    ("afa_auto_dna.input", "afa", "DNA"),
    ("afa_auto_rna.input", "afa", "RNA"),
    ("a2m_auto_pre_map_O.input", "a2m", "amino"),
])
def test_inferred_original_alphabet_uses_identical_existing_map_math(fixture, fmt, alphabet):
    content = (ORACLE / fixture).read_bytes()
    inferred = source_record(content, fmt)["records"][0]
    explicit = source_record(content, fmt, alphabet)["records"][0]
    settings = {"--informat": fmt, "--fast": True, "--wnone": True, "--fragthresh": 0.0}
    chosen = {**settings, {"amino": "--amino", "DNA": "--dna", "RNA": "--rna"}[alphabet]: True}
    first = calc.reconstruct_alimask_model_map(inferred, settings=settings)
    second = calc.reconstruct_alimask_model_map(explicit, settings=chosen)
    assert inferred["input_decoding"]["effective_alphabet"] == alphabet
    assert inferred["input_decoding"]["alphabet_basis"] == "native_source_inference"
    assert first == second
    assert first["state"] == "present" and first["map"] == list(range(1, 13))
    assert [row["weight"] for row in first["weights"]] == [1.0, 1.0]
    if fixture == "a2m_auto_pre_map_O.input":
        assert "O" not in "".join(row["aligned_sequence"] for row in inferred["rows"])
        assert inferred["input_decoding"]["alphabet_probe"]["counts_az"][14] == 4


@pytest.mark.parametrize("hand", [False, True])
@pytest.mark.parametrize("field,value", [
    ("reader_profile", "unbound-reader"), ("source_sha256", "0" * 64),
    ("format", "phylip"), ("effective_alphabet", "amino"),
])
def test_present_invalid_context_never_falls_back_to_flags_or_hand(hand, field, value):
    content = (ORACLE / "afa_auto_dna.input").read_bytes()
    record = source_record(content, "afa", "DNA")["records"][0]
    record["input_decoding"][field] = value
    # Local checks have no original occurrence, so a syntactically valid hash
    # alone cannot prove a custody mismatch; the saved-sheet test covers that.
    if field == "source_sha256":
        record["input_decoding"][field] = "not-a-digest"
    result = calc.reconstruct_alimask_model_map(record,
        settings={"--informat": "afa", "--dna": True, "--hand": hand})
    assert result["state"] == "incompatible" and result["map"] is None
    assert [item["code"] for item in result["issues"]] == ["input_decoding_invalid"]


@pytest.mark.parametrize("mutation", ["source_hash", "probe_count", "row_copy", "event_bytes", "source_handoff"])
def test_saved_optional_context_and_geometry_are_validated_before_calculation(mutation):
    content = (ORACLE / "afa_auto_dna.input").read_bytes()
    output = b"# STOCKHOLM 1.0\na ACGTACGTACGT\nb ACGTACGTACGT\n#=GC MM mm..........\n//\n"
    sheet = sheet_for(content, "afa", output=output)
    assert not any(item["code"] == "sheet_invalid" for item in calc.calculate_hmmer_alignment_preparation_components(sheet)["issues"])
    broken = deepcopy(sheet)
    record = broken["input_records"][0]
    if mutation == "source_hash":
        record["input_decoding"]["source_sha256"] = "0" * 64
    elif mutation == "probe_count":
        record["input_decoding"]["alphabet_probe"]["counts_az"][0] = True
    elif mutation == "row_copy":
        record["rows"][0]["aligned_sequence"] = "T" + record["rows"][0]["aligned_sequence"][1:]
    elif mutation == "event_bytes":
        record["native_input"]["events"][0]["raw"] += "x"
    else:
        broken["output_records"][0]["source_alphabet"]["alphabet"] = "RNA"
    result = worker.recalculate_hmmer_preparation(broken, parameters={})
    assert result["rows"] == []
    assert [item["code"] for item in result["issues"]] == ["sheet_invalid"]


def test_null_failed_geometry_remains_partial_data_and_not_zero():
    sheet = sheet_for((ORACLE / "a2m_fewer_consensus.input").read_bytes(), "a2m", alphabet="DNA")
    source = sheet["input_records"][0]
    assert any(row["aligned_sequence"] is None for row in source["rows"])
    result = worker.recalculate_hmmer_preparation(sheet, parameters={})
    assert not any(item["code"] == "sheet_invalid" for item in result["issues"])
    assert result["rows"][0]["components"]["input_sequence_count"]["value"] is None
    assert result["rows"][0]["components"]["input_sequence_count"]["state"] == "incomplete"


def annotated_selex(tag, bad):
    """An explicitly authored diagnostic copy of retained selex.good.4."""
    content = SELEX.read_bytes()
    if tag in {"RF", "MM"}:
        content = content.replace(b"#=RF", ("#=" + tag).encode(), 1)
        original = b"xxxxxxx"
    elif tag == "SS_cons":
        original = b">>>>+>>"
    else:
        if tag == "SA":
            content = content.replace(b"#=SS", b"#=SA", 1)
        original = b"+++++>>"
    replacement = b"x" + bad + b"x" * (6 - len(bad))
    return content.replace(original, replacement, 1)


@pytest.mark.parametrize("tag", ["RF", "MM", "SS_cons", "SS", "SA"])
@pytest.mark.parametrize("bad", [b"\x00", b"\xff", b"\xc3\xa9"])
def test_byte_annotations_preserve_sequence_math_and_qualified_unknowns(tag, bad):
    sheet = sheet_for(annotated_selex(tag, bad), "selex", alphabet="RNA",
        mode="mask_model", **{"--fast": True, "--wnone": True, "--fragthresh": 0.0})
    record = sheet["input_records"][0]
    original = source_record(SELEX.read_bytes(), "selex", "RNA")["records"][0]
    settings = sheet["operation"]["settings"]
    reconstruction = calc.reconstruct_alimask_model_map(record, settings=settings)
    assert reconstruction == calc.reconstruct_alimask_model_map(original, settings=settings)
    assert record["native_input"]["native_status_equivalent"] == 0
    assert record["native_input"]["reader_state"] == "complete"
    assert not {"alignment_invalid", "annotation_geometry_invalid"} & {i["code"] for i in record["issues"]}
    assert "annotation_byte_interpretation_unavailable" in {i["code"] for i in record["issues"]}
    target = record["rows"][0] if tag in {"SS", "SA"} else record
    annotation = target["column_annotations"][tag]
    assert annotation["valid"] is False
    assert bad in annotation["text"].encode("utf-8", errors="surrogateescape")
    result = worker.recalculate_hmmer_preparation(sheet, parameters={})
    assert not any(i["code"] == "sheet_invalid" for i in result["issues"])
    cells = result["rows"][0]["components"]
    assert cells["input_sequence_count"]["value"] == len(original["rows"])
    assert cells["mapped_model_position_count"]["value"] == len(reconstruction["map"])
    if tag == "RF":
        assert cells["rf_consensus_count"]["state"] == "missing"
        assert cells["rf_consensus_count"]["inputs"][0]["field"] == "column_annotations.RF"
        hand = calc.reconstruct_alimask_model_map(record, settings={**settings, "--hand": True})
        assert hand["map"] is None and hand["issues"][0]["code"] == "rf_missing"
    if tag == "MM":
        assert calc._mm(record, absent_is_empty=True) == (None, "incompatible")
        assert cells["input_masked_count"]["value"] is None
        assert cells["input_masked_count"]["state"] == "incompatible"


def test_inferred_source_alphabet_is_used_for_output_fragment_digitization():
    # Authored X is below the native 2% noncanonical threshold; it digitizes to N.
    sequence = "ACGT" * 25 + "X"
    target = "ACGT" * 25 + "N"
    content = (">a\n" + sequence + "\n>b\n" + sequence + "\n").encode()
    output = ("# STOCKHOLM 1.0\na " + target + "\nb " + target + "\n#=GC MM mm" + "." * 99 + "\n//\n").encode()
    sheet = sheet_for(content, "afa", output=output, mode="mask_model",
        **{"--fast": True, "--wnone": True, "--fragthresh": 0.0})
    result = calc.calculate_hmmer_alignment_preparation_components(sheet)
    assert sheet["input_records"][0]["input_decoding"]["effective_alphabet"] == "DNA"
    assert checks(result, "sequence_content")[0]["state"] == "pass"
    assert checks(result, "fragment_marking")[0]["state"] == "pass"
    assert result["rows"][0]["reconstruction"]["marked_sequences"][0]["sequence"] == target


def test_unknown_source_stays_unknown_and_legacy_absence_is_explicit_only():
    unknown = sheet_for((ORACLE / "afa_auto_refusal.input").read_bytes(), "afa")
    assert unknown["input_records"] == []
    result = calc.calculate_hmmer_alignment_preparation_components(unknown)
    assert result["rows"][0]["components"]["input_alignment_count"]["state"] == "missing"
    assert result["rows"][0]["components"]["input_alignment_count"]["value"] is None
    legacy = data._alignment_records(payload("alignment", b"# STOCKHOLM 1.0\na ACGT\n#=GC RF xxxx\n//\n"),
        "stockholm", {"engine_version": "3.4"}, {"issues": [], "native_rows": []})[0]
    assert "input_decoding" not in legacy
    assert calc.reconstruct_alimask_model_map(legacy, settings={})["issues"][0]["code"] == "alphabet_missing"
    assert calc.reconstruct_alimask_model_map(legacy, settings={"--dna": True, "--wnone": True})["map"] == [1, 2, 3, 4]
    assert calc.reconstruct_alimask_model_map(legacy, settings={"--hand": True})["map"] == [1, 2, 3, 4]
    assert "input_decoding" not in legacy


def test_new_saved_recalculation_never_reopens_probe_decoder_or_source(monkeypatch):
    sheet = sheet_for((ORACLE / "afa_auto_rna.input").read_bytes(), "afa", mode="alignment_to_model",
        **{"--fast": True, "--wnone": True})
    expected = worker.recalculate_hmmer_preparation(sheet, parameters={})
    original = deepcopy(sheet)
    def forbidden(*args, **kwargs):
        pytest.fail("saved recalculation reopened native input")
    with monkeypatch.context() as guard:
        for name in ("read_hmmer_alignment_input", "read_hmmer_alignment_output", "infer_hmmer_alignment_alphabet",
                     "decode_native_fasta_alignment", "decode_native_block_alignment", "decode_native_phylip_alignment"):
            guard.setattr(data, name, forbidden)
        guard.setattr(Path, "read_bytes", forbidden)
        guard.setattr(Path, "open", forbidden)
        assert worker.recalculate_hmmer_preparation(json.loads(json.dumps(sheet)), parameters={}) == expected
    assert sheet == original


def test_overwritten_mm_byte_qualification_does_not_poison_effective_mask():
    content = annotated_selex("MM", b"\xff")
    line = next(line for line in content.splitlines(keepends=True) if line.startswith(b"#=MM"))
    content = content.replace(line, line + b"#=MM        mmmmmmm.mmmm.mmmmmm\n", 1)
    record = source_record(content, "selex", "RNA")["records"][0]
    effective = record["column_annotations"]["MM"]
    assert effective["valid"] is True
    assert b"\xff" not in effective["text"].encode("utf-8", errors="surrogateescape")
    assert b"\xff" in b"".join(event["raw"].encode("utf-8", errors="surrogateescape") for event in record["original_events"])
    masked, state = calc._mm(record, absent_is_empty=True)
    assert state == "present" and len(masked) == 17
    assert not any(problem["code"] == "annotation_byte_interpretation_unavailable" and problem["field"] == "MM" for problem in record["issues"])
