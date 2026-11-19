"""Test-only library functions that keep a sheet of an Episode's work as a declared work table.

They are written the way a support-library function is: they receive the custody-scoped store (or the read-only
reader) and call only what it offers; they never see the Store, its connection or SQL."""
from episode_runtime import TableDeclaration

SHEET = TableDeclaration(name='probe_sheet', columns=('sheet', 'cell', 'value', 'source_ref'),
                         key=('sheet', 'cell'), record_refs=('source_ref',))


def write_cell(store, sheet, cell, value, source_ref):
    """Write one cell of ``sheet`` (the writing Episode's own row); the row the store returned."""
    return store.table(SHEET).put({'sheet': sheet, 'cell': cell, 'value': value, 'source_ref': source_ref})


def cells(reader, sheet):
    """The cells of ``sheet`` that the Episode holds, in receipt order."""
    return reader.table(SHEET).select({'sheet': sheet})
