from __future__ import annotations

def results_assignment_schema(self, internal, *, _read_request_LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, _read_request_RESULTS_SCHEMA, _read_request_deepcopy, _read_request_result_selector_conditions):
    schema = _read_request_deepcopy()(_read_request_RESULTS_SCHEMA())
    schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'local_file_source_selector_v1'}}}, 'then': _read_request_deepcopy()(_read_request_LOCAL_FILE_SOURCE_SELECTOR_SCHEMA())})
    schema['properties']['selector']['allOf'].extend(_read_request_result_selector_conditions()())
    if self.native_expression_nmf_results is not None:
        from gene_annotation_episode.episodic_workflow.root.a107.expression_nmf_result_contracts import EXPRESSION_NMF_RESULT_SELECTOR_SCHEMA
        schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'expression_nmf_result_selector_v1'}}}, 'then': _read_request_deepcopy()(EXPRESSION_NMF_RESULT_SELECTOR_SCHEMA)})
    if self.native_rna_structure_results is not None:
        from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_result_views import RESULT_SELECTOR_SCHEMA
        from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_contracts import RNA_COMPARISON_SELECTOR_SCHEMA
        alternatives = [*_read_request_deepcopy()(RESULT_SELECTOR_SCHEMA['oneOf']), _read_request_deepcopy()(RNA_COMPARISON_SELECTOR_SCHEMA)]
        versions = [branch['properties']['version']['const'] for branch in alternatives]
        schema['properties']['selector']['allOf'].append({'if': {'required': ['version'], 'properties': {'version': {'enum': versions}}}, 'then': {'oneOf': alternatives}})
    return schema

def launch_assignment_schema(self, internal, *, _read_request_INPUT_VERSION_SCHEMA, _read_request_LAUNCH_VERSION, _read_request_SELECTION_SCHEMA, _read_request_deepcopy, _read_request_launch_request_schema, _read_request_obj):
    schema = _read_request_obj()({'version': {'const': _read_request_LAUNCH_VERSION()}, 'requests': {'type': 'object', 'properties': {key: _read_request_launch_request_schema()(self._request_schema(key, selected=False, internal=internal, compact=False), key, self.resources[key].get('service')) for key in self.resources}, 'minProperties': 1, 'additionalProperties': False}, 'immutable_input_versions': {'type': 'array', 'items': _read_request_deepcopy()(_read_request_INPUT_VERSION_SCHEMA())}, 'constraints': {'type': 'object'}})
    schema['properties']['launch_instructions'] = _read_request_deepcopy()(_read_request_SELECTION_SCHEMA())
    return schema

def prepare_launch_assignment(self, parent, selected, scope):
    selected = self._launch(selected, scope=scope)
    for request in selected['requests'].values():
        self._masking_inputs(parent, request)
        self._utility_inputs(parent, request)
    self._versions(selected['immutable_input_versions'], scope, context=parent, nmf_assignments=selected['requests'].values())
    from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_result_publication import validate_native_job_inputs
    from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
    from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_result_publication import validate_rna_structure_job_inputs
    for request in selected['requests'].values():
        validate_native_job_inputs(self.store, parent, request)
        validate_standard_blast_job_inputs(self.store, parent, request)
        validate_rna_structure_job_inputs(self.store, parent, request)
    return selected

def prepare_results_assignment(self, parent, selected, scope, *, _read_request_is_file_source_selector, _read_request_is_native_blast_database_target, _read_request_is_native_rna_structure_target, _read_request_is_standard_blast_database_target):
    masking = self._retained_masking_target(parent, selected, scope)
    utility = self._retained_utility_target(parent, selected, scope)
    nmf = self._retained_expression_nmf_target(parent, selected, scope)
    target = nmf if nmf is not None else utility if utility is not None else masking if masking is not None else self.job_progress_provider.targets.read_target(selected['handoff_ref'], scope)
    self._selector(selected, target)
    if _read_request_is_file_source_selector()(selected.get('selector')):
        self.local_file_sources.admit(parent, selected, target)
    if self._masking_selector(selected):
        self.native_blast_masking_results.validate_selected_inputs(parent, selected)
    if self._utility_selector(selected):
        self.native_blast_utility_results.validate_selected_inputs(parent, selected)
    if self._comparison_selector(selected):
        from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_operands import validate_rna_comparison_selected_inputs
        validate_rna_comparison_selected_inputs(self.store, parent, selected['selector'], anchor_handoff_ref=selected['handoff_ref'], returns=self.native_rna_structure_returns)
    elif _read_request_is_native_rna_structure_target()(target):
        from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_result_publication import validate_rna_structure_selected_inputs
        validate_rna_structure_selected_inputs(self.store, parent, selected['selector'], handoff_ref=selected['handoff_ref'], returns=self.native_rna_structure_returns)
    if _read_request_is_standard_blast_database_target()(target):
        from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_result_publication import validate_standard_blast_selected_inputs
        validate_standard_blast_selected_inputs(self.store, parent, selected['selector'], handoff_ref=selected['handoff_ref'])
    if _read_request_is_native_blast_database_target()(target):
        from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_result_publication import validate_selected_inputs
        validate_selected_inputs(self.store, parent, selected['selector'], handoff_ref=selected['handoff_ref'])
    return selected
