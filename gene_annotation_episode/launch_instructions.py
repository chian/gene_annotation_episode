"""Run-frozen launch instructions and exact per-assignment selections.

This collection shares the existing document snapshot/retrieval implementation.
It owns no execution capability, resource choice, inventory, credit or loop.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from .tool_knowledge import ToolKnowledge


VERSION = 'launch_instruction_library_v1'
SELECTION_VERSION = 'launch_instruction_selection_v1'
INSTRUCTIONS = (
    ' Launch software/resource instructions have their own run-frozen library: '
    'launch.instructions.search, launch.instructions.entry, launch.instructions.read '
    'and launch.instructions.select. The launch_instruction_library context gives '
    'its identity. Select any relevant sections from one or several entries; pass '
    'the returned selection as launch_instructions in the child assignment. '
    'selected_launch_instructions contains exact sections already selected for '
    'this assignment. resource_launch_instructions contains the assigned resource\'s '
    'configured prompt, supplied automatically from this same frozen library; '
    'do not search for or select that prompt again. Instructions describe ways to work; they do not select '
    'resources, enable tools, override caller constraints, establish current '
    'availability or supply scientific evidence. Inventory and fresh observations '
    'remain separate. No instruction read or selection is mandatory.')


def _object(properties, *, required=None):
    return {'type': 'object', 'properties': properties,
            'required': list(properties) if required is None else required,
            'additionalProperties': False}


_TEXT = {'type': 'string', 'minLength': 1}
_PAIR_SCHEMA = _object({'entry_id': _TEXT, 'section_id': _TEXT})
_SECTION_SCHEMA = _object({'entry_id': _TEXT, 'section_id': _TEXT,
                          'sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}})
_SELECTION_OBJECT_SCHEMA = _object({
    'version': {'type': 'string', 'const': SELECTION_VERSION},
    'library_id': {'type': 'string', 'pattern': '^launch_instructions_[0-9a-f]{64}$'},
    'sections': {'type': 'array', 'minItems': 1, 'items': _SECTION_SCHEMA},
})
SELECTION_SCHEMA = {'anyOf': [{'type': 'null'}, _SELECTION_OBJECT_SCHEMA]}


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def validate_selection(value):
    """Validate shape and unique section identities; read no disk or resource."""
    value = _plain(value)
    if not Draft202012Validator(SELECTION_SCHEMA).is_valid(value):
        raise ValueError('launch_instruction_selection_invalid')
    if value is not None:
        identities = [(item['entry_id'], item['section_id']) for item in value['sections']]
        if len(identities) != len(set(identities)):
            raise ValueError('launch_instruction_selection_duplicate')
    return deepcopy(value)


def retain_inherited_selection(inherited, selected):
    """A child may explicitly add instructions, but cannot replace parent pins."""
    inherited, selected = validate_selection(inherited), validate_selection(selected)
    if inherited is None:
        return selected
    if selected is None or inherited['library_id'] != selected['library_id']:
        raise ValueError('launch_instruction_inheritance_conflict')
    pins = {(item['entry_id'], item['section_id'], item['sha256'])
            for item in selected['sections']}
    if any((item['entry_id'], item['section_id'], item['sha256']) not in pins
           for item in inherited['sections']):
        raise ValueError('launch_instruction_inheritance_conflict')
    return selected


def catalog():
    offset = {'type': 'integer', 'minimum': 0}
    limit = {'type': 'integer', 'minimum': 1}
    return [
        {'name': 'launch.instructions.search', 'description':
            'Search/page the separate run-frozen launch instruction metadata. '
            'Empty query browses entries. resource_kind is an optional exact metadata '
            'filter; neither matches nor manuals establish resource availability.',
         'input_schema': _object({'query': {'type': 'string'}, 'offset': offset,
             'limit': limit, 'resource_kind': {'type': ['string', 'null'],
                 'enum': ['api', 'local', 'hpc', None]}},
             required=['query', 'offset', 'limit'])},
        {'name': 'launch.instructions.entry', 'description':
            'Read one launch instruction entry index, sources and section hashes '
            'without loading section text. Listed operations still require an actual binding.',
         'input_schema': _object({'entry_id': _TEXT})},
        {'name': 'launch.instructions.read', 'description':
            'Read exact zero-based line windows from a selected launch instruction '
            'section. Returns its digest and next_query; reading performs no setup or execution.',
         'input_schema': _object({'entry_id': _TEXT, 'section_id': _TEXT,
                                 'offset': offset, 'limit': limit})},
        {'name': 'launch.instructions.select', 'description':
            'Pin explicitly selected sections from one or multiple entries in this '
            'run-frozen launch library. Pass the returned selection as the child '
            'assignment launch_instructions. Does not choose or launch a resource.',
         'input_schema': _object({'sections': {'type': 'array', 'minItems': 1,
                                             'items': _PAIR_SCHEMA}})},
    ]


def _translated(operation, *args, **kwargs):
    try:
        return operation(*args, **kwargs)
    except ValueError as error:
        code = str(error)
        if code.startswith('knowledge_'):
            raise ValueError('launch_instruction_' + code[len('knowledge_'):]) from error
        raise


class LaunchInstructions:
    @classmethod
    def freeze(cls, directory, *, source=None):
        source = Path(source) if source is not None else Path(__file__).with_name(
            'launch_instruction_library')
        backend = _translated(ToolKnowledge.freeze, directory, source=source)
        return cls(backend.directory)

    def __init__(self, directory):
        self.directory = Path(directory)
        self._knowledge = _translated(ToolKnowledge, self.directory)

    def context(self):
        backend = self._knowledge.context()
        return {'version': VERSION,
                'library_id': 'launch_instructions_' + backend['library_id'].removeprefix(
                    'tool_knowledge_'),
                'entry_count': backend['entry_count'],
                'discovery_tool': 'launch.instructions.search',
                'content_role': 'launch_instructions_not_inventory_or_scientific_evidence'}

    def _arguments(self, name, arguments):
        schema = next(item['input_schema'] for item in catalog() if item['name'] == name)
        if not Draft202012Validator(schema).is_valid(arguments):
            raise ValueError('launch_instruction_arguments_invalid')

    def search(self, *, query, offset, limit, resource_kind=None):
        self._arguments('launch.instructions.search', {
            'query': query, 'offset': offset, 'limit': limit, 'resource_kind': resource_kind})
        all_matches = self._knowledge.search(query=query, offset=0,
            limit=max(1, self._knowledge.context()['entry_count']))['entries']
        matches = [entry for entry in all_matches
                   if resource_kind is None or resource_kind in entry.get('resource_kinds', [])]
        end = offset + limit
        return {**self.context(), 'query': query, 'resource_kind': resource_kind,
                'offset': offset, 'total': len(matches), 'entries': deepcopy(matches[offset:end]),
                'next_query': {'query': query, 'resource_kind': resource_kind,
                               'offset': end, 'limit': limit} if end < len(matches) else None}

    def entry(self, entry_id):
        self._arguments('launch.instructions.entry', {'entry_id': entry_id})
        result = _translated(self._knowledge.entry, entry_id)
        return {**result, **self.context()}

    def read(self, *, entry_id, section_id, offset, limit):
        arguments = {'entry_id': entry_id, 'section_id': section_id,
                     'offset': offset, 'limit': limit}
        self._arguments('launch.instructions.read', arguments)
        result = _translated(self._knowledge.read, **arguments)
        return {**result, **self.context()}

    def _section(self, entry_id, section_id):
        sections = self.entry(entry_id)['entry']['sections']
        section = next((item for item in sections if item['section_id'] == section_id), None)
        if section is None:
            raise ValueError('launch_instruction_section_unknown')
        return section

    def select(self, sections):
        sections = _plain(sections)
        self._arguments('launch.instructions.select', {'sections': sections})
        selected = validate_selection({**{'version': SELECTION_VERSION,
            'library_id': self.context()['library_id']}, 'sections': [
                {**item, 'sha256': self._section(**item)['sha256']} for item in sections]})
        # Hash verification streams the complete file; the one-line window here
        # is not materialized as a second instruction body or returned finding.
        for item in sections:
            self.read(**item, offset=0, limit=1)
        return selected

    def materialize(self, selection):
        selection = validate_selection(selection)
        if selection is None:
            return None
        if selection['library_id'] != self.context()['library_id']:
            raise ValueError('launch_instruction_selection_library_mismatch')
        sections = []
        for pin in selection['sections']:
            metadata = self._section(pin['entry_id'], pin['section_id'])
            if pin['sha256'] != metadata['sha256']:
                raise ValueError('launch_instruction_selection_digest_mismatch')
            sections.append(self.read(entry_id=pin['entry_id'], section_id=pin['section_id'],
                                      offset=0, limit=max(1, metadata['lines'])))
        return {'selection': selection, 'sections': sections}

    def for_resource(self, configuration):
        """Supply a configured resource prompt without an agent lookup action.

        Resource configuration names a library entry, not an execution procedure.
        New resources supply another entry while retaining the same Launch
        episode and general execution tools.
        """
        entry_id = configuration.get('launch_prompt_entry')
        section_ids = configuration.get('launch_prompt_sections')
        if entry_id is None:
            if section_ids is not None:
                raise ValueError('launch_instruction_resource_entry_missing')
            return None
        if not isinstance(entry_id, str) or not entry_id:
            raise ValueError('launch_instruction_resource_entry_invalid')
        metadata = self.entry(entry_id)['entry']
        available = [item['section_id'] for item in metadata['sections']]
        if section_ids is None:
            section_ids = available
        elif (not isinstance(section_ids, (list, tuple)) or not section_ids
              or any(not isinstance(item, str) or not item for item in section_ids)
              or len(set(section_ids)) != len(section_ids)
              or any(item not in available for item in section_ids)):
            raise ValueError('launch_instruction_resource_sections_invalid')
        selected = self.select([{'entry_id': entry_id, 'section_id': section_id}
                                for section_id in section_ids])
        return self.materialize(selected)

    def execute(self, name, arguments):
        try:
            if name not in {item['name'] for item in catalog()}:
                raise ValueError('launch_instruction_tool_unknown')
            arguments = _plain(arguments)
            self._arguments(name, arguments)
            operation = {
                'launch.instructions.search': self.search,
                'launch.instructions.entry': self.entry,
                'launch.instructions.read': self.read,
                'launch.instructions.select': self.select,
            }[name]
            result = operation(**arguments)
            return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
                    'result': result, 'feedback': None}
        except (ValueError, OSError, UnicodeError) as error:
            return {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'code': str(error) if isinstance(error, ValueError) else
                        'launch_instruction_storage_unavailable', 'operation': name,
                        'exception_type': type(error).__name__}}


__all__ = ['LaunchInstructions', 'VERSION', 'SELECTION_VERSION', 'SELECTION_SCHEMA',
           'validate_selection', 'retain_inherited_selection', 'catalog', 'INSTRUCTIONS']
