from __future__ import annotations
from .source_contracts import (Mapping, deepcopy, hashlib, inspect, json, Path, re, ReportBoundaryError, interpretation_schema, plain, validate_closed_schema, validate_form, ContractError, identity, obj, validate_schema, reference_in_context, scientific_digest, scientific_invocation_ref, validate_child_selection, validate_filled_process, validate_option_ref, validate_revision_origin, validate_selection, selection_fields, selector_selection, SELECTION_VERSION, build_process_result, merge_process_results, report_sources, validate_process_result, support_observation_kinds, EVIDENCE_AXIS_VERSION, validate_evidence_axis_entry, INSTRUCTION_VERSION, instruction_view, validate_instruction_entry, evidence_axis_instruction_view, alignment_site_fact_sources, requested_site_projections, project_site_action_return, validate_frozen_site_return, restriction_mapping_fact_sources, requested_restriction_projections, project_restriction_action_return, validate_frozen_restriction_return, molecular_fact_sources, merge_molecular_facts, requested_molecular_fact_sources, requested_molecular_fact_fields, validate_frozen_molecular_return, PROTEIN_ACTION_FACT_SOURCES, protein_structure_action_fact_sources, merge_protein_structure_action_facts, requested_protein_structure_action_fields, validate_frozen_protein_structure_action_return, VERSION, ROLE, ROLES, _COMMON_TOOLS, _REFERENCE, _SHA256, _SCIENTIFIC_NAMESPACES, _ITC_PARAMETER_SOURCE, _EVIDENCE_AXIS, _THOUGHT_REF, _TOOL_SELECTOR, _TOOL_INFO, _SELECTION, _CANONICAL_SELECTION, _REVISION_ORIGIN, _EVIDENCE_TASK, _ASSIGNMENT, _RECORDED_ASSIGNMENT, _REVISION_ARGUMENTS, original_axis_task_projector, _object, _ref_schema)

from .report_reference_access import ScientificReportReferenceAccess

class ScientificReportValidation(ScientificReportReferenceAccess):
    def _validate_structural_report(self, context, form, schema):
        from dataclasses import replace
        from gene_annotation_episode.episodic_workflow.root.a102.a102_structural_evidence import is_merged_entry
        from gene_annotation_episode.episodic_workflow.root.a102.a102_structural_report import is_structural_report_schema, resolve_report
        from gene_annotation_episode.episodic_workflow.root.a102.domain import ContractError as A102ContractError
        if not is_structural_report_schema(schema):
            return
        axis = self.library.reference('A102')
        if not is_merged_entry(self.library.resolve(axis)):
            raise ContractError('a102_merged_structural_evidence_catalog_required')
        if context.role == ROLE:
            selection = self._original_selection(context)
            if selection[selection_fields(selection)[0]] != axis:
                raise ContractError('a102_structural_report_requires_merged_axis')
        workflow = getattr(self.services, 'workflow', None)
        if workflow is None:
            raise ContractError('a102_report_store_required')
        # C4 can retain a commission-time context while the child acquires new
        # evidence. Refresh only this reporting episode's actual durable set.
        selected = self.services.record_selection(context)
        if selected.get('run_id') != context.run_id or selected.get('episode_id') != context.episode_id:
            raise ContractError('a102_report_receiver_mismatch')
        current = replace(context, received_record_refs=tuple(selected['known_record_refs']))
        try:
            resolve_report(workflow.store, plain(form), context=current,
                structure_repository=self.services.literature_structure_repository())
        except (ContractError, A102ContractError) as error:
            fields = {'a102_comparative_status_differs_from_delivered_evidence': 'comparative_status',
                'a102_experimental_status_differs_from_delivered_evidence': 'experimental_status'}
            if str(error) not in fields:
                raise
            raise ReportBoundaryError('A102 interpretation requires its delivered structural evidence',
                code=str(error), field=fields[str(error)]) from error

    def _validate_component_axis_report(self, context, form, schema):
        from dataclasses import replace
        from gene_annotation_episode.episodic_workflow.root.library.component_received_reports import report_axis
        from .received_component_reports import resolve_report
        from gene_annotation_episode.episodic_workflow.root.a107.domain import ContractError as A107ContractError
        from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError as A110ContractError
        axis = report_axis(schema)
        if axis is None:
            return
        if context.role == ROLE:
            selected = self._original_selection(context)
            if selected[selection_fields(selected)[0]]['option_id'] != axis:
                raise ContractError('component_axis_report_requires_original_axis')
        workflow = getattr(self.services, 'workflow', None)
        if workflow is None:
            raise ContractError('component_axis_report_store_required')
        received = self.services.record_selection(context)
        if received.get('run_id') != context.run_id or received.get('episode_id') != context.episode_id:
            raise ContractError('component_axis_report_receiver_mismatch')
        current = replace(context, received_record_refs=tuple(received['known_record_refs']))
        try:
            resolve_report(workflow.store, plain(form), context=current, services=self.services, axis=axis)
        except (ContractError, A107ContractError, A110ContractError) as error:
            raise ReportBoundaryError('The axis report requires its actual received component evidence',
                code=str(error)) from error

    def _validate_molecular_report(self, context, form, schema):
        for source in requested_molecular_fact_sources(plain(schema)):
            fields = requested_molecular_fact_fields(plain(schema), fact_source=source)
            label, missing_code = {
                _ITC_PARAMETER_SOURCE: ('ITC parameter', 'itc_parameter_facts_not_frozen'),
                'liftover_point_mappings': ('point-liftover', 'liftover_facts_not_frozen'),
                'circular_dichroism_summaries': ('CD summary', 'circular_dichroism_facts_not_frozen'),
                'orf_measurements': ('ORF measurement', 'ordinary_orf_facts_not_frozen'),
                'n_glycosylation_motif_outcomes': ('literal N-glycosylation motif', 'ordinary_n_glycosylation_facts_not_frozen'),
                'o_glycosylation_hotspot_outcomes': ('S/T-density candidate', 'ordinary_o_glycosylation_facts_not_frozen'),
                'primer_placement_outcomes': ('literal primer placement', 'primer_placement_facts_not_frozen'),
                'reference_edit_outcomes': ('reference editing outcome', 'reference_edit_outcome_facts_not_frozen'),
                'macs2_peak_outcomes': ('native MACS2 peak measurement', 'macs2_peak_facts_not_frozen'),
                'homer_motif_outcomes': ('native HOMER motif measurement', 'homer_motif_facts_not_frozen'),
                'tf_binding_outcomes': ('native TF score measurement', 'tf_binding_facts_not_frozen'),
                'protease_kinetics_outcomes': ('protease kinetics measurement', 'protease_kinetics_facts_not_frozen'),
                'arsenic_speciation_outcomes': ('arsenic speciation measurement', 'arsenic_speciation_facts_not_frozen'),
                'protein_disorder_outcomes': ('protein disorder measurement', 'protein_disorder_facts_not_frozen'),
                'protein_conservation_outcomes': ('literal conservation', 'protein_conservation_facts_not_frozen'),
                'protein_phylogeny_outcomes': ('native protein phylogeny', 'protein_phylogeny_facts_not_frozen'),
                'somatic_variant_outcomes': ('native somatic variant', 'somatic_variant_facts_not_frozen'),
                'esm_gene_embedding_outcomes': ('ESM representation', 'esm_gene_embedding_facts_not_frozen'),
                'vcf_result_outcomes': ('retained VCF result', 'vcf_result_facts_not_frozen'),
            }[source]
            try:
                frozen = self.services.molecular_frozen_facts(context, fact_source=source)
                if frozen is None:
                    raise ValueError(missing_code)
                validate_frozen_molecular_return(plain(form), plain(schema), frozen, fact_source=source)
            except ReportBoundaryError:
                raise
            except ValueError as error:
                raise ReportBoundaryError(f'Return differs from the frozen {label} facts',
                    code=str(error), field=fields[0]) from error

    def _validate_protein_structure_action_report(self, context, form, schema):
        for source in PROTEIN_ACTION_FACT_SOURCES:
            fields = requested_protein_structure_action_fields(plain(schema), fact_source=source)
            if not fields:
                continue
            try:
                frozen = self.services.protein_structure_action_frozen_facts(context, fact_source=source)
            except ValueError as error:
                raise ReportBoundaryError('Original protein action facts unavailable',
                    code=str(error), field=fields[0]) from error
            validate_frozen_protein_structure_action_return(plain(form), plain(schema), frozen,
                fact_source=source)

    _validate_itc_parameter_report = _validate_molecular_report

    def validate_received_report(self, context, form, schema):
        # Scientific roles use their own validate_report branch. This hook also
        # runs for annotation receivers, without adding a new episode binding.
        if context.role == 'annotation':
            self._validate_molecular_report(context, form, schema)
            self._validate_protein_structure_action_report(context, form, schema)
            self._validate_structural_report(context, form, schema)
            self._validate_component_axis_report(context, form, schema)

    def validate_report(self, context, form, original_schema):
        self.validate_context(context)
        validate_form(form, original_schema, lambda reference, namespace:
            self.resolve(context, reference, namespace))
        self._validate_molecular_report(context, form, original_schema)
        self._validate_protein_structure_action_report(context, form, original_schema)
        self._validate_structural_report(context, form, original_schema)
        self._validate_component_axis_report(context, form, original_schema)
        from gene_annotation_episode.episodic_workflow.root.a102.a102_investigation import (report_schema as a102_report_schema,
            resolve_report as resolve_a102_report)
        if plain(original_schema) == a102_report_schema():
            workflow = getattr(self.services, 'workflow', None)
            if workflow is None:
                raise ContractError('a102_report_store_required')
            resolve_a102_report(workflow.store, plain(form), scope=plain(context.scope))
        from gene_annotation_episode.episodic_workflow.root.a103.a103_investigation import (
            measurement_report_schema as a103_measurement_report_schema,resolve_measurement_report)
        a103_axis=plain(context.assignment).get('selection',{}).get('evidence_axis',{}).get('option_id')=='A103'
        a103_fields=set(plain(original_schema).get('properties',{}))
        if a103_axis and a103_fields==set(a103_measurement_report_schema()['properties']):
            workflow=getattr(self.services,'workflow',None)
            if workflow is None:raise ContractError('a103_report_store_required')
            resolve_measurement_report(workflow.store,plain(form),scope=plain(context.scope))
        from gene_annotation_episode.episodic_workflow.root.a104.a104_investigation import (report_schema as a104_report_schema,
            resolve_report as resolve_a104_report)
        from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError as A104ContractError
        a104_axis = plain(context.assignment).get('selection', {}).get('evidence_axis', {}).get('option_id') == 'A104'
        if a104_axis and set(plain(original_schema).get('properties', {})) == set(a104_report_schema()['properties']):
            workflow = getattr(self.services, 'workflow', None)
            if workflow is None:
                raise ContractError('a104_report_store_required')
            try:
                resolve_a104_report(workflow.store, plain(form), scope=plain(context.scope))
            except (ContractError, A104ContractError) as error:
                interpretation_errors = {
                    'a104_report_numeric_credit_conflict': 'phylogenetic_credit',
                    'a104_native_tree_statement_requires_received_original_execution': 'phylogeny_status',
                    'a104_placement_statement_requires_native_measurement': 'phylogeny_status',
                    'a104_history_statement_requires_actual_two_tree_comparison': 'phylogeny_status',
                    'a104_history_agreement_requires_supported_native_comparison': 'history_interpretation',
                    'a104_discordance_statement_requires_native_comparison': 'history_interpretation',
                    'a104_function_clade_requires_exact_characterized_reference_links': 'function_scope',
                    'a104_mixed_function_statement_requires_characterized_members': 'function_scope',
                    'a104_function_statement_requires_explicit_hypothesis_and_assessment': 'function_scope'}
                interpretation_errors.update({
                    'a104_function_hypothesis_requires_original_target': 'hypothesis_refs',
                    'a104_function_statement_requires_corresponding_assessment_relation': 'assessment_refs'})
                if str(error) not in interpretation_errors:
                    raise
                raise ReportBoundaryError('A104 interpretation requires the particular native evidence and attribution',
                    code=str(error), field=interpretation_errors[str(error)]) from error
        fields = [name for name, node in plain(original_schema)["properties"].items()
                  if node.get("x-source") == "scientific_process_results"]
        projections = requested_site_projections(plain(original_schema))
        if projections:
            try:
                frozen_sites = self.services.alignment_site_frozen_facts(context,
                    sources=tuple(projections))
            except ValueError as error:
                raise ReportBoundaryError('Original site results unavailable',
                    code=str(error)) from error
            validate_frozen_site_return(plain(form), plain(original_schema), frozen_sites)
        restrictions = requested_restriction_projections(plain(original_schema))
        if restrictions:
            try:
                frozen = self.services.restriction_mapping_frozen_facts(context,
                    sources=tuple(restrictions))
            except ValueError as error:
                raise ReportBoundaryError('Original restriction results unavailable',
                    code=str(error)) from error
            validate_frozen_restriction_return(plain(form), plain(original_schema), frozen)
        if not fields:
            return
        # The child's source was frozen before the existing admission callback.
        # Comparing it here also protects the blocking and redelivery paths;
        # no closure quantity is recomputed while validating a returned form.
        try:
            read_frozen = getattr(self.services, "scientific_frozen_results", None)
            if not callable(read_frozen):
                raise ValueError("scientific_frozen_results_unavailable")
            frozen = read_frozen(context)
        except ValueError as error:
            raise ReportBoundaryError("Original process results unavailable",
                code=str(error), field=fields[0]) from error
        for name in fields:
            values = plain(form)[name]
            try:
                for value in values:
                    validate_process_result(value, library=self.library, tool_library=self.tool_library)
                if frozen is None or scientific_digest(values) != scientific_digest(frozen):
                    raise ValueError("scientific_process_result_source_mismatch")
            except ValueError as error:
                raise ReportBoundaryError("Return differs from the original process result",
                    code=str(error), field=name) from error

