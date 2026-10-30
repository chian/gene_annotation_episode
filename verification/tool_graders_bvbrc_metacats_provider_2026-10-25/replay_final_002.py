"""Replay immutable complete examples using final provider sources, without I/O."""
from contextlib import ExitStack
import json

from write_examples_001 import (
    ROOT, HERE, OWNED, DEPENDENCIES, fingerprint, save, no_io, no_calculators,
    calculate_metacats, validate_metacats_sheet, validate_metacats_components,
)


def main():
    manifest = json.loads((HERE / 'EXAMPLE_MANIFEST_001.json').read_text())
    before = [fingerprint(path) for path in OWNED + DEPENDENCIES]
    rows = []
    for row in manifest['cases']:
        records = [row['sheet'], row['components'], row['changed_epsilon_components']]
        for record in records:
            assert fingerprint(ROOT / record['path']) == record
        sheet, answer, changed = [json.loads((ROOT / record['path']).read_text()) for record in records]
        sheet_before = json.dumps(sheet, sort_keys=True, separators=(',', ':'))
        with ExitStack() as stack:
            no_io(stack)
            assert calculate_metacats(sheet, answer['parameters']) == answer
            assert calculate_metacats(sheet, changed['parameters']) == changed
            with ExitStack() as validators:
                no_calculators(validators)
                assert validate_metacats_sheet(sheet) == sheet
                assert validate_metacats_components(answer, sheet=sheet) == answer
                assert validate_metacats_components(changed, sheet=sheet) == changed
            assert json.dumps(sheet, sort_keys=True, separators=(',', ':')) == sheet_before
        for retained in row['retained_native_files']:
            assert fingerprint(ROOT / retained['original']['path']) == retained['original']
            assert fingerprint(ROOT / retained['copy']['path']) == retained['copy']
        rows.append({'case': row['case'], 'artifacts': records,
            'baseline_exact_no_io_replay': True, 'epsilon001_exact_no_io_replay': True,
            'saved_validation_without_calculators': True,
            'sheet_and_native_numbers_unchanged': True, 'native_bytes_unchanged': True})
        print(json.dumps({'case': row['case'], 'final_source_replay': True}), flush=True)
    after = [fingerprint(path) for path in OWNED + DEPENDENCIES]
    assert before == after
    save(HERE / 'FINAL_REPLAY_002.json', {
        'scope': 'Final-source pure provider replay; Python modules and saved JSON loaded before disabling I/O',
        'cases': rows, 'sources_before': before, 'sources_after': after,
        'new_native_service_hpc_jobs': 0, 'saved_examples_rewritten': False})


if __name__ == '__main__':
    main()
