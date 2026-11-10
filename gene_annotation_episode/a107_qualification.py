"""Per-use A107 qualification over actually received scientific records.

No sequence search or native detector runs here. Original numerical components,
source interpretations and particular sequence correspondences stay distinct.
"""
from copy import deepcopy
import hashlib
import json

from .communication import plain
from .domain import ContractError, canonical
from .tool_grading_artifacts import retain_tool_grading, source_tool_grading_entries
from .component_sequence_attribution import (MAX_MAP_POSITIONS,
    RESOLVED_AMINO_ACIDS, protein_sequence, protein_correspondence, received_sequence)


VERSION = 'a107_received_qualification_v1'
REQUEST_PROVIDER = 'host.a107.qualification_request'
PROVIDER = 'host.a107.qualification'
FACT_SOURCE = 'a107_qualification_records'
EXECUTION_SOURCE = 'a107_genomic_execution_records'
REQUIREMENT_EXPERIMENT_BINDING_VERSION = 'a107_requirement_experiment_binding_v1'


def require(condition, code):
    if not condition:
        raise ContractError(code)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def install(store):
    for table in ('a107_qualification_requests', 'a107_qualifications'):
        store.db.execute('CREATE TABLE IF NOT EXISTS '+table+' (source_ref TEXT PRIMARY KEY,body TEXT NOT NULL)')


def _publish(store, provider, body, *, graded=False):
    artifact = store.artifact(canonical(body), 'application/json')
    grading = retain_tool_grading(store, provider=provider, native_artifact_ref=artifact,
        grading={'grader': VERSION, 'failure': None, 'sheet': body}) if graded else None
    source = store.put('source', {'provider': provider, 'accession': digest(body), 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': VERSION,
        'retrieved_at': None, 'operand_refs': body['scope']['subject_refs'],
        **({'auxiliary_artifact_refs': [grading]} if graded else {})}, origin='tool')['id']
    table = 'a107_qualifications' if graded else 'a107_qualification_requests'
    store.db.execute('INSERT OR IGNORE INTO '+table+' VALUES(?,?)', (source, canonical(body)))
    return source


def _read(store, reference, *, graded=False):
    record = store.get(reference)
    provider = PROVIDER if graded else REQUEST_PROVIDER
    if record.get('provider') != provider:
        return None
    table = 'a107_qualifications' if graded else 'a107_qualification_requests'
    exists = store.db.execute('SELECT 1 FROM sqlite_master WHERE name=?', (table,)).fetchone()
    saved = store.db.execute('SELECT body FROM '+table+' WHERE source_ref=?', (reference,)).fetchone() if exists else None
    require(saved is not None and record['origin'] == 'tool' and record.get('version') == VERSION,
        'a107_original_qualification_grant_required')
    body = json.loads(saved[0])
    require(json.loads(store.get_artifact(record['artifact_ref'])) == body, 'a107_qualification_custody_conflict')
    if graded:
        entries = source_tool_grading_entries(store, reference)
        require(len(entries) == 1 and entries[0]['grading'] == {
            'grader': VERSION, 'failure': None, 'sheet': body}, 'a107_qualification_grader_conflict')
    return body


def request(store, operation, args, *, context, known):
    """Freeze original operands, never create a biological score or execution."""
    from .a107_tools import catalog
    from .domain import validate_schema
    validate_schema(args, catalog()[operation]['input_schema'])
    target = args['target_ref']
    require(target in known, 'a107_target_not_received')
    coverage = store.coverage(target)
    require(coverage and store.scope_covers(coverage, plain(context.scope)), 'a107_target_outside_original_scope')
    roots = {row['target_ref'] for row in coverage}
    require(len(roots) == 1, 'a107_single_original_target_required')
    refs = {target}
    for field in ('actual_ref', 'component_ref', 'assessment_ref', 'detection_ref', 'alignment_ref', 'sheet_ref', 'expression_ref', 'encoded_product_ref', 'locus_binding_ref',
                  'source_role_ref', 'observation_ref', 'experiment_ref', 'revises_identity_ref',
                  'component_identity_ref', 'subject_identity_ref', 'subject_alignment_ref', 'requirement_ref'):
        if args.get(field) is not None:
            refs.add(args[field])
    require(refs <= known, 'a107_qualification_operands_not_received')
    require(set(store.reference_subset(refs, plain(context.scope))) == refs, 'a107_qualification_operand_outside_scope')
    install(store)
    body = {'version': VERSION, 'operation': operation, 'arguments': deepcopy(args),
        'run_id': context.run_id, 'scope': plain(context.scope), 'target_ref': next(iter(roots)),
        'target_regions': [[row['start'], row['end']] for row in coverage],
        'operand_refs': sorted(refs), 'scientific_credit': None}
    return _publish(store, REQUEST_PROVIDER, body)


def _protein(store, reference):
    return protein_sequence(store, reference)


def _map(store, args, known):
    selected = args['positions']
    link, refs = protein_correspondence(store, args['actual_ref'], args['component_ref'], known,
        positions=selected, alignment_ref=args['alignment_ref'])
    return {'state': link['state'], 'missing': list(link['missing']),
        'required_record_refs': list(link.get('required_record_refs', [])),
        'component_correspondence': link,
        'required_actual_positions': selected,
        'functional_requirement': 'not_established_by_sequence_correspondence',
        'interpretation': 'particular_received_native_map_or_exact_peptide_identity'}, refs


def _requirement(store, args, known, context):
    assessment = store.get(args['assessment_ref'])
    require(assessment['record_type'] == 'assessment', 'a107_requirement_assessment_required')
    refs = {args['assessment_ref'], assessment['hypothesis_ref'], assessment['observation_ref']}
    require(refs <= known, 'a107_requirement_findings_not_received')
    hypothesis, observation = (store.get(assessment[key]) for key in ('hypothesis_ref', 'observation_ref'))
    refs.add(observation['source_ref'])
    require(refs <= known, 'a107_requirement_source_not_received')
    finding = assessment.get('investigation_finding')
    require(finding is not None, 'a107_source_requirement_finding_required')
    claim = finding['source_claim']
    require(claim['predicate'] in {'requires', 'partner_dependence'}, 'a107_specific_source_requirement_required')
    partners = ({claim['value']['ref']} if claim['value']['type'] == 'reference' else
        {row['ref'] for row in claim['value'].get('roles', []) if row['role'] == 'partner'})
    require(args['component_ref'] in partners, 'a107_requirement_particular_partner_mismatch')
    refs.update([*claim['subject_refs'], *claim['context_refs'], *partners,
        *assessment['condition_refs'], *assessment['assumption_refs'],
        *finding['qualification']['context_refs'], *finding['qualification']['assumption_refs']])
    require(refs <= known, 'a107_requirement_identity_or_condition_not_received')
    rows, missing, experiment_binding = [], [], None
    if args['sheet_ref'] is not None:
        from .literature_partner_storage import LiteraturePartnerRepository, literal_reference_role
        require(bool(args['components']), 'a107_requested_requirement_components_required')
        reader = LiteraturePartnerRepository(store, context.run_id)
        rows = reader.fact_cells(context, [args['sheet_ref']], components=args['components'])
        require(len(rows) == len(args['components']), 'a107_requirement_numerical_subset_not_received')
        require(all(row['partner_ref'] == args['component_ref']
            and row['subject_ref'] in claim['subject_refs'] for row in rows),
            'a107_requirement_actual_experiment_binding_mismatch')
        # One paper can contain several experiments on the same molecules.
        # Conversely, one experiment can have more than one source view. Bind
        # this particular numerical use by an explicit received observation
        # link, never by matching the paper, label or numerical values.
        observation_links = {*observation.get('subject_refs', []),
            *observation.get('source_subject_refs', []), *observation.get('dependencies', [])}
        experiments = sorted({row['experiment_ref'] for row in rows
            if row['experiment_ref'] is not None})
        invalid_experiments = sorted(reference for reference in experiments
            if reference in known and literal_reference_role(store.get(reference)) not in {None, 'experiment'})
        if invalid_experiments:
            missing.append('selected_partner_experiment_identity_is_nonexperiment_literal')
            refs.update(invalid_experiments)
        unlinked = sorted(set(experiments) - observation_links)
        unidentified = [row['component'] for row in rows if row['experiment_ref'] is None]
        if unidentified:
            missing.append('selected_partner_component_experiment_identity_unreported')
        if unlinked:
            missing.append('requirement_observation_to_selected_experiment_link_unestablished')
        experiment_binding = {'version': REQUIREMENT_EXPERIMENT_BINDING_VERSION,
            'source_observation_ref': observation['id'],
            'selected_experiment_refs': experiments,
            'linked_experiment_refs': sorted((set(experiments) & observation_links) - set(invalid_experiments)),
            'unlinked_experiment_refs': unlinked,
            'unidentified_experiment_components': unidentified,
            'basis': 'explicit_observation_link_to_original_sheet_experiment',
            'state': 'unresolved' if missing else 'matched'}
        if invalid_experiments:
            experiment_binding['invalid_experiment_refs'] = invalid_experiments
        refs.add(args['sheet_ref'])
    else:
        require(not args['components'], 'a107_requirement_sheet_required_for_components')
    from .component_assessment_dependencies import assessment_dependencies, correction_refs
    dependency = assessment_dependencies(store, args['assessment_ref'], known)
    replacements = dependency['replacement_refs']
    refs.update(correction_refs(dependency))
    retired = dependency['retired']
    result = {'state': ('retired_source_finding' if retired else
            'requirement_experiment_application_unresolved' if missing else 'source_requirement_retained'),
        'missing': missing,
        'assessment_ref': args['assessment_ref'], 'source_claim': deepcopy(claim),
        'assessment_hypothesis_ref': hypothesis['id'], 'source_observation_ref': observation['id'],
        'assessment_relation': assessment['relation'], 'applicability': assessment['applicability'],
        'qualification': deepcopy(finding['qualification']), 'replacement_refs': sorted(replacements),
        'assessment_revision_dependency': dependency,
        'experiment_binding': experiment_binding,
        'partner_components': rows,
        'target_transfer': 'not_created_by_source_requirement_interpretation',
        'interpretation': 'retained_source_requirement_and_native_diagnostics; not_automatic_necessity_or_target_transfer'}
    if args.get('component_identity_ref') is not None or args.get('subject_identity_ref') is not None:
        from .component_source_identity import use as use_identity, read as read_identity
        identities = {}
        for key, argument in (('component', 'component_identity_ref'), ('subject', 'subject_identity_ref')):
            reference = args.get(argument)
            if reference is None:
                continue
            source_role = args['component_ref'] if key == 'component' else read_identity(
                store, reference, known)['result']['source_role_ref']
            require(key != 'subject' or source_role in claim['subject_refs'],
                'a107_identity_not_bound_to_assayed_subject')
            identity, used = use_identity(store, reference, source_role, known,
                experiment_refs=[row['experiment_ref'] for row in rows if row['experiment_ref'] is not None])
            refs.update(used)
            missing.extend(identity['missing'])
            identities[key] = identity
        result['source_role_identities'] = identities
        result['required_record_refs'] = sorted({reference for identity in identities.values()
            for reference in identity['required_record_refs']})
        subject_identity = identities.get('subject')
        if subject_identity is not None and subject_identity['actual_ref'] in known:
            try:
                correspondence, used = protein_correspondence(store, subject_identity['actual_ref'],
                    args['target_ref'], known, alignment_ref=args.get('subject_alignment_ref'))
                refs.update(used)
                missing.extend(correspondence['missing'])
                result['source_subject_correspondence'] = correspondence
            except (ValueError, KeyError, TypeError) as error:
                missing.append(str(error))
        result['missing'] = list(dict.fromkeys(missing))
        if missing and not retired:
            result['state'] = 'source_requirement_identity_application_unresolved'
    return result, refs


def _with_requirement(store, args, measured, refs, known):
    """Attach a particular requirement; retain the original measurement state."""
    reference = args.get('requirement_ref')
    if reference is None:
        return measured, refs
    original = _read(store, reference, graded=True)
    require(original is not None and original.get('operation') == 'partner.requirement_evidence',
        'a107_original_qualified_requirement_required')
    refs = set(refs) | {reference}
    required = original['result']
    identity = required.get('source_role_identities', {}).get('component')
    missing, needed = list(required['missing']), []
    attached = {'requirement_ref': reference, 'source_requirement': deepcopy(required['source_claim']),
        'source_requirement_state': required['state'],
        'source_requirement_limitations': list(required['missing']),
        'experiment_binding': deepcopy(required.get('experiment_binding')),
        'condition_transfer': 'not_established_by_molecular_identity_or_sequence_detection',
        'functional_requirement': 'original_qualified_source_statement; not_automatic_physiological_necessity'}
    if identity is None:
        missing.append('source_requirement_component_sequence_identity_unestablished')
    elif identity['identity_ref'] not in known:
        missing.append('required_component_identity_result_not_received')
        needed.append(identity['identity_ref'])
    else:
        from .component_source_identity import use as use_identity
        identity, used = use_identity(store, identity['identity_ref'], identity['source_role_ref'], known,
            experiment_refs=[row['experiment_ref'] for row in required['partner_components']
                if row.get('experiment_ref') is not None])
        refs.update(used)
        missing.extend(identity['missing'])
        needed.extend(identity['required_record_refs'])
        attached['source_identity_use'] = identity
        if 'actual_query_ref' in measured:
            actual = measured['actual_query_ref']
        elif measured.get('reference_protein_ref') is not None:
            actual = measured['reference_protein_ref']
        else:
            actual = args.get('encoded_product_ref') or args.get('actual_ref')
        expected = identity['actual_ref']
        matched = (actual is not None and {actual, expected} <= known
            and store.subject_molecule(actual) == 'protein'
            and _protein(store, actual) == _protein(store, expected))
        attached.update(measured_sequence_ref=actual, required_sequence_ref=expected,
            exact_declared_required_sequence_matches_measured_sequence=matched)
        if not matched:
            missing.append('measured_sequence_not_identified_as_this_required_component')
        if actual in known:
            refs.add(actual)
    from .component_assessment_dependencies import assessment_dependencies, correction_refs
    dependency = assessment_dependencies(store, required['assessment_ref'], known,
        anchor=required.get('assessment_revision_dependency'))
    if dependency is not None:
        refs.update(correction_refs(dependency))
        attached['source_assessment_revision_dependency'] = dependency
        if dependency['retired']:
            missing.append('required_source_finding_withdrawn_or_replaced')
    attached.update(state='required_component_sequence_link_retained' if not missing else
        'required_component_application_unresolved', missing=list(dict.fromkeys(missing)))
    measured['source_requirement_use'] = attached
    measured['missing'] = list(dict.fromkeys([*measured['missing'], *missing]))
    measured['required_record_refs'] = sorted(set(measured.get('required_record_refs', [])) | set(needed))
    return measured, refs


def _expression(store, args, known):
    from .component_axis_native_hpc import read, RESULT_PROVIDER
    original = read(store, args['expression_ref'], RESULT_PROVIDER)
    require(original is not None and original['axis'] == 'A107'
        and original['operation'] == 'partner.request_expression_hpc'
        and original['scientific_profile'] in {'a107_expression_components_v1', 'a107_expression_components_v2'},
        'a107_original_native_expression_result_required')
    native = original['native_components']
    feature = native['features'][args['feature_side']]
    require(feature is not None, 'a107_selected_expression_feature_was_not_measured')
    molecule = store.subject_molecule(args['actual_ref'])
    missing = []
    refs = {args['expression_ref'], args['actual_ref'], args['component_ref']}
    encoding = None
    if molecule not in {'rna', 'dna', 'protein'} or feature['molecule'] != molecule:
        missing.append('measured_feature_molecule_identity_or_reporter_interpretation')
        link = {'state': 'unresolved', 'missing': list(missing), 'pairs': []}
        identity = 'unresolved_measured_feature_molecule'
    else:
        actual = _bounded_sequence(store, args['actual_ref'])
        expected = feature['sequence_sha256']
        identity = ('declared_measured_feature_sequence_equals_received_actual_sequence'
            if expected == hashlib.sha256(actual.encode()).hexdigest() else
            'measured_feature_sequence_unreported' if expected is None else
            'measured_sequence_hash_differs; molecular_correspondence_unresolved')
        if identity != 'declared_measured_feature_sequence_equals_received_actual_sequence':
            missing.append(identity)
        mapped_args = deepcopy(args)
        if args['encoded_product_ref'] is not None:
            require(molecule in {'rna', 'dna'}, 'a107_encoding_requires_measured_nucleotide_subject')
            product = store.get(args['encoded_product_ref'])
            require(product['record_type'] == 'product' and product['origin'] == 'tool'
                and product['molecule'] == 'protein' and product['derivation'] == 'translation'
                and product.get('mapping') is not None, 'a107_original_native_encoded_product_required')
            source_ref = product.get('mapping_source_ref')
            witnesses = {source_ref, *product['parent_refs']}
            require(None not in witnesses and witnesses <= known, 'a107_received_encoding_witnesses_required')
            require(all(store.get(parent)['record_type'] == 'feature' and
                store.get(parent)['subject_ref'] == args['actual_ref'] for parent in product['parent_refs']),
                'a107_encoded_product_not_derived_from_measured_subject')
            source = store.get(source_ref)
            grades = source_tool_grading_entries(store, source_ref)
            require(source['origin'] == 'tool' and source['provider'] in {'sequence.translate', 'genes.predict'}
                and bool(grades) and all(entry['grading'].get('failure') is None
                    and entry['grading'].get('sheet') is not None for entry in grades),
                'a107_original_encoding_grader_required')
            refs.update(witnesses)
            encoding = {'product_ref': args['encoded_product_ref'], 'mapping_source_ref': source_ref,
                'parent_refs': product['parent_refs'], 'mapping': deepcopy(product['mapping']),
                'meaning': 'native_sequence_translation; not_protein_expression_or_activity'}
            mapped_args['actual_ref'] = args['encoded_product_ref']
        if store.subject_molecule(mapped_args['actual_ref']) == 'protein':
            mapped, witnesses = _map(store, mapped_args, known)
            refs.update(witnesses)
            link = mapped['component_correspondence']
        else:
            expected = _bounded_sequence(store, args['component_ref'])
            selected = args['positions'] if args['positions'] is not None else list(range(len(actual)))
            require(selected and all(type(p) is int and 0 <= p < len(actual) for p in selected),
                'a107_selected_measured_nucleotide_positions_invalid')
            same = molecule == store.subject_molecule(args['component_ref']) and ''.join(actual[p] for p in selected) == expected
            link = {'state': 'evaluated' if same else 'unresolved',
                'route': 'exact_received_nucleotide_sequence_and_region_identity',
                'actual_subject_ref': args['actual_ref'], 'reference_subject_ref': args['component_ref'],
                'missing': [] if same else ['particular_received_nucleotide_correspondence'],
                'identity_distance': 0. if same else None, 'coverage': 1. if same else None,
                'pairs': [[p, j, actual[p], expected[j], 1.] for j, p in enumerate(selected)] if same else []}
            if same:
                resolved = set('ACGU' if molecule == 'rna' else 'ACGT')
                unknown = [{'position': position, 'symbol': actual[position]} for position in selected
                    if actual[position] not in resolved]
                link['unresolved_actual_symbols'] = unknown
                link['identity_distance_basis'] = 'literal_received_nucleotide_symbols; not_biological_identity_or_function'
                if unknown:
                    link['missing'].append('resolved_nucleotide_identity_in_requested_scope')
        missing.extend(link['missing'])
    correspondence_missing = list(dict.fromkeys(missing))
    criterion_fields = _expression_fields(native, args)
    return {'state': 'expression_correspondence_unresolved' if correspondence_missing else 'expression_correspondence_retained',
        **criterion_fields,
        'missing': list(dict.fromkeys([*correspondence_missing, *criterion_fields['expression_criterion_missing']])),
        'correspondence_missing': correspondence_missing, 'expression_ref': args['expression_ref'],
        'required_record_refs': list(link.get('required_record_refs', [])),
        'feature_side': args['feature_side'], 'measured_feature': deepcopy(feature),
        'measured_feature_identity': identity, 'component_ref': args['component_ref'],
        'measured_actual_ref': args['actual_ref'], 'encoding_correspondence': encoding,
        'component_correspondence': link,
        'biological_scope': 'whole_measured_feature_quantity; requested_local_map_is_not_site_specific_expression',
        'interpretation': 'particular_measured_feature_correspondence; not_required_partner_function_or_activity'}, refs


def _expression_fields(native, args):
    criteria = deepcopy(native.get('detection_criteria', {}).get(args['feature_side'], []))
    unreported = [row['sample_id'] for row in native['pairs'] if
        (row[args['feature_side']]['value'] is not None or row[args['feature_side']].get('reported_bound') is not None)
        and not row[args['feature_side']].get('detection_criteria')]
    criterion_missing = []
    if args.get('require_detection_criterion', False):
        if not criteria:
            criterion_missing.append('source_qualified_expression_detection_criterion')
        if unreported:
            criterion_missing.append('assay_criterion_for_selected_measured_samples')
        if not native['pairs']:
            criterion_missing.append('matched_expression_samples_unreported')
        criterion_missing.extend('expression_criterion:'+reason for criterion in criteria for reason in criterion['missing'])
    return {'expression_criterion_missing': list(dict.fromkeys(criterion_missing)),
        'expression_criterion_state': 'unreported' if not criteria else 'unavailable' if not any(
            row['status'] == 'available' for row in criteria) else 'partial' if any(
                row['status'] != 'available' for row in criteria) or unreported else 'source_comparisons_retained',
        'expression_criteria': criteria, 'unreported_criterion_sample_ids': unreported,
        'condition_key': native['selection']['condition_key'],
        'quantity': deepcopy(native['quantity']),
        'native_components': deepcopy(native['components']),
        'sample_scope': deepcopy(native['sample_scope']), 'dependence': deepcopy(native['dependence']),
        'measurement_dataset_id': native['dataset_id']}


def _locus_protein_projection(store, args, known):
    """Derive a reference from received translation bytes, never a private handle.

    An original biological-reference ID named in a source is not a receipt.
    The admitted public locus result does contain its full verified translation,
    so a new explicit projection can publish that same sequence without reading
    the undelivered reference or rerunning the genomic calculation.
    """
    from .a103_publication import received_measurement
    original = received_measurement(store, args['locus_binding_ref'])
    require(original is not None and original['body']['schema'] == 'a103_locus_binding_v1',
        'a107_original_received_locus_measurement_required')
    body = original['body']
    require({row['target_ref'] for row in store.coverage(args['target_ref'])} == {body['target_ref']},
        'a107_locus_original_question_scope_mismatch')
    if body['selection_status'] != 'selected' or body['locus']['translation']['status'] != 'verified':
        return None, []
    sequence = body['locus']['translation']['sequence']
    original_ref = body.get('protein_reference_ref')
    if original_ref is not None and original_ref in known:
        require(_protein(store, original_ref) == sequence.strip().upper(),
            'a107_native_locus_and_received_protein_sequence_conflict')
        return original_ref, []
    require(len(sequence) <= MAX_MAP_POSITIONS, 'a107_public_translation_exceeds_coordinator_projection_capacity')
    reference = store.put('reference', {'reference_type': 'protein', 'source_ref': args['locus_binding_ref'],
        'accession': body['accession']+'.CDS.'+str(body['locus']['source_feature_index']),
        'label': 'Protein sequence from received verified locus translation; function unestablished',
        'sequence_ref': store.artifact(sequence, 'text/plain'), 'molecule': 'protein',
        'length': len(sequence), 'term_refs': [], 'context_refs': []}, origin='tool')['id']
    return reference, [] if reference in known else [reference]


def _expression_locus(store, args, known, *, projected_protein_ref=None):
    from .component_axis_native_hpc import read, RESULT_PROVIDER
    from .a103_publication import received_measurement
    original = read(store, args['expression_ref'], RESULT_PROVIDER)
    require(original is not None and original['axis'] == 'A107' and original['operation'] == (
        'partner.request_expression_hpc') and original['scientific_profile'] in {
            'a107_expression_components_v1', 'a107_expression_components_v2'},
        'a107_original_native_expression_result_required')
    native = original['native_components']
    feature = native['features'][args['feature_side']]
    require(feature is not None and feature['molecule'] == 'rna', 'a107_measured_gene_level_rna_feature_required')
    binding = received_measurement(store, args['locus_binding_ref'])
    require(binding is not None and binding['body']['schema'] == 'a103_locus_binding_v1',
        'a107_original_received_locus_measurement_required')
    body = binding['body']
    require(body['selection_status'] == 'selected', 'a107_unambiguous_native_locus_required')
    roots = {row['target_ref'] for row in store.coverage(args['target_ref'])}
    require(roots == {body['target_ref']}, 'a107_locus_original_question_scope_mismatch')
    refs = {args['expression_ref'], args['locus_binding_ref'], args['component_ref']}
    missing, required = [], []
    locus = body['locus']
    matched = feature['entity_id'] is not None and feature['entity_id'] in locus['locus_tags']
    if not matched:
        missing.append('particular_expression_feature_to_genomic_locus_identity')
    samples = [{**deepcopy(row['sample']), 'genome_reference_matches':
        row['sample'].get('genome_accession') == body['accession']} for row in native['pairs']]
    if not samples:
        missing.append('matched_expression_samples_unreported')
    if any(row.get('genome_accession') is None for row in samples):
        missing.append('sample_reference_genome_accession_unreported')
    if any(row.get('genome_accession') is not None and not row['genome_reference_matches'] for row in samples):
        missing.append('sample_and_locus_reference_genomes_differ; correspondence_required')
    if feature['sequence_sha256'] is not None:
        missing.append('reported_transcript_sequence_hash_not_verified_by_locus_tag_mapping')
    protein = projected_protein_ref or body.get('protein_reference_ref')
    if protein is None or locus['translation']['status'] != 'verified':
        link = {'state': 'unresolved', 'missing': ['verified_reference_locus_translation'], 'pairs': []}
    elif protein not in known:
        required.append(protein)
        link = {'state': 'unresolved', 'missing': ['actually_received_native_locus_protein_reference'], 'pairs': []}
    else:
        mapped, witnesses = _map(store, {**args, 'actual_ref': protein}, known)
        refs.update(witnesses)
        link = mapped['component_correspondence']
    missing.extend(link['missing'])
    required.extend(link.get('required_record_refs', []))
    fields = _expression_fields(native, args)
    missing.extend(fields['expression_criterion_missing'])
    return {**fields, 'state': 'gene_expression_application_partial' if missing else 'gene_expression_application_retained',
        'missing': list(dict.fromkeys(missing)), 'required_record_refs': required,
        'expression_ref': args['expression_ref'], 'feature_side': args['feature_side'],
        'measured_feature': deepcopy(feature), 'locus_binding_ref': args['locus_binding_ref'],
        'locus_identifier_matches': matched, 'locus': deepcopy(locus),
        'genomic_provenance': {key: deepcopy(body.get(key)) for key in ('accession', 'organism',
            'source_annotations', 'source_file_sha256', 'file_source_ref', 'supplied_target_genome', 'native_input_placement')},
        'declared_sample_genome_correspondence': samples, 'reference_protein_ref': protein,
        'original_locus_protein_reference_handle': body.get('protein_reference_ref'),
        'projection_meaning': 'received_public_translation_projected_explicitly; no_implicit_original_reference_receipt',
        'component_ref': args['component_ref'], 'component_correspondence': link,
        'biological_scope': 'RNA_abundance_assigned_to_declared_reference_locus; not_isoform_or_protein_specific_abundance',
        'interpretation': 'declared_locus_and_reference_genome_assignment; assay_genotype_and_required_partner_function_remain_separate'}, refs


def _bounded_sequence(store, reference):
    return received_sequence(store, reference)


def _genomic_context(store, args, proof, known):
    from .a103_publication import received_measurement
    roots = {row['target_ref'] for row in store.coverage(args['target_ref'])}
    frames = {(row['accession'], row['source_file_sha256']) for row in proof['record_scopes']}
    provided, placements, references, missing = set(), [], set(), []
    for reference in proof.get('binding_refs', []):
        if reference not in known:
            missing.append(reference)
            continue
        native = received_measurement(store, reference)
        require(native is not None and native['body']['schema'] == 'a103_locus_binding_v1',
            'a107_actual_genomic_locus_binding_required')
        binding = native['body']
        frame = binding['accession'], binding['source_file_sha256']
        if binding['target_ref'] not in roots or frame not in frames:
            continue
        references.add(reference)
        if binding.get('supplied_target_genome'):
            provided.add(frame)
        placement = binding.get('native_input_placement')
        if (binding['selection_status'] == 'selected' and placement and placement['state'] == 'unique'
                and placement['placements'][0]['feature_index'] == binding['locus']['source_feature_index']):
            placements.append({'binding_ref': reference, 'frame': {'accession': frame[0],
                'source_file_sha256': frame[1]}, 'material_ref': binding.get('material_ref'),
                'target_regions': deepcopy(binding.get('target_regions')),
                'native_placement': deepcopy(placement)})
    declared = bool(frames) and provided == frames and bool(placements)
    return {'state': ('caller_associated_genomic_collection_with_exact_target_placement' if declared else
        'sequence_matched_reference_context' if placements else 'unresolved_target_genomic_context'),
        'all_examined_records_caller_associated': bool(frames) and provided == frames,
        'target_placements': placements, 'missing_binding_refs': sorted(missing),
        'biological_scope': 'original_declared_record_collection; not_automatic_single_organism_or_complete_genome',
        'origin_inference': 'exact_sequence_in_a_reference_does_not_establish_submitted_sample_origin'}, references


def _detection(store, args, known):
    from .a103_publication import received_measurement
    original = received_measurement(store, args['detection_ref'])
    reference_native = None
    custody = {'kind': 'original_A103_detection_publication', 'source_ref': args['detection_ref']}
    if original is not None:
        require(original['body']['schema'] == 'a103_detection_v1',
            'a107_actual_received_detection_inventory_required')
        proof = original['body']
    else:
        from .component_axis_native_hpc import read, RESULT_PROVIDER
        from .a107_genomic_detection_native import PROFILE
        native = read(store, args['detection_ref'], RESULT_PROVIDER)
        require(native is not None and native['axis'] == 'A107'
            and native['operation'] == 'partner.request_detection_hpc'
            and native['scientific_profile'] == PROFILE,
            'a107_actual_received_detection_inventory_required')
        proof = native['native_components']['detection']
        reference_native = native['native_components']
        require(proof['schema'] == 'a103_detection_v1', 'a107_original_detector_result_required')
        custody = {'kind': 'authenticated_HPC_search_and_original_A103_detector',
            'source_ref': args['detection_ref'], 'hpc_result_ref': native['hpc_result_ref'],
            'pbs_job_id': native['pbs_job_id'], 'profile': PROFILE,
            'legacy_snapshot_registration': 'not_claimed'}
    refs = {args['detection_ref'], proof['component_ref'], args['component_ref']}
    require(refs <= known, 'a107_actual_detection_query_not_received')
    query, expected = (_protein(store, ref) for ref in (proof['component_ref'], args['component_ref']))
    require(query == expected, 'a107_detection_requires_exact_query_identity; homology_does_not_substitute_required_component')
    sequence_sha = hashlib.sha256(expected.encode()).hexdigest()
    included = [row for row in proof['native_hits'] if row['native_included']]
    exact = [row for row in proof['native_hits'] if row['sequence_sha256'] == sequence_sha]
    unresolved_symbols = [{'position': position, 'symbol': symbol} for position, symbol in enumerate(expected)
        if symbol not in RESOLVED_AMINO_ACIDS]
    from .a107_genomic_detection_native import reference_translation_evidence
    reference_translation = (reference_translation_evidence(reference_native, sequence_sha, unresolved_symbols)
        if reference_native is not None else None)
    genomic, bindings = _genomic_context(store, args, proof, known)
    refs.update(bindings)
    complete = proof['native_search_complete'] is True
    negative = proof['present'] is False and proof['all_actual_cds_in_search'] is True and complete
    state = ('exact_reported_sequence_detected_with_unresolved_symbols' if exact and complete and unresolved_symbols else
        'exact_component_sequence_detected' if exact and complete else
        'homologous_sequence_detected' if included and complete else
        'no_included_hit_in_examined_cds' if negative else 'unresolved_detection')
    missing = ['complete_scoped_detection'] if state == 'unresolved_detection' else []
    if unresolved_symbols:
        missing.append('specific_component_amino_acid_identity_unresolved')
    if genomic['state'] != 'caller_associated_genomic_collection_with_exact_target_placement':
        missing.append('submitted_target_genomic_or_sample_origin_not_established_by_reference_correspondence'
            if reference_translation is not None and reference_translation['biological_residue_identity_complete']
            else 'target_genomic_collection_provenance_or_exact_target_placement')
    result = {'state': state, 'missing': missing,
        'native_search_custody': custody,
        'component_ref': args['component_ref'], 'actual_query_ref': proof['component_ref'],
        'query_identity_distance': 0., 'genome_key': proof['genome_key'],
        'native_detection_present': proof['present'] if complete else None,
        'exact_sequence_hit_native_inclusion': [row['native_included'] for row in exact],
        'identity_and_inclusion_meaning': 'literal_sequence_identity_and_native_statistical_inclusion_are_distinct_uses_of_the_same_hit',
        'exact_reported_sequence_string_detected': bool(exact) if complete else None,
        'exact_component_sequence_present': True if exact and complete and not unresolved_symbols else None,
        'unresolved_query_symbols': unresolved_symbols,
        'target_genomic_context': genomic,
        'functional_partner_presence': None,
        'absence_meaning': proof['absence_meaning'], 'scope': proof['scope'],
        'record_scopes': deepcopy(proof['record_scopes']), 'searched_cds': proof['searched_cds'],
        'uncertain_cds': deepcopy(proof['uncertain_cds']),
        'all_actual_cds_in_search': proof['all_actual_cds_in_search'],
        'native_method': proof['native_method'], 'native_parameters': deepcopy(proof['native_parameters']),
        'native_program_version': proof['native_program_version'],
        'native_database_sha256': proof['native_database_sha256'], 'native_hits': deepcopy(proof['native_hits']),
        'functional_requirement': 'requires_its_source_requirement_and_actual_biological_scope',
        'interpretation': 'sequence_detection_at_original_record_scope; not_whole_genome_or_functional_absence'}
    if reference_translation is not None:
        result['reference_encoded_correspondence'] = reference_translation
    return result, refs


def received_qualifications(store, references, scope, *, full=False, known_record_refs=None):
    rows = []
    known = set(references if known_record_refs is None else known_record_refs)
    for reference in sorted(set(references)):
        body = _read(store, reference, graded=True)
        if body is None or not store.scope_contains(plain(scope), body['scope']):
            continue
        result = {'source_ref': reference, **deepcopy(body)}
        if not full:
            artifact = store.get(reference)['artifact_ref']
            link = result['result'].get('component_correspondence')
            if link is not None and 'pairs' in link:
                pairs = link.pop('pairs')
                link['native_pair_map'] = {'source_ref': reference, 'artifact_ref': artifact,
                    'json_pointer': '/result/component_correspondence/pairs', 'pair_count': len(pairs)}
                for field in ('unresolved_actual_symbols', 'unresolved_reference_symbols'):
                    if field in link:
                        symbols = link.pop(field)
                        link[field+'_retained'] = {'source_ref': reference, 'artifact_ref': artifact,
                            'json_pointer': '/result/component_correspondence/'+field,
                            'count': len(symbols), 'preview': symbols[:8]}
            if 'native_hits' in result['result']:
                hits = result['result'].pop('native_hits')
                result['result']['native_hits_preview'] = hits[:8]
                result['result']['native_hits_location'] = {'source_ref': reference,
                    'artifact_ref': artifact, 'json_pointer': '/result/native_hits', 'hit_count': len(hits)}
            if 'expression_criteria' in result['result']:
                criteria = result['result'].pop('expression_criteria')
                result['result']['expression_criteria_retained'] = {'source_ref': reference,
                    'artifact_ref': artifact, 'json_pointer': '/result/expression_criteria',
                    'criterion_count': len(criteria), 'preview': criteria[:4]}
            if 'unresolved_query_symbols' in result['result']:
                symbols = result['result'].pop('unresolved_query_symbols')
                result['result']['unresolved_query_symbols_retained'] = {'source_ref': reference,
                    'artifact_ref': artifact, 'json_pointer': '/result/unresolved_query_symbols',
                    'count': len(symbols), 'preview': symbols[:8]}
            locus = result['result'].get('locus')
            if locus is not None and locus.get('translation', {}).get('sequence') is not None:
                translation = locus['translation']
                sequence = translation.pop('sequence')
                translation['sequence_retained'] = {'source_ref': reference,
                    'artifact_ref': artifact, 'json_pointer': '/result/locus/translation/sequence',
                    'length': len(sequence), 'sha256': hashlib.sha256(sequence.encode()).hexdigest()}
            if 'declared_sample_genome_correspondence' in result['result']:
                samples = result['result'].pop('declared_sample_genome_correspondence')
                result['result']['declared_sample_genome_correspondence_retained'] = {
                    'source_ref': reference, 'artifact_ref': artifact,
                    'json_pointer': '/result/declared_sample_genome_correspondence',
                    'sample_count': len(samples),
                    'matching_reference_genome_count': sum(row['genome_reference_matches'] for row in samples),
                    'unknown_reference_genome_count': sum(row.get('genome_accession') is None for row in samples),
                    'different_reference_genome_count': sum(row.get('genome_accession') is not None
                        and not row['genome_reference_matches'] for row in samples),
                    'preview': samples[:4]}
        rows.append(result)
    for row in rows:
        changed = [reference for reference, signature in row.get('operand_signatures', {}).items()
            if reference in known and digest(store.get(reference)) != signature]
        from .component_assessment_dependencies import qualification_assessment_changes
        revisions = qualification_assessment_changes(store, row, known)
        from .component_source_identity import qualification_changes
        identity_revisions = qualification_changes(store, row, known)
        binding = row['result'].get('experiment_binding') or {}
        legacy_experiment = (row.get('operation') == 'partner.requirement_evidence'
            and bool(row['result'].get('partner_components'))
            and binding.get('version') != REQUIREMENT_EXPERIMENT_BINDING_VERSION)
        row['current'] = not changed and not revisions and not identity_revisions and not legacy_experiment and not any(other['request_ref'] == row['request_ref'] and
            set(row['qualification_dependencies']) < set(other['qualification_dependencies']) for other in rows)
        row['changed_received_operand_refs'] = sorted(changed)
        if legacy_experiment:
            row['qualification_update_reasons'] = ['requirement_experiment_binding_not_recorded']
        if revisions:
            row['source_assessment_change_refs'] = revisions
        if identity_revisions:
            row['source_identity_change_refs'] = identity_revisions
    return rows


def refresh(store, context, known):
    """Hard-coded publication/receipt routing; no action chosen by a model."""
    install(store)
    known = set(known)
    generated, needs = [], []
    requests = [(ref, body) for ref in sorted(known) if (body := _read(store, ref)) is not None]
    admitted = received_qualifications(store, known, context.scope)
    for reference, original in requests:
        if original['run_id'] != context.run_id or not store.scope_contains(plain(context.scope), original['scope']):
            continue
        args = original['arguments']
        old = [row for row in admitted if row['request_ref'] == reference]
        operands = set(original['operand_refs'])
        if not operands <= known or old and not any(set(row['qualification_dependencies']) <= known for row in old):
            continue  # Keep a narrow admitted result; never downgrade private missing operands.
        operation = original['operation']
        try:
            from .component_source_identity import TOOLS as IDENTITY_TOOLS, calculate as source_identity
            if operation == IDENTITY_TOOLS['A107']:
                measured, refs = source_identity(store, args, context, known)
            elif operation == 'partner.component_correspondence':
                measured, refs = _map(store, args, known)
            elif operation == 'partner.requirement_evidence':
                measured, refs = _requirement(store, args, known, context)
            elif operation == 'partner.detection_evidence':
                measured, refs = _detection(store, args, known)
            elif operation == 'partner.expression_evidence':
                measured, refs = _expression(store, args, known)
            elif operation == 'partner.expression_locus_evidence':
                protein, projections = _locus_protein_projection(store, args, known)
                known.update(projections)
                generated.extend(projections)
                measured, refs = _expression_locus(store, args, known, projected_protein_ref=protein)
            else:
                raise ContractError('a107_unbound_qualification_operation')
            if operation in {'partner.detection_evidence', 'partner.expression_evidence',
                    'partner.expression_locus_evidence'}:
                measured, refs = _with_requirement(store, args, measured, refs, known)
        except (ValueError, KeyError, TypeError) as error:
            if operation == 'partner.requirement_evidence' and str(error) == (
                    'a107_requirement_numerical_subset_not_received') and any(
                        row['result'].get('partner_components') for row in old):
                # A received qualification already carries this exact numerical
                # subset. Do not ask for an undelivered private worksheet merely
                # to reproduce an unchanged, authenticated received result.
                continue
            # A later valid delivery must not be rolled back because another
            # requested use still lacks an operand or has conflicting identity.
            measured, refs = {'state': 'qualification_unavailable', 'missing': [str(error)],
                'interpretation': 'original_evidence_retained; no_qualified_scientific_value'}, operands
        require(refs <= known, 'a107_qualification_native_dependencies_not_received')
        body = {'version': VERSION, 'operation': operation, 'request_ref': reference,
            'scope': original['scope'], 'target_ref': original['target_ref'],
            'target_regions': original['target_regions'], 'result': measured,
            'qualification_dependencies': sorted(refs | operands), 'controller_credit': None,
            'operand_signatures': {ref: digest(store.get(ref)) for ref in sorted(refs | operands)},
            'meaning': 'per_use_scientific_components; not_annotation_probability_or_new_axis_scalar'}
        with store.transaction():
            generated.append(_publish(store, PROVIDER, body, graded=True))
        if measured['missing']:
            needs.append((reference, {'target_ref': original['target_ref'], 'policy': operation,
                'missing': measured['missing'], 'required_operands': {'source_refs': sorted(operands),
                    'actual_ref': args.get('actual_ref'), 'component_ref': args.get('component_ref'),
                    'positions': args.get('positions'), 'record_refs': measured.get('required_record_refs', [])}}))
    return list(dict.fromkeys(generated)), needs


def fact_sources():
    schema = {'type': 'array', 'items': {'type': 'string', 'format': 'reference'},
        'uniqueItems': True, 'x-source': FACT_SOURCE}
    execution = {**deepcopy(schema), 'x-source': EXECUTION_SOURCE}
    return {FACT_SOURCE: {'type': 'array', 'meaning': 'Actual received host-issued A107 per-use qualification records; no implicit upstream receipt.',
        'report_schema': schema},
        EXECUTION_SOURCE: {'type': 'array', 'meaning': 'Actual received original genomic HPC admission, pending-attribution and failure records. Operational status is not scientific credit.',
            'report_schema': execution}}


def execution_findings(store, context, known):
    from .a103_hpc import execution_findings as original_execution_findings
    return original_execution_findings(store, context, known)


def partner_requirement_scalar(cells):
    """Keep the weaker of the actual omission and addback response indices.

    The root uses signed softsign of the existing dimensionless diagnostics.
    It does not turn genomic non-detection into absence, infer a partner's
    biological presence, or establish target/condition correspondence.
    """
    from .root_axis_scalars import _number, prerequisite_scalar
    selected = {}
    for cell in cells:
        component = cell['component']
        if component in selected:
            raise ValueError('root_scalar_duplicate_partner_component')
        selected[component] = cell
    required = ('partner_loss_fraction', 'restored_reference_fraction')
    values, missing = {}, []
    for name in required:
        cell = selected.get(name)
        if cell is None or cell.get('value') is None or cell.get('status') != 'populated':
            missing.append(name)
            continue
        if cell.get('unit') != 'dimensionless':
            raise ValueError('root_scalar_dimensionless_partner_contrast_required')
        value = _number(cell['value'])
        values[name] = value / (1 + abs(value))
    return prerequisite_scalar('A107', values, required=required, missing=missing,
        inputs=cells, formula='min(softsign(partner_loss_fraction),softsign(restored_reference_fraction))')


def annotation_contribution(store, context, *, target, annotation, scope,
                            comparison_ref=None, selection=None, details_limit=0, details_offset=0):
    """This owner's qualified contribution and molecular-application status."""
    from .component_assessment_dependencies import qualification_annotation
    from .root_axis_scalars import _result, require_attribution, bind_contribution
    known = set(context.received_record_refs)
    rows = received_qualifications(store, known, plain(context.scope), known_record_refs=known)
    rows = [row for row in rows if row['operation'] == 'partner.requirement_evidence'
        and qualification_annotation(store, context, row['result']) == annotation['id']
        and (selection is None or row['source_ref'] == selection)]
    candidates = []
    for row in rows:
        result = row['result']
        correspondence = result.get('source_subject_correspondence') or {}
        subject = (correspondence.get('reference_subject_ref')
            or (result.get('source_function_finding') or {}).get('target_subject_ref') or row['target_ref'])
        if subject == target and row.get('current') is True:
            candidates.append(row)
    refs, details = [], []
    if len(candidates) != 1:
        reason = 'no_unique_received_current_qualified_use_for_this_question'
        scalar = _result('A107', None, formula='received_current_axis_result_required',
            inputs={'qualification_refs': [row['source_ref'] for row in candidates]}, reasons=[reason])
        status = 'unresolved'
        for row in rows:
            result = row['result']
            reference = result.get('assessment_ref') or (result.get('source_function_finding') or {}).get('assessment_ref')
            if reference in known and (store.get(reference).get('investigation_finding') or {}).get('status') == 'withdrawn':
                status = 'withdrawn'
        transfer = {'status': status, 'missing_inputs': [reason], 'needed_refs': [],
            'link_refs': [row['source_ref'] for row in rows]}
    else:
        row = candidates[0]
        result = row['result']
        refs = [row['source_ref']]
        missing = list(result['missing'])
        scalar = partner_requirement_scalar(result['partner_components'])
        if not result.get('source_subject_correspondence'):
            missing.append('source_requirement_subject_to_target_correspondence_unresolved')
        regions = row.get('target_regions')
        if regions:
            if isinstance(regions[0], (list, tuple)):
                regions = [{'target_ref': row['target_ref'], 'start': start, 'end': end,
                    'unit': store.subject_unit(row['target_ref'])} for start, end in regions]
            result_scope = {'subject_refs': sorted({part['target_ref'] for part in regions}), 'segments': regions}
        else:
            result_scope = row['scope']
        if not store.scope_contains(result_scope, plain(scope)):
            missing.append('received_axis_result_does_not_cover_requested_scope')
        scalar = require_attribution(scalar, missing=missing)
        applicability = result.get('assessment_applicability') or (result.get('source_function_finding') or {}).get('applicability')
        transfer = {'status': 'invalid' if applicability == 'incomparable' else 'unresolved' if missing else 'established',
            'missing_inputs': missing, 'needed_refs': sorted(set(result.get('required_record_refs', ())) - known),
            'link_refs': [row['source_ref']]}
        details = [{'source_ref': row['source_ref'], 'target_ref': target, 'proposed_annotation_ref': annotation['id'],
            'scope': plain(scope), 'transfer': transfer, 'qualification': result}]
    scalar.update(question={'assertion_ref': annotation['id']}, source_contribution_count=len(refs))
    return bind_contribution(scalar, annotation=annotation, subject=target, scope=scope,
        transfer=transfer, source_refs=refs), details[details_offset:details_offset + details_limit]

