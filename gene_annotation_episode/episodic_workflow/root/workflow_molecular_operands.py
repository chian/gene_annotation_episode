"""Root host ports defined by WorkflowMolecularOperands."""
from __future__ import annotations
import json
from .communication import plain
from .receiving_context import BindingContext

class WorkflowMolecularOperands:

    def read_received_molecular_input(self, context, reference, namespace, *, tag_key=None, file_format=None, source_metadata_only=False, subject_metadata_only=False):
        """Read one selected admitted representation through the shared owner."""
        if type(source_metadata_only) is not bool or type(subject_metadata_only) is not bool or sum((tag_key is not None, file_format is not None, source_metadata_only, subject_metadata_only)) != 1 or (source_metadata_only and namespace != 'source'):
            raise ValueError('molecular_sequence_input_invalid_selection')
        binding = self._molecular_input_binding()
        if source_metadata_only:
            return binding.read_received_source(context, reference)
        if subject_metadata_only:
            return binding.read_received_subject(context, reference, namespace)
        if file_format is not None:
            return binding.read_received_file(context, reference, namespace, file_format=file_format)
        return binding.read_received(context, reference, namespace, tag_key=tag_key)

    def _molecular_input_binding(self):
        from types import SimpleNamespace
        from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_input_bindings import MolecularSequenceInputBindings

        def resolve(current, selected, selected_namespace):
            verdict = self._molecular_reference_access(current, selected, selected_namespace)
            return verdict if verdict is not None else self.workflow.episode_bindings.resolve_received_reference(current, selected, selected_namespace)
        owner = SimpleNamespace(store=self.workflow.store, run_id=self.workflow.run_id, resolve_received_reference=resolve, commission_assignment_matches=self.molecular_commission_assignment_matches)
        return MolecularSequenceInputBindings(owner)

    def read_received_molecular_file_metadata(self, context, reference, namespace, *, file_format):
        """Authenticate current File receipt metadata without opening bytes."""
        return self._molecular_input_binding().read_received_file_metadata(context, reference, namespace, file_format=file_format)

    def molecular_commission_assignment_matches(self, parent, child, selected_action, *, decision_index):
        """Authenticate original selectors against their frozen host ToolInfos.

        Input inspection does not reconstruct today's invocation binding. Only
        the exact recorded commission and its immutable library can explain a
        selector→canonical-body difference in the saved child assignment.
        """
        from copy import deepcopy
        from .episode_return_records import EpisodeReturnRecords
        from .scientific_process_records import SELECTION_VERSION, scientific_digest, validate_filled_process, validate_selection
        try:
            if type(decision_index) is not int or decision_index < 0 or parent.run_id != self.workflow.run_id or (child.run_id != parent.run_id) or (child.role != 'scientific_process') or (child.path != (*parent.path, ('scientific_process', f'child_{decision_index}'))) or (selected_action.get('kind') != 'episode_child') or (selected_action.get('role') != child.role):
                return False
            records = EpisodeReturnRecords(self.workflow.store, self.workflow.run_id, failure_prefix='molecular_commission_')
            records.authenticate(parent)
            records.authenticate(child)
            row = self.workflow.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (parent.run_id, parent.episode_id, decision_index)).fetchone()
            if row is None or not records._equal(json.loads(row['action']), selected_action):
                return False
            request = plain(child.request)
            if not records._equal(selected_action.get('scope'), child.scope) or selected_action.get('goal') != request['goal']['objective']:
                return False
            binding = self.workflow.scientific_process_binding
            if binding is None:
                return False
            filled = validate_filled_process(request['message']['scientific_process'])
            mechanics = filled['mechanics_binding']
            configuration = mechanics['configuration']
            if mechanics.get('binding_id') != child.role or not records._equal(configuration['library'], binding._library_record) or (not records._equal(configuration['tool_library'], binding._tools_record)):
                return False
            expected = deepcopy(selected_action['assignment'])
            if expected['selection'].get('version') != SELECTION_VERSION:
                return False
            expected['selection']['child_tool_info'] = binding.tool_library.resolve_tool_info(expected['selection']['child_tool_info'], available_catalog=None)
            expected['selection'] = validate_selection(expected['selection'])
            for name in ('evidence_axis', 'thought_pattern'):
                binding.library.resolve(expected['selection'][name])
            initial = json.loads(selected_action['initial_report_json'])
            contract = request['report_contract']
            invocation = dict(objective=selected_action['goal'], scope=plain(child.scope), purpose=selected_action['purpose'], report_schema=contract['measurements']['schema'], initial_report=initial)
            return records._equal(expected, child.assignment) and records._equal(filled['selection'], expected['selection']) and records._equal(initial, request['message']['initial_report']) and (selected_action['purpose'] == contract['decision']) and (filled['assignment_sha256'] == scientific_digest(expected)) and (filled['invocation_sha256'] == scientific_digest(invocation))
        except (ValueError, TypeError, KeyError, AttributeError, OSError):
            return False

    def _molecular_reference_access(self, context, reference, namespace):
        owner = getattr(self.workflow.tools, 'retained_molecular_reference_access', None)
        return owner(context, reference, namespace, initial_record_refs=self.workflow.initial_known_record_refs or ()) if callable(owner) else None

    def authenticate_source_byte_operands(self, context: BindingContext, tool_name: str, arguments: dict) -> None:
        """Preserve utility artifact grants at the selected source/material read."""
        from gene_annotation_episode.domain import ContractError
        from gene_annotation_episode.materials import source_window_selection
        from gene_annotation_episode.episodic_workflow.root.library.native_blast_utility_contracts import BUNDLE_VERSION
        from gene_annotation_episode.source_locations import received_source
        if context.run_id != self.workflow.run_id:
            raise ContractError('source_byte_context_run_mismatch')
        store = self.workflow.store
        if tool_name in {'material.parse', 'material.read'}:
            material = store._require(arguments['material_ref'], {'material'})
            source = store._require(material['source_ref'], {'source'})
        else:
            source = store._require(arguments['source_ref'], {'source'})
        if tool_name == 'source.read':
            artifact_ref, _, _ = source_window_selection(source, arguments.get('representation', 'text'))
        elif tool_name == 'source.locate':
            artifact_ref = received_source(store, source['id'], arguments['representation'], permitted_inputs=context.received_record_refs, scope=plain(context.scope))['id']
        else:
            artifact_ref = source['artifact_ref']
        if self._molecular_reference_access(context, artifact_ref, 'artifact') is False:
            raise ContractError('molecular_source_artifact_not_granted')
        try:
            owner = self.workflow.episode_bindings.for_role('results')
        except LookupError:
            owner = None
        results = getattr(owner, 'native_blast_utility_results', None)
        if results is not None:
            allowed = results.retained_reference_access(context, artifact_ref, 'artifact')
            if allowed is False:
                raise ContractError('native_blast_utility_source_artifact_not_granted')
        elif source.get('provider') == 'episode.execution_result' and source.get('version') == BUNDLE_VERSION:
            raise ContractError('native_blast_utility_source_artifact_not_granted')

