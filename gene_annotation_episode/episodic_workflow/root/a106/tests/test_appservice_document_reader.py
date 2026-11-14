"""Offline schema/data binding controls; no complete receipt or science claim."""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.root.a106 import bvbrc_appservice_contracts as active
from gene_annotation_episode.episodic_workflow.root.a106.bvbrc_appservice_custody import AppServiceCustody, AppServiceCustodyError
from gene_annotation_episode.episodic_workflow.root.a106.state import Store

FIXTURE=Path(__file__).parent/'fixtures/appservice_read_contracts/original_schemas.json'
ORIGINAL_SHA='4e545e81b22b09ed121099b255e518c1ef33a9af5fe7ebf6f31de79d5956fd50'
CURRENT_SHA='d39fb13d799731868634601d27c35905836c534782be30f6aac0174bfd18c256'


def original_document():
    raw=FIXTURE.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==ORIGINAL_SHA
    return json.loads(raw)


def read_binding():
    return importlib.import_module('gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.appservice_read_contracts')


def test_active_schema_keeps_actual_capability_document():
    path=Path(active.__file__).with_name('bvbrc_appservice_schemas.json')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==CURRENT_SHA
    schema=active.contract_schema('RequiredApplication')
    assert schema['$defs']['RequiredApplication']['enum']==['TnSeq','RNASeq']
    for name in ('TnSeq','RNASeq'):
        assert active.validate_contract('RequiredApplication',name)==name
    with pytest.raises(active.ContractValidationError) as error:
        active.validate_contract('RequiredApplication','Variation')
    assert error.value.code=='contract_shape_invalid'


def test_original_document_diff_is_only_the_retained_application_enum():
    original=original_document()
    current=json.loads(Path(active.__file__).with_name('bvbrc_appservice_schemas.json').read_text())
    current['$defs']['RequiredApplication']['enum']=original['$defs']['RequiredApplication']['enum']
    assert current==original


@pytest.mark.parametrize('name',['Variation','GenomeAnnotation'])
def test_explicit_incoming_document_accepts_original_profile(name):
    reader=read_binding()
    assert reader.ContractValidationError is active.ContractValidationError
    assert reader.validate_contract('RequiredApplication',name)==name
    assert reader.contract_schema('RequiredApplication')['$defs']['RequiredApplication']==original_document()['$defs']['RequiredApplication']


@pytest.mark.parametrize('value',[True,1,'unregistered_application',''])
def test_original_document_keeps_typed_value_rejection(value):
    reader=read_binding()
    with pytest.raises(active.ContractValidationError) as error:
        reader.validate_contract('RequiredApplication',value)
    assert error.value.code=='contract_shape_invalid'


def test_incoming_cache_success_cannot_authorize_active_profile():
    reader=read_binding()
    assert reader.validate_contract('RequiredApplication','Variation')=='Variation'
    with pytest.raises(active.ContractValidationError,match='contract_shape_invalid'):
        active.validate_contract('RequiredApplication','Variation')
    assert active.validate_contract('RequiredApplication','RNASeq')=='RNASeq'
    assert reader.validate_contract('RequiredApplication','Variation')=='Variation'


@pytest.mark.parametrize('incoming',[False,True])
def test_recursive_schema_keeps_original_relationship_checks(incoming):
    validator=read_binding().validate_contract if incoming else active.validate_contract
    value=[2,5];saved=deepcopy(value)
    result=validator('Range',value)
    assert result==saved and result is not value and value==saved
    with pytest.raises(active.ContractValidationError) as error:
        validator('Range',[5,2])
    assert error.value.code=='range_conflict'
    with pytest.raises(active.ContractValidationError,match='contract_shape_invalid'):
        validator('Range',[True,2])


def test_read_schema_result_is_detached_from_both_documents():
    reader=read_binding();before=reader.contract_schema('RequiredApplication')
    changed=reader.contract_schema('RequiredApplication')
    changed['$defs']['RequiredApplication']['enum'].clear()
    assert reader.contract_schema('RequiredApplication')==before
    assert active.contract_schema('RequiredApplication')['$defs']['RequiredApplication']['enum']==['TnSeq','RNASeq']


@pytest.mark.parametrize('incoming',[False,True])
def test_actual_custody_constructor_selects_explicit_document(tmp_path,incoming):
    with Store(tmp_path/'state') as store:
        kwargs={'_contract_validator':read_binding().validate_contract} if incoming else {}
        custody=AppServiceCustody(store,'controlled-document-reader',**kwargs)
        assert type(custody) is AppServiceCustody
        assert custody._validate('RequiredApplication','TnSeq')=='TnSeq'
        if incoming:
            assert custody._validate('RequiredApplication','Variation')=='Variation'
        else:
            with pytest.raises(AppServiceCustodyError) as error:
                custody._validate('RequiredApplication','Variation')
            assert error.value.code=='bvbrc_appservice_custody_contract_shape_invalid'
        with pytest.raises(AppServiceCustodyError) as error:
            custody._validate('Range',[5,2])
        assert error.value.code=='bvbrc_appservice_custody_range_conflict'
        assert error.value.diagnostics==[{'code':error.value.code,'path':''}]
