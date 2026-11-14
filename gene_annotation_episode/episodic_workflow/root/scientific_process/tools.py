from __future__ import annotations
from .source_contracts import (Mapping, deepcopy, hashlib, inspect, json, Path, re, ReportBoundaryError, interpretation_schema, plain, validate_closed_schema, validate_form, ContractError, identity, obj, validate_schema, reference_in_context, scientific_digest, scientific_invocation_ref, validate_child_selection, validate_filled_process, validate_option_ref, validate_revision_origin, validate_selection, selection_fields, selector_selection, SELECTION_VERSION, LEGACY_SELECTION_VERSION, build_process_result, merge_process_results, report_sources, validate_process_result, SUPPORT_ENTRY_VERSION, support_observation_kinds, validate_support_entry, EVIDENCE_AXIS_VERSION, validate_evidence_axis_entry, INSTRUCTION_VERSION, instruction_view, validate_instruction_entry, evidence_axis_instruction_view, alignment_site_fact_sources, requested_site_projections, project_site_action_return, validate_frozen_site_return, restriction_mapping_fact_sources, requested_restriction_projections, project_restriction_action_return, validate_frozen_restriction_return, molecular_fact_sources, merge_molecular_facts, requested_molecular_fact_sources, requested_molecular_fact_fields, validate_frozen_molecular_return, PROTEIN_ACTION_FACT_SOURCES, protein_structure_action_fact_sources, merge_protein_structure_action_facts, requested_protein_structure_action_fields, validate_frozen_protein_structure_action_return, VERSION, ROLE, ROLES, _COMMON_TOOLS, _REFERENCE, _SHA256, _SCIENTIFIC_NAMESPACES, _IMPLEMENTATION_FILES, _ITC_PARAMETER_SOURCE, _ANNOTATION_REF, _EVIDENCE_AXIS, _THOUGHT_REF, _TOOLS, _LEGACY_SELECTION, _TOOL_SELECTOR, _TOOL_INFO, _SELECTION, _CANONICAL_SELECTION, _REVISION_ORIGIN, _EVIDENCE_TASK, _ASSIGNMENT, _RECORDED_ASSIGNMENT, _REVISION_ARGUMENTS, _LEGACY_REVISION_ARGUMENTS, original_axis_task_projector, _object, _ref_schema)

class ScientificTools:
    def _information_catalog(self, scope):
        # Older injected ordinary-only service ports have no resource routes.
        # This fallback grants no operation beyond their original direct map.
        callback = getattr(self.services, 'tool_information_catalog', self.services.tool_catalog)
        return callback(scope)

    def _closed_tool_resolution(self, context, selection):
        """Read only an authenticated closed owner's original frozen contracts."""
        original = self.restore_closed_process(context)
        if original is None:
            return None
        if scientific_digest(selection) != scientific_digest(original['selection']):
            raise ContractError('scientific_filled_identity_mismatch')
        return (self.tool_library.resolve(selection['tools'])
            if selection['version'] == LEGACY_SELECTION_VERSION else
            self.tool_library.resolve_invocations(selection['child_tool_info']))

    def _tool_resolution_for(self, selection, scope, *, context=None):
        if context is not None:
            if plain(scope) != plain(context.scope):
                raise ContractError('scientific_filled_identity_mismatch')
            closed = self._closed_tool_resolution(context, selection)
            if closed is not None:
                return closed
        return (self.tool_library.resolve(selection['tools'], self.services.tool_catalog(scope))
            if selection['version'] == LEGACY_SELECTION_VERSION else
            self.tool_library.resolve_invocations(selection['child_tool_info'], self._information_catalog(scope)))

    def _tool_resolution(self, context, selection):
        entries = self._tool_resolution_for(selection, context.scope, context=context)
        if any(entry["name"] in {*_COMMON_TOOLS, "process.revise"} for entry in entries):
            raise ContractError("scientific_primitive_uses_common_tool_name")
        return entries

    def _proposed_selection(self, initial, arguments, version, scope):
        axis_field = selection_fields(initial)[0]
        if version == LEGACY_SELECTION_VERSION:
            validate_schema(arguments, _LEGACY_REVISION_ARGUMENTS)
            return self._selection({'version': version, 'annotation_ref': initial[axis_field],
                'thought_ref': arguments['thought_ref'], 'tools': arguments['tools']})
        validate_schema(arguments, _REVISION_ARGUMENTS)
        return self._selection({'version': SELECTION_VERSION, 'evidence_axis': initial[axis_field],
            'thought_pattern': arguments['thought_pattern'], 'child_tool_info':
                self.tool_library.resolve_tool_info(arguments['child_tool_info'], self._information_catalog(scope))})

    def catalog(self, context):
        selection = self._original_selection(context)
        resolved = self._tool_resolution(context, selection)
        if selection['version'] != LEGACY_SELECTION_VERSION:
            direct = [row for row in resolved
                      if row.get('invocation_route', {'kind': 'direct'})['kind'] == 'direct']
            if self._closed_tool_resolution(context, selection) is not None:
                resolved = direct
            else:
                resolved = self.tool_library.resolve_invocations(
                    [{'name': row['name'], 'resources': row['resources']} for row in direct],
                    self.services.tool_catalog(context.scope))
        entries = [{key: deepcopy(value) for key, value in row.items()
                    if key not in {'instructions', 'invocation_route'}} for row in plain(resolved)]
        description = (
            "Prepare a pinned thought pattern and selected actual tools for a new child using the original "
            "scientific support and library. Return its selection for a separately selected episode_child "
            "commission with the child's job, scope, constraints and typed form. Copy result.selection "
            "and revision_origin into that assignment; request scientific_process_results in the form "
            "when process provenance and existing closed results are needed. Changes no current "
            "process, starts no child and records no biological observation. Supply the actual tool names "
            "returned by process.tools for the desired alternative investigation.")
        axis = self.library.resolve(selection[selection_fields(selection)[0]])
        if axis.get('entry_version') == INSTRUCTION_VERSION:
            description = (
                "Prepare a different thought pattern and/or selected actual tools for a new child "
                "investigating the same evidence axis. Return its selection for a separately selected "
                "episode_child commission with the child's job, scope, constraints and typed return "
                "form. Copy result.selection and revision_origin into that assignment. Changes no "
                "current process, starts no child and records no biological observation. Select the "
                "actual tool/resource choices returned by process.tools for the desired investigation.")
        entries.append({"name": "process.revise", "description": description,
            "input_schema": deepcopy(_LEGACY_REVISION_ARGUMENTS
                if selection['version'] == LEGACY_SELECTION_VERSION else _REVISION_ARGUMENTS)})
        if getattr(self.services, 'workflow', None) is not None and self.tool_library.supports_tool_info:
            from gene_annotation_episode.episodic_workflow.root.execution_planning import catalog
            entries.extend(catalog())
        return entries

    def common_tool_names(self, context):
        # Runtime applies this after adding its helpers, so retain selected
        # primitives and the child-selection preparation as well as retrieval.
        return (*_COMMON_TOOLS, *(entry["name"] for entry in self.catalog(context)))

    def decision_context(self, context, current_view):
        selection = self._original_selection(context)
        annotation, thought = (self.library.resolve(selection[key]) for key in selection_fields(selection)[:2])
        resolved = self._tool_resolution(context, selection)
        def selected_fields(entry, names):
            return {name: deepcopy(entry[name]) for name in names if name in entry}
        fields = selection_fields(selection)
        current = selection['version'] == SELECTION_VERSION
        assignment = plain(context.assignment)
        if current:
            assignment = {**assignment, 'selection': selector_selection(selection)}
        published = annotation.get('entry_version') == INSTRUCTION_VERSION
        if published:
            axis_view = instruction_view(annotation)
        elif annotation.get('entry_version') == EVIDENCE_AXIS_VERSION:
            axis_view = evidence_axis_instruction_view(annotation)
        else:
            axis_view = selected_fields(annotation, ("id", "name", "description", "support"))
        return {"scientific_process": {"selection": selector_selection(selection),
            "initial_selection_sha256": scientific_digest(plain(context.assignment["selection"])),
            ('evidence_axis' if current else 'annotation'): axis_view,
            **({} if published else {"annotation_support_routes": self.services.scientific_support_routes(context,
                observation_kinds=support_observation_kinds(annotation))}),
            ('thought_pattern' if current else 'thought'): selected_fields(thought, ("id", "name", "description", "use_when",
                "live_alternatives", "decision_guidance", "outcome_contingencies", "boundary")),
            **({'child_tool_info': deepcopy(selection[fields[2]])} if current else {'tools': deepcopy(resolved)}),
            "assignment": assignment, "permitted_children": list(self.allowed_children(context,None))}}

    async def execute(self, context, tool_name, arguments, operation_key):
        self.validate_execution_context(context)
        selection = validate_selection(context.assignment['selection'])
        try:
            if not isinstance(operation_key, str) or not operation_key:
                raise ContractError("operation_key_required")
            entries = {entry["name"]: entry for entry in self.catalog(context)}
            if tool_name not in entries:
                raise ContractError("scientific_operation_unavailable")
            axis = self.library.resolve(selection[selection_fields(selection)[0]])
            if axis.get('id')=='A103' and tool_name=='sequence.align':
                raise ContractError('a103_new_sequence_comparison_requires_shared_parent')
            if axis.get('id')=='A104' and tool_name=='sequence.align':
                raise ContractError('a104_new_sequence_comparison_requires_shared_parent')
            arguments = _object(arguments, "scientific_arguments_invalid")
            validate_schema(arguments, entries[tool_name]["input_schema"])
            if tool_name == 'process.execution':
                from gene_annotation_episode.episodic_workflow.root.execution_planning import read
                return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
                        'result': read(self, context, arguments)}
            if tool_name == 'sequence.align':
                self.services.authenticate_structure_alignment_operands(context, arguments)
            elif tool_name == 'execution.estimate' and arguments['tool'] == 'sequence.align':
                self.services.authenticate_structure_alignment_operands(context, arguments['arguments'])
            if tool_name in {'material.from_source', 'material.parse', 'material.read',
                             'source.read', 'source.locate'}:
                self.services.authenticate_source_byte_operands(context, tool_name, arguments)
            if tool_name == "process.revise":
                proposed = self._proposed_selection(selection, arguments, selection['version'], context.scope)
                self._tool_resolution(context, proposed)
                child_selection = validate_child_selection({
                    "version": "scientific_process_child_selection_v1",
                    "parent_selection_sha256": scientific_digest(selection),
                    "selection": proposed})
                operation_ref = identity("operation", {
                    "key": operation_key, "name": tool_name, "arguments": arguments})
                origin = validate_revision_origin({"version": "scientific_process_revision_origin_v1",
                    "parent_invocation_ref": scientific_invocation_ref(context.run_id, context.path),
                    "preparation_operation_ref": operation_ref})
                return {"status": "completed", "operation_ref": operation_ref,
                    "record_refs": [], "changed_record_refs": [], "result": child_selection,
                    "revision_origin": origin, "feedback": None}
        except ValueError as error:
            return {"status": "invalid", "operation_ref": identity("operation", {
                "key": operation_key, "name": tool_name}), "record_refs": [],
                "changed_record_refs": [], "result": None,
                "feedback": {"category": "arguments_or_reference", "code": str(error),
                    **({"detail": error.detail} if getattr(error, "detail", None) else {})}}
        outcome = self.services.execute_tool(tool_name, arguments,
            scope=context.scope, operation_key=operation_key,
            **({'permitted_record_refs': context.received_record_refs}
               if tool_name.startswith(('structure.','context.','phylogeny.','partner.','chemistry.')) or tool_name in {'reference.neighborhood','result.blast.hsp', 'source.locate',
                   'find_restriction_sites', 'find_restriction_enzymes'} else {}))
        return await outcome if inspect.isawaitable(outcome) else outcome

