"""Source-geometry fixtures, not claims about actual microbial functions."""

import io
import json

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import AfterPosition, BeforePosition, CompoundLocation, SeqFeature, SimpleLocation
from Bio.SeqRecord import SeqRecord
import pytest

from gene_annotation_episode.acquisition import parse_genbank
from gene_annotation_episode.comparative_ops import genbank_neighborhood


def feature(start, end, *, strand=1, kind="CDS", tag="locus_A", product="native source label"):
    return SeqFeature(SimpleLocation(start, end, strand=strand), type=kind,
        qualifiers={"locus_tag": [tag], "product": [product], "protein_id": ["FIXTURE_P.1"]})


def body(features, *, length=100, circular=False, accession="FIXTURE001.2", molecule="DNA"):
    record = SeqRecord(Seq("A"*length), id=accession, name=accession.split(".")[0],
                       description="synthetic source-coordinate fixture")
    record.annotations.update(molecule_type=molecule, topology="circular" if circular else "linear",
        organism="Fixture organism", taxonomy=["Bacteria", "Fixture lineage"])
    record.dbxrefs = ["BioSample:FIXTURE"]
    record.features = features
    output = io.StringIO()
    SeqIO.write(record, output, "genbank")
    return output.getvalue().encode()


def lookup(content, selector=None, **kwargs):
    return genbank_neighborhood(content, accession="FIXTURE001.2",
        selector=selector or {"locus_tag": "locus_A"}, left_bp=kwargs.pop("left_bp", 5),
        right_bp=kwargs.pop("right_bp", 7), **kwargs)


def test_reverse_strand_order_partial_boundaries_and_labels_are_source_faithful():
    joined = SeqFeature(CompoundLocation([SimpleLocation(60, 80, strand=-1),
        SimpleLocation(BeforePosition(20), AfterPosition(30), strand=-1)], operator="join"),
        type="CDS", qualifiers={"locus_tag": ["locus_A"], "product": ["specific-looking source name"]})
    content = body([joined])
    parsed = parse_genbank(content)[0]
    actual = parsed["features"][0]
    assert [part["start"] for part in actual["segments"]] == [60, 20]
    assert [part["strand"] for part in actual["segments"]] == ["-", "-"]
    assert actual["segments"][1]["start_kind"] == "BeforePosition"
    assert actual["segments"][1]["end_kind"] == "AfterPosition"
    assert actual["segments"][1]["partial_start"] is True
    assert actual["operator"] == "join"
    result = lookup(content)
    assert result["window"]["requested"]["start"] == 15
    assert result["window"]["requested"]["end"] == 87
    assert result["features"][0]["segments"] == actual["segments"]
    assert result["features"][0]["source_labels"]["product"] == ["specific-looking source name"]
    assert result["features"][0]["label_interpretation"] == "native_source_assertions_not_target_assignments"
    assert result["source"]["accession"] == "FIXTURE001.2"
    assert result["source"]["sequence_version"] == 2
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("strand", [1, -1])
def test_actual_circular_origin_join_wraps_without_losing_source_part_order(strand):
    parts = [SimpleLocation(90, 100, strand=strand), SimpleLocation(0, 10, strand=strand)]
    if strand == -1:
        parts.reverse()
    focal = SeqFeature(CompoundLocation(parts, operator="join"), type="CDS",
                       qualifiers={"locus_tag": ["locus_A"]})
    content = body([focal, feature(5, 8, tag="neighbor")], circular=True)
    result = lookup(content, left_bp=5, right_bp=5)
    assert result["focal_span"]["start"] == 90
    assert result["focal_span"]["end"] == 110
    assert result["window"]["requested"] == {"start": 85, "end": 115, "length": 30,
        "coordinate_frame": "returned_record_reference_axis_unclipped"}
    assert [(part["start"], part["end"]) for part in result["window"]["available_segments"]] == [(85, 100), (0, 15)]
    assert result["window"]["wrap_used"] is True
    assert result["window"]["missing_left_bp"] == result["window"]["missing_right_bp"] == 0
    observed_focal = next(row for row in result["features"] if row["is_focal"])
    assert [part["start"] for part in observed_focal["segments"]] == [int(part.start) for part in parts]
    neighbor = next(row for row in result["features"] if row["source_labels"]["locus_tag"] == ["neighbor"])
    assert neighbor["window_order_offset"] == 20


def test_long_join_is_not_silently_replaced_by_shorter_circular_arc():
    focal = SeqFeature(CompoundLocation([SimpleLocation(10, 20, strand=1),
        SimpleLocation(80, 90, strand=1)], operator="join"), type="CDS",
        qualifiers={"locus_tag": ["locus_A"]})
    result = lookup(body([focal], circular=True), left_bp=0, right_bp=0)
    assert result["focal_span"]["start"] == 10
    assert result["focal_span"]["end"] == 90
    assert result["window"]["available_unique_bp"] == 80
    assert result["window"]["wrap_used"] is False


def test_source_without_circular_assertion_clips_and_does_not_invent_neighbors():
    content = body([feature(0, 10), feature(90, 100, tag="far_end")])
    result = lookup(content, left_bp=20, right_bp=5)
    assert result["window"]["wrap_permitted"] is False
    assert result["window"]["missing_left_bp"] == 20
    assert [(part["start"], part["end"]) for part in result["window"]["available_segments"]] == [(0, 15)]
    assert all(row["source_labels"]["locus_tag"] != ["far_end"] for row in result["features"])
    assert result["biological_absence_established"] is False


def test_partial_acquired_subset_preserves_original_coordinates_and_unavailable_flanks():
    # A circular assertion about the source does not make this fetched slice
    # a complete circular molecule with adjacent slice ends.
    content = body([feature(35, 50)], circular=True)
    request = {"db": "nuccore", "id": "FIXTURE001.2", "seq_start": 101, "seq_stop": 200}
    result = lookup(content, left_bp=60, right_bp=80, source_request=request)
    assert result["coordinate_mapping"]["available_original_interval"] == {"start": 100, "end": 200}
    assert result["focal_features"][0]["mapped_original_segments"][0]["interval"] == {"start": 135, "end": 150}
    assert result["window"]["requested_original_interval_unclipped"] == {"start": 75, "end": 230}
    assert result["window"]["missing_left_bp"] == 25
    assert result["window"]["missing_right_bp"] == 30
    assert result["window"]["wrap_permitted"] is False
    assert result["window"]["boundary_kind"] == "fetched_subset_boundary"
    assert result["window"]["available_segments"][0]["original_interval"] == {"start": 100, "end": 200}
    selected = lookup(content, {"coordinate": 149, "coordinate_frame": "original"},
                      source_request=request, left_bp=2, right_bp=3)
    assert selected["focal_span"]["start"] == 49
    assert selected["window"]["requested_original_interval_unclipped"] == {"start": 147, "end": 153}
    outside = lookup(content, {"coordinate": 99, "coordinate_frame": "original"}, source_request=request)
    assert outside["selection_status"] == "coordinate_outside_available_context"
    assert outside["context_status"] == "unavailable"


def test_reverse_fetched_subset_maps_strand_without_rewriting_returned_record_parts():
    content = body([feature(10, 20)])
    result = lookup(content, source_request={"id": "FIXTURE001.2", "seq_start": 101,
                                            "seq_stop": 200, "strand": 2})
    actual = result["focal_features"][0]
    assert actual["segments"][0]["start"] == 10
    assert actual["segments"][0]["strand"] == "+"
    assert actual["mapped_original_segments"][0]["interval"] == {"start": 180, "end": 190}
    assert actual["mapped_original_segments"][0]["strand"] == "-"


def test_request_response_mismatch_does_not_fabricate_original_mapping():
    content = body([feature(10, 20)])
    request = {"id": "FIXTURE001.2", "seq_start": 101, "seq_stop": 250}
    result = lookup(content, source_request=request)
    assert result["context_status"] == "available"  # local annotation survives
    assert result["coordinate_mapping"]["status"] == "unavailable"
    assert result["coordinate_mapping"]["reason"] == "request_response_length_mismatch"
    assert result["focal_features"][0]["mapped_original_segments"][0]["interval"] is None
    original = lookup(content, {"coordinate": 115, "coordinate_frame": "original"}, source_request=request)
    assert original["selection_status"] == "coordinate_mapping_unavailable"


def test_colocated_gene_cds_are_visible_but_distinct_loci_are_not_arbitrarily_selected():
    content = body([feature(10, 20, kind="gene"), feature(10, 20)])
    result = lookup(content)
    assert result["selection_status"] == "co_located_matches"
    assert {row["kind"] for row in result["focal_features"]} == {"gene", "CDS"}
    ambiguous = lookup(body([feature(10, 20), feature(50, 60)]))
    assert ambiguous["selection_status"] == "identifier_ambiguous"
    assert ambiguous["window"] is None
    assert len(ambiguous["focal_features"]) == 2
    cds_only = lookup(content, {"locus_tag": "locus_A", "feature_kind": "CDS"})
    assert cds_only["selection_status"] == "identifier_selected"


def test_coordinate_window_can_examine_empty_annotations_without_claiming_gene_absence():
    content = body([])
    result = lookup(content, {"coordinate": 50}, left_bp=10, right_bp=10)
    assert result["context_status"] == "available"
    assert result["features"] == []
    assert result["annotation_result"] == "no_features_in_examined_source_annotations"
    assert result["biological_absence_established"] is False
    missing = lookup(content)
    assert missing["selection_status"] == "identifier_not_found_in_acquired_annotations"
    assert missing["context_status"] == "unavailable"
    assert missing["examined_identifier_scope"]["meaning"] == "source_annotation_lookup_not_gene_absence"


def test_window_clipping_does_not_change_intrinsic_source_partialness():
    result = lookup(body([feature(5, 40)]), {"coordinate": 15}, left_bp=2, right_bp=2)
    actual = result["features"][0]
    assert actual["partial_start"] is False and actual["partial_end"] is False
    assert actual["window_visibility"] == "partial_nominal_location"
    assert actual["segments"][0]["start"] == 5
    assert actual["visible_segments"][0]["start"] == 13


def test_accession_versions_remain_distinct_and_protein_record_has_no_genomic_context():
    content = body([feature(10, 20)], accession="FIXTURE001.1") + body([feature(50, 60)])
    ambiguous = genbank_neighborhood(content, accession="FIXTURE001", selector={"coordinate": 10},
                                    left_bp=1, right_bp=1)
    assert ambiguous["selection_status"] == "source_record_ambiguous"
    selected = lookup(content)
    assert selected["source"]["accession"] == "FIXTURE001.2"
    protein = lookup(body([], molecule="protein"), {"coordinate": 10})
    assert protein["context_status"] == "unavailable"
    assert protein["reason"] == "protein_record_has_no_genomic_neighborhood"


def test_circular_window_larger_than_record_returns_each_feature_once():
    result = lookup(body([feature(10, 20), feature(50, 60, tag="neighbor")], circular=True),
                    left_bp=110, right_bp=110)
    assert result["window"]["available_unique_bp"] == 100
    assert result["window"]["repeated_circular_bp"] == 130
    assert len(result["features"]) == 2
    assert len({feature["source_feature_key"] for feature in result["features"]}) == 2
