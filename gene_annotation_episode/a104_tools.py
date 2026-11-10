"""A104 tools: exact HPC requests, native readers and measured tree tests."""
from __future__ import annotations

import json
from pathlib import Path

from .communication import plain
from .domain import canonical, obj, validate_schema, ContractError
from .episode_return_records import EpisodeReturnRecords
from .tools import ToolRegistry
from .a104_hpc import request_body, native_body, import_result, prepare_request, commission, require, _source
from .a104_publication import publish, received_measurement, native_observation
from .a104_scoring import placement, history_comparison, VERSION


REF = {'type': 'string', 'format': 'reference'}
TEXT = {'type': 'string', 'minLength': 1}
REFS = {'type': 'array', 'items': REF, 'uniqueItems': True}
NAMES = ('phylogeny.request_analysis', 'phylogeny.import_hpc', 'phylogeny.inspect',
         'phylogeny.measure_placement', 'phylogeny.compare_histories',
         'phylogeny.clade_functions', 'phylogeny.compare_placements', 'phylogeny.prepare_analysis')


def catalog():
    regions = {'type': 'array', 'minItems': 1, 'items': {'type': 'array', 'minItems': 2,
        'maxItems': 2, 'items': {'type': 'integer', 'minimum': 0}}}
    part = obj({'subject_ref': REF, 'regions': regions}, required=['subject_ref'])
    member = obj({'tip_id': TEXT, 'parts': {'type': 'array', 'items': part, 'minItems': 1},
                  'taxon_id': {'type': 'integer', 'minimum': 1}}, required=['tip_id', 'parts'])
    analysis = obj({'name': TEXT, 'purpose': {'enum': ['family', 'organismal_reference', 'regional', 'sensitivity']},
        'members': {'type': 'array', 'items': member, 'minItems': 4, 'maxItems': 64},
        'model': {'enum': ['LG', 'MFP']}, 'seed': {'type': 'integer', 'minimum': 1},
        'organismal_basis': obj({'kind': TEXT, 'markers': {'type': 'array', 'items': TEXT},
            'limitations': {'type': 'array', 'items': TEXT}, 'unknown_marker_sets': {'type': 'array',
                'items': obj({'taxon_id': {'type': 'integer'}, 'marker': TEXT, 'reason': TEXT})}},
                required=['kind', 'markers', 'limitations'])}, required=['name', 'purpose', 'members'])
    entries = {
        NAMES[0]: ('Request an exact prepared native analysis through the shared parent. This creates a typed '
            'HPC need and zero A104 credit; it runs no alignment, inference or bootstrap locally.', obj({'request_ref': REF})),
        NAMES[1]: ('Admit actual results of the original shared-HPC execution. Verify input/worker hashes, native '
            'files, sequence/region/tip identity and original PBS collection. An imported tree alone creates no placement credit.',
            obj({'request_ref': REF, 'hpc_result_ref': REF})),
        NAMES[2]: ('Read actual received native tree splits, their support, original tip/region/taxon bindings, '
            'and available independent organismal analyses. corresponding_relationships matches physical '
            'reference groups across analyses and supplies their analysis-local split indices. '
            'This is a read, with no new scientific score.', obj({'native_ref': REF})),
        NAMES[3]: ('Measure one actual native target-containing split and its original bootstrap population. '
            'Return its exact target region and reference members. Function and biological rooting remain separate.',
            obj({'native_ref': REF, 'analysis': TEXT, 'split_index': {'type': 'integer', 'minimum': 0}})),
        NAMES[4]: ('Calculate shared-tip unrooted relationships between the actual family and independent '
            'organismal tree. Supply one explicit copy per taxon and include the target. Retain omitted taxa and '
            'native support. Discordance alone does not diagnose transfer.', obj({'native_ref': REF,
                'family_analysis': TEXT, 'organismal_analysis': TEXT,
                'tip_ids': {'type': 'array', 'items': TEXT, 'uniqueItems': True, 'minItems': 4}})),
        NAMES[5]: ('Measure characterized and unknown membership of this particular native clade using received '
            'A105 experimental worksheet links. Copied protein names cannot characterize members. Missing '
            'reference characterization is published to the shared parent; it does not erase other native tests. '
            'Supply the measurement_ref returned by phylogeny.measure_placement as placement_ref.',
            obj({'placement_ref': REF})),
        NAMES[6]: ('Compare genuinely different native placement analyses over the same target region and '
            'declared reference-member set. Retain conflicting placements as a compared set rather than picking '
            'the highest support. Supply the measurement_ref values returned by phylogeny.measure_placement.',
            obj({'placement_refs': {**REFS, 'minItems': 2}})),
        NAMES[7]: ('Freeze a new exact native request from received actual protein parts. Choose the panel, '
            'target regions and model/seed alternatives explicitly. This does metadata copying only, with zero '
            'A104 credit. Then use request_analysis to send the request to the shared execution parent.',
            obj({'target_ref': REF, 'case_id': TEXT, 'analyses': {'type': 'array', 'items': analysis, 'minItems': 1},
                 'target_origin_reference_ref': REF, 'model': {'enum': ['LG', 'MFP']},
                 'seed': {'type': 'integer', 'minimum': 1}}, required=['target_ref', 'case_id', 'analyses'])),
    }
    return {name: {'description': description, 'input_schema': schema, 'resources': 'local'}
            for name, (description, schema) in entries.items()}


class A104ToolRegistry(ToolRegistry):
    def __init__(self, *args, a104_work_directory, a104_execution_resources=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.a104_execution_resources = plain(a104_execution_resources) if a104_execution_resources is not None else None
        self.a104_directory = Path(a104_work_directory).resolve()
        require('runs' in self.a104_directory.parts, 'a104_outputs_require_runs_directory')
        self.a104_directory.mkdir(parents=True, exist_ok=True)
        self.store.db.execute('CREATE TABLE IF NOT EXISTS a104_operations '
                              '(operation_key TEXT PRIMARY KEY, request TEXT NOT NULL, result TEXT NOT NULL)')

    def as_record(self):
        return {**super().as_record(), 'a104_tools': {'version': VERSION, 'directory': str(self.a104_directory),
                'execution': 'shared_hpc_only_for_alignment_inference_and_bootstrap',
                'execution_resources': self.a104_execution_resources}}

    def catalog(self, scope=None):
        return {**super().catalog(scope=scope), **catalog()}

    def model_contract_catalog(self, context):
        """Keep names and exact requested contracts; look up other types on use.

        Unrelated registered assay schemas can occupy megabytes. The host's
        actual return-contract registry stays intact and available through
        episode.return_contract; these are presentation metadata, not evidence.
        """
        sources = context.get('available_report_facts', {})
        requested = {node.get('x-source') for node in (context.get('requested_form') or {}).get('properties', {}).values()}
        retained = requested | {'credit', 'committed_record_refs', 'changed_record_refs',
                                'a104_received_evolutionary_records'}
        return {name: value if name in retained else {key: value[key] for key in ('type', 'meaning') if key in value}
                for name, value in sources.items()}

    def received_attributions(self, context, known):
        if context.role not in {'annotation', 'scientific_process', 'improvement'}:
            return [], []
        if context.role == 'scientific_process' and context.assignment.get('selection', {}).get('evidence_axis', {}).get('option_id') != 'A104':
            return [], []
        # A typed HPC result delivered to its scientific owner is admitted by
        # its exact registered reader before the next credit projection. This
        # is deterministic receipt routing, not a model-selected grader call.
        known = set(known)
        generated = []
        requests = {body['native_request_sha256']: reference for reference in known
                    if (body := request_body(self.store, reference)) is not None}
        imported = {body['hpc_result_ref'] for reference in known
                    if (body := native_body(self.store, reference)) is not None}
        for reference in sorted(known-imported):
            source = self.store.get(reference)
            if source.get('provider') != 'episode.hpc_result':
                continue
            receipt = json.loads(self.store.get_artifact(source['artifact_ref']))
            document = receipt.get('document', {})
            request = requests.get(document.get('request_sha256'))
            if document.get('program') != 'a104_phylogeny_native' or request is None:
                continue
            try:
                admitted = import_result(self.store, request_ref=request, hpc_result_ref=reference,
                    known_record_refs=known, scope=plain(context.scope), run_id=context.run_id)
            except (ValueError, KeyError) as error:
                body = request_body(self.store, request)
                admitted = _source(self.store, 'host.a104.import_failure', {'target_ref': body['target_ref'],
                    'request_ref': request, 'hpc_result_ref': reference, 'code': str(error),
                    'scientific_credit': 0., 'next_owner': 'shared_parent_original_result_repair'}, [body['target_ref']])
            generated.append(admitted)
        known.update(generated)
        from .a104_attachments import refresh
        attachments, needs = refresh(self.store, known, plain(context.scope), context=context)
        generated.extend(attachments)
        for reference in sorted(known):
            record = self.store.get(reference)
            if record.get('provider') != 'host.a104.analysis_need':
                continue
            body = json.loads(self.store.get_artifact(record['artifact_ref']))
            original = request_body(self.store, body['request_ref'])
            expected_names = {row['name'] for row in original['native_request']['analyses']}
            received_names = {row['name'] for ref in known if (native := native_body(self.store, ref)) is not None
                              and native['request_ref'] == body['request_ref'] for row in native['result']['analyses']}
            missing_names = expected_names-received_names
            if missing_names:
                needs.append((reference, {'target_ref': body['target_ref'], 'policy': 'a104_exact_hpc_analysis',
                    'missing': ['native_phylogeny_from_original_shared_hpc_job'], 'required_operands': {
                        'request_ref': body['request_ref'],
                        **({'commission_source_ref': body['commission_source_ref']} if body.get('commission_source_ref')
                           else {'commission_id': 'a104-native'}), 'resource_kind': 'hpc',
                        'missing_analysis_names': sorted(missing_names)}}))
        return generated, needs

    def _known(self, reference, known):
        require(reference in known, 'a104_tool_input_not_received')
        return self.store.get(reference)

    async def execute_async(self, name, args, *, scope=None, operation_key=None, permitted_record_refs=None):
        if name not in NAMES:
            return await super().execute_async(name, args, scope=scope, operation_key=operation_key,
                                              permitted_record_refs=permitted_record_refs)
        try:
            validate_schema(args, catalog()[name]['input_schema'])
            invocation = self._current_invocation.get()
            require(invocation is not None and invocation[2:] == (name, args, operation_key),
                    'a104_original_current_action_required')
            context = invocation[0]
            EpisodeReturnRecords(self.store, context.run_id, failure_prefix='a104_').authenticate(context)
            scope = self.store.validate_scope(scope)
            # Ordinary shared parents invoke their actual registry directly;
            # specialist execution passes the same frozen receipt set explicitly.
            known = set(context.received_record_refs if permitted_record_refs is None else permitted_record_refs)
            request = canonical({'run_id': context.run_id, 'episode_id': context.episode_id, 'name': name,
                                 'arguments': args, 'scope': scope, 'version': VERSION})
            prior = self.store.db.execute('SELECT request,result FROM a104_operations WHERE operation_key=?',
                                          (operation_key,)).fetchone()
            if prior:
                require(prior['request'] == request, 'a104_action_identity_conflict')
                return json.loads(prior['result'])
            if 'native_ref' in args:
                self._known(args['native_ref'], known)
                native = native_body(self.store, args['native_ref'])
                require(native is not None and native['target_ref'] in scope['subject_refs'], 'a104_native_scope_conflict')
            for reference in ([args['placement_ref']] if 'placement_ref' in args else args.get('placement_refs', [])):
                self._known(reference, known)
                measured = received_measurement(self.store, reference)
                require(measured is not None and measured['body']['schema'] == 'a104_placement_v1',
                        'a104_measured_placement_required')
                require(measured['body']['target_ref'] in scope['subject_refs'], 'a104_native_scope_conflict')
            references, result = [], None
            if name == NAMES[0]:
                self._known(args['request_ref'], known)
                body = request_body(self.store, args['request_ref'])
                require(body is not None and body['scope'] == scope, 'a104_exact_original_request_required')
                retained = [(ref, value) for ref in known if (value := native_body(self.store, ref)) is not None
                            and value['request_sha256'] == body['native_request_sha256']]
                required = {row['name'] for row in body['native_request']['analyses']}
                received = {row['name'] for _, value in retained for row in value['result']['analyses']}
                if required <= received:
                    references = sorted(ref for ref, _ in retained)
                    result = {'request_ref': args['request_ref'], 'native_phylogeny_refs': references,
                        'execution_status': 'already_completed_and_received', 'scientific_credit': 0.,
                        'next_action': 'phylogeny.inspect', 'new_execution_requested': False}
                else:
                    need = {'request_ref': args['request_ref'], 'target_ref': body['target_ref'], 'scope': scope,
                            'native_request_sha256': body['native_request_sha256'], 'resource_kind': 'hpc'}
                    if self.a104_execution_resources is not None:
                        from .hpc_commission_sources import publish as publish_commission
                        work = commission(self.store, args['request_ref'], self.a104_execution_resources['aurora'])
                        need['commission_source_ref'] = publish_commission(self.store, work,
                            scope=scope, resources=self.a104_execution_resources)
                    reference = _source(self.store, 'host.a104.analysis_need', need, [body['target_ref']])
                    references, result = [reference, args['request_ref'],
                        *([need['commission_source_ref']] if 'commission_source_ref' in need else [])], {**need, 'analysis_need_ref': reference,
                        'scientific_credit': 0., 'next_owner': 'shared_hpc_execution_service',
                        **({'hpc_assignment': {'commission_source_ref': need['commission_source_ref']}}
                           if 'commission_source_ref' in need else {})}
            elif name == NAMES[1]:
                retained = sorted(ref for ref in known if (value := native_body(self.store, ref)) is not None
                    and value['request_ref'] == args['request_ref'] and value['hpc_result_ref'] == args['hpc_result_ref']
                    and value['scope'] == scope)
                # A retained, already authenticated result keeps its original
                # PBS/run identity. Reusing that received grant does not need
                # another import under the current scientific run's identity.
                reference = retained[0] if retained else import_result(self.store,
                    request_ref=args['request_ref'], hpc_result_ref=args['hpc_result_ref'],
                    known_record_refs=known, scope=scope, run_id=context.run_id)
                references, result = [reference], {'native_ref': reference, 'scientific_status': 'received_actual_native_trees'}
            elif name == NAMES[2]:
                from .a104_scoring import relationship_inventory
                self._known(args['native_ref'], known)
                body = native_body(self.store, args['native_ref'])
                require(body is not None and body['target_ref'] in scope['subject_refs'], 'a104_native_scope_conflict')
                result = {'native_ref': args['native_ref'], 'pbs_job_id': body['pbs_job_id'],
                    'admission_status': 'already_authenticated_native_phylogeny; use_measurement_tools_directly',
                    'partial_execution': body.get('partial_execution', not body['result']['completed']),
                    'missing_analysis_names': body.get('missing_analysis_names', []),
                    'corresponding_relationships': relationship_inventory(body),
                    'analyses': [{'name': row['name'], 'purpose': row['purpose'],
                        'native_splits': [{**split, 'split_index': i} for i, split in enumerate(row['tree_summary']['splits'])],
                        'members': next(binding['members'] for binding in body['bindings'] if binding['name'] == row['name'])}
                        for row in body['result']['analyses']]}
            elif name == NAMES[3]:
                body = placement(self.store, args['native_ref'], args['analysis'], args['split_index'], known)
                reference = publish(self.store, body)
                references, result = [reference], {'measurement_ref': reference, **body}
            elif name == NAMES[4]:
                body = history_comparison(self.store, args['native_ref'], args['family_analysis'], args['organismal_analysis'],
                                           args['tip_ids'], known)
                reference = publish(self.store, body)
                references, result = [reference], {'measurement_ref': reference, **body}
            elif name == NAMES[5]:
                from .a104_interpretation import clade_composition
                body = clade_composition(self.store, args['placement_ref'], known)
                reference = publish(self.store, body)
                references, result = [reference], {'measurement_ref': reference, **body}
            elif name == NAMES[6]:
                from .a104_interpretation import compare_placements
                body = compare_placements(self.store, args['placement_refs'], known)
                reference = publish(self.store, body)
                references, result = [reference], {'measurement_ref': reference, **body}
            else:
                reference = prepare_request(self.store, scope=scope, known_record_refs=known, **args)
                references, result = [reference], {'request_ref': reference, 'scientific_credit': 0.,
                    'next_action': 'phylogeny.request_analysis', 'execution_owner': 'shared_parent_hpc_service'}
            if name in NAMES[3:7]:
                observation = native_observation(self.store, reference)
                references.append(observation)
                result['observation_ref'] = observation
            outcome = {'status': 'completed', 'record_refs': references, 'changed_record_refs': [],
                       'result': result, 'feedback': None}
            self.store.db.execute('INSERT INTO a104_operations VALUES(?,?,?)', (operation_key, request, canonical(outcome)))
            return outcome
        except (ValueError, KeyError, TypeError, IndexError) as error:
            detail = getattr(error, 'detail', {})
            if str(error) == 'a104_measured_placement_required':
                detail = {**detail, 'recovery': 'Use the measurement_ref returned by phylogeny.measure_placement '
                    'for each placement operand.'}
            return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'code': str(error), 'detail': detail}}
