"""Record actual parser work, completed MSA case and isolated validation evidence."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
path = HERE / 'WORK_STATUS.json'
raw = path.read_bytes()
before = hashlib.sha256(raw).hexdigest()
assert before == '97b96941d78b45efcde59c43e3151c96a6f748e51014099591c052f114daaa00'
assert not (HERE / 'PROGRESS_UPDATE_028.json').exists()
work = json.loads(raw)
old = deepcopy(work)

def hashed(name):
    return {'path': name, 'sha256': hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}

def read(name):
    return json.loads((ROOT / name).read_text())

def junit(name):
    return {key: sum(int(s.get(key, '0')) for s in ET.parse(ROOT / name).getroot().iter('testsuite'))
            for key in ('tests', 'failures', 'errors', 'skipped')}

native = 'verification/tool_graders_bvbrc_proteome_native_2026-10-25/'
candidate = 'verification/tool_graders_form_reference_validation_2026-10-25/'
prompts = 'verification/tool_graders_prompt_boundary_inventory_2026-10-25_163/'
msa_path = 'verification/tool_graders_bvbrc_alignment_workflow_2026-10-25_162/case-msa_dna.json'
assert junit(native + 'ROOT_REGRESSION_005.xml') == dict(tests=94, failures=0, errors=0, skipped=0)
assert junit(candidate + 'candidate-tests-002.xml') == dict(tests=202, failures=0, errors=0, skipped=0)
assert junit(candidate + 'candidate-pin-tests-003.xml') == dict(tests=49, failures=0, errors=0, skipped=0)
msa = read(msa_path)
assert len(msa['passed_test_lines']) == 4
assert msa['replay']['new_http_calls'] == 0
assert msa['replay']['counts_before'] == msa['replay']['counts_after']
dispatch = read(prompts + 'PROVIDER_DISPATCH_EVIDENCE.json')
assert len(dispatch['checks']) == 24 and dispatch['source_unchanged'] and dispatch['original_closed_run_files_unchanged']
comparisons = {name: read(candidate + name + '.json') for name in (
    'baseline-msa', 'candidate-msa-checks', 'baseline-genome', 'candidate-original-backend-genome-checks')}
assert all(v['status'] == 'passed' and v['immutable_files_unchanged'] and
           v['counts_before'] == v['counts_after'] for v in comparisons.values())

native_id = 'BVBRC-PROTEOME-NATIVE-028'
native_evidence = {'id': native_id, 'kind': 'synthetic_native_format_component_verified',
    'summary': 'New pure GenomeComparison custom JSON/TSV parser and structural validator preserve all source rows, actual comparison indices, native rounded fractions, lexemes, source positions and separate incomplete/unknown/malformed meanings. Agent86 tests passed; root then reproduced two missing canonical key relationships, corrected them, and94 tests passed.',
    'qualification': 'Every native-looking example is synthetic from inspected producer writers. Not a complete scientific tool: actual native outputs, full directional reports, executed input FASTAs, metadata joins, sheet/calculators, source/task custody, deployment and episode integration remain unverified or unfinished. No registry or production episode imports these new modules. Packaging still needs the schema asset.',
    'example': {'reference_records': 2, 'associations': 3, 'comparison_ordinals': [2, 4],
        'native_identity_fractions': [0.875, 0.0, 0.875],
        'legacy_subject_fractions': [0.990, 0.500, 0.990],
        'meaning': 'first selected HSP fractions; legacy subject span omits inclusive endpoint; no corrected coverage or confidence inferred'},
    'retained_failure': 'ROOT_REGRESSION_004:92pass/2fail; new test accidentally duplicated an existing association key and received the earlier duplicate rejection. Changed test input to absent track9; production check not weakened.',
    'reports': [hashed(name) for name in (native + 'VERIFICATION_RECEIPT_001.json',
        native + 'ROOT_RELATIONSHIP_REVIEW_001.json', native + 'ROOT_REVIEW_002.md',
        native + 'ROOT_REGRESSION_004.xml', native + 'ROOT_REGRESSION_005.xml',
        native + 'SYNTHETIC_PROJECTIONS_001.json', 'gene_annotation_episode/bvbrc_proteome_native.py',
        'gene_annotation_episode/bvbrc_proteome_native_contracts.py',
        'gene_annotation_episode/bvbrc_proteome_native_schemas.json', 'tests/test_bvbrc_proteome_native.py')]}

validation_id = 'FORM-VALIDATION-CANDIDATE-028'
validation = {'id': validation_id, 'kind': 'isolated_candidate_and_saved_form_diagnostic',
    'summary': 'Candidate reuses authenticated facts only within one synchronous form validation. Context identity, assignment, scope, request, received references and requested schema remain in the key. New form/direct calls reauthenticate; copied contexts expire; exceptions discard the frame. Semantic value validation remains independent.',
    'qualification': 'Not applied to production. Candidate tests001 retained68passes/73missing-fixture failures; all73 were an omitted read-only native fixture directory. Corrected tests002 pass202, including81 GenomeAlignment return and121 strict saved-structure checks. Initial12 helper,6 communication and42 alignment-return cases passed. Separate49 source-closure checks passed. A fresh candidate Workflow is running; no full Workflow pass is claimed.',
    'source_pin_correction': 'GenomeAlignment closure includes communication.py, contrary to boundary019 assumption. Direct historical candidate construction correctly rejected changed digest. Boundary020 retains original pins and adds two candidate transitive dependencies prospectively. The saved genome comparison uses original pinned backend plus explicitly loaded candidate consumer; it is not full candidate integration.',
    'saved_form_comparisons': {name: {'checks': row['checks'], 'reference_occurrences': row['reference_occurrences'],
        'form_sha256': row['original_form_sha256'], 'no_added_records_or_changed_artifacts': True}
        for name, row in comparisons.items()},
    'reports': [hashed(candidate + name) for name in ('SOURCE_BASELINE_001.json',
        'FIXTURE_CORRECTION_001.json', 'candidate-tests-001.xml', 'candidate-tests-002.xml',
        'candidate-pin-tests-003.xml', 'candidate-genome-checks.log', 'compare_saved_form.py',
        *(name + '.json' for name in comparisons))]}

msa_id = 'MSA-ORDINARY-WORKFLOW-028'
msa_evidence = {'id': msa_id, 'kind': 'completed_controlled_Workflow_case',
    'summary': 'All four ordinary-MSA tests passed in the unchanged original12-test process; its used-source guard passed. Both typed parent boundaries retained4members,28cells,6/28gaps, entropy0.9182958340544896bits and native score92. Saved replay made zero HTTP calls and preserved all recorded counts. Required-missing-consensus endpoint and changed saved parameters were checked.',
    'qualification': 'Controlled loopback HTTP/scripted decisions with retained native byte examples. No live BV-BRC or configured-model inference. MetaCATS and XMFA remain pending in the original suite; no complete12-test suite claim.',
    'reports': [hashed(msa_path)]}

prompt_id = 'PROMPT-DISPATCH-INVENTORY-028'
prompt = {'id': prompt_id, 'kind': 'actual_dispatch_gap_and_modularity_evidence',
    'summary': '24 real controlled SessionConnection calls confirmed published scientific TASK/STEERING rendering and JSON fallback for annotation, launch, API and results. Source inventory distinguishes19main role names,25role/binding contracts,2retrieval contracts and4separate example roles;31semantic rows do not mean31new episode types.',
    'qualification': 'Read-only boundary planning, no inference, new Workflow, runtime edit or completed prompt repair. Every concrete template still needs its own decision analysis and user review before implementation. Literature inventory does not authorize literature work in this goal.',
    'reports': [hashed(prompts + name) for name in ('BOUNDARY_TABLE.md', 'TEMPLATE_INVENTORY.json',
        'IMPLEMENTATION_DIVISION_DRAFT.md', 'PROVIDER_DISPATCH_EVIDENCE.json')]}

added = [native_evidence, validation, msa_evidence, prompt]
assert not {v['id'] for v in added} & {v['id'] for v in work['verification_evidence']}
work['verification_evidence'].extend(added)
for row in work['rows']:
    if row['id'] == 'C-L206-GenomeComparison':
        row.update(overall='legacy_native_parser_synthetic_verified_complete_scientific_path_unfinished',
            native_parser='legacy_custom_JSON_TSV_component_implemented94synthetic_tests_actual_native_output_unverified',
            metadata_extractor='native_scalar_and_position_preservation_only_inventory_metadata_joins_unfinished',
            numerical_verification='native_fraction_preservation_verified_synthetic_examples_aggregate_sheet_and_calculators_unfinished')
        row['evidence_ids'].append(native_id)
        row['note'] += (' Update028:accepted native002 contract and pure parser implemented;94 synthetic tests pass after root key-relationship correction. '
            'Full native reports and exact executed input inventories remain absent; do not treat legacy first-HSP summaries as complete alignments. '
            'Fresh B workload defines separate inventory/join/sheet/calculator contracts before coding. No production registration or library completion.')
    elif row['id'] in ('C-L202-GenomeAlignment', 'C-L204-MSA', 'C-L205-MetaCATS'):
        row['evidence_ids'].extend([validation_id, prompt_id])
        row['note'] += (' Update028:repeated saved-form authentication measured and an isolated validation-frame candidate tested. '
            'Production files remain frozen for original full Workflows. Candidate complete Workflow and remaining role-specific prompt work are not complete.')
        if row['id'] == 'C-L204-MSA':
            row['integration_verification'] = 'ordinary_MSA_all4_full_Workflow_cases_passed_XMFA_pending_same12test_suite'
            row['evidence_ids'].append(msa_id)
for row in work['resource_bindings']:
    if row['id'] == 'C-L206-GenomeComparison::api':
        row['evidence_ids'].append(native_id)
    elif row['id'] in ('C-L202-GenomeAlignment::api', 'C-L204-MSA::api', 'C-L205-MetaCATS::api'):
        row['evidence_ids'].extend([validation_id, prompt_id])
        if row['id'] == 'C-L204-MSA::api':
            row['integration_verification'] = 'ordinary_MSA_all4_full_Workflow_cases_passed_XMFA_pending_same12test_suite'
            row['evidence_ids'].append(msa_id)

assert len(work['rows']) == len(old['rows']) == 308
assert len(work['resource_bindings']) == len(old['resource_bindings']) == 288
assert work['complete_scientific_tools_claimed'] == old['complete_scientific_tools_claimed'] == 0
changes = []
for group in ('rows', 'resource_bindings'):
    original = {r['id']: r for r in old[group]}
    assert set(original) == {r['id'] for r in work[group]}
    changes.extend({'group': group, 'id': r['id'], 'before': original[r['id']], 'after': deepcopy(r)}
        for r in work[group] if r != original[r['id']])
updated = (json.dumps(work, indent=2) + '\n').encode()
record = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-25',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': before, 'new_status_sha256': hashlib.sha256(updated).hexdigest(),
    'current_progress': 'Recorded native parser and root corrections, ordinary MSA complete case, measured isolated validation candidate and actual prompt-dispatch gap. Original and candidate full Workflow processes remain active; next proteome numerical contract is being defined before coding.',
    'changes': changes, 'added_evidence': added, 'scope_changes': False,
    'specific_pending_NCBI_job_verification_included': False, 'complete_scientific_tools_claimed': 0}
with (HERE / 'PROGRESS_UPDATE_028.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
path.write_bytes(updated)
print(json.dumps({'checkpoint': 28, 'changed_rows_and_bindings': len(changes),
    'scope_rows': 308, 'resource_bindings': 288, 'status_sha256': record['new_status_sha256']}))
