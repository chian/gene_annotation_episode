"""Run component and existing BLAST regressions under the existing local limits."""
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
capture_examples = sys.argv[2:] == ["--examples"]
tests = [] if capture_examples else [str(ROOT / item) for item in (sys.argv[2:] or [
    "tests/test_blast_hsp_sites.py", "tests/test_blast_pairwise_grader.py",
    "tests/test_blast_grading_inputs.py", "tests/test_blast_database_grader.py",
    "tests/test_blast_explicit_associations.py"])]
paths = [ROOT / name for name in (
    "gene_annotation_episode/blast_hsp_site_inputs.py", "gene_annotation_episode/blast_hsp_site_calculators.py",
    "gene_annotation_episode/blast_pairwise_grader.py", "gene_annotation_episode/alignment_site_mapping.py",
    "gene_annotation_episode/knowledge/blast-hsp-columns.md", "gene_annotation_episode/sequence_mapping.py",
    "gene_annotation_episode/minimap2_grading_inputs.py", "gene_annotation_episode/local_jobs.py",
    "verification/tool_graders_alignment_sites_2026-10-26_284/CONTRACT_001.md",
    "verification/tool_graders_alignment_sites_2026-10-26_284/RETURN_CONTRACT_002.md",
    "verification/tool_graders_alignment_sites_2026-10-26_282/CONTRACT_DRAFT.md",
    "tests/fixtures/blast_grading_inputs/native_pair_result.json",
    "verification/w04_blast_graders_2026-10-24_001/live_api/result.body",
)]
paths.extend(Path(arg.split("::", 1)[0]) for arg in tests)
paths.extend([Path(__file__), Path(__file__).with_name("capture_examples.py"), ROOT / "tests/test_blast_hsp_sites.py"])
paths = sorted(set(paths))


def hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


before = hashes()
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
argv = ([sys.executable, str(Path(__file__).with_name("capture_examples.py"))] if capture_examples else
    [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
     "--basetemp=" + str(directory / "temporary"), "--junitxml=" + str(directory / "junit.xml"), *tests])
intent = {"argv": argv, "cwd": str(directory), "policy": asdict(policy), "source_sha256": before}
(directory / "intent.json").write_text(json.dumps(intent, indent=2) + "\n")
result = run_local_job(argv, cwd=directory, policy=policy,
    env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"})
after = hashes()
receipt = {**intent, "source_sha256_after": after,
    "changed_sources": [name for name in before if before[name] != after[name]],
    "returncode": result.returncode, "metadata": result.metadata,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
(directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(directory), "returncode": result.returncode,
    "changed_sources": receipt["changed_sources"], "stdout_tail": result.stdout_path.read_text()[-16000:],
    "stderr_tail": result.stderr_path.read_text()[-2000:]}))
raise SystemExit(result.returncode)
