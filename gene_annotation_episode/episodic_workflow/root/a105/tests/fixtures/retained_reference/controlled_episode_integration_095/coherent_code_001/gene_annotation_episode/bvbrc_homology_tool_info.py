"""Scientific Homology modes as existing launch/results commission contracts.

This module supplies information only. It creates no job, discovers no service,
and adds no direct execution operation to a scientific episode.
"""
from copy import deepcopy

from .bvbrc_appservice_contracts import contract_schema
from .bvbrc_homology_bundle_adapter import ADAPTER_ID, ADAPTER_VERSION, PARAMETERS_SCHEMA
from .execution_episodes import RESULTS_SCHEMA


_DESCRIPTIONS = {
    'database_identification': (
        'Identify candidate functions from the complete returned BV-BRC Homology BLAST hit '
        'population, preserving alignments, function assignments, taxa and source measurements.'),
    'pairwise_correspondence': (
        'Measure aligned residues, substitutions, gaps and coverage between supplied sequences '
        'using BV-BRC Homology BLAST with an explicitly evidenced single-sequence reference.'),
}
_MODE_INSTRUCTIONS = {
    'database_identification': (
        'Select the original query and explicit database or supplied reference population. '
        'Retain every returned hit, description and HSP, the program and native thresholds, '
        'and any hit limit; the returned population is not the complete database. '
        'Supply exact query/member mappings and source-backed function, taxon and reference '
        'metadata when available. Never infer a function from a hit title or a metadata join '
        'from taxon alone. The numerical sheet retains native scores, coordinate correspondence, '
        'coverage denominators, duplicate groups, taxonomy and source measurements. Explicit '
        'database-population measurements are needed for representation adjustment. Conditional '
        'function weights use inspectable parameters; they are not calibrated annotation '
        'probabilities. Missing assignments or population data remain missing.'),
    'pairwise_correspondence': (
        'Supply the query and exactly one reference sequence, with source-backed sequence '
        'identities, lengths, molecule types and evidence that the submitted reference population '
        'contains only that sequence. One returned hit does not establish a pairwise experiment. '
        'Pass the original reference input and its retained member/inventory source through '
        'the results selector supplied_metadata. The deterministic check compares complete '
        'submitted FASTA, sequence digest, length, molecule and actual native hit identifiers. '
        'For retained reference files, supply a source-backed {content, text} value containing '
        'the original ContentBinding and complete FASTA text; a remote path alone is insufficient. '
        'Any explicit member-to-native mapping must retain its exact native ordinals and ID. '
        'Retain every HSP and its actual coordinate correspondence, including translated units, '
        'strand, overlapping positions, substitutions and gaps. Coverage uses unique paired '
        'positions divided by the full corresponding operand length; span coverage has a '
        'different meaning. Keep native alignment scores, but do not use database E-value as '
        'paired-sequence relevance. No database function-weight model applies to this mode.'),
}
_EXECUTION_INSTRUCTIONS = (
    'Use the existing launch episode and its selected API child for the original Homology '
    'assignment; the supplied invocation contract also includes the existing results assignment. '
    'The version field distinguishes these two actual commission payloads. Select native '
    'blastp, blastn, blastx, tblastn or tblastx and explicit native input/database parameters. '
    'api.bvbrc_appservice.prepare validates the original application and inputs without '
    'submitting. workspace_metadata, workspace_create and upload provide separately selected '
    'preparation or transfer operations when needed. submit performs the selected start_app2 '
    'request and retains its original task identity. Monitoring uses the existing monitor '
    'episode and separately selected query_tasks, stdout or stderr observations; logs do not '
    'declare execution state, and no polling schedule is prescribed. The results episode '
    'can select task_info, workspace_metadata, list_outputs, download_capability and download '
    'to acquire the original task manifest and actual output bytes. Preserve original task, '
    'Workspace path/UUID and manifest associations. An HTML report, basename or JSON suffix '
    'does not identify the numerical format. Declare the actual raw BLAST JSON, transformed '
    'Homology JSON or tabular representation and required fields; opaque archives remain '
    'unparsed. The bound deterministic parser fills the numerical sheet, and a separate '
    'calculator supplies requested quantities during the selected acquisition action. '
    'Saved sheets permit explicit recalculation without another service call. Request only '
    'the needed numerical fields or conditional distributions through the typed Homology '
    'return sources. Full bytes, sheets and components remain retained. Missing inputs become '
    'explicit acquisition requirements; partial, failed, unknown and measured zero remain '
    'distinct. This library information grants no direct scientific execution and does not '
    'establish live service authentication, deployment or annotation correctness.'
)


def homology_tool_contracts(*, resource_id, assignment_schema):
    """Return two information rows describing real, separately chosen commissions."""
    if type(resource_id) is not str or not resource_id or '\0' in resource_id:
        raise ValueError('homology_explicit_api_resource_required')
    if not isinstance(assignment_schema, dict):
        raise ValueError('homology_api_assignment_schema_required')
    launch = deepcopy(assignment_schema)
    launch.setdefault('allOf', []).append({'properties': {
        'resource_id': {'const': resource_id}, 'service': {'const': 'bvbrc_appservice'},
        'request': {'properties': {'required_application_id': {'const': 'Homology'}}}}})
    rows = []
    for mode, description in _DESCRIPTIONS.items():
        parameters = deepcopy(PARAMETERS_SCHEMA)
        parameters['$id'] = 'urn:gene-annotation:homology:parameters:' + mode
        parameters['properties']['scientific_mode'] = {'const': mode}
        if mode == 'pairwise_correspondence':
            parameters['properties']['database_model'] = {'type': 'null'}
        selector = contract_schema('ResultSelector')
        selector['$id'] = 'urn:gene-annotation:homology:selector:' + mode
        selector['allOf'] = [{'properties': {'adapter': {'type': 'object',
            'properties': {'adapter_id': {'const': ADAPTER_ID},
                'adapter_version': {'const': ADAPTER_VERSION}, 'parameters': parameters},
            'required': ['adapter_id', 'adapter_version', 'parameters']}}}]
        results = deepcopy(RESULTS_SCHEMA)
        results['properties']['selector'] = selector
        rows.append({'name': 'bvbrc.homology.' + mode, 'description': description,
            'resources': 'api',
            'instructions': _MODE_INSTRUCTIONS[mode] + ' ' + _EXECUTION_INSTRUCTIONS,
            'input_schema': {'oneOf': [deepcopy(launch), results]},
            'invocation_route': {'kind': 'commission', 'routes': [
                {'entry_role': 'launch', 'resource_id': resource_id, 'resource_role': 'launch_api'},
                {'entry_role': 'results', 'resource_id': resource_id, 'resource_role': 'results'}]}})
    return rows


__all__ = ['homology_tool_contracts']
