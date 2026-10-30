"""Run unchanged pinned producer functions on explicitly synthetic supplied inputs.

This is a contract witness, not a production parser/grader or a BV-BRC run.
All output lives beside this file. Network and authentication are not used.
"""
from pathlib import Path
import contextlib
import copy
import csv
import hashlib
import io
import json
import math
import socket
import sys
import types

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "vendor"))
import numpy as np
import pandas as pd
import requests

network_attempts = []
def blocked(*args, **kwargs):
    network_attempts.append("blocked")
    raise AssertionError("network_or_authentication_forbidden_in_source_witness")

socket.create_connection = blocked
socket.getaddrinfo = blocked
requests.sessions.Session.request = blocked
stub = types.ModuleType("bvbrc_api")
for name in ("authenticateByEnv", "getGenomeIdsByGenomeGroup", "getFeatureDataFrame",
             "getSubsystemsDataFrame", "getPathwayDataFrame", "getDataForGenomes",
             "getQueryData", "getQueryDataText"):
    setattr(stub, name, blocked)
sys.modules["bvbrc_api"] = stub
source = ROOT / "sources/comparative_systems_service/lib/compare_systems_lib.py"
raw = source.read_bytes()
assert hashlib.sha256(raw).hexdigest() == "052f74f971ee149bf5e07d1f6a6f965f9233d6a8f1795daae7a7b182b47b747f"
producer = types.ModuleType("pinned_comparative_systems_producer")
exec(compile(raw, str(source), "exec"), producer.__dict__)
session = types.SimpleNamespace(headers={"Authorization": "SYNTHETIC_NOT_A_TOKEN"})
columns = ["genome_name", "genome_id", "accession", "patric_id", "refseq_locus_tag",
           "alt_locus_tag", "feature_id", "annotation", "feature_type", "start", "end",
           "length", "strand", "figfam_id", "plfam_id", "pgfam_id", "protein_id",
           "aa_length", "gene", "product", "go"]

def feature(genome, index, aa=100, pl="PLF_TEST", pg="PGF_TEST"):
    return dict(zip(columns, ["Genome " + genome, genome, "contig", "fig|" + index,
        "", "", index, "PATRIC", "CDS", "1", "300", "300", "+", "", pl, pg,
        "protein_" + index, str(aa), "gene_" + index, "Synthetic product", ""]))

def pathway(genome, index, ec):
    return {"id": "pw_" + index, "annotation": "PATRIC", "ec_description": "Synthetic EC",
        "ec_number": ec, "feature_id": index, "genome_id": genome,
        "pathway_class": "Synthetic class", "pathway_id": "P_TEST", "pathway_name": "Synthetic pathway",
        "patric_id": "fig|" + index, "product": "Synthetic product"}

def subsystem(genome, index, role, active="active"):
    return {"id": "ss_" + index, "active": active, "class": "Synthetic class",
        "feature_id": index, "gene": "gene_" + index, "genome_id": genome,
        "genome_name": "Genome " + genome, "product": "Synthetic product",
        "role_id": role, "role_name": "Synthetic role " + role, "subclass": "Synthetic subclass",
        "subsystem_id": "S_TEST", "subsystem_name": "Synthetic subsystem", "superclass": "synthetic",
        "patric_id": "fig|" + index}

def records_tsv(rows):
    return "\n".join(["\t".join(columns)] + ["\t".join(str(row[col]) for col in columns) for row in rows])

def rows(text):
    return list(csv.DictReader(io.StringIO(text), delimiter="\t"))

def case(name, genomes, feature_rows, pathway_rows=None, subsystem_rows=None, families=False):
    out = ROOT / "source_executed_synthetic" / name
    out.mkdir(parents=True, exist_ok=True)
    inputs = {"classification": "synthetic_inputs_executed_by_unchanged_public_producer",
        "genome_ids": genomes, "features": feature_rows, "pathway_response": pathway_rows,
        "subsystem_response": subsystem_rows}
    (out / "inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    feature_df = pd.DataFrame(feature_rows, columns=columns)
    feature_df["plfam_index"] = feature_df["plfam_id"]
    feature_df["pgfam_index"] = feature_df["pgfam_id"]
    genome_df = pd.DataFrame([{"genome_id": g, "genome_name": "Genome " + g} for g in genomes])
    query_dict = {"feature": feature_df}
    calls = []
    def get_text(base, query, headers, **kwargs):
        calls.append({"base": base, "query": query, "accept": headers["accept"]})
        if "protein_family_ref" in base:
            return json.dumps([{"family_id": x, "family_product": "Synthetic family"}
                               for x in ("PLF_TEST", "PGF_TEST")])
        selected = query.split("in(genome_id,(", 1)[1].split("))", 1)[0].split(",")
        supplied = pathway_rows if "/pathway/" in base else subsystem_rows
        return json.dumps([r for r in supplied if r["genome_id"] in selected])
    def get_lines(base, query, headers):
        calls.append({"base": base, "query": query, "accept": headers["accept"]})
        selected = query.split("in(genome_id,(", 1)[1].split("))", 1)[0].split(",")
        return iter(records_tsv([r for r in feature_rows if r["genome_id"] in selected]).splitlines())
    producer.getQueryDataText = get_text
    producer.getQueryData = get_lines
    results = {}
    with (out / "producer_stdout.txt").open("w") as stdout, (out / "producer_stderr.txt").open("w") as stderr:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            for kind, supplied, fn in [("pathways", pathway_rows, producer.run_pathways),
                                      ("subsystems", subsystem_rows, producer.run_subsystems)]:
                if supplied is not None:
                    try:
                        results[kind] = fn(genomes, copy.deepcopy(query_dict), name, str(out), genome_df.copy(), session)
                    except Exception as error:
                        results[kind] = {"exception": type(error).__name__, "message": str(error)}
            if families:
                try:
                    result = producer.run_families(genomes, copy.deepcopy(query_dict), name, str(out),
                        genome_df.copy(), {g: "None" for g in genomes}, session)
                    results["families"] = {**result, "genomes": sorted(result["genomes"])}
                except Exception as error:
                    results["families"] = {"exception": type(error).__name__, "message": str(error)}
    (out / "producer_return.json").write_text(json.dumps(results, indent=2) + "\n")
    (out / "synthetic_query_calls.json").write_text(json.dumps(calls, indent=2) + "\n")
    return out, results

gids = ["1.1", "2.1", "3.1"]
features = [feature("3.1", "lost"), feature("1.1", "f1"), feature("1.1", "f2"),
            feature("2.1", "f3"), feature("1.1", "f4")]
pws = [pathway("3.1", "lost", "3.3.3.3"), pathway("1.1", "f1", "1.1.1.1"),
       pathway("1.1", "f2", "2.2.2.2"), pathway("2.1", "f3", "1.1.1.1"),
       pathway("1.1", "f4", "1.1.1.1")]
sss = [subsystem("3.1", "lost", "r3"), subsystem("1.1", "f1", "r1"),
       subsystem("1.1", "f2", "r2", "likely"), subsystem("2.1", "f3", "r1", "likely"),
       subsystem("1.1", "f4", "r1")]
out, result = case("discard_and_dependence", gids, features, pws + [pws[-1]], sss + [sss[-1]])
pw = json.loads((out / "discard_and_dependence_pathways_tables.json").read_text())
ss = json.loads((out / "discard_and_dependence_subsystems_tables.json").read_text())
pw_row = rows(pw["pathway"])[0]
ss_row = rows(ss["subsystems"])[0]
assert set(pw["genome_ids"]) == set(ss["genome_ids"]) == {"1.1", "2.1"}
assert [int(pw_row[k]) for k in ("gene_count", "ec_count", "genome_ec")] == [4, 2, 3]
assert float(pw_row["ec_conservation"]) == float(ss_row["role_conservation"]) == 75.0
assert float(pw_row["gene_conservation"]) == float(ss_row["gene_conservation"]) == 1.0
assert float(ss_row["prop_active"]) == 1.0
variant_lines = (out / "discard_and_dependence_subsystems_variant_mtx.tsv").read_text().splitlines()
assert len(variant_lines[1].split("\t")) == 9 and len(variant_lines[2].split("\t")) == 10
assert variant_lines[2].split("\t")[4:8] == ["3", "2", "0", "0"]

fam_features = [feature("1.1", "a", 100), feature("1.1", "b", 200),
                feature("2.1", "c", 300), feature("3.1", "d", 400, "", "")]
out, result = case("families", gids, fam_features, families=True)
family = json.loads((out / "families_proteinfams_tables.json").read_text())
family_row = rows(family["plfam"])[0]
assert family_row["genomes"] == "020100"
assert float(family_row["aa_length_mean"]) == 200.0
assert math.isclose(float(family_row["aa_length_std"]), math.sqrt(20000 / 3))
for count in (255, 256):
    fs = [feature("1.1", "repeat", 100)] * count + [feature("2.1", "other", 100)]
    out, result = case("hex_" + str(count), gids[:2], fs, families=True)
    data = json.loads((out / ("hex_" + str(count) + "_proteinfams_tables.json")).read_text())
    row = rows(data["plfam"])[0]
    assert row["genomes"] == ("ff01" if count == 255 else "10001")
    assert int(row["feature_count"]) == count + 1

out, result = case("empty_json_responses", gids, features, [], [])
assert result == {"pathways": {"success": False}, "subsystems": {"success": False}}
out, result = case("one_json_record", ["3.1"], features[:1], pws[:1], sss[:1])
assert result["pathways"] == {"genomes": [], "success": True}
assert result["subsystems"] == {"genomes": [], "success": True}
assert json.loads((out / "one_json_record_subsystems_tables.json").read_text())["subsystems"] == "\n"
out, result = case("empty_family_rows", gids, [], families=True)
assert result["families"]["exception"] == "ValueError"

many = [f"{i}.1" for i in range(1, 22)]
many_features = [feature(g, "f" + str(i)) for i, g in enumerate(many)]
many_pw = [pathway(g, "f" + str(i), "1.1.1.1") for i, g in enumerate(many)]
many_ss = [subsystem(g, "f" + str(i), "r1") for i, g in enumerate(many)]
out, result = case("two_chunks", many, many_features, many_pw, many_ss)
assert len(result["pathways"]["genomes"]) == len(result["subsystems"]["genomes"]) == 19
assert set(many) - set(result["pathways"]["genomes"]) == {"1.1", "21.1"}
assert network_attempts == []

summary = {"classification": "unchanged_public_producer_executed_on_synthetic_supplied_data",
    "producer_sha256": hashlib.sha256(raw).hexdigest(), "production_grader_executed": False,
    "service_job_submitted": False, "network_attempts": network_attempts,
    "environment": {"python": sys.version, "pandas": pd.__version__, "numpy": np.__version__},
    "cases": 8, "assertions_passed": True,
    "findings": {"pathway_native": pw_row, "subsystem_native": ss_row, "family_native": family_row,
        "variant_header_columns": 9, "variant_data_columns": 10,
        "two_chunk_input_records": 21, "two_chunk_retained_records": 19,
        "overflow_hex_counts": "10001", "overflow_expected_fixed_width": 4,
        "single_json_record_returns_success_with_empty_tables": True}}
(ROOT / "SOURCE_WITNESS_RESULTS_001.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
