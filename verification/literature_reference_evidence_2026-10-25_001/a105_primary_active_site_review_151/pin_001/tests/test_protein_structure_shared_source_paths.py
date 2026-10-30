"""Independent native selections may use the same original structure bytes."""
from copy import deepcopy
from importlib import import_module
from pathlib import Path
import json

import pytest

from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.native_protein_structure_contracts import (
    compile_protein_structure_job, validate_protein_structure_job,
    validate_protein_structure_bundle,
)
from gene_annotation_episode.native_protein_structure_driver import run_protein_structure_driver
from gene_annotation_episode.protein_structure_formats import parse_pdb_structure
from gene_annotation_episode.protein_structure_sequences import extract_structure_sequence

_a = import_module('verification.tool_graders_protein_structure_inputs_2026-10-27_386.fixture_helpers')
_c = import_module('verification.tool_graders_protein_structure_execution_2026-10-27_390.fixture_helpers')


def shared_file_job(tmp_path):
    records = []
    for chain_index, chain in enumerate(('A', 'B')):
        for i, (symbol, xyz) in enumerate(zip('AGST', _a.DEFAULT_XYZ)):
            coordinates = (xyz[0] + 3 * chain_index, xyz[1], xyz[2])
            records.append(_a.atom_line(serial=4 * chain_index + i + 1,
                component=_a.COMPONENTS[symbol], chain=chain, number=101 + i,
                xyz=coordinates))
    raw = ('HEADER    SYNTHETIC TWO-CHAIN FIXTURE\n' + ''.join(records) + 'END\n').encode('ascii')
    file = _a.identity(raw, 'pdb_3x_text')
    parsed = parse_pdb_structure(raw, file_identity=file)
    fixed = extract_structure_sequence(parsed, selection=_a.selection(parsed, role='fixed', chain_index=0))
    moving = extract_structure_sequence(parsed, selection=_a.selection(parsed, role='moving', chain_index=1))
    mapping, map_file, _ = _a.explicit_map(fixed, moving)
    request = {'version': 'protein_structure_compare_request_v1', 'operation': 'compare',
        'fixed_selection': fixed['selection'], 'moving_selection': moving['selection'],
        'correspondence': {'kind': 'explicit_map', 'map_file': map_file},
        'parameters': _a.fit_parameters(), 'supplied_metadata_files': []}
    inputs = [
        {'input_id': 'input_0', 'role': 'fixed_structure', 'file_identity': file, 'data': raw},
        {'input_id': 'input_1', 'role': 'moving_structure', 'file_identity': file, 'data': raw},
        {'input_id': 'input_2', 'role': 'explicit_map', 'file_identity': map_file,
            'data': canonical(mapping).encode('utf-8')},
    ]
    value = _c.job(tmp_path, request=request, inputs=inputs)
    # The original Store would return one content-addressed path for both roles.
    Path(value['inputs'][1]['path']).unlink()
    value['inputs'][1]['path'] = value['inputs'][0]['path']
    return value


def test_two_selected_chains_can_share_one_original_file(tmp_path):
    value = shared_file_job(tmp_path)
    checked = validate_protein_structure_job(value)
    assert checked == value and checked is not value
    assert checked['request']['fixed_selection']['chain_key'] != checked['request']['moving_selection']['chain_key']
    assert checked['inputs'][0]['path'] == checked['inputs'][1]['path']
    assert checked['inputs'][0]['staged_relative_path'] != checked['inputs'][1]['staged_relative_path']
    assert compile_protein_structure_job(value)['argv'][-1] == 'result.json'


def test_same_original_bytes_are_staged_separately_and_compare_natively(tmp_path):
    value = shared_file_job(tmp_path)
    plan = _c.plan(tmp_path, value)
    bundle = run_protein_structure_driver(plan)
    validate_protein_structure_bundle(bundle, plan=plan)
    assert bundle['native_status'] == 'complete'
    retained = [row for row in bundle['files'] if row['role'] in ('fixed_structure', 'moving_structure')]
    assert len(retained) == 2 and retained[0]['relative_path'] != retained[1]['relative_path']
    assert retained[0]['sha256'] == retained[1]['sha256']
    assert all(row['state'] == 'present' for row in retained)
    native = json.loads((Path(plan['attempt_directory']) / 'result.json').read_bytes())
    sheet = native['sheet']
    assert sheet['sequences']['fixed']['selection']['chain_key'] != sheet['sequences']['moving']['selection']['chain_key']
    original = sheet['native_baseline']
    assert original['counts']['evaluation_used_count']['value'] == 4
    assert original['evaluation']['evaluation_rmsd']['value'] == pytest.approx(0, abs=1e-12)
    assert original['transform']['translation']['value'] == pytest.approx([-3, 0, 0], abs=1e-12)


@pytest.mark.parametrize('change', ['different_identity', 'ancestor_path', 'staged_alias'])
def test_conflicting_source_or_staging_paths_still_reject(tmp_path, change):
    value = shared_file_job(tmp_path)
    if change == 'different_identity':
        # Keep each request/file association valid: only the shared path lies.
        other = deepcopy(value['inputs'][1]['file_identity'])
        other['sha256'] = 'f' * 64
        other['artifact_ref'] = 'artifact_' + other['sha256']
        value['inputs'][1]['file_identity'] = other
        value['request']['moving_selection']['file_identity'] = deepcopy(other)
    elif change == 'ancestor_path':
        value['inputs'][1]['path'] += '/nested-file'
    else:
        value['inputs'][1]['staged_relative_path'] = value['inputs'][0]['staged_relative_path']
    with pytest.raises(ValueError, match='invalid_output_path'):
        validate_protein_structure_job(value)
