"""Use the project virtualenv entrypoint, retaining its environment identity."""
from pathlib import Path
import json
import os
import subprocess
import sys

STAGE = Path(__file__).absolute().parent
ROOT = next(p for p in STAGE.parents if (p / '.venv/bin/python').exists())
OUT = STAGE / sys.argv[1]
OUT.mkdir(exist_ok=False)
launcher = ('import runpy,sys;sys.path[:0]=[sys.argv[1],sys.argv[1]+"/tests"];'
            'sys.argv=[sys.argv[1]+"/run_connected_checks_004.py",sys.argv[2]];'
            'runpy.run_path(sys.argv[0],run_name="__main__")')
command = [str(ROOT / '.venv/bin/python'), '-B', '-c', launcher, str(STAGE / 'pin_004'), str(OUT)]
with (OUT / 'TERMINAL_004.log').open('x') as stream:
    proc = subprocess.run(command, cwd=OUT, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                          stdout=stream, stderr=subprocess.STDOUT)
receipt = {'exit_code': proc.returncode, 'terminal': str(OUT / 'TERMINAL_004.log'),
    'interpreter_entrypoint': str(ROOT / '.venv/bin/python'),
    'initial_checks_004_failure': 'Launcher resolved virtualenv interpreter symlink; system Python lacked Bio. No application test ran.'}
(OUT / 'TERMINAL_RECEIPT_004.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
raise SystemExit(proc.returncode)
