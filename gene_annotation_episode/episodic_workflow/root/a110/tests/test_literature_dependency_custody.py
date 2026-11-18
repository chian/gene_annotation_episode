"""Dependency custody follows authenticated owners of the original synthetic sheet."""
from dataclasses import replace
import json

from .. import literature_sheet_updates as updates
from ..literature_reaction_storage import LiteratureReactionRepository
from ..biochemical_feasibility_evidence.tests.original_applicability_fixture import setup_case


def test_dependency_receipts_distinguish_original_owner_and_admitted_subset(tmp_path):
    store, context, arguments = setup_case(tmp_path / 'original-reaction', primary=False, incomplete=True)
    with store:
        repository = LiteratureReactionRepository(store, context.run_id)
        outcome = repository.populate(context, arguments, 'original-synthetic-publication')
        assert outcome['status'] == 'completed'
        reference = outcome['result']['sheet_ref']
        assert repository._sheet_origin_episode(reference) == context.episode_id

        def receipt(current):
            row = store.db.execute(f'SELECT receipt FROM {updates.TABLE} '
                'WHERE run_id=? AND episode_id=? AND sheet_ref=?',
                (current.run_id, current.episode_id, reference)).fetchone()
            assert row is not None
            return json.loads(row['receipt'])

        owned = receipt(context)
        assert owned['custody'] == 'owned'
        cells = repository.project_cells([reference], permitted_record_refs=outcome['record_refs'])[:1]
        assert len(cells) == 1
        parent = replace(context, episode_id='distinct-receiving-parent',
            received_record_refs=tuple(dict.fromkeys([*context.received_record_refs, *outcome['record_refs']])))
        repository.receive_cells(parent, cells, 'explicit-manual-admission-fixture')
        admitted = receipt(parent)
        assert admitted['custody'] == 'admitted'
        assert repository.received_cells(parent) == cells
        assert receipt(context) == owned
        assert repository.populate(context, arguments, 'original-synthetic-publication') == outcome
        repository.receive_cells(parent, cells, 'explicit-manual-admission-fixture')
        assert receipt(context) == owned and receipt(parent) == admitted
        assert repository._sheet_origin_episode(reference) == context.episode_id
