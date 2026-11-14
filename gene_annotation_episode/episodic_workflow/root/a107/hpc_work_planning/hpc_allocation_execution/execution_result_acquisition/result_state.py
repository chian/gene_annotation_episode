"""Private A107 Results result_state"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.a107_blast_execution import BLAST_GRADED_RETURN_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a107.a107_blast_execution import BLAST_GRADED_RETURN_SOURCE
from .binding_roles import ROLE_KINDS
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain

class ResultsResultState:

    def initialize(self, context):
        if self.local_file_sources.applies(context):
            target = self._target(context)
            self.local_file_sources.selector(plain(context.assignment), target, validate_paths=False)
            return self._result_directory(context)
        target = self._target(context)
        self._selector(plain(context.assignment), target)
        required = self._blast_target_requirement(target, context.scope)
        if required is not None:
            schema = plain(context.request)['report_contract']['measurements']['schema']
            if not any((node.get('x-source') == BLAST_GRADED_RETURN_SOURCE and node == BLAST_GRADED_RETURN_SCHEMA for node in schema.get('properties', {}).values())):
                raise ValueError('blast_grader_typed_return_required')
        if self._masking_selector(plain(context.assignment)) or self._utility_selector(plain(context.assignment)) or self._expression_nmf_selector(plain(context.assignment)):
            self.initial_references(context)
        if target['resource_kind'] == 'api':
            return self.api_execution.initialize(context)
        self._result_directory(context)
