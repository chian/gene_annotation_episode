"""One retained observing-producer dataset; native calls never serve assertions.

Baseline values come from the original717 capture. New native source captures
match groups and tests meaningful geometry/partial cases. Faults are labelled.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode import restriction_mapping_native as producer
from gene_annotation_episode.restriction_mapping_contracts import (
    restriction_canonical, restriction_schema, validate_restriction_record,
)

ATTEMPT = Path(os.environ["HMMER529_ATTEMPT"]) if "HMMER529_ATTEMPT" in os.environ else None
pytestmark = pytest.mark.skipif(ATTEMPT is None, reason="requires bounded529")
BASELINE = Path(__file__).resolve().parents[1] / (
    "verification/tool_graders_hmmer_map_verification_2026-10-28_529/"
    "check181b_restriction717/native-restriction-probe/native-probe.json")


def binding(sequence):
    return {"version": "restriction_selected_sequence_v1", "namespace": "subject",
        "sequence_ref": "subject_supplied718", "source_ref": "source_supplied718", "sequence_version": 1,
        "content_sha256": hashlib.sha256(sequence.encode()).hexdigest(), "length_nt": len(sequence),
        "origin_mapping_ref": None}


def store_json(path, value):
    with path.open("x") as f:
        json.dump(value, f, sort_keys=True, allow_nan=False)
        f.write("\n")


@pytest.fixture(scope="module")
def retained_native():
    from Bio import Restriction as R
    from Bio.Restriction import Restriction as impl
    old = json.loads(BASELINE.read_bytes())
    destination = ATTEMPT / "restriction-native718"
    destination.mkdir(exist_ok=False)
    parameters = [(r["case_name"], r["selected_sequence"]["sequence"], r["topology"],
        {"kind": r["population_kind"], "names": r["requested_enzyme_names"]}) for r in old["cases"]]
    # Literal selected contexts, not an implicit discovery or follow-up loop.
    motif = R.BcgI.site.replace("N", "A")
    parameters += [
        ("nocut_snai", "AAAAGTATACTTTT", "linear", {"kind": "explicit", "names": ["SnaI"]}),
        ("reverse_bsai", "A" * 30 + "GAGACC" + "A" * 30, "linear", {"kind": "explicit", "names": ["BsaI"]}),
        ("ambiguous_query", "AAAAGNATTCTTTT", "linear", {"kind": "explicit", "names": ["EcoRI"]}),
        ("duplicate_bcgi", "A" * 50 + motif + "A" * 22 + motif + "A" * 50, "linear", {"kind": "explicit", "names": ["BcgI"]}),
        ("short_circle_bcgi", motif, "circular", {"kind": "explicit", "names": ["BcgI"]}),
        ("empty_explicit", "AAAAGAATTCTTTT", "linear", {"kind": "explicit", "names": []}),
    ]
    result, errors, counters = {}, {}, {"batch_search_calls": 0, "original_finditer_calls": 0}
    active = [None]
    original_validate = producer.validate_restriction_record
    original_batch = impl.RestrictionBatch.search
    original_finditer = impl.FormattedSeq.finditer

    def retain_then_validate(kind, value):
        if kind == "NativeResult":
            store_json(destination / (active[0] + ".json"), value)
        return original_validate(kind, value)

    def count_batch(self, dna, linear=True):
        counters["batch_search_calls"] += 1
        return original_batch(self, dna, linear=linear)

    def count_finditer(self, pattern, size):
        counters["original_finditer_calls"] += 1
        return original_finditer(self, pattern, size)

    def invoke(name, sequence, topology, selection):
        active[0] = name
        try:
            result[name] = producer.run_restriction_mapping(sequence, sequence_binding=binding(sequence),
                enzyme_selection=selection, topology=topology)
        except Exception as error:
            errors[name] = {"class": type(error).__name__, "message": str(error)}

    patch = pytest.MonkeyPatch()
    try:
        patch.setattr(producer, "validate_restriction_record", retain_then_validate)
        patch.setattr(impl.RestrictionBatch, "search", count_batch)
        patch.setattr(impl.FormattedSeq, "finditer", count_finditer)
        for name, sequence, topology, selection in parameters:
            invoke(name, sequence, topology, selection)
        # Engineering fault: first native enzyme returns, second is interrupted.
        fault_count = [0]
        with pytest.MonkeyPatch.context() as faults:
            for enzyme in (R.EcoRI, R.BamHI, R.HindIII):
                original = enzyme.search

                def fault(cls, dna, linear=True, _original=original):
                    fault_count[0] += 1
                    if fault_count[0] == 2:
                        raise RuntimeError("labelled_engineering_second_enzyme_fault")
                    return _original(dna, linear=linear)

                faults.setattr(enzyme, "search", classmethod(fault))
            invoke("engineering_partial_search", "AAAAGAATTCTTTT", "linear",
                {"kind": "explicit", "names": ["EcoRI", "BamHI", "HindIII"]})
        # Engineering observer failure must preserve the native returned cuts.
        with pytest.MonkeyPatch.context() as faults:
            def fail_capture(_):
                raise RuntimeError("labelled_engineering_match_capture_fault")
            faults.setattr(producer, "_match_rows", fail_capture)
            invoke("engineering_observer_failure", "AAAAGAATTCTTTT", "linear", {"kind": "explicit", "names": ["EcoRI"]})
    finally:
        patch.undo()
    store_json(destination / "MANIFEST.json", {"selected_cases": parameters,
        "engineering_faults": ["engineering_partial_search", "engineering_observer_failure"],
        "counts": counters, "errors": errors, "original717_repeated_as_baseline": False})
    return {"results": result, "errors": errors, "counts": counters, "baseline": old,
        "directory": str(destination)}


def row(result, name):
    return next(r for r in result["enzyme_searches"] if r["name"] == name)


def test_all_selected_native_records_retained_and_valid(retained_native):
    assert retained_native["errors"] == {}, retained_native["errors"]
    assert retained_native["counts"]["batch_search_calls"] == 13
    for result in retained_native["results"].values():
        assert validate_restriction_record("NativeResult", result) == result
        for call in result["match_observations"]:
            assert len(call["owner_ordinals"]) == 1
    complete_calls = sum(len(r["match_observations"]) for r in retained_native["results"].values())
    assert retained_native["counts"]["original_finditer_calls"] == complete_calls


def test_observing_source_agrees_with_retained717_without_new_baseline(retained_native):
    for original in retained_native["baseline"]["cases"]:
        current = retained_native["results"][original["case_name"]]
        assert current["batch_state"] == "returned"
        wanted = {r["enzyme_name"]: r["native_cut_positions_1based"] for r in original["result"]["rows"]}
        actual = {r["name"]: r["native_search_positions_1based"] for r in current["enzyme_searches"]}
        assert actual == wanted
        assert len(current["match_observations"]) == len(wanted)
        if original["population_kind"] == "commercial_native_batch":
            assert len(current["catalog"]["enzymes"]) == 623
            assert sum(not r["native_search_positions_1based"] for r in current["enzyme_searches"]) == 616


def test_source_observed_matches_keep_native_coordinates_and_geometry(retained_native):
    values = retained_native["results"]
    for name, position, start in [("ecori_linear_internal", [6], 5), ("ecori_circular_origin", [1], 10)]:
        value = values[name]
        assert row(value, "EcoRI")["native_search_positions_1based"] == position
        assert value["match_observations"][0]["matches"][0]["native_start_1based"] == start
    snai = values["nocut_snai"]
    assert row(snai, "SnaI")["native_search_positions_1based"] == [5]
    assert snai["catalog"]["enzymes"][0]["position_meaning"] == "recognition_start_1based"
    reverse = values["reverse_bsai"]
    assert row(reverse, "BsaI")["native_search_positions_1based"] == [26]
    assert row(reverse, "BsaI")["native_on_minus_before_drop"] == [26]
    groups = {g["name"]: g["text"] for g in reverse["match_observations"][0]["matches"][0]["groups"]}
    assert groups["BsaI"] is None and any(v == "GAGACC" for v in groups.values())
    two = values["duplicate_bcgi"]
    assert row(two, "BcgI")["native_search_positions_1based"] == [41, 75, 75, 109]
    assert len(two["match_observations"][0]["matches"]) == 2
    assert row(values["short_circle_bcgi"], "BcgI")["native_search_positions_1based"] == [3, 13]
    assert values["short_circle_bcgi"]["request"]["sequence_binding"]["length_nt"] == 12
    assert values["ambiguous_query"]["request"]["sequence"] == "AAAAGNATTCTTTT"
    assert values["empty_explicit"]["batch_state"] == "returned"
    assert values["empty_explicit"]["enzyme_searches"] == []


def test_engineering_faults_preserve_completed_native_work(retained_native):
    partial = retained_native["results"]["engineering_partial_search"]
    assert partial["batch_state"] == "failed"
    assert sorted(r["state"] for r in partial["enzyme_searches"]) == ["failed", "not_started", "returned"]
    completed = next(r for r in partial["enzyme_searches"] if r["state"] == "returned")
    assert completed["native_search_positions_1based"] is not None
    assert all(r["native_search_positions_1based"] is None for r in partial["enzyme_searches"] if r["state"] != "returned")
    observer = retained_native["results"]["engineering_observer_failure"]
    assert observer["batch_state"] == "returned"
    assert row(observer, "EcoRI")["native_search_positions_1based"] == [6]
    assert observer["match_observations"][0]["state"] == "failed"
    assert observer["match_observations"][0]["matches"] is None


def test_original_native_descriptors_not_left_wrapped(retained_native):
    from Bio import Restriction as R
    for enzyme in (R.EcoRI, R.BamHI, R.HindIII, R.SnaI, R.BcgI, R.BsaI):
        assert "search" not in enzyme.__dict__
        assert "ObservedSequence" not in type(getattr(enzyme, "dna", None)).__name__


def test_invalid_inputs_never_search_or_synthesize_empty_results(monkeypatch):
    from Bio.Restriction import Restriction as impl
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid input searched")
    monkeypatch.setattr(impl.RestrictionBatch, "search", forbidden)
    for sequence, selection in [("AAAAGAATTCTTTT", {"kind": "explicit", "names": ["unknown718"]}),
            ("ACG T", {"kind": "explicit", "names": ["EcoRI"]})]:
        value = producer.run_restriction_mapping(sequence, sequence_binding=binding(sequence),
            enzyme_selection=selection, topology="linear")
        assert value["batch_state"] == "not_started" and value["issues"]
        assert value["catalog"] is None and value["enzyme_searches"] == []
    selected = binding("ACGT")
    selected["content_sha256"] = "0" * 64
    value = producer.run_restriction_mapping("ACGT", sequence_binding=selected,
        enzyme_selection={"kind": "explicit", "names": ["EcoRI"]}, topology="linear")
    assert value["issues"][0]["code"] == "sequence_binding_conflict"


def test_closed_contract_detaches_and_rejects_wrong_scalar_types(retained_native):
    value = retained_native["results"]["ecori_linear_internal"]
    checked = validate_restriction_record("NativeResult", value)
    checked["enzyme_searches"][0]["native_search_positions_1based"].append(2)
    assert row(value, "EcoRI")["native_search_positions_1based"] == [6]
    for field, wrong in [("length_nt", True), ("length_nt", 14.0), ("sequence_version", False)]:
        selected = binding("AAAAGAATTCTTTT");selected[field] = wrong
        with pytest.raises(ValueError):validate_restriction_record("SequenceBinding", selected)
    catalog = deepcopy(value["catalog"]["enzymes"][0]);catalog["native_pattern"]["flags"] = 0
    with pytest.raises(ValueError):validate_restriction_record("CatalogRow", catalog)
    catalog = deepcopy(value["catalog"]);catalog["dictionary_file"]["path"] = "relative/file"
    with pytest.raises(ValueError):validate_restriction_record("Catalog", catalog)
    schema = restriction_schema("NativeResult");schema["properties"].clear()
    assert restriction_schema("NativeResult")["properties"]
    cyclic = [];cyclic.append(cyclic)
    with pytest.raises(ValueError):restriction_canonical(cyclic)
