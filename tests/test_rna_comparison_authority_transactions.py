"""Existing commission transactions and deeper frozen-return lineage."""
from dataclasses import replace

import pytest

from test_rna_comparison_operand_authority import E, resolve
from gene_annotation_episode.rna_structure_comparison_operands import validate_rna_comparison_selected_inputs
from gene_annotation_episode.state import Store


def test_selected_inputs_and_resolution_preserve_outer_commission_rollback(tmp_path):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture", failure="null_source")
        selector = f.selector(scan=True)
        before = list(store.db.iterdump())
        with pytest.raises(RuntimeError, match="deliberate_commission_failure"):
            with store.transaction():
                validate_rna_comparison_selected_inputs(store, f.root, selector,
                    anchor_handoff_ref=f.originals[1].handoff, returns=f.native_returns)
                assert store.db.in_transaction
                child = f.child(selector)
                validate_rna_comparison_selected_inputs(store, child, selector,
                    anchor_handoff_ref=f.originals[1].handoff, returns=f.native_returns)
                operands = resolve(f, child, selector)
                assert operands["data"]["failed"]["received_failure"]["source_ref"] is None
                assert store.db.in_transaction
                raise RuntimeError("deliberate_commission_failure")
        assert not store.db.in_transaction and list(store.db.iterdump()) == before
        assert store.db.execute("SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (f.run_id, child.episode_id)).fetchone() is None
        assert store.db.execute("SELECT 1 FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?",
            (f.run_id, child.episode_id)).fetchone() is None
        E.retain("authority_transaction_rollback", selected_selector=selector,
            failed_child_episode_id=child.episode_id, rollback_preserved=True)


@pytest.mark.parametrize("kind", ["saved_sheet", "null_source"])
def test_late_outer_ancestor_return_cannot_enter_a_later_descendant(tmp_path, kind):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture", failure="null_source" if kind == "null_source" else False)
        index = 1 if kind == "saved_sheet" else 2
        attempt = dict(store.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?",
            (f.run_id, f.root.episode_id, index)).fetchone())
        store.db.execute("DELETE FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?",
            (f.run_id, f.root.episode_id, index))
        scientific = f.child(role="scientific_process", index=10)
        f.journal.save("runtime_report_attempts", attempt)
        selector = f.selector(scan=kind == "null_source")
        child = f.child(selector, parent=scientific, index=0)
        with pytest.raises(ValueError, match="saved_operand_not_received"):
            resolve(f, child, selector)


def test_wrong_scope_and_sibling_context_cannot_read_selected_action_result(tmp_path):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture")
        child = f.child()
        body = f.execute(child)
        assert f.results.read_result(child, body) == body
        sibling = f.child(index=11)
        with pytest.raises(ValueError, match="original_context_conflict"):
            f.results.read_result(sibling, body)
        with pytest.raises(ValueError):
            resolve(f, replace(child, scope={}), E.plain(child.assignment)["selector"])
        with pytest.raises(ValueError):
            f.results.read_result(replace(child, scope={}), body)
