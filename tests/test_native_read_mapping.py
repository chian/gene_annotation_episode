"""Synthetic reads with actual native minimap2; no biological truth is asserted."""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import random

from Bio.Seq import Seq
import pytest

from gene_annotation_episode.domain import REASONING_SCHEMA
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.episodic_workflow.root.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry


def binary():
    explicit = os.environ.get("GENE_EPISODE_MINIMAP2")
    candidates = ([Path(explicit)] if explicit else []) + [parent/"resources/software/minimap2-2.31/source/minimap2-2.31/minimap2"
        for parent in Path(__file__).resolve().parents]
    for path in candidates:
        if path.is_file():
            return str(path)
    pytest.skip("Explicit minimap2 or pinned local engineering binary is not installed")


def sequence():
    rng = random.Random(144)
    return "".join(rng.choice("ACGT") for _ in range(6000))


def checked(tools, name, args, **kwargs):
    value = tools.execute(name, args, **kwargs)
    assert value["status"] == "completed", value
    return value["result"]


def fixture(tmp_path, *, copies=2, executable=None):
    reference = sequence()
    altered = reference[100:5100]
    altered = altered[:2000] + "GGG" + altered[2000:3500] + altered[3502:]
    reads = [altered, str(Seq(reference[500:5500]).reverse_complement())]
    reads = [reads[i % 2] for i in range(copies)]
    path = tmp_path/"synthetic.fastq"
    path.write_text("".join(f"@duplicate source_title_{i}\n{read}\n+\n" + ("I" if i % 2 == 0 else "?")*len(read) + "\n"
        for i, read in enumerate(reads)))
    store = Store(tmp_path/"state")
    store.create_problem(path, molecule="dna")
    target, = store.targets()
    tools = ToolRegistry(store, run_directory=store.path / 'tool-run', minimap2_executable=executable if executable is not None else binary())
    material = store.register_material(data=">actual_reference\n"+reference+"\n", format="fasta", molecule="dna")
    parsed = store.parse_material(material["id"])
    member, = store.material_members(parsed["collection_ref"])["members"]
    comparison = store.material_reference(member["id"])
    selection = checked(tools, "library.select", {"library_ref": target["id"], "ordinal_ranges": [{"start":0,"end":copies}]})
    args = {"query_selection_ref": selection["selection"]["id"], "reference_refs": [comparison["id"]], "preset":"map-ont"}
    return store, tools, target, selection, args


def test_native_replay_uses_saved_operation_and_new_work_reuses_only_exact_index(tmp_path, monkeypatch):
    store, tools, target, selected, args = fixture(tmp_path)
    with store:
        first = tools.execute("reads.map", args, operation_key="first")
        assert first["status"] == "completed"
        assert not first["result"]["index"]["reused"]
        second = checked(tools,"reads.map",args,operation_key="second")
        assert second["index"]["reused"] and second["index"]["cache_key"] == first["result"]["index"]["cache_key"]
        changed = checked(tools,"reads.map",{**args,"parameters":{"kmer":13}},operation_key="different-index")
        assert not changed["index"]["reused"] and changed["index"]["cache_key"] != second["index"]["cache_key"]
        from gene_annotation_episode import read_mapping
        async def prohibited(*a,**k):
            pytest.fail("committed operation reran native work")
        monkeypatch.setattr(read_mapping,"run_mapping",prohibited)
        new_registry=ToolRegistry(store, run_directory=store.path / 'tool-run',minimap2_executable="/not/installed",minimap2_cpu=3)
        assert new_registry.execute("reads.map",args,operation_key="first") == first


def test_torn_disposable_cache_rebuilds_without_losing_selected_work(tmp_path):
    store, tools, target, selected, args = fixture(tmp_path)
    with store:
        first=checked(tools,"reads.map",args,operation_key="first")
        path=store.path/"cache"/"minimap2"/(first["index"]["cache_key"]+".json")
        metadata=json.loads(path.read_text());metadata.pop("stdout_base64");path.write_text(json.dumps(metadata))
        again=checked(tools,"reads.map",args,operation_key="new-attempt")
        assert not again["index"]["reused"] and again["reported_placement_count"] == 2


def test_selection_scope_and_selected_site_scope_are_distinct_from_reference_reuse(tmp_path):
    store, tools, target, selected, args = fixture(tmp_path)
    with store:
        members=checked(tools,"library.members",{"library_ref":target["id"]})["members"]
        child=checked(tools,"library.select",{"library_ref":target["id"],"member_refs":[members[0]["member_ref"]]})
        denied=tools.execute("reads.map",args,scope=child["scope"])
        assert denied["status"] == "invalid" and denied["feedback"]["code"] == "scope_members_outside_parent"
        local=checked(tools,"reads.map",{**args,"query_selection_ref":child["selection"]["id"]},scope=child["scope"])
        row=local["records"][0];obs=store.get(row["observation_ref"])
        q=row["query_interval"][0] if row["strand"] == "+" else row["query_interval"][1]-1
        p=row["reference_interval"][0]
        narrow={"subject_refs":[target["id"]],"segments":[{**store.coverage(row["query_name"])[0],"start":q,"end":q+1}]}
        assert checked(tools,"sequence.sites",{"alignment_ref":obs["id"],"positions":[p]},scope=narrow)["sites"][0]["query_position"] == q
        denied=tools.execute("sequence.sites",{"alignment_ref":obs["id"],"positions":[p+2]},scope=narrow)
        assert denied["status"] == "invalid" and "outside_assigned" in denied["feedback"]["code"]
        assert "native_minimap2" not in REASONING_SCHEMA["properties"]["observations"]["items"]["properties"]


def test_unconfigured_binary_is_actionable_and_no_scientific_publication(tmp_path):
    store, tools, target, selected, args = fixture(tmp_path)
    with store:
        before=store.db.execute("SELECT count(*) FROM records WHERE record_type='observation'").fetchone()[0]
        output=ToolRegistry(store, run_directory=store.path / 'tool-run').execute("reads.map",args,operation_key="unconfigured")
        assert output["status"] == "unavailable" and output["feedback"]["code"] == "minimap2_not_configured"
        assert store.db.execute("SELECT count(*) FROM records WHERE record_type='observation'").fetchone()[0] == before
        assert not list(store.path.glob(".native-read-mapping-*"))


def test_literal_aggregate_product_sites_do_not_invent_exact_ancestry_or_block_external_work(tmp_path):
    with Store(tmp_path/"aggregate") as store:
        root=store.create_problem(raw_sequence="ACGTACGT",molecule="dna")["subject_refs"][0]
        product=store.put("product",{"parent_refs":[root],"molecule":"dna","sequence_ref":store.artifact("ACGTACGT"),
            "derivation":"correction_hypothesis","context_refs":[],"footprint":store.coverage(root)},origin="tool")
        material=store.register_material(data=">reference\nACGTACGT\n",format="fasta",molecule="dna")
        parsed=store.parse_material(material["id"])
        reference=store.material_reference(store.material_members(parsed["collection_ref"])["members"][0]["id"])
        tools=ToolRegistry(store, run_directory=store.path / 'tool-run')
        aligned=checked(tools,"sequence.align",{"query_ref":product["id"],"reference_ref":reference["id"],"molecule":"dna","mode":"global"})
        result=checked(tools,"sequence.sites",{"alignment_ref":aligned["observation_ref"],"positions":[1]})
        assert result["sites"][0]["query_position"] == 1 and not store.has_exact_mapping(product["id"])
        assert store.get(result["observation_ref"])["operand_intervals"][0]["subject_ref"] == product["id"]
        denied=tools.execute("sequence.sites",{"alignment_ref":aligned["observation_ref"],"positions":[1]},
            scope={"subject_refs":[root],"segments":[{"target_ref":root,"start":1,"end":2,"unit":"nt"}]})
        assert denied["status"] == "invalid" and denied["feedback"]["code"] == "requested_measurement_outside_assigned_segments"


def test_cli_config_propagates_actual_mapping_binary_cpu_and_cache(tmp_path,capsys):
    from gene_annotation_episode.cli import main
    store,tools,target,selected,args=fixture(tmp_path)
    workspace=store.path
    store.close()
    cache=tmp_path/"caller-selected-cache"
    configuration=tmp_path/"caller.toml"
    configuration.write_text("[local_tools]\nminimap2_executable="+json.dumps(binary())+
        "\nminimap2_cpu=2\nminimap2_cache_dir="+json.dumps(str(cache))+"\n")
    assert main(["capabilities","--workspace",str(workspace),"--config",str(configuration)]) == 0
    catalog=json.loads(capsys.readouterr().out)
    binding=catalog["reads.map"]["configuration"]
    assert binding["executable"] == str(Path(binary()).resolve()) and binding["cpu"] == 2
    assert binding["cache_dir"] == str(cache.resolve())
    assert main(["tool","--workspace",str(workspace),"--config",str(configuration),"reads.map",
        "--args",json.dumps(args)]) == 0
    outcome=json.loads(capsys.readouterr().out)
    assert outcome["status"] == "completed"
    actual=outcome["result"]["resource_binding"]
    assert actual["executable"] == binding["executable"] and actual["cpu"] == 2
    assert actual["cache_dir"] == actual["effective_cache_dir"] == binding["cache_dir"]
    with Store(workspace) as reopened:
        source=reopened.get(outcome["result"]["source_ref"])
        metadata=json.loads(reopened.get_artifact(source["artifact_ref"]))
        command=metadata["commands"]["map"]
        assert command[command.index("-t")+1] == "2"
        assert reopened.current_annotations() == []
