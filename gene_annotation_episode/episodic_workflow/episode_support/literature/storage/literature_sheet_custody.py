"""Saved literature sheets and their cells as an Episode holds them, over the custody-scoped store.

A repository that saves numerical sheets declares two work tables, ``operations`` (the sheets one operation saved,
keyed by the operation) and ``cells_table`` (one row per saved cell, passed to a parent by naming its row).  An
Episode owns the sheets it produced; the cells of any other sheet are the cell rows it holds.  Nothing here
reads or writes anything but the scoped store (``self.store``) it was given.
"""
from copy import deepcopy

from gene_annotation_episode.domain import ContractError, canonical


class SheetCustody:
    """The ownership and cell-row operations every sheet repository shares; ``project_cells`` is the repository's."""
    operations = None
    cells_table = None

    def owned_sheet_refs(self):
        """The sheets this Episode produced, in the order it first saved them."""
        rows = self.store.table(self.operations).select()
        return list(dict.fromkeys((row['sheet_ref'] for row in rows if self.store.receipt(row['id'])['how'] == 'produced')))

    def owns(self, sheet_ref):
        return sheet_ref in self.owned_sheet_refs()

    def publish_cells(self, sheet_ref, components=None):
        """Save the cells of one owned sheet as rows the Episode can pass on by reference."""
        for row in self.project_cells([sheet_ref], components=components):
            self.store.table(self.cells_table).put({'sheet_ref': sheet_ref, 'component': row['component'], 'cell': row})

    def received_cells(self, context):
        """The cell rows held from another Episode's sheets, not the complete private child sheet."""
        rows = self.store.table(self.cells_table).select()
        return [deepcopy(row['cell']) for row in rows if self.store.receipt(row['id'])['how'] != 'produced']

    def fact_cells(self, context, sheet_refs, *, components):
        """Project owned cells or copy the cell rows this Episode holds."""
        self.project_cells([], components=components)
        received = None
        result = []
        for reference in dict.fromkeys(sheet_refs):
            if self.owns(reference):
                result.extend(self.project_cells([reference], components=components))
            else:
                if received is None:
                    received = {(row['sheet_ref'], row['component']): row for row in self.received_cells(context)}
                result.extend((deepcopy(received[reference, name]) for name in components if (reference, name) in received))
        return result

    def validate_fact_values(self, context, cells):
        """A valid saved row must also be held by the reporting Episode."""
        if not cells:
            return
        expected = {(row['sheet_ref'], row['component']): row for row in self.fact_cells(context, list(dict.fromkeys((row['sheet_ref'] for row in cells))), components=list(dict.fromkeys((row['component'] for row in cells))))}
        if any((canonical(row) != canonical(expected.get((row['sheet_ref'], row['component']))) for row in cells)):
            raise ContractError('literature_cell_not_received')
