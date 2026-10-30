"""Build and exercise the packaged directional calculator, without live science."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parent
BUILD = HERE.parent
CANDIDATE = BUILD / 'candidate'
OUT = HERE / 'package_001'
OUT.mkdir(exist_ok=False)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot():
    files = [CANDIDATE / 'pyproject.toml']
    for root in ('gene_annotation_episode', 'method_loop'):
        files += [p for p in (CANDIDATE / root).rglob('*')
                  if p.is_file() and p.suffix in ('.py', '.json')]
    return {str(p.relative_to(CANDIDATE)): digest(p) for p in sorted(files)}


before = snapshot()
(OUT / 'source_before.json').write_text(json.dumps(before, indent=2) + '\n')
command = [sys.executable, '-m', 'pip', 'wheel', '--no-deps',
           '--wheel-dir', str(OUT / 'wheel'), str(CANDIDATE)]
(OUT / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
started = datetime.now(timezone.utc).isoformat()
clock = time.monotonic()
with (OUT / 'build.log').open('w') as log:
    process = subprocess.run(command, cwd=OUT, stdout=log, stderr=subprocess.STDOUT)
receipt = {'started_at': started, 'build_exit_code': process.returncode,
           'live_scientific_execution': False}
try:
    assert process.returncode == 0, 'wheel build failed; see preserved build.log'
    wheels = list((OUT / 'wheel').glob('*.whl'))
    assert len(wheels) == 1
    wheel = wheels[0]
    installed = OUT / 'extracted_wheel'
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        required = ['gene_annotation_episode/' + name for name in (
            'bvbrc_proteome_directional_sheet.py',
            'bvbrc_proteome_directional_numerical_contracts.py',
            'bvbrc_proteome_directional_numerical_schemas.json',
            'bvbrc_proteome_directional_geometry.py',
            'bvbrc_proteome_directional_calculators.py')]
        assert set(required) <= names
        for name in required:
            assert archive.read(name) == (CANDIDATE / name).read_bytes(), name
        archive.extractall(installed)
    code = '''import hashlib, json, pathlib, sys
sys.path.insert(0, sys.argv[1])
from gene_annotation_episode import bvbrc_proteome_directional_calculators as c
from gene_annotation_episode.bvbrc_proteome_directional import parse_genome_comparison_directional_report
from gene_annotation_episode.bvbrc_proteome_directional_sheet import build_directional_sheet
assert pathlib.Path(c.__file__).is_relative_to(pathlib.Path(sys.argv[1]))
data = pathlib.Path(sys.argv[2]).read_bytes()
source = {'content': {'source_ref': 'package-native-example', 'artifact_field': 'stdout_ref',
    'artifact_ref': 'package-retained-native', 'sha256': hashlib.sha256(data).hexdigest(),
    'byte_count': len(data)}, 'body_complete': True, 'object_complete': 'yes'}
parsed = parse_genome_comparison_directional_report(data, source=source,
    declared_format='ncbi_blastall_blastp_pairwise_text_v1', report_key='package-native-example')
observed = build_directional_sheet([parsed])['sheet']
result = c.calculate_directional_components(observed, parameters={
    'version': 'bvbrc_proteome_directional_parameters_v1',
    'formula_version': 'displayed_blastp_correspondence_v1',
    'amino_acid_alphabet': 'standard20', 'ratio_decimal_places': 18, 'rounding': 'half_even'})
subject = result['components']['reports'][0]['queries'][1]['subjects'][0]
coverage = subject['coverage']['query_trace_paired_union']['coverage']['value']
identity = subject['compatible_unique_pair_symbol_identity']['value']
assert (coverage['numerator'], coverage['denominator']) == (529, 600)
assert (identity['numerator'], identity['denominator']) == (468, 529)
print(json.dumps({'module': c.__file__, 'result_state': result['state'],
    'coverage': coverage, 'symbol_identity': identity,
    'unresolved_pair_count': subject['compatible_pair_counts']['unresolved_pairs']['value']}))
'''
    (OUT / 'installed_probe.py').write_text(code)
    invocation = [sys.executable, '-I', str(OUT / 'installed_probe.py'), str(installed),
                  str(CANDIDATE / 'tests/fixtures/bvbrc_proteome_directional/biopython_text_2221L_blastp_001.txt')]
    (OUT / 'installed_command.json').write_text(json.dumps(invocation, indent=2) + '\n')
    result = subprocess.run(invocation, cwd=OUT, capture_output=True, text=True)
    (OUT / 'installed_stdout.log').write_text(result.stdout)
    (OUT / 'installed_stderr.log').write_text(result.stderr)
    receipt.update(wheel=str(wheel.relative_to(BUILD)), wheel_sha256=digest(wheel),
                   required_packaged_files=required, installed_exit_code=result.returncode)
    assert result.returncode == 0, 'installed probe failed; see preserved stderr'
    receipt['installed_result'] = json.loads(result.stdout)
    receipt['passed'] = True
except Exception as error:
    receipt.update(passed=False, error_type=type(error).__name__, error=str(error))
finally:
    after = snapshot()
    (OUT / 'source_after.json').write_text(json.dumps(after, indent=2) + '\n')
    receipt.update(ended_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic()-clock,
        changed_sources={k: {'before': v, 'after': after.get(k)} for k,v in before.items() if after.get(k) != v},
        added_sources={k:v for k,v in after.items() if k not in before})
    receipt['passed'] = receipt.get('passed', False) and not receipt['changed_sources'] and not receipt['added_sources']
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
sys.exit(0 if receipt['passed'] else 1)
