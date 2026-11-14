"""Closed ion-discrimination source selections and possessed activity rows.

Numeric values come from exact authorized sources or selected saved cells.
Scientific interpretations remain source-witnessed episode decisions.
"""
from copy import deepcopy
from fractions import Fraction
import json
import math
from .domain import identity, validate_schema
from .literature_assay_inputs import _Sources, _interpretation
from .literature_compiled_assay_storage import compiled_assay_cells_schema
from .literature_experimental_contracts import ExperimentalContractError
from .literature_ion_discrimination_numbers import read_ion_number, read_ion_unit, check_explicit_unit, rational

VERSION = 'a105_ion_discrimination_extraction_v1'
ROLES = ('preferred', 'alternative')

_SELECTION_SCHEMA = {'$schema': 'https://json-schema.org/draft/2020-12/schema',
 'oneOf': [{'type': 'object',
            'properties': {'route': {'const': 'compiled_activity_pair'},
                           'activities': {'type': 'object',
                                          'properties': {'preferred': {'$ref': '#/$defs/ActivitySelector'},
                                                         'alternative': {'$ref': '#/$defs/ActivitySelector'}},
                                          'required': ['preferred', 'alternative'],
                                          'additionalProperties': False},
                           'activity_covariance_source_ref': {'anyOf': [{'type': 'string',
                                                                         'format': 'reference',
                                                                         'minLength': 1},
                                                                        {'type': 'null'}]},
                           'variance_status': {'type': 'string', 'enum': ['known', 'estimated', 'unknown']},
                           'variance_witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/Witness'}},
                           'adjustment_bindings': {'type': 'array', 'items': {'$ref': '#/$defs/AdjustmentBinding'}}},
            'required': ['route', 'activities', 'activity_covariance_source_ref', 'variance_status',
                         'variance_witnesses', 'adjustment_bindings']},
           {'type': 'object',
            'properties': {'route': {'const': 'reported_ratio'},
                           'reported_ratio': {'$ref': '#/$defs/SourceQuantity'}},
            'required': ['route', 'reported_ratio']},
           {'type': 'object',
            'properties': {'route': {'const': 'reported_threshold_pair'},
                           'thresholds': {'type': 'object',
                                          'properties': {'preferred': {'$ref': '#/$defs/SourceQuantity'},
                                                         'alternative': {'$ref': '#/$defs/SourceQuantity'}},
                                          'required': ['preferred', 'alternative'],
                                          'additionalProperties': False}},
            'required': ['route', 'thresholds']}],
 '$defs': {'Witness': {'type': 'object',
                       'properties': {'source_ref': {'type': 'string', 'format': 'reference', 'minLength': 1},
                                      'representation': {'type': 'string', 'enum': ['original', 'text']},
                                      'start': {'type': 'integer', 'minimum': 0},
                                      'end': {'type': 'integer', 'minimum': 1},
                                      'quote': {'type': 'string', 'minLength': 1}},
                       'required': ['source_ref', 'representation', 'start', 'end', 'quote'],
                       'additionalProperties': False},
           'Context': {'type': 'object',
                       'properties': {'preferred': {'type': 'object',
                                                    'properties': {'organism': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                          {'type': 'null'}]},
                                                                   'genotype': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                          {'type': 'null'}]},
                                                                   'molecule': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                          {'type': 'null'}]},
                                                                   'construct': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                           {'type': 'null'}]},
                                                                   'preparation': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                             {'type': 'null'}]},
                                                                   'membrane': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                          {'type': 'null'}]},
                                                                   'ionic_conditions': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                                  {'type': 'null'}]},
                                                                   'voltage': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                         {'type': 'null'}]},
                                                                   'pH': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                    {'type': 'null'}]},
                                                                   'detector': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                          {'type': 'null'}]},
                                                                   'normalization': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                               {'type': 'null'}]},
                                                                   'molecular_unit': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                                {'type': 'null'}]},
                                                                   'time_window': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                             {'type': 'null'}]},
                                                                   'dead_time': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                           {'type': 'null'}]},
                                                                   'asserted_function': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                                   {'type': 'null'}]}},
                                                    'required': ['organism', 'genotype', 'molecule', 'construct',
                                                                 'preparation', 'membrane', 'ionic_conditions',
                                                                 'voltage', 'pH', 'detector', 'normalization',
                                                                 'molecular_unit', 'time_window', 'dead_time',
                                                                 'asserted_function'],
                                                    'additionalProperties': False},
                                      'alternative': {'type': 'object',
                                                      'properties': {'organism': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                            {'type': 'null'}]},
                                                                     'genotype': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                            {'type': 'null'}]},
                                                                     'molecule': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                            {'type': 'null'}]},
                                                                     'construct': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                             {'type': 'null'}]},
                                                                     'preparation': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                               {'type': 'null'}]},
                                                                     'membrane': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                            {'type': 'null'}]},
                                                                     'ionic_conditions': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                                    {'type': 'null'}]},
                                                                     'voltage': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                           {'type': 'null'}]},
                                                                     'pH': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                      {'type': 'null'}]},
                                                                     'detector': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                            {'type': 'null'}]},
                                                                     'normalization': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                                 {'type': 'null'}]},
                                                                     'molecular_unit': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                                  {'type': 'null'}]},
                                                                     'time_window': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                               {'type': 'null'}]},
                                                                     'dead_time': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                             {'type': 'null'}]},
                                                                     'asserted_function': {'anyOf': [{'$ref': '#/$defs/Witness'},
                                                                                                     {'type': 'null'}]}},
                                                      'required': ['organism', 'genotype', 'molecule', 'construct',
                                                                   'preparation', 'membrane', 'ionic_conditions',
                                                                   'voltage', 'pH', 'detector', 'normalization',
                                                                   'molecular_unit', 'time_window', 'dead_time',
                                                                   'asserted_function'],
                                                      'additionalProperties': False},
                                      'preferred_ion': {'anyOf': [{'$ref': '#/$defs/Witness'}, {'type': 'null'}]},
                                      'alternative_ion': {'anyOf': [{'$ref': '#/$defs/Witness'}, {'type': 'null'}]},
                                      'intended_change': {'anyOf': [{'$ref': '#/$defs/Witness'}, {'type': 'null'}]},
                                      'assertion': {'anyOf': [{'$ref': '#/$defs/Witness'}, {'type': 'null'}]}},
                       'required': ['preferred', 'alternative', 'preferred_ion', 'alternative_ion', 'intended_change',
                                    'assertion'],
                       'additionalProperties': False},
           'Relationships': {'type': 'object',
                             'properties': {'subject_construct': {'type': 'object',
                                                                  'properties': {'value': {'type': 'string',
                                                                                           'enum': ['same_construct',
                                                                                                    'different_construct',
                                                                                                    'paper_summary_unresolved',
                                                                                                    'unknown',
                                                                                                    'conflicting']},
                                                                                 'witnesses': {'type': 'array',
                                                                                               'items': {'$ref': '#/$defs/Witness'}}},
                                                                  'required': ['value', 'witnesses'],
                                                                  'additionalProperties': False},
                                            'quantity': {'type': 'object',
                                                         'properties': {'value': {'type': 'string',
                                                                                  'enum': ['same_ion_specific_rate_kind',
                                                                                           'different_physical_quantity',
                                                                                           'unknown',
                                                                                           'conflicting']},
                                                                        'witnesses': {'type': 'array',
                                                                                      'items': {'$ref': '#/$defs/Witness'}}},
                                                         'required': ['value', 'witnesses'],
                                                         'additionalProperties': False},
                                            'normalization': {'type': 'object',
                                                              'properties': {'value': {'type': 'string',
                                                                                       'enum': ['same_molecular_basis',
                                                                                                'common_unresolved_molecular_unit',
                                                                                                'different_molecular_basis',
                                                                                                'unknown',
                                                                                                'conflicting']},
                                                                             'witnesses': {'type': 'array',
                                                                                           'items': {'$ref': '#/$defs/Witness'}}},
                                                              'required': ['value', 'witnesses'],
                                                              'additionalProperties': False},
                                            'nonintended_conditions': {'type': 'object',
                                                                       'properties': {'value': {'type': 'string',
                                                                                                'enum': ['matched',
                                                                                                         'source_supported_adjustment',
                                                                                                         'different',
                                                                                                         'unknown',
                                                                                                         'conflicting']},
                                                                                      'witnesses': {'type': 'array',
                                                                                                    'items': {'$ref': '#/$defs/Witness'}}},
                                                                       'required': ['value', 'witnesses'],
                                                                       'additionalProperties': False},
                                            'preferred_ion_attribution': {'type': 'object',
                                                                          'properties': {'value': {'type': 'string',
                                                                                                   'enum': ['intended_protein_and_ion_supported',
                                                                                                            'mixed_contributors_unresolved',
                                                                                                            'unknown',
                                                                                                            'conflicting']},
                                                                                         'witnesses': {'type': 'array',
                                                                                                       'items': {'$ref': '#/$defs/Witness'}}},
                                                                          'required': ['value', 'witnesses'],
                                                                          'additionalProperties': False},
                                            'alternative_ion_attribution': {'type': 'object',
                                                                            'properties': {'value': {'type': 'string',
                                                                                                     'enum': ['intended_protein_and_ion_supported',
                                                                                                              'mixed_contributors_unresolved',
                                                                                                              'unknown',
                                                                                                              'conflicting']},
                                                                                           'witnesses': {'type': 'array',
                                                                                                         'items': {'$ref': '#/$defs/Witness'}}},
                                                                            'required': ['value', 'witnesses'],
                                                                            'additionalProperties': False},
                                            'preparations': {'type': 'object',
                                                             'properties': {'value': {'type': 'string',
                                                                                      'enum': ['same_preparation',
                                                                                               'different_preparations',
                                                                                               'unknown',
                                                                                               'conflicting']},
                                                                            'witnesses': {'type': 'array',
                                                                                          'items': {'$ref': '#/$defs/Witness'}}},
                                                             'required': ['value', 'witnesses'],
                                                             'additionalProperties': False},
                                            'intended_ions': {'type': 'object',
                                                              'properties': {'value': {'type': 'string',
                                                                                       'enum': ['different_ions',
                                                                                                'same_ion', 'unknown',
                                                                                                'conflicting']},
                                                                             'witnesses': {'type': 'array',
                                                                                           'items': {'$ref': '#/$defs/Witness'}}},
                                                              'required': ['value', 'witnesses'],
                                                              'additionalProperties': False}},
                             'required': ['subject_construct', 'quantity', 'normalization', 'nonintended_conditions',
                                          'preferred_ion_attribution', 'alternative_ion_attribution', 'preparations',
                                          'intended_ions'],
                             'additionalProperties': False},
           'ActivitySelector': {'type': 'object',
                                'properties': {'namespace': {'const': 'literature_compiled_assay_cells'},
                                               'sheet_ref': {'type': 'string', 'format': 'reference', 'minLength': 1},
                                               'component': {'const': 'corrected_activity'}},
                                'required': ['namespace', 'sheet_ref', 'component'],
                                'additionalProperties': False},
           'NumberSelection': {'type': 'object',
                               'properties': {'witness': {'$ref': '#/$defs/Witness'},
                                              'number_start': {'type': 'integer', 'minimum': 0},
                                              'number_end': {'type': 'integer', 'minimum': 1}},
                               'required': ['witness', 'number_start', 'number_end'],
                               'additionalProperties': False},
           'SourceQuantity': {'type': 'object',
                              'properties': {'number': {'anyOf': [{'$ref': '#/$defs/NumberSelection'},
                                                                  {'type': 'null'}]},
                                             'unit': {'anyOf': [{'$ref': '#/$defs/Witness'}, {'type': 'null'}]},
                                             'meaning': {'type': 'object',
                                                         'properties': {'value': {'type': 'string',
                                                                                  'enum': ['per_unit_ion_efflux_rate',
                                                                                           'author_inferred_per_unit_ion_efflux_rate',
                                                                                           'reported_permeability_ratio',
                                                                                           'reported_transport_selectivity_ratio',
                                                                                           'reported_cross_assay_summary_ratio',
                                                                                           'signed_reporter_estimator',
                                                                                           'charge_equivalent_rate',
                                                                                           'unknown',
                                                                                           'conflicting']},
                                                                        'witnesses': {'type': 'array',
                                                                                      'items': {'$ref': '#/$defs/Witness'}}},
                                                         'required': ['value', 'witnesses'],
                                                         'additionalProperties': False},
                                             'derivation': {'type': 'object',
                                                            'properties': {'value': {'type': 'string',
                                                                                     'enum': ['direct_reported_estimator',
                                                                                              'author_inferred_dead_time_and_geometry',
                                                                                              'author_inferred_electrical_model',
                                                                                              'author_summary_inference',
                                                                                              'unknown',
                                                                                              'conflicting',
                                                                                              'source_parameter_bound_derivation_supported']},
                                                                           'witnesses': {'type': 'array',
                                                                                         'items': {'$ref': '#/$defs/Witness'}}},
                                                            'required': ['value', 'witnesses'],
                                                            'additionalProperties': False},
                                             'qualification': {'type': 'object',
                                                               'properties': {'value': {'type': 'string',
                                                                                        'enum': ['source_qualified_approximate',
                                                                                                 'no_additional_source_qualification_selected',
                                                                                                 'unknown',
                                                                                                 'conflicting']},
                                                                              'witnesses': {'type': 'array',
                                                                                            'items': {'$ref': '#/$defs/Witness'}}},
                                                               'required': ['value', 'witnesses'],
                                                               'additionalProperties': False},
                                             'quantity_scope': {'type': 'object',
                                                                'properties': {'value': {'type': 'string',
                                                                                         'enum': ['specific_construct',
                                                                                                  'paper_summary_unresolved',
                                                                                                  'unknown',
                                                                                                  'conflicting']},
                                                                               'witnesses': {'type': 'array',
                                                                                             'items': {'$ref': '#/$defs/Witness'}}},
                                                                'required': ['value', 'witnesses'],
                                                                'additionalProperties': False},
                                             'domain_bearer': {'type': 'object',
                                                               'properties': {'value': {'type': 'string',
                                                                                        'enum': ['measured_estimator',
                                                                                                 'author_estimate',
                                                                                                 'physical_parameter',
                                                                                                 'unknown',
                                                                                                 'conflicting']},
                                                                              'witnesses': {'type': 'array',
                                                                                            'items': {'$ref': '#/$defs/Witness'}}},
                                                               'required': ['value', 'witnesses'],
                                                               'additionalProperties': False},
                                             'physical_domain_support': {'type': 'object',
                                                                         'properties': {'value': {'type': 'string',
                                                                                                  'enum': ['explicit_nonnegative_parameter_limit_supported',
                                                                                                           'reported_estimate_only',
                                                                                                           'approximation_model_missing',
                                                                                                           'unknown',
                                                                                                           'conflicting']},
                                                                                        'witnesses': {'type': 'array',
                                                                                                      'items': {'$ref': '#/$defs/Witness'}}},
                                                                         'required': ['value', 'witnesses'],
                                                                         'additionalProperties': False}},
                              'required': ['number', 'unit', 'meaning', 'derivation', 'qualification',
                                           'quantity_scope', 'domain_bearer', 'physical_domain_support'],
                              'additionalProperties': False},
           'NonintendedDifference': {'type': 'object',
                                     'properties': {'aspect': {'type': 'string',
                                                               'enum': ['detector', 'ion_concentration_or_activity',
                                                                        'voltage', 'pH', 'membrane',
                                                                        'molecular_amount', 'temperature',
                                                                        'other_reported_difference']},
                                                    'witnesses': {'type': 'array',
                                                                  'items': {'$ref': '#/$defs/Witness'}}},
                                     'required': ['aspect', 'witnesses'],
                                     'additionalProperties': False},
           'AdjustmentBinding': {'type': 'object',
                                 'properties': {'difference_index': {'type': 'integer', 'minimum': 0},
                                                'arm': {'type': 'string', 'enum': ['preferred', 'alternative']},
                                                'compiled_stage': {'type': 'string',
                                                                   'enum': ['recovery', 'molecule_amount',
                                                                            'nuisance_condition']},
                                                'control_application': {'type': 'string',
                                                                        'enum': ['addresses_selected_nonintended_difference',
                                                                                 'unknown', 'conflicting']},
                                                'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/Witness'}}},
                                 'required': ['difference_index', 'arm', 'compiled_stage', 'control_application',
                                              'witnesses'],
                                 'additionalProperties': False}},
 'type': 'object',
 'properties': {'version': {'const': 'a105_ion_discrimination_selection_v1'},
                'source_ref': {'type': 'string', 'format': 'reference', 'minLength': 1},
                'source_kind': {'type': 'string',
                                'enum': ['primary_source', 'retained_extraction', 'synthetic_fixture']},
                'context': {'$ref': '#/$defs/Context'},
                'relationships': {'$ref': '#/$defs/Relationships'},
                'nonintended_differences': {'type': 'array', 'items': {'$ref': '#/$defs/NonintendedDifference'}}},
 'required': ['version', 'source_ref', 'source_kind', 'context', 'relationships', 'nonintended_differences'],
 'unevaluatedProperties': False}

_SHEET_SCHEMA = {'$schema': 'https://json-schema.org/draft/2020-12/schema',
 'type': 'object',
 'properties': {'version': {'const': 'a105_ion_discrimination_sheet_v1'},
                'axis': {'const': 'A105'},
                'route': {'type': 'string',
                          'enum': ['compiled_activity_pair', 'reported_ratio', 'reported_threshold_pair']},
                'cells': {'type': 'object',
                          'properties': {'preferred_activity': {'allOf': [{'$ref': '#/$defs/Cell'},
                                                                          {'properties': {'component': {'const': 'preferred_activity'},
                                                                                          'formula_code': {'const': 'selected_preferred_activity_or_limit'}}}]},
                                         'alternative_activity': {'allOf': [{'$ref': '#/$defs/Cell'},
                                                                            {'properties': {'component': {'const': 'alternative_activity'},
                                                                                            'formula_code': {'const': 'selected_alternative_activity_or_limit'}}}]},
                                         'activity_ratio': {'allOf': [{'$ref': '#/$defs/Cell'},
                                                                      {'properties': {'component': {'const': 'activity_ratio'},
                                                                                      'formula_code': {'const': 'preferred_activity/alternative_activity'},
                                                                                      'unit': {'const': 'dimensionless'}}}]},
                                         'log_activity_ratio': {'allOf': [{'$ref': '#/$defs/Cell'},
                                                                          {'properties': {'component': {'const': 'log_activity_ratio'},
                                                                                          'formula_code': {'const': 'ln(activity_ratio)'},
                                                                                          'unit': {'const': 'dimensionless'}}}]},
                                         'activity_ratio_variance': {'allOf': [{'$ref': '#/$defs/Cell'},
                                                                               {'properties': {'component': {'const': 'activity_ratio_variance'},
                                                                                               'formula_code': {'const': 'J_R*C*J_R_transpose'},
                                                                                               'unit': {'const': 'dimensionless_squared'}}}]},
                                         'activity_ratio_standard_uncertainty': {'allOf': [{'$ref': '#/$defs/Cell'},
                                                                                           {'properties': {'component': {'const': 'activity_ratio_standard_uncertainty'},
                                                                                                           'formula_code': {'const': 'sqrt(activity_ratio_variance)'},
                                                                                                           'unit': {'const': 'dimensionless'}}}]},
                                         'log_activity_ratio_variance': {'allOf': [{'$ref': '#/$defs/Cell'},
                                                                                   {'properties': {'component': {'const': 'log_activity_ratio_variance'},
                                                                                                   'formula_code': {'const': 'J_log*C*J_log_transpose'},
                                                                                                   'unit': {'const': 'dimensionless_squared'}}}]},
                                         'log_activity_ratio_standard_uncertainty': {'allOf': [{'$ref': '#/$defs/Cell'},
                                                                                               {'properties': {'component': {'const': 'log_activity_ratio_standard_uncertainty'},
                                                                                                               'formula_code': {'const': 'sqrt(log_activity_ratio_variance)'},
                                                                                                               'unit': {'const': 'dimensionless'}}}]},
                                         'reported_selectivity': {'allOf': [{'$ref': '#/$defs/Cell'},
                                                                            {'properties': {'component': {'const': 'reported_selectivity'},
                                                                                            'formula_code': {'const': 'selected_original_reported_selectivity'},
                                                                                            'unit': {'const': 'dimensionless'}}}]},
                                         'nominal_threshold_ratio': {'allOf': [{'$ref': '#/$defs/Cell'},
                                                                               {'properties': {'component': {'const': 'nominal_threshold_ratio'},
                                                                                               'formula_code': {'const': 'preferred_threshold/alternative_threshold'},
                                                                                               'unit': {'const': 'dimensionless'}}}]}},
                          'required': ['preferred_activity', 'alternative_activity', 'activity_ratio',
                                       'log_activity_ratio', 'activity_ratio_variance',
                                       'activity_ratio_standard_uncertainty', 'log_activity_ratio_variance',
                                       'log_activity_ratio_standard_uncertainty', 'reported_selectivity',
                                       'nominal_threshold_ratio'],
                          'additionalProperties': False},
                'overall_quality_grade': {'type': 'null'},
                'annotation_credit': {'type': 'null'}},
 'required': ['version', 'axis', 'route', 'cells', 'overall_quality_grade', 'annotation_credit'],
 'additionalProperties': False,
 '$defs': {'Domain': {'type': 'object',
                      'properties': {'meaning': {'type': 'string',
                                                 'enum': ['reported_estimate_domain', 'derived_estimator_domain',
                                                          'nominal_threshold_arithmetic_domain',
                                                          'conditional_physical_parameter_domain']},
                                     'lower': {'anyOf': [{'type': 'number'}, {'type': 'null'}]},
                                     'upper': {'anyOf': [{'type': 'number'}, {'type': 'null'}]},
                                     'lower_inclusive': {'anyOf': [{'type': 'boolean'}, {'type': 'null'}]},
                                     'upper_inclusive': {'anyOf': [{'type': 'boolean'}, {'type': 'null'}]},
                                     'lower_unbounded': {'type': 'boolean'},
                                     'upper_unbounded': {'type': 'boolean'},
                                     'lower_exact': {'anyOf': [{'type': 'object',
                                                                'properties': {'numerator': {'type': 'string',
                                                                                             'pattern': '^-?[0-9]+$'},
                                                                               'denominator': {'type': 'string',
                                                                                               'pattern': '^[1-9][0-9]*$'}},
                                                                'required': ['numerator', 'denominator'],
                                                                'additionalProperties': False},
                                                               {'type': 'null'}]},
                                     'upper_exact': {'anyOf': [{'type': 'object',
                                                                'properties': {'numerator': {'type': 'string',
                                                                                             'pattern': '^-?[0-9]+$'},
                                                                               'denominator': {'type': 'string',
                                                                                               'pattern': '^[1-9][0-9]*$'}},
                                                                'required': ['numerator', 'denominator'],
                                                                'additionalProperties': False},
                                                               {'type': 'null'}]}},
                      'required': ['meaning', 'lower', 'upper', 'lower_inclusive', 'upper_inclusive',
                                   'lower_unbounded', 'upper_unbounded', 'lower_exact', 'upper_exact'],
                      'additionalProperties': False},
           'Dependency': {'type': 'object',
                          'properties': {'role': {'type': 'string', 'enum': ['preferred', 'alternative', 'reported']},
                                         'source_ref': {'type': 'string', 'format': 'reference', 'minLength': 1},
                                         'component_ref': {'anyOf': [{'type': 'string',
                                                                      'format': 'reference',
                                                                      'minLength': 1},
                                                                     {'type': 'null'}]},
                                         'namespace': {'anyOf': [{'type': 'string',
                                                                  'enum': ['literature_compiled_assay_cells']},
                                                                 {'type': 'null'}]},
                                         'component': {'anyOf': [{'type': 'string', 'enum': ['corrected_activity']},
                                                                 {'type': 'null'}]},
                                         'physical_keys': {'type': 'array',
                                                           'items': {'type': 'string', 'minLength': 1}},
                                         'opaque_dependency_keys': {'type': 'array',
                                                                    'items': {'type': 'string', 'minLength': 1}},
                                         'physical_identity_status': {'type': 'string',
                                                                      'enum': ['source_numeric_span',
                                                                               'partly_canonical',
                                                                               'cross_component_identity_unknown']}},
                          'required': ['role', 'source_ref', 'component_ref', 'namespace', 'component',
                                       'physical_keys', 'opaque_dependency_keys', 'physical_identity_status'],
                          'additionalProperties': False},
           'Cell': {'type': 'object',
                    'properties': {'component': {'type': 'string',
                                                 'enum': ['preferred_activity', 'alternative_activity',
                                                          'activity_ratio', 'log_activity_ratio',
                                                          'activity_ratio_variance',
                                                          'activity_ratio_standard_uncertainty',
                                                          'log_activity_ratio_variance',
                                                          'log_activity_ratio_standard_uncertainty',
                                                          'reported_selectivity', 'nominal_threshold_ratio']},
                                   'value': {'anyOf': [{'type': 'number'}, {'type': 'null'}]},
                                   'threshold': {'anyOf': [{'type': 'number'}, {'type': 'null'}]},
                                   'unit': {'anyOf': [{'type': 'string',
                                                       'enum': ['dimensionless', 'per_min', 'per_s', 'ions_per_s',
                                                                'dimensionless_squared']},
                                                      {'type': 'null'}]},
                                   'status': {'type': 'string',
                                              'enum': ['populated', 'bounded', 'conditional_arithmetic',
                                                       'unavailable', 'conflicting']},
                                   'origin': {'type': 'string',
                                              'enum': ['reported', 'author_inferred', 'derived', 'synthetic',
                                                       'graph_derived']},
                                   'meaning': {'type': 'string',
                                               'enum': ['native_selected_activity_or_limit',
                                                        'ion_specific_rate_ratio', 'log_ion_specific_rate_ratio',
                                                        'first_order_ratio_variance',
                                                        'first_order_ratio_standard_uncertainty',
                                                        'first_order_log_ratio_variance',
                                                        'first_order_log_ratio_standard_uncertainty',
                                                        'source_reported_selectivity_limit',
                                                        'nominal_reported_threshold_division',
                                                        'signed_activity_estimator_ratio']},
                                   'reported_domain': {'anyOf': [{'allOf': [{'$ref': '#/$defs/Domain'},
                                                                            {'properties': {'meaning': {'const': 'reported_estimate_domain'}}}]},
                                                                 {'type': 'null'}]},
                                   'nominal_domain': {'anyOf': [{'allOf': [{'$ref': '#/$defs/Domain'},
                                                                           {'properties': {'meaning': {'const': 'nominal_threshold_arithmetic_domain'}}}]},
                                                                {'type': 'null'}]},
                                   'physical_domain': {'anyOf': [{'allOf': [{'$ref': '#/$defs/Domain'},
                                                                            {'properties': {'meaning': {'const': 'conditional_physical_parameter_domain'}}}]},
                                                                 {'type': 'null'}]},
                                   'relation': {'type': 'string',
                                                'enum': ['point', 'lt', 'le', 'gt', 'ge', 'lower_limit',
                                                         'upper_limit', 'none']},
                                   'approximation': {'type': 'string',
                                                     'enum': ['source_qualified', 'not_explicitly_qualified',
                                                              'unknown', 'conflicting']},
                                   'quantity_kind': {'type': 'string',
                                                     'enum': ['ion_specific_rate', 'permeability_ratio',
                                                              'reported_transport_selectivity',
                                                              'author_cross_assay_summary',
                                                              'nominal_threshold_comparison', 'unknown',
                                                              'conflicting', 'source_activity_estimator_ratio']},
                                   'scientific_applicability': {'type': 'string',
                                                                'enum': ['supported_for_selected_comparison',
                                                                         'conditional_source_report', 'unresolved',
                                                                         'incompatible',
                                                                         'estimator_comparison_only']},
                                   'unavailable_reasons': {'type': 'array',
                                                           'items': {'type': 'string',
                                                                     'enum': ['source_number_not_selected',
                                                                              'source_unit_not_selected',
                                                                              'unsupported_source_expression',
                                                                              'ambiguous_source_number_role',
                                                                              'source_qualification_conflicting',
                                                                              'source_quantity_meaning_unknown',
                                                                              'selected_activity_unavailable',
                                                                              'endpoint_not_transport_flux',
                                                                              'ratio_not_positive',
                                                                              'denominator_not_strictly_positive',
                                                                              'different_subject_construct',
                                                                              'subject_construct_unresolved',
                                                                              'different_physical_quantities',
                                                                              'quantity_relation_unresolved',
                                                                              'different_molecular_basis',
                                                                              'normalization_unresolved',
                                                                              'nonintended_conditions_different',
                                                                              'nonintended_conditions_unresolved',
                                                                              'ion_attribution_unresolved',
                                                                              'signed_estimator_not_physical_rate',
                                                                              'approximation_model_missing',
                                                                              'reported_estimate_not_physical_bound',
                                                                              'physical_domain_support_missing',
                                                                              'covariance_not_selected',
                                                                              'covariance_status_unknown',
                                                                              'covariance_owner_or_dependency_mismatch',
                                                                              'covariance_units_incompatible',
                                                                              'covariance_invalid',
                                                                              'bounded_ratio_uncertainty_unimplemented',
                                                                              'numerical_model_range',
                                                                              'unrequested_route_component',
                                                                              'reused_activity_not_ion_discrimination',
                                                                              'intended_ions_not_distinct',
                                                                              'zero_denominator_estimator',
                                                                              'adjustment_binding_required',
                                                                              'adjustment_not_in_compiled_activity',
                                                                              'adjustment_scope_unresolved',
                                                                              'physical_parameter_model_unimplemented',
                                                                              'unimplemented_number_representation',
                                                                              'route_not_applicable']}},
                                   'limitations': {'type': 'array',
                                                   'items': {'type': 'string',
                                                             'enum': ['no_annotation_credit',
                                                                      'no_reliability_probability',
                                                                      'no_ion_flux_from_charge', 'no_GHK_inversion',
                                                                      'no_independence_from_distinct_refs',
                                                                      'reported_and_calculated_not_separate_experiments',
                                                                      'nominal_threshold_arithmetic_not_physical_bound',
                                                                      'paper_summary_not_construct_specific',
                                                                      'denominator_positive_condition',
                                                                      'first_order_joint_covariance',
                                                                      'approximate_source_inference',
                                                                      'nonintended_protocol_differences_retained']}},
                                   'dependencies': {'type': 'array', 'items': {'$ref': '#/$defs/Dependency'}},
                                   'variance_status': {'type': 'string', 'enum': ['known', 'estimated', 'unknown']},
                                   'annotation_credit': {'type': 'null'},
                                   'estimator_domain': {'anyOf': [{'allOf': [{'$ref': '#/$defs/Domain'},
                                                                             {'properties': {'meaning': {'const': 'derived_estimator_domain'}}}]},
                                                                  {'type': 'null'}]},
                                   'formula_code': {'type': 'string',
                                                    'enum': ['selected_preferred_activity_or_limit',
                                                             'selected_alternative_activity_or_limit',
                                                             'preferred_activity/alternative_activity',
                                                             'ln(activity_ratio)', 'J_R*C*J_R_transpose',
                                                             'sqrt(activity_ratio_variance)',
                                                             'J_log*C*J_log_transpose',
                                                             'sqrt(log_activity_ratio_variance)',
                                                             'selected_original_reported_selectivity',
                                                             'preferred_threshold/alternative_threshold']}},
                    'required': ['component', 'value', 'threshold', 'unit', 'status', 'origin', 'meaning',
                                 'reported_domain', 'nominal_domain', 'physical_domain', 'relation', 'approximation',
                                 'quantity_kind', 'scientific_applicability', 'unavailable_reasons', 'limitations',
                                 'dependencies', 'variance_status', 'annotation_credit', 'estimator_domain',
                                 'formula_code'],
                    'additionalProperties': False}}}

_COVARIANCE_SCHEMA = {'type': 'object',
 'properties': {'version': {'const': 'a105_ion_activity_covariance_v1'},
                'activity_order': {'const': ['preferred', 'alternative']},
                'activity_keys': {'type': 'array',
                                  'items': {'type': 'string', 'minLength': 1},
                                  'minItems': 2,
                                  'maxItems': 2},
                'activity_units': {'type': 'array', 'items': {'const': 'per_min'}, 'minItems': 2, 'maxItems': 2},
                'dependency_keys': {'type': 'array',
                                    'items': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}},
                                    'minItems': 2,
                                    'maxItems': 2},
                'matrix': {'type': 'array',
                           'items': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2},
                           'minItems': 2,
                           'maxItems': 2},
                'variance_status': {'type': 'string', 'enum': ['known', 'estimated', 'unknown']},
                'origin': {'type': 'string', 'enum': ['reported', 'derived', 'synthetic']},
                'basis': {'const': 'joint_covariance_of_selected_per_unit_activity_estimators'}},
 'required': ['version', 'activity_order', 'activity_keys', 'activity_units', 'dependency_keys', 'matrix',
              'variance_status', 'origin', 'basis'],
 'additionalProperties': False}


_SHEET_SCHEMA['$defs']['Cell']['properties']['unavailable_reasons']['items']['enum'].append('reported_uncertainty_reading_unimplemented')
_SHEET_SCHEMA['$defs']['Cell']['properties']['unavailable_reasons']['items']['enum'].append('physical_domain_inconsistent')
_SHEET_SCHEMA['$defs']['Cell']['properties']['zero_denominator_case']={'type':'string','enum':['not_applicable','selected_estimator_is_zero','selected_estimator_nonzero','possible_in_source_domain','excluded_by_selected_source_domain','unknown']}
_SHEET_SCHEMA['$defs']['Cell']['required'].append('zero_denominator_case')
_SHEET_SCHEMA['$defs']['Cell']['properties']['quantity_kind']['enum'].extend([x for x in _SELECTION_SCHEMA['$defs']['SourceQuantity']['properties']['meaning']['properties']['value']['enum'] if x not in _SHEET_SCHEMA['$defs']['Cell']['properties']['quantity_kind']['enum']])
_SHEET_SCHEMA['$defs']['Cell']['properties']['derivation']={'type':'string','enum':[*_SELECTION_SCHEMA['$defs']['SourceQuantity']['properties']['derivation']['properties']['value']['enum'],'selected_compiled_activity','derived_activity_ratio','first_order_activity_covariance','not_applicable']}
_SHEET_SCHEMA['$defs']['Cell']['required'].append('derivation')
_SHEET_SCHEMA['$defs']['Cell']['properties']['source_qualifications']={'type':'array','items':{'type':'string','enum':['adjacent_approximate','nonadjacent_source_approximation','selected_qualification_conflicting','selected_qualification_unknown','adjacent_uncertainty_uninterpreted']}}
_SHEET_SCHEMA['$defs']['Cell']['required'].append('source_qualifications')
_SHEET_SCHEMA['$defs']['Dependency']['properties']['origin']={'type':'string','enum':['reported','author_inferred','derived','synthetic','graph_derived']}
_SHEET_SCHEMA['$defs']['Dependency']['required'].append('origin')
_SHEET_SCHEMA['$defs']['Cell']['properties']['unavailable_reasons']['items']['enum'].extend(['shared_activity_estimator_inconsistent','shared_activity_covariance_inconsistent','synthetic_activity_for_nonsynthetic_selection'])



def ion_discrimination_population_schema():
    return deepcopy(_SELECTION_SCHEMA)


def ion_discrimination_sheet_schema():
    return deepcopy(_SHEET_SCHEMA)


def ion_activity_covariance_schema():
    return deepcopy(_COVARIANCE_SCHEMA)


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _meaning(value, schema, sources, field):
    allowed = schema['properties']['value']['enum']
    return _interpretation(value, allowed, sources, field)


def activity_key(selection):
    return identity('selected_ion_activity', selection)


def dependency_keys(row):
    return list(dict.fromkeys(key for dep in row['dependencies']
        for name in ('canonical_physical_keys', 'recorded_dependency_keys') for key in dep[name]))


def _read_quantity(selected, sources, *, field, source_kind):
    schema = _SELECTION_SCHEMA['$defs']['SourceQuantity']['properties']
    result = {name: _meaning(value, schema[name], sources, field + '.' + name)
        for name, value in selected.items() if name not in ('number', 'unit')}
    number, unit, reasons = None, None, []
    if selected['number'] is None:
        reasons.append('source_number_not_selected')
    else:
        try:
            number = read_ion_number(selected['number'], sources=sources)
        except ExperimentalContractError as error:
            if error.code not in ('unimplemented_number_representation', 'interval_source_number_unsupported',
                                   'untyped_limit_source_number', 'numerical_model_range'):
                raise
            reasons.append('numerical_model_range' if error.code == 'numerical_model_range' else 'unimplemented_number_representation')
    try:
        unit = read_ion_unit(selected['unit'], sources=sources)
    except ExperimentalContractError as error:
        if error.code != 'unsupported_source_unit':
            raise
        reasons.append('unimplemented_number_representation')
    ratio = result['meaning']['value'] in ('reported_permeability_ratio', 'reported_transport_selectivity_ratio', 'reported_cross_assay_summary_ratio')
    if selected['unit'] is None and not ratio:
        reasons.append('source_unit_not_selected')
    if number is not None:
        check_explicit_unit(number, unit, sources=sources, dimensionless=ratio)
    if ratio and unit is not None and unit['unit'] != 'dimensionless':
        _fail('source_number_unit_role_mismatch', field)
    qualified = result['qualification']['value']
    approximation = ('conflicting' if qualified=='conflicting' else 'source_qualified' if number and number['adjacent_approximate'] or qualified=='source_qualified_approximate' else 'unknown' if qualified=='unknown' else 'not_explicitly_qualified')
    qualifications=[]
    if number and number['adjacent_approximate']:qualifications.append('adjacent_approximate')
    if qualified=='source_qualified_approximate':qualifications.append('nonadjacent_source_approximation')
    if qualified=='conflicting':qualifications.append('selected_qualification_conflicting')
    if qualified=='unknown':qualifications.append('selected_qualification_unknown')
    if number and number.get('adjacent_uncertainty_uninterpreted'):qualifications.append('adjacent_uncertainty_uninterpreted')
    derivation=result['derivation']['value']
    origin='synthetic' if source_kind=='synthetic_fixture' else 'derived' if source_kind=='retained_extraction' else 'author_inferred' if derivation in ('author_inferred_dead_time_and_geometry','author_inferred_electrical_model','author_summary_inference') else 'reported'
    return {'kind': 'source_quantity', 'selection': deepcopy(selected), 'number': number, 'unit': unit,
        'interpretations': result, 'approximation': approximation, 'source_qualifications':qualifications,'origin':origin,'reasons': reasons}


def _read_covariance(reference, operands, sources, requested_status, source_kind):
    if reference is None:
        return {'status': 'not_selected', 'source_ref': None, 'data': None}
    source = sources.source(reference, 'original')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _fail('duplicate_json_key', 'activity_covariance')
            result[key] = value
        return result
    try:
        data = json.loads(source['content'].decode('utf8'), object_pairs_hook=pairs,
            parse_constant=lambda _token: _fail('finite_number_required', 'activity_covariance'))
        validate_schema(data, ion_activity_covariance_schema())
        if data['activity_keys'] != [operands[r]['activity_key'] for r in ROLES]:
            _fail('covariance_owner_or_dependency_mismatch', 'activity_keys')
        if data['dependency_keys'] != [dependency_keys(operands[r]['row']) for r in ROLES]:
            _fail('covariance_owner_or_dependency_mismatch', 'dependency_keys')
        if any(operands[r]['row']['unit'] != 'per_min' for r in ROLES):
            _fail('covariance_units_incompatible', 'activity_units')
        matrix = data['matrix']
        if any(type(v) not in (int, float) or not math.isfinite(v) for row in matrix for v in row):
            _fail('covariance_invalid', 'matrix')
        a,b,c,d = (Fraction(str(v)) for row in matrix for v in row)
        if b != c or a < 0 or d < 0 or a*d-b*b < 0:
            _fail('covariance_invalid', 'matrix')
        if data['origin']=='synthetic' and source_kind!='synthetic_fixture':
            _fail('covariance_invalid','synthetic_covariance_for_nonsynthetic_source')
        alias=[canonical_activity_owner(operands[r]['row']) for r in ROLES]
        if alias[0] is not None and alias[0]==alias[1] and (matrix[0]!=matrix[1] or any(row[0]!=row[1] for row in matrix)):
            _fail('shared_activity_covariance_inconsistent','matrix')
        if data['variance_status'] != requested_status:
            _fail('covariance_status_unknown', 'variance_status')
        return {'status': 'valid', 'source_ref': reference, 'artifact_ref': source['artifact_ref'], 'data': data}
    except (ExperimentalContractError, ValueError, TypeError, OverflowError) as error:
        code = getattr(error, 'code', 'covariance_invalid')
        if code not in ('covariance_owner_or_dependency_mismatch', 'covariance_units_incompatible', 'covariance_status_unknown','shared_activity_covariance_inconsistent'):
            code = 'covariance_invalid'
        return {'status': code, 'source_ref': reference, 'artifact_ref': source['artifact_ref'], 'data': None}


def _adjustments(arguments, operands, sources):
    bindings, reasons = [], []
    differences = arguments['nonintended_differences']
    for selected in arguments['adjustment_bindings']:
        binding = deepcopy(selected)
        binding['witnesses'] = [sources.witness(w, 'adjustment_binding') for w in selected['witnesses']]
        if selected['difference_index'] >= len(differences):
            _fail('adjustment_difference_index_unresolved', 'adjustment_bindings')
        if selected['control_application'] != 'addresses_selected_nonintended_difference' or not binding['witnesses']:
            reasons.append('adjustment_scope_unresolved')
        row = operands[selected['arm']]['row'];stage = selected['compiled_stage']
        state = row['correction_stages'][stage]
        roles = {'recovery': ('k',), 'molecule_amount': ('E',), 'nuisance_condition': ('u','v')}[stage]
        dep_roles = {d['role'] for d in row['dependencies']}
        meanings = row['operand_meanings']
        allowed = {'k': ('applicable_reporter_standard',), 'E': ('same_assay_active_molecules','same_assay_total_molecules'),
            'u': ('test_nuisance_control_excludes_intended_change',), 'v': ('reference_nuisance_control_excludes_intended_change',)}
        applied = (row['status'] == 'populated' and row['component'] == 'corrected_activity'
            and row['formula'] in ('(q-g)*v/(k*E*u)','source_already_corrected_amount_normalized_value')
            and state in ('already_applied','not_applied')
            and (state == 'already_applied' or all(r in dep_roles and meanings[r] in allowed[r] for r in roles)))
        if not applied:
            reasons.append('adjustment_not_in_compiled_activity')
        binding['compiled_stage_verified'] = applied
        bindings.append(binding)
    if arguments['relationships']['nonintended_conditions']['value'] == 'source_supported_adjustment':
        if not differences or any(not any(b['difference_index']==i and b['compiled_stage_verified'] for b in bindings) for i in range(len(differences))):
            reasons.append('adjustment_binding_required')
    return bindings, list(dict.fromkeys(reasons))


def read_ion_discrimination_inputs(arguments, *, read_source, read_component):
    """Authenticate original limits or exactly possessed compiled activities."""
    args = deepcopy(arguments);validate_schema(args, ion_discrimination_population_schema())
    sources = _Sources(read_source);original = sources.source(args['source_ref'],'original')
    context = {}
    for name,value in args['context'].items():
        if name in ROLES:
            context[name] = {key: None if w is None else sources.witness(w,'context.'+name+'.'+key) for key,w in value.items()}
        else:
            context[name] = None if value is None else sources.witness(value,'context.'+name)
    relschema = _SELECTION_SCHEMA['$defs']['Relationships']['properties']
    relationships = {name:_meaning(value,relschema[name],sources,'relationships.'+name) for name,value in args['relationships'].items()}
    differences = [{**deepcopy(d),'witnesses':[sources.witness(w,'nonintended_difference') for w in d['witnesses']]} for d in args['nonintended_differences']]
    operands={};covariance={'status':'not_selected','source_ref':None,'data':None};adjustments=[];adjustment_reasons=[]
    if args['route']=='compiled_activity_pair':
        for role, selection in args['activities'].items():
            rows = read_component(deepcopy(selection))
            if not isinstance(rows,list) or len(rows)!=1 or rows[0]['sheet_ref']!=selection['sheet_ref'] or rows[0]['component']!='corrected_activity':
                _fail('selected_activity_not_received',role)
            validate_schema(rows,compiled_assay_cells_schema())
            operands[role]={'kind':'compiled_activity','selection':deepcopy(selection),'activity_key':activity_key(selection),'row':deepcopy(rows[0])}
        covariance = _read_covariance(args['activity_covariance_source_ref'],operands,sources,args['variance_status'],args['source_kind'])
        witnesses=[sources.witness(w,'variance_witness') for w in args['variance_witnesses']]
        if args['variance_status']!='unknown' and not witnesses:
            _fail('variance_witness_required','variance_witnesses')
        adjustments,adjustment_reasons=_adjustments(args,operands,sources)
    elif args['route']=='reported_ratio':
        operands['reported']=_read_quantity(args['reported_ratio'],sources,field='reported_ratio',source_kind=args['source_kind'])
    else:
        operands={role:_read_quantity(selected,sources,field=role,source_kind=args['source_kind']) for role,selected in args['thresholds'].items()}
    return {'version':VERSION,'selection':args,'source_ref':args['source_ref'],'artifact_ref':original['artifact_ref'],
        'source_refs':list(sources.references),'route':args['route'],'context':context,'relationships':relationships,
        'nonintended_differences':differences,'operands':operands,'covariance':covariance,
        'adjustment_bindings':adjustments,'adjustment_reasons':adjustment_reasons}


__all__=['VERSION','ROLES','ion_discrimination_population_schema','ion_discrimination_sheet_schema',
    'ion_activity_covariance_schema','read_ion_discrimination_inputs','activity_key','dependency_keys']


def validate_ion_discrimination_extraction(extraction):
    """Validate parsed-input shape and numerical ownership without source I/O."""
    e=deepcopy(extraction)
    fields={'version','selection','source_ref','artifact_ref','source_refs','route','context','relationships',
        'nonintended_differences','operands','covariance','adjustment_bindings','adjustment_reasons'}
    if not isinstance(e,dict) or set(e)!=fields or e['version']!=VERSION:
        _fail('ion_extraction_shape_mismatch','extraction')
    validate_schema(e['selection'],ion_discrimination_population_schema())
    args=e['selection']
    if e['route']!=args['route'] or e['source_ref']!=args['source_ref'] or e['source_ref'] not in e['source_refs']:
        _fail('ion_extraction_selection_mismatch','extraction')
    if set(e['relationships'])!=set(args['relationships']) or any(e['relationships'][k]['value']!=v['value'] for k,v in args['relationships'].items()):
        _fail('ion_extraction_selection_mismatch','relationships')
    if e['route']=='compiled_activity_pair':
        if set(e['operands'])!=set(ROLES):_fail('ion_extraction_shape_mismatch','operands')
        for role in ROLES:
            op=e['operands'][role];selected=args['activities'][role]
            if set(op)!={'kind','selection','activity_key','row'} or op['kind']!='compiled_activity' or op['selection']!=selected or op['activity_key']!=activity_key(selected):
                _fail('ion_extraction_selection_mismatch','operands.'+role)
            validate_schema([op['row']],compiled_assay_cells_schema())
            if op['row']['sheet_ref']!=selected['sheet_ref'] or op['row']['component']!='corrected_activity':
                _fail('ion_extraction_selection_mismatch','operands.'+role)
        cov=e['covariance']
        if cov['status']=='valid':
            validate_schema(cov['data'],ion_activity_covariance_schema())
            if cov['data']['activity_keys']!=[e['operands'][r]['activity_key'] for r in ROLES] or cov['data']['dependency_keys']!=[dependency_keys(e['operands'][r]['row']) for r in ROLES]:
                _fail('covariance_owner_or_dependency_mismatch','covariance')
            C=cov['data']['matrix']
            if any(type(v) not in (int,float) or not math.isfinite(v) for row in C for v in row):
                _fail('covariance_invalid','covariance')
            a,b,c,d=(Fraction(str(v)) for row in C for v in row)
            if b!=c or a<0 or d<0 or a*d-b*b<0:_fail('covariance_invalid','covariance')
    else:
        wanted={'reported':args['reported_ratio']} if e['route']=='reported_ratio' else args['thresholds']
        if set(e['operands'])!=set(wanted):_fail('ion_extraction_shape_mismatch','operands')
        for role,selected in wanted.items():
            q=e['operands'][role]
            if set(q)!={'kind','selection','number','unit','interpretations','approximation','source_qualifications','origin','reasons'} or q['kind']!='source_quantity' or q['selection']!=selected:
                _fail('ion_extraction_selection_mismatch','operands.'+role)
            if any(q['interpretations'][k]['value']!=v['value'] for k,v in selected.items() if k not in ('number','unit')):
                _fail('ion_extraction_selection_mismatch','interpretations')
            n=q['number']
            if n is not None:
                sel=selected['number'];w=sel['witness'];token=w['quote'][sel['number_start']:sel['number_end']]
                if (n['raw_token']!=token or type(n['value']) not in (int,float) or not math.isfinite(n['value'])
                        or n['relation'] not in ('point','lt','le','gt','ge','lower_limit','upper_limit')
                        or type(n['adjacent_approximate']) is not bool):
                    _fail('ion_extraction_number_mismatch','number')
                exact=Fraction(int(n['exact']['numerator']),int(n['exact']['denominator']))
                if float(exact)!=n['value']:
                    _fail('ion_extraction_number_mismatch','number')
    return e


__all__.append('validate_ion_discrimination_extraction')


def canonical_activity_owner(row):
    """Known complete mean ownership, never a shared subset or equal values.

    Each retained quantity identity must have canonical source anchors; unknown
    physical identities return None. Stated correction identities are constants.
    """
    if row['unit']!='per_min':return None
    formula=row['formula'];stages=row['correction_stages']
    if any(v in ('unknown','conflicting') for v in stages.values()):return None
    if formula=='source_already_corrected_amount_normalized_value':
        if any(v!='already_applied' for v in stages.values()):return None
        roles=('q',)
    elif formula=='(q-g)*v/(k*E*u)':
        if stages['background']!='already_applied' or stages['molecule_amount']!='not_applied':return None
        roles=('q','g','k','E','u','v')
    else:return None
    parts=[]
    for role in roles:
        entries=[d for d in row['dependencies'] if d['role']==role]
        if len(entries)!=1:return None
        d=entries[0]
        if d['identity_stage'] is not None:
            allowed={'g':'contaminant','k':'recovery','u':'nuisance_condition','v':'nuisance_condition'}
            if allowed.get(role)!=d['identity_stage'] or stages[d['identity_stage']]!='already_applied':return None
            parts.append((role,'identity',d['identity_stage']))
        else:
            if not d['quantity_key'] or not d['canonical_physical_keys'] or d['physical_identity_status']!='partly_canonical':return None
            parts.append((role,'quantity',d['quantity_key'],tuple(sorted(d['canonical_physical_keys'])),tuple(sorted(d['recorded_dependency_keys']))))
    return row['unit'],formula,tuple(sorted(stages.items())),tuple(parts)


__all__.append('canonical_activity_owner')
