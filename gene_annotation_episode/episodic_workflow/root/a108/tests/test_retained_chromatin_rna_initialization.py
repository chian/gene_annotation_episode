"""Original closed read schemas; synthetic controls, no acquisition or science.

The PopulationSeal control combines unchanged original worked examples solely
to exercise the original additive native-header requirement. It is not a saved
execution, receipt, biological observation or new assessed result.
"""
from copy import deepcopy
from functools import lru_cache
import hashlib
from importlib import import_module
import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator, ValidationError

AXES=('a101','a105','a106','a108')

def owner(axis,name):
    return import_module('gene_annotation_episode.episodic_workflow.root.'+axis+'.library.retained_input_authority.'+name)

@lru_cache(maxsize=1)
def worked():
    path=Path(__file__).resolve().parents[2]/'tests/fixtures/chromatin/WORKED_RECORDS.json'
    raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()=='d1002a156dac237954f0663c2f98a422b8e1258a69f8ad00aa9610f6ad9be82a'
    return {row['example_key']:row['record'] for row in json.loads(raw)['records']}

@pytest.mark.parametrize('axis',AXES)
@pytest.mark.parametrize('native_present',[False,True])
def test_population_seal_requires_original_native_header(axis,native_present):
    c=owner(axis,'chromatin_interaction_contracts');seal=deepcopy(worked()['handoff.population_seal'])
    if native_present:
        seal['native']=deepcopy(worked()['raw.sheet']['native'])
        assert c.validate_chromatin_record('PopulationSeal',seal)==seal
        changed=deepcopy(seal);changed['native']['foreign_header']=True
        with pytest.raises(c.ChromatinValidationError):c.validate_chromatin_record('PopulationSeal',changed)
    else:
        with pytest.raises(c.ChromatinValidationError,match='native'):c.validate_chromatin_record('PopulationSeal',seal)

def hic_header():
    return {'version':'hic_native_header_v1','bin_id_space':'chromosome_local','source_version':9,'byte_order':'little',
        'header_range':{'offset':0,'size_bytes':8,'sha256':'1'*64},'footer_position':8,
        'normalization_index_position':8,'normalization_index_length':0,'genome_id':'controlled-genome',
        'chromosomes':[{'chromosome_index':0,'chromosome':'chr1','native_length':1000,'length_unit':'bp','kind':'chromosome'}],
        'bp_resolutions':[100],'frag_resolutions':[]}

@pytest.mark.parametrize('axis',AXES)
@pytest.mark.parametrize('bad_index',[False,True])
def test_hic_header_schema_and_original_index_relationship(axis,bad_index):
    c=owner(axis,'chromatin_interaction_contracts');value=hic_header()
    if bad_index:
        value['chromosomes'][0]['chromosome_index']=1
        with pytest.raises(c.ChromatinValidationError,match='hic_original_chromosome_indices_required'):c.validate_chromatin_record('HicHeader',value)
    else:
        returned=c.validate_chromatin_record('HicHeader',value);assert returned==value and returned is not value
        returned['chromosomes'].clear();assert value['chromosomes']

@pytest.mark.parametrize('axis',AXES)
def test_hic_failure_code_and_locators_use_original_closed_shapes(axis):
    c=owner(axis,'chromatin_interaction_contracts')
    base=worked()['missing_matrix.failure']
    additions=[{'code':'hic_matrix_absent'},
        {'locator':{'kind':'hic_bytes','value':{'offset':0,'size_bytes':10,'section':'header'}}},
        {'locator':{'kind':'hic_vector','value':{'normalization_type':'VC','chromosome_index':1,'unit':'BP','resolution_bp':10,'bin_index':None}}}]
    for addition in additions:
        value=deepcopy(base);value.update(addition);assert c.validate_chromatin_record('Failure',value)==value
    changed=deepcopy(base);changed['locator']={'kind':'hic_bytes','value':{'offset':0,'size_bytes':10,'section':'unrecognized'}}
    with pytest.raises(c.ChromatinValidationError):c.validate_chromatin_record('Failure',changed)

RNA_ROWS=(
    ('rna_pair_compare_v1.lost_pair_count','lost_pair_count','pairs','derived_topology_comparison',1),
    ('rna_site_compare_v1.change_indicator','change_indicator','indicator','derived_topology_comparison',1),
    ('rna_energy_compare_v1.energy_delta','energy_delta','kcal/mol','derived_energy_difference',-1.0),
    ('rna_scan_energy_v1.member_rank_start','member_rank_start','rank','derived_scan_rank',1),
    ('rna_scan_site_v1.changed_variant_fraction','changed_variant_fraction','fraction','derived_scan_count',0.5),
)

@pytest.mark.parametrize('axis',AXES)
@pytest.mark.parametrize('unregistered',[False,True])
def test_each_original_rna_family_reaches_returned_numeric_schema(axis,unregistered):
    c=owner(axis,'rna_structure_comparison_contracts');views=owner(axis,'rna_structure_comparison_views')
    for formula,metric,unit,origin,value in RNA_ROWS:
        cell={'metric':metric,'value':value,'unit':unit,'state':'present','reason':None,'numerator':None,'denominator':None,
            'origin':origin,'formula_id':formula if not unregistered else 'unregistered_scientific_formula',
            'population_id':'controlled-population','selection_id':None,
            'uncertainty':{'state':'not_produced','value':None,'reason':c.UNCERTAINTY_REASON}}
        validator=Draft202012Validator(views.RETURNED_NUMERIC_CELL_SCHEMA)
        if unregistered:
            with pytest.raises(ValidationError):validator.validate(cell)
        else:
            spec=c.METRIC_SPECS[formula];assert spec['metric']==metric and unit in spec['units'] and origin in spec['origins']
            validator.validate(cell)
            assert cell['uncertainty']=={'state':'not_produced','value':None,'reason':'selected_inputs_do_not_produce_comparison_uncertainty'}
