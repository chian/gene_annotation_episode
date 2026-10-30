"""Compile retained verification evidence without executing scientific work."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ORIGINAL = ROOT / 'verification/tool_graders_blast_geometry_2026-10-26_295/checks_003'


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def relative(path):
    return str(path.relative_to(ROOT))


def summary(directory):
    suite = ET.parse(directory / 'junit.xml').getroot()[0]
    result = {name: int(suite.get(name, '0')) for name in ('tests', 'failures', 'errors', 'skipped')}
    result['passed'] = result['tests'] - result['failures'] - result['errors'] - result['skipped']
    result['seconds'] = float(suite.get('time'))
    result['junit'] = relative(directory / 'junit.xml')
    result['stdout'] = relative(directory / 'stdout.txt')
    return result


def main():
    original_controls = HERE / 'original_run_evidence'
    original_controls.mkdir(exist_ok=True)
    controls = [*ORIGINAL.glob('.local-job-*'), *[ORIGINAL / name for name in
        ('stdout.txt', 'stderr.txt', 'junit.xml', 'source_manifest.json', 'RECOVERED_RECEIPT_001.json')]]
    copied = {}
    for source in controls:
        if source.is_file():
            destination = original_controls / source.name
            if not destination.exists():
                shutil.copy2(source, destination)
            copied[str(source)] = {'copy': relative(destination),
                'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}
    write('original_run_evidence_manifest.json', copied)

    initial = ET.parse(HERE / 'checks_001/junit.xml').getroot()[0]
    failures = []
    for case in initial.findall('testcase'):
        error = case.find('failure')
        if error is None:
            continue
        name = case.get('name')
        message = error.get('message')
        if 'ToolRegistry' in message:
            functions = ['cli.main', 'tool_configuration.build_tools', 'PublicClients.__init__']
            basis = 'The CLI delegates registry construction to the shared build_tools factory; the removed cli.ToolRegistry symbol is not the current callable contract.'
            repair = 'Patch the actual tool_configuration.ToolRegistry construction port while asserting the original default/configured provider-access directory exactly once.'
            trace = {'selected_operation': 'CLI capabilities', 'native_input': 'none; construction-only fixture',
                'stored_sheet': 'not applicable', 'calculator': 'not applicable',
                'typed_return': 'catalog through cli._print', 'responsible_caller': 'tool_configuration.build_tools'}
        elif 'StopIteration' in message:
            functions = ['composition_information.restricted_root', 'Workflow.catalog',
                'DecisionSource.next', 'APIServiceExecution.execute', 'APIServiceExecution._execute_locked',
                'NCBIBlastService.decode', 'ExecutionEpisodes.validate_report']
            basis = 'AGENTS episode ownership and immutable principles 3/14: root commissions resource children; invalid root selections create no completed action. A current API status request is one selected action and has no private polling loop.'
            repair = 'Keep legacy cancellation/wait/replay and original provider-handle checks, assert current root rejection with zero runtime observations, and verify current API-child status waiting, retained-response cancellation recovery, exactly-once observations and fetched-result replay through the actual parent typed-return path.'
            trace = {'selected_operation': 'obsolete root public.blast.search/collect, now rejected',
                'native_input': 'synthetic original RID/status/JSON2; no network',
                'stored_sheet': 'retained blast_database_sheet_v1 with exact native document',
                'calculator': 'calculate_database_probabilities and selected-column calculator',
                'typed_return': 'execution_blast_hsps through current results child',
                'responsible_caller': 'scientific parent -> launch -> launch_api; monitor/results select separate operations'}
        else:
            functions = ['credit.project_credit', 'credit._retired', 'ToolRegistry._import_blast',
                'grade_blast_result', 'build_database_sheet', 'calculate_database_probabilities',
                'Store._assessment_write_extent', 'blast_hsp_facts']
            basis = 'Contract 299 requirement 3 explicitly preserves scorer retirement. Immutable principles 4/5/6/7/11 separate numerical tool sheets and calculators from W05 annotation credit; missing annotation scoring is not zero.'
            repair = 'Assert precise AnnotationScoringUnavailable separately. Preserve native bytes, zero scores, exact original-input intervals, typed HSP facts, missing/partial failures and source-only references using their actual current consumers. Coherent translated fixtures now map 6 nt to 2 aa; protein operands use aa and forward protein coordinates.'
            trace = {'selected_operation': 'actual legacy ToolRegistry search/collect or retained malformed response',
                'native_input': 'complete synthetic NCBI JSON2/ZIP bytes or retained malformed bytes',
                'stored_sheet': 'blast_database_sheet_v1 in source auxiliary grading artifact, when parsing succeeds',
                'calculator': 'calculate_database_probabilities; raw alignment components remain separately inspectable',
                'typed_return': 'native projected records; BLAST_HSP_FACT_SCHEMA where requested',
                'responsible_caller': 'ToolRegistry owns primitive verification; current episode delivery verified separately through API child'}
        failures.append({'test': case.get('classname') + '::' + name, 'observed_error': message,
            'classification': 'obsolete_fixture', 'contract_basis': basis,
            'affected_functions': functions, 'repair': repair, 'path_trace': trace,
            'evidence_paths': [relative(HERE / 'checks_001/junit.xml'),
                relative(HERE / 'checks_001/stdout.txt'), relative(HERE / 'initial/tests/test_blast_binding.py'),
                relative(HERE / 'checks_003/junit.xml')]})

    examples = []
    temp = HERE / 'checks_003/temporary/pytest'
    for database in sorted(temp.glob('test_program_native_intervals_*/state/state.sqlite3')):
        if database.parent.parent.is_symlink():
            continue
        connection = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)
        connection.execute('PRAGMA query_only=ON')
        for source_id, data in connection.execute("SELECT id,data FROM records WHERE record_type='source'"):
            source = json.loads(data)
            if source.get('provider') != 'ncbi_blast':
                continue
            for ref in source.get('auxiliary_artifact_refs', []):
                sha = ref.removeprefix('artifact_')
                artifact_path = database.parent / 'artifacts' / sha[:2] / sha
                envelope = json.loads(artifact_path.read_bytes())
                if envelope.get('schema') != 'tool_grading_artifact_v1':
                    continue
                grade = envelope['grading']
                sheet = grade['sheet']
                component = sheet['hits'][0]['hsp_components'][0]
                examples.append({'program': sheet['normalized_result']['search']['program'],
                    'representation': 'synthetic offline native-format fixture; verification evidence',
                    'source_ref': source_id, 'source_database': relative(database),
                    'grading_artifact': relative(artifact_path), 'grading_artifact_sha256': sha,
                    'native_scores': component['native_scores'], 'counts': component['counts'],
                    'fractions': component['fractions'], 'denominators': component['denominators'],
                    'geometry_available': component['geometry_available'],
                    'function_probabilities': grade['probabilities']['unadjusted_probabilities']})
        connection.close()
    write('NUMERICAL_VERIFICATION_EXAMPLES.json', examples)

    live = json.loads((HERE / 'live_observation_001.json').read_text())
    terminal = json.loads((HERE / 'live_observation_002_terminal.json').read_text())
    identities = [{'pid': p['pid'], 'cmdline': p['cmdline'].replace('\u0000', ' ').strip(),
        'start_ticks': int(p['stat'].split()[21]), 'source': p['source']}
        for p in live['processes']]
    differences = json.loads((HERE / 'broad_source_provenance_differences.json').read_text())
    long_cases = sorted(ET.parse(ORIGINAL / 'junit.xml').getroot().iter('testcase'),
        key=lambda x: float(x.get('time', 0)), reverse=True)[:3]
    observations = [
        {'observation_time': live['observed_at'], 'process_identity': identities,
         'measured_fact': {'earlier_homology_counts': live['database']['counts'],
            'earlier_homology_episode_states': live['database']['episodes'],
            'active_database': 'verification/tool_graders_bvbrc_homology_composed_workflow_2026-10-24/runs/composed-r8cqvo0o/state/state.sqlite3',
            'active_archive_writes': [p for p in live['fd_sampling']['observed_paths'] if '/archive/.write-' in p],
            'fd_samples': live['fd_sampling']['sample_count']},
         'source': relative(HERE / 'live_observation_001.json'),
         'interpretation': 'The same original pytest process had advanced to another composed-workflow case; the earlier 15-action case had yielded. Archive writes show activity in that subsequent case.',
         'unknowns': ['Python call stack and time in individual validators were not measured.']},
        {'observation_time': terminal['observed_at'], 'process_identity': terminal['processes'],
         'previously_verified_identity': identities,
         'measured_fact': {'terminal': terminal['terminal_files'], 'pytest': summary(ORIGINAL),
            'long_fixture_cases': [{'test': c.get('classname') + '::' + c.get('name'),
                'seconds': float(c.get('time'))} for c in long_cases],
            'pairwise_setup_source_hash_mismatch': differences},
         'source': relative(HERE / 'live_observation_002_terminal.json'),
         'interpretation': 'Original native work ended with pytest exit 1 and no recorded resource/execution failure. Five pairwise setup errors share a nine-file provenance mismatch after workflow closure; no scientific defect follows from that mismatch alone.',
         'unknowns': ['There is no reconstructed broad-run end-of-run source snapshot.',
            'Elapsed fixture durations do not isolate parsing, return validation, archive writing or source hashing costs.']}
    ]
    diagnosis = {'workload': 299, 'generated_at': datetime.now(timezone.utc).isoformat(),
        'original_run': {'directory': str(ORIGINAL), 'ownership': 'root; observed read-only, never signaled/restarted by 299',
            'recovered_receipt': relative(ORIGINAL / 'RECOVERED_RECEIPT_001.json'),
            'retained_evidence_manifest': relative(HERE / 'original_run_evidence_manifest.json'),
            'result': summary(ORIGINAL)},
        'failures': failures, 'live_run_observations': observations,
        'verification_runs': {name: summary(HERE / name) for name in ('checks_001', 'checks_002', 'checks_003')},
        'verification_fixture_correction': {'test': 'typed_return[interrupted_submission]',
            'observed_error': 'checks_002 used a snapshot glob omitting the actual episodes directory; expected 1, observed 0',
            'classification': 'obsolete_fixture', 'contract_basis': 'Inspect actual retained API operation custody; do not fabricate a response.',
            'affected_functions': ['test_parent_receives_native_scores_and_scoped_hsp_without_per_tool_task_prose'],
            'repair': 'Use */episodes/*/actions/*/snapshot.json, assert retained submit metadata and original RID bytes, then reconstruct same run.',
            'evidence_paths': [relative(HERE / 'checks_002/stdout.txt'), relative(HERE / 'checks_003/stdout.txt')]},
        'implementation': {'production_files_changed': [],
            'tests_changed': ['tests/test_blast_binding.py', 'tests/test_blast_typed_return_integration.py'],
            'tests_unchanged': ['tests/test_blast_result_views.py'],
            'scoring_sheet_or_calculator_changes': 'none; existing field definitions and deterministic functions verified'},
        'source_hashes': {'initial': relative(HERE / 'checks_001/source_hashes.json'),
            'final_run_start': relative(HERE / 'checks_003/source_hashes.json'),
            'final_postrun': relative(HERE / 'checks_003/source_hashes_after.json'),
            'final_source_hash_changes': json.loads((HERE / 'checks_003/source_hash_changes.json').read_text()),
            'authority': relative(HERE / 'authority_hashes.json')},
        'remaining_production_defects_found_by 299': [],
        'limits': ['No new live API, HPC, database BLAST or model execution.',
            'Cancellation coverage begins after the real binding retained the native response; it does not prove arbitrary transport-interruption recovery.',
            'Legacy polling is one primitive receipt; the current API child selects separate status actions. These have distinct accounting contracts.',
            'Local native-BLAST publication/integration work 297/298 and other fixed programs/resource routes are outside this workload.',
            'The original broad run retains 15 failures and 5 setup errors; the separate 34-pass run repairs only the contracted modules.']}
    write('DIAGNOSIS.json', diagnosis)

    hashes = json.loads((HERE / 'checks_003/source_hashes.json').read_text())
    table = '\n'.join('| ' + row['program'] + ' | ' + str(row['counts']['identical_pairs']) +
        ' | ' + str(row['fractions']['query_paired_coverage']) + ' | ' +
        str(row['fractions']['reference_paired_coverage']) + ' |' for row in examples)
    owned_hashes = '\n'.join(f'- `{name}`: `{hashes[name]}`' for name in
        ('tests/test_blast_binding.py', 'tests/test_blast_result_views.py', 'tests/test_blast_typed_return_integration.py'))
    changed_names = '\n'.join('- `' + Path(name).name + '`' for row in differences for name in sorted(row['changed_files']))
    report = f'''# Workload 299: existing BLAST regression verification

The scoped repair is complete: **34 passed, 0 failed, 0 errors** in 140.80 seconds through `local_jobs.run_local_job`, with 20 GiB RAM, 4 GiB scratch and no wall-time cap. Final source hashes were unchanged between launch and the postrun observation. No production file, scoring-sheet definition, calculator, annotation-credit function, episode prompt or runtime task choice was changed.

## Implementation

Updated two owned test modules. `test_blast_result_views.py` is unchanged. Retired annotation scoring now has explicit `AnnotationScoringUnavailable` assertions separate from native-result, extent, source custody and typed-return assertions. Protein fixtures now declare protein operands and forward protein intervals. Translated fixtures use coherent 6 nt / 2 aa correspondence. The CLI test patches the actual shared construction port.

The legacy `public.blast.search/collect` fixtures still check retained native bytes, a single original provider handle, cancellation recovery, protocol waiting and exact receipt replay. They also verify that annotation root rejects those execution selections without a completed action. Runtime coverage is preserved through the actual current API child: separate selected status requests, cancellation after retained submission response, same-run reconstruction, exact one-submit behavior, one observation per completed own action, original fetched-result replay and the requested native HSP form reaching its parent. No default annotation formula is supplied.

## Verification

| Run | Passed | Failed | Errors | Meaning |
| --- | ---: | ---: | ---: | --- |
| checks_001 | 17 | 15 | 0 | Unmodified three-module reproduction; original tests and failing logs retained.|
| checks_002 | 33 | 1 | 0 | Repaired contracts; one added test had an incorrect retained-snapshot glob.|
| checks_003 | 34 | 0 | 0 | All three modules, including corrected cancellation recovery.|

The initial 15 failures comprise 11 retired-scorer expectations, 2 obsolete root execution selections and 2 stale CLI monkeypatch locations. Each has a separate entry and production-path trace in `DIAGNOSIS.json`.

These are numerical test examples from the existing scoring-sheet fields and functions, not new grader implementations:

| Program | Identical pairs | Query paired coverage | Reference paired coverage |
| --- | ---: | ---: | ---: |
{table}

All five examples retain bit score 0, raw score 12 and E-value 0 as measured zero. Function probabilities remain null without function assignments. Saved database-sheet recalculation matches the retained calculator output. The actual API-child example returns bit score 31.5, raw score 60, E-value 0.00001 and native identity 6/8; its selected three-column window has 2 identical pairs and 1 substitution, query coverage 3/8. Source-only references remain without an invented full sequence. ZIP bytes, malformed/partial native results, unreceived-HSP rejection, scope checks and tampered-record rejection remain covered.

## Original broad run: read-only diagnosis

Worker 1674733 and pytest 1674741 were verified against their command lines and original lifecycle identity. At 14:17:08Z, the earlier Homology state still contained 15 actions/model calls/observations, but all five episodes had yielded. The same pytest process had an open database and active archive writes in `composed-r8cqvo0o`, a subsequent composed-workflow case. This proves progress into other work. No Python stack or per-validator timing was obtained; an infinite loop or a particular expensive validator is not established.

The original native result ended at 14:19:49.872702Z with exit 1, no resource or execution failure, and 103,907,328 observed scratch bytes. Its unchanged result is **226 passed, 15 failed, 5 errors** in 2310.71 seconds. Root recovered its terminal receipt in `RECOVERED_RECEIPT_001.json`; 299 did not signal, restart, cancel or collect the original job. Its three large fixture timings were 457.585 s, 832.920 s and 692.090 s, covering distinct Homology, pairwise and composed cases.

All five setup errors share the pairwise fixture's before/after provenance assertion at line 438, after its workflow and numerical-output writes. Exact manifests show nine changed source files:

{changed_names}

Exact before/after hashes are in `broad_source_provenance_differences.json`. These source changes prevent treating that fixture as stable-source verification. They do not alone prove a numerical defect. No broad-run end-of-run source snapshot is reconstructed.

## Evidence and limits

- Full failure diagnosis: `DIAGNOSIS.json`.
- Initial tests: `initial/tests/`; initial native receipt and failures: `checks_001/`.
- Final command, native receipt, JUnit and complete logs: `checks_003/`.
- Numerical example artifact identities: `NUMERICAL_VERIFICATION_EXAMPLES.json`.
- Reviewable test changes: `CHANGES.patch`; final evidence and authority review: `FINAL_REVIEW.json`.
- Original run observations: `live_observation_001.json`, `live_observation_002_terminal.json` and copied original evidence with its manifest.
- Every production Python source and owned test has a retained launch SHA-256; the final postrun comparison is empty. Authority documents have separate hashes.

Final owned test hashes:

{owned_hashes}

No new production defect was established by 299. This is offline regression verification with synthetic protocol/native-format data. It does not establish live API/HPC operation, arbitrary transport-cancellation recovery, every BLAST program or resource route, or completion of workloads 297/298. The original broad failures remain preserved and separately qualified.
'''
    (HERE / 'REPORT.md').write_text(report)
    print(json.dumps({'diagnosis': relative(HERE / 'DIAGNOSIS.json'),
        'report': relative(HERE / 'REPORT.md'), 'initial_failures': len(failures),
        'numerical_examples': len(examples), 'final': diagnosis['verification_runs']['checks_003']}, indent=2))


if __name__ == '__main__':
    main()
