"""Actual annotation publication ownership; generated reads are not biology."""

import pytest

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry


def fixture(tmp_path):
    reads = tmp_path / "reads.fastq"
    reads.write_text("@a\nTTACGTAGGGGG\n+\nIIIIIIIIIIII\n@b\nGGTACCAACCGG\n+\n!!!!!!!!!!!!\n")
    store = Store(tmp_path / "state")
    store.create_problem(reads, molecule="dna")
    target, = store.targets()
    tools = ToolRegistry(store, run_directory=store.path / 'tool-run')
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
