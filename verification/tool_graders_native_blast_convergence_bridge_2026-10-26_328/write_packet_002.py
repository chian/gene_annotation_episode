"""Index retained outputs; this performs no new parsing, population or calculation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def identity(path):
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def write(name, value):
    with (HERE / name).open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


sources = ["AGENTS.md", "GOAL.md", "docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md",
    "research/tool_grader_inventory_2026-10-24/WORK_STATUS.json",
    "gene_annotation_episode/native_blast_database_convergence.py", "gene_annotation_episode/native_blast_database_metadata.py",
    "gene_annotation_episode/blast_native_iteration_records.py", "gene_annotation_episode/native_blast_database_contracts.py",
    "gene_annotation_episode/blast_iteration_inputs.py", "gene_annotation_episode/blast_iteration_calculators.py",
    "gene_annotation_episode/blast_report_collection.py", "gene_annotation_episode/local_jobs.py",
    "tests/test_native_blast_database_convergence_binding.py", "tests/test_blast_native_iteration_records.py",
    "tests/test_native_blast_database_metadata.py", "tests/test_blast_tabular_control_lines.py"]
contracts = [p for name in ("tool_graders_native_blast_convergence_binding_2026-10-26_325",
    "tool_graders_native_blast_database_result_contract_2026-10-26_314")
    for p in sorted((ROOT / "verification" / name).glob("*.md"))]
goal = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
write("SOURCE_HASHES_002.json", dict(recorded_at=datetime.now(timezone.utc).isoformat(),
    immutable_goal=identity(goal), contracts=[identity(p) for p in contracts],
    sources=[identity(ROOT / p) for p in sources], original_m=identity(HERE / "baseline/native_blast_database_metadata.py")))
checks = []
for path in sorted(HERE.glob("check*/receipt.json")):
    receipt = json.loads(path.read_bytes())
    suites = ET.parse(path.with_name("junit.xml")).getroot().findall("testsuite")
    checks.append(dict(receipt=identity(path), command=receipt["command"], policy=receipt["policy"],
        returncode=receipt["returncode"], tests=sum(int(s.attrib["tests"]) for s in suites),
        failures=sum(int(s.attrib["failures"]) for s in suites), errors=sum(int(s.attrib["errors"]) for s in suites),
        stdout=identity(path.with_name("stdout.txt")), stderr=identity(path.with_name("stderr.txt"))))
write("TEST_RECEIPTS_002.json", checks)
examples = []
for path in sorted((HERE / "check005/temporary/pytest").glob("*/binding.json")):
    if path.parent.is_symlink():
        continue
    binding = json.loads(path.read_bytes())
    extraction = binding["extraction"]
    calc_path = path.with_name("calculations.json")
    calculations = json.loads(calc_path.read_bytes()) if calc_path.exists() else None
    examples.append(dict(binding=identity(path), selected_states={k: v["status"] for k, v in binding["selected"].items() if isinstance(v, dict)}, invocation=binding["invocation"], query_status=binding["query_binding"]["status"],
        extraction_status=extraction["status"] if extraction else None,
        marker_spans=[m["byte_span"] for m in extraction["markers"]] if extraction else [],
        marker_keys=[m["record_key"] for m in extraction["markers"]] if extraction else [],
        extraction_artifact=binding["extraction_artifact"],
        counts=[{k: v["value"] for k, v in r["counts"].items()} for r in calculations["searches"]] if calculations else None,
        convergence_cells=[r["native_converged"] for r in calculations["convergence_observations"]] if calculations else None,
        files=[identity(p) for p in sorted(path.parent.iterdir()) if p.is_file()]))
write("EXAMPLE_INDEX_002.json", dict(evidence_kind="source-derived synthetic fixtures; full original artifacts retained at indexed paths",
    examples=examples, hash_seed_outputs=[identity(p) for p in sorted((HERE / "check005/temporary/pytest").glob("*/hash-seed-*.json")) if not p.parent.is_symlink()]))
print(json.dumps(dict(checks=len(checks), examples=len(examples), files=["SOURCE_HASHES_002.json", "TEST_RECEIPTS_002.json", "EXAMPLE_INDEX_002.json"])))
