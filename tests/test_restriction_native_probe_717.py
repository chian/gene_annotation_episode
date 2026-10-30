"""The five selected native calls run once; every assertion reads their result."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest


ATTEMPT = Path(os.environ["HMMER529_ATTEMPT"]) if "HMMER529_ATTEMPT" in os.environ else None
pytestmark = pytest.mark.skipif(ATTEMPT is None, reason="native probe requires bounded529")
PACKET = "verification/tool_graders_restriction_native_probe_2026-10-29_717"


@pytest.fixture(scope="module")
def native_probe():
    helper_path = ATTEMPT / "source_snapshot" / PACKET / "probe.py"
    spec = importlib.util.spec_from_file_location("restriction_probe717", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    result = helper.run_probe(ATTEMPT / "native-restriction-probe")
    assert result["batch_search_call_count"] == 5
    assert result["additional_finditer_call_count"] == 0
    assert all(case["exception"] is None for case in result["cases"])
    return result


def _rows(case):
    return {row["enzyme_name"]: row for row in case["result"]["rows"]}


def test_exact_native_call_and_input_populations(native_probe):
    assert len(native_probe["cases"]) == 5
    for ordinal, case in enumerate(native_probe["cases"]):
        sequence = case["selected_sequence"]
        assert case["case_ordinal"] == ordinal
        assert hashlib.sha256(sequence["sequence"].encode()).hexdigest() == sequence["sha256"]
        assert len(sequence["sequence"]) == sequence["length_nt"] == sequence["size_bytes"]
        assert case["native_batch_already_mapped_before"] is None
        assert set(_rows(case)) == set(case["resolved_enzyme_names"])
        assert case["result"]["native_mapping_order"] == case["native_batch_member_order"]
    assert native_probe["biopython_version"] == "1.88"
    assert native_probe["new_matching_implementation"] is False


def test_linear_ecori_after_cut_position_is_not_motif_start(native_probe):
    case = native_probe["cases"][0]
    assert case["selected_sequence"]["sequence"] == "AAAAGAATTCTTTT"
    assert case["topology"] == "linear"
    assert _rows(case)["EcoRI"]["native_cut_positions_1based"] == [6]
    enzyme, = case["catalog"]
    assert enzyme["native_attributes"]["site"] == "GAATTC"
    assert enzyme["native_attributes"]["fst5"] == 1
    assert enzyme["native_attributes"]["fst3"] == -1
    assert enzyme["native_attributes"]["ovhg"] == -4
    assert enzyme["cut_diagram"] == "G^AATT_C"
    assert enzyme["cut_diagram"] != enzyme["native_attributes"]["site"]


def test_same_origin_sequence_has_distinct_linear_and_circular_results(native_probe):
    linear, circular = native_probe["cases"][1:3]
    assert linear["selected_sequence"] == circular["selected_sequence"]
    assert _rows(linear)["EcoRI"]["native_cut_positions_1based"] == []
    assert _rows(circular)["EcoRI"]["native_cut_positions_1based"] == [1]
    assert linear["linear_argument"] is True and circular["linear_argument"] is False


def test_bcgi_retains_two_native_cuts_and_unimplemented_diagram(native_probe):
    case = native_probe["cases"][3]
    enzyme, = case["catalog"]
    attributes = enzyme["native_attributes"]
    assert attributes["site"] == "CGANNNNNNTGC"
    assert case["selected_sequence"]["sequence"] == "A" * 50 + "CGA" + "A" * 6 + "TGC" + "A" * 50
    assert "TwoCuts" in enzyme["native_class_mro"]
    assert [attributes[k] for k in ("fst5", "fst3", "scd5", "scd3", "ovhg")] == [-10, -24, 24, 10, 2]
    assert _rows(case)["BcgI"]["native_cut_positions_1based"] == [41, 75]
    assert _rows(case)["BcgI"]["native_on_minus_before_drop"] == []
    assert enzyme["cut_diagram_failure"] is None
    assert enzyme["cut_diagram"] == "cut twice, not yet implemented sorry."


def test_commercial_population_retains_native_negative_rows_and_catalog(native_probe):
    case = native_probe["cases"][4]
    rows = _rows(case)
    assert case["population_kind"] == "commercial_native_batch"
    assert len(rows) == len(case["resolved_enzyme_names"]) == len(case["catalog"])
    assert rows["EcoRI"]["native_cut_positions_1based"] == [6]
    assert rows["BamHI"]["native_cut_positions_1based"] == []
    assert any(row["native_cut_positions_1based"] for row in rows.values())
    assert any(not row["native_cut_positions_1based"] for row in rows.values())
    for enzyme in case["catalog"]:
        assert enzyme["native_attributes"]["suppl"]["native_type"] == "tuple"
        assert enzyme["native_attributes"]["suppl"]["items"]
        assert {"site", "fst5", "fst3", "scd5", "scd3", "ovhg"} <= set(enzyme["native_attributes"])
    descriptor = native_probe["dictionary_file"]
    raw = Path(descriptor["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == descriptor["sha256"]
    assert len(raw) == descriptor["size_bytes"]
    assert json.loads((ATTEMPT / "native-restriction-probe/native-probe.json").read_text()) == native_probe
