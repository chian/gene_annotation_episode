from __future__ import annotations
from .source_contracts import (Mapping, deepcopy, hashlib, inspect, json, Path, re, ReportBoundaryError, interpretation_schema, plain, validate_closed_schema, validate_form, ContractError, identity, obj, validate_schema, reference_in_context, scientific_digest, scientific_invocation_ref, validate_child_selection, validate_filled_process, validate_option_ref, validate_revision_origin, validate_selection, selection_fields, selector_selection, SELECTION_VERSION, build_process_result, merge_process_results, report_sources, validate_process_result, SUPPORT_ENTRY_VERSION, support_observation_kinds, validate_support_entry, EVIDENCE_AXIS_VERSION, validate_evidence_axis_entry, INSTRUCTION_VERSION, instruction_view, validate_instruction_entry, evidence_axis_instruction_view, alignment_site_fact_sources, requested_site_projections, project_site_action_return, validate_frozen_site_return, restriction_mapping_fact_sources, requested_restriction_projections, project_restriction_action_return, validate_frozen_restriction_return, molecular_fact_sources, merge_molecular_facts, requested_molecular_fact_sources, requested_molecular_fact_fields, validate_frozen_molecular_return, PROTEIN_ACTION_FACT_SOURCES, protein_structure_action_fact_sources, merge_protein_structure_action_facts, requested_protein_structure_action_fields, validate_frozen_protein_structure_action_return, VERSION, ROLE, ROLES, _COMMON_TOOLS, _REFERENCE, _SHA256, _SCIENTIFIC_NAMESPACES, _ITC_PARAMETER_SOURCE, _ANNOTATION_REF, _EVIDENCE_AXIS, _THOUGHT_REF, _TOOL_SELECTOR, _TOOL_INFO, _SELECTION, _CANONICAL_SELECTION, _REVISION_ORIGIN, _EVIDENCE_TASK, _ASSIGNMENT, _RECORDED_ASSIGNMENT, _REVISION_ARGUMENTS, original_axis_task_projector, _object, _ref_schema)

class ScientificGoal:

    def instructions(self, context):
        self.validate_context(context)
        selection = context.assignment['selection']
        axis = self.library.resolve(selection[selection_fields(selection)[0]])
        axis_guidance = ("A101 owns sequence similarity evidence. For an NCBI BLAST search that may run "
            "remotely, use the configured Launch API job when available: submit once, return its "
            "execution_handoff_refs to this episode, and let a separately selected monitor or Results "
            "episode check that same RID. The handoff is operational progress, not homology evidence. "
            "If that RID is waiting and no useful A101 work remains, return the handoff reference and "
            "current credit to your parent so it can choose another evidence axis. Consider ClusteredNR "
            "(nr_clustered_seq) for an initial blastx search; choose the database for the scientific "
            "question and preserve the selected database in the original request.\n\n"
            if axis.get('id') == 'A101' else '')
        axis_guidance += ("A102 owns structural work only. Scientific descendants remain A102. "
            "Use available shared operations to send the immediate parent specific missing operands or useful "
            "received evidence. That parent chooses within its own options or relays the need upward. "
            "Reuse qualified retained alignments. "
            "Native comparison results automatically populate the A102 numerical sheet before credit inspection; "
            "unknown functional features do not erase measured native correspondence. "
            "Follow up for missing structural cells, preserve original scope and model uncertainty, "
            "and distinguish fold resemblance from exact function. Novel folding requires an explicit configured "
            "remote/API/HPC binding; use structure.model_request when it is missing.\n\n"
            if axis.get('id') == 'A102' else '')
        if axis.get('id') == 'A102':
            from gene_annotation_episode.episodic_workflow.root.a102.a102_structural_evidence import is_merged_entry
            if is_merged_entry(axis):
                # The complete selected entry below owns both structural paths.
                axis_guidance = ('A102 owns comparative and experimental structural evidence. '
                    'Scientific descendants remain A102. Use either path or both as useful, '
                    'and return their separate scientific quantities and shared dependencies.\n\n')
        if axis.get('id') == 'A103':
            axis_guidance = ('A103 owns gene-context work. Scientific descendants remain A103. '
                'Use available shared operations to send the immediate parent specific missing operands or '
                'useful received evidence; that parent chooses within its own options or relays the need upward. '
                'Context measurements are automatically graded at publication/receipt. '
                'Each target/locus, neighboring component, domain and regulatory footprint retains its own attribution. '
                'An identity score, source label or fetched record alone is not an association score. Unknown flanks '
                'and unevaluated detections are not absence. Preserve optional modules, paralogs and related sampling. '
                'Use one small local job at a time, current resource_context and admission feedback. '
                'Root/owner credit comes from actual measured context, not narrative judgments.\n\n')
        if axis.get('id') in {'A107', 'A110'}:
            from gene_annotation_episode.episodic_workflow.root.library.component_investigation_instructions import INSTRUCTIONS
            axis_guidance = (INSTRUCTIONS[axis['id']] + '\n\nScientific descendants remain '
                + axis['id'] + '. Use available shared operations for specific parent information needs '
                'or useful received findings. The immediate parent chooses within its own options or relays '
                'the need upward; publication does not commission work or promise a reply. '
                'Preserve named scientific components separately from controller progress.\n\n')
        if axis.get('entry_version') == INSTRUCTION_VERSION:
            return (
                axis_guidance + "Determine what the supplied target does within the parent's assigned question, scope "
                "and constraints. Start with the supplied sequence, selected file contents or snippets, "
                "preserving their boundaries, completeness and known context. No initial candidate "
                "annotation or publicly searchable name is required. Possible functions can emerge "
                "from the evidence and be compared or revised. Apply the complete selected investigation "
                "instructions and thought-pattern guidance on every decision. Use actual outcomes and "
                "received child results to choose and revise your approach. Selected instructions "
                "describe how to investigate; they are not evidence about this target. Preserve the "
                "measured subject, conditions, controls, native measurements, uncertainty and limits of "
                "inference when interpreting evidence. Missing information remains unknown.\n\n"
                "Choose an available tool action, commit a scientific interpretation through the "
                "reasoning action, commission a scoped child with its own typed return form, or wait "
                "for selected pending work when that informs the investigation. Use only the selected "
                "actual tools and their supplied resource instructions; choose callable operands "
                "through the declared response contract. Preserve the parent's exact requested result "
                "meanings and allowed values. Recorded facts come from actual records. Keep inherited "
                "information distinct from new findings and completed work distinct from attempts. "
                "Return valid partial findings and specific failures through the requested form.\n\n"
                "Keep the assigned evidence axis, thought pattern and selected tools for this episode. "
                "process.revise prepares a different thought pattern and/or tool selection for a new "
                "child; it does not change this episode or start that child. To commission that "
                "alternative, copy its selection and revision_origin into a separately selected child "
                "assignment with the child's job, scope, constraints and typed return. Children own "
                "their iterative choices. The configured controller "
                "owns continuation. Waiting and unchanged observations do not manufacture progress.")
        return ("Investigate the parent's assigned scientific problem iteratively in the shared Episode loop. "
            "The selected scientific support proposition and operands define the support problem; "
            "the thought pattern supplies alternatives "
            "and outcome-sensitive guidance; the selected real tools supply their exact callable contracts. "
            "Choose your own actions using actual outcomes and received child forms. The selection is no "
            "prescribed sequence or automatic compatibility verdict. Library sources are instruction "
            "provenance, not scientific evidence about this target. Inspect actual source subjects, "
            "conditions and target applicability before interpreting evidence. annotation_support_routes "
            "describes the actual separately bound annotation policy's kind dispatch. An unmapped kind "
            "has no base-axis mapping in that known policy. Unavailable metadata means this reader cannot "
            "declare the bound policy; it is no verdict on evidence or the actual score. Metadata itself "
            "earns no credit and never replaces or filters the actual projectors, annotation formula or "
            "continuation rule. Keep the parent's objective, scope, constraints "
            "and exact typed form; support metadata never adds form fields or scoring axes. Use common reasoning "
            "to commit scientific interpretations. Keep the originally assigned scientific support, "
            "thought pattern and selected tool set throughout this episode. Explicit process.revise prepares "
            "a selection for a new child; a separately selected episode_child action commissions that "
            "child with its own job, scope, constraints and typed return form. Preparation changes no "
            "current process and starts no child. Copy both result.selection and revision_origin into "
            "that child's assignment to identify it as an alternative approach. Request the recorded "
            "scientific_process_results source in child forms when their process relationships and "
            "existing closed credit/yield are needed for steering. Only retrieved actual tools are available; "
            "their descriptions do not grant execution. The configured controller owns continuation.")

