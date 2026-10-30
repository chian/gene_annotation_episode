"""Saved-input consistency tests, authored for root's bounded test lifecycle.

Packet 545 pins unchanged retained source bytes and already recorded pure
decoder/probe results.  Additional diagnostic mutations are engineering cases,
not new native measurements.  Tests never supply a competing B1 adapter or
numerical implementation; cross-schema examples call the frozen data ports.
"""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from gene_annotation_episode.hmmer_alignment_input_alphabet import (
    classify_easel_alphabet_counts,
    infer_hmmer_alignment_alphabet,
)
from gene_annotation_episode.hmmer_alignment_input_blocks import decode_native_block_alignment
from gene_annotation_episode.hmmer_alignment_input_fasta import decode_native_fasta_alignment
from gene_annotation_episode.hmmer_alignment_input_phylip import decode_native_phylip_alignment
from gene_annotation_episode.hmmer_alignment_input_types import alignment_input_diagnostic
from gene_annotation_episode.hmmer_alignment_input_validation import (
    alphabet_probe_valid,
    input_decoding_local_valid,
    input_decoding_valid,
    native_alignment_batch_valid,
    saved_alignment_decoding_valid,
)


_REPO = Path(__file__).resolve().parents[1]
_PACKET = _REPO / "verification/tool_graders_hmmer_saved_input_validation_2026-10-28_545"
_CASES = json.loads((_PACKET / "FIXTURES.json").read_text())["cases"]
_INDEX = {c["id"]: c for c in _CASES}


def _pinned(pin):
    value = (_REPO / pin["path"]).read_bytes()
    assert len(value) == pin["size_bytes"]
    assert hashlib.sha256(value).hexdigest() == pin["sha256"]
    return value


def _case(case_id):
    case = _INDEX[case_id]
    content = _pinned(case["content"])
    result = json.loads(_pinned(case["result"])) if "result" in case else None
    return content, result


def _decode(content, fmt, alphabet="DNA"):
    decoder = (decode_native_fasta_alignment if fmt in {"afa", "a2m"} else
               decode_native_phylip_alignment if fmt in {"phylip", "phylips"} else
               decode_native_block_alignment)
    return decoder(content, declared_format=fmt, alphabet=alphabet)


def _occurrence(content, *, direction="input", role="alignment", oid="selected-input"):
    return {"occurrence_id": oid, "direction": direction, "role": role, "ordinal": 0,
            "artifact_ref": "retained-" + oid, "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content), "completeness": "complete"}


def _read(content, fmt="afa", alphabet=None):
    from gene_annotation_episode.hmmer_alignment_preparation_data import read_hmmer_alignment_input
    occurrence = _occurrence(content)
    result = read_hmmer_alignment_input(content, declared_format=fmt, occurrence=occurrence,
                                        explicit_alphabet=alphabet, engine_version="3.4")
    settings = {"--informat": fmt}
    if alphabet is not None:
        settings[{"DNA": "--dna", "RNA": "--rna", "amino": "--amino"}[alphabet]] = True
    return result, occurrence, settings


def _sheet(content, fmt="afa", *, alphabet=None, output=None, outformat="stockholm",
           settings_overrides=None, map_reconstruction_context=None):
    from gene_annotation_episode.hmmer_alignment_preparation_data import populate_hmmer_alignment_preparation_sheet
    source = _occurrence(content)
    settings = {"--informat": fmt, "--outformat": outformat, "--alirange": "1..1"}
    if alphabet is not None:
        settings[{"DNA": "--dna", "RNA": "--rna", "amino": "--amino"}[alphabet]] = True
    settings.update(settings_overrides or {})
    outputs, formats = {}, {source["occurrence_id"]: fmt}
    if output is not None:
        target = _occurrence(output, direction="output", role="masked_alignment", oid="selected-output")
        outputs["masked_alignment"] = [{"occurrence": target, "content": output}]
        formats[target["occurrence_id"]] = outformat
    sheet = populate_hmmer_alignment_preparation_sheet(
        operation={"program": "alimask", "mode": "mask_alignment", "engine_version": "3.4", "settings": settings},
        inputs={"alignment": [{"occurrence": source, "content": content}]}, outputs=outputs,
        map_reconstruction_context=map_reconstruction_context,
    )
    return sheet, formats


def _population_for(sheet, oid):
    return next(row for row in sheet["native_rows"]
                if row["kind"] == "population" and row["occurrence_id"] == oid)


def _saved_components(sheet, formats):
    from gene_annotation_episode.hmmer_alignment_preparation_calculations import (
        calculate_hmmer_alignment_preparation_components,
    )
    saved = json.loads(json.dumps(sheet))
    before = deepcopy(saved)
    module = "gene_annotation_episode.hmmer_alignment_preparation_data."
    with patch(module + "infer_hmmer_alignment_alphabet", side_effect=AssertionError("saved source probe")), \
            patch(module + "read_hmmer_alignment_input", side_effect=AssertionError("saved input read")), \
            patch(module + "read_hmmer_alignment_output", side_effect=AssertionError("saved output read")):
        assert saved_alignment_decoding_valid(saved, formats=formats)
        result = calculate_hmmer_alignment_preparation_components(saved)
    assert saved == before
    assert not any(problem["code"] == "sheet_invalid" for problem in result["issues"])
    assert len(result["rows"]) == 1
    return result["rows"][0]["components"]


def _assert_saved_rejected(sheet, formats):
    from gene_annotation_episode.hmmer_alignment_preparation_calculations import (
        calculate_hmmer_alignment_preparation_components,
    )
    assert not saved_alignment_decoding_valid(sheet, formats=formats)
    result = calculate_hmmer_alignment_preparation_components(sheet)
    assert result["rows"] == []
    assert any(problem["code"] == "sheet_invalid" for problem in result["issues"])


@pytest.mark.parametrize("case", [c for c in _CASES if c["kind"] in {"probe", "open_probe"}], ids=lambda c: c["id"])
def test_retained_scanner_probes(case):
    content, probe = _case(case["id"])
    original = deepcopy(probe)
    assert alphabet_probe_valid(probe, declared_format=case["format"], source_size_bytes=len(content))
    assert alphabet_probe_valid(probe, declared_format=case["format"])
    assert probe == original


@pytest.mark.parametrize("case", [c for c in _CASES if c["kind"] in {"batch", "decode"}], ids=lambda c: c["id"])
def test_retained_native_batches_and_initial_byte_validation(case):
    content, batch = _case(case["id"])
    if batch is None:
        batch = _decode(content, case["format"], case["alphabet"])
    original = deepcopy(batch)
    assert native_alignment_batch_valid(batch, source_size_bytes=len(content), content=content)
    assert native_alignment_batch_valid(batch, source_size_bytes=len(content))
    assert batch == original


@pytest.mark.parametrize("mutate", [
    lambda p: p["counts_az"].__setitem__(0, -1),
    lambda p: p["counts_az"].__setitem__(0, True),
    lambda p: p.__setitem__("counted_letters", p["counted_letters"] + 1),
    lambda p: p.__setitem__("scan_end_byte", 0),
    lambda p: p.__setitem__("format", "selex"),
    lambda p: p["checkpoints"][0].__setitem__("threshold", 5000),
    lambda p: p["checkpoints"][0].__setitem__("line", True),
    lambda p: p["checkpoints"][0].__setitem__("byte_end", 1),
    lambda p: p["checkpoints"][0].__setitem__("at_eof", True),
    lambda p: p["checkpoints"][0].__setitem__("rule", "aa_only_letter"),
    lambda p: p["checkpoints"].reverse(),
    lambda p: p.__setitem__("stopped_at", "checkpoint"),
    lambda p: p.__setitem__("unknown_field", 0),
], ids=["negative", "bool_bin", "sum", "scan", "format", "threshold", "line", "byte_end", "eof",
        "classifier", "reordered", "terminal", "extra"])
def test_probe_tampering_rejects_without_mutation(mutate):
    content, probe = _case("probe_afa_above5000")
    mutate(probe)
    before = deepcopy(probe)
    assert not alphabet_probe_valid(probe, declared_format="afa", source_size_bytes=len(content))
    assert probe == before


def test_first_success_and_eof_file_bound_are_distinct_from_local_validation():
    content, probe = _case("probe_afa_first_checkpoint_stops")
    bad = deepcopy(probe)
    second = deepcopy(bad["checkpoints"][0])
    second.update(at_eof=True, threshold=None)
    bad["checkpoints"].append(second)
    assert not alphabet_probe_valid(bad, declared_format="afa", source_size_bytes=len(content))
    content, probe = _case("open_probe_afa_auto_dna")
    assert alphabet_probe_valid(probe, declared_format="afa")
    assert not alphabet_probe_valid(probe, declared_format="afa", source_size_bytes=len(content) + 1)


def test_probe_validation_uses_the_one_existing_classifier():
    content, probe = _case("probe_afa_above5000")
    with patch("gene_annotation_episode.hmmer_alignment_input_validation.classify_easel_alphabet_counts",
               wraps=classify_easel_alphabet_counts) as classifier:
        assert alphabet_probe_valid(probe, declared_format="afa", source_size_bytes=len(content))
    assert classifier.call_count == len(probe["checkpoints"])
    assert [call.args[0] for call in classifier.call_args_list] == [c["counts_az"] for c in probe["checkpoints"]]


def _domain_probe(letter, count, *, fmt, scanner=False):
    counts = [0] * 26
    counts[ord(letter) - 65] = count
    classified = classify_easel_alphabet_counts(counts)
    probe = {"version": "hmmer_native_alignment_alphabet_probe_v1", "format": fmt,
             "state": classified["status"], "alphabet": classified["alphabet"], "counts_az": counts,
             "counted_letters": count, "scan_end_byte": count, "checkpoints": [],
             "stopped_at": "checkpoint", "diagnostics": []}
    if scanner:
        probe.update(state="source_semantics_unestablished", alphabet=None,
                     stopped_at="unestablished_count_semantics", diagnostics=[alignment_input_diagnostic(
                         "native_source_semantics_unestablished", byte_start=0, byte_end=count,
                         expected=9223372036854775807 if fmt in {"phylip", "phylips"} else 2147483647,
                         actual=count)])
    else:
        probe["checkpoints"] = [{"threshold": 500, "at_eof": False, "line": 1, "byte_end": count,
                                 "counts_az": counts.copy(), "state": classified["status"],
                                 "alphabet": classified["alphabet"], "rule": classified["rule"]}]
        if classified["status"] == "source_semantics_unestablished":
            probe.update(stopped_at="unestablished_count_semantics", diagnostics=[alignment_input_diagnostic(
                "native_source_semantics_unestablished", expected=2147483647, actual=count,
                token_hex=letter.encode("ascii").hex())])
        elif classified["status"] == "undetermined":
            probe["stopped_at"] = "eof"
            probe["checkpoints"].append({**deepcopy(probe["checkpoints"][0]), "threshold": None, "at_eof": True})
    return probe


@pytest.mark.parametrize("letter,fmt,count,scanner", [
    ("N", "afa", 2147483648, True), ("B", "afa", 2147483648, True),
    ("N", "phylip", 2147483648, False), ("B", "phylip", 2147483648, False),
    ("A", "phylip", 2147483648, False), ("E", "phylips", 2147483648, False),
    ("N", "phylip", 9223372036854775808, True),
])
def test_source_integer_domains_without_allocating_native_size_input(letter, fmt, count, scanner):
    probe = _domain_probe(letter, count, fmt=fmt, scanner=scanner)
    assert alphabet_probe_valid(probe, declared_format=fmt, source_size_bytes=count)
    if probe["diagnostics"]:
        probe["diagnostics"][0]["details"]["actual"] += 1
        assert not alphabet_probe_valid(probe, declared_format=fmt, source_size_bytes=count)


def test_byte_semantics_retains_whole_physical_line_and_prior_counts():
    content = b">first\n" + b"B" * 501 + b"\n>second\nAA\xffsuffix\n"
    probe = infer_hmmer_alignment_alphabet(content, declared_format="afa")
    assert probe["stopped_at"] == "unestablished_byte_semantics"
    assert probe["scan_end_byte"] == len(content)
    assert alphabet_probe_valid(probe, declared_format="afa", source_size_bytes=len(content))
    probe["diagnostics"][0]["details"]["token_hex"] = "7f"
    assert not alphabet_probe_valid(probe, declared_format="afa", source_size_bytes=len(content))


@pytest.mark.parametrize("mutate", [
    lambda b: b["records"][0].__setitem__("record_ordinal", True),
    lambda b: b["records"][0]["events"][0].__setitem__("raw", ">changed\n"),
    lambda b: b["records"][0]["events"][0]["locator"].__setitem__("line", 0),
    lambda b: b["records"][0]["rows"][0].__setitem__("name_bytes_hex", "00"),
    lambda b: b["records"][0]["rows"][0]["segments"][0].__setitem__("source_text", "!"),
    lambda b: b["records"][0]["rows"][0]["segments"][0].__setitem__("column_start", 999),
    lambda b: b["records"][0]["rows"][0]["segments"][0].__setitem__("aligned_start", 1),
    lambda b: b["records"][0]["rows"][0].__setitem__("geometry_valid", 1),
    lambda b: b.__setitem__("next_byte_offset", 0),
], ids=["ordinal", "raw", "line", "name", "source_slice", "physical_span", "aligned_span", "bool_flag", "cursor"])
def test_native_record_tampering_rejects(mutate):
    content, batch = _case("batch_retained_insertion_a2m")
    mutate(batch)
    assert not native_alignment_batch_valid(batch, source_size_bytes=len(content), content=content)


def test_generated_gaps_have_no_source_and_annotation_fragments_are_original():
    content, batch = _case("batch_retained_insertion_a2m")
    gap = next(s for r in batch["records"][0]["rows"] for s in r["segments"] if s["operation"] == "native_gap")
    gap["byte_start"] = 0
    assert not native_alignment_batch_valid(batch, source_size_bytes=len(content))
    content, _ = _case("decode_selex_mm_overwrite")
    batch = _decode(content, "selex")
    assert native_alignment_batch_valid(batch, source_size_bytes=len(content), content=content)
    fragment = batch["records"][0]["column_annotations"]["MM"]["fragments"][0]
    fragment["value"] = "tampered"
    assert not native_alignment_batch_valid(batch, source_size_bytes=len(content))


def test_aliases_cannot_be_relabeled_as_copies():
    content, batch = _case("batch_afa_nul_dna")
    segment = next(s for r in batch["records"][0]["rows"] for s in r["segments"] if s["operation"] == "symbol_alias")
    segment["decoded_text"] = "X" * len(segment["decoded_text"])
    assert not native_alignment_batch_valid(batch, source_size_bytes=len(content))


def test_null_a2m_and_native_status_zero_with_invalid_phylips_geometry():
    content, batch = _case("batch_a2m_fewer_consensus")
    assert batch["records"][0]["rows"][0]["aligned_sequence"] is None
    assert native_alignment_batch_valid(batch, source_size_bytes=len(content))
    content, _ = _case("decode_phylips_short_last_eof_safe_prefix")
    batch = _decode(content, "phylips")
    record = batch["records"][0]
    assert record["native_status_equivalent"] == 0 and record["reader_state"] == "invalid"
    assert native_alignment_batch_valid(batch, source_size_bytes=len(content), content=content)
    record["reader_state"] = "complete"
    for row in record["rows"]:
        row["geometry_valid"] = True
    assert not native_alignment_batch_valid(batch, source_size_bytes=len(content))


@pytest.mark.parametrize("tag", ["RF", "MM", "CS", "SS", "SA"])
@pytest.mark.parametrize("byte", [b"\x00", b"\xff", b"\xc3\xa9"])
def test_qualified_annotation_bytes_preserve_valid_rows(tag, byte):
    # Separately authored diagnostic bytes; these are not a native observation.
    annotation = b"#=" + tag.encode("ascii") + b"  x" + byte + b"x\n"
    width = 2 + len(byte)
    row = b"first A" + b"C" * (width - 1) + b"\n"
    content = row + annotation if tag in {"SS", "SA"} else annotation + row
    batch = _decode(content, "selex")
    record = batch["records"][0]
    assert record["reader_state"] == "complete" and record["native_status_equivalent"] == 0
    assert native_alignment_batch_valid(batch, source_size_bytes=len(content), content=content)
    annotations = record["rows"][0]["column_annotations"] if tag in {"SS", "SA"} else record["column_annotations"]
    item = annotations["SS_cons" if tag == "CS" else tag]
    assert item["valid"] is False and byte in item["text"].encode("utf-8", "surrogateescape")
    item["valid"] = True
    assert not native_alignment_batch_valid(batch, source_size_bytes=len(content))


def test_selex_reset_cursor_can_overlap_inspected_events():
    content = b"first ACGT\nsecond ACG!\n#=RF  xxxx\n\n"
    batch = _decode(content, "selex")
    assert batch["next_byte_offset"] < batch["records"][0]["byte_end"]
    assert native_alignment_batch_valid(batch, source_size_bytes=len(content), content=content)
    batch["trailing_range"]["byte_start"] += 1
    assert not native_alignment_batch_valid(batch, source_size_bytes=len(content))


def test_local_context_does_not_claim_actual_source_custody():
    content, _ = _case("batch_afa_auto_dna")
    result, occurrence, settings = _read(content)
    context, records = result["input_decoding"], result["records"]
    assert input_decoding_local_valid(context, alignment=records[0], settings=settings)
    assert input_decoding_valid(context, source_occurrence=occurrence, declared_format="afa", settings=settings, records=records)
    changed = deepcopy(occurrence)
    changed["size_bytes"] += 1
    assert input_decoding_local_valid(context, alignment=records[0], settings=settings)
    assert not input_decoding_valid(context, source_occurrence=changed, declared_format="afa", settings=settings, records=records)
    changed = deepcopy(occurrence)
    changed["sha256"] = "0" * 64
    assert not input_decoding_valid(context, source_occurrence=changed, declared_format="afa", settings=settings, records=records)


@pytest.mark.parametrize("change", [
    {"reader_profile": "future_registry_profile"}, {"source_sha256": "A" * 64},
    {"format": "selex"}, {"first_record_end_byte": True}, {"effective_alphabet": "RNA"},
    {"alphabet_basis": "explicit_flag"}, {"reader_state": "invalid"},
])
def test_saved_context_tampering_and_registry_independence(change):
    content, _ = _case("batch_afa_auto_dna")
    sheet, formats = _sheet(content)
    assert saved_alignment_decoding_valid(sheet, formats=formats)
    sheet["input_records"][0]["input_decoding"].update(change)
    assert not saved_alignment_decoding_valid(sheet, formats=formats)


def test_explicit_disagreement_and_b1_native_copy_conflict():
    content, _ = _case("batch_afa_auto_dna")
    sheet, formats = _sheet(content, alphabet="DNA")
    assert saved_alignment_decoding_valid(sheet, formats=formats)
    original = deepcopy(sheet)
    sheet["operation"]["settings"]["--rna"] = True
    assert not saved_alignment_decoding_valid(sheet, formats=formats)
    sheet = original
    sheet["input_records"][0]["rows"][0]["aligned_sequence"] = "X" * 12
    assert not saved_alignment_decoding_valid(sheet, formats=formats)


def test_zero_decoded_and_unperformed_decoding_remain_distinct():
    inferred, formats = _sheet(b"")
    explicit, explicit_formats = _sheet(b"", alphabet="DNA")
    assert saved_alignment_decoding_valid(inferred, formats=formats)
    assert saved_alignment_decoding_valid(explicit, formats=explicit_formats)
    assert inferred["native_rows"][0]["decoded_count"] is None
    assert explicit["native_rows"][0]["decoded_count"] == 0
    assert inferred["issues"][0]["details"]["native_decoding"] is None
    inferred["native_rows"][0]["decoded_count"] = 0
    assert not saved_alignment_decoding_valid(inferred, formats=formats)


def test_source_output_handoff_and_forbidden_direction_metadata():
    content, _ = _case("batch_afa_auto_dna")
    sheet, formats = _sheet(content, output=content, outformat="afa")
    assert saved_alignment_decoding_valid(sheet, formats=formats)
    original = deepcopy(sheet)
    sheet["output_records"][0]["source_alphabet"]["source_sha256"] = "0" * 64
    assert not saved_alignment_decoding_valid(sheet, formats=formats)
    sheet = deepcopy(original)
    sheet["output_records"][0]["input_decoding"] = sheet["input_records"][0]["input_decoding"]
    assert not saved_alignment_decoding_valid(sheet, formats=formats)
    sheet = deepcopy(original)
    sheet["input_records"][0]["source_alphabet"] = sheet["output_records"][0]["source_alphabet"]
    assert not saved_alignment_decoding_valid(sheet, formats=formats)
    sheet = deepcopy(original)
    sheet["output_records"][0]["kind"] = "model"
    assert not saved_alignment_decoding_valid(sheet, formats=formats)
    wrong_formats = {**formats, "selected-input": "selex"}
    assert not saved_alignment_decoding_valid(original, formats=wrong_formats)


def test_first_record_end_and_whole_source_probe_have_independent_extents():
    first = b"2 12\nfirst     ACGTACGTACGT\nsecond    ACGTACGTACGT\n"
    content = first + b"malformed second record\n"
    result, occurrence, settings = _read(content, "phylip")
    context = result["input_decoding"]
    assert context["first_record_end_byte"] == len(first)
    assert context["alphabet_probe"]["scan_end_byte"] == len(content)
    assert context["reader_state"] == "partial"
    assert input_decoding_valid(context, source_occurrence=occurrence, declared_format="phylip",
                                settings=settings, records=result["records"])
    assert input_decoding_local_valid(context, alignment=result["records"][0], settings=settings)
    result["records"][1]["native_decoding"]["next_byte_offset"] -= 1
    assert not input_decoding_valid(context, source_occurrence=occurrence, declared_format="phylip",
                                    settings=settings, records=result["records"])


def test_duplicate_and_empty_phylip_names_remain_positional():
    content = b"3 4\n          ACGT\nrepeated  ACGT\nrepeated  ACGT\n"
    sheet, formats = _sheet(content, "phylips", alphabet="DNA")
    assert saved_alignment_decoding_valid(sheet, formats=formats)
    rows = sheet["input_records"][0]["rows"]
    assert [row["name"] for row in rows] == ["", "repeated", "repeated"]
    assert [row["occurrence"] for row in rows] == [0, 0, 1]
    rows[2]["occurrence"] = 2
    assert not saved_alignment_decoding_valid(sheet, formats=formats)


@pytest.mark.parametrize("legacy", json.loads((_PACKET / "LEGACY_FIXTURES.json").read_text())["sheets"],
                         ids=lambda item: Path(item["retained"]["path"]).name)
def test_actual_legacy_sheet_is_valid_without_new_facts_or_classifier_calls(legacy):
    pin = legacy["retained"]
    content = _pinned(pin)
    sheet = json.loads(content)
    original = deepcopy(sheet)
    with patch("gene_annotation_episode.hmmer_alignment_input_validation.classify_easel_alphabet_counts",
               side_effect=AssertionError("legacy classification is forbidden")):
        assert saved_alignment_decoding_valid(sheet)
    assert sheet == original
    assert all("input_decoding" not in record for record in sheet["input_records"])


@pytest.mark.parametrize("value", [None, False, 0, "wrong", [], {}, {"counts_az": [False] * 26}])
def test_malformed_public_arguments_return_false(value):
    assert alphabet_probe_valid(value, declared_format="afa") is False
    assert native_alignment_batch_valid(value, source_size_bytes=0) is False
    assert input_decoding_local_valid(value, alignment=None, settings={}) is False
    assert input_decoding_valid(value, source_occurrence={}, declared_format="afa", settings={}, records=[]) is False
    assert saved_alignment_decoding_valid(value) is False


@pytest.mark.parametrize("fmt", ["stockholm", "pfam"])
@pytest.mark.parametrize("direction", ["input", "output"])
@pytest.mark.parametrize("annotation,code", [
    (b"", None),
    (b"#=GS s WT bad\n", "weight_invalid"),
    (b"#=GC MM x...\n", "mm_symbol_invalid"),
    (b"#=GC SS_cons xxx\n", "annotation_geometry_invalid"),
], ids=["clean", "invalid_weight", "invalid_mask_symbol", "annotation_width"])
def test_stockholm_population_qualifications_are_separate_from_decoding(fmt, direction, annotation, code):
    from gene_annotation_episode.hmmer_alignment_preparation_data import read_hmmer_alignment_output, valid_alignment
    # Authored diagnostic fixtures preserve ordinary Stockholm producer handling.
    plain = b"# STOCKHOLM 1.0\ns ACGT\n//\n"
    qualified = b"# STOCKHOLM 1.0\n" + annotation + b"s ACGT\n//\n"
    content, output = (qualified, plain) if direction == "input" else (plain, qualified)
    source, occurrence, settings = _read(content, fmt, "DNA")
    context = source["input_decoding"]
    assert (context["reader_state"], context["file_end_state"]) == ("complete", "eof")
    assert input_decoding_valid(context, source_occurrence=occurrence, declared_format=fmt,
                                settings=settings, records=source["records"])
    target = read_hmmer_alignment_output(output, declared_format=fmt,
        occurrence=_occurrence(output, direction="output", role="masked_alignment", oid="selected-output"),
        source_decoding=context, engine_version="3.4")
    selected = source if direction == "input" else target
    assert valid_alignment(selected["records"][0])
    assert selected["population"]["decoded_count"] == 1
    assert selected["population"]["complete"] is (code is None)
    assert selected["population"]["state"] == ("decoded" if code is None else "partial")
    if code is not None:
        assert code in {problem["code"] for problem in selected["records"][0]["issues"]}
    sheet, formats = _sheet(content, fmt, alphabet="DNA", output=output, outformat=fmt)
    assert sheet["input_records"] == source["records"]
    assert sheet["output_records"] == target["records"]
    oid = "selected-" + direction
    assert _population_for(sheet, oid) == selected["population"]
    cells = _saved_components(sheet, formats)
    assert (cells["input_sequence_count"]["value"], cells["input_column_count"]["value"]) == (1, 4)
    assert cells["input_alignment_count"]["value"] == 1
    assert cells["input_alignment_count"]["state"] == (
        "incomplete" if direction == "input" and code is not None else "present")
    tampered = deepcopy(sheet)
    population = _population_for(tampered, oid)
    population.update(complete=code is not None, state="decoded" if code is not None else "partial")
    _assert_saved_rejected(tampered, formats)


def test_duplicate_native_names_keep_stockholm_output_population_qualification():
    content = b"2 4\nrepeated  ACGT\nrepeated  ACGT\n"
    output = b"# STOCKHOLM 1.0\nrepeated ACGT\nrepeated ACGT\n//\n"
    sheet, formats = _sheet(content, "phylips", alphabet="DNA", output=output)
    assert [row["name"] for row in sheet["input_records"][0]["rows"]] == ["repeated", "repeated"]
    assert "duplicate_sequence_name" in {problem["code"] for problem in sheet["output_records"][0]["issues"]}
    population = _population_for(sheet, "selected-output")
    assert (population["decoded_count"], population["complete"], population["state"]) == (1, False, "partial")
    cells = _saved_components(sheet, formats)
    assert (cells["input_sequence_count"]["value"], cells["input_column_count"]["value"]) == (2, 4)
    population.update(complete=True, state="decoded")
    _assert_saved_rejected(sheet, formats)


@pytest.mark.parametrize("outformat", ["stockholm", "pfam"])
def test_empty_structural_output_without_source_alphabet_is_known_zero(outformat):
    from gene_annotation_episode.hmmer_alignment_preparation_data import read_hmmer_alignment_output
    content = b">s\nACG\n"
    source, _, _ = _read(content)
    assert source["input_decoding"]["effective_alphabet"] is None
    occurrence = _occurrence(b"", direction="output", role="masked_alignment", oid="selected-output")
    output = read_hmmer_alignment_output(b"", declared_format=outformat, occurrence=occurrence,
                                         source_decoding=None, engine_version="3.4")
    assert output == read_hmmer_alignment_output(b"", declared_format=outformat, occurrence=occurrence,
        source_decoding=source["input_decoding"], engine_version="3.4")
    assert output["source_alphabet"] is None and output["records"] == []
    assert output["issues"][-1]["code"] == "alignment_empty"
    assert output["issues"][-1]["details"] == {"context": None, "native_decoding": None}
    sheet, formats = _sheet(content, output=b"", outformat=outformat)
    population = _population_for(sheet, "selected-output")
    assert population == output["population"]
    assert (population["decoded_count"], population["complete"], population["state"]) == (0, True, "decoded")
    assert _population_for(sheet, "selected-input")["decoded_count"] is None
    cells = _saved_components(sheet, formats)
    assert (cells["input_alignment_count"]["value"], cells["input_alignment_count"]["state"]) == (None, "missing")
    population.update(decoded_count=None, complete=False, state="unsupported")
    _assert_saved_rejected(sheet, formats)


def test_empty_native_output_without_source_alphabet_remains_unknown():
    sheet, formats = _sheet(b">s\nACG\n", output=b"", outformat="afa")
    population = _population_for(sheet, "selected-output")
    assert (population["decoded_count"], population["complete"], population["state"]) == (None, False, "unsupported")
    _saved_components(sheet, formats)
    population.update(decoded_count=0, complete=True, state="decoded")
    _assert_saved_rejected(sheet, formats)


@pytest.mark.parametrize("fmt", ["stockholm", "pfam"])
def test_failed_stockholm_text_decode_retains_attempted_zero_population(fmt):
    source, _, _ = _read(b"\xff", fmt, "DNA")
    context = source["input_decoding"]
    assert source["records"] == []
    assert (context["reader_state"], context["file_end_state"], context["first_record_end_byte"]) == (
        "invalid", "parse_error", None)
    assert source["issues"][-1]["code"] == "alignment_decoding_unavailable"
    assert source["issues"][-1]["details"]["native_decoding"] is None
    assert "text_encoding_invalid" in {problem["code"] for problem in source["issues"]}
    sheet, formats = _sheet(b"\xff", fmt, alphabet="DNA")
    population = _population_for(sheet, "selected-input")
    assert population == source["population"]
    assert (population["decoded_count"], population["complete"], population["state"]) == (0, False, "partial")
    cells = _saved_components(sheet, formats)
    assert (cells["input_alignment_count"]["value"], cells["input_alignment_count"]["state"]) == (0, "incomplete")
    for change in ({"decoded_count": None, "state": "unsupported"}, {"complete": True, "state": "decoded"}):
        tampered = deepcopy(sheet)
        _population_for(tampered, "selected-input").update(change)
        _assert_saved_rejected(tampered, formats)
    sheet["issues"] = [problem for problem in sheet["issues"] if problem["code"] != "text_encoding_invalid"]
    _assert_saved_rejected(sheet, formats)


@pytest.mark.parametrize("outformat", ["stockholm", "pfam"])
@pytest.mark.parametrize("source_known", [True, False], ids=["bound_source", "unknown_source"])
def test_failed_stockholm_output_text_decode_retains_attempted_zero(outformat, source_known):
    from gene_annotation_episode.hmmer_alignment_preparation_data import read_hmmer_alignment_output
    content, alphabet = (b">s\nACGT\n", "DNA") if source_known else (b">s\nACG\n", None)
    source, _, _ = _read(content, alphabet=alphabet)
    output = read_hmmer_alignment_output(b"\xff", declared_format=outformat,
        occurrence=_occurrence(b"\xff", direction="output", role="masked_alignment", oid="selected-output"),
        source_decoding=source["input_decoding"], engine_version="3.4")
    assert output["records"] == []
    assert (output["source_alphabet"] is not None) is source_known
    assert output["issues"][-1]["code"] == "alignment_decoding_unavailable"
    assert output["issues"][-1]["details"]["native_decoding"] is None
    sheet, formats = _sheet(content, alphabet=alphabet, output=b"\xff", outformat=outformat)
    population = _population_for(sheet, "selected-output")
    assert population == output["population"]
    assert (population["decoded_count"], population["complete"], population["state"]) == (0, False, "partial")
    cells = _saved_components(sheet, formats)
    assert cells["input_alignment_count"]["value"] == (1 if source_known else None)
    for change in ({"decoded_count": None, "state": "unsupported"}, {"complete": True, "state": "decoded"}):
        tampered = deepcopy(sheet)
        _population_for(tampered, "selected-output").update(change)
        _assert_saved_rejected(tampered, formats)
    sheet["issues"] = [problem for problem in sheet["issues"] if problem["code"] != "text_encoding_invalid"]
    _assert_saved_rejected(sheet, formats)


def test_native_annotation_qualification_does_not_change_population_completeness():
    sheet, formats = _sheet(b"#=RF  x\xffx\nfirst ACG\n", "selex", alphabet="DNA")
    assert "annotation_byte_interpretation_unavailable" in {problem["code"] for problem in sheet["input_records"][0]["issues"]}
    population = _population_for(sheet, "selected-input")
    assert (population["decoded_count"], population["complete"], population["state"]) == (1, True, "decoded")
    cells = _saved_components(sheet, formats)
    assert cells["input_sequence_count"]["value"] == 1
    assert cells["input_column_count"]["value"] == 3
    assert cells["rf_consensus_count"]["value"] is None
    population.update(complete=False, state="partial")
    _assert_saved_rejected(sheet, formats)


def test_later_map_context_issue_does_not_rewrite_stockholm_population():
    from gene_annotation_episode.hmmer_alignment_preparation_calculations import resolve_alimask_map_context
    content = b"# STOCKHOLM 1.0\ns ACGT\n//\n"
    operation = {"program": "alimask", "mode": "mask_alignment", "engine_version": "3.4",
                 "settings": {"--informat": "stockholm", "--outformat": "stockholm", "--dna": True, "--alirange": "1..1"}}
    context = resolve_alimask_map_context(operation=operation,
        software={"executable": "retained-alimask", "expected_sha256": None, "actual_sha256": None,
                  "declared_engine_version": "3.4"}, source_occurrence=_occurrence(content), requested_options=[])
    context["source_sha256"] = "0" * 64
    sheet, formats = _sheet(content, "stockholm", alphabet="DNA", map_reconstruction_context=context)
    assert "map_context_invalid" in {problem["code"] for problem in sheet["input_records"][0]["issues"]}
    assert _population_for(sheet, "selected-input")["complete"] is True
    assert _saved_components(sheet, formats)["input_alignment_count"]["value"] == 1


@pytest.mark.parametrize("fmt,cli,content", [
    ("stockholm", "Stockholm", b"# STOCKHOLM 1.0\ns ACGT\n//\n"),
    ("pfam", "Pfam", b"# STOCKHOLM 1.0\ns ACGT\n//\n"),
    ("afa", "AFA", b">s\nACGT\n"),
    ("a2m", "A2M", b">s\nACGT\n"),
    ("clustal", "Clustal", b"CLUSTAL W multiple sequence alignment\n\ns ACGT\n      \n"),
    ("phylip", "PHYLIP", b"1 4\ns         ACGT\n"),
], ids=["Stockholm", "Pfam", "AFA", "A2M", "Clustal", "PHYLIP"])
def test_native_cli_format_case_is_compared_without_rewriting_settings(fmt, cli, content):
    from gene_annotation_episode.native_hmmer_preparation_contracts import FORMAT_ARGUMENTS
    assert FORMAT_ARGUMENTS[fmt] == cli
    result, occurrence, settings = _read(content, fmt, "DNA")
    settings["--informat"] = cli
    assert input_decoding_local_valid(result["input_decoding"], alignment=result["records"][0], settings=settings)
    assert input_decoding_valid(result["input_decoding"], source_occurrence=occurrence,
                               declared_format=fmt, settings=settings, records=result["records"])
    sheet, formats = _sheet(content, fmt, alphabet="DNA", output=content, outformat=fmt,
                           settings_overrides={"--informat": cli, "--outformat": cli})
    original = deepcopy(sheet)
    assert sheet["input_records"] == result["records"]
    cells = _saved_components(sheet, formats)
    assert (cells["input_sequence_count"]["value"], cells["input_column_count"]["value"]) == (1, 4)
    assert sheet == original
    assert sheet["operation"]["settings"]["--informat"] == cli
    assert sheet["operation"]["settings"]["--outformat"] == cli


@pytest.mark.parametrize("flag", ["--informat", "--outformat"])
@pytest.mark.parametrize("value", [None, False, [], {}, 9, "selex", " AFA", "AFA "],
                         ids=["null", "bool", "list", "dict", "integer", "different_format", "leading_space", "trailing_space"])
def test_format_case_normalization_keeps_malformed_and_conflicting_metadata_invalid(flag, value):
    sheet, formats = _sheet(b">s\nACGT\n", alphabet="DNA", output=b">s\nACGT\n", outformat="afa")
    _saved_components(sheet, formats)
    sheet["operation"]["settings"][flag] = value
    _assert_saved_rejected(sheet, formats)


def test_native_local_context_still_requires_its_declared_format():
    result, _, _ = _read(b">s\nACGT\n", alphabet="DNA")
    assert not input_decoding_local_valid(result["input_decoding"], alignment=result["records"][0],
                                          settings={"--dna": True})
