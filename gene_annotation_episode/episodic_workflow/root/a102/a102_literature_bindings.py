"""A102 literature task, source, and population bindings."""

from .literature_structure_calculations import COMPONENTS
from .literature_structure_prompt import STRUCTURE_TASK
from .literature_structure_storage import (PROVIDER, structure_population_schema,
    structure_cells_schema)


TOOL_NAME = 'literature.structure.populate'
SOURCE_NAME = 'literature_structure_cells'
REQUESTED = 'requested_structure_components'


def population_catalog_entry():
    return {'name': TOOL_NAME,
        'description': 'Populate source-model geometry and local residue RSCC components from received coordinates and optional matching deposited validation. Select exact model/author atom groups and fixed physical criteria. Preserve missing endpoints, validation entry/revision mismatch and unreported coordinate uncertainty. The explicit scope is conditional deposited-model geometry; it does not establish population occupancy, causal mechanism, target correspondence or annotation credit.',
        'input_schema': structure_population_schema()}


def task_family_fields():
    return (SOURCE_NAME, STRUCTURE_TASK, 'literature_structure_storage',
        'LiteratureStructureRepository', REQUESTED, TOOL_NAME)


def assignment_component_schema():
    return {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(COMPONENTS)}}


def scope_sources():
    return {'conditional_deposited_model_geometry': SOURCE_NAME}


def fact_source_definition():
    return {'type': 'array', 'meaning':
        'Saved conditional source-model geometry and local residue RSCC components with exact source bindings. Entry/revision validation, fixed required panels, proposed physical predicates and unreported coordinate/measurement uncertainty remain explicit. Conditional state/assignment identities do not establish population occupancy, causal isolation or target annotation credit.',
        'report_schema': structure_cells_schema()}


def population_route(episode):
    return (SOURCE_NAME, REQUESTED, PROVIDER, COMPONENTS,
        episode.literature_structure_repository)


