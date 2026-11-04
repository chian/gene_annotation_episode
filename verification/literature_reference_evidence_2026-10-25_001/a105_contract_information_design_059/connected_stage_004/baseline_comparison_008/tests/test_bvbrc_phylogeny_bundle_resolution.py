"""Synthetic C4 shapes exercise actual pure readers; no custody/live claim."""
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode import bvbrc_phylogeny_bundle_contracts as c
from gene_annotation_episode import bvbrc_phylogeny_bundle_resolution as r
from gene_annotation_episode.bvbrc_appservice_contracts import ContractValidationError, validate_contract


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def evidence(value, name="scientific", pointer=""):
    data = encoded(value)
    return {"content": {"source_ref": "SYNTHETIC-source/" + name, "artifact_field": "artifact_ref",
        "artifact_ref": "SYNTHETIC-artifact/" + name, "sha256": hashlib.sha256(data).hexdigest(), "byte_count": len(data)}, "pointer": pointer}


def slot(sid, aid="a", tree=False, index=0):
    return {"analysis_id": aid, "slot_id": sid, **({"tree_index": index} if tree else {})}


def fixture(provider="gene_tree", *, alignment=b">A\nA-CX\n>B\nATCX\n>C\nATGX\n>D\nAT-X\n", tree=b"((A:0,B:0.2)75:0.3,(C:-0.1,D:0.4):0.2);", aid="a"):
    app = "GeneTree" if provider == "gene_tree" else "CodonTree"
    mode = "gene_tree" if provider == "gene_tree" else "core_genome_codon_protein"
    analysis = {"analysis_id": aid, "mode": mode, "raw_tree_id": slot("tree", aid, True), "phyloxml_tree_id": None,
        "native_engine_slots": [], "output_role_evidence": []}
    if provider == "gene_tree":
        analysis.update(locus_ids=[], aligned_document_id=slot("alignment", aid))
        read_parameters = {"source_dialect": "retained_bvbrc_gene_tree", "raw_tree_required_for_branch_facts": False}
    else:
        analysis.update({key: None for key in c.CODON_DOCUMENT_FIELDS + c.CODON_TREE_FIELDS if key not in analysis})
        analysis.update(final_alignment_id=slot("alignment", aid), per_family_final_alignment_ids=[], explicit_family_matrix_id=None)
        read_parameters = {"source_dialect": "retained_codon_trees", "membership_dialect": "pgfams_legacy", "family_stats_dialect": None}
    calculation = {"version": provider + "_components_v1", **{key: [] for key in c.COMMON_CALCULATION_FIELDS}}
    calculation["alignment_requests"] = [{"population_id": "matrix", "alphabet": "protein", "case_policy": "uppercase", "pairs": [[0, 1]]}]
    calculation["tree_requests"] = [{"population_id": "leaves", "branch_unit": "native_unknown", "pairs": [[2, 3]]}]
    if provider == "codon_tree":
        calculation.update(literal_statistic_population_ids=["matrix"], family_population_requests=[], worst_sequence_population_id=None)
    plan = {"analysis": analysis, "population_plans": [
        {"kind": "whole_alignment", "population_id": "matrix", "alignment": slot("alignment", aid)},
        {"kind": "whole_tree", "population_id": "leaves", "tree": slot("tree", aid, True)}],
        "scientific_inputs": None, "read_parameters": read_parameters, "calculation_parameters": calculation}
    params = {"version": c.PARAMETERS_VERSION, "artifact_selection": [], "analyses": [plan]}
    bundle = {"version": "bvbrc_appservice_artifact_bundle_v1", "original_task": {"resource_id": "SYNTHETIC-service",
        "task_id": "SYNTHETIC-task", "required_application_id": app, "native_application_id": app,
        "submitted_parameters": {}, "submitted_start_parameters": {}, "scheduler_returned_parameters": None, "effective_parameters": None,
        "submission_receipt_ref": "SYNTHETIC-submit", "submission_operation_key": "SYNTHETIC:launch:0", "submission_source_ref": "SYNTHETIC-submit-source"},
        "artifacts": [], "input_bindings": [], "query_bindings": [], "supplied_scientific_metadata": [],
        "acquisition_receipt_refs": [], "requested_selector_sha256": "e" * 64,
        "status": "ok", "missing_requirements": [], "diagnostics": []}
    content, values = {}, []
    result = (bundle, content, values, params)
    add_artifact(result, "alignment", alignment, {"reader": "aligned_fasta", "id_rule": "first_whitespace_token", "encoding": "ascii"}, aid=aid)
    add_artifact(result, "tree", tree, {"reader": "newick", "dialect": "newick", "allow_multiple": True}, aid=aid)
    scientific = r._empty_scientific(aid, provider)
    alphabet = evidence({"alphabet": "protein"}, aid + "-alphabet")
    scientific["observed_run"]["settings"] = [{"name": "alphabet", "value": "protein", "origin": "observed", "evidence": [alphabet], "location": None}]
    supply(result, scientific, aid=aid)
    validate_contract("ArtifactBundle", bundle)
    return result


def add_artifact(fixture, sid, data, reader, *, aid="a"):
    bundle, content, _, params = fixture
    ident = aid + "/" + sid; raw = "SYNTHETIC-native/" + ident; role = aid + ":" + sid
    row = {"role": role, "source_ref": "SYNTHETIC-source/" + ident, "raw_artifact_ref": raw,
        "sha256": hashlib.sha256(data).hexdigest(), "byte_count": len(data),
        "workspace_object": {"path": "/SYNTHETIC/" + ident, "uuid": "SYNTHETIC-object/" + ident, "type": "file", "metadata_receipt_ref": None},
        "task_association": {"kind": "task_info_folder_member", "evidence_ref": "SYNTHETIC-folder", "pointer": "/members",
            "task_id": bundle["original_task"]["task_id"], "output_path": "/SYNTHETIC/" + ident, "output_uuid": None,
            "byte_version_status": "current_bytes_observed", "version_evidence": []},
        "transfer": {"receipt_ref": "SYNTHETIC-acquisition/" + ident, "body_complete": True, "requested_range": None,
            "observed_range": None, "total_size": len(data), "object_complete": "yes"},
        "declared_format": {"format": reader["reader"], "version": reader.get("dialect"),
            "mode": next(p["analysis"]["mode"] for p in params["analyses"] if p["analysis"]["analysis_id"] == aid),
            "producer_source_ref": None, "transformation_evidence": []}}
    params["artifact_selection"].append({"analysis_id": aid, "slot_id": sid, "role": role, "reader": reader})
    bundle["artifacts"].append(row); bundle["acquisition_receipt_refs"].append(row["transfer"]["receipt_ref"]); content[raw] = data
    return row


def supply(fixture, scientific, *, aid="a"):
    bundle, _, values, params = fixture
    ev = evidence(scientific, aid + "-scientific")
    plan = next(p for p in params["analyses"] if p["analysis"]["analysis_id"] == aid)
    old = plan["scientific_inputs"]
    if old is not None:
        values[:] = [v for v in values if v["evidence"] != old]
        bundle["supplied_scientific_metadata"][:] = [e for e in bundle["supplied_scientific_metadata"] if e != old]
    plan["scientific_inputs"] = ev
    bundle["supplied_scientific_metadata"].append(ev); values.append({"evidence": ev, "value": scientific})


def resolve(fixture, provider="gene_tree"):
    b, data, values, params = fixture
    return r.resolve_bundle(b, artifact_bytes=data, supplied_values=values, parameters=params, provider=provider)


def supplemental(fixture, *, data=b"((A,B),(C,D));", sid="reference", claim=None):
    b, content, values, params = fixture
    aid = params["analyses"][0]["analysis"]["analysis_id"]
    binding = {"source_ref": "SYNTHETIC-external/" + sid, "artifact_field": "artifact_ref", "artifact_ref": "SYNTHETIC-external-raw/" + sid,
               "sha256": hashlib.sha256(data).hexdigest(), "byte_count": len(data)}
    ref = {"raw_artifact_ref": binding["artifact_ref"], "source_ref": binding["source_ref"], "sha256": binding["sha256"]}
    spec = {"reader": "newick", "dialect": "newick", "allow_multiple": False}
    read = {"read_id": "SYNTHETIC-external-read/" + sid, "artifact": ref, "reader": spec,
            "result": r.parse_reader(data, artifact=ref, spec=spec) if claim is None else claim}
    scientific = deepcopy(values[0]["value"])
    scientific["supplemental_documents"].append({"slot_id": sid, "role": "organismal-reference", "read": read, "evidence": []})
    b.setdefault("supplied_contents", []).append(binding); content[binding["artifact_ref"]] = data
    supply(fixture, scientific, aid=aid)
    return read


def test_materializes_fixed_fields_preserves_originals_and_unknown_native_semantics():
    f = fixture(); before = deepcopy(f); resolved = resolve(f)
    operands = resolved.analysis_operands(f[3]["analyses"][0])
    assert f == before
    analysis = operands["documents"]["parsed"]["analyses"][0]
    assert analysis["aligned_document_id"].endswith("#alignment") and analysis["raw_tree_id"].endswith("/tree/0")
    assert len(operands["documents"]["reads"]) == 2
    assert operands["assembly"]["caller_populations"]["alignments"][0]["row_indices"] == [0, 1, 2, 3]
    assert {d["code"] for d in resolved.diagnostics["a"]} >= {"output_version_unproven", "output_association_unproven"}


@pytest.mark.parametrize("kind", ["task_result_manifest", "task_info_object", "task_info_folder_member", "unverified_original_path"])
def test_all_c4_task_associations_keep_their_qualified_meanings(kind):
    f = fixture()
    for artifact in f[0]["artifacts"]:
        association = artifact["task_association"]; association["kind"] = kind
        if kind in ("task_result_manifest", "task_info_object"):
            association["output_uuid"] = artifact["workspace_object"]["uuid"]
    resolved = resolve(f)
    assert all(s["state"] == "resolved" for s in resolved.selections.values())


def test_repeat_canonical_receipt_aliases_and_ambiguous_different_object():
    f = fixture(); original = f[0]["artifacts"][0]; alias = deepcopy(original)
    alias.update(source_ref="SYNTHETIC-alias", raw_artifact_ref="SYNTHETIC-alias-raw")
    alias["transfer"]["receipt_ref"] = "000-canonical"
    f[1][alias["raw_artifact_ref"]] = f[1][original["raw_artifact_ref"]]
    f[0]["artifacts"].append(alias); f[0]["acquisition_receipt_refs"].append("000-canonical")
    a = resolve(f); selected = a.selections[("a", "alignment")]
    assert len(selected["artifact_refs"]) == 2 and len(selected["acquisition_receipt_refs"]) == 2
    assert selected["document_id"] == "SYNTHETIC-alias-raw#alignment"
    f[0]["artifacts"].reverse()
    assert resolve(f).selections[("a", "alignment")]["document_id"] == selected["document_id"]
    alias["workspace_object"]["uuid"] = "DIFFERENT-object"
    assert resolve(f).selections[("a", "alignment")]["state"] == "ambiguous"


@pytest.mark.parametrize("missing", [False, True])
def test_every_repeated_alias_needs_its_actual_matching_bytes(missing):
    f = fixture(); alias = deepcopy(f[0]["artifacts"][0])
    alias.update(source_ref="SYNTHETIC-alias", raw_artifact_ref="SYNTHETIC-alias-raw")
    alias["transfer"]["receipt_ref"] = "zzz-noncanonical"
    f[0]["artifacts"].append(alias); f[0]["acquisition_receipt_refs"].append("zzz-noncanonical")
    if not missing:
        f[1][alias["raw_artifact_ref"]] = b"tampered alias"
    resolved = resolve(f)
    assert resolved.selections[("a", "alignment")]["state"] == "invalid"
    assert resolved.selections[("a", "tree")]["state"] == "resolved"


@pytest.mark.parametrize("reverse", [False, True])
def test_same_bytes_with_incompatible_parser_specs_invalidates_every_slot(reverse):
    f = fixture(); tree = f[1]["SYNTHETIC-native/a/tree"]
    add_artifact(f, "tree-again", tree, {"reader": "newick", "dialect": "newick", "allow_multiple": False})
    if reverse:
        f[3]["artifact_selection"].reverse()
    resolved = resolve(f)
    assert all(resolved.selections[("a", sid)]["state"] == "invalid" for sid in ("tree", "tree-again"))
    assert all(("a", sid) not in resolved.reads for sid in ("tree", "tree-again"))
    assert resolved.selections[("a", "alignment")]["state"] == "resolved"


def test_forest_indices_refer_to_original_source_order():
    f = fixture(tree=b"(A:0,B:1); (broken; (C:2,D:3);")
    resolved = resolve(f)
    read = resolved.reads[("a", "tree")]
    assert [t["tree_index"] for t in r._trees(read)] == [0, 2]
    with pytest.raises(r._Unavailable):
        resolved.value(slot("tree", tree=True, index=1), tree=True)
    assert resolved.value(slot("tree", tree=True, index=2), tree=True)["tree_index"] == 2


def test_supplemental_exact_bytes_required_and_forged_parsed_claim_rejected(monkeypatch):
    f = fixture(); read = supplemental(f)
    original = r.parse_reader; calls = []
    def observed(*args, **kwargs):
        calls.append(kwargs["artifact"]["raw_artifact_ref"])
        return original(*args, **kwargs)
    monkeypatch.setattr(r, "parse_reader", observed)
    resolved = resolve(f)
    assert resolved.selections[("a", "reference")]["state"] == "resolved"
    assert calls.count(read["artifact"]["raw_artifact_ref"]) == 1
    f[2][0]["value"]["supplemental_documents"][0]["read"]["result"]["value"]["trees"][0]["nodes"][1]["decoded_label"] = "FORGED"
    supply(f, f[2][0]["value"])
    forged = resolve(f)
    assert forged.selections[("a", "reference")]["state"] == "invalid"
    assert any(q["reason_code"] == "supplemental_parsed_claim_conflict" for q in forged.requirements["a"])
    assert forged.selections[("a", "tree")]["state"] == "resolved"
    del f[1][read["artifact"]["raw_artifact_ref"]]
    missing = resolve(f)
    assert any(q["reason_code"] == "supplemental_native_content_required" for q in missing.requirements["a"])


def test_wrong_task_and_wrong_hash_do_not_establish_output_association():
    f = fixture(); f[0]["original_task"]["native_application_id"] = "CodonTree"
    with pytest.raises(ContractValidationError):
        resolve(f)
    f = fixture(); f[1][f[0]["artifacts"][0]["raw_artifact_ref"]] = b"wrong bytes"
    resolved = resolve(f)
    assert resolved.selections[("a", "alignment")]["state"] == "invalid"
    assert resolved.selections[("a", "tree")]["state"] == "resolved"
