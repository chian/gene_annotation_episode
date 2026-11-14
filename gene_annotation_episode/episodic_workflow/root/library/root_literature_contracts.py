"""Literature specializations of the application's ordinary Episode loop.

This binding supplies operands, available ordinary operations, source custody,
and the commissioned task's private yield binding when selected. The shared
source owns decisions, reasoning commits, commissioning and report updates.
In particular, a reading selection is
information for an investigation, never a script that this binding executes.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
import hashlib
import inspect
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError, plain, validate_form
from gene_annotation_episode.episodic_workflow.root.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.domain import ContractError, REF, identity, obj, source_location_inputs, validate_schema
from gene_annotation_episode.episodic_workflow.root.episode_bindings import reference_in_context


VERSION = "literature_episode_binding_v1"
ROLES = ("literature", "literature_strategy", "literature_search",
         "literature_page", "literature_table", "literature_ordered",
         "literature_targeted")

_REFERENCES = {"type": "array", "items": REF, "uniqueItems": True}
_REPRESENTATION = {"type": "string", "enum": ["text", "original", "stdout", "stderr"]}
_NATURAL = {"type": "integer", "minimum": 0}
_POSITIVE = {"type": "integer", "minimum": 1}
_TEXT = {"type": "string", "minLength": 1}
_WINDOW = obj({"source_ref": REF, "representation": _REPRESENTATION,
               "offset": _NATURAL, "limit": _POSITIVE})
_TABLE = obj({"source_ref": REF, "sheet_key": _TEXT, "offset": _NATURAL,
    "limit": _NATURAL, "header_row": {"type": ["integer", "null"], "minimum": 1},
    "where": {**obj({"column": {"type": ["string", "null"], "pattern": "^[A-Z]+$"},
        "match": {"enum": ["equals", "contains"]}, "value": _TEXT,
        "case_sensitive": {"type": "boolean"}}), "type": ["object", "null"]}})
_PAGE = obj({"version": {"const": "page_assignment_v1"}, "source_ref": REF,
    "representation": _REPRESENTATION, "artifact_ref": REF,
    "question_context_refs": _REFERENCES, "prior_delivery_refs": _REFERENCES})

_CHILDREN = {"literature": ("literature_strategy",),
    "literature_strategy": ("literature_search",),
    "literature_search": ("literature_page",),
    "literature_page": ("literature_table", "literature_ordered", "literature_targeted"),
    "literature_table": (), "literature_ordered": (), "literature_targeted": ()}

from gene_annotation_episode.experimental_database_acquisition import OPERATIONS as EXPERIMENT_DATABASE_TOOLS

_ACCESS_TOOLS = ("state.query", "source.read", "source.locate", "source.sequence.scan", "source.sequence.references", "source.experimental.records", "image.view", "source.archive.members",
    "source.archive.extract", "source.xlsx.sheets", "source.xlsx.rows",
    "source.pdf.info", "source.pdf.text", "source.pdf.page", "execution.estimate")
_ACQUISITION_TOOLS = ("public.literature.search", "public.literature.read", "public.literature.sequence_identity",
    "public.ncbi.search", "public.pmc.versions", "public.pmc.files", "public.pmc.asset", *EXPERIMENT_DATABASE_TOOLS)
_A108_ACCESS_TOOLS = ("state.query", "source.read", "source.locate", "source.sequence.references",
    "image.view", "source.archive.members", "source.archive.extract", "source.xlsx.sheets",
    "source.xlsx.rows", "source.pdf.info", "source.pdf.text", "source.pdf.page",
    "material.annotations", "material.parse", "material.from_source", "execution.estimate")
_A108_ACQUISITION_TOOLS = ("public.literature.search", "public.literature.read",
    "public.literature.sequence_identity", "public.ncbi.search", "public.pmc.versions",
    "public.pmc.files", "public.pmc.asset", "public.uniprot.search", "public.uniprot.record",
    "public.taxonomy", "public.ncbi.sequence")
_A108_NAMESPACES = frozenset(("literature_a108_grading_cells", "literature_a108_aggregation_cells"))


def _a108_population_catalog():
    from gene_annotation_episode.episodic_workflow.root.literature_a108_grading_inputs import grading_population_schema
    from gene_annotation_episode.episodic_workflow.root.literature_a108_grading_storage import OPERATION_DESCRIPTION as GRADING_DESCRIPTION
    from gene_annotation_episode.episodic_workflow.root.literature_a108_aggregation_storage import aggregation_population_schema
    from gene_annotation_episode.episodic_workflow.root.literature_a108_aggregation_storage import OPERATION_DESCRIPTION as AGGREGATION_DESCRIPTION
    return [{'name': 'literature.a108_grading.populate', 'description': GRADING_DESCRIPTION,
             'input_schema': grading_population_schema()},
            {'name': 'literature.a108.aggregate', 'description': AGGREGATION_DESCRIPTION,
             'input_schema': aggregation_population_schema()}]


_READ_TOOLS = ("source.read", "source.locate", "source.sequence.scan", "source.sequence.references", "source.experimental.records", "source.xlsx.rows", "source.pdf.text", "image.view")

_ROLE_INSTRUCTIONS = {
    "literature": "Investigate which published evidence bears on the assigned scientific question. You can pursue ordinary searches and source reads directly, or assign a strategy investigation when that narrower question warrants iteration.",
    "literature_strategy": "Investigate which search approach is productive. Keep the information objective and evidence context separate from a literal provider query. Revise terms or source choices in light of actual search/read outcomes; a search child can investigate which returned sources deserve examination.",
    "literature_search": "Investigate which returned sources merit examination for the assigned question. Search results are source-discovery information. Examine original sources and their conditions before asserting biological evidence. A page child can investigate where and how to examine a selected source.",
    "literature_page": "Investigate where and how this exact source should be examined. Choose ordinary source operations or selected table, ordered-reading or targeted-passage investigations as useful. Paragraph projections omit some XML headings, tables and footnotes; retained original bytes remain addressable.",
    "literature_table": "Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches keep their native identity. Article XML tables are read through exact original-source windows.",
    "literature_ordered": "Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte continuations and retain representation identity. Decide whether to continue, reread, change the examined window or interpret obtained evidence from actual outcomes.",
    "literature_targeted": "Investigate the supplied source-bound passages for the assigned question. Read neighboring context, qualifications or alternative passages as needed and revise the interpretation from actual outcomes. Separate spans remain separate; never concatenate them into a fabricated quotation.",
}


def _population_catalog(*, a106_intervention=False, assay_grading_population=False, ratio_source_population=False, controlled_response_population=False, gel_population=False, completion_time_population=False, product_partition_population=False, active_site_population=False, parent_depletion_population=False, stoichiometric_balance_population=False, compiled_assay_population=False, channel_population=False, ion_discrimination_population=False):
    """Actual child population operations, independent of episode identity."""
    result = []
    from gene_annotation_episode.episodic_workflow.root.literature_concentration_window_storage import concentration_window_operation_schema
    result.append({'name': 'literature.concentration_window.populate',
        'description': 'Populate exactly requested source concentration-window components from original values, units, coordinates and witnessed experimental meanings. Preserve actual molecule, construct, preparation, participants, endpoint, normalization, physical versus descriptive accounts, stoichiometric model, timing qualifications and covariance ownership. Interval averages are not initial rates or turnover constants. Missing inputs preserve partials; no unrequested operands or covariance matrix, molecular attribution, target transfer or annotation credit.',
        'input_schema': concentration_window_operation_schema()})
    from gene_annotation_episode.episodic_workflow.root.library.literature_measurement_comparison_return_contracts import measurement_comparison_operation_schema
    result.append({'name': 'literature.measurement_comparison.populate',
        'description': 'Populate exactly requested source measurement-comparison components from received original selectors and witnessed experimental meanings. Preserve native qualifiers, actual subject/endpoint/protocol, fixed conversions, descriptive comparisons, declared common models, signed optical correction, dependence and owned covariance. Missing inputs preserve partials. No unrequested operands, covariance matrix, function probability, target transfer or annotation credit.',
        'input_schema': measurement_comparison_operation_schema()})
    from gene_annotation_episode.episodic_workflow.root.literature_rate_storage import rate_population_schema
    result.append({"name": "literature.rate.populate",
        "description": "Populate source-preparation rate cells from a selected already acquired CSV/TSV summary. Preserve actual subjects, conditions, units, uncertainty and missingness. This finite table route does not read arbitrary prose/figures or calculate target transfer/annotation credit. Select a statistical model only when supported; otherwise use none and unknown dependence.",
        "input_schema": rate_population_schema()})
    from gene_annotation_episode.episodic_workflow.root.library.literature_rate_observation_operation_contracts import rate_observation_operation_schema
    from gene_annotation_episode.episodic_workflow.root.library.literature_rate_observation_prompt import RATE_OBSERVATION_UNION_OPERATION_DESCRIPTION
    result.append({"name": "literature.rate.observations.populate",
        "description": RATE_OBSERVATION_UNION_OPERATION_DESCRIPTION,
        "input_schema": rate_observation_operation_schema()})
    from gene_annotation_episode.episodic_workflow.root.literature_calibration_recovery_inputs import calibration_recovery_population_schema
    result.append({"name": "literature.calibration.recovery.populate",
        "description": "Populate requested source-bound recovery-control components from exact original numerical/unit spans. Preserve measured/expected roles, reporter-standard versus enzyme-activity-spike meaning, matrix, endpoint, blank treatment, actual SD/SEM meaning and original measurement reuse. Calculate recovery, signed bias and reported-versus-displayed discrepancy deterministically. Unknown inputs preserve partials. This control does not establish product identity, independent verification or applicability to another measurement; no target correction or annotation credit is supplied.",
        "input_schema": calibration_recovery_population_schema()})
    from gene_annotation_episode.episodic_workflow.root.library.literature_product_coupling_inputs import product_coupling_population_schema
    result.append({"name": "literature.product_coupling.populate",
        "description": "Populate requested A105 source product/cofactor components from exact received number/unit spans and witnessed endpoint, pairing and reaction-account meanings. Keep native product/cofactor/reported-percent quantities separate, descriptive product-per-cofactor ratio distinct from a supported physical productive fraction, and molecule-specific attribution unresolved when unknown. No default or fitted stoichiometry, nondetection-as-zero ratio, invented covariance, independent reconstruction, target transfer or annotation credit. Uncertainty requires the explicitly owned joint covariance of selected rate estimates; requested derived returns contain no unrequested native operands or matrix.",
        "input_schema": product_coupling_population_schema()})
    from gene_annotation_episode.episodic_workflow.root.literature_measurement_validation_inputs import measurement_validation_population_schema
    result.append({"name": "literature.measurement_validation.populate",
        "description": "Populate requested source precision and control-separation components from exact CV/Z-prime number, label, unit and source-meaning witnesses, optionally using only actually possessed recovery/bias rows. Preserve each within/between population separately, unknown denominator relationships, conditional arithmetic, original measurement reuse and proposed-versus-reported meanings. Native statistics need no prior framework sheet. These components are not product identity, independent verification, a function probability, target transfer or final annotation credit.",
        "input_schema": measurement_validation_population_schema()})
    from gene_annotation_episode.episodic_workflow.root.literature_rate_replicate_storage import rate_replicate_population_schema
    from gene_annotation_episode.episodic_workflow.root.library.literature_rate_replicate_prompt import RATE_REPLICATE_OPERATION_DESCRIPTION
    result.append({"name": "literature.rate.replicates.populate",
        "description": RATE_REPLICATE_OPERATION_DESCRIPTION,
        "input_schema": rate_replicate_population_schema()})
    from gene_annotation_episode.episodic_workflow.root.library.literature_quantity_population_schema import quantity_population_schema
    result.append({"name": "literature.quantity.populate",
        "description": "Read one literal specific activity or apparent Km from selected original JATS prose, or apparent Km from selected original HTML prose. Select quantity role and analyte, not numbers. HTML paragraphs without IDs use the explicit direct_paragraph:N selector within the selected section. Preserve untyped plus-minus spread. Subject-token presence does not establish experimental attribution; inspect the assay context separately. No comparison arms, conditions, product identity or missing correction score are invented.",
        "input_schema": quantity_population_schema()})
    from gene_annotation_episode.episodic_workflow.root.literature_assay_inputs import assay_arguments_schema
    result.append({"name": "literature.assay.populate",
        "description": "Interpret the source assay's actual subject, conditions, endpoint and molecular arrangement with exact source witnesses. Select reported numerical spans only when they have the stated correction-operand meanings. Deterministically parse and correct the interpreted source endpoint, preserving full covariance, conditional assumptions and unknowns. Exact quotes validate custody, not interpretation; no target transfer or annotation probability.",
        "input_schema": assay_arguments_schema()})
    from gene_annotation_episode.episodic_workflow.root.literature_ratio_storage import ratio_population_schema
    result.append({"name": "literature.ratio.populate",
        "description": "Read reported relative-signal percentages from selected JATS prose and optionally compare retained visual transcriptions with original image custody. Preserve the actual denominator/arrangement and conflicting candidate values. Signal is not calibrated molar amount or an isolated functional effect; no source reliability or target-transfer score is fabricated.",
        "input_schema": ratio_population_schema()})
    from gene_annotation_episode.episodic_workflow.root.literature_binding_storage import binding_population_schema
    result.append({"name": "literature.binding.populate",
        "description": "Populate source binding-parameter components from an already received table or explicitly retained visual transcription. Keep IC50 distinct from reported Hill-fit Kd, actual protein/state/ligand identities, reported fit-spread basis and point/limit arithmetic. Original image custody is validated; no OCR, sampling confidence, intrinsic-affinity conversion or target credit is inferred.",
        "input_schema": binding_population_schema()})
    from gene_annotation_episode.episodic_workflow.root.literature_binding_model_storage import binding_model_population_schema
    result.append({"name": "literature.binding.model.populate",
        "description": "Evaluate the ordered parameter contrast in an actually received committed binding sheet using an explicitly supplied source model. Preserve full log-covariance measurement ownership, known versus estimated variance, and the stated threshold-reporting mechanism. Missing model source retains usable native contrast and explicit unknown likelihood cells. No inference of covariance from fit spreads or counts, limit-as-point calculation, intrinsic-affinity conversion, target transfer or annotation credit.",
        "input_schema": binding_model_population_schema()})
    from gene_annotation_episode.episodic_workflow.root.library.literature_transport_inputs import transport_response_population_schema
    result.append({"name": "literature.transport.response.populate",
        "description": "Calculate a conditional source substrate-response correction from exact concentration spans and a received saved apparent-Km quantity. Preserve actual molecule, preparation, analyte, endpoint and fitted-curve contexts. Different or unknown curves leave the comparison unavailable. Full covariance retains physical owners and shared Km once; no sampling variance from untyped spread, target transfer or annotation credit is inferred.",
        "input_schema": transport_response_population_schema()})
    from gene_annotation_episode.episodic_workflow.root.library.literature_perturbation_inputs import perturbation_population_schema
    result.append({"name": "literature.perturbation.populate",
        "description": "Populate reference perturbation/restoration components from source-bound design interpretations and optional received quantitative data. Keep actual recipient, changed component, partner, endpoint calibration and real restoration arms distinct. Qualitative-only outcomes cannot supply numerical rates. Preserve nuisance comparability separately from effect isolation and leave missing inputs/uncertainty unknown. No target transfer, necessity inference from an unmeasured catalytic knockout, or final annotation credit.",
        "input_schema": perturbation_population_schema()})
    from gene_annotation_episode.episodic_workflow.root.library.literature_structure_input_contracts import structure_population_schema
    result.append({"name": "literature.structure.populate",
        "description": "Populate source-model geometry and local residue RSCC components from received coordinates and optional matching deposited validation. Select exact model/author atom groups and fixed physical criteria. Preserve missing endpoints, validation entry/revision mismatch and unreported coordinate uncertainty. The explicit scope is conditional deposited-model geometry; it does not establish population occupancy, causal mechanism, target correspondence or annotation credit.",
        "input_schema": structure_population_schema()})
    from gene_annotation_episode.episodic_workflow.root.library.literature_reaction_inputs import reaction_population_schema
    result.append({"name": "literature.reaction.populate",
        "description": "Populate reported reference reaction-ratio residuals, named-prediction comparisons and simple resource-budget components from an explicitly retained received dataset or native source-selection recipe. Read exact report ratio points or author a:b expressions, summary uncertainty/counts and simple resource quantities with source units. Preserve unknown replication, missing alternatives, calibration basis and incomplete resource constraints. Product-pair ratios, instrument signals, supplied reagent budgets and usable capacity have distinct meanings. This route does not parse NMR spectra, establish measured oxygen coupling, apply missing corrections or calculate target transfer/annotation credit.",
        "input_schema": reaction_population_schema(include_assessment=True)})
    from gene_annotation_episode.episodic_workflow.root.library.literature_reaction_source_contracts import reaction_source_population_schema
    result.append({"name": "literature.reaction.source.populate",
        "description": "Populate the original experimental reaction components directly from exact received source spans, without a prepared measurement dataset. Select reported ratio points or author a:b expressions, actual uncertainty/count witnesses and source-unit resource quantities. Explicit predictions, coefficients and demand retain their interpreted basis. The host saves the source-selection recipe and invokes the existing native readers, numerical calculator, publication and exact selected-cell returns. Unknown sampling, calibration, alternatives and resource completeness remain unknown; no spectrum digitization, biological activity, target transfer or new score is inferred.",
        "input_schema": reaction_source_population_schema()})
    from gene_annotation_episode.episodic_workflow.root.library.literature_figure_return_contracts import figure_operation_schema
    result.append({"name": "literature.figure.populate",
        "description": "Select either the original mean-bar request or the explicit endpoint-signal population version. Endpoint work authenticates received original source/image selections and preserves only requested amplitudes, conditional correction fractions or variances, narrow source context, shared traces and reading-versus-physical uncertainty; it supplies no initial rate, function probability or full covariance return. Read native experimental mean-bar ordinates from received original images using a retained linear-axis selection recipe. Preserve both subject/partner arms, endpoint and normalization meanings, source representation relationships, reported repeat/spread meanings and conditional digitization bounds. Return raw ordinates and a signed difference; pixel extraction does not supply SD, statistical significance, molar calibration, partner necessity or target credit.",
        "input_schema": figure_operation_schema()})
    from gene_annotation_episode.episodic_workflow.root.literature_partner_storage import partner_population_schema
    result.append({"name": "literature.partner.populate",
        "description": "Populate source experimental partner-removal and addback components from received retained measurements and exact source witnesses. Preserve directed molecule/partner roles, nitrogen and other nonpartner conditions, normalization identity, physical measurement identity and reported spread meanings. Incompatible or incomplete comparisons keep native values and explicit unknown components. Censor domains are not confidence intervals; chemical bypass and partner swaps do not establish universal partner necessity, genomic presence, target transfer or annotation credit.",
        "input_schema": partner_population_schema(include_assessment=True)})
    from gene_annotation_episode.episodic_workflow.root.library.literature_partner_operand_information import partner_source_population_schema_with_information
    result.append({"name": "literature.partner.source.populate",
        "description": "Populate the same experimental partner components directly from selected literal source spans. Select complete rate/limit tokens, native units, spread meanings and source-bound entity/physical-measurement identities; do not supply scientific numbers or a prepared numeric JSON dataset. For source-defined activity units such as U/mg, select the endpoint-specific definition, quantity, molecular entity and time basis; no universal U conversion is assumed. Deterministic readers preserve original tokens, convert supported rate units and retain unknown normalization, conditions or observation identity. A repeated representation is not a new measurement. No sampling uncertainty, universal necessity, target correspondence or annotation credit is inferred.",
        "input_schema": partner_source_population_schema_with_information()})
    from gene_annotation_episode.episodic_workflow.root.library.literature_native_rate_operand_information import rate_source_population_schema_with_information
    result.append({"name": "literature.rate.source.populate",
        "description": "Populate the existing source-rate comparison sheet directly from selected literal paper spans, without a prepared CSV/TSV or model-authored scientific numbers. Request literature_rate_source_domain_cells for full reported-operand domains, including finite two-sided enclosures; the original literature_rate_source_cells projection preserves each arm's subject, construct, preparation, approximation and one-sided limits; literature_rate_cells is the separate legacy table projection. Select source-backed endpoint/basis relationships and statistical assumptions; different constructs may be the intended comparison. Source-defined U/mg requires its endpoint-specific definition. Missing meanings, unsupported units and censored values retain partial inputs. Exact witnesses verify custody, not causal isolation, target correspondence or annotation credit.",
        "input_schema": rate_source_population_schema_with_information()})
    from gene_annotation_episode.episodic_workflow.root.literature_amount_inputs import amount_arguments_schema
    result.append({"name": "literature.amount.populate",
        "description": "Populate A105 source amount components from exact reported numerical/unit spans and witnessed experimental meanings. Keep target/total same-stock mass-fraction estimates separate from nominal molar amounts between arms. Preserve both quantity roles, preparations, methods, bases, bounds, approximation and source-owned covariance. Ratios above one and missing relationships remain explicit; no active fraction, universal activity correction, target transfer or annotation credit is inferred. The conditional mass-denominator factor is retained without applying it to a saved rate.",
        "input_schema": amount_arguments_schema()})
    from gene_annotation_episode.episodic_workflow.root.literature_optical_inputs import optical_arguments_schema
    result.append({"name": "literature.optical.populate",
        "description": "Populate the existing net_rate and variance_net_rate input meanings from selected source-bound optical observations. Preserve NADH-depletion endpoint scope, actual subject/construct/preparation/conditions, qualified or missing inputs and source-owned covariance. Optical epsilon/path conversion is not recovery k, protein amount, product attribution or a complete activity score. Repeated representations create no independent evidence or annotation credit.",
        "input_schema": optical_arguments_schema()})
    from gene_annotation_episode.episodic_workflow.root.literature_kinetic_summary_precision_storage import kinetic_operation_schema
    from gene_annotation_episode.episodic_workflow.root.library.literature_kinetic_summary_precision_prompt import SUMMARY_PRECISION_OPERATION_DESCRIPTION
    result.append({"name": "literature.kinetic.populate",
        "description": "Read one source-reported Km, kcat or catalytic-efficiency estimate, or a descriptive comparison of two separately assayed parameters. A single estimate uses numerator and no denominator; request numerator_parameter. Number and unit witnesses can be separate, including a unit in a shared table header in paper or database HTML/XML. Select the complete unit token rather than its surrounding header label or data row. Exclude brackets or parentheses that merely enclose the entire unit. The returned literature_kinetic_cells sheet and numerator_parameter component can supply effect to literature.assay_grading.populate. Comparisons additionally offer difference, ratio and log-contrast components. Each native meaning selection has its own witnesses array: values other than unknown, unspecified or unreported require an authenticated source witness; conflicting requires two distinct source witnesses. Number or unit witnesses elsewhere are not copied into that array automatically. If a meaning cannot be established, select its available unresolved value and retain the gap. Preserve actual molecule/construct, per-row protocols, qualifications and source uncertainty meanings. This native route has no covariance/model source reader; model-dependent evidence cells are not supported here, which is not a finding that the paper lacks covariance. No quotient of reported means, common-condition correction, intrinsic-affinity inference, target transfer or annotation credit. " + SUMMARY_PRECISION_OPERATION_DESCRIPTION,
        "input_schema": kinetic_operation_schema()})
    from gene_annotation_episode.episodic_workflow.root.literature_kinetic_model_storage import kinetic_model_population_schema
    result.append({"name": "literature.kinetic.model.populate",
        "description": "Populate the existing four conditional kinetic log-model cells from an actually received committed native kinetic sheet and an optional received retained model source. Model JSON uses a105_kinetic_log_model_v1 fields except source; provenance is bound from actual bytes. Preserve exact numerator/denominator physical estimate owners, natural-log canonical-parameter basis, full covariance, known/estimated/unknown variance and source interpretation witnesses. Reported SD/SEM/counts never supply covariance. These dependent parameter-contrast statistics are not assay reliability, function probabilities, target transfer or annotation credit.",
        "input_schema": kinetic_model_population_schema()})
    from gene_annotation_episode.episodic_workflow.root.library.literature_binding_interaction_inputs import binding_interaction_arguments_schema
    result.append({"name": "literature.binding.interaction.populate",
        "description": "Read four selected original-image binding cells for two separately assayed source molecular forms and two ligands. Populate native IC50 or reported Hill-fit Kd parameters, within-form ligand ratios and their interaction/log interaction. Preserve actual source meanings, physical-fit identity, uncertain or conflicting readings, units, limits and partial uncertainty; unknown common kind retains raw results without choosing a default. Covariance/model source reading is unimplemented here, not a finding about the paper. No intrinsic-affinity conversion, target transfer or annotation credit.",
        "input_schema": binding_interaction_arguments_schema()})
    from gene_annotation_episode.episodic_workflow.root.literature_binding_interaction_model_storage import binding_interaction_model_population_schema
    result.append({"name": "literature.binding.interaction.model.populate",
        "description": "Populate the existing four conditional binding interaction log-model cells from an actually received committed native interaction sheet and an optional explicit received model packet. The prepared binding_interaction_log_model_v1 JSON omits source; provenance is bound from actual bytes. Keep four exact physical fit owners and canonical estimate keys, natural-log nM basis, full covariance, known/estimated/unknown status and source-defined reporting-event support. No paper-covariance packet producer is supplied here. SD/SEM/counts and distinct preparations do not establish covariance or independence. These dependent parameter-interaction statistics are not intrinsic affinity, reliability, function probabilities, target transfer or annotation credit.",
        "input_schema": binding_interaction_model_population_schema()})
    if ion_discrimination_population:
        from gene_annotation_episode.episodic_workflow.root.library.literature_ion_discrimination_input_contracts import ion_discrimination_population_schema
        result.append({"name": "literature.ion_discrimination.populate",
            "description": "Populate requested A105 ion-discrimination components from exactly possessed corrected activities or original witnessed reported ratios/rate thresholds. Preserve actual ions, molecule/construct, controls, normalization, nonintended differences, quantity meanings, source origin and dependency/uncertainty scope. Reported estimate domains, estimator domains, nominal threshold arithmetic and conditional physical domains remain distinct. No hidden full-sheet acquisition, GHK inversion, reliability probability, target transfer or annotation credit.",
            "input_schema": ion_discrimination_population_schema()})
    if channel_population:
        from gene_annotation_episode.episodic_workflow.root.library.literature_channel_inputs import channel_population_schema
        result.append({"name": "literature.channel.populate",
            "description": "Populate requested source electrical current, voltage, reported conductance and conditional chord/charge/uncertainty sections from exact original number/unit spans and witnessed experimental meanings. Preserve actual molecular arrangement, current definition, reversal applicability, physical measurement identity and original spread meanings. Distinct electrical arrangements cannot supply a common chord. Full supplied primitive covariance is separate from event counts or printed spread; unknown covariance remains unknown. Charge equivalents do not establish ion flux or pore/polypeptide turnover; no overall reliability, target transfer or annotation credit.",
            "input_schema": channel_population_schema()})
    if compiled_assay_population:
        from gene_annotation_episode.episodic_workflow.root.literature_compiled_assay_storage import compiled_assay_operation_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_compiled_assay_prompt import OPERATION_DESCRIPTION
        result.append({"name": "literature.assay.components.populate", "description": OPERATION_DESCRIPTION,
            "input_schema": compiled_assay_operation_schema()})
    if a106_intervention:
        from gene_annotation_episode.episodic_workflow.root.library.literature_intervention_inputs import intervention_population_schema
        from gene_annotation_episode.episodic_workflow.root.literature_intervention_storage import OPERATION_DESCRIPTION as INTERVENTION_DESCRIPTION
        result.append({'name': 'literature.intervention_grading.populate',
            'description': INTERVENTION_DESCRIPTION, 'input_schema': intervention_population_schema()})
        from gene_annotation_episode.episodic_workflow.root.library.literature_a106_subscore import population_schema as subscore_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_a106_task_declaration import TASK
        result.append({'name': 'literature.a106.finalize', 'description': TASK,
            'input_schema': subscore_schema()})
    if assay_grading_population:
        from gene_annotation_episode.episodic_workflow.root.literature_assay_grading_inputs import assay_grading_population_schema as grading_population_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_assay_grading_prompt import ASSAY_GRADING_OPERATION_DESCRIPTION as OPERATION_DESCRIPTION
        result.append({'name': 'literature.assay_grading.populate',
            'description': OPERATION_DESCRIPTION, 'input_schema': grading_population_schema()})
        from gene_annotation_episode.episodic_workflow.root.library.literature_a105_aggregation import aggregation_population_schema
        from gene_annotation_episode.episodic_workflow.root.literature_a105_aggregation_storage import OPERATION_DESCRIPTION as AGGREGATION_DESCRIPTION
        result.append({'name': 'literature.a105.aggregate',
            'description': AGGREGATION_DESCRIPTION, 'input_schema': aggregation_population_schema()})
    if product_partition_population:
        from gene_annotation_episode.episodic_workflow.root.library.literature_product_partition_inputs import product_partition_arguments_schema
        result.append({"name": "literature.product_partition.populate",
            "description": "Populate selected A105 reported product-composition fractions and their dependent sum, signed numerical closure and relative partition. Read exact original number/unit spans; retain basis, preparation, endpoint, stage, denominator, source qualification and competing-contribution evidence. These quantities are not rate, specificity, independent mass balance or molecule-specific attribution. Numerical uncertainty propagation is not implemented.",
            "input_schema": product_partition_arguments_schema()})
    if completion_time_population:
        from gene_annotation_episode.episodic_workflow.root.library.literature_completion_time_inputs import completion_time_arguments_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_completion_time_prompt import COMPLETION_TIME_OPERATION_DESCRIPTION
        result.append({"name": "literature.completion_time.populate",
            "description": COMPLETION_TIME_OPERATION_DESCRIPTION,
            "input_schema": completion_time_arguments_schema()})
    if active_site_population:
        from gene_annotation_episode.episodic_workflow.root.literature_active_site_inputs import active_site_arguments_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_active_site_prompt import ACTIVE_SITE_OPERATION_DESCRIPTION
        result.append({"name": "literature.active_site.populate",
            "description": ACTIVE_SITE_OPERATION_DESCRIPTION,
            "input_schema": active_site_arguments_schema()})
    if parent_depletion_population:
        from gene_annotation_episode.episodic_workflow.root.literature_parent_depletion_inputs import parent_depletion_population_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_parent_depletion_prompt import PARENT_DEPLETION_OPERATION_DESCRIPTION
        result.append({'name':'literature.parent_depletion.populate',
            'description':PARENT_DEPLETION_OPERATION_DESCRIPTION,
            'input_schema':parent_depletion_population_schema()})
    if stoichiometric_balance_population:
        from gene_annotation_episode.episodic_workflow.root.literature_stoichiometric_balance_inputs import stoichiometric_balance_population_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_stoichiometric_balance_prompt import STOICHIOMETRIC_BALANCE_OPERATION_DESCRIPTION
        result.append({'name': 'literature.stoichiometric_balance.populate',
            'description': STOICHIOMETRIC_BALANCE_OPERATION_DESCRIPTION,
            'input_schema': stoichiometric_balance_population_schema()})
    if ratio_source_population:
        from gene_annotation_episode.episodic_workflow.root.literature_ratio_source_storage import ratio_source_population_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_ratio_source_prompt import SOURCE_RATIO_OPERATION_DESCRIPTION
        result.append({"name": "literature.ratio.source.populate",
            "description": SOURCE_RATIO_OPERATION_DESCRIPTION,
            "input_schema": ratio_source_population_schema()})
    if controlled_response_population:
        from gene_annotation_episode.episodic_workflow.root.literature_controlled_response_storage import controlled_response_population_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_controlled_response_prompt import CONTROLLED_RESPONSE_OPERATION_DESCRIPTION
        result.append({"name": "literature.controlled_response.source_v3.populate",
            "description": CONTROLLED_RESPONSE_OPERATION_DESCRIPTION,
            "input_schema": controlled_response_population_schema()})
    if gel_population:
        from gene_annotation_episode.episodic_workflow.root.literature_gel_storage import gel_population_schema
        from gene_annotation_episode.episodic_workflow.root.library.literature_gel_prompt import GEL_OPERATION_DESCRIPTION
        result.append({"name": "literature.gel.populate",
            "description": GEL_OPERATION_DESCRIPTION,
            "input_schema": gel_population_schema()})
    return result


