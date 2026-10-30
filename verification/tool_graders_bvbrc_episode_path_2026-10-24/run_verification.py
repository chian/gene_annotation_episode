"""Run the focused engineering suite and retain its exact source-version scope."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODULES = [
    'api_bvbrc', 'api_service_execution', 'api_services',
    'execution_contracts', 'execution_episodes', 'execution_service_setup',
    'execution_progress', 'episode_bindings', 'episode_journal', 'episode_receipts',
    'runtime', 'communication', 'practical_yield', 'tool_grading_artifacts',
    'tool_information',
]
PATHS = [ROOT / 'gene_annotation_episode' / (name + '.py') for name in MODULES]
PATHS += sorted((ROOT / 'gene_annotation_episode').glob('bvbrc_data*.py'))
PATHS += [ROOT / 'tests/test_bvbrc_data_episode_path.py', ROOT / 'tests/bvbrc_episode_fixture.py',
          ROOT / 'gene_annotation_episode/launch_instruction_library/api-bvbrc-data-v2.md',
          ROOT / 'gene_annotation_episode/launch_instruction_library/index.json']


def source_hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in PATHS}


def now():
    return datetime.now(timezone.utc).isoformat()


if __name__ == '__main__':
    command = [sys.executable, '-m', 'pytest', '-q', 'tests/test_bvbrc_data_episode_path.py',
        '--basetemp=/tmp/bvbrc-episode-path-20261024-verified',
        '--junitxml=' + str(HERE / 'junit.xml')]
    before = source_hashes()
    record = {'command': command, 'started_at': now(), 'source_sha256_before': before,
              'verification_kind': 'engineering_shared_workflow_with_controlled_http_responses'}
    (HERE / 'RUN.json').write_text(json.dumps(record, indent=2) + '\n')
    start = time.monotonic()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    output = completed.stdout + completed.stderr
    (HERE / 'pytest.txt').write_text(output)
    after = source_hashes()
    record.update(finished_at=now(), elapsed_seconds=time.monotonic() - start,
        exit_code=completed.returncode, source_sha256_after=after,
        source_versions_unchanged=before == after)
    (HERE / 'RUN.json').write_text(json.dumps(record, indent=2) + '\n')
    print(output)
    print('Source versions unchanged:', record['source_versions_unchanged'])
    raise SystemExit(completed.returncode if before == after else 2)
