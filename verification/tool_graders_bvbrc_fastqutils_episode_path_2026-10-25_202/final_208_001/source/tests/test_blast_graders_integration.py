"""Complete BLAST grading paths; database inputs are synthetic, never executed.

The pairwise fixture is recorded native output with separate provenance. These
tests do not launch database searches, make network requests, or assign credit.
"""
from copy import deepcopy
import io
import json
from pathlib import Path
import zipfile

import pytest

from gene_annotation_episode.blast_database_grader import calculate_database_probabilities
from gene_annotation_episode.blast_graders import grade_blast_result, main
from gene_annotation_episode.blast_reference_metadata import (
    attach_taxonomy, read_ncbi_assembly_metadata, read_ncbi_taxonomy,
    read_uniprot_metadata,
)


F, G = "EC:1.2.3.4", "EC:2.3.4.5"
REQUEST = {"program": "blastp", "query_length": 10, "hitlist_size": 3,
           "database_release": "synthetic-v1"}
PROFILE = {"database": "synthetic_db", "release": "synthetic-v1",
    "source": "synthetic-complete-database-census", "count_unit": "unique_sequences",
    "total_count": 1000, "function_counts": {F: 200, G: 50}, "scope": "searched_database"}


def native_document():
    hits = []
    for accession, taxid, bits in (("SYN_A", 562, 10), ("SYN_B", 620, 9), ("SYN_C", 562, 10)):
        hits.append({"num": len(hits) + 1, "len": 10,
            "description": [{"id": accession, "accession": accession,
                "title": "Synthetic source description", "taxid": taxid,
                "sciname": "Synthetic organism " + str(taxid)}],
            "hsps": [{"num": 1, "bit_score": bits, "score": bits * 2, "evalue": 0.01,
                "query_from": 1, "query_to": 5, "hit_from": 1, "hit_to": 5,
                "identity": 5, "positive": 5, "align_len": 5, "gaps": 0,
                "qseq": "ACDEF", "hseq": "ACDEF"}]})
    return {"BlastOutput2": [{"report": {"program": "blastp", "version": "BLASTP synthetic fixture",
        "search_target": {"db": "synthetic_db"}, "params": {"expect": 10},
        "results": {"search": {"query_id": "synthetic_query", "query_title": "synthetic_query",
            "query_len": 10, "hits": hits, "stat": {"db_num": 1000, "db_len": 10000}}}}}]}


def metadata():
    entries = []
    # Equal aligned fragments, deliberately different complete sequences.
    for accession, taxid, ec, sequence in (("SYN_A", 562, "1.2.3.4", "ACDEFGHIKL"),
            ("SYN_B", 620, "2.3.4.5", "ACDEFVWYAA"), ("SYN_C", 562, "1.2.3.4", "ACDEFPQRST")):
        entries.append({"primaryAccession": accession, "organism": {"taxonId": taxid},
            "proteinDescription": {"recommendedName": {"fullName": {"value": "Synthetic function " + ec},
                "ecNumbers": [{"value": ec, "evidences": [{"evidenceCode": "ECO:0000269"}]}]}},
            "sequence": {"value": sequence}})
    rows = read_uniprot_metadata({"results": entries}, source="synthetic-uniprot-records")
    taxonomy = read_ncbi_taxonomy(b'''<TaxaSet>
<Taxon><TaxId>562</TaxId><Rank>species</Rank><ScientificName>Escherichia coli</ScientificName>
<LineageEx><Taxon><TaxId>2</TaxId><Rank>superkingdom</Rank><ScientificName>Bacteria</ScientificName></Taxon>
<Taxon><TaxId>561</TaxId><Rank>genus</Rank><ScientificName>Escherichia</ScientificName></Taxon></LineageEx></Taxon>
<Taxon><TaxId>620</TaxId><Rank>species</Rank><ScientificName>Shigella</ScientificName>
<LineageEx><Taxon><TaxId>2</TaxId><Rank>superkingdom</Rank><ScientificName>Bacteria</ScientificName></Taxon>
<Taxon><TaxId>629</TaxId><Rank>genus</Rank><ScientificName>Fixture genus</ScientificName></Taxon></LineageEx></Taxon>
</TaxaSet>''', source="synthetic-taxonomy-records")
    return attach_taxonomy(rows, taxonomy)


def zipped(content):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"BlastJSON": [{"File": "query_1.json"}]}))
        archive.writestr("query_1.json", content)
    return stream.getvalue()


def tabular_document():
    fields = "qseqid sacc qlen slen qstart qend sstart send qseq sseq score bitscore evalue length nident positive gaps staxids".split()
    lines = ["# BLASTP synthetic fixture", "# Query: synthetic_query", "# Database: synthetic_db"]
    for hit in native_document()["BlastOutput2"][0]["report"]["results"]["search"]["hits"]:
        d, h = hit["description"][0], hit["hsps"][0]
        values = ["synthetic_query", d["accession"], 10, 10, 1, 5, 1, 5,
                  "ACDEF", "ACDEF", h["score"], h["bit_score"], .01, 5, 5, 5, 0, d["taxid"]]
        lines.append("\t".join(map(str, values)))
    lines += ["# 3 hits found", "# BLAST processed 1 queries"]
    return ("\n".join(lines) + "\n").encode(), fields


def grade_json(document=None, **kwargs):
    return grade_blast_result(json.dumps(document or native_document()).encode(),
        mode="database", resource="api", output_format="json2", request=deepcopy(REQUEST),
        **kwargs)


@pytest.mark.parametrize("resource,archive", [("api", False), ("api", True), ("hpc", False)])
def test_json_and_api_zip_populate_reader_components_and_numerical_probabilities(resource, archive):
    raw = json.dumps(native_document()).encode()
    result = grade_blast_result(zipped(raw) if archive else raw, mode="database", resource=resource,
        output_format="json2", request=REQUEST, reference_metadata=metadata(), database_profile=PROFILE)
    sheet, probabilities = result["sheet"], result["probabilities"]
    assert sheet["normalized_result"]["resource"] == resource
    assert sheet["coverage"]["sequence_group_count"] == 3
    assert sheet["coverage"]["matched_metadata_row_count"] == 3
    assert sheet["hits"][0]["measurements"]["query_paired_coverage"] == .5
    assert sheet["hits"][0]["hsp_components"][0]["counts"]["identical_pairs"] == 5
    assert probabilities["function_masses"] == {F: 2, G: .5}
    assert probabilities["unadjusted_probabilities"] == {F: .8, G: .2}
    assert probabilities["representation_adjusted_probabilities"] == {F: .5, G: .5}
    assert sheet["search_limits"]["limit_reached"] is True
    assert sheet["search_limits"]["whole_database_result_complete"] is None


def test_hpc_tabular_and_api_json_agree_on_shared_numerical_inputs():
    rows = metadata()
    api = grade_json(reference_metadata=rows, database_profile=PROFILE)
    content, fields = tabular_document()
    hpc = grade_blast_result(content, mode="database", resource="hpc", output_format="tabular",
        fields=fields, request=REQUEST, reference_metadata=rows, database_profile=PROFILE)
    assert hpc["probabilities"]["function_masses"] == api["probabilities"]["function_masses"]
    assert hpc["probabilities"]["representation_adjusted_probabilities"] == api["probabilities"]["representation_adjusted_probabilities"]
    for a, b in zip(api["sheet"]["hits"], hpc["sheet"]["hits"]):
        assert a["measurements"] == b["measurements"]
        assert a["associations"][0]["taxid"] == b["associations"][0]["taxid"]
        assert a["associations"][0]["functions"] == b["associations"][0]["functions"]
    assert hpc["sheet"]["normalized_result"]["search"]["statistics"] == {}
    assert api["sheet"]["normalized_result"]["search"]["statistics"]["db_num"] == 1000


def test_native_alias_associations_and_duplicate_invariance_reach_probabilities():
    original = native_document()
    rows = metadata()
    base = grade_json(original, reference_metadata=rows)
    descriptions = original["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["description"]
    descriptions += [deepcopy(descriptions[0]), deepcopy(descriptions[0])]
    repeated = grade_json(original, reference_metadata=rows)
    assert repeated["probabilities"]["function_masses"] == base["probabilities"]["function_masses"]
    assert repeated["probabilities"]["unadjusted_probabilities"] == base["probabilities"]["unadjusted_probabilities"]
    for hit in repeated["sheet"]["hits"]:
        for association in hit["associations"]:
            expected = next(row for row in rows if row["accession"] == association["accession"])
            assert association["taxid"] == expected["taxid"]
            assert association["functions"] == expected["functions"]
            assert association["source"] == expected["source"]
    functions = {row["function"]: row for row in repeated["sheet"]["functions"]}
    assert {row["taxid"] for row in functions[F]["taxonomy"]["taxa"]} == {562}
    assert {row["taxid"] for row in functions[G]["taxonomy"]["taxa"]} == {620}


def test_missing_metadata_does_not_become_zero_grade_or_title_derived_function():
    result = grade_json()
    sheet, probabilities = result["sheet"], result["probabilities"]
    assert sheet["coverage"]["groups_without_explicit_function"] == 3
    assert sheet["functions"] == []
    assert sheet["hits"][0]["associations"][0]["source"] is None
    assert sheet["hits"][0]["associations"][0]["quality_measurements"]["completeness_fraction"] is None
    assert probabilities["unadjusted_probabilities"] is None
    assert probabilities["representation_adjusted_probabilities"] is None
    assert probabilities["unannotated_reference_kernel_fraction"] == 1


def test_merged_native_hit_keeps_function_taxon_and_source_associations_separate():
    document = native_document()
    search = document["BlastOutput2"][0]["report"]["results"]["search"]
    search["hits"] = search["hits"][:1]
    search["hits"][0]["description"].append({"accession": "SYN_Z", "taxid": 620,
        "title": "Synthetic alternative annotation of a merged sequence"})
    original, alias = metadata()[:2]
    alias["accession"] = "SYN_Z"
    alias["source"] = "synthetic-alias-Z-source"
    alias["functions"][0]["source"] = alias["source"]
    alias["sequence_group"] = original["sequence_group"]
    graded = grade_json(document, reference_metadata=[original, alias])
    sheet = graded["sheet"]
    assert sheet["coverage"]["sequence_group_count"] == 1
    assert graded["probabilities"]["unadjusted_probabilities"] == {F: .5, G: .5}
    associations = {row["accession"]: row for row in sheet["hits"][0]["associations"]}
    assert associations["SYN_A"]["taxid"] == 562
    assert associations["SYN_A"]["functions"][0]["function"] == F
    assert associations["SYN_Z"]["taxid"] == 620
    assert associations["SYN_Z"]["functions"][0]["function"] == G
    assert associations["SYN_Z"]["source"] == "synthetic-alias-Z-source"
    functions = {row["function"]: row for row in sheet["functions"]}
    assert {row["taxid"] for row in functions[F]["taxonomy"]["taxa"]} == {562}
    assert {row["taxid"] for row in functions[G]["taxonomy"]["taxa"]} == {620}


def test_tabular_taxon_sets_are_not_assigned_to_accessions_by_position():
    # NCBI tabular sets have no positional correspondence. Deliberately put
    # accessions and taxids in orders that would produce a wrong zipped join.
    fields = "qseqid sacc sallacc staxids qlen slen qstart qend sstart send qseq sseq bitscore".split()
    raw = b"synthetic_query\tSYN_A\tSYN_A;SYN_Z\t620;562\t10\t10\t1\t5\t1\t5\tACDEF\tACDEF\t10\n"
    unknown = grade_blast_result(raw, mode="database", resource="hpc", output_format="tabular",
        fields=fields, request={**REQUEST, "database": "synthetic_db"})
    hit = unknown["sheet"]["hits"][0]
    assert all(row["taxid"] is None for row in hit["associations"])
    assert hit["unpaired_metadata"]["staxids"] == [620, 562]
    assert unknown["sheet"]["taxonomy"]["taxa"] == []
    original, alias = metadata()[:2]
    alias["accession"] = "SYN_Z"
    resolved = grade_blast_result(raw, mode="database", resource="hpc", output_format="tabular",
        fields=fields, request={**REQUEST, "database": "synthetic_db"},
        reference_metadata=[original, alias])
    rows = {row["accession"]: row for row in resolved["sheet"]["hits"][0]["associations"]}
    assert rows["SYN_A"]["taxid"] == 562 and rows["SYN_Z"]["taxid"] == 620
    assert rows["SYN_A"]["functions"][0]["function"] == F
    assert rows["SYN_Z"]["functions"][0]["function"] == G


def test_assembly_reader_values_reach_global_and_function_specific_numerical_components():
    rows = metadata()
    rows.append(read_ncbi_assembly_metadata({"accession": "GCA_SYNTHETIC.1", "organism": {"taxId": 562},
        "assemblyInfo": {"assemblyLevel": "Complete Genome", "genomeNotes": ["metagenome"]},
        "assemblyStats": {"numberOfContigs": "3", "contigN50": "12000", "totalSequenceLength": "31000"},
        "checkmInfo": {"completeness": 96.5, "contamination": 2.4, "checkmVersion": "v1.2.0"}},
        reference_accession="SYN_A", assembly_accession="GCA_SYNTHETIC.1",
        linkage_source="synthetic-protein-to-assembly-link", source="synthetic-assembly-report"))
    sheet = grade_json(reference_metadata=rows)["sheet"]
    associations = sheet["hits"][0]["associations"]
    measured = [row for row in associations if row["assembly"]]
    assert len(measured) == 1
    assert measured[0]["quality_measurements"]["completeness_fraction"] == pytest.approx(.965)
    assert measured[0]["quality_measurements"]["contamination_fraction"] == pytest.approx(.024)
    assert measured[0]["quality_measurements"]["total_sequence_length"] == 31000
    assert sheet["source_quality"]["assembly_measurements"][0]["measurements"]["contig_count"] == 3
    functions = {row["function"]: row for row in sheet["functions"]}
    # A separate assembly report describes the same exact accession and taxon:
    # it must remain available when evaluating that accession's EC assignment.
    f_quality = functions[F]["source_quality"]["assembly_measurements"]
    assert len(f_quality) == 1
    assert f_quality[0]["measurements"]["completeness_fraction"] == pytest.approx(.965)
    assert functions[G]["source_quality"]["assembly_measurements"] == []


def test_saved_sheet_can_recalculate_without_reparsing_or_acquisition(tmp_path, monkeypatch):
    graded = grade_json(reference_metadata=metadata(), database_profile=PROFILE)
    saved = tmp_path / "sheet.json"
    saved.write_text(json.dumps(graded["sheet"], allow_nan=False))
    reopened = json.loads(saved.read_text())
    def forbidden(*_args, **_kwargs):
        raise AssertionError("recalculation must not read BLAST or fetch source data")
    monkeypatch.setattr("gene_annotation_episode.blast_graders.parse_blast_json", forbidden)
    monkeypatch.setattr("gene_annotation_episode.blast_graders.parse_blast_tabular", forbidden)
    monkeypatch.setattr("gene_annotation_episode.acquisition.PublicClients.blast", forbidden)
    assert calculate_database_probabilities(reopened) == graded["probabilities"]
    recalculated = calculate_database_probabilities(reopened, model={"temperature_bits": 2})
    assert recalculated["parameters"]["temperature_bits"] == 2
    assert recalculated["unadjusted_probabilities"][F] < .8
    assert reopened == json.loads(saved.read_text())


@pytest.mark.parametrize("filename,fmt", [("native_pair_result.json", "json2"), ("native_pair_result.tsv", "tabular")])
def test_recorded_native_pair_uses_public_entrypoint(filename, fmt):
    fixture = Path(__file__).parent / "fixtures/blast_grading_inputs" / filename
    result = grade_blast_result(fixture.read_bytes(), mode="pairwise", resource="local", output_format=fmt)
    assert result["probabilities"] is None
    sheet = result["sheet"]
    assert sheet["union"]["counts"]["distinct_residue_pairs"] == 243
    assert sheet["union"]["counts"]["identical_residue_pairs"] == 238
    assert sheet["union"]["fractions"]["query_paired_coverage"] == pytest.approx(243 / 253)
    assert sheet["union"]["fractions"]["reference_paired_coverage"] == 1
    assert sheet["union"]["fractions"]["paired_identity"] == pytest.approx(238 / 243)
    assert sheet["hsps"][0]["components"]["counts"]["reference_gap_columns"] == 10


def test_file_entrypoint_writes_roundtrippable_sheet_and_calculations(tmp_path, capsys):
    result_file = tmp_path / "native.json"
    result_file.write_text(json.dumps(native_document()))
    metadata_file = tmp_path / "metadata.json"
    metadata_file.write_text(json.dumps(metadata()))
    request_file = tmp_path / "request.json"
    request_file.write_text(json.dumps(REQUEST))
    output = tmp_path / "graded.json"
    main(["--input", str(result_file), "--output", str(output), "--mode", "database",
        "--resource", "hpc", "--format", "json2", "--request", str(request_file),
        "--reference-metadata", str(metadata_file)])
    assert json.loads(capsys.readouterr().out)["output"] == str(output)
    graded = json.loads(output.read_text())
    assert graded["probabilities"]["unadjusted_probabilities"] == {F: .8, G: .2}
    assert graded["sheet"]["normalized_result"]["resource"] == "hpc"


def test_standard_tabular_reported_identity_survives_without_invented_residue_pairs():
    row = b"query\tref\t83.33\t12\t2\t0\t1\t12\t1\t12\t0.001\t25\n"
    result = grade_blast_result(row, mode="pairwise", resource="local", output_format="tabular",
        fields=["std"], request={"program": "blastp"})
    component = result["sheet"]["hsps"][0]["components"]
    assert component["reported_percentages"]["identity_percent"] == 83.33
    assert component["fractions"]["alignment_identity"] == pytest.approx(.8333)
    assert component["counts"]["identical_pairs"] is None
    assert component["pairs"] == []
    assert component["fractions"]["query_paired_coverage"] is None


