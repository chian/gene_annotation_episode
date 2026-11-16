"""Focused real caller/owner paths for the six composed-source audit gaps.

Pure metadata validation only. No native worker or scientific calculation is
started. The one receipt case uses an uninitialized owner and rejects its
invalid plan before Store/context access, explicitly isolating import routing.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.root.a110 import bvbrc_appservice_custody as custody
from gene_annotation_episode.episodic_workflow.root.a110 import genomic_overlap_result_receipts as receipts
from gene_annotation_episode.episodic_workflow.root.a110 import molecular_sequence_ordinary as ordinary
from gene_annotation_episode.episodic_workflow.root.a110 import terminal_scientific_evidence as terminal
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information import historical_native_genomic_overlap_contracts as genomic
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import molecular_sequence_native as native


def test_original_custody_reference_formats_preserve_namespace_and_context():
    value={'operand':'artifact_123','context':'descriptive only','identifiers':['external-1','external-2']}
    schema={'properties':{
        'operand':{'format':'reference','x-reference-namespace':'artifact'},
        'context':{'format':'text'},
        'identifiers':{'items':{'format':'identifier','x-reference-namespace':'original_subject'}}}}
    assert list(custody._references(value,schema))==[
        ('artifact_123','artifact'),('external-1','original_subject'),('external-2','original_subject')]
    assert value['context']=='descriptive only'


def deployment(operation):
    glyco=operation=='find_n_glycosylation_motifs'
    manifest='b'*64
    return {'version':'molecular_sequence_deployment_v2' if glyco else 'molecular_sequence_deployment_v1',
        'runtime':{'executable':{'path':'/retained/python','sha256':'a'*64,'size_bytes':1},'home':'/retained'},
        'module':{'path':'/retained/native_source.py','sha256':'c'*64,'size_bytes':1},
        'import_roots':['/retained/library'],
        'software_files_ref':'artifact_'+manifest,
        'software_files_file':{'path':'/retained/manifest.json','sha256':manifest,'size_bytes':1}}


@pytest.mark.parametrize('operation',['annotate_open_reading_frames','find_n_glycosylation_motifs'])
def test_ordinary_path_reaches_original_deployment_validator(operation):
    value=deployment(operation)
    before=deepcopy(value)
    assert ordinary._deployment(operation,value) is None
    assert value==before


@pytest.mark.parametrize('mutation,code',[
    ('roots','molecular_sequence_ordered_import_roots_required'),
    ('manifest','molecular_sequence_manifest_artifact_identity_mismatch'),
])
def test_ordinary_deployment_keeps_native_failure_identity(mutation,code):
    value=deployment('annotate_open_reading_frames')
    if mutation=='roots':
        value['import_roots']*=2
    else:
        value['software_files_ref']='artifact_'+'c'*64
    before=deepcopy(value)
    with pytest.raises(native._BoundaryError) as error:
        ordinary._deployment('annotate_open_reading_frames',value)
    assert error.value.code==code
    assert value==before


@pytest.mark.parametrize('method',['_operand','_native_arguments','_scientific_context'])
def test_ordinary_primer_routes_retain_invalid_operand_outcome(method):
    with pytest.raises(ValueError):
        if method=='_operand':
            ordinary._operand({}, {}, operation='align_sequences')
        else:
            getattr(ordinary,method)('align_sequences',{}, {})


def test_genomic_native_receipt_reaches_same_plan_validation_failure(monkeypatch):
    monkeypatch.setattr(terminal,'is_terminal_target',lambda value:False)
    with pytest.raises(ValueError) as expected:
        genomic.validate_genomic_overlap_run_plan({})
    value=dict.fromkeys(receipts.GenomicOverlapNativeSnapshot.__annotations__)
    value['original_plan']={}
    before=deepcopy(value)
    owner=object.__new__(receipts.GenomicOverlapResultReceipts)
    with pytest.raises(type(expected.value)) as actual:
        owner.validate_native(value,{'target':{}},{})
    assert str(actual.value)==str(expected.value)
    assert value==before
