"""Automatic per-measurement attribution for genomic context evidence.

Measured loci remain their actual source loci. A target sequence's homology
score is never an A103 association score, nor an axis-wide transfer coefficient.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import json
import math

from .a103_publication import received_measurement, binding_body
from .a103_scoring import VERSION, PROFILE, digest, require
from .domain import canonical
from .sequence_attribution import sequence_link
from .tool_grading_artifacts import retain_tool_grading, source_tool_grading_entries


PROVIDER = 'native.a103.tool_attachment'


def install(store):
    store.db.execute('''CREATE TABLE IF NOT EXISTS a103_attachments (
        source_ref TEXT PRIMARY KEY, measurement_ref TEXT NOT NULL,
        target_ref TEXT NOT NULL, policy TEXT NOT NULL, body TEXT NOT NULL,
        grading_artifact_ref TEXT NOT NULL)''')


def _sequence(store, ref):
    row = store.get(ref)
    if row['record_type']=='feature':
        require(row['strand']!='-','a103_protein_feature_orientation_invalid')
        parent = _sequence(store,row['subject_ref'])
        return ''.join(parent[p['start']:p['end']] for p in row['segments'])
    require(row.get('sequence_ref') is not None, 'a103_actual_component_sequence_required')
    return store.get_artifact(row['sequence_ref']).decode('ascii').strip().upper()


def _component_link(store, actual_ref, component_ref, known, *, positions=None, alignment_ref=None):
    """Identify the actual measured component, optionally at a local domain."""
    if actual_ref not in known or component_ref not in known:
        return {'state':'unresolved','factor':None,'missing':['received_specific_component_sequences'],'pairs':[]}
    actual, expected = _sequence(store,actual_ref),_sequence(store,component_ref)
    selected = list(range(len(actual))) if positions is None else list(positions)
    require(selected and all(0<=p<len(actual) for p in selected), 'a103_component_scope_invalid')
    local = ''.join(actual[p] for p in selected)
    if local == expected:
        return {'state':'evaluated','factor':1.,'identity_distance':0.,'coverage':1.,
            'route':'exact_received_sequence_and_region_identity','missing':[],
            'pairs':[[p,j,actual[p],expected[j],1.] for j,p in enumerate(selected)],
            'evidence_refs':[actual_ref,component_ref]}
    link = sequence_link(store,actual_ref,expected,known,alignment_ref=alignment_ref)
    if link['state']=='unresolved':
        aliases = set()
        for ref in known:
            row = store.get(ref)
            if row['record_type']=='observation' and row.get('origin')=='tool' and row.get('kind')=='alignment':
                aliases.update(subject for subject in row['subject_refs'] if subject in known and subject!=actual_ref)
        for alias in sorted(aliases):
            if store.subject_molecule(alias)!='protein':continue
            try: equal = _sequence(store,alias)==actual
            except (ValueError,KeyError):equal=False
            if not equal:continue
            candidate = sequence_link(store,alias,expected,known,alignment_ref=alignment_ref)
            if candidate['state']=='evaluated':
                link = {**candidate,'exact_query_alias_ref':alias,
                    'query_alias_qualification':'complete_received_protein_strings_identical; native_positions_and_statistics_reused'}
                break
    if link['state']=='unresolved' and not link.get('witnesses') and store.get(component_ref).get('sequence_ref'):
        reverse = sequence_link(store,component_ref,actual,known,alignment_ref=alignment_ref)
        if reverse.get('witnesses'):
            # A family query can have searched the observed CDS. Invert only
            # the correspondence; native scores remain in their real direction.
            link = {**reverse,'target_ref':actual_ref,'reference_sequence_sha256':digest(expected),
                'route':'inverted_received_native_residue_correspondence',
                'native_statistics_direction':{'query_ref':component_ref,'reference_sequence_ref':actual_ref},
                'pairs':[[j,i,b,a,strength] for i,j,a,b,strength in reverse.get('pairs',[])],
                'conflicting_target_positions':reverse.get('conflicting_reference_positions',[]),
                'conflicting_reference_positions':reverse.get('conflicting_target_positions',[])}
    cells = [p for p in link.get('pairs',[]) if p[0] in set(selected)]
    ambiguous = set(link.get('conflicting_target_positions',[])) & set(selected)
    if not cells or ambiguous:
        return {**link,'factor':None,'missing':link['missing'] or ['native_map_in_required_component_region']}
    factor = math.fsum((a==b)*strength for _,_,a,b,strength in cells)/max(len(selected),len(expected))
    return {**link,'state':'evaluated','missing':[], 'factor':factor,
        'identity_distance':sum(a!=b for _,_,a,b,_ in cells)/len(cells),
        'coverage':len(cells)/max(len(selected),len(expected)), 'pairs':cells,
        'evidence_refs':sorted({actual_ref,component_ref,*[r[k] for r in link.get('witnesses',[])
            for k in ('observation_ref','source_ref','reference_ref')],
            *([link['exact_query_alias_ref']] if link.get('exact_query_alias_ref') else [])})}


def component_link(store,actual_ref,component_ref,known,*,positions=None,alignment_ref=None):
    link = _component_link(store,actual_ref,component_ref,known,positions=positions,alignment_ref=alignment_ref)
    return {'actual_subject_ref':actual_ref,'reference_subject_ref':component_ref,
        'functional_property':'unestablished_by_sequence_correspondence_alone',**link}


def target_link(store, target, binding, known, *, alignment_ref=None):
    """Keep actual target locus and inferred reference organization distinct."""
    actual = binding.get('protein_reference_ref')
    if binding['selection_status']!='selected':
        return {'state':'unresolved','factor':None,'missing':['actual_unambiguous_cds_translation'],'pairs':[]}
    placement = binding.get('native_input_placement')
    material = binding.get('material_ref',target)
    molecule = store.subject_molecule(material)
    if molecule!='protein':
        good = placement and placement['state']=='unique' and placement['molecule'] in {'dna','rna'}
        return {'state':'evaluated' if good else 'unresolved','factor':1. if good else None,
            'missing':[] if good else ['protein_product_or_original_genomic_placement'],'pairs':[],
            'locus_application':'actual_nucleotide_placement_in_received_genomic_source',
            'target_organism_inferred':False,'native_placement':placement}
    if actual is None:
        return {'state':'unresolved','factor':None,'missing':['actual_verified_cds_translation'],'pairs':[]}
    if placement and placement['state']=='ambiguous' and binding.get('supplied_target_genome'):
        return {'state':'unresolved','factor':None,'missing':['actual_target_locus_or_fragment_placement_disambiguation'],
            'pairs':[],'native_placement':placement,'target_organism_inferred':False,
            'locus_application':'ambiguous_supplied_target_placement'}
    if (placement and placement['state']=='unique' and placement['molecule']=='protein'
            and placement['placements'][0]['feature_index']==binding['locus']['source_feature_index']):
        p = placement['placements'][0]
        query = _sequence(store,material)
        reference = _sequence(store,actual)
        link = {'state':'evaluated','factor':1.,'identity_distance':0.,'coverage':1.,'missing':[],
            'route':'native_exact_input_placement_in_acquired_cds_inventory',
            'pairs':[[i,p['reference_start']+i,a,reference[p['reference_start']+i],1.] for i,a in enumerate(query)],
            'evidence_refs':[material,actual]}
    else:
        # A verified native fragment placement already supplies its map. In
        # particular, a local feature need not pretend to have a sequence file.
        link = component_link(store,material,actual,known,alignment_ref=alignment_ref)
    if material!=target and link.get('pairs'):
        mapping = store.sequence_mapping(material)
        scale = mapping['units_per_symbol']
        require(scale in {1,3} and {p['subject_ref'] for p in mapping['path']}=={target},
                'a103_original_material_positions_required')
        lift = [p for row in mapping['path'] for p in
            (range(row['end']-1,row['start']-1,-1) if row['strand']=='-' else range(row['start'],row['end']))]
        if scale==1:
            link['pairs'] = [[lift[i],j,a,b,strength] for i,j,a,b,strength in link['pairs']]
            link['pair_coordinate_unit'] = 'original_target_amino_acid'
        else:
            link['protein_to_target_positions'] = {str(j):lift[3*i:3*i+3] for i,j,_,_,_ in link['pairs']}
            link['pair_coordinate_unit'] = 'material_amino_acid_with_explicit_original_nucleotide_codons'
            link['original_target_unit'] = 'nt'
            link['original_target_strands'] = sorted({r['strand'] for r in mapping['path']})
    link['locus_application'] = ('supplied_target_genomic_provenance' if binding.get('supplied_target_genome')
        and link.get('identity_distance')==0 else 'inferred_reference_locus_context')
    link['target_organism_inferred'] = False
    return link


def _publish(store, measurement_ref, body, refs):
    body = {'schema':'a103_tool_attachment_v1','version':VERSION,'profile':PROFILE,
        'measurement_ref':measurement_ref, **deepcopy(body), 'evidence_refs':sorted(set(refs))}
    with store.transaction():
        artifact = store.artifact(canonical(body),'application/json')
        grade = retain_tool_grading(store,provider=PROVIDER,native_artifact_ref=artifact,
            grading={'grader':VERSION,'failure':None,'sheet':body})
        operands = [r for r in body['evidence_refs'] if store.get(r)['record_type'] in
            {'input','reference','read_subject','feature','product'}]
        ref = store.put('source',{'provider':PROVIDER,'accession':digest(body),'uri':None,
            'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,'version':VERSION,
            'retrieved_at':None,'operand_refs':operands,'auxiliary_artifact_refs':[grade]},origin='tool')['id']
        store.db.execute('INSERT OR IGNORE INTO a103_attachments VALUES(?,?,?,?,?,?)',
            (ref,measurement_ref,body['target_ref'],body['policy'],canonical(body),grade))
    return ref


def received_attachments(store, known):
    exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='a103_attachments'").fetchone()
    if not exists:
        return []
    known = set(known)
    latest = {}
    for row in store.db.execute('SELECT rowid,* FROM a103_attachments ORDER BY rowid'):
        if row['source_ref'] not in known:
            continue
        source = store.get(row['source_ref'])
        body = json.loads(row['body'])
        entries = source_tool_grading_entries(store,row['source_ref'])
        require(source['origin']=='tool' and source.get('provider')==PROVIDER and source['version']==VERSION
            and json.loads(store.get_artifact(source['artifact_ref']))==body and len(entries)==1
            and entries[0]['artifact_ref']==row['grading_artifact_ref']
            and entries[0]['grading']=={'grader':VERSION,'failure':None,'sheet':body}, 'a103_attachment_custody_conflict')
        latest[(row['measurement_ref'],row['policy'])] = {
            'source_ref':row['source_ref'],'grading_artifact_ref':row['grading_artifact_ref'],**body}
    return list(latest.values())


def _witnesses(link):
    return list(link.get('evidence_refs',[])) + [r[k] for r in link.get('witnesses',[])
        for k in ('observation_ref','source_ref','reference_ref')]


def _scoped_partner_detection(store, body, neighborhood_ref, known):
    """Join received detector receipts to this exact use, including late ones."""
    receipts = []
    for ref in sorted(known):
        source = store.get(ref)
        if source['record_type']!='source' or source.get('provider')!='native.a103.measurement':
            continue
        result = received_measurement(store,ref)
        proof = result['body']
        if (proof['schema']!='a103_detection_v1' or proof['target_ref']!=body['target_ref']
                or proof.get('neighborhood_ref')!=neighborhood_ref):
            continue
        actual,required=proof['component_ref'],body['partner_reference_ref']
        alias=actual!=required
        if alias and (not {actual,required}<=set(known) or _sequence(store,actual)!=_sequence(store,required)):
            continue
        usable = proof.get('native_search_complete') is True and (
            proof.get('present') is True or
            proof.get('present') is False and proof.get('all_actual_cds_in_search') is True)
        if usable:
            receipts.append((ref,proof,{'detection_ref':ref,'actual_query_ref':actual,'required_query_ref':required,
                'route':'exact_received_query_peptide_identity' if alias else 'same_query_reference',
                'identity_distance':0.}))
    states = {proof['present'] for _,proof,_ in receipts}
    return {'present':next(iter(states)) if len(states)==1 else None,
        'conflicting_calls':len(states)>1,
        'evidence_refs':list(dict.fromkeys([ref for ref,_,_ in receipts]+[
            subject for _,_,link in receipts if link['route']=='exact_received_query_peptide_identity'
            for subject in (link['actual_query_ref'],link['required_query_ref'])])),
        'query_bindings':[link for _,_,link in receipts],
        'absence_scopes':[proof['scope'] for _,proof,_ in receipts if proof['present'] is False]}


def _recurrence(store, body, known):
    cells = []
    refs = []
    missing = []
    required_operands = []
    for row in body['rows']:
        match = row['relationship_holds']
        if row['neighborhood_ref'] not in known:
            link = {'state':'unresolved','factor':None,'missing':['actual_neighborhood_measurement'],'pairs':[]}
            partner = {'state':'unresolved','factor':None,'missing':[]}
        else:
            sheet = received_measurement(store,row['neighborhood_ref'])['body']
            require(sheet['binding_ref'] in known,'a103_context_anchor_binding_not_received')
            binding = binding_body(store,sheet['binding_ref'],known)
            # The selected left component can differ from the original focal CDS.
            left = next(c for c in sheet['cds'] if c['source_feature_index']==row['left_feature_index'])
            focal = {**binding,'protein_reference_ref':left.get('protein_reference_ref'),
                'native_input_placement':binding.get('native_input_placement')
                    if row['left_feature_index']==binding['locus']['source_feature_index'] else None}
            link = target_link(store,body['target_ref'],focal,known)
            detection = _scoped_partner_detection(store,body,row['neighborhood_ref'],known)
            refs.extend(detection['evidence_refs'])
            if row['right_feature_index'] is None:
                partner = {'state':'unresolved','factor':None,'missing':[
                    'actual_partner_footprint_for_relationship' if detection['present'] is True
                    else 'complete_scoped_partner_detection']}
            else:
                right = next(c for c in sheet['cds'] if c['source_feature_index']==row['right_feature_index'])
                partner = component_link(store,right.get('protein_reference_ref'),body['partner_reference_ref'],known)
            refs.extend(_witnesses(partner))
            identity_conflict = (detection['present'] is False and partner.get('factor') is not None
                and partner['factor']>0)
            if detection['conflicting_calls'] or identity_conflict:
                partner = {'state':'unresolved','factor':None,
                    'missing':['conflicting_specific_component_detection'],
                    'component_correspondence':partner,'detection':detection}
                match = None
            elif detection['present'] is False:
                # A search of the complete local inventory can rule out the
                # named family. It does not erase an unrelated pair's geometry.
                partner = {'state':'evaluated_nondetection','factor':1.,'missing':[],
                    'evidence_refs':detection['evidence_refs'],'absence_scopes':detection['absence_scopes'],
                    'query_bindings':detection['query_bindings'],
                    'scope':'exact_received_neighborhood_CDS_inventory_only'}
                match = False
            if partner['missing']:
                required_operands.append({'use':'partner_in_exact_neighborhood',
                    'query_ref':body['partner_reference_ref'],'neighborhood_ref':row['neighborhood_ref'],
                    'actual_component_ref':right.get('protein_reference_ref')
                        if row['right_feature_index'] is not None else None,
                    'missing':partner['missing']})
            refs.extend([row['neighborhood_ref'],sheet['binding_ref'],*_witnesses(link),*_witnesses(partner)])
        factors = (link.get('factor'),partner.get('factor'))
        factor = min(factors) if all(v is not None for v in factors) else None
        value = float(match)*factor if match is not None and factor is not None else None
        if match is None: missing.append('actual_relationship_geometry_or_scoped_nondetection')
        missing.extend(link['missing']); missing.extend(partner['missing'])
        cells.append({'locus_measurement_key':row['locus_measurement_key'],'sampling_group':row['sampling_group'],
            'genome_key':row.get('genome_key',row['locus_measurement_key']),
            'raw_relationship_holds':row['relationship_holds'],'relationship_holds':match,
            'qualified_value':value,'target_link':link,'partner_link':partner,
            'organization':row['organization']})
    groups = defaultdict(lambda:defaultdict(list))
    for row in cells:
        groups[row['sampling_group']][row['genome_key']].append(row['qualified_value'])
    def bound(unknown):
        return math.fsum(math.fsum(math.fsum(unknown if v is None else v for v in values)/len(values)
            for values in genomes.values())/len(genomes) for genomes in groups.values())/len(groups) if groups else unknown
    lower,upper = bound(0.),bound(1.)
    return {'policy':'recurrence_specific_loci_components_and_sampling_v1','level':'context_relationship',
        'state':'partial' if missing else 'evaluated','score':lower,'bounds':[lower,upper],
        'raw_value':body['group_balanced_fraction'],'rows':cells,'missing':sorted(set(missing)),
        'required_operands':required_operands,
        'sampling_group_count':len(groups),'dependency_group':body['comparison_group'],
        'variant':body['comparison_variant'],
        'interpretation':'qualified_conservation_of_measured_arrangement; exact_chemistry_and_partner_necessity_unestablished'},refs


def _fusion(store, body, known):
    binding = binding_body(store,body['binding_ref'],known)
    target = target_link(store,body['target_ref'],binding,known)
    regions = []
    refs = [body['binding_ref'],*_witnesses(target)]
    missing = list(target['missing'])
    features = []
    for region in body['regions']:
        link = component_link(store,binding.get('protein_reference_ref'),region['component_ref'],known,
            positions=range(region['start'],region['end']),alignment_ref=region.get('alignment_ref'))
        missing.extend(link['missing']); refs.extend(_witnesses(link))
        # Lift each measured fusion subpart into actual original target positions.
        if target.get('protein_to_target_positions') is not None:
            positions = sorted({p for j,values in target['protein_to_target_positions'].items()
                if region['start']<=int(j)<region['end'] for p in values})
        else:
            positions = sorted({r[0] for r in target.get('pairs',[]) if region['start']<=r[1]<region['end']})
        feature = None
        if positions:
            feature = store.put('feature',{'subject_ref':body['target_ref'],'kind':'sequence_region',
                'segments':[{'start':p,'end':p+1} for p in positions],'strand':'.','context_refs':[]},origin='tool')['id']
            features.append(feature)
        regions.append({**region,'component_attribution':link,'target_positions':positions,'target_feature_ref':feature})
    factors = [target.get('factor'),*[r['component_attribution'].get('factor') for r in regions]]
    value = min(factors) if all(v is not None for v in factors) else None
    return {'policy':'fusion_each_required_region_and_actual_coding_product_v1','level':'feature_trait',
        'state':'evaluated' if value is not None else 'unresolved','score':value,
        'raw_value':body['observed_link_fraction'],'bounds':[value,value] if value is not None else [0.,1.],
        'target_link':target,'regions':regions,'missing':sorted(set(missing)),
        'dependency_group':body['comparison_group'],'variant':body['comparison_variant'],
        'interpretation':'attributed_domain_linkage; whole_protein_function_requires_explicit_interpretation'},[*refs,*features],features


def _contrast(store,body,known):
    selected = [*body['supporting_source_refs'],*body['opposing_source_refs']]
    grades = {r['measurement_ref']:r for r in received_attachments(store,known)}
    missing = []
    if not body['supporting_source_refs']:missing.append('supporting_context_comparison')
    if not body['opposing_source_refs']:missing.append('opposing_context_comparison')
    if any(r not in grades or grades[r]['score'] is None for r in selected):
        missing.append('qualified_context_for_each_selected_comparison')
    policies = {grades[r]['policy'] for r in selected if r in grades}
    scopes = {canonical(grades[r]['target_regions']) for r in selected if r in grades}
    if len(policies)>1 or len(scopes)>1:missing.append('matched_native_route_and_original_scope')
    supporting = [grades[r] for r in body['supporting_source_refs'] if r in grades and grades[r]['score'] is not None]
    opposing = [grades[r] for r in body['opposing_source_refs'] if r in grades and grades[r]['score'] is not None]
    def bounds(rows):
        return [max((r.get('bounds',[r['score'],r['score']])[i] for r in rows),default=0. if i==0 else 1.) for i in (0,1)]
    sb,ob = bounds(supporting),bounds(opposing)
    interval = [max(0.,sb[0]-ob[1]),max(0.,sb[1]-ob[0])]
    value = max(0.,max((r['score'] for r in supporting),default=0.)-
        max((r['score'] for r in opposing),default=0.)) if not missing else None
    refs = [*selected,*body['incompatibility_witness_refs'],body['function_ref'],
            *[grades[r]['source_ref'] for r in selected if r in grades]]
    return {'policy':'functional_contrast_matched_native_context_and_bounds_v1','level':'functional_interpretation',
        'score':None,'raw_value':None,'state':'unresolved' if missing else 'evaluated',
        'missing':missing,'qualified_panel':{'supporting_context_bounds':sb,'opposing_context_bounds':ob,
            'contrast':value,'contrast_bounds':interval,'comparison_state':'incomparable_or_unresolved' if missing else
                'discriminating_index' if interval[0]>0 else 'not_established_discriminating',
            'interpretation':'descriptive_qualified_association_index_difference; not_function_probability'},
        'interpretation':'explicit_context_contrast_with_no_additional_controller_credit'},refs


def refresh(store, known, scope):
    """Receipt/publication callback; credit reads never execute this function."""
    install(store)
    known = set(known)
    generated, needs = [],[]
    contrasts = []
    admitted = {r['measurement_ref']:r for r in received_attachments(store,known)}
    targets = set(scope['subject_refs'])
    for ref in sorted(known):
        result = received_measurement(store,ref)
        if result is None or result['body']['target_ref'] not in targets:
            continue
        body, native = result['body'],result['grade']
        if ref in admitted and not set(admitted[ref]['evidence_refs'])<=known:
            # The admitted sheet is a valid narrow numerical grant. A receiver
            # lacking private upstream operands cannot regrade it as missing.
            continue
        kind = native['kind']
        if kind=='functional_contrast':
            contrasts.append((ref,body))
            continue
        refs = [ref,body['target_ref']]
        if kind=='locus_binding':
            binding = binding_body(store,ref,known)
            link = target_link(store,body['target_ref'],binding,known)
            out = {'policy':'actual_cds_to_target_entity_binding_v1','level':'entity','state':link['state'],
                'score':None,'raw_value':None,'target_link':link,'missing':link['missing'],
                'interpretation':'locus_binding_not_a_context_association'}
            refs.extend(_witnesses(link))
        elif kind=='organization':
            if body['binding_ref'] not in known:
                continue
            binding = binding_body(store,body['binding_ref'],known)
            link = target_link(store,body['target_ref'],binding,known)
            out = {'policy':'actual_neighborhood_and_specific_target_locus_v1','level':'context_relationship',
                'state':link['state'],'score':None,'raw_value':None,'target_link':link,'missing':link['missing'],
                'interpretation':'measured_organization_requires_explicit_comparative_association_for_controller_credit'}
            refs.extend([body['binding_ref'],*_witnesses(link)])
        elif kind=='recurrence':
            out,more = _recurrence(store,body,known); refs.extend(more)
        elif kind=='fusion':
            if body['binding_ref'] not in known:
                continue
            out,more,features = _fusion(store,body,known); refs.extend(more); generated.extend(features)
        elif kind=='cooccurrence':
            target_correspondence = component_link(store,body['target_ref'],body['left_reference_ref'],known)
            factor = target_correspondence.get('factor')
            value = native['raw_value']*factor if native['raw_value'] is not None and factor is not None else None
            out = {'policy':'enumerated_panel_actual_detections_and_declared_null_v1','level':'context_relationship',
                'state':'evaluated' if value is not None else 'unresolved',
                'score':value,'raw_value':native['raw_value'],'target_link':target_correspondence,
                'missing':sorted(set(target_correspondence['missing']) | (set() if native['raw_value'] is not None
                    else {'evaluable_independent_detections_for_both_components'})),
                'contingency':body['contingency'],'risk_difference':body['risk_difference'],
                'p_value':body['p_value'],'detection_scope':body['detection_scope'],
                'dependency_group':body['comparison_group'],'variant':body['comparison_variant'],
                'interpretation':body['interpretation']}
            refs.extend([*body['detection_refs'],body['left_reference_ref'],body['right_reference_ref'],*_witnesses(target_correspondence)])
        elif kind=='native_channel':
            from .a103_channels import native_endpoint_binding
            endpoints_bound = all((native_endpoint_binding(store,body['left_reference_ref'],body['left_native_id'],known),
                native_endpoint_binding(store,body['right_actual_ref'],body['right_native_id'],known)))
            links = [component_link(store,body['target_ref'],body['left_reference_ref'],known),
                component_link(store,body['right_actual_ref'],body['right_reference_ref'],known)]
            factors = [l.get('factor') for l in links]
            factor = min(factors) if endpoints_bound and all(v is not None for v in factors) else None
            out = {'policy':'native_channel_exact_endpoints_and_specific_distance_v1','level':'context_relationship',
                'state':'evaluated' if factor is not None else 'unresolved',
                'score':native['raw_value']*factor if factor is not None else None,
                'raw_value':native['raw_value'],'channel':body['channel'],'endpoint_links':links,
                'missing':sorted({m for l in links for m in l['missing']} |
                    (set() if endpoints_bound else {'native_endpoint_to_canonical_sequence_identity'})),
                'dependency_group':body['comparison_group'],'variant':body['comparison_variant'],
                'interpretation':'native_context_channel_with_its_actual_endpoint_attribution'}
            refs.extend([body['source_ref'],body['left_reference_ref'],body['right_actual_ref'],body['right_reference_ref']])
            for link in links: refs.extend(_witnesses(link))
        else:
            continue
        out.update(target_ref=body['target_ref'],producer_operation=body['producer_operation'],
            target_regions=body['target_regions'],actual_measured_subjects=body.get('actual_measured_subjects',[]))
        attachment_ref = _publish(store,ref,out,refs)
        generated.append(attachment_ref)
        if out.get('score') is not None:
            observation = store.put('observation',{'subject_refs':[body['target_ref']],
                'source_subject_refs':[], 'kind':'context','source_ref':attachment_ref,
                'measurements':[{'name':'context_association_index','value':{'type':'number','value':out['score'],'unit_ref':None}}],
                'dependencies':[ref],'anchor':None},origin='tool')['id']
            generated.append(observation)
            if kind=='fusion':
                for region in out['regions']:
                    if region['target_feature_ref'] is None or region['component_attribution'].get('factor') is None:continue
                    local = store.put('observation',{'subject_refs':[region['target_feature_ref']],
                        'source_subject_refs':[region['component_ref']], 'kind':'context','source_ref':attachment_ref,
                        'measurements':[{'name':'context_association_index','value':{'type':'number',
                            'value':region['component_attribution']['factor'],'unit_ref':None}}],
                        'dependencies':[ref],'anchor':None},origin='tool')['id']
                    generated.append(local)
        if out['missing']:
            needs.append((ref,out))
    for ref,body in contrasts:
        refs = [*body['supporting_source_refs'],*body['opposing_source_refs'],*body['incompatibility_witness_refs'],body['function_ref']]
        if not set(refs)<=known:continue
        out,dependencies = _contrast(store,body,known|set(generated))
        out.update(target_ref=body['target_ref'],producer_operation=body['producer_operation'],
            target_regions=body['target_regions'],actual_measured_subjects=[])
        generated.append(_publish(store,ref,out,[ref,body['target_ref'],*dependencies]))
        if out['missing']:needs.append((ref,out))
    return list(dict.fromkeys(generated)),needs
