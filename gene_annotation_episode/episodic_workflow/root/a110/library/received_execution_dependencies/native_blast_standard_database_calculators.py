from __future__ import annotations
import math
import re
from gene_annotation_episode.episodic_workflow.root.a110.blast_pairwise_grader import validate_blast_correspondence_instance
from gene_annotation_episode.episodic_workflow.root.a110.alignment_correspondence import validate_correspondence_artifacts, _same
import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_standard_database_result_views as views
CALCULATION_SCHEMA = views.PREFIX + 'calculations_v2'
_CALC_FIELDS = {'schema', 'sequence_model', 'sequence', 'pssm', 'search_facts', 'native_search_statistics', 'native_hsp_components', 'qualified_hsp_components', 'issues'}

def _at(value, pointer):
    if type(pointer) is not str or (pointer and (not pointer.startswith('/'))) or re.search('~(?![01])', pointer):
        raise ValueError(views.PREFIX + 'pointer_invalid')
    for token in pointer.split('/')[1:] if pointer else ():
        token = token.replace('~1', '/').replace('~0', '~')
        if type(value) is list:
            if not re.fullmatch('0|[1-9][0-9]*', token):
                raise ValueError(views.PREFIX + 'pointer_invalid')
            value = value[int(token)]
        else:
            value = value[token]
    return value

def _number(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))

def validate_sequence_model(model):
    model = views._copy(model)
    if model is None:
        return None
    if type(model) is not dict or set(model) - {'temperature_bits', 'function_priors'}:
        raise ValueError(views.PREFIX + 'sequence_model_invalid')
    if 'temperature_bits' in model and (not _number(model['temperature_bits']) or model['temperature_bits'] <= 0):
        raise ValueError(views.PREFIX + 'sequence_model_invalid')
    priors = model.get('function_priors')
    if priors is not None and (type(priors) is not dict or not priors or any((type(k) is not str or not k.strip() or '\x00' in k or (not _number(v)) or (v < 0) for k, v in priors.items())) or (not any((v > 0 for v in priors.values())))):
        raise ValueError(views.PREFIX + 'sequence_model_invalid')
    if priors is not None:
        try:
            total = math.fsum(priors.values())
        except OverflowError as error:
            raise ValueError(views.PREFIX + 'sequence_model_invalid') from error
        if not math.isfinite(total):
            raise ValueError(views.PREFIX + 'sequence_model_invalid')
    return model

def validate_standard_blast_correspondence(calculations, *, admission=False):
    """Compare the required v2 common companion to its unchanged legacy cells."""
    if set(calculations) != _CALC_FIELDS | {'correspondence'} or calculations['schema'] != CALCULATION_SCHEMA:
        raise ValueError(views.PREFIX + 'correspondence_calculations_invalid')
    companion = validate_correspondence_artifacts(calculations['correspondence'], admission=admission)
    expected = {(f'/native_hsp_components/{i}/component', 'reported') for i in range(len(calculations['native_hsp_components']))}
    for si, entry in enumerate(calculations['sequence']):
        result = entry['components']
        database = result['components']['database_sheet'] if result is not None else None
        if database is not None:
            expected.update(((f'/sequence/{si}/components/components/database_sheet/hits/{hi}', 'qualified') for hi in range(len(database['hits']))))
    if {(item['legacy_pointer'], item['axis_basis']) for item in companion['instances']} != expected:
        raise ValueError(views.PREFIX + 'correspondence_population_conflict')
    for instance in companion['instances']:
        legacy = _at(calculations, instance['legacy_pointer'])
        database = _at(calculations, instance['legacy_pointer'].rsplit('/hits/', 1)[0]) if instance['axis_basis'] == 'qualified' else None
        program = database['normalized_result']['search']['program'] if database is not None else None
        validate_blast_correspondence_instance(legacy, instance, program=program)
        if instance['axis_basis'] == 'qualified':
            sequence_pointer = instance['legacy_pointer'].split('/components/components/database_sheet/')[0]
            result = _at(calculations, sequence_pointer + '/components/components')
            rowkey = next((row['row_key'] for row in result['row_keys']['hits'] if row['row_key']['hit_ordinal'] == legacy['hit_index']))
            selected = next((row for row in result['selected_query_coverage'] if row['row_key'] == rowkey))
            common = instance['components']['selected']['query']
            expected_selected = {'numerator': common['observed_numerator'], 'denominator': common['denominator'], 'value': common['complete_value'], 'complete_for_reported_hsps': common['complete_for_original_rows']}
            if not _same(expected_selected, {key: selected[key] for key in expected_selected}):
                raise ValueError(views.PREFIX + 'correspondence_selection_conflict')
