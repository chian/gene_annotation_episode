"""Record final source bytes and existing receipts without executing test code."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent


def identity(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def save(name, value):
    with (PACKET / name).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


owned = [base + name + ".py" for base in
         ("gene_annotation_episode/native_blast_standard_database_", "tests/test_native_blast_standard_database_")
         for name in ("contracts", "driver", "tool_info")]
sources = []
for relative in owned:
    source = ROOT / relative
    destination = PACKET / "final_source_snapshot" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(source.read_bytes())
    sources.append(identity(source))

baseline = json.loads((PACKET / "INSPECTED_SOURCE_HASHES_001.json").read_bytes())
existing = []
for row in baseline:
    current = identity(ROOT / row["path"])
    existing.append({**current, "initial_sha256": row["sha256"],
                     "matches_initial": current["sha256"] == row["sha256"]})

authority = [Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt"),
             *[ROOT / "verification/tool_graders_standard_blast_database_plan_2026-10-26_327" / name
               for name in ("PROPOSED_PLAN_001.md", "ACCEPTANCE_001.md", "CONTRACT_ADDENDUM_001.md", "CONTRACT_ADDENDUM_002.md")]]
help_root = ROOT / "verification/tool_graders_blast_program_boundaries_2026-10-26_290/installed_help"
inspected_help = [help_root / program / "help.txt" for program in ("blastn", "blastp", "blastx", "tblastn", "tblastx")]
receipts = []
for check in ("check001", "check002", "check003", "check004"):
    folder = PACKET / check
    receipt = json.loads((folder / "receipt.json").read_bytes())
    stdout = (folder / "stdout.txt").read_text()
    result_lines = [line for line in stdout.splitlines() if " passed" in line or " failed" in line]
    receipts.append({"check": check, "returncode": receipt["returncode"],
                     "pytest_result_lines": result_lines, "policy": receipt["metadata"]["policy"],
                     "files": [identity(folder / name) for name in ("selection.json", "receipt.json", "stdout.txt", "stderr.txt")]})

save("FINAL_SOURCE_HASHES_001.json", {"recorded_at": datetime.now(timezone.utc).isoformat(),
     "sources": sources, "existing_inspected_sources": existing,
     "authorities": [identity(path) for path in authority],
     "retained_help": [identity(path) for path in inspected_help]})
save("TEST_RECEIPT_INDEX_001.json", receipts)
print(json.dumps({"owned_sources": sources,
                  "existing_inspected_sources_unchanged": all(row["matches_initial"] for row in existing),
                  "checks": [{"check": row["check"], "returncode": row["returncode"],
                              "pytest_result_lines": row["pytest_result_lines"]} for row in receipts]}, indent=2))
