"""Particular uses of admitted A110 reaction/prediction/resource components.

The original literature readers own numerical values and selected-cell custody.
This adapter retains source context and molecular correspondence separately; it
does not calculate an axis scalar or turn reference measurements into target
activity, local-region measurements or physiological resource availability.
"""
from copy import deepcopy
import hashlib
import json

from .communication import plain
from .domain import canonical, obj, validate_schema
from .component_axis_native_hpc import require
from .component_sequence_attribution import protein_correspondence
from .tool_grading_artifacts import retain_tool_grading, source_tool_grading_entries


VERSION = 'a110_experimental_component_use_v1'
EXPERIMENT_BINDING_VERSION = 'a110_experimental_finding_binding_v1'
TOOL = 'chemistry.experimental_reaction_evidence'
REQUEST_PROVIDER = 'host.a110.experimental_qualification_request'
PROVIDER = 'host.a110.experimental_qualification'
TABLES = {REQUEST_PROVIDER: 'a110_experimental_qualification_requests',
          PROVIDER: 'a110_experimental_qualifications'}


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def catalog():
    from .literature_reaction_calculations import COMPONENTS
    ref = {'type': 'string', 'format': 'reference'}
    optional = {'anyOf': [ref, {'type': 'null'}]}
    entries = {TOOL: {'description': 'Retain a particular use of actually admitted experimental '
        'reaction-ratio/prediction or resource-model components. Select their original sheet '
        'and component names. Source evidence is useful before a biological reaction or '
        'protein correspondence is known; missing links produce an explicit unresolved '
        'qualification without removing numerical evidence. Select one ratio/prediction '
        'or resource-model scope per request. An optional source function finding must '
        'explicitly link the selected experiment from its observation, through subject_refs, '
        'source_subject_refs or dependencies; a shared paper is insufficient. Missing '
        'experiment identity or linkage retains the original components as unresolved. '
        'Optional source function findings and received '
        'protein/region maps do not establish target activity or change measurement scope.',
        'resources': 'local', 'input_schema': obj({'target_ref': ref, 'sheet_ref': ref,
            'components': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                'items': {'enum': list(COMPONENTS)}},
            'reaction_ref': optional, 'assessment_ref': optional, 'actual_ref': optional,
            'target_subject_ref': optional, 'source_alignment_ref': optional,
            'alignment_ref': optional,
            'positions': {'type': ['array', 'null'], 'minItems': 1, 'uniqueItems': True,
                'items': {'type': 'integer', 'minimum': 0}}})}}
    entries[TOOL]['input_schema']['properties']['source_identity_ref'] = optional
    entries[TOOL]['description'] += (
        ' Optional source_identity_ref selects an actual graded source_identity_evidence '
        'binding for the original assayed role. The literal source subject is preserved; '
        'its declared protein reference is then compared separately to the actual/target '
        'sequence. Missing or component-only identity retains unresolved application.')
    return entries


def _reader(store, run_id, sheet_ref):
    from .literature_reaction_storage import LiteratureReactionRepository, PROVIDER as SHEETS
    record = store.get(sheet_ref)
    require(record.get('provider') == SHEETS and record.get('version') in {
        'literature_reaction_record_v2', 'literature_reaction_record_v3'},
        'a110_original_experimental_reaction_sheet_required')
    reader = LiteratureReactionRepository(store, run_id)
    return reader.semantic_projection() if record['version'] == 'literature_reaction_record_v3' else reader


def publish(store, provider, body):
    for table in TABLES.values():
        store.db.execute(f'CREATE TABLE IF NOT EXISTS {table}(source_ref TEXT PRIMARY KEY,body TEXT NOT NULL)')
    artifact = store.artifact(canonical(body), 'application/json')
    grading = retain_tool_grading(store, provider=provider, native_artifact_ref=artifact,
        grading={'grader': VERSION, 'failure': None, 'sheet': body}) if provider == PROVIDER else None
    source = store.put('source', {'provider': provider, 'accession': digest(body), 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': VERSION,
        'retrieved_at': None, 'operand_refs': body['scope']['subject_refs'],
        **({'auxiliary_artifact_refs': [grading]} if grading is not None else {})}, origin='tool')['id']
    store.db.execute(f'INSERT OR IGNORE INTO {TABLES[provider]} VALUES(?,?)', (source, canonical(body)))
    return source


def read(store, reference, *, qualified=False):
    record = store.get(reference)
    provider = PROVIDER if qualified else REQUEST_PROVIDER
    if record.get('provider') != provider:
        return None
    installed = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (TABLES[provider],)).fetchone()
    saved = store.db.execute(f'SELECT body FROM {TABLES[provider]} WHERE source_ref=?',
        (reference,)).fetchone() if installed else None
    require(saved is not None and record['origin'] == 'tool' and record['version'] == VERSION,
        'a110_original_experimental_qualification_required')
    body = json.loads(saved[0])
    require(json.loads(store.get_artifact(record['artifact_ref'])) == body,
        'a110_experimental_qualification_custody_conflict')
    if qualified:
        entries = source_tool_grading_entries(store, reference)
        require(len(entries) == 1 and entries[0]['grading'] == {
            'grader': VERSION, 'failure': None, 'sheet': body},
            'a110_experimental_qualification_grader_conflict')
    return body


def request(store, args, *, context, known):
    validate_schema(args, catalog()[TOOL]['input_schema'])
    families = {'resource' if name.startswith('resource_') else 'ratio' for name in args['components']}
    require(len(families) == 1, 'a110_select_one_experimental_component_scope')
    refs = {value for key, value in args.items() if key.endswith('_ref') and value is not None}
    require(refs <= known and set(store.reference_subset(refs, plain(context.scope))) == refs,
        'a110_original_received_experimental_operands_required')
    coverage = store.coverage(args['target_ref'])
    roots = {row['target_ref'] for row in coverage}
    require(coverage and len(roots) == 1 and store.scope_covers(coverage, plain(context.scope)),
        'a110_original_experimental_question_scope_required')
    if args['target_subject_ref'] is not None:
        target = store.coverage(args['target_subject_ref'])
        require(target and {row['target_ref'] for row in target} == roots
            and store.scope_covers(target, plain(context.scope)),
            'a110_experimental_target_correspondence_outside_scope')
    require(args['positions'] is None or args['actual_ref'] is not None,
        'a110_experimental_positions_require_actual_subject')
    _reader(store, context.run_id, args['sheet_ref'])
    return publish(store, REQUEST_PROVIDER, {'version': VERSION, 'run_id': context.run_id,
        'qualification_kind': 'experimental_component_use', 'scope': plain(context.scope),
        'target_ref': next(iter(roots)), 'target_regions': coverage, 'arguments': deepcopy(args),
        'component_family': next(iter(families)), 'operand_refs': sorted(refs), 'scientific_credit': None})


def _record_refs(value):
    refs = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if (key.endswith('_ref') or key == 'ref') and isinstance(item, str) and not item.startswith('artifact_'):
                refs.add(item)
            elif key.endswith('_refs') and isinstance(item, (list, tuple)):
                refs.update(ref for ref in item if isinstance(ref, str) and not ref.startswith('artifact_'))
            refs.update(_record_refs(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            refs.update(_record_refs(item))
    return refs


def _map(store, actual, target, known, *, alignment_ref=None, positions=None):
    if actual is None or target is None:
        return {'state': 'unresolved', 'missing': ['particular_source_and_target_molecule']}, set()
    if {actual, target} - known:
        return {'state': 'unresolved', 'missing': ['actually_received_molecular_reference'],
            'required_record_refs': sorted({actual, target} - known)}, set()
    try:
        result, refs = protein_correspondence(store, actual, target, known,
            alignment_ref=alignment_ref, positions=positions)
    except (ValueError, KeyError, TypeError) as error:
        return {'state': 'unresolved', 'missing': [str(error)]}, set()
    return result, set(refs)


def calculate(store, original, context, known, *, retained_rows=()):
    args = original['arguments']
    reader = _reader(store, context.run_id, args['sheet_ref'])
    rows = reader.fact_cells(context, [args['sheet_ref']], components=args['components'])
    # A received qualified record is also an authenticated result containing
    # its exact selected quantities. Reuse only those actual rows, never other
    # cells in the upstream sheet, when refreshing that same qualification.
    by_component = {row['component']: row for row in rows}
    for row in retained_rows:
        if row['sheet_ref'] == args['sheet_ref'] and row['component'] in args['components']:
            reader.validate_returned_values([row], permitted_record_refs=context.received_record_refs)
            require(row['component'] not in by_component or
                canonical(by_component[row['component']]) == canonical(row),
                'a110_experimental_retained_component_conflict')
            by_component[row['component']] = deepcopy(row)
    rows = [by_component[name] for name in args['components'] if name in by_component]
    missing_components = sorted(set(args['components']) - {row['component'] for row in rows})
    refs = set(original['operand_refs'])
    missing = ['original_experimental_components_not_received'] if missing_components else []
    metadata_refs = _record_refs(rows)
    required = metadata_refs - known
    if required:
        missing.append('selected_component_identity_or_context_not_received')
    refs.update(metadata_refs & known)
    from .literature_reaction_storage import literal_reference_role
    invalid_experiments = sorted({row['experiment_ref'] for row in rows
        if row.get('experiment_ref') in known and literal_reference_role(
            store.get(row['experiment_ref'])) in {'molecule', 'construct'}})
    if invalid_experiments:
        missing.append('selected_experiment_identity_is_subject_or_construct_literal')
    source_subject = rows[0].get('assayed_subject_ref') if rows else None
    source_finding, experiment_binding = None, None
    if args['reaction_ref'] is None:
        missing.append('particular_source_reaction_reference')
    else:
        reaction = store.get(args['reaction_ref'])
        require(reaction['record_type'] == 'term' and (reaction.get('term_type') == 'reaction'
            or reaction.get('namespace') in {'literature_reaction_reaction', 'literature_reaction_process'})
            or reaction['record_type'] == 'reference' and reaction.get('reference_type') == 'reaction',
            'a110_experimental_reaction_reference_required')
    if original['component_family'] == 'ratio':
        models = rows[0].get('model_definitions', []) if rows else []
        if any(name != 'ratio_mean' for name in args['components']) and not models:
            missing.append('source_bound_prediction_model_definition')
    else:
        demand = rows[0].get('demand_definition') if rows else None
        if not demand:
            missing.append('source_bound_resource_model_definition')
        if not demand or args['reaction_ref'] is None or demand.get('process_ref') != args['reaction_ref']:
            missing.append('particular_resource_model_to_reaction_correspondence')
    source_identity = None
    if args.get('source_identity_ref') is not None and source_subject is not None:
        from .component_source_identity import use as identity_use
        source_identity, used = identity_use(store, args['source_identity_ref'], source_subject, known,
            experiment_refs=[row['experiment_ref'] for row in rows if row.get('experiment_ref') is not None])
        refs.update(used)
        missing.extend(source_identity['missing'])
        required.update(source_identity['required_record_refs'])
    actual = args['actual_ref'] or (source_identity['actual_ref'] if source_identity is not None else source_subject)
    if source_subject is None:
        missing.append('actual_assayed_molecule_identity')
    source_link, target_link = None, None
    if source_subject is not None and actual is not None:
        if source_identity is not None:
            source_link, mapped = _map(store, source_identity['actual_ref'], actual, known,
                alignment_ref=args['source_alignment_ref'])
            source_link['source_identity_use'] = source_identity
        elif source_subject == actual:
            source_link, mapped = {'state': 'same_received_subject', 'missing': [],
                'actual_ref': source_subject, 'reference_ref': actual}, {actual} & known
        else:
            source_link, mapped = _map(store, source_subject, actual, known,
                alignment_ref=args['source_alignment_ref'])
        refs.update(mapped)
        missing.extend(source_link['missing'])
        required.update(source_link.get('required_record_refs', []))
    if args['target_subject_ref'] is not None:
        target_link, mapped = _map(store, actual, args['target_subject_ref'], known,
            alignment_ref=args['alignment_ref'], positions=args['positions'])
        refs.update(mapped)
        missing.extend(target_link['missing'])
        required.update(target_link.get('required_record_refs', []))
    else:
        missing.append('particular_target_molecular_application_not_requested')
    if args['assessment_ref'] is None:
        missing.append('source_supported_molecular_reaction_finding')
    else:
        assessment = store.get(args['assessment_ref'])
        require(assessment['record_type'] == 'assessment', 'a110_experimental_source_assessment_required')
        needed = {assessment['hypothesis_ref'], assessment['observation_ref']}
        require(needed <= known, 'a110_experimental_assessment_witnesses_not_received')
        refs.update(needed)
        finding = assessment.get('investigation_finding')
        require(finding is not None, 'a110_experimental_retained_function_finding_required')
        claim = finding['source_claim']
        observation = store.get(assessment['observation_ref'])
        source_finding = {'assessment_ref': args['assessment_ref'], 'source_claim': deepcopy(claim),
            'qualification': deepcopy(finding['qualification']), 'relation': assessment['relation'],
            'applicability': assessment['applicability'], 'observation_ref': observation['id'],
            'observation_source_ref': observation['source_ref']}
        if (claim['predicate'] not in {'catalyzes', 'transports', 'participates_in'}
                or claim['value'].get('type') != 'reference'
                or claim['value'].get('ref') != args['reaction_ref']
                or source_subject not in claim['subject_refs']):
            missing.append('finding_not_bound_to_selected_measurement_subject_and_reaction')
        observation_links = {*observation.get('subject_refs', []),
            *observation.get('source_subject_refs', []), *observation.get('dependencies', [])}
        experiments = sorted({row['experiment_ref'] for row in rows
            if row.get('experiment_ref') is not None})
        unidentified = [row['component'] for row in rows if row.get('experiment_ref') is None]
        unlinked = sorted(set(experiments) - observation_links)
        if unidentified or not rows:
            missing.append('selected_reaction_component_experiment_identity_unreported')
        if unlinked:
            missing.append('function_finding_observation_to_selected_experiment_link_unestablished')
        experiment_binding = {'version': EXPERIMENT_BINDING_VERSION,
            'source_observation_ref': observation['id'], 'selected_experiment_refs': experiments,
            'linked_experiment_refs': sorted((set(experiments) & observation_links) - set(invalid_experiments)),
            'unlinked_experiment_refs': unlinked,
            'unidentified_experiment_components': unidentified,
            'basis': 'explicit_observation_link_to_original_sheet_experiment',
            'state': 'unresolved' if not rows or unidentified or unlinked or invalid_experiments else 'matched'}
        if invalid_experiments:
            experiment_binding['invalid_experiment_refs'] = invalid_experiments
        refs.update(_record_refs(source_finding) & known)
        required.update(_record_refs(source_finding) - known)
        from .component_assessment_dependencies import assessment_dependencies, correction_refs
        dependency = assessment_dependencies(store, args['assessment_ref'], known)
        replacements = dependency['replacement_refs']
        refs.update(correction_refs(dependency))
        source_finding['replacement_refs'] = sorted(replacements)
        source_finding['assessment_revision_dependency'] = dependency
        if dependency['retired']:
            missing.append('source_function_finding_withdrawn_or_replaced')
        if dependency['superseding_assessment_refs']:
            missing.append('source_function_assessment_superseded_by_received_revision')
    if required:
        missing.append('source_context_or_correspondence_witness_not_received')
    if any(row.get('operand_source_kind') == 'synthetic_fixture' for row in rows):
        missing.append('synthetic_inputs_do_not_establish_physical_application')
    return {'state': 'per_use_application_unresolved' if missing else 'per_use_evidence_retained',
        'missing': list(dict.fromkeys(missing)), 'missing_components': missing_components,
        'required_record_refs': sorted(required), 'sheet_ref': args['sheet_ref'],
        'component_family': original['component_family'], 'selected_components': deepcopy(rows),
        'source_assayed_subject_ref': source_subject, 'actual_reference_ref': actual,
        'reaction_ref': args['reaction_ref'], 'source_function_finding': source_finding,
        'experiment_binding': experiment_binding,
        'measured_subject_correspondence': source_link, 'component_correspondence': target_link,
        'quantity_scope': 'original_source_measurement_or_model; not_a_new_target_or_region_measurement',
        'limitation': 'Source quantities and model definitions retain their original conditions, uncertainty and dependence. Reaction assertions and sequence correspondence do not demonstrate target activity or physiological resource availability.'}, refs


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
            continue  # Do not reopen unreceived upstream evidence at a receiver.
        retained = [cell for row in old for cell in row['result']['selected_components']]
        result, refs = calculate(store, original, context, known, retained_rows=retained)
        require(refs <= known, 'a110_experimental_qualification_dependencies_not_received')
        body = {'version': VERSION, 'qualification_kind': 'experimental_component_use',
            'scope': original['scope'], 'target_ref': original['target_ref'],
            'target_regions': original['target_regions'], 'request_ref': reference, 'result': result,
            'qualification_dependencies': sorted(refs),
            'operand_signatures': {ref: digest(store.get(ref)) for ref in sorted(refs)}, 'scientific_credit': None}
        generated.append(publish(store, PROVIDER, body))
        if result['missing']:
            needs.append((reference, {'target_ref': original['target_ref'], 'policy': TOOL,
                'missing': result['missing'], 'required_operands': {
                    'source_refs': [original['arguments']['sheet_ref']],
                    'record_refs': result['required_record_refs'],
                    'recorded_fact_sources': [reader_source(store, context.run_id, original['arguments']['sheet_ref'])]}}))
    return list(dict.fromkeys(generated)), needs


def reader_source(store, run_id, sheet_ref):
    return _reader(store, run_id, sheet_ref).cells_schema()['x-source']


def received(store, references, scope):
    result = []
    for reference in sorted(set(references)):
        body = read(store, reference, qualified=True)
        if body is None or not store.scope_contains(plain(scope), body['scope']):
            continue
        row = {'source_ref': reference, **deepcopy(body)}
        for field in ('measured_subject_correspondence', 'component_correspondence'):
            link = row['result'].get(field)
            if link is not None and 'pairs' in link:
                pairs = link.pop('pairs')
                link['native_pair_map'] = {'source_ref': reference,
                    'artifact_ref': store.get(reference)['artifact_ref'],
                    'pointer': '/result/'+field+'/pairs', 'pair_count': len(pairs)}
        result.append(row)
    return result
