"""Native examples and explicit synthetic counterexamples for pure readers.

No fixture here is evidence of a live BV-BRC task or an episode result return.
The large retained examples are read completely, not sampled into toy matrices.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from gene_annotation_episode import phylogeny_formats as formats
from gene_annotation_episode.phylogeny_format_contracts import (
    validate_alignment_document, validate_tree_record,
)
from gene_annotation_episode.bvbrc_appservice_contracts import validate_contract


def artifact(data, name="synthetic"):
    return {"raw_artifact_ref": "artifact:" + name, "source_ref": "source:" + name,
            "sha256": hashlib.sha256(data).hexdigest()}


def read(function, data, **kwargs):
    return function(data, artifact=artifact(data), **kwargs)


def newick(data, **kwargs):
    return read(formats.parse_newick, data, dialect=kwargs.pop("dialect", "newick"), **kwargs)


def fasta(data, **kwargs):
    return read(formats.parse_aligned_fasta, data, id_rule="first_whitespace_token", **kwargs)


def phylip(data, **kwargs):
    return read(formats.parse_relaxed_phylip, data,
                layout=kwargs.pop("layout", "interleaved"),
                continuation_ids=kwargs.pop("continuation_ids", "absent"), **kwargs)


def xml(data):
    return read(formats.parse_phyloxml, data)


def codes(result):
    return [d["code"] for d in result["diagnostics"]]


def native_root():
    for directory in Path(__file__).resolve().parents:
        candidate = directory / "verification/tool_graders_bvbrc_phylogeny_boundaries_2026-10-24"
        if candidate.is_dir():
            return candidate
    raise AssertionError("Retained native fixtures missing; do not silently skip native verification")


class ShapeAssertions(unittest.TestCase):
    def assert_result(self, result, expected):
        self.assertEqual(result["status"], expected, result["diagnostics"])
        self.assertEqual(set(result), {"status", "value", "diagnostics"})
        json.dumps(result, allow_nan=False)
        for diagnostic in result["diagnostics"]:
            self.assertIn(diagnostic["code"], formats.DIAGNOSTIC_CODES)
            self.assertEqual(diagnostic, validate_contract("Diagnostic", diagnostic))


class NewickTests(ShapeAssertions):
    def test_zero_missing_negative_labels_comments_and_bytes(self):
        data = "\n[&R][pre]( 'é':+0.0, 'a''b':-1e-3, 'é', '':-0.0 )'0':5;\n[post]".encode()
        result = newick(data)
        self.assert_result(result, "ok")
        tree = result["value"]["trees"][0]
        nodes = tree["nodes"]
        self.assertEqual([n["node_index"] for n in nodes], [0, 1, 2, 3, 4])
        self.assertEqual(nodes[0]["child_indices"], [1, 2, 3, 4])
        self.assertEqual([n["decoded_label"] for n in nodes], ["0", "é", "a'b", "é", ""])
        self.assertEqual(nodes[2]["raw_label"], "a''b")
        self.assertEqual(nodes[2]["label_token"], "'a''b'")
        self.assertEqual([n["branch_length"] for n in nodes], [5, 0, -0.001, None, 0])
        self.assertEqual(math.copysign(1, nodes[4]["branch_length"]), -1)
        self.assertEqual([n["branch_length_token"] for n in nodes], ["5", "+0.0", "-1e-3", None, "-0.0"])
        self.assertEqual(tree["native_rooted_marker"], "rooted")
        self.assertIn("phylogeny_negative_branch_length", codes(result))
        self.assertEqual([c["position"] for c in nodes[0]["comments"]], ["before_tree", "before_tree", "after_tree"])
        for node in nodes:
            loc = node["source_location"]
            self.assertEqual(loc["artifact"], artifact(data))
            if node["label_token"] is not None:
                self.assertIn(node["label_token"].encode(), data[loc["byte_start_0based"]:loc["byte_end_0based_exclusive"]])
        self.assertEqual(validate_tree_record(tree), tree)

    def test_internal_labels_not_support_and_comments_not_labels(self):
        result = newick(b"([before]A[after]:0[length],(B,C)0:1[100])root;", dialect="raxml_branch_labels")
        self.assert_result(result, "ok")
        nodes = result["value"]["trees"][0]["nodes"]
        self.assertEqual(nodes[2]["decoded_label"], "0")
        self.assertEqual(nodes[2]["comments"][0]["text"], "100")
        self.assertEqual([c["position"] for c in nodes[1]["comments"]], ["before_label", "after_label", "after_length"])
        self.assertNotIn("support", nodes[2])
        self.assertEqual(result["value"]["trees"][0]["native_rooted_marker"], "unspecified")

    def test_comments_between_colon_and_number_remain_before_native_length(self):
        result = newick(b"(A:[note]0,B); ")
        self.assert_result(result, "ok")
        node = result["value"]["trees"][0]["nodes"][1]
        self.assertEqual(node["branch_length_token"], "0")
        self.assertEqual(node["comments"][0]["text"], "note")
        self.assertEqual(node["comments"][0]["position"], "after_label")

    def test_dialect_is_required_for_double_quoted_names(self):
        data = b'("A, (one)":"0",B);'
        rejected = newick(data)
        self.assert_result(rejected, "invalid")
        self.assertIn("phylogeny_newick_double_quote_dialect_required", codes(rejected))
        good = newick(b'("A, (one)":0,"A""quote":1);', dialect="bvbrc_double_quoted_names")
        self.assert_result(good, "ok")
        self.assertEqual([n["decoded_label"] for n in good["value"]["trees"][0]["nodes"]][1:], ["A, (one)", 'A"quote'])

    def test_forest_requires_explicit_permission(self):
        data = b"(A,B);(C,D);"
        self.assert_result(newick(data), "invalid")
        result = newick(data, allow_multiple=True)
        self.assert_result(result, "ok")
        self.assertEqual([t["tree_id"] for t in result["value"]["trees"]],
                         ["artifact:synthetic#tree_document/tree/0", "artifact:synthetic#tree_document/tree/1"])

    def test_independent_trees_survive_syntax_error_and_truncation(self):
        result = newick(b"(A,B);(E F);(G,H);(I,", allow_multiple=True)
        self.assert_result(result, "partial")
        self.assertEqual(result["value"]["completeness"], "truncated")
        self.assertEqual([t["tree_index"] for t in result["value"]["trees"]], [0, 2])
        self.assertEqual([t["nodes"][1]["decoded_label"] for t in result["value"]["trees"]], ["A", "G"])
        self.assertIn("phylogeny_newick_syntax_invalid", codes(result))
        self.assertIn("phylogeny_newick_truncated", codes(result))

    def test_numeric_errors_retain_native_tokens_and_never_default_zero(self):
        result = newick(b"(A:NaN,B:1e999,C:1e-999,D:0,E,F:);", allow_multiple=True)
        self.assert_result(result, "partial")
        nodes = result["value"]["trees"][0]["nodes"][1:]
        self.assertEqual([n["branch_length_token"] for n in nodes], ["NaN", "1e999", "1e-999", "0", None, ""])
        self.assertEqual([n["branch_length"] for n in nodes], [None, None, None, 0, None, None])
        self.assertEqual(codes(result).count("phylogeny_native_number_invalid"), 4)

    def test_comments_with_semicolons_nested_brackets_and_quoted_delimiters(self):
        result = newick(b"[before;[nested]]('a;b':1[one;[two]],B);[after;]", allow_multiple=True)
        self.assert_result(result, "ok")
        self.assertEqual(len(result["value"]["trees"]), 1)
        root, a, _ = result["value"]["trees"][0]["nodes"]
        self.assertEqual(a["decoded_label"], "a;b")
        self.assertEqual(a["comments"][0]["token"], "[one;[two]]")
        self.assertEqual(root["comments"][-1]["position"], "after_tree")

    def test_deep_tree_is_iterative_and_preorder(self):
        data = ("(" * 1600 + "A" + ",B)" * 1600 + ";").encode()
        result = newick(data)
        self.assert_result(result, "ok")
        tree = result["value"]["trees"][0]
        self.assertEqual(len(tree["nodes"]), 3201)
        self.assertEqual(tree["nodes"][1600]["decoded_label"], "A")
        self.assertEqual(tree["nodes"][0]["child_indices"], [1, 3200])

    def test_single_tip_missing_label_and_root_marker_conflict(self):
        self.assert_result(newick(b"Solo;"), "ok")
        result = newick(b"[&U](,A); ")
        self.assert_result(result, "ok")
        self.assertIsNone(result["value"]["trees"][0]["nodes"][1]["decoded_label"])
        self.assertEqual(result["value"]["trees"][0]["native_rooted_marker"], "unrooted")
        self.assert_result(newick(b"[&R][&U](A,B);"), "partial")


class AlignmentTests(ShapeAssertions):
    def test_fasta_retains_case_duplicate_labels_full_headers_and_locations(self):
        data = b">same first description\r\naC-\r\nT?\r\n>same second\r\nac.\r\nT*\r\n"
        result = fasta(data)
        self.assert_result(result, "ok")
        value = result["value"]
        self.assertEqual((value["observed_row_count"], value["observed_column_count"]), (2, 5))
        self.assertEqual([r["sequence"] for r in value["rows"]], ["aC-T?", "ac.T*"])
        self.assertEqual([r["member_label"] for r in value["rows"]], ["same", "same"])
        self.assertEqual(value["rows"][0]["raw_header"], "same first description")
        loc = value["rows"][1]["source_location"]
        self.assertEqual(data[loc["byte_start_0based"]:loc["byte_end_0based_exclusive"]], b">same second\r\nac.\r\nT*\r\n")
        self.assertEqual((loc["line_start_1based"], loc["line_end_1based_inclusive"]), (4, 6))

    def test_fasta_explicit_encoding_and_byte_offsets(self):
        data = ">é one\nAc\n>β two\naC\n".encode()
        self.assert_result(fasta(data), "invalid")
        result = fasta(data, encoding="utf-8")
        self.assert_result(result, "ok")
        row = result["value"]["rows"][1]
        self.assertEqual(row["member_label"], "β")
        self.assertEqual(row["source_location"]["byte_start_0based"], data.index(">β".encode()))

    def test_fasta_unequal_rows_are_not_padded_or_truncated(self):
        result = fasta(b">a\nAcGT\n>b\nAC\n")
        self.assert_result(result, "partial")
        self.assertEqual([r["sequence"] for r in result["value"]["rows"]], ["AcGT", "AC"])
        self.assertIsNone(result["value"]["observed_column_count"])
        self.assertEqual(result["value"]["completeness"], "partial")

    def test_empty_bytes_and_explicit_zero_length_rows_are_distinct(self):
        for parser in (fasta, phylip):
            self.assert_result(parser(b""), "invalid")
        result = fasta(b">A\n>B\n")
        self.assert_result(result, "ok")
        self.assertEqual((result["value"]["observed_row_count"], result["value"]["observed_column_count"]), (2, 0))
        result = phylip(b"0 0\n")
        self.assert_result(result, "ok")
        self.assertEqual((result["value"]["observed_row_count"], result["value"]["observed_column_count"]), (0, 0))
        self.assert_result(phylip(b"0 4\n"), "invalid")

    def test_fasta_invalid_data_does_not_hide_valid_records(self):
        result = fasta(b"orphan\n>A\nA@\n>\nAA\n>B\nAC\n")
        self.assert_result(result, "partial")
        self.assertEqual([r["sequence"] for r in result["value"]["rows"]], ["A@", "AA", "AC"])
        self.assertEqual(result["value"]["observed_row_count"], 3)
        self.assertIsNone(result["value"]["observed_column_count"])
        self.assertIn("phylogeny_fasta_header_missing", codes(result))
        self.assertIn("phylogeny_alignment_symbol_invalid", codes(result))
        self.assertIn("phylogeny_alignment_label_missing", codes(result))

    def test_whitespace_handling_is_explicit(self):
        result = fasta(b">a\na C\tG\n>b\nACG\n")
        self.assert_result(result, "ok")
        self.assertEqual(result["value"]["rows"][0]["sequence"], "aCG")
        self.assertIn("phylogeny_alignment_whitespace_ignored", codes(result))

    def test_phylip_all_layouts_and_continuation_policies(self):
        cases = [
            ("sequential", "absent", b"2 4\nlong_identifier_one Ac\nG-\nlong_identifier_two GT\nA?\n"),
            ("sequential", "repeated", b"2 4\nlong_identifier_one Ac\nlong_identifier_one G-\nlong_identifier_two GT\nlong_identifier_two A?\n"),
            ("interleaved", "absent", b"2 4\nlong_identifier_one Ac\nlong_identifier_two GT\n\nG-\nA?\n"),
            ("interleaved", "repeated", b"2 4\nlong_identifier_one Ac\nlong_identifier_two GT\n\nlong_identifier_one G-\nlong_identifier_two A?\n"),
        ]
        for layout, policy, data in cases:
            with self.subTest(layout=layout, policy=policy):
                result = phylip(data, layout=layout, continuation_ids=policy)
                self.assert_result(result, "ok")
                value = result["value"]
                self.assertEqual([r["sequence"] for r in value["rows"]], ["AcG-", "GTA?"])
                self.assertEqual([r["member_label"] for r in value["rows"]], ["long_identifier_one", "long_identifier_two"])
                self.assertEqual((value["observed_row_count"], value["observed_column_count"]), (2, 4))
                self.assertEqual(value["declared_row_count"], 2)

    def test_phylip_continuation_ids_are_not_inferred_or_reordered(self):
        data = b"2 4\nA AC\nB GT\n\nB AA\nA TT\n"
        result = phylip(data, continuation_ids="repeated")
        self.assert_result(result, "partial")
        self.assertEqual([r["sequence"] for r in result["value"]["rows"]], ["AC", "GT"])
        self.assertEqual(result["value"]["observed_row_count"], 0)
        self.assertIn("phylogeny_phylip_continuation_id_mismatch", codes(result))
        result = phylip(b"2 4\nA AC\nB GT\nA AA\nB TT\n")
        self.assert_result(result, "partial")
        self.assertIn("phylogeny_phylip_column_count_mismatch", codes(result))

    def test_absent_ids_do_not_reinterpret_sequence_groups_matching_labels(self):
        result = phylip(b"2 4\nA AC\nB GT\nA G\nB A\n")
        self.assert_result(result, "ok")
        self.assertEqual([r["sequence"] for r in result["value"]["rows"]], ["ACAG", "GTBA"])

    def test_phylip_truncated_complete_rows_remain_counted(self):
        result = phylip(b"2 4\nA AC\nB GT\n\nAA\n")
        self.assert_result(result, "partial")
        value = result["value"]
        self.assertEqual([r["sequence"] for r in value["rows"]], ["ACAA", "GT"])
        self.assertEqual(value["observed_row_count"], 1)
        self.assertIsNone(value["observed_column_count"])
        self.assertEqual(value["completeness"], "truncated")

    def test_phylip_extra_data_and_overlong_rows_are_not_truncated(self):
        for data, layout in [(b"2 2\nA ACT\nB GT\n", "interleaved"),
                             (b"1 2\nA AC\nB GT\n", "sequential"),
                             (b"2 2\nA AC\nB GT\nGG\nTT\n", "interleaved")]:
            result = phylip(data, layout=layout)
            self.assert_result(result, "partial")
            self.assertIsNone(result["value"]["observed_column_count"])
        self.assertEqual(phylip(b"2 2\nA ACT\nB GT\n")["value"]["rows"][0]["sequence"], "ACT")

    def test_phylip_duplicate_labels_zero_columns_and_bad_header(self):
        for layout in ("sequential", "interleaved"):
            result = phylip(b"2 0\nsame\nsame\n", layout=layout)
            self.assert_result(result, "ok")
            self.assertEqual([r["member_label"] for r in result["value"]["rows"]], ["same", "same"])
        self.assert_result(phylip(b"2 4 I\nA ACTG\nB ACTG\n"), "invalid")
        self.assert_result(phylip(b"2 2\nA AC\n"), "partial")


class PartitionTests(ShapeAssertions):
    def test_actual_denominator_ranges_order_model_tokens(self):
        data = b"DNA, one=1-6\\3\nDNA, two=2-6\\3\nDNA, three=3-6\\3\nLGF, aa=7-8\n"
        result = read(formats.parse_raxml_partitions, data, alignment_column_count=8)
        self.assert_result(result, "ok")
        value = result["value"]
        self.assertEqual([p["columns_0based"] for p in value["partitions"]], [[0, 3], [1, 4], [2, 5], [6, 7]])
        self.assertEqual(value["partitions"][0]["native_ranges"], [{"start_1based": 1, "end_1based_inclusive": 6, "step": 3}])
        self.assertEqual(value["partitions"][3]["model_token"], "LGF")
        self.assertNotIn("alphabet", value["partitions"][3])
        self.assertEqual(value["uncovered_columns_0based"], [])

    def test_overlap_within_and_across_partitions_holes_and_bounds(self):
        result = read(formats.parse_raxml_partitions, b"DNA, same=1-3,3\nLGF, same=3-6\n", alignment_column_count=5)
        self.assert_result(result, "partial")
        value = result["value"]
        self.assertEqual(value["overlapping_columns_0based"], [2])
        self.assertEqual(value["partitions"][1]["columns_0based"], [2, 3, 4, 5])
        self.assertIn("phylogeny_partition_out_of_bounds", codes(result))
        holes = read(formats.parse_raxml_partitions, b"DNA, p=1-5\\2\n", alignment_column_count=5)
        self.assert_result(holes, "partial")
        self.assertEqual(holes["value"]["uncovered_columns_0based"], [1, 3])

    def test_bad_partition_rows_retain_independent_valid_rows(self):
        data = b"DNA, valid=1-2\ncorrupted\nDNA, invalid=0-4\nLGF, valid=3-4\nDNA, zero_step=1-4\\0\n"
        result = read(formats.parse_raxml_partitions, data, alignment_column_count=4)
        self.assert_result(result, "partial")
        self.assertEqual([p["partition_index"] for p in result["value"]["partitions"]], [0, 3])
        self.assertEqual([p["name"] for p in result["value"]["partitions"]], ["valid", "valid"])
        self.assertEqual(result["value"]["uncovered_columns_0based"], [])
        self.assert_result(read(formats.parse_raxml_partitions, b"", alignment_column_count=0), "invalid")


class PhyloXMLTests(ShapeAssertions):
    def test_metadata_arrays_generic_support_and_missing_vs_zero(self):
        data = b'''<phyloxml xmlns="http://www.phyloxml.org" version="1.20"><phylogeny rooted="true" rerootable="false">
<property ref="tree" datatype="xsd:string" applies_to="phylogeny">t</property><clade><!--native--><name>Root</name>
<clade><name>duplicate</name><node_id>id1</node_id><sequence><name>sequence name</name><accession source="db">acc</accession></sequence><branch_length>0</branch_length>
<confidence type="support">0</confidence><confidence type="other"> 2.5e-1 </confidence>
<property ref="product" datatype="xsd:string" applies_to="node">one,two</property><property ref="product">second</property></clade>
<clade><name>duplicate</name><id>id2</id></clade></clade></phylogeny></phyloxml>'''
        result = xml(data)
        self.assert_result(result, "ok")
        value = result["value"]
        record = value["trees"][0]
        self.assertEqual(value["version"], "1.20")
        self.assertEqual([n["branch_length"] for n in record["tree"]["nodes"]], [None, 0, None])
        annotation = record["annotations"][1]
        self.assertEqual(annotation["names"], ["duplicate", "sequence name"])
        self.assertEqual(annotation["ids"], ["id1"])
        self.assertEqual(annotation["accessions"][0]["value"], "acc")
        self.assertEqual([x["value"] for x in annotation["properties"]], ["one,two", "second"])
        self.assertEqual([x["value"] for x in annotation["confidences"]], [0, 0.25])
        self.assertEqual([x["type"] for x in annotation["confidences"]], ["support", "other"])
        self.assertEqual(annotation["confidences"][1]["raw_token"], " 2.5e-1 ")
        self.assertEqual(record["tree"]["nodes"][0]["comments"][0]["token"], "<!--native-->")
        self.assertEqual(record["properties"][0]["value"], "t")
        self.assertIn("/{http://www.phyloxml.org}clade[2]", record["annotations"][2]["source_location"]["xml_path"])
        for node in record["tree"]["nodes"]:
            loc = node["source_location"]
            self.assertTrue(data[loc["byte_start_0based"]:loc["byte_end_0based_exclusive"]].startswith(b"<clade>"))

    def test_invalid_confidence_and_negative_branch_remain_native(self):
        result = xml(b"<phyloxml><phylogeny><clade><branch_length>-0.125</branch_length><confidence>bad</confidence><confidence type='support'>0</confidence></clade></phylogeny></phyloxml>")
        self.assert_result(result, "partial")
        record = result["value"]["trees"][0]
        self.assertEqual(record["tree"]["nodes"][0]["branch_length"], -0.125)
        self.assertEqual([c["value"] for c in record["annotations"][0]["confidences"]], [None, 0])
        self.assertEqual(record["annotations"][0]["confidences"][0]["raw_token"], "bad")
        self.assertIn("phylogeny_negative_branch_length", codes(result))

    def test_xml_raw_tokens_entities_cdata_utf16_and_line_locations(self):
        text = '''<?xml version="1.0" encoding="UTF-16"?><phyloxml><phylogeny rooted="0"><clade>
<name>A&amp;é</name><branch_length> &#48;.0 </branch_length><confidence><![CDATA[0.25]]></confidence>
<clade branch_length="1&#46;5"><name>child</name></clade></clade></phylogeny></phyloxml>'''
        data = text.encode("utf-16")
        result = xml(data)
        self.assert_result(result, "ok")
        record = result["value"]["trees"][0]
        root, child = record["tree"]["nodes"]
        self.assertEqual((root["raw_label"], root["decoded_label"]), ("A&amp;é", "A&é"))
        self.assertEqual(root["branch_length_token"], " &#48;.0 ")
        self.assertEqual(root["branch_length"], 0)
        self.assertEqual(child["branch_length_token"], "1&#46;5")
        self.assertEqual(child["branch_length"], 1.5)
        self.assertEqual(record["annotations"][0]["confidences"][0]["raw_token"], "<![CDATA[0.25]]>")
        self.assertEqual(record["annotations"][0]["confidences"][0]["value"], 0.25)
        self.assertEqual(record["tree"]["native_rooted_marker"], "unrooted")
        self.assertEqual(child["source_location"]["line_start_1based"], 3)
        loc = child["source_location"]
        self.assertTrue(data[loc["byte_start_0based"]:loc["byte_end_0based_exclusive"]].decode("utf-16-le").startswith("<clade branch_length"))

    def test_external_entities_and_dtd_are_never_read(self):
        texts = [b'<!DOCTYPE phyloxml SYSTEM "file:///etc/passwd"><phyloxml/>',
                 b'<!DOCTYPE phyloxml [<!ENTITY x SYSTEM "https://example.invalid/no">]><phyloxml>&x;</phyloxml>',
                 b'<!DOCTYPE phyloxml [<!ENTITY x "abc">]><phyloxml/>']
        for data in texts + [texts[0].decode().encode("utf-16")]:
            result = xml(data)
            self.assert_result(result, "invalid")
            self.assertIsNone(result["value"])
            self.assertIn("phylogeny_phyloxml_dtd_forbidden", codes(result))

    def test_unsupported_xml_encoding_returns_structured_failure(self):
        for encoding in ("NO_SUCH_ENCODING", "UTF-32", "UTF-7"):
            data = ('<?xml version="1.0" encoding="' + encoding + '"?><phyloxml/>').encode()
            result = xml(data)
            self.assert_result(result, "invalid")
            self.assertIn("phylogeny_encoding_invalid", codes(result))
        data = '<?xml version="1.0" encoding="iso-8859-1"?><phyloxml><phylogeny><clade><name>é</name></clade></phylogeny></phyloxml>'.encode("iso-8859-1")
        result = xml(data)
        self.assert_result(result, "ok")
        self.assertEqual(result["value"]["trees"][0]["tree"]["nodes"][0]["decoded_label"], "é")

    def test_complete_tree_survives_later_truncated_tree(self):
        data = b"<phyloxml><phylogeny><clade><name>A</name></clade></phylogeny><phylogeny><clade><name>B"
        result = xml(data)
        self.assert_result(result, "partial")
        self.assertEqual(result["value"]["completeness"], "truncated")
        self.assertEqual(len(result["value"]["trees"]), 1)
        self.assertEqual(result["value"]["trees"][0]["tree"]["nodes"][0]["decoded_label"], "A")

    def test_ambiguous_tree_does_not_discard_later_independent_tree(self):
        data = b"<phyloxml><phylogeny><clade/><clade/></phylogeny><phylogeny><clade><name>B</name></clade></phylogeny></phyloxml>"
        result = xml(data)
        self.assert_result(result, "partial")
        self.assertEqual(result["value"]["trees"][0]["tree"]["tree_index"], 1)
        self.assertEqual(result["value"]["trees"][0]["tree"]["tree_id"], "artifact:synthetic#phyloxml/tree/1")
        duplicate = b"<phyloxml><phylogeny><clade branch_length='1'><branch_length>2</branch_length></clade></phylogeny></phyloxml>"
        result = xml(duplicate)
        self.assert_result(result, "invalid")
        self.assertIn("phylogeny_phyloxml_branch_length_multiple", codes(result))

    def test_unknown_content_is_qualified_and_namespace_not_guessed(self):
        result = xml(b"<phyloxml><phylogeny><clade><unknown>opaque</unknown><name>A</name></clade></phylogeny></phyloxml>")
        self.assert_result(result, "ok")
        self.assertIn("phylogeny_phyloxml_element_uninterpreted", codes(result))
        self.assert_result(xml(b"<phyloxml xmlns='urn:other'><phylogeny><clade/></phylogeny></phyloxml>"), "invalid")

    def test_taxonomy_names_and_ids_remain_arrays_without_inferred_joins(self):
        result = xml(b"<phyloxml><phylogeny><clade><name>tip</name><taxonomy><id provider='db'>42</id><scientific_name>Species name</scientific_name><common_name>common</common_name><synonym>alias</synonym></taxonomy></clade></phylogeny></phyloxml>")
        self.assert_result(result, "ok")
        row = result["value"]["trees"][0]["annotations"][0]
        self.assertEqual(row["names"], ["tip", "Species name", "common", "alias"])
        self.assertEqual(row["ids"], ["42"])
        self.assertEqual(row["accessions"], [])
        self.assertIn("phylogeny_phyloxml_element_uninterpreted", codes(result))  # provider remains in native XML

    def test_unrepresented_xml_fields_are_qualified_and_nested_numbers_unavailable(self):
        result = xml(b"<phyloxml><phylogeny><name>Tree name</name><clade id_source='id'><confidence>1<bad>2</bad></confidence><name>A</name></clade></phylogeny></phyloxml>")
        self.assert_result(result, "partial")
        confidence = result["value"]["trees"][0]["annotations"][0]["confidences"][0]
        self.assertIsNone(confidence["value"])
        self.assertEqual(confidence["raw_token"], "1<bad>2</bad>")
        self.assertIn("phylogeny_phyloxml_element_uninterpreted", codes(result))
        self.assertIn("phylogeny_phyloxml_nested_scalar", codes(result))


class ContractTests(ShapeAssertions):
    def test_hash_validation_and_detachment_apply_to_all_readers(self):
        cases = [(formats.parse_newick, b"(A,B);", {"dialect": "newick"}),
                 (formats.parse_aligned_fasta, b">A\nAA\n", {"id_rule": "first_whitespace_token"}),
                 (formats.parse_relaxed_phylip, b"1 2\nA AA\n", {"layout": "sequential", "continuation_ids": "absent"}),
                 (formats.parse_raxml_partitions, b"DNA,p=1-2", {"alignment_column_count": 2}),
                 (formats.parse_phyloxml, b"<phyloxml><phylogeny><clade/></phylogeny></phyloxml>", {})]
        for function, data, kwargs in cases:
            with self.subTest(reader=function.__name__):
                ref = artifact(data)
                before = deepcopy(ref)
                result = function(data, artifact=ref, **kwargs)
                self.assert_result(result, "ok")
                self.assertEqual(ref, before)
                ref["source_ref"] = "changed"
                self.assertEqual(result["value"]["artifact"], before)
                bad = {**before, "sha256": "0" * 64}
                result = function(data, artifact=bad, **kwargs)
                self.assert_result(result, "invalid")
                self.assertIsNone(result["value"])
                self.assertEqual(result["diagnostics"][0]["phase"], "association")
                self.assert_result(function(data, artifact={**before, "unexpected": 1}, **kwargs), "invalid")
                self.assert_result(function("text", artifact=before, **kwargs), "invalid")

    def test_pure_calls_do_not_open_files_network_or_subprocesses(self):
        with patch("builtins.open", side_effect=AssertionError("IO forbidden")), \
             patch("pathlib.Path.read_bytes", side_effect=AssertionError("IO forbidden")), \
             patch("socket.socket", side_effect=AssertionError("network forbidden")), \
             patch("subprocess.Popen", side_effect=AssertionError("execution forbidden")):
            results = [newick(b"(A:0,B);"), fasta(b">A\nAC\n"), phylip(b"1 2\nA AC\n"),
                       read(formats.parse_raxml_partitions, b"DNA,p=1-2", alignment_column_count=2),
                       xml(b"<phyloxml><phylogeny><clade/></phylogeny></phyloxml>")]
            self.assertTrue(all(result["status"] == "ok" for result in results))
            validate_tree_record(results[0]["value"]["trees"][0])
            validate_alignment_document(results[1]["value"])

    def test_validators_return_detached_objects(self):
        tree = newick(b"(A:0,A);" )["value"]["trees"][0]
        alignment = fasta(b">A\nAC\n>A\nac\n")["value"]
        for validator, value, mutate in [(validate_tree_record, tree, lambda x: x["nodes"][1].update(raw_label="changed")),
                                        (validate_alignment_document, alignment, lambda x: x["rows"][0].update(sequence="changed"))]:
            before = deepcopy(value)
            returned = validator(value)
            mutate(returned)
            self.assertEqual(value, before)
            self.assertNotEqual(returned, value)

    def test_tree_validator_rejects_closed_shape_and_relationship_defects(self):
        tree = newick(b"((A:0,B),C);")["value"]["trees"][0]
        mutations = [lambda x: x.update(extra=1), lambda x: x.update(root_node_index=True),
                     lambda x: x["nodes"][1].update(parent_index=1),
                     lambda x: x["nodes"][0].update(child_indices=[4, 1]),
                     lambda x: x["nodes"][0].update(child_indices=[1, 1, 4]),
                     lambda x: x["nodes"][2].update(branch_length=2),
                     lambda x: x["nodes"][2].update(branch_length=None),
                     lambda x: x["nodes"][2]["source_location"].update(byte_end_0based_exclusive=None),
                     lambda x: x["nodes"][2]["source_location"]["artifact"].update(source_ref="wrong"),
                     lambda x: x.update(tree_id="different")]
        for mutate in mutations:
            bad = deepcopy(tree)
            mutate(bad)
            before = deepcopy(bad)
            with self.assertRaisesRegex(ValueError, "^phylogeny_[a-z_]+$"):
                validate_tree_record(bad)
            self.assertEqual(bad, before)

    def test_alignment_validator_rejects_false_complete_populations(self):
        alignment = phylip(b"2 2\nA AC\nA GT\n")["value"]
        mutations = [lambda x: x.update(extra=1), lambda x: x.update(observed_row_count=1),
                     lambda x: x.update(observed_column_count=1), lambda x: x.update(declared_column_count=3),
                     lambda x: x["rows"][0].update(sequence="A"),
                     lambda x: x["rows"][0].update(row_index=True),
                     lambda x: x["rows"][0].update(member_label="other"),
                     lambda x: x["rows"][0]["source_location"].update(line_start_1based=None),
                     lambda x: x.update(alignment_id="different")]
        for mutate in mutations:
            bad = deepcopy(alignment)
            mutate(bad)
            with self.assertRaisesRegex(ValueError, "^phylogeny_[a-z_]+$"):
                validate_alignment_document(bad)


class RetainedNativeTests(ShapeAssertions):
    def test_complete_historical_codontree_alignment_and_partitions(self):
        root = native_root() / "official_example/test9_genome_dir"
        path = next(root.glob("*.phy"))
        data = path.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), "405a5d67d39dd69a4e2f88d33bc5b89d101b1b6f8ed60fccb395f8aa7c85d671")
        result = formats.parse_relaxed_phylip(data, artifact=artifact(data, path.name), layout="interleaved", continuation_ids="absent")
        self.assert_result(result, "ok")
        value = result["value"]
        self.assertEqual((value["declared_row_count"], value["observed_row_count"], value["observed_column_count"]), (9, 9, 15300))
        self.assertEqual(sum(r["sequence"].count("-") for r in value["rows"]), 17308)
        self.assertEqual(sum(len(r["sequence"]) for r in value["rows"]), 137700)
        # Independent literal split by native blank-line blocks, preserving the
        # complete source strings, verifies all 137,700 returned characters.
        blocks = data.decode().split("\n\n")
        first = blocks[0].splitlines()[1:]
        expected = ["".join(line.split()[1:]) for line in first]
        for block in blocks[1:]:
            lines = [line for line in block.splitlines() if line.strip()]
            if lines:
                self.assertEqual(len(lines), 9)
                for i, line in enumerate(lines):
                    expected[i] += "".join(line.split())
        self.assertEqual([r["sequence"] for r in value["rows"]], expected)
        self.assertEqual([r["member_label"] for r in value["rows"]], [line.split()[0] for line in first])
        partition_data = next(root.glob("*.partitions")).read_bytes()
        partitions = read(formats.parse_raxml_partitions, partition_data, alignment_column_count=value["observed_column_count"])
        self.assert_result(partitions, "ok")
        self.assertEqual([len(p["columns_0based"]) for p in partitions["value"]["partitions"]], [3825] * 4)
        self.assertEqual([p["model_token"] for p in partitions["value"]["partitions"]], ["DNA", "DNA", "DNA", "LGF"])
        incomplete = data[:data.rfind(b"\n", 0, len(data) - 2)]
        truncated = phylip(incomplete)
        self.assert_result(truncated, "partial")
        self.assertIsNone(truncated["value"]["observed_column_count"])
        self.assertNotEqual([r["sequence"] for r in truncated["value"]["rows"]], expected)

    def test_complete_native_newick_trees_and_bootstrap_forest(self):
        root = native_root() / "official_example/test9_genome_dir"
        for prefix, dialect in [("RAxML_bestTree.", "newick"), ("RAxML_bipartitions.", "newick"),
                                ("RAxML_bipartitionsBranchLabels.", "raxml_branch_labels")]:
            data = next(root.glob(prefix + "*")).read_bytes()
            result = newick(data, dialect=dialect)
            self.assert_result(result, "ok")
            tree = result["value"]["trees"][0]
            self.assertEqual(sum(not n["child_indices"] for n in tree["nodes"]), 9)
            self.assertEqual(len(tree["nodes"]), 16)
            self.assertEqual(tree["native_rooted_marker"], "unspecified")
            if prefix == "RAxML_bestTree.":
                self.assertEqual(tree["nodes"][0]["branch_length_token"], "0.0")
            elif prefix == "RAxML_bipartitionsBranchLabels.":
                self.assertEqual([c["text"] for n in tree["nodes"] for c in n["comments"]], ["100"] * 6)
            else:
                self.assertEqual([n["decoded_label"] for n in tree["nodes"] if n["child_indices"] and n["decoded_label"] is not None], ["100"] * 6)
        data = next(root.glob("RAxML_bootstrap.*")).read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), "0d903aaf54bfd325e9bac0d44086d7ecdf7f7df5016723bbe69bf0eb4ab6aa21")
        result = newick(data, allow_multiple=True)
        self.assert_result(result, "ok")
        self.assertEqual(len(result["value"]["trees"]), 100)
        for tree in result["value"]["trees"]:
            self.assertEqual(sum(not n["child_indices"] for n in tree["nodes"]), 9)
            self.assertTrue(all(n["branch_length"] is None for n in tree["nodes"]))

    def test_both_complete_native_gene_tree_xml_files(self):
        root = native_root() / "additional_sources/bvbrc_gene_tree/tests"
        paths = sorted(root.glob("*.xml"))
        self.assertEqual(len(paths), 2)
        for path in paths:
            data = path.read_bytes()
            result = formats.parse_phyloxml(data, artifact=artifact(data, path.name))
            self.assert_result(result, "ok")
            value = result["value"]
            self.assertEqual(len(value["trees"]), 1)
            record = value["trees"][0]
            self.assertEqual(sum(not n["child_indices"] for n in record["tree"]["nodes"]), 17)
            self.assertEqual(len(record["tree"]["nodes"]), 32)
            native = ET.fromstring(data)
            native_confidences = [e.text for e in native.iter() if e.tag.endswith("}confidence")]
            parsed_confidences = [c for a in record["annotations"] for c in a["confidences"]]
            self.assertEqual([c["raw_token"] for c in parsed_confidences], native_confidences)
            self.assertEqual(len(parsed_confidences), 14)
            self.assertEqual(sum(c["value"] == 0 for c in parsed_confidences), 9)
            self.assertTrue(all(c["type"] == "support" for c in parsed_confidences))
            native_properties = [(e.attrib.get("ref"), e.text) for e in native.iter() if e.tag.endswith("}property")]
            parsed_properties = [(p["ref"], p["value"]) for a in record["annotations"] for p in a["properties"]]
            self.assertEqual(parsed_properties, native_properties)
            self.assertEqual(sum(p[0].split(":")[-1] == "product" for p in parsed_properties), 17)
            self.assertIsNone(record["tree"]["nodes"][0]["branch_length"])
            self.assertEqual(sum(n["branch_length"] is not None for n in record["tree"]["nodes"]), 31)


if __name__ == "__main__":
    unittest.main()
