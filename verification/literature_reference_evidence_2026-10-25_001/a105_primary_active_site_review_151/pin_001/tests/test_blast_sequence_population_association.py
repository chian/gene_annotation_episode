"""Numerical v3 examples on deliberately synthetic native-format reports."""
from copy import deepcopy
import builtins
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import blast_database_grader as grader
from gene_annotation_episode import blast_sequence_database as sequence
from gene_annotation_episode import blast_report_collection as collection
from test_blast_sequence_database import inputs, collect, document, invocation, native_search, operand
from test_blast_database_population_associations import population_inputs, OPERAND, PREFIX


def sequence_inputs(program="blastp", query_kind="sequence", *, format_name="json15", native_database=OPERAND,
                    no_hits=False, iterations=None):
    qnt, rnt = program in ("blastn", "blastx", "tblastx"), program in ("blastn", "tblastn", "tblastx")
    translated_q, translated_r = program in ("blastx", "tblastx"), program in ("tblastn", "tblastx")
    query = operand(length=12, selected_interval=[0, 12], molecule="dna" if qnt else "protein")
    inv = invocation(program, query_kind, query=query, request={"db": OPERAND})
    native = native_search(query_len=12)
    for hit in native["hits"]:
        hit["len"] = 12
        hsp = hit["hsps"][0]
        hsp.update(query_from=1, query_to=12 if translated_q else 4, hit_from=1,
                   hit_to=12 if translated_r else 4, qseq="ACGT", hseq="ACGT")
        if translated_q: hsp["query_frame"] = 1
        if translated_r: hsp["hit_frame"] = 1
    if no_hits: native["hits"] = []
    doc = document(program, search=native, iterations=iterations)
    if program == "tblastn" and query_kind == "pssm":
        doc["BlastOutput2"][0]["report"].update(program="psitblastn", version="PSITBLASTN 2.17.0+")
    doc["BlastOutput2"][0]["report"]["search_target"]["db"] = native_database
    if format_name == "json15":
        search = collect(doc=doc, inv=inv)["searches"][0]
    else:
        fields = ["qseqid", "sseqid", "qlen", "slen", "qstart", "qend", "sstart", "send", "length", "nident", "bitscore", "evalue", "qseq", "sseq"]
        header = (f"# {program.upper()} 2.17.0+\n# Query: q\n# Database: {native_database}\n" if format_name == "tabular7" else "")
        raw = header + "".join("\t".join(map(str, ["q", name, 12, 12, 1, 4, 1, 4, 4, 4, score, 0, "ACGT", "ACGT"])) + "\n"
            for name, score in (() if no_hits else (("A", 20), ("B", 18))))
        if format_name == "tabular7": raw += f"# {0 if no_hits else 2} hits found\n"
        search = collect(raw=raw.encode(), inv=inv, format_name=format_name, fields=fields)["searches"][0]
    args = inputs(search)
    args["report_source"]["source_ref"] = "source:original-report"
    args["query_binding"]["coordinate_unit"] = "nt" if qnt else "aa"
    for i, row in enumerate(args["sequence_identity_bindings"]):
        symbols = ("ACGTACGTACGT" if i == 0 else "ACGTACGTACTA") if rnt else ("ACDEFGHIKLMN" if i == 0 else "ACDEPQRSTVWL")
        digest = hashlib.sha256(symbols.encode()).hexdigest()
        row["binding"].update(molecule="nt" if rnt else "aa", sequence_length=12, digest=digest, sequence_group="sha256:" + digest)
    population = population_inputs(key=search["search_key"])
    args["search_binding"]["database_identity"] = population["database_identity"]
    args["database_profile"] = population["database_profile"]
    args["database_population_associations"] = population["context"]["associations"]
    return args


def calculate(args, model=None):
    return sequence.calculate_blast_sequence_database_components(sequence.populate_blast_sequence_database_sheet(**args), model=model)


def assert_numbers(out, *, adjusted=True, temperature=1):
    c = out["components"]
    weights, database = c["function_weights"], c["database_sheet"]
    assert weights["unadjusted_probabilities"] == ({"F": 4/5, "G": 1/5} if temperature == 1 else {"F": 2/3, "G": 1/3})
    assert weights["function_masses"] == ({"F": 1, "G": 1/4} if temperature == 1 else {"F": 1, "G": 1/2})
    if adjusted:
        expected = {"F": 2/7, "G": 5/7} if temperature == 1 else {"F": 1/6, "G": 5/6}
        assert weights["representation_adjusted_probabilities"] == pytest.approx(expected)
        assert [r["database_fraction"] for r in database["database_representation"]["function_representation"]] == [10/11, 1/11]
        assert database["database_population_relation"]["status"] == "available"
    else:
        assert weights["representation_adjusted_probabilities"] is None
    return database, weights


@pytest.mark.parametrize("program,query_kind", [(p, "sequence") for p in
    ("blastn", "blastp", "blastx", "tblastn", "tblastx", "psiblast", "deltablast")] +
    [("tblastn", "pssm"), ("psiblast", "pssm"), ("psiblast", "msa")])
def test_seven_programs_and_qualified_query_axes_preserve_native_facts(program, query_kind):
    args = sequence_inputs(program, query_kind)
    before = deepcopy(args)
    sheet = sequence.populate_blast_sequence_database_sheet(**args)
    assert sheet["schema"] == sequence.SHEET_SCHEMA_V3
    database, weights = assert_numbers(sequence.calculate_blast_sequence_database_components(sheet))
    assert database["schema"] == grader.SHEET_SCHEMA_V3 and database["association_mode"] == "explicit_bindings_v2"
    assert args == before and sheet["search"] == before["search"]
    assert database["normalized_result"]["search"]["database"] == OPERAND
    assert database["normalized_result"]["search"]["request"] == {"db": OPERAND}
    assert database["calculation_context"]["database_identity"]["value"] == "curated-proteins"
    assert len(database["sequence_groups"]) == 2 and weights["calibrated_annotation_probability"] is False
    assert_numbers(sequence.calculate_blast_sequence_database_components(sheet, model={"temperature_bits": 2}), temperature=2)


@pytest.mark.parametrize("format_name", ["json15", "tabular7", "tabular6"])
def test_native_formats_and_headerless_database_stays_null(format_name):
    args = sequence_inputs(format_name=format_name)
    database, _ = assert_numbers(calculate(args))
    assert database["normalized_result"]["search"]["database"] == (None if format_name == "tabular6" else OPERAND)


def test_absent_and_empty_associations_do_not_infer_path_basename_equivalence():
    args = sequence_inputs()
    args["database_population_associations"] = None
    args["report_source"].pop("source_ref")
    old = sequence.populate_blast_sequence_database_sheet(**args)
    assert old["schema"] == sequence.SHEET_SCHEMA
    assert "database_population_associations" not in old
    database, _ = assert_numbers(sequence.calculate_blast_sequence_database_components(old), adjusted=False)
    assert "database_context_value_conflict" in database["database_representation"]["reasons"]
    args["database_population_associations"] = []
    database, _ = assert_numbers(calculate(args), adjusted=False)
    assert database["database_population_relation"]["status"] == "unavailable"
    assert "database_context_value_conflict" in database["database_representation"]["reasons"]
    other = sequence_inputs(native_database="/other/location/proteins")
    other["database_population_associations"] = []
    assert_numbers(calculate(other), adjusted=False)


def test_exact_native_identity_can_use_old_rules_with_empty_list_but_not_selected_malformed_assertion():
    args = sequence_inputs(native_database="curated-proteins")
    # Original invocation also uses the exact semantic identity in this case.
    args["search"]["normalized"]["search"]["request"] = {"db": "curated-proteins"}
    args["database_population_associations"] = []
    out = calculate(args)
    assert out["components"]["function_weights"]["representation_adjusted_probabilities"] == pytest.approx({"F": 2/7, "G": 5/7})
    assert out["components"]["database_sheet"]["database_population_relation"]["status"] == "unavailable"
    args["database_population_associations"] = sequence_inputs()["database_population_associations"]
    args["database_population_associations"][0]["assertion_record"]["value"] = {"available": True}
    assert_numbers(calculate(args), adjusted=False)


@pytest.mark.parametrize("change,expected", [
    (lambda a: a["database_population_associations"][0]["assertion_record"]["value"].update(database_manifest_sha256="9" * 64), PREFIX + "manifest_identity_conflict"),
    (lambda a: a["database_population_associations"][0]["assertion_record"]["value"].update(native_database_operand="/different/proteins"), PREFIX + "native_operand_conflict"),
    (lambda a: a["database_profile"].update(release="release2"), "database_profile_release_unmatched"),
    (lambda a: a["database_profile"].update(scope="taxon_subset"), "database_profile_scope_mismatch"),
    (lambda a: a["database_profile"].update(count_unit="reads"), "database_profile_requires_sequence_count_unit"),
    (lambda a: a["database_profile"]["function_counts"].pop("G"), "database_function_count_unavailable_or_invalid:G"),
    (lambda a: a["database_profile"]["function_counts"].update(G=0), "database_function_count_below_observed_groups:G"),
    (lambda a: a["database_profile"].update(total_count=0), "database_profile_total_count_invalid"),
    (lambda a: a["database_profile"].update(source=""), "database_profile_source_required"),
])
def test_non_name_population_qualifications_survive(change, expected):
    args = sequence_inputs()
    change(args)
    database, weights = assert_numbers(calculate(args), adjusted=False)
    assert expected in weights["representation_adjustment_unavailable_reasons"]
    assert database["normalized_result"]["search"]["database"] == OPERAND


def test_unknown_release_and_both_null_do_not_qualify():
    args = sequence_inputs()
    args["search_binding"]["database_identity"]["release"] = None
    args["database_profile"]["release"] = None
    selected = population_inputs(key=args["search"]["search_key"], identity=args["search_binding"]["database_identity"], profile=args["database_profile"])
    args["database_population_associations"] = selected["context"]["associations"]
    database, weights = assert_numbers(calculate(args), adjusted=False)
    assert database["database_population_relation"]["status"] == "unavailable"
    assert "database_context_release_unavailable" in weights["representation_adjustment_unavailable_reasons"]


def test_same_ordinals_in_other_query_round_and_member_do_not_crosslink():
    for field, value in (("artifact_key", "another-report"), ("report_index", 4), ("member_ordinal", 2),
            ("search_pointer", "/BlastOutput2/0/report/results/iterations/1/search")):
        args = sequence_inputs("psiblast")
        args["database_population_associations"][0]["search_key"][field] = value
        database, _ = assert_numbers(calculate(args), adjusted=False)
        assert PREFIX + "search_key_mismatch" in database["database_population_relation"]["reason_codes"]


@pytest.mark.parametrize("layout", ["queries", "rounds"])
def test_original_multi_search_addresses_remain_distinct(layout):
    base = sequence_inputs("psiblast")
    doc = deepcopy(base["search"]["normalized"]["native"]["document"])
    report = doc["BlastOutput2"][0]["report"]
    native = report["results"]["search"]
    inv = invocation("psiblast", query=deepcopy(base["query_binding"]["operand"]), request={"db": OPERAND})
    if layout == "queries":
        other = deepcopy(doc["BlastOutput2"][0])
        other["report"]["results"]["search"].update(query_id="q2", query_title="q2")
        doc["BlastOutput2"].append(other)
        inv["operands"].append({**deepcopy(inv["operands"][0]), "record_ordinal": 1, "native_id": "q2", "native_title": "q2"})
    else:
        report["results"] = dict(iterations=[dict(iter_num=1, search=deepcopy(native)), dict(iter_num=2, search=deepcopy(native))])
    searches = collect(doc=doc, inv=inv)["searches"]
    supplied = []
    for search in searches:
        args = inputs(search)
        args["report_source"]["source_ref"] = "source:original-report"
        key = search["search_key"]
        for row, original in zip(args["sequence_identity_bindings"], base["sequence_identity_bindings"]):
            row["binding"] = {**deepcopy(original["binding"]), "report_index": key["report_index"]}
        population = population_inputs(key=key)
        args.update(database_profile=population["database_profile"], database_population_associations=population["context"]["associations"])
        args["search_binding"]["database_identity"] = population["database_identity"]
        assert_numbers(calculate(args))
        supplied.append(args)
    assert supplied[0]["search"]["search_key"] != supplied[1]["search"]["search_key"]
    supplied[1]["database_population_associations"] = supplied[0]["database_population_associations"]
    assert_numbers(calculate(supplied[1]), adjusted=False)


def test_zero_hit_native_measurements_and_failed_partial_output_keep_meaning():
    args = sequence_inputs(no_hits=True)
    result = calculate(args)
    assert result["status"] == "no_reported_hits"
    database = result["components"]["database_sheet"]
    assert database["coverage"]["native_hit_count"] == 0 and database["sequence_groups"] == []
    assert result["components"]["function_weights"]["unadjusted_probabilities"] is None
    assert result["components"]["function_weights"]["representation_adjusted_probabilities"] is None
    args = sequence_inputs()
    args["search"]["reporting"].update(native_returncode=1, producer_complete=False)
    result = calculate(args)
    assert result["status"] == "partial"
    assert "blast_sequence_database_execution_completion_unqualified" in {i["code"] for i in result["issues"]}


def test_delta_domain_stage_never_uses_sequence_population_context():
    args = sequence_inputs("deltablast")
    args["search_binding"]["stage"] = "domain_database"
    out = calculate(args)
    assert out["status"] == "incompatible" and out["components"]["database_sheet"] is None


def test_v3_preserves_existing_record_locators_and_quality_measurements():
    args = sequence_inputs()
    for i, row in enumerate(args["reference_metadata"]):
        row.update(source="sequences", native_pointer="", record_locator=dict(kind="fasta_record", record_ordinal=i),
            assembly=dict(accession="assembly-" + str(i), completeness_fraction=.95, contamination_fraction=.02,
                contig_count=3, contig_n50=100, total_sequence_length=400, quality_method="synthetic measurement"))
        args["description_bindings"][i]["binding"].update(metadata_source_ref="sequences", metadata_pointer="", metadata_record_locator=row["record_locator"])
        args["sequence_identity_bindings"][i]["binding"].update(pointer="", record_locator=row["record_locator"])
    new = calculate(args)["components"]["database_sheet"]
    args["database_population_associations"] = None
    args["report_source"].pop("source_ref")
    old_sheet = sequence.populate_blast_sequence_database_sheet(**args)
    assert old_sheet["schema"] == sequence.SHEET_SCHEMA_V2
    old = sequence.calculate_blast_sequence_database_components(old_sheet)["components"]["database_sheet"]
    # Locator source identities are the additive v3 source fact; all existing
    # association values and quality measurements remain unchanged.
    def without_new_source(value):
        if isinstance(value, list):
            return [without_new_source(v) for v in value]
        if isinstance(value, dict):
            return {k: without_new_source(v) for k, v in value.items()
                    if not (k == "source_ref" and v == "source:original-report")}
        return value
    new = without_new_source(new)
    for field in ("hits", "sequence_groups", "functions", "taxonomy", "source_quality", "reference_metadata"):
        assert new[field] == old[field]
    assert new["source_quality"]["assembly_measurements"][0]["measurements"]["completeness_fraction"] == .95


def test_saved_inner_sheet_recalculates_without_native_parsers_population_or_io(monkeypatch):
    saved = json.loads(json.dumps(calculate(sequence_inputs())["components"]["database_sheet"]))
    before = deepcopy(saved)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved numerical calculation must not parse, populate, execute or acquire")
    with monkeypatch.context() as patch:
        for obj, name in ((builtins, "open"), (io, "open"), (socket, "socket"), (socket, "create_connection"),
                (subprocess, "Popen"), (subprocess, "run"), (Path, "read_bytes"), (Path, "read_text"),
                (grader, "build_database_sheet"), (grader, "_build_database_sheet"),
                (sequence, "populate_blast_sequence_database_sheet"), (sequence, "_rows"),
                (collection, "parse_blast_report_collection")):
            patch.setattr(obj, name, forbidden)
        first = grader.calculate_database_probabilities(saved)
        second = grader.calculate_database_probabilities(saved, model={"temperature_bits": 2})
    assert saved == before
    assert first["unadjusted_probabilities"] == {"F": 4/5, "G": 1/5}
    assert first["representation_adjusted_probabilities"] == pytest.approx({"F": 2/7, "G": 5/7})
    assert second["unadjusted_probabilities"] == {"F": 2/3, "G": 1/3}
    assert second["representation_adjusted_probabilities"] == pytest.approx({"F": 1/6, "G": 5/6})


@pytest.mark.parametrize("mutate", [
    lambda s: s["database_population_relation"].update(status="unavailable"),
    lambda s: s["database_population_context"]["associations"][0]["assertion_record"]["value"].update(database_manifest_sha256="9" * 64),
    lambda s: s["database_population_context"]["associations"][0].update(census_record=None),
    lambda s: s["database_representation"]["function_representation"][0].update(database_sequence_count=1),
    lambda s: s["database_representation"]["function_representation"][0].update(database_sequence_count=100.0),
    lambda s: s["database_representation"].update(available_for_adjustment=1),
    lambda s: s["database_profile"]["function_counts"].update(F=1),
    lambda s: s["normalized_result"]["search"]["request"].update(db="third-spelling"),
    lambda s: s["normalized_result"]["source_locator"].pop("source_ref"),
    lambda s: s["database_population_relation"]["association_results"][0].update(reason_codes=["forged"]),
])
def test_saved_forgery_rejected_without_fallback(mutate):
    sheet = calculate(sequence_inputs())["components"]["database_sheet"]
    mutate(sheet)
    with pytest.raises(ValueError, match="^" + PREFIX + "saved_relation_conflict$"):
        grader.calculate_database_probabilities(sheet)


def test_forged_available_relation_does_not_upgrade_unavailable_sheet():
    args = sequence_inputs()
    args["database_population_associations"][0]["assertion_record"] = None
    sheet = calculate(args)["components"]["database_sheet"]
    sheet["database_population_relation"].update(status="available", reason_codes=[])
    sheet["database_representation"].update(available_for_adjustment=True, reasons=[])
    with pytest.raises(ValueError, match=PREFIX + "saved_relation_conflict"):
        grader.calculate_database_probabilities(sheet)


def test_public_builder_requires_explicit_reference_and_calculation_context():
    out = calculate(sequence_inputs())["components"]["database_sheet"]
    args = dict(result=out["normalized_result"], reference_metadata=out["reference_metadata"],
        database_profile=out["database_profile"], description_bindings=out["description_bindings"],
        sequence_identity_bindings=out["sequence_identity_bindings"], calculation_context=out["calculation_context"],
        database_population_context=out["database_population_context"])
    assert grader.build_database_sheet(**args)["database_representation"] == out["database_representation"]
    for missing in (("calculation_context",), ("description_bindings", "sequence_identity_bindings")):
        other = deepcopy(args)
        for key in missing: other[key] = None
        with pytest.raises(ValueError, match=PREFIX + "context_fields_invalid"):
            grader.build_database_sheet(**other)


def test_old_sheet_version_never_discovers_population_keys():
    args = sequence_inputs()
    args["database_population_associations"] = None
    args["report_source"].pop("source_ref")
    sheet = sequence.populate_blast_sequence_database_sheet(**args)
    sheet["database_population_associations"] = []
    with pytest.raises(ValueError, match="blast_sequence_database_sheet_fields_invalid"):
        sequence.calculate_blast_sequence_database_components(sheet)


def test_v3_report_source_identity_is_preserved_and_missing_identity_disables_adjustment():
    args = sequence_inputs()
    database, _ = assert_numbers(calculate(args))
    assert database["normalized_result"]["source_locator"]["source_ref"] == "source:original-report"
    assert database["normalized_result"]["source_locator"]["artifact_ref"] == args["report_source"]["artifact_ref"]
    args["report_source"].pop("source_ref")
    database, _ = assert_numbers(calculate(args), adjusted=False)
    assert database["database_population_relation"]["status"] == "unavailable"
    assert PREFIX + "source_record_unavailable" in database["database_population_relation"]["reason_codes"]


def test_report_source_alias_different_bytes_and_artifact_is_incompatible():
    args = sequence_inputs()
    row = args["database_population_associations"][0]
    row["assertion_source"]["source_ref"] = args["report_source"]["source_ref"]
    row["assertion_record"]["source_ref"] = row["assertion_source"]["source_ref"]
    database, _ = assert_numbers(calculate(args), adjusted=False)
    assert database["database_population_relation"]["status"] == "incompatible"
    assert PREFIX + "report_used_as_population_source" in database["database_population_relation"]["reason_codes"]


@pytest.mark.parametrize("version", [sequence.SHEET_SCHEMA, sequence.SHEET_SCHEMA_V2])
def test_old_declared_versions_keep_exact_four_field_report_source(version):
    args = sequence_inputs()
    args["database_population_associations"] = None
    args["report_source"].pop("source_ref")
    sheet = sequence.populate_blast_sequence_database_sheet(**args)
    sheet["schema"] = version
    sheet["report_source"]["source_ref"] = "source:original-report"
    with pytest.raises(ValueError, match="blast_sequence_database_report_source_fields_invalid"):
        sequence.calculate_blast_sequence_database_components(sheet)
