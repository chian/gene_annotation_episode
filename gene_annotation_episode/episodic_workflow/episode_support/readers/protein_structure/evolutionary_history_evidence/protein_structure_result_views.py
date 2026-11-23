"""Pure, explicitly selected protein-structure returns (shared contract 380).

Inputs are populated scientific records. This module performs no acquisition,
native parsing, alignment, fitting, distance evaluation, coordinate transform,
artifact publication, or custody authentication. A owns shared scientific types
and definitions; the definitions here describe only D's selected-return layer.
"""
from __future__ import annotations
from copy import deepcopy
import math
from typing import Literal, TypeAlias, TypedDict
from jsonschema import Draft202012Validator, validators
from gene_annotation_episode.episodic_workflow.episode_support.forms.evolutionary_history_evidence.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.episode_support.forms.protein_structure.evolutionary_history_evidence import protein_structure_contracts as a
from gene_annotation_episode.episodic_workflow.episode_support.forms.protein_structure.evolutionary_history_evidence.protein_structure_contracts import AtomIdentity, CalculationParameters, CoordinateSetSelection, CorrespondenceRow, DeclaredResidueIdentity, FileIdentity, MatrixCell, MetadataValueRow, NativeMetricDefinition, NativeQaRow, NumberCell, NumericalParameters, PairSelector, PositionKey, Qualification, ResidueIdentity, ProteinStructureCustody, Role, SavedSheetDescriptor, ScientificMode, SequenceResidueMapRow, Side, State, StructureSelection, StructureSequenceDescriptor, StructuredIssue, UnmappedPosition, VectorCell, InventoryModel, InventoryChain, InventoryPosition, InventoryMetadata, Count, Positive, NonemptyText, ReferenceRef, Sha256, Text, CellVec3, CellSix
ProjectionFamily: TypeAlias = Literal['comparison_summary', 'transform', 'site_measurements', 'correspondence', 'structure_coordinates', 'native_uncertainty', 'structure_inventory', 'extracted_sequence']

class ProjectionWindow(TypedDict):
    offset_0based: Count
    limit: Positive

class ComparisonMembers(TypedDict):
    kind: Literal['comparison']

class TransformMembers(TypedDict):
    kind: Literal['transform']

class EvaluationMembers(TypedDict):
    kind: Literal['evaluation_requests']
    request_indices_0based: list[Count]

class AllEvaluationMembers(TypedDict):
    kind: Literal['all_evaluation_requests']

class CorrespondenceMembers(TypedDict):
    kind: Literal['correspondence_rows']
    correspondence_ids: list[NonemptyText]

class UnmappedMembers(TypedDict):
    kind: Literal['unmapped_positions']
    structure_role: Side
    positions_0based: list[Count]

class CoordinateMembers(TypedDict):
    kind: Literal['coordinate_set']
    coordinate_set_id: NonemptyText

class AtomUncertaintyMembers(TypedDict):
    kind: Literal['atom_uncertainty']
    structure_role: Role
    atom_row_keys: list[NonemptyText]

class QaMembers(TypedDict):
    kind: Literal['qa_rows']
    structure_role: Role
    row_keys: list[NonemptyText]

class MetadataMembers(TypedDict):
    kind: Literal['metadata_rows']
    structure_role: Role
    row_keys: list[NonemptyText]

class InventoryMembers(TypedDict):
    kind: Literal['inventory_rows']
    row_keys: list[NonemptyText]

class AllInventoryMembers(TypedDict):
    kind: Literal['all_inventory_rows']

class AllResiduePositions(TypedDict):
    kind: Literal['all']

class ExplicitResiduePositions(TypedDict):
    kind: Literal['explicit']
    positions_0based: list[Count]

class ExtractedMembers(TypedDict):
    kind: Literal['extracted_sequence']
    residue_positions: AllResiduePositions | ExplicitResiduePositions
ProjectionMembers: TypeAlias = ComparisonMembers | TransformMembers | EvaluationMembers | AllEvaluationMembers | CorrespondenceMembers | UnmappedMembers | CoordinateMembers | AtomUncertaintyMembers | QaMembers | MetadataMembers | InventoryMembers | AllInventoryMembers | ExtractedMembers

class ProjectionSelection(TypedDict):
    projection_id: NonemptyText
    family: ProjectionFamily
    members: ProjectionMembers
    fields: list[NonemptyText]
    window: ProjectionWindow | None
    delivery_kind: Literal['values', 'artifact']

class ProteinResultSelector(TypedDict):
    version: Literal['protein_structure_result_selector']
    acquisition: Literal['complete_bound_bundle', 'retained_sheet_only']
    saved_sheet: SavedSheetDescriptor | None
    parameters: CalculationParameters | None
    projections: list[ProjectionSelection]
    return_saved_sheet: bool
    sequence_allowed_uses: list[Literal['sequence_align', 'structure_correspondence']]

class QuantityPopulation(TypedDict):
    kind: Literal['selected_sequence', 'declared_polymer', 'mapped_pairs', 'available_pairs', 'fit_requests', 'fit_used', 'evaluation_requests', 'evaluation_used', 'native_alignment_columns', 'native_atom', 'native_qa', 'selected_atoms', 'inventory', 'extracted_sequence']
    structure_role: Role | None
    sequence_basis: Literal['observed_polymer', 'mmcif_declared_polymer'] | None
    numerator: Count | None
    denominator: Count | None
    member_ids: list[NonemptyText]

class ComparisonIdentity(TypedDict):
    kind: Literal['comparison']
    fixed_selection: StructureSelection
    moving_selection: StructureSelection
    scientific_mode: ScientificMode
    transform_state: Literal['identifiable_fit', 'supplied', 'nonunique_fit', 'unavailable', 'invalid']

class TransformIdentity(TypedDict):
    kind: Literal['transform']
    direction: Literal['moving_to_fixed']
    convention: Literal['row_vector_y_R_plus_t']

class SiteIdentity(TypedDict):
    kind: Literal['site']
    selector: PairSelector
    correspondence_id: NonemptyText | None
    fixed_position_key: PositionKey | None
    moving_position_key: PositionKey | None

class CorrespondenceIdentity(TypedDict):
    kind: Literal['correspondence']
    correspondence_id: NonemptyText

class UnmappedIdentity(TypedDict):
    kind: Literal['unmapped']
    structure_role: Side
    position_key: PositionKey

class CoordinateIdentity(TypedDict):
    kind: Literal['coordinate']
    coordinate_set_id: NonemptyText
    atom_row_key: NonemptyText | None
    sequence_position_0based: Count | None

class UncertaintyIdentity(TypedDict):
    kind: Literal['uncertainty']
    structure_role: Role
    row_key: NonemptyText

class InventoryIdentity(TypedDict):
    kind: Literal['inventory']
    row_key: NonemptyText

class SequenceHeaderIdentity(TypedDict):
    kind: Literal['sequence_header']
    reference_ref: ReferenceRef | None

class SequencePositionIdentity(TypedDict):
    kind: Literal['sequence_position']
    position_key: PositionKey
    sequence_position_0based: Count

class UnresolvedEvaluationRequest(TypedDict):
    kind: Literal['evaluation_request']
    request_index_0based: Count

class UnresolvedUnmappedPosition(TypedDict):
    kind: Literal['unmapped_position']
    structure_role: Side
    sequence_position_0based: Count

class UnresolvedSequencePosition(TypedDict):
    kind: Literal['sequence_position']
    sequence_position_0based: Count

class UnresolvedRequestIdentity(TypedDict):
    kind: Literal['unresolved_request']
    request: UnresolvedEvaluationRequest | UnresolvedUnmappedPosition | UnresolvedSequencePosition
ProjectionIdentity: TypeAlias = ComparisonIdentity | TransformIdentity | SiteIdentity | CorrespondenceIdentity | UnmappedIdentity | CoordinateIdentity | UncertaintyIdentity | InventoryIdentity | SequenceHeaderIdentity | SequencePositionIdentity | UnresolvedRequestIdentity
FieldValue: TypeAlias = NumberCell | VectorCell | MatrixCell | NumericalParameters | ResidueIdentity | DeclaredResidueIdentity | AtomIdentity | CorrespondenceRow | UnmappedPosition | CellVec3 | CellSix | NativeQaRow | NativeMetricDefinition | MetadataValueRow | InventoryModel | InventoryChain | InventoryPosition | InventoryMetadata | StructureSequenceDescriptor | SequenceResidueMapRow | list[Text | None] | Text | bool | None

class SelectedField(TypedDict):
    field: NonemptyText
    value: FieldValue
    population: QuantityPopulation | None

class ProjectionRow(TypedDict):
    row_key: NonemptyText
    identity: ProjectionIdentity
    values: list[SelectedField]
    issues: list[StructuredIssue]
    qualifications: list[Qualification]

class ProjectionRows(TypedDict):
    version: Literal['protein_structure_projection_rows']
    projection_id: NonemptyText
    family: ProjectionFamily
    selection: ProjectionSelection
    calculation_id: NonemptyText | None
    coordinate_set: CoordinateSetSelection | None
    requested_count: Count
    matched_count: Count
    returned_count: Count
    omitted_count: Count
    rows: list[ProjectionRow]
    state: State
    issues: list[StructuredIssue]
    qualifications: list[Qualification]

class ProjectionCalculation(TypedDict):
    calculation_id: NonemptyText
    input_numerical_sha256: Sha256
    components_file: FileIdentity

class ValuesDelivery(TypedDict):
    kind: Literal['values']
    rows: list[ProjectionRow]

class ArtifactDelivery(TypedDict):
    kind: Literal['artifact']
    table_file: FileIdentity
    row_count: Count
    allowed_use: Literal['read_exact_selected_table']

class ProjectionResult(TypedDict):
    version: Literal['protein_structure_projection']
    projection_id: NonemptyText
    family: ProjectionFamily
    selection: ProjectionSelection
    custody: ProteinStructureCustody
    calculation: ProjectionCalculation | None
    coordinate_set: CoordinateSetSelection | None
    requested_count: Count
    matched_count: Count
    returned_count: Count
    omitted_count: Count
    delivery: ValuesDelivery | ArtifactDelivery
    state: State
    issues: list[StructuredIssue]
    qualifications: list[Qualification]

class ProteinFailureReturn(TypedDict):
    version: Literal['protein_structure_failure_return']
    custody: ProteinStructureCustody | None
    projection_id: NonemptyText | None
    issue: StructuredIssue

class FactSourceDefinition(TypedDict):
    type: Literal['array']
    meaning: NonemptyText
    report_schema: dict
COUNT_FIELDS = tuple('fixed_sequence_length moving_sequence_length fixed_declared_polymer_length\nmoving_declared_polymer_length mapped_pair_count fixed_coordinate_count moving_coordinate_count\navailable_pair_count fixed_unmapped_count moving_unmapped_count fit_requested_count fit_resolved_pair_count\nfit_available_candidate_count fit_used_count fit_excluded_count evaluation_requested_count\nevaluation_resolved_pair_count evaluation_available_candidate_count evaluation_used_count evaluation_excluded_count'.split())
COVERAGE_FIELDS = tuple('fixed_correspondence_coverage moving_correspondence_coverage fixed_coordinate_coverage\nmoving_coordinate_coverage fixed_paired_coordinate_coverage moving_paired_coordinate_coverage\nmapped_pair_coordinate_coverage fit_coverage evaluation_coverage'.split())
ALIGNMENT_FIELDS = tuple('alignment_score alignment_identity_count alignment_substitution_count\nalignment_column_count alignment_fixed_gap_count alignment_moving_gap_count'.split())
AGGREGATE_FIELDS = tuple('fit_sse fit_rmsd evaluation_sse evaluation_rmsd evaluation_mean_distance\nevaluation_min_distance evaluation_max_distance distance_threshold_A above_threshold_count above_threshold_fraction'.split())
TRANSFORM_VECTOR_FIELDS = tuple('translation fixed_centroid moving_centroid singular_values\nfixed_geometry_singular_values moving_geometry_singular_values'.split())
TRANSFORM_NUMBER_FIELDS = tuple('fixed_geometry_rank moving_geometry_rank cross_covariance_rank\nuncorrected_rotation_determinant reflection_correction_sign fit_sse_raw_formula\nfit_sse_roundoff_limit fit_residual_sse'.split())
PROTEIN_STRUCTURE_FIELD_REGISTRY = {'comparison_summary': {'comparison': {k: 'NumberCell' for k in COUNT_FIELDS + COVERAGE_FIELDS + ALIGNMENT_FIELDS + AGGREGATE_FIELDS}}, 'transform': {'transform': {**{k: 'VectorCell' for k in TRANSFORM_VECTOR_FIELDS}, **{k: 'NumberCell' for k in TRANSFORM_NUMBER_FIELDS}, 'rotation': 'MatrixCell', 'cross_covariance': 'MatrixCell', 'fit_member_ids': 'NonemptyText[]', 'numerical_parameters': 'NumericalParameters', 'identifiability': 'TransformState'}}, 'site_measurements': {'evaluation_requests': {'fixed_residue': 'ResidueIdentity|null', 'moving_residue': 'ResidueIdentity|null', 'fixed_declared_residue': 'DeclaredResidueIdentity|null', 'moving_declared_residue': 'DeclaredResidueIdentity|null', 'fixed_atom': 'AtomIdentity|null', 'moving_atom': 'AtomIdentity|null', 'fixed_xyz': 'VectorCell', 'moving_xyz': 'VectorCell', 'moving_transformed_xyz': 'VectorCell', 'residual_xyz': 'VectorCell', 'distance_squared': 'NumberCell', 'distance': 'NumberCell', 'in_fit': 'boolean', 'in_evaluation': 'boolean', 'evaluated': 'boolean', 'above_threshold': 'boolean|null', 'availability_reason': 'Reason|null'}}, 'correspondence': {'correspondence_rows': {'correspondence_row': 'CorrespondenceRow'}, 'unmapped_positions': {'unmapped_position': 'UnmappedPosition'}}, 'structure_coordinates': {'coordinate_set': {'atom_identity': 'AtomIdentity|null', 'residue_identity': 'ResidueIdentity|null', 'declared_residue_identity': 'DeclaredResidueIdentity|null', 'xyz': 'VectorCell'}}, 'native_uncertainty': {'atom_uncertainty': {'occupancy': 'NumberCell', 'b_factor_native': 'NumberCell', 'physical_b_A2': 'NumberCell', 'plddt': 'NumberCell', 'coordinate_standard_uncertainty_xyz_A': 'NumberCell[3]', 'anisotropic_U_A2': 'NumberCell[6]', 'anisotropic_U_standard_uncertainty_A2': 'NumberCell[6]', 'residue_identity': 'ResidueIdentity'}, 'qa_rows': {'qa': 'NativeQaRow', 'metric_definition': 'NativeMetricDefinition'}, 'metadata_rows': {'metadata_value': 'MetadataValueRow'}}, 'structure_inventory': {'inventory_rows': {'model': 'InventoryModel', 'chain': 'InventoryChain', 'position': 'InventoryPosition', 'native_metadata': 'InventoryMetadata'}}, 'extracted_sequence': {'extracted_sequence': {'descriptor': 'StructureSequenceDescriptor|null', 'alignment_sequence': 'Text|null', 'native_symbols': '(Text|null)[]', 'sequence_length': 'NumberCell', 'declared_polymer_length': 'NumberCell', 'residue_map_row': 'SequenceResidueMapRow'}}}
PROTEIN_STRUCTURE_FIELD_REGISTRY['site_measurements']['all_evaluation_requests'] = deepcopy(PROTEIN_STRUCTURE_FIELD_REGISTRY['site_measurements']['evaluation_requests'])
PROTEIN_STRUCTURE_FIELD_REGISTRY['structure_inventory']['all_inventory_rows'] = deepcopy(PROTEIN_STRUCTURE_FIELD_REGISTRY['structure_inventory']['inventory_rows'])
_FIELD_REGISTRY = deepcopy(PROTEIN_STRUCTURE_FIELD_REGISTRY)
_SUMMARY_UNITS = {**{k: 'residue' if k.startswith(('fixed_', 'moving_')) else 'count' if k.endswith(('requested_count', 'excluded_count')) else 'pair' for k in COUNT_FIELDS}, **{k: 'fraction' for k in COVERAGE_FIELDS}, **{k: 'native_alignment_score' if k == 'alignment_score' else 'count' for k in ALIGNMENT_FIELDS}, **{k: 'angstrom_squared' if k.endswith('_sse') else 'count' if k == 'above_threshold_count' else 'fraction' if k == 'above_threshold_fraction' else 'angstrom' for k in AGGREGATE_FIELDS}}
_TRANSFORM_UNITS = {'rotation': 'dimensionless', 'translation': 'angstrom', 'fixed_centroid': 'angstrom', 'moving_centroid': 'angstrom', 'singular_values': 'angstrom_squared', 'fixed_geometry_singular_values': 'angstrom', 'moving_geometry_singular_values': 'angstrom', 'cross_covariance': 'angstrom_squared', **{k: 'count' if k.endswith('_rank') else 'dimensionless' if k in ('uncorrected_rotation_determinant', 'reflection_correction_sign') else 'angstrom_squared' for k in TRANSFORM_NUMBER_FIELDS}}
_UNCERTAINTY_UNITS = {'occupancy': 'fraction', 'b_factor_native': 'native_b_column', 'physical_b_A2': 'angstrom_squared', 'plddt': 'score_0_100', 'coordinate_standard_uncertainty_xyz_A': 'angstrom', 'anisotropic_U_A2': 'angstrom_squared', 'anisotropic_U_standard_uncertainty_A2': 'angstrom_squared'}

def _ref(name):
    return {'$ref': '#/$defs/' + name}

def _obj(**properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def _array(items, *, nonempty=False, unique=False):
    value = {'type': 'array', 'items': items}
    if nonempty:
        value['minItems'] = 1
    if unique:
        value['uniqueItems'] = True
    return value
_TEXT = {'type': 'string', 'pattern': '^[^\\u0000]*$'}
_NAME = {**_TEXT, 'minLength': 1}
_COUNT = {'type': 'integer', 'minimum': 0}
_NULL = {'type': 'null'}

def _nullable(schema):
    return {'anyOf': [schema, _NULL]}

def _field_schema(name):
    if name.endswith('|null') and name != '(Text|null)[]':
        return _nullable(_field_schema(name[:-5]))
    if name == 'NonemptyText[]':
        return _array(_NAME, unique=True)
    if name == '(Text|null)[]':
        return _array(_nullable(_TEXT))
    if name.startswith('NumberCell['):
        size = int(name[-2])
        return {**_array(_ref('NumberCell')), 'minItems': size, 'maxItems': size}
    if name == 'TransformState':
        return {'enum': ['identifiable_fit', 'supplied', 'nonunique_fit', 'unavailable', 'invalid']}
    if name == 'Text':
        return _TEXT
    if name == 'boolean':
        return {'type': 'boolean'}
    return _ref(name)

def _make_definitions():
    shared = a.protein_structure_schema_definitions()
    d = {}
    d['ProjectionWindow'] = _obj(offset_0based=_COUNT, limit={'type': 'integer', 'minimum': 1})
    d['ProjectionFamily'] = {'enum': list(_FIELD_REGISTRY)}
    member_schemas = {'comparison': _obj(kind={'const': 'comparison'}), 'transform': _obj(kind={'const': 'transform'}), 'evaluation_requests': _obj(kind={'const': 'evaluation_requests'}, request_indices_0based=_array(_COUNT, nonempty=True, unique=True)), 'all_evaluation_requests': _obj(kind={'const': 'all_evaluation_requests'}), 'correspondence_rows': _obj(kind={'const': 'correspondence_rows'}, correspondence_ids=_array(_NAME, nonempty=True, unique=True)), 'unmapped_positions': _obj(kind={'const': 'unmapped_positions'}, structure_role=_ref('Side'), positions_0based=_array(_COUNT, nonempty=True, unique=True)), 'coordinate_set': _obj(kind={'const': 'coordinate_set'}, coordinate_set_id=_NAME), 'atom_uncertainty': _obj(kind={'const': 'atom_uncertainty'}, structure_role=_ref('Role'), atom_row_keys=_array(_NAME, nonempty=True, unique=True)), 'qa_rows': _obj(kind={'const': 'qa_rows'}, structure_role=_ref('Role'), row_keys=_array(_NAME, nonempty=True, unique=True)), 'metadata_rows': _obj(kind={'const': 'metadata_rows'}, structure_role=_ref('Role'), row_keys=_array(_NAME, nonempty=True, unique=True)), 'inventory_rows': _obj(kind={'const': 'inventory_rows'}, row_keys=_array(_NAME, nonempty=True, unique=True)), 'all_inventory_rows': _obj(kind={'const': 'all_inventory_rows'}), 'extracted_sequence': _obj(kind={'const': 'extracted_sequence'}, residue_positions={'oneOf': [_obj(kind={'const': 'all'}), _obj(kind={'const': 'explicit'}, positions_0based=_array(_COUNT, nonempty=True, unique=True))]})}
    d['ProjectionMembers'] = {'oneOf': list(member_schemas.values())}
    identities = {'comparison': _obj(kind={'const': 'comparison'}, fixed_selection=_ref('StructureSelection'), moving_selection=_ref('StructureSelection'), scientific_mode=_ref('ScientificMode'), transform_state=_field_schema('TransformState')), 'transform': _obj(kind={'const': 'transform'}, direction={'const': 'moving_to_fixed'}, convention={'const': 'row_vector_y_R_plus_t'}), 'site': _obj(kind={'const': 'site'}, selector=_ref('PairSelector'), correspondence_id=_nullable(_NAME), fixed_position_key=_nullable(_ref('PositionKey')), moving_position_key=_nullable(_ref('PositionKey'))), 'correspondence': _obj(kind={'const': 'correspondence'}, correspondence_id=_NAME), 'unmapped': _obj(kind={'const': 'unmapped'}, structure_role=_ref('Side'), position_key=_ref('PositionKey')), 'coordinate': _obj(kind={'const': 'coordinate'}, coordinate_set_id=_NAME, atom_row_key=_nullable(_NAME), sequence_position_0based=_nullable(_COUNT)), 'uncertainty': _obj(kind={'const': 'uncertainty'}, structure_role=_ref('Role'), row_key=_NAME), 'inventory': _obj(kind={'const': 'inventory'}, row_key=_NAME), 'sequence_header': _obj(kind={'const': 'sequence_header'}, reference_ref=_nullable({'type': 'string', 'pattern': '^reference_[a-f0-9]{24,64}$'})), 'sequence_position': _obj(kind={'const': 'sequence_position'}, position_key=_ref('PositionKey'), sequence_position_0based=_COUNT), 'unresolved_request': _obj(kind={'const': 'unresolved_request'}, request={'oneOf': [_obj(kind={'const': 'evaluation_request'}, request_index_0based=_COUNT), _obj(kind={'const': 'unmapped_position'}, structure_role=_ref('Side'), sequence_position_0based=_COUNT), _obj(kind={'const': 'sequence_position'}, sequence_position_0based=_COUNT)]})}
    d['ProjectionIdentity'] = {'oneOf': list(identities.values())}
    d['QuantityPopulation'] = _obj(kind={'enum': ['selected_sequence', 'declared_polymer', 'mapped_pairs', 'available_pairs', 'fit_requests', 'fit_used', 'evaluation_requests', 'evaluation_used', 'native_alignment_columns', 'native_atom', 'native_qa', 'selected_atoms', 'inventory', 'extracted_sequence']}, structure_role=_nullable(_ref('Role')), sequence_basis=_nullable({'enum': ['observed_polymer', 'mmcif_declared_polymer']}), numerator=_nullable(_COUNT), denominator=_nullable(_COUNT), member_ids=_array(_NAME, unique=True))
    identity_kinds = {'comparison': ['comparison'], 'transform': ['transform'], 'evaluation_requests': ['site', 'unresolved_request'], 'all_evaluation_requests': ['site', 'unresolved_request'], 'correspondence_rows': ['correspondence'], 'unmapped_positions': ['unmapped', 'unresolved_request'], 'coordinate_set': ['coordinate'], 'atom_uncertainty': ['uncertainty'], 'qa_rows': ['uncertainty'], 'metadata_rows': ['uncertainty'], 'inventory_rows': ['inventory'], 'all_inventory_rows': ['inventory'], 'extracted_sequence': ['sequence_header', 'sequence_position', 'unresolved_request']}
    selections, row_types, envelopes, results, selected_fields = ([], [], [], [], [])
    for family, members in _FIELD_REGISTRY.items():
        for kind, registry in members.items():
            suffix = family + '_' + kind
            sname, rname = ('DSelection_' + suffix, 'DRow_' + suffix)
            d[sname] = _obj(projection_id=_NAME, family={'const': family}, members=member_schemas[kind], fields=_array({'enum': list(registry)}, nonempty=True, unique=True), window=_nullable(_ref('ProjectionWindow')), delivery_kind={'enum': ['values', 'artifact']})
            fields = [_obj(field={'const': name}, value=_field_schema(type_name), population=_nullable(_ref('QuantityPopulation'))) for name, type_name in registry.items()]
            selected_fields.extend(fields)
            d[rname] = _obj(row_key=_NAME, identity={'oneOf': [identities[k] for k in identity_kinds[kind]]}, values=_array({'oneOf': fields}), issues=_array(_ref('StructuredIssue')), qualifications=_array(_ref('Qualification'), unique=True))
            base = dict(projection_id=_NAME, family={'const': family}, selection=_ref(sname), coordinate_set=_ref('CoordinateSetSelection') if family == 'structure_coordinates' else _NULL, requested_count=_COUNT, matched_count=_COUNT, returned_count=_COUNT, omitted_count=_COUNT, state=_ref('State'), issues=_array(_ref('StructuredIssue')), qualifications=_array(_ref('Qualification'), unique=True))
            row_type = 'DRows_' + suffix
            d[row_type] = _obj(version={'const': 'protein_structure_projection_rows'}, **base, calculation_id=_nullable(_NAME), rows=_array(_ref(rname)))
            result_type = 'DResult_' + suffix
            d[result_type] = _obj(version={'const': 'protein_structure_projection'}, **base, custody=_ref('ProteinStructureCustody'), calculation=_nullable(_ref('ProjectionCalculation')), delivery={'oneOf': [_obj(kind={'const': 'values'}, rows=_array(_ref(rname))), _ref('ArtifactDelivery')]})
            selections.append(_ref(sname))
            row_types.append(_ref(rname))
            envelopes.append(_ref(row_type))
            results.append(_ref(result_type))
    d['ProjectionSelection'] = {'oneOf': selections}
    d['ProjectionRow'] = {'anyOf': row_types}
    d['SelectedField'] = {'anyOf': selected_fields}
    d['FieldValue'] = {'anyOf': [_field_schema(n) for n in sorted({v for ms in _FIELD_REGISTRY.values() for fs in ms.values() for v in fs.values()})]}
    d['ProjectionRows'] = {'oneOf': envelopes}
    d['ProjectionResult'] = {'oneOf': results}
    d['ProjectionTable'] = _obj(version={'const': 'protein_structure_projection_table'}, rows=_array(_ref('ProjectionRow')))
    d['ProjectionCalculation'] = _obj(calculation_id=_NAME, input_numerical_sha256={'type': 'string', 'pattern': '^[a-f0-9]{64}$'}, components_file=_ref('FileIdentity'))
    d['ArtifactDelivery'] = _obj(kind={'const': 'artifact'}, table_file=_ref('FileIdentity'), row_count=_COUNT, allowed_use={'const': 'read_exact_selected_table'})
    d['ProteinFailureReturn'] = _obj(version={'const': 'protein_structure_failure_return'}, custody=_nullable(_ref('ProteinStructureCustody')), projection_id=_nullable(_NAME), issue=_ref('StructuredIssue'))
    d['ProteinResultSelector'] = _obj(version={'const': 'protein_structure_result_selector'}, acquisition={'enum': ['complete_bound_bundle', 'retained_sheet_only']}, saved_sheet=_nullable(_ref('SavedSheetDescriptor')), parameters=_nullable(_ref('CalculationParameters')), projections=_array(_ref('ProjectionSelection')), return_saved_sheet={'type': 'boolean'}, sequence_allowed_uses=_array({'enum': ['sequence_align', 'structure_correspondence']}, unique=True))
    d['ProjectionInput'] = {'oneOf': [_obj(kind={'const': 'comparison'}, sheet=_ref('ProteinStructureSheet'), components=_ref('ProteinStructureComponents')), _obj(kind={'const': 'inspection'}, inventory=_ref('StructureInventory')), _obj(kind={'const': 'extraction'}, sequence=_ref('StructureSequence'), metadata=_ref('StructureMetadata'), descriptor=_nullable(_ref('StructureSequenceDescriptor')))]}
    if shared.keys() & d.keys():
        raise RuntimeError('Protein return definitions must not replace shared types')
    return {**shared, **d}
_DEFINITIONS = _make_definitions()
_STRICT_VALIDATOR = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine('integer', lambda _, v: type(v) is int).redefine('number', lambda _, v: type(v) in (int, float) and math.isfinite(v)))

def _schema(name, *, array=False):
    definitions = deepcopy(_DEFINITIONS)
    schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$defs': definitions, **(_array(_ref(name)) if array else _ref(name))}
    schema['$id'] = 'urn:gene-annotation:protein-structure:schema:' + digest(schema)
    return schema
_VALIDATORS = {name: _STRICT_VALIDATOR(_schema(name)) for name in ('ProjectionSelection', 'ProjectionRows', 'ProjectionResult', 'ProteinFailureReturn', 'ProjectionInput')}

def protein_structure_fact_sources() -> dict[str, FactSourceDefinition]:
    """Return four detached, self-contained exact source schema resources."""
    sources = {'execution_protein_structure_projections': ('ProjectionResult', 'Exactly selected protein structure values or an exact selected-table descriptor; equality is checked against the original result record.'), 'execution_protein_structure_saved_sheets': ('SavedSheetDescriptor', 'Original saved numerical-sheet descriptor with explicitly granted uses; descriptor receipt is not receipt of unselected values.'), 'execution_protein_structure_sequences': ('StructureSequenceDescriptor', 'Original structure-derived sequence descriptor and explicit downstream uses; original record equality and authority are checked separately.'), 'execution_protein_structure_failures': ('ProteinFailureReturn', 'Recorded structured protein result failure with original identity; no model-authored finding.')}
    return {name: {'type': 'array', 'meaning': meaning, 'report_schema': _schema(record, array=True)} for name, (record, meaning) in sources.items()}

def _json(value):
    if type(value) is dict:
        if any((type(k) is not str or '\x00' in k for k in value)):
            raise ValueError('invalid_schema')
        for item in value.values():
            _json(item)
    elif type(value) is list:
        for item in value:
            _json(item)
    elif type(value) is str:
        if '\x00' in value:
            raise ValueError('invalid_schema')
    elif type(value) is float:
        if not math.isfinite(value):
            raise ValueError('invalid_schema')
    elif value is not None and type(value) not in (int, bool):
        raise ValueError('invalid_schema')

def _shape(name, value):
    _json(value)
    try:
        validator = _VALIDATORS[name]
        valid = validator.is_valid(value)
    except (TypeError, KeyError, RecursionError, OverflowError) as error:
        raise ValueError('invalid_schema') from error
    if not valid:
        raise ValueError('invalid_schema')

def _same(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all((_same(left[k], right[k]) for k in left))
    if type(left) is list:
        return len(left) == len(right) and all((_same(x, y) for x, y in zip(left, right)))
    return left == right

def _unique(values):
    if len({canonical(v) for v in values}) != len(values):
        raise ValueError('duplicate_selection')

def _shared_relations(value):
    """Check embedded selected data without a private A validation hook.

    Shared shapes come unchanged from A. Public A validators own complete shared
    records. Cell/null relationships and envelope identities are also checked
    here because selected fragments need not carry the enclosing full record.
    """
    if type(value) is list:
        for item in value:
            _shared_relations(item)
        return
    if type(value) is not dict:
        return
    version = value.get('version')
    complete = {'structure_sequence_descriptor': a.validate_structure_sequence_descriptor, 'protein_structure_saved_sheet': a.validate_saved_sheet_descriptor, 'protein_structure_calculation_parameters': a.validate_calculation_parameters}.get(version)
    if complete is not None:
        complete(value)
        return
    keys = set(value)
    if keys == {'value', 'state', 'reason', 'unit', 'origin'}:
        present = value['state'] == 'present'
        if present != (value['value'] is not None) or present != (value['reason'] is None):
            raise ValueError('invalid_schema')
        if present and value['unit'] in ('count', 'pair', 'residue') and (type(value['value']) is not int or value['value'] < 0):
            raise ValueError('invalid_schema')
    elif keys == set(FileIdentity.__annotations__):
        a.validate_file_identity(value)
        return
    elif keys == set(StructureSelection.__annotations__):
        a.validate_structure_selection(value)
        return
    elif keys == set(NativeQaRow.__annotations__):
        if (value['scope'] == 'global') != (value['endpoint_1'] is None) or (value['scope'] != 'ordered_pair') != (value['endpoint_2'] is None):
            raise ValueError('metadata_join_conflict')
    for item in value.values():
        _shared_relations(item)

def validate_protein_structure_projection_selection(value: ProjectionSelection) -> ProjectionSelection:
    _shape('ProjectionSelection', value)
    _unique(value['fields'])
    return deepcopy(value)

def _selected_fields(row, selection):
    fields = [v['field'] for v in row['values']]
    _unique(fields)
    if fields != [f for f in selection['fields'] if f in fields]:
        raise ValueError('invalid_schema')
    if not set(fields) <= set(selection['fields']):
        raise ValueError('invalid_schema')
    identity = row['identity']
    if identity['kind'] == 'unresolved_request':
        if fields or not any((i['code'] == 'selected_field_unavailable' for i in row['issues'])):
            raise ValueError('conflicting_identity')
        return
    if identity['kind'] == 'sequence_header' and 'residue_map_row' in fields:
        raise ValueError('invalid_schema')
    if identity['kind'] == 'sequence_position' and fields not in ([], ['residue_map_row']):
        raise ValueError('invalid_schema')
    if identity['kind'] == 'inventory' and len(fields) > 1:
        raise ValueError('invalid_schema')
    expected = [f for f in selection['fields'] if f != 'residue_map_row'] if identity['kind'] == 'sequence_header' else ['residue_map_row'] if identity['kind'] == 'sequence_position' else selection['fields']
    if identity['kind'] != 'inventory' and fields != expected and (not any((i['code'] == 'selected_field_unavailable' for i in row['issues']))):
        raise ValueError('selected_field_unavailable')
    for selected in row['values']:
        field, val, population = (selected['field'], selected['value'], selected['population'])
        spec = _FIELD_REGISTRY[selection['family']][selection['members']['kind']][field]
        numeric = spec in ('NumberCell', 'VectorCell', 'MatrixCell', 'NumberCell[3]', 'NumberCell[6]')
        if numeric != (population is not None):
            raise ValueError('invalid_schema')
        if population is not None:
            _unique(population['member_ids'])
            if population['sequence_basis'] is not None and population['structure_role'] is None:
                raise ValueError('conflicting_identity')
            if spec == 'NumberCell' and val['unit'] in ('count', 'pair', 'residue') and (population['numerator'] != val['value'] or population['denominator'] is not None):
                raise ValueError('conflicting_identity')
            family = selection['family']
            unit = _SUMMARY_UNITS[field] if family == 'comparison_summary' else _TRANSFORM_UNITS[field] if family == 'transform' else _UNCERTAINTY_UNITS[field] if family == 'native_uncertainty' else 'residue' if family == 'extracted_sequence' else 'angstrom_squared' if field == 'distance_squared' else 'angstrom'
            cells = val if spec in ('NumberCell[3]', 'NumberCell[6]') else [val]
            if any((cell['unit'] != unit for cell in cells)):
                raise ValueError('conflicting_identity')
            if family == 'comparison_summary' and (field in COVERAGE_FIELDS or field == 'above_threshold_fraction') and (val['state'] == 'present'):
                if population['numerator'] is None or population['denominator'] is None or population['denominator'] == 0 or (population['numerator'] > population['denominator']):
                    raise ValueError('conflicting_identity')
        if field == 'correspondence_row' and val['correspondence_id'] != identity['correspondence_id']:
            raise ValueError('conflicting_identity')
        if field == 'unmapped_position' and (not _same(val['position_key'], identity['position_key'])):
            raise ValueError('conflicting_identity')
        if field == 'residue_map_row' and (val['sequence_position_0based'] != identity['sequence_position_0based'] or not _same(val['position_key'], identity['position_key'])):
            raise ValueError('conflicting_identity')
        if identity['kind'] == 'inventory' and val['row_key'] != identity['row_key']:
            raise ValueError('conflicting_identity')
        if field in ('qa', 'metadata_value') and (val['row_key'] != identity['row_key'] or val['structure_role'] != identity['structure_role']):
            raise ValueError('conflicting_identity')
        if field == 'descriptor' and val is not None and (val['reference_ref'] != identity['reference_ref']):
            raise ValueError('conflicting_identity')
        if identity['kind'] == 'coordinate' and field == 'atom_identity' and (val is not None) and (val['atom_row_key'] != identity['atom_row_key']):
            raise ValueError('conflicting_identity')
    qa = next((f['value'] for f in row['values'] if f['field'] == 'qa'), None)
    metric = next((f['value'] for f in row['values'] if f['field'] == 'metric_definition'), None)
    if qa is not None and metric is not None and (qa['metric_key'] != metric['metric_key']):
        raise ValueError('metadata_join_conflict')
    if not fields and (not row['issues']):
        raise ValueError('selected_field_unavailable')

def _row_members(row, selection):
    member, identity = (selection['members'], row['identity'])
    kind = member['kind']
    if identity['kind'] == 'unresolved_request':
        requested = identity['request']
        expected = {'evaluation_requests': 'evaluation_request', 'all_evaluation_requests': 'evaluation_request', 'unmapped_positions': 'unmapped_position', 'extracted_sequence': 'sequence_position'}.get(kind)
        if requested['kind'] != expected:
            raise ValueError('conflicting_identity')
        if kind == 'evaluation_requests' and requested['request_index_0based'] not in member['request_indices_0based']:
            raise ValueError('conflicting_identity')
        if kind == 'unmapped_positions' and (requested['structure_role'] != member['structure_role'] or requested['sequence_position_0based'] not in member['positions_0based']):
            raise ValueError('conflicting_identity')
        if kind == 'extracted_sequence' and member['residue_positions']['kind'] == 'explicit' and (requested['sequence_position_0based'] not in member['residue_positions']['positions_0based']):
            raise ValueError('conflicting_identity')
    elif kind == 'correspondence_rows' and identity['correspondence_id'] not in member['correspondence_ids']:
        raise ValueError('conflicting_identity')
    elif kind in ('qa_rows', 'metadata_rows', 'inventory_rows') and identity['row_key'] not in member['row_keys']:
        raise ValueError('conflicting_identity')
    elif kind == 'coordinate_set' and identity['coordinate_set_id'] != member['coordinate_set_id']:
        raise ValueError('conflicting_identity')
    if 'structure_role' in member and 'structure_role' in identity and (member['structure_role'] != identity['structure_role']):
        raise ValueError('conflicting_identity')
    if identity['kind'] == 'comparison' and (identity['fixed_selection']['structure_role'] != 'fixed' or identity['moving_selection']['structure_role'] != 'moving'):
        raise ValueError('conflicting_identity')

def _envelope(value, rows):
    selection = validate_protein_structure_projection_selection(value['selection'])
    if value['projection_id'] != selection['projection_id'] or value['family'] != selection['family']:
        raise ValueError('conflicting_identity')
    n, m, r, o = (value[k] for k in ('requested_count', 'matched_count', 'returned_count', 'omitted_count'))
    if m > n or r > n or o != n - r:
        raise ValueError('conflicting_identity')
    member = selection['members']
    list_key = {'evaluation_requests': 'request_indices_0based', 'correspondence_rows': 'correspondence_ids', 'unmapped_positions': 'positions_0based', 'atom_uncertainty': 'atom_row_keys', 'qa_rows': 'row_keys', 'metadata_rows': 'row_keys', 'inventory_rows': 'row_keys'}.get(member['kind'])
    expected_count = len(member[list_key]) if list_key else 1 if member['kind'] in ('comparison', 'transform') else None
    if member['kind'] == 'extracted_sequence':
        header = int(any((f != 'residue_map_row' for f in selection['fields'])))
        if 'residue_map_row' not in selection['fields']:
            expected_count = header
        elif member['residue_positions']['kind'] == 'explicit':
            expected_count = header + len(member['residue_positions']['positions_0based'])
    if expected_count is not None and n != expected_count:
        raise ValueError('conflicting_identity')
    window = selection['window']
    if r != (n if window is None else min(window['limit'], max(0, n - window['offset_0based']))):
        raise ValueError('conflicting_identity')
    if selection['family'] == 'structure_coordinates':
        if value['coordinate_set']['coordinate_set_id'] != selection['members']['coordinate_set_id']:
            raise ValueError('conflicting_identity')
        coordinate = value['coordinate_set']
        if coordinate['frame'] == 'moving_in_fixed_frame' and coordinate['structure_role'] != 'moving':
            raise ValueError('conflicting_identity')
        if coordinate['members']['kind'] == 'sequence_positions':
            _unique(coordinate['members']['positions'])
    elif value['coordinate_set'] is not None:
        raise ValueError('conflicting_identity')
    comparison = selection['family'] not in ('structure_inventory', 'extracted_sequence') and (not (selection['family'] == 'native_uncertainty' and selection['members']['structure_role'] == 'single'))
    calc = value.get('calculation_id', value.get('calculation'))
    if comparison != (calc is not None):
        raise ValueError('conflicting_identity')
    if rows is not None:
        if len(rows) != r:
            raise ValueError('conflicting_identity')
        _unique([row['row_key'] for row in rows])
        for row in rows:
            _row_members(row, selection)
            _selected_fields(row, selection)
        matched_visible = sum((_row_matched(row) for row in rows))
        if not matched_visible <= m <= matched_visible + o:
            raise ValueError('conflicting_identity')
        if o == 0:
            observed_state = _selected_state(rows)
            if value['state'] == 'complete' and observed_state != 'complete' or (observed_state == 'invalid' and value['state'] != 'invalid'):
                raise ValueError('conflicting_identity')
    _shared_relations(value)

def _row_matched(row):
    identity = row['identity']
    return not (identity['kind'] == 'unresolved_request' or (identity['kind'] == 'coordinate' and identity['atom_row_key'] is None) or any((i['code'] == 'selected_field_unavailable' and i['field'] == 'projection_members' for i in row['issues'])))

def validate_protein_structure_projection_rows(value: ProjectionRows) -> ProjectionRows:
    _shape('ProjectionRows', value)
    _envelope(value, value['rows'])
    return deepcopy(value)

def validate_protein_structure_projection_result(value: ProjectionResult) -> ProjectionResult:
    _shape('ProjectionResult', value)
    delivery = value['delivery']
    if delivery['kind'] != value['selection']['delivery_kind']:
        raise ValueError('conflicting_identity')
    _envelope(value, delivery['rows'] if delivery['kind'] == 'values' else None)
    if value['calculation'] is not None and value['calculation']['components_file']['format'] != 'protein_structure_components':
        raise ValueError('unsupported_format')
    if delivery['kind'] == 'artifact':
        if delivery['table_file']['format'] != 'protein_structure_projection_table':
            raise ValueError('unsupported_format')
        if delivery['row_count'] != value['returned_count']:
            raise ValueError('conflicting_identity')
        if 'artifact_descriptor_not_numerical_delivery' not in value['qualifications']:
            raise ValueError('invalid_schema')
    return deepcopy(value)

def validate_protein_structure_failure_return(value: ProteinFailureReturn) -> ProteinFailureReturn:
    _shape('ProteinFailureReturn', value)
    _shared_relations(value)
    return deepcopy(value)

def _selected_state(rows):
    present, missing, invalid = (False, False, False)

    def visit(value):
        nonlocal present, missing, invalid
        if type(value) is dict:
            if set(value) == {'value', 'state', 'reason', 'unit', 'origin'}:
                present |= value['state'] in ('present', 'not_applicable')
                missing |= value['state'] in ('missing', 'unavailable')
                invalid |= value['state'] == 'invalid'
            else:
                for item in value.values():
                    visit(item)
        elif type(value) is list:
            for item in value:
                visit(item)
    for row in rows:
        missing |= any((i['code'] == 'selected_field_unavailable' for i in row['issues']))
        for field in row['values']:
            value = field['value']
            if type(value) is not dict or 'state' not in value:
                present |= value is not None
            visit(value)
    return 'invalid' if invalid else 'partial' if missing and present else 'unavailable' if missing else 'complete'
