"""Planning-only in-process ports; never imported by production.

All JSON record types imported below are exactly the corresponding closed
RECORD_SCHEMA.json $defs. C1 will supply their production type declarations.
This file fixes the array interface that JSON fixture records cannot describe.
"""
from typing import BinaryIO, ContextManager, Literal, Mapping, Sequence, TypedDict
import numpy as np
import numpy.typing as npt
from gene_annotation_episode.chromatin_interaction_contracts import (
    ChromatinRequest, ContactSpec, NormalizationSpec, PopulationSpec, ElementSpec,
    MetadataSpec, ContactExtraction, ParsedElements, MetadataRelations,
    TableDescriptor, ContactSheet, ContactParameters, InsulationParameters,
    CalculationParameters, ContactComponents, InsulationComponents,
    ChromatinComponents, ResultSelector, RequestedProjection,
)

ContactTableRole = Literal['bins', 'contacts', 'weights', 'cell_states', 'dense_values']

class ContactPopulationArrays(TypedDict):
    population_key: str
    # Every nonnull array is an ordinary read-only numpy ndarray, possibly backed
    # by a read-only mmap. Exact shape/dtype/order are in RECORD_SHAPES.md.
    bins: npt.NDArray[np.void] | None
    contacts: npt.NDArray[np.void] | None
    weights: npt.NDArray[np.float64] | None
    cell_states: npt.NDArray[np.void] | None
    dense_values: npt.NDArray[np.integer | np.floating] | None

class ContactTables(TypedDict):
    version: Literal['chromatin_contact_arrays_v1']
    # Read-only mapping; exact keys are the sheet's population keys, including
    # unavailable populations with null arrays. No unknown population fallback.
    populations: Mapping[str, ContactPopulationArrays]

def validate_chromatin_record(kind: str, value: object) -> dict: ...
def read_cooler_contacts(
    stream: BinaryIO, *, spec: ContactSpec, normalization: NormalizationSpec,
    populations: Sequence[PopulationSpec],
    table_streams: Mapping[tuple[str, ContactTableRole], BinaryIO],
) -> ContactExtraction: ...
def read_hic_contacts(
    stream: BinaryIO, *, spec: ContactSpec, normalization: NormalizationSpec,
    populations: Sequence[PopulationSpec],
    table_streams: Mapping[tuple[str, ContactTableRole], BinaryIO],
) -> ContactExtraction: ...
def parse_chromatin_elements(content: bytes, *, spec: ElementSpec) -> ParsedElements: ...
def extract_chromatin_metadata(
    *, native: ContactExtraction, supplied: MetadataSpec,
    elements: ParsedElements | None,
) -> MetadataRelations: ...
def build_chromatin_sheet(
    *, request: ChromatinRequest, contacts: ContactExtraction,
    elements: ParsedElements | None, metadata: MetadataRelations,
    tables: Sequence[TableDescriptor], table_views: ContactTables,
) -> ContactSheet: ...
def open_chromatin_contact_tables(
    descriptors: Sequence[TableDescriptor], *, streams: Mapping[str, BinaryIO],
) -> ContextManager[ContactTables]: ...
def read_chromatin_sheet_tables(
    sheet: ContactSheet, *, streams: Mapping[str, BinaryIO],
) -> ContextManager[ContactTables]: ...
def calculate_contact_enrichment(
    sheet: ContactSheet, *, tables: ContactTables,
    normalization: NormalizationSpec, parameters: ContactParameters,
) -> ContactComponents: ...
def calculate_insulation_components(
    sheet: ContactSheet, *, tables: ContactTables,
    normalization: NormalizationSpec, parameters: InsulationParameters,
) -> InsulationComponents: ...
def calculate_chromatin_components(
    sheet: ContactSheet, *, tables: ContactTables, parameters: CalculationParameters,
) -> ChromatinComponents: ...
def project_chromatin_result(
    sheet: ContactSheet, components: ChromatinComponents, *, selector: ResultSelector,
) -> RequestedProjection: ...
