"""Selected native producer acceptance, run only in the bounded test handle.

The BAMs are retained synthetic engineering fixtures. This checks actual MACS2
execution and byte custody, not biological validity or complete episode return.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.materials import source_for_artifact
from gene_annotation_episode.native_atac_differential_contracts import (
    MODE, OPERATION, POLICY, _dependency_roots, canonical, digest,
    requested_job_from_atac, validate_atac_native_bundle,
)
from gene_annotation_episode.native_atac_differential_software import freeze_atac_native_software_binding
from gene_annotation_episode.native_atac_differential_local import local_atac_differential_plan
from gene_annotation_episode.native_atac_differential_capture import capture_atac_native_files
from gene_annotation_episode.native_atac_differential_driver import _callpeak_binding
from gene_annotation_episode.native_atac_differential_observations import atac_observed_files, read_atac_output
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_execution_records import assess_validations
from gene_annotation_episode.practical_execution_state import PracticalState
from gene_annotation_episode.state import Store
from gene_annotation_episode.atac_differential_inputs import parse_macs2_peaks_xls, parse_macs2_narrowpeak


ATTEMPT = Path(os.environ['ATAC_NATIVE_ATTEMPT'])
REPO = Path(os.environ['ATAC_NATIVE_REPO'])
FIXTURES = Path(os.environ['ATAC_NATIVE_FIXTURES'])
SNAPSHOT = Path(__file__).parents[2]
PREPARED = REPO / 'verification/tool_graders_atac_differential_plan_2026-10-27_460/prerequisite001'


def pin(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return dict(path=str(path), sha256=h.hexdigest(), size_bytes=path.stat().st_size)


def save(name, value):
    path = ATTEMPT / name
    path.write_bytes(canonical(value))
    path.chmod(0o444)
    return path


def file_identity(path, format):
    row = pin(path)
    return dict(artifact_ref='artifact_' + row['sha256'], format=format,
        **{k: row[k] for k in ('sha256', 'size_bytes')})


def native_runtime():
    preparation = json.loads((PREPARED / 'prepared_software.json').read_text())
    for row in preparation['files']:
        assert pin(row['path']) == row
    python, script = Path(preparation['python']), Path(preparation['macs2'])
    site = PREPARED / 'environment/lib/python3.11/site-packages'
    paths = {script}
    for directory in ('MACS2', 'numpy', 'numpy.libs', 'MACS2-2.2.9.1.dist-info', 'numpy-1.26.4.dist-info'):
        paths.update(p for p in (site / directory).rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo'))
    runtime = dict(python_executable=str(python), python_sha256=pin(python)['sha256'],
        python_version='3.11.13', macs2_script=str(script), macs2_sha256=pin(script)['sha256'],
        macs2_version='2.2.9.1', import_roots=[str(site)], files=[pin(p) for p in sorted(paths)])
    save('prepared_native_pins_before.json', [pin(python), *runtime['files']])
    return runtime


def selected_job(software):
    inputs, samples, conditions, bindings = [], [], [], []
    for i in (1, 2):
        path = FIXTURES / f'bam_inputs/condition{i}.bam'
        file = file_identity(path, 'bam')
        inputs.append(dict(input_key=f'input{i}', condition_id=f'condition{i}', sample_id=f'sample{i}',
            reference_id='synthetic_chrToy_12000', file=file))
        samples.append(dict(sample_id=f'sample{i}', input_artifact_refs=[file['artifact_ref']],
            reference_id='synthetic_chrToy_12000', biospecimen_id=None, replicate_id=None,
            origin='synthetic_engineering_fixture'))
        conditions.append(dict(condition_id=f'condition{i}', label=None, sample_ids=[f'sample{i}']))
        bindings.append(dict(input_key=f'input{i}', file=file, path=str(path)))
    request = dict(version='atac_differential_request_v1', operation=OPERATION, mode=MODE,
        comparison_key='retained_native_acceptance', reference=dict(reference_id='synthetic_chrToy_12000',
            assembly_accession_version=None, source_refs=[], aliases=[], contigs=[dict(chromosome='chrToy',
                length_bp=12000, sequence_accession_version=None, sequence_sha256=None, source_refs=[])]),
        samples=samples, conditions=conditions, inputs=inputs,
        callpeak=dict(genome_size_argument='12000', qvalue_cutoff=0.05, keep_duplicates=1, nomodel=True,
            shift_bp=-100, extension_size_bp=200, store_bedgraph=True, spmr=False, broad=False, downsample=False),
        bdgdiff=dict(cutoff_log10_lr=3, minimum_length_bp=50, maximum_gap_bp=0), output_prefix='outputs')
    return dict(request=request, software=software, input_bindings=bindings)


def launch_selected(job, name):
    workspace = ATTEMPT / name
    workspace.mkdir()
    driver = job['software']['driver_runtime']
    environment = dict(PYTHONPATH=os.pathsep.join([driver['module_root'], *_dependency_roots(driver)]),
        PYTHONHOME=sys.base_prefix, PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1', PYTHONDONTWRITEBYTECODE='1',
        OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', TMP=str(workspace / 'tmp'), TEMP=str(workspace / 'tmp'),
        TMPDIR=str(workspace / 'tmp'), XDG_CACHE_HOME=str(workspace / 'cache'), PIP_CACHE_DIR=str(workspace / 'cache/pip'))
    selected = requested_job_from_atac(job, environment=environment)
    assignment = dict(version='practical_assignment_v1', assignment_id=name, resource_kind='local', resource_id='local',
        workspace=str(workspace), endpoint='usable_handoff', requested_job=selected,
        progress_requirements=[dict(key='handoff', credit=1, predicate=dict(kind='requested_job_handoff'))],
        completion_keys=['handoff'], initial_context=dict(revision=0, cwd=str(workspace), environment={}),
        inventory_snapshot={}, constraints=POLICY)
    operations = LocalPracticalOperations(dict(kind='local', workspace=str(workspace), policy=POLICY,
        native_atac_differential=[dict(operation=OPERATION, mode=MODE, software=job['software'])]))
    state = PracticalState(workspace / 'practical-state', 'producer-acceptance-474', name, assignment)
    operation_key = 'explicit-native-start'
    state.begin(operation_key, 'practical.job.start', {})
    outcome, after = operations._execute(state, 'practical.job.start', {}, operation_key)
    validations = assess_validations(assignment, outcome, state.context(), tool_name='practical.job.start')
    receipt = state.finish(operation_key, outcome, validations, context_after=after)
    handle = native.NativeJobHandle(Path(outcome['facts']['requested_job']['execution_id']))
    save(name + '-start-receipt.json', receipt)
    save(name + '-assignment.json', assignment)
    save(name + '-handle.json', handle.read())
    print(json.dumps(dict(case=name, handle=str(handle.path), unit=handle.read()['unit'])), flush=True)
    native_result = native.wait_job(handle)
    view = native.status(handle)
    assert view['terminal'] and view['quiescent']
    save(name + '-closure.json', view)
    plan = local_atac_differential_plan(assignment, str(handle.path))
    save(name + '-plan.json', plan)
    assert plan['identity']['operation_key'] == operation_key
    assert plan['identity']['assignment_sha256'] == digest(assignment)
    bundle = json.loads((Path(plan['attempt_directory']) / 'outputs/bundle.json').read_bytes())
    validate_atac_native_bundle(bundle, plan=plan)
    return plan, bundle, receipt, view, native_result.returncode


if len(sys.argv) == 3 and sys.argv[1] == '--resume-from':
    # Explicit follow-up after a closed harness failure. Reuse the original
    # producer handle and exact source/input/software pins; never resubmit it.
    prior = Path(sys.argv[2])
    for filename in ('source_pins_before.json', 'binary_pins_before.json',
            'driver_pins_before.json', 'prepared_native_pins_before.json'):
        originals = json.loads((prior / filename).read_text())
        for row in originals:
            actual = pin(row['path'])
            if actual != row:
                # The original launcher pinned its editable administrative
                # script in addition to its immutable copied execution source.
                # That script was repaired after native closure. Preserve this
                # mismatch and verify the original immutable copy explicitly.
                administrative = REPO / 'verification/tool_graders_atac_native_producer_finish_2026-10-27_474/run_checks.py'
                assert filename == 'binary_pins_before.json' and row['path'] == str(administrative)
                frozen = pin(prior / 'source_snapshot' / administrative.relative_to(REPO))
                assert all(frozen[key] == row[key] for key in ('sha256', 'size_bytes'))
                save('historical-administrative-script-change.json', dict(original=row, current=actual,
                    original_immutable_copy=frozen, scientific_source_or_binary_changed=False))
    software = json.loads((prior / 'software_binding.json').read_text())
    driver_pins = json.loads((prior / 'driver_pins_before.json').read_text())
    plan = json.loads((prior / 'native-success-plan.json').read_text())
    receipt = json.loads((prior / 'native-success-start-receipt.json').read_text())
    view = json.loads((prior / 'native-success-closure.json').read_text())
    original_handle = native.NativeJobHandle(Path(plan['identity']['execution_id']))
    current = native.status(original_handle)
    assert current['terminal'] and current['quiescent'] and current['metadata']['native_returncode'] == 0
    returncode = native.collect(original_handle).returncode
    bundle = json.loads((Path(plan['attempt_directory']) / 'outputs/bundle.json').read_text())
    validate_atac_native_bundle(bundle, plan=plan)
    save('prepared_native_pins_before.json', json.loads((prior / 'prepared_native_pins_before.json').read_text()))
    save('native-success-plan.json', plan)
    save('native-success-start-receipt.json', receipt)
    save('native-success-closure.json', view)
    print(json.dumps(dict(resumed_original_handle=str(original_handle.path), native_returncode=returncode)), flush=True)
else:
    assert len(sys.argv) == 1
    software = freeze_atac_native_software_binding(module_root=str(SNAPSHOT),
        snapshot_directory=str(ATTEMPT / 'driver-source'), native_runtime=native_runtime())
    driver_pins = [pin(Path(software['driver_runtime']['module_root']) / (r['module'].replace('.', '/') + '.py'))
        for r in software['driver_runtime']['implementation_files']]
    driver_pins += [p for d in software['driver_runtime']['dependencies'] for p in d['files']]
    save('software_binding.json', software)
    save('driver_pins_before.json', driver_pins)
    plan, bundle, receipt, view, returncode = launch_selected(selected_job(software), 'native-success')
if '--resume-from' in sys.argv:
    save('software_binding.json', software)
    save('driver_pins_before.json', driver_pins)
assert returncode == 0, view
assert [s['outcome'] for s in bundle['steps']] == ['succeeded'] * 3
assert [r['count'] for r in bundle['depth_selection']['conditions']] == [100, 200]
assert [bundle['steps'][2]['argv'][bundle['steps'][2]['argv'].index(flag) + 1] for flag in ('--d1', '--d2')] == ['0.0001', '0.0002']
store = Store(ATTEMPT / 'store')
start_ref = source_for_artifact(store, store.artifact(canonical(receipt), 'application/json'), provider='native_acceptance')['id']
closure_ref = source_for_artifact(store, store.artifact(canonical(view), 'application/json'), provider='native_acceptance')['id']
captured = capture_atac_native_files(store, original_plan=plan, source_action_receipt_ref=start_ref,
    writer_closure_receipt_ref=closure_ref, driver_started=True)
save('native-capture.json', captured)
assert len(captured['files']) == 31 and all(r['outcome'] == 'verified' for r in captured['files'])
rows = {r['specification']['file_key']: r for r in captured['files']}
for key in ('header1', 'header2'):
    assert Path(rows[key]['retained']['path']).read_bytes() == b'@HD\tVN:1.6\tSO:coordinate\n@SQ\tSN:chrToy\tLN:12000\n'
example = dict(depths=bundle['depth_selection'], conditions=[], tracks={}, native_regions={})
for i, seal in enumerate(bundle['steps'][:2], 1):
    binding = _callpeak_binding(plan, seal)
    reports = {}
    for role, parser in (('peaks_xls', parse_macs2_peaks_xls), ('narrowpeak', parse_macs2_narrowpeak)):
        retained = rows[f'callpeak{i}.{role}']['retained']
        file = retained['file']
        artifact = dict(artifact_ref=file['artifact_ref'], format=file['format'], expected_sha256=file['sha256'],
            expected_size_bytes=file['size_bytes'], supplied_extent='complete', producer_run_ref=seal['producer_ref'],
            producer_outcome='succeeded', writer_closed=True, producer_name='MACS2', producer_version='2.2.9.1',
            producer_source_ref=None, origin='synthetic_engineering_fixture')
        reports[role] = parser(Path(retained['path']).read_bytes(), artifact=artifact, callpeak=binding)
    assert reports['peaks_xls']['reported_numbers']['treatment_total_tags']['value'] == (105 if i == 1 else 200)
    assert reports['narrowpeak']['rows'][0]['display_score'] == (516 if i == 1 else 1045)
    example['conditions'].append(reports)
    for role, expected in (('signal', 110 if i == 1 else 210), ('background', 35 if i == 1 else 69)):
        raw = Path(rows[f'callpeak{i}.{role}']['retained']['path']).read_bytes()
        count = len(raw.splitlines())
        assert count == expected
        example['tracks'][f'callpeak{i}.{role}'] = dict(row_count=count, final_end=int(raw.splitlines()[-1].split(b'\t')[2]))
for role in ('condition1', 'condition2', 'common'):
    raw = Path(rows['bdgdiff.' + role]['retained']['path']).read_bytes()
    native_rows = [line.decode().split('\t') for line in raw.splitlines() if not line.startswith(b'track')]
    example['native_regions'][role] = native_rows
assert example['native_regions']['condition1'][0][1:3] == ['907', '1140']
assert example['native_regions']['condition2'][0][1:3] == ['2915', '3182']
assert example['native_regions']['common'] == [] and rows['bdgdiff.common']['retained']['file']['size_bytes'] == 89
files, logs, available = atac_observed_files(plan, view, log_window_bytes=512, log_roles=('stdout', 'stderr'))
assert available and len(logs) == 8 and all(row['writer_closed'] for row in files)
read_atac_output(plan, path=str(Path(plan['attempt_directory']) / 'outputs/callpeak/c1/stderr.log'), offset=0, limit=128)
save('filled-native-example.json', example)
save('native-observation.json', dict(outputs=files, logs=logs, result_available=available))

# An explicitly selected second test uses a contradictory source pin. It is
# not a retry and must launch no MACS2 commands or substitute current source.
changed = deepcopy(software)
changed['driver_runtime']['implementation_files'][0]['sha256'] = '0' * 64
bad_plan, bad_bundle, _, _, bad_rc = launch_selected(selected_job(changed), 'source-pin-rejection')
assert bad_rc == 1 and [s['outcome'] for s in bad_bundle['steps']] == ['not_run'] * 3
assert any(row['code'] == 'native_dependency_unavailable' for row in bad_bundle['failures'])
assert all(s['started_at'] is None for s in bad_bundle['steps'])
native_before = json.loads((ATTEMPT / 'prepared_native_pins_before.json').read_text())
assert [pin(row['path']) for row in native_before] == native_before
assert [pin(row['path']) for row in driver_pins] == driver_pins
save('prepared_native_pins_after.json', native_before)
save('driver_pins_after.json', driver_pins)
save('native-acceptance.json', dict(native_returncode=returncode, command_outcomes=[s['outcome'] for s in bundle['steps']],
    verified_capture_occurrences=len(captured['files']), original_header_bytes=48,
    postfilter_depths=[100, 200], cli_depths=['0.0001', '0.0002'], original_native_coordinate_defect_retained=True,
    source_pin_rejection_outcomes=[s['outcome'] for s in bad_bundle['steps']], source_pins_unchanged=True,
    native_pins_unchanged=True, episode_return_verified=False))
print(json.dumps(dict(native_acceptance='passed', postfilter_depths=[100, 200], capture_occurrences=31)), flush=True)
