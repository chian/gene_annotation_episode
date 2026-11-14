"""An audit must retain rejected requests separately from executed failures.

This small engineered trace exercises the auditor, not an autonomous episode.
"""
import hashlib
import json
import sqlite3

from audit_a106_workflow import assessment_receipt_inventory, audit


def test_rejected_request_and_partial_acquisition_failure_are_both_visible(tmp_path):
    (tmp_path / "state").mkdir()
    (tmp_path / "input.txt").write_text("ACDE\n")
    (tmp_path / "launch.json").write_text(json.dumps({
        "sequence_sha256": hashlib.sha256(b"ACDE").hexdigest()}))
    (tmp_path / "source-pins.json").write_text("{}")
    feedback = {"category": "action_contract", "status": "invalid", "detail": {
        "code": "schema_validation", "issues": [{"expected": "object", "rule": "type",
            "path": ["arguments", "representations", 1, "selection", "candidates", 0, "numerator"]}],
        "more_issues": False}}
    with sqlite3.connect(tmp_path / "state/state.sqlite3") as connection:
        connection.executescript("""
            CREATE TABLE runtime_episodes (episode_id TEXT, path TEXT, state TEXT, request TEXT);
            CREATE TABLE runtime_actions (episode_id TEXT, decision_index INTEGER, action TEXT, result TEXT);
            CREATE TABLE runtime_decision_effects (episode_id TEXT, decision_index INTEGER, effect TEXT);
            CREATE TABLE runtime_forms (episode_id TEXT, form TEXT);
            CREATE TABLE runtime_report_attempts (parent_episode_id TEXT, child_episode_id TEXT,
                decision_index INTEGER, delivery_ref TEXT, form TEXT, failure TEXT);
            CREATE TABLE runtime_model_calls (call_index INTEGER);
            CREATE TABLE runtime_decision_exchanges (decision_index INTEGER);
        """)
        connection.execute("INSERT INTO runtime_episodes VALUES(?,?,?,?)",
            ("child", json.dumps([["literature_perturbation", "child"]]), "active", "{}"))
        for index, effect in ((303, {"state": "rejected", "feedback": feedback}),
                              (304, {"state": "selected", "feedback": None})):
            connection.execute("INSERT INTO runtime_decision_effects VALUES(?,?,?)",
                ("child", index, json.dumps(effect)))
        # 303 has no executed action. 304 is a failed HTTP acquisition, while
        # 305 is a valid partial result with no recorded error.
        for index, outcome in ((304, {"status": "partial", "result": {
                "acquired": False, "failure_code": "ncbi_entrez_http_not_success"},
                "changed_record_refs": ["source_retained_failure"]}),
                (305, {"status": "partial", "result": {"acquired": True},
                    "changed_record_refs": ["source_partial_data"]})):
            connection.execute("INSERT INTO runtime_actions VALUES(?,?,?,?)",
                ("child", index, json.dumps({"kind": "tool", "tool": "public.ncbi.entrez"}),
                    json.dumps(outcome)))
    connection.close()

    result = audit(tmp_path)
    assert result["input_hash_matches"]
    assert result["rejected_decisions"] == [{"episode_id": "child", "decision_index": 303,
        "feedback": feedback}]
    assert result["action_counts"] == {"public.ncbi.entrez": 2}
    assert len(result["failed_actions"]) == 1
    failure = result["failed_actions"][0]
    assert failure["decision_index"] == 304
    assert failure["failure_code"] == "ncbi_entrez_http_not_success"
    assert failure["changed_record_refs"] == ["source_retained_failure"]
    assert result["numerical_publications"] == []
    assert result["report_delivery_attempts"] == []
    assert result["recorded_final_score_receipts"] == []
    assert result["recorded_assessment_receipts"] == []


def test_saved_revision_is_not_counted_as_received_by_its_parent():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    with connection:
        connection.executescript("""
            CREATE TABLE records (id TEXT, record_type TEXT, data TEXT);
            CREATE TABLE current_revisions (record_type TEXT, record_ref TEXT);
            CREATE TABLE runtime_record_receipts (receipt_index INTEGER, run_id TEXT,
                episode_id TEXT, record_ref TEXT, receipt_kind TEXT, source_index INTEGER);
        """)
        for ref, revision, replaced in (("old", 1, []), ("new", 2, ["old"]),
                                        ("saved_only", 1, [])):
            connection.execute("INSERT INTO records VALUES(?,?,?)", (ref, "assessment",
                json.dumps(dict(revision=revision, observation_ref="observation",
                    hypothesis_ref="hypothesis", relation="mixed", applicability="transfer",
                    investigation_finding=dict(status="retained", replaces_refs=replaced)))))
        connection.executemany("INSERT INTO current_revisions VALUES(?,?)",
            [("assessment", "new"), ("assessment", "saved_only")])
        connection.executemany("INSERT INTO runtime_record_receipts VALUES(?,?,?,?,?,?)", [
            (1, "run", "parent", "old", "child_form", 5),
            (2, "run", "child", "new", "own_action", 589)])
        rows = assessment_receipt_inventory(connection,
            {"records", "current_revisions", "runtime_record_receipts"},
            {"parent": "annotation", "child": "literature_perturbation"})
    connection.close()
    assert [(row["episode_id"], row["record_ref"]) for row in rows] == [
        ("parent", "old"), ("child", "new")]
    old, new = rows
    assert old["role"] == "annotation" and old["revision"] == 1
    assert old["first_receipt_kind"] == "child_form" and old["first_source_index"] == 5
    assert old["is_database_current_revision"] is False
    assert new["revision"] == 2 and new["replaces_refs"] == ["old"]
    assert new["first_receipt_kind"] == "own_action" and new["is_database_current_revision"] is True
