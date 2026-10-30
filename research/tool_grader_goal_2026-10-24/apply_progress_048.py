"""Record reviewed SAMstat calculations, SRA host proof and exact composition."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V = ROOT / 'verification'
STATUS = HERE / 'WORK_STATUS.json'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reports(base, names):
    return [dict(path=str((base / n).relative_to(ROOT)), sha256=sha(base / n)) for n in names]


raw = STATUS.read_bytes()
assert hashlib.sha256(raw).hexdigest() == 'ea01d5b1b3a360e3cd4804261b305eef8ef9de87cf3ab5a44e3fd859c590fc2b'
assert not (HERE / 'PROGRESS_UPDATE_048.json').exists()
work = json.loads(raw)
original = deepcopy(work)
scope_path = HERE / work['scope_file']
scope, scope_hash = read(scope_path), sha(scope_path)

p = V / 'tool_graders_fastqutils_samstat_calculation_2026-10-25_214'
h = read(p / 'IMPLEMENTATION_HANDOFF_001.json')
assert len(h['owned_changes']) == 18 and not h['outside_owned_changes']
for item in h['owned_changes']:
    assert sha(ROOT / h['candidate'] / item['path']) == item['after_sha256']
for path, expected in read(ROOT / h['final_source_manifest']['path']).items():
    assert sha(ROOT / h['candidate'] / path) == expected
r = read(p / 'FINAL_SCOPED_TESTS_001.json')
assert r['exit_code'] == 0 and r['source_unchanged'] and not r['changed_files']
assert '220 passed, 1 deselected' in (p / 'FINAL_SCOPED_TESTS_001.log').read_text()
calculation = dict(id='FASTQUTILS-SAMSTAT-CALCULATION-048',
    kind='reported_alignment_record_fractions_and_saved_recalculation_implemented_tested',
    summary='Scoped214 implemented two explicit report-record fractions, declaration resolution, '
        'saved version validation and scoped failure projection. Final verification passed220 '
        'cases:61 new and159 prior cases. Native legacy10/11 and5/11, current9/10 and4/10 '
        'retain bins, denominators, versions, unknown original-input scope and MAPQ255 limits. '
        'Saved R1 recalculation yields8/9 and4/9 without parsing or acquisition.',
    qualification='One unchanged stale dependency-count test was explicitly deselected in214; '
        'the newly delivered calculator was not yet in that candidate dependency manifest. '
        'Root216 fixes both before combined verification. These are scoped component/provider '
        'tests, not live execution, Workspace custody or complete episode-path proof.',
    reports=reports(p, ['IMPLEMENTATION_HANDOFF_001.json', 'IMPLEMENTATION_MANIFEST_001.json',
        'FINAL_EVIDENCE_REPORT_001.md', 'FINAL_SCOPED_TESTS_001.json',
        'FINAL_SCOPED_TESTS_001.log', 'FINAL_SCOPED_TESTS_001_SOURCE.json',
        'NUMERICAL_EVIDENCE_002.json', 'DEPENDENCY_INTEGRATION_LIMIT_001.json']))

p = V / 'tool_graders_fastqutils_sra_host_2026-10-25_215'
r = read(p / 'FINAL_RECEIPT_001.json')
assert r['passed'] and r['test_passes'] == 1 and r['runtime_observations'] == 0
assert r['selected_action_count'] == 15 and r['rejection_count'] == 3
assert r['numerical_values'] == dict(total_bases=2673129532, total_spots=35172757,
    size=937094000, read_length=76.0, n_reads=1)
for filename, expected in r['files'].items():
    assert sha(p / filename) == expected
manifest = read(p / 'FINAL_FILES_001.json')
assert len(manifest) == 1344
for filename, expected in manifest.items():
    assert sha(p / filename) == expected
cases = list(ET.parse(p / 'host_run_001/results.xml').iter('testcase'))
assert len(cases) == 1 and all(c.find(k) is None for c in cases for k in ('failure', 'error', 'skipped'))
host = dict(id='FASTQUTILS-SRA-SELECTED-HOST-048',
    kind='actual_host_custody_publication_saved_reconstruction_and_two_receiving_boundaries_verified',
    summary='The first215 focused host run passed. Actual selected material.parse, AppService '
        'prepare/submit/status and Workspace acquisition published five retained native SRA '
        'quantities2673129532/35172757/937094000/76/1. All26 labels remain. Two receiving '
        'boundaries preserved values; saved returns made zero forbidden calls with42 entrypoints '
        'disabled. Forged900 was rejected by owner and both receivers.',
    qualification='Controlled task/service transport;15 manual selected actions and0 runtime '
        'observations. No method_loop/controller or live-service proof. n_reads is reported '
        'read types per spot, not total reads; unknown producer/basis and absent associations '
        'stay unknown. The test used exact211 scientific code, not the later216 composition.',
    reports=reports(p, ['HANDOFF_001.md', 'FINAL_RECEIPT_001.json', 'FINAL_FILES_001.json',
        'NUMERICAL_EXAMPLE_001.json', 'host_run_001/receipt.json',
        'host_run_001/results.xml', 'host_run_001/evidence/typed_returns.json']))

p = V / 'tool_graders_fastqutils_combined_2026-10-25_216'
r = read(p / 'CALCULATOR_COMPOSITION_003.json')
assert r['delivery_paths'] == 18 and r['dependency_count'] == 36
assert r['total_tracked_paths'] == 1176 and not r['production_changed']
manifest = read(p / 'combined_source_before_003.json')
for filename, expected in manifest.items():
    assert sha(p / 'candidate_003' / filename) == expected
composition = dict(id='FASTQUTILS-SRA-SAMSTAT-CALCULATOR-COMPOSITION-048',
    kind='exact_reviewed_deliveries_composed_combined_verification_pending',
    summary='Root216 composed all18 immutable214 changes with the previously verified SRA '
        'and both SAMstat parsers. The36-file provider dependency closure includes the new '
        'calculator; the provider test now checks the current dependency set with no planned '
        'deselection. Tool instructions distinguish report-record fractions from original-read '
        'coverage and describe supported native versions and missing SVG arrays.',
    qualification='The1176-file composed candidate is frozen. Fresh217 owns all20 affected '
        'suites and installed-package verification; fresh218 owns SAMstat selected host and '
        'shared-Workflow verification. No outcome of those pending tests is claimed here. '
        'Production application remains unfinished; the earlier202 frozen208 invocation is '
        'unchanged and has not been replaced or restarted.',
    reports=reports(p, ['COMPOSITION_CONTRACT_001.md', 'PREPARED_CALCULATOR_COMPOSITION_003.json',
        'CALCULATOR_COMPOSITION_003.json', 'combined_source_before_003.json',
        'COMPOSE_CALCULATORS_003.py']))

evidence = [calculation, host, composition]
assert not {e['id'] for e in evidence} & {e['id'] for e in work['verification_evidence']}
work['verification_evidence'].extend(evidence)
for group in ('rows', 'resource_bindings'):
    for row in work[group]:
        if row['id'].split('::')[0] != 'C-L209-FastqUtils':
            continue
        row['evidence_ids'].extend(e['id'] for e in evidence)
        row['numerical_verification'] = '208baseline359_and216parser142_and214scoped220_passed_combined1176file_candidate_verification_pending'
        row['integration_verification'] = '209Cutadapt_and215SRA_actual_host_two_typed_boundaries_verified_202baselineWorkflow_and218SAMstat_pending'
        if group == 'rows':
            row['overall'] = 'candidate_all_delivered_parsers_calculators_composed_package_episode_verification_and_production_pending'
            row['deterministic_calculator'] = 'explicit_composition_quality_original_read_mapping_SAMstat_report_mapping_retention_consistency_implemented_scoped_tests_passed'
            row['note'] += ' Update048: ' + ' '.join(e['summary'] + ' ' + e['qualification'] for e in evidence)
changes = []
for group, count in (('rows', 308), ('resource_bindings', 288)):
    assert len(work[group]) == count
    assert [r['id'] for r in work[group]] == [r['id'] for r in original[group]] == [r['id'] for r in scope[group]]
    previous = {r['id']: r for r in original[group]}
    changes.extend(dict(group=group, id=r['id'], before=previous[r['id']], after=deepcopy(r))
                   for r in work[group] if r != previous[r['id']])
assert len(changes) == 2 and work['complete_scientific_tools_claimed'] == 0
assert sha(scope_path) == scope_hash
updated = (json.dumps(work, indent=2) + '\n').encode()
record = dict(schema='tool_grader_progress_update_v1', date='2026-10-26',
    recorded_at=datetime.now(timezone.utc).isoformat(), author='root',
    previous_status_sha256=hashlib.sha256(raw).hexdigest(), new_status_sha256=hashlib.sha256(updated).hexdigest(),
    scope_sha256_unchanged=scope_hash, scope_changes=False, changes=changes, added_evidence=evidence,
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False, complete_scientific_tools_claimed=0)
with (HERE / 'PROGRESS_UPDATE_048.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
STATUS.write_bytes(updated)
print(json.dumps(dict(checkpoint=48, changed_rows_and_bindings=len(changes), status_sha256=record['new_status_sha256'])))
