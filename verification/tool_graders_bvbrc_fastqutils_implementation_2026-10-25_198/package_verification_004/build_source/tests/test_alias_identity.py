"""Private commit names do not determine scientific identity or parent forms.

Names reproduce a live format failure; the biological content here is a local
engineering fixture, not an interpretation of those live observations.
"""
import copy
import json

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, reference_resolver, validate_form
from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.domain import obj
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


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


def test_long_private_aliases_commit_resolve_replay_and_cannot_cross_parent_form(tmp_path):
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"][0]
        inspection = ToolRegistry(store).execute("sequence.inspect", {"subject_ref": target})
        observed = next(ref for ref in inspection["record_refs"] if ref.startswith("observation_"))
        hypothesis_alias = "separate_sira_like_not_target_tusa"
        assessment_alias = "second_epimerase_comparative_revision"
        payload = _payload(target, observed, hypothesis_alias, assessment_alias)
        first = store.commit_reasoning(payload, None, "long-names")
        assert first["status"] == "completed", first
        assert len(first["changed_record_refs"]) == 3
        assert store.commit_reasoning(payload, None, "long-names") == first
        hypothesis_ref = first["aliases"][hypothesis_alias]
        assessment_ref = first["aliases"][assessment_alias]
        assert store.get(assessment_ref)["hypothesis_ref"] == hypothesis_ref
        assert store.current_annotations()[0]["coherent_sets"][0]["interpretations"][0]["assessment_refs"] == [assessment_ref]
        credit = project_credit(store).as_record()
        renamed = _payload(target, observed, "same_hypothesis_with_a_different_private_name",
            "same_assessment_with_a_different_private_name", revision=1)
        reused = store.commit_reasoning(renamed, None, "renamed-work")
        assert reused["status"] == "completed", reused
        assert reused["changed_record_refs"] == []
        assert reused["record_refs"] == first["record_refs"]
        assert project_credit(store).as_record() == credit
        for ref in first["record_refs"]:
            encoded = json.dumps(store.get(ref))
            assert hypothesis_alias not in encoded and assessment_alias not in encoded
            assert "alias" not in store.get(ref)
        form = obj({"hypothesis": {"type": "string", "format": "reference",
                                  "x-reference-namespace": "hypothesis"}})
        resolve = reference_resolver(store.references())
        assert validate_form({"hypothesis": hypothesis_ref}, form, resolve) == {"hypothesis": hypothesis_ref}
        for private_name in (hypothesis_alias, "@" + hypothesis_alias):
            with pytest.raises(ReportBoundaryError) as failure:
                validate_form({"hypothesis": private_name}, form, resolve)
            assert failure.value.diagnostic["code"] == "unknown_reference"


def test_removed_length_cap_preserves_alias_grammar_and_resolution_feedback(tmp_path):
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"][0]
        inspected = ToolRegistry(store).execute("sequence.inspect", {"subject_ref": target})
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
