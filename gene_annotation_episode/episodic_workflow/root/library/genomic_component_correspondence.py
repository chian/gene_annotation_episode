"""Original received genomic component correspondence for shared attribution."""
import math
from .sequence_attribution import digest, require, sequence_link


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
    selected_positions = set(selected)
    cells = [p for p in link.get('pairs',[]) if p[0] in selected_positions]
    ambiguous = set(link.get('conflicting_target_positions',[])) & selected_positions
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


