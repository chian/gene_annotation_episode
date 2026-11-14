"""Source-bound summary precision inputs, separate from numerical calculation.

Schemas are exact reviewed declarations (002 selection;004 input/extraction/sheet).
Repeated declarations below share Python values only; accessors detach them.
The sheet's local $defs remain scoped to that standalone sheet schema.
No acquisition, model call, Store or episode behavior belongs here.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import re

from .domain import ContractError, canonical, validate_schema
from .literature_assay_inputs import _Sources
from .literature_experimental_contracts import ExperimentalContractError
from .literature_kinetic_inputs import (
    read_kinetic_inputs, _count_reading, _cardinal_count, _literal_fraction,
    _UNIT_TABLES, _normalize,
)

# Generated, readable and losslessly shared schema declarations. Do not mutate.
_S0 = {'const': 'a105_kinetic_summary_precision_selection_v1'}
_S1 = {'const': 'a105_kinetic_source_selection_v1'}
_S2 = {'type': 'string', 'pattern': '^(?:[a-z][a-z_]*_[a-f0-9]{24,64}|@[A-Za-z][A-Za-z0-9_]*)$', 'description': 'An existing persistent record ID. In a reasoning commit only, @name refers to an earlier successfully processed row declared with alias name in this same commit. Ordinary tool calls require existing persistent IDs.'}
_S3 = ['primary_source', 'synthetic_fixture']
_S4 = {'enum': _S3}
_S5 = ['Km', 'kcat', 'catalytic_efficiency', 'unknown', 'conflicting']
_S6 = {'enum': _S5}
_S7 = ['original', 'text']
_S8 = {'enum': _S7}
_S9 = {'type': 'integer', 'minimum': 0}
_S10 = {'type': 'integer', 'minimum': 1}
_S11 = {'type': 'string', 'minLength': 1}
_S12 = {'source_ref': _S2, 'representation': _S8, 'start': _S9, 'end': _S10, 'quote': _S11}
_S13 = ['source_ref', 'representation', 'start', 'end', 'quote']
_S14 = {'type': 'object', 'properties': _S12, 'required': _S13, 'additionalProperties': False}
_S15 = {'type': 'array', 'items': _S14}
_S16 = {'value': _S6, 'witnesses': _S15}
_S17 = ['value', 'witnesses']
_S18 = {'type': 'object', 'properties': _S16, 'required': _S17, 'additionalProperties': False}
_S19 = {'type': 'null'}
_S20 = [_S14, _S19]
_S21 = {'anyOf': _S20}
_S22 = {'organism': _S21, 'genotype': _S21, 'molecule': _S21, 'construct': _S21}
_S23 = ['organism', 'genotype', 'molecule', 'construct']
_S24 = {'type': 'object', 'properties': _S22, 'required': _S23, 'additionalProperties': False}
_S25 = {'substrate': _S21, 'preparation': _S21, 'experiment': _S21, 'experimental_system': _S21, 'conditions': _S21, 'endpoint': _S21, 'normalization': _S21}
_S26 = ['substrate', 'preparation', 'experiment', 'experimental_system', 'conditions', 'endpoint', 'normalization']
_S27 = {'type': 'object', 'properties': _S25, 'required': _S26, 'additionalProperties': False}
_S28 = {'witness': _S14, 'number_start': _S9, 'number_end': _S10}
_S29 = ['witness', 'number_start', 'number_end']
_S30 = {'type': 'object', 'properties': _S28, 'required': _S29, 'additionalProperties': False}
_S31 = {'number': _S30, 'unit': _S21}
_S32 = ['number', 'unit']
_S33 = {'type': 'object', 'properties': _S31, 'required': _S32, 'additionalProperties': False}
_S34 = [_S33, _S19]
_S35 = {'anyOf': _S34}
_S36 = ['reported_point', 'source_qualified_approximate', 'unknown', 'conflicting']
_S37 = {'enum': _S36}
_S38 = {'value': _S37, 'witnesses': _S15}
_S39 = {'type': 'object', 'properties': _S38, 'required': _S17, 'additionalProperties': False}
_S40 = ['sd', 'sem', 'ci', 'unspecified', 'unreported']
_S41 = {'enum': _S40}
_S42 = {'value': _S41, 'witnesses': _S15}
_S43 = {'type': 'object', 'properties': _S42, 'required': _S17, 'additionalProperties': False}
_S44 = [_S30, _S19]
_S45 = {'anyOf': _S44}
_S46 = {'witness': _S14, 'lower_start': _S9, 'lower_end': _S9, 'upper_start': _S9, 'upper_end': _S9}
_S47 = ['witness', 'lower_start', 'lower_end', 'upper_start', 'upper_end']
_S48 = {'type': 'object', 'properties': _S46, 'required': _S47, 'additionalProperties': False}
_S49 = [_S48, _S19]
_S50 = {'anyOf': _S49}
_S51 = ['same_as_parameter', 'explicit_unit', 'unknown']
_S52 = {'enum': _S51}
_S53 = {'value': _S52, 'witnesses': _S15}
_S54 = {'type': 'object', 'properties': _S53, 'required': _S17, 'additionalProperties': False}
_S55 = {'type': 'object', 'properties': _S28, 'required': _S29, 'additionalProperties': False, 'description': 'Select the complete reported repetition numeral, which may be decimal digits or an English cardinal word expression. Outer witness offsets are UTF8 bytes; number_start and number_end are Unicode character positions inside that exact quote. Do not supply a converted number. Qualified or unsupported counts retain partial source information; repetition meaning is selected separately.'}
_S56 = [_S55, _S19]
_S57 = {'anyOf': _S56}
_S58 = ['biological_preparations', 'technical_measurements', 'unspecified']
_S59 = {'enum': _S58}
_S60 = {'value': _S59, 'witnesses': _S15}
_S61 = {'type': 'object', 'properties': _S60, 'required': _S17, 'additionalProperties': False}
_S62 = ['fit_to_averaged_curve', 'between_fitted_parameters', 'unknown']
_S63 = {'enum': _S62}
_S64 = {'value': _S63, 'witnesses': _S15}
_S65 = {'type': 'object', 'properties': _S64, 'required': _S17, 'additionalProperties': False}
_S66 = {'statistic': _S43, 'magnitude': _S45, 'interval': _S50, 'unit': _S21, 'unit_relationship': _S54, 'confidence_level': _S21, 'count': _S57, 'repetition_basis': _S61, 'estimate_basis': _S65}
_S67 = ['statistic', 'magnitude', 'interval', 'unit', 'unit_relationship', 'confidence_level', 'count', 'repetition_basis', 'estimate_basis']
_S68 = {'type': 'object', 'properties': _S66, 'required': _S67, 'additionalProperties': False}
_S69 = {'parameter_kind': _S18, 'subject': _S24, 'context': _S27, 'measurement_identity': _S21, 'measurement': _S35, 'qualification': _S39, 'uncertainty': _S68}
_S70 = ['parameter_kind', 'subject', 'context', 'measurement_identity', 'measurement', 'qualification', 'uncertainty']
_S71 = {'type': 'object', 'properties': _S69, 'required': _S70, 'additionalProperties': False}
_S72 = {'const': 'unknown'}
_S73 = {'type': 'array', 'items': _S14, 'maxItems': 0}
_S74 = {'value': _S72, 'witnesses': _S73}
_S75 = {'type': 'object', 'properties': _S74, 'required': _S17, 'additionalProperties': False}
_S76 = {'subject_relationship': _S75, 'parameter_definition_relationship': _S75, 'substrate_arrangement': _S75, 'comparison_scope': _S75, 'nonintended_conditions_relationship': _S75}
_S77 = ['subject_relationship', 'parameter_definition_relationship', 'substrate_arrangement', 'comparison_scope', 'nonintended_conditions_relationship']
_S78 = {'type': 'object', 'properties': _S76, 'required': _S77, 'additionalProperties': False}
_S79 = {'version': _S1, 'source_ref': _S2, 'source_kind': _S4, 'numerator': _S71, 'denominator': _S19, 'comparison': _S78}
_S80 = ['version', 'source_ref', 'source_kind', 'numerator', 'denominator', 'comparison']
_S81 = {'type': 'object', 'properties': _S79, 'required': _S80, 'additionalProperties': False}
_S82 = ['source_supported', 'source_contradicted', 'unknown', 'conflicting']
_S83 = {'enum': _S82}
_S84 = {'state': _S83, 'witnesses': _S15}
_S85 = ['state', 'witnesses']
_S86 = {'type': 'object', 'properties': _S84, 'required': _S85, 'additionalProperties': False}
_S87 = ['physical_preparation_count', 'statistical_estimator_count', 'both_same_count', 'technical_measurement_count', 'unknown', 'conflicting']
_S88 = {'enum': _S87}
_S89 = {'value': _S88, 'witnesses': _S15}
_S90 = {'type': 'object', 'properties': _S89, 'required': _S17, 'additionalProperties': False}
_S91 = {'row_footnote_applicability': _S86, 'source_count_meaning': _S90, 'statistical_count': _S45, 'statistical_count_matches_sd': _S86, 'one_estimate_per_preparation': _S86, 'equal_weight_arithmetic_mean': _S86, 'sample_sd_n_minus_one': _S86, 'iid_common_mean_finite_variance': _S86, 'normal_sampling_units': _S86, 'reported_sd_summarizes_counted_preparation_estimates': _S86}
_S92 = ['row_footnote_applicability', 'source_count_meaning', 'statistical_count', 'statistical_count_matches_sd', 'one_estimate_per_preparation', 'equal_weight_arithmetic_mean', 'sample_sd_n_minus_one', 'iid_common_mean_finite_variance', 'normal_sampling_units', 'reported_sd_summarizes_counted_preparation_estimates']
_S93 = {'type': 'object', 'properties': _S91, 'required': _S92, 'additionalProperties': False}
_S94 = {'const': 'a105_summary_precision_scenario_v1'}
_S95 = ['source_statistical_count', 'one_per_physical_preparation']
_S96 = {'enum': _S95}
_S97 = ['one_estimate_per_preparation', 'reported_sd_summarizes_counted_preparation_estimates', 'equal_weight_arithmetic_mean', 'sample_sd_n_minus_one', 'iid_common_mean_finite_variance', 'normal_sampling_units']
_S98 = {'enum': _S97}
_S99 = {'type': 'array', 'items': _S98, 'uniqueItems': True}
_S100 = {'version': _S94, 'count_rule': _S96, 'stipulated_assumptions': _S99}
_S101 = ['version', 'count_rule', 'stipulated_assumptions']
_S102 = {'type': 'object', 'properties': _S100, 'required': _S101, 'additionalProperties': False}
_S103 = [_S102, _S19]
_S104 = {'anyOf': _S103}
_S105 = ['none', 'student_t_95']
_S106 = {'enum': _S105}
_S107 = {'version': _S0, 'kinetic_selection': _S81, 'interpretation': _S93, 'scenario': _S104, 'interval_request': _S106}
_S108 = ['version', 'kinetic_selection', 'interpretation', 'scenario', 'interval_request']
_S109 = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': _S107, 'required': _S108, 'additionalProperties': False}
_S110 = {'const': 'a105_kinetic_summary_precision_extraction_v1'}
_S111 = {'type': 'object', 'properties': _S107, 'required': _S108, 'additionalProperties': False}
_S112 = {'const': 'a105_kinetic_source_extraction_v3'}
_S113 = {'type': 'string', 'format': 'reference'}
_S114 = {'source_ref': _S2, 'representation': _S8, 'start': _S9, 'end': _S10, 'quote': _S11, 'artifact_ref': _S11}
_S115 = ['source_ref', 'representation', 'start', 'end', 'quote', 'artifact_ref']
_S116 = {'type': 'object', 'properties': _S114, 'required': _S115, 'additionalProperties': False}
_S117 = {'type': 'array', 'items': _S116}
_S118 = {'value': _S6, 'witnesses': _S117}
_S119 = {'type': 'object', 'properties': _S118, 'required': _S17, 'additionalProperties': False}
_S120 = [_S116, _S19]
_S121 = {'anyOf': _S120}
_S122 = {'organism': _S121, 'genotype': _S121, 'molecule': _S121, 'construct': _S121}
_S123 = {'type': 'object', 'properties': _S122, 'required': _S23, 'additionalProperties': False}
_S124 = {'substrate': _S121, 'preparation': _S121, 'experiment': _S121, 'experimental_system': _S121, 'conditions': _S121, 'endpoint': _S121, 'normalization': _S121}
_S125 = {'type': 'object', 'properties': _S124, 'required': _S26, 'additionalProperties': False}
_S126 = {'witness': _S116, 'number_start': _S9, 'number_end': _S10}
_S127 = {'type': 'object', 'properties': _S126, 'required': _S29, 'additionalProperties': False}
_S128 = {'type': 'number'}
_S129 = ['point', 'lt', 'le', 'gt', 'ge']
_S130 = {'enum': _S129}
_S131 = {'type': 'boolean'}
_S132 = {'selector': _S127, 'raw_number': _S11, 'value': _S128, 'relation': _S130, 'approximate': _S131}
_S133 = ['selector', 'raw_number', 'value', 'relation', 'approximate']
_S134 = {'type': 'object', 'properties': _S132, 'required': _S133, 'additionalProperties': False}
_S135 = [_S134, _S19]
_S136 = {'anyOf': _S135}
_S137 = ['uM', 'per_min', 'uM^-1min^-1']
_S138 = {'enum': _S137}
_S139 = [_S138, _S19]
_S140 = {'anyOf': _S139}
_S141 = [_S128, _S19]
_S142 = {'anyOf': _S141}
_S143 = ['unsupported_source_kinetic_unit']
_S144 = {'enum': _S143}
_S145 = [_S144, _S19]
_S146 = {'anyOf': _S145}
_S147 = {'witness': _S116, 'raw_unit': _S11, 'canonical_unit': _S140, 'multiplier': _S142, 'unavailable_reason': _S146}
_S148 = ['witness', 'raw_unit', 'canonical_unit', 'multiplier', 'unavailable_reason']
_S149 = {'type': 'object', 'properties': _S147, 'required': _S148, 'additionalProperties': False}
_S150 = [_S149, _S19]
_S151 = {'anyOf': _S150}
_S152 = {'value': _S37, 'witnesses': _S117}
_S153 = {'type': 'object', 'properties': _S152, 'required': _S17, 'additionalProperties': False}
_S154 = ['reported', 'synthetic']
_S155 = {'enum': _S154}
_S156 = {'value': _S41, 'witnesses': _S117}
_S157 = {'type': 'object', 'properties': _S156, 'required': _S17, 'additionalProperties': False}
_S158 = {'value': _S52, 'witnesses': _S117}
_S159 = {'type': 'object', 'properties': _S158, 'required': _S17, 'additionalProperties': False}
_S160 = {'value': _S59, 'witnesses': _S117}
_S161 = {'type': 'object', 'properties': _S160, 'required': _S17, 'additionalProperties': False}
_S162 = {'value': _S63, 'witnesses': _S117}
_S163 = {'type': 'object', 'properties': _S162, 'required': _S17, 'additionalProperties': False}
_S164 = {'statistic': _S157, 'unit_relationship': _S159, 'repetition_basis': _S161, 'estimate_basis': _S163}
_S165 = ['statistic', 'unit_relationship', 'repetition_basis', 'estimate_basis']
_S166 = {'type': 'object', 'properties': _S164, 'required': _S165, 'additionalProperties': False}
_S167 = {'witness': _S116, 'lower_start': _S9, 'lower_end': _S9, 'upper_start': _S9, 'upper_end': _S9}
_S168 = {'type': 'object', 'properties': _S167, 'required': _S47, 'additionalProperties': False}
_S169 = {'type': 'array', 'items': _S11, 'minItems': 2, 'maxItems': 2}
_S170 = {'type': 'array', 'items': _S128, 'minItems': 2, 'maxItems': 2}
_S171 = {'selector': _S168, 'raw_values': _S169, 'values': _S170}
_S172 = ['selector', 'raw_values', 'values']
_S173 = {'type': 'object', 'properties': _S171, 'required': _S172, 'additionalProperties': False}
_S174 = [_S173, _S19]
_S175 = {'anyOf': _S174}
_S176 = {'witness': _S116, 'value': _S128}
_S177 = ['witness', 'value']
_S178 = {'type': 'object', 'properties': _S176, 'required': _S177, 'additionalProperties': False}
_S179 = [_S178, _S19]
_S180 = {'anyOf': _S179}
_S181 = {'type': 'integer'}
_S182 = [_S181, _S19]
_S183 = {'anyOf': _S182}
_S184 = ['decimal_digits', 'english_cardinal', 'unsupported']
_S185 = {'enum': _S184}
_S186 = ['point', 'lt', 'le', 'gt', 'ge', 'unresolved']
_S187 = {'enum': _S186}
_S188 = [_S131, _S19]
_S189 = {'anyOf': _S188}
_S190 = ['exact', 'qualified', 'range_or_alternatives', 'unsupported', 'not_positive']
_S191 = {'enum': _S190}
_S192 = ['exact_count_qualified', 'count_range_or_alternatives', 'unsupported_count_literal', 'positive_count_required']
_S193 = {'enum': _S192}
_S194 = [_S193, _S19]
_S195 = {'anyOf': _S194}
_S196 = {'selector': _S127, 'raw_number': _S11, 'value': _S183, 'notation': _S185, 'relation': _S187, 'approximate': _S189, 'status': _S191, 'unavailable_reason': _S195}
_S197 = ['selector', 'raw_number', 'value', 'notation', 'relation', 'approximate', 'status', 'unavailable_reason']
_S198 = {'type': 'object', 'properties': _S196, 'required': _S197, 'additionalProperties': False}
_S199 = [_S198, _S19]
_S200 = {'anyOf': _S199}
_S201 = [_S170, _S19]
_S202 = {'anyOf': _S201}
_S203 = [_S10, _S19]
_S204 = {'anyOf': _S203}
_S205 = {'statistic': _S41, 'magnitude': _S142, 'interval': _S202, 'confidence_level': _S142, 'count': _S204, 'repetition_basis': _S59, 'estimate_basis': _S63}
_S206 = ['statistic', 'magnitude', 'interval', 'confidence_level', 'count', 'repetition_basis', 'estimate_basis']
_S207 = {'type': 'object', 'properties': _S205, 'required': _S206, 'additionalProperties': False}
_S208 = ['source_uncertainty_unit_unavailable', 'source_numeric_range']
_S209 = {'enum': _S208}
_S210 = [_S209, _S19]
_S211 = {'anyOf': _S210}
_S212 = {'meanings': _S166, 'magnitude': _S136, 'interval': _S175, 'unit': _S151, 'effective_unit': _S151, 'confidence_level': _S180, 'count': _S200, 'canonical': _S207, 'unavailable_reason': _S211}
_S213 = ['meanings', 'magnitude', 'interval', 'unit', 'effective_unit', 'confidence_level', 'count', 'canonical', 'unavailable_reason']
_S214 = {'type': 'object', 'properties': _S212, 'required': _S213, 'additionalProperties': False}
_S215 = ['Km', 'kcat', 'catalytic_efficiency']
_S216 = {'enum': _S215}
_S217 = ['point', 'censored', 'missing', 'conflicting']
_S218 = {'enum': _S217}
_S219 = ['eq', 'lt', 'le', 'gt', 'ge', 'none']
_S220 = {'enum': _S219}
_S221 = ['reported', 'graph_derived', 'calculated', 'synthetic']
_S222 = {'enum': _S221}
_S223 = [_S11, _S19]
_S224 = {'anyOf': _S223}
_S225 = {'organism': _S224, 'genotype': _S224, 'molecule': _S224, 'construct': _S224}
_S226 = {'type': 'object', 'properties': _S225, 'required': _S23, 'additionalProperties': False}
_S227 = {'substrate': _S224, 'preparation': _S224, 'experiment': _S224, 'experimental_system': _S224, 'conditions': _S224, 'endpoint': _S224, 'normalization': _S224}
_S228 = {'type': 'object', 'properties': _S227, 'required': _S26, 'additionalProperties': False}
_S229 = {'source_ref': _S2, 'artifact_ref': _S11, 'representation': _S8, 'start': _S9, 'end': _S10}
_S230 = ['source_ref', 'artifact_ref', 'representation', 'start', 'end']
_S231 = {'type': 'object', 'properties': _S229, 'required': _S230, 'additionalProperties': False}
_S232 = ['source_measurement_unreported', 'source_kinetic_unit_unreported', 'unsupported_source_kinetic_unit', 'source_operand_qualification_unknown', 'source_operand_qualification_conflicting', 'source_numeric_range']
_S233 = {'enum': _S232}
_S234 = [_S233, _S19]
_S235 = {'anyOf': _S234}
_S236 = {'parameter_kind': _S216, 'unit': _S140, 'value': _S142, 'status': _S218, 'relation': _S220, 'approximate': _S131, 'origin': _S222, 'measurement_id': _S11, 'physical_measurement_id': _S224, 'subject': _S226, 'context': _S228, 'uncertainty': _S207, 'source': _S231, 'unavailable_reason': _S235}
_S237 = ['parameter_kind', 'unit', 'value', 'status', 'relation', 'approximate', 'origin', 'measurement_id', 'physical_measurement_id', 'subject', 'context', 'uncertainty', 'source', 'unavailable_reason']
_S238 = {'type': 'object', 'properties': _S236, 'required': _S237, 'additionalProperties': False}
_S239 = [_S238, _S19]
_S240 = {'anyOf': _S239}
_S241 = {'type': 'array', 'items': _S11}
_S242 = {'parameter_kind': _S119, 'subject': _S123, 'context': _S125, 'measurement_identity': _S121, 'number': _S136, 'unit': _S151, 'qualification': _S153, 'approximate': _S131, 'source_origin': _S155, 'canonical_value': _S142, 'uncertainty': _S214, 'calculation_operand': _S240, 'unavailable_reasons': _S241}
_S243 = ['parameter_kind', 'subject', 'context', 'measurement_identity', 'number', 'unit', 'qualification', 'approximate', 'source_origin', 'canonical_value', 'uncertainty', 'calculation_operand', 'unavailable_reasons']
_S244 = {'type': 'object', 'properties': _S242, 'required': _S243, 'additionalProperties': False}
_S245 = {'numerator': _S244, 'denominator': _S19}
_S246 = ['numerator', 'denominator']
_S247 = {'type': 'object', 'properties': _S245, 'required': _S246, 'additionalProperties': False}
_S248 = {'value': _S72, 'witnesses': _S117}
_S249 = {'type': 'object', 'properties': _S248, 'required': _S17, 'additionalProperties': False}
_S250 = {'subject_relationship': _S249, 'parameter_definition_relationship': _S249, 'substrate_arrangement': _S249, 'comparison_scope': _S249, 'nonintended_conditions_relationship': _S249}
_S251 = {'type': 'object', 'properties': _S250, 'required': _S77, 'additionalProperties': False}
_S252 = {'const': 'a105_kinetic_contrast_inputs_v1'}
_S253 = {'version': _S252, 'subject_relationship': _S72, 'parameter_definition_relationship': _S72, 'substrate_arrangement': _S72, 'comparison_scope': _S72, 'nonintended_conditions_relationship': _S72, 'numerator': _S240, 'denominator': _S19}
_S254 = ['version', 'subject_relationship', 'parameter_definition_relationship', 'substrate_arrangement', 'comparison_scope', 'nonintended_conditions_relationship', 'numerator', 'denominator']
_S255 = {'type': 'object', 'properties': _S253, 'required': _S254, 'additionalProperties': False}
_S256 = {'numerator': _S241, 'denominator': _S241}
_S257 = {'type': 'object', 'properties': _S256, 'required': _S246, 'additionalProperties': False}
_S258 = {'type': 'array', 'items': _S113, 'uniqueItems': True}
_S259 = {'custody_module': _S11, 'custody_sha256': _S11, 'scalar_module': _S11, 'scalar_sha256': _S11, 'scalar_scope_module': _S11, 'scalar_scope_sha256': _S11}
_S260 = ['custody_module', 'custody_sha256', 'scalar_module', 'scalar_sha256', 'scalar_scope_module', 'scalar_scope_sha256']
_S261 = {'type': 'object', 'properties': _S259, 'required': _S260, 'additionalProperties': False}
_S262 = {'version': _S112, 'source_ref': _S113, 'source_kind': _S4, 'operands': _S247, 'comparison': _S251, 'calculation_inputs': _S255, 'input_unavailable_reasons': _S257, 'source_refs': _S258, 'implementation_dependencies': _S261}
_S263 = ['version', 'source_ref', 'source_kind', 'operands', 'comparison', 'calculation_inputs', 'input_unavailable_reasons', 'source_refs', 'implementation_dependencies']
_S264 = {'type': 'object', 'properties': _S262, 'required': _S263, 'additionalProperties': False}
_S265 = {'state': _S83, 'witnesses': _S117}
_S266 = {'type': 'object', 'properties': _S265, 'required': _S85, 'additionalProperties': False}
_S267 = {'value': _S88, 'witnesses': _S117}
_S268 = {'type': 'object', 'properties': _S267, 'required': _S17, 'additionalProperties': False}
_S269 = {'row_footnote_applicability': _S266, 'source_count_meaning': _S268, 'statistical_count': _S200, 'statistical_count_matches_sd': _S266, 'one_estimate_per_preparation': _S266, 'equal_weight_arithmetic_mean': _S266, 'sample_sd_n_minus_one': _S266, 'iid_common_mean_finite_variance': _S266, 'normal_sampling_units': _S266, 'reported_sd_summarizes_counted_preparation_estimates': _S266}
_S270 = {'type': 'object', 'properties': _S269, 'required': _S92, 'additionalProperties': False}
_S271 = {'const': 'a105_kinetic_summary_precision_inputs_v1'}
_S272 = ['source_measurement_unreported', 'source_kinetic_unit_unreported', 'unsupported_source_kinetic_unit', 'source_operand_qualification_unknown', 'source_operand_qualification_conflicting', 'source_numeric_range', 'source_parameter_kind_unknown', 'source_parameter_kind_conflicting']
_S273 = {'enum': _S272}
_S274 = [_S273, _S19]
_S275 = {'anyOf': _S274}
_S276 = {'type': 'string', 'pattern': '^(0|-?[1-9][0-9]*)$'}
_S277 = {'type': 'string', 'pattern': '^[1-9][0-9]*$'}
_S278 = {'numerator': _S276, 'denominator': _S277}
_S279 = {'type': 'object', 'properties': _S278, 'required': _S246, 'additionalProperties': False}
_S280 = [_S279, _S19]
_S281 = {'anyOf': _S280}
_S282 = {'row_footnote_applicability': _S83, 'statistical_count_matches_sd': _S83, 'one_estimate_per_preparation': _S83, 'equal_weight_arithmetic_mean': _S83, 'sample_sd_n_minus_one': _S83, 'iid_common_mean_finite_variance': _S83, 'normal_sampling_units': _S83, 'reported_sd_summarizes_counted_preparation_estimates': _S83}
_S283 = ['row_footnote_applicability', 'statistical_count_matches_sd', 'one_estimate_per_preparation', 'equal_weight_arithmetic_mean', 'sample_sd_n_minus_one', 'iid_common_mean_finite_variance', 'normal_sampling_units', 'reported_sd_summarizes_counted_preparation_estimates']
_S284 = {'type': 'object', 'properties': _S282, 'required': _S283, 'additionalProperties': False}
_S285 = [_S231, _S19]
_S286 = {'anyOf': _S285}
_S287 = {'parameter_source': _S286, 'spread_source': _S286, 'count_source': _S286, 'statistical_count_source': _S286, 'physical_measurement_id': _S224, 'parameter_unit_source': _S286, 'spread_unit_source': _S286}
_S288 = ['parameter_source', 'spread_source', 'count_source', 'statistical_count_source', 'physical_measurement_id', 'parameter_unit_source', 'spread_unit_source']
_S289 = {'type': 'object', 'properties': _S287, 'required': _S288, 'additionalProperties': False}
_S290 = ['explicit_source_unit', 'inherited_parameter_unit', 'unavailable']
_S291 = {'enum': _S290}
_S292 = {'version': _S271, 'source_kind': _S4, 'parameter_kind': _S6, 'source_origin': _S155, 'source_parameter_status': _S218, 'source_parameter_reason': _S275, 'parameter_approximate': _S131, 'parameter_native_exact': _S281, 'sd_native_exact': _S281, 'canonical_scale_exact': _S281, 'canonical_unit': _S140, 'uncertainty_statistic': _S41, 'uncertainty_reason': _S211, 'source_count': _S200, 'source_statistical_count': _S200, 'source_count_meaning': _S88, 'repetition_basis': _S59, 'estimate_basis': _S63, 'assessments': _S284, 'scenario': _S104, 'interval_request': _S106, 'dependencies': _S289, 'sd_scale_exact': _S281, 'sd_canonical_unit': _S140, 'sd_unit_basis': _S291}
_S293 = ['version', 'source_kind', 'parameter_kind', 'source_origin', 'source_parameter_status', 'source_parameter_reason', 'parameter_approximate', 'parameter_native_exact', 'sd_native_exact', 'canonical_scale_exact', 'canonical_unit', 'uncertainty_statistic', 'uncertainty_reason', 'source_count', 'source_statistical_count', 'source_count_meaning', 'repetition_basis', 'estimate_basis', 'assessments', 'scenario', 'interval_request', 'dependencies', 'sd_scale_exact', 'sd_canonical_unit', 'sd_unit_basis']
_S294 = {'type': 'object', 'properties': _S292, 'required': _S293, 'additionalProperties': False}
_S295 = {'version': _S110, 'selection': _S111, 'kinetic_extraction': _S264, 'interpretation': _S270, 'source_refs': _S258, 'calculation_inputs': _S294}
_S296 = ['version', 'selection', 'kinetic_extraction', 'interpretation', 'source_refs', 'calculation_inputs']
_S297 = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': _S295, 'required': _S296, 'additionalProperties': False}
_S298 = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': _S292, 'required': _S293, 'additionalProperties': False}
_S299 = {'const': 'a105_kinetic_summary_precision_sheet_v1'}
_S300 = {'const': 'A105'}
_S301 = {'const': 'source_kinetic_summary_precision'}
_S302 = {'$ref': '#/$defs/Cell'}
_S303 = {'$ref': '#/$defs/CellStates'}
_S304 = {'$ref': '#/$defs/SourceCellQualifications'}
_S305 = [_S302, _S303, _S304]
_S306 = {'const': 'summary_precision_reported_parameter'}
_S307 = {'$ref': '#/$defs/Unit_canonical'}
_S308 = {'$ref': '#/$defs/Value_number'}
_S309 = {'formula_code': _S306, 'unit': _S307, 'value': _S308}
_S310 = {'allOf': _S305, 'properties': _S309}
_S311 = {'const': 'summary_precision_reported_sd'}
_S312 = {'$ref': '#/$defs/Value_nonnegative'}
_S313 = {'formula_code': _S311, 'unit': _S307, 'value': _S312}
_S314 = {'allOf': _S305, 'properties': _S313}
_S315 = {'const': 'summary_precision_source_summary_count'}
_S316 = {'$ref': '#/$defs/Unit_count'}
_S317 = {'$ref': '#/$defs/Value_positive_integer'}
_S318 = {'formula_code': _S315, 'unit': _S316, 'value': _S317}
_S319 = {'allOf': _S305, 'properties': _S318}
_S320 = {'const': 'summary_precision_independent_preparation_count'}
_S321 = {'formula_code': _S320, 'unit': _S316, 'value': _S317}
_S322 = {'allOf': _S305, 'properties': _S321}
_S323 = {'const': 'summary_precision_statistical_estimator_count'}
_S324 = {'formula_code': _S323, 'unit': _S316, 'value': _S317}
_S325 = {'allOf': _S305, 'properties': _S324}
_S326 = {'const': 'summary_precision_relative_reported_sd'}
_S327 = {'$ref': '#/$defs/Unit_dimensionless'}
_S328 = {'formula_code': _S326, 'unit': _S327, 'value': _S312}
_S329 = {'allOf': _S305, 'properties': _S328}
_S330 = {'const': 'summary_precision_mean_variance'}
_S331 = {'$ref': '#/$defs/Unit_squared'}
_S332 = {'formula_code': _S330, 'unit': _S331, 'value': _S312}
_S333 = {'allOf': _S305, 'properties': _S332}
_S334 = {'const': 'summary_precision_mean_standard_error'}
_S335 = {'formula_code': _S334, 'unit': _S307, 'value': _S312}
_S336 = {'allOf': _S305, 'properties': _S335}
_S337 = {'const': 'summary_precision_relative_mean_standard_error'}
_S338 = {'formula_code': _S337, 'unit': _S327, 'value': _S312}
_S339 = {'allOf': _S305, 'properties': _S338}
_S340 = {'const': 'summary_precision_mean_interval_df'}
_S341 = {'formula_code': _S340, 'unit': _S316, 'value': _S317}
_S342 = {'allOf': _S305, 'properties': _S341}
_S343 = {'const': 'summary_precision_mean_interval_confidence_level'}
_S344 = {'$ref': '#/$defs/Value_confidence_95'}
_S345 = {'formula_code': _S343, 'unit': _S327, 'value': _S344}
_S346 = {'allOf': _S305, 'properties': _S345}
_S347 = {'const': 'summary_precision_mean_interval_t_multiplier'}
_S348 = {'$ref': '#/$defs/Value_positive'}
_S349 = {'formula_code': _S347, 'unit': _S327, 'value': _S348}
_S350 = {'allOf': _S305, 'properties': _S349}
_S351 = {'const': 'summary_precision_mean_interval_halfwidth'}
_S352 = {'formula_code': _S351, 'unit': _S307, 'value': _S348}
_S353 = {'allOf': _S305, 'properties': _S352}
_S354 = {'const': 'summary_precision_mean_interval_lower'}
_S355 = {'formula_code': _S354, 'unit': _S307, 'value': _S308}
_S356 = {'allOf': _S305, 'properties': _S355}
_S357 = {'const': 'summary_precision_mean_interval_upper'}
_S358 = {'formula_code': _S357, 'unit': _S307, 'value': _S308}
_S359 = {'allOf': _S305, 'properties': _S358}
_S360 = {'reported_parameter': _S310, 'reported_sd': _S314, 'source_summary_count': _S319, 'independent_preparation_count': _S322, 'statistical_estimator_count': _S325, 'relative_reported_sd': _S329, 'mean_variance': _S333, 'mean_standard_error': _S336, 'relative_mean_standard_error': _S339, 'mean_interval_df': _S342, 'mean_interval_confidence_level': _S346, 'mean_interval_t_multiplier': _S350, 'mean_interval_halfwidth': _S353, 'mean_interval_lower': _S356, 'mean_interval_upper': _S359}
_S361 = ['reported_parameter', 'reported_sd', 'source_summary_count', 'independent_preparation_count', 'statistical_estimator_count', 'relative_reported_sd', 'mean_variance', 'mean_standard_error', 'relative_mean_standard_error', 'mean_interval_df', 'mean_interval_confidence_level', 'mean_interval_t_multiplier', 'mean_interval_halfwidth', 'mean_interval_lower', 'mean_interval_upper']
_S362 = {'type': 'object', 'properties': _S360, 'required': _S361, 'additionalProperties': False}
_S363 = {'$ref': '#/$defs/ScenarioCellQualifications'}
_S364 = [_S302, _S303, _S363]
_S365 = {'allOf': _S364, 'properties': _S309}
_S366 = {'allOf': _S364, 'properties': _S313}
_S367 = {'allOf': _S364, 'properties': _S318}
_S368 = {'allOf': _S364, 'properties': _S321}
_S369 = {'allOf': _S364, 'properties': _S324}
_S370 = {'allOf': _S364, 'properties': _S328}
_S371 = {'allOf': _S364, 'properties': _S332}
_S372 = {'allOf': _S364, 'properties': _S335}
_S373 = {'allOf': _S364, 'properties': _S338}
_S374 = {'allOf': _S364, 'properties': _S341}
_S375 = {'allOf': _S364, 'properties': _S345}
_S376 = {'allOf': _S364, 'properties': _S349}
_S377 = {'allOf': _S364, 'properties': _S352}
_S378 = {'allOf': _S364, 'properties': _S355}
_S379 = {'allOf': _S364, 'properties': _S358}
_S380 = {'reported_parameter': _S365, 'reported_sd': _S366, 'source_summary_count': _S367, 'independent_preparation_count': _S368, 'statistical_estimator_count': _S369, 'relative_reported_sd': _S370, 'mean_variance': _S371, 'mean_standard_error': _S372, 'relative_mean_standard_error': _S373, 'mean_interval_df': _S374, 'mean_interval_confidence_level': _S375, 'mean_interval_t_multiplier': _S376, 'mean_interval_halfwidth': _S377, 'mean_interval_lower': _S378, 'mean_interval_upper': _S379}
_S381 = {'type': 'object', 'properties': _S380, 'required': _S361, 'additionalProperties': False}
_S382 = [_S381, _S19]
_S383 = {'anyOf': _S382}
_S384 = {'const': 'one_summary_precision_contribution'}
_S385 = {'type': 'array', 'items': _S231, 'uniqueItems': True}
_S386 = {'const': False}
_S387 = {'kind': _S384, 'dependency_sources': _S385, 'physical_measurement_id': _S224, 'independence_inferred': _S386}
_S388 = ['kind', 'dependency_sources', 'physical_measurement_id', 'independence_inferred']
_S389 = {'type': 'object', 'properties': _S387, 'required': _S388, 'additionalProperties': False}
_S390 = ['source_summaries_do_not_reconstruct_raw_measurements', 'physical_count_does_not_define_statistical_count', 'source_conditions_and_stipulations_distinct', 'random_precision_does_not_include_unknown_systematics', 'shared_calibration_does_not_shrink_with_preparation_count', 'dependent_precision_representations_not_independent_assays', 'measurement_repeatability_does_not_establish_physiological_specificity', 'no_cross_construct_contrast', 'no_assay_error_probability', 'no_target_transfer_or_annotation_credit']
_S391 = {'enum': _S390}
_S392 = {'type': 'array', 'items': _S391, 'uniqueItems': True}
_S393 = {'version': _S299, 'axis': _S300, 'evaluation_scope': _S301, 'inputs': _S294, 'source_cells': _S362, 'scenario_cells': _S383, 'contribution': _S389, 'limits': _S392, 'total_uncertainty': _S19, 'assay_error_probability': _S19, 'annotation_credit': _S19}
_S394 = ['version', 'axis', 'evaluation_scope', 'inputs', 'source_cells', 'scenario_cells', 'contribution', 'limits', 'total_uncertainty', 'assay_error_probability', 'annotation_credit']
_S395 = ['uM', 'per_min', 'uM^-1min^-1', 'uM_squared', 'per_min_squared', 'uM_inverse_squared_min_inverse_squared', 'dimensionless', 'count']
_S396 = {'enum': _S395}
_S397 = [_S396, _S19]
_S398 = {'anyOf': _S397}
_S399 = ['populated', 'unavailable']
_S400 = {'enum': _S399}
_S401 = ['source_reported', 'derived_source_supported_conditions', 'conditional_on_stipulated_assumptions', 'unavailable']
_S402 = {'enum': _S401}
_S403 = ['summary_precision_reported_parameter', 'summary_precision_reported_sd', 'summary_precision_source_summary_count', 'summary_precision_independent_preparation_count', 'summary_precision_statistical_estimator_count', 'summary_precision_relative_reported_sd', 'summary_precision_mean_variance', 'summary_precision_mean_standard_error', 'summary_precision_relative_mean_standard_error', 'summary_precision_mean_interval_df', 'summary_precision_mean_interval_confidence_level', 'summary_precision_mean_interval_t_multiplier', 'summary_precision_mean_interval_halfwidth', 'summary_precision_mean_interval_lower', 'summary_precision_mean_interval_upper']
_S404 = {'enum': _S403}
_S405 = ['reported', 'derived', 'proposed', 'synthetic']
_S406 = {'enum': _S405}
_S407 = ['source_measurement_unreported', 'source_kinetic_unit_unreported', 'unsupported_source_kinetic_unit', 'source_operand_qualification_unknown', 'source_operand_qualification_conflicting', 'source_numeric_range', 'source_uncertainty_unit_unavailable', 'censored_parameter', 'conflicting_parameter', 'reported_sd_unreported', 'reported_statistic_not_sd', 'source_summary_count_unreported', 'source_count_not_exact', 'row_footnote_applicability_unknown', 'row_footnote_applicability_conflicting', 'row_footnote_applicability_contradicted', 'physical_preparation_count_unknown', 'statistical_estimator_count_unknown', 'statistical_count_conflicting', 'statistical_count_sd_relationship_unknown', 'insufficient_estimator_count', 'sample_sd_convention_unknown', 'iid_model_unknown', 'mean_identity_unknown', 'normality_unknown', 'source_condition_contradicted', 'source_condition_conflicting', 'zero_parameter_for_relative_precision', 'interval_not_requested', 'positive_sd_required_for_student_t', 'scenario_assumption_conflicts_with_source', 'numerical_model_range', 'sd_preparation_estimator_ownership_unknown', 'source_parameter_kind_unknown', 'source_parameter_kind_conflicting']
_S408 = {'enum': _S407}
_S409 = [_S408, _S19]
_S410 = {'anyOf': _S409}
_S411 = {'value': _S142, 'unit': _S398, 'status': _S400, 'qualification': _S402, 'formula_code': _S404, 'origin': _S406, 'approximate': _S131, 'source_exact_value': _S281, 'conditional_on': _S99, 'stipulated_assumptions': _S99, 'unavailable_reason': _S410}
_S412 = ['value', 'unit', 'status', 'qualification', 'formula_code', 'origin', 'approximate', 'source_exact_value', 'conditional_on', 'stipulated_assumptions', 'unavailable_reason']
_S413 = {'type': 'object', 'properties': _S411, 'required': _S412, 'additionalProperties': False}
_S414 = {'const': 'populated'}
_S415 = {'not': _S19}
_S416 = ['source_reported', 'derived_source_supported_conditions', 'conditional_on_stipulated_assumptions']
_S417 = {'enum': _S416}
_S418 = {'status': _S414, 'value': _S128, 'unit': _S415, 'qualification': _S417, 'unavailable_reason': _S19}
_S419 = {'const': 'conditional_on_stipulated_assumptions'}
_S420 = {'qualification': _S419}
_S421 = {'properties': _S420}
_S422 = {'minItems': 1}
_S423 = {'stipulated_assumptions': _S422}
_S424 = {'properties': _S423}
_S425 = {'maxItems': 0}
_S426 = {'stipulated_assumptions': _S425}
_S427 = {'properties': _S426}
_S428 = {'if': _S421, 'then': _S424, 'else': _S427}
_S429 = [_S428]
_S430 = {'properties': _S418, 'allOf': _S429}
_S431 = {'const': 'unavailable'}
_S432 = {'status': _S431, 'value': _S19, 'qualification': _S431, 'source_exact_value': _S19, 'unavailable_reason': _S415}
_S433 = {'properties': _S432}
_S434 = [_S430, _S433]
_S435 = {'oneOf': _S434}
_S436 = ['source_reported', 'derived_source_supported_conditions', 'unavailable']
_S437 = {'enum': _S436}
_S438 = {'qualification': _S437, 'stipulated_assumptions': _S425}
_S439 = {'properties': _S438}
_S440 = {'qualification': _S402}
_S441 = {'properties': _S440}
_S442 = ['uM', 'per_min', 'uM^-1min^-1', None]
_S443 = {'enum': _S442}
_S444 = ['uM_squared', 'per_min_squared', 'uM_inverse_squared_min_inverse_squared', None]
_S445 = {'enum': _S444}
_S446 = {'const': 'count'}
_S447 = {'const': 'dimensionless'}
_S448 = {'type': 'number', 'minimum': 0}
_S449 = [_S448, _S19]
_S450 = {'anyOf': _S449}
_S451 = {'type': 'number', 'exclusiveMinimum': 0}
_S452 = [_S451, _S19]
_S453 = {'anyOf': _S452}
_S454 = {'const': 0.95}
_S455 = [_S454, _S19]
_S456 = {'anyOf': _S455}
_S457 = {'Cell': _S413, 'CellStates': _S435, 'SourceCellQualifications': _S439, 'ScenarioCellQualifications': _S441, 'Unit_canonical': _S443, 'Unit_squared': _S445, 'Unit_count': _S446, 'Unit_dimensionless': _S447, 'Value_number': _S142, 'Value_nonnegative': _S450, 'Value_positive': _S453, 'Value_positive_integer': _S204, 'Value_confidence_95': _S456}
_S458 = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': _S393, 'required': _S394, 'additionalProperties': False, '$defs': _S457}

_SCHEMAS = {'selection': _S109, 'extraction': _S297, 'inputs': _S298, 'sheet': _S458}

VERSION = 'a105_kinetic_summary_precision_extraction_v1'
SELECTION_VERSION = 'a105_kinetic_summary_precision_selection_v1'
INPUT_VERSION = 'a105_kinetic_summary_precision_inputs_v1'
ASSUMPTIONS = (
    'one_estimate_per_preparation',
    'reported_sd_summarizes_counted_preparation_estimates',
    'equal_weight_arithmetic_mean', 'sample_sd_n_minus_one',
    'iid_common_mean_finite_variance', 'normal_sampling_units',
)
ASSESSMENTS = ('row_footnote_applicability', 'statistical_count_matches_sd', *ASSUMPTIONS)


def _schema(name):
    return deepcopy(_SCHEMAS[name])


def summary_precision_arguments_schema():
    return _schema('selection')


def summary_precision_extraction_schema():
    return _schema('extraction')


def _fail(code, field, *, detail=None):
    raise ExperimentalContractError(code, field, detail=detail)


def _check(value, schema, field):
    try:
        validate_schema(value, schema)
    except ContractError as error:
        _fail('summary_precision_schema_invalid', field, detail=error.detail)


def _rational(value):
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}


def _fraction(value, field):
    if value is None:
        return None
    try:
        result = Fraction(int(value['numerator']), int(value['denominator']))
    except (ValueError, ZeroDivisionError, OverflowError) as error:
        raise ExperimentalContractError('canonical_reduced_rational_required', field) from error
    if _rational(result) != value:
        _fail('canonical_reduced_rational_required', field)
    return result


def _locator(witness):
    return None if witness is None else {k: witness[k] for k in (
        'source_ref', 'artifact_ref', 'representation', 'start', 'end')}


def _number_locator(number):
    if number is None:
        return None
    selector = number['selector']
    witness = selector['witness']
    result = _locator(witness)
    result['start'] += len(witness['quote'][:selector['number_start']].encode('utf-8'))
    result['end'] = witness['start'] + len(witness['quote'][:selector['number_end']].encode('utf-8'))
    return result


def _meaning(selected, sources, field, *, count=False):
    witnesses = [sources.witness(w, field + '.witnesses') for w in selected['witnesses']]
    value = selected['value' if count else 'state']
    minimum = (2 if value == 'conflicting' else 0 if value == 'unknown' else 1)
    if len({canonical(_locator(w)) for w in witnesses}) < minimum:
        _fail('interpretation_witness_required', field)
    return {'value' if count else 'state': value, 'witnesses': witnesses}


def _quantity_scale(unit, kind):
    if kind not in _UNIT_TABLES or unit is None or unit['canonical_unit'] is None:
        return None
    return _UNIT_TABLES[kind][_normalize(unit['raw_unit'])][1]


def _project_inputs(kinetic, interpreted, scenario, interval_request):
    row = kinetic['operands']['numerator']
    kind = row['parameter_kind']['value']
    op, unc = row['calculation_operand'], row['uncertainty']
    punit, sunit = row['unit'], unc['effective_unit']
    ps, ss = _quantity_scale(punit, kind), _quantity_scale(sunit, kind)
    relationship = unc['meanings']['unit_relationship']['value']
    def exact(number):
        return None if number is None else _rational(_literal_fraction(number['raw_number']))
    return {
        'version': INPUT_VERSION, 'source_kind': kinetic['source_kind'],
        'parameter_kind': kind, 'source_origin': row['source_origin'],
        'source_parameter_status': op['status'] if op else 'conflicting' if kind == 'conflicting' else 'missing',
        'source_parameter_reason': op['unavailable_reason'] if op else 'source_parameter_kind_' + kind,
        'parameter_approximate': row['approximate'],
        'parameter_native_exact': exact(row['number']),
        'sd_native_exact': exact(unc['magnitude']) if unc['canonical']['statistic'] == 'sd' else None,
        'canonical_scale_exact': None if ps is None else _rational(ps),
        'canonical_unit': punit['canonical_unit'] if punit else None,
        'sd_scale_exact': None if ss is None else _rational(ss),
        'sd_canonical_unit': sunit['canonical_unit'] if sunit else None,
        'sd_unit_basis': ('explicit_source_unit' if relationship == 'explicit_unit'
                          else 'inherited_parameter_unit') if ss is not None else 'unavailable',
        'uncertainty_statistic': unc['canonical']['statistic'],
        'uncertainty_reason': unc['unavailable_reason'],
        'source_count': deepcopy(unc['count']),
        'source_statistical_count': deepcopy(interpreted['statistical_count']),
        'source_count_meaning': interpreted['source_count_meaning']['value'],
        'repetition_basis': unc['canonical']['repetition_basis'],
        'estimate_basis': unc['canonical']['estimate_basis'],
        'assessments': {k: interpreted[k]['state'] for k in ASSESSMENTS},
        'scenario': deepcopy(scenario), 'interval_request': interval_request,
        'dependencies': {
            'parameter_source': _number_locator(row['number']),
            'spread_source': _number_locator(unc['magnitude']),
            'count_source': _number_locator(unc['count']),
            'statistical_count_source': _number_locator(interpreted['statistical_count']),
            'physical_measurement_id': op['physical_measurement_id'] if op else None,
            'parameter_unit_source': _locator(punit['witness']) if punit else None,
            'spread_unit_source': _locator(sunit['witness']) if sunit else None,
        },
    }


def _validate_count(count, field):
    if count is None:
        return
    selector = count['selector']
    quote = selector['witness']['quote']
    start, end = selector['number_start'], selector['number_end']
    if not 0 <= start < end <= len(quote) or quote[start:end] != count['raw_number']:
        _fail('source_count_token_mismatch', field)
    raw = count['raw_number']
    parsed = (int(raw.replace('−', '-')) if re.fullmatch(r'[-−]?[0-9]+', raw)
              else _cardinal_count(raw))
    if count['status'] not in ('range_or_alternatives', 'unsupported') and parsed != count['value']:
        _fail('source_count_value_mismatch', field)
    if count['status'] == 'exact' and (
            type(count['value']) is not int or count['value'] < 1
            or count['relation'] != 'point' or count['approximate'] is not False
            or count['unavailable_reason'] is not None):
        _fail('exact_positive_count_required', field)
    reasons = {'qualified': 'exact_count_qualified',
        'range_or_alternatives': 'count_range_or_alternatives',
        'unsupported': 'unsupported_count_literal', 'not_positive': 'positive_count_required'}
    if count['status'] in reasons and count['unavailable_reason'] != reasons[count['status']]:
        _fail('count_status_reason_mismatch', field)
    if count['status'] in ('range_or_alternatives', 'unsupported') and count['value'] is not None:
        _fail('unavailable_count_must_be_null', field)
    if count['status'] == 'not_positive' and (count['value'] is None or count['value'] > 0):
        _fail('count_status_reason_mismatch', field)


def _validate_input_relationships(inputs):
    """Validate the detached scientific contract, without claiming source custody."""
    _check(inputs, _SCHEMAS['inputs'], 'inputs')
    kind = inputs['parameter_kind']
    known_kind = kind in _UNIT_TABLES
    quantities = {k: _fraction(inputs[k], k) for k in (
        'parameter_native_exact', 'sd_native_exact', 'canonical_scale_exact', 'sd_scale_exact')}
    if quantities['sd_native_exact'] is not None and quantities['sd_native_exact'] < 0:
        _fail('nonnegative_sd_required', 'sd_native_exact')
    expected = {'Km': 'uM', 'kcat': 'per_min', 'catalytic_efficiency': 'uM^-1min^-1'}.get(kind)
    if not known_kind:
        if (inputs['source_parameter_reason'] != 'source_parameter_kind_' + kind
                or inputs['source_parameter_status'] != ('conflicting' if kind == 'conflicting' else 'missing')):
            _fail('unresolved_parameter_kind_status_mismatch', 'parameter_kind')
        if any(inputs[k] is not None for k in (
                'canonical_unit', 'canonical_scale_exact', 'sd_canonical_unit', 'sd_scale_exact')):
            _fail('unresolved_parameter_kind_cannot_supply_dimension', 'parameter_kind')
    if (inputs['canonical_unit'] is not None and inputs['sd_canonical_unit'] is not None
            and inputs['canonical_unit'] != inputs['sd_canonical_unit']):
        _fail('parameter_sd_canonical_dimension_mismatch', 'sd_canonical_unit')
    for scale_field, unit_field, dependency in (
        ('canonical_scale_exact', 'canonical_unit', 'parameter_unit_source'),
        ('sd_scale_exact', 'sd_canonical_unit', 'spread_unit_source')):
        scale, unit = quantities[scale_field], inputs[unit_field]
        if (scale is None) != (unit is None):
            _fail('quantity_unit_scale_mismatch', unit_field)
        if unit is not None:
            if not known_kind or unit != expected or scale not in {v[1] for v in _UNIT_TABLES[kind].values()}:
                _fail('source_kinetic_scale_dimension_mismatch', unit_field)
            if inputs['dependencies'][dependency] is None:
                _fail('quantity_unit_source_required', dependency)
    basis = inputs['sd_unit_basis']
    if (basis == 'unavailable') != (quantities['sd_scale_exact'] is None):
        _fail('sd_unit_basis_mismatch', 'sd_unit_basis')
    if basis == 'inherited_parameter_unit' and (
            inputs['canonical_unit'] is None
            or quantities['sd_scale_exact'] != quantities['canonical_scale_exact']
            or inputs['sd_canonical_unit'] != inputs['canonical_unit']
            or inputs['dependencies']['parameter_unit_source'] != inputs['dependencies']['spread_unit_source']):
        _fail('known_matching_parameter_unit_required', 'sd_unit_basis')
    status, reason = inputs['source_parameter_status'], inputs['source_parameter_reason']
    if status in ('point', 'censored'):
        if reason is not None or quantities['parameter_native_exact'] is None or inputs['canonical_unit'] is None:
            _fail('source_parameter_status_mismatch', 'source_parameter_status')
    elif reason is None:
        _fail('source_parameter_reason_required', 'source_parameter_reason')
    if reason in ('source_kinetic_unit_unreported', 'unsupported_source_kinetic_unit') and inputs['canonical_unit'] is not None:
        _fail('unavailable_parameter_unit_must_be_null', 'canonical_unit')
    if inputs['uncertainty_reason'] == 'source_uncertainty_unit_unavailable' and inputs['sd_canonical_unit'] is not None:
        _fail('unavailable_sd_unit_must_be_null', 'sd_canonical_unit')
    if inputs['uncertainty_statistic'] in ('ci', 'unreported') and quantities['sd_native_exact'] is not None:
        _fail('source_uncertainty_representation_mismatch', 'sd_native_exact')
    if inputs['source_kind'] == 'synthetic_fixture' and inputs['source_origin'] != 'synthetic':
        _fail('synthetic_origin_required', 'source_origin')
    for name, dependency in (
        ('parameter_native_exact', 'parameter_source'), ('sd_native_exact', 'spread_source'),
        ('source_count', 'count_source'), ('source_statistical_count', 'statistical_count_source')):
        if inputs[name] is not None and inputs['dependencies'][dependency] is None:
            _fail('source_operand_locator_required', dependency)
    for name in ('source_count', 'source_statistical_count'):
        _validate_count(inputs[name], name)
    if (inputs['source_statistical_count'] is None
            and inputs['assessments']['statistical_count_matches_sd'] != 'unknown'):
        _fail('separate_statistical_count_required', 'statistical_count_matches_sd')
    for name, locator in inputs['dependencies'].items():
        if name == 'physical_measurement_id' or locator is None:
            continue
        if locator['start'] >= locator['end']:
            _fail('nonempty_source_span_required', 'dependencies.' + name)
    scenario = inputs['scenario']
    if scenario is not None:
        for code in scenario['stipulated_assumptions']:
            if inputs['assessments'][code] == 'source_supported':
                _fail('redundant_stipulated_assumption', 'scenario.' + code)
    return deepcopy(inputs)


def read_kinetic_summary_precision_inputs(selection, *, read_source):
    """Reuse source reading, authenticate extra meanings, preserve one summary.

    Unknown physical-to-estimator relationships remain unknown source facts.
    Explicit scenario assumptions are retained separately and never change them.
    """
    _check(selection, _SCHEMAS['selection'], 'selection')
    sources = _Sources(read_source)
    kinetic = read_kinetic_inputs(selection['kinetic_selection'], read_source=sources.source)
    interpreted = {}
    for key, selected in selection['interpretation'].items():
        if key == 'statistical_count':
            interpreted[key] = _count_reading(selected, sources)
        else:
            interpreted[key] = _meaning(selected, sources, 'interpretation.' + key,
                                        count=key == 'source_count_meaning')
    inputs = _project_inputs(kinetic, interpreted, selection['scenario'], selection['interval_request'])
    inputs = _validate_input_relationships(inputs)
    result = {'version': VERSION, 'selection': deepcopy(selection),
        'kinetic_extraction': kinetic, 'interpretation': interpreted,
        'source_refs': list(sources.references), 'calculation_inputs': inputs}
    _check(result, _SCHEMAS['extraction'], 'extraction')
    return deepcopy(result)


def validate_kinetic_summary_precision_extraction(extraction, *, read_source):
    """Rebuild the entire retained extraction from its authorized source bytes."""
    _check(extraction, _SCHEMAS['extraction'], 'extraction')
    expected = read_kinetic_summary_precision_inputs(extraction['selection'], read_source=read_source)
    if canonical(expected) != canonical(extraction):
        _fail('detached_source_operand_mismatch', 'extraction')
    return expected


__all__ = ['VERSION', 'SELECTION_VERSION', 'INPUT_VERSION', 'ASSUMPTIONS', 'ASSESSMENTS',
    'summary_precision_arguments_schema', 'summary_precision_extraction_schema',
    'read_kinetic_summary_precision_inputs', 'validate_kinetic_summary_precision_extraction']
