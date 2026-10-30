"""Offline SOURCE-EXECUTED SYNTHETIC probes; no installed program/service execution.

Only exact upstream AST nodes are compiled. External operations are explicit stubs.
Outputs establish producer structure, not a successful scientific job.
"""
from pathlib import Path
import ast
import contextlib
import dataclasses
import hashlib
import io
import json
import logging
import os
import sys
import types

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "synthetic"
OUT.mkdir(exist_ok=True)
RECEIPT = {"identity": "source_executed_synthetic_not_service_artifacts",
           "live_jobs": 0, "native_programs_executed": [], "fragments": [], "checks": {}}


def fragment(path, name, namespace):
    raw = path.read_bytes()
    source = raw.decode()
    node = next(n for n in ast.parse(source).body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name)
    RECEIPT["fragments"].append({"file": str(path.relative_to(ROOT)), "symbol": name,
        "source_sha256": hashlib.sha256(raw).hexdigest(), "start_line": node.lineno,
        "end_line": node.end_lineno,
        "fragment_sha256": hashlib.sha256(ast.get_source_segment(source, node).encode()).hexdigest()})
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


producer = ROOT / "sources/p3_fqutils/lib/fastq_utils.py"
calls = []
native_rows = []


def fake_hostile(cmd, *, check, stdout):
    row = {"synthetic_stub": True, "fastq1_in_path": cmd[cmd.index("--fastq1") + 1]}
    calls.append(cmd)
    native_rows.append(row)
    json.dump([row], stdout)


ns = {"Path": Path, "os": os, "sys": sys, "subprocess": types.SimpleNamespace(run=fake_hostile)}
run_hostile = fragment(producer, "run_hostile", ns)
reads = [{"read1": "libA_R1.fastq", "read2": "libA_R2.fastq"}, {"read1": "libB.fastq"}]
before = json.loads(json.dumps(reads))
saved_cache = os.environ.get("HOSTILE_CACHE_DIR")
try:
    with contextlib.redirect_stderr(io.StringIO()):
        run_hostile(reads, OUT / "overwrite", {}, {})
finally:
    if saved_cache is None:
        os.environ.pop("HOSTILE_CACHE_DIR", None)
    else:
        os.environ["HOSTILE_CACHE_DIR"] = saved_cache
retained = json.loads((OUT / "overwrite/hostile_report.txt").read_text())
assert retained == [native_rows[-1]] and reads == before
RECEIPT["checks"]["hostile_overwrite"] = {"calls": calls, "retained_report": retained,
    "earlier_report_lost": True, "read_operands_unchanged": True}

# Exact nested upstream with-statement: the apparent .gz file is opened in text mode.
tree = ast.parse(producer.read_text())
alignment = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_alignment")
node = next(n for n in ast.walk(alignment) if isinstance(n, ast.With)
            and "unmapped_fq_gz_path.open" in ast.unparse(n.items[0].context_expr))
unmapped = OUT / "synthetic.unmapped.fq.gz"
payload = "@synthetic-read\nACGT\n+\nIIII\n"
def fake_samtools(cmd, *, check, stdout):
    stdout.write(payload)
ns2 = {"unmapped_fq_gz_path": unmapped, "view_threads": 1, "bam_file_all": "SYNTHETIC_NOT_A_BAM",
       "subprocess": types.SimpleNamespace(run=fake_samtools)}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(producer), "exec"), ns2)
raw = unmapped.read_bytes()
assert raw == payload.encode() and not raw.startswith(b"\x1f\x8b")
RECEIPT["fragments"].append({"file": str(producer.relative_to(ROOT)), "symbol": "run_alignment/unmapped_with",
    "source_sha256": hashlib.sha256(producer.read_bytes()).hexdigest(), "start_line": node.lineno,
    "end_line": node.end_lineno,
    "fragment_sha256": hashlib.sha256(ast.get_source_segment(producer.read_text(), node).encode()).hexdigest()})
RECEIPT["checks"]["compression_identity"] = {"filename": unmapped.name, "magic_hex": raw[:4].hex(),
    "content_format": "fastq", "compression": "none", "suffix_disagrees": True,
    "sha256": hashlib.sha256(raw).hexdigest()}

# Native Hostile reports from exact gather_stats_paired and utility functions.
util_path = ROOT / "sources/hostile_1.1.0/src/hostile/util.py"
lib_path = ROOT / "sources/hostile_1.1.0/src/hostile/lib.py"
util_ns = {"Path": Path, "logging": logging}
util = types.SimpleNamespace(**{name: fragment(util_path, name, util_ns)
    for name in ("fastq_path_to_stem", "parse_count_file")})
module = types.ModuleType("synthetic_hostile_110")
sys.modules[module.__name__] = module
module.__dict__.update(Path=Path, dataclass=dataclasses.dataclass, util=util, __version__="1.1.0")
fragment(lib_path, "SampleReport", module.__dict__)
gather = fragment(lib_path, "gather_stats_paired", module.__dict__)
stats_dir = OUT / "hostile_counts"
stats_dir.mkdir(exist_ok=True)
report_rows = []
for label, count_in, count_out in (("nonzero", 8, 6), ("empty", 0, 0)):
    (stats_dir / f"{label}_R1.reads_in.txt").write_text(str(count_in))
    (stats_dir / f"{label}_R1.reads_out.txt").write_text(str(count_out))
    report_rows.extend(gather(False, False, [(Path(f"{label}_R1.fastq"), Path(f"{label}_R2.fastq"))],
        stats_dir, "bowtie2", "SYNTHETIC_REFERENCE_ID_NOT_ACQUIRED", False))
assert report_rows[0]["reads_removed"] == 2 and report_rows[0]["reads_removed_proportion"] == 0.25
assert report_rows[1]["reads_removed_proportion"] == 0.0
(OUT / "hostile_native_stats.json").write_text(json.dumps(report_rows, indent=2, allow_nan=False) + "\n")
RECEIPT["checks"]["hostile_native_counts"] = {"rows": report_rows,
    "count_units": "primary_alignment_read_records_not_pairs",
    "zero_denominator_native_fallback": 0.0}
(ROOT / "SYNTHETIC_PROBE_RECEIPT_001.json").write_text(json.dumps(RECEIPT, indent=2, allow_nan=False) + "\n")
print(json.dumps({"checks": list(RECEIPT["checks"]), "status": "passed",
                  "identity": RECEIPT["identity"], "live_jobs": 0}))
