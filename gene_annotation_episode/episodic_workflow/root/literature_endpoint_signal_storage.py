"""Selected endpoint sections with scoped immutable scientific returns.

Only population reads original science and computes. Saved reads authenticate
original schemas, rows and selected ownership without reacquisition or fitting.
Constructors and discovery never install tables. No continuation policy lives here.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.domain import ContractError, canonical, identity, validate_schema
from .literature_rate_storage import LiteratureRateRepository

from .library.literature_endpoint_signal_contracts import PROVIDER

from gene_annotation_episode.episodic_workflow.root.library.literature_endpoint_signal_metadata import VERSION
from .library.literature_endpoint_signal_contracts import POPULATION

from gene_annotation_episode.episodic_workflow.root.library.literature_endpoint_signal_metadata import NAMESPACE, REQUESTED, VIEW, SCOPE
from .library.literature_endpoint_signal_contracts import COMPONENTS


# Exact detached v1 metadata literals are inserted below. No scientific/current
# schema factory is called when the registered form compiler checks this type.
from .library.literature_endpoint_signal_contracts import ENDPOINT_SIGNAL_CELLS_SCHEMA_V1

from .library.literature_endpoint_signal_contracts import ENDPOINT_SIGNAL_REQUEST_SCHEMA_V1

_PURE_HASHES = json.loads('{"literature_endpoint_signal_calculations.py":"48dfcd0473ad087e714067c868388bf54210a5069112d04e2d678ed9cda08340","literature_endpoint_signal_inputs.py":"5fcbb6d3393a278500038df3ef934895ef5d5443f2d9878c179dbe89ae9e015d","literature_endpoint_signal_prompt.py":"f4ebb4281b23b3ce334ad3eafdfe47ddfe15a43d00f331ab4d46e4c201b56477"}')


from .library.literature_endpoint_signal_contracts import endpoint_signal_cells_schema, endpoint_signal_operation_schema

from .library.literature_endpoint_signal_projection import _witnesses, _direct, _location, _context_projection, _project_once


class LiteratureEndpointSignalRepository(LiteratureRateRepository):
    provider, record_version, components = PROVIDER, VERSION, COMPONENTS
    operations_table = 'literature_endpoint_signal_operations'
    received_table = 'literature_endpoint_signal_received'
    binding_fields = ()

    def __init__(self, store, run_id):
        if type(run_id) is not str or not run_id:
            raise ValueError('explicit_literature_run_required')
        self.store, self.run_id = store, run_id

    def _installed(self, table):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

    def _install(self):
        super().__init__(self.store, self.run_id)

    @staticmethod
    def _components(values):
        if (not isinstance(values, (list, tuple)) or any(type(x) is not str or x not in COMPONENTS for x in values)
                or len(set(values)) != len(values)):
            raise ContractError('endpoint_component_selection_invalid')
        return list(values)

    def _ancestors(self, scope, references):
        result = list(dict.fromkeys(references))
        for ref in result:
            for parent in self._native_provenance(scope, ref).get('parent_source_refs', ()):
                if parent not in result:
                    result.append(parent)
        return result

    def _original_implementation(self):
        from .library.literature_endpoint_signal_source_receipt import current_receipt
        return current_receipt()

    def populate(self, context, arguments, operation_key):
        from .library.literature_endpoint_signal_inputs import (read_endpoint_signal_inputs,
            endpoint_signal_population_schema, endpoint_signal_extraction_schema)
        from .library.literature_endpoint_signal_calculations import populate_endpoint_signal, endpoint_signal_sheet_schema
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if type(operation_key) is not str or not operation_key:
            raise ContractError('operation_key_required')
        args = plain(arguments)
        validate_schema(args, ENDPOINT_SIGNAL_REQUEST_SCHEMA_V1)
        components = self._components(context.assignment.get(REQUESTED, []))
        if components != args['selection']['requested_cells']:
            raise ContractError('endpoint_assignment_request_roster_mismatch')
        request = {'run_id': self.run_id, 'episode_id': context.episode_id, 'role': context.role,
            'operation_key': operation_key, 'scope': plain(context.scope), 'assignment': plain(context.assignment),
            'received_record_refs': list(context.received_record_refs), 'arguments': args, 'components': components}
        signature = canonical(request)
        old = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, context.episode_id, operation_key)).fetchone() if self._installed(self.operations_table) else None
        if old:
            if old['signature'] != signature:
                raise ContractError('operation_key_reused_for_different_work')
            outcome = json.loads(old['outcome']); saved = self.read(outcome['result']['sheet_ref'])
            for reference in saved['direct_input_source_refs']:
                self._native_source(context, reference)
            return outcome
        for reference in _direct(args):
            self._native_source(context, reference)
        receipt = self._original_implementation()
        read_sizes, authorization_errors = {}, []
        def read_source(reference, representation):
            try:
                row = self._native_source(context, reference)
            except ContractError as error:
                authorization_errors.append(error); raise
            artifact = row['artifact_ref'] if representation == 'original' else row.get('text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            raw = self.store.get_artifact(artifact)
            if artifact != 'artifact_' + hashlib.sha256(raw).hexdigest():
                raise ContractError('endpoint_source_artifact_hash_mismatch')
            read_sizes[(reference, representation)] = len(raw)
            return {'artifact_ref': artifact, 'content': raw}
        extraction = read_endpoint_signal_inputs(args['selection'], read_source=read_source)
        if authorization_errors:
            raise authorization_errors[0]
        sheet = populate_endpoint_signal(extraction)
        direct = list(dict.fromkeys([*_direct(args), *(s['source_ref'] for s in extraction['source_artifacts'])]))
        for reference in direct:
            self._native_source(context, reference)
        parents = self._ancestors(context.scope, direct)
        templates = _project_once(args, extraction, sheet, parents, read_sizes)
        source = self._native_source(context, args['selection']['source_ref'])
        snapshots = {'request': deepcopy(ENDPOINT_SIGNAL_REQUEST_SCHEMA_V1),
            'selection': endpoint_signal_population_schema(), 'extraction': endpoint_signal_extraction_schema(),
            'sheet': endpoint_signal_sheet_schema(), 'rows': deepcopy(ENDPOINT_SIGNAL_CELLS_SCHEMA_V1)}
        payload = {'version': VERSION, 'input_source_ref': source['id'], 'input_artifact_ref': source['artifact_ref'],
            'direct_input_source_refs': direct, 'input_source_refs': parents,
            'source_metadata': {ref: self.store.get(ref) for ref in parents}, 'original_implementation': receipt,
            'original_schemas': snapshots, 'extraction': extraction, 'sheet': sheet, 'row_templates': templates}
        with self.store.transaction():
            self._install()
            artifact = self.store.artifact(canonical(payload), 'application/json')
            req_ref = self.store.artifact(canonical(request), 'application/json')
            record = {'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': artifact,
                'text_ref': artifact, 'request_ref': req_ref, 'version': VERSION, 'retrieved_at': None,
                'parent_source_refs': parents}
            ref = identity('source', {'origin': 'tool', 'record': record})
            exists = self.store.db.execute('SELECT 1 FROM records WHERE id=?', (ref,)).fetchone()
            self.store.put('source', record, origin='tool', scope=plain(context.scope))
            rows = [{'sheet_ref': ref, **deepcopy(row)} for row in templates]
            validate_schema(rows, snapshots['rows'])
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {'run_id': self.run_id,
                'episode_id': context.episode_id, 'key': operation_key}), 'record_refs': [ref],
                'changed_record_refs': [] if exists else [ref], 'result': {'sheet_ref': ref,
                    'view': VIEW, 'record_version': VERSION, 'cells': rows}, 'feedback': None}
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def _json(self, reference):
        raw = self.store.get_artifact(reference)
        if reference != 'artifact_' + hashlib.sha256(raw).hexdigest():
            raise ContractError('endpoint_saved_artifact_hash_mismatch')
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ContractError('endpoint_saved_object_required')
        return value

    def read(self, reference):
        try:
            return self._read(reference)
        except ContractError:
            raise
        except (KeyError, TypeError, ValueError, OverflowError, AttributeError) as error:
            raise ContractError('endpoint_saved_binding_mismatch') from error

    def _read(self, reference):
        def require(condition):
            if not condition:
                raise ContractError('endpoint_saved_binding_mismatch')
        source = self.store.get(reference)
        record = {k: v for k, v in source.items() if k not in ('id', 'origin', 'record_type')}
        require(source.get('record_type') == 'source' and source.get('origin') == 'tool'
            and source.get('provider') == PROVIDER and source.get('version') == VERSION
            and identity('source', {'origin': 'tool', 'record': record}) == reference)
        request, saved = self._json(source['request_ref']), self._json(source['artifact_ref'])
        require(set(request) == {'run_id', 'episode_id', 'role', 'operation_key', 'scope', 'assignment',
            'received_record_refs', 'arguments', 'components'} and request['run_id'] == self.run_id)
        require(set(saved) == {'version', 'input_source_ref', 'input_artifact_ref', 'direct_input_source_refs',
            'input_source_refs', 'source_metadata', 'original_implementation', 'original_schemas',
            'extraction', 'sheet', 'row_templates'})
        require(saved['version'] == VERSION and source['text_ref'] == source['artifact_ref'])
        require(self._installed(self.operations_table))
        operation = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, request['episode_id'], request['operation_key'])).fetchone()
        require(operation is not None and operation['signature'] == canonical(request))
        schemas = saved['original_schemas']
        require(set(schemas) == {'request', 'selection', 'extraction', 'sheet', 'rows'})
        require(schemas['request'] == ENDPOINT_SIGNAL_REQUEST_SCHEMA_V1
            and schemas['rows'] == ENDPOINT_SIGNAL_CELLS_SCHEMA_V1
            and schemas['selection'] == schemas['request']['properties']['selection']
            and schemas['extraction']['properties']['arguments'] == schemas['selection']
            and schemas['sheet']['properties']['input_snapshot'] == schemas['extraction'])
        args, extraction, sheet = request['arguments'], saved['extraction'], saved['sheet']
        validate_schema(args, schemas['request']); validate_schema(args['selection'], schemas['selection'])
        validate_schema(extraction, schemas['extraction']); validate_schema(sheet, schemas['sheet'])
        require(args['version'] == POPULATION and extraction['arguments'] == args['selection'])
        require(request['components'] == request['assignment'].get(REQUESTED, []) == args['selection']['requested_cells'])
        require(sheet['input_snapshot'] == extraction and sheet['requested_cells'] == request['components'])
        require([c['component'] for c in sheet['cells']] == request['components'])
        require(saved['input_source_ref'] == args['selection']['source_ref'] == extraction['source_ref'])
        direct = saved['direct_input_source_refs']
        require(direct == list(dict.fromkeys([*_direct(args), *(s['source_ref'] for s in extraction['source_artifacts'])])))
        require(all(ref in request['received_record_refs'] for ref in direct))
        require(saved['input_source_refs'] == source['parent_source_refs'] == self._ancestors(request['scope'], direct))
        require(set(saved['source_metadata']) == set(saved['input_source_refs']))
        for ref, metadata in saved['source_metadata'].items():
            require(canonical(self._native_provenance(request['scope'], ref)) == canonical(metadata))
        require(saved['input_artifact_ref'] == saved['source_metadata'][saved['input_source_ref']]['artifact_ref'])
        receipt = saved['original_implementation']
        if type(receipt) is dict and receipt.get('version') == 'endpoint_signal_root_implementation_v4':
            from .library.literature_endpoint_signal_source_receipt import retained_current_receipt
            require(retained_current_receipt(receipt))
        elif type(receipt) is dict and receipt.get('version') == 'endpoint_signal_root_implementation_v3':
            from .library.literature_endpoint_signal_source_receipt import retained_v3_receipt
            require(retained_v3_receipt(receipt))
        elif type(receipt) is dict and receipt.get('version') == 'endpoint_signal_root_implementation_v2':
            from .library.literature_endpoint_signal_source_receipt import retained_v2_receipt
            require(retained_v2_receipt(receipt))
        else:
            require(set(receipt) == {'version', 'files'} and receipt['version'] == 'endpoint_signal_original_implementation_v1'
                and all(receipt['files'].get(name) == digest for name, digest in _PURE_HASHES.items())
                and all(type(name) is str and type(digest) is str and len(digest) == 64
                    and all(c in '0123456789abcdef' for c in digest) for name, digest in receipt['files'].items()))
        templates = saved['row_templates']
        require(len(templates) == len(sheet['cells']))
        cell_fields = schemas['sheet']['properties']['cells']['items']['properties']
        for template, cell in zip(templates, sheet['cells']):
            require({k: template[k] for k in cell_fields} == cell)
            require(template['source_scope'] == saved['input_source_refs'] and template['evidence_source_ref'] == saved['input_source_ref'])
            for name, projected in template['source_context'].items():
                selected = args['return_context'][name]; actual = extraction['context'][name]
                require(projected['status'] == ('not_selected' if not selected else 'source_unavailable' if actual is None else 'selected'))
                require(len(projected['fragments']) == (len(selected) if actual else 0))
                for fragment, window in zip(projected['fragments'], selected):
                    witness = actual['witness']; loc = fragment['location']
                    require(loc == {**_location(witness), **window})
                    a, b = window['start']-witness['start'], window['end']-witness['start']
                    require(0 <= a < b <= len(witness['quote'].encode()) and fragment['text'].encode() == witness['quote'].encode()[a:b])
        rows = [{'sheet_ref': reference, **deepcopy(row)} for row in templates]
        validate_schema(rows, schemas['rows'])
        outcome = json.loads(operation['outcome'])
        require(outcome['status'] == 'completed' and outcome['feedback'] is None and outcome['record_refs'] == [reference])
        require(outcome['operation_ref'] == identity('operation', {'run_id': self.run_id, 'episode_id': request['episode_id'], 'key': request['operation_key']}))
        require(canonical(outcome['result']) == canonical({'sheet_ref': reference, 'view': VIEW, 'record_version': VERSION, 'cells': rows}))
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = None if components is None else self._components(components)
        result = []
        for ref in dict.fromkeys(sheet_refs):
            if ref not in permitted_record_refs:
                raise ContractError('literature_sheet_not_received')
            saved = self.read(ref)
            by_name = {row['component']: row for row in saved['row_templates']}
            result.extend({'sheet_ref': ref, **deepcopy(by_name[name])} for name in
                (list(by_name) if selected is None else selected) if name in by_name)
        return result

    def validate_returned_values(self, cells, *, permitted_record_refs):
        validate_schema(cells, ENDPOINT_SIGNAL_CELLS_SCHEMA_V1)
        seen = set()
        for row in cells:
            key = row['sheet_ref'], row['component']
            if key in seen:
                raise ContractError('duplicate_endpoint_return_cell')
            seen.add(key)
            expected = self.project_cells([row['sheet_ref']], permitted_record_refs=permitted_record_refs, components=[row['component']])
            if canonical(expected) != canonical([row]):
                raise ContractError('endpoint_return_differs_from_saved_cells')

    def fact_cells(self, context, sheet_refs, *, components):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        selected = self._components(components); result = []; received = None
        for ref in dict.fromkeys(sheet_refs):
            if ref not in context.received_record_refs:
                raise ContractError('literature_sheet_not_received')
            self._native_provenance(context.scope, ref)
            if self._sheet_owner(ref) == context.episode_id:
                result.extend(self.project_cells([ref], permitted_record_refs=context.received_record_refs, components=selected))
            else:
                if received is None:
                    received = {(row['sheet_ref'], row['component']): row for row in self.received_cells(context)}
                result.extend(deepcopy(received[ref, name]) for name in selected if (ref, name) in received)
        return result

    def received_cells(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        return super().received_cells(context) if self._installed(self.received_table) else []

    def receive_cells(self, context, cells, operation_key):
        if cells:
            with self.store.transaction():
                self._install(); return super().receive_cells(context, cells, operation_key)

    def selected_sheet_refs(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not self._installed(self.operations_table):
            return []
        refs = list(dict.fromkeys(json.loads(row['outcome'])['result']['sheet_ref'] for row in self.store.db.execute(
            f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? ORDER BY rowid', (self.run_id, context.episode_id))))
        for ref in refs:
            self.read(ref)
        return refs

    def available_sheet_refs(self, context):
        return list(dict.fromkeys([*(r for r in self.selected_sheet_refs(context) if r in context.received_record_refs),
            *(row['sheet_ref'] for row in self.received_cells(context) if row['sheet_ref'] in context.received_record_refs)]))

    def has_work(self, context):
        return bool(self.available_sheet_refs(context))

    def validate_empty_return_family(self, context):
        return None

    @staticmethod
    def cell_record_refs(cells):
        refs = []
        def visit(value):
            if isinstance(value, dict):
                for name, child in value.items():
                    if name.endswith('_ref') and isinstance(child, str) and child.startswith(('source_', 'artifact_')):
                        refs.append(child)
                    elif name in ('source_scope', 'withheld_image_source_refs'):
                        refs.extend(child)
                    else:
                        visit(child)
            elif isinstance(value, (list, tuple)):
                for child in value:
                    visit(child)
        visit(cells)
        return list(dict.fromkeys(refs))

    def receipt_bindings(self):
        """Host-only selected identity/artifact ownership; never installs state."""
        result = {}
        if not self._installed(self.operations_table):
            return result
        for row in self.store.db.execute(f'SELECT outcome FROM {self.operations_table} WHERE run_id=?', (self.run_id,)):
            ref = json.loads(row['outcome'])['result']['sheet_ref']
            source = self.store.get(ref); owner = self._sheet_owner(ref)
            result[ref] = {'run_id': self.run_id, 'episode_id': owner,
                'artifacts': [source['artifact_ref'], source['request_ref']]}
        return result

    def _private_binding(self, source_ref, artifact=None):
        bindings = self.receipt_bindings()
        if source_ref in bindings:
            return bindings[source_ref]
        for binding in bindings.values():
            if artifact in binding['artifacts']:
                return binding
        source = self.store.get(source_ref) if source_ref is not None else {}
        if source.get('provider') == PROVIDER and source.get('version') == VERSION:
            raise ContractError('literature_endpoint_receipt_binding_invalid')
        return None

    def authorize_source_access(self, context, source_ref, representation, tool_name):
        source = self.store.get(source_ref)
        if source.get('record_type') != 'source':
            # Leave ordinary wrong-kind diagnostics to the selected source tool.
            return
        artifact = (source.get('text_ref') or source['artifact_ref']) if representation == 'text' and tool_name == 'source.read' else (
            source['artifact_ref'] if representation == 'original' else source.get(representation+'_ref'))
        binding = self._private_binding(source_ref, artifact)
        if binding and (binding['run_id'], binding['episode_id']) != (context.run_id, context.episode_id):
            raise ContractError('literature_endpoint_receipt_private')

    def authorize_record_access(self, context, record):
        if record.get('record_type') in {'source', 'artifact'}:
            return
        for anchor in (record, record.get('anchor'), record.get('visual_anchor')):
            if not isinstance(anchor, dict):
                continue
            binding = self._private_binding(anchor.get('source_ref'), anchor.get('artifact_ref'))
            if binding and (binding['run_id'], binding['episode_id']) != (context.run_id, context.episode_id):
                raise ContractError('literature_endpoint_receipt_private')


__all__ = ['LiteratureEndpointSignalRepository', 'ENDPOINT_SIGNAL_CELLS_SCHEMA_V1',
    'endpoint_signal_cells_schema', 'endpoint_signal_operation_schema', 'PROVIDER', 'VERSION',
    'POPULATION', 'NAMESPACE', 'REQUESTED', 'VIEW', 'SCOPE', 'COMPONENTS']
