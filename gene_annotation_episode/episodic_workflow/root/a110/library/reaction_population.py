"""Original complete A110 source reaction publication and saved replay."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_population_contracts import BINDINGS, ContractError, LITERAL_REFERENCE_TYPES, MEANINGS_INPUT_VERSION, MEANINGS_RECORD_VERSION, _direct_references, _metadata, assessments, binding_references, canonical, deepcopy, identity, json, plain, populate_reaction_constraints, publication, publish_meanings, reaction_direct_references, reaction_population_schema, read_reaction_inputs, semantic_metadata, source_literal_label, validate_schema

@publication
def populate(self, context, arguments, operation_key):
    if context.run_id != self.run_id:
        raise ContractError('literature_run_mismatch')
    if not isinstance(operation_key, str) or not operation_key:
        raise ContractError('operation_key_required')
    args = plain(arguments)
    validate_schema(args, reaction_population_schema(include_assessment=True))
    signature = canonical({'arguments': args, 'scope': plain(context.scope)})
    old = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?', (self.run_id, context.episode_id, operation_key)).fetchone()
    if old is not None:
        if old['signature'] != signature:
            raise ContractError('operation_key_reused_for_different_work')
        outcome = json.loads(old['outcome'])
        saved = self.read(outcome['result']['sheet_ref'])
        for reference in saved['direct_input_source_refs']:
            self._source(context, reference)
        for reference in saved['input_source_refs']:
            self._provenance(context, reference)
        if 'experiment_assessment' in args:
            assessments.authorize_assessment(self, context, args['experiment_assessment'])
        return outcome
    assessment = args.get('experiment_assessment')
    if assessment is not None:
        self._authorize_assessment(context, assessment)
    direct = _direct_references(args)
    for reference in direct:
        self._source(context, reference)
    source = self.store.get(args['source_ref'])

    def read_source(reference, representation):
        row = self._source(context, reference)
        if representation not in ('original', 'text'):
            raise ContractError('literature_source_representation_required')
        artifact = row['artifact_ref'] if representation == 'original' else row.get('text_ref')
        if artifact is None:
            raise ContractError('literature_source_representation_unavailable')
        return {'artifact_ref': artifact, 'content': self.store.get_artifact(artifact)}
    extraction = read_reaction_inputs(args, read_source=read_source)
    direct = reaction_direct_references(extraction, direct)
    if set(extraction['sources']) != set(direct):
        raise ContractError('literature_reaction_direct_source_mismatch')
    sheet = populate_reaction_constraints(extraction['calculation_inputs'])
    parents, seen = (list(direct), set(direct))
    if assessment is not None:
        parents.append(self.store.get(assessment['experiment_ref'])['source_ref'])
        if assessment['revises_sheet_ref'] is not None:
            parents.append(assessment['revises_sheet_ref'])
        parents = list(dict.fromkeys(parents))
        seen = set(parents)
    cursor = 0
    while cursor < len(parents):
        reference = parents[cursor]
        cursor += 1
        for parent in self.store.get(reference).get('parent_source_refs', ()):
            self._provenance(context, parent)
            if parent not in seen:
                seen.add(parent)
                parents.append(parent)
    record_version = MEANINGS_RECORD_VERSION if extraction['version'] == MEANINGS_INPUT_VERSION else self.record_version
    payload = {'version': record_version, 'input_source_ref': source['id'], 'input_artifact_ref': source['artifact_ref'], 'input_source_refs': parents, 'direct_input_source_refs': direct, 'data_source_ref': args['data_source_ref'], 'extraction': extraction, 'sheet': sheet}
    with self.store.transaction():
        if assessment is not None:
            assessments.check_revision(self, assessment)
        created = []

        def publish(kind, record):
            candidate = identity(kind, {'origin': 'tool', 'record': record})
            existed = self.store.db.execute('SELECT 1 FROM records WHERE id=?', (candidate,)).fetchone()
            row = self.store.put(kind, record, origin='tool', scope=plain(context.scope))
            if existed is None:
                created.append(row['id'])
            return row['id']
        bindings = {}
        for field, (literal, kind) in BINDINGS.items():
            if field == 'experiment_ref' and assessment is not None:
                bindings[field] = assessment['experiment_ref']
                continue
            entry = extraction['literals'][literal]
            if entry is None:
                bindings[field] = None
                continue
            witness = entry['witness']
            anchor = {name: witness[name] for name in ('source_ref', 'artifact_ref', 'start', 'end', 'quote')}
            common = {'source_ref': witness['source_ref'], 'anchor': anchor}
            accession = identity('reaction_literal', {'field': literal, **anchor})
            label = source_literal_label(entry['value'])
            if kind == 'reference':
                record = {**common, 'reference_type': LITERAL_REFERENCE_TYPES[literal], 'accession': accession, 'label': label, 'sequence_ref': None, 'molecule': None, 'length': None, 'term_refs': [], 'context_refs': []}
            elif kind == 'term':
                record = {**common, 'namespace': 'literature_reaction_' + literal, 'accession': accession, 'label': label, 'term_type': 'other'}
            else:
                record = {**common, 'context_type': 'assay_condition', 'name': label, 'attributes': [], 'related_refs': []}
            bindings[field] = publish(kind, record)
        if assessment is not None:
            bindings['experiment_ref'] = assessment['experiment_ref']
            payload['experiment_assessment'] = deepcopy(assessment)
        payload['experimental_bindings'] = bindings
        semantic_bindings = publish_meanings(extraction, publish) if record_version == MEANINGS_RECORD_VERSION else None
        if semantic_bindings is not None:
            payload['semantic_bindings'] = semantic_bindings
        metadata = _metadata(extraction, sheet)
        if semantic_bindings is not None:
            metadata = semantic_metadata(metadata, semantic_bindings, extraction['calculation_inputs'], sheet)
        native_rows = None
        if 'native_evidence' in extraction:
            from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_native_observations import publish_native_observations
            native_rows = publish_native_observations(extraction, bindings, semantic_bindings, publish)
            payload['native_observations'] = native_rows
            from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_native_observations import native_row_references
        artifact = self.store.artifact(canonical(payload), 'application/json')
        request = self.store.artifact(canonical({'run_id': self.run_id, 'episode_id': context.episode_id, 'operation_key': operation_key, 'arguments': args, 'scope': plain(context.scope)}), 'application/json')
        sheet_ref = publish('source', {'provider': self.provider, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request, 'version': record_version, 'retrieved_at': None, 'parent_source_refs': parents})
        outcome = {'status': 'completed', 'operation_ref': identity('operation', {'run_id': self.run_id, 'episode_id': context.episode_id, 'key': operation_key}), 'record_refs': list(dict.fromkeys([sheet_ref, *parents, *(reference for reference in bindings.values() if reference), *(binding_references(semantic_bindings) if semantic_bindings is not None else []), *(native_row_references(native_rows) if native_rows is not None else [])])), 'changed_record_refs': created, 'result': {'sheet_ref': sheet_ref, 'cells': sheet['cells'], 'assay_interpretation': extraction['literals'], **metadata, **({'native_observations': native_rows} if native_rows is not None else {})}, 'feedback': None}
        if assessment is not None:
            outcome['result']['experiment_assessment'] = deepcopy(assessment)
        self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)', (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
    return outcome
