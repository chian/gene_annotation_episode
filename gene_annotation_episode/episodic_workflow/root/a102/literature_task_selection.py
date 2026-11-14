"""Select A102 structure-reading instructions from this episode's work."""

from collections.abc import Mapping

from .a102_literature_bindings import REQUESTED, SOURCE_NAME, STRUCTURE_TASK, TOOL_NAME


def population_task_metadata_specs():
    """Describe only A102's own saved structure population."""
    from .literature_structure_storage import LiteratureStructureRepository, PROVIDER
    repository = LiteratureStructureRepository
    yield (SOURCE_NAME, 'structure_population', repository.operations_table,
        PROVIDER, (repository.record_version,))


def _structure_selected(value):
    if isinstance(value, (list, tuple)):
        return any(_structure_selected(child) for child in value)
    if not isinstance(value, Mapping):
        return False
    if value.get('x-source') == SOURCE_NAME:
        return True
    if value.get('$ref') == 'episode-fact:' + SOURCE_NAME:
        return True
    if value.get('source') == SOURCE_NAME and value.get('information_kind') in {
            'return_contract_information_v1', 'operation_contract_information_v1'}:
        return True
    if value.get('operation') == TOOL_NAME or value.get('selected_tool') == TOOL_NAME:
        return True
    if value.get('tool') == TOOL_NAME and value.get('kind') == 'tool':
        return True
    selection = value.get('selection')
    if (isinstance(selection, Mapping) and selection.get('tool') == TOOL_NAME
            and value.get('admitted_report') is None):
        return True
    if value.get('evaluation_scope') == 'conditional_deposited_model_geometry' and (
            'sheet_ref' in value or 'component' in value):
        return True
    return any(_structure_selected(child) for key, child in value.items()
        if key not in {'arguments', 'input_schema', 'tools', 'child_options',
            'report_schema', 'selection', 'private_history'})


def selected_literature_task_sections(state, lookup_results=()):
    """Return the A102 instruction when its structure work was selected."""
    if not isinstance(state, Mapping):
        return ()
    assignment = state.get('literature_assignment')
    if isinstance(assignment, Mapping) and REQUESTED in assignment:
        return ((SOURCE_NAME, STRUCTURE_TASK),)
    possessed = state.get('literature_owned_population_sources')
    if isinstance(possessed, (tuple, list)) and SOURCE_NAME in possessed:
        return ((SOURCE_NAME, STRUCTURE_TASK),)
    if _structure_selected(state.get('requested_form')) or _structure_selected(state.get('goal')):
        return ((SOURCE_NAME, STRUCTURE_TASK),)
    if _structure_selected(state.get('last_local_outcome')):
        return ((SOURCE_NAME, STRUCTURE_TASK),)
    if _structure_selected(state.get('literature_selected_population_attempt')):
        return ((SOURCE_NAME, STRUCTURE_TASK),)
    if _structure_selected(lookup_results):
        return ((SOURCE_NAME, STRUCTURE_TASK),)
    return ()
