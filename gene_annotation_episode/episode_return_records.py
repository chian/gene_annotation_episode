"""Proof of original immediate-child typed returns from existing runtime records.

This validates ownership and exact saved values. It does not retrieve science,
choose work, create a new journal, or create observations or credit.
"""
from __future__ import annotations

import json
import math
import re

from method_loop.identities import EpisodeRef

from .communication import plain
from .episode_bindings import BindingContext


def _normalized_same(left, right):
    def equal(a, b):
        if type(a) is not type(b):
            return False
        if a is None or type(a) in (str, int, bool):
            return a == b
        if type(a) is float:
            return math.isfinite(a) and math.isfinite(b) and a == b
        if type(a) is dict:
            return (all(type(key) is str for key in a)
                and all(type(key) is str for key in b)
                and a.keys() == b.keys() and all(equal(a[key], b[key]) for key in a))
        if type(a) is list:
            return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
        return False
    return equal(plain(left), plain(right))


def _same(left, right):
    """Compare ordinary normalized trees directly, preserving the old fallback.

    Custom containers (including proxies over arbitrary mappings) retain the
    original eager normalization. A mismatch also takes that path so an invalid
    unvisited tail cannot hide a normalization error. No identity shortcuts or
    successful authority verdicts are retained.
    """
    def equal(a, b, depth):
        if depth > 64:
            return False  # Preserve the original recursion/error behavior.
        ta, tb = type(a), type(b)
        if ta in (list, tuple) and tb in (list, tuple):
            return len(a) == len(b) and all(equal(x, y, depth + 1) for x, y in zip(a, b))
        if ta is not tb:
            return False
        if a is None or ta in (str, int, bool):
            return a == b
        if ta is float:
            return math.isfinite(a) and math.isfinite(b) and a == b
        if ta is dict:
            return (all(type(key) is str for key in a)
                and all(type(key) is str for key in b)
                and a.keys() == b.keys()
                and all(equal(a[key], b[key], depth + 1) for key in a))
        return False
    try:
        if equal(left, right, 0):
            return True
    except RecursionError:
        pass
    return _normalized_same(left, right)


class EpisodeReturnRecords:
    _equal = staticmethod(_same)

    def __init__(self, store, run_id, *, failure_prefix):
        self.store, self.db, self.run_id = store, store.db, run_id
        self.failure_prefix = failure_prefix

    def _require(self, condition, code):
        if not condition:
            raise ValueError(self.failure_prefix + code)

    def authenticate(self, context, *, allow_unsaved=False):
        request = plain(context.request)
        message = request.get('message', {})
        self._require(context.run_id == self.run_id
            and EpisodeRef(self.run_id, context.path).episode_id == context.episode_id
            and self._equal(message.get('scope'), context.scope)
            and self._equal(message.get('episode_assignment', {}), context.assignment), 'context_conflict')
        row = self.db.execute('SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id, context.episode_id)).fetchone()
        self._require(row is not None or allow_unsaved, 'saved_context_required')
        if row is not None:
            self._require(self._equal(json.loads(row['path']), context.path)
                and self._equal(json.loads(row['request']), request), 'original_context_conflict')
        return context

    def context(self, episode_id):
        row = self.db.execute('SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id, episode_id)).fetchone()
        self._require(row is not None, 'saved_context_required')
        path, request = json.loads(row['path']), json.loads(row['request'])
        message = request['message']
        result = BindingContext(self.run_id, episode_id, path[-1][0], tuple(map(tuple, path)),
            message['scope'], message.get('episode_assignment', {}), request)
        return self.authenticate(result)

    def _received_before(self, episode_id, reference, decision_index):
        current, through, seen = episode_id, None, set()
        while current is not None:
            self._require(current not in seen, 'receipt_lineage_cycle')
            seen.add(current)
            manifest = self.db.execute('SELECT parent_episode_id,through_receipt_index '
                'FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?',
                (self.run_id, current)).fetchone()
            self._require(manifest is not None, 'receipt_history_unbound')
            row = self.db.execute('SELECT receipt_index,receipt_kind,source_index FROM runtime_record_receipts '
                'WHERE run_id=? AND episode_id=? AND record_ref=?', (self.run_id, current, reference)).fetchone()
            if row is not None and (through is None or row['receipt_index'] <= through):
                if current != episode_id or row['receipt_kind'] == 'initial':
                    return True
                index = row['source_index']
                if type(index) is int and (index <= decision_index if row['receipt_kind'] == 'decision_input'
                                           else index < decision_index):
                    return True
            current, through = manifest['parent_episode_id'], manifest['through_receipt_index']
        return False

    def _attempt(self, context, index):
        self.authenticate(context)
        row = self.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? '
            'AND decision_index=?', (self.run_id, context.episode_id, index)).fetchone()
        self._require(row is not None and row['form'] is not None and row['failure'] is None, 'successful_return_required')
        child = self.context(row['child_episode_id'])
        contract, form = json.loads(row['contract']), json.loads(row['form'])
        self._require(child.path[:-1] == context.path, 'return_child_contract_conflict')
        schema = contract.get('measurements', {}).get('schema')
        self._require(isinstance(schema, dict), 'original_return_schema_required')
        action = self.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? '
            'AND decision_index=?', (self.run_id, context.episode_id, index)).fetchone()
        if action is not None:
            selected = json.loads(action['action'])
        else:
            # Redelivery is an internal recorded decision, not another
            # completed action. Its saved model selection and exact successful
            # report attempt establish the original request without creating
            # a synthetic runtime action or yield observation.
            decision = self.db.execute('SELECT response FROM runtime_model_calls WHERE run_id=? '
                'AND episode_id=? AND call_index=?', (self.run_id, context.episode_id, index)).fetchone()
            selected = {} if decision is None or decision['response'] is None else json.loads(decision['response']).get('selection', {})
            self._require(selected.get('kind') == 'redeliver_report', 'commission_action_required')
        if selected.get('kind') == 'redeliver_report':
            selected_schema = json.loads(selected['schema_json'])
            if ('report_contract_declaration' in row.keys()
                    and row['report_contract_declaration'] is not None):
                from .episode_contract_information import validate_saved_fact_form
                try:
                    selected_schema = validate_saved_fact_form(child_role=child.role,
                        submitted_schema_json=selected['schema_json'], expanded_schema=schema,
                        declaration=json.loads(row['report_contract_declaration']))
                except (ValueError, TypeError, KeyError, RecursionError) as error:
                    raise ValueError(self.failure_prefix + 'redelivery_declaration_invalid') from error
            self._require(selected.get('delivery_ref') == row['delivery_ref']
                and self._equal(selected_schema, schema)
                and selected.get('purpose') == contract.get('decision'), 'redelivery_conflict')
            earlier = self.db.execute('SELECT child_episode_id,contract FROM runtime_report_attempts '
                'WHERE run_id=? AND parent_episode_id=? AND delivery_ref=? AND decision_index<? '
                'ORDER BY decision_index LIMIT 1', (self.run_id, context.episode_id, row['delivery_ref'], index)).fetchone()
            self._require(earlier is not None and earlier['child_episode_id'] == child.episode_id
                and self._equal(json.loads(earlier['contract']), child.request.get('report_contract')), 'redelivery_origin_conflict')
        else:
            self._require(self._equal(child.request.get('report_contract'), contract), 'return_child_contract_conflict')
            self._require(child.path[-1][1] == 'child_' + str(index)
                and selected.get('kind') in {'child', 'episode_child', 'job_child', 'tool'}, 'commission_child_conflict')
            self._require(selected.get('kind') != 'tool' or selected.get('tool') == 'process.revise', 'commission_child_conflict')
            if selected.get('kind') in {'episode_child', 'job_child'}:
                self._require(selected.get('role') == child.role, 'commission_role_conflict')
            if child.role == 'results':
                self._require(self._equal(selected.get('assignment'), child.assignment), 'commission_assignment_conflict')
        frozen = self.db.execute('SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?',
            (self.run_id, child.episode_id)).fetchone()
        self._require(frozen is not None, 'closed_child_facts_required')
        facts = json.loads(frozen['facts'])
        for name, node in schema.get('properties', {}).items():
            source = node.get('x-source')
            if source is not None:
                self._require(source in facts and name in form and self._equal(form[name], facts[source]), 'frozen_return_conflict')
        return child, form, schema

    def _admission_index(self, context, operation_key):
        prefix = f'{self.run_id}:{context.episode_id}:'
        self._require(isinstance(operation_key, str) and operation_key.startswith(prefix)
            and operation_key.endswith(':typed_form'), 'admission_operation_required')
        index = operation_key[len(prefix):-len(':typed_form')]
        self._require(re.fullmatch(r'0|[1-9][0-9]*', index) is not None, 'admission_operation_required')
        return int(index)

    def recorded_admission_references(self, context, admitted, schema, index):
        """Recover an already received original projection, without granting it.

        A successful attempt is saved before first delivery. Only the completed
        parent action's original reference projection proves that its admission
        callbacks already ran. Older outcomes without that projection retain
        the ordinary delivery path. The host-owned projection defines its
        original order and subset; this does not reconstruct its completeness
        from the form or authenticate arbitrary rewrites of the journal.
        """
        self.authenticate(context)
        self._require(type(index) is int and index >= 0, 'admission_index_required')
        action = self.db.execute('SELECT result FROM runtime_actions WHERE run_id=? '
            'AND episode_id=? AND decision_index=?',
            (self.run_id, context.episode_id, index)).fetchone()
        if action is None or action['result'] is None:
            return None
        try:
            outcome = json.loads(action['result'])
        except (ValueError, TypeError) as error:
            raise ValueError(self.failure_prefix + 'original_projection_invalid') from error
        self._require(type(outcome) is dict, 'original_projection_invalid')
        if ('pending_handle' in outcome or 'record_refs' not in outcome
                or outcome.get('status') != 'completed'):
            return None
        _, original_form, original_schema = self._attempt(context, index)
        self._require(self._equal(admitted, original_form), 'original_form_conflict')
        self._require(self._equal(schema, original_schema), 'original_schema_conflict')
        references = outcome['record_refs']
        self._require(type(references) is list
            and all(type(ref) is str and ref for ref in references)
            and len(set(references)) == len(references), 'original_projection_invalid')
        paged_member = False
        for reference in references:
            try:
                record = self.store.get(reference)
            except (ValueError, KeyError) as error:
                raise ValueError(self.failure_prefix + 'original_reference_missing') from error
            self._require(isinstance(record, dict) and record.get('id') == reference
                and isinstance(record.get('record_type'), str)
                and record['record_type'], 'original_reference_conflict')
            paged_member = paged_member or record['record_type'] == 'collection_member'
        # Collection members use the existing paged interface and deliberately
        # have no ordinary EpisodeReceipts grant. Preserve that delivery path.
        if paged_member:
            return None
        for reference in references:
            receipt = self.db.execute('SELECT receipt_kind,source_index FROM runtime_record_receipts '
                'WHERE run_id=? AND episode_id=? AND record_ref=?',
                (self.run_id, context.episode_id, reference)).fetchone()
            original_delivery = (receipt is not None and receipt['receipt_kind'] == 'child_form'
                and type(receipt['source_index']) is int and receipt['source_index'] == index)
            self._require(original_delivery or self._received_before(
                context.episode_id, reference, index), 'original_receipt_conflict')
        return list(references)



__all__ = ["EpisodeReturnRecords"]
