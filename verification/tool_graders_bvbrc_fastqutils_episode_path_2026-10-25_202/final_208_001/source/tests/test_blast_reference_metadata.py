"""Metadata-to-numerical-input tests; source fixtures are explicitly synthetic."""
from copy import deepcopy

import pytest

from gene_annotation_episode.blast_reference_metadata import (
    attach_taxonomy, read_ncbi_assembly_metadata, read_ncbi_taxonomy,
    read_uniprot_metadata,
)


def protein():
    return {"primaryAccession": "SYNTHETIC_A", "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "organism": {"taxonId": 123, "lineage": ["Bacteria", "Example"]},
        "proteinDescription": {"recommendedName": {
            "fullName": {"value": "Test protein"},
            "ecNumbers": [{"value": "1.2.3.4", "evidences": [
                {"evidenceCode": "ECO:0000269", "source": "PubMed", "id": "123"}]}]},
            "contains": [{"recommendedName": {"ecNumbers": [{"value": "2.3.4.5"}]}}]},
        "sequence": {"value": "MACDEFGH"}, "references": [{"citation": {"id": "123"}}],
        "uniProtKBCrossReferences": [{"database": "GO", "id": "GO:0000000"}]}


def test_uniprot_preserves_assignment_evidence_without_mixing_go_or_components():
    original = protein()
    before = deepcopy(original)
    row, = read_uniprot_metadata(original, source="synthetic-protein-source")
    assert row["functions"] == [{"function": "EC:1.2.3.4", "label": "Test protein",
        "evidence": ["ECO:0000269"], "source": "synthetic-protein-source",
        "reported_evidence": [{"evidenceCode": "ECO:0000269", "source": "PubMed", "id": "123"}]}]
    assert row["lineage"] == []
    assert row["reported_lineage_names"] == ["Bacteria", "Example"]
    assert row["reported_go_annotations"][0]["id"] == "GO:0000000"
    assert row["sequence_length"] == 8
    assert row["publication_citation_count"] == 1
    assert row["study_groups"] == []  # bibliography is not experiment identity
    assert original == before
    row["native"]["sequence"]["value"] = "changed"
    assert original == before


def test_names_do_not_become_functions_and_full_sequence_duplicates_are_identified():
    other = deepcopy(protein())
    other["primaryAccession"] = "SYNTHETIC_B"
    other["proteinDescription"] = {"recommendedName": {"fullName": {"value": "Kinase-like protein"}}}
    a, b = read_uniprot_metadata({"results": [protein(), other]}, source="synthetic")
    assert b["functions"] == []
    assert a["sequence_group"] == b["sequence_group"]
    other.pop("sequence")
    missing, = read_uniprot_metadata(other, source="synthetic")
    assert missing["sequence_group"] is None and missing["sequence_length"] is None


XML = b'''<TaxaSet><Taxon><TaxId>123</TaxId><ScientificName>Example species</ScientificName>
<Rank>species</Rank><LineageEx><Taxon><TaxId>2</TaxId><ScientificName>Bacteria</ScientificName>
<Rank>superkingdom</Rank></Taxon><Taxon><TaxId>12</TaxId><ScientificName>Example</ScientificName>
<Rank>genus</Rank></Taxon></LineageEx></Taxon></TaxaSet>'''


def test_taxonomy_exact_join_and_conflict_remain_visible():
    taxa = read_ncbi_taxonomy(XML, source="synthetic-taxonomy")
    assert [x["taxid"] for x in taxa[0]["lineage"]] == [2, 12, 123]
    refs = read_uniprot_metadata(protein(), source="synthetic")
    attached = attach_taxonomy(refs, taxa)
    assert attached[0]["lineage"][-1]["rank"] == "species"
    assert refs[0]["lineage"] == []
    wrong = deepcopy(taxa)
    wrong[0]["lineage"][1]["taxid"] = 13
    conflicting = attach_taxonomy(refs, taxa + wrong)
    assert conflicting[0]["lineage"] == []
    assert len(conflicting[0]["taxonomy_records"]) == 2
    assert conflicting[0]["issues"] == [{"code": "conflicting_taxonomy_lineages"}]
    refs[0]["taxid"] = 124
    assert attach_taxonomy(refs, taxa)[0]["lineage"] == []


def assembly():
    return {"accession": "GCA_SYNTHETIC.1", "organism": {"taxId": 123},
        "assemblyInfo": {"assemblyLevel": "Complete Genome", "genomeNotes": ["metagenome"],
            "biosample": {"accession": "SAM_SYNTHETIC", "attributes": [
                {"name": "isolation_source", "value": "environmental sample"}]}},
        "assemblyStats": {"numberOfContigs": "3", "contigN50": "12000", "totalSequenceLength": "31000"},
        "checkmInfo": {"completeness": 96.5, "contamination": 2.4, "checkmVersion": "v1.2.0",
                       "completenessPercentile": 10}}


def read_assembly(value):
    return read_ncbi_assembly_metadata(value, reference_accession="SYNTHETIC_A",
        assembly_accession="GCA_SYNTHETIC.1", linkage_source="synthetic-explicit-protein-assembly-link",
        source="synthetic-assembly-report")


def test_measured_percentages_have_exact_units_and_no_source_category_grade():
    row = read_assembly(assembly())
    assert row["assembly"]["completeness_fraction"] == pytest.approx(.965)
    assert row["assembly"]["contamination_fraction"] == pytest.approx(.024)
    assert row["assembly"]["contig_count"] == 3
    assert row["assembly"]["total_sequence_length"] == 31000
    assert row["assembly"]["measurement_methods"]["contig_count"] == "NCBI assemblyStats"
    assert row["assembly"]["measurement_methods"]["completeness_fraction"] == "CheckM"
    assert row["origin"]["genome_notes"] == ["metagenome"]
    assert row["assembly"]["assembly_level"] == "Complete Genome"
    assert "source_quality_score" not in row
    assert row["functions"] == []


def test_missing_zero_invalid_and_large_contamination_are_distinct():
    raw = assembly()
    raw["checkmInfo"] = {"contamination": 150, "completeness": 0}
    row = read_assembly(raw)
    assert row["assembly"]["contamination_fraction"] == 1.5
    assert row["assembly"]["completeness_fraction"] == 0
    raw["checkmInfo"] = {"completeness": "high"}
    row = read_assembly(raw)
    assert row["assembly"]["completeness_fraction"] is None
    assert row["assembly"]["contamination_fraction"] is None
    assert row["issues"] == [{"code": "invalid_assembly_measurement", "field": "completeness"}]
    raw["checkmInfo"] = {}
    assert read_assembly(raw)["assembly"]["quality_method"] is None


def test_wrong_assembly_cannot_be_attached_by_shared_organism():
    raw = assembly()
    raw["accession"] = "GCA_DIFFERENT.1"
    with pytest.raises(ValueError, match="assembly_accession_link_conflict"):
        read_assembly(raw)
