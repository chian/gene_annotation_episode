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
    "JSON. Select each document's actual source and artifact; the primary document "
    "is explicit. Supply representation correspondence before treating JSON and TSV "
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


def proteome_tool_contracts(*, resource_id: str, assignment_schema: dict) -> list[dict]:
    """Describe a configured provider without performing discovery or execution."""
    if type(resource_id) is not str or not resource_id.strip() or '\0' in resource_id:
        raise ValueError('proteome_explicit_api_resource_required')
    if type(assignment_schema) is not dict:
        raise ValueError('proteome_api_assignment_schema_required')
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
    selector = contract_schema('ResultSelector')
    selector['$id'] = 'urn:gene-annotation:proteome:selector:1'
    parameters = parameters_schema()
    # This embedded schema has its own definitions. Give it a resource identity
    # so its local references cannot resolve against the host selector instead.
    parameters['$id'] = 'urn:gene-annotation:proteome:parameters:1'
    selector.setdefault('allOf', []).append({'properties': {
        'endpoint': {'const': 'requested_projection'},
        'adapter': {'type': 'object', 'required': ['adapter_id', 'adapter_version', 'parameters'],
            'properties': {'adapter_id': {'const': 'bvbrc_proteome'},
                'adapter_version': {'const': '1'}, 'parameters': parameters}}}})
    results = deepcopy(RESULTS_SCHEMA)
    results['properties']['selector'] = selector
    return [{'name': 'bvbrc.proteome_comparison', 'description':
        'Compare selected genome protein sets with BV-BRC GenomeComparison; retain original '
        'matches, reported first-HSP measurements and explicit comparison populations.',
        'resources': 'api', 'instructions': _INSTRUCTIONS,
        'input_schema': {'oneOf': [launch, results]},
        'invocation_route': {'kind': 'commission', 'routes': [
            {'entry_role': 'launch', 'resource_id': resource_id, 'resource_role': 'launch_api'},
            {'entry_role': 'results', 'resource_id': resource_id, 'resource_role': 'results'}]}}]


__all__ = ['proteome_tool_contracts']
