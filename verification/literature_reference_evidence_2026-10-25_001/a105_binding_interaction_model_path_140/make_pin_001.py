"""Snapshot current supplement and exact historical native dependency for engineering checks."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
PIN=OUT/'pin_001'
if PIN.exists():raise RuntimeError('pin must be new')
PIN.mkdir()
for folder in ('gene_annotation_episode','method_loop','tests'):
    shutil.copytree(ROOT/folder,PIN/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
shutil.copy2(ROOT/'pyproject.toml',PIN/'pyproject.toml')
legacy=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_visual_signal_repository_071/pin_004/gene_annotation_episode/literature_rate_storage.py'
assert hashlib.sha256(legacy.read_bytes()).hexdigest()=='171eb81f23bcf5b8c048807a093a066f42674f960ac59826cbcb4ae3d94490b4'
shutil.copy2(legacy,PIN/'gene_annotation_episode/literature_rate_storage.py')
fixture=Path('verification/literature_reference_evidence_2026-10-25_001/parent_population_information_023/population_catalog_before.json')
(PIN/fixture).parent.mkdir(parents=True)
shutil.copy2(ROOT/fixture,PIN/fixture)
files={str(p.relative_to(PIN)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(PIN.rglob('*')) if p.is_file()}
(OUT/'PIN_001.json').write_text(json.dumps({'files':files,'native_dependency_override':str(legacy.relative_to(ROOT)),
    'shared_checkout_rate_sha256':hashlib.sha256((ROOT/'gene_annotation_episode/literature_rate_storage.py').read_bytes()).hexdigest(),
    'scope':'Synthetic engineering under native frozen dependency. Does not establish current shared checkout execution or scientific model extraction.'},indent=2)+'\n')
print(PIN,len(files))
