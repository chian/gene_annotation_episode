"""Closed supplied-input/source-binding values for native DNA XMFA.

These validators check stored values. Host custody of source bytes remains a
separate responsibility; no path is opened and no sequence is retrieved here.
"""
from copy import deepcopy
import re

from . import phylogeny_calculation_contracts as shared
from .phylogeny_format_contracts import _artifact, _location
from .bvbrc_alignment_values import diagnostic, requirement

MODES = ('single_file_entries', 'multiple_files_concatenated', 'unknown')
DNA = re.compile(r'[ACGTRYSWKMBDHVNacgtryswkmbdhvn]*\Z')


def require(value, code):
    if not value:
        raise ValueError('xmfa_' + code)


def shape(value, fields):
    require(type(value) is dict and set(value) == set(fields), 'source_shape_invalid')


def text(value, *, empty=False, nullable=False):
    require(nullable and value is None or type(value) is str and (empty or bool(value)),
            'source_text_invalid')


def integer(value, *, minimum=0, nullable=False):
    require(nullable and value is None or type(value) is int and value >= minimum,
            'source_integer_invalid')


def array(value):
    require(type(value) is list, 'source_array_invalid')


def interval(value):
    require(type(value) is list and len(value) == 2, 'source_interval_invalid')
    for item in value:
        integer(item)
    require(value[0] <= value[1], 'source_interval_reversed')


def evidence(value):
    try:
        shared.evidence(value)
    except ValueError as error:
        raise ValueError('xmfa_source_evidence_invalid') from error


def occurrence(value):
    shape(value, {'input_binding_id','member_id','occurrence_index'})
    text(value['input_binding_id']); text(value['member_id']); integer(value['occurrence_index'])


def reports(value):
    array(value['requirements']); array(value['diagnostics'])
    for row in value['requirements']:
        shape(row, {'requirement_id','kind','role','source_refs','reason_code'})
        try:
            require(requirement(**row) == row, 'source_requirement_invalid')
        except ValueError as error:
            raise ValueError('xmfa_source_requirement_invalid') from error
    for row in value['diagnostics']:
        shape(row, {'code','phase','path','severity','evidence_refs'})
        try:
            require(diagnostic(**row) == row, 'source_diagnostic_invalid')
        except ValueError as error:
            raise ValueError('xmfa_source_diagnostic_invalid') from error


def validate_xmfa_original_map(value):
    shape(value, {'file_id','record_id','staged_interval_0based_half_open',
        'original_member','original_length','original_interval_0based_half_open',
        'strand','transformation_id','evidence'})
    for field in ('file_id','record_id','transformation_id'):
        text(value[field])
    occurrence(value['original_member']); integer(value['original_length'])
    interval(value['staged_interval_0based_half_open'])
    interval(value['original_interval_0based_half_open'])
    a,b = value['staged_interval_0based_half_open']
    x,y = value['original_interval_0based_half_open']
    require(b-a == y-x and y <= value['original_length'], 'original_map_interval_conflict')
    require(value['strand'] in ('+','-'), 'original_map_strand_invalid')
    evidence(value['evidence'])
    return deepcopy(value)


def validate_xmfa_source_inputs(value):
    shape(value, {'schema_version','invocation','files','original_maps'})
    require(value['schema_version']=='mauve_xmfa_source_inputs_v1', 'source_version_invalid')
    invocation=value['invocation']
    shape(invocation, {'mode','ordered_file_ids','evidence'})
    require(invocation['mode'] in MODES, 'invocation_mode_invalid')
    array(invocation['ordered_file_ids'])
    for file_id in invocation['ordered_file_ids']:
        text(file_id)
    evidence(invocation['evidence'])
    array(value['files']); array(value['original_maps'])
    files={}
    for file in value['files']:
        shape(file, {'file_id','native_path_token','artifact','format',
            'record_completeness','path_binding_evidence','records'})
        text(file['file_id']); text(file['native_path_token'],empty=True)
        require(file['file_id'] not in files, 'source_file_id_duplicate')
        files[file['file_id']]=file
        try:
            _artifact(file['artifact'])
        except ValueError as error:
            raise ValueError('xmfa_source_artifact_invalid') from error
        require(file['format'] in ('FastA','GenBank','raw','DNAstar'), 'source_format_invalid')
        require(file['record_completeness'] in shared.COMPLETENESS, 'source_completeness_invalid')
        evidence(file['path_binding_evidence']); array(file['records'])
        ids,entries=[],[]
        for record in file['records']:
            shape(record, {'record_id','entry_1based','header','sequence','source_location'})
            text(record['record_id']); integer(record['entry_1based'],minimum=1)
            text(record['header'],empty=True,nullable=True)
            text(record['sequence'],empty=True)
            require(DNA.fullmatch(record['sequence']) is not None, 'source_sequence_symbol_invalid')
            try:
                _location(record['source_location'],artifact=file['artifact'])
            except ValueError as error:
                raise ValueError('xmfa_source_location_invalid') from error
            ids.append(record['record_id']); entries.append(record['entry_1based'])
        require(len(ids)==len(set(ids)) and len(entries)==len(set(entries)), 'source_record_duplicate')
        require(entries==sorted(entries), 'source_entry_order_conflict')
        if file['record_completeness']=='complete':
            require(entries==list(range(1,len(entries)+1)), 'source_entry_population_conflict')
    for mapping in value['original_maps']:
        validate_xmfa_original_map(mapping)
        require(mapping['file_id'] in files, 'original_map_file_unknown')
        records={r['record_id']:r for r in files[mapping['file_id']]['records']}
        require(mapping['record_id'] in records, 'original_map_record_unknown')
        require(mapping['staged_interval_0based_half_open'][1] <= len(records[mapping['record_id']]['sequence']),
                'original_map_outside_source')
    return deepcopy(value)


def validate_xmfa_source_bindings(value):
    shape(value, {'schema_version','document_id','status','invocation_mode',
        'member_registry_completeness','members','source_checks','original_maps',
        'requirements','diagnostics'})
    require(value['schema_version']=='mauve_xmfa_source_bindings_v1', 'source_version_invalid')
    text(value['document_id'])
    require(value['status'] in ('ok','partial','invalid') and value['invocation_mode'] in MODES,
            'source_status_invalid')
    require(value['member_registry_completeness'] in shared.COMPLETENESS, 'source_completeness_invalid')
    array(value['members']); array(value['source_checks']); array(value['original_maps'])
    numbers=[]
    component_contents={}
    for member in value['members']:
        shape(member, {'member_number','metadata_indices','state','file_id','native_file_token',
            'entry_1based','source_length','source_sequence','components','evidence'})
        integer(member['member_number'],minimum=1); numbers.append(member['member_number'])
        array(member['metadata_indices'])
        for index in member['metadata_indices']: integer(index)
        require(len(member['metadata_indices'])==len(set(member['metadata_indices'])), 'source_metadata_index_duplicate')
        require(member['state'] in ('resolved','missing','conflicting'), 'source_member_state_invalid')
        text(member['file_id'],nullable=True); text(member['native_file_token'],empty=True,nullable=True)
        integer(member['entry_1based'],minimum=1,nullable=True)
        integer(member['source_length'],nullable=True)
        text(member['source_sequence'],empty=True,nullable=True)
        evidence(member['evidence']); array(member['components'])
        cursor=0; component_keys=[]
        for component in member['components']:
            shape(component, {'file_id','record_id','entry_1based',
                'member_interval_0based_half_open','record_length','evidence'})
            text(component['file_id']); text(component['record_id'])
            integer(component['entry_1based'],minimum=1); integer(component['record_length'])
            interval(component['member_interval_0based_half_open']); evidence(component['evidence'])
            start,end=component['member_interval_0based_half_open']
            require(start==cursor and end-start==component['record_length'], 'source_components_partition_conflict')
            require(component['file_id']==member['file_id'], 'source_component_file_conflict')
            cursor=end; component_keys.append((component['record_id'],component['entry_1based']))
        require(len(component_keys)==len(set(component_keys)), 'source_component_duplicate')
        if member['state']=='resolved':
            require(member['file_id'] is not None and member['native_file_token'] is not None
                and member['source_sequence'] is not None and member['source_length'] is not None,
                'resolved_source_missing')
            require(DNA.fullmatch(member['source_sequence']) is not None, 'source_sequence_symbol_invalid')
            require(cursor==member['source_length']==len(member['source_sequence']), 'source_length_conflict')
            require(bool(member['components']) and bool(member['evidence']), 'resolved_source_evidence_missing')
            for component in member['components']:
                key=(component['file_id'],component['record_id'])
                start,end=component['member_interval_0based_half_open']
                actual=(component['entry_1based'],member['source_sequence'][start:end])
                require(key not in component_contents or component_contents[key]==actual,
                        'source_component_content_conflict')
                component_contents[key]=actual
            if value['invocation_mode']=='single_file_entries':
                require(len(member['components'])==1 and member['entry_1based']==member['components'][0]['entry_1based'],
                        'source_entry_conflict')
            elif value['invocation_mode']=='multiple_files_concatenated':
                require(member['entry_1based'] is None, 'source_entry_conflict')
                require([c['entry_1based'] for c in member['components']]==list(range(1,len(member['components'])+1)),
                        'source_entry_population_conflict')
            else:
                require(False, 'resolved_source_invocation_unknown')
        else:
            require(member['source_sequence'] is None and member['source_length'] is None
                and not member['components'], 'unresolved_source_values_present')
    require(len(numbers)==len(set(numbers)), 'source_member_duplicate')
    if value['member_registry_completeness']=='complete':
        require(value['invocation_mode']!='unknown' and all(m['state']=='resolved' for m in value['members']),
                'source_registry_completeness_conflict')
    seen=set()
    for check in value['source_checks']:
        shape(check, {'record','member_number','state','compared_bases','mismatch_columns_0based','evidence'})
        shape(check['record'], {'block_index','record_index'})
        for index in check['record'].values(): integer(index)
        key=tuple(check['record'][k] for k in ('block_index','record_index'))
        require(key not in seen, 'source_check_duplicate'); seen.add(key)
        integer(check['member_number'],minimum=1,nullable=True)
        require(check['member_number'] is None or check['member_number'] in numbers, 'source_check_member_unknown')
        require(check['state'] in ('match','mismatch','not_checked','absent_zero'), 'source_check_state_invalid')
        integer(check['compared_bases']); array(check['mismatch_columns_0based'])
        for index in check['mismatch_columns_0based']: integer(index)
        require(check['mismatch_columns_0based']==sorted(set(check['mismatch_columns_0based'])), 'source_mismatch_columns_invalid')
        require(len(check['mismatch_columns_0based'])<=check['compared_bases'], 'source_mismatch_count_conflict')
        if check['state'] in ('not_checked','absent_zero'):
            require(check['compared_bases']==0 and not check['mismatch_columns_0based'], 'source_check_count_conflict')
        elif check['state']=='match':
            require(check['compared_bases']>0 and not check['mismatch_columns_0based'], 'source_check_count_conflict')
        else:
            require(bool(check['mismatch_columns_0based']), 'source_mismatch_missing')
        evidence(check['evidence'])
    for mapping in value['original_maps']:
        validate_xmfa_original_map(mapping)
        key=(mapping['file_id'],mapping['record_id'])
        if key in component_contents:
            require(mapping['staged_interval_0based_half_open'][1] <= len(component_contents[key][1]),
                    'original_map_outside_source')
    reports(value)
    require(value['status']!='ok' or not value['requirements'], 'source_status_requirement_conflict')
    return deepcopy(value)


__all__=['validate_xmfa_source_inputs','validate_xmfa_source_bindings','validate_xmfa_original_map']
