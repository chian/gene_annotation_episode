"""Record verified return-repair composition and the isolated Cutadapt parser."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
V = ROOT / 'verification'
A = V / 'tool_graders_verified_return_repairs_application_2026-10-25_206'
F = V / 'tool_graders_bvbrc_fastqutils_remaining_formats_2026-10-25_204'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reports(paths):
    return [{'path': str(path.relative_to(ROOT)), 'sha256': sha(path)} for path in paths]


raw = STATUS.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '50a1833192a185b200f0bd0fd1ea4c3a3fe276e8c7730b442ad114c388e8ef80'
assert not (HERE / 'PROGRESS_UPDATE_045.json').exists()
work = json.loads(raw)
original = deepcopy(work)
scope_path = HERE / work['scope_file']
scope = read(scope_path)
scope_hash = sha(scope_path)
audit = read(A / 'COMPOSITION_FINAL_AUDIT_001.json')
seal = read(A / 'COMPOSITION_SEAL_RECEIPT_001.json')
assert audit['exit_code'] == seal['exit_code'] == 0
assert audit['distinct_passing_cases'] == 7
assert audit['previously_failing_host_case_passed']
assert audit['candidate_common_production_hashes_equal']
assert audit['production_paths_unchanged'] == 1046
assert audit['frozen_candidate_paths_unchanged'] == 1054
assert not audit['production_mutated_by_verifier']
assert audit['saved_replay']['new_http_calls'] == 0
for name, digest in seal['key_receipts_sha256'].items():
    assert sha(A / name) == digest
for name, digest in read(A / 'APPLICATION_AFTER_001.json').items():
    assert sha(ROOT / name) == digest
assert sum(e['action_count'] for e in audit['episodes'].values()) == 26
assert sum(e['observation_count'] for e in audit['episodes'].values()) == 26
for role, gain in (('launch', 2), ('launch_api', 2), ('results', 3)):
    episode = audit['episodes'][role]
    assert episode['actual_marginal_gains'][-1] == gain
    assert episode['final_expected_next_gain']['value'] == 0
    assert episode['final_expected_next_gain']['upper'] == 0
for path, count in ((A / 'composition_checks_001/tests.xml', 7),
                    (F / 'provider_development_001.xml', 5)):
    cases = list(ET.parse(path).iter('testcase'))
    assert len(cases) == count
    assert all(c.find(k) is None for c in cases for k in ('failure', 'error', 'skipped'))
parser = read(F / 'parser_205/test_result_001.json')
assert parser['exit_code'] == 0 and parser['stdout_summary'] == '77 passed in 7.38s'
assert sha(F / 'candidate/gene_annotation_episode/bvbrc_fastqutils_cutadapt_reader.py') == parser['parser_sha256']
assert sha(F / 'candidate/tests/test_bvbrc_fastqutils_cutadapt_reader.py') == parser['tests_sha256']

composition = {
    'id': 'TYPED-RETURN-AND-GENOME-REPAIR-COMPOSITION-045',
    'kind': 'applied_composition_verified_with_seven_targeted_cases_and_fresh_registry_bindings',
    'summary': 'The exact applied197+203 composition passed the original failing public GenomeAlignment '
        'resolver case and all six unchanged GenomeAlignment Workflow cases in804.130 seconds. '
        'All1054 frozen candidate paths,1046 common production paths and five original application '
        'files remained unchanged. Fresh candidate and production processes agreed on all nine '
        'registry pins. The controlled Workflow returned690/693 and measured zero gaps through '
        'results, scientific child and root. Saved recalculation produced677/693 without acquisition '
        'or native parsing; saved replay made zero new HTTP calls and preserved original actions.',
    'qualification': 'The seven cases are bounded composition coverage, not a new whole-tool claim '
        'or a disjoint addition to historical suites.26 own actions produced26 observations across '
        '27 model calls. Practical final marginal gains2,2,3 are preserved with exact-zero future '
        'expectations. Scientific/root credit was controlled zero; their choices and HTTP service '
        'were fixtures. No configured-model investigation or live BV-BRC deployment is claimed. '
        'The original pending-composition receipt and failed first verification pin probe remain '
        'unchanged. Proteome/ComparativeSystems historical Workflow evidence remains separate; '
        'their new composition checks were registry/pin binding, not repeated full Workflow runs.',
    'reports': reports([A / 'FINAL_COMPOSITION_VERIFICATION_001.md',
        A / 'COMPOSITION_SEAL_RECEIPT_001.json', A / 'COMPOSITION_FINAL_AUDIT_001.json',
        A / 'COMPOSITION_WORKFLOW_ACCOUNTING_001.json', A / 'COMPOSITION_COMMANDS_001.json',
        A / 'COMPOSITION_PRODUCTION_PINS_002.json', A / 'COMPOSITION_CANDIDATE_PINS_002.json',
        A / 'composition_checks_001/tests.xml'])}

cutadapt = {
    'id': 'FASTQUTILS-CUTADAPT-PARSER-AND-PROVIDER-045',
    'kind': 'isolated_native_parser_and_provider_projection_verified_complete_package_composition_pending',
    'summary': 'The completed isolated embedded Cutadapt4.9 parser passed77 focused tests, with '
        '30 actual small Cutadapt runs and one genuine Trim Galore report. It preserves all23 '
        'native metric types, invocation and mate populations, adapter event counts and original '
        'byte locations. Five root provider/return-codec development tests passed: embedded '
        'Cutadapt4 reads/28 bases remain separate from final FASTQ3 reads/24 bases, requested '
        'retention is28/58, absent lineage cannot be inferred from filenames/recipe, and '
        'partial/wrong-version reports preserve independent valid final-read measurements.',
    'qualification': 'Bare Cutadapt direct-helper fixtures were relabelled truthfully as Cutadapt '
        'native text; historical evidence_001 is unchanged and corrected exports are evidence_002. '
        'That does not implement standalone Cutadapt dispatch. Native named discard counters '
        'were omitted by actual producer runs and are source-grammar fixture tests only. '
        'Root read the full final parser and verified final parser/test hashes. The all-Fastq '
        'frozen composition and updated wheel are undergoing separate208 verification. '
        'Existing202 full episode work continues on its original candidate. No production '
        'Fastq application, complete new episode custody path or live BV-BRC claim. '
        'SAMstat, SRA metadata and other producer versions remain unfinished.',
    'reports': reports([F / 'parser_205/HANDOFF_001.md', F / 'parser_205/test_result_001.json',
        F / 'parser_205/PROVENANCE_CORRECTION_001.md', F / 'parser_205/evidence_002/manifest.json',
        F / 'parser_205/native_examples_001/receipt.json',
        F / 'parser_205/native_examples_002/receipt.json',
        F / 'parser_205/native_examples_003/receipt.json', F / 'provider_development_001.xml'])}

for evidence in (composition, cutadapt):
    assert evidence['id'] not in {e['id'] for e in work['verification_evidence']}
    work['verification_evidence'].append(evidence)
targets = {'C-L202-GenomeAlignment', 'C-L206-GenomeComparison', 'C-L207-ComparativeSystems'}
for group in ('rows', 'resource_bindings'):
    for row in work[group]:
        base_id = row['id'].split('::')[0]
        if base_id in targets:
            row['evidence_ids'].append(composition['id'])
            if base_id == 'C-L202-GenomeAlignment':
                row['integration_verification'] = 'applied_composition_original_failure_and_six_Workflow_cases_passed_typed_returns_saved_replay_and_credit_verified'
                if group == 'rows':
                    row['overall'] = 'requirement_reference_repair_applied_composed_Workflow_verified_live_service_unverified'
            else:
                row['integration_verification'] = 'return_optimization_applied_prior_full_Workflow_verified_composed_fresh_registry_binding_verified'
            if group == 'rows':
                row['note'] += ' Update045: ' + composition['summary'] + ' ' + composition['qualification']
        elif base_id == 'C-L209-FastqUtils':
            row['evidence_ids'].append(cutadapt['id'])
            row['native_parser'] = 'candidate_existing_native_formats_and_embedded_Cutadapt4point9_tested_SAMstat_SRA_and_other_versions_unfinished'
            if group == 'rows':
                row['note'] += ' Update045: ' + cutadapt['summary'] + ' ' + cutadapt['qualification']

changes = []
for group, count in (('rows', 308), ('resource_bindings', 288)):
    assert len(work[group]) == count
    assert [r['id'] for r in work[group]] == [r['id'] for r in original[group]] == [r['id'] for r in scope[group]]
    previous = {r['id']: r for r in original[group]}
    changes += [{'group': group, 'id': r['id'], 'before': previous[r['id']], 'after': deepcopy(r)}
                for r in work[group] if r != previous[r['id']]]
assert len(changes) == 8 and work['complete_scientific_tools_claimed'] == 0
assert sha(scope_path) == scope_hash
updated = (json.dumps(work, indent=2) + '\n').encode()
record = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-25',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': hashlib.sha256(raw).hexdigest(),
    'new_status_sha256': hashlib.sha256(updated).hexdigest(),
    'scope_sha256_unchanged': scope_hash, 'scope_changes': False, 'changes': changes,
    'added_evidence': [composition, cutadapt], 'inventory_maintenance_counted_as_implementation_progress': False,
    'specific_pending_NCBI_job_verification_included': False, 'complete_scientific_tools_claimed': 0}
with (HERE / 'PROGRESS_UPDATE_045.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
STATUS.write_bytes(updated)
print(json.dumps({'checkpoint': 45, 'changed_rows_and_bindings': len(changes),
                  'status_sha256': record['new_status_sha256']}))
