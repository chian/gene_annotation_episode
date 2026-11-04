"""Run a two-wing root wiring mock with real native algorithms and fixed decisions."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tests'))
from evidence_root_fixture import EvidenceRootCase
from gene_annotation_episode.state import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['lacy', 'atpg'], required=True)
    parser.add_argument('--run-directory', type=Path, required=True)
    parser.add_argument('--usalign', required=True)
    args = parser.parse_args()
    directory = args.run_directory.resolve()
    if 'runs' not in directory.parts: raise ValueError('Run output must be beneath runs/')
    directory.mkdir(parents=True, exist_ok=False)
    (directory/'tmp').mkdir(); (directory/'cache').mkdir()
    os.environ.update(PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(directory/'tmp'), XDG_CACHE_HOME=str(directory/'cache'))
    with Store(directory/'state') as store:
        case = EvidenceRootCase(directory, store, case=args.case, usalign=args.usalign)
        try:
            result = asyncio.run(case.run())
            print(json.dumps({'case': args.case, **{key: result['credit'][key] for key in
                ('credit', 'axis_components', 'volume_components', 'axis_attribution')}}), flush=True)
        finally:
            case.jobs.close()


if __name__ == '__main__': main()
