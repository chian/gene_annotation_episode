"""Seal only new composition evidence after all required checks have passed."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import socket
import sys

OWN = Path(__file__).resolve().parent
ROOT = OWN.parents[1]
REL = str(OWN.relative_to(ROOT))
resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))


def forbidden(*args, **kwargs):
    raise AssertionError('Evidence sealing attempted network access')


socket.socket.connect = socket.socket.connect_ex = socket.create_connection = forbidden


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(name, value):
    path = OWN / name
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    return path


audit = read(OWN / 'COMPOSITION_FINAL_AUDIT_001.json')
assert audit['exit_code'] == 0 and audit['distinct_passing_cases'] == 7 and not audit['failing_cases']
receipt = read(OWN / 'composition_checks_001/receipt.json')
assert receipt['exit_code'] == 0
protected = read(OWN / 'COMPOSITION_PROTECTED_APPLICATION_001.json')
assert {name: sha(OWN / name) for name in protected} == protected
production = read(OWN / 'APPLICATION_AFTER_001.json')
assert {name: sha(ROOT / name) for name in production} == production
source = read(OWN / 'COMPOSITION_SOURCE_BEFORE_001.json')
assert {name: sha(OWN / 'composition_candidate' / name) for name in source} == source
commands = [
    ('prepare_composition_001.py', 0, 'COMPOSITION_PREPARATION_RECEIPT_001.json'),
    ('probe_composition_pins_001.py ' + REL + '/composition_candidate COMPOSITION_CANDIDATE_PINS_001.json',
        1, 'COMPOSITION_PIN_PROBE_FAILURE_001.json'),
    ('probe_composition_pins_002.py ' + REL + '/composition_candidate COMPOSITION_CANDIDATE_PINS_002.json',
        0, 'COMPOSITION_CANDIDATE_PINS_002.json'),
    ('probe_composition_pins_002.py ' + str(ROOT) + ' COMPOSITION_PRODUCTION_PINS_002.json',
        0, 'COMPOSITION_PRODUCTION_PINS_002.json'),
    ('run_composition_checks_001.py', 0, 'composition_checks_001/receipt.json'),
    ('audit_composition_001.py', 0, 'COMPOSITION_FINAL_AUDIT_001.json'),
    ('seal_composition_001.py', 0, 'COMPOSITION_SEAL_RECEIPT_001.json'),
]
write('COMPOSITION_COMMANDS_001.json', {'cwd': str(ROOT), 'executable': str(ROOT / '.venv/bin/python'),
    'commands': [{'command': '.venv/bin/python -B ' + REL + '/' + command,
        'exit_code': code, 'receipt': output,
        'script_sha256': sha(OWN / command.split()[0])} for command, code, output in commands],
    'pytest_arguments': read(OWN / 'composition_checks_001/process.json')['pytest_arguments'],
    'test_process_restarts': 0, 'poll_expiry_action': 'Continue the same original process', 'wall_time_limit': None})
rows = []
for role in ('annotation', 'scientific_process', 'launch', 'launch_api', 'results'):
    value = audit['episodes'][role]
    band = value['final_expected_next_gain']
    future = 'exact 0' if band['value'] == band['lower'] == band['upper'] == 0 else str(band['upper']) + ' upper bound'
    rows.append('| ' + ' | '.join((role, str(value['action_count']), str(value['observation_count']),
        json.dumps(value['actual_marginal_gains']), future)) + ' |')
flow = Path(audit['workflow_directory']).relative_to(OWN)
text = f'''# Bounded 197 + 203 composition verification

The exact applied composition passed the seven requested cases: the formerly failing public GenomeAlignment resolver case and all six unchanged Workflow cases. Pytest exited 0 in {receipt['seconds']:.3f} seconds. The original test process was never restarted and had no wall-time limit. This is new composition coverage only; the earlier 596/855-case evidence remains separate.

The frozen candidate has 1,054 source/input paths. All 1,046 common production targets equal the applied root hashes, before and after verification. The five existing application files, including the original pending-composition receipt, are unchanged. No production code or test assertion was modified by this verifier. The relocated 197 differential semantic test was retained but not run because its separate frozen_original dependency was not relocated.

Fresh candidate and root processes computed and bound all nine scientific facades through the existing registry. All nine pins agree. The combined GenomeAlignment pin is `{audit['registry_pins']['bvbrc_genome_alignment_bundle_adapter']}`. ComparativeSystems is `{audit['registry_pins']['bvbrc_comparative_systems_bundle_adapter']}`. Both independent historical GenomeAlignment pins remain historical. The production probe verified {audit['fresh_root_package_origin_count']} imported project modules originated in the production root and matched the applied source hashes.

The actual controlled Workflow retained native coverage **690/693 = {690/693}**, zero gaps as an available measured zero, full original bytes, missing source relationships, and qualifications. The original requested numerical values crossed results → scientific child → root with their original typed forms and source custody. Unrequested/forged values were rejected. Original partial publication at action 4 remains readable; the completed selected publication remains action 6 regardless of hash ordering.

An explicit recalculation of the saved data with changed selection produced **677/693 = {677/693}**, while an unchanged plan reproduced the original sheet. The original sheet was unchanged. Native parsing, acquisition and new processes were disabled during recalculation; saved replay additionally disabled scientific calculator/source-comparison aliases. Replay made zero new HTTP calls, preserved all five audited journal-table counts, preserved the original action, and redelivered the original typed report.

The independent read-only database audit uses `observation.step.marginal_credit` for actual gains; cumulative `credit.credit` is retained separately. Every completed own action has exactly one observation. The scientific child's repeated report delivery added one internal model call and no action or observation. Practical episodes closed with exact-zero future expectation on their positive final gain, with no extra zero observation.

| Role | Actions | Observations | Actual marginal gains | Final future expectation |
| --- | ---: | ---: | --- | --- |
{chr(10).join(rows)}

The caller-controlled scientific credit in this engineering fixture is zero. The actual Workflow assertion verified an empty root execution-tool catalog; root recorded no direct tool action. These facts do not assign biological annotation credit or establish configured-model scientific investigation.

The first pin probe failed because the verification harness assumed the GeneTree facade declared `_DEPENDENCIES` directly. It imports its pin function from the shared phylogeny module. The failed script, exact command, exit 1 and traceback are retained; the corrected verification-only probe uses the pin function's actual defining module and passes for both roots. No substantive implementation or test failure remains in these seven cases.

Evidence: `COMPOSITION_FINAL_AUDIT_001.json`, `COMPOSITION_WORKFLOW_ACCOUNTING_001.json`, `COMPOSITION_COMMANDS_001.json`, the two complete pin receipts, `COMPOSITION_ORIGINS_001.json`, source/production before-after manifests, and `composition_checks_001/tests.xml` / `test_events.jsonl` / `output.log`. Actual Workflow artifacts are under `{flow}`. `COMPOSITION_INSPECTION_001.json` and `COMPOSITION_BOUNDARY_TRACE_001.md` delimit source inspection from executed coverage.

Limits: decisions and AppService/Workspace responses were controlled fixtures using the unchanged authorized 127.0.0.1 HTTP service. No live BV-BRC, new aligner, configured model, HPC job, literature work, W05/scoring change, new workflow, or whole-tool/goal completion is claimed. Original-run source/feature mappings, genome census, and producer byte-version evidence remain missing or unknown as recorded. Other retained-format numerical examples verified by 203 were not rerun as new composition coverage. The original 197/203 verification remains the evidence for the broader unrelated cases.
'''
path = OWN / 'FINAL_COMPOSITION_VERIFICATION_001.md'
with path.open('x') as stream:
    stream.write(text)
scratch = sum(p.stat().st_size for p in OWN.rglob('*') if p.is_file())
assert scratch < 4 * 1024**3
seal = {'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv, 'executable': sys.executable,
    'cwd': str(Path.cwd()), 'exit_code': 0, 'composition_verification': 'passed_bounded_required_checks',
    'distinct_passing_cases': 7, 'source_paths_unchanged': len(source), 'production_paths_unchanged': len(production),
    'protected_application_files_unchanged': len(protected), 'scratch_bytes': scratch,
    'memory_limit_bytes': 20 * 1024**3, 'scratch_limit_bytes': 4 * 1024**3, 'wall_time_limit': None,
    'key_receipts_sha256': {name: sha(OWN / name) for name in (
        'COMPOSITION_FINAL_AUDIT_001.json', 'COMPOSITION_WORKFLOW_ACCOUNTING_001.json',
        'COMPOSITION_CANDIDATE_PINS_002.json', 'COMPOSITION_PRODUCTION_PINS_002.json',
        'COMPOSITION_COMMANDS_001.json', 'FINAL_COMPOSITION_VERIFICATION_001.md')},
    'whole_tool_completion_claim': False, 'goal_completion_claim': False}
write('COMPOSITION_SEAL_RECEIPT_001.json', seal)
hashes = {str(p.relative_to(OWN)): {'sha256': sha(p), 'bytes': p.stat().st_size}
    for p in sorted(OWN.rglob('*')) if p.is_file()}
write('COMPOSITION_OUTPUT_HASHES_001.json', hashes)
for p in OWN.rglob('*'):
    if p.is_file() and not (p.parent == OWN and p.name in protected):
        p.chmod(0o444)
assert {name: sha(OWN / name) for name in protected} == protected
print(json.dumps({'exit_code': 0, 'evidence_files_hashed': len(hashes), 'scratch_bytes': scratch,
    'final_report': str(path), 'final_report_sha256': sha(path),
    'seal_receipt_sha256': sha(OWN / 'COMPOSITION_SEAL_RECEIPT_001.json'),
    'output_hash_manifest_sha256': sha(OWN / 'COMPOSITION_OUTPUT_HASHES_001.json')}, sort_keys=True))
