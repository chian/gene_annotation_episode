"""Retain actual function-generated examples through an existing bounded job."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]


def worker(destination):
    sys.path.insert(0, str(ROOT / "tests"))
    from test_blast_vdb_inputs import (inputs, collect, hsp, identity, provenance, entity, metadata,
        extraction_context, reference_binding_fixture, binding, RUNINFO, GBSEQ)
    from test_blast_vdb_calculators import translated_case, feature, population, population_entity, table_values
    from gene_annotation_episode.blast_vdb_inputs import (populate_blast_vdb_sheet, parse_ncbi_sra_runinfo,
        parse_ncbi_gbseq_vdb_metadata, parse_blast_vdb_member_sequences, bind_blast_vdb_metadata)
    from gene_annotation_episode.blast_vdb_calculators import calculate_blast_vdb_components
    examples = {"blastn_two_reads_one_sequence": inputs(), "tblastn_forward_cds": translated_case(offset=True),
                "tblastn_reverse_cds": translated_case(reverse=True), "blastn_partial_table": table_values(),
                "blastn_missing_samples": inputs(samples=False)}
    unknown = inputs(); unknown["dataset_records"][0]["search_context"]["query_extent"] = dict(mode="unknown", interval=None, source=None)
    unknown["dataset_records"][1]["search_context"]["query_extent"] = dict(mode="unknown", interval=None, source=None)
    examples["blastn_unknown_query_extent"] = unknown
    native = dict(len=8, description=[dict(id="NC_X.1", accession="NC_X.1")], hsps=[hsp()])
    catalogue = inputs(collect(hits=[native])["searches"][0], kind="reference")
    catalogue["member_bindings"][0]["relationship"] = "catalog_membership"
    dataset = deepcopy(catalogue["dataset_records"][0]); dataset["dataset_key"] = "D1"
    member = deepcopy(catalogue["member_bindings"][0]); member["dataset_key"] = "D1"
    catalogue["dataset_records"].append(dataset); catalogue["member_bindings"].append(member)
    examples["blastn_two_catalogues_no_origin"] = catalogue
    values = inputs(); entities = []
    for i in range(10):
        member = {k: deepcopy(values["member_bindings"][i % 2][k]) for k in ("dataset_key", "member_kind", "member_identifier")}
        if i >= 2:
            member["member_identifier"] = identity(f"extra{i}")
        entities.append(population_entity("read", member=member))
    group = values["sequence_identity_bindings"][0]["binding"]["sequence_group"]
    values["population_records"] = [population(values, "reads", entities),
        population(values, "unique_sequences", [population_entity("unique_sequence", group=g) for g in [group, "sha256:"+"1"*64, "sha256:"+"2"*64, "sha256:"+"3"*64]]),
        population(values, "samples", [population_entity("sample", sample=f"S{i}") for i in range(5)])]
    examples["blastn_separate_population_units"] = values
    fn = {"namespace": "EC", "value": "1.2.3.4"}
    values["population_records"][0]["function_counts"] = [dict(function=fn, count=3,
        assignment_scope="whole_sequence", source=provenance("/function-population"))]
    merged = inputs()
    merged["member_bindings"][1]["sample_key"] = "S0"
    merged["dataset_records"][1]["sample_links"][0].update(sample_key="S0", sample_identifier=identity("S0", "sample"))
    sample = next(m for m in merged["reference_metadata"] if m["metadata_key"] == "sample1")
    sample["entity"]["sample_key"] = "S0"; sample["identifiers"] = [identity("S0", "sample")]
    examples["blastn_two_reads_one_sample"] = merged
    native = dict(len=12, description=[dict(id="r1", accession="r1")], hsps=[
        hsp("AAAAAA"), hsp("AAAAAA", query_from=4, query_to=9, hit_from=4, hit_to=9)])
    overlap = inputs(collect(query="A"*12, selected=[0, 9], hits=[native])["searches"][0], symbols=["A"*12])
    feature(overlap, interval=[4, 8], kind="misc_feature")
    feature(overlap, interval=[10, 12], identifier="outside", kind="misc_feature")
    examples["blastn_overlap_union"] = overlap
    features = inputs(); feature_members = []
    for i in range(2):
        feature(features, interval=[0, 8], identifier=f"f{i}", kind="misc_feature", function=fn, hit=i)
    for i in range(8):
        member = {k: deepcopy(features["member_bindings"][i % 2][k]) for k in ("dataset_key", "member_kind", "member_identifier")}
        feature_members.append(population_entity("feature", member=member, feature_id=identity(f"f{i}", "synthetic:feature")))
    features["population_records"] = [population(features, "features", feature_members,
        functions=[dict(function=fn, count=2, assignment_scope="feature", source=provenance("/feature-population"))],
        function_members=[dict(function=fn, entities=feature_members[:2])])]
    examples["blastn_feature_population"] = features
    hits = [dict(len=8, description=[dict(id=f"r{i}", accession=f"r{i}")], hsps=[hsp()]) for i in range(3)]
    taxa = inputs(collect(hits=hits)["searches"][0], symbols=["ACGTACGT", "ACGTACGA", "ACGTACGC"])
    for i, taxid in enumerate([10, 10, 20]):
        m = next(m for m in taxa["reference_metadata"] if m["metadata_key"] == f"member{i}")
        m.update(taxid=taxid, taxid_scope="entity_organism", lineage=[dict(taxid=taxid, rank="species", name=str(taxid))])
    taxa["target_context"] = dict(query_operand=deepcopy(taxa["query_binding"]["operand"]), taxid=10,
        lineage=[dict(taxid=10, rank="species", name="A")], independent_of_search=True, source=provenance("/target"))
    taxa["reference_metadata"][0]["assembly"] = dict(identifier=identity("assembly"), completeness_percent=97.5,
        contamination_percent=120, contig_count=3, contig_n50=100, total_sequence_length=200,
        method="CheckM", method_version="synthetic", source=provenance("/checkm"), linkage_source=provenance("/assembly-link"))
    examples["blastn_taxonomy_quality"] = taxa
    native = dict(len=8, description=[dict(id="r1", accession="r1")], hsps=[None, hsp()])
    archive = collect(hits=[native], archive=True)
    examples["blastn_archive_member0_partial_hsps"] = inputs(archive["searches"][0])
    examples["blastn_archive_member1_partial_hsps"] = inputs(archive["searches"][1])
    native = dict(len=8, description=[dict(id="r1", accession="r1")], hsps=[dict(bit_score=42, evalue=0,
        align_len=5, identity=4, gaps=1, query_from=1, query_to=5, hit_from=1, hit_to=4)])
    examples["blastn_partial_without_traceback"] = inputs(collect(hits=[native],
        completion={"native_returncode": 1, "producer_complete": False})["searches"][0])
    native = dict(len=9, description=[dict(id="r1", accession="r1")], hsps=[hsp("MAK", hit_to=9, hit_frame=1)])
    pssm = inputs(collect(program="tblastn_vdb", query="MAK", query_kind="pssm", hits=[native])["searches"][0], symbols=["ATGGCTAAA"])
    pssm["reference_metadata"].append(metadata("master", entity("query_master", pssm="pssm"), source=provenance("/master"),
        master_mapping=dict(pssm_key="pssm", num_columns=3, columns=[dict(column=0, master_position=0, symbol="M"),
            dict(column=1, master_position=None, symbol="-"), dict(column=2, master_position=1, symbol="K")])))
    examples["tblastn_pssm_master_with_gap"] = pssm
    examples["blastn_qualified_zero_hits"] = inputs(collect(hits=[])["searches"][0])
    inventory = []
    def save(name, value):
        path = destination / name
        path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
        inventory.append(dict(file=name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), size_bytes=path.stat().st_size))
    summaries = {}
    for name, arguments in examples.items():
        sheet = populate_blast_vdb_sheet(**arguments)
        components = calculate_blast_vdb_components(sheet)
        assert calculate_blast_vdb_components(json.loads(json.dumps(sheet))) == components
        save(name + ".sheet.json", sheet); save(name + ".components.json", components)
        summaries[name] = dict(status=components["status"], subjects=components["membership"]["reported_subject_count"]["value"],
            origin_members=len(components["membership"]["origin_members"]), sequence_groups=components["sequence_groups"]["demonstrated_group_count"]["value"],
            origin_samples=components["sample_groups"]["observed_origin_sample_count"]["value"],
            query_coverage=[r["full_query_coverage"]["value"] for r in components["subjects"]],
            member_coverage=[r["full_member_coverage"]["value"] for r in components["subjects"]],
            feature_residue_coverage=[r["feature_paired_residue_coverage"]["value"] for r in components["feature_components"]],
            population_fractions={r["count_unit"]: r["observed_fraction_of_supplied_population"]["value"] for r in components["population_components"]["records"]})
    member_raw = b"gnl|SRA|SRR1.1.2\tSRR1.1.2\t8\tacgunrya\n"
    for name, contents in (("synthetic_runinfo.csv", RUNINFO), ("synthetic_gbseq.xml", GBSEQ), ("synthetic_member_sequences.tsv", member_raw)):
        (destination / name).write_bytes(contents)
        inventory.append(dict(file=name, sha256=hashlib.sha256(contents).hexdigest(), size_bytes=len(contents)))
    save("synthetic_runinfo.parsed.json", parse_ncbi_sra_runinfo(RUNINFO, source_ref="synthetic:runinfo", source_version=None))
    save("synthetic_gbseq.parsed.json", parse_ncbi_gbseq_vdb_metadata(GBSEQ, source_ref="synthetic:gbseq", source_version="synthetic"))
    save("synthetic_member_sequences.parsed.json", parse_blast_vdb_member_sequences(member_raw,
        source_ref="synthetic:member-sequences", source_version="synthetic", extraction_context=extraction_context()))
    values, parsed, identifier = reference_binding_fixture()
    parent = binding(parsed["records"][0], "member", entity("member", dataset="D0", member=identifier), member=0)
    child = binding(parsed["records"][2], "cds", entity("feature", dataset="D0", member=identifier,
        feature=parsed["records"][2]["source_entity"]["feature_identifier"]), parent="member")
    arguments = dict(parsed_results=[parsed], dataset_records=values["dataset_records"],
        member_bindings=values["member_bindings"], query_binding=values["query_binding"], bindings=[child, parent])
    save("synthetic_gbseq.binding_inputs.json", arguments)
    save("synthetic_gbseq.binding_result.json", bind_blast_vdb_metadata(**arguments))
    save("SUMMARY.json", summaries)
    save("MANIFEST.json", dict(verification_class="synthetic native-format inputs and function-generated outputs; no native VDB execution", files=deepcopy(inventory)))
    print(json.dumps(summaries, indent=2))


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        worker(Path(sys.argv[2])); return
    directory = PACKET / (sys.argv[1] if len(sys.argv) > 1 else "example_export_001")
    directory.mkdir()
    destination = directory / "examples"; destination.mkdir()
    command = [str(ROOT / ".venv/bin/python"), str(Path(__file__).resolve()), "--worker", str(destination)]
    from run_check import hashes
    before = hashes()
    result = run_local_job(command, cwd=directory, policy=LocalJobPolicy(20*1024**3, 4*1024**3),
        env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
    (directory / "receipt.json").write_text(json.dumps(dict(command=command, returncode=result.returncode,
        metadata=result.metadata, stdout_path=str(result.stdout_path), stderr_path=str(result.stderr_path),
        source_sha256_before=before, source_sha256_after=hashes()), indent=2) + "\n")
    print(result.stdout_path.read_text()); print(result.stderr_path.read_text())
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
