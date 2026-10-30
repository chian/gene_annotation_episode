"""Frozen receipt-time proof, using real Store/Journal and saved typed forms.

These tests do not run a scientific tool or claim RNA comparison integration.
The separate comparison authority and Workflow suites exercise those consumers.
"""
from copy import deepcopy
from dataclasses import replace
import json
import sqlite3

import pytest

from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts, RECEIPT_VERSION
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.state import Store


CONTRACT = {"decision": "Return the selected acquisition outcome", "measurements": {
    "schema": {"type": "object", "properties": {"source_ref": {"type": "null"},
        "outcome": {"enum": ["acquisition_failed"]}},
        "required": ["source_ref", "outcome"], "additionalProperties": False}},
    "information": {"outcome": "Actual selected acquisition outcome"}}
FORM = {"source_ref": None, "outcome": "acquisition_failed"}


def _attempt(journal, index, *, parent="parent", form=FORM, failure=None):
    journal.save("runtime_report_attempts", {"parent_episode_id": parent,
        "decision_index": index, "delivery_ref": "delivery_" + str(index),
        "child_episode_id": "reporting_child_" + str(index),
        "contract": canonical(CONTRACT), "form": None if form is None else canonical(form),
        "failure": None if failure is None else canonical(failure)})


def _expected(index):
    return {"decision_index": index, "delivery_ref": "delivery_" + str(index),
        "child_episode_id": "reporting_child_" + str(index),
        "contract_sha256": digest(CONTRACT), "form_sha256": digest(FORM)}


def _empty():
    return {"version": "frozen_received_report_prefix_v1", "attempts": []}


def test_new_snapshot_excludes_late_return_with_earlier_commission_index(tmp_path):
    with Store(tmp_path / "store") as store:
        journal = Journal(store, "run")
        receipts = EpisodeReceipts(store, "run")
        receipts.bind("parent")
        _attempt(journal, 7)
        original = receipts.bind("child", "parent")
        assert original["received_report_prefix"]["attempts"] == [_expected(7)]
        # The child commissioned at action 2 returns only AFTER this bind.
        _attempt(journal, 2)
        assert receipts.bind("child", "parent") == original
        new = receipts.bind("later_child", "parent")
        assert new["received_report_prefix"]["attempts"] == [_expected(2), _expected(7)]
    with Store(tmp_path / "store") as store:
        receipts = EpisodeReceipts(store, "run")
        assert receipts.manifest("child") == original
        assert receipts.bind("child", "parent") == original


def test_null_source_return_needs_no_invented_store_reference_or_observation(tmp_path):
    with Store(tmp_path / "store") as store:
        journal = Journal(store, "run")
        receipts = EpisodeReceipts(store, "run")
        receipts.bind("parent")
        _attempt(journal, 0)
        before = store.db.execute("SELECT count(*) FROM records").fetchone()[0]
        manifest = receipts.bind("child", "parent")
        assert manifest["received_report_prefix"]["attempts"] == [_expected(0)]
        assert manifest["through_receipt_index"] == 0
        assert list(receipts.known("child")) == []
        assert store.db.execute("SELECT count(*) FROM records").fetchone()[0] == before
        for table in ("runtime_observations", "runtime_record_receipts", "runtime_actions"):
            assert store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
        # Only original identities and hashes, never the form or its prose.
        serialized = canonical(manifest["received_report_prefix"])
        assert "acquisition_failed" not in serialized
        assert "source_ref" not in serialized


def test_snapshot_selects_successful_actual_forms_from_only_this_parent_and_run(tmp_path):
    with Store(tmp_path / "store") as store:
        journal = Journal(store, "run")
        other = Journal(store, "other-run")
        receipts = EpisodeReceipts(store, "run")
        receipts.bind("parent")
        _attempt(journal, 9)
        _attempt(journal, 1)
        _attempt(journal, 2, form=None)
        _attempt(journal, 3, failure={"code": "invalid_form"})
        _attempt(journal, 4, form=None, failure={"code": "missing_form"})
        _attempt(journal, 5, parent="other-parent")
        _attempt(other, 6)
        manifest = receipts.bind("child", "parent")
        assert manifest["received_report_prefix"]["attempts"] == [_expected(1), _expected(9)]


def test_empty_snapshot_before_journal_exists_is_not_refilled_later(tmp_path):
    with Store(tmp_path / "store") as store:
        receipts = EpisodeReceipts(store, "run")
        root = receipts.bind("parent")
        child = receipts.bind("child", "parent")
        assert root["received_report_prefix"] == child["received_report_prefix"] == _empty()
        journal = Journal(store, "run")
        _attempt(journal, 0)
        assert receipts.bind("child", "parent") == child
        assert receipts.bind("parent") == root


def test_bind_and_read_participate_in_outer_commission_rollback(tmp_path):
    with Store(tmp_path / "store") as store:
        journal = Journal(store, "run")
        receipts = EpisodeReceipts(store, "run")
        receipts.bind("parent")
        with pytest.raises(RuntimeError, match="commission_failed"):
            with store.transaction():
                _attempt(journal, 0)
                manifest = receipts.bind("child", "parent")
                assert manifest["received_report_prefix"]["attempts"] == [_expected(0)]
                assert EpisodeReceipts.read_manifest(store.db, "run", "child") == manifest
                assert store.db.in_transaction
                raise RuntimeError("commission_failed")
        with pytest.raises(ValueError, match="episode_receipts_not_bound"):
            receipts.manifest("child")
        assert store.db.execute("SELECT count(*) FROM runtime_report_attempts").fetchone()[0] == 0


def test_old_rows_and_old_schema_remain_exactly_old_without_retrospective_proof(tmp_path):
    with Store(tmp_path / "store") as store:
        store.db.execute("CREATE TABLE runtime_receipt_inheritance (run_id TEXT NOT NULL, "
            "episode_id TEXT NOT NULL, parent_episode_id TEXT, through_receipt_index INTEGER, "
            "PRIMARY KEY(run_id,episode_id))")
        store.db.execute("INSERT INTO runtime_receipt_inheritance VALUES('run','parent',NULL,NULL)")
        store.db.execute("INSERT INTO runtime_receipt_inheritance VALUES('run','old-child','parent',0)")
        expected = {"version": RECEIPT_VERSION, "parent_episode_id": "parent", "through_receipt_index": 0}
        assert EpisodeReceipts.read_manifest(store.db, "run", "old-child") == expected
        journal = Journal(store, "run")
        _attempt(journal, 0)
        receipts = EpisodeReceipts(store, "run")
        assert receipts.bind("old-child", "parent") == expected
        assert store.db.execute("SELECT received_report_prefix FROM runtime_receipt_inheritance "
            "WHERE episode_id='old-child'").fetchone()[0] is None
        assert receipts.bind("new-child", "parent")["received_report_prefix"]["attempts"] == [_expected(0)]
    with Store(tmp_path / "store") as store:
        assert EpisodeReceipts(store, "run").manifest("old-child") == expected


def test_read_accessor_never_creates_a_missing_table_or_commits(tmp_path):
    with Store(tmp_path / "store") as store:
        with store.transaction():
            with pytest.raises(ValueError, match="episode_receipts_not_bound"):
                EpisodeReceipts.read_manifest(store.db, "run", "missing")
            assert store.db.in_transaction
            assert store.db.execute("SELECT 1 FROM sqlite_master WHERE "
                "name='runtime_receipt_inheritance'").fetchone() is None


def test_plain_sqlite_connection_is_supported_without_a_row_factory():
    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE TABLE runtime_receipt_inheritance (run_id,episode_id,parent_episode_id,"
                   "through_receipt_index,received_report_prefix)")
        db.execute("INSERT INTO runtime_receipt_inheritance VALUES(?,?,?,?,?)",
                   ("run", "root", None, None, canonical(_empty())))
        assert EpisodeReceipts.read_manifest(db, "run", "root") == {"version": RECEIPT_VERSION,
            "parent_episode_id": None, "through_receipt_index": None, "received_report_prefix": _empty()}
        assert db.in_transaction


@pytest.mark.parametrize("schema", ["absent", "legacy", "current"])
def test_constructor_schema_and_receipts_roll_back_with_callers_failed_commission(tmp_path, schema):
    with Store(tmp_path / "store") as store:
        journal = Journal(store, "run")
        if schema == "legacy":
            store.db.execute("CREATE TABLE runtime_receipt_inheritance (run_id TEXT NOT NULL, "
                "episode_id TEXT NOT NULL, parent_episode_id TEXT, through_receipt_index INTEGER, "
                "PRIMARY KEY(run_id,episode_id))")
            store.db.execute("INSERT INTO runtime_receipt_inheritance VALUES('run','parent',NULL,NULL)")
        elif schema == "current":
            EpisodeReceipts(store, "run").bind("parent")
        before = [tuple(row) for row in store.db.execute("PRAGMA table_info(runtime_receipt_inheritance)")]
        with pytest.raises(RuntimeError, match="commission_failed"):
            with store.transaction():
                _attempt(journal, 0)
                receipts = EpisodeReceipts(store, "run")
                receipts.bind("parent")
                child = receipts.bind("child", "parent")
                assert child["received_report_prefix"]["attempts"] == [_expected(0)]
                assert store.db.in_transaction
                raise RuntimeError("commission_failed")
        assert [tuple(row) for row in store.db.execute("PRAGMA table_info(runtime_receipt_inheritance)")] == before
        assert store.db.execute("SELECT count(*) FROM runtime_report_attempts").fetchone()[0] == 0
        if schema != "absent":
            assert store.db.execute("SELECT count(*) FROM runtime_receipt_inheritance "
                "WHERE episode_id='child'").fetchone()[0] == 0


@pytest.mark.parametrize("mutation", ["index_bool", "index_negative", "duplicate", "unordered",
    "missing_hash", "wrong_hash", "empty_child", "extra_field", "unknown_version", "prose"])
def test_invalid_stored_metadata_cannot_be_silently_accepted(tmp_path, mutation):
    with Store(tmp_path / "store") as store:
        receipts = EpisodeReceipts(store, "run")
        receipts.bind("root")
        prefix = {**_empty(), "attempts": [_expected(1)]}
        row = prefix["attempts"][0]
        if mutation == "index_bool": row["decision_index"] = True
        elif mutation == "index_negative": row["decision_index"] = -1
        elif mutation == "duplicate": prefix["attempts"].append(deepcopy(row))
        elif mutation == "unordered": prefix["attempts"].append(_expected(0))
        elif mutation == "missing_hash": del row["form_sha256"]
        elif mutation == "wrong_hash": row["form_sha256"] = "not a digest"
        elif mutation == "empty_child": row["child_episode_id"] = ""
        elif mutation == "extra_field": row["unrequested_form"] = FORM
        elif mutation == "unknown_version": prefix["version"] = "made_up"
        elif mutation == "prose": prefix = "received something"
        store.db.execute("UPDATE runtime_receipt_inheritance SET received_report_prefix=?",
                         (canonical(prefix),))
        with pytest.raises(ValueError, match="invalid_received_report_prefix"):
            receipts.manifest("root")


def test_commission_rejects_changed_prefix_even_when_saved_child_request_matches_change(tmp_path):
    from test_episode_commissions import setup_case
    from gene_annotation_episode.episode_commissions import CommissionCoordinator, CommissionError

    store, journal, backend, operands, _ = setup_case(tmp_path)
    with store:
        child = operands["child"]
        child["request"]["message"]["knowledge_inheritance"]["received_report_prefix"]["attempts"] = [_expected(0)]
        store.db.execute("UPDATE runtime_episodes SET request=? WHERE episode_id=?",
                         (canonical(child["request"]), child["episode_id"]))
        with pytest.raises(CommissionError, match="identity_conflict"):
            CommissionCoordinator(store, journal, backend).select(**operands)
        assert store.db.execute("SELECT count(*) FROM runtime_commission_intents").fetchone()[0] == 0


def test_appservice_custody_compares_complete_prefix_without_committing(tmp_path):
    from test_bvbrc_appservice_custody import SavedRecords, launch_assignment
    from gene_annotation_episode.bvbrc_appservice_custody import AppServiceCustodyError

    with Store(tmp_path / "store") as store:
        saved = SavedRecords(store)
        _attempt(saved.journal, 0, parent=saved.root.episode_id)
        child = saved.child(saved.root, "launch", launch_assignment(), 2)
        with store.transaction():
            assert saved.custody._inheritance(child, saved.root) == 0
            assert store.db.in_transaction
            altered = plain(child.request)
            altered["message"]["knowledge_inheritance"]["received_report_prefix"]["attempts"] = []
            with pytest.raises(AppServiceCustodyError, match="commission_inheritance_conflict"):
                saved.custody._inheritance(replace(child, request=altered), saved.root)
            assert store.db.in_transaction
