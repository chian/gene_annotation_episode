from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.library.appservice_monitor_values import *

class AppServiceMonitorCustody:

    def __init__(self, execution):
        self.api, self.store = (execution, execution.store)
        self.custody = execution.appservice.custody

    def _monitor(self, context, *, allow_unsaved=False):
        _require(isinstance(context, BindingContext) and context.role == 'monitor', 'saved_context_required')
        self.custody.authenticate(context, allow_unsaved=allow_unsaved)
        assignment = plain(context.assignment)
        validate_schema(assignment, _ASSIGNMENT)
        parent, index = self.custody._commission(context)
        return (assignment, parent, index)

    def _cutoff(self, child, parent, reference):
        cutoff = self.custody._inheritance(child, parent)
        if cutoff is not None:
            row = self.store.db.execute('SELECT 1 FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=? AND receipt_index<=?', (self.api.run_id, parent.episode_id, reference, cutoff)).fetchone()
            _require(row is not None, 'handoff_not_received_before_commission')

    def _relationship(self, snapshot, target, handoff):
        """Authenticate the particular physical dependency, never its basename."""
        for dependency in snapshot['dependencies']:
            if dependency['handle'] != target['handle'] or dependency['kind'] != 'job':
                continue
            _require(self.custody._table('runtime_execution_progress_dependencies'), 'dependency_record_missing')
            source = self.store.get(dependency['relation_ref'])
            payload = {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}}
            _require(source.get('record_type') == 'source' and source.get('origin') == 'tool' and (source.get('provider') == 'execution.progress.relationship') and (source.get('artifact_ref') == source.get('request_ref')) and (source['id'] == identity('source', {'origin': 'tool', 'record': payload})), 'dependency_source_conflict')
            value = self.api._artifact_json(source['artifact_ref'])
            expected = {'version': 'execution_resource_dependency_v1', 'run_id': self.api.run_id, 'owner_episode_id': target['origin_episode_id'], 'operation_key': handoff['original_task']['submission_operation_key'], 'target': target}
            _require(canonical(value) == canonical(expected), 'dependency_submission_conflict')
            physical = digest({key: target[key] for key in ('run_id', 'origin_episode_id', 'resource_id', 'resource_kind', 'execution_id', 'request_sha256')})
            row = self.store.db.execute('SELECT target_handle,relationship FROM runtime_execution_progress_dependencies WHERE run_id=? AND physical_identity=?', (self.api.run_id, physical)).fetchone()
            _require(row is not None and row['target_handle'] == target['handle'] and (canonical(json.loads(row['relationship'])) == canonical(dependency)), 'dependency_record_conflict')
            return True
        return False

    def _progress_identity(self, snapshot):
        row = self.store.db.execute('SELECT target_handle,scope,signature FROM runtime_progress_observations WHERE run_id=? AND progress_ref=?', (self.api.run_id, snapshot['progress_ref'])).fetchone()
        signature = content_digest(_same_observation(snapshot))
        _require(row is not None and row['target_handle'] == snapshot['target_handle'] and (row['signature'] == signature) and (snapshot['progress_ref'] == 'progress_' + content_digest({'run_id': self.api.run_id, 'target_handle': row['target_handle'], 'scope': json.loads(row['scope']), 'signature': signature})), 'dependency_observation_identity_conflict')

    def _dependency(self, parent, target, handoff, *, before, visiting=()):
        """An actual received progress result can carry a specific dependency.

        Own progress reads are synchronous completed actions, so their earlier
        selected index supplies the temporal bound. A typed return additionally
        needs the frozen record prefix at its receiving commission.
        """
        _require(parent.episode_id not in visiting, 'cyclic_dependency_custody')
        visiting = (*visiting, parent.episode_id)
        if parent.role == 'monitor':
            self._monitor(parent)
        if not self.custody._table('runtime_progress_observations'):
            return False
        sql = 'SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL AND decision_index>=0'
        args = [self.api.run_id, parent.episode_id]
        if before is not None:
            sql += ' AND decision_index<?'
            args.append(before)
        for row in self.store.db.execute(sql, args):
            action, outcome = (json.loads(row['action']), json.loads(row['result']))
            if action.get('kind') != 'tool' or action.get('tool') not in {'progress.observe', 'progress.read'} or outcome.get('status') not in {'completed', 'partial'}:
                continue
            snapshot = outcome.get('result')
            if not isinstance(snapshot, dict) or snapshot.get('progress_ref') not in outcome.get('progress_refs', []):
                continue
            saved = read_progress(self.store, self.api.run_id, snapshot['progress_ref'], parent.scope)
            validate_schema(saved, _SNAPSHOT)
            _require(canonical(snapshot) == canonical(saved), 'dependency_observation_conflict')
            if action['tool'] == 'progress.observe':
                _require(parent.role == 'monitor' and snapshot['target_handle'] == parent.assignment['target_handle'] and ('dependencies' in action.get('arguments', {}).get('requested_fields', [])), 'dependency_selection_conflict')
                key = f"{self.api.run_id}:{parent.episode_id}:{row['decision_index']}"
                selected = self.store.db.execute('SELECT selection,signature,progress_ref FROM runtime_progress_selections WHERE run_id=? AND operation_key=?', (self.api.run_id, key)).fetchone()
                _require(selected is not None and selected['progress_ref'] == snapshot['progress_ref'], 'dependency_selection_missing')
                selection = json.loads(selected['selection'])
                _require(selected['signature'] == content_digest(selection) and selection['target_handle'] == snapshot['target_handle'] and (canonical(selection['requested_fields']) == canonical(action['arguments']['requested_fields'])) and (canonical(selection['scope']) == canonical(parent.scope)), 'dependency_selection_conflict')
            else:
                _require(action.get('arguments') == {'progress_ref': snapshot['progress_ref']}, 'dependency_selection_conflict')
            if self._relationship(snapshot, target, handoff):
                self._progress_identity(snapshot)
                return True
        sql = 'SELECT decision_index FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND failure IS NULL AND form IS NOT NULL'
        args = [self.api.run_id, parent.episode_id]
        if before is not None:
            sql += ' AND decision_index<?'
            args.append(before)
        for row in self.store.db.execute(sql, args):
            child, form, schema = self.custody._attempt(parent, row['decision_index'])
            names = [name for name, node in schema['properties'].items() if node.get('x-source') == 'monitoring_dependency_handles' and node.get('items', {}).get('format') == 'reference' and (node['items'].get('x-reference-namespace') == 'execution_handle')]
            if not any((target['handle'] in form[name] for name in names)):
                continue
            if self._dependency(child, target, handoff, before=None, visiting=visiting):
                return 'typed_dependency'
        return False

    def _possession(self, context, target, handoff, *, allow_unsaved=False):
        assignment, parent, index = self._monitor(context, allow_unsaved=allow_unsaved)
        _require(assignment['target_handle'] == target['handle'], 'assigned_target_conflict')
        if parent.role == 'monitor':
            self._monitor(parent)
        if parent.role == 'monitor' and parent.assignment.get('target_handle') == target['handle']:
            return self._possession(parent, target, handoff)
        try:
            self.custody.possession(parent, target['handle'], before=index)
        except AppServiceCustodyError as error:
            if error.code != 'bvbrc_appservice_custody_input_not_possessed':
                raise
            dependency = self._dependency(parent, target, handoff, before=index)
            _require(bool(dependency), 'handoff_not_possessed_before_commission')
            if dependency == 'typed_dependency':
                self._cutoff(context, parent, target['handle'])
        else:
            self._cutoff(context, parent, target['handle'])

    def resolve_target(self, context, reference):
        """Validate an assigned target or an actually received dependency.

        This is the same original handoff and temporal custody proof used for
        native observation. Initial form validation can precede saving the
        child; only its exact saved parent model selection authorizes that
        interval. Dependencies still require a saved receiving monitor.
        """
        _require(isinstance(context, BindingContext) and context.role == 'monitor', 'saved_context_required')
        target = self.api.appservice.read_target(reference, context.scope)
        body = self.api.appservice.read_handoff(reference, context.scope)
        if context.assignment.get('target_handle') == reference:
            self._possession(context, target, body['task_handoff'], allow_unsaved=True)
        else:
            self._monitor(context)
            _require(self._dependency(context, target, body['task_handoff'], before=None), 'target_not_received_dependency')
        return True
