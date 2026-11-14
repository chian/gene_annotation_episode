"""A110 reaction storage, custody, exact saved projection and stable adapter identity."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_population_contracts import BASES, BINDINGS, COMPONENTS, CONDITIONAL_CODES, ContractError, DEMAND_FIELDS, EXPERIMENT_TYPES, FORMULA_CODES, LITERAL_FIELDS, LITERAL_REFERENCE_TYPES, MEANINGS_INPUT_VERSION, MEANINGS_NAMESPACE, MEANINGS_RECORD_VERSION, MODEL_FIELDS, PROVIDER, REASONS, RESOURCE_FIELDS, SOURCE_KINDS, _FIXED_METADATA, _direct_references, _metadata, annotations, assessments, binding_references, canonical, deepcopy, hashlib, identity, json, literal_reference_role, meaning_direct_references, obj, plain, populate_reaction_constraints, publication, publish_meanings, reaction_direct_references, reaction_population_schema, reaction_return_view_requirements, read_reaction_inputs, semantic_metadata, source_literal_label, validate_schema
from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_population import populate
from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_report_contracts import reaction_cells_schema, reaction_semantic_cells_schema

class LiteratureReactionRepository:
    experiment_types = EXPERIMENT_TYPES
    provider = PROVIDER
    components = COMPONENTS
    record_version = 'literature_reaction_record_v2'
    operations_table = 'literature_reaction_operations'
    received_table = 'literature_reaction_received'
    binding_fields = tuple(BINDINGS)

    def __init__(self, store, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('explicit_literature_run_required')
        self.store, self.run_id = (store, run_id)
        self._ensure_storage()

    def _ensure_storage(self):
        """Restore this adapter's schema after a caller transaction rolls back."""
        self.store.db.execute(f'CREATE TABLE IF NOT EXISTS {self.operations_table}(\n            run_id TEXT NOT NULL, episode_id TEXT NOT NULL, operation_key TEXT NOT NULL,\n            signature TEXT NOT NULL, outcome TEXT NOT NULL,\n            PRIMARY KEY(run_id,episode_id,operation_key))')
        self.store.db.execute(f'CREATE TABLE IF NOT EXISTS {self.received_table}(\n            run_id TEXT NOT NULL, episode_id TEXT NOT NULL, operation_key TEXT NOT NULL,\n            cells TEXT NOT NULL, PRIMARY KEY(run_id,episode_id,operation_key))')

    @property
    def _delivery_table(self):
        return self.received_table.removesuffix('_received') + '_delivery_bindings'

    def _delivery_binding(self, context, operation_key):
        installed = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (self._delivery_table,)).fetchone()
        return self.store.db.execute(f'SELECT cells_digest FROM {self._delivery_table} WHERE run_id=? AND episode_id=? AND operation_key=?', (self.run_id, context.episode_id, operation_key)).fetchone() if installed else None

    def _install_delivery_bindings(self):
        self.store.db.execute(f'CREATE TABLE IF NOT EXISTS {self._delivery_table}(\n            run_id TEXT NOT NULL, episode_id TEXT NOT NULL, operation_key TEXT NOT NULL,\n            cells_digest TEXT NOT NULL, PRIMARY KEY(run_id,episode_id,operation_key))')

    def _delivery_digest(self, cells):
        kind = self.received_table.removeprefix('literature_').removesuffix('_received')
        return identity(kind + '_admitted_cells', cells)

    def _runtime_delivery_cells(self, context, operation_key):
        """Authenticate runtime admission; other keys are a trusted manual API.

        A saved digest is not proof that runtime admitted the subset. Its actual
        successful form and original child contract supply that proof. Reading
        an old authentic runtime receipt needs no backfilled binding or history.
        """
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        prefix = self.run_id + ':' + context.episode_id + ':'
        if not operation_key.startswith(prefix) and (not operation_key.endswith(':typed_form')):
            return None
        suffix = operation_key[len(prefix):].split(':') if operation_key.startswith(prefix) else []
        if len(suffix) != 2 or not suffix[0].isascii() or (not suffix[0].isdigit()) or (suffix[1] != 'typed_form'):
            raise ContractError('literature_delivery_binding_mismatch')
        try:
            index = int(suffix[0])
        except ValueError as error:
            raise ContractError('literature_delivery_binding_mismatch') from error
        if index > 2 ** 63 - 1 or str(index) != suffix[0]:
            raise ContractError('literature_delivery_binding_mismatch')
        installed = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_report_attempts'").fetchone()
        attempt = self.store.db.execute('SELECT form,contract,failure,child_episode_id,delivery_ref FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (self.run_id, context.episode_id, index)).fetchone() if installed else None
        if attempt is None or attempt['form'] is None or attempt['failure'] is not None:
            raise ContractError('literature_delivery_binding_mismatch')
        try:
            form, contract = (json.loads(attempt['form']), json.loads(attempt['contract']))
            if self.store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_episodes'").fetchone() is None:
                raise ContractError('literature_delivery_binding_mismatch')
            child = self.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.run_id, attempt['child_episode_id'])).fetchone()
            if child is None:
                raise ContractError('literature_delivery_binding_mismatch')
            original_contract = json.loads(child['request'])['report_contract']
            if canonical(original_contract) != canonical(contract):
                installed_action = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_actions'").fetchone()
                action = self.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (self.run_id, context.episode_id, index)).fetchone() if installed_action else None
                installed_decision = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_model_calls'").fetchone()
                decision = self.store.db.execute("SELECT CASE WHEN json_valid(response) THEN response -> '$.selection' END AS selected FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index=? AND purpose='decision'", (self.run_id, context.episode_id, index)).fetchone() if installed_decision else None
                selected = json.loads(action['action']) if action else None
                chosen = json.loads(decision['selected']) if decision and decision['selected'] is not None else None
                if selected is not None and chosen is not None and (canonical(selected) != canonical(chosen)):
                    raise ContractError('literature_delivery_binding_mismatch')
                selected = selected if selected is not None else chosen
                if not isinstance(selected, dict):
                    raise ContractError('literature_delivery_binding_mismatch')
                prior = self.store.db.execute('SELECT child_episode_id,contract FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND delivery_ref=? AND decision_index<? ORDER BY decision_index LIMIT 1', (self.run_id, context.episode_id, selected.get('delivery_ref'), index)).fetchone()
                selected_schema = json.loads(selected['schema_json'])
                if not isinstance(selected_schema, dict) or not isinstance(selected_schema.get('properties'), dict):
                    raise ContractError('literature_delivery_binding_mismatch')
                for name, node in selected_schema['properties'].items():
                    if isinstance(node, dict) and set(node) == {'$ref'} and isinstance(node['$ref'], str) and node['$ref'].startswith('episode-fact:'):
                        source = node['$ref'][len('episode-fact:'):]
                        originals = {canonical(original): original for original in original_contract['measurements']['schema']['properties'].values() if isinstance(original, dict) and original.get('x-source') == source}
                        if len(originals) != 1:
                            raise ContractError('literature_delivery_binding_mismatch')
                        selected_schema['properties'][name] = next(iter(originals.values()))
                if selected.get('kind') != 'redeliver_report' or prior is None or attempt['delivery_ref'] != selected.get('delivery_ref') or (prior['child_episode_id'] != attempt['child_episode_id']) or (canonical(json.loads(prior['contract'])) != canonical(original_contract)) or (selected.get('purpose') != contract['decision']) or (canonical(selected_schema) != canonical(contract['measurements']['schema'])):
                    raise ContractError('literature_delivery_binding_mismatch')
            namespace = self.received_table.removesuffix('_received') + '_cells'
            fields = [name for name, node in contract['measurements']['schema']['properties'].items() if node.get('x-source') == namespace]
            if not fields:
                raise ContractError('literature_delivery_binding_mismatch')
            return [row for name in fields for row in form[name]]
        except (KeyError, TypeError, ValueError) as error:
            raise ContractError('literature_delivery_binding_mismatch') from error

    def _read_sheet(self, sheet_ref):
        """Read an A110 reaction sheet from its original selected operation."""
        source = self.store.get(sheet_ref)
        if source['record_type'] != 'source' or source['provider'] != self.provider or source['origin'] != 'tool' or (source['request_ref'] is None):
            raise ContractError('literature_reaction_sheet_required')
        request = json.loads(self.store.get_artifact(source['request_ref']))
        if request.get('run_id') != self.run_id:
            raise ContractError('literature_reaction_sheet_run_mismatch')
        operation = self.store.db.execute(f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?', (self.run_id, request.get('episode_id'), request.get('operation_key'))).fetchone()
        if operation is None or json.loads(operation['outcome']).get('result', {}).get('sheet_ref') != sheet_ref:
            raise ContractError('literature_reaction_sheet_not_selected_output')
        payload = json.loads(self.store.get_artifact(source['artifact_ref']))
        if payload.get('version') != self.record_version or source.get('version') != self.record_version or source.get('parent_source_refs') != payload.get('input_source_refs', [payload['input_source_ref']]) or (request.get('arguments', {}).get('source_ref') != payload['input_source_ref']):
            raise ContractError('literature_reaction_sheet_source_mismatch')
        return payload

    def validate_cells(self, cells, *, sheet_refs, permitted_record_refs, components=None):
        """Validate actual values and requested membership, beyond JSON syntax."""
        expected = self.project_cells(sheet_refs, permitted_record_refs=permitted_record_refs, components=components)
        if canonical(cells) != canonical(expected):
            raise ContractError('literature_reaction_return_differs_from_saved_cells')

    def _validate_returned_values(self, cells, *, permitted_record_refs):
        """Check each actual returned cell without exposing unrequested cells."""
        seen = set()
        for row in cells:
            key = (row['sheet_ref'], row['component'])
            if key in seen:
                raise ContractError('duplicate_literature_reaction_return_cell')
            seen.add(key)
            expected = self.project_cells([row['sheet_ref']], permitted_record_refs=permitted_record_refs, components=(row['component'],))
            if canonical(row) != canonical(expected[0]):
                raise ContractError('literature_reaction_return_differs_from_saved_cells')

    def _sheet_origin_episode(self, reference):
        """Check the original selected episode, without reading scientific bytes."""
        self.read(reference)
        source = self.store.get(reference)
        record = {key: value for key, value in source.items() if key not in ('id', 'record_type', 'origin')}
        if identity('source', {'origin': 'tool', 'record': record}) != reference:
            raise ContractError('literature_reaction_sheet_origin_mismatch')
        request_bytes = self.store.get_artifact(source['request_ref'])
        if 'artifact_' + hashlib.sha256(request_bytes).hexdigest() != source['request_ref']:
            raise ContractError('literature_reaction_sheet_origin_mismatch')
        request = json.loads(request_bytes)
        if request.get('run_id') != self.run_id or type(request.get('episode_id')) is not str or (not request['episode_id']) or (type(request.get('operation_key')) is not str) or (not request['operation_key']):
            raise ContractError('literature_reaction_sheet_origin_mismatch')
        operation = self.store.db.execute(f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?', (self.run_id, request['episode_id'], request['operation_key'])).fetchone()
        outcome = json.loads(operation['outcome']) if operation else {}
        if outcome.get('status') != 'completed' or outcome.get('result', {}).get('sheet_ref') != reference or reference not in outcome.get('record_refs', ()) or (outcome.get('operation_ref') != identity('operation', {'run_id': self.run_id, 'episode_id': request['episode_id'], 'key': request['operation_key']})):
            raise ContractError('literature_reaction_sheet_origin_mismatch')
        return request['episode_id']

    def fact_cells(self, context, sheet_refs, *, components):
        """Project owned cells or copy this receiver's exact admitted subset."""
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        self.project_cells([], permitted_record_refs=(), components=components)
        received = None
        result = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in context.received_record_refs:
                raise ContractError('literature_sheet_not_received')
            self.project_cells([reference], permitted_record_refs=context.received_record_refs, components=[])
            if self._sheet_origin_episode(reference) == context.episode_id:
                result.extend(self.project_cells([reference], permitted_record_refs=context.received_record_refs, components=components))
            else:
                if received is None:
                    received = {(row['sheet_ref'], row['component']): row for row in self.received_cells(context)}
                result.extend((deepcopy(received[reference, name]) for name in components if (reference, name) in received))
        return result

    def validate_fact_values(self, context, cells):
        """A valid saved row must also be possessed by the reporting episode."""
        self.validate_returned_values(cells, permitted_record_refs=context.received_record_refs)
        if not cells:
            return
        expected = {(row['sheet_ref'], row['component']): row for row in self.fact_cells(context, list(dict.fromkeys((row['sheet_ref'] for row in cells))), components=list(dict.fromkeys((row['component'] for row in cells))))}
        if any((canonical(row) != canonical(expected.get((row['sheet_ref'], row['component']))) for row in cells)):
            raise ContractError('literature_cell_not_received')

    def receive_cells(self, context, cells, operation_key):
        """Record exactly the already admitted subset, adding no observation."""
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        with self.store.transaction():
            original = self._runtime_delivery_cells(context, operation_key)
            if original is not None and canonical(original) != canonical(cells):
                raise ContractError('literature_delivery_binding_mismatch')
            self.validate_returned_values(cells, permitted_record_refs=[row['sheet_ref'] for row in cells])
            data = canonical(cells)
            old = self.store.db.execute(f'SELECT cells FROM {self.received_table} WHERE run_id=? AND episode_id=? AND operation_key=?', (self.run_id, context.episode_id, operation_key)).fetchone()
            if old is not None and old['cells'] != data:
                raise ContractError('literature_reaction_delivery_identity_conflict')
            digest = self._delivery_digest(cells)
            bound = self._delivery_binding(context, operation_key)
            if bound is not None and bound[0] != digest:
                raise ContractError('literature_delivery_binding_mismatch')
            if old is not None and bound is None and (original is None):
                raise ContractError('literature_delivery_binding_unavailable')
            if old is not None and bound is None:
                return
            self._install_delivery_bindings()
            self.store.db.execute(f'INSERT OR IGNORE INTO {self.received_table} VALUES(?,?,?,?)', (self.run_id, context.episode_id, operation_key, data))
            self.store.db.execute(f'INSERT OR IGNORE INTO {self._delivery_table} VALUES(?,?,?,?)', (self.run_id, context.episode_id, operation_key, digest))
            from .literature_sheet_updates import admitted
            admitted(self, context, cells, operation_key)

    def _received_cells(self, context):
        """Forward copied admitted cells, not the complete private child sheet."""
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        result, seen = ([], set())
        rows = self.store.db.execute(f'SELECT operation_key,cells FROM {self.received_table} WHERE run_id=? AND episode_id=? ORDER BY rowid', (self.run_id, context.episode_id))
        for saved in rows:
            cells = json.loads(saved['cells'])
            original = self._runtime_delivery_cells(context, saved['operation_key'])
            bound = self._delivery_binding(context, saved['operation_key'])
            if bound is None and original is None:
                raise ContractError('literature_delivery_binding_unavailable')
            if bound is not None and bound[0] != self._delivery_digest(cells) or (original is not None and canonical(original) != canonical(cells)):
                raise ContractError('literature_delivery_binding_mismatch')
            self.validate_returned_values(cells, permitted_record_refs=[row['sheet_ref'] for row in cells])
            for row in cells:
                key = (row['sheet_ref'], row['component'])
                if key not in seen:
                    seen.add(key)
                    result.append(deepcopy(row))
        return result

    def _authorize_assessment(self, context, value):
        assessments.authorize_assessment(self, context, value)
        if literal_reference_role(self.store.get(value['experiment_ref'])) in {'molecule', 'construct'}:
            raise ContractError('literature_reaction_experiment_identity_is_subject_or_construct_literal')

    def semantic_projection(self):
        return LiteratureReactionSemanticProjection(self.store, self.run_id)

    def native_observations_projection(self):
        from .literature_reaction_native_storage import LiteratureReactionNativeObservations
        return LiteratureReactionNativeObservations(self.store, self.run_id)

    def cells_schema(self):
        return reaction_cells_schema()

    def received_cells(self, context):
        from .component_axis_cell_receipts import inherited_cells
        return inherited_cells(self, context, self._received_cells(context))

    def _row_metadata(self, saved):
        return _metadata(saved['extraction'], saved['sheet'])

    def validate_empty_return_family(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        versions = set()
        for row in self.store.db.execute(f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)):
            outcome = json.loads(row['outcome'])
            if outcome.get('status') == 'completed':
                source = self.store.get(outcome['result']['sheet_ref'])
                if source.get('provider') == self.provider:
                    versions.add(source.get('version'))
        if self.record_version not in versions and versions & {'literature_reaction_record_v2', MEANINGS_RECORD_VERSION}:
            raise ContractError('literature_reaction_projection_version_mismatch')

    def _provenance(self, context, reference):
        if not self.store.reference_subset([reference], plain(context.scope)):
            raise ContractError('literature_source_outside_scope')
        row = self.store.get(reference)
        if row['record_type'] != 'source':
            raise ContractError('literature_source_required')
        return row

    def _source(self, context, reference):
        if reference not in context.received_record_refs:
            raise ContractError('literature_source_not_received')
        source = self._provenance(context, reference)
        page = context.assignment if context.role == 'literature_page' else context.assignment.get('page')
        if page:
            pending, seen = ([reference], set())
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                ancestor = self._provenance(context, current)
                if current == page['source_ref']:
                    break
                pending.extend(ancestor.get('parent_source_refs', ()))
            else:
                raise ContractError('literature_reading_outside_assigned_source')
        return source
    populate = populate

    def read(self, sheet_ref):
        if self.record_version != MEANINGS_RECORD_VERSION and self.store.get(sheet_ref).get('version') == MEANINGS_RECORD_VERSION:
            return self.semantic_projection().read(sheet_ref)
        saved = self._read_sheet(sheet_ref)
        source = self.store.get(sheet_ref)
        request = json.loads(self.store.get_artifact(source['request_ref']))
        args, extraction = (request['arguments'], saved['extraction'])
        operation = self.store.db.execute(f'SELECT signature FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?', (self.run_id, request['episode_id'], request['operation_key'])).fetchone()
        if source['version'] != self.record_version or operation['signature'] != canonical({'arguments': args, 'scope': request['scope']}) or saved['direct_input_source_refs'] != reaction_direct_references(extraction, _direct_references(args)) or (set(extraction['sources']) != set(saved['direct_input_source_refs'])) or (self.store.get(saved['input_source_ref'])['artifact_ref'] != saved['input_artifact_ref']) or (saved['data_source_ref'] != args['data_source_ref']) or (extraction['arguments'] != args) or (saved['sheet']['inputs'] != extraction['calculation_inputs']):
            raise ContractError('literature_reaction_sheet_source_mismatch')
        if 'native_evidence' in extraction:
            from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_native_inputs import TRACE_VERSION
            if extraction['native_evidence'].get('version') != TRACE_VERSION:
                raise ContractError('literature_reaction_native_saved_mismatch')

            def witnessed(value):
                if isinstance(value, dict):
                    if set(value) == {'source_ref', 'representation', 'start', 'end', 'quote', 'artifact_ref'}:
                        yield value
                    else:
                        for child in value.values():
                            yield from witnessed(child)
                elif isinstance(value, list):
                    for child in value:
                        yield from witnessed(child)
            for witness in witnessed(extraction['native_evidence']):
                row = self.store.get(witness['source_ref'])
                artifact = row['artifact_ref'] if witness['representation'] == 'original' else row.get('text_ref')
                if artifact != witness['artifact_ref'] or witness['source_ref'] not in saved['direct_input_source_refs']:
                    raise ContractError('literature_reaction_native_source_mismatch')
        assessments.validate_saved_assessment(self, saved, request)
        return saved

    def current_assessments(self):
        return assessments.current_assessments(self)

    def assessment_history(self, sheet_ref):
        return assessments.assessment_history(self, sheet_ref)

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        components = self.components if components is None else components
        if not isinstance(components, (list, tuple)) or any((not isinstance(name, str) or name not in self.components for name in components)) or len(set(components)) != len(components):
            raise ContractError('literature_reaction_component_selection_invalid')
        rows = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError('literature_sheet_not_received')
            saved = self.read(reference)
            if saved['version'] != self.record_version:
                raise ContractError('literature_reaction_projection_version_mismatch')
            for name in components:
                cell = {key: deepcopy(value) for key, value in saved['sheet']['cells'][name].items() if key != 'formula'}
                rows.append({'sheet_ref': reference, 'evidence_source_ref': saved['input_source_ref'], 'data_source_ref': saved['data_source_ref'], **saved['experimental_bindings'], 'component': name, **cell, 'formula_code': FORMULA_CODES[name], **self._row_metadata(saved)})
        validate_schema(rows, self.cells_schema())
        return rows

    def validate_returned_values(self, cells, *, permitted_record_refs):
        validate_schema(cells, self.cells_schema())
        self._validate_returned_values(cells, permitted_record_refs=permitted_record_refs)

class LiteratureReactionSemanticProjection(LiteratureReactionRepository):
    """Independent receipt of the named view, with no new operation or sheet."""
    record_version = MEANINGS_RECORD_VERSION
    received_table = 'literature_reaction_semantic_received'

    def __init__(self, store, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('explicit_literature_run_required')
        self.store, self.run_id = (store, run_id)

    def populate(self, context, arguments, operation_key):
        raise ContractError('reaction_semantic_return_view_cannot_publish')

    def cells_schema(self):
        return reaction_semantic_cells_schema()

    def _row_metadata(self, saved):
        return semantic_metadata(_metadata(saved['extraction'], saved['sheet']), saved['semantic_bindings'], saved['extraction']['calculation_inputs'], saved['sheet'])

    def read(self, sheet_ref):
        saved = super().read(sheet_ref)
        source = self.store.get(sheet_ref)
        request = json.loads(self.store.get_artifact(source['request_ref']))
        operation = self.store.db.execute(f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?', (self.run_id, request['episode_id'], request['operation_key'])).fetchone()
        outcome = json.loads(operation['outcome'])
        import hashlib
        payload = self.store.get_artifact(source['artifact_ref'])
        if 'artifact_' + hashlib.sha256(payload).hexdigest() != source['artifact_ref'] or saved['extraction'].get('version') != MEANINGS_INPUT_VERSION or saved['sheet']['cells'] != outcome['result']['cells'] or any((outcome['result'].get(key) != value for key, value in self._row_metadata(saved).items())):
            raise ContractError('literature_reaction_semantic_saved_mismatch')

        def validate_published(kind, record):
            expected = identity(kind, {'origin': 'tool', 'record': record})
            actual = self.store.get(expected)
            if actual != {'id': expected, 'record_type': kind, 'origin': 'tool', **record}:
                raise ContractError('literature_reaction_semantic_binding_mismatch')
            return expected
        expected_bindings = publish_meanings(saved['extraction'], validate_published)
        if expected_bindings != saved['semantic_bindings']:
            raise ContractError('literature_reaction_semantic_binding_mismatch')
        return saved

    def _installed(self):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (self.received_table,)).fetchone() is not None

    def received_cells(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        return super().received_cells(context) if self._installed() else []

    def receive_cells(self, context, cells, operation_key):
        with self.store.transaction():
            self.store.db.execute(f'CREATE TABLE IF NOT EXISTS {self.received_table}(\n                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, operation_key TEXT NOT NULL,\n                cells TEXT NOT NULL, PRIMARY KEY(run_id,episode_id,operation_key))')
            return super().receive_cells(context, cells, operation_key)
__all__ = ['LiteratureReactionRepository', 'LiteratureReactionSemanticProjection', 'COMPONENTS', 'PROVIDER', 'reaction_population_schema', 'reaction_cells_schema', 'reaction_semantic_cells_schema']
