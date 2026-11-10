"""Explicit source-role/sequence associations for particular evidence uses.

Experimental role references remain immutable and unsequenced. This adapter
checks a received source declaration against an actual protein reference. It
retains the declaration's scope, native sequence witness and experimental link;
it does not turn a name, shared paper or homolog into experimental identity.
"""
from copy import deepcopy
import html
import re

from .communication import plain
from .domain import ContractError, obj
from .component_sequence_attribution import protein_sequence, RESOLVED_AMINO_ACIDS


VERSION = 'source_role_sequence_identity_v1'
TOOLS = {'A107': 'partner.source_identity_evidence',
         'A110': 'chemistry.source_identity_evidence'}


def require(condition, code):
    if not condition:
        raise ContractError('source_identity_' + code)


def catalog(axis):
    ref = {'type': 'string', 'format': 'reference'}
    optional = {'anyOf': [ref, {'type': 'null'}]}
    return {TOOLS[axis]: {'resources': 'local', 'description':
        'Bind one original experimental role reference to an actually received '
        'protein sequence through a received source_content observation. The '
        'observation must explicitly name the role as a subject and the protein '
        'as a subject/reference_ref measurement; its exact source quote must '
        'contain the role label and a complete matching protein sequence or an '
        'actual acquired accession. For a particular experiment, explicitly link '
        'its reference from the observation. Choose whole_protein, protein_component '
        'or unspecified according to the source declaration. Component identity '
        'does not establish whole-complex identity. An accession alone retains '
        'unknown experimental sequence/construct identity and is useful as a search '
        'lead. Names alone are insufficient. Original assay roles and numbers are '
        'preserved. An explicit revision retains its predecessor and reason. '
        'This performs bounded source inspection, not an alignment, activity assay '
        'or new scalar calculation.',
        'input_schema': obj({'target_ref': ref, 'source_role_ref': ref,
            'actual_ref': ref, 'observation_ref': ref, 'experiment_ref': optional,
            'identity_scope': {'enum': ['whole_protein', 'protein_component', 'unspecified']},
            'revises_identity_ref': optional,
            'revision_reason': {'type': ['string', 'null'], 'minLength': 1}})}}


def read(store, reference, known):
    require(reference in known, 'evidence_not_received')
    record = store.get(reference)
    if record.get('provider') == 'host.a107.qualification':
        from .a107_qualification import _read
        body = _read(store, reference, graded=True)
    elif record.get('provider') == 'host.a110.qualification':
        from .a110_qualification import read as qualified_read
        body = qualified_read(store, reference, qualified=True)
    else:
        raise ContractError('source_identity_original_qualified_evidence_required')
    require(body.get('operation') in TOOLS.values()
        and body['result'].get('version') == VERSION, 'original_identity_result_required')
    return body


def successors(store, reference, known):
    """Follow only actually received explicit identity corrections."""
    known = set(known)
    links = []
    for candidate in sorted(known):
        record = store.get(candidate)
        if record.get('provider') not in {'host.a107.qualification', 'host.a110.qualification'}:
            continue
        # Ordinary qualified numerical evidence is not an identity declaration.
        try:
            body = read(store, candidate, known)
        except ContractError as error:
            if str(error) == 'source_identity_original_identity_result_required':
                continue
            raise
        previous = body['result'].get('revises_identity_ref')
        if previous is not None:
            links.append((candidate, previous))
    retired, found = {reference}, set()
    while True:
        additions = {candidate for candidate, previous in links if previous in retired} - retired
        if not additions:
            return sorted(found)
        retired.update(additions)
        found.update(additions)


def _plain_text(value):
    return ' '.join(html.unescape(re.sub(r'<[^>]*>', '', value)).split())


def calculate(store, args, context, known):
    """Qualify the source's selected identity declaration without changing it."""
    from .source_locations import received_source
    known = set(known)
    refs = {value for key, value in args.items() if key.endswith('_ref') and value is not None}
    require(refs <= known, 'operands_not_received')
    role, observation = store.get(args['source_role_ref']), store.get(args['observation_ref'])
    actual = store.get(args['actual_ref'])
    sequence = protein_sequence(store, args['actual_ref'])
    missing = []
    require((args['revises_identity_ref'] is None) == (args['revision_reason'] is None),
        'revision_reason_required')
    if args['revision_reason'] is not None:
        require(bool(args['revision_reason'].strip()), 'revision_reason_required')
    if args['revises_identity_ref'] is not None:
        previous = read(store, args['revises_identity_ref'], known)['result']
        require(previous['source_role_ref'] == args['source_role_ref']
            and previous['experiment_ref'] == args['experiment_ref'],
            'revision_changes_source_role_or_experiment')
    require(observation['record_type'] == 'observation', 'declaration_observation_required')
    links = {*observation['subject_refs'], *observation['source_subject_refs'],
             *observation.get('dependencies', [])}
    references = {row['value'].get('ref') for row in observation['measurements']
        if row['name'] == 'reference_ref' and row['value']['type'] == 'reference'}
    if args['source_role_ref'] not in links:
        missing.append('declaration_not_bound_to_original_source_role')
    if args['actual_ref'] not in links | references:
        missing.append('declaration_not_bound_to_actual_protein_reference')
    if args['experiment_ref'] is not None and args['experiment_ref'] not in links:
        missing.append('declaration_not_bound_to_selected_experiment')
    if args['identity_scope'] != 'whole_protein':
        missing.append('whole_assayed_entity_identity_not_established')
    if role.get('reference_type') == 'complex' and args['identity_scope'] == 'whole_protein':
        missing.append('a_protein_sequence_does_not_identify_a_whole_complex')
    anchor = observation.get('anchor')
    source = observation['source_ref']
    refs.add(source)
    require(refs <= known, 'source_not_received')
    sequence_witness = None
    accession_witness = None
    if observation.get('kind') != 'source_content' or anchor is None:
        missing.append('source_identity_declaration_witness_required')
    else:
        require(anchor['source_ref'] == source, 'declaration_source_conflict')
        representation = None
        for selected in ('original', 'text'):
            record = store.get(source)
            if (record.get('artifact_ref') if selected == 'original' else record.get('text_ref')) == anchor['artifact_ref']:
                representation = selected
                break
        require(representation is not None, 'declaration_representation_not_received')
        artifact = received_source(store, source, representation,
            permitted_inputs=tuple(sorted(known)), scope=plain(context.scope))
        width = anchor['end'] - anchor['start']
        require(0 <= anchor['start'] < anchor['end'] <= artifact['size'], 'declaration_bounds_invalid')
        # The existing source scanner's window is a memory/transfer capacity,
        # not a research stopping budget. Oversized declarations remain explicit.
        if width > 1048576:
            missing.append('source_identity_declaration_exceeds_source_reader_capacity')
        else:
            path = store.path/'artifacts'/artifact['sha256'][:2]/artifact['sha256']
            with path.open('rb') as stream:
                stream.seek(anchor['start'])
                raw = stream.read(width)
            require(raw.decode('utf-8') == anchor['quote'], 'declaration_bytes_conflict')
            text = _plain_text(anchor['quote'])
            if not role.get('label') or _plain_text(role['label']) not in text:
                missing.append('identity_declaration_does_not_name_original_source_role')
            else:
                # Read bounded context from the same received source so the
                # observation's last residue is not mistaken for a clipped
                # source block. Only a complete candidate inside the original
                # observation can establish this declaration; surrounding
                # sequences and a continuation beyond its quote cannot.
                from .source_sequences import scan
                class Reader:
                    def __init__(self):
                        self.store = store
                    def _check_sequence_operand(self, reference, scope):
                        require(reference in known, 'sequence_not_received')
                        return store.get(reference)
                    def _sequence(self, reference):
                        return protein_sequence(store, reference)
                matches, cursor = [], anchor['start']
                while True:
                    scanned, _ = scan(Reader(), {'subject_ref': args['actual_ref'],
                        'source_ref': source, 'representation': representation,
                        'offset': cursor, 'window_bytes': min(1048576, artifact['size'] - cursor),
                        'minimum_length': 8}, plain(context.scope), tuple(sorted(known)))
                    matches.extend(candidate for candidate in scanned['candidates']
                        if candidate['comparison']['relationship'] == 'full_string_equal'
                        and anchor['start'] <= candidate['start'] < candidate['end'] <= anchor['end']
                        and not candidate['unresolved_hyphen_offsets']
                        and not candidate['touches_window_boundary'])
                    continuation = scanned.get('next_query')
                    if continuation is None or continuation['offset'] >= anchor['end']:
                        break
                    # Candidate pagination is a reader capacity, not a stopping
                    # decision. Finish this exact declaration. Retain one
                    # preceding UTF-8 character so a complete next candidate
                    # is not mistaken for a fragment at a new page boundary.
                    next_cursor = continuation['offset'] - 1
                    while (next_cursor > anchor['start']
                            and raw[next_cursor - anchor['start']] & 0xc0 == 0x80):
                        next_cursor -= 1
                    require(cursor < next_cursor < anchor['end'], 'declaration_scan_did_not_advance')
                    cursor = next_cursor
                if matches:
                    sequence_witness = {'source_ref': source, 'artifact_ref': artifact['id'],
                        'representation': representation, 'candidate': deepcopy(matches[0]),
                        'additional_occurrences': deepcopy(matches[1:]),
                        'dependence': 'same_source_declaration; not_independent_experiments',
                        'normalization': scanned['normalization']}
                if sequence_witness is None:
                    # A native acquired accession is a declared reference link,
                    # not an observed sequence of the experimental construct.
                    accession = actual.get('accession')
                    actual_source = actual.get('source_ref')
                    provider = store.get(actual_source).get('provider') if actual_source in known else None
                    if (actual.get('origin') == 'tool' and actual.get('reference_type') == 'protein'
                            and provider in {'uniprot', 'ncbi_protein', 'ncbi.protein'}
                            and accession and accession in text):
                        accession_witness = {'accession': accession, 'reference_source_ref': actual_source,
                            'source_declaration_ref': source, 'anchor': deepcopy(anchor)}
                        refs.add(actual_source)
                    missing.append('actual_assayed_protein_sequence_not_established')
    unresolved = [index for index, symbol in enumerate(sequence) if symbol not in RESOLVED_AMINO_ACIDS]
    if unresolved:
        missing.append('specific_source_protein_residue_identity_unresolved')
    if sequence_witness is None and accession_witness is None:
        missing.append('source_molecule_to_protein_identity_unestablished')
    return {'version': VERSION,
        'state': 'source_sequence_identity_retained' if not missing else 'source_identity_unresolved',
        'missing': list(dict.fromkeys(missing)), 'source_role_ref': args['source_role_ref'],
        'actual_ref': args['actual_ref'], 'observation_ref': args['observation_ref'],
        'experiment_ref': args['experiment_ref'], 'identity_scope': args['identity_scope'],
        'native_sequence_witness': sequence_witness, 'accession_witness': accession_witness,
        'unresolved_actual_positions': unresolved,
        'revises_identity_ref': args['revises_identity_ref'], 'revision_reason': args['revision_reason'],
        'source_declaration_anchor': deepcopy(anchor),
        'interpretation': 'source_identity_declaration_and_literal_sequence_witness; '
            'not_new_measurement_validation_or_target_activity',
        'measurement_scope': 'original_experiment_and_source_role; no_new_region_measurement'}, refs


def use(store, reference, source_role, known, *, experiment_refs=()):
    """Consume an actual qualified identity without reading undelivered peers."""
    body = read(store, reference, known)
    result = deepcopy(body['result'])
    require(result['source_role_ref'] == source_role, 'selected_source_role_mismatch')
    refs = {reference}
    required = {result['source_role_ref'], result['actual_ref'], result['observation_ref']}
    if result['experiment_ref'] is not None:
        required.add(result['experiment_ref'])
    missing = list(result['missing'])
    absent = sorted(required - set(known))
    if absent:
        missing.append('source_identity_endpoints_not_received')
    refs.update(required & set(known))
    if experiment_refs and (len(set(experiment_refs)) != 1 or result['experiment_ref'] not in experiment_refs):
        missing.append('source_identity_to_selected_experiment_link_unestablished')
    revisions = successors(store, reference, known)
    refs.update(revisions)
    if revisions:
        missing.append('source_identity_superseded_by_received_revision')
    result.update(identity_ref=reference, superseding_identity_refs=revisions,
        use_state='source_identity_use_retained' if not missing else 'source_identity_use_unresolved',
        missing=list(dict.fromkeys(missing)), required_record_refs=absent)
    return result, refs


def qualification_changes(store, row, known):
    """Flag received corrections without replacing old scientific operands."""
    selected = set()
    def visit(value):
        if isinstance(value, dict):
            if value.get('identity_ref') is not None:
                selected.add(value['identity_ref'])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    if row.get('operation') in TOOLS.values():
        selected.add(row['source_ref'])
    visit(row.get('result', {}))
    return sorted({revision for reference in selected for revision in successors(store, reference, known)}
        - set(row.get('qualification_dependencies', [])))
