"""Dispatch explicit MetaCATS requests to their separate pure calculators.

The dependency graph compiles only caller-declared requests. It is not a work
selector or workflow: no acquisition, resource choices, retries or native runs.
"""
from copy import deepcopy

from . import bvbrc_metacats_provider_contracts as c
from . import phylogeny_calculators as shared
from . import bvbrc_metacats_calculators as native
from . import bvbrc_metacats_biological_calculators as biological
from . import bvbrc_metacats_adequacy as adequacy
from .bvbrc_alignment_values import diagnostic


class _Missing(Exception):
    def __init__(self, reason):
        self.reason = reason


def _required(value, reason='alignment_document_unavailable'):
    if value is None:
        raise _Missing(reason)
    return value


def _dispatch(sheet, request, outcomes):
    kind = request['kind']; identity = sheet['analysis']['analysis_id']
    kwargs = {k: deepcopy(v) for k, v in request.items() if k not in ('kind', 'request_id')}
    extra = []
    if kind in c.COMMON_KINDS | c.COUNT_KINDS:
        if kind == 'ungapped_map':
            alignment = _required(c.lookup_alignment(sheet, request['alignment_id']))
            return list(shared.ungapped_coordinate_map(alignment, row_indices=tuple(request['row_indices']))), extra
        population_kind = 'composition' if kind == 'function_composition' else 'taxonomy' if kind == 'taxonomy' else 'alignments'
        population = _required(c.lookup_population(sheet, population_kind, request['population_id']), 'alignment_calculation_dependency_unavailable')
        kwargs.pop('population_id'); kwargs['population'] = population
        if kind in ('function_composition', 'taxonomy'):
            subjects = population['member_subjects']
            if kind == 'function_composition':
                return shared.function_composition(population=population,
                    assignments=tuple(a for a in sheet['associations']['functions'] if a['subject'] in subjects),
                    equivalences=tuple(sheet['associations']['function_equivalences'])), extra
            return shared.taxon_components(population=population, rank=request['rank'],
                assignments=tuple(a for a in sheet['associations']['taxonomy'] if a['subject'] in subjects)), extra
        alignment = _required(c.lookup_alignment(sheet, population['alignment_id']))
        if kind == 'alignment':
            kwargs['pairs'] = tuple(tuple(pair) for pair in kwargs['pairs'])
            return shared.alignment_components(alignment, **kwargs), extra
        if kind == 'original_coverage':
            members = _required(c.coverage_operands(sheet, population), 'original_member_occurrence_ambiguous')
            return shared.original_member_coverage(alignment, population=population, members=tuple(members),
                correspondences=tuple(r for r in sheet['associations']['correspondences'] if r['alignment_id'] == alignment['alignment_id'] and r['row_index'] in population['row_indices'])), extra
        category = request['category_id']
        _required(next((x for x in sheet['categories'] if x['category_id'] == category), None), 'metacats_biological_group_membership_required')
        kwargs['analysis_id'] = identity
        if kind == 'biological_group_counts':
            kwargs.pop('group_population_id')
            groups = _required(next((p for p in sheet['biological_group_populations'] if p['group_population_id'] == request['group_population_id']), None), 'metacats_biological_group_membership_required')
            kwargs['group_population'] = groups
            kwargs['assignments'] = tuple(a for a in sheet['biological_assignments'] if a['category_id'] == category and a['alignment_id'] == alignment['alignment_id'])
            return biological.biological_group_counts(alignment, **kwargs), extra
        groups = [g for g in sheet['native_group_columns'] if g['category_id'] == category]
        if not groups:
            raise _Missing('metacats_r_column_evidence_required')
        if not c.native_input_provenance(sheet, population):
            raise _Missing('metacats_original_hash_provenance_required')
        kwargs['group_order'] = tuple(groups)
        kwargs['assignments'] = tuple(a for a in sheet['native_group_assignments'] if a['category_id'] == category and a['alignment_id'] == alignment['alignment_id'])
        return native.metacats_group_counts(alignment, **kwargs), extra
    if kind in c.STAT_KINDS | c.EFFECT_KINDS:
        counts = outcomes[kwargs.pop('counts_request_id')]['value']
        kwargs['selected_pairs'] = tuple(tuple(pair) for pair in kwargs['selected_pairs'])
        function = {'native_statistics': native.metacats_statistics,
            'native_effects': native.metacats_effects,
            'biological_statistics': biological.biological_group_statistics,
            'biological_effects': biological.biological_group_effects}[kind]
        return function(counts, **kwargs), extra
    if kind == 'expected_adequacy':
        statistics = outcomes[kwargs.pop('statistics_request_id')]['value']
        return adequacy.expected_count_adequacy(statistics, **kwargs), extra
    family, p_values, extra = c.compile_family(sheet, request, outcomes)
    if family is None:
        raise _Missing(extra[0]['reason_code'])
    return native.adjust_p_values(tuple(p_values), family=family, method=request['method'],
        alpha=request['alpha'], dependence_assumption=request['dependence_assumption']), extra


def calculate_metacats(sheet: dict, parameters: dict) -> dict:
    """Return complete separate outcomes in original request order."""
    sheet = c.validate_metacats_sheet(sheet)
    parameters = c.validate_metacats_parameters(parameters)
    pending = list(parameters['requests']); outcomes = {}; analysis_id = sheet['analysis']['analysis_id']
    while pending:
        ready = next(request for request in pending if all(d in outcomes for d in c.dependencies(request)))
        pending.remove(ready)
        outcome = {'request_id': ready['request_id'], 'kind': ready['kind'], 'status': 'ok',
            'value': None, 'requirements': [], 'diagnostics': []}
        try:
            if any(outcomes[d]['value'] is None or outcomes[d]['status'] == 'invalid' for d in c.dependencies(ready)):
                raise _Missing('alignment_calculation_dependency_unavailable')
            value, extra = _dispatch(sheet, ready, outcomes)
            outcome['value'] = value
            if ready['kind'] in c.COMMON_KINDS:
                if type(value) is dict:
                    outcome['requirements'] = shared.calculation_requirements(value)
                    outcome['diagnostics'] = deepcopy(value.get('diagnostics', []))
                outcome['status'] = 'partial' if outcome['requirements'] else 'ok'
            else:
                outcome['requirements'] = c.merge_reports(value['requirements'], extra)
                outcome['diagnostics'] = deepcopy(value['diagnostics'])
                outcome['status'] = 'partial' if extra and value['status'] == 'ok' else value['status']
        except _Missing as exc:
            outcome.update(status='partial', value=None, requirements=[c.need(analysis_id, ready['request_id'], exc.reason)])
        except ValueError:
            outcome.update(status='invalid', value=None,
                requirements=[c.need(analysis_id, ready['request_id'], 'alignment_calculation_invalid')],
                diagnostics=[diagnostic('alignment_calculation_invalid', path='/requests/' + str(parameters['requests'].index(ready)), severity='error')])
        outcomes[ready['request_id']] = outcome
    ordered = [outcomes[r['request_id']] for r in parameters['requests']]
    result = {'schema_version': c.VERSION, 'analysis_id': analysis_id, 'parameters': parameters, 'results': ordered,
        'requirements': c.merge_reports(*(o['requirements'] for o in ordered)),
        'diagnostics': c.merge_reports(*(o['diagnostics'] for o in ordered))}
    return c.validate_metacats_components(result, sheet=sheet)


__all__ = ['calculate_metacats']
