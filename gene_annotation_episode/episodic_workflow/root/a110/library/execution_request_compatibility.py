from __future__ import annotations

def results_assignment_schema(self, internal, *, _read_request_LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, _read_request_RESULTS_SCHEMA, _read_request_deepcopy):
    schema = _read_request_deepcopy()(_read_request_RESULTS_SCHEMA())
    schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'local_file_source_selector_v1'}}}, 'then': _read_request_deepcopy()(_read_request_LOCAL_FILE_SOURCE_SELECTOR_SCHEMA())})
    if self.native_flux_balance_results is not None:
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_result_selection import FBA_RESULT_SELECTOR_SCHEMA
        schema['properties']['selector']['allOf'].append({'if': {'required': ['version'], 'properties': {'version': {'const': 'flux_balance_result_selector_v1'}}}, 'then': _read_request_deepcopy()(FBA_RESULT_SELECTOR_SCHEMA)})
    return schema

def launch_assignment_schema(self, internal, *, _read_request_INPUT_VERSION_SCHEMA, _read_request_LAUNCH_VERSION, _read_request_SELECTION_SCHEMA, _read_request_deepcopy, _read_request_obj):
    schema = _read_request_obj()({'version': {'const': _read_request_LAUNCH_VERSION()}, 'requests': {'type': 'object', 'properties': {key: self._request_schema(key, selected=False, internal=internal, compact=False) for key in self.resources}, 'minProperties': 1, 'additionalProperties': False}, 'immutable_input_versions': {'type': 'array', 'items': _read_request_deepcopy()(_read_request_INPUT_VERSION_SCHEMA())}, 'constraints': {'type': 'object'}})
    schema['properties']['launch_instructions'] = _read_request_deepcopy()(_read_request_SELECTION_SCHEMA())
    if any((value.get('native_flux_balance') for value in self.resources.values())):
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import launch_assignment_schema
        return {'anyOf': [schema, launch_assignment_schema(self.resources)]}
    return schema

def prepare_launch_assignment(self, parent, selected, scope):
    selected = self._launch(selected, scope=scope)
    for request in selected['requests'].values():
        self._flux_balance_inputs(parent, request, input_versions=selected['immutable_input_versions'])
    self._versions(selected['immutable_input_versions'], scope, context=parent, flux_balance_assignments=selected['requests'].values())
    return selected

def prepare_results_assignment(self, parent, selected, scope, *, _read_request_is_file_source_selector):
    target = self._retained_flux_balance_target(parent, selected, scope)
    if target is None:
        target = self.job_progress_provider.targets.read_target(selected['handoff_ref'], scope)
    self._selector(selected, target)
    if _read_request_is_file_source_selector()(selected.get('selector')):
        self.local_file_sources.admit(parent, selected, target)
    return selected
