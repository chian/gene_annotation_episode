"""Assemble literature checks on the last complete runtime plus owned changes.

Does not modify a live pin, scientific Store or the separate tool-grader work.
The manifest records the limited integration claim rather than implying that
unrelated concurrent checkout changes were included or verified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
OWNED = [
    'gene_annotation_episode/episode_services.py',
    'gene_annotation_episode/literature_episodes.py',
    'gene_annotation_episode/literature_experimental_prompt.py',
    'gene_annotation_episode/literature_binding_prompt.py',
    'gene_annotation_episode/literature_binding_reader.py',
    'gene_annotation_episode/literature_binding_calculations.py',
    'gene_annotation_episode/literature_binding_storage.py',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    destination = args.directory.resolve()
    if not destination.is_relative_to(BASE) or destination.exists():
        raise ValueError('new_owned_verification_directory_required')
    prior = BASE / 'live_pin_004'
    manifest = json.loads((prior / 'PACKAGE_MANIFEST.json').read_text())
    for name, expected in manifest.items():
        if sha(prior / name) != expected:
            raise ValueError('prior_pin_changed:' + name)
    destination.mkdir(parents=True)
    files = {}
    for name in manifest:
        source = ROOT / name if name in OWNED else prior / name
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        files[name] = {'source': str(source), 'sha256': sha(target)}
    for name in OWNED:
        if name not in files:
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
            files[name] = {'source': str(ROOT / name), 'sha256': sha(target)}
    shutil.copytree(ROOT / 'tests', destination / 'tests',
                    ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache'))
    for name in ['primary_iscr2013', 'primary_yeag', 'primary_csid']:
        target = destination / 'verification' / BASE.name / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(BASE / name, target)
    for name in ['pyproject.toml']:
        if (ROOT / name).is_file():
            shutil.copyfile(ROOT / name, destination / name)
    (destination / 'ASSEMBLY.json').write_text(json.dumps({
        'baseline': str(prior), 'owned_overlay': OWNED, 'files': files,
        'scope': 'Complete prior runtime plus current owned literature changes; concurrent unrelated tool edits excluded',
        'live_pin_or_state_modified': False}, indent=2) + '\n')
    print(json.dumps({'directory': str(destination), 'package_files': len(files),
                      'owned_overlay_files': len(OWNED)}))


if __name__ == '__main__':
    main()
