"""Supplied-data calculations only; all tests are run under local_jobs."""
from copy import deepcopy
import builtins
import hashlib
import importlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.rna_structure_comparison_worker import (
    comparison_input_digests, comparison_calculation_key, run_rna_comparison_worker,
)

f = importlib.import_module("verification.tool_graders_rna_comparison_worker_2026-10-26_369.fixture_helpers")


def test_value_and_byte_digests_are_distinct_and_membership_order_is_preserved():
    selector, operands = f.scan()
    rows = comparison_input_digests(selector, operands["data"])
    assert [r["member_id"] for r in rows] == ["WT", "A", "B", "C", "D", "NS", "NT"]
    assert rows[0]["input_sha256"] == digest(operands["data"]["WT"])
    assert rows[0]["input_sha256"] != f.sha(operands["data"]["WT"])
    assert rows[-1]["kind"] == "declared_absent"
    assert rows[-1]["input_sha256"] == rows[-2]["input_sha256"]
    reversed_dict = dict(reversed(list(operands["data"].items())))
    assert comparison_input_digests(selector, reversed_dict) == rows


def test_calculation_identity_excludes_projection_but_includes_question_and_parameters():
    selector, operands = f.pair()
    before = deepcopy(selector)
    key = comparison_calculation_key(selector, operands["data"])
    selector["projections"] = [f.projection("structures", fields=["pairs"])]
    assert comparison_calculation_key(selector, operands["data"]) == key
    selector["question"]["comparisons"][0]["energy"]["baseline_absolute_tolerance"] = 0.1
    assert comparison_calculation_key(selector, operands["data"]) != key
    selector = before
    selector["parameters"]["arithmetic"] = "unapproved_arithmetic"
    with pytest.raises(ValueError):
        comparison_calculation_key(selector, operands["data"])


@pytest.mark.parametrize("corruption", ["extra_member", "missing_member", "extra_field", "wrong_sheet", "false_failure"])
def test_selected_member_data_cannot_expand_or_substitute(corruption):
    selector, operands = f.pair()
    data = operands["data"]
    if corruption == "extra_member":
        data["unselected"] = f.b.blank()
    elif corruption == "missing_member":
        del data["V"]
    elif corruption == "extra_field":
        data["V"]["producer_path"] = "/unselected/path"
    elif corruption == "wrong_sheet":
        data["V"]["original_sheet"] = data["WT"]["original_sheet"]
    else:
        data["V"]["received_failure"] = f.b.failure()
    with pytest.raises(ValueError):
        comparison_input_digests(selector, data)


@pytest.mark.parametrize("field,value", [("version", "other"), ("directory", "relative"),
    ("result_receipt_key", "rna_comparison_receipt:wrong"), ("calculation_key", "rna_comparison_calculation:" + "0" * 64)])
def test_worker_rejects_changed_plan_identity(tmp_path, field, value):
    selector, operands = f.pair()
    plan = f.plan(tmp_path, selector, operands)
    plan[field] = value
    with pytest.raises(ValueError):
        run_rna_comparison_worker(plan)
    assert not (tmp_path / "worker-result.json").exists()


@pytest.mark.parametrize("fault", ["missing", "changed_bytes", "wrong_size", "bool_size", "duplicate_key", "nonfinite", "noncanonical", "unexpected_field", "symlink"])
def test_worker_input_faults_are_execution_failures_not_scientific_missing_values(tmp_path, fault):
    selector, operands = f.pair()
    plan = f.plan(tmp_path, selector, operands)
    path = tmp_path / "input-data.json"
    if fault == "missing":
        path.unlink()
    elif fault == "changed_bytes":
        path.write_bytes(b"{}\n")
    elif fault == "wrong_size":
        plan["input_data"]["size_bytes"] += 1
    elif fault == "bool_size":
        plan["input_data"]["size_bytes"] = True
    elif fault == "unexpected_field":
        plan["producer_directory"] = "/not-selected"
    elif fault == "symlink":
        original = tmp_path / "other.json"
        path.rename(original)
        path.symlink_to(original)
    else:
        raw = {"duplicate_key": b'{"WT":null,"WT":null}\n', "nonfinite": b'{"WT":NaN}\n',
            "noncanonical": json.dumps(operands["data"], indent=2).encode()}[fault]
        path.write_bytes(raw)
        plan["input_data"].update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
    with pytest.raises((ValueError, OSError)):
        run_rna_comparison_worker(plan)
    assert not (tmp_path / "sheet.json").exists()


def test_worker_retains_all_numeric_components_and_exactly_two_requested_structure_fields(tmp_path, monkeypatch):
    selector, operands = f.pair()
    plan = f.plan(tmp_path, selector, operands)
    original_import = builtins.__import__
    def guarded(name, *args, **kwargs):
        assert name not in ("RNA", "gene_annotation_episode.native_rna_structure_worker")
        return original_import(name, *args, **kwargs)
    def forbidden(*args, **kwargs):
        raise AssertionError("No native/network/subprocess operation is permitted")
    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    result = run_rna_comparison_worker(plan)
    components = f.load(tmp_path / "components.json")
    rows = f.load(tmp_path / "projections.json")
    assert f.b.values(components["comparisons"][0]["energy"]["components"])["energy_delta"] == 1.0
    assert f.b.values(components["comparisons"][0]["components"])["preserved_pair_count"] == 3
    assert f.b.values(components["comparisons"][0]["components"], "selected")["decidable_site_count"] == 9
    assert [(r["member_id"], r["values"]) for r in rows[2]["payload"]["rows"]] == [
        (m, [{"field": "dot_bracket", "state": "present", "value": "(((...)))", "reason": None}]) for m in ("WT", "V")]
    assert "input_paths" not in f.keys(rows)
    assert "input_paths" in f.keys(components)
    assert result["components_sha256"] == hashlib.sha256((tmp_path / "components.json").read_bytes()).hexdigest()
    before = {p.name: p.read_bytes() for p in tmp_path.glob("*.json")}
    assert run_rna_comparison_worker(plan) == result
    assert before == {p.name: p.read_bytes() for p in tmp_path.glob("*.json")}


def _numerical_cells(value):
    if isinstance(value, dict):
        if "metric" in value and "formula_id" in value:
            return [{k: v for k, v in value.items() if k not in ("population_id", "input_paths")}]
        return [c for v in value.values() for c in _numerical_cells(v)]
    if isinstance(value, list):
        return [c for v in value for c in _numerical_cells(v)]
    return []


def test_all_eight_filled_examples_match_saved_numerical_answers(tmp_path):
    saved = f.load(f.REPO / "verification/tool_graders_rna_comparison_calculations_2026-10-26_367/FILLED_EXAMPLES_001.json")
    filled = {}
    for name, example in saved["examples"].items():
        sheet = example["sheet"]
        selector, operands = f.resolved(sheet)
        plan = f.plan(tmp_path / name, selector, operands)
        run_rna_comparison_worker(plan)
        result = f.load(tmp_path / name / "components.json")
        assert _numerical_cells(result) == _numerical_cells(example["components"])
        filled[name] = {"selector": selector, "data": operands["data"], "sheet": f.load(tmp_path / name / "sheet.json"),
            "components": result, "projections": f.load(tmp_path / name / "projections.json")}
    assert len(filled) == 8
    (tmp_path / "filled_eight_worker_examples.json").write_bytes(f.raw({"identity": "synthetic_arithmetic_fixtures", "examples": filled}))


@pytest.mark.parametrize("name,quantity", [("prediction", "native_mfe"), ("evaluation", "native_evaluation")])
def test_retained357_original_values_and_unavailable_arrays_survive_worker(tmp_path, name, quantity):
    packet = f.load(f.REPO / "tests/fixtures/rna_structure_comparison_calculations_367/retained357" / (name + ".json"))
    original, software = packet["sheet"], packet["bundle"]["software"]
    from gene_annotation_episode.rna_structure_comparison_inputs import populate_rna_comparison_sheet
    selected = f.b.selector([f.b.member(original, key="WT")], [], scan=f.b.scan_request({**f.b.energy_request(), "quantity": quantity}))
    sheet = populate_rna_comparison_sheet(selected, operands={"WT": {
        "original_sheet": original, "original_bundle_software": software, "received_failure": None}})
    selector, operands = f.resolved(sheet, [f.projection("scan_energy", metrics=["baseline_selected_energy", "baseline_rank_start"])])
    run_rna_comparison_worker(f.plan(tmp_path, selector, operands))
    retained = f.load(tmp_path / "sheet.json")["operands"][0]["original_sheet"]
    assert retained == original
    cells = f.load(tmp_path / "projections.json")[0]["payload"]["measurements"]
    assert [c["value"] for c in cells] == [-1.2000000476837158, 1]
    assert cells[0]["origin"] == ("retained_native_prediction" if name == "prediction" else "retained_native_evaluation")
    assert {r["name"]: r["state"] for r in retained["model"]["other_observed_settings"] if r["name"] in ("alias", "pair", "rtype")} == {
        "alias": "unavailable", "pair": "unavailable", "rtype": "unavailable"}


def test_worker_preserves_sheet_when_later_immutable_component_write_fails(tmp_path):
    selector, operands = f.pair()
    plan = f.plan(tmp_path, selector, operands)
    (tmp_path / "components.json").write_bytes(b'{"intentional_conflict":true}\n')
    with pytest.raises(ValueError, match="immutable_record_conflict"):
        run_rna_comparison_worker(plan)
    assert f.load(tmp_path / "sheet.json")["selected_question"] == selector["question"]
    assert (tmp_path / "components.json").read_bytes() == b'{"intentional_conflict":true}\n'
    assert not (tmp_path / "worker-result.json").exists()
