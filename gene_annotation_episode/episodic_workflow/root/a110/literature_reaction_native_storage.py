"""Independently requested native A110 observations over one saved sheet.

Native observations are source operands, not scoring components. Aggregate-only
forms never acquire them. Saved projection reads no scientific source bytes.
"""
from copy import deepcopy
import json
from .domain import ContractError, canonical, identity, obj, validate_schema
from gene_annotation_episode.episodic_workflow.root.a110.literature_reaction_storage import LiteratureReactionSemanticProjection
from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_population_contracts import BINDINGS
from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_native_inputs import RATIO_BASES, COUNT_BASES, UNCERTAINTY_KINDS, TRACE_VERSION
from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_meanings import _witness_label
from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_native_observations import NAMESPACE, POSITIONS_FIELD, native_observations_schema, native_row_references, positions_schema, publish_native_observations

class LiteratureReactionNativeObservations(LiteratureReactionSemanticProjection):
    received_table = 'literature_reaction_native_observations_received'

    def read(self, sheet_ref):
        saved = super().read(sheet_ref)
        if saved['extraction'].get('native_evidence', {}).get('version') != TRACE_VERSION or 'native_observations' not in saved:
            raise ContractError('literature_reaction_native_observations_unavailable')
        source = self.store.get(sheet_ref)
        request = json.loads(self.store.get_artifact(source['request_ref']))
        operation = self.store.db.execute(f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?', (self.run_id, request['episode_id'], request['operation_key'])).fetchone()
        outcome = json.loads(operation['outcome'])
        if outcome['result'].get('native_observations') != saved['native_observations']:
            raise ContractError('literature_reaction_native_saved_mismatch')
        return saved

    def _positions(self, positions):
        if not isinstance(positions, (tuple, list)) or any((type(p) not in (str, int) for p in positions)):
            raise ContractError('reaction_native_positions_invalid')
        if len(set(positions)) != len(positions) or ('all' in positions and tuple(positions) != ('all',)):
            raise ContractError('reaction_native_positions_invalid')
        if any((p != 'all' and (type(p) is not int or p < 0) for p in positions)):
            raise ContractError('reaction_native_positions_invalid')
        return tuple(positions)

    def project_rows(self, sheet_refs, *, permitted_record_refs, positions=('all',)):
        positions = self._positions(positions)
        result = []
        for sheet_ref in dict.fromkeys(sheet_refs):
            if sheet_ref not in permitted_record_refs:
                raise ContractError('literature_sheet_not_received')
            rows = self.read(sheet_ref)['native_observations']
            if positions != ('all',) and any((p >= len(rows) for p in positions)):
                raise ContractError('reaction_native_position_unavailable')
            result.extend(({'sheet_ref': sheet_ref, **deepcopy(row)} for row in rows if positions == ('all',) or row['observation_position'] in positions))
        validate_schema(result, native_observations_schema())
        return result

    def validate_returned_values(self, rows, *, permitted_record_refs):
        validate_schema(rows, native_observations_schema())
        seen = set()
        for row in rows:
            key = (row['sheet_ref'], row['observation_position'])
            if key in seen:
                raise ContractError('duplicate_reaction_native_observation')
            seen.add(key)
            expected = self.project_rows([key[0]], permitted_record_refs=permitted_record_refs, positions=[key[1]])
            if len(expected) != 1 or canonical(row) != canonical(expected[0]):
                raise ContractError('reaction_native_return_differs_from_saved')

    def fact_rows(self, context, sheet_refs, *, positions=('all',)):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        positions = self._positions(positions)
        received, result = (None, [])
        for sheet_ref in dict.fromkeys(sheet_refs):
            if sheet_ref not in context.received_record_refs:
                raise ContractError('literature_sheet_not_received')
            self.project_rows([sheet_ref], permitted_record_refs=context.received_record_refs, positions=[])
            if self._sheet_origin_episode(sheet_ref) == context.episode_id:
                result.extend(self.project_rows([sheet_ref], permitted_record_refs=context.received_record_refs, positions=positions))
            else:
                if received is None:
                    received = self.received_rows(context)
                result.extend((deepcopy(row) for row in received if row['sheet_ref'] == sheet_ref and (positions == ('all',) or row['observation_position'] in positions)))
        return result

    def validate_fact_rows(self, context, rows):
        self.validate_returned_values(rows, permitted_record_refs=context.received_record_refs)
        expected = {(row['sheet_ref'], row['observation_position']): row for row in self.fact_rows(context, list(dict.fromkeys((row['sheet_ref'] for row in rows))), positions=list(dict.fromkeys((row['observation_position'] for row in rows))))}
        if any((canonical(row) != canonical(expected.get((row['sheet_ref'], row['observation_position']))) for row in rows)):
            raise ContractError('reaction_native_observation_not_received')

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
                if selected.get('kind') != 'redeliver_report' or prior is None or attempt['delivery_ref'] != selected.get('delivery_ref') or (prior['child_episode_id'] != attempt['child_episode_id']) or (canonical(json.loads(prior['contract'])) != canonical(original_contract)) or (selected.get('purpose') != contract['decision']) or (canonical(json.loads(selected['schema_json'])) != canonical(contract['measurements']['schema'])):
                    raise ContractError('literature_delivery_binding_mismatch')
            namespace = NAMESPACE
            fields = [name for name, node in contract['measurements']['schema']['properties'].items() if node.get('x-source') == namespace]
            if not fields:
                raise ContractError('literature_delivery_binding_mismatch')
            return [row for name in fields for row in form[name]]
        except (KeyError, TypeError, ValueError) as error:
            raise ContractError('literature_delivery_binding_mismatch') from error

    def _receive_rows(self, context, cells, operation_key):
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
                raise ContractError('literature_rate_delivery_identity_conflict')
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

    def _received_rows(self, context):
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
                key = (row['sheet_ref'], row['observation_position'])
                if key not in seen:
                    seen.add(key)
                    result.append(deepcopy(row))
        return result

    def receive_rows(self, context, rows, operation_key):
        with self.store.transaction():
            self.store.db.execute(f'CREATE TABLE IF NOT EXISTS {self.received_table}(\n                run_id TEXT NOT NULL,episode_id TEXT NOT NULL,operation_key TEXT NOT NULL,\n                cells TEXT NOT NULL,PRIMARY KEY(run_id,episode_id,operation_key))')
            return self._receive_rows(context, rows, operation_key)

    def received_rows(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        return self._received_rows(context) if self._installed() else []
