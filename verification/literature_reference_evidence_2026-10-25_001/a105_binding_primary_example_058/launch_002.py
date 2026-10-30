"""Launch once from a newly sealed pin; preserve terminal output and exit code."""
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PYTHON = ROOT / '.venv/bin/python'

def main():
    environment = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
    for label, command, cwd in (
        ('prepare', [str(PYTHON), '-B', str(HERE / 'prepare_pin_002.py')], ROOT),
        ('run', [str(PYTHON), '-B', str(HERE / 'pin_002/run_primary_002.py')], HERE / 'pin_002')):
        result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, text=True)
        with (HERE / ('TERMINAL_'+label.upper()+'_002.txt')).open('x') as stream:
            stream.write(result.stdout); stream.write(result.stderr)
        with (HERE / ('EXIT_'+label.upper()+'_002.json')).open('x') as stream:
            json.dump({'phase': label, 'exit_code': result.returncode}, stream); stream.write('\n')
        print(json.dumps({'phase': label, 'exit_code': result.returncode}))
        if result.returncode: raise SystemExit(result.returncode)

if __name__ == '__main__':
    main()
