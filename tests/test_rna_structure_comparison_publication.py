"""Actual bounded worker and retained-byte publication checks, not E authority."""
from copy import deepcopy
import importlib
import json
import socket

import pytest

from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.state import Store
from gene_annotation_episode.rna_structure_comparison_contracts import validate_rna_comparison_components
from gene_annotation_episode import rna_structure_comparison_publication as p

f = importlib.import_module("verification.tool_graders_rna_comparison_worker_2026-10-26_369.fixture_helpers")
POLICY = LocalJobPolicy(**p.POLICY)


def prepare(store, directory, selector, operands, *, key=f.KEY):
    return p.prepare_rna_comparison_grading(store, selector=selector, operands=operands,
        result_receipt_key=key, directory=directory, policy=POLICY)


def validate(store, prepared, selector, operands, *, key=f.KEY):
    return p.validate_prepared_rna_comparison(store, prepared, selector=selector, operands=operands, result_receipt_key=key)


def read(store, ref):
    return p._artifact_value(store, ref)


def forbidden(*args, **kwargs):
    raise AssertionError("Replay/publication must not execute or acquire anything")


@pytest.fixture
def actual(tmp_path):
    selector, operands = f.pair()
    with Store(tmp_path / "store") as store:
        directory = tmp_path / "grading"
        prepared = prepare(store, directory, selector, operands)
        assert prepared["delivery_complete"], prepared
        yield store, directory, selector, operands, prepared


def test_actual_worker_cgroup_receipt_full_retention_and_exact_publication(actual, monkeypatch):
    store, directory, selector, operands, prepared = actual
    assert set(prepared) == p.PREPARED_FIELDS
    assert prepared["preparation_failure"] is None
    receipt = read(store, prepared["worker_receipt_artifact_ref"])
    execution = read(store, receipt["execution_receipt_artifact_ref"])
    assert execution["returncode"] == 0 and execution["error"] is None
    assert execution["metadata"]["policy"] == p.POLICY
    assert execution["metadata"]["verified_cgroup"]["memory_max"] == 20 * 1024 ** 3
    assert execution["metadata"]["verified_cgroup"]["runtime_max"] == "infinity"
    assert execution["metadata"]["verified_cgroup"]["memory_swap_max"] == 0
    plan = read(store, receipt["plan_artifact_ref"])
    assert set(plan) == {"version", "selector", "input_data", "result_receipt_key", "calculation_key", "directory"}
    assert read(store, receipt["input_data_artifact_ref"]) == operands["data"]
    assert "original_receipts" not in f.keys(read(store, receipt["input_data_artifact_ref"]))
    monkeypatch.setattr(p, "run_local_job", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    checked = validate(store, prepared, selector, operands)
    rows = p.publish_selected_rna_comparison_rows(store, selector=selector, prepared=prepared,
        operands=operands, result_receipt_key=f.KEY)
    assert rows == prepared["projection_rows"] == checked["projection_rows"]
    assert [cell["value"] for cell in rows[0]["payload"]["rows"][0]["measurements"]] == [-3.0, -2.0, 1.0]
    assert "input_paths" not in f.keys(rows) and "input_paths" in f.keys(checked["components"])
    (directory.parent / "filled_actual_pair.json").write_bytes(f.raw({"identity": "synthetic_inputs_actual_bounded_worker",
        "prepared": prepared, "worker_receipt": receipt, "execution": execution, **checked}))


def test_completed_preparation_replays_from_retained_custody_without_local_outputs(actual, monkeypatch):
    store, directory, selector, operands, prepared = actual
    before = (directory / "prepared.json").read_bytes()
    for filename in ("sheet.json", "components.json", "projections.json", "worker-result.json", "input-data.json"):
        (directory / filename).unlink()
    monkeypatch.setattr(p, "run_local_job", forbidden)
    assert prepare(store, directory, selector, operands) == prepared
    assert (directory / "prepared.json").read_bytes() == before


@pytest.mark.parametrize("keep_final_receipt", [False, True])
def test_completed_worker_recovery_without_prepared_file_never_restarts(actual, monkeypatch, keep_final_receipt):
    store, directory, selector, operands, prepared = actual
    (directory / "prepared.json").unlink()
    if keep_final_receipt:
        for name in ("execution-receipt.json", "plan.json", "worker-started.json", "components.json"):
            (directory / name).unlink()
    else:
        (directory / "worker-receipt.json").unlink()
    monkeypatch.setattr(p, "run_local_job", forbidden)
    assert prepare(store, directory, selector, operands) == prepared


def test_incomplete_start_is_explicit_and_does_not_dispatch_or_rewrite(actual, monkeypatch):
    store, directory, selector, operands, _ = actual
    for name in ("prepared.json", "worker-receipt.json", "execution-receipt.json"):
        (directory / name).unlink()
    before = {path.name: path.read_bytes() for path in directory.glob("*.json")}
    monkeypatch.setattr(p, "run_local_job", forbidden)
    with pytest.raises(ValueError, match="preparation_incomplete"):
        prepare(store, directory, selector, operands)
    assert before == {path.name: path.read_bytes() for path in directory.glob("*.json")}


@pytest.mark.parametrize("mutation", ["parameters", "selection", "question", "key", "references", "receipt", "sheet_digest"])
def test_replay_rejects_changed_original_intent(actual, mutation):
    store, directory, selector, operands, prepared = actual
    selector, operands = deepcopy(selector), deepcopy(operands)
    key = f.KEY
    if mutation == "parameters":
        selector["parameters"]["tie_rule"] = "epsilon"
    elif mutation == "selection":
        selector["projections"][2]["fields"] = ["pairs"]
    elif mutation == "question":
        selector["question"]["comparisons"][0]["energy"]["baseline_absolute_tolerance"] = 0.1
    elif mutation == "key":
        key = "rna_comparison_receipt:" + "4" * 64
    elif mutation == "references":
        operands["selected_references"].append("source_unselected")
    elif mutation == "receipt":
        operands["original_receipts"]["WT"]["operation_key"] = "other"
    else:
        selector["question"]["membership"][0]["saved_input"]["sheet_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        validate(store, prepared, selector, operands, key=key)
    with pytest.raises(ValueError):
        prepare(store, directory, selector, operands, key=key)


@pytest.mark.parametrize("field", ["comparison_sheet_artifact_ref", "components_artifact_ref", "projection_rows_artifact_ref", "worker_receipt_artifact_ref"])
def test_missing_retained_artifact_cannot_trigger_recalculation_worker(actual, monkeypatch, field):
    store, directory, selector, operands, prepared = actual
    metadata = store.get(prepared[field])
    path = store.path / "artifacts" / metadata["sha256"][:2] / metadata["sha256"]
    path.unlink()
    monkeypatch.setattr(p, "run_local_job", forbidden)
    with pytest.raises((OSError, ValueError)):
        prepare(store, directory, selector, operands)


def test_corrupt_retained_artifact_bytes_reject_before_number_comparison(actual):
    store, _, selector, operands, prepared = actual
    metadata = store.get(prepared["components_artifact_ref"])
    (store.path / "artifacts" / metadata["sha256"][:2] / metadata["sha256"]).write_bytes(b"{}\n")
    with pytest.raises(ValueError, match="artifact_digest_mismatch"):
        validate(store, prepared, selector, operands)


def rehash_output_chain(store, prepared, *, role, transform):
    """Adversarial fresh artifacts, preserving every old source/receipt byte."""
    candidate = deepcopy(prepared)
    receipt = read(store, candidate["worker_receipt_artifact_ref"])
    entry = next(r for r in receipt["output_artifacts"] if r["role"] == role)
    value = read(store, entry["artifact_ref"])
    transform(value)
    new_ref = store.artifact(f.raw(value), "application/json")
    entry.update(artifact_ref=new_ref, sha256=store.get(new_ref)["sha256"])
    field = {"sheet": "comparison_sheet", "components": "components", "projections": "projection_rows"}[role]
    candidate[field + "_artifact_ref"] = new_ref
    if role != "projections":
        candidate[field + "_sha256"] = entry["sha256"]
    else:
        candidate["projection_rows"] = value
    manifest_entry = next(r for r in receipt["output_artifacts"] if r["role"] == "worker_result")
    manifest = read(store, manifest_entry["artifact_ref"])
    manifest[{"sheet": "sheet_sha256", "components": "components_sha256", "projections": "projection_rows_sha256"}[role]] = entry["sha256"]
    manifest_ref = store.artifact(f.raw(manifest), "application/json")
    manifest_entry.update(artifact_ref=manifest_ref, sha256=store.get(manifest_ref)["sha256"])
    candidate["worker_receipt_artifact_ref"] = store.artifact(f.raw(receipt), "application/json")
    return candidate


@pytest.mark.parametrize("role", ["sheet", "components", "projections"])
def test_rehashed_numerical_outputs_and_request_changes_are_recomputed_not_trusted(actual, role):
    store, _, selector, operands, prepared = actual
    def alter(value):
        if role == "sheet":
            value["selected_question"]["comparisons"][0]["energy"]["baseline_absolute_tolerance"] = 99
        elif role == "components":
            cell = next(c for c in value["comparisons"][0]["energy"]["components"] if c["metric"] == "energy_delta")
            cell["value"] = 7.0
            validate_rna_comparison_components(value, sheet=read(store, prepared["comparison_sheet_artifact_ref"]))
        else:
            value[0]["payload"]["rows"][0]["measurements"][2]["value"] = 7.0
    forged = rehash_output_chain(store, prepared, role=role, transform=alter)
    with pytest.raises(ValueError, match="prepared_mismatch"):
        validate(store, forged, selector, operands)
    assert validate(store, prepared, selector, operands)["projection_rows"] == prepared["projection_rows"]


def test_actual_partial_worker_failure_retains_valid_sheet_and_original_failure_receipt(tmp_path, monkeypatch):
    selector, operands = f.pair()
    original_runner = p.run_local_job
    def conflict(command, **kwargs):
        (kwargs["cwd"] / "components.json").write_bytes(b'{"injected_conflict":true}\n')
        return original_runner(command, **kwargs)
    monkeypatch.setattr(p, "run_local_job", conflict)
    with Store(tmp_path / "store") as store:
        prepared = prepare(store, tmp_path / "grading", selector, operands)
        assert prepared["preparation_failure"] == {"code": "calculation_worker_failed", "member_id": None, "artifact_role": None}
        assert not prepared["delivery_complete"] and prepared["comparison_sheet_artifact_ref"] is not None
        assert prepared["components_artifact_ref"] is None and prepared["projection_rows"] == []
        receipt = read(store, prepared["worker_receipt_artifact_ref"])
        execution = read(store, receipt["execution_receipt_artifact_ref"])
        assert execution["returncode"] != 0
        assert b"practical_immutable_record_conflict" in store.get_artifact(execution["stderr_artifact_ref"])
        assert {r["role"] for r in receipt["output_artifacts"]} == {"sheet", "components"}
        monkeypatch.setattr(p, "run_local_job", forbidden)
        assert prepare(store, tmp_path / "grading", selector, operands) == prepared
        checked = validate(store, prepared, selector, operands)
        assert checked["sheet"] is not None and checked["components"] is None


@pytest.mark.parametrize("fault", ["missing_input", "changed_input", "missing_output", "malformed_output"])
def test_actual_worker_records_specific_input_and_output_failures(tmp_path, monkeypatch, fault):
    selector, operands = f.pair()
    original_runner = p.run_local_job
    def faulty(command, **kwargs):
        path = kwargs["cwd"] / "input-data.json"
        if fault == "missing_input":
            path.unlink()
        elif fault == "changed_input":
            path.write_bytes(b"{}\n")
        result = original_runner(command, **kwargs)
        if fault == "missing_output":
            (kwargs["cwd"] / "projections.json").unlink()
        elif fault == "malformed_output":
            (kwargs["cwd"] / "projections.json").write_bytes(b'{"malformed":\n')
        return result
    monkeypatch.setattr(p, "run_local_job", faulty)
    with Store(tmp_path / "store") as store:
        prepared = prepare(store, tmp_path / "grading", selector, operands)
        expected = {"missing_input": ("retained_input_missing", "input_data"),
            "changed_input": ("retained_input_digest_mismatch", "input_data"),
            "missing_output": ("calculation_output_invalid", "projections"),
            "malformed_output": ("calculation_output_invalid", "projections")}[fault]
        assert prepared["preparation_failure"] == {"code": expected[0], "member_id": None, "artifact_role": expected[1]}
        assert not prepared["delivery_complete"]
        assert prepared["projection_rows"] == []
        if "output" in fault:
            assert prepared["components_artifact_ref"] is not None
        monkeypatch.setattr(p, "run_local_job", forbidden)
        assert prepare(store, tmp_path / "grading", selector, operands) == prepared


def test_qualified_incompatible_energy_is_completed_requested_calculation(tmp_path):
    selector, operands = f.pair(temperature=25.0)
    with Store(tmp_path / "store") as store:
        prepared = prepare(store, tmp_path / "grading", selector, operands)
        assert prepared["delivery_complete"] and prepared["preparation_failure"] is None
        energy = prepared["projection_rows"][0]
        assert energy["delivery"] == "qualified_unavailability"
        assert [cell["value"] for cell in energy["payload"]["rows"][0]["measurements"]] == [-3.0, -2.0, None]
        assert energy["payload"]["rows"][0]["compatibility_state"] == "incompatible"


def test_actual_scan_rank_alias_failure_and_absent_members_have_exact_denominators(tmp_path):
    selector, operands = f.scan()
    with Store(tmp_path / "store") as store:
        prepared = prepare(store, tmp_path / "grading", selector, operands)
        checked = validate(store, prepared, selector, operands)
        assert prepared["delivery_complete"]
        scan = checked["components"]["scan"]
        values = f.b.values(scan["energy_components"])
        assert {k: values[k] for k in ("declared_entry_count", "canonical_member_count", "declared_variant_count",
            "alias_entry_count", "comparable_variant_count", "rank_population_count")} == {
            "declared_entry_count": 8, "canonical_member_count": 7, "declared_variant_count": 6,
            "alias_entry_count": 1, "comparable_variant_count": 3, "rank_population_count": 4}
        assert values["received_failure_variant_count"] == values["not_supplied_variant_count"] == values["not_tested_variant_count"] == 1
        assert (values["baseline_rank_start"], values["baseline_rank_end"], values["baseline_energy_above_minimum"]) == (2, 3, 1)
        rows = prepared["projection_rows"]
        assert rows[0]["qualification"]["member_ids"] == ["WT"]
        assert [r["member_id"] for r in rows[1]["payload"]["rows"]] == ["A"]
        assert "dot_bracket" not in f.keys(rows) and "input_paths" not in f.keys(rows)
        (tmp_path / "filled_actual_scan.json").write_bytes(f.raw({"identity": "synthetic_inputs_actual_bounded_worker", "prepared": prepared, **checked}))


def test_actual_requested_insertion_site_preserves_original_and_corresponding_partner(tmp_path):
    baseline = f.b.feature(energy=-3.0)
    variant = f.b.feature("V", "UGGGAAACCC", ".(((...)))", energy=-2.0)
    sheet = f.b.pair(baseline, variant, correspondence=f.b.complete([(None, 0)] + [(i, i + 1) for i in range(9)]),
        selections=[f.b.site(positions=[0])], energy=f.b.energy_request(normalization="per_nt"))
    selector, operands = f.resolved(sheet, [f.projection("position_changes"), f.projection("energy_comparison")])
    with Store(tmp_path / "store") as store:
        prepared = prepare(store, tmp_path / "grading", selector, operands)
        row = prepared["projection_rows"][0]["payload"]["rows"][0]
        assert (row["baseline_index"], row["variant_index"]) == (0, 1)
        assert (row["baseline_partner"]["local_index"], row["variant_partner"]["local_index"]) == (8, 9)
        assert row["transition"] == "unchanged_partner" and row["change_indicator"]["value"] == 0
        assert "input_paths" not in row["change_indicator"]
        delta = prepared["projection_rows"][1]["payload"]["rows"][0]["measurements"][-1]
        assert delta["unit"] == "kcal/mol/nt" and delta["value"] == pytest.approx(2 / 15)


def test_changed_projection_reuses_scientific_identity_and_retains_prior_result(tmp_path):
    selector, operands = f.pair([f.projection("energy_comparison")])
    with Store(tmp_path / "store") as store:
        first = prepare(store, tmp_path / "first", selector, operands)
        before = (tmp_path / "first/prepared.json").read_bytes()
        changed = deepcopy(selector)
        changed["projections"] = [f.projection("structures", fields=["pairs"])]
        second = prepare(store, tmp_path / "second", changed, operands, key="rna_comparison_receipt:" + "2" * 64)
        assert first["calculation_key"] == second["calculation_key"]
        assert first["comparison_sheet_artifact_ref"] == second["comparison_sheet_artifact_ref"]
        assert first["components_artifact_ref"] == second["components_artifact_ref"]
        assert first["projection_rows_artifact_ref"] != second["projection_rows_artifact_ref"]
        assert (tmp_path / "first/prepared.json").read_bytes() == before


def test_invalid_local_policy_never_starts_worker(tmp_path, monkeypatch):
    selector, operands = f.pair()
    monkeypatch.setattr(p, "run_local_job", forbidden)
    with Store(tmp_path / "store") as store:
        with pytest.raises(ValueError, match="policy_mismatch"):
            p.prepare_rna_comparison_grading(store, selector=selector, operands=operands, result_receipt_key=f.KEY,
                directory=tmp_path / "grading", policy=LocalJobPolicy(21474836480, 4294967296, wall_seconds=1))
    assert not (tmp_path / "grading").exists()


def test_actual_257_member_worker_keeps_aggregate_return_compact(tmp_path):
    sequences = ["AAAA" + "".join("ACGU"[(n // (4 ** i)) % 4] for i in range(5)) for n in range(257)]
    originals = [f.b.feature("WT" if i == 0 else f"V{i:03d}", seq, "." * 9,
        energy=-10.0 if i == 0 else -9.0 + i % 4) for i, seq in enumerate(sequences)]
    energy = f.b.energy_request()
    selected = f.b.selector([f.b.member(s) for s in originals],
        [f.b.comparison(s["record_key"], energy=energy) for s in originals[1:]], scan=f.b.scan_request(energy))
    from gene_annotation_episode.rna_structure_comparison_inputs import populate_rna_comparison_sheet
    sheet = populate_rna_comparison_sheet(selected, operands={s["record_key"]: f.b.supplied(s) for s in originals})
    selector, operands = f.resolved(sheet, [f.projection("scan_energy", metrics=["baseline_rank_start",
        "baseline_rank_end", "lowest_energy_tie_count", "baseline_energy_above_minimum"])])
    with Store(tmp_path / "store") as store:
        prepared = prepare(store, tmp_path / "grading", selector, operands)
        assert prepared["delivery_complete"]
        components = read(store, prepared["components_artifact_ref"])
        result, = prepared["projection_rows"]
        assert len(components["scan"]["members"]) == 257
        assert len(f.b.cells(components["scan"]["energy_components"])["baseline_rank_start"]["input_paths"]) > 1500
        assert [c["value"] for c in result["payload"]["measurements"]] == [1, 1, 1, 0.0]
        assert result["payload"]["rank_class"] == "unique_lowest"
        assert result["qualification"]["member_ids"] == ["WT"]
        assert result["qualification"]["population"]["rank_population_count"] == 257
        assert "input_paths" not in f.keys(result) and "dot_bracket" not in f.keys(result)
        assert len(json.dumps(result).encode()) < 12000
        (tmp_path / "large_scan_selected_projection.json").write_bytes(f.raw({"identity": "synthetic_inputs_actual_bounded_worker",
            "retained_member_count": 257, "return_utf8_bytes": len(json.dumps(result).encode()), "projection": result}))
