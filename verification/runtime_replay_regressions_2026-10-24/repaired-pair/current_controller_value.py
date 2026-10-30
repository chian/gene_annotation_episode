def controller_value(self, source, index, credit):
    observed = self.store.db.execute('SELECT observation FROM runtime_observations '
        'WHERE run_id=? AND episode_id=? AND json_extract(observation,\'$.decision_index\')=?',
        (self.run_id, source.episode_id, index)).fetchone()
    if observed is not None:
        # SQLite REAL is not the original JSON representation (3 becomes
        # 3.0). Replay the one recorded completed-action input, including
        # its original completion fields, instead of changing closed
        # archive identities or rebuilding historical forecast inputs.
        original = json.loads(observed['observation'])['credit']
        if (not isinstance(original, dict) or 'credit' not in original
                or original.get('estimation_action_index', index) != index):
            raise WorkflowError('recorded controller input does not match its action')
        return Record(original)
    value = {"credit": credit}
    if self.has_native_estimation() or self.execution_expectations is not None and self.execution_expectations.applies(source.path[-1][0]):
        value["estimation_action_index"] = index
    elif (self.execution_binding is not None or self.wait_inputs_version == 'wait_inputs_binding_v2'
            or self.completed_action_inputs_version is not None):
        value['estimation_action_index'] = index
    else:
        action = self.journal.row('runtime_actions', source.episode_id, index)
        if action is not None and json.loads(action['action']).get('kind') == 'wait':
            value['estimation_action_index'] = index
    binding = self.specialist(source)
    completion = getattr(binding, 'completion_for_action', None)
    if completion is not None:
        proof = completion(self.binding_context(source), f'{self.run_id}:{source.episode_id}:{index}')
        if proof is not None:
            value['practical_completion'] = proof
            value['estimation_action_index'] = index
    return Record(value)
