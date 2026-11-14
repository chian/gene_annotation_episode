"""Original host-tracking projection preserves scientific operands and meanings."""
from copy import deepcopy

from gene_annotation_episode.episodic_workflow.root.a106.library.literature_experimental_prompt import _safe


def test_nested_tracking_does_not_hide_actual_scientific_qualification():
    value={'status':'completed','result':{'measurement_keys':{'W':'HOST_HASH'},
        'curve_keys':['HOST_CURVE'],'primitive_measurement_keys':['HOST_PRIMITIVE'],
        'source_ref':'source_original','subject_ref':'reference_original',
        'design':'cas_free_reconstitution','measurement_status':'qualitative_only',
        'cells':{'effect':{'value':None,'unit':'dimensionless','status':'unavailable',
            'origin':'proposed','unavailable_reason':'ratio_scale_not_validated'}},
        'assay_interpretation':{'recipient':{'value':'BL21-AI','witness':{'quote':'BL21-AI'}}}}}
    before=deepcopy(value)
    expected=deepcopy(value)
    for name in ('measurement_keys','curve_keys','primitive_measurement_keys'):
        del expected['result'][name]
    assert _safe(value)==expected
    assert value==before


def test_original_generated_accessions_are_distinct_from_scientific_accessions():
    for prefix in ('transport_curve_','transport_quantity_','native_rate_','amount_'):
        assert _safe({'accession':prefix+'generated','value':2.5,'unit':'mg/ml'})=={'value':2.5,'unit':'mg/ml'}
    assert _safe({'accession':'UniProt:P00000','value':2.5})=={'accession':'UniProt:P00000','value':2.5}


def test_existing_private_provider_body_filter_is_retained():
    assert _safe({'provider_result':{'raw':'PRIVATE_PROVIDER_BODY'},'private_history':['private'],
        'value':1.4,'qualification':'unknown','source_ref':'source_original'})=={
        'value':1.4,'qualification':'unknown','source_ref':'source_original'}


def test_original_nested_history_and_hashes_are_host_metadata_not_scientific_findings():
    assert _safe([{'goal_id':'HOST_GOAL','record_type':'source','implementation_sha256':'HOST_HASH',
        'restored_episode_history':{'host':'history'},'source_ref':'source_original',
        'evidence':[{'measurement_keys':['HOST'],'value':0.0,'status':'measured'}]}])==[
        {'source_ref':'source_original','evidence':[{'value':0.0,'status':'measured'}]}]
