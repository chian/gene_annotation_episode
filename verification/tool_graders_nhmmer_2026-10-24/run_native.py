"""Reproduce tiny synthetic-input, real HMMER 3.4 verification artifacts.

Every command uses the existing 20 GiB RAM / 4 GiB scratch bounded runner,
without a wall-time budget. This script is not imported by pure graders.
"""
from pathlib import Path
import hashlib
import json
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


def main():
    directory = Path(__file__).resolve().parent
    binaries = ROOT / "resources/software/infernal-1.1.5/hmmer/src"
    policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3)
    rng = random.Random(20261024)
    query = "".join(rng.choices("ACGT", k=100))
    rev = query.translate(str.maketrans("ACGT", "TGCA"))[::-1]
    targets = {"forward": "ACGCTAGCAT" + query + "GACTAGCATG",
               "reverse": "AGTCAGTCAG" + rev + "TCAGTCAGTC",
               "gapped": "ACTGACTGAC" + query[:40] + "GTA" + query[40:70] + query[72:] + "TCGATCGATC"}
    data = directory / "inputs"
    data.mkdir(exist_ok=True)
    (data / "query.fa").write_text(">query\n" + query + "\n")
    (data / "model.sto").write_text("# STOCKHOLM 1.0\n#=GF ID model\n"
        + "\n".join(name + " " + query for name in ("one", "two", "three")) + "\n//\n")
    (data / "targets.fa").write_text("".join(">" + key + "\n" + seq + "\n" for key, seq in targets.items()))
    receipts = []

    def run(label, program, arguments):
        work = directory / label
        work.mkdir(exist_ok=True)
        command = [str(binaries / program), *map(str, arguments)]
        result = run_local_job(command, cwd=work, policy=policy,
            stdout_path=work / "stdout.txt", stderr_path=work / "stderr.txt")
        receipt = {"fixture_kind": "synthetic_sequences_real_native_execution", "command": command,
            "binary_sha256": hashlib.sha256((binaries / program).read_bytes()).hexdigest(),
            "returncode": result.returncode, "metadata": result.metadata}
        (work / "receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
        receipts.append({"label": label, "program": program, "returncode": result.returncode})
        if result.returncode:
            raise RuntimeError("native_fixture_failed:" + label)

    run("prepare_build", "hmmbuild", ["--dna", "--cpu", "1", data / "model.hmm", data / "model.sto"])
    run("prepare_press", "hmmpress", ["-f", data / "model.hmm"])
    for label, query_file, mode, extra in [
        ("nhmmer_sequence", "query.fa", "single_sequence", []),
        ("nhmmer_profile", "model.hmm", "profile", []),
        ("nhmmer_msa", "model.sto", "msa", []),
        ("nhmmer_z_watson", "model.hmm", "profile", ["-Z", "0.1", "--watson"]),
        ("nhmmer_z_both", "model.hmm", "profile", ["-Z", "0.1"]),
    ]:
        run(label, "nhmmer", ["--cpu", "1", "--notextw", "--tblout", directory / label / "hits.tbl",
            *extra, data / query_file, data / "targets.fa"])
        context = {"query": {"name": "query" if query_file == "query.fa" else "model",
            "kind": "nucleotide_sequence" if mode == "single_sequence" else mode,
            "alphabet": "DNA", "length": 100}, "native_parameters": {"query_construction_mode": mode,
            "argv": extra}, "targets": [{"name": key, "kind": "nucleotide_sequence", "length": len(seq),
            "sequence": seq, "alphabet": "DNA"} for key, seq in targets.items()],
            "acquisition": {"output_complete": True, "hit_population_complete": True}}
        (directory / label / "inputs.json").write_text(json.dumps(context, indent=2) + "\n")
    run("nhmmscan", "nhmmscan", ["--cpu", "1", "--notextw", "--tblout", directory / "nhmmscan/hits.tbl",
        data / "model.hmm", data / "targets.fa"])
    (directory / "nhmmscan/inputs.json").write_text(json.dumps({"targets": [{"name": "model", "kind": "profile",
        "length": 100, "alphabet": "DNA"}], "native_parameters": {"argv": []},
        "acquisition": {"output_complete": True, "hit_population_complete": True}}, indent=2) + "\n")
    (directory / "native_runs.json").write_text(json.dumps({"policy": policy.to_dict(), "runs": receipts}, indent=2) + "\n")
    print(json.dumps(receipts))


if __name__ == "__main__":
    main()
