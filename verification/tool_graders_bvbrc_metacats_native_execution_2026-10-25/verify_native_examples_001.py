"""Check actual native output against supplied populations and independent math."""
import csv
import hashlib
import json
import math
from pathlib import Path
import re

import scipy
from scipy.stats import chi2


BASE = Path(__file__).resolve().parent
BOUNDARIES = BASE.parent / 'tool_graders_bvbrc_msa_metacats_boundaries_2026-10-25'


def table(case, kind):
    paths = list((BASE / 'cases' / case / 'output').glob('*-' + kind + 'Table.tsv'))
    assert len(paths) == 1
    rows = list(csv.reader(paths[0].read_text().splitlines(), delimiter='\t'))
    return rows[0], rows[1:]


def raw_table(case, kind):
    paths = list((BASE / 'cases' / case / 'output/retained_raw').glob('*-' + kind + 'Table.txt'))
    assert len(paths) == 1
    rows = []
    for line in paths[0].read_text().splitlines():
        match = re.match(r'^\s*Site(\d+)\s*\t(.*)', line)
        if match:
            rows.append([match[1], *[item.strip() for item in match[2].split('\t')]])
    return rows


def pearson(counts, epsilon=0.001, yates=False):
    a = [[value + epsilon for value in row] for row in counts]
    rows = [sum(row) for row in a]
    columns = [sum(row[j] for row in a) for j in range(len(a[0]))]
    n = sum(rows)
    expected = [[r * c / n for c in columns] for r in rows]
    delta = min(.5, min(abs(v-e) for row, erow in zip(a, expected) for v, e in zip(row, erow))) if yates else 0
    statistic = sum((abs(v-e)-delta)**2/e for row, erow in zip(a, expected) for v, e in zip(row, erow))
    return statistic, expected, delta


def main():
    receipts = json.loads((BASE / 'NATIVE_RUNS_001.json').read_text())
    assert len(receipts) == 7 and all(row['returncode'] == 0 for row in receipts)
    for receipt in receipts:
        folder = BASE / 'cases' / receipt['case']
        for relative, original in receipt['files'].items():
            raw = (folder / relative).read_bytes()
            assert len(raw) == original['bytes'] and hashlib.sha256(raw).hexdigest() == original['sha256']
        for path, expected in receipt['source_hashes'].items():
            assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
    independent = json.loads((BOUNDARIES / 'OFFICIAL_INPUT_ARITHMETIC_INSPECTION.json').read_text())
    inspected = {row['position_1based']: row for row in independent['all_variable_position_calculations']}
    raw = raw_table('official_na', 'chisq')
    variable = {int(row[0]): row for row in raw if row[1] != 'NA'}
    assert set(variable) == set(inspected) and len(variable) == 312
    for position, values in variable.items():
        reference = inspected[position]
        assert math.isclose(float(values[1]), reference['chi_square_recalculated'], rel_tol=1e-12, abs_tol=1e-12)
        assert math.isclose(float(values[2]), reference['p_recalculated'], rel_tol=1e-12, abs_tol=1e-14)
        assert int(values[3]) == reference['df_recalculated']
    _, native_significant = table('official_na', 'chisq')
    assert len(native_significant) == 143
    assert {int(row[0]) for row in native_significant} == {
        position for position, row in inspected.items() if row['p_recalculated'] < .05}
    _, pairs2 = table('aa_two_groups', 'mc')
    _, omni2 = table('aa_two_groups', 'chisq')
    chi2_yates, _, delta = pearson([[6, 0], [0, 6]], yates=True)
    pair2, _, _ = pearson([[6, 0], [0, 6]])
    assert math.isclose(float(omni2[0][1]), chi2_yates, rel_tol=1e-12)
    assert math.isclose(float(pairs2[0][1]), chi2.sf(pair2, 1), rel_tol=1e-12)
    _, pairs3 = table('aa_three_groups', 'mc')
    pair3, _, _ = pearson([[6, 0], [0, 6], [0, 0]])
    source_p, corrected_p = float(chi2.sf(pair3, 4)), float(chi2.sf(pair3, 2))
    assert len(pairs3) == 3 and all(math.isclose(float(row[1]), source_p, rel_tol=1e-12) for row in pairs3)
    missing_header, missing = table('metadata_only_first_group', 'chisq')
    _, missing_pairs = table('metadata_only_first_group', 'mc')
    assert missing_header[-3:] == ['A', 'B', 'C'] and missing[0][-3:] == ['6 A', '6 C', '']
    assert missing_pairs[0][-1] == 'A,B'
    twelve_header, twelve = table('twelve_groups', 'chisq')
    assert twelve_header[-12:] == ['g' + str(i+1).zfill(2) for i in range(12)]
    assert twelve[0][-12:] == ['4 ' + symbol for symbol in 'ACDEFGHIKLMN']
    _, native_tiny = table('native_pair_tail_underflow', 'chisq')
    _, filtered_tiny_pair = table('native_pair_tail_underflow', 'mc')
    unfiltered_tiny_pair = next(row for row in raw_table('native_pair_tail_underflow', 'mc') if row[0] == '2')
    extreme_statistic, _, _ = pearson([[2000, 0], [0, 2000]])
    assert chi2.sf(extreme_statistic, 1) == 0
    assert float(native_tiny[0][2]) == 0 and unfiltered_tiny_pair[1] == '1' and filtered_tiny_pair == []
    assert table('all_missing', 'chisq')[1] == table('all_missing', 'mc')[1] == []
    report = {
        'verification_scope': 'Unchanged retained R/Perl numerical/export producers under private local R; no full AppService, aligner or production grader',
        'all_seven_native_cases_exit_zero': True, 'native_and_input_artifact_digests_unchanged': True,
        'reference_kernel': {'package': 'scipy', 'version': scipy.__version__},
        'official_na': {'rows': 14, 'columns': 765, 'unfiltered_omnibus_rows': len(raw),
            'variable_tests': len(variable), 'conserved_native_placeholders': len(raw)-len(variable),
            'exported_omnibus_rows': len(native_significant), 'all_312_calculated_stats_and_p_match_native': True,
            'site_28_native': variable[28]},
        'two_group_aa': {'raw_counts': [[6,0],[0,6]], 'epsilon': .001,
            'omnibus_yates_delta': delta, 'omnibus_chi_square': chi2_yates,
            'omnibus_p_native': float(omni2[0][2]), 'pair_chi_square': pair2,
            'pair_df': 1, 'pair_p_native': float(pairs2[0][1])},
        'three_group_aa': {'pair_raw_counts': [[6,0],[0,6],[0,0]], 'pair_chi_square': pair3,
            'native_source_df': 4, 'native_p': source_p,
            'standard_pair_df': 2, 'standard_pair_p': corrected_p,
            'native_is_not_silently_replaced': True},
        'metadata_only_group': {'actual_observed_groups': {'B': '6 A', 'C': '6 C'},
            'metadata_only_group': 'A', 'native_exported_group_counts': dict(zip(missing_header[-3:],missing[0][-3:])),
            'actual_pair': ['B','C'], 'native_exported_pair': missing_pairs[0][-1],
            'confirmed_native_group_label_shift': True},
        'twelve_groups': {'group_count': 12, 'native_columns_match_original_groups': True,
            'speculative_lexical_order_bug_reproduced': False,
            'explanation_from_actual_R_check': 'as.matrix pads group numbers to equal width; group strings are space-padded before table ordering in this R version'},
        'underflow': {'counts_per_group': 2000, 'pair_chi_square': extreme_statistic,
            'native_unfiltered_pair_p': 1, 'pair_omitted_at_cutoff': True,
            'omnibus_native_p': 0, 'source_zero_to_one_replacement_observed': True},
        'all_missing': {'rows': 2, 'columns': 3, 'emitted_omnibus_rows': 0, 'emitted_pair_rows': 0,
            'unfiltered_omnibus_rows': len(raw_table('all_missing','chisq'))},
    }
    path = BASE / 'NUMERICAL_VERIFICATION_001.json'
    with path.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
