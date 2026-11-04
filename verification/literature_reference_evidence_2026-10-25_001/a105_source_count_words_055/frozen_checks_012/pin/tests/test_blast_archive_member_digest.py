"""Exact member-byte identity from retained NCBI output and synthetic ZIP layouts.

The repackaged archives are explicit byte-identity counterexamples; no searches
or native algorithms execute here, and their duplicated records are not new data.
"""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
import zipfile

import pytest

from gene_annotation_episode.blast_grading_inputs import parse_blast_json
from gene_annotation_episode.blast_report_collection import parse_blast_report_collection


ROOT = Path(__file__).resolve().parents[1]
NATIVE_ARCHIVE = ROOT / "verification/w04_blast_graders_2026-10-24_001/live_api/result.body"


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def retained():
    raw = NATIVE_ARCHIVE.read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = [(info.filename, archive.read(info)) for info in archive.infolist()]
    assert len(members) == 2
    assert members[1][0] == "DTKE1D4G016_1.json"
    return raw, members, json.loads(members[1][1])


def _invocation():
    return {"execution_program": "blastp", "scientific_mode": "database", "resource_kind": "api",
        "query_kind": "sequence", "reference_kind": "sequence", "request": {},
        "effective_options": {"requested_hit_limit": None, "requested_hsp_limit": None},
        "operands": [{"role": "query", "artifact_key": "query.fa", "record_ordinal": 0,
            "native_id": "gene_001", "native_title": "gene_001", "subject_ref": "actual-query",
            "molecule": "protein", "length": 253, "selected_interval": None, "identity": None}],
        "completion": {"native_returncode": None, "producer_complete": None}}


def _collect(raw, *, format_name="json2_archive", invocation=None):
    artifacts = [{"artifact_key": "retained", "role": "primary_report", "format": format_name,
                  "fields": None, "delimiter": None}]
    invocation = _invocation() if invocation is None else invocation
    original_artifacts, original_invocation = deepcopy(artifacts), deepcopy(invocation)
    result = parse_blast_report_collection({"retained": raw}, artifacts=artifacts, invocation=invocation)
    assert artifacts == original_artifacts
    assert invocation == original_invocation
    return result


def _archive(members):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members:
            archive.writestr(name, payload)
    return buffer.getvalue()


def _assert_member_identities(result, raw, members):
    artifact, = result["artifacts"]
    assert artifact["sha256"] == _sha(raw)
    assert artifact["size_bytes"] == len(raw)
    assert artifact["members"] == [
        {"member_ordinal": ordinal, "name": name, "size_bytes": len(payload), "sha256": _sha(payload)}
        for ordinal, (name, payload) in enumerate(members)]
    for search in result["searches"]:
        ordinal = search["search_key"]["member_ordinal"]
        name, payload = members[ordinal]
        native = search["normalized"]["native"]
        assert native["archive_member"] == {"ordinal": ordinal, "name": name, "sha256": _sha(payload)}
        assert native["archive_member"]["sha256"] == artifact["members"][ordinal]["sha256"]
        assert native["sha256"] == _sha(raw)
        assert native["archive_member"]["sha256"] != native["sha256"]
        assert native["document"] == json.loads(payload)


def test_retained_ncbi_members_numerics_and_legacy_reader_shape(retained):
    raw, members, document = retained
    result = _collect(raw)
    _assert_member_identities(result, raw, members)
    search, = result["searches"]
    old = parse_blast_json(raw, mode="database", resource="api")
    assert old["native"]["archive_member"] == {"ordinal": 1, "name": "DTKE1D4G016_1.json"}
    assert old["native"]["sha256"] == _sha(raw)
    assert search["search_key"] == {"artifact_key": "retained", "member_ordinal": 1,
        "report_index": 0, "search_pointer": "/BlastOutput2/report/results/search"}
    assert search["normalized"]["hits"] == old["hits"]
    assert search["normalized"]["query"] == old["query"]
    assert search["normalized"]["search"]["statistics"] == old["search"]["statistics"]
    assert [hit["hsps"][0]["score"] for hit in old["hits"]] == [1358, 87, 72, 71, 70, 69, 69]
    assert [hit["hsps"][0]["identity"] for hit in old["hits"]] == [253, 31, 38, 23, 15, 22, 22]
    assert search["native"]["report"] == document["BlastOutput2"]["report"]
    assert search["native"]["search"] == document["BlastOutput2"]["report"]["results"]["search"]
    assert search["program_context"]["geometry_program"] == "blastp"
    assert not result["issues"] and not search["issues"]


def test_duplicate_member_names_keep_distinct_bytes_and_every_report_ordinal(retained):
    _, retained_members, document = retained
    # A synthetic second wrapper repeats retained native records; it is neither
    # a new search nor evidence of independent scientific observations.
    repeated_reports = json.dumps({"BlastOutput2": [document["BlastOutput2"], document["BlastOutput2"]]}).encode()
    members = [("same.json", retained_members[1][1]), ("same.json", repeated_reports)]
    with pytest.warns(UserWarning, match="Duplicate name"):
        raw = _archive(members)
    result = _collect(raw)
    _assert_member_identities(result, raw, members)
    assert [row["search_key"]["member_ordinal"] for row in result["searches"]] == [0, 1, 1]
    assert [row["search_key"]["report_index"] for row in result["searches"]] == [0, 0, 1]
    digests = [row["normalized"]["native"]["archive_member"]["sha256"] for row in result["searches"]]
    assert digests[0] != digests[1] == digests[2]
    first_hits = result["searches"][0]["normalized"]["hits"]
    assert all(row["normalized"]["hits"] == first_hits for row in result["searches"])
    for row in result["searches"]:
        issue, = row["issues"]
        assert issue["code"] == "blast_archive_member_name_duplicate"
        assert issue["details"] == {"name": "same.json", "member_ordinals": [0, 1]}


def test_equal_decoded_json_with_different_whitespace_has_different_member_hashes(retained):
    _, retained_members, document = retained
    exact = retained_members[1][1]
    whitespace_variant = b" \n\t" + exact + b"\r\n  "
    assert json.loads(exact) == json.loads(whitespace_variant) == document
    members = [("exact.json", exact), ("whitespace.json", whitespace_variant)]
    raw = _archive(members)
    result = _collect(raw)
    _assert_member_identities(result, raw, members)
    first, second = result["searches"]
    assert first["native"] == second["native"]
    assert first["normalized"]["hits"] == second["normalized"]["hits"]
    hashes = {row["normalized"]["native"]["archive_member"]["sha256"] for row in result["searches"]}
    assert hashes == {_sha(exact), _sha(whitespace_variant)} and len(hashes) == 2
    assert _sha(json.dumps(document).encode()) not in hashes
    assert not result["issues"] and all(not row["issues"] for row in result["searches"])


def test_manifest_bad_siblings_and_nonreports_do_not_compact_member_ordinals(retained):
    _, retained_members, document = retained
    members = [("directory/", b""),
        ("manifest.json", b'{"BlastJSON":[{"File":"good.json"},{"File":"absent.json"}]}'),
        ("bad.json", b"{truncated"), ("good.json", retained_members[1][1]),
        ("notes.txt", b"retained bytes"),
        ("../partial.json", json.dumps({"BlastOutput2": [None, document["BlastOutput2"]]}).encode()),
        ("unrelated.json", b'{"unrelated":true}')]
    raw = _archive(members)
    result = _collect(raw)
    _assert_member_identities(result, raw, members)
    assert [row["search_key"]["member_ordinal"] for row in result["searches"]] == [3, 5]
    assert [row["search_key"]["report_index"] for row in result["searches"]] == [0, 1]
    assert result["searches"][1]["search_key"]["search_pointer"] == "/BlastOutput2/1/report/results/search"
    assert {(row["code"], row["member_ordinal"]) for row in result["issues"]} == {
        ("blast_native_json_invalid", 2), ("blast_archive_manifest_member_missing", 1),
        ("blast_report_object_required", 5), ("blast_report_document_layout_unsupported", 6)}
    assert not result["searches"][0]["issues"]
    assert [row["code"] for row in result["searches"][1]["issues"]] == ["blast_archive_report_not_in_manifest"]
    assert result["searches"][0]["normalized"]["hits"] == result["searches"][1]["normalized"]["hits"]


@pytest.mark.parametrize("branch", ["bl2seq", "iterations"])
def test_each_original_search_branch_receives_its_member_digest(retained, branch):
    _, _, document = retained
    report = document["BlastOutput2"]["report"]
    native_search = report["results"]["search"]
    invocation = _invocation()
    if branch == "bl2seq":
        # Synthetic branch layout preserves actual native measurement records.
        report["results"] = {branch: [native_search, native_search]}
        report["search_target"] = {"subjects": ["synthetic-layout"]}
        invocation["scientific_mode"] = "pairwise"
    else:
        report["results"] = {branch: [{"iter_num": 1, "search": native_search},
            None, {"iter_num": 3, "search": native_search}]}
    members = [("manifest.json", b'{"BlastJSON":[{"File":"report.json"}]}'),
               ("report.json", json.dumps(document).encode())]
    raw = _archive(members)
    result = _collect(raw, invocation=invocation)
    _assert_member_identities(result, raw, members)
    assert len(result["searches"]) == 2
    pointers = [row["search_key"]["search_pointer"] for row in result["searches"]]
    suffixes = ["bl2seq/0", "bl2seq/1"] if branch == "bl2seq" else ["iterations/0/search", "iterations/2/search"]
    assert pointers == ["/BlastOutput2/report/results/" + suffix for suffix in suffixes]
    assert all(row["native"]["search"] == native_search for row in result["searches"])


@pytest.mark.parametrize("format_name", ["json2", "json15"])
def test_standalone_json_keeps_null_member_and_original_byte_hash(retained, format_name):
    _, members, document = retained
    raw = members[1][1]
    result = _collect(raw, format_name=format_name)
    search, = result["searches"]
    assert search["normalized"]["native"] == {"document": document, "archive_member": None, "sha256": _sha(raw)}
    assert search["search_key"]["member_ordinal"] is None
    assert "members" not in result["artifacts"][0]
    old = parse_blast_json(raw, mode="database", resource="api")
    assert search["normalized"] == old
    assert not result["issues"] and not search["issues"]


def test_archive_parser_uses_supplied_bytes_without_external_access(retained, monkeypatch):
    raw, members, _ = retained
    def forbidden(*args, **kwargs):
        raise AssertionError("archive parsing attempted external access")
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    _assert_member_identities(_collect(raw), raw, members)
