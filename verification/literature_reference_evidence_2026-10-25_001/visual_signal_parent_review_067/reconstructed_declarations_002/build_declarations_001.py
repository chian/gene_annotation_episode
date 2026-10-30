"""Design declarations only; no application import or reader implementation."""
from copy import deepcopy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def obj(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def arr(item, **extra):
    return {'type': 'array', 'items': item, **extra}


def choice(*values):
    return {'type': 'string', 'enum': list(values)}


def nullable(value):
    return {'anyOf': [value, {'type': 'null'}]}


TEXT = {'type': 'string', 'minLength': 1}
REF = {'type': 'string', 'format': 'reference'}
NUMBER = {'type': ['number', 'null']}
BOOL = {'type': 'boolean'}
INDEX = {'type': 'integer', 'minimum': 0}
BOX = {'type': 'array', 'minItems': 4, 'maxItems': 4, 'items': INDEX}
READING = ('exact', 'ambiguous', 'unreadable', 'conflicting')
COMPONENTS = ('reported_ratio', 'difference_from_reference', 'log_reported_ratio',
              'calibrated_amount_ratio', 'amount_adjusted_effect', 'source_profile_log_ratio', 'source_signed_index')
REASONS = ('no_selected_representations', 'source_dependency_unavailable', 'unreadable_transcription',
    'ambiguous_transcription', 'source_representation_conflict', 'incomplete_conflicting_representations',
    'comparison_association_unresolved', 'signal_scale_unresolved', 'unsupported_expression',
    'negative_reported_signal_unsupported', 'reported_limit_not_point', 'positive_denominator_not_established',
    'zero_reported_ratio', 'numerical_model_range', 'jats_expression_capability_partial',
    'calibrated_amount_conversion_unimplemented', 'functional_response_conversion_unimplemented',
    'observation_model_unimplemented')
TW = obj({'kind': {'const': 'text'}, 'source_ref': REF, 'representation': choice('original', 'text'),
          'start': INDEX, 'end': {'type': 'integer', 'minimum': 1}, 'quote': TEXT})
IW = obj({'kind': {'const': 'image'}, 'view_ref': REF, 'region': BOX, 'quote': TEXT})
WITNESS = {'oneOf': [TW, IW]}
FRAGMENT = obj({'view_ref': REF, 'region': BOX, 'raw_fragment': {'type': ['string', 'null']}})


def meaning(values=None):
    value = {'type': ['string', 'null']}
    if values:
        value['enum'] = [*values, None]
    return obj({'status': choice('known', 'unknown', 'conflicting'), 'value': value,
                'witnesses': arr(WITNESS)})


RELATION = obj({'value': choice('supported', 'unknown', 'conflicting'), 'witnesses': arr(WITNESS)})
COMPARISON_FIELDS = ('subject', 'variant', 'reference', 'organism', 'genotype', 'construct_variant',
    'construct_reference', 'preparation_variant', 'preparation_reference', 'experiment', 'condition',
    'endpoint', 'normalization')
comparison = {name: meaning() for name in COMPARISON_FIELDS}
comparison.update(signal_kind=meaning(('protein_band', 'transcript_signal', 'other_reported_signal')),
    reference_role=meaning(('tagged_wt_complementation', 'endogenous_wt', 'other_reported_reference')),
    arrangement=meaning(('single_preparation', 'replacement', 'coexistence', 'not_applicable')),
    signal_use=meaning(('experimental_comparability', 'measured_endpoint', 'other')))
pair = obj({'numerator': IW, 'denominator': nullable(IW)})
visual_selection = obj({'reading_state': choice(*READING), 'candidates': arr(pair), 'fragments': arr(FRAGMENT),
                        'signal_scale': RELATION})
jats_selection = obj({'source_ref': REF, 'section_id': TEXT, 'paragraph_index': INDEX,
    'expected_subject': TEXT, 'variant': TEXT, 'reference_literal': TEXT})


def representation(kind, selection):
    return obj({'representation_id': TEXT, 'kind': {'const': kind}, 'selection': selection,
        'comparison_relation': RELATION, 'physical_measurement': meaning(), 'reference_measurement': meaning()})


REQUEST = obj({'version': {'const': 'relative_signal_source_selection_v2'}, 'source_ref': REF,
    'comparison': obj(comparison), 'representations': arr({'oneOf': [representation('jats_percent', jats_selection),
        *[representation(kind, visual_selection) for kind in ('visual_ratio', 'visual_percent', 'visual_signal_pair')]]})})
RATIONAL = obj({'numerator': {'type': 'string', 'pattern': '^-?[0-9]+$'},
                'denominator': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}})
DOMAIN = obj({'lower': NUMBER, 'lower_infinite': BOOL, 'lower_closed': BOOL,
              'upper': NUMBER, 'upper_infinite': BOOL, 'upper_closed': BOOL,
              'meaning': {'const': 'reported_estimate_domain'}})
JATS_LOCATOR = obj({'kind': {'const': 'jats'}, 'source_ref': REF, 'artifact_ref': REF,
    'section_id': TEXT, 'paragraph_index': INDEX, 'paragraph_text': TEXT, 'expression': TEXT,
    'expression_start': INDEX, 'expression_end': {'type': 'integer', 'minimum': 1}})
IMAGE_LOCATOR = obj({'kind': {'const': 'image'}, 'view_ref': REF, 'source_ref': REF, 'artifact_ref': REF,
    'original_source_ref': REF, 'original_artifact_ref': REF, 'frame': INDEX, 'region': BOX, 'quote': TEXT})
LOCATOR = {'oneOf': [JATS_LOCATOR, IMAGE_LOCATOR]}
DIAGNOSTIC = obj({'code': choice(*REASONS), 'field': TEXT, 'source_refs': arr(REF, uniqueItems=True)})
AUTH_WITNESS = obj({'selection': WITNESS, 'locator': nullable(LOCATOR),
    'authentication': choice('exact_utf8_span', 'native_view_bytes_and_geometry', 'unavailable'),
    'attribution': choice('literal_source_record', 'investigating_episode_interpretation'),
    'diagnostics': arr(DIAGNOSTIC)})


def extracted_meaning(selected):
    fields = deepcopy(selected['properties'])
    fields['witnesses'] = arr(AUTH_WITNESS)
    fields['interpretation_kind'] = {'const': 'episode_source_interpretation'}
    return obj(fields)


view_fields = {'id': REF, 'record_type': {'const': 'image_view'}, 'origin': {'const': 'tool'},
    'representation': {'const': 'selected_native_image_frame_v1'}, 'source_ref': REF, 'input_source_ref': REF,
    'original_artifact_ref': REF, 'image_artifact_ref': REF, 'native_format': TEXT, 'native_initial_mode': TEXT,
    'selected_mode': TEXT, 'display_mode': TEXT, 'frame': INDEX,
    'frame_count': {'type': 'integer', 'minimum': 1}, 'width': {'type': 'integer', 'minimum': 1},
    'height': {'type': 'integer', 'minimum': 1}, 'colour_conversion': choice('preserve', 'rgb'),
    'software': {'const': 'Pillow'}, 'software_version': TEXT, 'geometric_transform': {'const': 'identity'},
    'contrast_transform': {'const': 'identity'}, 'orientation': {'const': 'stored_pixel_axis_no_exif_rotation'}}
OWN_VIEW_RECEIPT = obj({'run_id': TEXT, 'episode_id': TEXT, 'decision_index': INDEX,
    'operation_ref': REF, 'result_sha256': TEXT, 'view_ref': REF})
view = obj({'view_ref': REF, 'metadata': nullable(obj(view_fields)),
    'original_sha256': {'type': ['string', 'null']}, 'display_sha256': {'type': ['string', 'null']},
    'own_action_receipt': nullable(OWN_VIEW_RECEIPT), 'state': choice('available', 'unavailable'),
    'diagnostics': arr(DIAGNOSTIC)})
parsed_number = obj({'literal': TEXT, 'relation': choice('point', 'lt', 'le', 'gt', 'ge', 'unavailable'),
    'value': NUMBER, 'exact': nullable(RATIONAL), 'locator': nullable(LOCATOR), 'diagnostics': arr(DIAGNOSTIC)})
reading = obj({'candidate_index': INDEX, 'numerator': parsed_number, 'denominator': nullable(parsed_number),
    'ratio': NUMBER, 'ratio_exact': nullable(RATIONAL), 'reported_domains': arr(DOMAIN),
    'source_reading_key': {'type': ['string', 'null']}, 'diagnostics': arr(DIAGNOSTIC)})
row = obj({'representation_id': TEXT, 'kind': choice('jats_percent', 'visual_ratio', 'visual_percent', 'visual_signal_pair'),
    'selection': {'oneOf': [jats_selection, visual_selection]},
    'comparison_relation': extracted_meaning(RELATION),
    'physical_measurement': extracted_meaning(meaning()), 'reference_measurement': extracted_meaning(meaning()),
    'reading_state': choice(*READING), 'readings': arr(reading),
    'fragments': arr(obj({'selection': FRAGMENT, 'locator': nullable(IMAGE_LOCATOR), 'diagnostics': arr(DIAGNOSTIC)})),
    'origin': choice('reported', 'visual_transcription'), 'diagnostics': arr(DIAGNOSTIC)})
EXTRACTION = obj({'version': {'const': 'relative_signal_source_extraction_v2'}, 'selection': REQUEST,
    'sources': arr(obj({'source_ref': REF, 'representation': choice('original', 'text'),
        'artifact_ref': {'type': ['string', 'null'], 'format': 'reference'},
        'byte_sha256': {'type': ['string', 'null']}, 'state': choice('available', 'unavailable'),
        'diagnostics': arr(DIAGNOSTIC)})), 'views': arr(view),
    'comparison': obj({name: extracted_meaning(value) for name, value in comparison.items()}),
    'representations': arr(row), 'interpretation_attribution': {'const': 'investigating_episode_interpretation'}})
CELL = obj({'value': NUMBER, 'value_candidates': arr({'type': 'number'}, uniqueItems=True),
    'reported_domains': arr(DOMAIN), 'unit': {'type': ['string', 'null'], 'enum': ['fraction', 'dimensionless', None]},
    'status': choice('populated', 'conflicting', 'unavailable'), 'origin': choice('reported', 'visual_transcription', 'derived', 'proposed'),
    'formula': TEXT, 'unavailable_reason': {'type': ['string', 'null'], 'enum': [*REASONS, None]},
    'conditional_on': arr(choice('source_comparison_interpretation', 'nominated_printed_signal_pair'), uniqueItems=True)})
SHEET = obj({'version': {'const': 'relative_signal_sheet_v2'}, 'scope': {'const': 'reported_relative_signal'},
    'cells': obj({name: CELL for name in COMPONENTS}), 'selected_roster_resolved': BOOL,
    'point_candidate_set_complete': BOOL, 'known_source_conflict': BOOL,
    'independent_preparation_count': {'type': 'null'}, 'annotation_credit': {'type': 'null'}})


def report_ref(namespace, nullable_value=False):
    return {'type': ['string', 'null'] if nullable_value else 'string', 'format': 'reference',
            'x-reference-namespace': namespace}


return_domain = deepcopy(DOMAIN)
properties = {name: deepcopy(value) for name, value in CELL['properties'].items() if name != 'formula'}
properties.update(sheet_ref=report_ref('source'), evidence_source_ref=report_ref('source'),
    component=choice(*COMPONENTS), selected_roster_resolved=BOOL, point_candidate_set_complete=BOOL,
    known_source_conflict=BOOL, independent_preparation_count={'type': 'null'},
    candidate_basis={'const': 'selected_received_source_representations'},
    uncertainty_kind={'const': 'unreported'}, interpretation_kind={'const': 'episode_source_interpretation'},
    source_origins=arr(choice('reported', 'visual_transcription'), uniqueItems=True),
    representation_reading_states=arr(choice(*READING), uniqueItems=True),
    signal_kind=choice('protein_band', 'transcript_signal', 'other_reported_signal', 'unknown', 'conflicting'),
    reference_role=choice('tagged_wt_complementation', 'endogenous_wt', 'other_reported_reference', 'unknown', 'conflicting'),
    arrangement=choice('single_preparation', 'replacement', 'coexistence', 'not_applicable', 'unknown', 'conflicting'))
for name in COMPARISON_FIELDS:
    properties[name + '_ref'] = report_ref('context' if name == 'condition' else 'reference', True)
properties['input_measurement_refs'] = arr(report_ref('reference'), uniqueItems=True)
properties['reference_measurement_refs'] = arr(report_ref('reference'), uniqueItems=True)
RETURN = arr(obj(properties))
RETURN['x-source'] = 'literature_ratio_source_cells'


def main():
    documents = {'REQUEST_SCHEMA_001.json': REQUEST, 'EXTRACTION_SCHEMA_001.json': EXTRACTION,
                 'SHEET_SCHEMA_001.json': SHEET, 'RETURN_SCHEMA_001.json': RETURN}
    for name, document in documents.items():
        with (HERE / name).open('x') as stream:
            json.dump(document, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write('\n')
    print(json.dumps({'design_schemas_written': len(documents), 'application_imports': 0,
                      'scientific_reader_or_calculator_executed': False}))


if __name__ == '__main__':
    main()
