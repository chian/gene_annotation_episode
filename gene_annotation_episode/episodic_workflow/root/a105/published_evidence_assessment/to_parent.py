from __future__ import annotations
'Private to parent responsibility for literature.'
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.source_contracts import ROLES, deepcopy, plain, reference_in_context, replace, validate_form
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError

class LiteratureReport:

    def fact_sources(self, role):
        self._role(role)
        from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.goal import SCREENING
        from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.credit import screening_schema
        from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.goal import LEADS
        from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.credit import lead_return_schema
        return {**(self._rate_fact_sources() if self.rate_population else {}), SCREENING: screening_schema(), LEADS: lead_return_schema()}

    def facts(self, context, completion_snapshot):
        self._role(context.role)
        from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.goal import SCREENING
        from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.credit import screening_answers
        from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.goal import LEADS
        from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.credit import lead_dispositions
        screening = {SCREENING: screening_answers(self.services.workflow.store, context)} if context.assignment.get('literature_task', {}).get('answer_kind') == 'screening' else {}
        if context.assignment.get('literature_task', {}).get('kind') == 'verified_source_leads':
            screening[LEADS] = lead_dispositions(self.services.workflow.store, context)
        if not self.rate_population:
            return screening
        return {**self._rate_facts(context, completion_snapshot['committed_record_refs']), **self.current_report_facts(context), **screening}

    def current_report_facts(self, context):
        if not self._enabled('assay_grading_population', context):
            return {}
        workflow = getattr(self.services, 'workflow', None)
        if workflow is None:
            return {}
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_sheet_updates import current_scoring_sheets
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_work_report import completed_work
        sheets = current_scoring_sheets(workflow.store, context)
        return {'literature_completed_work': completed_work(workflow.store, context), **({'literature_current_scoring_sheets': sheets} if sheets else {})}

    def _rate_fact_sources(self):
        if not self.rate_population:
            return {}
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_summary_precision_storage import SUMMARY_PRECISION_CELLS_SCHEMA_V1
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_product_coupling_storage import product_coupling_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_measurement_validation_storage import measurement_validation_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_calibration_recovery_storage import calibration_recovery_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_observation_storage import rate_observation_cells_schema, rate_grid_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_replicate_storage import rate_replicate_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_meaning_delivery import rate_source_meaning_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_domains import rate_source_domain_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_storage import rate_cells_schema, rate_source_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_quantity_storage import quantity_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_storage import assay_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_ratio_storage import ratio_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_storage import binding_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_model_storage import binding_model_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_transport_storage import transport_response_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_figure_storage import figure_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_amount_storage import amount_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_optical_storage import optical_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_storage import kinetic_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_model_storage import kinetic_model_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_interaction_model_storage import binding_interaction_model_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_interaction_storage import binding_interaction_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_endpoint_signal_storage import ENDPOINT_SIGNAL_CELLS_SCHEMA_V1, NAMESPACE as ENDPOINT_NAMESPACE
        result = {'literature_kinetic_summary_precision_cells': {'type': 'array', 'meaning': 'Exactly requested source/scenario precision cells for one kinetic summary with actual subject/context, units, physical versus estimator sampling basis, explicit conditions and precise unavailable reasons. Estimated random mean precision, dependent interval calculation parameters and source facts remain distinct. No unrequested operands, independent assay count or annotation credit.', 'report_schema': deepcopy(SUMMARY_PRECISION_CELLS_SCHEMA_V1)}, ENDPOINT_NAMESPACE: {'type': 'array', 'meaning': 'Exactly requested saved endpoint amplitudes, conditional correction fractions and variances. Preserve subject, endpoint, coexistence, finite window, correction stage/applicability, source origin, reading-versus-physical uncertainty and shared measurements. Unrequested source coordinates, amplitudes, caption results and covariance remain private; this is not initial-rate g, molecular attribution, function probability or annotation credit.', 'report_schema': deepcopy(ENDPOINT_SIGNAL_CELLS_SCHEMA_V1)}, 'literature_product_coupling_cells': {'type': 'array', 'meaning': 'Exactly requested saved product/cofactor numerical components with actual molecule, construct, preparation, endpoint and experimental relationships. Native reports, descriptive product-per-cofactor ratio, conditional physical fraction and original author-reported coupling remain distinct. Preserve reaction-account direction/status/model identity, shared measurements and dependent reconstruction; requested uncertainty carries source/owner/basis/origin/status provenance without raw covariance. No unrequested native operands, molecular attribution, independent replication, function probability, target transfer or annotation credit is inferred.', 'report_schema': product_coupling_cells_schema()}, 'literature_measurement_validation_cells': {'type': 'array', 'meaning': 'Exactly requested saved precision/control numerical sections, retaining every selected physical measurement and its actual alternative within/between basis. Reported statistics, deterministic re-expressions and supported versus conditional plug-in error components remain distinct, with analyte/matrix/endpoint/repetition, population and denominator meanings, original dependencies and shared contribution identities. A component request returns all its retained measurement instances in original order. No independent replication, product identity, function probability, target transfer or annotation credit is inferred.', 'report_schema': measurement_validation_cells_schema()}, 'literature_calibration_recovery_cells': {'type': 'array', 'meaning': 'Exactly requested saved recovery-control numerical components with actual control analyte, experiment/matrix/endpoint/blank/expected-basis meanings, reporter-standard versus enzyme-activity-spike scope, SD/SEM interpretation, reported-versus-displayed discrepancies and original measurement reuse. Recovery, bias and inverse share operands. Unknown applicability and denominator uncertainty remain unknown; no correction to another measurement, product identity, molecular attribution, function probability or annotation credit is inferred.', 'report_schema': calibration_recovery_cells_schema()}, 'literature_rate_observation_cells': {'type': 'array', 'meaning': 'Exactly requested source-native reported-entry descriptive means, SD/CV and selected functional contrasts. Preserve witnessed panel/subject/group/observation labels, unknown preparation grouping, actual entry/representation/point counts, shared and conflicting source-labelled identities, missing/censored roster and actual input origins. Native arithmetic uses only the selected same-source reporting convention; it establishes neither experimental comparability nor effect isolation. Physical unit conversion, method/blank/calibration/product attribution, preparation n, SE, corrected activity and annotation credit remain unknown.', 'report_schema': rate_observation_cells_schema()}, 'literature_rate_grid_cells': {'type': 'array', 'meaning': 'Exactly requested reported-curve precision scalars with only their named concentration context, actual source labels, native amount-rate units, distinct estimators, reporting denominators and fixed-coordinate sampling scope. Preserve conditional versus ordinary values, source conflicts, unknown physical preparation/published-estimate covariance, shared measurements and source versus implementation limitations. No full rate roster, fitted-parameter set or covariance matrix is delivered by a scalar request; no overall reliability grade or annotation credit.', 'report_schema': rate_grid_cells_schema()}, 'literature_rate_replicate_cells': {'type': 'array', 'meaning': 'Exactly requested raw-rate measurement components with actual source subject/experiment, selected versus observed groups, per-group sampling bases, actual measurement and unit counts, missing/censored/conflicting identities and selected dependence. Unit means receive equal weight after within-unit averaging. Descriptive SD and conditional SE are separate; grouping proves no biological independence. These dependent numerical views supply no assay specificity, error rate, function probability, target transfer or annotation credit.', 'report_schema': rate_replicate_cells_schema()}, 'literature_rate_cells': {'type': 'array', 'meaning': 'Saved source-preparation rate cells with measured subject/experiment retained in the referenced sheet. Conditional statistics are not annotation probabilities or target-transfer scores; unavailable operands remain null with reasons.', 'report_schema': rate_cells_schema()}, 'literature_rate_source_cells': {'type': 'array', 'meaning': "The same saved numerical rate components from native source spans, with each arm's actual subject/construct/preparation bindings and approximation retained. Source-supported conditional statistical assumptions do not establish causal isolation, target transfer or annotation credit. This closed native return view is distinct from the legacy table view, not a second scoring sheet.", 'report_schema': rate_source_cells_schema()}, 'literature_rate_source_domain_cells': {'type': 'array', 'meaning': 'The same saved native rate components with conditional logical enclosures of reported operands. Finite bounds, inclusivity, undefined denominators and outward numerical projection are explicit; range failure can qualify a still-useful partial enclosure. Status concerns the point estimate. Domains are not sampling confidence intervals, independence, endpoint co-attainability, target transfer or annotation credit. This is another closed return view of the same numerical sheet, not another assay.', 'report_schema': rate_source_domain_cells_schema()}, 'literature_rate_source_meaning_cells': {'type': 'array', 'meaning': "The same saved native numerical rate/domain rows with the exact recorded intended-change witness and each requested component's operand-role endpoint, normalization and rate-unit conversion meanings, including endpoint-specific source-defined unit definitions. Null means absent from the saved selection, not a demonstrated publication omission. Witnesses do not establish a blank, replacement, isolated effect, sufficiency or independence. No unrequested assay numbers or covariance are expanded. This optional closed return view adds no measurement, scoring component or annotation credit.", 'report_schema': rate_source_meaning_cells_schema()}, 'literature_quantity_cells': {'type': 'array', 'meaning': 'Saved single reported source quantities, with quantity and analyte identity. Untyped spread remains untyped. Source conditions, attribution and correction scores remain unknown where unsupported.', 'report_schema': quantity_cells_schema()}, 'literature_assay_cells': {'type': 'array', 'meaning': "Saved source-anchored assay interpretations and numerical operands/corrections. Endpoint and arrangement describe the episode's source interpretation. Known-normal indices remain conditional and are not function probabilities. Unknown operands remain null.", 'report_schema': assay_cells_schema()}, 'literature_ratio_cells': {'type': 'array', 'meaning': 'Reported comparative signal components with actual denominator/arrangement, received representation candidates and source origins. Conflicts are not sampling intervals. Calibration and functional response/uncertainty remain separate missing inputs.', 'report_schema': ratio_cells_schema()}, 'literature_binding_cells': {'type': 'array', 'meaning': 'Saved source binding-parameter components with actual protein/state/ligand comparison, uncertainty basis and reported-limit arithmetic. Limits are not confidence or true-parameter bounds; IC50 is not Kd. Missing inputs and unimplemented observation models remain explicit.', 'report_schema': binding_cells_schema()}, 'literature_binding_model_cells': {'type': 'array', 'meaning': 'Saved conditional source log-parameter contrast, full-covariance noise and signed likelihood/index components for test parameter exceeding reference. Known/estimated variance, actual censor mechanism and model origin stay explicit. Native reporting limits are not point observations or confidence bounds; these are not probabilities of function or target-transfer scores.', 'report_schema': binding_model_cells_schema()}, 'literature_transport_cells': {'type': 'array', 'meaning': 'Saved native concentrations and conditional same-curve kinetic-response components. condition_response is test substrate saturation divided by reference substrate saturation under the same fitted curve. Keep actual curve/preparation identities, Km uncertainty meaning and full covariance ownership. The response can divide an appropriate source effect once; it is not reliability or annotation credit. Missing or different curves remain unavailable.', 'report_schema': transport_response_cells_schema()}, 'literature_figure_cells': {'type': 'array', 'meaning': 'Saved native experimental graph ordinates and signed differences with both molecule/partner arms, endpoint/normalization, source representation relationships and repeat/spread meanings. Bounds describe conditional pixel digitization, not SD or confidence intervals. Coupled product or partner-swap differences do not establish upstream-only activity, partner necessity, target correspondence or annotation credit.', 'report_schema': figure_cells_schema()}, 'literature_amount_cells': {'type': 'array', 'meaning': "Saved A105 source amount components with both quantities' actual roles, preparation/stock, method, basis, qualification and covariance ownership. Target/total mass-fraction estimates differ from nominal molar arm comparisons. Conditional denominator conversion is not applied to a rate; uncertainty and unknown relationships remain explicit, without target correspondence or annotation credit.", 'report_schema': amount_cells_schema()}, 'literature_optical_cells': {'type': 'array', 'meaning': 'Saved projections of existing net_rate(q) and variance_net_rate(Vq) inputs for the source NADH-depletion endpoint, conditional on the selected optical relationships. Preserve actual subject/construct/preparation/conditions, source qualifications, local reuse and covariance ownership. This is not isolated product formation, recovery k, protein amount, corrected activity, target transfer, annotation credit or independent evidence from another rate representation.', 'report_schema': optical_cells_schema()}, 'literature_kinetic_cells': {'type': 'array', 'meaning': 'Saved native kinetic parameter and descriptive contrast components, preserving per-operand subject/construct, source protocols, qualification and actual uncertainty meanings. Only the five native cells are supported by this route. Its covariance/model source reader is unimplemented, not a source finding. Ratio, difference and log contrast are dependent representations, not independent experimental support or annotation credit.', 'report_schema': kinetic_cells_schema()}, 'literature_kinetic_model_cells': {'type': 'array', 'meaning': 'Four saved conditional precision/evidence components of the same source kinetic parameter contrast. Full supplied log covariance, exact physical owners, known/estimated/unknown variance and model origin remain explicit. Estimated covariance can supply variance/SE while the existing known-normal profile/index remain unavailable. These dependent representations are not reliability, function probability, target transfer or annotation credit; higher Km is not automatically stronger function.', 'report_schema': kinetic_model_cells_schema()}, 'literature_binding_interaction_model_cells': {'type': 'array', 'meaning': 'Four conditional precision/evidence components for the same source binding interaction. Actual ordered physical owners, full prepared-packet log covariance and source support remain retained; model applicability requires scientific interpretation. Known/estimated/unknown status, distribution, source-defined reporting events, parameter kind and reported versus common conditions remain separate. No covariance producer from original papers is supplied. These dependent representations are not intrinsic affinity, reliability, function probability or annotation credit.', 'report_schema': binding_interaction_model_cells_schema()}, 'literature_binding_interaction_cells': {'type': 'array', 'meaning': "Eight saved native source binding-discrimination interaction components for two molecular forms and two ligands. A requested raw parameter row alone expands that role's numerical source readings and partial uncertainty. Derived rows preserve source meaning/status references without unrequested operand numbers. Unknown common kind does not imply IC50; the model/covariance source reader is unimplemented, not a paper omission. No target transfer or annotation credit.", 'report_schema': binding_interaction_cells_schema()}}
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_concentration_window_storage import CONCENTRATION_WINDOW_CELLS_SCHEMA_V1, NAMESPACE as WINDOW_NAMESPACE
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_numerical_contracts import RETURN_MEANINGS
        result[WINDOW_NAMESPACE] = {'type': 'array', 'meaning': RETURN_MEANINGS[WINDOW_NAMESPACE], 'report_schema': deepcopy(CONCENTRATION_WINDOW_CELLS_SCHEMA_V1)}
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_measurement_comparison_storage import MEASUREMENT_COMPARISON_CELLS_SCHEMA_V2, NAMESPACE as COMPARISON_NAMESPACE
        result[COMPARISON_NAMESPACE] = {'type': 'array', 'meaning': 'Exactly requested source measurement-comparison cells with native qualifiers, actual studied subject, endpoint, normalization, estimator scale, protocol differences and declared model conditions. Descriptive comparisons, common-estimand inference and explicitly conditional signed optical calculations remain distinct. Joint covariance retains owners/status/origin/dependence without its matrix. No unrequested operands, independent assay count, function probability, target transfer or annotation credit.', 'report_schema': deepcopy(MEASUREMENT_COMPARISON_CELLS_SCHEMA_V2)}
        if self.ion_discrimination_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_ion_discrimination_storage import ion_discrimination_cells_schema, NAMESPACE
            result[NAMESPACE] = {'type': 'array', 'meaning': 'Exactly requested saved ion-discrimination numerical sections with actual source ions, biological subject/construct, conditions, controls, normalization, scientific applicability, distinct reported/estimator/nominal/conditional physical domains, uncertainty and dependencies. Derived-only returns expose no unrequested activity, spread or covariance operands. Native component quantities are not complete common reliability, validity or relevance scoring, target transfer or annotation credit.', 'report_schema': ion_discrimination_cells_schema()}
        if self.channel_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_channel_storage import channel_cells_schema, NAMESPACE
            result[NAMESPACE] = {'type': 'array', 'meaning': 'Exactly requested saved source electrical numerical sections with source molecule, construct, preparation, conditions, current meaning, reversal applicability and measurement dependencies. Native point/spread readings expand only their selected quantity; derived sections contain no unrequested primitive numbers. Conditional chord conductance is distinct from reported conductance and differential conductance; charge equivalents are not ion flux or pore turnover. Missing covariance stays unknown, with no independent preparation inference, overall reliability or annotation credit.', 'report_schema': channel_cells_schema()}
        if self.compiled_assay_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_compiled_assay_storage import compiled_assay_cells_schema, NAMESPACE
            result[NAMESPACE] = {'type': 'array', 'meaning': 'Exactly requested saved within-assay numerical sections compiled from actually possessed component cells. Preserve source subject/endpoint, correction stages, controls, partial q/E and q/(kE), full corrected activity, covariance, dependencies and unavailable applicability. Derived views share original measurements; no cross-assay quality grade, target transfer or annotation credit.', 'report_schema': compiled_assay_cells_schema()}
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_compiled_assay_storage import NAMESPACE_V2, compiled_assay_v2_cells_schema
            result[NAMESPACE_V2] = {'type': 'array', 'meaning': 'Exactly requested versioned within-assay numerical sections with estimand-scoped joint covariance, known/estimated/unknown status, signed first-order propagation and separate distinct residual variability. Partial uncertainty is not full corrected-activity uncertainty; shared measurements are not independent evidence or annotation credit.', 'report_schema': compiled_assay_v2_cells_schema()}
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_compiled_assay_storage import NAMESPACE_V3, compiled_assay_v3_cells_schema
            result[NAMESPACE_V3] = {'type': 'array', 'meaning': 'Exactly requested common source-assessment components for the studied functional assertion and contrast. Keep identified-product, reporter, saturation turnover, low-substrate efficiency and explicitly modeled occupancy meanings distinct. Preserve native and conditional values, actual experimental relationships, source versus implementation limitations, reported spread, joint covariance ownership and shared measurements. Conditional residuals do not isolate their cause. No universal quality grade, independent-evidence count, target transfer or final annotation credit.', 'report_schema': compiled_assay_v3_cells_schema()}
        if self.assay_grading_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_grading_storage import assay_grading_cells_schema, NAMESPACE
            result[NAMESPACE] = {'type': 'array', 'meaning': 'Exactly requested assay-type grading components for the selected reference functional assertion. Retain all populated experiment instances using their experiment_ref and sheet_ref; another assessment of one experiment remains linked to that experiment. Preserve shared reliability, validity, relevance, attribution and comparability meanings, source-bound scientific interpretations, measurement dependence, conditions and unknowns. Native measurements, corrections and evidence comparisons are dependent views, not additional independent assays. No unrequested numerical operands, target transfer or final annotation credit.', 'report_schema': assay_grading_cells_schema()}
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_a105_aggregation_storage import aggregation_cells_schema, NAMESPACE
            result[NAMESPACE] = {'type': 'array', 'meaning': 'Requested A105 aggregates of retained experiment values: reliability SUM, validity SUM, relevance MAX, attribution MAX, overall SUM. Preserve exact selected native components, experiment identities and units; no weighting or orthogonality adjustment. Complete values and partial available values remain distinct; no annotation credit.', 'report_schema': aggregation_cells_schema()}
        if self.product_partition_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_product_partition_storage import product_partition_cells_schema, NAMESPACE
            result[NAMESPACE] = {'type': 'array', 'meaning': 'Exactly requested reported product-composition fractions and dependent sum, signed closure deviation or relative partition, with actual species, preparation, endpoint, stage, denominator, basis and source qualifications. Selected numerical closure is not independent mass balance, rate, specificity or molecular attribution. Unknown relationships preserve individual fractions; numerical uncertainty propagation is not implemented. Unrequested native operands are not expanded.', 'report_schema': product_partition_cells_schema()}
        if self.completion_time_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_completion_time_storage import completion_time_cells_schema, NAMESPACE
            result[NAMESPACE] = {'type': 'array', 'meaning': 'Exactly requested source-preparation endpoint-time components, with positive physical-time conditioning, strict reported-limit domains, source-backed endpoint/preparation/condition/change meanings and unknown relationships. The inverse is inverse endpoint time only, not activity retention, intrinsic rate, contaminant fraction, probability, effect isolation or annotation credit. Unrequested time operands are not expanded.', 'report_schema': completion_time_cells_schema()}
        if self.active_site_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_active_site_storage import active_site_cells_schema, NAMESPACE
            result[NAMESPACE] = {'type': 'array', 'meaning': 'Exactly requested active-site titration amount components, including monomer-basis total concentration, active-site density, conditional one-site fraction and conditional physical denominator conversion. Preserve same preparation/assay linkage, nominal versus standardized titrant basis, titrant-site stoichiometry, source uncertainty, normalization stage and actual scientific meanings. Full joint covariance propagation is unimplemented; unknown input meanings remain unknown. No factor is applied to a rate and no annotation credit is computed.', 'report_schema': active_site_cells_schema()}
        if self.parent_depletion_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_parent_depletion_storage import parent_depletion_cells_schema, NAMESPACE
            result[NAMESPACE] = {'type': 'array', 'meaning': 'Exactly requested original XLSX finite parent-removal arm fractions, reported per-arm SD and dependent active-minus-inactive/abiotic differences. Native cell addresses, shared active observation, missing raw denominator, replicate unit, covariance, mutant amount and product identity remain explicit. This is parent disappearance, not a catalytic product yield, confidence score, target transfer or annotation credit.', 'report_schema': parent_depletion_cells_schema()}
        if self.stoichiometric_balance_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_stoichiometric_balance_storage import stoichiometric_balance_cells_schema, NAMESPACE
            result[NAMESPACE] = {'type': 'array', 'meaning': 'Exactly requested original Figure 2D XLSX G2-G6 and Pi concentrations, duplicate-reaction SDs and dependent soluble-product balance components. G2_0 matches nominal charge; W/Pi is descriptive one-Pi-model accounting and Pi-W is an inferred remainder, not measured insoluble product. No ratio uncertainty, method-validity multiplier, matched no-enzyme correction, molecule attribution, target transfer or annotation credit.', 'report_schema': stoichiometric_balance_cells_schema()}
        if self.ratio_source_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_ratio_source_storage import ratio_source_cells_schema
            result['literature_ratio_source_cells'] = {'type': 'array', 'meaning': 'Saved selected source-reported relative-signal components with candidates, reported-estimate domains, selected-roster/completeness/conflict flags, actual scientific meaning/status and source origins. Common scale, source association and physical identity remain separate. Numeric uncertainty, calibrated amount, functional-response and observation-model readers are unimplemented in this route, not demonstrated paper omissions. Dependent transforms do not add independent experimental support or annotation credit.', 'report_schema': ratio_source_cells_schema()}
        if self.controlled_response_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_controlled_response_storage import controlled_response_cells_schema
            result['literature_controlled_response_component_cells'] = {'type': 'array', 'meaning': "Exact saved controlled-response component keys and views, preserving each alternative's scientific meaning, source origins, uncertainty, controls and partial support. Conditional graph-reading bounds are not sampling uncertainty. Derived views do not grant possession of raw operands or covariance. Dependent representations do not create independent evidence, target transfer or annotation credit.", 'report_schema': controlled_response_cells_schema()}
        if self.gel_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_gel_storage import gel_cells_schema
            result['literature_gel_component_cells'] = {'type': 'array', 'meaning': 'Exact saved gel display components and coherent ROI alternatives with source-backed experiment/lane meanings, actual origin, exact arithmetic, units, method, dependence and partial available-only sensitivity. Image darkness is not calibrated molecular occupancy; ROI ranges are not sampling confidence intervals. Derived returns grant no unrequested raw operands, target transfer or annotation credit.', 'report_schema': gel_cells_schema()}
        return result

    def _rate_facts(self, context, references):
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_sheet_updates import current_sheet_refs
        current = current_sheet_refs(self.services.workflow.store, context)
        references = list(dict.fromkeys([*references, *current]))
        context = replace(context, received_record_refs=tuple(dict.fromkeys([*context.received_record_refs, *current])))
        result = {}
        for namespace, requested_field, provider, defaults, repository in self._population_routes(context):
            selected = []
            adapter = repository()
            for reference in references:
                if reference not in context.received_record_refs:
                    continue
                row = self.services.read_record(reference)
                if row.get('record_type') == 'source' and row.get('provider') == provider:
                    if namespace in {'literature_figure_cells', 'literature_endpoint_signal_cells'}:
                        if row.get('version') not in {'literature_figure_record_v1', 'literature_figure_endpoint_signal_record_v1'}:
                            raise ContractError('literature_figure_projection_version_mismatch')
                        if row.get('version') != adapter.record_version:
                            continue
                    if namespace in {'literature_rate_cells', 'literature_rate_source_cells', 'literature_rate_source_domain_cells', 'literature_rate_source_meaning_cells'}:
                        if row.get('version') not in {'literature_rate_population_record_v1', 'literature_rate_population_record_v2'}:
                            raise ContractError('literature_rate_projection_version_mismatch')
                        if row.get('version') != adapter.record_version:
                            continue
                    if namespace in {'literature_rate_observation_cells', 'literature_rate_grid_cells'}:
                        if row.get('version') not in {'literature_reported_rate_observation_record_v1', 'literature_reported_rate_observation_record_v2'}:
                            raise ContractError('literature_rate_grid_projection_version_mismatch')
                        if row.get('version') != adapter.record_version:
                            continue
                    if namespace == 'literature_ratio_source_cells' and row.get('version') != adapter.record_version:
                        raise ContractError('literature_ratio_source_projection_version_mismatch')
                    if namespace in {'literature_perturbation_cells', 'literature_perturbation_summary_cells'}:
                        if row.get('version') not in {'literature_perturbation_record_v1', 'literature_perturbation_record_v2'}:
                            raise ContractError('literature_perturbation_projection_version_mismatch')
                        if row.get('version') != adapter.record_version:
                            continue
                    if namespace in {'literature_reaction_cells', 'literature_reaction_semantic_cells'}:
                        if row.get('version') not in {'literature_reaction_record_v2', 'literature_reaction_record_v3'}:
                            raise ContractError('literature_reaction_projection_version_mismatch')
                        if row.get('version') != adapter.record_version:
                            continue
                    if namespace in {'literature_compiled_assay_cells', 'literature_compiled_assay_v2_cells', 'literature_compiled_assay_v3_cells'}:
                        if row.get('version') not in {'literature_compiled_assay_record_v1', 'literature_compiled_assay_record_v2', 'literature_compiled_assay_record_v3'}:
                            raise ContractError('literature_compiled_assay_projection_version_mismatch')
                        if row.get('version') != adapter.record_version:
                            continue
                    selected.append(reference)
            components = tuple(context.assignment.get(requested_field, defaults))
            result[namespace] = adapter.fact_cells(context, selected, components=components)
        if not self.rate_population:
            return result
        if self.controlled_response_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_controlled_response_storage import PROVIDER
            adapter = self._controlled_response_repository()
            rows = []
            for reference in dict.fromkeys(references):
                if reference not in context.received_record_refs:
                    continue
                record = self.services.read_record(reference)
                if record.get('record_type') == 'source' and record.get('provider') == PROVIDER:
                    keys = adapter.requested_component_keys(reference, context.assignment)
                    rows.extend(adapter.fact_cells(context, [reference], components=keys))
            result['literature_controlled_response_component_cells'] = rows
        if self.gel_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_gel_storage import PROVIDER
            adapter = self._gel_repository()
            rows = []
            for reference in dict.fromkeys(references):
                if reference not in context.received_record_refs:
                    continue
                record = self.services.read_record(reference)
                if record.get('record_type') == 'source' and record.get('provider') == PROVIDER:
                    keys = adapter.requested_component_keys(reference, context.assignment)
                    rows.extend(adapter.fact_cells(context, [reference], components=keys))
            result['literature_gel_component_cells'] = rows
        return result

    def validate_received_report(self, context, form, schema):
        from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.goal import LEADS
        from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.goal import SCREENING
        from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.credit import lead_dispositions
        from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.credit import screening_answers
        task = context.assignment.get('literature_task')
        if task is not None:
            for name, node in schema.get('properties', {}).items():
                source = node.get('x-source')
                if source in (LEADS, SCREENING):
                    reader = lead_dispositions if source == LEADS else screening_answers
                    expected = reader(self.services.workflow.store, context)
                    if plain(form[name]) != expected:
                        raise ReportBoundaryError('Literature answer differs from its original saved work', code='literature_task_answer_differs_from_saved', field=name)
        if not self.rate_population:
            return
        requested_sources = {node.get('x-source') for node in schema.get('properties', {}).values() if node.get('x-source')}
        for namespace, requested_field, _, _, repository in self._population_routes(context if context.role in ROLES else None):
            for name, node in schema.get('properties', {}).items():
                if node.get('x-source') != namespace:
                    continue
                rows = form[name]
                permitted = set(context.received_record_refs)
                stale_channel_receipt = namespace in {'literature_assay_grading_cells', 'literature_a105_aggregation_cells', 'literature_concentration_window_cells', 'literature_measurement_comparison_cells', 'literature_kinetic_summary_precision_cells', 'literature_endpoint_signal_cells', 'literature_rate_grid_cells', 'literature_compiled_assay_v3_cells', 'literature_product_coupling_cells', 'literature_measurement_validation_cells', 'literature_channel_cells', 'literature_ion_discrimination_cells'} and bool(set(repository().selected_sheet_refs(context)) - permitted)
                if any((row['sheet_ref'] not in permitted for row in rows)) or stale_channel_receipt:
                    selection = self.services.record_selection(context)
                    if selection.get('run_id') != context.run_id or selection.get('episode_id') != context.episode_id:
                        raise ReportBoundaryError('Literature return receiver differs', code='literature_rate_receiver_mismatch', field=name)
                    permitted.update(selection['known_record_refs'])
                try:
                    if namespace in {'literature_rate_observation_cells', 'literature_rate_grid_cells', 'literature_compiled_assay_cells', 'literature_compiled_assay_v2_cells', 'literature_compiled_assay_v3_cells'} and (not rows) and (context.assignment.get(requested_field) not in ([], ())):
                        repository().validate_empty_return_family(context)
                    if namespace in {'literature_rate_cells', 'literature_rate_source_cells', 'literature_rate_source_domain_cells', 'literature_rate_source_meaning_cells'} and (not rows) and (context.assignment.get('requested_rate_components') not in ([], ())):
                        repository().validate_empty_return_family(context)
                    if namespace in {'literature_perturbation_cells', 'literature_perturbation_summary_cells'} and (not rows) and (context.assignment.get(requested_field) not in ([], ())):
                        repository().validate_empty_return_family(context)
                    if namespace in {'literature_reaction_cells', 'literature_reaction_semantic_cells'} and (not rows) and (context.assignment.get(requested_field) not in ([], ())):
                        other_namespace = 'literature_reaction_semantic_cells' if namespace == 'literature_reaction_cells' else 'literature_reaction_cells'
                        companion_returned = any((other_node.get('x-source') == other_namespace and bool(form[other_name]) for other_name, other_node in schema.get('properties', {}).items()))
                        if not companion_returned:
                            repository().validate_empty_return_family(context)
                    repository().validate_fact_values(replace(context, received_record_refs=tuple(permitted)), rows)
                    requested = context.assignment.get(requested_field, [] if namespace in {'literature_assay_grading_cells', 'literature_a105_aggregation_cells', 'literature_concentration_window_cells', 'literature_measurement_comparison_cells', 'literature_kinetic_summary_precision_cells', 'literature_endpoint_signal_cells', 'literature_product_coupling_cells', 'literature_measurement_validation_cells', 'literature_calibration_recovery_cells', 'literature_rate_observation_cells', 'literature_rate_grid_cells', 'literature_rate_replicate_cells', 'literature_completion_time_cells', 'literature_product_partition_cells', 'literature_active_site_cells', 'literature_parent_depletion_cells', 'literature_stoichiometric_balance_cells', 'literature_compiled_assay_cells', 'literature_compiled_assay_v2_cells', 'literature_compiled_assay_v3_cells', 'literature_channel_cells', 'literature_ion_discrimination_cells'} else None)
                    permitted_components = repository()._components(requested or []) if namespace == 'literature_rate_grid_cells' else requested
                    if namespace == 'literature_perturbation_operand_cells':
                        permitted_components = context.assignment.get(requested_field, [])
                    if permitted_components is not None and any((row['component'] not in permitted_components for row in rows)):
                        raise ContractError('unrequested_literature_rate_component')
                    if namespace == 'literature_rate_replicate_cells' and rows:
                        from gene_annotation_episode.episodic_workflow.root.a105.domain import canonical
                        expected = repository().fact_cells(replace(context, received_record_refs=tuple(permitted)), list(dict.fromkeys((row['sheet_ref'] for row in rows))), components=requested or [])
                        if canonical(rows) != canonical(expected):
                            raise ContractError('literature_rate_replicate_requested_subset_mismatch')
                    if namespace in {'literature_assay_grading_cells', 'literature_a105_aggregation_cells', 'literature_concentration_window_cells', 'literature_measurement_comparison_cells', 'literature_kinetic_summary_precision_cells', 'literature_endpoint_signal_cells', 'literature_product_coupling_cells', 'literature_measurement_validation_cells', 'literature_rate_observation_cells', 'literature_rate_grid_cells', 'literature_calibration_recovery_cells', 'literature_parent_depletion_cells', 'literature_stoichiometric_balance_cells', 'literature_compiled_assay_cells', 'literature_compiled_assay_v2_cells', 'literature_compiled_assay_v3_cells', 'literature_channel_cells', 'literature_ion_discrimination_cells'}:
                        from gene_annotation_episode.episodic_workflow.root.a105.domain import canonical
                        owned = repository().available_sheet_refs(replace(context, received_record_refs=tuple(permitted)))
                        selected = list(dict.fromkeys([*(row['sheet_ref'] for row in rows), *owned]))
                        expected = repository().fact_cells(replace(context, received_record_refs=tuple(permitted)), selected, components=requested or [])
                        if canonical(rows) != canonical(expected):
                            raise ContractError('literature_assay_grading_requested_subset_mismatch' if namespace == 'literature_assay_grading_cells' else 'literature_concentration_window_requested_subset_mismatch' if namespace == 'literature_concentration_window_cells' else 'literature_measurement_comparison_requested_subset_mismatch' if namespace == 'literature_measurement_comparison_cells' else 'literature_product_coupling_requested_subset_mismatch' if namespace == 'literature_product_coupling_cells' else 'literature_measurement_validation_requested_subset_mismatch' if namespace == 'literature_measurement_validation_cells' else 'literature_ion_discrimination_requested_subset_mismatch' if namespace == 'literature_ion_discrimination_cells' else 'literature_channel_requested_subset_mismatch' if namespace == 'literature_channel_cells' else 'literature_compiled_assay_requested_subset_mismatch' if namespace in {'literature_compiled_assay_cells', 'literature_compiled_assay_v2_cells', 'literature_compiled_assay_v3_cells'} else 'literature_calibration_recovery_requested_subset_mismatch' if namespace == 'literature_calibration_recovery_cells' else 'literature_rate_grid_requested_subset_mismatch' if namespace == 'literature_rate_grid_cells' else 'literature_rate_observation_requested_subset_mismatch')
                except ContractError as error:
                    raise ReportBoundaryError(str(error), code=str(error), field=name) from error
        if self.controlled_response_population and 'literature_controlled_response_component_cells' in requested_sources:
            adapter = self._controlled_response_repository()
            for name, node in schema.get('properties', {}).items():
                if node.get('x-source') != 'literature_controlled_response_component_cells':
                    continue
                rows = form[name]
                permitted = set(context.received_record_refs)
                if any((row['sheet_ref'] not in permitted for row in rows)):
                    selection = self.services.record_selection(context)
                    if selection.get('run_id') != context.run_id or selection.get('episode_id') != context.episode_id:
                        raise ReportBoundaryError('Literature return receiver differs', code='literature_controlled_response_receiver_mismatch', field=name)
                    permitted.update(selection['known_record_refs'])
                try:
                    reporting = replace(context, received_record_refs=tuple(permitted))
                    adapter.validate_fact_values(reporting, rows)
                    allowed = {reference: set(adapter.requested_component_keys(reference, context.assignment)) for reference in dict.fromkeys((row['sheet_ref'] for row in rows))}
                    if any((row['component_key'] not in allowed[row['sheet_ref']] for row in rows)):
                        raise ContractError('unrequested_literature_controlled_response_component')
                except ContractError as error:
                    raise ReportBoundaryError(str(error), code=str(error), field=name) from error
        if self.gel_population and 'literature_gel_component_cells' in requested_sources:
            adapter = self._gel_repository()
            for name, node in schema.get('properties', {}).items():
                if node.get('x-source') != 'literature_gel_component_cells':
                    continue
                rows = form[name]
                permitted = set(context.received_record_refs)
                if any((row['sheet_ref'] not in permitted for row in rows)):
                    selection = self.services.record_selection(context)
                    if selection.get('run_id') != context.run_id or selection.get('episode_id') != context.episode_id:
                        raise ReportBoundaryError('Literature return receiver differs', code='literature_gel_receiver_mismatch', field=name)
                    permitted.update(selection['known_record_refs'])
                try:
                    reporting = replace(context, received_record_refs=tuple(permitted))
                    adapter.validate_fact_values(reporting, rows)
                    allowed = {reference: set(adapter.requested_component_keys(reference, context.assignment)) for reference in dict.fromkeys((row['sheet_ref'] for row in rows))}
                    if any((row['component_key'] not in allowed[row['sheet_ref']] for row in rows)):
                        raise ContractError('unrequested_literature_gel_component')
                except ContractError as error:
                    raise ReportBoundaryError(str(error), code=str(error), field=name) from error
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_a105_worksheet import FAMILIES as WORKSHEET_FAMILIES, validate_a105_worksheet_links
        if requested_sources.intersection(WORKSHEET_FAMILIES):
            known = set(context.received_record_refs)

            def read_public_record(reference):
                if reference not in known:
                    try:
                        selection = self.services.record_selection(context)
                    except (AttributeError, LookupError):
                        return None
                    if selection.get('run_id') != context.run_id or selection.get('episode_id') != context.episode_id:
                        raise ReportBoundaryError('Worksheet reference receiver differs', code='a105_worksheet_receiver_mismatch')
                    known.update(selection.get('known_record_refs', ()))
                return self.services.read_record(reference) if reference in known else None
            try:
                validate_a105_worksheet_links(form, schema, context.assignment, read_public_record=read_public_record)
            except ContractError as error:
                raise ReportBoundaryError(str(error), code=str(error)) from error

    def resolve(self, context, reference, namespace):
        self._role(context.role)
        return reference_in_context(self.services, context, reference, namespace)

    def validate_report(self, context, form, original_schema):
        self._validate_assignment(context.role, context.assignment, context.scope, context=context)
        validate_form(form, original_schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        self.validate_received_report(context, form, original_schema)

    def received_form_references(self, context, form, schema, operation_key):
        if context.role in ROLES:
            return []
        if not self.rate_population:
            return []
        for namespace, _, _, _, repository in self._population_routes():
            cells = []
            for name, node in schema.get('properties', {}).items():
                if node.get('x-source') == namespace:
                    cells.extend(form[name])
            if cells:
                repository().receive_cells(context, cells, operation_key)
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_sheet_updates import current_sheet_refs
        references = current_sheet_refs(self.services.workflow.store, context)
        window_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_concentration_window_cells' for row in form[name]]
        references.extend(self._concentration_window_repository().cell_record_refs(window_cells))
        comparison_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_measurement_comparison_cells' for row in form[name]]
        references.extend(self._measurement_comparison_repository().cell_record_refs(comparison_cells))
        summary_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_kinetic_summary_precision_cells' for row in form[name]]
        references.extend(self._summary_precision_repository().cell_record_refs(summary_cells))
        endpoint_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_endpoint_signal_cells' for row in form[name]]
        references.extend(self._endpoint_signal_repository().cell_record_refs(endpoint_cells))
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_product_coupling_storage import NAMESPACE as COUPLING_NAMESPACE
        coupling_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == COUPLING_NAMESPACE for row in form[name]]
        references.extend(self._product_coupling_repository().cell_record_refs(coupling_cells))
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_measurement_validation_storage import NAMESPACE as VALIDATION_NAMESPACE
        validation_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == VALIDATION_NAMESPACE for row in form[name]]
        references.extend(self._measurement_validation_repository().cell_record_refs(validation_cells))
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_calibration_recovery_storage import NAMESPACE as RECOVERY_NAMESPACE
        recovery_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == RECOVERY_NAMESPACE for row in form[name]]
        references.extend(self.literature_calibration_recovery_repository().cell_record_refs(recovery_cells))
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_observation_storage import NAMESPACE as OBSERVATION_NAMESPACE
        observation_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == OBSERVATION_NAMESPACE for row in form[name]]
        references.extend(self.literature_rate_observation_repository().cell_record_refs(observation_cells))
        grid_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_rate_grid_cells' for row in form[name]]
        references.extend(self._rate_grid_repository().cell_record_refs(grid_cells))
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_replicate_storage import NAMESPACE as REPLICATE_NAMESPACE
        replicate_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == REPLICATE_NAMESPACE for row in form[name]]
        references.extend(self.literature_rate_replicate_repository().cell_record_refs(replicate_cells))
        if self.ion_discrimination_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_ion_discrimination_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._ion_discrimination_repository().cell_record_refs(cells))
        if self.channel_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_channel_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._channel_repository().cell_record_refs(cells))
        if self.compiled_assay_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_compiled_assay_storage import NAMESPACE, NAMESPACE_V2, NAMESPACE_V3
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') in {NAMESPACE, NAMESPACE_V2, NAMESPACE_V3} for row in form[name]]
            references.extend(self._compiled_assay_repository().cell_record_refs(cells))
        if self.assay_grading_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_grading_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._assay_grading_repository().cell_record_refs(cells))
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_a105_aggregation_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._a105_aggregation_repository().cell_record_refs(cells))
        if self.product_partition_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_product_partition_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._product_partition_repository().cell_record_refs(cells))
        if self.completion_time_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_completion_time_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._completion_time_repository().cell_record_refs(cells))
        if self.active_site_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_active_site_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._active_site_repository().cell_record_refs(cells))
        if self.parent_depletion_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_parent_depletion_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._parent_depletion_repository().cell_record_refs(cells))
        if self.stoichiometric_balance_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_stoichiometric_balance_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._stoichiometric_balance_repository().cell_record_refs(cells))
        if self.controlled_response_population:
            adapter = self._controlled_response_repository()
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_controlled_response_component_cells' for row in form[name]]
            if cells:
                adapter.receive_cells(context, cells, operation_key)
                references.extend(adapter.cell_record_refs(cells))
        if self.gel_population:
            adapter = self._gel_repository()
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_gel_component_cells' for row in form[name]]
            if cells:
                adapter.receive_cells(context, cells, operation_key)
                references.extend(adapter.cell_record_refs(cells))
        return list(dict.fromkeys(references))
