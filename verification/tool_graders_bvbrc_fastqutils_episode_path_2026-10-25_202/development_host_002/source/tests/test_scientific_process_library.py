"""Scientific option persistence without a runtime, model or biological work."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from method_loop.durable import canonical, content_digest
from gene_annotation_episode.scientific_process_records import (
    scientific_digest, validate_option_ref, validate_selection,
    validate_filled_process, validate_revision)
from gene_annotation_episode.scientific_process_library import (
    ScientificProcessLibrary, catalog)


RESEARCH = (Path(__file__).resolve().parents[1] / "research/slotted_process_library"
            / "publications/2026-10-21-001")


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def synthetic_support_entry(evidence, *, option_id="A01"):
    """Explicit synthetic metadata; never an adopted scientific-support option."""
    return {"entry_version": "scientific_support_entry_v1", "id": option_id,
        "slot": "annotation_distinction", "name": "Synthetic engineering support",
        "description": "Exercise declared support operands without biological claims.",
        "support": {"proposition": "A synthetic recorded contrast bears on a bounded fixture property.",
            "operands": [{"operand_id": "synthetic_correspondence",
                "observation_kinds": ["alignment", "assay_report"],
                "hypothesis_predicates": ["functional_family"],
                "assessment_relations": ["strengthens", "weakens", "does_not_discriminate"],
                "applicabilities": ["transfer", "scope_limited"],
                "extent_bases": ["inferred_extent"],
                "finding_qualifications": ["none", "measurement_does_not_establish_claim"],
                "instruction": "Keep actual source subjects, measured facts and bounded target attribution."}],
            "qualifications": ["Fixture instructions supply no target observation or score."],
            "boundary": "Synthetic contract exercise only; the caller owns numerical policy and form."},
        "evidence": deepcopy(evidence)}


def independent_source(path, *, extra=False):
    """Small invented material, independent of the published catalog content."""
    evidence = {"case_group": "fixture_case", "case_id": "fixture_record",
        "source_url": "https://example.org/fixture", "source_locator": "Figure 2",
        "observation": "The fixture records a contrast.",
        "limit": "Engineering fixture only; no biological observation."}
    common = {"name": "Fixture option", "description": "Compare the declared alternatives.",
              "evidence": [evidence]}
    bodies = [
        synthetic_support_entry([evidence]),
        {**deepcopy(common), "id": "P01", "slot": "thought_pattern",
         "name": "Find a discriminating CONTRAST", "use_when": "Two explanations remain.",
         "live_alternatives": ["Explanation one", "Explanation two"],
         "decision_guidance": ["Look for a difference in their predictions."],
         "outcome_contingencies": [{"if_observed": "Predictions remain equal",
             "then_consider": "Revise the comparison."}],
         "boundary": "This is an iterative process, not a fixed tool itinerary."},
        {**deepcopy(common), "id": "T01", "slot": "tools",
         "capability_operations": [{"operation": "Read a selected row",
             "inputs": {"row": "integer"}, "outputs": {"value": "recorded value"}}],
         "availability": {"binding_limit": "No tools are granted by this entry."},
         "limits": ["A missing row is unknown, not a negative."]},
    ]
    if extra:
        other = deepcopy(bodies[1])
        other.update(id="P77", name="New data-defined contrast",
            decision_guidance=["Retain two rival explanations after a mixed result."])
        bodies.append(other)
    entries, rows = [], []
    for body in bodies:
        evidence_ids = ["E-" + body["id"] + "-01"]
        entries.append({**{key: body[key] for key in ("id", "slot", "name", "description")},
            "detail_path": "entries/" + body["id"] + ".json",
            "source_evidence_ids": evidence_ids})
        rows.append({"evidence_id": evidence_ids[0], "option_id": body["id"], **evidence})
        write(path / entries[-1]["detail_path"], body)
    index = {"format": "research_three_slot_options_v1", "status": "Fixture content",
        "slots": [{"slot": slot, "catalog": filename,
                   "count": sum(body["slot"] == slot for body in bodies)}
            for slot, filename in (("annotation_distinction", "annotations.json"),
                ("thought_pattern", "thoughts.json"), ("tools", "tools.json"))],
        "entries": entries}
    write(path / "index.json", index)
    write(path / "option_sources.json", {"meaning": "Instruction provenance only", "rows": rows})
    # Runtime identity must not trust the research build manifest.
    write(path / "catalog_manifest.json", {"claimed_sha256": "0" * 64})
    return bodies


@pytest.fixture
def frozen(tmp_path):
    source = tmp_path / "source"
    bodies = independent_source(source)
    directory = tmp_path / "run/scientific-process-library"
    library = ScientificProcessLibrary.freeze(directory, source=source)
    return library, source, directory, bodies


def selection(library):
    return {"version": "scientific_process_selection_v2",
        "annotation_ref": library.reference("A01"), "thought_ref": library.reference("P01"),
        "tools": ["fixture.inspect"]}


def test_curated_p_entries_are_frozen_with_their_original_source_links(tmp_path):
    directory = tmp_path / "run/scientific-process-library"
    library = ScientificProcessLibrary.freeze(directory, source=RESEARCH)
    source_index = json.loads((RESEARCH / "index.json").read_text())
    source_table = json.loads((RESEARCH / "option_sources.json").read_text())["rows"]
    expected_ids = [f"P{number:02d}" for number in range(1, 20)]
    assert [row["id"] for row in source_index["entries"]] == expected_ids
    assert [row["option_ref"]["option_id"] for row in library.headers()] == expected_ids
    assert [(row["slot"], row["count"]) for row in source_index["slots"]] == [
        ("annotation_distinction", 0), ("thought_pattern", 19)]
    assert len(source_table) == 76
    assert library.search(slot="annotation_distinction", query="", offset=0,
                          limit=99)["entries"] == []
    for unavailable in ("A01", "A10", "T01", "T13"):
        with pytest.raises(ValueError):
            library.reference(unavailable)
    observed_rows = []
    for header in source_index["entries"]:
        body = json.loads((RESEARCH / header["detail_path"]).read_text())
        ref = library.reference(header["id"])
        assert ref["entry_sha256"] == content_digest(body)
        assert library.resolve(ref) == body
        record = library.entry(header["id"])
        assert record == {"option_ref": ref, "entry": body,
                          "source_count": len(header["source_evidence_ids"])}
        offset = 0
        while True:
            page = library.sources(option_ref=ref, offset=offset, limit=2)
            observed_rows.extend(page["rows"])
            if page["next_offset"] is None:
                break
            offset = page["next_offset"]
    assert observed_rows == source_table
    reopened = ScientificProcessLibrary(directory)
    assert reopened.as_record() == library.as_record()
    assert reopened.headers() == library.headers()
    assert [row for option_id in expected_ids for row in reopened.sources(
        option_ref=reopened.reference(option_id), offset=0, limit=99)["rows"]] == source_table
    assert {path.name for path in directory.iterdir()} == {
        "index.json", "research_index.json", "entries", "sources"}
    # No raw papers, all-case archives or aggregate catalog bodies were copied.
    assert len(list(directory.rglob("*.json"))) == 40
    manifest = json.loads((directory / "index.json").read_text())
    assert library.as_record()["manifest_sha256"] == content_digest(manifest)
    assert manifest["library_id"] == content_digest({k: v for k, v in manifest.items() if k != "library_id"})
    for metadata in library._entries.values():
        assert not ({"evidence", "decision_guidance", "capability_operations", "claim_scope"} & metadata.keys())


def test_metadata_search_is_literal_paged_and_does_not_read_bodies(frozen, monkeypatch):
    library, _, _, _ = frozen
    monkeypatch.setattr(library, "_read_selected", lambda entry: pytest.fail("metadata loaded a body"))
    result = library.search(slot="thought_pattern", query="CONTRAST discriminating", offset=0, limit=1)
    assert [header["option_ref"]["option_id"] for header in result["entries"]] == ["P01"]
    assert set(result["entries"][0]) == {"option_ref", "name", "description"}
    assert library.search(slot=None, query="", offset=0, limit=1)["next_offset"] == 1
    assert library.search(slot=None, query="", offset=2, limit=2)["next_offset"] is None
    assert library.search(slot=None, query="contrast.*", offset=0, limit=99)["entries"] == []
    with pytest.raises(ValueError):
        library.search(slot="tools", query="discriminating", offset=0, limit=99)


def test_lookup_source_paging_and_returned_values_are_detached(frozen):
    library, _, _, bodies = frozen
    assert library.entry("P01")["entry"] == bodies[1]
    ref = library.reference("P01")
    page = library.sources(option_ref=ref, offset=0, limit=1)
    assert page["rows"][0]["limit"] == bodies[1]["evidence"][0]["limit"]
    assert page["next_offset"] is None
    assert library.sources(option_ref=ref, offset=10, limit=1)["rows"] == []
    page["rows"][0]["limit"] = "changed caller copy"
    body = library.resolve(ref)
    body["decision_guidance"].append("caller mutation")
    header = library.headers()[0]
    header["option_ref"]["library_id"] = "0" * 64
    assert library.resolve(ref) == bodies[1]
    assert library.sources(option_ref=ref, offset=0, limit=1)["rows"][0]["limit"] == bodies[1]["evidence"][0]["limit"]


def test_new_data_defined_entry_and_source_updates_do_not_replace_snapshot(tmp_path):
    source = tmp_path / "source"
    bodies = independent_source(source, extra=True)
    library = ScientificProcessLibrary.freeze(tmp_path / "snapshot", source=source)
    original = library.as_record()
    assert library.entry("P77")["entry"] == bodies[-1]
    changed = deepcopy(bodies[-1])
    changed["decision_guidance"] = ["A later source revision."]
    write(source / "entries/P77.json", changed)
    assert ScientificProcessLibrary.freeze(tmp_path / "snapshot", source=source).as_record() == original
    shutil.rmtree(source)
    reopened = ScientificProcessLibrary.freeze(tmp_path / "snapshot", source=source)
    assert reopened.entry("P77")["entry"] == bodies[-1]


def test_atomic_concurrent_freeze_keeps_one_complete_snapshot(tmp_path):
    source = tmp_path / "source"
    independent_source(source)
    destination = tmp_path / "snapshot"
    with ThreadPoolExecutor(max_workers=4) as pool:
        libraries = list(pool.map(lambda _: ScientificProcessLibrary.freeze(destination, source=source), range(4)))
    assert all(library.as_record() == libraries[0].as_record() for library in libraries)
    assert all(library.entry("P01") == libraries[0].entry("P01") for library in libraries)


def test_recomputed_source_pins_cannot_detach_rows_from_entry(frozen):
    _, _, directory, _ = frozen
    path = directory / "sources/P01.json"
    rows = json.loads(path.read_text())
    rows[0]["limit"] = "Broader than the entry actually established."
    path.write_text(canonical(rows) + "\n")
    manifest_path = directory / "index.json"
    manifest = json.loads(manifest_path.read_text())
    metadata = next(entry for entry in manifest["entries"] if entry["option_id"] == "P01")
    metadata["sources_sha256"] = scientific_digest(rows)
    metadata["sources_file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest["library_id"] = scientific_digest({k: v for k, v in manifest.items() if k != "library_id"})
    manifest_path.write_text(canonical(manifest) + "\n")
    with pytest.raises(ValueError, match="source_entry_mismatch"):
        ScientificProcessLibrary(directory)


def test_selected_snapshot_paths_cannot_escape_through_symlinks(frozen, tmp_path):
    library, _, directory, _ = frozen
    path = directory / "entries/P01.json"
    external = tmp_path / "external.json"
    external.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(external)
    with pytest.raises(ValueError, match="entry_changed"):
        library.entry("P01")
    with pytest.raises(ValueError, match="entry_changed"):
        ScientificProcessLibrary(directory)


@pytest.mark.parametrize("relative,operation,error", [
    ("index.json", "search", "snapshot_changed"),
    ("research_index.json", "entry", "snapshot_changed"),
    ("entries/P01.json", "entry", "entry_changed"),
    ("sources/P01.json", "sources", "sources_changed"),
])
def test_live_reads_and_reopen_reject_byte_drift_even_when_json_is_unchanged(frozen, relative, operation, error):
    library, _, directory, _ = frozen
    ref = library.reference("P01")
    path = directory / relative
    path.write_bytes(path.read_bytes() + b" \n")
    if operation == "search":
        call = lambda: library.search(slot=None, query="", offset=0, limit=1)
    elif operation == "entry":
        call = lambda: library.entry("P01")
    else:
        call = lambda: library.sources(option_ref=ref, offset=0, limit=1)
    with pytest.raises(ValueError, match=error):
        call()
    with pytest.raises(ValueError, match=error):
        ScientificProcessLibrary(directory)


@pytest.mark.parametrize("relative", ["index.json", "research_index.json", "entries/P01.json", "sources/P01.json"])
def test_content_drift_and_missing_files_are_rejected(frozen, relative):
    library, _, directory, _ = frozen
    path = directory / relative
    value = json.loads(path.read_text())
    if relative == "index.json":
        value["entries"][0]["description"] = "A changed annotation focus."
    elif relative == "research_index.json":
        value["entries"][0]["description"] = "A changed annotation focus."
    elif relative.startswith("entries/"):
        value["decision_guidance"] = ["Changed process meaning."]
    else:
        value[0]["limit"] = "An incorrectly broadened limit."
    write(path, value)
    with pytest.raises(ValueError):
        ScientificProcessLibrary(directory)
    path.unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        library.entry("P01")


@pytest.mark.parametrize("mutation", ["duplicate_option", "duplicate_row", "wrong_source_id", "wrong_evidence", "wrong_index", "orphan_row", "wrong_namespace", "path_escape"])
def test_malformed_source_relationships_fail_without_publishing(tmp_path, mutation):
    source = tmp_path / "source"
    independent_source(source)
    index_path, rows_path = source / "index.json", source / "option_sources.json"
    index, table = json.loads(index_path.read_text()), json.loads(rows_path.read_text())
    if mutation == "duplicate_option":
        index["entries"].append(index["entries"][0])
    elif mutation == "duplicate_row":
        table["rows"].append(table["rows"][0])
    elif mutation == "wrong_source_id":
        index["entries"][0]["source_evidence_ids"] = ["E-P01-99"]
    elif mutation == "wrong_evidence":
        table["rows"][0]["observation"] = "A different observation."
    elif mutation == "wrong_index":
        index["entries"][0]["name"] = "Wrong title"
    elif mutation == "orphan_row":
        row = deepcopy(table["rows"][0])
        row.update(option_id="A99", evidence_id="E-A99-01")
        table["rows"].append(row)
    elif mutation == "wrong_namespace":
        index["entries"][0]["slot"] = "tools"
    elif mutation == "path_escape":
        index["entries"][0]["detail_path"] = "../external.json"
    write(index_path, index)
    write(rows_path, table)
    destination = tmp_path / "snapshot"
    with pytest.raises(ValueError):
        ScientificProcessLibrary.freeze(destination, source=source)
    assert not destination.exists()


def test_duplicate_json_keys_and_nonfinite_json_fail_before_publication(tmp_path):
    source = tmp_path / "source"
    independent_source(source)
    body = source / "entries/P01.json"
    body.write_text('{"id":"P01","id":"P02"}')
    with pytest.raises(ValueError):
        ScientificProcessLibrary.freeze(tmp_path / "snapshot", source=source)
    independent_source(source)
    body.write_text(body.read_text().replace('"decision_guidance": [', '"nonfinite": NaN, "decision_guidance": ['))
    with pytest.raises(ValueError):
        ScientificProcessLibrary.freeze(tmp_path / "snapshot", source=source)


def test_selected_reference_must_match_all_pinned_identity_fields(frozen):
    library, _, _, _ = frozen
    for name, replacement in (("library_id", "0" * 64), ("entry_sha256", "0" * 64),
                              ("option_id", "P99"), ("slot", "tools")):
        ref = library.reference("P01")
        ref[name] = replacement
        with pytest.raises(ValueError):
            library.resolve(ref)
        with pytest.raises(ValueError):
            library.sources(option_ref=ref, offset=0, limit=1)


def test_all_tool_outcomes_publish_no_scientific_records(frozen):
    library, _, _, _ = frozen
    assert [entry["name"] for entry in catalog()] == ["process.search", "process.entry", "process.sources"]
    calls = [("process.search", {"slot": None, "query": "", "offset": 0, "limit": 1}),
        ("process.entry", {"option_id": "P01"}),
        ("process.sources", {"option_ref": library.reference("P01"), "offset": 0, "limit": 1})]
    for name, arguments in calls:
        outcome = library.execute(name, arguments)
        assert outcome["status"] == "completed"
        assert outcome["record_refs"] == outcome["changed_record_refs"] == []
        assert outcome["feedback"] is None
    for name, arguments in [("process.entry", {"option_id": "P99"}),
        ("process.search", {"slot": None, "query": "", "offset": True, "limit": 1}),
        ("process.entry", {"option_id": "P01", "extra": 1}),
        ("process.sources", {"option_ref": library.reference("P01"), "offset": 0, "limit": 0}),
        ("process.unknown", {}), ("process.entry", {"option_id": float("inf")})]:
        outcome = library.execute(name, arguments)
        assert outcome["status"] == "failed"
        assert outcome["record_refs"] == outcome["changed_record_refs"] == []
        assert outcome["feedback"]["code"]


def test_versioned_records_exact_fields_digest_shapes_and_detachment(frozen):
    library, _, _, _ = frozen
    selected = selection(library)
    filled = {"version": "filled_scientific_process_v1", "selection": selected,
        "assignment_sha256": "a" * 64, "invocation_sha256": "b" * 64,
        "mechanics_binding": {"id": "caller-bound-mechanics", "configuration": [1]}}
    revision = {"version": "scientific_process_revision_v1",
        "initial_selection_sha256": scientific_digest(selected),
        "previous_selection_sha256": scientific_digest(selected), "selection": selected}
    for value, validator in ((library.reference("A01"), validate_option_ref),
        (selected, validate_selection), (filled, validate_filled_process),
        (revision, validate_revision)):
        result = validator(value)
        assert result == value and result is not value
        broken = deepcopy(value)
        broken["unrecognized"] = True
        with pytest.raises(ValueError):
            validator(broken)
        broken = deepcopy(value)
        broken["version"] = "future_or_wrong_version"
        with pytest.raises(ValueError):
            validator(broken)
    detached = validate_filled_process(filled)
    detached["mechanics_binding"]["configuration"].append(2)
    assert filled["mechanics_binding"]["configuration"] == [1]
    assert scientific_digest({"b": (2, 3), "a": 1}) == hashlib.sha256(canonical({"a": 1, "b": [2, 3]}).encode()).hexdigest()


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), {1: "non-string key"}, object()])
def test_records_reject_nonfinite_or_unsupported_json(frozen, bad):
    library, _, _, _ = frozen
    filled = {"version": "filled_scientific_process_v1", "selection": selection(library),
        "assignment_sha256": "a" * 64, "invocation_sha256": "b" * 64,
        "mechanics_binding": {"id": "fixture", "bad": bad}}
    with pytest.raises((ValueError, TypeError)):
        validate_filled_process(filled)
    with pytest.raises((ValueError, TypeError)):
        scientific_digest({"bad": bad})


def test_record_namespace_common_library_and_nonempty_binding(frozen):
    library, _, _, _ = frozen
    selected = selection(library)
    selected["thought_ref"]["library_id"] = "0" * 64
    with pytest.raises(ValueError):
        validate_selection(selected)
    selected = selection(library)
    selected["annotation_ref"], selected["thought_ref"] = selected["thought_ref"], selected["annotation_ref"]
    with pytest.raises(ValueError):
        validate_selection(selected)
    for digest in ("0" * 63, "g" * 64, "A" * 64, 1, None):
        ref = library.reference("A01")
        ref["entry_sha256"] = digest
        with pytest.raises(ValueError):
            validate_option_ref(ref)
    with pytest.raises(ValueError):
        validate_filled_process({"version": "filled_scientific_process_v1",
            "selection": selection(library), "assignment_sha256": "a" * 64,
            "invocation_sha256": "b" * 64, "mechanics_binding": {}})


def test_ap_only_source_needs_no_historical_tool_definitions(tmp_path):
    source = tmp_path / "source"
    independent_source(source)
    index = json.loads((source / "index.json").read_text())
    index["slots"] = [row for row in index["slots"] if row["slot"] != "tools"]
    index["entries"] = [row for row in index["entries"] if row["slot"] != "tools"]
    write(source / "index.json", index)
    table = json.loads((source / "option_sources.json").read_text())
    table["rows"] = [row for row in table["rows"] if not row["option_id"].startswith("T")]
    write(source / "option_sources.json", table)
    (source / "entries/T01.json").unlink()
    library = ScientificProcessLibrary.freeze(tmp_path / "library", source=source)
    assert [row["option_ref"]["option_id"] for row in library.headers()] == ["A01", "P01"]
    with pytest.raises(ValueError):
        library.reference("T01")


def test_old_selected_tool_bundle_is_rejected_instead_of_reinterpreted(frozen):
    library, _, _, _ = frozen
    old = selection(library)
    old["version"] = "scientific_process_selection_v1"
    old["tool_ref"] = old.pop("tools")
    with pytest.raises(ValueError, match="selection_invalid"):
        validate_selection(old)


def test_legacy_annotation_body_remains_exactly_readable_without_support_upgrade(tmp_path):
    source = tmp_path / "legacy-source"
    independent_source(source)
    body = {"id": "A01", "slot": "annotation_distinction", "name": "Synthetic engineering support",
        "description": "Exercise declared support operands without biological claims.",
        "claim_scope": "Historical fixture relationship.", "distinctions": ["Historical distinction."],
        "not_established": ["No adopted support body."], "boundary": "Original legacy boundary.",
        "example_structured_values": {"legacy": ["illustration"]},
        "evidence": json.loads((source / "entries/A01.json").read_text())["evidence"]}
    write(source / "entries/A01.json", body)
    library = ScientificProcessLibrary.freeze(tmp_path / "legacy-snapshot", source=source)
    assert library.resolve(library.reference("A01")) == body
    assert "entry_version" not in library.entry("A01")["entry"]
    shutil.rmtree(source)
    assert ScientificProcessLibrary(library.directory).entry("A01")["entry"] == body
