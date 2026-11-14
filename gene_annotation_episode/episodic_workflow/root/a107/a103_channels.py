"""Native STRING context channels with exact response and endpoint custody."""
from __future__ import annotations

import json

from .a103_publication import publish
from .a103_scoring import digest, require
from .molecular_provider_acquisition import VALUE_VERSION, validate_provider_value, provider_receipt


CHANNELS = {'nscore':'neighborhood','fscore':'fusion','pscore':'phylogenetic_profile'}


def native_endpoint_binding(store,reference,native_id,known):
    """An identifier label alone cannot establish the actual protein sequence."""
    if reference not in known:
        return False
    row = store.get(reference)
    if not row.get('sequence_ref'):
        return False
    sequence = store.get_artifact(row['sequence_ref']).decode('ascii').strip().upper()
    sources = set(known)
    if row.get('source_ref') in known:sources.add(row['source_ref'])
    for ref in sources:
        source = store.get(ref)
        if source['record_type']!='source' or source.get('provider') not in {'uniprot','public.uniprot.record','retained.uniprot'}:
            continue
        try:
            value = json.loads(store.get_artifact(source['artifact_ref']))
        except (ValueError,UnicodeError):
            continue
        records = value.get('results',[value]) if isinstance(value,dict) else []
        for record in records:
            if record.get('sequence',{}).get('value','').upper()!=sequence:
                continue
            if any(r.get('database')=='STRING' and r.get('id')==native_id for r in record.get('uniProtKBCrossReferences',[])):
                return True
    return False


def publish_channels(store,args):
    source = store.get(args['source_ref'])
    require(source.get('provider')=='string' and source['origin']=='external','a103_actual_string_acquisition_required')
    candidates = []
    for ref in source.get('auxiliary_artifact_refs',[]):
        try:
            body = json.loads(store.get_artifact(ref))
        except (ValueError,UnicodeError):
            continue
        if body.get('version')==VALUE_VERSION and body.get('operation')=='public.string.network':
            candidates.append(validate_provider_value(body))
    require(len(candidates)==1,'a103_string_native_capture_required')
    value = candidates[0]
    receipt = provider_receipt(value,source_ref=args['source_ref'])
    require(receipt['acquired'] and value['raw_artifact_ref']==source['artifact_ref'],
            'a103_complete_string_capture_required')
    actual = json.loads(store.get_artifact(source['artifact_ref']))
    require(actual==value['native_json'],'a103_string_native_payload_conflict')
    pair = {args['left_native_id'],args['right_native_id']}
    require(len(pair)==2 and pair<=set(value['requested']['string_ids']),'a103_string_endpoint_request_conflict')
    rows = [r for r in actual if {r['stringId_A'],r['stringId_B']}==pair]
    require(rows,'a103_no_native_context_edge; missing_edges_do_not_establish_absence')
    results,refs = [],[]
    for field,channel in CHANNELS.items():
        numbers = {r[field] for r in rows if field in r}
        if not numbers:continue
        require(len(numbers)==1,'a103_conflicting_native_channel_rows')
        number = next(iter(numbers))
        require(type(number) in {int,float} and 0<=number<=1,'a103_native_channel_scale_invalid')
        body = {'schema':'a103_channel_v1','producer_operation':'context.association_channels',
            **args,'channel':channel,'native_field':field,'native_value':number,
            'native_unit':'STRING_channel_0_to_1','native_taxon_id':value['requested']['taxon_id'],
            'native_request_url':value['response']['request_url'],
            'actual_measured_subjects':[args['left_native_id'],args['right_native_id']],
            'comparison_group':digest([args['target_ref'],sorted(pair),field]),
            'comparison_variant':digest([source['artifact_ref'],value['response']['request_url'],field]),
            'interpretation':'one_native_context_channel; combined_score_and_other_axes_excluded'}
        ref = publish(store,body,[args['target_ref'],args['left_reference_ref'],args['right_actual_ref'],args['right_reference_ref']])
        refs.append(ref); results.append({'measurement_ref':ref,'channel':channel,'native_field':field,'raw_value':number})
    require(refs,'a103_no_native_context_channels')
    return {'channels':results,'combined_score_used':False},refs
