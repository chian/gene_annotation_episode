"""Synthetic, source-derived fixtures; these are not captured native outputs.

Expected trees follow the retained Easel cluster_engine scan/swap order.
Expected weights are raw operands, before the shared native normalizer. Native
conformance and the complete parser/driver/sheet/return path require separate
root-owned verification; authoring this file does not establish those results.
"""
from __future__ import annotations

import math
from unittest import TestCase

from gene_annotation_episode.hmmer_alignment_tree_weights import (
    blosum_raw_weights,
    gsc_raw_weights,
)


DNA = "ACGTRYMKSWHBVDN"


class TreeWeightFixtures(TestCase):
    def test_singleton_early_return_has_explicit_derived_diagnostics(self):
        for sequence in ("A", "---", "~*-"):
            with self.subTest(sequence=sequence):
                self.assertEqual(gsc_raw_weights([sequence], residue_symbols=DNA), {
                    "raw_weights": [1.0],
                    "tree": {"children": [], "branches": [], "clade_sizes": []},
                })
                self.assertEqual(blosum_raw_weights(
                    [sequence], residue_symbols=DNA, identity_cutoff=1.0), {
                        "raw_weights": [1.0],
                        "clusters": {"assignment": [0], "sizes": [1], "identity_cutoff": 1.0},
                    })

    def test_pair_identity_denominator_is_minimum_residue_count(self):
        # One identity / min(3,2) = 1/2, not 1/4 columns or 1/1 paired sites.
        sequences = ["A-CG", "AT--"]
        self.assertEqual(gsc_raw_weights(sequences, residue_symbols=DNA), {
            "raw_weights": [0.25, 0.25],
            "tree": {"children": [[0, -1]], "branches": [[0.25, 0.25]], "clade_sizes": [2]},
        })
        self.assertEqual(blosum_raw_weights(
            sequences, residue_symbols=DNA, identity_cutoff=0.5)["raw_weights"], [0.5, 0.5])
        self.assertEqual(blosum_raw_weights(
            sequences, residue_symbols=DNA, identity_cutoff=math.nextafter(0.5, 1.0))["raw_weights"],
            [1.0, 1.0])
        self.assertEqual(gsc_raw_weights(["AC--", "ACGT"], residue_symbols=DNA)["raw_weights"],
                         [0.0, 0.0])

    def test_gsc_equal_distances_preserve_native_scan_and_swap_topology(self):
        # Every off-diagonal distance is 1. Strict-< chooses active pair (0,1)
        # each time; j-then-i swaps make the next cherry taxa 2/3, not 0/2.
        self.assertEqual(gsc_raw_weights(["A", "C", "G", "T"], residue_symbols=DNA), {
            "raw_weights": [0.5, 0.5, 0.5, 0.5],
            "tree": {
                "children": [[2, 1], [-2, -3], [0, -1]],
                "branches": [[0.0, 0.0], [0.5, 0.5], [0.5, 0.5]],
                "clade_sizes": [4, 2, 2],
            },
        })

    def test_gsc_identical_residues_remain_raw_zero_for_common_normalizer(self):
        self.assertEqual(gsc_raw_weights(["N", "N", "N", "N"], residue_symbols=DNA), {
            "raw_weights": [0.0, 0.0, 0.0, 0.0],
            "tree": {
                "children": [[2, 1], [-2, -3], [0, -1]],
                "branches": [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]],
                "clade_sizes": [4, 2, 2],
            },
        })

    def test_zero_length_subtree_splits_positive_inherited_weight_by_clade_size(self):
        # The zero-length, three-taxon A subtree inherits 1/2 from its parent.
        # Its uneven 1+2 child sizes must still give each A row exactly 1/6.
        self.assertEqual(gsc_raw_weights(["A", "A", "A", "C"], residue_symbols=DNA), {
            "raw_weights": [1.0 / 6.0, 1.0 / 6.0, 1.0 / 6.0, 0.5],
            "tree": {
                "children": [[-3, 1], [-2, 2], [0, -1]],
                "branches": [[0.5, 0.5], [0.0, 0.0], [0.0, 0.0]],
                "clade_sizes": [4, 3, 2],
            },
        })

    def test_upgma_uses_clade_sizes_in_merged_distances(self):
        # AAAC joins the two AAAA rows at distance 1/4. Its three-taxon clade
        # meets CCCC at (3/4 + 1 + 1)/3 = 11/12, not unweighted 7/8.
        result = gsc_raw_weights(["AAAA", "AAAA", "AAAC", "CCCC"], residue_symbols=DNA)
        self.assertEqual(result["tree"], {
            "children": [[-3, 1], [-2, 2], [0, -1]],
            "branches": [[11.0 / 24.0, 11.0 / 24.0 - 1.0 / 8.0],
                         [1.0 / 8.0, 1.0 / 8.0], [0.0, 0.0]],
            "clade_sizes": [4, 3, 2],
        })
        for actual, expected in zip(result["raw_weights"], [7.0 / 48.0, 7.0 / 48.0, 7.0 / 24.0, 11.0 / 24.0]):
            self.assertAlmostEqual(actual, expected, places=15)

    def test_all_gap_missing_and_nonresidue_pairs_have_native_zero_identity(self):
        self.assertEqual(gsc_raw_weights(["--", "~*", "**"], residue_symbols=DNA), {
            "raw_weights": [0.5, 0.5, 0.5],
            "tree": {
                "children": [[-2, 1], [0, -1]],
                "branches": [[0.5, 0.0], [0.5, 0.5]],
                "clade_sizes": [3, 2],
            },
        })
        distinct = blosum_raw_weights(["--", "~*", "**"], residue_symbols=DNA, identity_cutoff=1.0)
        self.assertEqual(distinct["clusters"]["assignment"], [0, 1, 2])
        self.assertEqual(distinct["raw_weights"], [1.0, 1.0, 1.0])
        linked = blosum_raw_weights(["--", "~*", "**"], residue_symbols=DNA, identity_cutoff=0.0)
        self.assertEqual(linked["clusters"]["assignment"], [0, 0, 0])
        self.assertEqual(linked["raw_weights"], [1.0 / 3.0] * 3)

    def test_degenerate_codes_count_only_exact_matches(self):
        sequences = ["N-*~", "N-**", "A-~*"]
        self.assertEqual(gsc_raw_weights(sequences, residue_symbols=DNA)["raw_weights"], [0.25, 0.25, 0.5])
        self.assertEqual(blosum_raw_weights(sequences, residue_symbols=DNA, identity_cutoff=1.0), {
            "raw_weights": [0.5, 0.5, 1.0],
            "clusters": {"assignment": [0, 0, 1], "sizes": [2, 1], "identity_cutoff": 1.0},
        })
        self.assertEqual(gsc_raw_weights(["R", "N"], residue_symbols=DNA)["raw_weights"], [0.5, 0.5])

    def test_blosum_transitive_links_cross_a_nonlinked_endpoint_pair(self):
        # Id(0,1)=Id(1,2)=1/2, Id(0,2)=0; row 3 is a separate cluster.
        sequences = ["AAAA", "AACC", "CCCC", "GGGG"]
        self.assertEqual(blosum_raw_weights(sequences, residue_symbols=DNA, identity_cutoff=0.5), {
            "raw_weights": [1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0, 1.0],
            "clusters": {"assignment": [0, 0, 0, 1], "sizes": [3, 1], "identity_cutoff": 0.5},
        })
        self.assertEqual(blosum_raw_weights(sequences, residue_symbols=DNA, identity_cutoff=1.0), {
            "raw_weights": [1.0, 1.0, 1.0, 1.0],
            "clusters": {"assignment": [0, 1, 2, 3], "sizes": [1, 1, 1, 1], "identity_cutoff": 1.0},
        })

    def test_blosum_cluster_ids_follow_native_deletion_swaps(self):
        # Removing linked row 3 swaps row 1 into its slot. Native's next seed
        # is then row 2: canonicalizing component IDs by minimum row is wrong.
        self.assertEqual(blosum_raw_weights(
            ["A", "C", "G", "A", "T"], residue_symbols=DNA, identity_cutoff=1.0), {
                "raw_weights": [0.5, 1.0, 1.0, 0.5, 1.0],
                "clusters": {"assignment": [0, 2, 1, 0, 3], "sizes": [2, 1, 1, 1], "identity_cutoff": 1.0},
            })

    def test_input_order_is_preserved_and_input_rows_are_not_changed(self):
        sequences = ["C", "A", "A"]
        before = list(sequences)
        self.assertEqual(gsc_raw_weights(sequences, residue_symbols=DNA)["raw_weights"], [0.5, 0.25, 0.25])
        self.assertEqual(blosum_raw_weights(
            sequences, residue_symbols=DNA, identity_cutoff=1.0)["raw_weights"], [1.0, 0.5, 0.5])
        self.assertEqual(sequences, before)

    def test_malformed_alignment_fails_with_closed_code(self):
        for sequences in (None, "A", ("A",), [], [""], ["A", "AA"], ["A", 1], ["a"], ["."], ["?"], ["A\x00"]):
            with self.subTest(sequences=sequences):
                with self.assertRaisesRegex(ValueError, "^alignment_invalid$"):
                    gsc_raw_weights(sequences, residue_symbols=DNA)
                with self.assertRaisesRegex(ValueError, "^alignment_invalid$"):
                    blosum_raw_weights(sequences, residue_symbols=DNA, identity_cutoff=0.5)

    def test_invalid_residue_settings_fail_without_guessing_alphabet(self):
        for residues in (None, "", "AA", "A-", "A~", "A*", "A C", "acgt", "Aé", ["A"]):
            with self.subTest(residues=residues):
                with self.assertRaisesRegex(ValueError, "^settings_invalid$"):
                    gsc_raw_weights(["A"], residue_symbols=residues)
                with self.assertRaisesRegex(ValueError, "^settings_invalid$"):
                    blosum_raw_weights(["A"], residue_symbols=residues, identity_cutoff=0.5)

    def test_invalid_cutoffs_fail_even_for_singleton_early_return(self):
        for cutoff in (None, True, False, "0.5", -0.01, 1.01, float("nan"), float("inf"), -float("inf"), 10 ** 400):
            with self.subTest(cutoff=cutoff):
                with self.assertRaisesRegex(ValueError, "^settings_invalid$"):
                    blosum_raw_weights(["A"], residue_symbols=DNA, identity_cutoff=cutoff)

    def test_integer_endpoint_cutoff_is_recorded_as_float(self):
        result = blosum_raw_weights(["A", "C", "-"], residue_symbols=DNA, identity_cutoff=0)
        self.assertEqual(result["raw_weights"], [1.0 / 3.0] * 3)
        self.assertIs(type(result["clusters"]["identity_cutoff"]), float)
