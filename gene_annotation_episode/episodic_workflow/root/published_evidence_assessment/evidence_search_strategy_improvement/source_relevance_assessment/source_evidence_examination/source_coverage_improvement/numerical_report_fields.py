from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)
from gene_annotation_episode.episodic_workflow.root.published_evidence_assessment.family import member_for_role



class LiteratureNumericalReportFields:

    def _rate_fact_sources(self):
        if not self.rate_population:
            return self._a108_fact_sources() if self.a108_context_evidence else {}
        from gene_annotation_episode.episodic_workflow.root.library.literature_summary_precision_return_schema import SUMMARY_PRECISION_CELLS_SCHEMA_V1
        from gene_annotation_episode.episodic_workflow.root.literature_product_coupling_storage import product_coupling_cells_schema
        from gene_annotation_episode.episodic_workflow.root.literature_measurement_validation_storage import measurement_validation_cells_schema
        from gene_annotation_episode.episodic_workflow.root.literature_calibration_recovery_storage import calibration_recovery_cells_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_rate_observation_return_contracts import rate_observation_cells_schema, rate_grid_cells_schema
        from gene_annotation_episode.episodic_workflow.root.literature_rate_replicate_storage import rate_replicate_cells_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_rate_meaning_return_schema import rate_source_meaning_cells_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_rate_domain_return_schema import rate_source_domain_cells_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_rate_return_schema import rate_cells_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_native_rate_return_schema import rate_source_cells_schema
        from gene_annotation_episode.episodic_workflow.root.literature_quantity_storage import quantity_cells_schema
        from gene_annotation_episode.episodic_workflow.root.literature_assay_storage import assay_cells_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_ratio_return_schema import ratio_cells_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_binding_return_contracts import binding_cells_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_binding_model_return_contracts import binding_model_cells_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_transport_return_contracts import transport_response_cells_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_perturbation_return_contracts import perturbation_cells_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_perturbation_summary_return_contracts import perturbation_summary_cells_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_structure_return_contracts import structure_cells_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_reaction_return_contracts import reaction_cells_schema, reaction_semantic_cells_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_figure_return_contracts import figure_cells_schema
        from gene_annotation_episode.episodic_workflow.root.literature_partner_storage import partner_cells_schema
        from gene_annotation_episode.episodic_workflow.root.literature_amount_storage import amount_cells_schema
        from gene_annotation_episode.episodic_workflow.root.literature_optical_storage import optical_cells_schema
        from gene_annotation_episode.episodic_workflow.root.literature_kinetic_storage import kinetic_cells_schema
        from gene_annotation_episode.episodic_workflow.root.literature_kinetic_model_storage import kinetic_model_cells_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_binding_interaction_model_return_contracts import binding_interaction_model_cells_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_binding_interaction_return_contracts import binding_interaction_cells_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_endpoint_signal_contracts import ENDPOINT_SIGNAL_CELLS_SCHEMA_V1
        from gene_annotation_episode.episodic_workflow.root.library.literature_endpoint_signal_metadata import NAMESPACE as ENDPOINT_NAMESPACE
        result = {'literature_kinetic_summary_precision_cells': {'type': 'array', 'meaning':
            'Exactly requested source/scenario precision cells for one kinetic summary with actual subject/context, units, physical versus estimator sampling basis, explicit conditions and precise unavailable reasons. Estimated random mean precision, dependent interval calculation parameters and source facts remain distinct. No unrequested operands, independent assay count or annotation credit.',
            'report_schema': deepcopy(SUMMARY_PRECISION_CELLS_SCHEMA_V1)}, ENDPOINT_NAMESPACE: {"type": "array", "meaning":
            "Exactly requested saved endpoint amplitudes, conditional correction fractions and variances. Preserve subject, endpoint, coexistence, finite window, correction stage/applicability, source origin, reading-versus-physical uncertainty and shared measurements. Unrequested source coordinates, amplitudes, caption results and covariance remain private; this is not initial-rate g, molecular attribution, function probability or annotation credit.",
            "report_schema": deepcopy(ENDPOINT_SIGNAL_CELLS_SCHEMA_V1)}, "literature_product_coupling_cells": {"type": "array", "meaning":
            "Exactly requested saved product/cofactor numerical components with actual molecule, construct, preparation, endpoint and experimental relationships. Native reports, descriptive product-per-cofactor ratio, conditional physical fraction and original author-reported coupling remain distinct. Preserve reaction-account direction/status/model identity, shared measurements and dependent reconstruction; requested uncertainty carries source/owner/basis/origin/status provenance without raw covariance. No unrequested native operands, molecular attribution, independent replication, function probability, target transfer or annotation credit is inferred.",
            "report_schema": product_coupling_cells_schema()},
            "literature_measurement_validation_cells": {"type": "array", "meaning":
            "Exactly requested saved precision/control numerical sections, retaining every selected physical measurement and its actual alternative within/between basis. Reported statistics, deterministic re-expressions and supported versus conditional plug-in error components remain distinct, with analyte/matrix/endpoint/repetition, population and denominator meanings, original dependencies and shared contribution identities. A component request returns all its retained measurement instances in original order. No independent replication, product identity, function probability, target transfer or annotation credit is inferred.",
            "report_schema": measurement_validation_cells_schema()},
            "literature_calibration_recovery_cells": {"type": "array", "meaning":
            "Exactly requested saved recovery-control numerical components with actual control analyte, experiment/matrix/endpoint/blank/expected-basis meanings, reporter-standard versus enzyme-activity-spike scope, SD/SEM interpretation, reported-versus-displayed discrepancies and original measurement reuse. Recovery, bias and inverse share operands. Unknown applicability and denominator uncertainty remain unknown; no correction to another measurement, product identity, molecular attribution, function probability or annotation credit is inferred.",
            "report_schema": calibration_recovery_cells_schema()},
            "literature_rate_observation_cells": {"type": "array", "meaning":
            "Exactly requested source-native reported-entry descriptive means, SD/CV and selected functional contrasts. Preserve witnessed panel/subject/group/observation labels, unknown preparation grouping, actual entry/representation/point counts, shared and conflicting source-labelled identities, missing/censored roster and actual input origins. Native arithmetic uses only the selected same-source reporting convention; it establishes neither experimental comparability nor effect isolation. Physical unit conversion, method/blank/calibration/product attribution, preparation n, SE, corrected activity and annotation credit remain unknown.",
            "report_schema": rate_observation_cells_schema()},
            "literature_rate_grid_cells": {"type": "array", "meaning":
                "Exactly requested reported-curve precision scalars with only their named concentration context, actual source labels, native amount-rate units, distinct estimators, reporting denominators and fixed-coordinate sampling scope. Preserve conditional versus ordinary values, source conflicts, unknown physical preparation/published-estimate covariance, shared measurements and source versus implementation limitations. No full rate roster, fitted-parameter set or covariance matrix is delivered by a scalar request; no overall reliability grade or annotation credit.",
                "report_schema": rate_grid_cells_schema()},
            "literature_rate_replicate_cells": {"type": "array", "meaning":
            "Exactly requested raw-rate measurement components with actual source subject/experiment, selected versus observed groups, per-group sampling bases, actual measurement and unit counts, missing/censored/conflicting identities and selected dependence. Unit means receive equal weight after within-unit averaging. Descriptive SD and conditional SE are separate; grouping proves no biological independence. These dependent numerical views supply no assay specificity, error rate, function probability, target transfer or annotation credit.",
            "report_schema": rate_replicate_cells_schema()},
            "literature_rate_cells": {"type": "array", "meaning":
            "Saved source-preparation rate cells with measured subject/experiment retained in the referenced sheet. Conditional statistics are not annotation probabilities or target-transfer scores; unavailable operands remain null with reasons.",
            "report_schema": rate_cells_schema()},
            "literature_rate_source_cells": {"type": "array", "meaning":
                "The same saved numerical rate components from native source spans, with each arm's actual subject/construct/preparation bindings and approximation retained. Source-supported conditional statistical assumptions do not establish causal isolation, target transfer or annotation credit. This closed native return view is distinct from the legacy table view, not a second scoring sheet.",
                "report_schema": rate_source_cells_schema()},
            "literature_rate_source_domain_cells": {"type": "array", "meaning":
                "The same saved native rate components with conditional logical enclosures of reported operands. Finite bounds, inclusivity, undefined denominators and outward numerical projection are explicit; range failure can qualify a still-useful partial enclosure. Status concerns the point estimate. Domains are not sampling confidence intervals, independence, endpoint co-attainability, target transfer or annotation credit. This is another closed return view of the same numerical sheet, not another assay.",
                "report_schema": rate_source_domain_cells_schema()},
            "literature_rate_source_meaning_cells": {"type": "array", "meaning":
                "The same saved native numerical rate/domain rows with the exact recorded intended-change witness and each requested component's operand-role endpoint, normalization and rate-unit conversion meanings, including endpoint-specific source-defined unit definitions. Null means absent from the saved selection, not a demonstrated publication omission. Witnesses do not establish a blank, replacement, isolated effect, sufficiency or independence. No unrequested assay numbers or covariance are expanded. This optional closed return view adds no measurement, scoring component or annotation credit.",
                "report_schema": rate_source_meaning_cells_schema()},
            "literature_quantity_cells": {"type": "array", "meaning":
                "Saved single reported source quantities, with quantity and analyte identity. Untyped spread remains untyped. Source conditions, attribution and correction scores remain unknown where unsupported.",
                "report_schema": quantity_cells_schema()},
            "literature_assay_cells": {"type": "array", "meaning":
                "Saved source-anchored assay interpretations and numerical operands/corrections. Endpoint and arrangement describe the episode's source interpretation. Known-normal indices remain conditional and are not function probabilities. Unknown operands remain null.",
                "report_schema": assay_cells_schema()},
            "literature_ratio_cells": {"type": "array", "meaning":
                "Reported comparative signal components with actual denominator/arrangement, received representation candidates and source origins. Conflicts are not sampling intervals. Calibration and functional response/uncertainty remain separate missing inputs.",
                "report_schema": ratio_cells_schema()},
            "literature_binding_cells": {"type": "array", "meaning":
                "Saved source binding-parameter components with actual protein/state/ligand comparison, uncertainty basis and reported-limit arithmetic. Limits are not confidence or true-parameter bounds; IC50 is not Kd. Missing inputs and unimplemented observation models remain explicit.",
                "report_schema": binding_cells_schema()},
            "literature_binding_model_cells": {"type": "array", "meaning":
                "Saved conditional source log-parameter contrast, full-covariance noise and signed likelihood/index components for test parameter exceeding reference. Known/estimated variance, actual censor mechanism and model origin stay explicit. Native reporting limits are not point observations or confidence bounds; these are not probabilities of function or target-transfer scores.",
                "report_schema": binding_model_cells_schema()},
            "literature_transport_cells": {"type": "array", "meaning":
                "Saved native concentrations and conditional same-curve kinetic-response components. condition_response is test substrate saturation divided by reference substrate saturation under the same fitted curve. Keep actual curve/preparation identities, Km uncertainty meaning and full covariance ownership. The response can divide an appropriate source effect once; it is not reliability or annotation credit. Missing or different curves remain unavailable.",
                "report_schema": transport_response_cells_schema()},
            "literature_perturbation_cells": {"type": "array", "meaning":
                "Saved reference-perturbation effects and proposed restoration components, retaining actual recipient/construct/partner and endpoint meanings. Calibrated same-endpoint contrasts, real restoration, nuisance comparability and effect isolation are distinct. Missing quantitative outcomes and uncertainty remain unknown. The proposed source index is not target correspondence or annotation credit.",
                "report_schema": perturbation_cells_schema()},
            "literature_perturbation_summary_cells": {"type": "array", "meaning":
                "The same A106 source experiment and point components with retained per-observation statistics, actual unit counts, raw-unit descriptive summaries, conditional mean variances and shared-control covariance. Unknown covariance is not zero. Reported intervals, digitization constraints and covariance enclosures keep different meanings; no source-index uncertainty, target transfer or annotation credit is invented.",
                "report_schema": perturbation_summary_cells_schema()},
            "literature_structure_cells": {"type": "array", "meaning":
                "Saved conditional source-model geometry and local residue RSCC components with exact source bindings. Entry/revision validation, fixed required panels, proposed physical predicates and unreported coordinate/measurement uncertainty remain explicit. Conditional state/assignment identities do not establish population occupancy, causal isolation or target annotation credit.",
                "report_schema": structure_cells_schema()},
            "literature_reaction_cells": {"type": "array", "meaning":
                "Saved reported reference reaction-ratio residuals, fixed named-prediction comparisons and simple resource budgets. Source summary uncertainty and incomplete resources remain explicit unknowns. Product-pair ratios and supplied reagent coverage do not establish consumption, native capacity or measured coupling. Logical domain bounds are not confidence intervals; no target correspondence or annotation credit is calculated.",
                "report_schema": reaction_cells_schema()},
            "literature_reaction_semantic_cells": {"type": "array", "meaning":
                "The same saved reference reaction/resource components with source-supported claim and alternative identities, named predictions and exact comparison membership. Resource meanings preserve supply basis, coefficient-to-demand linkage, period and compartment. Missing descriptions add no numerical gate. These are conditional source comparisons and fixed-consumption constraints, not extra assays, physiological sufficiency, target correspondence or annotation credit.",
                "report_schema": reaction_semantic_cells_schema()},
            "literature_figure_cells": {"type": "array", "meaning":
                "Saved native experimental graph ordinates and signed differences with both molecule/partner arms, endpoint/normalization, source representation relationships and repeat/spread meanings. Bounds describe conditional pixel digitization, not SD or confidence intervals. Coupled product or partner-swap differences do not establish upstream-only activity, partner necessity, target correspondence or annotation credit.",
                "report_schema": figure_cells_schema()},
            "literature_partner_cells": {"type": "array", "meaning":
                "Saved experimental partner-removal and addback components with actual molecule/partner identities, nonpartner-condition comparisons, normalization, physical observation identity and reported spread meanings. Native rates survive unavailable controlled comparisons. Bounds condition on supplied censor domains and exact reported means; they are not sampling confidence. Directed condition-specific dependence does not establish universal necessity, genomic presence, coexpression, target correspondence or annotation credit.",
                "report_schema": partner_cells_schema()},
            "literature_amount_cells": {"type": "array", "meaning":
                "Saved A105 source amount components with both quantities' actual roles, preparation/stock, method, basis, qualification and covariance ownership. Target/total mass-fraction estimates differ from nominal molar arm comparisons. Conditional denominator conversion is not applied to a rate; uncertainty and unknown relationships remain explicit, without target correspondence or annotation credit.",
                "report_schema": amount_cells_schema()},
            "literature_optical_cells": {"type": "array", "meaning":
                "Saved projections of existing net_rate(q) and variance_net_rate(Vq) inputs for the source NADH-depletion endpoint, conditional on the selected optical relationships. Preserve actual subject/construct/preparation/conditions, source qualifications, local reuse and covariance ownership. This is not isolated product formation, recovery k, protein amount, corrected activity, target transfer, annotation credit or independent evidence from another rate representation.",
                "report_schema": optical_cells_schema()},
            "literature_kinetic_cells": {"type": "array", "meaning":
                "Saved native kinetic parameter and descriptive contrast components, preserving per-operand subject/construct, source protocols, qualification and actual uncertainty meanings. Only the five native cells are supported by this route. Its covariance/model source reader is unimplemented, not a source finding. Ratio, difference and log contrast are dependent representations, not independent experimental support or annotation credit.",
                "report_schema": kinetic_cells_schema()},
            "literature_kinetic_model_cells": {"type": "array", "meaning":
                "Four saved conditional precision/evidence components of the same source kinetic parameter contrast. Full supplied log covariance, exact physical owners, known/estimated/unknown variance and model origin remain explicit. Estimated covariance can supply variance/SE while the existing known-normal profile/index remain unavailable. These dependent representations are not reliability, function probability, target transfer or annotation credit; higher Km is not automatically stronger function.",
                "report_schema": kinetic_model_cells_schema()},
            "literature_binding_interaction_model_cells": {"type": "array", "meaning":
                "Four conditional precision/evidence components for the same source binding interaction. Actual ordered physical owners, full prepared-packet log covariance and source support remain retained; model applicability requires scientific interpretation. Known/estimated/unknown status, distribution, source-defined reporting events, parameter kind and reported versus common conditions remain separate. No covariance producer from original papers is supplied. These dependent representations are not intrinsic affinity, reliability, function probability or annotation credit.",
                "report_schema": binding_interaction_model_cells_schema()},
            "literature_binding_interaction_cells": {"type": "array", "meaning":
                "Eight saved native source binding-discrimination interaction components for two molecular forms and two ligands. A requested raw parameter row alone expands that role's numerical source readings and partial uncertainty. Derived rows preserve source meaning/status references without unrequested operand numbers. Unknown common kind does not imply IC50; the model/covariance source reader is unimplemented, not a paper omission. No target transfer or annotation credit.",
                "report_schema": binding_interaction_cells_schema()}}
        from gene_annotation_episode.episodic_workflow.root.library.literature_concentration_window_contracts import CONCENTRATION_WINDOW_CELLS_SCHEMA_V1
        from gene_annotation_episode.episodic_workflow.root.literature_concentration_window_storage import NAMESPACE as WINDOW_NAMESPACE
        from gene_annotation_episode.episodic_workflow.root.literature_numerical_contracts import RETURN_MEANINGS
        result[WINDOW_NAMESPACE] = {'type': 'array', 'meaning': RETURN_MEANINGS[WINDOW_NAMESPACE],
            'report_schema': deepcopy(CONCENTRATION_WINDOW_CELLS_SCHEMA_V1)}
        from gene_annotation_episode.episodic_workflow.root.library.literature_measurement_comparison_return_contracts import MEASUREMENT_COMPARISON_CELLS_SCHEMA_V2
        from gene_annotation_episode.episodic_workflow.root.library.literature_measurement_comparison_metadata import NAMESPACE as COMPARISON_NAMESPACE
        result[COMPARISON_NAMESPACE] = {'type': 'array', 'meaning':
            'Exactly requested source measurement-comparison cells with native qualifiers, actual studied subject, endpoint, normalization, estimator scale, protocol differences and declared model conditions. Descriptive comparisons, common-estimand inference and explicitly conditional signed optical calculations remain distinct. Joint covariance retains owners/status/origin/dependence without its matrix. No unrequested operands, independent assay count, function probability, target transfer or annotation credit.',
            'report_schema': deepcopy(MEASUREMENT_COMPARISON_CELLS_SCHEMA_V2)}
        if self.ion_discrimination_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_ion_discrimination_return_contracts import ion_discrimination_cells_schema, NAMESPACE
            result[NAMESPACE] = {"type": "array", "meaning":
                "Exactly requested saved ion-discrimination numerical sections with actual source ions, biological subject/construct, conditions, controls, normalization, scientific applicability, distinct reported/estimator/nominal/conditional physical domains, uncertainty and dependencies. Derived-only returns expose no unrequested activity, spread or covariance operands. Native component quantities are not complete common reliability, validity or relevance scoring, target transfer or annotation credit.",
                "report_schema": ion_discrimination_cells_schema()}
        if self.channel_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_channel_return_contracts import channel_cells_schema, NAMESPACE
            result[NAMESPACE] = {"type": "array", "meaning":
                "Exactly requested saved source electrical numerical sections with source molecule, construct, preparation, conditions, current meaning, reversal applicability and measurement dependencies. Native point/spread readings expand only their selected quantity; derived sections contain no unrequested primitive numbers. Conditional chord conductance is distinct from reported conductance and differential conductance; charge equivalents are not ion flux or pore turnover. Missing covariance stays unknown, with no independent preparation inference, overall reliability or annotation credit.",
                "report_schema": channel_cells_schema()}
        if self.compiled_assay_population:
            from gene_annotation_episode.episodic_workflow.root.literature_compiled_assay_storage import compiled_assay_cells_schema, NAMESPACE
            result[NAMESPACE] = {"type": "array", "meaning":
                "Exactly requested saved within-assay numerical sections compiled from actually possessed component cells. Preserve source subject/endpoint, correction stages, controls, partial q/E and q/(kE), full corrected activity, covariance, dependencies and unavailable applicability. Derived views share original measurements; no cross-assay quality grade, target transfer or annotation credit.",
                "report_schema": compiled_assay_cells_schema()}
            from gene_annotation_episode.episodic_workflow.root.literature_compiled_assay_storage import NAMESPACE_V2, compiled_assay_v2_cells_schema
            result[NAMESPACE_V2] = {"type": "array", "meaning":
                "Exactly requested versioned within-assay numerical sections with estimand-scoped joint covariance, known/estimated/unknown status, signed first-order propagation and separate distinct residual variability. Partial uncertainty is not full corrected-activity uncertainty; shared measurements are not independent evidence or annotation credit.",
                "report_schema": compiled_assay_v2_cells_schema()}
            from gene_annotation_episode.episodic_workflow.root.literature_compiled_assay_storage import NAMESPACE_V3, compiled_assay_v3_cells_schema
            result[NAMESPACE_V3] = {'type': 'array', 'meaning':
                'Exactly requested common source-assessment components for the studied functional assertion and contrast. Keep identified-product, reporter, saturation turnover, low-substrate efficiency and explicitly modeled occupancy meanings distinct. Preserve native and conditional values, actual experimental relationships, source versus implementation limitations, reported spread, joint covariance ownership and shared measurements. Conditional residuals do not isolate their cause. No universal quality grade, independent-evidence count, target transfer or final annotation credit.',
                'report_schema': compiled_assay_v3_cells_schema()}
        if self.a106_intervention:
            from gene_annotation_episode.episodic_workflow.root.library.literature_perturbation_operand_contracts import cells_schema, NAMESPACE
            result[NAMESPACE] = {'type': 'array', 'meaning':
                'Selected original perturbation effects and matching mean variances for the A106 grader. '
                'Retains original measurement identities, shared controls and full source cell meanings. '
                'No additional experiment, independence claim or recalculated science.',
                'report_schema': cells_schema()}
            from gene_annotation_episode.episodic_workflow.root.literature_intervention_storage import intervention_cells_schema, NAMESPACE
            result[NAMESPACE] = {'type': 'array', 'meaning':
                'A106 intervention assessments, native diagnostics and conditional signed evidence ratios with experiment identity, comparison, design and revisions.',
                'report_schema': intervention_cells_schema()}
            from gene_annotation_episode.episodic_workflow.root.library.literature_a106_subscore import cells_schema, NAMESPACE
            result[NAMESPACE] = {'type': 'array', 'meaning':
                'A106 final signed log evidence ratio bound to the subject, assertion, alternative, scope and current original experiments; retain missing scores, dependence and revisions.',
                'report_schema': cells_schema()}
        if self.assay_grading_population:
            from gene_annotation_episode.episodic_workflow.root.literature_assay_grading_storage import assay_grading_cells_schema, NAMESPACE
            result[NAMESPACE] = {'type': 'array', 'meaning':
                'Exactly requested assay-type grading components for the selected reference functional assertion. '
                'Retain all populated experiment instances using their experiment_ref and sheet_ref; '
                'another assessment of one experiment remains linked to that experiment. '
                'Preserve shared reliability, validity, relevance, attribution and comparability meanings, '
                'source-bound scientific interpretations, measurement dependence, conditions and unknowns. '
                'Native measurements, corrections and evidence comparisons are dependent views, not additional '
                'independent assays. No unrequested numerical operands, target transfer or final annotation credit.',
                'report_schema': assay_grading_cells_schema()}
            from gene_annotation_episode.episodic_workflow.root.literature_a105_aggregation_storage import aggregation_cells_schema, NAMESPACE
            result[NAMESPACE] = {'type': 'array', 'meaning':
                'Requested A105 aggregates of retained experiment values: reliability SUM, validity SUM, '
                'relevance MAX, attribution MAX, overall SUM. Preserve exact selected native components, '
                'experiment identities and units; no weighting or orthogonality adjustment. '
                'Complete values and partial available values remain distinct; no annotation credit.',
                'report_schema': aggregation_cells_schema()}
        if self.product_partition_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_product_partition_return_schema import product_partition_cells_schema, NAMESPACE
            result[NAMESPACE] = {"type": "array", "meaning":
                "Exactly requested reported product-composition fractions and dependent sum, signed closure deviation or relative partition, with actual species, preparation, endpoint, stage, denominator, basis and source qualifications. Selected numerical closure is not independent mass balance, rate, specificity or molecular attribution. Unknown relationships preserve individual fractions; numerical uncertainty propagation is not implemented. Unrequested native operands are not expanded.",
                "report_schema": product_partition_cells_schema()}
        if self.completion_time_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_completion_time_return_schema import completion_time_cells_schema, NAMESPACE
            result[NAMESPACE] = {"type": "array", "meaning":
                "Exactly requested source-preparation endpoint-time components, with positive physical-time conditioning, strict reported-limit domains, source-backed endpoint/preparation/condition/change meanings and unknown relationships. The inverse is inverse endpoint time only, not activity retention, intrinsic rate, contaminant fraction, probability, effect isolation or annotation credit. Unrequested time operands are not expanded.",
                "report_schema": completion_time_cells_schema()}
        if self.active_site_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_active_site_return_schema import active_site_cells_schema, NAMESPACE
            result[NAMESPACE] = {"type": "array", "meaning":
                "Exactly requested active-site titration amount components, including monomer-basis total concentration, active-site density, conditional one-site fraction and conditional physical denominator conversion. Preserve same preparation/assay linkage, nominal versus standardized titrant basis, titrant-site stoichiometry, source uncertainty, normalization stage and actual scientific meanings. Full joint covariance propagation is unimplemented; unknown input meanings remain unknown. No factor is applied to a rate and no annotation credit is computed.",
                "report_schema": active_site_cells_schema()}
        if self.parent_depletion_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_parent_depletion_return_schema import parent_depletion_cells_schema, NAMESPACE
            result[NAMESPACE]={'type':'array','meaning':
                'Exactly requested original XLSX finite parent-removal arm fractions, reported per-arm SD and dependent active-minus-inactive/abiotic differences. Native cell addresses, shared active observation, missing raw denominator, replicate unit, covariance, mutant amount and product identity remain explicit. This is parent disappearance, not a catalytic product yield, confidence score, target transfer or annotation credit.',
                'report_schema':parent_depletion_cells_schema()}
        if self.stoichiometric_balance_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_stoichiometric_balance_return_schema import stoichiometric_balance_cells_schema, NAMESPACE
            result[NAMESPACE] = {'type': 'array', 'meaning':
                'Exactly requested original Figure 2D XLSX G2-G6 and Pi concentrations, duplicate-reaction SDs and dependent soluble-product balance components. G2_0 matches nominal charge; W/Pi is descriptive one-Pi-model accounting and Pi-W is an inferred remainder, not measured insoluble product. No ratio uncertainty, method-validity multiplier, matched no-enzyme correction, molecule attribution, target transfer or annotation credit.',
                'report_schema': stoichiometric_balance_cells_schema()}
        if self.ratio_source_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_ratio_source_return_schema import ratio_source_cells_schema
            result["literature_ratio_source_cells"] = {"type": "array", "meaning":
                "Saved selected source-reported relative-signal components with candidates, reported-estimate domains, selected-roster/completeness/conflict flags, actual scientific meaning/status and source origins. Common scale, source association and physical identity remain separate. Numeric uncertainty, calibrated amount, functional-response and observation-model readers are unimplemented in this route, not demonstrated paper omissions. Dependent transforms do not add independent experimental support or annotation credit.",
                "report_schema": ratio_source_cells_schema()}
        if self.controlled_response_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_controlled_response_return_contract import controlled_response_cells_schema
            result["literature_controlled_response_component_cells"] = {"type": "array", "meaning":
                "Exact saved controlled-response component keys and views, preserving each alternative's scientific meaning, source origins, uncertainty, controls and partial support. Conditional graph-reading bounds are not sampling uncertainty. Derived views do not grant possession of raw operands or covariance. Dependent representations do not create independent evidence, target transfer or annotation credit.",
                "report_schema": controlled_response_cells_schema()}
        if self.gel_population:
            from gene_annotation_episode.episodic_workflow.root.literature_gel_storage import gel_cells_schema
            result["literature_gel_component_cells"] = {"type": "array", "meaning":
                "Exact saved gel display components and coherent ROI alternatives with source-backed experiment/lane meanings, actual origin, exact arithmetic, units, method, dependence and partial available-only sensitivity. Image darkness is not calibrated molecular occupancy; ROI ranges are not sampling confidence intervals. Derived returns grant no unrequested raw operands, target transfer or annotation credit.",
                "report_schema": gel_cells_schema()}
        from gene_annotation_episode.episodic_workflow.root.library.literature_reaction_native_return_contracts import NAMESPACE, native_observations_schema
        result[NAMESPACE] = {"type": "array", "meaning":
            "Separately requested native reaction observations preserving exact reported points or ratio-expression operands, source unit conversion, measurement/calibration basis, actual uncertainty kind and count basis. Reported technical or unknown counts are not independent n. These are source operands, not extra scoring components or independent evidence.",
            "report_schema": native_observations_schema()}
        if self.a108_context_evidence:
            result.update(self._a108_fact_sources())
        return result

    def _a108_fact_sources(self):
        from gene_annotation_episode.episodic_workflow.root.literature_a108_grading_storage import grading_cells_schema
        from gene_annotation_episode.episodic_workflow.root.literature_a108_aggregation_storage import aggregation_cells_schema
        from gene_annotation_episode.episodic_workflow.root.literature_numerical_contracts import RETURN_MEANINGS
        return {name: {'type': 'array', 'meaning': RETURN_MEANINGS[name], 'report_schema': schema()}
            for name, schema in (
                ('literature_a108_grading_cells', grading_cells_schema),
                ('literature_a108_aggregation_cells', aggregation_cells_schema))}

