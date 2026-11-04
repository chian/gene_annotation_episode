"""Numerical sheets built through the actual native readers and exact inputs."""
from copy import deepcopy
import hashlib
import json
import math

import pytest

from gene_annotation_episode.bvbrc_comparative_systems_native import parse_comparative_systems_document
from gene_annotation_episode.bvbrc_comparative_systems_sheet import build_comparative_systems_sheet
from gene_annotation_episode.bvbrc_comparative_systems_sheet_contracts import validate_sheet
from test_bvbrc_comparative_systems_native import BUILD_INPUTS, FIXTURES, artifact


def inputs(name="pathway_subsystem_sheet"):
    options = deepcopy(BUILD_INPUTS[name])
    source_documents = options.pop("source_documents")
    files = {hashlib.sha256(p.read_bytes()).hexdigest(): p for p in (FIXTURES / "source_executed_synthetic").rglob("*") if p.is_file()}
    contents = {document["document_id"]: files[document["sha256"]].read_bytes() for document in source_documents}
    return options, source_documents, contents


def build(options, sources, contents, *, omit=()):
    parsed = []
    for original in sources:
        if original["document_id"] in omit:
            continue
        document = deepcopy(original)
        content = contents[document["document_id"]]
        document.update(byte_count=len(content), sha256=hashlib.sha256(content).hexdigest())
        parsed.append(parse_comparative_systems_document(content, document=document, format_profile=document["format_profile"],
                                                       producer_evidence=tuple(options["producer_evidence"])))
    return build_comparative_systems_sheet(tuple(parsed), **options)


def sheet(name="pathway_subsystem_sheet"):
    return build(*inputs(name))


def pop(value, population_id):
    return next(p for p in value["populations"] if p["population_id"] == population_id)


def modify_table(content, table, mutate):
    value = json.loads(content)
    rows = [line.split("\t") for line in value[table].splitlines()]
    mutate(rows)
    value[table] = "\n".join("\t".join(row) for row in rows)
    return json.dumps(value).encode()


def test_family_native_numbers_populations_and_zero_remain_separate():
    value = sheet("families_sheet")
    assert len(value["family_rows"]) == 2
    for row in value["family_rows"]:
        assert row["reported_feature_occurrences"]["value"] == 3
        assert row["reported_genome_count"]["value"] == 2
        assert row["reported_length_min"]["value"] == 100
        assert row["reported_length_max"]["value"] == 300
        assert row["reported_length_mean"]["value"] == 200
        assert row["reported_length_population_sd"]["value"] == pytest.approx(math.sqrt((100**2 + 0 + 100**2) / 3))
        assert row["reported_length_mean"]["uncertainty"] is None
        assert row["positive_genome_count_from_list"]["value"] == 2
        assert [count["reported_occurrences"]["value"] for count in row["genome_counts"]] == [2, 1, 0]
        assert row["genome_counts"][2]["presence_state"] == "no_record_completeness_unknown"
    assert pop(value, "families_native_genomes")["members"] == ["1.1", "2.1", "3.1"]
    assert value["family_rows"][0]["entity"]["family_kind"] == "plfam"
    assert value["family_rows"][1]["entity"]["family_kind"] == "pgfam"
    # Native family summaries contain no feature IDs or individual lengths.
    assert not value["association_rows"]


@pytest.mark.parametrize("table_name", ["plfam", "pgfam"])
@pytest.mark.parametrize("shape", ["identity_only", "missing_hex", "extra_column", "blank_hex"])
def test_malformed_family_row_keeps_exact_hex_lexeme_and_valid_siblings(table_name, shape):
    options, sources, contents = inputs("families_sheet")
    original = build(options, sources, contents)
    document_id = sources[0]["document_id"]
    added_tokens = []

    def append_malformed(rows):
        tokens = list(rows[1])
        column = rows[0].index("genomes")
        tokens[rows[0].index("family_id")] = "malformed-family"
        if shape == "identity_only":
            tokens = tokens[:1]
        elif shape == "missing_hex":
            tokens = tokens[:column]
        elif shape == "extra_column":
            tokens.append("unassigned-column")
        else:
            tokens[column] = ""
        added_tokens.extend(tokens)
        rows.append(tokens)

    contents[document_id] = modify_table(contents[document_id], table_name, append_malformed)
    value = build(options, sources, contents)
    assert validate_sheet(value) == value
    native = next(n for n in value["native_documents"] if n["document"]["document_id"] == document_id)
    table = next(t for t in native["tables"] if t["table"] == table_name)
    row = table["rows"][1]
    assert row["tokens"] == added_tokens
    assert row["status"] == ("partial" if shape == "blank_hex" else "invalid")
    column = table["headers"][0].index("genomes")
    expected_lexeme = added_tokens[column] if column < len(added_tokens) else None
    numbers = [n for n in row["numeric_fields"] if n["native_field"] == "genomes"]
    assert len(numbers) == 3
    assert all(n["raw_lexeme"] == expected_lexeme for n in numbers)
    assert all(n["location"]["column_ordinal"] == column for n in numbers)
    assert all(n["cell"]["state"] == "incompatible" and n["cell"]["value"] is None for n in numbers)
    # Both families retain their independently reported 200-aa mean and 2/1/0
    # occurrence vector. A malformed neighbor does not discard these facts.
    retained = [r for r in value["family_rows"] if r["native_row_ordinal"] == 0]
    assert retained == original["family_rows"]
    malformed = next(r for r in value["family_rows"]
                     if r["entity"]["family_kind"] == table_name and r["native_row_ordinal"] == 1)
    assert all(c["reported_occurrences"]["state"] == "incompatible"
               and c["reported_occurrences"]["value"] is None for c in malformed["genome_counts"])


def test_pathway_native75_and_supplied_later_population_are_both_preserved():
    value = sheet()
    row = value["pathway_rows"][0]
    assert row["reported_ec_conservation_percent"]["value"] == 75
    assert row["reported_ec_token_count"]["value"] == 2
    assert row["reported_feature_token_count"]["value"] == 4
    assert row["reported_genome_ec_count"]["value"] == 3
    assert row["reported_gene_conservation"]["value"] == 1
    assert row["reported_ec_conservation_percent"]["population_id"] == "pathway_native_genomes"
    assert pop(value, "pathway_native_genomes")["distinct_valid_member_count"]["value"] == 2
    assert pop(value, "later_pathway_genomes")["distinct_valid_member_count"]["value"] == 3
    assert pop(value, "pathway_native_ecs")["raw_occurrence_count"]["value"] == 5
    assert pop(value, "pathway_native_ecs")["distinct_valid_member_count"]["value"] == 2
    assert len([r for r in value["association_rows"] if r["document_id"] == "pathway_raw"]) == 5
    assert len([r for r in value["association_rows"] if r["document_id"] == "pathways" and r["table"] == "genes"]) == 5
    supplied = value["supplied_record_sets"]["record_sets"][0]
    tuples = {(r["association"]["identifiers"]["genome_id"], r["association"]["identifiers"]["ec_number"])
              for r in supplied["rows"]}
    assert len(tuples) == 4  # Independent input facts for C's 4/(3*3)*100 calculation.
    assert len({ec for _, ec in tuples}) == 3
    assert supplied == BUILD_INPUTS["pathway_subsystem_sheet"]["supplied_record_sets"]["record_sets"][0]


def test_literal_subsystem_case_and_variant_unknown_id():
    value = sheet()
    assert value["subsystem_rows"][0]["entity"]["superclass_native"] == "SYNTHETIC"
    raw = next(r for r in value["association_rows"] if r["document_id"] == "subsystem_raw")
    assert next(f for f in raw["fields"] if f["name"] == "superclass")["raw_text"] == "synthetic"
    variant = value["variant_rows"][0]
    assert variant["entity"]["subsystem_id"] is None
    assert variant["entity"]["kind"] == "variant"
    assert variant["reported_active_occurrences"]["value"] == 3
    assert variant["reported_likely_occurrences"]["value"] == 2
    assert variant["reported_inactive_placeholder"]["value"] == 0
    assert variant["reported_missing_genome_count"]["value"] == 0
    assert "native_category_imputed" in variant["reported_missing_genome_count"]["qualification_codes"]
    assert (variant["header_field_count"], variant["data_field_count"]) == (9, 10)
    raw_rows = [r for r in value["association_rows"] if r["document_id"] == "subsystem_raw"]
    categories = {}
    for row in raw_rows:
        categories.setdefault(row["identifiers"]["genome_id"], set()).add(row["active_category"])
    assert categories == {"1.1": {"active", "likely"}, "2.1": {"likely"}}
    assert sum(states == {"active"} for states in categories.values()) == 0
    assert sum(states == {"likely"} for states in categories.values()) == 1
    assert value["subsystem_rows"][0]["reported_record_genome_fraction"]["value"] == 1


def test_overflow_aggregate_list_and_dispersion_survive():
    value = sheet("hex_256_sheet")
    row = value["family_rows"][0]
    assert row["raw_hex_counts"] == "10001"
    assert row["reported_feature_occurrences"]["value"] == 257
    assert row["reported_genome_count"]["value"] == row["positive_genome_count_from_list"]["value"] == 2
    assert row["reported_length_mean"]["state"] == "available"
    assert [g["reported_occurrences"]["state"] for g in row["genome_counts"]] == ["incompatible", "incompatible"]


def test_builder_is_detached_and_uses_exact_assigned_ids():
    options, sources, contents = inputs("families_sheet")
    options["population_assignments"]["assignments"][1]["population_id"] = "chosen-before-acquisition"
    before = deepcopy((options, sources, contents))
    value = build(options, sources, contents)
    assert (options, sources, contents) == before
    assert {p["population_id"] for p in value["populations"]} == {"families_requested", "chosen-before-acquisition"}
    assert value["family_rows"][0]["reported_feature_occurrences"]["population_id"] == "chosen-before-acquisition"
    detached = validate_sheet(value)
    detached["family_rows"][0]["reported_feature_occurrences"]["value"] = 9
    assert value["family_rows"][0]["reported_feature_occurrences"]["value"] == 3


def test_unknown_original_groups_and_executed_population_are_not_reconstructed():
    options, sources, contents = inputs("families_sheet")
    original = options["original_request"]
    original.update(genome_ids=["292462.10", "292462.10"], genome_groups=["/folder/same-name"],
                    executed_genome_ids=None, executed_population_evidence=[])
    options["population_assignments"]["assignments"].append({"population_id": "executed", "kind": "executed_genomes",
                                                            "view_id": None, "entity": None, "component_kind": None})
    value = build(options, sources, contents)
    requested = pop(value, "families_requested")
    assert requested["members"] == ["292462.10"]
    assert requested["raw_occurrence_count"]["value"] == 2 and requested["distinct_valid_member_count"]["value"] == 1
    assert "group_membership_unknown" in requested["qualification_codes"]
    assert pop(value, "executed")["distinct_valid_member_count"]["state"] == "missing"
    assert pop(value, "executed")["members"] == []


@pytest.mark.parametrize("mutation,code", [
    (lambda o, s: o["population_assignments"]["assignments"].append(deepcopy(o["population_assignments"]["assignments"][0])), "duplicate_selection_id"),
    (lambda o, s: o["population_assignments"]["assignments"][1].update(view_id="absent"), "population_assignment_selector_invalid"),
    (lambda o, s: o["population_assignments"]["assignments"][0].update(view_id="plfam"), "population_assignment_selector_invalid"),
    (lambda o, s: s[0].update(original_task_ref="wrong-task"), "original_task_mismatch"),
    (lambda o, s: o["document_selection"]["documents"][0].update(producer_evidence_id=None), "document_selection_mismatch"),
])
def test_explicit_selection_and_binding_failures(mutation, code):
    options, sources, contents = inputs("families_sheet")
    mutation(options, sources)
    with pytest.raises(ValueError, match=code):
        build(options, sources, contents)


def test_population_collision_with_supplied_snapshot_is_rejected():
    options, sources, contents = inputs()
    options["population_assignments"]["assignments"][0]["population_id"] = "later_pathway_genomes"
    with pytest.raises(ValueError, match="population_id_collision"):
        build(options, sources, contents)


def test_missing_and_invalid_documents_preserve_valid_siblings_and_assigned_population():
    options, sources, contents = inputs()
    contents["pathways"] = b'{"pathway":'
    invalid = build(options, sources, contents)
    assert not invalid["pathway_rows"]
    assert invalid["subsystem_rows"][0]["reported_role_conservation_percent"]["value"] == 75
    assert pop(invalid, "pathway_native_genomes")["distinct_valid_member_count"]["state"] == "missing"
    missing = build(options, sources, contents, omit=("pathways",))
    assert any(r["document_id"] == "pathways" for r in missing["requirements"])
    assert pop(missing, "pathway_native_genomes")["population_id"] == "pathway_native_genomes"
    assert missing["subsystem_rows"] == invalid["subsystem_rows"]


def test_blank_ids_and_malformed_rows_keep_raw_fields_without_clean_population_claim():
    options, sources, contents = inputs()
    text = contents["pathway_raw"].decode().splitlines()
    header = text[0].split("\t")
    first = text[1].split("\t")
    first[header.index("ec_number")] = " "
    text[1] = "\t".join(first)
    text.insert(2, "malformed\trow")
    contents["pathway_raw"] = "\n".join(text).encode()
    value = build(options, sources, contents)
    rows = [r for r in value["association_rows"] if r["document_id"] == "pathway_raw"]
    assert len(rows) == 6 and rows[0]["identifiers"]["ec_number"] is None
    assert next(f for f in rows[0]["fields"] if f["name"] == "ec_number")["raw_text"] == " "
    assert rows[1]["identity_status"] == "partial"
    assert all(v is None for v in rows[1]["identifiers"].values())
    assert rows[-1]["identifiers"]["feature_id"] == "f4"
    assert pop(value, "pathway_native_ecs")["completeness"] == "partial"
    assert value["pathway_rows"][0]["reported_ec_conservation_percent"]["value"] == 75


def test_duplicate_conflict_retains_each_occurrence_and_invalidates_affected_population():
    options, sources, contents = inputs()
    rows = [line.split("\t") for line in contents["pathway_raw"].decode().splitlines()]
    rows[-1][rows[0].index("feature_id")] = "conflicting-feature"
    contents["pathway_raw"] = "\n".join("\t".join(r) for r in rows).encode()
    value = build(options, sources, contents)
    conflicts = [r for r in value["association_rows"] if r["document_id"] == "pathway_raw" and r["identity_status"] == "conflicting"]
    assert len(conflicts) == 2
    assert {r["identifiers"]["feature_id"] for r in conflicts} == {"f4", "conflicting-feature"}
    assert pop(value, "pathway_native_ecs")["completeness"] == "incompatible"
    assert pop(value, "subsystem_native_roles")["completeness"] == "complete_for_declared_population"
    assert any(g["kind"] == "conflicting_record" for g in value["duplicate_groups"])


def test_subsystem_name_id_collisions_are_explicit():
    options, sources, contents = inputs()
    rows = [line.split("\t") for line in contents["subsystem_raw"].decode().splitlines()]
    rows[1][rows[0].index("subsystem_id")] = "DIFFERENT_ID"
    contents["subsystem_raw"] = "\n".join("\t".join(r) for r in rows).encode()
    value = build(options, sources, contents)
    rows = [r for r in value["association_rows"] if r["document_id"] == "subsystem_raw"]
    assert all(r["identity_status"] == "conflicting" and "identity_conflict" in r["qualification_codes"] for r in rows)
    assert value["subsystem_rows"][0]["entity"]["subsystem_id"] == "S_TEST"
    assert "identity_conflict" in value["subsystem_rows"][0]["qualification_codes"]
    assert value["subsystem_rows"][0]["reported_role_conservation_percent"]["value"] == 75


def test_explicit_raw_and_joined_views_preserve_inner_join_missing_and_multiplicity():
    options, sources, contents = inputs()
    selection = options["document_selection"]
    selection["authoritative_views"].append({"view_id": "pathway_genes", "document_id": "pathways", "table": "genes"})
    selection["dependent_views"].append({"left_view_id": "pathway_raw", "right_view_id": "pathway_genes"})
    contents["pathways"] = modify_table(contents["pathways"], "genes", lambda rows: rows.pop(2))
    value = build(options, sources, contents)
    join = value["join_results"][0]
    assert join["keys"] == ["genome_id", "patric_id"]
    assert join["left_occurrence_count"]["value"] == 5 and join["right_occurrence_count"]["value"] == 4
    assert join["multiplicity"] == "many_to_many"
    assert len(join["unmatched_left_refs"]) == 1
    assert set(join["qualification_codes"]) == {"inner_join_missing", "inner_join_many_to_many"}
    assert value["pathway_rows"][0]["reported_feature_token_count"]["value"] == 4


def test_overview_parent_counts_remain_native_sums():
    options, sources, contents = inputs()
    source = json.loads(contents["subsystems"])
    source["overview"] = {"SHARED": {"subsystem_name_counts": 2, "gene_counts": 2,
        "Class": {"subsystem_name_counts": 2, "gene_counts": 2,
                  "Subclass A": {"subsystem_name_counts": 1, "gene_counts": 1},
                  "Subclass B": {"subsystem_name_counts": 1, "gene_counts": 1}}}}
    contents["subsystems"] = json.dumps(source).encode()
    value = build(options, sources, contents)
    assert [(r["level"], r["reported_feature_count"]["value"]) for r in value["overview_rows"]] == [
        ("superclass", 2), ("class", 2), ("subclass", 1), ("subclass", 1)]
    assert all(r["reported_feature_count"]["origin"] == "program_reported_derived" for r in value["overview_rows"])


def test_same_bytes_at_distinct_sources_are_dependent_representations():
    options, sources, contents = inputs("families_sheet")
    source = deepcopy(sources[0])
    source.update(document_id="copy", source_ref="another-source", raw_artifact_ref="another-artifact")
    sources.append(source)
    contents["copy"] = contents["families_document"]
    selected = deepcopy(options["document_selection"]["documents"][0])
    selected.update(document_id="copy", input={"kind": "possessed_artifact", "source_ref": "another-source", "raw_artifact_ref": "another-artifact"})
    options["document_selection"]["documents"].append(selected)
    value = build(options, sources, contents)
    assert len(value["family_rows"]) == 4
    assert any(g["kind"] == "dependent_view" and {m["owner_id"] for m in g["members"]} == {"families_document", "copy"} for g in value["duplicate_groups"])


@pytest.mark.parametrize("mutation,code", [
    (lambda s: s["family_rows"][0]["reported_feature_occurrences"].update(value=999), "measurement_native_value_mismatch"),
    (lambda s: s["family_rows"][0]["reported_feature_occurrences"].update(population_id="not-present"), "measurement_population_mismatch"),
    (lambda s: s["family_rows"][0]["reported_feature_occurrences"].update(population_id="families_requested"), "measurement_population_mismatch"),
    (lambda s: s["family_rows"][0]["entity"].update(family_id="not-the-original-family"), "measurement_entity_mismatch"),
    (lambda s: s["populations"][0]["distinct_valid_member_count"].update(value=99), "population_membership_count_mismatch"),
    (lambda s: s["source_documents"][0].update(source_ref="other"), "source_document_projection_mismatch"),
    (lambda s: s["family_rows"][0]["genome_counts"][0]["reported_occurrences"].update(value=3), "family_decoded_count_mismatch"),
])
def test_saved_sheet_tampering_rejected_without_reparsing(mutation, code, monkeypatch):
    value = sheet("families_sheet")
    monkeypatch.setattr("gene_annotation_episode.bvbrc_comparative_systems_native.parse_comparative_systems_document",
                        lambda *a, **k: pytest.fail("saved validation parsed again"))
    mutation(value)
    with pytest.raises(ValueError, match=code):
        validate_sheet(value)


def test_no_acquisition_process_or_model_is_needed(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("pure reader/builder attempted external work")
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    value = sheet()
    assert value["pathway_rows"][0]["reported_ec_conservation_percent"]["value"] == 75
    assert validate_sheet(value) == value


def test_source_failure_without_artifact_is_not_zero_family_measurement():
    failure = json.loads((FIXTURES / "source_executed_synthetic/empty_family_rows/producer_return.json").read_text())
    assert failure["families"]["exception"] == "ValueError"
    options, sources, contents = inputs("families_sheet")
    value = build(options, sources, contents, omit=("families_document",))
    assert value["family_rows"] == []
    assert pop(value, "families_native_genomes")["raw_occurrence_count"]["state"] == "missing"
    assert pop(value, "families_native_genomes")["raw_occurrence_count"]["value"] is None
    assert value["requirements"][0]["code"] == "missing_document_selection"


def test_density_above_one_and_native_zero_are_not_clamped():
    options, sources, contents = inputs()
    def alter(rows):
        rows[1][rows[0].index("gene_conservation")] = "3.5"
        rows[1][rows[0].index("ec_conservation")] = "0"
    contents["pathways"] = modify_table(contents["pathways"], "pathway", alter)
    value = build(options, sources, contents)
    assert value["pathway_rows"][0]["reported_gene_conservation"]["value"] == 3.5
    assert value["pathway_rows"][0]["reported_ec_conservation_percent"]["value"] == 0


def test_duplicate_summary_rows_remain_separately_identifiable():
    options, sources, contents = inputs("families_sheet")
    contents["families_document"] = modify_table(contents["families_document"], "plfam", lambda rows: rows.append(list(rows[-1])))
    value = build(options, sources, contents)
    rows = [r for r in value["family_rows"] if r["entity"]["family_kind"] == "plfam"]
    assert [row["native_row_ordinal"] for row in rows] == [0, 1]
    assert all("duplicate_identical_representation" in row["qualification_codes"] for row in rows)
    assert all(row["reported_feature_occurrences"]["value"] == 3 for row in rows)


def test_wrong_view_table_and_component_context_are_rejected():
    options, sources, contents = inputs("families_sheet")
    options["document_selection"]["authoritative_views"][0]["table"] = "pathway"
    with pytest.raises(ValueError, match="view_table_incompatible"):
        build(options, sources, contents)
    options, sources, contents = inputs()
    options["population_assignments"]["assignments"][3]["component_kind"] = "role_id"
    with pytest.raises(ValueError, match="population_component_selector_invalid"):
        build(options, sources, contents)


def test_native_represented_ids_are_compared_only_to_explicit_execution_evidence():
    value = sheet()
    assert pop(value, "pathway_native_genomes")["missing_members"] == []
    assert "3.1" in value["original_request"]["executed_genome_ids"]
    assert "3.1" not in pop(value, "pathway_native_genomes")["members"]
    options, sources, contents = inputs("families_sheet")
    source = json.loads(contents["families_document"])
    source["genome_ids"][2] = "unselected-genome"
    contents["families_document"] = json.dumps(source).encode()
    value = build(options, sources, contents)
    population = pop(value, "families_native_genomes")
    assert "unselected-genome" in population["members"]
    assert population["completeness"] == "incompatible"
    assert "population_incompatible" in population["qualification_codes"]


def test_partial_artifact_keeps_measured_values_but_not_complete_population():
    options, sources, contents = inputs("families_sheet")
    sources[0]["object_complete"] = "partial"
    value = build(options, sources, contents)
    assert value["family_rows"][0]["reported_feature_occurrences"]["value"] == 3
    assert "artifact_truncated" in value["family_rows"][0]["reported_feature_occurrences"]["qualification_codes"]
    assert pop(value, "families_native_genomes")["completeness"] == "partial"


def test_source_loss_qualification_cannot_be_removed_from_saved_measurement():
    value = sheet()
    value["pathway_rows"][0]["reported_ec_conservation_percent"]["qualification_codes"].remove("native_first_object_discard")
    with pytest.raises(ValueError, match="measurement_qualification_missing"):
        validate_sheet(value)


def test_occurrence_witness_populates_sheet_without_inventing_feature_rows():
    value = sheet("occurrence_omissions_sheet")
    row = value["family_rows"][0]
    assert row["reported_feature_occurrences"]["value"] == 3
    assert row["reported_length_mean"]["value"] == pytest.approx(500 / 3)
    assert [g["genome_id"] for g in row["genome_counts"]] == ["292462.10", "2.1", "3.1"]
    assert [g["reported_occurrences"]["value"] for g in row["genome_counts"]] == [2, 1, 0]
    assert not value["association_rows"]
    assert pop(value, "occurrence_native_genomes")["distinct_valid_member_count"]["value"] == 3
