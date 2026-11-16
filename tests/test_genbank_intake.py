"""Native intake/storage/tool/export contracts, not annotation accuracy tests."""
import gzip
import io
import json
from pathlib import Path

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import SeqFeature, SimpleLocation
from Bio.SeqRecord import SeqRecord
import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry


def body(identifier="FIXTURE.1", *, sequence="ATGAAATAA", features=None, molecule="DNA", note="synthetic native input"):
    record = SeqRecord(Seq(sequence), id=identifier, name=identifier.split(".")[0], description=note)
    record.annotations.update(molecule_type=molecule, topology="circular", organism="Source-asserted organism",
        taxonomy=["Source-asserted lineage"], comment="Original caller annotation, not verified here")
    record.features = features or []
    output = io.StringIO()
    SeqIO.write(record, output, "genbank")
    return output.getvalue().encode()


def contig(identifier="CONTIGONLY.1"):
    data = body(identifier)
    return data[:data.index(b"ORIGIN")] + b"CONTIG      join(REMOTE.1:1..3,gap(3),REMOTE.2:1..3)\n//\n"


def call(tools, name, args, **kwargs):
    result = tools.execute(name, args, **kwargs)
    assert result["status"] in {"completed", "partial"}, result
    return result


def native_entry(store, entry):
    source = store.get(entry["source_ref"])
    raw = store.get_artifact(source["artifact_ref"])
    return json.loads(raw[entry["start"]:entry["end"]])


def test_native_feature_pages_are_bounded_and_exact_full_qualifiers_remain_readable(tmp_path):
    qualifiers = {"note": ["π" * 100000], "translation": ["M" * 100000]}
    features = [SeqFeature(SimpleLocation(i, i+1), type="misc_feature", qualifiers=qualifiers if i == 0 else {})
                for i in range(3)]
    content = body(features=features)
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MACT")
        material = store.register_material(data=content, use="evidence")
        attempt = store.parse_material(material["id"])
        tools = ToolRegistry(store, run_directory=store.path / 'tool-run')
        first = call(tools, "material.annotations", {"parse_ref": attempt["id"], "kind": "feature", "limit": 1})["result"]
        assert first["total"] == 3 and len(json.dumps(first).encode()) < 5000
        second = call(tools, "material.annotations", first["next_query"])["result"]
        assert [first["entries"][0]["entry_ordinal"], second["entries"][0]["entry_ordinal"]] == [0, 1]
        entry = first["entries"][0]
        tiny = call(tools, "source.read", {**entry["read_with"], "limit": 128})["result"]
        assert len(tiny["text"].encode()) <= 128
        explicit = call(tools, "source.read", {**entry["read_with"], "limit": entry["end"]-entry["start"]})["result"]
        parsed = json.loads(explicit["text"])
        expected = SeqIO.read(io.StringIO(content.decode()), "genbank").features[0].qualifiers
        assert parsed["feature"]["qualifiers"] == expected
        assert explicit["start"] == entry["start"] and explicit["end"] == entry["end"]
        store._anchor({"source_ref": explicit["source_ref"], "artifact_ref": explicit["artifact_ref"],
            "start": tiny["start"], "end": tiny["end"]}, explicit["source_ref"])
        original = store.get(material["source_ref"])
        with pytest.raises(ContractError, match="anchor_source_mismatch"):
            store._anchor({"source_ref": original["id"], "artifact_ref": explicit["artifact_ref"],
                "start": tiny["start"], "end": tiny["end"]}, original["id"])


def test_metadata_only_caller_genbank_has_no_fabricated_sequence_target(tmp_path):
    content = contig()
    path = tmp_path / "contig.gb"
    path.write_bytes(content)
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(path)
        assert not problem["subject_refs"] and problem["target_binding"] == "unresolved"
        attempt = store.get(problem["initial_parse_refs"][0])
        assert attempt["status"] == "partial" and attempt["valid_records"] == 0
        assert attempt["code"] == "native_metadata_without_sequence_projection"
        assert store.material_members(attempt["collection_ref"])["members"] == []
        page = call(ToolRegistry(store, run_directory=store.path / 'tool-run'), "material.annotations", {"parse_ref": attempt["id"]})["result"]
        native = native_entry(store, page["entries"][0])
        assert native["record"]["sequence"]["length"] == 9 and native["record"]["sequence"]["defined"] is False
        assert not store.targets() and not store.list("feature")


def test_feature_projection_failure_preserves_sequence_and_independent_native_features(tmp_path, monkeypatch):
    import gene_annotation_episode.genbank_intake as native
    project = native.native_feature
    def fail_one(feature, index):
        if index == 1:
            raise TypeError("explicit synthetic projection failure")
        return project(feature, index)
    monkeypatch.setattr(native, "native_feature", fail_one)
    content = body(features=[SeqFeature(SimpleLocation(i, i+1), type="misc_feature") for i in range(3)])
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MACT")
        material = store.register_material(data=content)
        attempt = store.parse_material(material["id"])
        assert attempt["status"] == "partial" and attempt["valid_records"] == 1
        entries = store.material_annotations(attempt["id"], kind="feature")["entries"]
        assert [row["entry_ordinal"] for row in entries] == [0, 1, 2]
        failed = native_entry(store, entries[1])
        assert failed["feature"] is None and entries[1]["preview"]["metadata_available"] is False
        assert failed["projection_failure"] == {"class": "TypeError", "message": "explicit synthetic projection failure"}
        assert store.material_errors(attempt["id"])["errors"] == [{"ordinal": 0, "byte_offset": 0,
            "code": "genbank_feature_projection_failed", "feature_ordinal": 1}]
        assert native_entry(store, store.material_annotations(attempt["id"])["entries"][0])["record"]["feature_count"] == 3
        workspace = store.path
    with Store(workspace) as store:
        entries = store.material_annotations(attempt["id"], kind="feature")["entries"]
        assert native_entry(store, entries[1])["projection_failure"]["message"] == "explicit synthetic projection failure"
        exported = export_annotation(store, tmp_path / "projection-partial.json", include_artifacts=True)
        document = json.loads(Path(exported["json"]["path"]).read_text())
        assert len(document["native_material_annotations"]) == 4
        assert document["parse_errors"][0]["code"] == "genbank_feature_projection_failed"


def test_gzip_frame_coordinates_remain_decoded_source_coordinates_not_compressed_or_jsonl_bytes(tmp_path):
    raw = body("FIRST.1").removesuffix(b"//\n") + body("NEXT.1")
    compressed = gzip.compress(raw, mtime=0)
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MACT")
        material = store.register_material(data=compressed)
        attempt = store.parse_material(material["id"])
        assert attempt["status"] == "partial" and attempt["valid_records"] == 2
        assert attempt["compression"] == "gzip"
        original = store.get(material["source_ref"])
        decoded = store.get(attempt["source_ref"])
        native_source = store.get(attempt["native_source_ref"])
        assert store.get_artifact(original["artifact_ref"]) == compressed
        assert store.get_artifact(decoded["artifact_ref"]) == raw
        assert native_source["parent_source_refs"] == [decoded["id"]]
        request = json.loads(store.get_artifact(native_source["request_ref"]))
        assert request["original_material_source_ref"] == original["id"]
        assert request["input_source_ref"] == decoded["id"]
        page = store.material_annotations(attempt["id"])
        entries = [native_entry(store, entry) for entry in page["entries"]]
        assert [entry["record"]["id"] for entry in entries] == ["FIRST.1", "NEXT.1"]
        first_end = raw.index(b"LOCUS ", 1)
        assert entries[0]["source_frame"] == {"start": 0, "end": first_end, "terminated": False,
            "coordinate_system": "parsed_input_source_byte_offsets"}
        assert entries[1]["source_frame"]["start"] == first_end
        assert page["original_source_ref"] == original["id"] and page["parsed_input_source_ref"] == decoded["id"]
        assert any(error["code"] == "genbank_record_terminator_missing" for error in store.material_errors(attempt["id"])["errors"])


def test_native_read_contracts_do_not_accept_paths_forge_sources_or_claim_empty_fasta_annotations(tmp_path):
    with Store(tmp_path / "state") as store:
        original = store.create_problem(raw_sequence="MACT")
        tools = ToolRegistry(store, run_directory=store.path / 'tool-run')
        unavailable = call(tools, "material.annotations", {"parse_ref": original["initial_parse_refs"][0]})["result"]
        assert unavailable["availability"] == "unavailable" and unavailable["total"] is None
        assert unavailable["code"] == "native_annotations_not_available"
        invalid = tools.execute("material.annotations", {"parse_ref": original["initial_parse_refs"][0], "path": "/etc/passwd"})
        assert invalid["status"] == "invalid" and invalid["feedback"]["code"] == "representation_error"
        material = store.register_material(data=body())
        parsed = store.parse_material(material["id"])
        wrong = {key: value for key, value in parsed.items() if key not in {"id", "record_type", "origin"}}
        wrong["native_source_ref"] = store.get(material["source_ref"])["id"]
        with pytest.raises(ContractError, match="native_genbank_source_identity_mismatch"):
            store.put("parse_attempt", wrong, origin="tool")
