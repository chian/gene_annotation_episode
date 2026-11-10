"""Per-reaction chemical evidence use and particular molecular correspondence.

Reaction accounting stands on its own. A molecular-function interpretation is
separate and retains its actual claim, assayed subject, map and qualifications.
"""
from copy import deepcopy
import hashlib
import json

from .communication import plain
from .domain import canonical, obj, validate_schema
from .tool_grading_artifacts import retain_tool_grading, source_tool_grading_entries
from .component_sequence_attribution import protein_correspondence
from .component_axis_native_hpc import read as native_read, RESULT_PROVIDER, require


VERSION = 'a110_received_qualification_v1'
REQUEST_PROVIDER = 'host.a110.qualification_request'
PROVIDER = 'host.a110.qualification'
FACT_SOURCE = 'a110_qualification_records'
TOOL = 'chemistry.reaction_evidence'


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def catalog():
    ref = {'type': 'string', 'format': 'reference'}
    nullable = {'anyOf': [ref, {'type': 'null'}]}
    native = {TOOL: {'description': 'Qualify one received native chemical reaction result against its '
        'actual biological reaction reference. Optionally attach a retained source function finding '
        'and its particular received actual-to-target protein/region correspondence. Protein '
        'features retain local coordinates and require actually received parent frames for native reuse. Chemical '
        'accounting is independently useful; a sequence map is not catalysis or activity proof.',
        'resources': 'local', 'input_schema': obj({'target_ref': ref, 'accounting_ref': ref,
            'reaction_id': {'type': 'string', 'minLength': 1}, 'reaction_ref': ref,
            'assessment_ref': nullable, 'actual_ref': nullable, 'target_subject_ref': nullable,
            'positions': {'type': ['array', 'null'], 'minItems': 1, 'uniqueItems': True,
                'items': {'type': 'integer', 'minimum': 0}}, 'alignment_ref': nullable})}}
    from .a110_experimental_qualification import catalog as experimental_catalog
    from .component_source_identity import catalog as identity_catalog
    native[TOOL]['input_schema']['properties']['source_identity_ref'] = nullable
    native[TOOL]['description'] += (
        ' Optional source_identity_ref binds an original unsequenced source '
        'subject to its declared protein reference. It does not relabel the '
        'original finding or turn an identifier into a measured construct sequence.')
    return {**native, **experimental_catalog(), **identity_catalog('A110')}


def publish(store, provider, body):
    for table in ('a110_qualification_requests', 'a110_qualifications'):
        store.db.execute('CREATE TABLE IF NOT EXISTS '+table+' (source_ref TEXT PRIMARY KEY,body TEXT NOT NULL)')
    artifact = store.artifact(canonical(body), 'application/json')
    grading = retain_tool_grading(store, provider=provider, native_artifact_ref=artifact,
        grading={'grader': VERSION, 'failure': None, 'sheet': body}) if provider == PROVIDER else None
    reference = store.put('source', {'provider': provider, 'accession': digest(body), 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': VERSION,
        'retrieved_at': None, 'operand_refs': body['scope']['subject_refs'],
        **({'auxiliary_artifact_refs': [grading]} if grading is not None else {})}, origin='tool')['id']
    table = 'a110_qualifications' if provider == PROVIDER else 'a110_qualification_requests'
    store.db.execute('INSERT OR IGNORE INTO '+table+' VALUES(?,?)', (reference, canonical(body)))
    return reference


def read(store, reference, *, qualified=False):
    record = store.get(reference)
    provider = PROVIDER if qualified else REQUEST_PROVIDER
    if record.get('provider') != provider:
        return None
    table = 'a110_qualifications' if qualified else 'a110_qualification_requests'
    exists = store.db.execute('SELECT 1 FROM sqlite_master WHERE name=?', (table,)).fetchone()
    saved = store.db.execute('SELECT body FROM '+table+' WHERE source_ref=?', (reference,)).fetchone() if exists else None
    require(saved is not None and record['origin'] == 'tool' and record['version'] == VERSION,
        'a110_original_qualification_grant_required')
    body = json.loads(saved[0])
    require(json.loads(store.get_artifact(record['artifact_ref'])) == body, 'a110_qualification_custody_conflict')
    if qualified:
        entries = source_tool_grading_entries(store, reference)
        require(len(entries) == 1 and entries[0]['grading'] == {'grader': VERSION, 'failure': None, 'sheet': body},
            'a110_qualification_grader_conflict')
    return body


def request(store, args, *, context, known):
    validate_schema(args, catalog()[TOOL]['input_schema'])
    refs = {args[key] for key in ('target_ref', 'accounting_ref', 'reaction_ref', 'assessment_ref',
        'actual_ref', 'target_subject_ref', 'alignment_ref') if args[key] is not None}
    if args.get('source_identity_ref') is not None:
        refs.add(args['source_identity_ref'])
    require(refs <= known and set(store.reference_subset(refs, plain(context.scope))) == refs,
        'a110_original_received_operands_required')
    coverage = store.coverage(args['target_ref'])
    require(coverage and store.scope_covers(coverage, plain(context.scope)), 'a110_original_target_scope_required')
    roots = {row['target_ref'] for row in coverage}
    require(len(roots) == 1, 'a110_single_original_target_required')
    return publish(store, REQUEST_PROVIDER, {'version': VERSION, 'run_id': context.run_id,
        'scope': plain(context.scope), 'target_ref': next(iter(roots)), 'target_regions': coverage,
        'arguments': deepcopy(args), 'operand_refs': sorted(refs), 'scientific_credit': None})


def source_identity_request(store, args, *, context, known):
    from .component_source_identity import TOOLS
    validate_schema(args, catalog()[TOOLS['A110']]['input_schema'])
    refs = {value for key, value in args.items() if key.endswith('_ref') and value is not None}
    require(refs <= known and set(store.reference_subset(refs, plain(context.scope))) == refs,
        'a110_source_identity_operands_not_received')
    coverage = store.coverage(args['target_ref'])
    roots = {row['target_ref'] for row in coverage}
    require(coverage and len(roots) == 1 and store.scope_covers(coverage, plain(context.scope)),
        'a110_source_identity_target_scope_required')
    return publish(store, REQUEST_PROVIDER, {'version': VERSION, 'run_id': context.run_id,
        'operation': TOOLS['A110'], 'scope': plain(context.scope),
        'target_ref': next(iter(roots)), 'target_regions': coverage,
        'arguments': deepcopy(args), 'operand_refs': sorted(refs), 'scientific_credit': None})


def calculate(store, original, known):
    args = original['arguments']
    refs = set(original['operand_refs'])
    native = native_read(store, args['accounting_ref'], RESULT_PROVIDER)
    require(native is not None and native['axis'] == 'A110' and native['scientific_profile'] in {
        'a110_chemical_accounting_v1', 'a110_chemical_accounting_v2'}, 'a110_original_chemical_accounting_required')
    selected = [row for row in native['native_components']['reactions'] if row['reaction_id'] == args['reaction_id']]
    require(len(selected) == 1, 'a110_particular_returned_reaction_required')
    reaction = selected[0]
    reference = store.get(args['reaction_ref'])
    require(reference['record_type'] == 'term' and reference['term_type'] == 'reaction' or
        reference['record_type'] == 'reference' and reference['reference_type'] == 'reaction',
        'a110_biological_reaction_reference_required')
    missing, required = [], set()
    identity = reaction['entity_id'] is not None and reaction['entity_id'] == reference.get('accession')
    if not identity:
        missing.append('particular_source_reaction_to_biological_reference_identity')
    source_finding, correspondence = None, None
    if args['assessment_ref'] is None:
        require(all(args[key] is None for key in ('actual_ref', 'target_subject_ref', 'positions', 'alignment_ref')),
            'a110_source_finding_required_for_molecular_application')
        missing.append('source_supported_molecular_reaction_application')
    else:
        require(args['actual_ref'] is not None and args['target_subject_ref'] is not None,
            'a110_actual_and_target_molecule_required')
        assessment = store.get(args['assessment_ref'])
        require(assessment['record_type'] == 'assessment', 'a110_actual_source_assessment_required')
        refs.update([assessment['hypothesis_ref'], assessment['observation_ref']])
        require(refs <= known, 'a110_received_source_assessment_witnesses_required')
        finding = assessment.get('investigation_finding')
        require(finding is not None, 'a110_retained_source_function_finding_required')
        claim = finding['source_claim']
        source_identity = None
        actual_source = args['actual_ref']
        if args.get('source_identity_ref') is not None:
            from .component_source_identity import read as identity_read, use as identity_use
            actual_source = identity_read(store, args['source_identity_ref'], known)['result']['source_role_ref']
            source_identity, used = identity_use(store, args['source_identity_ref'], actual_source, known)
            refs.update(used)
            missing.extend(source_identity['missing'])
            required.update(source_identity['required_record_refs'])
            declared = source_identity['actual_ref']
            if declared not in known:
                missing.append('source_identity_actual_protein_not_received')
            else:
                from .component_sequence_attribution import protein_sequence
                if protein_sequence(store, declared) != protein_sequence(store, args['actual_ref']):
                    missing.append('actual_molecule_not_source_identified_sequence')
        require(claim['predicate'] in {'catalyzes', 'transports', 'participates_in'} and
            actual_source in claim['subject_refs'] and claim['value']['type'] == 'reference'
            and claim['value']['ref'] == args['reaction_ref'], 'a110_particular_source_function_claim_required')
        observation = store.get(assessment['observation_ref'])
        if source_identity is not None and source_identity['experiment_ref'] is not None:
            experiment_links = {*observation['subject_refs'], *observation['source_subject_refs'],
                *observation.get('dependencies', [])}
            if source_identity['experiment_ref'] not in experiment_links:
                missing.append('source_identity_to_function_finding_experiment_link_unestablished')
        refs.update([observation['source_ref'], *claim['subject_refs'], *claim['context_refs'],
            *assessment['condition_refs'], *assessment['assumption_refs'],
            *finding['qualification']['context_refs'], *finding['qualification']['assumption_refs']])
        require(refs <= known, 'a110_source_context_or_identity_witness_not_received')
        from .component_assessment_dependencies import assessment_dependencies, correction_refs
        dependency = assessment_dependencies(store, args['assessment_ref'], known)
        replacements = dependency['replacement_refs']
        refs.update(correction_refs(dependency))
        if dependency['retired']:
            missing.append('source_function_finding_withdrawn_or_replaced')
        if dependency['superseding_assessment_refs']:
            missing.append('source_function_assessment_superseded_by_received_revision')
        target_scope = store.coverage(args['target_subject_ref'])
        require(target_scope and {row['target_ref'] for row in target_scope} == {original['target_ref']}
            and store.scope_covers(target_scope, original['scope']), 'a110_target_molecular_mapping_outside_original_scope')
        correspondence, mapped_refs = protein_correspondence(store, args['actual_ref'], args['target_subject_ref'], known,
            positions=args['positions'], alignment_ref=args['alignment_ref'])
        refs.update(mapped_refs)
        missing.extend(correspondence['missing'])
        source_finding = {'assessment_ref': args['assessment_ref'], 'source_claim': deepcopy(claim),
            'actual_subject_ref': args['actual_ref'], 'target_subject_ref': args['target_subject_ref'],
            'relation': assessment['relation'], 'applicability': assessment['applicability'],
            'qualification': deepcopy(finding['qualification']), 'replacement_refs': sorted(replacements),
            'assessment_revision_dependency': dependency}
        if source_identity is not None:
            source_finding['source_identity_use'] = source_identity
    return {'state': 'per_use_evidence_retained' if not missing else 'per_use_application_unresolved',
        'missing': list(dict.fromkeys(missing)), 'native_entity_identifier_matches_reference_accession': identity,
        'reaction_ref': args['reaction_ref'], 'native_reaction': deepcopy(reaction),
        'required_record_refs': sorted(required | (set() if correspondence is None else
            set(correspondence.get('required_record_refs', [])))),
        'source_function_finding': source_finding, 'component_correspondence': correspondence,
        'limitation': 'Native entity labels and extracted equations remain source assertions. Chemical accounting and sequence correspondence remain separate components; neither proves activity.'}, refs


def refresh(store, context, known):
    generated, needs = [], []
    admitted = received(store, known, context.scope)
    for reference in sorted(known):
        original = read(store, reference)
        if original is None or original['run_id'] != context.run_id or not store.scope_contains(
                plain(context.scope), original['scope']) or not set(original['operand_refs']) <= known:
            continue
        old = [row for row in admitted if row['request_ref'] == reference]
        if old and not any(set(row['qualification_dependencies']) <= known for row in old):
            continue  # Preserve an admitted narrow result without reopening private upstream data.
        try:
            from .component_source_identity import TOOLS as IDENTITY_TOOLS, calculate as identity_calculate
            if original.get('operation') == IDENTITY_TOOLS['A110']:
                result, refs = identity_calculate(store, original['arguments'], context, known)
            else:
                result, refs = calculate(store, original, known)
        except (ValueError, KeyError, TypeError) as error:
            refs = set(original['operand_refs'])
            result = {'state': 'qualification_unavailable', 'missing': [str(error)]}
        require(refs <= known, 'a110_qualification_dependencies_not_received')
        body = {'version': VERSION, 'scope': original['scope'], 'target_ref': original['target_ref'],
            'target_regions': original['target_regions'], 'request_ref': reference, 'result': result,
            'qualification_dependencies': sorted(refs), 'operand_signatures': {ref: digest(store.get(ref)) for ref in sorted(refs)},
            'scientific_credit': None}
        if original.get('operation') == IDENTITY_TOOLS['A110']:
            body['operation'] = original['operation']
        generated.append(publish(store, PROVIDER, body))
        if result['missing']:
            needs.append((reference, {'target_ref': original['target_ref'], 'policy': original.get('operation', TOOL),
                'missing': result['missing'], 'required_operands': {'source_refs': sorted(original['operand_refs']),
                    'record_refs': result.get('required_record_refs', [])}}))
    from .a110_experimental_qualification import refresh as experimental_refresh
    more, pending = experimental_refresh(store, context, known | set(generated))
    return list(dict.fromkeys([*generated, *more])), [*needs, *pending]


def received(store, references, scope, *, known=None):
    known = set(references if known is None else known)
    rows = []
    for reference in sorted(set(references)):
        body = read(store, reference, qualified=True)
        if body is None:
            continue
        if not store.scope_contains(plain(scope), body['scope']):
            continue
        row = {'source_ref': reference, **deepcopy(body)}
        link = row['result'].get('component_correspondence')
        if link is not None and 'pairs' in link:
            pairs = link.pop('pairs')
            link['native_pair_map'] = {'source_ref': reference, 'artifact_ref': store.get(reference)['artifact_ref'],
                'pointer': '/result/component_correspondence/pairs', 'pair_count': len(pairs)}
            for field in ('unresolved_actual_symbols', 'unresolved_reference_symbols'):
                if field in link:
                    symbols = link.pop(field)
                    link[field+'_retained'] = {'source_ref': reference, 'artifact_ref': store.get(reference)['artifact_ref'],
                        'pointer': '/result/component_correspondence/'+field, 'count': len(symbols), 'preview': symbols[:8]}
        rows.append(row)
    from .a110_experimental_qualification import (
        received as experimental_received, EXPERIMENT_BINDING_VERSION)
    rows.extend(experimental_received(store, references, scope))
    for row in rows:
        changed = [ref for ref, value in row['operand_signatures'].items() if ref in known and digest(store.get(ref)) != value]
        from .component_assessment_dependencies import qualification_assessment_changes
        revisions = qualification_assessment_changes(store, row, known)
        from .component_source_identity import qualification_changes
        identity_revisions = qualification_changes(store, row, known)
        binding = row['result'].get('experiment_binding') or {}
        legacy_experiment = (row.get('qualification_kind') == 'experimental_component_use'
            and row['result'].get('source_function_finding') is not None
            and binding.get('version') != EXPERIMENT_BINDING_VERSION)
        row['current'] = not changed and not revisions and not identity_revisions and not legacy_experiment and not any(other['request_ref'] == row['request_ref'] and
            set(row['qualification_dependencies']) < set(other['qualification_dependencies']) for other in rows)
        row['changed_received_operand_refs'] = changed
        if legacy_experiment:
            row['qualification_update_reasons'] = ['experimental_finding_experiment_binding_not_recorded']
        if revisions:
            row['source_assessment_change_refs'] = revisions
        if identity_revisions:
            row['source_identity_change_refs'] = identity_revisions
    return rows


def fact_sources():
    schema = {'type': 'array', 'items': {'type': 'string', 'format': 'reference'},
        'uniqueItems': True, 'x-source': FACT_SOURCE}
    return {FACT_SOURCE: {'type': 'array', 'meaning': 'Actual received host-issued A110 native-accounting or selected experimental-component use qualifications.',
        'report_schema': schema}}


def chemical_constraint_scalar(cells, *, required):
    """Reuse A110's existing signed comparisons, never raw residual/energy units."""
    from .root_axis_scalars import prerequisite_scalar
    allowed = {'reaction_comparison', 'resource_comparison'}
    if not set(required) <= allowed:
        raise ValueError('root_scalar_existing_chemical_comparison_required')
    values = {}
    selected = []
    for cell in cells:
        if cell['component'] not in required:
            continue
        if cell['component'] in {row['component'] for row in selected}:
            raise ValueError('root_scalar_duplicate_chemical_component')
        selected.append(cell)
        if cell.get('unit') != 'dimensionless':
            raise ValueError('root_scalar_dimensionless_chemical_comparison_required')
        if cell.get('status') == 'populated' and cell.get('value') is not None:
            values[cell['component']] = cell['value']
    return prerequisite_scalar('A110', values, required=required, inputs=selected)


def annotation_contribution(store, context, *, target, annotation, scope,
                            comparison_ref=None, selection=None, details_limit=0, details_offset=0):
    """This owner's qualified contribution and molecular-application status."""
    from .component_assessment_dependencies import qualification_annotation
    from .root_axis_scalars import _result, require_attribution, bind_contribution
    known = set(context.received_record_refs)
    rows = received(store, known, plain(context.scope), known=known)
    rows = [row for row in rows if row['result'].get('selected_components')
        and qualification_annotation(store, context, row['result']) == annotation['id']
        and (selection is None or row['source_ref'] == selection)]
    candidates = []
    for row in rows:
        result = row['result']
        correspondence = result.get('component_correspondence') or {}
        subject = (correspondence.get('reference_subject_ref')
            or (result.get('source_function_finding') or {}).get('target_subject_ref') or row['target_ref'])
        if subject == target and row.get('current') is True:
            candidates.append(row)
    refs, details = [], []
    if len(candidates) != 1:
        reason = 'no_unique_received_current_qualified_use_for_this_question'
        scalar = _result('A110', None, formula='received_current_axis_result_required',
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
        required = ('resource_comparison',) if result['component_family'] == 'resource' else ('reaction_comparison',)
        scalar = chemical_constraint_scalar(result['selected_components'], required=required)
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
