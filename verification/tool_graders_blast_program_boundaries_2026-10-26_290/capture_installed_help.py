"""Planning evidence only: capture installed BLAST help without a search."""
from dataclasses import asdict
import json
from pathlib import Path

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).resolve().parent / "installed_help"
BIN = ROOT / "resources/software/ncbi-blast-2.17.0+/bin"
PROGRAMS = ("blastn", "blastp", "blastx", "tblastn", "tblastx", "psiblast",
            "deltablast", "rpsblast", "rpstblastn", "blastn_vdb", "tblastn_vdb")
POLICY = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3,
                        wall_seconds=None)


def main():
    DEST.mkdir(exist_ok=True)
    receipts = []
    for name in PROGRAMS:
        work = DEST / name
        work.mkdir(exist_ok=True)
        command = [str(BIN / name), "-help"]
        result = run_local_job(command, cwd=work, policy=POLICY,
                               stdout_path=work / "help.txt", stderr_path=work / "stderr.txt")
        receipts.append({"program": name, "command": command, "returncode": result.returncode,
                         "stdout_path": str(result.stdout_path.relative_to(ROOT)),
                         "stderr_path": str(result.stderr_path.relative_to(ROOT)),
                         "metadata": result.metadata})
    path = DEST / "receipts.json"
    path.write_text(json.dumps({"purpose": "read_only_installed_help_no_search",
                               "policy": asdict(POLICY), "receipts": receipts}, indent=2) + "\n")
    print(json.dumps({"receipt": str(path.relative_to(ROOT)),
                      "exit_codes": {row["program"]: row["returncode"] for row in receipts}}))


if __name__ == "__main__":
    main()
