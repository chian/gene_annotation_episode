"""Diagnostic instrumentation only; does not alter Workflow selections."""
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


def snapshot(signum, frame):
    profile.disable()
    profile.dump_stats(str(directory / 'diagnostic-004.prof'))
    with (directory / 'diagnostic-004-stack.txt').open('w') as stream:
        traceback.print_stack(frame, file=stream)
    with (directory / 'diagnostic-004-profile.txt').open('w') as stream:
        pstats.Stats(profile, stream=stream).sort_stats('cumtime').print_stats(50)
    # One diagnostic snapshot; no episode or test deadline is imposed.


signal.signal(signal.SIGALRM, snapshot)
signal.alarm(30)
profile.enable()
try:
    result = pytest.main(['-q', str(root / 'tests/test_bvbrc_alignment_episode_flow.py'),
        '-k', 'msa_dna', '-x', '--tb=short',
        '--junitxml=' + str(directory / 'diagnostic-004.xml')])
finally:
    profile.disable()
    signal.alarm(0)
raise SystemExit(result)
