"""Native representability, not scientific quality or resource-budget tests."""
import asyncio
import json

import pytest

from gene_annotation_episode import read_mapping as mapper
from gene_annotation_episode.cli import main
from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


@pytest.mark.parametrize("name,value",[("kmer",1),("kmer",28),("window",1),("window",255),
    ("seed",0),("seed",2147483647),("max_secondary",0),("max_secondary",2147483647)])
def test_native_parameter_boundaries_preserve_original_selected_integer(name,value):
    given={name:value}
    result=mapper.settings("map-ont",given)
    assert result["overrides"] == given and type(result["overrides"][name]) is int
    assert given == {name:value}


@pytest.mark.parametrize("name,value,low,high",[("kmer",0,1,28),("kmer",29,1,28),
    ("window",0,1,255),("window",256,1,255),("window",4294967306,1,255),
    ("seed",-1,0,2147483647),("seed",2147483648,0,2147483647),
    ("max_secondary",-1,0,2147483647),("max_secondary",2147483648,0,2147483647)])
def test_native_unrepresentable_value_reports_exact_field_and_range(name,value,low,high):
    with pytest.raises(ContractError,match="native_mapping_integer_out_of_range") as failure:
        mapper.settings("map-ont",{name:value})
    assert failure.value.detail == {"field_path":["parameters",name],"minimum":low,"maximum":high,
        "value":value,"native_representation":"minimap2_2_31_supported_integer_interface"}


@pytest.mark.parametrize("name",["kmer","window","seed","max_secondary"])
@pytest.mark.parametrize("value",[True,False,1.5,"1"])
def test_native_integer_interface_does_not_coerce_boolean_float_or_string(name,value):
    with pytest.raises(ContractError,match="native_mapping_integer_required") as failure:
        mapper.settings("map-ont",{name:value})
    assert failure.value.detail["field_path"] == ["parameters",name]
    assert failure.value.detail["actual_type"] == type(value).__name__


@pytest.mark.parametrize("cpu",[1,2147483647])
def test_caller_cpu_representable_boundaries_only_inspect_configuration(cpu):
    assert mapper.local_configuration(cpu=cpu)["cpu"] == cpu  # never spawn these thread counts


@pytest.mark.parametrize("cpu",[0,-1,2147483648,True,False])
def test_caller_cpu_representation_errors_are_actionable_before_execution(cpu):
    with pytest.raises(ContractError) as failure:
        mapper.local_configuration(cpu=cpu)
    assert str(failure.value) == ("native_mapping_integer_required" if type(cpu) is bool else "native_mapping_integer_out_of_range")
    assert failure.value.detail["field_path"] == ["local_tools","minimap2_cpu"]
    assert failure.value.detail["minimum"] == 1 and failure.value.detail["maximum"] == 2147483647


def prepared(tmp_path):
    fastq=tmp_path/"synthetic.fq";fastq.write_text("@read\nACGT\n+\nIIII\n")
    store=Store(tmp_path/"state");store.create_problem(fastq,molecule="dna")
    target,=store.targets();tools=ToolRegistry(store)
    selected=tools.execute("library.select",{"library_ref":target["id"],"ordinal_ranges":[{"start":0,"end":1}]})
    material=store.register_material(data=">synthetic_ref\nACGT\n",format="fasta",molecule="dna")
    parsed=store.parse_material(material["id"])
    reference=store.material_reference(store.material_members(parsed["collection_ref"])["members"][0]["id"])
    args={"query_selection_ref":selected["result"]["selection"]["id"],"reference_refs":[reference["id"]],"preset":"map-ont"}
    return store,tools,args


def test_catalog_and_direct_interface_share_native_bounds_and_zero_alias(tmp_path):
    store,tools,args=prepared(tmp_path)
    with store:
        schema=tools.catalog()["reads.map"]["input_schema"]
        expected={"kmer":(1,28),"window":(1,255),"seed":(0,2147483647),"max_secondary":(0,2147483647)}
        for name,(low,high) in expected.items():
            field=schema["properties"]["parameters"]["properties"][name]
            assert (field["minimum"],field["maximum"]) == (low,high)
            for value in (low,high):
                validate_schema({**args,"parameters":{name:value}},schema)
            with pytest.raises(ContractError):
                validate_schema({**args,"parameters":{name:high+1}},schema)
        assert "Native -N0" in schema["properties"]["parameters"]["properties"]["max_secondary"]["description"]
        result=mapper.settings("map-ont",{"max_secondary":0,"secondary":True})
        assert result["overrides"] == {"max_secondary":0,"secondary":True}
        assert result["native_option_effects"] == [{"option":"max_secondary","requested":0,
            "native_effect":"secondary_output_disabled_prior_preset_internal_best_n_retained",
            "secondary_yes_does_not_override_zero_alias":True}]


@pytest.mark.parametrize("parameters",[{"window":4294967306},{"window":256},{"kmer":29},
    {"seed":2147483648},{"max_secondary":2147483648},{"window":True}])
def test_ordinary_tool_feedback_stops_unrepresentable_native_arguments_before_work(tmp_path,monkeypatch,parameters):
    store,tools,args=prepared(tmp_path)
    with store:
        async def forbidden(*a,**k):
            pytest.fail("invalid represented argument reached native preparation")
        monkeypatch.setattr(tools,"_native_mapping_async",forbidden)
        before=store.count("source"),store.count("observation")
        output=tools.execute("reads.map",{**args,"parameters":parameters},operation_key="invalid-native-number")
        name=next(iter(parameters))
        assert output["status"] == "invalid" and output["record_refs"] == []
        assert output["feedback"]["code"] == ("native_mapping_integer_required" if type(parameters[name]) is bool else "native_mapping_integer_out_of_range")
        assert output["feedback"]["detail"]["field_path"] == ["parameters",name]
        assert (store.count("source"),store.count("observation")) == before
        assert not list(store.path.glob(".native-read-mapping-*"))
        assert tools.execute("reads.map",{**args,"parameters":parameters},operation_key="invalid-native-number") == output


@pytest.mark.parametrize("value",[2147483648,True])
def test_cli_cpu_configuration_preserves_field_range_error_without_native_work(tmp_path,capsys,value):
    store,tools,args=prepared(tmp_path);workspace=store.path;store.close()
    config=tmp_path/"invalid.toml";config.write_text("[local_tools]\nminimap2_cpu="+("true" if value is True else str(value))+"\n")
    assert main(["capabilities","--workspace",str(workspace),"--config",str(config)]) == 1
    output=json.loads(capsys.readouterr().out)
    assert output["status"] == "operational_failure"
    assert output["detail"] == ("native_mapping_integer_required" if value is True else "native_mapping_integer_out_of_range")
    assert output["error_detail"]["field_path"] == ["local_tools","minimap2_cpu"]
    assert (output["error_detail"]["minimum"],output["error_detail"]["maximum"]) == (1,2147483647)


@pytest.mark.parametrize("parameters,code,keyword",[
    ({"window":4294967306},"native_mapping_integer_out_of_range","maximum"),
    ({"window":True},"native_mapping_integer_required","type"),
    ({"seed":-1},"native_mapping_integer_out_of_range","minimum")])
def test_invalid_native_integer_feedback_creates_no_completed_action_observation(tmp_path,monkeypatch,parameters,code,keyword):
    from test_runtime import FixtureController,ScriptedProvider
    store,tools,args=prepared(tmp_path)
    with store:
        async def forbidden(*a,**k):
            pytest.fail("invalid native argument invoked native work")
        monkeypatch.setattr(tools,"_native_mapping_async",forbidden)
        def corrected_choice(context):
            assert context["feedback"]["code"] == code
            assert context["feedback"]["category"] == "action_contract"
            name=next(iter(parameters))
            assert context["feedback"]["detail"]["field_path"] == ["parameters",name]
            assert context["feedback"]["detail"]["maximum"] == mapper.PARAMETER_RANGES[name][1]
            assert context["feedback"]["detail"]["schema_keyword"] == keyword
            assert context["controller"]["scores"] == []
            assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 0
            return {"selection":{"kind":"tool","tool":"state.query","arguments":{"refs":[]}},"report_update":{}}
        provider=ScriptedProvider([{"selection":{"kind":"tool","tool":"reads.map", "arguments":{**args,"parameters":parameters}},"report_update":{}},corrected_choice])
        summary=asyncio.run(run_workflow(store,tools,provider=provider,run_dir=tmp_path/"scripted-preflight",
            controller_factory=lambda path,initial:FixtureController(str(path),initial,1)))
        assert summary["completed_actions"] == 1 and summary["credit"] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM runtime_model_calls").fetchone()[0] == 2
        actions=store.db.execute("SELECT decision_index,result,credit FROM runtime_actions").fetchall()
        assert len(actions) == 1 and actions[0]["decision_index"] == 1
        assert json.loads(actions[0]["result"])["status"] == "completed" and actions[0]["credit"] == 0
