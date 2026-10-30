"""Append verified work and unresolved failures without changing inventory scope."""
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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def report(path):
    return {'path': path, 'sha256': sha(ROOT / path)}


raw = STATUS.read_bytes()
assert hashlib.sha256(raw).hexdigest() == 'cdba13b82eb253276f95a35bd9a5700610c444bbcdfb36579dbf0f075fcd8ce2'
assert not (HERE / 'PROGRESS_UPDATE_040.json').exists()
work = json.loads(raw)
original = deepcopy(work)
scope_path = HERE / work['scope_file']
scope_sha = sha(scope_path)
scope = json.loads(scope_path.read_text())
authority = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
assert sha(authority) == work['authority_sha256']
p = 'verification/tool_graders_bvbrc_proteome_directional_integration_2026-10-25_182/'
c = 'verification/tool_graders_bvbrc_comparative_systems_implementation_2026-10-25_186/'
application = 'verification/tool_graders_bvbrc_comparative_systems_application_2026-10-25_196/'
performance = 'verification/tool_graders_typed_return_performance_2026-10-25_197/'
f = 'verification/tool_graders_bvbrc_fastqutils_implementation_2026-10-25_198/'
for name, value in read(p + 'BASELINE_001.json').items():
    assert sha(ROOT / name) == value, name
assert not (ROOT / (p + 'APPLICATION_RECEIPT_001.json')).exists()
cw = read(c + 'final_workflow_001/receipt.json')
assert cw['passed'] and cw['exit_code'] == 0 and not cw['changed_sources'] and cw['source_count'] == 1045
assert cw['case_counts'] == {'passed': 1, 'failed': 0, 'error': 0, 'skipped': 0}
a = read(f + 'evidence_root_mapping_001/receipt.json')
assert a['exit_code'] == 0 and not a['changed_during_test']
b = read(f + 'evidence_b/TERMINAL_RECEIPT_FINAL.json')
assert b['exit_code'] == 0 and b['dependencies_unchanged_during_run']
assert b['junit_summary']['tests'] == '75' and all(b['junit_summary'][key] == '0' for key in ('failures', 'errors', 'skipped'))
assert b['dependency_hashes_before'] == b['dependency_hashes_after']
for item in b['dependency_hashes_after']:
    if item['path'].endswith('/gene_annotation_episode/bvbrc_fastqutils_contracts.py'):
        assert item['sha256'] == read(f + 'evidence_contract_order_001/before.json')['gene_annotation_episode/bvbrc_fastqutils_contracts.py']
    else:
        assert sha(ROOT / item['path']) == item['sha256'], item['path']
cp = read(f + 'evidence_c/frozen_001/VERIFICATION_RECEIPT.json')
assert cp['exit_code'] == 0 and not cp['concurrent_changes'] and cp['scientific_dependency_count'] == 24
assert cp['implementation_sha256'] == '72a25500a523a2c354529ec5e34f73d1c5e448ba0b9b95497ed1ef79999f0ae4'
assert cp['junit'][0]['tests'] == '86' and all(cp['junit'][0][key] == '0' for key in ('failures', 'errors', 'skipped'))
root_test = read(f + 'evidence_root_returns_003/receipt.json')
assert root_test['exit_code'] == 0 and not root_test['frozen']
assert root_test['changed_sources'] == ['tests/fixtures/bvbrc_fastqutils/bundle/fixture_support.py']
cases = list(ET.parse(ROOT / (f + 'evidence_root_returns_003/tests.xml')).iter('testcase'))
assert len(cases) == 30 and not any(case.find(tag) is not None for case in cases for tag in ('failure', 'error', 'skipped'))
assert read(performance + 'baseline_fixture_001/receipt.json')['exit_code'] == 1
assert 'bvbrc_genome_alignment_provider_requirement_reference_unknown' in (ROOT / (performance + 'baseline_fixture_001/output.log')).read_text()
regression = read(performance + 'regressions_001/receipt.json')
assert regression['exit_code'] == 1
assert read(performance + 'fixture_comparison_001/receipt.json')['exit_code'] == 0
assert read(performance + 'minhash_accounting_001/receipt.json')['exit_code'] == 0

comparative = {
    'id': 'COMPARATIVE-SYSTEMS-FULL-WORKFLOW-PASS-040',
    'kind': 'frozen_candidate_actual_Workflow_verified_not_applied',
    'summary': 'The actual shared Workflow case passed, exit0,1203.880465641seconds,1045sources unchanged. It exercised selected tool construction, launch/API, results, seven-family typed delivery, scientific forwarding and root closure. Application196 is prepared but not run; production remains unchanged pending proteome182 final host verification/application.',
    'qualification': 'Controlled choices and transport with real host/communication. No live ComparativeSystems task, deployed producer attestation or immutable remote Data snapshot claimed.',
    'reports': [report(c + 'final_workflow_001/' + name) for name in ('receipt.json', 'pytest.xml', 'source_after.json')] +
        [report(application + name) for name in ('DELTA_MANIFEST_001.json', 'APPLICATION_CONTRACT_001.md', 'HANDOFF_001.md')],
}
fastq = {
    'id': 'FASTQUTILS-PARSERS-CALCULATORS-RETURNS-CANDIDATE-040',
    'kind': 'candidate_scientific_components_tested_host_integration_implemented_full_Workflow_pending',
    'summary': 'A sequence/alignment parsers and calculators37pass after root corrected fastq-pair key matching; B report parsers/calculators75pass; C metadata/sheet/provider/projection86pass on frozen24-source closure. Root registered the actual configured API tool, publication, saved validation, seven-family return owner and packaged schema. Root pure return/catalog30development tests pass; full actual host/Workflow verification is assigned to fresh202 and remains unfinished. No production application.',
    'numerical_example': 'C actual synthetic parser/provider output:2reads,GC5/9,Phred-model expected errors0.001 under explicit encoding assumption,Hostile6/8=0.75; nine requested fields across seven families. Association remains unresolved and recipe stages remain unknown. Separate A example has2reads8bases,GC0.5,meanPhred30 and expectederrors0.0404.',
    'corrections': 'Actual fastq-pair strips only final mate character after /_. and uses ASCII space as its title delimiter; original A removed the delimiter too. Signed report differences retain both measurement operands but have null numerator/denominator. Root development001/002 failed on invalid synthetic host identities and test-selector mistakes; these receipts remain. Corrected003passes but C fixture helper changed during that run. Fresh202 then found an actual storage-order defect in root validate_requested_form: canonical JSON sorts object keys. Root reproduced and repaired it using the exact required array with full-schema equality preserved. Six regression cases added; combined frozen verification is running against new actual pin e25e6accdeb551f989701d50b2bfed8a6f9393da31848cbc62a0fb2f5856e135. Earlier scoped receipts retain their actual original dependency hashes.',
    'qualification': 'Synthetic native-format and retained source-executed-synthetic fixtures, no live remote service or actual binary execution by these workers. Cutadapt, SAMstat and p3-sra formats remain explicit unfinished work. Full episode path, packaging verification and application remain unfinished. Counts are separate suites, not repeated-pass totals or whole-tool completion.',
    'reports': [report(f + name) for name in ('ROOT_RETURN_CONTRACT_001.md', 'HOST_WORKLOAD_002.md',
        'evidence_root_mapping_001/receipt.json', 'evidence_root_mapping_001/tests.xml',
        'evidence_b/HANDOFF.md', 'evidence_b/TERMINAL_RECEIPT_FINAL.json', 'evidence_b/REPORT_DIFFERENCE_CLARIFICATION.md',
        'evidence_c/frozen_001/VERIFICATION_RECEIPT.json', 'evidence_c/integration_handoff_002/provider_result.json',
        'evidence_root_returns_001/receipt.json', 'evidence_root_returns_002/receipt.json',
        'evidence_root_returns_003/receipt.json', 'evidence_root_returns_003/tests.xml',
        'evidence_contract_order_001/CORRECTION.md', 'evidence_contract_order_001/original_failure.json',
        'combined_unit_001/command.json')],
}
genome = {
    'id': 'GENOME-ALIGNMENT-REQUIREMENT-REFERENCE-FAILURE-040',
    'kind': 'unresolved_actual_provider_failure_reproduced_on_pre_performance_baseline',
    'summary': 'After retained fixtures were supplied, the actual selected-operation host failed in build_genome_alignment_data→validate_genome_alignment_data→_links with bvbrc_genome_alignment_provider_requirement_reference_unknown. The same failure occurs on exact1045-path186baseline with the same seven fixtures, before typed-return validation. It is not attributed to197performance changes and remains unrepaired.',
    'qualification': 'Historical passing checks remain facts. They do not erase this current failing native host case. Initial missing-fixture failures are distinct from the later provider failure.',
    'reports': [report(performance + name) for name in ('baseline_fixture_001/receipt.json', 'baseline_fixture_001/tests.xml',
        'baseline_fixture_001/output.log', 'fixture_retry_002/receipt.json')],
}
perf = {
    'id': 'TYPED-RETURN-PERFORMANCE-CANDIDATE-040',
    'kind': 'measured_application_binding_optimization_unapplied_final_verification_in_progress',
    'summary': 'Three-file197 candidate caches successful pure exact-content schema compilation and private grammar templates, and accelerates exact built-in JSON equality with fallback. It preserves actual custody/pin/source checks. Saved-read warm benchmark9.425069→6.220734seconds with the same authoritative-call counts. Broader regression559pass,5fail,1setup error: all six exceptions were missing retained fixtures before the requested boundary. Five affected alignment/MinHash cases subsequently pass with exact retained fixtures; the sixth reaches the separately reproduced GenomeAlignment baseline failure. The controlled MinHash Workflow has8completed actions/8observations and exact-zero practical endpoint forecasts. Proteome/ComparativeSystems full Workflow verification remains running.',
    'qualification': 'Benchmark used read-only SQLite/no-write effects shim and does not prove actual runtime behavior. Full Workflow is unshimmed and not yet terminal. Existing GenomeAlignment provider failure is separately recorded. No method_loop, scientific credit or continuation change; no production application.',
    'reports': [report(performance + name) for name in ('REVIEW_HANDOFF.md', 'BOUNDARY_TRACE.md',
        'benchmark_before_001/publication_warm_probe_001/receipt.json',
        'benchmark_after_001/publication_warm_probe_001/receipt.json',
        'regressions_001/receipt.json', 'regressions_001/tests.xml', 'REGRESSION_OUTCOMES.md',
        'fixture_comparison_001/receipt.json', 'fixture_comparison_001/tests.xml',
        'minhash_accounting_001/receipt.json')],
}
added = [comparative, fastq, genome, perf]
assert not {e['id'] for e in added}.intersection(e['id'] for e in work['verification_evidence'])
work['verification_evidence'].extend(added)
updates = {
    'C-L202-GenomeAlignment': ({
        'overall': 'applied_prior_controlled_paths_tested_current_native_host_requirement_reference_failure_unresolved',
        'integration_verification': 'prior23applied_checks_retained_new_actual_host_failure_reproduced_on_baseline_before_returns',
    }, [genome['id']], ' Update040: current actual native host case fails requirement_reference_unknown during data-sheet construction, independently reproduced on unchanged pre-performance186baseline. Prior passes remain historical facts; this failure is not repaired.'),
    'C-L206-GenomeComparison': ({}, [perf['id']], ' Update040:182finalhost stillrunning and182notapplied.197separate binding-performance candidate measured with same authoritative checks; final real Workflow/retry verification unfinished. No method_loop change or whole-tool completion.'),
    'C-L207-ComparativeSystems': ({
        'overall': 'candidate_provider_package_and_full_Workflow_verified_not_applied',
        'invocation_contract': 'candidate_actual_selected_API_submission_artifact_and_typed_return_path_verified_controlled_transport',
        'integration_verification': 'provider127_installed_package_and_frozen_actual_Workflow_pass_application_pending',
    }, [comparative['id']], ' Update040: final actual Workflow1pass in1203.880s,exit0,1045sourcesunchanged. This supersedes pending status only.196application prepared/notrun; live execution and remote attestation remain unverified.'),
    'C-L209-FastqUtils': ({
        'overall': 'candidate_parsers_sheets_calculators_and_typed_return_code_implemented_full_host_Workflow_unfinished',
        'tool_information': 'candidate_name_description_API_resources_substantive_instructions_and_actual_catalog_contract_tested',
        'numerical_sheet': 'candidate_native_and_calculated_quantities_populated_explicit_populations_assumptions_unknowns_preserved',
        'native_parser': 'candidate_FASTQ_SAM_BAM_FastQC_TrimGalore_fastq_pair_Hostile_formats_tested_unsupported_formats_remain',
        'metadata_extractor': 'candidate_original_arrays_recipe_source_bound_metadata_explicit_joins_and_failures_tested',
        'deterministic_calculator': 'candidate_explicit_saved_sheet_composition_quality_mapping_retention_and_signed_consistency_tested',
        'production_result_binding': 'candidate_actual_registration_publication_saved_validation_and_seven_family_returns_implemented_not_applied',
        'numerical_verification': 'A37pass_B75pass_C86pass_separate_suites_actual_filled_synthetic_examples_retained',
        'integration_verification': 'root_return_catalog30development_pass_not_frozen_actual_host_Workflow_and_package_unfinished',
    }, [fastq['id']], ' Update040:195interfaces finalized;198A/B/Cscientific code androottypedreturn wiring implemented in candidate.37/75/86scoped tests pass;root30developmentpass with concurrent fixture change explicitly recorded. Fresh202foundrootcanonicalstorage-orderbug;rootfixedwithsixnewcasesandnewactualpin,combinedfrozenverificationrunning. Actualhost/Workflowworkongoing. No production orlive claim; unsupportedCutadapt/SAMstat/p3-sra stayunfinished.'),
}
for row in work['rows']:
    if row['id'] in updates:
        fields, evidence, note = updates[row['id']]
        row.update(fields)
        row['evidence_ids'].extend(evidence)
        row['note'] += note
for row in work['resource_bindings']:
    key = row['id'].removesuffix('::api')
    if row['id'].endswith('::api') and key in updates:
        fields, evidence, _ = updates[key]
        row.update({k: v for k, v in fields.items() if k in row and k != 'overall'})
        row['evidence_ids'].extend(evidence)

changes = []
for group, count in (('rows', 308), ('resource_bindings', 288)):
    assert len(work[group]) == count
    assert [r['id'] for r in work[group]] == [r['id'] for r in original[group]] == [r['id'] for r in scope[group]]
    previous = {r['id']: r for r in original[group]}
    changes.extend({'group': group, 'id': r['id'], 'before': previous[r['id']], 'after': deepcopy(r)}
        for r in work[group] if r != previous[r['id']])
assert len(changes) == 8 and work['complete_scientific_tools_claimed'] == 0
assert sha(scope_path) == scope_sha
updated = (json.dumps(work, indent=2) + '\n').encode()
record = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-25',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': hashlib.sha256(raw).hexdigest(), 'new_status_sha256': hashlib.sha256(updated).hexdigest(),
    'scope_sha256_unchanged': scope_sha, 'scope_changes': False,
    'current_progress': 'Implemented FastqUtils scientific modules and actual host/return registration in candidate; verified separate numerical suites and developmental return/catalog path; preserved new GenomeAlignment failure and confirmed186fullWorkflow terminal result. Fresh202fullpath verification continues.',
    'inventory_maintenance_counted_as_implementation_progress': False,
    'specific_pending_NCBI_job_verification_included': False,
    'changes': changes, 'added_evidence': added, 'complete_scientific_tools_claimed': 0}
with (HERE / 'PROGRESS_UPDATE_040.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
STATUS.write_bytes(updated)
print(json.dumps({'checkpoint': 40, 'changed_rows_and_bindings': len(changes), 'status_sha256': record['new_status_sha256']}))
