"""Synthetic source extractions check condition identity, not biological truth."""
import json
from pathlib import Path

from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.domain import REASONING_SCHEMA
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.runtime import _action_generation_schema
from gene_annotation_episode.state import Store


TEXT = "construct A was assayed in M9 with 5% LB at 30 C. Growth was observed."


def payload():
    return {key: [] for key in REASONING_SCHEMA["properties"]}


def setup(tmp_path):
    store = Store(tmp_path)
    store.create_problem(raw_sequence="ATGAAATAA", molecule="dna", role="gene")
    artifact = store.artifact(TEXT, "text/plain")
    source = store.put("source", {"provider": "synthetic_condition_fixture", "accession": None,
        "uri": None, "artifact_ref": artifact, "text_ref": None, "request_ref": None,
        "version": None, "retrieved_at": None}, origin="external")
    anchor = {"source_ref": source["id"], "artifact_ref": artifact, "start": 0,
              "end": len(TEXT.encode()), "quote": TEXT}
    return store, source, anchor


def contexts(source, anchor):
    data = payload()
    data["source_subjects"] = [{"alias": "construct", "reference_type": "construct",
        "source_ref": source["id"], "label": "construct A", "anchor": anchor}]
    data["contexts"] = [{"alias": "medium", "context_type": "assay_condition",
        "name": "M9 with 5% LB", "source_ref": source["id"], "anchor": anchor,
        "attributes": [{"name": "temperature", "value": {"type": "number", "value": 30, "unit_ref": None}}],
        "related_refs": ["@construct"]}]
    return data


def test_source_condition_retains_actual_entity_and_is_used_by_the_existing_reasoning_call(tmp_path):
    store, source, anchor = setup(tmp_path / "state")
    with store:
        data = contexts(source, anchor)
        data["observations"] = [{"alias": "growth", "kind": "growth_assay",
            "subject_refs": ["@construct"], "source_subject_refs": ["@construct"],
            "source_ref": source["id"], "anchor": anchor, "dependencies": ["@medium"],
            "measurements": [{"name": "observed_growth", "value": {"type": "enum", "value": "growth"}}]}]
        result = store.commit_reasoning(data, store.validate_scope(None), "source-conditions")
        assert result["status"] == "completed", result
        condition = store.get(result["aliases"]["medium"])
        observation = store.get(result["aliases"]["growth"])
        assert condition["origin"] == "extracted" and condition["anchor"] == anchor
        assert condition["related_refs"] == [result["aliases"]["construct"]]
        assert condition["related_refs"] != store.problem()["subject_refs"]
        assert observation["dependencies"] == [condition["id"]]
        assert observation["source_subject_refs"] == [result["aliases"]["construct"]]
        assert project_credit(store).credit == 0  # acquisition/extraction is not an annotation
        assert store.commit_reasoning(data, store.validate_scope(None), "source-conditions") == result
        # Link the condition through an explicitly unresolved, transferred
        # interpretation. This fixture tests provenance/closure, not a claim
        # that a short DNA fragment's physiological role was established.
        interpretation = payload()
        target = store.problem()["subject_refs"][0]
        interpretation["hypotheses"] = [{"alias": "role", "subject_refs": [target],
            "predicate": "growth_capability", "value": {"type": "enum", "value": "growth"},
            "context_refs": [condition["id"]]}]
        interpretation["assessments"] = [{"extent_basis": "inferred_extent", "alias": "assessment", "hypothesis_ref": "@role",
            "observation_ref": observation["id"], "relation": "mixed", "applicability": "transfer",
            "condition_refs": [condition["id"]], "assumption_refs": [], "expected_revision": 0,
            "target_footprint": store.coverage(target)}]
        interpretation["annotation_updates"] = [{"alias": "account", "subject_ref": target,
            "footprint_kind": "whole_input_context", "coherent_sets": [{"context_refs": [condition["id"]],
                "interpretations": [{"hypothesis_ref": "@role", "disposition": "unresolved", "assessment_refs": ["@assessment"]}]}],
            "alternative_refs": [], "resolution": "unresolved", "expected_revision": 0}]
        linked = store.commit_reasoning(interpretation, store.validate_scope(None), "condition-linked-interpretation")
        assert linked["status"] == "completed", linked
        output = export_annotation(store, tmp_path / "annotation.json")
        exported = json.loads(Path(output["json"]["path"]).read_text())
        rows = {r["id"]: r for r in exported["records"]}
        assert rows[condition["id"]] == condition
        assert rows[observation["id"]]["source_subject_refs"] == observation["source_subject_refs"]


def test_partial_context_extraction_does_not_discard_prior_source_entity_or_rewrite_its_name(tmp_path):
    store, source, anchor = setup(tmp_path)
    with store:
        data = contexts(source, anchor)
        data["contexts"][0]["name"] = "minimal medium, no other nutrients"
        first = store.commit_reasoning(data, store.validate_scope(None), "invalid-context-name")
        assert first["status"] == "partial"
        assert set(first["aliases"]) == {"construct"}
        assert first["errors"] == [{"section": "contexts", "row_index": 0,
            "code": "context_name_not_in_source_span", "field_path": ["name"]}]
        assert store.list("context") == []
        corrected = payload()
        corrected["contexts"] = contexts(source, anchor)["contexts"]
        corrected["contexts"][0]["related_refs"] = [first["aliases"]["construct"]]
        last = store.commit_reasoning(corrected, store.validate_scope(None), "corrected-context-name")
        assert last["status"] == "completed", last
        assert len(store.list("reference")) == 1 and len(store.list("context")) == 1


def test_existing_reference_check_reports_nested_field_and_actual_allowed_types(tmp_path):
    store, source, anchor = setup(tmp_path)
    with store:
        first = store.commit_reasoning(contexts(source, anchor), store.validate_scope(None), "context")
        data = payload()
        data["hypotheses"] = [{"alias": "hypothesis", "subject_refs": store.problem()["subject_refs"],
            "predicate": "sequence_integrity", "value": {"type": "enum", "value": "intact"},
            "context_refs": [first["aliases"]["construct"]]}]
        bad = store.commit_reasoning(data, store.validate_scope(None), "wrong-context-reference")
        assert bad["status"] == "invalid" and not bad["record_refs"]
        assert bad["errors"] == [{"section": "hypotheses", "row_index": 0,
            "code": "wrong_reference_type", "reference": first["aliases"]["construct"],
            "actual_record_type": "reference", "allowed_record_types": ["context", "hypothesis"],
            "field_path": ["context_refs", 0]}]
        data["hypotheses"][0]["context_refs"] = [first["aliases"]["medium"]]
        assert store.commit_reasoning(data, store.validate_scope(None), "right-context-reference")["status"] == "completed"


def test_alias_definition_reference_feedback_and_provider_guidance_are_distinct(tmp_path):
    store, source, anchor = setup(tmp_path)
    with store:
        data = contexts(source, anchor)
        data["contexts"][0]["alias"] = "@medium"
        data["contexts"][0]["related_refs"] = ["construct"]
        bad = store.commit_reasoning(data, store.validate_scope(None), "bare-reference-and-prefixed-definition")
        assert bad["errors"][0]["field_path"] == ["alias"]
        assert bad["errors"][0]["schema_keyword"] == "pattern"
        data["contexts"][0]["alias"] = "medium"
        bad_ref = store.commit_reasoning(data, store.validate_scope(None), "bare-reference")
        assert bad_ref["errors"][0]["field_path"] == ["related_refs", 0]
        data["contexts"][0]["related_refs"] = ["@missing"]
        unresolved = store.commit_reasoning(data, store.validate_scope(None), "missing-alias")
        assert unresolved["errors"][0] == {"section": "contexts", "row_index": 0,
            "code": "unresolved_alias", "field_path": ["related_refs", 0], "reference": "@missing"}
        provider_schema = _action_generation_schema(store.reasoning_schema())
        declared = provider_schema["properties"]["hypotheses"]["items"]["properties"]
        assert "pattern" not in declared["alias"]
        assert "@role" in declared["alias"]["description"]
        assert "not protein/profile" in declared["context_refs"]["description"]
