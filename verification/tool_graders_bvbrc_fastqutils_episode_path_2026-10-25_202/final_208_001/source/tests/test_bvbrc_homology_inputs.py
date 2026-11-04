"""Synthetic Homology contracts; no scientific executable or service runs."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_homology_inputs import (
    FIELDS, FORMATS, _decode_description, _expected_processed,
    read_homology_raw_json, read_homology_processed_json, read_homology_tabular,
    reconcile_homology_artifacts,
)


FIXTURES = Path(__file__).parent / "fixtures" / "bvbrc_homology"


def encoded(value):
    return json.dumps(value, allow_nan=False).encode()


def artifact(content, role, *, mode="database_identification"):
    return {"role": role, "source_ref": "SYNTHETIC-source-" + role, "raw_artifact_ref": "SYNTHETIC-artifact-" + role,
        "sha256": hashlib.sha256(content).hexdigest(), "byte_count": len(content),
        "workspace_object": {"path": "/SYNTHETIC/" + role, "uuid": "SYNTHETIC-uuid-" + role,
            "type": "file", "metadata_receipt_ref": "SYNTHETIC-metadata-receipt"},
        "task_association": {"manifest_source_ref": "SYNTHETIC-manifest", "manifest_record_pointer": "/output_files/0",
            "task_id": "SYNTHETIC-task", "output_path": "/SYNTHETIC/" + role, "output_uuid": "SYNTHETIC-uuid-" + role},
        "transfer": {"receipt_ref": "SYNTHETIC-transfer", "body_complete": True,
            "requested_range": None, "observed_range": None, "total_size": len(content)},
        "declared_format": {"format": FORMATS[role], "version": None, "mode": mode,
            "producer_source_ref": "SYNTHETIC-retained-source-transform", "transformation_version": "source-sha256-qualified",
            "fields": FIELDS if role in {"blast_tabular", "blast_tabular_header"} else None}}


def raw_document(kind="synthetic_database"):
    return json.loads((FIXTURES / kind / "blast_out.raw.json").read_bytes())


def query_binding(report, index):
    query = report["report"]["results"]["search"]
    program = report["report"]["program"]
    molecule = "aa" if program in {"blastp", "tblastn"} else "nt"
    sequence = ("ACDEFGHIKL" if molecule == "aa" else "ACGTACGTACGTACGT")
    length = query["query_len"]
    sequence = (sequence * (1 + length // len(sequence)))[:length]
    digest = hashlib.sha256(sequence.encode()).hexdigest()
    return {"input_source_ref": "SYNTHETIC-input", "member_ref": f"SYNTHETIC-member-{index}",
        "subject_ref": f"SYNTHETIC-subject-{index}", "molecule": molecule, "supplied_id": query["query_title"],
        "supplied_length": length, "supplied_sequence_sha256": digest,
        "staged_id": query["query_title"], "staged_length": length, "staged_sequence_sha256": digest,
        "sequence_transform": {"kind": "identity", "source_ref": "SYNTHETIC-input", "pointer": f"/members/{index}",
            "coordinate_map_ref": None},
        "native_query": {"report_index": index, "query_id": query.get("query_id"),
            "query_title": query.get("query_title"), "query_len": query.get("query_len")},
        "id_mapping_evidence": [{"source_ref": "SYNTHETIC-stage-map", "pointer": f"/queries/{index}",
                                 "relation": "exact_submitted_member_to_native_query"}]}


def bundle(document=None, *, primary="raw", mode="database_identification", extras=True):
    document = raw_document() if document is None else deepcopy(document)
    entries = document["BlastOutput2"]
    contents = {"blast_json15_raw": encoded(document)}
    if extras:
        contents.update({"homology_processed_json": (FIXTURES / "synthetic_database/blast_out.json").read_bytes(),
            "homology_metadata_json": (FIXTURES / "synthetic_database/blast_out.metadata.json").read_bytes(),
            "blast_tabular": (FIXTURES / "synthetic_database/blast_out.txt").read_bytes(),
            "blast_tabular_header": (FIXTURES / "synthetic_database/blast_headers.txt").read_bytes()})
    artifacts = {role: artifact(content, role, mode=mode) for role, content in contents.items()}
    program = entries[0]["report"]["program"] if entries else "blastp"
    binding = {"schema": "bvbrc_homology_artifact_bundle_v1", "primary_representation": primary,
        "original_task": {"resource_id": "SYNTHETIC-api", "task_id": "SYNTHETIC-task",
            "required_application_id": "Homology", "native_application_id": "Homology",
            "submitted_parameters": {"blast_program": program, "blast_max_hits": 3},
            "submission_receipt_ref": "SYNTHETIC-submit", "effective_parameters": None,
            "effective_parameters_source": None},
        "scientific_mode": mode, "query_bindings": [query_binding(entry, i) for i, entry in enumerate(entries)
            if isinstance(entry, dict) and isinstance(entry.get("report"), dict)
            and isinstance(entry["report"].get("results", {}).get("search"), dict)],
        "subject_binding": None,
        "database_binding": {"requested_selection": {"db_source": "fasta_file", "db_type": "faa" if program in {"blastp", "blastx"} else "ffn"},
            "effective_native_database": "SYNTHETIC_DATABASE_PATH", "effective_parameters_source": None,
            "reference_release": None, "reference_release_source": None, "actual_taxon_filter": None,
            "actual_database_members": None, "input_or_database_sequence_inventory_ref": None},
        "artifacts": list(artifacts.values())}
    return binding, artifacts, contents


def replace_content(binding, artifacts, contents, role, content):
    contents[role] = content
    artifacts[role] = artifact(content, role, mode=binding["scientific_mode"])
    binding["artifacts"] = list(artifacts.values())


def parse_raw(binding, artifacts, contents):
    return read_homology_raw_json(contents["blast_json15_raw"], artifact=artifacts["blast_json15_raw"], binding=binding)


def parse_all(binding, artifacts, contents):
    raw = parse_raw(binding, artifacts, contents) if "blast_json15_raw" in contents else None
    processed = read_homology_processed_json(contents["homology_processed_json"],
        artifact=artifacts["homology_processed_json"], binding=binding) if "homology_processed_json" in contents else None
    tabular = read_homology_tabular(contents["blast_tabular"], header_content=contents["blast_tabular_header"],
        artifact=artifacts["blast_tabular"], header_artifact=artifacts["blast_tabular_header"], binding=binding) if "blast_tabular" in contents else None
    return reconcile_homology_artifacts(raw=raw, processed=processed, tabular=tabular, binding=binding)


def codes(parsed):
    return {item["code"] for item in parsed.get("diagnostics", [])} | {
        item["code"] for query in parsed.get("queries", []) for item in query.get("diagnostics", [])}


def test_raw_multiquery_all_hits_hsps_source_locators_and_separate_projection_hash():
    binding, artifacts, contents = bundle(extras=False)
    before = deepcopy(binding)
    parsed = parse_raw(binding, artifacts, contents)
    assert set(parsed) == {"schema", "status", "binding", "queries", "artifacts", "diagnostics"}
    assert parsed["status"] == "complete"
    assert len(parsed["queries"]) == 2
    query = parsed["queries"][0]
    assert query["query_binding_status"] == "validated"
    result = query["normalized_result"]
    assert len(result["hits"]) == 3
    assert [len(hit["hsps"]) for hit in result["hits"]] == [3, 1, 1]
    hsp = result["hits"][0]["hsps"][2]
    assert hsp["source_locator"]["pointer"].endswith("/hits/0/hsps/2")
    assert hsp["source_locator"]["hsp_index"] == 2
    assert result["native"]["original_sha256"] == artifacts["blast_json15_raw"]["sha256"]
    assert result["native"]["sha256"] == result["native"]["projection_sha256"]
    assert result["native"]["sha256"] != result["native"]["original_sha256"]
    assert parsed["queries"][1]["normalized_result"]["search"]["reported_hit_count"] == 0
    assert binding == before


def test_processed_only_preserves_all_rows_and_explicit_missing_raw_aliases():
    binding, artifacts, contents = bundle(primary="processed")
    doc = json.loads(contents["homology_processed_json"])
    binding["query_bindings"] = [query_binding(row, i) for i, row in enumerate(doc)]
    parsed = read_homology_processed_json(contents["homology_processed_json"], artifact=artifacts["homology_processed_json"], binding=binding)
    assert len(parsed["queries"]) == 2
    assert parsed["queries"][0]["query_binding_status"] == "validated"
    link = parsed["queries"][0]["description_links"][0]
    assert link["raw_id"] is None and link["raw_description_pointer"] is None
    assert link["processed_id"] == "fig|999999.1.peg.1"
    assert "homology_raw_identifiers_unavailable" in link["diagnostics"]


@pytest.mark.parametrize("content,code", [(b'{"BlastOutput2":[],"BlastOutput2":[]}', "homology_json_duplicate_key"),
    (b'{"BlastOutput2":[],"x":NaN}', "homology_json_nonfinite_number"),
    (b'{"BlastOutput2":[],"x":1e900}', "homology_json_nonfinite_number"),
    (b'{"BlastOutput2":[', "homology_json_document_invalid"),
    (b'[]', "homology_format_shape_mismatch"),
    (b'{"BlastOutput2":[],"x":' + b'9' * 400 + b'}', "homology_json_unrepresentable_number")])
def test_whole_document_defects_do_not_salvage_or_guess(content, code):
    binding, artifacts, contents = bundle(extras=False)
    replace_content(binding, artifacts, contents, "blast_json15_raw", content)
    parsed = parse_raw(binding, artifacts, contents)
    assert parsed["status"] == "unavailable" and parsed["queries"] == []
    assert code in codes(parsed)


@pytest.mark.parametrize("field,value,code", [
    (("task_association", "task_id"), "wrong", "homology_artifact_task_mismatch"),
    (("task_association", "output_uuid"), "wrong", "homology_artifact_object_mismatch"),
    (("task_association", "output_path"), "/wrong", "homology_artifact_object_mismatch"),
    (("transfer", "body_complete"), False, "homology_transfer_incomplete"),
    (("transfer", "total_size"), 1, "homology_transfer_incomplete"),
    (("transfer", "requested_range"), {"start": 0, "end": 1}, "homology_transfer_range_invalid"),
    (("declared_format", "format"), "json", "homology_format_shape_mismatch"),
    (("declared_format", "mode"), "pairwise_correspondence", "homology_format_shape_mismatch"),
])
def test_incompatible_artifact_claims_prevent_task_attachment(field, value, code):
    binding, artifacts, contents = bundle(extras=False)
    artifacts["blast_json15_raw"][field[0]][field[1]] = value
    parsed = parse_raw(binding, artifacts, contents)
    assert not parsed["queries"] and code in codes(parsed)


def test_wrong_body_digest_and_size_are_not_format_inference():
    binding, artifacts, contents = bundle(extras=False)
    parsed = read_homology_raw_json(b'{}', artifact=artifacts["blast_json15_raw"], binding=binding)
    assert {"homology_artifact_digest_mismatch", "homology_artifact_size_mismatch"} <= codes(parsed)


def test_malformed_independent_rows_keep_original_ordinals_and_other_queries():
    doc = raw_document()
    hits = doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"]
    hits.insert(0, "SYNTHETIC-invalid-hit")
    hits[1]["description"].insert(0, None)
    hits[1]["hsps"].insert(1, None)
    binding, artifacts, contents = bundle(doc, extras=False)
    parsed = parse_raw(binding, artifacts, contents)
    result = parsed["queries"][0]["normalized_result"]
    assert [hit["hit_index"] for hit in result["hits"]] == [0, 1, 2, 3]
    assert result["hits"][0]["native_invalid"] == "SYNTHETIC-invalid-hit"
    assert result["hits"][1]["descriptions"][0]["source_locator"]["description_index"] == 1
    assert [hsp["source_locator"]["hsp_index"] for hsp in result["hits"][1]["hsps"]] == [0, 1, 2, 3]
    assert result["hits"][1]["hsps"][1]["native_invalid"] is None
    assert parsed["queries"][1]["status"] == "complete"


def test_missing_hits_is_not_explicit_zero_and_zero_query_list_is_not_a_query():
    doc = raw_document()
    del doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"]
    binding, artifacts, contents = bundle(doc, extras=False)
    parsed = parse_raw(binding, artifacts, contents)
    assert parsed["queries"][0]["normalized_result"]["search"]["reported_hit_count"] is None
    assert parsed["queries"][1]["normalized_result"]["search"]["reported_hit_count"] == 0
    binding, artifacts, contents = bundle({"BlastOutput2": []}, extras=False)
    empty = parse_raw(binding, artifacts, contents)
    assert empty["queries"] == [] and "homology_zero_query_report" in codes(empty)


@pytest.mark.parametrize("change,code", [("missing", "homology_query_binding_unavailable"),
    ("duplicate", "homology_query_binding_ambiguous"), ("length", "homology_query_binding_native_conflict"),
    ("digest", "homology_query_sequence_identity_conflict"), ("evidence", "homology_query_binding_evidence_required")])
def test_unresolved_query_attachment_keeps_native_measurements(change, code):
    binding, artifacts, contents = bundle(extras=False)
    query = binding["query_bindings"][0]
    if change == "missing":
        binding["query_bindings"].pop(0)
    elif change == "duplicate":
        binding["query_bindings"].append(deepcopy(query))
    elif change == "length":
        query["native_query"]["query_len"] = 99
    elif change == "digest":
        query["staged_sequence_sha256"] = "0" * 64
    elif change == "evidence":
        query["id_mapping_evidence"] = []
    parsed = parse_raw(binding, artifacts, contents)
    assert code in codes(parsed)
    assert len(parsed["queries"][0]["normalized_result"]["hits"]) == 3
    assert parsed["queries"][0]["query_binding"] is None


def test_declared_normalization_keeps_native_coordinates_and_requires_actual_map_content():
    binding, artifacts, contents = bundle(extras=False)
    query = binding["query_bindings"][0]
    query["supplied_length"] = 12
    query["supplied_sequence_sha256"] = "1" * 64
    query["sequence_transform"].update(kind="verified_fasta_normalization", coordinate_map_ref="SYNTHETIC-map-ref")
    parsed = parse_raw(binding, artifacts, contents)
    assert parsed["queries"][0]["query_binding_status"] == "validated"
    assert "homology_original_coordinate_map_content_unavailable" in codes(parsed)
    assert parsed["queries"][0]["normalized_result"]["query"]["length"] == 10


def test_program_conflict_keeps_observed_program_and_native_values():
    binding, artifacts, contents = bundle(extras=False)
    binding["original_task"]["submitted_parameters"]["blast_program"] = "blastn"
    parsed = parse_raw(binding, artifacts, contents)
    assert "homology_program_request_conflict" in codes(parsed)
    assert parsed["queries"][0]["normalized_result"]["search"]["program"] == "blastp"


def test_tabular_native_counts_lexemes_duplicate_lines_and_empty_not_zero():
    binding, artifacts, contents = bundle(primary="tabular")
    parsed = read_homology_tabular(contents["blast_tabular"], header_content=contents["blast_tabular_header"],
        artifact=artifacts["blast_tabular"], header_artifact=artifacts["blast_tabular_header"], binding=binding)
    rows = parsed["queries"][0]["native_tabular_measurements"]
    assert len(rows) == 5 and rows[0]["native_line"] == rows[2]["native_line"]
    assert rows[3]["mismatch"] == 1 and rows[3]["gapopen"] == 0 and rows[3]["pident"] == 75
    assert rows[3]["fields"]["pident"] == "75.0"
    assert len(parsed["queries"]) == 1  # no invention of the omitted zero-hit query
    replace_content(binding, artifacts, contents, "blast_tabular", b'')
    empty = read_homology_tabular(b'', header_content=contents["blast_tabular_header"],
        artifact=artifacts["blast_tabular"], header_artifact=artifacts["blast_tabular_header"], binding=binding)
    assert empty["queries"] == [] and "homology_zero_hit_query_unestablished" in codes(empty)


def test_tabular_header_conflict_and_partial_independent_lines():
    binding, artifacts, contents = bundle(primary="tabular")
    replace_content(binding, artifacts, contents, "blast_tabular_header", b'qseqid\tsseqid\n')
    parsed = read_homology_tabular(contents["blast_tabular"], header_content=contents["blast_tabular_header"],
        artifact=artifacts["blast_tabular"], header_artifact=artifacts["blast_tabular_header"], binding=binding)
    assert "homology_tabular_fields_conflict" in codes(parsed)
    binding, artifacts, contents = bundle(primary="tabular")
    text = contents["blast_tabular"].decode().splitlines()
    text.insert(1, "synthetic_query_hit\tbroken")
    text[4] = text[4].replace("\t75.0\t", "\tnonsense\t")
    replace_content(binding, artifacts, contents, "blast_tabular", ("\n".join(text) + "\n").encode())
    parsed = read_homology_tabular(contents["blast_tabular"], header_content=contents["blast_tabular_header"],
        artifact=artifacts["blast_tabular"], header_artifact=artifacts["blast_tabular_header"], binding=binding)
    assert len(parsed["queries"][0]["native_tabular_measurements"]) == 6
    result = parsed["queries"][0]["normalized_result"]
    assert sum(len(hit["hsps"]) for hit in result["hits"]) == 5
    assert result["hits"][0]["hsps"][1]["source_locator"]["line"] == 3
    assert "blast_tabular_number_invalid" in codes(parsed)


def test_reconciliation_never_chooses_secondary_or_adds_duplicate_evidence():
    binding, artifacts, contents = bundle()
    parsed = parse_all(binding, artifacts, contents)
    assert len(parsed["queries"]) == 2
    assert sum(len(hit["hsps"]) for hit in parsed["queries"][0]["normalized_result"]["hits"]) == 5
    table = next(row for row in parsed["artifacts"] if row["artifact"]["role"] == "blast_tabular")
    assert len(table["representation_links"][0]["matches"]) == 2
    assert table["representation_links"][0]["status"] == "ambiguous"
    assert len(parsed["queries"][0]["native_tabular_measurements"]) == 5
    raw = parse_raw(binding, artifacts, contents)
    absent = reconcile_homology_artifacts(raw=None, processed=None, tabular=None, binding=binding)
    assert absent["status"] == "unavailable" and not absent["queries"]
    assert "homology_primary_representation_unavailable" in codes(absent)
    doc = json.loads(contents["homology_processed_json"])
    doc[0]["report"]["results"]["search"]["hits"][0]["hsps"][0]["bit_score"] = 999
    replace_content(binding, artifacts, contents, "homology_processed_json", encoded(doc))
    conflict = parse_all(binding, artifacts, contents)
    assert "homology_processed_transform_conflict" in codes(conflict)
    assert conflict["queries"][0]["normalized_result"]["hits"][0]["hsps"][0]["bit_score"] == 20
    assert conflict["queries"][1]["status"] == "complete"


def test_collision_keeps_both_descriptions_and_marks_overwritten_sidecar_link():
    binding, artifacts, contents = bundle(raw_document("synthetic_collision"), extras=False)
    parsed = parse_raw(binding, artifacts, contents)
    links = [link for query in parsed["queries"] for link in query["description_links"]]
    assert len(links) == 3
    collision = [link for link in links if link["metadata_key"] == "fig|999999.1.peg.1"]
    assert len(collision) == 2 and all(link["status"] == "ambiguous" for link in collision)


@pytest.mark.parametrize("description,expected_id,expected_function", [
    ({"id": "gnl|BL_ORD_ID|0", "title": "accn|ABC|ALT   FUNCTION   [ORGANISM | 1.2]"}, "accn|ABC", "FUNCTION"),
    ({"id": "gnl|BL_ORD_ID|0", "title": "ref function words   [Organism | genome]"}, "ref", "function words"),
    ({"id": "gnl|BL_ORD_ID|0", "title": "ref [Organism | genome]"}, "ref", None),
    ({"id": "gnl|BL_ORD_ID|0", "title": "ref generic words"}, "ref", "generic words"),
    ({"id": "gnl|BL_ORD_ID|0", "title": "ref"}, "ref", None),
    ({"id": "gnl|ref", "title": "Function   [Organism | genome]"}, "ref", "Function"),
    ({"id": "gnl|ref", "title": "[Organism | genome]"}, "ref", None),
    ({"id": "kb|g.123.peg.1", "title": "plain"}, "kb|g.123.peg.1", None),
    ({"id": "gnl|BL_ORD_ID|0", "title": "badprefix   Function   [Organism | 1.2]"}, "badprefix", "Function"),
])
def test_retained_transform_branches_are_literal_link_validation_only(description, expected_id, expected_function):
    transformed, metadata = _decode_description(description)
    assert transformed["id"] == expected_id
    assert (metadata or {}).get("function") == expected_function
    if description["id"].startswith("kb|"):
        assert metadata["genome_id"] == "kb|g.123"


def test_retained_source_executed_examples_match_python_transform_exactly():
    for kind in ("synthetic_database", "synthetic_collision"):
        raw = raw_document(kind)
        processed = json.loads((FIXTURES / kind / "blast_out.json").read_bytes())
        assert [_expected_processed(entry) for entry in raw["BlastOutput2"]] == processed


def test_archive_descriptor_retained_without_decoder_or_inferred_format():
    binding, artifacts, contents = bundle(extras=False)
    # Deliberately a descriptor only. These are not fabricated native archive bytes.
    archive = artifact(b'SYNTHETIC descriptor placeholder; never decoded', "blast_archive")
    binding["artifacts"].append(archive)
    parsed = reconcile_homology_artifacts(raw=parse_raw(binding, artifacts, contents), processed=None, tabular=None, binding=binding)
    row = next(item for item in parsed["artifacts"] if item["artifact"]["role"] == "blast_archive")
    assert row["native_document"] is None
    assert "archive_decoder_not_provided" in row["qualifications"]
    assert not any("content_base64" in item for item in parsed["artifacts"])


def test_declared_observed_version_conflict_is_explicit_and_preserves_other_fields():
    binding, artifacts, contents = bundle(extras=False)
    artifacts["blast_json15_raw"]["declared_format"]["version"] = "BLASTP other version"
    parsed = parse_raw(binding, artifacts, contents)
    assert "homology_format_version_conflict" in codes(parsed)
    assert parsed["queries"][0]["normalized_result"]["search"]["version"] == "BLASTP SYNTHETIC_FORMAT_EXAMPLE"


def test_malformed_report_does_not_shift_later_report_ordinal():
    doc = raw_document()
    doc["BlastOutput2"].insert(1, None)
    binding, artifacts, contents = bundle(doc, extras=False)
    parsed = parse_raw(binding, artifacts, contents)
    assert [row["report_index"] for row in parsed["queries"]] == [0, 1, 2]
    assert parsed["queries"][1]["status"] == "invalid"
    assert parsed["queries"][2]["query_binding_status"] == "validated"
    assert parsed["queries"][2]["normalized_result"]["search"]["reported_hit_count"] == 0


def test_matching_supplied_query_length_is_only_used_after_explicit_member_link():
    doc = raw_document()
    binding, artifacts, contents = bundle(doc, extras=False)
    del doc["BlastOutput2"][0]["report"]["results"]["search"]["query_len"]
    binding["query_bindings"][0]["native_query"]["query_len"] = None
    replace_content(binding, artifacts, contents, "blast_json15_raw", encoded(doc))
    parsed = parse_raw(binding, artifacts, contents)
    query = parsed["queries"][0]
    assert query["query_binding_status"] == "validated"
    assert query["normalized_result"]["query"]["length"] == 10
    assert query["normalized_result"]["query"]["length_source"]["kind"] == "verified_supplied_query_binding"
    binding["query_bindings"][0]["id_mapping_evidence"] = []
    unmatched = parse_raw(binding, artifacts, contents)
    assert unmatched["queries"][0]["normalized_result"]["query"]["length"] is None


@pytest.mark.parametrize("column,value", [("mismatch", "3"), ("gapopen", "1"), ("pident", "99.0"),
                                         ("bitscore", "21"), ("qlen", "99")])
def test_table_to_json_association_checks_native_measurements_and_lengths(column, value):
    binding, artifacts, contents = bundle()
    lines = contents["blast_tabular"].decode().splitlines()
    cells = lines[3].split("\t")
    from gene_annotation_episode.bvbrc_homology_inputs import FIELDS
    cells[FIELDS.index(column)] = value
    lines[3] = "\t".join(cells)
    replace_content(binding, artifacts, contents, "blast_tabular", ("\n".join(lines) + "\n").encode())
    parsed = parse_all(binding, artifacts, contents)
    assert "homology_tabular_representation_conflict" in codes(parsed)
    primary = parsed["queries"][0]["normalized_result"]
    assert primary["hits"][1]["hsps"][0]["bit_score"] == 18
    assert primary["query"]["length"] == 10


def test_table_duplicate_multiplicity_conflict_is_not_an_arbitrary_first_match():
    binding, artifacts, contents = bundle()
    lines = contents["blast_tabular"].decode().splitlines()
    lines.append(lines[0])
    replace_content(binding, artifacts, contents, "blast_tabular", ("\n".join(lines) + "\n").encode())
    parsed = parse_all(binding, artifacts, contents)
    assert "homology_tabular_hsp_multiplicity_conflict" in codes(parsed)
    table = next(row for row in parsed["artifacts"] if row["artifact"]["role"] == "blast_tabular")
    repeated = [link for link in table["representation_links"] if link["line"] in {1, 3, 6}]
    assert len(repeated) == 3 and all(len(link["matches"]) == 2 for link in repeated)
    assert all(link["status"] == "conflicting" for link in repeated)


def test_headerless_multiquery_table_retains_query_and_line_groups():
    binding, artifacts, contents = bundle(primary="tabular")
    lines = contents["blast_tabular"].decode().splitlines()
    second = lines[0].replace("synthetic_query_hit", "another_query")
    replace_content(binding, artifacts, contents, "blast_tabular", (lines[0] + "\n" + second + "\n" + lines[1] + "\n").encode())
    parsed = read_homology_tabular(contents["blast_tabular"], header_content=contents["blast_tabular_header"],
        artifact=artifacts["blast_tabular"], header_artifact=artifacts["blast_tabular_header"], binding=binding)
    assert len(parsed["queries"]) == 2
    assert [row["line"] for row in parsed["queries"][0]["native_tabular_measurements"]] == [1, 3]
    assert [row["line"] for row in parsed["queries"][1]["native_tabular_measurements"]] == [2]


@pytest.mark.parametrize("observed", [False, True])
def test_requested_range_does_not_reject_verified_entire_object(observed):
    binding, artifacts, contents = bundle(extras=False)
    size = len(contents["blast_json15_raw"])
    transfer = artifacts["blast_json15_raw"]["transfer"]
    transfer.update(requested_range=[0, size + 100], object_complete="yes")
    if observed:
        transfer["observed_range"] = {"start": 0, "end_inclusive": size - 1, "total_size": size}
    parsed = parse_raw(binding, artifacts, contents)
    assert parsed["status"] == "complete"
    assert len(parsed["queries"]) == 2
    qualification = "observed_byte_interval_covers_entire_object" if observed else "complete_body_despite_requested_range"
    assert qualification in parsed["artifacts"][0]["qualifications"]


@pytest.mark.parametrize("changes", [{"start": 1}, {"end_inclusive": 1}, {"total_size": 1},
                                  {"start": False}, {"end_inclusive": 1.0}, {"extra": 1}])
def test_partial_or_malformed_observed_ranges_cannot_establish_whole_document(changes):
    binding, artifacts, contents = bundle(extras=False)
    size = len(contents["blast_json15_raw"])
    transfer = artifacts["blast_json15_raw"]["transfer"]
    transfer["observed_range"] = {"start": 0, "end_inclusive": size - 1, "total_size": size, **changes}
    parsed = parse_raw(binding, artifacts, contents)
    assert parsed["queries"] == []
    assert codes(parsed) & {"homology_transfer_incomplete", "homology_transfer_range_invalid"}


@pytest.mark.parametrize("value", [False, 0.0, "0"])
def test_query_report_identity_never_accepts_boolean_float_or_text_ordinal(value):
    binding, artifacts, contents = bundle(extras=False)
    binding["query_bindings"][0]["native_query"]["report_index"] = value
    parsed = parse_raw(binding, artifacts, contents)
    assert parsed["queries"][0]["query_binding_status"] != "validated"
    assert parsed["queries"][0]["normalized_result"]["hits"][0]["hsps"][0]["bit_score"] == 20


def test_invalid_native_query_identity_is_not_sanitized_to_valid_null_attachment():
    doc = raw_document()
    doc["BlastOutput2"][0]["report"]["results"]["search"]["query_id"] = False
    binding, artifacts, contents = bundle(doc, extras=False)
    binding["query_bindings"][0]["native_query"]["query_id"] = None
    parsed = parse_raw(binding, artifacts, contents)
    assert parsed["queries"][0]["query_binding_status"] == "invalid"


def test_failed_source_feature_prefix_keeps_observed_invalid_id_without_guessing_association():
    doc = raw_document()
    doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["description"][0]["title"] = "badprefix   Function   [Organism | 1.2]"
    binding, artifacts, contents = bundle(doc, extras=False)
    parsed = parse_raw(binding, artifacts, contents)
    link = parsed["queries"][0]["description_links"][0]
    assert link["processed_id"] == "badprefix"
    assert link["status"] == "invalid" and link["metadata_key"] is None


def test_tabular_primary_preserves_secondary_zero_query_without_switching_numerical_source():
    binding, artifacts, contents = bundle(primary="tabular")
    parsed = parse_all(binding, artifacts, contents)
    assert len(parsed["queries"]) == 2
    assert parsed["queries"][0]["normalized_result"]["format"] == "tabular"
    zero = parsed["queries"][1]
    assert zero["report_index"] == 1 and zero["normalized_result"] is None
    assert zero["status"] == "unavailable"
    assert zero["query_binding"]["subject_ref"] == binding["query_bindings"][1]["subject_ref"]
    assert "homology_primary_query_unavailable" in {row["code"] for row in zero["diagnostics"]}
    raw = next(row for row in parsed["artifacts"] if row["artifact"]["role"] == "blast_json15_raw")
    assert raw["native_document"]["BlastOutput2"][1]["report"]["results"]["search"]["hits"] == []
