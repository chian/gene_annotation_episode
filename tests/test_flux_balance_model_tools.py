"""Pure contracts and selected-runtime inspect/edit controls; zero optimizations.

Native fixtures are tiny caller-authored controls, not biological measurements
or a Workflow/publication proof. They use the bounded runner's actual selected
Cobra closure. Fault cases are explicitly engineered; no old212/217 solve runs.
"""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode import flux_balance_model_tools as tools


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


@pytest.fixture(scope="module")
def native_cases(tmp_path_factory):
    if "HMMER529_ATTEMPT" not in os.environ:
        pytest.skip("selected Cobra work requires the bounded runner")
    import cobra
    from test_native_flux_balance_producer_688 import _json_model, _software
    root = tmp_path_factory.mktemp("fba-model-selected")
    software = _software()
    optimize_calls = []
    def forbidden(*args, **kwargs):
        optimize_calls.append(True)
        raise AssertionError("model inspection/editing must never optimize")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(cobra.Model, "optimize", forbidden)
        document = _json_model()
        # Cobra's native JSON writer exports used compartments only. Keep the
        # positive roundtrip control within that actual supported representation.
        document["compartments"] = {"c": "cytosol"}
        raw = canonical(document).encode()
        model_file = root / "caller.json"
        model_file.write_bytes(raw)
        inputs = {model_file: raw}
        values = {"inspect": tools.run_flux_balance_model_request(request(raw), model_path=model_file,
            output_directory=root / "inspect", software=software),
            "edit": tools.run_flux_balance_model_request(request(raw, edit=addition()), model_path=model_file,
                output_directory=root / "edit", software=software)}
        minimum = edits()
        minimum["objective"] = {"kind": "single_reaction", "reaction_id": "OUT", "direction": "min", "source_refs": []}
        values["json_min"] = tools.run_flux_balance_model_request(request(raw, edit=minimum), model_path=model_file,
            output_directory=root / "json-min", software=software)
        # Native serialization creates a distinct explicit caller SBML control;
        # this fixture itself never optimizes and is not a database acquisition.
        sbml_model = cobra.io.from_json(raw.decode())
        sbml_model.objective.direction = "min"
        sbml_file = root / "caller.xml"
        cobra.io.write_sbml_model(sbml_model, str(sbml_file))
        sbml = sbml_file.read_bytes()
        inputs[sbml_file] = sbml
        minimum["output_format"] = "sbml"
        values["sbml_min"] = tools.run_flux_balance_model_request(request(sbml, edit=minimum, format_="sbml"),
            model_path=sbml_file, output_directory=root / "sbml-min", software=software)
        default = _json_model()
        del default["reactions"][1]["upper_bound"]
        default_raw = canonical(default).encode()
        default_file = root / "caller-missing-bound.json"
        default_file.write_bytes(default_raw)
        inputs[default_file] = default_raw
        values["default_inspect"] = tools.run_flux_balance_model_request(request(default_raw), model_path=default_file,
            output_directory=root / "default-inspect", software=software)
        values["default_edit"] = tools.run_flux_balance_model_request(request(default_raw, edit=edits()), model_path=default_file,
            output_directory=root / "default-edit", software=software)
        assert optimize_calls == []
        assert all(path.read_bytes() == original for path, original in inputs.items())
    return SimpleNamespace(root=root, software=software, values=values, model_file=model_file, raw=raw, inputs=inputs)


def test_selected_native_inspection_and_explicit_edit_preserve_originals_without_solve(native_cases):
    inspect, edited = native_cases.values["inspect"], native_cases.values["edit"]
    assert inspect["model_optimize_call_count"] == edited["model_optimize_call_count"] == 0
    assert inspect["edit_state"] == "not_requested" and inspect["edited_model"] is None
    assert edited["edit_state"] == "exact" and all(row["state"] == "applied" for row in edited["edit_results"])
    original = inspect["models"]["loaded_original"]
    effective = edited["models"]["effective"]
    assert [row["id"] for row in original["reactions"]] == ["IN", "AB", "OUT"]
    assert [row["id"] for row in effective["reactions"]] == ["IN", "AB", "OUT", "BC"]
    assert effective["reactions"][1]["lower"]["value"] == effective["reactions"][1]["upper"]["value"] == 0
    assert [row["id"] for row in effective["metabolites"]] == ["A", "B", "C"]
    assert effective["metabolites"][2]["charge"]["value"] == 0
    declaration = edited["edited_model"]
    output = native_cases.root / "edit" / declaration["relative_path"]
    assert file_for(output.read_bytes()) == declaration["file"]
    assert output != native_cases.model_file
    assert all(path.read_bytes() == original for path, original in native_cases.inputs.items())


def test_explicit_format_preserves_min_sbml_and_rejects_json_direction_loss(native_cases):
    sbml, json_result = native_cases.values["sbml_min"], native_cases.values["json_min"]
    assert sbml["edit_state"] == "exact"
    assert sbml["edited_model"]["file"]["format"] == "sbml"
    assert sbml["problems"]["loaded_original"]["objective"]["direction"] == sbml["problems"]["effective"]["objective"]["direction"] == "min"
    assert json_result["edit_state"] == "partial" and json_result["edited_model"] is None
    assert all(row["role"] != "edited_model" for row in json_result["files"])
    assert any(issue["code"] == "request_effective_mismatch" for issue in json_result["issues"])
    assert (native_cases.root / "json-min/edited-model.json").is_file()  # rejected private candidate only


def test_source_default_is_observed_for_inspection_but_not_serialized_as_authored(native_cases):
    inspect, edited = native_cases.values["default_inspect"], native_cases.values["default_edit"]
    view = tools.project_flux_balance_model_result(inspect, selector=selector())
    assert any(row["kind"] == "default_bound" for row in view["source_features"])
    assert inspect["models"]["loaded_original"] is not None
    assert edited["edit_state"] == "rejected" and edited["edited_model"] is None
    assert any(issue["code"] == "source_semantics_unsupported" for issue in edited["issues"])
    assert not (native_cases.root / "default-edit/edited-model.json").exists()


@pytest.mark.parametrize("collection", ["model", "compartments", "metabolites", "reactions", "genes", "groups", "stoichiometry", "objective"])
def test_saved_views_and_validation_need_no_parser_native_calculator_or_io(native_cases, monkeypatch, collection):
    stored = deepcopy(native_cases.values["edit"])
    expected = tools.project_flux_balance_model_result(stored, selector=selector(collection, "effective"))
    frozen = canonical(stored)
    def forbidden(*args, **kwargs): raise AssertionError("saved view reopened private/native data")
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(tools, "parse_cobra_glpk_model_capture", forbidden)
    monkeypatch.setattr(tools, "parse_cobra_glpk_problem_capture", forbidden)
    monkeypatch.setattr(tools, "run_flux_balance_model_request", forbidden)
    assert canonical(tools.validate_flux_balance_model_result(stored)) == frozen
    actual = tools.project_flux_balance_model_result(stored, selector=selector(collection, "effective"))
    assert canonical(actual) == canonical(expected) and canonical(stored) == frozen
    assert "native_capture_evidence" not in canonical(actual) and "native_cobra_json" not in canonical(actual)


def test_explicit_original_ordinals_duplicates_zero_and_window_population(native_cases):
    selected = selector("reactions", "effective", ordinals=[3, 1, 3, 0], offset=1, limit=2)
    view = tools.project_flux_balance_model_result(native_cases.values["edit"], selector=selected)
    assert view["population"]["expected_count"] == view["population"]["retained_count"] == 4
    assert view["page"] == {"selected_row_count": 4, "offset": 1, "returned_row_count": 2, "has_more": True}
    assert [row["ordinal"] for row in view["rows"]] == [1, 3]
    assert view["rows"][0]["values"]["lower"]["value"] == view["rows"][0]["values"]["upper"]["value"] == 0
    assert tools.project_flux_balance_model_result(native_cases.values["edit"], selector=selector("groups", "effective"))["population"]["expected_count"] == 0
    with pytest.raises(ValueError, match="view_position_out_of_range"):
        tools.project_flux_balance_model_result(native_cases.values["edit"], selector=selector(ordinals=[50]))


def test_qualified_unavailable_snapshot_remains_missing_not_observed_empty(native_cases):
    value = deepcopy(native_cases.values["inspect"])
    issue = tools._issue("schema_invalid", "parse", "/capture")
    value["models"].update(loaded_original=None, effective=None, source=None, input_profile="unknown",
        loader=None, source_to_loaded_ids=[], source_feature_audit=[], source_audit=None, issues=[issue])
    value["problems"].update(loaded_original=None, effective=None, source=None, configuration_before_solve=None, issues=[issue])
    missing = tools.project_flux_balance_model_result(value, selector=selector("groups", ordinals=[6]))
    empty = tools.project_flux_balance_model_result(native_cases.values["inspect"], selector=selector("groups"))
    assert missing["population"] == {"basis": "captured_loaded_native_collection", "expected_count": None,
        "retained_count": 0, "snapshot_available": False}
    assert missing["rows"] == [{"ordinal": 6, "availability": "unavailable", "values": None}]
    assert missing["issues"] == [tools._public(issue)]
    assert empty["population"]["expected_count"] == 0 and empty["population"]["snapshot_available"] is True
    assert empty["rows"] == []


@pytest.mark.parametrize("fault", ["extra", "version", "count_bool", "count_float", "count_nonzero", "input_identity",
    "original_identity", "snapshot_identity", "edited_identity", "edited_format", "private_path", "missing_edited", "edit_order",
    "missing_heads", "missing_original_model", "missing_effective_model", "missing_original_problem", "missing_effective_problem",
    "partial_effective_population", "model_issue", "problem_issue", "top_issue", "audit_size", "audit_foreign_file",
    "original_reaction_join", "effective_reaction_join", "original_metabolite_join", "effective_metabolite_join"])
def test_saved_result_rejects_closed_envelope_and_identity_tampering(native_cases, fault):
    value = deepcopy(native_cases.values["edit"])
    if fault == "extra": value["host_path"] = "/private"
    elif fault == "version": value["version"] = "other"
    elif fault == "count_bool": value["model_optimize_call_count"] = False
    elif fault == "count_float": value["model_optimize_call_count"] = 0.0
    elif fault == "count_nonzero": value["model_optimize_call_count"] = 1
    elif fault == "input_identity": value["request"]["model_file"]["size_bytes"] += 1
    elif fault == "original_identity": value["files"][0]["file"]["sha256"] = "0" * 64
    elif fault == "snapshot_identity":
        value["models"]["source"] = deepcopy(value["models"]["source"])
        value["models"]["source"]["size_bytes"] += 1
    elif fault == "edited_identity":
        value["edited_model"] = deepcopy(value["edited_model"])
        value["edited_model"]["file"]["size_bytes"] += 1
    elif fault == "edited_format": value["edited_model"]["file"]["format"] = "sbml"
    elif fault == "private_path": value["files"][0]["relative_path"] = "../private"
    elif fault == "missing_edited": value["edited_model"] = None
    elif fault == "edit_order": value["edit_results"].reverse()
    elif fault == "missing_heads": value["models"] = value["problems"] = None
    elif fault == "missing_original_model": value["models"]["loaded_original"] = None
    elif fault == "missing_effective_model": value["models"]["effective"] = None
    elif fault == "missing_original_problem": value["problems"]["loaded_original"] = None
    elif fault == "missing_effective_problem": value["problems"]["effective"] = None
    elif fault == "partial_effective_population": value["models"]["effective"]["population"]["completeness"] = "partial"
    elif fault in {"audit_size", "audit_foreign_file"}:
        audit = value["models"]["source_audit"]
        audit["original_model"]["file"] = deepcopy(audit["original_model"]["file"])
        if fault == "audit_size": audit["original_model"]["file"]["size_bytes"] += 1
        else:
            audit["original_model"]["file"].update(artifact_ref="artifact_" + "0" * 64, sha256="0" * 64)
    elif fault.endswith("_reaction_join"):
        phase = "loaded_original" if fault.startswith("original") else "effective"
        value["problems"][phase]["reaction_variables"][0]["reaction_id"] = "different_native_reaction"
    elif fault.endswith("_metabolite_join"):
        phase = "loaded_original" if fault.startswith("original") else "effective"
        value["problems"][phase]["constraints"][0]["metabolite_position"] = 500
    else:
        owner = value if fault == "top_issue" else value["models" if fault == "model_issue" else "problems"]
        owner["issues"].append(tools._issue("schema_invalid", "parse", "/capture"))
    with pytest.raises(ValueError): tools.validate_flux_balance_model_result(value)


def test_saved_partial_unknown_model_rows_remain_unknown_without_invented_joins(native_cases):
    # Engineered saved partial population, not a new native publication.
    value = deepcopy(native_cases.values["inspect"])
    issue = tools._issue("partial_population", "parse", "/partial")
    for phase in ("loaded_original", "effective"):
        model = value["models"][phase]
        model["reactions"] = model["reactions"][1:]
        model["metabolites"] = model["metabolites"][1:]
        model["population"].update(reactions=None, metabolites=None, completeness="partial")
        value["problems"][phase]["representation"] = "partial"
    value["models"]["issues"].append(issue)
    value["problems"]["issues"].append(issue)
    before = canonical(value)
    assert canonical(tools.validate_flux_balance_model_result(value)) == before
    view = tools.project_flux_balance_model_result(value, selector=selector(ordinals=[0, 1]))
    assert view["population"]["expected_count"] is None
    assert view["rows"][0] == {"ordinal": 0, "availability": "unavailable", "values": None}
    assert view["rows"][1]["availability"] == "present"
    assert canonical(value) == before


def test_unbound_worker_source_rejects_before_any_model_read(native_cases, monkeypatch, tmp_path):
    software = deepcopy(native_cases.software)
    software["implementation_files"] = [pin for pin in software["implementation_files"] if pin["path"] != str(Path(tools.__file__).resolve())]
    def forbidden(*args, **kwargs): raise AssertionError("unbound worker read input")
    monkeypatch.setattr(tools, "read_bytes", forbidden)
    with pytest.raises(ValueError, match="worker_source_unbound"):
        tools.run_flux_balance_model_request(request(native_cases.raw), model_path=native_cases.model_file,
            output_directory=tmp_path / "unbound", software=software)
    assert not (tmp_path / "unbound").exists()


def test_engineered_partial_setter_retains_applied_rows_and_private_trace_without_model_output(native_cases, monkeypatch, tmp_path, capsys):
    import cobra
    original_add = cobra.Model.add_reactions
    def failed_add(model, rows):
        if any(row.id == "BC" for row in rows):
            raise ValueError("engineered setter diagnostic /private/control/location")
        return original_add(model, rows)
    monkeypatch.setattr(cobra.Model, "add_reactions", failed_add)
    def forbidden(*args, **kwargs): raise AssertionError("fault case must not optimize")
    monkeypatch.setattr(cobra.Model, "optimize", forbidden)
    result = tools.run_flux_balance_model_request(request(native_cases.raw, edit=addition()), model_path=native_cases.model_file,
        output_directory=tmp_path / "partial", software=native_cases.software)
    assert result["edit_state"] == "partial" and result["edited_model"] is None
    assert result["edit_results"][0]["state"] == "applied" and result["edit_results"][1]["state"] == "unknown"
    assert result["models"]["effective"]["population"]["metabolites"] == 3
    assert "/private/control/location" in capsys.readouterr().err
    assert "/private/control/location" not in canonical(tools.project_flux_balance_model_result(result, selector=selector()))
    assert native_cases.model_file.read_bytes() == native_cases.raw


@pytest.mark.parametrize("missing", [False, True])
def test_actual_input_identity_or_unavailable_failure_never_reaches_loader(native_cases, monkeypatch, tmp_path, missing):
    from gene_annotation_episode import native_flux_balance_cobra_glpk as capture
    def forbidden(*args, **kwargs): raise AssertionError("failed input reached native loader")
    monkeypatch.setattr(capture, "_load_model", forbidden)
    supplied = request(native_cases.raw)
    if not missing:
        supplied["model_file"]["size_bytes"] += 1
    result = tools.run_flux_balance_model_request(supplied,
        model_path=tmp_path / "missing.json" if missing else native_cases.model_file,
        output_directory=tmp_path / "failed-input", software=native_cases.software)
    assert result["models"] is result["problems"] is None and result["files"] == []
    assert result["model_optimize_call_count"] == 0
    assert {issue["code"] for issue in result["issues"]} == {"artifact_missing" if missing else "model_identity_conflict"}
