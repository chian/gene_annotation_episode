"""Append verified SAMstat parsing and combined142-case evidence; keep scope."""
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


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def reports(base, names):
    return [dict(path=str((base / n).relative_to(ROOT)), sha256=sha(base / n)) for n in names]


def passed_xml(path, count):
    cases = list(ET.parse(path).iter('testcase'))
    assert len(cases) == count
    assert all(c.find(k) is None for c in cases for k in ('failure', 'error', 'skipped'))


raw = STATUS.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '955d05163451ae13d8d771f50c08a76d25fce7cb4d9845bb920b72a113497221'
assert not (HERE / 'PROGRESS_UPDATE_047.json').exists()
work = json.loads(raw)
original = deepcopy(work)
scope_path = HERE / work['scope_file']
scope, scope_hash = read(scope_path), sha(scope_path)

p = V / 'tool_graders_fastqutils_samstat_implementation_2026-10-25_212'
manifest = read(p / 'COMMON_CONTRACT_MANIFEST_003.json')
for item in manifest['owned_files']:
    assert sha(p / 'candidate' / item['path']) == item['after_sha256']
assert read(p / 'FINAL_SCOPED_TESTS_002.json')['exit_code'] == 0
passed_xml(p / 'FINAL_SCOPED_TESTS_002.xml', 56)
current = dict(id='FASTQUTILS-SAMSTAT-CURRENT-PARSER-047',
    kind='current_native_parser_and_shared_finite_contracts_implemented_tested',
    summary='Current2.5 parser and shared contracts are implemented. The final focused56 cases passed. '
        'Native examples preserve total10, bins4/3/2/1, MeanQ16.2, Q0/Q40 nativeMeanQ3.0, '
        'exact10001 despite a10.0k display, rounded length summaries, and unknown-mode empty counts. '
        'The caller error has one failed sentinel; missing SVG arrays are not reconstructed.',
    qualification='This is a parser/shared-contract delivery, not the separate SAMstat calculator, '
        'full provider/episode integration or live BV-BRC. Exact198/208 grammar assets and prior tests '
        'remain unchanged. Earlier74 contract/return tests overlap the final56 and are not added.',
    reports=reports(p, ['HANDOFF_003.md', 'COMMON_CONTRACT_MANIFEST_003.json',
        'FINAL_AUDIT_003.json', 'NUMERICAL_EXAMPLES_003.json',
        'FINAL_SCOPED_TESTS_002.json', 'FINAL_SCOPED_TESTS_002.xml']))

p = V / 'tool_graders_fastqutils_samstat_legacy_2026-10-25_213'
manifest = read(p / 'IMPLEMENTATION_HANDOFF_002.json')
for path, expected in manifest['owned_code'].items():
    assert sha(ROOT / path) == expected
for item in manifest['native_documents']:
    assert sha(ROOT / item['fixture']) == item['sha256']
assert manifest['fixture_count'] == 20
assert '57 passed' in (p / 'PYTEST_ATTEMPT_007.log').read_text()
legacy = dict(id='FASTQUTILS-SAMSTAT-LEGACY-PARSER-047',
    kind='legacy_native_parser_implemented_and_source_executed_examples_preserved',
    summary='Legacy2.2.3 parser passed57 focused tests. Twenty native reports retain6547 cells '
        'across all37 legacy metrics. Exact totals, native rounded displays, density rather than '
        'counts, native quality defects, clustered means and absent coordinates remain distinct. '
        'Additional native executions establish optional missing-QUAL and clustered/error cases.',
    qualification='Local tiny source-executed examples, not BV-BRC deployment. The initial library '
        'loading failures and later test failures remain recorded. This leaf delivery does not '
        'implement the mapping calculator or establish production installation/episode integration.',
    reports=reports(p, ['FINAL_EVIDENCE_REPORT_001.md', 'IMPLEMENTATION_HANDOFF_002.json',
        'SOURCE_CLARIFICATION_001.md', 'PYTEST_ATTEMPT_007.log',
        'NATIVE_RUN_RECEIPTS_001.json', 'NATIVE_RUN_RECEIPTS_002.json', 'NATIVE_RUN_RECEIPTS_003.json']))

p = V / 'tool_graders_fastqutils_combined_2026-10-25_216'
r = read(p / 'parser_checks_001/receipt.json')
assert r['passed'] and r['exit_code'] == 0 and not r['changed_sources']
assert r['source_file_count'] == 1162 and not r['calculator214_included']
before = read(p / 'parser_checks_001/source_before.json')
assert before == read(p / 'parser_checks_001/source_after.json')
for path, expected in before.items():
    assert sha(p / 'candidate_002' / path) == expected
passed_xml(p / 'parser_checks_001/results.xml', 142)
combined = dict(id='FASTQUTILS-SRA-SAMSTAT-PARSER-COMPOSITION-047',
    kind='combined_schema_parser_and_provider_examples_verified_calculator_integration_pending',
    summary='Root combined completed211/212/213 parser deliveries over exact208. All142 cases '
        'passed in33.55 pytest seconds; all1162 source/input files were unchanged. One shared '
        'provider test preserves SRA values2673129532/35172757/937094000/76/1 and legacy/current '
        'SAMstat totals11/10 without conflating source populations, versions or library links. '
        'All37 overlapping finite enum locations were explicitly merged; old198/208 assets retained.',
    qualification='142 includes the earlier28 SRA,56 current/shared and57 legacy cases plus one '
        'new composition test. It is not an extra142 unique cases. The first composition attempt '
        'stopped at an optional-schema branch conflict and remains recorded. SAMstat calculators, '
        'combined host/Workflow verification, installed package and production application remain '
        'unfinished. No live service or new native producer execution occurred in216.',
    reports=reports(p, ['COMPOSITION_CONTRACT_001.md', 'PARSER_COMPOSITION_ATTEMPT_001.json',
        'PARSER_COMPOSITION_001.json', 'PARSER_INPUTS_001.json',
        'parser_checks_001/receipt.json', 'parser_checks_001/results.xml',
        'parser_checks_001/source_before.json', 'parser_checks_001/source_after.json']))

evidence = [current, legacy, combined]
assert not {e['id'] for e in evidence} & {e['id'] for e in work['verification_evidence']}
work['verification_evidence'].extend(evidence)
for group in ('rows', 'resource_bindings'):
    for row in work[group]:
        if row['id'].split('::')[0] != 'C-L209-FastqUtils':
            continue
        row['evidence_ids'].extend(e['id'] for e in evidence)
        row['native_parser'] = 'SRA_and_versioned_SAMstat_parsers_implemented_combined142cases_passed_production_unapplied'
        row['numerical_verification'] = '208baseline359cases_and216combined_parser142cases_passed_separately_SAMstat_calculation_pending'
        if group == 'rows':
            row['overall'] = 'candidate_parsers_SRA_SAMstat_composed_verified_calculators_and_production_pending'
            row['note'] += ' Update047: ' + ' '.join(e['summary'] + ' ' + e['qualification'] for e in evidence)
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
record = dict(schema='tool_grader_progress_update_v1', date='2026-10-25',
    recorded_at=datetime.now(timezone.utc).isoformat(), author='root',
    previous_status_sha256=hashlib.sha256(raw).hexdigest(), new_status_sha256=hashlib.sha256(updated).hexdigest(),
    scope_sha256_unchanged=scope_hash, scope_changes=False, changes=changes, added_evidence=evidence,
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False, complete_scientific_tools_claimed=0)
with (HERE / 'PROGRESS_UPDATE_047.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
STATUS.write_bytes(updated)
print(json.dumps(dict(checkpoint=47, changed_rows_and_bindings=len(changes), status_sha256=record['new_status_sha256'])))
