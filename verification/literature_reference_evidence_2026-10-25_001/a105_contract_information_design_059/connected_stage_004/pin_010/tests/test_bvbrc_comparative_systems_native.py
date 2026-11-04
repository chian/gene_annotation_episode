"""Actual parser tests; retained producer outputs are explicitly synthetic."""
from copy import deepcopy
import csv
import hashlib
import io
import json
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_comparative_systems_handoff_contracts import canonical_sha256, schema, validate_shape
from gene_annotation_episode.bvbrc_comparative_systems_native import parse_comparative_systems_document
from gene_annotation_episode.bvbrc_comparative_systems_sheet_contracts import validate_native_document


FIXTURES = Path(__file__).parent / "fixtures" / "bvbrc_comparative_systems_native"
BUILD_INPUTS = json.loads((FIXTURES / "build_inputs.json").read_text())
EVIDENCE = BUILD_INPUTS["families_sheet"]["producer_evidence"]


def artifact(case, suffix):
    return (FIXTURES / "source_executed_synthetic" / case / (case + suffix)).read_bytes()


def parse(content, profile="families_json_v1", *, known=True, document_id="document", **overrides):
    document = {"document_id": document_id, "role": "native_document", "format_profile": "comparative_systems_" + profile,
                "source_ref": "source:" + document_id, "raw_artifact_ref": "bytes:" + document_id,
                "byte_count": len(content), "sha256": hashlib.sha256(content).hexdigest(),
                "transfer_body_complete": "complete", "object_complete": "complete", "original_task_ref": "synthetic-task",
                "producer_evidence_id": "source670b" if known else None, "basis": "source_executed_synthetic"}
    document.update(overrides)
    return parse_comparative_systems_document(content, document=document, format_profile=document["format_profile"], producer_evidence=tuple(EVIDENCE))


def numbers(native, table="plfam", row=0):
    return {n["native_field"]: n for n in next(t for t in native["tables"] if t["table"] == table)["rows"][row]["numeric_fields"]
            if n["native_field"] != "genomes"}


def hex_cells(native, table="plfam"):
    return [n["cell"] for n in next(t for t in native["tables"] if t["table"] == table)["rows"][0]["numeric_fields"] if n["native_field"] == "genomes"]


def family_modified(change):
    value = json.loads(artifact("families", "_proteinfams_tables.json"))
    change(value)
    return json.dumps(value, ensure_ascii=False).encode()


def test_shared_asset_is_reviewed_and_detached():
    import gene_annotation_episode.bvbrc_comparative_systems_handoff_contracts as contracts
    path = Path(contracts.__file__).with_name("bvbrc_comparative_systems_handoff_schemas.json")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "b1310c2f3c7a464191f8c9eb5918d516ed2e6dd13f49bec024a2e9a8bde159f8"
    s = schema("SourceDocumentV1")
    s["$defs"].clear()
    assert schema("SourceDocumentV1")["$defs"]
    source = parse(artifact("families", "_proteinfams_tables.json"))["document"]
    copy = validate_shape("SourceDocumentV1", source)
    copy["document_id"] = "changed"
    assert source["document_id"] == "document"
    for bad in (True, float(source["byte_count"])):
        with pytest.raises(ValueError, match="comparative_systems_shape_invalid"):
            validate_shape("SourceDocumentV1", {**source, "byte_count": bad})
    with pytest.raises(ValueError):
        validate_shape("SourceDocumentV1", {**source, "unknown": None})
    value = {"z": [1, 0.5, False], "é": "λ"}
    expected = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    assert canonical_sha256(value) == expected


@pytest.mark.parametrize("bad", [float("nan"), {"a": float("inf")}, {1: "x"}, (1,), {1, 2}])
def test_non_json_values_rejected(bad):
    with pytest.raises(ValueError, match="comparative_systems_"):
        canonical_sha256(bad)


@pytest.mark.parametrize("case,suffix,profile,table,rows", [
    ("families", "_proteinfams_tables.json", "families_json_v1", "plfam", 1),
    ("discard_and_dependence", "_pathways_tables.json", "pathways_json_v1", "pathway", 1),
    ("discard_and_dependence", "_subsystems_tables.json", "subsystems_json_v1", "subsystems", 1),
    ("discard_and_dependence", "_pathways.tsv", "pathways_tsv_v1", "pathways_tsv", 5),
    ("discard_and_dependence", "_subsystems.tsv", "subsystems_tsv_v1", "subsystems_tsv", 5),
    ("discard_and_dependence", "_subsystems_variant_mtx.tsv", "variant_matrix_source670b_v1", "variant_matrix", 1),
    ("one_json_record", "_pathways_tables.json", "pathways_json_v1", "pathway", 0),
    ("one_json_record", "_subsystems_tables.json", "subsystems_json_v1", "subsystems", 0),
    ("two_chunks", "_pathways.tsv", "pathways_tsv_v1", "pathways_tsv", 19),
    ("two_chunks", "_subsystems.tsv", "subsystems_tsv_v1", "subsystems_tsv", 19),
])
def test_six_profiles_read_actual_source_outputs(case, suffix, profile, table, rows):
    content = artifact(case, suffix)
    native = parse(content, profile)
    assert len(next(t for t in native["tables"] if t["table"] == table)["rows"]) == rows
    assert native["document"]["sha256"] == hashlib.sha256(content).hexdigest()
    assert validate_native_document(native) == native


def test_reported_native_values_and_exact_locations():
    native = parse(artifact("discard_and_dependence", "_pathways_tables.json"), "pathways_json_v1")
    n = numbers(native, "pathway")["ec_conservation"]
    assert n["raw_lexeme"] == "75.0"
    assert n["cell"]["value"] == 75.0
    assert n["location"] == {"source_ref": "source:document", "raw_artifact_ref": "bytes:document", "document_id": "document",
                             "json_pointer": "/pathway", "table": "pathway", "row_ordinal": 0, "column_ordinal": 8,
                             "native_field": "ec_conservation"}
    assert numbers(native, "pathway")["gene_count"]["cell"]["value"] == 4
    assert numbers(native, "pathway")["genome_ec"]["cell"]["value"] == 3


def test_source_version_is_not_inferred_from_parser_profile():
    content = artifact("discard_and_dependence", "_pathways_tables.json")
    known, unknown = parse(content, "pathways_json_v1"), parse(content, "pathways_json_v1", known=False)
    assert "native_first_object_discard" in {d["code"] for d in known["diagnostics"]}
    assert "native_first_object_discard" not in {d["code"] for d in unknown["diagnostics"]}
    assert "producer_version_unverified" in {d["code"] for d in unknown["diagnostics"]}
    assert numbers(known, "pathway")["ec_conservation"]["cell"]["value"] == numbers(unknown, "pathway")["ec_conservation"]["cell"]["value"]
    evidence = deepcopy(EVIDENCE)
    evidence[0]["identity_kind"] = "source_examined"
    document = known["document"]
    inspected_only = parse_comparative_systems_document(content, document=document, format_profile=document["format_profile"], producer_evidence=tuple(evidence))
    assert "native_first_object_discard" not in {d["code"] for d in inspected_only["diagnostics"]}


@pytest.mark.parametrize("case,expected,aggregate", [("hex_255", [255, 1], 256), ("hex_256", [None, None], 257)])
def test_hex_255_and_256_native_witnesses(case, expected, aggregate):
    native = parse(artifact(case, "_proteinfams_tables.json"))
    assert [c["value"] for c in hex_cells(native)] == expected
    assert numbers(native)["feature_count"]["cell"]["value"] == aggregate
    if case == "hex_256":
        assert all(c["state"] == "incompatible" for c in hex_cells(native))
        assert next(t for t in native["tables"] if t["table"] == "plfam")["rows"][0]["tokens"][-1] == "10001"


@pytest.mark.parametrize("replacement", ["02010g", "010100", "10001"])
def test_hex_never_guesses_split_or_repairs_inconsistent_counts(replacement):
    content = family_modified(lambda v: v.update(plfam=v["plfam"].replace("020100", replacement)))
    native = parse(content)
    assert all(c["state"] == "incompatible" for c in hex_cells(native))
    assert numbers(native)["feature_count"]["cell"]["value"] == 3
    assert numbers(native)["aa_length_mean"]["cell"]["value"] == 200
    assert [c["value"] for c in hex_cells(native, "pgfam")] == [2, 1, 0]


def test_hex_order_is_exact_and_display_names_do_not_join_genomes():
    content = family_modified(lambda v: v.update(genome_ids=["2.1", "1.1", "3.1"], genome_names=["same", "same", "other"]))
    native = parse(content)
    assert [c["value"] for c in hex_cells(native)] == [2, 1, 0]
    assert "genome_name_collision" in {d["code"] for d in native["diagnostics"]}
    assert native["metadata"][0]["value"] == ["2.1", "1.1", "3.1"]


@pytest.mark.parametrize("content,code", [(b'{"plfam":"","plfam":"x"}', "duplicate_json_key"),
    (b'{"x": NaN}', "nonfinite_number"), (b'{"x": 1e999}', "nonfinite_number"),
    (b'{"plfam":', "outer_json_invalid"), (b'\xff', "outer_json_invalid"), (b'[]', "format_incompatible")])
def test_invalid_outer_document_is_not_prefix_salvaged(content, code):
    native = parse(content)
    assert native["status"] == "invalid"
    assert not native["tables"]
    assert code in {d["code"] for d in native["diagnostics"]}


def test_wrong_profile_and_byte_identity_are_not_accepted():
    content = artifact("families", "_proteinfams_tables.json")
    native = parse(content, "pathways_json_v1")
    assert native["status"] == "invalid"
    bad = parse(content, sha256="0" * 64)
    assert bad["status"] == "invalid" and bad["diagnostics"][0]["code"] == "byte_identity_mismatch"
    with pytest.raises(ValueError, match="format_profile_mismatch"):
        parse_comparative_systems_document(content, document=parse(content)["document"],
                                           format_profile="comparative_systems_pathways_json_v1", producer_evidence=tuple(EVIDENCE))


def test_manual_tabs_do_not_use_pandas_quoting_and_later_rows_survive():
    value = json.loads(artifact("families", "_proteinfams_tables.json"))
    header, row = value["plfam"].splitlines()
    tokens = row.split("\t")
    tokens[3] = '"product\twith tab"'
    value["plfam"] = header + "\n" + "\t".join(tokens) + "\n" + row
    native = parse(json.dumps(value).encode())
    rows = native["tables"][0]["rows"]
    assert rows[0]["status"] == "invalid" and len(rows[0]["tokens"]) == 10
    assert rows[1]["status"] == "ok"
    assert numbers(native, row=1)["feature_count"]["cell"]["value"] == 3
    assert native["tables"][0]["raw_text"] == value["plfam"]


def test_pandas_tabs_quotes_and_multiline_fields_are_preserved():
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
    writer.writerow(["id", "genome_id", "feature_id", "pathway_id", "ec_number", "product"])
    writer.writerow(["record", "292462.10", "feature", "pathway", "1.2.3.4", 'one\ttwo\n"three"'])
    native = parse(stream.getvalue().encode(), "pathways_tsv_v1")
    row = native["tables"][0]["rows"][0]
    assert row["tokens"][-1] == 'one\ttwo\n"three"'
    assert row["tokens"][1] == "292462.10"
    assert len(native["tables"][0]["rows"]) == 1
    assert native["tables"][0]["raw_text"] == stream.getvalue()


@pytest.mark.parametrize("token", ["nan", "-1", "inf", "True", "1_0", " 200.0", "200.0 "])
def test_invalid_length_tokens_keep_lexemes(token):
    content = family_modified(lambda v: v.update(plfam=v["plfam"].replace("\t200.0\t", "\t" + token + "\t")))
    native = parse(content)
    number = numbers(native)["aa_length_mean"]
    assert number["raw_lexeme"] == token and number["cell"]["state"] == "invalid" and number["cell"]["value"] is None
    assert numbers(native)["feature_count"]["cell"]["value"] == 3


def test_missing_zero_and_truncated_are_distinct():
    value = json.loads(artifact("families", "_proteinfams_tables.json"))
    header, row = value["plfam"].splitlines()
    tokens = row.split("\t")
    tokens[6], tokens[7] = "", "0"
    value["plfam"] = header + "\n" + "\t".join(tokens)
    native = parse(json.dumps(value).encode(), object_complete="partial")
    assert numbers(native)["aa_length_mean"]["cell"]["state"] == "missing"
    assert numbers(native)["aa_length_std"]["cell"]["value"] == 0
    assert "artifact_truncated" in {d["code"] for d in native["diagnostics"]}
    value["plfam"] = header
    assert parse(json.dumps(value).encode())["tables"][0]["rows"] == []


def test_variant_matrix_retains_both_headers_extra_column_and_unknown_producer():
    content = artifact("discard_and_dependence", "_subsystems_variant_mtx.tsv")
    native = parse(content, "variant_matrix_source670b_v1")
    table = native["tables"][0]
    assert len(table["headers"]) == 2 and len(table["headers"][1]) == 9 and len(table["rows"][0]["tokens"]) == 10
    assert table["raw_text"].encode() == content
    assert {n["native_field"]: n["cell"]["value"] for n in table["rows"][0]["numeric_fields"]} == {"active": 3, "likely": 2, "inactive": 0, "missing_genomes": 0}
    unknown = parse(content, "variant_matrix_source670b_v1", known=False)
    assert all(n["cell"]["state"] == "incompatible" for n in unknown["tables"][0]["rows"][0]["numeric_fields"])


def test_native_saved_lexeme_relationship_validation():
    native = parse(artifact("families", "_proteinfams_tables.json"))
    native["tables"][0]["rows"][0]["numeric_fields"][0]["raw_lexeme"] = "999"
    with pytest.raises(ValueError, match="native_number_lexeme_mismatch"):
        validate_native_document(native)


def test_source_executed_non_cds_repeated_features_and_omissions_are_occurrences():
    native = parse(artifact("occurrence_omissions", "_proteinfams_tables.json"))
    values = numbers(native)
    assert values["feature_count"]["cell"]["value"] == 3
    assert values["genome_count"]["cell"]["value"] == 2
    assert values["aa_length_mean"]["cell"]["value"] == pytest.approx(500 / 3)
    assert [cell["value"] for cell in hex_cells(native)] == [2, 1, 0]
    assert native["tables"][0]["rows"][0]["tokens"][3] == "NOTHING"
    metadata = {item["location"]["json_pointer"]: item["value"] for item in native["metadata"]}
    assert metadata["/genome_ids"] == ["292462.10", "2.1", "3.1"]
    source = json.loads((FIXTURES / "source_executed_synthetic/occurrence_omissions/inputs.json").read_text())
    assert source["features"][0]["feature_type"] == source["features"][1]["feature_type"] == "rRNA"
    assert source["features"][0]["feature_id"] == source["features"][1]["feature_id"]
    assert source["features"][3]["aa_length"] == ""
    assert source["extra_short_row"] == "too\tshort"
    assert source["features"][4]["plfam_id"] == ""


def test_duplicate_genome_ids_disable_hex_identity_but_retain_each_ordinal():
    content = family_modified(lambda v: v.update(genome_ids=["1.1", "1.1", "3.1"]))
    native = parse(content)
    assert len(hex_cells(native)) == 3
    assert all(cell["state"] == "incompatible" for cell in hex_cells(native))
    assert numbers(native)["feature_count"]["cell"]["value"] == 3


def test_unpaired_unicode_surrogate_is_an_invalid_document():
    native = parse(b'{"x":"\\ud800"}')
    assert native["status"] == "invalid"
    assert "outer_json_invalid" in {d["code"] for d in native["diagnostics"]}


def test_overview_json_lexemes_and_boolean_counts():
    content = artifact("discard_and_dependence", "_subsystems_tables.json")
    value = json.loads(content)
    value["overview"] = {"S": {"subsystem_name_counts": True, "gene_counts": 1,
                              "C": {"subsystem_name_counts": 1, "gene_counts": 1,
                                    "D": {"subsystem_name_counts": 1, "gene_counts": 1}}}}
    native = parse(json.dumps(value).encode(), "subsystems_json_v1")
    number = next(n for n in native["reported_numbers"] if n["location"]["json_pointer"] == "/overview/S/subsystem_name_counts")
    assert number["raw_lexeme"] == "True" and number["cell"]["state"] == "invalid"
    assert numbers(native, "subsystems")["role_conservation"]["cell"]["value"] == 75


def test_arbitrary_metadata_that_resembles_internal_contract_is_retained_as_data():
    embedded = {"state": "available", "value": -7, "unit": "genome", "origin": "native-text",
                "population_id": None, "method_id": "unknown", "input_refs": [], "uncertainty": None, "qualification_codes": []}
    native = parse(family_modified(lambda v: v.update(extra_metadata=embedded)))
    assert next(m for m in native["metadata"] if m["location"]["json_pointer"] == "/extra_metadata")["value"] == embedded
    assert validate_native_document(native) == native


def test_pandas_unclosed_quote_retains_previous_valid_row_and_raw_remainder():
    content = b'id\tgenome_id\tfeature_id\tpathway_id\tec_number\nfirst\t1.1\tf1\tP\t1.1.1.1\n"unclosed\t2.1\nfurther bytes'
    native = parse(content, "pathways_tsv_v1")
    assert native["tables"][0]["raw_text"].encode() == content
    rows = native["tables"][0]["rows"]
    assert rows[0]["status"] == "ok" and rows[1]["status"] == "invalid"
    assert rows[1]["tokens"] == ['"unclosed\t2.1\nfurther bytes']


def test_duplicate_headers_cannot_supply_valid_shifted_numbers():
    content = family_modified(lambda v: v.update(plfam=v["plfam"].replace("family_id\tfeature_count", "feature_count\tfeature_count")))
    native = parse(content)
    assert native["tables"][0]["rows"][0]["status"] == "invalid"
    assert all(n["cell"]["state"] != "available" for n in native["tables"][0]["rows"][0]["numeric_fields"])
    assert numbers(native, "pgfam")["feature_count"]["cell"]["value"] == 3


def test_saved_native_unit_meaning_is_validated_without_parser():
    native = parse(artifact("families", "_proteinfams_tables.json"))
    for number in native["tables"][0]["rows"][0]["numeric_fields"] + native["reported_numbers"]:
        if number["native_field"] == "feature_count" and number["location"]["table"] == "plfam":
            number["cell"]["unit"] = "genome"
    with pytest.raises(ValueError, match="native_number_unit_mismatch"):
        validate_native_document(native)
