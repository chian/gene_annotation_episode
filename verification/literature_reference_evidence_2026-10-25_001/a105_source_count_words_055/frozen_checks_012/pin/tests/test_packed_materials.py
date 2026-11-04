"""Packed read custody across tools and portable export; synthetic data only."""
import hashlib
import io
import json
from pathlib import Path
import sqlite3

from Bio.SeqIO.QualityIO import FastqGeneralIterator
import pytest

from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


REPRESENTATION = "packed_member_components_v1"
WRAPPED_FASTQ = (
    "@dup αβ exact 🧬\r\nACGT\r\nTGCA\r\n+\r\n!@+~\r\n@@##\r\n"
    "@dup second native\r\nTTTT\r\nAACC\r\n+\r\nIIII\r\n$$$$\r\n"
).encode("utf-8")


def execute(tools, name, args, **kwargs):
    result = tools.execute(name, args, **kwargs)
    assert result["status"] in {"completed", "partial"}, result
    return result["result"]


def native_fastq(content):
    return list(FastqGeneralIterator(io.StringIO(content.decode("utf-8"))))


def rows(store, collection_ref):
    return [json.loads(row[0]) for row in store.db.execute(
        "SELECT data FROM material_members WHERE collection_ref=? ORDER BY ordinal", (collection_ref,))]


def artifact_ids(store):
    return {row[0] for row in store.db.execute("SELECT id FROM artifacts")}


def component_bytes(db, member_ref, component, read_artifact):
    """Reconstruct independently from the public relational representation."""
    spans = list(db.execute(
        "SELECT s.part,s.start,s.end,c.artifact_ref FROM material_component_spans s "
        "JOIN material_pack_chunks c ON c.chunk_index=s.chunk_index "
        "JOIN material_members m ON m.id=s.member_ref AND m.parse_key=c.parse_key "
        "WHERE s.member_ref=? AND s.component=? ORDER BY s.part", (member_ref, component)))
    assert [row[0] for row in spans] == list(range(len(spans)))
    parts = []
    for _, start, end, artifact_ref in spans:
        chunk = read_artifact(artifact_ref)
        assert 0 <= start < end <= len(chunk)
        parts.append(chunk[start:end])
    return b"".join(parts)


def check_packed_native(store, member, title, sequence, quality):
    assert member["storage"]["representation"] == REPRESENTATION
    assert {field: member[field] for field in ("header_ref", "sequence_ref", "quality_ref")} == {
        "header_ref": None, "sequence_ref": None, "quality_ref": None}
    expected = {"header": title.encode("utf-8"), "sequence": sequence.encode("ascii"),
                "quality": quality.encode("ascii") if quality is not None else None}
    for component, data in expected.items():
        metadata = member["storage"]["components"][component]
        if data is None:
            assert metadata is None
            assert component_bytes(store.db, member["id"], component, store.get_artifact) == b""
        else:
            assert metadata == {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
            assert component_bytes(store.db, member["id"], component, store.get_artifact) == data


def test_wrapped_fastq_keeps_native_quality_metadata_without_per_read_artifacts(tmp_path):
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(raw_sequence="MKWV", molecule="protein")
        material = store.register_material(data=WRAPPED_FASTQ, role="read", quality_encoding="unspecified")
        original = store.get(material["source_ref"])
        before = artifact_ids(store)
        attempt = store.parse_material(material["id"])
        collection = store.get(attempt["collection_ref"])
        assert attempt["status"] == "completed" and attempt["valid_records"] == 2
        assert collection["storage_representation"] == REPRESENTATION
        members = rows(store, collection["id"])
        assert [member["name"] for member in members] == ["dup", "dup"]
        assert [member["occurrence"] for member in members] == [0, 1]
        assert [member["ordinal"] for member in members] == [0, 1]
        assert "duplicate_source_identifier" in members[1]["issues"]
        assert all(member["source_byte_offset"] is None and member["molecule"] == "unspecified" for member in members)
        for member, native in zip(members, native_fastq(WRAPPED_FASTQ), strict=True):
            check_packed_native(store, member, *native)
        chunks = list(store.db.execute("SELECT artifact_ref FROM material_pack_chunks WHERE parse_key=?", (attempt["parse_key"],)))
        assert len(chunks) == 1
        assert artifact_ids(store) - before == {chunks[0][0]}
        page = store.material_members(collection["id"], limit=1)
        assert page["members"][0]["quality_present"]
        assert page["members"][0]["quality_encoding"] == "unspecified"
        assert page["next_query"]["offset"] == 1
        assert store.get_artifact(original["artifact_ref"]) == WRAPPED_FASTQ
        assert store.problem() == problem and store.list("reference") == []
        assert project_credit(store).as_record()["credit"] == 0


def test_components_cross_chunks_and_unicode_header_windows_remain_exact(tmp_path, monkeypatch):
    import gene_annotation_episode.materials_packing as packing
    monkeypatch.setattr(packing, "CHUNK_BYTES", 64)
    title = "αβ" * 70 + " 🧬 exact title"
    sequence, quality = "ACGT" * 75, "!@+~" * 75
    content = ("@" + title + "\n" + sequence + "\n+\n" + quality + "\n").encode("utf-8")
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWV")
        material = store.register_material(data=content)
        attempt = store.parse_material(material["id"])
        assert attempt["status"] == "completed"
        member, = rows(store, attempt["collection_ref"])
        check_packed_native(store, member, title, sequence, quality)
        chunks = list(store.db.execute("SELECT artifact_ref FROM material_pack_chunks WHERE parse_key=?", (attempt["parse_key"],)))
        assert len(chunks) > 3
        assert all(0 < store.get(row[0])["size"] <= 64 for row in chunks)
        for component in ("header", "sequence", "quality"):
            assert store.db.execute("SELECT count(*) FROM material_component_spans WHERE member_ref=? AND component=?",
                                    (member["id"], component)).fetchone()[0] > 1
        args, fragments = {"member_ref": member["id"], "limit": 17}, []
        while args:
            page = store.material_header(**args)
            exact = store.get_artifact(page["artifact_ref"])
            assert exact == title.encode("utf-8")
            assert exact[page["start"]:page["end"]] == page["text"].encode("utf-8")
            fragments.append(page["text"])
            args = page["next_query"]
        assert "".join(fragments) == title
        with pytest.raises(ContractError, match="header_offset_not_utf8_boundary"):
            store.material_header(member["id"], offset=1, limit=4)
        selected = execute(ToolRegistry(store), "material.member", {"member_ref": member["id"], "offset": 61, "limit": 13})
        assert selected["sequence"] == sequence[61:74] and selected["quality"] == quality[61:74]
        assert store.get_artifact(store.get(selected["reference_ref"])["sequence_ref"]) == sequence.encode("ascii")


def test_malformed_fastq_preserves_packed_valid_prefix_and_original_bytes(tmp_path, monkeypatch):
    import gene_annotation_episode.materials_packing as packing
    monkeypatch.setattr(packing, "CHUNK_BYTES", 11)
    content = b"@good native\nACGTACGT\n+\n!@+~####\n@bad\nACGT\n+\n!!\n"
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(raw_sequence="MKWV")
        material = store.register_material(data=content)
        attempt = store.parse_material(material["id"])
        assert attempt["status"] == "partial" and attempt["valid_records"] == 1
        assert attempt["error_count"] == 1 and not store.get(attempt["collection_ref"])["complete"]
        member, = rows(store, attempt["collection_ref"])
        check_packed_native(store, member, "good native", "ACGTACGT", "!@+~####")
        assert store.material_errors(attempt["id"])["errors"] == [{"ordinal": 1, "byte_offset": None,
            "code": "malformed_fastq_remaining_scope_unparsed"}]
        selected = execute(ToolRegistry(store), "material.member", {"member_ref": member["id"]})
        assert selected["sequence"] == "ACGTACGT" and selected["quality"] == "!@+~####"
        assert store.get_artifact(store.get(material["source_ref"])["artifact_ref"]) == content
        assert store.problem() == problem and project_credit(store).as_record()["credit"] == 0


def test_read_fasta_explicit_fragment_binding_stays_fixed_after_evidence_selection(tmp_path):
    source = tmp_path / "reads.fa"
    source.write_text(">same first\nACGT\n>same selected exact\nTGCAA\n>third\nCCCCCC\n")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 2, "entries": [{"path": source.name,
        "role": "read", "molecule": "dna", "target_records": [1]}]}))
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(manifest_path=manifest)
        target, = store.targets()
        assert target["name"] == "same" and target["description"] == "selected exact"
        assert target["source_record"]["ordinal"] == 1 and target["source_record"]["occurrence"] == 1
        assert store.get_artifact(target["sequence_ref"]) == b"TGCAA"
        assert store.scope_coverage() == [{"target_ref": target["id"], "start": 0, "end": 5, "unit": "nt"}]
        before = project_credit(store).as_record()
        members = rows(store, problem["initial_collection_refs"][0])
        for member, title, sequence in zip(members, ("same first", "same selected exact", "third"),
                                           ("ACGT", "TGCAA", "CCCCCC"), strict=True):
            check_packed_native(store, member, title, sequence, None)
        selected = execute(ToolRegistry(store), "material.member", {"member_ref": members[2]["id"]})
        assert selected["quality"] is None
        assert store.coverage(selected["reference_ref"]) == []
        late = store.register_material(data=b">later\nAAAAAAAAAAAAAAAA\n", role="read")
        store.parse_material(late["id"])
        assert store.problem() == problem and store.targets() == [target]
        assert project_credit(store).as_record() == before
        assert rows(store, problem["initial_collection_refs"][0]) == members


def test_selected_reference_and_operation_cache_survive_reopen_and_feed_alignment(tmp_path):
    workspace = tmp_path / "state"
    with Store(workspace) as store:
        problem = store.create_problem(raw_sequence="ACGTTGCA", molecule="dna")
        material = store.register_material(data=WRAPPED_FASTQ, molecule="dna")
        attempt = store.parse_material(material["id"])
        native = rows(store, attempt["collection_ref"])
        tools = ToolRegistry(store)
        result = execute(tools, "material.member", {"member_ref": native[0]["id"], "offset": 1, "limit": 3},
                         operation_key="selected-read")
        reference = store.get(result["reference_ref"])
        assert store.get_artifact(reference["sequence_ref"]) == b"ACGTTGCA"
        assert reference["source_ref"] == native[0]["source_ref"]
        assert store.reference_subset([reference["id"], reference["sequence_ref"]]) == [reference["id"], reference["sequence_ref"]]
        artifacts = artifact_ids(store)
        assert rows(store, attempt["collection_ref"]) == native
    with Store(workspace) as store:
        assert store.parse_material(material["id"]) == attempt
        replay = execute(ToolRegistry(store), "material.member", {"member_ref": native[0]["id"], "offset": 1, "limit": 3},
                         operation_key="selected-read")
        assert replay == result and artifact_ids(store) == artifacts
        alignment = execute(ToolRegistry(store), "sequence.align", {"query_ref": problem["subject_refs"][0],
                            "reference_ref": result["reference_ref"], "molecule": "dna", "mode": "global"})
        observation = store.get(alignment["observation_ref"])
        assert observation["source_subject_refs"] == [result["reference_ref"]]
        assert observation["subject_refs"] == problem["subject_refs"]
        assert store.get_artifact(store.get(result["reference_ref"])["sequence_ref"]) == b"ACGTTGCA"
        assert store.problem() == problem and project_credit(store).as_record()["credit"] == 0


def test_portable_index_reconstructs_all_reads_without_exporting_unselected_tiny_files(tmp_path, monkeypatch):
    import gene_annotation_episode.materials_packing as packing
    monkeypatch.setattr(packing, "CHUNK_BYTES", 64)
    native = [(f"read_{index} native α {index}", "ACGT" * 7 + "A" * index,
               "!@+~" * 7 + "#" * index) for index in range(12)]
    content = "".join(f"@{title}\n{sequence}\n+\n{quality}\n" for title, sequence, quality in native).encode("utf-8")
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(raw_sequence="MKWV", molecule="protein")
        material = store.register_material(data=content)
        attempt = store.parse_material(material["id"])
        members = rows(store, attempt["collection_ref"])
        selected = execute(ToolRegistry(store), "material.member", {"member_ref": members[4]["id"], "limit": 2})
        before = artifact_ids(store)
        exported = export_annotation(store, tmp_path / "portable.json", include_artifacts=True, page_size=2)
        document = json.loads(Path(exported["json"]["path"]).read_text())
        descriptor, = document["packed_material_indexes"]
        assert set(descriptor) == {"format", "schema_version", "storage_representation", "parse_ref", "parse_key",
            "collection_ref", "member_count", "relative_path", "sha256", "bytes", "chunk_count", "content_included"}
        assert descriptor["format"] == "gene_annotation_episode.packed_material_index" and descriptor["schema_version"] == 1
        assert descriptor["storage_representation"] == REPRESENTATION and descriptor["content_included"]
        assert descriptor["parse_ref"] == attempt["id"] and descriptor["parse_key"] == attempt["parse_key"]
        assert descriptor["collection_ref"] == attempt["collection_ref"] and descriptor["member_count"] == len(native)
        index_path = Path(exported["json"]["path"]).parent / descriptor["relative_path"]
        index_bytes = index_path.read_bytes()
        assert len(index_bytes) == descriptor["bytes"] and hashlib.sha256(index_bytes).hexdigest() == descriptor["sha256"]
        artifacts = {row["id"]: row for row in document["artifacts"]}
        def read_exported(ref):
            artifact = artifacts[ref]
            value = (Path(exported["json"]["path"]).parent / artifact["relative_path"]).read_bytes()
            assert len(value) == artifact["size"] and hashlib.sha256(value).hexdigest() == artifact["sha256"]
            return value
        with sqlite3.connect(index_path) as index:
            portable = [json.loads(row[0]) for row in index.execute("SELECT data FROM material_members ORDER BY ordinal")]
            assert portable == members
            assert index.execute("SELECT count(*) FROM material_pack_chunks").fetchone()[0] == descriptor["chunk_count"]
            assert {row[0] for row in index.execute("SELECT id FROM artifacts")} == {
                row[0] for row in index.execute("SELECT DISTINCT artifact_ref FROM material_pack_chunks")}
            for member, expected in zip(portable, native, strict=True):
                for component, value in zip(("header", "sequence", "quality"), expected, strict=True):
                    assert component_bytes(index, member["id"], component, read_exported) == value.encode("utf-8")
        main_member_ids = {row["id"] for row in document["records"] if row["record_type"] == "collection_member"}
        packed_ids = {member["id"] for member in members}
        assert main_member_ids & packed_ids == {members[4]["id"]}
        selected_reference = store.get(selected["reference_ref"])
        assert selected_reference["sequence_ref"] in artifacts
        for component in ("header", "sequence", "quality"):
            selected_id = "artifact_" + members[4]["storage"]["components"][component]["sha256"]
            assert selected_id in artifacts
        selected_hashes = {part["sha256"] for part in members[4]["storage"]["components"].values()}
        for member in members:
            if member["id"] == members[4]["id"]:
                continue
            for component in member["storage"]["components"].values():
                if component["sha256"] not in selected_hashes:
                    assert "artifact_" + component["sha256"] not in artifacts
        assert artifact_ids(store) == before and store.problem() == problem


def test_header_only_materialization_remains_outside_form_registry_until_member_selection(tmp_path):
    title = "αβ native title only"
    content = ("@" + title + "\nACGT\n+\n!@+~\n").encode("utf-8")
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWV")
        material = store.register_material(data=content)
        attempt = store.parse_material(material["id"])
        member, = rows(store, attempt["collection_ref"])
        header = execute(ToolRegistry(store), "material.header", {"member_ref": member["id"]})
        header_id = "artifact_" + hashlib.sha256(title.encode("utf-8")).hexdigest()
        assert header["artifact_ref"] == header_id and store.get_artifact(header_id) == title.encode("utf-8")
        assert header["start"] == 0 and header["end"] == len(title.encode("utf-8"))
        assert not header["original_header_bytes"]
        assert store.reference_subset([header_id]) == []
        assert header_id not in store.references()["artifact"] and store.list("reference") == []
        selected = execute(ToolRegistry(store), "material.member", {"member_ref": member["id"], "limit": 1})
        component_refs = ["artifact_" + item["sha256"] for item in member["storage"]["components"].values()]
        assert store.reference_subset(component_refs) == component_refs
        assert set(component_refs) <= set(store.references()["artifact"])
        assert store.get(selected["reference_ref"])["member_ref"] == member["id"]
        assert store.get(member["id"]) == member


def test_packed_external_fastq_retains_actual_source_request_and_origin(tmp_path):
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(raw_sequence="MKWV", molecule="protein")
        artifact = store.artifact(WRAPPED_FASTQ, "text/plain")
        request = store.artifact(json.dumps({"provider_parameter": "fixture_only"}), "application/json")
        source = store.put("source", {"provider": "fixture_external_reads", "accession": "fixture-readset",
            "uri": "https://example.invalid/reads.fastq", "artifact_ref": artifact, "text_ref": artifact,
            "request_ref": request, "version": "fixture1", "retrieved_at": None}, origin="external")
        tools = ToolRegistry(store)
        wrapped = execute(tools, "material.from_source", {"source_ref": source["id"]})
        material = store.get(wrapped["material_ref"])
        assert material["origin"] == "tool" and material["use"] == "evidence"
        attempt = execute(tools, "material.parse", {"material_ref": material["id"]})["parse_attempt"]
        member, second = rows(store, attempt["collection_ref"])
        assert member["source_ref"] == second["source_ref"] == source["id"]
        selected = execute(tools, "material.member", {"member_ref": second["id"]})
        assert store.get(selected["reference_ref"])["source_ref"] == source["id"]
        assert selected["sequence"] == native_fastq(WRAPPED_FASTQ)[1][1]
        assert store.get(source["id"]) == source and store.get_artifact(artifact) == WRAPPED_FASTQ
        assert store.get_artifact(source["request_ref"]) == store.get_artifact(request)
        assert store.problem() == problem and len(store.targets()) == 1
        assert project_credit(store).as_record()["credit"] == 0
