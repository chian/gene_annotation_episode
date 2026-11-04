"""Finite projections of already saved MSA/MetaCATS measurements.

This module does not parse, calculate scientific quantities, or acquire data.
It checks the original request, scoped saved identities and selected cells, then
copies their values. Authentication of the saved records belongs to the host.
"""
from __future__ import annotations

from copy import deepcopy
from functools import wraps
import json
import math
from urllib.parse import quote

from jsonschema import Draft202012Validator

from .bvbrc_alignment_bundle_contracts import (
    DIAGNOSTIC_CODES, FACT_SCHEMAS, MEASUREMENT_CATALOG, decode_reference,
    encode_reference, validate_parameters, validate_requested_form,
    validate_selection,
)


def _require(ok, code):
    if not ok:
        raise ValueError('bvbrc_alignment_projection_' + code)


def _closed(function):
    @wraps(function)
    def call(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (KeyError, TypeError, IndexError, OverflowError, UnicodeError, RecursionError) as exc:
            raise ValueError('bvbrc_alignment_projection_saved_shape_invalid') from exc
    return call


def _shape(value, keys):
    _require(type(value) is dict and set(value) == set(keys), 'saved_shape_invalid')


def _finite(value):
    if type(value) is dict:
        _require(all(type(k) is str for k in value), 'json_key_invalid')
        for child in value.values():
            _finite(child)
    elif type(value) in (list, tuple):
        for child in value:
            _finite(child)
    elif type(value) is float:
        _require(math.isfinite(value), 'nonfinite_number')
    else:
        _require(value is None or type(value) in (str, bool, int), 'json_value_invalid')


def _same(a, b):
    return json.dumps(a, sort_keys=True, separators=(',', ':'), allow_nan=False) == json.dumps(b, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _index(rows, field):
    _require(type(rows) is list, 'saved_rows_invalid')
    result = {}
    for row in rows:
        key = row[field]
        _require(key not in result, 'saved_identity_ambiguous')
        result[key] = row
    return result


def _one(rows, **fields):
    matches = [r for r in rows if all(k in r and _same(r[k], v) for k, v in fields.items())]
    _require(len(matches) == 1, 'selected_row_unknown_or_ambiguous')
    return matches[0]


def _unique(rows):
    result = []
    for row in rows:
        if row not in result:
            result.append(row)
    return result


def _ref(kind, aid, identity):
    value = encode_reference(kind, aid, identity)
    _require(decode_reference(value) == (kind, aid, identity), 'reference_noncanonical')
    return value


def _test_key(row):
    return row['category_id'], row['column_0based'], row.get('kind', row.get('test_kind')), tuple(row['group_ids'])


def _document_id(wrapper):
    value = wrapper['value']
    return value['alignment_id'] if wrapper['kind'] == 'alignment' else value['table_id'] if wrapper['kind'] in ('msa_frequency', 'metacats_chisq', 'metacats_pair', 'metacats_raw_r') else value['document_id']


_REQUEST_KINDS = {
    'msa_sites': ('msa_entropy',), 'reference_differences': ('msa_reference_differences',),
    'group_counts': ('native_group_counts', 'biological_group_counts'),
    'statistical_tests': ('native_statistics', 'biological_statistics'),
    'function_composition': ('function_composition',), 'tree_branches': ('tree',),
    'multiplicity': ('multiplicity',), 'xmfa_coordinates': ('xmfa_column_coordinates',),
    'xmfa_source_positions': ('xmfa_source_positions',),
    'xmfa_alignment_measurements': ('xmfa_alignment_components',),
    'xmfa_coverage': ('xmfa_interval_coverage',),
}

# Only units/origins are known for an absent cell. In particular, no method or
# population identity is invented (accepted additive contracts 025 and 026).
_UNITS = {}
for _unit, _names in {
    'rows': 'member_count', 'columns': 'site_count difference_category_count pair_identical_positions pair_substitutions pair_both_gap_positions pair_a_gap_only_positions pair_b_gap_only_positions pair_unpaired_nongap_ambiguous_positions',
    'characters': 'cell_count gap_cells canonical_cells ambiguity_cells stop_cells other_nongap_cells site_gap_count site_canonical_count site_ambiguity_count site_stop_count site_other_nongap_count row_nongap_count eligible_count internal_gap_count terminal_gap_excluded_count',
    'fraction': 'gap_fraction canonical_fraction ambiguity_fraction stop_fraction other_nongap_fraction site_gap_fraction site_canonical_fraction site_canonical_majority_fraction row_matrix_occupancy pair_identity_fraction original_member_coverage cramers_v total_variation fraction_all fraction_recorded same_taxon_pair_fraction support_rescaled rf_fraction',
    'bits': 'site_canonical_entropy_bits literal_entropy_bits', 'positions': 'original_length original_covered_positions',
    'hundredths_of_bit': 'native_score_recalculated score_residual', 'pseudocount_per_cell': 'epsilon',
    'augmented_observations': 'augmented_total continuity_delta',
    'chi_square': 'chi_square raw_chi_square', 'degrees_of_freedom': 'df',
    'probability': 'mathematical_p native_zero_rule_p', 'natural_log_probability': 'log_p',
    'expected_observations': 'minimum_expected raw_minimum_expected',
    'cells': 'cells_below_5 cells_below_1 cell_denominator raw_cells_below_5 raw_cells_below_1 raw_cell_denominator',
    'signed_fraction': 'frequency_delta',
    'members': 'total_members members_with_recorded_assignment members_without_recorded_assignment assigned_members known_members unknown_members taxon_member_count',
    'taxa': 'distinct_known_taxa', 'pairs': 'same_taxon_pairs known_taxon_pairs',
    'tips': 'tip_count matched_tips', 'nodes': 'internal_node_count rooted_representation_polytomies unrooted_degree_polytomies',
    'edges': 'missing_branch_length_count', 'splits': 'gene_splits organismal_splits shared_splits rf',
    'native_unknown': 'branch_length branch_length_sum known_branch_length_sum patristic_distance',
}.items():
    _UNITS.update(dict.fromkeys(_names.split(), _unit))


class _Projection:
    def __init__(self, *, sheet_set, component_set, missing_requirements, diagnostics,
                 requested_form, parameters, provider):
        self.provider = provider
        self.parameters = validate_parameters(parameters, provider=provider)
        self.form = validate_requested_form(requested_form, provider=provider)
        _finite((sheet_set, component_set, missing_requirements, diagnostics))
        self.requirements = list(missing_requirements)
        self.diagnostics = list(diagnostics)
        self.req = _index(self.requirements, 'requirement_id')
        for row in self.requirements:
            _shape(row, ('requirement_id', 'kind', 'role', 'source_refs', 'reason_code'))
            # Use the actual public outward contract to check finite enums and
            # reference syntax without converting any source Store reference.
            _require(Draft202012Validator(FACT_SCHEMAS['missing_requirements']).is_valid([self.requirement_fact(row)]), 'requirement_invalid')
        for row in self.diagnostics:
            _shape(row, ('code', 'phase', 'path', 'severity', 'evidence_refs'))
            _require(type(row['code']) is str and row['code'] and type(row['path']) is str and type(row['evidence_refs']) is list, 'diagnostic_invalid')
        self.plans = {p['analysis']['analysis_id']: p for p in self.parameters['analyses']}
        self.plan_indices = {p['analysis']['analysis_id']: i for i, p in enumerate(self.parameters['analyses'])}
        self.original = {a: _index(p['calculation_parameters']['requests'], 'request_id') for a, p in self.plans.items()}
        self.slots = {(s['analysis_id'], s['slot_id']): s for s in self.parameters['artifact_selection']}
        self.selections, self.sheets, self.components, self.outcomes = {}, {}, {}, {}
        self.analysis_reports = {}
        self.families = {}
        self.global_plans = _index(self.parameters['multiplicity_families'], 'family_request_id')
        if sheet_set is not None:
            _shape(sheet_set, ('schema_version', 'tool', 'selections', 'analyses'))
            _require(sheet_set['schema_version'] == 'bvbrc_alignment_sheet_set_v1' and sheet_set['tool'] == ('C-L204-MSA' if provider == 'msa' else 'C-L205-MetaCATS'), 'sheet_set_identity_conflict')
            rows = _index(sheet_set['analyses'], 'analysis_id')
            _require(set(rows) == set(self.plans), 'analysis_population_conflict')
            for row in sheet_set['selections']:
                key = row['analysis_id'], row['slot_id']
                _require(key in self.slots and key not in self.selections, 'slot_identity_conflict')
                _shape(row, ('analysis_id', 'slot_id', 'semantic_role', 'source', 'reader', 'state', 'artifacts', 'content_bindings', 'acquisition_receipt_refs', 'document_ids', 'tree_ids', 'requirement_ids', 'diagnostics'))
                _require(all(_same(row[k], self.slots[key][k]) for k in ('semantic_role', 'source', 'reader')), 'slot_selection_conflict')
                _require(row['state'] in ('resolved', 'missing', 'ambiguous', 'incomplete', 'invalid', 'retained_unparsed'), 'slot_state_invalid')
                self.refs(row['requirement_ids']); self.selections[key] = row
            _require(set(self.selections) == set(self.slots), 'slot_population_conflict')
            for aid, row in rows.items():
                _shape(row, ('analysis_id', 'status', 'sheet', 'requirements', 'diagnostics'))
                _require(row['status'] in ('ok', 'partial', 'invalid'), 'analysis_status_invalid')
                self.reports(row)
                self.analysis_reports[aid] = row
                sheet = row['sheet']; self.sheets[aid] = sheet
                if sheet is not None:
                    _require(sheet['schema_version'] == 'bvbrc_' + provider + '_sheet_v1' and sheet['tool'] == sheet_set['tool'], 'sheet_identity_conflict')
                    _require(sheet['analysis']['analysis_id'] == aid and sheet['analysis']['mode'] == self.plans[aid]['analysis']['mode'], 'analysis_mode_conflict')
                    self.reports(sheet)
                    docs = {_document_id(d): d for d in sheet['documents']}
                    _require(len(docs) == len(sheet['documents']), 'document_identity_ambiguous')
                    for key, selected in self.selections.items():
                        if key[0] == aid:
                            _require(all(d in docs for d in selected['document_ids']), 'slot_document_unknown')
                            reads = [r for r in sheet['read_outcomes'] if r['slot_id'] == key[1]]
                            if selected['document_ids']:
                                _require(len(reads) == 1 and reads[0]['document_ids'] == selected['document_ids'] and reads[0]['reader'] == selected['reader'], 'slot_document_binding_conflict')
                    self.check_analysis(aid, sheet)
        elif component_set is not None:
            _require(False, 'components_without_sheet_set')
        if component_set is not None:
            _shape(component_set, ('schema_version', 'analyses', 'multiplicity_families'))
            _require(component_set['schema_version'] == 'bvbrc_alignment_component_set_v1', 'component_set_identity_conflict')
            rows = _index(component_set['analyses'], 'analysis_id')
            _require(set(rows) == set(self.plans), 'component_analysis_population_conflict')
            for aid, row in rows.items():
                _shape(row, ('analysis_id', 'components'))
                comp = row['components']; self.components[aid] = comp
                if comp is None:
                    continue
                _require(self.sheets.get(aid) is not None, 'components_without_sheet')
                _shape(comp, ('schema_version', 'analysis_id', 'parameters', 'results', 'requirements', 'diagnostics'))
                _require(comp['schema_version'] == 'bvbrc_' + provider + '_components_v1' and comp['analysis_id'] == aid, 'components_identity_conflict')
                self.reports(comp)
                saved_requests = _index(comp['parameters']['requests'], 'request_id')
                _require(comp['parameters']['version'] == self.plans[aid]['calculation_parameters']['version'], 'parameters_version_conflict')
                _require(set(saved_requests) <= set(self.original[aid]), 'saved_request_not_original')
                for rid, request in self.original[aid].items():
                    if rid not in saved_requests:
                        _require(self.quarantine(aid, rid), 'request_omission_unqualified')
                    else:
                        _require(_same(saved_requests[rid], self.compile_request(aid, request)), 'original_request_conflict')
                outcomes = _index(comp['results'], 'request_id')
                _require(list(outcomes) == list(saved_requests), 'result_request_population_conflict')
                self.outcomes[aid] = outcomes
                for rid, outcome in outcomes.items():
                    _shape(outcome, ('request_id', 'kind', 'status', 'value', 'requirements', 'diagnostics'))
                    _require(outcome['kind'] == saved_requests[rid]['kind'] and outcome['status'] in ('ok', 'partial', 'invalid'), 'result_kind_conflict')
                    self.reports(outcome)
                    if outcome['value'] is None:
                        _require(outcome['status'] != 'ok' and outcome['requirements'], 'null_result_unqualified')
                    else:
                        _require(outcome['status'] != 'invalid', 'invalid_result_has_value')
                        self.check_result(aid, saved_requests[rid], outcome['value'])
            self.families = _index(component_set['multiplicity_families'], 'family_request_id')
            _require(set(self.families) == set(self.global_plans), 'family_population_conflict')
            for row in self.families.values():
                _shape(row, ('family_request_id', 'status', 'value', 'requirements', 'diagnostics')); self.reports(row)
                _require(row['status'] in ('ok', 'partial', 'invalid') and (row['value'] is not None or row['status'] != 'ok' and row['requirements']), 'family_status_conflict')

    def refs(self, ids):
        _require(type(ids) is list and all(type(i) is str and i in self.req for i in ids), 'requirement_reference_unknown')
        return [_ref('requirement', '@requirements', i) for i in _unique(ids)]

    def reports(self, value):
        for req in value.get('requirements', value.get('missing_requirements', [])):
            _require(req['requirement_id'] in self.req and _same(req, self.req[req['requirement_id']]), 'requirement_record_conflict')
        for diag in value.get('diagnostics', []):
            _require(diag in self.diagnostics, 'diagnostic_record_conflict')

    def requirement_fact(self, row):
        return {'requirement_ref': _ref('requirement', '@requirements', row['requirement_id']),
            'kind': row['kind'], 'role_ref': None if row['role'] is None else _ref('role', '@requirements', row['role']),
            'source_refs': deepcopy(row['source_refs']), 'reason_ref': _ref('reason', '@requirements', row['reason_code'])}

    def quarantine(self, aid, rid):
        pos = list(self.original[aid]).index(rid)
        path = f'/analyses/{self.plan_indices[aid]}/calculation_parameters/requests/{pos}'
        identity = 'alignment-bundle/' + '/'.join(quote(v, safe='') for v in (self.provider, aid, path, 'alignment_calculation_dependency_unavailable'))
        row = self.req.get(identity)
        return [row] if row is not None and row['role'] == rid and row['reason_code'] == 'alignment_calculation_dependency_unavailable' else []

    def resolve(self, aid, ref):
        _require(ref['analysis_id'] == aid and (aid, ref['slot_id']) in self.slots, 'slot_reference_unknown')
        selected = self.selections.get((aid, ref['slot_id']))
        if selected is None or not selected['document_ids']:
            return None
        if 'tree_index' in ref:
            sheet = self.sheets.get(aid)
            _require(sheet is not None, 'tree_sheet_missing')
            trees = [t for d in sheet['documents'] if d['kind'] == 'tree' and d['value']['document_id'] in selected['document_ids'] for t in d['value']['trees'] if t['tree_index'] == ref['tree_index']]
            return _one(trees)['tree_id']
        _require(len(selected['document_ids']) == 1, 'slot_document_ambiguous')
        return selected['document_ids'][0]

    def compile_request(self, aid, request):
        result = deepcopy(request)
        for key in ('alignment_id', 'observed_table_id', 'document_id', 'gene_tree_id', 'organismal_tree_id'):
            if key in result and result[key] is not None:
                result[key] = self.resolve(aid, result[key])
        if request['kind'] == 'msa_reference_differences':
            result['reference']['alignment_id'] = self.resolve(aid, request['reference']['alignment_id'])
        if request['kind'] == 'relationship_comparison':
            for row in result['injective_tip_join']:
                for key in ('gene_tree_id', 'organismal_tree_id'):
                    row[key] = self.resolve(aid, row[key])
        if request['kind'].startswith('xmfa_') and 'selection' in result:
            result['selection']['document_id'] = self.resolve(aid, request['selection']['document_id'])
        if request['kind'] == 'multiplicity' and request['p_values']['kind'] == 'native_tables':
            result['p_values']['table_ids'] = [self.resolve(aid, r) for r in request['p_values']['table_ids']]
        return result

    def check_analysis(self, aid, sheet):
        original, saved = self.plans[aid]['analysis'], sheet['analysis']
        for key, val in original.items():
            if key in ('reference', 'output_role_evidence'):
                continue
            if type(val) is dict:
                _require(saved[key] == self.resolve(aid, val), 'analysis_document_conflict')
            elif type(val) is list and val and type(val[0]) is dict:
                _require(saved[key] == [d for r in val if (d := self.resolve(aid, r)) is not None], 'analysis_documents_conflict')
            else:
                _require(_same(saved[key], val), 'analysis_original_conflict')
        if original.get('reference') is not None and saved.get('reference') is not None:
            expected = deepcopy(original['reference'])
            expected['alignment_id'] = self.resolve(aid, expected['alignment_id'])
            _require(all(_same(expected[k], saved['reference'][k]) for k in expected if k != 'identity_state'), 'analysis_reference_conflict')
            _require(saved['reference']['identity_state'] == expected['identity_state'] or expected['identity_state'] == 'resolved' and saved['reference']['identity_state'] == 'unresolved', 'reference_state_conflict')

    def population(self, aid, request):
        pid = request.get('population_id')
        if pid is None:
            return None
        sheet = self.sheets.get(aid)
        if sheet is None:
            return None
        kind = 'composition' if request['kind'] == 'function_composition' else 'taxonomy' if request['kind'] == 'taxonomy' else 'leaves' if request['kind'] == 'tree' else 'alignments'
        rows = [p for p in sheet['populations'][kind] if p['population_id'] == pid]
        _require(len(rows) <= 1, 'population_ambiguous')
        if not rows:
            return None
        pop = rows[0]
        planned = _one(self.plans[aid]['population_plans'], **({'population_id': pid} if kind in ('alignments', 'leaves') else {})) if kind in ('alignments', 'leaves') else _one([p['population'] for p in self.plans[aid]['population_plans'] if p['kind'] == kind], population_id=pid)
        if kind in ('composition', 'taxonomy'):
            _require(_same(pop, planned), 'population_original_conflict')
        else:
            field = 'tree' if kind == 'leaves' else 'alignment'
            _require(pop[field + '_id'] == self.resolve(aid, planned[field]), 'population_document_conflict')
            if planned['kind'] == 'alignment_subset':
                _require(pop['row_indices'] == planned['row_indices'] and pop['columns_0based'] == planned['columns_0based'], 'population_subset_conflict')
            elif kind == 'alignments':
                document = _one([d['value'] for d in sheet['documents'] if d['kind'] == 'alignment'], alignment_id=pop['alignment_id'])
                width = document['observed_column_count']
                if width is None:
                    width = document['declared_column_count']
                if width is None:
                    width = max((len(r['sequence']) for r in document['rows']), default=0)
                _require(pop['row_indices'] == [r['row_index'] for r in document['rows']] and pop['columns_0based'] == list(range(width)), 'whole_population_conflict')
            else:
                tree = _one([t for d in sheet['documents'] if d['kind'] == 'tree' for t in d['value']['trees']], tree_id=pop['tree_id'])
                _require(pop['node_indices'] == [n['node_index'] for n in tree['nodes'] if not n['child_indices']], 'leaf_population_conflict')
        return pop

    def check_result(self, aid, request, value):
        kind = request['kind']
        if type(value) is not dict:
            _require(kind == 'ungapped_map' and type(value) is list, 'result_shape_invalid'); return
        self.reports(value)
        if 'analysis_id' in value:
            _require(value['analysis_id'] == aid, 'result_analysis_conflict')
        if 'category_id' in value:
            source = request
            while 'counts_request_id' in source or 'statistics_request_id' in source:
                source = self.original[aid][source.get('counts_request_id', source.get('statistics_request_id'))]
            _require(value['category_id'] == source['category_id'], 'result_category_conflict')
        if 'population_id' in request:
            population = self.population(aid, request)
            _require(population is not None and value['population_id'] == population['population_id'], 'result_population_conflict')
            for key in ('alignment_id', 'tree_id'):
                if key in population:
                    _require(value[key] == population[key], 'result_document_conflict')
        if kind.startswith('xmfa_'):
            _require(self.plans[aid]['analysis']['mode'] == 'mauve_blocks' and value['document_id'] == request['document_id'], 'xmfa_document_or_mode_conflict')
            if 'selection' in request:
                _require(_same(value['selection'], request['selection']), 'xmfa_selection_conflict')
                document = _one([d['value'] for d in self.sheets[aid]['documents'] if d['kind'] == 'xmfa'], document_id=request['document_id'])
                known_members = {r['member_number']['value'] for b in document['blocks'] for r in b['records'] if r['member_number']['state'] == 'available' and r['member_number']['value'] > 0}
                known_members.update(m['member_number']['value'] for m in document.get('metadata', []) if m.get('member_number') is not None and m['member_number']['state'] == 'available' and m['member_number']['value'] > 0)
                _require(set(request['selection']['member_numbers']) <= known_members, 'xmfa_native_member_unknown')
                for chosen in request['selection']['block_columns']:
                    block = _one(document['blocks'], block_index=chosen['block_index'])
                    bound = max((len(r['sequence']) for r in block['records']), default=0)
                    _require(all(i < bound for i in chosen['columns_0based']), 'xmfa_native_column_unknown')
            if kind == 'xmfa_column_coordinates':
                _require([r['cell'] for r in value['cells']] == request['cells'], 'xmfa_requested_cells_conflict')
            elif kind == 'xmfa_source_positions':
                _require([{k: r[k] for k in ('member_number', 'position_0based')} for r in value['queries']] == request['queries'], 'xmfa_requested_queries_conflict')
            else:
                keys = ('case_policy', 'selected_pairs') if kind == 'xmfa_alignment_components' else ('basis',)
                _require(value['parameters'] == {k: request[k] for k in keys}, 'xmfa_parameters_conflict')
        if kind in ('native_statistics', 'biological_statistics'):
            _require(value['method_parameters'] == {k: v for k, v in request.items() if k not in ('request_id', 'kind', 'counts_request_id')}, 'statistics_parameters_conflict')
        if kind == 'msa_entropy':
            _require(value['method_parameters'] == {k: request[k] for k in ('alphabet', 'case_policy', 'terminal_gap', 'native_rounding')}, 'entropy_parameters_conflict')
        if kind == 'relationship_comparison':
            _require(value['comparison_id'] == request['comparison_id'] and value['matched_tip_pairs'] == request['injective_tip_join'], 'comparison_identity_conflict')
        if kind == 'msa_reference_differences':
            _require(value['reference'] == self.sheets[aid]['analysis']['reference'], 'reference_result_conflict')
        if kind in ('native_effects', 'biological_effects'):
            dependency = self.outcomes[aid][request['counts_request_id']]['value']
            _require(dependency is not None and [(s['column_0based'], s['raw_table_id']) for s in value['sites']] == [(s['column_0based'], s['table_id']) for s in dependency['sites']], 'effect_count_identity_conflict')
            _require(all([pair['group_ids'] for pair in s['pairs']] == request['selected_pairs'] for s in value['sites']), 'effect_selected_pairs_conflict')

    def request(self, selection):
        aid, rid = selection['analysis_id'], selection['request_id']
        _require(aid in self.plans and rid in self.original[aid], 'original_request_unknown')
        request = self.original[aid][rid]
        kinds = MEASUREMENT_CATALOG[selection['metric']]['request_kinds'] if selection['kind'] == 'measurement' else _REQUEST_KINDS[selection['kind']]
        _require(request['kind'] in kinds, 'request_kind_conflict')
        outcome = self.outcomes.get(aid, {}).get(rid)
        return request, None if outcome is None else outcome['value']

    def missing(self, aid, rid=None, slot=None):
        rows = []
        if rid is not None:
            rows += self.quarantine(aid, rid)
            outcome = self.outcomes.get(aid, {}).get(rid)
            if outcome is not None:
                rows += outcome['requirements']
        if slot is not None and (aid, slot) in self.selections:
            rows += [self.req[i] for i in self.selections[aid, slot]['requirement_ids']]
        if not rows:
            rows += self.analysis_reports.get(aid, {}).get('requirements', [])
        if not rows and not self.sheets:
            rows += self.requirements
        _require(bool(rows), 'unavailable_dependency_unqualified')
        return self.refs([r['requirement_id'] for r in rows])

    def cell(self, aid, cell, *, population=None, unit=None):
        numeric = 'method_id' in cell
        keys = ('value', 'state', 'unit', 'origin', 'numerator', 'denominator', 'population_id', 'method_id', 'evidence', 'uncertainty', 'requirement_ids') if numeric else ('value', 'state', 'unit', 'origin', 'numerator', 'denominator', 'population_ref', 'method', 'evidence', 'requirement_ids')
        _shape(cell, keys)
        pid = cell['population_id' if numeric else 'population_ref']
        _require(population is None or pid == population, 'cell_population_conflict')
        _require(unit is None or cell['unit'] == unit, 'cell_unit_conflict')
        _require((cell['state'] == 'available') == (cell['value'] is not None), 'cell_availability_conflict')
        method = cell['method_id' if numeric else 'method']
        _require(type(method) is str and method, 'cell_method_missing')
        return {'value': cell['value'], 'state': cell['state'], 'unit': cell['unit'], 'origin': cell['origin'],
            'method_ref': _ref('method', aid, method), 'population_ref': _ref('population', aid, pid),
            'numerator': cell['numerator'], 'denominator': cell['denominator'], 'requirement_refs': self.refs(cell['requirement_ids'])}

    def value(self, aid, cell, *, population=None):
        return self.cell(aid, cell, population=population)['value']

    def collected_refs(self, *values):
        ids = []
        def walk(node):
            if type(node) is dict:
                ids.extend(node.get('requirement_ids', []))
                ids.extend(r['requirement_id'] for r in node.get('requirements', node.get('missing_requirements', [])))
                for key, child in node.items():
                    if key not in ('requirements', 'missing_requirements', 'evidence', 'diagnostics'):
                        walk(child)
            elif type(node) is list:
                for child in node:
                    walk(child)
        for value in values:
            walk(value)
        return self.refs(_unique(ids))

    def scope(self, aid, request, selection):
        """Check explicitly selected indices even when a dependency is missing."""
        pop = self.population(aid, request)
        fields = selection.get('selector', selection)
        if pop is None and 'population_id' in request:
            planned = next((v for v in self.plans[aid]['population_plans'] if v.get('population_id') == request['population_id']), None)
            if planned is not None and planned['kind'] == 'alignment_subset':
                pop = planned
        if pop is not None and 'columns_0based' in pop:
            columns = list(fields.get('columns_0based', [fields['column_0based']] if 'column_0based' in fields else []))
            if 'test' in fields:
                columns += [fields['test']['column_0based']]
            columns += [t['column_0based'] for t in fields.get('tests', [])]
            _require(set(columns) <= set(pop['columns_0based']), 'column_outside_population')
            rows = fields.get('row_indices', [fields['row_index']] if 'row_index' in fields else [])
            _require(set(rows) <= set(pop['row_indices']), 'row_outside_population')
        if request['kind'] == 'alignment' and 'row_a' in fields:
            _require([fields['row_a'], fields['row_b']] in request['pairs'], 'pair_not_requested')
        if request['kind'] == 'tree' and 'node_a' in fields:
            _require([fields['node_a'], fields['node_b']] in request['pairs'], 'tree_pair_not_requested')
        if request['kind'] == 'msa_reference_differences':
            rows = fields.get('row_indices', [fields['row_index']] if 'row_index' in fields else [])
            _require(set(rows) <= set(request['member_row_indices']), 'reference_row_not_requested')
        if request['kind'] in ('native_statistics', 'biological_statistics', 'native_effects', 'biological_effects', 'expected_adequacy'):
            source = self.original[aid][request.get('counts_request_id', request.get('statistics_request_id'))]
            self.scope(aid, source, selection)
            tests = fields.get('tests', [fields['test']] if 'test' in fields else [])
            if request['kind'] != 'expected_adequacy':
                for test in tests:
                    if test['kind'] == 'pairwise':
                        _require(test['group_ids'] in request['selected_pairs'], 'test_pair_not_requested')
                if 'group_ids' in fields:
                    _require(fields['group_ids'] in request['selected_pairs'], 'effect_pair_not_requested')
        if 'category_id' in request:
            for test in fields.get('tests', [fields['test']] if 'test' in fields else []):
                _require(test['category_id'] == request['category_id'], 'test_category_conflict')
        if request['kind'] == 'xmfa_column_coordinates':
            _require(all(c in request['cells'] for c in selection['cells']), 'xmfa_cell_not_requested')
        if request['kind'] == 'xmfa_source_positions':
            _require(all(q in request['queries'] for q in selection['queries']), 'xmfa_query_not_requested')
        if request['kind'] in ('xmfa_alignment_components', 'xmfa_interval_coverage'):
            chosen = request['selection']
            if 'member_numbers' in selection:
                _require(set(selection['member_numbers']) <= set(chosen['member_numbers']), 'xmfa_member_not_requested')
            blocks = _index(chosen['block_columns'], 'block_index')
            for metric in selection.get('measurements', []):
                _require(metric['block_index'] in blocks, 'xmfa_block_not_requested')
                if 'column_0based' in metric:
                    _require(metric['column_0based'] in blocks[metric['block_index']]['columns_0based'], 'xmfa_column_not_requested')
                if 'member_a' in metric:
                    _require([metric['member_a'], metric['member_b']] in request['selected_pairs'], 'xmfa_pair_not_requested')

    def measurement(self, selection, request, value):
        aid, metric, selector = selection['analysis_id'], selection['metric'], selection['selector']
        kind = request['kind']
        if value is None:
            shared = kind in ('alignment', 'original_coverage', 'function_composition', 'taxonomy', 'tree', 'relationship_comparison')
            origin = 'native_observed' if metric == 'original_length' else 'native_fitted' if metric == 'branch_length' else 'derived' if shared else 'calculated'
            return {'value': None, 'state': 'missing', 'unit': _UNITS[metric], 'origin': origin, 'method_ref': None,
                'population_ref': None, 'numerator': None, 'denominator': None,
                'requirement_refs': self.missing(aid, request['request_id'])}
        pid = value.get('population_id', value.get('comparison_id'))
        if kind == 'alignment':
            if metric.startswith('site_') and metric != 'site_count':
                cell = _one(value['sites'], column_0based=selector['column_0based'])[metric[5:]]
            elif metric.startswith('row_'):
                cell = _one(value['rows'], row_index=selector['row_index'])[metric[4:]]
            elif metric.startswith('pair_'):
                cell = _one(value['pairs'], row_a=selector['row_a'], row_b=selector['row_b'])[metric[5:]]
            else:
                cell = value[metric]
        elif kind == 'original_coverage':
            cell = _one(value['rows'], row_index=selector['row_index'], member={k: selector[k] for k in ('input_binding_id', 'member_id')})[metric]
        elif kind == 'msa_entropy':
            cell = _one(value['sites'], column_0based=selector['column_0based'])[metric]
        elif kind == 'msa_reference_differences':
            cell = _one(value['counts'], row_index=selector['row_index'], category=selector['category'])['count']
        elif kind in ('native_statistics', 'biological_statistics', 'expected_adequacy'):
            row = self.test_row(aid, request, value, selector['test']); cell = row[metric]; pid = row['test_id']
        elif kind in ('native_effects', 'biological_effects'):
            row = _one(value['sites'], column_0based=selector['column_0based']); pid = row['raw_table_id']
            if metric in ('total_variation', 'frequency_delta'):
                pair = _one(row['pairs'], group_ids=selector['group_ids'])
                cell = pair['total_variation'] if metric == 'total_variation' else _one(pair['frequency_deltas'], symbol=selector['symbol'])['value']
            elif metric.startswith('raw_') and metric != 'raw_chi_square':
                cell = row['raw_adequacy'][metric[4:]]
            else:
                cell = row[metric]
        elif kind == 'function_composition':
            cell = _one(value['rows'], function_key=selector['function_key'])[metric] if selector else value[metric]
        elif kind == 'taxonomy':
            cell = _one(value['rows'], taxon_id=selector['taxon_id'])['member_count'] if selector else value[metric]
        elif kind == 'tree':
            if metric == 'patristic_distance':
                cell = _one(value['distances'], node_a=selector['node_a'], node_b=selector['node_b'])['value']
            elif metric in ('branch_length', 'support_rescaled'):
                cell = _one(value['branches'], node_index=selector['node_index'])['length' if metric == 'branch_length' else metric]
            else:
                cell = value[metric]
        else:
            cell = value[metric]
        return self.cell(aid, cell, population=pid, unit=None if _UNITS[metric] == 'native_unknown' else _UNITS[metric])

    def test_row(self, aid, request, value, selected):
        rows = value['rows'] if request['kind'] == 'expected_adequacy' else value['omnibus'] + value['pairs']
        row = _one([r for r in rows if _test_key({**r, 'category_id': value['category_id']}) == _test_key(selected)])
        _require('category_id' not in row or row['category_id'] == value['category_id'], 'test_category_conflict')
        source = request
        if request['kind'] == 'expected_adequacy':
            source = self.original[aid][request['statistics_request_id']]
            dependency = self.outcomes[aid][source['request_id']]['value']
            actual = self.test_row(aid, source, dependency, selected)
            _require(row['test_id'] == actual['test_id'] and row['raw_table_id'] == actual['raw_table_id'], 'adequacy_test_conflict')
        else:
            counts = self.outcomes[aid][source['counts_request_id']]['value']
            _require(counts is not None, 'test_counts_missing')
            site = _one(counts['sites'], column_0based=selected['column_0based'])
            _require(row['raw_table_id'] == site['table_id'], 'test_count_identity_conflict')
            groups = self.groups(aid, self.original[aid][source['counts_request_id']], counts)
            _require(row['group_ids'] == groups if row['kind'] == 'omnibus' else row['group_ids'] in source['selected_pairs'], 'test_group_population_conflict')
        return row

    def groups(self, aid, request, value):
        sheet = self.sheets[aid]; cat = request['category_id']
        _require(cat in sheet['analysis']['category_ids'], 'category_not_in_analysis')
        if request['kind'] == 'biological_group_counts':
            saved = _one(sheet['biological_group_populations'], group_population_id=request['group_population_id'])
            _require(saved == value['group_population'] and saved['category_id'] == cat, 'group_population_conflict')
            groups = [r['group_id'] for r in saved['groups']]
        else:
            saved = [r for r in sheet['native_group_columns'] if r['category_id'] == cat]
            _require(saved == value['group_order'], 'native_group_order_conflict')
            groups = [r['group_id'] for r in saved]
        _require(len(groups) == len(set(groups)), 'group_identity_ambiguous')
        return groups

    def native(self, selection):
        aid, slot = selection['analysis_id'], selection['table']['slot_id']
        _require(aid in self.plans and (aid, slot) in self.slots, 'native_slot_unknown')
        reader = self.slots[aid, slot]['reader']; field = selection['field']; kind = field['kind']
        allowed = {'msa_frequency': ('score', 'n_sequences', 'dna_count', 'protein_count'),
            'metacats_chisq': ('chi_square', 'p_value', 'df', 'export_group_count'),
            'metacats_pair': ('p_value',), 'metacats_raw_r': ('chi_square', 'p_value', 'df', 'raw_r_group_count')}
        _require(reader is not None and kind in allowed.get(reader['reader'], ()), 'native_field_reader_conflict')
        if reader['reader'] == 'msa_frequency' and kind in ('dna_count', 'protein_count'):
            _require(reader['alphabet'] == ('dna' if kind == 'dna_count' else 'protein'), 'native_alphabet_conflict')
        if reader['reader'] == 'metacats_raw_r' and reader['kind'] == 'pairwise':
            _require(kind == 'p_value', 'native_field_reader_conflict')
        tid = self.resolve(aid, selection['table'])
        units = {'score': 'hundredths_of_bit', 'n_sequences': 'sequences', 'chi_square': 'chi_square', 'p_value': 'probability', 'df': 'degrees_of_freedom'}
        if tid is None or self.sheets.get(aid) is None:
            return {'value': None, 'state': 'missing', 'unit': units.get(kind, 'observations'), 'origin': 'native_observation', 'method_ref': None, 'population_ref': None, 'numerator': None, 'denominator': None, 'requirement_refs': self.missing(aid, slot=slot)}
        sheet = self.sheets[aid]; wrapper = _one([d for d in sheet['documents'] if _document_id(d) == tid]); table = wrapper['value']
        rows = table['rows'] if 'rows' in table else table['omnibus_rows'] if table['kind'] == 'omnibus' else table['pair_rows']
        row = _one(rows, row_index=selection['row_index']); indices = []
        if kind == 'dna_count':
            number = row['dna_counts'][field['symbol']]; indices = [('A', 'T', 'G', 'C', 'Deletion').index(field['symbol'])]; native_field = 'msa_symbol_count'; suffix = 'dna_counts/' + field['symbol']
        elif kind == 'protein_count':
            _require(field['detail_index'] < len(row['protein_detail']), 'native_detail_unknown')
            number = row['protein_detail'][field['detail_index']]['count']; indices = [field['detail_index']]; native_field = 'msa_symbol_count'; suffix = 'protein_detail/' + str(field['detail_index']) + '/count'
        elif kind in ('export_group_count', 'raw_r_group_count'):
            collection = row['group_cells' if kind == 'export_group_count' else 'positional_groups']
            index_key = 'heading_index' if kind == 'export_group_count' else 'position_1based'
            group = _one(collection, **{index_key: field[index_key]})
            _require(field['count_index'] < len(group['symbol_counts']), 'native_count_unknown')
            number = group['symbol_counts'][field['count_index']]['count']; indices = [collection.index(group), field['count_index']]; native_field = 'metacats_symbol_count'
            suffix = ('group_cells' if kind == 'export_group_count' else 'positional_groups') + '/' + str(indices[0]) + '/symbol_counts/' + str(indices[1]) + '/count'
        else:
            number = row[kind]
            native_field = {'score': 'msa_score', 'n_sequences': 'msa_sequence_count', 'chi_square': 'metacats_chi_square', 'p_value': 'metacats_p_value', 'df': 'metacats_df'}[kind]
            suffix = kind
        observation = _one(sheet['native_observations'], document_id=tid, row_index=selection['row_index'], field=native_field, nested_indices=indices)
        _require(_same(number, observation['number']) and observation['unit'] == units.get(kind, 'observations'), 'native_observation_source_conflict')
        _require(observation['observation_id'] == tid + '/rows/' + str(row['row_index']) + '/' + suffix, 'native_observation_identity_conflict')
        if self.provider == 'metacats':
            _require(observation['category_id'] == table['category_id'] == reader['category_id'], 'native_category_conflict')
            tests = [t for t in sheet['native_test_associations'] if t['table_id'] == tid and t['row_index'] == row['row_index']]
            _require(len(tests) <= 1 and observation['population_id'] == (tests[0]['test_id'] if tests else None), 'native_test_population_conflict')
        elif observation['population_id'] is not None:
            population = _one(sheet['populations']['alignments'], population_id=observation['population_id'])
            _require(population['alignment_id'] == sheet['analysis']['alignment_id'] and tid == sheet['analysis']['frequency_table_id'], 'native_alignment_population_conflict')
        related = [r['requirement_id'] for r in sheet['requirements'] if r['role'] in (tid, observation['observation_id'])]
        return {'value': number['value'] if number['state'] == 'available' else None, 'state': number['state'], 'unit': observation['unit'], 'origin': 'native_observation',
            'method_ref': None, 'population_ref': None if observation['population_id'] is None else _ref('population', aid, observation['population_id']),
            'numerator': None, 'denominator': None, 'requirement_refs': self.refs(related)}

    def occurrence(self, aid, key):
        members = self.sheets[aid]['associations']['original_members']
        candidates = [r['key'] for r in members if all(r['key'][k] == v for k, v in key.items())]
        actual = _one([{'key': r} for r in candidates])['key']
        identity = 'input_member_occurrence:' + quote(actual['input_binding_id'], safe='') + '/' + quote(actual['member_id'], safe='') + '/' + str(actual['occurrence_index'])
        return _ref('member', aid, identity)

    def original_coordinate(self, aid, mapping):
        if mapping is None or mapping['original_member'] is None or mapping['original_interval_0based_half_open'] is None:
            return None
        _require(mapping in self.sheets[aid]['associations']['correspondences'], 'coordinate_proof_missing')
        transform = mapping['transformation_id']
        if transform is not None:
            _one(self.sheets[aid]['associations']['transformations'], transformation_id=transform)
        return {'member_ref': self.occurrence(aid, mapping['original_member']),
            'interval_0based_half_open': deepcopy(mapping['original_interval_0based_half_open']), 'strand': mapping['strand'],
            'translation_table': mapping['translation_table'], 'transformation_ref': None if transform is None else _ref('transformation', aid, transform)}

    def rows(self, selection, request, value):
        aid, kind = selection['analysis_id'], selection['kind']
        if value is None:
            self.missing(aid, request['request_id']); return None
        pid = value.get('population_id'); result = []
        if kind == 'msa_sites':
            keys = ('eligible_count', 'internal_gap_count', 'terminal_gap_excluded_count', 'literal_entropy_bits', 'native_score_recalculated', 'score_residual')
            for column in selection['columns_0based']:
                row = _one(value['sites'], column_0based=column)
                result.append({'alignment_ref': _ref('alignment', aid, value['alignment_id']), 'population_ref': _ref('population', aid, pid), 'column_0based': column,
                    **{k: self.value(aid, row[k], population=pid) for k in keys}, 'strict_majority_consensus': row['strict_majority_consensus'], 'requirement_refs': self.collected_refs(row)})
        elif kind == 'reference_differences':
            for index in selection['row_indices']:
                for column in selection['columns_0based']:
                    matches = [r for r in value['differences'] if r['row_index'] == index and r['column_0based'] == column]
                    if not matches:
                        self.missing(aid, request['request_id']); return None
                    row = _one(matches)
                    alignment = _one([d['value'] for d in self.sheets[aid]['documents'] if d['kind'] == 'alignment'], alignment_id=value['alignment_id'])
                    for axis, source_index in (('member', index), ('reference', value['reference']['row_index'])):
                        source_row = _one(alignment['rows'], row_index=source_index)
                        _require(column < len(source_row['sequence']), 'difference_source_column_unknown')
                        symbol = source_row['sequence'][column]
                        _require(row[axis + '_character'] == (symbol.upper() if request['case_policy'] == 'uppercase' else symbol), 'difference_character_source_conflict')
                        mapping = row[axis + '_original_correspondence']
                        if mapping is not None:
                            _require(mapping['alignment_id'] == value['alignment_id'] and mapping['row_index'] == source_index and mapping['column_0based'] == column, 'difference_coordinate_identity_conflict')
                    result.append({'alignment_ref': _ref('alignment', aid, value['alignment_id']), **{k: row[k] for k in ('row_index', 'column_0based', 'member_character', 'reference_character', 'category', 'member_ungapped_position_0based', 'reference_ungapped_position_0based')},
                        'member_original': self.original_coordinate(aid, row['member_original_correspondence']), 'reference_original': self.original_coordinate(aid, row['reference_original_correspondence'])})
        elif kind == 'group_counts':
            _require(all(len(s) == 1 and s.isascii() and not s.isspace() for s in selection['symbols']), 'count_symbol_invalid')
            groups = self.groups(aid, request, value)
            _require(set(selection['group_ids']) <= set(groups), 'group_outside_population')
            for column in selection['columns_0based']:
                row = _one(value['sites'], column_0based=column)
                complete = row['completeness'] == 'complete' and row['state'] != 'unresolved'
                for gid in selection['group_ids']:
                    for symbol in selection['symbols']:
                        count = row['observed_counts'][row['symbols'].index(symbol)][groups.index(gid)] if symbol in row['symbols'] else 0
                        refs = self.collected_refs(value) if not complete else []
                        _require(complete or refs, 'incomplete_counts_unqualified')
                        result.append({'alignment_ref': _ref('alignment', aid, value['alignment_id']), 'population_ref': _ref('population', aid, pid), 'category_ref': _ref('category', aid, value['category_id']), 'group_ref': _ref('group', aid, gid), 'column_0based': column, 'symbol': symbol,
                            'count': count if complete else None, 'basis': 'biological' if request['kind'] == 'biological_group_counts' else 'native_reproduction', 'state': 'available' if complete else 'truncated' if row['completeness'] == 'truncated' else 'missing', 'requirement_refs': refs})
        elif kind == 'statistical_tests':
            for test in selection['tests']:
                row = self.test_row(aid, request, value, test); testid = row['test_id']
                result.append({'test_ref': _ref('test', aid, testid), 'category_ref': _ref('category', aid, value['category_id']), 'column_0based': row['column_0based'], 'kind': row['kind'], 'group_refs': [_ref('group', aid, g) for g in row['group_ids']],
                    'basis': 'biological' if request['kind'] == 'biological_statistics' else 'native_reproduction',
                    **{out: self.value(aid, row[source], population=testid) for out, source in (('chi_square', 'chi_square'), ('df', 'df'), ('p_value', 'mathematical_p'), ('log_p', 'log_p'))},
                    'native_zero_rule_p': None if request['kind'] == 'biological_statistics' else self.value(aid, row['native_zero_rule_p'], population=testid), 'numerical_state': row['numerical_state'], 'requirement_refs': self.collected_refs(row)})
        elif kind == 'function_composition':
            for function in selection['function_keys']:
                row = _one(value['rows'], function_key=function)
                result.append({'population_ref': _ref('population', aid, pid), 'function_ref': _ref('function', aid, function),
                    **{k: self.value(aid, (row if k in row else value)[k], population=pid) for k in ('assigned_members', 'total_members', 'members_with_recorded_assignment', 'fraction_all', 'fraction_recorded')}, 'requirement_refs': self.collected_refs(row, value['total_members'], value['members_with_recorded_assignment'])})
        elif kind == 'tree_branches':
            tree = _one([t for d in self.sheets[aid]['documents'] if d['kind'] == 'tree' for t in d['value']['trees']], tree_id=value['tree_id'])
            for node in selection['node_indices']:
                row = _one(value['branches'], node_index=node)
                native = _one(tree['nodes'], node_index=node)
                _require(native['parent_index'] is not None and row['length']['value'] == native['branch_length'], 'branch_source_conflict')
                if row['split_id'] is not None:
                    split = _one(value['splits'], split_id=row['split_id']); _require(node in split['edge_node_indices'] and split['tree_id'] == value['tree_id'], 'branch_split_conflict')
                result.append({'tree_ref': _ref('tree', aid, value['tree_id']), 'node_index': node, 'split_ref': None if row['split_id'] is None else _ref('split', aid, row['split_id']),
                    'length': self.value(aid, row['length'], population=pid), 'length_unit': row['length']['unit'], 'support_rescaled': self.value(aid, row['support_rescaled'], population=pid), 'support_method': row['support_method'], 'support_scale': row['support_scale'], 'requirement_refs': self.collected_refs(row)})
        else:
            return self.xmfa_rows(selection, request, value)
        return result

    def xmfa_rows(self, selection, request, value):
        aid, kind, did = selection['analysis_id'], selection['kind'], value['document_id']
        result = []; docref = _ref('xmfa_document', aid, did)
        document = _one([d['value'] for d in self.sheets[aid]['documents'] if d['kind'] == 'xmfa'], document_id=did)
        if kind == 'xmfa_coordinates':
            for cell in selection['cells']:
                row = _one(value['cells'], cell=cell)
                block = _one(document['blocks'], block_index=cell['block_index']); record = _one(block['records'], record_index=cell['record_index'])
                _require(cell['column_0based'] < len(record['sequence']) and row['aligned_symbol'] == record['sequence'][cell['column_0based']], 'xmfa_cell_source_conflict')
                member = record['member_number']; _require(row['member_number'] == (member['value'] if member['state'] == 'available' and member['value'] > 0 else None), 'xmfa_cell_member_conflict')
                source = row['source_coordinate']; originals = []
                if source is not None:
                    binding = _one(self.sheets[aid]['xmfa_bindings'], document_id=did)
                    _require(request['use_source_bindings'] and binding['bindings'] is not None, 'xmfa_source_unrequested')
                    bound_member = _one(binding['bindings']['members'], member_number=row['member_number'])
                    check = _one(binding['bindings']['source_checks'], record={k: cell[k] for k in ('block_index', 'record_index')})
                    _require(bound_member['state'] == 'resolved' and check['state'] == 'match', 'xmfa_source_not_verified')
                    _one(bound_member['components'], file_id=source['file_id'], record_id=source['record_id'], entry_1based=source['entry_1based'])
                    for original in row['original_coordinates']:
                        _require(any(m['original_member'] == original['original_member'] and m['transformation_id'] == original['transformation_id'] and m['file_id'] == source['file_id'] and m['record_id'] == source['record_id'] for m in binding['bindings']['original_maps']), 'xmfa_original_map_unknown')
                        originals.append({'member_ref': self.occurrence(aid, original['original_member']), **{k: original[k] for k in ('position_0based', 'original_length', 'strand')}, 'transformation_ref': _ref('transformation', aid, original['transformation_id'])})
                else:
                    _require(not row['original_coordinates'], 'xmfa_original_without_source')
                result.append({'document_ref': docref, **{k: deepcopy(row[k]) for k in ('cell', 'member_number', 'aligned_symbol', 'state', 'native_position_1based', 'native_position_0based', 'native_strand', 'forward_symbol', 'source_state')},
                    'source_coordinate': None if source is None else {'file_ref': _ref('xmfa_file', aid, source['file_id']), 'record_ref': _ref('xmfa_record', aid, source['record_id']), **{k: source[k] for k in ('entry_1based', 'position_0based', 'strand')}}, 'original_coordinates': originals, 'requirement_refs': self.collected_refs(value)})
        elif kind == 'xmfa_source_positions':
            for query in selection['queries']:
                row = _one(value['queries'], **query)
                _require(row['search_completeness'] == document['completeness'], 'xmfa_inverse_completeness_conflict')
                for cell in row['matches']:
                    record = _one(_one(document['blocks'], block_index=cell['block_index'])['records'], record_index=cell['record_index'])
                    _require(record['member_number']['value'] == query['member_number'] and cell['column_0based'] < len(record['sequence']), 'xmfa_inverse_member_conflict')
                result.append({'document_ref': docref, **{k: deepcopy(row[k]) for k in ('member_number', 'position_0based', 'state', 'matches', 'search_completeness')}, 'requirement_refs': self.collected_refs(value)})
        elif kind == 'xmfa_alignment_measurements':
            pid = value['selection']['population_id']
            for chosen in selection['measurements']:
                block = _one(value['blocks'], block_index=chosen['block_index']); metric = chosen['metric']
                if 'column_0based' in chosen:
                    site = _one(block['sites'], column_0based=chosen['column_0based'])
                    cell = _one(site['symbol_counts'], symbol=chosen['symbol'])['count'] if metric == 'symbol_count' else site['present_member_count' if metric == 'site_present_member_count' else metric]
                elif 'member_a' in chosen:
                    cell = _one(block['pairs'], member_a=chosen['member_a'], member_b=chosen['member_b'])[metric]
                else:
                    cell = block[metric]
                result.append({'document_ref': docref, 'population_ref': _ref('population', aid, pid),
                    'selection': {k: deepcopy(chosen.get(k)) for k in ('metric', 'block_index', 'column_0based', 'symbol', 'member_a', 'member_b')},
                    'measurement': self.cell(aid, cell, population=pid)})
        else:
            pid = value['selection']['population_id']
            fields = ('source_length', 'known_union_bases', 'placement_bases', 'multiply_represented_bases', 'excess_placement_bases', 'selected_coverage_fraction', 'complement_bases')
            for member in selection['member_numbers']:
                row = _one(value['members'], member_number=member)
                originals = None
                if selection['include_original_coverage']:
                    originals = [{'member_ref': self.occurrence(aid, original['original_member']), **{k: self.value(aid, original[k], population=pid) for k in ('original_length', 'known_union_bases', 'coverage_fraction')}, 'mapping_completeness': original['mapping_completeness']} for original in row['original_coverage']]
                result.append({'document_ref': docref, 'population_ref': _ref('population', aid, pid), 'member_number': member, 'basis': value['parameters']['basis'], **{k: self.value(aid, row[k], population=pid) for k in fields},
                    'known_union_intervals': deepcopy(row['known_union_intervals']) if selection['include_intervals'] else None, 'complement_intervals': deepcopy(row['complement_intervals']) if selection['include_intervals'] else None,
                    'membership_completeness': row['membership_completeness'], 'original_coverage': originals, 'requirement_refs': self.collected_refs(row, {'requirements': value['requirements']})})
        return result

    def family_candidates(self, plan, local_aid):
        source = plan['p_values']; candidates = []
        if source['kind'] == 'statistical_results':
            requests = source['requests'] if local_aid is None else [{'analysis_id': local_aid, 'request_id': rid} for rid in source['statistics_request_ids']]
            for item in requests:
                aid, rid = item['analysis_id'], item['request_id']; _require(aid in self.original and rid in self.original[aid], 'family_source_unknown')
                result = self.outcomes.get(aid, {}).get(rid, {}).get('value')
                if result is not None:
                    for row in result['omnibus'] + result['pairs']:
                        if row['kind'] == plan['family']['test_kind']:
                            candidates.append((aid, _test_key(row), row['test_id'], row['mathematical_p']))
        else:
            tables = source['tables'] if local_aid is None else self.original[local_aid][plan['request_id']]['p_values']['table_ids']
            for ref in tables:
                aid = ref['analysis_id']; tid = self.resolve(aid, ref); sheet = self.sheets.get(aid)
                if tid is None or sheet is None:
                    continue
                for row in sheet['native_test_associations']:
                    if row['table_id'] == tid and row['test_id'] is not None and row['test_kind'] == plan['family']['test_kind'] and row['state'] in ('resolved', 'wrong_native_label'):
                        obs = _one(sheet['native_observations'], document_id=tid, row_index=row['row_index'], field='metacats_p_value')
                        candidates.append((aid, _test_key(row), row['test_id'], obs['number']))
        return candidates

    def multiplicity(self, selection):
        aid, rid, fid = selection['analysis_id'], selection['request_id'], selection['family_request_id']
        if fid is None:
            request, value = self.request(selection); plan = request
        else:
            _require(fid in self.global_plans, 'original_family_unknown'); plan = self.global_plans[fid]
            value = self.families.get(fid, {}).get('value')
        for item in selection['tests']:
            _require(item['analysis_id'] in plan['family']['analysis_ids'] and item['test']['category_id'] in plan['family']['category_ids'] and item['test']['kind'] == plan['family']['test_kind'], 'family_test_scope_conflict')
        if value is None:
            if fid is None:
                self.missing(aid, rid)
            else:
                _require(self.families.get(fid, {}).get('requirements') or self.requirements and not self.sheets, 'family_unavailable_unqualified')
            return None
        family = value['family']; expected = {k: v for k, v in plan['family'].items() if k not in ('selection', 'tests', 'total_test_count')}
        _require(all(_same(family[k], v) for k, v in expected.items()), 'family_identity_conflict')
        _require(plan['family']['total_test_count'] is None or family['total_test_count'] == plan['family']['total_test_count'], 'family_count_conflict')
        _require(all(value[k] == plan[k] for k in ('method', 'alpha', 'dependence_assumption')), 'family_parameters_conflict')
        candidates = self.family_candidates(plan, aid)
        by_id = {}
        for scope, key, identity, cell in candidates:
            _require(identity not in by_id or by_id[identity] == (scope, key, cell), 'family_test_ambiguous')
            by_id[identity] = (scope, key, cell)
        rows = _index(value['results'], 'test_id')
        _require(list(rows) == family['test_ids'] and set(rows) <= set(by_id), 'family_result_identity_conflict')
        if selection['selection'] == 'all_family':
            wanted = list(rows)
        else:
            wanted = []
            for test in selection['tests']:
                matching = [identity for identity, (scope, key, _) in by_id.items() if scope == test['analysis_id'] and key == _test_key(test['test']) and identity in rows]
                _require(len(matching) == 1, 'family_selected_test_unknown_or_ambiguous'); wanted += matching
        output = []
        for identity in wanted:
            row = rows[identity]; scope, _, source = by_id[identity]
            _require(row['input_p']['value'] == source['value'] and row['input_p']['state'] == source['state'], 'family_input_cell_conflict')
            if plan['p_values']['kind'] == 'statistical_results':
                _require(_same(row['input_p'], source), 'family_input_cell_conflict')
            output.append({'family_ref': _ref('family', '@families' if fid is not None else aid, family['family_id']), 'test_ref': _ref('test', scope, identity),
                'input_p': self.value(scope, row['input_p'], population=identity), 'adjusted_p': self.value(scope, row['adjusted_p'], population=family['family_id']),
                'method': value['method'], 'alpha': value['alpha'], 'total_test_count': family['total_test_count'], 'rejected_at_alpha': row['rejected_at_alpha'], 'p_value_basis': family['p_value_basis'], 'requirement_refs': self.collected_refs(row, {'requirements': value['requirements']})})
        return output

    def qualifications(self, selection):
        aid = selection['analysis_id']; _require(aid in self.plans, 'analysis_unknown')
        sid, rid = selection['slot_id'], selection['request_id']; sources = []
        if sid is not None:
            _require((aid, sid) in self.slots, 'slot_unknown')
            if (aid, sid) in self.selections:
                row = self.selections[aid, sid]; sources.append({'diagnostics': row['diagnostics'], 'requirements': [self.req[i] for i in row['requirement_ids']]})
        if rid is not None:
            _require(rid in self.original[aid], 'original_request_unknown')
            row = self.outcomes.get(aid, {}).get(rid)
            if row is not None:
                sources.append(row)
            else:
                reqs = self.quarantine(aid, rid)
                sources.append({'requirements': reqs, 'diagnostics': [d for d in self.diagnostics if any(d['code'] == r['reason_code'] for r in reqs) and d['path'].startswith('/analyses/' + str(self.plan_indices[aid]) + '/')]})
        if sid is None and rid is None:
            sources += [self.analysis_reports[aid]] if aid in self.analysis_reports else []
            sources += [v for v in (self.sheets.get(aid), self.components.get(aid)) if v is not None]
            if not self.sheets:
                sources.append({'requirements': self.requirements, 'diagnostics': self.diagnostics})
        result = []
        for source in sources:
            for row in source['diagnostics']:
                requirements = [r for r in source['requirements'] if r['reason_code'] == row['code']]
                roles = _unique([r['role'] for r in requirements if r['role'] is not None])
                fact = {'code': row['code'] if row['code'] in DIAGNOSTIC_CODES else 'alignment_unregistered_qualification', 'phase': row['phase'], 'severity': row['severity'],
                    'role_ref': _ref('role', '@requirements', roles[0]) if len(roles) == 1 else None, 'requirement_refs': self.refs([r['requirement_id'] for r in requirements])}
                if fact not in result:
                    result.append(fact)
        return result

    def project(self):
        result = {}
        for field, schema in self.form['properties'].items():
            selection = validate_selection(schema['x-alignment-fact'], provider=self.provider)
            kind = selection['kind']
            symbols = selection.get('symbols', []) + [m['symbol'] for m in selection.get('measurements', []) if 'symbol' in m]
            if 'symbol' in selection.get('selector', {}):
                symbols.append(selection['selector']['symbol'])
            _require(all(len(s) == 1 and 33 <= ord(s) <= 126 for s in symbols), 'symbol_invalid')
            if kind == 'missing_requirements':
                fact = [self.requirement_fact(r) for r in self.requirements]
            elif kind == 'qualifications':
                fact = self.qualifications(selection)
            elif kind == 'native_measurement':
                fact = self.native(selection)
            elif kind == 'multiplicity':
                fact = self.multiplicity(selection)
            else:
                request, value = self.request(selection)
                self.scope(selection['analysis_id'], request, selection)
                fact = self.measurement(selection, request, value) if kind == 'measurement' else self.rows(selection, request, value)
            literal_fields = {'msa_sites': ('strict_majority_consensus',),
                'reference_differences': ('member_character', 'reference_character'),
                'group_counts': ('symbol',), 'xmfa_coordinates': ('aligned_symbol', 'forward_symbol')}.get(kind, ())
            if fact is not None:
                for row in fact if literal_fields else ():
                    _require(all(row[k] is None or type(row[k]) is str and len(row[k]) == 1 and 33 <= ord(row[k]) <= 126 for k in literal_fields), 'literal_symbol_invalid')
            _finite(fact)
            _require(Draft202012Validator(FACT_SCHEMAS[kind]).is_valid(fact), 'fact_shape_invalid')
            result[field] = fact
        return deepcopy(result)


@_closed
def project_requested_facts(*, sheet_set: dict | None, component_set: dict | None,
        missing_requirements: tuple[dict, ...], diagnostics: tuple[dict, ...],
        requested_form: dict, parameters: dict, provider: str) -> dict:
    """Copy exactly the finite original selections from supplied saved records."""
    return _Projection(sheet_set=sheet_set, component_set=component_set,
        missing_requirements=missing_requirements, diagnostics=diagnostics,
        requested_form=requested_form, parameters=parameters, provider=provider).project()


@_closed
def validate_projected_facts(facts: dict, *, sheet_set: dict | None,
        component_set: dict | None, missing_requirements: tuple[dict, ...],
        diagnostics: tuple[dict, ...], requested_form: dict, parameters: dict,
        provider: str) -> dict:
    """Validate exact saved values; no formula, parser or acquisition is run."""
    _finite(facts)
    expected = project_requested_facts(sheet_set=sheet_set, component_set=component_set,
        missing_requirements=missing_requirements, diagnostics=diagnostics,
        requested_form=requested_form, parameters=parameters, provider=provider)
    _require(_same(facts, expected), 'saved_facts_conflict')
    return deepcopy(facts)


__all__ = ['project_requested_facts', 'validate_projected_facts']
