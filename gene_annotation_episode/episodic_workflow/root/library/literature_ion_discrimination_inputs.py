"""Closed ion-discrimination source selections and possessed activity rows.

Numeric values come from exact authorized sources or selected saved cells.
Scientific interpretations remain source-witnessed episode decisions.
"""
from copy import deepcopy
from fractions import Fraction
import json
import math
from gene_annotation_episode.domain import identity, validate_schema
from ..literature_assay_inputs import _Sources, _interpretation
from .literature_compiled_assay_return_schema import compiled_assay_cells_schema
from .literature_experimental_contracts import ExperimentalContractError
from .literature_ion_discrimination_numbers import read_ion_number, read_ion_unit, check_explicit_unit, rational

VERSION = 'a105_ion_discrimination_extraction_v1'
ROLES = ('preferred', 'alternative')

from gene_annotation_episode.episodic_workflow.root.library.literature_ion_discrimination_input_contracts import _SELECTION_SCHEMA, _SHEET_SCHEMA, _COVARIANCE_SCHEMA, ion_discrimination_population_schema, ion_discrimination_sheet_schema, ion_activity_covariance_schema
def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _meaning(value, schema, sources, field):
    allowed = schema['properties']['value']['enum']
    return _interpretation(value, allowed, sources, field)


def activity_key(selection):
    return identity('selected_ion_activity', selection)


def dependency_keys(row):
    return list(dict.fromkeys(key for dep in row['dependencies']
        for name in ('canonical_physical_keys', 'recorded_dependency_keys') for key in dep[name]))


def _read_quantity(selected, sources, *, field, source_kind):
    schema = _SELECTION_SCHEMA['$defs']['SourceQuantity']['properties']
    result = {name: _meaning(value, schema[name], sources, field + '.' + name)
        for name, value in selected.items() if name not in ('number', 'unit')}
    number, unit, reasons = None, None, []
    if selected['number'] is None:
        reasons.append('source_number_not_selected')
    else:
        try:
            number = read_ion_number(selected['number'], sources=sources)
        except ExperimentalContractError as error:
            if error.code not in ('unimplemented_number_representation', 'interval_source_number_unsupported',
                                   'untyped_limit_source_number', 'numerical_model_range'):
                raise
            reasons.append('numerical_model_range' if error.code == 'numerical_model_range' else 'unimplemented_number_representation')
    try:
        unit = read_ion_unit(selected['unit'], sources=sources)
    except ExperimentalContractError as error:
        if error.code != 'unsupported_source_unit':
            raise
        reasons.append('unimplemented_number_representation')
    ratio = result['meaning']['value'] in ('reported_permeability_ratio', 'reported_transport_selectivity_ratio', 'reported_cross_assay_summary_ratio')
    if selected['unit'] is None and not ratio:
        reasons.append('source_unit_not_selected')
    if number is not None:
        check_explicit_unit(number, unit, sources=sources, dimensionless=ratio)
    if ratio and unit is not None and unit['unit'] != 'dimensionless':
        _fail('source_number_unit_role_mismatch', field)
    qualified = result['qualification']['value']
    approximation = ('conflicting' if qualified=='conflicting' else 'source_qualified' if number and number['adjacent_approximate'] or qualified=='source_qualified_approximate' else 'unknown' if qualified=='unknown' else 'not_explicitly_qualified')
    qualifications=[]
    if number and number['adjacent_approximate']:qualifications.append('adjacent_approximate')
    if qualified=='source_qualified_approximate':qualifications.append('nonadjacent_source_approximation')
    if qualified=='conflicting':qualifications.append('selected_qualification_conflicting')
    if qualified=='unknown':qualifications.append('selected_qualification_unknown')
    if number and number.get('adjacent_uncertainty_uninterpreted'):qualifications.append('adjacent_uncertainty_uninterpreted')
    derivation=result['derivation']['value']
    origin='synthetic' if source_kind=='synthetic_fixture' else 'derived' if source_kind=='retained_extraction' else 'author_inferred' if derivation in ('author_inferred_dead_time_and_geometry','author_inferred_electrical_model','author_summary_inference') else 'reported'
    return {'kind': 'source_quantity', 'selection': deepcopy(selected), 'number': number, 'unit': unit,
        'interpretations': result, 'approximation': approximation, 'source_qualifications':qualifications,'origin':origin,'reasons': reasons}


def _read_covariance(reference, operands, sources, requested_status, source_kind):
    if reference is None:
        return {'status': 'not_selected', 'source_ref': None, 'data': None}
    source = sources.source(reference, 'original')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _fail('duplicate_json_key', 'activity_covariance')
            result[key] = value
        return result
    try:
        data = json.loads(source['content'].decode('utf8'), object_pairs_hook=pairs,
            parse_constant=lambda _token: _fail('finite_number_required', 'activity_covariance'))
        validate_schema(data, ion_activity_covariance_schema())
        if data['activity_keys'] != [operands[r]['activity_key'] for r in ROLES]:
            _fail('covariance_owner_or_dependency_mismatch', 'activity_keys')
        if data['dependency_keys'] != [dependency_keys(operands[r]['row']) for r in ROLES]:
            _fail('covariance_owner_or_dependency_mismatch', 'dependency_keys')
        if any(operands[r]['row']['unit'] != 'per_min' for r in ROLES):
            _fail('covariance_units_incompatible', 'activity_units')
        matrix = data['matrix']
        if any(type(v) not in (int, float) or not math.isfinite(v) for row in matrix for v in row):
            _fail('covariance_invalid', 'matrix')
        a,b,c,d = (Fraction(str(v)) for row in matrix for v in row)
        if b != c or a < 0 or d < 0 or a*d-b*b < 0:
            _fail('covariance_invalid', 'matrix')
        if data['origin']=='synthetic' and source_kind!='synthetic_fixture':
            _fail('covariance_invalid','synthetic_covariance_for_nonsynthetic_source')
        alias=[canonical_activity_owner(operands[r]['row']) for r in ROLES]
        if alias[0] is not None and alias[0]==alias[1] and (matrix[0]!=matrix[1] or any(row[0]!=row[1] for row in matrix)):
            _fail('shared_activity_covariance_inconsistent','matrix')
        if data['variance_status'] != requested_status:
            _fail('covariance_status_unknown', 'variance_status')
        return {'status': 'valid', 'source_ref': reference, 'artifact_ref': source['artifact_ref'], 'data': data}
    except (ExperimentalContractError, ValueError, TypeError, OverflowError) as error:
        code = getattr(error, 'code', 'covariance_invalid')
        if code not in ('covariance_owner_or_dependency_mismatch', 'covariance_units_incompatible', 'covariance_status_unknown','shared_activity_covariance_inconsistent'):
            code = 'covariance_invalid'
        return {'status': code, 'source_ref': reference, 'artifact_ref': source['artifact_ref'], 'data': None}


def _adjustments(arguments, operands, sources):
    bindings, reasons = [], []
    differences = arguments['nonintended_differences']
    for selected in arguments['adjustment_bindings']:
        binding = deepcopy(selected)
        binding['witnesses'] = [sources.witness(w, 'adjustment_binding') for w in selected['witnesses']]
        if selected['difference_index'] >= len(differences):
            _fail('adjustment_difference_index_unresolved', 'adjustment_bindings')
        if selected['control_application'] != 'addresses_selected_nonintended_difference' or not binding['witnesses']:
            reasons.append('adjustment_scope_unresolved')
        row = operands[selected['arm']]['row'];stage = selected['compiled_stage']
        state = row['correction_stages'][stage]
        roles = {'recovery': ('k',), 'molecule_amount': ('E',), 'nuisance_condition': ('u','v')}[stage]
        dep_roles = {d['role'] for d in row['dependencies']}
        meanings = row['operand_meanings']
        allowed = {'k': ('applicable_reporter_standard',), 'E': ('same_assay_active_molecules','same_assay_total_molecules'),
            'u': ('test_nuisance_control_excludes_intended_change',), 'v': ('reference_nuisance_control_excludes_intended_change',)}
        applied = (row['status'] == 'populated' and row['component'] == 'corrected_activity'
            and row['formula'] in ('(q-g)*v/(k*E*u)','source_already_corrected_amount_normalized_value')
            and state in ('already_applied','not_applied')
            and (state == 'already_applied' or all(r in dep_roles and meanings[r] in allowed[r] for r in roles)))
        if not applied:
            reasons.append('adjustment_not_in_compiled_activity')
        binding['compiled_stage_verified'] = applied
        bindings.append(binding)
    if arguments['relationships']['nonintended_conditions']['value'] == 'source_supported_adjustment':
        if not differences or any(not any(b['difference_index']==i and b['compiled_stage_verified'] for b in bindings) for i in range(len(differences))):
            reasons.append('adjustment_binding_required')
    return bindings, list(dict.fromkeys(reasons))


def read_ion_discrimination_inputs(arguments, *, read_source, read_component):
    """Authenticate original limits or exactly possessed compiled activities."""
    args = deepcopy(arguments);validate_schema(args, ion_discrimination_population_schema())
    sources = _Sources(read_source);original = sources.source(args['source_ref'],'original')
    context = {}
    for name,value in args['context'].items():
        if name in ROLES:
            context[name] = {key: None if w is None else sources.witness(w,'context.'+name+'.'+key) for key,w in value.items()}
        else:
            context[name] = None if value is None else sources.witness(value,'context.'+name)
    relschema = _SELECTION_SCHEMA['$defs']['Relationships']['properties']
    relationships = {name:_meaning(value,relschema[name],sources,'relationships.'+name) for name,value in args['relationships'].items()}
    differences = [{**deepcopy(d),'witnesses':[sources.witness(w,'nonintended_difference') for w in d['witnesses']]} for d in args['nonintended_differences']]
    operands={};covariance={'status':'not_selected','source_ref':None,'data':None};adjustments=[];adjustment_reasons=[]
    if args['route']=='compiled_activity_pair':
        for role, selection in args['activities'].items():
            rows = read_component(deepcopy(selection))
            if not isinstance(rows,list) or len(rows)!=1 or rows[0]['sheet_ref']!=selection['sheet_ref'] or rows[0]['component']!='corrected_activity':
                _fail('selected_activity_not_received',role)
            validate_schema(rows,compiled_assay_cells_schema())
            operands[role]={'kind':'compiled_activity','selection':deepcopy(selection),'activity_key':activity_key(selection),'row':deepcopy(rows[0])}
        covariance = _read_covariance(args['activity_covariance_source_ref'],operands,sources,args['variance_status'],args['source_kind'])
        witnesses=[sources.witness(w,'variance_witness') for w in args['variance_witnesses']]
        if args['variance_status']!='unknown' and not witnesses:
            _fail('variance_witness_required','variance_witnesses')
        adjustments,adjustment_reasons=_adjustments(args,operands,sources)
    elif args['route']=='reported_ratio':
        operands['reported']=_read_quantity(args['reported_ratio'],sources,field='reported_ratio',source_kind=args['source_kind'])
    else:
        operands={role:_read_quantity(selected,sources,field=role,source_kind=args['source_kind']) for role,selected in args['thresholds'].items()}
    return {'version':VERSION,'selection':args,'source_ref':args['source_ref'],'artifact_ref':original['artifact_ref'],
        'source_refs':list(sources.references),'route':args['route'],'context':context,'relationships':relationships,
        'nonintended_differences':differences,'operands':operands,'covariance':covariance,
        'adjustment_bindings':adjustments,'adjustment_reasons':adjustment_reasons}


__all__=['VERSION','ROLES','ion_discrimination_population_schema','ion_discrimination_sheet_schema',
    'ion_activity_covariance_schema','read_ion_discrimination_inputs','activity_key','dependency_keys']


def validate_ion_discrimination_extraction(extraction):
    """Validate parsed-input shape and numerical ownership without source I/O."""
    e=deepcopy(extraction)
    fields={'version','selection','source_ref','artifact_ref','source_refs','route','context','relationships',
        'nonintended_differences','operands','covariance','adjustment_bindings','adjustment_reasons'}
    if not isinstance(e,dict) or set(e)!=fields or e['version']!=VERSION:
        _fail('ion_extraction_shape_mismatch','extraction')
    validate_schema(e['selection'],ion_discrimination_population_schema())
    args=e['selection']
    if e['route']!=args['route'] or e['source_ref']!=args['source_ref'] or e['source_ref'] not in e['source_refs']:
        _fail('ion_extraction_selection_mismatch','extraction')
    if set(e['relationships'])!=set(args['relationships']) or any(e['relationships'][k]['value']!=v['value'] for k,v in args['relationships'].items()):
        _fail('ion_extraction_selection_mismatch','relationships')
    if e['route']=='compiled_activity_pair':
        if set(e['operands'])!=set(ROLES):_fail('ion_extraction_shape_mismatch','operands')
        for role in ROLES:
            op=e['operands'][role];selected=args['activities'][role]
            if set(op)!={'kind','selection','activity_key','row'} or op['kind']!='compiled_activity' or op['selection']!=selected or op['activity_key']!=activity_key(selected):
                _fail('ion_extraction_selection_mismatch','operands.'+role)
            validate_schema([op['row']],compiled_assay_cells_schema())
            if op['row']['sheet_ref']!=selected['sheet_ref'] or op['row']['component']!='corrected_activity':
                _fail('ion_extraction_selection_mismatch','operands.'+role)
        cov=e['covariance']
        if cov['status']=='valid':
            validate_schema(cov['data'],ion_activity_covariance_schema())
            if cov['data']['activity_keys']!=[e['operands'][r]['activity_key'] for r in ROLES] or cov['data']['dependency_keys']!=[dependency_keys(e['operands'][r]['row']) for r in ROLES]:
                _fail('covariance_owner_or_dependency_mismatch','covariance')
            C=cov['data']['matrix']
            if any(type(v) not in (int,float) or not math.isfinite(v) for row in C for v in row):
                _fail('covariance_invalid','covariance')
            a,b,c,d=(Fraction(str(v)) for row in C for v in row)
            if b!=c or a<0 or d<0 or a*d-b*b<0:_fail('covariance_invalid','covariance')
    else:
        wanted={'reported':args['reported_ratio']} if e['route']=='reported_ratio' else args['thresholds']
        if set(e['operands'])!=set(wanted):_fail('ion_extraction_shape_mismatch','operands')
        for role,selected in wanted.items():
            q=e['operands'][role]
            if set(q)!={'kind','selection','number','unit','interpretations','approximation','source_qualifications','origin','reasons'} or q['kind']!='source_quantity' or q['selection']!=selected:
                _fail('ion_extraction_selection_mismatch','operands.'+role)
            if any(q['interpretations'][k]['value']!=v['value'] for k,v in selected.items() if k not in ('number','unit')):
                _fail('ion_extraction_selection_mismatch','interpretations')
            n=q['number']
            if n is not None:
                sel=selected['number'];w=sel['witness'];token=w['quote'][sel['number_start']:sel['number_end']]
                if (n['raw_token']!=token or type(n['value']) not in (int,float) or not math.isfinite(n['value'])
                        or n['relation'] not in ('point','lt','le','gt','ge','lower_limit','upper_limit')
                        or type(n['adjacent_approximate']) is not bool):
                    _fail('ion_extraction_number_mismatch','number')
                exact=Fraction(int(n['exact']['numerator']),int(n['exact']['denominator']))
                if float(exact)!=n['value']:
                    _fail('ion_extraction_number_mismatch','number')
    return e


__all__.append('validate_ion_discrimination_extraction')


def canonical_activity_owner(row):
    """Known complete mean ownership, never a shared subset or equal values.

    Each retained quantity identity must have canonical source anchors; unknown
    physical identities return None. Stated correction identities are constants.
    """
    if row['unit']!='per_min':return None
    formula=row['formula'];stages=row['correction_stages']
    if any(v in ('unknown','conflicting') for v in stages.values()):return None
    if formula=='source_already_corrected_amount_normalized_value':
        if any(v!='already_applied' for v in stages.values()):return None
        roles=('q',)
    elif formula=='(q-g)*v/(k*E*u)':
        if stages['background']!='already_applied' or stages['molecule_amount']!='not_applied':return None
        roles=('q','g','k','E','u','v')
    else:return None
    parts=[]
    for role in roles:
        entries=[d for d in row['dependencies'] if d['role']==role]
        if len(entries)!=1:return None
        d=entries[0]
        if d['identity_stage'] is not None:
            allowed={'g':'contaminant','k':'recovery','u':'nuisance_condition','v':'nuisance_condition'}
            if allowed.get(role)!=d['identity_stage'] or stages[d['identity_stage']]!='already_applied':return None
            parts.append((role,'identity',d['identity_stage']))
        else:
            if not d['quantity_key'] or not d['canonical_physical_keys'] or d['physical_identity_status']!='partly_canonical':return None
            parts.append((role,'quantity',d['quantity_key'],tuple(sorted(d['canonical_physical_keys'])),tuple(sorted(d['recorded_dependency_keys']))))
    return row['unit'],formula,tuple(sorted(stages.items())),tuple(parts)


__all__.append('canonical_activity_owner')
