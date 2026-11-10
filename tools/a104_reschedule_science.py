"""Retain an original calendar condition with the corrected resume adapter."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from gene_annotation_episode.workflow_budget import active_budget
from gene_annotation_episode.hpc_scheduler import register_resume


def main():
    run = Path(active_budget()['run_directory'])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case-directory', type=Path, required=True)
    args = parser.parse_args()
    case = args.case_directory.resolve()
    root = Path(__file__).resolve().parents[1]
    previous = json.loads((case/'scheduled-resume.json').read_text())
    if previous['window'] != os.environ['CODEX_THREAD_ID']:
        raise ValueError('a104_resume_must_belong_to_original_window')
    subprocess.run(['systemctl', '--user', 'stop', previous['timer']], check=True)
    command = [sys.executable, '-B', str(root/'tools/a104_resume_science.py'), '--case-directory', str(case),
               '--refresh-resource-policy', '--parent-wait-availability']
    (run/'REPLACED_RESUME.json').write_text(json.dumps({'previous': previous,
        'command': command, 'change': 'same_original_wait_and_science; updated_environment_adapter_and_parent_action_availability'}, indent=2)+'\n')
    due = datetime.fromisoformat(previous['resume_at'])
    if due <= datetime.now(timezone.utc):
        os.execvpe(command[0], command, {**os.environ, 'PYTHONPATH': str(root)})
    spec = register_resume(case, root, ['/usr/bin/env', 'PYTHONPATH='+str(root), *command], previous['schedule'])
    print(json.dumps({'event': 'a104_original_wait_rescheduled', 'resume_at': spec['resume_at'],
                      'timer': spec['timer'], 'condition_unchanged': True}), flush=True)


if __name__ == '__main__':
    main()
