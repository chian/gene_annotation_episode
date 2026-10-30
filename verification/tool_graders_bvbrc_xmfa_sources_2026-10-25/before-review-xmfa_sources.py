"""Bind retained native XMFA members to explicitly supplied staged inputs.

The file/entry relation and original-coordinate maps are evidence, not guessed
from labels or taxa. Pure functions below never open their recorded paths.
"""
from copy import deepcopy
import hashlib
import json
import re

from . import xmfa_source_contracts as c
from .bvbrc_alignment_values import diagnostic, requirement

_COMPLEMENT = str.maketrans('ACGTRYSWKMBDHVNacgtryswkmbdhvn',
                          'TGCAYRSWMKVHDBNtgcayrswmkvhdbn')


def _positive(number):
    if (number is not None and number['state']=='available'
            and type(number['value']) is int and number['value']>0
            and re.fullmatch(r'[0-9]+',number['raw_token'].strip()) is not None):
        return number['value']
    return None


def _native_members(document):
    values=[]
    for meta in document['metadata']:
        number=_positive(meta['member_number'])
        if number is not None and number not in values:
            values.append(number)
    for block in document['blocks']:
        for row in block['records']:
            number=_positive(row['member_number'])
            if number is not None and number not in values:
                values.append(number)
    return values


def _unique_evidence(*groups):
    result=[]
    for group in groups:
        for item in group:
            if item not in result:
                result.append(deepcopy(item))
    return result


def _add_issue(result, scope, reason, *, kind='scientific_metadata',role='xmfa_input_binding'):
    code='xmfa_'+reason
    key=hashlib.sha256(json.dumps([result['document_id'],scope,code],separators=(',',':')).encode()).hexdigest()
    item=requirement('xmfa_source:'+key,kind=kind,role=role,reason_code=code)
    if item not in result['requirements']:
        result['requirements'].append(item)
    result['diagnostics'].append(diagnostic(code,path=scope))


def _bind_member(number, document, inputs, result):
    metadata=[m for m in document['metadata'] if _positive(m['member_number'])==number]
    fields={kind:[m for m in metadata if m['kind']==kind]
            for kind in ('sequence_file','sequence_entry','sequence_format')}
    names=list(dict.fromkeys(m['value_token'] for m in fields['sequence_file']))
    formats=list(dict.fromkeys(m['value_token'] for m in fields['sequence_format']))
    entries=list(dict.fromkeys(_positive(m['integer_value']) for m in fields['sequence_entry']))
    member={'member_number':number,'metadata_indices':[m['metadata_index'] for m in metadata],
        'state':'missing','file_id':None,'native_file_token':names[0] if len(names)==1 else None,
        'entry_1based':entries[0] if len(entries)==1 else None,'source_length':None,
        'source_sequence':None,'components':[],'evidence':[]}
    scope='/members/'+str(number)
    if len(names)>1 or len(formats)>1 or len(entries)>1 or None in entries:
        member['state']='conflicting'; _add_issue(result,scope,'source_binding_conflict')
        return member
    if not names:
        _add_issue(result,scope,'source_binding_missing'); return member
    invocation=inputs['invocation']; mode=invocation['mode']
    if mode=='unknown' or not invocation['evidence']:
        _add_issue(result,scope,'invocation_mode_missing'); return member
    if document['format_version_token']!='Mauve1':
        _add_issue(result,scope,'version_missing' if document['format_version_token'] is None else 'version_unsupported')
        return member
    candidates=[f for f in inputs['files'] if f['native_path_token']==names[0]]
    if len(candidates)!=1:
        if candidates:
            member['state']='conflicting'
        _add_issue(result,scope,'source_binding_conflict' if candidates else 'source_binding_missing',
                   kind='scientific_metadata' if candidates else 'input_bytes',
                   role='xmfa_input_binding' if candidates else 'xmfa_staged_input')
        return member
    file=candidates[0]
    member['file_id']=file['file_id']
    member['evidence']=_unique_evidence(invocation['evidence'],file['path_binding_evidence'])
    if formats and formats[0]!=file['format']:
        member['state']='conflicting'; _add_issue(result,scope,'source_binding_conflict'); return member
    if not file['path_binding_evidence']:
        _add_issue(result,scope,'source_binding_missing'); return member
    ordered=invocation['ordered_file_ids']
    if mode=='single_file_entries':
        if len(ordered)!=1 or ordered[0]!=file['file_id']:
            member['state']='conflicting'; _add_issue(result,scope,'source_binding_conflict'); return member
        if not entries:
            _add_issue(result,scope,'source_binding_missing'); return member
        records=[r for r in file['records'] if r['entry_1based']==entries[0]]
    else:
        member['entry_1based']=None
        if number>len(ordered) or ordered[number-1]!=file['file_id'] or entries and entries[0]!=number:
            member['state']='conflicting'; _add_issue(result,scope,'source_binding_conflict'); return member
        records=file['records']
    if file['record_completeness']!='complete' or not records:
        _add_issue(result,scope,'input_population_partial',kind='input_metadata',role='xmfa_input_records')
        return member
    member['state']='resolved'
    member['source_sequence']=''.join(r['sequence'] for r in records)
    member['source_length']=len(member['source_sequence'])
    cursor=0
    for record in records:
        end=cursor+len(record['sequence'])
        member['components'].append({'file_id':file['file_id'],'record_id':record['record_id'],
            'entry_1based':record['entry_1based'],'member_interval_0based_half_open':[cursor,end],
            'record_length':len(record['sequence']),'evidence':deepcopy(member['evidence'])})
        cursor=end
    return member


def _check_record(block, record, member):
    check={'record':{'block_index':block['block_index'],'record_index':record['record_index']},
        'member_number':_positive(record['member_number']),'state':'not_checked',
        'compared_bases':0,'mismatch_columns_0based':[],
        'evidence':deepcopy(member['evidence']) if member is not None else []}
    if record['coordinate_state']=='absent_zero':
        check['state']='absent_zero'
        return check,None
    if record['coordinate_state']!='present' or record['sequence_state']!='dna_iupac':
        return check,'coordinate_invalid'
    if member is None or member['state']!='resolved':
        return check,None
    start,end=record['interval_0based_half_open']
    if end>member['source_length']:
        return check,'source_span_outside_input'
    expected=member['source_sequence'][start:end]
    if record['strand']=='-':
        expected=expected.translate(_COMPLEMENT)[::-1]
    observed=[(i,ch) for i,ch in enumerate(record['sequence']) if ch!='-']
    # Both lengths must already agree with the complete native span.
    c.require(len(observed)==len(expected), 'source_check_span_conflict')
    check['compared_bases']=len(observed)
    check['mismatch_columns_0based']=[column for (column,ch),base in zip(observed,expected)
                                    if ch.upper()!=base.upper()]
    check['state']='mismatch' if check['mismatch_columns_0based'] else 'match'
    return check,'source_sequence_mismatch' if check['state']=='mismatch' else None


def _original_map_conflicts(maps):
    conflicts=[]
    for i,a in enumerate(maps):
        for j in range(i):
            b=maps[j]
            if a['original_member']!=b['original_member']:
                continue
            if a['original_length']!=b['original_length']:
                conflicts.append((j,i)); continue
            if (a['file_id'],a['record_id'])!=(b['file_id'],b['record_id']):
                continue
            start=max(a['staged_interval_0based_half_open'][0],b['staged_interval_0based_half_open'][0])
            end=min(a['staged_interval_0based_half_open'][1],b['staged_interval_0based_half_open'][1])
            if start>=end:
                continue
            def mapped(mapping,p):
                x,y=mapping['original_interval_0based_half_open']
                offset=p-mapping['staged_interval_0based_half_open'][0]
                return x+offset if mapping['strand']=='+' else y-1-offset
            if a['strand']!=b['strand'] or any(mapped(a,p)!=mapped(b,p) for p in (start,end-1)):
                conflicts.append((j,i))
    return conflicts


def _registry_complete(document, inputs, members):
    invocation=inputs['invocation']; files={f['file_id']:f for f in inputs['files']}
    ordered=invocation['ordered_file_ids']
    if invocation['mode']=='unknown' or not invocation['evidence'] or not ordered or not members:
        return False
    if any(f not in files or files[f]['record_completeness']!='complete' for f in ordered):
        return False
    if any(m['state']!='resolved' for m in members):
        return False
    if invocation['mode']=='single_file_entries':
        expected=len(files[ordered[0]]['records'])
        if sorted(m['entry_1based'] for m in members)!=list(range(1,expected+1)):
            return False
    else:
        expected=len(ordered)
    return set(m['member_number'] for m in members)==set(range(1,expected+1))


def bind_xmfa_sources(document: dict, *, inputs: dict,
                      source_comparison: str) -> dict:
    from .xmfa_format_contracts import validate_xmfa_document
    document=validate_xmfa_document(document)
    inputs=c.validate_xmfa_source_inputs(inputs)
    c.require(source_comparison=='case_insensitive_iupac_exact', 'source_comparison_invalid')
    result={'schema_version':'mauve_xmfa_source_bindings_v1','document_id':document['document_id'],
        'status':'ok','invocation_mode':inputs['invocation']['mode'],
        'member_registry_completeness':'unknown','members':[],'source_checks':[],
        'original_maps':deepcopy(inputs['original_maps']),'requirements':[],'diagnostics':[]}
    result['members']=[_bind_member(n,document,inputs,result) for n in _native_members(document)]
    members={m['member_number']:m for m in result['members']}
    for block in document['blocks']:
        for record in block['records']:
            check,issue=_check_record(block,record,members.get(_positive(record['member_number'])))
            result['source_checks'].append(check)
            if issue:
                _add_issue(result,f"/blocks/{block['block_index']}/records/{record['record_index']}",issue)
    complete=_registry_complete(document,inputs,result['members'])
    result['member_registry_completeness']='complete' if complete else 'partial' if result['members'] else 'unknown'
    if not complete:
        _add_issue(result,'/members','input_population_partial',kind='input_metadata',role='xmfa_input_records')
    for first,second in _original_map_conflicts(result['original_maps']):
        _add_issue(result,f'/original_maps/{second}','original_map_conflict',role='xmfa_original_map')
    for index,mapping in enumerate(result['original_maps']):
        if not mapping['evidence']:
            _add_issue(result,f'/original_maps/{index}','original_map_missing',role='xmfa_original_map')
    if result['requirements']:
        result['status']='partial'
    return c.validate_xmfa_source_bindings(result)


def validate_xmfa_bindings_for_document(document: dict, bindings: dict) -> dict:
    """Validate saved identities/checks against the actual supplied native rows."""
    from .xmfa_format_contracts import validate_xmfa_document
    document=validate_xmfa_document(document)
    bindings=c.validate_xmfa_source_bindings(bindings)
    c.require(bindings['document_id']==document['document_id'], 'source_document_conflict')
    numbers=_native_members(document)
    c.require([m['member_number'] for m in bindings['members']]==numbers, 'source_member_population_conflict')
    members={m['member_number']:m for m in bindings['members']}
    for member in bindings['members']:
        expected=[m['metadata_index'] for m in document['metadata'] if _positive(m['member_number'])==member['member_number']]
        c.require(member['metadata_indices']==expected, 'source_metadata_association_conflict')
        metadata=[document['metadata'][i] for i in expected]
        names={m['value_token'] for m in metadata if m['kind']=='sequence_file'}
        if member['state']=='resolved':
            c.require(names=={member['native_file_token']}, 'source_file_token_conflict')
            entries={_positive(m['integer_value']) for m in metadata if m['kind']=='sequence_entry'}
            if bindings['invocation_mode']=='single_file_entries':
                c.require(entries=={member['entry_1based']}, 'source_entry_conflict')
    expected=[]
    for block in document['blocks']:
        for record in block['records']:
            check,_=_check_record(block,record,members.get(_positive(record['member_number'])))
            expected.append(check)
    c.require(bindings['source_checks']==expected, 'source_checks_conflict')
    return bindings


__all__=['bind_xmfa_sources','validate_xmfa_bindings_for_document']
