"""Closed protein-structure data contracts and pure structural validation.

The concrete records implement shared contract 380. This module performs no
acquisition, alignment, superposition, resource selection, or authority check.
Schemas are a mechanical projection of these ordinary TypedDict declarations;
scientific calculations remain ordinary functions in the calculator module.
"""
from __future__ import annotations

from copy import deepcopy
import math
import types
from typing import Annotated, Literal, TypeAlias, TypedDict, Union, get_args, get_origin, get_type_hints, is_typeddict

from jsonschema import Draft202012Validator, validators
from .execution_contracts import canonical, digest

Count: TypeAlias = Annotated[int, "count"]
Positive: TypeAlias = Annotated[int, "positive"]
Signed: TypeAlias = int
Real: TypeAlias = float
Text: TypeAlias = Annotated[str, "text"]
NonemptyText: TypeAlias = Annotated[str, "nonempty"]
Sha256: TypeAlias = Annotated[str, "sha256"]
ArtifactRef: TypeAlias = Annotated[str, "artifact_ref"]
SourceRef: TypeAlias = Annotated[str, "source_ref"]
ReferenceRef: TypeAlias = Annotated[str, "reference_ref"]
ObservationRef: TypeAlias = Annotated[str, "observation_ref"]
Vec3: TypeAlias = Annotated[list[Real], "three"]
Mat3: TypeAlias = Annotated[list[Vec3], "three"]
Role: TypeAlias = Literal["single", "fixed", "moving"]
Side: TypeAlias = Literal["fixed", "moving"]
State: TypeAlias = Literal["complete", "partial", "unavailable", "invalid"]
ScientificMode: TypeAlias = Literal["fit_then_evaluate_ca", "evaluate_declared_transform_ca"]
StructureFormat: TypeAlias = Literal["pdb_3x_text", "pdbx_mmcif_text"]
Unit: TypeAlias = Literal["count", "residue", "pair", "fraction", "angstrom", "angstrom_squared", "dimensionless", "native_alignment_score", "native_b_column", "score_0_100", "unknown"]
Origin: TypeAlias = Literal["observed", "native_predicted", "fitted", "derived", "supplied"]
CellState: TypeAlias = Literal["present", "missing", "not_applicable", "invalid", "unavailable"]
IssueCode: TypeAlias = Literal[
    "invalid_schema", "unsupported_format", "malformed_record", "malformed_cif_loop",
    "conflicting_identity", "unselected_data_block", "model_not_found", "chain_not_found",
    "ambiguous_chain", "ambiguous_residue_variant", "ambiguous_ca", "ca_missing",
    "invalid_coordinate_identity", "invalid_occupancy", "zero_occupancy_excluded",
    "nonfinite_coordinate", "unsupported_alignment_symbol", "polymer_mapping_unavailable",
    "empty_sequence", "sequence_not_received", "sequence_artifact_mismatch",
    "alignment_not_received", "alignment_operand_mismatch", "alignment_symbol_mismatch",
    "invalid_traceback", "map_endpoint_missing", "map_not_injective", "map_not_collinear",
    "duplicate_selection", "unmapped_site", "empty_fit", "empty_evaluation", "incomplete_fit",
    "incomplete_evaluation", "nonunique_fit", "invalid_transform", "numeric_inconsistency",
    "confidence_not_supplied", "metadata_join_conflict", "input_digest_mismatch",
    "resource_budget_exceeded", "native_process_failed", "native_result_missing",
    "capture_incomplete", "retained_artifact_missing", "saved_sheet_not_received",
    "original_commission_mismatch", "selected_field_unavailable", "software_identity_mismatch", "invalid_output_path"]
Reason: TypeAlias = Union[IssueCode, Literal["not_requested", "not_supplied", "zero_denominator", "mode_not_applicable", "no_coordinate_residue", "outside_alignment", "explicit_map_unmapped", "gap_in_other_sequence", "native_field_missing", "native_field_invalid", "semantics_unspecified", "unit_unspecified", "policy_requires_all", "transform_unavailable", "no_alignment", "calculation_not_performed"]]
IssueField: TypeAlias = Literal["file_identity", "data_block", "model_key", "chain_key", "position_key", "component_id", "symbol", "sequence", "residue_map", "atom_identity", "xyz", "occupancy", "b_factor_native", "physical_b_A2", "plddt", "coordinate_esd", "anisotropic_u", "native_qa", "native_metadata", "alignment", "traceback", "explicit_map", "fit_selection", "evaluation_selection", "rotation", "translation", "fit_sse", "distance", "threshold", "numerical_parameters", "coordinate_set", "projection_fields", "projection_members", "descriptor", "request", "software", "manifest", "returncode", "duration", "receipt"]
Qualification: TypeAlias = Literal["alternative_correspondences_not_enumerated", "declared_correspondence_not_homology_proof", "observed_sequence_not_full_polymer", "explicit_symbol_override", "explicit_unknown_symbol_X", "occupancy_not_reported", "native_zero_b_not_proof_of_measured_uncertainty", "bfactor_semantics_unspecified", "confidence_not_supplied", "native_qa_unit_unknown", "uncertainty_join_conflict", "minimum_only", "numerical_roundoff_clamp", "available_subset_used", "threshold_is_descriptive", "uncertainty_not_used_as_weight", "predicted_score_not_function_probability", "original_coordinates_preserved", "artifact_descriptor_not_numerical_delivery"]
InputRole: TypeAlias = Literal["single_structure", "fixed_structure", "moving_structure", "explicit_map", "alignment_native", "alignment_grading", "fixed_sequence", "moving_sequence", "fixed_residue_map", "moving_residue_map", "supplied_metadata", "received_transform_components", "received_transform_sheet"]
ManifestRole: TypeAlias = Union[InputRole, Literal["run_plan", "worker_input", "native_result", "sequence", "residue_map", "stdout", "stderr"]]
AlignmentSymbol: TypeAlias = Annotated[str, "alignment_symbol"]
FileFormat: TypeAlias = Union[StructureFormat, Literal["ascii_protein_sequence_v1", "protein_structure_sequence_v1", "protein_residue_map_v1", "protein_structure_metadata_v1", "biopython_pairwise_json", "tool_grading_artifact_v1", "tool_grading_artifact_v2", "protein_structure_comparison_sheet_v1", "protein_structure_components_v1", "protein_structure_projection_table_v1", "native_protein_structure_bundle_v1", "native_protein_structure_run_plan_v1", "protein_structure_worker_input_v1", "protein_structure_native_v1", "protein_structure_inventory_native_v1", "protein_structure_sequence_native_v1", "text"]]

class NumberCell(TypedDict):
    value: Real | None
    state: CellState
    reason: Reason | None
    unit: Unit
    origin: Origin

class VectorCell(TypedDict):
    value: Vec3 | None
    state: CellState
    reason: Reason | None
    unit: Unit
    origin: Origin

class MatrixCell(TypedDict):
    value: Mat3 | None
    state: CellState
    reason: Reason | None
    unit: Unit
    origin: Origin

class FileIdentity(TypedDict):
    artifact_ref: ArtifactRef
    sha256: Sha256
    byte_length: Count
    format: FileFormat

class ByteSpan(TypedDict):
    start_0based: Count
    end_exclusive: Count

class NativeToken(TypedDict):
    lexeme: Text | None
    text: Text | None
    syntax: Literal["pdb_field", "bare", "single_quoted", "double_quoted", "semicolon", "absent"]
    lexical_state: Literal["value", "pdb_blank", "cif_unknown", "cif_not_applicable", "absent"]
    span: ByteSpan | None

class NativeNumber(TypedDict):
    token: NativeToken
    value: Real | None
    state: Literal["present", "missing", "invalid"]
    embedded_standard_uncertainty: Real | None

NativeVec3: TypeAlias = Annotated[list[NativeNumber], "three"]
NativeSix: TypeAlias = Annotated[list[NativeNumber], "six"]
CellVec3: TypeAlias = Annotated[list[NumberCell], "three"]
CellSix: TypeAlias = Annotated[list[NumberCell], "six"]

class NativeAddress(TypedDict):
    file_sha256: Sha256
    block_ordinal_0based: Count | None
    record_key: NonemptyText
    field_name: NonemptyText

class PdbRecord(TypedDict):
    record_key: NonemptyText
    line_1based: Positive
    span: ByteSpan
    text: Text
    record_name: Text

class NativeTable(TypedDict):
    table_key: NonemptyText
    form: Literal["scalar", "loop"]
    tags: list[NativeToken]
    rows: list[list[NativeToken]]
    row_keys: list[NonemptyText]

class NativeBlock(TypedDict):
    ordinal_0based: Count
    name: Text
    span: ByteSpan
    state: State
    tables: list[NativeTable]
    unparsed_spans: list[ByteSpan]

class ModelKey(TypedDict):
    ordinal_0based: Count
    native_serial_token: NativeToken
    serial_state: Literal["explicit", "implicit", "missing"]

class PdbChainKey(TypedDict):
    namespace: Literal["pdb"]
    chain_id: Annotated[str, "one"]
    ter_segment_ordinal_0based: Count

class CifChainKey(TypedDict):
    namespace: Literal["label_asym_id"]
    label_asym_id: NonemptyText

ChainKey: TypeAlias = PdbChainKey | CifChainKey

class PdbPositionKey(TypedDict):
    namespace: Literal["pdb"]
    file_sha256: Sha256
    block_ordinal_0based: None
    model_key: ModelKey
    chain_key: PdbChainKey
    residue_number: Signed
    insertion_code: Annotated[str, "one"]

class CifPositionKey(TypedDict):
    namespace: Literal["label_seq_id"]
    file_sha256: Sha256
    block_ordinal_0based: Count
    model_key: ModelKey
    chain_key: CifChainKey
    label_seq_id: Positive

PositionKey: TypeAlias = PdbPositionKey | CifPositionKey

class PdbResidueIdentity(TypedDict):
    format: Literal["pdb_3x_text"]
    position_key: PdbPositionKey
    record_class: Literal["ATOM", "HETATM"]
    component_id: NonemptyText

class CifResidueIdentity(TypedDict):
    format: Literal["pdbx_mmcif_text"]
    file_sha256: Sha256
    block_ordinal_0based: Count
    model_key: ModelKey
    label_asym_id: NativeToken
    auth_asym_id: NativeToken
    label_entity_id: NativeToken
    label_seq_id: NativeToken
    auth_seq_id: NativeToken
    insertion_code: NativeToken
    label_comp_id: NativeToken
    auth_comp_id: NativeToken
    group_pdb: NativeToken

ResidueIdentity: TypeAlias = PdbResidueIdentity | CifResidueIdentity

class DeclaredResidueIdentity(TypedDict):
    file_sha256: Sha256
    block_ordinal_0based: Count
    model_key: ModelKey
    label_asym_id: NonemptyText
    label_entity_id: NonemptyText
    label_seq_id: Positive
    component_id: NonemptyText
    scheme_row_keys: list[NonemptyText]
    auth_asym_id: NativeToken
    auth_seq_id: NativeToken
    insertion_code: NativeToken

class AtomIdentity(TypedDict):
    atom_row_key: NonemptyText
    residue: ResidueIdentity | None
    serial_or_atom_site_id: NativeToken
    atom_name: NativeToken
    auth_atom_name: NativeToken
    alt_id: NativeToken
    element: NativeToken
    formal_charge: NativeToken

class StructuredIssue(TypedDict):
    stage: Literal["input", "parse", "selection", "sequence", "correspondence", "metadata", "fit", "evaluation", "projection", "native", "capture", "authority"]
    code: IssueCode
    structure_role: Role | None
    position_key: PositionKey | None
    atom_row_key: NonemptyText | None
    correspondence_id: NonemptyText | None
    field: IssueField | None
    artifact_role: ManifestRole | None

class RawAtomRow(TypedDict):
    identity: AtomIdentity
    xyz_A: NativeVec3
    occupancy: NativeNumber
    b_iso: NativeNumber
    state: Literal["valid", "partial", "invalid"]
    issues: list[StructuredIssue]

class ModelInventoryRow(TypedDict):
    block_ordinal_0based: Count | None
    model_key: ModelKey
    atom_row_keys: list[NonemptyText]

class ChainInventoryRow(TypedDict):
    block_ordinal_0based: Count | None
    model_key: ModelKey
    chain_key: ChainKey
    auth_chain_tokens: list[NativeToken]
    entity_tokens: list[NativeToken]
    atom_row_keys: list[NonemptyText]

class ParsedStructure(TypedDict):
    version: Literal["protein_structure_parsed_v1"]
    file_identity: FileIdentity
    state: State
    pdb_records: list[PdbRecord]
    cif_blocks: list[NativeBlock]
    atoms: list[RawAtomRow]
    models: list[ModelInventoryRow]
    chains: list[ChainInventoryRow]
    unparsed_spans: list[ByteSpan]
    issues: list[StructuredIssue]

class BlockSelection(TypedDict):
    ordinal_0based: Count
    name: Text

class VariantChoice(TypedDict):
    position_key: PositionKey
    selected_native_component_id: NonemptyText

class SymbolOverride(TypedDict):
    component_id: NonemptyText
    alignment_symbol: AlignmentSymbol

class CaChoice(TypedDict):
    position_key: PositionKey
    atom_row_key: NonemptyText

class MetadataEvidence(TypedDict):
    file_identity: FileIdentity
    declaration_id: NonemptyText

class SymbolPolicy(TypedDict):
    unknown: Literal["reject", "explicit_X"]
    explicit_component_overrides: list[SymbolOverride]

class CaPolicy(TypedDict):
    policy: Literal["unambiguous_only", "explicit_atom_rows"]
    choices: list[CaChoice]

class StructureSelection(TypedDict):
    structure_role: Role
    file_identity: FileIdentity
    data_block: BlockSelection | None
    model_key: ModelKey
    chain_key: ChainKey
    sequence_basis: Literal["observed_polymer", "mmcif_declared_polymer"]
    residue_variant_choices: list[VariantChoice]
    symbol_policy: SymbolPolicy
    ca_selection: CaPolicy
    zero_occupancy_policy: Literal["include", "exclude"]
    bfactor_semantics: Literal["unspecified", "native_atomic_displacement", "declared_plddt"]
    semantics_evidence: MetadataEvidence | None

SymbolOrigin: TypeAlias = Literal["standard_amino_acid", "pdb_modres_parent", "mmcif_chemical_parent", "mmcif_native_one_letter", "explicit_override", "explicit_unknown_X", "unresolved"]

class CaSelection(TypedDict):
    candidate_atom_row_keys: list[NonemptyText]
    selected_atom_row_key: NonemptyText | None
    state: Literal["available", "missing", "ambiguous", "excluded", "invalid"]
    primary_reason: Reason | None
    qualifications: list[Qualification]

class SequenceResidueMapRow(TypedDict):
    sequence_position_0based: Count
    position_key: PositionKey
    native_component_ids: list[NonemptyText]
    selected_component_id: NonemptyText | None
    native_one_letter: Text | None
    alignment_symbol: AlignmentSymbol | None
    symbol_mapping_origin: SymbolOrigin
    symbol_evidence: list[NativeAddress]
    observed_residue_identities: list[ResidueIdentity]
    selected_residue_identity: ResidueIdentity | None
    no_coordinate_identity: DeclaredResidueIdentity | None
    ca: CaSelection

class StructureSequence(TypedDict):
    version: Literal["protein_structure_sequence_v1"]
    state: State
    selection: StructureSelection
    alignment_sequence: Text | None
    native_symbols: list[Text | None]
    residues: list[SequenceResidueMapRow]
    sequence_length: Count | None
    declared_polymer_length: Count | None
    sequence_available: bool
    issues: list[StructuredIssue]
    qualifications: list[Qualification]

class ResultCustody(TypedDict):
    run_id: NonemptyText
    result_episode_id: NonemptyText
    result_operation_key: NonemptyText
    result_receipt_key: NonemptyText
    handoff_ref: SourceRef
    source_ref: SourceRef
    bundle_artifact_ref: ArtifactRef
    original_request_sha256: Sha256

class StructureSequenceDescriptor(TypedDict):
    version: Literal["structure_sequence_descriptor_v1"]
    custody: ResultCustody
    reference_ref: ReferenceRef
    sequence_file: FileIdentity
    residue_map_file: FileIdentity
    structure_file: FileIdentity
    selection: StructureSelection
    sequence_length: Positive
    allowed_uses: list[Literal["sequence_align", "structure_correspondence"]]

class SavedSheetDescriptor(TypedDict):
    version: Literal["protein_structure_saved_sheet_v1"]
    custody: ResultCustody
    sheet_file: FileIdentity
    original_components_file: FileIdentity
    operation: Literal["compare_protein_structures"]
    original_mode: ScientificMode
    allowed_uses: list[Literal["recalculate", "select_projection", "use_transform"]]

class AlignmentDescriptor(TypedDict):
    version: Literal["structure_alignment_descriptor_v1"]
    observation_ref: ObservationRef
    source_ref: SourceRef
    original_operation_key: NonemptyText
    query_reference_ref: ReferenceRef
    reference_reference_ref: ReferenceRef
    native_file: FileIdentity
    grading_file: FileIdentity
    molecule: Literal["protein"]
    mode: Literal["local", "global"]
    traceback_selection: Literal["explicit_retained"]
    producer_traceback_selection: Literal["first_native_optimal_returned"]
    optimal_alternative_count: None

Interval: TypeAlias = Annotated[list[Count], "two"]
CoordinatePath: TypeAlias = Annotated[list[list[Count]], "two"]
class AlignedNative(TypedDict):
    aligned: Literal[True]
    native_score: Real
    query_length: Positive
    reference_length: Positive
    paired_positions: Count
    identical_positions: Count
    identity_fraction: Real
    query_coverage: Real
    reference_coverage: Real
    query_interval: Interval | None
    reference_interval: Interval | None
    coordinates: CoordinatePath
    aligned_query: NonemptyText
    aligned_reference: NonemptyText
    mode: Literal["local", "global"]
    matrix: Literal["BLOSUM62"]
    gap_open: Literal[-10.0]
    gap_extend: Literal[-0.5]
    biopython_version: NonemptyText
    limitations: list[Text]

class NoAlignmentNative(TypedDict):
    aligned: Literal[False]
    query_length: Positive
    reference_length: Positive
    mode: Literal["local", "global"]
    matrix: Literal["BLOSUM62"]
    biopython_version: NonemptyText

class AlignedNativeV2(TypedDict):
    native_format: Literal["biopython_pairwise_native_v2"]
    aligned: Literal[True]
    native_score: Real
    query_length: Positive
    reference_length: Positive
    query_interval: Interval | None
    reference_interval: Interval | None
    coordinates: CoordinatePath
    aligned_query: NonemptyText
    aligned_reference: NonemptyText
    mode: Literal["local", "global"]
    matrix: Literal["BLOSUM62"]
    gap_open: Literal[-10.0]
    gap_extend: Literal[-0.5]
    biopython_version: NonemptyText
    limitations: list[Text]

class NoAlignmentNativeV2(NoAlignmentNative):
    native_format: Literal["biopython_pairwise_native_v2"]
    native_score: None
    gap_open: Literal[-10.0]
    gap_extend: Literal[-0.5]
    limitations: list[Text]

BiopythonPairwiseNative: TypeAlias = AlignedNative | NoAlignmentNative | AlignedNativeV2 | NoAlignmentNativeV2
class PairwiseParameters(TypedDict):
    matrix: Text | None
    gap_open: Real | None
    gap_extend: Real | None
class PairwiseLengths(TypedDict):
    query: Count | None
    reference: Count | None
class PairwiseReported(TypedDict):
    paired_positions: Count | None
    identical_positions: Count | None
    identity_fraction: Real | None
    query_coverage: Real | None
    reference_coverage: Real | None
class PairwiseTraceback(TypedDict):
    status: Text
    query: Text | None
    reference: Text | None
class PairwiseCounts(TypedDict):
    alignment_columns: Count | None
    paired_positions: Count | None
    identical_positions: Count | None
    substituted_positions: Count | None
    query_gap_columns: Count | None
    reference_gap_columns: Count | None
    query_aligned_positions: Count | None
    reference_aligned_positions: Count | None
class PairwiseBounds(TypedDict):
    query: bool
    reference: bool
class PairwiseGeometry(TypedDict):
    available: bool
    coordinate_system: Literal["zero_based_half_open"]
    coordinates: CoordinatePath | None
    query_interval: Interval | None
    reference_interval: Interval | None
    operand_bounds_checked: PairwiseBounds
class PairwiseRow(TypedDict):
    column: Count
    query_position: Count | None
    reference_position: Count | None
    query_symbol: Text | None
    reference_symbol: Text | None
    relationship: Literal["identical", "substituted", "query_gap", "reference_gap"]
class PairwiseSymbols(TypedDict):
    reader_normalization: Literal["uppercase_of_native_traceback_symbols"]
    native_nucleotide_normalization: None
    identity: Literal["literal_normalized_symbol_equality_without_ambiguity_resolution"]
class BiopythonPairwiseSheetV1(TypedDict):
    schema: Literal["biopython_pairwise_sheet_v1"]
    status: Text
    native_result: BiopythonPairwiseNative
    molecule: Literal["protein"]
    mode: Literal["local", "global"]
    aligned: bool
    alignment_state: Literal["alignment", "no_alignment", "conflicting"]
    native_parameters: PairwiseParameters
    native_score: Real | None
    lengths: PairwiseLengths
    reported_measurements: PairwiseReported
    traceback: PairwiseTraceback
    measured_column_counts: PairwiseCounts
    geometry: PairwiseGeometry
    residue_correspondence: list[PairwiseRow]
    issues: Annotated[list[None], "empty"]
    symbol_interpretation: PairwiseSymbols
    limitations: list[Text]
class AlignmentSnapshot(TypedDict):
    descriptor: AlignmentDescriptor
    native_result: BiopythonPairwiseNative
    pairwise_sheet: BiopythonPairwiseSheetV1
class RetainedAlignmentInput(TypedDict):
    kind: Literal["retained_alignment"]
    alignment: AlignmentDescriptor
    fixed_sequence_descriptor: StructureSequenceDescriptor
    moving_sequence_descriptor: StructureSequenceDescriptor
    orientation: Literal["fixed_is_query", "fixed_is_reference"]
class ExplicitMapRow(TypedDict):
    fixed_position_key: PositionKey
    moving_position_key: PositionKey
class ExplicitMapDocument(TypedDict):
    version: Literal["protein_residue_map_v1"]
    declared_order: Literal["collinear"]
    fixed_selection: StructureSelection
    moving_selection: StructureSelection
    rows: list[ExplicitMapRow]
class ExplicitMapInput(TypedDict):
    kind: Literal["explicit_map"]
    map_file: FileIdentity
CorrespondenceInput: TypeAlias = RetainedAlignmentInput | ExplicitMapInput
class CorrespondenceRow(TypedDict):
    correspondence_id: NonemptyText
    origin_ordinal_0based: Count
    fixed_position_0based: Count | None
    moving_position_0based: Count | None
    fixed_symbol: AlignmentSymbol | None
    moving_symbol: AlignmentSymbol | None
    fixed_position_key: PositionKey | None
    moving_position_key: PositionKey | None
    fixed_residue: ResidueIdentity | None
    moving_residue: ResidueIdentity | None
    fixed_declared_residue: DeclaredResidueIdentity | None
    moving_declared_residue: DeclaredResidueIdentity | None
    relationship: Literal["identical", "substituted", "fixed_gap", "moving_gap"]
    fixed_ca: CaSelection | None
    moving_ca: CaSelection | None
class UnmappedPosition(TypedDict):
    sequence_position_0based: Count
    position_key: PositionKey
    correspondence_id: NonemptyText | None
    reason: Literal["outside_alignment", "explicit_map_unmapped", "gap_in_other_sequence", "no_alignment"]
class Correspondence(TypedDict):
    version: Literal["protein_structure_correspondence_v1"]
    state: State
    population_available: bool
    origin: Literal["retained_alignment", "explicit_map"]
    alignment_native: AlignmentSnapshot | None
    explicit_map: ExplicitMapDocument | None
    map_file: FileIdentity | None
    fixed_sequence_selection: StructureSelection
    moving_sequence_selection: StructureSelection
    rows: list[CorrespondenceRow]
    unmapped_fixed: list[UnmappedPosition]
    unmapped_moving: list[UnmappedPosition]
    issues: list[StructuredIssue]
    qualifications: list[Qualification]
class IdSelector(TypedDict):
    kind: Literal["correspondence_id"]
    correspondence_id: NonemptyText
class SequenceSelector(TypedDict):
    kind: Literal["sequence_position"]
    structure_role: Side
    position_0based: Count
PairSelector: TypeAlias = IdSelector | SequenceSelector
class AllMappedPairs(TypedDict):
    kind: Literal["all_mapped_pairs"]
class ExplicitPairSelection(TypedDict):
    kind: Literal["explicit"]
    members: list[PairSelector]
PairSelection: TypeAlias = AllMappedPairs | ExplicitPairSelection
class ResolvedRequestRow(TypedDict):
    request_index_0based: Count
    selector: PairSelector
    correspondence_id: NonemptyText | None
    fixed_position_0based: Count | None
    moving_position_0based: Count | None
    available: bool
    primary_reason: Reason | None
    qualifications: list[Qualification]
class ResolvedPairSelection(TypedDict):
    selection: PairSelection
    rows: list[ResolvedRequestRow]
    requested_count: Count | None
    resolved_pair_count: Count | None
    available_candidate_count: Count | None
class CoordinatePair(TypedDict):
    correspondence_id: NonemptyText
    fixed_position_0based: Count
    moving_position_0based: Count
    fixed_atom_row_key: NonemptyText | None
    moving_atom_row_key: NonemptyText | None
    fixed_xyz_A: VectorCell
    moving_xyz_A: VectorCell
    fixed_ca_state: CaSelection
    moving_ca_state: CaSelection
    fixed_uncertainty_row_key: NonemptyText | None
    moving_uncertainty_row_key: NonemptyText | None
class MetadataScope(TypedDict):
    structure_file: FileIdentity
    data_block: BlockSelection | None
    model_key: ModelKey
    chain_key: ChainKey
class SemanticsDeclaration(TypedDict):
    declaration_id: NonemptyText
    scope: MetadataScope
    bfactor_semantics: Literal["native_atomic_displacement", "declared_plddt"]
    producer_name: NonemptyText
    producer_version: Text | None
    evidence_artifact_ref: ArtifactRef
    evidence_span: ByteSpan | None
class MetricUnitDeclaration(TypedDict):
    declaration_id: NonemptyText
    structure_file: FileIdentity
    block_ordinal_0based: Count
    metric_id: NonemptyText
    meaning: Literal["plddt", "pae", "other"]
    unit: Unit
    evidence_artifact_ref: ArtifactRef
    evidence_span: ByteSpan | None
class MetadataDocument(TypedDict):
    version: Literal["protein_structure_metadata_v1"]
    semantics_declarations: list[SemanticsDeclaration]
    metric_unit_declarations: list[MetricUnitDeclaration]
class SuppliedMetadata(TypedDict):
    file_identity: FileIdentity
    document: MetadataDocument
class NativeMetricDefinition(TypedDict):
    metric_key: NonemptyText
    block_ordinal_0based: Count
    native_metric_id: NativeToken
    name: NativeToken
    type: NativeToken
    mode: NativeToken
    software_group_id: NativeToken
    native_row_key: NonemptyText
    meaning: Literal["plddt", "pae", "other", "unknown"]
    unit: Unit
    interpretation_evidence: list[NativeAddress]
    supplied_declaration_id: NonemptyText | None
class AtomUncertainty(TypedDict):
    row_key: NonemptyText
    structure_role: Role
    atom_row_key: NonemptyText
    residue_identity: ResidueIdentity
    occupancy: NumberCell
    b_factor_native: NumberCell
    physical_b_A2: NumberCell
    plddt: NumberCell
    coordinate_standard_uncertainty_xyz_A: CellVec3
    anisotropic_U_A2: CellSix
    anisotropic_U_standard_uncertainty_A2: CellSix
    native_addresses: list[NativeAddress]
    qualifications: list[Qualification]
    issues: list[StructuredIssue]
class QaEndpoint(TypedDict):
    model_key: ModelKey
    label_asym_id: NonemptyText
    label_seq_id: Positive
    selected_position_0based: Count | None
class NativeQaRow(TypedDict):
    row_key: NonemptyText
    structure_role: Role
    scope: Literal["global", "local", "ordered_pair"]
    metric_key: NonemptyText
    endpoint_1: QaEndpoint | None
    endpoint_2: QaEndpoint | None
    native_value: NativeNumber
    value: NumberCell
    native_addresses: list[NativeAddress]
    issues: list[StructuredIssue]
class MetadataValueRow(TypedDict):
    row_key: NonemptyText
    structure_role: Role
    kind: Literal["method", "resolution", "declared_sequence_length"]
    native_text: NativeToken | None
    value: NumberCell | None
    native_addresses: list[NativeAddress]
class UnjoinedMetadata(TypedDict):
    row_key: NonemptyText
    native_addresses: list[NativeAddress]
    reason: Reason
class StructureMetadata(TypedDict):
    version: Literal["protein_structure_metadata_extracted_v1"]
    state: State
    structure_role: Role
    file_identity: FileIdentity
    selection: StructureSelection
    supplied_metadata: list[SuppliedMetadata]
    atom_uncertainty: list[AtomUncertainty]
    metric_definitions: list[NativeMetricDefinition]
    qa_rows: list[NativeQaRow]
    metadata_values: list[MetadataValueRow]
    unjoined_rows: list[UnjoinedMetadata]
    issues: list[StructuredIssue]
    qualifications: list[Qualification]
class NumericalParameters(TypedDict):
    svd_relative_tolerance: Real
    svd_absolute_tolerance_A2: Real
    geometry_absolute_tolerance_A: Real
    rotation_orthogonality_tolerance: Real
    rotation_determinant_tolerance: Real
    sse_roundoff_absolute_tolerance_A2: Real
    sse_roundoff_relative_tolerance: Real
class ReceivedTransform(TypedDict):
    saved_sheet: SavedSheetDescriptor
    components_file: FileIdentity
    calculation_id: NonemptyText
    calculation_custody: ResultCustody
class DeclaredTransform(TypedDict):
    version: Literal["protein_structure_transform_v1"]
    direction: Literal["moving_to_fixed"]
    convention: Literal["row_vector_y_R_plus_t"]
    rotation: Mat3
    translation_A: Vec3
    fixed_selection: StructureSelection
    moving_selection: StructureSelection
    origin: Literal["supplied", "received_fitted"]
    received_from: ReceivedTransform | None
class AllSelectedChain(TypedDict):
    kind: Literal["all_selected_chain"]
class SequencePositions(TypedDict):
    kind: Literal["sequence_positions"]
    positions: list[Count]
class CoordinateSetSelection(TypedDict):
    coordinate_set_id: NonemptyText
    structure_role: Side
    members: AllSelectedChain | SequencePositions
    atom_scope: Literal["selected_ca", "selected_chain_all_atoms"]
    frame: Literal["original", "moving_in_fixed_frame"]
class CalculationParameters(TypedDict):
    version: Literal["protein_structure_calculation_parameters_v1"]
    mode: ScientificMode
    fit_selection: PairSelection | None
    evaluation_selection: PairSelection
    missing_coordinate_policy: Literal["require_all", "use_available"]
    declared_transform: DeclaredTransform | None
    distance_threshold_A: Real | None
    numerical: NumericalParameters
    coordinate_sets: list[CoordinateSetSelection]
TransformState: TypeAlias = Literal["identifiable_fit", "supplied", "nonunique_fit", "unavailable", "invalid"]
class TransformResult(TypedDict):
    state: TransformState
    direction: Literal["moving_to_fixed"]
    convention: Literal["row_vector_y_R_plus_t"]
    rotation: MatrixCell
    translation: VectorCell
    issues: list[StructuredIssue]
    qualifications: list[Qualification]
class ExcludedRequest(TypedDict):
    request_index_0based: Count
    reason: Reason
class FitResult(TypedDict):
    state: Literal["performed", "minimum_only", "not_applicable", "unavailable", "invalid"]
    selection: ResolvedPairSelection | None
    used_correspondence_ids: list[NonemptyText]
    excluded: list[ExcludedRequest]
    fixed_centroid: VectorCell
    moving_centroid: VectorCell
    cross_covariance: MatrixCell
    singular_values: VectorCell
    fixed_geometry_singular_values: VectorCell
    moving_geometry_singular_values: VectorCell
    fixed_geometry_rank: NumberCell
    moving_geometry_rank: NumberCell
    cross_covariance_rank: NumberCell
    uncorrected_rotation_determinant: NumberCell
    reflection_correction_sign: NumberCell
    fit_sse_raw_formula: NumberCell
    fit_sse_roundoff_limit: NumberCell
    fit_sse: NumberCell
    fit_residual_sse: NumberCell
    fit_rmsd: NumberCell
    transform: TransformResult
    issues: list[StructuredIssue]
    qualifications: list[Qualification]
class SiteMeasurement(TypedDict):
    request_index_0based: Count
    selector: PairSelector
    correspondence_id: NonemptyText | None
    fixed_position_0based: Count | None
    moving_position_0based: Count | None
    in_fit: bool
    in_evaluation: bool
    evaluated: bool
    primary_reason: Reason | None
    moving_transformed_xyz: VectorCell
    residual_xyz: VectorCell
    distance_squared: NumberCell
    distance: NumberCell
    above_threshold: bool | None
    qualifications: list[Qualification]
class CoordinateRow(TypedDict):
    row_index_0based: Count
    atom_row_key: NonemptyText | None
    sequence_position_0based: Count | None
    residue_identity: ResidueIdentity | None
    declared_residue_identity: DeclaredResidueIdentity | None
    atom_identity: AtomIdentity | None
    xyz: VectorCell
    issues: list[StructuredIssue]
class CoordinateSet(TypedDict):
    selection: CoordinateSetSelection
    state: State
    rows: list[CoordinateRow]
    requested_position_count: Count | None
    atom_row_count: Count
    issues: list[StructuredIssue]
class CountComponents(TypedDict):
    fixed_sequence_length: NumberCell
    moving_sequence_length: NumberCell
    fixed_declared_polymer_length: NumberCell
    moving_declared_polymer_length: NumberCell
    mapped_pair_count: NumberCell
    fixed_coordinate_count: NumberCell
    moving_coordinate_count: NumberCell
    available_pair_count: NumberCell
    fixed_unmapped_count: NumberCell
    moving_unmapped_count: NumberCell
    fit_requested_count: NumberCell
    fit_resolved_pair_count: NumberCell
    fit_available_candidate_count: NumberCell
    fit_used_count: NumberCell
    fit_excluded_count: NumberCell
    evaluation_requested_count: NumberCell
    evaluation_resolved_pair_count: NumberCell
    evaluation_available_candidate_count: NumberCell
    evaluation_used_count: NumberCell
    evaluation_excluded_count: NumberCell
class CoverageComponents(TypedDict):
    fixed_correspondence_coverage: NumberCell
    moving_correspondence_coverage: NumberCell
    fixed_coordinate_coverage: NumberCell
    moving_coordinate_coverage: NumberCell
    fixed_paired_coordinate_coverage: NumberCell
    moving_paired_coordinate_coverage: NumberCell
    mapped_pair_coordinate_coverage: NumberCell
    fit_coverage: NumberCell
    evaluation_coverage: NumberCell
class AlignmentComponents(TypedDict):
    alignment_score: NumberCell
    alignment_identity_count: NumberCell
    alignment_substitution_count: NumberCell
    alignment_column_count: NumberCell
    alignment_fixed_gap_count: NumberCell
    alignment_moving_gap_count: NumberCell
class EvaluationComponents(TypedDict):
    state: Literal["performed", "unavailable", "invalid"]
    selection: ResolvedPairSelection
    used_correspondence_ids: list[NonemptyText]
    excluded: list[ExcludedRequest]
    evaluation_sse: NumberCell
    evaluation_rmsd: NumberCell
    evaluation_mean_distance: NumberCell
    evaluation_min_distance: NumberCell
    evaluation_max_distance: NumberCell
    distance_threshold_A: NumberCell
    above_threshold_count: NumberCell
    above_threshold_fraction: NumberCell
    issues: list[StructuredIssue]
class SheetInputIdentities(TypedDict):
    fixed: FileIdentity
    moving: FileIdentity
    correspondence: CorrespondenceInput
    metadata_artifacts: list[FileIdentity]
class StructureSides(TypedDict):
    fixed: ParsedStructure
    moving: ParsedStructure
class SequenceSides(TypedDict):
    fixed: StructureSequence
    moving: StructureSequence
class MetadataSides(TypedDict):
    fixed: StructureMetadata
    moving: StructureMetadata
class ProteinStructureSheet(TypedDict):
    version: Literal["protein_structure_comparison_sheet_v1"]
    operation: Literal["compare_protein_structures"]
    scientific_mode: ScientificMode
    input_identities: SheetInputIdentities
    structures: StructureSides
    sequences: SequenceSides
    correspondence: Correspondence
    coordinate_pairs: list[CoordinatePair]
    native_request: CalculationParameters
    native_baseline: ProteinStructureComponents | None
    native_uncertainty: MetadataSides
    parse_issues: list[StructuredIssue]
    correspondence_issues: list[StructuredIssue]
    source_qualifications: list[Qualification]
class ProteinStructureComponents(TypedDict):
    version: Literal["protein_structure_components_v1"]
    calculation_id: NonemptyText
    input_numerical_sha256: Sha256
    parameters: CalculationParameters
    state: State
    counts: CountComponents
    coverage: CoverageComponents
    alignment: AlignmentComponents
    fit: FitResult
    transform: TransformResult
    evaluation: EvaluationComponents
    site_measurements: list[SiteMeasurement]
    coordinate_sets: list[CoordinateSet]
    issues: list[StructuredIssue]
    qualifications: list[Qualification]
class AllBlocks(TypedDict):
    kind: Literal["all"]
class ExplicitBlocks(TypedDict):
    kind: Literal["explicit"]
    blocks: list[BlockSelection]
class InventorySelection(TypedDict):
    blocks: AllBlocks | ExplicitBlocks
    include: list[Literal["models", "chains", "sequence_bases", "residue_variants", "ca_candidates", "native_metadata"]]
class InventoryModel(TypedDict):
    row_key: NonemptyText
    block: BlockSelection | None
    model_key: ModelKey
    atom_count: Count
class InventoryChain(TypedDict):
    row_key: NonemptyText
    block: BlockSelection | None
    model_key: ModelKey
    chain_key: ChainKey
    auth_chain_tokens: list[NativeToken]
    entity_tokens: list[NativeToken]
    atom_count: Count
    observed_polymer_position_count: Count | None
    declared_polymer_position_count: Count | None
    available_sequence_bases: list[Literal["observed_polymer", "mmcif_declared_polymer"]]
class InventoryPosition(TypedDict):
    row_key: NonemptyText
    position_key: PositionKey
    component_ids: list[NonemptyText]
    ca_candidate_atom_row_keys: list[NonemptyText]
class InventoryMetadata(TypedDict):
    row_key: NonemptyText
    block: BlockSelection | None
    native_addresses: list[NativeAddress]
    native_tokens: list[NativeToken]
class StructureInventory(TypedDict):
    version: Literal["protein_structure_inventory_v1"]
    state: State
    file_identity: FileIdentity
    selection: InventorySelection
    models: list[InventoryModel]
    chains: list[InventoryChain]
    positions: list[InventoryPosition]
    metadata: list[InventoryMetadata]
    issues: list[StructuredIssue]

PUBLIC_TYPE_NAMES = tuple("""FileIdentity BlockSelection ModelKey ChainKey PositionKey ResidueIdentity
DeclaredResidueIdentity AtomIdentity RawAtomRow ParsedStructure NativeToken NativeNumber NativeAddress
NumberCell VectorCell MatrixCell Role Side State ScientificMode Unit Origin Reason IssueCode IssueField
StructuredIssue Qualification InputRole ManifestRole StructureSelection SequenceResidueMapRow StructureSequence
ResultCustody StructureSequenceDescriptor SavedSheetDescriptor AlignmentDescriptor BiopythonPairwiseNative
BiopythonPairwiseSheetV1 AlignmentSnapshot ExplicitMapDocument CorrespondenceInput CorrespondenceRow
Correspondence UnmappedPosition PairSelector PairSelection ResolvedRequestRow ResolvedPairSelection CoordinatePair
MetadataDocument SuppliedMetadata StructureMetadata AtomUncertainty NativeMetricDefinition NativeQaRow MetadataValueRow
NumericalParameters DeclaredTransform CalculationParameters CoordinateSetSelection TransformResult FitResult SiteMeasurement
CoordinateRow CoordinateSet CountComponents CoverageComponents AlignmentComponents EvaluationComponents
ProteinStructureSheet ProteinStructureComponents InventorySelection StructureInventory""".split())


def same(left, right) -> bool:
    """Type-sensitive equality, including integer versus floating observations."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def _unique(values, code="duplicate_selection", *, nonempty=False):
    if nonempty and not values or len({canonical(x) for x in values}) != len(values):
        raise ValueError(code)


def issue(code, *, stage="parse", role=None, position=None, atom=None, correspondence=None, field=None, artifact_role=None):
    return {"stage": stage, "code": code, "structure_role": role,
            "position_key": deepcopy(position), "atom_row_key": atom,
            "correspondence_id": correspondence, "field": field, "artifact_role": artifact_role}


def _type_schema(annotation):
    origin, args = get_origin(annotation), get_args(annotation)
    if is_typeddict(annotation):
        return {"$ref": "#/$defs/" + annotation.__name__}
    if origin is Annotated:
        schema = _type_schema(args[0])
        for flag in args[1:]:
            schema.update({
                "count": {"minimum": 0}, "positive": {"minimum": 1},
                "text": {"pattern": "^[^\\u0000]*$"},
                "nonempty": {"minLength": 1, "pattern": "^[^\\u0000]*$"},
                "sha256": {"pattern": "^[a-f0-9]{64}$"},
                "artifact_ref": {"pattern": "^artifact_[a-f0-9]{64}$"},
                "source_ref": {"pattern": "^source_[a-f0-9]{24,64}$"},
                "reference_ref": {"pattern": "^reference_[a-f0-9]{24,64}$"},
                "observation_ref": {"pattern": "^observation_[a-f0-9]{24,64}$"},
                "one": {"minLength": 1, "maxLength": 1, "pattern": "^[^\\u0000]*$"},
                "alignment_symbol": {"pattern": "^[ARNDCQEGHILKMFPSTWYVBZX]$"},
                "two": {"minItems": 2, "maxItems": 2},
                "three": {"minItems": 3, "maxItems": 3},
                "six": {"minItems": 6, "maxItems": 6},
                "empty": {"maxItems": 0},
            }[flag])
        return schema
    if origin in (Union, types.UnionType):
        return {"anyOf": [_type_schema(a) for a in args]}
    if origin is Literal:
        return {"enum": list(args)}
    if origin is list:
        return {"type": "array", "items": _type_schema(args[0])}
    return {"type": {str: "string", int: "integer", float: "number", bool: "boolean", type(None): "null", None: "null"}[annotation]}


def _make_definitions():
    namespace = globals()
    definitions = {}
    # Every nested TypedDict has one schema owner, and recursive sheet/baseline
    # links remain references rather than recursively expanded documents.
    for name, value in list(namespace.items()):
        if is_typeddict(value) and value.__module__ == __name__:
            props = {key: _type_schema(annotation) for key, annotation in get_type_hints(value, include_extras=True).items()}
            definitions[name] = {"type": "object", "properties": props,
                                 "required": list(props), "additionalProperties": False}
    for name in PUBLIC_TYPE_NAMES:
        if name not in definitions:
            definitions[name] = _type_schema(namespace[name])
    # Native producer limitations are fixed-order declarations, not free prose.
    for typename, values in (
        ("AlignedNative", ["pairwise_alignment_is_not_a_database_significance_test", "one_alignment_is_not_an_orthology_or_function_assignment"]),
        ("BiopythonPairwiseSheetV1", ["only_the_supplied_native_alignment_is_available_not_all_optimal_alternatives", "original_unaligned_sequence_symbols_are_not_present_in_this_native_result", "native_score_is_not_database_significance_or_function_confidence"]),
    ):
        definitions[typename]["properties"]["limitations"] = {"const": values}
    return definitions


_DEFINITIONS = _make_definitions()
# JSON Schema's mathematical integer includes 1.0; the native contract does not.
_STRICT_VALIDATOR = validators.extend(Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER.redefine("integer", lambda _, v: type(v) is int)
    .redefine("number", lambda _, v: type(v) in (int, float) and math.isfinite(v)))
_VALIDATORS = {name: _STRICT_VALIDATOR({"$defs": _DEFINITIONS, "$ref": "#/$defs/" + name}) for name in PUBLIC_TYPE_NAMES}


def protein_structure_schema_definitions(*, action_custody=False) -> dict:
    if type(action_custody) is not bool:
        raise ValueError("invalid_schema")
    if action_custody:
        return protein_structure_action_schema_definitions()
    return deepcopy(_DEFINITIONS)


def protein_structure_schema_ref(type_name: str) -> dict:
    if type(type_name) is not str or type_name not in PUBLIC_TYPE_NAMES:
        raise ValueError("invalid_schema")
    return {"$ref": "#/$defs/" + type_name}


def _json_only(value):
    if type(value) is dict:
        if any(type(k) is not str or "\0" in k for k in value):
            raise ValueError("invalid_schema")
        for x in value.values():
            _json_only(x)
    elif type(value) is list:
        for x in value:
            _json_only(x)
    elif type(value) is str:
        if "\0" in value:
            raise ValueError("invalid_schema")
    elif type(value) is float:
        if not math.isfinite(value):
            raise ValueError("invalid_schema")
    elif value is not None and type(value) not in (bool, int):
        raise ValueError("invalid_schema")


def _position_in_selection(position, selection):
    if (position["file_sha256"] != selection["file_identity"]["sha256"]
            or not same(position["model_key"], selection["model_key"])
            or not same(position["chain_key"], selection["chain_key"])
            or position["block_ordinal_0based"] != (selection["data_block"]["ordinal_0based"] if selection["data_block"] else None)):
        raise ValueError("conflicting_identity")


def _residue_at_position(residue, position):
    if residue["format"] == "pdb_3x_text":
        if not same(residue["position_key"], position):
            raise ValueError("conflicting_identity")
    else:
        token = residue["label_seq_id"]
        if (position["namespace"] != "label_seq_id" or residue["file_sha256"] != position["file_sha256"]
                or residue["block_ordinal_0based"] != position["block_ordinal_0based"]
                or not same(residue["model_key"], position["model_key"])
                or residue["label_asym_id"]["text"] != position["chain_key"]["label_asym_id"]
                or token["lexical_state"] != "value" or token["text"] != str(position["label_seq_id"])):
            # Positive labels can have leading zeros; compare exact integer value.
            try:
                ok = (position["namespace"] == "label_seq_id" and residue["file_sha256"] == position["file_sha256"]
                    and residue["block_ordinal_0based"] == position["block_ordinal_0based"]
                    and same(residue["model_key"], position["model_key"])
                    and residue["label_asym_id"]["text"] == position["chain_key"]["label_asym_id"]
                    and token["lexical_state"] == "value" and int(token["text"]) == position["label_seq_id"])
            except (TypeError, ValueError):
                ok = False
            if not ok:
                raise ValueError("conflicting_identity")


def _check_selection(v):
    pdb = v["file_identity"]["format"] == "pdb_3x_text"
    if v["file_identity"]["format"] not in ("pdb_3x_text", "pdbx_mmcif_text"):
        raise ValueError("unsupported_format")
    if (pdb and (v["data_block"] is not None or v["chain_key"]["namespace"] != "pdb" or v["sequence_basis"] != "observed_polymer")
            or not pdb and (v["data_block"] is None or v["chain_key"]["namespace"] != "label_asym_id")):
        raise ValueError("unselected_data_block" if not pdb and v["data_block"] is None else "conflicting_identity")
    for choices in (v["residue_variant_choices"], v["ca_selection"]["choices"]):
        _unique([x["position_key"] for x in choices])
        for x in choices:
            _position_in_selection(x["position_key"], v)
    _unique([x["component_id"] for x in v["symbol_policy"]["explicit_component_overrides"]])
    if v["ca_selection"]["policy"] == "unambiguous_only" and v["ca_selection"]["choices"]:
        raise ValueError("invalid_schema")
    if (v["bfactor_semantics"] == "unspecified") != (v["semantics_evidence"] is None):
        raise ValueError("metadata_join_conflict")
    if v["semantics_evidence"] is not None and v["semantics_evidence"]["file_identity"]["format"] != "protein_structure_metadata_v1":
        raise ValueError("unsupported_format")


def _check_sequence(v):
    rows = v["residues"]
    _unique([x["position_key"] for x in rows], "conflicting_identity")
    if [x["sequence_position_0based"] for x in rows] != list(range(len(rows))):
        raise ValueError("conflicting_identity")
    if v["native_symbols"] != [x["native_one_letter"] for x in rows]:
        raise ValueError("sequence_artifact_mismatch")
    if v["sequence_length"] is not None and v["sequence_length"] != len(rows):
        raise ValueError("conflicting_identity")
    available = v["sequence_length"] is not None and bool(rows) and all(x["alignment_symbol"] is not None and x["selected_component_id"] is not None for x in rows)
    if v["sequence_available"] != available or v["alignment_sequence"] != ("".join(x["alignment_symbol"] for x in rows) if available else None):
        raise ValueError("sequence_artifact_mismatch")
    if v["declared_polymer_length"] is not None and len(rows) > v["declared_polymer_length"]:
        raise ValueError("conflicting_identity")
    for row in rows:
        _position_in_selection(row["position_key"], v["selection"])
        _unique(row["native_component_ids"], "conflicting_identity", nonempty=True)
        if row["selected_component_id"] is not None and row["selected_component_id"] not in row["native_component_ids"]:
            raise ValueError("conflicting_identity")
        for residue in row["observed_residue_identities"]:
            _residue_at_position(residue, row["position_key"])
        selected = row["selected_residue_identity"]
        if selected is not None:
            if not any(same(selected, r) for r in row["observed_residue_identities"]):
                raise ValueError("conflicting_identity")
            component = selected["component_id"] if selected["format"] == "pdb_3x_text" else selected["label_comp_id"]["text"]
            if component != row["selected_component_id"] or row["no_coordinate_identity"] is not None:
                raise ValueError("conflicting_identity")
        declared = row["no_coordinate_identity"]
        if declared is not None:
            p = row["position_key"]
            if (p["namespace"] != "label_seq_id" or declared["file_sha256"] != p["file_sha256"]
                    or declared["block_ordinal_0based"] != p["block_ordinal_0based"]
                    or declared["label_seq_id"] != p["label_seq_id"]
                    or declared["label_asym_id"] != p["chain_key"]["label_asym_id"]
                    or not same(declared["model_key"], p["model_key"])
                    or declared["component_id"] != row["selected_component_id"]):
                raise ValueError("conflicting_identity")
        if row["ca"]["state"] == "available" and selected is None:
            raise ValueError("invalid_coordinate_identity")
    role = v["selection"]["structure_role"]
    if any(x["structure_role"] not in (None, role) for x in v["issues"]):
        raise ValueError("conflicting_identity")


def _check_parsed(v):
    pdb = v["file_identity"]["format"] == "pdb_3x_text"
    if v["file_identity"]["format"] not in ("pdb_3x_text", "pdbx_mmcif_text"):
        raise ValueError("unsupported_format")
    if pdb and v["cif_blocks"] or not pdb and v["pdb_records"]:
        raise ValueError("conflicting_identity")
    atoms = {x["identity"]["atom_row_key"]: x for x in v["atoms"]}
    if len(atoms) != len(v["atoms"]):
        raise ValueError("conflicting_identity")
    record_keys = set()
    for record in v["pdb_records"]:
        if record["record_key"] != "pdb_line_" + str(record["line_1based"]):
            raise ValueError("conflicting_identity")
        record_keys.add(record["record_key"])
    for i, block in enumerate(v["cif_blocks"]):
        if block["ordinal_0based"] != i:
            raise ValueError("conflicting_identity")
        tags = []
        for j, table in enumerate(block["tables"]):
            key = f"cif_block_{i}_table_{j}"
            if table["table_key"] != key or table["row_keys"] != [f"{key}_row_{n}" for n in range(len(table["rows"]))]:
                raise ValueError("conflicting_identity")
            if any(len(row) != len(table["tags"]) for row in table["rows"]):
                raise ValueError("malformed_cif_loop")
            tags += [x["text"].lower() for x in table["tags"]]
            record_keys.update(table["row_keys"])
        if block["state"] == "complete":
            _unique(tags, "conflicting_identity")
    if not set(atoms) <= record_keys:
        raise ValueError("conflicting_identity")
    for entries in (v["models"], v["chains"]):
        _unique([{k: x[k] for k in x if k in ("block_ordinal_0based", "model_key", "chain_key")} for x in entries], "conflicting_identity")
        for row in entries:
            _unique(row["atom_row_keys"], "conflicting_identity")
            if not set(row["atom_row_keys"]) <= atoms.keys():
                raise ValueError("conflicting_identity")
            for key in row["atom_row_keys"]:
                residue = atoms[key]["identity"]["residue"]
                if residue is not None:
                    r = residue["position_key"] if pdb else residue
                    if r["file_sha256"] != v["file_identity"]["sha256"] or not same(r["model_key"], row["model_key"]) or r["block_ordinal_0based"] != row["block_ordinal_0based"]:
                        raise ValueError("conflicting_identity")
                    if "chain_key" in row and (not same(r["chain_key"], row["chain_key"]) if pdb else r["label_asym_id"]["text"] != row["chain_key"]["label_asym_id"]):
                        raise ValueError("conflicting_identity")
    for span in [x["span"] for x in v["pdb_records"]] + [x["span"] for x in v["cif_blocks"]] + v["unparsed_spans"]:
        if span["end_exclusive"] > v["file_identity"]["byte_length"]:
            raise ValueError("conflicting_identity")


def _check_correspondence(v):
    if not v["population_available"] and v["state"] == "complete":
        raise ValueError("conflicting_identity")
    _unique([x["correspondence_id"] for x in v["rows"]], "duplicate_selection")
    if v["fixed_sequence_selection"]["structure_role"] != "fixed" or v["moving_sequence_selection"]["structure_role"] != "moving":
        raise ValueError("conflicting_identity")
    if v["origin"] == "explicit_map":
        if v["alignment_native"] is not None or v["explicit_map"] is None or v["map_file"] is None:
            raise ValueError("conflicting_identity")
        if v["map_file"]["format"] != "protein_residue_map_v1":
            raise ValueError("unsupported_format")
    elif v["explicit_map"] is not None or v["map_file"] is not None or v["population_available"] and v["alignment_native"] is None:
        raise ValueError("conflicting_identity")
    for side in ("fixed", "moving"):
        positions = [x[side + "_position_0based"] for x in v["rows"] if x[side + "_position_0based"] is not None]
        if positions != sorted(set(positions)):
            raise ValueError("map_not_injective" if len(positions) != len(set(positions)) else "map_not_collinear")
        for row in v["rows"]:
            p, key = row[side + "_position_0based"], row[side + "_position_key"]
            if (p is None) != (key is None) or (p is None) != (row[side + "_symbol"] is None) or (p is None) != (row[side + "_ca"] is None):
                raise ValueError("conflicting_identity")
            if key is not None:
                _position_in_selection(key, v[side + "_sequence_selection"])
                residue = row[side + "_residue"]
                if residue is not None:
                    _residue_at_position(residue, key)
        _unique([x["sequence_position_0based"] for x in v["unmapped_" + side]], "conflicting_identity")
        by_position = {r[side + "_position_0based"]: r for r in v["rows"] if r[side + "_position_0based"] is not None}
        other = "moving" if side == "fixed" else "fixed"
        for unmapped in v["unmapped_" + side]:
            _position_in_selection(unmapped["position_key"], v[side + "_sequence_selection"])
            row = by_position.get(unmapped["sequence_position_0based"])
            if unmapped["reason"] == "gap_in_other_sequence":
                if row is None or row[other + "_position_0based"] is not None or unmapped["correspondence_id"] != row["correspondence_id"] or not same(unmapped["position_key"], row[side + "_position_key"]):
                    raise ValueError("conflicting_identity")
            elif row is not None or unmapped["correspondence_id"] is not None:
                raise ValueError("conflicting_identity")
    for row in v["rows"]:
        a, b = row["fixed_symbol"], row["moving_symbol"]
        relationship = "fixed_gap" if a is None else "moving_gap" if b is None else "identical" if a == b else "substituted"
        prefix = "column_" if v["origin"] == "retained_alignment" else "map_"
        if a is None and b is None or row["relationship"] != relationship or row["correspondence_id"] != prefix + str(row["origin_ordinal_0based"]):
            raise ValueError("conflicting_identity")


def _check_parameters(v):
    fit = v["mode"] == "fit_then_evaluate_ca"
    if fit != (v["fit_selection"] is not None) or fit != (v["declared_transform"] is None):
        raise ValueError("invalid_schema")
    if any(x < 0 for x in v["numerical"].values()) or v["distance_threshold_A"] is not None and v["distance_threshold_A"] < 0:
        raise ValueError("invalid_schema")
    _unique([x["coordinate_set_id"] for x in v["coordinate_sets"]])
    for item in v["coordinate_sets"]:
        if item["frame"] == "moving_in_fixed_frame" and item["structure_role"] != "moving":
            raise ValueError("invalid_schema")
        if item["members"]["kind"] == "sequence_positions":
            _unique(item["members"]["positions"], nonempty=True)


def _check_snapshot(v):
    from .biopython_pairwise_grader import build_biopython_pairwise_sheet
    native, sheet, desc = v["native_result"], v["pairwise_sheet"], v["descriptor"]
    try:
        rebuilt = build_biopython_pairwise_sheet(native, molecule="protein")
    except (ValueError, TypeError, KeyError) as error:
        raise ValueError("invalid_traceback") from error
    if not same(rebuilt, sheet) or sheet["status"] not in ("complete", "no_alignment"):
        raise ValueError("invalid_traceback")
    if native["mode"] != desc["mode"]:
        raise ValueError("alignment_operand_mismatch")
    if native["aligned"] and not sheet["geometry"]["available"]:
        raise ValueError("invalid_traceback")


def _relations(v):
    if isinstance(v, list):
        for x in v:
            _relations(x)
        return
    if not isinstance(v, dict):
        return
    for x in v.values():
        _relations(x)
    keys = set(v)
    if keys == {"artifact_ref", "sha256", "byte_length", "format"}:
        if v["artifact_ref"] != "artifact_" + v["sha256"]:
            raise ValueError("input_digest_mismatch")
    elif keys == {"start_0based", "end_exclusive"}:
        if v["end_exclusive"] < v["start_0based"]:
            raise ValueError("invalid_schema")
    elif keys == {"value", "state", "reason", "unit", "origin"}:
        present = v["state"] == "present"
        if present != (v["value"] is not None) or present != (v["reason"] is None):
            raise ValueError("invalid_schema")
        if present and v["unit"] in ("count", "residue", "pair") and (type(v["value"]) is not int or v["value"] < 0):
            raise ValueError("invalid_schema")
    elif keys == {"lexeme", "text", "syntax", "lexical_state", "span"}:
        absent = v["syntax"] == "absent"
        if absent != (v["lexical_state"] == "absent") or absent != (v["lexeme"] is None) or absent != (v["text"] is None) or absent != (v["span"] is None):
            raise ValueError("invalid_schema")
        if not absent:
            if v["lexical_state"] == "cif_unknown" and (v["syntax"] != "bare" or v["lexeme"] != "?") or v["lexical_state"] == "cif_not_applicable" and (v["syntax"] != "bare" or v["lexeme"] != "."):
                raise ValueError("invalid_schema")
            if v["lexical_state"] == "pdb_blank" and (v["syntax"] != "pdb_field" or v["text"].strip()):
                raise ValueError("invalid_schema")
    elif keys == {"token", "value", "state", "embedded_standard_uncertainty"}:
        if (v["state"] == "present") != (v["value"] is not None) or v["embedded_standard_uncertainty"] is not None and (v["state"] != "present" or v["embedded_standard_uncertainty"] < 0):
            raise ValueError("invalid_schema")
        if (v["token"]["lexical_state"] != "value") != (v["state"] == "missing"):
            raise ValueError("invalid_schema")
    elif keys == {"ordinal_0based", "native_serial_token", "serial_state"}:
        if (v["serial_state"] == "explicit") != (v["native_serial_token"]["lexical_state"] == "value") or v["serial_state"] == "implicit" and v["native_serial_token"]["syntax"] != "absent":
            raise ValueError("conflicting_identity")
    elif "bfactor_semantics" in v and "ca_selection" in v:
        _check_selection(v)
    elif keys == {"candidate_atom_row_keys", "selected_atom_row_key", "state", "primary_reason", "qualifications"}:
        _unique(v["candidate_atom_row_keys"], "conflicting_identity")
        if v["selected_atom_row_key"] is not None and v["selected_atom_row_key"] not in v["candidate_atom_row_keys"]:
            raise ValueError("invalid_coordinate_identity")
        if (v["state"] == "available") != (v["primary_reason"] is None) or v["state"] == "available" and v["selected_atom_row_key"] is None:
            raise ValueError("invalid_coordinate_identity")
    elif keys == set(ResultCustody.__annotations__):
        payload = {"run_id": v["run_id"], "episode_id": v["result_episode_id"], "operation_key": v["result_operation_key"]}
        if v["result_receipt_key"] != "protein_structure_result_receipt:" + digest(payload):
            raise ValueError("conflicting_identity")
    elif keys == set(AlignmentDescriptor.__annotations__):
        if v["native_file"]["format"] != "biopython_pairwise_json" or v["grading_file"]["format"] not in ("tool_grading_artifact_v1", "tool_grading_artifact_v2"):
            raise ValueError("unsupported_format")
    elif keys == set(AlignmentSnapshot.__annotations__):
        _check_snapshot(v)
    elif v.get("kind") == "explicit" and "members" in v:
        _unique(v["members"], nonempty=True)
    elif keys == set(ResolvedPairSelection.__annotations__):
        if [r["request_index_0based"] for r in v["rows"]] != list(range(len(v["rows"]))):
            raise ValueError("conflicting_identity")
        if v["requested_count"] is not None and v["requested_count"] != len(v["rows"]):
            raise ValueError("conflicting_identity")
        for field in ("resolved_pair_count", "available_candidate_count"):
            if v[field] is not None and (v["requested_count"] is None or v[field] > v["requested_count"]):
                raise ValueError("conflicting_identity")
    elif keys == set(NativeQaRow.__annotations__):
        if ((v["scope"] == "global") != (v["endpoint_1"] is None)
                or (v["scope"] != "ordered_pair") != (v["endpoint_2"] is None)):
            raise ValueError("metadata_join_conflict")
    elif keys == set(TransformResult.__annotations__):
        usable = v["state"] in ("identifiable_fit", "supplied")
        if usable != (v["rotation"]["state"] == "present") or usable != (v["translation"]["state"] == "present"):
            raise ValueError("invalid_transform")
    elif keys == set(CoordinateSet.__annotations__):
        if [r["row_index_0based"] for r in v["rows"]] != list(range(len(v["rows"]))) or v["atom_row_count"] != sum(r["atom_row_key"] is not None for r in v["rows"]):
            raise ValueError("conflicting_identity")
    elif keys == set(InventorySelection.__annotations__):
        _unique(v["include"], nonempty=True)
        if v["blocks"]["kind"] == "explicit":
            _unique(v["blocks"]["blocks"], nonempty=True)
    version = v.get("version")
    if version == "protein_structure_parsed_v1":
        _check_parsed(v)
    elif version == "protein_structure_sequence_v1":
        _check_sequence(v)
    elif version == "structure_sequence_descriptor_v1":
        _unique(v["allowed_uses"], nonempty=True)
        if not same(v["selection"]["file_identity"], v["structure_file"]) or v["sequence_file"]["byte_length"] != v["sequence_length"]:
            raise ValueError("sequence_artifact_mismatch")
        if v["sequence_file"]["format"] != "ascii_protein_sequence_v1" or v["residue_map_file"]["format"] != "protein_structure_sequence_v1":
            raise ValueError("unsupported_format")
    elif version == "protein_structure_saved_sheet_v1":
        _unique(v["allowed_uses"], nonempty=True)
        if v["sheet_file"]["format"] != "protein_structure_comparison_sheet_v1" or v["original_components_file"]["format"] != "protein_structure_components_v1":
            raise ValueError("unsupported_format")
    elif version == "protein_residue_map_v1":
        if v["fixed_selection"]["structure_role"] != "fixed" or v["moving_selection"]["structure_role"] != "moving":
            raise ValueError("conflicting_identity")
        for side in ("fixed", "moving"):
            _unique([r[side + "_position_key"] for r in v["rows"]], "map_not_injective")
            for row in v["rows"]:
                _position_in_selection(row[side + "_position_key"], v[side + "_selection"])
    elif version == "protein_structure_correspondence_v1":
        _check_correspondence(v)
    elif version == "protein_structure_metadata_v1":
        _unique([x["declaration_id"] for x in v["semantics_declarations"] + v["metric_unit_declarations"]], "metadata_join_conflict")
        for decl in v["metric_unit_declarations"]:
            if decl["meaning"] == "plddt" and decl["unit"] != "score_0_100" or decl["meaning"] == "pae" and decl["unit"] != "angstrom":
                raise ValueError("metadata_join_conflict")
    elif version == "protein_structure_metadata_extracted_v1":
        if v["structure_role"] != v["selection"]["structure_role"] or not same(v["file_identity"], v["selection"]["file_identity"]):
            raise ValueError("conflicting_identity")
        for atom in v["atom_uncertainty"]:
            residue = atom["residue_identity"]
            if residue["format"] == "pdb_3x_text":
                _position_in_selection(residue["position_key"], v["selection"])
            elif residue["file_sha256"] != v["file_identity"]["sha256"] or not same(residue["model_key"], v["selection"]["model_key"]) or residue["block_ordinal_0based"] != v["selection"]["data_block"]["ordinal_0based"] or residue["label_asym_id"]["text"] != v["selection"]["chain_key"]["label_asym_id"]:
                raise ValueError("conflicting_identity")
        for name in ("atom_uncertainty", "qa_rows", "metadata_values"):
            _unique([r["row_key"] for r in v[name]], "metadata_join_conflict")
            if any(r["structure_role"] != v["structure_role"] for r in v[name]):
                raise ValueError("conflicting_identity")
        _unique([r["metric_key"] for r in v["metric_definitions"]], "metadata_join_conflict")
        metrics = {r["metric_key"] for r in v["metric_definitions"]}
        if any(r["metric_key"] not in metrics for r in v["qa_rows"]):
            raise ValueError("metadata_join_conflict")
    elif version == "protein_structure_transform_v1":
        if (v["origin"] == "supplied") != (v["received_from"] is None) or v["fixed_selection"]["structure_role"] != "fixed" or v["moving_selection"]["structure_role"] != "moving":
            raise ValueError("invalid_transform")
        if v["received_from"] is not None and v["received_from"]["components_file"]["format"] != "protein_structure_components_v1":
            raise ValueError("unsupported_format")
    elif version == "protein_structure_calculation_parameters_v1":
        _check_parameters(v)
    elif version == "protein_structure_comparison_sheet_v1":
        _check_sheet(v)
    elif version == "protein_structure_components_v1":
        _check_components(v)
    elif version == "protein_structure_inventory_v1":
        _check_inventory(v)


def _check_sheet(v):
    if v["scientific_mode"] != v["native_request"]["mode"]:
        raise ValueError("conflicting_identity")
    for side in ("fixed", "moving"):
        selection = v["sequences"][side]["selection"]
        if selection["structure_role"] != side or not same(selection["file_identity"], v["input_identities"][side]) or not same(selection["file_identity"], v["structures"][side]["file_identity"]) or not same(selection, v["native_uncertainty"][side]["selection"]) or not same(selection, v["correspondence"][side + "_sequence_selection"]):
            raise ValueError("conflicting_identity")
    rows = {x["correspondence_id"]: x for x in v["correspondence"]["rows"] if x["fixed_position_0based"] is not None and x["moving_position_0based"] is not None}
    _unique([x["correspondence_id"] for x in v["coordinate_pairs"]], "conflicting_identity")
    if list(rows) != [x["correspondence_id"] for x in v["coordinate_pairs"]]:
        raise ValueError("conflicting_identity")
    for row in v["correspondence"]["rows"]:
        for side in ("fixed", "moving"):
            index = row[side + "_position_0based"]
            if index is None:
                continue
            sequence_rows = v["sequences"][side]["residues"]
            if index >= len(sequence_rows):
                raise ValueError("conflicting_identity")
            sequence_row = sequence_rows[index]
            for key, map_key in (("symbol", "alignment_symbol"), ("position_key", "position_key"), ("residue", "selected_residue_identity"), ("declared_residue", "no_coordinate_identity"), ("ca", "ca")):
                if not same(row[side + "_" + key], sequence_row[map_key]):
                    raise ValueError("conflicting_identity")
    for pair in v["coordinate_pairs"]:
        row = rows[pair["correspondence_id"]]
        for side in ("fixed", "moving"):
            if pair[side + "_position_0based"] != row[side + "_position_0based"] or not same(pair[side + "_ca_state"], row[side + "_ca"]):
                raise ValueError("conflicting_identity")
            key = pair[side + "_atom_row_key"]
            if key != row[side + "_ca"]["selected_atom_row_key"]:
                raise ValueError("invalid_coordinate_identity")
            atoms = {a["identity"]["atom_row_key"]: a for a in v["structures"][side]["atoms"]}
            if key is not None and key not in atoms:
                raise ValueError("invalid_coordinate_identity")
            coordinate = pair[side + "_xyz_A"]
            if row[side + "_ca"]["state"] == "available":
                if coordinate["state"] != "present" or key is None or coordinate["value"] != [x["value"] for x in atoms[key]["xyz_A"]]:
                    raise ValueError("invalid_coordinate_identity")
            elif coordinate["state"] == "present":
                raise ValueError("invalid_coordinate_identity")
            uncertainty_key = pair[side + "_uncertainty_row_key"]
            if uncertainty_key is not None and not any(r["row_key"] == uncertainty_key and r["atom_row_key"] == key for r in v["native_uncertainty"][side]["atom_uncertainty"]):
                raise ValueError("metadata_join_conflict")


def _check_components(v):
    expected_id = "protein_structure_calculation_" + digest({"input_numerical_sha256": v["input_numerical_sha256"], "parameters": v["parameters"]})
    if v["calculation_id"] != expected_id or not same(v["fit"]["transform"], v["transform"]):
        raise ValueError("conflicting_identity")
    _unique([x["selection"]["coordinate_set_id"] for x in v["coordinate_sets"]])
    if [x["request_index_0based"] for x in v["site_measurements"]] != list(range(len(v["site_measurements"]))):
        raise ValueError("conflicting_identity")
    for group in (v["fit"], v["evaluation"]):
        _unique(group["used_correspondence_ids"])
        _unique([x["request_index_0based"] for x in group["excluded"]])
        selection = group["selection"]
        if selection is None:
            continue
        requests = selection["rows"]
        if any(x["request_index_0based"] >= len(requests) for x in group["excluded"]):
            raise ValueError("conflicting_identity")
        if not set(group["used_correspondence_ids"]) <= {x["correspondence_id"] for x in requests}:
            raise ValueError("conflicting_identity")


def _check_inventory(v):
    include = v["selection"]["include"]
    for name in ("models", "chains", "positions", "metadata"):
        _unique([x["row_key"] for x in v[name]], "conflicting_identity")
    if "models" not in include and v["models"] or not set(include) & {"chains", "sequence_bases"} and v["chains"] or not set(include) & {"residue_variants", "ca_candidates"} and v["positions"] or "native_metadata" not in include and v["metadata"]:
        raise ValueError("invalid_schema")


def _validate(name, value):
    try:
        _json_only(value)
        action_custody = _contains_action_custody(value)
        validator = _action_validator(name) if action_custody else _VALIDATORS[name]
        if not validator.is_valid(value):
            raise ValueError("invalid_schema")
        _relations(value)
        if action_custody:
            _action_relations(value)
    except (KeyError, TypeError, IndexError, RecursionError, OverflowError) as error:
        raise ValueError("invalid_schema") from error
    return deepcopy(value)


def validate_file_identity(value: FileIdentity) -> FileIdentity:
    return _validate("FileIdentity", value)

def validate_structure_selection(value: StructureSelection) -> StructureSelection:
    return _validate("StructureSelection", value)

def validate_parsed_structure(value: ParsedStructure) -> ParsedStructure:
    return _validate("ParsedStructure", value)

def validate_structure_sequence(value: StructureSequence) -> StructureSequence:
    return _validate("StructureSequence", value)

def validate_structure_sequence_descriptor(value: StructureSequenceDescriptor) -> StructureSequenceDescriptor:
    return _validate("StructureSequenceDescriptor", value)

def validate_alignment_descriptor(value: AlignmentDescriptor) -> AlignmentDescriptor:
    return _validate("AlignmentDescriptor", value)

def validate_alignment_snapshot(value: AlignmentSnapshot) -> AlignmentSnapshot:
    return _validate("AlignmentSnapshot", value)

def validate_explicit_residue_map_document(value: ExplicitMapDocument) -> ExplicitMapDocument:
    return _validate("ExplicitMapDocument", value)

def validate_correspondence_input(value: CorrespondenceInput) -> CorrespondenceInput:
    result = _validate("CorrespondenceInput", value)
    if result["kind"] == "explicit_map" and result["map_file"]["format"] != "protein_residue_map_v1":
        raise ValueError("unsupported_format")
    if result["kind"] == "retained_alignment":
        fixed, moving = result["fixed_sequence_descriptor"], result["moving_sequence_descriptor"]
        query, reference = (fixed, moving) if result["orientation"] == "fixed_is_query" else (moving, fixed)
        if result["alignment"]["query_reference_ref"] != query["reference_ref"] or result["alignment"]["reference_reference_ref"] != reference["reference_ref"]:
            raise ValueError("alignment_operand_mismatch")
    return result

def validate_correspondence(value: Correspondence) -> Correspondence:
    return _validate("Correspondence", value)

def validate_metadata_document(value: MetadataDocument) -> MetadataDocument:
    return _validate("MetadataDocument", value)

def validate_structure_metadata(value: StructureMetadata) -> StructureMetadata:
    return _validate("StructureMetadata", value)

def validate_declared_transform_record(value: DeclaredTransform) -> DeclaredTransform:
    return _validate("DeclaredTransform", value)

def validate_calculation_parameters(value: CalculationParameters) -> CalculationParameters:
    return _validate("CalculationParameters", value)

def validate_protein_structure_sheet(value: ProteinStructureSheet) -> ProteinStructureSheet:
    return _validate("ProteinStructureSheet", value)

def validate_protein_structure_components(value: ProteinStructureComponents) -> ProteinStructureComponents:
    return _validate("ProteinStructureComponents", value)

def validate_saved_sheet_descriptor(value: SavedSheetDescriptor) -> SavedSheetDescriptor:
    return _validate("SavedSheetDescriptor", value)

def validate_inventory_selection(value: InventorySelection) -> InventorySelection:
    return _validate("InventorySelection", value)

def validate_structure_inventory(value: StructureInventory) -> StructureInventory:
    return _validate("StructureInventory", value)

__all__ = [*PUBLIC_TYPE_NAMES, "protein_structure_schema_definitions", "protein_structure_schema_ref",
           *[name for name in globals() if name.startswith("validate_")]]


# These authority types are deliberately defined AFTER the legacy cohort was
# constructed. Default exported definitions and their historical digests stay
# unchanged; only an explicitly selected action cohort includes these types.
class ProteinStructureActionCustody(TypedDict):
    version: Literal["protein_structure_action_custody_v1"]
    source_ref: SourceRef


class StructureSequenceDescriptorV2(TypedDict):
    version: Literal["structure_sequence_descriptor_v2"]
    custody: ProteinStructureActionCustody
    reference_ref: ReferenceRef
    sequence_file: FileIdentity
    residue_map_file: FileIdentity
    structure_file: FileIdentity
    selection: StructureSelection
    sequence_length: Positive
    allowed_uses: list[Literal["sequence_align", "structure_correspondence"]]


class SavedSheetDescriptorV2(TypedDict):
    version: Literal["protein_structure_saved_sheet_v2"]
    custody: ProteinStructureActionCustody
    sheet_file: FileIdentity
    original_components_file: FileIdentity
    operation: Literal["compare_protein_structures"]
    original_mode: ScientificMode
    allowed_uses: list[Literal["recalculate", "select_projection", "use_transform"]]


def protein_structure_action_schema_definitions() -> dict:
    """Extend only authority positions in a detached opt-in schema cohort."""
    definitions = deepcopy(_DEFINITIONS)
    definitions["ResultCustodyV1"] = deepcopy(definitions["ResultCustody"])
    definitions["ProteinStructureActionCustody"] = {
        "type": "object", "properties": {
            "version": {"enum": ["protein_structure_action_custody_v1"]},
            "source_ref": {**_type_schema(SourceRef), "format": "reference", "x-reference-namespace": "source"}},
        "required": ["version", "source_ref"], "additionalProperties": False}
    for name, version in (("StructureSequenceDescriptor", "structure_sequence_descriptor_v2"),
                          ("SavedSheetDescriptor", "protein_structure_saved_sheet_v2")):
        legacy = deepcopy(_DEFINITIONS[name])
        legacy["properties"]["custody"] = {"$ref": "#/$defs/ResultCustodyV1"}
        definitions[name + "V1"] = legacy
        action = deepcopy(legacy)
        action["properties"]["version"] = {"enum": [version]}
        action["properties"]["custody"] = {"$ref": "#/$defs/ProteinStructureActionCustody"}
        if name == "StructureSequenceDescriptor":
            action["properties"]["reference_ref"].update(format="reference", **{"x-reference-namespace": "reference"})
        definitions[name + "V2"] = action
        definitions[name] = {"anyOf": [{"$ref": "#/$defs/" + name + "V1"},
                                      {"$ref": "#/$defs/" + name + "V2"}]}
    for suffix, descriptor, custody in (("V1", "SavedSheetDescriptorV1", "ResultCustodyV1"),
                                       ("V2", "SavedSheetDescriptorV2", "ProteinStructureActionCustody")):
        received = deepcopy(_DEFINITIONS["ReceivedTransform"])
        received["properties"]["saved_sheet"] = {"$ref": "#/$defs/" + descriptor}
        received["properties"]["calculation_custody"] = {"$ref": "#/$defs/" + custody}
        definitions["ReceivedTransform" + suffix] = received
    definitions["ReceivedTransform"] = {"anyOf": [{"$ref": "#/$defs/ReceivedTransformV1"},
                                                 {"$ref": "#/$defs/ReceivedTransformV2"}]}
    return definitions


def _contains_action_custody(value):
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            if isinstance(item.get("version"), str) and item["version"] in {"protein_structure_action_custody_v1",
                    "structure_sequence_descriptor_v2", "protein_structure_saved_sheet_v2"}:
                return True
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return False


def _action_validator(name):
    definitions = protein_structure_action_schema_definitions()
    if name not in definitions:
        raise ValueError("invalid_schema")
    return _STRICT_VALIDATOR({"$defs": definitions, "$ref": "#/$defs/" + name})


def _action_relations(value):
    if isinstance(value, list):
        for item in value:
            _action_relations(item)
    elif isinstance(value, dict):
        for item in value.values():
            _action_relations(item)
        version = value.get("version")
        if version == "structure_sequence_descriptor_v2":
            _unique(value["allowed_uses"], nonempty=True)
            if (not same(value["selection"]["file_identity"], value["structure_file"])
                    or value["sequence_file"]["byte_length"] != value["sequence_length"]):
                raise ValueError("sequence_artifact_mismatch")
            if (value["sequence_file"]["format"] != "ascii_protein_sequence_v1"
                    or value["residue_map_file"]["format"] != "protein_structure_sequence_v1"):
                raise ValueError("unsupported_format")
        elif version == "protein_structure_saved_sheet_v2":
            _unique(value["allowed_uses"], nonempty=True)
            if (value["sheet_file"]["format"] != "protein_structure_comparison_sheet_v1"
                    or value["original_components_file"]["format"] != "protein_structure_components_v1"):
                raise ValueError("unsupported_format")


def validate_protein_structure_action_custody(value):
    return _validate("ProteinStructureActionCustody", value)


def validate_structure_sequence_descriptor_v2(value):
    return _validate("StructureSequenceDescriptorV2", value)


def validate_saved_sheet_descriptor_v2(value):
    return _validate("SavedSheetDescriptorV2", value)


__all__ += ["ProteinStructureActionCustody", "StructureSequenceDescriptorV2", "SavedSheetDescriptorV2",
    "protein_structure_action_schema_definitions", "validate_protein_structure_action_custody",
    "validate_structure_sequence_descriptor_v2", "validate_saved_sheet_descriptor_v2"]
