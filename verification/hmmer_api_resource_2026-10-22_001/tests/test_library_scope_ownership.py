"""Ownership corrections through real Store commits, native tools and credit.

Generated sequence fixtures establish boundaries, not biological conclusions.
"""
import json

import pytest

from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def fixture(tmp_path):
    reads = tmp_path / "reads.fastq"
    reads.write_text("@a native\nTTACGTAGGGGG\n+\nIIIIIIIIIIII\n@b native\nGGTACCAACCGG\n+\n!!!!!!!!!!!!\n")
    store = Store(tmp_path / "state")
    store.create_problem(reads, molecule="dna")
    target, = store.targets()
    tools = ToolRegistry(store)
    members = tools.execute("library.members", {"library_ref": target["id"]})["result"]["members"]
    selected = tools.execute("library.select", {"library_ref": target["id"],
        "member_refs": [members[0]["member_ref"]]})["result"]
    return store, tools, target, members[0], members[1], selected["scope"]


def payload(store):
    return {key: [] for key in store.reasoning_schema()["required"]}


def hypothesis(subject_ref, *, alias=None, value="intact"):
    return {**({"alias": alias} if alias else {}), "subject_refs": [subject_ref],
        "predicate": "sequence_integrity", "value": {"type": "enum", "value": value}, "context_refs": []}


def assessment(hypothesis_ref, observation_ref, *, alias=None, revision=0, relation="strengthens", **fields):
    return {**({"alias": alias} if alias else {}), "hypothesis_ref": hypothesis_ref,
        "observation_ref": observation_ref, "relation": relation, "applicability": "direct",
        "extent_basis": "observed_extent", "condition_refs": [], "assumption_refs": [],
        "expected_revision": revision, **fields}


def current_account(store, tools, subject):
    observed = tools.execute("sequence.inspect", {"subject_ref": subject["id"]})
    assert observed["status"] == "completed", observed
    h = store.put("hypothesis", hypothesis(subject["id"]), origin="reasoning")
    a = store.put("assessment", assessment(h["id"], observed["result"]["observation_ref"]), origin="reasoning")
    annotation = store.put("annotation", {"subject_ref": subject["id"], "footprint_kind": "localized",
        "coherent_sets": [{"interpretations": [{"hypothesis_ref": h["id"], "disposition": "supported",
            "assessment_refs": [a["id"]]}], "context_refs": []}], "alternative_refs": [],
        "resolution": "selected", "expected_revision": 0}, origin="reasoning")
    return h, a, annotation


def resolver(store, scope):
    workflow = Workflow.__new__(Workflow)
    workflow.store = store
    return workflow.resolver(scope)


def test_disjoint_child_hypothesis_and_cas_cannot_erase_root_progress_and_valid_rows_survive(tmp_path):
    store, tools, target, a, b, child_scope = fixture(tmp_path)
    with store:
        h_b, a_b, annotation_b = current_account(store, tools, b)
        before_root = project_credit(store).credit
        before_child = project_credit(store, child_scope).credit
        assert before_root > 0 and before_child == 0
        proposed = payload(store)
        proposed["hypotheses"] = [hypothesis(b["id"], alias="outside", value="coding"),
            hypothesis(a["id"], alias="owned", value="unresolved")]
        proposed["assessments"] = [assessment(h_b["id"], a_b["observation_ref"],
            alias="outsideCorrection", revision=1, relation="weakens")]
        result = store.commit_reasoning(proposed, child_scope, "disjoint-member-attempt")
        assert result["status"] == "partial" and result["aliases"].keys() == {"owned"}
        assert [row["code"] for row in result["errors"]] == [
            "record_subject_member_outside_scope", "assessment_hypothesis_member_outside_scope"]
        assert result["errors"][0]["field_path"] == ["subject_refs", 0]
        assert result["errors"][0]["member_ref"] == b["member_ref"]
        assert result["errors"][1]["field_path"] == ["hypothesis_ref"]
        assert store.current_assessment_subset([a_b["id"]]) == {a_b["id"]: a_b}
        assert store.current_annotations() == [annotation_b]
        assert project_credit(store).credit == before_root
        assert project_credit(store, child_scope).credit == before_child
        assert store.db.execute("SELECT count(*) FROM proposals").fetchone()[0] == 0
        returned = result["record_refs"]
        assert returned == result["changed_record_refs"] == [result["aliases"]["owned"]]
        assert store.reference_subset(returned, child_scope) == returned
        assert [row["id"] for row in store.query_records("hypothesis", child_scope)["records"]] == returned
        assert all(resolver(store, child_scope)(ref) for ref in returned)
        assert store.commit_reasoning(proposed, child_scope, "disjoint-member-attempt") == result


def test_partial_child_reads_broad_account_but_cannot_cas_erase_its_outside_attribution(tmp_path):
    store, tools, target, a, b, child_scope = fixture(tmp_path)
    with store:
        h_a, a_a, annotation_a = current_account(store, tools, a)
        span = {**store.coverage(a["id"])[0], "start": 2, "end": 7}
        narrow = {**child_scope, "segments": [span]}
        root_before, child_before = project_credit(store).credit, project_credit(store, narrow).credit
        assert root_before > 0 and child_before > 0
        assert store.current_annotations(narrow) == [annotation_a]
        assert resolver(store, narrow)(a_a["id"], "assessment")
        proposed = payload(store)
        proposed["hypotheses"] = [hypothesis(a["id"], alias="overlappingWorking", value="unresolved")]
        proposed["assessments"] = [assessment(h_a["id"], a_a["observation_ref"],
            alias="narrowOverwrite", revision=1, relation="weakens", target_footprint=[span])]
        result = store.commit_reasoning(proposed, narrow, "partial-cas-must-not-delete-outside")
        assert result["status"] == "partial" and "overlappingWorking" in result["aliases"]
        error, = result["errors"]
        assert error["code"] == "assessment_current_attribution_outside_assigned_read_scope"
        assert error["current_assessment_ref"] == a_a["id"] and error["current_revision"] == 1
        assert error["field_path"] == ["expected_revision"]
        assert store.current_assessment_subset([a_a["id"]]) == {a_a["id"]: a_a}
        assert project_credit(store).credit == root_before
        assert project_credit(store, narrow).credit == child_before
        assert resolver(store, narrow)(result["aliases"]["overlappingWorking"], "hypothesis")


def test_new_missing_inferred_extent_remains_valid_uncredited_science_with_notice(tmp_path):
    store, tools, target, a, b, child_scope = fixture(tmp_path)
    with store:
        observed = tools.execute("sequence.inspect", {"subject_ref": b["id"]})["result"]["observation_ref"]
        narrow = {**child_scope, "segments": [{**store.coverage(a["id"])[0], "start": 2, "end": 7}]}
        proposed = payload(store)
        proposed["hypotheses"] = [hypothesis(a["id"], alias="working", value="unresolved")]
        proposed["assessments"] = [assessment("@working", observed, alias="unlocalized",
            applicability="contextual", extent_basis="inferred_extent")]
        result = store.commit_reasoning(proposed, narrow, "missing-inferred-extent-stays-recorded")
        assert result["status"] == "completed" and result["errors"] == []
        assert result["notices"] == [{"section": "assessments", "row_index": 0,
            "record_ref": result["aliases"]["unlocalized"], "field_path": ["target_footprint"],
            "code": "inferred_extent_requires_target_footprint"}]
        stored = store.get(result["aliases"]["unlocalized"])
        assert "target_footprint" not in stored
        assert store.reference_subset(result["record_refs"], narrow) == result["record_refs"]
        assert project_credit(store).credit == project_credit(store, narrow).credit == 0
        # The old unlocalized inference had no outside spatial contribution.
        # Its first explicit, owned attribution may replace that current row.
        localized = payload(store)
        localized["assessments"] = [assessment(result["aliases"]["working"], observed, alias="nowLocalized",
            revision=1, applicability="contextual", extent_basis="inferred_extent", target_footprint=narrow["segments"])]
        changed = store.commit_reasoning(localized, narrow, "first-owned-inferred-attribution")
        assert changed["status"] == "completed" and not changed["errors"]
        assert store.get(changed["aliases"]["nowLocalized"])["revision"] == 2


def test_native_observed_local_extent_needs_no_extra_assessment_footprint_field(tmp_path):
    store, tools, target, a, b, child_scope = fixture(tmp_path)
    with store:
        material = store.register_material(data=">actual_reference\nACGTA\n", format="fasta", molecule="dna")
        attempt = store.parse_material(material["id"])
        native = store.material_members(attempt["collection_ref"])["members"][0]
        reference = store.material_reference(native["id"])
        native_alignment = tools.execute("sequence.align", {"query_ref": a["id"], "reference_ref": reference["id"],
            "molecule": "dna", "mode": "local"})
        assert native_alignment["status"] == "completed", native_alignment
        assert native_alignment["result"]["query_interval"] == [2, 7]
        narrow = {**child_scope, "segments": [{**store.coverage(a["id"])[0], "start": 2, "end": 7}]}
        proposed = payload(store)
        proposed["hypotheses"] = [hypothesis(a["id"], alias="broaderWorking", value="unresolved")]
        proposed["assessments"] = [assessment("@broaderWorking", native_alignment["result"]["observation_ref"],
            alias="localNative")]
        result = store.commit_reasoning(proposed, narrow, "native-bounds-are-enough")
        assert result["status"] == "completed" and not result["errors"]
        assert "target_footprint" not in store.get(result["aliases"]["localNative"])
        assert store.reference_subset(result["record_refs"], narrow) == result["record_refs"]
        revision = payload(store)
        revision["assessments"] = [assessment(result["aliases"]["broaderWorking"], native_alignment["result"]["observation_ref"],
            alias="localNativeRevision", revision=1, relation="mixed")]
        revised = store.commit_reasoning(revision, narrow, "native-local-cas-needs-no-artificial-hypothesis-narrowing")
        assert revised["status"] == "completed" and not revised["errors"]
        assert store.get(revised["aliases"]["localNativeRevision"])["revision"] == 2


def test_library_global_context_current_revision_still_has_full_target_ownership(tmp_path, monkeypatch):
    store, tools, target, a, b, child_scope = fixture(tmp_path)
    with store:
        observed = tools.execute("sequence.inspect", {"subject_ref": a["id"]})["result"]["observation_ref"]
        h = store.put("hypothesis", {"subject_refs": [target["id"]], "predicate": "molecule_type",
            "value": {"type": "enum", "value": "dna"}, "context_refs": []}, origin="reasoning")
        current = store.put("assessment", assessment(h["id"], observed), origin="reasoning")
        assert store.record_coverage(h) == [] and store.roots(h["id"]) == [target["id"]]
        monkeypatch.setattr(store, "iter_scope_coverage", lambda *args, **kwargs: pytest.fail("full-target ownership must stay compact"))
        proposed = payload(store)
        proposed["hypotheses"] = [{"alias": "newContextScience", "subject_refs": [target["id"]], "predicate": "molecule_type",
            "value": {"type": "enum", "value": "mixture"}, "context_refs": []}]
        proposed["assessments"] = [assessment(h["id"], observed, alias="outsideGlobalCas", revision=1, relation="weakens")]
        result = store.commit_reasoning(proposed, child_scope, "library-context-is-not-ownerless")
        assert result["status"] == "partial" and "newContextScience" in result["aliases"]
        error, = result["errors"]
        assert error["code"] == "assessment_current_library_context_outside_assigned_scope"
        assert error["current_assessment_ref"] == current["id"] and error["target_ref"] == target["id"]
        assert store.current_assessment_subset([current["id"]]) == {current["id"]: current}
        full = tools.execute("library.select", {"library_ref": target["id"], "ordinal_ranges": [{"start": 0, "end": 2}]})["result"]["scope"]
        owned = payload(store)
        owned["assessments"] = [assessment(h["id"], observed, alias="ownedGlobalCas", revision=1, relation="weakens")]
        permitted = store.commit_reasoning(owned, full, "all-fixed-members-own-global-context")
        assert permitted["status"] == "completed" and not permitted["errors"]
        assert store.get(permitted["aliases"]["ownedGlobalCas"])["revision"] == 2


def test_external_context_without_original_target_ownership_stays_reusable(tmp_path):
    store, tools, target, a, b, child_scope = fixture(tmp_path)
    with store:
        source = store._caller_source({"fixture": "external reported assay context"}, "fixture_external_context")
        context = store.put("context", {"context_type": "assay_condition", "name": "fixture condition",
            "source_ref": source["id"], "attributes": [], "related_refs": []}, origin="tool")
        hypothesis_context = store.put("hypothesis", {"subject_refs": [context["id"]], "predicate": "molecule_type",
            "value": {"type": "enum", "value": "unknown"}, "context_refs": []}, origin="reasoning")
        observed = tools.execute("sequence.inspect", {"subject_ref": b["id"]})["result"]["observation_ref"]
        current = store.put("assessment", assessment(hypothesis_context["id"], observed,
            applicability="contextual"), origin="reasoning")
        assert store.roots(hypothesis_context["id"]) == []
        proposed = payload(store)
        proposed["assessments"] = [assessment(hypothesis_context["id"], observed, alias="sourceContextRevision",
            revision=1, relation="does_not_discriminate", applicability="contextual")]
        result = store.commit_reasoning(proposed, child_scope, "source-context-reusable")
        assert result["status"] == "completed" and not result["errors"]
        assert store.get(result["aliases"]["sourceContextRevision"])["revision"] == current["revision"] + 1
        assert resolver(store, child_scope)(result["aliases"]["sourceContextRevision"], "assessment")


def test_owned_cas_can_change_credit_while_other_members_current_contribution_survives(tmp_path):
    store, tools, target, a, b, child_scope = fixture(tmp_path)
    with store:
        h_a, a_a, annotation_a = current_account(store, tools, a)
        h_b, a_b, annotation_b = current_account(store, tools, b)
        root_before, child_before = project_credit(store).credit, project_credit(store, child_scope).credit
        assert root_before > 0 and child_before > 0
        proposed = payload(store)
        proposed["assessments"] = [assessment(h_a["id"], a_a["observation_ref"], alias="ownedCorrection",
            revision=1, relation="weakens")]
        result = store.commit_reasoning(proposed, child_scope, "owned-correction-is-not-clamped")
        assert result["status"] == "completed" and not result["errors"]
        assert store.get(result["aliases"]["ownedCorrection"])["revision"] == 2
        assert store.current_assessment_subset([a_b["id"]]) == {a_b["id"]: a_b}
        assert annotation_b in store.current_annotations()
        assert 0 < project_credit(store).credit < root_before
        assert project_credit(store, child_scope).credit == 0


@pytest.mark.parametrize("atom", [
    lambda ref: {"type": "reference", "ref": ref},
    lambda ref: {"type": "relation", "roles": [{"role": "substrate", "ref": ref}]},
])
def test_dataset_selection_is_not_biological_atom_but_remains_legitimate_parent_form_context(tmp_path, atom):
    store, tools, target, a, b, child_scope = fixture(tmp_path)
    with store:
        broader = tools.execute("library.select", {"library_ref": target["id"], "ordinal_ranges": [{"start": 0, "end": 2}]})["result"]["selection"]
        proposed = payload(store)
        proposed["hypotheses"] = [{"alias": "notBiological", "subject_refs": [a["id"]], "predicate": "binds",
            "value": atom(broader["id"]), "context_refs": []}, hypothesis(a["id"], alias="valid", value="unresolved")]
        result = store.commit_reasoning(proposed, child_scope, "selection-not-biological")
        assert result["status"] == "partial" and result["aliases"].keys() == {"valid"}
        assert result["errors"][0]["code"] == "semantic_value_requires_entity_reference"
        assert resolver(store, child_scope)(broader["id"], "read_selection")
        assert store.reference_subset([broader["id"]], child_scope) == [broader["id"]]
        with pytest.raises(ContractError, match="scope_members_outside_parent"):
            store.validate_scope({"subject_refs": [target["id"]], "read_selection_refs": [broader["id"]]}, parent_scope=child_scope)


def test_library_read_checks_actual_window_and_never_reads_outside_owned_positions(tmp_path, monkeypatch):
    store, tools, target, a, b, child_scope = fixture(tmp_path)
    with store:
        narrow = {**child_scope, "segments": [{**store.coverage(a["id"])[0], "start": 2, "end": 7}]}
        original, calls = store.material_member, []
        def read(member_ref, **kwargs):
            calls.append((member_ref, kwargs))
            return original(member_ref, **kwargs)
        monkeypatch.setattr(store, "material_member", read)
        local = tools.execute("library.read", {"subject_ref": a["id"], "offset": 2, "limit": 5}, scope=narrow)
        assert local["status"] == "completed", local
        assert local["result"]["sequence"] == "ACGTA" and local["result"]["quality"] == "IIIII"
        assert (local["result"]["start"], local["result"]["end"]) == (2, 7)
        assert calls == [(a["member_ref"], {"offset": 2, "limit": 5})]
        for subject, offset, limit in [(a, 1, 5), (a, 6, 2), (b, 2, 5)]:
            bad = tools.execute("library.read", {"subject_ref": subject["id"], "offset": offset, "limit": limit}, scope=narrow)
            assert bad["status"] == "invalid" and not bad["record_refs"]
        assert len(calls) == 1
        malformed = tools.execute("library.read", {"subject_ref": a["id"], "offset": 13, "limit": 1}, scope=narrow)
        assert malformed["feedback"]["code"] == "invalid_member_window" and len(calls) == 1
        eof = tools.execute("library.read", {"subject_ref": a["id"], "offset": 12, "limit": 1}, scope=narrow)
        assert eof["status"] == "completed" and eof["result"]["sequence"] == "" and eof["result"]["quality"] == ""


def context_account(store, tools, references, *, scope=None):
    source = store._caller_source({"condition": "fixture condition"}, "fixture_context_owner")
    context = store.put("context", {"context_type": "assay_condition", "name": "fixture condition",
        "source_ref": source["id"], "attributes": [], "related_refs": references}, origin="caller", scope=scope)
    h = store.put("hypothesis", {"subject_refs": [context["id"]], "predicate": "growth_capability",
        "value": {"type": "enum", "value": "unknown"}, "context_refs": []}, origin="reasoning", scope=scope)
    return context, h


def test_member_local_context_created_by_child_remains_iteratively_revisable_by_same_child(tmp_path):
    store, tools, target, a, b, child_scope = fixture(tmp_path)
    with store:
        context, h = context_account(store, tools, [a["id"]], scope=child_scope)
        observed = tools.execute("sequence.inspect", {"subject_ref": a["id"]})["result"]["observation_ref"]
        initial = store.put("assessment", assessment(h["id"], observed, relation="does_not_discriminate",
            applicability="contextual"), origin="reasoning", scope=child_scope)
        assert store.record_coverage(h) == [] and store.roots(h["id"]) == [target["id"]]
        proposed = payload(store)
        proposed["assessments"] = [assessment(h["id"], observed, alias="localContextRevision", revision=1,
            relation="mixed", applicability="contextual")]
        revised = store.commit_reasoning(proposed, child_scope, "member-context-remains-iterative")
        assert revised["status"] == "completed" and not revised["errors"]
        current = store.get(revised["aliases"]["localContextRevision"])
        assert current["revision"] == initial["revision"] + 1 and current["relation"] == "mixed"
        assert store.reference_subset(revised["record_refs"], child_scope) == revised["record_refs"]
        assert project_credit(store).credit == project_credit(store, child_scope).credit == 0


@pytest.mark.parametrize("members", [("b",), ("a", "b")])
def test_context_original_member_branches_cannot_bypass_disjoint_hypothesis_and_cas_ownership(tmp_path, members):
    store, tools, target, a, b, child_scope = fixture(tmp_path)
    with store:
        subjects = {"a": a, "b": b}
        context, h = context_account(store, tools, [subjects[name]["id"] for name in members])
        observed = tools.execute("sequence.inspect", {"subject_ref": a["id"]})["result"]["observation_ref"]
        initial = store.put("assessment", assessment(h["id"], observed, applicability="contextual"), origin="reasoning")
        proposed = payload(store)
        proposed["hypotheses"] = [{"alias": "outsideContext", "subject_refs": [context["id"]],
            "predicate": "molecule_type", "value": {"type": "enum", "value": "unknown"}, "context_refs": []},
            hypothesis(a["id"], alias="inside", value="unresolved")]
        proposed["assessments"] = [assessment(h["id"], observed, alias="outsideContextCas", revision=1,
            applicability="contextual", relation="mixed")]
        result = store.commit_reasoning(proposed, child_scope, "all-related-member-branches-retained")
        assert result["status"] == "partial" and result["aliases"].keys() == {"inside"}
        assert [row["code"] for row in result["errors"]] == ["record_subject_member_outside_scope",
            "assessment_hypothesis_member_outside_scope"]
        assert result["errors"][0]["member_ref"] == b["member_ref"]
        assert store.current_assessment_subset([initial["id"]]) == {initial["id"]: initial}
        # Even a fresh source-anchored context row cannot attach itself to an
        # unowned original member merely by entering through contexts section.
        source = store._caller_source({"condition": "read B condition"}, "fixture_context_scope")
        raw = store.get_artifact(source["artifact_ref"])
        start = raw.index(b"read B condition")
        fresh = payload(store)
        fresh["contexts"] = [{"alias": "outsideSourceContext", "context_type": "assay_condition", "name": "read B condition",
            "source_ref": source["id"], "attributes": [], "related_refs": [b["id"]],
            "anchor": {"source_ref": source["id"], "artifact_ref": source["artifact_ref"],
                "start": start, "end": start + len(b"read B condition"), "quote": "read B condition"}}]
        rejected = store.commit_reasoning(fresh, child_scope, "disjoint-anchored-context-is-still-outside")
        assert rejected["status"] == "invalid" and rejected["errors"][0]["code"] == "record_subject_member_outside_scope"
        assert rejected["errors"][0]["field_path"] == ["related_refs", 0]


def test_explicit_library_container_remains_global_alongside_local_context_branch(tmp_path):
    store, tools, target, a, b, child_scope = fixture(tmp_path)
    with store:
        context, h = context_account(store, tools, [target["id"], a["id"]])
        reach = store._ownership_reach([context["id"]])
        assert reach["library_refs"] == [target["id"]] and reach["segments"] == store.coverage(a["id"])
        observed = tools.execute("sequence.inspect", {"subject_ref": a["id"]})["result"]["observation_ref"]
        initial = store.put("assessment", assessment(h["id"], observed, applicability="contextual"), origin="reasoning")
        proposed = payload(store)
        proposed["assessments"] = [assessment(h["id"], observed, alias="notOnlyA", revision=1,
            applicability="contextual", relation="mixed")]
        result = store.commit_reasoning(proposed, child_scope, "local-provenance-cannot-shrink-explicit-library-context")
        assert result["status"] == "invalid"
        assert result["errors"][0]["code"] == "assessment_current_library_context_outside_assigned_scope"
        assert store.current_assessment_subset([initial["id"]]) == {initial["id"]: initial}


def test_direct_mixed_library_and_read_subject_cas_preserves_explicit_global_branch(tmp_path):
    store, tools, target, a, b, child_scope = fixture(tmp_path)
    with store:
        observed = tools.execute("sequence.inspect", {"subject_ref": a["id"]})["result"]["observation_ref"]
        h = store.put("hypothesis", {"subject_refs": [target["id"], a["id"]], "predicate": "molecule_type",
            "value": {"type": "enum", "value": "unknown"}, "context_refs": []}, origin="reasoning")
        initial = store.put("assessment", assessment(h["id"], observed), origin="reasoning")
        store.put("annotation", {"subject_ref": a["id"], "footprint_kind": "localized",
            "coherent_sets": [{"interpretations": [{"hypothesis_ref": h["id"], "disposition": "supported",
                "assessment_refs": [initial["id"]]}], "context_refs": []}], "alternative_refs": [],
            "resolution": "selected", "expected_revision": 0}, origin="reasoning")
        assert store.record_coverage(h) == store.coverage(a["id"])
        before = project_credit(store).credit
        assert before > 0
        proposed = payload(store)
        proposed["assessments"] = [assessment(h["id"], observed, alias="globalAndLocal", revision=1, relation="weakens")]
        result = store.commit_reasoning(proposed, child_scope, "direct-library-branch-cannot-disappear")
        assert result["status"] == "invalid"
        assert result["errors"][0]["code"] == "assessment_current_library_context_outside_assigned_scope"
        assert store.current_assessment_subset([initial["id"]]) == {initial["id"]: initial}
        assert project_credit(store).credit == before


def test_exact_metadata_read_uses_existing_overlap_visibility_without_measurement_permission(tmp_path, monkeypatch):
    store, tools, target, a, b, child_scope = fixture(tmp_path)
    with store:
        h, assessed, annotation = current_account(store, tools, a)
        narrow = {**child_scope, "segments": [{**store.coverage(a["id"])[0], "start": 2, "end": 7}]}
        monkeypatch.setattr(tools, "_sequence", lambda *args, **kwargs: pytest.fail("metadata is not a sequence measurement"))
        assert store.reference_subset([a["id"]], narrow) == [a["id"]]
        read = tools.execute("state.query", {"refs": [a["id"], h["id"], assessed["id"], annotation["id"], target["id"]]}, scope=narrow)
        assert read["status"] == "completed", read
        assert [row["id"] for row in read["result"]["records"]] == [a["id"], h["id"], assessed["id"], annotation["id"], target["id"]]
        assert read["result"]["records"][3]["footprint"] == store.coverage(a["id"])
        outside = tools.execute("state.query", {"refs": [b["id"]]}, scope=narrow)
        assert outside["status"] == "invalid" and outside["feedback"]["code"] == "subject_outside_assigned_scope"
        measurement = tools.execute("sequence.inspect", {"subject_ref": a["id"]}, scope=narrow)
        assert measurement["status"] == "invalid"
        assert measurement["feedback"]["code"] == "requested_measurement_outside_assigned_segments_or_members"
