from __future__ import annotations
from .source_contracts import (Mapping, deepcopy, hashlib, inspect, json, Path, re, ReportBoundaryError, interpretation_schema, plain, validate_closed_schema, validate_form, ContractError, identity, obj, validate_schema, reference_in_context, scientific_digest, scientific_invocation_ref, validate_child_selection, validate_filled_process, validate_option_ref, validate_revision_origin, validate_selection, selection_fields, selector_selection, SELECTION_VERSION, build_process_result, merge_process_results, report_sources, validate_process_result, SUPPORT_ENTRY_VERSION, support_observation_kinds, validate_support_entry, EVIDENCE_AXIS_VERSION, validate_evidence_axis_entry, INSTRUCTION_VERSION, instruction_view, validate_instruction_entry, evidence_axis_instruction_view, alignment_site_fact_sources, requested_site_projections, project_site_action_return, validate_frozen_site_return, restriction_mapping_fact_sources, requested_restriction_projections, project_restriction_action_return, validate_frozen_restriction_return, molecular_fact_sources, merge_molecular_facts, requested_molecular_fact_sources, requested_molecular_fact_fields, validate_frozen_molecular_return, PROTEIN_ACTION_FACT_SOURCES, protein_structure_action_fact_sources, merge_protein_structure_action_facts, requested_protein_structure_action_fields, validate_frozen_protein_structure_action_return, VERSION, ROLE, ROLES, _COMMON_TOOLS, _REFERENCE, _SHA256, _SCIENTIFIC_NAMESPACES, _ITC_PARAMETER_SOURCE, _ANNOTATION_REF, _EVIDENCE_AXIS, _THOUGHT_REF, _TOOL_SELECTOR, _TOOL_INFO, _SELECTION, _CANONICAL_SELECTION, _REVISION_ORIGIN, _EVIDENCE_TASK, _ASSIGNMENT, _RECORDED_ASSIGNMENT, _REVISION_ARGUMENTS, original_axis_task_projector, _object, _ref_schema)

class ScientificReferences:
    def initial_references(self, context):
        if context.role != ROLE:
            return []
        self.validate_context(context)
        return list(dict.fromkeys([*context.assignment["evidence_refs"],
            *([context.assignment['proposed_annotation_ref']]
              if context.assignment.get('proposed_annotation_ref') else [])]))

    def received_form_references(self, context, form, schema, operation_key):
        from gene_annotation_episode.episodic_workflow.root.protein_structure_action_records import protein_structure_action_form_references
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_result_contracts import validate_macs2_peak_return
        from gene_annotation_episode.episodic_workflow.root.library.homer_motif_result_contracts import validate_homer_motif_return
        from gene_annotation_episode.episodic_workflow.root.library.tf_binding_result_contracts import validate_tf_binding_return
        from gene_annotation_episode.episodic_workflow.root.library.protease_kinetics_result_contracts import validate_ordinary_protease_kinetics_return
        from gene_annotation_episode.episodic_workflow.root.library.arsenic_speciation_result_contracts import validate_ordinary_arsenic_return
        from gene_annotation_episode.episodic_workflow.root.library.protein_disorder_result_contracts import validate_ordinary_disorder_return
        from gene_annotation_episode.episodic_workflow.root.library.protein_conservation_result_contracts import validate_conservation_return
        from gene_annotation_episode.episodic_workflow.root.library.protein_phylogeny_result_contracts import validate_phylogeny_return
        from gene_annotation_episode.episodic_workflow.root.library.esm_gene_embedding_contracts import validate_esm_embedding_return
        from gene_annotation_episode.episodic_workflow.root.library.somatic_variant_contracts import validate_somatic_return
        from gene_annotation_episode.episodic_workflow.root.library.vcf_result_measurements import validate_vcf_return
        from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_result_contracts import validate_ordinary_molecular_sequence_return
        from gene_annotation_episode.episodic_workflow.root.library.primer_placement_result_contracts import validate_ordinary_primer_placement_return
        form, schema = plain(form), plain(schema)
        references = protein_structure_action_form_references(form, schema)
        for field in requested_molecular_fact_fields(schema, fact_source='somatic_variant_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('somatic_variant_return_array_required')
            references.extend(validate_somatic_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='esm_gene_embedding_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('esm_gene_embedding_return_array_required')
            references.extend(validate_esm_embedding_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='protein_conservation_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('protein_conservation_return_array_required')
            references.extend(validate_conservation_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='protein_phylogeny_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('protein_phylogeny_return_array_required')
            references.extend(validate_phylogeny_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='arsenic_speciation_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('arsenic_speciation_return_array_required')
            references.extend(validate_ordinary_arsenic_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='protein_disorder_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('protein_disorder_return_array_required')
            references.extend(validate_ordinary_disorder_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='vcf_result_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('vcf_result_return_array_required')
            references.extend(validate_vcf_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='macs2_peak_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('macs2_peak_return_array_required')
            references.extend(validate_macs2_peak_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='homer_motif_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('homer_motif_return_array_required')
            references.extend(validate_homer_motif_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='tf_binding_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('tf_binding_return_array_required')
            references.extend(validate_tf_binding_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='protease_kinetics_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('protease_kinetics_return_array_required')
            references.extend(validate_ordinary_protease_kinetics_return(value)['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='n_glycosylation_motif_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('ordinary_n_glycosylation_return_array_required')
            references.extend(validate_ordinary_molecular_sequence_return(value,
                operation='find_n_glycosylation_motifs')['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='o_glycosylation_hotspot_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('ordinary_o_glycosylation_return_array_required')
            references.extend(validate_ordinary_molecular_sequence_return(value,
                operation='predict_o_glycosylation_hotspots')['source_ref'] for value in form[field])
        for field in requested_molecular_fact_fields(schema, fact_source='primer_placement_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('ordinary_primer_placement_return_array_required')
            references.extend(validate_ordinary_primer_placement_return(value)['source_ref'] for value in form[field])
        return list(dict.fromkeys(references))

    def resolve_received_reference(self, context, reference, namespace):
        # This registry port also runs for the actual receiving parent's role.
        # It precedes generic Store fallback and grants only proved names.
        if namespace == 'restriction_enzyme':
            return self.services.restriction_mapping_reference(context, reference, namespace)
        callback = getattr(self.services, 'protein_structure_reference_access', None)
        return callback(context, reference, namespace) if callable(callback) else None


