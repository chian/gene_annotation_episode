"""Verify selected derivation/publication paths in the existing local limits."""
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
tests = sys.argv[2:] or [str(ROOT / "tests/test_sequence_derivation_publication.py"),
                        str(ROOT / "tests/test_sequence_derivation_workflow.py")]
paths = [ROOT / name for name in (
    "gene_annotation_episode/domain.py",
    "gene_annotation_episode/sequence_ops.py",
    "gene_annotation_episode/sequence_views.py",
    "gene_annotation_episode/sequence_mapping.py",
    "gene_annotation_episode/sequence_translation_grader.py",
    "gene_annotation_episode/sequence_extraction_grader.py",
    "gene_annotation_episode/tools.py",
    "gene_annotation_episode/tool_grading_artifacts.py",
    "gene_annotation_episode/tool_information.py",
    "gene_annotation_episode/knowledge/index.json",
    "gene_annotation_episode/knowledge/sequence-translation.md",
    "gene_annotation_episode/knowledge/sequence-extraction.md",
    "gene_annotation_episode/runtime.py",
    "gene_annotation_episode/episode_receipts.py",
    "tests/test_sequence_derivation_publication.py",
    "tests/test_sequence_derivation_workflow.py",
    "verification/tool_graders_sequence_derivation_2026-10-26_279/CONTRACT_001.md",
    "verification/tool_graders_sequence_derivation_2026-10-26_279/SUMMARY_SHAPE_ADDENDUM_001.md",
    "verification/tool_graders_sequence_derivation_2026-10-26_279/PUBLICATION_SCHEMA_ADDENDUM_001.md",
)]
paths.extend(Path(arg.split("::", 1)[0]) for arg in tests)
paths = sorted(set(paths))
def hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths}
before = hashes()
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
argv = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
        "--basetemp=" + str(directory / "temporary"),
        "--junitxml=" + str(directory / "junit.xml"), *tests]
intent = {"argv": argv, "cwd": str(directory), "policy": asdict(policy),
          "source_sha256": before}
(directory / "intent.json").write_text(json.dumps(intent, indent=2) + "\n")
result = run_local_job(argv, cwd=directory, policy=policy,
    env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1",
         "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"})
after = hashes()
receipt = {**intent, "source_sha256_after": after,
    "changed_sources": [name for name in before if before[name] != after[name]],
    "returncode": result.returncode, "metadata": result.metadata,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
(directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(directory), "returncode": result.returncode,
    "changed_sources": receipt["changed_sources"],
    "stdout_tail": result.stdout_path.read_text()[-10000:],
    "stderr_tail": result.stderr_path.read_text()[-2000:]}))
raise SystemExit(result.returncode)
