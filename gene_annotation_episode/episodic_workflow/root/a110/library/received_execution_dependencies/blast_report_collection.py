from __future__ import annotations
import re
import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.blast_grading_inputs as _reader
_PROGRAM_HEADER = re.compile('([A-Z][A-Z0-9_-]+)\\s+(\\d\\S*.*)')

def _sections(text, artifact):
    """Retain contiguous query/round sections; never merge a repeated query."""
    sections, lines, has_query, has_data, query_id = ([], [], False, False, None)
    fields = _reader._fields(artifact['fields']) if artifact['fields'] is not None else None
    delimiter = artifact['delimiter'] or '\t'
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        content = line.rstrip('\r\n')
        heading = content[1:].strip() if content.startswith('#') else None
        boundary = False
        if heading is not None:
            boundary = bool(_PROGRAM_HEADER.fullmatch(heading) and (has_query or has_data))
            boundary |= heading.startswith('Query:') and has_query
            boundary |= heading.startswith('Iteration:') and (has_query or has_data)
        elif content.strip():
            if artifact['format'] == 'tabular6' and fields is not None:
                cells = content.split(delimiter)
                if len(cells) == len(fields):
                    row = dict(zip(fields, cells))
                    new_id = row.get('qseqid') or row.get('qaccver') or row.get('qacc')
                    if new_id and query_id is not None and (new_id != query_id):
                        boundary = True
                    if new_id:
                        query_id = new_id
        if boundary:
            sections.append(lines)
            lines, has_query, has_data = ([], False, False)
        lines.append((number, line))
        has_query |= heading is not None and heading.startswith('Query:')
        has_data |= heading is None and bool(content.strip())
    if lines or not sections:
        sections.append(lines)
    return sections
