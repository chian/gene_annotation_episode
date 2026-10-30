"""Actual custody/index/tool paths; synthetic data are not biological validation."""
import base64
import gzip
import hashlib
from importlib.metadata import version
import json
import sqlite3
from pathlib import Path

import pytest

from gene_annotation_episode.cli import main
from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def manifest(tmp_path, entries):
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps({"schema_version": 2, "entries": entries}))
    return path


def target():
    return {"sequence": "MKWV", "name": "target", "molecule": "protein"}


def call(tools, name, args, **kwargs):
    result = tools.execute(name, args, **kwargs)
    assert result["status"] in {"completed", "partial"}, result
    return result["result"]


def test_repeated_semantic_target_is_listed_once_with_original_manifest_occurrences(tmp_path):
    entries = [target(), target(), {"sequence": "MAAA", "name": "other", "molecule": "protein"}]
    path = manifest(tmp_path, entries)
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(manifest_path=path)
        assert len(problem["subject_refs"]) == len(set(problem["subject_refs"])) == 2
        assert store.db.execute("SELECT COUNT(*) FROM inputs").fetchone()[0] == 2
        assert len(problem["material_refs"]) == 3
        assert problem["material_refs"][0] == problem["material_refs"][1]
        assert json.loads(store.get_artifact(problem["manifest_ref"]))["entries"] == entries
        assert [row["name"] for row in store.targets()] == ["target", "other"]
        projection = project_credit(store).as_record()
        assert len(projection["targets"]) == 2 and projection["credit"] == 0
        view = store.reasoning_view()
        assert len(view["subjects"]) == len(view["scope"]["subject_refs"]) == 2
        call(ToolRegistry(store), "sequence.inspect", {"subject_ref": problem["subject_refs"][0]})
        assert store.problem() == problem


@pytest.mark.parametrize("declarations", [
    ({"sample": "S1"}, {"sample": "S2"}),
    ({"context": {"reported_temperature": 37}}, {"context": {"reported_temperature": 55}}),
])
def test_equal_sequences_with_distinct_caller_contexts_remain_distinct_targets(tmp_path, declarations):
    path = manifest(tmp_path, [{**target(), **declaration} for declaration in declarations])
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(manifest_path=path)
        assert len(problem["subject_refs"]) == len(set(problem["subject_refs"])) == 2
        first, second = store.targets()
        assert first["sequence_ref"] == second["sequence_ref"]
        assert (first["sample_ref"], first["context_source_refs"]) != (second["sample_ref"], second["context_source_refs"])
        assert len(project_credit(store).as_record()["targets"]) == 2
        assert len(store.reasoning_view()["subjects"]) == 2


def test_explicit_uncertain_single_read_is_target(tmp_path):
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(raw_sequence="AT?N", molecule="dna", role="read")
        assert problem["target_binding"] == "sequence_targets"
        row, = store.targets()
        assert row["role"] == "read"
        assert store.get_artifact(row["sequence_ref"]) == b"AT?N"
        assert row["input_issues"] == ["unexpected_symbol_for_declared_molecule"]
        assert store.list("feature") == []


def test_member_reference_rejects_different_same_length_native_sequence(tmp_path):
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWV", molecule="protein")
        material = store.register_material(data=b">a\nACGT\n>b\nTTTT\n")
        attempt = store.parse_material(material["id"])
        first, second = [store.get(row["id"]) for row in
                         store.material_members(attempt["collection_ref"])["members"]]
        actual = store.material_reference(first["id"])
        assert actual["member_ref"] == first["id"]
        assert actual["sequence_ref"] == first["sequence_ref"]
        assert store.get_artifact(actual["sequence_ref"]) == b"ACGT"
        wrong = {key: value for key, value in actual.items()
                 if key not in {"id", "record_type", "origin"}}
        wrong["sequence_ref"] = second["sequence_ref"]
        assert first["length"] == second["length"]
        assert store.get_artifact(wrong["sequence_ref"]) == b"TTTT"
        with pytest.raises(ContractError, match="member_reference_identity_mismatch"):
            store.put("reference", wrong, origin="tool")
        assert store.list("reference") == [actual]
        with pytest.raises(ContractError, match="subject_has_no_input_mapping"):
            store.sequence_mapping(material["id"])


@pytest.mark.parametrize("content,representation", [
    (b"growth\tph\nobserved\t7\n", "unknown"),
    (b'{"organism": "unknown"}', "unknown"),
    (b"\x00\xff\x80binary", "unknown"),
])
def test_auto_unknown_assets_remain_bytes_not_sequences(tmp_path, content, representation):
    path = tmp_path / "supplied.data"
    path.write_bytes(content)
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(path)
        assert problem["subject_refs"] == []
        assert store.targets() == []
        attempt = store.get(problem["initial_parse_refs"][0])
        assert attempt["status"] == "unavailable"
        assert attempt["representation"] == representation
        material = store.get(problem["material_refs"][0])
        source = store.get(material["source_ref"])
        assert store.get_artifact(source["artifact_ref"]) == content
        assert store.get(source["artifact_ref"])["sha256"] == hashlib.sha256(content).hexdigest()
        tools = ToolRegistry(store)
        page = call(tools, "material.read", {"material_ref": material["id"], "offset": 1, "limit": 3})
        assert base64.b64decode(page["content"]) == content[1:4]
        assert call(tools, "state.query", {"kind": "material"})["records"][0]["id"] == material["id"]


def test_mixed_evidence_fastq_order_qualities_links_and_fixed_targets(tmp_path):
    (tmp_path / "reads.fq").write_bytes(b"@r repeated\nACGT\n+\n!@+~\n@r duplicate\nTGCA\n+\n####\n")
    path = manifest(tmp_path, [target(), {"path": "reads.fq", "name": "left", "use": "evidence",
        "role": "read", "sample": "S1", "library": "L1", "quality_encoding": "phred33",
        "links": [{"relation": "paired_with", "name": "right"}]},
        {"sequence": "NNNN", "name": "right", "use": "evidence", "role": "read", "sample": "S1", "library": "L1"}])
    with Store(tmp_path / "state") as store:
        initial = store.create_problem(manifest_path=path)
        targets = store.targets()
        before = project_credit(store).as_record()
        assert len(targets) == 1
        reads = next(row for row in store.list("collection") if row["representation"] == "fastq")
        assert reads["member_count"] == 2 and reads["sequence_symbols"] == 8
        tools = ToolRegistry(store)
        first = call(tools, "material.members", {"collection_ref": reads["id"], "limit": 1})
        second = call(tools, "material.members", first["next_query"])
        assert [first["members"][0]["ordinal"], second["members"][0]["ordinal"]] == [0, 1]
        assert second["members"][0]["occurrence"] == 1
        assert "duplicate_source_identifier" in second["members"][0]["issues"]
        assert "sequence_ref" not in first["members"][0]
        member = call(tools, "material.member", {"member_ref": first["members"][0]["id"], "offset": 1, "limit": 2})
        assert (member["sequence"], member["quality"]) == ("CG", "@+")
        reference = store.get(member["reference_ref"])
        assert reference["molecule"] == "unspecified"
        assert store.coverage(reference["id"]) == []
        assert reads["sample_ref"] in reference["context_refs"]
        assert reads["library_ref"] in reference["context_refs"]
        assert member["member"]["quality_encoding"] == "phred33"
        assert store.list("material_link")[0]["relation"] == "paired_with"
        call(tools, "sequence.inspect", {"subject_ref": reference["id"]})
        late = store.register_material(data=b"another unknown report", name="later")
        assert store.parse_material(late["id"])["status"] == "unavailable"
        assert store.problem() == initial and store.targets() == targets
        after = project_credit(store).as_record()
        assert after["credit"] == before["credit"] == 0
        assert len(after["targets"]) == 1


def test_partial_fasta_retains_independent_records_and_source_ordinals(tmp_path):
    content = b">same good\nACGT\n>same empty\n>same recovered\nTGCA\n"
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWV", molecule="protein")
        material = store.register_material(data=content, name="partial")
        result = ToolRegistry(store).execute("material.parse", {"material_ref": material["id"]})
        assert result["status"] == "partial"
        attempt = result["result"]["parse_attempt"]
        assert attempt["valid_records"] == 2 and attempt["error_count"] == 1
        page = store.material_members(attempt["collection_ref"])
        assert [row["ordinal"] for row in page["members"]] == [0, 2]
        assert [row["occurrence"] for row in page["members"]] == [0, 2]
        errors = store.material_errors(attempt["id"])["errors"]
        assert errors[0]["ordinal"] == 1
        assert errors[0]["byte_offset"] == content.index(b">same empty")
        assert store.get_artifact(store.get(material["source_ref"])["artifact_ref"]) == content
        assert attempt["collection_ref"] in result["record_refs"]


def test_malformed_fastq_keeps_valid_prefix_and_marks_remainder_unparsed(tmp_path):
    content = b"@good\nACGT\n+\n!!!!\n@bad\nACGT\n+\n!!\n"
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(raw_sequence="MKWV")
        material = store.register_material(data=content)
        attempt = store.parse_material(material["id"])
        assert attempt["status"] == "partial" and attempt["valid_records"] == 1
        assert attempt["parser_version"].endswith("biopython_" + version("biopython"))
        assert not store.get(attempt["collection_ref"])["complete"]
        error, = store.material_errors(attempt["id"])["errors"]
        assert error == {"ordinal": 1, "byte_offset": None, "code": "malformed_fastq_remaining_scope_unparsed"}
        assert store.problem() == problem


def test_read_library_is_bound_without_per_read_targets(tmp_path):
    path = tmp_path / "reads.fa"
    path.write_text(">a\nACGT\n>b\nTGCA\n")
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(path, role="read")
        target, = store.targets()
        assert problem["target_binding"] == "fixed_original_read_libraries_and_sequences"
        assert target["target_kind"] == "read_library" and target["position_mass"] == 8
        assert problem["intake_feedback"] == []
        assert store.get(problem["initial_collection_refs"][0])["member_count"] == 2
        tools = ToolRegistry(store)
        member = call(tools, "material.members", {"collection_ref": problem["initial_collection_refs"][0]})["members"][0]
        reference = call(tools, "material.member", {"member_ref": member["id"]})["reference_ref"]
        call(tools, "sequence.inspect", {"subject_ref": reference})
        assert store.targets() == [target]
        assert store.coverage(reference) == []


def test_caller_can_select_actual_fragment_without_read_role_gate(tmp_path):
    (tmp_path / "reads.fq").write_text("@a\nACGT\n+\n!!!!\n@b\nTGCA\n+\n####\n")
    path = manifest(tmp_path, [{"path": "reads.fq", "role": "read", "target_records": [1]}])
    with Store(tmp_path / "state") as store:
        store.create_problem(manifest_path=path)
        row, = store.targets()
        assert row["name"] == "b" and store.get_artifact(row["sequence_ref"]) == b"TGCA"
        assert row["source_record"]["ordinal"] == 1


def test_gzip_lineage_cache_reopen_and_bounded_members(tmp_path, monkeypatch):
    raw = b">a\nACGT\n>b\nTGCA\n"
    packed = gzip.compress(raw, mtime=0)
    workspace = tmp_path / "state"
    with Store(workspace) as store:
        problem = store.create_problem(raw_sequence="MKWV")
        material = store.register_material(data=packed, name="compressed")
        attempt = store.parse_material(material["id"])
        assert attempt["compression"] == "gzip"
        original = store.get(material["source_ref"])
        decoded = store.get(attempt["source_ref"])
        assert store.get_artifact(original["artifact_ref"]) == packed
        assert store.get_artifact(decoded["artifact_ref"]) == raw
        request = json.loads(store.get_artifact(decoded["request_ref"]))
        assert request["source_ref"] == original["id"]
        assert store.parse_material(material["id"]) == attempt
        tools = ToolRegistry(store)
        monkeypatch.setattr(store, "get_artifact", lambda *a, **k: pytest.fail("bounded reads must not hydrate an artifact"))
        page = call(tools, "material.members", {"collection_ref": attempt["collection_ref"], "limit": 1})
        selected = call(tools, "material.member", {"member_ref": page["members"][0]["id"], "limit": 2}, operation_key="member-window")
        assert selected["sequence"] == "AC"
        window = call(tools, "source.read", {"source_ref": decoded["id"], "offset": 1, "limit": 3})
        assert window["text"] == "a\nA"
    with Store(workspace) as store:
        assert store.problem() == problem
        assert store.parse_material(material["id"]) == attempt
        replay = call(ToolRegistry(store), "material.member", {"member_ref": page["members"][0]["id"], "limit": 2}, operation_key="member-window")
        assert replay == selected
        assert store.db.execute("SELECT COUNT(*) FROM material_members").fetchone()[0] == 3  # original target + two evidence records


def test_registered_external_source_reused_without_origin_or_target_relabeling(tmp_path):
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(raw_sequence="MKWV", molecule="protein")
        body = store.artifact(b">actual_reference\nMAWV\n", "text/plain")
        source = store.put("source", {"provider": "fixture_public_supplement", "accession": "actual-supplement",
            "uri": "https://example.invalid/supplement.faa", "artifact_ref": body, "text_ref": body,
            "request_ref": None, "version": "fixture1", "retrieved_at": None}, origin="external")
        tools = ToolRegistry(store)
        material = call(tools, "material.from_source", {"source_ref": source["id"]}, operation_key="source-wrapper")
        wrapper = store.get(material["material_ref"])
        assert wrapper["origin"] == "tool" and wrapper["use"] == "evidence"
        assert wrapper["source_ref"] == source["id"] and wrapper["name"] == "actual-supplement"
        attempt = call(tools, "material.parse", {"material_ref": wrapper["id"]})["parse_attempt"]
        member = store.material_members(attempt["collection_ref"])["members"][0]
        selected = call(tools, "material.member", {"member_ref": member["id"]})
        assert store.get(selected["reference_ref"])["source_ref"] == source["id"]
        call(tools, "sequence.inspect", {"subject_ref": selected["reference_ref"]})
        assert store.get(source["id"]) == source
        assert store.problem() == problem and len(store.targets()) == 1
        bad = tools.execute("material.from_source", {"source_ref": source["id"], "path": "/tmp/not-permitted"})
        assert bad["status"] == "invalid"


def test_failed_independent_entry_retains_other_targets_and_manifest(tmp_path):
    (tmp_path / "broken.fq").write_text("@bad\nACGT\n+\n!\n")
    path = manifest(tmp_path, [target(), {"path": "broken.fq", "use": "evidence"}, {"path": "missing.faa"}])
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(manifest_path=path)
        assert len(store.targets()) == 1
        assert len(problem["material_refs"]) == 2
        assert store.get_artifact(problem["manifest_ref"]) == path.read_bytes()
        assert problem["intake_status"] == "partial"
        broken = store.get(problem["initial_parse_refs"][1])
        assert broken["status"] == "failed" and broken["valid_records"] == 0
        assert store.get(store.get(problem["material_refs"][1])["source_ref"])["artifact_ref"]


def test_portable_export_keeps_material_members_and_quality_reference_closure(tmp_path):
    (tmp_path / "reads.fq").write_text("@a\nACGT\n+\n!@+~\n@b\nTGCA\n+\n####\n")
    path = manifest(tmp_path, [target(), {"path": "reads.fq", "use": "evidence"}])
    with Store(tmp_path / "state") as store:
        store.create_problem(manifest_path=path)
        result = export_annotation(store, tmp_path / "result.gff3", format="gff3", include_artifacts=True, page_size=1)
        data = json.loads(Path(result["json"]["path"]).read_text())
        assert len(data["inputs"]) == 1
        members = [row for row in data["records"] if row["record_type"] == "collection_member"]
        assert len(members) == 1  # unexamined read inventory lives in its packed index
        artifacts = {row["id"]: row for row in data["artifacts"]}
        for member in members:
            assert member["sequence_ref"] in artifacts
            if member["quality_ref"]:
                artifact = artifacts[member["quality_ref"]]
                saved = Path(result["json"]["path"]).parent / artifact["relative_path"]
                assert hashlib.sha256(saved.read_bytes()).hexdigest() == artifact["sha256"]
        descriptor, = data["packed_material_indexes"]
        index_path = Path(result["json"]["path"]).parent / descriptor["relative_path"]
        assert hashlib.sha256(index_path.read_bytes()).hexdigest() == descriptor["sha256"]
        with sqlite3.connect(index_path) as index:
            assert index.execute("SELECT count(*) FROM material_members").fetchone()[0] == 2
            for member_id, native_data in index.execute("SELECT id,data FROM material_members ORDER BY ordinal"):
                native = json.loads(native_data)
                quality = bytearray()
                for chunk_ref, start, end in index.execute("SELECT c.artifact_ref,s.start,s.end FROM material_component_spans s JOIN material_pack_chunks c ON c.parse_key=? AND c.chunk_index=s.chunk_index WHERE s.member_ref=? AND s.component='quality' ORDER BY s.part", (native["storage"]["parse_key"], member_id)):
                    packed_file = Path(result["json"]["path"]).parent / artifacts[chunk_ref]["relative_path"]
                    quality.extend(packed_file.read_bytes()[start:end])
                assert hashlib.sha256(quality).hexdigest() == native["storage"]["components"]["quality"]["sha256"]
        assert not [line for line in Path(result["gff3"]["path"]).read_text().splitlines() if not line.startswith("#")]


def test_unbound_cli_run_reports_missing_binding_without_model_call(tmp_path, monkeypatch, capsys):
    import gene_annotation_episode.runtime as runtime
    monkeypatch.setattr(runtime, "run_workflow", lambda *a, **k: pytest.fail("unbound asset must not pretend to be a solved biological target"))
    path = tmp_path / "report.txt"
    path.write_text("reported growth conditions: unknown")
    workspace = tmp_path / "state"
    assert main(["init", "--workspace", str(workspace), "--input", str(path)]) == 0
    capsys.readouterr()
    assert main(["run", "--workspace", str(workspace)]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["code"] == "biological_target_binding_unavailable"
    assert result["scientific_completion"] == "not_established"


def test_invalid_manifest_and_failed_gzip_still_have_original_custody(tmp_path):
    path = tmp_path / "dataset.json"
    path.write_bytes(b"{broken manifest")
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(manifest_path=path)
        assert problem["target_binding"] == "unresolved"
        assert store.get_artifact(problem["manifest_ref"]) == path.read_bytes()
        broken = store.register_material(data=b"\x1f\x8bmalformed", name="compressed")
        attempt = store.parse_material(broken["id"])
        assert attempt["status"] == "failed"
        assert store.material_errors(attempt["id"])["errors"][0]["code"] == "gzip_decode_incomplete"
        assert store.get_artifact(store.get(broken["source_ref"])["artifact_ref"]) == b"\x1f\x8bmalformed"
