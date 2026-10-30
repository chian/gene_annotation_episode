"""Execute a two-sequence BLAST test, never a local database search."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
out = HERE / "native_pair"
out.mkdir(exist_ok=True)
exe = ROOT / "resources/software/ncbi-blast-2.17.0+/bin/blastp"
query = "".join((ROOT / "cases/gene_001/target.faa").read_text().splitlines()[1:])
# Explicit synthetic derivative for numerical verification, not a natural
# homolog or a proposed biological annotation.
reference = list(query[:100] + query[110:])
for position in (20, 40, 60, 80, 120):
    reference[position] = "A" if reference[position] != "A" else "G"
reference = "".join(reference)
(out / "query.faa").write_text(">public_ybhP_pair_test\n" + query + "\n")
(out / "subject.faa").write_text(">synthetic_deletion_and_substitutions\n" + reference + "\n")
base = [str(exe), "-query", str(out / "query.faa"), "-subject", str(out / "subject.faa"),
        "-seg", "no", "-num_threads", "1"]
fields = "qseqid sseqid qlen slen qstart qend sstart send qseq sseq score bitscore evalue length nident positive gaps qframe sframe"
commands = []
for name, fmt in (("result.json", "15"), ("result.tsv", "7 " + fields)):
    command = base + ["-outfmt", fmt, "-out", str(out / name)]
    process = subprocess.run(command, capture_output=True, text=True, check=True)
    (out / (name + ".stderr")).write_text(process.stderr)
    commands.append(command)
receipt = {"test_type": "actual_native_pairwise_run_on_public_sequence_and_synthetic_derivative",
    "query_length": len(query), "subject_length": len(reference),
    "deleted_query_positions_zero_based": [100, 110],
    "substituted_subject_positions_zero_based": [20, 40, 60, 80, 120],
    "program_version": subprocess.check_output([str(exe), "-version"], text=True),
    "executable_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(), "commands": commands}
(out / "execution.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({k: v for k, v in receipt.items() if k not in {"commands", "executable_sha256"}}))
