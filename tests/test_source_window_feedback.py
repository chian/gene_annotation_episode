"""Source-read failures distinguish byte boundaries from undecodable content."""
from copy import deepcopy

import pytest

from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def source(store, raw, representation):
    body = store.artifact(raw, "text/plain")
    other = store.artifact(b"A different source representation.", "text/plain")
    row = store.put("source", {"provider": "fixture.source-window", "accession": None,
        "uri": None, "artifact_ref": body if representation == "original" else other,
        "text_ref": body if representation == "text" else other, "request_ref": None,
        "version": None, "retrieved_at": None}, origin="caller")
    return row, body


@pytest.mark.parametrize("representation", ["original", "text"])
@pytest.mark.parametrize("character,inside", [("α", 1), ("前", 1), ("前", 2),
    ("🧬", 1), ("🧬", 2), ("🧬", 3)])
def test_interior_offset_feedback_can_be_used_without_changing_original_request(
        tmp_path, representation, character, inside):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="MACD", molecule="protein")
        row, body = source(store, ("prefix " + character + " suffix").encode(), representation)
        tools = ToolRegistry(store)
        start, width = len(b"prefix "), len(character.encode())
        arguments = {"source_ref": row["id"], "representation": representation,
            "offset": start + inside, "limit": 1}
        original = deepcopy(arguments)
        failed = tools.execute("source.read", arguments, operation_key="interior-offset")
        assert failed["status"] == "invalid" and failed["result"] is None
        assert failed["record_refs"] == []
        assert failed["feedback"]["code"] == "source_offset_not_utf8_boundary"
        detail = failed["feedback"]["detail"]
        assert detail == {"source_ref": row["id"], "artifact_ref": body,
            "representation": representation, "requested_offset": start + inside,
            "character_start": start, "character_end": start + width,
            "retry_query": {"source_ref": row["id"], "representation": representation,
                "offset": start, "limit": width}}
        assert arguments == original
        assert tools.execute("source.read", arguments, operation_key="interior-offset") == failed
        retry = tools.execute("source.read", detail["retry_query"], operation_key="selected-retry")
        assert retry["status"] == "completed"
        assert retry["result"]["text"] == character
        assert retry["result"]["artifact_ref"] == body
        assert retry["result"]["start"] == start and retry["result"]["end"] == start + width
        assert not store.list("observation") and not store.list("assessment")


@pytest.mark.parametrize("raw,offset", [(b"A\x80Z", 1),
    (b"A\xf0\x80\x80\x80Z", 2), (b"A\xe2\x82", 2)])
def test_invalid_utf8_has_no_fabricated_character_boundary(tmp_path, raw, offset):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="MACD", molecule="protein")
        row, _ = source(store, raw, "original")
        outcome = ToolRegistry(store).execute("source.read", {"source_ref": row["id"],
            "representation": "original", "offset": offset, "limit": 2})
        assert outcome["status"] == "invalid" and outcome["result"] is None
        assert outcome["feedback"] == {"category": "arguments_or_reference",
            "code": "source_offset_not_utf8_boundary"}


def test_missing_text_derivative_identifies_original_binary_without_retry(tmp_path):
    # A synthetic compound-file header tests rejection metadata, not Word parsing.
    raw = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + bytes(16)
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="MACD", molecule="protein")
        body = store.artifact(raw, "application/octet-stream")
        row = store.put("source", {"provider": "fixture.binary-source", "accession": None,
            "uri": None, "artifact_ref": body, "text_ref": None, "request_ref": None,
            "version": None, "retrieved_at": None}, origin="caller")
        tools = ToolRegistry(store)
        arguments = {"source_ref": row["id"], "representation": "text", "offset": 0,
            "limit": len(raw)}
        original = deepcopy(arguments)
        outcome = tools.execute("source.read", arguments, operation_key="binary-text-request")
        assert outcome["status"] == "invalid" and outcome["result"] is None
        assert outcome["record_refs"] == []
        assert outcome["feedback"]["code"] == "source_not_utf8_text"
        assert outcome["feedback"]["detail"] == {
            "source_ref": row["id"], "artifact_ref": body,
            "requested_representation": "text", "representation": "original",
            "available_representations": ["original"], "requested_offset": 0,
            "invalid_byte_offset": 0, "required_encoding": "utf-8"}
        assert arguments == original
        assert tools.execute("source.read", arguments, operation_key="binary-text-request") == outcome
        assert store.get_artifact(body) == raw and store.get(row["id"])["text_ref"] is None
        assert not store.list("source_derivative")
        assert not store.list("observation") and not store.list("assessment")


@pytest.mark.parametrize("representation", ["original", "text"])
def test_undecodable_selected_representation_does_not_switch_to_readable_alternative(
        tmp_path, representation):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="MACD", molecule="protein")
        row, body = source(store, b"prefix \xff suffix", representation)
        arguments = {"source_ref": row["id"], "representation": representation,
            "offset": len(b"prefix "), "limit": 4}
        outcome = ToolRegistry(store).execute("source.read", arguments)
        assert outcome["status"] == "invalid" and outcome["result"] is None
        assert outcome["record_refs"] == []
        assert outcome["feedback"]["code"] == "source_not_utf8_text"
        assert outcome["feedback"]["detail"] == {
            "source_ref": row["id"], "artifact_ref": body,
            "requested_representation": representation, "representation": representation,
            "available_representations": ["original", "text"], "requested_offset": 7,
            "invalid_byte_offset": 7, "required_encoding": "utf-8"}
        assert not store.list("source_derivative")
        assert not store.list("observation") and not store.list("assessment")
