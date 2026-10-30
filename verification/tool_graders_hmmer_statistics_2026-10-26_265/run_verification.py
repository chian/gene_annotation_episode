"""Bounded verification of the hmmstat sheet and deterministic calculations."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

HERE = Path(__file__).resolve().parent


def main():
    directory = HERE / sys.argv[1]
    directory.mkdir()
    policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
        str(ROOT / "tests/test_hmmer_statistics_data.py"),
        str(ROOT / "tests/test_hmmer_statistics_calculations.py"), "--junitxml", str(directory / "tests.xml")]
    if len(sys.argv) > 2 and sys.argv[2] == "examples":
        command = [sys.executable, str(HERE / "generate_examples.py")]
    paths = [ROOT / "gene_annotation_episode" / (name + ".py") for name in (
        "hmmer_model_data", "hmmer_model_calculations", "hmmer_statistics_data", "hmmer_statistics_calculations")]
    paths += [ROOT / "tests" / (name + ".py") for name in ("test_hmmer_statistics_data", "test_hmmer_statistics_calculations")]
    paths += [HERE / "run_verification.py"]
    native = ROOT / "verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259/native"
    paths += [native / f"hmmbuild_{kind}" / "profile.hmm" for kind in ("dna", "rna", "protein", "annotated")]
    paths += [native / f"hmmstat_{kind}" / "stdout.log" for kind in ("dna", "rna", "protein", "annotated")]
    if (HERE / "generate_examples.py").exists():
        paths.append(HERE / "generate_examples.py")
    def hashes():
        return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    intent = {"argv": command, "cwd": str(directory), "policy": asdict(policy), "source_sha256": hashes()}
    (directory / "intent.json").write_text(json.dumps(intent, indent=2) + "\n")
    result = run_local_job(command, cwd=directory, policy=policy,
        env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
             "TMPDIR": str(directory), "XDG_CACHE_HOME": str(directory / "cache")})
    receipt = {**intent, "returncode": result.returncode, "metadata": result.metadata,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path), "source_sha256_after": hashes()}
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"receipt": str(directory / "receipt.json"), "returncode": result.returncode}))
    print(result.stdout_path.read_text())


if __name__ == "__main__":
    main()
