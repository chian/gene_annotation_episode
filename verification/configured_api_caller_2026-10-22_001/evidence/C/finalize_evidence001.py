"""Stdlib-only post-invocation custody evidence; no application/SQLite opens."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

ROOT = Path('/tmp/scientific-checkpoint-c006-evidence-20261022-001')
CHECKOUT = Path('/tmp/gene-annotation-configured-caller-20261022-006')
PYTHON = '/home/chia/repos/gene_annotation_episode/.venv/bin/python'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    path = ROOT/name
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return {'path': str(path), 'sha256': digest(path), 'bytes': path.stat().st_size}


selections = {
    'first': 'tests/test_scientific_checkpoint_fork.py::test_success_exact_checkpoint_and_actual_lineage_readers',
    'second': 'tests/test_scientific_checkpoint_fork.py::test_success_exact_checkpoint_and_actual_lineage_readers',
    'group1': 'tests/test_scientific_checkpoint_fork.py',
    'group2': 'tests/test_scientific_checkpoint_fork.py',
    'memory-first': 'tests/test_scientific_checkpoint_fork.py::test_success_exact_checkpoint_and_actual_lineage_readers tests/test_scientific_checkpoint_fork.py::test_packed_component_corruption_is_not_materialized_or_repaired \'tests/test_scientific_checkpoint_fork.py::test_actual_destination_constructor_must_not_change_schema_or_old_data[table]\'',
    'group3': 'tests/test_scientific_checkpoint_fork.py',
    'packed-first': 'tests/test_scientific_checkpoint_fork.py::test_actual_packed_target_member_reuses_materialized_sequence_without_row_rewrite',
    'packed-second': 'tests/test_scientific_checkpoint_fork.py::test_actual_packed_target_member_reuses_materialized_sequence_without_row_rewrite',
    'corrections': 'tests/test_scientific_checkpoint_fork.py::test_actual_packed_target_member_reuses_materialized_sequence_without_row_rewrite tests/test_scientific_checkpoint_fork.py::test_replaced_working_inode_is_checked_before_truncation tests/test_scientific_checkpoint_fork.py::test_parent_replacement_between_validation_and_open_creates_no_stage tests/test_scientific_checkpoint_fork.py::test_fd_stage_and_actual_memory_store_resist_parent_replacement',
    'final': 'tests/test_scientific_checkpoint_fork.py',
    'late-first': 'tests/test_scientific_checkpoint_fork.py::test_late_observed_database_change_cannot_be_labelled_preserved',
    'late-final': 'tests/test_scientific_checkpoint_fork.py::test_late_observed_database_change_cannot_be_labelled_preserved tests/test_scientific_checkpoint_fork.py::test_success_exact_checkpoint_and_actual_lineage_readers tests/test_scientific_checkpoint_fork.py::test_published_location_unknown_never_uses_guessed_path_or_hides_fsync_failure',
}
seconds = {'first': 1.92, 'second': 5.43, 'group1': 117.20, 'group2': 179.15,
    'memory-first': 16.97, 'group3': 238.77, 'packed-first': 1.51,
    'packed-second': 6.85, 'corrections': 33.41, 'final': 257.74,
    'late-first': 12.09, 'late-final': 28.99}
invocations = []
for label, selection in selections.items():
    base = '/tmp/scientific-checkpoint-c006-'+label+'-20261022-001'
    # These first two commands had the original option order recorded here.
    options = (' --basetemp='+base+' -q') if label in {'first', 'second'} else (' -q --basetemp='+base)
    command = PYTHON+' -m pytest '+selection+options+' --junitxml='+str(ROOT/(label+'.xml'))+' > '+str(ROOT/(label+'.log'))+' 2>&1'
    cases = list(ET.parse(ROOT/(label+'.xml')).iter('testcase'))
    failures = [c for c in cases if c.find('failure') is not None]
    errors = [c for c in cases if c.find('error') is not None]
    skips = [c for c in cases if c.find('skipped') is not None]
    invocations.append({'label': label, 'shell_command': command, 'cwd': str(CHECKOUT),
        'basetemp': base, 'basetemp_was_unique_explicit': True,
        'exit_code': int(bool(failures or errors)), 'test_nodes': len(cases),
        'passed': len(cases)-len(failures)-len(errors)-len(skips), 'failures': len(failures),
        'errors': len(errors), 'skipped': len(skips), 'pytest_reported_seconds': seconds[label],
        'log': {'path': str(ROOT/(label+'.log')), 'sha256': digest(ROOT/(label+'.log'))},
        'xml': {'path': str(ROOT/(label+'.xml')), 'sha256': digest(ROOT/(label+'.xml'))},
        'node_ids': [c.attrib.get('classname', '')+'::'+c.attrib['name'] for c in cases]})

guard = json.loads((ROOT/'FINAL_GUARD001.json').read_bytes())
runtime = {r['path']: r['sha256'] for r in guard['files']}
clone_checks = []
for directory in sorted(Path('/tmp/scientific-checkpoint-c006-late-final-20261022-001').glob('test_*/original')):
    if directory.parent.is_symlink():
        continue
    actual = {str(p.relative_to(directory)): digest(p) for package in ('gene_annotation_episode', 'method_loop')
        for p in (directory/package).rglob('*.py')}
    assert actual == runtime
    binding = json.loads((directory/'case/runs/stopped/episode-execution-binding.json').read_bytes())
    assert binding['implementation_sha256'] == guard['implementation_sha256']
    clone_checks.append({'source_fixture': str(directory), 'runtime_files': len(actual),
        'runtime_bytes_equal_final': True, 'saved_binding_pin_equal_final': True})
assert len(clone_checks) == 5
input_receipt = write('POST_FIX_INPUT_RECEIPT001.json', {
    'verification_timing': 'post_invocation_stdlib_verification',
    'not_a_fabricated_pre_run_guard': True,
    'final_guard': {'path': str(ROOT/'FINAL_GUARD001.json'), 'sha256': digest(ROOT/'FINAL_GUARD001.json')},
    'in_invocation_source_authority_copies': clone_checks,
    'source_and_test_held_unchanged_during_late_final_invocation': True,
    'owned_test_sha256': guard['owned_test']['sha256']})

result = {'version': 'scientific_checkpoint_c006_component_evidence_v1',
    'checkout': str(CHECKOUT), 'production_and_test_frozen': True,
    'final_runtime_file_count': guard['runtime_files'], 'final_implementation_sha256': guard['implementation_sha256'],
    'owned_runtime': next(r for r in guard['files'] if r['path'].endswith('/scientific_checkpoint_fork.py')),
    'owned_test': guard['owned_test'],
    'baseline_guard': {'runtime_and_test_files': 348, 'static_assets': 319, 'mismatches': 0,
        'path': str(ROOT/'FINAL_GUARD001.json'), 'sha256': digest(ROOT/'FINAL_GUARD001.json')},
    'authority': {'scope001_sha256': 'a0bea99e80848a0f1c1c7bba00a586a363737bd430c0da39628146191f721573',
        'scope002_sha256': 'f64a3af66db132cfea895e50e2fc155ffc5dbc9c77cf926886bc7ac02929cc40',
        'schema_sha256': guard['new_schema_sha256']},
    'historical_full_suite': {'invocation': 'final', 'passed': 56, 'seconds': 257.74,
        'runtime_module_sha256': 'cce9936cf502be683d32ee0606844b063eb02a6f0a68e60e5d02cdb8d5fbb2ec',
        'implementation_sha256': 'd115a648ec79320ac2b5895a4c4d6e184bee07f2877ac63c82399d8902925e2a',
        'preserved_inputs_and_fixture': str(ROOT/'cce993-full56-001'),
        'not_a_full_suite_at_final_source': True},
    'final_focused_verification': {'invocation': 'late-final', 'passed': 5, 'seconds': 28.99,
        'scope': ['two actual late source database changes rejected', 'normal full checkpoint/lineage/readers/modes',
            'published location unknown with and without parent fsync failure'],
        'input_receipt': input_receipt},
    'counts_must_not_be_added_across_overlapping_invocations_or_pins': True,
    'historical_limit': 'group2 ran before final source freeze and one fixture copied an earlier authority while source files changed; its results are historical only',
    'late_defect': {'reproduced_invocation': 'late-first', 'failing_nodes': 2,
        'change': 'reject observed before/after DB/sidecar witness differences, source_changed/False, no publication'},
    'raw_fixture_receipts': [{'path': str(ROOT/name), 'sha256': digest(ROOT/name)} for name in
        ('SECOND_FIXTURE_RECEIPT.json', 'CORRECTION_FIXTURES_RECEIPT.json', 'POST_FIX_FIXTURE_RECEIPT001.json')],
    'invocations': invocations,
    'limits': ['Synthetic fixtures only; no original scientific database opened or forked.',
        'No model/public HTTP/native program launched. Pure fixture translation and synthetic native receipt construction are explicit.',
        'No original source factory or scoring/controller replay in custody.',
        'Historical run journals remain old; retained relocated raw databases are not asserted self-contained resumable.',
        'Final source has focused affected verification; historical full56 is a separately pinned earlier source.',
        'Root owns joined caller/worker verification and final publication; no overall scientific completion claim.']}
receipt = write('RESULTS001.json', result)
print(json.dumps(receipt))
