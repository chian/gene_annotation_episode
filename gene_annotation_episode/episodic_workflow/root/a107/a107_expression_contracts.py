"""A107 declared expression source formats, separate from chemical accounting."""
from .component_axis_native_contracts import obj, text, nullable, array, identities


VERSION = 'a107_expression_components_v2'


def source_schema(version=None):
    if version is None:
        return {'oneOf': [source_schema(1), source_schema(2)]}
    feature = obj({'id': text(), 'entity_id': nullable(text()),
        'molecule': {'enum': ['rna', 'protein', 'reporter', 'other', 'unknown']},
        'sequence_sha256': nullable({'type': 'string', 'pattern': '^[a-f0-9]{64}$'}),
        'source_locator': text()})
    sample = obj({'id': text(), 'biological_unit_id': nullable(text()),
        'condition_key': text(), 'organism_id': nullable(text()), 'source_locator': text()})
    if version == 2:
        sample['properties']['genome_accession'] = nullable(text())
        sample['required'].append('genome_accession')
    measurement = obj({'feature_id': text(), 'sample_id': text(),
        'measurement_id': nullable(text()), 'value': nullable({'type': 'number'}),
        'missing_reason': nullable(text()), 'source_locator': text()})
    if version == 2:
        measurement['properties']['reported_bound'] = nullable(obj({
            'operator': {'enum': ['less_than', 'less_or_equal', 'greater_than', 'greater_or_equal']},
            'value': {'type': 'number'}, 'source_locator': text()}))
        measurement['required'].append('reported_bound')
    result = obj({'version': {'const': 'a107_expression_table_v'+str(version)},
        'dataset_id': nullable(text()), 'origin': {'enum': ['reported', 'retained_extraction', 'synthetic']},
        'quantity': obj({'unit': text(), 'scale': text(), 'normalization': text(),
            'nonnegative': {'type': 'boolean'}, 'source_locator': text()}),
        'features': array(feature, minimum=1 if version == 2 else 2),
        'samples': array(sample, minimum=1), 'measurements': array(measurement)})
    if version == 2:
        criterion = obj({'id': text(), 'feature_id': text(), 'sample_id': text(),
            'kind': {'enum': ['limit_of_detection', 'limit_of_quantification', 'background_cutoff']},
            'operator': {'enum': ['greater_than', 'greater_or_equal']},
            'value': nullable({'type': 'number'}), 'unit': text(), 'scale': text(), 'normalization': text(),
            'calibration_condition_key': nullable(text()), 'control_source_locator': nullable(text()),
            'source_locator': text()})
        result['properties']['detection_criteria'] = array(criterion)
        result['required'].append('detection_criteria')
    return result


def selection_schema():
    return obj({'left_feature_id': text(), 'right_feature_id': nullable(text()),
        'condition_key': text(), 'sample_ids': identities()})
