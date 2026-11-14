"""Resource-specific information for actual workflow operations.

The four public fields are data about an operation, not an episode definition.
Original callable contracts are retained separately. Information cannot enable
an operation in a receiver which has no actual invocation binding for it.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.root.a102.method_loop.durable import canonical


RESOURCE_KINDS = ('api', 'local', 'hpc')
SELECTOR_FIELDS = {'name', 'resources'}
INFO_FIELDS = SELECTOR_FIELDS | {'description', 'instructions'}


def tool_info_selection(value):
    if not isinstance(value, list):
        raise ValueError('scientific_child_tool_info_invalid')
    result, seen = [], set()
    for item in value:
        if (not isinstance(item, Mapping) or set(item) not in (SELECTOR_FIELDS, INFO_FIELDS)
                or not isinstance(item.get('name'), str) or not item['name'].strip()
                or item.get('resources') not in RESOURCE_KINDS
                or any(not isinstance(item.get(field), str) or not item[field].strip()
                       for field in set(item) - SELECTOR_FIELDS)):
            raise ValueError('scientific_child_tool_info_invalid')
        key = item['name'], item['resources']
        if key in seen:
            raise ValueError('scientific_child_tool_info_duplicate')
        seen.add(key)
        result.append(deepcopy(dict(item)))
    return result


def selectors(value):
    if (not isinstance(value, list) or any(not isinstance(row, Mapping)
            or not SELECTOR_FIELDS <= set(row) <= INFO_FIELDS for row in value)):
        raise ValueError('scientific_child_tool_info_invalid')
    return tool_info_selection([{field: row[field] for field in ('name', 'resources')}
                                for row in value])


def parent_view(value):
    return [{field: row[field] for field in ('name', 'description', 'resources')}
            for row in value]


def resource_kind(name):
    if name.startswith(('public.', 'api.')):
        return 'api'
    if name.startswith(('state.', 'source.', 'result.', 'image.', 'material.', 'library.',
                        'reads.', 'rna.', 'sequence.', 'translation.', 'genes.', 'reference.',
                        'execution.', 'knowledge.', 'episode.', 'process.', 'homology.')):
        return 'local'
    raise ValueError('scientific_tool_resource_kind_required:' + name)


def _documents(name, resource):
    root = Path(__file__).parent
    selected = []
    for directory in ('knowledge', 'launch_instruction_library'):
        folder = root/directory
        manifest = json.loads((folder/'index.json').read_text())
        for entry in manifest['entries']:
            if name not in entry.get('tool_names', []):
                continue
            if entry.get('resource_kinds') and resource not in entry['resource_kinds']:
                continue
            section_ids = None
            if entry['entry_id'] == 'native-phmmer':
                section_ids = ({'monitor'} if name == 'homology.sample' else {'results'}
                    if name in {'homology.extract', 'homology.coverage', 'homology.errors'} else {'launch'})
            elif entry['entry_id'] == 'publication-access':
                section_ids = {'search'} if name == 'public.literature.search' else {'access'}
            elif entry['entry_id'] == 'source-reading':
                section_ids = {'tables'} if name.startswith(('source.xlsx.', 'source.archive.')) else {'representations'}
            elif entry['entry_id'] == 'launch-local':
                section_ids = {'homology'} if name.startswith('homology.') else {'operations'}
                if name in {'practical.inspect', 'practical.inventory.refresh', 'practical.context.set'}:
                    section_ids.add('preparation')
                if name in {'practical.file.read', 'practical.job.status', 'practical.job.collect'}:
                    section_ids.add('results')
            elif entry['entry_id'] == 'launch-aurora':
                # The configured prompt is delivered automatically to its
                # execution agent. Tool information describes general command
                # semantics; it does not prescribe scheduler workflow steps.
                section_ids = {'operations'}
            elif entry['entry_id'] == 'launch-api':
                section_ids = ({'results'} if name == 'api.hmmer.result' else
                    {'operations', 'results'} if name == 'api.hmmer.status' else {'service', 'operations'})
            for section in entry['sections']:
                if section_ids is not None and section['section_id'] not in section_ids:
                    continue
                path = (folder/section['path']).resolve()
                if not path.is_relative_to(folder.resolve()) or not path.is_file():
                    raise ValueError('scientific_tool_instruction_path_invalid')
                selected.append(path.read_text(encoding='utf-8').strip())
    return '\n\n'.join(dict.fromkeys(selected))


RESOURCE_INSTRUCTIONS = {
    'api': ('Use the caller-bound API client or the actual assigned API-execution episode. '
        'Use the registered operation contract, configured service/contact and actual request or job identity. '
        'A service operation requiring an execution assignment is available only in that assigned resource episode; '
        'this information does not make it an ordinary ToolRegistry operation. Preserve native responses, '
        'provider failures, pagination and uncertainty about submission. A source assertion is not a target annotation.'),
    'local': ('Use the actual local binding and its caller-owned resource limits. Read or measure only '
        'the assigned operands and explicit received inputs. Reuse retained outputs when the operation is a read; '
        'do not treat a read as a new measurement. Preserve native values, coordinate meanings, partial results '
        'and actionable failures. Job-specific operations require their original assigned execution.'),
    'hpc': ('Use only the actual assigned HPC execution binding and supplied access/resource configuration. '
        'The implemented HPC operations are the practical PBS/SSH operations, not a remote substitute for '
        'an arbitrary local tool. Preparation and execution can require multiple selected episode actions. '
        'Keep software, environments, inputs, caches, temporary files, logs and runs within the '
        'actual assignment workspace. Use configuration.account for PBS charging and select queue '
        'and resources consistent with the assignment constraints and supplied resource configuration. '
        'Preserve the original attempt, explicit queue/resources and native handoff. '
        'Configured or documented access is not proof of present authentication or availability.'),
}


def make_tool_info(contract, resource):
    name = contract['name']
    description = contract.get('description', '')
    if not isinstance(description, str) or not description.strip():
        raise ValueError('scientific_tool_description_required:' + name)
    details = _documents(name, resource)
    instructions = ('Operation: ' + name + '\n\n' + description + '\n\n'
        + RESOURCE_INSTRUCTIONS[resource]
        + '\n\nUse exactly the separately supplied actual input_schema; required operands and allowed values '
          'come from that contract. Do not infer another callable, resource or environment from this entry.')
    if details:
        instructions += '\n\n' + details
    if contract.get('instructions'):
        instructions += '\n\n' + contract['instructions']
    return {'name': name, 'description': description, 'resources': resource,
            'instructions': instructions}


def comparable_contract(entry):
    """Context-specific descriptions and availability do not change arguments."""
    return {field: deepcopy(entry[field]) for field in ('name', 'input_schema') if field in entry}


__all__ = ['RESOURCE_KINDS', 'tool_info_selection', 'selectors', 'parent_view',
           'resource_kind', 'make_tool_info', 'comparable_contract']
