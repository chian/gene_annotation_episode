"""Source-symbol fidelity and explicit model choice, not biological identity."""
import pytest

from gene_annotation_episode.sequence_views import view_sequence


def test_identity_view_records_assumption_without_classifying_or_changing_input():
    protein = "MKWVTFISLLFLFSSAYSRGVFRR"
    result = view_sequence(protein, molecule="protein")
    assert result["sequence"] == protein
    assert result["molecule_assignment"] == "not_performed"
    assert result["molecule_model"] == "protein"
    assert result["input_segments"] == [{"start": 0, "end": len(protein)}]
    assert protein == "MKWVTFISLLFLFSSAYSRGVFRR"


def test_ordered_and_repeated_extractions_preserve_actual_selected_symbols():
    segments = [{"start": 4, "end": 7}, {"start": 0, "end": 3}, {"start": 4, "end": 7}]
    result = view_sequence("ACGTTGCAA", molecule="dna", segments=segments)
    assert result["sequence"] == "TGCACGTGC"
    result["input_segments"][0]["start"] = 0
    assert segments[0]["start"] == 4


def test_rna_orientation_preserves_rna_symbols_and_dna_uses_dna_complement():
    assert view_sequence("AUGC", molecule="rna", orientation="reverse_complement")["sequence"] == "GCAU"
    assert view_sequence("ATGC", molecule="dna", orientation="reverse_complement")["sequence"] == "GCAT"


def test_reverse_complement_applies_to_concatenated_selected_segments():
    result = view_sequence("ATGAAACCCTGA", molecule="dna",
        segments=[{"start": 0, "end": 3}, {"start": 9, "end": 12}], orientation="reverse_complement")
    assert result["sequence"] == "TCACAT"


def test_protein_is_never_silently_treated_as_dna_for_complement():
    with pytest.raises(ValueError, match="protein_reverse_complement_undefined"):
        view_sequence("MACT", molecule="protein", orientation="reverse_complement")
    assert view_sequence("MACT", molecule="protein")["sequence"] == "MACT"


@pytest.mark.parametrize("segments", [[], [{"start": -1, "end": 2}], [{"start": 1, "end": 1}],
    [{"start": False, "end": 2}], [{"start": 0, "end": 5}], [{"start": 0, "end": 2, "extra": 1}]])
def test_extraction_does_not_silently_clip_or_repair_invalid_intervals(segments):
    with pytest.raises(ValueError, match="view_interval_outside_subject"):
        view_sequence("ACGT", molecule="dna", segments=segments)


def test_unknown_identity_and_incompatible_symbols_are_not_invented():
    with pytest.raises(ValueError, match="explicit_sequence_model_required"):
        view_sequence("ACGT", molecule="unspecified")
    with pytest.raises(ValueError, match="reverse_complement_requires_nucleotide_symbols"):
        view_sequence("AZGT", molecule="dna", orientation="reverse_complement")
    # Forward extraction preserves unusual symbols; it does not certify them.
    assert view_sequence("AZGT", molecule="dna")["sequence"] == "AZGT"
