#!/usr/bin/env python3
"""Small CPU-only protein alignment using an existing gentner-ave executor.

--source-root is the gentner-ave repository root, whose src directory must
already be on PYTHONPATH. --run-dir contains target.faa and
reported-references.faa. No package installation or network access is performed.
"""

from __future__ import annotations

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import platform
import socket
import sys
import time
import traceback


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def package_versions():
    versions = {}
    for name in ("academy-py", "pydantic", "biopython"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def make_analysis(run_dir):
    return "\n".join([
        "from pathlib import Path",
        "import json",
        "from Bio import SeqIO",
        "from Bio.Align import PairwiseAligner, substitution_matrices",
        f"run_dir = Path({str(run_dir)!r})",
        "query = SeqIO.read(run_dir / 'target.faa', 'fasta')",
        "references = list(SeqIO.parse(run_dir / 'reported-references.faa', 'fasta'))",
        "if not query.seq or not references:",
        "    raise ValueError('A nonempty query and at least one reference are required')",
        "if any(not reference.seq for reference in references):",
        "    raise ValueError('Empty reference sequence')",
        "aligner = PairwiseAligner(mode='global',",
        "    substitution_matrix=substitution_matrices.load('BLOSUM62'),",
        "    open_gap_score=-10, extend_gap_score=-0.5)",
        "rows = [{'reference_id': reference.id, 'query_length': len(query),",
        "         'reference_length': len(reference),",
        "         'alignment_score': float(aligner.score(str(query.seq), str(reference.seq)))}",
        "        for reference in references]",
        "rows.sort(key=lambda row: (-row['alignment_score'], row['reference_id']))",
        "output = {'query_id': query.id, 'reference_count': len(references),",
        "    'method': {'algorithm': 'pairwise alignment', 'mode': 'global',",
        "        'substitution_matrix': 'BLOSUM62', 'open_gap_score': -10,",
        "        'extend_gap_score': -0.5}, 'comparisons': rows}",
        "(run_dir / 'alignment_scores.json').write_text(",
        "    json.dumps(output, indent=2, allow_nan=False) + '\\n')",
        "print(json.dumps({'reference_count': len(rows), 'top_matches': rows[:3]}))",
        "",
    ])


async def execute(run_dir, source_root, analysis_code, record):
    from academy.exchange import LocalExchangeFactory
    from academy.manager import Manager
    from gentner_ave.execution.agent import AnalysisExecutor

    imported_file = Path(inspect.getfile(AnalysisExecutor)).resolve()
    expected_file = (source_root / "src/gentner_ave/execution/agent.py").resolve()
    record["executor_module"] = str(imported_file)
    if imported_file != expected_file:
        raise RuntimeError(f"Imported executor {imported_file}; expected {expected_file}")

    record["phase"] = "manager_creation"
    pool = ThreadPoolExecutor(max_workers=1)
    manager = None
    try:
        manager = await Manager.from_exchange_factory(
            factory=LocalExchangeFactory(), executors=pool,
        )
        async with manager:
            record["phase"] = "executor_launch"
            handle = await manager.launch(AnalysisExecutor, args=(str(run_dir),))
            record["owned_handle_shutdown"] = "pending"
            try:
                record["phase"] = "analysis_execution"
                result = await handle.run_script("python", analysis_code)
                write_json(run_dir / "executor_result.json", {
                    "receipt_kind": "executor_result", "received": True,
                    "result": result.model_dump(mode="json"),
                })
                record["executor_status"] = result.status
                record["phase"] = "trace_receipt"
                trace = await handle.get_trace()
                write_json(run_dir / "executor_trace.json", {
                    "receipt_kind": "executor_trace", "received": True,
                    "trace": trace.model_dump(mode="json"),
                })
                if result.status != "ok":
                    raise RuntimeError("AnalysisExecutor returned an error; see executor_result.json")
                record["phase"] = "output_receipt"
                output = json.loads((run_dir / "alignment_scores.json").read_text())
                rows = output["comparisons"]
                if len(rows) != record["inputs"]["reported-references.faa"]["fasta_records"]:
                    raise RuntimeError("Output count does not match the reference FASTA record count")
                if output["reference_count"] != len(rows):
                    raise RuntimeError("Output reference count is inconsistent")
                record["completed_comparisons"] = len(rows)
                record["alignment_scores_sha256"] = file_sha256(run_dir / "alignment_scores.json")
            finally:
                try:
                    await manager.shutdown(handle, blocking=True)
                    record["owned_handle_shutdown"] = "completed"
                except BaseException:
                    record["owned_handle_shutdown"] = "failed"
                    raise
    finally:
        # Manager.close owns its executor pool after creation. A factory failure
        # leaves this driver responsible for its otherwise unused pool.
        if manager is None:
            pool.shutdown(wait=True, cancel_futures=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    source_root = args.source_root.expanduser().resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    output_names = ("execution.json", "executor_result.json", "executor_trace.json",
                    "alignment_scores.json", "analysis.py")
    if any((run_dir / name).exists() for name in output_names):
        parser.error("Use a fresh run directory: an output receipt already exists")

    start_clock = time.monotonic()
    record = {
        "schema": "gentner_alignment_smoke_execution_v1",
        "status": "failed", "phase": "input_inspection", "started_utc": utc_now(),
        "hostname": socket.gethostname(), "pbs_job_id": os.environ.get("PBS_JOBID"),
        "python_executable": sys.executable, "python_version": sys.version,
        "platform": platform.platform(), "packages": package_versions(),
        "run_dir": str(run_dir), "source_root": str(source_root),
        "driver_sha256": file_sha256(Path(__file__).resolve()),
        "inputs": {}, "source_sha256": {}, "owned_handle_shutdown": "not_launched",
    }
    exit_code = 1
    try:
        for name in ("target.faa", "reported-references.faa"):
            path = run_dir / name
            data = path.read_bytes()
            record["inputs"][name] = {
                "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                "fasta_records": sum(line.startswith(b">") for line in data.splitlines()),
            }
        if record["inputs"]["target.faa"]["fasta_records"] != 1:
            raise ValueError("target.faa must contain exactly one FASTA record")
        for relative in ("src/gentner_ave/__init__.py",
                         "src/gentner_ave/execution/__init__.py",
                         "src/gentner_ave/execution/agent.py",
                         "src/gentner_ave/execution/handle.py",
                         "src/gentner_ave/execution/results.py",
                         "src/gentner_ave/execution/_pyrepl.py"):
            record["source_sha256"][relative] = file_sha256(source_root / relative)
        analysis_code = make_analysis(run_dir)
        (run_dir / "analysis.py").write_text(analysis_code)
        record["analysis_sha256"] = file_sha256(run_dir / "analysis.py")
        record["phase"] = "executor_import"
        asyncio.run(execute(run_dir, source_root, analysis_code, record))
        record["status"] = "succeeded"
        record["phase"] = "completed"
        exit_code = 0
    except BaseException as exc:
        record["error"] = {"type": type(exc).__name__, "message": str(exc),
                           "traceback": traceback.format_exc()}
        print(record["error"]["traceback"], file=sys.stderr)
    finally:
        record["ended_utc"] = utc_now()
        record["elapsed_seconds"] = time.monotonic() - start_clock
        for filename, kind in (("executor_result.json", "executor_result"),
                               ("executor_trace.json", "executor_trace")):
            if not (run_dir / filename).exists():
                write_json(run_dir / filename, {
                    "receipt_kind": kind, "received": False, "phase": record["phase"],
                    "error": record.get("error"),
                })
        write_json(run_dir / "execution.json", record)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
