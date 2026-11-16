"""Provenance representation fixtures, not biological annotation validation."""

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry


def test_optional_native_stream_fields_require_artifacts_and_are_not_model_authored(tmp_path):
    with Store(tmp_path / "state") as store:
        target = store.create_problem(raw_sequence="MACT")["subject_refs"][0]
        material = store.register_material(data=b"synthetic source content")
        source = store.get(material["source_ref"])
        body = {key: value for key, value in source.items() if key not in {"id", "record_type", "origin"}}
        stream = store.artifact(b"synthetic native stream\x00\xff", "application/octet-stream")
        recorded = store.put("source", {**body, "stdout_ref": stream, "stderr_ref": stream}, origin="tool")
        assert recorded["stdout_ref"] == recorded["stderr_ref"] == stream
        unreadable = ToolRegistry(store, run_directory=store.path / 'tool-run').execute("source.read", {"source_ref": recorded["id"], "representation": "stdout"})
        assert unreadable["status"] == "invalid" and unreadable["feedback"]["code"] == "source_not_utf8_text"
        missing = ToolRegistry(store, run_directory=store.path / 'tool-run').execute("source.read", {"source_ref": source["id"], "representation": "stderr"})
        assert missing["status"] == "invalid"
        assert missing["feedback"]["code"] == "source_representation_unavailable"
        assert missing["feedback"]["detail"] == {"representation": "stderr", "available_representations": ["original", "text"]}
        for field in ("stdout_ref", "stderr_ref"):
            with pytest.raises(ContractError, match="wrong_reference_type"):
                store.put("source", {**body, field: target}, origin="tool")
        with pytest.raises(ContractError, match="origin_not_allowed"):
            store.put("source", {**body, "stdout_ref": stream}, origin="reasoning")
        assert "source" not in store.reasoning_schema()["properties"]


