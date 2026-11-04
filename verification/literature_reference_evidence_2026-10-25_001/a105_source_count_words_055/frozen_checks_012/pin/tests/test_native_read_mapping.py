"""Synthetic reads with actual native minimap2; no biological truth is asserted."""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import random
import sys

from Bio.Seq import Seq
import pytest

from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.domain import ContractError, REASONING_SCHEMA
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.numerical import YieldController
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


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
    tools = ToolRegistry(store, minimap2_executable=executable if executable is not None else binary())
    material = store.register_material(data=">actual_reference\n"+reference+"\n", format="fasta", molecule="dna")
    parsed = store.parse_material(material["id"])
    member, = store.material_members(parsed["collection_ref"])["members"]
    comparison = store.material_reference(member["id"])
    selection = checked(tools, "library.select", {"library_ref": target["id"], "ordinal_ranges": [{"start":0,"end":copies}]})
    args = {"query_selection_ref": selection["selection"]["id"], "reference_refs": [comparison["id"]], "preset":"map-ont"}
    return store, tools, target, selection, args


def test_actual_native_placements_preserve_duplicate_titles_reverse_gap_insertions_and_sources(tmp_path):
    store, tools, target, selected, args = fixture(tmp_path)
    with store:
        original = deepcopy(store.problem())
        result = checked(tools, "reads.map", args, operation_key="native-placement")
        assert result["reported_placement_count"] == result["query_count"] == 2
        assert {row["strand"] for row in result["records"]} == {"+", "-"}
        assert len({row["query_name"] for row in result["records"]}) == 2
        source = store.get(result["source_ref"])
        metadata = json.loads(store.get_artifact(source["artifact_ref"]))
        assert source["version"] == "2.31-r1302" or source["version"]
        assert metadata["configuration"]["executable_sha256"] == hashlib.sha256(Path(binary()).read_bytes()).hexdigest()
        assert "-c" in metadata["commands"]["map"] and "--cs=long" in metadata["commands"]["map"]
        assert metadata["input_metadata"]["selection_membership_sha256"] == selected["selection"]["membership_sha256"]
        assert metadata["configuration"]["effective_cache_dir"] == str(store.path/"cache"/"minimap2")
        raw = store.get_artifact(source["stdout_ref"])
        assert b"cg:Z:" in raw and b"cs:Z:" in raw
        plus = next(row for row in result["records"] if row["strand"] == "+")
        obs = store.get(plus["observation_ref"])
        locator = obs["native_minimap2"]
        assert raw[locator["row_start"]:locator["row_end"]].split(b"\t")[0].decode() == plus["query_name"]
        sites = checked(tools, "sequence.sites", {"alignment_ref": obs["id"], "positions": [0,2099,2100,3600,5999]})
        assert [row["relationship"] for row in sites["sites"]] == ["outside_alignment","identical","identical","gap","outside_alignment"]
        assert sites["sites"][3]["query_position"] is None
        assert sites["insertions"] == [{"reference_boundary":2100, "query_interval":[2000,2003],
            "query_strand":"+", "query_sequence":"GGG", "query_quality_characters":"III",
            "quality_encoding":"unspecified", "native_operation":"I"}]
        assert sites["sites"][1]["query_quality_character"] == "I" and sites["sites"][1]["query_quality_score"] is None
        minus = next(row for row in result["records"] if row["strand"] == "-")
        reverse = checked(tools,"sequence.sites",{"alignment_ref":minus["observation_ref"],"positions":[500,5499]})["sites"]
        assert [row["query_position"] for row in reverse] == [4999,0]
        assert all(row["query_residue"] == str(Seq(row["query_original_residue"]).complement()) for row in reverse)
        assert store.problem() == original and not store.current_annotations()
        assert project_credit(store).credit == 0  # native activity is not an annotation
        assert not list(store.path.glob(".native-read-mapping-*"))


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
        new_registry=ToolRegistry(store,minimap2_executable="/not/installed",minimap2_cpu=3)
        assert new_registry.execute("reads.map",args,operation_key="first") == first


def test_torn_disposable_cache_rebuilds_without_losing_selected_work(tmp_path):
    store, tools, target, selected, args = fixture(tmp_path)
    with store:
        first=checked(tools,"reads.map",args,operation_key="first")
        path=store.path/"cache"/"minimap2"/(first["index"]["cache_key"]+".json")
        metadata=json.loads(path.read_text());metadata.pop("stdout_base64");path.write_text(json.dumps(metadata))
        again=checked(tools,"reads.map",args,operation_key="new-attempt")
        assert not again["index"]["reused"] and again["reported_placement_count"] == 2


def test_native_pages_parent_form_current_annotation_credit_correction_and_portable_closure(tmp_path):
    store, tools, target, selected, args = fixture(tmp_path, copies=14)
    with store:
        result=checked(tools,"reads.map",args,operation_key="fourteen")
        assert result["reported_placement_count"] == 14 and len(result["records"]) == 12
        assert not result["record_refs_are_preview"]
        page=checked(tools,"state.query",result["all_observations_query"])
        assert len(page["records"]) == 12 and page["next_query"]
        remaining=checked(tools,"state.query",page["next_query"])
        assert len(remaining["records"]) == 3 and remaining["next_query"] is None
        assert sum(row["kind"] == "alignment" for row in page["records"]+remaining["records"]) == 14
        assert sum(row["kind"] == "source_content" for row in page["records"]+remaining["records"]) == 1
        obs=store.get(result["records"][0]["observation_ref"]);subject=obs["subject_refs"][0]
        h=store.put("hypothesis",{"subject_refs":[subject],"predicate":"sequence_integrity",
            "value":{"type":"enum","value":"unresolved"},"context_refs":[]},origin="reasoning")
        a_payload={"hypothesis_ref":h["id"],"observation_ref":obs["id"],"relation":"strengthens",
            "applicability":"direct","extent_basis":"observed_extent","condition_refs":[],"assumption_refs":[],"expected_revision":0}
        a=store.put("assessment",a_payload,origin="reasoning")
        n_payload={"subject_ref":subject,"footprint_kind":"localized","coherent_sets":[{"interpretations":[{
            "hypothesis_ref":h["id"],"disposition":"unresolved","assessment_refs":[a["id"]]}],"context_refs":[]}],
            "alternative_refs":[],"resolution":"unresolved","expected_revision":0}
        n=store.put("annotation",n_payload,origin="reasoning")
        projected=project_credit(store,details_limit=100)
        assert projected.credit>0 and {row["member_ref"] for row in projected.source_contributions} == {store.get(subject)["member_ref"]}
        workflow=Workflow.__new__(Workflow);workflow.store=store
        schema={"type":"object","additionalProperties":False,"required":["placements","interpretations","selection"],"properties":{
            "placements":{"type":"array","items":{"type":"string","format":"reference","x-reference-namespace":"observation"}},
            "interpretations":{"type":"array","items":{"type":"string","format":"reference","x-reference-namespace":"annotation"}},
            "selection":{"type":"string","format":"reference","x-reference-namespace":"read_selection"}}}
        form={"placements":[obs["id"]],"interpretations":[n["id"]],"selection":selected["selection"]["id"]}
        assert validate_form(form,schema,workflow.resolver(selected["scope"])) == form
        exported=export_annotation(store,tmp_path/"portable.json",include_artifacts=True,page_size=2)
        doc=json.loads(Path(exported["json"]["path"]).read_text())
        nodes={row["id"]:row for row in doc["records"]}
        assert obs["id"] in nodes and nodes[obs["source_ref"]]["provider"] == "minimap2.mapping"
        artifact_ids={row["id"] for row in doc["artifacts"]}
        assert set(store.get(obs["source_ref"])["auxiliary_artifact_refs"]) <= artifact_ids
        assert nodes[obs["id"]]["native_minimap2"] == obs["native_minimap2"]
        before=projected.credit
        corrected=store.put("assessment",{**a_payload,"expected_revision":1,"applicability":"incomparable"},origin="reasoning")
        n_payload["coherent_sets"][0]["interpretations"][0]["assessment_refs"]=[corrected["id"]]
        store.put("annotation",{**n_payload,"expected_revision":1},origin="reasoning")
        after=project_credit(store).credit
        controller=YieldController("synthetic-mapping-correction",before,.001)
        assert controller.observe("reason:correction",{"credit":after}).marginal_credit == after-before < 0
        assert controller.estimator.scores == (after-before,)


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
        output=ToolRegistry(store).execute("reads.map",args,operation_key="unconfigured")
        assert output["status"] == "unavailable" and output["feedback"]["code"] == "minimap2_not_configured"
        assert store.db.execute("SELECT count(*) FROM records WHERE record_type='observation'").fetchone()[0] == before
        assert not list(store.path.glob(".native-read-mapping-*"))


def test_zero_placement_subset_search_exports_actual_derived_reference_and_custody(tmp_path):
    store, tools, target, selected, args = fixture(tmp_path)
    with store:
        original=deepcopy(store.problem())
        members=checked(tools,"library.members",{"library_ref":target["id"]})["members"]
        child=checked(tools,"library.select",{"library_ref":target["id"],"member_refs":[members[0]["member_ref"]]})
        # This actual external feature has no direct source_ref. Its ancestry
        # crosses a native extraction product/context/source to the reference.
        view=checked(tools,"sequence.view",{"subject_ref":args["reference_refs"][0],"molecule":"dna",
            "segments":[{"start":0,"end":100}]})
        product=store.get(view["records"][0]["product_ref"])
        external=store.put("feature",{"subject_ref":product["id"],"kind":"sequence_region",
            "segments":[{"start":10,"end":70}],"strand":"+","context_refs":[]},origin="reasoning")
        assert not store.roots(external["id"]) and "source_ref" not in external
        output=tools.execute("reads.map",{**args,"query_selection_ref":child["selection"]["id"],
            "reference_refs":[external["id"]]},scope=child["scope"],operation_key="actual-no-placement")
        assert output["status"] == "completed",output
        result=output["result"]
        assert result["reported_placement_count"] == 0
        summary=store.get(result["search_result_observation_ref"])
        source=store.get(result["source_ref"])
        assert summary["kind"] == "source_content" and summary["operand_intervals"] == []
        assert summary["source_subject_refs"] == source["operand_refs"] == [external["id"]]
        assert summary["dependencies"] == [child["selection"]["id"],external["id"]]
        assert source["query_selection_ref"] == child["selection"]["id"]
        working=store.reasoning_view(child["scope"],limit=100)
        assert summary["id"] in {row["id"] for row in working["observations"]}
        workflow=Workflow.__new__(Workflow);workflow.store=store
        assert workflow.resolver(child["scope"])(summary["id"],"observation")
        assert project_credit(store).credit == project_credit(store,child["scope"]).credit == 0
        h=store.put("hypothesis",{"subject_refs":[target["id"]],"predicate":"sequence_integrity",
            "value":{"type":"enum","value":"unresolved"},"context_refs":[]},origin="reasoning")
        with pytest.raises(ContractError,match="annotation_library_context_outside_assigned_scope"):
            store.put("annotation",{"subject_ref":target["id"],"footprint_kind":"whole_input_context",
                "coherent_sets":[{"interpretations":[{"hypothesis_ref":h["id"],"disposition":"unresolved",
                    "assessment_refs":[]}],"context_refs":[]}],"alternative_refs":[],"resolution":"unresolved",
                "expected_revision":0},origin="reasoning",scope=child["scope"])
        exported=export_annotation(store,tmp_path/"no-hit.json",scope=child["scope"],include_artifacts=True)
        document=json.loads(Path(exported["json"]["path"]).read_text())
        nodes={row["id"]:row for row in document["records"]}
        assert {summary["id"],source["id"],external["id"],product["id"],product["mapping_source_ref"],args["reference_refs"][0]} <= nodes.keys()
        assert document["inputs"] == [target]
        assert document["eligible_geometry"][0]["position_mass"] == members[0]["length"]
        assert store.problem() == original and store.current_annotations() == []
        other=checked(tools,"library.select",{"library_ref":target["id"],"member_refs":[members[1]["member_ref"]]})
        # Custody is reusable context. Its readability does not reinterpret
        # selectionA as a measurement of disjoint B or change B's denominator.
        readable=checked(tools,"state.query",{"refs":[summary["id"],source["id"]]},scope=other["scope"])
        assert readable["records"][0] == summary
        resolver=workflow.resolver(other["scope"])
        assert resolver(summary["id"],"observation") and not resolver(summary["id"],"read_subject")
        assert not resolver(members[0]["id"],"read_subject")
        generic={"type":"object","additionalProperties":False,"required":["custody_refs"],"properties":{
            "custody_refs":{"type":"array","items":{"type":"string","format":"reference","x-reference-namespace":"observation"}}}}
        assert validate_form({"custody_refs":[summary["id"]]},generic,resolver) == {"custody_refs":[summary["id"]]}
        assert source["query_selection_ref"] != other["selection"]["id"] and summary["operand_intervals"] == []
        assert project_credit(store,other["scope"]).credit == 0
        second=export_annotation(store,tmp_path/"disjoint.json",scope=other["scope"])
        disjoint=json.loads(Path(second["json"]["path"]).read_text())
        assert disjoint["eligible_geometry"][0]["position_mass"] == members[1]["length"]
        included={row["id"]:row for row in disjoint["records"]}
        assert included[source["id"]]["query_selection_ref"] == child["selection"]["id"]


def test_literal_aggregate_product_sites_do_not_invent_exact_ancestry_or_block_external_work(tmp_path):
    with Store(tmp_path/"aggregate") as store:
        root=store.create_problem(raw_sequence="ACGTACGT",molecule="dna")["subject_refs"][0]
        product=store.put("product",{"parent_refs":[root],"molecule":"dna","sequence_ref":store.artifact("ACGTACGT"),
            "derivation":"correction_hypothesis","context_refs":[],"footprint":store.coverage(root)},origin="tool")
        material=store.register_material(data=">reference\nACGTACGT\n",format="fasta",molecule="dna")
        parsed=store.parse_material(material["id"])
        reference=store.material_reference(store.material_members(parsed["collection_ref"])["members"][0]["id"])
        tools=ToolRegistry(store)
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
