"""The A105 home factory and the literature population declarations on the shared Store.

Real modules, the run's one shared ``gene_annotation_episode.state.Store`` and test-written
inputs; no model call, network or tool execution. The bindings' decision sources and
controllers need the shared yield controllers (``yield_control``)
and each binding's own A105 tool registry (``a105.tools``); what is checked here is what
runs without them: the factory's explicit service requirements and
the literature episode's declared sheet populations, their catalog and the assay grader's
source-sheet reader.
"""
from __future__ import annotations

import pytest

from episode_runtime import BindingRegistry

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.a105.experimental_activity_evidence.runtime_binding import (
    a105_home_factory)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_populations import (CATALOG_ORDER, OPTIONAL, TOOLS, LiteraturePopulations, population_sources,
                                   validate_populations)

NONE_DECLARED = {name: False for name in OPTIONAL}


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MAAA', molecule='protein')
        yield store


def test_the_home_factory_names_each_missing_construction_service(store):
    with pytest.raises(ContractError, match='a105_home_factory_requires_service:a105'):
        BindingRegistry.compose([a105_home_factory], {'store': store})
    with pytest.raises(ContractError, match='a105_home_factory_requires_service:tool_settings'):
        BindingRegistry.compose([a105_home_factory], {'store': store, 'a105': {'head': {}, 'literature': {}}})
    with pytest.raises(ContractError, match='a105_home_factory_tool_settings_must_be_a_mapping'):
        BindingRegistry.compose([a105_home_factory], {'store': store, 'a105': {
            'tool_settings': 'not settings', 'head': {}, 'literature': {}}})


def test_each_optional_population_family_must_be_declared_explicitly():
    assert validate_populations(dict(NONE_DECLARED)) == NONE_DECLARED
    with pytest.raises(ContractError, match='a105_literature_populations_must_declare_each_family'):
        validate_populations({})
    with pytest.raises(ContractError, match='a105_literature_populations_must_declare_each_family'):
        validate_populations({**NONE_DECLARED, 'gel': 1})


def test_grading_and_the_main_sheet_are_always_offered_and_optional_families_only_when_declared(store):
    populations = LiteraturePopulations(store, 'run', dict(NONE_DECLARED))
    names = [entry['name'] for entry in populations.catalog()]
    assert {'literature.assay_grading.populate', 'literature.a105.aggregate', 'literature.rate.populate'} <= set(names)
    assert 'literature.gel.populate' not in names and 'literature.channel.populate' not in names
    assert names == sorted(names, key=CATALOG_ORDER.index) and set(names) <= set(TOOLS)
    everything = LiteraturePopulations(store, 'run', {name: True for name in OPTIONAL})
    assert {entry['name'] for entry in everything.catalog()} == set(TOOLS)
    with pytest.raises(ContractError, match='a105_literature_population_not_declared:gel'):
        populations.repository('gel')


def test_the_grader_reads_source_sheets_through_their_own_repositories(store):
    populations = LiteraturePopulations(store, 'run', {**NONE_DECLARED, 'channel': True})
    grading = populations.repository('grading')
    assert grading.provider == 'literature.a105.assay_grading' and grading.store is store
    assert populations.repository('aggregation').provider == 'literature.a105.aggregation'
    routes = dict(populations.routes())
    assert 'literature_rate_cells' in routes and 'literature_channel_cells' in routes
    assert 'literature_gel_component_cells' not in routes
    assert routes['literature_rate_cells']() is populations.repository('rate')
    with pytest.raises(ContractError, match='assay_grading_reader_namespace_unbound:literature_gel_component_cells'):
        populations.source_cells(None, 'literature_gel_component_cells', 'source_x', [])


def test_population_sources_name_every_read_source_and_sheet():
    arguments = {'sheet_ref': 'source_sheet', 'nested': [{'source_ref': 'source_a'}],
                 'metadata_source_ref': 'source_meta', 'covariance_source_refs': ['source_cov']}
    assert population_sources('literature.assay_grading.populate', arguments) == {
        'source_sheet', 'source_a', 'source_meta', 'source_cov'}
    assert population_sources('literature.rate.populate', arguments) == {'source_a', 'source_meta', 'source_cov'}
