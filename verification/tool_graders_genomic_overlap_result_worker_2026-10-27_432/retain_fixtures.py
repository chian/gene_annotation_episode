"""Copy already retained native427 bytes; perform no native work/calculation."""
from pathlib import Path
import hashlib
import json

PACKET = Path(__file__).resolve().parent
ORIGIN = PACKET.parent / 'tool_graders_genomic_overlap_native_driver_2026-10-27_427/check005/temporary/pytest'
CASES = {
    'three': ('test_real_three_sets_native_to0', 'actual_pinned_bedtools_on_synthetic_inputs'),
    'empty_c': ('test_real_empty_or_invalid_thi0', 'actual_pinned_bedtools_ab_and_analytic_empty_c'),
    'invalid_c': ('test_real_empty_or_invalid_thi1', 'actual_native_ab_and_invalid_input_c'),
    'partial_c': ('test_real_empty_or_invalid_thi2', 'actual_native_ab_and_partial_input_c'),
    'missing_c': ('test_unavailable_third_preserv0', 'actual_native_ab_with_missing_c'),
    'wrong_c': ('test_unavailable_third_preserv1', 'actual_native_ab_with_mismatched_c'),
    'missing_binary': ('test_wrong_or_unavailable_soft2', 'actual_dependency_unavailable_without_pair_invocation'),
    'no_hit': ('test_real_nonempty_no_hit_is_p0', 'actual_pinned_bedtools_zero_byte_success'),
    'duplicates': ('test_real_duplicates_remain_fo0', 'actual_pinned_bedtools_duplicate_occurrences'),
    'long': ('test_real_long_coordinates_ret1', 'actual_pinned_bedtools_int64_endpoint'),
    'variable': ('test_real_variable_bed_columns0', 'actual_pinned_bedtools_variable_input_formats'),
    'synthetic_nonzero': ('test_synthetic_nonzero_partial0', 'synthetic_nonzero_ab_with_real_native_ac_bc'),
    'synthetic_canonical_failure': ('test_synthetic_canonical_failu0', 'synthetic_canonical_publication_failure_with_empty_operand'),
    'killed': ('test_actual_lifecycle_kill_aft0', 'actual_lifecycle_killed_after_first_pair_seal'),
}
pins = []
for name, (test_name, evidence) in CASES.items():
    source = ORIGIN / test_name
    plans = list(source.rglob('genomic-overlap-plan.json'))
    if len(plans) != 1:
        raise ValueError((name, 'one_original_plan_required', len(plans)))
    plan = json.loads(plans[0].read_bytes())
    destination = PACKET / 'fixtures' / name
    destination.mkdir(parents=True, exist_ok=False)
    files = [(plans[0], destination / 'plan.json')]
    attempt = Path(plan['attempt_directory'])
    for output in plan['requested_job']['native_genomic_overlap']['outputs']:
        path = attempt / output['relative_path']
        if path.is_file():
            files.append((path, destination / 'native' / output['relative_path']))
    for original, retained in files:
        raw = original.read_bytes()
        retained.parent.mkdir(parents=True, exist_ok=True)
        retained.write_bytes(raw)
        retained.chmod(0o444)
        pins.append({'case': name, 'evidence': evidence, 'source_path': str(original),
            'retained_path': str(retained.relative_to(PACKET)),
            'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)})
(PACKET / 'FIXTURE_PINS.json').write_text(json.dumps({'source_packet': '427/check005',
    'custody_and_episode_authority': 'synthetic_worker_transport_only', 'files': pins}, indent=2) + '\n')
print(json.dumps({'cases': len(CASES), 'retained_files': len(pins)}))
