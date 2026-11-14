"""Populate retained protein comparison inputs, independently of calculations.

All input bytes have already been parsed and authenticated by their owners. This
module joins supplied records only. It neither runs alignment nor fits a
transform; a native baseline is validated and preserved, never replaced.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
from gene_annotation_episode.episodic_workflow.root.a106.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.protein_structure_contracts import ProteinStructureSheet, CoordinatePair, VectorCell, same
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.protein_structure_sequences import extract_structure_sequence, rebind_structure_sequence
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.protein_structure_metadata import extract_native_structure_metadata
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.protein_structure_correspondence import validate_explicit_residue_map, correspondence_from_pairwise_sheet

def _unique_records(values):
    result = []
    for value in values:
        if not any((same(value, old) for old in result)):
            result.append(deepcopy(value))
    return result

def _coordinate_cell(ca, atom) -> VectorCell:
    if ca['state'] == 'available':
        if atom is None or any((n['state'] != 'present' for n in atom['xyz_A'])):
            raise ValueError('invalid_coordinate_identity')
        return {'value': [n['value'] for n in atom['xyz_A']], 'state': 'present', 'reason': None, 'unit': 'angstrom', 'origin': 'observed'}
    return {'value': None, 'state': 'invalid' if ca['state'] == 'invalid' else 'unavailable', 'reason': ca['primary_reason'], 'unit': 'angstrom', 'origin': 'observed'}

def _join_pairs(structures, sequences, correspondence, metadata) -> list[CoordinatePair]:
    atoms = {s: {a['identity']['atom_row_key']: a for a in structures[s]['atoms']} for s in ('fixed', 'moving')}
    uncertainty = {}
    for side in ('fixed', 'moving'):
        uncertainty[side] = {}
        for row in metadata[side]['atom_uncertainty']:
            key = row['atom_row_key']
            if key in uncertainty[side] or key not in atoms[side]:
                raise ValueError('metadata_join_conflict')
            if not same(row['residue_identity'], atoms[side][key]['identity']['residue']):
                raise ValueError('metadata_join_conflict')
            uncertainty[side][key] = row['row_key']
    result = []
    for row in correspondence['rows']:
        if row['fixed_position_0based'] is None or row['moving_position_0based'] is None:
            continue
        pair = {'correspondence_id': row['correspondence_id']}
        for side in ('fixed', 'moving'):
            position = row[side + '_position_0based']
            if position >= len(sequences[side]['residues']):
                raise ValueError('map_endpoint_missing')
            residue = sequences[side]['residues'][position]
            ca = residue['ca']
            key = ca['selected_atom_row_key']
            atom = atoms[side].get(key)
            if key is not None and atom is None:
                raise ValueError('invalid_coordinate_identity')
            if atom is not None and (not same(atom['identity']['residue'], residue['selected_residue_identity'])):
                raise ValueError('invalid_coordinate_identity')
            pair.update({side + '_position_0based': position, side + '_atom_row_key': key, side + '_xyz_A': _coordinate_cell(ca, atom), side + '_ca_state': deepcopy(ca), side + '_uncertainty_row_key': uncertainty[side].get(key)})
        result.append(pair)
    return result

def _validate_input_relationships(sheet: ProteinStructureSheet) -> None:
    """Check saved selections against complete supplied native tables/maps.

    Re-extraction validates native input relationships; it does not execute an
    alignment or numerical fit, and never substitutes a rebuilt record.
    """
    sequences = sheet['sequences']
    for side in ('fixed', 'moving'):
        parsed, seq, metadata = (sheet['structures'][side], sequences[side], sheet['native_uncertainty'][side])
        if not same(extract_structure_sequence(parsed, selection=seq['selection']), seq):
            raise ValueError('sequence_artifact_mismatch')
        rebuilt_metadata = extract_native_structure_metadata(parsed, selected_sequence=seq, supplied_metadata=metadata['supplied_metadata'])
        if not same(rebuilt_metadata, metadata):
            raise ValueError('metadata_join_conflict')
    source, corr = (sheet['input_identities']['correspondence'], sheet['correspondence'])
    if source['kind'] != corr['origin']:
        raise ValueError('alignment_operand_mismatch')
    if source['kind'] == 'retained_alignment':
        for side in ('fixed', 'moving'):
            descriptor = source[side + '_sequence_descriptor']
            original = rebind_structure_sequence(sequences[side], structure_role=descriptor['selection']['structure_role'])
            if 'structure_correspondence' not in descriptor['allowed_uses'] or not same(original['selection'], descriptor['selection']) or (not original['sequence_available']) or (original['sequence_length'] != descriptor['sequence_length']):
                raise ValueError('sequence_artifact_mismatch')
            for data, file in ((original['alignment_sequence'].encode('ascii'), descriptor['sequence_file']), (canonical(original).encode('utf-8'), descriptor['residue_map_file'])):
                if len(data) != file['byte_length'] or hashlib.sha256(data).hexdigest() != file['sha256']:
                    raise ValueError('sequence_artifact_mismatch')
    if source['kind'] == 'explicit_map':
        if not same(source['map_file'], corr['map_file']):
            raise ValueError('input_digest_mismatch')
        rebuilt = validate_explicit_residue_map(corr['explicit_map'], map_file=source['map_file'], fixed=sequences['fixed'], moving=sequences['moving'])
        if not same(rebuilt, corr):
            raise ValueError('conflicting_identity')
    elif corr['alignment_native'] is not None:
        snapshot = corr['alignment_native']
        if not same(snapshot['descriptor'], source['alignment']):
            raise ValueError('alignment_operand_mismatch')
        rebuilt = correspondence_from_pairwise_sheet(snapshot['pairwise_sheet'], native=snapshot['native_result'], alignment=source['alignment'], fixed=sequences['fixed'], moving=sequences['moving'], fixed_descriptor=source['fixed_sequence_descriptor'], moving_descriptor=source['moving_sequence_descriptor'], orientation=source['orientation'])
        if not same(rebuilt, corr):
            raise ValueError('conflicting_identity')
    elif corr['population_available'] or not any((i['code'] == 'invalid_traceback' for i in corr['issues'])):
        raise ValueError('invalid_traceback')
    pairs = _join_pairs(sheet['structures'], sequences, corr, sheet['native_uncertainty'])
    if not same(pairs, sheet['coordinate_pairs']):
        raise ValueError('invalid_coordinate_identity')
    expected_files = _unique_records([item['file_identity'] for side in ('fixed', 'moving') for item in sheet['native_uncertainty'][side]['supplied_metadata']])
    if not same(expected_files, sheet['input_identities']['metadata_artifacts']):
        raise ValueError('metadata_join_conflict')
    expected_issues = _unique_records([i for side in ('fixed', 'moving') for i in sheet['structures'][side]['issues'] + sequences[side]['issues'] + sheet['native_uncertainty'][side]['issues']])
    expected_quals = _unique_records([q for side in ('fixed', 'moving') for q in sequences[side]['qualifications'] + sheet['native_uncertainty'][side]['qualifications']] + corr['qualifications'] + ['uncertainty_not_used_as_weight', 'original_coordinates_preserved'])
    if not same(expected_issues, sheet['parse_issues']) or not same(corr['issues'], sheet['correspondence_issues']) or (not same(expected_quals, sheet['source_qualifications'])):
        raise ValueError('conflicting_identity')
    declared = sheet['native_request']['declared_transform']
    if declared is not None:
        for side in ('fixed', 'moving'):
            if not same(declared[side + '_selection'], sequences[side]['selection']):
                raise ValueError('invalid_transform')

def _numerical_digest(sheet: ProteinStructureSheet) -> str:
    """The original baseline is deliberately outside numerical input identity."""
    return digest({key: value for key, value in sheet.items() if key != 'native_baseline'})
