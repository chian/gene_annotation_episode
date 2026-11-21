"""The input list of a gene-context source-reading episode (nano-graphrag's remaining-input paradigm: the items the
episode works through are a list; an item that has been read is consumed and is no longer offered).

The commissioned selection of the reader is one extent, ``[offset, offset + limit]``, counted in bytes of one
representation of the source (a byte window) or in matching rows of one sheet (a table selection). The extent is
consumed by what the episode has read of it: a completed ``source_read`` of the window's source and representation
(bytes), a completed ``source_xlsx_rows`` of the selection's sheet and filter (rows), and the readings of a report
(``kind`` ``table_bytes`` or ``sheet_rows``). The input list is what remains of the extent, in document order, as
``[start, end]`` pairs; it is empty when the whole selection has been read, and the episode's yield estimator then ends
the episode. Pure functions over the selection and the episode's own outcomes; nothing is written."""

KIND_OF_READ = {'source_read': 'table_bytes', 'source_xlsx_rows': 'sheet_rows'}


def selection_kind(selection):
    """``table_bytes`` for a byte window (a selection with a representation), ``sheet_rows`` for a sheet selection."""
    return 'table_bytes' if 'representation' in selection else 'sheet_rows'


def selection_extent(selection):
    """The commissioned extent ``[start, end]``; empty (``[]``) when the selection reads no row or byte."""
    start, end = selection['offset'], selection['offset'] + selection['limit']
    return [[start, end]] if end > start else []


def read_extent(selection, outcome):
    """The ``[start, end]`` extent of ``selection``'s kind that one unit outcome read, or ``None`` when the outcome is not
    a completed read of the selection's source (and representation, or sheet and filter) with explicit bounds."""
    kind = selection_kind(selection)
    if outcome['kind'] != 'tool':
        return None
    if outcome['tool'] == 'report':
        if outcome['outcome'].get('status') != 'reported':
            return None
        rows = [reading for reading in outcome['outcome']['report']['readings']
                if reading['kind'] == kind and reading['source_ref'] == selection['source_ref']]
        return [[reading['offset'], reading['offset'] + reading['limit']] for reading in rows]
    if KIND_OF_READ.get(outcome['tool']) != kind or outcome['outcome'].get('status') != 'completed':
        return None
    arguments = outcome['arguments']['arguments']
    if arguments.get('source_ref') != selection['source_ref']:
        return None
    if kind == 'table_bytes':
        if arguments.get('representation') != selection['representation']:
            return None
    elif arguments.get('sheet_key') != selection['sheet_key'] or arguments.get('where') != selection.get('where'):
        return None
    offset, limit = arguments.get('offset', 0), arguments.get('limit')
    if type(offset) is not int or type(limit) is not int or limit < 1:
        return None
    return [[offset, offset + limit]]


def subtract(extents, consumed):
    """``extents`` without ``consumed`` (both lists of ``[start, end]``), in document order."""
    remaining = [list(extent) for extent in extents]
    for start, end in consumed:
        parts = []
        for low, high in remaining:
            if end <= low or start >= high:
                parts.append([low, high])
                continue
            if low < start:
                parts.append([low, start])
            if end < high:
                parts.append([end, high])
        remaining = parts
    return sorted(remaining)


def consumed_extents(selection, outcomes):
    """Every extent of the selection's kind that the episode's outcomes have read."""
    found = []
    for outcome in outcomes:
        extents = read_extent(selection, outcome)
        if extents:
            found.extend(extents)
    return found


def selection_input_list(selection, outcomes):
    """What remains of the selection: ``[[start, end], ...]`` in document order; empty once it has all been read."""
    return subtract(selection_extent(selection), consumed_extents(selection, outcomes))


def already_read(selection, consumed, name, arguments):
    """Whether a read the model asks for (tool ``name`` with ``arguments``) is of the selection's kind and lies wholly
    inside ``consumed`` (the extents read already: the summary's ``consumed_inputs``), so it would offer a consumed
    input again. Reads of other sources, other sheets or filters, other representations, or without explicit bounds
    are not of the input list and are not affected."""
    probe = {'kind': 'tool', 'tool': name, 'arguments': {'arguments': arguments},
             'outcome': {'status': 'completed'}}
    extents = read_extent(selection, probe)
    if not extents:
        return False
    return not subtract(extents, consumed)
