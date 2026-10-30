"""Tiny actual HMMER executions through the existing bounded local runner.

Usage: .venv/bin/python verification/.../run_native.py PROGRAM
Input sequences are synthetic fixtures; algorithm outputs are real. This does
not exercise episode communication. Existing attempts replay their sealed data.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.hmmer_graders import grade_hmmer_native_artifacts
from gene_annotation_episode.hmmer_search_grader import calculate_hmmer_search_scores
from gene_annotation_episode.nhmmer_grader import calculate_nhmmer_scores
from gene_annotation_episode.hmmalign_grader import calculate_hmmalign_scores
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
from gene_annotation_episode.native_hmmer_contracts import (
    native_hmmer_digest, output_contract, requested_job_from_native,
)
from gene_annotation_episode.native_hmmer_driver import run_native_hmmer


DIRECTORY = Path(__file__).resolve().parent
BIN = ROOT / "resources/software/infernal-1.1.5/hmmer/src"
PROTEIN = ROOT / "verification/tool_graders_hmmer_search_2026-10-24/native"
NUCLEOTIDE = ROOT / "verification/tool_graders_nhmmer_2026-10-24/inputs"
ALIGNMENT = ROOT / "verification/tool_graders_hmmalign_2026-10-24"
POLICY = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n")


def fasta(path, kind, alphabet):
    rows = []
    for line in path.read_text().splitlines():
        if line.startswith(">"):
            rows.append({"name": line[1:].split()[0], "accession": None, "sequence": "", "kind": kind, "alphabet": alphabet})
        elif line.strip():
            rows[-1]["sequence"] += line.strip()
    for row in rows:
        row["length"] = len(row["sequence"])
    return rows


def profile(path, alphabet):
    text = path.read_text()
    return {"name": re.search(r"^NAME\s+(\S+)", text, re.M)[1], "accession": None,
            "kind": "profile", "alphabet": alphabet, "length": int(re.search(r"^LENG\s+(\d+)", text, re.M)[1])}


def operand(role, path, fmt):
    return {"role": role, "path": str(path), "format": fmt, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size_bytes": path.stat().st_size, "artifact_ref": "fixture:sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()}


def make_job(program, mode, variant):
    options = [] if program == "hmmalign" else ["--cpu", "1", "--notextw"]
    operands, metadata = [], {}
    if program in {"hmmscan", "nhmmscan"}:
        base = PROTEIN if program == "hmmscan" else NUCLEOTIDE
        operands = [operand("profile_database", base / "model.hmm", "hmmer3_ascii"),
                    operand("query_sequence", base / ("query.fa" if program == "hmmscan" else "targets.fa"), "fasta")]
        operands += [operand("profile_database_"+suffix, base / ("model.hmm."+suffix), "hmmer_"+suffix)
                     for suffix in ("h3f", "h3i", "h3m", "h3p")]
        alphabet, kind = ("protein", "protein_sequence") if program == "hmmscan" else ("DNA", "nucleotide_sequence")
        metadata = {"targets": [profile(base / "model.hmm", alphabet)]}
        if program == "hmmscan":
            metadata["query"] = fasta(base / "query.fa", kind, alphabet)[0]
    elif program in {"hmmsearch", "jackhmmer"}:
        role, name, fmt = (("query_profile", "model.hmm", "hmmer3_ascii") if program == "hmmsearch"
                           else ("query_sequence", "query.fa", "fasta"))
        operands = [operand(role, PROTEIN / name, fmt), operand("sequence_database", PROTEIN / "targets.fa", "fasta")]
        metadata = {"query": profile(PROTEIN / name, "protein") if fmt == "hmmer3_ascii" else fasta(PROTEIN / name, "protein_sequence", "protein")[0],
                    "targets": fasta(PROTEIN / "targets.fa", "protein_sequence", "protein")}
        if program == "jackhmmer":
            options += ["-N", "2"]
    elif program == "nhmmer":
        role, name, fmt = {"sequence": ("query_sequence", "query.fa", "fasta"),
                           "profile": ("query_profile", "model.hmm", "hmmer3_ascii"),
                           "alignment": ("query_alignment", "model.sto", "stockholm")}[mode]
        operands = [operand(role, NUCLEOTIDE / name, fmt), operand("sequence_database", NUCLEOTIDE / "targets.fa", "fasta")]
        metadata = {"query": fasta(NUCLEOTIDE / name, "nucleotide_sequence", "DNA")[0] if mode == "sequence" else
                            {**profile(NUCLEOTIDE / "model.hmm", "DNA"), "kind": "msa" if mode == "alignment" else "profile"},
                    "targets": fasta(NUCLEOTIDE / "targets.fa", "nucleotide_sequence", "DNA"),
                    "native_parameters": {"query_construction_mode": {"sequence": "single_sequence", "profile": "profile", "alignment": "msa"}[mode]}}
        if variant == "watson":
            options += ["-Z", "0.1", "--watson"]
    else:
        operands = [operand("profile", ALIGNMENT / "native/profile.hmm", "hmmer3_ascii"),
                    operand("sequences", ALIGNMENT / "native/sequences.fa", "fasta")]
        metadata = json.loads((ALIGNMENT / "saved" / variant / "inputs.json").read_text())
        if variant == "trim":
            options += ["--trim"]
        if variant == "mapali":
            operands.append(operand("mapali", ALIGNMENT / "native/seed.sto", "stockholm"))
    required, optional = output_contract(program, mode)
    outputs = [{"role": role, "format": fmt, "relative_path": "outputs/"+role} for role, fmt in required.items()]
    for role in optional:
        outputs.append({"role": role, "format": optional[role], "relative_path": "outputs/"+role})
    if variant == "empty":
        options += ["-T", "1000000", "--domT", "1000000", "--incT", "1000000", "--incdomT", "1000000"]
    metadata["acquisition"] = {"output_complete": True, "hit_population_complete": True}
    metadata.setdefault("native_parameters", {})["argv"] = options
    return {"version": "native_hmmer_job_v1", "program": program, "mode": mode,
            "software": {"executable": str(BIN/program), "sha256": hashlib.sha256((BIN/program).read_bytes()).hexdigest(), "engine_version": "3.4"},
            "environment": {}, "operands": operands, "operand_bindings": [], "options": options, "outputs": outputs,
            "metadata": metadata, "grading_parameters": {}}


def execute(program, mode, variant):
    label = program + "_" + mode + "_" + variant
    work = DIRECTORY / "runs" / label
    work.mkdir(parents=True, exist_ok=True)
    job = make_job(program, mode, variant)
    request = requested_job_from_native(job)
    plan = {"version": "native_hmmer_run_plan_v1", "identity": {"run_id": "producer-native-verification-2026-10-24",
            "episode_id": "no-episode-standalone-verification", "resource_id": "local", "execution_id": label,
            "attempt_id": "original", "operation_key": label, "requested_job_sha256": native_hmmer_digest(request)},
            "requested_job": request, "attempt_directory": str(work/"attempt"), "policy": POLICY.to_dict()}
    plan_path = work / "plan.json"
    if plan_path.exists():
        assert json.loads(plan_path.read_text()) == plan
        bundle = run_native_hmmer(plan)
    else:
        write(plan_path, plan)
        command = [sys.executable, "-m", "gene_annotation_episode.native_hmmer_driver", str(plan_path)]
        result = run_local_job(command, cwd=work, policy=POLICY, stdout_path=work/"producer.stdout",
                               stderr_path=work/"producer.stderr", env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
        write(work/"runner_receipt.json", {"fixture_kind": "synthetic_inputs_real_native_execution",
            "command": command, "returncode": result.returncode, "metadata": result.metadata})
        bundle = json.loads((work/"attempt/bundle.json").read_text())
    assert bundle["returncode"] == 0, bundle["failures"]
    assert bundle["failures"] == [], bundle["failures"]
    artifacts, refs, checkpoints = {}, {}, []
    for artifact in bundle["artifacts"]:
        role = artifact["role"]
        text = (work/"attempt"/artifact["relative_path"]).read_text()
        ref = "fixture:sha256:" + artifact["sha256"]
        if role in {"checkpoint_hmm", "checkpoint_msa"}:
            checkpoints.append({"role": {"checkpoint_hmm": "chkhmm", "checkpoint_msa": "chkali"}[role],
                                "text": text, "artifact_ref": ref})
        elif role in {"stdout", "tblout", "domtblout", "included_msa", "stockholm"}:
            artifacts[role], refs[role] = text, ref
    if program == "hmmalign":
        artifacts = {"stockholm": artifacts["stockholm"]}
        refs = {"stockholm": refs["stockholm"]}
    if program.startswith("nhmm"):
        artifacts = {k:v for k,v in artifacts.items() if k in {"stdout", "tblout"}}
        refs = {k:v for k,v in refs.items() if k in artifacts}
    graded = grade_hmmer_native_artifacts(program=program, artifacts=artifacts, artifact_refs=refs,
                engine_version="3.4", inputs=job["metadata"], parameters={}, checkpoints=checkpoints)
    write(work/"sheet.json", graded["sheet"])
    write(work/"scores.json", graded["scores"])
    calculator = (calculate_hmmalign_scores if program == "hmmalign" else calculate_nhmmer_scores
                  if program.startswith("nhmm") else calculate_hmmer_search_scores)
    assert calculator(json.loads((work/"sheet.json").read_text()), parameters={}) == graded["scores"]
    saved_bundle = (work/"attempt/bundle.json").read_bytes()
    assert run_native_hmmer(plan) == bundle
    assert (work/"attempt/bundle.json").read_bytes() == saved_bundle
    family = "sequences" if program == "hmmalign" else "loci" if program.startswith("nhmm") else "domains"
    rows = graded["scores"][family]
    example = {"label": label, "program": program, "mode": mode, "variant": variant, "native_returncode": 0,
               "artifact_count": len(bundle["artifacts"]), "row_family": family, "row_count": len(rows),
               "saved_sheet_recalculation_equal": True, "sealed_replay_equal": True,
               "episode_integration_verified": False, "example_row": rows[0] if rows else None}
    if variant == "empty":
        assert not rows
    else:
        assert rows
    write(work/"example.json", example)
    compact = {k:v for k,v in example.items() if k != "example_row"}
    if rows:
        compact["measurements"] = {k:v for k,v in rows[0].items() if k in {
            "native_domain_score_bits", "model_length", "sequence_length", "model_span_coverage", "sequence_span_coverage",
            "native_score_bits", "model_occupancy", "sequence_match_coverage", "match_state_residues", "original_length"}}
    print(json.dumps(compact, allow_nan=False))


def main():
    program = sys.argv[1]
    if program == "nhmmer":
        for mode in ("sequence", "profile", "alignment"):
            execute(program, mode, "ordinary")
        execute(program, "profile", "watson")
    elif program == "hmmalign":
        for variant in ("ordinary", "trim", "mapali"):
            execute(program, "align", variant)
    else:
        execute(program, "search", "ordinary")
        if program == "hmmsearch":
            execute(program, "search", "empty")


if __name__ == "__main__":
    main()
