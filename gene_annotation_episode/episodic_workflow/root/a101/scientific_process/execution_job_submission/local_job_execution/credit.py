"""Private launch_local credit behavior for A101."""
from __future__ import annotations
from .execution_contracts import ROLES, ROLE_KINDS, _CLOSED_CREDIT, canonical, digest, json, math, plain, validate_completion_proof

class ExecutionEpisodeCredit:

    def credit_kind(self, role):
        if role not in self.roles:
            raise ValueError('unknown_execution_episode_role')
        return 'operational'

    def _closed_credit_carrier(self, context):
        """Validate closed runtime metadata without reading scientific payloads."""
        from gene_annotation_episode.episodic_workflow.root.a101.episode_return_records import EpisodeReturnRecords
        EpisodeReturnRecords(self.store, self.run_id, failure_prefix='execution_closed_credit_').authenticate(context)
        row = self.store.db.execute('SELECT state,completion,archive FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()
        if 'launch_local' not in ROLES or row is None or row['state'] != 'yielded' or (row['completion'] is None) or (row['archive'] is None):
            raise ValueError('execution_closed_credit_carrier_conflict')
        completion, archive = (json.loads(row['completion']), json.loads(row['archive']))
        if type(completion) is not dict or set(completion) != {'actions', 'ended_by'} or type(completion['actions']) is not int or (completion['actions'] < 0) or (type(completion['ended_by']) is not str) or (not completion['ended_by']) or (type(archive) is not dict) or (set(archive) != {'file', 'sha256', 'index_sha256'}) or (type(archive['file']) is not str) or (len(archive['file']) != 69) or (not archive['file'].endswith('.json')) or any((character not in '0123456789abcdef' for character in archive['file'][:-5])) or any((type(archive[key]) is not str or len(archive[key]) != 64 or any((character not in '0123456789abcdef' for character in archive[key])) for key in ('sha256', 'index_sha256'))):
            raise ValueError('execution_closed_credit_carrier_conflict')
        observations = list(self.store.db.execute('SELECT unit_index,observation FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index', (self.run_id, context.episode_id)))
        if [row['unit_index'] for row in observations] != list(range(completion['actions'])):
            raise ValueError('execution_closed_credit_history_conflict')
        return {'completion': completion, 'archive': archive, 'history_sha256': digest([list(row) for row in observations])}

    def _closed_credit_receipts(self, context, *, through=None):
        """Pin the original receipt prefix; later delivery never reprices it."""
        from gene_annotation_episode.episodic_workflow.root.a101.episode_receipts import EpisodeReceipts
        from gene_annotation_episode.episodic_workflow.root.a101.episode_return_records import _same
        db = self.store.db
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_receipt_inheritance'").fetchone() is None or db.execute('SELECT 1 FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone() is None:
            return (None, None, None)
        if through is None:
            through = db.execute('SELECT coalesce(max(receipt_index),0) FROM runtime_record_receipts WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()[0]
        if type(through) is not int or through < 0:
            raise ValueError('execution_closed_credit_receipt_conflict')
        own_through, current, seen, manifests, rows = (through, context.episode_id, set(), [], [])
        while current is not None:
            if current in seen:
                raise ValueError('execution_closed_credit_receipt_conflict')
            seen.add(current)
            manifest = EpisodeReceipts.read_manifest(db, self.run_id, current)
            recorded = db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.run_id, current)).fetchone()
            if recorded is None or not _same(json.loads(recorded['request'])['message'].get('knowledge_inheritance'), manifest):
                raise ValueError('execution_closed_credit_receipt_conflict')
            manifests.append({'episode_id': current, 'manifest': manifest})
            rows.extend((list(row) for row in db.execute('SELECT receipt_index,episode_id,record_ref,receipt_kind,source_index FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND (? IS NULL OR receipt_index<=?) ORDER BY receipt_index', (self.run_id, current, through, through))))
            current, through = (manifest['parent_episode_id'], manifest['through_receipt_index'])
        known = sorted({row[2] for row in rows})
        initial = sorted({row[2] for row in rows if row[1] != context.episode_id or row[3] == 'initial'})
        return ({'through_receipt_index': own_through, 'sha256': digest({'manifests': manifests, 'rows': rows})}, known, initial)

    def _closed_credit_value(self, view):
        if type(view) is not dict or type(view.get('credit')) not in (int, float) or (not math.isfinite(view['credit'])):
            raise ValueError('execution_closed_credit_view_conflict')

    def _closed_credit_facts(self, context, completion_snapshot):
        """Capture the already projected view once, inside the closing facts."""
        if completion_snapshot is None:
            return {}
        capture = completion_snapshot.get('operational_credit_snapshot')
        completion = completion_snapshot.get('completion')
        if capture is None or completion is None:
            return {}
        if self.store.db.execute('SELECT 1 FROM runtime_forms WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone() is not None:
            return {}
        if type(capture) is not dict or set(capture) != {'view', 'selection'}:
            raise ValueError('execution_closed_credit_snapshot_conflict')
        capture = json.loads(canonical(plain(capture)))
        carrier = self._closed_credit_carrier(context)
        if completion.get('ended_by') != carrier['completion']['ended_by'] or type(completion.get('units_consumed')) is not int or completion['units_consumed'] != carrier['completion']['actions']:
            raise ValueError('execution_closed_credit_carrier_conflict')
        selection = self._selection(context, capture['selection'])
        prefix, known, initial = self._closed_credit_receipts(context)
        if prefix is not None and (selection['known_record_refs'] != known or selection['initial_known_record_refs'] != initial):
            raise ValueError('execution_closed_credit_receipt_conflict')
        self._closed_credit_value(capture['view'])
        return {_CLOSED_CREDIT: {'version': _CLOSED_CREDIT, 'context_sha256': digest(context.as_record()), 'binding_sha256': digest(self.as_record()), 'selection': selection, 'receipt_prefix': prefix, 'completion_sha256': digest(carrier['completion']), 'archive_sha256': digest(carrier['archive']), 'history_sha256': carrier['history_sha256'], 'view': capture['view'], 'view_sha256': digest(capture['view'])}}

    def _closed_operational_credit_view(self, context, receiver_selection):
        """Return only the original closed view, never another projection."""
        from gene_annotation_episode.episodic_workflow.root.a101.episode_return_records import _same
        if self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_forms'").fetchone() is None:
            return None
        row = self.store.db.execute('SELECT facts,form FROM runtime_forms WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()
        if row is None:
            return None
        facts = json.loads(row['facts'])
        if _CLOSED_CREDIT not in facts:
            return None
        value = facts[_CLOSED_CREDIT]
        fields = {'version', 'context_sha256', 'binding_sha256', 'selection', 'receipt_prefix', 'completion_sha256', 'archive_sha256', 'history_sha256', 'view', 'view_sha256'}
        if row['form'] is None or type(value) is not dict or set(value) != fields or (value['version'] != _CLOSED_CREDIT):
            raise ValueError('execution_closed_credit_snapshot_conflict')
        carrier = self._closed_credit_carrier(context)
        if value['context_sha256'] != digest(context.as_record()) or value['binding_sha256'] != digest(self.as_record()) or value['completion_sha256'] != digest(carrier['completion']) or (value['archive_sha256'] != digest(carrier['archive'])) or (value['history_sha256'] != carrier['history_sha256']):
            raise ValueError('execution_closed_credit_carrier_conflict')
        saved = self._selection(context, value['selection'])
        prefix = value['receipt_prefix']
        if prefix is not None and (type(prefix) is not dict or set(prefix) != {'through_receipt_index', 'sha256'}):
            raise ValueError('execution_closed_credit_receipt_conflict')
        actual, known, initial = self._closed_credit_receipts(context, through=None if prefix is None else prefix['through_receipt_index'])
        if not _same(actual, prefix) or (prefix is not None and (saved['known_record_refs'] != known or saved['initial_known_record_refs'] != initial)):
            raise ValueError('execution_closed_credit_receipt_conflict')
        supplied = self._selection(context, receiver_selection)
        if not set(saved['known_record_refs']) <= set(supplied['known_record_refs']) or supplied['initial_known_record_refs'] != saved['initial_known_record_refs']:
            raise ValueError('execution_closed_credit_receipt_conflict')
        if prefix is not None:
            _, current_known, current_initial = self._closed_credit_receipts(context)
            if set(supplied['known_record_refs']) != set(current_known) or set(supplied['initial_known_record_refs']) != set(current_initial):
                raise ValueError('execution_closed_credit_receipt_conflict')
        elif supplied['known_record_refs'] != saved['known_record_refs']:
            raise ValueError('execution_closed_credit_receipt_conflict')
        view = json.loads(canonical(value['view']))
        if value['view_sha256'] != digest(view):
            raise ValueError('execution_closed_credit_view_conflict')
        self._closed_credit_value(view)
        if not _same(view['credit'], facts.get('credit')):
            raise ValueError('execution_closed_credit_view_conflict')
        return view

    def project_credit(self, context, receiver_selection):
        closed = self._closed_operational_credit_view(context, receiver_selection)
        return self._live_project_credit(context, receiver_selection) if closed is None else closed

    def _live_project_credit(self, context, receiver_selection):
        if self.native_blast_masking_results.applies(context):
            return self.native_blast_masking_results.credit_view(context, receiver_selection)
        if self.native_blast_utility_results.applies(context):
            return self.native_blast_utility_results.credit_view(context, receiver_selection)
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            return self.native_blast_standard_database_results.credit_view(context, receiver_selection)
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            return self.native_blast_database_results.credit_view(context, receiver_selection)
        if self.native_hmmer_preparation_results is not None and self.native_hmmer_preparation_results.applies(context):
            return self.native_hmmer_preparation_results.credit_view(context, receiver_selection)
        if self.native_blast_results is not None and self.native_blast_results.applies(context):
            return self.native_blast_results.credit_view(context, receiver_selection)
        if self.native_hmmer_results.applies(context):
            return self.native_hmmer_results.credit_view(context, receiver_selection)
        return self._delegate(context).credit_view(self._practical_context(context), receiver_selection)

    def credit_view(self, context, receiver_selection):
        return self.project_credit(context, receiver_selection)

    def _proof_for_action(self, context, operation_key):
        if self.native_blast_masking_results.applies(context):
            proof = self.native_blast_masking_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_utility_results.applies(context):
            proof = self.native_blast_utility_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            proof = self.native_blast_standard_database_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            proof = self.native_blast_database_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        prefix = context.run_id + ':' + context.episode_id + ':'
        index = operation_key.removeprefix(prefix)
        if not operation_key.startswith(prefix) or not index.isdecimal() or str(int(index)) != index:
            return None
        row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (context.run_id, context.episode_id, int(index))).fetchone()
        if row is None or row['result'] is None:
            return None
        result = json.loads(row['result'])
        if result.get('status') != 'completed':
            return None
        bodies = []
        rows = self.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index<=? AND result IS NOT NULL ORDER BY decision_index', (context.run_id, context.episode_id, int(index)))
        for earlier in rows:
            outcome = json.loads(earlier[0])
            if outcome.get('status') != 'completed':
                continue
            for reference in outcome.get('record_refs', []):
                body = self._read_result(reference, context.scope)
                if body is not None and body['assignment'] == plain(context.assignment):
                    bodies.append(body)
        complete = self._native_results_complete(context, bodies)
        keys = ['requested_filesystem_acquisition', 'successful_exact_attempt_observed', 'attempt_output_version_unverified']
        if self.local_file_sources.applies(context):
            keys = ['requested_complete_file_sources', 'exact_attempt_terminal_quiescent_observed', 'attempt_output_version_unverified']
        endpoint = 'usable_handoff'
        if not complete:
            return None
        receipt = {'action': json.loads(row['action']), 'outcome': result, 'endpoint': endpoint, 'validation_keys': keys}
        return {'version': 'practical_completion_v1', 'run_id': context.run_id, 'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment), 'endpoint': endpoint, 'operation_key': operation_key, 'receipt_sha256': digest(receipt), 'validation_keys': keys}

    def completion_for_action(self, context, operation_key):
        self.credit_kind(context.role)
        if self.native_blast_masking_results.applies(context):
            proof = self.native_blast_masking_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_utility_results.applies(context):
            proof = self.native_blast_utility_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            proof = self.native_blast_standard_database_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            proof = self.native_blast_database_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if 'launch_local' in ROLE_KINDS:
            return self._delegate(context).completion_for_action(self._practical_context(context), operation_key)
        if self.native_hmmer_preparation_results is not None and self.native_hmmer_preparation_results.applies(context):
            proof = self.native_hmmer_preparation_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_results is not None and self.native_blast_results.applies(context):
            proof = self.native_blast_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_hmmer_results.applies(context):
            proof = self.native_hmmer_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        return self._proof_for_action(context, operation_key)

    def _closed_completion_verdict(self, context, proof):
        """Reuse only an endpoint verification actually recorded in history."""
        if self._closed_operational_credit_view(context, None) is None:
            return None
        from gene_annotation_episode.episodic_workflow.root.a101.method_loop.identities import UnitRef
        from gene_annotation_episode.episodic_workflow.root.a101.episode_return_records import _same
        from gene_annotation_episode.episodic_workflow.root.a101.numerical import NumericBand
        from gene_annotation_episode.episodic_workflow.root.a101.practical_yield import ESTIMATOR_VERSION
        assignment = context.assignment
        matches = 0
        for row in self.store.db.execute('SELECT unit_index,observation FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index', (self.run_id, context.episode_id)):
            try:
                observed = json.loads(row['observation'])
                supplied = observed['credit']
                if type(supplied) is not dict or not _same(supplied.get('practical_completion'), proof):
                    continue
                index = observed['decision_index']
                unit = UnitRef.from_record(observed['unit_ref'])
                estimate = observed['step']['estimate']
                diagnostics, provenance = (estimate['diagnostics'], estimate['provenance'])
                if type(index) is int and index >= 0 and (type(supplied.get('estimation_action_index')) is int) and (supplied['estimation_action_index'] == index) and (unit.episode_id == context.episode_id) and (unit.unit_index == row['unit_index']) and (proof['run_id'] == self.run_id) and (proof['episode_id'] == context.episode_id) and (proof['assignment_sha256'] == digest(assignment)) and (proof['operation_key'] == f'{self.run_id}:{context.episode_id}:{index}') and (type(estimate['turns']) is int) and (estimate['turns'] == unit.unit_index + 1) and (provenance['version'] == ESTIMATOR_VERSION) and (diagnostics['fitting_scope'] == 'verified_assignment_endpoint') and _same(diagnostics['completion_proof'], proof) and (type(diagnostics['completion_action_index']) is int) and (diagnostics['completion_action_index'] == index) and _same(diagnostics['completion_unit_ref'], unit.as_record()) and _same(estimate['expected_next_gain'], NumericBand.exact(0).as_record()):
                    matches += 1
            except (ValueError, TypeError, KeyError):
                continue
        return matches == 1

    def verify_completion(self, context, proof):
        self.credit_kind(context.role)
        try:
            proof = validate_completion_proof(plain(proof))
        except (ValueError, TypeError):
            return False
        historical = self._closed_completion_verdict(context, proof)
        if historical is not None:
            return historical
        if self.native_blast_masking_results.applies(context):
            return proof == self.native_blast_masking_results.completion(context)
        if self.native_blast_utility_results.applies(context):
            return proof == self.native_blast_utility_results.completion(context)
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            return proof == self.native_blast_standard_database_results.completion(context)
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            return proof == self.native_blast_database_results.completion(context)
        return self.state(context).verify_completion(proof)
