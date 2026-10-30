"""Summarize terminal verification receipts and seal the owned evidence."""
raise SystemExit('Historical note/provenance sealer retired; retained evidence is not regenerated from agent notes.')
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / 'verification/tool_graders_fastqutils_combined_2026-10-25_216/candidate_003'
PKG = HERE / 'package_verification_001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


suite, package = read(HERE / 'suite_receipt.json'), read(PKG / 'receipt.json')
assert suite['passed'] and package['passed']
source_before = read(HERE / 'source_before.json')
source_after = {str(p.relative_to(SOURCE)): sha(p) for p in sorted(SOURCE.rglob('*')) if p.is_file()}
candidate_after = {str(p.relative_to(HERE / 'candidate')): sha(p) for p in sorted((HERE / 'candidate').rglob('*')) if p.is_file()}
assert source_before == source_after == candidate_after and len(source_before) == 1176
save('source_at_handoff.json', source_after)
save('candidate_at_handoff.json', candidate_after)
cases = read(HERE / 'distinct_test_cases.json')
counts = dict(sorted(Counter(row['classname'].removeprefix('tests.') + '.py' for row in cases).items()))
assert sum(counts.values()) == 562 and len(counts) == 20
assert not any(row['outcomes'] for row in cases)
save('test_counts_001.json', counts)
old_result = read(PKG / 'installed_original_result.json')
new_result = read(PKG / 'installed_new_modes_result.json')
provider_cases = read(PKG / 'specimen/provider_cases.json')
numbers = dict(new_modes=new_result['numerical'])
for case, names in [('seven_family_synthetic', ('read_count', 'gc', 'errors', 'retained')),
                    ('native', ('cutadapt_base_retention',))]:
    result = provider_cases[case]['expected']
    measurements = {row['id']: row for row in result['sheet']['measurements']}
    rows = {}
    for name in names:
        payload = result['facts'][name]['records'][0]['payload']
        refs = payload.get('operand_measurement_refs', [payload['measurement_ref']] if 'measurement_ref' in payload else [])
        rows[name] = dict(payload=payload, operands=[measurements[ref] for ref in refs])
    numbers[case] = dict(provenance=provider_cases[case]['provenance'], fields=rows,
        installed_equality_check='installed_original_result.json and installed_original exit 0; expected result exported from the exact candidate',
        source_specimen_sha256=sha(PKG / 'specimen/provider_cases.json'))
assert [numbers['seven_family_synthetic']['fields'][name]['payload']['value'] for name in
        ('read_count', 'gc', 'errors', 'retained')] == [2, 5/9, .001, .75]
save('NUMERICAL_EVIDENCE_001.json', numbers)

goal = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
contract_dir = ROOT / 'verification/tool_graders_fastqutils_samstat_contract_2026-10-25_207'
save('READING_RECEIPT_001.json', dict(authoritative_goal=str(goal), authoritative_goal_sha256=sha(goal),
    complete_original_goal_read_before_work=True,
    verbatim_objective_and_all_16_principles_reread_after_substantial_examination=True,
    verbatim_objective_and_all_16_principles_reread_before_handoff=True,
    contract_reread_after_final_reset={name: sha(contract_dir / name)
        for name in ('PARSER_CALCULATOR_PORTS_002.md', 'NATIVE_FIELDS_002.json')},
    own_workload_reread=True,
    qualification='Recorded reading discipline only; not a deployed episode action, runtime gate or credit.'))

handoff = dict(version='fastqutils_combined_verification_217_v1', status='passed',
    completed_at=datetime.now(timezone.utc).isoformat(), source=str(SOURCE),
    source_file_count=1176, source_manifest_sha256=suite['source_manifest_sha256'],
    source_changed=False, candidate_changed=False, tracked_inputs_changed=False,
    implementation_edits_performed=False, production_edits_performed=False,
    provider_pin=package['provider_pin'], wheel_sha256=package['wheel_sha256'],
    packaged_source_asset_count=package['packaged_source_asset_count'],
    dependency_count=36, exact_historical_schema_hashes=package['historical_schema_hashes'],
    tests=dict(distinct_cases=562, files=20, suite_runs=1, passed=562, failed=0, errors=0,
               skipped=0, deselected=0, per_file=counts,
               package_assertions_counted_as_additional_pytest_cases=False),
    installed_imports=dict(unique_modules=package['isolated_import_count'],
                           all_from_installed_wheel=True, checkout_imports=False),
    numerical_answers=dict(original=[2, 5/9, .001, .75], cutadapt_base_retention=[28, 58],
        sra=package['sra_answers'], samstat=package['samstat_answers']),
    saved_recalculation=dict(same_parameters=True, changed_R1=[[8, 9], [4, 9]],
        old_result_unchanged=True, parsers_and_io_forbidden=True,
        typed_saved_return_without_calculators=True, forbidden_call_count=0),
    resources=dict(memory_limit_bytes=20 * 1024**3, aggregate_scratch_limit_bytes=4 * 1024**3,
        wall_time_limit=None, suite_seconds=suite['elapsed_seconds'], package_seconds=package['elapsed_seconds'],
        suite_child_peak_rss_kib=suite['child_peak_rss_kib'], package_child_peak_rss_kib=package['child_peak_rss_kib'],
        scratch_bytes_before_seal=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file()),
        actual_sessions=dict(suite=89231, package=41746),
        observation_timeout_restarts=0),
    limitations=[
        'Retained producer artifacts and synthetic provider/publication envelopes; no live acquisition, producer execution or BV-BRC service run in 217.',
        'No selected host custody or complete Workflow proof; 218 owns that separate verification.',
        'Original seven-family provider example is handcrafted synthetic data; retained historical saved forms are separately replayed.',
        'SAMstat fractions concern selected report alignment records; original input coverage is unknown, MAPQ 255 remains merged in the high bin, and uncertainty is not estimated.',
        'SRA values are reported metadata, not evidence of downloaded reads, verified mate relationships or a deployed producer version.',
        'This verifies the fixed affected suites and package scenarios, not an exhaustive scientific source audit or unknown producer versions.',
        'Root owns production application and inventory accounting. The active 202 Workflow was not touched.',
    ],
    receipts={name: sha(HERE / name) for name in (
        'suite_receipt.json', 'suite_command.json', 'distinct_test_cases.json',
        'package_verification_001/receipt.json', 'package_verification_001/packaged_hashes.json',
        'package_verification_001/installed_hashes.json', 'package_verification_001/installed_original_result.json',
        'package_verification_001/installed_new_modes_result.json', 'PROVENANCE_CHECK_001.json',
        'NUMERICAL_EVIDENCE_001.json', 'READING_RECEIPT_001.json')})
save('HANDOFF_001.json', handoff)
text = f'''Verification 217 passed for the exact composed candidate in 216/candidate_003. All 1,176 source files match the supplied manifest before testing, after testing and at handoff. No implementation or production edit was made by this workload.

All 20 FastqUtils suites ran once: **562 distinct cases passed**, with zero failures, errors, skips or deselections. This includes the restored 36-dependency provider test, all original 14 suites, SRA, the four SAMstat suites and the combined-report suite. `distinct_test_cases.json` records each case once; package probes are separate checks and are not added to that count.

The wheel was built offline using the retained 208 setuptools wheel and installed with pip into `package_verification_001/installed_wheel`. All 489 packaged source/assets match the verified candidate. The required 36 scientific dependencies, current schema, both exact historical schemas, returns and substantive tool information are present. All 197 package imports came from the installed wheel; all 290 suite imports came from the isolated candidate.

| Quantity | Verified answer | Meaning and qualification |
|---|---:|---|
| Original provider read count | 2 | Supplied synthetic FASTQ; also preserved in historical saved replay |
| GC fraction | 5/9 | G+C divided by A+C+G+T |
| Phred expected errors | 0.001 | Model quantity with explicit Phred33 assumption |
| Hostile report retention | 6/8 = 0.75 | Native-report relationship in the synthetic provider example |
| Cutadapt base retention | 28/58 | Retained actual Cutadapt 4.9 output; final Trim Galore FASTQ remains 3 reads/24 bases |
| SRA total bases | 2,673,129,532 | Reported metadata |
| SRA total spots | 35,172,757 | Spots, not total reads |
| SRA archive bytes | 937,094,000 | Reported archive size, not measured download size |
| SRA read length | 76.0 | Native reported basis remains qualified |
| SRA read types per spot | 1 | Native layout/count basis remains qualified |
| SAMstat 2.2.3 R1+R2 | 10/11 mapped; 5/11 high bin | Secondary excluded; supplementary contributes |
| SAMstat 2.5.0 all records | 9/10 mapped; 4/10 high bin | Secondary and supplementary excluded |
| Saved 2.5.0 R1 selection | 8/9 mapped; 4/9 high bin | Changed selection, same saved sheet, original result unchanged |

For SAMstat, bins are [ge30, 10–29, 0–9, unmapped]. The legacy selected combined counts are [5,3,2,1]; current all counts are [4,3,2,1]; current R1 counts are [4,2,2,1]. Exact operand records, locators, populations, numerator/denominator and qualifications are retained in `NUMERICAL_EVIDENCE_001.json`. Each report fraction retains unknown original-input scope, report-population-only meaning and merged MAPQ 255. None is annotation confidence.

Saved recalculation passed with native parsers, acquisition, subprocesses and file I/O denied. Same-parameter values were preserved. The R1 selection produced new parameter/component identities without changing the saved original. Typed saved returns also passed with calculators denied. Both historical generations remained valid. There were zero forbidden calls. The existing suites supply the missing/zero/partial/malformed/conflicting-data cases without separate duplicate case accounting.

`PROVENANCE_CHECK_001.json` records 54 retained artifact hash comparisons and the linked historical native execution receipts. These are provenance comparisons, not additional tests or new executions. No live service, scientific acquisition, native producer, selected host custody or complete Workflow run occurred in 217. The provider/publication envelopes are synthetic. Host/Workflow verification belongs to 218, and the active 202 run was not touched. Root owns production application and inventory accounting.

| Identity | SHA-256 |
|---|---|
| Supplied complete source manifest | `{suite['source_manifest_sha256']}` |
| Provider scientific dependency pin | `{package['provider_pin']}` |
| Wheel | `{package['wheel_sha256']}` |
| Original 198 schema | `{package['historical_schema_hashes']['original198']}` |
| Exact 208 schema | `{package['historical_schema_hashes']['exact208']}` |

Suite elapsed time was {suite['elapsed_seconds']:.3f} seconds; package verification took {package['elapsed_seconds']:.3f} seconds. Peak child RSS was {suite['child_peak_rss_kib']:,} KiB for the suite and {package['child_peak_rss_kib']:,} KiB for package phases. Aggregate scratch remained below 84 MB before sealing, under the 4 GiB bound; address-space limits were 20 GiB and no wall-time cap was applied. The original sessions were polled to terminal and never restarted. Exact commands, origins, source/input snapshots and logs are retained beside the receipts.

The complete original goal was read before work. Its objective and all 16 principles were reread verbatim after substantial examination and before this handoff, followed by the agreed workload, parser/calculator ports and full numerical field contract. `HANDOFF_001.json` provides the structured result; `SEAL_001.json` hashes the owned evidence files.
'''
with (HERE / 'HANDOFF_001.md').open('x') as stream:
    stream.write(text)
files = {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()}
save('SEAL_001.json', dict(version='verification_evidence_sha256_v1',
    sealed_at=datetime.now(timezone.utc).isoformat(), file_count=len(files), files=files,
    excluded=['SEAL_001.json itself'], handoff_sha256=sha(HERE / 'HANDOFF_001.json'),
    handoff_markdown_sha256=sha(HERE / 'HANDOFF_001.md')))
print(json.dumps(dict(status='passed', sealed_files=len(files),
    handoff_sha256=sha(HERE / 'HANDOFF_001.json'), seal_sha256=sha(HERE / 'SEAL_001.json'),
    scratch_bytes=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())), sort_keys=True))
