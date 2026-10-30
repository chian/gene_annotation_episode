"""Explicit small synthetic sequences processed by real pinned minimap2 2.31.

This is verification only. Pure readers/calculators do not invoke this script.
Every native command uses the existing bounded runner (20 GiB RAM, 4 GiB
scratch, no wall-time budget), preserving command receipts and full output.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
from gene_annotation_episode.minimap2_grading_inputs import PRESETS, parse_minimap2_paf_row
from gene_annotation_episode.minimap2_grader import grade_minimap2_placement, calculate_minimap2_query_scores


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n")


def main():
    directory = Path(__file__).resolve().parent
    executable = ROOT/"resources/software/minimap2-2.31/source/minimap2-2.31/minimap2"
    policy = LocalJobPolicy(memory_bytes=20*1024**3, scratch_bytes=4*1024**3)
    rng = random.Random(20261024)
    reference = "".join(rng.choices("ACGT", k=3200))
    # Same normalized ambiguity but distinct original IUPAC symbols; plus an
    # ambiguous inserted base. Native output determines the actual alignment.
    reference = reference[:1400]+"R"+reference[1401:]
    query = list(reference[300:2700])
    query[1100] = "Y"
    for i in (200, 600, 1500, 1800):
        query[i] = next(base for base in "ACGT" if base != query[i])
    query = "".join(query)
    query = query[:1700]+"N"+query[1700:]
    query = query[:2100]+query[2103:]
    complement = str.maketrans("ACGTRYSWKMBDHVN", "TGCAYRSWMKVHDBN")
    sequences = {"forward": query, "reverse": query.translate(complement)[::-1],
                 "exact": reference[600:2600]}
    version_dir = directory/"version"
    version_dir.mkdir(exist_ok=True)
    version_command = [str(executable), "--version"]
    version = run_local_job(version_command, cwd=version_dir, policy=policy,
        stdout_path=version_dir/"stdout", stderr_path=version_dir/"stderr")
    write_json(version_dir/"receipt.json", {"command": version_command, "returncode": version.returncode,
                                           "metadata": version.metadata})
    if version.returncode:
        raise RuntimeError("native version query failed")
    native_version = (version_dir/"stdout").read_text().strip()
    summary = {"fixture_kind": "synthetic_sequences_real_minimap2_execution",
        "native_version": native_version, "binary_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "policy": policy.to_dict(), "runs": []}
    for preset in PRESETS:
        run = directory/("native_"+preset.replace(":", "_"))
        run.mkdir(exist_ok=True)
        (run/"references.fasta").write_text(">reference\n"+reference+"\n")
        (run/"queries.fasta").write_text("".join(">"+name+"\n"+seq+"\n" for name, seq in sequences.items()))
        command = [str(executable), "-x", preset, "-c", "--cs=long", "--frag=no", "-t", "1",
                   str(run/"references.fasta"), str(run/"queries.fasta")]
        result = run_local_job(command, cwd=run, policy=policy,
            stdout_path=run/"mappings.paf", stderr_path=run/"mapping.stderr")
        write_json(run/"receipt.json", {"command": command, "returncode": result.returncode,
            "metadata": result.metadata, "query_lengths": {name: len(seq) for name, seq in sequences.items()},
            "reference_length": len(reference)})
        if result.returncode:
            raise RuntimeError("native fixture failed: "+preset)
        groups = {name: [] for name in sequences}
        metrics = []
        with (run/"placements.jsonl").open("w") as output:
            for line in (run/"mappings.paf").read_bytes().splitlines(keepends=True):
                row = parse_minimap2_paf_row(line, native_version=native_version)
                name = row["query_name"]
                graded = grade_minimap2_placement(row, preset=preset, native_version=native_version,
                    query_metadata={"name": name, "length": len(sequences[name]), "sequence": sequences[name]},
                    reference_metadata={"name": "reference", "length": len(reference), "sequence": reference})
                output.write(json.dumps(graded, sort_keys=True, allow_nan=False)+"\n")
                groups[name].append(graded["sheet"])
                fields = ("query_span", "reference_span", "native_matching_bases", "native_block_length",
                    "paired_positions", "inserted_bases", "deleted_bases", "alignment_columns", "cs_equal_positions",
                    "cs_substituted_positions", "native_ambiguity_count", "original_symbol_equal_positions",
                    "original_symbol_substituted_positions", "native_alignment_identity", "query_paired_coverage")
                metrics.append({"query_name": name, "strand": row["strand"], "cigar": row["cigar"],
                    "sheet_status": graded["sheet"]["status"], "issues": graded["sheet"]["issues"],
                    **{field: graded["scores"][field] for field in fields}})
        query_scores = [calculate_minimap2_query_scores(sheets,
            query_metadata={"name": name, "length": len(sequences[name])}, output_complete=True)
            for name, sheets in groups.items()]
        write_json(run/"query_scores.json", query_scores)
        summary["runs"].append({"preset": preset, "returncode": result.returncode,
            "placement_count": len(metrics), "metrics": metrics})
    write_json(directory/"native_summary.json", summary)
    print(json.dumps({"native_version": native_version,
        "runs": [{"preset": row["preset"], "placements": row["placement_count"],
                  "metrics": row["metrics"]} for row in summary["runs"]]}, indent=2))


if __name__ == "__main__":
    main()
