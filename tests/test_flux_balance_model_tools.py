"""Pure contracts and selected-runtime inspect/edit controls; zero optimizations.

Native fixtures are tiny caller-authored controls, not biological measurements
or a Workflow/publication proof. Fault cases are explicitly engineered.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.library import flux_balance_model_tools as tools


def file_for(raw, format_="cobra_json"):
    sha = hashlib.sha256(raw).hexdigest()
    return {"artifact_ref": "artifact_" + sha, "sha256": sha, "size_bytes": len(raw), "format": format_}


def bound(value):
    return {"kind": "finite", "value": value}


def edits(format_="cobra_json"):
    return {"output_format": format_, "add_metabolites": [], "add_reactions": [], "bounds": [],
        "objective": {"kind": "preserve"}}


def request(raw=b"{}", *, edit=None, format_="cobra_json"):
    return {"version": tools.REQUEST_VERSION, "mode": "inspect" if edit is None else "edit",
        "model_file": file_for(raw, format_), "edits": edit}


def selector(collection="reactions", phase="loaded_original", *, ordinals=None, offset=0, limit=50):
    return {"snapshot_phase": phase, "collection": collection, "ordinals": ordinals,
        "row_window": {"offset": offset, "limit": limit}}


def addition():
    value = edits()
    value["add_metabolites"] = [{"id": "C", "name": "caller C", "compartment_id": "c", "formula": None,
        "charge": 0, "source_refs": ["source_" + "a" * 24]}]
    value["add_reactions"] = [{"id": "BC", "name": "caller hypothetical conversion", "lower": bound(0), "upper": bound(5),
        "stoichiometry": [{"metabolite_id": "B", "coefficient": -1}, {"metabolite_id": "C", "coefficient": 1}],
        "source_refs": []}]
    value["bounds"] = [{"reaction_id": "AB", "lower": bound(0), "upper": bound(0), "source_refs": []}]
    value["objective"] = {"kind": "single_reaction", "reaction_id": "BC", "direction": "max", "source_refs": []}
    return value


def test_closed_requests_preserve_literals_and_do_not_authenticate_sources():
    value = request(edit=addition())
    actual = tools.validate_flux_balance_model_request(value)
    assert canonical(actual) == canonical(value)
    actual["edits"]["add_metabolites"][0]["name"] = "detached"
    assert value["edits"]["add_metabolites"][0]["name"] == "caller C"
    schema = tools.flux_balance_model_schema("Edits")
    schema["properties"]["output_format"] = {}
    assert tools.flux_balance_model_schema("Edits")["properties"]["output_format"]["enum"] == ["sbml", "cobra_json"]


@pytest.mark.parametrize("fault", ["extra", "mode", "format", "file_bool", "file_identity", "duplicate_metabolite",
    "duplicate_reaction", "duplicate_stoichiometry", "duplicate_bounds", "conflicting_bounds", "bool_coefficient",
    "nonfinite_coefficient", "empty_id", "unknown_source", "bad_source_type", "reversed_bounds", "missing_finite_value",
    "infinite_value", "wrong_infinity_side", "direction", "extra_gpr", "missing_output_format"])
def test_request_rejects_malformed_or_ambiguous_edits_before_any_io(monkeypatch, fault):
    value = request(edit=addition())
    selected = value["edits"]
    if fault == "extra": value["environment"] = {}
    elif fault == "mode": value["mode"] = "solve"
    elif fault == "format": value["model_file"]["format"] = "repository_identifier"
    elif fault == "file_bool": value["model_file"]["size_bytes"] = True
    elif fault == "file_identity": value["model_file"]["artifact_ref"] = "artifact_" + "0" * 64
    elif fault == "duplicate_metabolite": selected["add_metabolites"] *= 2
    elif fault == "duplicate_reaction": selected["add_reactions"] *= 2
    elif fault == "duplicate_stoichiometry": selected["add_reactions"][0]["stoichiometry"] *= 2
    elif fault == "duplicate_bounds": selected["bounds"] *= 2
    elif fault == "conflicting_bounds": selected["bounds"][0]["reaction_id"] = "BC"
    elif fault == "bool_coefficient": selected["add_reactions"][0]["stoichiometry"][0]["coefficient"] = True
    elif fault == "nonfinite_coefficient": selected["add_reactions"][0]["stoichiometry"][0]["coefficient"] = float("inf")
    elif fault == "empty_id": selected["add_metabolites"][0]["id"] = ""
    elif fault == "unknown_source": selected["add_metabolites"][0]["source_refs"] = ["some label"]
    elif fault == "bad_source_type": selected["add_metabolites"][0]["source_refs"] = [True]
    elif fault == "reversed_bounds": selected["bounds"][0]["lower"] = bound(1)
    elif fault == "missing_finite_value": selected["bounds"][0]["lower"]["value"] = None
    elif fault == "infinite_value": selected["bounds"][0]["lower"] = {"kind": "negative_infinity", "value": 0}
    elif fault == "wrong_infinity_side": selected["bounds"][0]["lower"] = {"kind": "positive_infinity", "value": None}
    elif fault == "direction": selected["objective"]["direction"] = "automatically_choose"
    elif fault == "extra_gpr": selected["add_reactions"][0]["gene_reaction_rule"] = "infer_gene"
    else: del selected["output_format"]
    def forbidden(*args, **kwargs): raise AssertionError("pure validation attempted I/O")
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    with pytest.raises(ValueError): tools.validate_flux_balance_model_request(value)


@pytest.mark.parametrize("fault", ["metabolite_exists", "reaction_exists", "compartment_unknown", "metabolite_unknown", "reaction_unknown", "objective_unknown"])
def test_native_identity_preflight_finishes_before_any_setter(fault):
    model = SimpleNamespace(metabolites=[SimpleNamespace(id="A"), SimpleNamespace(id="B")],
        reactions=[SimpleNamespace(id="IN"), SimpleNamespace(id="AB"), SimpleNamespace(id="OUT")],
        _compartments={"c": "cytosol", "unused": "explicit unused compartment"})
    value = addition()
    if fault == "metabolite_exists": value["add_metabolites"][0]["id"] = "A"
    elif fault == "reaction_exists": value["add_reactions"][0]["id"] = "AB"
    elif fault == "compartment_unknown": value["add_metabolites"][0]["compartment_id"] = "guessed"
    elif fault == "metabolite_unknown": value["add_reactions"][0]["stoichiometry"][0]["metabolite_id"] = "guessed"
    elif fault == "reaction_unknown": value["bounds"][0]["reaction_id"] = "guessed"
    else: value["objective"]["reaction_id"] = "guessed"
    before = deepcopy(model.__dict__)
    with pytest.raises(ValueError): tools._preflight(model, value)
    assert model.__dict__ == before


