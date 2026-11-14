"""Assemble native accounting inputs from actually received chemical records.

This is source preparation, not a balance calculation or evidence assessment.
The original public projections authenticate each selected field; the existing
native calculator and shared HPC owner retain their numerical responsibilities.
"""
from copy import deepcopy
import hashlib
import json
import math
import re

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema


VERSION = 'a110_reference_accounting_source_v1'
TOOL = 'chemistry.prepare_reference_accounting'
REQUEST = 'host.a110.reference_panel_request'
RESULT = 'host.a110.reference_panel_result'
PANEL = 'host.a110.reference_panel'
PROVENANCE = 'host.a110.reference_panel_provenance'
TABLES = {REQUEST: 'a110_reference_panel_requests', RESULT: 'a110_reference_panel_results'}


def require(condition, code):
    if not condition:
        raise ContractError('a110_reference_accounting_' + code)


class MissingRecords(ContractError):
    def __init__(self, refs, *, received=()):
        self.refs = set(refs)
        self.received = set(received)
        super().__init__('a110_reference_accounting_records_not_received',
            detail={'required_record_refs': sorted(self.refs)})


def catalog():
    ref = {'type': 'string', 'format': 'reference'}
    return {TOOL: {'resources': 'local', 'description':
        'Prepare a source panel for the existing chemistry.request_accounting_hpc '
        'operation from an actually received public Rhea reaction reference and '
        'selected ChEBI compound references. Use native_record_ref/state.query '
        'to inspect acquired records. Original native records and source records '
        'must also be received; named pointers grant no access. Authenticate the '
        'existing public projections against their original bytes. Match each '
        'participant by exact chemical accession, never by name, secondary ID, '
        'parent compound or a different protonation state. Select one compound '
        'record per accession; conflicting selections remain explicit. An empty '
        'chemical_refs array retains unknown chemistry while preserving the '
        'equation. Source-explicit constant coefficients and Rhea implicit-unit '
        'notation are supported; symbolic coefficients need further source '
        'information. Source left/right signs are an accounting convention, '
        'not physiological direction. Repeated occurrences remain separate '
        'participants, preserving transport locations and shared origins. '
        'Missing formulas or charges do not suppress other applicable inputs. '
        'The returned panel_source_ref can be used for native accounting, '
        'including partial panels. This operation calculates no balance, Gibbs '
        'energy, activity, evidence score or controller credit, and launches no '
        'job. Original conditions, energetics and resource models are not invented.',
        'input_schema': obj({'target_ref': ref, 'reaction_ref': ref,
            'chemical_refs': {'type': 'array', 'uniqueItems': True, 'items': ref}})}}


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def install(store):
    for table in TABLES.values():
        store.db.execute('CREATE TABLE IF NOT EXISTS ' + table +
            ' (source_ref TEXT PRIMARY KEY,body TEXT NOT NULL)')


def _publish(store, provider, body, *, request_ref=None, parents=(), scope=None):
    artifact = store.artifact(canonical(body), 'application/json')
    source = store.put('source', {'provider': provider, 'accession': digest(body),
        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact,
        'request_ref': request_ref, 'version': VERSION, 'retrieved_at': None,
        'parent_source_refs': sorted(set(parents)),
        'operand_refs': [] if scope is None else list(plain(scope)['subject_refs'])}, origin='tool')['id']
    if provider in TABLES:
        install(store)
        store.db.execute('INSERT OR IGNORE INTO ' + TABLES[provider] + ' VALUES(?,?)',
            (source, canonical(body)))
    return source


def read(store, reference, *, result=False):
    record = store.get(reference)
    provider = RESULT if result else REQUEST
    if record.get('provider') != provider:
        return None
    table = TABLES[provider]
    exists = store.db.execute('SELECT 1 FROM sqlite_master WHERE name=?', (table,)).fetchone()
    saved = store.db.execute('SELECT body FROM ' + table + ' WHERE source_ref=?',
        (reference,)).fetchone() if exists else None
    require(record['origin'] == 'tool' and record.get('version') == VERSION and saved is not None,
        'original_preparation_required')
    body = json.loads(saved[0])
    require(json.loads(store.get_artifact(record['artifact_ref'])) == body,
        'preparation_custody_conflict')
    return body


def request(store, args, *, context, known):
    validate_schema(args, catalog()[TOOL]['input_schema'])
    refs = {args['target_ref'], args['reaction_ref'], *args['chemical_refs']}
    require(refs <= set(known) and set(store.reference_subset(refs, plain(context.scope))) == refs,
        'original_operands_not_received')
    coverage = store.coverage(args['target_ref'])
    roots = {row['target_ref'] for row in coverage}
    require(coverage and len(roots) == 1 and store.scope_covers(coverage, plain(context.scope)),
        'original_question_scope_required')
    return _publish(store, REQUEST, {'version': VERSION, 'run_id': context.run_id,
        'operation': TOOL, 'scope': plain(context.scope), 'target_ref': next(iter(roots)),
        'target_regions': coverage, 'arguments': deepcopy(args), 'operand_refs': sorted(refs),
        'scientific_credit': None}, scope=context.scope)


def _immutable(record):
    body = {key: value for key, value in record.items() if key not in {'id', 'record_type', 'origin'}}
    require(record['id'] == identity(record['record_type'], {'origin': record['origin'], 'record': body}),
        'original_record_identity_conflict')


def _received(store, reference, known, used):
    if reference not in known:
        raise MissingRecords([reference], received=used)
    used.add(reference)
    return store.get(reference)


def _native(store, reference, kind, known, context, *, used=None):
    """Reproduce the selected original public projection, without private reads."""
    from .chemistry import rhea_response, rhea_row, chebi_response, chemical_row
    from .source_locations import received_source
    used = set() if used is None else used
    ref = _received(store, reference, known, used)
    require(ref['record_type'] == 'reference' and ref.get('reference_type') == kind
        and ref['origin'] == 'external', 'original_public_' + kind + '_reference_required')
    _immutable(ref)
    native_ref = ref.get('native_record_ref')
    require(native_ref is not None, 'selected_reference_has_no_original_native_record')
    native = _received(store, native_ref, known, used)
    require(native['record_type'] == ('reaction_record' if kind == 'reaction' else 'chemical_record')
        and native['origin'] == 'external' and native['source_ref'] == ref['source_ref']
        and native['accession'] == ref['accession'], 'selected_native_record_conflict')
    _immutable(native)
    source = _received(store, native['source_ref'], known, used)
    require(source['origin'] == 'external' and source.get('provider') == (
        'rhea' if kind == 'reaction' else 'chebi'), 'original_public_source_required')
    artifact = received_source(store, source['id'], 'original',
        permitted_inputs=tuple(sorted(known)), scope=plain(context.scope))
    raw = store.get_artifact(artifact['id'])
    require(hashlib.sha256(raw).hexdigest() == artifact['sha256'], 'source_artifact_identity_conflict')
    expected = {key: deepcopy(value) for key, value in native.items()
        if key not in {'id', 'record_type', 'origin', 'source_ref'}}
    if kind == 'reaction':
        for participant in expected['participants']:
            participant.pop('chemical_ref', None)
        rows = rhea_response(raw)['results']
        project = rhea_row
    else:
        search = native['representation'] == 'search_summary'
        body = chebi_response(raw, search=search)
        rows = body['results'] if search else [body]
        project = lambda row: chemical_row(row, search=search)
    matches = []
    for index, row in enumerate(rows):
        try:
            projected = project(row)
        except (ValueError, KeyError, TypeError):
            continue  # Other unselected malformed rows do not alter this record.
        if projected == expected:
            matches.append(index)
    require(bool(matches), 'native_projection_not_reproduced_from_original_source')
    witness = {'reference_ref': reference, 'native_record_ref': native_ref,
        'source_ref': source['id'], 'artifact_ref': artifact['id'],
        'matching_native_rows': matches, 'projection': 'original_rhea_row' if kind == 'reaction'
            else 'original_chemical_row', 'accession': native['accession'],
        'source_uri': source.get('uri'), 'retrieved_at': source.get('retrieved_at')}
    if kind == 'chemical':
        witness['source_properties'] = {key: deepcopy(native[key]) for key in (
            'representation', 'formula', 'charge', 'secondary_accessions',
            'source_modified_on', 'source_is_released', 'source_structure_id')}
    return native, witness, used


def _charge(value):
    if type(value) is int:
        return value
    if type(value) is float and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, str) and re.fullmatch(r'[+-]?[0-9]+', value.strip().replace('\u2212', '-')):
        return int(value.strip().replace('\u2212', '-'))
    return None


def _location(value):
    label = value.strip()
    if '?' in label or label.strip('() ').lower() in {'', 'unknown', 'unspecified', 'unreported'}:
        return None
    return label


def assemble(store, args, context, known, *, tracked_refs=None):
    """Copy authenticated source fields; leave scientific accounting to HPC."""
    from .chemistry import accession
    from .a110_chemical_accounting import rational, exact
    from .a110_chemical_contracts import source_schema
    refs = set() if tracked_refs is None else tracked_refs
    missing, required, sources = [], set(), set()
    reaction, reaction_witness, used = _native(store, args['reaction_ref'], 'reaction', known, context, used=refs)
    refs.update(used)
    sources.add(reaction['source_ref'])
    compounds, compound_witnesses, unresolved = {}, [], []
    for selected in args['chemical_refs']:
        try:
            compound, witness, used = _native(store, selected, 'chemical', known, context, used=refs)
        except MissingRecords as error:
            required.update(error.refs)
            refs.update(error.received)
            missing.append('selected_chemical_records_not_received')
            continue
        except ContractError as error:
            if str(error) != 'a110_reference_accounting_selected_reference_has_no_original_native_record':
                raise
            missing.append('selected_chemical_reference_has_no_original_native_record')
            continue
        refs.update(used)
        sources.add(compound['source_ref'])
        compounds.setdefault(compound['accession'], []).append((compound, witness))
        compound_witnesses.append(witness)
    species, participants, bindings = [], [], []
    symbolic = False
    for participant in reaction['participants']:
        try:
            amount = rational(participant['coefficient_expression'], positive=True)
            signed = exact(-amount if participant['side'] == 'left' else amount)
        except ValueError:
            symbolic = True
            missing.append('participant_requires_supported_constant_stoichiometry')
            signed = None
        try:
            cid = accession(participant['source_accession'], 'CHEBI')
            chemical_identity = True
        except ValueError:
            cid = participant['source_accession']
            chemical_identity = False
            missing.append('participant_has_no_exact_chebi_chemical_state')
        candidates = compounds.get(cid, [])
        compound, witness = candidates[0] if len(candidates) == 1 else (None, None)
        if len(candidates) > 1:
            missing.append('select_one_native_compound_record_per_chemical_state')
        elif not candidates:
            missing.append('participant_chemical_record_unavailable')
        if compound is None:
            formula, charge = None, None
            unresolved.append(cid)
        else:
            formula = compound['formula'] if isinstance(compound['formula'], str) and compound['formula'].strip() else None
            charge = _charge(compound['charge'])
            if formula is None:
                missing.append('source_formula_unreported')
            if charge is None:
                missing.append('source_formal_charge_unreported_or_unsupported')
        species_id = 'participant_' + str(participant['ordinal'])
        # Native source sides/occurrences remain distinct. Equal accessions do
        # not silently collapse a transport event across unknown compartments.
        locator = reaction['accession'] + '#' + species_id
        species.append({'id': species_id, 'entity_id': cid,
            'compartment': _location(participant['source_location']),
            'kind': 'chemical' if chemical_identity else 'unknown',
            'formula': formula, 'charge': charge,
            'source_locator': locator + (';native:' + witness['native_record_ref'] if witness else ';chemistry_unresolved')})
        if signed is not None:
            participants.append({'species_id': species_id, 'coefficient': signed,
                'source_locator': locator + ';native:' + reaction['id']})
        bindings.append({'native_participant': deepcopy(participant), 'panel_species_id': species_id,
            'selected_compound': witness, 'candidate_compound_refs': [row[1]['reference_ref'] for row in candidates],
            'source_formula': None if compound is None else compound['formula'],
            'source_charge': None if compound is None else compound['charge'],
            'declared_formula': formula, 'declared_charge': charge,
            'source_compartment_label': participant['source_location'],
            'sign_convention': 'source_left_negative_source_right_positive; not_physiological_direction'})
    # Acquisition time and record addresses do not turn the same chemistry into
    # independent datasets. The input values determine this semantic identity.
    basis = {'version': VERSION, 'reaction_accession': reaction['accession'],
        'source_direction': reaction['source_direction'],
        'species': [{key: value for key, value in row.items() if key != 'source_locator'} for row in species],
        'participants': [{key: value for key, value in row.items() if key != 'source_locator'} for row in participants]}
    dataset = None if symbolic else 'public_chemistry:' + digest(basis)
    panel = None if symbolic else {'version': 'a110_chemical_panel_v1', 'dataset_id': dataset,
        'origin': 'retained_extraction', 'species': species, 'reactions': [{
            'id': 'reaction_1', 'entity_id': reaction['accession'], 'participants': participants,
            'source_locator': reaction['accession'] + ';native:' + reaction['id'],
            'standard_gibbs': None, 'conditions': None, 'activities': []}],
        'pathway': [], 'carrier_pools': [], 'reported_constraints': None}
    if panel is not None:
        validate_schema(panel, source_schema())
    provenance = {'version': VERSION, 'operation': TOOL, 'reaction': reaction_witness,
        'source_reaction_record': deepcopy(reaction),
        'compounds': compound_witnesses, 'participant_bindings': bindings,
        'shared_source_keys': sorted({reaction['accession'], *compounds}),
        'source_direction': reaction['source_direction'], 'source_balanced_assertion': reaction['source_balanced'],
        'balance_calculated': False, 'missing': list(dict.fromkeys(missing)),
        'required_record_refs': sorted(required), 'unresolved_chemical_accessions': sorted(set(unresolved)),
        'dataset_id': dataset, 'scientific_credit': None, 'native_execution_requested': False,
        'dataset_identity_kind': 'declared_chemical_input_definition; not_an_experimental_dataset',
        'biological_scope': 'declared_source_equation_and_selected_or_unresolved_chemical_states; no_target_activity_or_physiological_transfer',
        'limitations': ['Database balance is a source assertion, not a calculated result.',
            'Source locations are declared source labels, not verified target compartments.',
            'No Gibbs data, activities, resource model, pathway or carrier pool is inferred.',
            'Original native accounting determines which formulas and electron conventions it supports.',
            'Source assembly and repeated source representations are not independent experiments.']}
    return panel, provenance, refs, sources


def refresh(store, context, known):
    install(store)
    known = set(known)
    generated, needs = [], []
    admitted = [(ref, value) for ref in sorted(known)
        if (value := read(store, ref, result=True)) is not None]
    for reference in sorted(known):
        original = read(store, reference)
        if original is None or original['run_id'] != context.run_id or not store.scope_contains(
                plain(context.scope), original['scope']):
            continue
        old = [body for _, body in admitted if body['request_ref'] == reference]
        if old and not any(set(body['input_dependencies']) <= known for body in old):
            continue  # An admitted narrow result does not reopen private inputs.
        reusable = [body for body in old if set(body['input_dependencies']) <= known
            and not set(body['required_record_refs']) & known
            and {body['provenance_source_ref'], *([] if body['panel_source_ref'] is None else
                [body['panel_source_ref']])} <= known
            and all(digest(store.get(ref)) == signature
                for ref, signature in body.get('input_signatures', {}).items())]
        if reusable:
            # Selected input records are immutable. Unrelated new facts do not
            # require re-reading every public source or republishing a panel.
            # Receipt of a specifically missing endpoint does trigger assembly.
            current = max(reusable, key=lambda body: len(body['input_dependencies']))
            if current['missing']:
                needs.append((reference, {'target_ref': original['target_ref'], 'policy': TOOL,
                    'missing': current['missing'], 'required_operands': {
                        'record_refs': current['required_record_refs'],
                        'chemical_accessions': current['unresolved_chemical_accessions']}}))
            continue
        refs = {reference, *(set(original['operand_refs']) & known)}
        panel, provenance, sources = None, {}, set()
        try:
            absent = set(original['operand_refs']) - known
            if absent:
                raise MissingRecords(absent)
            panel, provenance, used, sources = assemble(store, original['arguments'], context, known,
                tracked_refs=refs)
            refs.update(used)
        except MissingRecords as error:
            refs.update(error.received)
            provenance = {'version': VERSION, 'missing': ['original_native_records_or_sources_not_received'],
                'required_record_refs': sorted(error.refs), 'scientific_credit': None,
                'native_execution_requested': False}
        except (ValueError, KeyError, TypeError) as error:
            provenance = {'version': VERSION, 'missing': [str(error)], 'required_record_refs': [],
                'scientific_credit': None, 'native_execution_requested': False}
        require(refs <= known, 'unreceived_source_dependency')
        raw_request = store.get(reference)['artifact_ref']
        prepared_artifact = None if panel is None else store.artifact(canonical(panel), 'application/json')
        provenance = {**provenance, 'scope': original['scope'], 'target_ref': original['target_ref'],
            'request_ref': reference, 'panel_artifact_ref': prepared_artifact,
            'input_dependencies': sorted(refs)}
        proof_ref = _publish(store, PROVENANCE, provenance, request_ref=raw_request,
            parents=sources, scope=original['scope'])
        panel_ref = None if panel is None else _publish(store, PANEL, panel,
            request_ref=raw_request, parents=[proof_ref, *sources], scope=original['scope'])
        result = {'version': VERSION, 'scope': original['scope'], 'target_ref': original['target_ref'],
            'request_ref': reference, 'operation': TOOL, 'input_dependencies': sorted(refs),
            'input_signatures': {ref: digest(store.get(ref)) for ref in sorted(refs)},
            'panel_source_ref': panel_ref, 'panel_artifact_ref': prepared_artifact,
            'provenance_source_ref': proof_ref,
            'state': 'reference_panel_unavailable' if panel is None else
                'reference_panel_partial' if provenance['missing'] else 'reference_panel_available',
            'missing': provenance['missing'], 'required_record_refs': provenance['required_record_refs'],
            'unresolved_chemical_accessions': provenance.get('unresolved_chemical_accessions', []),
            'dataset_id': provenance.get('dataset_id'), 'scientific_credit': None,
            'dataset_identity_kind': 'declared_chemical_input_definition; not_an_experimental_dataset',
            'native_execution_requested': False}
        result_ref = _publish(store, RESULT, result, request_ref=raw_request,
            parents=[proof_ref, *([] if panel_ref is None else [panel_ref])], scope=original['scope'])
        generated.extend([proof_ref, *([] if panel_ref is None else [panel_ref]), result_ref])
        if result['missing']:
            needs.append((reference, {'target_ref': original['target_ref'], 'policy': TOOL,
                'missing': result['missing'], 'required_operands': {
                    'record_refs': result['required_record_refs'],
                    'chemical_accessions': result['unresolved_chemical_accessions']}}))
    return list(dict.fromkeys(generated)), needs


def received(store, references, scope):
    """Show received preparation results without treating them as scores."""
    known = set(references)
    rows = [{'source_ref': ref, **deepcopy(body)} for ref in sorted(known)
        if (body := read(store, ref, result=True)) is not None
        and store.scope_contains(plain(scope), body['scope'])]
    for row in rows:
        row['changed_received_input_refs'] = [ref for ref, signature in row['input_signatures'].items()
            if ref in known and digest(store.get(ref)) != signature]
    for row in rows:
        row['current'] = not row['changed_received_input_refs'] and not any(
            other['request_ref'] == row['request_ref'] and not other['changed_received_input_refs']
            and set(row['input_dependencies']) < set(other['input_dependencies']) for other in rows)
    return rows
