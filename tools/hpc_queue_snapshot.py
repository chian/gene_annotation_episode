"""Inspect actual or saved Aurora queue features; this command cannot submit jobs."""
import argparse
import json
from pathlib import Path

from gene_annotation_episode.hpc_queue import features, observe, snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--live', action='store_true')
    source.add_argument('--recorded-directory', type=Path)
    parser.add_argument('--resources', type=Path, default=Path('examples/aurora_execution_resources.json'))
    parser.add_argument('--queue', required=True)
    parser.add_argument('--nodes', type=int, required=True)
    parser.add_argument('--wall-seconds', type=int, required=True)
    parser.add_argument('--job-id')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if not args.output.resolve().is_relative_to(root/'runs'):
        parser.error('output must be below repository runs/')
    if args.nodes < 1 or args.wall_seconds < 1:
        parser.error('positive nodes and walltime required')
    if args.live:
        acquisition = observe(json.loads(args.resources.read_text())['aurora'])
    else:
        directory = args.recorded_directory
        jobs = json.loads((directory/'qstat-jobs.json').read_text())
        queues = json.loads((directory/'qstat-queues.json').read_text())
        activity = json.loads((directory/'aurora-activity.json').read_text())
        # Replay the recorded conditions at their original source time. This
        # is explicitly historical, never a fresh queue prediction.
        captured = max(jobs['timestamp'], queues['timestamp'], activity.get('updated', 0))
        acquisition = {'snapshot': snapshot(jobs, queues, activity, captured_at=captured)}
    candidate = {'queue': args.queue, 'nodes': args.nodes, 'wall_seconds': args.wall_seconds}
    result = {'historical_replay': not args.live, 'snapshot': acquisition['snapshot'],
              'features': features(acquisition['snapshot'], candidate, job_id=args.job_id)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'output': str(args.output), 'historical_replay': not args.live,
                      'features': result['features']}, indent=2))


if __name__ == '__main__':
    main()
