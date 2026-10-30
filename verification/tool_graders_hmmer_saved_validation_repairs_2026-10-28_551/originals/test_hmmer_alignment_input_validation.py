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


def _sheet(content, fmt="afa", *, alphabet=None, output=None, outformat="stockholm"):
    from gene_annotation_episode.hmmer_alignment_preparation_data import populate_hmmer_alignment_preparation_sheet
    source = _occurrence(content)
    settings = {"--informat": fmt, "--outformat": outformat, "--alirange": "1..1"}
    if alphabet is not None:
        settings[{"DNA": "--dna", "RNA": "--rna", "amino": "--amino"}[alphabet]] = True
    outputs, formats = {}, {source["occurrence_id"]: fmt}
    if output is not None:
        target = _occurrence(output, direction="output", role="masked_alignment", oid="selected-output")
        outputs["masked_alignment"] = [{"occurrence": target, "content": output}]
        formats[target["occurrence_id"]] = outformat
    sheet = populate_hmmer_alignment_preparation_sheet(
        operation={"program": "alimask", "mode": "mask_alignment", "engine_version": "3.4", "settings": settings},
        inputs={"alignment": [{"occurrence": source, "content": content}]}, outputs=outputs,
    )
    return sheet, formats


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
