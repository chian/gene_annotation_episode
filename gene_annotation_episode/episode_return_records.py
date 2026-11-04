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

    def decision_witnesses(self, context, value, cutoff):
        """Locate an own return in decision inputs actually saved by the runtime.

        A commission index does not establish arrival time. Assignment text and
        model selections are excluded; only the runtime child_reports container
        can witness the value before the selected cutoff.
        """
        from .execution_contracts import digest

        def contains(node):
            if self._equal(node, value):
                return True
            return (any(contains(item) for item in node.values()) if type(node) is dict
                else any(contains(item) for item in node) if type(node) is list else False)
        witnesses = []
        for row in self.db.execute("SELECT call_index,request FROM runtime_model_calls WHERE run_id=? "
                "AND episode_id=? AND purpose='decision' AND call_index<=? ORDER BY call_index",
                (self.run_id, context.episode_id, cutoff)):
            request = json.loads(row["request"])
            if contains(request.get("context", {}).get("child_reports", [])):
                witnesses.append(dict(call_index=row["call_index"], request_sha256=digest(request)))
        return witnesses

    def source_admission_before(self, context, source_ref, cutoff):
        """Pin existing receipt authority at the caller's original action cutoff.

        Callers authenticate the context and publication separately. This reads
        metadata only and neither grants a reference nor opens Source bytes.
        Initial and frozen inherited inputs retain their existing authority;
        an own typed return also needs its actual saved decision-input witness.
        """
        from .episode_receipts import EpisodeReceipts
        from .execution_contracts import digest

        # Use this owner's prefix for these two public guard failures. An
        # existing subclass can preserve its original typed error translation.
        EpisodeReturnRecords._require(self, type(cutoff) is int and cutoff >= 0, 'invalid_schema')
        EpisodeReturnRecords._require(self, self._received_before(context.episode_id, source_ref, cutoff),
            'result_not_received')
        receipts = EpisodeReceipts.__new__(EpisodeReceipts)
        receipts.store, receipts.db, receipts.run_id = self.store, self.db, self.run_id
        baseline = source_ref in set(receipts.known(context.episode_id, baseline=True))
        receipt = self.db.execute("SELECT receipt_index,receipt_kind,source_index FROM runtime_record_receipts "
            "WHERE run_id=? AND episode_id=? AND record_ref=?", (self.run_id, context.episode_id, source_ref)).fetchone()
        decision = []
        if not baseline:
            EpisodeReturnRecords._require(self, receipt is not None, 'result_not_received')
            if receipt["receipt_kind"] in {"child_form", "report_redelivery"}:
                decision = self.decision_witnesses(context, source_ref, cutoff)
                EpisodeReturnRecords._require(self, bool(decision), 'result_not_received')
        return dict(source_ref=source_ref, source_sha256=digest(self.store.get(source_ref)),
            receipt_manifest_sha256=digest(EpisodeReceipts.read_manifest(self.db, self.run_id, context.episode_id)),
            receipt=(None if baseline else dict(receipt)), baseline=baseline, decision_witnesses=decision)

    def file_admission_before(self, context, reference, namespace, artifact_ref, cutoff):
        """Prove File timing through original semantic roots, without bytes.

        This grants nothing. The existing received-File reader remains the
        namespace, scope, private-reference and streamed byte-identity owner.
        """
        from .alignment_site_native import immutable_record
        from .episode_receipts import EpisodeReceipts
        from .execution_contracts import digest

        self.authenticate(context)
        self._require(type(cutoff) is int and cutoff >= 0 and namespace in {'source', 'artifact'}
            and type(reference) is str and type(artifact_ref) is str
            and (namespace != 'artifact' or reference == artifact_ref), 'file_admission_selection_invalid')
        reference_admission = (self.source_admission_before(context, reference, cutoff)
            if namespace == 'source' else None)
        selected, artifact = self.store.get(reference), self.store.get(artifact_ref)
        self._require(artifact.get('record_type') == 'artifact' and artifact.get('id') == artifact_ref,
            'file_admission_identity_conflict')
        self._require(self._received_before(context.episode_id, artifact_ref, cutoff), 'file_not_received')
        receipts = EpisodeReceipts.__new__(EpisodeReceipts)
        receipts.store, receipts.db, receipts.run_id = self.store, self.db, self.run_id
        baseline = artifact_ref in set(receipts.known(context.episode_id, baseline=True))
        row = self.db.execute('SELECT receipt_index,receipt_kind,source_index FROM runtime_record_receipts '
            'WHERE run_id=? AND episode_id=? AND record_ref=?',
            (self.run_id, context.episode_id, artifact_ref)).fetchone()
        receipt, delivery = None if baseline else (None if row is None else dict(row)), None
        if not baseline:
            self._require(receipt is not None, 'file_not_received')
            if receipt['receipt_kind'] in {'child_form', 'report_redelivery'}:
                index = receipt['source_index']
                child, form, schema = self._attempt(context, index)
                selected_action = self.db.execute('SELECT action FROM runtime_actions WHERE run_id=? '
                    'AND episode_id=? AND decision_index=?', (self.run_id, context.episode_id, index)).fetchone()
                redelivery = selected_action is None or json.loads(selected_action['action']).get('kind') == 'redeliver_report'
                self._require(redelivery == (receipt['receipt_kind'] == 'report_redelivery'),
                    'file_admission_receipt_conflict')
                witnesses = self.decision_witnesses(context, form, cutoff)
                self._require(bool(witnesses), 'file_not_received')
                roots = self.recorded_admission_references(context, form, schema, index)
                if roots is None:
                    # The existing generic form walker handles explicit object,
                    # array and leaf formats only; opaque resource/hook schemas
                    # require their original recorded grant-root projection.
                    def supported(node):
                        blocked = {'x-source', '$ref', '$defs', '$id', 'anyOf', 'oneOf', 'allOf', 'if', 'then', 'else',
                            'prefixItems', 'patternProperties', 'additionalItems', 'contains', 'dependentSchemas'}
                        if type(node) is not dict or blocked.intersection(node):
                            return False
                        kinds = node.get('type')
                        if type(kinds) is list:
                            if any(type(kind) is not str for kind in kinds):
                                return False
                            kinds = set(kinds)
                        elif type(kinds) is str:
                            kinds = {kinds}
                        else:
                            return False
                        kinds.discard('null')
                        if len(kinds) != 1:
                            return not kinds and node.get('type') == 'null'
                        kind = next(iter(kinds))
                        if kind == 'object':
                            return (type(node.get('properties')) is dict and node.get('additionalProperties') is False
                                and all(supported(item) for item in node['properties'].values()))
                        if kind == 'array':
                            return supported(node.get('items'))
                        return kind in {'string', 'number', 'integer', 'boolean'}
                    self._require(supported(schema), 'file_admission_projection_unavailable')
                    from .runtime import _references_in
                    roots = _references_in({}, self.store.get, forms=[(form, schema)],
                        reference_subset=lambda refs: self.store.reference_subset(refs, plain(context.scope)))
                    self._require(bool(roots), 'file_admission_projection_unavailable')

                def forward_path(root):
                    pending, seen = [(root, [])], set()
                    while pending:
                        candidate, path = pending.pop()
                        if candidate in seen:
                            continue
                        seen.add(candidate)
                        record = self.store.get(candidate)
                        if record.get('record_type') == 'collection_member':
                            continue
                        if record.get('record_type') != 'artifact':
                            try:
                                immutable_record(record)
                            except (ValueError, TypeError, KeyError) as error:
                                raise ValueError(self.failure_prefix + 'file_admission_identity_conflict') from error
                        path = [*path, dict(reference=candidate, record_sha256=digest(record))]
                        if candidate == artifact_ref:
                            return path
                        pending.extend((ref, path) for ref in receipts.forward_references(record) if ref not in seen)
                    return None

                for root in roots:
                    root_receipt = self.db.execute('SELECT receipt_kind,source_index FROM runtime_record_receipts '
                        'WHERE run_id=? AND episode_id=? AND record_ref=?',
                        (self.run_id, context.episode_id, root)).fetchone()
                    if (root_receipt is None or root_receipt['receipt_kind'] != receipt['receipt_kind']
                            or root_receipt['source_index'] != index):
                        continue
                    path = forward_path(root)
                    if path is not None:
                        delivery = dict(source_index=index, child_episode_id=child.episode_id,
                            form_sha256=digest(form), schema_sha256=digest(schema), decision_witnesses=witnesses,
                            root_ref=root, forward_path=path)
                        break
                self._require(delivery is not None, 'file_admission_receipt_conflict')
        return dict(selection=dict(reference=reference, namespace=namespace), artifact_ref=artifact_ref,
            reference_record_sha256=digest(selected), artifact_record_sha256=digest(artifact),
            receipt_manifest_sha256=digest(EpisodeReceipts.read_manifest(self.db, self.run_id, context.episode_id)),
            reference_admission=reference_admission, baseline=baseline, file_receipt=receipt, delivery=delivery)

    def _results_assignment(self, selected, child):
        """Compare selectable operands while authenticating host preparation.

        The homology resource adapter adds its frozen native assignment after
        commission. Execution-family assignments retain their exact comparison.
        No native registry is opened and no handoff is checked again here.
        """
        from .resource_records import RESULTS_VERSION, RESULTS_SCHEMA
        actual = plain(child.assignment)
        if self._equal(selected, actual):
            return
        if not (isinstance(selected, dict) and selected.get('version') == RESULTS_VERSION
                and actual.get('version') == RESULTS_VERSION):
            self._require(self._equal(selected, actual), 'commission_assignment_conflict')
            return
        from .domain import validate_schema
        if actual.get('adapter_assignment',{}).get('version')=='a102_structural_results_assignment_v1':
            from .a102_resources import validate_results_preparation
            validate_schema(selected,RESULTS_SCHEMA)
            valid=validate_results_preparation(self.store,self.run_id,selected,actual,child)
            self._require(valid and self._equal(selected,
                {key:value for key,value in actual.items() if key!='adapter_assignment'}),
                'commission_assignment_conflict')
            return
        from .homology_jobs import HANDOFF_SCHEMA
        try:
            validate_schema(selected, RESULTS_SCHEMA)
            native = actual['adapter_assignment']
            validate_schema(native['handoff'], HANDOFF_SCHEMA)
            handoff = selected['handoff']
            resource = handoff['resource_selection']
            footprint = self.store.coverage(native['query_ref'])
            query_valid = bool(footprint) and self.store.scope_covers(footprint, plain(child.scope))
            if not footprint and self.store.get(native['query_ref'])['record_type']=='reference':
                # An external sequence is an algorithm operand, not a target
                # interval. Preserve the commissioning molecular/scope check
                # and require its actual receipt before this child began.
                from .homology_query import protein_query
                from .episode_receipts import EpisodeReceipts
                protein_query(self.store,plain(child.scope),native['query_ref'],
                    error_code='results_query_outside_assigned_scope')
                query_valid = native['query_ref'] in EpisodeReceipts(self.store,self.run_id).known(
                    child.episode_id,baseline=True)
            valid = (set(native) in ({'job_ref', 'query_ref', 'cpu', 'handoff'},
                                    {'job_ref', 'query_ref', 'cpu', 'handoff', 'search_mode'})
                and native['job_ref'] == native['handoff']['job_ref'] == handoff['execution_handle']
                and type(native['cpu']) is int and native['cpu'] == resource['allocation']['cpu']
                and native['handoff']['registry_ref'] == resource['capability_binding_ref']
                and native['handoff']['status_interface'] == handoff['monitoring']['contract_ref']
                and native['handoff']['results_interface'] == handoff['results']['contract_ref']
                and query_valid)
        except (KeyError, TypeError, ValueError):
            valid = False
        self._require(valid and self._equal(selected,
            {key: value for key, value in actual.items() if key != 'adapter_assignment'}),
            'commission_assignment_conflict')

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
                self._results_assignment(selected.get('assignment'), child)
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

    def received_attempts(self, context, *, allow_unsaved=False):
        """Yield actual typed returns through original frozen ancestor prefixes.

        Family-specific value and reference checks remain with the caller. This
        iterator neither grants references nor opens scientific artifact bytes.
        """
        from .episode_receipts import EpisodeReceipts
        from .execution_contracts import digest
        self.authenticate(context, allow_unsaved=allow_unsaved)
        current, prefix, seen = context, None, set()
        while True:
            self._require(current.episode_id not in seen, 'receipt_lineage_cycle')
            seen.add(current.episode_id)
            manifest = EpisodeReceipts.read_manifest(self.db, self.run_id, current.episode_id)
            self._require(self._equal(plain(current.request)["message"].get("knowledge_inheritance"), manifest),
                'received_lineage_conflict')
            if prefix is None:
                indices = [row[0] for row in self.db.execute('SELECT decision_index FROM runtime_report_attempts '
                    'WHERE run_id=? AND parent_episode_id=? AND failure IS NULL AND form IS NOT NULL '
                    'ORDER BY decision_index', (self.run_id, current.episode_id))]
            else:
                indices = []
                for frozen in prefix['attempts']:
                    row = self.db.execute('SELECT delivery_ref,child_episode_id,contract,form,failure '
                        'FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
                        (self.run_id, current.episode_id, frozen['decision_index'])).fetchone()
                    self._require(row is not None and row['failure'] is None and row['form'] is not None
                        and all(row[key] == frozen[key] for key in ('delivery_ref', 'child_episode_id'))
                        and digest(json.loads(row['contract'])) == frozen['contract_sha256']
                        and digest(json.loads(row['form'])) == frozen['form_sha256'], 'received_prefix_conflict')
                    indices.append(frozen['decision_index'])
            for index in indices:
                yield self._attempt(current, index)
            if manifest['parent_episode_id'] is None:
                return
            self._require('received_report_prefix' in manifest, 'received_prefix_unavailable')
            parent = self.context(manifest['parent_episode_id'])
            self._require(current.path[:-1] == parent.path, 'received_lineage_conflict')
            prefix, current = manifest['received_report_prefix'], parent

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
