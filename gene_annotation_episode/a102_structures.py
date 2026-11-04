"""Coordinate populations and explicit maps to supplied biological sequences.

Run parsing/mapping through the bounded A102 worker. Residue numbers are native
identities, never assumed to be offsets into the user's original sequence.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from itertools import islice
import math

from .a102_scoring import digest, require
from .protein_structure_formats import parse_pdb_structure, parse_mmcif_structure
from .protein_structure_sequences import _extract_validated_structure_sequence
from .protein_structure_contracts import validate_structure_selection


BINDING_SCHEMA='a102_structure_binding_v1'
MAX_RESIDUES=4096
MAX_FILE_BYTES=8*1024**2


def sequence_map(supplied,represented):
    """Unique global coordinate-to-input map; this is no homolog search."""
    import Bio
    from Bio.Align import PairwiseAligner
    require(supplied and represented and len(supplied)<=MAX_RESIDUES
        and len(represented)<=MAX_RESIDUES,'a102_sequence_mapping_size_limit')
    if supplied==represented:
        return list(range(len(represented))),{'algorithm':'identity','exact':True,
            'substitutions':[],'unmapped_model_positions':[]}
    aligner=PairwiseAligner(mode='global',match_score=2,mismatch_score=-4,
        open_gap_score=-6,extend_gap_score=-0.5)
    candidates=[]
    for alignment in islice(iter(aligner.align(supplied,represented)),3):
        mapping=[None]*len(represented)
        for (a,b),(c,d) in zip(*alignment.aligned,strict=True):
            require(b-a==d-c,'a102_coordinate_mapping_alignment_conflict')
            for i,j in zip(range(int(a),int(b)),range(int(c),int(d)),strict=True):mapping[j]=i
        if mapping not in candidates:candidates.append(mapping)
    require(len(candidates)==1,'a102_ambiguous_coordinate_to_input_mapping')
    mapping=candidates[0]
    paired=[(i,j) for j,i in enumerate(mapping) if i is not None]
    mismatches=[{'input_position':i,'model_position':j,'input_symbol':supplied[i],
        'model_symbol':represented[j]} for i,j in paired if supplied[i]!=represented[j]]
    require(paired and len(mismatches)/len(paired)<=0.1,'a102_model_does_not_represent_supplied_sequence')
    return mapping,{'algorithm':'Bio.Align.PairwiseAligner','version':Bio.__version__,
        'mode':'global','match_score':2,'mismatch_score':-4,'open_gap_score':-6,
        'extend_gap_score':-0.5,'mapping_only_no_A101_credit':True,
        'exact':not mismatches,'substitutions':mismatches,
        'unmapped_model_positions':[j for j,i in enumerate(mapping) if i is None]}


def bind_structure(data,request):
    require(len(data)<=MAX_FILE_BYTES,'a102_structure_file_size_limit')
    format=request['format']
    identity={'artifact_ref':request['artifact_ref'],'sha256':hashlib.sha256(data).hexdigest(),
        'byte_length':len(data),'format':format}
    if format=='pdb_3x_text':parsed=parse_pdb_structure(data,file_identity=identity)
    else:
        require(format=='pdbx_mmcif_text','a102_unsupported_structure_format')
        parsed=parse_mmcif_structure(data,file_identity=identity,data_block=None)
    block=request['block_ordinal'] if format=='pdbx_mmcif_text' else None
    models=[m for m in parsed['models'] if m['block_ordinal_0based']==block]
    ordinal=request['model_ordinal']
    require(type(ordinal) is int and 0<=ordinal<len(models),'a102_explicit_model_not_found')
    model=models[ordinal]
    chain_field='label_asym_id' if format=='pdbx_mmcif_text' else 'chain_id'
    chains=[c for c in parsed['chains'] if c['block_ordinal_0based']==block
        and c['model_key']==model['model_key'] and c['chain_key'].get(chain_field)==request['chain_id']]
    require(len(chains)==1,'a102_explicit_chain_not_found_or_ambiguous')
    selection={'structure_role':'single','file_identity':identity,
        'data_block':None if block is None else {'ordinal_0based':block,'name':parsed['cif_blocks'][block]['name']},
        'model_key':deepcopy(model['model_key']),'chain_key':deepcopy(chains[0]['chain_key']),
        'sequence_basis':'mmcif_declared_polymer' if block is not None else 'observed_polymer',
        'residue_variant_choices':[], 'symbol_policy':{'unknown':'reject','explicit_component_overrides':[]},
        'ca_selection':{'policy':'unambiguous_only','choices':[]},'zero_occupancy_policy':'exclude',
        'bfactor_semantics':'unspecified','semantics_evidence':None}
    sequence=_extract_validated_structure_sequence(parsed,selection=validate_structure_selection(selection))
    require(sequence['sequence_available'],'a102_structure_sequence_unavailable',issues=sequence['issues'])
    represented=sequence['alignment_sequence']
    require(len(represented)<=MAX_RESIDUES,'a102_structure_residue_limit')
    supplied=request.get('supplied_sequence') or represented
    mapping,alignment=sequence_map(supplied,represented)
    by_key={a['identity']['atom_row_key']:a for a in parsed['atoms']}
    coordinates=[];missing=[];atoms=[]
    atoms_by_residue={}
    for atom in parsed['atoms']:
        key=digest(atom['identity']['residue'])
        atoms_by_residue.setdefault(key,[]).append(atom)
    for residue,position in zip(sequence['residues'],mapping,strict=True):
        if position is None or residue['ca']['state']!='available':
            missing.append({'model_position':residue['sequence_position_0based'],
                'input_position':position,'position_key':residue['position_key'],
                'reason':'model_residue_unmapped' if position is None else residue['ca']['primary_reason']})
            continue
        atom=by_key[residue['ca']['selected_atom_row_key']]
        xyz=[v['value'] for v in atom['xyz_A']]
        require(all(type(x) in (int,float) and math.isfinite(x) for x in xyz),'a102_nonfinite_coordinate')
        coordinates.append({'position':position,'symbol':residue['alignment_symbol'],
            'position_key':deepcopy(residue['position_key']),'atom_row_key':atom['identity']['atom_row_key'],
            'xyz_A':xyz,'native_b_column':atom['b_iso']['value'],
            'occupancy':atom['occupancy']['value']})
        for item in atoms_by_residue.get(digest(residue['selected_residue_identity']),[]):
            if any(v['state']!='present' for v in item['xyz_A']):continue
            atoms.append({'position':position,'atom_name':(item['identity']['atom_name']['text'] or '').strip(),
                'alt_id':(item['identity']['alt_id']['text'] or '').strip(),
                'atom_row_key':item['identity']['atom_row_key'],'occupancy':item['occupancy']['value'],
                'xyz_A':[v['value'] for v in item['xyz_A']]})
    require(len(coordinates)>=3,'a102_insufficient_unambiguous_coordinates')
    meta=deepcopy(request['model_metadata'])
    require(meta.get('origin') in {'experimental','predicted','supplied_unknown'},'a102_model_origin_required')
    from .protein_structure_metadata import _metadata_values
    native_metadata={'selection':selection,'structure_role':'single','metadata_values':[]}
    _metadata_values(parsed,native_metadata)
    meta['native_metadata_values']=native_metadata['metadata_values']
    quality=[row['native_b_column'] for row in coordinates if row['native_b_column'] is not None]
    meta['uncertainty']={'native_CA_b_column':{'n':len(quality),'min':min(quality) if quality else None,
        'max':max(quality) if quality else None,'mean':math.fsum(quality)/len(quality) if quality else None},
        'semantics':'uninterpreted_native_column','PAE':None,'weights_applied':False}
    return {'schema':BINDING_SCHEMA,'file_identity':identity,'file_source_ref':request['file_source_ref'],
        'target_ref':request.get('target_ref'),'material_ref':request.get('target_ref'),
        'target_scope':[0,len(supplied)],'selection':selection,'sequence':supplied,
        'length':len(supplied),'represented_sequence':represented,'coordinate_to_input_mapping':mapping,
        'mapping_algorithm':alignment,'coordinates':coordinates,'atoms':atoms,'missing_coordinates':missing,
        'unrepresented_input_positions':sorted(set(range(len(supplied)))-set(p for p in mapping if p is not None)),
        'model_metadata':meta,'qualifications':list(dict.fromkeys([*sequence['qualifications'],
            *(['reference_full_polymer_length_unknown'] if block is None and not request.get('supplied_sequence') else []),
            'native_uncertainty_retained_without_credit_weight'])),
        'declared_polymer_length':sequence['declared_polymer_length'],
        'coordinate_sha256':digest([[r['symbol'],r['xyz_A']] for r in coordinates])}


def ca_pdb(binding):
    """Stage a single selected CA population and preserve its reversible map."""
    from .protein_structure_sequences import COMPONENT_SYMBOLS
    components={v:k for k,v in COMPONENT_SYMBOLS.items()}
    lines=[]
    for i,row in enumerate(binding['coordinates'],1):
        x,y,z=row['xyz_A']
        require(all(abs(v)<10000 for v in (x,y,z)),'a102_pdb_staging_coordinate_range')
        lines.append(f"ATOM  {i:5d}  CA  {components[row['symbol']]:3s} A{i:4d}    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00           C  \n")
    return ''.join(lines)+'TER\nEND\n'


def binding_summary(binding):
    return {key:deepcopy(binding[key]) for key in ('schema','file_identity','file_source_ref','target_ref','material_ref','target_scope',
        'selection','length','mapping_algorithm','missing_coordinates','model_metadata','qualifications',
        'declared_polymer_length','coordinate_sha256')} | {'coordinate_residue_count':len(binding['coordinates']),
        'map_sha256':digest(binding['coordinate_to_input_mapping'])}


def comparison_identity(target,reference):
    """Same sequence scope/model variants share one declared comparison group."""
    return digest({'target_ref':target['target_ref'],'target_scope':target['target_scope'],
        'target_sequence_sha256':digest(target['sequence']),
        'reference_sequence_sha256':digest(reference['sequence']),'reference_scope':[0,reference['length']]})
