"""Authored exact-result inputs for the retained Easel alphabet-open rules.

These fixtures are deliberately supplied test bytes, not scientific native
outputs.  Native execution, explicit-flag bypass, status 26, and integration
remain separate root-owned checks.  No fixture allocates a native-overflow-size
alignment; standalone histogram tests cover the representable count boundary.
"""

import json
from unittest import TestCase

from gene_annotation_episode.hmmer_alignment_input_alphabet import (
    classify_easel_alphabet_counts,
    infer_hmmer_alignment_alphabet,
)


FORMATS = (
    "stockholm", "pfam", "afa", "a2m", "psiblast", "selex",
    "clustal", "clustallike", "phylip", "phylips",
)


def histogram(**letters):
    """Place explicitly supplied expected counts in their A--Z slots."""
    return [letters.get(chr(65 + index), 0) for index in range(26)]


def checkpoint(counts, *, threshold, line, byte_end, alphabet, rule):
    return {
        "threshold": threshold,
        "at_eof": threshold is None,
        "line": line,
        "byte_end": byte_end,
        "counts_az": counts,
        "state": "determined" if alphabet is not None else "undetermined",
        "alphabet": alphabet,
        "rule": rule,
    }


def eof_probe(fmt, counts, *, line, byte_end, alphabet, rule):
    return {
        "version": "hmmer_native_alignment_alphabet_probe_v1",
        "format": fmt,
        "state": "determined" if alphabet is not None else "undetermined",
        "alphabet": alphabet,
        "counts_az": counts,
        "counted_letters": sum(counts),
        "checkpoints": [checkpoint(
            counts.copy(), threshold=None, line=line, byte_end=byte_end,
            alphabet=alphabet, rule=rule,
        )],
        "scan_end_byte": byte_end,
        "stopped_at": "eof",
        "diagnostics": [],
    }


class AlphabetCountTests(TestCase):
    def assert_classification(self, counts, alphabet, rule):
        self.assertEqual(classify_easel_alphabet_counts(counts), {
            "alphabet": alphabet,
            "status": "determined" if alphabet is not None else "undetermined",
            "rule": rule,
        })

    def test_a01_ten_vs_eleven_and_unknown_without_a_native_rule(self):
        self.assert_classification(histogram(), None, "short_sample")
        self.assert_classification(histogram(O=10), None, "short_sample")
        self.assert_classification(histogram(O=11), "amino", "aa_only_letter")
        self.assert_classification(histogram(A=3, C=3, G=2, T=2), None, "short_sample")
        self.assert_classification(histogram(A=4, C=3, G=2, T=2), "DNA", "dna_canonical_fraction")
        self.assert_classification(histogram(A=11), None, "undetermined")
        self.assert_classification(histogram(B=8000), None, "undetermined")

    def test_a02_all_n_special_case_is_strictly_above_2000(self):
        self.assert_classification(histogram(N=2000), None, "undetermined")
        self.assert_classification(histogram(N=2001), "DNA", "all_n_dna")
        self.assert_classification(histogram(N=2001, B=1), None, "undetermined")

    def test_a02_all_nine_aa_only_letters_including_o_and_i_take_precedence(self):
        for letter in "EFIJLOPQZ":
            with self.subTest(letter=letter):
                counts = histogram(A=24, C=25, G=25, T=25, **{letter: 1})
                self.assert_classification(counts, "amino", "aa_only_letter")

    def test_a03_exact_two_percent_and_required_four_canonical_letters(self):
        for terminal, alphabet, rule in (
            ("T", "DNA", "dna_canonical_fraction"),
            ("U", "RNA", "rna_canonical_fraction"),
        ):
            with self.subTest(alphabet=alphabet):
                self.assert_classification(
                    histogram(A=24, C=24, G=24, B=2, **{terminal: 26}), alphabet, rule,
                )
                self.assert_classification(
                    histogram(A=24, C=24, G=24, B=3, **{terminal: 25}), None, "undetermined",
                )
                self.assert_classification(
                    histogram(A=49, C=24, G=24, B=2, **{terminal: 1}), alphabet, rule,
                )
                self.assert_classification(
                    histogram(A=50, C=24, G=24, B=2), None, "undetermined",
                )
                self.assert_classification(
                    histogram(A=49, C=24, N=2, **{terminal: 25}), None, "undetermined",
                )

    def test_a03_dna_rule_precedes_rna_when_both_qualify(self):
        self.assert_classification(
            histogram(A=96, C=1, G=1, T=1, U=1), "DNA", "dna_canonical_fraction",
        )

    def test_a03_amino_diversity_fifteenth_letter_is_preempted_by_aa_only(self):
        # Without aa-only letters there are at most 3 + 9 + N + T = 14.
        # This exact source branch is unreachable, even when n3 > n2.
        fourteen = dict.fromkeys("ACGDHKMRSVWYNT", 1)
        fourteen["H"] = 21
        self.assert_classification(histogram(**fourteen), None, "undetermined")
        self.assert_classification(histogram(**fourteen, X=10), None, "undetermined")
        self.assert_classification(histogram(**fourteen, E=1), "amino", "aa_only_letter")
        fourteen.update(A=3, C=3, G=3, H=1)  # n3 == n2 also cannot qualify.
        self.assert_classification(histogram(**fourteen), None, "undetermined")
        fourteen["A"] = 4  # n3 < n2.
        self.assert_classification(histogram(**fourteen), None, "undetermined")

    def test_argument_counts_are_closed_and_not_coerced(self):
        bad_values = [None, {}, "A" * 26, tuple([0] * 26), [0] * 25, [0] * 27]
        for value in (True, False, -1, 1.0, "1", None):
            bad_values.append([value] + [0] * 25)
        for counts in bad_values:
            with self.subTest(counts=counts):
                with self.assertRaisesRegex(ValueError, "^hmmer_alignment_counts_invalid$"):
                    classify_easel_alphabet_counts(counts)

    def test_native_integer_domain_is_explicit_without_an_arbitrary_count_cap(self):
        unavailable = {
            "alphabet": None, "status": "source_semantics_unestablished",
            "rule": "native_count_range_unestablished",
        }
        for letter in "EFIJLOPQZACGDHKMRSVWY":
            with self.subTest(letter=letter):
                self.assertEqual(
                    classify_easel_alphabet_counts(histogram(**{letter: 2147483648})),
                    unavailable,
                )
        self.assert_classification(histogram(A=2147483647), None, "undetermined")
        self.assert_classification(histogram(O=2147483647), "amino", "aa_only_letter")
        for letter in "BTUX":
            with self.subTest(not_narrowed=letter):
                self.assert_classification(
                    histogram(**{letter: 9223372036854775807}), None, "undetermined",
                )
        self.assert_classification(histogram(N=9223372036854775807), "DNA", "all_n_dna")
        self.assertEqual(
            classify_easel_alphabet_counts(histogram(N=9223372036854775807, T=1)),
            unavailable,
        )
        self.assertEqual(classify_easel_alphabet_counts(histogram(N=10**400)), unavailable)


class AlphabetProbeTests(TestCase):
    def assert_eof(self, content, fmt, counts, *, line, alphabet, rule):
        self.assertEqual(
            infer_hmmer_alignment_alphabet(content, declared_format=fmt),
            eof_probe(fmt, counts, line=line, byte_end=len(content), alphabet=alphabet, rule=rule),
        )

    def test_a01_empty_and_blank_sources_preserve_actual_classifier_attempts(self):
        header_formats = {"clustal", "clustallike", "phylip", "phylips"}
        for fmt in FORMATS:
            for content, line in ((b"", None), (b"\n \t\x00\r\n", 2)):
                with self.subTest(fmt=fmt, content=content):
                    expected = eof_probe(
                        fmt, histogram(), line=line, byte_end=len(content),
                        alphabet=None, rule="short_sample",
                    )
                    if fmt in header_formats:
                        expected["checkpoints"] = []
                    self.assertEqual(
                        infer_hmmer_alignment_alphabet(content, declared_format=fmt), expected,
                    )
        for fmt in header_formats:
            with self.subTest(header_only=fmt):
                self.assert_eof(b"ignored header\n", fmt, histogram(), line=1,
                                alphabet=None, rule="short_sample")

    def test_line_extent_keeps_crlf_unterminated_tail_and_ascii_controls(self):
        self.assert_eof(b">id\r\nacgTACgtACGT", "afa", histogram(A=3, C=3, G=3, T=3),
                        line=2, alphabet="DNA", rule="dna_canonical_fraction")
        self.assert_eof(b">q\nACGT\rACGT\vACGT\fACGT", "afa", histogram(A=4, C=4, G=4, T=4),
                        line=2, alphabet="DNA", rule="dna_canonical_fraction")

    def test_a04_500_vs_501_and_first_success_stops_before_unexamined_suffix(self):
        first = b">q\n" + b"ACGT" * 125 + b"\n"
        self.assert_eof(first, "afa", histogram(A=125, C=125, G=125, T=125),
                        line=2, alphabet="DNA", rule="dna_canonical_fraction")
        content = first + b"a\n\xffE\n"
        counts = histogram(A=126, C=125, G=125, T=125)
        expected = eof_probe("afa", counts, line=3, byte_end=506,
                             alphabet="DNA", rule="dna_canonical_fraction")
        expected["stopped_at"] = "checkpoint"
        expected["checkpoints"][0].update(threshold=500, at_eof=False)
        self.assertEqual(infer_hmmer_alignment_alphabet(content, declared_format="afa"), expected)

    def test_a04_a05_strict_thresholds_and_eof_after_50000_are_not_sample_caps(self):
        content = b"\n".join((b"A" * 500, b"A", b"A" * 4499, b"A", b"A" * 44999, b"A", b"E")) + b"\n"
        expected = eof_probe("afa", histogram(A=50001, E=1), line=7, byte_end=50009,
                             alphabet="amino", rule="aa_only_letter")
        expected["checkpoints"] = [
            checkpoint(histogram(A=501), threshold=500, line=2, byte_end=503,
                       alphabet=None, rule="undetermined"),
            checkpoint(histogram(A=5001), threshold=5000, line=4, byte_end=5005,
                       alphabet=None, rule="undetermined"),
            checkpoint(histogram(A=50001), threshold=50000, line=6, byte_end=50007,
                       alphabet=None, rule="undetermined"),
            checkpoint(histogram(A=50001, E=1), threshold=None, line=7, byte_end=50009,
                       alphabet="amino", rule="aa_only_letter"),
        ]
        self.assertEqual(infer_hmmer_alignment_alphabet(content, declared_format="afa"), expected)

    def test_a04_one_huge_line_attempts_only_one_threshold_then_eof(self):
        content = b"A" * 60000 + b"\r\n"
        expected = eof_probe("afa", histogram(A=60000), line=1, byte_end=60002,
                             alphabet=None, rule="undetermined")
        expected["checkpoints"].insert(0, checkpoint(
            histogram(A=60000), threshold=500, line=1, byte_end=60002,
            alphabet=None, rule="undetermined",
        ))
        self.assertEqual(infer_hmmer_alignment_alphabet(content, declared_format="afa"), expected)

    def test_a05_ignored_tail_extends_scan_beyond_last_threshold_checkpoint(self):
        content = b"A" * 501 + b"\n>EEEEEEEEEEE\n\n"
        expected = eof_probe("afa", histogram(A=501), line=3, byte_end=516,
                             alphabet=None, rule="undetermined")
        expected["checkpoints"].insert(0, checkpoint(
            histogram(A=501), threshold=500, line=1, byte_end=502,
            alphabet=None, rule="undetermined",
        ))
        self.assertEqual(infer_hmmer_alignment_alphabet(content, declared_format="afa"), expected)

    def test_a04_token_only_lines_can_check_but_blank_and_comment_lines_cannot(self):
        content = b"s " + b"A" * 60000 + b"\n\n#ignored E\nonlyname\nonlyname\n"
        expected = eof_probe("stockholm", histogram(A=60000), line=5, byte_end=60033,
                             alphabet=None, rule="undetermined")
        expected["checkpoints"] = [
            checkpoint(histogram(A=60000), threshold=500, line=1, byte_end=60003,
                       alphabet=None, rule="undetermined"),
            checkpoint(histogram(A=60000), threshold=5000, line=4, byte_end=60024,
                       alphabet=None, rule="undetermined"),
            checkpoint(histogram(A=60000), threshold=50000, line=5, byte_end=60033,
                       alphabet=None, rule="undetermined"),
            checkpoint(histogram(A=60000), threshold=None, line=5, byte_end=60033,
                       alphabet=None, rule="undetermined"),
        ]
        self.assertEqual(infer_hmmer_alignment_alphabet(content, declared_format="stockholm"), expected)

    def test_a06_later_stockholm_record_and_malformed_suffix_affect_first_open(self):
        first = b"# STOCKHOLM 1.0\ns ACGT\n//\n"
        second = b"# STOCKHOLM 1.0\ns ACGTACGT\n//\n"
        for fmt in ("stockholm", "pfam"):
            with self.subTest(fmt=fmt):
                self.assert_eof(first, fmt, histogram(A=1, C=1, G=1, T=1),
                                line=3, alphabet=None, rule="short_sample")
                self.assert_eof(first + second, fmt, histogram(A=3, C=3, G=3, T=3),
                                line=6, alphabet="DNA", rule="dna_canonical_fraction")
                self.assert_eof(first + b"garbage EEEEEEEEEEE\n", fmt,
                                histogram(A=1, C=1, G=1, T=1, E=11),
                                line=4, alphabet="amino", rule="aa_only_letter")
                self.assert_eof(first + b"// EEEEEEEEEEE", fmt,
                                histogram(A=1, C=1, G=1, T=1, E=11),
                                line=4, alphabet="amino", rule="aa_only_letter")

    def test_a07_fasta_leading_c_whitespace_and_a2m_o_are_native_scan_bytes(self):
        content = b"\t >E-name E-description \xff\n\v\f\rACGTACGTACGT\n"
        for fmt in ("afa", "a2m"):
            with self.subTest(fmt=fmt):
                self.assert_eof(content, fmt, histogram(A=3, C=3, G=3, T=3),
                                line=2, alphabet="DNA", rule="dna_canonical_fraction")
        self.assert_eof(b">q\nACGTACGTACGTOo\n", "a2m", histogram(A=3, C=3, G=3, T=3, O=2),
                        line=2, alphabet="amino", rule="aa_only_letter")

    def test_a07_token_names_comments_and_indented_selex_comment_are_distinct(self):
        content = b" \t#comment EEEEEEEEEEE\nE-name ACGTACGTACGT\n"
        for fmt in ("stockholm", "pfam", "selex"):
            with self.subTest(fmt=fmt):
                self.assert_eof(content, fmt, histogram(A=3, C=3, G=3, T=3),
                                line=2, alphabet="DNA", rule="dna_canonical_fraction")
        self.assert_eof(content, "psiblast", histogram(A=3, C=3, G=3, T=3, E=11),
                        line=2, alphabet="amino", rule="aa_only_letter")

    def test_a07_clustal_header_is_unvalidated_and_all_tail_tokens_are_counted(self):
        content = b"\n \t\n\xff EEEEEEEEEEE\nE-name ACGTACGTACGT EoI\n"
        for fmt in ("clustal", "clustallike"):
            with self.subTest(fmt=fmt):
                self.assert_eof(content, fmt, histogram(A=3, C=3, G=3, T=3, E=1, O=1, I=1),
                                line=4, alphabet="amino", rule="aa_only_letter")

    def test_a07_phylip_continuations_always_lose_first_ten_bytes_in_probe(self):
        content = b" not a header EEE\nABCDEFGHIJACGTACGTACGT\nEEEEEEEEEEacgtacgtacgt\nshortEE\n"
        for fmt in ("phylip", "phylips"):
            with self.subTest(fmt=fmt):
                self.assert_eof(content, fmt, histogram(A=6, C=6, G=6, T=6),
                                line=4, alphabet="DNA", rule="dna_canonical_fraction")
                self.assert_eof(content + b"0123456789E\n", fmt,
                                histogram(A=6, C=6, G=6, T=6, E=1),
                                line=5, alphabet="amino", rule="aa_only_letter")

    def test_native_nul_token_delimiter_does_not_become_c_whitespace(self):
        for fmt in ("stockholm", "pfam", "selex", "psiblast"):
            with self.subTest(fmt=fmt):
                self.assert_eof(b"\x00\ts\x00ACGTACGTACGT\n", fmt, histogram(A=3, C=3, G=3, T=3),
                                line=1, alphabet="DNA", rule="dna_canonical_fraction")
        for fmt in ("afa", "a2m"):
            with self.subTest(not_c_whitespace=fmt):
                self.assert_eof(b"\x00>EEEEEEEEEEE\n", fmt, histogram(E=11),
                                line=1, alphabet="amino", rule="aa_only_letter")
        for fmt in ("clustal", "clustallike"):
            with self.subTest(nul_blank_header=fmt):
                self.assert_eof(b"\x00\nbadheader EEEEEEEEEEE\ns ACGTACGTACGT\n", fmt,
                                histogram(A=3, C=3, G=3, T=3),
                                line=3, alphabet="DNA", rule="dna_canonical_fraction")
        for fmt in ("phylip", "phylips"):
            with self.subTest(nul_blank_header=fmt):
                self.assert_eof(b"\x00\n0123456789EEEEEEEEEEE\nabcdefghijACGTACGTACGT\n", fmt,
                                histogram(A=3, C=3, G=3, T=3),
                                line=3, alphabet="DNA", rule="dna_canonical_fraction")

    def test_nonascii_scanned_byte_preserves_prefix_and_fetched_line_extent(self):
        content = b">q\n" + b"A" * 501 + b"\n\xffE\n"
        expected = {
            "version": "hmmer_native_alignment_alphabet_probe_v1",
            "format": "afa", "state": "source_semantics_unestablished", "alphabet": None,
            "counts_az": histogram(A=501), "counted_letters": 501,
            "checkpoints": [checkpoint(histogram(A=501), threshold=500, line=2, byte_end=505,
                                       alphabet=None, rule="undetermined")],
            "scan_end_byte": 508, "stopped_at": "unestablished_byte_semantics",
            "diagnostics": [{
                "code": "native_source_semantics_unestablished",
                "record_ordinal": None, "row_ordinal": None, "event_ordinal": None,
                "byte_start": 505, "byte_end": 506,
                "details": {"expected": "ascii_ctype", "actual": 255, "token_hex": "ff"},
            }],
        }
        self.assertEqual(infer_hmmer_alignment_alphabet(content, declared_format="afa"), expected)
        content = b">q\r\nACG\xffT\n"
        expected.update(counts_az=histogram(A=1, C=1, G=1), counted_letters=3,
                        checkpoints=[], scan_end_byte=10)
        expected["diagnostics"][0].update(byte_start=7, byte_end=8)
        self.assertEqual(infer_hmmer_alignment_alphabet(content, declared_format="afa"), expected)

    def test_nonascii_payload_failure_is_local_to_each_native_scan_region(self):
        for fmt in FORMATS:
            if fmt in {"afa", "a2m"}:
                prefix, line = b">q\n", 2
            elif fmt in {"clustal", "clustallike"}:
                prefix, line = b"header\ns ", 2
            elif fmt in {"phylip", "phylips"}:
                prefix, line = b"1 4\n0123456789", 2
            else:
                prefix, line = b"s ", 1
            content = prefix + b"ACG\xffT\n"
            byte_start = len(prefix) + 3
            expected = eof_probe(fmt, histogram(A=1, C=1, G=1), line=line, byte_end=len(content),
                                 alphabet=None, rule="short_sample")
            expected.update(state="source_semantics_unestablished", checkpoints=[],
                            stopped_at="unestablished_byte_semantics", diagnostics=[{
                                "code": "native_source_semantics_unestablished",
                                "record_ordinal": None, "row_ordinal": None, "event_ordinal": None,
                                "byte_start": byte_start, "byte_end": byte_start + 1,
                                "details": {"expected": "ascii_ctype", "actual": 255, "token_hex": "ff"},
                            }])
            with self.subTest(fmt=fmt):
                self.assertEqual(infer_hmmer_alignment_alphabet(content, declared_format=fmt), expected)

    def test_nonascii_leading_ctype_is_unestablished_but_unscanned_names_are_safe(self):
        content = b"\t\xff>header E\n"
        expected = eof_probe("a2m", histogram(), line=1, byte_end=len(content),
                             alphabet=None, rule="short_sample")
        expected.update(state="source_semantics_unestablished", checkpoints=[],
                        stopped_at="unestablished_byte_semantics", diagnostics=[{
                            "code": "native_source_semantics_unestablished",
                            "record_ordinal": None, "row_ordinal": None, "event_ordinal": None,
                            "byte_start": 1, "byte_end": 2,
                            "details": {"expected": "ascii_ctype", "actual": 255, "token_hex": "ff"},
                        }])
        self.assertEqual(infer_hmmer_alignment_alphabet(content, declared_format="a2m"), expected)
        self.assert_eof(b"\xffname ACGTACGTACGT\n", "stockholm", histogram(A=3, C=3, G=3, T=3),
                        line=1, alphabet="DNA", rule="dna_canonical_fraction")
        self.assert_eof(b"1 12\n" + b"\xff" * 10 + b"ACGTACGTACGT\n\xffshort\n", "phylip",
                        histogram(A=3, C=3, G=3, T=3), line=3,
                        alphabet="DNA", rule="dna_canonical_fraction")

    def test_probe_does_not_validate_sequence_grammar_or_treat_byte_controls_as_letters(self):
        self.assert_eof(b">q\nACGT1234-*._~?\x00ACGTACGT", "afa", histogram(A=3, C=3, G=3, T=3),
                        line=2, alphabet="DNA", rule="dna_canonical_fraction")
        # CR/VT/FF inside a first token are not native space/tab delimiters.
        self.assert_eof(b"name\rE\vE\fE ACGTACGTACGT\n", "stockholm",
                        histogram(A=3, C=3, G=3, T=3), line=1,
                        alphabet="DNA", rule="dna_canonical_fraction")

    def test_saved_histograms_reclassify_without_source_and_snapshots_are_independent(self):
        probe = infer_hmmer_alignment_alphabet(b"A" * 501 + b"\nE\n", declared_format="afa")
        saved = json.loads(json.dumps(probe))
        self.assertEqual(saved["counts_az"], histogram(A=501, E=1))
        self.assertEqual(saved["counted_letters"], 502)
        self.assertEqual(saved["checkpoints"][0]["counts_az"], histogram(A=501))
        for snapshot in saved["checkpoints"]:
            with self.subTest(at_eof=snapshot["at_eof"]):
                self.assertEqual(classify_easel_alphabet_counts(snapshot["counts_az"]), {
                    "alphabet": snapshot["alphabet"], "status": snapshot["state"], "rule": snapshot["rule"],
                })
        saved["counts_az"][0] = 0
        self.assertEqual(saved["checkpoints"][-1]["counts_az"], histogram(A=501, E=1))

    def test_argument_content_and_declared_format_are_not_coerced(self):
        for content in (None, "ACGT", bytearray(b"ACGT"), memoryview(b"ACGT"), []):
            with self.subTest(content=content):
                with self.assertRaisesRegex(ValueError, "^hmmer_alignment_content_invalid$"):
                    infer_hmmer_alignment_alphabet(content, declared_format="afa")
        for fmt in (None, "AFA", "fasta", "unknown", b"afa", [], {}):
            with self.subTest(fmt=fmt):
                with self.assertRaisesRegex(ValueError, "^hmmer_alignment_format_invalid$"):
                    infer_hmmer_alignment_alphabet(b"", declared_format=fmt)
