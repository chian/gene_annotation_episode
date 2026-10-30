"""Independent native-format verification; execute only with bounded529.

Writer inputs are synthetic, upstream fixtures are unmodified original files,
and deliberately changed files are separately retained as handcrafted mutations.
None of these fixtures establishes an acquired molecular assay or deployment.
"""

import ast
import builtins
from copy import deepcopy
import inspect
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request

import pytest

from fluorescence_flowio_test_support import (
    SOURCE_RELATIVE, acquire_upstream_fixture, artifact_root, file_identity,
    mutate_writer, mutation_fixture, require_bounded_runtime, retain_bytes,
    save_json, source_flowio, upstream_source_path, writer_fixture,
)

# This executes before importing any application or scientific module. A host
# pytest invocation fails collection rather than running unbounded or skipping.
require_bounded_runtime()

from gene_annotation_episode import fluorescence_event_calculations as calculations
from gene_annotation_episode import fluorescence_fcs_reader as reader
from gene_annotation_episode.fluorescence_event_contracts import (
    FluorescenceContractError, canonical, validate_event_parse_result,
)
from gene_annotation_episode.fluorescence_event_readers import (
    parse_fluorescence_csv, parse_fluorescence_table_snapshot,
)
from gene_annotation_episode.fluorescence_event_sheet import populate_fluorescence_sheet
from gene_annotation_episode.fluorescence_result_views import project_fluorescence_result


PACKET548_VALUES = [90, 100, 125, 150, 200, 250, 300, 350]


@pytest.fixture
def flowio():
    with source_flowio() as module:
        yield module


def _request(raw, names, *, dataset=0, origin="supplied_predicted", fixture_kind="synthetic writer"):
    source = dict(key="source", file=file_identity(raw), dataset_position=dataset,
                  format_profile="fcs_flowio_1_4_0_encoded", extent="unavailable",
                  native_event_count=919,
                  metadata=[dict(name="fixture_origin", value=fixture_kind),
                            dict(name="supplied_duplicate", value="first"),
                            dict(name="supplied_duplicate", value="second")])
    sample = dict(key="sample", primary_domain_key="encoded", label="verification sample",
                  condition=None, biological_replicate=None, technical_replicate=None,
                  associations=[])
    preparation = dict(state="not_applied", method=None, parameters_file=None)
    domain = dict(key="encoded", sample_key="sample", source_key="source",
                  parent_domain_key=None, state="available", scale_kind="encoded",
                  compensation=deepcopy(preparation), transformation=deepcopy(preparation),
                  correspondence=None, comparison_basis=None)
    channels = [dict(key=f"channel_{i}", ordinal=i, native_name=name, label=None,
                     unit="arbitrary_instrument_units", analyte=None, measurement_origin=origin)
                for i, name in enumerate(names)]
    return dict(source=source, sample=sample, channels=channels, domain=domain)


def _parse(raw, names, **kwargs):
    request = _request(raw, names, **kwargs)
    before = deepcopy(request)
    result = reader.parse_fluorescence_fcs(raw, **request)
    assert request == before
    assert validate_event_parse_result(result) is result
    return result


def _values(batch, position=0):
    return [row["values"][position]["measurement"]["value"] for row in batch["events"]]


def _metadata(batch):
    return {item["name"]: item["value"] for item in batch["source"]["metadata"]}


def _codes(batch):
    return {item["code"] for item in batch["issues"]}


def _sheet(batch, *, channel=0, lower=100, upper=250, pass_all=False):
    gate = dict(key="selected", sample_key="sample",
                parent=dict(kind="population", key="all"),
                kind="pass_all" if pass_all else "threshold",
                domain_key=None if pass_all else "encoded",
                channel_key=None if pass_all else f"channel_{channel}",
                lower=None if pass_all or lower is None else dict(value=lower, inclusive=True),
                upper=None if pass_all or upper is None else dict(value=upper, inclusive=True))
    return populate_fluorescence_sheet([batch],
        populations=[dict(key="all", sample_key="sample", kind="all", event_ordinals=None)],
        gates=[gate], control_pairs=[], native_reports=[])


def _parameters(channel=0):
    return dict(fraction_requests=[dict(gate_key="selected", denominator="parent")],
                intensity_requests=[dict(gate_key="selected", domain_key="encoded",
                                         channel_key=f"channel_{channel}")],
                control_requests=[], native_comparison_requests=[])


def _cell(components, metric):
    rows = [cell for cell in components["cells"] if cell["request"]["metric"] == metric]
    assert len(rows) == 1
    return rows[0]


def _packet_fixture(flowio, name="writer/packet548.fcs"):
    return writer_fixture(flowio, name, PACKET548_VALUES, ["signal"])


def _forbidden(*args, **kwargs):
    raise AssertionError("unexpected preprocessing, reacquisition or recalculation")


def test_native_writer_packet548_uses_exact_common_sheet_calculator_and_projection(flowio):
    raw = _packet_fixture(flowio)
    fcs = _parse(raw, ["signal"])
    csv = b"signal\r\n90\r\n100\r\n125\r\n150\r\n200\r\n250\r\n300\r\n350\r\n"
    snapshot = canonical({"schema": "fluorescence_event_table_v1", "columns": ["signal"],
                          "rows": [[value] for value in PACKET548_VALUES]})
    retain_bytes("supplied/packet548.csv", csv, kind="synthetic_supplied_csv",
                 details={"measurement_origin": "supplied_predicted"})
    retain_bytes("supplied/packet548.json", snapshot, kind="synthetic_supplied_table",
                 details={"measurement_origin": "supplied_predicted"})
    csv_request = _request(csv, ["signal"])
    csv_request["source"]["file"] = file_identity(csv, "csv")
    csv_request["source"]["format_profile"] = "explicit_synthetic_csv"
    table_request = _request(snapshot, ["signal"])
    table_request["source"]["file"] = file_identity(snapshot, "json")
    table_request["source"]["format_profile"] = "explicit_synthetic_snapshot"
    batches = [fcs, parse_fluorescence_csv(csv, **csv_request, format_spec=dict(
        encoding="utf-8", delimiter=",", quotechar='"', escapechar=None,
        doublequote=True, header=True, missing_tokens=[])),
        parse_fluorescence_table_snapshot(snapshot, **table_request)]
    sheets = [_sheet(batch) for batch in batches]
    parameters = _parameters()
    calculated = [calculations.calculate_fluorescence_sheet(sheet, parameters=parameters)
                  for sheet in sheets]
    assert calculated[0]["cells"] == calculated[1]["cells"] == calculated[2]["cells"]
    assert calculated[0]["memberships"] == calculated[1]["memberships"] == calculated[2]["memberships"]
    expected = {"selected_event_count": 5, "parent_event_count": 8,
                "selected_fraction": .625, "selected_percent": 62.5,
                "selected_intensity_sum": 825, "selected_intensity_mean": 165,
                "selected_intensity_median": 150}
    for metric, value in expected.items():
        assert _cell(calculated[0], metric)["value"] == value
        assert _cell(calculated[0], metric)["state"] == "present"
    assert fcs["source"]["native_event_count"] == 8
    assert batches[1]["source"]["native_event_count"] is None
    assert batches[2]["source"]["native_event_count"] is None
    assert fcs["source"]["file"] == file_identity(raw)
    assert fcs["source"]["extent"] == "complete"
    assert calculated[0]["memberships"][0]["selected"] == [1, 2, 3, 4, 5]
    selection = dict(requests=[_cell(calculated[0], metric)["request"] for metric in expected],
                     offset=0, limit=20)
    projected = project_fluorescence_result(sheets[0], calculated[0], selection=selection)
    assert projected["rows"] == [_cell(calculated[0], metric) for metric in expected]
    for name, value in (("packet548_fcs_parse.json", fcs), ("packet548_fcs_sheet.json", sheets[0]),
                        ("packet548_parameters.json", parameters),
                        ("packet548_components.json", calculated[0]),
                        ("packet548_projection.json", projected)):
        save_json(name, value)


def test_native_writer_metadata_ordinals_and_encoded_values_never_preprocess(flowio, monkeypatch):
    raw = writer_fixture(flowio, "writer/gain_and_time.fcs", [90, 10, 200, 20],
                         ["signal", "Time"], labels=["supplied signal", "clock label"],
                         metadata={"p1g": "2", "p2g": "7", "timestep": "0.08",
                                   "custom_tag": "synthetic gain metadata"})
    monkeypatch.setattr(flowio.FlowData, "as_array", _forbidden)
    monkeypatch.setattr(flowio.FlowData, "write_fcs", _forbidden)
    result = _parse(raw, [None, None])
    assert _values(result) == [90, 200]
    assert _values(result, 1) == [10, 20]
    assert all(type(value) is float for value in _values(result))
    assert result["source"]["metadata"][:3] == _request(raw, [None, None])["source"]["metadata"]
    native = _metadata(result)
    assert native["flowio.header.version"] == "3.1"
    assert native["flowio.text.datatype"] == "F"
    assert native["flowio.text.p1g"] == "2"
    assert native["flowio.text.p2g"] == "7"
    assert native["flowio.text.timestep"] == "0.08"
    assert native["flowio.text.custom_tag"] == "synthetic gain metadata"
    assert [channel["native_name"] for channel in result["channels"]] == ["signal", "Time"]
    assert [channel["label"] for channel in result["channels"]] == ["supplied signal", "clock label"]
    for ordinal, event in enumerate(result["events"]):
        assert event["event_ordinal"] == event["source_ordinal"] == ordinal
        assert event["location"] == dict(record_ordinal=ordinal, line_start=None,
                                         line_end=None, byte_start=None, byte_end=None)
        assert all(cell["measurement"]["raw"] is None and
                   cell["measurement"]["state"] == "supplied_predicted" for cell in event["values"])
    assert all(channel["analyte"] is None for channel in result["channels"])
    assert result["domain"]["compensation"]["state"] == "not_applied"
    assert result["domain"]["transformation"]["state"] == "not_applied"


def test_writer_duplicate_names_remain_distinct_positional_channels(flowio):
    raw = writer_fixture(flowio, "writer/duplicate_names.fcs", [7, 11, 7, 19],
                         ["duplicate", "duplicate"], labels=["left", "right"])
    result = _parse(raw, [None, None])
    assert [channel["native_name"] for channel in result["channels"]] == ["duplicate", "duplicate"]
    assert [channel["key"] for channel in result["channels"]] == ["channel_0", "channel_1"]
    assert _values(result) == [7, 7]
    assert _values(result, 1) == [11, 19]
    assert [event["event_ordinal"] for event in result["events"]] == [0, 1]


def test_writer_positional_mismatch_and_unbound_native_column(flowio):
    raw = writer_fixture(flowio, "writer/two_channels.fcs", [1, 2, 3, 4], ["a", "b"])
    result = _parse(raw, ["b", "a"])
    assert result["events"] == []
    assert "native_format_mismatch" in _codes(result)
    with pytest.raises(FluorescenceContractError) as error:
        _parse(raw, ["a"])
    assert error.value.code == "invalid_channel"
    extra = _parse(raw, ["a", "b", "absent"])
    assert _values(extra) == [1, 3]
    assert _values(extra, 1) == [2, 4]
    assert _values(extra, 2) == [None, None]
    assert all(event["values"][2]["measurement"]["state"] == "unavailable"
               for event in extra["events"])
    assert "channel_missing" in _codes(extra)


def test_writer_nonfinite_values_remain_located_without_row_loss(flowio):
    raw = writer_fixture(flowio, "writer/nonfinite.fcs", [0, float("nan"), float("inf"),
                         -float("inf"), 5], ["signal"])
    result = _parse(raw, ["signal"])
    assert _values(result) == [0, None, None, None, 5]
    assert result["source"]["native_event_count"] == 5
    assert [event["event_ordinal"] for event in result["events"]] == [0, 1, 2, 3, 4]
    assert {entry["event_ordinal"] for entry in result["issues"]
            if entry["code"] == "invalid_numeric_token"} == {1, 2, 3}
    for ordinal in (1, 2, 3):
        assert result["events"][ordinal]["values"][0]["measurement"] == dict(
            value=None, state="invalid", raw=None)


def test_writer_complete_empty_dataset_is_a_known_zero_population(flowio):
    raw = writer_fixture(flowio, "writer/empty.fcs", [], ["signal"])
    result = _parse(raw, ["signal"])
    assert result["events"] == []
    assert result["source"]["extent"] == "complete"
    assert result["source"]["native_event_count"] == 0
    components = calculations.calculate_fluorescence_sheet(_sheet(result), parameters=_parameters())
    assert _cell(components, "retained_event_count")["value"] == 0
    assert _cell(components, "retained_event_count")["state"] == "present"
    assert _cell(components, "selected_fraction")["value"] is None


def test_writer_mutation_reported_tot_conflict_preserves_both_quantities(flowio):
    original = _packet_fixture(flowio)
    raw = mutation_fixture("mutated/tot9.fcs", mutate_writer(original, text_updates={"$TOT": "9"}),
                           [original], ["change native TOT from 8 to 9; retain all eight DATA values"])
    result = _parse(raw, ["signal"], fixture_kind="handcrafted TOT mutation of native writer")
    assert result["source"]["native_event_count"] == 9
    assert len(result["events"]) == 8
    assert result["source"]["extent"] == "partial"
    assert "native_count_conflict" in _codes(result)
    assert _metadata(result)["flowio.text.tot"] == "9"
    components = calculations.calculate_fluorescence_sheet(_sheet(result), parameters=_parameters())
    assert _cell(components, "retained_event_count")["value"] == 8
    assert _cell(components, "retained_event_count")["state"] == "qualified"
    assert _cell(components, "selected_fraction")["value"] is None
    save_json("count_conflict_parse.json", result)
    save_json("count_conflict_components.json", components)


def test_writer_mutation_trailing_partial_row_preserves_available_cells(flowio):
    original = writer_fixture(flowio, "writer/complete_two_rows.fcs", [100, 10, 200, 20], ["a", "b"])
    start, stop = int(original[26:34]), int(original[34:42])
    raw = mutation_fixture("mutated/partial_row.fcs",
        mutate_writer(original, data=original[start:stop + 1][:-4]), [original],
        ["remove final float; update DATA end offsets; retain native TOT=2 and PAR=2"])
    result = _parse(raw, ["a", "b"], fixture_kind="handcrafted trailing-cell mutation")
    assert _values(result) == [100, 200]
    assert _values(result, 1) == [10, None]
    assert result["source"]["native_event_count"] == 2
    assert result["source"]["extent"] == "partial"
    assert {"invalid_event_row", "truncated_source"} <= _codes(result)
    assert result["events"][1]["values"][1]["measurement"]["state"] == "unavailable"
    assert [event["event_ordinal"] for event in result["events"]] == [0, 1]


def test_absent_optional_scaling_metadata_does_not_become_observed_defaults(flowio, monkeypatch):
    original = _packet_fixture(flowio)
    raw = mutation_fixture("mutated/absent_pne_png.fcs",
        mutate_writer(original, text_updates={"$P1E": None, "$P1G": None}), [original],
        ["remove P1E and P1G without changing encoded DATA"])
    monkeypatch.setattr(flowio.FlowData, "as_array", _forbidden)
    result = _parse(raw, [None], fixture_kind="handcrafted missing-metadata fixture")
    assert _values(result) == PACKET548_VALUES
    assert result["source"]["extent"] == "complete"
    assert "flowio.text.p1e" not in _metadata(result)
    assert "flowio.text.p1g" not in _metadata(result)
    assert "flowio.text.p1s" not in _metadata(result)
    assert result["channels"][0]["label"] is None


def test_unmodified_official_variable_integer_fixture_matches_upstream_literal_vector(flowio, monkeypatch):
    raw, receipt = acquire_upstream_fixture("variable_int_example.fcs")
    # Read the literal in the pinned upstream test; do not execute that test or
    # derive expected values by calling this parser/decoder a second time.
    tree = ast.parse(upstream_source_path("tests/test_flowdata.py").read_text())
    method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                  and node.name == "test_parse_var_int_data")
    assignment = next(node for node in method.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == "event_values"
                              for target in node.targets))
    expected = ast.literal_eval(assignment.value)
    assert len(expected) == 52
    monkeypatch.setattr(flowio.FlowData, "as_array", _forbidden)
    result = _parse(raw, [None] * 26, fixture_kind="unmodified official upstream test fixture")
    assert result["source"]["extent"] == "complete"
    assert result["source"]["native_event_count"] == 2
    assert len(result["channels"]) == 26
    actual = [cell["measurement"]["value"] for event in result["events"] for cell in event["values"]]
    assert actual == expected
    assert all(type(value) is int for value in actual)
    assert _values(result, 25) == [8265081, 15691602]
    metadata = _metadata(result)
    assert metadata["flowio.text.datatype"] == "I"
    assert metadata["flowio.text.p26b"] == "32"
    assert metadata["flowio.text.p26r"] == "11209599"
    assert metadata["flowio.text.par"] == "26"
    assert result["source"]["file"]["sha256"] == receipt["sha256"]
    sheet = _sheet(result, channel=25, lower=8_000_000, upper=9_000_000)
    components = calculations.calculate_fluorescence_sheet(sheet, parameters=_parameters(25))
    assert components["memberships"][0]["selected"] == [0]
    assert _cell(components, "selected_fraction")["value"] == .5
    assert _cell(components, "selected_intensity_sum")["value"] == 8265081
    assert _cell(components, "selected_intensity_mean")["value"] == 8265081
    assert _cell(components, "selected_intensity_median")["value"] == 8265081
    for name, value in (("upstream_integer_parse.json", result), ("upstream_integer_sheet.json", sheet),
                        ("upstream_integer_components.json", components),
                        ("upstream_integer_expected.json", expected)):
        save_json(name, value)
    # A second acquisition reads retained bytes. No second network request is
    # permitted, and original provenance remains unchanged.
    monkeypatch.setattr(urllib.request, "urlopen", _forbidden)
    retained, repeated_receipt = acquire_upstream_fixture("variable_int_example.fcs")
    assert retained == raw and repeated_receipt == receipt


@pytest.mark.parametrize("name", ["data_start_offset_discrepancy_example.fcs",
                                  "data_stop_offset_discrepancy_example.fcs"])
def test_unmodified_official_offset_discrepancies_are_strict_failures(flowio, name):
    raw, receipt = acquire_upstream_fixture(name)
    # These expected exceptions are independently specified by upstream's pinned
    # test_data_start_offset_discrepancy / test_data_stop_offset_discrepancy.
    with pytest.raises(flowio.exceptions.DataOffsetDiscrepancyError):
        flowio.FlowData(io.BytesIO(raw), nextdata_offset=0)
    result = _parse(raw, [None] * 26, fixture_kind="unmodified official strict-offset fixture")
    assert result["events"] == []
    assert result["source"]["extent"] == "unavailable"
    assert "native_format_mismatch" in _codes(result)
    assert result["source"]["file"]["sha256"] == receipt["sha256"]
    save_json(name + ".parse.json", result)


def _multidataset_fixture(flowio):
    first = writer_fixture(flowio, "writer/dataset0.fcs", [17, 23], ["unselected"])
    second = _packet_fixture(flowio, "writer/dataset1.fcs")
    prepared = mutate_writer(first, text_updates={"$NEXTDATA": "0000000000"})
    prepared = mutate_writer(prepared, text_updates={"$NEXTDATA": str(len(prepared)).zfill(10)})
    raw = mutation_fixture("mutated/two_datasets.fcs", prepared + second, [first, second],
        ["replace first NEXTDATA with its relative dataset length using fixed-width decimal",
         "concatenate the two writer outputs; second dataset offsets remain relative"])
    return raw, len(prepared)


def test_selected_dataset_uses_relative_link_and_decodes_only_selected_data(flowio, monkeypatch):
    raw, offset = _multidataset_fixture(flowio)
    calls = []
    original_init = flowio.FlowData.__init__
    original_decode = flowio.FlowData._FlowData__parse_data

    def track_init(self, *args, **kwargs):
        calls.append(dict(kwargs))
        assert "nextdata_offset" in kwargs
        assert kwargs.get("ignore_offset_error", False) is False
        assert kwargs.get("ignore_offset_discrepancy", False) is False
        assert kwargs.get("use_header_offsets", False) is False
        return original_init(self, *args, **kwargs)

    def track_decode(self, selected_offset, *args, **kwargs):
        assert selected_offset == offset, "unselected event DATA was decoded"
        return original_decode(self, selected_offset, *args, **kwargs)

    monkeypatch.setattr(flowio.FlowData, "__init__", track_init)
    monkeypatch.setattr(flowio.FlowData, "_FlowData__parse_data", track_decode)
    monkeypatch.setattr(flowio.FlowData, "as_array", _forbidden)
    result = _parse(raw, ["signal"], dataset=1, fixture_kind="handcrafted writer-derived multidataset")
    assert _values(result) == PACKET548_VALUES
    assert result["source"]["dataset_position"] == 1
    assert result["source"]["native_event_count"] == 8
    assert result["source"]["file"] == file_identity(raw)
    assert _metadata(result)["flowio.text.p1n"] == "signal"
    assert any(call["nextdata_offset"] == 0 and call.get("only_text") for call in calls)
    assert any(call["nextdata_offset"] == offset and not call.get("only_text", False) for call in calls)
    save_json("selected_dataset_parse.json", result)
    save_json("selected_dataset_decoder_calls.json", calls)


def test_requested_missing_dataset_is_unavailable_without_synthesizing_events(flowio):
    raw, _ = _multidataset_fixture(flowio)
    result = _parse(raw, [None], dataset=2, fixture_kind="handcrafted writer-derived multidataset")
    assert result["events"] == []
    assert result["source"]["dataset_position"] == 2
    assert result["source"]["extent"] == "unavailable"
    assert "source_unavailable" in _codes(result)


def test_selected_dataset_data_cannot_cross_next_dataset_boundary(flowio):
    original = _packet_fixture(flowio)
    prepared = mutate_writer(original, text_updates={"$NEXTDATA": "0000000000"})
    prepared = mutate_writer(prepared, text_updates={"$NEXTDATA": str(len(prepared) - 1).zfill(10)})
    raw = mutation_fixture("mutated/data_crosses_next_boundary.fcs", prepared + original,
        [original], ["NEXTDATA points into the selected DATA's final byte"])
    result = _parse(raw, ["signal"], fixture_kind="handcrafted invalid dataset boundary")
    assert result["events"] == []
    assert result["source"]["extent"] == "unavailable"
    assert _codes(result) & {"native_format_mismatch", "truncated_source"}


_ANALYSIS_PAYLOAD = b"/$ANALYSISTOKEN/17/$NOTE/retained fixture metadata/"


def _set_analysis_offsets(prepared, start, stop, *, next_offset=None):
    """Edit known writer fields; this does not decode an ANALYSIS segment."""
    updates = {"$BEGINANALYSIS": str(start).zfill(10),
               "$ENDANALYSIS": str(stop).zfill(10)}
    if next_offset is not None:
        updates["$NEXTDATA"] = str(next_offset).zfill(10)
    changed = bytearray(mutate_writer(prepared, text_updates=updates))
    changed[42:50] = f"{start:>8}".encode("ascii")
    changed[50:58] = f"{stop:>8}".encode("ascii")
    assert len(changed) == len(prepared)
    return bytes(changed)


def _appended_analysis(original, *, end_extra=0):
    prepared = mutate_writer(original, text_updates={"$BEGINANALYSIS": "0000000000",
                                                     "$ENDANALYSIS": "0000000000"})
    start = len(prepared)
    stop = start + len(_ANALYSIS_PAYLOAD) - 1 + end_extra
    return _set_analysis_offsets(prepared, start, stop) + _ANALYSIS_PAYLOAD, start, stop


def _analysis_fixture(flowio, case):
    original = _packet_fixture(flowio)
    if case == "later_dataset":
        later_writer = writer_fixture(flowio, "writer/analysis_later_dataset.fcs",
                                       [41, 43], ["later_signal"])
        later, later_start, _ = _appended_analysis(later_writer)
        mutation_fixture("mutated/later_dataset_with_analysis.fcs", later, [later_writer],
            ["append the literal ANALYSIS payload after unchanged writer DATA",
             "set matching HEADER/TEXT ANALYSIS offsets", _ANALYSIS_PAYLOAD.decode("ascii")])
        prepared = mutate_writer(original, text_updates={"$BEGINANALYSIS": "0000000000",
            "$ENDANALYSIS": "0000000000", "$NEXTDATA": "0000000000"})
        boundary = len(prepared)
        start = boundary + later_start
        stop = start + len(_ANALYSIS_PAYLOAD) - 1
        raw = _set_analysis_offsets(prepared, start, stop, next_offset=boundary) + later
        changes = ["link two writer-derived datasets through first NEXTDATA",
                   "point first ANALYSIS offsets to the later dataset's real ANALYSIS bytes",
                   "preserve both original writer DATA segments", _ANALYSIS_PAYLOAD.decode("ascii")]
        parents = [original, later]
    else:
        raw, start, stop = _appended_analysis(original, end_extra=8 if case == "beyond_eof" else 0)
        changes = ["append the literal ANALYSIS payload after unchanged writer DATA",
                   "set matching HEADER/TEXT ANALYSIS offsets", _ANALYSIS_PAYLOAD.decode("ascii")]
        if case == "beyond_eof":
            changes.append("declare ANALYSIS end eight bytes beyond the retained artifact")
        parents = [original]
    raw = mutation_fixture(f"mutated/analysis_{case}.fcs", raw, parents, changes)
    return raw, start, stop


def _observe_actual_analysis_reads(flowio, monkeypatch):
    """Observe real decoder reads without replacing its parsing or input guard."""
    trace = {"attempts": [], "consumed": []}
    actual_parse = flowio.FlowData._FlowData__parse_analysis

    def observe(native, offset, start, stop):
        handle = native._fh
        actual_read = handle.read

        def read(size=-1):
            location = handle.tell()
            trace["attempts"].append({"byte_start": location, "requested_size": size})
            block = actual_read(size)
            trace["consumed"].append({"byte_start": location, "size_bytes": len(block),
                                      "bytes_hex": block.hex()})
            return block

        handle.read = read
        try:
            return actual_parse(native, offset, start, stop)
        finally:
            handle.read = actual_read

    monkeypatch.setattr(flowio.FlowData, "_FlowData__parse_analysis", observe)
    return trace


@pytest.mark.parametrize("case", ["valid", "beyond_eof", "later_dataset"])
def test_analysis_is_bounded_before_actual_decoder_consumes_segment_bytes(flowio, monkeypatch, case):
    raw, start, stop = _analysis_fixture(flowio, case)
    trace = _observe_actual_analysis_reads(flowio, monkeypatch)
    result = _parse(raw, ["signal"], fixture_kind="handcrafted writer-derived ANALYSIS fixture")
    save_json(f"analysis_{case}_parse.json", result)
    save_json(f"analysis_{case}_decoder_reads.json", trace)
    assert result["source"]["file"] == file_identity(raw)
    assert result["source"]["native_event_count"] == 8
    assert result["source"]["dataset_position"] == 0
    metadata = _metadata(result)
    assert metadata["flowio.header.version"] == "3.1"
    assert metadata["flowio.header.analysis_start"] == str(start)
    assert metadata["flowio.header.analysis_stop"] == str(stop)
    assert metadata["flowio.text.beginanalysis"] == str(start).zfill(10)
    assert metadata["flowio.text.endanalysis"] == str(stop).zfill(10)
    assert metadata["flowio.text.p1n"] == "signal"
    assert metadata["flowio.text.par"] == "1"
    assert metadata["flowio.text.tot"] == "8"
    if case == "valid":
        assert result["source"]["extent"] == "complete"
        assert _values(result) == PACKET548_VALUES
        assert result["issues"] == []
        assert metadata["flowio.analysis.analysistoken"] == "17"
        assert metadata["flowio.analysis.note"] == "retained fixture metadata"
        assert trace["consumed"]
        assert all(read == {"byte_start": start, "size_bytes": len(_ANALYSIS_PAYLOAD),
                            "bytes_hex": _ANALYSIS_PAYLOAD.hex()} for read in trace["consumed"])
    else:
        expected = "truncated_source" if case == "beyond_eof" else "native_format_mismatch"
        assert _codes(result) == {expected}
        assert result["source"]["extent"] == "unavailable"
        assert result["events"] == []
        assert trace["consumed"] == []
        assert not any(name.startswith("flowio.analysis.") for name in metadata)


@pytest.mark.parametrize("unavailable", ["absent", "wrong_version", "missing_version"])
def test_native_bytes_do_not_bypass_missing_or_wrong_decoder(flowio, monkeypatch, unavailable):
    raw = _packet_fixture(flowio)
    if unavailable == "absent":
        monkeypatch.setitem(sys.modules, "flowio", None)
    elif unavailable == "wrong_version":
        monkeypatch.setattr(flowio, "__version__", "1.3.0")
    else:
        monkeypatch.delattr(flowio, "__version__")
    result = _parse(raw, ["signal"])
    assert result["events"] == []
    assert result["source"]["extent"] == "unavailable"
    assert "decoder_unavailable" in _codes(result)


def test_native_artifact_identity_mismatch_never_admits_values(flowio, monkeypatch):
    raw = _packet_fixture(flowio)
    request = _request(raw, ["signal"])
    monkeypatch.setattr(flowio.FlowData, "__init__", _forbidden)
    result = reader.parse_fluorescence_fcs(raw + b"wrong bytes", **request)
    assert result["events"] == []
    assert "retained_artifact_mismatch" in _codes(result)
    assert result["source"]["file"] == file_identity(raw)


def test_saved_native_sheet_recalculates_without_decoder_files_network_or_processes(flowio, monkeypatch):
    raw = _packet_fixture(flowio)
    sheet = _sheet(_parse(raw, ["signal"]))
    parameters = _parameters()
    components = calculations.calculate_fluorescence_sheet(sheet, parameters=parameters)
    saved = save_json("saved_only_sheet.json", sheet)
    saved_parameters = save_json("saved_only_parameters.json", parameters)
    replay_sheet = json.loads(saved.read_text())
    replay_parameters = json.loads(saved_parameters.read_text())
    before_sheet, before_parameters = canonical(replay_sheet), canonical(replay_parameters)
    actual_import = builtins.__import__

    def guard_import(name, *args, **kwargs):
        if name.split(".")[0] in {"flowio", "numpy", "subprocess", "socket", "urllib", "requests", "openai"}:
            raise AssertionError("external package imported during saved-only recalculation: " + name)
        return actual_import(name, *args, **kwargs)

    with monkeypatch.context() as guard:
        guard.setattr(builtins, "__import__", guard_import)
        guard.setattr(builtins, "open", _forbidden)
        guard.setattr(io, "open", _forbidden)
        guard.setattr(Path, "open", _forbidden)
        guard.setattr(urllib.request, "urlopen", _forbidden)
        guard.setattr(socket, "socket", _forbidden)
        guard.setattr(subprocess, "run", _forbidden)
        guard.setattr(subprocess, "Popen", _forbidden)
        guard.setattr(flowio, "FlowData", _forbidden)
        guard.setattr(reader, "parse_fluorescence_fcs", _forbidden)
        recalculated = calculations.calculate_fluorescence_sheet(replay_sheet, parameters=replay_parameters)
        assert recalculated == components
        assert canonical(replay_sheet) == before_sheet
        assert canonical(replay_parameters) == before_parameters
        guard.setattr(calculations, "calculate_fluorescence_sheet", _forbidden)
        guard.setattr(calculations, "evaluate_gate_membership", _forbidden)
        guard.setattr(calculations, "_Calculation", _forbidden)
        selection = dict(requests=[_cell(components, "selected_percent")["request"]], offset=0, limit=1)
        view = project_fluorescence_result(replay_sheet, recalculated, selection=selection)
        assert view["rows"] == [_cell(components, "selected_percent")]
    save_json("saved_only_recalculated_components.json", recalculated)
    save_json("saved_only_projection.json", view)


def test_encoded_parser_has_no_preprocessing_or_second_calculation_entrypoint(flowio):
    source = inspect.getsource(reader)
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    forbidden = {"as_array", "write_fcs", "create_fcs", "calculate_fluorescence_sheet",
                 "evaluate_gate_membership", "compensate"}
    assert not [node for node in calls if (isinstance(node.func, ast.Attribute) and
                                        node.func.attr in forbidden) or
                (isinstance(node.func, ast.Name) and node.func.id in forbidden)]
    assert calculations.calculate_fluorescence_sheet.__module__ == \
        "gene_annotation_episode.fluorescence_event_calculations"
    assert Path(flowio.__file__).is_relative_to(require_bounded_runtime() / "source_snapshot" / SOURCE_RELATIVE)
