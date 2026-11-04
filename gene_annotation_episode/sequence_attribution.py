"""Exact received protein-to-protein maps for entity and local trait uses.

This consumes qualified native grades; it does not run sequence homology or
read an aggregate axis score. A profile column is not a protein residue.
"""
from __future__ import annotations

import math
import hashlib

from .a101_scoring import route_native_grading, SCALES
from .domain import canonical,ContractError
from .tool_grading_artifacts import source_tool_grading_entries


def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def require(condition,code):
    if not condition:raise ContractError(code)


def original_positions(store, subject, target):
    """Lift a protein region/site/product into original protein coordinates."""
    if subject==target:return list(range(store.subject_length(target)))
    if store.get(subject)['record_type'] not in {'input','feature','product','read_subject'}:return None
    mapping=store.sequence_mapping(subject)
    if mapping['units_per_symbol']!=1 or {r['subject_ref'] for r in mapping['path']}!={target} or any(
            r['unit']!='aa' or r['strand']!='+' for r in mapping['path']):return None
    return [i for row in mapping['path'] for i in range(row['start'],row['end'])]


def sequence_link(store, target, reference_sequence, known, *, alignment_ref=None):
    """Join only the actual X/Y sequence pair, retaining competing mappings."""
    known = set(known)
    require(target in known, 'attribution_target_not_received')
    require(store.subject_molecule(target)=='protein','attribution_requires_protein_coordinates')
    actual = store.get_artifact(store.get(target)['sequence_ref']).decode('ascii').strip().upper()
    candidates = []
    for ref in sorted(known):
        record = store.get(ref)
        if record['record_type'] != 'observation' or record['origin'] != 'tool':
            continue
        lifts=[p for subject in record['subject_refs'] if (p:=original_positions(store,subject,target)) is not None]
        if len(lifts)!=1:continue
        lift=lifts[0]
        if alignment_ref is not None and ref != alignment_ref:
            continue
        source = record['source_ref']
        if source not in known:
            continue
        matched = []
        for subject in record['source_subject_refs']:
            if subject not in known:
                continue
            row = store.get(subject)
            if row['record_type'] != 'reference' or row.get('molecule') != 'protein' or not row.get('sequence_ref'):
                continue
            sequence = store.get_artifact(row['sequence_ref']).decode('ascii').strip().upper()
            if sequence == reference_sequence:
                matched.append(subject)
        if not matched:
            continue
        for entry in source_tool_grading_entries(store, source):
            if record.get('native_blast') and record['native_blast'].get('shared_projection',{}).get('grading_artifact_ref')!=entry['artifact_ref']:
                continue
            schema = (entry['grading'].get('sheet') or {}).get('schema', '')
            if schema != 'hmmer_search_sheet_v1' and not schema.startswith('blast_') and schema!='biopython_pairwise_sheet_v1':
                continue
            if schema=='biopython_pairwise_sheet_v1':
                sheet=entry['grading']['sheet']
                if sheet['molecule']!='protein' or sheet['status']!='complete':continue
                native=sheet['native_result']
                mapped=[r for r in sheet['residue_correspondence'] if r['query_position'] is not None and r['reference_position'] is not None]
                population=[{'algorithm':'biopython_pairwise','program':'biopython_pairwise',
                    'native_record_key':'retained-pairwise-correspondence','bits':None,'native_score':native['native_score'],
                    'reference_length':native['reference_length'],
                    'residue_pairs':[[r['query_position'],r['reference_position'],r['query_symbol'],r['reference_symbol']] for r in mapped]}]
            else:population=route_native_grading(entry['grading'])
            for row in population:
                if row['program'] not in {'phmmer', 'blastp','biopython_pairwise'}:
                    continue
                if record.get('native_blast'):
                    native = record['native_blast']
                    if row.get('hit_index') != native['hit_ordinal'] or row.get('hsp_index') != native['hsp_ordinal']:
                        continue
                if any(i>=len(lift) for i,_,_,_ in row['residue_pairs']):continue
                pairs = [[lift[i],j,a,b] for i,j,a,b in row['residue_pairs']]
                if row['reference_length'] != len(reference_sequence):
                    continue
                if any(i >= len(actual) or j >= len(reference_sequence) or actual[i] != a or reference_sequence[j] != b
                       for i,j,a,b in pairs):
                    continue
                require(len({i for i,_,_,_ in pairs}) == len(pairs)
                    and len({j for _,j,_,_ in pairs}) == len(pairs), 'attribution_noninjective_native_map')
                candidates.append({'pairs': pairs, 'observation_ref': ref, 'source_ref': source,
                    'reference_ref': matched[0], 'grading_artifact_ref': entry['artifact_ref'],
                    'algorithm': row['algorithm'], 'native_record_key': row['native_record_key'],
                    'bits': row['bits'], 'native_score':row.get('native_score'),
                    'strength_profile':'native_bit_kernel' if row['algorithm'] in SCALES else 'identity_distance_only_no_bit_statistic',
                    'native_strength': -math.expm1(-SCALES[row['algorithm']]*max(0,row['bits'])) if row['algorithm'] in SCALES else 1.})
    if not candidates:
        return {'state': 'unresolved', 'missing': ['specific_target_reference_native_alignment'],
            'target_ref': target, 'reference_sequence_sha256': digest(reference_sequence)}
    unique = {}
    for row in candidates:
        unique.setdefault(digest([row['pairs'],row['algorithm'],row['bits']]), row)
    # Distinct, nonoverlapping native domains can jointly cover a protein.
    # Conflicting or differently scored overlapping variants require selection.
    positions, inverse, witnesses = {}, {}, []
    conflicting_targets, conflicting_references = set(), set()
    for row in unique.values():
        for i,j,a,b in row['pairs']:
            item = [j,a,b,row['native_strength']]
            if (i in positions and positions[i] != item) or (j in inverse and inverse[j] != i):
                conflicting_targets.add(i); conflicting_references.add(j)
                if i in positions: conflicting_references.add(positions[i][0])
                if j in inverse: conflicting_targets.add(inverse[j])
            positions.setdefault(i,item); inverse.setdefault(j,i)
        witnesses.append({k:v for k,v in row.items() if k != 'pairs'})
    if conflicting_targets:
        # Entity-level uses remain unresolved. Local traits can still consume
        # the unaffected cells without selecting a higher-scoring alignment.
        return {'state':'unresolved','missing':['unambiguous_primary_native_correspondence'],
            'target_ref':target,'reference_sequence_sha256':digest(reference_sequence),
            'candidate_observation_refs':sorted({r['observation_ref'] for r in candidates}),
            'conflicting_target_positions':sorted(conflicting_targets),
            'conflicting_reference_positions':sorted(conflicting_references),
            'pairs':[[i,*positions[i]] for i in sorted(positions)
                if i not in conflicting_targets and positions[i][0] not in conflicting_references],
            'witnesses':witnesses}
    return {'state': 'evaluated', 'target_ref': target, 'reference_sequence_sha256': digest(reference_sequence),
        'pairs': [[i,*positions[i]] for i in sorted(positions)], 'witnesses': witnesses, 'missing': []}


def scoped_distance(link, positions):
    """A local distance with its original denominator, not a whole-axis value."""
    positions = set(positions)
    rows = [r for r in link.get('pairs', []) if r[0] in positions]
    identical = sum(a == b for _,_,a,b,_ in rows)
    return {'required_position_count': len(positions), 'mapped_position_count': len(rows),
        'identity_on_mapped': identical/len(rows) if rows else None,
        'sequence_distance': 1-identical/len(rows) if rows else None,
        'target_coverage': len(rows)/len(positions) if positions else None,
        'native_strength': math.fsum(r[4] for r in rows)/len(rows) if rows else None}
