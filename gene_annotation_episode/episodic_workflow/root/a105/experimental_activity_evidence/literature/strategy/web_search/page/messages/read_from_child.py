"""What this episode takes from a child's admitted return. Every child is a leaf extractor (``chunk``: one window; ``table``:
one window that holds a table; ``report``: the paper window after window in document order); each returns ``credit``, the
``finding`` counts (``stated``, ``newly_stated``, ``asked``; ``chunk/messages/final_to_parent.py``) and the selected
``record_refs``, the immutable leaf records. This episode groups them into graders and updates the subscoring sheet
(``task.update_sheet``, automatic). Nothing else of the child's work reaches this episode; the records are held through the
``returned`` receipts, so ``internal_summary`` and the sheet update read them through ``records`` and the Store."""
CHUNK_COUNTS = ('stated', 'newly_stated', 'asked')
LEAF_SLOTS = ('chunk', 'table', 'report')


def read_from_child(slot, result, summary, records):
    return {'slot': slot, 'credit': result['credit'],
            'counts': {name: result['finding'][name] for name in CHUNK_COUNTS},
            'record_refs': list(result['record_refs'])}
