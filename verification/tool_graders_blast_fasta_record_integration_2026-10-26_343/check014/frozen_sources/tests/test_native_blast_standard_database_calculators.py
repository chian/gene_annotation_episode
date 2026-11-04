"""R333 deterministic tests. All database reports below are synthetic fixtures."""
from copy import deepcopy
import json
import builtins
import os
import socket
import subprocess
from pathlib import Path

import pytest

from gene_annotation_episode import native_blast_standard_database_calculators as c
from gene_annotation_episode import native_blast_standard_database_result_views as v
from gene_annotation_episode.blast_pairwise_grader import alignment_components
from test_native_blast_standard_database_metadata import (
    ROOT, add_metadata, fixture, hit, hsp, numerical_metadata, pssm, report, run, received, query_payload, address, encoded,
)


def assert_pure(monkeypatch):
    def fail(*a, **kw): pytest.fail("pure R boundary attempted I/O")
    for obj, name in ((builtins, "open"), (Path, "open"), (Path, "read_bytes"), (Path, "read_text"),
            (os, "stat"), (os, "listdir"), (socket, "socket"), (socket, "getaddrinfo"), (subprocess, "Popen"), (subprocess, "run")):
        monkeypatch.setattr(obj, name, fail)


def calculate(inputs, model=None):
    sheets = run(inputs)
    result = c.calculate_standard_blast_database_sheets(sheets, sequence_model=model)
    rows = c.build_standard_blast_database_rows(bundle_identity=inputs["bundle"]["identity"], calculation_id="a" * 64,
        sheet_set=sheets, calculations=result)
    return sheets, result, rows


def cell(row, name):
    return next(x for x in row["measurements"] + row["booleans"] if x["name"] == name)


def family(rows, name):
    return [r for r in rows if r["family"] == name]


def numerical():
    inputs = fixture()
    add_metadata(inputs, numerical_metadata(inputs), "sequence_database")
    return inputs


def test_R1_R2_kernel_temperature_census_and_single_scientific_call(monkeypatch):
    inputs = numerical()
    sheets = run(inputs)
    calls = []
    original = c._sequence.calculate_blast_sequence_database_components
    def counted(sheet, *, model):
        calls.append((deepcopy(sheet), deepcopy(model)))
        return original(sheet, model=model)
    monkeypatch.setattr(c._sequence, "calculate_blast_sequence_database_components", counted)
    for temperature, probabilities in ((1, (.8, .2)), (2, (2 / 3, 1 / 3))):
        model = dict(temperature_bits=temperature, function_priors={"F": .5, "G": .5})
        with monkeypatch.context() as blocked:
            assert_pure(blocked)
            results = c.calculate_standard_blast_database_sheets(sheets, sequence_model=model)
            rows = c.build_standard_blast_database_rows(bundle_identity=inputs["bundle"]["identity"], calculation_id=str(temperature) * 64,
                sheet_set=sheets, calculations=results)
        function_rows = family(rows, "sequence_function")
        assert [cell(r, "unadjusted_probability")["value"] for r in function_rows] == pytest.approx(probabilities)
        if temperature == 1:
            assert [cell(r, "representation_adjusted_probability")["value"] for r in function_rows] == pytest.approx((2 / 7, 5 / 7))
        assert all(cell(r, "calibrated_annotation_probability")["value"] is False for r in function_rows)
        population = family(rows, "sequence_population")
        assert [cell(r, "database_sequence_count")["value"] for r in population] == [100, 10]
        assert all(r["identity"]["count_unit"] == r["context"]["count_unit"] == "unique_sequences" for r in population)
    assert len(calls) == 2 and calls[0][0] == calls[1][0] == sheets["sequence"][0]["sheet"]
    assert calls[0][1]["temperature_bits"] == 1 and calls[1][1]["temperature_bits"] == 2


@pytest.mark.parametrize("model", [[], True, {"temperature_bits": 0}, {"temperature_bits": -1},
    {"temperature_bits": float("inf")}, {"function_priors": {}}, {"function_priors": {"F": -1}},
    {"function_priors": {"F": 0}}, {"function_priors": {"F": 1e308, "G": 1e308}}, {"hidden": 1}])
def test_R2_invalid_model_never_falls_back(model, monkeypatch):
    sheets = run(fixture())
    def forbidden(*a, **kw): raise AssertionError("invalid model reached scientific calculator")
    monkeypatch.setattr(c._sequence, "calculate_blast_sequence_database_components", forbidden)
    with pytest.raises(ValueError): c.calculate_standard_blast_database_sheets(sheets, sequence_model=model)


def test_R1_search_specific_incompatible_priors_keep_native_and_sibling(monkeypatch):
    inputs = numerical()
    sheets = run(inputs)
    sibling = deepcopy(sheets["sequence"][0])
    sibling["search_key"]["report_index"] = 1
    sibling["search_key"]["search_pointer"] = "/BlastOutput2/1/report/results/search"
    # Use actual public303 for the incompatible search; a controlled second
    # calculator exception tests the catch boundary without replacement model.
    original = c._sequence.calculate_blast_sequence_database_components
    calls = []
    def counted(sheet, *, model):
        calls.append(model)
        return original(sheet, model=model)
    monkeypatch.setattr(c._sequence, "calculate_blast_sequence_database_components", counted)
    result = c.calculate_standard_blast_database_sheets(sheets, sequence_model={"function_priors": {"other": 1}})
    assert calls == [{"function_priors": {"other": 1}}]
    assert result["sequence"] == [dict(search_key=sheets["sequence"][0]["search_key"], components=None)]
    assert result["issues"][0]["code"] == v.PREFIX + "calculation_failed"
    assert "message" not in result["issues"][0]
    rows = c.build_standard_blast_database_rows(bundle_identity=inputs["bundle"]["identity"], calculation_id="a" * 64,
        sheet_set=sheets, calculations=result)
    assert [cell(r, "native_score_bits")["value"] for r in family(rows, "hsp")] == [20, 18]
    assert all(cell(r, "qualified_geometry_available")["value"] is None for r in family(rows, "hsp"))


@pytest.mark.parametrize("program", v.PROGRAMS)
def test_R3_all_standard_modes_units_and_full_denominators(program):
    qnt, snt = program in {"blastn", "blastx", "tblastx"}, program in {"blastn", "tblastn", "tblastx"}
    translated = program != "blastn"
    qwidth = 3 if qnt and translated else 1
    swidth = 3 if snt and translated else 1
    native = hsp(qseq="AAAA", hseq="AAAA", query_to=4 * qwidth, hit_to=4 * swidth,
        **({"query_frame": 1} if qwidth == 3 else {}), **({"hit_frame": 1} if swidth == 3 else {}))
    inputs = fixture(program, query=b">q\n" + b"A" * (8 * qwidth) + b"\n",
        doc=report(program, query_len=8 * qwidth, hits=[hit(length=10 * swidth, hsps=[native])]))
    sheets, result, rows = calculate(inputs)
    row = family(rows, "hsp")[0]
    assert row["context"]["query_unit"] == ("nt" if qnt else "aa")
    assert row["context"]["reference_unit"] == ("nt" if snt else "aa")
    assert cell(row, "qualified_paired_query_units")["value"] == 4 * qwidth
    assert cell(row, "qualified_paired_reference_units")["value"] == 4 * swidth
    assert cell(row, "full_query_paired_coverage")["value"] == .5
    assert cell(row, "full_reference_paired_coverage")["value"] == .4
    assert cell(family(rows, "sequence_hit")[0], "selected_query_coverage")["value"] is None
    pointer = result["qualified_hsp_components"][0]["component_pointer"]
    qualified = c._at(result, pointer)
    assert qualified["counts"]["paired_query_positions"] == cell(row, "qualified_paired_query_units")["value"]


def test_R3_retained_paired_blastx_format_and_separate_synthetic_database_range():
    path = ROOT / "verification/tool_graders_blast_pairwise_2026-10-26_294/native_ranges/blastx_range_reverse_json15/attempt/report.json"
    raw = path.read_bytes(); native = json.loads(raw)
    actual = native["BlastOutput2"][0]["report"]
    assert "subjects" in actual["search_target"]  # Paired evidence stays paired.
    source_hsp = actual["results"]["bl2seq"][0]["hits"][0]["hsps"][0]
    component = alignment_components(source_hsp, program="blastx", query_length=244, reference_length=80, coordinate_convention="blast_json2")
    assert (component["pairs"][0]["query_start"], component["pairs"][0]["query_end"]) == (212, 215)
    native_hsp = hsp(qseq="A" * 62, hseq="A" * 62, query_from=30, query_to=215, query_frame=-3,
        hit_from=10, hit_to=71, align_len=62, identity=62)
    inputs = fixture("blastx", query=b">q\n" + b"A" * 244 + b"\n", options=["-query_loc", "30-215"],
        doc=report("blastx", query_len=186, hits=[hit(length=80, hsps=[native_hsp])]))
    sheets, result, rows = calculate(inputs)
    h = family(rows, "hsp")[0]
    assert cell(h, "reported_query_length")["value"] == 186
    assert cell(h, "reported_query_coverage")["value"] is None
    assert cell(h, "full_query_paired_coverage")["value"] == 186 / 244
    assert cell(h, "qualified_paired_query_units")["value"] == 186
    assert cell(family(rows, "sequence_hit")[0], "selected_query_coverage")["value"] == 1
    exact = c._at(result, result["qualified_hsp_components"][0]["component_pointer"])
    assert (exact["pairs"][0]["query_start"], exact["pairs"][0]["query_end"]) == (212, 215)
    assert path.read_bytes() == raw


def test_R3_translated_overlap_union_and_invalid_preceding_hsp():
    first = hsp(qseq="AA", hseq="AA", query_from=1, query_to=6, query_frame=1, hit_from=1, hit_to=6, hit_frame=1, align_len=2, identity=2)
    second = dict(first, query_from=4, query_to=9, hit_from=4, hit_to=9)
    inputs = fixture("tblastx", query=b">q\nAAAAAAAAAAAA\n", doc=report("tblastx", query_len=12,
        hits=[hit(length=15, hsps=[None, first, second])]))
    sheets, result, rows = calculate(inputs)
    assert [r["row_key"]["hsp_ordinal"] for r in result["native_hsp_components"]] == [0, 1, 2]
    qualified = result["qualified_hsp_components"]
    assert qualified[0]["component_pointer"] is None
    assert qualified[1]["component_pointer"].endswith("/hsp_components/0")
    assert qualified[2]["component_pointer"].endswith("/hsp_components/1")
    invalid_row = family(rows, "hsp")[0]
    assert cell(invalid_row, "reported_query_length")["value"] == 12
    assert cell(invalid_row, "reported_reference_length")["value"] == 15
    assert cell(invalid_row, "reported_query_coverage")["denominator"] == 12
    assert cell(invalid_row, "reported_reference_coverage")["denominator"] == 15
    assert cell(invalid_row, "native_score_bits")["value"] is None
    assert cell(invalid_row, "paired_query_units")["value"] is None
    assert cell(invalid_row, "qualified_paired_query_units")["value"] is None
    assert cell(invalid_row, "full_query_paired_coverage")["value"] is None
    invalid_component = result["native_hsp_components"][0]["component"]
    assert invalid_component["geometry_available"] is False and invalid_component["pairs"] == []
    assert invalid_component["native_scores"] == dict(bit_score=None, score=None, evalue=None)
    union = family(rows, "sequence_hit")[0]
    assert cell(union, "observed_paired_query_positions")["value"] == 9
    assert cell(union, "observed_paired_reference_positions")["value"] == 9
    assert cell(union, "query_paired_coverage")["value"] is None  # Invalid original HSP means incomplete union.
    assert cell(family(rows, "hsp")[1], "qualified_paired_query_units")["value"] == 6


def test_R3_unknown_full_query_identity_is_unavailable_not_reported_length():
    inputs = fixture(doc=report(query_id="other", query_title="other"))
    _, result, rows = calculate(inputs)
    h = family(rows, "hsp")[0]
    assert cell(h, "native_score_bits")["value"] == 20
    assert cell(h, "reported_query_length")["value"] == 8
    assert cell(h, "full_query_paired_coverage")["value"] is None
    assert cell(h, "full_query_paired_coverage")["denominator"] is None


def test_R5_native_statistics_keep_exact_source_units_and_zero():
    doc = report()
    doc["BlastOutput2"][0]["report"]["results"]["search"]["stat"].update(hsp_len=0, eff_space=123456, **{"lambda": .267, "kappa": .041, "entropy": .14})
    _, _, rows = calculate(fixture(doc=doc))
    row = family(rows, "search_statistic")[0]
    assert [x["value"] for x in row["measurements"]] == [1000, 10000, 0, 123456, .267, .041, .14]
    assert cell(row, "native_hsp_length_adjustment")["status"] == "available"
    assert cell(row, "native_database_letters")["unit"] == "native_database_letter"


@pytest.mark.parametrize("fmt,raw,fields,expected", [
    ("json15", report(hits=[]), None, 0),
    ("tabular7", b"# BLASTP 2.17.0+\n# Query: q\n# Database: target\n# 0 hits found\n", ["qseqid", "sseqid"], 0),
    ("tabular6", b"", ["qseqid", "sseqid"], None),
])
def test_R4_empty_native_populations_are_not_fabricated(fmt, raw, fields, expected):
    _, result, rows = calculate(fixture(doc=raw, fmt=fmt, fields=fields))
    assert not family(rows, "hsp")
    assert not family(rows, "sequence_function")
    if expected is not None:
        assert cell(family(rows, "search")[0], "reported_hit_count")["value"] == expected
    else:
        assert not rows or cell(family(rows, "search")[0], "reported_hit_count")["value"] is None


def test_R5_actual_pssm_population_once_and_original_cells(monkeypatch):
    inputs = fixture("tblastn", kind="pssm", query=pssm(), doc=report("psitblastn", query_len=3, hits=[]))
    sheets = run(inputs)
    calls = []; original = c._pssm.calculate_blast_pssm_components
    def counted(sheet): calls.append(sheet); return original(sheet)
    monkeypatch.setattr(c._pssm, "calculate_blast_pssm_components", counted)
    result = c.calculate_standard_blast_database_sheets(sheets, sequence_model=None)
    rows = c.build_standard_blast_database_rows(bundle_identity=inputs["bundle"]["identity"], calculation_id="a" * 64, sheet_set=sheets, calculations=result)
    assert calls == sheets["pssm"]
    assert len(family(rows, "pssm_matrix")) == 1 and len(family(rows, "pssm_position")) == 3 and len(family(rows, "pssm_cell")) == 6
    assert [cell(r, "freqRatios")["value"] for r in family(rows, "pssm_cell")] == [0, 1, 2, 3, 4, 5]
    assert all(cell(r, "scores")["value"] is None for r in family(rows, "pssm_cell"))


def test_R1_wrong_source_hash_is_invalid_supplied_sheet():
    inputs = fixture(); sheets = run(inputs)
    report_doc = next(r for r in sheets["prepared_inputs"]["resolved_documents"] if r["catalog"].get("artifact_key") == "report")
    report_doc["contents_hex"] = b"changed".hex()
    with pytest.raises(ValueError, match="saved_search_source_identity_invalid"):
        c.calculate_standard_blast_database_sheets(sheets, sequence_model=None)


def test_R1_tblastn_eighty_amino_acids_are_240_nucleotides():
    native = hsp(qseq="A" * 80, hseq="A" * 80, query_to=80, hit_to=240, hit_frame=1, align_len=80, identity=80)
    inputs = fixture("tblastn", query=b">q\n" + b"A" * 80 + b"\n", doc=report("tblastn", query_len=80, hits=[hit(length=243, hsps=[native])]))
    _, _, rows = calculate(inputs)
    row = family(rows, "hsp")[0]
    assert cell(row, "full_query_paired_coverage")["value"] == 1
    assert cell(row, "full_reference_paired_coverage")["value"] == 240 / 243
    assert cell(row, "qualified_paired_reference_units")["value"] == 240


@pytest.mark.parametrize("changes", [{"query_frame": -2}, {"query_to": 8}, {"query_frame": 0}])
def test_R3_invalid_translated_phase_keeps_string_counts(changes):
    native = hsp(qseq="AAA", hseq="AAA", query_from=1, query_to=9, query_frame=1,
        hit_from=1, hit_to=9, hit_frame=1, align_len=3, identity=3)
    native.update(changes)
    _, _, rows = calculate(fixture("tblastx", query=b">q\nAAAAAAAAAAAA\n",
        doc=report("tblastx", query_len=12, hits=[hit(length=12, hsps=[native])])))
    row = family(rows, "hsp")[0]
    assert cell(row, "alignment_columns")["value"] == cell(row, "identical_pairs")["value"] == 3
    assert cell(row, "native_score_bits")["value"] == 20
    assert cell(row, "qualified_geometry_available")["value"] is False
    assert cell(row, "full_query_paired_coverage")["value"] is None


def test_R4_duplicate_full_reference_maximum_once_and_missing_census():
    inputs = fixture()
    payload = numerical_metadata(inputs, sequences=("ACDEFGHIKL", "ACDEFGHIKL"), census=False)
    add_metadata(inputs, payload, "sequence_database")
    _, result, rows = calculate(inputs)
    groups = family(rows, "sequence_group")
    assert len(groups) == 1 and groups[0]["identity"]["hit_ordinals"] == [0, 1]
    assert cell(groups[0], "maximum_bit_score")["value"] == 20
    assert cell(groups[0], "hit_representation_count")["value"] == 2
    functions = family(rows, "sequence_function")
    assert [cell(r, "function_mass")["value"] for r in functions] == [.5, .5]
    assert all(cell(r, "representation_adjusted_probability")["value"] is None for r in functions)
    assert not family(rows, "sequence_population")


def test_R5_taxa_A_A_B_and_independent_target_A():
    inputs = fixture(doc=report(hits=[hit(), hit(1), hit(2)]))
    payload = numerical_metadata(inputs, sequences=("ACDEFGHIKL", "ACDEPQRSTV", "ACDEFGHIKM"), indices=(0, 1, 2), description_ordinals=(0, 0, 0), census=False)
    for i, row in enumerate(payload["searches"][0]["reference_metadata"]):
        row["lineage"] = [dict(rank="genus", taxid=10 if i < 2 else 20, name=None)]
    add_metadata(inputs, payload, "sequence_database")
    target = query_payload(); source = received(inputs, "independent-target", encoded(dict(taxid=10)))
    target["documents"] = [source]
    target["target_contexts"] = [dict(search_key=address(), taxid=10, lineage=[dict(rank="genus", taxid=10, name=None)],
        independent_of_search=True, source=dict(source_ref=source["document_key"], pointer=""))]
    add_metadata(inputs, target, "query_identity", "target-meta")
    _, _, rows = calculate(inputs)
    row = next(r for r in family(rows, "sequence_taxonomy") if r["identity"]["function"] is None and r["identity"]["rank"] == "genus")
    assert cell(row, "same_taxon_pair_count")["value"] == 1
    assert cell(row, "comparable_pair_count")["value"] == 3
    assert cell(row, "same_taxon_pair_fraction")["value"] == pytest.approx(1 / 3)
    assert cell(row, "target_matching_fraction")["value"] == pytest.approx(2 / 3)
    assert cell(row, "target_matching_fraction")["numerator"] == 2
    assert cell(row, "target_matching_fraction")["denominator"] == 3
    assert cell(row, "target_independent_of_search")["value"] is True


def test_R6_assembly_percentages_original_source_and_method():
    from gene_annotation_episode.blast_reference_metadata import read_ncbi_assembly_metadata
    inputs = fixture(); payload = numerical_metadata(inputs, census=False)
    native = dict(accession="GCA_SYNTHETIC.1", checkmInfo=dict(completeness=95, contamination=125, checkmVersion="synthetic-version"),
        assemblyStats=dict(numberOfContigs="3", contigN50="12000", totalSequenceLength="31000"))
    source = received(inputs, "assembly", encoded(native)); link = received(inputs, "assembly-link", encoded(dict(reference="S0.1", assembly="GCA_SYNTHETIC.1")))
    payload["documents"] += [source, link]
    extracted = read_ncbi_assembly_metadata(native, reference_accession="S0.1", assembly_accession="GCA_SYNTHETIC.1",
        linkage_source=link["document_key"], source=source["document_key"])
    allowed = ("accession", "completeness_fraction", "contamination_fraction", "contig_count", "contig_n50", "total_sequence_length",
        "quality_method", "quality_version", "measurement_methods", "source", "linkage_source")
    payload["searches"][0]["reference_metadata"][0]["assembly"] = {k: extracted["assembly"][k] for k in allowed}
    add_metadata(inputs, payload, "sequence_database")
    sheets, results, rows = calculate(inputs)
    row = next(r for r in family(rows, "sequence_quality") if r["identity"]["function"] is None)
    assert cell(row, "completeness_fraction")["value"] == .95
    assert cell(row, "contamination_fraction")["value"] == 1.25
    assert cell(row, "contig_n50")["value"] == 12000 and cell(row, "contig_n50")["unit"] == "nt"
    assert cell(row, "total_sequence_length")["value"] == 31000
    quality = results["sequence"][0]["components"]["components"]["database_sheet"]["source_quality"]["assembly_measurements"][0]
    assert quality["quality_method"] == "CheckM"
    assert any(r["contents_hex"] == encoded(native).hex() for r in sheets["prepared_inputs"]["resolved_documents"])


def test_R7_table_declared_rows_not_subjects_and_native_percent_fallback():
    fields = ["qseqid", "sseqid", "pident", "qcovhsp", "qcovs", "bitscore", "evalue"]
    raw = b"# BLASTP 2.17.0+\n# Query: q\n# Database: target\n# 2 hits found\nq\ts\t50\t25\t75\t20\t0\nq\ts\t60\t30\t75\t18\t0\n"
    _, _, rows = calculate(fixture(fmt="tabular7", fields=fields, doc=raw))
    search = family(rows, "search")[0]
    assert cell(search, "declared_alignment_row_count")["value"] == 2
    assert cell(search, "declared_alignment_row_count")["unit"] == "alignment_row"
    assert cell(search, "reported_hit_count")["value"] == 1
    h = family(rows, "hsp")[0]
    assert cell(h, "native_reported_identity_percent")["value"] == 50
    assert cell(h, "alignment_identity")["value"] == .5 and cell(h, "alignment_identity")["denominator"] is None
    assert cell(h, "reported_reference_coverage")["value"] is None


def test_R9_mutated_normalized_score_not_authenticated_as_native():
    inputs = fixture(); sheets = run(inputs)
    sheets["collection"]["searches"][0]["normalized"]["hits"][0]["hsps"][0]["bit_score"] = 999
    sheets["sequence"][0]["sheet"]["search"] = deepcopy(sheets["collection"]["searches"][0])
    results = c.calculate_standard_blast_database_sheets(sheets, sequence_model=None)
    assert results["native_hsp_components"][0]["component"]["native_scores"]["bit_score"] is None
    assert results["native_hsp_components"][1]["component"]["native_scores"]["bit_score"] == 18


def test_R2_unchanged_retained_paired_table_directional_coordinates():
    from gene_annotation_episode.blast_grading_inputs import parse_blast_tabular
    path = ROOT / "verification/tool_graders_blast_pairwise_2026-10-26_294/native_ranges/blastx_range_reverse_tabular7/attempt/report.tsv"
    raw = path.read_bytes()
    parsed = parse_blast_tabular(raw, mode="pairwise", resource="local", request={"program": "blastx"})
    native = parsed["hits"][0]["hsps"][0]
    assert native["query_from"] == 215 and native["query_to"] == 30
    component = alignment_components(native, program="blastx", query_length=244, reference_length=80, coordinate_convention="directional")
    assert component["fractions"]["query_paired_coverage"] == 186 / 244
    assert (component["pairs"][0]["query_start"], component["pairs"][0]["query_end"]) == (212, 215)
    assert path.read_bytes() == raw


def test_R10_search_exception_preserves_successful_real_sibling(monkeypatch):
    native = report()
    native["BlastOutput2"].append(deepcopy(native["BlastOutput2"][0]))
    inputs = fixture(doc=native); sheets = run(inputs)
    original = c._sequence.calculate_blast_sequence_database_components; calls = []
    def sometimes(sheet, *, model):
        calls.append(sheet["search"]["search_key"]["report_index"])
        if calls[-1] == 0: raise ValueError("retained synthetic first-search failure")
        return original(sheet, model=model)
    monkeypatch.setattr(c._sequence, "calculate_blast_sequence_database_components", sometimes)
    results = c.calculate_standard_blast_database_sheets(sheets, sequence_model=None)
    assert calls == [0, 1]
    assert results["sequence"][0]["components"] is None
    assert results["sequence"][1]["components"]["schema"] == "blast_sequence_database_result_components_v1"
    rows = c.build_standard_blast_database_rows(bundle_identity=inputs["bundle"]["identity"], calculation_id="a" * 64, sheet_set=sheets, calculations=results)
    assert len(family(rows, "hsp")) == 4
    assert all(r["identity"]["row_key"]["search_key"]["report_index"] == 1 for r in family(rows, "sequence_hit"))
