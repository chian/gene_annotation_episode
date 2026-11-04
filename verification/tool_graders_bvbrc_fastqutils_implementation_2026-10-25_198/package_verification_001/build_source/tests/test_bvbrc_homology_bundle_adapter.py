"""Synthetic C4-to-Homology integration. No remote call or BLAST execution."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import bvbrc_homology_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_appservice_contracts import ContractValidationError, validate_contract
from gene_annotation_episode.bvbrc_homology_grader import calculate_homology_scores
from gene_annotation_episode.bvbrc_homology_inputs import FIELDS, _expected_processed
from test_bvbrc_homology_inputs import bundle as legacy_bundle, encoded, query_binding, replace_content, raw_document
from test_bvbrc_homology_grader import (
    F, G, add_subject, program_document, supplied, source_record, metadata_link, full_sequence_link,
)


def evidence(value, *, source="SYNTHETIC-scientific-inputs", pointer=""):
    content = encoded(value)
    return {"content": {"source_ref": source, "artifact_field": "artifact_ref", "artifact_ref": source + "-artifact",
                        "sha256": hashlib.sha256(content).hexdigest(), "byte_count": len(content)}, "pointer": pointer}


def c4_fixture(document=None, *, primary="raw", mode="database_identification", extras=True):
    legacy, artifacts, contents = legacy_bundle(document, primary=primary, mode=mode, extras=extras)
    if primary == "processed":
        entries = [_expected_processed(row) for row in (document or raw_document())["BlastOutput2"]]
        replace_content(legacy, artifacts, contents, "homology_processed_json", encoded(entries))
        legacy["query_bindings"] = [query_binding(row, i) for i, row in enumerate(entries)]
    if mode == "pairwise_correspondence":
        add_subject(legacy, document)
    if primary == "tabular" and document is not None:
        search = document["BlastOutput2"][0]["report"]["results"]["search"]
        hit, = search["hits"]
        hsp, = hit["hsps"]
        fields = ["Query_1", "SYNTHETIC-subject", "100.0", "3", "0", "0", str(hsp["query_from"]), str(hsp["query_to"]),
                  str(hsp["hit_from"]), str(hsp["hit_to"]), "0.0", "20", str(search["query_len"]), str(hit["len"])]
        replace_content(legacy, artifacts, contents, "blast_tabular", ("\t".join(fields) + "\n").encode())
        replace_content(legacy, artifacts, contents, "blast_tabular_header", ("\t".join(FIELDS) + "\n").encode())
        legacy["query_bindings"][0]["native_query"]["query_title"] = None
    task = deepcopy(legacy["original_task"])
    task.pop("effective_parameters_source")
    task["submitted_parameters"].update(legacy["database_binding"]["requested_selection"])
    task.update(submitted_start_parameters={}, scheduler_returned_parameters=None,
                submission_operation_key="SYNTHETIC-run:launch:0", submission_source_ref="SYNTHETIC-submit-body")
    version_evidence = evidence({"test_fixture": "SYNTHETIC producer digests"}, source="SYNTHETIC-version")
    c4_artifacts = []
    for row in artifacts.values():
        item = deepcopy(row)
        old = item["task_association"]
        item["task_association"] = {"kind": "task_result_manifest", "evidence_ref": old["manifest_source_ref"],
            "pointer": old["manifest_record_pointer"], **{k: old[k] for k in ("task_id", "output_path", "output_uuid")},
            "byte_version_status": "producer_bytes_bound", "version_evidence": [version_evidence]}
        item["transfer"]["object_complete"] = "yes"
        for key in ("fields", "transformation_version"):
            item["declared_format"].pop(key)
        item["declared_format"]["transformation_evidence"] = []
        c4_artifacts.append(item)
    input_content = evidence({"test_fixture": "SYNTHETIC supplied members"}, source="SYNTHETIC-input")["content"]
    input_binding = {"binding_id": "query-input", "parameter_pointer": "/input_fasta_file", "kind": "retained_bytes",
        "content": input_content, "workspace_path": "/SYNTHETIC/queries", "inline_value": None,
        "link_evidence": None, "members": [{"member_id": q["member_ref"], "member_pointer": f"/members/{i}",
            "length": q["supplied_length"], "molecule": "protein" if q["molecule"] == "aa" else "dna",
            "sequence_sha256": q["supplied_sequence_sha256"], "evidence": None}
            for i, q in enumerate(legacy["query_bindings"])]}
    task["submitted_parameters"]["input_fasta_file"] = input_binding["workspace_path"]
    reference_binding = reference_value = None
    if mode == "pairwise_correspondence":
        # The earlier fixture asserted a subject digest without supplying its
        # original reference input. Retain a real synthetic single-sequence
        # input and source row; a one-hit result is never membership evidence.
        report = document["BlastOutput2"][0]["report"]
        program = report["program"]
        hit = report["results"]["search"]["hits"][0]
        molecule = "protein" if program in {"blastp", "blastx"} else "dna"
        prefix = "MKT" if molecule == "protein" else "ACT" if program == "blastn" else "ATGAAAACC"
        sequence = prefix + "A" * (hit["len"] - len(prefix))
        native_id = hit["description"][0]["id"]
        fasta = ">" + native_id + "\n" + sequence + "\n"
        row = {"member_id": "SYNTHETIC-member-reference", "subject_ref": "SYNTHETIC-reference-subject",
            "supplied_id": native_id, "sequence": sequence, "length": len(sequence), "molecule": molecule,
            "sequence_sha256": hashlib.sha256(sequence.encode()).hexdigest()}
        original = {"fasta": fasta, "members": [row]}
        reference_source = evidence(original, source="SYNTHETIC-original-reference")
        member_evidence = {"content": reference_source["content"], "pointer": "/members/0"}
        reference_binding = {"binding_id": "reference-input", "parameter_pointer": "/db_fasta_data",
            "kind": "supplied_link", "content": None, "workspace_path": None, "inline_value": fasta,
            "link_evidence": {"content": reference_source["content"], "pointer": "/fasta"},
            "members": [{"member_id": row["member_id"], "member_pointer": "/members/0",
                **{key: row[key] for key in ("length", "molecule", "sequence_sha256")}, "evidence": member_evidence}]}
        db = {"db_source": "fasta_data", "db_type": "faa" if molecule == "protein" else "fna", "db_fasta_data": fasta}
        task["submitted_parameters"] = {key: value for key, value in task["submitted_parameters"].items() if not key.startswith("db_")}
        task["submitted_parameters"].update(db)
        legacy["database_binding"].update(requested_selection=db,
            actual_database_members=[{"identifier": row["member_id"], "sequence_sha256": row["sequence_sha256"],
                "length": row["length"], "molecule": "aa" if molecule == "protein" else "nt"}],
            input_or_database_sequence_inventory_ref=reference_source["content"]["source_ref"])
        legacy["subject_binding"].update(source_ref=reference_source["content"]["source_ref"],
            sequence_sha256=row["sequence_sha256"], length=row["length"],
            database_membership={"source_ref": reference_source["content"]["source_ref"], "pointer": "/members", "member_count": 1})
        reference_value = {"evidence": reference_source, "value": original}
    inputs = {"version": adapter.SCIENTIFIC_INPUTS_VERSION,
        "queries": [{"input_binding_id": "query-input", "input_member_id": q["member_ref"],
                     "representation": primary, "binding": q} for q in legacy["query_bindings"]],
        "database_binding": legacy["database_binding"], "subject_binding": legacy["subject_binding"], "metadata": supplied()}
    source = evidence(inputs)
    bundle = {"version": "bvbrc_appservice_artifact_bundle_v1", "original_task": task,
        "artifacts": c4_artifacts, "input_bindings": [input_binding], "query_bindings": [],
        "supplied_scientific_metadata": [source],
        "acquisition_receipt_refs": list(dict.fromkeys(a["transfer"]["receipt_ref"] for a in c4_artifacts)),
        "requested_selector_sha256": "e" * 64, "status": "ok", "missing_requirements": [], "diagnostics": []}
    params = {"version": adapter.PARAMETERS_VERSION, "scientific_mode": mode, "primary_representation": primary,
        "artifact_source_refs": dict.fromkeys(adapter.FORMATS), "scientific_inputs": source,
        "tabular_fields": FIELDS, "database_model": {"temperature_bits": 2, "function_priors": None}
            if mode == "database_identification" else None}
    values = [{"evidence": source, "value": inputs}]
    if reference_binding is not None:
        bundle["input_bindings"].append(reference_binding)
        bundle["supplied_scientific_metadata"].append(reference_value["evidence"])
        values.append(reference_value)
    content_map = {a["raw_artifact_ref"]: contents[a["role"]] for a in c4_artifacts}
    validate_contract("ArtifactBundle", bundle)
    return bundle, content_map, values, params


def refresh_metadata(bundle, values, params):
    source = evidence(values[0]["value"])
    bundle["supplied_scientific_metadata"] = [source, *[row["evidence"] for row in values[1:]]]
    values[0]["evidence"] = params["scientific_inputs"] = source


def consume(fixture, selections=None):
    bundle, content, values, parameters = fixture
    return adapter.consume_bundle(bundle, artifact_bytes=content, supplied_values=values, parameters=parameters,
        requested_form=adapter.requested_form_schema(selections or {"hits": {"metric": "reported_hit_count", "report_index": 0}}))


def codes(result):
    return {row["code"] for row in result["diagnostics"]}


def test_exact_c4_contract_numerical_sheet_components_and_small_projection():
    fixture = c4_fixture()
    result = consume(fixture, {"hits": {"metric": "reported_hit_count", "report_index": 0},
        "qcov": {"metric": "query_paired_coverage", "report_index": 0, "hit_index": 0},
        "rcov": {"metric": "reference_paired_coverage", "report_index": 0, "hit_index": 0},
        "alpha": {"metric": "conditional_function_weight", "report_index": 0, "function": F},
        "beta": {"metric": "conditional_function_weight", "report_index": 0, "function": G},
        "missing": {"metric": "missing_requirements"}})
    assert set(result) == {"adapter_id", "adapter_version", "status", "sheet", "components", "facts", "missing_requirements", "diagnostics"}
    assert result["status"] == "ok", result["diagnostics"]
    assert result["facts"] == {"hits": 3, "qcov": .6, "rcov": .75, "alpha": 2 / 3, "beta": 1 / 3, "missing": []}
    assert len(result["sheet"]["queries"]) == 2
    assert result["sheet"]["queries"][0]["blast_sheet"]["hits"][0]["measurements"]["overlap_pair_representations"] == 6
    assert result["sheet"]["binding"]["c4_bundle"] == fixture[0]
    assert result["sheet"]["binding"]["supplied_values"] == fixture[2]


@pytest.mark.parametrize("program", ["blastp", "blastn", "blastx", "tblastn", "tblastx"])
@pytest.mark.parametrize("mode", ["database_identification", "pairwise_correspondence"])
@pytest.mark.parametrize("representation", ["raw", "processed", "tabular"])
def test_five_programs_two_modes_three_explicit_representations(program, mode, representation):
    fixture = c4_fixture(program_document(program), primary=representation, mode=mode, extras=False)
    result = consume(fixture, {"span": {"metric": "query_span_coverage", "report_index": 0, "hit_index": 0},
        "aligned": {"metric": "paired_columns", "report_index": 0, "hit_index": 0, "hsp_index": 0}})
    assert result["facts"]["span"] == .6, result["diagnostics"]
    assert result["facts"]["aligned"] == (None if representation == "tabular" else 3)
    sheet = result["sheet"]["queries"][0]
    assert sheet["query_binding_status"] == "validated"
    assert sheet["blast_sheet"]["schema"] == ("blast_database_sheet_v1" if mode == "database_identification" else "blast_pairwise_sheet_v1")
    assert (result["components"]["queries"][0]["pairwise_correspondence"] is not None) == (mode == "pairwise_correspondence")
    assert (result["components"]["queries"][0]["conditional_function_weights"] is not None) == (mode == "database_identification")


def test_sequential_actual_bytes_leave_prior_publication_unchanged():
    full = c4_fixture()
    early = deepcopy(full)
    early[0]["artifacts"] = [a for a in early[0]["artifacts"] if a["role"] == "blast_json15_raw"]
    early[1].clear()
    early[1][early[0]["artifacts"][0]["raw_artifact_ref"]] = full[1][early[0]["artifacts"][0]["raw_artifact_ref"]]
    selection = {"alpha": {"metric": "conditional_function_weight", "report_index": 0, "function": F}}
    first = consume(early, selection)
    snapshot = deepcopy(first)
    second = consume(full, selection)
    assert first["status"] == "partial" and first["facts"] == {"alpha": None}
    assert first["missing_requirements"]
    assert second["status"] == "ok" and second["facts"] == {"alpha": 2 / 3}
    assert first == snapshot
    assert len(first["sheet"]["queries"][0]["normalized_result"]["hits"]) == 3


def test_no_hit_missing_hits_and_empty_table_are_different():
    fixture = c4_fixture()
    no_hit = consume(fixture, {"zero": {"metric": "reported_hit_count", "report_index": 1}})
    assert no_hit["status"] == "ok" and no_hit["facts"] == {"zero": 0}
    doc = program_document("blastp")
    del doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"]
    missing = consume(c4_fixture(doc, extras=False))
    assert missing["facts"] == {"hits": None} and missing["status"] == "partial"
    table = c4_fixture(program_document("blastp"), primary="tabular", extras=False)
    row = next(a for a in table[0]["artifacts"] if a["role"] == "blast_tabular")
    row["sha256"], row["byte_count"], row["transfer"]["total_size"] = hashlib.sha256(b"").hexdigest(), 0, 0
    table[1][row["raw_artifact_ref"]] = b""
    empty = consume(table)
    assert empty["facts"] == {"hits": None} and empty["status"] == "partial"
    assert "homology_zero_hit_query_unestablished" in codes(empty)


@pytest.mark.parametrize("kind", ["task_info_object", "task_info_folder_member", "unverified_original_path"])
def test_weaker_c4_association_never_fabricates_manifest(kind):
    fixture = c4_fixture(program_document("blastp"), extras=False)
    artifact = fixture[0]["artifacts"][0]
    artifact["task_association"]["kind"] = kind
    if kind == "unverified_original_path":
        artifact["task_association"].update(evidence_ref=None, pointer=None, output_uuid=None)
    result = consume(fixture)
    assert result["status"] == "partial" and result["facts"]["hits"] is None
    assert "homology_task_manifest_required" in codes(result)
    assert result["sheet"]["binding"]["c4_bundle"]["artifacts"][0] == artifact
    assert result["sheet"]["binding"]["artifacts"] == []


@pytest.mark.parametrize("field", ["path", "type", "metadata_receipt_ref"])
def test_uuid_does_not_invent_missing_workspace_metadata(field):
    fixture = c4_fixture(program_document("blastp"), extras=False)
    artifact = fixture[0]["artifacts"][0]
    artifact["workspace_object"][field] = None
    if field == "path":
        artifact["task_association"]["output_path"] = None
    result = consume(fixture)
    assert result["facts"]["hits"] is None
    assert "homology_workspace_metadata_required" in codes(result)


def test_current_bytes_retained_but_not_upgraded_to_producer_version():
    fixture = c4_fixture(program_document("blastp"), extras=False)
    association = fixture[0]["artifacts"][0]["task_association"]
    association.update(byte_version_status="current_bytes_observed", version_evidence=[])
    result = consume(fixture)
    assert result["facts"] == {"hits": 1} and result["status"] == "ok"
    assert result["missing_requirements"] == []
    assert any(d["code"] == "output_version_unproven" and d["severity"] == "qualification" for d in result["diagnostics"])


def test_wrong_task_and_supplied_digest_never_calculate_as_valid():
    fixture = c4_fixture(program_document("blastp"), extras=False)
    fixture[0]["artifacts"][0]["task_association"]["task_id"] = "SYNTHETIC-wrong-task"
    result = consume(fixture)
    assert result["status"] == "invalid" and result["sheet"] is None
    fixture = c4_fixture(program_document("blastp"), extras=False)
    fixture[1][fixture[0]["artifacts"][0]["raw_artifact_ref"]] += b" "
    result = consume(fixture)
    assert result["status"] == "partial" and result["facts"]["hits"] is None
    assert "homology_artifact_bytes_conflict" in codes(result)


def test_duplicate_representation_keeps_all_original_records_and_no_extra_mass():
    fixture = c4_fixture()
    before = consume(fixture)
    repeated = deepcopy(fixture[0]["artifacts"][0])
    repeated["source_ref"] += "-repeat"
    repeated["transfer"]["receipt_ref"] = "SYNTHETIC-transfer-repeat"
    fixture[0]["artifacts"].append(repeated)
    fixture[0]["acquisition_receipt_refs"].append("SYNTHETIC-transfer-repeat")
    result = consume(fixture)
    assert result["status"] == "ok" and result["facts"] == before["facts"]
    assert result["components"] == before["components"]
    assert len(result["sheet"]["binding"]["c4_bundle"]["artifacts"]) == 6
    assert "duplicate_artifact_representation" in codes(result)


def test_distinct_same_role_requires_explicit_selection_and_preserves_other_bytes():
    fixture = c4_fixture(program_document("blastp"), extras=False)
    first = fixture[0]["artifacts"][0]
    second = deepcopy(first)
    second["source_ref"] += "-other"
    second["raw_artifact_ref"] += "-other"
    body = fixture[1][first["raw_artifact_ref"]] + b"\n"
    fixture[1][second["raw_artifact_ref"]] = body
    second.update(sha256=hashlib.sha256(body).hexdigest(), byte_count=len(body))
    second["transfer"]["total_size"] = len(body)
    fixture[0]["artifacts"].append(second)
    ambiguous = consume(fixture)
    assert ambiguous["facts"]["hits"] is None
    assert "homology_artifact_role_ambiguous" in codes(ambiguous)
    fixture[3]["artifact_source_refs"]["blast_json15_raw"] = first["source_ref"]
    selected = consume(fixture)
    assert selected["status"] == "ok" and selected["facts"]["hits"] == 1
    assert selected["sheet"]["binding"]["c4_bundle"]["artifacts"] == fixture[0]["artifacts"]


@pytest.mark.parametrize("field,value", [("supplied_length", 99), ("supplied_sequence_sha256", "f" * 64),
    ("input_source_ref", "SYNTHETIC-unreceived"), ("molecule", "nt"), ("member_ref", "SYNTHETIC-other-member")])
def test_query_mapping_conflict_keeps_native_numbers_but_no_attached_fact(field, value):
    fixture = c4_fixture(program_document("blastp"), extras=False)
    fixture[2][0]["value"]["queries"][0]["binding"][field] = value
    refresh_metadata(fixture[0], fixture[2], fixture[3])
    result = consume(fixture)
    assert result["status"] == "partial" and result["facts"]["hits"] is None
    assert result["sheet"]["queries"][0]["normalized_result"]["search"]["reported_hit_count"] == 1
    assert "homology_query_input_member_conflict" in codes(result)


def test_existing_c4_query_binding_conflict_not_overridden():
    fixture = c4_fixture(program_document("blastp"), extras=False)
    binding = fixture[0]["input_bindings"][0]
    member = binding["members"][0]
    fixture[0]["query_bindings"] = [{"input_binding_id": binding["binding_id"], "input_source_ref": binding["content"]["source_ref"],
        "input_member_id": member["member_id"], "input_member_pointer": member["member_pointer"],
        **{k: member[k] for k in ("length", "molecule", "sequence_sha256")}, "raw_source_ref": fixture[0]["artifacts"][0]["source_ref"],
        "raw_report_ordinal": 0, "query_id": "SYNTHETIC-wrong-native-id", "query_title": "SYNTHETIC-query", "transformation_evidence": []}]
    result = consume(fixture)
    assert result["facts"]["hits"] is None
    assert "homology_c4_query_mapping_conflict" in codes(result)


def test_unknown_sequence_transform_and_no_pairwise_membership_are_not_inferred():
    fixture = c4_fixture(program_document("blastp"), mode="pairwise_correspondence", extras=False)
    fixture[2][0]["value"]["subject_binding"] = None
    fixture[2][0]["value"]["queries"][0]["binding"]["sequence_transform"]["kind"] = "unavailable"
    refresh_metadata(fixture[0], fixture[2], fixture[3])
    result = consume(fixture, {"pairs": {"metric": "pairwise_distinct_pairs", "report_index": 0}})
    assert result["status"] == "partial" and result["facts"]["pairs"] is None
    assert "homology_pairwise_subject_membership_unproved" in codes(result)
    assert result["sheet"]["queries"][0]["normalized_result"]["hits"][0]["hsps"][0]["bit_score"] == 20


def test_original_task_parameter_and_supplied_database_binding_conflicts_rejected():
    fixture = c4_fixture(program_document("blastp"), extras=False)
    fixture[2][0]["value"]["database_binding"]["requested_selection"]["db_type"] = "fna"
    refresh_metadata(fixture[0], fixture[2], fixture[3])
    result = consume(fixture)
    assert result["status"] == "invalid" and "homology_database_request_binding_conflict" in codes(result)
    fixture = c4_fixture(program_document("blastp"), extras=False)
    recorded = {"blast_program": "blastp", "blast_max_hits": 9, "db_type": "faa"}
    original = deepcopy(fixture[0]["original_task"])
    ev = evidence(recorded, source="SYNTHETIC-effective")
    fixture[0]["original_task"]["effective_parameters"] = {"value": recorded, "evidence": ev}
    result = consume(fixture)
    assert result["sheet"]["binding"]["original_task"]["effective_parameters"] == recorded
    assert result["sheet"]["binding"]["c4_bundle"]["original_task"]["effective_parameters"]["evidence"] == ev
    assert result["sheet"]["binding"]["original_task"]["submitted_parameters"] == original["submitted_parameters"]


def test_source_evidence_identity_and_extra_byte_inputs_checked_exactly():
    fixture = c4_fixture(program_document("blastp"), extras=False)
    fixture[2][0]["evidence"]["pointer"] = "/changed"
    # params and bundle share this fixture identity, so replace the supplied entry alone.
    fixture[2][0]["evidence"] = deepcopy(fixture[2][0]["evidence"])
    fixture[2][0]["evidence"]["content"]["sha256"] = "f" * 64
    result = consume(fixture)
    assert result["status"] == "invalid" and "homology_supplied_evidence_not_in_bundle" in codes(result)
    fixture = c4_fixture(program_document("blastp"), extras=False)
    fixture[1]["SYNTHETIC-unselected"] = b"unselected"
    result = consume(fixture)
    assert result["status"] == "invalid" and "homology_artifact_bytes_map_invalid" in codes(result)


def test_scientific_metadata_absence_never_makes_operational_bundle_scientific_completion():
    fixture = c4_fixture(program_document("blastp"), extras=False)
    fixture[3]["scientific_inputs"] = None
    result = consume(fixture)
    assert fixture[0]["status"] == "ok"
    assert result["status"] == "partial" and result["facts"]["hits"] is None
    assert result["sheet"]["queries"][0]["normalized_result"]["hits"]


def test_missing_header_no_fallback_and_tabular_native_counts_retained():
    fixture = c4_fixture()
    fixture[3]["primary_representation"] = "tabular"
    fixture[0]["artifacts"] = [a for a in fixture[0]["artifacts"] if a["role"] != "blast_tabular_header"]
    fixture[1].pop("SYNTHETIC-artifact-blast_tabular_header")
    result = consume(fixture)
    assert result["facts"]["hits"] is None and result["status"] == "partial"
    assert any(r["reason_code"] == "homology_tabular_header_and_fields_required" for r in result["missing_requirements"])
    fixture = c4_fixture()
    result = consume(fixture, {"mismatches": {"metric": "tabular_mismatch", "report_index": 0, "line": 4},
                               "opens": {"metric": "tabular_gapopen", "report_index": 0, "line": 4}})
    assert result["facts"] == {"mismatches": 1, "opens": 0}


def test_missing_and_malformed_sidecar_preserve_alignment_results():
    fixture = c4_fixture()
    artifact = next(a for a in fixture[0]["artifacts"] if a["role"] == "homology_metadata_json")
    content = b'{"duplicate": 1, "duplicate": 2}'
    fixture[1][artifact["raw_artifact_ref"]] = content
    artifact.update(sha256=hashlib.sha256(content).hexdigest(), byte_count=len(content))
    artifact["transfer"]["total_size"] = len(content)
    result = consume(fixture, {"alpha": {"metric": "conditional_function_weight", "report_index": 0, "function": F},
                               "coverage": {"metric": "query_paired_coverage", "report_index": 0, "hit_index": 0}})
    assert result["status"] == "partial" and result["facts"] == {"alpha": None, "coverage": .6}
    assert "homology_json_duplicate_key" in codes(result)


def test_supplied_taxonomy_source_quality_and_population_numbers_reach_projection():
    fixture = c4_fixture(extras=False)
    extra = fixture[2][0]["value"]["metadata"]
    first, second = source_record(0, F, taxid=562), source_record(1, G, taxid=562)
    for row in (first, second):
        row["lineage"] = [{"rank": "species", "taxid": 562}]
    first["assembly_measurements"] = {"completeness_fraction": .95, "source": "SYNTHETIC-quality",
        "measurement_units": {"completeness_fraction": "fraction"},
        "measurement_methods": {"completeness_fraction": "SYNTHETIC-marker"},
        "feature_to_genome_link": {"source_ref": "SYNTHETIC-feature", "pointer": "/genome_id",
            "genome_id": "999999.1", "feature_identifier": first["source_identifier"]}}
    extra["records"], extra["bindings"] = [first, second], [metadata_link(0), metadata_link(1, hit_index=1)]
    extra["target_context_by_query"] = [{"report_index": 0, "taxid": 562, "lineage": [{"rank": "species", "taxid": 562}],
        "source": "SYNTHETIC-target", "independent_of_search": True}]
    extra["database_profile"] = {"database": "SYNTHETIC_DATABASE_PATH", "release": None, "count_unit": "unique_sequences",
        "scope": "searched_database", "source": "SYNTHETIC-independent-population", "total_count": 100, "function_counts": {F: 80, G: 20}}
    refresh_metadata(fixture[0], fixture[2], fixture[3])
    result = consume(fixture, {"target": {"metric": "target_matching_fraction", "report_index": 0, "rank": "species"},
        "agreement": {"metric": "same_taxon_pair_fraction", "report_index": 0, "rank": "species"},
        "quality": {"metric": "source_quality_mean", "report_index": 0, "field": "completeness_fraction", "method": "SYNTHETIC-marker"},
        "population": {"metric": "database_function_fraction", "report_index": 0, "function": F},
        "adjusted": {"metric": "representation_adjusted_function_weight", "report_index": 0, "function": F}})
    assert result["facts"] == {"target": 1, "agreement": 1, "quality": .95, "population": .8, "adjusted": 1 / 3}


def test_source_collision_and_sequence_dependence_preserve_existing_calculators():
    fixture = c4_fixture(raw_document("synthetic_collision"), extras=False)
    extra = fixture[2][0]["value"]["metadata"]
    extra["records"] = [source_record(0, F), source_record(1, G)]
    extra["bindings"] = [metadata_link(0), metadata_link(1, hit_index=1)]
    extra["sequence_identity_bindings"] = [full_sequence_link(0), full_sequence_link(1)]
    refresh_metadata(fixture[0], fixture[2], fixture[3])
    result = consume(fixture, {"groups": {"metric": "sequence_group_count", "report_index": 0},
                               "alpha": {"metric": "conditional_function_weight", "report_index": 0, "function": F}})
    assert result["facts"] == {"groups": 2, "alpha": .5}
    assert len(result["sheet"]["queries"][0]["normalized_result"]["hits"]) == 3


def test_pure_consumption_and_saved_sheet_recalculation_no_io_or_mutation(monkeypatch):
    fixture = c4_fixture()
    before = deepcopy(fixture)
    def forbidden(*args, **kwargs):
        raise AssertionError("No filesystem, network, subprocess or model operation is allowed")
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    result = consume(fixture)
    sheet = json.loads(json.dumps(result["sheet"]))
    monkeypatch.setattr(adapter, "read_homology_raw_json", forbidden)
    monkeypatch.setattr(adapter, "build_homology_sheet", forbidden)
    recalculated = calculate_homology_scores(sheet, database_model={"temperature_bits": 1})
    assert recalculated["queries"][0]["conditional_function_weights"]["unadjusted_probabilities"] == {F: .8, G: .2}
    assert fixture == before and sheet == result["sheet"]


def test_implementation_pin_includes_real_dependency_bytes(monkeypatch):
    initial = adapter.implementation_sha256()
    original = Path.read_bytes
    def changed(path):
        content = original(path)
        return content + b"\n# test pin\n" if path.name == "blast_pairwise_grader.py" else content
    monkeypatch.setattr(Path, "read_bytes", changed)
    assert adapter.implementation_sha256() != initial


@pytest.mark.parametrize("selection", [
    {"metric": "anything", "report_index": 0},
    {"metric": "reported_hit_count", "report_index": False},
    {"metric": "reported_hit_count", "report_index": 0, "path": "/secret"},
    {"metric": "hsp_evalue", "report_index": 0, "hit_index": 0},
])
def test_projection_has_no_arbitrary_paths_prose_or_formula_language(selection):
    with pytest.raises(ContractValidationError):
        adapter.requested_form_schema({"value": selection})


def test_parameters_and_original_form_closed_and_extraneous_facts_disallowed():
    fixture = c4_fixture()
    fixture[3]["invented_formula"] = "eval(anything)"
    assert consume(fixture)["status"] == "invalid"
    schema = adapter.requested_form_schema({"count": {"metric": "reported_hit_count", "report_index": 0}})
    schema["additionalProperties"] = True
    with pytest.raises(ContractValidationError):
        adapter.validate_requested_form(schema)


def test_native_program_conflict_blocks_requested_fact_without_losing_measurements():
    fixture = c4_fixture(program_document("blastp"), extras=False)
    fixture[0]["original_task"]["submitted_parameters"]["blast_program"] = "blastx"
    result = consume(fixture)
    assert result["status"] == "partial" and result["facts"]["hits"] is None
    assert "homology_native_request_conflict" in codes(result)
    assert result["sheet"]["queries"][0]["normalized_result"]["hits"][0]["hsps"][0]["bit_score"] == 20


def test_native_database_conflict_and_mode_mismatch_do_not_silently_override():
    fixture = c4_fixture(program_document("blastp"), extras=False)
    fixture[2][0]["value"]["database_binding"]["effective_native_database"] = "SYNTHETIC-other-db"
    refresh_metadata(fixture[0], fixture[2], fixture[3])
    result = consume(fixture)
    assert result["facts"]["hits"] is None and "homology_native_database_conflict" in codes(result)
    result = consume(c4_fixture(program_document("blastp"), mode="pairwise_correspondence", extras=False),
        {"invalid~/selector": {"metric": "conditional_function_weight", "report_index": 0, "function": F}})
    assert result["status"] == "invalid" and "homology_fact_scientific_mode_conflict" in codes(result)


def test_wrong_application_and_incomplete_body_are_not_zero_hits():
    fixture = c4_fixture(program_document("blastp"), extras=False)
    fixture[0]["original_task"].update(required_application_id="GenomeAnnotation", native_application_id="GenomeAnnotation")
    result = consume(fixture)
    assert result["status"] == "invalid" and result["sheet"] is None
    fixture = c4_fixture(program_document("blastp"), extras=False)
    fixture[0]["artifacts"][0]["transfer"].update(body_complete=False, object_complete="no")
    result = consume(fixture)
    assert result["status"] == "partial" and result["facts"]["hits"] is None
    assert "homology_complete_object_required" in codes(result)


def test_invalid_supplied_metadata_collection_keeps_valid_alignment_and_source():
    fixture = c4_fixture(extras=False)
    fixture[2][0]["value"]["metadata"]["records"] = "SYNTHETIC invalid collection"
    refresh_metadata(fixture[0], fixture[2], fixture[3])
    result = consume(fixture, {"coverage": {"metric": "query_paired_coverage", "report_index": 0, "hit_index": 0},
                               "alpha": {"metric": "conditional_function_weight", "report_index": 0, "function": F}})
    assert result["status"] == "partial" and result["facts"] == {"coverage": .6, "alpha": None}
    assert "homology_supplied_metadata_shape_invalid" in codes(result)
    assert result["sheet"]["binding"]["supplied_values"] == fixture[2]


def test_invalid_metadata_locator_is_retained_without_invalid_c4_diagnostic():
    fixture = c4_fixture(extras=False)
    row = source_record(0, F)
    row["pointer"] = "not a JSON pointer~"
    fixture[2][0]["value"]["metadata"]["records"] = [row]
    refresh_metadata(fixture[0], fixture[2], fixture[3])
    result = consume(fixture)
    assert result["facts"]["hits"] == 3
    assert "homology_metadata_record_identity_invalid" in codes(result)
    for diagnostic in result["diagnostics"]:
        validate_contract("Diagnostic", diagnostic)


def test_transformation_provenance_missing_never_promotes_title_to_function():
    fixture = c4_fixture()
    for row in fixture[0]["artifacts"]:
        if row["role"] in {"blast_json15_raw", "homology_processed_json"}:
            row["declared_format"]["producer_source_ref"] = None
    result = consume(fixture, {"alpha": {"metric": "conditional_function_weight", "report_index": 0, "function": F},
                               "hits": {"metric": "reported_hit_count", "report_index": 0}})
    assert result["facts"] == {"alpha": None, "hits": 3}
    assert "homology_metadata_transformation_source_unavailable" in codes(result)


def test_malformed_independent_hsp_keeps_original_ordinals_and_valid_other_query():
    document = raw_document()
    hsps = document["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"]
    hsps[1] = None
    result = consume(c4_fixture(document, extras=False),
        {"paired": {"metric": "paired_columns", "report_index": 0, "hit_index": 0, "hsp_index": 2},
         "bad": {"metric": "paired_columns", "report_index": 0, "hit_index": 0, "hsp_index": 1},
         "other": {"metric": "reported_hit_count", "report_index": 1}})
    assert result["facts"] == {"paired": 4, "bad": None, "other": 0}
    loc = result["sheet"]["queries"][0]["normalized_result"]["hits"][0]["hsps"][2]["source_locator"]
    assert loc["hsp_index"] == 2 and loc["pointer"].endswith("/hits/0/hsps/2")


def test_reverse_translated_correspondence_and_original_map_limitation():
    doc = program_document("blastx")
    native = doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"][0]
    native.update(query_from=15, query_to=7, query_frame=-1, hit_from=2, hit_to=4)
    result = consume(c4_fixture(doc, extras=False),
        {"coverage": {"metric": "hsp_query_paired_coverage", "report_index": 0, "hit_index": 0, "hsp_index": 0}})
    assert result["facts"] == {"coverage": .6}
    pairs = result["components"]["alignment_supplements"]["queries"][0]["hits"][0]["hsps"][0]["alignment_components"]["pairs"]
    assert [[pair["query_start"], pair["query_end"]] for pair in pairs] == [[12, 15], [9, 12], [6, 9]]
    fixture = c4_fixture(extras=False)
    member = fixture[0]["input_bindings"][0]["members"][0]
    member.update(length=13, sequence_sha256="2" * 64)
    rich = fixture[2][0]["value"]["queries"][0]["binding"]
    rich.update(supplied_length=13, supplied_sequence_sha256="2" * 64)
    rich["sequence_transform"].update(kind="verified_fasta_normalization", coordinate_map_ref="SYNTHETIC-map")
    refresh_metadata(fixture[0], fixture[2], fixture[3])
    result = consume(fixture)
    assert result["facts"]["hits"] == 3
    assert result["components"]["alignment_supplements"]["queries"][0]["original_supplied_coordinate_projection"] == "unavailable"
    assert "homology_original_coordinate_map_content_unavailable" in codes(result)


def test_pairwise_evalue_never_changes_correspondence_relevance():
    doc = program_document("blastp")
    first = consume(c4_fixture(doc, mode="pairwise_correspondence", extras=False),
        {"identity": {"metric": "pairwise_identity", "report_index": 0},
         "coverage": {"metric": "pairwise_query_coverage", "report_index": 0}})
    doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"][0]["evalue"] = 1000000.0
    second = consume(c4_fixture(doc, mode="pairwise_correspondence", extras=False),
        {"identity": {"metric": "pairwise_identity", "report_index": 0},
         "coverage": {"metric": "pairwise_query_coverage", "report_index": 0}})
    assert first["facts"] == second["facts"] == {"identity": 1, "coverage": .6}


def test_opaque_archive_is_retained_without_decoder_or_scientific_mass():
    fixture = c4_fixture()
    row = deepcopy(fixture[0]["artifacts"][0])
    body = b"SYNTHETIC opaque archive bytes; no native archive producer was run"
    row.update(role="blast_archive", source_ref="SYNTHETIC-archive-source", raw_artifact_ref="SYNTHETIC-archive-artifact",
               sha256=hashlib.sha256(body).hexdigest(), byte_count=len(body))
    row["declared_format"]["format"] = "blast_archive"
    row["transfer"]["total_size"] = len(body)
    fixture[0]["artifacts"].append(row)
    fixture[1][row["raw_artifact_ref"]] = body
    result = consume(fixture)
    assert result["status"] == "ok" and result["facts"]["hits"] == 3
    archive = next(item for item in result["sheet"]["artifact_statuses"] if item["artifact"]["role"] == "blast_archive")
    assert archive["status"] == "complete" and archive["native_document"] is None
    assert "archive_decoder_not_provided" in archive["qualifications"]


def test_secondary_conflict_cannot_overwrite_explicit_primary_values():
    fixture = c4_fixture()
    row = next(a for a in fixture[0]["artifacts"] if a["role"] == "homology_processed_json")
    document = json.loads(fixture[1][row["raw_artifact_ref"]])
    document[0]["report"]["results"]["search"]["hits"][0]["hsps"][0]["bit_score"] = 99999
    body = encoded(document)
    fixture[1][row["raw_artifact_ref"]] = body
    row.update(sha256=hashlib.sha256(body).hexdigest(), byte_count=len(body))
    row["transfer"]["total_size"] = len(body)
    result = consume(fixture, {"bits": {"metric": "hsp_bit_score", "report_index": 0, "hit_index": 0, "hsp_index": 0}})
    assert result["facts"] == {"bits": 20}
    assert "homology_processed_transform_conflict" in codes(result)


def test_candidate_function_distribution_emerges_without_prespecified_labels():
    fixture = c4_fixture()
    selection = {"weights": {"metric": "conditional_function_weights", "report_index": 0}}
    result = consume(fixture, selection)
    assert result["status"] == "ok"
    assert result["facts"] == {"weights": [{"function": F, "weight": 2 / 3}, {"function": G, "weight": 1 / 3}]}
    assert F not in json.dumps(adapter.requested_form_schema(selection))
    assert "weights" not in consume(fixture)["facts"]
    assert result["components"]["queries"][0]["conditional_function_weights"]["calibrated_annotation_probability"] is False
    absent = consume(c4_fixture(extras=False), selection)
    assert absent["facts"] == {"weights": None} and absent["status"] == "partial"
    empty = consume(fixture, {"weights": {"metric": "conditional_function_weights", "report_index": 1}})
    assert empty["facts"] == {"weights": []} and empty["status"] == "ok"
    unknown_adjustment = consume(fixture,
        {"adjusted": {"metric": "representation_adjusted_function_weights", "report_index": 0}})
    assert unknown_adjustment["facts"] == {"adjusted": None} and unknown_adjustment["status"] == "partial"
    extra = fixture[2][0]["value"]["metadata"]
    extra["database_profile"] = {"database": "SYNTHETIC_DATABASE_PATH", "release": None, "count_unit": "unique_sequences",
        "scope": "searched_database", "source": "SYNTHETIC-independent-population", "total_count": 100, "function_counts": {F: 80, G: 20}}
    refresh_metadata(fixture[0], fixture[2], fixture[3])
    adjusted = consume(fixture, {"adjusted": {"metric": "representation_adjusted_function_weights", "report_index": 0}})
    assert adjusted["facts"] == {"adjusted": [{"function": F, "weight": 1 / 3}, {"function": G, "weight": 2 / 3}]}


def test_unproved_pairwise_reference_preserves_requested_native_counts_and_original_data():
    fixture = c4_fixture(program_document("blastx"), mode="pairwise_correspondence", extras=False)
    wrong_digest = hashlib.sha256(b"AAAAA").hexdigest()
    fixture[2][0]["value"]["subject_binding"]["sequence_sha256"] = wrong_digest
    refresh_metadata(fixture[0], fixture[2], fixture[3])
    original = deepcopy(fixture)
    result = consume(fixture, {
        "hits": {"metric": "reported_hit_count", "report_index": 0},
        "pairs": {"metric": "pairwise_distinct_pairs", "report_index": 0},
        "missing": {"metric": "missing_requirements"}})
    assert fixture == original
    assert result["status"] == "partial"
    assert result["facts"]["hits"] == 1
    assert result["facts"]["pairs"] is None
    assert "homology_subject_sequence_identity_conflict" in {row["reason_code"] for row in result["facts"]["missing"]}
    assert result["sheet"]["queries"][0]["normalized_result"]["hits"][0]["hsps"][0]["bit_score"] == 20
    assert result["sheet"]["binding"]["supplied_values"][0]["value"]["subject_binding"]["sequence_sha256"] == wrong_digest
    assert result["sheet"]["binding"]["subject_binding"] is None


def test_unrequested_pairwise_reference_problem_does_not_invalidate_actual_native_count():
    fixture = c4_fixture(program_document("blastx"), mode="pairwise_correspondence", extras=False)
    fixture[2][0]["value"]["subject_binding"]["sequence_sha256"] = hashlib.sha256(b"AAAAA").hexdigest()
    refresh_metadata(fixture[0], fixture[2], fixture[3])
    result = consume(fixture, {"hits": {"metric": "reported_hit_count", "report_index": 0},
        "missing": {"metric": "missing_requirements"}})
    assert result["facts"] == {"hits": 1, "missing": []}
    assert result["status"] == "ok"
    assert "homology_subject_sequence_identity_conflict" in codes(result)
    assert result["sheet"]["queries"][0]["blast_sheet"] is None
