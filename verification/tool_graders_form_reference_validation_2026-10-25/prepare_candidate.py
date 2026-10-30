"""Prepare an isolated candidate; original production and run files are read-only."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[1]
CANDIDATE = EVIDENCE / 'candidate'
CANDIDATE.mkdir()
before = {}
for name in ('gene_annotation_episode', 'method_loop', 'tests'):
    shutil.copytree(ROOT / name, CANDIDATE / name,
        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache',
                                    'bvbrc_proteome_native*', 'test_bvbrc_proteome_native.py'))
    if name != 'tests':
        for path in (CANDIDATE / name).rglob('*'):
            if path.is_file():
                before[str(path.relative_to(CANDIDATE))] = hashlib.sha256(path.read_bytes()).hexdigest()
shutil.copy2(ROOT / 'pyproject.toml', CANDIDATE / 'pyproject.toml')
(CANDIDATE / 'reference').symlink_to(ROOT / 'reference', target_is_directory=True)
(CANDIDATE / 'verification').mkdir()
for name in (
    'tool_graders_bvbrc_msa_metacats_boundaries_2026-10-25',
    'tool_graders_bvbrc_metacats_native_execution_2026-10-25',
    'tool_graders_bvbrc_msa_metacats_implementation_2026-10-25',
    'tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25',
    'tool_graders_bvbrc_xmfa_sources_2026-10-25',
    'tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25',
):
    (CANDIDATE / 'verification' / name).symlink_to(ROOT / 'verification' / name,
                                                 target_is_directory=True)
receipt = {'created_at': datetime.now(timezone.utc).isoformat(), 'owner': '/root',
    'contract': 'verification/tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/FORM_REFERENCE_VALIDATION_019.md',
    'previous_goal_turn': 'progress: isolated performance evidence and accepted native parser boundary',
    'current_original_pids_confirmed_live': [1056858, 1057060],
    'candidate': str(CANDIDATE), 'original_sources': before,
    'production_edited': False, 'method_loop_changed': False}
(EVIDENCE / 'SOURCE_BASELINE_001.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps({'candidate': str(CANDIDATE), 'source_files': len(before)}))
