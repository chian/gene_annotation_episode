"""Native intake/storage/tool/export contracts, not annotation accuracy tests."""
import hashlib
import gzip
import io
import json
from pathlib import Path

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import BeforePosition, AfterPosition, CompoundLocation, SeqFeature, SimpleLocation
from Bio.SeqRecord import SeqRecord
import pytest

from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


ACQUISITION = Path(__file__).resolve().parents[1] / "validation/acquisition"


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


def test_caller_genbank_collection_binds_sequences_without_copying_native_assertions(tmp_path):
    feature = SeqFeature(CompoundLocation([SimpleLocation(6, 9, strand=-1),
        SimpleLocation(BeforePosition(0), AfterPosition(3), strand=-1)], operator="join"), type="CDS",
        qualifiers={"gene": ["asserted_name"], "product": ["asserted function"], "transl_table": ["11"],
                    "codon_start": ["2"], "transl_except": ["(pos:1..3,aa:Sec)"]})
    content = body(features=[feature]) + body("PROTEINFIXTURE.1", sequence="MACT", molecule="protein")
    path = tmp_path / "supplied.gb"
    path.write_bytes(content)
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(path)
        targets = store.targets()
        assert len(targets) == 2
        assert all(row["molecule"] == "unspecified" and row["unit"] == "symbol" for row in targets)
        assert [store.get_artifact(row["sequence_ref"]) for row in targets] == [b"ATGAAATAA", b"MACT"]
        attempt = store.get(problem["initial_parse_refs"][0])
        assert attempt["status"] == "completed" and attempt["valid_records"] == 2
        native = store.get(attempt["native_source_ref"])
        assert native["parent_source_refs"] == [attempt["source_ref"]]
        assert store.get_artifact(store.get(attempt["source_ref"])["artifact_ref"]) == content
        tools = ToolRegistry(store)
        records = call(tools, "material.annotations", {"parse_ref": attempt["id"]})["result"]
        actual = [native_entry(store, entry) for entry in records["entries"]]
        assert [row["record"]["annotations"]["molecule_type"] for row in actual] == ["DNA", "protein"]
        assert actual[0]["record"]["annotations"]["topology"] == "circular"
        features = call(tools, "material.annotations", {"parse_ref": attempt["id"], "kind": "feature"})["result"]
        preserved = native_entry(store, features["entries"][0])["feature"]
        assert preserved["qualifiers"]["transl_except"] == ["(pos:1..3,aa:Sec)"]
        assert [part["start"]["nominal"] for part in preserved["location"]["parts"]] == [6, 0]
        assert preserved["location"]["parts"][1]["start"]["class"] == "BeforePosition"
        assert not store.list("feature") and not store.list("hypothesis") and not store.current_annotations()
        assert project_credit(store).credit == 0
        member = store.get(store.material_members(attempt["collection_ref"])["members"][0]["id"])
        header = store.material_header(member["id"])
        assert header["representation"] == "biopython_genbank_identifier"
        assert header["text"] == "FIXTURE.1" and not header["original_header_bytes"]
        assert member["description"] == "synthetic native input"


def test_native_feature_pages_are_bounded_and_exact_full_qualifiers_remain_readable(tmp_path):
    qualifiers = {"note": ["π" * 100000], "translation": ["M" * 100000]}
    features = [SeqFeature(SimpleLocation(i, i+1), type="misc_feature", qualifiers=qualifiers if i == 0 else {})
                for i in range(3)]
    content = body(features=features)
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MACT")
        material = store.register_material(data=content, use="evidence")
        attempt = store.parse_material(material["id"])
        tools = ToolRegistry(store)
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
            "start": tiny["start"], "end": tiny["end"], "quote": tiny["text"]}, explicit["source_ref"])
        original = store.get(material["source_ref"])
        with pytest.raises(ContractError, match="anchor_source_mismatch"):
            store._anchor({"source_ref": original["id"], "artifact_ref": explicit["artifact_ref"],
                "start": tiny["start"], "end": tiny["end"], "quote": tiny["text"]}, original["id"])


def test_partial_native_records_warnings_and_metadata_only_records_survive_export_reopen(tmp_path):
    malformed = b"LOCUS       BROKEN\n//\n"
    warning = body("WARNING.1").replace(b"FEATURES             Location/Qualifiers\n",
        b"FEATURES             Location/Qualifiers\n     misc_feature    nonsense_location\n                     /note=\"native note survives\"\n")
    content = body("FIRST.1") + malformed + contig() + warning
    workspace = tmp_path / "state"
    with Store(workspace) as store:
        original = store.create_problem(raw_sequence="MACT", molecule="protein")
        material = store.register_material(data=content, use="evidence")
        result = call(ToolRegistry(store), "material.parse", {"material_ref": material["id"]}, operation_key="native-partial")
        assert result["status"] == "partial"
        attempt = result["result"]["parse_attempt"]
        assert attempt["native_source_ref"] in result["record_refs"]
        assert [row["ordinal"] for row in store.material_members(attempt["collection_ref"])["members"]] == [0, 3]
        errors = store.material_errors(attempt["id"])["errors"]
        assert {row["code"] for row in errors} >= {"genbank_record_parse_failed", "genbank_record_sequence_unavailable", "genbank_native_parser_warning"}
        records = store.material_annotations(attempt["id"])
        assert [row["record_ordinal"] for row in records["entries"]] == [0, 1, 2, 3]
        native = [native_entry(store, entry) for entry in records["entries"]]
        assert native[1]["record"] is None and native[1]["parse_failure"] is not None
        assert native[2]["record"]["sequence"]["defined"] is False
        assert native[2]["record"]["annotations"]["contig"].startswith("join(REMOTE")
        assert native[3]["parser_warnings"]
        location = native_entry(store, store.material_annotations(attempt["id"], record_ordinal=3, kind="feature")["entries"][0])["feature"]
        assert location["location"] is None and location["qualifiers"]["note"] == ["native note survives"]
    with Store(workspace) as store:
        assert store.problem() == original and store.parse_material(material["id"]) == attempt
        exported = export_annotation(store, tmp_path / "portable.json", include_artifacts=True, page_size=1)
        document = json.loads(Path(exported["json"]["path"]).read_text())
        rows = document["native_material_annotations"]
        assert len(rows) == 5 and all(row["parse_ref"] == attempt["id"] for row in rows)
        artifacts = {row["id"]: row for row in document["artifacts"]}
        for row in rows:
            artifact = artifacts[row["artifact_ref"]]
            raw = (tmp_path / artifact["relative_path"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == artifact["sha256"]
            native = json.loads(raw[row["start"]:row["end"]])
            assert native["record_ordinal"] == row["record_ordinal"]
        assert [row["code"] for row in document["parse_errors"]] == [row["code"] for row in errors]
        assert document["problem"] == original and len(document["inputs"]) == 1
        assert project_credit(store).credit == 0 and not store.list("feature") and not store.current_annotations()


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
        page = call(ToolRegistry(store), "material.annotations", {"parse_ref": attempt["id"]})["result"]
        native = native_entry(store, page["entries"][0])
        assert native["record"]["sequence"]["length"] == 9 and native["record"]["sequence"]["defined"] is False
        assert not store.targets() and not store.list("feature")


def test_saved_external_genbank_evidence_preserves_origin_fixed_targets_cache_and_portable_custody(tmp_path):
    provenance = json.loads((ACQUISITION / "acquisition-provenance.json").read_text())
    raw = (ACQUISITION / "AJ320226.1.genbank").read_bytes()
    with Store(tmp_path / "state") as store:
        original = store.create_problem(raw_sequence="MACT", molecule="protein")
        before = project_credit(store).as_record()
        original_source = provenance["source"]
        assert store.artifact(raw, "text/x-genbank") == original_source["artifact_ref"]
        assert store.artifact(canonical(provenance["request"]), "application/json") == original_source["request_ref"]
        source = store.put("source", {key: value for key, value in original_source.items()
            if key not in {"id", "record_type", "origin"}}, origin="external")
        assert source == original_source
        tools = ToolRegistry(store)
        wrapped = call(tools, "material.from_source", {"source_ref": source["id"]})["result"]
        material = store.get(wrapped["material_ref"])
        assert material["source_ref"] == source["id"] and material["use"] == "evidence"
        parsed = call(tools, "material.parse", {"material_ref": material["id"]}, operation_key="saved-genbank")
        attempt = parsed["result"]["parse_attempt"]
        counts = store.count("source"), store.db.execute("SELECT count(*) FROM material_annotations").fetchone()[0]
        assert call(tools, "material.parse", {"material_ref": material["id"]}, operation_key="saved-genbank") == parsed
        assert store.parse_material(material["id"]) == attempt
        assert counts == (store.count("source"), store.db.execute("SELECT count(*) FROM material_annotations").fetchone()[0])
        page = store.material_annotations(attempt["id"], kind="feature")
        assert page["total"] == 4
        assert store.problem() == original and project_credit(store).as_record() == before
        assert not store.list("hypothesis") and not store.current_annotations()
        exported = export_annotation(store, tmp_path / "evidence.gff3", format="gff3", include_artifacts=True)
        document = json.loads(Path(exported["json"]["path"]).read_text())
        assert document["inputs"] == store.targets() and len(document["native_material_annotations"]) == 5
        assert exported["gff3"]["emitted_rows"] == 0
        artifact = next(row for row in document["artifacts"] if row["id"] == source["artifact_ref"])
        assert (tmp_path / artifact["relative_path"]).read_bytes() == raw


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
        tools = ToolRegistry(store)
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
