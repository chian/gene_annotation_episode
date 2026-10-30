"""Explicit dependency installation inside the selected bounded check only.

This is verification setup, not an episode tool or an automatic runtime install.
The separate scientific checks will freeze and inspect the installed closure.
"""
import json
import os
from pathlib import Path
import subprocess
import sys


def test_install_selected_fluorescence_dependencies():
    attempt = Path(os.environ['HMMER529_ATTEMPT']).resolve(strict=True)
    assert Path(__file__).resolve().is_relative_to(attempt / 'source_snapshot')
    request = json.loads((attempt / 'selected_request.json').read_text())
    assert request['policy'] == {'memory_bytes': 21474836480,
        'scratch_bytes': 4294967296, 'wall_seconds': None}
    assert request['swap_bytes'] == 0
    destination = attempt / 'installed'
    assert destination.is_dir() and not any(destination.iterdir())
    command = [sys.executable, '-B', '-m', 'pip', 'install',
        '--disable-pip-version-check', '--no-input', '--no-deps',
        '--target', str(destination), '--report', str(attempt / 'install_report.json'),
        'FlowIO==1.4.0', 'FlowUtils==1.2.2']
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    (attempt / 'install_stdout.txt').write_text(process.stdout)
    (attempt / 'install_stderr.txt').write_text(process.stderr)
    assert process.returncode == 0, process.stderr[-6000:]
    report = json.loads((attempt / 'install_report.json').read_text())
    installed = {row['metadata']['name'].lower(): row['metadata']['version']
        for row in report['install']}
    assert installed == {'flowio': '1.4.0', 'flowutils': '1.2.2'}
    environment = dict(os.environ)
    environment['PYTHONPATH'] = os.pathsep.join((str(destination),
        str(attempt / 'dependencies')))
    probe = subprocess.run([sys.executable, '-B', '-c',
        "import json,flowio,flowutils,numpy; "
        "from flowutils.compensate import compensate; "
        "a=compensate(numpy.array([[110.,60.],[20.,100.]]),"
        "numpy.array([[1.,.1],[.2,1.]]),fluoro_indices=[0,1]); "
        "assert numpy.allclose(a,[[100.,50.],[0.,100.]],rtol=0,atol=1e-12); "
        "print(json.dumps({'flowio':flowio.__version__,'flowutils':flowutils.__version__,"
        "'numpy':numpy.__version__,'compensated_synthetic_values':a.tolist(),"
        "'flowio_path':flowio.__file__,'flowutils_path':flowutils.__file__}))"],
        env=environment, capture_output=True, text=True, check=False)
    (attempt / 'import_probe.json').write_text(json.dumps({
        'returncode': probe.returncode, 'stdout': probe.stdout, 'stderr': probe.stderr}, indent=2) + '\n')
    assert probe.returncode == 0, probe.stderr
    values = json.loads(probe.stdout)
    assert values['flowio'] == '1.4.0' and values['flowutils'] == '1.2.2'
    assert all(Path(values[name]).is_relative_to(destination)
        for name in ('flowio_path', 'flowutils_path'))
