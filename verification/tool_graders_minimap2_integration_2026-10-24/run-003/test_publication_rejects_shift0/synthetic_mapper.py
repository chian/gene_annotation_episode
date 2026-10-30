#!/home/chia/repos/gene_annotation_episode/.venv/bin/python

"""Synthetic process fixture, not minimap2 or an alignment implementation."""
import json
import os
from pathlib import Path
import signal
import sys
import time

MODE = 'partial'
ROOT = Path(__file__).resolve().parent
args = sys.argv[1:]
if args == ["--version"]:
    print("synthetic-process-fixture-not-minimap2")
    raise SystemExit(0)
if args == ["-h"]:
    print("Synthetic version/help/index stubs; no mapping algorithm is implemented.")
    raise SystemExit(0)
if "-d" in args:
    Path(args[args.index("-d")+1]).write_bytes(b"synthetic index fixture\n")
    sys.stderr.write("synthetic index stub completed\n")
    raise SystemExit(0)

if MODE == "cancel":
    def terminated(signum, frame):
        (ROOT/"termination-observed.json").write_text(json.dumps({"pid": os.getpid(), "signal": signum}))
        raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM, terminated)
    (ROOT/"mapping-started.json").write_text(json.dumps({"pid": os.getpid()}))
    while True:
        time.sleep(1)

if MODE == "failure":
    sys.stderr.write("synthetic mapper execution failure; fixture exit 17\n")
    raise SystemExit(17)

def fasta(path):
    # The production adapter writes exactly one sequence line per operand.
    lines = Path(path).read_text().splitlines()
    return [(lines[i][1:], lines[i+1]) for i in range(0, len(lines), 2)]

query_path = Path(args[-1])
queries = fasta(query_path)
reference, reference_sequence = fasta(query_path.parent/"references.fasta")[0]
for ordinal, (query, sequence) in enumerate(queries):
    if ordinal:
        sys.stdout.write("synthetic damaged PAF row\n")
    length = len(sequence)
    fields = [query, str(length), "0", str(length), "+", reference,
        str(len(reference_sequence)), "0", str(length), str(length), str(length),
        "60", "tp:A:P", "cg:Z:"+str(length)+"M", "cs:Z:="+sequence]
    sys.stdout.write("\t".join(fields)+"\n")
    if MODE == "resource_after_row" and ordinal == 0:
        sys.stdout.flush()
        while True:
            time.sleep(.05)
sys.stderr.write("synthetic mapper emitted controlled PAF records\n")
