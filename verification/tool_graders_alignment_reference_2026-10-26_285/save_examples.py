"""Retain filled examples, then recalculate saved sheets with I/O disabled."""
from copy import deepcopy
import builtins
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import socket
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n")


def child(directory):
    from gene_annotation_episode.alignment_site_calculators import calculate_reference_site_components
    from gene_annotation_episode import sequence_ops
    fixtures = runpy.run_path(str(ROOT/"tests/test_alignment_site_graders.py"))
    synthetic = {"biopython_gapped": fixtures["bio"](), "phmmer_compatibility": fixtures["phmmer"](),
        "paf_hand": fixtures["minimap"](),
        "paf_reverse_quality": fixtures["minimap"](
            fixtures["paf"]("q\t4\t0\t4\t-\tr\t4\t0\t4\t4\t4\t255\tcg:Z:4M\tcs:Z:=ACGT"),
            "ACGT", "ACGT", [0, 3], quality="!I?5", quality_encoding="phred33"),
        "paf_skip": fixtures["minimap"](
            fixtures["paf"]("q\t4\t0\t4\t+\tr\t7\t0\t7\t4\t4\t0\tcg:Z:2M3N2M"), "ACGT", "ACNNNGT"),
        "biopython_no_alignment": fixtures["bio"]({"aligned": False, "mode": "local", "matrix": "synthetic",
            "query_length": 10, "reference_length": 12}),
        "paf_wrong_operand": fixtures["minimap"](query="AGTGGTA")}
    examples = [(name, "explicit_synthetic_native_input", sheet) for name, sheet in synthetic.items()]
    input_hashes = {}
    for preset in fixtures["PRESETS"]:
        native_directory = fixtures["NATIVE"]/("native_"+preset.replace(":", "_"))
        for name in ("queries.fasta", "references.fasta", "mappings.paf", "receipt.json"):
            path = native_directory/name
            input_hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        for sheet in fixtures["retained_native_sheets"](preset):
            name = preset.replace(":", "_")+"__"+sheet["native_input"]["native_row"]["query_name"]
            examples.append((name, "retained_real_minimap2_output_on_synthetic_sequences", sheet))
    filled = directory/"filled"
    filled.mkdir()
    manifest = []
    for name, evidence_class, sheet in examples:
        scores = calculate_reference_site_components(sheet)
        write(filled/(name+".sheet.json"), sheet)
        write(filled/(name+".components.json"), scores)
        manifest.append({"name": name, "evidence_class": evidence_class, "summary": scores["summary"]})
    def forbidden(*args, **kwargs):
        raise AssertionError("saved-sheet calculation attempted external work")
    checked = []
    for row in manifest:
        name = row["name"]
        sheet = json.loads((filled/(name+".sheet.json")).read_text())
        expected = json.loads((filled/(name+".components.json")).read_text())
        before = deepcopy(sheet)
        with patch.object(builtins, "open", forbidden), patch.object(io, "open", forbidden), \
             patch.object(socket, "socket", forbidden), patch.object(socket, "create_connection", forbidden), \
             patch.object(subprocess, "Popen", forbidden), patch.object(subprocess, "run", forbidden), \
             patch.object(sequence_ops, "align_pair", forbidden):
            calculated = calculate_reference_site_components(sheet)
            assert calculated == expected and sheet == before
        checked.append(name)
    write(directory/"manifest.json", manifest)
    write(directory/"retained_input_hashes.json", input_hashes)
    write(directory/"recalculation_report.json", {"checked": checked, "count": len(checked),
        "file_network_subprocess_alignment_calls_blocked_during_calculation": True,
        "saved_sheets_unchanged": True, "fresh_native_execution": False})
    print(json.dumps({"filled_examples": len(manifest), "retained_native_placements": 18,
                      "saved_sheet_recalculations": len(checked)}))
    for row in manifest:
        summary = row["summary"]
        print(json.dumps({"example": row["name"], **{key: summary[key] for key in (
            "paired_positions", "identical_positions", "substituted_positions", "query_gap_positions",
            "reference_skip_positions", "inserted_query_positions", "selected_paired_identity", "selected_alignment_identity")}}))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "child":
        child(Path(sys.argv[2]))
    else:
        directory = Path(__file__).resolve().parent/"examples_001"
        directory.mkdir()
        policy = LocalJobPolicy(memory_bytes=20*1024**3, scratch_bytes=4*1024**3)
        command = [str(ROOT/".venv/bin/python"), str(Path(__file__).resolve()), "child", str(directory)]
        result = run_local_job(command, cwd=directory, policy=policy,
            stdout_path=directory/"stdout.log", stderr_path=directory/"stderr.log",
            env={**os.environ, "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
        write(directory/"receipt.json", {"command": command, "policy": policy.to_dict(),
            "returncode": result.returncode, "metadata": result.metadata})
        print(json.dumps({"returncode": result.returncode, "stdout": str(result.stdout_path)}))
        print(result.stdout_path.read_text())
        print(result.stderr_path.read_text())
