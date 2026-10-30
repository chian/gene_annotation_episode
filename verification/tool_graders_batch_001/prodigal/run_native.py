"""Reproduce the two bounded native runs into a new requested output directory.

The inputs retained here are used exactly; no data acquisition is performed.
This verification script is separate from the pure production grader.
"""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import time

from gene_annotation_episode.sequence_ops import predict_genes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).resolve().parent
    for mode in ("meta", "single"):
        lines = (source / f"{mode}.input.fna").read_text().splitlines()
        sequence = "".join(line for line in lines if not line.startswith(">"))
        started = time.perf_counter()
        native = predict_genes(sequence, code=11, mode=mode)
        elapsed = time.perf_counter() - started
        metadata = {"mode": mode, "code": 11, "input_length": len(sequence),
            "input_header": lines[0], "input_sha256": hashlib.sha256(sequence.encode()).hexdigest(),
            "elapsed_seconds": elapsed, "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "native_version": native["pyrodigal_version"], "reported_candidate_count": len(native["candidates"]),
            "execution": "actual sequence_ops.predict_genes; no episode path"}
        for suffix, value in (("native", native), ("execution", metadata)):
            (args.output / f"{mode}.{suffix}.json").write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
        print(json.dumps(metadata))


if __name__ == "__main__":
    main()
