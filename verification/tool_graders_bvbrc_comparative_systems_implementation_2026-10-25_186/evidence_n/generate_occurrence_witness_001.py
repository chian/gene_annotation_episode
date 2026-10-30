"""Additional offline, source-executed synthetic family omission witness.

This evidence generator is not imported by production or the test suite.
"""
from pathlib import Path
import contextlib
import hashlib
import json
import socket
import sys
import types

HERE = Path(__file__).resolve().parent
CONTRACT = HERE.parent.parent / "tool_graders_bvbrc_comparative_systems_contract_2026-10-25_185"
sys.dont_write_bytecode = True
sys.path.insert(0, str(CONTRACT / "vendor"))
import numpy as np
import pandas as pd
import requests

network_attempts = []


def blocked(*args, **kwargs):
    network_attempts.append("blocked")
    raise AssertionError("network_or_authentication_forbidden")


socket.create_connection = socket.getaddrinfo = blocked
requests.sessions.Session.request = blocked
stub = types.ModuleType("bvbrc_api")
for name in ("authenticateByEnv", "getGenomeIdsByGenomeGroup", "getFeatureDataFrame", "getSubsystemsDataFrame",
             "getPathwayDataFrame", "getDataForGenomes", "getQueryData", "getQueryDataText"):
    setattr(stub, name, blocked)
sys.modules["bvbrc_api"] = stub
source = CONTRACT / "sources/comparative_systems_service/lib/compare_systems_lib.py"
raw = source.read_bytes()
assert hashlib.sha256(raw).hexdigest() == "052f74f971ee149bf5e07d1f6a6f965f9233d6a8f1795daae7a7b182b47b747f"
producer = types.ModuleType("unchanged_comparative_systems_producer")
exec(compile(raw, str(source), "exec"), producer.__dict__)
columns = ["genome_name", "genome_id", "accession", "patric_id", "refseq_locus_tag", "alt_locus_tag", "feature_id",
           "annotation", "feature_type", "start", "end", "length", "strand", "figfam_id", "plfam_id", "pgfam_id",
           "protein_id", "aa_length", "gene", "product", "go"]


def feature(genome, ident, aa, kind="CDS", pl="PLF_TEST", pg="PGF_TEST"):
    return dict(zip(columns, ["Genome " + genome, genome, "contig", "fig|" + ident, "", "", ident,
        "PATRIC", kind, "1", "300", "300", "+", "", pl, pg, "protein_" + ident, aa, "gene_" + ident, "Synthetic product", ""]))


genomes = ["292462.10", "2.1", "3.1"]
repeated = feature(genomes[0], "repeated-rna", "100", "rRNA")
features = [repeated, dict(repeated), feature(genomes[1], "other", "300"),
            feature(genomes[0], "no-aa", ""), feature(genomes[2], "no-family", "400", pl="", pg="")]
lines = ["\t".join(columns)] + ["\t".join(row[col] for col in columns) for row in features] + ["too\tshort"]
producer.getQueryData = lambda *a, **k: iter(lines)
producer.getQueryDataText = lambda *a, **k: "[]"  # The producer emits literal NOTHING descriptions.
out = HERE.parent / "candidate/tests/fixtures/bvbrc_comparative_systems_native/source_executed_synthetic/occurrence_omissions"
out.mkdir(parents=True, exist_ok=True)
(out / "input_feature_response.tsv").write_text("\n".join(lines) + "\n")
(out / "inputs.json").write_text(json.dumps({"classification": "synthetic_inputs_executed_by_unchanged_public_producer",
    "genome_ids": genomes, "features": features, "extra_short_row": "too\tshort", "family_reference_response": []}, indent=2) + "\n")
genome_data = pd.DataFrame([{"genome_id": g, "genome_name": label} for g, label in zip(genomes, ("A", "B", "C"))])
with (HERE / "occurrence_witness_stdout.log").open("w") as stdout, (HERE / "occurrence_witness_stderr.log").open("w") as stderr:
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        result = producer.run_families(genomes, {}, "occurrence_omissions", str(out), genome_data,
            {g: "None" for g in genomes}, types.SimpleNamespace(headers={"Authorization": "SYNTHETIC_NOT_A_TOKEN"}))
result["genomes"] = sorted(result["genomes"])
(out / "producer_return.json").write_text(json.dumps(result, indent=2) + "\n")
output = json.loads((out / "occurrence_omissions_proteinfams_tables.json").read_text())
assert output["plfam"].splitlines()[1].split("\t")[1:4] == ["3", "2", "NOTHING"]
assert output["plfam"].splitlines()[1].split("\t")[-1] == "020100"
assert network_attempts == []
receipt = {"basis": "source_executed_synthetic", "service_job_submitted": False, "network_attempts": network_attempts,
           "producer_sha256": hashlib.sha256(raw).hexdigest(), "python": sys.version, "numpy": np.__version__, "pandas": pd.__version__,
           "raw_feature_occurrences": 6, "accepted_family_occurrences": 3, "reported_genomes": output["genome_ids"],
           "accepted_non_cds_occurrences": 2, "repeated_feature_id": "repeated-rna", "omitted_no_aa_occurrences": 1,
           "omitted_short_occurrences": 1, "accepted_no_family_genomes": ["3.1"], "missing_family_description_literal": "NOTHING"}
(HERE / "OCCURRENCE_WITNESS_001.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
