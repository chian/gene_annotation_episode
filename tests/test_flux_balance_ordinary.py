"""Ordinary FBA compiler and engineered lifecycle ports; no native solve.

Software records are explicitly uninstalled metadata controls. Legacy
materialization is only a whole-request oracle, not an ordinary commission or
permission proof. Lifecycle methods are controlled ports: no systemd job,
Cobra model, scientific capture, optimization or new Workflow is executed.
"""

import pytest

from gene_annotation_episode.episodic_workflow.root.library import flux_balance_ordinary as ordinary
from gene_annotation_episode.episodic_workflow.root.library.flux_balance_worker_contracts import build_saved_flux_balance_worker_plan
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.library.native_flux_balance_contracts import POLICY


def saved_plan(tmp_path):
    file = {"artifact_ref": "artifact_" + "c" * 64, "sha256": "c" * 64, "size_bytes": 3, "format": "flux_balance_sheet_v1"}
    selector = {"version": "flux_balance_result_selector_v1", "mode": "saved_sheet_recalculation", "saved_sheet_file": file,
        "calculation_parameters": {"version": "fba_calculation_parameters_v1", "reaction_bound_tolerances": [],
            "constraint_tolerances": [], "active_flux_thresholds": [], "objective_absolute_tolerance": None,
            "variable_bound_tolerances": [], "reaction_flux_tolerances": [], "constraint_activity_tolerances": []},
        "projection": {"version": "flux_balance_projection_selector_v1", "view": "run_diagnostics", "fields": ["native_run"],
            "row_window": {"offset": 0, "limit": 1}}}
    return build_saved_flux_balance_worker_plan(directory=str(tmp_path / "worker/output"),
        sheet={"file": file, "path": "/engineered/store/artifacts/cc/" + "c" * 64}, selector=selector)


@pytest.mark.parametrize("bad", [None, {}, "default"])
def test_result_worker_refuses_absent_or_invalid_selected_software_before_preparation(tmp_path, monkeypatch, bad):
    def forbidden(*args, **kwargs): raise AssertionError("invalid software reached worker preparation")
    monkeypatch.setattr(ordinary, "prepare_flux_balance_result_worker", forbidden)
    with pytest.raises(ValueError):
        ordinary.run_selected_flux_balance_result_worker(object(), plan=saved_plan(tmp_path), software=bad,
            policy=LocalJobPolicy(**POLICY))


