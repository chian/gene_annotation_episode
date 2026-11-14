"""Present saved A104 results beside the original action's recorded credit.

The common work report supplies original action identity and iterator credit.
This pure adapter selects already returned native measurements and exact
receiver-authorized attribution publications. It opens no source, reconstructs
no tree, computes no support value and supplies no evolutionary verdict.
"""
from collections.abc import Mapping
from copy import deepcopy
import json


_NATIVE_RESULTS = {
    'a104_placement_v1': 'Measured target placement in the selected native tree',
    'a104_history_comparison_v1': 'Measured family-tree and organismal-tree comparison',
    'a104_clade_composition_v1': 'Measured reference membership of the selected native clade',
    'a104_robustness_v1': 'Measured placement stability across the declared native analyses',
}
_MEASUREMENT_OPERATIONS = frozenset({'phylogeny.measure_placement',
    'phylogeny.compare_histories', 'phylogeny.clade_functions',
    'phylogeny.compare_placements'})
_COMMON = ('schema', 'version', 'producer_operation', 'source_ref',
    'measurement_ref', 'grading_artifact_ref', 'target_ref', 'target_regions',
    'native_phylogeny_ref', 'native_request_ref', 'hpc_result_ref', 'pbs_job_id',
    'variant_group', 'variant')
_DETAILS = {
    'a104_placement_v1': ('analysis', 'target_tip', 'split_index',
        'target_side_tip_ids', 'native_split', 'clade_members',
        'reference_panel_members', 'support_method', 'support_scale',
        'bootstrap_population', 'population', 'native_correspondence',
        'reference_correspondences', 'rooting_status'),
    'a104_history_comparison_v1': ('family_analysis', 'organismal_analysis',
        'selected_tip_ids', 'taxon_join', 'organismal_basis', 'comparison',
        'native_relationship_reliability', 'limitations'),
    'a104_clade_composition_v1': ('native_placement_ref', 'clade_members',
        'reference_correspondences', 'required_reference_parts',
        'characterization_subject_refs'),
    'a104_robustness_v1': ('placement_refs', 'analysis_identities',
        'common_reference_members', 'union_reference_members',
        'native_support_values', 'compared_variant_group', 'compared_variants'),
}


def _nodes(value):
    if isinstance(value, Mapping):
        yield value
        body = value.get('body')
        schema = value.get('schema')
        native_schema = isinstance(schema, str) and (
            schema in _NATIVE_RESULTS or schema == 'a104_per_use_attribution_v1')
        wrapped_schema = body.get('schema') if isinstance(body, Mapping) else None
        if native_schema or isinstance(wrapped_schema, str) and (
                wrapped_schema in _NATIVE_RESULTS or wrapped_schema == 'a104_per_use_attribution_v1'):
            return
        for child in value.values():
            yield from _nodes(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from _nodes(child)


def _references(value):
    if isinstance(value, Mapping):
        for child in value.values():
            yield from _references(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from _references(child)
    elif isinstance(value, str) and value.startswith('source_'):
        yield value


def _native(row):
    wrapped = row.get('body')
    body = wrapped if isinstance(wrapped, Mapping) else row
    schema = body.get('schema')
    if not isinstance(schema, str) or schema not in _NATIVE_RESULTS:
        return None
    result = {'result': _NATIVE_RESULTS[schema],
        **{name: deepcopy(body[name]) for name in (*_COMMON, *_DETAILS[schema]) if name in body}}
    if isinstance(wrapped, Mapping):
        result.update({name: deepcopy(row[name]) for name in
            ('source_ref', 'grading_artifact_ref') if name in row})
    quantities = []
    if 'raw_value' in body:
        quantities.append({'name': 'Saved native phylogenetic index',
            'value': body['raw_value'], 'unit': 'dimensionless'})
    if schema == 'a104_placement_v1':
        bootstrap = body.get('bootstrap_population', {})
        for name, meaning in (('matches', 'Bootstrap replicates containing the selected split'),
                ('denominator', 'Bootstrap replicates evaluated for the selected split')):
            if name in bootstrap:
                quantities.append({'name': meaning, 'value': bootstrap[name], 'unit': 'replicates'})
    elif schema == 'a104_history_comparison_v1':
        comparison = body.get('comparison', {})
        for name, meaning in (('rf', 'Unrooted Robinson–Foulds distance'),
                ('gene_splits', 'Retained family-tree splits'),
                ('organismal_splits', 'Retained organismal-tree splits'),
                ('shared_splits', 'Shared retained splits')):
            value = comparison.get(name)
            if isinstance(value, Mapping) and 'value' in value:
                quantities.append({'name': meaning, 'value': deepcopy(value['value']), 'unit': 'splits'})
    elif schema == 'a104_robustness_v1':
        for name, meaning, unit in (
                ('stability_numerator', 'Reference members shared by the selected placements', 'members'),
                ('stability_denominator', 'Reference members in the union of selected placements', 'members'),
                ('stability_fraction', 'Saved placement-membership stability', 'fraction')):
            if name in body:
                quantities.append({'name': meaning, 'value': body[name], 'unit': unit})
    if quantities:
        result['quantities'] = quantities
    result['value_meaning'] = 'Saved native test quantities; original action earned credit is reported separately'
    return result


def _attachment(row):
    wrapped = row.get('body')
    body = wrapped if isinstance(wrapped, Mapping) else row
    if body.get('schema') != 'a104_per_use_attribution_v1':
        return None
    result = {'result': 'Saved attribution for this particular phylogenetic measurement',
        **{name: deepcopy(body[name]) for name in ('schema', 'version', 'source_ref',
            'measurement_ref', 'grading_artifact_ref', 'target_ref', 'target_regions',
            'policy', 'state', 'score', 'raw_value', 'bounds', 'missing',
            'native_phylogeny_ref', 'hpc_result_ref', 'request_ref',
            'variant_group', 'variant', 'compared_variant_group',
            'compared_variants', 'qualification_dependencies') if name in body},
        'value_meaning': 'Saved attributed phylogenetic index; not the parent action earned credit'}
    if isinstance(wrapped, Mapping):
        result.update({name: deepcopy(row[name]) for name in
            ('source_ref', 'grading_artifact_ref') if name in row})
    sheets = body.get('sheets', {})
    result['qualification_facts'] = {name: deepcopy(sheets[name]) for name in
        ('target_identity', 'execution', 'native_test', 'reference_characterization') if name in sheets}
    return result


def completed_work_result(selection, outcome, received_records):
    """Select original A104 publications; retain partial and missing facts.

    A later attribution of the same measurement cannot qualify an older action.
    Receiver views must match their own immutable output publication reference,
    never merely their input measurement or a shared target/phylogeny.
    """
    if not isinstance(selection, Mapping) or not isinstance(outcome, Mapping):
        return None
    direct = {key: value for key, value in outcome.items() if key != 'received_axis_results'}
    original_refs = set(_references(direct))
    operation = str(selection.get('tool', ''))
    related = operation.startswith('phylogeny.') or any(
        node.get('option_id') == 'A104' or node.get('id') == 'A104' and node.get('slot') == 'evidence_axis'
        for node in _nodes(selection))
    results, limitations, seen = [], [], set()

    def append(row, *, received=False):
        nonlocal related
        result = _native(row) or _attachment(row)
        if result is None:
            return
        # Native direct results use measurement_ref as their own publication;
        # attribution measurement_ref is an input, not its output identity.
        publication = result.get('source_ref')
        if publication is None and result.get('schema') in _NATIVE_RESULTS:
            publication = result.get('measurement_ref')
        if received and (publication is None or publication not in original_refs):
            return
        identity = ((result['schema'], publication) if publication
            else json.dumps(result, sort_keys=True, separators=(',', ':')))
        if identity in seen:
            return
        seen.add(identity)
        related = True
        results.append(result)
        for name in ('missing', 'limitations'):
            if result.get(name):
                limitations.append({'source_ref': publication, name: deepcopy(result[name])})

    for row in _nodes(direct):
        append(row)
    for row in _nodes(outcome.get('received_axis_results', ())):
        append(row, received=True)
    if operation.startswith('phylogeny.'):
        body = outcome.get('result')
        if isinstance(body, Mapping) and not body.get('schema'):
            fields = ('request_ref', 'analysis_need_ref', 'commission_source_ref',
                'native_ref', 'native_phylogeny_refs', 'execution_status',
                'scientific_status', 'new_execution_requested', 'execution_owner',
                'next_owner', 'pbs_job_id', 'admission_status', 'partial_execution',
                'missing_analysis_names', 'corresponding_relationships', 'analyses')
            facts = {name: deepcopy(body[name]) for name in fields if name in body}
            if facts:
                results.append({'result': 'Recorded phylogenetic execution or native inspection outcome', **facts})
    if not related:
        return None
    admitted = outcome.get('admitted_child_return')
    if isinstance(admitted, Mapping) and 'phylogenetic_credit' in admitted:
        results.append({'result': 'Delivered child-local phylogenetic credit',
            'value': admitted['phylogenetic_credit'],
            'meaning': 'Child task units; receiving-parent earned credit is reported separately'})
    if not results and operation in _MEASUREMENT_OPERATIONS and outcome.get('status') in {'completed', 'partial'}:
        limitations.append({'reason': 'This action did not return a native A104 measurement or an originally delivered resolved attribution'})
    return {'axis': 'A104', 'results': results, 'limitations': limitations}
