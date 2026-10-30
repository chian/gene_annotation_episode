"""Versioned, on-demand instructions available inside every episode.

This is a document library, not an executor, relevance gate or agent. The run
owns a disk snapshot. Only its small index stays in memory; selected sections
are streamed from disk. Retrieval returns no scientific records or credit.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile


VERSION = 'tool_knowledge_v1'
INSTRUCTIONS = (' Tool-specific and resource instructions are available through '
    'knowledge.search, knowledge.entry and knowledge.read. The tool_knowledge '
    'context identifies the run-frozen library. Retrieve sections when useful; '
    'these instructions do not select work, supply scientific evidence or add '
    'execution capabilities. Use the actual tool schemas and caller-owned '
    'configuration for execution. Knowledge reads use line coordinates, not '
    'scientific source-byte anchors. No manual read is mandatory.')


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def _digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            value.update(chunk)
    return value.hexdigest()


def _within(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('knowledge_section_path_invalid')
    return path


def _object(properties, required=None):
    return {'type': 'object', 'properties': properties,
            'required': list(properties) if required is None else required,
            'additionalProperties': False}


def catalog():
    text = {'type': 'string', 'minLength': 1}
    offset = {'type': 'integer', 'minimum': 0}
    limit = {'type': 'integer', 'minimum': 1}
    return [
        {'name': 'knowledge.search', 'description':
            'Search/page the run-frozen tool-instruction index. All whitespace-separated query terms must occur in entry metadata, case-insensitively; this is literal discovery, not a scientific suitability verdict. Empty query lists entries. No manual bodies are loaded.',
         'input_schema': _object({'query': {'type': 'string'}, 'offset': offset,
                                  'limit': limit})},
        {'name': 'knowledge.entry', 'description':
            'Read one instruction entry\'s section index, tool names and provenance without loading manual bodies. A listed tool is not necessarily enabled for this episode.',
         'input_schema': _object({'entry_id': text})},
        {'name': 'knowledge.read', 'description':
            'Read a selected instruction section by zero-based line offset and line count. Follow next_query for more. Returns run library identity and exact section digest; instructions are not scientific source evidence.',
         'input_schema': _object({'entry_id': text, 'section_id': text,
                                  'offset': offset, 'limit': limit})},
    ]


class ToolKnowledge:
    @classmethod
    def freeze(cls, directory, *, source=None):
        directory = Path(directory)
        if (directory/'index.json').is_file():
            return cls(directory)
        source = (Path(source) if source is not None else
                  Path(__file__).with_name('knowledge'))
        specification = json.loads((source/'index.json').read_text())
        if specification['version'] != VERSION:
            raise ValueError('knowledge_version_unknown')
        directory.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.tool-knowledge-', dir=directory.parent) as staging:
            staging = Path(staging)
            entries = []
            seen = set()
            for raw in specification['entries']:
                entry = deepcopy(raw)
                if entry['entry_id'] in seen:
                    raise ValueError('knowledge_entry_identity_duplicate')
                seen.add(entry['entry_id'])
                section_ids = set()
                for section in entry['sections']:
                    if section['section_id'] in section_ids:
                        raise ValueError('knowledge_section_identity_duplicate')
                    section_ids.add(section['section_id'])
                    original = _within(source, section['path'])
                    # Snapshot filenames are generated, not supplied by a manual.
                    name = str(len(entries))+'-'+str(len(section_ids))+'.md'
                    saved = staging/name
                    shutil.copyfile(original, saved)
                    section['path'] = name
                    section['sha256'] = _digest(saved)
                    section['bytes'] = saved.stat().st_size
                    with saved.open(encoding='utf-8') as stream:
                        section['lines'] = sum(1 for _ in stream)
                entries.append(entry)
            manifest = {'version': VERSION, 'entries': entries}
            manifest['library_id'] = 'tool_knowledge_'+hashlib.sha256(_json(manifest).encode()).hexdigest()
            (staging/'index.json').write_text(_json(manifest)+'\n')
            staging.rename(directory)
        return cls(directory)

    def __init__(self, directory):
        self.directory = Path(directory)
        self.manifest = json.loads((self.directory/'index.json').read_text())
        content = {key: value for key, value in self.manifest.items() if key != 'library_id'}
        expected = 'tool_knowledge_'+hashlib.sha256(_json(content).encode()).hexdigest()
        if self.manifest['version'] != VERSION or self.manifest['library_id'] != expected:
            raise ValueError('knowledge_snapshot_identity_mismatch')
        self.entries = {entry['entry_id']: entry for entry in self.manifest['entries']}

    def context(self):
        return {'version': VERSION, 'library_id': self.manifest['library_id'],
                'entry_count': len(self.entries), 'discovery_tool': 'knowledge.search',
                'content_role': 'tool_and_resource_instructions_not_scientific_evidence'}

    def entries_for_tool(self, name):
        return sorted(entry['entry_id'] for entry in self.entries.values()
                      if name in entry['tool_names'])

    def _entry(self, entry_id):
        if entry_id not in self.entries:
            raise ValueError('knowledge_entry_unknown')
        return self.entries[entry_id]

    def search(self, *, query, offset, limit):
        terms = query.casefold().split()
        matches = []
        for entry in sorted(self.entries.values(), key=lambda item: item['entry_id']):
            metadata = {key: value for key, value in entry.items() if key != 'sections'}
            if all(term in _json(metadata).casefold() for term in terms):
                matches.append(metadata)
        end = offset + limit
        return {**self.context(), 'query': query, 'offset': offset,
                'total': len(matches), 'entries': deepcopy(matches[offset:end]),
                'next_query': {'query': query, 'offset': end, 'limit': limit}
                    if end < len(matches) else None}

    def entry(self, entry_id):
        entry = deepcopy(self._entry(entry_id))
        for section in entry['sections']:
            section.pop('path')
        return {**self.context(), 'entry': entry}

    def read(self, *, entry_id, section_id, offset, limit):
        entry = self._entry(entry_id)
        section = next((item for item in entry['sections'] if item['section_id'] == section_id), None)
        if section is None:
            raise ValueError('knowledge_section_unknown')
        path = _within(self.directory, section['path'])
        if _digest(path) != section['sha256']:
            raise ValueError('knowledge_section_bytes_changed')
        lines = []
        # Preserve original newline bytes in the text returned for this digest.
        # Universal line recognition still supplies the same line coordinates.
        with path.open(encoding='utf-8', newline='') as stream:
            for number, line in enumerate(stream):
                if number >= offset + limit:
                    break
                if number >= offset:
                    lines.append(line)
        end = offset + len(lines)
        return {**self.context(), 'entry_id': entry_id, 'section_id': section_id,
                'section_sha256': section['sha256'], 'coordinate_unit': 'zero_based_lines',
                'offset': offset, 'returned_lines': len(lines), 'total_lines': section['lines'],
                'text': ''.join(lines),
                'next_query': {'entry_id': entry_id, 'section_id': section_id,
                               'offset': end, 'limit': limit} if end < section['lines'] else None}

    def execute(self, name, arguments):
        try:
            from jsonschema import Draft202012Validator
            definition = next((item for item in catalog() if item['name'] == name), None)
            if definition is None:
                raise ValueError('knowledge_tool_unknown')
            if not Draft202012Validator(definition['input_schema']).is_valid(arguments):
                raise ValueError('knowledge_arguments_invalid')
            operation = {'knowledge.search': self.search, 'knowledge.entry': self.entry,
                         'knowledge.read': self.read}[name]
            result = operation(**arguments)
            return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
                    'result': result, 'feedback': None}
        except (ValueError, OSError, UnicodeError) as error:
            return {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'code': str(error) if isinstance(error, ValueError) else
                        'knowledge_storage_unavailable', 'operation': name,
                        'exception_type': type(error).__name__}}
