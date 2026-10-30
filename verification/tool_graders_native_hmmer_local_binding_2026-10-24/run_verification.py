"""Run only the local-binding checks and retain source stability evidence."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (OUTPUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    paths = [*ROOT.joinpath('gene_annotation_episode').rglob('*.py'),
             *ROOT.joinpath('method_loop').rglob('*.py'),
             ROOT / 'tests/test_native_hmmer_local_binding.py', Path(__file__).resolve()]
    before = {str(path.relative_to(ROOT)): sha(path) for path in paths}
    write('final_all_source_hashes_before.json', before)
    arguments = ['-q', 'tests/test_native_hmmer_local_binding.py',
        '--basetemp=' + str(OUTPUT / 'final-tmp'), '--junitxml=' + str(OUTPUT / 'final.junit.xml')]
    write('final_command.json', {'executable': sys.executable,
        'entrypoint': str(Path(__file__).relative_to(ROOT)), 'pytest_arguments': arguments,
        'native_policy': {'memory_bytes': 20 * 1024**3, 'scratch_bytes': 4 * 1024**3,
                          'wall_seconds': None}})
    with (OUTPUT / 'final_pytest.txt').open('w') as stream, redirect_stdout(stream), redirect_stderr(stream):
        code = int(pytest.main(arguments))
    loaded = set()
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT) and path.suffix == '.py':
                relative = str(path.relative_to(ROOT))
                if relative in before:
                    loaded.add(relative)
    loaded.add('tests/test_native_hmmer_local_binding.py')
    loaded_before = {name: before[name] for name in sorted(loaded)}
    loaded_after = {name: sha(ROOT / name) for name in sorted(loaded)}
    write('final_loaded_source_hashes_before.json', loaded_before)
    write('final_loaded_source_hashes_after.json', loaded_after)
    changed = [name for name in sorted(loaded) if loaded_before[name] != loaded_after[name]]
    summary = {'pytest_exit_code': code, 'loaded_local_python_files': len(loaded),
               'changed_loaded_sources': changed, 'stable_loaded_sources': not changed}
    write('final_source_stability.json', summary)
    print(json.dumps(summary))
    return code or int(bool(changed))


if __name__ == '__main__':
    raise SystemExit(main())
