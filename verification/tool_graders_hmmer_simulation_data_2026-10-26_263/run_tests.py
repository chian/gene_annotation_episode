"""Run only S1 verification using the caller's required local_jobs limits."""
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
directory = HERE / sys.argv[1]
directory.mkdir()
temporary = directory / "temporary"
temporary.mkdir()
files = [ROOT / "gene_annotation_episode" / f"hmmer_{part}.py" for part in
         ("simulation_data", "simulation_calculations", "model_data")]
tests = [ROOT / "tests" / f"test_hmmer_simulation_{part}.py" for part in ("data", "calculations")]
files += tests + [Path(__file__), HERE / "verify_examples.py"]
source = ROOT / "resources/software/infernal-1.1.5"
files += [source / "hmmer/src/hmmsim.c"]
files += [source / "easel" / name for name in ("esl_gumbel.c", "esl_exponential.c", "esl_histogram.c", "esl_stats.c")]
native = ROOT / "verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259/native"
files += [native / "hmmbuild_dna/profile.hmm", native / "hmmbuild_rna/profile.hmm"]
files += sorted(path for case in native.glob("hmmsim_*") for path in case.iterdir() if path.is_file())
def hashes():
    return {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
           "--basetemp="+str(temporary / "pytest"), "--junitxml="+str(directory / "tests.xml"), *map(str, tests), *sys.argv[2:]]
if sys.argv[2:] == ["examples"]:
    command = [str(ROOT / ".venv/bin/python"), str(HERE / "verify_examples.py"), str(directory / "examples")]
environment = {"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
               "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(directory / "cache")}
policy = LocalJobPolicy(20*1024**3, 4*1024**3, None)
before = hashes()
result = run_local_job(command, cwd=directory, policy=policy, env=environment)
receipt = {"scope": "pure supplied-byte parsers, retained native examples and offline calculations; no simulation rerun",
           "command": command, "environment": environment, "policy": policy.to_dict(),
           "source_hashes_before": before, "source_hashes_after": hashes(), "returncode": result.returncode,
           "metadata": result.metadata, "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
(directory / "receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")
print(result.stdout_path.read_text())
if result.stderr_path.stat().st_size:
    print(result.stderr_path.read_text(), file=sys.stderr)
print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
raise SystemExit(result.returncode)
