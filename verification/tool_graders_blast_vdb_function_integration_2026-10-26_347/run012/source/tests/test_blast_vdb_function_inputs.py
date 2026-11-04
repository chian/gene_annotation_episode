"""Frozen338 numerical input examples; synthetic reports, no database execution."""
from copy import deepcopy
import builtins
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import blast_vdb_function_inputs as module
from gene_annotation_episode import blast_vdb_inputs as v1
from gene_annotation_episode import blast_vdb_calculators as base
from test_blast_vdb_inputs import collect, inputs, hsp, identity, provenance, entity, metadata, sequence, GBSEQ, binding
from test_blast_vdb_calculators import feature, table_values


def function(label, namespace="fixture_function"):
    return {"namespace": namespace, "value": label}


def member_key(member):
    return {k: deepcopy(member[k]) for k in ("dataset_key", "member_kind", "member_identifier")}


def explicit(values, hit=0, label="A", *, key=None, witness=None, namespace="fixture_function"):
    meta = next(m for m in values["reference_metadata"] if m["metadata_key"] == f"member{hit}")
    ordinal = len(meta["functions"])
    fn = function(label, namespace)
    meta["functions"].append(dict(function=fn, evidence=[], source=provenance(f"/functions/{hit}/{ordinal}")))
    return dict(assignment_key=key or f"assignment-{hit}-{ordinal}", function=fn, assignment_scope="whole_sequence",
        target=dict(member_key=member_key(values["member_bindings"][hit]), feature_identifier=None, sample_key=None),
        metadata_key=meta["metadata_key"], function_ordinal=ordinal, scope_origin="supplied_explicit_scope",
        scope_source=provenance(f"/scopes/{hit}/{ordinal}"), whole_sequence_cds_feature_identifier=witness,
        sources=[provenance(f"/scope-records/{hit}/{ordinal}")])


def whole_case():
    hits = [dict(len=8, description=[dict(id="a1", accession="a1")], hsps=[hsp(bit_score=22), hsp(bit_score=18)]),
            dict(len=8, description=[dict(id="a2", accession="a2")], hsps=[hsp(bit_score=21)]),
            dict(len=8, description=[dict(id="b1", accession="b1")], hsps=[hsp(r="ACGTTCGT", bit_score=20)])]
    values = inputs(collect(hits=hits)["searches"][0], symbols=["ACGTACGT", "ACGTACGT", "ACGTTCGT"])
    assignments = [explicit(values, 0), explicit(values, 1), explicit(values, 2, "B")]
    return values, assignments


def translated_case(*, siblings=False):
    symbols = ["CCCATGGCTAAACCCCCC", "TTTAGCCATAAA", "CAGACCCATCCC"]
    hsps = [[hsp("MAK", query_from=2, query_to=4, hit_from=4, hit_to=12, hit_frame=1, bit_score=30)],
            [hsp("MAK", query_from=2, query_to=4, hit_from=1, hit_to=9, hit_frame=-1, bit_score=29)],
            [hsp("MAK", "MGL", query_from=2, query_to=4, hit_from=1, hit_to=9, hit_frame=-1, bit_score=28)]]
    if siblings:
        hsps[0].extend([hsp("MAK", query_from=2, query_to=4, hit_from=4, hit_to=12, hit_frame=1, bit_score=27),
                       hsp("MAK", query_from=2, query_to=4, hit_from=4, hit_to=12, hit_frame=2, bit_score=40),
                       hsp("PMAKPP", hit_from=1, hit_to=18, hit_frame=1, bit_score=50)])
    hits = [dict(len=len(s), description=[dict(id=f"member{i}", accession=f"member{i}")], hsps=rows) for i, (s, rows) in enumerate(zip(symbols, hsps))]
    values = inputs(collect(program="tblastn_vdb", query="PMAKPP", hits=hits)["searches"][0], symbols=symbols, kind="reference")
    for i in range(3):
        feature(values, interval=[3, 12] if i == 0 else [0, 9], identifier=f"feature{i}", strand=1 if i == 0 else -1,
            translation="MAK" if i < 2 else "MGL", genetic_code=1, codon_start=1, function=function("A" if i < 2 else "B"), hit=i)
    return values


def feature_case(*, query_gap=False):
    rows = [hsp("AAAAAA", hit_from=13, hit_to=18, bit_score=18),
            hsp("A" * 30, bit_score=60), hsp("A" * 10, hit_from=31, hit_to=40, bit_score=25)]
    if query_gap:
        rows[1] = hsp("-" + "A" * 6, "A" * 7, query_to=6, hit_from=10, hit_to=16, bit_score=60)
    values = inputs(collect(query="A" * 40, hits=[dict(len=40, description=[dict(id="contig", accession="contig")], hsps=rows)])["searches"][0], symbols=["A" * 40], kind="reference")
    feature(values, interval=[10, 20], identifier="F", kind="misc_feature", function=function("A"))
    feature(values, interval=[30, 40], identifier="G", kind="misc_feature", function=function("B"))
    return values


def populate(values, assignments=(), dependencies=(), censuses=()):
    return module.populate_blast_vdb_function_sheet(v1.populate_blast_vdb_sheet(**values),
        supplied_assignments=list(assignments), dependency_records=list(dependencies), census_records=list(censuses))


def assigned(sheet, label=None):
    return [o for o in sheet["observations"] if o["function"] is not None and (label is None or o["function"]["value"] == label)]


def codes(sheet):
    return {i["code"] for i in sheet["issues"]}


def census_for(sheet, scope="whole_sequence", *, extra=True):
    base_sheet = sheet["base_sheet"]
    source = provenance("/enumeration", "synthetic:independent-census")
    digest = hashlib.sha256(b"supplied-fixture-annotation-snapshot").hexdigest()
    sequences = {m["sequence"]["sha256"]: m["sequence"]["symbols"] for m in base_sheet["reference_metadata"] if m["sequence"]}
    entities, proofs, bindings = [], [], []
    for row in sheet["entities"]:
        if row["address"]["assignment_scope"] != scope or row["target_identity"] is None:
            continue
        own = [a for a in sheet["assignment_records"] if a["assignment_key"] in row["assignment_keys"]]
        entities.append(dict(entity_key=row["entity_key"], address=deepcopy(row["address"]), target_identity=deepcopy(row["target_identity"]),
            parent_sequence_identity=deepcopy(row["parent_sequence_identity"]), functions=[deepcopy(a["function"]) for a in own],
            function_assignment_sources=[source], origin_sample_keys=deepcopy(row["origin_sample_keys"]),
            sample_relation_status=row["sample_relation_status"], source=source))
        parent = sequences[row["parent_sequence_identity"]["sha256"]]
        proofs.append(dict(entity_key=row["entity_key"], sequence_source=source, linkage_source=source, normalization="full_member_nt_v1", symbols=parent))
        if scope == "feature":
            feature_binding = next(f for f in base_sheet["feature_bindings"] if f["feature_identifier"] == row["address"]["feature_identifier"])
            from Bio.Seq import Seq
            fragment = "".join(parent[a:b] if feature_binding["strand"] == 1 else str(Seq(parent[a:b]).reverse_complement()) for a, b in feature_binding["segments"])
            proofs.append(dict(entity_key=row["entity_key"], sequence_source=source, linkage_source=source, normalization="oriented_feature_nt_v1", symbols=fragment))
        for a in own:
            bindings.append(dict(assignment_key=a["assignment_key"], census_entity_key=row["entity_key"], annotation_snapshot_sha256=digest, source=source))
    if extra and scope == "whole_sequence":
        for i, symbols in enumerate(["AACGTACG", "ACGTAACG", "ACGTACGA"]):
            seq = sequence(symbols); row = deepcopy(entities[0]); row["entity_key"] = f"census-extra-{i}"
            row["address"]["member_key"]["member_identifier"] = identity(f"extra{i}")
            row["target_identity"].update(sha256=seq["sha256"], length=seq["length"])
            row["parent_sequence_identity"] = {k: seq[k] for k in ("molecule", "sha256", "length")}
            entities.append(row)
            proofs.append(dict(entity_key=row["entity_key"], sequence_source=source, linkage_source=source, normalization="full_member_nt_v1", symbols=symbols))
    datasets = [dict(dataset_key=d["dataset_key"], identifier=deepcopy(d["identifier"]), snapshot=deepcopy(d["snapshot"]),
        selected_input=deepcopy(d["selected_input"]), sra_mode=d["search_context"]["sra_mode"], include_filtered_reads=d["search_context"]["include_filtered_reads"]) for d in base_sheet["dataset_records"]]
    return dict(census_key="census-1", assignment_scope=scope, function_namespace="fixture_function", scope="searched_population", datasets=datasets,
        annotation_snapshot=dict(identifier=identity("fixture-annotation", "snapshot"), content_sha256=digest, assignment_namespace="fixture_function", source=source),
        enumeration=dict(base_count_unit="member_instance" if scope == "whole_sequence" else "feature_instance", reported_total=len(entities), complete=True,
            pagination_complete=True, source=source, native_record={"fixture_kind": "synthetic_independent_full_enumeration"}),
        entities=entities, dependency_records=[], annotation_bindings=bindings, identity_proofs=proofs,
        source=source, native_record={"fixture_kind": "synthetic_independent_census"})


def test_frozen_whole_example_retains_all_native_measurements_and_duplicate_targets(monkeypatch):
    values, assignments = whole_case()
    original = v1.populate_blast_vdb_sheet(**values); saved = deepcopy(original)
    calculate = base.calculate_blast_vdb_components; calls = []
    def once(value):
        calls.append(deepcopy(value)); return calculate(value)
    monkeypatch.setattr(base, "calculate_blast_vdb_components", once)
    sheet = module.populate_blast_vdb_function_sheet(original, supplied_assignments=assignments, dependency_records=[], census_records=[])
    assert calls == [original] and original == saved and sheet["base_sheet"] == saved
    assert sheet["base_components"] == calculate(original)
    assert sheet["assignment_records"] == assignments
    assert [o["native_bit_score"]["value"] for o in assigned(sheet)] == [22, 18, 21, 20]
    assert all(o["paired_query_units"]["value"] == 8 and o["attributable_reference_nt"]["value"] == 8 for o in assigned(sheet))
    assert len(sheet["entities"]) == 3
    assert sheet["entities"][0]["target_identity"] == sheet["entities"][1]["target_identity"]
    assert sheet["entities"][0]["target_identity"] != sheet["entities"][2]["target_identity"]
    assert len([o for o in sheet["observations"] if o["assignment_key"] is None]) == 4
    assert sheet["base_components"]["population_components"]["function_weight_model"]["reason"] == "vdb_function_weight_model_not_defined"


@pytest.mark.parametrize("query_gap", [False, True])
def test_entire_hsp_is_required_for_feature_score_even_opposite_query_gap(query_gap):
    sheet = populate(feature_case(query_gap=query_gap))
    rows = assigned(sheet, "A")
    assert [r["qualification"] for r in rows] == ["available", "incompatible", "incompatible"]
    assert [r["native_bit_score"]["value"] for r in rows] == [18, 60, 25]
    assert rows[0]["attributable_reference_nt"]["value"] == 6
    assert rows[1]["aligned_reference_nt"]["value"] == (7 if query_gap else 30)
    assert rows[1]["attributable_reference_nt"]["value"] is None
    assert rows[1]["reason_code"] == "blast_vdb_function_hsp_not_contained_in_feature"
    assert assigned(sheet, "B")[2]["qualification"] == "available"
    assert all(a["assignment_scope"] == "feature" for a in sheet["assignment_records"])


def test_translated_opposite_strands_prove_one_target_and_keep_original_maps():
    sheet = populate(translated_case())
    rows = assigned(sheet)
    assert [r["native_bit_score"]["value"] for r in rows] == [30, 29, 28]
    assert all(r["qualification"] == "available" and r["paired_query_units"]["value"] == 3 and r["aligned_reference_nt"]["value"] == 9
               and r["corresponding_feature_residues"]["value"] == 3 for r in rows)
    features = [e for e in sheet["entities"] if e["address"]["assignment_scope"] == "feature"]
    assert features[0]["target_identity"] == features[1]["target_identity"]
    assert features[0]["parent_sequence_identity"] != features[1]["parent_sequence_identity"]
    maps = [f["translation_map"] for f in sheet["base_components"]["feature_components"]]
    assert [c["member_positions"] for c in maps[0]["codons"]] == [[3, 4, 5], [6, 7, 8], [9, 10, 11]]
    assert [c["member_positions"] for c in maps[1]["codons"]] == [[8, 7, 6], [5, 4, 3], [2, 1, 0]]
    assert not any(o["assignment_key"] is None and next(e for e in sheet["entities"] if e["entity_key"] == o["entity_key"])["address"]["assignment_scope"] == "whole_sequence" for o in sheet["observations"])


def test_valid_sibling_hsp_survives_wrong_frame_and_broad_hsp():
    sheet = populate(translated_case(siblings=True))
    rows = [o for o in assigned(sheet, "A") if o["row_key"]["hit_ordinal"] == 0]
    assert [o["native_bit_score"]["value"] for o in rows] == [30, 27, 40, 50]
    assert [o["qualification"] for o in rows] == ["available", "available", "unavailable", "incompatible"]
    assert rows[2]["reason_code"] == "blast_vdb_function_hsp_geometry_unavailable"
    assert sheet["base_components"]["feature_components"][0]["relation_status"] != "translated_correspondence"


@pytest.mark.parametrize("witness", [True, False])
def test_translated_whole_member_requires_explicit_whole_scope_and_full_coding_witness(witness):
    native = dict(len=9, description=[dict(id="whole", accession="whole")], hsps=[hsp("MAK", hit_to=9, hit_frame=1)])
    values = inputs(collect(program="tblastn_vdb", query="MAK", hits=[native])["searches"][0], symbols=["ATGGCTAAA"], kind="reference")
    feature(values, interval=[0, 9], identifier="whole-cds", translation="MAK", genetic_code=1, codon_start=1)
    assignment = explicit(values, witness=values["feature_bindings"][0]["feature_identifier"] if witness else None)
    sheet = populate(values, [assignment]); row = assigned(sheet)[0]
    assert row["qualification"] == ("available" if witness else "unavailable")
    assert (row["reason_code"] is None) == witness
    if not witness:
        assert "blast_vdb_function_coding_witness_missing" in codes(sheet)
    assert sheet["entities"][0]["target_identity"]["coding"] is None


@pytest.mark.parametrize("change,code", [
    (lambda v: v["reference_metadata"][0]["sequence"].update(symbols="AAAAAAAA"), "target_identity_conflict"),
    (lambda v: v["member_bindings"][0].update(relationship="catalog_membership"), "member_origin_unavailable"),
    (lambda v: v.update(query_binding=None), "query_binding_unavailable"),
    (lambda v: v["dataset_records"][0]["search_context"].update(query_extent=dict(mode="unknown", interval=None, source=None)), "query_binding_unavailable"),
])
def test_missing_or_conflicting_inputs_are_retained_scientific_qualifications(change, code):
    values, assignments = whole_case(); change(values)
    sheet = populate(values, assignments)
    assert "blast_vdb_function_" + code in codes(sheet)
    assert assigned(sheet)[0]["qualification"] != "available"
    assert assigned(sheet)[0]["native_bit_score"]["value"] == 22
    assert sheet["base_sheet"]["reference_metadata"] == values["reference_metadata"]


def test_reference_symbols_must_match_complete_member_at_original_orientation():
    hits = [dict(len=8, description=[dict(id="x", accession="x")], hsps=[hsp()])]
    values = inputs(collect(hits=hits)["searches"][0], symbols=["AAAAAAAA"])
    sheet = populate(values, [explicit(values)])
    assert "blast_vdb_function_hsp_sequence_conflict" in codes(sheet)
    assert assigned(sheet)[0]["native_bit_score"]["value"] == 20
    assert not sheet["entities"][0]["eligible_hsp_rows"]
    native = hsp("ACGTA", "ACGTA", hit_from=5, hit_to=1, hit_strand="Minus")
    values = inputs(collect(query="ACGTA", hits=[dict(len=5, description=[dict(id="x", accession="x")], hsps=[native])])["searches"][0], symbols=["TACGT"])
    assert assigned(populate(values, [explicit(values)]))[0]["qualification"] == "available"


def test_assignment_conflict_retains_both_records_without_source_order_winner():
    values, assignments = whole_case()
    duplicate = deepcopy(assignments[0]); duplicate["sources"].append(provenance("/second-proof"))
    sheet = populate(values, [assignments[0], duplicate, *assignments[1:]])
    assert len(sheet["assignment_records"]) == 3 and len(sheet["assignment_records"][0]["sources"]) == 2
    conflict = deepcopy(assignments[0]); conflict["function"] = function("Z")
    sheet = populate(values, [*assignments, conflict])
    assert len(sheet["assignment_records"]) == 4
    link = next(r for r in sheet["link_results"] if r["record_key"] == assignments[0]["assignment_key"])
    assert link["status"] == "incompatible" and len(link["input_pointers"]) == 2
    assert not any(o["assignment_key"] == assignments[0]["assignment_key"] for o in sheet["observations"])


@pytest.mark.parametrize("kind", ["wrong_entity", "wrong_function", "wrong_ordinal", "sample"])
def test_assignment_links_use_exact_metadata_entity_and_function_ordinal(kind):
    values, assignments = whole_case(); row = assignments[0]
    if kind == "wrong_entity":
        row["target"]["member_key"] = member_key(values["member_bindings"][2])
    elif kind == "wrong_function":
        row["function"] = function("unrelated")
    elif kind == "wrong_ordinal":
        row["function_ordinal"] = 99
    else:
        meta = next(m for m in values["reference_metadata"] if m["metadata_key"] == "sample0")
        meta["functions"] = deepcopy(values["reference_metadata"][0]["functions"])
        row.update(metadata_key="sample0", assignment_scope="sample", target=dict(member_key=None, feature_identifier=None, sample_key="S0"))
    sheet = populate(values, assignments)
    link = next(r for r in sheet["link_results"] if r["record_key"] == row["assignment_key"])
    expected = "assignment_entity_conflict" if kind == "wrong_entity" else "sample_assignment_not_query_function" if kind == "sample" else "assignment_function_conflict"
    assert link["reason_code"] == "blast_vdb_function_" + expected
    assert not any(o["assignment_key"] == row["assignment_key"] and o["qualification"] == "available" for o in sheet["observations"])


def test_matching_census_preserves_full_enumeration_and_all_source_proofs():
    values, assignments = whole_case(); first = populate(values, assignments); census = census_for(first)
    sheet = populate(values, assignments, censuses=[census])
    assert sheet["census_records"] == [census]
    assert sheet["link_results"][-1]["status"] == "available"
    assert len(census["entities"]) == 6
    assert len({e["target_identity"]["sha256"] for e in census["entities"]}) == 5


@pytest.mark.parametrize("change,reason", [
    (lambda c: c["enumeration"].update(complete=False), "census_partial"),
    (lambda c: c["enumeration"].update(pagination_complete=None), "census_partial"),
    (lambda c: c["enumeration"].update(reported_total=100), "census_count_conflict"),
    (lambda c: c["enumeration"].update(base_count_unit="feature_instance"), "census_unit_mismatch"),
    (lambda c: c["datasets"][0]["snapshot"].update(release="other"), "census_snapshot_mismatch"),
    (lambda c: c["datasets"][0].update(include_filtered_reads=True), "census_filter_mismatch"),
    (lambda c: c["datasets"][0]["selected_input"].update(value="other"), "census_scope_mismatch"),
    (lambda c: c.update(scope="supplied_subset"), "census_scope_mismatch"),
    (lambda c: c["annotation_bindings"][0].update(annotation_snapshot_sha256="f" * 64), "census_annotation_snapshot_mismatch"),
    (lambda c: c["identity_proofs"].pop(), "census_membership_unverified"),
    (lambda c: c.update(source=provenance("", "synthetic:report")), "census_membership_unverified"),
    (lambda c: c["entities"][2].update(functions=[]), "census_zero_conflict"),
])
def test_census_mismatches_keep_original_rows_and_specific_link_failure(change, reason):
    values, assignments = whole_case(); census = census_for(populate(values, assignments)); change(census)
    sheet = populate(values, assignments, censuses=[census])
    assert sheet["census_records"] == [census]
    assert "blast_vdb_function_" + reason in {i["code"] for i in sheet["link_results"][-1]["issues"]}
    assert sheet["link_results"][-1]["status"] != "available"
    assert all(o["qualification"] == "available" for o in assigned(sheet))


def test_feature_census_requires_separate_full_parent_and_oriented_target_proofs():
    values = translated_case(); census = census_for(populate(values), "feature", extra=False)
    sheet = populate(values, censuses=[census])
    assert sheet["link_results"][-1]["status"] == "available"
    assert len(census["identity_proofs"]) == 6
    census["identity_proofs"] = [p for p in census["identity_proofs"] if p["normalization"] == "oriented_feature_nt_v1"]
    sheet = populate(values, censuses=[census])
    assert sheet["link_results"][-1]["reason_code"] == "blast_vdb_function_census_membership_unverified"


def test_explicit_dependencies_are_retained_without_identity_or_weight_changes():
    values, assignments = whole_case(); original = populate(values, assignments)
    dependency = dict(dependency_key="same-library", relation="same_library", entities=[e["address"] for e in original["entities"]],
        sources=[provenance("/library-relation")], native_record={"explicit_library": "library1"})
    sheet = populate(values, assignments, [dependency])
    assert sheet["dependency_records"] == [dependency]
    assert sheet["entities"] == original["entities"] and sheet["observations"] == original["observations"]
    assert sheet["link_results"][-1]["status"] == "available"
    dependency["entities"][0]["member_key"]["member_identifier"] = identity("missing")
    assert populate(values, assignments, [dependency])["link_results"][-1]["reason_code"] == "blast_vdb_function_dependency_relation_unresolved"


def test_explicit_successful_zero_and_failed_empty_capture_remain_distinct():
    values = inputs(collect(hits=[])["searches"][0]); sheet = populate(values)
    assert sheet["base_components"]["status"] == "no_reported_hits"
    assert not sheet["entities"] and not sheet["observations"]
    values = inputs(collect(hits=[], completion=dict(native_returncode=1, producer_complete=False))["searches"][0])
    sheet = populate(values)
    assert sheet["base_components"]["status"] == "unavailable"
    assert "blast_vdb_function_base_source_unavailable" in codes(sheet)


def test_partial_output_keeps_original_hsp_ordinals_and_valid_sibling():
    native = dict(len=8, description=[dict(id="a", accession="a")], hsps=[hsp(bit_score=22), None, hsp(bit_score=18)])
    values = inputs(collect(hits=[native], completion=dict(native_returncode=1, producer_complete=False))["searches"][0])
    sheet = populate(values, [explicit(values)])
    assert [o["row_key"]["hsp_ordinal"] for o in assigned(sheet)] == [0, 2]
    assert [o["native_bit_score"]["value"] for o in assigned(sheet)] == [22, 18]
    assert all(o["qualification"] == "available" for o in assigned(sheet))
    assert sheet["base_sheet"]["search"]["native"]["search"]["hits"][0]["hsps"][1] is None


def test_saved_validation_never_calls_native_parser_base_calculator_or_population(monkeypatch):
    values, assignments = whole_case(); frozen = json.loads(json.dumps(populate(values, assignments)))
    before = deepcopy(frozen)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved validation invoked forbidden operation")
    for name in ("populate_blast_vdb_sheet", "parse_ncbi_sra_runinfo", "parse_blast_vdb_member_sequences", "parse_ncbi_gbseq_vdb_metadata", "bind_blast_vdb_metadata", "_recheck_metadata", "_reparse"):
        monkeypatch.setattr(v1, name, forbidden)
    monkeypatch.setattr(base, "calculate_blast_vdb_components", forbidden)
    monkeypatch.setattr(module, "populate_blast_vdb_function_sheet", forbidden)
    monkeypatch.setattr(module, "extract_blast_vdb_feature_function_assignments", forbidden)
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    output = module.validate_blast_vdb_function_sheet(frozen)
    assert output == before and frozen == before and output is not frozen
    output["base_sheet"]["reference_metadata"][0]["sequence"]["symbols"] = "CHANGED"
    assert frozen == before


@pytest.mark.parametrize("change", [
    lambda s: s.update(extra=1),
    lambda s: s["entities"][0].update(entity_key="forged"),
    lambda s: s["entities"][0]["target_identity"].update(sha256="f" * 64),
    lambda s: s["observations"][0]["native_bit_score"].update(value=999),
    lambda s: s["observations"][0].update(base_component_pointer="/base_components/hsps/999"),
    lambda s: s["observations"][0]["row_key"].update(hsp_ordinal=99),
    lambda s: s["observations"][0]["source_locator"].update(artifact_ref="forged"),
    lambda s: s["observations"][0]["paired_query_units"].update(value=True),
    lambda s: s["base_components"]["hsps"][0]["correspondence"]["columns"][0].update(reference_interval=[2, 3]),
    lambda s: s["base_components"]["hsps"][0]["native_components"]["native_scores"].update(bit_score=999),
    lambda s: s["link_results"][0].update(input_pointers=["/assignment_records/999"]),
    lambda s: s["entities"][0]["eligible_hsp_rows"].clear(),
    lambda s: s["assignment_records"][0].update(function_ordinal=True),
    lambda s: s["base_components"]["population_components"]["function_weight_model"].update(status="available"),
    lambda s: s["base_components"]["subjects"][0]["coordinate_context"]["query"].update(full_length=999),
    lambda s: s["base_components"]["subjects"][0]["coordinate_context"]["query"].update(effective_query_interval=[0, 999]),
    lambda s: s["base_components"]["subjects"][0].update(maximum_bit_score=999),
    lambda s: s["base_components"]["sample_groups"].update(observed_origin_sample_count=True),
    lambda s: s["base_components"]["sequence_groups"]["groups"][0]["subject_count"].update(value=True),
])
def test_saved_sheet_rejects_field_pointer_identity_measurement_and_source_tampering(change):
    values, assignments = whole_case(); saved = populate(values, assignments); change(saved)
    with pytest.raises(ValueError, match="^blast_vdb_function_(sheet_schema_invalid|record_fields_invalid|reference_out_of_range|record_key_duplicate)$"):
        module.validate_blast_vdb_function_sheet(saved)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), b"bytes", {1: "not a JSON object"}])
def test_nonfinite_or_non_json_inputs_raise_closed_structural_error(value):
    values, assignments = whole_case(); assignments[0]["sources"].append(value)
    with pytest.raises(ValueError, match="^blast_vdb_function_finite_json_required$"):
        populate(values, assignments)


def test_feature_extractor_retains_native_and_explicit_origin_without_title_inference():
    values = feature_case()
    extraction = module.extract_blast_vdb_feature_function_assignments(v1.populate_blast_vdb_sheet(**values))
    assert all(a["scope_origin"] == "supplied_explicit_scope" for a in extraction["records"])
    assert [a["function_ordinal"] for a in extraction["records"]] == [0, 0]
    assert all(a["assignment_scope"] == "feature" for a in extraction["records"])
    values, assignments = whole_case()
    assert module.extract_blast_vdb_feature_function_assignments(v1.populate_blast_vdb_sheet(**values))["records"] == []


def test_native_gbseq_feature_assignment_is_extracted_from_exact_bound_record():
    parsed = v1.parse_ncbi_gbseq_vdb_metadata(GBSEQ, source_ref="synthetic:gbseq", source_version=None)
    member_record, _, feature_record = parsed["records"]
    identifier = member_record["source_entity"]["member_identifier"]
    values = inputs(collect(program="tblastn_vdb", query="MAK", hits=[dict(len=18, description=[dict(id="NC_X.1", accession="NC_X.1")],
        hsps=[hsp("MAK", hit_from=4, hit_to=12, hit_frame=1)])])["searches"][0], symbols=["CCCATGGCTAAACCCCCC"], kind="reference", samples=False)
    member = values["member_bindings"][0]
    member["member_identifier"] = identifier; member["reference_identity"]["identifier"] = identifier
    feature_id = feature_record["source_entity"]["feature_identifier"]
    links = [binding(member_record, "member0", entity("member", dataset="D0", member=identifier), member=0),
             binding(feature_record, "feature:native", entity("feature", dataset="D0", member=identifier, feature=feature_id), parent="member0")]
    bound = v1.bind_blast_vdb_metadata([parsed], dataset_records=values["dataset_records"], member_bindings=values["member_bindings"],
        query_binding=values["query_binding"], bindings=links)
    values["reference_metadata"] = bound["reference_metadata"]
    values["feature_bindings"] = [dict(search_key=deepcopy(values["search"]["search_key"]), hit_ordinal=0, member_binding_index=0,
        member_identifier=identifier, feature_identifier=feature_id, feature_kind="CDS", member_interval=[3, 12], segments=[[3, 12]],
        location_status="exact", strand=1, genetic_code=1, codon_start=1, function=None, feature_sequence_sha256=None,
        translation_metadata_key="feature:native", provenance=provenance("/exact-feature-link"))]
    sheet = populate(values)
    assert len(sheet["assignment_records"]) == 2
    assert all(a["scope_origin"] == "native_feature_record" for a in sheet["assignment_records"])
    assert all(o["qualification"] == "available" for o in assigned(sheet))
    assert [a["function_ordinal"] for a in sheet["assignment_records"]] == [0, 1]
    assert sheet["base_sheet"]["reference_metadata"][1]["native_record"]["input_text"] == GBSEQ.decode()


@pytest.mark.parametrize("filename", ["whole_sequence.json", "translated_features.json", "translated_siblings.json"])
def test_complete_frozen_fixtures_validate_without_base_recalculation(filename, monkeypatch):
    path = Path(__file__).resolve().parents[1] / "verification/tool_graders_blast_vdb_function_inputs_2026-10-26_342/fixtures_001" / filename
    frozen = json.loads(path.read_text())
    def forbidden(*args, **kwargs):
        raise AssertionError("frozen validation must consume saved values")
    monkeypatch.setattr(base, "calculate_blast_vdb_components", forbidden)
    monkeypatch.setattr(v1, "populate_blast_vdb_sheet", forbidden)
    monkeypatch.setattr(v1, "_reparse", forbidden)
    monkeypatch.setattr(v1, "_recheck_metadata", forbidden)
    monkeypatch.setattr(module, "populate_blast_vdb_function_sheet", forbidden)
    monkeypatch.setattr(module, "extract_blast_vdb_feature_function_assignments", forbidden)
    assert module.validate_blast_vdb_function_sheet(frozen) == frozen


def test_saved_eligible_observation_cannot_disappear_with_its_entity_index():
    values, assignments = whole_case(); saved = populate(values, assignments)
    row = next(o for o in saved["observations"] if o["assignment_key"] is None)
    saved["observations"].remove(row)
    target = next(e for e in saved["entities"] if e["entity_key"] == row["entity_key"])
    target["eligible_hsp_rows"].remove(row["row_key"])
    with pytest.raises(ValueError, match="^blast_vdb_function_reference_out_of_range$"):
        module.validate_blast_vdb_function_sheet(saved)


def test_literal_feature_assignment_cannot_be_removed_with_all_derived_links():
    saved = populate(translated_case())
    saved["assignment_records"] = []
    saved["link_results"] = []
    saved["observations"] = [o for o in saved["observations"] if o["assignment_key"] is None]
    for entity_row in saved["entities"]:
        entity_row["assignment_keys"] = []
    with pytest.raises(ValueError, match="^blast_vdb_function_reference_out_of_range$"):
        module.validate_blast_vdb_function_sheet(saved)


def test_original_hsp_cannot_disappear_from_base_and_all_derived_indices():
    values, assignments = whole_case(); saved = populate(values, assignments)
    row = saved["base_components"]["hsps"].pop()["row_key"]
    saved["base_components"]["subjects"][-1]["hsp_row_keys"] = []
    saved["base_components"]["membership"]["row_keys"]["hits"][-1]["hsps"] = []
    saved["observations"] = [o for o in saved["observations"] if o["row_key"] != row]
    saved["entities"][-1]["eligible_hsp_rows"] = []
    with pytest.raises(ValueError, match="^blast_vdb_function_reference_out_of_range$"):
        module.validate_blast_vdb_function_sheet(saved)


@pytest.mark.parametrize("mutation,reason", [
    (lambda h: h.pop("bit_score"), "hsp_score_missing"),
    (lambda h: h.pop("qseq"), "hsp_geometry_unavailable"),
    (lambda h: h.update(hit_to=7), "hsp_geometry_unavailable"),
])
def test_missing_native_measurement_qualifies_only_the_original_affected_hsp(mutation, reason):
    first = hsp(bit_score=22); mutation(first)
    values = inputs(collect(hits=[dict(len=8, description=[dict(id="x", accession="x")], hsps=[first, hsp(bit_score=18)])])["searches"][0])
    sheet = populate(values, [explicit(values)])
    rows = assigned(sheet)
    assert rows[0]["qualification"] == "unavailable"
    assert "blast_vdb_function_" + reason in {i["code"] for i in rows[0]["issues"]}
    assert rows[1]["qualification"] == "available" and rows[1]["native_bit_score"]["value"] == 18
    assert sheet["base_sheet"]["search"]["native"]["search"]["hits"][0]["hsps"][0] == first


@pytest.mark.parametrize("conflict", [False, True])
def test_census_repeated_representation_proofs_keep_sources_and_conflicts(conflict):
    values = translated_case(); census = census_for(populate(values), "feature", extra=False)
    repeated = deepcopy(census["identity_proofs"][0])
    repeated["sequence_source"] = provenance("/independent-proof", "synthetic:other-census-proof")
    if conflict:
        repeated["symbols"] = "A" * len(repeated["symbols"])
    census["identity_proofs"].append(repeated)
    census["annotation_bindings"].append(dict(census["annotation_bindings"][0], source=provenance("/second-annotation-proof")))
    sheet = populate(values, censuses=[census])
    assert sheet["census_records"][0] == census
    assert sheet["link_results"][-1]["status"] == ("incompatible" if conflict else "available")


def test_wrong_declared_proof_identity_is_incompatible_not_missing():
    values, assignments = whole_case(); census = census_for(populate(values, assignments))
    census["identity_proofs"][0]["symbols"] = "AAAAAAAA"
    sheet = populate(values, assignments, censuses=[census])
    assert sheet["link_results"][-1]["status"] == "incompatible"
    assert sheet["link_results"][-1]["reason_code"] == "blast_vdb_function_census_membership_unverified"


def test_tabular_original_row_and_line_remain_exact_after_invalid_native_sibling():
    values = table_values(); sheet = populate(values, [explicit(values)])
    row = assigned(sheet)[0]
    assert row["qualification"] == "available" and row["row_key"]["hsp_ordinal"] == 1
    assert row["source_locator"]["line_numbers"] == [5] and row["source_locator"]["data_row_ordinals"] == [1]
    assert module.validate_blast_vdb_function_sheet(json.loads(json.dumps(sheet))) == sheet
    row["source_locator"]["line_numbers"] = [4]
    sheet["base_components"]["hsps"][0]["source_locator"]["line_numbers"] = [4]
    with pytest.raises(ValueError, match="^blast_vdb_function_reference_out_of_range$"):
        module.validate_blast_vdb_function_sheet(sheet)


@pytest.mark.parametrize("failure", ["missing_layout", "source_conflict", "entirely_malformed"])
def test_base_source_failure_is_retained_without_fabricating_empty_success(failure):
    values = table_values() if failure == "missing_layout" else inputs()
    if failure == "missing_layout":
        values["search"]["normalized"]["native"].pop("table_layout")
    elif failure == "source_conflict":
        values["report_source"]["artifact_key"] = "wrong-source"
    else:
        values["search"] = collect(hits=[None])["searches"][0]
    sheet = populate(values)
    assert not sheet["observations"]
    assert sheet["base_components"]["status"] == ("incompatible" if failure == "source_conflict" else "unavailable")
    assert module.validate_blast_vdb_function_sheet(sheet) == sheet


@pytest.mark.parametrize("field", ["snapshot", "sra_mode", "include_filtered_reads"])
def test_unknown_selected_population_context_is_unavailable_not_a_matching_wildcard(field):
    values, assignments = whole_case(); census = census_for(populate(values, assignments))
    if field == "snapshot":
        values["dataset_records"][0][field] = dict(release=None, snapshot_id=None, manifest_sha256=None)
    else:
        values["dataset_records"][0]["search_context"][field] = None
    sheet = populate(values, assignments, censuses=[census])
    assert sheet["link_results"][-1]["status"] == "unavailable"
    assert sheet["census_records"] == [census]


def test_conflicting_observed_census_membership_is_incompatible():
    values, assignments = whole_case(); census = census_for(populate(values, assignments))
    census["entities"][0]["target_identity"] = deepcopy(census["entities"][2]["target_identity"])
    census["entities"][0]["parent_sequence_identity"] = deepcopy(census["entities"][2]["parent_sequence_identity"])
    census["identity_proofs"][0]["symbols"] = census["identity_proofs"][2]["symbols"]
    sheet = populate(values, assignments, censuses=[census])
    assert sheet["link_results"][-1]["status"] == "incompatible"
    assert sheet["link_results"][-1]["reason_code"] == "blast_vdb_function_census_membership_unverified"


def test_saved_feature_component_requires_its_original_feature_binding():
    sheet = populate(translated_case())
    sheet["base_components"]["feature_components"][0]["feature_binding_indices"] = []
    with pytest.raises(ValueError, match="^blast_vdb_function_reference_out_of_range$"):
        module.validate_blast_vdb_function_sheet(sheet)
