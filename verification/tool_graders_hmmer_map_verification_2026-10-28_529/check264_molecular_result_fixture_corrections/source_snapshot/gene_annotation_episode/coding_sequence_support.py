"""Selected native CDS geometry and the existing extraction sheet authority.

This supplies explicit transformation requests and reads supplied results. It
does not acquire records, run Bio, select candidates or assign target functions.
"""
from copy import deepcopy
import json

from .sequence_extraction_grader import grade_extraction


def _require(condition, code):
    if not condition:
        raise ValueError('coding_sequence_' + code)


def _copy(value):
    def check(node):
        if node is None or type(node) in (str,int,bool):return
        if type(node) is float:
            import math
            if math.isfinite(node):return
        if type(node) is list:
            for child in node:check(child)
            return
        if type(node) is dict and all(type(k) is str for k in node):
            for child in node.values():check(child)
            return
        raise ValueError('coding_sequence_finite_json_required')
    try:check(value)
    except RecursionError as error:raise ValueError('coding_sequence_finite_json_required') from error
    return deepcopy(value)


def _same(left,right):
    return json.dumps(left,sort_keys=True,allow_nan=False)==json.dumps(right,sort_keys=True,allow_nan=False)


def plan_coding_sequence_extractions(records, *, selection, source_ref, molecule_model):
    records,selection=_copy(records),_copy(selection)
    _require(type(source_ref) is str and bool(source_ref),'source_required')
    _require(molecule_model in ('dna','rna'),'molecule_model_required')
    _require(type(records) is list and all(type(r) is dict for r in records),'records_required')
    _require(type(selection) is list,'explicit_selection_required')
    by_record={}
    for record in records:
        index=record.get('source_record_index')
        _require(type(index) is int and index>=0 and index not in by_record,'record_identity_conflict')
        by_record[index]=record
    rows=[]
    for ordinal,chosen in enumerate(selection):
        _require(type(chosen) is dict and set(chosen)=={'record_ordinal','feature_ordinal','subject_ref','parent_mapping'},'selection_fields_required')
        _require(all(type(chosen[k]) is int and chosen[k]>=0 for k in ('record_ordinal','feature_ordinal')),
            'selection_ordinals_required')
        _require(type(chosen['subject_ref']) is str and bool(chosen['subject_ref']),'subject_required')
        _require(chosen['parent_mapping'] is None or type(chosen['parent_mapping']) is dict,'parent_mapping_required')
        record=by_record.get(chosen['record_ordinal'])
        row={'selection_ordinal':ordinal,**chosen,'record_metadata':None,'source_feature':None,
            'input_sequence':None,'effective_request':None,'native_part_order':[],
            'geometry_basis':'unavailable','status':'unavailable','issue_codes':[]}
        rows.append(row)
        if record is None:
            row['issue_codes'].append('selected_record_unavailable');continue
        row['record_metadata']={k:v for k,v in record.items() if k not in ('sequence','features','unlocated_features')}
        row['input_sequence']=record.get('sequence')
        features={}
        _require(all(type(record.get(k,[])) is list for k in ('features','unlocated_features')),'feature_rows_required')
        for feature in [*record.get('features',[]),*record.get('unlocated_features',[])]:
            _require(type(feature) is dict,'feature_rows_required')
            index=feature.get('source_feature_index')
            _require(type(index) is int and index>=0 and index not in features,'feature_identity_conflict')
            features[index]=feature
        feature=features.get(chosen['feature_ordinal'])
        row['source_feature']=feature
        if feature is None:
            row['issue_codes'].append('selected_feature_unavailable');continue
        if feature.get('kind')!='CDS':
            row['issue_codes'].append('selected_feature_not_cds');continue
        sequence=row['input_sequence']
        if type(sequence) is not str or not sequence:
            row['issue_codes'].append('source_sequence_unavailable');continue
        parts=feature.get('segments')
        if type(parts) is not list or not parts:
            row['issue_codes'].append('source_location_unavailable');continue
        _require(all(type(part) is dict for part in parts),'location_parts_required')
        row['native_part_order']=list(range(len(parts)))
        if any(p.get('ref') is not None or p.get('ref_db') is not None for p in parts):
            row['issue_codes'].append('remote_sequence_operand_required');continue
        if any(type(p.get('start')) is not int or type(p.get('end')) is not int
                or not 0<=p['start']<p['end']<=len(sequence) for p in parts):
            row['issue_codes'].append('source_bounds_unavailable_or_outside_sequence');continue
        orientations={'reverse_complement' if p.get('strand')=='-' else 'as_is' for p in parts}
        if len(orientations)!=1:
            row['issue_codes'].append('mixed_orientation_requires_shared_view_extension');continue
        orientation=orientations.pop()
        if any(p.get('strand') not in ('+','-') for p in parts):
            row['issue_codes'].append('source_strand_unknown_as_is')
        fuzzy=any(p.get(k)!='ExactPosition' for p in parts for k in ('start_kind','end_kind'))
        if fuzzy:row['issue_codes'].append('nominal_fuzzy_coordinates')
        if feature.get('operator')=='order':row['issue_codes'].append('native_order_location')
        segments=[{'start':p['start'],'end':p['end']} for p in parts]
        if orientation=='reverse_complement':segments.reverse()
        row.update(status='ready',geometry_basis='nominal_fuzzy' if fuzzy else 'exact',
            effective_request={'molecule':molecule_model,'segments':segments,'orientation':orientation})
    return {'version':'coding_sequence_plan_v1','source_ref':source_ref,'molecule_model':molecule_model,
        'records':records,'selection':selection,'rows':deepcopy(rows)}


def _validated_plan(plan):
    plan=_copy(plan)
    _require(type(plan) is dict and set(plan)=={'version','source_ref','molecule_model','records','selection','rows'}
        and plan['version']=='coding_sequence_plan_v1','plan_required')
    expected=plan_coding_sequence_extractions(plan['records'],selection=plan['selection'],
        source_ref=plan['source_ref'],molecule_model=plan['molecule_model'])
    _require(_same(plan,expected),'plan_source_binding_conflict')
    return plan


def read_coding_sequence_results(plan, *, extracted):
    plan=_validated_plan(plan)
    extracted=_copy(extracted)
    _require(type(extracted) is list,'results_required')
    by_ordinal={}
    for result in extracted:
        _require(type(result) is dict and set(result)=={'selection_ordinal','native_result','failure_code'},'result_fields_required')
        index=result['selection_ordinal']
        _require(type(index) is int and 0<=index<len(plan['rows']) and index not in by_ordinal,'result_identity_conflict')
        _require(result['failure_code'] is None or type(result['failure_code']) is str and bool(result['failure_code']),'failure_code_required')
        _require(result['native_result'] is None or type(result['native_result']) is dict,'native_result_required')
        _require(result['native_result'] is None or result['failure_code'] is None,'result_failure_conflict')
        by_ordinal[index]=result
    rows=[]
    for selected in plan['rows']:
        result=by_ordinal.get(selected['selection_ordinal'])
        row={**deepcopy(selected),'extraction_status':'unavailable' if selected['status']=='unavailable' else 'not_started',
            'sequence':None,'native_result':None,'grading':None}
        rows.append(row)
        if selected['status']=='unavailable':
            _require(result is None or result['native_result'] is None,'unavailable_plan_has_native_result')
            continue
        if result is None:continue
        if result['native_result'] is None:
            row['extraction_status']='failed' if result['failure_code'] is not None else 'not_started'
            if result['failure_code']:row['issue_codes'].append(result['failure_code'])
            continue
        native=result['native_result']
        row['native_result']=native
        row['sequence']=native.get('sequence') if type(native.get('sequence')) is str else None
        try:
            row['grading']=grade_extraction(native,input_sequence=selected['input_sequence'],
                subject_ref=selected['subject_ref'],parent_mapping=selected['parent_mapping'],
                request=selected['effective_request'])
        except ValueError as error:
            row['issue_codes'].append(str(error))
            row['extraction_status']='failed'
            continue
        row['extraction_status']=('completed' if row['grading']['scores']['status']=='complete'
            and not row['issue_codes'] else 'partial')
    return {'version':'coding_sequence_results_v1','source_ref':plan['source_ref'],'plan':plan,'rows':rows,
        'population_scope':'explicit_selected_source_features_only',
        'status':'complete' if all(r['extraction_status']=='completed' for r in rows) else 'partial'}


__all__=['plan_coding_sequence_extractions','read_coding_sequence_results']
