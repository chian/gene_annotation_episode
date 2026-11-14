"""Source-bound concentration windows; pure reading and typed compilation.

The scientific episode supplies witnessed meanings. Custody and deterministic
arithmetic do not establish those meanings or target correspondence. Schema
resources are the exact private-interface release002, embedded without IO.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import html
import io
import json
import math
import re
import sqlite3
import xml.etree.ElementTree as ET
import zipfile

from .domain import ContractError, validate_schema
from .literature_assay_inputs import _Sources
from .literature_experimental_contracts import ExperimentalContractError
from .literature_product_partition_inputs import _number as _lexical_number
from .literature_rate_native_inputs import _field_contexts
from .literature_measurement_validation_inputs import _associate, _table_cells, _visible_span
from .literature_partner_source_fields import _unit_continuation, _soft_break_numeric_token
from .spreadsheet_tools import Workbook

# Generated from the unchanged reviewed SCHEMAS_002 resources. Definitions are
# shared exactly; factories reconstitute each original resource, including $id.
_SCHEMA_RESOURCES = {
    'SELECTION': ({'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': 'urn:a105:concentration-window:275:proposal002:selection', 'type': 'object', 'properties': {'version': {'const': 'a105_concentration_window_selection_v2'}, 'source_ref': {'type': 'string', 'minLength': 1}, 'source_kind': {'enum': ['primary_source', 'retained_extraction', 'graph_extraction', 'synthetic_fixture']}, 'assay': {'$ref': '#/$defs/assay'}, 'grid': {'anyOf': [{'$ref': '#/$defs/grid'}, {'type': 'null'}]}, 'quantities': {'type': 'object', 'properties': {'substrate_start': {'anyOf': [{'$ref': '#/$defs/quantity'}, {'type': 'null'}]}, 'substrate_end': {'anyOf': [{'$ref': '#/$defs/quantity'}, {'type': 'null'}]}, 'total_product_start': {'anyOf': [{'$ref': '#/$defs/quantity'}, {'type': 'null'}]}, 'total_product_end': {'anyOf': [{'$ref': '#/$defs/quantity'}, {'type': 'null'}]}, 'fate_product_start': {'anyOf': [{'$ref': '#/$defs/quantity'}, {'type': 'null'}]}, 'fate_product_end': {'anyOf': [{'$ref': '#/$defs/quantity'}, {'type': 'null'}]}, 'coordinate_start': {'anyOf': [{'$ref': '#/$defs/quantity'}, {'type': 'null'}]}, 'coordinate_end': {'anyOf': [{'$ref': '#/$defs/quantity'}, {'type': 'null'}]}}, 'required': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end'], 'additionalProperties': False}, 'stoichiometry': {'type': 'object', 'properties': {'substrate': {'anyOf': [{'$ref': '#/$defs/coefficient'}, {'type': 'null'}]}, 'total_product': {'anyOf': [{'$ref': '#/$defs/coefficient'}, {'type': 'null'}]}, 'fate_product': {'anyOf': [{'$ref': '#/$defs/coefficient'}, {'type': 'null'}]}}, 'required': ['substrate', 'total_product', 'fate_product'], 'additionalProperties': False}, 'timing': {'$ref': '#/$defs/timing'}, 'covariance_source_ref': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'null'}]}, 'covariance_material': {'enum': ['closed_joint_estimator_covariance_document', 'unsupported_observation_table', 'not_selected']}, 'evidence': {'type': 'array', 'items': {'type': 'object', 'properties': {'role': {'enum': ['chemical_relation', 'product_identity', 'normalization', 'calibration', 'blank', 'replication', 'uncertainty', 'alternative_contribution', 'preparation_change', 'timing']}, 'witness': {'$ref': '#/$defs/field'}}, 'required': ['role', 'witness'], 'additionalProperties': False}}, 'requested_cells': {'type': 'array', 'items': {'enum': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end', 'substrate_loss', 'total_product_gain', 'fate_product_gain', 'coordinate_span', 'chemical_discrepancy', 'chemical_ratio', 'chemical_relative_discrepancy', 'fate_fraction', 'substrate_depletion_fraction', 'source_interval_average_substrate', 'scenario_interval_average_substrate', 'source_interval_average_total_product', 'scenario_interval_average_total_product', 'source_interval_average_fate_product', 'scenario_interval_average_fate_product', 'substrate_loss_variance', 'total_product_gain_variance', 'fate_product_gain_variance', 'coordinate_span_variance', 'chemical_discrepancy_variance', 'chemical_ratio_variance', 'fate_fraction_variance', 'source_interval_average_substrate_variance', 'source_interval_average_total_product_variance', 'source_interval_average_fate_product_variance', 'chemical_standardized_discrepancy']}, 'uniqueItems': True}, 'pair_relationships': {'$ref': '#/$defs/pair_relationships'}, 'cross_relationships': {'$ref': '#/$defs/cross_relationships'}}, 'required': ['version', 'source_ref', 'source_kind', 'assay', 'grid', 'quantities', 'stoichiometry', 'timing', 'covariance_source_ref', 'covariance_material', 'evidence', 'requested_cells', 'pair_relationships', 'cross_relationships'], 'additionalProperties': False}, ['assay', 'coefficient', 'cross_relationships', 'field', 'grid', 'number_selector', 'pair_relationships', 'quantity', 'relationship', 'text_field', 'timing', 'xlsx_field']),
    'EXTRACTION': ({'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': 'urn:a105:concentration-window:275:proposal002:extraction', 'type': 'object', 'properties': {'version': {'const': 'a105_concentration_window_extraction_v2'}, 'selection': {'$ref': '#/$defs/selection'}, 'quantities': {'type': 'object', 'properties': {'substrate_start': {'anyOf': [{'$ref': '#/$defs/reading'}, {'type': 'null'}]}, 'substrate_end': {'anyOf': [{'$ref': '#/$defs/reading'}, {'type': 'null'}]}, 'total_product_start': {'anyOf': [{'$ref': '#/$defs/reading'}, {'type': 'null'}]}, 'total_product_end': {'anyOf': [{'$ref': '#/$defs/reading'}, {'type': 'null'}]}, 'fate_product_start': {'anyOf': [{'$ref': '#/$defs/reading'}, {'type': 'null'}]}, 'fate_product_end': {'anyOf': [{'$ref': '#/$defs/reading'}, {'type': 'null'}]}, 'coordinate_start': {'anyOf': [{'$ref': '#/$defs/reading'}, {'type': 'null'}]}, 'coordinate_end': {'anyOf': [{'$ref': '#/$defs/reading'}, {'type': 'null'}]}}, 'required': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end'], 'additionalProperties': False}, 'coefficients': {'type': 'object', 'properties': {'substrate': {'$ref': '#/$defs/coefficient_reading'}, 'total_product': {'$ref': '#/$defs/coefficient_reading'}, 'fate_product': {'$ref': '#/$defs/coefficient_reading'}}, 'required': ['substrate', 'total_product', 'fate_product'], 'additionalProperties': False}, 'covariance': {'anyOf': [{'$ref': '#/$defs/covariance_reading'}, {'type': 'null'}]}, 'source_artifacts': {'type': 'array', 'items': {'$ref': '#/$defs/artifact'}}, 'selection_digest': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'scientific_context': {'$ref': '#/$defs/scientific_context'}}, 'required': ['version', 'selection', 'quantities', 'coefficients', 'covariance', 'source_artifacts', 'selection_digest', 'scientific_context'], 'additionalProperties': False}, ['artifact', 'assay', 'coefficient', 'coefficient_reading', 'covariance_document', 'covariance_reading', 'cross_relationships', 'exact', 'field', 'field_binding', 'grid', 'location', 'number_selector', 'pair_relationships', 'quantity', 'reading', 'reasons', 'relationship', 'scientific_assay', 'scientific_coefficient', 'scientific_context', 'scientific_cross_relationships', 'scientific_field', 'scientific_pair_relationships', 'scientific_quantity', 'scientific_timing', 'selection', 'text_field', 'timing', 'xlsx_field']),
    'CALCULATION_INPUTS': ({'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': 'urn:a105:concentration-window:275:proposal003:calculation_inputs', 'type': 'object', 'properties': {'version': {'const': 'a105_concentration_window_calculation_inputs_v3'}, 'extraction_digest': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'source_kind': {'enum': ['primary_source', 'retained_extraction', 'graph_extraction', 'synthetic_fixture']}, 'quantities': {'type': 'object', 'properties': {'substrate_start': {'anyOf': [{'$ref': '#/$defs/reading'}, {'type': 'null'}]}, 'substrate_end': {'anyOf': [{'$ref': '#/$defs/reading'}, {'type': 'null'}]}, 'total_product_start': {'anyOf': [{'$ref': '#/$defs/reading'}, {'type': 'null'}]}, 'total_product_end': {'anyOf': [{'$ref': '#/$defs/reading'}, {'type': 'null'}]}, 'fate_product_start': {'anyOf': [{'$ref': '#/$defs/reading'}, {'type': 'null'}]}, 'fate_product_end': {'anyOf': [{'$ref': '#/$defs/reading'}, {'type': 'null'}]}, 'coordinate_start': {'anyOf': [{'$ref': '#/$defs/reading'}, {'type': 'null'}]}, 'coordinate_end': {'anyOf': [{'$ref': '#/$defs/reading'}, {'type': 'null'}]}}, 'required': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end'], 'additionalProperties': False}, 'coefficients': {'type': 'object', 'properties': {'substrate': {'$ref': '#/$defs/coefficient_reading'}, 'total_product': {'$ref': '#/$defs/coefficient_reading'}, 'fate_product': {'$ref': '#/$defs/coefficient_reading'}}, 'required': ['substrate', 'total_product', 'fate_product'], 'additionalProperties': False}, 'covariance': {'anyOf': [{'$ref': '#/$defs/covariance_reading'}, {'type': 'null'}]}, 'covariance_material': {'enum': ['closed_joint_estimator_covariance_document', 'unsupported_observation_table', 'not_selected']}, 'requested_cells': {'type': 'array', 'items': {'enum': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end', 'substrate_loss', 'total_product_gain', 'fate_product_gain', 'coordinate_span', 'chemical_discrepancy', 'chemical_ratio', 'chemical_relative_discrepancy', 'fate_fraction', 'substrate_depletion_fraction', 'source_interval_average_substrate', 'scenario_interval_average_substrate', 'source_interval_average_total_product', 'scenario_interval_average_total_product', 'source_interval_average_fate_product', 'scenario_interval_average_fate_product', 'substrate_loss_variance', 'total_product_gain_variance', 'fate_product_gain_variance', 'coordinate_span_variance', 'chemical_discrepancy_variance', 'chemical_ratio_variance', 'fate_fraction_variance', 'source_interval_average_substrate_variance', 'source_interval_average_total_product_variance', 'source_interval_average_fate_product_variance', 'chemical_standardized_discrepancy']}, 'uniqueItems': True}, 'source_artifacts': {'type': 'array', 'items': {'$ref': '#/$defs/artifact'}}, 'selection_digest': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'scientific_context': {'$ref': '#/$defs/scientific_context'}, 'covariance_context': {'$ref': '#/$defs/covariance_context'}}, 'required': ['version', 'extraction_digest', 'source_kind', 'quantities', 'coefficients', 'covariance', 'covariance_material', 'requested_cells', 'source_artifacts', 'selection_digest', 'scientific_context', 'covariance_context'], 'additionalProperties': False}, ['artifact', 'coefficient_reading', 'covariance_document', 'covariance_reading', 'exact', 'field', 'field_binding', 'location', 'reading', 'reasons', 'scientific_assay', 'scientific_coefficient', 'scientific_context', 'scientific_cross_relationships', 'scientific_field', 'scientific_pair_relationships', 'scientific_quantity', 'scientific_timing', 'text_field', 'xlsx_field', 'covariance_context']),
    'SHEET': ({'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': 'urn:a105:concentration-window:275:proposal003:sheet', 'type': 'object', 'properties': {'version': {'const': 'a105_concentration_window_sheet_v3'}, 'axis': {'const': 'A105'}, 'section': {'const': 'observed_concentration_window'}, 'cells': {'type': 'array', 'items': {'$ref': '#/$defs/cell'}}, 'assertion_resolution': {'enum': ['total_chemical_extent_and_selected_product_fate']}, 'source_artifacts': {'type': 'array', 'items': {'$ref': '#/$defs/artifact'}}, 'estimate_bindings': {'type': 'array', 'items': {'type': 'object', 'properties': {'role': {'enum': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end']}, 'owner_key': {'type': 'string', 'minLength': 1}, 'physical_owner_key': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'null'}]}, 'dependency_keys': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'uniqueItems': True}}, 'required': ['role', 'owner_key', 'physical_owner_key', 'dependency_keys'], 'additionalProperties': False}}, 'derived_covariance': {'anyOf': [{'type': 'object', 'properties': {'components': {'type': 'array', 'items': {'enum': ['substrate_loss', 'total_product_gain', 'fate_product_gain', 'coordinate_span', 'chemical_discrepancy', 'chemical_ratio', 'fate_fraction', 'source_interval_average_substrate', 'source_interval_average_total_product', 'source_interval_average_fate_product']}, 'uniqueItems': True}, 'matrix': {'type': 'array', 'items': {'type': 'array', 'items': {'type': 'number'}}}, 'method': {'const': 'G*C*G_transpose'}, 'covariance_source_ref': {'type': 'string', 'minLength': 1}}, 'required': ['components', 'matrix', 'method', 'covariance_source_ref'], 'additionalProperties': False}, {'type': 'null'}]}, 'limits': {'type': 'array', 'items': {'enum': ['observed_source_scale_not_blank_corrected', 'no_unique_molecular_attribution', 'unknown_calibration_systematics', 'no_independent_replication_inferred', 'shared_derived_contribution', 'interval_average_not_initial_or_turnover_rate', 'no_cumulative_amount_from_initial_volume', 'selected_integration_unimplemented', 'general_reliability_compilation_unfinished', 'no_target_transfer_or_W05']}, 'uniqueItems': True}, 'annotation_credit': {'type': 'null'}, 'scientific_context': {'$ref': '#/$defs/scientific_context'}, 'association': {'$ref': '#/$defs/association'}, 'covariance_context': {'$ref': '#/$defs/covariance_context'}}, 'required': ['version', 'axis', 'section', 'cells', 'assertion_resolution', 'source_artifacts', 'estimate_bindings', 'derived_covariance', 'limits', 'annotation_credit', 'scientific_context', 'association', 'covariance_context'], 'additionalProperties': False}, ['artifact', 'association', 'cell', 'exact', 'field_binding', 'reasons', 'scientific_assay', 'scientific_coefficient', 'scientific_context', 'scientific_cross_relationships', 'scientific_field', 'scientific_pair_relationships', 'scientific_quantity', 'scientific_timing', 'covariance_context']),
    'COVARIANCE_DOCUMENT': ({'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': 'urn:a105:concentration-window:275:proposal002:covariance_document', 'type': 'object', 'properties': {'version': {'const': 'a105_concentration_window_covariance_v1'}, 'roles': {'type': 'array', 'items': {'enum': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end']}, 'uniqueItems': True}, 'owner_keys': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}}, 'units': {'type': 'array', 'items': {'enum': ['uM', 's']}}, 'dependency_keys': {'type': 'array', 'items': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'uniqueItems': True}}, 'covariance': {'anyOf': [{'type': 'array', 'items': {'type': 'array', 'items': {'type': 'number'}}}, {'type': 'null'}]}, 'basis': {'const': 'joint_covariance_of_selected_estimates'}, 'variance_status': {'enum': ['known', 'estimated', 'unknown']}, 'origin': {'enum': ['reported', 'derived', 'synthetic']}, 'derivation': {'enum': ['reported_estimator_covariance', 'exact_linear_transform', 'estimated_from_observations', 'synthetic_model']}, 'systematic_coverage': {'enum': ['included_as_declared', 'not_established', 'identified_unresolved']}}, 'required': ['version', 'roles', 'owner_keys', 'units', 'dependency_keys', 'covariance', 'basis', 'variance_status', 'origin', 'derivation', 'systematic_coverage'], 'additionalProperties': False}, []),
}
_SCHEMA_DEFINITIONS = {
    'assay': {'type': 'object', 'properties': {'organism': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'genotype': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'molecule': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'accession': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'construct': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'preparation': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'expression_host': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'experimental_system': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'conditions': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'intended_change': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'endpoint': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'calibration': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'blank': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'normalization': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'independent_replication': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'arrangement': {'type': 'object', 'properties': {'value': {'enum': ['single_preparation', 'coexistence', 'replacement', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'participants': {'type': 'array', 'items': {'type': 'object', 'properties': {'identity': {'$ref': '#/$defs/field'}, 'role': {'enum': ['assayed_molecule', 'partner', 'activator', 'substrate', 'product', 'control', 'unknown']}, 'presence': {'enum': ['present', 'absent', 'unknown', 'conflicting']}}, 'required': ['identity', 'role', 'presence'], 'additionalProperties': False}}}, 'required': ['organism', 'genotype', 'molecule', 'accession', 'construct', 'preparation', 'expression_host', 'experimental_system', 'conditions', 'intended_change', 'endpoint', 'calibration', 'blank', 'normalization', 'independent_replication', 'arrangement', 'participants'], 'additionalProperties': False},
    'coefficient': {'type': 'object', 'properties': {'kind': {'enum': ['implicit_unit_coefficient', 'explicit_source_token']}, 'number': {'anyOf': [{'$ref': '#/$defs/number_selector'}, {'type': 'null'}]}, 'reaction': {'$ref': '#/$defs/field'}, 'relationship': {'$ref': '#/$defs/relationship'}}, 'required': ['kind', 'number', 'reaction', 'relationship'], 'additionalProperties': False},
    'cross_relationships': {'type': 'object', 'properties': {'chemical': {'type': 'object', 'properties': {'window_compatibility': {'$ref': '#/$defs/relationship'}, 'concentration_basis': {'$ref': '#/$defs/relationship'}, 'calibration_compatibility': {'$ref': '#/$defs/relationship'}, 'endpoint_account': {'type': 'object', 'properties': {'value': {'enum': ['same_reaction_account_supported', 'compatible_separate_accounts_supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'physical_pairing': {'type': 'object', 'properties': {'value': {'enum': ['same_reaction_supported', 'paired_reactions_supported', 'separate_reactions_supported', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}}, 'required': ['window_compatibility', 'concentration_basis', 'calibration_compatibility', 'endpoint_account', 'physical_pairing'], 'additionalProperties': False}, 'fate': {'type': 'object', 'properties': {'window_compatibility': {'$ref': '#/$defs/relationship'}, 'concentration_basis': {'$ref': '#/$defs/relationship'}, 'calibration_compatibility': {'$ref': '#/$defs/relationship'}, 'endpoint_account': {'type': 'object', 'properties': {'value': {'enum': ['same_reaction_account_supported', 'compatible_separate_accounts_supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'physical_pairing': {'type': 'object', 'properties': {'value': {'enum': ['same_reaction_supported', 'paired_reactions_supported', 'separate_reactions_supported', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}}, 'required': ['window_compatibility', 'concentration_basis', 'calibration_compatibility', 'endpoint_account', 'physical_pairing'], 'additionalProperties': False}}, 'required': ['chemical', 'fate'], 'additionalProperties': False},
    'field': {'oneOf': [{'$ref': '#/$defs/text_field'}, {'$ref': '#/$defs/xlsx_field'}]},
    'grid': {'type': 'object', 'properties': {'source_ref': {'type': 'string', 'minLength': 1}, 'sheet_key': {'type': 'string', 'minLength': 1}, 'sheet_name': {'type': 'string', 'minLength': 1}, 'worksheet_part': {'type': 'string', 'minLength': 1}, 'header_row': {'type': 'integer', 'minimum': 1}, 'start_row': {'type': 'integer', 'minimum': 1}, 'end_row': {'type': 'integer', 'minimum': 1}, 'coordinate_column': {'type': 'string', 'pattern': '^[A-Z]+$'}, 'columns': {'type': 'object', 'properties': {'substrate': {'type': 'string', 'pattern': '^[A-Z]+$'}, 'total_product': {'type': 'string', 'pattern': '^[A-Z]+$'}, 'fate_product': {'type': 'string', 'pattern': '^[A-Z]+$'}}, 'required': ['substrate', 'total_product', 'fate_product'], 'additionalProperties': False}}, 'required': ['source_ref', 'sheet_key', 'sheet_name', 'worksheet_part', 'header_row', 'start_row', 'end_row', 'coordinate_column', 'columns'], 'additionalProperties': False},
    'number_selector': {'type': 'object', 'properties': {'field': {'$ref': '#/$defs/field'}, 'number_start': {'type': 'integer', 'minimum': 0}, 'number_end': {'type': 'integer', 'minimum': 1}}, 'required': ['field', 'number_start', 'number_end'], 'additionalProperties': False},
    'pair_relationships': {'type': 'object', 'properties': {'substrate': {'type': 'object', 'properties': {'endpoint_comparability': {'type': 'object', 'properties': {'value': {'enum': ['same_series_supported', 'separately_measured_compatible', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'selected_window': {'$ref': '#/$defs/relationship'}, 'concentration_basis': {'$ref': '#/$defs/relationship'}, 'physical_pairing': {'type': 'object', 'properties': {'value': {'enum': ['same_reaction_supported', 'paired_reactions_supported', 'separate_reactions_supported', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}}, 'required': ['endpoint_comparability', 'selected_window', 'concentration_basis', 'physical_pairing'], 'additionalProperties': False}, 'total_product': {'type': 'object', 'properties': {'endpoint_comparability': {'type': 'object', 'properties': {'value': {'enum': ['same_series_supported', 'separately_measured_compatible', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'selected_window': {'$ref': '#/$defs/relationship'}, 'concentration_basis': {'$ref': '#/$defs/relationship'}, 'physical_pairing': {'type': 'object', 'properties': {'value': {'enum': ['same_reaction_supported', 'paired_reactions_supported', 'separate_reactions_supported', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}}, 'required': ['endpoint_comparability', 'selected_window', 'concentration_basis', 'physical_pairing'], 'additionalProperties': False}, 'fate_product': {'type': 'object', 'properties': {'endpoint_comparability': {'type': 'object', 'properties': {'value': {'enum': ['same_series_supported', 'separately_measured_compatible', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'selected_window': {'$ref': '#/$defs/relationship'}, 'concentration_basis': {'$ref': '#/$defs/relationship'}, 'physical_pairing': {'type': 'object', 'properties': {'value': {'enum': ['same_reaction_supported', 'paired_reactions_supported', 'separate_reactions_supported', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}}, 'required': ['endpoint_comparability', 'selected_window', 'concentration_basis', 'physical_pairing'], 'additionalProperties': False}}, 'required': ['substrate', 'total_product', 'fate_product'], 'additionalProperties': False},
    'quantity': {'type': 'object', 'properties': {'number': {'anyOf': [{'$ref': '#/$defs/number_selector'}, {'type': 'null'}]}, 'unit': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'record': {'anyOf': [{'$ref': '#/$defs/text_field'}, {'type': 'null'}]}, 'analyte': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'coordinate': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'measurement_identity': {'anyOf': [{'$ref': '#/$defs/field'}, {'type': 'null'}]}, 'unit_association': {'type': 'object', 'properties': {'value': {'enum': ['same_record', 'source_header', 'source_shared_header', 'source_method', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'reading_meaning': {'type': 'object', 'properties': {'value': {'enum': ['reported_point', 'source_qualified_approximate', 'reported_nondetection', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'concentration_basis': {'type': 'object', 'properties': {'value': {'enum': ['native_reaction_concentration', 'quenched_sample_concentration', 'other_normalized_concentration', 'coordinate', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'uncertainty': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}}, 'required': ['number', 'unit', 'record', 'analyte', 'coordinate', 'measurement_identity', 'unit_association', 'reading_meaning', 'concentration_basis', 'uncertainty'], 'additionalProperties': False},
    'relationship': {'type': 'object', 'properties': {'value': {'enum': ['supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False},
    'text_field': {'type': 'object', 'properties': {'kind': {'const': 'text'}, 'source_ref': {'type': 'string', 'minLength': 1}, 'representation': {'enum': ['original', 'text']}, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}, 'quote': {'type': 'string', 'minLength': 1}}, 'required': ['kind', 'source_ref', 'representation', 'start', 'end', 'quote'], 'additionalProperties': False},
    'timing': {'type': 'object', 'properties': {'source_meaning': {'type': 'object', 'properties': {'value': {'enum': ['actual_sampling_time', 'plot_coordinate_only', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'scenario': {'anyOf': [{'type': 'object', 'properties': {'kind': {'const': 'coordinates_are_elapsed_sampling_times'}, 'status': {'const': 'stipulated_sensitivity'}}, 'required': ['kind', 'status'], 'additionalProperties': False}, {'type': 'null'}]}}, 'required': ['source_meaning', 'scenario'], 'additionalProperties': False},
    'xlsx_field': {'type': 'object', 'properties': {'kind': {'const': 'xlsx_cell_slice'}, 'source_ref': {'type': 'string', 'minLength': 1}, 'representation': {'const': 'original'}, 'sheet_key': {'type': 'string', 'minLength': 1}, 'sheet_name': {'type': 'string', 'minLength': 1}, 'worksheet_part': {'type': 'string', 'minLength': 1}, 'cell': {'type': 'string', 'pattern': '^[A-Z]+[1-9][0-9]*$'}, 'decoded_start': {'type': 'integer', 'minimum': 0}, 'decoded_end': {'type': 'integer', 'minimum': 1}, 'quote': {'type': 'string', 'minLength': 1}}, 'required': ['kind', 'source_ref', 'representation', 'sheet_key', 'sheet_name', 'worksheet_part', 'cell', 'decoded_start', 'decoded_end', 'quote'], 'additionalProperties': False},
    'artifact': {'type': 'object', 'properties': {'source_ref': {'type': 'string', 'minLength': 1}, 'representation': {'enum': ['original', 'text']}, 'artifact_ref': {'type': 'string', 'minLength': 1}, 'sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}}, 'required': ['source_ref', 'representation', 'artifact_ref', 'sha256'], 'additionalProperties': False},
    'coefficient_reading': {'type': 'object', 'properties': {'value': {'type': ['number', 'null']}, 'exact_value': {'anyOf': [{'$ref': '#/$defs/exact'}, {'type': 'null'}]}, 'origin': {'enum': ['implicit_chemical_notation', 'reported', 'synthetic', 'unavailable']}, 'dependency_keys': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'uniqueItems': True}, 'reasons': {'$ref': '#/$defs/reasons'}}, 'required': ['value', 'exact_value', 'origin', 'dependency_keys', 'reasons'], 'additionalProperties': False},
    'covariance_document': {'type': 'object', 'properties': {'version': {'const': 'a105_concentration_window_covariance_v1'}, 'roles': {'type': 'array', 'items': {'enum': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end']}, 'uniqueItems': True}, 'owner_keys': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}}, 'units': {'type': 'array', 'items': {'enum': ['uM', 's']}}, 'dependency_keys': {'type': 'array', 'items': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'uniqueItems': True}}, 'covariance': {'anyOf': [{'type': 'array', 'items': {'type': 'array', 'items': {'type': 'number'}}}, {'type': 'null'}]}, 'basis': {'const': 'joint_covariance_of_selected_estimates'}, 'variance_status': {'enum': ['known', 'estimated', 'unknown']}, 'origin': {'enum': ['reported', 'derived', 'synthetic']}, 'derivation': {'enum': ['reported_estimator_covariance', 'exact_linear_transform', 'estimated_from_observations', 'synthetic_model']}, 'systematic_coverage': {'enum': ['included_as_declared', 'not_established', 'identified_unresolved']}}, 'required': ['version', 'roles', 'owner_keys', 'units', 'dependency_keys', 'covariance', 'basis', 'variance_status', 'origin', 'derivation', 'systematic_coverage'], 'additionalProperties': False},
    'covariance_reading': {'type': 'object', 'properties': {'document': {'$ref': '#/$defs/covariance_document'}, 'source_ref': {'type': 'string', 'minLength': 1}, 'artifact_ref': {'type': 'string', 'minLength': 1}, 'sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'matrix_exact': {'anyOf': [{'type': 'array', 'items': {'type': 'array', 'items': {'$ref': '#/$defs/exact'}}}, {'type': 'null'}]}}, 'required': ['document', 'source_ref', 'artifact_ref', 'sha256', 'matrix_exact'], 'additionalProperties': False},
    'exact': {'type': 'object', 'properties': {'numerator': {'type': 'string', 'pattern': '^-?[0-9]+$'}, 'denominator': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}}, 'required': ['numerator', 'denominator'], 'additionalProperties': False},
    'field_binding': {'oneOf': [{'type': 'object', 'properties': {'kind': {'const': 'text'}, 'source_ref': {'type': 'string', 'minLength': 1}, 'representation': {'enum': ['original', 'text']}, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}}, 'required': ['kind', 'source_ref', 'representation', 'start', 'end'], 'additionalProperties': False}, {'type': 'object', 'properties': {'kind': {'const': 'xlsx_cell_slice'}, 'source_ref': {'type': 'string', 'minLength': 1}, 'representation': {'const': 'original'}, 'sheet_key': {'type': 'string', 'minLength': 1}, 'sheet_name': {'type': 'string', 'minLength': 1}, 'worksheet_part': {'type': 'string', 'minLength': 1}, 'cell': {'type': 'string', 'pattern': '^[A-Z]+[1-9][0-9]*$'}, 'decoded_start': {'type': 'integer', 'minimum': 0}, 'decoded_end': {'type': 'integer', 'minimum': 1}}, 'required': ['kind', 'source_ref', 'representation', 'sheet_key', 'sheet_name', 'worksheet_part', 'cell', 'decoded_start', 'decoded_end'], 'additionalProperties': False}]},
    'location': {'oneOf': [{'type': 'object', 'properties': {'kind': {'const': 'text'}, 'source_ref': {'type': 'string', 'minLength': 1}, 'artifact_ref': {'type': 'string', 'minLength': 1}, 'representation': {'enum': ['original', 'text']}, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}}, 'required': ['kind', 'source_ref', 'artifact_ref', 'representation', 'start', 'end'], 'additionalProperties': False}, {'type': 'object', 'properties': {'kind': {'const': 'xlsx_cell'}, 'source_ref': {'type': 'string', 'minLength': 1}, 'artifact_ref': {'type': 'string', 'minLength': 1}, 'representation': {'const': 'original'}, 'worksheet_part': {'type': 'string', 'minLength': 1}, 'member_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'sheet_key': {'type': 'string', 'minLength': 1}, 'sheet_name': {'type': 'string', 'minLength': 1}, 'cell': {'type': 'string', 'minLength': 1}, 'xml_start': {'type': 'integer', 'minimum': 0}, 'xml_end': {'type': 'integer', 'minimum': 1}, 'decoded_start': {'type': 'integer', 'minimum': 0}, 'decoded_end': {'type': 'integer', 'minimum': 1}, 'shared_string_location': {'anyOf': [{'type': 'object', 'properties': {'member': {'type': 'string', 'minLength': 1}, 'member_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}}, 'required': ['member', 'member_sha256', 'start', 'end'], 'additionalProperties': False}, {'type': 'null'}]}}, 'required': ['kind', 'source_ref', 'artifact_ref', 'representation', 'worksheet_part', 'member_sha256', 'sheet_key', 'sheet_name', 'cell', 'xml_start', 'xml_end', 'decoded_start', 'decoded_end', 'shared_string_location'], 'additionalProperties': False}]},
    'reading': {'type': 'object', 'properties': {'role': {'enum': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end']}, 'value': {'type': ['number', 'null']}, 'exact_value': {'anyOf': [{'$ref': '#/$defs/exact'}, {'type': 'null'}]}, 'unit': {'enum': ['uM', 's', None]}, 'raw_number': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'null'}]}, 'raw_unit': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'null'}]}, 'unit_multiplier': {'anyOf': [{'$ref': '#/$defs/exact'}, {'type': 'null'}]}, 'relation': {'enum': ['eq', 'lt', 'le', 'gt', 'ge', 'none']}, 'status': {'enum': ['point', 'bounded', 'nondetection', 'unavailable']}, 'approximate': {'type': 'boolean'}, 'origin': {'enum': ['reported', 'graph_derived', 'calculated', 'synthetic']}, 'owner_key': {'type': 'string', 'minLength': 1}, 'physical_owner_key': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'null'}]}, 'dependency_keys': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'uniqueItems': True}, 'locations': {'type': 'array', 'items': {'$ref': '#/$defs/location'}}, 'reported_uncertainty': {'type': 'array', 'items': {'$ref': '#/$defs/field'}}, 'reasons': {'$ref': '#/$defs/reasons'}}, 'required': ['role', 'value', 'exact_value', 'unit', 'raw_number', 'raw_unit', 'unit_multiplier', 'relation', 'status', 'approximate', 'origin', 'owner_key', 'physical_owner_key', 'dependency_keys', 'locations', 'reported_uncertainty', 'reasons'], 'additionalProperties': False},
    'reasons': {'type': 'object', 'properties': {'source': {'type': 'array', 'items': {'enum': ['number_unavailable', 'unit_unavailable', 'native_nondetection', 'joint_covariance_unknown', 'joint_covariance_incomplete', 'timing_meaning_unknown']}, 'uniqueItems': True}, 'selection': {'type': 'array', 'items': {'enum': ['operand_not_selected', 'coefficient_not_selected', 'covariance_not_selected', 'timing_scenario_not_selected']}, 'uniqueItems': True}, 'relationship': {'type': 'array', 'items': {'enum': ['same_series_unknown', 'same_series_conflicting', 'same_series_incompatible', 'same_window_unknown', 'same_window_conflicting', 'same_window_incompatible', 'same_aliquot_window_unknown', 'same_aliquot_window_conflicting', 'same_aliquot_window_incompatible', 'concentration_basis_unknown', 'concentration_basis_conflicting', 'concentration_basis_incompatible', 'calibration_linkage_unknown', 'calibration_linkage_conflicting', 'calibration_linkage_incompatible', 'endpoint_assignment_unknown', 'endpoint_assignment_conflicting', 'endpoint_assignment_incompatible', 'timing_meaning_conflicting', 'timing_meaning_not_elapsed', 'normalization_mapping_unresolved', 'coefficient_meaning_unresolved', 'reused_physical_operand', 'pair_endpoint_comparability_unknown', 'pair_endpoint_comparability_conflicting', 'pair_endpoint_comparability_incompatible', 'pair_selected_window_unknown', 'pair_selected_window_conflicting', 'pair_selected_window_incompatible', 'pair_concentration_basis_unknown', 'pair_concentration_basis_conflicting', 'pair_concentration_basis_incompatible', 'cross_window_compatibility_unknown', 'cross_window_compatibility_conflicting', 'cross_window_compatibility_incompatible', 'cross_concentration_basis_unknown', 'cross_concentration_basis_conflicting', 'cross_concentration_basis_incompatible', 'cross_calibration_compatibility_unknown', 'cross_calibration_compatibility_conflicting', 'cross_calibration_compatibility_incompatible', 'cross_endpoint_account_unknown', 'cross_endpoint_account_conflicting', 'cross_endpoint_account_incompatible']}, 'uniqueItems': True}, 'implementation': {'type': 'array', 'items': {'enum': ['bounded_arithmetic_unimplemented', 'approximate_arithmetic_unimplemented', 'formula_cache_point_unimplemented', 'source_unit_unsupported', 'covariance_estimation_from_table_unimplemented', 'scenario_uncertainty_unimplemented']}, 'uniqueItems': True}, 'domain': {'type': 'array', 'items': {'enum': ['zero_denominator', 'positive_time_span_required', 'positive_coefficient_required', 'positive_variance_required', 'numerical_model_range']}, 'uniqueItems': True}}, 'required': ['source', 'selection', 'relationship', 'implementation', 'domain'], 'additionalProperties': False},
    'scientific_assay': {'type': 'object', 'properties': {'organism': {'$ref': '#/$defs/scientific_field'}, 'genotype': {'$ref': '#/$defs/scientific_field'}, 'molecule': {'$ref': '#/$defs/scientific_field'}, 'accession': {'$ref': '#/$defs/scientific_field'}, 'construct': {'$ref': '#/$defs/scientific_field'}, 'preparation': {'$ref': '#/$defs/scientific_field'}, 'expression_host': {'$ref': '#/$defs/scientific_field'}, 'experimental_system': {'$ref': '#/$defs/scientific_field'}, 'conditions': {'$ref': '#/$defs/scientific_field'}, 'intended_change': {'$ref': '#/$defs/scientific_field'}, 'endpoint': {'$ref': '#/$defs/scientific_field'}, 'calibration': {'$ref': '#/$defs/scientific_field'}, 'blank': {'$ref': '#/$defs/scientific_field'}, 'normalization': {'$ref': '#/$defs/scientific_field'}, 'independent_replication': {'$ref': '#/$defs/scientific_field'}, 'arrangement': {'type': 'object', 'properties': {'value': {'enum': ['single_preparation', 'coexistence', 'replacement', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'participants': {'type': 'array', 'items': {'type': 'object', 'properties': {'identity': {'$ref': '#/$defs/scientific_field'}, 'role': {'enum': ['assayed_molecule', 'partner', 'activator', 'substrate', 'product', 'control', 'unknown']}, 'presence': {'enum': ['present', 'absent', 'unknown', 'conflicting']}}, 'required': ['identity', 'role', 'presence'], 'additionalProperties': False}}}, 'required': ['organism', 'genotype', 'molecule', 'accession', 'construct', 'preparation', 'expression_host', 'experimental_system', 'conditions', 'intended_change', 'endpoint', 'calibration', 'blank', 'normalization', 'independent_replication', 'arrangement', 'participants'], 'additionalProperties': False},
    'scientific_coefficient': {'type': 'object', 'properties': {'selection_status': {'enum': ['selected', 'not_selected']}, 'kind': {'enum': ['implicit_unit_coefficient', 'explicit_source_token', None]}, 'value': {'type': ['number', 'null']}, 'exact_value': {'anyOf': [{'$ref': '#/$defs/exact'}, {'type': 'null'}]}, 'origin': {'enum': ['implicit_chemical_notation', 'reported', 'synthetic', 'unavailable']}, 'relationship': {'type': 'object', 'properties': {'value': {'enum': ['supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'reaction': {'$ref': '#/$defs/scientific_field'}, 'coefficient_token_support': {'$ref': '#/$defs/scientific_field'}, 'analyte': {'$ref': '#/$defs/scientific_field'}, 'operand_roles': {'type': 'array', 'items': {'enum': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end']}, 'uniqueItems': True}, 'coefficient_meaning': {'const': 'moles_of_selected_analyte_per_reaction_equivalent'}, 'conversion_direction': {'const': 'selected_concentration_change_divided_by_coefficient'}, 'dependency_keys': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'uniqueItems': True}, 'reasons': {'$ref': '#/$defs/reasons'}}, 'required': ['selection_status', 'kind', 'value', 'exact_value', 'origin', 'relationship', 'reaction', 'coefficient_token_support', 'analyte', 'operand_roles', 'coefficient_meaning', 'conversion_direction', 'dependency_keys', 'reasons'], 'additionalProperties': False},
    'scientific_context': {'type': 'object', 'properties': {'usage': {'const': 'host_scientific_context_requires_scoped_parent_projection'}, 'assay': {'$ref': '#/$defs/scientific_assay'}, 'quantities': {'type': 'object', 'properties': {'substrate_start': {'$ref': '#/$defs/scientific_quantity'}, 'substrate_end': {'$ref': '#/$defs/scientific_quantity'}, 'total_product_start': {'$ref': '#/$defs/scientific_quantity'}, 'total_product_end': {'$ref': '#/$defs/scientific_quantity'}, 'fate_product_start': {'$ref': '#/$defs/scientific_quantity'}, 'fate_product_end': {'$ref': '#/$defs/scientific_quantity'}, 'coordinate_start': {'$ref': '#/$defs/scientific_quantity'}, 'coordinate_end': {'$ref': '#/$defs/scientific_quantity'}}, 'required': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end'], 'additionalProperties': False}, 'stoichiometry': {'type': 'object', 'properties': {'substrate': {'$ref': '#/$defs/scientific_coefficient'}, 'total_product': {'$ref': '#/$defs/scientific_coefficient'}, 'fate_product': {'$ref': '#/$defs/scientific_coefficient'}}, 'required': ['substrate', 'total_product', 'fate_product'], 'additionalProperties': False}, 'pair_relationships': {'$ref': '#/$defs/scientific_pair_relationships'}, 'cross_relationships': {'$ref': '#/$defs/scientific_cross_relationships'}, 'timing': {'$ref': '#/$defs/scientific_timing'}}, 'required': ['usage', 'assay', 'quantities', 'stoichiometry', 'pair_relationships', 'cross_relationships', 'timing'], 'additionalProperties': False},
    'scientific_cross_relationships': {'type': 'object', 'properties': {'chemical': {'type': 'object', 'properties': {'window_compatibility': {'type': 'object', 'properties': {'value': {'enum': ['supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'concentration_basis': {'type': 'object', 'properties': {'value': {'enum': ['supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'calibration_compatibility': {'type': 'object', 'properties': {'value': {'enum': ['supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'endpoint_account': {'type': 'object', 'properties': {'value': {'enum': ['same_reaction_account_supported', 'compatible_separate_accounts_supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'physical_pairing': {'type': 'object', 'properties': {'value': {'enum': ['same_reaction_supported', 'paired_reactions_supported', 'separate_reactions_supported', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}}, 'required': ['window_compatibility', 'concentration_basis', 'calibration_compatibility', 'endpoint_account', 'physical_pairing'], 'additionalProperties': False}, 'fate': {'type': 'object', 'properties': {'window_compatibility': {'type': 'object', 'properties': {'value': {'enum': ['supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'concentration_basis': {'type': 'object', 'properties': {'value': {'enum': ['supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'calibration_compatibility': {'type': 'object', 'properties': {'value': {'enum': ['supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'endpoint_account': {'type': 'object', 'properties': {'value': {'enum': ['same_reaction_account_supported', 'compatible_separate_accounts_supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'physical_pairing': {'type': 'object', 'properties': {'value': {'enum': ['same_reaction_supported', 'paired_reactions_supported', 'separate_reactions_supported', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}}, 'required': ['window_compatibility', 'concentration_basis', 'calibration_compatibility', 'endpoint_account', 'physical_pairing'], 'additionalProperties': False}}, 'required': ['chemical', 'fate'], 'additionalProperties': False},
    'scientific_field': {'type': 'object', 'properties': {'status': {'enum': ['retained', 'not_selected']}, 'scientific_text': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'null'}]}, 'display_status': {'enum': ['semantic_context', 'support_location_only', 'not_selected']}, 'binding': {'anyOf': [{'$ref': '#/$defs/field_binding'}, {'type': 'null'}]}, 'artifact_ref': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'null'}]}, 'source_sha256': {'anyOf': [{'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, {'type': 'null'}]}}, 'required': ['status', 'scientific_text', 'display_status', 'binding', 'artifact_ref', 'source_sha256'], 'additionalProperties': False},
    'scientific_pair_relationships': {'type': 'object', 'properties': {'substrate': {'type': 'object', 'properties': {'endpoint_comparability': {'type': 'object', 'properties': {'value': {'enum': ['same_series_supported', 'separately_measured_compatible', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'selected_window': {'type': 'object', 'properties': {'value': {'enum': ['supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'concentration_basis': {'type': 'object', 'properties': {'value': {'enum': ['supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'physical_pairing': {'type': 'object', 'properties': {'value': {'enum': ['same_reaction_supported', 'paired_reactions_supported', 'separate_reactions_supported', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}}, 'required': ['endpoint_comparability', 'selected_window', 'concentration_basis', 'physical_pairing'], 'additionalProperties': False}, 'total_product': {'type': 'object', 'properties': {'endpoint_comparability': {'type': 'object', 'properties': {'value': {'enum': ['same_series_supported', 'separately_measured_compatible', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'selected_window': {'type': 'object', 'properties': {'value': {'enum': ['supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'concentration_basis': {'type': 'object', 'properties': {'value': {'enum': ['supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'physical_pairing': {'type': 'object', 'properties': {'value': {'enum': ['same_reaction_supported', 'paired_reactions_supported', 'separate_reactions_supported', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}}, 'required': ['endpoint_comparability', 'selected_window', 'concentration_basis', 'physical_pairing'], 'additionalProperties': False}, 'fate_product': {'type': 'object', 'properties': {'endpoint_comparability': {'type': 'object', 'properties': {'value': {'enum': ['same_series_supported', 'separately_measured_compatible', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'selected_window': {'type': 'object', 'properties': {'value': {'enum': ['supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'concentration_basis': {'type': 'object', 'properties': {'value': {'enum': ['supported', 'incompatible', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'physical_pairing': {'type': 'object', 'properties': {'value': {'enum': ['same_reaction_supported', 'paired_reactions_supported', 'separate_reactions_supported', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}}, 'required': ['endpoint_comparability', 'selected_window', 'concentration_basis', 'physical_pairing'], 'additionalProperties': False}}, 'required': ['substrate', 'total_product', 'fate_product'], 'additionalProperties': False},
    'scientific_quantity': {'type': 'object', 'properties': {'selection_status': {'enum': ['selected', 'not_selected']}, 'analyte': {'$ref': '#/$defs/scientific_field'}, 'coordinate': {'$ref': '#/$defs/scientific_field'}, 'unit': {'$ref': '#/$defs/scientific_field'}, 'record': {'$ref': '#/$defs/scientific_field'}, 'measurement_identity': {'$ref': '#/$defs/scientific_field'}, 'reading_meaning': {'type': 'object', 'properties': {'value': {'enum': ['reported_point', 'source_qualified_approximate', 'reported_nondetection', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'concentration_basis': {'type': 'object', 'properties': {'value': {'enum': ['native_reaction_concentration', 'quenched_sample_concentration', 'other_normalized_concentration', 'coordinate', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'unit_association': {'type': 'object', 'properties': {'value': {'enum': ['same_record', 'source_header', 'source_shared_header', 'source_method', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'uncertainty': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['selection_status', 'analyte', 'coordinate', 'unit', 'record', 'measurement_identity', 'reading_meaning', 'concentration_basis', 'unit_association', 'uncertainty'], 'additionalProperties': False},
    'scientific_timing': {'type': 'object', 'properties': {'source_meaning': {'type': 'object', 'properties': {'value': {'enum': ['actual_sampling_time', 'plot_coordinate_only', 'unknown', 'conflicting']}, 'witnesses': {'type': 'array', 'items': {'$ref': '#/$defs/scientific_field'}}}, 'required': ['value', 'witnesses'], 'additionalProperties': False}, 'scenario': {'anyOf': [{'type': 'object', 'properties': {'kind': {'const': 'coordinates_are_elapsed_sampling_times'}, 'status': {'const': 'stipulated_sensitivity'}}, 'required': ['kind', 'status'], 'additionalProperties': False}, {'type': 'null'}]}}, 'required': ['source_meaning', 'scenario'], 'additionalProperties': False},
    'selection': {'type': 'object', 'properties': {'version': {'const': 'a105_concentration_window_selection_v2'}, 'source_ref': {'type': 'string', 'minLength': 1}, 'source_kind': {'enum': ['primary_source', 'retained_extraction', 'graph_extraction', 'synthetic_fixture']}, 'assay': {'$ref': '#/$defs/assay'}, 'grid': {'anyOf': [{'$ref': '#/$defs/grid'}, {'type': 'null'}]}, 'quantities': {'type': 'object', 'properties': {'substrate_start': {'anyOf': [{'$ref': '#/$defs/quantity'}, {'type': 'null'}]}, 'substrate_end': {'anyOf': [{'$ref': '#/$defs/quantity'}, {'type': 'null'}]}, 'total_product_start': {'anyOf': [{'$ref': '#/$defs/quantity'}, {'type': 'null'}]}, 'total_product_end': {'anyOf': [{'$ref': '#/$defs/quantity'}, {'type': 'null'}]}, 'fate_product_start': {'anyOf': [{'$ref': '#/$defs/quantity'}, {'type': 'null'}]}, 'fate_product_end': {'anyOf': [{'$ref': '#/$defs/quantity'}, {'type': 'null'}]}, 'coordinate_start': {'anyOf': [{'$ref': '#/$defs/quantity'}, {'type': 'null'}]}, 'coordinate_end': {'anyOf': [{'$ref': '#/$defs/quantity'}, {'type': 'null'}]}}, 'required': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end'], 'additionalProperties': False}, 'stoichiometry': {'type': 'object', 'properties': {'substrate': {'anyOf': [{'$ref': '#/$defs/coefficient'}, {'type': 'null'}]}, 'total_product': {'anyOf': [{'$ref': '#/$defs/coefficient'}, {'type': 'null'}]}, 'fate_product': {'anyOf': [{'$ref': '#/$defs/coefficient'}, {'type': 'null'}]}}, 'required': ['substrate', 'total_product', 'fate_product'], 'additionalProperties': False}, 'timing': {'$ref': '#/$defs/timing'}, 'covariance_source_ref': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'null'}]}, 'covariance_material': {'enum': ['closed_joint_estimator_covariance_document', 'unsupported_observation_table', 'not_selected']}, 'evidence': {'type': 'array', 'items': {'type': 'object', 'properties': {'role': {'enum': ['chemical_relation', 'product_identity', 'normalization', 'calibration', 'blank', 'replication', 'uncertainty', 'alternative_contribution', 'preparation_change', 'timing']}, 'witness': {'$ref': '#/$defs/field'}}, 'required': ['role', 'witness'], 'additionalProperties': False}}, 'requested_cells': {'type': 'array', 'items': {'enum': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end', 'substrate_loss', 'total_product_gain', 'fate_product_gain', 'coordinate_span', 'chemical_discrepancy', 'chemical_ratio', 'chemical_relative_discrepancy', 'fate_fraction', 'substrate_depletion_fraction', 'source_interval_average_substrate', 'scenario_interval_average_substrate', 'source_interval_average_total_product', 'scenario_interval_average_total_product', 'source_interval_average_fate_product', 'scenario_interval_average_fate_product', 'substrate_loss_variance', 'total_product_gain_variance', 'fate_product_gain_variance', 'coordinate_span_variance', 'chemical_discrepancy_variance', 'chemical_ratio_variance', 'fate_fraction_variance', 'source_interval_average_substrate_variance', 'source_interval_average_total_product_variance', 'source_interval_average_fate_product_variance', 'chemical_standardized_discrepancy']}, 'uniqueItems': True}, 'pair_relationships': {'$ref': '#/$defs/pair_relationships'}, 'cross_relationships': {'$ref': '#/$defs/cross_relationships'}}, 'required': ['version', 'source_ref', 'source_kind', 'assay', 'grid', 'quantities', 'stoichiometry', 'timing', 'covariance_source_ref', 'covariance_material', 'evidence', 'requested_cells', 'pair_relationships', 'cross_relationships'], 'additionalProperties': False},
    'covariance_context': {'type': 'object', 'properties': {'selection_status': {'enum': ['selected', 'not_selected']}, 'material': {'enum': ['closed_joint_estimator_covariance_document', 'unsupported_observation_table', 'not_selected']}, 'source_ref': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'null'}]}, 'artifact_ref': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'null'}]}, 'sha256': {'anyOf': [{'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, {'type': 'null'}]}, 'roles': {'type': 'array', 'items': {'enum': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end']}, 'uniqueItems': True}, 'owner_keys': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}}, 'units': {'type': 'array', 'items': {'enum': ['uM', 's']}}, 'dependency_keys': {'type': 'array', 'items': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'uniqueItems': True}}, 'basis': {'enum': ['joint_covariance_of_selected_estimates', None]}, 'variance_status': {'enum': ['known', 'estimated', 'unknown', None]}, 'origin': {'enum': ['reported', 'derived', 'synthetic', None]}, 'derivation': {'enum': ['reported_estimator_covariance', 'exact_linear_transform', 'estimated_from_observations', 'synthetic_model', None]}, 'systematic_coverage': {'enum': ['included_as_declared', 'not_established', 'identified_unresolved', None]}}, 'required': ['selection_status', 'material', 'source_ref', 'artifact_ref', 'sha256', 'roles', 'owner_keys', 'units', 'dependency_keys', 'basis', 'variance_status', 'origin', 'derivation', 'systematic_coverage'], 'additionalProperties': False},
    'association': {'type': 'object', 'properties': {'selection_digest': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'extraction_digest': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'calculation_inputs_digest': {'anyOf': [{'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, {'type': 'null'}]}}, 'required': ['selection_digest', 'extraction_digest', 'calculation_inputs_digest'], 'additionalProperties': False},
    'cell': {'type': 'object', 'properties': {'component': {'enum': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end', 'substrate_loss', 'total_product_gain', 'fate_product_gain', 'coordinate_span', 'chemical_discrepancy', 'chemical_ratio', 'chemical_relative_discrepancy', 'fate_fraction', 'substrate_depletion_fraction', 'source_interval_average_substrate', 'scenario_interval_average_substrate', 'source_interval_average_total_product', 'scenario_interval_average_total_product', 'source_interval_average_fate_product', 'scenario_interval_average_fate_product', 'substrate_loss_variance', 'total_product_gain_variance', 'fate_product_gain_variance', 'coordinate_span_variance', 'chemical_discrepancy_variance', 'chemical_ratio_variance', 'fate_fraction_variance', 'source_interval_average_substrate_variance', 'source_interval_average_total_product_variance', 'source_interval_average_fate_product_variance', 'chemical_standardized_discrepancy']}, 'value': {'type': ['number', 'null']}, 'exact_value': {'anyOf': [{'$ref': '#/$defs/exact'}, {'type': 'null'}]}, 'conditional_value': {'type': ['number', 'null']}, 'conditional_exact_value': {'anyOf': [{'$ref': '#/$defs/exact'}, {'type': 'null'}]}, 'status': {'enum': ['populated', 'conditional_scenario', 'unavailable']}, 'unit': {'enum': ['uM', 's', 'uM_reaction_equivalents', 'dimensionless', 'fraction', 'uM/min', '(uM)^2', '(s)^2', '(uM_reaction_equivalents)^2', '(dimensionless)^2', '(uM/min)^2']}, 'formula': {'enum': ['selected_native_token*unit_multiplier', 'S0-S1', 'T1-T0', 'F1-F0', 't1-t0', '(S0-S1)/nuS-(T1-T0)/nuT', '((S0-S1)/nuS)/((T1-T0)/nuT)', 'chemical_ratio-1', '((F1-F0)/nuF)/((T1-T0)/nuT)', '(S0-S1)/S0', '60*substrate_loss/coordinate_span', '60*total_product_gain/coordinate_span', '60*fate_product_gain/coordinate_span', 'gradient(substrate_loss)^T*C*gradient(substrate_loss)', 'gradient(total_product_gain)^T*C*gradient(total_product_gain)', 'gradient(fate_product_gain)^T*C*gradient(fate_product_gain)', 'gradient(coordinate_span)^T*C*gradient(coordinate_span)', 'gradient(chemical_discrepancy)^T*C*gradient(chemical_discrepancy)', 'gradient(chemical_ratio)^T*C*gradient(chemical_ratio)', 'gradient(fate_fraction)^T*C*gradient(fate_fraction)', 'gradient(source_interval_average_substrate)^T*C*gradient(source_interval_average_substrate)', 'gradient(source_interval_average_total_product)^T*C*gradient(source_interval_average_total_product)', 'gradient(source_interval_average_fate_product)^T*C*gradient(source_interval_average_fate_product)', 'chemical_discrepancy/sqrt(chemical_discrepancy_variance)']}, 'meaning': {'enum': ['Native source operand; not an experimental reliability score.', 'Signed observed change over the selected common window.', 'Released coordinate separation, not automatically elapsed time.', 'Signed disagreement between matched chemical readouts under declared stoichiometry.', 'Relative agreement of matched substrate loss and total-product gain.', 'Signed relative mismatch of the same chemical readouts.', 'Specific measured product fate relative to total measured cleavage; not enzyme attribution.', 'Fractional depletion, which can limit an initial-regime interpretation.', 'Interval-average concentration change; never initial rate, Vmax or kcat.', 'Selected-estimate uncertainty; exact linear propagation or explicitly first-order nonlinear propagation.', 'Discrepancy relative to justified joint-estimate uncertainty; no p-value or probability.']}, 'origin': {'enum': ['reported', 'graph_derived', 'calculated', 'synthetic']}, 'operand_roles': {'type': 'array', 'items': {'enum': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end']}, 'uniqueItems': True}, 'dependency_keys': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'uniqueItems': True}, 'contribution_key': {'type': 'string', 'minLength': 1}, 'approximate': {'type': 'boolean'}, 'bound': {'enum': ['none', 'lt', 'le', 'gt', 'ge']}, 'threshold': {'type': ['number', 'null']}, 'outside_physical_fraction_range': {'type': 'boolean'}, 'negative_observed_change': {'type': 'boolean'}, 'timing_stipulation': {'enum': ['coordinates_are_elapsed_sampling_times', None]}, 'uncertainty_method': {'enum': ['not_applicable', 'exact_linear_covariance', 'first_order_covariance', 'not_available']}, 'reasons': {'$ref': '#/$defs/reasons'}, 'interpretation_scope': {'enum': ['native_observation', 'descriptive_change', 'physical_window_change', 'descriptive_cross_readout_comparison', 'physical_reaction_account', 'conditional_timing_sensitivity', 'uncertainty_of_declared_estimates', 'unavailable']}}, 'required': ['component', 'value', 'exact_value', 'conditional_value', 'conditional_exact_value', 'status', 'unit', 'formula', 'meaning', 'origin', 'operand_roles', 'dependency_keys', 'contribution_key', 'approximate', 'bound', 'threshold', 'outside_physical_fraction_range', 'negative_observed_change', 'timing_stipulation', 'uncertainty_method', 'reasons', 'interpretation_scope'], 'additionalProperties': False},
}

ROLES = ('substrate_start', 'substrate_end', 'total_product_start', 'total_product_end',
         'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end')
ANALYTES = ('substrate', 'total_product', 'fate_product')
_REASON_NAMES = ('source', 'selection', 'relationship', 'implementation', 'domain')


def _schema(name):
    body, names = _SCHEMA_RESOURCES[name]
    return {**deepcopy(body), '$defs': {k: deepcopy(_SCHEMA_DEFINITIONS[k]) for k in names}}


def concentration_window_selection_schema(): return _schema('SELECTION')
def concentration_window_extraction_schema(): return _schema('EXTRACTION')
def concentration_window_calculation_inputs_schema(): return _schema('CALCULATION_INPUTS')
def concentration_window_sheet_schema(): return _schema('SHEET')
def concentration_window_covariance_schema(): return _schema('COVARIANCE_DOCUMENT')


def _fail(code, field): raise ExperimentalContractError(code, field)
def _digest(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
def _exact(v): return dict(numerator=str(v.numerator), denominator=str(v.denominator))
def _q(v):
    q = Fraction(int(v['numerator']), int(v['denominator']))
    if _exact(q) != v: _fail('canonical_exact_fraction_required', 'exact_value')
    return q
def _float(q):
    try: value = float(q)
    except (ArithmeticError, ValueError): return None
    return value if math.isfinite(value) and (value != 0 or q == 0) else None
def _reasons(): return {k: [] for k in _REASON_NAMES}
def _merge(*groups):
    return {k: list(dict.fromkeys(x for g in groups for x in g[k])) for k in _REASON_NAMES}
def _check(value, name): validate_schema(value, _schema(name))
def _same(a, b, field):
    if a != b: _fail('concentration_window_saved_arithmetic_mismatch', field)


def _binding(f): return {k: v for k, v in f.items() if k != 'quote'}


class _Reader:
    def __init__(self, read_source):
        self.sources = _Sources(read_source)
        self.books = {}

    def close(self):
        for book, connection, _, _, _ in self.books.values():
            connection.close(); book.close()

    def artifacts(self):
        return [dict(source_ref=ref, representation=rep, artifact_ref=s['artifact_ref'],
                     sha256=hashlib.sha256(s['content']).hexdigest())
                for (ref, rep), s in sorted(self.sources.cache.items())]

    def book(self, reference):
        if reference not in self.books:
            source = self.sources.source(reference, 'original')
            book = Workbook.__new__(Workbook)
            connection = sqlite3.connect(':memory:')
            try:
                book.archive = zipfile.ZipFile(io.BytesIO(source['content']))
                layout = book.layout()
                if layout['shared_strings_failure'] or book.index_strings(connection, layout['shared_strings_part']):
                    _fail('xlsx_shared_string_reference_unresolved', 'source_ref')
                self.books[reference] = (book, connection, layout, {}, {})
            except Exception:
                connection.close()
                if hasattr(book, 'archive'): book.close()
                raise
        return self.books[reference]

    def cell(self, f):
        book, connection, layout, parts, string_spans = self.book(f['source_ref'])
        selected = [s for s in layout['sheets'] if all(s[k] == f[k] for k in ('sheet_key', 'name', 'worksheet_part'))] if 'name' in f else [
            s for s in layout['sheets'] if s['sheet_key'] == f['sheet_key'] and s['name'] == f['sheet_name'] and s['worksheet_part'] == f['worksheet_part']]
        if len(selected) != 1 or not selected[0]['available']:
            _fail('concentration_window_sheet_binding_mismatch', 'field')
        part = f['worksheet_part']
        if part not in parts:
            with book.open(part) as stream: raw = stream.read()
            root = ET.fromstring(raw)
            cells = {}
            for el in root.iter():
                if el.tag.rsplit('}', 1)[-1] != 'c': continue
                address = el.get('r')
                if address in cells: _fail('concentration_window_duplicate_cell', 'cell')
                cells[address] = Workbook.cell(el, connection)
            spans = {}
            pattern = rb'<(?:[A-Za-z_][\w.-]*:)?c(?=[\s/>])[^>]*(?:/\s*>|>.*?</(?:[A-Za-z_][\w.-]*:)?c\s*>)'
            for match in re.finditer(pattern, raw, re.S):
                el = ET.fromstring(match.group()) if b':' not in match.group().split(b'>', 1)[0].split(b' ', 1)[0] else None
                if el is None: _fail('xlsx_namespaced_cell_span_unsupported', 'cell')
                address = el.get('r')
                if address in spans: _fail('concentration_window_duplicate_cell', 'cell')
                spans[address] = (match.start(), match.end())
            if set(spans) != set(cells): _fail('concentration_window_sheet_binding_mismatch', 'cell')
            parts[part] = (raw, cells, spans)
        raw, cells, spans = parts[part]
        if f['cell'] not in cells: _fail('concentration_window_sheet_binding_mismatch', 'cell')
        cell = cells[f['cell']]
        if cell['error'] or cell['value'] is None or cell['cell_type'] not in ('n', 's', 'str', 'inlineStr'):
            _fail('xlsx_source_or_selection_invalid', 'cell')
        text = cell['value']
        start, end = f['decoded_start'], f['decoded_end']
        if not 0 <= start < end <= len(text): _fail('source_span_out_of_bounds', 'field')
        if text[start:end] != f['quote']: _fail('source_quote_mismatch', 'field')
        shared = None
        if cell['cell_type'] == 's':
            part_s = layout['shared_strings_part']
            if part_s not in string_spans:
                with book.open(part_s) as stream: strings = stream.read()
                matches = list(re.finditer(rb'<si(?=[\s>])[^>]*>.*?</si\s*>', strings, re.S))
                string_spans[part_s] = (strings, matches)
            strings, matches = string_spans[part_s]
            ordinal = int(cell['raw_value'])
            if not 0 <= ordinal < len(matches): _fail('xlsx_shared_string_reference_unresolved', 'cell')
            span = matches[ordinal]
            shared = dict(member=part_s, member_sha256=hashlib.sha256(strings).hexdigest(), start=span.start(), end=span.end())
        source = self.sources.source(f['source_ref'], 'original')
        location = dict(kind='xlsx_cell', source_ref=f['source_ref'], artifact_ref=source['artifact_ref'],
            representation='original', worksheet_part=part, member_sha256=hashlib.sha256(raw).hexdigest(),
            sheet_key=f['sheet_key'], sheet_name=f['sheet_name'], cell=f['cell'],
            xml_start=spans[f['cell']][0], xml_end=spans[f['cell']][1], decoded_start=start, decoded_end=end,
            shared_string_location=shared)
        return text, location, cell

    def field(self, f):
        if f is None: return None
        if f['kind'] == 'text':
            selected = {k: v for k, v in f.items() if k != 'kind'}
            self.sources.witness(selected, 'field')
        else: self.cell(f)
        return f

    def number(self, selector):
        f = selector['field']; self.field(f)
        ns, ne = selector['number_start'], selector['number_end']
        if f['kind'] == 'text':
            w = {k: v for k, v in f.items() if k != 'kind'}
            result = _lexical_number(dict(witness=w, number_start=ns, number_end=ne), self.sources)
            enriched = self.sources.witness(w, 'number')
            absolute_start = f['start'] + len(f['quote'][:ns].encode())
            absolute_end = f['start'] + len(f['quote'][:ne].encode())
            _visible_span(self.sources, enriched, absolute_start, absolute_end, 'number')
            if _soft_break_numeric_token(self.sources, enriched, ns, ne, result['raw_number'], pm_spread=False):
                _fail('partial_source_numeric_token', 'number')
            location = dict(kind='text', source_ref=f['source_ref'], artifact_ref=enriched['artifact_ref'],
                representation=f['representation'], start=absolute_start, end=absolute_end)
            prefix, suffix = _field_contexts(self.sources, enriched, ns, ne)
            formula = False
        else:
            text, location, cell = self.cell(f)
            # A numeric cell selector includes its complete decoded field. This
            # retains visible qualifiers for source-free later validation.
            if f['decoded_start'] != 0 or f['decoded_end'] != len(text):
                _fail('partial_source_numeric_token', 'number.field')
            virtual = _Sources(lambda _ref, _rep: dict(artifact_ref='decoded_cell', content=text.encode()))
            w = dict(source_ref='decoded_cell', representation='original', start=0, end=len(text.encode()), quote=text)
            result = _lexical_number(dict(witness=w, number_start=ns, number_end=ne), virtual)
            prefix, suffix = _field_contexts(virtual, virtual.witness(w, 'number'), ns, ne)
            formula = cell['value_is_formula_cache']
        return result, location, prefix, suffix, formula


def _validate_fields(selection, reader):
    def visit(v):
        if isinstance(v, dict):
            if v.get('kind') in ('text', 'xlsx_cell_slice'):
                reader.field(v); return
            if set(v) == {'value', 'witnesses'}:
                required = 2 if v['value'] == 'conflicting' else 0 if v['value'] == 'unknown' else 1
                if len({_digest(_binding(w)) for w in v['witnesses']}) < required:
                    _fail('interpretation_witness_required', 'witnesses')
            for child in v.values(): visit(child)
        elif isinstance(v, list):
            for child in v: visit(child)
    visit(selection)


def _unit_scale(raw, role):
    text = re.sub(r'\s+', '', html.unescape(re.sub(r'</?[A-Za-z_][^<>]*>', '', raw))).replace('µ', 'u').replace('μ', 'u')
    if role.startswith('coordinate'):
        return ('s', Fraction(1)) if text in ('s','sec','second','seconds') else (
            ('s', Fraction(60)) if text in ('min','minute','minutes') else
            ('s', Fraction(3600)) if text in ('h','hr','hour','hours') else (None,None))
    for prefix, scale in (('',1000000), ('m',1000), ('u',1), ('n',Fraction(1,1000)), ('p',Fraction(1,1000000))):
        if text in (prefix+'M', prefix+'mol/L', prefix+'molL^-1', prefix+'molL−1'):
            return 'uM', Fraction(scale)
    return None, None


def _unit(field, role, reader, suffix=None):
    if field is None: return None, None
    reader.field(field)
    if field['kind'] == 'text':
        w = reader.sources.witness({k:v for k,v in field.items() if k!='kind'}, 'unit')
        before, after = _field_contexts(reader.sources, w, 0, len(w['quote']))
    else:
        text, _, _ = reader.cell(field)
        before, after = text[:field['decoded_start']], text[field['decoded_end']:]
    if (before[-1:] and (before[-1:].isalpha() or before[-1:] in '/_^µμ') or
            _unit_continuation(after) or re.match(r'\s+per\b', after)):
        _fail('source_unit_mismatch', 'unit')
    unit, scale = _unit_scale(field['quote'], role)
    if suffix is not None:
        incompatible = re.match(r'\s*(?:%|(?i:percent\b|per\s+cent\b|fraction\b|dimensionless\b)|[pnumkµμ]?g(?![A-Za-z_µμ]))',suffix)
        if scale is not None and incompatible:
            _fail('source_unit_mismatch','number.unit')
        printed = re.match(r'\s*([munpµμ]?M|[munpµμ]?mol\s*/\s*L|s|sec(?:ond)?s?|min(?:ute)?s?|h|hr|hours?)(?![A-Za-z_µμ])', suffix)
        if printed and (_unit_continuation(suffix[printed.end():]) or _unit_scale(printed.group(1), role) != (unit, scale)):
            _fail('source_unit_mismatch', 'number.unit')
    return unit, scale


def _grid(selection):
    g = selection['grid']
    workbook_fields = []
    def collect(v):
        if isinstance(v, dict):
            if v.get('kind') == 'xlsx_cell_slice': workbook_fields.append(v)
            else:
                for c in v.values(): collect(c)
        elif isinstance(v,list):
            for c in v: collect(c)
    collect(selection['quantities'])
    if workbook_fields and g is None: _fail('concentration_window_sheet_binding_mismatch', 'grid')
    if g is None: return
    if len(set(g['columns'].values()) | {g['coordinate_column']}) != 4 or len({g['header_row'],g['start_row'],g['end_row']}) != 3:
        _fail('concentration_window_sheet_binding_mismatch', 'grid')
    def field_at(f, cell):
        if f is None or f['kind'] != 'xlsx_cell_slice' or f['cell'] != cell or any(
                f[k] != g[k] for k in ('source_ref','sheet_key','sheet_name','worksheet_part')):
            _fail('concentration_window_sheet_binding_mismatch', 'field')
    for role,q in selection['quantities'].items():
        if q is None or q['number'] is None or q['number']['field']['kind'] != 'xlsx_cell_slice': continue
        base, endpoint = role.rsplit('_',1)
        column = g['coordinate_column'] if base=='coordinate' else g['columns'][base]
        row = g[endpoint+'_row']
        field_at(q['number']['field'],column+str(row))
        field_at(q['analyte'],column+str(g['header_row']))
        field_at(q['coordinate'],g['coordinate_column']+str(row))
        if q['unit'] is not None and q['unit']['kind']=='xlsx_cell_slice':
            assoc=q['unit_association']['value']
            if assoc=='source_header': field_at(q['unit'],column+str(g['header_row']))
            elif assoc=='source_shared_header':
                if int(re.fullmatch(r'[A-Z]+([1-9][0-9]*)',q['unit']['cell']).group(1))!=g['header_row'] or any(q['unit'][k]!=g[k] for k in ('source_ref','sheet_key','sheet_name','worksheet_part')):
                    _fail('concentration_window_sheet_binding_mismatch','unit')


def _text_association(q, number, location, reader):
    f=q['number']['field']
    if f['kind'] != 'text': return
    record=q['record']
    if record is None: _fail('concentration_window_record_association_mismatch','record')
    if any(record[k]!=f[k] for k in ('source_ref','representation')) or not record['start']<=location['start']<location['end']<=record['end']:
        _fail('concentration_window_record_association_mismatch','record')
    for key in ('analyte','coordinate'):
        w=q[key]
        if w is None: continue
        if w['kind']!='text' or any(w[k]!=record[k] for k in ('source_ref','representation')):
            _fail('concentration_window_record_association_mismatch',key)
        enriched=reader.sources.witness({k:v for k,v in w.items() if k!='kind'},key)
        inside=record['start']<=w['start']<w['end']<=record['end']
        if key=='analyte' and not getattr(reader,'retained_only',False):
            _associate({**number,'number_start_bytes':location['start'],'number_end_bytes':location['end']},enriched,reader.sources,key)
            table,_=_table_cells(reader.sources,enriched)
            if not inside and table is None: _fail('concentration_window_record_association_mismatch',key)
        elif key=='coordinate' and not inside: _fail('concentration_window_record_association_mismatch',key)
    unit=q['unit']
    if q['unit_association']['value']=='same_record' and unit is not None and (
            unit['kind']!='text' or any(unit[k]!=record[k] for k in ('source_ref','representation')) or
            not record['start']<=unit['start']<unit['end']<=record['end']):
        _fail('concentration_window_record_association_mismatch','unit')
    if unit is not None and unit['kind']=='text' and q['unit_association']['value']=='source_header' and not getattr(reader,'retained_only',False):
        _associate({**number,'number_start_bytes':location['start'],'number_end_bytes':location['end']},
            reader.sources.witness({k:v for k,v in unit.items() if k!='kind'},'unit'),reader.sources,'unit')


def _quantity(role,q,selection,reader):
    if q is None: return None
    why=_reasons(); raw=None; relation='none'; approximate=False; value=None; ex=None; locations=[]; formula=False
    unit,scale=_unit(q['unit'],role,reader)
    if q['unit'] is None: why['source'].append('unit_unavailable')
    elif scale is None: why['implementation'].append('source_unit_unsupported')
    if q['number'] is None:
        why['source'].append('native_nondetection' if q['reading_meaning']['value']=='reported_nondetection' else 'number_unavailable')
    else:
        try:
            n,location,_,suffix,formula=reader.number(q['number']); raw=n['raw_number']
            _text_association(q,n,location,reader)
            unit,scale=_unit(q['unit'],role,reader,suffix)
            locations=[location];relation='eq' if n['relation']=='point' else n['relation'];approximate=n['approximate']
            ex=Fraction(raw.replace('−','-'))*scale if scale is not None else None
            value=_float(ex) if ex is not None else None
            if ex is not None and value is None: why['domain'].append('numerical_model_range');ex=None
        except ExperimentalContractError as error:
            if error.code!='numerical_model_range': raise
            raw=q['number']['field']['quote'][q['number']['number_start']:q['number']['number_end']]
            why['domain'].append('numerical_model_range')
    approximate=approximate or q['reading_meaning']['value']=='source_qualified_approximate'
    if formula:why['implementation'].append('formula_cache_point_unimplemented');value=ex=None
    nd=q['reading_meaning']['value']=='reported_nondetection'
    if nd:
        if 'native_nondetection' not in why['source']:why['source'].append('native_nondetection')
        if relation=='eq':value=ex=None
    status='nondetection' if nd else 'unavailable' if value is None else 'bounded' if relation not in ('eq','none') else 'point'
    number_binding=None if q['number'] is None else {'field':_binding(q['number']['field']),
        'number_start':q['number']['number_start'],'number_end':q['number']['number_end']}
    key='source_observation:'+_digest(number_binding if number_binding else {'role':role,'selection':q})
    physical=None if q['measurement_identity'] is None else 'physical:'+_digest(_binding(q['measurement_identity']))
    deps=[key]
    if not role.startswith('coordinate'):
        for name in ('calibration','normalization'):
            if selection['assay'][name] is not None:deps.append(name+':'+_digest(_binding(selection['assay'][name])))
    return dict(role=role,value=value,exact_value=_exact(ex) if ex is not None else None,unit=unit,
        raw_number=raw,raw_unit=q['unit']['quote'] if q['unit'] else None,
        unit_multiplier=_exact(scale) if scale is not None else None,relation=relation,status=status,
        approximate=approximate,origin='synthetic' if selection['source_kind']=='synthetic_fixture' else
        'graph_derived' if selection['source_kind']=='graph_extraction' else 'reported',
        owner_key=key,physical_owner_key=physical,dependency_keys=deps,locations=locations,
        reported_uncertainty=deepcopy(q['uncertainty']),reasons=why)


def _coefficients(selection,reader):
    result={}
    for name,model in selection['stoichiometry'].items():
        why=_reasons();q=None;origin='unavailable';deps=[]
        if model is None:why['selection'].append('coefficient_not_selected')
        else:
            deps=['chemical_relation:'+_digest(_binding(model['reaction']))]
            if model['relationship']['value']!='supported':why['relationship'].append('coefficient_meaning_unresolved')
            if model['kind']=='implicit_unit_coefficient':
                if model['number'] is not None:_fail('concentration_window_saved_selection_mismatch','stoichiometry.number')
                if not why['relationship']:q=Fraction(1);origin='implicit_chemical_notation'
            elif model['number'] is None:why['source'].append('number_unavailable')
            else:
                number,_,_,_,formula=reader.number(model['number'])
                if formula:why['implementation'].append('formula_cache_point_unimplemented')
                elif number['relation']!='point':why['implementation'].append('bounded_arithmetic_unimplemented')
                elif number['approximate']:why['implementation'].append('approximate_arithmetic_unimplemented')
                elif not why['relationship']:
                    q=Fraction(number['raw_number'].replace('−','-'));origin='synthetic' if selection['source_kind']=='synthetic_fixture' else 'reported'
                deps.append('coefficient:'+_digest(model['number']))
            if q is not None and q<=0:why['domain'].append('positive_coefficient_required');q=None;origin='unavailable'
        result[name]=dict(value=_float(q) if q is not None else None,exact_value=_exact(q) if q is not None else None,
            origin=origin,dependency_keys=deps,reasons=why)
    return result


def _scientific_context(selection,coefficients,artifacts):
    roster={(a['source_ref'],a['representation']):a for a in artifacts}
    def sf(field,support=False):
        if field is None:return dict(status='not_selected',scientific_text=None,display_status='not_selected',binding=None,artifact_ref=None,source_sha256=None)
        a=roster[field['source_ref'],field['representation']]
        return dict(status='retained',scientific_text=None if support else field['quote'],
            display_status='support_location_only' if support else 'semantic_context',binding=_binding(field),
            artifact_ref=a['artifact_ref'],source_sha256=a['sha256'])
    def meaning(v):return dict(value=v['value'],witnesses=[sf(w,True) for w in v['witnesses']])
    assay={k:sf(v) for k,v in selection['assay'].items() if k not in ('arrangement','participants')}
    assay.update(arrangement=meaning(selection['assay']['arrangement']),participants=[{**deepcopy(p),'identity':sf(p['identity'])} for p in selection['assay']['participants']])
    quantities={}
    for role,q in selection['quantities'].items():
        quantities[role]=dict(selection_status='selected' if q else 'not_selected',
            **{k:sf(q[k] if q else None,k in ('coordinate','record','measurement_identity')) for k in ('analyte','coordinate','unit','record','measurement_identity')},
            **{k:meaning(q[k]) if q else dict(value='unknown',witnesses=[]) for k in ('reading_meaning','concentration_basis','unit_association')},
            uncertainty=[sf(w,True) for w in q['uncertainty']] if q else [])
    stoich={}
    for name,model in selection['stoichiometry'].items():
        pair=selection['quantities'][name+'_start']
        stoich[name]=dict(selection_status='selected' if model else 'not_selected',kind=model['kind'] if model else None,
            **deepcopy(coefficients[name]),relationship=meaning(model['relationship']) if model else dict(value='unknown',witnesses=[]),
            reaction=sf(model['reaction'] if model else None,True),
            coefficient_token_support=sf(model['number']['field'] if model and model['number'] else None,True),
            analyte=sf(pair['analyte'] if pair else None),operand_roles=[name+'_start',name+'_end'],
            coefficient_meaning='moles_of_selected_analyte_per_reaction_equivalent',conversion_direction='selected_concentration_change_divided_by_coefficient')
    return dict(usage='host_scientific_context_requires_scoped_parent_projection',assay=assay,quantities=quantities,stoichiometry=stoich,
        pair_relationships={a:{k:meaning(v) for k,v in p.items()} for a,p in selection['pair_relationships'].items()},
        cross_relationships={a:{k:meaning(v) for k,v in p.items()} for a,p in selection['cross_relationships'].items()},
        timing=dict(source_meaning=meaning(selection['timing']['source_meaning']),scenario=deepcopy(selection['timing']['scenario'])))


def _psd(matrix):
    a=deepcopy(matrix);n=len(a)
    if any(a[i][j]!=a[j][i] for i in range(n) for j in range(n)):return False
    for k in range(n):
        if a[k][k]<0:return False
        if a[k][k]==0:
            if any(a[k][j]!=0 for j in range(k+1,n)):return False
            continue
        for i in range(k+1,n):
            for j in range(i,n):a[i][j]-=a[i][k]*a[k][j]/a[k][k];a[j][i]=a[i][j]
    return True


def _validate_covariance(cov,quantities):
    if cov is None:return
    doc=cov['document'];_check(doc,'COVARIANCE_DOCUMENT');roles=doc['roles'];n=len(roles)
    if not n or len(doc['owner_keys'])!=n or len(doc['units'])!=n or len(doc['dependency_keys'])!=n:
        _fail('concentration_window_covariance_matrix_invalid','roles')
    for i,r in enumerate(roles):
        row=quantities[r]
        if row is None or row['status']!='point' or row['approximate'] or row['owner_key']!=doc['owner_keys'][i]:
            _fail('concentration_window_covariance_owner_mismatch',r)
        if row['unit']!=doc['units'][i]:_fail('concentration_window_covariance_unit_mismatch',r)
        if row['dependency_keys']!=doc['dependency_keys'][i]:_fail('concentration_window_covariance_dependency_mismatch',r)
    if doc['variance_status']=='unknown':
        if doc['covariance'] is not None or cov['matrix_exact'] is not None:_fail('concentration_window_covariance_matrix_invalid','covariance')
        return
    matrix=cov['matrix_exact']
    if matrix is None or len(matrix)!=n or any(len(row)!=n for row in matrix):_fail('concentration_window_covariance_matrix_invalid','covariance')
    q=[[_q(x) for x in row] for row in matrix]
    if not _psd(q) or doc['covariance']!=[[_float(x) for x in row] for row in q] or any(_float(x) is None for row in q for x in row):
        _fail('concentration_window_covariance_matrix_invalid','covariance')


def _covariance(selection,reader,quantities):
    reference=selection['covariance_source_ref'];material=selection['covariance_material']
    if material=='not_selected':
        if reference is not None:_fail('concentration_window_saved_selection_mismatch','covariance_source_ref')
        return None
    if reference is None:_fail('concentration_window_saved_selection_mismatch','covariance_source_ref')
    source=reader.sources.source(reference,'original')
    if material=='unsupported_observation_table':return None
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:_fail('duplicate_json_key','covariance')
            d[k]=v
        return d
    def bad(_):_fail('concentration_window_covariance_matrix_invalid','covariance')
    try:exact_doc=json.loads(source['content'],parse_float=Fraction,object_pairs_hook=pairs,parse_constant=bad)
    except (json.JSONDecodeError,UnicodeDecodeError) as error:raise ExperimentalContractError('concentration_window_covariance_matrix_invalid','covariance') from error
    def floats(v):
        if isinstance(v,Fraction):return _float(v)
        if isinstance(v,list):return [floats(x) for x in v]
        if isinstance(v,dict):return {k:floats(x) for k,x in v.items()}
        return v
    document=floats(exact_doc)
    try:_check(document,'COVARIANCE_DOCUMENT')
    except ContractError as error:raise ExperimentalContractError('concentration_window_covariance_matrix_invalid','covariance') from error
    # Validate closed shape and scalar types before .get or matrix iteration.
    # Detailed owner/unit/dependency checks remain in _validate_covariance.
    matrix=exact_doc['covariance']
    exact_matrix=None if matrix is None else [[_exact(Fraction(x)) for x in row] for row in matrix]
    result=dict(document=document,source_ref=reference,artifact_ref=source['artifact_ref'],
        sha256=hashlib.sha256(source['content']).hexdigest(),matrix_exact=exact_matrix)
    _validate_covariance(result,quantities)
    return result


def read_concentration_window_inputs(selection,*,read_source):
    """Authenticate selected original fields; retain independent partial roles."""
    _check(selection,'SELECTION');selection=deepcopy(selection);reader=_Reader(read_source)
    try:
        reader.sources.source(selection['source_ref'],'original')
        _validate_fields(selection,reader);_grid(selection)
        rows={r:_quantity(r,q,selection,reader) for r,q in selection['quantities'].items()}
        coefficients=_coefficients(selection,reader)
        covariance=_covariance(selection,reader,rows)
        artifacts=reader.artifacts()
        result=dict(version='a105_concentration_window_extraction_v2',selection=selection,selection_digest=_digest(selection),
            scientific_context=_scientific_context(selection,coefficients,artifacts),quantities=rows,
            coefficients=coefficients,covariance=covariance,source_artifacts=artifacts)
        _check(result,'EXTRACTION')
        return result
    finally:reader.close()


def _retained_reader(selection,extraction):
    """Sparse selected text/decoded-cell adapter; never claims byte reauthentication.

    Exact actual byte reauthentication uses the optional real source callback.
    The source-free path checks retained lexical/semantic consistency and never
    acquires a source, reparses a workbook or verifies a host receipt.
    """
    artifacts={(a['source_ref'],a['representation']):a for a in extraction['source_artifacts']}
    if len(artifacts)!=len(extraction['source_artifacts']):_fail('source_artifact_mismatch','source_artifacts')
    class Saved:
        def field(self,f):
            if f is None:return None
            if (f['source_ref'],f['representation']) not in artifacts:_fail('source_artifact_mismatch','field')
            if f['kind']=='text' and (f['end']-f['start']!=len(f['quote'].encode())):_fail('source_quote_mismatch','field')
            if f['kind']=='xlsx_cell_slice' and f['decoded_end']-f['decoded_start']!=len(f['quote']):_fail('source_quote_mismatch','field')
            return f
        def number(self,n):
            f=n['field'];self.field(f)
            selected=[row for row in extraction['quantities'].values() if row is not None and row['locations'] and
                _location_matches_field(row['locations'][0],f)]
            if f['kind']=='xlsx_cell_slice':
                lexical=_Sources(lambda _r,_p:dict(artifact_ref='retained',content=f['quote'].encode()))
                w=dict(source_ref='retained',representation='original',start=0,end=len(f['quote'].encode()),quote=f['quote'])
                got=_lexical_number(dict(witness=w,number_start=n['number_start'],number_end=n['number_end']),lexical)
                prefix,suffix=_field_contexts(lexical,lexical.witness(w,'number'),n['number_start'],n['number_end'])
            else:
                containers=[v for v in _fields(selection) if v['kind']=='text' and
                    (v['source_ref'],v['representation'])==(f['source_ref'],f['representation']) and v['start']<=f['start']<f['end']<=v['end']]
                container=max(containers,key=lambda v:v['end']-v['start'])
                content=b' '*container['start']+container['quote'].encode()
                lexical=_Sources(lambda _r,_p:dict(artifact_ref=artifacts[f['source_ref'],f['representation']]['artifact_ref'],content=content))
                w={k:v for k,v in f.items() if k!='kind'}
                got=_lexical_number(dict(witness=w,number_start=n['number_start'],number_end=n['number_end']),lexical)
                prefix,suffix=_field_contexts(lexical,lexical.witness(w,'number'),n['number_start'],n['number_end'])
            # Formula-cache implementation state is retained, not inferred anew
            # from an unavailable ZIP. A real-source validator verifies it.
            formula=bool(selected and 'formula_cache_point_unimplemented' in selected[0]['reasons']['implementation'])
            if not selected:
                location=dict(kind='text',source_ref=f['source_ref'],artifact_ref=artifacts[f['source_ref'],f['representation']]['artifact_ref'],
                    representation=f['representation'],start=f.get('start',0),end=f.get('end',1))
            else:location=deepcopy(selected[0]['locations'][0])
            return got,location,prefix,suffix,formula
        def cell(self,f):
            self.field(f)
            fields=[v for v in _fields(selection) if v['kind']=='xlsx_cell_slice' and all(
                v[k]==f[k] for k in ('source_ref','worksheet_part','sheet_key','sheet_name','cell'))]
            characters=[' ']*max(v['decoded_end'] for v in fields)
            for v in fields:characters[v['decoded_start']:v['decoded_end']]=v['quote']
            return ''.join(characters),{},dict(value_is_formula_cache=False)
    return Saved()


def _fields(v):
    if isinstance(v,dict):
        if v.get('kind') in ('text','xlsx_cell_slice'):yield v
        else:
            for x in v.values():yield from _fields(x)
    elif isinstance(v,list):
        for x in v:yield from _fields(x)


def _location_matches_field(location,field):
    if any(location.get(k)!=field[k] for k in ('source_ref','representation')):return False
    if field['kind']=='xlsx_cell_slice':return all(location.get(k)==field[k] for k in ('worksheet_part','sheet_key','sheet_name','cell','decoded_start','decoded_end'))
    return field['start']<=location.get('start',-1)<location.get('end',-1)<=field['end']


def validate_concentration_window_extraction(extraction,*,selection,read_source=None):
    """Check authoritative selection and retained meanings; optional real custody."""
    _check(extraction,'EXTRACTION');_check(selection,'SELECTION')
    if extraction['selection']!=selection or extraction['selection_digest']!=_digest(selection):
        _fail('concentration_window_saved_selection_mismatch','selection')
    if read_source is not None:
        _same(extraction,read_concentration_window_inputs(selection,read_source=read_source),'extraction')
        return extraction
    saved=_retained_reader(selection,extraction)
    _validate_fields(selection,saved);_grid(selection)
    # Recompute quantities with retained source fields. Text association geometry
    # and original ZIP/member digests are reauthenticated only with read_source.
    rows={}
    for role,q in selection['quantities'].items():
        if q is None:rows[role]=None;continue
        class ArithmeticSaved:
            retained_only=True
            def field(self,f):return saved.field(f)
            def number(self,n):return saved.number(n)
            def cell(self,f):return saved.cell(f)
        arithmetic=ArithmeticSaved()
        # Unit/number contexts need the actual selected strings, not IO.
        arithmetic.sources=_SparseSources(selection,extraction)
        rows[role]=_quantity(role,q,selection,arithmetic)
        old=extraction['quantities'][role]
        if rows[role] is not None and old is not None:
            for loc in old['locations']:
                if q['number'] is None or not _location_matches_field(loc,q['number']['field']):
                    _fail('source_artifact_mismatch',role+'.locations')
                a=next((a for a in extraction['source_artifacts'] if a['source_ref']==loc['source_ref'] and a['representation']==loc['representation']),None)
                if a is None or a['artifact_ref']!=loc['artifact_ref']:_fail('source_artifact_mismatch',role+'.artifact_ref')
    _same(rows,extraction['quantities'],'quantities')
    coefficients=_coefficients(selection,saved)
    _same(coefficients,extraction['coefficients'],'coefficients')
    _same(_scientific_context(selection,coefficients,extraction['source_artifacts']),extraction['scientific_context'],'scientific_context')
    cov=extraction['covariance']
    material=selection['covariance_material'];reference=selection['covariance_source_ref']
    if material=='closed_joint_estimator_covariance_document':
        if reference is None or cov is None:_fail('source_artifact_mismatch','covariance')
    elif material=='unsupported_observation_table':
        if reference is None or cov is not None:_fail('source_artifact_mismatch','covariance')
    elif reference is not None or cov is not None:_fail('source_artifact_mismatch','covariance')
    if reference is not None and not any(a['source_ref']==reference and a['representation']=='original' for a in extraction['source_artifacts']):
        _fail('source_artifact_mismatch','covariance')
    _validate_covariance(cov,rows)
    if cov is not None:
        if selection['covariance_material']!='closed_joint_estimator_covariance_document' or cov['source_ref']!=selection['covariance_source_ref']:
            _fail('source_artifact_mismatch','covariance')
        a=next((a for a in extraction['source_artifacts'] if a['source_ref']==cov['source_ref'] and a['representation']=='original'),None)
        if a is None or a['artifact_ref']!=cov['artifact_ref'] or a['sha256']!=cov['sha256']:_fail('source_artifact_mismatch','covariance')
    return extraction


class _SparseSources(_Sources):
    def __init__(self,selection,extraction):
        fields=list(_fields(selection));roster={(a['source_ref'],a['representation']):a for a in extraction['source_artifacts']}
        def read(ref,rep):
            selected=[f for f in fields if f['kind']=='text' and f['source_ref']==ref and f['representation']==rep]
            content=bytearray(b' '*max((f['end'] for f in selected),default=0));written={}
            for f in selected:
                for i,b in enumerate(f['quote'].encode(),f['start']):
                    if i in written and written[i]!=b:_fail('source_quote_mismatch','retained_fields')
                    content[i]=b;written[i]=b
            return dict(artifact_ref=roster[ref,rep]['artifact_ref'],content=bytes(content))
        super().__init__(read)


def compile_concentration_window_inputs(extraction):
    """Losslessly retain validated numerical operands and scientific meanings."""
    validate_concentration_window_extraction(extraction,selection=extraction['selection'])
    s=extraction['selection']
    result=dict(version='a105_concentration_window_calculation_inputs_v3',extraction_digest=_digest(extraction),
        selection_digest=extraction['selection_digest'],source_kind=s['source_kind'],
        scientific_context=deepcopy(extraction['scientific_context']),quantities=deepcopy(extraction['quantities']),
        coefficients=deepcopy(extraction['coefficients']),covariance=deepcopy(extraction['covariance']),
        covariance_material=s['covariance_material'],requested_cells=deepcopy(s['requested_cells']),
        source_artifacts=deepcopy(extraction['source_artifacts']),covariance_context=_covariance_context(extraction))
    _check(result,'CALCULATION_INPUTS');return result


def validate_concentration_window_calculation_inputs(inputs,*,extraction):
    _check(inputs,'CALCULATION_INPUTS')
    _same(inputs,compile_concentration_window_inputs(extraction),'calculation_inputs')
    return inputs


def _covariance_context(extraction):
    """Retain selected uncertainty meaning without returning any matrix values."""
    selection=extraction['selection'];reference=selection['covariance_source_ref']
    context=dict(selection_status='not_selected' if reference is None else 'selected',
        material=selection['covariance_material'],source_ref=reference,artifact_ref=None,sha256=None,
        roles=[],owner_keys=[],units=[],dependency_keys=[],basis=None,variance_status=None,
        origin=None,derivation=None,systematic_coverage=None)
    if reference is not None:
        artifact=next((a for a in extraction['source_artifacts'] if a['source_ref']==reference and a['representation']=='original'),None)
        if artifact is None:_fail('source_artifact_mismatch','covariance_context')
        context.update(artifact_ref=artifact['artifact_ref'],sha256=artifact['sha256'])
    if extraction['covariance'] is not None:
        document=extraction['covariance']['document']
        context.update({k:deepcopy(document[k]) for k in ('roles','owner_keys','units','dependency_keys',
            'basis','variance_status','origin','derivation','systematic_coverage')})
    return context
