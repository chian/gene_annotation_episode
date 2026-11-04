"""Proposed data-only additions. Planning artifact; never imported by production.

All fields required unless the parent record explicitly makes the HIC extension
optional. Lists retain source order. Closed JSON validators must enforce the
relationships in CONTRACT.md; these declarations are not executable rules.
"""
from typing import BinaryIO, Literal, Mapping, Sequence, TypedDict
from gene_annotation_episode.chromatin_interaction_contracts import (
    ContactExtraction, ContactSpec, NormalizationSpec, PopulationSpec, ContactTableRole,
)

class HicByteRange(TypedDict):
    offset: int                 # >=0, absolute byte offset in retained source
    size_bytes: int             # >=0, exact encoded size
    sha256: str | None          # only nonnull after complete range read

class HicRuntimeFile(TypedDict):
    path: str                  # absolute actual runtime file
    sha256: str
    size_bytes: int

class HicNativeRuntime(TypedDict):
    zlib_compile_version: str
    zlib_runtime_version: str
    files: list[HicRuntimeFile]

class HicHeaderChromosome(TypedDict):
    chromosome_index: int       # original header ordinal, never renumbered
    chromosome: str             # original token
    native_length: int          # >=0, not always bp
    length_unit: Literal['bp', 'kb_proxy']
    kind: Literal['chromosome', 'all_by_all']

class HicHeader(TypedDict):
    version: Literal['hic_native_header_v1']
    bin_id_space: Literal['chromosome_local']
    source_version: Literal[9]
    byte_order: Literal['little']
    header_range: HicByteRange
    footer_position: int
    normalization_index_position: int
    normalization_index_length: int
    genome_id: str
    chromosomes: list[HicHeaderChromosome]
    bp_resolutions: list[int]
    frag_resolutions: list[int]  # preserved, not selected by this adapter

class HicBlockRead(TypedDict):
    block_id: int
    compressed_range: HicByteRange
    outcome: Literal['complete', 'partial', 'unavailable', 'incompatible']
    decoded_size_bytes: int | None
    decoded_sha256: str | None
    zlib_eof: bool
    zlib_checksum_valid: bool
    payload_consumed_exactly: bool
    matrix_representation: Literal[1, 2] | None
    value_encoding: Literal['int16', 'float32'] | None
    x_encoding: Literal['int16', 'int32'] | None
    y_encoding: Literal['int16', 'int32'] | None
    bin_x_offset: int | None
    bin_y_offset: int | None
    n_records_declared: int | None
    n_records_decoded: int | None  # excludes type2 filler slots, includes type1 nonfinite
    dense_slot_count: int | None
    dense_width: int | None
    dense_filler_slot_count: int | None  # entire encoded rectangle, not population cells
    retained_population_record_count: int | None
    record_ordinal_kind: Literal['sparse_record', 'dense_slot'] | None

class HicVectorRead(TypedDict):
    normalization_type: str
    chromosome_index: int
    unit: Literal['BP']
    resolution_bp: int
    index_extent: Literal['complete', 'partial', 'unavailable', 'incompatible']
    native_range: HicByteRange | None
    n_values_declared: int | None
    n_values_read: int | None
    native_dtype: Literal['<f4'] | None
    selected_bin_start: int
    selected_bin_end_exclusive: int
    physical_chromosome_bin_count: int
    extra_terminal_values: int | None
    outcome: Literal['complete', 'partial', 'unavailable', 'incompatible']

class HicPopulationRead(TypedDict):
    version: Literal['hic_population_read_v1']
    source_sha256: str
    scan_scope: Literal['all_indexed_blocks_selected_cis_zoom']
    matrix_key: str              # exact chrIdx_chrIdx
    matrix_index_range: HicByteRange
    matrix_metadata_range: HicByteRange
    zoom_index_range: HicByteRange
    chromosome1_index: int
    chromosome2_index: int
    unit: Literal['BP']
    resolution_bp: int
    block_bin_count: int
    block_column_count: int
    declared_block_count: int
    blocks: list[HicBlockRead]   # complete native block-index order, one outcome each
    selected_normalization: HicVectorRead | None

# Proposed closed Locator union additions:
# {kind:'hic_bytes', value:{offset:int>=0, size_bytes:int>=0,
#                          section:'header'|'footer'|'matrix_index'|'zoom_index'|
#                                  'normalization_index'|'normalization_vector'}}
# {kind:'hic_vector', value:{normalization_type:str, chromosome_index:int>=0,
#                           unit:'BP', resolution_bp:int>0, bin_index:int>=0|null}}
# HicBlockRead and HicPopulationRead fields unavailable before matrix-index
# discovery do not become dummy records: PopulationReadEvidence.hic may be null
# for failed HIC populations. Nonnull is mandatory for complete HIC populations.

def read_hic_contacts(
    stream: BinaryIO, *, spec: ContactSpec, normalization: NormalizationSpec,
    populations: Sequence[PopulationSpec],
    table_streams: Mapping[tuple[str, ContactTableRole], BinaryIO],
) -> ContactExtraction: ...
