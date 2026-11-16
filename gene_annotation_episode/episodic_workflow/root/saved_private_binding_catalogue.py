"""Literal A105 saved binding reconstruction beside unchanged private descriptors.

This catalogue supports the original eight-member A105 tree only. It does not
choose an axis, authorize a commission, or replace private scientific validators.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from .method_loop.durable import canonical
from .saved_run_records import _failure

VERSION = 'root_saved_private_binding_catalogue_v1'
OWNER = 'A105'
HEAD = 'scientific_process'
LITERATURE = HEAD + '/published_evidence_assessment'
STRATEGY = LITERATURE + '/evidence_search_strategy_improvement'
SEARCH = STRATEGY + '/source_relevance_assessment'
EXAMINATION = SEARCH + '/source_evidence_examination'
PATHS = (HEAD, LITERATURE, STRATEGY, SEARCH, EXAMINATION,
    EXAMINATION + '/table_evidence_extraction',
    EXAMINATION + '/source_coverage_improvement',
    EXAMINATION + '/passage_evidence_extraction')
PRIVATE_PREFIX = 'gene_annotation_episode.episodic_workflow.root.a105.'
TREE_CONSTRUCTOR = PRIVATE_PREFIX + LITERATURE.replace('/', '.') + '.episode.create_binding_tree'
HEAD_CONSTRUCTOR = PRIVATE_PREFIX + 'scientific_process.episode.ScientificProcessEpisode'
LIBRARY_CONSTRUCTOR = PRIVATE_PREFIX + 'scientific_process_library.ScientificProcessLibrary'
TOOLS_CONSTRUCTOR = PRIVATE_PREFIX + 'scientific_tool_library.ScientificToolLibrary'


def _copy(value):
    return json.loads(canonical(value))


def _same(left, right):
    return canonical(left) == canonical(right)


def catalogue_source_record():
    """The literal constructors of the saved tree."""
    return {'version': VERSION, 'owner': OWNER, 'binding_paths': list(PATHS),
        'head_constructor': HEAD_CONSTRUCTOR, 'tree_constructor': TREE_CONSTRUCTOR,
        'library_constructor': LIBRARY_CONSTRUCTOR, 'tool_library_constructor': TOOLS_CONSTRUCTOR}


def _rows(descriptors, records):
    """Validate the complete ordered metadata before selecting any constructor."""
    descriptors, records = _copy(descriptors), _copy(records)
    if type(descriptors) is not list or type(records) is not list or len(records) != len(PATHS):
        raise _failure('unavailable_binding', 'root_saved_private_binding_tree')
    expected = [{'version': 'root_private_binding_selection_v1', 'owner': OWNER,
        'binding_path': path, 'descriptor': descriptor} for path, descriptor in zip(PATHS, descriptors)]
    if len(descriptors) != len(PATHS) or not _same(records, expected):
        raise _failure('identity_conflict', 'episode_binding_owners')
    for path, descriptor in zip(PATHS, descriptors):
        if (type(descriptor) is not dict or set(descriptor) !=
                {'version', 'binding_id', 'configuration'}
                or descriptor['binding_id'] != path
                or type(descriptor['configuration']) is not dict):
            raise _failure('identity_conflict', path)
    if any(not _same(item['configuration'], descriptors[1]['configuration']) for item in descriptors[2:]):
        raise _failure('unavailable_binding', 'original_shared_literature_configuration')
    return descriptors, records


def _constructors():
    """Literal current classes; no saved string is imported or evaluated."""
    from .a105.scientific_process.episode import ScientificProcessEpisode
    from .a105.scientific_process.published_evidence_assessment.episode import LiteratureEpisode
    from .a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.episode import LiteratureEpisode as Strategy
    from .a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.episode import LiteratureEpisode as Search
    from .a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.episode import LiteratureEpisode as Examination
    from .a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.episode import LiteratureEpisode as Table
    from .a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.episode import LiteratureEpisode as Coverage
    from .a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.episode import LiteratureEpisode as Passage
    return (ScientificProcessEpisode, LiteratureEpisode, Strategy, Search, Examination, Table, Coverage, Passage)


def _check_objects(bindings, descriptors, records):
    if len(bindings) != len(PATHS):
        raise _failure('identity_conflict', 'original_eight_binding_tree')
    for binding, cls, path, descriptor in zip(bindings, _constructors(), PATHS, descriptors):
        if type(binding) is not cls or binding.binding_path != path or not _same(binding.as_record(), descriptor):
            raise _failure('identity_conflict', path)
    from .private_episode_selection import PrivateBindingOwners
    PrivateBindingOwners(owners=(OWNER,), entries=((OWNER, binding) for binding in bindings)).validate_saved(records)


def catalogue_for_registry(registry):
    """Record actual supplied objects and their actual frozen-library locations."""
    from .terminal_binding_catalogue import OWNER as TERMINAL_OWNER, catalogue_for_fixed_registry
    if registry.private_owners == (TERMINAL_OWNER,):
        return catalogue_for_fixed_registry(registry)
    records = registry.owner_records()
    if records is None:
        return None
    descriptors, records = _rows(registry.as_record(), records)
    bindings = tuple(registry.for_binding_path(path, owner=OWNER) for path in PATHS)
    _check_objects(bindings, descriptors, records)
    from .a105.scientific_process_library import ScientificProcessLibrary
    from .a105.scientific_tool_library import ScientificToolLibrary
    head = bindings[0]
    if type(head.library) is not ScientificProcessLibrary or type(head.tool_library) is not ScientificToolLibrary:
        raise _failure('identity_conflict', 'original_private_library_types')
    assets = {'library_directory': str(head.library.directory.resolve()),
        'tool_library_directory': str(head.tool_library.directory.resolve())}
    return {'source': catalogue_source_record(), 'assets': assets}


def validate_saved_catalogue(settings):
    """Authenticate source and metadata before any private constructor executes."""
    from .terminal_binding_catalogue import is_fixed_saved_catalogue, validate_saved_fixed_catalogue
    if is_fixed_saved_catalogue(settings):
        return validate_saved_fixed_catalogue(settings)
    records = settings.get('episode_binding_owners')
    catalogue = settings.get('episode_binding_catalogue')
    if records is None and catalogue is None:
        return None
    if records is None or type(catalogue) is not dict or set(catalogue) != {'source', 'assets'}:
        raise _failure('identity_conflict', 'episode_binding_catalogue')
    descriptors, records = _rows(settings.get('episode_bindings'), records)
    if not _same(catalogue['source'], catalogue_source_record()):
        raise _failure('identity_conflict', 'root_saved_private_catalogue_constructors')
    assets = _copy(catalogue['assets'])
    if type(assets) is not dict or set(assets) != {'library_directory', 'tool_library_directory'}:
        raise _failure('identity_conflict', 'original_private_library_locations')
    for value in assets.values():
        if type(value) is not str or str(Path(value).resolve()) != value:
            raise _failure('identity_conflict', 'original_private_library_locations')
    return descriptors, records, assets


def _reopen_head(services, *, descriptor, assets):
    """Original private head reconstruction with exact current descriptor equality."""
    from .a105.scientific_process.episode import ScientificProcessEpisode
    from .a105.scientific_process_library import ScientificProcessLibrary
    from .a105.scientific_tool_library import ScientificToolLibrary
    reference = 'scientific_process'
    try:
        if descriptor.get('version') not in {'scientific_process_episodes_v10', 'scientific_process_episode_v10'}:
            raise _failure('unavailable_binding', reference)
        configuration = descriptor['configuration']
        expected = {'library', 'tool_library', 'child_roles'}
        if 'tool_retrieval' in configuration:
            expected.add('tool_retrieval')
        if 'contract_information_profile' in configuration:
            expected.add('contract_information_profile')
        if 'yield_bindings' in configuration:
            expected.add('yield_bindings')
        if set(configuration) != expected:
            raise _failure('unavailable_binding', reference)
        library = ScientificProcessLibrary(Path(assets['library_directory']))
        if not _same(library.as_record(), configuration['library']):
            raise _failure('identity_conflict', reference)
        tools = ScientificToolLibrary(Path(assets['tool_library_directory']))
        if not _same(tools.as_record(), configuration['tool_library']):
            raise _failure('identity_conflict', reference)
        binding = ScientificProcessEpisode(services, library=library, tool_library=tools, child_roles=configuration['child_roles'], tool_retrieval=configuration.get('tool_retrieval'), contract_information_profile=configuration.get('contract_information_profile'), yield_bindings=configuration.get('yield_bindings'))
        if not _same(binding.as_record(), descriptor):
            raise _failure('identity_conflict', reference)
        return binding
    except (OSError, TypeError, ValueError, KeyError, AttributeError) as error:
        raise _failure('unavailable_binding', reference) from error


def saved_private_factories(settings):
    """Restore one original tree per assembly, preserving actual services identity."""
    from .terminal_binding_catalogue import is_fixed_saved_catalogue
    if is_fixed_saved_catalogue(settings):
        raise _failure('unavailable_binding', 'root_terminal_requires_original_service_factory')
    selected = validate_saved_catalogue(settings)
    if selected is None:
        return None
    descriptors, records, assets = selected
    captured = {}
    def head_factory(services):
        if captured:
            raise _failure('identity_conflict', 'private_factories_already_constructed')
        from .a105.scientific_process.published_evidence_assessment.episode import create_binding_tree
        head = _reopen_head(services, descriptor=descriptors[0], assets=assets)
        children = tuple(create_binding_tree(services, **deepcopy(descriptors[1]['configuration'])))
        bindings = (head, *children)
        _check_objects(bindings, descriptors, records)
        if any(binding.services is not services for binding in bindings):
            raise _failure('identity_conflict', 'original_private_service_receiver')
        captured.update(services=services, bindings=bindings)
        return head
    def child_factory(index):
        def from_original_tree(services):
            if not captured or captured['services'] is not services:
                raise _failure('identity_conflict', 'original_private_service_receiver')
            return captured['bindings'][index]
        return from_original_tree
    return (head_factory, *(child_factory(index) for index in range(1, len(PATHS)))), (OWNER,) * len(PATHS)
