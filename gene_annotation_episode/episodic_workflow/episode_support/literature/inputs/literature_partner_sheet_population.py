"""Original A107 partner source read, calculation, publication and replay."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_partner_sheet_records import BINDINGS, ContractError, LITERAL_REFERENCE_ROLES_VERSION, _arguments_schema, _binding_record, _condition_refs, _condition_role, _direct_references, _factor_names, _factor_record, _metadata, _native_operand_projection, assessments, canonical, deepcopy, identity, plain, publication, read_partner_inputs, validate_schema

@publication
def populate(self, context, arguments, operation_key):
    if context.run_id != self.run_id:
        raise ContractError('literature_run_mismatch')
    if not isinstance(operation_key, str) or not operation_key:
        raise ContractError('operation_key_required')
    args = plain(arguments)
    validate_schema(args, _arguments_schema(args))
    assessment = args.get('experiment_assessment')
    if assessment is not None:
        assessments.authorize_assessment(self, context, assessment)
    signature = canonical({'arguments': args, 'scope': plain(context.scope)})
    parameters = (self.run_id, context.episode_id, operation_key)
    query = f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?'
    old = self.store.db.execute(query, parameters).fetchone()
    if old is not None:
        return self._replay(context, old, signature)
    if assessment is not None:
        self._authorize_assessment(context, assessment)
    with self.store.transaction():
        old = self.store.db.execute(query, parameters).fetchone()
        if old is not None:
            return self._replay(context, old, signature)
        if assessment is not None:
            assessments.check_revision(self, assessment)

        def read_source(reference, representation):
            source = self._source(context, reference)
            if representation not in ('original', 'text'):
                raise ContractError('literature_source_representation_required')
            artifact = source['artifact_ref'] if representation == 'original' else source.get('text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': self.store.get_artifact(artifact)}
        extraction = read_partner_inputs(args, read_source=read_source)
        direct = _direct_references(args)
        if len(extraction['sources']) != len(direct) or set(extraction['sources']) != set(direct):
            raise ContractError('literature_partner_direct_source_mismatch')
        for reference in direct:
            self._source(context, reference)
        extra_parents = self._assessment_sources(assessment)
        parents = self._parents(context.scope, list(dict.fromkeys([*direct, *extra_parents])))
        source = self.store.get(args['source_ref'])
        payload = {'version': self.record_version, 'input_source_ref': source['id'], 'input_artifact_ref': source['artifact_ref'], 'input_source_refs': parents, 'direct_input_source_refs': direct, 'data_source_ref': args['data_source_ref'], 'extraction': extraction, 'sheet': {'cells': deepcopy(extraction['cells'])}}
        payload['literal_reference_roles_version'] = LITERAL_REFERENCE_ROLES_VERSION
        created = []

        def publish(kind, record):
            candidate = identity(kind, {'origin': 'tool', 'record': record})
            exists = self.store.db.execute('SELECT 1 FROM records WHERE id=?', (candidate,)).fetchone()
            row = self.store.put(kind, record, origin='tool', scope=plain(context.scope))
            if exists is None:
                created.append(row['id'])
            return row['id']
        bindings = {}
        native_projection = native_records = None
        native_common, interpretation = ({}, extraction['literals'])
        if args.get('input_mode') == 'native_source_spans':
            native_projection, native_records, native_common, interpretation = _native_operand_projection(extraction)
            for kind, record in native_records.values():
                publish(kind, record)
            payload['native_operand_bindings'] = native_projection
        for field, (literal, kind) in BINDINGS.items():
            if field == 'experiment_ref' and assessment is not None:
                bindings[field] = assessment['experiment_ref']
                continue
            if field in native_common:
                bindings[field] = native_common[field]
                continue
            entry = extraction['literals'][literal]
            if entry and kind == 'context':
                publish('reference', _condition_role(literal, entry))
            bindings[field] = publish(kind, _binding_record(literal, kind, entry)) if entry else None
        payload['experimental_bindings'] = bindings
        if assessment is not None:
            payload['experiment_assessment'] = deepcopy(assessment)
        factor_bindings = {name: publish('term', _factor_record(args['data_source_ref'], name)) for name in _factor_names(extraction)}
        payload['factor_bindings'] = factor_bindings
        artifact = self.store.artifact(canonical(payload), 'application/json')
        request = self.store.artifact(canonical({'run_id': self.run_id, 'episode_id': context.episode_id, 'operation_key': operation_key, 'arguments': args, 'scope': plain(context.scope)}), 'application/json')
        sheet_ref = publish('source', {'provider': self.provider, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request, 'version': self.record_version, 'retrieved_at': None, 'parent_source_refs': parents})
        outcome = {'status': 'completed', 'operation_ref': identity('operation', {'run_id': self.run_id, 'episode_id': context.episode_id, 'key': operation_key}), 'record_refs': list(dict.fromkeys([sheet_ref, *parents, *(reference for reference in bindings.values() if reference), *(native_records if native_records is not None else _condition_refs(extraction)), *(factor_bindings[name] for name in sorted(factor_bindings))])), 'changed_record_refs': created, 'result': {'sheet_ref': sheet_ref, 'cells': deepcopy(extraction['cells']), 'assay_interpretation': deepcopy(interpretation), **_metadata(extraction, factor_bindings)}, 'feedback': None}
        if assessment is not None:
            outcome['result']['experiment_assessment'] = deepcopy(assessment)
        self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)', (*parameters, signature, canonical(outcome)))
    return outcome
