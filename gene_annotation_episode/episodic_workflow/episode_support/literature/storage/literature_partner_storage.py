"""Selected immutable partner sheets and exact typed receipt projection.

Custody validates retained source records; it does not establish the truth of
supplied experimental interpretations. Saved reads never reopen source bytes or
repeat calculation. Ordinary episode accounting belongs to the caller.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_partner_sheet_records import BINDINGS, CHECK_REASONS, COMPONENTS, ContractError, EXPERIMENT_TYPES, FORMULA_CODES, LITERAL_FIELDS, LITERAL_REFERENCE_ROLES_VERSION, LITERAL_REFERENCE_TYPES, NATIVE_UNITS, PROVIDER, REASONS, SOURCE_KINDS, _COMPONENT_ROLES, _FIXED_METADATA, _NATIVE_ARGUMENT_SCHEMA, _NATIVE_BINDING_VERSION, _NATIVE_EVIDENCE_SCHEMA, _NATIVE_EVIDENCE_V2_SCHEMA, _NATIVE_IDENTITY_FIELDS, _ROLES, _arguments_schema, _arm_metadata_schema, _binding_record, _cell_schema, _check_schema, _checks_schema, _condition_refs, _condition_role, _direct_references, _factor_names, _factor_record, _input_schema, _metadata, _native_evidence_schema, _native_operand_projection, _native_population_schema, _native_version, _saved_check, _spread_schema, assessments, canonical, deepcopy, hashlib, identity, json, literal_reference_role, obj, partner_cells_schema, partner_population_schema, partner_source_population_schema, plain, publication, read_partner_inputs, source_literal_label, unicodedata, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.literature_partner_sheet_population import populate as _populate_partner_sheet
from gene_annotation_episode.episodic_workflow.episode_support.literature.validation.literature_partner_saved_validation import _validate_native_saved as _science_validate_native_saved, _validate_saved as _science_validate_saved, _validate_scientific_saved as _science_validate_scientific_saved

class LiteraturePartnerRepository:
    experiment_types = EXPERIMENT_TYPES
    provider = PROVIDER
    components = COMPONENTS
    record_version = 'literature_partner_record_v1'
    operations_table = 'literature_partner_operations'
    received_table = 'literature_partner_received'
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

    def _read_sheet(self, sheet_ref):
        """Read an A107 partner sheet from its original selected operation."""
        source = self.store.get(sheet_ref)
        if source['record_type'] != 'source' or source['provider'] != self.provider or source['origin'] != 'tool' or (source['request_ref'] is None):
            raise ContractError('literature_partner_sheet_required')
        request = json.loads(self.store.get_artifact(source['request_ref']))
        if request.get('run_id') != self.run_id:
            raise ContractError('literature_partner_sheet_run_mismatch')
        operation = self.store.db.execute(f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?', (self.run_id, request.get('episode_id'), request.get('operation_key'))).fetchone()
        if operation is None or json.loads(operation['outcome']).get('result', {}).get('sheet_ref') != sheet_ref:
            raise ContractError('literature_partner_sheet_not_selected_output')
        payload = json.loads(self.store.get_artifact(source['artifact_ref']))
        if payload.get('version') != self.record_version or source.get('version') != self.record_version or source.get('parent_source_refs') != payload.get('input_source_refs', [payload['input_source_ref']]) or (request.get('arguments', {}).get('source_ref') != payload['input_source_ref']):
            raise ContractError('literature_partner_sheet_source_mismatch')
        return payload

    def validate_cells(self, cells, *, sheet_refs, permitted_record_refs, components=None):
        """Validate actual values and requested membership, beyond JSON syntax."""
        expected = self.project_cells(sheet_refs, permitted_record_refs=permitted_record_refs, components=components)
        if canonical(cells) != canonical(expected):
            raise ContractError('literature_partner_return_differs_from_saved_cells')

    def _validate_returned_values(self, cells, *, permitted_record_refs):
        """Check each actual returned cell without exposing unrequested cells."""
        seen = set()
        for row in cells:
            key = (row['sheet_ref'], row['component'])
            if key in seen:
                raise ContractError('duplicate_literature_partner_return_cell')
            seen.add(key)
            expected = self.project_cells([row['sheet_ref']], permitted_record_refs=permitted_record_refs, components=(row['component'],))
            if canonical(row) != canonical(expected[0]):
                raise ContractError('literature_partner_return_differs_from_saved_cells')

    def _sheet_origin_episode(self, reference):
        """Check the original selected episode, without reading scientific bytes."""
        self.read(reference)
        source = self.store.get(reference)
        record = {key: value for key, value in source.items() if key not in ('id', 'record_type', 'origin')}
        if identity('source', {'origin': 'tool', 'record': record}) != reference:
            raise ContractError('literature_partner_sheet_origin_mismatch')
        request_bytes = self.store.get_artifact(source['request_ref'])
        if 'artifact_' + hashlib.sha256(request_bytes).hexdigest() != source['request_ref']:
            raise ContractError('literature_partner_sheet_origin_mismatch')
        request = json.loads(request_bytes)
        if request.get('run_id') != self.run_id or type(request.get('episode_id')) is not str or (not request['episode_id']) or (type(request.get('operation_key')) is not str) or (not request['operation_key']):
            raise ContractError('literature_partner_sheet_origin_mismatch')
        operation = self.store.db.execute(f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?', (self.run_id, request['episode_id'], request['operation_key'])).fetchone()
        outcome = json.loads(operation['outcome']) if operation else {}
        if outcome.get('status') != 'completed' or outcome.get('result', {}).get('sheet_ref') != reference or reference not in outcome.get('record_refs', ()) or (outcome.get('operation_ref') != identity('operation', {'run_id': self.run_id, 'episode_id': request['episode_id'], 'key': request['operation_key']})):
            raise ContractError('literature_partner_sheet_origin_mismatch')
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
            self.validate_returned_values(cells, permitted_record_refs=[row['sheet_ref'] for row in cells])
            data = canonical(cells)
            old = self.store.db.execute(f'SELECT cells FROM {self.received_table} WHERE run_id=? AND episode_id=? AND operation_key=?', (self.run_id, context.episode_id, operation_key)).fetchone()
            if old is not None and old['cells'] != data:
                raise ContractError('literature_partner_delivery_identity_conflict')
            digest = self._delivery_digest(cells)
            bound = self._delivery_binding(context, operation_key)
            if bound is not None and bound[0] != digest:
                raise ContractError('literature_delivery_binding_mismatch')
            if old is not None and bound is None:
                raise ContractError('literature_delivery_binding_unavailable')
            self._install_delivery_bindings()
            self.store.db.execute(f'INSERT OR IGNORE INTO {self.received_table} VALUES(?,?,?,?)', (self.run_id, context.episode_id, operation_key, data))
            self.store.db.execute(f'INSERT OR IGNORE INTO {self._delivery_table} VALUES(?,?,?,?)', (self.run_id, context.episode_id, operation_key, digest))
            from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.partner_presence_evidence.literature_sheet_updates import admitted
            admitted(self, context, cells, operation_key)

    def _received_cells(self, context):
        """Forward copied admitted cells, not the complete private child sheet."""
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        result, seen = ([], set())
        rows = self.store.db.execute(f'SELECT operation_key,cells FROM {self.received_table} WHERE run_id=? AND episode_id=? ORDER BY rowid', (self.run_id, context.episode_id))
        for saved in rows:
            cells = json.loads(saved['cells'])
            bound = self._delivery_binding(context, saved['operation_key'])
            if bound is None:
                raise ContractError('literature_delivery_binding_unavailable')
            if bound[0] != self._delivery_digest(cells):
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
        role = literal_reference_role(self.store.get(value['experiment_ref']))
        if role in {'subject', 'partner'}:
            raise ContractError('literature_partner_experiment_identity_is_subject_or_partner_literal')
        if role is not None and role != 'experiment':
            raise ContractError('literature_partner_experiment_identity_is_condition_literal')

    def cells_schema(self):
        return partner_cells_schema()

    def received_cells(self, context):
        return self._received_cells(context)

    def _provenance(self, scope, reference):
        if not self.store.reference_subset([reference], plain(scope)):
            raise ContractError('literature_source_outside_scope')
        source = self.store.get(reference)
        if source['record_type'] != 'source':
            raise ContractError('literature_source_required')
        return source

    def _source(self, context, reference):
        if reference not in context.received_record_refs:
            raise ContractError('literature_source_not_received')
        source = self._provenance(context.scope, reference)
        page = context.assignment if context.role == 'literature_page' else context.assignment.get('page')
        if page:
            pending, seen = ([reference], set())
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                ancestor = self._provenance(context.scope, current)
                if current == page['source_ref']:
                    break
                pending.extend(ancestor.get('parent_source_refs', ()))
            else:
                raise ContractError('literature_reading_outside_assigned_source')
        return source

    def _parents(self, scope, direct):
        parents, seen = (list(direct), set(direct))
        cursor = 0
        while cursor < len(parents):
            source = self._provenance(scope, parents[cursor])
            cursor += 1
            for reference in source.get('parent_source_refs', ()):
                self._provenance(scope, reference)
                if reference not in seen:
                    seen.add(reference)
                    parents.append(reference)
        return parents

    def _replay(self, context, old, signature):
        if old['signature'] != signature:
            raise ContractError('operation_key_reused_for_different_work')
        outcome = json.loads(old['outcome'])
        saved = self.read(outcome['result']['sheet_ref'])
        for reference in saved['direct_input_source_refs']:
            self._source(context, reference)
        for reference in saved['input_source_refs']:
            self._provenance(context.scope, reference)
        if 'experiment_assessment' in saved:
            assessments.authorize_assessment(self, context, saved['experiment_assessment'])
        return outcome
    populate = _populate_partner_sheet

    def _assessment_sources(self, assessment):
        if assessment is None:
            return []
        return [self.store.get(assessment['experiment_ref'])['source_ref'], *([assessment['revises_sheet_ref']] if assessment['revises_sheet_ref'] is not None else [])]

    def current_assessments(self):
        return assessments.current_assessments(self)

    def assessment_history(self, sheet_ref):
        return assessments.assessment_history(self, sheet_ref)

    def read(self, sheet_ref):
        """Validate saved authority and copy cells, without source-byte reads."""
        saved = self._read_sheet(sheet_ref)
        try:
            self._validate_saved(sheet_ref, saved)
        except ContractError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise ContractError('literature_partner_sheet_source_mismatch') from error
        return saved
    _validate_saved = _science_validate_saved
    _validate_native_saved = _science_validate_native_saved
    _validate_scientific_saved = _science_validate_scientific_saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        components = self.components if components is None else components
        if not isinstance(components, (list, tuple)) or any((not isinstance(name, str) or name not in self.components for name in components)) or len(set(components)) != len(components):
            raise ContractError('literature_partner_component_selection_invalid')
        rows = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError('literature_sheet_not_received')
            saved = self.read(reference)
            for name in components:
                bindings = deepcopy(saved['experimental_bindings'])
                if 'native_operand_bindings' in saved:
                    bindings.update(saved['native_operand_bindings']['component_bindings'][name])
                rows.append({'sheet_ref': reference, 'evidence_source_ref': saved['input_source_ref'], 'data_source_ref': saved['data_source_ref'], **bindings, 'component': name, **deepcopy(saved['sheet']['cells'][name]), 'formula_code': FORMULA_CODES[name], **_metadata(saved['extraction'], saved['factor_bindings'])})
        validate_schema(rows, partner_cells_schema())
        return rows

    def validate_returned_values(self, cells, *, permitted_record_refs):
        validate_schema(cells, partner_cells_schema())
        self._validate_returned_values(cells, permitted_record_refs=permitted_record_refs)
__all__ = ['LiteraturePartnerRepository', 'COMPONENTS', 'PROVIDER', 'BINDINGS', 'FORMULA_CODES', 'partner_population_schema', 'partner_source_population_schema', 'partner_cells_schema']
