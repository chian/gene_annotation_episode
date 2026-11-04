"""Real Store/tool read-library geometry and custody; generated fixtures only."""
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


READS = b"@same first native\nACGTTGCAACGT\n+\n!@+~########\n@same second native\nTTTTAAAACCCC\n+\nIIII$$$$!!!!\n"


def library(store, tmp_path, content=READS, **kwargs):
    path = tmp_path / "reads.fastq"
    path.write_bytes(content)
    problem = store.create_problem(path, **kwargs)
    target, = store.targets()
    return problem, target


def work(tools, name, args, **kwargs):
    result = tools.execute(name, args, **kwargs)
    assert result["status"] in {"completed", "partial"}, result
    return result["result"]


def members(store, target):
    return work(ToolRegistry(store), "library.members", {"library_ref": target["id"]})["members"]


def test_fixed_library_is_not_a_joined_sequence_or_per_read_input_inventory(tmp_path):
    with Store(tmp_path / "state") as store:
        problem, target = library(store, tmp_path)
        assert target["target_kind"] == "read_library"
        assert target["molecule"] == "unspecified" and target["position_mass"] == 24
        assert target["member_count"] == 2 and target["complete_file_membership"]
        assert target["sequence_ref"] is None and "length" not in target and "unit" not in target
        assert len(problem["subject_refs"]) == store.db.execute("SELECT count(*) FROM inputs").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM records WHERE record_type='read_subject'").fetchone()[0] == 0
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='library_members'").fetchone()
        before = store.db.execute("SELECT count(*) FROM artifacts").fetchone()[0]
        reads = members(store, target)
        assert len(reads) == 2 and reads[0]["member_ref"] != reads[1]["member_ref"]
        assert all(row["unit"] == "symbol" and row["role"] == "read" for row in reads)
        assert store.db.execute("SELECT count(*) FROM artifacts").fetchone()[0] == before
        assert store.coverage(target["id"]) == []
        with pytest.raises(ContractError, match="library_scope_requires_streamed_geometry"):
            store.scope_coverage()
        result = ToolRegistry(store).execute("sequence.inspect", {"subject_ref": target["id"]})
        assert result["status"] == "invalid" and result["feedback"]["code"] == "library_is_not_a_sequence_operand"
        assert store.current_annotations() == []


def test_read_identity_local_coordinates_native_quality_survive_reopening(tmp_path):
    path = tmp_path / "state"
    with Store(path) as store:
        problem, target = library(store, tmp_path, molecule="dna")
        reads = members(store, target)
        intervals = [store.coverage(row["id"])[0] for row in reads]
        assert len(store._merge_segments(intervals)) == 2
        assert intervals[0]["target_ref"] == intervals[1]["target_ref"] == target["id"]
        assert not store._covered_by([intervals[0]], [intervals[1]])
        assert store.scope_measure(None, target["id"]) == 24
        assert list(store.iter_scope_coverage()) == intervals
        saved = work(ToolRegistry(store), "library.read", {"subject_ref": reads[0]["id"], "offset": 2, "limit": 5}, operation_key="read-window")
        assert saved["sequence"] == "GTTGC" and saved["quality"] == "+~###"
        raw = store.get_artifact(store.get(target["source_refs"][0])["artifact_ref"])
        assert raw == READS
    with Store(path) as store:
        assert store.problem() == problem and store.targets() == [target]
        assert members(store, target) == reads
        assert work(ToolRegistry(store), "library.read", {"subject_ref": reads[0]["id"], "offset": 2, "limit": 5}, operation_key="read-window") == saved
        assert store.get(reads[0]["id"])["name"] == "same"
        assert store.get(reads[1]["id"])["description"] == "second native"
        assert store.roots(reads[0]["id"]) == [target["id"]]


def test_selected_members_and_intervals_bound_tools_records_forms_and_child_scope(tmp_path):
    with Store(tmp_path / "state") as store:
        _, target = library(store, tmp_path, molecule="dna")
        a, b = members(store, target)
        tools = ToolRegistry(store)
        selected = work(tools, "library.select", {"library_ref": target["id"], "member_refs": [a["member_ref"]]})
        scope = store.validate_scope(selected["scope"], parent_scope=store.validate_scope())
        assert store.scope_measure(scope, target["id"]) == 12
        assert store.scope_dimension_segments(scope, a["id"]) == [{"start": 0, "end": 12}]
        assert store.scope_dimension_segments(scope, b["id"]) == []
        for row in (a, b):
            work(tools, "sequence.view", {"subject_ref": row["id"], "molecule": "dna"})
        assert len(store.list("feature", scope)) == 1
        assert len(store.query_records("feature", scope)["records"]) == 1
        assert store.reference_subset([a["id"], b["id"]], scope) == [a["id"]]
        failed = tools.execute("sequence.inspect", {"subject_ref": b["id"]}, scope=scope)
        assert failed["status"] == "invalid"
        assert failed["feedback"]["code"] == "requested_measurement_outside_assigned_segments_or_members"
        with pytest.raises(ContractError, match="scope_members_outside_parent"):
            store.validate_scope({"subject_refs": [target["id"]]}, parent_scope=scope)
        selected_again = work(tools, "library.select", {"library_ref": target["id"], "ordinal_ranges": [{"start": 0, "end": 1}]})
        assert selected_again == selected
        segment = {**store.coverage(a["id"])[0], "start": 2, "end": 7}
        narrow = store.validate_scope({**scope, "segments": [segment]}, parent_scope=scope)
        assert store.scope_measure(narrow, target["id"]) == 5
        projected = work(tools, "sequence.view", {"subject_ref": a["id"], "molecule": "dna", "segments": [{"start": 2, "end": 7}]}, scope=narrow)
        product = store.get(projected["records"][0]["product_ref"])
        assert product["footprint"] == [segment]
        assert store.map_segments(product["id"], [{"start": 1, "end": 3}]) == [{**segment, "start": 3, "end": 5}]
        assert store.reference_subset([selected["selection"]["id"]], narrow) == [selected["selection"]["id"]]
        exported = export_annotation(store, tmp_path / "narrow.json", scope=narrow)
        document = json.loads(Path(exported["json"]["path"]).read_text())
        assert selected["selection"]["id"] in {row["id"] for row in document["records"]}
        assert document["eligible_footprint"] == [segment]


def test_native_translation_stays_on_original_read_and_cannot_cover_another(tmp_path):
    content = b"@a\nATGAAATTTGGG\n+\nIIIIIIIIIIII\n@b\nATGAAATTTGGG\n+\n!!!!!!!!!!!!\n"
    with Store(tmp_path / "state") as store:
        _, target = library(store, tmp_path, content, molecule="dna")
        a, b = members(store, target)
        tools = ToolRegistry(store)
        translated = work(tools, "sequence.translate", {"subject_ref": a["id"], "code": 11})
        product = store.get(translated["records"][0]["product_ref"])
        assert store.get_artifact(product["sequence_ref"]) == b"MKFG"
        assert product["mapping"]["path"][0]["subject_ref"] == a["id"]
        assert store.map_segments(product["id"], [{"start": 1, "end": 2}]) == [{"target_ref": target["id"],
            "member_ref": a["member_ref"], "start": 3, "end": 6, "unit": "nt"}]
        assert not store._covered_by(product["footprint"], store.coverage(b["id"]))


def test_partial_read_membership_is_explicit_and_external_selection_does_not_expand_it(tmp_path):
    content = READS + b"@bad\nACGT\n+\n!!\n"
    with Store(tmp_path / "state") as store:
        problem, target = library(store, tmp_path, content, molecule="dna")
        assert not target["complete_file_membership"] and target["member_count"] == 2 and target["position_mass"] == 24
        assert problem["intake_status"] == "partial"
        external = store.register_material(data=READS, role="read", molecule="dna", use="evidence")
        attempt = store.parse_material(external["id"])
        member = store.material_members(attempt["collection_ref"])["members"][0]
        with pytest.raises(ContractError, match="member_not_in_fixed_library"):
            store.read_subject_ref(target["id"], member["id"])
        work(ToolRegistry(store), "material.member", {"member_ref": member["id"]})
        assert store.problem() == problem and store.targets() == [target]
        assert store.scope_measure(None, target["id"]) == 24


def test_caller_library_declaration_groups_files_without_inventing_sample_or_pairing(tmp_path):
    for name in ("one.fq", "two.fq"):
        (tmp_path / name).write_bytes(READS)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 2, "entries": [
        {"path": name, "name": name, "library": "caller lib", "molecule": "dna"} for name in ("one.fq", "two.fq")]}))
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(manifest_path=manifest)
        target, = store.targets()
        assert target["collection_refs"] == problem["initial_collection_refs"]
        assert target["member_count"] == 4 and target["position_mass"] == 48 and target["sample_refs"] == []
        assert len(target["collection_refs"]) == 2
        assert store.list("material_link") == []
        all_reads = members(store, target)
        assert [row["ordinal"] for row in all_reads] == [0, 1, 2, 3]
        assert len({row["id"] for row in all_reads}) == 4


def test_batch_is_one_ordinary_tool_result_with_separate_native_member_observations(tmp_path):
    with Store(tmp_path / "state") as store:
        _, target = library(store, tmp_path, molecule="dna")
        reads = members(store, target)
        tools = ToolRegistry(store)
        args = {"subject_refs": [row["id"] for row in reads]}
        result = work(tools, "reads.inspect", args, operation_key="batch")
        assert result["count"] == 2 and len(result["records"]) == 2
        assert {row["subject_ref"] for row in result["records"]} == set(args["subject_refs"])
        observations = [store.get(row["observation_ref"]) for row in result["records"]]
        assert [row["subject_refs"] for row in observations] == [[ref] for ref in args["subject_refs"]]
        source = store.get(result["source_ref"])
        native = [json.loads(line) for line in store.get_artifact(source["artifact_ref"]).splitlines()]
        assert [row["subject_ref"] for row in native] == args["subject_refs"]
        assert store.current_annotations() == []
        assert work(tools, "reads.inspect", args, operation_key="batch") == result
        assert store.db.execute("SELECT count(*) FROM tool_operations WHERE name='reads.inspect'").fetchone()[0] == 1


def test_portable_export_keeps_member_identity_selection_and_no_library_chromosome(tmp_path):
    with Store(tmp_path / "state") as store:
        _, target = library(store, tmp_path, molecule="dna")
        a, b = members(store, target)
        tools = ToolRegistry(store)
        selected = work(tools, "library.select", {"library_ref": target["id"], "member_refs": [a["member_ref"]]})
        work(tools, "sequence.view", {"subject_ref": a["id"], "molecule": "dna"}, scope=selected["scope"])
        result = export_annotation(store, tmp_path / "out.gff3", format="gff3", scope=selected["scope"], include_artifacts=True, page_size=1)
        document = json.loads(Path(result["json"]["path"]).read_text())
        assert document["eligible_footprint"] is None
        assert document["eligible_geometry"][0]["position_mass"] == 12
        assert document["inputs"] == [target]
        reads = [row for row in document["records"] if row["record_type"] == "read_subject"]
        assert [row["id"] for row in reads] == [a["id"]]
        assert b["id"] not in {row["id"] for row in document["records"]}
        descriptor, = document["read_library_indexes"]
        path = tmp_path / descriptor["relative_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == descriptor["sha256"]
        with sqlite3.connect(path) as db:
            assert db.execute("SELECT read_ref FROM library_selection_members").fetchone()[0] == a["id"]
            assert json.loads(db.execute("SELECT data FROM inputs").fetchone()[0]) == target
        native_descriptor, = document["packed_material_indexes"]
        with sqlite3.connect(tmp_path / native_descriptor["relative_path"]) as db:
            native = [json.loads(row[0]) for row in db.execute("SELECT data FROM material_members ORDER BY ordinal")]
            assert {row["id"] for row in native} == {a["member_ref"], b["member_ref"]}
        gff = (tmp_path / "out.gff3").read_text()
        assert "##sequence-region" not in gff
        assert result["gff3"]["exclusion_counts"] == {"read_local_coordinates_retained_in_authoritative_json": 1}


def test_batch_native_alignments_share_single_operation_path_and_preserve_partial_work(tmp_path):
    with Store(tmp_path / "state") as store:
        _, target = library(store, tmp_path, molecule="dna")
        a, b = members(store, target)
        evidence = store.register_material(data=">external actual sequence\nACGTTGCAACGT\n", format="fasta", molecule="dna")
        parsed = store.parse_material(evidence["id"])
        member = store.material_members(parsed["collection_ref"])["members"][0]
        reference = store.material_reference(member["id"])
        tools = ToolRegistry(store)
        batch = tools.execute("reads.align", {"subject_refs": [a["id"], "read_subject_" + "0"*48, b["id"]],
            "reference_ref": reference["id"], "molecule": "dna", "mode": "local"}, operation_key="align-batch")
        assert batch["status"] == "partial", batch
        result = batch["result"]
        assert result["count"] == 3 and result["completed_count"] == 2
        assert result["errors"] == [{"row_index": 1, "subject_ref": "read_subject_" + "0"*48, "code": "unknown_reference"}]
        assert [row["subject_ref"] for row in result["records"]] == [a["id"], b["id"]]
        for row in result["records"]:
            observation = store.get(row["observation_ref"])
            assert observation["subject_refs"] == [row["subject_ref"]]
            assert observation["source_subject_refs"] == [reference["id"]]
            source = store.get(row["source_ref"])
            assert source["provider"] == "biopython.alignment"
            native = json.loads(store.get_artifact(source["artifact_ref"]))
            assert native["query_length"] == 12
            assert observation["operand_intervals"][0]["subject_ref"] == row["subject_ref"]
            assert observation["operand_intervals"][1]["subject_ref"] == reference["id"]
        site = work(tools, "sequence.sites", {"alignment_ref": result["records"][0]["observation_ref"], "positions": [0, 3]})
        assert [row["relationship"] for row in site["sites"]] == ["identical", "identical"]
        assert store.db.execute("SELECT count(*) FROM tool_operations WHERE name='reads.align'").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM tool_operations WHERE name='sequence.align'").fetchone()[0] == 0
        assert store.current_annotations() == []


def test_parent_form_namespaces_restrict_read_and_selection_references_to_scope(tmp_path):
    from gene_annotation_episode.runtime import Workflow
    with Store(tmp_path / "state") as store:
        _, target = library(store, tmp_path, molecule="dna")
        a, b = members(store, target)
        tools = ToolRegistry(store)
        chosen = work(tools, "library.select", {"library_ref": target["id"], "member_refs": [a["member_ref"]]})
        broader = work(tools, "library.select", {"library_ref": target["id"], "ordinal_ranges": [{"start": 0, "end": 2}]})
        workflow = Workflow.__new__(Workflow)
        workflow.store = store
        resolve = workflow.resolver(chosen["scope"])
        assert resolve(a["id"], "read_subject") and resolve(a["id"], "subject")
        assert not resolve(a["id"], "input") and not resolve(b["id"], "read_subject")
        assert resolve(chosen["selection"]["id"], "read_selection")
        # A genuinely examined dataset handle is contextual information, not
        # permission to enlarge the child's own fixed work scope.
        assert resolve(broader["selection"]["id"], "read_selection")


def test_existing_broad_interpretation_visible_on_child_overlap_without_broader_write_permission(tmp_path):
    from gene_annotation_episode.runtime import Workflow
    with Store(tmp_path / "state") as store:
        _, target = library(store, tmp_path, molecule="dna")
        a, b = members(store, target)
        tools = ToolRegistry(store)
        observed = work(tools, "sequence.inspect", {"subject_ref": a["id"]})
        hypothesis = store.put("hypothesis", {"subject_refs": [a["id"]], "predicate": "sequence_integrity",
            "value": {"type": "enum", "value": "unresolved"}, "context_refs": []}, origin="reasoning")
        assessment = store.put("assessment", {"hypothesis_ref": hypothesis["id"],
            "observation_ref": observed["observation_ref"], "relation": "does_not_discriminate",
            "applicability": "scope_limited", "extent_basis": "observed_extent", "condition_refs": [],
            "assumption_refs": [], "expected_revision": 0}, origin="reasoning")
        annotation = store.put("annotation", {"subject_ref": a["id"], "footprint_kind": "localized",
            "coherent_sets": [{"interpretations": [{"hypothesis_ref": hypothesis["id"], "disposition": "unresolved",
                "assessment_refs": [assessment["id"]]}], "context_refs": []}], "alternative_refs": [],
            "resolution": "unresolved", "expected_revision": 0}, origin="reasoning")
        narrow = {"subject_refs": [target["id"]], "segments": [{**store.coverage(a["id"])[0], "start": 4, "end": 8}]}
        assert store.current_annotations(narrow) == [annotation]
        assert store.query_records("annotation", narrow, current_only=True)["records"] == [annotation]
        assert store.list("hypothesis", narrow) == [hypothesis]
        assert store.count("annotation", narrow, current=True) == 1
        workflow = Workflow.__new__(Workflow)
        workflow.store = store
        resolve = workflow.resolver(narrow)
        assert resolve(annotation["id"], "annotation") and resolve(assessment["id"], "assessment")
        assert resolve(a["id"], "subject") and not resolve(b["id"], "subject")
        with pytest.raises(ContractError, match="record_outside_scope_segments"):
            store.put("feature", {"subject_ref": a["id"], "kind": "sequence_region", "segments": [{"start": 0, "end": 12}],
                "strand": "+", "context_refs": []}, origin="reasoning", scope=narrow)
        full = tools.execute("sequence.inspect", {"subject_ref": a["id"]}, scope=narrow)
        assert full["status"] == "invalid"
        local = work(tools, "sequence.view", {"subject_ref": a["id"], "molecule": "dna", "segments": [{"start": 4, "end": 8}]}, scope=narrow)
        assert store.coverage(local["records"][0]["product_ref"]) == narrow["segments"]
