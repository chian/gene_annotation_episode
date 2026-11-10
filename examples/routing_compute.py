"""Small-memory engineering work for the live resource-routing investigation.

This is real SHA-256 computation, not a scientific algorithm or timing oracle.
The witness ends the resource-occupancy experiment once its routing question
has been answered. It is an event condition, never an elapsed-time cutoff.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time


def run(directory, witness, rounds):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    os.nice(10)
    started = time.time()
    digest = hashlib.sha256(b'gene-episode-routing-engineering-probe-v1').digest()
    block = b'engineering resource occupancy\n' * 2048
    completed = 0
    for index in range(rounds):
        digest = hashlib.sha256(digest + block).digest()
        completed = index + 1
        if completed % 4096 == 0:
            (directory/'progress.json').write_text(json.dumps({
                'completed_rounds': completed, 'pid': os.getpid(), 'observed_at': time.time()}))
            if witness is not None and Path(witness).is_file():
                break
    result = {'kind': 'engineering_sha256_probe', 'pid': os.getpid(),
        'started_at': started, 'finished_at': time.time(), 'completed_rounds': completed,
        'processed_bytes': completed*len(block), 'digest': digest.hex(),
        'routing_witness_observed': witness is not None and Path(witness).is_file()}
    (directory/'result.json').write_text(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--witness')
    parser.add_argument('--rounds', type=int, default=8_000_000)
    args = parser.parse_args()
    run(args.directory, args.witness, args.rounds)
