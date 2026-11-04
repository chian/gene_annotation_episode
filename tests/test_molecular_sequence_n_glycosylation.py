"""Engineered ordinary N boundary controls; no current native science.

The literal overlap log is copied byte-exact from retained227's authenticated
whole-source report201d130ce7880db9ad0e66267ce5beaaa9a9aeee03df3a05f01c802f5acd6bf3.
The fake lifecycle below is explicitly an engineering observation, never an
assertion that this test executed that historical source or another scan.
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
from gene_annotation_episode.runtime import ActionFailure, Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from tests.test_glycosylation_measurements import n_log
from tests.test_molecular_sequence_ordinary import selected_call, _lifecycle, _metadata_fixture, _pin, _write
from tests.test_molecular_sequence_tools_native import _controller, _credit
from tests.test_runtime import ScriptedProvider


N = "find_n_glycosylation_motifs"
ORF = contracts.ORDINARY_ORF_TOOL
OVERLAP_LOG = ("# N-linked glycosylation sequon scan (N-X-[S/T], X≠P)\n"
    "Sequence length: 4\nTotal sequons found: 2\n\nPositions (1-based):\n- 1: NNS\n- 2: NST")
OVERLAP_LOG_SHA256 = "e356ae4fa7e04c01f7f7337d490b8bf13bdc284db10a154d84f1501628457f20"


def _forbidden(*args, **kwargs):
    raise AssertionError("engineering boundary must not execute this port")


def _rows():
    return [dict(row_id={"kind": "summary"}, fields=["original_symbol_count",
        "native_reported_total_count", "retained_printed_row_count", "usable_checked_row_count",
        "native_report_complete", "scan_exhaustiveness_verified"]),
        dict(row_id={"kind": "glycosylation_site", "row_ordinal": 0}, fields=["motif",
            "position_1based", "processed_interval", "source_intervals", "literal_sequon"]),
        dict(row_id={"kind": "glycosylation_site", "row_ordinal": 1}, fields=["motif"])]


def _n_call(selected_call):
    original, calls = selected_call
    call = {key: value if key in ("context", "policy") else deepcopy(value)
        for key, value in original.items()}
    profile = contracts.ordinary_molecular_sequence_profile(N)
    call["arguments"] = dict(subject_ref=call["frozen_operand"]["subject"]["id"],
        allow_overlap=True, rows=_rows())
    call["frozen_operand"]["version"] = profile["operand_version"]
    deployment = call["selected"]["deployment"]
    deployment["version"] = native.DEPLOYMENT_VERSION_V2
    deployment["module"]["sha256"] = native.GLYCO_SOURCE_SHA256
    return call, calls


def _configuration(call):
    selected = call["selected"]
    n_binding = dict(version=tools.BINDING_VERSION, operation=N,
        deployment=deepcopy(selected["deployment"]), software=deepcopy(selected["software"]))
    orf_binding = deepcopy(n_binding)
    orf_binding["operation"] = ORF
    orf_binding["deployment"]["version"] = native.DEPLOYMENT_VERSION
    orf_binding["deployment"]["module"]["sha256"] = native.SOURCE_SHA256
    resources = {"explicit-mixed": dict(kind="local", workspace=selected["workspace"],
        policy=deepcopy(ordinary.POLICY), native_molecular_sequence=[orf_binding, n_binding])}
    environments = [dict(operation=N, resource_id="explicit-mixed", binding_ordinal_0based=1,
        environment=deepcopy(ordinary.ENVIRONMENT_SELECTION))]
    return resources, environments


def _retained(store, document):
    raw = (canonical(document) + "\n").encode()
    reference = store.artifact(raw, "application/json")
    file = dict(artifact_ref=reference, sha256=hashlib.sha256(raw).hexdigest(),
        size_bytes=len(raw), format=document["schema"])
    return dict(state="retained", file=file, declared=None,
        observed_identity={k: file[k] for k in ("sha256", "size_bytes")}, failure=None)


def _projection(store, sheet, components, rows):
    sources = {role: contracts.empty_file_state("not_requested") for role in contracts.FILE_ROLES}
    sources["sheet"], sources["components"] = _retained(store, sheet), _retained(store, components)
    selection = contracts.ordinary_molecular_sequence_selector(N,
        dict(subject_ref=sheet["inputs"]["input_ref"] or "engineering-input", allow_overlap=True, rows=rows))
    return contracts.select_stored_molecular_sequence_values(operation=N, sheet=sheet,
        components=components, selection=selection, source_files=sources)


def _cell(public, field, ordinal=None):
    return next(row for row in public["rows"] if row["field"] == field
        and (ordinal is None or row["row_id"].get("row_ordinal") == ordinal))


def _tables(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: sorted([tuple(row) for row in store.db.execute('SELECT * FROM "' +
        name.replace('"', '""') + '"')], key=repr) for name in names}


def _caller(store, registry, resources, environments, directory, run_id, initial):
    directory.mkdir(parents=True, exist_ok=True)
    factory = ExecutionServiceFactory(resources=resources, initial_information={}, handoff_unit=1,
        acquired_record_unit=1, monitoring_information_unit=1,
        molecular_sequence_environments=tuple(environments), molecular_sequence_saved_modes=True)
    application = factory(store, run_id=run_id, directory=directory, tool_registry=registry)
    provider = ScriptedProvider([])
    provider.complete = _forbidden
    flow = Workflow(store, registry, provider, directory, run_id, _controller, _credit,
        project_child_credit=_credit, root_role="improvement",
        episode_binding_descriptors=application.episode_binding_descriptors,
        role_credit_bindings=application.role_credit_bindings,
        job_progress_provider=application.job_progress_provider,
        episode_record_receipts=True, initial_known_record_refs=initial)
    caller = flow.build("improvement", "caller", "Read the selected retained N candidate motifs and their original overlap meaning.",
        store.validate_scope())
    return flow, caller, provider


def _dispatch(value, arguments, index):
    selection = dict(kind="tool", tool=N, arguments=deepcopy(arguments))
    asyncio.run(value.caller.source.execute(selection, index))
    row = value.flow.journal.row("runtime_actions", value.caller.source.episode_id, index)
    assert json.loads(row["action"]) == selection and row["result"] is not None
    return json.loads(row["result"])


def _engineered_roles(prepared, *, alter=None, log=OVERLAP_LOG, native_outcome="completed"):
    """Existing custody/bytes with an explicit not-started native observation."""
    bundle, declaration = _metadata_fixture(prepared)
    request = prepared["plan"]["selection"]["driver_request"]
    declaration["operation"] = N
    declaration["qualification"] = "engineered lifecycle; retained227 literal log; no current scanner invocation"
    operand = prepared["binding"]["frozen_operand"]
    arguments = prepared["binding"]["arguments"]
    sheet = glyco.build_glycosylation_sheet(N, log, sequence=operand["sequence"],
        parameters={"allow_overlap": arguments["allow_overlap"]}, input_ref=arguments["subject_ref"],
        input_mapping=operand["parent_mapping"], native_outcome=native_outcome)
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
def n_boundary(tmp_path, monkeypatch, selected_call, request):
    call, calls = _n_call(selected_call)
    options = getattr(request, "param", {})
    store = Store(tmp_path / "state")
    store.create_problem(raw_sequence=options.get("sequence", "nnst"), molecule="protein")
    scope = store.validate_scope()
    subject = store.get(scope["subject_refs"][0])
    registry = ToolRegistry(store, job_limits=deepcopy(ordinary.POLICY))
    resources, environments = _configuration(call)
    flow, caller, provider = _caller(store, registry, resources, environments, tmp_path / "run",
        "engineering-n-boundary", [subject["id"], subject["sequence_ref"]])
    value = SimpleNamespace(store=store, registry=registry, flow=flow, caller=caller, provider=provider,
        subject=subject, resources=resources, environments=environments, call=call, calls=calls,
        prepared=None, frozen=None, sheet=None, components=None, admissions=[], freezes=[], sequence_models=[],
        alter_documents=None, native_log=options.get("log", OVERLAP_LOG),
        native_outcome=options.get("native_outcome", "completed"),
        initial_arguments=dict(subject_ref=subject["id"], allow_overlap=options.get("allow_overlap", True),
            rows=deepcopy(options.get("rows", _rows()))))
    reader = flow.services.read_received_molecular_input
    def admission(*args, **kwargs):
        value.admissions.append((args[1], args[2], deepcopy(kwargs)))
        return reader(*args, **kwargs)
    monkeypatch.setattr(flow.services, "read_received_molecular_input", admission)
    sequence = registry._sequence
    def sequence_model(reference, *, molecule_model=None):
        value.sequence_models.append(molecule_model)
        return sequence(reference, molecule_model=molecule_model)
    monkeypatch.setattr(registry, "_sequence", sequence_model)
    freeze = registry._prepare_molecular_sequence_operand
    def freeze_after_admission(operation, subject_ref, *, scope):
        assert value.admissions and value.admissions[-1] == (subject_ref, "input", {"subject_metadata_only": True})
        frozen = freeze(operation, subject_ref, scope=scope)
        value.freezes.append(subject_ref)
        value.frozen = deepcopy(frozen)
        return frozen
    monkeypatch.setattr(registry, "_prepare_molecular_sequence_operand", freeze_after_admission)
    prepare = ordinary.prepare_ordinary_molecular_sequence_attempt
    def reserve(**kwargs):
        assert kwargs["operation"] == N and value.freezes
        assert not store.db.in_transaction
        value.prepared = prepare(**kwargs)
        value.sheet, value.components = _engineered_roles(value.prepared, alter=value.alter_documents,
            log=value.native_log, native_outcome=value.native_outcome)
        _lifecycle(monkeypatch, value.prepared, views=("returned",))
        return value.prepared
    monkeypatch.setattr(ordinary, "prepare_ordinary_molecular_sequence_attempt", reserve)
    monkeypatch.setattr(native, "execute_molecular_sequence_request", _forbidden)
    monkeypatch.setattr(ordinary.driver, "execute_molecular_sequence_request", _forbidden)
    monkeypatch.setattr(registry.clients, "_http", _forbidden)
    monkeypatch.setattr("socket.create_connection", _forbidden)
    monkeypatch.setattr(ordinary.native, "start_prepared", _forbidden)
    try:
        yield value
    finally:
        assert provider.contexts == []
        store.close()


def test_mixed_configuration_requires_explicit_matching_unique_operation_ordinal(selected_call):
    call, _ = _n_call(selected_call)
    resources, environments = _configuration(call)
    config = tools.normalize_molecular_sequence_configuration(resources, environments, call["policy"])
    selected = tools.compile_ordinary_molecular_sequence_selection(config, operation=N)
    assert selected["deployment"]["module"]["sha256"] == native.GLYCO_SOURCE_SHA256
    assert config["bindings"][0]["binding_ordinal_0based"] == 1
    with pytest.raises(ValueError):
        tools.compile_ordinary_orf_selection(config)
    both = [dict(operation=ORF, resource_id="explicit-mixed", binding_ordinal_0based=0,
        environment=deepcopy(ordinary.ENVIRONMENT_SELECTION)), *environments]
    config = tools.normalize_molecular_sequence_configuration(resources, both, call["policy"])
    assert [row["operation"] for row in config["bindings"]] == [ORF, N]
    for invalid in ([*environments, *environments], [{**environments[0], "binding_ordinal_0based": 0}]):
        with pytest.raises(ValueError):
            tools.normalize_molecular_sequence_configuration(resources, invalid, call["policy"])
    catalog = tools.molecular_sequence_tool_catalog(config, saved_modes=True)
    o = "predict_o_glycosylation_hotspots"
    assert set(catalog) == {ORF, N, o}
    # No O native binding was selected; explicit saved-mode setup exposes only
    # its retained-source operations, without borrowing an available deployment.
    saved_variants = catalog[o]["input_schema"]["anyOf"]
    assert {variant["properties"]["mode"]["const"] for variant in saved_variants} == {"read_stored", "calculate_saved"}
    assert all("subject_ref" not in variant["properties"] for variant in saved_variants)
    assert tools.molecular_sequence_tool_catalog(None) == {}


@pytest.mark.parametrize("change", ["v1", "wrong_source"])
def test_n_wrong_deployment_rejects_before_any_reservation(selected_call, change):
    call, calls = _n_call(selected_call)
    if change == "v1":
        call["selected"]["deployment"]["version"] = native.DEPLOYMENT_VERSION
    else:
        call["selected"]["deployment"]["module"]["sha256"] = native.SOURCE_SHA256
    with pytest.raises(ValueError):
        ordinary.prepare_ordinary_molecular_sequence_attempt(operation=N, **call)
    assert calls == [] and list(Path(call["selected"]["workspace"]).iterdir()) == []


@pytest.mark.parametrize("overlap", [0, 1, None, "false"])
def test_overlap_requires_explicit_strict_boolean(overlap):
    with pytest.raises(ValueError):
        contracts.validate_ordinary_molecular_sequence_arguments(N,
            dict(subject_ref="engineering-input", allow_overlap=overlap, rows=[]))


@pytest.mark.parametrize("override", [{"allow_overlap": False}, {"sequence": "NNST"},
    {"subject_ref": "engineering-input"}])
def test_saved_arguments_cannot_replace_scan_inputs_or_overlap(override):
    with pytest.raises(ValueError):
        contracts.validate_ordinary_molecular_sequence_arguments(N,
            dict(mode="calculate_saved", result_ref="source_" + "a" * 24, rows=[], **override))


def test_unreceived_reference_subject_never_reaches_freezer_or_native(n_boundary, monkeypatch, tmp_path):
    from tests.test_orf_sequence_operand import _external

    value = n_boundary
    flow, caller, provider = _caller(value.store, value.registry, value.resources, value.environments,
        tmp_path / "unreceived-subject-run", "engineering-unreceived-n-subject", [])
    foreign = SimpleNamespace(flow=flow, caller=caller)
    # Root scopes legitimately receive supplied input subjects. A later
    # external reference can be in scope without having been received.
    _source, reference = _external(value.store, sequence="NNST")
    assert value.store.reference_subset([reference["id"]], caller.source.scope) == [reference["id"]]
    assert reference["id"] not in set(flow.receipts.known(caller.source.episode_id))
    monkeypatch.setattr(value.registry, "_prepare_molecular_sequence_operand", _forbidden)
    monkeypatch.setattr(ordinary, "prepare_ordinary_molecular_sequence_attempt", _forbidden)
    arguments = dict(subject_ref=reference["id"], allow_overlap=True, rows=[])
    with pytest.raises(ActionFailure):
        _dispatch(foreign, arguments, 0)
    row = flow.journal.row("runtime_actions", caller.source.episode_id, 0)
    assert row is not None and json.loads(row["result"])["status"] == "invalid"
    assert value.calls == [] and value.freezes == [] and provider.contexts == []


def test_real_ordinary_action_preserves_stored_operand_and_source_only_n_return(n_boundary):
    value = n_boundary
    assert hashlib.sha256(OVERLAP_LOG.encode()).hexdigest() == OVERLAP_LOG_SHA256
    before = set(value.flow.receipts.known(value.caller.source.episode_id))
    outcome = _dispatch(value, dict(subject_ref=value.subject["id"], allow_overlap=True, rows=_rows()), 0)
    assert outcome["status"] == "partial"  # Current lifecycle is engineered/not-started.
    public = contracts.validate_ordinary_molecular_sequence_return(outcome["result"], operation=N)
    # Intake normalized the supplied material before this operation. The
    # operation must preserve its actual stored operand and File identity.
    assert value.store.get_artifact(value.subject["sequence_ref"]) == b"NNST"
    assert value.frozen["sequence"] == "NNST"
    assert value.sequence_models == ["protein"]
    assert value.frozen["input_file"]["artifact_ref"] == value.subject["sequence_ref"]
    assert value.frozen["input_file"]["sha256"] == hashlib.sha256(b"NNST").hexdigest()
    assert value.frozen["parent_mapping"] == value.store.sequence_mapping(value.subject["id"])
    request = value.prepared["plan"]["selection"]["driver_request"]
    assert request["version"] == "molecular_sequence_driver_request_v1"
    assert request["selection"]["version"] == "molecular_sequence_request_v2"
    assert request["selection"]["arguments"] == {"sequence": "NNST", "allow_overlap": True}
    assert request["scientific_context"] == dict(input_ref=value.subject["id"], input_mapping=value.frozen["parent_mapping"])
    assert outcome["record_refs"] == [public["source_ref"]]
    known = set(value.flow.receipts.known(value.caller.source.episode_id))
    assert known - before == {public["source_ref"]} and value.subject["sequence_ref"] in known
    source = value.store.get(public["source_ref"])
    assert source["request_ref"] not in known and source["artifact_ref"] not in known
    assert value.subject["sequence_ref"] not in source["auxiliary_artifact_refs"]
    assert public["values"]["schema"] == "molecular_sequence_selected_values_v2"
    assert _cell(public["values"], "motif", 0)["value"] == "NNS"
    assert _cell(public["values"], "motif", 1)["value"] == "NST"
    assert _cell(public["values"], "processed_interval", 0)["value"] == [0, 3]
    assert _cell(public["values"], "source_intervals", 0)["value"] == value.components["rows"][0]["cells"]["source_intervals"]
    assert _cell(public["values"], "native_reported_total_count")["population_id"] == "n_glyco_native_reported_sites"
    assert public["values"]["context"]["parameters"]["supplied_allow_overlap"]["value"] is True
    report_schema = contracts.ordinary_molecular_sequence_fact_sources(N)["n_glycosylation_motif_outcomes"]["report_schema"]
    Draft202012Validator(report_schema["items"]).validate(public)
    schema = dict(type="object", properties={"measurements": report_schema},
        required=["measurements"], additionalProperties=False)
    payload = {"measurements": [public]}
    resolved = []
    actual = value.flow.resolver(value.caller.source.scope, source=value.caller.source)
    def resolver(reference, namespace):
        resolved.append((reference, namespace))
        return actual(reference, namespace)
    assert validate_form(payload, schema, resolver) == payload
    assert resolved == [(public["source_ref"], "source")]
    assert len(value.calls) == 1


def test_empty_selection_retains_global_context_and_capped_population(tmp_path):
    store = Store(tmp_path / "pure-state")
    try:
        log = n_log(315, 105, [f"- {3 * index + 1}: NAT" for index in range(100)], 5)
        sheet = glyco.build_glycosylation_sheet(N, log, sequence="NAT" * 105,
            parameters={"allow_overlap": False}, input_ref="literal-supplied-input", input_mapping=None)
        components = glyco.calculate_glycosylation_components(sheet)
        projection = _projection(store, sheet, components, [])
        assert projection["schema"] == "molecular_sequence_private_projection_v2"
        assert projection["public"]["rows"] == []
        context = projection["public"]["context"]
        assert context["parameters"]["effective_allow_overlap"]["value"] is False
        assert context["native"]["selected_metadata"]["value"]["total"]["total_count"] == 105
        assert components["summary"]["retained_printed_row_count"] == 100
        assert components["summary"]["original_symbol_count"] == 315
        assert components["summary"]["native_reported_sequence_length"] == 315
        assert components["summary"]["unretained_reported_row_count"] == 5
        assert context["completeness"]["value"]["native_report_complete"] is False
        assert context["mapping"]["available"]["value"] is False
        assert len(context["row_issues"]) == 100
        assert contracts.validate_molecular_sequence_projection(projection) == projection
    finally:
        store.close()


def test_contradictory_rows_keep_original_ordinals_and_missing_mapping(tmp_path):
    store = Store(tmp_path / "pure-state")
    try:
        log = n_log(6, 4, ["- 1: NAT", "- malformed", "- 1: NAT", "- 4: NAT"])
        sheet = glyco.build_glycosylation_sheet(N, log, sequence="NATNAT", parameters={"allow_overlap": True})
        components = glyco.calculate_glycosylation_components(sheet)
        rows = [dict(row_id={"kind": "glycosylation_site", "row_ordinal": i}, fields=["motif", "source_intervals"])
            for i in (3, 1, 2, 0)]
        projection = _projection(store, sheet, components, rows)
        public = projection["public"]
        assert [row["row_id"]["row_ordinal"] for row in public["rows"]] == [3, 3, 1, 1, 2, 2, 0, 0]
        assert _cell(public, "motif", 1)["value_state"] == "path_missing"
        assert _cell(public, "source_intervals", 3)["value_state"] == "stored_null"
        assert [row["row_ordinal"] for row in public["context"]["row_issues"]] == [0, 1, 2, 3]
        assert public["context"]["mapping"]["reason"]["value"] == "not_supplied"
        assert components["summary"]["native_report_complete"] is False
        assert contracts.validate_molecular_sequence_projection(projection) == projection
    finally:
        store.close()


@pytest.mark.parametrize("log,total,retained,complete", [
    (None, None, None, False), ("", None, 0, False),
    (n_log(0, 0), 0, 0, True)])
def test_missing_empty_capture_and_observed_zero_remain_distinct(tmp_path, log, total, retained, complete):
    store = Store(tmp_path / "pure-state")
    try:
        sheet = glyco.build_glycosylation_sheet(N, log, sequence="", parameters={"allow_overlap": False},
            native_outcome="failed" if log is None else "completed")
        components = glyco.calculate_glycosylation_components(sheet)
        projection = _projection(store, sheet, components, [])
        assert components["summary"]["native_reported_total_count"] is total
        assert components["summary"]["retained_printed_row_count"] is retained
        assert projection["public"]["context"]["completeness"]["value"]["native_log_complete"] is complete
        assert projection["public"]["context"]["row_issues"] == []
        assert contracts.validate_molecular_sequence_projection(projection) == projection
    finally:
        store.close()


@pytest.mark.parametrize("wrong_role", ["sheet", "components"])
def test_n_projection_rejects_o_document_with_shared_schema_tag(tmp_path, wrong_role):
    store = Store(tmp_path / "pure-state")
    try:
        sheet = glyco.build_glycosylation_sheet(N, OVERLAP_LOG, sequence="NNST", parameters={"allow_overlap": True})
        components = glyco.calculate_glycosylation_components(sheet)
        if wrong_role == "sheet":
            sheet["inputs"]["operation"] = "predict_o_glycosylation_hotspots"
        else:
            components["operation"] = "predict_o_glycosylation_hotspots"
        # The shared schema tags still match. The new N-only operation join
        # must reject even an empty requested view before relabelling cells.
        with pytest.raises(ValueError):
            _projection(store, sheet, components, [])
    finally:
        store.close()


def test_legacy_orf_selection_and_qualifier_shape_is_unchanged(tmp_path):
    store = Store(tmp_path / "pure-state")
    try:
        sheet = {"schema": "orf_measurement_sheet_v1"}
        components = dict(schema="orf_measurement_components_v1", status="complete", native_outcome="completed",
            summary=dict(reported_row_count=1, usable_saved_row_count=1, retained_length_denominator_rows=1))
        sources = {role: contracts.empty_file_state("not_requested") for role in contracts.FILE_ROLES}
        sources["sheet"], sources["components"] = _retained(store, sheet), _retained(store, components)
        selector = contracts.ordinary_orf_selector(dict(subject_ref="engineering-input", min_length=0,
            search_reverse=False, filter_subsets=False,
            rows=[dict(row_id={"kind": "summary"}, fields=["reported_row_count"])]))
        projection = contracts.select_stored_molecular_sequence_values(operation=ORF, sheet=sheet,
            components=components, selection=selector, source_files=sources)
        assert selector["version"] == "molecular_sequence_result_selector_v1"
        assert projection["schema"] == "molecular_sequence_private_projection_v1"
        assert projection["public"]["schema"] == "molecular_sequence_selected_values_v1"
        assert "context" not in projection["public"]
        qualifiers = projection["public"]["rows"][0]["scientific_qualifiers"]
        assert qualifiers["schema"] == "molecular_sequence_scientific_qualifiers_v1"
        assert set(qualifiers["states"]) == {"component_status", "native_outcome", "reported_row_count",
            "usable_saved_row_count", "retained_string_denominator"}
        assert contracts.validate_molecular_sequence_projection(projection) == projection
    finally:
        store.close()


def _seed(value):
    return _dispatch(value, value.initial_arguments, 0)


@pytest.mark.parametrize("n_boundary", [
    {"sequence": "NAT" * 105, "allow_overlap": False, "rows": [],
        "log": n_log(315, 105, [f"- {3 * index + 1}: NAT" for index in range(100)], 5)},
    {"sequence": "nnst", "allow_overlap": True, "rows": [], "native_outcome": "failed"}],
    indirect=True, ids=["capped_105_printed_100", "failed_source_outcome"])
def test_empty_native_and_saved_views_keep_global_partial_or_failed_status(n_boundary):
    value = n_boundary
    native_result = _seed(value)
    reference = native_result["result"]["source_ref"]
    context = native_result["result"]["values"]["context"]
    assert native_result["result"]["values"]["rows"] == []
    assert context["component_status"]["value"] in ("partial", "failed")
    assert native_result["status"] == "partial"
    if value.native_outcome == "completed":
        assert native_result["result"]["failures"] == []
        assert context["native"]["selected_metadata"]["value"]["total"]["total_count"] == 105
    for index, mode in ((1, "read_stored"), (2, "calculate_saved")):
        result = _dispatch(value, dict(mode=mode, result_ref=reference, rows=[]), index)
        assert result["result"]["values"]["rows"] == []
        status = result["result"]["values"]["context"]["component_status"]
        assert status["value_state"] == "stored_value" and status["value"] == context["component_status"]["value"]
        assert result["status"] == "partial"
    assert len(value.calls) == 1


def test_saved_only_literal_read_and_once_calculation_keep_original_sheet(n_boundary, monkeypatch):
    value = n_boundary
    original = _seed(value)
    reference = original["result"]["source_ref"]
    sheet_file = value.registry.molecular_sequence_results_for(value.flow.run_id).read_ordinary_molecular_sequence_publication(
        value.flow.binding_context(value.caller.source), reference, operation=N)["control"]["source_files"]["sheet"]["file"]
    shutil.rmtree(Path(value.prepared["handle_path"]).parent)
    shutil.rmtree(Path(value.call["selected"]["software"]["python_home"]))
    input_sha = value.subject["sequence_ref"][9:]
    input_body = value.store.path / "artifacts" / input_sha[:2] / input_sha
    input_body.unlink()  # Owned test operand only; retained sheet/controls remain.
    monkeypatch.setattr(value.registry, "_prepare_molecular_sequence_operand", _forbidden)
    monkeypatch.setattr(ordinary, "prepare_ordinary_molecular_sequence_attempt", _forbidden)
    monkeypatch.setattr(ordinary, "run_ordinary_molecular_sequence_attempt", _forbidden)
    calls = []
    calculator = glyco.calculate_glycosylation_components
    def once(sheet):
        calls.append(deepcopy(sheet))
        return calculator(sheet)
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", once)
    read = _dispatch(value, dict(mode="read_stored", result_ref=reference, rows=[]), 1)
    assert read["result"]["source_ref"] == reference and read["changed_record_refs"] == [] and calls == []
    calculated = _dispatch(value, dict(mode="calculate_saved", result_ref=reference, rows=_rows()), 2)
    assert len(calls) == 1 and calls[0] == value.sheet
    assert calculated["result"]["source_ref"] != reference
    assert calculated["result"]["values"]["source_sheet_ref"] == sheet_file["artifact_ref"]
    assert calculated["result"]["values"]["context"]["parameters"]["effective_allow_overlap"]["value"] is True
    assert len(value.calls) == 1
    before = _tables(value.store)
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", _forbidden)
    cached = asyncio.run(value.flow.execute(value.caller.source, N,
        dict(mode="calculate_saved", result_ref=reference, rows=_rows()), decision_index=2,
        operation_key=f"{value.flow.run_id}:{value.caller.source.episode_id}:2"))
    expected = {key: item for key, item in calculated.items() if key != "pending_work_after_action"}
    assert cached == expected and _tables(value.store) == before


def test_saved_calculation_unknown_start_never_reissues(n_boundary, monkeypatch):
    value = n_boundary
    reference = _seed(value)["result"]["source_ref"]
    calls = []
    class EngineeredProcessStop(BaseException):
        pass
    def stopped(sheet):
        calls.append("entered calculator boundary, no completed calculation")
        raise EngineeredProcessStop()
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", stopped)
    arguments = dict(mode="calculate_saved", result_ref=reference, rows=[])
    with pytest.raises(EngineeredProcessStop):
        _dispatch(value, arguments, 1)
    with pytest.raises(MolecularOperationUnpublished):
        _dispatch(value, arguments, 1)
    assert len(calls) == 1 and len(value.calls) == 1
    row = value.flow.journal.row("runtime_actions", value.caller.source.episode_id, 1)
    assert row["result"] is None
    assert value.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 1


def test_wrong_o_sheet_is_rejected_before_saved_start_or_calculator(n_boundary, monkeypatch):
    value = n_boundary
    def wrong_sheet(sheet, components):
        sheet["inputs"]["operation"] = "predict_o_glycosylation_hotspots"
    value.alter_documents = wrong_sheet
    original = _seed(value)
    assert original["status"] == "partial"
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", _forbidden)
    with pytest.raises(ActionFailure):
        _dispatch(value, dict(mode="calculate_saved", result_ref=original["result"]["source_ref"], rows=[]), 1)
    owner = value.registry.molecular_sequence_results_for(value.flow.run_id)
    key = f"{value.flow.run_id}:{value.caller.source.episode_id}:1"
    directory = owner.action_directory(value.caller.source.episode_id, key)
    assert not (directory / "ordinary-calculation-started.json").exists()
    assert not (directory / "ordinary-calculation-result.json").exists()
    assert len(value.calls) == 1


def test_current_saved_source_receipt_is_required_before_private_body_reads(n_boundary, monkeypatch, tmp_path):
    value = n_boundary
    reference = _seed(value)["result"]["source_ref"]
    flow, caller, provider = _caller(value.store, value.registry, value.resources, value.environments,
        tmp_path / "unreceived-run", "engineering-unreceived-n-source",
        [value.subject["id"], value.subject["sequence_ref"]])
    assert reference not in flow.receipts.known(caller.source.episode_id)
    foreign = SimpleNamespace(store=value.store, registry=value.registry, flow=flow, caller=caller)
    private_reads = []
    def denied_bytes(*args, **kwargs):
        private_reads.append(args)
        raise AssertionError("unreceived Source opened an Artifact body")
    owner = value.registry.molecular_sequence_results_for(flow.run_id)
    monkeypatch.setattr(value.store, "get_artifact", denied_bytes)
    monkeypatch.setattr(owner, "_ordinary_value", denied_bytes)
    monkeypatch.setattr("gene_annotation_episode.molecular_measurement_tools._publication_bytes", denied_bytes)
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", _forbidden)
    with pytest.raises(ActionFailure):
        _dispatch(foreign, dict(mode="read_stored", result_ref=reference, rows=[]), 0)
    row = flow.journal.row("runtime_actions", caller.source.episode_id, 0)
    outcome = json.loads(row["result"])
    assert outcome["status"] == "invalid" and outcome["result"] is None and outcome["record_refs"] == []
    assert private_reads == [] and len(value.calls) == 1 and provider.contexts == []


def test_pending_saved_selection_rejects_later_current_source_receipt(n_boundary, monkeypatch):
    value = n_boundary
    arguments = dict(subject_ref=value.subject["id"], allow_overlap=True, rows=_rows())
    receive = value.flow.receive_outcome
    def stop_delivery(source, selection, result, index):
        assert index == 5
        raise MolecularOperationUnpublished("engineering_stop_after_publication_before_receipt")
    monkeypatch.setattr(value.flow, "receive_outcome", stop_delivery)
    with pytest.raises(MolecularOperationUnpublished):
        _dispatch(value, arguments, 5)
    native_row = value.flow.journal.row("runtime_actions", value.caller.source.episode_id, 5)
    original = json.loads(native_row["result"])
    reference = original["result"]["source_ref"]
    assert reference not in value.flow.receipts.known(value.caller.source.episode_id)
    owner = value.registry.molecular_sequence_results_for(value.flow.run_id)
    prepare = owner.prepare_ordinary_molecular_sequence_saved
    def stop_prepare(*args, **kwargs):
        raise MolecularOperationUnpublished("engineering_stop_after_selection_before_admission")
    monkeypatch.setattr(owner, "prepare_ordinary_molecular_sequence_saved", stop_prepare)
    saved = dict(mode="read_stored", result_ref=reference, rows=[])
    with pytest.raises(MolecularOperationUnpublished):
        _dispatch(value, saved, 2)
    pending = value.flow.journal.row("runtime_actions", value.caller.source.episode_id, 2)
    assert pending["result"] is None
    monkeypatch.setattr(value.flow, "receive_outcome", receive)
    monkeypatch.setattr(owner, "prepare_ordinary_molecular_sequence_saved", prepare)
    assert _dispatch(value, arguments, 5) == original  # Real cached action, normal receipt delivery.
    assert reference in value.flow.receipts.known(value.caller.source.episode_id)
    monkeypatch.setattr(owner, "_ordinary_value", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.molecular_measurement_tools._publication_bytes", _forbidden)
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", _forbidden)
    with pytest.raises(ActionFailure):
        _dispatch(value, saved, 2)
    row = value.flow.journal.row("runtime_actions", value.caller.source.episode_id, 2)
    assert row["action"] == pending["action"]
    assert json.loads(row["result"])["status"] == "invalid"
    directory = owner.action_directory(value.caller.source.episode_id,
        f"{value.flow.run_id}:{value.caller.source.episode_id}:2")
    assert not (directory / "ordinary-source-admission.json").exists()
    assert not (directory / "ordinary-calculation-started.json").exists()
    assert len(value.calls) == 1


def test_same_key_cache_authenticates_retained_control_without_new_grants(n_boundary, monkeypatch):
    value = n_boundary
    arguments = dict(subject_ref=value.subject["id"], allow_overlap=True, rows=_rows())
    original = _dispatch(value, arguments, 0)
    source = value.store.get(original["result"]["source_ref"])
    sha = source["request_ref"][9:]
    path = value.store.path / "artifacts" / sha[:2] / sha
    raw, mode = path.read_bytes(), path.stat().st_mode
    before = _tables(value.store)
    known = set(value.flow.receipts.known(value.caller.source.episode_id))
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", _forbidden)
    monkeypatch.setattr(ordinary, "prepare_ordinary_molecular_sequence_attempt", _forbidden)
    monkeypatch.setattr(ordinary, "run_ordinary_molecular_sequence_attempt", _forbidden)
    try:
        path.chmod(0o600)
        path.write_bytes(b"!" + raw[1:])  # Same-size corruption of an owned test Artifact.
        with pytest.raises(ValueError):
            asyncio.run(value.flow.execute(value.caller.source, N, arguments, decision_index=0,
                operation_key=f"{value.flow.run_id}:{value.caller.source.episode_id}:0"))
    finally:
        path.write_bytes(raw)
        path.chmod(mode)
    assert _tables(value.store) == before
    assert set(value.flow.receipts.known(value.caller.source.episode_id)) == known
    assert len(value.calls) == 1


def test_n_renderer_unknown_row_issues_do_not_become_known_empty(n_boundary, monkeypatch):
    from gene_annotation_episode.scientific_process_prompt import _selected_molecular_packet, _selected_molecular_text

    value = n_boundary
    def partial_components(sheet, components):
        components.pop("rows")
        components["status"] = "partial"
        components["issues"] = []
    value.alter_documents = partial_components
    packet = _seed(value)["result"]
    context = packet["values"]["context"]
    assert context["row_issues"] is None and context["component_issues"]["value"] == []
    assert _selected_molecular_packet(packet) == packet
    monkeypatch.setattr(value.store, "get_artifact", _forbidden)
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", _forbidden)
    shown = _selected_molecular_text(packet, 1)
    assert "retained row issues" in shown and "unavailable" in shown
    assert "Known empty issue arrays." not in shown


def test_n_renderer_uses_diagnostic_role_without_artifact_identity(n_boundary, monkeypatch):
    from gene_annotation_episode.scientific_process_prompt import _selected_molecular_packet, _selected_molecular_text

    value = n_boundary
    original = _seed(value)["result"]
    diagnostic = value.store.artifact(b"engineered retained diagnostic", "text/plain")
    issue = contracts.failure("producer_unavailable", "capture", role="components", diagnostic_ref=diagnostic)
    # Detached validation/presentation fixture only. No Source, operation,
    # receipt or frozen form is rewritten to contain this added diagnostic.
    packet = deepcopy(original)
    packet["failures"].append(issue)
    packet["values"]["failures"].append(deepcopy(issue))
    assert _selected_molecular_packet(packet) == packet
    monkeypatch.setattr(value.store, "get_artifact", _forbidden)
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", _forbidden)
    shown = _selected_molecular_text(packet, 1)
    assert diagnostic not in shown and "diagnostic_role" in shown
    assert "retained diagnostic association" in shown


def test_n_frozen_value_and_received_reference_hooks_use_only_public_group(n_boundary, monkeypatch):
    from gene_annotation_episode.communication import ReportBoundaryError
    from gene_annotation_episode.molecular_result_facts import merge_molecular_facts, validate_frozen_molecular_return
    from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes

    value = n_boundary
    public = _seed(value)["result"]
    fact_source = "n_glycosylation_motif_outcomes"
    registered = contracts.ordinary_molecular_sequence_fact_sources(N)[fact_source]["report_schema"]
    schema = dict(type="object", properties={"measurements": registered},
        required=["measurements"], additionalProperties=False)
    form = {"measurements": [public]}
    # A detached group exercises the pure frozen-value consumer, without
    # manufacturing a runtime_forms row or claiming an actual SCI return.
    frozen = merge_molecular_facts([public], [deepcopy(public)], fact_source=fact_source)
    assert frozen == [public]
    before, known = _tables(value.store), list(value.flow.receipts.known(value.caller.source.episode_id))
    monkeypatch.setattr(value.store, "get_artifact", _forbidden)
    monkeypatch.setattr(glyco, "calculate_glycosylation_components", _forbidden)
    assert validate_frozen_molecular_return(form, schema, frozen, fact_source=fact_source) is None
    altered = deepcopy(form)
    _cell(altered["measurements"][0]["values"], "native_reported_total_count")["value"] = 3
    with pytest.raises(ReportBoundaryError) as error:
        validate_frozen_molecular_return(altered, schema, frozen, fact_source=fact_source)
    assert error.value.diagnostic["code"] == "ordinary_n_glycosylation_frozen_source_mismatch"
    # This existing hook is pure: it does not use a binding instance, context
    # or key. A full services-backed SCI freeze/delivery is separate coverage.
    references = ScientificProcessEpisodes.received_form_references(None, None, form, schema, None)
    assert references == [public["source_ref"]]
    assert value.subject["sequence_ref"] not in references
    assert _tables(value.store) == before
    assert list(value.flow.receipts.known(value.caller.source.episode_id)) == known

