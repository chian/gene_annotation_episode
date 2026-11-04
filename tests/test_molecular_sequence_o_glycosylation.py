"""Engineered ordinary O boundaries; no current native scanner is executed.

The STP and ASA logs below are literal retained227 outputs (report SHA256
201d130ce7880db9ad0e66267ce5beaaa9a9aeee03df3a05f01c802f5acd6bf3).
The existing normal Workflow, action, receipt and publication owners run here;
their reservation/completion observations are explicitly engineering fixtures.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import glycosylation_measurements as glyco
from gene_annotation_episode import molecular_sequence_native as native
from gene_annotation_episode import molecular_sequence_ordinary as ordinary
from gene_annotation_episode import molecular_sequence_result_contracts as contracts
from gene_annotation_episode import molecular_sequence_tools as tools
from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.molecular_measurement_tools import MolecularOperationUnpublished
from gene_annotation_episode.native_file_capture import retained_native_file
from gene_annotation_episode.runtime import ActionFailure, Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from tests.test_glycosylation_measurements import o_log
from tests.test_molecular_sequence_n_glycosylation import _retained, _tables
from tests.test_molecular_sequence_ordinary import selected_call, _lifecycle, _metadata_fixture, _pin, _write
from tests.test_molecular_sequence_tools_native import _controller, _credit
from tests.test_runtime import ScriptedProvider


O = "predict_o_glycosylation_hotspots"
N = "find_n_glycosylation_motifs"
ORF = contracts.ORDINARY_ORF_TOOL
PARAMETERS = dict(window=2, min_st_fraction=.4, disallow_proline_next=True)
STP_LOG = ("# Heuristic O-glycosylation hotspot prediction (S/T density based)\n"
    "Sequence length: 3 | window=7 | threshold=0.4\nTotal candidate sites: 1\n\nTop candidates:\n"
    "- pos 1 (S): S/T fraction=0.667 in window 1-3\n\n"
    "Note: For state-of-the-art O-glycosite prediction, use NetOGlyc 4.0 (web service).")
ASA_LOG = ("# Heuristic O-glycosylation hotspot prediction (S/T density based)\n"
    "Sequence length: 3 | window=3 | threshold=0.3333\nTotal candidate sites: 1\n\nTop candidates:\n"
    "- pos 2 (S): S/T fraction=0.333 in window 1-3\n\n"
    "Note: For state-of-the-art O-glycosite prediction, use NetOGlyc 4.0 (web service).")


def _forbidden(*args, **kwargs):
    raise AssertionError("Native/scanner/provider/HTTP work is forbidden by this engineering fixture")


def _rows():
    return [dict(row_id={"kind": "summary"}, fields=["native_reported_total_count",
        "retained_printed_row_count", "usable_checked_row_count", "native_report_complete"]),
        dict(row_id={"kind": "glycosylation_site", "row_ordinal": 0}, fields=["position_1based",
            "processed_interval", "native_st_fraction", "st_count", "window_denominator_symbols",
            "calculated_st_fraction", "source_rounded_st_fraction", "residue", "native_st_fraction_token",
            "source_intervals", "native_window_interval", "expected_clipped_window_interval",
            "window_source_intervals", "window_symbols", "window_symbol_counts"])]


def _cell(public, field, ordinal=None):
    return next(cell for cell in public["values"]["rows"] if cell["field"] == field
        and (ordinal is None or cell["row_id"].get("row_ordinal") == ordinal))


def _o_call(selected_call):
    original, calls = selected_call
    call = {key: value if key in ("context", "policy") else deepcopy(value)
        for key, value in original.items()}
    call["arguments"] = dict(subject_ref=call["frozen_operand"]["subject"]["id"], **PARAMETERS, rows=_rows())
    call["frozen_operand"]["version"] = contracts.ordinary_molecular_sequence_profile(O)["operand_version"]
    deployment = call["selected"]["deployment"]
    deployment["version"] = native.DEPLOYMENT_VERSION_V2
    deployment["module"]["sha256"] = native.GLYCO_SOURCE_SHA256
    return call, calls


def _configuration(call):
    selected = call["selected"]
    glyco = dict(version=tools.BINDING_VERSION, operation=O,
        deployment=deepcopy(selected["deployment"]), software=deepcopy(selected["software"]))
    n, orf = deepcopy(glyco), deepcopy(glyco)
    n["operation"], orf["operation"] = N, ORF
    orf["deployment"]["version"] = native.DEPLOYMENT_VERSION
    orf["deployment"]["module"]["sha256"] = native.SOURCE_SHA256
    resources = {"three-explicit": dict(kind="local", workspace=selected["workspace"],
        policy=deepcopy(ordinary.POLICY), native_molecular_sequence=[orf, n, glyco])}
    environments = [dict(operation=operation, resource_id="three-explicit", binding_ordinal_0based=index,
        environment=deepcopy(ordinary.ENVIRONMENT_SELECTION)) for index, operation in enumerate((ORF, N, O))]
    return resources, environments


def _caller(store, registry, resources, environments, directory, run_id, initial):
    directory.mkdir(parents=True, exist_ok=True)
    factory = ExecutionServiceFactory(resources, {}, 1, 1, 1,
        molecular_sequence_environments=environments, molecular_sequence_saved_modes=True)
    application = factory(store, run_id=run_id, directory=directory, tool_registry=registry)
    provider = ScriptedProvider([])
    provider.complete = _forbidden
    flow = Workflow(store, registry, provider, directory, run_id, _controller, _credit,
        project_child_credit=_credit, root_role="improvement", episode_record_receipts=True,
        episode_binding_descriptors=application.episode_binding_descriptors,
        role_credit_bindings=application.role_credit_bindings,
        job_progress_provider=application.job_progress_provider, initial_known_record_refs=initial)
    caller = flow.build("improvement", "caller", "Read the retained O hotspot density and its original clipped-window meaning.",
        store.validate_scope())
    return flow, caller, provider


def _dispatch(value, arguments, index):
    selection = dict(kind="tool", tool=O, arguments=deepcopy(arguments))
    asyncio.run(value.caller.source.execute(selection, index))
    row = value.flow.journal.row("runtime_actions", value.caller.source.episode_id, index)
    assert json.loads(row["action"]) == selection and row["result"] is not None
    return json.loads(row["result"])


def _engineered_roles(prepared, *, log, outcome, alter=None):
    bundle, declaration = _metadata_fixture(prepared)
    request = prepared["plan"]["selection"]["driver_request"]
    declaration.update(operation=O, qualification="engineered lifecycle; retained O log; no current scanner")
    operand, arguments = prepared["binding"]["frozen_operand"], prepared["binding"]["arguments"]
    parameters = {key: arguments[key] for key in PARAMETERS}
    sheet = glyco.build_glycosylation_sheet(O, log, sequence=operand["sequence"], parameters=parameters,
        native_outcome=outcome, input_ref=arguments["subject_ref"], input_mapping=operand["parent_mapping"])
    components = glyco.calculate_glycosylation_components(sheet)
    if alter is not None:
        alter(sheet, components)
    capture = dict(version=native.RESULT_VERSION_V2, request=deepcopy(request["selection"]),
        request_canonical_sha256=hashlib.sha256(canonical(request["selection"]).encode()).hexdigest(),
        stage="engineering_fixture", native_record=None, native_call_state="not_started", reference_data=None,
        execution_receipt=None, stdout="", stderr="", failure={"engineering_fixture": True})
    root = Path(prepared["plan"]["attempt_directory"])
    for role, document in dict(capture=capture, sheet=sheet, components=components).items():
        path = root / "driver-output" / (role + ".json")
        _write(path, document)
        pin = _pin(path, path.read_bytes())
        declaration["files"][role] = dict(relative_path=path.name, format="json", state="present",
            sha256=pin["sha256"], size_bytes=pin["size_bytes"])
    _write(root / "driver-output/declaration.json", declaration)
    for row in bundle["files"]:
        path = root / row["relative_path"]
        row["observed"] = _pin(path, path.read_bytes()) if path.exists() else None
        row["observed_state"] = "present" if row["observed"] is not None else "absent"
        row["declared"] = deepcopy(declaration["files"].get(row["role"]))
    _write(root / "attempt-bundle.json", bundle)
    return sheet, components


@pytest.fixture
def o_boundary(tmp_path, monkeypatch, selected_call, request):
    call, calls = _o_call(selected_call)
    options = getattr(request, "param", {})
    store = Store(tmp_path / "state")
    subject_ref, = store.create_problem(raw_sequence=options.get("sequence", "STP"), molecule="protein")["subject_refs"]
    subject = store.get(subject_ref)
    registry = ToolRegistry(store, job_limits=deepcopy(ordinary.POLICY))
    resources, environments = _configuration(call)
    flow, caller, provider = _caller(store, registry, resources, environments, tmp_path / "run",
        "engineering-o-boundary", [subject_ref, subject["sequence_ref"]])
    parameters = deepcopy(options.get("parameters", PARAMETERS))
    value = SimpleNamespace(store=store, registry=registry, flow=flow, caller=caller, provider=provider,
        subject=subject, resources=resources, environments=environments, call=call, calls=calls,
        parameters=parameters, log=options.get("log", STP_LOG), outcome=options.get("outcome", "completed"),
        arguments=dict(subject_ref=subject_ref, **parameters, rows=deepcopy(options.get("rows", _rows()))),
        prepared=None, frozen=None, sheet=None, components=None, alter=None, admissions=[], models=[])
    reader, freeze, sequence = flow.services.read_received_molecular_input, registry._prepare_molecular_sequence_operand, registry._sequence
    def admission(*args, **kwargs):
        value.admissions.append((args[1], args[2], deepcopy(kwargs)))
        return reader(*args, **kwargs)
    def sequence_model(reference, *, molecule_model=None):
        value.models.append(molecule_model)
        return sequence(reference, molecule_model=molecule_model)
    def admitted_freeze(operation, reference, *, scope):
        assert operation == O
        assert value.admissions[-1] == (reference, "input", {"subject_metadata_only": True})
        value.frozen = freeze(operation, reference, scope=scope)
        return value.frozen
    prepare = ordinary.prepare_ordinary_molecular_sequence_attempt
    def reserve(**kwargs):
        assert kwargs["operation"] == O and value.frozen is not None and not store.db.in_transaction
        value.prepared = prepare(**kwargs)
        value.sheet, value.components = _engineered_roles(value.prepared, log=value.log,
            outcome=value.outcome, alter=value.alter)
        _lifecycle(monkeypatch, value.prepared, views=("returned",))
        return value.prepared
    monkeypatch.setattr(flow.services, "read_received_molecular_input", admission)
    monkeypatch.setattr(registry, "_sequence", sequence_model)
    monkeypatch.setattr(registry, "_prepare_molecular_sequence_operand", admitted_freeze)
    monkeypatch.setattr(ordinary, "prepare_ordinary_molecular_sequence_attempt", reserve)
    monkeypatch.setattr(native, "execute_molecular_sequence_request", _forbidden)
    monkeypatch.setattr(ordinary.driver, "execute_molecular_sequence_request", _forbidden)
    monkeypatch.setattr(ordinary.native, "start_prepared", _forbidden)
    monkeypatch.setattr(registry.clients, "_http", _forbidden)
    monkeypatch.setattr("socket.create_connection", _forbidden)
    try:
        yield value
    finally:
        assert provider.contexts == []
        store.close()


def _seed(value):
    return _dispatch(value, value.arguments, 0)


def _project(store, sheet, components, rows):
    sources = {role: contracts.empty_file_state("not_requested") for role in contracts.FILE_ROLES}
    sources["sheet"], sources["components"] = _retained(store, sheet), _retained(store, components)
    selection = contracts.ordinary_molecular_sequence_selector(O,
        dict(subject_ref=sheet["inputs"]["input_ref"] or "engineering-O",
            **sheet["parameters"]["requested_with_defaults"], rows=rows))
    return contracts.select_stored_molecular_sequence_values(operation=O, sheet=sheet, components=components,
        selection=selection, source_files=sources)


def test_three_operations_require_exact_unique_selected_ordinal(selected_call):
    call, _ = _o_call(selected_call)
    resources, environments = _configuration(call)
    configuration = tools.normalize_molecular_sequence_configuration(resources, environments, call["policy"])
    assert [row["operation"] for row in configuration["bindings"]] == [ORF, N, O]
    assert tools.compile_ordinary_molecular_sequence_selection(configuration, operation=O)["deployment"]["version"] == native.DEPLOYMENT_VERSION_V2
    assert configuration["bindings"][2]["binding_ordinal_0based"] == 2
    wrong = deepcopy(environments)
    wrong[2]["binding_ordinal_0based"] = 1
    with pytest.raises(ValueError):
        tools.normalize_molecular_sequence_configuration(resources, wrong, call["policy"])
    with pytest.raises(ValueError):
        tools.normalize_molecular_sequence_configuration(resources, [*environments, environments[2]], call["policy"])
    assert O in tools.molecular_sequence_tool_catalog(configuration)
    assert tools.molecular_sequence_tool_catalog(None) == {}


@pytest.mark.parametrize("field,value", [("version", native.DEPLOYMENT_VERSION), ("source", "0" * 64)])
def test_o_deployment_v2_and_glyco_source_pin_precede_reservation(selected_call, field, value):
    call, calls = _o_call(selected_call)
    if field == "source":
        call["selected"]["deployment"]["module"]["sha256"] = value
    else:
        call["selected"]["deployment"]["version"] = value
    with pytest.raises(ValueError):
        ordinary.prepare_ordinary_molecular_sequence_attempt(operation=O, **call)
    assert calls == []


@pytest.mark.parametrize("key,item", [("window", True), ("window", 3.5), ("window", "3"),
    ("min_st_fraction", True), ("min_st_fraction", float("inf")), ("min_st_fraction", float("nan")),
    ("disallow_proline_next", 1), ("disallow_proline_next", None)])
def test_o_arguments_require_strict_types_and_finite_threshold(key, item):
    arguments = dict(subject_ref="selected-protein", **PARAMETERS, rows=[])
    arguments[key] = item
    with pytest.raises(ValueError):
        contracts.validate_ordinary_molecular_sequence_arguments(O, arguments)


@pytest.mark.parametrize("extra", [{"window": 3}, {"min_st_fraction": .2},
    {"disallow_proline_next": False}, {"subject_ref": "other"}, {"allow_overlap": True}])
def test_o_saved_modes_cannot_replace_scan_parameters(extra):
    with pytest.raises(ValueError):
        contracts.validate_ordinary_molecular_sequence_arguments(O,
            dict(mode="calculate_saved", result_ref="source_" + "a" * 24, rows=[], **extra))


def test_real_o_action_keeps_requested_window_and_source_only_registered_form(o_boundary):
    value = o_boundary
    assert hashlib.sha256(STP_LOG.encode()).hexdigest() == "d7e33970da8e2a0c544a144cc8d4196e04d0353052b81e9f6bf2a54658c919cc"
    before = set(value.flow.receipts.known(value.caller.source.episode_id))
    public = _seed(value)["result"]
    assert value.models == ["protein"]
    assert value.frozen["sequence"].encode("ascii") == value.store.get_artifact(value.subject["sequence_ref"])
    assert value.frozen["parent_mapping"] == value.store.sequence_mapping(value.subject["id"])
    request = value.prepared["plan"]["selection"]["driver_request"]
    assert request["selection"]["version"] == native.REQUEST_VERSION_V2
    assert request["selection"]["arguments"] == dict(sequence="STP", **PARAMETERS)
    assert value.sheet["parameters"]["requested_with_defaults"]["window"] == 2
    assert value.sheet["parameters"]["effective"]["window"] == 7
    assert _cell(public, "st_count")["value"] == 2 and _cell(public, "window_denominator_symbols")["value"] == 3
    assert _cell(public, "native_st_fraction")["value"] == .667
    assert _cell(public, "native_st_fraction_token")["value"] == "0.667"
    assert _cell(public, "calculated_st_fraction")["value"] == 2 / 3
    assert public["values"]["schema"] == "molecular_sequence_selected_values_v3"
    context = public["values"]["context"]
    assert context["schema"] == "o_glycosylation_public_context_v1"
    assert context["parameters"]["supplied_window"]["value"] == 2
    assert context["parameters"]["requested_window"]["value"] == 2
    assert context["parameters"]["effective_window"]["value"] == 7
    assert context["parameters"]["source_default_window"]["value"] == 7
    assert context["parameters"]["supplied_min_st_fraction"]["value"] == .4
    assert context["parameters"]["supplied_disallow_proline_next"]["value"] is True
    assert context["native"]["selected_metadata"]["value"]["sequence"] == dict(
        sequence_length=3, window=7, threshold_token="0.4", threshold=.4)
    assert _cell(public, "source_intervals")["value"] == value.components["rows"][0]["cells"]["source_intervals"]
    assert _cell(public, "window_source_intervals")["value"] == value.components["rows"][0]["cells"]["window_source_intervals"]
    assert _cell(public, "processed_interval")["value"] == [0, 1]
    assert _cell(public, "native_window_interval")["value"] == [0, 3]
    assert _cell(public, "expected_clipped_window_interval")["value"] == [0, 3]
    for name in ("st_count", "window_denominator_symbols"):
        assert _cell(public, name)["denominators"] == []
    for name in ("native_st_fraction", "calculated_st_fraction", "source_rounded_st_fraction"):
        numerator, denominator = _cell(public, name)["denominators"]
        assert (numerator["kind"], numerator["value"], numerator["unit"]) == ("numerator", 2, "symbols")
        assert (denominator["kind"], denominator["value"], denominator["unit"]) == ("denominator", 3, "symbols")
        assert type(numerator["value"]) is type(denominator["value"]) is int
    assert value.prepared["binding"]["version"] == "ordinary_o_glycosylation_attempt_binding_v1"
    known = set(value.flow.receipts.known(value.caller.source.episode_id))
    assert known - before == {public["source_ref"]} and value.subject["sequence_ref"] in known
    source = value.store.get(public["source_ref"])
    assert source["request_ref"] not in known and source["artifact_ref"] not in known
    assert value.subject["sequence_ref"] not in source["auxiliary_artifact_refs"]
    group = contracts.ordinary_molecular_sequence_fact_sources(O)["o_glycosylation_hotspot_outcomes"]["report_schema"]
    Draft202012Validator(group["items"]).validate(public)
    schema = dict(type="object", properties={"hotspots": group}, required=["hotspots"], additionalProperties=False)
    calls = []
    actual = value.flow.resolver(value.caller.source.scope, source=value.caller.source)
    def resolver(reference, namespace):
        calls.append((reference, namespace))
        return actual(reference, namespace)
    assert validate_form({"hotspots": [public]}, schema, resolver) == {"hotspots": [public]}
    assert calls == [(public["source_ref"], "source")] and len(value.calls) == 1


def test_o_saved_only_reads_and_once_calculation_need_no_original_bytes(o_boundary, monkeypatch):
    value = o_boundary
    public = _seed(value)["result"]
    original = public["source_ref"]
    shutil.rmtree(Path(value.prepared["handle_path"]).parent)
    shutil.rmtree(Path(value.call["selected"]["software"]["python_home"]))
    retained_native_file(value.store, value.frozen["input_file"]).unlink()
    monkeypatch.setattr(value.registry, "_prepare_molecular_sequence_operand", _forbidden)
    monkeypatch.setattr(ordinary, "prepare_ordinary_molecular_sequence_attempt", _forbidden)
    monkeypatch.setattr(ordinary, "run_ordinary_molecular_sequence_attempt", _forbidden)
    calculator, calls = glyco.calculate_glycosylation_components, []
    def once(sheet):
        calls.append(deepcopy(sheet))
        return calculator(sheet)
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", once)
    read = _dispatch(value, dict(mode="read_stored", result_ref=original, rows=_rows()), 1)
    assert read["result"] == public and read["changed_record_refs"] == [] and calls == []
    calculated = _dispatch(value, dict(mode="calculate_saved", result_ref=original, rows=_rows()), 2)
    assert calls == [value.sheet] and calculated["result"]["source_ref"] != original
    assert calculated["result"]["values"]["source_sheet_ref"] == public["values"]["source_sheet_ref"]
    assert _cell(calculated["result"], "calculated_st_fraction")["value"] == 2 / 3
    before = _tables(value.store)
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", _forbidden)
    cached = asyncio.run(value.flow.execute(value.caller.source, O,
        dict(mode="calculate_saved", result_ref=original, rows=_rows()), decision_index=2,
        operation_key=f"{value.flow.run_id}:{value.caller.source.episode_id}:2"))
    assert cached == {key: item for key, item in calculated.items() if key != "pending_work_after_action"}
    assert _tables(value.store) == before and len(value.calls) == 1


def test_o_unknown_saved_start_marker_never_reissues(o_boundary, monkeypatch):
    value = o_boundary
    reference = _seed(value)["result"]["source_ref"]
    class Interrupted(BaseException):
        pass
    calls = []
    def interrupted(sheet):
        calls.append(True)
        raise Interrupted()
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", interrupted)
    arguments = dict(mode="calculate_saved", result_ref=reference, rows=[])
    with pytest.raises(Interrupted):
        _dispatch(value, arguments, 1)
    key = f"{value.flow.run_id}:{value.caller.source.episode_id}:1"
    directory = value.registry.molecular_sequence_results_for(value.flow.run_id).action_directory(value.caller.source.episode_id, key)
    assert (directory / "ordinary-calculation-started.json").is_file()
    assert not (directory / "ordinary-calculation-result.json").exists()
    with pytest.raises(MolecularOperationUnpublished):
        _dispatch(value, arguments, 1)
    assert calls == [True] and value.flow.journal.row("runtime_actions", value.caller.source.episode_id, 1)["result"] is None


@pytest.mark.parametrize("document", ["sheet", "components"])
def test_o_projection_rejects_n_document_with_shared_scientific_tags(tmp_path, document):
    with Store(tmp_path / "store") as store:
        sheet = glyco.build_glycosylation_sheet(O, STP_LOG, sequence="STP", parameters=PARAMETERS)
        components = glyco.calculate_glycosylation_components(sheet)
        if document == "sheet":
            sheet["inputs"]["operation"] = N
        else:
            components["operation"] = N
        with pytest.raises(ValueError):
            _project(store, sheet, components, [])


def test_o_wrong_n_sheet_rejects_before_saved_calculator_or_start(o_boundary, monkeypatch):
    value = o_boundary
    def wrong(sheet, components):
        sheet["inputs"]["operation"] = N
    value.alter = wrong
    reference = _seed(value)["result"]["source_ref"]
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", _forbidden)
    with pytest.raises(ActionFailure):
        _dispatch(value, dict(mode="calculate_saved", result_ref=reference, rows=[]), 1)
    owner = value.registry.molecular_sequence_results_for(value.flow.run_id)
    directory = owner.action_directory(value.caller.source.episode_id,
        f"{value.flow.run_id}:{value.caller.source.episode_id}:1")
    assert not (directory / "ordinary-calculation-started.json").exists()
    assert len(value.calls) == 1


def test_o_unreceived_reference_is_denied_before_sequence_bytes(o_boundary, monkeypatch, tmp_path):
    from tests.test_orf_sequence_operand import _external

    value = o_boundary
    flow, caller, provider = _caller(value.store, value.registry, value.resources, value.environments,
        tmp_path / "unreceived-subject", "engineering-unreceived-o-subject", [])
    _source, reference = _external(value.store, sequence="STP")
    assert value.store.reference_subset([reference["id"]], caller.source.scope) == [reference["id"]]
    assert reference["id"] not in flow.receipts.known(caller.source.episode_id)
    monkeypatch.setattr(value.registry, "_prepare_molecular_sequence_operand", _forbidden)
    monkeypatch.setattr(ordinary, "prepare_ordinary_molecular_sequence_attempt", _forbidden)
    foreign = SimpleNamespace(flow=flow, caller=caller)
    with pytest.raises(ActionFailure):
        _dispatch(foreign, dict(subject_ref=reference["id"], **PARAMETERS, rows=[]), 0)
    outcome = json.loads(flow.journal.row("runtime_actions", caller.source.episode_id, 0)["result"])
    assert outcome["status"] == "invalid" and outcome["record_refs"] == []
    assert value.frozen is None and value.calls == [] and provider.contexts == []


def test_o_retained_rounding_threshold_crossing_uses_existing_calculator(tmp_path):
    assert hashlib.sha256(ASA_LOG.encode()).hexdigest() == "96381625cf643be941e50b1ccd9c46d6f2ecc3bcf6bcb00c7afe2081fc5aad05"
    excluded = o_log(3, 0, window=3, threshold=.3334)
    assert hashlib.sha256(excluded.encode()).hexdigest() == "bbad1d65b472aa2b6c03b832bcc0de3f78537f480827d2ac8d420b78dec81d2d"
    with Store(tmp_path / "store") as store:
        for threshold, log, count in ((.3333, ASA_LOG, 1), (.3334, excluded, 0)):
            sheet = glyco.build_glycosylation_sheet(O, log, sequence="ASA",
                parameters=dict(window=3, min_st_fraction=threshold, disallow_proline_next=True))
            components = glyco.calculate_glycosylation_components(sheet)
            assert components["summary"]["native_reported_total_count"] == count
            if count:
                cell = components["rows"][0]["cells"]
                assert cell["st_count"] == 1 and cell["window_denominator_symbols"] == 3
                assert cell["calculated_st_fraction"] == 1 / 3 and cell["source_rounded_st_fraction"] == .333
                assert cell["unrounded_threshold_satisfied"] is True
            rows = _rows() if count else []
            projection = _project(store, sheet, components, rows)
            assert projection["public"]["context"]["parameters"]["effective_min_st_fraction"]["value"] == threshold
            assert projection["public"]["context"]["native"]["selected_metadata"]["value"]["total"] == {"total_count": count}


def test_o_next_p_filter_and_distinct_centers_share_actual_clipped_window():
    for disallow, count in ((True, 1), (False, 2)):
        rows = ["- pos 1 (S): S/T fraction=0.667 in window 1-3"]
        if not disallow:
            rows.append("- pos 2 (T): S/T fraction=0.667 in window 1-3")
        log = o_log(3, count, rows)
        sheet = glyco.build_glycosylation_sheet(O, log, sequence="STP",
            parameters=dict(window=7, min_st_fraction=.4, disallow_proline_next=disallow))
        components = glyco.calculate_glycosylation_components(sheet)
        assert len(components["rows"]) == count
        assert components["rows"][0]["cells"]["processed_interval"] == [0, 1]
        if not disallow:
            first, second = components["rows"]
            assert [first["row_ordinal"], second["row_ordinal"]] == [0, 1]
            assert second["cells"]["processed_interval"] == [1, 2]
            assert first["cells"]["native_window_interval"] == second["cells"]["native_window_interval"] == [0, 3]
            assert second["cells"]["following_proline"] is True and second["cells"]["following_proline_allowed"] is True


def test_o_window_counts_preserve_noncanonical_symbols_and_missing_mapping(tmp_path):
    log = o_log(4, 2, ["- pos 1 (S): S/T fraction=0.5 in window 1-4",
        "- pos 4 (T): S/T fraction=0.5 in window 1-4"])
    sheet = glyco.build_glycosylation_sheet(O, log, sequence="SX?T", parameters=dict(
        window=7, min_st_fraction=.4, disallow_proline_next=False), input_mapping=None)
    components = glyco.calculate_glycosylation_components(sheet)
    with Store(tmp_path / "store") as store:
        fields = ["window_symbols", "window_symbol_counts", "st_count", "window_denominator_symbols",
            "source_intervals", "window_source_intervals"]
        projection = _project(store, sheet, components,
            [dict(row_id={"kind": "glycosylation_site", "row_ordinal": 0}, fields=fields)])
        public = {"values": projection["public"]}
        assert _cell(public, "window_symbols")["value"] == "SX?T"
        assert _cell(public, "window_symbol_counts")["value"] == {"S": 1, "X": 1, "?": 1, "T": 1}
        assert _cell(public, "st_count")["value"] == 2 and _cell(public, "window_denominator_symbols")["value"] == 4
        for name in ("source_intervals", "window_source_intervals"):
            assert _cell(public, name)["value"] is None and _cell(public, name)["value_state"] == "stored_null"
        assert projection["public"]["context"]["mapping"]["reason"]["value"] == "not_supplied"


def test_o_malformed_duplicate_rows_keep_original_ordinals(tmp_path):
    log = o_log(4, 4, ["malformed retained line", "- pos 1 (S): S/T fraction=1.0 in window 1-2",
        "- pos 1 (S): S/T fraction=1.0 in window 1-2", "- pos 3 (S): S/T fraction=1.0 in window 2-4"],
        window=3, threshold=0)
    sheet = glyco.build_glycosylation_sheet(O, log, sequence="SSSS", parameters=dict(
        window=3, min_st_fraction=0, disallow_proline_next=False))
    components = glyco.calculate_glycosylation_components(sheet)
    with Store(tmp_path / "store") as store:
        rows = [dict(row_id={"kind": "glycosylation_site", "row_ordinal": i},
            fields=["row_ordinal", "native_line", "order_compatible"]) for i in (3, 1, 2, 0)]
        selected = _project(store, sheet, components, rows)["public"]
        assert [row["row_id"]["row_ordinal"] for row in selected["rows"][::3]] == [3, 1, 2, 0]
        assert components["rows"][0]["native_values"] is None
        assert components["rows"][2]["cells"]["order_compatible"] is False
        assert [row["row_ordinal"] for row in selected["context"]["row_issues"]] == [0, 1, 2, 3]
        assert len(components["rows"]) == 4 and components["summary"]["malformed_row_count"] == 1


@pytest.mark.parametrize("log,outcome,total,printed,status", [(None, "completed", None, None, "partial"),
    ("", "completed", None, 0, "partial"), (o_log(3, 0), "completed", 0, 0, "complete"),
    (None, "failed", None, None, "failed")])
def test_o_empty_selection_keeps_missing_empty_zero_and_failure_distinct(tmp_path, log, outcome, total, printed, status):
    sheet = glyco.build_glycosylation_sheet(O, log, sequence="AAA", parameters=dict(
        window=7, min_st_fraction=.4, disallow_proline_next=True), native_outcome=outcome)
    components = glyco.calculate_glycosylation_components(sheet)
    assert components["summary"]["native_reported_total_count"] == total
    assert components["summary"]["retained_printed_row_count"] == printed
    with Store(tmp_path / "store") as store:
        public = _project(store, sheet, components, [])["public"]
        assert public["rows"] == [] and public["context"]["component_status"]["value"] == status
        assert public["context"]["input"]["native_outcome"]["value"] == outcome


def test_o_out_of_domain_threshold_is_qualified_native_zero(tmp_path):
    log = o_log(1, 0, threshold=2)
    assert hashlib.sha256(log.encode()).hexdigest() == "8a1d8c492d5d2eef20c2f59c2e209306460e17dc7271e3139a219782c398d314"
    arguments = dict(subject_ref="selected-protein", window=7, min_st_fraction=2, disallow_proline_next=True, rows=[])
    assert contracts.validate_ordinary_molecular_sequence_arguments(O, arguments) == arguments
    sheet = glyco.build_glycosylation_sheet(O, log, sequence="S", parameters={k: arguments[k] for k in PARAMETERS})
    components = glyco.calculate_glycosylation_components(sheet)
    with Store(tmp_path / "store") as store:
        public = _project(store, sheet, components, [])["public"]
        assert public["context"]["parameters"]["effective_min_st_fraction"]["value"] == 2
        issues = public["context"]["component_issues"]["value"]
        assert any(row["code"] == "glycosylation_threshold_outside_documented_domain" for row in issues)
        assert components["summary"]["native_reported_total_count"] == 0 and components["status"] == "partial"


@pytest.mark.parametrize("o_boundary", [dict(sequence="S" * 105,
    parameters=dict(window=3, min_st_fraction=0, disallow_proline_next=False), rows=[],
    log=o_log(105, 105, [f"- pos {i} (S): S/T fraction=1.0 in window {max(1, i-1)}-{min(105, i+1)}"
        for i in range(1, 101)], window=3, threshold=0, remaining=5)),
    dict(sequence="AAA", log=None, outcome="failed", rows=[])], indirect=True)
def test_o_actual_saved_empty_view_retains_global_partial_status(o_boundary):
    value = o_boundary
    original = _seed(value)
    public = original["result"]
    assert public["values"]["rows"] == []
    assert public["values"]["context"]["component_status"]["value"] in ("partial", "failed")
    read = _dispatch(value, dict(mode="read_stored", result_ref=public["source_ref"], rows=[]), 1)
    assert read["status"] == "partial"
    if value.outcome == "completed":
        assert read["result"]["failures"] == []
    calculated = _dispatch(value, dict(mode="calculate_saved", result_ref=public["source_ref"], rows=[]), 2)
    assert calculated["status"] == "partial" and calculated["result"]["values"]["rows"] == []
    if value.log is not None:
        assert value.components["summary"]["native_reported_total_count"] == 105
        assert value.components["summary"]["retained_printed_row_count"] == 100
        assert value.components["summary"]["unretained_reported_row_count"] == 5
    assert len(value.calls) == 1


def test_o_v4_does_not_widen_n_v3_or_legacy_selectors():
    rows = [dict(row_id={"kind": "glycosylation_site", "row_ordinal": 0}, fields=["window_symbols"])]
    for version, operation in ((contracts.N_SELECTOR_VERSION, N), (contracts.SELECTOR_VERSION, O)):
        with pytest.raises(ValueError):
            contracts.validate_molecular_sequence_result_selector(dict(version=version, mode=contracts.MODES[0],
                operation=operation, saved_sheet_ref=None, rows=rows, return_files=[]))
    with pytest.raises(ValueError):
        contracts.validate_molecular_sequence_result_selector(dict(version=contracts.O_SELECTOR_VERSION,
            mode=contracts.MODES[0], operation=N, saved_sheet_ref=None, rows=[], return_files=[]))


def test_o_pending_saved_selection_rejects_later_source_receipt(o_boundary, monkeypatch):
    value = o_boundary
    receive = value.flow.receive_outcome
    def stop_delivery(source, selection, result, index):
        assert index == 5
        raise MolecularOperationUnpublished("engineering_O_stop_after_publication_before_receipt")
    monkeypatch.setattr(value.flow, "receive_outcome", stop_delivery)
    with pytest.raises(MolecularOperationUnpublished):
        _dispatch(value, value.arguments, 5)
    row = value.flow.journal.row("runtime_actions", value.caller.source.episode_id, 5)
    original = json.loads(row["result"])
    reference = original["result"]["source_ref"]
    assert reference not in value.flow.receipts.known(value.caller.source.episode_id)
    owner = value.registry.molecular_sequence_results_for(value.flow.run_id)
    prepare = owner.prepare_ordinary_molecular_sequence_saved
    def stop_prepare(*args, **kwargs):
        raise MolecularOperationUnpublished("engineering_O_stop_before_admission")
    monkeypatch.setattr(owner, "prepare_ordinary_molecular_sequence_saved", stop_prepare)
    arguments = dict(mode="read_stored", result_ref=reference, rows=[])
    with pytest.raises(MolecularOperationUnpublished):
        _dispatch(value, arguments, 2)
    pending = value.flow.journal.row("runtime_actions", value.caller.source.episode_id, 2)
    assert pending["result"] is None
    monkeypatch.setattr(value.flow, "receive_outcome", receive)
    monkeypatch.setattr(owner, "prepare_ordinary_molecular_sequence_saved", prepare)
    assert _dispatch(value, value.arguments, 5) == original
    assert reference in value.flow.receipts.known(value.caller.source.episode_id)
    monkeypatch.setattr(owner, "_ordinary_value", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.molecular_measurement_tools._publication_bytes", _forbidden)
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", _forbidden)
    with pytest.raises(ActionFailure):
        _dispatch(value, arguments, 2)
    assert value.flow.journal.row("runtime_actions", value.caller.source.episode_id, 2)["action"] == pending["action"]
    directory = owner.action_directory(value.caller.source.episode_id,
        f"{value.flow.run_id}:{value.caller.source.episode_id}:2")
    assert not (directory / "ordinary-source-admission.json").exists()
    assert not (directory / "ordinary-calculation-started.json").exists()
    assert len(value.calls) == 1


@pytest.mark.parametrize("mutation", ["swapped_kinds", "wrong_unit", "unit_sources", "count_bool", "count_float"])
def test_o_ratio_operands_reject_mutated_kind_unit_and_count_types(tmp_path, mutation):
    sheet = glyco.build_glycosylation_sheet(O, STP_LOG, sequence="STP", parameters=PARAMETERS)
    components = glyco.calculate_glycosylation_components(sheet)
    with Store(tmp_path / "store") as store:
        public = _project(store, sheet, components, _rows())["public"]
        row = next(row for row in public["rows"] if row["field"] == "calculated_st_fraction")
        first, second = row["denominators"]
        if mutation == "swapped_kinds":
            first["kind"], second["kind"] = second["kind"], first["kind"]
        elif mutation == "wrong_unit":
            second["unit"] = "probability"
        elif mutation == "unit_sources":
            first["unit_sources"] = [{key: first[key] for key in
                ("value_state", "value", "source_ref", "source_pointer", "source_state")}]
            first["unit_sources"][0]["value"] = "symbols"
        else:
            first["value"] = True if mutation == "count_bool" else 2.0
        with pytest.raises(ValueError):
            contracts.validate_molecular_sequence_fact_values(contracts.PROJECTION_SOURCE, [public])


def test_o_valid_sheet_recovers_independently_invalid_components_once(o_boundary, monkeypatch):
    value = o_boundary
    def wrong_components(sheet, components):
        components["operation"] = N
    value.alter = wrong_components
    original = _seed(value)
    assert original["status"] == "partial"
    reference = original["result"]["source_ref"]
    source = value.store.get(reference)
    packet = value.store.get_artifact(source["artifact_ref"])
    calculator, calls = glyco.calculate_glycosylation_components, []
    def once(sheet):
        calls.append(deepcopy(sheet))
        return calculator(sheet)
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", once)
    derived = _dispatch(value, dict(mode="calculate_saved", result_ref=reference, rows=_rows()), 1)
    assert calls == [value.sheet] and derived["result"]["source_ref"] != reference
    assert _cell(derived["result"], "calculated_st_fraction")["value"] == 2 / 3
    assert value.store.get(reference) == source and value.store.get_artifact(source["artifact_ref"]) == packet
    assert json.loads(value.flow.journal.row("runtime_actions", value.caller.source.episode_id, 0)["result"]) == original
    assert len(value.calls) == 1


def test_o_unreceived_source_denies_private_bytes_and_saved_work(o_boundary, monkeypatch, tmp_path):
    value = o_boundary
    reference = _seed(value)["result"]["source_ref"]
    flow, caller, provider = _caller(value.store, value.registry, value.resources, value.environments,
        tmp_path / "unreceived-source", "engineering-unreceived-o-source", [])
    assert reference not in flow.receipts.known(caller.source.episode_id)
    owner = value.registry.molecular_sequence_results_for(flow.run_id)
    monkeypatch.setattr(value.store, "get_artifact", _forbidden)
    monkeypatch.setattr(owner, "_ordinary_value", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.molecular_measurement_tools._publication_bytes", _forbidden)
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", _forbidden)
    with pytest.raises(ActionFailure):
        _dispatch(SimpleNamespace(flow=flow, caller=caller), dict(mode="read_stored", result_ref=reference, rows=[]), 0)
    outcome = json.loads(flow.journal.row("runtime_actions", caller.source.episode_id, 0)["result"])
    assert outcome["status"] == "invalid" and outcome["record_refs"] == [] and outcome["result"] is None
    assert len(value.calls) == 1 and provider.contexts == []


def test_o_same_key_cache_reauthenticates_control_without_new_receipts(o_boundary, monkeypatch):
    value = o_boundary
    original = _seed(value)
    source = value.store.get(original["result"]["source_ref"])
    metadata = value.store.get(source["request_ref"])
    file = dict(artifact_ref=source["request_ref"], sha256=metadata["sha256"], size_bytes=metadata["size"],
        format=contracts.ordinary_molecular_sequence_profile(O)["custody_version"])
    path = retained_native_file(value.store, file)
    raw, mode = path.read_bytes(), path.stat().st_mode
    before = _tables(value.store)
    known = list(value.flow.receipts.known(value.caller.source.episode_id))
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", _forbidden)
    monkeypatch.setattr(ordinary, "prepare_ordinary_molecular_sequence_attempt", _forbidden)
    try:
        path.chmod(mode | 0o200)
        path.write_bytes(b"[" + raw[1:])  # Intentional same-size corruption of owned test control only.
        with pytest.raises(ValueError):
            asyncio.run(value.flow.execute(value.caller.source, O, value.arguments, decision_index=0,
                operation_key=f"{value.flow.run_id}:{value.caller.source.episode_id}:0"))
    finally:
        path.write_bytes(raw)
        path.chmod(mode)
    assert _tables(value.store) == before
    assert list(value.flow.receipts.known(value.caller.source.episode_id)) == known and len(value.calls) == 1


def test_o_unavailable_components_keep_available_native_header_and_unknown_rows(tmp_path):
    sheet = glyco.build_glycosylation_sheet(O, STP_LOG, sequence="STP", parameters=PARAMETERS)
    with Store(tmp_path / "store") as store:
        sources = {role: contracts.empty_file_state("not_requested") for role in contracts.FILE_ROLES}
        sources["sheet"] = _retained(store, sheet)
        selection = contracts.ordinary_molecular_sequence_selector(O,
            dict(subject_ref="engineering-O", **PARAMETERS, rows=[]))
        public = contracts.select_stored_molecular_sequence_values(operation=O, sheet=sheet, components=None,
            selection=selection, source_files=sources)["public"]
        assert public["rows"] == [] and public["context"]["row_issues"] is None
        assert public["context"]["component_status"]["value_state"] != "stored_value"
        assert public["context"]["native"]["selected_metadata"]["value"]["total"] == {"total_count": 1}


def test_n_registered_schema_matches_actual_pre_o_parent_contract():
    # Actual473 proof ed2a1cf1…: /calls/1/context/requested_form/properties/measurements.
    # Keep this required expectation here; no dated run is read by the test.
    schema = contracts.ordinary_molecular_sequence_fact_sources(N)["n_glycosylation_motif_outcomes"]["report_schema"]
    encoded = json.dumps(schema, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    assert hashlib.sha256(encoded).hexdigest() == "82a0195218c53b90b7e5f7b3e1a293151a8c50ae4861c99a31b769bb5e51537b"
