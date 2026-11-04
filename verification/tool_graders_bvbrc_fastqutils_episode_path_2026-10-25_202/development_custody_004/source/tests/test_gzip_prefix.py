"""Generated damaged wrappers: native prefix custody, not biological accuracy."""
import asyncio
import gzip
import hashlib
import json

import pytest

from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


FIRST = b"@one native read\nACGTACGT\n+\nIIIIIIII\n"
SECOND = b"@two native read\nGATTACAA\n+\nHHHHHHHH\n"
RAW = FIRST + SECOND


def native_wrapper(fault):
    body = gzip.compress(RAW, mtime=0)
    if fault == "trailer_absent":
        return body[:-8]
    if fault == "crc_wrong":
        return body[:-8] + bytes([body[-8] ^ 1]) + body[-7:]
    return body


@pytest.mark.parametrize("fault,exception", [("trailer_absent", "EOFError"),
                                            ("crc_wrong", "BadGzipFile")])
def test_native_prefix_survives_wrapper_failure_reopen_and_portable_export(tmp_path, fault, exception):
    wrapper = native_wrapper(fault)
    workspace = tmp_path / "store"
    with Store(workspace) as store:
        problem = store.create_problem(raw_sequence="MKWV", molecule="protein")
        material = store.register_material(data=wrapper, name="generated_damaged_gzip", role="read", molecule="dna")
        attempt = store.parse_material(material["id"])
        assert attempt["status"] == "partial" and attempt["valid_records"] == 2
        errors = store.material_errors(attempt["id"])["errors"]
        assert errors == [{"ordinal": None, "byte_offset": None,
            "code": "gzip_decode_incomplete", "decoded_prefix_bytes": len(RAW),
            "exception_type": exception, "unparsed_remainder": "unknown", "wrapper_integrity": "not_established"}]
        original, decoded = store.get(material["source_ref"]), store.get(attempt["source_ref"])
        assert store.get_artifact(original["artifact_ref"]) == wrapper
        assert store.get_artifact(decoded["artifact_ref"]) == RAW
        assert decoded["parent_source_refs"] == [original["id"]]
        metadata = json.loads(store.get_artifact(decoded["request_ref"]))
        assert metadata["complete"] is False and metadata["decoded_bytes"] == len(RAW)
        assert metadata["exception_type"] == exception and metadata["exception_message"]
        assert metadata["source_ref"] == original["id"]
        assert metadata["decoder_mode"] == "native_gzip_read1_prefix_v1"
        collection = store.get(attempt["collection_ref"])
        assert collection["complete"] is False
        members = store.material_members(collection["id"])["members"]
        assert [store.material_member(row["id"])["sequence"] for row in members] == ["ACGTACGT", "GATTACAA"]
        assert [store.material_member(row["id"])["quality"] for row in members] == ["IIIIIIII", "HHHHHHHH"]
        assert all(row["source_ref"] == decoded["id"] for row in members)
        assert project_credit(store).credit == 0 and not store.current_annotations()
        assert store.problem() == problem
    with Store(workspace) as store:
        assert store.parse_material(material["id"]) == attempt
        assert [row["id"] for row in store.material_members(collection["id"])["members"]] == [row["id"] for row in members]
        out = tmp_path / "portable.json"
        export_annotation(store, out, include_artifacts=True)
        exported = json.loads(out.read_text())
        records = {row["id"]: row for row in exported["records"]}
        artifacts = {row["id"]: row for row in exported["artifacts"]}
        for source, body in [(original, wrapper), (decoded, RAW)]:
            assert records[source["id"]] == source
            assert (out.parent / artifacts[source["artifact_ref"]]["relative_path"]).read_bytes() == body
        assert json.loads((out.parent / artifacts[decoded["request_ref"]]["relative_path"]).read_text()) == metadata
        sidecar, = exported["packed_material_indexes"]
        assert sidecar["member_count"] == 2
        assert hashlib.sha256((out.parent / sidecar["relative_path"]).read_bytes()).hexdigest() == sidecar["sha256"]
        assert store.material_errors(attempt["id"])["errors"] == errors


def test_partial_deflate_payload_keeps_only_complete_native_fastq_records(tmp_path):
    wrapper = gzip.compress(FIRST, mtime=0) + gzip.compress(SECOND, mtime=0)[:-12]
    expected = FIRST + b"@two native read\nGATTACAA\n+\n"
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="MKWV", molecule="protein")
        material = store.register_material(data=wrapper, role="read", molecule="dna")
        attempt = store.parse_material(material["id"])
        assert attempt["status"] == "partial" and attempt["valid_records"] == 1
        decoded = store.get(attempt["source_ref"])
        assert store.get_artifact(decoded["artifact_ref"]) == expected
        errors = store.material_errors(attempt["id"])["errors"]
        assert [row["code"] for row in errors] == ["gzip_decode_incomplete", "malformed_fastq_remaining_scope_unparsed"]
        member, = store.material_members(attempt["collection_ref"])["members"]
        assert member["ordinal"] == 0
        assert store.material_member(member["id"])["sequence"] == "ACGTACGT"
        assert store.material_member(member["id"])["quality"] == "IIIIIIII"


def test_complete_wrapper_remains_complete_with_explicit_decoder_provenance(tmp_path):
    wrapper = native_wrapper("complete")
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="MKWV", molecule="protein")
        material = store.register_material(data=wrapper, role="read", molecule="dna")
        attempt = store.parse_material(material["id"])
        assert attempt["status"] == "completed" and attempt["valid_records"] == 2
        assert store.material_errors(attempt["id"])["errors"] == []
        decoded = store.get(attempt["source_ref"])
        metadata = json.loads(store.get_artifact(decoded["request_ref"]))
        assert metadata["complete"] is True and metadata["exception_type"] is None
        assert metadata["decoded_bytes"] == len(RAW) and "exception_message" not in metadata
        assert decoded["parent_source_refs"] == [material["source_ref"]]
        assert store.get_artifact(decoded["artifact_ref"]) == RAW
        assert project_credit(store).credit == 0


def test_wrapper_failure_without_emitted_bytes_retains_original_and_explicit_empty_prefix(tmp_path):
    wrapper = b"\x1f\x8bmalformed"
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="MKWV", molecule="protein")
        material = store.register_material(data=wrapper, role="read", molecule="dna")
        attempt = store.parse_material(material["id"])
        assert attempt["status"] == "failed" and attempt["valid_records"] == 0
        errors = store.material_errors(attempt["id"])["errors"]
        assert len(errors) == 1 and errors[0]["code"] == "gzip_decode_incomplete"
        assert errors[0]["decoded_prefix_bytes"] == 0
        decoded = store.get(attempt["source_ref"])
        assert store.get_artifact(decoded["artifact_ref"]) == b""
        assert decoded["parent_source_refs"] == [material["source_ref"]]
        assert store.get_artifact(store.get(material["source_ref"])["artifact_ref"]) == wrapper
        assert store.db.execute("SELECT count(*) FROM material_members").fetchone()[0] == 1  # Only the scalar control target.


def test_one_selected_parse_records_partial_work_once_without_scientific_credit(tmp_path):
    from gene_annotation_episode.runtime import run_workflow
    from test_runtime import FixtureController, ScriptedProvider

    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="MKWV", molecule="protein")
        material = store.register_material(data=native_wrapper("trailer_absent"), role="read", molecule="dna")
        tools = ToolRegistry(store)
        provider = ScriptedProvider([{"selection": {"kind": "tool", "tool": "material.parse",
            "arguments": {"material_ref": material["id"]}}, "report_update": {}}])
        summary = asyncio.run(run_workflow(store, tools, provider=provider, run_dir=tmp_path / "run",
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 1)))
        assert summary["completed_actions"] == 1 and summary["credit"] == 0
        action = store.db.execute("SELECT result,credit FROM runtime_actions").fetchone()
        result = json.loads(action["result"])
        assert result["status"] == "partial" and result["result"]["parse_attempt"]["valid_records"] == 2
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 1
        assert not store.current_annotations() and action["credit"] == 0
