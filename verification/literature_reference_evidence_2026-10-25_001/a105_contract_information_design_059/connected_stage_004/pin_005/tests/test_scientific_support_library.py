"""Versioned instruction persistence with invented source rows, no runtime work."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from method_loop.durable import canonical, content_digest
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from test_scientific_support_metadata import support_entry


PUBLICATION = (Path(__file__).resolve().parents[1] / "research/slotted_process_library"
               / "publications/2026-10-21-001")


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical(value) + "\n", encoding="utf-8")


def synthetic_source(directory, *, legacy=False):
    annotation = support_entry()
    if legacy:
        annotation.pop("entry_version")
        annotation.pop("support")
        annotation.update(claim_scope="An old engineering claim heading.",
            distinctions=["Historical fixture only."],
            not_established=["No scientific support metadata."],
            boundary="Reading preserves the old body without upgrading it.")
    thought = {"id": "P01", "slot": "thought_pattern", "name": "Synthetic contrast",
        "description": "Invented P instruction.", "evidence": deepcopy(annotation["evidence"]),
        "use_when": "The fixture asks for contrasting predictions.",
        "live_alternatives": ["One", "Two"],
        "decision_guidance": ["Inspect the observed contrast."],
        "outcome_contingencies": [{"if_observed": "No contrast",
            "then_consider": "Retain uncertainty."}], "boundary": "Engineering only."}
    bodies = [annotation, thought]
    headers, rows = [], []
    for body in bodies:
        evidence_id = "E-" + body["id"] + "-01"
        headers.append({**{key: body[key] for key in ("id", "slot", "name", "description")},
            "detail_path": "entries/" + body["id"] + ".json",
            "source_evidence_ids": [evidence_id]})
        rows.append({"evidence_id": evidence_id, "option_id": body["id"], **body["evidence"][0]})
        write(directory / headers[-1]["detail_path"], body)
    write(directory / "index.json", {"format": "research_three_slot_options_v1",
        "status": "Invented engineering source only.", "slots": [
            {"slot": "annotation_distinction", "catalog": "annotations.json", "count": 1},
            {"slot": "thought_pattern", "catalog": "thoughts.json", "count": 1}],
        "entries": headers})
    write(directory / "option_sources.json", {"meaning": "Invented instruction provenance.", "rows": rows})
    return bodies


def test_support_freezes_exact_bytes_and_semantics_detaches_reads_and_survives_removed_source(tmp_path):
    source, snapshot = tmp_path / "source", tmp_path / "snapshot"
    body = synthetic_source(source)[0]
    original_bytes = (source / "entries/A01.json").read_bytes()
    library = ScientificProcessLibrary.freeze(snapshot, source=source)
    ref, metadata = library.reference("A01"), library._entries["A01"]
    assert ref["slot"] == "annotation_distinction"
    assert ref["entry_sha256"] == content_digest(body)
    assert metadata["entry_file_sha256"] == hashlib.sha256(original_bytes).hexdigest()
    assert (snapshot / "entries/A01.json").read_bytes() == original_bytes
    result = library.execute("process.entry", {"option_id": "A01"})
    assert result["status"] == "completed"
    assert result["record_refs"] == result["changed_record_refs"] == []
    assert result["result"] == {"option_ref": ref, "entry": body, "source_count": 1}
    result["result"]["entry"]["support"]["operands"][0]["instruction"] = "Caller mutation"
    assert library.resolve(ref) == body
    changed = deepcopy(body)
    changed["support"]["proposition"] = "A later source changes no frozen body."
    write(source / "entries/A01.json", changed)
    assert ScientificProcessLibrary.freeze(snapshot, source=source).resolve(ref) == body
    shutil.rmtree(source)
    assert ScientificProcessLibrary(snapshot).resolve(ref) == body


def test_legacy_source_remains_exact_and_never_receives_support_metadata(tmp_path):
    source, snapshot = tmp_path / "source", tmp_path / "snapshot"
    original = synthetic_source(source, legacy=True)[0]
    original_bytes = (source / "entries/A01.json").read_bytes()
    library = ScientificProcessLibrary.freeze(snapshot, source=source)
    assert library.entry("A01")["entry"] == original
    assert "entry_version" not in library.entry("A01")["entry"]
    assert "support" not in library.entry("A01")["entry"]
    assert (snapshot / "entries/A01.json").read_bytes() == original_bytes
    assert ScientificProcessLibrary(snapshot).entry("A01") == library.entry("A01")


@pytest.mark.parametrize("legacy,version", [(False, "future"), (False, None), (True, "misspelled_v1")])
def test_present_unknown_version_cannot_fall_back_to_legacy(tmp_path, legacy, version):
    source, snapshot = tmp_path / "source", tmp_path / "snapshot"
    body = synthetic_source(source, legacy=legacy)[0]
    body["entry_version"] = version
    write(source / "entries/A01.json", body)
    with pytest.raises(ValueError, match="scientific_support_entry_invalid"):
        ScientificProcessLibrary.freeze(snapshot, source=source)
    assert not snapshot.exists()


@pytest.mark.parametrize("mutation", ["body_semantic", "body_bytes", "source_bytes", "reference", "source_row"])
def test_frozen_support_body_source_and_reference_tampering_is_rejected(tmp_path, mutation):
    source, snapshot = tmp_path / "source", tmp_path / "snapshot"
    body = synthetic_source(source)[0]
    library = ScientificProcessLibrary.freeze(snapshot, source=source)
    ref = library.reference("A01")
    if mutation == "reference":
        ref["entry_sha256"] = "0" * 64
        with pytest.raises(ValueError, match="option_reference_mismatch"):
            library.resolve(ref)
        return
    if mutation == "body_semantic":
        body["support"]["qualifications"] = ["Changed support meaning."]
        write(snapshot / "entries/A01.json", body)
    elif mutation in {"body_bytes", "source_bytes"}:
        path = snapshot / ("entries/A01.json" if mutation == "body_bytes" else "sources/A01.json")
        path.write_bytes(path.read_bytes() + b" \n")
    elif mutation == "source_row":
        path = snapshot / "sources/A01.json"
        rows = json.loads(path.read_text())
        rows[0]["limit"] = "Broadened beyond actual instruction source row."
        write(path, rows)
        manifest = json.loads((snapshot / "index.json").read_text())
        metadata = next(item for item in manifest["entries"] if item["option_id"] == "A01")
        metadata["sources_sha256"] = content_digest(rows)
        metadata["sources_file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest["library_id"] = content_digest({key: value for key, value in manifest.items()
                                               if key != "library_id"})
        write(snapshot / "index.json", manifest)
    with pytest.raises(ValueError):
        library.resolve(ref)
    with pytest.raises(ValueError):
        ScientificProcessLibrary(snapshot)


@pytest.mark.parametrize("malformed", ["duplicate_json_key", "nonfinite_json", "source_equality", "support_syntax"])
def test_invalid_support_source_is_never_published(tmp_path, malformed):
    source, snapshot = tmp_path / "source", tmp_path / "snapshot"
    body = synthetic_source(source)[0]
    path = source / "entries/A01.json"
    if malformed == "duplicate_json_key":
        path.write_text(path.read_text().replace('"id":"A01"', '"id":"A01","id":"A01"'))
    elif malformed == "nonfinite_json":
        path.write_text(path.read_text().replace('"name":"Synthetic support problem"', '"name":NaN'))
    elif malformed == "source_equality":
        body["evidence"][0]["limit"] = "Broader than the source table."
        write(path, body)
    else:
        body["support"]["operands"][0]["observation_kinds"] = ["invented_kind"]
        write(path, body)
    with pytest.raises(ValueError):
        ScientificProcessLibrary.freeze(snapshot, source=source)
    assert not snapshot.exists()


def test_actual_publication_stays_zero_support_nineteen_thoughts_seventy_six_rows(tmp_path):
    original = {str(path.relative_to(PUBLICATION)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in PUBLICATION.rglob("*") if path.is_file()}
    library = ScientificProcessLibrary.freeze(tmp_path / "snapshot", source=PUBLICATION)
    assert library.search(slot="annotation_distinction", query="", offset=0, limit=99)["entries"] == []
    assert len(library.headers()) == 19
    assert all(header["option_ref"]["slot"] == "thought_pattern" for header in library.headers())
    assert sum(library.entry(header["option_ref"]["option_id"])["source_count"]
               for header in library.headers()) == 76
    assert original == {str(path.relative_to(PUBLICATION)): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in PUBLICATION.rglob("*") if path.is_file()}
