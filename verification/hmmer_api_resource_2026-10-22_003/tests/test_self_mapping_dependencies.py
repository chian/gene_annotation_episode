"""Actual synthetic self operands; dependencies are identities, roles are not."""
import hashlib
import json
import os
from pathlib import Path
import random

import pytest

from gene_annotation_episode import read_mapping
from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_native_read_mapping import binary, checked


def prepare(tmp_path, reads, *, native=False):
    path=tmp_path/"explicitly-synthetic.fastq"
    path.write_text("".join(f"@synthetic_{i}\n{sequence}\n+\n"+"?"*len(sequence)+"\n"
        for i,sequence in enumerate(reads)))
    store=Store(tmp_path/"state");store.create_problem(path,molecule="dna")
    tools=ToolRegistry(store,minimap2_executable=binary() if native else None)
    target,=store.targets()
    selected=checked(tools,"library.select",{"library_ref":target["id"],"ordinal_ranges":[{"start":0,"end":len(reads)}]})
    members=checked(tools,"library.members",{"library_ref":target["id"],"selection_ref":selected["selection"]["id"]})["members"]
    return store,tools,selected,[row["id"] for row in members]


def test_actual_native_self_placement_and_later_independent_row_keep_roles_and_one_dependency_identity(tmp_path,monkeypatch):
    rng=random.Random(1964)
    original="".join(rng.choice("ACGT") for _ in range(6000))
    store,tools,selected,subjects=prepare(tmp_path,[original,original[500:5500]],native=True)
    with store:
        reference=subjects[0]
        args={"query_selection_ref":selected["selection"]["id"],"reference_refs":[reference],"preset":"map-ont"}
        outcome=tools.execute("reads.map",args,scope=selected["scope"],operation_key="synthetic-self-native")
        assert outcome["status"] == "completed",outcome
        body=outcome["result"]
        assert body["reported_placement_count"] == 2 and body["projection_error_count"] == 0
        assert {row["query_name"] for row in body["records"]} == set(subjects)
        source=store.get(body["source_ref"])
        assert source["operand_refs"] == [reference]
        assert source["query_selection_ref"] == selected["selection"]["id"]
        raw=store.get_artifact(source["stdout_ref"])
        for row in body["records"]:
            observation=store.get(row["observation_ref"])
            query=row["query_name"]
            assert observation["subject_refs"] == [query] and observation["source_subject_refs"] == [reference]
            assert observation["dependencies"] == list(dict.fromkeys([query,reference,selected["selection"]["id"]]))
            assert [(part["role"],part["subject_ref"]) for part in observation["operand_intervals"]] == [
                ("query",query),("reference",reference)]
            locator=observation["native_minimap2"]
            columns=raw[locator["row_start"]:locator["row_end"]].decode().split("\t")
            assert (columns[0],columns[5]) == (query,reference)
            assert observation["source_ref"] == source["id"]
        self_row=next(row for row in body["records"] if row["query_name"] == reference)
        self_observation=store.get(self_row["observation_ref"])
        assert self_observation["dependencies"] == [reference,selected["selection"]["id"]]
        assert next(item["value"]["value"] for item in self_observation["measurements"]
            if item["name"] == "identity_fraction") == 1
        assert len(outcome["record_refs"]) == 4  # source, both placements, search custody
        assert not store.current_annotations() and project_credit(store).credit == 0
        async def forbidden(*args,**kwargs):
            pytest.fail("committed self-placement operation reran native work")
        monkeypatch.setattr(read_mapping,"run_mapping",forbidden)
        assert tools.execute("reads.map",args,scope=selected["scope"],operation_key="synthetic-self-native") == outcome
        if destination := os.environ.get("GENE_EPISODE_SELF_MAPPING_CUSTODY"):
            directory=Path(destination);directory.mkdir(parents=True,exist_ok=False)
            files={}
            for name,content in {"input.fastq":(tmp_path/"explicitly-synthetic.fastq").read_bytes(),
                "native-source.json":store.get_artifact(source["artifact_ref"]),
                "native.stdout.paf":raw,"native.stderr":store.get_artifact(source["stderr_ref"])}.items():
                (directory/name).write_bytes(content)
                files[name]={"bytes":len(content),"sha256":hashlib.sha256(content).hexdigest()}
            exported=export_annotation(store,directory/"portable.json",scope=selected["scope"],include_artifacts=True)
            (directory/"CUSTODY.json").write_text(json.dumps({
                "meaning":"actual_native_self_overlap_on_explicitly_synthetic_reads_no_annotation",
                "request":{"name":"reads.map","arguments":args,"scope":selected["scope"]},
                "result":outcome,"source":source,
                "observations":[store.get(row["observation_ref"]) for row in body["records"]],
                "files":files,"export":exported,"current_annotation_count":0},indent=2)+"\n")


@pytest.mark.parametrize("tool",["sequence.align","reads.align"])
def test_actual_pairwise_self_operand_keeps_both_roles_without_duplicate_dependencies(tmp_path,tool):
    store,tools,selected,subjects=prepare(tmp_path,["ACGTAGCTGGTA","TAGCTG"])
    with store:
        query,other=subjects
        args={"reference_ref":query,"molecule":"dna","mode":"local"}
        args.update({"query_ref":query} if tool == "sequence.align" else {"subject_refs":subjects})
        result=tools.execute(tool,args,scope=selected["scope"])
        assert result["status"] == "completed",result
        records=([result["result"]] if tool == "sequence.align" else result["result"]["records"])
        for row in records:
            observation=store.get(row["observation_ref"])
            subject=observation["subject_refs"][0]
            assert observation["dependencies"] == ([query] if subject == query else [other,query])
            assert observation["source_subject_refs"] == [query]
            assert [(part["role"],part["subject_ref"]) for part in observation["operand_intervals"]] == [
                ("query",subject),("reference",query)]
            source=store.get(observation["source_ref"])
            actual=json.loads(store.get_artifact(source["artifact_ref"]))
            assert actual["aligned"] and actual["query_coverage"] == 1
        assert not store.current_annotations() and project_credit(store).credit == 0
