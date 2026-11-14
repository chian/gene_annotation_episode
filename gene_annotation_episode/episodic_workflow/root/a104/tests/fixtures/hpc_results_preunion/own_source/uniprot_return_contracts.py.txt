"""Exact selected UniProt return shapes and source-independent value checks.

One definition tree supplies both selection and expanded return schemas. These
checks establish internal relationships only; the owning return reader must
separately authenticate actual source bytes, publications and receipt custody.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re

from jsonschema import Draft202012Validator, ValidationError, validators


SOURCE = "uniprot_selected_returns"
_SELECTION_VERSION = "uniprot_return_selection_v1"

# The frozen Contract002 definitions are internal data, never model context.
_DEFINITIONS = {'Pointer': {'type': 'string', 'pattern': '^(?:/(?:[^~/]|~0|~1)*)*$'},
 'RelativePointer': {'type': 'string', 'pattern': '^/(?:[^~/]|~0|~1)*(?:/(?:[^~/]|~0|~1)*)*$'},
 'Digest': {'type': 'string', 'minLength': 1, 'pattern': '^[0-9a-f]{64}$'},
 'NativeState': {'type': 'string', 'enum': ['present', 'absent', 'null', 'invalid']},
 'Representation': {'type': 'string', 'enum': ['exact', 'unavailable']},
 'NativeToken': {'type': 'object',
                 'properties': {'native_state': {'$ref': '#/$defs/NativeState'},
                                'representation': {'$ref': '#/$defs/Representation'},
                                'value': {'anyOf': [{'type': 'string',
                                                     'minLength': 1,
                                                     'pattern': '^[^\\s\\x00-\\x1f\\x7f]+$'},
                                                    {'type': 'null'}]},
                                'pointer': {'$ref': '#/$defs/Pointer'}},
                 'required': ['native_state', 'representation', 'value', 'pointer'],
                 'additionalProperties': False},
 'IntegerValue': {'type': 'object',
                  'properties': {'native_state': {'$ref': '#/$defs/NativeState'},
                                 'value': {'anyOf': [{'type': 'integer', 'minimum': 0},
                                                     {'type': 'null'}]},
                                 'pointer': {'$ref': '#/$defs/Pointer'},
                                 'origin': {'type': 'string', 'enum': ['native', 'derived']},
                                 'unit': {'type': 'string',
                                          'enum': ['taxon_id', 'version', 'aa', 'count']}},
                  'required': ['native_state', 'value', 'pointer', 'origin', 'unit'],
                  'additionalProperties': False},
 'TextWindow': {'type': 'object',
                'properties': {'native_state': {'$ref': '#/$defs/NativeState'},
                               'pointer': {'$ref': '#/$defs/Pointer'},
                               'owner_pointer': {'$ref': '#/$defs/Pointer'},
                               'offset': {'type': 'integer', 'minimum': 0},
                               'limit': {'type': 'integer', 'minimum': 1},
                               'native_length': {'anyOf': [{'type': 'integer', 'minimum': 0},
                                                           {'type': 'null'}]},
                               'start': {'anyOf': [{'type': 'integer', 'minimum': 0},
                                                   {'type': 'null'}]},
                               'end': {'anyOf': [{'type': 'integer', 'minimum': 0},
                                                 {'type': 'null'}]},
                               'text': {'anyOf': [{'type': 'string', 'maxLength': 0},
                                                  {'type': 'null'}]},
                               'omitted_prefix': {'anyOf': [{'type': 'integer', 'minimum': 0},
                                                            {'type': 'null'}]},
                               'omitted_suffix': {'anyOf': [{'type': 'integer', 'minimum': 0},
                                                            {'type': 'null'}]},
                               'extent': {'type': 'string',
                                          'enum': ['whole_value',
                                                   'window',
                                                   'empty_value',
                                                   'offset_past_end',
                                                   'unavailable']},
                               'unit': {'type': 'string', 'const': 'unicode_code_points'}},
                'required': ['native_state',
                             'pointer',
                             'owner_pointer',
                             'offset',
                             'limit',
                             'native_length',
                             'start',
                             'end',
                             'text',
                             'omitted_prefix',
                             'omitted_suffix',
                             'extent',
                             'unit'],
                'additionalProperties': False},
 'Position': {'type': 'object',
              'properties': {'native_state': {'$ref': '#/$defs/NativeState'},
                             'value': {'anyOf': [{'type': 'integer', 'minimum': 0},
                                                 {'type': 'null'}]},
                             'value_pointer': {'$ref': '#/$defs/Pointer'},
                             'value_state': {'$ref': '#/$defs/NativeState'},
                             'modifier': {'$ref': '#/$defs/NativeToken'}},
              'required': ['native_state', 'value', 'value_pointer', 'value_state', 'modifier'],
              'additionalProperties': False},
 'FeatureLocationValue': {'type': 'object',
                          'properties': {'ordinal': {'type': 'integer', 'minimum': 0},
                                         'pointer': {'$ref': '#/$defs/Pointer'},
                                         'start': {'$ref': '#/$defs/Position'},
                                         'end': {'$ref': '#/$defs/Position'},
                                         'native_sequence_id': {'$ref': '#/$defs/NativeToken'},
                                         'sequence_binding': {'type': 'string',
                                                              'enum': ['entry_sequence',
                                                                       'explicit_other_sequence',
                                                                       'unresolved']},
                                         'native_coordinates': {'type': 'string',
                                                                'const': 'one_based_inclusive'},
                                         'exact_interval': {'anyOf': [{'type': 'array',
                                                                       'items': {'type': 'integer',
                                                                                 'minimum': 0},
                                                                       'minItems': 2,
                                                                       'maxItems': 2},
                                                                      {'type': 'null'}]},
                                         'derived_coordinates': {'type': 'string',
                                                                 'const': 'zero_based_half_open'},
                                         'unit': {'type': 'string', 'const': 'aa'},
                                         'type_window': {'anyOf': [{'$ref': '#/$defs/TextWindow'},
                                                                   {'type': 'null'}]},
                                         'description_window': {'anyOf': [{'$ref': '#/$defs/TextWindow'},
                                                                          {'type': 'null'}]},
                                         'evidence': {'anyOf': [{'$ref': '#/$defs/EvidenceCollection'},
                                                                {'type': 'null'}]}},
                          'required': ['ordinal',
                                       'pointer',
                                       'start',
                                       'end',
                                       'native_sequence_id',
                                       'sequence_binding',
                                       'native_coordinates',
                                       'exact_interval',
                                       'derived_coordinates',
                                       'unit',
                                       'type_window',
                                       'description_window',
                                       'evidence'],
                          'additionalProperties': False},
 'EvidenceValue': {'type': 'object',
                   'properties': {'ordinal': {'type': 'integer', 'minimum': 0},
                                  'pointer': {'$ref': '#/$defs/Pointer'},
                                  'owner_pointer': {'$ref': '#/$defs/Pointer'},
                                  'eco': {'$ref': '#/$defs/NativeToken'},
                                  'source': {'$ref': '#/$defs/NativeToken'},
                                  'source_identifier': {'$ref': '#/$defs/NativeToken'}},
                   'required': ['ordinal',
                                'pointer',
                                'owner_pointer',
                                'eco',
                                'source',
                                'source_identifier'],
                   'additionalProperties': False},
 'ECValue': {'type': 'object',
             'properties': {'pointer': {'$ref': '#/$defs/Pointer'},
                            'owner_pointer': {'$ref': '#/$defs/Pointer'},
                            'name_group_pointer': {'$ref': '#/$defs/Pointer'},
                            'component_pointer': {'anyOf': [{'$ref': '#/$defs/Pointer'},
                                                            {'type': 'null'}]},
                            'scope': {'type': 'string', 'enum': ['entry', 'component']},
                            'ec': {'$ref': '#/$defs/NativeToken'},
                            'interpretation': {'type': 'string',
                                               'const': 'external_annotation_not_target_experiment'}},
             'required': ['pointer',
                          'owner_pointer',
                          'name_group_pointer',
                          'component_pointer',
                          'scope',
                          'ec',
                          'interpretation'],
             'additionalProperties': False},
 'CrossReferenceValue': {'type': 'object',
                         'properties': {'ordinal': {'type': 'integer', 'minimum': 0},
                                        'pointer': {'$ref': '#/$defs/Pointer'},
                                        'database': {'$ref': '#/$defs/NativeToken'},
                                        'identifier': {'$ref': '#/$defs/NativeToken'},
                                        'properties_state': {'$ref': '#/$defs/NativeState'},
                                        'evidence': {'anyOf': [{'$ref': '#/$defs/EvidenceCollection'},
                                                               {'type': 'null'}]},
                                        'properties': {'type': 'array',
                                                       'items': {'$ref': '#/$defs/XrefPropertyReply'}}},
                         'required': ['ordinal',
                                      'pointer',
                                      'database',
                                      'identifier',
                                      'properties_state',
                                      'evidence',
                                      'properties'],
                         'additionalProperties': False},
 'SequenceWindowValue': {'type': 'object',
                         'properties': {'start': {'type': 'integer', 'minimum': 0},
                                        'end': {'type': 'integer', 'minimum': 1},
                                        'sequence_length': {'type': 'integer', 'minimum': 0},
                                        'sequence_sha256': {'$ref': '#/$defs/Digest'},
                                        'value': {'type': 'string', 'pattern': '^[A-Z]+$'},
                                        'coordinates': {'type': 'string',
                                                        'const': 'zero_based_half_open'},
                                        'unit': {'type': 'string', 'const': 'aa'},
                                        'reported_length_state': {'$ref': '#/$defs/NativeState'},
                                        'reported_length': {'anyOf': [{'type': 'integer',
                                                                       'minimum': 0},
                                                                      {'type': 'null'}]},
                                        'length_relation': {'type': 'string',
                                                            'enum': ['agree',
                                                                     'conflict',
                                                                     'unavailable']}},
                         'required': ['start',
                                      'end',
                                      'sequence_length',
                                      'sequence_sha256',
                                      'value',
                                      'coordinates',
                                      'unit',
                                      'reported_length_state',
                                      'reported_length',
                                      'length_relation'],
                         'additionalProperties': False},
 'IntegerRequest': {'type': 'object',
                    'properties': {'kind': {'type': 'string', 'const': 'integer'},
                                   'field': {'type': 'string',
                                             'enum': ['taxon_id',
                                                      'entry_version',
                                                      'sequence_version',
                                                      'reported_sequence_length',
                                                      'observed_sequence_length']}},
                    'required': ['kind', 'field'],
                    'additionalProperties': False},
 'TokenRequest': {'type': 'object',
                  'properties': {'kind': {'type': 'string', 'const': 'token'},
                                 'field': {'type': 'string',
                                           'enum': ['primary_accession',
                                                    'secondary_accession',
                                                    'uniprot_id',
                                                    'sequence_md5',
                                                    'sequence_crc64']},
                                 'array_ordinal': {'anyOf': [{'type': 'integer', 'minimum': 0},
                                                             {'type': 'null'}]}},
                  'required': ['kind', 'field', 'array_ordinal'],
                  'additionalProperties': False},
 'TextRequest': {'type': 'object',
                 'properties': {'kind': {'type': 'string', 'const': 'text'},
                                'field': {'type': 'string',
                                          'enum': ['protein_name',
                                                   'gene_name',
                                                   'entry_type',
                                                   'protein_existence',
                                                   'entry_date',
                                                   'taxon_name',
                                                   'taxon_synonym',
                                                   'taxon_lineage_name',
                                                   'feature_type',
                                                   'feature_description',
                                                   'xref_property_key',
                                                   'xref_property_value',
                                                   'comment_text',
                                                   'native_text']},
                                'pointer': {'$ref': '#/$defs/RelativePointer'},
                                'offset': {'type': 'integer', 'minimum': 0},
                                'limit': {'type': 'integer', 'minimum': 1}},
                 'required': ['kind', 'field', 'pointer', 'offset', 'limit'],
                 'additionalProperties': False},
 'ECRequest': {'type': 'object',
               'properties': {'kind': {'type': 'string', 'const': 'ec_assignment'},
                              'pointer': {'$ref': '#/$defs/RelativePointer'}},
               'required': ['kind', 'pointer'],
               'additionalProperties': False},
 'FeatureRequest': {'type': 'object',
                    'properties': {'kind': {'type': 'string', 'const': 'feature_location'},
                                   'selection': {'$ref': '#/$defs/FeatureSelector'},
                                   'include_evidence': {'type': 'boolean'},
                                   'type_window': {'anyOf': [{'$ref': '#/$defs/TextRange'},
                                                             {'type': 'null'}]},
                                   'description_window': {'anyOf': [{'$ref': '#/$defs/TextRange'},
                                                                    {'type': 'null'}]}},
                    'required': ['kind',
                                 'selection',
                                 'include_evidence',
                                 'type_window',
                                 'description_window'],
                    'additionalProperties': False},
 'EvidenceRequest': {'type': 'object',
                     'properties': {'kind': {'type': 'string', 'const': 'evidence'},
                                    'selection': {'$ref': '#/$defs/EvidenceSelector'}},
                     'required': ['kind', 'selection'],
                     'additionalProperties': False},
 'XrefRequest': {'type': 'object',
                 'properties': {'kind': {'type': 'string', 'const': 'cross_reference'},
                                'selection': {'$ref': '#/$defs/XrefSelector'},
                                'include_evidence': {'type': 'boolean'},
                                'properties': {'type': 'array',
                                               'items': {'$ref': '#/$defs/XrefPropertyRequest'}}},
                 'required': ['kind', 'selection', 'include_evidence', 'properties'],
                 'additionalProperties': False},
 'SequenceRequest': {'type': 'object',
                     'properties': {'kind': {'type': 'string', 'const': 'sequence_window'},
                                    'start': {'type': 'integer', 'minimum': 0},
                                    'end': {'type': 'integer', 'minimum': 1}},
                     'required': ['kind', 'start', 'end'],
                     'additionalProperties': False},
 'RecordFieldRequest': {'oneOf': [{'$ref': '#/$defs/IntegerRequest'},
                                  {'$ref': '#/$defs/TokenRequest'},
                                  {'$ref': '#/$defs/TextRequest'},
                                  {'$ref': '#/$defs/ECRequest'},
                                  {'$ref': '#/$defs/FeatureRequest'},
                                  {'$ref': '#/$defs/EvidenceRequest'},
                                  {'$ref': '#/$defs/XrefRequest'},
                                  {'$ref': '#/$defs/SequenceRequest'}]},
 'PageIntegerRequest': {'type': 'object',
                        'properties': {'kind': {'type': 'string', 'const': 'page_integer'},
                                       'field': {'type': 'string', 'const': 'total_results'}},
                        'required': ['kind', 'field'],
                        'additionalProperties': False},
 'PageTokenRequest': {'type': 'object',
                      'properties': {'kind': {'type': 'string', 'const': 'page_token'},
                                     'field': {'type': 'string',
                                               'enum': ['release',
                                                        'release_date',
                                                        'next_cursor',
                                                        'next_url']}},
                      'required': ['kind', 'field'],
                      'additionalProperties': False},
 'PageTextRequest': {'type': 'object',
                     'properties': {'kind': {'type': 'string', 'const': 'page_text'},
                                    'field': {'type': 'string',
                                              'enum': ['effective_query',
                                                       'release',
                                                       'release_date',
                                                       'next_cursor',
                                                       'next_url']},
                                    'offset': {'type': 'integer', 'minimum': 0},
                                    'limit': {'type': 'integer', 'minimum': 1}},
                     'required': ['kind', 'field', 'offset', 'limit'],
                     'additionalProperties': False},
 'PageFieldRequest': {'oneOf': [{'$ref': '#/$defs/PageIntegerRequest'},
                                {'$ref': '#/$defs/PageTokenRequest'},
                                {'$ref': '#/$defs/PageTextRequest'}]},
 'PublicationSelector': {'oneOf': [{'type': 'object',
                                    'properties': {'mode': {'type': 'string',
                                                            'const': 'assigned_page'}},
                                    'required': ['mode'],
                                    'additionalProperties': False},
                                   {'type': 'object',
                                    'properties': {'mode': {'type': 'string',
                                                            'const': 'received_publication'},
                                                   'source_id': {'type': 'string',
                                                                 'minLength': 1,
                                                                 'pattern': '^source_[0-9a-f]+$'},
                                                   'publication_sha256': {'$ref': '#/$defs/Digest'}},
                                    'required': ['mode', 'source_id', 'publication_sha256'],
                                    'additionalProperties': False}]},
 'RecordSelection': {'type': 'object',
                     'properties': {'record': {'$ref': '#/$defs/RecordSelector'},
                                    'fields': {'type': 'array',
                                               'items': {'$ref': '#/$defs/RecordFieldRequest'}},
                                    'grant_sequence_artifact': {'type': 'boolean'}},
                     'required': ['record', 'fields', 'grant_sequence_artifact'],
                     'additionalProperties': False},
 'PageSelection': {'type': 'object',
                   'properties': {'publication': {'$ref': '#/$defs/PublicationSelector'},
                                  'page_fields': {'type': 'array',
                                                  'items': {'$ref': '#/$defs/PageFieldRequest'}},
                                  'records': {'type': 'array',
                                              'items': {'$ref': '#/$defs/RecordSelection'}},
                                  'grant_source': {'type': 'boolean'}},
                   'required': ['publication', 'page_fields', 'records', 'grant_source'],
                   'additionalProperties': False},
 'Selection': {'type': 'object',
               'properties': {'version': {'type': 'string', 'const': 'uniprot_return_selection_v1'},
                              'pages': {'type': 'array',
                                        'items': {'$ref': '#/$defs/PageSelection'}}},
               'required': ['version', 'pages'],
               'additionalProperties': False},
 'Failure': {'type': 'object',
             'properties': {'code': {'type': 'string',
                                     'enum': ['not_acquired',
                                              'publication_not_received',
                                              'record_not_in_response',
                                              'record_parser_unpublishable',
                                              'record_binding_omitted',
                                              'field_absent',
                                              'field_null',
                                              'field_invalid',
                                              'field_not_received',
                                              'token_not_representable',
                                              'text_pointer_not_string',
                                              'sequence_unavailable',
                                              'sequence_window_out_of_range',
                                              'sequence_artifact_not_received',
                                              'source_not_received',
                                              'selected_ordinal_unavailable',
                                              'record_selection_no_match',
                                              'record_selection_indeterminate',
                                              'page_field_unavailable',
                                              'property_not_received',
                                              'property_not_found',
                                              'publication_unavailable']},
                            'page_selection_index': {'type': 'integer', 'minimum': 0},
                            'record_selection_index': {'anyOf': [{'type': 'integer', 'minimum': 0},
                                                                 {'type': 'null'}]},
                            'field_selection_index': {'anyOf': [{'type': 'integer', 'minimum': 0},
                                                                {'type': 'null'}]},
                            'native_pointer': {'anyOf': [{'$ref': '#/$defs/Pointer'},
                                                         {'type': 'null'}]}},
             'required': ['code',
                          'page_selection_index',
                          'record_selection_index',
                          'field_selection_index',
                          'native_pointer'],
             'additionalProperties': False},
 'RecordFieldReply': {'oneOf': [{'type': 'object',
                                 'properties': {'request_index': {'type': 'integer', 'minimum': 0},
                                                'request': {'$ref': '#/$defs/IntegerRequest'},
                                                'status': {'type': 'string',
                                                           'enum': ['available',
                                                                    'partial',
                                                                    'unavailable']},
                                                'value': {'anyOf': [{'$ref': '#/$defs/IntegerValue'},
                                                                    {'type': 'null'}]},
                                                'failures': {'type': 'array',
                                                             'items': {'$ref': '#/$defs/Failure'}}},
                                 'required': ['request_index',
                                              'request',
                                              'status',
                                              'value',
                                              'failures'],
                                 'additionalProperties': False},
                                {'type': 'object',
                                 'properties': {'request_index': {'type': 'integer', 'minimum': 0},
                                                'request': {'$ref': '#/$defs/TokenRequest'},
                                                'status': {'type': 'string',
                                                           'enum': ['available',
                                                                    'partial',
                                                                    'unavailable']},
                                                'value': {'anyOf': [{'$ref': '#/$defs/NativeToken'},
                                                                    {'type': 'null'}]},
                                                'failures': {'type': 'array',
                                                             'items': {'$ref': '#/$defs/Failure'}}},
                                 'required': ['request_index',
                                              'request',
                                              'status',
                                              'value',
                                              'failures'],
                                 'additionalProperties': False},
                                {'type': 'object',
                                 'properties': {'request_index': {'type': 'integer', 'minimum': 0},
                                                'request': {'$ref': '#/$defs/TextRequest'},
                                                'status': {'type': 'string',
                                                           'enum': ['available',
                                                                    'partial',
                                                                    'unavailable']},
                                                'value': {'anyOf': [{'$ref': '#/$defs/TextWindow'},
                                                                    {'type': 'null'}]},
                                                'failures': {'type': 'array',
                                                             'items': {'$ref': '#/$defs/Failure'}}},
                                 'required': ['request_index',
                                              'request',
                                              'status',
                                              'value',
                                              'failures'],
                                 'additionalProperties': False},
                                {'type': 'object',
                                 'properties': {'request_index': {'type': 'integer', 'minimum': 0},
                                                'request': {'$ref': '#/$defs/ECRequest'},
                                                'status': {'type': 'string',
                                                           'enum': ['available',
                                                                    'partial',
                                                                    'unavailable']},
                                                'value': {'anyOf': [{'$ref': '#/$defs/ECValue'},
                                                                    {'type': 'null'}]},
                                                'failures': {'type': 'array',
                                                             'items': {'$ref': '#/$defs/Failure'}}},
                                 'required': ['request_index',
                                              'request',
                                              'status',
                                              'value',
                                              'failures'],
                                 'additionalProperties': False},
                                {'type': 'object',
                                 'properties': {'request_index': {'type': 'integer', 'minimum': 0},
                                                'request': {'$ref': '#/$defs/FeatureRequest'},
                                                'status': {'type': 'string',
                                                           'enum': ['available',
                                                                    'partial',
                                                                    'unavailable']},
                                                'value': {'anyOf': [{'$ref': '#/$defs/FeatureCollection'},
                                                                    {'type': 'null'}]},
                                                'failures': {'type': 'array',
                                                             'items': {'$ref': '#/$defs/Failure'}}},
                                 'required': ['request_index',
                                              'request',
                                              'status',
                                              'value',
                                              'failures'],
                                 'additionalProperties': False},
                                {'type': 'object',
                                 'properties': {'request_index': {'type': 'integer', 'minimum': 0},
                                                'request': {'$ref': '#/$defs/EvidenceRequest'},
                                                'status': {'type': 'string',
                                                           'enum': ['available',
                                                                    'partial',
                                                                    'unavailable']},
                                                'value': {'anyOf': [{'$ref': '#/$defs/EvidenceCollection'},
                                                                    {'type': 'null'}]},
                                                'failures': {'type': 'array',
                                                             'items': {'$ref': '#/$defs/Failure'}}},
                                 'required': ['request_index',
                                              'request',
                                              'status',
                                              'value',
                                              'failures'],
                                 'additionalProperties': False},
                                {'type': 'object',
                                 'properties': {'request_index': {'type': 'integer', 'minimum': 0},
                                                'request': {'$ref': '#/$defs/XrefRequest'},
                                                'status': {'type': 'string',
                                                           'enum': ['available',
                                                                    'partial',
                                                                    'unavailable']},
                                                'value': {'anyOf': [{'$ref': '#/$defs/XrefCollection'},
                                                                    {'type': 'null'}]},
                                                'failures': {'type': 'array',
                                                             'items': {'$ref': '#/$defs/Failure'}}},
                                 'required': ['request_index',
                                              'request',
                                              'status',
                                              'value',
                                              'failures'],
                                 'additionalProperties': False},
                                {'type': 'object',
                                 'properties': {'request_index': {'type': 'integer', 'minimum': 0},
                                                'request': {'$ref': '#/$defs/SequenceRequest'},
                                                'status': {'type': 'string',
                                                           'enum': ['available',
                                                                    'partial',
                                                                    'unavailable']},
                                                'value': {'anyOf': [{'$ref': '#/$defs/SequenceWindowValue'},
                                                                    {'type': 'null'}]},
                                                'failures': {'type': 'array',
                                                             'items': {'$ref': '#/$defs/Failure'}}},
                                 'required': ['request_index',
                                              'request',
                                              'status',
                                              'value',
                                              'failures'],
                                 'additionalProperties': False}]},
 'PageFieldReply': {'oneOf': [{'type': 'object',
                               'properties': {'request_index': {'type': 'integer', 'minimum': 0},
                                              'request': {'$ref': '#/$defs/PageIntegerRequest'},
                                              'status': {'type': 'string',
                                                         'enum': ['available',
                                                                  'partial',
                                                                  'unavailable']},
                                              'value': {'anyOf': [{'$ref': '#/$defs/IntegerValue'},
                                                                  {'type': 'null'}]},
                                              'failures': {'type': 'array',
                                                           'items': {'$ref': '#/$defs/Failure'}}},
                               'required': ['request_index',
                                            'request',
                                            'status',
                                            'value',
                                            'failures'],
                               'additionalProperties': False},
                              {'type': 'object',
                               'properties': {'request_index': {'type': 'integer', 'minimum': 0},
                                              'request': {'$ref': '#/$defs/PageTokenRequest'},
                                              'status': {'type': 'string',
                                                         'enum': ['available',
                                                                  'partial',
                                                                  'unavailable']},
                                              'value': {'anyOf': [{'$ref': '#/$defs/NativeToken'},
                                                                  {'type': 'null'}]},
                                              'failures': {'type': 'array',
                                                           'items': {'$ref': '#/$defs/Failure'}}},
                               'required': ['request_index',
                                            'request',
                                            'status',
                                            'value',
                                            'failures'],
                               'additionalProperties': False},
                              {'type': 'object',
                               'properties': {'request_index': {'type': 'integer', 'minimum': 0},
                                              'request': {'$ref': '#/$defs/PageTextRequest'},
                                              'status': {'type': 'string',
                                                         'enum': ['available',
                                                                  'partial',
                                                                  'unavailable']},
                                              'value': {'anyOf': [{'$ref': '#/$defs/TextWindow'},
                                                                  {'type': 'null'}]},
                                              'failures': {'type': 'array',
                                                           'items': {'$ref': '#/$defs/Failure'}}},
                               'required': ['request_index',
                                            'request',
                                            'status',
                                            'value',
                                            'failures'],
                               'additionalProperties': False}]},
 'PageWitness': {'type': 'object',
                 'properties': {'source_id': {'type': 'string',
                                              'minLength': 1,
                                              'pattern': '^source_[0-9a-f]+$'},
                                'native_artifact_id': {'type': 'string',
                                                       'minLength': 1,
                                                       'pattern': '^artifact_[0-9a-f]+$'},
                                'content_sha256': {'$ref': '#/$defs/Digest'},
                                'publication_sha256': {'$ref': '#/$defs/Digest'}},
                 'required': ['source_id',
                              'native_artifact_id',
                              'content_sha256',
                              'publication_sha256'],
                 'additionalProperties': False},
 'RecordWitness': {'type': 'object',
                   'properties': {'record_id': {'type': 'string',
                                                'minLength': 1,
                                                'pattern': '^reference_[0-9a-f]+$'},
                                  'record_ordinal': {'type': 'integer', 'minimum': 0},
                                  'record_pointer': {'$ref': '#/$defs/Pointer'},
                                  'accession_relation': {'type': 'string',
                                                         'enum': ['primary',
                                                                  'secondary',
                                                                  'search_member',
                                                                  'unverified']},
                                  'sequence_artifact_id': {'anyOf': [{'type': 'string',
                                                                      'minLength': 1,
                                                                      'pattern': '^artifact_[0-9a-f]+$'},
                                                                     {'type': 'null'}]}},
                   'required': ['record_id',
                                'record_ordinal',
                                'record_pointer',
                                'accession_relation',
                                'sequence_artifact_id'],
                   'additionalProperties': False},
 'Issue': {'type': 'object',
           'properties': {'origin': {'type': 'string',
                                     'enum': ['native_page',
                                              'native_record',
                                              'native_projection',
                                              'publication_projection',
                                              'publication_qualification']},
                          'original_issue_index': {'type': 'integer', 'minimum': 0},
                          'code': {'type': 'string',
                                   'enum': ['invalid_json',
                                            'invalid_envelope',
                                            'request_mismatch',
                                            'accession_unmatched',
                                            'record_not_object',
                                            'primary_accession_missing',
                                            'field_type_invalid',
                                            'sequence_invalid',
                                            'sequence_length_conflict',
                                            'feature_location_invalid',
                                            'feature_sequence_unresolved',
                                            'evidence_row_invalid',
                                            'cross_reference_invalid',
                                            'link_invalid',
                                            'link_query_conflict',
                                            'total_results_invalid',
                                            'release_conflict',
                                            'native_request_unverified',
                                            'uniprot_legacy_label_unrepresentable',
                                            'uniprot_legacy_term_unrepresentable',
                                            'uniprot_legacy_reference_unrepresentable',
                                            'uniprot_legacy_source_version_omitted']},
                          'record_ordinal': {'anyOf': [{'type': 'integer', 'minimum': 0},
                                                       {'type': 'null'}]},
                          'pointer': {'$ref': '#/$defs/Pointer'},
                          'field': {'type': 'string',
                                    'enum': ['envelope',
                                             'request',
                                             'identity',
                                             'metadata',
                                             'sequence',
                                             'taxon',
                                             'features',
                                             'evidence',
                                             'cross_references',
                                             'pagination',
                                             'legacy_publication',
                                             'legacy_source']},
                          'effect': {'type': 'string',
                                     'enum': ['page_unusable',
                                              'record_unpublishable',
                                              'field_partial',
                                              'qualification']}},
           'required': ['origin',
                        'original_issue_index',
                        'code',
                        'record_ordinal',
                        'pointer',
                        'field',
                        'effect'],
           'additionalProperties': False},
 'SourceGrant': {'type': 'object',
                 'properties': {'source_ref': {'type': 'string',
                                               'format': 'reference',
                                               'x-reference-namespace': 'source'},
                                'native_artifact_id': {'type': 'string',
                                                       'minLength': 1,
                                                       'pattern': '^artifact_[0-9a-f]+$'},
                                'content_sha256': {'$ref': '#/$defs/Digest'},
                                'meaning': {'type': 'string',
                                            'const': 'explicit_whole_native_source'}},
                 'required': ['source_ref', 'native_artifact_id', 'content_sha256', 'meaning'],
                 'additionalProperties': False},
 'SequenceGrant': {'type': 'object',
                   'properties': {'artifact_ref': {'type': 'string',
                                                   'format': 'reference',
                                                   'x-reference-namespace': 'artifact'},
                                  'record_id': {'type': 'string',
                                                'minLength': 1,
                                                'pattern': '^reference_[0-9a-f]+$'},
                                  'record_ordinal': {'type': 'integer', 'minimum': 0},
                                  'sequence_sha256': {'$ref': '#/$defs/Digest'},
                                  'length': {'type': 'integer', 'minimum': 0},
                                  'unit': {'type': 'string', 'const': 'aa'},
                                  'molecule': {'type': 'string', 'const': 'protein'},
                                  'meaning': {'type': 'string',
                                              'const': 'explicit_full_sequence_artifact'}},
                   'required': ['artifact_ref',
                                'record_id',
                                'record_ordinal',
                                'sequence_sha256',
                                'length',
                                'unit',
                                'molecule',
                                'meaning'],
                   'additionalProperties': False},
 'GrantStatus': {'type': 'string', 'enum': ['not_requested', 'available', 'unavailable']},
 'RecordReply': {'type': 'object',
                 'properties': {'record_selection_index': {'type': 'integer', 'minimum': 0},
                                'requested_record_ordinal': {'type': 'integer', 'minimum': 0},
                                'state': {'type': 'string',
                                          'enum': ['bound',
                                                   'parser_unpublishable',
                                                   'binding_omitted',
                                                   'not_in_response',
                                                   'unavailable']},
                                'witness': {'anyOf': [{'$ref': '#/$defs/RecordWitness'},
                                                      {'type': 'null'}]},
                                'fields': {'type': 'array',
                                           'items': {'$ref': '#/$defs/RecordFieldReply'}},
                                'issues': {'type': 'array', 'items': {'$ref': '#/$defs/Issue'}},
                                'sequence_grant_status': {'$ref': '#/$defs/GrantStatus'},
                                'sequence_grant': {'anyOf': [{'$ref': '#/$defs/SequenceGrant'},
                                                             {'type': 'null'}]},
                                'failures': {'type': 'array',
                                             'items': {'$ref': '#/$defs/Failure'}}},
                 'required': ['record_selection_index',
                              'requested_record_ordinal',
                              'state',
                              'witness',
                              'fields',
                              'issues',
                              'sequence_grant_status',
                              'sequence_grant',
                              'failures'],
                 'additionalProperties': False},
 'PageStatus': {'type': 'object',
                'properties': {'operation': {'type': 'string',
                                             'enum': ['record', 'search', 'unknown']},
                               'selection_extent': {'type': 'string',
                                                    'enum': ['one_record',
                                                             'one_selected_page',
                                                             'not_established']},
                               'response_body_state': {'type': 'string',
                                                       'enum': ['complete_json',
                                                                'invalid_json',
                                                                'invalid_envelope']},
                               'parser_projection_state': {'type': 'string',
                                                           'enum': ['complete',
                                                                    'partial',
                                                                    'invalid']},
                               'outer_acquisition_status': {'type': 'string',
                                                            'enum': ['completed', 'partial']},
                               'native_record_count': {'anyOf': [{'type': 'integer', 'minimum': 0},
                                                                 {'type': 'null'}]},
                               'parser_eligible_record_count': {'type': 'integer', 'minimum': 0},
                               'bound_record_count': {'type': 'integer', 'minimum': 0},
                               'requested_record_count': {'type': 'integer', 'minimum': 0},
                               'returned_bound_record_count': {'type': 'integer', 'minimum': 0},
                               'pagination_metadata_available': {'type': 'boolean'},
                               'next_state': {'type': 'string',
                                              'enum': ['present',
                                                       'absent',
                                                       'unknown',
                                                       'invalid',
                                                       'not_applicable']},
                               'whole_query_complete': {'anyOf': [{'type': 'boolean'},
                                                                  {'type': 'null'}]},
                               'request_verification': {'type': 'string',
                                                        'enum': ['caller_supplied', 'unknown']},
                               'unselected_issue_count': {'type': 'integer', 'minimum': 0},
                               'record_selection_count': {'type': 'integer', 'minimum': 0},
                               'indeterminate_record_count': {'type': 'integer', 'minimum': 0}},
                'required': ['operation',
                             'selection_extent',
                             'response_body_state',
                             'parser_projection_state',
                             'outer_acquisition_status',
                             'native_record_count',
                             'parser_eligible_record_count',
                             'bound_record_count',
                             'requested_record_count',
                             'returned_bound_record_count',
                             'pagination_metadata_available',
                             'next_state',
                             'whole_query_complete',
                             'request_verification',
                             'unselected_issue_count',
                             'record_selection_count',
                             'indeterminate_record_count'],
                'additionalProperties': False},
 'PageReply': {'type': 'object',
               'properties': {'page_selection_index': {'type': 'integer', 'minimum': 0},
                              'witness': {'$ref': '#/$defs/PageWitness'},
                              'status': {'$ref': '#/$defs/PageStatus'},
                              'page_fields': {'type': 'array',
                                              'items': {'$ref': '#/$defs/PageFieldReply'}},
                              'records': {'type': 'array',
                                          'items': {'$ref': '#/$defs/RecordReply'}},
                              'issues': {'type': 'array', 'items': {'$ref': '#/$defs/Issue'}},
                              'source_grant_status': {'$ref': '#/$defs/GrantStatus'},
                              'source_grant': {'anyOf': [{'$ref': '#/$defs/SourceGrant'},
                                                         {'type': 'null'}]},
                              'failures': {'type': 'array', 'items': {'$ref': '#/$defs/Failure'}}},
               'required': ['page_selection_index',
                            'witness',
                            'status',
                            'page_fields',
                            'records',
                            'issues',
                            'source_grant_status',
                            'source_grant',
                            'failures'],
               'additionalProperties': False},
 'TextRange': {'type': 'object',
               'properties': {'offset': {'type': 'integer', 'minimum': 0},
                              'limit': {'type': 'integer', 'minimum': 1}},
               'required': ['offset', 'limit'],
               'additionalProperties': False},
 'RecordSelector': {'oneOf': [{'type': 'object',
                               'properties': {'mode': {'type': 'string', 'const': 'ordinal'},
                                              'ordinal': {'type': 'integer', 'minimum': 0}},
                               'required': ['mode', 'ordinal'],
                               'additionalProperties': False},
                              {'type': 'object',
                               'properties': {'mode': {'type': 'string',
                                                       'const': 'all_native_records'}},
                               'required': ['mode'],
                               'additionalProperties': False},
                              {'type': 'object',
                               'properties': {'mode': {'type': 'string',
                                                       'const': 'primary_accession'},
                                              'accession': {'type': 'string',
                                                            'minLength': 1,
                                                            'pattern': '^[^\\s\\x00-\\x1f\\x7f]+$'}},
                               'required': ['mode', 'accession'],
                               'additionalProperties': False}]},
 'FeatureSelector': {'oneOf': [{'type': 'object',
                                'properties': {'mode': {'type': 'string', 'const': 'ordinal'},
                                               'ordinal': {'type': 'integer', 'minimum': 0}},
                                'required': ['mode', 'ordinal'],
                                'additionalProperties': False},
                               {'type': 'object',
                                'properties': {'mode': {'type': 'string', 'const': 'all'}},
                                'required': ['mode'],
                                'additionalProperties': False},
                               {'type': 'object',
                                'properties': {'mode': {'type': 'string',
                                                        'const': 'entry_interval_overlap'},
                                               'start': {'type': 'integer', 'minimum': 0},
                                               'end': {'type': 'integer', 'minimum': 1},
                                               'coordinates': {'type': 'string',
                                                               'const': 'zero_based_half_open'},
                                               'unit': {'type': 'string', 'const': 'aa'}},
                                'required': ['mode', 'start', 'end', 'coordinates', 'unit'],
                                'additionalProperties': False}]},
 'XrefSelector': {'oneOf': [{'type': 'object',
                             'properties': {'mode': {'type': 'string', 'const': 'ordinal'},
                                            'ordinal': {'type': 'integer', 'minimum': 0}},
                             'required': ['mode', 'ordinal'],
                             'additionalProperties': False},
                            {'type': 'object',
                             'properties': {'mode': {'type': 'string', 'const': 'all'}},
                             'required': ['mode'],
                             'additionalProperties': False},
                            {'type': 'object',
                             'properties': {'mode': {'type': 'string', 'const': 'database'},
                                            'database': {'type': 'string',
                                                         'minLength': 1,
                                                         'pattern': '^[^\\s\\x00-\\x1f\\x7f]+$'}},
                             'required': ['mode', 'database'],
                             'additionalProperties': False}]},
 'EvidenceSelector': {'oneOf': [{'type': 'object',
                                 'properties': {'mode': {'type': 'string',
                                                         'const': 'owner_ordinal'},
                                                'owner_pointer': {'$ref': '#/$defs/Pointer'},
                                                'ordinal': {'type': 'integer', 'minimum': 0}},
                                 'required': ['mode', 'owner_pointer', 'ordinal'],
                                 'additionalProperties': False},
                                {'type': 'object',
                                 'properties': {'mode': {'type': 'string', 'const': 'all_at_owner'},
                                                'owner_pointer': {'$ref': '#/$defs/Pointer'}},
                                 'required': ['mode', 'owner_pointer'],
                                 'additionalProperties': False},
                                {'type': 'object',
                                 'properties': {'mode': {'type': 'string', 'const': 'all_record'}},
                                 'required': ['mode'],
                                 'additionalProperties': False}]},
 'XrefPropertyRequest': {'type': 'object',
                         'properties': {'key': {'type': 'string', 'minLength': 1},
                                        'window': {'$ref': '#/$defs/TextRange'}},
                         'required': ['key', 'window'],
                         'additionalProperties': False},
 'EvidenceCollection': {'type': 'object',
                        'properties': {'native_state': {'$ref': '#/$defs/NativeState'},
                                       'native_member_count': {'anyOf': [{'type': 'integer',
                                                                          'minimum': 0},
                                                                         {'type': 'null'}]},
                                       'matching_member_count': {'type': 'integer', 'minimum': 0},
                                       'indeterminate_member_count': {'type': 'integer',
                                                                      'minimum': 0},
                                       'unavailable_member_count': {'type': 'integer',
                                                                    'minimum': 0},
                                       'excluded_member_count': {'type': 'integer', 'minimum': 0},
                                       'members': {'type': 'array',
                                                   'items': {'type': 'object',
                                                             'properties': {'ordinal': {'type': 'integer',
                                                                                        'minimum': 0},
                                                                            'pointer': {'$ref': '#/$defs/Pointer'},
                                                                            'selection_state': {'type': 'string',
                                                                                                'enum': ['matched',
                                                                                                         'indeterminate',
                                                                                                         'unavailable']},
                                                                            'value': {'anyOf': [{'$ref': '#/$defs/EvidenceValue'},
                                                                                                {'type': 'null'}]},
                                                                            'failures': {'type': 'array',
                                                                                         'items': {'$ref': '#/$defs/Failure'}}},
                                                             'required': ['ordinal',
                                                                          'pointer',
                                                                          'selection_state',
                                                                          'value',
                                                                          'failures'],
                                                             'additionalProperties': False}}},
                        'required': ['native_state',
                                     'native_member_count',
                                     'matching_member_count',
                                     'indeterminate_member_count',
                                     'unavailable_member_count',
                                     'excluded_member_count',
                                     'members'],
                        'additionalProperties': False},
 'XrefPropertyMatch': {'type': 'object',
                       'properties': {'ordinal': {'type': 'integer', 'minimum': 0},
                                      'pointer': {'$ref': '#/$defs/Pointer'},
                                      'value': {'$ref': '#/$defs/TextWindow'}},
                       'required': ['ordinal', 'pointer', 'value'],
                       'additionalProperties': False},
 'XrefPropertyReply': {'type': 'object',
                       'properties': {'request_index': {'type': 'integer', 'minimum': 0},
                                      'request': {'$ref': '#/$defs/XrefPropertyRequest'},
                                      'native_state': {'$ref': '#/$defs/NativeState'},
                                      'matches': {'type': 'array',
                                                  'items': {'$ref': '#/$defs/XrefPropertyMatch'}},
                                      'indeterminate_property_count': {'type': 'integer',
                                                                       'minimum': 0},
                                      'failures': {'type': 'array',
                                                   'items': {'$ref': '#/$defs/Failure'}}},
                       'required': ['request_index',
                                    'request',
                                    'native_state',
                                    'matches',
                                    'indeterminate_property_count',
                                    'failures'],
                       'additionalProperties': False},
 'FeatureCollection': {'type': 'object',
                       'properties': {'native_state': {'$ref': '#/$defs/NativeState'},
                                      'native_member_count': {'anyOf': [{'type': 'integer',
                                                                         'minimum': 0},
                                                                        {'type': 'null'}]},
                                      'matching_member_count': {'type': 'integer', 'minimum': 0},
                                      'indeterminate_member_count': {'type': 'integer',
                                                                     'minimum': 0},
                                      'unavailable_member_count': {'type': 'integer', 'minimum': 0},
                                      'excluded_member_count': {'type': 'integer', 'minimum': 0},
                                      'members': {'type': 'array',
                                                  'items': {'type': 'object',
                                                            'properties': {'ordinal': {'type': 'integer',
                                                                                       'minimum': 0},
                                                                           'pointer': {'$ref': '#/$defs/Pointer'},
                                                                           'selection_state': {'type': 'string',
                                                                                               'enum': ['matched',
                                                                                                        'indeterminate',
                                                                                                        'unavailable']},
                                                                           'value': {'anyOf': [{'$ref': '#/$defs/FeatureLocationValue'},
                                                                                               {'type': 'null'}]},
                                                                           'failures': {'type': 'array',
                                                                                        'items': {'$ref': '#/$defs/Failure'}}},
                                                            'required': ['ordinal',
                                                                         'pointer',
                                                                         'selection_state',
                                                                         'value',
                                                                         'failures'],
                                                            'additionalProperties': False}}},
                       'required': ['native_state',
                                    'native_member_count',
                                    'matching_member_count',
                                    'indeterminate_member_count',
                                    'unavailable_member_count',
                                    'excluded_member_count',
                                    'members'],
                       'additionalProperties': False},
 'XrefCollection': {'type': 'object',
                    'properties': {'native_state': {'$ref': '#/$defs/NativeState'},
                                   'native_member_count': {'anyOf': [{'type': 'integer',
                                                                      'minimum': 0},
                                                                     {'type': 'null'}]},
                                   'matching_member_count': {'type': 'integer', 'minimum': 0},
                                   'indeterminate_member_count': {'type': 'integer', 'minimum': 0},
                                   'unavailable_member_count': {'type': 'integer', 'minimum': 0},
                                   'excluded_member_count': {'type': 'integer', 'minimum': 0},
                                   'members': {'type': 'array',
                                               'items': {'type': 'object',
                                                         'properties': {'ordinal': {'type': 'integer',
                                                                                    'minimum': 0},
                                                                        'pointer': {'$ref': '#/$defs/Pointer'},
                                                                        'selection_state': {'type': 'string',
                                                                                            'enum': ['matched',
                                                                                                     'indeterminate',
                                                                                                     'unavailable']},
                                                                        'value': {'anyOf': [{'$ref': '#/$defs/CrossReferenceValue'},
                                                                                            {'type': 'null'}]},
                                                                        'failures': {'type': 'array',
                                                                                     'items': {'$ref': '#/$defs/Failure'}}},
                                                         'required': ['ordinal',
                                                                      'pointer',
                                                                      'selection_state',
                                                                      'value',
                                                                      'failures'],
                                                         'additionalProperties': False}}},
                    'required': ['native_state',
                                 'native_member_count',
                                 'matching_member_count',
                                 'indeterminate_member_count',
                                 'unavailable_member_count',
                                 'excluded_member_count',
                                 'members'],
                    'additionalProperties': False}}

_RETURN_ROOT = {'type': 'object',
 'properties': {'version': {'type': 'string', 'const': 'uniprot_selected_returns_v1'},
                'pages': {'type': 'array', 'items': {'$ref': '#/$defs/PageReply'}},
                'failures': {'type': 'array', 'items': {'$ref': '#/$defs/Failure'}}},
 'required': ['version', 'pages', 'failures'],
 'additionalProperties': False,
 'x-source': 'uniprot_selected_returns'}


class UniProtReturnValidationError(ValueError):
    """Declared boundary code with a separate, exact local field path."""

    def __init__(self, code, field=None):
        self.code, self.field = code, field
        super().__init__(code)


def _require(condition, field, code="uniprot_selected_value_conflict"):
    if not condition:
        raise UniProtReturnValidationError(code, field)


def _copy_json(value, *, field, code):
    kind = type(value)
    if value is None or kind in (str, bool, int):
        return value
    if kind is float and math.isfinite(value):
        return value
    if kind is list:
        return [_copy_json(v, field=f"{field}[{i}]", code=code) for i, v in enumerate(value)]
    if kind is dict and all(type(k) is str for k in value):
        return {k: _copy_json(v, field=f"{field}.{k}", code=code) for k, v in value.items()}
    raise UniProtReturnValidationError(code, field)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _full_pattern(validator, pattern, instance, schema):
    # All frozen patterns are anchored. Python's `$` also matches just before
    # a final newline; a typed token, digest or host ID must consume its value.
    if type(instance) is str and re.fullmatch(pattern, instance) is None:
        yield ValidationError("Value does not match the complete declared pattern")


# JSON Schema normally accepts 1.0 as an integer; this contract does not.
_StrictValidator = validators.extend(Draft202012Validator, validators={"pattern": _full_pattern}, type_checker=
    Draft202012Validator.TYPE_CHECKER.redefine_many({
        "integer": lambda _, value: type(value) is int,
        "number": lambda _, value: type(value) in (int, float) and math.isfinite(value),
        "object": lambda _, value: type(value) is dict,
        "array": lambda _, value: type(value) is list,
    }))


def uniprot_return_selection_schema() -> dict:
    """Return the exact detached internal selection schema, including its defs."""
    return {"$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": "#/$defs/Selection", "$defs": deepcopy(_DEFINITIONS)}


_SELECTION_VALIDATOR = _StrictValidator(uniprot_return_selection_schema())
_INDEX = r"(?:0|[1-9][0-9]*)"
_COMPONENT = rf"(?:/(?:contains|includes)/{_INDEX})*"
_NAME_GROUP = rf"/proteinDescription{_COMPONENT}/(?:recommendedName|alternativeNames/{_INDEX}|submissionNames/{_INDEX})"
_EC_POINTER = re.compile(rf"({_NAME_GROUP})/ecNumbers/({_INDEX})/value\Z")
_TEXT_POINTERS = {
    "protein_name": rf"{_NAME_GROUP}/(?:fullName|shortNames/{_INDEX})/value",
    "gene_name": rf"/genes/{_INDEX}/(?:geneName|(?:synonyms|orderedLocusNames|orfNames)/{_INDEX})/value",
    "entry_type": r"/entryType",
    "protein_existence": r"/proteinExistence",
    "entry_date": r"/entryAudit/(?:firstPublicDate|lastAnnotationUpdateDate|lastSequenceUpdateDate)",
    "taxon_name": r"/organism/(?:scientificName|commonName)",
    "taxon_synonym": rf"/organism/synonyms/{_INDEX}",
    "taxon_lineage_name": rf"/organism/lineage/{_INDEX}",
    "feature_type": rf"/features/{_INDEX}/type",
    "feature_description": rf"/features/{_INDEX}/description",
    "xref_property_key": rf"/uniProtKBCrossReferences/{_INDEX}/properties/{_INDEX}/key",
    "xref_property_value": rf"/uniProtKBCrossReferences/{_INDEX}/properties/{_INDEX}/value",
    "comment_text": rf"/comments/{_INDEX}/(?:[^/]+/)*[^/]+",
}


def _schema_check(value, validator, field, code):
    error = next(validator.iter_errors(value), None)
    if error is not None:
        for part in error.absolute_path:
            field += f"[{part}]" if type(part) is int else "." + part
        raise UniProtReturnValidationError(code, field) from error


def _unique(values, field, *, selector=None):
    seen = set()
    for index, value in enumerate(values):
        key = _canonical(value if selector is None else value[selector])
        _require(key not in seen, f"{field}[{index}]", "uniprot_selection_duplicate")
        seen.add(key)


def _selection_intervals(value, field):
    if type(value) is dict:
        if "offset" in value or "limit" in value:
            _require(type(value.get("offset")) is int and value["offset"] >= 0
                     and type(value.get("limit")) is int and value["limit"] > 0,
                     field, "uniprot_selection_interval_invalid")
        if value.get("kind") == "sequence_window" or value.get("mode") == "entry_interval_overlap":
            _require(type(value.get("start")) is int and type(value.get("end")) is int
                     and 0 <= value["start"] < value["end"], field,
                     "uniprot_selection_interval_invalid")
        for key, child in value.items():
            _selection_intervals(child, field + "." + key)
    elif type(value) is list:
        for index, child in enumerate(value):
            _selection_intervals(child, f"{field}[{index}]")


def validate_uniprot_return_selection(selection: dict) -> dict:
    """Check the parent's explicit selection; return an unchanged JSON copy."""
    selection = _copy_json(selection, field="selection", code="uniprot_selection_invalid")
    _selection_intervals(selection, "selection")
    _schema_check(selection, _SELECTION_VALIDATOR, "selection", "uniprot_selection_invalid")
    _unique(selection["pages"], "selection.pages", selector="publication")
    modes = {page["publication"]["mode"] for page in selection["pages"]}
    _require(len(modes) <= 1, "selection.pages", "uniprot_selection_mode_conflict")
    for pi, page in enumerate(selection["pages"]):
        pp = f"selection.pages[{pi}]"
        _unique(page["page_fields"], pp + ".page_fields")
        _unique(page["records"], pp + ".records", selector="record")
        for ri, record in enumerate(page["records"]):
            rp = f"{pp}.records[{ri}].fields"
            _unique(record["fields"], rp)
            for fi, field in enumerate(record["fields"]):
                path, kind = f"{rp}[{fi}]", field["kind"]
                if kind == "token":
                    _require((field["array_ordinal"] is not None) ==
                             (field["field"] == "secondary_accession"), path,
                             "uniprot_selection_invalid")
                elif kind == "text":
                    pointer = field["pointer"]
                    valid = (pointer != "/sequence/value" and not pointer.startswith("/sequence/value/"))
                    if field["field"] != "native_text":
                        valid = re.fullmatch(_TEXT_POINTERS[field["field"]], pointer) is not None
                    _require(valid, path + ".pointer", "uniprot_selection_pointer_conflict")
                elif kind == "ec_assignment":
                    _require(_EC_POINTER.fullmatch(field["pointer"]) is not None,
                             path + ".pointer", "uniprot_selection_pointer_conflict")
                elif kind == "cross_reference":
                    _unique(field["properties"], path + ".properties")
    return selection


def _text_limit(value):
    if type(value) is dict:
        own = value.get("limit", 0) if "offset" in value else 0
        return max([own, *(_text_limit(child) for child in value.values())])
    if type(value) is list:
        return max([0, *(_text_limit(child) for child in value)])
    return 0


def _expand(value, text_limit):
    if type(value) is list:
        return [_expand(child, text_limit) for child in value]
    if type(value) is not dict:
        return value
    if "$ref" in value:
        name = value["$ref"].removeprefix("#/$defs/")
        expanded = _expand(_DEFINITIONS[name], text_limit)
        if name == "TextWindow":
            expanded["properties"]["text"]["anyOf"][0]["maxLength"] = text_limit
        return expanded
    return {key: _expand(child, text_limit) for key, child in value.items()
            if key not in {"$schema", "$defs"}}


def uniprot_selected_return_schema(selection: dict) -> dict:
    """Build the one exact fully inlined field schema for this selection."""
    selection = validate_uniprot_return_selection(selection)
    schema = _expand(_RETURN_ROOT, _text_limit(selection))
    schema["x-uniprot-selection"] = selection
    return schema


def uniprot_fact_sources() -> dict:
    return {SOURCE: {"type": "object",
        "meaning": "Exactly requested UniProt source facts and explicit material grants.",
        "report_schema": uniprot_selected_return_schema({"version": _SELECTION_VERSION, "pages": []})}}


def requested_uniprot_selection(schema: dict) -> dict | None:
    """Recover an exact registration only from whole top-level properties."""
    if not isinstance(schema, dict) or not isinstance(schema.get("properties"), dict):
        return None
    selected = [(name, node) for name, node in schema["properties"].items()
                if isinstance(node, dict) and node.get("x-source") == SOURCE]
    _require(len(selected) <= 1, "properties", "uniprot_selection_duplicate")
    if not selected:
        return None
    name, node = selected[0]
    path = "properties." + name
    node = _copy_json(node, field=path, code="uniprot_original_schema_conflict")
    selection = validate_uniprot_return_selection(node.get("x-uniprot-selection"))
    _require(_canonical(node) == _canonical(uniprot_selected_return_schema(selection)),
             path, "uniprot_original_schema_conflict")
    return selection


def _owner(condition, field):
    _require(condition, field, "uniprot_selected_owner_conflict")


def _within(pointer, owner):
    return pointer == owner or pointer.startswith(owner + "/")


def _token(value, field, *, pointer=None, pattern=None):
    if pointer is not None:
        _owner(value["pointer"] == pointer, field + ".pointer")
    exact = value["representation"] == "exact"
    _require((value["value"] is not None) == exact, field)
    if exact:
        _require(value["native_state"] == "present", field)
        if pattern is not None:
            _require(re.fullmatch(pattern, value["value"]) is not None, field + ".value")


def _integer(value, field, *, pointer, unit, origin="native"):
    _owner(value["pointer"] == pointer, field + ".pointer")
    _require(value["unit"] == unit and value["origin"] == origin, field)
    _require((value["value"] is not None) == (value["native_state"] == "present"), field)
    if unit in {"version", "taxon_id"} and value["value"] is not None:
        _require(value["value"] > 0, field + ".value")


def _text(value, requested, field, *, pointer):
    _owner(value["pointer"] == pointer and value["owner_pointer"] == pointer.rsplit("/", 1)[0], field)
    _require(value["offset"] == requested["offset"] and value["limit"] == requested["limit"], field)
    quantities = ("native_length", "start", "end", "omitted_prefix", "omitted_suffix")
    if value["native_state"] != "present":
        _require(value["text"] is None and value["extent"] == "unavailable"
                 and all(value[key] is None for key in quantities), field)
        return
    _require(value["text"] is not None and all(value[key] is not None for key in quantities), field)
    n, o, limit = value["native_length"], value["offset"], value["limit"]
    start, end = min(o, n), min(o + limit, n)
    extent = ("offset_past_end" if o > n else "empty_value" if n == 0 and o == 0
              else "whole_value" if start == 0 and end == n else "window")
    _require((value["start"], value["end"], value["omitted_prefix"], value["omitted_suffix"],
              value["extent"], len(value["text"])) == (start, end, start, n - end, extent, end - start), field)


def _incomplete(value):
    """Requested absence/partiality propagates, without promoting qualifications."""
    if type(value) is list:
        return any(_incomplete(child) for child in value)
    if type(value) is not dict:
        return False
    if value.get("failures"):
        return True
    if value.get("representation") == "unavailable":
        return True
    if "native_state" in value and value["native_state"] != "present":
        # An absent optional feature sequence ID describes the entry sequence.
        return True
    if value.get("selection_state") in {"indeterminate", "unavailable"}:
        return True
    return any(_incomplete(child) for key, child in value.items()
               if key != "request" and not (key == "native_sequence_id"
                   and isinstance(child, dict) and child.get("native_state") == "absent"))


def _reply_status(reply, field):
    if reply["status"] == "unavailable":
        _require(reply["value"] is None and bool(reply["failures"]), field)
    else:
        _require(reply["value"] is not None, field)
        incomplete = bool(reply["failures"]) or _incomplete(reply["value"])
        _require(reply["status"] == ("partial" if incomplete else "available"), field + ".status")


def _failure_indices(value, selection, field="value", *, expected=None):
    if type(value) is dict:
        if set(value) == set(_DEFINITIONS["Failure"]["properties"]):
            pi, ri, fi = (value[key] for key in
                          ("page_selection_index", "record_selection_index", "field_selection_index"))
            _require(pi < len(selection["pages"]), field)
            page = selection["pages"][pi]
            _require(ri is None or ri < len(page["records"]), field)
            fields = page["page_fields"] if ri is None else page["records"][ri]["fields"]
            _require(fi is None or fi < len(fields), field)
            if expected is not None:
                _owner((pi, ri, fi) == expected, field)
            return
        for key, child in value.items():
            _failure_indices(child, selection, field + "." + key, expected=expected)
    elif type(value) is list:
        for index, child in enumerate(value):
            _failure_indices(child, selection, f"{field}[{index}]", expected=expected)


def _collection(value, selector, field, *, family, record_pointer, owner=None, request=None):
    count, state, members = value["native_member_count"], value["native_state"], value["members"]
    keys = {"matched": "matching_member_count", "indeterminate": "indeterminate_member_count",
            "unavailable": "unavailable_member_count"}
    for membership, key in keys.items():
        _require(value[key] == sum(member["selection_state"] == membership for member in members), field + "." + key)
    if count is not None:
        _require(sum(value[key] for key in (*keys.values(), "excluded_member_count")) == count, field)
    if state == "absent":
        _require(count == 0 and not members and value["excluded_member_count"] == 0, field)
    elif state in {"null", "invalid"}:
        _require(count is None and not members and value["excluded_member_count"] == 0, field)
    if selector["mode"] in {"all", "all_record", "all_at_owner"}:
        _require(value["excluded_member_count"] == 0, field)
    seen, previous, owner_ordinals = set(), -1, {}
    for mi, member in enumerate(members):
        mp = f"{field}.members[{mi}]"
        ordinal, pointer, cell = member["ordinal"], member["pointer"], member["value"]
        if selector["mode"] not in {"entry_interval_overlap", "database"}:
            _require(member["selection_state"] != "indeterminate", mp + ".selection_state")
        _owner(pointer not in seen and _within(pointer, record_pointer), mp)
        seen.add(pointer)
        if selector["mode"] in {"ordinal", "owner_ordinal"}:
            _owner(ordinal == selector["ordinal"], mp + ".ordinal")
        if count is not None:
            _owner(ordinal < count, mp + ".ordinal")
        if family != "evidence":
            _owner(ordinal > previous, mp + ".ordinal")
            previous = ordinal
            prefix = "/features/" if family == "feature_location" else "/uniProtKBCrossReferences/"
            _owner(pointer == record_pointer + prefix + str(ordinal), mp + ".pointer")
        if member["selection_state"] == "unavailable":
            _require(cell is None and bool(member["failures"]), mp)
        elif member["selection_state"] == "matched":
            _require(cell is not None, mp)
        else:
            _require(bool(member["failures"]) or cell is not None, mp)
        if family == "evidence":
            suffix = "/evidences/" + str(ordinal)
            _owner(pointer.endswith(suffix), mp + ".pointer")
            actual_owner = pointer[:-len(suffix)]
            if owner is not None:
                _owner(_within(actual_owner, owner), mp)
            if selector["mode"] in {"owner_ordinal", "all_at_owner"}:
                _owner(actual_owner == record_pointer + selector["owner_pointer"], mp)
            _owner(ordinal > owner_ordinals.get(actual_owner, -1), mp + ".ordinal")
            owner_ordinals[actual_owner] = ordinal
            if cell is not None:
                _owner(cell["ordinal"] == ordinal and cell["pointer"] == pointer
                       and cell["owner_pointer"] == actual_owner, mp)
                for key, native, pattern in (("eco", "evidenceCode", r"ECO:[0-9]{7}"),
                                              ("source", "source", None), ("source_identifier", "id", None)):
                    _token(cell[key], mp + ".value." + key, pointer=pointer + "/" + native, pattern=pattern)
        elif cell is not None:
            _owner(cell["ordinal"] == ordinal and cell["pointer"] == pointer, mp)
            if family == "feature_location":
                _feature(cell, request, mp + ".value", member["selection_state"], record_pointer)
            else:
                _xref(cell, request, mp + ".value", member["selection_state"], record_pointer)
        elif selector["mode"] in {"entry_interval_overlap", "database"}:
            _require(member["selection_state"] == "indeterminate", mp)


def _feature(value, request, field, membership, record_pointer):
    pointer = value["pointer"]
    for key in ("start", "end"):
        position = value[key]
        _owner(position["value_pointer"] == pointer + "/location/" + key + "/value", field + "." + key)
        _require((position["value"] is not None) == (position["value_state"] == "present"), field + "." + key)
        if position["value"] is not None:
            _require(position["value"] > 0, field + "." + key)
        if position["native_state"] != "present":
            _require(position["value_state"] == "absent" and position["modifier"]["native_state"] == "absent", field + "." + key)
        _token(position["modifier"], field + "." + key + ".modifier",
               pointer=pointer + "/location/" + key + "/modifier")
    _token(value["native_sequence_id"], field + ".native_sequence_id", pointer=pointer + "/location/sequence")
    interval = value["exact_interval"]
    if interval is not None:
        start, end = value["start"], value["end"]
        _require(value["sequence_binding"] == "entry_sequence"
                 and start["modifier"]["value"] == end["modifier"]["value"] == "EXACT"
                 and start["value"] is not None and end["value"] is not None
                 and 0 < start["value"] <= end["value"]
                 and interval == [start["value"] - 1, end["value"]], field + ".exact_interval")
    selected = request["selection"]
    if selected["mode"] == "entry_interval_overlap":
        _require(value["sequence_binding"] != "explicit_other_sequence", field)
        if interval is not None:
            _require(interval[0] < selected["end"] and interval[1] > selected["start"]
                     and membership == "matched", field)
        else:
            _require(membership == "indeterminate", field)
    for key, native in (("type_window", "type"), ("description_window", "description")):
        _require((value[key] is None) == (request[key] is None), field + "." + key)
        if value[key] is not None:
            _text(value[key], request[key], field + "." + key, pointer=pointer + "/" + native)
    _require((value["evidence"] is not None) == request["include_evidence"], field + ".evidence")
    if value["evidence"] is not None:
        _collection(value["evidence"], {"mode": "all_record"}, field + ".evidence",
                    family="evidence", record_pointer=record_pointer, owner=pointer)


def _xref(value, request, field, membership, record_pointer):
    pointer = value["pointer"]
    _token(value["database"], field + ".database", pointer=pointer + "/database")
    _token(value["identifier"], field + ".identifier", pointer=pointer + "/id")
    if request["selection"]["mode"] == "database":
        database = value["database"]
        if database["representation"] == "exact":
            _require(database["value"] == request["selection"]["database"] and membership == "matched", field)
        else:
            _require(membership == "indeterminate", field)
    _require((value["evidence"] is not None) == request["include_evidence"], field + ".evidence")
    if value["evidence"] is not None:
        _collection(value["evidence"], {"mode": "all_record"}, field + ".evidence",
                    family="evidence", record_pointer=record_pointer, owner=pointer)
    _require(len(value["properties"]) == len(request["properties"]), field + ".properties")
    for index, (reply, selected) in enumerate(zip(value["properties"], request["properties"])):
        pp = f"{field}.properties[{index}]"
        _owner(reply["request_index"] == index and _canonical(reply["request"]) == _canonical(selected), pp)
        _require(reply["native_state"] == value["properties_state"], pp)
        if reply["native_state"] != "present":
            _require(not reply["matches"] and reply["indeterminate_property_count"] == 0, pp)
        previous = -1
        for match in reply["matches"]:
            ordinal = match["ordinal"]
            expected = pointer + "/properties/" + str(ordinal)
            _owner(ordinal > previous and match["pointer"] == expected, pp)
            previous = ordinal
            _text(match["value"], selected["window"], pp + ".value", pointer=expected + "/value")


_INTEGER_FIELDS = {
    "taxon_id": ("/organism/taxonId", "taxon_id", "native"),
    "entry_version": ("/entryAudit/entryVersion", "version", "native"),
    "sequence_version": ("/entryAudit/sequenceVersion", "version", "native"),
    "reported_sequence_length": ("/sequence/length", "aa", "native"),
    "observed_sequence_length": ("/sequence/value", "aa", "derived"),
}
_TOKEN_FIELDS = {"primary_accession": "/primaryAccession", "uniprot_id": "/uniProtkbId",
                 "sequence_md5": "/sequence/md5", "sequence_crc64": "/sequence/crc64"}
_PAGE_POINTERS = {"total_results": "/headers/x-total-results", "release": "/headers/x-uniprot-release",
                  "release_date": "/headers/x-uniprot-release-date", "next_cursor": "/headers/link",
                  "next_url": "/headers/link", "effective_query": "/effective_request/query"}


def _field(reply, request, index, field, *, record_pointer=None):
    _owner(reply["request_index"] == index and _canonical(reply["request"]) == _canonical(request), field)
    _reply_status(reply, field)
    value, kind = reply["value"], request["kind"]
    if value is None:
        return
    if kind == "integer":
        pointer, unit, origin = _INTEGER_FIELDS[request["field"]]
        _integer(value, field + ".value", pointer=record_pointer + pointer, unit=unit, origin=origin)
    elif kind == "token":
        pointer = (_TOKEN_FIELDS[request["field"]] if request["field"] != "secondary_accession"
                   else "/secondaryAccessions/" + str(request["array_ordinal"]))
        _token(value, field + ".value", pointer=record_pointer + pointer)
    elif kind == "text":
        _text(value, request, field + ".value", pointer=record_pointer + request["pointer"])
    elif kind == "ec_assignment":
        pointer = record_pointer + request["pointer"]
        match = _EC_POINTER.fullmatch(request["pointer"])
        name_group = record_pointer + match[1]
        component = re.match(rf"/proteinDescription({_COMPONENT})/", request["pointer"])[1]
        component_pointer = record_pointer + "/proteinDescription" + component if component else None
        _owner(value["pointer"] == pointer and value["owner_pointer"] == pointer.rsplit("/", 1)[0]
               and value["name_group_pointer"] == name_group and value["component_pointer"] == component_pointer, field)
        _require(value["scope"] == ("component" if component else "entry"), field)
        _token(value["ec"], field + ".value.ec", pointer=pointer, pattern=r"(?:[0-9]+|n[0-9]+|-)(?:\.(?:[0-9]+|n[0-9]+|-)){3}")
    elif kind in {"feature_location", "evidence", "cross_reference"}:
        _collection(value, request["selection"], field + ".value", family=kind,
                    record_pointer=record_pointer, request=request)
        selected = request["selection"]
        count = value["native_member_count"]
        if (selected["mode"] in {"ordinal", "owner_ordinal"}
                and value["native_state"] == "present" and count is not None):
            available = selected["ordinal"] < count
            _require(len(value["members"]) == int(available), field + ".value.members")
            if not available:
                _require(any(failure["code"] == "selected_ordinal_unavailable" for failure in reply["failures"]),
                         field + ".failures")
    elif kind == "sequence_window":
        _require(value["start"] == request["start"] and value["end"] == request["end"]
                 and 0 <= value["start"] < value["end"] <= value["sequence_length"]
                 and len(value["value"]) == value["end"] - value["start"], field)
        _require((value["reported_length"] is not None) == (value["reported_length_state"] == "present"), field)
        relation = ("unavailable" if value["reported_length"] is None else
                    "agree" if value["reported_length"] == value["sequence_length"] else "conflict")
        _require(value["length_relation"] == relation, field)
    elif kind == "page_integer":
        _integer(value, field + ".value", pointer=_PAGE_POINTERS[request["field"]], unit="count")
    elif kind == "page_token":
        _token(value, field + ".value", pointer=_PAGE_POINTERS[request["field"]])
    elif kind == "page_text":
        _text(value, request, field + ".value", pointer=_PAGE_POINTERS[request["field"]])


def _grant(status, grant, requested, failures, field):
    if not requested:
        _require(status == "not_requested" and grant is None, field)
    else:
        _require(status in {"available", "unavailable"}, field)
        _require((grant is not None) == (status == "available"), field)
        if status == "unavailable":
            _require(bool(failures), field)


def _issues(issues, field, *, ordinal, pointer=None):
    seen = set()
    for index, issue in enumerate(issues):
        path = f"{field}[{index}]"
        _owner(issue["record_ordinal"] == ordinal, path)
        if pointer is not None:
            _owner(_within(issue["pointer"], pointer), path + ".pointer")
        identity = (issue["origin"], issue["original_issue_index"])
        _owner(identity not in seen, path)
        seen.add(identity)


def _record(reply, selected, field, *, page, selection):
    ordinal = reply["requested_record_ordinal"]
    record = selected["record"]
    if record["mode"] == "ordinal":
        _owner(ordinal == record["ordinal"], field + ".requested_record_ordinal")
    status = page["status"]
    n = status["native_record_count"]
    witness = reply["witness"]
    _require((witness is not None) == (reply["state"] == "bound"), field + ".witness")
    pointer = "" if status["operation"] == "record" else "/results/" + str(ordinal)
    if witness is not None:
        _owner(witness["record_ordinal"] == ordinal and witness["record_pointer"] == pointer, field + ".witness")
        _owner(n is not None and ordinal < n, field + ".witness")
        if status["operation"] == "record":
            _owner(ordinal == 0, field)
    if reply["state"] == "not_in_response":
        _require(n is not None and ordinal >= n, field + ".state")
    elif reply["state"] in {"parser_unpublishable", "binding_omitted"}:
        _require(n is not None and ordinal < n, field + ".state")
    if reply["state"] != "bound":
        _require(bool(reply["failures"]), field + ".failures")
        codes = {failure["code"] for failure in reply["failures"]}
        required = {"not_in_response": "record_not_in_response", "parser_unpublishable": "record_parser_unpublishable",
                    "binding_omitted": "record_binding_omitted"}.get(reply["state"])
        _require(required is None or required in codes, field + ".failures")
    _require(len(reply["fields"]) == len(selected["fields"]), field + ".fields")
    lengths, digests, reported, windows = set(), set(), set(), []
    for fi, (cell, request) in enumerate(zip(reply["fields"], selected["fields"])):
        fp = f"{field}.fields[{fi}]"
        _failure_indices(cell, selection, fp, expected=(page["page_selection_index"], reply["record_selection_index"], fi))
        if witness is None:
            _require(cell["status"] == "unavailable" and cell["value"] is None, fp)
        _field(cell, request, fi, fp, record_pointer=pointer)
        value = cell["value"]
        if value is not None and request["kind"] == "sequence_window":
            lengths.add(value["sequence_length"])
            digests.add(value["sequence_sha256"])
            for previous in windows:
                left, right = max(previous["start"], value["start"]), min(previous["end"], value["end"])
                if left < right:
                    _require(previous["value"][left - previous["start"]:right - previous["start"]]
                             == value["value"][left - value["start"]:right - value["start"]], fp)
            windows.append(value)
            if value["reported_length"] is not None:
                reported.add(value["reported_length"])
        if (value is not None and request["kind"] == "token" and request["field"] == "primary_accession"
                and record["mode"] == "primary_accession" and value["representation"] == "exact"):
            _require(value["value"] == record["accession"], fp)
        if value is not None and request["kind"] == "integer" and value["value"] is not None:
            if request["field"] == "observed_sequence_length":
                lengths.add(value["value"])
            elif request["field"] == "reported_sequence_length":
                reported.add(value["value"])
    _grant(reply["sequence_grant_status"], reply["sequence_grant"], selected["grant_sequence_artifact"],
           reply["failures"], field + ".sequence_grant")
    grant = reply["sequence_grant"]
    if grant is not None:
        _owner(witness is not None and grant["artifact_ref"] == witness["sequence_artifact_id"]
               and grant["record_id"] == witness["record_id"] and grant["record_ordinal"] == ordinal,
               field + ".sequence_grant")
        lengths.add(grant["length"])
        digests.add(grant["sequence_sha256"])
    _require(len(lengths) <= 1 and len(digests) <= 1 and len(reported) <= 1, field)
    if lengths:
        length = next(iter(lengths))
        for cell in reply["fields"]:
            if cell["value"] is None or cell["request"]["kind"] != "feature_location":
                continue
            request = cell["request"]["selection"]
            if request["mode"] == "entry_interval_overlap":
                _require(request["end"] <= length, field + ".fields")
            for member in cell["value"]["members"]:
                feature = member["value"]
                if feature is not None and feature["exact_interval"] is not None:
                    _require(feature["exact_interval"][1] <= length, field + ".fields")
    _issues(reply["issues"], field + ".issues", ordinal=ordinal, pointer=pointer)
    _failure_indices(reply["failures"], selection, field + ".failures",
                     expected=(page["page_selection_index"], reply["record_selection_index"], None))


def _page(page, selected, field, *, selection):
    pi, status = page["page_selection_index"], page["status"]
    n, eligible, bound = (status[key] for key in
                          ("native_record_count", "parser_eligible_record_count", "bound_record_count"))
    _require(bound <= eligible and (n is None or eligible <= n), field + ".status")
    _require(status["selection_extent"] == {"record": "one_record", "search": "one_selected_page",
             "unknown": "not_established"}[status["operation"]], field + ".status")
    if n is None:
        _require(eligible == bound == 0, field + ".status")
    if status["response_body_state"] != "complete_json":
        _require(n is None, field + ".status")
    if status["operation"] == "record" and n is not None:
        _require(n <= 1, field + ".status")
    if status["next_state"] == "present":
        _require(status["pagination_metadata_available"] and status["operation"] == "search"
                 and status["whole_query_complete"] is not True, field + ".status")
    if status["whole_query_complete"] is True:
        _require(status["response_body_state"] == "complete_json" and
                 (status["operation"] == "record" or status["pagination_metadata_available"]), field + ".status")
    publication = selected["publication"]
    if publication["mode"] == "received_publication":
        _owner(page["witness"]["source_id"] == publication["source_id"] and
               page["witness"]["publication_sha256"] == publication["publication_sha256"], field + ".witness")
    _require(len(page["page_fields"]) == len(selected["page_fields"]), field + ".page_fields")
    for fi, (cell, request) in enumerate(zip(page["page_fields"], selected["page_fields"])):
        fp = f"{field}.page_fields[{fi}]"
        _field(cell, request, fi, fp)
        _failure_indices(cell, selection, fp, expected=(pi, None, fi))
        if request["field"] in {"next_cursor", "next_url"} and cell["value"] is not None:
            if status["next_state"] in {"present", "absent"}:
                _require(cell["value"]["native_state"] == status["next_state"], fp)
            else:
                _require(cell["status"] != "available", fp)
    _require(status["record_selection_count"] == len(selected["records"]), field + ".status")
    clauses = [[] for _ in selected["records"]]
    order, bound_ordinals, distinct, indeterminate = [], set(), set(), set()
    witnesses = {}
    for ri, reply in enumerate(page["records"]):
        rp = f"{field}.records[{ri}]"
        index, ordinal = reply["record_selection_index"], reply["requested_record_ordinal"]
        _owner(index < len(clauses), rp)
        order.append((index, ordinal))
        clauses[index].append(ordinal)
        distinct.add(ordinal)
        if reply["state"] == "bound":
            bound_ordinals.add(ordinal)
            if ordinal in witnesses:
                _owner(_canonical(witnesses[ordinal]) == _canonical(reply["witness"]), rp + ".witness")
            witnesses[ordinal] = reply["witness"]
        if any(failure["code"] == "record_selection_indeterminate" for failure in reply["failures"]):
            _require(selected["records"][index]["record"]["mode"] == "primary_accession"
                     and reply["state"] == "unavailable" and n is not None and ordinal < n, rp)
            indeterminate.add(ordinal)
        _record(reply, selected["records"][index], rp, page=page, selection=selection)
    _owner(order == sorted(set(order)), field + ".records")
    for index, (ordinals, requested) in enumerate(zip(clauses, selected["records"])):
        record = requested["record"]
        failures = [failure for failure in page["failures"] if failure["record_selection_index"] == index]
        missing_forwarded = any(failure["code"] == "field_not_received" for failure in failures)
        if record["mode"] == "ordinal":
            _require(ordinals == [record["ordinal"]] or (not ordinals and missing_forwarded), field + ".records")
        elif record["mode"] == "all_native_records" and n is not None and not missing_forwarded:
            _require(ordinals == list(range(n)), field + ".records")
        elif record["mode"] == "primary_accession" and not ordinals:
            _require(bool(failures), field + ".failures")
        if any(failure["code"] == "record_selection_no_match" for failure in failures):
            _require(record["mode"] == "primary_accession" and not ordinals and n is not None, field + ".failures")
    _require(status["requested_record_count"] == len(distinct)
             and status["returned_bound_record_count"] == len(bound_ordinals)
             and len(bound_ordinals) <= bound
             and status["indeterminate_record_count"] == len(indeterminate), field + ".status")
    _grant(page["source_grant_status"], page["source_grant"], selected["grant_source"],
           page["failures"], field + ".source_grant")
    grant = page["source_grant"]
    if grant is not None:
        witness = page["witness"]
        _owner(grant["source_ref"] == witness["source_id"]
               and grant["native_artifact_id"] == witness["native_artifact_id"]
               and grant["content_sha256"] == witness["content_sha256"], field + ".source_grant")
    _issues(page["issues"], field + ".issues", ordinal=None)
    for index, failure in enumerate(page["failures"]):
        _owner(failure["page_selection_index"] == pi, f"{field}.failures[{index}]")


def validate_uniprot_selected_values(value: dict, *, selection: dict) -> None:
    """Validate selected facts' shape and relations, without authenticating data."""
    selection = validate_uniprot_return_selection(selection)
    value = _copy_json(value, field="value", code="uniprot_selected_value_conflict")
    _schema_check(value, _StrictValidator(uniprot_selected_return_schema(selection)),
                  "value", "uniprot_selected_value_conflict")
    _failure_indices(value, selection)
    previous, witnessed, represented = -1, set(), set()
    for index, page in enumerate(value["pages"]):
        field = f"value.pages[{index}]"
        pi = page["page_selection_index"]
        _owner(previous <= pi < len(selection["pages"]), field + ".page_selection_index")
        previous = pi
        witness = (page["witness"]["source_id"], page["witness"]["publication_sha256"])
        _owner(witness not in witnessed, field + ".witness")
        witnessed.add(witness)
        represented.add(pi)
        _page(page, selection["pages"][pi], field, selection=selection)
    for failure in value["failures"]:
        _require(failure["record_selection_index"] is None and failure["field_selection_index"] is None,
                 "value.failures")
        represented.add(failure["page_selection_index"])
    _require(represented == set(range(len(selection["pages"]))), "value.pages")


__all__ = ["validate_uniprot_return_selection", "uniprot_selected_return_schema",
           "uniprot_return_selection_schema", "uniprot_fact_sources", "requested_uniprot_selection",
           "validate_uniprot_selected_values", "UniProtReturnValidationError"]
