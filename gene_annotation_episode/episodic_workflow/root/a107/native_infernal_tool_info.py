"""Real Infernal tool information and separate local commissioning contracts."""
from __future__ import annotations

from copy import deepcopy
import re

from .native_infernal_contracts import (NATIVE_INFERNAL_REQUESTED_JOB_SCHEMA,
    PROGRAMS, finite_json_copy, operand_contract, output_contract, _path)


_DESCRIPTION = {
    'cmsearch': 'Search supplied RNA covariance models against supplied nucleotide sequences.',
    'cmscan': 'Search supplied nucleotide sequences against an explicitly supplied pressed covariance-model database.',
    'cmalign': 'Align supplied nucleotide sequences to one supplied RNA covariance model.',
}
_MEANING = {
    'cmsearch': 'The native query is the model and the native target is the physical sequence. '
        'Retain every reported hit, including reporting-only hits, bit score, E-value, bias, GC, '
        'strand, truncation and separate model/sequence coordinates. Formats 1 and 3 differ in '
        'whether model and sequence lengths are reported. Preserve the full native output and '
        'any selected included-hit alignment; absence of a reported hit is conditional on the '
        'actual search settings and input population.',
    'cmscan': 'The native query is the physical sequence and the native target is the model. '
        'Supply all four actual cmpress companions with their model database. Index preparation '
        'is separate selected work. Formats 1, 2 and 3 have distinct fields; format 2 retains '
        'clan and overlapping-hit relationships. Keep all reported hits, native scores, strand, '
        'truncation and actual row associations. Overlapping or repeated hits are not independent '
        'evidence, and identical names do not establish identical input records.',
    'cmalign': 'Retain Stockholm rows, RF, SS_cons, posterior bins, the native score table and '
        'insertion information. A selected local-end file is valid for local alignment, not -g. '
        'Keep original sequence correspondence, model occupancy, insertions, rendered gaps and '
        'local ends distinct. A rendered gap alone may not distinguish deletion from an unvisited '
        'model position. Posterior characters give probability intervals; native average posterior '
        'is a separate measurement. Preserve algorithm, truncation, banding and seed settings. '
        'Sampled alignments remain sampled; inherited --mapali rows remain inherited.',
}


def validate_native_infernal_bindings(value):
    rows = finite_json_copy(value)
    if type(rows) is not list:
        raise ValueError('native_infernal_explicit_binding_rows_required')
    seen = set()
    for row in rows:
        if (type(row) is not dict or set(row) != {'program', 'software'}
                or row['program'] not in PROGRAMS):
            raise ValueError('native_infernal_invalid_binding')
        software = row['software']
        if (type(software) is not dict or set(software) != {'executable', 'sha256', 'engine_version'}
                or type(software['executable']) is not str
                or type(software['sha256']) is not str
                or re.fullmatch(r'[0-9a-f]{64}', software['sha256']) is None
                or software['engine_version'] is not None and (type(software['engine_version']) is not str
                    or not software['engine_version'] or '\x00' in software['engine_version'])):
            raise ValueError('native_infernal_invalid_bound_software')
        _path(software['executable'], absolute=True)
        if row['program'] in seen:
            raise ValueError('native_infernal_duplicate_bound_program')
        seen.add(row['program'])
    return rows


def native_infernal_tool_contracts(bindings, *, resource_kind, resource_id):
    if resource_kind != 'local':
        raise ValueError('native_infernal_resource_binding_unfinished:' + str(resource_kind))
    if type(resource_id) is not str or not resource_id or '\x00' in resource_id:
        raise ValueError('native_infernal_explicit_resource_required')
    entries = []
    for binding in validate_native_infernal_bindings(bindings):
        program = binding['program']
        inputs, optional_inputs = operand_contract(program)
        outputs, optional_outputs = output_contract(program)
        instructions = ('Supply ' + ', '.join(inputs) + '. '
            + ('Optional inputs: ' + ', '.join(optional_inputs) + '. ' if optional_inputs else '')
            + 'Retain ' + ', '.join(outputs) + '. '
            + ('Optional outputs: ' + ', '.join(optional_outputs) + '. ' if optional_outputs else '')
            + _MEANING[program] + ' '
            'Use exact supplied input identities, formats and native options. Unknown lengths, '
            'input-record associations and search-population quantities remain unknown. Commission '
            'the selected job through launch and its configured local-compute child. The child '
            'owns preparation and selects practical.job.start. Monitoring observes that original '
            'attempt; results acquisition retains the complete original artifacts and invokes the '
            'separate deterministic parser and calculator. Recalculate a saved sheet without '
            'rerunning the native program. Request only the numerical components and associations '
            'needed by the receiving episode. Native significance and model-alignment quantities '
            'are not probabilities of correct gene annotation. This information grants no direct '
            'native execution operation to the scientific episode.')
        schema = deepcopy(NATIVE_INFERNAL_REQUESTED_JOB_SCHEMA)
        native = schema['properties']['native_infernal']['properties']
        native['program'] = {'const': program}
        native['software'] = {'const': deepcopy(binding['software'])}
        native['table_format'] = ({'type': 'null'} if program == 'cmalign' else
            {'enum': [1, 3] if program == 'cmsearch' else [1, 2, 3]})
        entries.append({'name': 'native.' + program, 'description': _DESCRIPTION[program],
            'resources': resource_kind, 'instructions': instructions, 'input_schema': schema,
            'invocation_route': {'kind': 'commission', 'routes': [{'entry_role': 'launch',
                'resource_id': resource_id, 'resource_role': 'launch_local'}]}})
    return entries


def native_infernal_tool_information(bindings, *, resource_kind, resource_id):
    return [{key: entry[key] for key in ('name', 'description', 'resources', 'instructions')}
        for entry in native_infernal_tool_contracts(bindings,
            resource_kind=resource_kind, resource_id=resource_id)]
