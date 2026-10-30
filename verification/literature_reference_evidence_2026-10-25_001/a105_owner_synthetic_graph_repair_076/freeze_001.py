"""Freeze only the constructed-input calculator/test closure; no scientific IO."""
raise SystemExit("Historical note-governed artifact generator retired.")

from pathlib import Path
import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = Path('verification/literature_reference_evidence_2026-10-25_001')
PIN = OUT / 'pin_001'
PIN.mkdir(exist_ok=False)
files = [Path('pyproject.toml'), Path('AGENTS.md'), Path('GOAL.md'),
    *[Path('gene_annotation_episode') / n for n in ('__init__.py', 'literature_controlled_response_owner_calculations.py',
        'literature_controlled_response_calculations.py', 'literature_experimental_contracts.py')],
    *[Path('tests') / n for n in ('test_literature_controlled_response_owner_calculations.py',
        'test_literature_controlled_response_calculations.py')],
    *[BASE / 'a105_controlled_adapter_design_065' / n for n in ('OWNER_INPUT_SCHEMA_004.json', 'OWNER_OUTPUT_SCHEMA_004.json',
        'OWNER_SHAPE_EXAMPLES_004.json', 'ACTIVE_UNKNOWN_OWNER_CASE_006.json')],
    BASE / 'controlled_full_source_parent_review_069/OWNER_SYNTHETIC_GRAPH_REPAIR_RELEASE_076.md',
    BASE / 'controlled_full_source_parent_review_069/SOURCE_STAGE_IMPLEMENTATION_RELEASE_073.md']
files += [Path(n) for n in ('docs/EPISODE_STRUCTURE.md', 'docs/TIME_AWARE_ESTIMATION.md', 'docs/TOOL_KNOWLEDGE.md',
    'docs/TASK_AND_STEERING.md', 'docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md',
    'docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md',
    'docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md',
    'research/experimental_scoring_review_2026-10-23/AGENTS.md',
    'research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md',
    'research/slotted_process_library/publications/2026-10-23-002/VERBATIM_RECOVERY_002.md',
    'verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md')]
for source in files:
    dest = PIN / source
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / source, dest)
attachment = Path('/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt')
shutil.copyfile(attachment, PIN / 'ACTIVE_GOAL_ATTACHMENT_001.txt')
shutil.copyfile(OUT / 'counterexample_001.py', PIN / 'counterexample_001.py')
shutil.copyfile(OUT / 'run_pin_001.py', PIN / 'run_pin_001.py')
manifest = {str(p.relative_to(PIN)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(PIN.rglob('*')) if p.is_file()}
(OUT / 'PIN_MANIFEST_001.json').write_text(json.dumps(manifest, indent=2) + '\n')
exe = Path(sys.executable).resolve()
packages = {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}
environment = {'python_executable': sys.executable, 'resolved_executable': str(exe),
    'executable_sha256': hashlib.sha256(exe.read_bytes()).hexdigest(), 'version': sys.version,
    'platform': platform.platform(), 'packages': dict(sorted(packages.items())),
    'pip_freeze': subprocess.run([sys.executable, '-m', 'pip', 'freeze', '--all'], capture_output=True, text=True, check=True).stdout,
    'external_environment': 'Existing venv reused; executable, distribution versions and loaded files recorded. No claim of a vendored environment.'}
(OUT / 'ENVIRONMENT_001.json').write_text(json.dumps(environment, indent=2) + '\n')
print(json.dumps({'pin': str(PIN), 'files': len(manifest)}))
