"""Finite result tests on explicit synthetic retained producer artifacts.

The fixture software declarations are not an installed-producer claim. Root
owns authentic original execution and full episode verification. Run this file
only through the coordinator's existing bounded verification lifecycle.
"""
import builtins
from copy import deepcopy
import errno
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode import fluorescence_event_contracts as core
from gene_annotation_episode import fluorescence_result_worker as worker
from gene_annotation_episode.fluorescence_event_readers import parse_fluorescence_csv, parse_fluorescence_table_snapshot
from gene_annotation_episode.fluorescence_execution_common import canonical, digest, identity
from gene_annotation_episode.fluorescence_result_contracts import OUTPUTS
from gene_annotation_episode.native_fluorescence_capture import capture_fluorescence_native_files
from gene_annotation_episode.native_fluorescence_contracts import OPERATIONS, unavailable_fluorescence_input, validate_fluorescence_manifest
from gene_annotation_episode.native_fluorescence_preparation import build_native_fluorescence_worker_plan, build_saved_fluorescence_worker_plan
from gene_annotation_episode.native_fluorescence_storage import read_json
from gene_annotation_episode.native_file_capture import capture_native_file, retained_native_file
from gene_annotation_episode.state import Store
from test_native_fluorescence_contracts import event_input, job, plan as original_plan
from test_fluorescence_event_calculations import _batch, _sheet, _standard_parameters, _request

VALUES = [90, 100, 125, 150, 200, 250, 300, 350]


def selection(gate="gate-0", domain="domain-0", channel="channel-0"):
    return dict(requests=[_request("fraction", "selected_fraction", gate_key=gate, denominator="parent"),
        _request("fraction", "selected_percent", gate_key=gate, denominator="parent"),
        _request("intensity", "selected_intensity_mean", gate_key=gate, domain_key=domain, channel_key=channel),
        _request("intensity", "selected_intensity_median", gate_key=gate, domain_key=domain, channel_key=channel)],
        offset=0, limit=20)


def selector(*, selected=None, fields=None, file=None, parameters=None):
    return dict(version="fluorescence_result_selector_v1", mode="native_result" if file is None else "saved_sheet_recalculation",
        selection=selected or selection(), context_fields=[] if fields is None else fields,
        saved_sheet_file=file, parameters=parameters)


def _retain(store, root, raw, format_, name="replacement.json"):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_bytes(raw)
    file = capture_native_file(store, directory=str(root), relative_path=name, format=format_)
    return dict(file=file, path=str(retained_native_file(store, file)))


def native_plan(store, root, *, parser="csv", rows=None, count=1, operation=OPERATIONS[0], unavailable=False,
                manifest=True, paired_controls=False):
    root = Path(root)
    values = VALUES if rows is None else rows
    raw = (("signal\n" + "".join(("" if value is None else str(value)) + "\n" for value in values)).encode()
        if parser == "csv" else core.canonical(dict(schema=core.TABLE_SCHEMA, columns=["signal"], rows=[[v] for v in values])))
    inputs = [event_input(root / "inputs", raw, index=i, parser=parser) for i in range(count)]
    selected_job = job(root, inputs=inputs, operation=operation)
    for i, gate in enumerate(selected_job["definitions"]["gates"]):
        gate.update(kind="threshold", domain_key=f"domain-{i}", channel_key=f"channel-{i}",
            lower=dict(value=100, inclusive=True), upper=dict(value=250, inclusive=True))
    selected_job["parameters"] = dict(
        fraction_requests=[dict(gate_key=f"gate-{i}", denominator="parent") for i in range(count)],
        intensity_requests=[dict(gate_key=f"gate-{i}", domain_key=f"domain-{i}", channel_key=f"channel-{i}") for i in range(count)],
        control_requests=[], native_comparison_requests=[])
    if paired_controls:
        assert count >= 2 and count % 2 == 0
        for group in range(count // 2):
            payload = f"synthetic comparison support {group}".encode()
            support_path = root / f"comparison-{group}.json"
            support_path.write_bytes(payload)
            file = identity(payload, format="json")
            selected_job["support_inputs"].append(dict(file=file, path=str(support_path)))
            basis = dict(key=f"declared-support-{group}", evidence_file=file)
            for binding in inputs[group * 2:group * 2 + 2]:
                binding["domain"]["comparison_basis"] = deepcopy(basis)
                binding["channels"][0]["analyte"] = dict(namespace="synthetic", identifier="signal", file=file,
                    source_key=None, location={key: None for key in (
                        "record_ordinal", "line_start", "line_end", "byte_start", "byte_end")})
            selected_job["definitions"]["control_pairs"].append(dict(key=f"pair-{group}",
                target_gate_key=f"gate-{2 * group}", control_gate_key=f"gate-{2 * group + 1}",
                denominator="parent", comparison_basis=basis))
            selected_job["parameters"]["control_requests"].append(dict(control_key=f"pair-{group}",
                include_legacy_clipping=True))
    original = original_plan(root, selected_job=selected_job)
    paths = {row["role"]: Path(original["attempt_directory"]) / row["relative_path"] for row in original["outputs"]}
    input_outcomes = []
    for i, binding in enumerate(inputs):
        parsed = (unavailable_fluorescence_input(binding, code="source_unavailable") if unavailable else
            (parse_fluorescence_csv(raw, **{k: binding[k] for k in ("source", "sample", "channels", "domain", "format_spec")})
             if parser == "csv" else parse_fluorescence_table_snapshot(raw,
                **{k: binding[k] for k in ("source", "sample", "channels", "domain")})))
        batch = dict(version="fluorescence_parsed_batch_v1", original_plan_sha256=digest(original), input_index=i,
            input_binding_sha256=digest(binding), software_sha256=digest(selected_job["software"]), parse=parsed)
        batch_raw = core.canonical(batch) + b"\n"
        for role, payload in ((f"event_input:{i}", raw), (f"event_batch:{i}", batch_raw)):
            paths[role].parent.mkdir(parents=True, exist_ok=True)
            paths[role].write_bytes(payload)
        input_outcomes.append(dict(input_index=i, source_file=binding["source"]["file"],
            batch_file=identity(batch_raw, format="fluorescence_parsed_batch_v1"), extent=parsed["source"]["extent"]))
    for i, support in enumerate(selected_job["support_inputs"]):
        paths[f"support_input:{i}"].parent.mkdir(parents=True, exist_ok=True)
        paths[f"support_input:{i}"].write_bytes(Path(support["path"]).read_bytes())
    if manifest:
        outputs = []
        for spec in original["outputs"][:-1]:
            file = identity(paths[spec["role"]].read_bytes(), format=spec["format"])
            outputs.append(dict(role=spec["role"], declaration=dict(relative_path=spec["relative_path"], format=spec["format"],
                state="present", sha256=file["sha256"], size_bytes=file["size_bytes"])))
        value = validate_fluorescence_manifest(dict(version="fluorescence_native_manifest_v1", original_plan_sha256=digest(original),
            identity=original["identity"], requested_job_sha256=original["identity"]["requested_job_sha256"], operation=operation,
            mode=selected_job["mode"], software_sha256=digest(selected_job["software"]), outputs=outputs,
            inputs=input_outcomes, support=[dict(input_index=i, file=row["file"])
                for i, row in enumerate(selected_job["support_inputs"])], failures=[]), original_plan=original)
        paths["manifest"].write_bytes(canonical(value) + b"\n")
    capture = capture_fluorescence_native_files(store, original_plan=original,
        source_action_receipt_ref="artifact_" + "3" * 64, writer_closure_receipt_ref="artifact_" + "4" * 64, driver_started=True)
    return build_native_fluorescence_worker_plan(directory=str(root / "worker"), original_plan=original, capture=capture,
        selector=selector(fields=["sources", "samples", "channels", "domains", "populations", "gates"]))


def saved_plan(store, root):
    root = Path(root)
    sheet = _sheet([_batch([[v] for v in VALUES])])
    sheet["samples"][0]["label"] = "CD4 α"
    retained = _retain(store, root / "supplied", core.canonical(sheet) + b"\n", core.SHEET_SCHEMA, "sheet.json")
    selected = selection("g", "s.raw", "s.raw.c0")
    return build_saved_fluorescence_worker_plan(directory=str(root / "worker"), sheet=retained,
        selector=selector(selected=selected, fields=["samples"], file=retained["file"], parameters=_standard_parameters()))


def output(plan, role):
    return read_json(Path(plan["directory"]) / next(name for key, name, _ in OUTPUTS if key == role))


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("parser", ["csv", "table_snapshot"])
def test_common_cells_and_exact_unicode_artifacts(tmp_path, monkeypatch, parser, operation):
    with Store(tmp_path / "store") as store:
        plan = native_plan(store, tmp_path / "case", parser=parser, operation=operation)
        before = deepcopy(plan)
        calls = []
        calculate = worker.calculate_fluorescence_sheet
        def once(*args, **kwargs):
            calls.append(1)
            return calculate(*args, **kwargs)
        monkeypatch.setattr(worker, "calculate_fluorescence_sheet", once)
        monkeypatch.setattr("socket.socket", lambda *a, **k: pytest.fail("unexpected acquisition"))
        monkeypatch.setattr("subprocess.Popen", lambda *a, **k: pytest.fail("unexpected subprocess"))
        result = worker.execute_fluorescence_worker(plan)
        assert calls == [1] and plan == before
        assert result["native_binding"] and result["original_events_acquired"] and result["analysis_complete"]
        assert result["native_outcome"] == "complete"
        projected = output(plan, "projection")
        assert [row["value"] for row in projected["rows"]] == [.625, 62.5, 165, 150]
        components = output(plan, "calculations")
        assert all(row in components["cells"] for row in projected["rows"])
        for role in ("sheet", "calculations", "projection", "context"):
            value = output(plan, role)
            raw = (Path(plan["directory"]) / f"{role}.json").read_bytes()
            assert raw == core.canonical(value) + b"\n"
            spec = next(row["declaration"] for row in result["outputs"] if row["role"] == role)
            assert spec["sha256"] == hashlib.sha256(raw).hexdigest() and spec["size_bytes"] == len(raw)
        assert core.digest(output(plan, "sheet")) == components["sheet_sha256"]
        assert core.canonical(output(plan, "sheet")) != canonical(output(plan, "sheet"))


def test_missing_manifest_and_later_batch_preserve_independent_first_source(tmp_path):
    with Store(tmp_path / "store") as store:
        plan = native_plan(store, tmp_path / "case", count=2, manifest=False)
        next(row for row in plan["capture"]["files"] if row["role"] == "event_batch:1")["retained"] = None
        result = worker.execute_fluorescence_worker(plan)
        assert result["native_binding"] and result["original_events_acquired"] and result["native_outcome"] == "partial"
        assert not result["analysis_complete"]
        assert [row["value"] for row in output(plan, "projection")["rows"]] == [.625, 62.5, 165, 150]
        cells = output(plan, "calculations")["cells"]
        assert all(row["value"] is None for row in cells if row["request"]["gate_key"] == "gate-1")


@pytest.mark.parametrize("change", ["plan", "binding", "software", "metadata", "origin", "label", "source", "manifest"])
def test_foreign_batch_or_bytes_never_become_measurements(tmp_path, change):
    with Store(tmp_path / "store") as store:
        plan = native_plan(store, tmp_path / "case", count=2)
        role = "event_input:0" if change == "source" else "manifest" if change == "manifest" else "event_batch:0"
        row = next(row for row in plan["capture"]["files"] if row["role"] == role)
        if change == "source":
            raw = b"changed source bytes"
        else:
            value = read_json(row["retained"]["path"])
            if change in ("plan", "manifest"): value["original_plan_sha256"] = "0" * 64
            elif change == "binding": value["input_binding_sha256"] = "0" * 64
            elif change == "software": value["software_sha256"] = "0" * 64
            elif change == "metadata": value["parse"]["source"]["metadata"][0]["value"] = "reassigned"
            elif change == "origin": value["parse"]["events"][0]["values"][0]["measurement"]["state"] = "observed"
            elif change == "label": value["parse"]["sample"]["label"] = "reassigned"
            raw = core.canonical(value) + b"\n"
        row["retained"] = _retain(store, tmp_path / "changed", raw, row["format"])
        result = worker.execute_fluorescence_worker(plan)
        assert result["original_events_acquired"] and result["native_outcome"] == "partial"
        assert not result["analysis_complete"] and result["failures"]
        values = [row["value"] for row in output(plan, "projection")["rows"]]
        assert values == ([.625, 62.5, 165, 150] if change == "manifest" else [None] * 4)
        assert any(row["value"] == .625 for row in output(plan, "calculations")["cells"] if row["request"]["gate_key"] == "gate-1")


@pytest.mark.parametrize("change,issue_code", [("absent", "source_unavailable"),
    ("bytes", "retained_artifact_mismatch"), ("identity", "retained_artifact_mismatch"), ("intact", None)])
def test_support_custody_qualifies_only_dependent_control_and_survives_saved_recalculation(
        tmp_path, monkeypatch, change, issue_code):
    with Store(tmp_path / "store") as store:
        plan = native_plan(store, tmp_path / "case", count=4, paired_controls=True)
        requests = plan["selector"]["selection"]["requests"]
        requests.extend(_request("control", metric, control_key=f"pair-{index}")
            for index in range(2) for metric in ("control_difference_fraction",
                "control_difference_percentage_points", "legacy_nonnegative_difference_percentage_points"))
        captured = next(row for row in plan["capture"]["files"] if row["role"] == "support_input:0")
        if change == "absent":
            captured["retained"] = None
        elif change == "bytes":
            Path(captured["retained"]["path"]).write_bytes(b"corrupted captured evidence")
        elif change == "identity":
            captured["retained"] = _retain(store, tmp_path / "changed", b"different evidence", "json")
        before = deepcopy(plan["original_plan"]["requested_job"]["native_fluorescence"])
        result = worker.execute_fluorescence_worker(plan)
        assert result["native_binding"] and result["original_events_acquired"]
        assert result["native_outcome"] == ("complete" if issue_code is None else "partial")
        assert result["analysis_complete"] is (issue_code is None)
        sheet, calculations, projection = (output(plan, role) for role in ("sheet", "calculations", "projection"))
        assert sheet["control_pairs"] == before["definitions"]["control_pairs"]
        assert sheet["gate_definitions"] == before["definitions"]["gates"]
        assert sheet["population_definitions"] == before["definitions"]["populations"]
        assert [row["comparison_basis"] for row in sheet["measurement_domains"]] == [
            row["domain"]["comparison_basis"] for row in before["inputs"]]
        assert [row["analyte"] for row in sheet["channels"]] == [row["channels"][0]["analyte"] for row in before["inputs"]]
        assert [row["value"] for row in calculations["cells"] if row["request"]["metric"] == "selected_event_count"] == [5] * 4
        assert [row["value"] for row in calculations["cells"] if row["request"]["metric"] == "retained_event_count"] == [8] * 4
        assert [row["value"] for row in calculations["cells"] if row["request"]["metric"] == "selected_fraction"] == [.625] * 4
        assert [row["value"] for row in calculations["cells"] if row["request"]["metric"] == "selected_intensity_mean"] == [165] * 4
        expected_control = [0] * 3 if issue_code is None else [None] * 3
        assert [row["value"] for row in projection["rows"]] == [.625, 62.5, 165, 150, *expected_control, 0, 0, 0]
        assert all(row in calculations["cells"] for row in projection["rows"])
        assert sheet["issues"] == ([] if issue_code is None else [core.issue(issue_code, "input", control_key="pair-0")])
        assert not any(problem["code"] == "control_pair_incompatible" for row in projection["rows"] for problem in row["issues"])
        if issue_code is not None:
            assert any(row["input_index"] == 0 and row["role"] == "support_input:0" for row in result["failures"])
            assert all(row["state"] == "unavailable" and row["population"]["extent"] == "unavailable"
                for row in projection["rows"] if row["request"]["control_key"] == "pair-0")

        raw = (Path(plan["directory"]) / "sheet.json").read_bytes()
        retained = _retain(store, tmp_path / "supplied", raw, core.SHEET_SCHEMA)
        saved = build_saved_fluorescence_worker_plan(directory=str(tmp_path / "saved"), sheet=retained,
            selector=selector(selected=deepcopy(plan["selector"]["selection"]), file=retained["file"],
                parameters=deepcopy(before["parameters"])))
        shutil.rmtree(tmp_path / "case")
        def forbidden(*args, **kwargs): pytest.fail("saved support qualification reacquired native input")
        monkeypatch.setattr(worker, "_native", forbidden)
        monkeypatch.setattr("socket.socket", forbidden)
        monkeypatch.setattr("subprocess.Popen", forbidden)
        recalculated = worker.execute_fluorescence_worker(saved)
        assert recalculated["analysis_complete"] and recalculated["failures"] == []
        assert not recalculated["original_events_acquired"] and recalculated["native_outcome"] == "not_applicable"
        assert output(saved, "projection") == projection
        assert (Path(saved["directory"]) / "sheet.json").read_bytes() == raw


@pytest.mark.parametrize("unavailable", [False, True])
def test_complete_empty_is_distinct_from_all_unavailable(tmp_path, unavailable):
    with Store(tmp_path / "store") as store:
        plan = native_plan(store, tmp_path / "case", rows=[], unavailable=unavailable)
        result = worker.execute_fluorescence_worker(plan)
        assert result["original_events_acquired"] is (not unavailable)
        assert result["native_outcome"] == ("unavailable" if unavailable else "complete")
        counts = [row for row in output(plan, "calculations")["cells"] if row["request"]["kind"] == "population"]
        assert all(row["value"] is None for row in counts) if unavailable else all(row["value"] == 0 for row in counts)


def test_saved_sheet_recalculation_has_no_source_decoder_or_native_work(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        original = native_plan(store, tmp_path / "case", rows=[*VALUES[:-1], None])
        worker.execute_fluorescence_worker(original)
        raw = (Path(original["directory"]) / "sheet.json").read_bytes()
        retained = _retain(store, tmp_path / "supplied", raw, core.SHEET_SCHEMA)
        parameters = deepcopy(original["original_plan"]["requested_job"]["native_fluorescence"]["parameters"])
        parameters["fraction_requests"] = [dict(gate_key="gate-0", denominator="evaluable")]
        selected = dict(requests=[_request("fraction", "selected_fraction", gate_key="gate-0", denominator="evaluable")], offset=0, limit=1)
        plan = build_saved_fluorescence_worker_plan(directory=str(tmp_path / "saved"), sheet=retained,
            selector=selector(selected=selected, file=retained["file"], parameters=parameters))
        shutil.rmtree(tmp_path / "case")
        def forbidden(*args, **kwargs): pytest.fail("saved calculation touched native work")
        monkeypatch.setattr(worker, "_native", forbidden)
        monkeypatch.setattr("socket.socket", forbidden)
        monkeypatch.setattr("subprocess.Popen", forbidden)
        import_ = builtins.__import__
        def imports(name, *args, **kwargs):
            assert not any(part in name for part in ("flowio", "fluorescence_event_readers", "fluorescence_fcs_reader", "native_fluorescence_driver"))
            return import_(name, *args, **kwargs)
        monkeypatch.setattr(builtins, "__import__", imports)
        result = worker.execute_fluorescence_worker(plan)
        assert result["analysis_complete"] and result["native_outcome"] == "not_applicable"
        assert not result["native_binding"] and not result["original_events_acquired"]
        assert output(plan, "projection")["rows"][0]["value"] == 5 / 7
        assert (Path(plan["directory"]) / "sheet.json").read_bytes() == raw


def test_saved_worker_resource_failure_is_not_converted_to_a_sheet(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        plan = saved_plan(store, tmp_path / "case")
        def fail(*args, **kwargs): raise OSError(errno.ENOMEM, "controlled allocation failure")
        monkeypatch.setattr(worker, "regular", fail)
        with pytest.raises(OSError): worker.execute_fluorescence_worker(plan)
        assert not (Path(plan["directory"]) / "worker-result.json").exists()


def test_completed_worker_replays_without_calculator_or_operand_read(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        plan = saved_plan(store, tmp_path / "case")
        result = worker.execute_fluorescence_worker(plan)
        monkeypatch.setattr(worker, "calculate_fluorescence_sheet", lambda *a, **k: pytest.fail("recalculated"))
        monkeypatch.setattr(worker, "_operand", lambda *a, **k: pytest.fail("reacquired"))
        assert worker.execute_fluorescence_worker(plan) == result
