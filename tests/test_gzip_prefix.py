"""Generated damaged wrappers: native prefix custody, not biological accuracy."""
import asyncio
import gzip
import json


from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry


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
    from gene_annotation_episode.episodic_workflow.root.run_execution import run_workflow
    from test_runtime import FixtureController, ScriptedProvider

    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="MKWV", molecule="protein")
        material = store.register_material(data=native_wrapper("trailer_absent"), role="read", molecule="dna")
        tools = ToolRegistry(store, run_directory=store.path / 'tool-run')
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
