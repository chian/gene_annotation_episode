"""Shared Root policy assembly; actual private consumers and configuration are recorded in the ownership account."""
from __future__ import annotations

def scientific_library_available(self, source):
    if self.scientific_process_binding is None:
        return False
    if source is None:
        return True
    if self.is_job_source(source):
        return False
    binding = self.specialist(source)
    return binding is None or 'scientific_process' in binding.allowed_children(self.binding_context(source), self.services.capabilities())

def scientific_retriever_catalog(self):
    catalog = getattr(self.scientific_process_binding, 'scientific_retriever_catalog', None)
    if catalog is not None:
        return catalog()
    from gene_annotation_episode.episodic_workflow.root.scientific_tool_library import catalog
    configuration = self.scientific_process_binding.tool_retrieval
    return catalog(retrieval_mode=None if configuration is None else configuration['mode'], tool_info=self.scientific_process_binding.tool_library.supports_tool_info)

def catalog(self, scope, source=None):
    from gene_annotation_episode.episodic_workflow.root.commissioning_policy import annotation_catalog
    _root_handled, _root_value = annotation_catalog(self, source)
    if _root_handled:
        return _root_value
    catalog = self.job_implementation(path=source.path).catalog(source) if source is not None and self.is_job_source(source) else self.specialist(source).catalog(self.binding_context(source)) if source is not None and self.specialist(source) is not None else self.tools.catalog(scope=scope)
    entries = [{'name': name, **definition} for name, definition in catalog.items()] if isinstance(catalog, _original_action_catalog.Mapping) else list(catalog)
    knowledge_tools = _original_action_catalog.knowledge_catalog()
    launch_tools = _original_action_catalog.launch_instruction_catalog()
    from gene_annotation_episode.episodic_workflow.root.shared_information import catalog as shared_catalog
    shared_tools = self.shared_information_catalog(source)
    process_tools = []
    if self.scientific_process_binding is not None:
        scientific_catalog = getattr(self.scientific_process_binding, 'scientific_library_catalog', None)
        if scientific_catalog is None:
            from gene_annotation_episode.episodic_workflow.root.scientific_process_library import catalog as scientific_catalog
        process_tools = scientific_catalog() + self.scientific_retriever_catalog()
    reserved = {'episode.history', 'episode.credit', 'episode.annotation_score', 'episode.estimate_wait', 'episode.monitoring_information', *(item['name'] for item in knowledge_tools), *(item['name'] for item in launch_tools), *(item['name'] for item in shared_catalog()), *(item['name'] for item in process_tools)}
    if any((item['name'] in reserved for item in entries)):
        raise _original_action_catalog.WorkflowError('Episode inspection tools are owned by the current Episode runtime')
    for entry in entries:
        guides = self.knowledge.entries_for_tool(entry['name'])
        if guides:
            entry['knowledge_entry_ids'] = guides
    entries.extend(knowledge_tools)
    entries.extend(launch_tools)
    entries.extend(shared_tools)
    if self.scientific_library_available(source):
        entries.extend(process_tools)
    if source is not None and self.permits_common_action(source, 'wait'):
        entries.append(_original_action_catalog._wait_estimate_operation())
    entries.append({'name': 'episode.history', 'description': "Read only this Episode's prior decisions: metadata index, exact selected actions/outcomes and admitted direct-child forms, or a bounded publication-ID page from one prior own action. Prior history-read bodies are represented by references to their original decision indices; read those indices directly rather than recursively copying history responses. Original scientific outcomes remain exact. Failed outcomes remain failed. In view=records, a saved rejected selection retains its exact rejection_feedback without becoming an executed outcome. This ordinary read never executes old work or reads child-private conversations.", 'input_schema': {'anyOf': [{'type': 'object', 'additionalProperties': False, 'required': ['view'], 'properties': {'view': {'type': 'string', 'enum': ['index', 'records']}, 'offset': {'type': 'integer', 'minimum': 0, 'description': "Position in this Episode's ordered prior-decision page; omit when selecting decision_indices."}, 'limit': {'type': 'integer', 'minimum': 1, 'description': 'Requested page size; defaults to max(1, restoration preview_size), so disabling automatic previews still permits an ordinary page to advance. Omit when selecting decision_indices.'}, 'decision_indices': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': {'type': 'integer', 'minimum': 0}}}}, {'type': 'object', 'additionalProperties': False, 'required': ['view', 'decision_index'], 'properties': {'view': {'type': 'string', 'const': 'publications'}, 'decision_index': {'type': 'integer', 'minimum': 0}, 'offset': {'type': 'integer', 'minimum': 0, 'description': 'Position in the actual saved publication-ID array for this one prior own action.'}, 'limit': {'type': 'integer', 'minimum': 1, 'description': 'Requested publication-ID page size; defaults to max(1, restoration preview_size).'}}}]}})
    projector = self.credit_detail_projector(source)
    if callable(getattr(projector, 'read_details', None)):
        entries.append({'name': 'episode.credit', 'description': "Read the current credit projection for this Episode's fixed scope using this run's actual frozen projector and policy. The explicit limit and offset page source contributions and inactive dependencies independently; each includes its own total and next_offset. Zero limit requests metadata only. These are current source-bound operands, not biological accuracy or newly performed work.", 'input_schema': _original_action_catalog._object({'limit': {'type': 'integer', 'minimum': 0}, 'offset': {'type': 'integer', 'minimum': 0}})})
    if not (source is not None and self.is_job_source(source)) and callable(getattr(self.project_annotation_score, 'read_details', None)):
        entries.append({'name': 'episode.annotation_score', 'description': 'Inspect the separately bound score for each proposed annotation and its actual evidence operands for this fixed scope. This uses the same projector and policy as the annotation scores in your decision context. Explicit limit and offset page its source contributions and inactive dependencies; limit zero requests metadata only. The result does not award investigation progress or establish biological correctness.', 'input_schema': _original_action_catalog._object({'limit': {'type': 'integer', 'minimum': 0}, 'offset': {'type': 'integer', 'minimum': 0}})})
    if self.native_timing_information is not None:
        entries.append({'name': 'episode.monitoring_information', 'description': "Read this episode's separately bound monitoring credit for received native durations. Explicit limit/offset page actual measurements beyond the inherited/original baseline. This read changes no scientific state, timer, job or continuation rule.", 'input_schema': _original_action_catalog._object({'limit': {'type': 'integer', 'minimum': 0}, 'offset': {'type': 'integer', 'minimum': 0}})})
    binding = self.specialist(source) if source is not None else None
    if self.decision_protocol == _original_action_catalog.DECISION_EXCHANGE_PROTOCOL:
        for entry in entries:
            if entry['name'] == 'episode.history':
                entry['input_schema']['anyOf'][0]['properties']['view'] = {'type': 'string', 'const': 'records'}
    names = getattr(binding, 'common_tool_names', None)
    if names is not None:
        permitted = set(names(self.binding_context(source)))
        instruction_tools = {entry['name'] for entry in launch_tools}
        entries = [entry for entry in entries if entry['name'] in permitted | instruction_tools]
    return entries

from gene_annotation_episode.episodic_workflow.root import action_catalog as _original_action_catalog
