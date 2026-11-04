"""Automatic, measurement-specific entity and feature/trait attribution.

Policies are selected by actual producers and result kinds. Raw geometry is
immutable; borrowed observations have explicit subjects, maps and local traits.
No axis-wide coefficient or model-selected grading route exists.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math

from .a102_publication import received_grade
from .a102_scoring import digest, geometry, require,contrast_panel
from .a102_structures import binding_summary
from .domain import canonical
from .sequence_attribution import sequence_link, scoped_distance
from .tool_grading_artifacts import retain_tool_grading, source_tool_grading_entries


VERSION = 'measurement_entity_and_trait_attribution_v1'
PROVIDER = 'native.a102.tool_attachment'
REQUEST_PROVIDER = 'native.a102.attachment_request'
CHEMICAL_ROLES = {'acidic': 'DE', 'basic_KR': 'KR', 'aromatic': 'FWY',
    'hydroxyl': 'STY', 'amide': 'NQ', 'sulfur': 'CM', 'small': 'AGS'}
DIRECT_PRODUCERS = {'US-align': 'structure.align', 'Foldseek': 'structure.discover',
    'compare_protein_structures': 'compare_protein_structures'}


def install(store):
    for sql in (
        'CREATE TABLE IF NOT EXISTS a102_attachment_requests (source_ref TEXT PRIMARY KEY, body TEXT NOT NULL)',
        '''CREATE TABLE IF NOT EXISTS a102_tool_attachments (source_ref TEXT PRIMARY KEY,
            request_ref TEXT NOT NULL, measurement_ref TEXT, target_ref TEXT NOT NULL,
            policy TEXT NOT NULL, grading_artifact_ref TEXT NOT NULL, body TEXT NOT NULL)''',
    ): store.db.execute(sql)


def _source(store, provider, body, refs, *, grading=None):
    artifact = store.artifact(canonical(body), 'application/json')
    operands=[ref for ref in sorted(set(refs)) if store.get(ref)['record_type'] in {'input','reference','read_subject','feature','product'}]
    return store.put('source', {'provider': provider, 'accession': digest(body), 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': VERSION,
        'retrieved_at': None, 'operand_refs': operands,
        **({'auxiliary_artifact_refs': [grading]} if grading else {})}, origin='tool')['id']


def request(store, body, refs):
    install(store)
    body = {'version': VERSION, **deepcopy(body)}
    ref = _source(store, REQUEST_PROVIDER, body, refs)
    store.db.execute('INSERT OR IGNORE INTO a102_attachment_requests VALUES(?,?)', (ref, canonical(body)))
    return ref


def _binding(store, ref, known):
    require(ref in known, 'attachment_binding_not_received')
    row = store.db.execute('SELECT body FROM a102_structure_bindings WHERE source_ref=?', (ref,)).fetchone()
    source = store.get(ref)
    require(row is not None and source['origin']=='tool' and source['provider']=='native.a102.structure_binding',
        'attachment_binding_custody_unavailable')
    body = json.loads(row[0])
    require(json.loads(store.get_artifact(source['artifact_ref'])) == binding_summary(body), 'attachment_binding_custody_conflict')
    return body


def _dependencies(link):
    return sorted({ref for row in link.get('witnesses', []) for key,ref in row.items()
        if key in {'observation_ref', 'source_ref', 'reference_ref'}} |
        set(link.get('candidate_observation_refs', [])))


def _publish(store, key, body, refs):
    body = {'schema': 'a102_tool_attachment_v1', 'version': VERSION,
        'request_ref': key, **body, 'evidence_refs': sorted(set(refs))}
    artifact = store.artifact(canonical(body),'application/json')
    grading = retain_tool_grading(store, provider=PROVIDER,
        native_artifact_ref=artifact,
        grading={'grader': VERSION, 'failure': None, 'sheet': body})
    source = _source(store, PROVIDER, body, refs, grading=grading)
    store.db.execute('INSERT OR IGNORE INTO a102_tool_attachments VALUES(?,?,?,?,?,?,?)',
        (source,key,body.get('measurement_ref'),body['target_ref'],body['policy'],grading,canonical(body)))
    return source


def received_attachments(store, known):
    """Only actual admitted sheets; reading credit never creates a grade."""
    exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='a102_tool_attachments'").fetchone()
    if not exists: return []
    known = set(known); latest = {}
    for row in store.db.execute('SELECT rowid,* FROM a102_tool_attachments ORDER BY rowid'):
        if row['source_ref'] not in known: continue
        source = store.get(row['source_ref']); body = json.loads(row['body'])
        entries = source_tool_grading_entries(store,row['source_ref'])
        require(source['origin']=='tool' and source['provider']==PROVIDER and source['version']==VERSION
            and json.loads(store.get_artifact(source['artifact_ref']))==body and len(entries)==1
            and entries[0]['artifact_ref']==row['grading_artifact_ref']
            and entries[0]['grading']=={'grader':VERSION,'failure':None,'sheet':body}, 'attachment_grade_custody_conflict')
        # This actual producer-issued Source is the narrow numerical grant.
        # Its provenance IDs do not disclose private upstream artifacts/maps.
        latest[(row['request_ref'],row['policy'],body.get('physical_feature_key'))] = {
            'source_ref':row['source_ref'],'grading_artifact_ref':row['grading_artifact_ref'],**body}
    return list(latest.values())


def _direct(store, ref, grade, known):
    q = _binding(store,grade['target_binding_ref'],known)
    t = _binding(store,grade['reference_ref'],known)
    require(q['target_ref']==grade['target_ref'], 'attachment_direct_subject_conflict')
    return {'measurement_ref':ref,'target_ref':grade['target_ref'],'policy':'direct_native_geometry_v1',
        'producer_operation':DIRECT_PRODUCERS[grade['producer']], 'level':'entity',
        'actual_subject_refs':[grade['target_binding_ref'],grade['reference_ref']],
        'state':'direct','score':grade['components']['B'],'raw_score':grade['components']['B'],
        'regions':[grade['target_scope']],'missing':[],
        'construct_changes':q['mapping_algorithm']['substitutions'],
        'entity_attribution':{'route':'authenticated_coordinate_to_supplied_sequence_binding',
            'sequence_distance_on_mapped_residues':len(q['mapping_algorithm']['substitutions'])/max(1,sum(p is not None for p in q['coordinate_to_input_mapping'])),
            'qualifier':'mapped_construct_or_model_geometry; residue-level changes require local trait checks'},
        'origin':q['model_metadata']['origin'], 'reference_origin':t['model_metadata']['origin'],
        'interpretation':'geometry_of_received_target_model_with_construct_and_origin_qualifications'}


def _fold(store, body, known):
    grade = received_grade(store,body['measurement_ref'])['grade']
    q = _binding(store,body['measured_binding_ref'],known)
    require(grade['target_binding_ref']==body['measured_binding_ref'] and q['target_ref'] is None,
        'attachment_reference_subject_conflict')
    if not grade['eligible'] or not grade['primary']:
        return {'measurement_ref':body['measurement_ref'],'target_ref':body['target_ref'],
            'policy':'reference_fold_native_map_and_local_distance_v1','producer_operation':'structure.reference_align',
            'level':'entity','actual_subject_refs':[body['measured_binding_ref'],grade['reference_ref']],
            'raw_score':grade['components']['B'],'score':None,'regions':body['regions'],
            'state':'excluded','exclusion':grade['exclusion'] or 'nonprimary_comparison',
            'mapped_geometry':[],'region_scores':[],'missing':[]},[]
    link = sequence_link(store,body['target_ref'],q['sequence'],known,
        alignment_ref=body.get('sequence_alignment_ref'))
    out = {'measurement_ref':body['measurement_ref'],'target_ref':body['target_ref'],
        'policy':'reference_fold_native_map_and_local_distance_v1','producer_operation':'structure.reference_align',
        'level':'entity','actual_subject_refs':[body['measured_binding_ref'],grade['reference_ref']],
        'raw_score':grade['components']['B'],'regions':body['regions'], 'sequence_link':link,
        'comparison_group':digest([body['target_ref'],digest(q['sequence']),
            grade.get('reference_sequence_sha256') or grade['reference_ref'],body['regions']]),
        'comparison_variant':digest([grade.get('target_coordinate_sha256'),grade.get('reference_coordinate_sha256'),link.get('pairs')]),
        'state':'evaluated_transfer' if link['state']=='evaluated' else 'unresolved',
        'missing':link['missing'], 'region_scores':[],
        'interpretation':'inferred_target_correspondence_from_reference_geometry_not_measured_target_coordinates'}
    by_reference = {r[1]:r for r in link.get('pairs', [])}
    out['reference_length']=grade['reference_length']
    out['mapped_geometry']=[[by_reference[p][0],p,z,d,float(by_reference[p][2]==by_reference[p][3]),by_reference[p][4]]
        for p,z,d in zip(grade['target_positions'],grade['reference_positions'],grade['distances_A'],strict=True)
        if p in by_reference and any(a<=by_reference[p][0]<b for a,b in body['regions'])]
    for start,end in body['regions']:
        selected = [(p,d,by_reference[p]) for p,d in zip(grade['target_positions'],grade['distances_A'],strict=True)
            if p in by_reference and start<=by_reference[p][0]<end]
        distance = scoped_distance(link,range(start,end))
        projected = geometry([d for _,d,_ in selected],end-start,grade['reference_length']) if selected else None
        # Coverage is already applied by the projected geometry denominator.
        # Local identity/native strength qualify the particular X/Y path once.
        factor = (math.fsum((a==b)*strength for _,_,a,b,strength in (row for _,_,row in selected))/len(selected)
            if selected else None)
        value = projected['B']*factor if projected is not None else None
        out['region_scores'].append({'start':start,'end':end,'value':value,
            'local_sequence_distance':distance,'projected_reference_geometry':projected,
            'applicability_factor':factor,'mapped_pair_count':len(selected)})
    values = [r['value'] for r in out['region_scores']]
    out['score'] = math.exp(math.fsum(math.log(v) for v in values)/len(values)) if values and all(v is not None and v>0 for v in values) else (0. if values and all(v is not None for v in values) else None)
    if link['state'] != 'evaluated': out['score'] = None
    if link['state']=='evaluated' and any(v is None for v in values):
        out.update(state='unresolved',missing=['native_correspondence_in_required_region'])
    return out,_dependencies(link)


def reference_region_value(attachment,start,end):
    """Recompute only declared cells at the receiving parent's denominator."""
    rows=[r for r in attachment.get('mapped_geometry',[]) if start<=r[0]<end]
    if not rows or attachment['state']=='unresolved': return None
    projected=geometry([r[3] for r in rows],end-start,attachment['reference_length'])
    factor=math.fsum(r[4]*r[5] for r in rows)/len(rows)
    return {'value':projected['B']*factor,'projected_reference_geometry':projected,
        'applicability_factor':factor,'attachment_source_ref':attachment['source_ref'],
        'actual_measurement_ref':attachment['measurement_ref'],'attribution_kind':'reference_geometry_inference'}


def qualified_feature(store,reference,body,known):
    if not body.get('attachment_required'): return body
    attachment=next((row for row in received_attachments(store,known)
        if row.get('measurement_ref')==reference and row['policy']=='feature_geometry_local_scaffold_v1'),None)
    return {**body,'raw_E':body.get('raw_E',body['E']),
        'E':attachment['E'] if attachment else None,
        'E_bounds':[attachment['E'],attachment['E']] if attachment and attachment['E'] is not None else [0.,body['B']],
        'attribution':attachment or {'state':'unresolved','missing':['local_feature_attachment_grade']}}


def _local_map(store, target, binding_ref, known, comparison_ref, alignment_ref):
    binding = _binding(store,binding_ref,known)
    if comparison_ref is not None:
        require(comparison_ref in known,'attachment_comparison_not_received')
        grade = received_grade(store,comparison_ref)['grade']
        if grade['target_ref']==target and grade['reference_ref']==binding_ref:
            q = _binding(store,grade['target_binding_ref'],known)
            sequence = store.get_artifact(store.get(target)['sequence_ref']).decode('ascii')
            result={'state':'evaluated','missing':[], 'route':'native_structural_residue_correspondence',
                'pairs':[[i,j,sequence[i],binding['sequence'][j],1.] for i,j in zip(grade['target_positions'],grade['reference_positions'],strict=True)],
                'witnesses':[], 'additional_refs':[comparison_ref,grade['target_binding_ref']],
                'structural_comparison_ref':comparison_ref,'model_origin':q['model_metadata']['origin']}
            seq=sequence_link(store,target,binding['sequence'],known,alignment_ref=alignment_ref)
            if seq['state']=='evaluated':
                by_target={row[0]:row for row in result['pairs']};inverse={row[1]:row[0] for row in result['pairs']}
                added=[];conflicts=set()
                for row in seq['pairs']:
                    i,j=row[:2]
                    if (i in by_target and by_target[i][1]!=j) or (j in inverse and inverse[j]!=i):
                        conflicts.add(j)
                        if i in by_target:conflicts.add(by_target[i][1])
                    elif i not in by_target and j not in inverse:
                        added.append(row);by_target[i]=row;inverse[j]=i
                if added or conflicts:
                    result['witnesses']=seq['witnesses']
                    result['pairs']=[row for row in [*result['pairs'],*added] if row[1] not in conflicts]
                    result['conflicting_reference_positions']=sorted(conflicts)
                    result['route']='native_structure_with_specific_sequence_site_evidence'
            return result
    return sequence_link(store,target,binding['sequence'],known,alignment_ref=alignment_ref)


def _traits(store, request_ref, body, known):
    reference = _binding(store,body['reference_binding_ref'],known)
    link = _local_map(store,body['target_ref'],body['reference_binding_ref'],known,
        body.get('comparison_source_ref'),body.get('sequence_alignment_ref'))
    regions=body.get('target_regions',[[0,store.subject_length(body['target_ref'])]])
    inverse = {row[1]:row for row in link.get('pairs',[]) if any(a<=row[0]<b for a,b in regions)}
    results = []; produced = []
    for trait in body['traits']:
        positions = trait['reference_positions']; mapped = [inverse.get(p) for p in positions]
        expected = ''.join(reference['sequence'][p] for p in positions)
        actual = ''.join(row[2] if row else '?' for row in mapped)
        allowed = ([CHEMICAL_ROLES[trait['chemical_role']]]*len(positions) if trait['chemical_role'] is not None
            else [c for c in expected] if trait['kind'] in {'residue_identity','region_identity','geometry_constraint'}
            else trait['allowed_symbols'])
        require(len(allowed)==len(positions) and all(reference['sequence'][p] in symbols for p,symbols in zip(positions,allowed,strict=True)),
            'reference_trait_definition_does_not_hold_on_reference')
        known_cells = [row is not None for row in mapped]
        scores = [float(row[2] in symbols) if row else None for row,symbols in zip(mapped,allowed,strict=True)]
        raw_geometry = None; reference_geometry = None; target_geometry = None; geometry_refs=[]
        if trait['kind']=='geometry_constraint':
            measurement = store.get(trait['measurement_source_ref'])
            require(trait['measurement_source_ref'] in known and measurement.get('provider')=='native.a102.features',
                'trait_geometry_requires_received_native_feature_measurement')
            raw = json.loads(store.get_artifact(measurement['artifact_ref']))
            retained=store.db.execute('SELECT body,permitted_use FROM a102_derived_publications WHERE source_ref=?',
                (trait['measurement_source_ref'],)).fetchone()
            require(retained is not None and retained['permitted_use']=='a102_scoring' and measurement['origin']=='tool'
                and json.loads(retained['body'])==raw,'trait_geometry_measurement_custody_conflict')
            grade = received_grade(store,raw['comparison_source_ref'])['grade'] if raw['comparison_source_ref'] in known else None
            measured_binding=grade['target_binding_ref'] if grade else raw.get('actual_measured_binding_ref')
            require(measured_binding is None or measured_binding==body['reference_binding_ref'],'trait_geometry_measured_subject_conflict')
            rows = [row for row in raw['features'] if row['physical_feature_key']==trait['physical_feature_key']]
            require(len(rows)==1 and rows[0]['definition']['target_position'] in positions,
                'trait_geometry_feature_or_position_conflict')
            eligible=grade['eligible'] and grade['primary'] if grade else raw.get('eligible',False) and raw.get('primary',False)
            raw_geometry = reference_geometry = rows[0]['kernel'] if eligible and measured_binding is not None else None
            if grade is None and body.get('comparison_source_ref') and link.get('structural_comparison_ref'):raw_geometry=None
            if grade and eligible and body.get('comparison_source_ref') and link.get('structural_comparison_ref'):
                xy=received_grade(store,body['comparison_source_ref'])['grade']
                x=_binding(store,xy['target_binding_ref'],known)
                z=_binding(store,grade['reference_ref'],known)
                definition=rows[0]['definition'];mapped= [inverse.get(p) for p in positions]
                point=inverse.get(definition['target_position'])
                xa=[a for a in x['atoms'] if point and a['position']==point[0] and a['atom_name']==definition['target_atom'] and a['occupancy']!=0]
                za=[a for a in z['atoms'] if a['position']==definition['reference_position'] and a['atom_name']==definition['reference_atom'] and a['occupancy']!=0]
                changed={row['input_position'] for row in x['mapping_algorithm']['substitutions']}
                if len(xa)==len(za)==1 and point[0] not in changed:
                    xyz=xa[0]['xyz_A']
                    for transform in (xy['transform'],grade['transform']):
                        xyz=[math.fsum(a*b for a,b in zip(row,xyz,strict=True))+shift
                            for row,shift in zip(transform['rotation'],transform['translation_A'],strict=True)]
                    distance=math.dist(xyz,za[0]['xyz_A'])
                    target_geometry={'distance_A':distance,'kernel':1/(1+distance*distance),
                        'transform_chain_refs':[body['comparison_source_ref'],raw['comparison_source_ref']],
                        'target_model_origin':x['model_metadata']['origin'],'fit':'existing_native_transforms_composed_without_refit'}
                    raw_geometry=target_geometry['kernel']
                    geometry_refs=[raw['comparison_source_ref'],grade['reference_ref'],xy['target_binding_ref']]
                    if trait['chemical_role'] is None:
                        # Geometric shape does not require amino-acid identity.
                        allowed=['ACDEFGHIKLMNPQRSTVWYOU']*len(positions)
                        scores=[float(row[2] in symbols) if row else None for row,symbols in zip(mapped,allowed,strict=True)]
                else:raw_geometry=None
        factor = raw_geometry if trait['kind']=='geometry_constraint' else 1.
        match = math.fsum(scores)/len(scores)*factor if all(known_cells) and factor is not None else None
        qualified_cells=[s*row[4] if s is not None and row is not None else None for s,row in zip(scores,mapped,strict=True)]
        value=math.fsum(qualified_cells)/len(scores)*factor if all(known_cells) and factor is not None else None
        missing = list(link.get('missing',[]))
        if all(known_cells) and link.get('conflicting_reference_positions'):
            missing = [item for item in missing if item != 'unambiguous_primary_native_correspondence']
        if not all(known_cells): missing.append('native_map_for_all_required_trait_positions')
        if trait['kind']=='geometry_constraint' and raw_geometry is None: missing.append('native_reference_feature_geometry')
        target_positions = sorted({row[0] for row in mapped if row is not None})
        feature = None
        if target_positions:
            feature = store.put('feature',{'subject_ref':body['target_ref'],'kind':'protein_site' if len(target_positions)==1 else 'sequence_region',
                'segments':[{'start':p,'end':p+1} for p in target_positions], 'strand':'.','context_refs':[]},origin='tool')['id']
        result = {'target_ref':body['target_ref'],'policy':'local_trait_'+trait['kind']+'_v1',
            'producer_operation':'structure.reference_traits','level':'feature_trait',
            'physical_feature_key':trait['physical_feature_key'],'trait_kind':trait['kind'],
            'actual_subject_refs':[body['reference_binding_ref']], 'target_feature_ref':feature,
            'reference_positions':positions,'target_positions':[row[0] if row else None for row in mapped],
            'reference_symbols':expected,'target_symbols':actual,'allowed_symbols':allowed,
            'state':'unresolved' if value is None else 'evaluated_geometry' if trait['kind']=='geometry_constraint' else 'conserved' if match==1 else 'changed',
            'score':value,'trait_match':match,'cell_scores':scores,'qualified_cell_scores':qualified_cells,
            'missing':sorted(set(missing)),
            'bounds':[math.fsum(s or 0 for s in qualified_cells)/len(scores)*(factor or 0),
                (math.fsum(s or 0 for s in qualified_cells)+scores.count(None))/len(scores)*(factor if factor is not None else 1)],
            'raw_geometry_kernel':reference_geometry,'correspondence':{**link,
                'required_scope_state':'evaluated' if all(known_cells) else 'unresolved',
                'pairs':[row for row in link.get('pairs',[]) if row[1] in positions]},
            'target_geometry':target_geometry,
            'local_sequence_distance':{'identity_distance':sum(row[2]!=row[3] for row in mapped if row)/sum(row is not None for row in mapped) if any(mapped) else None,
                'required_reference_positions':len(positions),'mapped_positions':sum(known_cells)},
            'dependency_group':digest([body['reference_binding_ref'],positions]),
            'inference_kind':('measured_target_model_shape_trait' if target_geometry else 'inferred_shape_trait') if trait['kind']=='geometry_constraint' else 'evaluated_target_sequence_trait',
            'whole_protein_function':'requires_explicit_feature_to_whole_interpretation'}
        refs = [request_ref,body['target_ref'],body['reference_binding_ref'],*trait['definition_source_refs'],
            *_dependencies(link),*link.get('additional_refs',[]),*([trait['measurement_source_ref']] if trait['measurement_source_ref'] else []),
            *([feature] if feature else []),*geometry_refs]
        source = _publish(store,request_ref,result,refs)
        produced.extend([source,*([feature] if feature else [])])
        if feature and value is not None:
            observation = store.put('observation',{'subject_refs':[feature],'source_subject_refs':[],
                'kind':'comparison','source_ref':source,'measurements':[{'name':'trait_conservation_index',
                    'value':{'type':'number','value':value,'unit_ref':None}}],
                'dependencies':[request_ref,*trait['definition_source_refs']], 'anchor':None},origin='tool')['id']
            produced.append(observation)
        results.append(result)
    return produced,results


def _feature_geometry(store,ref,body,known):
    grade = received_grade(store,body['comparison_source_ref'])['grade']
    query=_binding(store,grade['target_binding_ref'],known)
    changed={row['input_position'] for row in query['mapping_algorithm']['substitutions']}
    native_pairs = set(zip(grade['target_positions'],grade['reference_positions'],strict=True))
    rows = []; dependencies = []; alternative = None
    for row in body['features']:
        definition = row['definition']
        mapped = (definition['target_position'],definition['reference_position']) in native_pairs
        route='native_scaffold_map'
        if not mapped and row['state']=='measured':
            if alternative is None:
                binding = _binding(store,grade['reference_ref'],known)
                alternative = sequence_link(store,body['target_ref'],binding['sequence'],known)
                dependencies.extend(_dependencies(alternative))
            mapped = any(i==definition['target_position'] and j==definition['reference_position']
                for i,j,_,_,_ in alternative.get('pairs',[]))
            route='specific_sequence_site_map'
        value = row['kernel'] if (mapped and definition['target_position'] not in changed) or row['state'] in {'established_absent','established_incompatible'} else None
        rows.append({'physical_feature_key':row['physical_feature_key'], 'score':value,
            'state':'evaluated' if value is not None else 'unresolved',
            'missing':[] if value is not None else ['construct_to_target_site_attribution' if definition['target_position'] in changed else 'specific_local_structural_correspondence'],
            'correspondence_route':route,
            'target_position':definition['target_position'],'reference_position':definition['reference_position']})
    value = math.fsum(r['score'] for r in rows)/len(rows) if all(r['score'] is not None for r in rows) else None
    return {'measurement_ref':ref,'target_ref':body['target_ref'],'policy':'feature_geometry_local_scaffold_v1',
        'producer_operation':'structure.feature_geometry','level':'feature_trait',
        'actual_subject_refs':[grade['target_binding_ref'],grade['reference_ref']],
        'state':'evaluated' if value is not None else 'unresolved','score':value,
        'raw_score':body['F'],'raw_E':body.get('raw_E',body['E']),
        'E':grade['components']['B']*value if value is not None and grade['eligible'] else None,
        'features':rows,'missing':sorted({m for row in rows for m in row['missing']}),
        'whole_protein_function':'feature_geometry_requires_source_grounded_interpretation'},dependencies


def _interface(store,ref,body,known):
    component_links=[]; dependencies=[]; missing=[]
    for ordinal,(binding_ref,target) in enumerate(zip(body['binding_refs'],body['target_refs'],strict=True)):
        binding=_binding(store,binding_ref,known)
        positions=sorted({row['left_position' if ordinal==0 else 'right_position'] for row in body['contacts']})
        if target is None:
            link={'state':'unresolved','missing':['attributed_partner_identity'],'pairs':[]}
        elif binding['target_ref']==target:
            sequence=store.get_artifact(store.get(target)['sequence_ref']).decode('ascii')
            link={'state':'evaluated','missing':[],'pairs':[[p,p,sequence[p],binding['sequence'][p],1.] for p in positions],
                'route':'direct_coordinate_component'}
            if any(row['input_position'] in positions for row in binding['mapping_algorithm']['substitutions']):
                link={'state':'unresolved','missing':['construct_to_target_interface_site_attribution'],'pairs':[]}
        elif store.get(target).get('sequence_ref') and store.get_artifact(store.get(target)['sequence_ref']).decode('ascii').strip().upper()==binding['sequence']:
            link={'state':'evaluated','missing':[],'pairs':[[p,p,binding['sequence'][p],binding['sequence'][p],1.] for p in positions],
                'route':'sequence_identical_received_partner_model; genome_presence_not_inferred'}
        else:
            link=sequence_link(store,target,binding['sequence'],known)
        dependencies.extend(_dependencies(link)); missing.extend(link['missing'])
        inverse={row[1]:row for row in link.get('pairs',[])}
        mapped=[inverse.get(p) for p in positions]
        factor=(math.fsum((row[2]==row[3])*row[4] for row in mapped)/len(mapped)
            if mapped and all(row is not None for row in mapped) else None)
        if factor is None: missing.append('interface_component_'+str(ordinal)+'_local_map')
        component_links.append({'target_ref':target,'binding_ref':binding_ref,'required_positions':positions,
            'local_applicability':factor,'correspondence':{**link,'pairs':[r for r in link.get('pairs',[]) if r[1] in positions]}})
    values=[row['local_applicability'] for row in component_links]
    factor=min(values) if all(v is not None for v in values) else None
    value=body['raw_score']*factor if factor is not None and body['raw_score'] is not None else None
    if body['raw_score'] is None: missing.append('native_contact_atoms')
    return {'measurement_ref':ref,'target_ref':body['target_ref'],'policy':'interface_required_components_local_contacts_v1',
        'producer_operation':'structure.interface_geometry','level':'feature_trait',
        'actual_subject_refs':body['binding_refs'],'state':'evaluated_transfer' if value is not None else 'unresolved',
        'score':value,'raw_score':body['raw_score'],'component_links':component_links,
        'missing':sorted(set(missing)),'assembly_context':body['assembly_context'],
        'whole_protein_function':'coordinate_interface_constraint_does_not_establish_partner_presence_or_complex_activity'},dependencies


def _reported(store,ref,body,known):
    result={'measurement_ref':ref,'target_ref':body['target_ref'],'policy':'reported_subject_scope_and_specific_distance_v1',
        'producer_operation':'structure.reported_comparison','level':'entity','score':None,
        'reported_metric':{k:body[k] for k in ('metric_name','metric_value','metric_unit','matched_extent')},
        'native_B':None,'actual_subject_refs':body.get('measured_subject_refs',[]),
        'state':'unresolved','missing':[],'interpretation':'reported_evidence_not_fresh_target_geometry'}
    refs=body.get('measured_subject_refs',[])
    if len(refs)!=2 or not set(refs)<=known:
        result['missing'].append('actual_reported_subject_pair');return result,[]
    if not body.get('measured_regions') or not body.get('target_regions'):
        result['missing'].append('structured_reported_and_target_regions');return result,refs
    measured=store.get(refs[0])
    if refs[0]==body['target_ref']:
        result.update(state='reported_on_target',missing=[]);return result,refs
    if measured.get('provider')=='native.a102.structure_binding':
        sequence=_binding(store,refs[0],known)['sequence']
    elif measured.get('sequence_ref'):
        sequence=store.get_artifact(measured['sequence_ref']).decode('ascii').strip().upper()
    else:
        result['missing'].append('canonical_reported_subject_sequence');return result,refs
    link=sequence_link(store,body['target_ref'],sequence,known)
    positions=[p for a,b in body['target_regions'] for p in range(a,b)]
    distance=scoped_distance(link,positions)
    result.update(sequence_link=link,local_sequence_distance=distance,missing=link['missing'],
        state='evaluated_reported_transfer' if link['state']=='evaluated' else 'unresolved')
    return result,[*refs,*_dependencies(link)]


def refresh(store, known, scope):
    """Host receipt hook, called before credit projection, never by credit reads."""
    install(store); known = set(known); produced = []; needs = []
    targets = set(scope['subject_refs']); contrasts=[]
    for ref in sorted(known):
        source = store.get(ref)
        if source['record_type']!='source': continue
        if source.get('provider')=='native.a102.structure_binding':
            binding=_binding(store,ref,known)
            if binding['target_ref'] not in targets:continue
            mapped=sum(p is not None for p in binding['coordinate_to_input_mapping'])
            result={'measurement_ref':ref,'target_ref':binding['target_ref'],'policy':'model_sequence_entity_binding_v1',
                'producer_operation':'structure.bind','level':'entity','state':'mapped_model','score':None,
                'actual_subject_refs':[ref],'sequence_distance':len(binding['mapping_algorithm']['substitutions'])/max(1,mapped),
                'mapped_sequence_positions':mapped,'observed_coordinate_positions':len(binding['coordinates']),
                'construct_changes':binding['mapping_algorithm']['substitutions'],'missing':[],
                'origin':binding['model_metadata']['origin'],'interpretation':'model_sequence_binding_not_a_function_assignment'}
            produced.append(_publish(store,ref,result,[ref,binding['target_ref']]))
        elif source.get('provider')=='native.a102.structural_comparison':
            grade = received_grade(store,ref)['grade']
            if grade['target_ref'] in targets and grade['producer'] in DIRECT_PRODUCERS and {
                    grade['target_binding_ref'],grade['reference_ref']} <= known:
                body = _direct(store,ref,grade,known)
                produced.append(_publish(store,ref,body,[ref,grade['target_ref'],grade['target_binding_ref'],grade['reference_ref']]))
        elif source.get('provider')=='native.a102.features':
            row = store.db.execute('SELECT body FROM a102_derived_publications WHERE source_ref=?',(ref,)).fetchone()
            if row is None: continue
            raw = json.loads(row[0])
            if raw['target_ref'] not in targets or raw['comparison_source_ref'] not in known: continue
            body,dependencies = _feature_geometry(store,ref,raw,known)
            produced.append(_publish(store,ref,body,[ref,raw['target_ref'],raw['comparison_source_ref'],*raw['definition_source_refs'],*dependencies]))
            if body['missing']: needs.append((ref,body))
        elif source.get('provider')=='native.a102.interface_geometry':
            row=store.db.execute('SELECT body FROM a102_derived_publications WHERE source_ref=?',(ref,)).fetchone()
            if row is None: continue
            raw=json.loads(row[0])
            if raw['target_ref'] not in targets: continue
            body,dependencies=_interface(store,ref,raw,known)
            produced.append(_publish(store,ref,body,[ref,raw['target_ref'],*raw['binding_refs'],
                *[r for c in raw['contacts'] for r in c['definition_source_refs']],*dependencies]))
            if body['missing']: needs.append((ref,body))
        elif source.get('provider')=='native.a102.reported_comparison':
            row=store.db.execute('SELECT body FROM a102_derived_publications WHERE source_ref=?',(ref,)).fetchone()
            if row is None:continue
            raw=json.loads(row[0])
            if raw['target_ref'] not in targets or not set(raw['source_refs'])<=known:continue
            body,dependencies=_reported(store,ref,raw,known)
            produced.append(_publish(store,ref,body,[ref,raw['target_ref'],*raw['source_refs'],*dependencies]))
            if body['missing']:needs.append((ref,body))
        elif source.get('provider')=='native.a102.contrast':
            contrasts.append(ref)
        elif source.get('provider')==REQUEST_PROVIDER:
            row = store.db.execute('SELECT body FROM a102_attachment_requests WHERE source_ref=?',(ref,)).fetchone()
            require(row is not None and source['origin']=='tool' and source['version']==VERSION
                and json.loads(store.get_artifact(source['artifact_ref']))==json.loads(row[0]),'attachment_request_custody_conflict')
            body = json.loads(row[0])
            if body['target_ref'] not in targets: continue
            if body['operation']=='structure.reference_align':
                if body['measurement_ref'] not in known or body['measured_binding_ref'] not in known: continue
                result,dependencies = _fold(store,body,known)
                produced.append(_publish(store,ref,result,[ref,body['measurement_ref'],body['target_ref'],body['measured_binding_ref'],*dependencies]))
                if result['missing']: needs.append((ref,result))
            elif body['operation']=='structure.reference_traits':
                if body['reference_binding_ref'] not in known: continue
                if any(ref not in known for trait in body['traits'] for ref in
                    [*trait['definition_source_refs'],*([trait['measurement_source_ref']] if trait['measurement_source_ref'] else [])]):continue
                additions,traits = _traits(store,ref,body,known)
                produced.extend(additions)
                for trait in traits:
                    if trait['missing']: needs.append((ref,trait))
            else: raise ValueError('unbound_tool_attachment_policy')
    for ref in contrasts:
        row=store.db.execute('SELECT body FROM a102_derived_publications WHERE source_ref=?',(ref,)).fetchone()
        if row is None:continue
        raw=json.loads(row[0]);selected=[*raw['supporting_source_refs'],*raw['opposing_source_refs']]
        if 'contrast_witness_refs' not in raw:continue  # immutable historical panel, before automatic local attachments
        if raw['target_ref'] not in targets or not set(selected)<=known:continue
        bodies=[];addresses={}
        for original in selected:
            saved=store.db.execute('SELECT body FROM a102_derived_publications WHERE source_ref=?',(original,)).fetchone()
            require(saved is not None,'contrast_feature_custody_unavailable')
            feature=qualified_feature(store,original,json.loads(saved[0]),known|set(produced))
            bodies.append(feature);addresses[original]=feature['comparison_ref']
        panel=contrast_panel(bodies,function_ref=raw['function_ref'],
            supporting_refs=[addresses[r] for r in raw['supporting_source_refs']],
            opposing_refs=[addresses[r] for r in raw['opposing_source_refs']],
            contrast_witness_refs=raw.get('contrast_witness_refs',[]),scope_ref=raw['scope_ref'])
        body={'measurement_ref':ref,'target_ref':raw['target_ref'],'policy':'contrast_from_qualified_local_features_v1',
            'producer_operation':'structure.contrast','level':'qualified_panel','score':panel['A102_f'],
            'state':panel['status'],'missing':[],'qualified_panel':panel}
        produced.append(_publish(store,ref,body,[ref,raw['target_ref'],*selected]))
    return list(dict.fromkeys(produced)),needs
