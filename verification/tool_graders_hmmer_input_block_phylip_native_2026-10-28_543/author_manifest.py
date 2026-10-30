"""Stdlib-only authoring of pinned diagnostic cases, never scientific execution.

This retains authored edge bytes separately from existing unmodified upstream
fixtures/emission artifacts. Run only to author this packet, not during tests.
It imports no application modules and runs no native program or compiler.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
FIXTURES = PACKET / "fixtures"
FIXTURES.mkdir(exist_ok=True)
UPSTREAM = REPO / "resources/software/infernal-1.1.5/easel/esl_msa_testfiles"
EMISSION = REPO / "verification/tool_graders_infernal_preparation_emission_2026-10-26_250/native"
OLD = REPO / "verification/tool_graders_hmmer_input_native_oracle_2026-10-28_539"
BLOCK = REPO / "verification/tool_graders_hmmer_input_blocks_2026-10-28_540"
PHY = REPO / "verification/tool_graders_hmmer_input_phylip_2026-10-28_541"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def pin(path):
    content = path.read_bytes()
    return {"path": str(path.relative_to(REPO)), "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)}


cases = []
excluded = []
provenance = {}


def add(identifier, fmt, alphabet, status, *, content=None, path=None,
        basis="authored_edge_input_not_native_emission", geometry=None,
        scope="single_record", rowscope="whole_rows", py=None, native=None, note=None):
    if path is None:
        path = FIXTURES / (identifier + ".bytes")
        path.write_bytes(content)
    else:
        content = path.read_bytes()
    checks = dict(native or {})
    if status in (0, 3) and scope == "single_record":
        checks.setdefault("read_line_number", content.count(b"\n") + int(bool(content) and not content.endswith(b"\n")))
    cases.append({
        "id": identifier, "format": fmt, "alphabet": alphabet,
        **pin(path), "basis": basis, "source_expected_status": status,
        "source_expected_geometry": ("complete" if status == 0 else None) if geometry is None else geometry,
        "native_oracle_eligible": True, "native_record_scope": scope,
        "row_comparison_scope": rowscope, "python_checks": py or {},
        "native_checks": checks, "source_note": note,
    })


# Twenty source-reviewed safe block inputs from packet 540. Its two unsafe
# examples remain manifest exclusions, never arguments to native_observer.
old_block = json.loads((BLOCK / "AUTHORED_NATIVE_CASES.json").read_text())
for case in old_block["cases"]:
    if not case["native_oracle_eligible"]:
        excluded.append({"id": case["name"], "basis": "packet_540_source_only", "reason": "unsafe_SELEX_pointer_or_negative_copy_geometry", "content_sha256": hashlib.sha256(bytes.fromhex(case["content_hex"])).hexdigest()})
        continue
    add(case["name"], case["format"], case["alphabet"], case["expected_read_status"],
        content=bytes.fromhex(case["content_hex"]), note="Unmodified authored input bytes from packet 540 AUTHORED_NATIVE_CASES.json.")

by_id = {case["id"]: case for case in cases}
by_id["psi_duplicate_blocks"]["python_checks"] = {"rows": ["A-c-T-", "G-t-C-"], "names": ["dup", "dup"], "annotations": {"RF": "x-.-x-"}, "block_count": 2}
by_id["psi_case_conflict"]["python_checks"] = {"rows": ["Aa"], "diagnostic_code": "psiblast_case_conflict"}
by_id["psi_nul_unknown"]["python_checks"] = {"rows": ["AN-"], "annotations": {"RF": "x--"}}
by_id["psi_name_nul_prefix"]["python_checks"] = {"rows": ["ACGT"], "names": ["a"]}
by_id["selex_physical"]["python_checks"] = {
    "rows": ["--AC-G", "ATCGTT", "------"], "column_count": 6,
    "annotations": {"RF": "..x..x", "MM": "..m..m", "SS_cons": "..>..<"},
    "first_row_annotations": {"SS": "..(..)", "SA": "..1234"},
}
by_id["selex_mm_overwrite"]["python_checks"] = {"annotations": {"MM": "cd"}}
by_id["selex_later_missing"]["python_checks"] = {"rows": ["AC--------", "----------"], "column_count": 10}
by_id["selex_ss_rewind"]["native_checks"] = {"read_line_number": 3}
by_id["selex_ss_rewind"]["python_checks"] = {"next_byte_offset": len(b"a    AC\r\n#=SS xx\r\n#=SS yy"), "diagnostic_code": "annotation_cardinality_mismatch"}
by_id["clustal_trailing_tokens"]["python_checks"] = {"consensus_event_count": 1, "annotations": {"RF": None}, "rows": ["AC", "GT"]}

for fmt in ("psiblast", "selex", "clustal", "clustallike", "phylip", "phylips"):
    for label, content in (("empty", b""), ("blank_nul_crlf", b"\n \t\r\n\x00\n")):
        add(f"{fmt}_{label}", fmt, "amino", 3, content=content,
            py={"record_count": 0, "end_state": "eof", "next_byte_offset": len(content)})

for label, content in [
    ("all_gap_rf", b"a --\nb --\n"),
    ("crlf_unterminated", b"dup A-c-\r\ndup G-t-\r\n\r\ndup T-\r\ndup C-"),
    ("trailing_bare_cr_trimmed", b"a AC\r"),
]:
    add("psi_" + label, "psiblast", "amino", 0, content=content)
for label, content in [
    ("forbidden_underscore", b"a A_\n"), ("forbidden_star", b"a A*\n"),
    ("forbidden_missing", b"a A~\n"), ("forbidden_lower_o", b"a Ao\n"),
    ("later_row_order", b"a AA\nb CC\n\nb GG\na TT\n"),
    ("later_row_count", b"a AA\nb CC\n\na GG\n"),
    ("later_extra_allocated_row", b"a AA\n\na GG\nb TT\n"),
]:
    add("psi_" + label, "psiblast", "amino", 7, content=content)

add("selex_comments_and_indented_row", "selex", "amino", 0,
    content=b"# ignored\na AC\n # XX\n# ignored again\n", py={"rows": ["AC-", "-XX"], "names": ["a", "#"]})
add("selex_mm_two_blocks", "selex", "amino", 0,
    content=b"#=MM ab\n#=MM cd\na    AC\n\n#=MM ef\n#=MM gh\na    GT\n",
    py={"annotations": {"MM": "cdgh"}, "block_count": 2})
add("selex_reversible_byte_name", "selex", "DNA", 0,
    content=b"\xff\xc3\xa9 A\x00C\n", py={"rows": ["ANC"]},
    note="High bytes occur only in a memtok name; the last sequence byte tested by ctype is ASCII C.")
add("selex_internal_highbyte_rejected", "selex", "amino", 7,
    content=b"a A\xffC\n", py={"rows": ["A"], "diagnostic_code": "invalid_sequence_byte"},
    note="Safe ASCII right edge stops ctype; internal high byte reaches the explicit digital isascii rejection.")
add("selex_annotation_before_failure", "selex", "amino", 7,
    content=b"#=RF xxx\n#=MM abc\n#=MM def\na    AC1\n",
    py={"rows": ["AC"], "annotations": {"RF": "xxx", "MM": "def"}},
    native={"read_line_number": 4})
add("clustal_nul_name_prefix", "clustal", "amino", 0,
    content=b"CLUSTAL alignment\na\x00z AC\n **\n\na GT\n **\n", py={"rows": ["ACGT"], "names": ["a"]})
add("clustal_nul_name_repeat", "clustal", "amino", 7,
    content=b"CLUSTAL alignment\na\x00z AC\n **\n\na\x00z GT\n **\n")
add("clustal_digital_aliases", "clustal", "DNA", 0,
    content=b"CLUSTAL alignment\na A._*~uXI\n ********\n", py={"annotations": {"RF": None}})
add("clustal_ignored_trailing_highbyte", "clustal", "amino", 0,
    content=b"CLUSTAL alignment\na AC 999 anything \xff\nb GT text\n **\n",
    note="Byte after a sequence-delimiting ASCII space is ignored trailing syntax and never reaches ctype.")
add("clustal_empty_consensus", "clustal", "amino", 0, content=b"CLUSTAL alignment\na AC\n\n")
add("clustal_nul_consensus", "clustal", "amino", 0, content=b"CLUSTAL alignment\na AC\n\x00\n")
add("clustal_header_nul_delimiter", "clustal", "amino", 0, content=b"CLUSTAL\x00alignment\na AC\n **\n")
add("clustal_header_case_sensitive", "clustal", "amino", 7, content=b"CLUSTAL Alignment\na AC\n **\n")
add("clustal_later_extra_allocated_row", "clustal", "amino", 7,
    content=b"CLUSTAL alignment\na AC\n **\n\na GT\nb AC\n **\n")
add("clustallike_duplicate_blocks", "clustallike", "amino", 0,
    content=b"MUSCLE alignment\ndup AC\ndup GT\n **\n\ndup DE\ndup FG\n **\n",
    py={"names": ["dup", "dup"], "rows": ["ACDE", "GTFG"], "consensus_event_count": 2})
add("clustallike_missing_alignment_word", "clustallike", "amino", 7, content=b"MUSCLE\na AC\n **\n")


def named(name, sequence, ending=b"\n"):
    assert len(name) <= 10
    return name.ljust(10, b" ") + sequence + ending


for fmt in ("phylip", "phylips"):
    add(fmt + "_strict_positional_names", fmt, "DNA", 0,
        content=b"4 4\n" + named(b"with space", b"ACGT") + named(b"with space", b"A-GT") + named(b"", b"AC-T") + b"abcdefghijACGT\n",
        py={"names": ["with_space", "with_space", "", "abcdefghij"], "rows": ["ACGT", "A-GT", "AC-T", "ACGT"]})
    add(fmt + "_trim_literal_spaces", fmt, "DNA", 0, content=b"1 2\n  a b     AC\n", py={"names": ["a_b"]})
    add(fmt + "_short_name", fmt, "DNA", 7, content=b"1 4\nshort\nACGT\n", py={"rows": []})
    for label, byte in (("tab", b"\t"), ("nul", b"\x00"), ("cr", b"\r"), ("del", b"\x7f")):
        add(fmt + "_name_" + label, fmt, "DNA", 7, content=b"1 2\n" + named(b"a" + byte + b"b", b"AC"))
    for alphabet in ("DNA", "RNA"):
        add(fmt + "_native_aliases_" + alphabet.lower(), fmt, alphabet, 0,
            content=b"1 9\n" + named(b"sample", b"A 0\t1?2O3.4*5u6x7I8-"),
            py={"rows": ["A~-.*uxI-"]})
    add(fmt + "_amino_o_residues", fmt, "amino", 0, content=b"1 4\n" + named(b"sample", b"Oo?."), py={"rows": ["Oo~."]})
    for alphabet, expected in (("DNA", "ANC"), ("RNA", "ANC"), ("amino", "AXC")):
        add(fmt + "_sequence_nul_" + alphabet.lower(), fmt, alphabet, 0,
            content=b"1 3\n" + named(b"sample", b"A\x00C"), py={"rows": [expected]})
    for label, bad in (("digit9", b"9"), ("underscore", b"_"), ("tilde", b"~"), ("lower_o", b"o"), ("bare_cr", b"\r"), ("highbyte", b"\xff")):
        content = b"1 4\n" + named(b"sample", b"A 8C" + bad + b"GT") + b"suffix\n"
        add(fmt + "_bad_symbol_" + label, fmt, "DNA", 7, content=content,
            py={"rows": ["AC"], "next_byte_offset": len(content)-len(b"suffix\n"), "diagnostic_code": "invalid_sequence_byte"})
    for label, header in (("octal", b"02 04"), ("hex", b"0x2 0x4"), ("prefix_suffix", b"2tail 4tail extra"), ("cspace", b"\v2 \r4"), ("nul_delimiter", b"2\x004")):
        add(fmt + "_dimensions_" + label, fmt, "DNA", 0,
            content=header + b"\n" + named(b"one", b"ACGT") + named(b"two", b"A-GT"),
            py={"declared_column_count": 4})
    for label, header in (("plus", b"+1 2"), ("only_one_field", b"1"), ("hex_no_digits", b"0x 2"), ("int32_positive_overflow", b"2147483648 2"), ("int32_negative_overflow", b"-2147483649 2")):
        add(fmt + "_invalid_header_" + label, fmt, "DNA", 7, content=header + b"\n",
            note="Rejected by integer/header parsing before esl_msa_CreateDigital; no huge or nonpositive allocation is attempted.")
    first = b"1 2\r\n" + named(b"first", b"AC", b"\r\n") + b" \t\r\n"
    second = b"1 2\n" + named(b"second", b"GT", b"")
    add(fmt + "_first_of_two_complete", fmt, "DNA", 0, content=first + second, scope="first_record_only",
        native={"read_line_number": 3, "nseq": 1, "alen": 2},
        py={"record_count": 2, "record_states": ["complete", "complete"], "record_statuses": [0, 0], "first_record_end_byte": len(first), "end_state": "eof"},
        note="Only the first record is compared to native. Second-record state and boundary are source-derived Python assertions.")
    add(fmt + "_first_before_malformed_second", fmt, "DNA", 0, content=first + b"broken\n" + second, scope="first_record_only",
        native={"read_line_number": 3, "nseq": 1, "alen": 2},
        py={"record_states": ["complete", "invalid"], "record_statuses": [0, 7], "first_record_end_byte": len(first), "next_byte_offset": len(first) + len(b"broken\n"), "end_state": "parse_error"},
        note="Native does not read the malformed second record; no second-record native conformance claim.")

add("phylip_interleaved_unnamed_blocks", "phylip", "DNA", 0,
    content=b"2 4\n" + named(b"same", b"AC") + named(b"same", b"A-") + b"\nGT\nG-\n",
    py={"rows": ["ACGT", "A-G-"], "block_count": 2})
add("phylip_relaxed_looking_name", "phylip", "DNA", 7,
    content=b"1 4\nalpha ACGT\n", py={"names": ["alpha_ACGT"], "rows": [""]})
content = b"2 4\n" + named(b"one", b"AC") + b"\n" + named(b"two", b"GT")
add("phylip_missing_block_row", "phylip", "DNA", 7, content=content,
    py={"block_count": 0, "next_byte_offset": len(content)-len(named(b"two", b"GT"))}, native={"read_line_number": 3})
add("phylip_block_width_mismatch", "phylip", "DNA", 7,
    content=b"2 4\n" + named(b"one", b"AC") + named(b"two", b"A") + b"GT\nGT\n",
    py={"rows": ["AC", "A"], "diagnostic_code": "block_geometry_mismatch"})
first = b"1 2\n" + named(b"first", b"ACGT")
second = b"1 2\n" + named(b"second", b"GT")
add("phylip_overwidth_at_eof", "phylip", "DNA", 7, content=first,
    py={"rows": ["ACGT"], "column_count": 4, "declared_column_count": 2})
add("phylip_overwidth_with_lookahead", "phylip", "DNA", 0, content=first + second,
    geometry="invalid", scope="first_record_only", native={"read_line_number": 2, "nseq": 1, "alen": 4},
    py={"record_states": ["invalid", "complete"], "record_statuses": [0, 0], "rows": ["ACGT"], "column_count": 4, "declared_column_count": 2, "first_record_end_byte": len(first)},
    note="Rectangular initialized first row is safe for this observer, but declared geometry is invalid. No MAP is executed.")
add("phylips_zero_length_name_replacement", "phylips", "DNA", 0,
    content=b"2 4\n" + named(b"discarded", b"0128 \t") + named(b"replaced", b"AC") + b"GT\n\n" + named(b"second", b"A-") + b"G-\n",
    py={"names": ["replaced", "second"], "rows": ["ACGT", "A-G-"], "block_count": None})
add("phylips_zero_length_short_followup", "phylips", "DNA", 7,
    content=b"1 4\n" + named(b"first", b"012") + b"ACGT\n", py={"rows": [""], "names": ["first"]})
add("phylips_short_nonfinal_eof", "phylips", "DNA", 7,
    content=b"2 4\n" + named(b"first", b"AC"), py={"rows": ["AC"]})
add("phylips_overwidth_consumed_lookahead", "phylips", "DNA", 7,
    content=first + second, py={"rows": ["ACGT"], "next_byte_offset": len(first)+len(b"1 2\n"), "end_state": "parse_error"},
    native={"read_line_number": 3})
add("phylips_short_last_eof_safe_prefix", "phylips", "DNA", 0,
    content=b"2 4\n" + named(b"first", b"AAAA") + named(b"last", b"CC"),
    geometry="invalid", rowscope="native_alen_prefixes", native={"nseq": 2, "alen": 2},
    py={"rows": ["AAAA", "CC"], "column_count": 2, "declared_column_count": 4, "record_states": ["invalid"]},
    note="esl_msafile_phylip.c:587-598 sets native alen to final length 2. Observer print_msa and esl_msa_Checksum access only 1..2, initialized in both rows. Only displayed prefixes AA/CC are native comparisons; full unequal Python rows remain invalid.")
add("phylips_single_short_eof", "phylips", "DNA", 0,
    content=b"1 4\n" + named(b"only", b"AC"), geometry="invalid",
    py={"rows": ["AC"], "column_count": 2, "declared_column_count": 4})

# Authentic retained fixtures are read in place, never rewritten or regenerated.
for group, choices in {
    "psiblast": [("psiblast.good.1", "amino", 0), ("psiblast.good.2", "RNA", 0)],
    "selex": [("selex.good.1", "amino", 0), ("selex.good.2", "amino", 0), ("selex.good.4", "RNA", 0)] + [(f"selex.bad.{i}", "amino", 3 if i == 1 else 7) for i in range(1, 15)],
    "phylip": [("phylip.good.1", "DNA", 0), ("phylip.good.2", "DNA", 0), ("phylip.good.3", "amino", 0), ("phylip.ambig.1", "amino", 0)] + [(f"phylip.bad.{i}", "amino", 7) for i in range(1, 12)],
    "phylips": [("phylips.good.1", "DNA", 0), ("phylips.good.2", "amino", 0)],
}.items():
    for name, alphabet, status in choices:
        add("upstream_" + name.replace(".", "_"), group, alphabet, status,
            path=UPSTREAM/group/name, basis="unchanged_upstream_Easel_fixture_not_workflow_emission")
for name, fmt, alphabet, status in [
    ("clustal.good.1", "clustallike", "amino", 0),
    ("clustal.good.1", "clustal", "amino", 7),
    ("clustal.good.2", "clustal", "RNA", 0),
]:
    add("upstream_" + name.replace(".", "_") + "_" + fmt, fmt, alphabet, status,
        path=UPSTREAM/"clustal"/name, basis="unchanged_upstream_Easel_fixture_not_workflow_emission")
add("upstream_phylip_ambig_1_as_phylips", "phylips", "amino", 0,
    path=UPSTREAM/"phylip"/"phylip.ambig.1", basis="unchanged_upstream_Easel_fixture_not_workflow_emission")
for name, fmt in [
    ("aligned_clustal", "clustal"), ("clustal_long_interleaved", "clustal"),
    ("aligned_phylip", "phylip"), ("phylip_interleaved", "phylip"), ("phylip_long_interleaved", "phylip"),
]:
    add("retained_cmemit_" + name, fmt, "RNA", 0, path=EMISSION/name/"emitted.out",
        basis="unchanged_retained_native_cmemit_emission_new_reader_comparison")
    for file in ("receipt.json", "request.json", "stdout.txt", "stderr.txt"):
        item = pin(EMISSION/name/file)
        provenance[item["path"]] = item

for path in [BLOCK/"AUTHORED_NATIVE_CASES.json", BLOCK/"FIXTURE_INDEX.json", PHY/"EVIDENCE.json", UPSTREAM/"selex"/"00MANIFEST"]:
    item = pin(path)
    provenance[item["path"]] = item

excluded += [
    {"id": "upstream_selex_good_3", **pin(UPSTREAM/"selex"/"selex.good.3"), "reason": "first retained missing-data annotation gives unestablished native pointer/width semantics; upstream good label is not safety proof"},
    {"id": "selex_no_sequence_rows", "reason": "zero-sequence native allocation path remains source-only"},
    {"id": "psi_clustal_row_storage_overrun", "reason": "later-block row index beyond growable allocated array is undefined access; only still-allocated-null-name rejection is selected"},
    {"id": "signed_char_nonascii_ctype", "reason": "no execution where a high byte reaches isspace/isupper/islower/isgraph; explicitly safe byte-name/digital/ignored-tail cases are separate"},
    {"id": "selex_surviving_nul_or_highbyte_annotation", "reason": "observer strlen/print_hex cannot prove full position-indexed annotation bytes; existing pure lossless cases retain them"},
    {"id": "phylip_nonpositive_or_huge_accepted_dimensions", "reason": "no unsafe or oversized allocation; rejected out-of-range integer tokens are safe because Read returns before allocation"},
    {"id": "phylips_final_row_longer_than_prior_rows", "reason": "observer/checksum would access sentinel or uninitialized/out-of-bounds storage in shorter earlier rows"},
    {"id": "phylips_final_zero_length", "reason": "zero/native-null digital geometry is excluded from diagnostic execution"},
    {"id": "unsafe_native_MAP", "reason": "no alignment-to-model tool or native MAP calculation is invoked anywhere in this suite"},
]

assert len({case["id"] for case in cases}) == len(cases)
old_pins = json.loads((OLD/"SOURCE_PINS.json").read_text())
manifest = {
    "schema": "hmmer_six_format_native_comparison_cases_v1",
    "authorship_status": "authored_not_executed",
    "expected_native_comparison_count": len(cases),
    "case_counts_by_format": dict(sorted(Counter(case["format"] for case in cases).items())),
    "case_counts_by_source_expected_status": dict(sorted(Counter(str(case["source_expected_status"]) for case in cases).items())),
    "cases": cases, "excluded_from_native_execution": excluded,
    "provenance_pins": [provenance[key] for key in sorted(provenance)],
    "observer": pin(OLD/"input_observer.c"),
    "reused_fixture_module": pin(REPO/"tests/test_hmmer_alignment_input_native_oracle.py"),
    "original_source_pin_manifest": pin(OLD/"SOURCE_PINS.json"),
    "native_record_limit": "one Read per observer call; only first record compared",
    "cursor_limit": "read_line_number observable; byte offset source-derived only",
    "scoring_added": False, "scientific_producers_executed": False,
}
write_json(PACKET/"CASES.json", manifest)

required = set(old_pins["fixture_files"]) | set(old_pins["diagnostic_sources"])
required |= {case["path"] for case in cases} | set(provenance)
required |= {str((OLD/name).relative_to(REPO)) for name in ("CASES.json", "SOURCE_PINS.json", "input_observer.c")}
required |= {
    "tests/test_hmmer_alignment_input_block_phylip_native.py",
    "tests/test_hmmer_alignment_input_native_oracle.py",
    str((PACKET/"CASES.json").relative_to(REPO)),
    "gene_annotation_episode/hmmer_alignment_input_blocks.py",
    "gene_annotation_episode/hmmer_alignment_input_phylip.py",
    "gene_annotation_episode/hmmer_alignment_input_types.py",
    "gene_annotation_episode/hmmer_alignment_input_alphabet.py",
    "gene_annotation_episode/hmmer_alignment_input_fasta.py",
    "gene_annotation_episode/hmmalign_inputs.py",
}
write_json(PACKET/"STAGING.json", {
    "required_repo_files": [pin(REPO/path) for path in sorted(required)],
    "easel_files_under_explicit_HMMER_NATIVE_ORACLE_EASEL_DIR": old_pins["easel_files"],
    "existing_source_root": "resources/software/infernal-1.1.5/easel",
    "environment": {"HMMER_NATIVE_ORACLE_EASEL_DIR": "root-selected absolute staged Easel directory", "HMMER_NATIVE_ORACLE_CC": "root-selected absolute staged compiler"},
    "execution": "existing frozen root lifecycle, sequential selected tests, 20 GiB RAM, 4 GiB scratch, zero swap, no wall cap",
    "pytest_selector": "tests/test_hmmer_alignment_input_block_phylip_native.py",
    "do_not_select": "tests/test_hmmer_alignment_input_native_oracle.py (its fixture/helpers are reused; its 201 completed cases are not selected)",
    "required_existing_runtime": "root's existing staged package/Python/pytest/compiler/sysroot/runtime dependencies; no new runner or discovery",
})
print(json.dumps({key: manifest[key] for key in ("expected_native_comparison_count", "case_counts_by_format", "case_counts_by_source_expected_status")}, sort_keys=True))
