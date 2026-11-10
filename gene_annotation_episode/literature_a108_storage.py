"""A105-style immutable numerical-sheet custody for A108's distinct science.

Only the two population adapters read inputs and invoke their calculations.
Reading a committed sheet authenticates saved values and receipts; it does not
repeat scientific interpretation or expose unrequested child components.
"""
from copy import deepcopy
from hashlib import sha256
import json

from .communication import plain
from .domain import ContractError, canonical, identity, validate_schema
from .literature_rate_storage import LiteratureRateRepository


class A108SheetRepository(LiteratureRateRepository):
    binding_fields = ()

    def __init__(self, store, run_id, *, read_cells=None):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('explicit_literature_run_required')
        self.store, self.run_id, self._read_cells = store, run_id, read_cells

    def _installed(self, table):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

    def _install(self):
        super().__init__(self.store, self.run_id)

    def _record(self, context, ref, kind=None):
        if ref not in context.received_record_refs:
            raise ContractError('a108_record_not_received')
        if not self.store.reference_subset([ref], plain(context.scope)):
            raise ContractError('a108_record_outside_scope')
        record = self.store.get(ref)
        if kind is not None and record['record_type'] != kind:
            raise ContractError('a108_record_type_mismatch')
        return record

    def _components(self, selected):
        if (not isinstance(selected, (list, tuple)) or len(set(selected)) != len(selected)
                or any(name not in self.components for name in selected)):
            raise ContractError('a108_component_selection_invalid')
        return list(selected)

    def _artifact_json(self, ref):
        raw = self.store.get_artifact(ref)
        if ref != 'artifact_' + sha256(raw).hexdigest():
            raise ContractError('a108_saved_artifact_hash_mismatch')
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, ValueError) as error:
            raise ContractError('a108_saved_json_required') from error
        if not isinstance(value, dict):
            raise ContractError('a108_saved_object_required')
        return value

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        args = plain(arguments)
        validate_schema(args, self.population_schema())
        requested = self._components(context.assignment.get(self.requested, ()))
        request = {'run_id': self.run_id, 'episode_id': context.episode_id,
            'operation_key': operation_key, 'arguments': args, 'scope': plain(context.scope),
            'requested_components': requested}
        signature = canonical(request)
        old = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} '
            'WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, context.episode_id, operation_key)).fetchone() if self._installed(self.operations_table) else None
        if old:
            if old['signature'] != signature:
                raise ContractError('operation_key_reused_for_different_work')
            outcome = json.loads(old['outcome'])
            saved = self.read(outcome['result']['sheet_ref'])
            for ref in saved['direct_record_refs']:
                self._record(context, ref)
            return outcome

        direct, bindings, artifacts, reader_records = [], {}, {}, []
        def retain(record, possessed=False):
            ref = record['id']
            bindings[ref] = identity('a108_input_record', record)
            if possessed and ref not in direct:
                direct.append(ref)
            return record
        def read_record(ref):
            return retain(self._record(context, ref), True)
        def read_source(ref, representation):
            source = retain(self._native_source(context, ref), True)
            # External sources remain readable. Saved A108 computations are
            # delivered through selected components, not source-byte aliases.
            self.authorize_source_access(context, ref, representation, 'source.read')
            other = self.peer_repository()
            if other is not None:
                other.authorize_source_access(context, ref, representation, 'source.read')
            artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
            if artifact is None:
                raise ContractError('a108_source_representation_unavailable')
            content = self.store.get_artifact(artifact)
            if artifact != 'artifact_' + sha256(content).hexdigest():
                raise ContractError('a108_source_artifact_hash_mismatch')
            artifacts[(ref, representation)] = artifact
            return {'artifact_ref': artifact, 'content': content}
        extraction = self.read_inputs(context, args, read_record=read_record,
            read_source=read_source, retain_selection=reader_records.append)
        validate_schema(extraction, self.input_schema())
        calculation_context = self.calculation_context(context, args, extraction)
        sheet = (self.calculate(args, extraction) if calculation_context is None else
            self.calculate_current(args, extraction, calculation_context))
        validate_schema(sheet, self.sheet_schema())
        sources = []
        for ref in list(bindings):
            record = self.store.get(ref)
            source = ref if record['record_type'] == 'source' else record.get('source_ref')
            if source is not None and source not in sources:
                sources.append(source)
        # Source metadata closure is retained without acquiring private source
        # bytes or widening a delivered numerical subset.
        for ref in sources:
            source = retain(self._native_provenance(context.scope, ref))
            for ancestor in source.get('parent_source_refs', ()):
                if ancestor not in sources:
                    sources.append(ancestor)
        payload = {'version': self.record_version, 'selection': args,
            'extraction': extraction, 'sheet': sheet, 'reader_records': reader_records,
            'direct_record_refs': direct, 'input_source_refs': sources,
            'record_bindings': bindings,
            'artifact_bindings': [{'source_ref': ref, 'representation': representation, 'artifact_ref': artifact}
                for (ref, representation), artifact in artifacts.items()]}
        if calculation_context is not None:
            payload['calculation_context'] = calculation_context
        with self.store.transaction():
            self._install()
            artifact = self.store.artifact(canonical(payload), 'application/json')
            request_ref = self.store.artifact(signature, 'application/json')
            record = {'provider': self.provider, 'accession': None, 'uri': None,
                'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request_ref,
                'version': self.record_version, 'retrieved_at': None, 'parent_source_refs': sources}
            sheet_ref = identity('source', {'origin': 'tool', 'record': record})
            exists = self.store.db.execute('SELECT 1 FROM records WHERE id=?', (sheet_ref,)).fetchone()
            self.store.put('source', record, origin='tool', scope=plain(context.scope))
            rows = self.rows(payload, sheet_ref, requested)
            validate_schema(rows, self.cells_schema())
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {
                'run_id': self.run_id, 'episode_id': context.episode_id, 'key': operation_key}),
                'record_refs': [sheet_ref], 'changed_record_refs': [] if exists else [sheet_ref],
                'result': {'sheet_ref': sheet_ref, 'cells': rows}, 'feedback': None}
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def peer_repository(self):
        return None

    def calculation_context(self, context, arguments, extraction):
        return None

    def read(self, sheet_ref):
        source = self.store.get(sheet_ref)
        if (source.get('record_type') != 'source' or source.get('origin') != 'tool'
                or source.get('provider') != self.provider or source.get('version') != self.record_version):
            raise ContractError('a108_saved_sheet_required')
        record = {key: value for key, value in source.items() if key not in ('id', 'record_type', 'origin')}
        if identity('source', {'origin': 'tool', 'record': record}) != sheet_ref:
            raise ContractError('a108_saved_identity_mismatch')
        request = self._artifact_json(source['request_ref'])
        if (set(request) != {'run_id', 'episode_id', 'operation_key', 'arguments', 'scope', 'requested_components'}
                or request['run_id'] != self.run_id):
            raise ContractError('a108_saved_request_mismatch')
        scope = self.store.validate_scope(request['scope'])
        self._native_provenance(scope, sheet_ref)
        operation = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} '
            'WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, request['episode_id'], request['operation_key'])).fetchone() if self._installed(self.operations_table) else None
        if operation is None or operation['signature'] != canonical(request):
            raise ContractError('a108_saved_operation_mismatch')
        saved = self._artifact_json(source['artifact_ref'])
        outcome = json.loads(operation['outcome'])
        if (set(saved) - {'calculation_context'} != {'version', 'selection', 'extraction', 'sheet', 'reader_records',
                'direct_record_refs', 'input_source_refs', 'record_bindings', 'artifact_bindings'}
                or saved['version'] != self.record_version or saved['selection'] != request['arguments']
                or saved['input_source_refs'] != source['parent_source_refs']
                or outcome.get('status') != 'completed' or outcome.get('result', {}).get('sheet_ref') != sheet_ref
                or outcome.get('record_refs') != [sheet_ref]
                or outcome.get('operation_ref') != identity('operation', {'run_id': self.run_id,
                    'episode_id': request['episode_id'], 'key': request['operation_key']})):
            raise ContractError('a108_saved_selection_mismatch')
        validate_schema(saved['selection'], self.population_schema())
        validate_schema(saved['extraction'], self.input_schema())
        validate_schema(saved['sheet'], self.sheet_schema())
        if not set(saved['direct_record_refs']) <= set(saved['record_bindings']):
            raise ContractError('a108_saved_input_mismatch')
        for ref, digest in saved['record_bindings'].items():
            if (not self.store.reference_subset([ref], plain(scope))
                    or identity('a108_input_record', self.store.get(ref)) != digest):
                raise ContractError('a108_saved_input_mismatch')
        for binding in saved['artifact_bindings']:
            field = {'original': 'artifact_ref', 'text': 'text_ref'}[binding['representation']]
            if self.store.get(binding['source_ref']).get(field) != binding['artifact_ref']:
                raise ContractError('a108_saved_input_artifact_mismatch')
        self.validate_saved_inputs(saved)
        rows = self.rows(saved, sheet_ref, self._components(request['requested_components']))
        validate_schema(rows, self.cells_schema())
        if canonical(rows) != canonical(outcome['result']['cells']):
            raise ContractError('a108_saved_cells_mismatch')
        return saved

    def validate_saved_inputs(self, saved):
        """Optional structural provenance checks, without scientific recomputation."""

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = self._components(self.components if components is None else components)
        rows = []
        for ref in dict.fromkeys(sheet_refs):
            if ref not in permitted_record_refs:
                raise ContractError('literature_sheet_not_received')
            rows.extend(self.rows(self.read(ref), ref, selected))
        return rows

    def selected_sheet_refs(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not self._installed(self.operations_table):
            return []
        rows = self.store.db.execute(f'SELECT outcome FROM {self.operations_table} '
            'WHERE run_id=? AND episode_id=? ORDER BY rowid', (self.run_id, context.episode_id))
        return list(dict.fromkeys(json.loads(row['outcome'])['result']['sheet_ref'] for row in rows))

    def available_sheet_refs(self, context):
        refs = []
        for ref in context.received_record_refs:
            record = self.store.get(ref)
            if record.get('provider') == self.provider and record.get('version') == self.record_version:
                self.read(ref)
                refs.append(ref)
        return list(dict.fromkeys(refs))

    def received_cells(self, context):
        return super().received_cells(context) if self._installed(self.received_table) else []

    def receive_cells(self, context, cells, operation_key):
        with self.store.transaction():
            self._install()
            return super().receive_cells(context, cells, operation_key)

    def _private_binding(self, source_ref, artifact_ref):
        if not self._installed(self.operations_table):
            return None
        for row in self.store.db.execute(f'SELECT run_id,episode_id,outcome FROM {self.operations_table}'):
            outcome = json.loads(row['outcome'])
            ref = outcome.get('result', {}).get('sheet_ref')
            if ref is None:
                continue
            source = self.store.get(ref)
            if source_ref == ref or artifact_ref is not None and artifact_ref in {
                    source.get('artifact_ref'), source.get('text_ref'), source.get('request_ref')}:
                return row['run_id'], row['episode_id']
        return None

    def authorize_source_access(self, context, source_ref, representation, tool_name):
        source = self.store.get(source_ref)
        if source.get('record_type') != 'source':
            return
        field = 'artifact_ref' if representation == 'original' else 'text_ref' if representation == 'text' else representation + '_ref'
        artifact = source.get(field)
        if representation == 'text' and tool_name == 'source.read':
            artifact = artifact or source.get('artifact_ref')
        owner = self._private_binding(source_ref, artifact)
        if owner is not None and owner != (context.run_id, context.episode_id):
            raise ContractError('a108_selected_components_required_for_nonowner')

    def authorize_record_access(self, context, record):
        if record.get('record_type') in {'source', 'artifact'}:
            return
        for anchor in (record, record.get('anchor'), record.get('visual_anchor')):
            if isinstance(anchor, dict):
                owner = self._private_binding(anchor.get('source_ref'), anchor.get('artifact_ref'))
                if owner is not None and owner != (context.run_id, context.episode_id):
                    raise ContractError('a108_selected_components_required_for_nonowner')

    @staticmethod
    def cell_record_refs(cells):
        refs = []
        def collect(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key.endswith('_ref') and isinstance(item, str):
                        refs.append(item)
                    elif key.endswith('_refs') and isinstance(item, list):
                        refs.extend(ref for ref in item if isinstance(ref, str))
                    else:
                        collect(item)
            elif isinstance(value, list):
                for item in value:
                    collect(item)
        collect(cells)
        return list(dict.fromkeys(refs))


__all__ = ['A108SheetRepository']
