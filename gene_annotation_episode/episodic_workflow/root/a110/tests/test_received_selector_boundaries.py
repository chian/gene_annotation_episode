"""Real selector/receiving boundaries with explicit controlled availability.

Direct selector tests execute existing scientific contract validators. Receiving
tests bypass construction and set only result-family availability and resources;
the real assignment_schema method and schema owners execute. No API client,
provider, database, native worker, saved episode or scientific result is claimed.
Imports are inside cases so unchanged-current failures are retained per boundary.
"""
from copy import deepcopy
from importlib import import_module

from jsonschema import Draft202012Validator
import pytest


AXIS = 'gene_annotation_episode.episodic_workflow.root.a110'


def _fluorescence_selector(contracts, mode):
    value = {'version': 'fluorescence_result_selector_v1', 'mode': mode,
             'selection': {'requests': [], 'offset': 0, 'limit': 1},
             'context_fields': ['samples'], 'saved_sheet_file': None, 'parameters': None}
    if mode == 'saved_sheet_recalculation':
        value['saved_sheet_file'] = {'artifact_ref': 'artifact_' + '0' * 64,
                                    'sha256': '0' * 64, 'size_bytes': 0,
                                    'format': contracts.core.SHEET_SCHEMA}
        value['parameters'] = {'fraction_requests': [], 'intensity_requests': [],
                               'control_requests': [], 'native_comparison_requests': []}
    return value


def _protein_selector():
    # The original resource-registration test's concrete inventory selection.
    return {'version': 'protein_structure_result_selector_v1',
            'acquisition': 'complete_bound_bundle', 'saved_sheet': None, 'parameters': None,
            'projections': [{'projection_id': 'inventory', 'family': 'structure_inventory',
                             'members': {'kind': 'all_inventory_rows'}, 'fields': ['model'],
                             'window': None, 'delivery_kind': 'values'}],
            'return_saved_sheet': False, 'sequence_allowed_uses': []}


def _receiving_owner(*, protein):
    module = import_module(AXIS + '.library.received_execution_information.historical_receiving_owner')
    owner = object.__new__(module.HistoricalReceivedExecutionOwner)
    for name in ('native_expression_nmf_results', 'native_flux_balance_results', 'atac_results',
                 'native_chromatin_interaction_results', 'native_rna_structure_results',
                 'native_genomic_overlap_results'):
        setattr(owner, name, None)
    owner.resources = {'controlled_local': {'kind': 'local',
                       'native_protein_structure': [{'operation': 'inspect'}] if protein else []}}
    return owner


@pytest.mark.parametrize('mode', ['native_result', 'saved_sheet_recalculation'])
def test_original_fluorescence_selector_schema_and_validator_accept_both_modes(mode):
    contracts = import_module(AXIS + '.fluorescence_result_contracts')
    schema = contracts.FLUORESCENCE_RESULT_SELECTOR_SCHEMA
    Draft202012Validator.check_schema(schema)
    value = _fluorescence_selector(contracts, mode)
    Draft202012Validator(schema).validate(value)
    selected = contracts.validate_fluorescence_selector(value)
    assert selected == value and selected is not value
    selected['context_fields'].clear()
    assert value['context_fields'] == ['samples']


def test_fluorescence_invalid_context_keeps_original_failure_code():
    contracts = import_module(AXIS + '.fluorescence_result_contracts')
    value = _fluorescence_selector(contracts, 'native_result')
    value['context_fields'] = ['samples', 'samples']
    assert not Draft202012Validator(contracts.FLUORESCENCE_RESULT_SELECTOR_SCHEMA).is_valid(value)
    with pytest.raises(ValueError, match='^projection_contract_invalid$'):
        contracts.validate_fluorescence_selector(value)


def test_original_protein_schema_is_detached_and_accepts_its_inventory_selector():
    contracts = import_module(AXIS + '.protein_structure_selection')
    schema = contracts.protein_structure_result_selector_schema()
    before = deepcopy(schema)
    Draft202012Validator.check_schema(schema)
    value = _protein_selector()
    Draft202012Validator(schema).validate(value)
    assert contracts.validate_protein_structure_result_selector(value) == value
    schema['$defs'].clear()
    assert contracts.protein_structure_result_selector_schema() == before


def test_protein_invalid_boolean_keeps_original_failure_code():
    contracts = import_module(AXIS + '.protein_structure_selection')
    value = _protein_selector()
    value['return_saved_sheet'] = 0
    assert not Draft202012Validator(contracts.protein_structure_result_selector_schema()).is_valid(value)
    with pytest.raises(ValueError, match='^invalid_schema$'):
        contracts.validate_protein_structure_result_selector(value)


@pytest.mark.parametrize('protein', [False, True])
def test_real_receiving_assignment_composes_available_selectors_without_mutating_owners(protein):
    owner = _receiving_owner(protein=protein)
    fluorescence = import_module(AXIS + '.fluorescence_result_contracts')
    schema = owner.assignment_schema('results')
    Draft202012Validator.check_schema(schema)
    alternatives = schema['properties']['selector']['allOf']
    selected = {row['if']['properties']['version'].get('const'): row['then'] for row in alternatives}
    assert selected['fluorescence_result_selector_v1'] == fluorescence.FLUORESCENCE_RESULT_SELECTOR_SCHEMA
    assert ('protein_structure_result_selector_v1' in selected) is protein
    if protein:
        contracts = import_module(AXIS + '.protein_structure_selection')
        assert selected['protein_structure_result_selector_v1'] == contracts.protein_structure_result_selector_schema()
    before = deepcopy(schema)
    selected['fluorescence_result_selector_v1']['properties'].clear()
    assert owner.assignment_schema('results') == before


def test_real_receiving_assignment_rejects_original_unknown_role():
    owner = _receiving_owner(protein=False)
    with pytest.raises(ValueError, match='^unknown_execution_episode_role$'):
        owner.assignment_schema('unrecognized_role')
