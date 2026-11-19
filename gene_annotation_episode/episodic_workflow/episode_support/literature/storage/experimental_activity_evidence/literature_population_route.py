"""The A105 population route of a literature episode: which population tools are offered, how one runs, and how the
assay grader reads the cells of a reader sheet the episode populated.

Carried from the old ``LiteratureOperations.catalog`` / ``execute`` population branch, ``_population_routes`` and
``scientific_records._assay_grading_source_cells`` of the A105 literature episodes at ``97308b94c``. The route is
offered when ``settings['rate_population']`` is true, each family under its own flag (the old configuration
``rate_population=False`` and its flags are settings of the same names; each is read directly).

The assay grader (``literature.assay_grading.populate``) and the across-experiment aggregation
(``literature.a105.aggregate``) save their sheets through the custody repositories of
``literature_assay_grading_storage`` and ``literature_aggregation_storage``. The reader families save theirs through
their own repositories (``<Repository>(store, run_id)`` with the episode's ``LiteratureContext``), as the library
holds them."""
from importlib import import_module

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_population_catalog import (
    population_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_assay_inputs import (
    materialize_text_witness_inputs)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_task_families import (
    ROWS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_aggregation_storage import (
    LiteratureA105AggregationRepository)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_grading_storage import (
    LiteratureAssayGradingRepository)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import (
    LiteratureContext)

FLAGS = ('assay_grading_population', 'ratio_source_population', 'controlled_response_population', 'gel_population',
         'completion_time_population', 'product_partition_population', 'active_site_population',
         'parent_depletion_population', 'stoichiometric_balance_population', 'compiled_assay_population',
         'channel_population', 'ion_discrimination_population')
_STORAGE = 'gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.'
# The reader repository each population tool writes (the old ``repo`` dispatch).
REPOSITORIES = {
    **{tool: (module, repository) for _namespace, _task, module, repository, _requested, tool in ROWS.values()
       if tool not in ('literature.assay_grading.populate', 'literature.a105.aggregate')},
    'literature.rate.populate': (_STORAGE + 'literature_rate_storage', 'LiteratureRateRepository'),
    'literature.rate.source.populate': (_STORAGE + 'literature_rate_storage', 'LiteratureRateRepository'),
    'literature.quantity.populate': (_STORAGE + 'literature_quantity_storage', 'LiteratureQuantityRepository'),
    'literature.ratio.populate': (_STORAGE + 'literature_ratio_storage', 'LiteratureRatioRepository'),
    'literature.optical.populate': (_STORAGE + 'literature_optical_storage', 'LiteratureOpticalRepository'),
    'literature.figure.populate': (_STORAGE + 'literature_figure_storage', 'LiteratureFigureRepository'),
    'literature.kinetic.populate': (_STORAGE + 'literature_kinetic_storage', 'LiteratureKineticRepository'),
    'literature.rate.observations.populate': (_STORAGE + 'literature_rate_observation_storage',
                                              'LiteratureRateObservationRepository'),
}
# The reader sheet namespaces the grader takes a ``received_component`` from, by the repository that saved them.
NAMESPACES = {namespace: (module, repository) for namespace, _task, module, repository, _requested, tool in ROWS.values()
              if tool not in ('literature.assay_grading.populate', 'literature.a105.aggregate')}
NAMESPACES.update({
    'literature_rate_cells': (_STORAGE + 'literature_rate_storage', 'LiteratureRateRepository'),
    'literature_ratio_cells': (_STORAGE + 'literature_ratio_storage', 'LiteratureRatioRepository'),
    'literature_optical_cells': (_STORAGE + 'literature_optical_storage', 'LiteratureOpticalRepository'),
})


def population_entries(settings):
    """The population operations offered: none unless ``rate_population``; otherwise the catalog under the flags."""
    if not settings['rate_population']:
        return []
    return population_catalog(**{name: settings[name] for name in FLAGS})


def _context(run_id, episode_id, binding_path, scope, assignment, store):
    return LiteratureContext(run_id=run_id, episode_id=episode_id, role='literature',
                             path=tuple(binding_path.split('/')), scope=scope, assignment=assignment,
                             request={'scope': scope}, received_record_refs=tuple(store.refs()))


def _reader(store, run_id, module, repository):
    return getattr(import_module(module), repository)(store, run_id)


def reader_cells(store, run_id, episode_id, binding_path, scope, assignment, offered):
    """``read_cells(namespace, sheet_ref, components)`` for the grader: the cells of a held reader sheet through the
    repository of its family, when that family's population is offered (the old ``_assay_grading_source_cells``);
    any other namespace is ``assay_grading_reader_namespace_unbound``."""
    def read_cells(namespace, sheet_ref, components):
        if namespace not in NAMESPACES or not any(REPOSITORIES.get(tool) == NAMESPACES[namespace] for tool in offered):
            raise ContractError('assay_grading_reader_namespace_unbound')
        repository = _reader(store, run_id, *NAMESPACES[namespace])
        return repository.fact_cells(_context(run_id, episode_id, binding_path, scope, assignment, store),
                                     [sheet_ref], components=components)
    return read_cells


def run_population(name, store, arguments, operation_key, *, scope, page_source_ref, assignment, requested,
                   run_id, episode_id, binding_path, offered, read_source):
    """One population operation. ``read_source(ref, representation)`` returns the held bytes of a source below the
    assigned page (the old ``_materialize_text_arguments`` reader); ``requested`` the components the parent asked
    for. A refusal is the library's ``ContractError``."""
    materialized = materialize_text_witness_inputs(arguments, read_source=read_source)
    if name == 'literature.assay_grading.populate':
        repository = LiteratureAssayGradingRepository(
            store, reader_cells(store, run_id, episode_id, binding_path, scope, assignment, offered))
        return repository.populate(scope, page_source_ref, materialized, operation_key,
                                   requested.get('requested_assay_grading_components', ()))
    if name == 'literature.a105.aggregate':
        return LiteratureA105AggregationRepository(store).populate(
            scope, materialized, operation_key, requested.get('requested_a105_aggregation_components', ()))
    module, repository_name = REPOSITORIES[name]
    if name == 'literature.figure.populate' and materialized.get('version') == 'literature_figure_endpoint_signal_population_v1':
        module, repository_name = _STORAGE + 'literature_endpoint_signal_storage', 'LiteratureEndpointSignalRepository'
    if name == 'literature.kinetic.populate' and materialized.get('version') == 'literature_kinetic_summary_precision_population_v1':
        module, repository_name = (_STORAGE + 'literature_kinetic_summary_precision_storage',
                                   'LiteratureKineticSummaryPrecisionRepository')
    method = {'literature.controlled_response.source_v3.populate': 'populate_v3',
              'literature.rate.source.populate': 'populate_native'}.get(name, 'populate')
    repository = _reader(store, run_id, module, repository_name)
    context = _context(run_id, episode_id, binding_path, scope, {**assignment, **requested}, store)
    return getattr(repository, method)(context, materialized, operation_key)


# The repositories that authorize every source read and record read of an episode while the population route is on
# (the old ``_tool_arguments`` source authorization: ``_endpoint_signal_repository``, ``_summary_precision_repository``,
# ``_measurement_comparison_repository``, ``_concentration_window_repository``).
ACCESS_AUTHORITIES = (('literature_endpoint_signal_storage', 'LiteratureEndpointSignalRepository'),
                      ('literature_kinetic_summary_precision_storage', 'LiteratureKineticSummaryPrecisionRepository'),
                      ('literature_measurement_comparison_storage', 'LiteratureMeasurementComparisonRepository'),
                      ('literature_concentration_window_storage', 'LiteratureConcentrationWindowRepository'))


def authorize_source_access(store, run_id, episode_id, binding_path, scope, assignment, source_ref, representation,
                            tool_name):
    """Each access authority's ``authorize_source_access`` for one source read; a refusal is its ``ContractError``."""
    context = _context(run_id, episode_id, binding_path, scope, assignment, store)
    for module, repository in ACCESS_AUTHORITIES:
        _reader(store, run_id, _STORAGE + module, repository).authorize_source_access(
            context, source_ref, representation, tool_name)


def authorize_record_access(store, run_id, episode_id, binding_path, scope, assignment, record):
    """Each access authority's ``authorize_record_access`` for one record a query returned or names."""
    context = _context(run_id, episode_id, binding_path, scope, assignment, store)
    for module, repository in ACCESS_AUTHORITIES:
        _reader(store, run_id, _STORAGE + module, repository).authorize_record_access(context, record)


__all__ = ['FLAGS', 'REPOSITORIES', 'NAMESPACES', 'ACCESS_AUTHORITIES', 'population_entries', 'reader_cells',
           'run_population', 'authorize_source_access', 'authorize_record_access']
