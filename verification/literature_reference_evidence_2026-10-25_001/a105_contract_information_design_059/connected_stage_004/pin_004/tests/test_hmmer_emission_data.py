"""Retained native hmmemit outputs plus explicitly synthetic edge cases."""
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from gene_annotation_episode.hmmer_model_data import extract_hmmer_models
from gene_annotation_episode.hmmer_emission_data import populate_hmmemit_sheet


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259/native"
MODES = {"core": "sample_core_unaligned", "alignment": "sample_core_aligned",
         "consensus": "consensus_simple", "fancy": "consensus_thresholded",
         **{f"profile_{style}": "sample_profile" for style in ("local", "unilocal", "glocal", "uniglocal")}}


def payload(content, role, *, direction="output", identity=None, ordinal=0, completeness="complete"):
    return {"occurrence": {"occurrence_id": identity or direction+":"+role,
        "direction": direction, "role": role, "ordinal": ordinal,
        "artifact_ref": "artifact:"+(identity or direction+":"+role),
        "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content),
        "completeness": completeness}, "content": content}


def arguments(style="core", *, output=None, model=None, settings=None, completeness="complete"):
    model = (NATIVE / "hmmbuild_protein/profile.hmm").read_bytes() if model is None else model
    data = (NATIVE / f"hmmemit_{style}/stdout.log").read_bytes() if output is None else output
    actual = {} if style in {"consensus", "fancy"} else {"--seed": 42}
    if style not in {"consensus", "fancy"}:
        actual["-N"] = 3
    if style == "fancy":
        actual.update({"-C": True, "--minl": 0.8, "--minu": 0.9})
    if style.startswith("profile_"):
        actual.update({"-p": True, "-L": 20, "--"+style.removeprefix("profile_"): True})
    if style == "alignment":
        actual["-a"] = True
    if style == "consensus":
        actual["-c"] = True
    if settings is not None:
        actual = settings
    input_payload = payload(model, "models", direction="input")
    role = "generated_alignment" if style == "alignment" else "generated_sequences"
    return {"operation": {"program": "hmmemit", "mode": MODES[style], "engine_version": "3.4", "settings": actual},
        "inputs": {"models": [input_payload]},
        "outputs": {role: [payload(data, role, completeness=completeness)],
                    "stdout": [payload(data, "stdout")], "stderr": [payload(b"", "stderr")]},
        "model_extraction": extract_hmmer_models(model, occurrence=input_payload["occurrence"], format="hmmer3_ascii")}


def make_sheet(style="core", **kwargs):
    return populate_hmmemit_sheet(**arguments(style, **kwargs))


def sequences(sheet):
    return [r for r in sheet["output_records"] if r["kind"] != "alignment"]


@pytest.mark.parametrize("style", MODES)
def test_full_retained_native_population_and_roles(style):
    sheet = make_sheet(style)
    assert set(sheet) == {"schema", "operation", "artifact_occurrences", "model_extraction", "output_records", "native_rows", "associations", "issues"}
    assert not sheet["issues"]
    rows = sequences(sheet)
    assert len(rows) == (1 if style in {"consensus", "fancy"} else 3)
    assert all(row["model_record_key"] == "input:models#model/0" for row in rows)
    assert all(row["alphabet"]["kind"] == "amino" for row in rows)
    assert rows[0]["record_key"].startswith("output:generated_")
    assert len(sheet["artifact_occurrences"]) == 4
    data = (NATIVE / f"hmmemit_{style}/stdout.log").read_bytes()
    native = [r for r in sheet["native_rows"] if r["occurrence_id"] == "output:generated_"+("alignment" if style == "alignment" else "sequences")]
    assert b"".join(r["raw"].encode() for r in native) == data
    for row in rows:
        loc = row["locator"]
        assert row["name"].encode() in data[loc["byte_start"]:loc["byte_end"]]


def test_fasta_case_wrapping_description_and_exact_locators():
    data = b">tiny_protein-sample1 description with spaces\r\nAcD\r\nexG\r\n"
    sheet = make_sheet(output=data, settings={"-N": 1})
    row, = sequences(sheet)
    assert row["sequence"] == "AcDexG"
    assert row["description"] == "description with spaces"
    assert row["locator"]["byte_start"] == 0
    assert row["locator"]["byte_end"] == len(data)
    assert row["locator"]["line_end"] == 3
    assert row["sample_ordinal"] == 1
    assert row["basis"] == "generated"


@pytest.mark.parametrize("alphabet,sequence", [("dna", "AcgTN"), ("rna", "AcgUN")])
def test_supplied_nucleotide_model_and_synthetic_emission(alphabet, sequence):
    model = (NATIVE / f"hmmbuild_{alphabet}/profile.hmm").read_bytes()
    name = next(line.split()[1] for line in model.decode().splitlines() if line.startswith("NAME"))
    sheet = make_sheet(model=model, output=f">{name}-sample1\n{sequence}\n".encode(), settings={"-N": 1})
    row, = sequences(sheet)
    assert row["alphabet"]["kind"] == alphabet.upper()
    assert row["sequence"] == sequence
    assert not sheet["issues"]


def test_two_distinct_models_missing_first_sample_does_not_shift_second():
    first = (NATIVE / "hmmbuild_protein/profile.hmm").read_bytes()
    second = first.replace(b"NAME  tiny_protein", b"NAME  second")
    output = b">tiny_protein-sample1\nAC\n>tiny_protein-sample3\nAD\n>second-sample1\nAE\n>second-sample2\nAF\n>second-sample3\nAG\n"
    sheet = make_sheet(model=first+second, output=output)
    rows = sequences(sheet)
    assert [r["sample_ordinal"] for r in rows] == [1, 3, 1, 2, 3]
    assert [r["model_record_key"] for r in rows] == ["input:models#model/0"]*2 + ["input:models#model/1"]*3
    populations = [a for a in sheet["associations"] if a["kind"] == "model_population"]
    assert [p["state"] for p in populations] == ["incomplete", "complete"]


def test_repeated_names_use_occurrences_only_with_complete_ordered_population():
    model = (NATIVE / "hmmbuild_protein/profile.hmm").read_bytes()
    output = (NATIVE / "hmmemit_core/stdout.log").read_bytes()
    sheet = make_sheet(model=model+model, output=output+output)
    rows = sequences(sheet)
    assert len({r["record_key"] for r in rows}) == 6
    assert [r["model_record_key"] for r in rows] == ["input:models#model/0"]*3 + ["input:models#model/1"]*3
    assert not sheet["issues"]
    partial = make_sheet(model=model+model, output=output+output.split(b">tiny_protein-sample2")[0])
    assert all(r["model_record_key"] is None for r in sequences(partial))
    assert any(i["code"] == "association_unresolved" for i in partial["issues"])


def test_duplicate_samples_do_not_collapse_or_claim_native_count():
    sheet = make_sheet(output=b">tiny_protein-sample1\nAC\n>tiny_protein-sample1\nAD\n", settings={"-N": 2})
    rows = sequences(sheet)
    assert len(rows) == 2 and rows[0]["record_key"] != rows[1]["record_key"]
    assert all(r["model_record_key"] is None for r in rows)
    assert any(i["code"] == "association_conflicting" for i in sheet["issues"])


@pytest.mark.parametrize("output", [b">tiny_protein-sample1\nAC\n>\nAD\n", b">tiny_protein-sample1\nAC\n>tiny_protein-sample2\n", b">tiny_protein-sample1\nAC\n>tiny_protein-sample2\nA1C\n"])
def test_malformed_trailing_fasta_preserves_valid_prefix(output):
    sheet = make_sheet(output=output)
    assert sequences(sheet)[0]["sequence"] == "AC"
    assert sequences(sheet)[0]["model_record_key"] == "input:models#model/0"
    assert sequences(sheet)[1]["state"] != "complete"
    assert sheet["issues"]


def test_empty_zero_length_sequence_is_not_header_only_truncation():
    full = make_sheet(output=b">tiny_protein-sample1\n\n", settings={"-N": 1})
    assert sequences(full)[0]["state"] == "complete"
    truncated = make_sheet(output=b">tiny_protein-sample1\n", settings={"-N": 1})
    assert sequences(truncated)[0]["state"] == "incomplete"


def test_missing_settings_stay_omitted():
    sheet = make_sheet(settings={})
    assert sheet["operation"]["settings"] == {}
    assert all(r["model_record_key"] is not None for r in sequences(sheet))
    assert next(a for a in sheet["associations"] if a["kind"] == "model_population")["expected_count"] is None


def test_partial_model_population_preserves_full_first_model():
    model = (NATIVE / "hmmbuild_protein/profile.hmm").read_bytes()
    partial = model.replace(b"NAME  tiny_protein", b"NAME  trailing").split(b"      4 ")[0]
    sheet = make_sheet(model=model+partial)
    assert sheet["model_extraction"]["population"]["state"] == "partial"
    assert all(r["model_record_key"] == "input:models#model/0" for r in sequences(sheet))


def test_stockholm_preserves_interleaving_all_annotations_and_occurrence_keys():
    text = b"# STOCKHOLM 1.0\n#=GF ID native_id\n#=GS tiny_protein-sample1 DE description\ntiny_protein-sample1 AC-\n#=GR tiny_protein-sample1 PP 99.\n#=GC RF xx.\n#=GC MM ..m\n\ntiny_protein-sample1 dEF\n#=GR tiny_protein-sample1 PP 999\n#=GC RF .xx\n#=GC MM ...\n//\n"
    sheet = make_sheet("alignment", output=text, settings={"-N": 1})
    alignment, row = sheet["output_records"]
    assert row["sequence"] == "AC-dEF"
    assert row["description"] == "description"
    assert row["native"]["column_annotations"]["PP"]["text"] == "99.999"
    assert alignment["native"]["column_annotations"]["RF"]["text"] == "xx..xx"
    assert alignment["native"]["column_annotations"]["MM"]["text"] == "..m..."
    assert {line["kind"] for line in sheet["native_rows"]} >= {"GC", "GS", "GR", "GF", "header", "terminator"}
    assert row["alignment_record_key"] == alignment["record_key"]
    assert "posterior" not in row and "score" not in row


def test_truncated_stockholm_retains_complete_prior_alignment():
    data = (NATIVE / "hmmemit_alignment/stdout.log").read_bytes()
    sheet = make_sheet("alignment", output=data+b"# STOCKHOLM 1.0\nunknown ACD\n")
    alignments = [r for r in sheet["output_records"] if r["kind"] == "alignment"]
    assert len(alignments) == 2
    assert alignments[0]["state"] == "complete"
    assert alignments[1]["state"] != "complete"


@pytest.mark.parametrize("field,value,code", [("size_bytes", 1, "occurrence_size_mismatch"), ("sha256", "0"*64, "occurrence_digest_mismatch"), ("role", "wrong", "occurrence_role_mismatch")])
def test_occurrence_conflicts_preserve_data_but_disable_association(field, value, code):
    args = arguments()
    args["outputs"]["generated_sequences"][0]["occurrence"][field] = value
    sheet = populate_hmmemit_sheet(**args)
    assert len(sequences(sheet)) == 3
    assert all(r["model_record_key"] is None for r in sequences(sheet))
    assert code in {i["code"] for i in sheet["issues"]}


def test_extraction_tampering_and_wrong_occurrence_are_not_silently_accepted():
    args = arguments()
    args["model_extraction"]["records"][0]["positions"][0]["match"]["cells"][0]["probability"] = 0.5
    sheet = populate_hmmemit_sheet(**args)
    assert any(i["code"] == "model_extraction_mismatch" for i in sheet["issues"])
    assert all(r["model_record_key"] is None for r in sequences(sheet))


def test_missing_and_empty_output_are_distinct():
    args = arguments()
    args["outputs"] = {}
    missing = populate_hmmemit_sheet(**args)
    empty = make_sheet(output=b"")
    assert any(i["code"] == "generated_output_missing" for i in missing["issues"])
    assert not any(i["code"] == "generated_output_missing" for i in empty["issues"])
    assert not sequences(missing) and not sequences(empty)


def test_duplicate_artifact_occurrences_preserve_rows_with_conflicting_identity():
    args = arguments()
    args["outputs"]["generated_sequences"].append(deepcopy(args["outputs"]["generated_sequences"][0]))
    sheet = populate_hmmemit_sheet(**args)
    assert len(sequences(sheet)) == 6
    assert any(i["code"] == "occurrence_duplicate" for i in sheet["issues"])
    assert all(row["model_record_key"] is None for row in sequences(sheet))


def test_stockholm_duplicate_rows_and_malformed_interleaving_are_not_joined():
    text = b"# STOCKHOLM 1.0\ntiny_protein-sample1 AC\ntiny_protein-sample1 AD\n#=GC RF xx\n\ntiny_protein-sample1 EF\n#=GC RF xx\n//\n"
    sheet = make_sheet("alignment", output=text, settings={"-N": 2})
    assert len(sequences(sheet)) == 2
    assert all(row["state"] == "invalid" for row in sequences(sheet))
    assert all(row["model_record_key"] is None for row in sequences(sheet))


def test_multiple_native_alignment_records_with_repeated_model_names():
    model = (NATIVE / "hmmbuild_protein/profile.hmm").read_bytes()
    output = (NATIVE / "hmmemit_alignment/stdout.log").read_bytes()
    sheet = make_sheet("alignment", model=model+model, output=output+output)
    assert len(sheet["output_records"]) == 8
    assert len({row["record_key"] for row in sheet["output_records"]}) == 8
    assert not sheet["issues"]


def test_invalid_utf8_retains_exact_native_bytes_and_valid_prefix():
    output = b">tiny_protein-sample1\nAC\n>tiny_protein-sample2\nA\xff\n"
    sheet = make_sheet(output=output)
    assert sequences(sheet)[0]["sequence"] == "AC"
    assert any(i["code"] == "text_encoding_invalid" for i in sheet["issues"])
    raw = "".join(row["raw"] for row in sheet["native_rows"] if row["occurrence_id"] == "output:generated_sequences")
    assert raw.encode("utf-8", errors="surrogateescape") == output


def test_parser_has_no_external_effects(monkeypatch):
    import builtins
    import socket
    import subprocess
    args = arguments("fancy")
    original = deepcopy(args)
    def forbidden(*args, **kwargs):
        raise AssertionError("pure parser attempted an external effect")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    sheet = populate_hmmemit_sheet(**args)
    assert sequences(sheet)[0]["sequence"] == "ACDExGHIKLMN"
    assert args == original
