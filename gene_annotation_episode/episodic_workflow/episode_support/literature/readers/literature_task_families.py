"""Task-family instructions and metadata owned by A106."""

from collections.abc import Mapping
from importlib import import_module

from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_perturbation_prompt import PERTURBATION_TASK
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_subscore import TASK as A106_SUBSCORE_TASK



_ROWS = {
    'literature_perturbation_cells': ("literature_perturbation_cells", PERTURBATION_TASK, "gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_perturbation_storage", "LiteraturePerturbationRepository", "requested_perturbation_components", "literature.perturbation.populate"),
    'literature_intervention_grading_cells': ("literature_intervention_grading_cells", PERTURBATION_TASK, "gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_intervention_storage", "LiteratureInterventionRepository", "requested_intervention_grading_components", "literature.intervention_grading.populate"),
    'literature_a106_subscore_cells': ("literature_a106_subscore_cells", A106_SUBSCORE_TASK, "gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_subscore_storage", "LiteratureA106SubscoreRepository", "requested_a106_subscore_components", "literature.a106.finalize"),
}

def family_row(source):
    return _ROWS[source]


_BY_REQUEST = {row[4]: source for source, row in _ROWS.items()}
_BY_REQUEST['requested_perturbation_summary_components'] = 'literature_perturbation_cells'
_BY_REQUEST['requested_perturbation_operand_components'] = 'literature_perturbation_cells'
_BY_OPERATION = {row[5]: source for source, row in _ROWS.items()}


def population_task_metadata_specs():
    """A106 operation metadata without another episode's task catalogue."""
    for source, row in _ROWS.items():
        module = import_module(row[2])
        repository = getattr(module, row[3])
        versions = (getattr(module, 'VERSION', repository.record_version),)
        yield source, repository.operations_table, module.PROVIDER, versions


def _selected_sources(value):
    if isinstance(value, (list, tuple)):
        for child in value:
            yield from _selected_sources(child)
        return
    if not isinstance(value, Mapping):
        return
    source = value.get('x-source')
    if source in _ROWS:
        yield source
    reference = value.get('$ref')
    if isinstance(reference, str) and reference.startswith('episode-fact:'):
        source = reference.removeprefix('episode-fact:')
        if source in _ROWS:
            yield source
    if value.get('status') in ('invalid', 'failed', 'error'):
        source = _BY_OPERATION.get(value.get('selected_tool'))
        if source:
            yield source
    if value.get('sheet_ref') and value.get('evaluated_scope') == 'interpreted_reference_perturbation':
        yield 'literature_perturbation_cells'
    if value.get('sheet_ref') and value.get('evaluation_scope') == 'intervention_experimental_evidence':
        yield 'literature_intervention_grading_cells'
    if value.get('sheet_ref') and value.get('evaluation_scope') == 'a106_intervention_experimental_evidence':
        yield 'literature_a106_subscore_cells'
    for name, child in value.items():
        if name not in ('private_history', 'assignment', 'context', 'tools', 'child_options'):
            yield from _selected_sources(child)


def selected_literature_task_sections(state, lookup_results=()):
    """Select A106's own scientific task text from requested and returned facts."""
    sources = []
    assignment = state.get('literature_assignment', {}) if isinstance(state, Mapping) else {}
    if isinstance(assignment, Mapping):
        sources.extend(_BY_REQUEST[key] for key in assignment if key in _BY_REQUEST)
    if isinstance(state, Mapping):
        sources.extend(_selected_sources(state.get('requested_form')))
        sources.extend(_selected_sources(state.get('last_local_outcome')))
        sources.extend(_selected_sources(state.get('literature_selected_population_attempt')))
    sources.extend(_selected_sources(lookup_results))
    sections, seen = [], set()
    for source in sources:
        task = _ROWS[source][1]
        if task not in seen:
            sections.append((source, task))
            seen.add(task)
    return tuple(sections)
