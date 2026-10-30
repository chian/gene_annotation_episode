"""Coordinate tests against independently selected original sequence symbols."""
from copy import deepcopy

import pytest
from Bio.Seq import Seq

from gene_annotation_episode.sequence_mapping import (
    extract_path, map_interval, mapping_footprint, path_length, reverse_path,
    slice_path, translation_mapping, validate_mapping,
)
from gene_annotation_episode.sequence_ops import translate


def segment(start, end, strand="+", target="input:test"):
    return {"subject_ref": target, "start": start, "end": end, "unit": "nt", "strand": strand}


def symbols(sequences, path):
    result = []
    for row in path:
        seq = sequences[row["subject_ref"]][row["start"]:row["end"]]
        result.append(str(Seq(seq).reverse_complement()) if row["strand"] == "-" else seq)
    return "".join(result)


@pytest.mark.parametrize("strand,frame,cds", [("+", 0, False), ("-", 1, False), ("+", 0, True), ("-", 0, True)])
def test_actual_translator_residues_map_to_their_original_codons(strand, frame, cds):
    region = "ATGAAAGGGTAA" if cds else "CATGAAAGGGTAAA"
    if strand == "-":
        region = str(Seq(region).reverse_complement())
    dna = "CCCC" + region + "CCCC"
    result = translate(dna, code=11, start=4, end=4 + len(region), strand=strand, frame=frame, cds=cds)
    mapping = translation_mapping([segment(0, len(dna))],
        start=result["translated_interval"][0], end=result["translated_interval"][1],
        strand=strand, protein_length=len(result["sequence"]), omitted_terminal_stop=cds)
    for i, residue in enumerate(result["sequence"]):
        codon = symbols({"input:test": dna}, map_interval(mapping, i, i+1))
        assert len(codon) == 3
        assert str(Seq(codon).translate(table=11)) == residue
    assert sum(row["end"]-row["start"] for row in mapping_footprint(mapping, input_refs={"input:test"})) == 3 * len(result["sequence"])


def test_split_codon_retains_actual_segments_without_inventing_contiguous_genome_span():
    dna = "ATGACCCCAAGGGTAA"
    path = extract_path([segment(0, len(dna))], [{"start": 0, "end": 4}, {"start": 8, "end": 16}])
    assert symbols({"input:test": dna}, path) == "ATGAAAGGGTAA"
    mapping = translation_mapping(path, start=0, end=12, strand="+", protein_length=4)
    assert map_interval(mapping, 1, 2) == [segment(3, 4), segment(8, 10)]
    assert str(Seq(symbols({"input:test": dna}, map_interval(mapping, 1, 2))).translate()) == "K"


def test_reverse_extraction_changes_segment_traversal_and_orientation_together():
    path = [segment(2, 6), segment(10, 15)]
    assert reverse_path(path) == [segment(10, 15, "-"), segment(2, 6, "-")]
    assert slice_path(reverse_path(path), 3, 7) == [segment(10, 12, "-"), segment(4, 6, "-")]
    assert extract_path([segment(0, 20)], [{"start": 10, "end": 15}, {"start": 2, "end": 6}], strand="-") == [segment(2, 6, "-"), segment(10, 15, "-")]


def test_cdstop_is_only_omitted_when_execution_explicitly_says_so():
    with pytest.raises(ValueError, match="translation_mapping_length_mismatch"):
        translation_mapping([segment(10, 22)], start=0, end=12, strand="+", protein_length=3)
    forward = translation_mapping([segment(10, 22)], start=0, end=12, strand="+", protein_length=3, omitted_terminal_stop=True)
    reverse = translation_mapping([segment(10, 22)], start=0, end=12, strand="-", protein_length=3, omitted_terminal_stop=True)
    assert mapping_footprint(forward, input_refs={"input:test"}) == [{"target_ref": "input:test", "start": 10, "end": 19, "unit": "nt"}]
    assert map_interval(reverse, 0, 3) == [segment(13, 22, "-")]


def test_paths_retain_input_identity_order_and_do_not_mutate_callers():
    path = [segment(20, 26, target="input:b"), segment(0, 6, "-", target="input:a")]
    original = deepcopy(path)
    mapping = translation_mapping(path, start=0, end=12, strand="+", protein_length=4)
    assert map_interval(mapping, 1, 3) == [segment(23, 26, target="input:b"), segment(3, 6, "-", target="input:a")]
    assert path == original
    assert map_interval(mapping, 4, 4) == []


@pytest.mark.parametrize("path", [[], [segment(2, 2)], [segment(-1, 3)], [segment(True, 4)], [dict(segment(0, 3), strand=".")]])
def test_unrepresentable_paths_are_not_silently_repaired(path):
    with pytest.raises(ValueError):
        path_length(path)


def test_interval_must_refer_to_actual_output_symbols_and_mapping_length_is_exact():
    mapping = translation_mapping([segment(0, 9)], start=0, end=9, strand="+", protein_length=3)
    for start, end in [(0, 4), (-1, 1), (2, 1), (False, 1)]:
        with pytest.raises(ValueError, match="interval_outside_mapped_sequence"):
            map_interval(mapping, start, end)
    mapping["symbol_length"] = 4
    with pytest.raises(ValueError, match="mapping_length_mismatch"):
        validate_mapping(mapping)
