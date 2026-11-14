"""Observe native CPU admission without preparing or dispatching native work.

The cpu_threads argument is tested directly against the real live canonical
checker. No cgroup, owner, receipt, environment bound or policy is simulated.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path

from gene_annotation_episode import workflow_budget


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    owner = workflow_budget.active_budget()
    directory = args.directory.resolve()
    if not directory.is_relative_to(Path(owner['run_directory']).resolve()):
        raise ValueError('probe_output_must_be_inside_actual_workflow_run')
    directory.mkdir(parents=True, exist_ok=True)
    jobs = importlib.import_module('gene_annotation_episode.episodic_workflow.root.a103.local_jobs')
    policy = jobs.LocalJobPolicy(memory_bytes=1024 ** 3, scratch_bytes=128 * 1024 ** 2)
    report = {'version': 'canonical_cpu_argument_diagnostic_v1',
              'scope': 'active checker only; no native preparation, process or thread creation',
              'owner': owner, 'policy': policy.to_dict(),
              'policy_type': type(policy).__module__ + '.' + type(policy).__qualname__,
              'canonical_source_sha256': hashlib.sha256(Path(workflow_budget.__file__).read_bytes()).hexdigest(),
              'helper_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'cases': [], 'diagnostic_complete': False}
    path = directory / 'cpu-request-probe.json'
    for count in (1, 2):
        row = {'cpu_threads_argument': count}
        report['cases'].append(row)
        try:
            returned = workflow_budget.native_budget(policy, count, directory)
            row.update(status='returned', same_owner=returned == owner)
        except Exception as error:
            row.update(status='raised', error={'type': type(error).__module__ + '.' + type(error).__qualname__,
                                              'message': str(error)})
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    report['diagnostic_complete'] = True
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'diagnostic_complete': True, 'report': str(path)}))


if __name__ == '__main__':
    main()
