"""SIGUSR1 starts a30second diagnostic profile inside an actual test run."""
import cProfile
from pathlib import Path
import pstats
import signal
import sys
import traceback

import pytest


directory = Path(__file__).resolve().parent
root = directory.parents[1]
sys.path.insert(0, str(root))
profile = cProfile.Profile()
active = False


def snapshot(signum, frame):
    global active
    if not active:
        return
    profile.disable()
    active = False
    profile.dump_stats(str(directory / 'diagnostic-007.prof'))
    with (directory / 'diagnostic-007-stack.txt').open('w') as stream:
        traceback.print_stack(frame, file=stream)
    with (directory / 'diagnostic-007-profile.txt').open('w') as stream:
        pstats.Stats(profile, stream=stream).sort_stats('cumtime').print_stats(80)


def start(signum, frame):
    global active
    active = True
    profile.enable()
    signal.alarm(30)


signal.signal(signal.SIGUSR1, start)
signal.signal(signal.SIGALRM, snapshot)
try:
    result = pytest.main(['-q', str(root / 'tests/test_bvbrc_alignment_episode_flow.py'),
        '-k', 'metacats_files', '-x', '--tb=short',
        '--junitxml=' + str(directory / 'diagnostic-007.xml')])
finally:
    snapshot(None, None)
    signal.alarm(0)
raise SystemExit(result)
