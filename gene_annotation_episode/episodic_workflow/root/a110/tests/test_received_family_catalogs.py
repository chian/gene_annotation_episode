"""Real A110 retained receiving catalogs with explicitly controlled availability.

The fixture bypasses construction and supplies only availability flags/service
names. Every catalog function and original schema factory executes unchanged.
No provider, native job, database or scientific assessment is exercised here.
"""
from copy import deepcopy
from types import SimpleNamespace

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_receiving_owner import HistoricalReceivedExecutionOwner


@pytest.fixture
def all_family_catalog_owner():
    owner = object.__new__(HistoricalReceivedExecutionOwner)
    for name in (
        'native_flux_balance', 'native_expression_nmf', 'native_chromatin_interaction',
        'native_genomic_overlap', 'native_rna_structure', 'native_blast_standard_database',
        'native_blast_database', 'native_hmmer_preparation', 'native_infernal_preparation',
        'native_blast', 'native_infernal', 'rna_structure_comparison',
    ):
        setattr(owner, name + '_results', object())
        setattr(owner, name + '_returns', object())
    owner.atac_results = owner.atac_returns = object()
    owner.native_flux_balance_returns = SimpleNamespace(ordinary_backend=None)
    owner.api_execution = SimpleNamespace(services={name:SimpleNamespace(service=name) for name in (
        'bvbrc_appservice', 'bvbrc_data', 'bvbrc_minhash', 'uniprot', 'enrichr',
        'sequence_support', 'rfam_batch', 'ncbi_blast',
    )})
    return owner


def check_catalog(catalog):
    assert type(catalog) is dict and catalog
    for source, definition in catalog.items():
        assert type(source) is str and source
        assert type(definition['meaning']) is str and definition['meaning']
        if 'report_schema' in definition:
            Draft202012Validator.check_schema(definition['report_schema'])


def test_all_native_and_api_fact_catalogs_keep_original_reference_qualifications(all_family_catalog_owner):
    owner = all_family_catalog_owner
    actual = owner.fact_sources('results')
    check_catalog(actual)
    assert actual['execution_completed']['type'] == 'boolean'
    assert actual['execution_result_origin']['type'] == ['object', 'null']
    assert 'failed native attempts' in actual['execution_result_origin']['meaning']
    assert 'unrequested numerical rows' in actual['execution_blast_pairwise_result_refs']['meaning']
    for key in ('execution_blast_pairwise_result_refs', 'execution_infernal_result_refs'):
        assert actual[key]['report_schema'] == {
            'type':'array', 'uniqueItems':True,
            'items':{'type':'string', 'format':'reference', 'x-reference-namespace':'execution_result'},
            'x-source':key,
        }
    assert actual['bvbrc_appservice_support_refs']['report_schema']['items']['x-reference-namespace'] == 'bvbrc_appservice_support'


@pytest.mark.parametrize('role', ['annotation', 'biochemical_feasibility_evidence'])
def test_actual_received_catalog_composes_real_families_for_each_receiving_role(all_family_catalog_owner, role):
    owner = all_family_catalog_owner
    actual = owner.received_report_sources(role)
    check_catalog(actual)
    assert {'execution_file_source_refs', 'execution_file_capture_outcomes',
        'execution_blast_pairwise_result_refs', 'execution_infernal_result_refs',
        'bvbrc_appservice_support_refs'} <= actual.keys()
    assert 'execution_completed' not in actual
    assert 'execution_result_origin' not in actual
    before = deepcopy(actual)
    actual['execution_blast_pairwise_result_refs']['report_schema']['items']['format'] = 'changed-by-receiver'
    assert owner.received_report_sources(role) == before


def test_original_receiver_role_boundary_keeps_catalog_absent(all_family_catalog_owner):
    assert all_family_catalog_owner.received_report_sources('results') == {}
    assert all_family_catalog_owner.received_report_sources('launch') == {}
