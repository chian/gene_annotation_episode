"""Explicit result modes/parameters retain the existing numerical contracts."""
import builtins
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.flux_balance_result_selection import (
    FBA_RESULT_SELECTOR_SCHEMA, validate_flux_balance_result_selector,
)

pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")
ROOT = Path(__file__).resolve().parents[1]
EMITTED = ROOT / "verification/tool_graders_hmmer_map_verification_2026-10-28_529/check151c_producer688/producer-emissions/sbml"


@pytest.fixture
def selector():
    parameters = json.loads((EMITTED / "calculated.json").read_text())["parameters"]
    return {"version": "flux_balance_result_selector_v1", "mode": "native_result", "saved_sheet_file": None,
        "calculation_parameters": parameters, "projection": {"version": "flux_balance_projection_selector_v1",
            "view": "reaction_fluxes", "fields": ["flux", "csv_comparison"], "snapshot_phase": "effective",
            "reaction_positions": [2, 0], "row_window": {"offset": 0, "limit": 2}}}


def _saved(selector):
    selector["mode"] = "saved_sheet_recalculation"
    selector["saved_sheet_file"] = {"artifact_ref": "artifact_" + "a" * 64, "sha256": "a" * 64,
        "size_bytes": 123, "format": "flux_balance_sheet_v1"}
    return selector


@pytest.mark.parametrize("saved", [False, True])
def test_explicit_modes_detach_and_match_public_schema(selector, saved):
    if saved: _saved(selector)
    before = deepcopy(selector)
    result = validate_flux_balance_result_selector(selector)
    Draft202012Validator.check_schema(FBA_RESULT_SELECTOR_SCHEMA)
    assert Draft202012Validator(FBA_RESULT_SELECTOR_SCHEMA).is_valid(result)
    assert result == before and selector == before
    result["projection"]["reaction_positions"].reverse()
    result["calculation_parameters"]["objective_absolute_tolerance"] = 0
    assert selector == before


@pytest.mark.parametrize("fault", ["missing_parameters", "null_parameters", "missing_projection", "unknown_mode",
    "extra_path", "native_with_sheet", "saved_without_sheet", "wrong_sheet_format", "wrong_sheet_digest",
    "bool_tolerance", "nan_tolerance", "bool_position", "duplicate_position", "unknown_field"])
def test_invalid_selection_cannot_change_mode_inputs_or_numerical_meanings(selector, fault):
    if fault == "missing_parameters": del selector["calculation_parameters"]
    elif fault == "null_parameters": selector["calculation_parameters"] = None
    elif fault == "missing_projection": del selector["projection"]
    elif fault == "unknown_mode": selector["mode"] = "auto"
    elif fault == "extra_path": selector["path"] = "/unselected/model.xml"
    elif fault == "native_with_sheet":
        _saved(selector);selector["mode"] = "native_result"
    elif fault == "saved_without_sheet": selector["mode"] = "saved_sheet_recalculation"
    elif fault == "wrong_sheet_format": _saved(selector)["saved_sheet_file"]["format"] = "sbml"
    elif fault == "wrong_sheet_digest": _saved(selector)["saved_sheet_file"]["artifact_ref"] = "artifact_" + "b" * 64
    elif fault == "bool_tolerance": selector["calculation_parameters"]["objective_absolute_tolerance"] = True
    elif fault == "nan_tolerance": selector["calculation_parameters"]["objective_absolute_tolerance"] = float("nan")
    elif fault == "bool_position": selector["projection"]["reaction_positions"] = [True]
    elif fault == "duplicate_position": selector["projection"]["reaction_positions"] = [2, 2]
    else: selector["projection"]["fields"] = ["function_probability"]
    with pytest.raises(ValueError): validate_flux_balance_result_selector(selector)


def test_native_original_job_is_validated_saved_has_no_native_job_operand(selector):
    job = json.loads((EMITTED / "selected-plan.json").read_text())["requested_job"]
    assert validate_flux_balance_result_selector(selector, job=job) == selector
    _saved(selector)
    with pytest.raises(ValueError, match="fba_result_selector_invalid:/job"):
        validate_flux_balance_result_selector(selector, job=job)
    with pytest.raises(ValueError):
        validate_flux_balance_result_selector({**selector, "mode": "native_result", "saved_sheet_file": None},
            job={"argv": ["unselected"], "environment": {}})


def test_saved_selection_performs_no_io_or_scientific_work(selector, monkeypatch):
    _saved(selector)
    def forbidden(*args, **kwargs): raise AssertionError("selection attempted I/O or scientific execution")
    original_import = builtins.__import__
    def imports(name, *args, **kwargs):
        if any(word in name for word in ("native_flux_balance", "cobra", "optlang", "swiglpk", "flux_balance_calculations", "flux_balance_readers")):
            forbidden()
        return original_import(name, *args, **kwargs)
    with monkeypatch.context() as m:
        m.setattr(builtins, "open", forbidden);m.setattr(io, "open", forbidden)
        m.setattr(socket, "socket", forbidden);m.setattr(subprocess, "run", forbidden);m.setattr(subprocess, "Popen", forbidden)
        m.setattr(builtins, "__import__", imports)
        result = validate_flux_balance_result_selector(selector)
    assert result == selector
