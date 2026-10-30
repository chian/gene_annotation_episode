"""Create a new independent079 pin; never writes into prior workloads' pins."""
raise SystemExit("Historical note-governed artifact generator retired.")

import difflib
import hashlib
import json
from pathlib import Path
import shutil


base = Path(__file__).resolve().parent
root = base.parents[2]
pin = base / 'pin_001'
pin.mkdir(exist_ok=False)
for folder in ('gene_annotation_episode', 'method_loop'):
    shutil.copytree(root / folder, pin / folder,
        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache'))
files = ['pyproject.toml', 'AGENTS.md', 'GOAL.md',
    'docs/EPISODE_STRUCTURE.md', 'docs/TIME_AWARE_ESTIMATION.md',
    'docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md',
    'research/experimental_scoring_review_2026-10-23/AGENTS.md']
for name in ('runtime_receipt', 'storage', 'readonly', 'inputs', 'calculations', 'validation'):
    files.append(f'tests/test_literature_ratio_source_{name}.py')
prefix = 'verification/literature_reference_evidence_2026-10-25_001/'
files.extend(prefix + 'a105_visual_signal_reader_070/normative/' + name + '_SCHEMA_008.json'
    for name in ('REQUEST', 'EXTRACTION', 'SHEET'))
files.extend(prefix + 'visual_signal_parent_review_067/text_locator_declarations_008/' + name + '_SCHEMA_008.json'
    for name in ('REQUEST', 'RETURN'))
for name in files:
    destination = pin / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / name, destination)
shutil.copyfile(base / 'receipt_import_audit.py', pin / 'receipt_import_audit.py')
before = base / 'before/gene_annotation_episode/literature_ratio_source_storage.py'
after = pin / 'gene_annotation_episode/literature_ratio_source_storage.py'
(base / 'NATIVE_PATCH_001.diff').write_text(''.join(difflib.unified_diff(
    before.read_text().splitlines(keepends=True), after.read_text().splitlines(keepends=True),
    fromfile='before/gene_annotation_episode/literature_ratio_source_storage.py',
    tofile='gene_annotation_episode/literature_ratio_source_storage.py')))
manifest = {'pin_root': str(pin),
    'native_before_sha256': hashlib.sha256(before.read_bytes()).hexdigest(),
    'files': {str(path.relative_to(pin)): {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'size': path.stat().st_size} for path in sorted(pin.rglob('*')) if path.is_file()}}
(base / 'PIN_MANIFEST_001.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'pin': str(pin), 'file_count': len(manifest['files']),
    'native_sha256': manifest['files']['gene_annotation_episode/literature_ratio_source_storage.py']['sha256']}))
