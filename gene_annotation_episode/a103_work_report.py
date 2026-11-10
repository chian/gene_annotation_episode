"""Present actual A103 results beside their original action's recorded credit.

This pure adapter receives only an action's own result and already authorized
receiver projections. It opens no sources, revisits no child history, performs
no calculation and supplies no functional verdict or new progress measure.
"""
from collections.abc import Mapping
from copy import deepcopy
import json


_NATIVE_RESULTS = {
    'a103_locus_binding_v1': 'Recorded genomic locus and source-to-material placement',
    'a103_neighborhood_v1': 'Measured genomic neighborhood',
    'a103_recurrence_v1': 'Measured recurrence of the declared gene arrangement',
    'a103_fusion_v1': 'Measured linkage of the selected coding-product regions',
    'a103_cooccurrence_v1': 'Measured component co-occurrence in the declared genome panel',
    'a103_channel_v1': 'Received native STRING context channel',
    'a103_detection_v1': 'Detection inventory from the completed received search',
    'a103_contrast_v1': 'Saved contrast between the selected qualified context results',
}
_OPERATIONS = frozenset({'context.bind_locus', 'context.compare_neighborhoods',
    'context.fusion', 'context.cooccurrence', 'context.contrast',
    'context.association_channels', 'context.detection_inventory', 'context.request_hpc'})
_QUANTITIES = {
    'supporting_loci': ('Loci satisfying the declared arrangement', 'loci'),
    'evaluable_loci': ('Loci with an evaluated arrangement', 'loci'),
    'unknown_loci': ('Loci with unresolved arrangement', 'loci'),
    'evaluable_genomes': ('Evaluated genomes', 'genomes'),
    'unknown_genomes': ('Genomes with unresolved detection', 'genomes'),
    'sampling_group_count': ('Recorded sampling groups', 'groups'),
    'native_fraction': ('Native arrangement recurrence', 'fraction'),
    'group_balanced_fraction': ('Sampling-group-balanced arrangement recurrence', 'fraction'),
    'observed_link_fraction': ('Observed coding-product linkage', 'fraction'),
    'risk_difference': ('Native co-occurrence risk difference', 'difference of fractions'),
    'p_value': ('Native one-sided enrichment p-value', 'dimensionless'),
    'log10_significance': ('Native negative log10 enrichment p-value', 'dimensionless'),
    'native_significance_index': ('Native co-occurrence significance index', 'dimensionless'),
    'searched_cds': ('Coding sequences included in the detection inventory', 'CDS'),
    'uncertain_cds': ('Coding sequences with unresolved search coverage', 'CDS'),
    'supporting_context': ('Saved supporting-context index', 'dimensionless'),
    'opposing_context': ('Saved opposing-context index', 'dimensionless'),
    'contrast': ('Saved context contrast', 'dimensionless'),
}
_COMMON = ('source_ref', 'grading_artifact_ref', 'target_ref', 'target_regions',
    'material_ref', 'producer_operation', 'accession', 'organism', 'schema',
    'binding_ref', 'neighborhood_ref', 'recurrence_ref', 'fusion_ref',
    'cooccurrence_ref', 'contrast_ref', 'detection_ref', 'measurement_ref', 'file_source_ref',
    'sequence_source_ref', 'protein_reference_ref', 'coordinate_system')
_DETAILS = {
    'a103_locus_binding_v1': ('source_format', 'record_length', 'topology', 'selector',
        'selection_status', 'source_annotations', 'native_input_placement', 'supplied_target_genome'),
    'a103_neighborhood_v1': ('window', 'coordinate_mapping', 'gene_order_reference_axis',
        'regulatory_features', 'source_labels_are'),
    'a103_recurrence_v1': ('definition', 'rows', 'sampling_groups', 'sampling_aggregation'),
    'a103_fusion_v1': ('regions', 'same_coding_product'),
    'a103_cooccurrence_v1': ('contingency', 'rows', 'independent_row_test_eligible',
        'null_model', 'multiple_comparison_adjustment', 'normalization', 'detection_scope',
        'left_reference_ref', 'right_reference_ref', 'detection_refs'),
    'a103_channel_v1': ('channel', 'native_field', 'native_taxon_id',
        'actual_measured_subjects', 'left_reference_ref', 'right_actual_ref',
        'right_reference_ref', 'native_request_url'),
    'a103_detection_v1': ('component_ref', 'genome_key', 'present', 'scope', 'absence_meaning',
        'all_actual_cds_in_search', 'native_hits', 'native_method', 'native_parameters',
        'native_program_version', 'native_search_complete', 'record_scopes', 'snapshot_ref',
        'native_source_ref', 'database_source_ref'),
    'a103_contrast_v1': ('function_ref', 'supporting_source_refs', 'opposing_source_refs',
        'incompatibility_witness_refs'),
}


def _nodes(value):
    if isinstance(value, Mapping):
        yield value
        body = value.get('body')
        schema = value.get('schema')
        if isinstance(schema, str) and (schema in _NATIVE_RESULTS or schema == 'a103_tool_attachment_v1'):
            return
        if (isinstance(body, Mapping) and isinstance(body.get('schema'), str)
                and body['schema'] in _NATIVE_RESULTS):
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


def _locus(value):
    if not isinstance(value, Mapping):
        return deepcopy(value)
    result = {name: deepcopy(value[name]) for name in ('source_feature_index',
        'source_feature_key', 'location', 'segments', 'strand', 'locus_tags',
        'protein_ids', 'qualifiers', 'protein_reference_ref', 'focal',
        'exact_boundaries', 'translation_status') if name in value}
    translation = value.get('translation')
    if isinstance(translation, Mapping):
        result['translation'] = {name: deepcopy(translation[name]) for name in
            ('status', 'qualification', 'genetic_code', 'codon_start',
             'exact_boundaries', 'translation_exception') if name in translation}
    return result


def _native(row):
    wrapped = row.get('body')
    body = wrapped if isinstance(wrapped, Mapping) else row
    schema = body.get('schema')
    # The neighborhood tool returns its measured coordinates and features
    # directly, while its publication retains the schema-bearing native body.
    if not isinstance(schema, str) or schema not in _NATIVE_RESULTS:
        if 'neighborhood_ref' in body and 'cds' in body and 'coordinate_mapping' in body:
            schema = 'a103_neighborhood_v1'
        else:
            return None
    result = {'result': _NATIVE_RESULTS[schema],
        **{name: deepcopy(body[name]) for name in (*_COMMON, *_DETAILS[schema]) if name in body}}
    if isinstance(wrapped, Mapping):
        result.update({name: deepcopy(row[name]) for name in
            ('source_ref', 'grading_artifact_ref') if name in row})
    quantities = [{'name': meaning, 'value': deepcopy(body[name]), 'unit': unit}
        for name, (meaning, unit) in _QUANTITIES.items() if name in body]
    if schema == 'a103_channel_v1' and 'native_value' in body:
        quantities.append({'name': 'Native ' + body['channel'] + ' channel value',
            'value': body['native_value'], 'unit': body['native_unit']})
    if quantities:
        result['quantities'] = quantities
    for name in ('locus', 'coding_locus'):
        if name in body:
            result[name] = _locus(body[name])
    for name in ('selected_loci', 'cds'):
        if name in body:
            result[name] = [_locus(value) for value in body[name]]
    raw = body.get('raw_neighborhood')
    if isinstance(raw, Mapping):
        result.update({name: deepcopy(raw[name]) for name in
            ('window', 'coordinate_mapping') if name in raw})
    return result


def _attachment(row):
    if row.get('schema') != 'a103_tool_attachment_v1':
        return None
    return {'result': 'Saved measurement-specific context attribution',
        **{name: deepcopy(row[name]) for name in ('source_ref', 'grading_artifact_ref',
            'measurement_ref', 'target_ref', 'target_regions', 'policy', 'state',
            'score', 'raw_value', 'bounds', 'missing', 'rows', 'regions',
            'target_link', 'qualified_panel', 'dependency_group', 'variant') if name in row},
        'score_meaning': 'Saved attributed context index; original action earned credit is reported separately'}


def completed_work_result(selection, outcome, received_records):
    """Select only original own/delivered A103 result versions, without I/O."""
    if not isinstance(selection, Mapping) or not isinstance(outcome, Mapping):
        return None
    direct = {key: value for key, value in outcome.items() if key != 'received_axis_results'}
    original_refs = set(_references(direct))
    related = selection.get('tool') in _OPERATIONS or any(
        row.get('option_id') == 'A103' or row.get('id') == 'A103' and row.get('slot') == 'evidence_axis'
        for row in _nodes(selection))
    results, limitations, seen = [], [], set()

    def append(row, *, received=False):
        nonlocal related
        result = _native(row) or _attachment(row)
        if result is None:
            return
        # A later attribution for the same measurement is not the original
        # action's result. Match its own immutable publication, not its input.
        publication = next((result[name] for name in ('source_ref', 'neighborhood_ref',
            'recurrence_ref', 'fusion_ref', 'cooccurrence_ref', 'contrast_ref',
            'detection_ref', 'binding_ref') if result.get(name)), None)
        publications = [publication] if publication else []
        if received and not original_refs.intersection(publications):
            return
        identity = ((result['result'], tuple(sorted(set(publications)))) if publications
            else json.dumps(result, sort_keys=True, separators=(',', ':')))
        if identity in seen:
            return
        seen.add(identity)
        related = True
        results.append(result)
        if result.get('missing'):
            limitations.append({'source_ref': result.get('source_ref'),
                'measurement_ref': result.get('measurement_ref'),
                'missing': deepcopy(result['missing'])})

    for row in _nodes(direct):
        append(row)
        if 'channels' in row and isinstance(row['channels'], (tuple, list)):
            for channel in row['channels']:
                if not isinstance(channel, Mapping) or not {'measurement_ref', 'native_field', 'raw_value'} <= channel.keys():
                    continue
                related = True
                results.append({'result': 'Received native STRING context channel',
                    **deepcopy(channel), 'unit': 'STRING_channel_0_to_1'})
        if selection.get('tool') == 'context.request_hpc' and 'new_execution_requested' in row:
            results.append({'result': 'Recorded A103 execution request or reuse',
                **{name: deepcopy(row[name]) for name in ('request_ref', 'commission_source_ref',
                    'execution_status', 'new_execution_requested', 'execution_owner') if name in row}})
    for row in _nodes(outcome.get('received_axis_results', ())):
        append(row, received=True)
    if not related:
        return None
    admitted = outcome.get('admitted_child_return')
    if isinstance(admitted, Mapping) and 'context_credit' in admitted:
        results.append({'result': 'Delivered child-local context credit',
            'value': admitted['context_credit'],
            'meaning': 'Child task units; receiving-parent earned credit is reported separately'})
    if not results:
        limitations.append({'reason': 'No concrete A103 measurement or attributed sheet was included in this action or its admitted resolved results'})
    return {'axis': 'A103', 'results': results, 'limitations': limitations}
