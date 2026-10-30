"""Pure projection checks: saved679 normalization and authentic688 saved outputs.

Synthetic changes below are structural/authority counterexamples, never new
scientific measurements. No parser, scientific calculator or solver is invoked.
"""
from copy import deepcopy
import builtins
import hashlib
import importlib
import io
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.flux_balance_result_contracts import (
    FIELD_SCHEMAS, ORIGINAL_FIELDS, POSITION_KEYS, fba_result_schema,
    validate_fba_projection_selector, validate_fba_projection, validate_fba_saved_sheet_reference,
)
from gene_annotation_episode.flux_balance_result_views import project_fba_result
from gene_annotation_episode.flux_balance_return_views import (
    fba_fact_sources, requested_fba_sources, select_fba_return_facts, validate_fba_fact_values,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "verification/tool_graders_flux_balance_core_2026-10-29_679/VERIFIED_NUMERICAL_EXAMPLE_001.json"
EMISSIONS = ROOT / "verification/tool_graders_hmmer_map_verification_2026-10-28_529/check151c_producer688/producer-emissions"
pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="application checks require bounded529")


@pytest.fixture
def pair():
    value = json.loads(BASE.read_text())
    return value["sheet"], value["calculations"]


def _selector(view="reaction_fluxes", fields=None, positions=None, phase="effective", offset=0, limit=99, **extra):
    result = {"version": "flux_balance_projection_selector_v1", "view": view,
        "fields": fields or list(ORIGINAL_FIELDS[view] if phase == "loaded_original" and view in ORIGINAL_FIELDS else FIELD_SCHEMAS[view]),
        "row_window": {"offset": offset, "limit": limit}, **extra}
    if view in POSITION_KEYS:
        result[POSITION_KEYS[view][0]] = [0] if positions is None else positions
        if view in ORIGINAL_FIELDS:
            result["snapshot_phase"] = phase
    return result


def _rehash(sheet, calculations):
    calculations["sheet_sha256"] = digest(sheet)
    return sheet, calculations


def _plain(value):
    if type(value) is list:
        return [_plain(v) for v in value]
    if type(value) is dict:
        return {k: _plain(v) for k, v in value.items() if k not in {"source", "detail_file", "flux_expression_pointer"}}
    return value


def _csv_only():
    s = json.loads((EMISSIONS / "sbml/parsed-sheet.json").read_text())
    c = json.loads((EMISSIONS / "sbml/calculated.json").read_text())
    for phase in ("loaded_original", "effective"):
        s["models"][phase] = None
        s["problems"][phase] = None
    s["native_solution"]["native"] = None
    for axis in ("reaction", "constraint", "variable"):
        c[axis + "_checks"] = []
        c["expected_" + axis + "_count"] = None
    for r in s["native"]["flux_rows"]:
        r["reaction_position"] = None
        r["association"] = "unknown"
    return _rehash(s, c)


def _issue(*, source=None, field=None, stage="parse", **positions):
    return {"code": "input_missing", "stage": stage, "field": field, "detail_file": source,
        **{key: positions.get(key) for key in ("source_row_index", "reaction_position", "metabolite_position", "variable_position", "constraint_position")}}


@pytest.mark.parametrize("view,phase", [(v,p) for v in FIELD_SCHEMAS for p in
    (("loaded_original", "effective") if v in ORIGINAL_FIELDS else (None,))])
def test_complete_catalog_views_validate_and_detach(pair, view, phase):
    s,c = pair
    original = deepcopy(pair)
    selection = _selector(view, phase=phase)
    result = project_fba_result(s,c,selector=selection)
    assert validate_fba_projection(result) == result
    assert Draft202012Validator(fba_result_schema("FBAProjection")).is_valid(result)
    assert (s,c) == original
    assert result == project_fba_result(s,c,selector=selection)
    result["population"]["retained_count"] = 987
    assert (s,c) == original


def test_recorded679_numerical_example_and_all_native_values(pair):
    s,c = pair
    run = project_fba_result(s,c,selector=_selector("run_diagnostics"))
    r = {row["field"]: row["value"] for row in run["rows"]}
    assert r["objective"]["check"] == _plain(c["objective"])
    assert r["objective"]["check"]["native_basis_calculated"]["value"] == -4.25
    assert r["objective"]["check"]["full_calculated"]["value"] == -2.75
    assert r["objective"]["definition"]["interface_offset"]["value"] == 1.5
    assert r["variable_population"]["expected_variable_count"] == 7
    assert r["reaction_population"]["expected_reaction_count"] == 3
    assert r["variable_bound_counts"]["evaluated_variable_bound_count"] == 11
    assert r["balance_residual"]["max_abs_balance_residual"]["state"] == "missing"
    assert "unknown_units" in r["balance_residual"]["max_abs_balance_residual"]["issue_codes"]
    reaction = project_fba_result(s,c,selector=_selector(positions=[2,0]))
    assert [r["reaction_id"] for r in reaction["rows"]] == ["OUT","IN"]
    assert [r["values"]["flux"]["flux"]["value"] for r in reaction["rows"]] == [6,7]
    assert reaction["rows"][0]["values"]["native_values"]["reduced_cost_unit"] is None
    assert reaction["rows"][0]["values"]["bound_check"]["upper_slack"] == _plain(c["reaction_checks"][2]["upper_slack"])
    constraints = project_fba_result(s,c,selector=_selector("constraint_residuals",positions=[3,0]))
    split,a = [r["values"] for r in constraints["rows"]]
    assert split["activity"]["activity"]["value"] == 7
    assert split["bound_check"]["upper_slack"]["value"] == 2
    assert split["equality_residual"]["equality_residual"]["state"] == "not_applicable"
    assert a["activity"]["activity"]["value"] == 1
    assert a["equality_residual"]["equality_residual"]["value"] == 0
    assert constraints["rows"][0]["values"]["native_values"]["shadow_price_unit"] is None
    assert project_fba_result(s,c,selector=_selector("variable_bounds",positions=[6]))["rows"][0]["variable_id"] == "aux"
    out = Path(os.environ["HMMER529_ATTEMPT"]) / "projection693-recorded-examples.json"
    out.write_text(json.dumps({"fixture":"679 test-only normalization, no new solve", "run":run,"reactions":reaction,"constraints":constraints},allow_nan=False))


@pytest.mark.parametrize("profile", ["sbml", "cobra_json"])
def test_authentic688_saved_emission_projection(profile):
    s=json.loads((EMISSIONS/profile/"parsed-sheet.json").read_text())
    c=json.loads((EMISSIONS/profile/"calculated.json").read_text())
    result=project_fba_result(s,c,selector=_selector(positions=[2,0,1]))
    assert [r["reaction_id"] for r in result["rows"]] == ["OUT","IN","AB"]
    for row in result["rows"]:
        source = next(r for r in c["reaction_checks"] if r["reaction_position"] == row["reaction_position"])
        assert row["values"]["flux"]["flux"] == _plain(source["flux"])
        assert row["values"]["flux"]["flux"]["value"] == 10
        for k in ("lower_slack","upper_slack","lower_violation","upper_violation"):
            assert row["values"]["bound_check"][k] == _plain(source[k])
    run=project_fba_result(s,c,selector=_selector("run_diagnostics",fields=["objective","native_run","variable_bound_counts"]))
    assert run["rows"][0]["value"]["check"] == _plain(c["objective"])
    assert run["rows"][2]["value"]["evaluated_variable_bound_count"] == 12


def test_pure_projection_uses_authoritative_values_without_io_or_calculation(pair,monkeypatch):
    s,c=pair
    # Deliberately distinctive synthetic calculated facts, not scientific truth.
    c["reaction_checks"][0]["active"] = False
    c["reaction_checks"][0]["upper_slack"]["value"] = 321.5
    c["objective"]["glpk_minus_calculated"]["value"] = -98
    c["active_count"] = 123
    def deny(*args,**kwargs):
        raise AssertionError("projection attempted I/O, import or scientific work")
    actual_import = builtins.__import__
    def guarded_import(name,*args,**kwargs):
        if any(v in name for v in ("cobra","optlang","swiglpk","flux_balance_calculations","flux_balance_readers")):
            deny()
        return actual_import(name,*args,**kwargs)
    with monkeypatch.context() as m:
        m.setattr(builtins,"open",deny);m.setattr(io,"open",deny)
        m.setattr(socket,"socket",deny);m.setattr(subprocess,"run",deny);m.setattr(subprocess,"Popen",deny)
        m.setattr(builtins,"__import__",guarded_import)
        r=project_fba_result(s,c,selector=_selector(fields=["active","bound_check"]))
        run=project_fba_result(s,c,selector=_selector("run_diagnostics",fields=["active_population","objective"]))
    assert r["rows"][0]["values"]["active"]["active"] is False
    assert r["rows"][0]["values"]["bound_check"]["upper_slack"]["value"] == 321.5
    assert run["rows"][0]["value"]["active_count"] == 123
    assert run["rows"][1]["value"]["check"]["glpk_minus_calculated"]["value"] == -98


def test_sparse_known_population_keeps_original_positions(pair):
    s,c=pair
    m=s["models"]["effective"];m["population"]["completeness"]="partial"
    m["reactions"]=[r for r in m["reactions"] if r["position"]!=1]
    c["reaction_checks"]=[r for r in c["reaction_checks"] if r["reaction_position"]!=1]
    _rehash(s,c)
    selection=_selector(fields=["flux"],positions=[2,1,0])
    result=project_fba_result(s,c,selector=selection)
    assert [r["reaction_position"] for r in result["rows"]]==[2,1,0]
    assert result["rows"][1]=={"reaction_position":1,"reaction_id":None,"availability":"unavailable",
        "existence":"within_known_population","unavailable_reason":"position_not_retained","filter_match":None,"values":{"flux":None}}
    assert result["population"]["expected_count"]==3 and result["population"]["retained_count"]==2
    selection["reaction_positions"]=[3]
    with pytest.raises(ValueError,match="fba_projection_position_out_of_range"):
        project_fba_result(s,c,selector=selection)
    selection["reaction_positions"]=[]
    assert project_fba_result(s,c,selector=selection)["rows"]==[]


def test_unknown_population_and_snapshot_unavailable(pair):
    s,c=pair
    s["models"]["effective"]["population"].update(completeness="unknown",reactions=None)
    c["expected_reaction_count"]=None;_rehash(s,c)
    result=project_fba_result(s,c,selector=_selector(fields=["flux"],positions=[99,0]))
    assert result["rows"][0]["existence"]=="unknown"
    s["models"]["effective"]=None;c["reaction_checks"]=[];_rehash(s,c)
    result=project_fba_result(s,c,selector=_selector(fields=["flux"],positions=[0]))
    assert result["rows"][0]["unavailable_reason"]=="snapshot_unavailable"
    assert result["population"]["expected_count"] is None


@pytest.mark.parametrize("patch,code", [
    ({"reaction_positions":[2,2]},"position_duplicate"),({"reaction_positions":[True]},"selector_invalid"),
    ({"reaction_positions":[1.0]},"selector_invalid"),({"reaction_positions":[-1]},"selector_invalid"),
    ({"fields":["flux","flux"]},"field_invalid"),({"fields":["nonsense"]},"field_invalid"),
    ({"snapshot_phase":"loaded_original","fields":["flux"]},"field_invalid"),
    ({"bogus":0},"selector_invalid"),({"constraint_positions":[0]},"selector_invalid"),
    ({"row_window":{"offset":False,"limit":2}},"selector_invalid"),
    ({"row_window":{"offset":0,"limit":0}},"selector_invalid"),
    ({"filter":{"field":"name","minimum":0}},"filter_invalid"),
    ({"fields":["name"],"filter":{"field":"flux","minimum":0}},"filter_invalid"),
    ({"filter":{"field":"flux","minimum":True}},"filter_invalid"),
    ({"filter":{"field":"flux","minimum":float("nan")}},"selector_invalid"),
    ({"filter":{"field":"flux","minimum":float("inf")}},"selector_invalid"),
    ({"view":[]},"selector_invalid"),
])
def test_selector_failures_are_specific(patch,code):
    selection=_selector();selection.update(patch)
    with pytest.raises(ValueError,match="fba_projection_"+code):
        validate_fba_projection_selector(selection)


def test_csv_only_unknown_population_filter_and_empty_page():
    s,c=_csv_only()
    s["native"]["flux_rows"]=[s["native"]["flux_rows"][0],s["native"]["flux_rows"][2]]
    _rehash(s,c)
    selected=_selector("csv_flux_rows",fields=["flux","model_association"],positions=[1,2,99],filter={"field":"flux","minimum":11})
    r=project_fba_result(s,c,selector=selected)
    assert [v["source_row_index"] for v in r["rows"]]==[1,99]
    assert r["population"]["expected_count"] is None and r["population"]["retained_count"]==2
    assert all(v["filter_match"]=="unknown" and v["existence"]=="unknown" for v in r["rows"])
    assert r["page"]=={"selected_row_count":3,"matched_row_count":0,"filter_unknown_row_count":2,
        "filtered_row_count":2,"row_offset":0,"returned_row_count":2,"has_more":False}
    selected["row_window"]["offset"]=100
    assert project_fba_result(s,c,selector=selected)["rows"]==[]


def test_csv_duplicate_indices_ambiguous_biological_ids_distinct():
    s,c=_csv_only()
    rows=s["native"]["flux_rows"]
    rows.append(deepcopy(rows[0]));rows[1]["reaction_id"]=rows[0]["reaction_id"]
    _rehash(s,c)
    r=project_fba_result(s,c,selector=_selector("csv_flux_rows",positions=[0,1,2]))
    assert r["rows"][0]["availability"]=="ambiguous"
    assert r["rows"][1]["availability"]=="present" and r["rows"][2]["availability"]=="present"
    assert r["qualification_issues"][-1]["issue"]["code"]=="flux_identity_conflict"
    assert all(v is None for v in r["rows"][0]["values"].values())


@pytest.mark.parametrize("mismatch",["hash","missing","duplicate","reaction_position","variable_id","constraint_id","metabolite","population","status","multiplicity"])
def test_calculation_association_not_repaired(pair,mismatch):
    s,c=pair
    if mismatch=="hash":c["sheet_sha256"]="0"*64
    elif mismatch=="missing":c["reaction_checks"].pop()
    elif mismatch=="duplicate":c["variable_checks"].append(deepcopy(c["variable_checks"][0]))
    elif mismatch=="reaction_position":c["reaction_checks"][0]["reaction_position"]=99
    elif mismatch=="variable_id":c["variable_checks"][0]["variable_id"]="wrong"
    elif mismatch=="constraint_id":c["constraint_checks"][0]["constraint_id"]="wrong"
    elif mismatch=="metabolite":c["constraint_checks"][0]["metabolite_position"]=99
    elif mismatch=="population":c["expected_reaction_count"]=99
    elif mismatch=="status":c["native_solver_status"]="infeasible"
    else:c["optimum_multiplicity"]="reported_unique"
    with pytest.raises(ValueError,match="fba_calculation_"):
        project_fba_result(s,c,selector=_selector())


def test_native_duplicate_values_and_conflicts_are_copied(pair):
    s,c=pair
    native=s["native_solution"]["native"];native["reaction_values"].append(deepcopy(native["reaction_values"][0]));_rehash(s,c)
    rc=c["reaction_checks"][0]
    rc["csv_flux"]=deepcopy(rc["flux"]);rc["csv_flux"].update(value=5,native_token="5",float_hex=None,precision="unknown")
    rc["csv_minus_flux"].update(value=-2,state="calculated");rc["csv_flux_comparison"]="unknown"
    r=project_fba_result(s,c,selector=_selector(fields=["native_values","csv_comparison"]))["rows"][0]["values"]
    assert len(r["native_values"]["rows"])==2
    assert r["csv_comparison"]["csv_minus_flux"]["value"]==-2
    assert r["csv_comparison"]["csv_flux_comparison"]=="unknown"


@pytest.mark.parametrize("status",["infeasible","time_limit","unknown"])
def test_native_status_is_not_delivery_gate(pair,status):
    s,c=pair;s["native"]["solver"]["status"]=status;c["native_solver_status"]=status
    _rehash(s,c)
    assert project_fba_result(s,c,selector=_selector())["rows"][0]["availability"]=="present"


@pytest.mark.parametrize("state",["missing","nonfinite","invalid"])
def test_qualified_missing_number_survives_filter(pair,state):
    s,c=pair
    number=c["reaction_checks"][0]["flux"]
    number.update(value=None,state=state,native_token="nan" if state=="nonfinite" else None,float_hex=None,
        missing_reason="not_returned" if state=="missing" else None)
    result=project_fba_result(s,c,selector=_selector(fields=["flux"],filter={"field":"flux","minimum":100}))
    assert result["rows"][0]["filter_match"]=="unknown"
    assert result["rows"][0]["values"]["flux"]["flux"]["state"]==state


def test_zero_negative_and_infinite_bounds_and_missing_tolerances(pair):
    s,c=pair
    rc=c["reaction_checks"][0]
    rc["flux"].update(value=-0.0,native_token="-0.0",float_hex="-0x0.0p+0")
    c["parameters"]["reaction_bound_tolerances"]=[]
    s["models"]["effective"]["reactions"][0]["lower"].update(kind="negative_infinity",value=None,native_token="-inf",float_hex=None)
    _rehash(s,c)
    r=project_fba_result(s,c,selector=_selector(fields=["flux","bound_check"]))["rows"][0]["values"]
    assert math.copysign(1,r["flux"]["flux"]["value"])==-1
    assert r["bound_check"]["lower"]["kind"]=="negative_infinity" and r["bound_check"]["tolerance"] is None
    rc["flux"].update(value=-3,native_token="-3",float_hex=None)
    assert project_fba_result(s,c,selector=_selector(fields=["flux"]))["rows"][0]["values"]["flux"]["flux"]["value"]==-3


def test_original_effective_phases_and_gpr_partial_genes(pair):
    s,c=pair
    m=s["models"]["loaded_original"];m["population"]["completeness"]="partial"
    r=m["reactions"][0];r["name"]="native <name>";r["gpr_native"]=None;r["gpr_loaded"]="g1 or g2"
    r["gpr_source_pointer"]="/xml/0";r["gene_positions"]=[0,1];m["genes"]=[];m["population"]["genes"]=2
    r["lower"].update(value=-999,native_token="-999",float_hex=None)
    _rehash(s,c)
    r=project_fba_result(s,c,selector=_selector(phase="loaded_original",fields=["name","bounds","gpr","genes"]))["rows"][0]["values"]
    assert r["name"]=="native <name>" and r["bounds"]["lower"]["value"]==-999
    assert r["gpr"]["source_gpr_retained"] is True and r["gpr"]["gpr_native"] is None
    assert all(g["availability"]=="unavailable" for g in r["genes"])
    assert project_fba_result(s,c,selector=_selector(fields=["bounds"]))["rows"][0]["values"]["bounds"]["lower"]["value"]!=-999


def test_incomplete_sparse_constraint_copies_counts_and_missing_activity(pair):
    s,c=pair
    row=c["constraint_checks"][0];row["expected_term_count"]=None
    row["activity"].update(value=None,state="missing",issue_codes=["term_population_incomplete"])
    r=project_fba_result(s,c,selector=_selector("constraint_residuals",fields=["activity"]))["rows"][0]["values"]["activity"]
    assert r["expected_term_count"] is None and r["available_term_count"]==4
    assert r["activity"]["value"] is None and "term_population_incomplete" in r["activity"]["issue_codes"]


def test_qualifications_require_source_phase_not_bare_position(pair):
    s,c=pair
    model=s["models"]["source"];solution=s["native_solution"]["source"]
    # Distinguish solution from synthetic model/source files for phase test.
    replacement=deepcopy(solution);replacement["artifact_ref"]="different-solution-source"
    s["retained_files"].append(replacement);s["native_solution"]["source"]=replacement
    c["issues"]=[_issue(),_issue(reaction_position=0,field="/effective/reactions/0",source=model),
        _issue(reaction_position=0,field="/loaded_original/reactions/0",source=model),
        _issue(reaction_position=0,field="/other",source=model),
        _issue(reaction_position=0,stage="calculate"),_issue(reaction_position=0,source=replacement)]
    _rehash(s,c)
    eff=project_fba_result(s,c,selector=_selector(fields=["name"]))["qualification_issues"]
    orig=project_fba_result(s,c,selector=_selector(phase="loaded_original",fields=["name"]))["qualification_issues"]
    assert len(eff)==4 and len(orig)==2
    assert [r["scope"] for r in eff]==["bundle","selected_entity","selected_entity","selected_entity"]
    assert orig[1]["issue"]["field"].startswith("/loaded_original/")
    run=project_fba_result(s,c,selector=_selector("run_diagnostics",fields=["native_run"]))
    assert len(run["qualification_issues"])==1


def test_csv_qualification_requires_actual_csv_file():
    s,c=_csv_only();csv_file=s["native"]["flux_rows"][0]["flux"]["source"]["file"]
    unrelated=s["models"]["source"]
    assert unrelated!=csv_file
    c["issues"]=[_issue(source_row_index=0,source=unrelated),_issue(source_row_index=0,source=csv_file),
        _issue(source_row_index=0),_issue(source_row_index=2,source=csv_file)]
    r=project_fba_result(s,c,selector=_selector("csv_flux_rows",fields=["name"],positions=[0]))
    assert len(r["qualification_issues"])==1 and r["qualification_issues"][0]["scope"]=="selected_csv_row"


def _no_capability(value):
    if type(value) is dict:
        assert not set(value)&{"artifact_ref","sha256","path","source","detail_file","supplied_target_refs",
            "annotation_pointer","notes_pointer","gpr_source_pointer","native_capture_evidence"}
        for v in value.values():_no_capability(v)
    elif type(value) is list:
        for v in value:_no_capability(v)


def test_facts_exact_requested_groups_detached_no_grants(pair):
    s,c=pair;r=project_fba_result(s,c,selector=_selector())
    _no_capability(r)
    facts=fba_fact_sources()
    saved={"artifact_ref":"artifact_"+"a"*64,"sha256":"a"*64,"size_bytes":9,"format":"flux_balance_sheet_v1"}
    groups={"flux_balance_measurements":[r],"flux_balance_saved_sheets":[saved],"flux_balance_failures":[]}
    for sources in [[],["flux_balance_measurements"],["flux_balance_saved_sheets"],list(groups),["flux_balance_failures"]]:
        schema={"type":"object","properties":{str(i):facts[source]["report_schema"] for i,source in enumerate(sources)}}
        assert requested_fba_sources(schema)==tuple(sources)
        selected=select_fba_return_facts(groups,schema=schema)
        assert list(selected)==sources
        if sources==["flux_balance_measurements"]:_no_capability(selected)
    assert facts["flux_balance_saved_sheets"]["report_schema"]["items"]["properties"]["artifact_ref"]["format"]=="reference"
    with pytest.raises(ValueError,match="requested_source_unavailable"):
        select_fba_return_facts({},schema={"properties":{"wanted":facts["flux_balance_measurements"]["report_schema"]}})
    with pytest.raises(ValueError,match="selection_mismatch"):
        requested_fba_sources({"properties":{"bad":{"x-source":"flux_balance_unknown"}}})
    saved["artifact_ref"]="artifact_"+"b"*64
    with pytest.raises(ValueError,match="selection_mismatch"):
        validate_fba_saved_sheet_reference(saved)


@pytest.mark.parametrize("mutation",["extra_value","missing_value","wrong_position","wrong_id","unavailable","page","population","nonfinite","wrong_state","float_position","wrong_token"])
def test_projection_validator_rejects_malformed_facts(pair,mutation):
    r=project_fba_result(*pair,selector=_selector(fields=["flux"]))
    row=r["rows"][0]
    if mutation=="extra_value":row["values"]["other"]=None
    elif mutation=="missing_value":row["values"]={}
    elif mutation=="wrong_position":row["reaction_position"]=99
    elif mutation=="wrong_id":row["reaction_id"]=None
    elif mutation=="unavailable":row["availability"]="unavailable"
    elif mutation=="page":r["page"]["returned_row_count"]=99
    elif mutation=="population":r["population"]["axis"]="variables"
    elif mutation=="nonfinite":row["values"]["flux"]["flux"]["value"]=float("nan")
    elif mutation=="wrong_state":row["values"]["flux"]["flux"]["state"]="missing"
    elif mutation=="float_position":row["reaction_position"]=0.0
    else:row["values"]["flux"]["flux"]["native_token"]="9"
    with pytest.raises(ValueError,match="fba_projection_"):
        validate_fba_projection(r)


def test_detached_public_schemas_and_unknown_kinds():
    schema=fba_result_schema("FBAResultNumber");schema["properties"]["value"]={}
    assert fba_result_schema("FBAResultNumber")["properties"]["value"]!={}
    with pytest.raises(ValueError):fba_result_schema("absent")
    for kind in ["FBAResultUnit","FBAResultNumber","FBAResultBound","FBAResultCell","FBAResultTolerance","FBAResultIssue","FBAResultQualification","FBASavedSheetReference"]:
        Draft202012Validator.check_schema(fba_result_schema(kind))
    with pytest.raises(ValueError):validate_fba_fact_values("flux_balance_unknown",[])


def test_absent_native_point_and_incompatible_calculated_cell(pair):
    s,c=pair
    # Synthetic absence; every actual native value is explicitly unavailable.
    native=s["native_solution"]["native"];native["point_state"]="not_established"
    for collection,key in [("reaction_values","flux"),("variable_values","primal"),("constraint_values","activity")]:
        for row in native[collection]:
            row[key].update(state="missing",value=None,native_token=None,float_hex=None,missing_reason="primal_not_established")
    check=c["reaction_checks"][0]
    check["variable_net_flux"].update(value=None,state="incompatible",issue_codes=["unit_incompatible"])
    _rehash(s,c)
    result=project_fba_result(s,c,selector=_selector(fields=["native_values","variable_net_comparison"]))
    assert result["rows"][0]["values"]["native_values"]["point_state"]=="not_established"
    assert result["rows"][0]["values"]["variable_net_comparison"]["variable_net_flux"]["state"]=="incompatible"


@pytest.mark.parametrize("profile",["sbml","cobra_json"])
def test_v13_current_parser_native_bytes_shared_calculator_projection_saved_only(profile,monkeypatch):
    """Actual original688 emissions; new consumer verification, zero new solves."""
    from gene_annotation_episode.flux_balance_readers import parse_fba_capture
    from gene_annotation_episode.flux_balance_sheet import populate_flux_balance_sheet
    from gene_annotation_episode.flux_balance_calculations import calculate_flux_balance_sheet
    folder=EMISSIONS/profile
    plan=json.loads((folder/"selected-plan.json").read_text())
    original_directory=Path(plan["attempt_directory"])
    manifest=json.loads((original_directory/"outputs/native-manifest.json").read_text())
    states={r["role"]:r["state"] for r in manifest["files"]}|{"manifest":"present"}
    payloads={}
    for row in plan["outputs"]:
        raw=(original_directory/row["relative_path"]).read_bytes()
        sha=hashlib.sha256(raw).hexdigest()
        payloads[row["role"]]={"file":{"artifact_ref":"fixture-artifact-"+row["role"]+"-"+sha,
            "sha256":sha,"size_bytes":len(raw),"format":row["format"]},"bytes":raw,"state":states[row["role"]]}
    original_sheet=json.loads((folder/"parsed-sheet.json").read_text())
    original_calculations=json.loads((folder/"calculated.json").read_text())
    def deny(*args,**kwargs):raise AssertionError("V13 attempted acquisition or native execution")
    actual_import=builtins.__import__
    def guarded_import(name,*args,**kwargs):
        if name.split('.')[0] in {"cobra","optlang","swiglpk","libsbml"} or "native_flux_balance" in name:
            deny()
        return actual_import(name,*args,**kwargs)
    with monkeypatch.context() as m:
        m.setattr(socket,"socket",deny);m.setattr(subprocess,"run",deny);m.setattr(subprocess,"Popen",deny)
        m.setattr(builtins,"__import__",guarded_import)
        sheet=populate_flux_balance_sheet(bundle=parse_fba_capture(payloads,expected=plan["identity"]))
        assert digest(sheet)==digest(original_sheet)
        calculated=calculate_flux_balance_sheet(sheet,parameters=original_calculations["parameters"])
        assert calculated==original_calculations
        projected=project_fba_result(sheet,calculated,selector=_selector(positions=[2,0]))
        before=digest(sheet)
        changed=deepcopy(calculated["parameters"]);changed["objective_absolute_tolerance"]=0
        # Saved-only rerender/recalculation cannot reopen native files or parser.
        m.setattr(builtins,"open",deny);m.setattr(io,"open",deny)
        saved=calculate_flux_balance_sheet(sheet,parameters=changed)
        saved_projection=project_fba_result(sheet,saved,selector=_selector("run_diagnostics",fields=["objective"]))
        assert digest(sheet)==before
    assert projected["rows"][0]["values"]["flux"]["flux"]["value"]==10
    assert saved_projection["rows"][0]["value"]["check"]["full_calculated"]["value"]==10
    evidence={"profile":profile,"evidence_class":"original688 authentic retained bytes; new parser/sheet/calculation/projection consumer check",
        "payload_roles":list(payloads),"sheet_sha256":before,"original_sheet_sha256":digest(original_sheet),
        "parser_calls":1,"sheet_population_calls":1,"calculator_calls":2,"native_calls":0,"acquisition_calls":0,
        "projection":projected,"saved_projection":saved_projection}
    (Path(os.environ["HMMER529_ATTEMPT"])/("projection693-chain-"+profile+".json")).write_text(json.dumps(evidence,allow_nan=False))
