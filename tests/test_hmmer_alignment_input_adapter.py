"""Frozen542 B1 adapter checks; native fixtures are unchanged retained bytes.

Inline inputs and SELEX diagnostic copies are explicitly authored engineering
cases. No test launches native work or defines a numerical scoring formula.
Execution belongs to root's bounded lifecycle, not the authoring host.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode import hmmer_alignment_preparation_data as data
from gene_annotation_episode.hmmer_alignment_input_fasta import decode_native_fasta_alignment
from gene_annotation_episode.hmmer_alignment_input_blocks import decode_native_block_alignment
from gene_annotation_episode.hmmer_alignment_input_phylip import decode_native_phylip_alignment
from gene_annotation_episode.hmmer_alignment_input_validation import (
    input_decoding_local_valid, saved_alignment_decoding_valid,
)
from gene_annotation_episode.hmmer_alignment_preparation_calculations import (
    calculate_hmmer_alignment_preparation_components, reconstruct_alimask_model_map,
)


ROOT = Path(__file__).resolve().parents[1]
EMISSIONS = ROOT / "verification/tool_graders_infernal_preparation_emission_2026-10-26_250/native"
UPSTREAM = ROOT / "resources/software/infernal-1.1.5/easel/esl_msa_testfiles"
ORACLE = ROOT / "verification/tool_graders_hmmer_input_native_oracle_2026-10-28_539/fixtures"
PACKET = ROOT / "verification/tool_graders_hmmer_input_data_adapter_2026-10-28_546"


def occurrence(content, *, direction="input", role="alignment", ordinal=0):
    return {"occurrence_id": f"{direction}:{role}:{ordinal}", "direction": direction,
        "role": role, "ordinal": ordinal, "artifact_ref": f"retained:{direction}:{role}:{ordinal}",
        "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content), "completeness": "complete"}


def read(content, fmt="afa", alphabet="DNA"):
    return data.read_hmmer_alignment_input(content, declared_format=fmt,
        occurrence=occurrence(content), explicit_alphabet=alphabet, engine_version="3.4")


def sheet(content, fmt="afa", alphabet="DNA", *, output=None, outformat="stockholm"):
    settings = {"--informat": fmt, "--alirange": "1-1", "--outformat": outformat}
    if alphabet is not None:
        settings[{"DNA": "--dna", "RNA": "--rna", "amino": "--amino"}[alphabet]] = True
    outputs = {} if output is None else {"masked_alignment": [{"content": output,
        "occurrence": occurrence(output, direction="output", role="masked_alignment")}]}
    return data.populate_hmmer_alignment_preparation_sheet(
        operation={"program": "alimask", "mode": "mask_alignment", "engine_version": "3.4", "settings": settings},
        inputs={"alignment": [{"content": content, "occurrence": occurrence(content)}]}, outputs=outputs)


def forbidden(*args, **kwargs):
    raise AssertionError("forbidden inference or decoder invocation")


@pytest.mark.parametrize("path,fmt,alphabet,count,width,digest", [
    (EMISSIONS / "a2m_insertions/emitted.out", "a2m", "RNA", 5, 17,
     "4a47f0cd7fad3b309d62e69985932c31b12358e0befa0e78d0d4cb92b7ed22e3"),
    (EMISSIONS / "aligned_clustal/emitted.out", "clustal", "RNA", 3, 12,
     "aacde9e96408bb894a79665ab28dc3c3bbf2a87976123f69052a6f361701821a"),
    (EMISSIONS / "aligned_clustal/emitted.out", "clustallike", "RNA", 3, 12,
     "aacde9e96408bb894a79665ab28dc3c3bbf2a87976123f69052a6f361701821a"),
    (EMISSIONS / "aligned_phylip/emitted.out", "phylip", "RNA", 3, 12,
     "2080aeba7e96b2b39127ae483c66b61ff53394a6e2c696203fff88dcb470d649"),
    (EMISSIONS / "phylip_long_interleaved/emitted.out", "phylip", "RNA", 2, 74,
     "1da160dadc5a685c83856a689d40443a2050aecf1c49188ec3b64ae7473ecc75"),
    (UPSTREAM / "selex/selex.good.4", "selex", "RNA", 11, 31,
     "2c583468c2268306feef69bb9c62cd90e4727738e93a6d24f2d8338ef6fd1d62"),
    (UPSTREAM / "psiblast/psiblast.good.1", "psiblast", "amino", 4, 165,
     "cbd57eab6959a8a9ef8d7de7aff80b1f3eb08e297e02bf9d605382311b68a2e3"),
    (UPSTREAM / "phylips/phylips.good.1", "phylips", "DNA", 5, 42,
     "eb02748583ebb035d1f566eb6b263d9b021886ef20e99ae6fceb1813bc7c12af"),
    (ORACLE / "afa_auto_dna.input", "afa", "DNA", 2, 12,
     "824a8ce36203927eafe75d6c6b8be163c47c07f3423f588d5f434bd0b89af645"),
])
def test_v01_retained_native_operands_share_b1_enrichment_and_calculator(path, fmt, alphabet, count, width, digest):
    content = path.read_bytes()
    assert hashlib.sha256(content).hexdigest() == digest
    parsed = read(content, fmt, alphabet)
    decoder = (decode_native_fasta_alignment if fmt in {"afa", "a2m"} else
        decode_native_phylip_alignment if fmt in {"phylip", "phylips"} else decode_native_block_alignment)
    native = decoder(content, declared_format=fmt, alphabet=alphabet)
    record = parsed["records"][0]
    assert {**record["native_decoding"], "records": [r["native_input"] for r in parsed["records"]]} == native
    assert set(parsed) == {"version", "input_decoding", "records", "population", "issues"}
    assert parsed["population"]["decoded_count"] == 1 and parsed["population"]["complete"]
    assert len(record["rows"]) == count and record["column_count"] == width
    assert data.gf_value(record, "ID") is None
    assert record["original_events"] == native["records"][0]["events"]
    for ordinal, row in enumerate(record["rows"]):
        source = native["records"][0]["rows"][ordinal]
        assert row["row_index"] == row["row_ordinal"] == ordinal
        for field in ("name", "name_bytes_hex", "description", "aligned_sequence", "segments", "annotation_fragments", "column_annotations"):
            assert row[field] == source[field]
        assert row["fragments"] == [e for e in record["original_events"] if e["kind"] == "sequence" and e["row_ordinal"] == ordinal]
        assert row["weight"] == {"value": None, "state": "missing", "events": []}
        assert row["sequence_annotations"] == [] and row["sequence_annotations_joined"]
    if path.parent.name == "aligned_phylip":
        assert [r["name"] for r in record["rows"]] == ["fixture246"] * 3
        assert [r["occurrence"] for r in record["rows"]] == [0, 1, 2]
        assert "duplicate_sequence_name" not in {p["code"] for p in parsed["issues"]}
    if fmt == "a2m":
        assert data.annotation(record, "RF") == "xx.xxx.xxx..xxx.x"
        assert any(s["operation"] == "native_gap" for row in record["rows"] for s in row["segments"])
    populated = sheet(content, fmt, alphabet)
    assert len(populated) == 9 and saved_alignment_decoding_valid(populated)
    components = calculate_hmmer_alignment_preparation_components(populated)["rows"][0]["components"]
    assert components["input_sequence_count"]["value"] == count
    assert components["input_column_count"]["value"] == width
    # Already-decoded equivalent rows go through the same original B1 calculator.
    sto = b"# STOCKHOLM 1.0\n" + b"".join(
        f"row{i} {r['aligned_sequence']}\n".encode() for i, r in enumerate(record["rows"])) + b"//\n"
    equivalent = calculate_hmmer_alignment_preparation_components(sheet(sto, "stockholm", alphabet))["rows"][0]["components"]
    for field in ("input_sequence_count", "input_column_count"):
        assert (components[field]["value"], components[field]["unit"]) == (equivalent[field]["value"], equivalent[field]["unit"])


@pytest.mark.parametrize("name,fmt,expected", [
    ("a2m_auto_pre_map_O.input", "a2m", "amino"), ("afa_auto_rna.input", "afa", "RNA"),
])
def test_v02_inference_once_from_original_bytes_and_output_handoff(monkeypatch, name, fmt, expected):
    content = (ORACLE / name).read_bytes()
    original = data.infer_hmmer_alignment_alphabet
    calls = []
    def observe(value, *, declared_format):
        calls.append((value, declared_format))
        return original(value, declared_format=declared_format)
    monkeypatch.setattr(data, "infer_hmmer_alignment_alphabet", observe)
    parsed = read(content, fmt, None)
    assert calls == [(content, fmt)]
    context = parsed["input_decoding"]
    assert context["effective_alphabet"] == expected
    if fmt == "a2m":
        assert context["alphabet_probe"]["counts_az"][ord("O") - 65] == 4
        assert all("O" not in r["aligned_sequence"] for r in parsed["records"][0]["rows"])
    target = (ORACLE / "afa_auto_dna.input").read_bytes()
    monkeypatch.setattr(data, "infer_hmmer_alignment_alphabet", forbidden)
    output = data.read_hmmer_alignment_output(target, declared_format="afa",
        occurrence=occurrence(target, direction="output", role="masked_alignment"),
        source_decoding=context, engine_version="3.4")
    assert set(output) == {"version", "source_alphabet", "records", "population", "issues"}
    assert output["source_alphabet"] == {"version": "hmmer_alignment_source_alphabet_v1",
        "source_occurrence_id": context["source_occurrence_id"], "source_sha256": context["source_sha256"],
        "alphabet": expected, "alphabet_basis": "native_source_inference"}
    assert output["records"][0]["native_decoding"]["alphabet"] == expected
    assert all("input_decoding" not in r and "alphabet_probe" not in r for r in output["records"])
    explicit = read(content, fmt, expected)
    assert explicit["input_decoding"]["alphabet_probe"] is None


def test_v02_populator_carries_original_source_context_once(monkeypatch):
    content = (ORACLE / "afa_auto_rna.input").read_bytes()
    original = data.infer_hmmer_alignment_alphabet
    calls = []
    def observe(value, *, declared_format):
        calls.append((value, declared_format))
        return original(value, declared_format=declared_format)
    monkeypatch.setattr(data, "infer_hmmer_alignment_alphabet", observe)
    result = sheet(content, alphabet=None, output=content, outformat="afa")
    assert calls == [(content, "afa")]
    assert result["output_records"][0]["source_alphabet"]["source_sha256"] == hashlib.sha256(content).hexdigest()
    assert saved_alignment_decoding_valid(result)


@pytest.mark.parametrize("content,fmt", [
    (b"", "afa"), (b" \t\r\n", "afa"), (b">a\nACGT\n", "afa"),
    (b"# STOCKHOLM 1.0\na AC\n//\n", "stockholm"),
])
def test_v03_unknown_alphabet_never_runs_placeholder_reader(monkeypatch, content, fmt):
    monkeypatch.setattr(data, "_decoded_alignment_records", forbidden)
    result = read(content, fmt, None)
    assert result["records"] == [] and result["population"]["decoded_count"] is None
    assert result["input_decoding"]["reader_state"] == "unavailable"
    assert result["input_decoding"]["file_end_state"] == "alphabet_undetermined"
    assert result["issues"][0]["code"] == "alignment_decoding_unavailable"
    assert set(result["issues"][0]["details"]) == {"context", "native_decoding"}
    assert input_decoding_local_valid(result["input_decoding"], alignment=None, settings={"--informat": fmt})


def test_v03_known_zero_and_a2m_null_geometry_are_distinct():
    empty = read((ORACLE / "afa_empty_file.input").read_bytes())
    assert empty["records"] == [] and empty["population"]["decoded_count"] == 0
    assert empty["population"]["complete"] and empty["input_decoding"]["reader_state"] == "complete"
    assert empty["input_decoding"]["first_record_end_byte"] is None
    assert [i["code"] for i in empty["issues"]] == ["alignment_empty"]
    failed = read((ORACLE / "a2m_fewer_consensus.input").read_bytes(), "a2m")
    assert failed["input_decoding"]["reader_state"] == "invalid"
    assert failed["population"]["decoded_count"] == 1 and not failed["population"]["complete"]
    assert all(r["aligned_sequence"] is None and r["segments"] == [] for r in failed["records"][0]["rows"])
    assert not data.valid_alignment(failed["records"][0])
    assert saved_alignment_decoding_valid(sheet((ORACLE / "a2m_fewer_consensus.input").read_bytes(), "a2m"))


def test_v03_present_invalid_context_does_not_fall_back_and_legacy_absence_does():
    record = read((ORACLE / "afa_auto_dna.input").read_bytes())["records"][0]
    assert data.effective_hmmer_alignment_alphabet(record, settings={"--informat": "afa", "--dna": True})["alphabet"] == "DNA"
    for value in (None, {}, {**record["input_decoding"], "reader_profile": "unrecognized"}):
        changed = {**record, "input_decoding": value}
        assert data.effective_hmmer_alignment_alphabet(changed, settings={"--informat": "afa", "--dna": True}) == {
            "state": "incompatible", "alphabet": None, "basis": None, "issue_code": "input_decoding_invalid"}
    assert data.effective_hmmer_alignment_alphabet(record, settings={"--informat": "afa", "--rna": True})["state"] == "incompatible"
    legacy = {k: v for k, v in record.items() if k not in {"input_decoding", "native_input", "native_decoding"}}
    before = deepcopy(legacy)
    assert data.effective_hmmer_alignment_alphabet(legacy, settings={})["issue_code"] == "alphabet_missing"
    assert data.effective_hmmer_alignment_alphabet(legacy, settings={"--amino": True})["alphabet"] == "amino"
    assert legacy == before


@pytest.mark.parametrize("field,value,code", [("sha256", "0" * 64, "occurrence_digest_mismatch"),
                                             ("size_bytes", 999, "occurrence_size_mismatch")])
def test_v03_unbound_bytes_gain_no_authenticated_context(monkeypatch, field, value, code):
    content = (ORACLE / "afa_auto_dna.input").read_bytes()
    selected = occurrence(content)
    selected[field] = value
    monkeypatch.setattr(data, "infer_hmmer_alignment_alphabet", forbidden)
    result = data.read_hmmer_alignment_input(content, declared_format="afa", occurrence=selected,
        explicit_alphabet=None, engine_version="3.4")
    assert result["input_decoding"] is None and result["records"] == []
    assert result["population"]["decoded_count"] is None and code in {i["code"] for i in result["issues"]}


def test_v03_multiple_selected_alphabets_stop_before_probe_or_decoder(monkeypatch):
    monkeypatch.setattr(data, "infer_hmmer_alignment_alphabet", forbidden)
    monkeypatch.setattr(data, "_decoded_alignment_records", forbidden)
    result = data.populate_hmmer_alignment_preparation_sheet(operation={"program": "alimask",
        "mode": "mask_alignment", "engine_version": "3.4", "settings": {"--amino": True, "--dna": True}},
        inputs={}, outputs={})
    assert [i["code"] for i in result["issues"]] == ["operation_invalid"]


def test_v03_output_missing_handoff_and_malformed_present_handoff():
    content = b">a\nACGT\n"
    args = {"declared_format": "afa", "occurrence": occurrence(content, direction="output", role="masked_alignment"),
            "engine_version": "3.4"}
    result = data.read_hmmer_alignment_output(content, source_decoding=None, **args)
    assert result["source_alphabet"] is None and result["population"]["decoded_count"] is None
    assert result["issues"][0]["code"] == "alignment_decoding_unavailable"
    with pytest.raises(ValueError, match="^hmmer_alignment_source_decoding_invalid$"):
        data.read_hmmer_alignment_output(content, source_decoding={}, **args)
    sto = b"# STOCKHOLM 1.0\na AC\n//\n"
    structural = data.read_hmmer_alignment_output(sto, declared_format="stockholm",
        occurrence=occurrence(sto, direction="output", role="masked_alignment"), source_decoding=None, engine_version="3.4")
    assert data.valid_alignment(structural["records"][0]) and structural["source_alphabet"] is None
    assert "source_alphabet" not in structural["records"][0]


def test_v05_aliases_empty_names_and_header_only_rows_preserve_positions():
    content = b"3 3\n          A?O\n          GCO\nwith spaceACT\n"
    result = read(content, "phylip")
    rows = result["records"][0]["rows"]
    assert [r["name"] for r in rows] == ["", "", "with_space"]
    assert [r["occurrence"] for r in rows] == [0, 1, 0]
    assert rows[0]["aligned_sequence"] == "A~-"
    assert not result["issues"]
    assert [s["source_text"] for s in rows[0]["segments"] if s["operation"] == "symbol_alias"] == ["?O"]
    header = read(b">header_only\n")["records"][0]["rows"][0]
    assert header["fragments"] == []
    assert (header["locator"]["byte_start"], header["locator"]["byte_end"]) == (0, len(b">header_only\n"))


@pytest.mark.parametrize("mutation", ["row_copy", "event_raw", "name_hex", "segment_span", "gap_source"])
def test_v05_saved_operand_tampering_is_rejected(mutation):
    content = (EMISSIONS / "a2m_insertions/emitted.out").read_bytes()
    result = sheet(content, "a2m", "RNA")
    assert saved_alignment_decoding_valid(result)
    record = result["input_records"][0]
    if mutation == "row_copy":
        record["rows"][0]["aligned_sequence"] = "X" * record["column_count"]
    elif mutation == "event_raw":
        record["original_events"][0]["raw"] += "\n"
    elif mutation == "name_hex":
        record["rows"][0]["name_bytes_hex"] = "00"
    elif mutation == "segment_span":
        record["rows"][0]["segments"][0]["aligned_end"] += 1
    else:
        gap = next(s for row in record["rows"] for s in row["segments"] if s["operation"] == "native_gap")
        gap["byte_start"] = 0
    assert not saved_alignment_decoding_valid(result)


def test_v05_selex_reset_overlap_and_native_ok_invalid_phylips_geometry():
    reset = read(b"a AC\n\nb GT\n", "selex")
    record = reset["records"][0]
    assert record["native_decoding"]["next_byte_offset"] < record["locator"]["byte_end"]
    assert record["native_decoding"]["trailing_range"]["byte_start"] == record["native_decoding"]["next_byte_offset"]
    content = b"2 4\na         ACGT\nb         AC\n"
    result = read(content, "phylips")
    record = result["records"][0]
    assert record["native_input"]["native_status_equivalent"] == 0
    assert not data.valid_alignment(record)
    assert [r["aligned_sequence"] for r in record["rows"]] == ["ACGT", "AC"]
    assert result["input_decoding"]["reader_state"] == "invalid"


def test_v06_valid_first_record_and_later_error_keep_independent_probe_extent():
    first = (EMISSIONS / "aligned_phylip/emitted.out").read_bytes()
    # An authored later-record error; retained first-record bytes are unchanged.
    content = first + b"broken\nabcdefghijACGUACGUACGU\n"
    result = read(content, "phylip", None)
    assert len(result["records"]) == 2
    assert data.valid_alignment(result["records"][0]) and not data.valid_alignment(result["records"][1])
    context = result["input_decoding"]
    assert context["reader_state"] == "partial"
    assert context["first_record_end_byte"] == len(first)
    assert context["alphabet_probe"]["scan_end_byte"] == len(content)
    reconstruction = reconstruct_alimask_model_map(result["records"][0], settings={"--informat": "phylip", "--wnone": True})
    assert reconstruction["state"] == "present" and reconstruction["map"] == list(range(1, 13))
    whole_file = read(b">a\nACGT\n>bad\nAC1\ntrailing\n")
    assert len(whole_file["records"]) == 1 and not data.valid_alignment(whole_file["records"][0])


def _annotation_diagnostic_copy(tag, payload):
    """A separately authored byte mutation, never an overwrite of upstream data."""
    lines = (UPSTREAM / "selex/selex.good.4").read_bytes().splitlines(keepends=True)
    base_tag = b"SS" if tag in {"SS", "SA"} else b"CS" if tag == "CS" else b"RF"
    index = next(i for i, line in enumerate(lines) if line.startswith(b"#=" + base_tag))
    line = lines[index]
    start = 4
    while line[start:start + 1] in (b" ", b"\t"):
        start += 1
    changed = b"#=" + tag.encode() + line[4:start + 1] + payload + line[start + 1 + len(payload):]
    if tag in {"MM", "SA"}:
        lines.insert(index + 1, changed)
    else:
        lines[index] = changed
    return b"".join(lines)


@pytest.mark.parametrize("tag", ["RF", "MM", "CS", "SS", "SA"])
@pytest.mark.parametrize("payload", [b"\x00", b"\xff", b"\xc3\xa9"])
def test_v07_byte_qualified_annotations_keep_successful_sequence_geometry(tag, payload):
    content = _annotation_diagnostic_copy(tag, payload)
    result = read(content, "selex", "RNA")
    record = result["records"][0]
    assert data.valid_alignment(record) and result["population"]["complete"]
    assert record["native_input"]["native_status_equivalent"] == 0
    assert record["column_count"] == 31 and len(record["rows"]) == 11
    output_tag = "SS_cons" if tag == "CS" else tag
    container = record["rows"][0] if tag in {"SS", "SA"} else record
    value = container["column_annotations"][output_tag]
    assert payload in value["text"].encode("utf-8", "surrogateescape")
    assert len(value["text"].encode("utf-8", "surrogateescape")) == 31
    assert not value["valid"] and data.annotation(container, output_tag) is None
    qualified = [p for p in result["issues"] if p["code"] == "annotation_byte_interpretation_unavailable"]
    assert len(qualified) == 1 and qualified[0]["field"] == output_tag
    assert qualified[0]["details"]["native_diagnostic"] in record["native_issues"]
    assert not {"alignment_invalid", "annotation_geometry_invalid"} & {p["code"] for p in result["issues"]}
    assert b"".join(e["raw"].encode("utf-8", "surrogateescape") for e in record["original_events"]) == content
    populated = sheet(content, "selex", "RNA")
    assert saved_alignment_decoding_valid(populated)
    calculated = calculate_hmmer_alignment_preparation_components(populated)["rows"][0]["components"]
    assert calculated["input_sequence_count"]["value"] == 11
    assert calculated["input_column_count"]["value"] == 31
    if tag == "RF":
        assert calculated["rf_consensus_count"]["value"] is None
        assert reconstruct_alimask_model_map(record, settings={"--informat": "selex", "--rna": True, "--hand": True})["issues"][0]["code"] == "rf_missing"
    if tag == "MM":
        assert calculated["input_masked_count"]["value"] is None
        assert calculated["input_masked_count"]["state"] == "incompatible"
    assert reconstruct_alimask_model_map(record, settings={"--informat": "selex", "--rna": True, "--wnone": True})["state"] == "present"


def test_v07_repeated_mm_keeps_effective_value_and_every_fragment():
    result = read(b"#=MM x\x00x\n#=MM m..\na    ACG\n", "selex")
    record = result["records"][0]
    assert data.annotation(record, "MM") == "m.."
    assert len(record["column_annotations"]["MM"]["fragments"]) == 2
    assert not result["issues"] and record["native_issues"] == []


@pytest.mark.parametrize("field,value,code", [
    ("content", "ACGT", "hmmer_alignment_content_invalid"),
    ("declared_format", "FASTA", "hmmer_alignment_format_invalid"),
    ("explicit_alphabet", "dna", "hmmer_alignment_alphabet_invalid"),
    ("occurrence", {}, "hmmer_alignment_occurrence_invalid"),
])
def test_public_misuse_errors_are_closed(field, value, code):
    content = b">a\nACGT\n"
    kwargs = {"content": content, "declared_format": "afa", "occurrence": occurrence(content),
              "explicit_alphabet": "DNA", "engine_version": "3.4"}
    kwargs[field] = value
    with pytest.raises(ValueError, match="^" + code + "$"):
        data.read_hmmer_alignment_input(**kwargs)


def test_reviewable_result_dictionaries(tmp_path):
    """Retain actual port results inside the bounded test's own temporary tree."""
    content = (ORACLE / "afa_auto_dna.input").read_bytes()
    source = read(content, alphabet=None)
    target = data.read_hmmer_alignment_output(content, declared_format="afa",
        occurrence=occurrence(content, direction="output", role="masked_alignment"),
        source_decoding=source["input_decoding"], engine_version="3.4")
    output = tmp_path / "adapter_input_output_examples.json"
    output.write_text(json.dumps({"input": source, "output": target}, indent=2, ensure_ascii=True) + "\n")
    assert json.loads(output.read_text()) == {"input": source, "output": target}


@pytest.mark.parametrize("fmt,native_name,path,alphabet,count,width", [
    ("afa", "AFA", ORACLE / "afa_auto_dna.input", "DNA", 2, 12),
    ("a2m", "A2M", EMISSIONS / "a2m_insertions/emitted.out", "RNA", 5, 17),
    ("clustal", "Clustal", EMISSIONS / "aligned_clustal/emitted.out", "RNA", 3, 12),
    ("phylip", "PHYLIP", EMISSIONS / "aligned_phylip/emitted.out", "RNA", 3, 12),
    ("stockholm", "Stockholm", None, "DNA", 2, 4),
    ("pfam", "Pfam", None, "DNA", 2, 4),
])
def test_native_cli_format_spelling_preserves_original_settings_and_shared_values(
        fmt, native_name, path, alphabet, count, width):
    content = path.read_bytes() if path else b"# STOCKHOLM 1.0\na ACGT\nb ACGT\n//\n"
    populated = sheet(content, native_name, alphabet)
    assert populated["operation"]["settings"]["--informat"] == native_name
    assert populated["input_records"][0]["format"] == fmt
    assert populated["input_records"][0]["input_decoding"]["format"] == fmt
    assert saved_alignment_decoding_valid(populated)
    values = calculate_hmmer_alignment_preparation_components(populated)["rows"][0]["components"]
    assert values["input_sequence_count"]["value"] == count
    assert values["input_column_count"]["value"] == width


@pytest.mark.parametrize("outformat,canonical,content", [
    ("Stockholm", "stockholm", b"# STOCKHOLM 1.0\na ACGT\nb ACGT\n//\n"),
    ("AFA", "afa", b">a\nACGT\n>b\nACGT\n"),
])
def test_native_output_format_spelling_keeps_source_alphabet(outformat, canonical, content):
    source = b"# STOCKHOLM 1.0\na ACGT\nb ACGT\n//\n"
    populated = sheet(source, "Stockholm", "DNA", output=content, outformat=outformat)
    target = populated["output_records"][0]
    assert populated["operation"]["settings"]["--outformat"] == outformat
    assert target["format"] == canonical
    assert target["source_alphabet"]["alphabet"] == "DNA"
    assert saved_alignment_decoding_valid(populated)
    calculated = calculate_hmmer_alignment_preparation_components(populated)
    assert next(c for c in calculated["checks"] if c["code"] == "sequence_content")["state"] == "pass"
