"""Actual prospective pin and retained-publication input authentication controls.

The saved-input checks exercise the original _validate_inputs method and its real
helper chain, not a full publication Store replay or service reconstruction.
Custody callbacks are controlled ports; no scientific evidence or support is
created by these metadata-only checks.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from ..library import bvbrc_homology_bundle_adapter as adapter
from ..bvbrc_appservice_adapters import bind_adapters
from ..bvbrc_appservice_publication import AppServicePublications
from ..library.bvbrc_appservice_contracts import validate_contract
from ..practical_execution_state import _immutable, _read
from .bvbrc_controlled_saved_records import request
from .bvbrc_phylogeny_saved_fixture import selector as original_selector
from .test_bvbrc_homology_bundle_adapter import c4_fixture
from .homology_pin_publication_fixture import output_target,download_args

PROFILE=Path(__file__).parent/'fixtures/homology_original_pin_profile.json'


@pytest.mark.parametrize('dependency',('domain.py','blast_database_population_associations.py','blast_fasta_record_identity.py'))
def test_each_actual_scientific_dependency_changes_the_current_pin_and_old_config_is_rejected(monkeypatch,dependency):
    before=adapter.implementation_sha256()
    selected={'adapter_id':adapter.ADAPTER_ID,'adapter_version':adapter.ADAPTER_VERSION,'implementation_sha256':before}
    assert bind_adapters([selected])[(adapter.ADAPTER_ID,adapter.ADAPTER_VERSION)]==(adapter,before)
    original=Path.read_bytes
    def changed(path):
        content=original(path)
        return content+b'\n# controlled actual dependency byte change\n' if path.name==dependency else content
    monkeypatch.setattr(Path,'read_bytes',changed)
    assert adapter.implementation_sha256()!=before
    with pytest.raises(ValueError,match='appservice_adapter_implementation_conflict'):
        bind_adapters([selected])


@pytest.mark.parametrize('alter_configuration',(False,True))
def test_saved_publication_input_pin_uses_retained_configuration_not_current_calculator(tmp_path,monkeypatch,alter_configuration):
    profile=json.loads(PROFILE.read_bytes());saved_pin=profile['pre_extension_implementation_sha256']
    digest=hashlib.sha256()
    for row in sorted(profile['sources'],key=lambda r:r['logical_name']):
        raw=Path(row['required_source']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row['size_bytes']
        digest.update(row['logical_name'].encode()+b'\0'+str(len(raw)).encode()+b'\0'+raw)
    assert digest.hexdigest()==saved_pin
    selected={'adapter_id':'bvbrc_homology','adapter_version':'1','parameters':c4_fixture()[3]}
    adapter.validate_parameters(selected['parameters'])
    selector=original_selector();selector['adapter']=selected
    query=request();obj=output_target(query)
    arguments=download_args(obj,{'kind':'acquired','receipt_ref':'source_controlled_capability','input_index':0})
    operation='api.bvbrc_appservice.download'
    prepared={'operation':operation,'native_operands':{'request':query,'selector':selector,'arguments':arguments},'bound_inputs':{'support_receipt_refs':[]}}
    snapshot_bytes=b'{"controlled_transport":true}'
    snapshot_hash=hashlib.sha256(snapshot_bytes).hexdigest()
    binding={'source_ref':'source_controlled_snapshot','content':{'source_ref':'source_controlled_snapshot','artifact_field':'artifact_ref','artifact_ref':'artifact_'+snapshot_hash,'sha256':snapshot_hash,'byte_count':len(snapshot_bytes)},'retrieved_at':'controlled-original-stamp','media_type':'application/json','transport':{'controlled':True},'selected_operands':arguments}
    context=SimpleNamespace(run_id='controlled-run',episode_id='controlled-results',scope={},assignment={'handoff_ref':'source_controlled_handoff'})
    value={'version':'bvbrc_appservice_publication_inputs_v1','request':prepared['native_operands']['request'],'selector':selector,'original_handoff_ref':context.assignment['handoff_ref'],'current_snapshot':binding,'current_operation':{'name':operation,'arguments':arguments},'support_receipt_refs':[],'prior_acquisition_receipt_refs':[],'supplied_evidence':[],'adapter':selected,'adapter_implementation_sha256':saved_pin}
    assert validate_contract('PublicationInputs',value)==value
    path=tmp_path/'publication_inputs.json';_immutable(path,value);original_bytes=path.read_bytes();retained=_read(path)
    configured={'adapter_id':'bvbrc_homology','adapter_version':'1','implementation_sha256':'0'*64 if alter_configuration else saved_pin};calls=[]
    def possession(ctx,reference,*,before):
        assert ctx is context and reference==context.assignment['handoff_ref'] and before==1
        calls.append((reference,before))
    def forbidden(*args,**kwargs):raise AssertionError('Saved input authentication called current grading, acquisition or nonexistent evidence')
    custody=SimpleNamespace(possession=possession,evidence=forbidden,content=forbidden)
    api=SimpleNamespace(configuration={'controlled-api':{'scientific_adapters':[configured]}})
    def read_target(reference,scope):
        assert reference==context.assignment['handoff_ref'] and scope==context.scope
        return {'resource_id':'controlled-api'}
    host=SimpleNamespace(api=api,store=None,custody=custody,read_target=read_target,read_acquisition=forbidden)
    monkeypatch.setattr(adapter,'implementation_sha256',forbidden)
    monkeypatch.setattr(adapter,'consume_bundle',forbidden)
    publication=AppServicePublications(host)
    if alter_configuration:
        with pytest.raises(ValueError,match='appservice_publication_adapter_configuration_conflict'):
            publication._validate_inputs(context,prepared,binding,retained,'controlled-run:controlled-results:1')
    else:
        assert publication._validate_inputs(context,prepared,binding,retained,'controlled-run:controlled-results:1')==value
    assert calls==[(context.assignment['handoff_ref'],1)] and path.read_bytes()==original_bytes and retained==value
