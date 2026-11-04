"""Saved structure is distinct from numerical producer verification.

Retained native examples are real; task/source witnesses and publication
envelopes are explicitly synthetic. Store, original commission, content hashes
and typed returns are exercised by F's controlled fixture, not a live service.
"""
import ast
from copy import deepcopy
import importlib
import inspect
import math
import sys
import textwrap

import pytest

from gene_annotation_episode import mauve_v4_calculation_contracts as v4
from gene_annotation_episode import mauve_backbone_contracts as side
from gene_annotation_episode import xmfa_calculation_contracts as xmfa
from gene_annotation_episode import bvbrc_genome_alignment_calculation_contracts as provider
from gene_annotation_episode import bvbrc_genome_alignment_bundle_projection as projection
from gene_annotation_episode.bvbrc_genome_alignment_sheet import validate_genome_alignment_sheet
from gene_annotation_episode.bvbrc_genome_alignment_calculators import (
    calculate_genome_alignment_components, recalculate_genome_alignment_sheet)
from gene_annotation_episode.state import Store
from test_bvbrc_genome_alignment_sheet import fixture_sheet, fixture_data, all_requests, plan
from test_bvbrc_genome_alignment_bundle_projection import saved_arguments, synthetic_original_sheet
from test_bvbrc_genome_alignment_bundle_resolution import measurement
from test_bvbrc_genome_alignment_calculators import IO_AND_PARSERS
from test_bvbrc_genome_alignment_returns import (
    ReturnFixture, example, project, fact_form, FACT_SOURCES, MEASUREMENTS)


KINDS = ('mauve_v4_segments', 'mauve_backbone', 'mauve_bbcols', 'xmfa_alignment', 'xmfa_coverage')
FULL = (v4.validate_mauve_v4_components, side.validate_mauve_backbone_components,
        side.validate_mauve_bbcols_components, xmfa.validate_xmfa_alignment_components,
        xmfa.validate_xmfa_coverage_components)
STRUCTURE = (v4.validate_mauve_v4_component_structure, side.validate_mauve_backbone_component_structure,
             side.validate_mauve_bbcols_component_structure, xmfa.validate_xmfa_alignment_component_structure,
             xmfa.validate_xmfa_coverage_component_structure)


@pytest.fixture(scope='module')
def seven():
    return fixture_sheet()


def native(sheet, index):
    return sheet['components']['outcomes'][index]['measurement']['value']


def fraction_cell(value, index):
    if index in (0, 1):
        return value['coverage'][0]['coverage_fraction']
    if index == 2:
        return value['intervals'][0]['selected_block_fraction']
    if index == 3:
        return value['blocks'][0]['pairs'][0]['identity_fraction']
    return value['members'][0]['selected_coverage_fraction']


def scientific_barrier(monkeypatch):
    """Block scientific functions at every loaded import alias, including helpers.

    The numerical cell checkers in the full validators divide fractions, and
    the interval checkers construct unions; names alone do not make them safe.
    Native format/token validation and saved custody remain active.
    """
    entire_modules = ('mauve_v4_calculators', 'mauve_backbone_calculators', 'xmfa_calculators',
        'xmfa_coordinates', 'xmfa_sources', 'bvbrc_genome_alignment_calculators',
        'bvbrc_genome_alignment_bundle_resolution', 'bvbrc_genome_alignment_inputs',
        'bvbrc_genome_alignment_associations')
    selected = {
        'mauve_v4_formats': ('parse_mauve_v4',),
        'mauve_backbone_formats': ('parse_mauve_backbone', 'parse_mauve_bbcols'),
        'xmfa_formats': ('parse_mauve_xmfa',),
        'mauve_v4_calculation_contracts': ('validate_mauve_v4_components', '_cell'),
        'mauve_backbone_contracts': ('validate_mauve_backbone_components', 'validate_mauve_bbcols_components', '_cell', '_coverage_counts'),
        'xmfa_calculation_contracts': ('validate_xmfa_alignment_components', 'validate_xmfa_coverage_components',
            '_cell', '_union', 'union_intervals', 'interval_length', 'multiplicity_bases', 'complement_intervals'),
        'bvbrc_genome_alignment_bundle_adapter': ('consume_bundle', 'implementation_sha256'),
    }
    targets = set()
    for name in entire_modules:
        module = importlib.import_module('gene_annotation_episode.' + name)
        targets.update(id(function) for function in vars(module).values()
                       if inspect.isfunction(function) and function.__module__ == module.__name__)
    for name, names in selected.items():
        module = importlib.import_module('gene_annotation_episode.' + name)
        targets.update(id(getattr(module, attr)) for attr in names)
    aliases = [(module, name) for module_name, module in list(sys.modules.items())
               if module_name.startswith('gene_annotation_episode.') and module is not None
               for name, value in list(vars(module).items()) if id(value) in targets]

    def forbidden(*args, **kwargs):
        raise AssertionError('scientific recomputation or acquisition during saved validation')

    for module, name in aliases:
        monkeypatch.setattr(module, name, forbidden)
    for name in ('log2', 'log', 'log10', 'isclose'):
        monkeypatch.setattr(math, name, forbidden)
    monkeypatch.setattr('socket.create_connection', forbidden)
    monkeypatch.setattr('socket.socket', forbidden)
    monkeypatch.setattr('subprocess.Popen', forbidden)
    assert len(aliases) >= 100
    return tuple(module.__name__ + '.' + name for module, name in aliases)


def test_dispatch_uses_exact_five_structural_interfaces_and_preserves_coordinate_checks():
    for kind, validator in zip(KINDS, STRUCTURE):
        assert provider.COMPONENT_VALIDATORS[kind] is validator
        assert list(inspect.signature(validator).parameters) == ['value']
    assert provider.COMPONENT_VALIDATORS['xmfa_coordinates'] is xmfa.validate_xmfa_coordinates
    assert provider.COMPONENT_VALIDATORS['xmfa_inverse_coordinates'] is xmfa.validate_xmfa_inverse_coordinates


@pytest.mark.parametrize('index', range(5), ids=KINDS)
def test_native_values_are_detached_with_every_scientific_alias_disabled(seven, monkeypatch, index):
    value = native(seven, index); before = deepcopy(value)
    scientific_barrier(monkeypatch)
    saved = STRUCTURE[index](value)
    assert saved == before and saved is not value
    saved['selection']['population_id'] = 'changed-copy'
    assert value == before


@pytest.mark.parametrize('index', range(5), ids=KINDS)
def test_full_validator_still_rejects_wrong_fraction_but_structure_does_not_recalculate(seven, index):
    value = deepcopy(native(seven, index))
    fraction_cell(value, index)['value'] = 0.125
    assert STRUCTURE[index](value) == value
    with pytest.raises(ValueError):
        FULL[index](value)


@pytest.mark.parametrize('index', range(5), ids=KINDS)
def test_full_validator_still_checks_lengths_counts_and_entropy(seven, index):
    value = deepcopy(native(seven, index))
    if index == 0:
        value['coverage'][0]['complement_bases']['value'] = 2
    elif index == 1:
        value['rows'][0]['member_spans'][0]['span_bases']['value'] = 31
    elif index == 2:
        value['intervals'][0]['column_placements']['value'] = 53
    elif index == 3:
        value['blocks'][0]['sites'][0]['literal_entropy_bits']['value'] = 0.5
    else:
        value['members'][0]['placement_bases']['value'] = 51
    assert STRUCTURE[index](value) == value
    with pytest.raises(ValueError):
        FULL[index](value)


@pytest.mark.parametrize('index', range(5), ids=KINDS)
@pytest.mark.parametrize('damage', ['extra', 'document', 'unit', 'method', 'population', 'nonfinite',
    'boolean', 'state', 'operand', 'requirement', 'fraction_range'])
def test_structural_corruption_rejected_without_science(seven, monkeypatch, index, damage):
    value = deepcopy(native(seven, index)); cell = fraction_cell(value, index)
    if damage == 'extra': value['unbounded'] = 'not allowed'
    elif damage == 'document': value['document_id'] = 'another-document'
    elif damage == 'unit': cell['unit'] = 'confidence'
    elif damage == 'method': cell['method_id'] = 'different-formula'
    elif damage == 'population': cell['population_id'] = 'unselected-population'
    elif damage == 'nonfinite': cell['value'] = float('nan')
    elif damage == 'boolean': cell['value'] = True
    elif damage == 'state': cell['state'] = 'missing'
    elif damage == 'operand': cell['numerator'] = 0
    elif damage == 'requirement': cell['requirement_ids'] = ['not-recorded']
    else: cell['value'] = 1.125
    scientific_barrier(monkeypatch)
    with pytest.raises(ValueError):
        STRUCTURE[index](value)


@pytest.mark.parametrize('index', [0, 1, 2, 4], ids=[KINDS[i] for i in (0, 1, 2, 4)])
@pytest.mark.parametrize('intervals', [[[4, 3]], [[0, 4], [3, 8]], [[4, 8], [0, 3]], [[0, 4], [4, 8]], [[True, 4]]])
def test_interval_shape_is_checked_without_constructing_union(seven, monkeypatch, index, intervals):
    value = deepcopy(native(seven, index))
    rows = value['coverage'] if index in (0, 1) else value['intervals'] if index == 2 else value['members']
    rows[0]['known_union_intervals'] = intervals
    scientific_barrier(monkeypatch)
    with pytest.raises(ValueError):
        STRUCTURE[index](value)


@pytest.mark.parametrize('index', range(5), ids=KINDS)
def test_selected_row_order_remains_binding(seven, monkeypatch, index):
    value = deepcopy(native(seven, index))
    key = ('member_segments', 'rows', 'rows', 'blocks', 'members')[index]
    value[key].reverse()
    scientific_barrier(monkeypatch)
    with pytest.raises(ValueError):
        STRUCTURE[index](value)


def test_new_structure_paths_have_no_inline_scientific_arithmetic():
    """Helper barriers cannot intercept inline division, aggregation or entropy."""
    functions = [*STRUCTURE, v4._cell_structure, v4._intervals_structure, side._cell_structure,
        side._intervals_structure, side._coverage_structure, xmfa._cell_structure, xmfa._intervals_structure]
    for function in functions:
        tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp):
                # Text method-name concatenation and this signed native start
                # convention are the only arithmetic syntax in these functions.
                assert isinstance(node.op, ast.Add) or ast.unparse(node) == 'abs(start) - 1'
            if isinstance(node, ast.Call):
                name = ast.unparse(node.func)
                assert name not in {'sum', 'math.log2', 'math.log', 'math.isclose', 'interval_length',
                    'union_intervals', 'multiplicity_bases', 'complement_intervals', '_cell', '_coverage_counts', '_union'}


@pytest.mark.parametrize('operation', ['project_genome_alignment_facts', 'validate_projected_facts', 'requested_projection_status'])
def test_actual_e_saved_paths_block_internal_and_aliased_science(monkeypatch, operation):
    sheet, original = synthetic_original_sheet()
    args = saved_arguments(sheet, {'original': measurement('coverage', 'xmfa_original_coverage', 'coverage_fraction',
        member_number=1, original_member=original)})
    expected = projection.project_genome_alignment_facts(**args)
    aliases = scientific_barrier(monkeypatch)
    assert any(name.endswith('._cell') for name in aliases)
    assert any(name.endswith('._entropy') for name in aliases)
    method = getattr(projection, operation)
    if operation == 'project_genome_alignment_facts':
        assert method(**args) == expected
    elif operation == 'validate_projected_facts':
        assert method(expected['facts'], **args) == expected['facts']
    else:
        assert method(expected['facts'], **args) == 'ok'


@pytest.mark.parametrize('boundary', ['pure', 'own', 'received'])
def test_actual_f_saved_paths_and_original_typed_return_have_no_science(tmp_path, monkeypatch, boundary):
    sheet, _ = synthetic_original_sheet()
    args = example(sheet=sheet)
    with Store(tmp_path / 'state') as store:
        run = ReturnFixture(store)
        child = run.child(run.saved.root, 'results', args[0])
        run.publications.add(child, args)
        _, schema, _, _ = run.admit(run.saved.root, child)
        expected = project(args)
        scientific_barrier(monkeypatch)
        if boundary == 'pure': actual = project(args)
        elif boundary == 'own': actual = run.host.facts(child, schema)
        else: actual = run.host.received_facts(run.saved.root, schema)
        assert set(actual) == set(FACT_SOURCES)
        assert [r['value'] for r in actual[MEASUREMENTS]] == [r['value'] for r in expected[MEASUREMENTS]]
        assert actual[MEASUREMENTS][0]['value']['value']['value'] == 40 / 48
        assert store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


def test_original_hash_and_frozen_values_still_reject_changed_science(seven, tmp_path, monkeypatch):
    args = list(example(sheet=seven)); altered = deepcopy(args)
    value = native(altered[1], 3); fraction_cell(value, 3)['value'] = 0.125
    assert STRUCTURE[3](value) == value
    with pytest.raises(ValueError, match='saved_sheet_content_conflict'):
        project(altered)
    with Store(tmp_path / 'state') as store:
        run = ReturnFixture(store); child = run.child(run.saved.root, 'results', args[0], sources=(MEASUREMENTS,))
        run.publications.add(child, args)
        form, schema, _, _ = run.admit(run.saved.root, child)
        form['f0'][0]['value']['value']['value'] = 0.125
        scientific_barrier(monkeypatch)
        with pytest.raises(ValueError, match='returned_facts_conflict'):
            run.host.validate_received_report(child, form, schema)


def test_missing_duplicate_requests_and_explicit_recalculation_keep_original_history(monkeypatch):
    data = fixture_data(include_missing=True)
    requests = all_requests()
    missing = deepcopy(requests[3]); missing.update(request_id='missing-first', document_slot_id='missing')
    requests.insert(0, missing)
    requests.append(deepcopy(requests[4]) | {'request_id': 'duplicate-science-distinct-request'})
    from gene_annotation_episode.bvbrc_genome_alignment_sheet import build_genome_alignment_sheet
    components = calculate_genome_alignment_components(data, calculation_plan=plan(requests))
    sheet = build_genome_alignment_sheet(data=data, components=components); before = deepcopy(sheet)
    with monkeypatch.context() as barrier:
        scientific_barrier(barrier)
        assert validate_genome_alignment_sheet(sheet) == before
    assert components['outcomes'][0]['state'] == 'missing'
    assert components['outcomes'][4]['measurement'] == components['outcomes'][-1]['measurement']
    requests[5]['basis'] = 'cooccupied_column'

    def forbidden(*args, **kwargs):
        raise AssertionError('acquisition or parser during explicit saved recalculation')

    for target in IO_AND_PARSERS:
        monkeypatch.setattr(target, forbidden)
    changed = recalculate_genome_alignment_sheet(sheet, calculation_plan=plan(requests))
    assert [m['known_union_bases']['value'] for m in changed['components']['outcomes'][5]['measurement']['value']['members']] == [48, 48, 18]
    assert sheet == before and changed['data'] == before['data']


@pytest.mark.parametrize('case', ['v4_overlap_reverse', 'v4_missing', 'v4_absent', 'v4_zero_identity',
    'backbone_overlap_reverse', 'backbone_partial', 'backbone_absent', 'backbone_unknown',
    'bbcols_overlap_duplicate', 'bbcols_partial', 'bbcols_duplicate_member', 'bbcols_empty',
    'xmfa_overlap', 'xmfa_duplicate_member', 'xmfa_zero', 'xmfa_truncated'])
def test_native_partial_missing_zero_reverse_overlap_and_duplicates(case, monkeypatch):
    """Deliberately synthetic edge bytes; they are not live-service evidence."""
    if case.startswith('v4_'):
        from test_mauve_v4_calculators import calculate, native as raw_native
        if case == 'v4_overlap_reverse': raw = '4 -1 1\n4 -1 1\n4 -3 3\n'
        elif case == 'v4_missing': raw = 'GappedAlignment\n4 1 1\nACGT\n'
        elif case == 'v4_absent': raw = 'GappedAlignment\n4 0 1\n----\nCCCC\n'
        else: raw = 'GappedAlignment\n4 1 1\nAAAA\nCCCC\n'
        value = calculate(raw_native(raw), denominator='native_declared_length'); checks = [(STRUCTURE[0], value)]
        if case == 'v4_overlap_reverse':
            assert [value['coverage'][0][k]['value'] for k in ('known_union_bases', 'placement_bases', 'multiply_represented_bases', 'excess_placement_bases')] == [6, 12, 4, 6]
        elif case == 'v4_missing': assert value['member_segments'][0]['state'] == 'missing'
        elif case == 'v4_absent': assert value['coverage'][0]['known_union_bases']['value'] == 0
        else: assert value['pair_segments'][0]['counts']['identity_fraction']['value'] == 0
    elif case.startswith('backbone_'):
        from test_mauve_backbone_calculators import calculate, backbone, members
        rows = {'backbone_overlap_reverse': b'1 5\n-3 -7\n1 5\n8 9\n',
            'backbone_partial': b'1 5\n6\n', 'backbone_absent': b'0 0\n', 'backbone_unknown': b''}[case]
        value = calculate(backbone(b'seq0_leftend seq0_rightend\n' + rows)['value'], chosen=members(0))
        checks = [(STRUCTURE[1], value)]
        if case == 'backbone_overlap_reverse':
            assert [value['coverage'][0][k]['value'] for k in ('known_union_bases', 'placement_bases', 'multiply_represented_bases', 'excess_placement_bases')] == [9, 17, 5, 8]
        elif case == 'backbone_partial': assert value['coverage'][0]['population_state'] == 'partial_selected'
        elif case == 'backbone_absent': assert value['coverage'][0]['known_union_bases']['value'] == 0
        else: assert value['coverage'][0]['known_union_bases']['state'] == 'missing'
    elif case.startswith('bbcols_'):
        from test_mauve_bbcols_calculators import calculate, bbcols, members
        raw = {'bbcols_overlap_duplicate': b'7 1 5 0 1\n7 3 5 0 1\n7 1 5 0 1\n7 8 2 0 1\n',
            'bbcols_partial': b'0 1 3 0 1\n0 4 7 0 x\n',
            'bbcols_duplicate_member': b'0 1 3 0 0\n', 'bbcols_empty': b''}[case]
        value = calculate(bbcols(raw)['value'], chosen=members(0, 1), threshold=2); checks = [(STRUCTURE[2], value)]
        if case == 'bbcols_overlap_duplicate':
            assert [value['intervals'][0][k]['value'] for k in ('union_columns', 'column_placements', 'multiply_represented_columns', 'excess_column_placements')] == [9, 17, 5, 8]
        elif case == 'bbcols_partial': assert value['intervals'][0]['union_columns']['value'] == 3
        elif case == 'bbcols_duplicate_member': assert value['rows'][0]['selected_by_multiplicity'] is None
        else: assert value['rows'] == value['intervals'] == [] and value['status'] == 'partial'
    else:
        from test_xmfa_calculators import toy, alignment, coverage
        raw = {'xmfa_overlap': b'#FormatVersion Mauve1\n>1:1-4 +\nACGT\n=\n>1:2-5 +\nCGTA\n=\n>1:3-4 +\nGT\n=\n',
            'xmfa_duplicate_member': b'#FormatVersion Mauve1\n>1:1-2 +\nAC\n>1:1-2 +\nAC\n>2:1-2 +\nAT\n=\n',
            'xmfa_zero': b'#FormatVersion Mauve1\n>1:0-0 +\n--\n=\n',
            'xmfa_truncated': b'#FormatVersion Mauve1\n>1:1-4 +\nACGT\n'}[case]
        document, _ = toy(raw); aligned = alignment(document); covered = coverage(document)
        checks = [(STRUCTURE[3], aligned), (STRUCTURE[4], covered)]
        if case == 'xmfa_overlap':
            assert [covered['members'][0][k]['value'] for k in ('known_union_bases', 'placement_bases', 'multiply_represented_bases', 'excess_placement_bases')] == [5, 10, 3, 5]
        elif case == 'xmfa_duplicate_member': assert aligned['blocks'][0]['conflicting_members'] == [1]
        elif case == 'xmfa_zero': assert covered['members'][0]['known_union_bases']['value'] == 0
        else: assert covered['members'][0]['membership_completeness'] == 'truncated'
    scientific_barrier(monkeypatch)
    for validator, value in checks:
        assert validator(value) == value
