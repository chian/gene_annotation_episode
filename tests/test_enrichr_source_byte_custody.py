"""Actual ordinary byte tools over genuine engineered Enrichr publication.

The existing Harness executes the registered finite API protocol against its
explicit HTTP fixture and commits the original publication/action chain. These
tests then select actual ToolRegistry source/material/location reads, without a
Workflow constructor, scientific child, model, live HTTP or native analysis.
Source aliases are explicit engineering fixtures, not provider-produced facts.
"""
import base64
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_enrichr_reference_privacy import receiver
from test_enrichr_returns import Harness


def forbidden(*args, **kwargs):
    raise AssertionError("selected byte tools must not acquire or read private payloads")


def alias_source(store, original, artifact_ref, *, representation="original"):
    value = {key: deepcopy(item) for key, item in original.items()
        if key not in {"id", "record_type", "origin"}}
    value.update(provider="engineering_attachment", accession=None, uri=None,
        request_ref=None, auxiliary_artifact_refs=[], text_ref=None)
    if representation == "original":
        value["artifact_ref"] = artifact_ref
    else:
        value[representation + "_ref"] = artifact_ref
    return store.put("source", value, origin="external")


@pytest.fixture
def case(tmp_path):
    with Store(tmp_path / "store") as store:
        original = Harness(store, tmp_path / "run-a")
        child = original.child(original.root)
        outcome = original.action(child)
        source = store.get(outcome["result"]["source_ref"])
        original.returned(original.root, child)
        # Read original custody once before installing the no-payload controls.
        import json
        control = json.loads(store.get_artifact(source["request_ref"]))
        upload_ref = control["transport"]["enrichr_protocol"]["stages"][0]["snapshot"]["content_ref"]
        private = {"request": source["request_ref"],
            "grading": source["auxiliary_artifact_refs"][0], "upload": upload_ref}
        unrelated_bytes = b"independent target source"
        unrelated = alias_source(store, source, store.artifact(unrelated_bytes, "text/plain"))
        receiving = receiver(store, original.scope, run_id="no-api-byte-reader")
        receiving.receipts.receive(receiving.context.episode_id,
            [source["id"], unrelated["id"]], kind="initial")
        registry = ToolRegistry(store, clients=SimpleNamespace(_http=forbidden))
        yield SimpleNamespace(store=store, original=original, source=source,
            private=private, unrelated=unrelated, unrelated_bytes=unrelated_bytes,
            receiving=receiving, registry=registry, operations=0)


def guard_payloads(case, monkeypatch):
    """Real metadata classification must precede every private path.open."""
    private_paths = {case.store.path / "artifacts" / ref[9:11] / ref[9:]
        for ref in case.private.values()}
    artifact_directory = case.store.path / "artifacts"
    original_open, opened = Path.open, []
    def checked_open(path, *args, **kwargs):
        assert path not in private_paths, "private artifact reached byte-opening port"
        if path.is_relative_to(artifact_directory):
            opened.append(path)
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", checked_open)
    monkeypatch.setattr(case.store, "get_artifact", forbidden)
    monkeypatch.setattr(case.original.client, "_http", forbidden)
    return opened


def select(case, tool, source, *, representation="original", **overrides):
    """Invoke the real registered operation; no action/Workflow is fabricated."""
    case.operations += 1
    key = f"byte-custody:{case.operations}"
    arguments = {"source_ref": source["id"], "representation": representation,
        "offset": 0, "limit": 65536}
    permitted = None
    if tool.startswith("material."):
        material = case.store.register_material(source_ref=source["id"], format="raw")
        arguments = {"material_ref": material["id"]}
        if tool == "material.read":
            arguments.update(offset=0, limit=65536)
        else:
            arguments["format"] = "raw"
    elif tool == "source.locate":
        arguments.update(needle="target", limit=1, context_bytes=0)
        permitted = (source["id"],)
    arguments.update(overrides)
    return case.registry.execute(tool, arguments, scope=plain(case.receiving.context.scope),
        operation_key=key, permitted_record_refs=permitted)


@pytest.mark.parametrize("role", ["request", "grading", "upload"])
@pytest.mark.parametrize("tool", ["source.read", "material.read", "source.locate"])
def test_private_source_alias_is_denied_before_the_selected_byte_port(case, monkeypatch, role, tool):
    private_ref = case.private[role]
    source = alias_source(case.store, case.source, private_ref)
    # Even an actual historical expanded File receipt does not grant controls.
    case.receiving.receipts.receive(case.receiving.context.episode_id,
        [source["id"], private_ref], kind="initial")
    assert private_ref in set(case.receiving.receipts.known(case.receiving.context.episode_id))
    opened = guard_payloads(case, monkeypatch)
    result = select(case, tool, source)
    assert result["status"] == "invalid", result
    assert result["feedback"] == {"category": "arguments_or_reference",
        "code": "enrichr_private_artifact_not_readable"}
    assert result["result"] is None and result["record_refs"] == []
    assert opened == []
    assert len(case.original.client.calls) == 2


def test_private_source_alias_cannot_be_parsed_as_material(case, monkeypatch):
    source = alias_source(case.store, case.source, case.private["upload"])
    opened = guard_payloads(case, monkeypatch)
    result = select(case, "material.parse", source)
    assert result["status"] == "invalid", result
    assert result["feedback"]["code"] == "enrichr_private_artifact_not_readable"
    assert result["result"] is None and result["record_refs"] == []
    assert opened == []
    assert not case.store.db.execute("SELECT 1 FROM records WHERE record_type='parse_attempt' "
        "AND json_extract(data,'$.source_ref')=?", (source["id"],)).fetchall()


@pytest.mark.parametrize("representation", ["text", "stdout", "stderr"])
def test_selected_secondary_representation_cannot_alias_a_private_control(case, monkeypatch, representation):
    source = alias_source(case.store, case.source, case.private["request"], representation=representation)
    assert source["artifact_ref"] == case.source["artifact_ref"]
    opened = guard_payloads(case, monkeypatch)
    result = select(case, "source.read", source, representation=representation)
    assert result["status"] == "invalid", result
    assert result["feedback"]["code"] == "enrichr_private_artifact_not_readable"
    assert opened == []


@pytest.mark.parametrize("kind", ["native", "unrelated"])
@pytest.mark.parametrize("tool", ["source.read", "material.read", "source.locate"])
def test_native_and_unrelated_source_reads_keep_the_actual_selected_bytes(case, monkeypatch, kind, tool):
    source, raw, needle = ((case.source, case.original.client.content, "Literal library")
        if kind == "native" else (case.unrelated, case.unrelated_bytes, "target"))
    known = set(case.receiving.receipts.known(case.receiving.context.episode_id))
    assert source["id"] in known
    if kind == "native":
        assert source["artifact_ref"] not in known
    opened = guard_payloads(case, monkeypatch)
    result = select(case, tool, source, **({"needle": needle} if tool == "source.locate" else {}))
    assert result["status"] == "completed", result
    body = result["result"]
    assert body["source_ref"] == source["id"] and body["artifact_ref"] == source["artifact_ref"]
    if tool == "source.read":
        assert body["text"].encode() == raw
    elif tool == "material.read":
        assert base64.b64decode(body["content"]) == raw
    else:
        assert body["matches"][0]["witness"]["quote"] == needle
    assert opened
    assert set(case.receiving.receipts.known(case.receiving.context.episode_id)) == known
    assert len(case.original.client.calls) == 2


def test_locate_preserves_partial_scan_without_a_new_whole_file_rehash(case, monkeypatch):
    raw = b"ignored-prefix target tail"
    source = alias_source(case.store, case.source, case.store.artifact(raw, "text/plain"))
    artifact = case.store.get(source["artifact_ref"])
    path = case.store.path / "artifacts" / artifact["sha256"][:2] / artifact["sha256"]
    path.write_bytes(b"\xff" + raw[1:])  # Outside the selected scan and zero-width context.
    guard_payloads(case, monkeypatch)
    result = select(case, "source.locate", source, offset=len(b"ignored-prefix "))
    assert result["status"] == "completed", result
    assert result["result"]["matches"][0]["witness"] == {
        "source_ref": source["id"], "representation": "original",
        "start": len(b"ignored-prefix "), "end": len(b"ignored-prefix target"), "quote": "target"}


def test_source_read_keeps_existing_digest_failure_for_an_unrelated_source(case, monkeypatch):
    raw = case.unrelated_bytes
    artifact = case.store.get(case.unrelated["artifact_ref"])
    path = case.store.path / "artifacts" / artifact["sha256"][:2] / artifact["sha256"]
    path.write_bytes(b"X" + raw[1:])
    guard_payloads(case, monkeypatch)
    result = select(case, "source.read", case.unrelated)
    assert result["status"] == "invalid", result
    assert result["feedback"]["code"] == "artifact_digest_mismatch"


def test_locate_still_requires_the_original_explicitly_received_source(case, monkeypatch):
    opened = guard_payloads(case, monkeypatch)
    result = case.registry.execute("source.locate", {"source_ref": case.unrelated["id"],
        "representation": "original", "needle": "target"}, scope=plain(case.receiving.context.scope),
        operation_key="unreceived-location", permitted_record_refs=())
    assert result["status"] == "invalid", result
    assert result["feedback"]["code"] == "source_location_source_not_received"
    assert opened == []
