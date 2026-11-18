"""Own source interpretation and required grading in the original action."""
from gene_annotation_episode.episodic_workflow.root.a104.library.required_evidence_contracts import ContractError, ExperimentalContractError, ORIGINAL_RESULTS, SCIENTIFIC_SECTIONS, _Sources, _matches_grading, _requires_sheet, _resolve, action_schema, json, plain, replace, source_location_inputs, validate_schema

def execute(context, selection, operation_key, repository, *, authorize_source_access):
    """Save the interpretation and its sheets before ordinary credit projection."""
    store = repository.store
    payload = plain(selection['commit'])
    processing = plain(selection.get('evidence_processing'))
    attempted = False
    try:
        validate_schema(selection, source_location_inputs(action_schema({'type': 'object'}, repository.population_schema())))
        if any((not isinstance(payload.get(section, []), list) for section in SCIENTIFIC_SECTIONS)):
            raise ContractError('representation_error')
        scientific = [row for section in SCIENTIFIC_SECTIONS for row in payload.get(section, [])]
        source_subjects = payload.get('source_subjects', [])
        original_results = [row for row in (source_subjects if isinstance(source_subjects, list) else []) if isinstance(row, dict) and row.get('reference_type') in ORIGINAL_RESULTS]
        if (scientific or original_results) and processing is None:
            raise ContractError('applicable_evidence_requires_grading')
        if processing is not None and processing['kind'] == 'no_applicable_evidence' and any((payload.get(section, []) for section in SCIENTIFIC_SECTIONS if section != 'observations')):
            raise ContractError('no_applicable_evidence_cannot_assess_evidence')
        missing_findings = [row.get('alias') for row in payload.get('assessments', []) if isinstance(row, dict) and (not isinstance(row.get('investigation_finding'), dict))]
        if missing_findings:
            raise ContractError('evidence_assessment_source_finding_required', detail={'assessment_aliases': missing_findings, 'required_field': 'investigation_finding', 'meaning': 'Record the actual source claim, its subject and qualification. A saved numerical sheet does not replace this scientific finding. Preserve unknown target correspondence; do not manufacture target support.'})
        with store.transaction():
            if processing is not None and processing['kind'] == 'no_applicable_evidence':
                attempted = True

                def read_source(ref, representation):
                    record = repository._native_source(context, ref)
                    authorize_source_access(ref, representation)
                    artifact = record.get('artifact_ref' if representation == 'original' else 'text_ref')
                    if artifact is None:
                        raise ContractError('literature_source_representation_unavailable')
                    return {'artifact_ref': artifact, 'content': store.get_artifact(artifact)}
                sources = _Sources(read_source)
                examined = [sources.witness(witness, f'examined[{index}]') for index, witness in enumerate(processing['examined'])]
                processing['examined'] = [{**original, 'quote': witness['quote']} for original, witness in zip(processing['examined'], examined)]
            account_binding = {'account_invocation': (context.run_id, context.episode_id)} if payload.get('interpretation_accounts') else {}
            attempted = True
            outcome = store.commit_reasoning(payload, plain(context.scope), operation_key, **account_binding)
            if outcome['status'] not in ('completed', 'partial'):
                return outcome
            if processing is not None and processing['kind'] == 'no_applicable_evidence':
                for ref in outcome['record_refs']:
                    record = store.get(ref)
                    if not (record['record_type'] == 'observation' or record.get('reference_type') in ORIGINAL_RESULTS):
                        continue
                    anchor = record.get('anchor')
                    if anchor is None or not any((anchor['source_ref'] == witness['source_ref'] and anchor['artifact_ref'] == witness['artifact_ref'] and (witness['start'] <= anchor['start'] < anchor['end'] <= witness['end']) for witness in examined)):
                        raise ContractError('no_applicable_observation_outside_examined_material')
            if processing is None or processing['kind'] == 'no_applicable_evidence':
                return {**outcome, 'evidence_processing': processing}
            grading_context = replace(context, received_record_refs=tuple(dict.fromkeys([*context.received_record_refs, *outcome['record_refs']])))
            gradings = _resolve(processing['gradings'], outcome['aliases'])
            required_refs = {ref for ref in outcome['record_refs'] if _requires_sheet(store.get(ref))}
            linked = set()
            results = []
            for index, grading in enumerate(gradings):
                try:
                    arguments = json.loads(grading['arguments'])
                except (ValueError, TypeError) as error:
                    raise ContractError('required_grading_arguments_json_object_required') from error
                if not isinstance(arguments, dict):
                    raise ContractError('required_grading_arguments_json_object_required')
                arguments = _resolve(arguments, outcome['aliases'])
                from gene_annotation_episode.episodic_workflow.root.a104.literature_assay_inputs import materialize_text_witness_inputs

                def read_grading_source(ref, representation):
                    record = repository._native_source(grading_context, ref)
                    authorize_source_access(ref, representation)
                    artifact = record.get('artifact_ref' if representation == 'original' else 'text_ref')
                    if artifact is None:
                        raise ContractError('literature_source_representation_unavailable')
                    return {'artifact_ref': artifact, 'content': store.get_artifact(artifact)}
                arguments = materialize_text_witness_inputs(arguments, read_source=read_grading_source)
                validate_schema(arguments, repository.population_schema())
                contextual = repository.provider == 'literature.a108.context_grading'
                linked_observations = [ref for ref in required_refs if store.get(ref)['record_type'] == 'observation']
                graded_refs = [ref for ref in required_refs if _matches_grading(store, ref, arguments, contextual=contextual, linked_observations=linked_observations)]
                result = repository.populate(grading_context, arguments, f'{operation_key}:grading:{index}')
                if result['status'] not in ('completed', 'partial') or not result['result'].get('sheet_ref'):
                    raise ContractError('required_grading_sheet_not_saved')
                linked.update(graded_refs)
                results.append(result)
            if linked != required_refs:
                raise ContractError('required_grading_interpretation_uncovered', detail={'ungraded_interpretation_refs': sorted(required_refs - linked)})
            return {**outcome, 'record_refs': list(dict.fromkeys([*outcome['record_refs'], *[ref for result in results for ref in result['record_refs']]])), 'changed_record_refs': list(dict.fromkeys([*outcome['changed_record_refs'], *[ref for result in results for ref in result['changed_record_refs']]])), 'evidence_processing': {'kind': 'graded', 'gradings': results}}
    except (ContractError, ExperimentalContractError) as error:
        return {'status': 'failed' if attempted else 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'required_evidence_grading', 'code': getattr(error, 'code', str(error)), **({'field': error.field} if isinstance(error, ExperimentalContractError) else {}), **({'detail': error.detail} if error.detail else {}), **({'reasoning_errors': outcome['errors'], 'reasoning_conflicts': outcome['conflicts']} if 'outcome' in locals() and (outcome['errors'] or outcome['conflicts']) else {})}}
