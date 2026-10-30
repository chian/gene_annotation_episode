"""Strict PHYLIP decoder tests; inline bytes are authored edge cases.

Only the three cmemit paths named in RETAINED are authentic retained emissions.
No test executes native code, a model map, a compiler, or a scientific calculator.
Run these tests only in the root-selected bounded verification lifecycle.
"""

import hashlib
from pathlib import Path
import unittest

from gene_annotation_episode.hmmer_alignment_input_phylip import decode_native_phylip_alignment


ROOT = Path(__file__).resolve().parents[1]
RETAINED = {
    "aligned_phylip": (
        "2080aeba7e96b2b39127ae483c66b61ff53394a6e2c696203fff88dcb470d649",
        "fixture246", 12, 1,
        ["GCGC-UAAGCGC", "GCGCUAAAGCGC", "GCGAUUUAUCGU"],
    ),
    "phylip_interleaved": (
        "f328a9f75340fa0286ffc31428dad984199b09651982d6b8ae50613f52e4342a",
        "fixture246", 15, 1,
        ["C---UU-A-A-GGCC", "CCC--A--AUG---G"],
    ),
    "phylip_long_interleaved": (
        "1da160dadc5a685c83856a689d40443a2050aecf1c49188ec3b64ae7473ecc75",
        "tRNA5-samp", 74, 2,
        [
            "GGGAGUAUAGUGUACUAGGU-AACACGUAUGGGUUCAGACCGUACGGUCCUGGGUUC--U"
            "CCCCAGUACGCACA",
            "GCGAAUCUGGCCUAGU-GGCAAUGGCGGACUACUAGAAUUAGCCAGAUCAUUUGAUCGAU"
            "CCAAGUGAUUUGUA",
        ],
    ),
}


def decode(content, fmt="phylip", alphabet="DNA"):
    return decode_native_phylip_alignment(content, declared_format=fmt, alphabet=alphabet)


def named(name, sequence, newline=b"\n"):
    assert len(name) <= 10
    return name.ljust(10, b" ") + sequence + newline


def codes(record):
    return [diagnostic["code"] for diagnostic in record["diagnostics"]]


class NativePhylipInputTests(unittest.TestCase):
    def assert_complete(self, batch, rows, *, width=None):
        self.assertEqual(batch["end_state"], "eof")
        self.assertIsNone(batch["trailing_range"])
        self.assertEqual(len(batch["records"]), 1)
        record = batch["records"][0]
        self.assertEqual(record["reader_state"], "complete")
        self.assertEqual(record["native_status_equivalent"], 0)
        self.assertEqual([row["aligned_sequence"] for row in record["rows"]], rows)
        self.assertEqual(record["column_count"], len(rows[0]) if width is None else width)
        self.assertTrue(all(row["geometry_valid"] and row["symbols_valid"]
                            and row["identity_unambiguous"] for row in record["rows"]))
        self.assertEqual(record["diagnostics"], [])
        return record

    def assert_source_spans(self, content, record):
        for ordinal, event in enumerate(record["events"]):
            self.assertEqual(event["event_ordinal"], ordinal)
            loc = event["locator"]
            self.assertEqual(event["raw"].encode("utf-8", "surrogateescape"),
                             content[loc["byte_start"]:loc["byte_end"]])
        for row in record["rows"]:
            pieces = []
            aligned_position = 0
            for segment in row["segments"]:
                self.assertEqual(segment["aligned_start"], aligned_position)
                self.assertEqual(segment["source_text"].encode("utf-8", "surrogateescape"),
                                 content[segment["byte_start"]:segment["byte_end"]])
                event = record["events"][segment["event_ordinal"]]
                line_start = event["locator"]["byte_start"]
                self.assertEqual(segment["byte_start"], line_start + segment["column_start"])
                self.assertEqual(segment["byte_end"], line_start + segment["column_end"])
                self.assertEqual(segment["aligned_end"] - segment["aligned_start"],
                                 len(segment["decoded_text"]))
                if segment["operation"] == "ignore":
                    self.assertEqual(segment["basis"], "input_ignored")
                    self.assertEqual(segment["decoded_text"], "")
                else:
                    self.assertEqual(segment["basis"], "input_symbol")
                pieces.append(segment["decoded_text"])
                aligned_position = segment["aligned_end"]
            self.assertEqual("".join(pieces), row["aligned_sequence"])

    def test_retained_cmemit_truncation_collisions(self):
        for directory, (digest, name, width, blocks, rows) in RETAINED.items():
            with self.subTest(directory=directory):
                path = ROOT / "verification/tool_graders_infernal_preparation_emission_2026-10-26_250/native" / directory / "emitted.out"
                content = path.read_bytes()
                self.assertEqual(hashlib.sha256(content).hexdigest(), digest)
                record = self.assert_complete(decode(content, alphabet="RNA"), rows, width=width)
                self.assertEqual(record["block_count"], blocks)
                self.assertEqual([row["name"] for row in record["rows"]], [name] * len(rows))
                self.assertEqual([row["row_ordinal"] for row in record["rows"]], list(range(len(rows))))
                self.assert_source_spans(content, record)

    def test_strict_names_are_ten_bytes_and_positional(self):
        content = (b"4 4\n" + named(b"with space", b"ACGT")
                   + named(b"with space", b"A-GT") + named(b"", b"AC-T")
                   + b"abcdefghijACGT\n")
        record = self.assert_complete(decode(content), ["ACGT", "A-GT", "AC-T", "ACGT"])
        self.assertEqual([row["name"] for row in record["rows"]],
                         ["with_space", "with_space", "", "abcdefghij"])
        self.assertEqual(record["rows"][0]["name_bytes_hex"], b"with_space".hex())
        self.assertEqual(record["rows"][2]["name_bytes_hex"], "")
        self.assert_source_spans(content, record)

    def test_relaxed_looking_line_is_not_a_relaxed_name(self):
        content = b"1 4\nalpha ACGT\n"
        record = decode(content)["records"][0]
        self.assertEqual(record["native_status_equivalent"], 7)
        self.assertEqual(record["rows"][0]["name"], "alpha_ACGT")
        self.assertEqual(record["rows"][0]["aligned_sequence"], "")
        self.assertIn("column_count_mismatch", codes(record))

    def test_truncated_ten_byte_name_is_retained_as_an_invalid_event(self):
        content = b"1 4\nshort\nACGT\n"
        batch = decode(content)
        record = batch["records"][0]
        self.assertEqual(record["native_status_equivalent"], 7)
        self.assertEqual(record["rows"], [])
        self.assertEqual(record["diagnostics"][-1]["details"],
                         {"expected": 10, "actual": 5, "token_hex": None})
        self.assertEqual(batch["next_byte_offset"], len(b"1 4\nshort\n"))
        self.assertEqual(record["events"][-1]["raw"], "short\n")

    def test_name_controls_fail_and_high_bytes_are_unestablished(self):
        for byte in (b"\t", b"\x00", b"\r", b"\x7f", b"\xff"):
            with self.subTest(byte=byte):
                content = b"1 2\n" + named(b"a" + byte + b"b", b"AC")
                batch = decode(content)
                record = batch["records"][0]
                unknown = byte == b"\xff"
                self.assertEqual(batch["end_state"], "source_semantics_unestablished" if unknown else "parse_error")
                self.assertEqual(record["native_status_equivalent"], None if unknown else 7)
                self.assertEqual(record["diagnostics"][-1]["details"]["token_hex"], byte.hex())
                self.assertEqual(record["rows"], [])
                self.assert_source_spans(content, record)
        # The first invalid ASCII name byte ends native name examination.
        record = decode(b"1 2\n" + named(b"a\t\xff", b"AC"))["records"][0]
        self.assertEqual(record["native_status_equivalent"], 7)

    def test_trim_only_literal_spaces(self):
        record = self.assert_complete(decode(b"1 2\n  a b     AC\n"), ["AC"])
        self.assertEqual(record["rows"][0]["name"], "a_b")
        self.assertEqual(record["rows"][0]["name_bytes_hex"], b"a_b".hex())

    def test_interleaved_blocks_use_unnamed_full_lines(self):
        content = b"2 4\n" + named(b"same", b"AC") + named(b"same", b"A-") + b"\nGT\nG-\n"
        record = self.assert_complete(decode(content), ["ACGT", "A-G-"])
        self.assertEqual(record["block_count"], 2)
        self.assertEqual([event["block_index"] for event in record["events"] if event["kind"] == "sequence"], [0, 0, 1, 1])
        self.assertEqual(record["rows"][0]["segments"][-1]["column_start"], 0)
        self.assert_source_spans(content, record)
        # Repeating a name does not cause native stripping on later blocks.
        bad = decode(b"1 4\n" + named(b"AC", b"AC") + named(b"AC", b"GT"))["records"][0]
        self.assertEqual(bad["native_status_equivalent"], 7)
        self.assertEqual(bad["rows"][0]["aligned_sequence"], "ACACGT")
        self.assertEqual(bad["column_count"], 6)

    def test_block_count_and_width_failures_keep_consumed_boundary(self):
        prefix = b"2 4\n" + named(b"one", b"AC") + b"\n"
        content = prefix + named(b"two", b"GT")
        batch = decode(content)
        record = batch["records"][0]
        self.assertEqual(record["block_count"], 0)
        self.assertEqual(batch["next_byte_offset"], len(prefix))
        self.assertEqual(batch["trailing_range"], {"byte_start": len(prefix), "byte_end": len(content)})
        self.assertEqual(record["events"][-1]["kind"], "blank")
        self.assertIn("row_count_mismatch", codes(record))
        content = b"2 4\n" + named(b"one", b"AC") + named(b"two", b"A") + b"GT\nGT\n"
        batch = decode(content)
        self.assertIn("block_geometry_mismatch", codes(batch["records"][0]))
        self.assertEqual(batch["next_byte_offset"], len(content) - len(b"GT\nGT\n"))
        self.assertEqual([row["aligned_sequence"] for row in batch["records"][0]["rows"]], ["AC", "A"])

    def test_phylips_continuation_and_zero_length_name_replacement(self):
        content = b"2 4\n" + named(b"discarded", b"0128 \t") + named(b"replaced", b"AC")
        content += b"GT\n\n" + named(b"second", b"A-") + b"G-\n"
        record = self.assert_complete(decode(content, "phylips"), ["ACGT", "A-G-"])
        self.assertIsNone(record["block_count"])
        self.assertEqual([row["name"] for row in record["rows"]], ["replaced", "second"])
        self.assertEqual(record["rows"][0]["segments"][0]["operation"], "ignore")
        self.assertEqual(record["rows"][0]["segments"][0]["aligned_end"], 0)
        self.assert_source_spans(content, record)

    def test_phylips_zero_length_repeats_strict_name_requirement(self):
        content = b"1 4\n" + named(b"first", b"012") + b"ACGT\n"
        batch = decode(content, "phylips")
        record = batch["records"][0]
        self.assertEqual(record["native_status_equivalent"], 7)
        self.assertIn("missing_name", codes(record))
        self.assertEqual(record["rows"][0]["name"], "first")
        self.assertEqual(record["rows"][0]["aligned_sequence"], "")

    def test_phylips_final_eof_width_anomaly_is_not_padded(self):
        for last, observed in ((b"CC", 2), (b"CCCCCC", 6), (b"0128", 0)):
            with self.subTest(last=last):
                content = b"2 4\n" + named(b"first", b"AAAA") + named(b"last", last)
                record = decode(content, "phylips")["records"][0]
                self.assertEqual(record["native_status_equivalent"], 0)
                self.assertEqual(record["reader_state"], "invalid")
                self.assertEqual(record["column_count"], observed)
                self.assertEqual(record["declared_column_count"], 4)
                self.assertEqual([len(row["aligned_sequence"]) for row in record["rows"]], [4, observed])
                self.assertTrue(all(not row["geometry_valid"] for row in record["rows"]))
                self.assert_source_spans(content, record)

    def test_phylips_overwidth_with_suffix_consumes_lookahead_on_error(self):
        prefix = b"1 2\n" + named(b"first", b"ACGT") + b"1 2\n"
        content = prefix + named(b"later", b"AC")
        batch = decode(content, "phylips")
        self.assertEqual(len(batch["records"]), 1)
        record = batch["records"][0]
        self.assertEqual(record["native_status_equivalent"], 7)
        self.assertEqual(record["events"][-1]["raw"], "1 2\n")
        self.assertEqual(record["events"][-1]["kind"], "invalid")
        self.assertEqual(batch["next_byte_offset"], len(prefix))
        self.assertEqual(batch["trailing_range"], {"byte_start": len(prefix), "byte_end": len(content)})

    def test_phylips_premature_nonfinal_row_eof_fails(self):
        record = decode(b"2 4\n" + named(b"first", b"AC"), "phylips")["records"][0]
        self.assertEqual(record["native_status_equivalent"], 7)
        self.assertEqual(record["reader_state"], "partial")
        self.assertIn("row_count_mismatch", codes(record))
        self.assertEqual(record["rows"][0]["aligned_sequence"], "AC")

    def test_exact_digital_aliases_and_ignored_spans(self):
        payload = b"A 0\t1?2O3.4*5u6x7I8-"
        for alphabet in ("DNA", "RNA"):
            with self.subTest(alphabet=alphabet):
                content = b"1 9\n" + named(b"sample", payload)
                record = self.assert_complete(decode(content, alphabet=alphabet), ["A~-.*uxI-"])
                self.assert_source_spans(content, record)
                self.assertEqual("".join(segment["source_text"] for segment in record["rows"][0]["segments"]), payload.decode())
        record = self.assert_complete(decode(b"1 4\n" + named(b"sample", b"Oo?."), alphabet="amino"), ["Oo~."])
        self.assertEqual(record["rows"][0]["segments"][0]["operation"], "copy")

    def test_alias_coordinates_are_zero_based_byte_and_alignment_spans(self):
        content = b"1 3\r\n" + named(b"x", b"A0?\tO", b"\r\n")
        record = self.assert_complete(decode(content), ["A~-"])
        segments = record["rows"][0]["segments"]
        self.assertEqual(
            [(s["byte_start"], s["byte_end"], s["column_start"], s["column_end"],
              s["aligned_start"], s["aligned_end"], s["operation"]) for s in segments],
            [(15, 16, 10, 11, 0, 1, "copy"),
             (16, 17, 11, 12, 1, 1, "ignore"),
             (17, 18, 12, 13, 1, 2, "symbol_alias"),
             (18, 19, 13, 14, 2, 2, "ignore"),
             (19, 20, 14, 15, 2, 3, "symbol_alias")],
        )
        self.assertEqual(record["events"][1]["locator"],
                         {"line": 2, "byte_start": 5, "byte_end": 22})
        self.assertEqual(record["byte_end"], 22)
        self.assert_source_spans(content, record)

    def test_sequence_nul_is_a_defined_unknown_alias(self):
        for alphabet, expected in (("DNA", "ANC"), ("RNA", "ANC"), ("amino", "AXC")):
            with self.subTest(alphabet=alphabet):
                content = b"1 3\n" + named(b"sample", b"A\x00C")
                record = self.assert_complete(decode(content, alphabet=alphabet), [expected])
                self.assertEqual(record["rows"][0]["segments"][1]["operation"], "symbol_alias")
                self.assert_source_spans(content, record)

    def test_forbidden_sequence_bytes_and_partial_prefix(self):
        for bad in (b"9", b"_", b"~", b"o", b"\r", b"\v", b"\xff", b"\xc3\xa9"):
            with self.subTest(bad=bad):
                content = b"1 4\n" + named(b"sample", b"A 8C" + bad + b"GT") + b"suffix\n"
                batch = decode(content)
                record = batch["records"][0]
                self.assertEqual(record["native_status_equivalent"], 7)
                self.assertEqual(batch["end_state"], "parse_error")
                self.assertEqual(record["rows"][0]["aligned_sequence"], "AC")
                self.assertFalse(record["rows"][0]["symbols_valid"])
                self.assertFalse(record["rows"][0]["geometry_valid"])
                self.assertEqual(record["diagnostics"][-1]["details"]["token_hex"], bad[:1].hex())
                self.assertEqual(batch["next_byte_offset"], len(content) - len(b"suffix\n"))
                self.assert_source_spans(content, record)

    def test_base_zero_prefix_header_conversion(self):
        for header in (b"2 4 extra", b"02 04", b"0x2 0x4", b"2tail 4tail", b"\v2 \r4", b"2\x004", b"2!\xff 4"):
            with self.subTest(header=header):
                content = header + b"\n" + named(b"one", b"ACGT") + named(b"two", b"A-GT")
                record = self.assert_complete(decode(content), ["ACGT", "A-GT"])
                self.assertEqual(record["declared_row_count"], 2)
                self.assertEqual(record["declared_column_count"], 4)

    def test_header_syntax_overflow_and_native_ctype_domain(self):
        for header in (b"+1 2", b"1 +2", b"0x 2", b"1", b"2147483648 2", b"-2147483649 2", b"1 0x80000000"):
            with self.subTest(header=header):
                record = decode(header + b"\n")["records"][0]
                self.assertEqual(record["native_status_equivalent"], 7)
                self.assertFalse(record["header_valid"])
                self.assertEqual(record["rows"], [])
        for header in (b"\xff1 2", b"1\xff 2", b"1 2\xff", b"-\xff1 2"):
            with self.subTest(header=header):
                batch = decode(header + b"\n")
                self.assertEqual(batch["end_state"], "source_semantics_unestablished")
                self.assertEqual(batch["records"][0]["diagnostics"][-1]["details"]["actual"], "nonascii_ctype")
        record = decode(b"2147483647 2\n")["records"][0]
        self.assertEqual(record["declared_row_count"], 2147483647)
        self.assertTrue(record["header_valid"])
        self.assertEqual(record["native_status_equivalent"], 7)

    def test_nonpositive_dimensions_are_source_safety_cases_only(self):
        # These are pure source-contract cases, never native/map executions.
        for header in (b"0 2", b"-1 2", b"1 0", b"1 -2", b"-2147483648 2", b"0X2 2", b"08 2"):
            with self.subTest(header=header):
                content = header + b"\n" + named(b"sample", b"AC")
                batch = decode(content)
                record = batch["records"][0]
                self.assertEqual(batch["end_state"], "source_semantics_unestablished")
                self.assertIsNone(record["native_status_equivalent"])
                self.assertTrue(record["header_valid"])
                self.assertEqual(record["rows"], [])
                self.assertIn("phylip_dimension_invalid", codes(record))
                self.assertEqual(batch["next_byte_offset"], len(header) + 1)

    def test_multiple_records_exact_offsets_and_failed_later_occurrence(self):
        for fmt in ("phylip", "phylips"):
            with self.subTest(fmt=fmt):
                first = b"1 2\r\n" + named(b"first", b"AC", b"\r\n") + b" \t\r\n"
                second = b"1 2\n" + named(b"second", b"GT", b"")
                content = first + second
                batch = decode(content, fmt)
                self.assertEqual([record["reader_state"] for record in batch["records"]], ["complete", "complete"])
                self.assertEqual(batch["records"][0]["byte_end"], len(first))
                self.assertEqual(batch["records"][1]["byte_start"], len(first))
                self.assertEqual(batch["records"][1]["line_start"], 4)
                self.assertEqual(batch["next_byte_offset"], len(content))
                self.assertEqual([record["record_ordinal"] for record in batch["records"]], [0, 1])
                for record in batch["records"]:
                    self.assert_source_spans(content, record)
                broken = first + b"broken\n" + second
                batch = decode(broken, fmt)
                self.assertEqual(batch["records"][0]["reader_state"], "complete")
                self.assertEqual(batch["records"][1]["reader_state"], "invalid")
                self.assertEqual(batch["records"][1]["native_status_equivalent"], 7)
                self.assertEqual(batch["next_byte_offset"], len(first) + len(b"broken\n"))
                self.assertEqual(batch["trailing_range"]["byte_end"], len(broken))
                partial = first + b"1 2\n" + named(b"second", b"A9") + b"suffix\n"
                batch = decode(partial, fmt)
                self.assertEqual([record["reader_state"] for record in batch["records"]],
                                 ["complete", "partial"])
                self.assertEqual(batch["records"][1]["rows"][0]["aligned_sequence"], "A")
                self.assertEqual(batch["next_byte_offset"], len(partial) - len(b"suffix\n"))

    def test_interleaved_overwidth_eof_and_suffix_are_distinct(self):
        first = b"1 2\n" + named(b"first", b"ACGT")
        eof_record = decode(first)["records"][0]
        self.assertEqual(eof_record["native_status_equivalent"], 7)
        self.assertEqual(eof_record["column_count"], 4)
        suffix = b"1 2\n" + named(b"second", b"GT")
        batch = decode(first + suffix)
        self.assertEqual(len(batch["records"]), 2)
        record = batch["records"][0]
        self.assertEqual(record["native_status_equivalent"], 0)
        self.assertEqual(record["reader_state"], "invalid")
        self.assertFalse(record["rows"][0]["geometry_valid"])
        self.assertEqual(record["declared_column_count"], 2)
        self.assertEqual(record["column_count"], 4)
        self.assertEqual(record["byte_end"], len(first))
        self.assertEqual(batch["records"][1]["reader_state"], "complete")

    def test_empty_and_nul_delimited_blank_inputs_have_no_occurrence(self):
        for fmt in ("phylip", "phylips"):
            for content in (b"", b"\n \t\r\n\x00\n"):
                with self.subTest(fmt=fmt, content=content):
                    batch = decode(content, fmt)
                    self.assertEqual(batch["records"], [])
                    self.assertEqual(batch["end_state"], "eof")
                    self.assertEqual(batch["next_byte_offset"], len(content))
                    self.assertIsNone(batch["trailing_range"])
                    self.assertEqual(batch["diagnostics"][0]["code"], "empty_alignment")
        content = b"\x00\n1 2\n\t\x00\n" + named(b"sample", b"AC") + b"\x00\n"
        record = self.assert_complete(decode(content), ["AC"])
        self.assertEqual(record["byte_start"], 0)
        self.assertEqual(record["byte_end"], len(content))
        self.assert_source_spans(content, record)

    def test_complete_population_is_not_a_first_record_sample(self):
        one = b"1 2\n" + named(b"same", b"AC")
        content = one * 130
        batch = decode(content)
        self.assertEqual(len(batch["records"]), 130)
        self.assertEqual(batch["records"][-1]["record_ordinal"], 129)
        self.assertEqual(batch["next_byte_offset"], len(content))
        self.assertTrue(all(record["reader_state"] == "complete" for record in batch["records"]))

    def test_closed_batch_and_diagnostic_shapes(self):
        batch = decode(b"1 2\n" + named(b"sample", b"A9"))
        self.assertEqual(set(batch), {"version", "format", "alphabet", "records", "diagnostics", "end_state", "next_byte_offset", "trailing_range"})
        record = batch["records"][0]
        self.assertEqual(set(record), {"record_ordinal", "reader_state", "native_status_equivalent", "byte_start", "byte_end", "line_start", "line_end", "header_valid", "column_count", "declared_row_count", "declared_column_count", "block_count", "rows", "column_annotations", "events", "diagnostics"})
        self.assertEqual(set(record["rows"][0]), {"row_ordinal", "name", "name_bytes_hex", "description", "aligned_sequence", "segments", "annotation_fragments", "column_annotations", "geometry_valid", "symbols_valid", "identity_unambiguous", "diagnostics"})
        diagnostic = record["diagnostics"][-1]
        self.assertEqual(set(diagnostic), {"code", "record_ordinal", "row_ordinal", "event_ordinal", "byte_start", "byte_end", "details"})
        self.assertEqual(set(diagnostic["details"]), {"expected", "actual", "token_hex"})
        self.assertEqual(diagnostic["details"]["token_hex"], "39")

    def test_argument_misuse_has_closed_errors(self):
        cases = [
            (("", "phylip", "DNA"), "hmmer_alignment_content_invalid"),
            ((bytearray(), "phylip", "DNA"), "hmmer_alignment_content_invalid"),
            ((b"", "PHYLIP", "DNA"), "hmmer_alignment_format_invalid"),
            ((b"", "relaxed", "DNA"), "hmmer_alignment_format_invalid"),
            ((b"", "phylip", "dna"), "hmmer_alignment_alphabet_invalid"),
            ((b"", "phylip", None), "hmmer_alignment_alphabet_invalid"),
        ]
        for (content, fmt, alphabet), expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(ValueError, "^" + expected + "$"):
                    decode_native_phylip_alignment(content, declared_format=fmt, alphabet=alphabet)


if __name__ == "__main__":
    unittest.main()
