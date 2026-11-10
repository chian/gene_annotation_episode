"""Scientific scope rejection identifies the actual mismatch without repairing it."""
from copy import deepcopy

import pytest

from gene_annotation_episode.state import Store
from test_state import empty_payload, hypothesis, source


@pytest.mark.parametrize("section", ["interpretation_accounts", "annotation_updates"])
@pytest.mark.parametrize("position", ["interpretation", "alternative"])
@pytest.mark.parametrize("other_subject_kind", ["source", "region"])
def test_scope_feedback_preserves_other_subject_and_accepts_explicit_correction(
        tmp_path, section, position, other_subject_kind):
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence="MACD", molecule="protein")["subject_refs"]
        scope = {"subject_refs": [target]}
        target_hypothesis = hypothesis(store, target)["id"]
        if other_subject_kind == "source":
            src = source(store, "A different source molecule.")
            other = store.put("reference", {"reference_type": "rna", "source_ref": src["id"],
                "accession": "source-rna", "label": "source RNA", "sequence_ref": None,
                "molecule": "rna", "length": None, "term_refs": [], "context_refs": []},
                origin="external")["id"]
            other_footprint = []
        else:
            other = store.put("feature", {"subject_ref": target, "kind": "sequence_region",
                "segments": [{"start": 0, "end": 2}], "strand": "+", "context_refs": []},
                origin="caller")["id"]
            other_footprint = [{"target_ref": target, "start": 0, "end": 2, "unit": "aa"}]
        other_hypothesis = hypothesis(store, other)["id"]
        original = deepcopy(store.get(other_hypothesis))
        interpretation = lambda ref: {"hypothesis_ref": ref, "disposition": "unresolved",
                                       "assessment_refs": []}
        account = {"alias": "account", "subject_ref": target, "footprint_kind": "localized",
            "coherent_sets": [{"interpretations": [interpretation(target_hypothesis)],
                               "context_refs": []}],
            "alternative_refs": [], "resolution": "unresolved", "expected_revision": 0}
        if position == "interpretation":
            account["coherent_sets"][0]["interpretations"].append(interpretation(other_hypothesis))
            field_path = ["coherent_sets", 0, "interpretations", 1, "hypothesis_ref"]
        else:
            account["alternative_refs"] = [other_hypothesis]
            field_path = ["alternative_refs", 0]
        payload = empty_payload()
        payload[section] = [account]
        before = deepcopy(payload)
        owner = {"account_owner": ("run", "episode")}
        rejected = store.commit_reasoning(payload, scope, "wrong-subject", **owner)
        assert rejected["status"] == "invalid"
        assert rejected["record_refs"] == rejected["changed_record_refs"] == []
        error, = rejected["errors"]
        assert error["code"] == "annotation_hypothesis_footprint_mismatch"
        assert error["section"] == section and error["row_index"] == 0
        assert error["field_path"] == field_path
        assert error["hypothesis_ref"] == other_hypothesis
        assert error["hypothesis_subject_refs"] == [other]
        assert error["subject_ref"] == target
        assert error["account_footprint"] == [
            {"target_ref": target, "start": 0, "end": 4, "unit": "aa"}]
        assert error["hypothesis_footprint"] == other_footprint
        assert "return their references separately" in error["repair"]
        assert payload == before and store.get(other_hypothesis) == original
        assert store.commit_reasoning(payload, scope, "wrong-subject", **owner) == rejected
        assert not store.list("annotation") and not store.list("interpretation_account")

        # The caller chooses the correction; validation does not rewrite a
        # source claim, widen a region or attach either to the target.
        corrected = deepcopy(payload)
        corrected[section][0]["coherent_sets"][0]["interpretations"] = [
            interpretation(target_hypothesis)]
        corrected[section][0]["alternative_refs"] = []
        accepted = store.commit_reasoning(corrected, scope, "caller-corrected-subject", **owner)
        assert accepted["status"] == "completed" and accepted["errors"] == []
        saved = store.get(accepted["aliases"]["account"])
        assert saved["coherent_sets"][0]["interpretations"] == [interpretation(target_hypothesis)]
        assert store.get(other_hypothesis) == original
