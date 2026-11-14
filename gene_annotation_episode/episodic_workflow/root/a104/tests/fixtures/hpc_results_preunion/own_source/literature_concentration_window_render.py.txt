"""Render only received concentration-window rows, without source/science IO."""
from collections.abc import Mapping
from copy import deepcopy

from .literature_concentration_window_storage import SCOPE,OPERATION,POPULATION


def is_row(value):
    return isinstance(value,Mapping) and value.get('row_version')=='concentration_window_return_v1' and value.get('evaluation_scope')==SCOPE


def rows_from_values(value):
    if is_row(value):yield value
    elif isinstance(value,Mapping):
        for child in value.values():yield from rows_from_values(child)
    elif isinstance(value,(list,tuple)):
        for child in value:yield from rows_from_values(child)


def history_record(record):
    selection=record.get('selection') if isinstance(record,Mapping) else None
    args=selection.get('arguments') if isinstance(selection,Mapping) else None
    return isinstance(selection,Mapping) and selection.get('tool')==OPERATION and isinstance(args,Mapping) and args.get('version')==POPULATION


def hidden_records(rows,records,bindings=None):
    locations=[loc for row in rows for loc in row['withheld_locations']]
    sources=set(bindings or {})
    artifacts={r for b in (bindings or {}).values() for r in b['artifacts']}
    hidden=set()
    for ref,record in records.items():
        for anchor in (record,record.get('anchor'),record.get('visual_anchor')):
            if not isinstance(anchor,Mapping):continue
            if anchor.get('source_ref') in sources or anchor.get('artifact_ref') in artifacts:hidden.add(ref)
            if any(anchor.get('artifact_ref')==loc['artifact_ref'] and type(anchor.get('start')) is int and type(anchor.get('end')) is int
                and anchor['start']<loc['end'] and loc['start']<anchor['end'] for loc in locations):hidden.add(ref)
    return hidden


def sanitize_private(value,bindings):
    if not bindings:return dict(value) if isinstance(value,Mapping) else value
    sources=set(bindings);artifacts={r for b in bindings.values() for r in b['artifacts']}
    def copy(item):
        if is_row(item):return deepcopy(item)
        if isinstance(item,Mapping):
            anchored=any(isinstance(a,Mapping) and (isinstance(a.get('source_ref'),str) and a['source_ref'] in sources
                or isinstance(a.get('artifact_ref'),str) and a['artifact_ref'] in artifacts) for a in (item,item.get('anchor'),item.get('visual_anchor')))
            if anchored and any(k in item for k in ('text','anchor','visual_anchor')):
                return {'scientific_meaning':'Private concentration-window receipt; use the requested typed components.'}
            return {k:copy(v) for k,v in item.items()}
        if isinstance(item,(tuple,list)):return [copy(v) for v in item]
        return item
    return copy(value)


def state_view(state,lookup_results=()):
    return sanitize_private(state,state.get('literature_concentration_window_receipt_bindings',{}))


def _meaning(value):return value.replace('_',' ') if isinstance(value,str) else value
def _text(field):return '; '.join(fragment['text'] for fragment in field['fragments']) or _meaning(field['display_status'])


def render_received(parts,rows,*,section,table):
    groups,seen={},set()
    for row in rows:
        key=row['sheet_ref'],row['component']
        if key not in seen:seen.add(key);groups.setdefault(row['sheet_ref'],[]).append(row)
    for number,selected in enumerate(groups.values(),1):
        section(parts,'Requested concentration window '+str(number),table(
            ('Component','Value','Conditional value','Unit','Status','Origin','Meaning','Interpretation scope'),
            [(_meaning(r['component']),r['cell']['value'],r['cell']['conditional_value'],r['cell']['unit'],
                _meaning(r['cell']['status']),_meaning(r['cell']['origin']),r['cell']['meaning'],_meaning(r['cell']['interpretation_scope'])) for r in selected]))
        section(parts,'Concentration evidence scope',table(('Source kind','Assertion resolution'),
            list(dict.fromkeys((_meaning(r['source_kind']),_meaning(r['assertion_resolution'])) for r in selected))))
        contexts=[];participants=[];relations=[];operands=[];models=[];timing=[];covariance=[];covariance_owners=[]
        owner_labels={};dependency_labels={}
        for row in selected:
            context=row['scientific_context'];assay=context['assay']
            for name,field in assay.items():
                if name not in ('arrangement','participants'):
                    contexts.append((_meaning(name),_text(field)))
            relations.append(('participant arrangement',_meaning(assay['arrangement']['value'])))
            for p in assay['participants']:participants.append((_text(p['identity']),_meaning(p['role']),_meaning(p['presence'])))
            for role,q in context['quantities'].items():
                for name in ('analyte','unit','record','measurement_identity'):
                    if q[name]['fragments']:contexts.append((_meaning(role)+' / '+_meaning(name),_text(q[name])))
                for name in ('reading_meaning','concentration_basis','unit_association'):
                    relations.append((_meaning(role)+' / '+_meaning(name),_meaning(q[name]['value'])))
            for group in ('pair_relationships','cross_relationships'):
                for name,relationship in context[group].items():
                    for key,meaning in relationship.items():relations.append((_meaning(name)+' / '+_meaning(key),_meaning(meaning['value'])))
            for operand in row['operand_metadata']:
                operands.append(tuple(_meaning(operand[k]) for k in ('role','status','origin','relation','approximate','unit')))
            for analyte,model in context['stoichiometry'].items():
                models.append((_meaning(analyte),model['value'],_meaning(model['kind']),_meaning(model['origin']),
                    _meaning(model['relationship']['value']),_meaning(model['coefficient_meaning']),_meaning(model['conversion_direction'])))
            t=context['timing'];timing.append((_meaning(t['source_meaning']['value']),
                _meaning(t['scenario']['status']) if t['scenario'] is not None else 'not selected'))
            cov=row['covariance_context'];covariance.append(tuple(_meaning(cov[k]) for k in
                ('selection_status','material','basis','variance_status','origin','derivation','systematic_coverage')))
            for role,owner,unit,dependencies in zip(cov['roles'],cov['owner_keys'],cov['units'],cov['dependency_keys']):
                owner_labels.setdefault(owner,'estimate '+str(len(owner_labels)+1))
                for key in dependencies:dependency_labels.setdefault(key,'dependency '+str(len(dependency_labels)+1))
                covariance_owners.append((_meaning(role),owner_labels[owner],unit,', '.join(dependency_labels[key] for key in dependencies)))
        def unique(items):return list(dict.fromkeys(items))
        section(parts,'Assayed molecule and selected experimental definitions',table(('Meaning','Received source definition'),unique(contexts)))
        if participants:section(parts,'Actual experimental participants',table(('Identity','Role','Presence'),unique(participants)))
        section(parts,'Native input meanings without operand values',table(('Role','Status','Origin','Relation','Approximate','Unit'),unique(operands)))
        section(parts,'Pair and reaction-account qualifications',table(('Meaning','Received interpretation'),unique(relations)))
        if models:section(parts,'Interpreted stoichiometric model',table(('Analyte','Coefficient','Kind','Origin','Support','Coefficient meaning','Conversion'),unique(models)))
        section(parts,'Timing meaning',table(('Source time meaning','Sensitivity premise'),unique(timing)))
        section(parts,'Covariance meaning without a matrix',table(('Selection','Material','Basis','Variance status','Origin','Derivation','Systematic coverage'),unique(covariance)))
        if covariance_owners:section(parts,'Ordered covariance ownership',table(('Role','Recorded estimate','Unit','Shared dependencies'),unique(covariance_owners)))
        section(parts,'Requested concentration limitations',table(('Component','Source','Selection','Relationship','Implementation','Domain','Uncertainty method'),
            [(_meaning(r['component']),*('; '.join(_meaning(c) for c in r['cell']['reasons'][k]) for k in ('source','selection','relationship','implementation','domain')),
                _meaning(r['cell']['uncertainty_method'])) for r in selected]))
        section(parts,'Source-window interpretation limits','; '.join(_meaning(c) for c in dict.fromkeys(c for r in selected for c in r['limits'])))
        section(parts,'Measurement contribution meaning',
            'These numerical views retain shared observations and interpreted chemical coefficients. '
            'Product-fate fractions and chemical agreement do not establish unique molecular attribution. '
            'An interval average is not an initial rate or turnover constant. Source uncertainty and conditional timing remain qualified; '
            'no independent replication, function probability, target-transfer weight or annotation credit is inferred.')
