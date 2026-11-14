"""GenomeAlignment information for actual API launch/results commissions."""
from copy import deepcopy

from .bvbrc_appservice_contracts import contract_schema
from .bvbrc_genome_alignment_bundle_contracts import parameters_schema
from .execution_episodes import RESULTS_SCHEMA


_INSTRUCTIONS = (
    "Align the supplied BV-BRC genomes to compare conserved regions, rearrangements and "
    "sequence correspondence. Assign the original genome_ids list, output_path and "
    "output_file to the GenomeAlignment AppService application. Preserve repeated input "
    "occurrences. Its native recipe choices are progressiveMauve and mauveAligner. Keep "
    "the selected recipe and numerical options unchanged; requested options, native "
    "manifest parameters and observed executable arguments are distinct facts. A declared "
    "recipe does not determine the acquired file's format. The retained service definition "
    "does not establish current deployment or that its default was used.\n\n"
    "Commission the existing launch episode and its selected API child. "
    "api.bvbrc_appservice.prepare validates the chosen application definition, original "
    "parameters, input bindings and output destination without submitting. Select any "
    "needed Workspace preparation/transfer separately. submit performs the selected "
    "AppService.start_app2 call and retains its original task identity. Monitor with the "
    "resource's generic monitoring task and selected status/query_tasks or task_info "
    "observations. Preserve native states, timestamps and actual logs. An episode chooses "
    "further observations and repairs; these instructions supply no polling schedule, "
    "hidden retry, resource substitution or independent annotation-confidence score.\n\n"
    "Use the existing results episode to acquire selected original-task outputs. "
    "task_info(job_result_id) supplies a UUID; workspace_metadata retrieves the actual "
    "job_result object's type/path. Select that receipt_row for its capability/download, "
    "then select exact manifest_member output indices for scientific files. Keep native "
    "receipt relationships and full bytes. A folder listing, matching basename or HTML "
    "report does not prove scientific format or immutable producing-run byte identity. "
    "If retained stdout is needed to extract observed command arguments, explicitly "
    "supply its actual task-info receipt as supplied_metadata and its native snapshot "
    "ContentBinding as supplied_contents. A receipt alone does not expose its log.\n\n"
    "Select bvbrc_genome_alignment version 1 in the result selector. Its parameters "
    "contain analysis_id, document_slots and calculation_plan. Primary native formats "
    "are mauve_v4 (declared version null or 4) and mauve1_xmfa (null or Mauve1); mode "
    "is null. The XMFA reader uses dialect mauve1 and DNA. Sidecar readers are "
    "mauve_backbone/libmems_signed_coordinate_pairs_v1 and "
    "mauve_bbcols/libmems_interval_columns_members_v1, with null declared version/mode. "
    "Select roles genome_alignment_primary, genome_alignment_backbone or "
    "genome_alignment_bbcols explicitly. Visualization JSON is not an alignment matrix. "
    "Do not join BBCols interval numbers to exported XMFA blocks without actual mapping "
    "evidence. Mauve1 member numbers are one-based; v4/sidecar member indices are zero-based.\n\n"
    "Request the exact calculations needed: v4 segment correspondence/coverage, backbone "
    "coverage, BBCols column unions, XMFA alignment counts, XMFA coverage, forward "
    "coordinates or inverse coordinates. Preserve selection populations, overlap and "
    "gap/ambiguity policies. Native declared lengths differ from authenticated original "
    "source lengths. Original-source coverage and feature coordinates require actual "
    "source and transformation evidence; a current refetch cannot prove historical "
    "staged bytes. Missing denominators stay missing. Native parsers and metadata "
    "extractors populate the numerical sheet; separate deterministic calculators use "
    "that sheet and explicit parameters without acquisition, new jobs or model calls. "
    "Retain full native outputs, sheet and calculated components. Recalculate saved "
    "data with changed parameters without rewriting historical observations.\n\n"
    "Use requested_form_schema's finite selectors for numerical measurements, v4 "
    "segments, backbone spans, BBCols intervals, coverage intervals, XMFA native/source/"
    "original/inverse coordinates, request status, requirements and qualifications. "
    "The corresponding twelve bvbrc_genome_alignment return sources pass only the "
    "parent's requested fields through the existing typed boundary. Keep measured zero, "
    "missing, incompatible, partial and unavailable distinct. Alignment identity and "
    "coverage are measurements, not calibrated gene-function probabilities. This API "
    "route does not claim local/HPC deployment or a verified live service execution."
)


def genome_alignment_tool_contracts(*, resource_id: str, assignment_schema: dict) -> list[dict]:
    if type(resource_id) is not str or not resource_id.strip() or '\0' in resource_id:
        raise ValueError('genome_alignment_explicit_api_resource_required')
    if type(assignment_schema) is not dict:
        raise ValueError('genome_alignment_api_assignment_schema_required')
    launch = deepcopy(assignment_schema)
    launch.setdefault('allOf', []).append({'properties': {
        'resource_id': {'const': resource_id}, 'service': {'const': 'bvbrc_appservice'},
        'request': {'properties': {'required_application_id': {'const': 'GenomeAlignment'},
            'parameters': {'type': 'object', 'required': ['genome_ids', 'output_path', 'output_file'],
                'properties': {'genome_ids': {'type': 'array', 'minItems': 1,
                    'items': {'type': 'string', 'minLength': 1}},
                    'output_path': {'type': 'string', 'minLength': 1},
                    'output_file': {'type': 'string', 'minLength': 1},
                    'recipe': {'enum': ['progressiveMauve', 'mauveAligner', None]}}}}}}})
    selector = contract_schema('ResultSelector')
    selector['$id'] = 'urn:gene-annotation:genome-alignment:selector:1'
    selector.setdefault('allOf', []).append({'properties': {'adapter': {'type': 'object',
        'required': ['adapter_id', 'adapter_version', 'parameters'], 'properties': {
            'adapter_id': {'const': 'bvbrc_genome_alignment'}, 'adapter_version': {'const': '1'},
            'parameters': parameters_schema()}}}})
    results = deepcopy(RESULTS_SCHEMA)
    results['properties']['selector'] = selector
    return [{'name': 'bvbrc.genome_alignment', 'description':
        'Align selected genomes with BV-BRC GenomeAlignment and retain Mauve sequence correspondence, '
        'rearranged intervals, overlap-aware coverage and explicit native/source coordinates.',
        'resources': 'api', 'instructions': _INSTRUCTIONS,
        'input_schema': {'oneOf': [launch, results]}, 'invocation_route': {'kind': 'commission', 'routes': [
            {'entry_role': 'launch', 'resource_id': resource_id, 'resource_role': 'launch_api'},
            {'entry_role': 'results', 'resource_id': resource_id, 'resource_role': 'results'}]}}]


__all__ = ['genome_alignment_tool_contracts']
