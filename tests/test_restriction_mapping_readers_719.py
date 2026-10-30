"""Labelled synthetic reader semantics; no native search or measured biology.

The fabricated source/catalog identifiers below are engineering fixtures only.
Authentic observing-producer artifacts are tested separately after718 delivers
their retained paths. All application execution requires bounded529.
"""
import builtins
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.restriction_mapping_contracts import (
    restriction_digest, restriction_issue, validate_restriction_record,
)
from gene_annotation_episode.restriction_mapping_readers import read_restriction_mapping


pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")
_PIN = {"path": "/synthetic719/dictionary.py", "sha256": "a" * 64, "size_bytes": 123}


def _profile(name, motif, offsets, *, kind="one_cut", symmetry="palindromic", pattern=None):
    fst5, fst3, scd5, scd3, ovhg = offsets
    pattern = pattern or "(?=(?P<" + name + ">" + motif + "))"
    dictionary = {"site": motif, "size": len(motif), "fst5": fst5, "fst3": fst3,
        "scd5": scd5, "scd3": scd3, "ovhg": ovhg, "id": 99, "uri": "synthetic719",
        "compsite": pattern}
    return {"ordinal": 0, "name": name, "native_site": motif, "size_nt": len(motif),
        "elucidate_text": "synthetic native-text fixture", "elucidate_error": None,
        "fst5": fst5, "fst3": fst3, "scd5": scd5, "scd3": scd3, "native_ovhg": ovhg,
        "native_pattern": {"text": pattern, "flags": 32},
        "native_class_mro": [name, "Palindromic" if symmetry == "palindromic" else "NonPalindromic",
            {"one_cut": "OneCut", "two_cuts": "TwoCuts", "no_cut": "NoCut"}[kind], "AbstractCut"],
        "cut_kind": kind, "symmetry": symmetry,
        "position_meaning": "recognition_start_1based" if kind == "no_cut" else "first_base_after_cut_1based",
        "is_commercial": True, "rebase_id": 99, "rebase_uri": "synthetic719",
        "dictionary_entry_json": json.dumps(dictionary, sort_keys=True)}


def _fixture(*, sequence="AAAAGAATTCTTTT", topology="linear", specs=None, reverse_order=False):
    """Construct supplied records, not scientific observations or a producer."""
    if specs is None:
        specs = [(_profile("EcoRI", "GAATTC", (1, -1, None, None, -4)), [6],
                  [(5, {"EcoRI": "GAATTC"})])]
    catalog_rows = []
    for ordinal, (profile, _, _) in enumerate(specs):
        profile = deepcopy(profile)
        profile["ordinal"] = ordinal
        catalog_rows.append(profile)
    names = [row["name"] for row in catalog_rows]
    selection = {"kind": "explicit", "names": names}
    binding = {"version": "restriction_selected_sequence_v1", "namespace": "subject",
        "sequence_ref": "subject_synthetic719", "source_ref": "source_synthetic719",
        "sequence_version": 0, "content_sha256": hashlib.sha256(sequence.encode()).hexdigest(),
        "length_nt": len(sequence), "origin_mapping_ref": None}
    catalog = {"version": "restriction_catalog_snapshot_v1", "biopython_version": "1.88",
        "dictionary_file": deepcopy(_PIN), "selection": deepcopy(selection),
        "resolved_names": names, "enzymes": catalog_rows}
    order = list(reversed(names)) if reverse_order else list(names)
    searches, calls = [], []
    for ordinal, (row, (_, positions, matches)) in enumerate(zip(catalog_rows, specs)):
        searches.append({"catalog_ordinal": ordinal, "name": row["name"],
            "search_ordinal": order.index(row["name"]), "state": "returned",
            "native_search_positions_1based": deepcopy(positions),
            "native_on_minus_before_drop": None, "error": None})
    for call_ordinal, name in enumerate(order):
        ordinal = names.index(name)
        row, (_, _, matches) = catalog_rows[ordinal], specs[ordinal]
        calls.append({"call_ordinal": call_ordinal, "owner_ordinals": [ordinal],
            "native_pattern": deepcopy(row["native_pattern"]), "site_size_nt": row["size_nt"],
            "linear": topology == "linear", "state": "returned",
            "matches": [{"match_ordinal": i, "native_start_1based": start,
                "groups": [{"name": n, "text": text} for n, text in groups.items()]}
                for i, (start, groups) in enumerate(matches)], "error": None})
    native = {"version": "restriction_mapping_native_v1",
        "request": {"sequence": sequence, "normalized_sequence": sequence.upper(),
            "sequence_binding": binding, "enzyme_selection": selection, "topology": topology},
        "software": {"biopython_version": "1.88", "dictionary_file": deepcopy(_PIN),
            "native_source_file": {**_PIN, "path": "/synthetic719/native.py"}},
        "catalog": catalog, "formatted_sequence": " " + sequence.upper(),
        "native_batch_member_order": order, "batch_state": "returned", "native_mapping_order": list(order),
        "enzyme_searches": searches, "match_observations": calls,
        "warnings": [], "issues": [], "exception": None}
    validate_restriction_record("NativeResult", native)
    return native


def _read(native, *, selected=None, catalog=None):
    return read_restriction_mapping(native,
        selected_sequence=selected or native["request"]["sequence_binding"],
        enzyme_catalog=native["catalog"] if catalog is None else catalog)


def test_source_positions_coordinate_arithmetic_and_detached_catalog():
    native = _fixture()
    original = deepcopy(native)
    result = _read(native)
    assert result["status"] == "complete" and result["binding_status"] == "matched"
    row, = result["enzyme_rows"]
    assert row["native_search_positions_1based"] == [6]
    assert row["returned_position_count"] == row["recognition_match_count"] == 1
    assert row["positions"][0] == {"position_ordinal": 0, "native_position": 6,
        "watson_boundary_0based": 5, "crick_boundary_0based": 9,
        "watson_canonical_boundary_0based": 5, "crick_canonical_boundary_0based": 9,
        "geometry_state": "known", "recognition_association": "not_recorded",
        "recognition_event_ordinal": None}
    event, = row["recognition_events"]
    assert event["orientation"] == "palindromic" and event["segments"] == [{"start": 4, "end": 10}]
    assert event["unwrapped_span_0based"] == [4, 10] and event["crosses_origin"] is False
    assert row["catalog_row"] == native["catalog"]["enzymes"][0]
    assert result["native_sha256"] == restriction_digest(native)
    row["catalog_row"]["native_site"] = "changed caller copy"
    assert native == original


def test_zero_rows_preserve_actual_population_and_order_joins():
    specs = [(_profile("EcoRI", "GAATTC", (1, -1, None, None, -4)), [6], [(5, {"EcoRI": "GAATTC"})]),
             (_profile("BamHI", "GGATCC", (1, -1, None, None, -4)), [], [])]
    native = _fixture(specs=specs, reverse_order=True)
    result = _read(native)
    assert result["status"] == "complete"
    assert [row["name"] for row in result["enzyme_rows"]] == ["EcoRI", "BamHI"]
    assert result["enzyme_rows"][0]["recognition_events"][0]["match_call_ordinal"] == 1
    assert result["population"] == {"selected_enzyme_count": 2, "attempted_enzyme_count": 2,
        "returned_enzyme_count": 2, "complete_empty_enzyme_count": 1, "recognition_match_count": 1}


def test_two_positions_do_not_become_two_recognition_events():
    sequence = "A" * 50 + "CGA" + "A" * 6 + "TGC" + "A" * 50
    profile = _profile("BcgI", "CGANNNNNNTGC", (-10, -24, 24, 10, 2),
        kind="two_cuts", symmetry="nonpalindromic",
        pattern="(?=(?P<BcgI>CGA......TGC))|(?=(?P<BcgI_as>GCA......TCG))")
    native = _fixture(sequence=sequence, specs=[(profile, [41, 75],
        [(51, {"BcgI": "CGA" + "A" * 6 + "TGC", "BcgI_as": None})])])
    row, = _read(native)["enzyme_rows"]
    assert row["returned_position_count"] == 2 and row["recognition_match_count"] == 1
    assert [(p["watson_boundary_0based"], p["crick_boundary_0based"]) for p in row["positions"]] == [(40, 38), (74, 72)]
    assert all(p["recognition_event_ordinal"] is None for p in row["positions"])


def test_nocut_recognition_starts_do_not_acquire_cleavage_boundaries():
    profile = _profile("SnaI", "GTATAC", (None, None, None, None, None), kind="no_cut")
    native = _fixture(sequence="AAAAGTATACTTTT", specs=[(profile, [5], [(5, {"SnaI": "GTATAC"})])])
    result = _read(native)
    row, = result["enzyme_rows"]
    assert result["status"] == "complete" and row["position_meaning"] == "recognition_start_1based"
    assert row["positions"][0]["geometry_state"] == "unknown"
    assert all(row["positions"][0][name] is None for name in
        ("watson_boundary_0based", "crick_boundary_0based", "watson_canonical_boundary_0based", "crick_canonical_boundary_0based"))
    assert row["recognition_events"][0]["segments"] == [{"start": 4, "end": 10}]


def test_circular_origin_spans_and_separate_canonical_boundaries():
    profile = _profile("EcoRI", "GAATTC", (1, -1, None, None, -4))
    native = _fixture(sequence="AATTCAAAAG", topology="circular",
        specs=[(profile, [1], [(10, {"EcoRI": "GAATTC"})])])
    row, = _read(native)["enzyme_rows"]
    assert row["recognition_events"][0]["segments"] == [{"start": 9, "end": 10}, {"start": 0, "end": 5}]
    assert row["recognition_events"][0]["crosses_origin"] is True
    assert row["positions"][0]["watson_boundary_0based"] == 0
    assert row["positions"][0]["crick_boundary_0based"] == 4


def test_negative_native_integer_is_preserved_separate_from_modulo():
    profile = _profile("FarCut", "ATGC", (-30, -34, None, None, -4))
    native = _fixture(sequence="AAAAATGCAA", topology="circular",
        specs=[(profile, [-14], [(6, {"FarCut": "ATGC"})])])
    row, = _read(native)["enzyme_rows"]
    assert row["native_search_positions_1based"] == [-14]
    p, = row["positions"]
    assert (p["watson_boundary_0based"], p["crick_boundary_0based"]) == (-15, -11)
    assert (p["watson_canonical_boundary_0based"], p["crick_canonical_boundary_0based"]) == (5, 9)


def test_reverse_native_group_is_interpreted_without_a_new_match():
    profile = _profile("BsaI", "GGTCTC", (7, 5, None, None, -4), symmetry="nonpalindromic",
        pattern="(?=(?P<BsaI>GGTCTC))|(?=(?P<BsaI_as>GAGACC))")
    native = _fixture(sequence="A" * 15 + "GAGACC" + "A" * 15,
        specs=[(profile, [11], [(16, {"BsaI": None, "BsaI_as": "GAGACC"})])])
    event = _read(native)["enzyme_rows"][0]["recognition_events"][0]
    assert event["orientation"] == "reverse" and event["unwrapped_span_0based"] == [15, 21]


@pytest.mark.parametrize("fault", ["bool_position", "float_position", "missing_row", "duplicate_row", "extra_row_field", "wrong_row_name"])
def test_bad_individual_rows_keep_independent_completed_empty_rows(fault):
    specs = [(_profile("EcoRI", "GAATTC", (1, -1, None, None, -4)), [6], [(5, {"EcoRI": "GAATTC"})]),
             (_profile("BamHI", "GGATCC", (1, -1, None, None, -4)), [], [])]
    native = _fixture(specs=specs)
    if fault == "bool_position": native["enzyme_searches"][0]["native_search_positions_1based"] = [True]
    elif fault == "float_position": native["enzyme_searches"][0]["native_search_positions_1based"] = [6.0]
    elif fault == "missing_row": native["enzyme_searches"].pop(0)
    elif fault == "duplicate_row": native["enzyme_searches"].append(deepcopy(native["enzyme_searches"][0]))
    elif fault == "extra_row_field": native["enzyme_searches"][0]["function_confidence"] = 1
    else: native["enzyme_searches"][0]["name"] = "unselected name"
    result = _read(native)
    assert result["status"] == "partial"
    broken, retained = result["enzyme_rows"]
    assert broken["search_state"] == "invalid" and broken["returned_position_count"] is None
    assert retained["native_search_positions_1based"] == [] and retained["returned_position_count"] == 0
    assert result["population"]["returned_enzyme_count"] == result["population"]["complete_empty_enzyme_count"] == 1


@pytest.mark.parametrize("fault", ["selected_source", "input_hash", "catalog_file", "catalog_version", "pattern_flags", "formatted_input"])
def test_global_identity_conflicts_do_not_attribute_geometry(fault):
    native = _fixture();selected = deepcopy(native["request"]["sequence_binding"]);catalog = deepcopy(native["catalog"])
    if fault == "selected_source": selected["source_ref"] = "another_source"
    elif fault == "input_hash": native["request"]["sequence_binding"]["content_sha256"] = "b" * 64
    elif fault == "catalog_file": catalog["dictionary_file"]["sha256"] = "b" * 64
    elif fault == "catalog_version": catalog["biopython_version"] = "1.89"
    elif fault == "pattern_flags": native["catalog"]["enzymes"][0]["native_pattern"]["flags"] = 0
    else: native["formatted_sequence"] = " different"
    result = _read(native, selected=selected, catalog=catalog)
    assert result["status"] in ("invalid", "partial")
    assert result["enzyme_rows"][0]["positions"][0]["geometry_state"] == "unavailable"
    assert result["enzyme_rows"][0]["positions"][0]["watson_boundary_0based"] is None


@pytest.mark.parametrize("fault", ["missing_capture", "duplicate_capture", "wrong_owner", "bad_group", "wrong_topology"])
def test_observer_corruption_does_not_manufacture_recognition_count(fault):
    native = _fixture()
    if fault == "missing_capture": native["match_observations"] = []
    elif fault == "duplicate_capture": native["match_observations"].append(deepcopy(native["match_observations"][0]))
    elif fault == "wrong_owner": native["match_observations"][0]["owner_ordinals"] = []
    elif fault == "bad_group": native["match_observations"][0]["matches"][0]["groups"][0]["text"] = "TTTTTT"
    else: native["match_observations"][0]["linear"] = False
    result = _read(native)
    assert result["status"] == "partial"
    assert result["enzyme_rows"][0]["returned_position_count"] == 1
    assert result["enzyme_rows"][0]["recognition_match_count"] is None
    assert result["population"]["recognition_match_count"] is None


def test_failed_and_unstarted_rows_are_not_complete_negatives():
    specs = [(_profile("EcoRI", "GAATTC", (1, -1, None, None, -4)), [6], [(5, {"EcoRI": "GAATTC"})]),
             (_profile("BamHI", "GGATCC", (1, -1, None, None, -4)), [], []),
             (_profile("SnaI", "GTATAC", (None, None, None, None, None), kind="no_cut"), [], [])]
    native = _fixture(specs=specs)
    error = {"module": "builtins", "class": "RuntimeError", "message": "synthetic fault"}
    native.update(batch_state="failed", native_mapping_order=None, exception=error)
    native["enzyme_searches"][1].update(state="failed", native_search_positions_1based=None, error=error)
    native["enzyme_searches"][2].update(state="not_started", search_ordinal=None, native_search_positions_1based=None)
    native["match_observations"] = native["match_observations"][:1]
    result = _read(native)
    assert [row["search_state"] for row in result["enzyme_rows"]] == ["returned", "failed", "not_started"]
    assert result["population"]["attempted_enzyme_count"] == 2
    assert result["population"]["returned_enzyme_count"] == 1
    assert result["population"]["complete_empty_enzyme_count"] == 0
    assert result["population"]["recognition_match_count"] is None


def test_selected_empty_population_is_complete_with_exact_zero_counts():
    native = _fixture(specs=[])
    result = _read(native)
    assert result["status"] == "complete" and result["enzyme_rows"] == []
    assert set(result["population"].values()) == {0}


def test_original_input_failure_codes_are_preserved_without_fabricated_results():
    native = _fixture()
    native.update(catalog=None, batch_state="not_started", formatted_sequence=None,
        native_batch_member_order=[], native_mapping_order=None, enzyme_searches=[], match_observations=[])
    native["issues"] = [restriction_issue("enzyme_unknown", "input", enzyme_ordinal=0)]
    result = read_restriction_mapping(native, selected_sequence=native["request"]["sequence_binding"], enzyme_catalog=None)
    assert result["status"] == "invalid" and result["enzyme_rows"] == []
    assert any(issue["code"] == "enzyme_unknown" for issue in result["issues"])
    assert result["population"]["selected_enzyme_count"] is None


def test_unavailable_native_data_and_malformed_selected_binding_remain_distinct():
    native = _fixture()
    result = read_restriction_mapping(None, selected_sequence=native["request"]["sequence_binding"], enzyme_catalog=native["catalog"])
    assert result["status"] == "unavailable" and result["population"]["selected_enzyme_count"] is None
    with pytest.raises(ValueError): read_restriction_mapping(native, selected_sequence={}, enzyme_catalog=native["catalog"])


def test_saved_reader_has_no_native_import_io_network_or_dispatch(monkeypatch):
    native = _fixture()
    expected = _read(native)
    original_import = builtins.__import__
    def imports(name, *args, **kwargs):
        if name == "Bio" or name.startswith("Bio.") or name.endswith("restriction_mapping_native"):
            raise AssertionError("reader imported native implementation")
        return original_import(name, *args, **kwargs)
    def denied(*args, **kwargs): raise AssertionError("reader attempted I/O, network or dispatch")
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "__import__", imports)
        patch.setattr(builtins, "open", denied);patch.setattr(io, "open", denied);patch.setattr(Path, "open", denied)
        patch.setattr(socket.socket, "connect", denied);patch.setattr(socket, "create_connection", denied)
        patch.setattr(subprocess, "run", denied);patch.setattr(subprocess, "Popen", denied)
        actual = _read(native)
    assert actual == expected


@pytest.fixture(scope="module")
def retained_observing_results():
    """Read actual718 records, including explicitly labelled engineering faults."""
    root = Path(__file__).resolve().parents[1]
    pins = json.loads((root / "verification/tool_graders_restriction_mapping_2026-10-29_718/NATIVE_FIXTURE_PINS_001.json").read_text())
    directory = root / "verification/tool_graders_hmmer_map_verification_2026-10-28_529/check182_native718/restriction-native718"
    native, results = {}, {}
    for pin in pins:
        path = directory / Path(pin["path"]).name
        raw = path.read_bytes()
        assert len(raw) == pin["size_bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"]
        if path.name == "MANIFEST.json":
            continue
        record = json.loads(raw)
        native[path.stem] = record
        results[path.stem] = read_restriction_mapping(record,
            selected_sequence=record["request"]["sequence_binding"], enzyme_catalog=record["catalog"])
    assert len(native) == 13
    destination = Path(os.environ["HMMER529_ATTEMPT"]) / "retained-reader719"
    destination.mkdir(exist_ok=False)
    for name, result in results.items():
        (destination / (name + ".json")).write_text(json.dumps(result, sort_keys=True, allow_nan=False) + "\n")
    return native, results


def test_all_retained_observing_formats_keep_native_rows_and_catalog(retained_observing_results):
    natives, results = retained_observing_results
    for name, native in natives.items():
        result = results[name]
        assert result["native_sha256"] == restriction_digest(native)
        assert result["binding_status"] == "matched"
        assert result["status"] == ("partial" if name.startswith("engineering_") else "complete")
        assert result["population"]["selected_enzyme_count"] == len(native["catalog"]["enzymes"])
        by_name = {row["name"]: row for row in native["enzyme_searches"]}
        for row in result["enzyme_rows"]:
            original = by_name[row["name"]]
            assert row["native_search_positions_1based"] == original["native_search_positions_1based"]
            assert row["search_state"] == original["state"]
            assert row["catalog_row"] == native["catalog"]["enzymes"][row["catalog_ordinal"]]
    population = results["commercial_linear_internal"]["population"]
    assert population["selected_enzyme_count"] == population["returned_enzyme_count"] == 623
    assert population["complete_empty_enzyme_count"] == 616
    assert results["empty_explicit"]["population"] == {"selected_enzyme_count": 0,
        "attempted_enzyme_count": 0, "returned_enzyme_count": 0,
        "complete_empty_enzyme_count": 0, "recognition_match_count": 0}


def test_actual_nocut_reverse_duplicate_short_circle_and_fault_meanings(retained_observing_results):
    _, results = retained_observing_results
    no_cut, = results["nocut_snai"]["enzyme_rows"]
    assert no_cut["native_search_positions_1based"] == [5]
    assert no_cut["position_meaning"] == "recognition_start_1based"
    assert no_cut["positions"][0]["geometry_state"] == "unknown"
    assert no_cut["positions"][0]["watson_boundary_0based"] is None
    reverse, = results["reverse_bsai"]["enzyme_rows"]
    assert reverse["native_search_positions_1based"] == [26]
    assert reverse["recognition_events"][0]["orientation"] == "reverse"
    assert reverse["recognition_events"][0]["unwrapped_span_0based"] == [30, 36]
    assert (reverse["positions"][0]["watson_boundary_0based"], reverse["positions"][0]["crick_boundary_0based"]) == (25, 29)
    duplicate, = results["duplicate_bcgi"]["enzyme_rows"]
    assert duplicate["native_search_positions_1based"] == [41, 75, 75, 109]
    assert duplicate["returned_position_count"] == 4 and duplicate["recognition_match_count"] == 2
    assert [position["position_ordinal"] for position in duplicate["positions"]] == [0, 1, 2, 3]
    assert all(position["recognition_event_ordinal"] is None for position in duplicate["positions"])
    short, = results["short_circle_bcgi"]["enzyme_rows"]
    assert short["native_search_positions_1based"] == [3, 13]
    assert [p["watson_boundary_0based"] for p in short["positions"]] == [2, 12]
    assert [p["watson_canonical_boundary_0based"] for p in short["positions"]] == [2, 0]
    partial = results["engineering_partial_search"]
    assert sorted(row["search_state"] for row in partial["enzyme_rows"]) == ["failed", "not_started", "returned"]
    assert partial["population"]["attempted_enzyme_count"] == 2
    assert partial["population"]["returned_enzyme_count"] == 1
    observer, = results["engineering_observer_failure"]["enzyme_rows"]
    assert observer["native_search_positions_1based"] == [6] and observer["returned_position_count"] == 1
    assert observer["recognition_events"] is None and observer["recognition_match_count"] is None


def test_actual_saved_records_read_with_native_io_and_network_forbidden(retained_observing_results, monkeypatch):
    native, results = retained_observing_results
    original_import = builtins.__import__
    def imports(name, *args, **kwargs):
        if name == "Bio" or name.startswith("Bio.") or name.endswith("restriction_mapping_native"):
            raise AssertionError("actual saved reader imported native implementation")
        return original_import(name, *args, **kwargs)
    def denied(*args, **kwargs): raise AssertionError("actual saved reader attempted I/O or dispatch")
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "__import__", imports)
        patch.setattr(builtins, "open", denied);patch.setattr(io, "open", denied);patch.setattr(Path, "open", denied)
        patch.setattr(socket.socket, "connect", denied);patch.setattr(socket, "create_connection", denied)
        patch.setattr(subprocess, "run", denied);patch.setattr(subprocess, "Popen", denied)
        for name in ("commercial_linear_internal", "nocut_snai", "engineering_partial_search"):
            assert _read(native[name]) == results[name]
