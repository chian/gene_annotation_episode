"""Actual annotation publication ownership; generated reads are not biology."""

import pytest

from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def fixture(tmp_path):
    reads = tmp_path / "reads.fastq"
    reads.write_text("@a\nTTACGTAGGGGG\n+\nIIIIIIIIIIII\n@b\nGGTACCAACCGG\n+\n!!!!!!!!!!!!\n")
    store = Store(tmp_path / "state")
    store.create_problem(reads, molecule="dna")
    target, = store.targets()
    tools = ToolRegistry(store)
    members = tools.execute("library.members", {"library_ref": target["id"]})["result"]["members"]
    selected = tools.execute("library.select", {"library_ref": target["id"],
        "member_refs": [members[0]["member_ref"]]})["result"]
    return store, tools, target, members, selected["scope"]


def hypothesis(store, subject_ref, *, scope=None):
    return store.put("hypothesis", {"subject_refs": [subject_ref], "predicate": "molecule_type",
        "value": {"type": "enum", "value": "dna"}, "context_refs": []}, origin="reasoning", scope=scope)


def annotation(subject_ref, hypothesis_ref, *, alias=None, revision=0,
               resolution="unresolved", footprint_kind="whole_input_context"):
    return {**({"alias": alias} if alias else {}), "subject_ref": subject_ref,
        "footprint_kind": footprint_kind,
        "coherent_sets": [{"interpretations": [{"hypothesis_ref": hypothesis_ref,
            "disposition": "unresolved", "assessment_refs": []}], "context_refs": []}],
        "alternative_refs": [], "resolution": resolution, "expected_revision": revision}


def payload(store, rows):
    return {**{key: [] for key in store.reasoning_schema()["required"]}, "annotation_updates": rows}


def current_pointer(store, subject_ref):
    row = store.db.execute("SELECT revision,record_ref FROM current_revisions "
        "WHERE record_type='annotation' AND key_ref=?", (subject_ref,)).fetchone()
    return dict(row) if row else None


def test_subset_cannot_publish_empty_footprint_library_annotation_and_valid_local_row_survives(tmp_path):
    store, tools, target, members, child = fixture(tmp_path)
    with store:
        global_h = hypothesis(store, target["id"])
        local_h = hypothesis(store, members[0]["id"], scope=child)
        proposed = payload(store, [annotation(target["id"], global_h["id"], alias="outside"),
            annotation(members[0]["id"], local_h["id"], alias="owned")])
        result = store.commit_reasoning(proposed, child, "subset-library-annotation-create")
        assert result["status"] == "partial" and result["aliases"].keys() == {"owned"}
        error, = result["errors"]
        assert error == {"section": "annotation_updates", "row_index": 0,
            "code": "annotation_library_context_outside_assigned_scope", "field_path": ["subject_ref"],
            "subject_ref": target["id"], "target_ref": target["id"],
            "meaning": "library_annotation_requires_ownership_of_its_fixed_original_library"}
        assert current_pointer(store, target["id"]) is None
        assert store.db.execute("SELECT count(*) FROM proposals").fetchone()[0] == 0
        local = store.get(result["aliases"]["owned"])
        assert local["subject_ref"] == members[0]["id"] and local["revision"] == 1
        assert local["footprint"] == store.coverage(members[0]["id"])
        assert result["record_refs"] == result["changed_record_refs"] == [local["id"]]
        assert store.reference_subset(result["record_refs"], child) == result["record_refs"]
        assert store.commit_reasoning(proposed, child, "subset-library-annotation-create") == result
        assert project_credit(store).credit == project_credit(store, child).credit == 0


def test_subset_cannot_replace_global_current_but_full_library_child_can_revise_it(tmp_path):
    store, tools, target, members, child = fixture(tmp_path)
    with store:
        global_h = hypothesis(store, target["id"])
        initial = store.put("annotation", annotation(target["id"], global_h["id"]), origin="reasoning")
        assert initial["footprint"] == [] and initial["revision"] == 1
        before = current_pointer(store, target["id"])
        proposed = payload(store, [annotation(target["id"], global_h["id"], alias="outsideRevision",
            revision=1, resolution="selected")])
        result = store.commit_reasoning(proposed, child, "subset-library-annotation-revise")
        assert result["status"] == "invalid" and result["record_refs"] == result["changed_record_refs"] == []
        error, = result["errors"]
        assert error["code"] == "annotation_library_context_outside_assigned_scope"
        assert error["field_path"] == ["expected_revision"]
        assert error["current_annotation_ref"] == initial["id"] and error["current_revision"] == 1
        assert error["subject_ref"] == error["target_ref"] == target["id"]
        assert current_pointer(store, target["id"]) == before
        assert store.current_annotations() == [initial]
        assert store.db.execute("SELECT count(*) FROM proposals").fetchone()[0] == 0
        # Scope ownership prevents writes, not access to the inherited account.
        visible = tools.execute("state.query", {"refs": [initial["id"]]}, scope=child)
        assert visible["status"] == "completed" and visible["result"]["records"] == [initial]
        assert store.reference_subset([initial["id"]], child) == [initial["id"]]
        selected = tools.execute("library.select", {"library_ref": target["id"],
            "member_refs": [member["member_ref"] for member in members]})["result"]
        assert store.scope_measure(selected["scope"], target["id"]) == target["position_mass"]
        revised = store.commit_reasoning(proposed, selected["scope"], "full-library-annotation-revise")
        assert revised["status"] == "completed" and revised["errors"] == revised["conflicts"] == []
        current = store.get(revised["aliases"]["outsideRevision"])
        assert current["revision"] == 2 and current["resolution"] == "selected" and current["footprint"] == []
        assert current_pointer(store, target["id"]) == {"revision": 2, "record_ref": current["id"]}
        assert store.get(initial["id"]) == initial
        assert store.reference_subset(revised["record_refs"], selected["scope"]) == revised["record_refs"]
        assert project_credit(store).credit == project_credit(store, child).credit == 0


@pytest.mark.parametrize("footprint_kind", ["whole_input_context", "localized"])
def test_owned_read_context_annotations_remain_iteratively_revisable(tmp_path, footprint_kind):
    store, tools, target, members, child = fixture(tmp_path)
    with store:
        subject = members[0]
        local_h = hypothesis(store, subject["id"], scope=child)
        first = store.put("annotation", annotation(subject["id"], local_h["id"],
            footprint_kind=footprint_kind), origin="reasoning", scope=child)
        proposed = payload(store, [annotation(subject["id"], local_h["id"], alias="revision",
            revision=1, resolution="alternatives_retained", footprint_kind=footprint_kind)])
        result = store.commit_reasoning(proposed, child, "owned-read-context-revise")
        assert result["status"] == "completed" and not result["errors"]
        second = store.get(result["aliases"]["revision"])
        assert second["revision"] == first["revision"] + 1
        assert second["footprint"] == first["footprint"] == store.coverage(subject["id"])
        assert current_pointer(store, subject["id"]) == {"revision": 2, "record_ref": second["id"]}
        assert store.reference_subset(result["record_refs"], child) == result["record_refs"]
