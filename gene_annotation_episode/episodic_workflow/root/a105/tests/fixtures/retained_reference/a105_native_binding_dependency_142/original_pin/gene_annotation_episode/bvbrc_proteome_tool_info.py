"""GenomeComparison information for existing API launch/results commissions."""
from copy import deepcopy

from .bvbrc_appservice_contracts import contract_schema
from .bvbrc_proteome_bundle_contracts import parameters_schema
from .execution_episodes import RESULTS_SCHEMA


_INSTRUCTIONS = (
    "Compare the supplied protein sets with BV-BRC GenomeComparison to examine shared "
    "protein matches and differences between selected genomes. Supply the original "
    "genome_ids, Workspace protein FASTA paths in user_genomes, and Workspace "
    "feature_group paths in user_feature_groups as applicable. Preserve their order "
    "and repeated occurrences. reference_genome_index is one-based in the concatenation "
    "of those three arrays, in that order. Supply an explicit index when its identity "
    "must be established; an omitted option does not prove that a declared default was "
    "used. Supply output_path and output_file explicitly. min_ident, min_seq_cov, "
    "min_positives and max_e_val are native application parameters; preserve the "
    "selected values. Submitted parameters, observed effective parameters and later "
    "score-calculation parameters are distinct.\n\n"
    "Commission the existing launch episode with the requested comparison, scope and "
    "resource constraints. Its API child uses api.bvbrc_appservice.prepare to validate "
    "the chosen definition, original parameters, explicit input bindings and Workspace "
    "destination without submission. Select required Workspace creation and upload "
    "operations separately. submit makes the selected AppService.start_app2 request "
    "and retains the response and original task identity. Monitoring uses the API "
    "resource's generic monitoring task with selected query_tasks, stdout or stderr "
    "observations. Retain native states, timing and logs. The episode chooses any "
    "further observation or repair; there is no automatic retry or polling schedule.\n\n"
    "Commission the existing results episode to acquire the original task's selected "
    "artifacts. task_info(job_result_id) gives the job-result UUID; workspace_metadata "
    "obtains its actual object. Acquire the selected manifest through its capability, "
    "then select exact manifest_member output indices for scientific files. Preserve "
    "complete bytes, task associations and acquisition completeness. A basename, "
    "folder listing, HTML page or stable UUID does not establish a numerical format "
    "or immutable producing-run bytes.\n\n"
    "Select bvbrc_proteome version 1 for the requested projection. Its parameters "
    "specify analysis_id, native_documents, primary_document_id, supplied_data_evidence "
    "and calculation_parameters. Select the actual proteome_native_projection role "
    "and genome_comparison_json_v1 or genome_comparison_tsv_v1 format, with null "
    "version and mode. These are GenomeComparison's custom formats, not NCBI BLAST "
    "JSON. Before acquisition, select each document by its parent-declared result "
    "requirement_id; the unique acquired bundle member must retain that selected "
    "requirement, role and format. Do not predict future source or artifact identities. "
    "Already retained documents can instead select their exact source_ref and "
    "raw_artifact_ref. The primary document is explicit. Missing or multiple matching "
    "members remain missing or ambiguous. Supply representation correspondence before treating JSON and TSV "
    "as interchangeable observations.\n\n"
    "Supply original parameter, FASTA and feature/genome/sequence metadata evidence "
    "explicitly when requested calculations need it. Keep original input slots, "
    "duplicate occurrences, sequence identities and metadata joins distinct. Current "
    "database records do not prove the bytes staged in an earlier job. Missing exact "
    "executed-input counts remain missing; do not infer a no-match fraction from "
    "returned rows alone. Retained input files are not proof they were executed.\n\n"
    "The current numerical path preserves reported first-HSP identity, the legacy "
    "subject-endpoint-difference measurement, native hit categories, explicit bound "
    "occurrence counts and selected-population summaries. It does not reconstruct "
    "discarded HSPs or treat endpoint differences as full alignment coverage. Native "
    "measurements, supplied metadata, populated sheet and calculated components are "
    "retained separately. Calculators consume the saved sheet and explicit thresholds; "
    "changing thresholds does not rerun the service or rewrite historical results. "
    "Native match categories are categories, not calibrated annotation probabilities.\n\n"
    "Request only the needed measurement, ratio, population, association, selection, "
    "requirements, qualifications and request_status fields using the provider's "
    "finite requested-form selectors. Their eight typed return families carry the "
    "requested original facts to the receiving episode. Preserve measured zero, "
    "unavailable, invalid, incompatible and partial results separately. Full native "
    "artifacts and sheets remain retained for later use; they are not copied into "
    "the parent's prompt. This API contract does not establish a live service run "
    "or local/HPC deployment."
)


_DIRECTIONAL_INSTRUCTIONS = (
    "Select bvbrc_proteome version 2 explicitly when the requested result includes retained "
    "complete directional BLASTP text. Supply analysis_id, native_documents, primary_document_id, "
    "supplied_data_evidence, calculation_parameters, directional_documents and "
    "directional_calculation_parameters. A directional-only selection has native_documents=[], "
    "primary_document_id=null and calculation_parameters=null. Each directional document names "
    "its document_id and report_key plus either a parent-declared requirement_id before acquisition "
    "or an already possessed exact source_ref/raw_artifact_ref pair. Select role "
    "proteome_directional_report and format ncbi_blastall_blastp_pairwise_text_v1, mode "
    "protein_database_search_pairwise_display, version 2.0.11, 2.2.2, 2.2.21 or null, "
    "producer_source_ref and transformation_evidence. A declared version must match the retained "
    "banner; null makes no version claim. No producer identity or executed input roster is inferred. "
    "The acquisition must carry the selected requirement membership. Missing or ambiguous members "
    "remain explicit failures; document_id resolves its actual saved report occurrence even when "
    "an earlier selected document was not acquired. Nonzero-offset fragments cannot substitute "
    "for a complete report; valid zero-origin prefixes retain their actual completeness.\n\n"
    "Supply the exact directional parameter version bvbrc_proteome_directional_parameters_v1, "
    "formula_version displayed_blastp_correspondence_v1, amino_acid_alphabet standard20, an explicit "
    "ratio_decimal_places and rounding half_even. The reader retains every displayed query, "
    "description, subject, HSP and traceback block. The numerical sheet preserves reported counts "
    "and scores separately from trace columns, resolved amino-acid identities/substitutions, "
    "unresolved/stop populations, gaps, per-axis interval unions and correspondence conflicts. "
    "Coverage uses the same occurrence's reported length and saved half-open coordinate intervals. "
    "Resolved-only identity includes its unresolved and stop population. A missing native Gaps "
    "clause stays missing even when displayed traceback gaps measure zero. Native expectation "
    "values remain statistics, with printed zero identified as unknown reporting precision; "
    "they do not select a correspondence or establish function confidence.\n\n"
    "Request finite directional_count, directional_fraction, directional_coverage, "
    "directional_native_integer, directional_native_decimal, directional_state, "
    "directional_extremum, directional_intervals, directional_columns, directional_edges, "
    "directional_conflicts, directional_support, directional_issues and directional_requirements "
    "selectors at their declared report/query/subject/HSP/block scopes and actual native ordinals. "
    "Pages require explicit offset and limit and return total_count, returned_count and next_offset. "
    "Their matching bvbrc_proteome_directional_* typed sources deliver only requested facts. "
    "Decimal values use exact sign/digits/exponent tuples, preserving values such as 1e-900; "
    "ratios retain unreduced numerator and denominator alongside their saved decimal rendering. "
    "Source, parameter, operand, support, state and requirement references retain each quantity's "
    "meaning. Full reports and sheets remain in retained artifacts.\n\n"
    "Version 2 also accepts the unchanged finite legacy selectors for separately selected custom "
    "GenomeComparison JSON/TSV native_documents. Their first-HSP identity and endpoint-difference "
    "measurements keep their original meaning. Mixed selections do not join legacy rows to HSPs "
    "without evidence. Supply original input and metadata evidence explicitly where required; "
    "retained files and current database records do not prove executed input occurrence counts. "
    "Directional_operand_binding remains unbound. Saved returns validate the original immutable "
    "publication and copy its requested facts without rerunning parsing or calculation. A newly "
    "selected recalculation uses saved observations and explicit changed parameters, preserving "
    "earlier results and history. Availability of a prefix fact does not complete a required "
    "artifact acquisition. This binding establishes neither a live GenomeComparison run nor "
    "deployed producer retention, executed rosters, row-to-HSP linkage or local/HPC deployment."
)


def proteome_tool_contracts(*, resource_id: str, assignment_schema: dict,
                           adapter_versions: tuple[str, ...] = ("1",)) -> list[dict]:
    """Describe a configured provider without performing discovery or execution."""
    if type(resource_id) is not str or not resource_id.strip() or '\0' in resource_id:
        raise ValueError('proteome_explicit_api_resource_required')
    if type(assignment_schema) is not dict:
        raise ValueError('proteome_api_assignment_schema_required')
    if (type(adapter_versions) is not tuple or not adapter_versions
            or any(type(v) is not str or v not in ('1', '2') for v in adapter_versions)
            or len(adapter_versions) != len(set(adapter_versions))):
        raise ValueError('proteome_explicit_adapter_versions_required')
    launch = deepcopy(assignment_schema)
    launch.setdefault('allOf', []).append({'properties': {
        'resource_id': {'const': resource_id}, 'service': {'const': 'bvbrc_appservice'},
        'request': {'properties': {'required_application_id': {'const': 'GenomeComparison'},
            'parameters': {'type': 'object', 'required': ['output_path', 'output_file'],
                'properties': {'output_path': {'type': 'string', 'minLength': 1},
                    'output_file': {'type': 'string', 'minLength': 1},
                    'genome_ids': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}},
                    'user_genomes': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}},
                    'user_feature_groups': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}},
                    'reference_genome_index': {'type': 'integer', 'minimum': 1}}}}}}})
    result_variants = []
    for version in adapter_versions:
        selector = contract_schema('ResultSelector')
        selector['$id'] = 'urn:gene-annotation:proteome:selector:' + version
        if version == '1':
            parameters = parameters_schema()
        else:
            from .bvbrc_proteome_bundle_v2_contracts import parameters_schema_v2
            parameters = parameters_schema_v2()
        # Each embedded schema owns its definitions and explicit resource ID.
        parameters['$id'] = 'urn:gene-annotation:proteome:parameters:' + version
        selector.setdefault('allOf', []).append({'properties': {
            'endpoint': {'const': 'requested_projection'},
            'adapter': {'type': 'object', 'required': ['adapter_id', 'adapter_version', 'parameters'],
                'properties': {'adapter_id': {'const': 'bvbrc_proteome'},
                    'adapter_version': {'const': version}, 'parameters': parameters}}}})
        results = deepcopy(RESULTS_SCHEMA)
        results['properties']['selector'] = selector
        result_variants.append(results)
    instructions = (_INSTRUCTIONS if '1' in adapter_versions else _INSTRUCTIONS.split('Select bvbrc_proteome version 1')[0])
    if '2' in adapter_versions:
        instructions += '\n\n' + _DIRECTIONAL_INSTRUCTIONS
    description = ('Compare selected genome protein sets with BV-BRC GenomeComparison; retain original '
        'matches, reported first-HSP measurements and explicit comparison populations.' if adapter_versions == ('1',) else
        'Compare selected genome protein sets with BV-BRC GenomeComparison; retain explicitly selected '
        'native measurements and full directional correspondence, coverage and support populations using adapter version '
        + ', '.join(adapter_versions) + '.')
    return [{'name': 'bvbrc.proteome_comparison', 'description':
        description, 'resources': 'api', 'instructions': instructions,
        'input_schema': {'oneOf': [launch, *result_variants]},
        'invocation_route': {'kind': 'commission', 'routes': [
            {'entry_role': 'launch', 'resource_id': resource_id, 'resource_role': 'launch_api'},
            {'entry_role': 'results', 'resource_id': resource_id, 'resource_role': 'results'}]}}]


__all__ = ['proteome_tool_contracts']
