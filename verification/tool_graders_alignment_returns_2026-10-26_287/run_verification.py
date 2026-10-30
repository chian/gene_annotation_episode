"""Run the pure site-return and existing communication tests under local limits."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = Path(__file__).parent / sys.argv[1]
directory.mkdir()
paths = [ROOT / name for name in (
    "gene_annotation_episode/alignment_site_returns.py",
    "tests/test_alignment_site_returns.py",
    "gene_annotation_episode/communication.py",
    "gene_annotation_episode/blast_search.py",
    "gene_annotation_episode/local_jobs.py",
    "verification/tool_graders_alignment_returns_2026-10-26_287/run_verification.py",
    "verification/tool_graders_alignment_returns_2026-10-26_287/write_examples.py",
    "verification/tool_graders_alignment_sites_2026-10-26_284/CONTRACT_001.md",
    "verification/tool_graders_alignment_sites_2026-10-26_284/RETURN_CONTRACT_002.md",
    "verification/tool_graders_alignment_sites_2026-10-26_282/OWN_ACTION_RETURN_PORT_PROPOSAL.md",
)]
examples = sys.argv[2:] == ["--examples"]
tests = [] if examples else sys.argv[2:] or [str(ROOT / "tests/test_alignment_site_returns.py"), str(ROOT / "tests/test_communication.py")]
paths.extend((ROOT / name.split("::", 1)[0]).resolve() for name in tests)
paths = sorted(set(paths))
objective = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")

def hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}

before = hashes()
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
argv = ([sys.executable, str(Path(__file__).with_name("write_examples.py")), str(directory / "filled_examples.json")]
    if examples else [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--basetemp=" + str(directory / "temporary"), "--junitxml=" + str(directory / "junit.xml"), *tests])
intent = {"argv": argv, "cwd": str(directory), "policy": asdict(policy), "source_sha256": before,
    "immutable_objective_sha256": hashlib.sha256(objective.read_bytes()).hexdigest()}
(directory / "intent.json").write_text(json.dumps(intent, indent=2) + "\n")
result = run_local_job(argv, cwd=directory, policy=policy, env={"PYTHONPATH": str(ROOT),
    "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"})
after = hashes()
receipt = {**intent, "source_sha256_after": after,
    "changed_sources": [name for name in before if before[name] != after[name]],
    "returncode": result.returncode, "metadata": result.metadata,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
(directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(directory), "returncode": result.returncode,
    "changed_sources": receipt["changed_sources"], "stdout_tail": result.stdout_path.read_text()[-15000:],
    "stderr_tail": result.stderr_path.read_text()[-2000:]}))
raise SystemExit(result.returncode)
