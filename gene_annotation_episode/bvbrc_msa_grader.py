"""Dispatch only the caller's explicit MSA calculations on the saved sheet."""
from copy import deepcopy
from . import bvbrc_msa_provider_contracts as c
from . import phylogeny_calculators as shared
from . import bvbrc_msa_calculators as native
from . import xmfa_coordinates as coordinates
from . import xmfa_calculators as xmfa
from .bvbrc_alignment_values import diagnostic


class _Missing(Exception):
    def __init__(self, reason):
        self.reason = reason


def _required(value, reason='alignment_document_unavailable'):
    if value is None:
        raise _Missing(reason)
    return value


def _dispatch(sheet, request):
    kind = request['kind']; analysis_id = sheet['analysis']['analysis_id']; extra = []
    kwargs = {k: deepcopy(v) for k,v in request.items() if k not in ('kind','request_id')}
    if kind.startswith('xmfa_'):
        c.require(sheet['analysis']['mode'] == 'mauve_blocks', 'xmfa_analysis_mode_conflict')
        document = _required(c.lookup_document(sheet, kwargs.pop('document_id'), 'xmfa'), 'msa_full_xmfa_binding_required')
        if 'use_source_bindings' in kwargs:
            use = kwargs.pop('use_source_bindings'); record = next((b for b in sheet['xmfa_bindings'] if b['document_id']==document['document_id']), None)
            kwargs['bindings'] = record['bindings'] if use and record else None
            if use:
                extra = deepcopy(record['requirements']) if record else [c.need(analysis_id,request['request_id'],'msa_full_xmfa_binding_required')]
        if 'cells' in kwargs:
            kwargs['cells']=tuple(kwargs['cells'])
        if 'queries' in kwargs:
            kwargs['queries']=tuple(kwargs['queries'])
        if 'selected_pairs' in kwargs:
            kwargs['selected_pairs']=tuple(tuple(p) for p in kwargs['selected_pairs'])
        function = {'xmfa_column_coordinates':coordinates.xmfa_column_coordinates,'xmfa_source_positions':coordinates.xmfa_source_positions,
            'xmfa_alignment_components':xmfa.xmfa_alignment_components,'xmfa_interval_coverage':xmfa.xmfa_interval_coverage}[kind]
        return function(document, **kwargs), extra
    if kind == 'relationship_comparison':
        gene = _required(c.lookup_tree(sheet, request['gene_tree_id']), 'alignment_calculation_dependency_unavailable')
        org = _required(c.lookup_tree(sheet, request['organismal_tree_id']), 'alignment_calculation_dependency_unavailable')
        return shared.compare_unrooted_relationships(gene, comparison_id=request['comparison_id'], organismal_tree=org, injective_tip_join=tuple(request['injective_tip_join'])), extra
    if kind == 'ungapped_map':
        alignment = _required(c.lookup_alignment(sheet, request['alignment_id']))
        return list(shared.ungapped_coordinate_map(alignment,row_indices=tuple(request['row_indices']))), extra
    population_kind = {'function_composition':'composition','taxonomy':'taxonomy','tree':'leaves'}.get(kind,'alignments')
    population = _required(c.lookup_population(sheet,population_kind,kwargs.pop('population_id')),'alignment_calculation_dependency_unavailable')
    if kind in ('function_composition','taxonomy'):
        subjects = population['member_subjects']
        if kind == 'function_composition':
            return shared.function_composition(population=population,assignments=tuple(a for a in sheet['associations']['functions'] if a['subject'] in subjects),equivalences=tuple(sheet['associations']['function_equivalences'])),extra
        return shared.taxon_components(population=population,rank=request['rank'],assignments=tuple(a for a in sheet['associations']['taxonomy'] if a['subject'] in subjects)),extra
    if kind == 'tree':
        tree = _required(c.lookup_tree(sheet,population['tree_id']))
        return shared.tree_components(tree,leaf_population=population,support_observations=tuple(s for s in sheet['support_observations'] if s['tree_id']==tree['tree_id']),
            native_measurements=tuple(s for s in sheet['native_tree_measurements'] if s['population_id']==tree['tree_id']),branch_unit=request['branch_unit'],pairs=tuple(tuple(p) for p in request['pairs'])),extra
    alignment = _required(c.lookup_alignment(sheet,population['alignment_id'])); kwargs['population']=population
    if kind == 'alignment':
        kwargs['pairs']=tuple(tuple(p) for p in kwargs['pairs'])
        return shared.alignment_components(alignment,**kwargs),extra
    if kind == 'original_coverage':
        members = _required(c.coverage_operands(sheet,population),'original_member_occurrence_ambiguous')
        return shared.original_member_coverage(alignment,population=population,members=tuple(members),correspondences=tuple(r for r in sheet['associations']['correspondences'] if r['alignment_id']==alignment['alignment_id'] and r['row_index'] in population['row_indices'])),extra
    kwargs['analysis_id']=analysis_id
    if kind == 'msa_entropy':
        table_id=kwargs.pop('observed_table_id'); table=c.lookup_document(sheet,table_id,'msa_frequency')
        if table_id is not None and table is None:
            extra.append(c.need(analysis_id,request['request_id'],'alignment_document_unavailable',kind='output_bytes'))
        kwargs['observed_table']=table
        return native.msa_native_entropy(alignment,**kwargs),extra
    if sheet['analysis']['reference'] is None:
        raise _Missing('msa_reference_unresolved')
    kwargs['reference']=c.effective_reference(sheet,request['reference'])
    kwargs['member_row_indices']=tuple(kwargs['member_row_indices'])
    # Shared MemberRef cannot express concatenated originals or repeated occurrences.
    usable_rows=[]
    for row in alignment['rows']:
        single={**population,'row_indices':[row['row_index']]}
        if c.coverage_operands(sheet,single) is not None:
            usable_rows.append(row['row_index'])
    kwargs['original_correspondences']=tuple(r for r in sheet['associations']['correspondences'] if r['alignment_id']==alignment['alignment_id'] and r['row_index'] in usable_rows)
    return native.msa_reference_differences(alignment,**kwargs),extra


def calculate_msa(sheet: dict, parameters: dict) -> dict:
    sheet=c.validate_msa_sheet(sheet); parameters=c.validate_msa_parameters(parameters)
    outcomes=[]
    for index,request in enumerate(parameters['requests']):
        outcome={'request_id':request['request_id'],'kind':request['kind'],'status':'ok','value':None,'requirements':[],'diagnostics':[]}
        try:
            value,extra=_dispatch(sheet,request); outcome['value']=value
            if request['kind'] in c.COMMON_KINDS | {'tree','relationship_comparison'}:
                outcome['requirements']=c.merge_reports(shared.calculation_requirements(value) if type(value) is dict else [],extra)
                outcome['diagnostics']=deepcopy(value.get('diagnostics',[])) if type(value) is dict else []
            else:
                outcome['requirements']=c.merge_reports(value['requirements'],extra); outcome['diagnostics']=deepcopy(value['diagnostics'])
            outcome['status']='partial' if outcome['requirements'] or outcome['diagnostics'] else 'ok'
        except _Missing as exc:
            outcome.update(status='partial',value=None,requirements=[c.need(sheet['analysis']['analysis_id'],request['request_id'],exc.reason)])
        except ValueError as exc:
            # Preserve a finite specific failure while retaining other requests.
            code=str(exc) if str(exc).replace('_','').isalnum() else 'alignment_calculation_invalid'
            outcome.update(status='invalid',value=None,requirements=[c.need(sheet['analysis']['analysis_id'],request['request_id'],code)],diagnostics=[diagnostic(code,path='/requests/'+str(index),severity='error')])
        outcomes.append(outcome)
    result={'schema_version':c.VERSION,'analysis_id':sheet['analysis']['analysis_id'],'parameters':parameters,'results':outcomes,
        'requirements':c.merge_reports(*(o['requirements'] for o in outcomes)),'diagnostics':c.merge_reports(*(o['diagnostics'] for o in outcomes))}
    return c.validate_msa_components(result,sheet=sheet)


__all__=['calculate_msa']
