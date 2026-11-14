"""Check saved identities and stored numerical relationships without recalculation.

No parser, builder or geometry/calculator entrypoint is called here. The pinned
producer established geometry before publication; the host authenticates that
immutable publication. These checks do not claim custody for caller dictionaries.
"""
from copy import deepcopy
from decimal import Decimal

from . import bvbrc_proteome_bundle_v2_contracts as c
from . import bvbrc_proteome_directional_numerical_contracts as n
from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_proteome_sheet_contracts import validate_proteome_sheet_data

_NUMERICAL = 'proteome_directional_saved_numerical_relationship_conflict'
_KEYS = n._KEY_FIELDS


def _require(condition, path=''):
    c._require(condition, _NUMERICAL, path)


def _same(actual, expected, path=''):
    _require(c.canonical(actual) == c.canonical(expected), path)


def _key(value):
    return tuple(value[k] for k in _KEYS if k in value)


def _unique(values, path):
    _require(len({c.canonical(v) for v in values}) == len(values), path)


def _members(bundle, selection):
    if 'requirement_id' in selection:
        return [a for a in bundle['artifacts'] if selection['requirement_id'] in a.get('requirement_ids', [])]
    return [a for a in bundle['artifacts'] if (a['source_ref'],a['raw_artifact_ref']) == (selection['source_ref'],selection['raw_artifact_ref'])]


def _bundle_binding(saved, bundle):
    selections = [('native_document', i, s) for i,s in enumerate(saved['parameters']['native_documents'])]
    selections += [('directional_document', i, s) for i,s in enumerate(saved['parameters']['directional_documents'])]
    if bundle is None:
        c._require(not any('requirement_id' in s for _,_,s in selections), path='/bundle')
        return
    bundle = c._checked(validate_contract, 'ArtifactBundle', bundle, path='/bundle')
    c._require(c.digest(bundle) == saved['bundle_sha256'] and c.canonical(bundle['original_task']) == c.canonical(saved['original_task']), path='/bundle')
    c._require([v['evidence'] for v in saved['supplied_values']] == bundle['supplied_scientific_metadata'], path='/supplied_values')
    memberships = [_members(bundle,s) for _,_,s in selections]
    refs = [m[0]['source_ref'] for m in memberships if len(m) == 1]
    for (kind,index,selected), members in zip(selections,memberships):
        row = next(r for r in saved['input_resolution'] if (r['selector_kind'],r['selection_index']) == (kind,index))
        path = f'/input_resolution/{saved["input_resolution"].index(row)}'
        c._require(row['construction_evidence'] is None, path=path)
        if len(members) != 1 or refs.count(members[0]['source_ref']) > 1:
            c._require(row['result_index'] is None and row['content'] is None, path=path)
            continue
        member = members[0]
        content = dict(source_ref=member['source_ref'], artifact_field='artifact_ref', artifact_ref=member['raw_artifact_ref'],
                       sha256=member['sha256'], byte_count=member['byte_count'])
        if row['content'] is None:
            c._require(row['result_index'] is None and row['state'] in ('invalid','incompatible','unverified'), path=path)
            continue
        c._require(row['content'] == content, path=path + '/content')
        if row['result_index'] is None: continue
        c._require(member['role'] == selected['role'] and member['declared_format'] == selected['declared_format'], path=path)
        transfer = member['transfer']
        observed, requested = transfer['observed_range'], transfer['requested_range']
        c._require(not (observed is not None and observed['start'] != 0 or observed is None and transfer['object_complete'] != 'yes'
                        and requested is not None and requested[0] != 0), path=path)
        result = saved['directional_results'][row['result_index']] if kind == 'directional_document' else saved['native_results'][row['result_index']]['value']
        if result is not None:
            c._require(result['source'] == dict(content=content, body_complete=transfer['body_complete'], object_complete=transfer['object_complete']), path=path)


def _ref_scope(reference, scope, observed, path):
    # Resolve only saved fields. Equal-valued fields of another occurrence are
    # not interchangeable operands, including equal query/subject lengths.
    try: n._resolve(observed, reference, path)
    except ValueError as error: raise c.ProteomeBundleV2Error(_NUMERICAL, path) from error
    if scope is None: return
    _require(reference['report_ordinal'] == scope['report_ordinal'], path)
    tokens = reference['pointer'].split('/')
    for field,array in (('query_ordinal','queries'),('subject_ordinal','subjects'),('hsp_ordinal','hsps'),('block_ordinal','traceback_blocks')):
        if field in scope and array in tokens:
            at = tokens.index(array) + 1
            _require(at < len(tokens) and tokens[at] == str(scope[field]), path)


def _relations(value, observed, params, path='', scope=None):
    if type(value) is list:
        for i, child in enumerate(value): _relations(child, observed, params, f'{path}/{i}', scope)
    elif type(value) is dict:
        if set(value) == {'report_ordinal','pointer'}:
            _ref_scope(value, scope, observed, path)
            return
        if 2 <= len(value) <= 6 and set(value) == set(_KEYS[:len(value)]):
            try:
                owner=n._native(observed,value,path)
                if 'column_ordinal' in value:
                    _require(owner['query_symbols']['state'] == owner['subject_symbols']['state'] == 'present' and
                        value['column_ordinal'] < len(owner['query_symbols']['value']) == len(owner['subject_symbols']['value']),path)
            except (ValueError,KeyError,IndexError) as error:
                raise c.ProteomeBundleV2Error(_NUMERICAL,path) from error
            if scope is not None:
                _require(all(value[f] == scope[f] for f in value.keys() & scope.keys()),path)
            return
        if 'key' in value and type(value['key']) is dict: scope = value['key']
        elif 'report_ordinal' in value and 'queries' in value: scope = {'report_ordinal':value['report_ordinal']}
        if set(value) == {'numerator','denominator','decimal'}:
            a,b = value['numerator'],value['denominator']
            _require(0 <= a <= b and b > 0 and value['decimal'] == n._ratio_text(a,b,params['ratio_decimal_places']), path)
        if 'inputs' in value:
            _unique(value['inputs'], path + '/inputs')
            _unique(value['reasons'], path + '/reasons')
            _require((value['state'] == 'value') == (value['value'] is not None), path)
            _require(value['state'] == 'value' or bool(value['reasons']), path + '/reasons')
        if set(value) == {'code','fields','columns','hsps','argument_pointer'}:
            for field in ('fields','columns','hsps'): _unique(value[field], path + '/' + field)
            argument = value['code'] in n._ARGUMENT_CODES
            _require((value['argument_pointer'] is not None) == argument, path)
            _require(not argument or not any(value[f] for f in ('fields','columns','hsps')), path)
        for name,child in value.items(): _relations(child,observed,params,path + '/' + name,scope)


def _support(support, blocks, missing, path):
    expected = {_key(b['key']) for b in blocks}
    included, excluded = support['included_blocks'],support['excluded_blocks']
    for field in ('included_blocks','excluded_blocks','hsps_without_traceback'): _unique(support[field],path + '/' + field)
    a,b = {_key(k) for k in included},{_key(k) for k in excluded}
    _require(not a & b and a | b == expected, path)
    _same(support['hsps_without_traceback'], missing, path + '/hsps_without_traceback')
    _require(support['complete_for_displayed_blocks'] == (not excluded and not missing), path)


def _intervals(intervals, path):
    previous = -1
    for i,(start,end) in enumerate(intervals):
        _require(previous < start < end, f'{path}/{i}')
        previous = end


def _union(value, length, length_ref, blocks, missing, params, path):
    _same(value['reported_length'],length,path + '/reported_length')
    _intervals(value['intervals'],path + '/intervals')
    count,coverage = value['count'],value['coverage']
    if count['state'] == 'value':
        _require(count['value'] == sum(b-a for a,b in value['intervals']),path + '/count')
    else:
        _require(not value['intervals'],path + '/intervals')
    _require(length_ref in coverage['inputs'],path + '/coverage/inputs')
    expected = n._union_refs([count])
    if length_ref not in expected: expected.append(length_ref)
    _require({c.canonical(r) for r in coverage['inputs']} == {c.canonical(r) for r in expected},path + '/coverage/inputs')
    if coverage['state'] == 'value':
        _require(count['state'] == 'value' and length['state'] == 'present' and length['value'] > 0,path + '/coverage')
        _same((coverage['value']['numerator'],coverage['value']['denominator']), (count['value'],length['value']),path + '/coverage/value')
    _support(value['support'],blocks,missing,path + '/support')


def _coverage(coverage, query, subject, key, blocks, missing, params, path):
    for name,value in coverage.items():
        axis = name.split('_',1)[0]
        k = {f:key[f] for f in _KEYS[:2 if axis == 'query' else 3]}
        _union(value,(query if axis == 'query' else subject)['length'],n._ref(k,'length'),blocks,missing,params,path + '/' + name)


def _trace(counts, fractions, params, path, columns=None):
    # Only relationships among persisted counts/classes are checked. No residue
    # classification or position construction is repeated from native strings.
    equations = [('alignment_columns',('paired_columns','query_gap_columns','subject_gap_columns')),
        ('paired_columns',('displayed_symbol_identical_pairs','displayed_symbol_nonidentical_pairs')),
        ('paired_columns',('resolved_amino_acid_pairs','unresolved_symbol_pairs','stop_containing_pairs')),
        ('resolved_amino_acid_pairs',('resolved_amino_acid_identical_pairs','resolved_amino_acid_substituted_pairs')),
        ('query_non_gap_symbols',('paired_columns','subject_gap_columns')),
        ('subject_non_gap_symbols',('paired_columns','query_gap_columns'))]
    for total,parts in equations:
        if all(counts[f]['state'] == 'value' for f in (total,*parts)):
            _require(counts[total]['value'] == sum(counts[f]['value'] for f in parts),path + '/' + total)
    for axis in ('query','subject'):
        runs,gaps = counts[axis + '_gap_runs'],counts[axis + '_gap_columns']
        if runs['state'] == gaps['state'] == 'value':
            _require(0 <= runs['value'] <= gaps['value'] and bool(runs['value']) == bool(gaps['value']),path + '/' + axis + '_gap_runs')
    try: n._validate_fractions(fractions,counts,params,path + '/fractions')
    except ValueError as error: raise c.ProteomeBundleV2Error(_NUMERICAL,getattr(error,'pointer',path)) from error
    if columns is not None:
        width = counts['alignment_columns']
        if width['state'] != 'value':
            _require(not columns,path + '/columns')
            return
        _require(width['value'] == len(columns),path + '/columns')
        types = {'resolved_amino_acid_identical_pairs':('resolved_identical',),
                 'resolved_amino_acid_substituted_pairs':('resolved_substituted',),
                 'unresolved_symbol_pairs':('unresolved_pair',),'stop_containing_pairs':('stop_containing_pair',),
                 'query_gap_columns':('query_gap',),'subject_gap_columns':('subject_gap',)}
        for field,kinds in types.items():
            _require(counts[field]['state'] == 'value' and counts[field]['value'] == sum(x['kind'] in kinds for x in columns),path + '/' + field)
        _require(counts['displayed_symbol_identical_pairs']['value'] == sum(x['displayed_symbol_equal'] for x in columns),path + '/displayed_symbol_identical_pairs')


def _count(value, number, path):
    _require(value['state'] == 'value' and value['value'] == number,path)


def _expectation(cell):
    if cell['state'] != 'present': return cell['state']
    value = Decimal(cell['value'])
    return 'invalid' if value < 0 else 'printed_zero_precision_unknown' if value == 0 else 'positive_reported_decimal'


def _extremum(value, native, key, field, path):
    ties,excluded = value['tied_hsps'],value['excluded_hsps']
    _unique(ties,path + '/tied_hsps'); _unique(excluded,path + '/excluded_hsps')
    for h in ties + excluded:
        _require(all(h[f] == key[f] for f in key) and h['hsp_ordinal'] < len(native['hsps']),path)
    _require(not {_key(k) for k in ties} & {_key(k) for k in excluded},path)
    if value['state'] == 'value':
        _require(bool(ties) and value['selected_field'] == n._ref(ties[0],field),path + '/selected_field')
        chosen = native['hsps'][ties[0]['hsp_ordinal']][field]
        _require(chosen['state'] == 'present' and (field != 'expect' or Decimal(chosen['value']) >= 0),path)
        for hk in ties:
            cell = native['hsps'][hk['hsp_ordinal']][field]
            _require(cell['state'] == 'present' and Decimal(cell['value']) == Decimal(chosen['value']),path + '/tied_hsps')
    else:
        _require(value['selected_field'] is None and not ties,path)
    for hk in excluded:
        cell = native['hsps'][hk['hsp_ordinal']][field]
        _require(cell['state'] != 'present' or field == 'expect' and Decimal(cell['value']) < 0,path + '/excluded_hsps')


def _graph(graph, subject, path):
    _same(graph['key'],subject['key'],path + '/key')
    blocks = [b for h in subject['hsps'] for b in h['blocks']]
    columns = {_key(col['key']):col for b in blocks for col in b['columns']}
    missing = [h['key'] for h in subject['hsps'] if not h['blocks']]
    _support(graph['pair_geometry_support'],blocks,missing,path + '/pair_geometry_support')
    edges = graph['edges']
    _unique([(e['query_position'],e['subject_position']) for e in edges],path + '/edges')
    all_supports = []
    for i,edge in enumerate(edges):
        _require(bool(edge['supports']),f'{path}/edges/{i}/supports')
        _unique(edge['supports'],f'{path}/edges/{i}/supports')
        for key in edge['supports']:
            col = columns.get(_key(key))
            _require(col is not None,f'{path}/edges/{i}/supports')
            for axis in ('query','subject'):
                _require(col[axis + '_position'] == {'state':'position','value':edge[axis + '_position']},f'{path}/edges/{i}')
            all_supports.append(key)
    _unique(all_supports,path + '/edges/supports')
    if graph['distinct_pair_count']['state'] == 'value':
        _count(graph['distinct_pair_count'],len(edges),path + '/distinct_pair_count')
        _count(graph['repeated_pair_occurrence_count'],len(all_supports)-len(edges),path + '/repeated_pair_occurrence_count')
    for i,conflict in enumerate(graph['conflicts']):
        _unique(conflict['columns'],f'{path}/conflicts/{i}/columns')
        _require(bool(conflict['columns']) and all(_key(k) in columns for k in conflict['columns']),f'{path}/conflicts/{i}/columns')
        for axis in ('query','subject'): _intervals(conflict[axis + '_intervals'],f'{path}/conflicts/{i}/{axis}_intervals')
    _require((graph['mapping_state'] == 'observed_conflict') == bool(graph['conflicts']),path + '/mapping_state')
    counts = subject['compatible_pair_counts']
    expected_state = {'compatible_displayed_partial_map':'value','observed_conflict':'conflict','incomplete_geometry':'missing'}[graph['mapping_state']]
    for cell in counts.values(): _require(cell['state'] == expected_state,path + '/compatible_pair_counts')
    if expected_state == 'value':
        selected = [columns[_key(e['supports'][0])] for e in edges]
        _require(counts['identical_symbol_pairs']['value'] == sum(x['displayed_symbol_equal'] for x in selected),path)
        for field,kinds in (('resolved_pairs',('resolved_identical','resolved_substituted')),
            ('resolved_identical_pairs',('resolved_identical',)),('resolved_substituted_pairs',('resolved_substituted',)),
            ('unresolved_pairs',('unresolved_pair',)),('stop_containing_pairs',('stop_containing_pair',))):
            _require(counts[field]['value'] == sum(x['kind'] in kinds for x in selected),path + '/' + field)
    for name,num,den in (('compatible_unique_pair_symbol_identity',counts['identical_symbol_pairs'],graph['distinct_pair_count']),
            ('compatible_unique_pair_resolved_identity',counts['resolved_identical_pairs'],counts['resolved_pairs']),
            ('compatible_unique_pair_resolved_fraction',counts['resolved_pairs'],graph['distinct_pair_count'])):
        cell = subject[name]
        if cell['state'] == 'value':
            _require(expected_state == 'value' and num['state'] == den['state'] == 'value',path + '/' + name)
            _same([cell['value']['numerator'],cell['value']['denominator']],[num['value'],den['value']],path + '/' + name)
        elif expected_state != 'value': _require(cell['state'] == expected_state,path + '/' + name)


def validate_directional_saved(result, observed, parameters):
    c.validate_shape_v2('DirectionalDirectionalComponentsResult',result,code=_NUMERICAL)
    if result['components'] is None:
        for issue in result['diagnostics']:
            _require(issue['code'] in n._ARGUMENT_CODES and issue['argument_pointer'] is not None and
                     not any(issue[f] for f in ('fields','columns','hsps')),'/diagnostics')
        return
    value = result['components']
    _require(observed is not None,'/sheet')
    _same(value['parameters'],parameters,'/parameters')
    _same(value['formula_version'],parameters['formula_version'],'/formula_version')
    _same(value['sheet_sha256'],n.canonical_sheet_sha256(observed),'/sheet_sha256')
    _same(result['diagnostics'],value['diagnostics'],'/diagnostics')
    _relations(value,observed,parameters)
    _require(len(value['reports']) == len(observed['reader_results']),'/reports')
    for ri,(report,raw) in enumerate(zip(value['reports'],observed['reader_results'])):
        rp=f'/reports/{ri}'
        _require(report['report_ordinal'] == ri and len(report['queries']) == len(raw['queries']),rp)
        for qi,(query,nq) in enumerate(zip(report['queries'],raw['queries'])):
            qp=f'{rp}/queries/{qi}'; qk=n._key(ri,qi)
            _same(query['key'],qk,qp + '/key')
            _require(len(query['subjects']) == len(nq['subjects']),qp)
            for si,(subject,ns) in enumerate(zip(query['subjects'],nq['subjects'])):
                sp=f'{qp}/subjects/{si}'; sk=n._key(ri,qi,si)
                _same(subject['key'],sk,sp + '/key')
                _require(len(subject['hsps']) == len(ns['hsps']),sp)
                for hi,(hsp,nh) in enumerate(zip(subject['hsps'],ns['hsps'])):
                    hp=f'{sp}/hsps/{hi}'; hk=n._key(ri,qi,si,hi)
                    _same(hsp['key'],hk,hp + '/key')
                    _require(len(hsp['blocks']) == len(nh['traceback_blocks']),hp)
                    for bi,(block,nb) in enumerate(zip(hsp['blocks'],nh['traceback_blocks'])):
                        bp=f'{hp}/blocks/{bi}'; bk=n._key(ri,qi,si,hi,bi)
                        _same(block['key'],bk,bp + '/key')
                        for ci,col in enumerate(block['columns']):
                            _same(col['key'],{**bk,'column_ordinal':ci},bp + '/columns')
                            for axis in ('query','subject'):
                                source=nb[axis + '_symbols']
                                _require(source['state'] == 'present' and ci < len(source['value']) and col[axis + '_symbol'] == source['value'][ci],bp + '/columns')
                        _trace(block['counts'],block['fractions'],parameters,bp,block['columns'])
                        _coverage(block['coverage'],nq,ns,bk,[block],[],parameters,bp + '/coverage')
                    for field in ('bit_score','raw_score','expect','expect_group_count'):
                        _same(hsp['native_scores'][field],nh[field],hp + '/native_scores/' + field)
                    _same(hsp['native_scores']['expectation_display'],_expectation(nh['expect']),hp + '/native_scores/expectation_display')
                    try: n._validate_reported(hsp['reported'],nh,hk,parameters,hp + '/reported')
                    except ValueError as error: raise c.ProteomeBundleV2Error(_NUMERICAL,getattr(error,'pointer',hp)) from error
                    missing=[] if hsp['blocks'] else [hk]
                    for field in ('strings_support','pair_geometry_support'):
                        _support(hsp[field],hsp['blocks'],missing,hp + '/' + field)
                    _trace(hsp['trace_counts'],hsp['trace_fractions'],parameters,hp)
                    _coverage(hsp['coverage'],nq,ns,hk,hsp['blocks'],missing,parameters,hp + '/coverage')
                blocks=[b for h in subject['hsps'] for b in h['blocks']]
                missing=[h['key'] for h in subject['hsps'] if not h['blocks']]
                _count(subject['displayed_hsp_count'],len(subject['hsps']),sp)
                _count(subject['displayed_block_count'],len(blocks),sp)
                _coverage(subject['coverage'],nq,ns,sk,blocks,missing,parameters,sp + '/coverage')
                _graph(subject['correspondence'],subject,sp + '/correspondence')
                for name,field in (('maximum_reported_hsp_bit_score','bit_score'),('maximum_reported_hsp_raw_score','raw_score'),('minimum_reported_hsp_expectation','expect')):
                    _extremum(subject[name],ns,sk,field,sp + '/' + name)
                a,b,ratio=(subject[f] for f in ('nonoverlapping_hsp_reported_identity_count','nonoverlapping_hsp_reported_alignment_columns','nonoverlapping_hsp_reported_identity_over_columns'))
                _require(a['state'] == b['state'] == ratio['state'],sp + '/nonoverlapping_hsp_reported_identity_count')
                if a['state'] == 'value':
                    _require(all(h['identity_count']['state'] == h['identity_denominator']['state'] == 'present' for h in ns['hsps']),sp)
                    _require(a['value'] == sum(h['identity_count']['value'] for h in ns['hsps']) and b['value'] == sum(h['identity_denominator']['value'] for h in ns['hsps']),sp)
                    _same([ratio['value']['numerator'],ratio['value']['denominator']],[a['value'],b['value']],sp)
            blocks=[b for s in query['subjects'] for h in s['hsps'] for b in h['blocks']]
            missing=[h['key'] for s in query['subjects'] for h in s['hsps'] if not h['blocks']]
            _union(query['any_displayed_subject_query_paired_union'],nq['length'],n._ref(qk,'length'),blocks,missing,parameters,qp + '/any_displayed_subject_query_paired_union')
            for kind,number in (('description',len(nq['descriptions'])),('subject',len(nq['subjects'])),('hsp',sum(len(s['hsps']) for s in nq['subjects'])),('block',len(blocks))):
                _count(query['displayed_' + kind + '_count'],number,qp)
        _count(report['displayed_query_count'],len(raw['queries']),rp)
        for kind in ('description','subject','hsp','block'):
            _count(report['displayed_' + kind + '_count'],sum(q['displayed_' + kind + '_count']['value'] for q in report['queries']),rp)
    codes={i['code'] for i in result['diagnostics']} - {'printed_zero_expectation','no_execution_or_occurrence_evidence'}
    _require(result['state'] == ('partial' if codes else 'available'),'/state')


def validate_saved_provider_v2(sheet, components, *, parameters, requested_form, original_task, bundle_sha256, bundle):
    parameters=c.validate_parameters_v2(parameters)
    form=c.validate_form_parameters(requested_form,parameters)
    if sheet is None:
        c._require(components is None,path='/components')
        return None,None
    saved=c.validate_provider_sheet_v2(sheet)
    c._require(c.canonical(saved['parameters']) == c.canonical(parameters) and saved['requested_form'] == form and
        c.canonical(saved['original_task']) == c.canonical(original_task) and saved['bundle_sha256'] == bundle_sha256,path='/sheet')
    _bundle_binding(saved,bundle)
    native=None if saved['native_sheet_result'] is None else saved['native_sheet_result']['value']
    observed=None if saved['directional_sheet_result'] is None else saved['directional_sheet_result']['sheet']
    if components is None:
        c._require(native is None and observed is None,path='/components')
        return saved,None
    components=c.validate_shape_v2('ProviderComponentsV2',components)
    c._require(components['provider_sheet_sha256'] == c.digest(saved),path='/components/provider_sheet_sha256')
    c._require(components['legacy'] is not None or components['directional'] is not None,path='/components')
    c._require((components['legacy'] is not None) == (native is not None) and
               (components['directional'] is not None) == (observed is not None),path='/components')
    if components['legacy'] is not None:
        legacy=c._checked(validate_proteome_sheet_data,'NativeComponentsResult',components['legacy'],path='/components/legacy')
        if legacy['value'] is not None:
            c._require(legacy['value']['sheet_sha256'] == c.digest(native) and
                c.canonical(legacy['value']['parameters']) == c.canonical(parameters['calculation_parameters']),path='/components/legacy/value')
    if components['directional'] is not None:
        validate_directional_saved(components['directional'],observed,parameters['directional_calculation_parameters'])
    return deepcopy(saved),deepcopy(components)


__all__=['validate_saved_provider_v2']
