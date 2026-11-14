"""ComparativeSystems information for existing API launch/results owners."""
from copy import deepcopy

from .bvbrc_appservice_contracts import contract_schema
from .bvbrc_comparative_systems_bundle_contracts import parameters_schema
from .execution_episodes import RESULTS_SCHEMA

_INSTRUCTIONS = '''Compare the stored pathway, subsystem and PLFam/PGFam assignments of the selected BV-BRC genomes. Supply genome_ids and genome_groups as two explicit arrays, including [] for an unused array, with at least one selected input. Preserve their original order and repetitions and supply output_path and output_file explicitly. The service deduplicates its executed genome union; a group path or basename does not establish its original expanded membership. This operation accepts selected genomes without requiring a candidate function or publicly searchable gene name. A sequence investigation may motivate separate genome acquisition or annotation; this tool does not submit that additional work. ComparativeSystems computes all three native views. Select the result views needed for the question without inventing a native mode or recipe switch.

Commission the existing launch episode with the selected job, scope, constraints and requested typed handoff. Its API child uses api.bvbrc_appservice.prepare to validate the definition, original parameters, supplied inputs and explicit output destination without submission. Explicit Workspace transfers are separate available operations. submit uses the exact preparation receipt for one AppService.start_app2 call and retains the original task. The existing API monitoring task can select status, stdout or stderr observations. Preserve native timing, state and logs; the episode decides whether further observation or repair is useful.

Commission the existing results episode for the original task. task_info(job_result_id), Workspace metadata, manifest bytes, exact manifest_member selections, capabilities and downloads are available operations. Their selection belongs to the episode. A guessed output basename, folder or HTML page does not establish artifact custody. Retain complete selected bytes and their original task associations. Select adapter bvbrc_comparative_systems version 1 with analysis_id, document_selection, population_assignments, producer_evidence_selections, supplied_data_selection, reference_memberships and calculation_parameters. Each document names its role and one of the six declared source-format profiles. Before acquisition, input.kind=requirement selects a parent requirement_id. A possessed artifact can instead use input.kind=possessed_artifact with its exact source_ref and raw_artifact_ref. Select authoritative_views explicitly; multiple satisfying artifacts remain ambiguous. JSON table fields contain TSV strings and are not generic arrays or BLAST JSON. A nullable producer_evidence_id maps only explicit supplied producer evidence; a parser profile cannot identify a deployed version.

Native pathway/subsystem outputs from the inspected producer drop an object from each nonempty API chunk. Retain the original report and its represented population; source inspection alone does not establish a remote producer version. Its conservation quantities describe stored assignment occupancy or feature density, not biochemical completion. Family count strings are decoded only at an unambiguous exact width; overflow leaves per-genome counts unavailable while independent aggregates survive. Duplicate records, missing features in inner joins, imputed categories, unknown releases and unknown group expansion remain qualified. prop_active is a reported any-record genome fraction, not an activity probability.

Supply additional Data API results only when requested measurements require them. Their exact sources and retained bytes must be explicitly selected as supplied_contents or SourceEvidence.content. Qualified Data publications retain original queries, selected fields, pagination and snapshot limitations. Later data do not reconstruct an earlier job. Explicit reference memberships require selected qualified pathway_ref/subsystem_ref records; role IDs and names are not zipped. Unknown releases, immutable snapshots and original-task group attestations remain unknown. Source-only metadata or caller flags cannot attest execution or deployment.

The numerical sheet retains native measurements separately from calculated components. Calculators consume that saved sheet and explicit parameters and make no acquisition, submission, model call or resource choice. Request finite measurement, computed_measurement, ratio, population, membership, requirement, qualification or request_status selectors with exact cardinality and availability meaning. The seven typed return families copy only the selected saved facts and qualifications through the original parent form. Keep measured zero, missing, failed, truncated, incompatible and invalid distinct. Full raw data and numerical sheets remain stored. Parsing, calculation and forwarding create no extra completed action or credit. This API binding does not establish live service execution or local/HPC deployment.'''


def comparative_systems_tool_contracts(*, resource_id: str, assignment_schema: dict) -> list[dict]:
    if type(resource_id) is not str or not resource_id.strip() or '\0' in resource_id:
        raise ValueError('comparative_systems_explicit_api_resource_required')
    if type(assignment_schema) is not dict:
        raise ValueError('comparative_systems_api_assignment_schema_required')
    launch = deepcopy(assignment_schema)
    text = {'type': 'string', 'minLength': 1, 'pattern': r'^\S(?:.*\S)?$'}
    arrays = {key: {'type': 'array', 'items': deepcopy(text)} for key in ('genome_ids', 'genome_groups')}
    launch.setdefault('allOf', []).append({'properties': {
        'resource_id': {'const': resource_id}, 'service': {'const': 'bvbrc_appservice'},
        'request': {'properties': {'required_application_id': {'const': 'ComparativeSystems'},
            'parameters': {'type': 'object', 'required': ['genome_ids', 'genome_groups', 'output_path', 'output_file'],
                'properties': {**arrays, 'output_path': deepcopy(text), 'output_file': deepcopy(text)},
                'anyOf': [{'properties': {key: {'minItems': 1}}} for key in arrays]}}}}})
    selector = contract_schema('ResultSelector')
    selector['$id'] = 'urn:gene-annotation:comparative-systems:selector:1'
    parameters = parameters_schema()
    parameters['$id'] = 'urn:gene-annotation:comparative-systems:parameters:1'
    selector.setdefault('allOf', []).append({'properties': {
        'endpoint': {'const': 'requested_projection'},
        'adapter': {'type': 'object', 'required': ['adapter_id', 'adapter_version', 'parameters'],
            'properties': {'adapter_id': {'const': 'bvbrc_comparative_systems'},
                'adapter_version': {'const': '1'}, 'parameters': parameters}}}})
    results = deepcopy(RESULTS_SCHEMA)
    results['properties']['selector'] = selector
    return [{'name': 'bvbrc.comparative_systems', 'description':
        'Compare stored pathway, subsystem and PLFam/PGFam assignments of selected BV-BRC genomes; retain native measurements, explicit populations and qualified numerical components.',
        'resources': 'api', 'instructions': _INSTRUCTIONS,
        'input_schema': {'oneOf': [launch, results]},
        'invocation_route': {'kind': 'commission', 'routes': [
            {'entry_role': 'launch', 'resource_id': resource_id, 'resource_role': 'launch_api'},
            {'entry_role': 'results', 'resource_id': resource_id, 'resource_role': 'results'}]}}]


__all__ = ['comparative_systems_tool_contracts']


def validate_comparative_request(request):
    """Check actual selected API operands without rewriting any native value."""
    parameters = request['parameters']
    for key in ('genome_ids', 'genome_groups'):
        values = parameters.get(key)
        if type(values) is not list or any(type(value) is not str or not value.strip()
                or value != value.strip() or '\0' in value for value in values):
            raise ValueError('comparative_systems_original_' + key + '_required')
    if not (parameters['genome_ids'] or parameters['genome_groups']):
        raise ValueError('comparative_systems_original_population_required')
    for key in ('output_path', 'output_file'):
        value = parameters.get(key)
        if type(value) is not str or not value.strip() or '\0' in value:
            raise ValueError('comparative_systems_explicit_' + key + '_required')
    return deepcopy(request)
