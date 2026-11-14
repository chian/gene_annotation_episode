"""Automatic numerical delivery from an existing explicit-map CA comparison.

The producer publishes after validating its complete sheet; a receiving host
can use the same bridge after authenticating the exact saved-sheet grant.
A Source handle, auxiliary artifact or unselected projection is insufficient.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from types import SimpleNamespace

from .a102_native_worker import _validated_transform
from .a102_publication import publish_comparison
from .a102_scoring import NATIVE_SCHEMA,digest,require
from .a102_structures import comparison_identity

VERSION = 'a102_received_saved_comparison_bridge_v2'


def publish_received_comparisons(store, context, *, input_authority, known_record_refs):
    """Use exact received saved-sheet grants, independent of execution location.

    The configured ordinary/native return authority owns descriptor admission.
    This adapter neither discovers private sheets from Source IDs nor performs
    an alignment. Matching original target bindings remain a separate condition.
    """
    from .protein_structure_action_records import SAVED_SOURCE
    from .protein_structure_calculations import validate_recorded_protein_structure_components
    from .communication import plain
    known = set(known_record_refs)
    descriptors = [*input_authority.received_facts(context, fact_source=SAVED_SOURCE),
        *input_authority.own_facts(context, fact_source=SAVED_SOURCE)]
    legacy = input_authority.legacy_returns
    if legacy is not None:
        from .native_protein_structure_returns import SAVED_SOURCE as RESOURCE_SAVED_SOURCE
        descriptors.extend(row for group in legacy.received_context(context)
            if group['fact_source'] == RESOURCE_SAVED_SOURCE for row in group['facts'])
    generated, needs, seen = [], [], set()
    for descriptor in descriptors:
        key = digest(descriptor)
        if key in seen:
            continue
        seen.add(key)
        original = input_authority.authenticate_received_saved_sheet(context, descriptor,
            required_use='recalculate')
        scientific = original.get('scientific')
        if scientific is None:
            def document(field):
                file = original[field]
                raw = store.get_artifact(file['artifact_ref'])
                require(len(raw) == file['byte_length']
                    and hashlib.sha256(raw).hexdigest() == file['sha256'],
                    'a102_saved_comparison_artifact_conflict')
                return json.loads(raw)
            sheet, components = document('sheet_file'), document('original_components_file')
            components = validate_recorded_protein_structure_components(sheet, components=components)
            scientific = {'kind': 'comparison', 'sheet': sheet, 'components': components}
        reference = descriptor['custody']['source_ref']
        admitted = publish_bridge(SimpleNamespace(store=store), scientific=scientific,
            source_ref=reference, selection={'return_saved_sheet': True},
            known_record_refs=known, scope=plain(context.scope))
        generated.extend(admitted)
        if not admitted:
            for target in context.scope['subject_refs']:
                needs.append((reference, {'target_ref': target,
                    'policy': 'a102_received_saved_comparison',
                    'missing': ['qualified_CA_comparison_and_unambiguous_received_target_model_bindings'],
                    'required_operands': {'saved_comparison_source_ref': reference}}))
    return list(dict.fromkeys(generated)), needs


def publish_bridge(registry,*,scientific,source_ref,selection,known_record_refs,scope):
    if not selection.get('return_saved_sheet') or scientific is None or scientific['kind']!='comparison':return []
    sheet,components=scientific['sheet'],scientific['components']
    if components['evaluation']['state']!='performed' or components['transform']['state'] not in {'identifiable_fit','supplied'}:
        return []
    original=registry.store.get(source_ref)
    # The caller is either the qualified producer or the receipt-bound adapter
    # above. Both require the actual selected saved-sheet grant.
    candidates={side:[] for side in ('fixed','moving')}
    for ref in known_record_refs:
        row=registry.store.db.execute('SELECT body FROM a102_structure_bindings WHERE source_ref=?',(ref,)).fetchone()
        if row is None:continue
        binding=json.loads(row['body'])
        for side in candidates:
            selected=sheet['sequences'][side]['selection']
            if (binding['file_identity']==selected['file_identity'] and all(
                    binding['selection'][key]==selected[key] for key in ('data_block','model_key','chain_key'))):
                candidates[side].append((ref,binding))
    if any(len(items)!=1 for items in candidates.values()):return []
    target_sides=[side for side,items in candidates.items() if items[0][1]['target_ref'] is not None]
    if len(target_sides)!=1:return []
    target_side=target_sides[0];reference_side='moving' if target_side=='fixed' else 'fixed'
    qref,q=candidates[target_side][0];tref,t=candidates[reference_side][0]
    require(registry.store.scope_covers(registry.store.coverage(q.get('material_ref') or q['target_ref']),scope),
        'a102_existing_comparison_target_outside_scope')
    transform=components['transform']
    rotation=transform['rotation']['value'];translation=transform['translation']['value']
    if rotation is None or translation is None:return []
    if target_side=='moving':rotation=[list(row) for row in zip(*rotation,strict=True)]
    else:translation=[-math.fsum(a*b for a,b in zip(row,translation,strict=True)) for row in rotation]
    transform=_validated_transform(rotation,translation)
    used=set(components['evaluation']['used_correspondence_ids'])
    positions=[];reference_positions=[];distances=[]
    for pair in sheet['coordinate_pairs']:
        if pair['correspondence_id'] not in used:continue
        qi,ti=pair[target_side+'_position_0based'],pair[reference_side+'_position_0based']
        qposition=q['coordinate_to_input_mapping'][qi];tposition=t['coordinate_to_input_mapping'][ti]
        if qposition is None or tposition is None:continue
        xyz=pair[target_side+'_xyz_A']['value'];fixed=pair[reference_side+'_xyz_A']['value']
        require(xyz is not None and fixed is not None,'a102_existing_comparison_used_coordinates_unavailable')
        moved=[math.fsum(a*b for a,b in zip(row,xyz,strict=True))+v for row,v in zip(rotation,translation,strict=True)]
        positions.append(qposition);reference_positions.append(tposition);distances.append(math.dist(moved,fixed))
    if not distances:return []
    group=comparison_identity(q,t)
    native={'schema':NATIVE_SCHEMA,'producer':'compare_protein_structures','target_ref':q['target_ref'],
        'reference_ref':tref,'target_binding_ref':qref,'original_comparison_source_ref':source_ref,
        'supplied_length':q['length'],'target_scope':q['target_scope'],'reference_length':t['length'],
        'target_positions':positions,'reference_positions':reference_positions,'distances_A':distances,
        'comparison_group':group,'variant_ref':digest({'source_ref':source_ref,'target_binding_ref':qref}),
        'primary':True,'atom_selection':'CA','transform':transform,'transform_sha256':digest(transform),
        'target_model':deepcopy(q['model_metadata']),'reference_model':deepcopy(t['model_metadata']),
        'target_structure_sha256':q['file_identity']['sha256'],'reference_structure_sha256':t['file_identity']['sha256'],
        'target_coordinate_sha256':q.get('coordinate_sha256'),'reference_coordinate_sha256':t.get('coordinate_sha256'),
        'target_selection':q['selection'],'reference_selection':t['selection'],
        'native_metrics':{'algorithm':'explicit_map_CA_fit_and_evaluation',
            'reported_rmsd_A':components['evaluation']['evaluation_rmsd']['value'],
            'original_calculation_id':components['calculation_id'],'source_provider':original['provider']},
        'qualifications':['declared_correspondence_not_homology_proof','explicit_saved_sheet_recalculation_grant',
            'original_scope_and_supplied_sequence_mapping_preserved']}
    return [publish_comparison(registry.store,native)['source_ref']]
