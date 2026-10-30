"""Retained-payload admission under the coordinator's bounded verification.

Native preparation uses the installed pinned libraries on synthetic FCS values.
Report inputs below are labelled source-format fixtures, not authentic legacy
executions. Envelope construction tests the result boundary, not native launch.
"""
import builtins
from copy import deepcopy
import importlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from fluorescence_flowio_test_support import require_bounded_runtime

require_bounded_runtime()

from gene_annotation_episode import fluorescence_event_contracts as core
from gene_annotation_episode import fluorescence_result_worker as worker
from gene_annotation_episode import fluorescence_event_preparation as preparation
from gene_annotation_episode.communication import plain
from gene_annotation_episode.fluorescence_event_readers import parse_fluorescence_csv
from gene_annotation_episode.fluorescence_execution_common import canonical, digest, identity
from gene_annotation_episode.fluorescence_native_report_contracts import (
    FACS_PROFILE, CYTOKINE_CSV_PROFILE, make_fluorescence_report_binding,
)
from gene_annotation_episode.fluorescence_native_reports import parse_fluorescence_native_reports
from gene_annotation_episode.fluorescence_preparation_contracts import (
    COMPENSATE_METHOD, assemble_prepared_parse,
)
from gene_annotation_episode.fluorescence_result_contracts import (
    FAILURE_SCHEMA, OUTPUTS, validate_fluorescence_selector,
)
from gene_annotation_episode.fluorescence_result_receipts import FluorescenceResultReceipts, qualified_files
from gene_annotation_episode.fluorescence_return_views import (
    PROJECTION_SOURCE, CONTEXT_SOURCE, SAVED_SOURCE, FAILURE_SOURCE,
)
from gene_annotation_episode.native_fluorescence_capture import capture_fluorescence_native_files
from gene_annotation_episode.native_fluorescence_contracts import (
    OPERATIONS, validate_fluorescence_manifest,
)
from gene_annotation_episode.native_fluorescence_preparation import (
    build_native_fluorescence_worker_plan, build_saved_fluorescence_worker_plan,
    _dependencies,
)
from gene_annotation_episode.native_atac_differential_preparation import _source_closure
from gene_annotation_episode.native_fluorescence_results import NativeFluorescenceResults
from gene_annotation_episode.state import Store
from test_native_fluorescence_contracts import event_input, job, plan as original_plan, pin
from test_fluorescence_result_worker import _retain, selector, output
from test_fluorescence_event_calculations import _request
from test_fluorescence_preparation import _fcs, _parse, _request as preparation_request, _matrix
from test_fluorescence_result_receipts import receipt_fixture, schema
from test_fluorescence_episode_routing import selected, _request as routed_request
from test_fluorescence_returns import Fixture, form_schema


def _software(value, *, native=False):
    value = deepcopy(value)
    names = {Path(row["path"]).name for row in value["implementation_files"]}
    for name in ("native_fluorescence_prepared_contracts.py", "native_fluorescence_prepared_driver.py",
                 "fluorescence_preparation_contracts.py", "fluorescence_preparation_readers.py",
                 "fluorescence_event_preparation.py", "fluorescence_native_report_contracts.py",
                 "fluorescence_native_reports.py"):
        if name not in names:
            value["implementation_files"].append(pin(Path(value["module_root"]) / "gene_annotation_episode" / name))
    if native:
        for name, version in (("numpy", "2.2.6"), ("FlowUtils", "1.2.2")):
            value["distributions"].append(dict(name=name, version=version, requires=[]))
            value["runtime_files"].extend([
                pin(f"/declared-software/dependencies/{name.lower()}/__init__.py"),
                pin(f"/declared-software/dependencies/{name.lower()}-{version}.dist-info/METADATA")])
    return value


def _support(root, raw, *, format_="json", name="support.json"):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return dict(file=identity(raw, format=format_), path=str(path))


def _assembled(outcome, request, parent):
    data_file = None if outcome["data"] is None else identity(core.canonical(outcome["data"]) + b"\n",
        format="fluorescence_prepared_event_data_v1")
    parameters_file = identity(core.canonical(outcome["parameters"]) + b"\n",
        format="fluorescence_resolved_preparation_v1")
    return assemble_prepared_parse(outcome, request=request, parent=parent,
        data_file=data_file, parameters_file=parameters_file), data_file, parameters_file


def _capture_plan(store, root, selected_job, originals, preparations=(), *, missing=(), report_associations=None):
    """Retain exact finite envelopes; software declarations are shape fixtures."""
    original = original_plan(root, selected_job=selected_job)
    payloads, files, original_rows, prepared_rows, report_rows = {}, {}, [], [], []
    specs = {row["role"]: row for row in original["outputs"]}

    def retain(role, value, *, raw=False, control=False):
        payload = value if raw else (canonical(value) if control else core.canonical(value)) + b"\n"
        payloads[role] = payload
        files[role] = identity(payload, format=specs[role]["format"])
        return files[role]

    for index, (binding, parsed) in enumerate(zip(selected_job["inputs"], originals)):
        retain(f"event_input:{index}", Path(binding["path"]).read_bytes(), raw=True)
        file = retain(f"event_batch:{index}", dict(version="fluorescence_parsed_batch_v1",
            original_plan_sha256=digest(original), input_index=index, input_binding_sha256=digest(binding),
            software_sha256=digest(selected_job["software"]), parse=parsed))
        original_rows.append(dict(input_index=index, source_file=binding["source"]["file"],
            batch_file=file, extent=parsed["source"]["extent"]))
    for index, support in enumerate(selected_job["support_inputs"]):
        retain(f"support_input:{index}", Path(support["path"]).read_bytes(), raw=True)
    for index, selected in enumerate(selected_job.get("report_inputs", [])):
        retain(f"report_input:{index}", Path(selected["path"]).read_bytes(), raw=True)
    for index, (parent, outcome) in enumerate(preparations):
        request = selected_job["preparations"][index]
        parsed, data_file, parameters_file = _assembled(outcome, request, parent)
        assert retain(f"preparation_parameters:{index}", outcome["parameters"]) == parameters_file
        if outcome["data"] is not None:
            assert retain(f"prepared_data:{index}", outcome["data"]) == data_file
        parent_role = ("event_batch" if request["input"]["kind"] == "event_input" else "prepared_batch")
        parent_file = files[f"{parent_role}:{request['input']['index']}"]
        batch_file = retain(f"prepared_batch:{index}", dict(version="fluorescence_prepared_batch_v1",
            original_plan_sha256=digest(original), preparation_index=index,
            preparation_request_sha256=core.digest(request), software_sha256=digest(selected_job["software"]),
            parent_batch_file=parent_file, recipe_file=request["recipe_file"], parameters_file=parameters_file,
            prepared_file=data_file, parse=parsed, status=outcome["status"], problems=outcome["parameters"]["problems"]))
        prepared_rows.append(dict(preparation_index=index, parent_batch_file=parent_file,
            parameters_file=parameters_file, prepared_file=data_file, batch_file=batch_file, status=outcome["status"]))
    for index, selected in enumerate(selected_job.get("report_inputs", [])):
        binding = make_fluorescence_report_binding(selected, definitions=selected_job["definitions"],
            event_inputs=selected_job["inputs"], preparations=selected_job["preparations"])
        association = report_associations[index]
        parsed = parse_fluorescence_native_reports(payloads[f"report_input:{index}"], binding=binding,
            association_raw=association)
        batch_file = retain(f"report_batch:{index}", dict(version="fluorescence_report_batch_v1",
            original_plan_sha256=digest(original), report_index=index, report_input_sha256=digest(selected),
            software_sha256=digest(selected_job["software"]), report_file=selected["file"],
            association_file=selected["association_file"] if association is not None else None, parse=parsed))
        report_rows.append(dict(report_index=index, source_file=selected["file"], batch_file=batch_file,
            extent=parsed["source"]["extent"]))
    outputs = [dict(role=spec["role"], declaration=dict(relative_path=spec["relative_path"], format=spec["format"],
        state="present" if spec["role"] in files else "absent", sha256=files.get(spec["role"], {}).get("sha256"),
        size_bytes=files.get(spec["role"], {}).get("size_bytes"))) for spec in original["outputs"][:-1]]
    manifest = dict(version="fluorescence_native_manifest_v2", original_plan_sha256=digest(original),
        identity=original["identity"], requested_job_sha256=original["identity"]["requested_job_sha256"],
        operation=selected_job["operation"], mode=selected_job["mode"], software_sha256=digest(selected_job["software"]),
        outputs=outputs, inputs=original_rows,
        support=[dict(input_index=index, file=row["file"]) for index, row in enumerate(selected_job["support_inputs"])],
        preparations=prepared_rows, reports=report_rows, failures=[])
    retain("manifest", validate_fluorescence_manifest(manifest, original_plan=original), control=True)
    for role, payload in payloads.items():
        if role in missing:
            continue
        path = Path(original["attempt_directory"]) / specs[role]["relative_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    capture = capture_fluorescence_native_files(store, original_plan=original,
        source_action_receipt_ref="artifact_" + "3" * 64, writer_closure_receipt_ref="artifact_" + "4" * 64,
        driver_started=True)
    return build_native_fluorescence_worker_plan(directory=str(root / "worker"), original_plan=original,
        capture=capture, selector=selector(selected=dict(requests=[], offset=0, limit=50)))


def _prepared_plan(store, root, operation=OPERATIONS[0], *, missing=(), singular=False):
    native = importlib.import_module("flowio")
    assert native.__version__ == "1.4.0"
    raw = _fcs(native, [[220, 120], [40, 200]], metadata=dict(p1g="2", p2g="2",
        spill="2,A,B,1,1,1,1" if singular else "2,A,B,1,0.1,0.2,1"))
    parent = _parse(raw)
    binding = {name: deepcopy(parent[name]) for name in ("source", "sample", "channels", "domain")}
    binding["source"].update(extent="unavailable", native_event_count=None, metadata=[])
    for channel in binding["channels"]:
        channel.pop("domain_key")
        channel["measurement_origin"] = "supplied_predicted"
    path = root / "original.fcs"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    binding.update(parser="fcs_encoded", path=str(path), format_spec=None)
    selected_job = job(root, inputs=[binding], operation=operation)
    selected_job.update(version="native_fluorescence_job_v2", preparations=[], report_inputs=[])
    selected_job["software"] = _software(selected_job["software"], native=True)
    selected_job["support_inputs"].append(_support(root, b"synthetic matrix-domain declaration", name="basis.json"))
    first = preparation_request(parent, key="scaled")
    first["key"] = "scale-request"
    first_outcome = preparation.prepare_fcs_scaling(raw, parent=parent, request=first)
    first_parse = _assembled(first_outcome, first, parent)[0]
    matrix = _matrix(raw, first_parse, source=parent["source"])
    second = preparation_request(first_parse, COMPENSATE_METHOD, matrix=matrix, key="compensated")
    second.update(key="compensate-request", input=dict(kind="preparation", index=0))
    second_outcome = preparation.prepare_spill_compensation(first_parse, matrix=matrix, request=second)
    selected_job["preparations"] = [first, second]
    for index, request in enumerate(selected_job["preparations"]):
        support = _support(root, core.canonical(request["recipe"]) + b"\n", name=f"recipe-{index}.json")
        assert support["file"] == request["recipe_file"]
        selected_job["support_inputs"].append(support)
    gates = []
    for index, domain in enumerate(("raw", "scaled", "compensated")):
        gates.append(dict(key=f"gate-{index}", sample_key="sample", parent=dict(kind="population", key="population-0"),
            kind="threshold", domain_key=domain, channel_key=f"{domain}.c0", lower=dict(value=105, inclusive=True), upper=None))
    selected_job["definitions"]["gates"] = gates
    selected_job["parameters"]["fraction_requests"] = [dict(gate_key=row["key"], denominator="parent") for row in gates]
    selected_job["parameters"]["intensity_requests"] = [dict(gate_key="gate-0", domain_key="compensated", channel_key="compensated.c0")]
    plan = _capture_plan(store, root, selected_job, [parent], [(parent, first_outcome), (first_parse, second_outcome)], missing=missing)
    plan["selector"] = selector(selected=dict(requests=[
        *[_request("fraction", "selected_percent", gate_key=row["key"], denominator="parent") for row in gates],
        _request("intensity", "selected_intensity_mean", gate_key="gate-0", domain_key="compensated", channel_key="compensated.c0")],
        offset=0, limit=50), fields=["sources", "samples", "channels", "domains", "gates"])
    return plan


def _report_plan(store, root, operation=OPERATIONS[0], *, native_value=None, missing=(), association=True):
    facs = operation == OPERATIONS[0]
    raw = b"signal\n150\n250\n0\n" if facs else b"CD4,IFN-g\n1500,600\n1500,400\n500,900\n"
    binding = event_input(root / "inputs", raw, name="signal" if facs else "CD4")
    binding["sample"]["condition"] = "stimulated"
    if not facs:
        binding["channels"].append({**deepcopy(binding["channels"][0]), "key": "channel-1", "ordinal": 1, "native_name": "IFN-g"})
    selected_job = job(root, inputs=[binding], operation=operation)
    selected_job.update(version="native_fluorescence_job_v2", preparations=[], report_inputs=[])
    selected_job["software"] = _software(selected_job["software"])
    gate = selected_job["definitions"]["gates"][0]
    gate.update(kind="threshold", domain_key="domain-0", channel_key="channel-0",
        lower=dict(value=100 if facs else 1000, inclusive=facs), upper=dict(value=200, inclusive=True) if facs else None)
    if not facs:
        selected_job["definitions"]["gates"].append(dict(key="marker", sample_key="sample-0", parent=dict(kind="gate", key="gate-0"),
            kind="threshold", domain_key="domain-0", channel_key="channel-1", lower=dict(value=500, inclusive=False), upper=None))
    selected_gate = "gate-0" if facs else "marker"
    selected_job["parameters"]["fraction_requests"] = [dict(gate_key=selected_gate, denominator="parent")]
    linked = _request("fraction", "selected_percent", gate_key=selected_gate, denominator="parent")
    number = ("33.33" if facs else "50.0") if native_value is None else native_value
    report_raw = (("# FACS-based Cell Sorting and Enrichment Research Log\n"
        "## Applying Gating Strategy for signal\nApplied minimum threshold of 100: 2 cells remaining\n"
        "Applied maximum threshold of 200: 1 cells remaining\n## Enrichment Results\n"
        f"Enrichment percentage: {number}%\n").encode() if facs else f",IFN-γ\nstimulated,{number}\n".encode())
    report_file = _support(root, report_raw, format_="text", name="source-format-report.txt")
    locator = (dict(kind="facs_metric", metric="selected_percent", occurrence=0) if facs else
        dict(kind="cytokine_csv_cell", row_ordinal=0, column_ordinal=1, condition_label="stimulated", column_label="IFN-γ"))
    report = dict(**report_file, source_key="reported", profile=FACS_PROFILE if facs else CYTOKINE_CSV_PROFILE,
        fields=[dict(key="native-percent", locator=locator, component_request=linked)], association_file=None)
    association_raw = core.canonical(dict(version="fluorescence_report_association_v1", report_file=report["file"],
        fields=[dict(report_key="native-percent", component_request=linked,
            event_sources=[dict(file=binding["source"]["file"], dataset_position=0)], sample_keys=["sample-0"],
            domain_keys=["domain-0"], gates=selected_job["definitions"]["gates"], control_pair=None)])) + b"\n"
    association_input = _support(root, association_raw, name="association.json")
    report["association_file"] = association_input["file"]
    selected_job["support_inputs"] = [association_input]
    selected_job["report_inputs"] = [report]
    selected_job["parameters"]["native_comparison_requests"] = ["native-percent"]
    parsed = parse_fluorescence_csv(raw, **{key: binding[key] for key in ("source", "sample", "channels", "domain", "format_spec")})
    plan = _capture_plan(store, root, selected_job, [parsed], missing=missing,
        report_associations=[association_raw if association else None])
    plan["selector"] = selector(selected=dict(requests=[linked,
        _request("native_comparison", "native_value", native_report_key="native-percent"),
        _request("native_comparison", "native_minus_calculated", native_report_key="native-percent")], offset=0, limit=50),
        fields=["sources", "samples", "domains", "channels", "gates", "native_reports"])
    return plan


def _deny_native(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("retained admission/recalculation executed native preparation or parsing")
    for module, names in ((preparation, ("prepare_fcs_scaling", "prepare_spill_compensation")),
            (importlib.import_module("gene_annotation_episode.fluorescence_native_reports"), ("parse_fluorescence_native_reports",)),
            (importlib.import_module("gene_annotation_episode.fluorescence_fcs_reader"), ("parse_fluorescence_fcs", "decode_selected_fcs")),
            (importlib.import_module("gene_annotation_episode.fluorescence_event_readers"), ("parse_fluorescence_csv", "parse_fluorescence_table_snapshot"))):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    original_import = builtins.__import__
    def guarded(name, *args, **kwargs):
        assert name.split(".")[0] not in {"flowio", "flowutils", "numpy"}
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_prepared_chain_common_cells_and_primary_event_identity(tmp_path, monkeypatch, operation):
    with Store(tmp_path / "store") as store:
        plan = _prepared_plan(store, tmp_path / "case", operation)
        _deny_native(monkeypatch)
        calls, calculate = [], worker.calculate_fluorescence_sheet
        def once(*args, **kwargs):
            calls.append(1)
            return calculate(*args, **kwargs)
        monkeypatch.setattr(worker, "calculate_fluorescence_sheet", once)
        result = worker.execute_fluorescence_worker(plan)
        assert calls == [1] and result["analysis_complete"] and result["native_outcome"] == "complete"
        assert len(result["input_identities"]) == 1 and result["original_events_acquired"]
        sheet, view, components = (output(plan, key) for key in ("sheet", "projection", "calculations"))
        assert [row["value"] for row in view["rows"]] == pytest.approx([50, 50, 0, 100])
        assert all(row in components["cells"] for row in view["rows"])
        assert [row["event_ordinal"] for row in sheet["events"]] == [0, 1, 0, 1, 0, 1]
        assert sheet["measurement_domains"][2]["parent_domain_key"] == "scaled"
        assert sheet["events"][0]["values"][0]["measurement"]["value"] == 220
        assert sheet["events"][2]["values"][0]["measurement"]["value"] == 110
        assert sheet["events"][4]["values"][0]["measurement"]["value"] == pytest.approx(100)
        assert output(plan, "context")["domains"][1]["scaling"]["state"] == "applied"


@pytest.mark.parametrize("operation", OPERATIONS)
def test_existing_selected_producer_envelopes_reach_worker_and_requested_projection(tmp_path, monkeypatch, operation):
    from native_fluorescence_prepared_test_support import prepared_job
    from test_native_fluorescence_driver import finite_driver
    from gene_annotation_episode.native_fluorescence_driver import run_fluorescence_driver
    with Store(tmp_path / "store") as store:
        selected_job = prepared_job(tmp_path / "supplied", operation=operation)
        selected_job["parameters"]["intensity_requests"] = [
            dict(gate_key="gate-0", domain_key="compensated", channel_key="compensated.c0"),
            dict(gate_key="gate-0", domain_key="scaled", channel_key="scaled.c2")]
        original = original_plan(tmp_path / "native", selected_job=selected_job)
        # This controls software trust explicitly, while executing the real
        # selected finite producer and installed preparation libraries.
        finite_driver(monkeypatch, original)
        manifest = run_fluorescence_driver(original)
        assert not manifest["failures"]
        capture = capture_fluorescence_native_files(store, original_plan=original,
            source_action_receipt_ref="artifact_" + "3" * 64, writer_closure_receipt_ref="artifact_" + "4" * 64,
            driver_started=True)
        selected = dict(requests=[
            _request("intensity", "selected_intensity_mean", **row)
            for row in selected_job["parameters"]["intensity_requests"]], offset=0, limit=20)
        selected["requests"].extend(_request("native_comparison", metric, native_report_key="native.report.percent")
            for metric in ("native_value", "native_minus_calculated"))
        plan = build_native_fluorescence_worker_plan(directory=str(tmp_path / "worker"), original_plan=original,
            capture=capture, selector=selector(selected=selected, fields=["domains", "channels", "native_reports"]))
        _deny_native(monkeypatch)
        result = worker.execute_fluorescence_worker(plan)
        assert result["analysis_complete"] and result["native_outcome"] == "complete"
        projection, calculations = output(plan, "projection"), output(plan, "calculations")
        assert [row["value"] for row in projection["rows"]] == pytest.approx([50, 1.5, 100, 0])
        assert all(row in calculations["cells"] for row in projection["rows"])


def test_authentic_failed_preparation_retains_actual_parameters_and_diagnostics(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        plan = _prepared_plan(store, tmp_path / "case", singular=True)
        _deny_native(monkeypatch)
        result = worker.execute_fluorescence_worker(plan)
        domains = output(plan, "sheet")["measurement_domains"]
        assert domains[2]["state"] == "failed" and domains[2]["compensation"]["state"] == "failed"
        recorded = next(row for row in plan["capture"]["files"] if row["role"] == "preparation_parameters:1")["retained"]
        assert domains[2]["compensation"]["parameters_file"] == recorded["file"]
        parameters = json.loads(Path(recorded["path"]).read_text())
        assert parameters["diagnostics"] and parameters["diagnostics"][0]["exception_class"].endswith("LinAlgError")
        assert [row["value"] for row in output(plan, "projection")["rows"]] == [50, 50, None, None]
        assert any(row["code"] == "preparation_failed" for row in result["failures"])


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("association", [True, False])
def test_native_report_shared_delta_and_unknown_association(tmp_path, monkeypatch, operation, association):
    with Store(tmp_path / "store") as store:
        plan = _report_plan(store, tmp_path / "case", operation, association=association,
            missing=() if association else ("support_input:0",))
        _deny_native(monkeypatch)
        result = worker.execute_fluorescence_worker(plan)
        sheet, view, components = (output(plan, key) for key in ("sheet", "projection", "calculations"))
        expected = 100 * (1 / 3) if operation == OPERATIONS[0] else 50
        native = 33.33 if operation == OPERATIONS[0] else 50
        assert [row["value"] for row in view["rows"]] == [expected, native, native - expected if association else None]
        assert all(row in components["cells"] for row in view["rows"])
        assert sheet["native_reports"][0]["component_request"] == plan["selector"]["selection"]["requests"][0]
        assert result["original_events_acquired"] and len(result["input_identities"]) == 1
        retained_batch = next(row for row in plan["capture"]["files"] if row["role"] == "report_batch:0")["retained"]
        batch = json.loads(Path(retained_batch["path"]).read_text())
        assert batch["parse"]["provenance"]["producer_execution"] == "unverified"
        if not association:
            assert core.issue("native_population_unknown", "input", source_key="reported") in sheet["issues"]


@pytest.mark.parametrize("operation", OPERATIONS)
def test_conflicting_report_is_preserved_and_compared_by_common_calculator(tmp_path, operation):
    with Store(tmp_path / "store") as store:
        plan = _report_plan(store, tmp_path / "case", operation, native_value="49.00")
        worker.execute_fluorescence_worker(plan)
        cells = output(plan, "projection")["rows"]
        assert cells[1]["value"] == 49 and cells[2]["value"] == 49 - cells[0]["value"]


@pytest.mark.parametrize("operation", OPERATIONS)
def test_report_without_original_events_reaches_received_form_without_acquisition(tmp_path, monkeypatch, operation):
    """Real worker/publication/return consumers with a closed-receipt test port.

    Native action/writer lifecycle authentication is covered by the coordinator's
    Workflow test; this port makes no claim to have run that lifecycle.
    """
    with Store(tmp_path / "store") as store:
        plan = _report_plan(store, tmp_path / "case", operation,
            missing=("event_input:0", "event_batch:0"))
        plan["selector"]["context_fields"] = ["sources", "samples"]
        _deny_native(monkeypatch)
        result = worker.execute_fluorescence_worker(plan)
        expected = 33.33 if operation == OPERATIONS[0] else 50
        projection, context = output(plan, "projection"), output(plan, "context")
        assert [row["value"] for row in projection["rows"]] == [None, expected, None]
        assert not result["native_binding"] and not result["original_events_acquired"]
        assert result["native_outcome"] == "unavailable" and not result["analysis_complete"]

        f = Fixture(store)
        f.projection, f.context_view = projection, context
        requested = form_schema(PROJECTION_SOURCE, CONTEXT_SOURCE, FAILURE_SOURCE)
        child = f.child(f.root, requested)
        receipt = receipt_fixture(store, acquired=False, native_outcome="unavailable")
        receipt["intent"].update(episode_id=child.episode_id,
            operation_key=f"{f.run_id}:{child.episode_id}:0", assignment=plain(child.assignment))
        receipt["native"]["original_plan"], receipt["capture"] = plan["original_plan"], plan["capture"]
        receipt["worker_capture"]["result"] = result
        receipt["worker_capture"]["outputs"] = []
        for (role, name, format_), declared in zip(OUTPUTS, result["outputs"]):
            raw = (Path(plan["directory"]) / name).read_bytes()
            file = _retain(store, tmp_path / "qualified" / role, raw, format_)["file"]
            receipt["worker_capture"]["outputs"].append(dict(declared=declared["declaration"],
                observed=file, outcome="verified", failure=None))
        receipt["qualified_files"] = qualified_files(receipt["worker_capture"], receipt["worker_execution"])
        receipt["projection"], receipt["context"] = projection, context
        owner = SimpleNamespace(store=store, run_id=f.run_id, acquired_record_unit=2, handoff_unit=3,
            native_fluorescence_returns=f.boundary)
        host = NativeFluorescenceResults(owner)
        f.host = f.boundary.results = host
        def closed_receipts(actual):
            assert actual.episode_id == child.episode_id
            return [receipt]
        monkeypatch.setattr(host.receipts, "completed_receipts", closed_receipts)
        receipt["facts"], receipt["delivery_complete"] = host.receipts.publication(receipt)
        receipt["acquired_population"] = host.receipts.acquisition_population(receipt)
        assert receipt["acquired_population"] is None and not receipt["delivery_complete"]
        assert receipt["facts"][PROJECTION_SOURCE] == [projection]
        assert host.facts(child)[PROJECTION_SOURCE] == [projection]
        assert not host.facts(child)["execution_completed"] and host.completion(child) is None
        form = f.returned(f.root, child)
        received = f.boundary.received_facts(f.root, requested)
        assert received[PROJECTION_SOURCE] == [projection]
        assert received[CONTEXT_SOURCE] == [context]
        assert [row["value"] for row in form["field_0"][0]["rows"]] == [None, expected, None]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0


@pytest.mark.parametrize("missing", [("manifest",), ("manifest", "prepared_batch:1"),
    ("preparation_parameters:0",), ("prepared_data:0",), ("support_input:1",)])
def test_absent_artifacts_preserve_raw_and_selected_downstream_domains(tmp_path, missing):
    with Store(tmp_path / "store") as store:
        plan = _prepared_plan(store, tmp_path / "case", missing=missing)
        result = worker.execute_fluorescence_worker(plan)
        assert result["original_events_acquired"] and result["native_outcome"] == "partial"
        assert not result["analysis_complete"]
        values = [row["value"] for row in output(plan, "projection")["rows"]]
        assert values[0] == 50
        if missing == ("manifest",):
            assert values == pytest.approx([50, 50, 0, 100])
        elif missing == ("manifest", "prepared_batch:1"):
            assert values == [50, 50, None, None]
        else:
            assert values == [50, None, None, None]
            domains = output(plan, "sheet")["measurement_domains"]
            assert domains[1]["scaling"]["parameters_file"] is None
            assert domains[1]["scaling"]["state"] == "unknown"
            assert domains[2]["parent_domain_key"] == "scaled"


def _replace(store, root, plan, role, change):
    row = next(row for row in plan["capture"]["files"] if row["role"] == role)
    raw = Path(row["retained"]["path"]).read_bytes()
    changed = change(json.loads(raw)) if callable(change) else change
    payload = core.canonical(changed) + b"\n" if isinstance(changed, dict) else changed
    row["retained"] = _retain(store, root, payload, row["format"])


@pytest.mark.parametrize("target", ["parent", "recipe", "parameters", "data", "data_values", "parse_values", "manifest"])
def test_prepared_identity_and_relationship_tampering_is_local(tmp_path, target):
    with Store(tmp_path / "store") as store:
        plan = _prepared_plan(store, tmp_path / "case")
        if target == "parent":
            _replace(store, tmp_path / "changed", plan, "prepared_batch:0",
                lambda value: {**value, "parent_batch_file": identity(b"foreign", format="fluorescence_parsed_batch_v1")})
        elif target == "recipe":
            _replace(store, tmp_path / "changed", plan, "support_input:1", b"{}\n")
        elif target in {"parameters", "data"}:
            role = "preparation_parameters:0" if target == "parameters" else "prepared_data:0"
            _replace(store, tmp_path / "changed", plan, role, lambda value: {**value, "request_sha256": "0" * 64})
        elif target == "data_values":
            def changed(value):
                value["events"][0]["values"][0]["measurement"]["value"] = 999
                return value
            _replace(store, tmp_path / "changed", plan, "prepared_data:0", changed)
        elif target == "parse_values":
            def changed(value):
                value["parse"]["events"][0]["values"][0]["measurement"]["value"] = 999
                return value
            _replace(store, tmp_path / "changed", plan, "prepared_batch:0", changed)
        else:
            _replace(store, tmp_path / "changed", plan, "manifest", lambda value: {**value, "software_sha256": "0" * 64})
        result = worker.execute_fluorescence_worker(plan)
        values = [row["value"] for row in output(plan, "projection")["rows"]]
        assert values == pytest.approx([50, 50, 0, 100]) if target == "manifest" else values == [50, None, None, None]
        assert result["native_outcome"] == "partial" and result["failures"]


@pytest.mark.parametrize("target", ["report_input", "report_binding", "span", "association", "batch_missing"])
def test_report_tampering_or_absence_preserves_requested_keys(tmp_path, target):
    with Store(tmp_path / "store") as store:
        plan = _report_plan(store, tmp_path / "case")
        if target == "report_input":
            _replace(store, tmp_path / "changed", plan, "report_input:0", b"different report")
        elif target == "report_binding":
            _replace(store, tmp_path / "changed", plan, "report_batch:0", lambda value: {**value, "report_input_sha256": "0" * 64})
        elif target == "span":
            def changed(value):
                value["parse"]["reports"][0]["location"]["byte_start"] -= 1
                return value
            _replace(store, tmp_path / "changed", plan, "report_batch:0", changed)
        elif target == "association":
            _replace(store, tmp_path / "changed", plan, "support_input:0", b"{}\n")
        else:
            next(row for row in plan["capture"]["files"] if row["role"] == "report_batch:0")["retained"] = None
        result = worker.execute_fluorescence_worker(plan)
        values = [row["value"] for row in output(plan, "projection")["rows"]]
        assert values == [100 * (1 / 3), 33.33 if target == "association" else None, None]
        report = output(plan, "sheet")["native_reports"][0]
        assert report["key"] == "native-percent" and report["component_request"] is not None
        if target != "association":
            assert report["raw"] is None and report["label"] is None and all(value is None for value in report["location"].values())
        assert result["original_events_acquired"] and result["native_outcome"] == "partial"


@pytest.mark.parametrize("kind", ["prepared", "report"])
def test_saved_only_recalculation_preserves_values_without_native_import_or_new_acquisition(tmp_path, monkeypatch, kind):
    with Store(tmp_path / "store") as store:
        original = (_prepared_plan if kind == "prepared" else _report_plan)(store, tmp_path / "case")
        first = worker.execute_fluorescence_worker(original)
        view = output(original, "projection")
        raw = (Path(original["directory"]) / "sheet.json").read_bytes()
        retained = _retain(store, tmp_path / "saved-input", raw, core.SHEET_SCHEMA)
        plan = build_saved_fluorescence_worker_plan(directory=str(tmp_path / "saved-worker"), sheet=retained,
            selector=selector(selected=original["selector"]["selection"], fields=original["selector"]["context_fields"],
                file=retained["file"], parameters=original["original_plan"]["requested_job"]["native_fluorescence"]["parameters"]))
        for row in original["capture"]["files"]:
            if row["retained"] is not None:
                Path(row["retained"]["path"]).unlink(missing_ok=True)
        shutil.rmtree(tmp_path / "case")
        _deny_native(monkeypatch)
        monkeypatch.setattr(worker, "_native", lambda *_: pytest.fail("saved result reacquired original inputs"))
        saved = worker.execute_fluorescence_worker(plan)
        assert first["original_events_acquired"] and not saved["original_events_acquired"]
        assert saved["analysis_complete"] and saved["native_outcome"] == "not_applicable"
        assert output(plan, "projection") == view and (Path(plan["directory"]) / "sheet.json").read_bytes() == raw


def test_result_worker_closure_remains_native_free():
    sources = _source_closure(Path(__file__).resolve().parents[1], ["gene_annotation_episode.fluorescence_result_worker"])
    assert _dependencies(sources) == []
    assert not {"gene_annotation_episode.fluorescence_event_preparation",
        "gene_annotation_episode.fluorescence_preparation_readers", "gene_annotation_episode.fluorescence_native_reports",
        "gene_annotation_episode.fluorescence_fcs_reader"}.intersection(sources)


def test_report_inputs_use_existing_received_authority_and_exact_store_path(selected, monkeypatch):
    f = selected
    chosen = deepcopy(f.selected)
    chosen.update(version="native_fluorescence_job_v2", preparations=[], report_inputs=[])
    chosen["software"] = _software(chosen["software"])
    raw = b"# FACS-based Cell Sorting and Enrichment Research Log\n"
    reference = f.store.artifact(raw, "text/plain")
    file = identity(raw, format="text")
    path = str(f.store.path / "artifacts" / file["sha256"][:2] / file["sha256"])
    chosen["report_inputs"] = [dict(file=file, path=path, source_key="report", profile=FACS_PROFILE, fields=[], association_file=None)]
    assignment = {**f.assignment, "requested_job": routed_request(f, chosen)}
    with pytest.raises(ValueError, match="not_received"):
        f.owner._fluorescence_inputs(f.root, assignment)
    f.ledger.receive(f.root.episode_id, [reference], kind="own_action")
    assert f.owner._fluorescence_inputs(f.root, assignment) == [*f.input_refs, reference]
    Path(path).unlink()
    monkeypatch.setattr(f.store, "get_artifact", lambda *_: pytest.fail("operand admission read scientific bytes"))
    assert f.owner._fluorescence_inputs(f.root, assignment) == [*f.input_refs, reference]
    wrong = deepcopy(chosen)
    wrong["report_inputs"][0]["path"] = str(f.directory / "unselected-report")
    with pytest.raises(ValueError, match="selected_path_mismatch"):
        f.owner._fluorescence_inputs(f.root, {**f.assignment, "requested_job": routed_request(f, wrong)})


def test_supplied_report_custody_is_not_taken_over_and_generated_outputs_stay_protected(monkeypatch):
    from gene_annotation_episode.fluorescence_result_receipts import VERSION
    original = identity(b"supplied report", format="text")
    generated = identity(b"generated report envelope", format="fluorescence_report_batch_v1")
    prepared = identity(b"generated prepared values", format="fluorescence_prepared_event_data_v1")
    receipt = dict(version=VERSION, intent=dict(operation_key="run:child:0"), worker_capture=None,
        capture=dict(files=[dict(role=role, retained=dict(file=file)) for role, file in (
            ("report_input:0", original), ("report_batch:0", generated), ("prepared_data:0", prepared))]))
    class DB:
        def execute(self, *args):
            return [dict(episode_id="child", result=json.dumps(dict(result=receipt)))]
    owner = SimpleNamespace(store=SimpleNamespace(db=DB()), run_id="run",
        native_fluorescence_returns=SimpleNamespace(context=lambda _: SimpleNamespace(scope={})))
    reader = FluorescenceResultReceipts(owner)
    reads = []
    monkeypatch.setattr(reader, "read_completed", lambda **kwargs: reads.append(kwargs))
    assert not reader.owns_reference(original["artifact_ref"]) and reads == []
    assert reader.owns_reference(generated["artifact_ref"]) and reader.owns_reference(prepared["artifact_ref"])
    assert len(reads) == 2


def test_prepared_artifacts_do_not_increase_acquisition_and_publication_copies_selected_cells(tmp_path):
    with Store(tmp_path / "store") as store:
        plan = _report_plan(store, tmp_path / "case")
        result = worker.execute_fluorescence_worker(plan)
        receipt = receipt_fixture(store)
        receipt["native"]["original_plan"] = plan["original_plan"]
        receipt["capture"] = plan["capture"]
        receipt["worker_capture"]["result"] = result
        receipt["projection"], receipt["context"] = output(plan, "projection"), output(plan, "context")
        requested = schema(PROJECTION_SOURCE, CONTEXT_SOURCE, FAILURE_SOURCE)
        owner = SimpleNamespace(store=store, acquired_record_unit=2, handoff_unit=3,
            native_fluorescence_returns=SimpleNamespace(context=lambda _: SimpleNamespace(
                request={"report_contract": {"measurements": {"schema": requested}}})))
        host = NativeFluorescenceResults(owner)
        facts, complete = host.receipts.publication(receipt)
        assert complete and facts[PROJECTION_SOURCE] == [receipt["projection"]]
        assert facts[CONTEXT_SOURCE] == [receipt["context"]] and facts[SAVED_SOURCE] == []
        population = host.receipts.acquisition_population(receipt)
        receipt["capture"]["files"].extend(deepcopy(receipt["capture"]["files"]))
        assert host.receipts.acquisition_population(receipt) == population


def test_declared_prepared_and_report_requests_validate_without_exposing_other_fields(tmp_path):
    from jsonschema import Draft202012Validator
    with Store(tmp_path / "store") as store:
        for factory, name in ((_prepared_plan, "prepared"), (_report_plan, "report")):
            plan = factory(store, tmp_path / name)
            selected_job = plan["original_plan"]["requested_job"]["native_fluorescence"]
            assert validate_fluorescence_selector(plan["selector"], job=selected_job) == plan["selector"]
            bad = deepcopy(plan["selector"])
            bad["selection"]["requests"][-1] = _request("native_comparison", "native_value", native_report_key="undeclared")
            with pytest.raises(ValueError):
                validate_fluorescence_selector(bad, job=selected_job)
        for code, role in (("preparation_unavailable", "prepared_batch:0"), ("preparation_incompatible", "prepared_data:0"),
                ("preparation_failed", "preparation_parameters:0"), ("report_batch_invalid", "report_batch:0"),
                ("report_batch_unavailable", "report_input:0")):
            Draft202012Validator(FAILURE_SCHEMA).validate(dict(code=code, stage="capture", input_index=0, role=role))
