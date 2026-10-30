"""Bounded native preparation with labelled synthetic numerical inputs.

The actual installed FlowIO/FlowUtils methods execute. No molecular assay,
production deployment, selected producer or episode return is claimed here.
"""

import builtins
from copy import deepcopy
import hashlib
import importlib
import io
import json
from pathlib import Path
import struct

import pytest

from fluorescence_flowio_test_support import require_bounded_runtime, mutate_writer

require_bounded_runtime()

from gene_annotation_episode import fluorescence_event_contracts as core
from gene_annotation_episode import fluorescence_event_preparation as preparation
from gene_annotation_episode import fluorescence_preparation_contracts as contracts
from gene_annotation_episode import fluorescence_preparation_readers as readers
from gene_annotation_episode.fluorescence_fcs_reader import parse_fluorescence_fcs
from gene_annotation_episode.fluorescence_event_calculations import calculate_fluorescence_sheet
from gene_annotation_episode.fluorescence_event_sheet import populate_fluorescence_sheet
from gene_annotation_episode.fluorescence_result_views import project_fluorescence_result


@pytest.fixture
def native():
    flowio = importlib.import_module("flowio")
    flowutils = importlib.import_module("flowutils")
    assert flowio.__version__ == "1.4.0"
    assert flowutils.__version__ == "1.2.2"
    return flowio


def _file(raw, format_name="json"):
    sha = hashlib.sha256(raw).hexdigest()
    return dict(artifact_ref="artifact_" + sha, sha256=sha, size_bytes=len(raw), format=format_name)


def _retain(raw, suffix, description):
    directory = require_bounded_runtime() / "temporary" / "fluorescence_preparation_589"
    directory.mkdir(exist_ok=True)
    identity = _file(raw, suffix)
    path = directory / (identity["sha256"] + "." + suffix)
    path.write_bytes(raw)
    (directory / (identity["sha256"] + ".provenance.json")).write_text(json.dumps(dict(
        kind="synthetic_native_format_verification_fixture", description=description,
        measurement_origin="supplied_predicted", molecular_assay_claimed=False, file=identity),
        sort_keys=True, indent=2) + "\n")
    return identity


def _fcs(native, rows, names=("A", "B"), metadata=None):
    stream = io.BytesIO()
    native.create_fcs(stream, [number for row in rows for number in row], list(names), metadata_dict=metadata)
    raw = stream.getvalue()
    _retain(raw, "fcs", "FlowIO1.4.0.create_fcs writer with synthetic event values")
    return raw


def _parse(raw, names=("A", "B"), *, dataset=0):
    file = _file(raw, "fcs")
    source = dict(key="raw.source", file=file, dataset_position=dataset,
                  format_profile="fcs_flowio_1_4_0_encoded", extent="unavailable",
                  native_event_count=None, metadata=[])
    sample = dict(key="sample", primary_domain_key="raw", label="synthetic fixture",
                  condition=None, biological_replicate=None, technical_replicate=None, associations=[])
    unchanged = dict(state="not_applied", method=None, parameters_file=None)
    domain = dict(key="raw", source_key=source["key"], sample_key=sample["key"], parent_domain_key=None,
                  state="available", scale_kind="encoded", compensation=deepcopy(unchanged),
                  transformation=deepcopy(unchanged), correspondence=None,
                  comparison_basis=dict(key="declared linear matrix domain", evidence_file=_file(b"synthetic matrix-domain declaration")))
    channels = [dict(key=f"raw.c{index}", ordinal=index, native_name=name, label=None,
                     unit=None, analyte=None, measurement_origin="supplied_predicted")
                for index, name in enumerate(names)]
    return parse_fluorescence_fcs(raw, source=source, sample=sample, channels=channels, domain=domain)


def _request(parent, method=contracts.SCALE_METHOD, *, matrix=None, key="prepared"):
    output_channels = [dict({name: value for name, value in channel.items() if name != "domain_key"},
                            key=f"{key}.c{channel['ordinal']}") for channel in parent["channels"]]
    if method == contracts.SCALE_METHOD:
        params = dict(metadata_policy=contracts.POLICY)
    else:
        params = dict(matrix_file=deepcopy(matrix["file"]), dataset_position=matrix["dataset_position"],
                      keyword=matrix["keyword"], input_domain_basis=deepcopy(parent["domain"]["comparison_basis"]),
                      axes=[dict(native_label=label, input_channel_key=channel["key"], input_ordinal=channel["ordinal"])
                            for label in matrix["axis_tokens"]
                            for channel in parent["channels"] if channel["native_name"] == label])
    recipe = dict(version="fluorescence_preparation_recipe_v1", method=method, parameters=params)
    request = dict(key=key, input=dict(kind="event_input", index=0),
                   output=dict(key=key, source_key=key + ".source", sample_key=parent["sample"]["key"],
                               channels=output_channels, comparison_basis=deepcopy(parent["domain"]["comparison_basis"])),
                   recipe_file=_file(core.canonical(recipe) + b"\n"), recipe=recipe)
    return request


def _matrix(raw, parent, *, keyword="spill", source=None):
    source = parent["source"] if source is None else source
    return readers.read_fcs_spill_matrix(raw, source=source,
        locator=dict(dataset_position=source["dataset_position"], keyword=keyword), channels=parent["channels"])


def _comp_case(native, rows=((110, 60), (20, 100)), names=("A", "B"), spill="2,A,B,1,0.1,0.2,1"):
    raw = _fcs(native, rows, names=names, metadata=dict(spill=spill))
    parent = _parse(raw, names)
    matrix = _matrix(raw, parent)
    request = _request(parent, contracts.COMPENSATE_METHOD, matrix=matrix)
    return raw, parent, matrix, request


def _assembled(outcome, parent, request):
    data_file = None if outcome["data"] is None else _retain(
        core.canonical(outcome["data"]) + b"\n", "json", "actual native prepared data from synthetic fixture")
    parameters_file = _retain(core.canonical(outcome["parameters"]) + b"\n", "json",
                              "actual selected preparation resolution for synthetic fixture")
    return contracts.assemble_prepared_parse(outcome, request=request, parent=parent,
                                             data_file=data_file, parameters_file=parameters_file)


def _values(data, column=0):
    return [event["values"][column]["measurement"]["value"] for event in data["events"]]


def _codes(outcome):
    return {row["code"] for row in outcome["parameters"]["problems"]}


def _identities(parent):
    return [{name: parent["domain"][name] for name in ("key", "source_key", "sample_key")}]


def test_request_port_accepts_only_selected_kind_domain_identities(native):
    parent = _parse(_fcs(native, [[100]], names=("A",)), ("A",))
    request = _request(parent)
    original = core.canonical(request)
    checked = contracts.validate_preparation_request(request, input_domains=_identities(parent))
    assert checked == request and checked is not request
    assert core.canonical(request) == original
    with pytest.raises(core.FluorescenceContractError):
        contracts.validate_preparation_request(request, input_domains=[parent["domain"]])
    second = deepcopy(request)
    second["input"] = dict(kind="preparation", index=0)
    second["output"]["key"] = "second"
    second["output"]["source_key"] = "second.source"
    assert contracts.validate_preparation_request(second, input_domains=[
        {key: request["output"][key] for key in ("key", "source_key", "sample_key")}]) == second


@pytest.mark.parametrize("fault", ["extra", "bool_index", "future_index", "other_method", "extra_parameter", "bad_recipe_file", "wrong_sample", "same_domain"])
def test_request_rejects_malformed_closed_shapes(native, fault):
    parent = _parse(_fcs(native, [[100]], names=("A",)), ("A",))
    request = _request(parent)
    if fault == "extra": request["instructions"] = "run anything"
    elif fault == "bool_index": request["input"]["index"] = False
    elif fault == "future_index": request["input"]["index"] = 1
    elif fault == "other_method": request["recipe"]["method"] = "logicle"
    elif fault == "extra_parameter": request["recipe"]["parameters"]["gain"] = 2
    elif fault == "bad_recipe_file": request["recipe_file"]["sha256"] = "bad"
    elif fault == "wrong_sample": request["output"]["sample_key"] = "unrelated"
    elif fault == "same_domain": request["output"]["key"] = "raw"
    with pytest.raises(core.FluorescenceContractError):
        contracts.validate_preparation_request(request, input_domains=_identities(parent))


def test_actual_scaling_gain_time_and_untouched_columns(native):
    raw = _fcs(native, [[100, 10, 7]], names=("A", "Time", "U"),
               metadata=dict(p1g="2", p2g="9", timestep="0.1"))
    parent = _parse(raw, ("A", "Time", "U"))
    request = _request(parent)
    before = core.canonical([parent, request])
    outcome = preparation.prepare_fcs_scaling(raw, parent=parent, request=request)
    assert outcome["status"] == "complete"
    assert [_values(outcome["data"], column) for column in range(3)] == [[50], [1], [7]]
    resolution = outcome["parameters"]["scaling"]
    assert resolution["channels"][0]["png_raw"] == "2"
    assert resolution["channels"][0]["gain"] == 2
    assert resolution["channels"][1]["png_raw"] == "9"
    assert resolution["channels"][1]["gain"] == 1
    assert not resolution["channels"][1]["gain_applied"]
    assert resolution["time"] == dict(channel_key="raw.c1", timestep_raw="0.1", timestep=.1, applied=True)
    child = _assembled(outcome, parent, request)
    assert child["domain"]["scaling"]["state"] == "applied"
    assert child["domain"]["scale_kind"] == "scaled"
    assert child["source"]["native_event_count"] is None
    assert child["events"][0]["values"][2]["measurement"] == parent["events"][0]["values"][2]["measurement"]
    assert child["events"][0]["values"][0]["measurement"]["state"] == "derived"
    assert core.canonical([parent, request]) == before


def test_actual_integer_log_scaling(native):
    original = _fcs(native, [[50]], names=("A",))
    raw = mutate_writer(original, text_updates={"$DATATYPE": "I", "$P1B": "16", "$P1E": "2,1", "$P1R": "100"},
                        data=struct.pack("<H", 50))
    _retain(raw, "fcs", "explicit integer/log mutation of native writer synthetic fixture")
    parent = _parse(raw, ("A",))
    outcome = preparation.prepare_fcs_scaling(raw, parent=parent, request=_request(parent))
    assert outcome["status"] == "complete"
    assert _values(parent) == [50]
    assert _values(outcome["data"]) == pytest.approx([10], rel=1e-12)


@pytest.mark.parametrize("updates,metadata", [
    ({"$P1E": None}, None), ({"$P1E": "2,0"}, None), ({"$P1G": "0"}, None),
    ({"$P1G": "-2"}, None), ({"$TIMESTEP": " "}, {"timestep": "0.1"}),
    ({"$TIMESTEP": "-1"}, {"timestep": "0.1"}),
])
def test_strict_scaling_rejects_native_fallbacks_without_replacing_raw(native, updates, metadata):
    raw = mutate_writer(_fcs(native, [[100]], names=("A",), metadata=metadata), text_updates=updates)
    parent = _parse(raw, ("A",))
    before = core.canonical(parent)
    outcome = preparation.prepare_fcs_scaling(raw, parent=parent, request=_request(parent))
    assert outcome["status"] == "incompatible"
    assert "parameter_invalid" in _codes(outcome)
    assert outcome["data"] is None
    assert core.canonical(parent) == before
    assert _values(parent) == [100]


def test_optional_absent_gain_and_timestep_remain_undeclared(native):
    raw = mutate_writer(_fcs(native, [[100, 10]], names=("A", "Time")),
                        text_updates={"$P1G": None, "$P2G": None})
    parent = _parse(raw, ("A", "Time"))
    outcome = preparation.prepare_fcs_scaling(raw, parent=parent, request=_request(parent))
    assert outcome["status"] == "complete"
    assert [row["gain"] for row in outcome["parameters"]["scaling"]["channels"]] == [None, None]
    assert outcome["parameters"]["scaling"]["time"]["timestep"] is None
    assert not outcome["parameters"]["scaling"]["time"]["applied"]
    assert outcome["data"]["events"][0]["values"][0]["measurement"] == parent["events"][0]["values"][0]["measurement"]


def test_actual_compensation_orientation_raw_gates_and_shared_saved_calculation(native, monkeypatch):
    raw, parent, matrix, request = _comp_case(native)
    before = core.canonical([parent, matrix, request])
    outcome = preparation.prepare_spill_compensation(parent, matrix=matrix, request=request)
    assert outcome["status"] == "complete"
    assert _values(outcome["data"], 0) == pytest.approx([100, 0], abs=1e-12)
    assert _values(outcome["data"], 1) == pytest.approx([50, 100], abs=1e-12)
    child = _assembled(outcome, parent, request)
    assert child["domain"]["parent_domain_key"] == "raw"
    gates = [dict(key=key, sample_key="sample", parent=dict(kind="population", key="all"),
                  kind="threshold", domain_key=domain, channel_key=channel,
                  lower=dict(value=105, inclusive=True), upper=None)
             for key, domain, channel in (("raw-gate", "raw", "raw.c0"),
                                          ("prepared-gate", "prepared", "prepared.c0"))]
    gates.append(dict(key="all-prepared", sample_key="sample", parent=dict(kind="population", key="all"),
                      kind="pass_all", domain_key=None, channel_key=None, lower=None, upper=None))
    sheet = populate_fluorescence_sheet([parent, child], populations=[dict(
        key="all", sample_key="sample", kind="all", event_ordinals=None)], gates=gates,
        control_pairs=[], native_reports=[])
    params = dict(fraction_requests=[dict(gate_key=key, denominator="parent") for key in ("raw-gate", "prepared-gate")],
                  intensity_requests=[dict(gate_key="all-prepared", domain_key="prepared", channel_key="prepared.c1")],
                  control_requests=[], native_comparison_requests=[])
    components = calculate_fluorescence_sheet(sheet, parameters=params)
    def cell(metric, gate):
        return next(row for row in components["cells"] if row["request"]["metric"] == metric and row["request"]["gate_key"] == gate)
    assert cell("selected_event_count", "raw-gate")["value"] == 1
    assert cell("selected_event_count", "prepared-gate")["value"] == 0
    assert cell("selected_intensity_sum", "all-prepared")["value"] == pytest.approx(150)
    assert cell("selected_intensity_mean", "all-prepared")["value"] == pytest.approx(75)
    assert cell("selected_intensity_median", "all-prepared")["value"] == pytest.approx(75)
    saved = json.loads(core.canonical(sheet))
    original_import = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in {"flowio", "flowutils", "numpy"}:
            raise AssertionError("saved calculation attempted native preparation")
        return original_import(name, *args, **kwargs)
    with monkeypatch.context() as context:
        context.setattr(builtins, "__import__", guarded)
        context.setattr(preparation, "prepare_fcs_scaling", lambda *a, **k: pytest.fail("reprepared saved data"))
        context.setattr(preparation, "prepare_spill_compensation", lambda *a, **k: pytest.fail("reprepared saved data"))
        recalculated = calculate_fluorescence_sheet(saved, parameters=params)
        selected = [cell("selected_event_count", "raw-gate"), cell("selected_event_count", "prepared-gate")]
        view = project_fluorescence_result(saved, recalculated,
            selection=dict(requests=[row["request"] for row in selected], offset=0, limit=2))
    assert recalculated == components
    assert view["rows"] == selected
    assert core.canonical([parent, matrix, request]) == before


def test_reversed_source_order_keeps_explicit_matrix_order(native):
    _, parent, matrix, request = _comp_case(native, rows=((60, 110), (100, 20)), names=("B", "A"))
    assert [axis["input_ordinal"] for axis in request["recipe"]["parameters"]["axes"]] == [1, 0]
    outcome = preparation.prepare_spill_compensation(parent, matrix=matrix, request=request)
    assert _values(outcome["data"], 1) == pytest.approx([100, 0], abs=1e-12)
    assert _values(outcome["data"], 0) == pytest.approx([50, 100], abs=1e-12)


def test_missing_matrix_components_keep_all_rows_and_untouched_values(native):
    _, parent, matrix, request = _comp_case(native,
        rows=((110, 60, 7), (20, float("nan"), 9), (0, 10, 0)), names=("A", "B", "U"))
    outcome = preparation.prepare_spill_compensation(parent, matrix=matrix, request=request)
    assert outcome["status"] == "partial"
    assert len(outcome["data"]["events"]) == 3
    assert _values(outcome["data"], 0)[0] == pytest.approx(100)
    assert _values(outcome["data"], 0)[1] is None
    assert _values(outcome["data"], 1)[1] is None
    assert _values(outcome["data"], 0)[2] < 0
    assert _values(outcome["data"], 2) == [7, 9, 0]
    assert [row["event_ordinal"] for row in outcome["data"]["events"]] == [0, 1, 2]
    assert outcome["data"]["events"][1]["values"][2]["measurement"] == parent["events"][1]["values"][2]["measurement"]
    core.validate_event_parse_result(_assembled(outcome, parent, request))


def test_singular_matrix_retains_native_exception_and_no_fallback(native):
    _, parent, matrix, request = _comp_case(native, spill="2,A,B,1,1,1,1")
    outcome = preparation.prepare_spill_compensation(parent, matrix=matrix, request=request)
    assert outcome["status"] == "failed" and outcome["data"] is None
    assert "matrix_singular" in _codes(outcome)
    assert outcome["parameters"]["diagnostics"] == [dict(
        problem_code="matrix_singular", exception_class="numpy.linalg.LinAlgError")]
    child = _assembled(outcome, parent, request)
    assert child["source"]["file"] is None and child["source"]["extent"] == "unavailable"
    assert child["events"] == [] and child["domain"]["state"] == "failed"
    assert _values(parent) == [110, 20]


@pytest.mark.parametrize("field,state", [("compensation", "applied"), ("compensation", "unknown"),
                                          ("compensation", "failed"), ("transformation", "applied"),
                                          ("transformation", "unknown")])
def test_compensation_rejects_double_or_unresolved_preparation(native, field, state):
    _, parent, matrix, request = _comp_case(native)
    parent["domain"][field] = dict(state=state, method="supplied" if state == "applied" else None,
                                   parameters_file=_file(b"supplied parameters") if state == "applied" else None)
    outcome = preparation.prepare_spill_compensation(parent, matrix=matrix, request=request)
    assert outcome["status"] == "incompatible" and outcome["data"] is None
    assert _codes(outcome) == {"already_prepared" if state == "applied" else "preparation_state_unknown"}


def test_scaling_rejects_prepared_child_but_original_can_be_selected_again(native):
    raw = _fcs(native, [[100]], names=("A",), metadata=dict(p1g="2"))
    parent = _parse(raw, ("A",))
    request = _request(parent)
    outcome = preparation.prepare_fcs_scaling(raw, parent=parent, request=request)
    child = _assembled(outcome, parent, request)
    second = _request(child, key="second")
    rejected = preparation.prepare_fcs_scaling(raw, parent=child, request=second)
    assert rejected["status"] == "incompatible" and rejected["data"] is None
    repeated_original = preparation.prepare_fcs_scaling(raw, parent=parent, request=_request(parent, key="other"))
    assert _values(repeated_original["data"]) == [50]


def test_partial_encoded_row_is_not_padded_or_renumbered(native):
    raw = _fcs(native, [[100, 80], [40, 20]], metadata=dict(p1g="2", p2g="2"))
    start, stop = int(raw[26:34]), int(raw[34:42])
    raw = mutate_writer(raw, data=raw[start:stop + 1 - 4])
    parent = _parse(raw)
    assert parent["source"]["extent"] == "partial" and len(parent["events"]) == 2
    outcome = preparation.prepare_fcs_scaling(raw, parent=parent, request=_request(parent))
    assert outcome["status"] == "partial"
    assert _values(outcome["data"]) == [50, None]
    assert _values(outcome["data"], 1) == [40, None]
    assert _values(parent) == [100, 40]
    assert outcome["data"]["correspondence"] == [dict(source_ordinal=0, event_ordinal=0), dict(source_ordinal=1, event_ordinal=1)]


def test_native_nonfinite_preparation_stays_invalid_with_raw_retained(native):
    original = _fcs(native, [[65535]], names=("A",))
    raw = mutate_writer(original, text_updates={"$DATATYPE": "I", "$P1B": "16", "$P1E": "1000,1", "$P1R": "65536"},
                        data=struct.pack("<H", 65535))
    parent = _parse(raw, ("A",))
    outcome = preparation.prepare_fcs_scaling(raw, parent=parent, request=_request(parent))
    assert outcome["status"] == "partial"
    assert outcome["data"]["events"][0]["values"][0]["measurement"] == dict(value=None, state="invalid", raw=None)
    assert _codes(outcome) == {"derived_nonfinite"}
    assert _values(parent) == [65535]


def test_unavailable_backend_is_explicit_and_does_not_install(native, monkeypatch):
    _, parent, matrix, request = _comp_case(native)
    monkeypatch.setattr(preparation, "_load_flowutils", lambda: None)
    outcome = preparation.prepare_spill_compensation(parent, matrix=matrix, request=request)
    assert outcome["status"] == "unavailable" and _codes(outcome) == {"backend_unavailable"}
    assert outcome["data"] is None and _values(parent) == [110, 20]


@pytest.mark.parametrize("fault", ["parent_hash", "mapping", "event_identity", "copied_transformed", "untouched", "extra", "source_file"])
def test_outcome_rejects_tampered_lineage_and_generated_states(native, fault):
    _, parent, matrix, request = _comp_case(native, rows=((110, 60, 7),), names=("A", "B", "U"))
    outcome = preparation.prepare_spill_compensation(parent, matrix=matrix, request=request)
    if fault == "parent_hash": outcome["data"]["input_parse_sha256"] = "0" * 64
    elif fault == "mapping": outcome["data"]["correspondence"][0]["event_ordinal"] = 1
    elif fault == "event_identity": outcome["data"]["events"][0]["event_ordinal"] = 1
    elif fault == "copied_transformed": outcome["data"]["events"][0]["values"][0]["measurement"] = deepcopy(parent["events"][0]["values"][0]["measurement"])
    elif fault == "untouched": outcome["data"]["events"][0]["values"][2]["measurement"]["value"] = 99
    elif fault == "extra": outcome["parameters"]["options"] = {}
    elif fault == "source_file": outcome["parameters"]["compensation"]["file"] = _file(b"not the selected matrix")
    with pytest.raises(core.FluorescenceContractError):
        contracts.validate_preparation_outcome(outcome, request=request, parent=parent)


def test_assembly_requires_actual_numerical_canonical_bytes(native):
    _, parent, matrix, request = _comp_case(native)
    outcome = preparation.prepare_spill_compensation(parent, matrix=matrix, request=request)
    with pytest.raises(core.FluorescenceContractError):
        contracts.assemble_prepared_parse(outcome, request=request, parent=parent,
            data_file=_file(core.canonical(outcome["data"])),
            parameters_file=_file(core.canonical(outcome["parameters"]) + b"\n"))


def test_selected_scale_then_compensate_preserves_inherited_parameter_identity(native):
    raw = _fcs(native, [[220, 120], [40, 200]], metadata=dict(p1g="2", p2g="2", spill="2,A,B,1,0.1,0.2,1"))
    original = _parse(raw)
    scaling_request = _request(original, key="scaled")
    scaling_request["output"]["comparison_basis"] = dict(key="explicit scaled matrix domain", evidence_file=_file(b"scaled matrix domain declaration"))
    scaled = _assembled(preparation.prepare_fcs_scaling(raw, parent=original, request=scaling_request), original, scaling_request)
    matrix = _matrix(raw, scaled, source=original["source"])
    request = _request(scaled, contracts.COMPENSATE_METHOD, matrix=matrix, key="compensated")
    request["input"]["kind"] = "preparation"
    outcome = preparation.prepare_spill_compensation(scaled, matrix=matrix, request=request)
    child = _assembled(outcome, scaled, request)
    assert _values(child) == pytest.approx([100, 0], abs=1e-12)
    assert child["domain"]["parent_domain_key"] == "scaled"
    assert child["domain"]["scaling"] == scaled["domain"]["scaling"]
    assert child["domain"]["compensation"]["parameters_file"] != child["domain"]["scaling"]["parameters_file"]
    assert child["sample"] == original["sample"]
    assert child["domain"]["correspondence"] == scaled["domain"]["correspondence"]


def test_compensation_composes_supplied_primary_correspondence(native):
    from gene_annotation_episode.fluorescence_event_readers import parse_fluorescence_table_snapshot

    raw, original, matrix, _ = _comp_case(native)
    table_raw = core.canonical(dict(schema=core.TABLE_SCHEMA, columns=["A", "B"], rows=[[110, 60], [20, 100]]))
    source = dict(key="supplied.source", file=_file(table_raw), dataset_position=0,
                  format_profile="synthetic_supplied_snapshot", extent="unavailable", native_event_count=None, metadata=[])
    domain = deepcopy(original["domain"])
    domain.update(key="supplied", source_key=source["key"], parent_domain_key="raw", scale_kind="as_supplied",
                  correspondence=[dict(source_ordinal=0, event_ordinal=5), dict(source_ordinal=1, event_ordinal=2)])
    channels = [{name: value for name, value in row.items() if name != "domain_key"} for row in original["channels"]]
    for index, channel in enumerate(channels):
        channel.update(key=f"supplied.c{index}", measurement_origin="supplied_predicted")
    parent = parse_fluorescence_table_snapshot(table_raw, source=source, sample=original["sample"], channels=channels, domain=domain)
    request = _request(parent, contracts.COMPENSATE_METHOD, matrix=matrix)
    outcome = preparation.prepare_spill_compensation(parent, matrix=matrix, request=request)
    assert outcome["data"]["correspondence"] == [dict(source_ordinal=0, event_ordinal=5), dict(source_ordinal=1, event_ordinal=2)]
    assert [row["event_ordinal"] for row in outcome["data"]["events"]] == [5, 2]
    assert _values(outcome["data"]) == pytest.approx([100, 0], abs=1e-12)
    core.validate_event_parse_result(_assembled(outcome, parent, request))


def test_finite_near_singular_solution_has_no_invented_acceptance_threshold(native):
    _, parent, matrix, request = _comp_case(native, rows=((2, 2),), spill="2,A,B,1,1,1,1.000000000001")
    outcome = preparation.prepare_spill_compensation(parent, matrix=matrix, request=request)
    assert outcome["status"] == "complete"
    assert _values(outcome["data"], 0) == pytest.approx([2], abs=1e-8)
    assert _values(outcome["data"], 1) == pytest.approx([0], abs=1e-8)
    assert outcome["parameters"]["compensation"]["raw_token"] == "2,A,B,1,1,1,1.000000000001"


def test_missing_matrix_preserves_raw_and_unavailable_selected_domain(native):
    raw = _fcs(native, [[110, 60]])
    parent = _parse(raw)
    missing = _matrix(raw, parent)
    # Select the two axes explicitly even though the native keyword is absent.
    declared = dict(missing, axis_tokens=["A", "B"])
    request = _request(parent, contracts.COMPENSATE_METHOD, matrix=declared)
    outcome = preparation.prepare_spill_compensation(parent, matrix=missing, request=request)
    assert outcome["status"] == "unavailable" and _codes(outcome) == {"parameter_unavailable"}
    assert _values(parent) == [110]
    child = _assembled(outcome, parent, request)
    assert child["domain"]["key"] == "prepared" and child["events"] == []
    assert child["domain"]["state"] == "unavailable"


def test_wrong_matrix_basis_and_positional_axis_are_specific_incompatibilities(native):
    _, parent, matrix, request = _comp_case(native)
    wrong_basis = deepcopy(request)
    wrong_basis["recipe"]["parameters"]["input_domain_basis"]["key"] = "unrelated domain"
    outcome = preparation.prepare_spill_compensation(parent, matrix=matrix, request=wrong_basis)
    assert _codes(outcome) == {"domain_incompatible"}
    wrong_position = deepcopy(request)
    wrong_position["recipe"]["parameters"]["axes"][0]["input_ordinal"] = 4
    outcome = preparation.prepare_spill_compensation(parent, matrix=matrix, request=wrong_position)
    assert _codes(outcome) == {"channel_mapping_incompatible"}


@pytest.mark.parametrize("output_unit", ["seconds", None, "ticks", "minutes"])
def test_time_timestep_requires_matching_selected_output_unit(native, output_unit):
    raw = _fcs(native, [[10]], names=("Time",), metadata=dict(timestep="0.1"))
    parent = _parse(raw, ("Time",))
    parent["channels"][0]["unit"] = "ticks"
    request = _request(parent)
    request["output"]["channels"][0]["unit"] = output_unit
    outcome = preparation.prepare_fcs_scaling(raw, parent=parent, request=request)
    if output_unit in {"seconds", None}:
        assert outcome["status"] == "complete"
        assert _values(outcome["data"]) == [1]
        assert _assembled(outcome, parent, request)["channels"][0]["unit"] == output_unit
    else:
        assert outcome["status"] == "incompatible" and _codes(outcome) == {"domain_incompatible"}
        assert outcome["data"] is None
    assert parent["channels"][0]["unit"] == "ticks" and _values(parent) == [10]


@pytest.mark.parametrize("output_unit", ["ticks", "seconds", None])
def test_absent_time_timestep_preserves_only_original_unit(native, output_unit):
    raw = _fcs(native, [[10]], names=("Time",))
    parent = _parse(raw, ("Time",))
    parent["channels"][0]["unit"] = "ticks"
    request = _request(parent)
    request["output"]["channels"][0]["unit"] = output_unit
    outcome = preparation.prepare_fcs_scaling(raw, parent=parent, request=request)
    if output_unit == "ticks":
        assert outcome["status"] == "complete" and _values(outcome["data"]) == [10]
    else:
        assert outcome["status"] == "incompatible" and _codes(outcome) == {"domain_incompatible"}


@pytest.mark.parametrize("output_unit", [None, "seconds", "ticks"])
def test_nonlinear_time_preserves_native_values_only_with_unknown_unit(native, output_unit):
    raw = _fcs(native, [[50]], names=("Time",), metadata=dict(timestep="0.1"))
    raw = mutate_writer(raw, text_updates={"$DATATYPE": "I", "$P1B": "16", "$P1E": "2,1", "$P1R": "100"},
                        data=struct.pack("<H", 50))
    parent = _parse(raw, ("Time",))
    parent["channels"][0]["unit"] = "ticks"
    request = _request(parent)
    request["output"]["channels"][0]["unit"] = output_unit
    outcome = preparation.prepare_fcs_scaling(raw, parent=parent, request=request)
    if output_unit is None:
        assert outcome["status"] == "complete"
        # Native order is timestep first, then declared logarithmic operation.
        assert _values(outcome["data"]) == pytest.approx([10 ** .1], rel=1e-12)
    else:
        assert outcome["status"] == "incompatible" and _codes(outcome) == {"domain_incompatible"}
        assert "parameter_invalid" not in _codes(outcome)


@pytest.mark.parametrize("field,state", [("compensation", "applied"), ("compensation", "unknown"),
                                          ("transformation", "applied"), ("transformation", "failed")])
def test_scaling_preserves_original_other_preparation_records(native, field, state):
    raw = _fcs(native, [[100]], names=("A",), metadata=dict(p1g="2"))
    parent = _parse(raw, ("A",))
    inherited = dict(state=state, method="retained supplied preparation",
                     parameters_file=_file(b"retained supplied preparation parameters"))
    parent["domain"][field] = deepcopy(inherited)
    request = _request(parent)
    outcome = preparation.prepare_fcs_scaling(raw, parent=parent, request=request)
    assert outcome["status"] == "complete" and _values(outcome["data"]) == [50]
    assert _assembled(outcome, parent, request)["domain"][field] == inherited
    assert parent["domain"][field] == inherited


@pytest.mark.parametrize("method", [contracts.SCALE_METHOD, contracts.COMPENSATE_METHOD])
def test_non_time_unit_changes_are_not_silent_calibration(native, method):
    raw, parent, matrix, _ = _comp_case(native)
    request = _request(parent, method, matrix=matrix)
    request["output"]["channels"][0]["unit"] = "molecules"
    with pytest.raises(core.FluorescenceContractError):
        if method == contracts.SCALE_METHOD:
            preparation.prepare_fcs_scaling(raw, parent=parent, request=request)
        else:
            preparation.prepare_spill_compensation(parent, matrix=matrix, request=request)


@pytest.mark.parametrize("fault", ["gain_token", "gain_number", "range_token", "decades_token", "timestep_token", "time_identity", "application_flag"])
def test_successful_scaling_resolution_must_match_its_retained_metadata(native, fault):
    raw = _fcs(native, [[100, 10]], names=("A", "Time"), metadata=dict(p1g="2", timestep="0.1"))
    parent = _parse(raw, ("A", "Time"))
    request = _request(parent)
    outcome = preparation.prepare_fcs_scaling(raw, parent=parent, request=request)
    resolution = outcome["parameters"]["scaling"]
    if fault == "gain_token": resolution["channels"][0]["png_raw"] = "4"
    elif fault == "gain_number": resolution["channels"][0]["gain"] = 4
    elif fault == "range_token": resolution["channels"][0]["pnr_raw"] = "500"
    elif fault == "decades_token": resolution["channels"][0]["pne_raw"] = "2,1"
    elif fault == "timestep_token": resolution["time"]["timestep_raw"] = "0.5"
    elif fault == "time_identity": resolution["time"]["channel_key"] = "raw.c0"
    elif fault == "application_flag": resolution["time"]["applied"] = False
    with pytest.raises(core.FluorescenceContractError):
        contracts.validate_preparation_outcome(outcome, request=request, parent=parent)
