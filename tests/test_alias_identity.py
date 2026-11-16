"""Private commit names do not determine scientific identity or parent forms.

Names reproduce a live format failure; the biological content here is a local
engineering fixture, not an interpretation of those live observations.
"""
import copy


from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry


def _payload(target, observed_ref, hypothesis_alias, assessment_alias, *, revision=0):
    return {
        "structural_proposals": [], "terms": [], "source_subjects": [], "observations": [],
        "hypotheses": [{"alias": hypothesis_alias, "subject_refs": [target],
            "predicate": "sequence_integrity", "value": {"type": "enum", "value": "intact"},
            "context_refs": []}],
        "assessments": [{"alias": assessment_alias, "hypothesis_ref": "@" + hypothesis_alias,
            "observation_ref": observed_ref, "relation": "strengthens", "applicability": "direct", "extent_basis": "observed_extent",
            "condition_refs": [], "assumption_refs": [], "expected_revision": revision}],
        "annotation_updates": [{"alias": "current_annotation", "subject_ref": target,
            "footprint_kind": "localized", "coherent_sets": [{"interpretations": [{
                "hypothesis_ref": "@" + hypothesis_alias, "disposition": "supported",
                "assessment_refs": ["@" + assessment_alias]}], "context_refs": []}],
            "alternative_refs": [], "resolution": "selected", "expected_revision": revision}],
    }


def test_removed_length_cap_preserves_alias_grammar_and_resolution_feedback(tmp_path):
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"][0]
        inspected = ToolRegistry(store, run_directory=store.path / 'tool-run').execute("sequence.inspect", {"subject_ref": target})
        observed = next(ref for ref in inspected["record_refs"] if ref.startswith("observation_"))
        original = _payload(target, observed, "a_private_hypothesis_name_longer_than_thirty_two", "valid_assessment")
        invalid = copy.deepcopy(original)
        invalid["hypotheses"][0]["alias"] = "this is a paragraph rather than an identifier"
        result = store.commit_reasoning(invalid, None, "invalid-grammar")
        assert result["status"] == "invalid", result
        assert result["changed_record_refs"] == []
        assert result["errors"][0]["field_path"] == ["alias"]
        missing = copy.deepcopy(original)
        missing["hypotheses"] = []
        missing["annotation_updates"] = []
        result = store.commit_reasoning(missing, None, "undefined-long-alias")
        assert result["status"] == "invalid", result
        assert result["errors"][0]["code"] == "unresolved_alias"
        assert result["errors"][0]["field_path"] == ["hypothesis_ref"]
        assert not store.current_annotations()
