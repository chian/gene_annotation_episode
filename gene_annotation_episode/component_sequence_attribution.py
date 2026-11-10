"""Particular received sequence/region correspondence, with no axis reducer."""
from copy import deepcopy

from .domain import ContractError


MAX_MAP_POSITIONS = 50_000
RESOLVED_AMINO_ACIDS = frozenset('ACDEFGHIKLMNPQRSTVWYOU')


def require(condition, code):
    if not condition:
        raise ContractError('component_sequence_'+code)


def received_sequence(store, reference):
    from .tools import ToolRegistry
    current = reference
    while True:
        require(store.subject_length(current) <= MAX_MAP_POSITIONS,
            'coordinator_capacity_exceeded; shared_hpc_verification_required')
        row = store.get(current)
        if row['record_type'] != 'feature':
            break
        current = row['subject_ref']
    class Reader:
        _sequence = ToolRegistry._sequence
        def __init__(self, source_store):
            self.store = source_store
    value = Reader(store)._sequence(reference).strip().upper()
    require(len(value) <= MAX_MAP_POSITIONS, 'coordinator_capacity_exceeded')
    return value


def protein_sequence(store, reference):
    require(store.subject_molecule(reference) == 'protein', 'actual_protein_sequence_required')
    return received_sequence(store, reference)


def _complete_identity(actual_ref, component_ref, actual, expected, selected, alignment_ref):
    """Keep selected indices in identical complete received sequence frames.

    Comparing the selected peptide with the complete reference would otherwise
    lose an already known correspondence. Equality of a selected peptide alone
    does not establish this complete-frame identity.
    """
    if alignment_ref is not None or actual != expected:
        return None
    from .sequence_attribution import digest
    return {'state': 'evaluated', 'missing': [], 'target_ref': actual_ref,
        'actual_subject_ref': actual_ref, 'reference_subject_ref': component_ref,
        'reference_sequence_sha256': digest(expected),
        'route': 'identity_of_complete_received_protein_sequences',
        'correspondence_basis': 'complete_received_sequences_identical; same_zero_based_residue_indices',
        'coordinate_system': 'zero_based_protein_symbols',
        'pairs': [[position, position, actual[position], expected[position], 1.] for position in selected],
        'identity_distance': 0., 'coverage': len(selected)/max(len(selected), len(expected)),
        'evidence_refs': sorted({actual_ref, component_ref}),
        'functional_property': 'unestablished_by_sequence_correspondence_alone'}


def _received_component_link(store, actual_ref, component_ref, known, *, positions, alignment_ref):
    from .a103_attachments import component_link
    if {actual_ref, component_ref} <= known:
        actual, expected = protein_sequence(store, actual_ref), protein_sequence(store, component_ref)
        selected = list(range(len(actual))) if positions is None else positions
        identity = _complete_identity(actual_ref, component_ref, actual, expected, selected, alignment_ref)
        if identity is not None:
            return identity
    return component_link(store, actual_ref, component_ref, known,
        positions=positions, alignment_ref=alignment_ref)


def _protein_frame(store, reference, known):
    """Retain a feature's explicit path into a received protein query frame.

    Feature extraction is in protein symbols, independently of a translated
    product's nucleotide footprint. No inferred residue offset or private
    parent reference is used to interpret an alignment.
    """
    current, path, refs = reference, [], set()
    while current in known:
        refs.add(current)
        row = store.get(current)
        if row['record_type'] != 'feature':
            break
        require(store.subject_molecule(current) == 'protein' and row['strand'] in {'+', '.'},
            'protein_region_requires_nonreversed_protein_coordinates')
        path.append({'feature_ref': current, 'subject_ref': row['subject_ref'],
            'segments': deepcopy(row['segments']), 'strand': row['strand']})
        current = row['subject_ref']
    frame = {'subject_ref': reference, 'native_subject_ref': current,
        'feature_path': path, 'coordinate_system': 'zero_based_protein_symbols',
        'missing': [], 'required_record_refs': []}
    if current not in known:
        frame['missing'] = ['received_protein_region_parent_sequence']
        frame['required_record_refs'] = [current]
        return frame, None, refs
    root_sequence = protein_sequence(store, current)
    lift = list(range(len(root_sequence)))
    for row in reversed(path):
        require(all(0 <= segment['start'] < segment['end'] <= len(lift)
            for segment in row['segments']), 'protein_region_segments_outside_parent')
        lift = [lift[position] for segment in row['segments']
            for position in range(segment['start'], segment['end'])]
        require(len(lift) <= MAX_MAP_POSITIONS and len(lift) == len(set(lift)),
            'protein_region_requires_bounded_injective_coordinates')
    require(''.join(root_sequence[position] for position in lift) == protein_sequence(store, reference),
        'protein_region_sequence_and_coordinate_path_conflict')
    return frame, lift, refs


def _region_correspondence(store, actual_ref, component_ref, known, actual, expected,
                           positions, alignment_ref):
    from .sequence_attribution import digest
    actual_frame, actual_lift, actual_refs = _protein_frame(store, actual_ref, known)
    # A native result may already compare to this exact reference-region
    # sequence. Do not require its full parent merely to use that direct map.
    reference_frame = {'subject_ref': component_ref, 'native_subject_ref': component_ref,
        'feature_path': [], 'coordinate_system': 'zero_based_protein_symbols',
        'scope': 'exact_received_component_sequence',
        'native_reference_identity': 'complete_sequence_match; original_reference_ids_retained_in_native_witnesses',
        'missing': [], 'required_record_refs': []}
    reference_lift, reference_refs = list(range(len(expected))), {component_ref}
    frames = {'actual': actual_frame, 'reference': reference_frame}
    refs = actual_refs | reference_refs
    if actual_frame['missing']:
        return {'state': 'unresolved', 'missing': actual_frame['missing'],
            'required_record_refs': actual_frame['required_record_refs'],
            'actual_subject_ref': actual_ref, 'reference_subject_ref': component_ref,
            'coordinate_frames': frames, 'pairs': [], 'identity_distance': None, 'coverage': None,
            'functional_property': 'unestablished_by_sequence_correspondence_alone'}, refs
    selected = list(range(len(actual))) if positions is None else positions
    native = _received_component_link(store, actual_frame['native_subject_ref'], reference_frame['native_subject_ref'],
        known, positions=[actual_lift[position] for position in selected], alignment_ref=alignment_ref)
    if (store.get(component_ref)['record_type'] == 'feature' and native['state'] == 'unresolved'
            and not native.get('witnesses')):
        reference_frame, reference_lift, reference_refs = _protein_frame(store, component_ref, known)
        frames['reference'] = reference_frame
        refs.update(reference_refs)
        if reference_frame['missing']:
            return {'state': 'unresolved', 'missing': reference_frame['missing'],
                'required_record_refs': reference_frame['required_record_refs'],
                'actual_subject_ref': actual_ref, 'reference_subject_ref': component_ref,
                'coordinate_frames': frames, 'pairs': [], 'identity_distance': None, 'coverage': None,
                'functional_property': 'unestablished_by_sequence_correspondence_alone'}, refs
        native = _received_component_link(store, actual_frame['native_subject_ref'], reference_frame['native_subject_ref'],
            known, positions=[actual_lift[position] for position in selected], alignment_ref=alignment_ref)
    inverse_actual = {position: local for local, position in enumerate(actual_lift)}
    inverse_reference = {position: local for local, position in enumerate(reference_lift)}
    selected_set = set(selected)
    pairs = [[inverse_actual[i], inverse_reference[j], a, b, strength]
        for i, j, a, b, strength in native.get('pairs', [])
        if i in inverse_actual and inverse_actual[i] in selected_set and j in inverse_reference]
    require(all(actual[i] == a and expected[j] == b for i, j, a, b, _ in pairs),
        'native_region_pair_symbols_conflict')
    conflicts_actual = [inverse_actual[position] for position in native.get('conflicting_target_positions', [])
        if position in inverse_actual and inverse_actual[position] in selected_set]
    conflicts_reference = [inverse_reference[position] for position in native.get('conflicting_reference_positions', [])
        if position in inverse_reference]
    resolved = bool(pairs) and not conflicts_actual and not conflicts_reference
    excluded = {'factor', 'pairs', 'identity_distance', 'coverage', 'target_ref',
        'actual_subject_ref', 'reference_subject_ref', 'reference_sequence_sha256',
        'conflicting_target_positions', 'conflicting_reference_positions', 'state', 'missing'}
    link = {key: deepcopy(value) for key, value in native.items() if key not in excluded}
    link.update({'state': 'evaluated' if resolved else 'unresolved',
        'missing': [] if resolved else native.get('missing') or ['unambiguous_native_map_in_requested_regions'],
        'target_ref': actual_ref, 'actual_subject_ref': actual_ref, 'reference_subject_ref': component_ref,
        'reference_sequence_sha256': digest(expected), 'coordinate_frames': frames,
        'route': ('received_protein_feature_coordinates_projected_from_complete_sequence_identity'
            if native.get('route') == 'identity_of_complete_received_protein_sequences' else
            'received_protein_feature_coordinates_projected_from_native_correspondence'),
        'native_correspondence_route': native.get('route', 'received_native_sequence_map'),
        'native_reference_sequence_sha256': native.get('reference_sequence_sha256'),
        'conflicting_target_positions': conflicts_actual, 'conflicting_reference_positions': conflicts_reference,
        'pairs': pairs, 'identity_distance': sum(a != b for _, _, a, b, _ in pairs)/len(pairs) if pairs else None,
        'coverage': len(pairs)/max(len(selected), len(expected)) if pairs else None,
        'distance_scope': 'unambiguous_received_pairs_in_requested_regions; unmatched_positions_not_imputed'})
    refs.update(native.get('evidence_refs', []))
    link['evidence_refs'] = sorted(refs)
    return link, refs


def protein_correspondence(store, actual_ref, component_ref, known, *, positions=None, alignment_ref=None):
    from .a103_attachments import component_link
    known = set(known)
    require({actual_ref, component_ref} <= known, 'particular_sequences_not_received')
    actual = protein_sequence(store, actual_ref)
    expected = protein_sequence(store, component_ref)
    require(positions is None or positions and len(set(positions)) == len(positions)
        and all(type(p) is int and 0 <= p < len(actual) for p in positions), 'selected_positions_invalid')
    selected_order = list(range(len(actual))) if positions is None else positions
    identity = _complete_identity(actual_ref, component_ref, actual, expected, selected_order, alignment_ref)
    if identity is not None:
        link, refs = identity, {actual_ref, component_ref}
    elif (any(store.get(ref)['record_type'] == 'feature' for ref in (actual_ref, component_ref))
            and ''.join(actual[position] for position in selected_order) != expected):
        link, refs = _region_correspondence(store, actual_ref, component_ref, known, actual, expected,
            positions, alignment_ref)
    else:
        link = component_link(store, actual_ref, component_ref, known, positions=positions, alignment_ref=alignment_ref)
        refs = set(link.get('evidence_refs', [])) | {actual_ref, component_ref}
    for witness in link.get('witnesses', []):
        refs.update(witness[key] for key in ('observation_ref', 'source_ref', 'reference_ref'))
    link.pop('factor', None)
    selected = set(range(len(actual)) if positions is None else positions)
    reference_positions = {row[1] for row in link.get('pairs', []) if row[0] in selected}
    link['requested_actual_position_count'] = len(selected)
    link['reference_position_count'] = len(expected)
    link['mapped_pair_count'] = sum(row[0] in selected for row in link.get('pairs', []))
    link['identity_distance_formula'] = 'literal_mismatches/unambiguous_mapped_pairs; no_gap_imputation'
    link['coverage_formula'] = 'mapped_pairs/max(requested_actual_positions,reference_positions)'
    ambiguous_actual = [{'position': position, 'symbol': actual[position]} for position in sorted(selected)
        if actual[position] not in RESOLVED_AMINO_ACIDS]
    ambiguous_reference = [{'position': position, 'symbol': expected[position]} for position in sorted(reference_positions)
        if expected[position] not in RESOLVED_AMINO_ACIDS]
    link['identity_distance_basis'] = 'literal_received_symbols_on_saved_correspondence; not_evolutionary_or_functional_distance'
    link['unresolved_actual_symbols'] = ambiguous_actual
    link['unresolved_reference_symbols'] = ambiguous_reference
    if ambiguous_actual or ambiguous_reference:
        link['missing'] = list(dict.fromkeys([*link['missing'], 'resolved_amino_acid_identity_in_requested_scope']))
    return link, refs
