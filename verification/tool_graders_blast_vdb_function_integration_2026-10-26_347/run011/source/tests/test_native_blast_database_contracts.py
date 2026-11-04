"""Pure 313 contract oracles. These are synthetic descriptors, not databases."""
from copy import deepcopy
import builtins
import os
from pathlib import Path
import socket
import subprocess

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import native_blast_database_contracts as c


def identity(path):
    return {"path": path, "sha256": "a" * 64, "size_bytes": 12, "artifact_ref": None}


def database(key="target", kind="blast_protein_sequence"):
    prep = {"blast_protein_sequence": "sequence_database", "rps_profile": "rps", "delta_profile": "delta", "vdb": "vdb"}[kind]
    source = {"source_ref": "source_explicit", "pointer": "/preparation"}
    ident = {"namespace": "synthetic", "value": key, "version": None, "release": None, "scope": None,
        "preparation_type": "unknown" if prep == "vdb" else prep, "source": source}
    paths = ["/selected/db/" + key]
    manifest = {"version": "native_blast_prepared_database_manifest_v1", "database_key": key, "kind": kind,
        "identity": ident, "native_paths": paths,
        "files": [{"path": paths[0] + ("/dataset.bin" if kind == "vdb" else ".pin"), "sha256": "b" * 64, "size_bytes": 23}],
        "preparation": {"method": "publisher_package", "preparation_type": prep,
            "software": {"name": "fixture preparation", "version": None, "executable_sha256": None},
            "argv": None, "source": source, "input_manifest": None, "receipt": identity("/selected/" + key + ".receipt")},
        "metadata_manifests": [], "access": {"mode": "prepared_local",
            "offline_configuration": identity("/selected/offline.conf") if kind == "vdb" else None}, "inventory_complete": True}
    return {"database_key": key, "role": "domain" if key == "domain" else "target", "kind": kind,
        "identity": ident, "native_paths": paths, "manifest_file": identity("/selected/" + key + ".manifest"), "manifest": manifest}


def job_for(program="psiblast", query="sequence", fmt="json15"):
    kind = "blast_protein_sequence" if program in {"psiblast", "deltablast"} else (
        "rps_profile" if program in {"rpsblast", "rpstblastn"} else "vdb")
    job = {"version": "native_blast_database_job_v1", "program": program, "mode": "database",
        "software": {"executable": "/selected/bin/" + program, "sha256": "c" * 64, "engine_version": "2.17.0+"},
        "environment": {"EXPLICIT": "selected"}, "inputs": [{"input_key": "query", "role": "query_" + query,
            "format": {"sequence": "fasta", "msa": "clustal", "pssm": "scoremat_asn_text"}[query], **identity("/selected/query")}],
        "query": {"kind": query, "input_key": "query", "msa_master_record_ordinal": None, "ignore_msa_master": None},
        "databases": [database(kind=kind)], "options": [], "outputs": [
            {"output_key": role, "role": role, "path_kind": "file", "relative_path": role + ".txt", "format": "text",
             "fields": [], "delimiter": None, "required": True} for role in ("stdout", "stderr")],
        "metadata_inputs": [], "grading_parameters": {"sequence_database_model": None}}
    job["outputs"].append({"output_key": "report", "role": "primary_report", "path_kind": "file", "relative_path": "report",
        "format": fmt, "fields": [] if fmt == "json15" else ["qseqid", "sseqid", "bitscore", "qstart", "qend"],
        "delimiter": None if fmt == "json15" else "\t", "required": True})
    if program == "deltablast":
        job["databases"].append(database("domain", "delta_profile"))
    return job


def checkpoint(job, role="checkpoint_asn"):
    job["outputs"].append({"output_key": role, "role": role, "path_kind": "prefix", "relative_path": role + "/selected",
        "format": "scoremat_asn_text" if role == "checkpoint_asn" else "ascii_pssm", "fields": [], "delimiter": None, "required": False})
    return job


def compiled(job, **kw):
    return c.compile_native_blast_database_job(job,
        input_paths=kw.get("input_paths", {r["input_key"]: r["path"] for r in job["inputs"]}),
        database_paths=kw.get("database_paths", {r["database_key"]: r["native_paths"] for r in job["databases"]}),
        output_directory=kw.get("output_directory", "."))


def forbid_io(monkeypatch):
    def fail(*a, **kw):
        pytest.fail("pure contract attempted I/O, process or network")
    for obj, name in ((builtins, "open"), (Path, "open"), (Path, "resolve"), (os, "stat"), (os, "listdir"),
                      (subprocess, "run"), (subprocess, "Popen"), (socket, "socket"), (socket, "getaddrinfo")):
        monkeypatch.setattr(obj, name, fail)


@pytest.mark.parametrize("program,query", [(p, q) for p in c.PROGRAMS for q in
    ({"psiblast": ["sequence", "msa", "pssm"], "tblastn_vdb": ["sequence", "pssm"]}.get(p, ["sequence"]))])
@pytest.mark.parametrize("fmt", ["json15", "tabular6", "tabular7"])
def test_exact_compilation_and_all_modes_without_io(monkeypatch, program, query, fmt):
    job = job_for(program, query, fmt)
    job["options"] = ["-evalue", "0.0100", "-num_threads", "0" if "rps" in program else "2", "-soft_masking", "false"]
    if program in {"psiblast", "deltablast"}:
        job["options"] += ["-num_iterations", "0"]
    original = deepcopy(job)
    forbid_io(monkeypatch)
    assert c.validate_native_blast_database_job(job) == job
    result = compiled(job)
    query_flag = {"sequence": "-query", "msa": "-in_msa", "pssm": "-in_pssm"}[query]
    expected = [job["software"]["executable"], *job["options"], query_flag, "/selected/query", "-db", "/selected/db/target"]
    if program == "deltablast":
        expected += ["-rpsdb", "/selected/db/domain"]
    outfmt = "15" if fmt == "json15" else ("6" if fmt == "tabular6" else "7") + " qseqid sseqid bitscore qstart qend"
    assert result["argv"] == [*expected, "-outfmt", outfmt, "-out", "report"]
    assert [r["path"] for r in result["outputs"]] == [r["relative_path"] for r in job["outputs"]]
    request = c.requested_job_from_native_blast_database(job)
    assert c.validate_native_blast_database_requested_job(request) == request
    Draft202012Validator(c.NATIVE_BLAST_DATABASE_REQUESTED_JOB_SCHEMA).validate(request)
    result["outputs"][0]["relative_path"] = "changed"
    request["native_blast_database"]["query"]["input_key"] = "changed"
    assert job == original


@pytest.mark.parametrize("ordinal,ignore,flags", [(None, None, []), (None, False, []), (None, True, ["-ignore_msa_master"]),
    (0, None, ["-msa_master_idx", "1"]), (4, False, ["-msa_master_idx", "5"])])
def test_msa_master_only_selected_flags(ordinal, ignore, flags):
    job = job_for(query="msa")
    job["query"].update(msa_master_record_ordinal=ordinal, ignore_msa_master=ignore)
    assert compiled(job)["argv"][3:3 + len(flags)] == flags
    assert compiled(job)["argv"].count("-msa_master_idx") == (ordinal is not None)
    assert c.validate_native_blast_database_job(job)["query"] == job["query"]


@pytest.mark.parametrize("program,options", [
    ("psiblast", ["-seg", "12 2.2 2.5", "-comp_based_stats", "3", "-matrix", "BLOSUM62", "-num_iterations", "0", "-pseudocount", "-1"]),
    ("deltablast", ["-show_domain_hits", "-domain_inclusion_ethresh", "0.001", "-inclusion_ethresh", "0.02"]),
    ("rpsblast", ["-num_threads", "0", "-mt_mode", "1", "-sum_stats", "true", "-comp_based_stats", "D"]),
    ("rpstblastn", ["-strand", "minus", "-query_gencode", "33", "-ungapped"]),
    ("blastn_vdb", ["-task", "dc-megablast", "-template_type", "coding", "-template_length", "18", "-dust", "20 64 1", "-sra_mode", "2", "-include_filtered_reads"]),
    ("tblastn_vdb", ["-db_gencode", "11", "-max_intron_length", "0", "-sra_mode", "0", "-word_size", "2"]),
])
def test_selected_native_options_preserved(program, options):
    job = job_for(program)
    job["options"] = options
    assert compiled(job)["argv"][1:1 + len(options)] == options


@pytest.mark.parametrize("options,code", [(["-remote"], "forbidden_option"), (["-subject", "file"], "forbidden_option"),
    (["-db", "elsewhere"], "compiler_owned"), (["-outfmt", "6"], "compiler_owned"), (["-phi_pattern", "x"], "forbidden_option"),
    (["-taxidlist", "x"], "forbidden_option"), (["-mystery"], "unsupported_option"), (["-num_threads"], "operand_required"),
    (["-num_threads", "0"], "invalid_option"), (["-evalue", "NaN"], "invalid_option"),
    (["-evalue", "1", "-evalue", "2"], "duplicate_option"), (["-query_loc", "9-1"], "invalid_option"),
    (["-soft_masking", "yes"], "invalid_option"), (["-max_target_seqs", "1", "-num_alignments", "0"], "conflicting"),
    (["-culling_limit", "1", "-best_hit_overhang", "0.2"], "conflicting"), (["-save_each_pssm"], "checkpoint_output"),
    (["-searchsp", str(2**63)], "invalid_option"), (["-dbsize", str(-2**63 - 1)], "invalid_option"),
    (["-matrix", "/path/matrix"], "invalid_option")])
def test_excluded_invalid_duplicate_options_fail(options, code):
    job = job_for()
    job["options"] = options
    with pytest.raises(ValueError, match=code):
        c.validate_native_blast_database_job(job)


def test_realization_custom_layout_and_checkpoint_flags():
    job = checkpoint(checkpoint(job_for(fmt="tabular7")), "checkpoint_ascii")
    job["options"] = ["-save_each_pssm", "-save_pssm_after_last_round"]
    job["outputs"][2]["delimiter"] = "@"
    result = compiled(job, input_paths={"query": "/attempt/inputs/query"}, output_directory="/attempt/results")
    assert result["argv"] == ["/selected/bin/psiblast", *job["options"], "-query", "/attempt/inputs/query", "-db", "/selected/db/target",
        "-outfmt", "7 delim=@ qseqid sseqid bitscore qstart qend", "-out", "/attempt/results/report",
        "-out_pssm", "/attempt/results/checkpoint_asn/selected", "-out_ascii_pssm", "/attempt/results/checkpoint_ascii/selected"]


def test_unknown_metadata_schema_custody_and_closed_descriptor():
    job = job_for()
    job["inputs"].append({"input_key": "meta", "role": "metadata", "format": "json", **identity("/selected/metadata")})
    job["metadata_inputs"] = [{"input_key": "meta", "consumer": "profile", "schema_id": "unregistered-do-not-interpret"},
        {"input_key": "meta", "consumer": "vdb", "schema_id": "another-schema"}]
    assert c.validate_native_blast_database_job(job) == job
    assert "/selected/metadata" not in compiled(job)["argv"]
    bad = deepcopy(job)
    bad["metadata_inputs"].append(deepcopy(bad["metadata_inputs"][0]))
    with pytest.raises(ValueError, match="uniqueItems"):
        c.validate_native_blast_database_job(bad)
    for change in ({"input_key": "query"}, {"consumer": "arbitrary"}, {"schema_id": "bad\0schema"}, {"reader": "invented"}):
        bad = deepcopy(job)
        bad["metadata_inputs"][0].update(change)
        with pytest.raises(ValueError):
            c.validate_native_blast_database_job(bad)


@pytest.mark.parametrize("mutate", [
    lambda j: j.update(mode="pairwise"), lambda j: j["software"].update(sha256="A" * 64),
    lambda j: j["inputs"][0].update(size_bytes=True), lambda j: j["inputs"][0].update(path="/x/../y"),
    lambda j: j["query"].update(msa_master_record_ordinal=0),
    lambda j: j["outputs"][2].update(relative_path="../escape"),
    lambda j: j["outputs"][2].update(relative_path="stdout.txt/child"),
    lambda j: j["outputs"][2].update(output_key="query"),
    lambda j: j["outputs"][2].update(required=False),
    lambda j: j["databases"][0]["manifest"].update(inventory_complete=False),
    lambda j: j["databases"][0]["manifest"].update(database_key="wrong"),
    lambda j: j["grading_parameters"].update(sequence_database_model={"temperature_bits": 0}),
    lambda j: j["grading_parameters"].update(sequence_database_model={"function_priors": {"f": 0}}),
    lambda j: j["grading_parameters"].update(sequence_database_model={"weight": 1}),
    lambda j: j.update(extra="undeclared"),
])
def test_job_relationship_and_finite_type_rejections(mutate):
    job = job_for()
    mutate(job)
    with pytest.raises(ValueError):
        c.validate_native_blast_database_job(job)


@pytest.mark.parametrize("key", sorted(c.RESERVED_ENVIRONMENT))
def test_job_cannot_override_producer_environment(key):
    job = job_for()
    job["environment"][key] = "/elsewhere"
    with pytest.raises(ValueError, match="producer_owned_environment"):
        c.validate_native_blast_database_job(job)


def test_database_selection_and_translated_restrictions():
    for program in c.PROGRAMS[1:]:
        if program == "tblastn_vdb":
            continue
        with pytest.raises(ValueError, match="query_kind"):
            c.validate_native_blast_database_job(job_for(program, "pssm"))
    with pytest.raises(ValueError, match="query_kind"):
        c.validate_native_blast_database_job(job_for("tblastn_vdb", "msa"))
    job = job_for("blastn_vdb")
    job["databases"][0]["manifest"]["access"]["offline_configuration"] = None
    with pytest.raises(ValueError, match="offline_configuration"):
        c.validate_native_blast_database_job(job)
    job = job_for("deltablast")
    assert compiled(job)["argv"].index("-db") < compiled(job)["argv"].index("-rpsdb")
    with pytest.raises(ValueError, match="selected_database_paths"):
        compiled(job, database_paths={"target": ["/wrong"], "domain": ["/selected/db/domain"]})
    job = job_for("blastn_vdb")
    db = job["databases"][0]
    db["native_paths"].append("/selected/db/other")
    db["manifest"]["files"].append({"path": "/selected/db/other/data", "sha256": "d" * 64, "size_bytes": 2})
    assert compiled(job)["argv"][4] == "/selected/db/target /selected/db/other"


def manifest_for():
    return {"version": "native_blast_database_producer_manifest_v1", "module_root": "/deploy",
        "entry_module": "gene_annotation_episode.native_blast_database_driver",
        "python": {"path": "/runtime/python", "sha256": "a" * 64, "size_bytes": 23},
        "package_files": [{"relative_path": "gene_annotation_episode/" + n, "sha256": "b" * 64, "size_bytes": 10}
            for n in ("__init__.py", "native_blast_database_contracts.py", "native_blast_database_driver.py")],
        "runtime_files": [{"path": "/runtime/lib", "sha256": "c" * 64, "size_bytes": 10}]}


def test_producer_manifest_is_pure_defensive_and_closed(monkeypatch):
    manifest = manifest_for()
    forbid_io(monkeypatch)
    result = c.validate_native_blast_database_producer_manifest(manifest, module_root="/deploy", python_executable="/runtime/python")
    result["python"]["size_bytes"] = 99
    assert manifest["python"]["size_bytes"] == 23
    for change in (lambda m: m["package_files"].pop(), lambda m: m["package_files"].append(m["package_files"][0]),
        lambda m: m["package_files"][0].update(relative_path="../escape"),
        lambda m: m["runtime_files"][0].update(path="/deploy/extra"),
        lambda m: m["runtime_files"][0].update(path="/runtime/python"), lambda m: m.update(extra=True),
        lambda m: m["python"].update(size_bytes=True), lambda m: m.update(module_root="/different")):
        bad = deepcopy(manifest)
        change(bad)
        with pytest.raises(ValueError):
            c.validate_native_blast_database_producer_manifest(bad, module_root="/deploy", python_executable="/runtime/python")


def test_original_request_and_paired_compiler_remain_distinct():
    request = c.requested_job_from_native_blast_database(job_for())
    request["argv"][0] = "/replaced"
    with pytest.raises(ValueError, match="compiler_mismatch"):
        c.validate_native_blast_database_requested_job(request)
    from test_native_blast_contracts import job_for as paired_job
    from gene_annotation_episode.native_blast_contracts import compile_native_blast_job
    before = compile_native_blast_job(paired_job())
    compiled(job_for())
    assert compile_native_blast_job(paired_job()) == before
    assert "-subject" in before["argv"] and "-db" not in before["argv"]


def test_finite_json_contract_rejects_cycles_nonfinite_and_non_json_values():
    cyclic = []
    cyclic.append(cyclic)
    for value in (float("nan"), float("inf"), (1, 2), {1: "value"}, cyclic):
        job = job_for()
        job["grading_parameters"]["sequence_database_model"] = value
        with pytest.raises(ValueError, match="finite_json_required"):
            c.validate_native_blast_database_job(job)
