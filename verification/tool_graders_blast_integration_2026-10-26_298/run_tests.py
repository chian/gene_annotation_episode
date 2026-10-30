"""Explicit selected checks under the existing local_jobs resource boundary."""
import json
import hashlib
from pathlib import Path
import sys
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]


def source_snapshot(selected):
    paths = set((ROOT / 'gene_annotation_episode').glob('*.py'))
    paths.update((ROOT / 'method_loop').rglob('*.py'))
    paths.update((ROOT / 'gene_annotation_episode/knowledge').rglob('*.md'))
    paths.add(ROOT / 'gene_annotation_episode/knowledge/index.json')
    paths.add(Path(__file__).resolve())
    paths.update(Path(name.split('::', 1)[0]).resolve() for name in selected
        if not name.startswith('-') and '.py' in name)
    paths.update((ROOT / 'verification/tool_graders_blast_programs_2026-10-26_292').glob('CONTRACT_ADDENDUM_*.md'))
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths) if path.is_file()}


def main():
    label, *selected = sys.argv[1:]
    directory = Path(__file__).resolve().parent / label
    directory.mkdir()
    (directory / 'temporary').mkdir()
    before = source_snapshot(selected)
    (directory / 'source_hashes_before.json').write_text(json.dumps(before, indent=2) + '\n')
    command = [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', *selected,
        '--basetemp', str(directory / 'temporary/pytest')]
    result = run_local_job(command, cwd=directory,
        policy=LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None),
        stdout_path=directory / 'stdout.txt', stderr_path=directory / 'stderr.txt',
        env={'PYTHONPATH': str(ROOT), 'PYTHONDONTWRITEBYTECODE': '1',
            'TMPDIR': str(directory / 'temporary'), 'XDG_CACHE_HOME': str(directory / 'cache')})
    after = source_snapshot(selected)
    (directory / 'source_hashes_after.json').write_text(json.dumps(after, indent=2) + '\n')
    (directory / 'receipt.json').write_text(json.dumps({'command': command,
        'returncode': result.returncode, 'metadata': result.metadata,
        'python': sys.version, 'changed_sources': sorted(path for path in before.keys() | after.keys()
            if before.get(path) != after.get(path))}, indent=2) + '\n')
    print(json.dumps({'returncode': result.returncode, 'receipt': str(directory / 'receipt.json')}))
    print((directory / 'stdout.txt').read_text())
    print((directory / 'stderr.txt').read_text())
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
