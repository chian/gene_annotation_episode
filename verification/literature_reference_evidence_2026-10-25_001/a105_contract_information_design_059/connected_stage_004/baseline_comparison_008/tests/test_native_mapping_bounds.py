"""Actual pinned native boundary/zero-alias check with synthetic source bytes."""
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import struct

from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_native_read_mapping import binary,checked


def test_actual_native_index_keeps_requested_boundaries_and_zero_alias(tmp_path):
    rng=random.Random(1226)
    sequence="".join(rng.choice("ACGT") for _ in range(12000))
    query=sequence[1000:11000]
    fastq=tmp_path/"explicitly-synthetic.fastq"
    fastq.write_text("@synthetic_read\n"+query+"\n+\n"+"?"*len(query)+"\n")
    with Store(tmp_path/"state") as store:
        store.create_problem(fastq,molecule="dna")
        tools=ToolRegistry(store,minimap2_executable=binary(),minimap2_cpu=1)
        target,=store.targets()
        selected=checked(tools,"library.select",{"library_ref":target["id"],"ordinal_ranges":[{"start":0,"end":1}]})
        # Distinct actual reference identities with duplicate sequence supply
        # a native alternative placement without treating label equality as biology.
        material=store.register_material(data=">synthetic_reference_A\n"+sequence+"\n>synthetic_reference_B\n"+sequence+"\n",
            format="fasta",molecule="dna")
        parsed=store.parse_material(material["id"])
        refs=[store.material_reference(member["id"])["id"] for member in store.material_members(parsed["collection_ref"])["members"]]
        requested={"kmer":28,"window":255,"seed":2147483647,"max_secondary":0,"secondary":True}
        args={"query_selection_ref":selected["selection"]["id"],"reference_refs":refs,
            "preset":"map-ont","parameters":requested}
        result=tools.execute("reads.map",args,scope=selected["scope"],operation_key="synthetic-native-numeric-boundary")
        assert result["status"] == "completed",result
        source=store.get(result["result"]["source_ref"])
        metadata=json.loads(store.get_artifact(source["artifact_ref"]))
        index_path=Path(metadata["configuration"]["cache_dir"])/(metadata["index"]["cache_key"]+".mmi")
        raw_index=index_path.read_bytes()
        assert raw_index[:4] == b"MMI\x02"
        window,kmer,bucket_bits,sequence_count,flags=struct.unpack("=5I",raw_index[4:24])
        assert (window,kmer,sequence_count) == (255,28,2)
        assert metadata["settings"]["overrides"] == result["result"]["native_settings"]["overrides"] == requested
        index_command=metadata["commands"]["index"]
        assert index_command[index_command.index("-w")+1] == "255"
        assert index_command[index_command.index("-k")+1] == "28"
        command=metadata["commands"]["map"]
        assert command[command.index("-N")+1] == "0" and "--secondary=yes" in command
        assert command[command.index("--seed")+1] == "2147483647"
        assert command[command.index("-t")+1] == "1"
        stderr=store.get_artifact(source["stderr_ref"])
        assert b"changed '-N 0' to '-N 5 --secondary=no'" in stderr
        stdout=store.get_artifact(source["stdout_ref"])
        assert stdout and b"tp:A:S" not in stdout
        assert result["result"]["reported_placement_count"] == 1
        assert metadata["settings"]["native_option_effects"][0]["secondary_yes_does_not_override_zero_alias"]
        assert store.current_annotations() == []
        destination=os.environ.get("GENE_EPISODE_NATIVE_BOUNDS_CUSTODY")
        if destination:
            directory=Path(destination)
            directory.mkdir(parents=True,exist_ok=False)
            copied={}
            for name,content in {"input.fastq":fastq.read_bytes(),"index.mmi":raw_index,
                "mapping.stdout.paf":stdout,"mapping.stderr":stderr,"native-metadata.json":store.get_artifact(source["artifact_ref"]),
                "staged-queries.fasta":store.get_artifact(metadata["artifacts"]["queries.fasta"]),
                "staged-references.fasta":store.get_artifact(metadata["artifacts"]["references.fasta"])}.items():
                (directory/name).write_bytes(content)
                copied[name]={"bytes":len(content),"sha256":hashlib.sha256(content).hexdigest()}
            exported=export_annotation(store,directory/"portable.json",scope=selected["scope"],include_artifacts=True)
            receipt={"meaning":"actual_native_integer_boundary_and_zero_alias_with_explicitly_synthetic_reads_not_annotation",
                "request":{"name":"reads.map","arguments":args,"scope":selected["scope"]},
                "result":result,"native_version":source["version"],"native_configuration":metadata["configuration"],
                "native_index_header":{"window":window,"kmer":kmer,"bucket_bits":bucket_bits,"sequence_count":sequence_count,"flags":flags},
                "native_alias_warning":"changed '-N 0' to '-N 5 --secondary=no'",
                "selected_flags_preserved":True,"current_annotations":0,"files":copied,"export":exported}
            (directory/"CUSTODY.json").write_text(json.dumps(receipt,indent=2)+"\n")
